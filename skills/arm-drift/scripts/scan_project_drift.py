#!/usr/bin/env python3
"""Multi-Directory Project Drift & Teammate Change Scanner (ADR 0023).

Discovers all owned code and documentation directories for an Armature project,
tracks a compact commit watermark in `armature/.api_surface_cache.json`, finds
changes landed by teammates outside Armature, and identifies undocumented code,
unindexed docs, and stale doc links. Zero third-party dependencies.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any

_CODE_EXTS = frozenset({
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".kt",
    ".java",
    ".go",
    ".rs",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".proto",
    ".sh",
})
_TEST_MARKERS = ("_test.", ".test.", ".spec.", "test_", "Test.", "Tests.")
_IGNORED_DIRS = frozenset({
    ".git",
    ".hg",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "target",
    "armature",
    "conductor",
})
_EXTERNAL_PREFIXES = (
    "third_party",
    "vendor",
    "node_modules",
)
_PATH_TOKEN_RE = re.compile(
    r"(?:(?://|/)([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+))"
)
_FENCED_CODE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#\s]+)")
_DOC_INDEX_NAMES = frozenset(
    {"index.md", "sitemap.md", "_sitemap.md", "readme.md"}
)
_DOC_HEADER_SKIP_PREFIXES = (
    "#!",
    "package ",
    "from __future__",
    "import ",
    "syntax =",
    "edition =",
    "#ifndef ",
    "#define ",
    "#pragma once",
)
_DOC_HEADER_START_PREFIXES = (
    '"""',
    "'''",
    'r"""',
    "r'''",
    'u"""',
    "u'''",
    'f"""',
    "f'''",
    "/**",
    "/*",
    "//",
    "#",
)


@dataclasses.dataclass(frozen=True)
class ProjectRoot:
  """Represents a normalized owned project directory."""

  path: str
  kind: str  # "code" | "docs" | "config" | "tests"
  source: str = "declared"


@dataclasses.dataclass(frozen=True)
class ExternalCommit:
  """Represents a submitted commit that bypassed Armature."""

  revision: str
  author: str
  date: str
  subject: str
  files: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class DriftScanResult:
  """Structured multi-directory drift scan report."""

  vcs: str
  head_revision: str
  watermark_revision: str | None
  full_scan: bool
  roots_source: str
  project_roots: list[ProjectRoot]
  external_non_armature_commits: list[ExternalCommit]
  new_files_since_watermark: list[str]
  deleted_files_since_watermark: list[str]
  unindexed_docs: list[str]
  undocumented_code_files: list[str]
  missing_code_doc_headers: list[str]
  stale_doc_references: list[dict[str, str]]
  total_code_files: int
  total_doc_files: int
  warnings: list[str] = dataclasses.field(default_factory=list)


def _extract_section(text: str, heading_pattern: str) -> str:
  """Returns markdown lines under the first matching level-2 heading."""
  lines = text.splitlines()
  in_section = False
  captured: list[str] = []
  header_re = re.compile(
      rf"^##\s+(?:\d+(?:\.\d+)*\.?\s+)?{heading_pattern}\b", re.IGNORECASE
  )
  for line in lines:
    if re.match(r"^##\s+", line):
      if header_re.match(line):
        in_section = True
        continue
      if in_section:
        break
    elif in_section:
      captured.append(line)
  return "\n".join(captured)


def normalize_rel_path(raw: str) -> str:
  """Normalizes repo-relative path tokens to a clean relative path."""
  cleaned = raw.strip().strip("`'\"")
  for prefix in ("//", "./"):
    if cleaned.startswith(prefix):
      cleaned = cleaned[len(prefix) :]
      break
  cleaned = cleaned.split("#", 1)[0].split("?", 1)[0].split(":", 1)[0]
  cleaned = cleaned.lstrip("/").rstrip("/")
  if cleaned.endswith("/..."):
    cleaned = cleaned[:-4]
  return cleaned


def _classify_kind(rel_path: str, explicit_kind: str = "") -> str:
  """Classifies a project directory as docs, tests, config, or code."""
  lowered = explicit_kind.strip().lower()
  if lowered in ("code", "docs", "config", "tests"):
    return lowered
  parts = set(rel_path.lower().split("/"))
  if parts & {"docs", "doc"} or rel_path.lower().endswith(".md"):
    return "docs"
  if parts & {"tests", "test", "__tests__"}:
    return "tests"
  return "code"


def parse_legacy_fences(tech_stack_text: str) -> list[str]:
  """Extracts deprecated paths only from column 0 or bullet heads."""
  section = _extract_section(
      tech_stack_text, r"Legacy\s*&\s*Deprecated\s+Boundaries"
  )
  if not section:
    return []
  fences: list[str] = []
  for line in section.splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("<!--"):
      continue
    candidate = ""
    if stripped.startswith("|"):
      cells = [c.strip() for c in stripped.strip("|").split("|")]
      if not cells or set(cells[0]) <= {":", "-", " "}:
        continue
      if cells[0].lower() in ("deprecated path", "legacy path", "path"):
        continue
      match = re.search(r"`([^`]+)`", cells[0])
      candidate = match.group(1) if match else cells[0]
    elif stripped.startswith(("-", "*", ">")):
      head = re.split(r"(?:->|→|\breplaced by\b)", stripped, maxsplit=1)[0]
      match = re.search(r"`([^`]+)`", head)
      if match:
        candidate = match.group(1)
    norm = normalize_rel_path(candidate) if candidate else ""
    if norm and "/" in norm and norm not in fences:
      fences.append(norm)
  return fences


def parse_owned_project_directories(tech_stack_text: str) -> list[ProjectRoot]:
  """Parses explicit `## Owned Project Directories` in tech-stack.md."""
  section = _extract_section(
      tech_stack_text, r"(?:Owned\s+)?Project\s+Directories"
  )
  if not section:
    return []
  roots: list[ProjectRoot] = []
  seen: set[str] = set()
  for line in section.splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("<!--"):
      continue
    if stripped.startswith("|"):
      cells = [c.strip() for c in stripped.strip("|").split("|")]
      if len(cells) < 2 or set(cells[0]) <= {":", "-", " "}:
        continue
      if cells[0].lower() in ("path", "directory", "root"):
        continue
      norm = normalize_rel_path(cells[0])
      if norm and norm not in seen:
        seen.add(norm)
        roots.append(
            ProjectRoot(norm, _classify_kind(norm, cells[1]), "declared")
        )
    elif stripped.startswith(("-", "*")):
      match = re.search(r"`([^`]+)`", stripped)
      if not match:
        continue
      norm = normalize_rel_path(match.group(1))
      if norm and norm not in seen:
        seen.add(norm)
        roots.append(ProjectRoot(norm, _classify_kind(norm), "declared"))
  return roots


def _is_under_any(path: str, prefixes: list[str]) -> bool:
  """Returns True if path equals or is inside any prefix directory."""
  return any(path == p or path.startswith(f"{p}/") for p in prefixes)


def _collapse_nested_roots(roots: list[ProjectRoot]) -> list[ProjectRoot]:
  """Removes directories already covered by a parent root of the same kind."""
  by_path = {r.path: r for r in roots}
  ordered = sorted(
      by_path.values(), key=lambda r: (len(r.path.split("/")), r.path)
  )
  kept: list[ProjectRoot] = []
  for root in ordered:
    covered = any(
        k.kind == root.kind
        and (root.path == k.path or root.path.startswith(f"{k.path}/"))
        for k in kept
    )
    if not covered:
      kept.append(root)
  return kept


def discover_project_roots(
    armature_dir: pathlib.Path, repo_root: pathlib.Path
) -> tuple[list[ProjectRoot], str, list[str]]:
  """Returns (project_roots, source_kind, legacy_fences)."""
  tech_stack_path = armature_dir / "tech-stack.md"
  tech_stack_text = (
      tech_stack_path.read_text(encoding="utf-8")
      if tech_stack_path.is_file()
      else ""
  )
  legacy_fences = parse_legacy_fences(tech_stack_text)

  declared = parse_owned_project_directories(tech_stack_text)
  if declared:
    valid = [
        r
        for r in declared
        if (repo_root / r.path).exists()
        and not _is_under_any(r.path, legacy_fences)
    ]
    return valid, "declared", legacy_fences

  candidates: list[ProjectRoot] = []
  project_root = armature_dir.parent
  try:
    proj_rel = project_root.relative_to(repo_root).as_posix()
  except ValueError:
    proj_rel = ""
  if proj_rel and proj_rel != ".":
    candidates.append(ProjectRoot(proj_rel, "code", "inferred"))
    for doc_name in ("docs", "doc"):
      if (project_root / doc_name).is_dir():
        candidates.append(
            ProjectRoot(f"{proj_rel}/{doc_name}", "docs", "inferred")
        )
  else:
    for top in ("src", "app", "lib", "packages", "skills", "rules", "docs"):
      if (repo_root / top).is_dir():
        candidates.append(ProjectRoot(top, _classify_kind(top), "inferred"))

  non_legacy_text = tech_stack_text.split("## ", 1)[0]
  for chunk in re.split(r"(?m)^(?=##\s+)", tech_stack_text):
    if not re.match(r"^##\s+(?:\d+\.?\s+)?Legacy\s*&", chunk, re.IGNORECASE):
      non_legacy_text += "\n" + chunk
  for doc_name in ("index.md", "product.md"):
    doc_path = armature_dir / doc_name
    if doc_path.is_file():
      non_legacy_text += "\n" + doc_path.read_text(encoding="utf-8")

  for match in _PATH_TOKEN_RE.finditer(non_legacy_text):
    norm = normalize_rel_path(match.group(1))
    if not norm or _is_under_any(norm, list(_EXTERNAL_PREFIXES)):
      continue
    if _is_under_any(norm, legacy_fences):
      continue
    padded = f"/{norm}/"
    if "/armature/" in padded or "/conductor/" in padded:
      continue
    target = repo_root / norm
    if target.is_file():
      norm = str(pathlib.Path(norm).parent).replace("\\", "/")
      target = repo_root / norm
    if norm and norm != "." and target.is_dir():
      candidates.append(ProjectRoot(norm, _classify_kind(norm), "inferred"))

  return _collapse_nested_roots(candidates), "inferred", legacy_fences


def detect_vcs(repo_root: pathlib.Path) -> str:
  """Detects whether repo_root is a Git repo or plain directory."""
  if (repo_root / ".git").exists():
    return "git"
  return "none"


def _run_cmd(
    cmd: list[str], cwd: pathlib.Path, timeout: int = 12
) -> tuple[int, str, str]:
  """Runs a subprocess command safely with timeout."""
  try:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr
  except (OSError, subprocess.TimeoutExpired) as exc:
    return 1, "", str(exc)


def get_head_revision(repo_root: pathlib.Path, vcs: str) -> str:
  """Returns current HEAD commit SHA for Git repos."""
  if vcs == "git":
    code, out, _ = _run_cmd(["git", "rev-parse", "HEAD"], repo_root, timeout=8)
    if code == 0 and out.strip():
      return out.strip()
  return "unknown"


def list_files_in_root(
    repo_root: pathlib.Path,
    rel_root: str,
    vcs: str,
    legacy_fences: list[str],
) -> tuple[list[str], list[str]]:
  """Lists target code and doc files under rel_root."""
  warnings: list[str] = []
  if vcs == "git":
    files: set[str] = set()
    for extra in ([], ["--others", "--exclude-standard"]):
      code, out, err = _run_cmd(
          ["git", "ls-files", *extra, rel_root], repo_root, timeout=10
      )
      if code != 0:
        warnings.append(f"git ls-files failed for {rel_root}: {err.strip()}")
        continue
      for line in out.splitlines():
        rel = line.strip()
        if rel and not _is_under_any(rel, legacy_fences):
          if not any(part in _IGNORED_DIRS for part in pathlib.Path(rel).parts):
            files.add(rel)
    return sorted(files), warnings

  base = repo_root / rel_root
  if not base.is_dir():
    return [], warnings
  found: list[str] = []
  for current, dirs, filenames in os.walk(base):
    dirs[:] = [
        d
        for d in sorted(dirs)
        if d not in _IGNORED_DIRS
        and not _is_under_any(
            pathlib.Path(current, d).relative_to(repo_root).as_posix(),
            legacy_fences,
        )
    ]
    for name in sorted(filenames):
      rel = pathlib.Path(current, name).relative_to(repo_root).as_posix()
      if not _is_under_any(rel, legacy_fences):
        found.append(rel)
  return found, warnings


def parse_git_log_output(
    raw_output: str, armature_rel: str, root_paths: list[str]
) -> list[ExternalCommit]:
  """Parses git log --name-status and returns non-Armature commits."""
  commits: list[dict[str, Any]] = []
  current: dict[str, Any] | None = None
  for line in raw_output.splitlines():
    if line.startswith("__COMMIT__"):
      if current is not None:
        commits.append(current)
      parts = line[len("__COMMIT__") :].split("|", 3)
      if len(parts) == 4:
        current = {
            "revision": parts[0],
            "author": parts[1],
            "date": parts[2],
            "subject": parts[3],
            "files": [],
        }
    elif current is not None and "\t" in line:
      path = line.split("\t")[-1].strip()
      if path:
        current["files"].append(path)
  if current is not None:
    commits.append(current)

  external: list[ExternalCommit] = []
  arm_prefix = f"{armature_rel.rstrip('/')}/" if armature_rel else "armature/"
  for item in commits:
    touched_armature = any(f.startswith(arm_prefix) for f in item["files"])
    owned_files = [
        f
        for f in item["files"]
        if not f.startswith(arm_prefix) and _is_under_any(f, root_paths)
    ]
    if owned_files and not touched_armature:
      external.append(
          ExternalCommit(
              revision=item["revision"][:12],
              author=item["author"],
              date=item["date"],
              subject=item["subject"],
              files=owned_files,
          )
      )
  return external


def parse_git_diff_status(
    raw_output: str, legacy_fences: list[str]
) -> tuple[list[str], list[str]]:
  """Parses git diff --name-status into (added_files, deleted_files)."""
  added: list[str] = []
  deleted: list[str] = []
  for line in raw_output.splitlines():
    parts = line.split("\t")
    if len(parts) < 2:
      continue
    status = parts[0].strip()
    if status.startswith("R") and len(parts) >= 3:
      old_path, new_path = parts[1].strip(), parts[2].strip()
      if not _is_under_any(old_path, legacy_fences):
        deleted.append(old_path)
      if not _is_under_any(new_path, legacy_fences):
        added.append(new_path)
    elif status == "A":
      path = parts[1].strip()
      if not _is_under_any(path, legacy_fences):
        added.append(path)
    elif status == "D":
      path = parts[1].strip()
      if not _is_under_any(path, legacy_fences):
        deleted.append(path)
  return sorted(set(added)), sorted(set(deleted))


def scan_vcs_changes_since_watermark(
    repo_root: pathlib.Path,
    roots: list[ProjectRoot],
    armature_rel: str,
    vcs: str,
    since_rev: str | None,
    head_rev: str,
    legacy_fences: list[str],
) -> tuple[list[ExternalCommit], list[str], list[str], list[str]]:
  """Returns (external_commits, added_files, deleted_files, warnings)."""
  warnings: list[str] = []
  if not since_rev or since_rev == head_rev or not roots or vcs != "git":
    return [], [], [], warnings

  root_paths = [r.path for r in roots]
  log_paths = sorted(set(root_paths + [armature_rel]))
  cmd = [
      "git",
      "log",
      "--name-status",
      "--pretty=format:__COMMIT__%H|%an|%ad|%s",
      "--date=short",
      f"{since_rev}..HEAD",
      "--",
      *log_paths,
  ]
  code, out, err = _run_cmd(cmd, repo_root, timeout=15)
  if code != 0:
    warnings.append(f"git log since {since_rev} failed: {err.strip()}")
    return [], [], [], warnings
  external = parse_git_log_output(out, armature_rel, root_paths)
  diff_code, diff_out, diff_err = _run_cmd(
      ["git", "diff", "--name-status", f"{since_rev}..HEAD", "--", *root_paths],
      repo_root,
      timeout=15,
  )
  if diff_code != 0:
    warnings.append(f"git diff since {since_rev} failed: {diff_err.strip()}")
    return external, [], [], warnings
  added, deleted = parse_git_diff_status(diff_out, legacy_fences)
  return external, added, deleted, warnings


def has_code_doc_header(file_path: pathlib.Path) -> bool:
  """Checks whether a source file has a module docstring or file comment."""
  try:
    lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()[
        :25
    ]
  except OSError:
    return True
  for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith(_DOC_HEADER_SKIP_PREFIXES):
      continue
    if stripped.startswith(_DOC_HEADER_START_PREFIXES):
      return True
    return False
  return True


def _is_test_file(rel_path: str) -> bool:
  """Returns True when a file looks like a test file."""
  name = pathlib.Path(rel_path).name
  return (
      any(marker in name for marker in _TEST_MARKERS)
      or "/tests/" in f"/{rel_path}"
  )


def read_watermark(cache_path: pathlib.Path) -> dict[str, Any]:
  """Reads drift_watermark from .api_surface_cache.json if present."""
  if not cache_path.is_file():
    return {}
  try:
    data = json.loads(cache_path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return {}
  wm = data.get("drift_watermark")
  return wm if isinstance(wm, dict) else {}


def write_watermark(
    cache_path: pathlib.Path,
    vcs: str,
    revision: str,
    roots: list[ProjectRoot],
) -> None:
  """Updates compact drift_watermark in .api_surface_cache.json."""
  data: dict[str, Any] = {}
  if cache_path.is_file():
    try:
      loaded = json.loads(cache_path.read_text(encoding="utf-8"))
      if isinstance(loaded, dict):
        data = loaded
    except (OSError, json.JSONDecodeError):
      data = {}
  data["drift_watermark"] = {
      "vcs": vcs,
      "revision": revision,
      "audited_at": datetime.datetime.now(datetime.timezone.utc).strftime(
          "%Y-%m-%dT%H:%M:%SZ"
      ),
      "project_roots": [{"path": r.path, "kind": r.kind} for r in roots],
  }
  cache_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _collect_doc_corpus(
    repo_root: pathlib.Path,
    armature_dir: pathlib.Path,
    doc_files: list[str],
) -> tuple[str, list[pathlib.Path]]:
  """Reads all markdown docs in armature/ and owned docs roots."""
  paths: list[pathlib.Path] = []
  for md in sorted(armature_dir.glob("*.md")):
    paths.append(md)
  for sub in ("guidelines", "adr", "manual_testing"):
    sub_dir = armature_dir / sub
    if sub_dir.is_dir():
      paths.extend(sorted(sub_dir.glob("*.md")))
  for rel in doc_files:
    p = repo_root / rel
    if p.is_file() and p not in paths:
      paths.append(p)
  chunks: list[str] = []
  for p in paths:
    try:
      chunks.append(p.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
      continue
  return "\n".join(chunks), paths


def _find_unindexed_docs(
    repo_root: pathlib.Path,
    armature_dir: pathlib.Path,
    roots: list[ProjectRoot],
    doc_files: list[str],
) -> list[str]:
  """Finds markdown docs not linked from their root index/sitemap/README."""
  unindexed: list[str] = []
  for root in roots:
    if root.kind != "docs":
      continue
    root_dir = repo_root / root.path
    index_text = ""
    for candidate in ("index.md", "sitemap.md", "_sitemap.md", "README.md"):
      idx_path = root_dir / candidate
      if idx_path.is_file():
        index_text += "\n" + idx_path.read_text(
            encoding="utf-8", errors="ignore"
        )
    if not index_text:
      continue
    for rel in doc_files:
      if not rel.startswith(f"{root.path}/"):
        continue
      name = pathlib.Path(rel).name
      if name.lower() in _DOC_INDEX_NAMES:
        continue
      if name not in index_text and rel not in index_text:
        unindexed.append(rel)

  arm_index = armature_dir / "index.md"
  if arm_index.is_file() and (armature_dir / "guidelines").is_dir():
    arm_text = arm_index.read_text(encoding="utf-8", errors="ignore")
    for md in sorted((armature_dir / "guidelines").glob("*.md")):
      if md.name not in arm_text:
        unindexed.append(md.relative_to(repo_root).as_posix())
  return sorted(set(unindexed))


def _resolve_doc_link_target(
    raw_target: str, doc_path: pathlib.Path, repo_root: pathlib.Path
) -> str | None:
  """Resolves a markdown link target to a normalized repo-relative path."""
  if any(ch in raw_target for ch in ("<", ">", "{", "}")):
    return None
  if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw_target):
    return None
  if raw_target.startswith(("//", "/")):
    return normalize_rel_path(raw_target)
  clean_rel = raw_target.split("#", 1)[0].split("?", 1)[0]
  if not clean_rel:
    return None
  resolved = (doc_path.parent / clean_rel).resolve()
  try:
    return resolved.relative_to(repo_root.resolve()).as_posix()
  except ValueError:
    return None


def find_stale_doc_links(
    repo_root: pathlib.Path,
    owned_prefixes: list[str],
    doc_paths: list[pathlib.Path],
) -> list[dict[str, str]]:
  """Flags links in docs pointing to missing files under owned roots."""
  stale: list[dict[str, str]] = []
  seen: set[tuple[str, str]] = set()
  for doc_path in doc_paths:
    try:
      raw_text = doc_path.read_text(encoding="utf-8", errors="ignore")
      doc_rel = doc_path.relative_to(repo_root).as_posix()
    except (OSError, ValueError):
      continue
    stripped_text = _INLINE_CODE_RE.sub("", _FENCED_CODE_RE.sub("", raw_text))
    for match in _MD_LINK_RE.finditer(stripped_text):
      norm = _resolve_doc_link_target(match.group(1), doc_path, repo_root)
      if not norm or not _is_under_any(norm, owned_prefixes):
        continue
      if not (repo_root / norm).exists() and (doc_rel, norm) not in seen:
        seen.add((doc_rel, norm))
        stale.append({"doc": doc_rel, "missing_target": norm})
  return stale


def scan_project_drift(
    armature_dir: pathlib.Path,
    repo_root: pathlib.Path,
    since_override: str | None = None,
    full_scan: bool = False,
) -> DriftScanResult:
  """Runs the complete multi-directory discovery and drift scan."""
  vcs = detect_vcs(repo_root)
  head_rev = get_head_revision(repo_root, vcs)
  roots, roots_source, legacy_fences = discover_project_roots(
      armature_dir, repo_root
  )
  cache_path = armature_dir / ".api_surface_cache.json"
  watermark = read_watermark(cache_path)
  watermark_rev = since_override or watermark.get("revision")

  code_files: set[str] = set()
  doc_files: set[str] = set()
  warnings: list[str] = []
  for root in roots:
    listed, list_warnings = list_files_in_root(
        repo_root, root.path, vcs, legacy_fences
    )
    warnings.extend(list_warnings)
    for rel in listed:
      if rel.lower().endswith(".md"):
        doc_files.add(rel)
      elif pathlib.Path(rel).suffix.lower() in _CODE_EXTS:
        code_files.add(rel)

  try:
    armature_rel = armature_dir.relative_to(repo_root).as_posix()
  except ValueError:
    armature_rel = "armature"

  external_commits, new_files, deleted_files, vcs_warnings = (
      scan_vcs_changes_since_watermark(
          repo_root,
          roots,
          armature_rel,
          vcs,
          None if full_scan else watermark_rev,
          head_rev,
          legacy_fences,
      )
  )
  warnings.extend(vcs_warnings)

  doc_corpus, doc_paths = _collect_doc_corpus(
      repo_root, armature_dir, sorted(doc_files)
  )
  unindexed_docs = _find_unindexed_docs(
      repo_root, armature_dir, roots, sorted(doc_files)
  )

  if full_scan or not watermark_rev:
    candidate_code = sorted(code_files)
  else:
    touched = {f for f in new_files if f in code_files}
    for commit in external_commits:
      for changed in commit.files:
        if changed in code_files:
          touched.add(changed)
    candidate_code = sorted(touched)

  undocumented_code: list[str] = []
  missing_headers: list[str] = []
  for rel in candidate_code:
    if _is_test_file(rel):
      continue
    basename = pathlib.Path(rel).name
    if rel not in doc_corpus and basename not in doc_corpus:
      undocumented_code.append(rel)
    if not has_code_doc_header(repo_root / rel):
      missing_headers.append(rel)

  owned_prefixes = [r.path for r in roots]
  stale_links = find_stale_doc_links(repo_root, owned_prefixes, doc_paths)

  return DriftScanResult(
      vcs=vcs,
      head_revision=head_rev,
      watermark_revision=watermark_rev,
      full_scan=full_scan,
      roots_source=roots_source,
      project_roots=roots,
      external_non_armature_commits=external_commits,
      new_files_since_watermark=new_files,
      deleted_files_since_watermark=deleted_files,
      unindexed_docs=unindexed_docs,
      undocumented_code_files=undocumented_code,
      missing_code_doc_headers=missing_headers,
      stale_doc_references=stale_links,
      total_code_files=len(code_files),
      total_doc_files=len(doc_files),
      warnings=warnings,
  )


def format_markdown_report(result: DriftScanResult) -> str:
  """Renders a concise Markdown summary of the multi-directory drift scan."""
  wm_label = result.watermark_revision or "none (initial baseline)"
  root_str = ", ".join(f"`{r.path}` ({r.kind})" for r in result.project_roots)
  lines = [
      "## Multi-Directory Project Drift Scan",
      f"- VCS: `{result.vcs}` | HEAD: `{result.head_revision}` "
      f"| Watermark: `{wm_label}`",
      f"- Roots ({result.roots_source}): {root_str}",
      f"- Scanned: `{result.total_code_files}` code files, "
      f"`{result.total_doc_files}` doc files",
  ]
  if result.external_non_armature_commits:
    count = len(result.external_non_armature_commits)
    lines.append(f"\n### Non-Armature Commits Since Watermark ({count})")
    for c in result.external_non_armature_commits[:15]:
      lines.append(
          f"- `{c.revision}` ({c.date}, {c.author}): {c.subject} "
          f"({len(c.files)} file(s))"
      )
  if result.unindexed_docs:
    lines.append(f"\n### [Tier A] Unindexed Docs ({len(result.unindexed_docs)})")
    lines.extend(f"- `{d}`" for d in result.unindexed_docs[:25])
  if result.undocumented_code_files:
    count = len(result.undocumented_code_files)
    lines.append(f"\n### [Tier B] Undocumented Code Files ({count})")
    lines.extend(f"- `{f}`" for f in result.undocumented_code_files[:25])
  if result.missing_code_doc_headers:
    count = len(result.missing_code_doc_headers)
    lines.append(f"\n### [Tier B] Missing Module/File Doc Headers ({count})")
    lines.extend(f"- `{f}`" for f in result.missing_code_doc_headers[:25])
  if result.stale_doc_references:
    count = len(result.stale_doc_references)
    lines.append(f"\n### [Tier B] Stale Doc References ({count})")
    lines.extend(
        f"- `{item['doc']}` -> missing `{item['missing_target']}`"
        for item in result.stale_doc_references[:25]
    )
  if result.warnings:
    lines.append("\n### Warnings")
    lines.extend(f"- {w}" for w in result.warnings)
  return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
  """CLI entrypoint for scan_project_drift.py."""
  parser = argparse.ArgumentParser(
      description="Scan all owned project directories for drift."
  )
  parser.add_argument(
      "--armature-dir",
      required=True,
      help="Path to project's armature/ directory.",
  )
  parser.add_argument("--repo-root", default=".", help="Repository root.")
  parser.add_argument("--since", default=None, help="Override commit SHA.")
  parser.add_argument(
      "--full", action="store_true", help="Ignore watermark and scan all files."
  )
  parser.add_argument(
      "--check", action="store_true", help="Read-only mode (no writes)."
  )
  parser.add_argument(
      "--update-watermark",
      action="store_true",
      help="Persist compact drift_watermark to .api_surface_cache.json.",
  )
  parser.add_argument("--json", action="store_true", help="Emit JSON output.")
  args = parser.parse_args(argv)

  armature_dir = pathlib.Path(args.armature_dir).resolve()
  repo_root = pathlib.Path(args.repo_root).resolve()
  result = scan_project_drift(
      armature_dir=armature_dir,
      repo_root=repo_root,
      since_override=args.since,
      full_scan=args.full,
  )

  if args.update_watermark and not args.check:
    if result.head_revision == "unknown":
      result.warnings.append(
          "Skipped updating drift_watermark because head_revision is unknown."
      )
    elif any("failed" in w for w in result.warnings):
      result.warnings.append(
          "Skipped updating drift_watermark because VCS scan had errors."
      )
    else:
      write_watermark(
          armature_dir / ".api_surface_cache.json",
          vcs=result.vcs,
          revision=result.head_revision,
          roots=result.project_roots,
      )

  if args.json:
    print(json.dumps(dataclasses.asdict(result), indent=2))
  else:
    print(format_markdown_report(result))
  return 0


if __name__ == "__main__":
  sys.exit(main())
