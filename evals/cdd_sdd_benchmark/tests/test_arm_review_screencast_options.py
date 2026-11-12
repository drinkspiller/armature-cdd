"""Unit tests for /arm-review screencast mode options and plain-language rules."""

import json
import os
import re
import unittest

BENCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARMATURE_ROOT = os.path.abspath(os.path.join(BENCH_DIR, "..", ".."))


class ArmReviewScreencastOptionsTest(unittest.TestCase):
  """Verifies /arm-review mode gate options, plain-language rules, and versions."""

  def test_arm_review_mode_gate_includes_automated_screencast_option(self):
    """Checks Review Mode Gate ask_question options and Path C wiring."""
    skill_path = os.path.join(
        ARMATURE_ROOT, "skills", "arm-review", "SKILL.md"
    )
    with open(skill_path, encoding="utf-8") as f:
      content = f.read()

    self.assertIn("Full Review + Automated Screencast Testing", content)
    self.assertIn("--automated", content)
    self.assertIn("Path C: Automated Scenario Testing with Screencasts", content)
    self.assertIn("instructional_reel.run_reel", content)

  def test_version_bump_parity_across_manifest_installers_and_changelog(self):
    """Verifies install.sh, install.bat, plugin.json, and CHANGELOG.md match."""
    with open(os.path.join(ARMATURE_ROOT, "plugin.json"), encoding="utf-8") as f:
      plugin_version = json.load(f)["version"]

    with open(os.path.join(ARMATURE_ROOT, "install.sh"), encoding="utf-8") as f:
      m_sh = re.search(r'^VERSION="([^"]+)"', f.read(), re.M)
    self.assertIsNotNone(m_sh)
    self.assertEqual(m_sh.group(1), plugin_version)

    with open(os.path.join(ARMATURE_ROOT, "install.bat"), encoding="utf-8") as f:
      m_bat = re.search(r'^set "VERSION=([^"]+)"', f.read(), re.M)
    self.assertIsNotNone(m_bat)
    self.assertEqual(m_bat.group(1), plugin_version)

    with open(
        os.path.join(ARMATURE_ROOT, "CHANGELOG.md"), encoding="utf-8"
    ) as f:
      self.assertIn(f"## [{plugin_version}]", f.read())

  def test_val_review_format_includes_screencast_mode_gate_task(self):
    """Verifies VAL_05_ARM_REVIEW_MODE_GATE_SCREENCAST is valid JSONL."""
    val_path = os.path.join(
        ARMATURE_ROOT, "evals", "skillopt", "tasks", "val_review_format.jsonl"
    )
    with open(val_path, encoding="utf-8") as f:
      tasks = [json.loads(line) for line in f if line.strip()]
    ids = {t["id"] for t in tasks}
    self.assertIn("VAL_05_ARM_REVIEW_MODE_GATE_SCREENCAST", ids)

  def test_plain_language_guardrails_in_rules_and_skills(self):
    """Verifies behavior-first and visible-on-screen plain-language rules."""
    with open(
        os.path.join(ARMATURE_ROOT, "rules", "armature_protocol.md"),
        encoding="utf-8",
    ) as f:
      self.assertIn("behavior-first", f.read())

    with open(
        os.path.join(
            ARMATURE_ROOT, "skills", "arm-review", "references", "screencast_adapter.md"
        ),
        encoding="utf-8",
    ) as f:
      self.assertIn("Visible-on-Screen Plain Language", f.read())
