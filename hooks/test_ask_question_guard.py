#!/usr/bin/env python3
"""Unit tests for `ask_question_guard.py` (PreToolUse + Stop hooks)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if HOOKS_DIR not in sys.path:
  sys.path.insert(0, HOOKS_DIR)

import ask_question_guard as guard  # pylint: disable=g-import-not-at-top


def _write_transcript(directory, steps, full=False):
  name = "transcript_full.jsonl" if full else "transcript.jsonl"
  path = os.path.join(directory, name)
  with open(path, "w", encoding="utf-8") as f:
    for s in steps:
      f.write(json.dumps(s) + "\n")
  return path


def _run_hook(payload):
  proc = subprocess.run(
      [sys.executable, os.path.join(HOOKS_DIR, "ask_question_guard.py")],
      input=json.dumps(payload),
      capture_output=True,
      text=True,
      check=True,
  )
  return json.loads(proc.stdout.strip())


class AskQuestionGuardTest(unittest.TestCase):
  """Verifies PreToolUse blank-box blocking and Stop dropped-ask detection."""

  def test_pre_tool_allows_rich_visible_text(self):
    """Allows ask_question when its step carries at least MIN_WORDS."""
    with tempfile.TemporaryDirectory() as tmp:
      path = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Start interview"},
              {
                  "type": "PLANNER_RESPONSE",
                  "content": " ".join(["word"] * 30),
                  "tool_calls": [{"name": "ask_question"}],
              },
          ],
      )
      res = _run_hook({
          "hookEventName": "PreToolUse",
          "toolCall": {"name": "ask_question"},
          "transcriptPath": path,
      })
      self.assertEqual(res["decision"], "allow")

  def test_pre_tool_blocks_blank_box_and_escalates_to_plain(self):
    """Denies blank ask_question and escalates to Plain-Text mode."""
    with tempfile.TemporaryDirectory() as tmp:
      path = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Start interview"},
              {
                  "type": "PLANNER_RESPONSE",
                  "content": "short text",
                  "tool_calls": [{"name": "ask_question"}],
              },
          ],
      )
      res1 = _run_hook({
          "hookEventName": "PreToolUse",
          "toolCall": {"name": "ask_question"},
          "transcriptPath": path,
      })
      self.assertEqual(res1["decision"], "deny")
      self.assertIn(guard.MARKER, res1["reason"])
      self.assertNotIn("Plain-Text Question Mode", res1["reason"])

      path = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Start interview"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "ERROR",
                  "error": f"{guard.MARKER} Blocked",
                  "content": "",
                  "tool_calls": [{"name": "ask_question"}],
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "content": "",
                  "tool_calls": [{"name": "ask_question"}],
              },
          ],
      )
      res2 = _run_hook({
          "hookEventName": "PreToolUse",
          "toolCall": {"name": "ask_question"},
          "transcriptPath": path,
      })
      self.assertEqual(res2["decision"], "deny")
      self.assertIn("Plain-Text Question Mode", res2["reason"])

  def test_stop_continues_when_decision_turn_drops_ask_question(self):
    """Continues when a turn prints option cards without calling ask_question."""
    with tempfile.TemporaryDirectory() as tmp:
      content = (
          "# Controlling Text Fields\n\n"
          "Here are some options:\n\n"
          "> **Option 1: Fixed codes (Recommended)**\n"
          "> - **Pros:** Safe.\n\n"
          "### Recommendation: Option 1\n\n"
          "Blocks untrusted text.\n\n"
          "- Pick 1 if safety matters.\n"
          "- Pick 2 if labels matter."
      )
      path = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Zoom out"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": content,
                  "tool_calls": [],
              },
          ],
      )
      res = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 0,
          "continuationActive": False,
          "terminationReason": "MODEL_STOP",
          "transcriptPath": path,
      })
      self.assertEqual(res["decision"], "continue")
      self.assertEqual(res["reason"], guard.STOP_CONTINUE_REASON)
      self.assertIn(guard.STOP_MARKER, res["reason"])

  def test_stop_continues_on_waiting_for_tunnel_turn(self):
    """Continues when a turn asks the user to act without calling ask_question."""
    with tempfile.TemporaryDirectory() as tmp:
      path = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Continue"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": (
                      "The reverse tunnel returned Connection refused. "
                      "Please restart the tunnel and tell me when it's up."
                  ),
                  "tool_calls": [],
              },
          ],
      )
      res = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 0,
          "continuationActive": False,
          "terminationReason": "MODEL_STOP",
          "transcriptPath": path,
      })
      self.assertEqual(res["decision"], "continue")
      self.assertEqual(res["reason"], guard.STOP_CONTINUE_SHORT_REASON)

      for tail in (
          "Ping me when the tunnel is back and I'll pick up from step 1.",
          "Want to go with both, or adjust either one before proceeding?",
          "Which of these would you like to tackle first — backup or ping?",
      ):
        self.assertTrue(
            guard.looks_like_dropped_ask_question(tail),
            f"Expected dropped-ask detection for: {tail}",
        )

  def test_stop_allows_informational_reply(self):
    """Allows stopping on informational replies that do not wait on decisions."""
    with tempfile.TemporaryDirectory() as tmp:
      path = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "What is git commit --amend?"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": (
                      "`git commit --amend` updates the current commit in place"
                      " in Git. Let me know if you want more details."
                  ),
                  "tool_calls": [],
              },
          ],
      )
      res = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 0,
          "continuationActive": False,
          "terminationReason": "MODEL_STOP",
          "transcriptPath": path,
      })
      self.assertEqual(res["decision"], "stop")

  def test_stop_allows_when_plain_mode_or_continuation_active(self):
    """Allows stopping in Plain-Text Question Mode or after continuation."""
    with tempfile.TemporaryDirectory() as tmp:
      content = (
          "Here are some options:\n\n1. Wait\n2. Copy\n\nReply with 1 or 2."
      )
      path = _write_transcript(
          tmp,
          [
              {
                  "type": "USER_INPUT",
                  "content": "Stop using the question box, ask me in chat.",
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": content,
                  "tool_calls": [],
              },
          ],
      )
      res_plain = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 0,
          "continuationActive": False,
          "terminationReason": "MODEL_STOP",
          "transcriptPath": path,
      })
      self.assertEqual(res_plain["decision"], "stop")

      path2 = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Continue"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": content,
                  "tool_calls": [],
              },
          ],
      )
      res_cont = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 1,
          "continuationActive": True,
          "terminationReason": "MODEL_STOP",
          "transcriptPath": path2,
      })
      self.assertEqual(res_cont["decision"], "stop")

  def test_pretool_allows_short_ask_after_stop_continuation(self):
    """Counts Stop-continued prior text toward PreToolUse word minimum."""
    prior_decision = (
        "# Controlling Text Fields\n\n"
        "The choice here is how strictly to lock down free text slots for"
        " unusual hardware parts across the external boundary. Here are some"
        " options:\n\n"
        "> **Option 1: Fixed codes only (Recommended)**\n"
        "> - **Pros:** Blocks untrusted web text.\n"
        "> - **Cons:** Drops rare labels.\n"
        "> - **Implications:** Keeps unexpected geometry numeric.\n\n"
        "### Recommendation: Option 1\n\n"
        "Strict enums eliminate free-text injection risk.\n\n"
        "- Pick 1 if safety matters.\n"
        "- Pick 2 if custom labels matter."
    )
    with tempfile.TemporaryDirectory() as tmp:
      path_with_stop_user = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Next question"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": prior_decision,
                  "tool_calls": [],
              },
              {
                  "type": "USER_INPUT",
                  "content": guard.STOP_CONTINUE_REASON,
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "content": "",
                  "tool_calls": [{"name": "ask_question"}],
              },
          ],
      )
      res1 = _run_hook({
          "hookEventName": "PreToolUse",
          "toolCall": {"name": "ask_question"},
          "transcriptPath": path_with_stop_user,
      })
      self.assertEqual(res1["decision"], "allow")

      # Even if the Stop continuation marker isn't persisted in transcript,
      # the preceding dropped-decision text counts toward MIN_WORDS.
      path_without_marker = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Next question"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": prior_decision,
                  "tool_calls": [],
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "content": "Choose which option to apply.",
                  "tool_calls": [{"name": "ask_question"}],
              },
          ],
      )
      res2 = _run_hook({
          "hookEventName": "PreToolUse",
          "toolCall": {"name": "ask_question"},
          "transcriptPath": path_without_marker,
      })
      self.assertEqual(res2["decision"], "allow")

      # Combined text under MIN_WORDS must still be blocked.
      path_too_short = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Next question"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": "How should we proceed? Option 1 or 2?",
                  "tool_calls": [],
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "content": "Pick one.",
                  "tool_calls": [{"name": "ask_question"}],
              },
          ],
      )
      res3 = _run_hook({
          "hookEventName": "PreToolUse",
          "toolCall": {"name": "ask_question"},
          "transcriptPath": path_too_short,
      })
      self.assertEqual(res3["decision"], "deny")


if __name__ == "__main__":
  unittest.main()
