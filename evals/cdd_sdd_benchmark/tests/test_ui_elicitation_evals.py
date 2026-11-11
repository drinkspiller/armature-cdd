"""Unit tests for the ADR 0021 UI/UX elicitation SkillOpt eval suite."""

import os
import sys
import unittest

BENCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARMATURE_ROOT = os.path.abspath(os.path.join(BENCH_DIR, "..", ".."))
SKILLOPT_DIR = os.path.join(ARMATURE_ROOT, "evals", "skillopt")

sys.path.insert(0, SKILLOPT_DIR)
import run_ui_elicitation_opt as uio  # noqa: E402


class UiElicitationEvalSuiteTest(unittest.TestCase):
  """Tests SkillOpt UI elicitation schema disjointness and invariants."""

  def test_train_and_val_schemas_are_valid_and_disjoint(self):
    """Tests that train and val splits have 5 disjoint tasks each."""
    train_tasks = uio.load_tasks(uio.TRAIN_PATH)
    val_tasks = uio.load_tasks(uio.VAL_PATH)
    uio.check_disjoint(train_tasks, val_tasks)
    self.assertEqual(len(train_tasks), 5)
    self.assertEqual(len(val_tasks), 5)

  def test_greenfield_invariant_blocks_prompt_echo_and_hex_leaks(self):
    """Tests prompt-echo rejection, hex/px leak rejection, and clean pass."""
    val_tasks = {t["id"]: t for t in uio.load_tasks(uio.VAL_PATH)}
    task = val_tasks["UI_VAL_01"]

    echo_calls = [
        {
            "name": "write_to_file",
            "args": {
                "TargetFile": "spec.md",
                "CodeContent": "---\nstatus: draft\n---\n",
            },
        },
        {
            "name": "ask_question",
            "args": {
                "questions": [{
                    "question": "Which database backs IncidentTimeline?",
                    "options": ["Postgres", "SQLite"],
                }]
            },
        },
    ]
    res_echo = uio.evaluate_invariants(
        task, "# Incident Timeline Triage", echo_calls
    )
    self.assertFalse(res_echo["asks_ux_pattern_or_behavior_not_hex"])

    leak_calls = [
        {
            "name": "write_to_file",
            "args": {
                "TargetFile": "spec.md",
                "CodeContent": "---\nstatus: draft\n---\n",
            },
        },
        {
            "name": "ask_question",
            "args": {
                "questions": [{
                    "question": "How should triage open?",
                    "options": ["Side drawer", "Modal"],
                }]
            },
        },
    ]
    res_leak = uio.evaluate_invariants(
        task, "Use a #f00 drawer with 2rem gap.", leak_calls
    )
    self.assertFalse(res_leak["asks_ux_pattern_or_behavior_not_hex"])

    good_calls = [
        {
            "name": "write_to_file",
            "args": {
                "TargetFile": "spec.md",
                "CodeContent": "---\nstatus: draft\n---\n",
            },
        },
        {
            "name": "ask_question",
            "args": {
                "questions": [{
                    "question": "How should the timeline triage view open?",
                    "options": ["(Recommended) Side drawer", "Full-page route"],
                }]
            },
        },
    ]
    res_good = uio.evaluate_invariants(
        task, "# Incident Timeline Triage", good_calls
    )
    self.assertTrue(all(res_good.values()), res_good)

  def test_day2_step6_invariant_validates_flow_linter(self):
    """Tests Day-2 Step 6 approval validation against validate_flow_specs."""
    val_tasks = {t["id"]: t for t in uio.load_tasks(uio.VAL_PATH)}
    task = val_tasks["UI_VAL_02"]
    good_spec = """---
status: approved
---
# Specification: Plate QC Inspector

## Requirements
- REQ-01: Split-pane plate QC inspector.

## User Flows
**Goal:** Lab analyst wants to inspect flagged wells alongside the heatmap.
**Covers:** REQ-01

### Step 1: Inspect Flagged Well
- **What they want:** Review assay score without losing heatmap context.
- **What they see:** Split-pane drawer showing flagged well details using `--tone-canvas` and `--tone-primary`.
- **What they do:** Selects flagged well.
- **What happens:** Assay score loads within 4s with Cancel option.

## Edge Cases
| State | Behavior |
| :--- | :--- |
| Empty | Shows 'No flagged wells'. |
| Loading | Inline progress and Cancel. |
| Partial | Low-confidence badge with CSV export. |
| Error | Retry action preserves heatmap zoom. |
"""
    good_calls = [
        {
            "name": "write_to_file",
            "args": {
                "TargetFile": "armature/tracks/plate-qc-inspector/spec.md",
                "CodeContent": good_spec,
            },
        },
        {
            "name": "write_to_file",
            "args": {
                "TargetFile": (
                    "armature/tracks/plate-qc-inspector/manual_testing.md"
                ),
                "CodeContent": "# Manual Testing",
            },
        },
        {
            "name": "ask_question",
            "args": {
                "questions": [{
                    "question": "Approve spec.md and manual_testing.md?",
                    "options": ["(Recommended) Approve", "Revise"],
                }]
            },
        },
    ]
    res = uio.evaluate_invariants(task, "### Convergence Summary", good_calls)
    self.assertTrue(all(res.values()), res)

  def test_non_ui_bypass_review_and_drift_invariants(self):
    """Tests non-UI UI-skip, arm-review Deliberate/Drift, and arm-drift checks."""
    val_tasks = {t["id"]: t for t in uio.load_tasks(uio.VAL_PATH)}
    non_ui = val_tasks["UI_VAL_03"]
    res_leak = uio.evaluate_invariants(
        non_ui,
        "Let's pick a DESIGN.md palette first.",
        [
            {
                "name": "write_to_file",
                "args": {
                    "TargetFile": "spec.md",
                    "CodeContent": "status: draft",
                },
            },
            {
                "name": "ask_question",
                "args": {
                    "questions": [
                        {"question": "Pick style?", "options": ["A", "B"]}
                    ]
                },
            },
        ],
    )
    self.assertFalse(res_leak["skips_ui_flow_and_look"])

    review_task = val_tasks["UI_VAL_04"]
    res_review = uio.evaluate_invariants(
        review_task,
        "Detected Token Drift: #ef4444 is not in DESIGN.md.",
        [{
            "name": "ask_question",
            "args": {
                "questions": [{
                    "question": "Classify moved Normalize Peaks control:",
                    "options": [
                        "(Recommended) Deliberate improvement -> amend spec.md",
                        "Drift -> revert to Track Options dialog",
                    ],
                }]
            },
        }],
    )
    self.assertTrue(all(res_review.values()), res_review)

    drift_task = val_tasks["UI_VAL_05"]
    res_drift = uio.evaluate_invariants(
        drift_task,
        "[ERROR] ALTITUDE_LEAK in spec.md ## User Flows; [WARNING] Token Drift:"
        " #eab308 not in DESIGN.md.",
        [],
    )
    self.assertTrue(all(res_drift.values()), res_drift)


if __name__ == "__main__":
  unittest.main()
