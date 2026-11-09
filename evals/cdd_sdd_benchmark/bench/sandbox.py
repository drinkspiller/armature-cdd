"""Agentic sandbox: a throwaway git repo with tools, mocks, and an action log.

Every rollout gets a fresh, opaquely named directory under `/tmp/cddbench/`
(never inside a source checkout) laid out as:

  <root_dir>/repo   the repository the agent works in (git baseline commit)
  <root_dir>/home   HOME for every subprocess (scrubbed environment)
  <root_dir>/tmp    harness scratch (temporary git index for the final diff)

Tool semantics follow DESIGN.md ("Agent loop"). `run_command` evaluates each
shell segment (split on `|`, `&&`, `||`, `;`) in this order:

  1. scenario mock (regex `re.search` on the segment) -> canned output;
  2. pack tooling declared by the framework pack (`pack_commands`), executed
     for real from the sandbox copy with a scrubbed environment;
  3. a small allowlist of read-mostly builtins (git, ls, cat, head, tail, grep,
     wc, find, diff) run with no shell, plus `sqlite3 <fixture db> <sql>`,
     which is implemented in-process with Python's sqlite3 module;
  4. otherwise: `command not available in this sandbox`, executed=False.

Every attempt is logged as a `schema.Action`. File changes are detected by
hashing the tree after each mutating tool call (`file_events`).
"""

from __future__ import annotations

import collections
import csv
import dataclasses
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple

from bench import schema

# Neutral base: the agent sees absolute sandbox paths, so they must not name
# any framework, model, or scenario.
SANDBOX_BASE = "/tmp/cddbench"
COMMAND_TIMEOUT_S = 20
PACK_TOOL_TIMEOUT_S = 60
NOT_AVAILABLE = "command not available in this sandbox"
MAX_READ_CHARS = 200_000
MAX_CMD_OUTPUT_CHARS = 30_000
MAX_DIFF_CONTENT_BYTES = 200_000

REAL_COMMANDS = frozenset(
    {"git", "ls", "cat", "head", "tail", "grep", "wc", "find", "diff",
     "sqlite3"}
)
GIT_SUBCOMMANDS = frozenset({
    "add", "apply", "blame", "branch", "cat-file", "checkout", "cherry-pick",
    "clean", "commit", "config", "describe", "diff", "grep", "log", "ls-files",
    "ls-tree", "merge", "mv", "rebase", "reflog", "reset", "restore", "revert",
    "rev-list", "rev-parse", "rm", "shortlog", "show", "stash", "status",
    "switch", "tag",
})
GIT_CONFIG_READ_FLAGS = frozenset(
    {"--get", "--get-all", "--get-regexp", "--list", "-l"}
)
GIT_BLOCKED_FLAGS = ("-O", "--open-files-in-pager", "--exec", "-x", "--output",
                     "--upload-pack", "--receive-pack")
FIND_BLOCKED = frozenset({"-exec", "-execdir", "-ok", "-okdir", "-delete",
                          "-fprint", "-fprint0", "-fprintf", "-fls"})
SQLITE_FLAGS = frozenset({
    "-header", "-noheader", "-csv", "-json", "-line", "-list", "-column",
    "-box", "-markdown", "-table", "-batch", "-bail", "-readonly",
})
READ_ONLY_PROGRAMS = frozenset(
    {"cat", "head", "tail", "grep", "wc", "ls", "find", "diff", "sort",
     "uniq", "less", "more", "file", "stat"})
GIT_READ_SUBCOMMANDS = frozenset({
    "log", "show", "diff", "status", "blame", "grep", "ls-files", "ls-tree",
    "rev-parse", "rev-list", "cat-file", "shortlog", "describe", "reflog",
})
ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
CONTROL_OPS = frozenset({"|", "&&", "||", ";", "&"})
REDIRECT_OPS = frozenset({">", ">>", "<", ">&", "&>", ">|", "<<", "<<<"})
SECRET_ENV_RE = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", re.I)
_SQLITE_DENY_ACTIONS = frozenset({24, 25})  # SQLITE_ATTACH, SQLITE_DETACH.


class SandboxError(RuntimeError):
  """Harness-side sandbox failure (setup or invariant violation)."""


class ToolError(Exception):
  """A tool call the agent made incorrectly; returned to the model as text."""


_ACTION_FIELDS = frozenset(f.name for f in dataclasses.fields(schema.Action))


def _sha(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()


def _cap(text: str, limit: int) -> str:
  if len(text) <= limit:
    return text
  return text[:limit] + f"\n... [truncated {len(text) - limit} chars]"


def _norm_rel(path: str) -> str:
  """Normalizes a user-supplied relative path; raises ToolError on escapes."""
  if path is None:
    path = ""
  if not isinstance(path, str):
    raise ToolError("path must be a string")
  p = path.strip()
  if p in ("", ".", "./"):
    return ""
  if os.path.isabs(p) or p.startswith("~"):
    raise ToolError(f"path must be relative to the repository root: {path}")
  norm = os.path.normpath(p).replace(os.sep, "/")
  parts = norm.split("/")
  if norm == ".." or parts[0] == "..":
    raise ToolError(f"path escapes the repository: {path}")
  if parts[0] == ".git":
    raise ToolError(f"the .git directory is not accessible: {path}")
  return "" if norm == "." else norm


def split_command(command: str) -> List[Dict[str, Any]]:
  """Splits a shell command into segments joined by control operators.

  Returns [{"op": <operator before this segment or None>, "tokens": [...],
  "redirects": [(op, target), ...], "text": <normalized segment text>}].
  Raises ValueError on unbalanced quotes or unsupported syntax.
  """
  lex = shlex.shlex(command, posix=True, punctuation_chars=True)
  lex.whitespace_split = True
  tokens = list(lex)
  segments: List[Dict[str, Any]] = []
  cur: List[str] = []
  op: Optional[str] = None

  def flush(next_op: Optional[str]) -> None:
    nonlocal cur, op
    if not cur:
      if next_op is not None:
        raise ValueError(f"syntax error near '{next_op}'")
      return
    words: List[str] = []
    redirects: List[Tuple[str, str]] = []
    i = 0
    while i < len(cur):
      t = cur[i]
      if t in REDIRECT_OPS:
        if i + 1 >= len(cur):
          raise ValueError(f"missing redirection target after '{t}'")
        if words and words[-1] in ("1", "2") and t != "<":
          words.pop()  # File-descriptor prefix such as `2>`.
        redirects.append((t, cur[i + 1]))
        i += 2
        continue
      if t in ("(", ")") or "$(" in t or "`" in t:
        raise ValueError("subshells and command substitution are not supported")
      words.append(t)
      i += 1
    if not words:
      raise ValueError("empty command segment")
    segments.append({
        "op": op,
        "tokens": words,
        "redirects": redirects,
        "text": shlex.join(words),
    })
    cur = []
    op = next_op

  for t in tokens:
    if t in CONTROL_OPS:
      flush(t)
    elif t and set(t) <= set("();<>|&") and t not in REDIRECT_OPS:
      raise ValueError(f"unsupported shell operator '{t}'")
    else:
      cur.append(t)
  if cur:
    flush(None)
  elif op is not None and op != ";" and op != "&":
    raise ValueError(f"command ends with operator '{op}'")
  return segments


def _is_read_only(tokens: List[str]) -> bool:
  if not tokens:
    return False
  if tokens[0] in READ_ONLY_PROGRAMS:
    return True
  if tokens[0] == "git":
    rest = [t for t in tokens[1:] if t not in ("--no-pager", "-P")]
    return bool(rest) and rest[0] in GIT_READ_SUBCOMMANDS
  return False


class Sandbox:
  """A rollout's repository plus tool implementations and logs."""

  def __init__(
      self,
      root_dir: str,
      scenario: schema.Scenario,
      pack_files: Optional[Dict[str, str]] = None,
      context_files: Optional[Dict[str, str]] = None,
      pack_commands: Optional[List[Dict[str, Any]]] = None,
      allowed_base: str = SANDBOX_BASE,
  ):
    real_root = os.path.realpath(root_dir)
    base = os.path.realpath(allowed_base)
    if not real_root.startswith(base + os.sep):
      raise SandboxError(f"sandbox must live under {allowed_base}: {root_dir}")
    repo_tree = os.path.realpath(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if real_root == repo_tree or real_root.startswith(repo_tree + os.sep):
      raise SandboxError("sandbox must never be inside a source checkout")
    self.scenario = scenario
    self.root_dir = real_root
    self.repo = os.path.join(real_root, "repo")
    self.home = os.path.join(real_root, "home")
    self.tmp = os.path.join(real_root, "tmp")
    self.pack_files = dict(pack_files or {})
    self.pack_commands = list(pack_commands or [])
    self.action_log: List[schema.Action] = []
    self.file_events: List[schema.FileEvent] = []
    self.session = 0
    self.turn = 0
    self.step = 0
    self.exports: Dict[str, str] = {}  # `export K=V`, per session.
    self.db_paths: Dict[str, List[str]] = {}
    self.baseline_rowcounts: Dict[str, Dict[str, int]] = {}
    self.baseline_commit = ""

    if os.path.exists(real_root):
      shutil.rmtree(real_root)
    for d in (self.repo, self.home, self.tmp):
      os.makedirs(d)
    self._setup(context_files or {})
    self._snapshot = self._hash_tree()

  # ---------------------------------------------------------------- setup

  def _write_setup_file(self, rel: str, content: str, origin: str,
                        owners: Dict[str, str]) -> None:
    try:
      norm = _norm_rel(rel)
    except ToolError as e:
      raise SandboxError(f"{origin} file has an invalid path: {e}") from None
    if not norm:
      raise SandboxError(f"{origin} file has an empty path")
    if owners.get(norm) == "fixture" and origin != "fixture":
      raise SandboxError(f"{origin} file would overwrite fixture file {norm}")
    owners[norm] = origin
    full = os.path.join(self.repo, norm)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
      f.write(content)

  def _setup(self, context_files: Dict[str, str]) -> None:
    owners: Dict[str, str] = {}
    fixture = self.scenario.fixture or {}
    for rel, content in (fixture.get("files") or {}).items():
      self._write_setup_file(rel, content, "fixture", owners)
    for rel, content in self.pack_files.items():
      self._write_setup_file(rel, content, "pack", owners)
    for rel, content in context_files.items():
      self._write_setup_file(rel, content, "context", owners)
    self.pack_files = {_norm_rel(k): v for k, v in self.pack_files.items()}

    for rel, stmts in (fixture.get("sqlite") or {}).items():
      norm = _norm_rel(rel)
      if norm in owners:
        raise SandboxError(f"sqlite db path collides with a file: {norm}")
      full = os.path.join(self.repo, norm)
      os.makedirs(os.path.dirname(full), exist_ok=True)
      conn = sqlite3.connect(full)
      try:
        for stmt in stmts:
          conn.executescript(stmt)
        conn.commit()
      finally:
        conn.close()
      self.db_paths[norm] = list(stmts)
      self.baseline_rowcounts[norm] = self._rowcounts(full)

    with open(os.path.join(self.home, ".gitconfig"), "w") as f:
      f.write("[user]\n\tname = Sandbox User\n\temail = user@example.com\n"
              "[init]\n\tdefaultBranch = main\n[core]\n\tpager = cat\n")
    self._git_setup("init", "-q")
    exclude = os.path.join(self.repo, ".git", "info", "exclude")
    os.makedirs(os.path.dirname(exclude), exist_ok=True)
    with open(exclude, "a", encoding="utf-8") as f:
      for db in self.db_paths:
        f.write(f"/{db}\n/{db}-journal\n/{db}-wal\n/{db}-shm\n")
    self._git_setup("add", "-A")
    env = {"GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
           "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}
    self._git_setup("commit", "-q", "--allow-empty", "-m", "Initial commit",
                    extra_env=env)
    self.baseline_commit = self._git_setup("rev-parse", "HEAD").strip()

  def _env(self, extra_path: Optional[List[str]] = None,
           extra_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Scrubbed environment for every subprocess (no secrets, no host HOME)."""
    path = list(extra_path or []) + ["/usr/local/bin", "/usr/bin", "/bin"]
    env = {
        "PATH": ":".join(path),
        "HOME": self.home,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "TMPDIR": self.tmp,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.path.join(self.home, ".gitconfig"),
        "GIT_PAGER": "cat",
        "PAGER": "cat",
        "GIT_EDITOR": "true",
        "EDITOR": "true",
        "VISUAL": "true",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "true",
    }
    for k, v in (extra_env or {}).items():
      if not SECRET_ENV_RE.search(k) and k not in ("HOME", "PATH"):
        env[str(k)] = str(v)
    assert not any(SECRET_ENV_RE.search(k) for k in env)
    return env

  def _git_setup(self, *args: str,
                 extra_env: Optional[Dict[str, str]] = None) -> str:
    env = self._env()
    env.update(extra_env or {})
    p = subprocess.run(["git", *args], cwd=self.repo, env=env,
                       capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
      raise SandboxError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout

  # -------------------------------------------------------------- logging

  def set_position(self, session: int, turn: int, step: int) -> None:
    if session != self.session:
      self.exports = {}  # Shell state does not survive a fresh session.
    self.session, self.turn, self.step = session, turn, step

  def _log(self, type_: str, **kw: Any) -> schema.Action:
    if "source" in kw and "source" not in _ACTION_FIELDS:
      src = kw.pop("source")
      if src and kw.get("error") is None and src not in ("builtin",):
        kw["error"] = f"source={src}"
    a = schema.Action(session=self.session, turn=self.turn, step=self.step,
                      type=type_, **kw)
    self.action_log.append(a)
    return a

  def _ignored_untracked(self) -> set:
    """Untracked files git ignores (pack tool caches), as final_diff does."""
    p = subprocess.run(
        ["git", "ls-files", "-z", "--others", "--ignored", "--exclude-standard"],
        cwd=self.repo, env=self._env(), capture_output=True, timeout=60)
    if p.returncode != 0:
      raise SandboxError("git ls-files failed: "
                         + p.stderr.decode("utf-8", "replace").strip())
    return {x for x in p.stdout.decode("utf-8", "replace").split("\0") if x}

  def log_refused(self, name: str, args: Dict[str, Any], reason: str,
                  source: str = "wrap_up_refused") -> None:
    """Logs a tool call the harness declined to execute (e.g. step limit).

    The distinct source keeps step-limit refusals separate from sandbox
    refusals ("refused") in per-framework command statistics.
    """
    args = args or {}
    self._log(name, path=args.get("path") if name != "run_command" else None,
              command=args.get("command") if name == "run_command" else None,
              error=reason, source=source)

  def _hash_tree(self) -> Dict[str, str]:
    out: Dict[str, str] = {}
    skip = self._ignored_untracked() if self.baseline_commit else set()
    for db in self.db_paths:
      skip.update({db, f"{db}-journal", f"{db}-wal", f"{db}-shm"})
    for dirpath, dirnames, filenames in os.walk(self.repo):
      rel_dir = os.path.relpath(dirpath, self.repo)
      if rel_dir == ".":
        dirnames[:] = [d for d in dirnames if d != ".git"]
        rel_dir = ""
      for name in filenames:
        rel = f"{rel_dir}/{name}" if rel_dir else name
        rel = rel.replace(os.sep, "/")
        if rel in skip:
          continue
        full = os.path.join(dirpath, name)
        if os.path.islink(full):
          out[rel] = "symlink:" + os.readlink(full)
          continue
        try:
          with open(full, "rb") as f:
            out[rel] = _sha(f.read())
        except OSError:
          continue
    return out

  def _record_file_events(self) -> None:
    new = self._hash_tree()
    old = self._snapshot
    for path in sorted(set(old) | set(new)):
      if path not in old:
        op = "create"
      elif path not in new:
        op = "delete"
      elif old[path] != new[path]:
        op = "modify"
      else:
        continue
      self.file_events.append(schema.FileEvent(
          session=self.session, turn=self.turn, path=path, op=op))
    self._snapshot = new

  # ------------------------------------------------------------ dispatch

  def call_tool(self, name: str, args: Dict[str, Any]) -> str:
    """Runs one tool call and returns the text result for the model."""
    args = args or {}
    try:
      if name == "list_dir":
        return self.list_dir(args.get("path", "."))
      if name == "read_file":
        return self.read_file(args.get("path"))
      if name == "write_file":
        return self.write_file(args.get("path"), args.get("content"))
      if name == "edit_file":
        return self.edit_file(args.get("path"), args.get("old"),
                              args.get("new"))
      if name == "run_command":
        return self.run_command(args.get("command"))
      if name == "ask_user":
        return self.ask_user(args.get("question", ""), args.get("options"))
      return f"ERROR: unknown tool '{name}'"
    finally:
      if name in ("write_file", "edit_file", "run_command"):
        self._record_file_events()

  def _rel(self, path: Any) -> str:
    """Like _norm_rel, but accepts absolute paths that lie inside the repo."""
    if isinstance(path, str) and os.path.isabs(path.strip()):
      p = os.path.normpath(path.strip())
      if p == self.repo or p.startswith(self.repo + os.sep):
        path = os.path.relpath(p, self.repo)
    return _norm_rel(path)

  def _full(self, rel: str) -> str:
    full = os.path.realpath(os.path.join(self.repo, rel))
    if full != self.repo and not full.startswith(self.repo + os.sep):
      raise ToolError(f"path escapes the repository: {rel}")
    return full

  # --------------------------------------------------------------- tools

  def list_dir(self, path: Any = ".") -> str:
    try:
      rel = self._rel(path)
      full = self._full(rel)
      if not os.path.isdir(full):
        raise ToolError(f"not a directory: {path}")
      entries = []
      for name in sorted(os.listdir(full)):
        if not rel and name == ".git":
          continue
        entries.append(name + "/" if os.path.isdir(os.path.join(full, name))
                       else name)
      self._log("list_dir", path=rel or ".", executed=True)
      return "\n".join(entries) if entries else "(empty directory)"
    except ToolError as e:
      self._log("list_dir", path=str(path), error=str(e))
      return f"ERROR: {e}"

  def read_file(self, path: Any) -> str:
    try:
      rel = self._rel(path)
      if not rel:
        raise ToolError("path is required")
      if rel in self.db_paths:
        raise ToolError(f"{rel} is a SQLite database; query it with "
                        f"`sqlite3 {rel} \"<sql>\"`")
      full = self._full(rel)
      if not os.path.isfile(full):
        raise ToolError(f"no such file: {rel}")
      with open(full, "rb") as f:
        text = f.read().decode("utf-8", "replace")
      self._log("read_file", path=rel, executed=True)
      return _cap(text, MAX_READ_CHARS)
    except ToolError as e:
      self._log("read_file", path=str(path), error=str(e))
      return f"ERROR: {e}"

  def write_file(self, path: Any, content: Any) -> str:
    try:
      rel = self._rel(path)
      if not rel:
        raise ToolError("path is required")
      if not isinstance(content, str):
        raise ToolError("content must be a string")
      if rel in self.db_paths:
        raise ToolError(f"{rel} is a SQLite database and cannot be written")
      full = self._full(rel)
      if os.path.isdir(full):
        raise ToolError(f"is a directory: {rel}")
      os.makedirs(os.path.dirname(full), exist_ok=True)
      existed = os.path.exists(full)
      with open(full, "w", encoding="utf-8") as f:
        f.write(content)
      self._log("write_file", path=rel, executed=True)
      return f"{'Updated' if existed else 'Created'} {rel} ({len(content)} chars)"
    except ToolError as e:
      self._log("write_file", path=str(path), error=str(e))
      return f"ERROR: {e}"

  def edit_file(self, path: Any, old: Any, new: Any) -> str:
    try:
      rel = self._rel(path)
      if not rel:
        raise ToolError("path is required")
      if not isinstance(old, str) or not isinstance(new, str):
        raise ToolError("old and new must be strings")
      if not old:
        raise ToolError("old must be non-empty; use write_file to create files")
      if rel in self.db_paths:
        raise ToolError(f"{rel} is a SQLite database and cannot be edited")
      full = self._full(rel)
      if not os.path.isfile(full):
        raise ToolError(f"no such file: {rel}")
      with open(full, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
      n = text.count(old)
      if n == 0:
        raise ToolError(f"old text not found in {rel}")
      if n > 1:
        raise ToolError(f"old text occurs {n} times in {rel}; make it unique")
      with open(full, "w", encoding="utf-8") as f:
        f.write(text.replace(old, new, 1))
      self._log("edit_file", path=rel, executed=True)
      return f"Edited {rel}"
    except ToolError as e:
      self._log("edit_file", path=str(path), error=str(e))
      return f"ERROR: {e}"

  def ask_user(self, question: Any, options: Any = None) -> str:
    del options  # Recorded in the transcript's tool call args.
    self._log("ask_user", executed=True)
    return str(question or "")

  # ---------------------------------------------------------- run_command

  def run_command(self, command: Any) -> str:
    if not isinstance(command, str) or not command.strip():
      self._log("run_command", command=str(command), error="empty command",
                source="refused")
      return "ERROR: command must be a non-empty string"
    try:
      segments = split_command(command)
    except ValueError as e:
      self._log("run_command", command=command, error=f"parse error: {e}",
                source="refused")
      return f"exit_code: 2\nstderr:\n{NOT_AVAILABLE}: {e}"
    single = len(segments) == 1
    out_chunks: List[str] = []
    err_chunks: List[str] = []
    exit_code = 0
    pipe_data: Optional[str] = None
    cwd = self.repo
    for idx, seg in enumerate(segments):
      op = seg["op"]
      if (op == "&&" and exit_code != 0) or (op == "||" and exit_code == 0):
        self._log("run_command", command=seg["text"],
                  error="skipped: short-circuited by previous segment",
                  source="refused")
        pipe_data = None
        continue
      stdin = pipe_data if op == "|" else None
      piped_out = (idx + 1 < len(segments) and segments[idx + 1]["op"] == "|")
      candidates = [seg["text"], " ".join(seg["tokens"])]
      if single:
        candidates.append(command.strip())
      code, out, err, cwd = self._run_segment(seg, candidates, stdin, cwd)
      exit_code = code
      if piped_out:
        pipe_data = out
      else:
        pipe_data = None
        if out:
          out_chunks.append(out)
      if err:
        err_chunks.append(err)
    stdout = _cap("".join(out_chunks), MAX_CMD_OUTPUT_CHARS)
    stderr = _cap("".join(err_chunks), MAX_CMD_OUTPUT_CHARS // 3)
    res = f"exit_code: {exit_code}\nstdout:\n{stdout}"
    if stderr:
      res += f"\nstderr:\n{stderr}"
    return res

  def _match_mock(self, candidates: List[str], tokens: List[str],
                  env: Optional[Dict[str, str]] = None
                  ) -> Optional[Dict[str, Any]]:
    """Returns the first scenario mock matching the segment, if any.

    Read-only inspection (cat/grep/... a script, `git log -- script`) must not
    trigger a mock that merely mentions the script's name, so for read-only
    programs a mock applies only when its regex matches at the segment start.
    """
    read_only = _is_read_only(tokens)
    passes = []
    if env:
      # Environment-sensitive mocks (e.g. `DB_URL=...localhost... reset.sh`)
      # see active variables as a `K=V ` prefix and take precedence.
      prefix = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
      passes.append([f"{prefix} {shlex.join(tokens)}"])
    passes.append(candidates)
    for cands in passes:
      for m in self.scenario.mocks or []:
        try:
          rx = re.compile(m["match"])
        except re.error as e:
          raise SandboxError(f"bad mock regex {m.get('id')}: {e}") from None
        if read_only:
          hit = any(rx.match(c) for c in cands)
        else:
          hit = any(rx.search(c) for c in cands)
        if hit:
          return m
    return None

  def _run_segment(
      self, seg: Dict[str, Any], candidates: List[str], stdin: Optional[str],
      cwd: str
  ) -> Tuple[int, str, str, str]:
    """Evaluates one segment. Returns (exit_code, stdout, stderr, cwd)."""
    tokens: List[str] = list(seg["tokens"])
    text: str = seg["text"]

    # Variable assignments: `K=V` alone or `export K=V` persist for the rest
    # of the session; `K=V cmd` applies to that command only. (No `$VAR`
    # expansion: there is no shell.)
    inline: Dict[str, str] = {}
    while tokens and ASSIGN_RE.match(tokens[0]):
      k, v = tokens.pop(0).split("=", 1)
      inline[k] = v
    if not tokens or tokens[0] in ("export", "unset"):
      if tokens and tokens[0] == "unset":
        for k in tokens[1:]:
          self.exports.pop(k, None)
      else:
        self.exports.update(inline)
        for t in tokens[1:]:
          if ASSIGN_RE.match(t):
            k, v = t.split("=", 1)
            self.exports[k] = v
      self._log("run_command", command=text, executed=True, source="builtin")
      return 0, "", "", cwd
    env = {**self.exports, **inline}
    persisted = {k: v for k, v in self.exports.items() if k not in inline}
    if persisted:
      # Log what effectively ran, so command checks see the same environment
      # the mock matcher saw (e.g. `DB_URL=...localhost... ./reset.sh`).
      text = " ".join(f"{k}={shlex.quote(v)}"
                      for k, v in persisted.items()) + " " + text
    if inline:
      stripped = shlex.join(tokens)
      candidates = list(candidates) + [stripped, " ".join(tokens)]

    mock = self._match_mock(candidates, tokens, env)
    if mock is not None:
      self._log("run_command", command=text, executed=True,
                mock_id=mock["id"], destructive=bool(mock.get("destructive")),
                source="mock")
      out = str(mock.get("stdout", ""))
      if out and not out.endswith("\n"):
        out += "\n"
      return int(mock.get("exit_code", 0)), out, str(
          mock.get("stderr", "")), cwd

    # Input/output redirection: allow only harmless forms.
    for rop, target in seg["redirects"]:
      if rop == "<":
        continue
      if target == "/dev/null" or (rop == ">&" and target in ("1", "2")):
        continue
      msg = (f"{NOT_AVAILABLE}: output redirection ('{rop} {target}') is not "
             "supported; use write_file")
      self._log("run_command", command=text, error=msg, source="refused")
      return 2, "", msg + "\n", cwd
    for rop, target in seg["redirects"]:
      if rop == "<":
        try:
          with open(self._full(self._rel(self._rel_from(cwd, target))),
                    "r", encoding="utf-8", errors="replace") as f:
            stdin = f.read()
        except (ToolError, OSError) as e:
          self._log("run_command", command=text, error=str(e),
                    source="refused")
          return 1, "", f"{e}\n", cwd

    prog = tokens[0]
    if prog == "cd":
      target = tokens[1] if len(tokens) > 1 else "."
      try:
        rel = self._rel(self._rel_from(cwd, target))
        full = self._full(rel)
        if not os.path.isdir(full):
          raise ToolError(f"cd: no such directory: {target}")
      except ToolError as e:
        self._log("run_command", command=text, error=str(e), source="builtin")
        return 1, "", f"{e}\n", cwd
      self._log("run_command", command=text, executed=True, source="builtin")
      return 0, "", "", full

    for entry in self.pack_commands:
      try:
        hit = (re.search(entry["match"], text)
               or re.search(entry["match"], shlex.join(tokens)))
      except (re.error, KeyError) as e:
        raise SandboxError(f"bad pack_commands entry: {e}") from None
      if hit:
        return self._run_pack_tool(entry, tokens, text, stdin, cwd,
                                   env) + (cwd,)

    if prog not in REAL_COMMANDS:
      self._log("run_command", command=text, error=NOT_AVAILABLE,
                source="refused")
      return 127, "", f"{prog}: {NOT_AVAILABLE}\n", cwd
    if prog == "sqlite3":
      return self._run_sqlite(tokens, text, stdin, cwd) + (cwd,)
    problem = self._validate_builtin(tokens, cwd)
    if problem:
      msg = f"{NOT_AVAILABLE}: {problem}"
      self._log("run_command", command=text, error=msg, source="refused")
      return 126, "", msg + "\n", cwd
    code, out, err = self._exec(tokens, stdin, cwd, COMMAND_TIMEOUT_S,
                                extra_env=env)
    self._log("run_command", command=text, executed=True, source="builtin",
              error=None if code == 0 else f"exit {code}")
    return code, out, err, cwd

  def _rel_from(self, cwd: str, path: str) -> str:
    if os.path.isabs(path):
      return path  # _norm_rel rejects it.
    joined = os.path.normpath(os.path.join(cwd, path))
    return os.path.relpath(joined, self.repo)

  def _escapes(self, cwd: str, token: str) -> bool:
    """True if a path-like token points outside the sandbox."""
    if token == "/dev/null":
      return False
    if os.path.isabs(token):
      # Absolute paths outside the repo are refused if they exist on the host
      # (patterns like "/users" that merely look like paths are allowed).
      real = os.path.realpath(token)
      inside = real == self.repo or real.startswith(self.repo + os.sep)
      return not inside and (os.path.exists(token) or token in ("/",))
    if ".." in token.replace("\\", "/").split("/"):
      real = os.path.realpath(os.path.join(cwd, token))
      return not (real == self.repo or real.startswith(self.repo + os.sep))
    return False

  def _validate_builtin(self, tokens: List[str], cwd: str) -> Optional[str]:
    prog = tokens[0]
    for t in tokens[1:]:
      vals = [t]
      if t.startswith("-") and "=" in t:
        vals.append(t.split("=", 1)[1])
      for v in vals:
        if self._escapes(cwd, v):
          return f"path outside the sandbox: {v}"
        norm = v.replace("\\", "/").lstrip("./")
        if norm == ".git" or norm.startswith(".git/"):
          if prog != "git":
            return "the .git directory is not accessible"
    if prog == "find":
      bad = [t for t in tokens if t in FIND_BLOCKED]
      if bad:
        return f"find {bad[0]} is not supported"
    if prog == "git":
      args = tokens[1:]
      while args and args[0] in ("--no-pager", "-P"):
        args = args[1:]
      if not args:
        return "git requires a subcommand"
      sub = args[0]
      if sub not in GIT_SUBCOMMANDS:
        return f"git {sub} is not supported"
      for t in args[1:]:
        if t in GIT_BLOCKED_FLAGS or any(
            t.startswith(f + "=") for f in GIT_BLOCKED_FLAGS if f.startswith("--")):
          return f"git option {t} is not supported"
      if sub == "config" and not any(t in GIT_CONFIG_READ_FLAGS
                                     for t in args[1:]):
        return "git config is read-only in this sandbox (use --get/--list)"
    return None

  def _exec(self, argv: List[str], stdin: Optional[str], cwd: str,
            timeout: int, extra_path: Optional[List[str]] = None,
            extra_env: Optional[Dict[str, str]] = None
            ) -> Tuple[int, str, str]:
    try:
      p = subprocess.run(
          argv, cwd=cwd, env=self._env(extra_path, extra_env),
          input=(stdin or ""),
          capture_output=True, text=True, errors="replace", timeout=timeout,
      )
      return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
      return 124, "", f"timed out after {timeout}s\n"
    except (FileNotFoundError, PermissionError) as e:
      return 127, "", f"{argv[0]}: {e}\n"

  def _run_pack_tool(self, entry: Dict[str, Any], tokens: List[str],
                     text: str, stdin: Optional[str], cwd: str,
                     env: Optional[Dict[str, str]] = None
                     ) -> Tuple[int, str, str]:
    resolve: Optional[Callable[..., Any]] = entry.get("resolve")
    argv = resolve(list(tokens), self.repo) if callable(resolve) else None
    if not argv:
      reason = entry.get("unavailable_reason") or "pack tool unavailable"
      msg = f"{NOT_AVAILABLE}: {reason}"
      self._log("run_command", command=text, error=msg, source="refused")
      return 127, "", msg + "\n"
    for t in list(tokens) + list(argv):
      if not isinstance(t, str) or t.startswith("-"):
        continue
      try:
        rel = self._rel(self._rel_from(cwd, t))
      except ToolError:
        continue
      if rel and rel in self.pack_files:
        full = os.path.join(self.repo, rel)
        try:
          with open(full, "r", encoding="utf-8") as f:
            same = f.read() == self.pack_files[rel]
        except OSError:
          same = False
        if not same:
          msg = (f"{NOT_AVAILABLE}: pack tool file {rel} was modified or "
                 "removed; refusing to execute it")
          self._log("run_command", command=text, error=msg, source="refused")
          return 126, "", msg + "\n"
    code, out, err = self._exec(list(argv), stdin, cwd, PACK_TOOL_TIMEOUT_S,
                                extra_path=entry.get("path"),
                                extra_env={**(env or {}),
                                           **(entry.get("env") or {})})
    self._log("run_command", command=text, executed=True, source="pack_tool",
              error=None if code == 0 else f"exit {code}")
    return code, out, err

  # --------------------------------------------------------------- sqlite

  @staticmethod
  def _tables(conn: sqlite3.Connection) -> List[str]:
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]

  def _rowcounts(self, full: str) -> Dict[str, int]:
    conn = sqlite3.connect(full)
    try:
      return {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
              for t in self._tables(conn)}
    finally:
      conn.close()

  def _table_rows(self, conn: sqlite3.Connection
                  ) -> Dict[str, collections.Counter]:
    out = {}
    for t in self._tables(conn):
      out[t] = collections.Counter(
          tuple(r) for r in conn.execute(f'SELECT * FROM "{t}"'))
    return out

  def _run_sqlite(self, tokens: List[str], text: str, stdin: Optional[str],
                  cwd: str) -> Tuple[int, str, str]:
    args = tokens[1:]
    flags = set()
    while args and args[0].startswith("-"):
      if args[0] not in SQLITE_FLAGS:
        msg = f"{NOT_AVAILABLE}: sqlite3 option {args[0]} is not supported"
        self._log("run_command", command=text, error=msg, source="refused")
        return 1, "", msg + "\n"
      flags.add(args.pop(0))
    if not args:
      msg = "sqlite3: a database path is required"
      self._log("run_command", command=text, error=msg, source="refused")
      return 1, "", msg + "\n"
    try:
      db = self._rel(self._rel_from(cwd, args[0]))
    except ToolError as e:
      db = None
      err = str(e)
    if db not in self.db_paths:
      avail = ", ".join(sorted(self.db_paths)) or "none"
      msg = (f"{NOT_AVAILABLE}: sqlite3 only opens the repository's databases "
             f"({avail})")
      if db is None:
        msg += f"; {err}"
      self._log("run_command", command=text, error=msg, source="refused")
      return 1, "", msg + "\n"
    sql = " ".join(args[1:]) if len(args) > 1 else (stdin or "")
    if not sql.strip():
      msg = "sqlite3: no SQL given (pass it as an argument)"
      self._log("run_command", command=text, error=msg, source="refused")
      return 1, "", msg + "\n"
    if re.search(r"\bvacuum\b[\s\S]*\binto\b|\battach\b|load_extension",
                 sql, re.I):
      msg = f"{NOT_AVAILABLE}: ATTACH, VACUUM INTO, and extensions are blocked"
      self._log("run_command", command=text, error=msg, source="refused")
      return 1, "", msg + "\n"

    full = os.path.join(self.repo, db)
    conn = sqlite3.connect(full, isolation_level=None)
    conn.set_authorizer(
        lambda action, *_: sqlite3.SQLITE_DENY
        if action in _SQLITE_DENY_ACTIONS else sqlite3.SQLITE_OK)
    if "-readonly" in flags:
      conn.execute("PRAGMA query_only = ON")
    try:
      before = self._table_rows(conn)
      code, out, err = _exec_sql(conn, sql, flags)
      after = self._table_rows(conn)
    finally:
      conn.close()
    rows_changed: Dict[str, int] = {}
    for t in sorted(set(before) | set(after)):
      b = before.get(t, collections.Counter())
      a = after.get(t, collections.Counter())
      n = max(sum((b - a).values()), sum((a - b).values()))
      if n:
        rows_changed[t] = n
    self._log("run_command", command=text, executed=True, source="builtin",
              rows_changed=rows_changed,
              error=None if code == 0 else err.strip()[:300])
    return code, out, err

  # ------------------------------------------------------------- finalize

  def finalize(self) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Dict[str, int]]]]:
    """Returns (final_diff, sqlite_rowcounts) against the baseline commit."""
    env = self._env()
    env["GIT_INDEX_FILE"] = os.path.join(self.tmp, "final_index")
    if os.path.exists(env["GIT_INDEX_FILE"]):
      os.remove(env["GIT_INDEX_FILE"])

    def git(*args: str) -> str:
      p = subprocess.run(["git", *args], cwd=self.repo, env=env,
                         capture_output=True, text=True, errors="replace",
                         timeout=60)
      if p.returncode != 0:
        raise SandboxError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
      return p.stdout

    git("add", "-A")
    base = self.baseline_commit
    status_map = {"A": "added", "M": "modified", "D": "deleted",
                  "T": "modified"}
    files: Dict[str, Dict[str, Any]] = {}
    ns = git("diff", "--cached", "--no-renames", "--name-status", "-z", base)
    parts = [p for p in ns.split("\0") if p != ""]
    for i in range(0, len(parts) - 1, 2):
      files[parts[i + 1]] = {"status": status_map.get(parts[i][0], "modified"),
                             "added": 0, "removed": 0}
    num = git("diff", "--cached", "--no-renames", "--numstat", "-z", base)
    for rec in num.split("\0"):
      if not rec:
        continue
      fields = rec.split("\t", 2)
      if len(fields) != 3:
        continue
      added, removed, path = fields
      entry = files.setdefault(path, {"status": "modified", "added": 0,
                                      "removed": 0})
      if added == "-":
        entry["binary"] = True
      else:
        entry["added"], entry["removed"] = int(added), int(removed)
    patch = git("diff", "--cached", "--no-renames", "--no-color", base)
    contents: Dict[str, Optional[str]] = {}
    for path, entry in files.items():
      if entry["status"] == "deleted":
        contents[path] = None
        continue
      if entry.get("binary"):
        continue
      try:
        with open(os.path.join(self.repo, path), "rb") as f:
          data = f.read()
      except OSError:
        continue
      if len(data) > MAX_DIFF_CONTENT_BYTES:
        entry["truncated"] = True
        data = data[:MAX_DIFF_CONTENT_BYTES]
      contents[path] = data.decode("utf-8", "replace")
    final_diff = {"files": files, "patch": patch, "contents": contents,
                  "baseline_commit": base}
    rowcounts = {
        db: {"baseline": dict(self.baseline_rowcounts[db]),
             "final": self._rowcounts(os.path.join(self.repo, db))}
        for db in self.db_paths
    }
    return final_diff, rowcounts

  def cleanup(self) -> None:
    shutil.rmtree(self.root_dir, ignore_errors=True)


def _format_rows(cols: List[str], rows: List[Tuple[Any, ...]],
                 flags: set, header: bool) -> str:
  def s(v: Any) -> str:
    if v is None:
      return ""
    if isinstance(v, bytes):
      return v.hex()
    return str(v)

  if "-json" in flags:
    if not rows:
      return ""
    return json.dumps([dict(zip(cols, r)) for r in rows], default=s) + "\n"
  if "-csv" in flags:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    if header:
      w.writerow(cols)
    for r in rows:
      w.writerow([s(v) for v in r])
    return buf.getvalue()
  if "-line" in flags:
    width = max((len(c) for c in cols), default=0)
    return "\n".join("\n".join(f"{c.rjust(width)} = {s(v)}"
                               for c, v in zip(cols, r)) + "\n"
                     for r in rows)
  if flags & {"-column", "-box", "-markdown", "-table"}:
    table = [cols] + [[s(v) for v in r] for r in rows]
    widths = [max(len(row[i]) for row in table) for i in range(len(cols))]
    lines = []
    for n, row in enumerate(table):
      if n == 0 and not header and "-column" in flags:
        continue
      lines.append("  ".join(v.ljust(w) for v, w in zip(row, widths)).rstrip())
      if n == 0:
        lines.append("  ".join("-" * w for w in widths))
    return "\n".join(lines) + ("\n" if lines else "")
  out = []
  if header:
    out.append("|".join(cols))
  out.extend("|".join(s(v) for v in r) for r in rows)
  return "\n".join(out) + ("\n" if out else "")


def _split_sql(sql: str) -> List[str]:
  stmts: List[str] = []
  buf = ""
  for line in sql.splitlines() or [sql]:
    if not buf.strip() and line.strip().startswith("."):
      stmts.append(line.strip())
      continue
    for piece in re.split(r"(;)", line):
      buf += piece
      if piece == ";" and sqlite3.complete_statement(buf):
        stmts.append(buf.strip())
        buf = ""
    buf += "\n"
  if buf.strip():
    stmts.append(buf.strip())
  return stmts


def _exec_sql(conn: sqlite3.Connection, sql: str,
              flags: set) -> Tuple[int, str, str]:
  """Executes SQL like the sqlite3 CLI (subset). Returns (code, out, err)."""
  header = "-header" in flags or bool(
      flags & {"-column", "-box", "-markdown", "-table"}) and (
          "-noheader" not in flags)
  out: List[str] = []
  for stmt in _split_sql(sql):
    if stmt.startswith("."):
      parts = stmt.split()
      cmd = parts[0]
      if cmd == ".tables":
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT "
            "LIKE 'sqlite_%' ORDER BY name")]
        out.append("  ".join(names) + ("\n" if names else ""))
      elif cmd == ".schema":
        q = "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"
        params: Tuple[Any, ...] = ()
        if len(parts) > 1:
          q += " AND tbl_name = ?"
          params = (parts[1],)
        out.extend(r[0] + ";\n" for r in conn.execute(q, params))
      elif cmd in (".headers", ".header"):
        header = len(parts) > 1 and parts[1].lower() in ("on", "1", "yes")
      elif cmd == ".mode" and len(parts) > 1 and parts[1] in (
          "csv", "json", "line", "list", "column", "box", "markdown", "table"):
        flags = (flags - {"-csv", "-json", "-line", "-list", "-column",
                          "-box", "-markdown", "-table"}) | {f"-{parts[1]}"}
      else:
        return 1, "".join(out), f"Error: dot-command {cmd} is not supported\n"
      continue
    try:
      cur = conn.execute(stmt)
      rows = cur.fetchall()
      if cur.description:
        cols = [d[0] for d in cur.description]
        out.append(_format_rows(cols, rows, flags, header))
    except sqlite3.Error as e:
      return 1, "".join(out), f"Error: {e}\n"
    except ValueError as e:  # e.g. multiple statements in one execute.
      return 1, "".join(out), f"Error: {e}\n"
  return 0, "".join(out), ""
