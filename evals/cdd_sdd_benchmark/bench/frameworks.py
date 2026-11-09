"""Framework pack loading, context rendering, and command expansion.

Each framework under test is described by an entry in `frameworks/registry.json`
(public) or `frameworks/registry_internal.json` (internal only). An entry points
at the framework's real shipped files: a pinned upstream commit fetched into
`.pack_cache/` by `fetch_packs.py`, or a local path inside the monorepo.

`FrameworkPack` turns those files into what a real agent host would give the
model:

* `system_prompt()`: the shared base prompt, then the always-on rule files in
  order, then an index of on-demand skills/commands (name, description, and the
  sandbox path to read).
* `sandbox_files()`: the files a real install places in or near the repo, so
  the agent can `read_file` them.
* `render_context()`: the scenario's neutral project facts rendered into the
  framework's native context files (or a generic `docs/` fallback).
* `expand_user_message()`: host-style slash-command expansion for the
  scenario's intent.
* `identifiers()`: every framework-identifying string, for judge blinding.
* `file_hashes()`: sha256 of every loaded upstream file, checked against the
  lockfile.

Standard library only. See DESIGN.md ("Framework registry") and
frameworks/README.md (mapping rationale).
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

try:  # Python 3.11+.
  import tomllib  # pylint: disable=g-import-not-at-top
except ImportError:  # pragma: no cover - Python 3.10 fallback.
  tomllib = None

try:
  from bench import schema  # pylint: disable=g-import-not-at-top
except ImportError:  # pragma: no cover - when run with bench/ on sys.path.
  import schema  # type: ignore  # pylint: disable=g-import-not-at-top

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMEWORKS_DIR = os.path.join(BASE_DIR, "frameworks")
TOOLS_SUBDIR = "_tools"


def _default_cache_dir() -> str:
  """`.pack_cache/` next to the benchmark, or `~/.cache` on read-only mounts.

  When `CDD_BENCH_PACK_CACHE` is set it takes precedence. Otherwise uses an
  existing `.pack_cache/`, falls back to `~/.cache/cdd_sdd_benchmark/pack_cache`
  when already populated or when `BASE_DIR` is not writable, and defaults to
  `.pack_cache/` in standard writable checkouts.
  """
  env = os.environ.get("CDD_BENCH_PACK_CACHE")
  if env:
    return os.path.abspath(env)
  local_cache = os.path.join(BASE_DIR, ".pack_cache")
  if os.path.isdir(local_cache):
    return local_cache
  user_cache = os.path.join(
      os.path.expanduser("~"), ".cache", "cdd_sdd_benchmark", "pack_cache"
  )
  if os.path.isdir(user_cache) or not os.access(BASE_DIR, os.W_OK):
    return user_cache
  return local_cache


PACK_CACHE_DIR = _default_cache_dir()

# Cap on the one-line description shown in the skills index.
_MAX_DESCRIPTION_CHARS = 600

# Paths produced by the generic renderer. They are shared by several frameworks
# and are not framework-identifying, so `identifiers()` leaves them out.
_GENERIC_PATH_PREFIXES = ("docs/",)


class PackError(Exception):
  """Raised when a pack cannot be loaded."""


class PackIntegrityError(PackError):
  """Raised when loaded files do not match the lockfile."""


# ---------------------------------------------------------------------------
# Paths, hashing, globbing.
# ---------------------------------------------------------------------------


def find_monorepo_root(start: str = __file__) -> Optional[str]:
  """Returns the nearest ancestor directory named `monorepo`, or None."""
  path = os.path.dirname(os.path.abspath(start))
  while True:
    if os.path.basename(path) == "monorepo":
      return path
    parent = os.path.dirname(path)
    if parent == path:
      return None
    path = parent


def lock_path_for(registry_path: str) -> str:
  """Maps `registry.json` -> `packs.lock.json`, `registry_X.json` -> `packs_X...`."""
  directory = os.path.dirname(os.path.abspath(registry_path))
  name = os.path.basename(registry_path)
  m = re.fullmatch(r"registry(_[A-Za-z0-9]+)?\.json", name)
  suffix = m.group(1) if m and m.group(1) else ""
  return os.path.join(directory, f"packs{suffix}.lock.json")


def sha256_bytes(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
  with open(path, "rb") as f:
    return sha256_bytes(f.read())


def _glob_to_regex(pattern: str) -> "re.Pattern[str]":
  """Translates a `**`-aware glob into an anchored regex over `/` paths."""
  i, out = 0, []
  while i < len(pattern):
    c = pattern[i]
    if pattern.startswith("**/", i):
      out.append("(?:.*/)?")
      i += 3
    elif pattern.startswith("**", i):
      out.append(".*")
      i += 2
    elif c == "*":
      out.append("[^/]*")
      i += 1
    elif c == "?":
      out.append("[^/]")
      i += 1
    else:
      out.append(re.escape(c))
      i += 1
  return re.compile("".join(out) + r"\Z")


def glob_match(path: str, pattern: str) -> bool:
  return bool(_glob_to_regex(pattern).match(path))


def _walk_files(root: str) -> List[str]:
  out = []
  for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = sorted(d for d in dirnames if d not in (".git", TOOLS_SUBDIR))
    for fn in sorted(filenames):
      out.append(
          os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/")
      )
  return out


def source_root(entry: Dict[str, Any], cache_dir: str = PACK_CACHE_DIR) -> str:
  """Returns the on-disk root of a registry entry's files."""
  src = entry["source"]
  if src["type"] == "git":
    return os.path.join(cache_dir, entry["key"], src["ref"])
  if src["type"] == "local":
    g3 = find_monorepo_root()
    if g3 is None:
      raise PackError(
          f"{entry['key']}: local source needs a monorepo root above {__file__}"
      )
    return os.path.join(g3, src["path"])
  if src["type"] == "local_path":
    env_name = src.get("env") or ""
    val = os.environ.get(env_name, "").strip() if env_name else ""
    if not val:
      raise PackError(
          f"{entry['key']}: local_path source requires environment variable "
          f"{env_name!r} to be set"
      )
    return os.path.abspath(val)
  raise PackError(f"{entry['key']}: unknown source type {src['type']!r}")


def check_git_pack_mtime(
    entry: Dict[str, Any], cache_dir: str = PACK_CACHE_DIR
) -> List[str]:
  """Checks that no cached file in a `git` pack is newer than `.fetched`."""
  src = entry.get("source") or {}
  if src.get("type") != "git":
    return []
  root = source_root(entry, cache_dir)
  marker = os.path.join(root, ".fetched")
  if not os.path.isfile(marker):
    return [f"{entry['key']}: missing .fetched marker in {root}"]
  marker_mtime = os.path.getmtime(marker)
  problems: List[str] = []
  for rel in _walk_files(root):
    if rel == ".fetched":
      continue
    fpath = os.path.join(root, rel)
    if os.path.getmtime(fpath) > marker_mtime:
      problems.append(f"cache modified after fetch: {entry['key']}/{rel}")
  return problems


def git_working_tree_state(root: str) -> Tuple[Optional[str], Optional[int]]:
  """Returns `(git_head_sha, dirty_file_count)` for a git working tree."""
  try:
    head_proc = subprocess.run(
        ["git", "-C", root, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    status_proc = subprocess.run(
        ["git", "-C", root, "status", "--porcelain"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if head_proc.returncode == 0:
      head = head_proc.stdout.strip()
      dirty = (
          len([ln for ln in status_proc.stdout.splitlines() if ln.strip()])
          if status_proc.returncode == 0
          else 0
      )
      return head, dirty
  except OSError:
    pass
  return None, None


def tools_dir(entry: Dict[str, Any], cache_dir: str = PACK_CACHE_DIR) -> str:
  """Directory where fetch_packs.py installs a pack's own CLI tooling."""
  return os.path.join(cache_dir, entry["key"], TOOLS_SUBDIR)


def expand_source_files(entry: Dict[str, Any], root: str) -> List[str]:
  """Lists every upstream file the pack loads, relative to `root`, in order.

  Order: always-on files, skills, commands, then `extra_files` glob matches
  (sorted) minus `exclude_files` glob matches.

  Args:
    entry: A registry entry.
    root: The pack's source root.

  Returns:
    Ordered, de-duplicated relative paths.

  Raises:
    PackError: If an explicitly listed file is missing.
  """
  ordered: "collections.OrderedDict[str, None]" = collections.OrderedDict()
  explicit = list(entry.get("always_on", []))
  explicit += list(entry.get("skills_index", {}).values())
  explicit += list(entry.get("commands", {}).values())
  for rel in explicit:
    if not os.path.isfile(os.path.join(root, rel)):
      raise PackError(f"{entry['key']}: missing pack file {rel} under {root}")
    ordered[rel] = None
  patterns = entry.get("extra_files", [])
  excludes = entry.get("exclude_files", [])
  if patterns:
    for rel in _walk_files(root):
      if any(glob_match(rel, p) for p in patterns) and not any(
          glob_match(rel, x) for x in excludes
      ):
        ordered.setdefault(rel, None)
  return list(ordered)


# ---------------------------------------------------------------------------
# Frontmatter and description parsing.
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)


def split_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
  """Parses top-level scalar keys of YAML frontmatter; returns (keys, body).

  Handles plain, quoted, and block (`>`, `>-`, `|`) scalars, which is all the
  packs use for `name` and `description`. Nested mappings are ignored.

  Args:
    text: File text.

  Returns:
    (frontmatter scalars, body without frontmatter).
  """
  m = _FRONTMATTER_RE.match(text)
  if not m:
    return {}, text
  lines = m.group(1).splitlines()
  keys: Dict[str, str] = {}
  i = 0
  while i < len(lines):
    line = lines[i]
    km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
    i += 1
    if not km:
      continue
    key, value = km.group(1), km.group(2).strip()
    if value in (">", ">-", "|", "|-", ">+", "|+"):
      block = []
      while i < len(lines) and (not lines[i].strip() or lines[i][:1] in " \t"):
        block.append(lines[i].strip())
        i += 1
      sep = "\n" if value.startswith("|") else " "
      value = sep.join(b for b in block).strip()
    elif value[:1] in ("'", '"') and value[-1:] == value[:1] and len(value) > 1:
      q = value[0]
      value = value[1:-1]
      if q == "'":
        value = value.replace("''", "'")
      else:
        value = value.replace('\\"', '"')
    elif not value:
      # Possibly a nested mapping; collect indented continuation as text-less.
      while i < len(lines) and lines[i][:1] in " \t":
        i += 1
      continue
    keys[key] = value
  return keys, text[m.end():]


def _first_paragraph(body: str) -> str:
  for para in re.split(r"\n\s*\n", body):
    p = para.strip()
    if p and not p.startswith("#") and not p.startswith("```"):
      return p
  return ""


def one_line(text: str) -> str:
  s = re.sub(r"\s+", " ", text).strip()
  if len(s) > _MAX_DESCRIPTION_CHARS:
    s = s[: _MAX_DESCRIPTION_CHARS - 3].rstrip() + "..."
  return s


def parse_toml_command(text: str) -> Tuple[str, str]:
  """Returns (description, prompt) from a Gemini CLI command .toml file."""
  if tomllib is not None:
    data = tomllib.loads(text)
    return str(data.get("description", "")), str(data.get("prompt", ""))
  desc = re.search(r'^description\s*=\s*"((?:[^"\\]|\\.)*)"', text, re.M)
  prompt = re.search(r'^prompt\s*=\s*"""\n?(.*?)"""', text, re.M | re.S)
  return (desc.group(1) if desc else ""), (prompt.group(1) if prompt else "")


# ---------------------------------------------------------------------------
# Upstream-installer transforms.
# ---------------------------------------------------------------------------

# Mirrors CommandRegistrar.rewrite_project_relative_paths in spec-kit v1.3.0
# (src/specify_cli/agents.py): bare `scripts/`, `memory/`, `templates/` refer
# to the installed `.specify/` copies.
_SPECKIT_REL_RE = re.compile(
    r"(?:(?<![.\w])(?P<parent>(?:\.\./){2,})|"
    r"(?P<boundary>^|[\s`\"'(\[{<=])(?P<rel>\.specify/|(?:\.?/))?)"
    r"(?P<target>scripts|memory|templates)/",
    re.M,
)


def _speckit_rewrite_paths(text: str) -> str:
  def repl(m: "re.Match[str]") -> str:
    boundary = "" if m.group("parent") else (m.group("boundary") or "")
    return f"{boundary}.specify/{m.group('target')}/"

  return _SPECKIT_REL_RE.sub(repl, text)


def _speckit_command_to_skill(name: str, text: str, agent: str) -> str:
  """Renders a spec-kit command template the way `specify init --ai agy` does.

  Follows SkillsIntegration in spec-kit v1.3.0: `{SCRIPT}` becomes the `sh`
  script variant, `{ARGS}` becomes `$ARGUMENTS`, `__AGENT__` the agent key,
  `__SPECKIT_COMMAND_X__` the hyphenated skill invocation, and repo-relative
  paths are rewritten to `.specify/`. Frontmatter is normalized to name and
  description.

  Args:
    name: Command stem (for example `specify`).
    text: Raw template text.
    agent: Integration key used for `__AGENT__`.

  Returns:
    SKILL.md text.
  """
  meta, body = split_frontmatter(text)
  script = None
  m = _FRONTMATTER_RE.match(text)
  if m:
    sm = re.search(r"^\s+sh:\s*(.+)$", m.group(1), re.M)
    if sm:
      script = sm.group(1).strip()
  if script:
    script = script.replace("{ARGS}", "$ARGUMENTS")
    body = body.replace("{SCRIPT}", script)
  body = body.replace("{ARGS}", "$ARGUMENTS").replace("__AGENT__", agent)
  body = _speckit_command_refs(body)
  body = _speckit_rewrite_paths(body)
  desc = meta.get("description", "")
  return (
      f"---\nname: speckit-{name}\ndescription: {json.dumps(desc)}\n---\n\n"
      + body.lstrip("\n")
  )


def _speckit_command_refs(text: str) -> str:
  """`__SPECKIT_COMMAND_X__` -> `/speckit-x` (skills-agent invocation form)."""
  return re.sub(
      r"__SPECKIT_COMMAND_([A-Z][A-Z0-9_-]*)__",
      lambda mm: "/speckit-" + mm.group(1).lower().replace("_", "-"),
      text,
  )


# ---------------------------------------------------------------------------
# Neutral project-context rendering.
# ---------------------------------------------------------------------------


def _slug(text: str, limit: int = 48) -> str:
  s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
  return (s[:limit].rstrip("-")) or "item"


def _decision_number(decision_id: str, fallback: int) -> str:
  m = re.search(r"(\d+)", decision_id or "")
  return m.group(1).zfill(4) if m else str(fallback).zfill(4)


def _decision_md(d: Dict[str, Any]) -> str:
  """One decision record. Identical wording for every layout."""
  title = d.get("title", "").strip()
  did = d.get("id", "").strip()
  head = f"# {did}: {title}" if did else f"# {title}"
  status = d.get("status")
  lines = [head, ""]
  if status:
    lines += [f"- Status: {status}", ""]
  lines += [d.get("body", "").strip(), ""]
  return "\n".join(lines)


def _decisions_section(decisions: List[Dict[str, Any]], level: str = "##") -> str:
  out = []
  for d in decisions:
    did = d.get("id", "").strip()
    title = d.get("title", "").strip()
    status = d.get("status")
    out.append(f"{level} {did}: {title}" if did else f"{level} {title}")
    out.append("")
    if status:
      out += [f"- Status: {status}", ""]
    out += [d.get("body", "").strip(), ""]
  return "\n".join(out)


def _glossary_md(glossary: List[Dict[str, Any]], title: str = "Glossary") -> str:
  lines = [f"# {title}", ""]
  for g in glossary:
    lines.append(f"- **{g.get('term', '').strip()}**: {g.get('definition', '').strip()}")
  return "\n".join(lines) + "\n"


def _tech_md(tech: List[str], title: str = "Tech Stack") -> str:
  return f"# {title}\n\n" + "".join(f"- {t}\n" for t in tech)


def _tasks_md(tasks: List[Dict[str, Any]], fmt: str = "- [{x}] {text}") -> str:
  out = []
  for n, t in enumerate(tasks, 1):
    out.append(
        fmt.format(x="x" if t.get("done") else " ", text=t.get("text", ""), n=n)
    )
  return "\n".join(out) + ("\n" if out else "")


def _plan_parts(plan: Dict[str, Any]) -> Tuple[str, str, List[str], List[Dict[str, Any]]]:
  return (
      plan.get("title", "Current work").strip(),
      plan.get("summary", "").strip(),
      [str(x) for x in plan.get("decisions", [])],
      list(plan.get("tasks", [])),
  )


def _bullets(items: Iterable[str]) -> str:
  return "".join(f"- {i}\n" for i in items)


# Setup-produced guidelines file for layouts whose commands require it. The
# scenarios carry no product-guideline facts, so it says so (same text for all).
_NO_GUIDELINES = "# Product Guidelines\n\nNo product guidelines recorded yet.\n"


class _Ctx:
  """Normalized neutral project context."""

  def __init__(self, pc: Optional[Dict[str, Any]]):
    pc = pc or {}
    self.product = (pc.get("product") or "").strip()
    self.tech = [str(t) for t in (pc.get("tech_stack") or [])]
    self.decisions = list(pc.get("decisions") or [])
    self.glossary = list(pc.get("glossary") or [])
    plan = pc.get("prior_plan") or None
    if isinstance(plan, str):
      plan = {"title": "Current work", "summary": plan, "decisions": [], "tasks": []}
    self.plan = plan


def _render_generic(c: _Ctx, out: Dict[str, str], parts: Iterable[str]) -> None:
  """Generic fallback locations for facts a framework has no native home for."""
  parts = set(parts)
  if "product" in parts and c.product:
    out["docs/product.md"] = f"# Product\n\n{c.product}\n"
  if "tech" in parts and c.tech:
    out["docs/tech-stack.md"] = _tech_md(c.tech)
  if "decisions" in parts:
    for n, d in enumerate(c.decisions, 1):
      num = _decision_number(d.get("id", ""), n)
      out[f"docs/decisions/ADR-{num}.md"] = _decision_md(d)
  if "glossary" in parts and c.glossary:
    out["docs/glossary.md"] = _glossary_md(c.glossary)
  if "plan" in parts and c.plan:
    title, summary, decisions, tasks = _plan_parts(c.plan)
    text = f"# {title}\n\n{summary}\n\n"
    if decisions:
      text += "## Decisions\n\n" + _bullets(decisions) + "\n"
    if tasks:
      text += "## Tasks\n\n" + _tasks_md(tasks)
    out["docs/plan/current.md"] = text


def _render_armature(c: _Ctx, out: Dict[str, str], pack: "FrameworkPack") -> None:
  d = "armature"
  index = ["# Project Context", ""]
  if c.product:
    out[f"{d}/product.md"] = f"# Product\n\n{c.product}\n"
    index.append("- [Product Definition](./product.md)")
  # `/arm-setup` writes these; skills halt if they are missing. The workflow
  # comes from the pack's own template; guidelines have no neutral facts.
  out[f"{d}/product-guidelines.md"] = _NO_GUIDELINES
  index.append("- [Product Guidelines](./product-guidelines.md)")
  workflow = pack.raw_text("skills/arm-setup/assets/workflow_template.md")
  if workflow is not None:
    out[f"{d}/workflow.md"] = workflow
    index.append("- [Workflow](./workflow.md)")
  if c.tech:
    out[f"{d}/tech-stack.md"] = _tech_md(c.tech)
    index.append("- [Tech Stack](./tech-stack.md)")
  for n, dec in enumerate(c.decisions, 1):
    num = _decision_number(dec.get("id", ""), n)
    out[f"{d}/adr/{num}-{_slug(dec.get('title', ''))}.md"] = _decision_md(dec)
  if c.decisions:
    index.append("- [Architecture Decision Records](./adr/)")
  if c.glossary:
    out[f"{d}/terms.md"] = _glossary_md(c.glossary)
    index.append("- [Glossary](./terms.md)")
  tracks = "# Tracks\n\n"
  if c.plan:
    title, summary, decisions, tasks = _plan_parts(c.plan)
    tid = _slug(title)
    tracks += f"- [~] **{title}** ([folder](./tracks/{tid}/))\n"
    td = f"{d}/tracks/{tid}"
    spec = f"# Specification: {title}\n\n{summary}\n"
    if decisions:
      spec += "\n## Decisions\n\n" + _bullets(decisions)
    out[f"{td}/spec.md"] = spec
    out[f"{td}/plan.md"] = f"# Implementation Plan: {title}\n\n" + _tasks_md(tasks)
    out[f"{td}/metadata.json"] = json.dumps(
        {"track_id": tid, "type": "feature", "status": "in_progress",
         "description": title}, indent=2) + "\n"
    out[f"{td}/index.md"] = (
        f"# {title}\n\n- [Specification](./spec.md)\n- [Plan](./plan.md)\n"
        "- [Metadata](./metadata.json)\n")
  out[f"{d}/tracks.md"] = tracks
  index.append("- [Tracks Registry](./tracks.md)")
  out[f"{d}/index.md"] = "\n".join(index) + "\n"


def _render_conductor(c: _Ctx, out: Dict[str, str], pack: "FrameworkPack") -> None:
  d = "conductor"
  index = ["# Project Context", ""]
  if c.product:
    out[f"{d}/product.md"] = f"# Product\n\n{c.product}\n"
    index.append("- [Product Definition](./product.md)")
  if c.tech:
    out[f"{d}/tech-stack.md"] = _tech_md(c.tech)
    index.append("- [Tech Stack](./tech-stack.md)")
  workflow = pack.raw_text("templates/workflow.md")
  if workflow is not None:
    # `/conductor:setup` copies the extension's workflow template verbatim.
    out[f"{d}/workflow.md"] = workflow
    index.append("- [Workflow](./workflow.md)")
  out[f"{d}/product-guidelines.md"] = _NO_GUIDELINES
  index.append("- [Product Guidelines](./product-guidelines.md)")
  tracks = "# Tracks Registry\n\n"
  if c.plan:
    title, summary, decisions, tasks = _plan_parts(c.plan)
    tid = _slug(title)
    tracks += f"---\n\n- [~] **Track: {title}**\n  *Link: [./tracks/{tid}/](./tracks/{tid}/)*\n"
    td = f"{d}/tracks/{tid}"
    spec = f"# Specification: {title}\n\n{summary}\n"
    if decisions:
      spec += "\n## Decisions\n\n" + _bullets(decisions)
    out[f"{td}/spec.md"] = spec
    out[f"{td}/plan.md"] = f"# Implementation Plan: {title}\n\n" + _tasks_md(tasks)
    out[f"{td}/metadata.json"] = json.dumps(
        {"track_id": tid, "type": "feature", "status": "in_progress",
         "description": title}, indent=2) + "\n"
    out[f"{td}/index.md"] = (
        f"# Track {tid} Context\n\n- [Specification](./spec.md)\n"
        "- [Implementation Plan](./plan.md)\n- [Metadata](./metadata.json)\n")
  out[f"{d}/tracks.md"] = tracks
  index.append("- [Tracks Registry](./tracks.md)")
  out[f"{d}/index.md"] = "\n".join(index) + "\n"
  _render_generic(c, out, ("decisions", "glossary"))


def _render_speckit(c: _Ctx, out: Dict[str, str], pack: "FrameworkPack") -> None:
  del pack  # Unused.
  if c.tech or c.decisions:
    text = "# Project Constitution\n\n"
    if c.tech:
      text += "## Technology Constraints\n\n" + _bullets(c.tech) + "\n"
    if c.decisions:
      text += "## Architectural Decisions\n\n" + _decisions_section(c.decisions, "###")
    out[".specify/memory/constitution.md"] = text
  if c.plan:
    title, summary, decisions, tasks = _plan_parts(c.plan)
    fd = f"specs/001-{_slug(title, 32)}"
    out[f"{fd}/spec.md"] = f"# Feature Specification: {title}\n\n{summary}\n"
    plan = f"# Implementation Plan: {title}\n\n**Spec**: [spec.md](./spec.md)\n\n"
    if decisions:
      plan += "## Decisions\n\n" + _bullets(decisions)
    out[f"{fd}/plan.md"] = plan
    out[f"{fd}/tasks.md"] = f"# Tasks: {title}\n\n" + _tasks_md(
        tasks, "- [{x}] T{n:03d} {text}")
  _render_generic(c, out, ("product", "glossary"))


def _render_openspec(c: _Ctx, out: Dict[str, str], pack: "FrameworkPack") -> None:
  del pack  # Unused.
  ctx_lines = []
  if c.product:
    ctx_lines.append(f"Product: {c.product}")
  if c.tech:
    ctx_lines.append("Tech stack:")
    ctx_lines += [f"- {t}" for t in c.tech]
  text = "schema: spec-driven\n"
  if ctx_lines:
    text += "\ncontext: |\n" + "".join(f"  {l}\n" for l in ctx_lines)
  out["openspec/config.yaml"] = text
  out["openspec/specs/.gitkeep"] = ""
  out["openspec/changes/archive/.gitkeep"] = ""
  if c.plan:
    title, summary, decisions, tasks = _plan_parts(c.plan)
    cd = f"openspec/changes/{_slug(title)}"
    out[f"{cd}/proposal.md"] = f"## Why\n\n{summary}\n\n## What Changes\n\n- {title}\n"
    if decisions:
      out[f"{cd}/design.md"] = "## Decisions\n\n" + _bullets(decisions)
    out[f"{cd}/tasks.md"] = "## 1. Tasks\n\n" + _tasks_md(tasks, "- [{x}] 1.{n} {text}")
  _render_generic(c, out, ("decisions", "glossary"))


def _render_bmad(c: _Ctx, out: Dict[str, str], pack: "FrameworkPack") -> None:
  del pack  # Unused.
  if c.tech or c.decisions:
    text = "# Architecture\n\n"
    if c.tech:
      text += "## Technology Stack\n\n" + _bullets(c.tech) + "\n"
    if c.decisions:
      text += "## Architecture Decisions\n\n" + _decisions_section(c.decisions, "###")
    out["_bmad-output/planning-artifacts/architecture/architecture.md"] = text
  if c.plan:
    title, summary, decisions, tasks = _plan_parts(c.plan)
    text = f"# {title}\n\n{summary}\n\n"
    if decisions:
      text += "## Decisions\n\n" + _bullets(decisions) + "\n"
    if tasks:
      text += "## Tasks\n\n" + _tasks_md(tasks)
    out[f"_bmad-output/specs/{_slug(title)}/SPEC.md"] = text
  _render_generic(c, out, ("product", "glossary"))


def _render_memory_bank(c: _Ctx, out: Dict[str, str], pack: "FrameworkPack") -> None:
  del pack  # Unused.
  d = "memory-bank"
  out[f"{d}/projectbrief.md"] = "# Project Brief\n\n" + (c.product or "") + "\n"
  out[f"{d}/productContext.md"] = "# Product Context\n\n" + (c.product or "") + "\n"
  out[f"{d}/techContext.md"] = _tech_md(c.tech, "Tech Context")
  sp = "# System Patterns\n\n"
  if c.decisions:
    sp += "## Key Technical Decisions\n\n" + _decisions_section(c.decisions, "###")
  if c.glossary:
    sp += "## Terminology\n\n" + "".join(
        f"- **{g.get('term', '')}**: {g.get('definition', '')}\n" for g in c.glossary)
  out[f"{d}/systemPatterns.md"] = sp
  if c.plan:
    title, summary, decisions, tasks = _plan_parts(c.plan)
    ac = f"# Active Context\n\n## Current Work Focus\n\n{title}: {summary}\n"
    if decisions:
      ac += "\n## Active Decisions\n\n" + _bullets(decisions)
    out[f"{d}/activeContext.md"] = ac
    done = [t for t in tasks if t.get("done")]
    left = [t for t in tasks if not t.get("done")]
    pr = "# Progress\n\n## What Works\n\n" + _bullets(t.get("text", "") for t in done)
    pr += "\n## What's Left\n\n" + _bullets(t.get("text", "") for t in left)
    out[f"{d}/progress.md"] = pr
  else:
    out[f"{d}/activeContext.md"] = "# Active Context\n\nNo active work recorded.\n"
    out[f"{d}/progress.md"] = "# Progress\n\nNo progress recorded.\n"


def _render_internal_sdd(c: _Ctx, out: Dict[str, str], pack: "FrameworkPack") -> None:
  del pack  # Unused.
  for n, dec in enumerate(c.decisions, 1):
    num = _decision_number(dec.get("id", ""), n)
    out[f"docs/adrs/ADR-{num}.md"] = _decision_md(dec)
  if c.glossary:
    out["docs/glossary.md"] = _glossary_md(c.glossary)
  if c.plan:
    title, summary, decisions, tasks = _plan_parts(c.plan)
    pd = f"docs/openspec/proposals/{_slug(title)}"
    text = f"# Proposal: {title}\n\n## Summary\n\n{summary}\n"
    if decisions:
      text += "\n## Decisions\n\n" + _bullets(decisions)
    out[f"{pd}/proposal.md"] = text
    out[f"{pd}/tasks.md"] = f"# Tasks: {title}\n\n" + _tasks_md(tasks)
  _render_generic(c, out, ("product", "tech"))


def _render_mattpocock(c: _Ctx, out: Dict[str, str], pack: "FrameworkPack") -> None:
  for n, dec in enumerate(c.decisions, 1):
    num = _decision_number(dec.get("id", ""), n)
    out[f"docs/adr/{num}-{_slug(dec.get('title', ''))}.md"] = _decision_md(dec)
  if c.glossary:
    out["GLOSSARY.md"] = _glossary_md(c.glossary)
  # `/setup-matt-pocock-skills` with no git remote writes these from the seed
  # templates in its skill folder (local-markdown tracker, single context).
  for src, dest in (
      ("skills/engineering/setup-matt-pocock-skills/issue-tracker-local.md",
       "docs/agents/issue-tracker.md"),
      ("skills/engineering/setup-matt-pocock-skills/domain.md",
       "docs/agents/domain.md"),
  ):
    text = pack.raw_text(src)
    if text is not None:
      out[dest] = text
  if c.plan:
    title, summary, decisions, tasks = _plan_parts(c.plan)
    sd = f".scratch/{_slug(title)}"
    spec = f"# {title}\n\n{summary}\n"
    if decisions:
      spec += "\n## Decisions\n\n" + _bullets(decisions)
    out[f"{sd}/spec.md"] = spec
    for n, t in enumerate(tasks, 1):
      status = "resolved" if t.get("done") else "ready-for-agent"
      out[f"{sd}/issues/{n:02d}-{_slug(t.get('text', ''), 32)}.md"] = (
          f"# {t.get('text', '')}\n\nStatus: {status}\n")
  _render_generic(c, out, ("product", "tech"))


def _render_generic_only(c: _Ctx, out: Dict[str, str], pack: "FrameworkPack") -> None:
  del pack  # Unused.
  _render_generic(c, out, ("product", "tech", "decisions", "glossary", "plan"))


_RENDERERS: Dict[str, Callable[[_Ctx, Dict[str, str], "FrameworkPack"], None]] = {
    "armature": _render_armature,
    "conductor": _render_conductor,
    "speckit": _render_speckit,
    "openspec": _render_openspec,
    "bmad": _render_bmad,
    "memory_bank": _render_memory_bank,
    "internal_sdd": _render_internal_sdd,
    "mattpocock": _render_mattpocock,
    "generic": _render_generic_only,
}

# Native context directories per layout, used by identifiers().
_LAYOUT_IDENTIFIERS: Dict[str, Tuple[str, ...]] = {
    "armature": ("armature/", "terms.md", "tracks.md"),
    "conductor": ("conductor/", "tracks.md"),
    "speckit": (".specify/", "constitution.md", "specs/001-"),
    "openspec": ("openspec/", "openspec/changes/", "openspec/specs/"),
    "bmad": ("_bmad/", "_bmad-output/"),
    "memory_bank": ("memory-bank/", "projectbrief.md", "productContext.md",
                    "activeContext.md", "systemPatterns.md", "techContext.md"),
    "internal_sdd": ("docs/adrs/", "docs/openspec/", "docs/glossary.md"),
    "mattpocock": (".scratch/",),
    "generic": (),
}


# ---------------------------------------------------------------------------
# Pack-owned tooling (executed for real by the sandbox).
# ---------------------------------------------------------------------------


def _strip_project_root(token: str, sandbox_dir: str) -> str:
  token = token.replace("{project-root}", sandbox_dir)
  if sandbox_dir and token.startswith(sandbox_dir.rstrip("/") + "/"):
    token = token[len(sandbox_dir.rstrip("/")) + 1:]
  return token


def _make_resolver(spec: Dict[str, Any], entry: Dict[str, Any],
                   cache_dir: str) -> Tuple[Optional[Callable[[List[str], str], Optional[List[str]]]], List[str], Optional[str]]:
  """Builds the (resolve, path, unavailable_reason) triple for one spec."""
  kind = spec["kind"]
  globs = list(spec.get("path_globs", []))

  def allowed(script: str) -> bool:
    script = script[2:] if script.startswith("./") else script
    return ".." not in script.split("/") and any(glob_match(script, g) for g in globs)

  if kind == "bash_script":
    bash = shutil.which("bash") or "/bin/bash"

    def resolve_bash(argv: List[str], sandbox_dir: str) -> Optional[List[str]]:
      args = [_strip_project_root(a, sandbox_dir) for a in argv]
      if args and os.path.basename(args[0]) in ("bash", "sh"):
        args = args[1:]
      if not args or not allowed(args[0]):
        return None
      return [bash] + args

    return resolve_bash, [], None
  if kind == "python_script":
    py = sys.executable or shutil.which("python3") or "python3"

    def resolve_py(argv: List[str], sandbox_dir: str) -> Optional[List[str]]:
      args = [_strip_project_root(a, sandbox_dir) for a in argv]
      if args[:2] == ["uv", "run"]:
        args = args[2:]
        while args and args[0].startswith("-"):
          args = args[1:]
      elif args and os.path.basename(args[0]) in ("python", "python3"):
        args = args[1:]
      if not args or not allowed(args[0]):
        return None
      return [py, args[0]] + args[1:]

    return resolve_py, [], None
  if kind == "node_cli":
    tdir = tools_dir(entry, cache_dir)
    binary = os.path.join(tdir, "node_modules", ".bin", spec["bin"])
    node = shutil.which("node")
    if not os.path.isfile(binary) or node is None:
      reason = spec.get("unavailable_reason") or (
          f"{spec['bin']} CLI not installed (run fetch_packs.py with node/npm)")
      return None, [], reason

    def resolve_node(argv: List[str], sandbox_dir: str) -> Optional[List[str]]:
      del sandbox_dir  # Unused.
      if not argv or argv[0] != spec["bin"]:
        return None
      return [binary] + argv[1:]

    return resolve_node, [os.path.dirname(node)], None
  raise PackError(f"{entry['key']}: unknown pack_command kind {kind!r}")


# ---------------------------------------------------------------------------
# FrameworkPack.
# ---------------------------------------------------------------------------


class FrameworkPack:
  """One framework's shipped pack, loaded as a real host would load it."""

  def __init__(self, entry: Dict[str, Any], root: str,
               lock: Optional[Dict[str, Any]] = None,
               cache_dir: str = PACK_CACHE_DIR, verify: bool = True):
    self.entry = entry
    self.key: str = entry["key"]
    self.display_name: str = entry["display_name"]
    self.paradigm: str = entry["paradigm"]
    self.visibility: str = entry["visibility"]
    self.intent_map: Dict[str, Optional[str]] = dict(entry.get("intent_map", {}))
    self.context_layout: str = entry.get("context_layout", "generic")
    self.root = root
    self._cache_dir = cache_dir
    for intent in schema.INTENTS:
      self.intent_map.setdefault(intent, None)
    unknown = set(self.intent_map) - set(schema.INTENTS)
    if unknown:
      raise PackError(f"{self.key}: unknown intents {sorted(unknown)}")
    if self.context_layout not in _RENDERERS:
      raise PackError(f"{self.key}: unknown context_layout {self.context_layout}")

    self._raw: "collections.OrderedDict[str, bytes]" = collections.OrderedDict()
    for rel in expand_source_files(entry, root):
      with open(os.path.join(root, rel), "rb") as f:
        self._raw[rel] = f.read()
    self._generated: Dict[str, str] = dict(entry.get("generated_files", {}))
    self._hashes = {rel: sha256_bytes(b) for rel, b in self._raw.items()}
    for path, text in self._generated.items():
      self._hashes[f"generated:{path}"] = sha256_bytes(text.encode("utf-8"))
    if verify and lock is not None:
      self._verify_lock(lock)

    self._install_rules = [
        (re.compile(pat), repl) for pat, repl in entry.get("install_map", [])
    ]
    self._rewrites = [tuple(r) for r in entry.get("path_rewrites", [])]
    self._sandbox: "collections.OrderedDict[str, str]" = collections.OrderedDict()
    self._src_to_sandbox: Dict[str, str] = {}
    self._build_sandbox()
    for name in list(self.intent_map.values()):
      if name is not None and self._command_source(name) is None:
        raise PackError(f"{self.key}: intent command {name!r} is not a pack command")
    self.pack_commands = self._build_pack_commands()

  # -- Loading -------------------------------------------------------------

  def _verify_lock(self, lock: Dict[str, Any]) -> None:
    locked = lock.get("files", {})
    if lock.get("ref") and lock["ref"] != self.entry["source"].get("ref", lock["ref"]):
      raise PackIntegrityError(
          f"{self.key}: registry ref {self.entry['source'].get('ref')} != lock ref {lock['ref']}")
    if set(locked) != set(self._hashes):
      missing = sorted(set(self._hashes) ^ set(locked))[:5]
      raise PackIntegrityError(
          f"{self.key}: loaded file set differs from lockfile (e.g. {missing}); "
          "re-run fetch_packs.py")
    bad = [p for p, h in self._hashes.items() if locked.get(p) != h]
    if bad:
      raise PackIntegrityError(
          f"{self.key}: sha256 mismatch vs lockfile for {bad[:5]}; re-run fetch_packs.py")

  def raw_text(self, rel: str) -> Optional[str]:
    """Upstream text of a loaded file, or None if the pack does not load it."""
    data = self._raw.get(rel)
    return None if data is None else data.decode("utf-8", errors="replace")

  def _rewrite(self, text: str) -> str:
    for old, new in self._rewrites:
      text = text.replace(old, new)
    return text

  def _sandbox_path(self, rel: str) -> str:
    for pat, repl in self._install_rules:
      m = pat.fullmatch(rel)
      if m:
        return m.expand(repl)
    return f".agent/{self.key}/{rel}"

  def _build_sandbox(self) -> None:
    transform = self.entry.get("transform")
    for rel, data in self._raw.items():
      text = data.decode("utf-8", errors="replace")
      dest = self._sandbox_path(rel)
      if transform == "speckit_agy":
        m = re.fullmatch(r"templates/commands/([\w.-]+)\.md", rel)
        if m:
          text = _speckit_command_to_skill(m.group(1), text, "agy")
        elif rel.startswith("templates/"):
          # shared_infra.py resolves command refs in installed templates too.
          text = _speckit_command_refs(text)
      text = self._rewrite(text)
      self._sandbox[dest] = text
      self._src_to_sandbox[rel] = dest
    for src, dest in self.entry.get("copies", []):
      if src in self._raw:
        self._sandbox[dest] = self._rewrite(self._raw[src].decode("utf-8", errors="replace"))
    for path, text in self._generated.items():
      self._sandbox[path] = text

  def _command_source(self, name: str) -> Optional[str]:
    rel = self.entry.get("commands", {}).get(name)
    if rel is None:
      rel = self.entry.get("skills_index", {}).get(name)
    return rel

  def _build_pack_commands(self) -> List[Dict[str, Any]]:
    out = []
    for spec in self.entry.get("pack_commands", []):
      resolve, path, reason = _make_resolver(spec, self.entry, self._cache_dir)
      item: Dict[str, Any] = {
          "id": spec["id"],
          "match": spec["match"],
          "resolve": resolve,
          "path": path,
          "env": dict(spec.get("env", {})),
      }
      if reason:
        item["unavailable_reason"] = reason
      out.append(item)
    return out

  # -- Public interface ----------------------------------------------------

  def skills(self) -> List[Tuple[str, str, str]]:
    """Returns [(name, one-line description, sandbox path)] for the index."""
    out = []
    for name, rel in self.entry.get("skills_index", {}).items():
      text = self._raw[rel].decode("utf-8", errors="replace")
      if rel.endswith(".toml"):
        desc, _ = parse_toml_command(text)
      else:
        meta, body = split_frontmatter(text)
        desc = meta.get("description") or _first_paragraph(body)
      out.append((name, one_line(desc), self._src_to_sandbox[rel]))
    return out

  def always_on(self) -> List[Tuple[str, str]]:
    """Returns [(sandbox path, text with frontmatter stripped)] in order."""
    out = []
    for rel in self.entry.get("always_on", []):
      text = self._raw[rel].decode("utf-8", errors="replace")
      _, body = split_frontmatter(text)
      out.append((self._src_to_sandbox[rel], self._rewrite(body).strip("\n")))
    return out

  def system_prompt(self, base_prompt: str) -> str:
    """Base prompt + always-on files in order + skills index."""
    parts = [base_prompt.rstrip("\n")]
    rules = self.always_on()
    if rules:
      parts.append(
          "# Installed workspace instructions (always on)\n\n"
          "The host loads the following instruction files into every "
          "conversation in this workspace.")
      for path, text in rules:
        parts.append(f'<instructions file="{path}">\n{text}\n</instructions>')
    skills = self.skills()
    if skills:
      lines = [
          "# Installed skills and commands",
          "",
          "The following on-demand instruction files are installed in this "
          "workspace. When one is relevant to the task, read it with read_file "
          "at the path shown and follow it. The user may also invoke one by "
          "name as a slash command.",
          "",
      ]
      for name, desc, path in skills:
        lines.append(f"- {name}: {desc} (path: {path})")
      parts.append("\n".join(lines))
    return "\n\n".join(parts) + "\n"

  def sandbox_files(self) -> Dict[str, str]:
    """Pack files a real install places in or near the repo (path -> text)."""
    return dict(self._sandbox)

  def render_context(self, project_context: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Neutral project facts -> this framework's native context files."""
    out: Dict[str, str] = collections.OrderedDict()
    _RENDERERS[self.context_layout](_Ctx(project_context), out, self)
    return dict(out)

  def command_body(self, name: str) -> Optional[str]:
    """Body a host injects when the user types `/<name>` (frontmatter removed)."""
    rel = self._command_source(name)
    if rel is None:
      return None
    if rel.endswith(".toml"):
      _, prompt = parse_toml_command(self._raw[rel].decode("utf-8", errors="replace"))
      return self._rewrite(prompt)
    _, body = split_frontmatter(self._sandbox[self._src_to_sandbox[rel]])
    return body

  def expand_user_message(self, intent: str, text: str) -> str:
    """Host-style slash-command expansion of the user's message.

    When `intent_map[intent]` is null the message is returned unchanged.
    Otherwise the command body is inlined with the user's text substituted for
    `$ARGUMENTS` (Claude/Antigravity/spec-kit convention) or `{{args}}` (Gemini
    CLI convention), or appended under `User request:` when the body has no
    placeholder.

    Args:
      intent: Scenario intent (one of schema.INTENTS).
      text: The user's original message.

    Returns:
      The message as the model receives it.
    """
    if intent not in schema.INTENTS:
      raise PackError(f"unknown intent {intent!r}")
    name = self.intent_map.get(intent)
    if not name:
      return text
    body = (self.command_body(name) or "").strip("\n")
    # Like Claude Code / Antigravity skill invocation, tell the model where the
    # command's files live so relative references (./workflow.md) resolve.
    header = f"Base directory for this command: {self.command_dir(name)}\n\n"
    if "$ARGUMENTS" in body:
      return header + body.replace("$ARGUMENTS", text)
    if "{{args}}" in body:
      return header + body.replace("{{args}}", text)
    return header + body + "\n\nUser request: " + text

  def command_dir(self, name: str) -> str:
    """Sandbox directory holding the command's file."""
    rel = self._command_source(name)
    if rel is None:
      raise PackError(f"{self.key}: unknown command {name}")
    return os.path.dirname(self._src_to_sandbox[rel])

  def identifiers(self) -> List[str]:
    """Every framework-identifying string (longest first) for blinding."""
    ids = {self.key, self.display_name}
    ids.update(self.entry.get("identifiers", []))
    names = list(self.entry.get("skills_index", {})) + list(
        self.entry.get("commands", {}))
    # Bare skill names are emitted only when they carry a framework-distinctive
    # token; generic names (implement, research, pr, ...) would otherwise blind
    # ordinary words in user and agent text. Their "/name" form is kept.
    tokens = [t.lower() for t in self.entry.get("bare_name_tokens", [])]
    for name in names:
      ids.add("/" + name)
      if any(t in name.lower() for t in tokens):
        ids.add(name)
    for path in self._sandbox:
      if path.startswith(_GENERIC_PATH_PREFIXES):
        continue
      segs = path.split("/")
      top = segs[0] + "/"
      if top in (".agent/", ".agents/") and len(segs) > 2:
        ids.add("/".join(segs[:2]) + "/")
        ids.add("/".join(segs[:3]))
      elif len(segs) > 1:
        ids.add(top)
      else:
        ids.add(path)
    for _, _, path in self.skills():
      ids.add(path)
    for path, _ in self.always_on():
      ids.add(path)
      ids.add(os.path.basename(path))
    # Pack-tool script and CLI names show up in commands and their output.
    for spec in self.entry.get("pack_commands", []):
      if spec.get("bin"):
        ids.add(spec["bin"])
      for path in self._sandbox:
        if any(glob_match(path, g) for g in spec.get("path_globs", [])):
          ids.add(path)
          ids.add(os.path.basename(path))
    ids.update(_LAYOUT_IDENTIFIERS.get(self.context_layout, ()))
    ids = {i for i in ids if i and len(i) >= 3}
    return sorted(ids, key=lambda s: (-len(s), s))

  def file_hashes(self) -> Dict[str, str]:
    """sha256 of every loaded upstream file (and generated install file)."""
    return dict(self._hashes)

  def size_stats(self) -> Dict[str, int]:
    """Character counts: always-on (as injected) and total pack text."""
    always = sum(len(t) for _, t in self.always_on())
    index = len(self.system_prompt("")) - 1 if (self.always_on() or self.skills()) else 0
    total = sum(len(b.decode("utf-8", errors="replace")) for b in self._raw.values())
    total += sum(len(t) for t in self._generated.values())
    return {
        "always_on_chars": always,
        "system_prompt_addition_chars": max(index, 0),
        "always_on_tokens_est": always // 4,
        "system_prompt_addition_tokens_est": max(index, 0) // 4,
        "total_pack_chars": total,
        "total_pack_tokens_est": total // 4,
        "files": len(self._raw),
        "skills": len(self.entry.get("skills_index", {})),
    }


# ---------------------------------------------------------------------------
# Registry loading.
# ---------------------------------------------------------------------------


def read_registry(path: str) -> List[Dict[str, Any]]:
  with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
  return list(data.get("frameworks", []))


def read_lock(path: str) -> Dict[str, Any]:
  if not os.path.isfile(path):
    return {}
  with open(path, "r", encoding="utf-8") as f:
    return json.load(f).get("frameworks", {})


def load_registry(paths: List[str], cache_dir: str = PACK_CACHE_DIR,
                  verify: bool = True) -> List[FrameworkPack]:
  """Loads every non-excluded framework from the given registry files.

  Missing registry files are skipped (the OSS copy has no internal registry).
  Each registry's lockfile (`packs.lock.json` for `registry.json`,
  `packs_<suffix>.lock.json` for `registry_<suffix>.json`) must contain every
  loaded framework when `verify` is true.

  Args:
    paths: Registry JSON paths.
    cache_dir: Root of fetched git packs.
    verify: Check file hashes against the lockfile.

  Returns:
    Loaded packs in registry order.

  Raises:
    PackError: On a missing pack, duplicate key, or integrity failure.
  """
  packs: List[FrameworkPack] = []
  seen = set()
  for path in paths:
    if not os.path.isfile(path):
      continue
    lock = read_lock(lock_path_for(path))
    for entry in read_registry(path):
      if entry.get("excluded"):
        continue
      key = entry["key"]
      if key in seen:
        raise PackError(f"duplicate framework key {key}")
      seen.add(key)
      root = source_root(entry, cache_dir)
      if not os.path.isdir(root):
        raise PackError(
            f"{key}: pack not found at {root}; run fetch_packs.py first")
      if verify and key not in lock:
        raise PackIntegrityError(
            f"{key}: not in {lock_path_for(path)}; run fetch_packs.py")
      packs.append(FrameworkPack(entry, root, lock.get(key), cache_dir, verify))
  return packs


def default_registry_paths() -> List[str]:
  return [
      os.path.join(FRAMEWORKS_DIR, "registry.json"),
      os.path.join(FRAMEWORKS_DIR, "registry_internal.json"),
  ]
