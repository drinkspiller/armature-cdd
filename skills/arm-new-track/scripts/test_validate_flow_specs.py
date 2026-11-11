#!/usr/bin/env python3
"""Unit tests for validate_flow_specs.py (ADR 0022)."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_flow_specs as vfs  # noqa: E402

VALID_SPEC = """---
status: approved
---

# Specification: Export STL Flow

## Requirements

- REQ-01: Export watertight STL from inspector drawer.

## User Flows

**Goal:** Hardware engineer wants to export a printable STL without blocking the 3D viewport.
**Covers:** REQ-01

### Step 1: Trigger Export

- **What they want:** Start STL export from the active model.
- **What they see:** Export action inside the inspector drawer alongside mesh validity status.
- **What they do:** Selects Export STL.
- **What happens:** System runs printability check and streams binary STL.

## Edge Cases

| State | Behavior |
| :--- | :--- |
| Empty | Disabled trigger with prompt to generate a model first. |
| Loading | Inline progress label and Cancel action during 8s check. |
| Partial | Thin-wall warning still permits draft STL download. |
| Error | Timeout banner offers Retry without losing camera pose. |
"""


class ValidateFlowSpecsTest(unittest.TestCase):
  """Tests Flow Spec Altitude linting and DESIGN.md token drift audits."""

  def test_valid_flow_spec_passes_with_zero_warnings(self):
    """Tests that a complete Flow Spec passes with zero errors or warnings."""
    res = vfs.lint_flow_spec_text(VALID_SPEC, require_flows=True)
    self.assertTrue(res["ok"], res)
    self.assertEqual(res["errors"], [])
    self.assertEqual(res["warnings"], [])

  def test_colon_outside_bold_and_sublist_numbers_and_numbered_h2_pass(self):
    """Tests numbered H2 sections, numbered sublists, and colon placement."""
    spec = """# Spec
## 1. Requirements
- REQ-01: Export STL.
## 2. User Flows
**Covers**: REQ-01
#### Step 1: Trigger Export
1. **What they want**: Download STL for Invoice #1042.
2. **What they see**: Export button with status.
3. **What they do**: Clicks Export.
4. **What happens**: Streams binary STL.
## Edge Cases
Empty, Loading, Partial, Error all handled.
"""
    res = vfs.lint_flow_spec_text(spec, require_flows=True)
    self.assertTrue(res["ok"], res)
    self.assertEqual(res["warnings"], [])

  def test_bulleted_flow_block_passes(self):
    """Tests bulleted Flow headings and parenthesized step labels."""
    spec = """# Spec
## Requirements
- R1: Preview flagged invoice #1042.
## User Flows
- **Flow 1: Review Invoice #1042**
  - **Covers:** R1
  - **What they want:** Check status of Invoice #1042.
  - **What they see:** Summary banner without raw styling tokens.
  - **What they do:** Opens detail drawer.
  - **What happens:** Shows line items and approval controls.
### Flow 2: Parenthesized Step Labels
- **Covers:** R1
- **Step 1 (What they want):** Trigger check.
- **Step 2 (What they see):** Progress banner.
- **Step 3 (What they do):** Wait for completion.
- **Step 4 (What happens):** Displays clean result.
## Edge Cases
Empty, Loading, Partial, Error handled cleanly.
"""
    res = vfs.lint_flow_spec_text(spec, require_flows=True)
    self.assertTrue(res["ok"], res)
    self.assertEqual(res["warnings"], [])

  def test_catches_altitude_leak_on_do_happens_and_wrapped_lines(self):
    """Tests detection of px/hex literals on wrapped flow step lines."""
    bad = VALID_SPEC.replace(
        "System runs printability check and streams binary STL.",
        "System runs check\n  and slides a 360px drawer with #7cc4fa border.",
    )
    res = vfs.lint_flow_spec_text(bad, require_flows=True)
    self.assertFalse(res["ok"])
    codes = [e["code"] for e in res["errors"]]
    self.assertEqual(codes.count("ALTITUDE_LEAK"), 2)

  def test_catches_incomplete_4q_step(self):
    bad = VALID_SPEC.replace("- **What they do:** Selects Export STL.\n", "")
    res = vfs.lint_flow_spec_text(bad, require_flows=True)
    self.assertFalse(res["ok"])
    self.assertEqual(res["errors"][0]["code"], "INCOMPLETE_FLOW_STEP")
    self.assertIn("Do", res["errors"][0]["message"])

  def test_catches_unknown_requirement_id_and_warns_covers_none(self):
    bad = VALID_SPEC.replace("**Covers:** REQ-01", "**Covers:** REQ-99")
    res = vfs.lint_flow_spec_text(bad, require_flows=True)
    self.assertFalse(res["ok"])
    self.assertEqual(res["errors"][0]["code"], "UNKNOWN_COVERAGE_ID")

    none_cov = VALID_SPEC.replace("**Covers:** REQ-01", "**Covers:** none")
    res2 = vfs.lint_flow_spec_text(none_cov, require_flows=True)
    self.assertTrue(res2["ok"])
    self.assertEqual(res2["warnings"][0]["code"], "MISSING_COVERS")

  def test_warns_on_missing_ui_stack_state(self):
    partial_missing = VALID_SPEC.replace(
        "| Partial | Thin-wall warning still permits draft STL download. |\n",
        "",
    )
    res = vfs.lint_flow_spec_text(partial_missing, require_flows=True)
    self.assertTrue(res["ok"])
    self.assertEqual(len(res["warnings"]), 1)
    self.assertIn("Partial", res["warnings"][0]["message"])

  def test_non_ui_spec_skips_when_not_required(self):
    non_ui = (
        "# Specification: Backend Worker\n\n## Requirements\n- REQ-01: Run"
        " job.\n"
    )
    self.assertTrue(vfs.lint_flow_spec_text(non_ui, require_flows=False)["ok"])
    self.assertFalse(vfs.lint_flow_spec_text(non_ui, require_flows=True)["ok"])

  def test_token_drift_handles_timestamps_4digit_hex_and_ignores_anchors(self):
    """Tests token drift diff parsing and non-color anchor/comment filtering."""
    design_md = "--color-surface: #161b24\n--color-glass: #ffffffff\n"
    diff = (
        "--- a/src/ui/Drawer.tsx\tThu Nov 11 10:00:00 2026 +0000\n"
        "+++ b/src/ui/Drawer.tsx\tThu Nov 11 10:01:00 2026 +0000\n"
        "@@ -1,2 +1,6 @@\n"
        "+const bg = '#161b24';\n"
        "+const glass = '#ffff';\n"
        "+// Bug #1234 comment ignored\n"
        "+const rogue = '#7c3aed';\n"
        "+++ b/src/ui/index.html\tThu Nov 11 10:01:00 2026 +0000\n"
        '+<a href="#fade">Jump</a>\n'
        "+const sel = document.querySelector('#dead');\n"
    )
    res = vfs.audit_design_token_drift(diff, design_md)
    self.assertFalse(res["ok"])
    self.assertEqual(len(res["findings"]), 1)
    self.assertEqual(res["findings"][0]["hex"], "#7c3aed")

  def test_cli_modes_and_missing_file_exit_code(self):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as tf:
      tf.write(VALID_SPEC)
      spec_path = tf.name
    try:
      self.assertEqual(vfs.main([spec_path, "--require-flows", "--json"]), 0)
      self.assertEqual(vfs.main(["/nonexistent/spec.md"]), 2)
    finally:
      os.unlink(spec_path)


if __name__ == "__main__":
  unittest.main()
