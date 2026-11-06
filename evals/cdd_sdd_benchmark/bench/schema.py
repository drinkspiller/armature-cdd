"""Shared data contracts for the CDD/SDD benchmark v2.

Every module in `bench/` exchanges these structures. Records are serialized as
plain JSON dicts (via `dataclasses.asdict`) so result files stay readable
without this package. See DESIGN.md for field semantics.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any, Dict, List, Optional

PILLARS = (
    "spec_gating",
    "surgical_velocity",
    "drift_governance",
    "state_safety",
    "context_continuity",
)
INTENTS = (
    "feature_plan",
    "hotfix",
    "drift_audit",
    "ops_request",
    "review",
    "resume",
)
SETS = ("core", "heldout")
CHECK_TYPES = (
    "no_destructive_exec",
    "no_source_change",
    "source_changed",
    "diff_scope",
    "file_matches",
    "planning_artifact_written",
    "no_planning_artifact",
    "asked_user",
    "command_attempted",
    "command_not_attempted",
    "sqlite_unchanged",
    "output_tokens_max",
    "text_mentions",
)
TOOL_NAMES = (
    "list_dir",
    "read_file",
    "write_file",
    "edit_file",
    "run_command",
    "ask_user",
)

# Vocabulary that must not appear in user turns or judge criteria because it
# belongs to one framework's dialect. Checked by `validate_scenario`.
FORBIDDEN_SCENARIO_TERMS = (
    "armature",
    "conductor",
    "spec kit",
    "speckit",
    "openspec",
    "bmad",
    "memory bank",
    "memory-bank",
    "internal_sdd",
    "wayfinder",
    "/arm-",
    "terms.md",
    "spec.md",
    "plan.md",
    "track",
    "ubiquitous",
    "living runbook",
    "api surface cache",
    "api_surface_cache",
    "phase checkpoint",
    "settled",
    "up next",
    "constitution",
    "prd",
    "epic",
)


@dataclasses.dataclass
class Check:
  id: str
  type: str
  args: Dict[str, Any]
  description: str


@dataclasses.dataclass
class Scenario:
  id: str
  set: str
  pillar: str
  intent: str
  description: str
  fixture: Dict[str, Any]
  mocks: List[Dict[str, Any]]
  sessions: List[Dict[str, Any]]
  checks: List[Check]
  judge_criteria: List[str]

  @staticmethod
  def from_dict(d: Dict[str, Any]) -> "Scenario":
    return Scenario(
        id=d["id"],
        set=d["set"],
        pillar=d["pillar"],
        intent=d["intent"],
        description=d["description"],
        fixture=d.get("fixture", {}),
        mocks=d.get("mocks", []),
        sessions=d["sessions"],
        checks=[Check(**c) for c in d["checks"]],
        judge_criteria=d.get("judge_criteria", []),
    )


@dataclasses.dataclass
class Usage:
  input_tokens: int = 0
  output_tokens: int = 0  # candidatesTokenCount: visible output only.
  thinking_tokens: int = 0  # thoughtsTokenCount.
  cached_tokens: int = 0
  api_calls: int = 0
  latency_s: float = 0.0

  def add(self, other: "Usage") -> None:
    self.input_tokens += other.input_tokens
    self.output_tokens += other.output_tokens
    self.thinking_tokens += other.thinking_tokens
    self.cached_tokens += other.cached_tokens
    self.api_calls += other.api_calls
    self.latency_s += other.latency_s


@dataclasses.dataclass
class ToolCall:
  name: str
  args: Dict[str, Any]
  result_preview: str  # First 2,000 chars of the tool result.


@dataclasses.dataclass
class TurnRecord:
  user: str  # The message as the model received it (after command expansion).
  user_raw: str  # The scenario's original text.
  assistant_text: str  # Concatenated visible text across all steps.
  tool_calls: List[ToolCall]
  steps: int
  finish_reasons: List[str]
  ended_by: str  # "text", "ask_user", or "max_steps".
  usage: Usage


@dataclasses.dataclass
class SessionRecord:
  turns: List[TurnRecord]


@dataclasses.dataclass
class Action:
  session: int
  turn: int
  step: int
  type: str  # One of TOOL_NAMES.
  path: Optional[str] = None
  command: Optional[str] = None
  executed: bool = False
  mock_id: Optional[str] = None
  destructive: bool = False
  rows_changed: Optional[Dict[str, int]] = None  # table -> delta, sqlite only.
  error: Optional[str] = None
  # How run_command was resolved: "mock", "pack_tool", "builtin", "refused".
  source: Optional[str] = None


@dataclasses.dataclass
class FileEvent:
  session: int
  turn: int
  path: str
  op: str  # "create", "modify", or "delete".


@dataclasses.dataclass
class CheckResult:
  id: str
  type: str
  passed: bool
  detail: str


@dataclasses.dataclass
class JudgeResult:
  criterion: str
  votes: Dict[str, Optional[bool]]  # judge model -> verdict (None = invalid).
  reasons: Dict[str, str]
  score: Optional[float]  # Mean of valid votes; None if < 2 valid votes.


@dataclasses.dataclass
class RolloutRecord:
  run_id: str
  config_hash: str
  framework: str
  framework_visibility: str  # "public" or "internal".
  scenario_id: str
  set: str
  pillar: str
  seed: int
  model: str
  status: str = "ok"  # "ok" or "harness_error".
  error: Optional[str] = None
  sessions: List[SessionRecord] = dataclasses.field(default_factory=list)
  action_log: List[Action] = dataclasses.field(default_factory=list)
  file_events: List[FileEvent] = dataclasses.field(default_factory=list)
  final_diff: Dict[str, Any] = dataclasses.field(default_factory=dict)
  # final_diff = {"files": {path: {"status": str, "added": int,
  #               "removed": int}}, "patch": str}
  sqlite_rowcounts: Dict[str, Dict[str, Dict[str, int]]] = dataclasses.field(
      default_factory=dict
  )
  # sqlite_rowcounts = {db_path: {"baseline": {table: n}, "final": {table: n}}}
  usage: Usage = dataclasses.field(default_factory=Usage)
  retry_usage: Usage = dataclasses.field(default_factory=Usage)
  checks: List[CheckResult] = dataclasses.field(default_factory=list)
  judge: List[JudgeResult] = dataclasses.field(default_factory=list)
  pack_digest: str = ""
  pack_sha256: Optional[str] = None
  pack_file_hashes: Optional[Dict[str, str]] = None

  def to_json(self) -> str:
    return json.dumps(dataclasses.asdict(self), ensure_ascii=False)

  @staticmethod
  def from_dict(d: Dict[str, Any]) -> "RolloutRecord":
    r = RolloutRecord(
        **{
            k: v
            for k, v in d.items()
            if k
            not in (
                "sessions",
                "action_log",
                "file_events",
                "usage",
                "checks",
                "judge",
            )
        }
    )
    r.sessions = [
        SessionRecord(
            turns=[
                TurnRecord(
                    **{
                        **t,
                        "tool_calls": [ToolCall(**c) for c in t["tool_calls"]],
                        "usage": Usage(**t["usage"]),
                    }
                )
                for t in s["turns"]
            ]
        )
        for s in d.get("sessions", [])
    ]
    r.action_log = [Action(**a) for a in d.get("action_log", [])]
    r.file_events = [FileEvent(**e) for e in d.get("file_events", [])]
    r.usage = Usage(**d.get("usage", {}))
    r.retry_usage = Usage(**d.get("retry_usage", {}))
    r.checks = [CheckResult(**c) for c in d.get("checks", [])]
    r.judge = [JudgeResult(**j) for j in d.get("judge", [])]
    return r


def pack_sha256_from_hashes(
    file_hashes: Optional[Dict[str, str]],
) -> Optional[str]:
  """Deterministic SHA-256 over a pack's `{rel_path: sha256}` map."""
  if not isinstance(file_hashes, dict):
    return None
  return hashlib.sha256(
      json.dumps(file_hashes, sort_keys=True).encode("utf-8")
  ).hexdigest()


def validate_scenario(d: Dict[str, Any]) -> List[str]:
  """Returns a list of human-readable schema/neutrality errors (empty = ok)."""
  errs: List[str] = []
  sid = d.get("id", "<missing id>")
  for key in ("id", "set", "pillar", "intent", "description", "sessions",
              "checks"):
    if key not in d:
      errs.append(f"{sid}: missing '{key}'")
  if errs:
    return errs
  if d["set"] not in SETS:
    errs.append(f"{sid}: bad set {d['set']}")
  if d["pillar"] not in PILLARS:
    errs.append(f"{sid}: bad pillar {d['pillar']}")
  if d["intent"] not in INTENTS:
    errs.append(f"{sid}: bad intent {d['intent']}")
  if not d["sessions"] or not all(s.get("turns") for s in d["sessions"]):
    errs.append(f"{sid}: every session needs at least one turn")
  for si, sess in enumerate(d.get("sessions", [])):
    sess_intent = sess.get("intent")
    if sess_intent is not None and sess_intent not in INTENTS:
      errs.append(f"{sid}: session[{si}] bad intent {sess_intent}")
  checks = d.get("checks", [])
  if len(checks) < 2:
    errs.append(f"{sid}: needs >= 2 deterministic checks")
  if all(c.get("type") == "text_mentions" for c in checks):
    errs.append(f"{sid}: text_mentions cannot be the only check type")
  for c in checks:
    if c.get("type") not in CHECK_TYPES:
      errs.append(f"{sid}: unknown check type {c.get('type')}")
    for k in ("id", "type", "args", "description"):
      if k not in c:
        errs.append(f"{sid}: check missing '{k}'")
  if len(d.get("judge_criteria", [])) > 3:
    errs.append(f"{sid}: at most 3 judge criteria")
  mock_ids = set()
  for m in d.get("mocks", []):
    for k in ("id", "match", "stdout", "exit_code", "destructive"):
      if k not in m:
        errs.append(f"{sid}: mock missing '{k}'")
    mock_ids.add(m.get("id"))
  neutral_texts = [t for s in d["sessions"] for t in s["turns"]]
  neutral_texts += d.get("judge_criteria", [])
  for text in neutral_texts:
    low = text.lower()
    for term in FORBIDDEN_SCENARIO_TERMS:
      # Whole-word match for short alphabetic terms to avoid false hits.
      if term.isalpha() and len(term) <= 6:
        import re  # pylint: disable=g-import-not-at-top

        if re.search(rf"\b{re.escape(term)}\b", low):
          errs.append(f"{sid}: framework-specific term '{term}' in: {text[:80]}")
      elif term in low:
        errs.append(f"{sid}: framework-specific term '{term}' in: {text[:80]}")
  return errs


def load_scenarios(path: str) -> List[Scenario]:
  out: List[Scenario] = []
  with open(path, "r", encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if line:
        out.append(Scenario.from_dict(json.loads(line)))
  return out
