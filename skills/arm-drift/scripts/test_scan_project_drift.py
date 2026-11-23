#!/usr/bin/env python3
"""Unit tests for scan_project_drift.py (ADR 0023)."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scan_project_drift as spd  # pylint: disable=g-import-not-at-top


class TestProjectRootDiscovery(unittest.TestCase):
  """Tests explicit and fallback owned directory parsing."""

  def test_parses_explicit_owned_project_directories_table(self) -> None:
    """Verifies explicit table rows normalize paths and kinds."""
    text = """# Tech Stack
## Owned Project Directories

| Path | Kind | Notes |
| :--- | :--- | :--- |
| `packages/web` | code | Frontend UI |
| `docs` | docs | Engineering guides |
| `services/billing` | code | Backend |
"""
    roots = spd.parse_owned_project_directories(text)
    self.assertEqual(
        [(r.path, r.kind) for r in roots],
        [
            ("packages/web", "code"),
            ("docs", "docs"),
            ("services/billing", "code"),
        ],
    )

  def test_legacy_fences_only_parse_deprecated_column(self) -> None:
    """Never fence the Modern Replacement column."""
    text = """# Tech Stack
## Legacy & Deprecated Boundaries

| Deprecated Path | Modern Replacement | Mode |
| :--- | :--- | :--- |
| `packages/legacy_portal/` | `packages/portal_v2/` | exclude |
| `src/legacy_billing/` | `src/billing_v2/` | exclude |
"""
    fences = spd.parse_legacy_fences(text)
    self.assertEqual(
        fences,
        ["packages/legacy_portal", "src/legacy_billing"],
    )

  def test_fallback_excludes_legacy_fences_and_external_paths(self) -> None:
    """Verifies fallback inference skips legacy fences and vendor dirs."""
    with tempfile.TemporaryDirectory() as tmp:
      repo = pathlib.Path(tmp)
      (repo / "app/client").mkdir(parents=True)
      (repo / "app/docs").mkdir(parents=True)
      (repo / "app/legacy_old").mkdir(parents=True)
      (repo / "vendor/shared/demo").mkdir(parents=True)
      arm = repo / "app/armature"
      arm.mkdir(parents=True)
      (arm / "tech-stack.md").write_text(
          """# Tech Stack
## 1. Frontend (`/app/client`)
Active UI under `/app/client/main.ts` with `/vendor/shared/demo`.
## 2. Legacy & Deprecated Boundaries
* `/app/legacy_old/` -> `/app/client/`: Retired folder.
""",
          encoding="utf-8",
      )
      roots, source, fences = spd.discover_project_roots(arm, repo)
      self.assertEqual(source, "inferred")
      self.assertIn("app/legacy_old", fences)
      self.assertNotIn("app/client", fences)
      root_paths = [r.path for r in roots]
      self.assertIn("app", root_paths)
      self.assertIn("app/docs", root_paths)
      self.assertNotIn("app/legacy_old", root_paths)
      self.assertNotIn("vendor/shared/demo", root_paths)


class TestLinkAndHeaderHelpers(unittest.TestCase):
  """Tests link resolution, normalization, and doc header detection."""

  def test_normalize_rel_path_strips_anchors_and_lines(self) -> None:
    """Verifies normalization strips leading slashes and line suffixes."""
    self.assertEqual(spd.normalize_rel_path("/src/app.py:42"), "src/app.py")
    self.assertEqual(spd.normalize_rel_path("./docs/api.md#L10"), "docs/api.md")

  def test_stale_doc_links_resolve_relative_subfolders_and_skip_code(
      self,
  ) -> None:
    """Resolves relative subfolder links and skips code spans/placeholders."""
    with tempfile.TemporaryDirectory() as tmp:
      repo = pathlib.Path(tmp)
      (repo / "docs/guides").mkdir(parents=True)
      (repo / "src").mkdir(parents=True)
      (repo / "docs/guides/setup.md").write_text("# Setup\n", encoding="utf-8")
      index_md = repo / "docs/index.md"
      index_md.write_text(
          """# Docs
- [Setup](guides/setup.md)
- [Broken Root](/src/missing.py)
- [Placeholder](./tracks/<track_id>/)
- Inline code: `[fake](src/not_real_inline.py)`

```markdown
[fenced](src/not_real_fenced.py)
```
""",
          encoding="utf-8",
      )
      stale = spd.find_stale_doc_links(repo, ["docs", "src"], [index_md])
      self.assertEqual(
          stale,
          [{"doc": "docs/index.md", "missing_target": "src/missing.py"}],
      )

  def test_has_code_doc_header_accepts_raw_docstrings_and_guards(self) -> None:
    """Accepts raw docstrings, bare # borders, proto syntax, C++ guards."""
    with tempfile.TemporaryDirectory() as tmp:
      root = pathlib.Path(tmp)
      py_raw = root / "raw.py"
      py_raw.write_text('r"""Raw docstring."""\n', encoding="utf-8")
      sh_border = root / "border.sh"
      sh_border.write_text("#!/bin/bash\n#\n# Script.\n", encoding="utf-8")
      proto_file = root / "svc.proto"
      proto_file.write_text(
          'syntax = "proto3";\n// Service.\n', encoding="utf-8"
      )
      cpp_hdr = root / "hdr.h"
      cpp_hdr.write_text("#pragma once\n// Header.\n", encoding="utf-8")
      missing = root / "bare.py"
      missing.write_text("def x():\n  return 1\n", encoding="utf-8")

      self.assertTrue(spd.has_code_doc_header(py_raw))
      self.assertTrue(spd.has_code_doc_header(sh_border))
      self.assertTrue(spd.has_code_doc_header(proto_file))
      self.assertTrue(spd.has_code_doc_header(cpp_hdr))
      self.assertFalse(spd.has_code_doc_header(missing))


class TestGitWatermarkAndTeammateDrift(unittest.TestCase):
  """End-to-end test in a temporary git repo simulating teammate commits."""

  def _git(self, repo: pathlib.Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()

  def test_distinguishes_armature_vs_non_armature_commits(self) -> None:
    """Verifies compact watermark and Git pathspec separation."""
    with tempfile.TemporaryDirectory() as tmp:
      repo = pathlib.Path(tmp)
      self._git(repo, "init")
      self._git(repo, "config", "user.email", "dev@example.com")
      self._git(repo, "config", "user.name", "Initial Dev")

      (repo / "src").mkdir()
      (repo / "docs").mkdir()
      arm = repo / "armature"
      arm.mkdir()
      (repo / "src/app.py").write_text(
          '"""Main application module."""\n', encoding="utf-8"
      )
      (repo / "docs/index.md").write_text(
          "# Docs\n- [app.py](../src/app.py)\n- [old.py](../src/deleted.py)\n",
          encoding="utf-8",
      )
      (arm / "tech-stack.md").write_text(
          """# Tech Stack
## Owned Project Directories
| Path | Kind | Notes |
| :--- | :--- | :--- |
| `src` | code | Application source |
| `docs` | docs | Engineering docs |
""",
          encoding="utf-8",
      )
      (arm / ".api_surface_cache.json").write_text(
          json.dumps({"symbols": ["app.main"]}) + "\n", encoding="utf-8"
      )
      self._git(repo, "add", ".")
      self._git(repo, "commit", "-m", "initial commit")
      first_sha = self._git(repo, "rev-parse", "HEAD")

      spd.write_watermark(
          arm / ".api_surface_cache.json",
          vcs="git",
          revision=first_sha,
          roots=[
              spd.ProjectRoot("src", "code"),
              spd.ProjectRoot("docs", "docs"),
          ],
      )
      cache_data = json.loads(
          (arm / ".api_surface_cache.json").read_text(encoding="utf-8")
      )
      self.assertEqual(cache_data["symbols"], ["app.main"])
      self.assertNotIn("known_files", cache_data["drift_watermark"])
      self.assertNotIn("known_docs", cache_data["drift_watermark"])

      # Commit 1: Armature-managed commit (touches src/ AND armature/).
      (repo / "src/tracked.py").write_text(
          '"""Tracked feature."""\n', encoding="utf-8"
      )
      (arm / "terms.md").write_text(
          "- `tracked.py`: tracked\n", encoding="utf-8"
      )
      self._git(repo, "add", "src/tracked.py", "armature/terms.md")
      self._git(repo, "commit", "-m", "armature-managed feature")

      # Commit 2: Teammate lands code + unindexed doc WITHOUT armature/.
      (repo / "src/billing.py").write_text(
          "def charge(amount: int) -> int:\n  return amount\n",
          encoding="utf-8",
      )
      (repo / "docs/billing.md").write_text("# Billing\n", encoding="utf-8")
      self._git(repo, "add", "src/billing.py", "docs/billing.md")
      self._git(repo, "commit", "-m", "teammate adds billing without armature")

      result = spd.scan_project_drift(arm, repo)
      self.assertEqual(result.vcs, "git")
      self.assertEqual(result.watermark_revision, first_sha)
      self.assertEqual(len(result.external_non_armature_commits), 1)
      self.assertEqual(
          result.external_non_armature_commits[0].subject,
          "teammate adds billing without armature",
      )
      self.assertIn("src/billing.py", result.new_files_since_watermark)
      self.assertIn("docs/billing.md", result.unindexed_docs)
      self.assertIn("src/billing.py", result.undocumented_code_files)
      self.assertIn("src/billing.py", result.missing_code_doc_headers)
      self.assertEqual(
          result.stale_doc_references,
          [{"doc": "docs/index.md", "missing_target": "src/deleted.py"}],
      )


if __name__ == "__main__":
  unittest.main()
