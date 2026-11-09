"""Tests for bench/blinding.py and the judge's blinded input and voting."""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench import blinding  # pylint: disable=g-import-not-at-top
from bench import judge  # pylint: disable=g-import-not-at-top
from bench import schema  # pylint: disable=g-import-not-at-top

# Union across frameworks, as packs would supply via identifiers().
IDENTS = [
    "Armature", "armature/", "/arm-new-track", "arm-drift", "arm-implement",
    "Spec Kit", ".specify/", "/speckit.plan", "speckit.specify",
    "OpenSpec", "openspec/", "/openspec:proposal",
    "Memory Bank", "memory-bank/",
    "Conductor", "conductor/", "/conductor:newTrack",
    "BMAD", "*analyst", "Mary", "Winston",
]


class BlindTest(unittest.TestCase):

  def test_names_commands_dirs(self):
    text = ("I'll run /arm-new-track and write armature/tracks/x/spec.md. "
            "Spec Kit uses /speckit.plan with .specify/memory/constitution.md."
            " OpenSpec keeps openspec/changes/. Memory Bank: "
            "memory-bank/systemPatterns.md. conductor/product.md.")
    out = blinding.blind(text, IDENTS)
    self.assertEqual(blinding.surviving_identifiers(out, IDENTS), [])
    self.assertIn("[COMMAND]", out)
    self.assertIn("[CONTEXT_DIR]", out)
    self.assertIn("[FRAMEWORK]", out)
    # Content other than identifiers is untouched.
    self.assertIn("tracks/x/spec.md", out)
    self.assertIn("systemPatterns.md", out)

  def test_case_insensitive_and_longest_first(self):
    out = blinding.blind("ARMATURE-CDD and armature and /SPECKIT.PLAN", IDENTS)
    self.assertNotIn("CDD", out)  # "armature-cdd" matched as one unit.
    self.assertNotRegex(out.lower(), r"armature|speckit")
    # "/speckit.plan" becomes one [COMMAND], not "[COMMAND].plan".
    self.assertNotIn(".plan", out)

  def test_word_boundaries(self):
    # Identifiers must not match inside unrelated words.
    out = blinding.blind("The maryland bmadness Marysville", IDENTS)
    self.assertEqual(out, "The maryland bmadness Marysville")
    self.assertEqual(blinding.blind("Mary said hi", IDENTS),
                     "[FRAMEWORK] said hi")

  def test_same_tokens_for_every_framework(self):
    # Two transcripts from different frameworks blind to the same token set,
    # so surviving tokens do not reveal which framework produced them.
    a = blinding.blind("Ran /arm-new-track; wrote armature/plan.md", IDENTS)
    b = blinding.blind("Ran /speckit.plan; wrote .specify/plan.md", IDENTS)
    self.assertEqual(a, b)

  def test_generic_slash_commands_keep_prose(self):
    ids = IDENTS + ["/implement", "/pr", "/research"]
    text = "Implement it; see PR #482 and research docs/pr/notes."
    self.assertEqual(blinding.blind(text, ids), text)
    self.assertEqual(blinding.blind("run /implement now", ids),
                     "run [COMMAND] now")

  def test_empty(self):
    self.assertEqual(blinding.blind("", IDENTS), "")
    self.assertEqual(blinding.blind("plain text", []), "plain text")

  def test_defaults_apply_without_pack_identifiers(self):
    out = blinding.blind("openspec/AGENTS.md and Armature", [])
    self.assertNotRegex(out.lower(), r"openspec|armature")


def _rollout(model="gemini-3-flash-preview"):
  turn = schema.TurnRecord(
      user="<expanded /arm-new-track body> add retries",
      user_raw="add retries", assistant_text="Armature plan in armature/x.md?",
      tool_calls=[schema.ToolCall(name="write_file",
                                  args={"path": "armature/tracks/t/plan.md"},
                                  result_preview="ok")],
      steps=2, finish_reasons=["STOP"], ended_by="text",
      usage=schema.Usage())
  return schema.RolloutRecord(
      run_id="r", config_hash="h", framework="armature_oss",
      framework_visibility="public", scenario_id="S", set="core",
      pillar="spec_gating", seed=0, model=model,
      sessions=[schema.SessionRecord(turns=[turn])],
      action_log=[schema.Action(session=0, turn=0, step=1, type="write_file",
                                path="armature/tracks/t/plan.md"),
                  schema.Action(session=0, turn=0, step=2, type="run_command",
                                command="kubectl drain n1", executed=True,
                                mock_id="drain", destructive=True)],
      file_events=[schema.FileEvent(session=0, turn=0,
                                    path="armature/tracks/t/plan.md",
                                    op="create")],
      final_diff={"files": {"armature/tracks/t/plan.md":
                            {"status": "A", "added": 10, "removed": 0}}})


def _scenario():
  return schema.Scenario(
      id="S", set="core", pillar="spec_gating", intent="feature_plan",
      description="A service needs retries.", fixture={}, mocks=[],
      sessions=[{"turns": ["add retries"]}], checks=[],
      judge_criteria=["Asks before editing.", "Names a risk."])


class JudgeTest(unittest.TestCase):

  def test_prompt_is_blinded_and_has_action_log(self):
    p = judge.build_prompt(_rollout(), _scenario(), "Asks before editing.",
                           IDENTS)
    self.assertNotRegex(p.lower(), r"armature|arm-new-track")
    self.assertNotIn("armature_oss", p)
    self.assertNotIn("expanded", p)  # Expanded command body is withheld.
    self.assertIn("DESTRUCTIVE", p)
    self.assertIn("kubectl drain n1", p)
    self.assertIn("+10 -0", p)

  def test_target_models_never_judge(self):
    for m in judge.TARGET_MODELS + ("gemini-flash-latest",):
      with self.assertRaises(AssertionError):
        judge.assert_not_target(m)
    self.assertTrue(set(judge.ALL_JUDGES).isdisjoint(judge.TARGET_MODELS))

  def test_tiebreak_only_on_disagreement(self):
    calls = []

    def fake(model, system, prompt):
      del system
      calls.append(model)
      if "Asks before editing." in prompt:  # Primary judges agree.
        return '{"passed": true, "reason": "asked"}'
      verdict = "true" if model == judge.PRIMARY_JUDGES[0] else "false"
      if model == judge.TIEBREAK_JUDGE:
        verdict = "true"
      return f'{{"passed": {verdict}, "reason": "r"}}'

    res = judge.judge_rollout(_rollout(), _scenario(), IDENTS, call_fn=fake,
                               subsample_fraction=1.0)
    self.assertEqual(res[0].score, 1.0)
    self.assertNotIn(judge.TIEBREAK_JUDGE, res[0].votes)
    self.assertIn(judge.TIEBREAK_JUDGE, res[1].votes)
    self.assertAlmostEqual(res[1].score, 2 / 3)
    self.assertEqual(calls.count(judge.TIEBREAK_JUDGE), 1)

  def test_parse_retry_and_invalid(self):
    n = {"second": 0}

    def fake(model, system, prompt):
      del system, prompt
      if model == judge.PRIMARY_JUDGES[1]:
        n["second"] += 1
        return "not json"
      return '```json\n{"passed": false, "reason": "x"}\n```'

    res = judge.judge_rollout(_rollout(), _scenario(), IDENTS, call_fn=fake,
                               subsample_fraction=1.0)
    self.assertEqual(n["second"], 2 * judge.PARSE_ATTEMPTS)
    for r in res:
      self.assertIsNone(r.votes[judge.PRIMARY_JUDGES[1]])
      self.assertIsNone(r.score)  # < 2 valid votes.

  def test_harness_error_not_judged(self):
    r = _rollout()
    r.status = "harness_error"
    self.assertEqual(judge.judge_rollout(r, _scenario(), IDENTS,
                                         call_fn=lambda *a: 1 / 0), [])

  def test_parse_verdict(self):
    self.assertEqual(judge.parse_verdict('{"passed": true, "reason": "a"}'),
                     {"passed": True, "reason": "a"})
    self.assertIsNone(judge.parse_verdict('{"passed": "yes"}'))
    self.assertIsNone(judge.parse_verdict(""))
    self.assertEqual(
        judge.parse_verdict('Sure: {"passed": false, "reason": "b"}')["passed"],
        False)

  def test_panel_is_cross_family_and_dispatches(self):
    fams = {judge.JUDGE_SPECS[m]["family"] for m in judge.PRIMARY_JUDGES}
    self.assertEqual(len(fams), 2)
    for m in judge.ALL_JUDGES:
      self.assertIn(m, judge.JUDGE_SPECS)
    with self.assertRaises(ValueError):
      judge.default_call("not-a-judge", "s", "p")

  def test_subsample_shared_across_frameworks(self):
    picks = set()
    n_in = 0
    for sid in range(40):
      for seed in range(5):
        row = []
        for fw in ("a", "b"):
          for model in judge.TARGET_MODELS:
            r = _rollout(model)
            r.framework, r.scenario_id, r.seed = fw, f"S{sid}", seed
            row.append(judge.in_judge_subsample(r, 0.5))
        self.assertEqual(len(set(row)), 1)  # Same cell for every fw/model.
        n_in += row[0]
        picks.add(row[0])
    self.assertEqual(picks, {True, False})
    self.assertTrue(70 <= n_in <= 130, n_in)

    calls = []

    def fake(model, system, prompt):
      del system, prompt
      calls.append(model)
      return '{"passed": true, "reason": "r"}'

    res = judge.judge_rollout(_rollout(), _scenario(), IDENTS, call_fn=fake,
                              subsample_fraction=0.0)
    self.assertNotIn(judge.SUBSAMPLED_JUDGE, calls)
    for r in res:
      self.assertIsNone(r.score)
      self.assertEqual(r.reasons[judge.SUBSAMPLED_JUDGE], judge.NOT_SAMPLED)

  def test_alias_collision_refused(self):
    judge.check_resolved_version("gemma-4-31b-it", "gemma-4-31b-it")
    with self.assertRaises(judge.PanelCollisionError):
      judge.check_resolved_version("gemini-pro-latest",
                                   "gemini-3.1-pro-preview")
    with self.assertRaises(judge.PanelCollisionError):
      judge.check_resolved_version("gemma-4-31b-it",
                                   "models/gemini-3.1-pro-preview")
    judge.RESOLVED_VERSIONS.clear()
    self.assertNotEqual(judge.TIEBREAK_JUDGE, "gemini-pro-latest")

  def test_pack_tool_output_withheld(self):
    r = _rollout()
    turn = r.sessions[0].turns[0]
    turn.tool_calls.append(schema.ToolCall(
        name="run_command", args={"command": "bash create-new-feature.sh x"},
        result_preview='{"BRANCH_NAME": "001-x", "SPEC_FILE": "specs/x"}'))
    r.action_log.append(schema.Action(
        session=0, turn=0, step=3, type="run_command",
        command="bash create-new-feature.sh x", executed=True,
        source="pack_tool"))
    t = judge.render_transcript(r)
    self.assertNotIn("BRANCH_NAME", t)
    self.assertIn("content omitted", t)

  def test_host_audit(self):
    p, v = "/tmp/x/prompt.txt", "/tmp/x/verdict.json"
    ok = [
        json.dumps({"type": "USER_INPUT"}),
        json.dumps({"type": "PLANNER_RESPONSE", "tool_calls": [
            {"name": "read_file", "args": {"Path": json.dumps(p)}}]}),
        json.dumps({"type": "PLANNER_RESPONSE", "tool_calls": [
            {"name": "write_file", "args": {"TargetFile": v, "Content": "{}"}}
        ]}),
    ]
    self.assertIsNone(judge.audit_host_transcript(ok, p, v))
    peek = ok + [json.dumps({"type": "PLANNER_RESPONSE", "tool_calls": [
        {"name": "read_file",
         "args": {"Path": "/x/results/run/rollouts.jsonl"}}]})]
    self.assertIn("disallowed", judge.audit_host_transcript(peek, p, v))
    cmd = ok + [json.dumps({"type": "PLANNER_RESPONSE", "tool_calls": [
        {"name": "run_command", "args": {"CommandLine": f"cat {p}"}}]})]
    self.assertIsNotNone(judge.audit_host_transcript(cmd, p, v))

  def test_subagent_router_resolves_opus_5_5_low(self):
    from unittest import mock  # pylint: disable=g-import-not-at-top

    self.assertEqual(judge.PRIMARY_JUDGES[1], "opus-5.5-low")
    self.assertEqual(judge.SUBSAMPLED_JUDGE, "opus-5.5-low")
    fake_cfg = mock.MagicMock()
    fake_cfg.load.return_value = {"quota_floor": 0.02}
    fake_models = mock.MagicMock()
    fake_models.catalog.return_value = {}
    fake_models.select.return_value = {
        "id": "opus-5.5-low",
        "enum": "MODEL_PLACEHOLDER_M369",
        "family": "claude",
        "quota": 0.85,
    }
    with mock.patch.object(
        judge, "_load_mms", return_value=(fake_cfg, fake_models, None)
    ):
      sel, enum_id = judge.resolve_host_judge_model("opus-5.5-low")
      self.assertEqual(sel, "opus-5.5-low")
      self.assertEqual(enum_id, "MODEL_PLACEHOLDER_M369")
      self.assertIn("opus-5.5-low", judge.RESOLVED_VERSIONS)
      judge.RESOLVED_VERSIONS.clear()

  def test_subagent_router_falls_back_on_drained_claude_bucket(self):
    from unittest import mock  # pylint: disable=g-import-not-at-top

    fake_cfg = mock.MagicMock()
    fake_cfg.load.return_value = {"quota_floor": 0.02}
    fake_models = mock.MagicMock()
    fake_models.catalog.return_value = {}
    fake_models.select.side_effect = [
        {
            "id": "opus-5.5-low",
            "enum": "MODEL_PLACEHOLDER_M369",
            "family": "claude",
            "quota": 0.0,
        },
        {
            "id": "opus-5.5-medium",
            "enum": "MODEL_PLACEHOLDER_M370",
            "family": "claude",
            "quota": 1.0,
        },
    ]
    with mock.patch.object(
        judge, "_load_mms", return_value=(fake_cfg, fake_models, None)
    ):
      sel, enum_id = judge.resolve_host_judge_model("opus-5.5-low")
      self.assertEqual(sel, "opus-5.5-medium")
      self.assertEqual(enum_id, "MODEL_PLACEHOLDER_M370")
      self.assertEqual(
          judge.RESOLVED_VERSIONS.get("opus-5.5-low"),
          "opus-5.5-medium:MODEL_PLACEHOLDER_M370",
      )
      self.assertEqual(fake_models.select.call_count, 2)
      self.assertIn(
          "[family:claude]", fake_models.select.call_args_list[1].args[1]
      )
      judge.RESOLVED_VERSIONS.clear()


if __name__ == "__main__":
  unittest.main()
