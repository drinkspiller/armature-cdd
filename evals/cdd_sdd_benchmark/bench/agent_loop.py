"""Agent loop: runs one framework pack on one scenario in a fresh sandbox.

Every framework gets the same `BASE_PROMPT`, the same tools, and the same
generation config. The only per-framework inputs are what the pack provides:
its system-prompt additions, the files it installs, the rendering of the
scenario's neutral project context, and host-style command expansion of the
first user message.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import traceback
from typing import Any, Dict, List, Optional, Protocol

from bench import gemini_client
from bench import sandbox as sandbox_lib
from bench import schema

MAX_STEPS_PER_TURN = 40
TEMPERATURE = 1.0
MAX_OUTPUT_TOKENS = gemini_client.DEFAULT_MAX_OUTPUT_TOKENS
RESULT_PREVIEW_CHARS = 2000
# When a turn hits MAX_STEPS_PER_TURN, make one extra call with tool calling
# disabled so the turn still ends with a reply to the user.
WRAP_UP_AT_MAX_STEPS = True
WRAP_UP_MAX_CALLS = 3
WRAP_UP_REFUSAL = ("tools are disabled: the step limit was reached. Reply to "
                   "the user in plain text now.")
WRAP_UP_MESSAGE = ("You have reached the step limit. Please provide your final "
                   "response to the user now.")

BASE_PROMPT = """\
You are a coding agent working inside a software repository on the user's \
behalf. The repository is your current working directory.

Use the provided tools to inspect and change the repository: list_dir, \
read_file, write_file, edit_file, run_command (a restricted shell; some \
commands are unavailable and will say so), and ask_user. Paths are relative \
to the repository root.

When you need a decision or information that only the user can provide, call \
ask_user, or end your turn with the question as your final message. When you \
have finished what was asked, end your turn with a short summary for the user.

Follow the project's instructions below.
"""

TOOL_DECLARATIONS: List[Dict[str, Any]] = [
    {
        "name": "list_dir",
        "description": "List the entries of a directory in the repository.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string",
                         "description": "Directory path; '.' is the root."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a text file from the repository.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a text file in the repository.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": ("Replace one exact, unique occurrence of `old` with "
                        "`new` in a file."),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
        },
    },
    {
        "name": "run_command",
        "description": ("Run a shell command in the repository root and "
                        "return its exit code and output."),
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "ask_user",
        "description": ("Ask the user a question and wait for the answer. "
                        "Ends your turn."),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "options": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["question"],
        },
    },
]


class FrameworkPackLike(Protocol):
  """The subset of bench.frameworks.FrameworkPack the loop relies on."""

  key: str
  display_name: str
  visibility: str

  def system_prompt(self, base_prompt: str) -> str:
    ...

  def sandbox_files(self) -> Dict[str, str]:
    ...

  def render_context(self, project_context: Dict[str, Any]) -> Dict[str, str]:
    ...

  def expand_user_message(self, intent: str, text: str) -> str:
    ...

  def identifiers(self) -> List[str]:
    ...


def rollout_dir(sandbox_root: str, run_id: str, framework: str, model: str,
                scenario_id: str, seed: int) -> str:
  """Neutral per-rollout directory.

  The model sees absolute sandbox paths (pack tools print them), so the path
  must not reveal the framework, model, or scenario: it is an opaque digest.
  """
  digest = hashlib.sha256(
      json.dumps([run_id, framework, model, scenario_id, seed]).encode()
  ).hexdigest()[:16]
  return os.path.join(sandbox_root, f"rollout-{digest}")


def _append_user_parts(contents: List[Dict[str, Any]],
                       parts: List[Dict[str, Any]]) -> None:
  if contents and contents[-1].get("role") == "user":
    contents[-1]["parts"].extend(parts)
  else:
    contents.append({"role": "user", "parts": list(parts)})


def _response_part(call: Dict[str, Any], output: str) -> Dict[str, Any]:
  fr: Dict[str, Any] = {"name": call["name"], "response": {"output": output}}
  if call.get("id"):
    fr["id"] = call["id"]
  return {"functionResponse": fr}


def run_rollout(
    pack: FrameworkPackLike,
    scenario: schema.Scenario,
    model: str,
    seed: int,
    run_id: str,
    config_hash: str,
    sandbox_root: str = sandbox_lib.SANDBOX_BASE,
    client: Optional[gemini_client.GeminiClient] = None,
    keep_sandbox: bool = False,
) -> schema.RolloutRecord:
  """Runs every session and turn of `scenario`; never raises on API failure.

  Harness failures (API retries exhausted, sandbox setup errors, harness bugs)
  produce `status="harness_error"` with the error message; those rollouts are
  excluded from scoring.
  """
  fh_fn = getattr(pack, "file_hashes", None)
  raw_fh = fh_fn() if callable(fh_fn) else None
  pack_fh = dict(raw_fh) if isinstance(raw_fh, dict) else None
  rec = schema.RolloutRecord(
      run_id=run_id,
      config_hash=config_hash,
      framework=pack.key,
      framework_visibility=pack.visibility,
      scenario_id=scenario.id,
      set=scenario.set,
      pillar=scenario.pillar,
      seed=seed,
      model=model,
      pack_sha256=schema.pack_sha256_from_hashes(pack_fh),
      pack_file_hashes=pack_fh,
  )
  sbx: Optional[sandbox_lib.Sandbox] = None
  try:
    if client is None:
      client = gemini_client.GeminiClient()
    project_context = (scenario.fixture or {}).get("project_context") or {}
    sbx = sandbox_lib.Sandbox(
        rollout_dir(sandbox_root, run_id, pack.key, model, scenario.id, seed),
        scenario,
        pack_files=pack.sandbox_files(),
        context_files=pack.render_context(project_context),
        pack_commands=getattr(pack, "pack_commands", None) or [],
    )
    system = pack.system_prompt(BASE_PROMPT)
    for s_idx, session in enumerate(scenario.sessions):
      srec = schema.SessionRecord(turns=[])
      rec.sessions.append(srec)
      _run_session(client, model, seed, system, pack, scenario, sbx, s_idx,
                   session, srec, rec)
    rec.action_log = sbx.action_log
    rec.file_events = sbx.file_events
    rec.final_diff, rec.sqlite_rowcounts = sbx.finalize()
  except gemini_client.HarnessError as e:
    rec.status = "harness_error"
    rec.error = f"HarnessError: {e}"
  except sandbox_lib.SandboxError as e:
    rec.status = "harness_error"
    rec.error = f"SandboxError: {e}"
  except Exception as e:  # pylint: disable=broad-except
    rec.status = "harness_error"
    rec.error = (f"unexpected {type(e).__name__}: {e}\n"
                 + traceback.format_exc(limit=8))
  finally:
    if sbx is not None:
      if rec.status != "ok":
        rec.action_log = sbx.action_log
        rec.file_events = sbx.file_events
      if not keep_sandbox and rec.status == "ok":
        sbx.cleanup()
  return rec


def _run_session(
    client: gemini_client.GeminiClient,
    model: str,
    seed: int,
    system: str,
    pack: FrameworkPackLike,
    scenario: schema.Scenario,
    sbx: sandbox_lib.Sandbox,
    s_idx: int,
    session: Dict[str, Any],
    srec: schema.SessionRecord,
    rec: schema.RolloutRecord,
) -> None:
  contents: List[Dict[str, Any]] = []  # Fresh conversation per session.
  pending_ask: Optional[Dict[str, Any]] = None  # Unanswered ask_user call.
  for t_idx, raw in enumerate(session["turns"]):
    # A session's first message is expanded like a host slash command. Session
    # 0 uses its own `intent` or the scenario intent (which describes S0T0).
    # Later sessions are expanded only when they set `intent` (a user opening a
    # fresh session types e.g. the resume command); otherwise plain text.
    intent = session.get("intent") or (scenario.intent if s_idx == 0 else None)
    if t_idx == 0 and intent:
      user_msg = pack.expand_user_message(intent, raw)
    else:
      user_msg = raw
    if pending_ask is not None:
      _append_user_parts(contents, [_response_part(pending_ask, user_msg)])
      pending_ask = None
    else:
      _append_user_parts(contents, [{"text": user_msg}])

    turn = schema.TurnRecord(user=user_msg, user_raw=raw, assistant_text="",
                             tool_calls=[], steps=0, finish_reasons=[],
                             ended_by="max_steps", usage=schema.Usage())
    srec.turns.append(turn)
    texts: List[str] = []
    overflow = False
    for step in range(MAX_STEPS_PER_TURN):
      sbx.set_position(s_idx, t_idx, step)
      try:
        resp = client.generate(
            model, contents, system_instruction=system,
            tools=TOOL_DECLARATIONS, temperature=TEMPERATURE, seed=seed,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
      except gemini_client.ContextOverflowError:
        # Scored, not excluded: the framework's prompts plus transcript no
        # longer fit. The session cannot continue.
        turn.ended_by = "context_overflow"
        turn.finish_reasons.append("CONTEXT_OVERFLOW")
        overflow = True
        break
      turn.steps += 1
      turn.finish_reasons.extend(f"retried:{r}"
                                 for r in resp.retried_finish_reasons)
      turn.finish_reasons.append(resp.finish_reason or "UNSPECIFIED")
      usage = dataclasses.replace(resp.usage, api_calls=resp.attempts)
      turn.usage.add(usage)
      rec.usage.add(usage)
      retry_usage = getattr(rec, "retry_usage", None)
      if retry_usage is not None and resp.retry_usage is not None:
        retry_usage.add(dataclasses.replace(resp.retry_usage, api_calls=0))
      contents.append(resp.content)  # Verbatim, keeps thought signatures.
      if resp.text:
        texts.append(resp.text)
      if not resp.function_calls:
        turn.ended_by = "text"
        break
      parts: List[Dict[str, Any]] = []
      ask_call: Optional[Dict[str, Any]] = None
      for call in resp.function_calls:
        name = call.get("name", "")
        args = call.get("args") or {}
        if name == "ask_user":
          if ask_call is None:
            ask_call = call
            question = sbx.call_tool("ask_user", args)
            turn.tool_calls.append(schema.ToolCall(
                name=name, args=args, result_preview=""))
            if question and not resp.text:
              texts.append(question)
            continue
          output = "ERROR: only one ask_user call per step is allowed"
        else:
          output = sbx.call_tool(name, args)
        turn.tool_calls.append(schema.ToolCall(
            name=name, args=args, result_preview=output[:RESULT_PREVIEW_CHARS]))
        parts.append(_response_part(call, output))
      if ask_call is not None:
        if parts:
          _append_user_parts(contents, parts)
        pending_ask = ask_call
        turn.ended_by = "ask_user"
        break
      _append_user_parts(contents, parts)
    if turn.ended_by == "max_steps" and not overflow and WRAP_UP_AT_MAX_STEPS:
      overflow = _wrap_up(client, model, seed, system, contents, turn, rec,
                          texts, sbx)
    turn.assistant_text = "\n\n".join(texts)
    if overflow:
      return


def _wrap_up(client: gemini_client.GeminiClient, model: str, seed: int,
             system: str, contents: List[Dict[str, Any]],
             turn: schema.TurnRecord, rec: schema.RolloutRecord,
             texts: List[str], sbx: sandbox_lib.Sandbox) -> bool:
  """At the step limit, asks the model for a final text reply.

  Gemini 3 ignores `functionCallingConfig.mode=NONE` (it still emits function
  calls, and after refusals NONE often yields an empty candidate), so the
  harness keeps the normal tool config, sends a neutral nudge, and answers any
  further tool call with an error instead of executing it, up to
  WRAP_UP_MAX_CALLS times. Refused calls are logged (executed=False). The turn
  keeps ended_by="max_steps"; finish reasons are tagged "WRAP_UP:". A failure
  here never turns the rollout into a harness error. Returns True on context
  overflow.
  """
  _append_user_parts(contents, [{"text": WRAP_UP_MESSAGE}])
  for _ in range(WRAP_UP_MAX_CALLS):
    try:
      resp = client.generate(
          model, contents, system_instruction=system,
          tools=TOOL_DECLARATIONS, temperature=TEMPERATURE, seed=seed,
          max_output_tokens=MAX_OUTPUT_TOKENS,
      )
    except gemini_client.ContextOverflowError:
      turn.finish_reasons.append("WRAP_UP:CONTEXT_OVERFLOW")
      turn.ended_by = "context_overflow"
      return True
    except gemini_client.HarnessError as e:
      turn.finish_reasons.append(f"WRAP_UP:FAILED:{str(e)[:120]}")
      return False
    turn.steps += 1
    turn.finish_reasons.extend(f"retried:{r}"
                               for r in resp.retried_finish_reasons)
    turn.finish_reasons.append(
        f"WRAP_UP:{resp.finish_reason or 'UNSPECIFIED'}")
    usage = dataclasses.replace(resp.usage, api_calls=resp.attempts)
    turn.usage.add(usage)
    rec.usage.add(usage)
    retry_usage = getattr(rec, "retry_usage", None)
    if retry_usage is not None and resp.retry_usage is not None:
      retry_usage.add(dataclasses.replace(resp.retry_usage, api_calls=0))
    contents.append(resp.content)
    if resp.text.strip():
      texts.append(resp.text)
    if not resp.function_calls:
      return False
    parts = []
    for call in resp.function_calls:
      name = call.get("name", "")
      args = call.get("args") or {}
      if name in schema.TOOL_NAMES:
        sbx.log_refused(name, args, WRAP_UP_REFUSAL)
      turn.tool_calls.append(schema.ToolCall(
          name=name, args=args, result_preview=f"ERROR: {WRAP_UP_REFUSAL}"))
      parts.append(_response_part(call, f"ERROR: {WRAP_UP_REFUSAL}"))
    _append_user_parts(contents, parts)
  turn.finish_reasons.append("WRAP_UP:NO_TEXT")
  return False


def rollout_summary(rec: schema.RolloutRecord) -> str:
  u = rec.usage
  return json.dumps({
      "framework": rec.framework, "scenario": rec.scenario_id,
      "model": rec.model, "seed": rec.seed, "status": rec.status,
      "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
      "thinking_tokens": u.thinking_tokens, "cached_tokens": u.cached_tokens,
      "api_calls": u.api_calls, "latency_s": round(u.latency_s, 2),
      "turns": [[t.ended_by for t in s.turns] for s in rec.sessions],
      "actions": len(rec.action_log), "file_events": len(rec.file_events),
      "error": rec.error,
  })
