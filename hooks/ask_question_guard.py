#!/usr/bin/env python3
"""PreToolUse + Stop guard for `ask_question` delivery (ADR 0022).

Two enforcement hooks share this script:

1. `PreToolUse` (matcher `ask_question`): blocks `ask_question` calls whose step
   has fewer than MIN_WORDS visible words (preventing bare question boxes when
   the model wrote its explanation into `thinking`). First denial requests a
   retry with visible text; second+ denial switches that question to Plain-Text
   Question Mode. Stops denying after MAX_DENIALS.

2. `Stop`: blocks a turn from ending with `tool_calls: []` when the final
   response clearly presented options (`> **Option N:`, `### Recommendation:`,
   `- Pick N if`, numbered choices + decision prompt) or ended waiting on a
   user action without calling `ask_question` (unless Plain-Text Question Mode
   is active, `continuationActive` is already true, or the turn errored /
   was cancelled).

Fails open on any read or parse error so the agent can never get wedged.
"""

import json
import os
import re
import sys

MIN_WORDS = 25
MAX_DENIALS = 4
MARKER = "[armature-ask-guard]"
STOP_MARKER = "[armature-ask-stop-guard]"

RETRY_REASON = (
    f"{MARKER} Blocked: the step that called ask_question had {{words}} words"
    " of visible text. Text in thinking is never shown, so the user would see a"
    " bare question box. In your next step, write the full turn as visible text"
    " first (the # <Topic> H1 heading, short orientation, concise blockquote"
    " option cards with Pros/Cons/Implications, recommendation, and - Pick N if"
    " lines, or the follow-up # <Topic> H1 explanation), then call"
    " ask_question again with the same options in that same step."
)
PLAIN_REASON = (
    f"{MARKER} Blocked again: the retry also had {{words}} words of visible"
    " text. Switch to Plain-Text Question Mode for this question: reply with"
    " the full turn as visible text (the # <Topic> H1 heading, orientation,"
    " concise blockquote option cards with Pros/Cons/Implications,"
    " recommendation, and - Pick N if lines) and end with 'Reply with 1, 2,"
    " or 3.' Don't call ask_question or any other tool in that reply. Use the"
    " box again for later questions."
)
STOP_CONTINUE_REASON = (
    f"{STOP_MARKER} Blocked turn end: your previous message already showed the"
    " options in chat, so do NOT repeat the heading, explanation, or option"
    " list in text. Emit zero prose and call the ask_question tool immediately"
    " with the matching options."
)
STOP_CONTINUE_SHORT_REASON = (
    f"{STOP_MARKER} Blocked turn end: your reply ended waiting on the user"
    " without calling ask_question. Write a short plain-prose paragraph"
    " (>= 25 visible words, no bulleted option list) explaining the options"
    " and call ask_question immediately."
)

_FENCED_CODE_RE = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_BLOCKQUOTE_LINE_RE = re.compile(r"^\s*>.*$", re.M)
_ARMATURE_TAIL_PATTERNS = (
    re.compile(r"^###\s+Recommendation:\s+Option\s+\d+", re.M),
    re.compile(r"^\s*(?:[-*]\s+)*(?:\*\*)?Pick\s+\d+(?:\*\*)?\s+if\b", re.M),
    re.compile(r"^\s*Safe to ignore for now:", re.M),
)
_ARMATURE_CARD_PATTERNS = (
    re.compile(r"^>\s*\*\*Option\s+\d+\s*:", re.M),
    re.compile(r"\bHere are some options:"),
)
_NUMBERED_LINE_RE = re.compile(r"^\s*[1-4]\.\s+\S", re.M)
_NUMBERED_CHOICE_PROMPT_RE = re.compile(
    r"(?:\bOption\s+[1-4]\b"
    r"|\bwhich\s+(?:one|option|approach|path|style)\b"
    r"|\b(?:do\s+you|would\s+you)\s+(?:prefer|choose|want)\b"
    r"|\b(?:please\s+)?choose\s+"
    r"(?:one|an\s+option|your\s+(?:option|approach|preference))\b"
    r"|\breply\s+with\b|\bpick\s+(?:one|[1-4])\b"
    r"|would\s+you\s+like\s+me\s+to"
    r"|\bhow\s+(?:would\s+you\s+like|should\s+(?:we|i))\s+(?:to\s+)?proceed)",
    re.I,
)
_CONFIRM_BEFORE_PROCEED_RE = re.compile(
    r"(?:(?:worth\s+confirming|things?\s+to\s+(?:confirm|clarify)|"
    r"questions?(?:\s+to\s+(?:confirm|clarify))?|"
    r"confirm(?:ing)?|clarify(?:ing)?)\s+"
    r"before\s+(?:(?:you|we|i)\s+(?:proceed|continue|start|rename|apply|edit)"
    r"|proceeding)\s*:"
    r"|before\s+(?:you|we|i)\s+(?:proceed|continue)\s*,\s*"
    r"(?:a\s+few\s+)?(?:things?|questions?)\s+"
    r"(?:to\s+|worth\s+)?(?:confirm|clarify)\w*\s*:)",
    re.I,
)
_WAITING_TURN_TAIL_RE = re.compile(
    r"(?:(?:tell|ping)\s+me\s+(?:when|once)\b"
    r"|let\s+me\s+know\s+(?:when|once|which|whether)\b"
    r"|let\s+me\s+know\s+(?:how|what)\s+"
    r"(?:you(?:'d|\s+would)\s+like|should\s+(?:we|i)|we\s+should|to\s+(?:do|proceed))"
    r"|let\s+me\s+know\s+if\s+(?:you(?:'d|\s+would)\s+like\s+me\s+to"
    r"|i\s+should|we\s+should)\s+"
    r"(?:proceed|continue|run|start|apply|upload|submit|merge|fix|delete|create|wait)"
    r"|once\s+(?:it(?:'s| is)|that(?:'s| is)|you(?:'ve| have)"
    r"|the\s+\S+\s+is)\s+"
    r"(?:up|back|ready|done|restarted)[^.\n]{0,80}"
    r"(?:\b(?:let\s+me\s+know|tell\s+me|ping\s+me)\b"
    r"|\b(?:please\s+)?(?:reply|respond)\s+(?:here|back|when|to\s+this)\b"
    r"|\b(?:please|just)\s+(?:reply|respond|say)\b"
    r"|\bsay\s+(?:when|go|ready|the\s+word)\b"
    r"|i(?:'ll|\s+(?:can|will))\s+(?:continue|proceed|resume|re-?run))"
    r"|please\s+restart\b.*\band\s+(?:tell|let)"
    r"|how\s+(?:would\s+you\s+like|should\s+(?:we|i))\s+(?:to\s+)?proceed\b"
    r"|which\s+(?:option|approach|one)\s+(?:should|would|do\s+you)"
    r"|which\s+of\s+(?:these|those)\b[^.\n]*\?"
    r"|(?:(?:do\s+you\s+)?want\s+(?:me\s+)?to|(?:shall|should)\s+(?:we|i))\s+"
    r"(?:go\s+with|proceed|continue|run|start|tackle|apply|rename|delete"
    r"|upload|wait|prepare|fix|submit|merge|use)\b[^.\n]*\?"
    r"|would\s+you\s+like\s+me\s+to\s+"
    r"(?:proceed|continue|run|delete|upload|apply|create|submit|wait|fix|merge)"
    r"|(?:reply|respond)\s+with\s+1\b)",
    re.I,
)
_PLAIN_MODE_USER_RE = re.compile(
    r"(?:stop\s+using\s+the\s+(?:question\s+)?box"
    r"|(?:don'?t|do\s+not|never)\s+use\s+the\s+(?:question\s+)?box"
    r"|just\s+ask\s+(?:me\s+)?in\s+chat"
    r"|(?:switch\s+to|use|enable)\s+plain[- ]text\s+question\s+mode"
    r"|ask\s+(?:me\s+)?without\s+(?:the\s+)?(?:question\s+)?box"
    r"|skip\s+the\s+(?:question\s+)?box)",
    re.I,
)
_BOX_REENABLE_USER_RE = re.compile(
    r"(?:use\s+the\s+(?:question\s+)?box\s+again"
    r"|(?:switch|go)\s+back\s+to\s+(?:the\s+)?(?:question\s+)?box"
    r"|re-?enable\s+(?:the\s+)?(?:question\s+)?box"
    r"|turn\s+(?:the\s+)?(?:question\s+)?box\s+back\s+on)",
    re.I,
)


def allow():
  """Emits a PreToolUse allow decision."""
  print(json.dumps({"decision": "allow"}))


def stop_allow():
  """Emits a Stop hook allow-stop decision."""
  print(json.dumps({"decision": "stop"}))


def load_steps(path):
  """Loads parsed JSONL steps, preferring untruncated `transcript_full.jsonl`."""
  if not path:
    return []
  full_path = os.path.join(os.path.dirname(path), "transcript_full.jsonl")
  target = full_path if os.path.exists(full_path) else path
  steps = []
  with open(target, encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if line:
        try:
          steps.append(json.loads(line))
        except json.JSONDecodeError:
          pass
  return steps


def _is_stop_continuation_step(step):
  """True when `step` is a real Stop-hook continuation prompt, not user prose."""
  step_type = step.get("type")
  content = str(step.get("content") or "")
  if step_type == "SYSTEM_MESSAGE":
    return STOP_MARKER in content or STOP_MARKER in str(step.get("error") or "")
  if step_type == "USER_INPUT":
    if STOP_MARKER not in content:
      return False
    source = step.get("source")
    return source in ("SYSTEM", "SYSTEM_SDK") or (
        not source and content.lstrip().startswith(STOP_MARKER)
    )
  return False


def current_turn(steps):
  """Returns steps after the last non-guard USER_INPUT."""
  for i in range(len(steps) - 1, -1, -1):
    if steps[i].get("type") == "USER_INPUT":
      if _is_stop_continuation_step(steps[i]):
        continue
      return steps[i + 1 :]
  return steps


def _is_ask_step(step):
  """True when `step` is a PLANNER_RESPONSE invoking `ask_question`."""
  if step.get("type") != "PLANNER_RESPONSE":
    return False
  return any(
      c.get("name") == "ask_question" for c in step.get("tool_calls") or []
  )


def _ask_was_denied(turn, idx):
  """True when the `ask_question` call at `turn[idx]` failed or was denied."""
  step = turn[idx]
  if step.get("status") == "ERROR":
    return True
  single_call = len(step.get("tool_calls") or []) == 1
  saw_error = False
  for s in turn[idx + 1 :]:
    stype = s.get("type")
    if stype in ("PLANNER_RESPONSE", "USER_INPUT"):
      break
    if stype == "ASK_QUESTION" and s.get("status") == "DONE":
      return False
    if s.get("status") == "ERROR":
      err = str(s.get("error") or "")
      if (
          MARKER in err
          or stype == "ASK_QUESTION"
          or single_call
          or (
              stype in ("GENERIC", "ERROR_MESSAGE", None, "")
              and "ask_question" in err.lower()
          )
      ):
        saw_error = True
  return saw_error


def current_question_round(turn, active_ask_step=None):
  """Returns steps after the last completed (non-denied) `ask_question`."""
  for i in range(len(turn) - 1, -1, -1):
    if turn[i] is active_ask_step:
      continue
    if _is_ask_step(turn[i]) and not _ask_was_denied(turn, i):
      return turn[i + 1 :]
  return turn


def asking_step(turn):
  """Returns the latest planner step that calls ask_question."""
  for s in reversed(turn):
    if _is_ask_step(s):
      return s
  return None


def last_planner_step(turn):
  """Returns the latest PLANNER_RESPONSE step in `turn`, or None."""
  for s in reversed(turn):
    if s.get("type") == "PLANNER_RESPONSE":
      return s
  return None


_ASK_ANSWER_BLOCK_RE = re.compile(
    r"^A\d+:\s*(.*?)(?=^(?:[QA]\d+:|Created At:|Completed At:)|\Z)",
    re.M | re.S,
)
_ASK_QUESTION_LINE_RE = re.compile(r"^Q\d+:", re.M)


def _extract_ask_answers(raw, allow_unstructured=False):
  """Extracts user answer text (`A1:`, multi-line) while ignoring `Q1:` text."""
  answers = [m.strip() for m in _ASK_ANSWER_BLOCK_RE.findall(raw) if m.strip()]
  if answers:
    return "\n".join(answers)
  if allow_unstructured and not _ASK_QUESTION_LINE_RE.search(raw):
    return raw
  return ""


def user_requested_plain_mode(steps):
  """True when user requested plain-text questions and has not re-enabled box."""
  plain_mode = False
  awaiting_ask_answer = False
  for s in steps:
    step_type = s.get("type")
    if step_type == "PLANNER_RESPONSE":
      awaiting_ask_answer = _is_ask_step(s)
      continue
    if step_type == "USER_INPUT":
      awaiting_ask_answer = False
      if _is_stop_continuation_step(s):
        continue
      raw = str(s.get("content") or "")
    elif step_type == "ASK_QUESTION" and s.get("status") == "DONE":
      raw = _extract_ask_answers(
          str(s.get("content") or ""), allow_unstructured=True
      )
      if not raw:
        continue
    elif (
        awaiting_ask_answer
        and step_type == "GENERIC"
        and s.get("status") == "DONE"
    ):
      raw = _extract_ask_answers(
          str(s.get("content") or ""), allow_unstructured=False
      )
      if not raw:
        continue
    else:
      continue
    cleaned = _INLINE_CODE_RE.sub(
        "", _BLOCKQUOTE_LINE_RE.sub("", _FENCED_CODE_RE.sub("", raw))
    )
    plain_matches = list(_PLAIN_MODE_USER_RE.finditer(cleaned))
    reenable_matches = [
        m
        for m in _BOX_REENABLE_USER_RE.finditer(cleaned)
        if not any(
            pm.start() < m.end() and m.start() < pm.end()
            for pm in plain_matches
        )
    ]
    last_plain = plain_matches[-1].end() if plain_matches else -1
    last_reenable = reenable_matches[-1].end() if reenable_matches else -1
    if last_plain > last_reenable:
      plain_mode = True
    elif last_reenable > last_plain:
      plain_mode = False
  return plain_mode


def looks_like_dropped_ask_question(text):
  """True when `text` ends waiting on a choice/action without `ask_question`."""
  cleaned = _FENCED_CODE_RE.sub("", text or "").strip()
  if not cleaned:
    return False
  tail = cleaned[-900:]
  for pat in _ARMATURE_TAIL_PATTERNS:
    if pat.search(tail):
      return True
  card_window = cleaned[-1400:]
  for pat in _ARMATURE_CARD_PATTERNS:
    if pat.search(card_window):
      return True
  if len(
      _NUMBERED_LINE_RE.findall(card_window)
  ) >= 2 and _NUMBERED_CHOICE_PROMPT_RE.search(tail):
    return True
  m_confirm = _CONFIRM_BEFORE_PROCEED_RE.search(tail)
  if m_confirm and re.search(
      r"(?:^\s*[-*]\s+\S|\?)", tail[m_confirm.end() :], re.M
  ):
    return True
  paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
  last_para = paragraphs[-1] if paragraphs else cleaned[-400:]
  return bool(_WAITING_TURN_TAIL_RE.search(last_para))


def _prior_stopped_decision_words(round_steps, ask_step):
  """Counts visible words from a Stop-continued text-only step before ask_step."""
  has_stop_marker = any(_is_stop_continuation_step(s) for s in round_steps)
  if not has_stop_marker:
    return 0
  prior_words = 0
  for s in round_steps:
    if s is ask_step:
      break
    if s.get("type") != "PLANNER_RESPONSE" or s.get("tool_calls"):
      continue
    text = s.get("content") or ""
    if looks_like_dropped_ask_question(text):
      prior_words += len(text.split())
  return prior_words


def _extract_transcript_path(payload):
  """Resolves transcriptPath from top-level or nested `common` payload."""
  common = payload.get("common")
  common_map = common if isinstance(common, dict) else {}
  return payload.get("transcriptPath") or common_map.get("transcriptPath") or ""


def handle_pre_tool(payload):
  """Handles `PreToolUse` on `ask_question` to block blank boxes."""
  if (payload.get("toolCall") or {}).get("name") != "ask_question":
    return allow()
  path = _extract_transcript_path(payload)
  try:
    turn = current_turn(load_steps(path))
  except OSError:
    return allow()
  step = asking_step(turn)
  if step is None or "content" in (step.get("truncated_fields") or []):
    return allow()
  round_steps = current_question_round(turn, active_ask_step=step)
  words = len((step.get("content") or "").split())
  words += _prior_stopped_decision_words(round_steps, step)
  if words >= MIN_WORDS:
    return allow()
  denials = sum(
      1
      for s in round_steps
      if s.get("status") == "ERROR" and MARKER in str(s.get("error") or "")
  )
  if denials >= MAX_DENIALS:
    return allow()
  reason = RETRY_REASON if denials == 0 else PLAIN_REASON
  print(json.dumps({"decision": "deny", "reason": reason.format(words=words)}))


def handle_stop(payload):
  """Handles `Stop` to catch dropped `ask_question` turns."""
  stop_args = payload.get("stopHookArgs")
  stop_map = stop_args if isinstance(stop_args, dict) else {}
  err = payload.get("error") or stop_map.get("error") or ""
  if str(err).strip():
    return stop_allow()
  term = str(
      payload.get("terminationReason")
      or stop_map.get("terminationReason")
      or ""
  ).lower()
  if any(
      tok in term
      for tok in ("cancel", "max_", "budget", "timeout", "abort", "error")
  ):
    return stop_allow()
  fully_idle = (
      payload.get("fullyIdle")
      if "fullyIdle" in payload
      else stop_map.get("fullyIdle")
  )
  if isinstance(fully_idle, bool) and not fully_idle:
    return stop_allow()
  cont_active = (
      payload.get("continuationActive")
      if "continuationActive" in payload
      else stop_map.get("continuationActive")
  )
  raw_exec_num = (
      payload.get("executionNum")
      if "executionNum" in payload
      else stop_map.get("executionNum", 0)
  )
  try:
    exec_num = int(raw_exec_num or 0)
  except (TypeError, ValueError):
    exec_num = 0
  path = _extract_transcript_path(payload)
  try:
    steps = load_steps(path)
  except OSError:
    return stop_allow()
  if not steps:
    return stop_allow()
  if user_requested_plain_mode(steps):
    return stop_allow()
  turn = current_turn(steps)
  round_steps = current_question_round(turn)
  round_continued = any(
      _is_stop_continuation_step(s) for s in round_steps
  )
  if round_continued:
    return stop_allow()
  has_prior_round = len(round_steps) < len(turn)
  if not has_prior_round and (cont_active or exec_num >= 1):
    return stop_allow()
  if has_prior_round:
    prior_dropped = sum(
        1
        for s in round_steps
        if s.get("type") == "PLANNER_RESPONSE"
        and not s.get("tool_calls")
        and looks_like_dropped_ask_question(s.get("content") or "")
    )
    if prior_dropped >= 2:
      return stop_allow()
  # If PreToolUse already switched this question to Plain-Text Question Mode,
  # allow the plain-text reply to stop normally.
  guard_denials = sum(
      1
      for s in round_steps
      if s.get("status") == "ERROR" and MARKER in str(s.get("error") or "")
  )
  if guard_denials >= 2:
    return stop_allow()
  step = last_planner_step(round_steps)
  if step is None:
    return stop_allow()
  if step.get("tool_calls"):
    return stop_allow()
  content = step.get("content") or ""
  if looks_like_dropped_ask_question(content):
    reason = (
        STOP_CONTINUE_REASON
        if len(content.split()) >= MIN_WORDS
        else STOP_CONTINUE_SHORT_REASON
    )
    print(json.dumps({"decision": "continue", "reason": reason}))
    return
  return stop_allow()


def _is_stop_event(payload):
  """True when `payload` represents a `Stop` hook invocation."""
  event = payload.get("hookEventName") or ""
  if event == "Stop":
    return True
  return "toolCall" not in payload and (
      "stopHookArgs" in payload
      or "terminationReason" in payload
      or "executionNum" in payload
  )


def _extract_workspace_paths(payload):
  """Returns active workspace paths and cwd from top-level or nested `common`."""
  common = payload.get("common")
  common_map = common if isinstance(common, dict) else {}
  raw_paths = (
      payload.get("workspacePaths")
      or common_map.get("workspacePaths")
      or []
  )
  paths = [p for p in raw_paths if isinstance(p, str) and p]
  cwd = payload.get("cwd") or common_map.get("cwd") or ""
  if isinstance(cwd, str) and cwd:
    paths.append(cwd)
  return paths


def _should_defer(payload, argv, is_stop=False):
  """True when a workspace-scoped hooks.json owns this guard for the event."""
  prefixes = []
  hooks_file = ""
  i = 0
  while i < len(argv):
    arg = argv[i]
    if arg == "--defer-when-workspace-prefix" and i + 1 < len(argv):
      prefixes.append(argv[i + 1])
      i += 2
    elif arg == "--defer-if-hooks-file" and i + 1 < len(argv):
      hooks_file = argv[i + 1]
      i += 2
    else:
      i += 1
  if not prefixes or not hooks_file or not os.path.exists(hooks_file):
    return False
  paths = _extract_workspace_paths(payload)
  prefix_tuple = tuple(prefixes)
  if not any(p.startswith(prefix_tuple) for p in paths):
    return False
  try:
    with open(hooks_file, encoding="utf-8") as f:
      data = json.load(f)
  except (OSError, json.JSONDecodeError):
    return False
  entry = (
      data.get("armature-ask-question-guard")
      if isinstance(data, dict)
      else None
  )
  event_key = "Stop" if is_stop else "PreToolUse"
  return (
      isinstance(entry, dict)
      and bool(entry.get("enabled", True))
      and bool(entry.get(event_key))
  )


def main():
  try:
    payload = json.load(sys.stdin)
  except json.JSONDecodeError:
    return allow()
  is_stop = _is_stop_event(payload)
  try:
    if _should_defer(payload, sys.argv[1:], is_stop=is_stop):
      return stop_allow() if is_stop else allow()
    if is_stop:
      return handle_stop(payload)
    return handle_pre_tool(payload)
  except Exception:  # pylint: disable=broad-except
    return stop_allow() if is_stop else allow()


if __name__ == "__main__":
  try:
    main()
  except Exception:  # pylint: disable=broad-except
    try:
      allow()
    except Exception:  # pylint: disable=broad-except
      pass
