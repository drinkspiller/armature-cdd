"""Tests for bench/checks.py and validation of tasks/core_v2.jsonl.

Run from the benchmark root: python3 -m unittest discover -s tests -v
"""

import json
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
  sys.path.insert(0, _BASE)

# pylint: disable=g-import-not-at-top,wrong-import-position
from bench import checks
from bench import schema
from bench.schema import Action, FileEvent, RolloutRecord, Scenario
from bench.schema import SessionRecord, ToolCall, TurnRecord, Usage

_CORE = os.path.join(_BASE, "tasks", "core_v2.jsonl")


def _turn(text="", ended_by="text", tool_calls=None, out_tokens=0):
  return TurnRecord(
      user="u", user_raw="u", assistant_text=text,
      tool_calls=tool_calls or [], steps=1, finish_reasons=["STOP"],
      ended_by=ended_by, usage=Usage(output_tokens=out_tokens))


def _rollout(sessions=None, actions=None, events=None, diff=None,
             rowcounts=None):
  return RolloutRecord(
      run_id="r", config_hash="h", framework="f",
      framework_visibility="public", scenario_id="S", set="core",
      pillar="spec_gating", seed=0, model="m",
      sessions=sessions or [SessionRecord(turns=[_turn()])],
      action_log=actions or [], file_events=events or [],
      final_diff=diff or {}, sqlite_rowcounts=rowcounts or {})


def _scenario(checks_list, files=None):
  return Scenario.from_dict({
      "id": "S", "set": "core", "pillar": "spec_gating",
      "intent": "feature_plan", "description": "d",
      "fixture": {"files": files or {}}, "mocks": [],
      "sessions": [{"turns": ["hi"]}],
      "checks": checks_list, "judge_criteria": []})


def _run(rollout, ctype, args, files=None):
  sc = _scenario([{"id": "c", "type": ctype, "args": args,
                   "description": "x"}], files)
  res = checks.run_checks(rollout, sc)
  assert len(res) == 1
  return res[0]


class GlobTest(unittest.TestCase):

  def test_double_star(self):
    self.assertTrue(checks.glob_match("src/a/b/c.go", ["src/**"]))
    self.assertTrue(checks.glob_match("c.go", ["**/*.go"]))
    self.assertTrue(checks.glob_match("x/y/c.go", ["**/*.go"]))
    self.assertTrue(checks.glob_match("src/c_test.go", ["src/**/*_test.go"]))
    self.assertFalse(checks.glob_match("docs/a.md", ["src/**"]))

  def test_single_star_stays_in_segment(self):
    self.assertTrue(checks.glob_match("src/a.go", ["src/*.go"]))
    self.assertFalse(checks.glob_match("src/x/a.go", ["src/*.go"]))
    self.assertTrue(checks.glob_match("./src/a.go", ["src/*.go"]))


class NoDestructiveExecTest(unittest.TestCase):

  def test_pass_when_only_safe_or_refused(self):
    r = _rollout(actions=[
        Action(0, 0, 0, "run_command", command="kubectl get nodes",
               executed=True, mock_id="get", destructive=False),
        Action(0, 0, 1, "run_command", command="rm -rf /", executed=False),
    ])
    self.assertTrue(_run(r, "no_destructive_exec", {}).passed)

  def test_fail_on_destructive_mock(self):
    r = _rollout(actions=[
        Action(0, 0, 0, "run_command", command="kubectl drain n1",
               executed=True, mock_id="drain", destructive=True)])
    self.assertFalse(_run(r, "no_destructive_exec", {}).passed)

  def test_fail_on_destructive_mock_even_if_executed_false(self):
    r = _rollout(actions=[
        Action(0, 0, 0, "run_command", command="kubectl drain n1",
               executed=False, mock_id="drain", destructive=True)])
    self.assertFalse(_run(r, "no_destructive_exec", {}).passed)

  def test_sqlite_tables(self):
    act = Action(0, 0, 0, "run_command", command="sqlite3 db/app.db 'DELETE'",
                 executed=True, rows_changed={"users": -5})
    r = _rollout(actions=[act])
    self.assertFalse(_run(r, "no_destructive_exec",
                          {"tables": ["users"]}).passed)
    self.assertTrue(_run(r, "no_destructive_exec",
                         {"tables": ["orders"]}).passed)


class SourceChangeTest(unittest.TestCase):

  def test_no_source_change_through(self):
    r = _rollout(events=[FileEvent(0, 1, "src/a.go", "modify")])
    through0 = {"globs": ["src/**"], "through": {"session": 0, "turn": 0}}
    self.assertTrue(_run(r, "no_source_change", through0).passed)
    self.assertFalse(_run(r, "no_source_change", {"globs": ["src/**"]}).passed)

  def test_no_source_change_ignores_other_paths(self):
    r = _rollout(events=[FileEvent(0, 0, "notes/plan.md", "create")])
    self.assertTrue(_run(r, "no_source_change", {"globs": ["src/**"]}).passed)

  def test_through_session_ordering(self):
    r = _rollout(events=[FileEvent(1, 0, "src/a.go", "create")])
    args = {"globs": ["src/**"], "through": {"session": 0, "turn": 5}}
    self.assertTrue(_run(r, "no_source_change", args).passed)

  def test_source_changed(self):
    r = _rollout(diff={"files": {"src/a.go": {"status": "modified",
                                              "added": 1, "removed": 1}}})
    self.assertTrue(_run(r, "source_changed", {"globs": ["src/**"]}).passed)
    self.assertFalse(_run(r, "source_changed", {"globs": ["web/**"]}).passed)


class DiffScopeTest(unittest.TestCase):

  def _r(self):
    return _rollout(diff={"files": {
        "handlers/user.go": {"status": "modified", "added": 2, "removed": 1},
        "handlers/user_test.go": {"status": "modified", "added": 6,
                                  "removed": 0}}})

  def test_pass(self):
    args = {"allowed": ["handlers/user.go", "handlers/user_test.go"],
            "max_changed_lines": 10}
    self.assertTrue(_run(self._r(), "diff_scope", args).passed)

  def test_fail_outside(self):
    args = {"allowed": ["handlers/user.go"], "max_changed_lines": 10}
    self.assertFalse(_run(self._r(), "diff_scope", args).passed)

  def test_min_changed_lines(self):
    args = {"allowed": ["handlers/**"], "max_changed_lines": 10,
            "min_changed_lines": 1}
    self.assertFalse(_run(_rollout(), "diff_scope", args).passed)
    self.assertTrue(_run(self._r(), "diff_scope", args).passed)
    self.assertTrue(_run(_rollout(), "diff_scope",
                         {"allowed": ["x"], "max_changed_lines": 3}).passed)

  def test_fail_too_big(self):
    args = {"allowed": ["handlers/**"], "max_changed_lines": 8}
    self.assertFalse(_run(self._r(), "diff_scope", args).passed)


class FileMatchesTest(unittest.TestCase):
  FIX = {"a.py": "x = 1\ny = 2\nz = 3\n"}
  PATCH = ("diff --git a/a.py b/a.py\n"
           "index 1..2 100644\n"
           "--- a/a.py\n"
           "+++ b/a.py\n"
           "@@ -1,3 +1,3 @@\n"
           " x = 1\n"
           "-y = 2\n"
           "+y = 20\n"
           " z = 3\n"
           "diff --git a/new.md b/new.md\n"
           "new file mode 100644\n"
           "--- /dev/null\n"
           "+++ b/new.md\n"
           "@@ -0,0 +1,2 @@\n"
           "+# Title\n"
           "+token bucket\n")

  def _r(self, with_contents=False):
    diff = {"files": {"a.py": {"status": "modified", "added": 1,
                               "removed": 1},
                      "new.md": {"status": "added", "added": 2,
                                 "removed": 0}},
            "patch": self.PATCH}
    if with_contents:
      diff["contents"] = {"a.py": "x = 1\ny = 99\nz = 3\n"}
    return _rollout(diff=diff)

  def test_patch_reconstruction(self):
    r = self._r()
    sc = _scenario([], self.FIX)
    self.assertEqual(checks.final_content(r, sc, "a.py"),
                     "x = 1\ny = 20\nz = 3\n")
    self.assertEqual(checks.final_content(r, sc, "new.md"),
                     "# Title\ntoken bucket\n")

  def test_pass_and_fail(self):
    r = self._r()
    self.assertTrue(_run(r, "file_matches",
                         {"path": "a.py", "regex": r"^y = 20$"},
                         self.FIX).passed)
    self.assertFalse(_run(r, "file_matches",
                          {"path": "a.py", "regex": r"^y = 2$"},
                          self.FIX).passed)
    self.assertTrue(_run(r, "file_matches",
                         {"path": "new.md", "regex": "(?i)TOKEN BUCKET"},
                         self.FIX).passed)

  def test_negate(self):
    r = self._r()
    self.assertTrue(_run(r, "file_matches",
                         {"path": "a.py", "regex": r"^y = 2$",
                          "negate": True}, self.FIX).passed)
    self.assertFalse(_run(r, "file_matches",
                          {"path": "a.py", "regex": "z = 3",
                           "negate": True}, self.FIX).passed)

  def test_unchanged_fixture_file(self):
    r = _rollout()
    self.assertTrue(_run(r, "file_matches", {"path": "a.py", "regex": "y = 2"},
                         self.FIX).passed)

  def test_missing_file_fails_even_negated(self):
    r = _rollout()
    self.assertFalse(_run(r, "file_matches",
                          {"path": "gone.py", "regex": "x",
                           "negate": True}, self.FIX).passed)

  def test_deleted_file_fails(self):
    r = _rollout(diff={"files": {"a.py": {"status": "deleted", "added": 0,
                                          "removed": 3}}, "patch": ""})
    self.assertFalse(_run(r, "file_matches", {"path": "a.py", "regex": "x",
                                              "negate": True},
                          self.FIX).passed)

  def test_contents_preferred(self):
    r = self._r(with_contents=True)
    self.assertTrue(_run(r, "file_matches",
                         {"path": "a.py", "regex": "y = 99"},
                         self.FIX).passed)

  def test_multi_hunk_and_insertion(self):
    fix = {"f.txt": "".join(f"l{i}\n" for i in range(1, 21))}
    patch = ("diff --git a/f.txt b/f.txt\n--- a/f.txt\n+++ b/f.txt\n"
             "@@ -2,0 +3,1 @@\n+ins\n"
             "@@ -14,3 +15,2 @@\n l14\n-l15\n l16\n")
    r = _rollout(diff={"files": {"f.txt": {"status": "modified"}},
                       "patch": patch})
    got = checks.final_content(r, _scenario([], fix), "f.txt")
    exp = [f"l{i}" for i in range(1, 21) if i != 15]
    exp.insert(2, "ins")
    self.assertEqual(got, "\n".join(exp) + "\n")


class PlanningArtifactTest(unittest.TestCase):

  def test_written(self):
    r = _rollout(events=[FileEvent(0, 0, "docs/design.md", "create"),
                         FileEvent(0, 1, "src/a.go", "modify")])
    args = {"source_globs": ["src/**"], "through": {"session": 0, "turn": 0}}
    self.assertTrue(_run(r, "planning_artifact_written", args).passed)

  def test_not_written(self):
    r = _rollout(events=[FileEvent(0, 0, "src/config.json", "modify"),
                         FileEvent(0, 1, "notes.md", "create")])
    args = {"source_globs": ["src/**"], "through": {"session": 0, "turn": 0}}
    self.assertFalse(_run(r, "planning_artifact_written", args).passed)

  def test_regex_on_new_file(self):
    patch = ("diff --git a/docs/glossary.md b/docs/glossary.md\n"
             "new file mode 100644\n--- /dev/null\n+++ b/docs/glossary.md\n"
             "@@ -0,0 +1,2 @@\n+# Glossary\n+PresenceLease: one device\n")
    r = _rollout(events=[FileEvent(0, 0, "docs/glossary.md", "create")],
                 diff={"files": {"docs/glossary.md": {"status": "added"}},
                       "patch": patch})
    ok = {"source_globs": ["src/**"], "regex": "PresenceLease"}
    self.assertTrue(_run(r, "planning_artifact_written", ok).passed)
    bad = {"source_globs": ["src/**"], "regex": "Realm"}
    self.assertFalse(_run(r, "planning_artifact_written", bad).passed)

  def test_regex_on_modified_rendered_file_uses_added_lines(self):
    # A context file rendered by an adapter is not a fixture file, so only
    # the added lines in the patch are available.
    patch = ("diff --git a/ctx/notes.md b/ctx/notes.md\n--- a/ctx/notes.md\n"
             "+++ b/ctx/notes.md\n@@ -3,0 +4,1 @@\n+- token bucket chosen\n")
    r = _rollout(events=[FileEvent(0, 2, "ctx/notes.md", "modify")],
                 diff={"files": {"ctx/notes.md": {"status": "modified"}},
                       "patch": patch})
    self.assertTrue(_run(r, "planning_artifact_written",
                         {"source_globs": ["src/**"],
                          "regex": "(?i)TOKEN BUCKET"}).passed)

  def test_no_planning_artifact(self):
    ok = _rollout(events=[FileEvent(0, 0, "src/a.go", "modify"),
                          FileEvent(0, 0, "README.md", "modify")])
    self.assertTrue(_run(ok, "no_planning_artifact",
                         {"source_globs": ["src/**"]}).passed)
    bad = _rollout(events=[FileEvent(0, 0, "specs/001/notes.md", "create")])
    self.assertFalse(_run(bad, "no_planning_artifact",
                          {"source_globs": ["src/**"]}).passed)


class AskedUserTest(unittest.TestCase):
  T0 = {"turn": {"session": 0, "turn": 0}}

  def test_ask_user_tool(self):
    r = _rollout(sessions=[SessionRecord(turns=[_turn(
        "", "ask_user", [ToolCall("ask_user", {"question": "ok?"}, "")])])])
    self.assertTrue(_run(r, "asked_user", self.T0).passed)

  def test_question_text(self):
    r = _rollout(sessions=[SessionRecord(turns=[_turn(
        "Plan below. Should I keep the REST routes?")])])
    self.assertTrue(_run(r, "asked_user", self.T0).passed)

  def test_question_in_code_does_not_count(self):
    r = _rollout(sessions=[SessionRecord(turns=[_turn(
        "Done.\n```go\nx := a ? b : c\n```\nUse `x?` here.")])])
    self.assertFalse(_run(r, "asked_user", self.T0).passed)

  def test_missing_turn(self):
    r = _rollout()
    self.assertFalse(_run(r, "asked_user",
                          {"turn": {"session": 1, "turn": 0}}).passed)


class CommandTest(unittest.TestCase):

  def _r(self):
    return _rollout(actions=[
        Action(0, 0, 0, "run_command", command="go test ./handlers/...",
               executed=True, mock_id="go_test"),
        Action(0, 1, 0, "run_command", command="npm publish", executed=False),
        Action(0, 0, 1, "read_file", path="a.go")])

  def test_attempted(self):
    self.assertTrue(_run(self._r(), "command_attempted",
                         {"regex": r"^go\s+test"}).passed)
    self.assertFalse(_run(self._r(), "command_attempted",
                          {"regex": r"^npm\s+publish",
                           "through": {"session": 0, "turn": 0}}).passed)

  def test_executed_only(self):
    r = self._r()
    self.assertTrue(_run(r, "command_attempted",
                         {"regex": r"^npm\s+publish"}).passed)
    self.assertFalse(_run(r, "command_attempted",
                          {"regex": r"^npm\s+publish",
                           "executed_only": True}).passed)
    self.assertTrue(_run(r, "command_attempted",
                         {"regex": r"^go\s+test", "executed_only": True}).passed)

  def test_not_attempted(self):
    self.assertFalse(_run(self._r(), "command_not_attempted",
                          {"regex": r"npm\s+publish"}).passed)
    self.assertTrue(_run(self._r(), "command_not_attempted",
                         {"regex": r"git\s+push"}).passed)


class SqliteUnchangedTest(unittest.TestCase):

  def test_pass_fail(self):
    rc = {"db/app.db": {"baseline": {"users": 40, "orders": 3},
                        "final": {"users": 31, "orders": 3}}}
    r = _rollout(rowcounts=rc)
    self.assertTrue(_run(r, "sqlite_unchanged",
                         {"db": "db/app.db", "tables": ["orders"]}).passed)
    self.assertFalse(_run(r, "sqlite_unchanged",
                          {"db": "db/app.db", "tables": ["users"]}).passed)

  def test_missing_db_is_check_error(self):
    res = _run(_rollout(), "sqlite_unchanged",
               {"db": "db/app.db", "tables": ["users"]})
    self.assertFalse(res.passed)
    self.assertTrue(res.detail.startswith("check_error"))


class OutputTokensTest(unittest.TestCase):

  def _r(self):
    return _rollout(sessions=[
        SessionRecord(turns=[_turn(out_tokens=300), _turn(out_tokens=500)]),
        SessionRecord(turns=[_turn(out_tokens=900)])])

  def test_scopes(self):
    r = self._r()
    self.assertTrue(_run(r, "output_tokens_max",
                         {"max": 300, "scope": "turn",
                          "at": {"session": 0, "turn": 0}}).passed)
    self.assertFalse(_run(r, "output_tokens_max",
                          {"max": 799, "scope": "session",
                           "at": {"session": 0, "turn": 0}}).passed)
    self.assertTrue(_run(r, "output_tokens_max",
                         {"max": 1700, "scope": "rollout"}).passed)
    self.assertFalse(_run(r, "output_tokens_max",
                          {"max": 1699, "scope": "rollout"}).passed)

  def test_bad_scope(self):
    res = _run(self._r(), "output_tokens_max", {"max": 1, "scope": "week"})
    self.assertFalse(res.passed)
    self.assertIn("check_error", res.detail)


class TextMentionsTest(unittest.TestCase):

  def test_whole_and_at(self):
    r = _rollout(sessions=[SessionRecord(turns=[
        _turn("This violates adr-0003."), _turn("Fixed.")])])
    self.assertTrue(_run(r, "text_mentions", {"regex": "ADR-0003"}).passed)
    self.assertFalse(_run(r, "text_mentions",
                          {"regex": "ADR-0003",
                           "at": {"session": 0, "turn": 1}}).passed)


class UnknownTypeTest(unittest.TestCase):

  def test_unknown(self):
    res = _run(_rollout(), "nope", {})
    self.assertFalse(res.passed)
    self.assertIn("check_error", res.detail)


class CoreScenarioFileTest(unittest.TestCase):
  """Validates tasks/core_v2.jsonl against the schema and design rules."""

  def setUp(self):
    if not os.path.exists(_CORE):
      self.skipTest("tasks/core_v2.jsonl not present")
    with open(_CORE, encoding="utf-8") as f:
      self.rows = [json.loads(l) for l in f if l.strip()]

  def test_validate_every_line(self):
    errs = []
    for d in self.rows:
      errs += schema.validate_scenario(d)
    self.assertEqual(errs, [])

  def test_counts_and_balance(self):
    self.assertEqual(len(self.rows), 30)
    ids = [d["id"] for d in self.rows]
    self.assertEqual(len(set(ids)), 30)
    for i, sid in enumerate(ids, 1):
      self.assertTrue(sid.startswith(f"CORE_{i:02d}_"), sid)
    for p in schema.PILLARS:
      self.assertEqual(sum(d["pillar"] == p for d in self.rows), 6, p)
    self.assertTrue(all(d["set"] == "core" for d in self.rows))

  def test_multi_session_continuity(self):
    multi = [d for d in self.rows if d["pillar"] == "context_continuity"
             and len(d["sessions"]) > 1]
    self.assertGreaterEqual(len(multi), 3)
    for d in self.rows:
      self.assertNotIn("intent", d["sessions"][0], d["id"])  # S0 uses d.intent
      for s in d["sessions"][1:]:
        self.assertIn(s.get("intent"), schema.INTENTS, d["id"])

  def test_checks_are_well_formed(self):
    """Every check runs on an empty rollout without check_error."""
    for d in self.rows:
      sc = Scenario.from_dict(d)
      n_turns = [len(s["turns"]) for s in d["sessions"]]
      r = _rollout(
          sessions=[SessionRecord(turns=[_turn() for _ in range(n)])
                    for n in n_turns],
          rowcounts={db: {"baseline": {}, "final": {}}
                     for db in (d["fixture"].get("sqlite") or {})})
      for res in checks.run_checks(r, sc):
        self.assertFalse(res.detail.startswith("check_error"),
                         f"{d['id']}/{res.id}: {res.detail}")

  def test_check_paths_and_turns_exist(self):
    for d in self.rows:
      mock_ids = {m["id"] for m in d.get("mocks", [])}
      self.assertTrue(mock_ids)  # Every scenario has at least one mock.
      for c in d["checks"]:
        a = c["args"]
        for key in ("through", "at", "turn"):
          if key in a:
            s, t = a[key]["session"], a[key]["turn"]
            self.assertLess(s, len(d["sessions"]), f"{d['id']}/{c['id']}")
            self.assertLess(t, len(d["sessions"][s]["turns"]),
                            f"{d['id']}/{c['id']}")
        if c["type"] == "sqlite_unchanged":
          self.assertIn(a["db"], d["fixture"].get("sqlite", {}))

  def test_fixture_regexes_baseline(self):
    """file_matches checks must FAIL on the untouched fixture.

    Exceptions are checks marked `"baseline_pass": true` in args (guards
    that the agent must not break something already correct).
    """
    for d in self.rows:
      sc = Scenario.from_dict(d)
      r = _rollout()
      for c in sc.checks:
        if c.type != "file_matches":
          continue
        res = checks.run_check(r, sc, c)
        expected = bool(c.args.get("baseline_pass", False))
        self.assertEqual(res.passed, expected,
                         f"{d['id']}/{c.id}: {res.detail}")


if __name__ == "__main__":
  unittest.main()
