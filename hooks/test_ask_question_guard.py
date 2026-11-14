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
          "Ping me once the tunnel is up and I'll kick off step 1 immediately.",
          "Let me know once the server restarts.",
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
                      "`git commit --amend` updates the current commit in place in Git. "
                      "Let me know if you want more details."
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

      # Without a Stop continuation marker in the turn, a prior text-only step
      # must NOT exempt a short/blank ask_question call from PreToolUse.
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
      self.assertEqual(res2["decision"], "deny")

      # Combined text under MIN_WORDS must still be blocked even with marker.
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
                  "type": "SYSTEM_MESSAGE",
                  "content": f"{guard.STOP_MARKER} Blocked turn end.",
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

  def test_multi_round_ask_question_resets_stop_credit_and_denials(self):
    """Completed ask_question exchanges isolate later interview rounds."""
    prior_decision = (
        "# Round 1 Storage\n\n"
        "The choice here is where to store drafts. Here are some options:\n\n"
        "> **Option 1: Save locally (Recommended)**\n"
        "> - **Pros:** Fast offline edits.\n"
        "> - **Cons:** Single machine only.\n"
        "> - **Implications:** Uses local files.\n\n"
        "### Recommendation: Option 1\n\nFastest default.\n\n"
        "- Pick 1 if offline edits matter.\n"
        "- Pick 2 if syncing matters."
    )
    with tempfile.TemporaryDirectory() as tmp:
      # Round 1 had a Stop recovery; user answered via GENERIC tool response
      # (no USER_INPUT). Round 2 blank ask_question MUST still be denied.
      path_r2_blank = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "/arm-new-track auth"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": prior_decision,
                  "tool_calls": [],
              },
              {
                  "type": "SYSTEM_MESSAGE",
                  "content": f"{guard.STOP_MARKER} Blocked turn end.",
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": "",
                  "tool_calls": [{"name": "ask_question"}],
              },
              {
                  "type": "GENERIC",
                  "status": "DONE",
                  "content": "A1: (Recommended) Save locally",
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "content": "",
                  "tool_calls": [{"name": "ask_question"}],
              },
          ],
      )
      res_blank = _run_hook({
          "hookEventName": "PreToolUse",
          "toolCall": {"name": "ask_question"},
          "transcriptPath": path_r2_blank,
      })
      self.assertEqual(res_blank["decision"], "deny")
      self.assertIn("Blocked:", res_blank["reason"])

      # Round 1 & Round 2 each had 1 PreToolUse retry before completing.
      # Round 3 dropped ask_question MUST still trigger Stop continuation.
      path_r3_stop = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "/arm-new-track auth"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": "",
                  "tool_calls": [{"name": "ask_question"}],
              },
              {
                  "type": "GENERIC",
                  "status": "ERROR",
                  "error": f"{guard.MARKER} Blocked: 0 words",
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": prior_decision,
                  "tool_calls": [{"name": "ask_question"}],
              },
              {"type": "GENERIC", "status": "DONE", "content": "A1: Option 1"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": "",
                  "tool_calls": [{"name": "ask_question"}],
              },
              {
                  "type": "GENERIC",
                  "status": "ERROR",
                  "error": f"{guard.MARKER} Blocked: 0 words",
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": prior_decision,
                  "tool_calls": [{"name": "ask_question"}],
              },
              {"type": "GENERIC", "status": "DONE", "content": "A1: Option 1"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": prior_decision,
                  "tool_calls": [],
              },
          ],
      )
      res_stop = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 0,
          "continuationActive": False,
          "transcriptPath": path_r3_stop,
      })
      self.assertEqual(res_stop["decision"], "continue")

  def test_plain_mode_reenable_and_quoted_text_safety(self):
    """Plain-Text mode toggles off on re-enable and ignores quotes/reports."""
    decision = (
        "# Next Step\n\n"
        "The choice here is how to deploy. Here are some options:\n\n"
        "> **Option 1: Stage first (Recommended)**\n"
        "> - **Pros:** Safe.\n"
        "> - **Cons:** Slower.\n"
        "> - **Implications:** Needs staging run.\n\n"
        "### Recommendation: Option 1\n\nSafer rollout.\n\n"
        "- - Pick 1 if safety matters.\n"
        "* Pick 2 if speed matters."
    )
    with tempfile.TemporaryDirectory() as tmp:
      # User re-enables the question box after earlier plain-text request.
      path_reenabled = _write_transcript(
          tmp,
          [
              {
                  "type": "USER_INPUT",
                  "content": "Stop using the question box for now.",
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "content": "Sure.",
                  "tool_calls": [],
              },
              {
                  "type": "USER_INPUT",
                  "content": "Okay, use the question box again.",
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "content": decision,
                  "tool_calls": [],
              },
          ],
      )
      res1 = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 0,
          "transcriptPath": path_reenabled,
      })
      self.assertEqual(res1["decision"], "continue")

      # Bug report mentioning "no question box" must NOT disable Stop guard.
      path_bug_report = _write_transcript(
          tmp,
          [
              {
                  "type": "USER_INPUT",
                  "content": (
                      "Earlier I saw no question box.\n"
                      "> Stop using the question box\n"
                      "```text\nplain-text question mode\n```"
                  ),
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "content": "Should we rename both flags or just one?",
                  "tool_calls": [],
              },
          ],
      )
      res2 = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 0,
          "transcriptPath": path_bug_report,
      })
      self.assertEqual(res2["decision"], "continue")

  def test_stop_ignores_fenced_quotes_fully_idle_false_and_nested_args(self):
    """Fenced option examples, fullyIdle=False, and nested stopHookArgs."""
    with tempfile.TemporaryDirectory() as tmp:
      # Informational report quoting an Option card inside a code fence.
      fenced_report = (
          "Here is the template format used in docs:\n\n"
          "```markdown\n"
          "> **Option 1: Demo (Recommended)**\n"
          "### Recommendation: Option 1\n"
          "- Pick 1 if needed.\n"
          "```\n\n"
          "All 10 tests passed cleanly."
      )
      path_fenced = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Show the template"},
              {
                  "type": "PLANNER_RESPONSE",
                  "content": fenced_report,
                  "tool_calls": [],
              },
          ],
      )
      res_fenced = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 0,
          "transcriptPath": path_fenced,
      })
      self.assertEqual(res_fenced["decision"], "stop")

      # Waiting on a background task (fullyIdle=False) must allow stop.
      path_waiting = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Run the build"},
              {
                  "type": "PLANNER_RESPONSE",
                  "content": "Do you want me to wait for the tunnel?",
                  "tool_calls": [],
              },
          ],
      )
      res_busy = _run_hook({
          "hookEventName": "Stop",
          "stopHookArgs": {"executionNum": 0, "fullyIdle": False},
          "common": {"transcriptPath": path_waiting},
      })
      self.assertEqual(res_busy["decision"], "stop")

      # Nested stopHookArgs executionNum >= 1 must allow stop.
      res_nested_exec = _run_hook({
          "stopHookArgs": {"executionNum": 1, "continuationActive": True},
          "common": {"transcriptPath": path_waiting},
      })
      self.assertEqual(res_nested_exec["decision"], "stop")

      # Nested stopHookArgs executionNum=0, fullyIdle=True catches waiting tail.
      res_nested_catch = _run_hook({
          "stopHookArgs": {"executionNum": 0, "fullyIdle": True},
          "common": {"transcriptPath": path_waiting},
      })
      self.assertEqual(res_nested_catch["decision"], "continue")

  def test_round2_stop_fires_even_when_turn_continuation_active_and_caps_once(
      self,
  ):
    """Round 2+ Stop still fires after Round 1 Stop + completed ask_question."""
    with tempfile.TemporaryDirectory() as tmp:
      round1_text = (
          "# Round 1\n\nHere are some options:\n\n"
          "> **Option 1: Keep (Recommended)**\n"
          "> - **Pros:** Fast.\n\n- Pick 1 if fast.\n- Pick 2 if thorough. "
          + " ".join(["context"] * 20)
      )
      round2_text = (
          "# Round 2\n\nHere are some options:\n\n"
          "> **Option 1: Retry (Recommended)**\n"
          "> - **Pros:** Safe.\n\n- Pick 1 if safe.\n- Pick 2 if skip. "
          + " ".join(["detail"] * 20)
      )
      round2_steps = [
          {"type": "USER_INPUT", "content": "/arm-new-track demo"},
          {
              "type": "PLANNER_RESPONSE",
              "status": "DONE",
              "content": round1_text,
              "tool_calls": [],
          },
          {
              "type": "SYSTEM_MESSAGE",
              "content": f"{guard.STOP_MARKER} Blocked turn end.",
          },
          {
              "type": "PLANNER_RESPONSE",
              "status": "DONE",
              "content": "",
              "tool_calls": [{"name": "ask_question"}],
          },
          {
              "type": "GENERIC",
              "status": "DONE",
              "content": "A1: (Recommended) Keep",
          },
          {
              "type": "PLANNER_RESPONSE",
              "status": "DONE",
              "content": round2_text,
              "tool_calls": [],
          },
      ]
      path_r2 = _write_transcript(tmp, round2_steps)
      # Turn-global continuationActive=True / executionNum=1 from Round 1 must
      # NOT suppress Stop for Round 2's first dropped ask_question.
      res_r2 = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 1,
          "continuationActive": True,
          "terminationReason": "MODEL_STOP",
          "transcriptPath": path_r2,
      })
      self.assertEqual(res_r2["decision"], "continue")
      self.assertEqual(res_r2["reason"], guard.STOP_CONTINUE_REASON)

      # Once Round 2 has already had a Stop continuation, Stop allows ending.
      round2_continued = round2_steps + [
          {
              "type": "SYSTEM_MESSAGE",
              "content": f"{guard.STOP_MARKER} Blocked turn end.",
          },
          {
              "type": "PLANNER_RESPONSE",
              "status": "DONE",
              "content": round2_text,
              "tool_calls": [],
          },
      ]
      path_r2_done = _write_transcript(tmp, round2_continued)
      res_r2_done = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 2,
          "continuationActive": True,
          "terminationReason": "MODEL_STOP",
          "transcriptPath": path_r2_done,
      })
      self.assertEqual(res_r2_done["decision"], "stop")

  def test_plain_mode_via_ask_question_write_in_and_ignores_read_file(self):
    """Write-in plain-mode opt-out/re-enable works; read_file GENERIC ignored."""
    with tempfile.TemporaryDirectory() as tmp:
      options_text = (
          "Here are some options:\n\n1. A\n2. B\n\nReply with 1 or 2."
      )
      # A GENERIC tool response from read_file mentioning "stop using the box"
      # must NOT activate Plain-Text Question Mode.
      path_read = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Review rules"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": "",
                  "tool_calls": [{"name": "read_file"}],
              },
              {
                  "type": "GENERIC",
                  "status": "DONE",
                  "content": (
                      "Showing lines 1-10\n"
                      "1: only when the user says stop using the question box\n"
                  ),
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": options_text,
                  "tool_calls": [],
              },
          ],
      )
      res_read = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 0,
          "transcriptPath": path_read,
      })
      self.assertEqual(res_read["decision"], "continue")

      # Write-in opt-out on a GENERIC ask_question answer disables Stop.
      path_writein = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Start interview"},
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": "Round 1 " + " ".join(["w"] * 30),
                  "tool_calls": [{"name": "ask_question"}],
              },
              {
                  "type": "GENERIC",
                  "status": "DONE",
                  "content": (
                      "Created At: 2026-11-14\n"
                      "A1: Stop using the question box, ask me in chat"
                  ),
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": options_text,
                  "tool_calls": [],
              },
          ],
      )
      res_writein = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 0,
          "transcriptPath": path_writein,
      })
      self.assertEqual(res_writein["decision"], "stop")

      # Re-enable via ASK_QUESTION step turns Stop back on.
      path_reenable = _write_transcript(
          tmp,
          [
              {"type": "USER_INPUT", "content": "Start interview"},
              {
                  "type": "ASK_QUESTION",
                  "status": "DONE",
                  "content": "A1: Stop using the question box",
              },
              {
                  "type": "ASK_QUESTION",
                  "status": "DONE",
                  "content": "A1: Use the question box again",
              },
              {
                  "type": "PLANNER_RESPONSE",
                  "status": "DONE",
                  "content": options_text,
                  "tool_calls": [],
              },
          ],
      )
      res_reenable = _run_hook({
          "hookEventName": "Stop",
          "executionNum": 0,
          "transcriptPath": path_reenable,
      })
      self.assertEqual(res_reenable["decision"], "continue")


if __name__ == "__main__":
  unittest.main()
