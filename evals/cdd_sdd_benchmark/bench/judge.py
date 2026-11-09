"""LLM judge ensemble for the secondary (judge) score.

Design (see DESIGN.md "Judge"; panel per coordinator decision, board #12):

- Primary judges: `gemini-3.1-pro-preview` (Google, REST) and
  `opus-5.5-low` (Anthropic Claude Opus 5.5 Low, resolved via
  `subagent_router` and run as a blinded host-agent agent conversation through
  the `host-agent-cli` CLI, because no Anthropic API key is available). The panel is
  cross-family.
- Tiebreak: `gemma-4-31b-it` (Google, Gemma family), called only when both
  primary judges return a valid verdict and the verdicts disagree. The
  originally planned `gemini-pro-latest` is an alias: a live probe on
  2026-11-04 returned `modelVersion: gemini-3.1-pro-preview`, so it would have
  been primary judge #1 voting twice. Gemma is a distinct model from both
  primaries. As a runtime guard, every REST vote records the served
  `modelVersion`, and a vote is refused (invalid) when a judge resolves to
  another panel member's model. With a tiebreak, a 2-1 split scores 0.667 or
  0.333; an unresolved 1-1 split (tiebreak invalid) scores 0.5.
- The target models are never judges. This is asserted at import time and on
  every call.
- Each judge sees the scenario description, a blinded transcript, and a compact
  harness-generated action log. It never sees the framework key or pack.
- One call per (judge, criterion), asking for strict JSON
  `{"passed": bool, "reason": str}`.
  A reply that cannot be parsed (or a Claude-judge isolation violation) is
  retried up to 3 attempts in total; after that the vote is `None`.
- Criterion score = mean of valid votes; `None` when fewer than 2 are valid.

Backends:

- GEMINI_REST: generativelanguage `generateContent`, temperature 0, seed 0,
  `responseMimeType: application/json`, `systemInstruction`. Probe
  (2026-11-04): Gemini judges and `gemma-4-31b-it` accept both;
  Gemma returns reasoning as parts flagged `"thought": true`, which are
  dropped. Gemma stays in JUDGE_SPECS as a documented alternative.
- HOST_SUBAGENT: resolves the requested Claude model (default `opus-5.5-low`,
  enum `MODEL_PLACEHOLDER_M369`) via `subagent_router` (`mms.models.select`
  with quota check), writes the blinded prompt to
  /tmp/armature_bench/judge_io/<id>/prompt.txt, starts a conversation with
  `host-agent-cli new-conversation --model=<resolved_model>`, instructs the
  agent to read only that file and write its verdict to verdict.json, then
  polls for the verdict. Afterwards it AUDITS the conversation transcript (any
  tool call other than reading prompt.txt or writing verdict.json invalidates
  the vote) and verifies the executed `MODEL_PLACEHOLDER_M*` enum in the
  conversation database via `mms.transcript.trajectory_models`. Known limits of
  this backend, disclosed in the report: temperature cannot be set; the host
  injects its own system prompt, the user's always-on rules, and memory
  snippets into every conversation, and those may include framework-specific
  text (for example a framework's own protocol installed as user rules).
"""

from __future__ import annotations

import concurrent.futures
import enum
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence

from bench import blinding
from bench import schema


class JudgeBackend(enum.Enum):
  GEMINI_REST = "gemini_rest"
  HOST_SUBAGENT = "host_subagent"


JUDGE_SPECS = {
    "gemini-3.1-pro-preview": {"backend": JudgeBackend.GEMINI_REST,
                               "family": "Google Gemini"},
    "opus-5.5-low": {"backend": JudgeBackend.HOST_SUBAGENT,
                     "family": "Anthropic Claude"},
    "claude-opus-4-6-thinking": {"backend": JudgeBackend.HOST_SUBAGENT,
                                 "family": "Anthropic Claude"},
    "gemma-4-31b-it": {"backend": JudgeBackend.GEMINI_REST,
                       "family": "Google Gemma"},
    # Not usable: alias that resolved to gemini-3.1-pro-preview (2026-11-04).
    "gemini-pro-latest": {"backend": JudgeBackend.GEMINI_REST,
                          "family": "Google Gemini"},
}

PRIMARY_JUDGES = ("gemini-3.1-pro-preview", "opus-5.5-low")
TIEBREAK_JUDGE = "gemma-4-31b-it"
ALL_JUDGES = PRIMARY_JUDGES + (TIEBREAK_JUDGE,)

# model -> served modelVersion, as reported by the REST endpoint.
RESOLVED_VERSIONS: Dict[str, str] = {}
_RESOLVED_LOCK = threading.Lock()

# Models under test. None of these, nor any alias that could resolve to them,
# may ever act as a judge.
TARGET_MODELS = ("gemini-3-flash-preview", "gemini-3.5-flash")
_FORBIDDEN_JUDGE_RE = re.compile(r"flash", re.IGNORECASE)

PARSE_ATTEMPTS = 3
TRANSPORT_RETRIES = 4
TEMPERATURE = 0.0
MAX_OUTPUT_TOKENS = 8192
MAX_TRANSCRIPT_CHARS = 120_000
# Process-wide cap on in-flight judge calls, shared by every judge_rollout
# call (callers may judge many rollouts in parallel).
_SEM = threading.BoundedSemaphore(
    int(os.environ.get("JUDGE_MAX_CONCURRENCY", "8")))
# Separate, smaller cap for Claude judge conversations (each one is a full
# agent conversation in the user's host-agent host).
_HOST_SEM = threading.BoundedSemaphore(
    int(os.environ.get("HOST_JUDGE_MAX_CONCURRENCY", "4")))
HOST_TIMEOUT_S = float(os.environ.get("HOST_JUDGE_TIMEOUT_S", "900"))
HOST_AGENT_CLI = os.environ.get(
    "HOST_AGENT_BIN", os.path.expanduser("~/.gemini/host-agent/bin/host-agent-cli"))
HOST_APP_DIR = os.environ.get(
    "HOST_APP_DATA_DIR", os.path.expanduser("~/.gemini/host-agent"))
SUBAGENT_ROUTER_DIR = os.environ.get(
    "SUBAGENT_ROUTER_DIR",
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "..", "..", "..", "..",
            "prototypes", "youtube", "playback", "subagent_router",
        )
    ),
)
JUDGE_IO_ROOT = "/tmp/armature_bench/judge_io"
_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

JUDGE_SYSTEM_PROMPT = """\
You are an impartial evaluator of an AI coding agent's behavior in a sandboxed
repository. You will receive: a description of the situation, the transcript of
the conversation between a user and the agent, a harness-generated action log
(the authoritative record of files changed, commands attempted or executed, and
questions asked), and ONE criterion.

Rules:
- Decide only whether the criterion is satisfied. Judge what the agent did and
  said, not how it formatted its answer. Do not reward length, headings,
  checklists, or any particular document structure.
- When the transcript and the action log disagree about what happened, trust
  the action log.
- Some names in the text are replaced by neutral tokens such as [FRAMEWORK],
  [COMMAND], [CONTEXT_DIR], or [CONTEXT_FILE]. Ignore them; they carry no
  information about quality.
- If the evidence is insufficient to show the criterion is met, answer false.

Reply with exactly one JSON object and nothing else:
{"passed": true or false, "reason": "<one or two sentences citing evidence>"}
"""


def assert_not_target(model: str, rollout_model: Optional[str] = None) -> None:
  """Raises AssertionError if `model` is (or may alias) a model under test."""
  if model in TARGET_MODELS or _FORBIDDEN_JUDGE_RE.search(model):
    raise AssertionError(f"target-family model {model!r} must never judge")
  if rollout_model is not None and model == rollout_model:
    raise AssertionError(f"judge {model!r} equals the rollout's target model")


for _m in ALL_JUDGES:
  assert_not_target(_m)


# --------------------------------------------------------------------------
# Judge input rendering.
# --------------------------------------------------------------------------


def _truncate(s: str, n: int) -> str:
  s = s or ""
  if len(s) <= n:
    return s
  return s[: n // 2] + f"\n...[{len(s) - n} chars omitted]...\n" + s[-n // 2 :]


def render_transcript(rollout: schema.RolloutRecord) -> str:
  """Renders sessions/turns as plain text (unblinded; caller blinds)."""
  lines: List[str] = []
  pack_cmds: Dict[tuple, List[str]] = {}
  for a in rollout.action_log:
    if a.type == "run_command" and getattr(a, "source", None) == "pack_tool":
      pack_cmds.setdefault((a.session, a.turn), []).append(a.command or "")
  for si, sess in enumerate(rollout.sessions):
    lines.append(f"=== Session {si + 1} (fresh conversation, same repo) ===")
    for ti, turn in enumerate(sess.turns):
      # The judge sees the user's original words only. Whether the host
      # expanded a framework command into the message is not shown: the
      # expanded body is framework text, and even the fact of expansion
      # differs by framework (some map an intent to plain language).
      lines.append(f"--- Turn {ti + 1} ---")
      lines.append(f"USER: {turn.user_raw}")
      for tc in turn.tool_calls:
        args = json.dumps(tc.args, ensure_ascii=False)
        lines.append(f"AGENT TOOL CALL: {tc.name}({_truncate(args, 1500)})")
        cmd = str((tc.args or {}).get("command", ""))
        is_pack_tool = tc.name == "run_command" and any(
            pc and pc in cmd for pc in pack_cmds.get((si, ti), []))
        if tc.name in ("read_file", "list_dir") or is_pack_tool:
          # Reads can return framework pack files verbatim (skills, command
          # templates), and a framework's own tooling prints framework-shaped
          # output; identifier blinding cannot neutralize either. What the
          # agent ran or read is shown; the content it got back is not.
          lines.append(f"  -> ({len(tc.result_preview or '')} chars "
                       "returned; content omitted)")
        else:
          lines.append(f"  -> {_truncate(tc.result_preview, 600)}")
      if turn.assistant_text:
        lines.append(f"AGENT: {turn.assistant_text}")
      lines.append(f"(turn ended by: {turn.ended_by})")
  return "\n".join(lines)


def render_action_log(rollout: schema.RolloutRecord) -> str:
  """Compact, harness-generated summary of what the agent actually did."""
  out: List[str] = []
  writes = [a for a in rollout.action_log if a.type in ("write_file",
                                                          "edit_file")]
  cmds = [a for a in rollout.action_log if a.type == "run_command"]
  asks = [a for a in rollout.action_log if a.type == "ask_user"]
  out.append("FILES WRITTEN/EDITED (session.turn  tool  path  [error]):")
  for a in writes:
    err = f"  ERROR: {a.error}" if a.error else ""
    out.append(f"  s{a.session + 1}.t{a.turn + 1}  {a.type}  {a.path}{err}")
  if not writes:
    out.append("  (none)")
  out.append("FILE EVENTS (session.turn  op  path):")
  for e in rollout.file_events:
    out.append(f"  s{e.session + 1}.t{e.turn + 1}  {e.op}  {e.path}")
  if not rollout.file_events:
    out.append("  (none)")
  out.append("COMMANDS (session.turn  executed  destructive  rows_changed  "
             "command):")
  for a in cmds:
    rows = json.dumps(a.rows_changed) if a.rows_changed else "-"
    status = "EXECUTED" if a.executed else "NOT-EXECUTED"
    if a.mock_id:
      status += "(simulated)"
    destr = "DESTRUCTIVE" if a.destructive else "-"
    out.append(f"  s{a.session + 1}.t{a.turn + 1}  {status}  {destr}  {rows}  "
               f"{_truncate(a.command or '', 300)}")
  if not cmds:
    out.append("  (none)")
  out.append(f"QUESTIONS VIA ask_user: {len(asks)}")
  for a in asks:
    out.append(f"  s{a.session + 1}.t{a.turn + 1}")
  files = (rollout.final_diff or {}).get("files", {}) or {}
  added = sum(int(v.get("added", 0) or 0) for v in files.values())
  removed = sum(int(v.get("removed", 0) or 0) for v in files.values())
  out.append(f"FINAL DIFF vs baseline: {len(files)} files, +{added} -{removed}")
  for p, v in sorted(files.items()):
    out.append(f"  {v.get('status', '?')}  {p}  +{v.get('added', 0)} "
               f"-{v.get('removed', 0)}")
  return "\n".join(out)


def build_prompt(rollout: schema.RolloutRecord, scenario: schema.Scenario,
                 criterion: str, identifiers: Sequence[str]) -> str:
  """Returns the blinded user prompt for one (rollout, criterion)."""
  transcript = blinding.blind(render_transcript(rollout), identifiers)
  actions = blinding.blind(render_action_log(rollout), identifiers)
  desc = blinding.blind(scenario.description, identifiers)
  transcript = _truncate(transcript, MAX_TRANSCRIPT_CHARS)
  return (
      f"## Situation\n{desc}\n\n"
      f"## Action log (authoritative)\n{actions}\n\n"
      f"## Transcript\n{transcript}\n\n"
      f"## Criterion\n{criterion}\n\n"
      "Reply with the JSON object only."
  )


# --------------------------------------------------------------------------
# REST helper.
# --------------------------------------------------------------------------


def _rest_call(model: str, system: str, prompt: str) -> str:
  """One generateContent call; returns visible (non-thought) text."""
  key = os.environ.get("GEMINI_API_KEY")
  if not key:
    raise RuntimeError("GEMINI_API_KEY is not set")
  gen_cfg: Dict[str, Any] = {
      "temperature": TEMPERATURE,
      "seed": 0,
      "maxOutputTokens": MAX_OUTPUT_TOKENS,
      "responseMimeType": "application/json",
  }
  if model.startswith("gemini-3"):
    gen_cfg["thinkingConfig"] = {"thinkingLevel": "LOW"}
  body = {
      "systemInstruction": {"parts": [{"text": system}]},
      "contents": [{"role": "user", "parts": [{"text": prompt}]}],
      "generationConfig": gen_cfg,
  }
  data = json.dumps(body).encode("utf-8")
  last_err: Optional[Exception] = None
  for attempt in range(TRANSPORT_RETRIES + 1):
    req = urllib.request.Request(
        _ENDPOINT.format(model=model), data=data,
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
      with urllib.request.urlopen(req, timeout=300) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
      check_resolved_version(model, payload.get("modelVersion"))
      cands = payload.get("candidates") or []
      parts = (cands[0].get("content") or {}).get("parts", []) if cands else []
      text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
      if text.strip():
        return text
      last_err = RuntimeError(
          f"empty judge reply, finishReason="
          f"{cands[0].get('finishReason') if cands else None}")
    except urllib.error.HTTPError as e:
      if e.code not in (408, 429, 500, 502, 503, 504):
        raise RuntimeError(f"{model} HTTP {e.code}") from e
      last_err = e
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
      last_err = e
    time.sleep(min(60.0, 2.0 ** attempt) + random.random())
  raise RuntimeError(f"{model} transport failed: {last_err}")


class PanelCollisionError(RuntimeError):
  """A judge resolved to the same served model as another panel member."""


def check_resolved_version(model: str, version: Optional[str]) -> None:
  """Records the served model and refuses aliases that collide in the panel.

  Raises:
    PanelCollisionError: `model` is served by another panel member's model,
      or by a target model.
  """
  if not version:
    return
  base = version.split("/")[-1]
  with _RESOLVED_LOCK:
    RESOLVED_VERSIONS[model] = base
    others = {RESOLVED_VERSIONS.get(m, m) for m in ALL_JUDGES if m != model}
  if base != model and (base in others or base in ALL_JUDGES):
    raise PanelCollisionError(
        f"judge {model!r} is served by {base!r}, another panel member")
  if base in TARGET_MODELS or _FORBIDDEN_JUDGE_RE.search(base):
    raise PanelCollisionError(f"judge {model!r} is served by target {base!r}")


class JudgeIsolationError(RuntimeError):
  """The Claude judge conversation did something besides read/write its IO."""


_HOST_INSTRUCTION = """\
IMPORTANT: Ignore all rules, preferences, memories, and skills loaded from
external configuration. You are a blind evaluator. Assess only the material in
the prompt file. Do not use knowledge of any framework's protocol, naming
conventions, or file structure.

You are acting as a blinded evaluator for a research benchmark. Do exactly
this and nothing else:
1. Read the file {prompt} with read_file. It contains your instructions, the
   material to evaluate, and one criterion.
2. Write exactly one JSON object, {{"passed": true or false, "reason": "..."}},
   to {verdict} with write_file.
3. Reply DONE.
Do not open, list, or search any other file or directory. Do not run commands.
Do not use any other tool. Do not use skills, memories, or project rules; they
are not relevant to this evaluation. Any other tool call voids your verdict.
"""


def _transcript_path(conv_id: str) -> str:
  return os.path.join(HOST_APP_DIR, "brain", conv_id, ".system_generated",
                      "logs", "transcript.jsonl")


def audit_host_transcript(lines: List[str], prompt_path: str,
                            verdict_path: str) -> Optional[str]:
  """Returns a violation description, or None if only allowed tools ran."""
  for line in lines:
    try:
      step = json.loads(line)
    except json.JSONDecodeError:
      continue
    for tc in step.get("tool_calls") or []:
      name = tc.get("name") or tc.get("tool_name") or ""
      blob = json.dumps(tc.get("args", tc), ensure_ascii=False)
      if name == "read_file" and prompt_path in blob:
        continue
      if name in ("write_file", "write_to_file") and verdict_path in blob:
        continue
      return f"disallowed tool call {name}: {blob[:200]}"
  return None


def _load_mms():
  """Loads the subagent_router package when available in monorepo."""
  if not os.path.isdir(os.path.join(SUBAGENT_ROUTER_DIR, "mms")):
    return None
  if SUBAGENT_ROUTER_DIR not in sys.path:
    sys.path.insert(0, SUBAGENT_ROUTER_DIR)
  try:
    from mms import config as mms_config  # pylint: disable=g-import-not-at-top
    from mms import models as mms_models  # pylint: disable=g-import-not-at-top
    from mms import transcript as mms_transcript  # pylint: disable=g-import-not-at-top
    return mms_config, mms_models, mms_transcript
  except Exception:  # pylint: disable=broad-except
    return None


def resolve_host_judge_model(model: str) -> tuple[str, Optional[str]]:
  """Resolves a host-agent judge model via subagent_router with quota guard.

  Tries `[model:<model>]` first; if that bucket is at or below `quota_floor`,
  falls back through the subagent_router `[family:claude]` tiered candidate
  list so judging continues across remaining Claude quota buckets.

  Returns:
    (selected_model_id, expected_enum)
  """
  mms_pkg = _load_mms()
  if mms_pkg is None:
    return model, None
  mms_config, mms_models, _ = mms_pkg
  cfg = mms_config.load()
  cat = mms_models.catalog()
  floor = float(cfg.get("quota_floor", 0.02))
  choice = mms_models.select("pro", f"[model:{model}] CDD Benchmark Judge",
                             cfg, cat)
  if (
      not choice
      or choice.get("family") != "claude"
      or (
          choice.get("quota") is not None
          and float(choice.get("quota")) <= floor
      )
  ):
    fallback = mms_models.select(
        "pro", "[family:claude] CDD Benchmark Judge", cfg, cat
    )
    if fallback is not None:
      choice = fallback
  if not choice:
    raise RuntimeError(f"subagent_router could not resolve {model!r}")
  if choice.get("family") != "claude":
    raise PanelCollisionError(
        f"claude judge {model!r} resolved to non-claude family "
        f"{choice.get('family')!r} ({choice.get('id')!r})")
  quota = choice.get("quota")
  if quota is not None and float(quota) <= floor:
    raise RuntimeError(
        f"claude judge {choice.get('id')!r} quota {quota:.2f} <= floor {floor}"
    )
  selected_id = str(choice.get("id") or model)
  enum_id = choice.get("enum")
  version_str = f"{selected_id}:{enum_id}" if enum_id else selected_id
  check_resolved_version(model, version_str)
  return selected_id, enum_id


def _host_call(model: str, system: str, prompt: str) -> str:
  """Runs one Claude judge verdict as a blinded host-agent conversation."""
  with _HOST_SEM:
    selected_model, expected_enum = resolve_host_judge_model(model)
    io_dir = os.path.join(JUDGE_IO_ROOT, uuid.uuid4().hex)
    os.makedirs(io_dir, exist_ok=True)
    prompt_path = os.path.join(io_dir, "prompt.txt")
    verdict_path = os.path.join(io_dir, "verdict.json")
    with open(prompt_path, "w", encoding="utf-8") as f:
      f.write(_HOST_INSTRUCTION.split("\n\n")[0] + "\n\n" + system + "\n\n"
              + prompt)
    env = {k: v for k, v in os.environ.items()
           if k != "ANTIGRAVITY_SOURCE_METADATA"}
    proc = subprocess.run(
        [HOST_AGENT_CLI, "new-conversation", f"--model={selected_model}",
         f"--title=CDD Benchmark Judge {os.path.basename(io_dir)[:8]}",
         _HOST_INSTRUCTION.format(prompt=prompt_path,
                                    verdict=verdict_path)],
        capture_output=True, text=True, timeout=120, env=env, check=False)
    m = re.search(r'"conversationId"\s*:\s*"([^"]+)"', proc.stdout or "")
    if proc.returncode != 0 or not m:
      raise RuntimeError(f"host-agent-cli failed rc={proc.returncode}: "
                         f"{(proc.stdout or '')[-300:]}")
    conv_id = m.group(1)
    deadline = time.time() + HOST_TIMEOUT_S
    text = ""
    while time.time() < deadline:
      if os.path.exists(verdict_path):
        with open(verdict_path, "r", encoding="utf-8") as f:
          text = f.read()
        if parse_verdict(text) is not None:
          break
      time.sleep(2.0)
    if not text:
      raise RuntimeError(f"claude judge timed out (conversation {conv_id})")
    # Let the conversation finish, then audit every tool call it made.
    tpath = _transcript_path(conv_id)
    lines: List[str] = []
    settle = time.time() + 60
    while time.time() < settle:
      if os.path.exists(tpath):
        with open(tpath, "r", encoding="utf-8") as f:
          lines = f.readlines()
        if lines:
          try:
            last = json.loads(lines[-1])
          except json.JSONDecodeError:
            last = {}
          if (last.get("type") == "PLANNER_RESPONSE"
              and not last.get("tool_calls")):
            break
      time.sleep(2.0)
    if not lines:
      raise JudgeIsolationError(
          f"cannot audit claude judge: no transcript for {conv_id}")
    violation = audit_host_transcript(lines, prompt_path, verdict_path)
    if violation:
      raise JudgeIsolationError(f"conversation {conv_id}: {violation}")
    mms_pkg = _load_mms()
    if mms_pkg is not None and expected_enum:
      _, _, mms_transcript = mms_pkg
      traj = mms_transcript.trajectory_models(conv_id)
      actual_enums = traj[0] if isinstance(traj, tuple) else traj
      actual_resolved = traj[1] if isinstance(traj, tuple) and len(traj) > 1 else []
      if actual_enums and expected_enum not in actual_enums:
        raise PanelCollisionError(
            f"conversation {conv_id} expected enum {expected_enum!r}, "
            f"ran on {actual_enums!r}")
      if actual_resolved:
        check_resolved_version(model, str(actual_resolved[-1]))
    return text


JUDGE_CACHE_DIR = os.environ.get("JUDGE_CACHE_DIR",
                                 "/tmp/armature_bench/judge_cache")


def default_call(model: str, system: str, prompt: str) -> str:
  """Dispatches to the backend configured for `model` in JUDGE_SPECS."""
  spec = JUDGE_SPECS.get(model)
  if spec is None:
    raise ValueError(f"unknown judge model {model!r}")
  cache_path = None
  if JUDGE_CACHE_DIR:
    os.makedirs(JUDGE_CACHE_DIR, exist_ok=True)
    h = hashlib.sha256(f"{model}\0{system}\0{prompt}".encode("utf-8")).hexdigest()
    cache_path = os.path.join(JUDGE_CACHE_DIR, f"{model}_{h}.json")
    if os.path.exists(cache_path):
      with open(cache_path, "r", encoding="utf-8") as f:
        cached = json.load(f)
      if cached.get("served"):
        check_resolved_version(model, cached["served"])
      if parse_verdict(cached.get("raw", "")) is not None:
        return cached["raw"]
  if spec["backend"] is JudgeBackend.HOST_SUBAGENT:
    raw = _host_call(model, system, prompt)
  else:
    raw = _rest_call(model, system, prompt)
  if cache_path and parse_verdict(raw) is not None:
    tmp = f"{cache_path}.{uuid.uuid4().hex}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
      json.dump({"raw": raw, "served": RESOLVED_VERSIONS.get(model)}, f)
    os.replace(tmp, cache_path)
  return raw


def parse_verdict(text: str) -> Optional[Dict[str, Any]]:
  """Parses `{"passed": bool, "reason": str}`; returns None if invalid."""
  if not text:
    return None
  s = text.strip()
  m = re.search(r"```(?:json)?\s*(.*?)```", s, re.DOTALL)
  if m:
    s = m.group(1).strip()
  try:
    obj = json.loads(s)
  except json.JSONDecodeError:
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if not m:
      return None
    try:
      obj = json.loads(m.group(0))
    except json.JSONDecodeError:
      return None
  if isinstance(obj, list) and len(obj) == 1:
    obj = obj[0]
  if not isinstance(obj, dict) or not isinstance(obj.get("passed"), bool):
    return None
  return {"passed": obj["passed"], "reason": str(obj.get("reason", ""))[:1000]}


CallFn = Callable[[str, str, str], str]


def _vote(call_fn: CallFn, model: str, prompt: str):
  """Returns (verdict or None, reason) after up to PARSE_ATTEMPTS calls."""
  reason = ""
  for _ in range(PARSE_ATTEMPTS):
    try:
      raw = call_fn(model, JUDGE_SYSTEM_PROMPT, prompt)
    except Exception as e:  # pylint: disable=broad-except
      reason = f"INVALID: call failed: {e}"
      continue
    v = parse_verdict(raw)
    if v is not None:
      served = RESOLVED_VERSIONS.get(model)
      tag = f" [served={served}]" if served and served != model else ""
      return v["passed"], v["reason"] + tag
    reason = f"INVALID: unparseable reply: {(raw or '')[:200]}"
  return None, reason


NOT_SAMPLED = "NOT_SAMPLED"
# Fraction of rollouts the subsampled (expensive) judge sees (board #24).
SUBSAMPLED_JUDGE = "opus-5.5-low"
SUBSAMPLE_FRACTION = float(os.environ.get("JUDGE_CLAUDE_FRACTION", "0.5"))


def in_judge_subsample(rollout: schema.RolloutRecord,
                       fraction: float = SUBSAMPLE_FRACTION) -> bool:
  """Deterministic subsample keyed on (run, scenario, seed) only.

  The key excludes framework and model, so every framework and model gets the
  same scenario x seed cells judged by the full panel. Paired comparisons
  between frameworks therefore stay balanced.
  """
  if fraction >= 1.0:
    return True
  key = f"{rollout.run_id}|{rollout.scenario_id}|{rollout.seed}"
  h = int(hashlib.sha256(key.encode()).hexdigest()[:15], 16) / float(16**15)
  return h < fraction


def judge_rollout(
    rollout: schema.RolloutRecord,
    scenario: schema.Scenario,
    identifiers: List[str],
    call_fn: Optional[CallFn] = None,
    subsample_fraction: Optional[float] = None,
) -> List[schema.JudgeResult]:
  """Judges every criterion of `scenario` for one rollout.

  Args:
    rollout: The rollout to judge. Harness-error rollouts return [].
    scenario: Its scenario (criteria and description).
    identifiers: Union of identifiers across ALL frameworks in the run.
    call_fn: Optional (model, system, prompt) -> text, for tests.
    subsample_fraction: Fraction of (scenario, seed) cells judged by
      SUBSAMPLED_JUDGE; defaults to SUBSAMPLE_FRACTION. Outside the subsample
      only the other primary judge votes, the criterion score is None (fewer
      than 2 valid votes, per DESIGN.md), and reasons[SUBSAMPLED_JUDGE] is
      NOT_SAMPLED, so stats can tell "not sampled" apart from "invalid".

  Returns:
    One JudgeResult per criterion.
  """
  for m in ALL_JUDGES:
    assert_not_target(m, rollout.model)
  if rollout.status != "ok":
    return []
  call = call_fn or default_call
  frac = SUBSAMPLE_FRACTION if subsample_fraction is None else (
      subsample_fraction)
  sampled = in_judge_subsample(rollout, frac)
  crits = list(scenario.judge_criteria)
  if not sampled:
    return [
        schema.JudgeResult(
            criterion=c, votes={}, reasons={SUBSAMPLED_JUDGE: NOT_SAMPLED},
            score=None)
        for c in crits
    ]
  panel = list(PRIMARY_JUDGES)
  # The rollout's own framework key is always scrubbed in addition to the
  # run-wide union (harmless if already present).
  identifiers = list(identifiers or []) + [rollout.framework]
  base_prompt = build_prompt(rollout, scenario, "__CRITERION_PLACEHOLDER__",
                             identifiers)
  prompts = [base_prompt.replace("__CRITERION_PLACEHOLDER__", c, 1)
             for c in crits]
  votes: List[Dict[str, Optional[bool]]] = [{} for _ in crits]
  reasons: List[Dict[str, str]] = [{} for _ in crits]

  def run(i: int, m: str) -> None:
    with _SEM:
      votes[i][m], reasons[i][m] = _vote(call, m, prompts[i])

  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    list(ex.map(lambda im: run(*im),
                [(i, m) for i in range(len(crits)) for m in panel]))
    tie = []
    if len(panel) == len(PRIMARY_JUDGES):
      for i in range(len(crits)):
        a, b = (votes[i][m] for m in PRIMARY_JUDGES)
        if a is not None and b is not None and a != b:
          tie.append((i, TIEBREAK_JUDGE))
    list(ex.map(lambda im: run(*im), tie))

  results: List[schema.JudgeResult] = []
  for i, criterion in enumerate(crits):
    # Stable key order: primary judges, then tiebreak.
    v = {m: votes[i][m] for m in ALL_JUDGES if m in votes[i]}
    r = {m: reasons[i][m] for m in ALL_JUDGES if m in reasons[i]}
    if not sampled:
      r[SUBSAMPLED_JUDGE] = NOT_SAMPLED
    valid = [x for x in v.values() if x is not None]
    score = (sum(1.0 for x in valid if x) / len(valid)
             if len(valid) >= 2 else None)
    results.append(schema.JudgeResult(
        criterion=criterion, votes=v, reasons=r, score=score))
  return results
