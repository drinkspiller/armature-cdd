#!/usr/bin/env python3
"""PreToolUse guard: blocks `ask_question` calls whose step has no visible text.

Some models (seen with Claude Opus 5.5 Medium) write the
user-facing explanation into `thinking` and call `ask_question` with empty
visible text, usually after a tool step in the same turn. The user then sees a
bare question box. The agent host writes the asking step to the transcript before
`PreToolUse` runs, so this hook reads that step and denies the call when it has
fewer than MIN_WORDS visible words. The model gets the reason back and retries
with the explanation as visible text.

Fails open: any read or parse problem allows the call. The first denial asks
for a retry with visible text plus the box. Later denials switch that one
question to Plain-Text Question Mode (`rules/armature_antigravity.md`): reply with
the full turn as visible text and no tool call, which models that keep leaving
the box blank (Opus 5.5 Medium retried with 0 words after two denials) still
deliver. After MAX_DENIALS the call is allowed so the agent can't get stuck.
"""

import json
import sys

MIN_WORDS = 25
MAX_DENIALS = 4
MARKER = "[armature-ask-guard]"
RETRY_REASON = (
    f"{MARKER} Blocked: the step that called ask_question had {{words}} words"
    " of visible text. Text in thinking is never shown, so the user would see a"
    " bare question box. In your next step, write the full turn as visible text"
    " first (the # <Topic> heading, a short orientation, numbered options with"
    " benefit and cost, the recommendation, and the - Pick N if lines, or the"
    " explanation the user asked for), then call ask_question again with the"
    " same options in that same step."
)
PLAIN_REASON = (
    f"{MARKER} Blocked again: the retry also had {{words}} words of visible"
    " text. Switch to Plain-Text Question Mode for this question: reply with"
    " the full turn as visible text (the # <Topic> heading, orientation,"
    " numbered options, recommendation, and - Pick N if lines) and end with"
    " 'Reply with 1, 2, or 3.' Don't call ask_question or any other tool in"
    " that reply. Use the box again for later questions."
)


def allow():
  print(json.dumps({"decision": "allow"}))


def load_steps(path):
  steps = []
  with open(path, encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if line:
        try:
          steps.append(json.loads(line))
        except json.JSONDecodeError:
          pass
  return steps


def current_turn(steps):
  """Returns steps after the last USER_INPUT."""
  for i in range(len(steps) - 1, -1, -1):
    if steps[i].get("type") == "USER_INPUT":
      return steps[i + 1:]
  return steps


def asking_step(turn):
  """Returns the latest planner step that calls ask_question."""
  for s in reversed(turn):
    if s.get("type") != "PLANNER_RESPONSE":
      continue
    names = [c.get("name") for c in s.get("tool_calls") or []]
    return s if "ask_question" in names else None
  return None


def main():
  try:
    payload = json.load(sys.stdin)
  except json.JSONDecodeError:
    return allow()
  if (payload.get("toolCall") or {}).get("name") != "ask_question":
    return allow()
  path = payload.get("transcriptPath") or ""
  try:
    turn = current_turn(load_steps(path))
  except OSError:
    return allow()
  step = asking_step(turn)
  if step is None or "content" in (step.get("truncated_fields") or []):
    return allow()
  words = len((step.get("content") or "").split())
  if words >= MIN_WORDS:
    return allow()
  denials = sum(
      1
      for s in turn
      if s.get("status") == "ERROR" and MARKER in str(s.get("error") or "")
  )
  if denials >= MAX_DENIALS:
    return allow()
  reason = RETRY_REASON if denials == 0 else PLAIN_REASON
  print(json.dumps({"decision": "deny", "reason": reason.format(words=words)}))


if __name__ == "__main__":
  try:
    main()
  except Exception:  # pylint: disable=broad-except
    allow()
