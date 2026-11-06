#!/usr/bin/env python3
"""Fetches pinned framework packs and writes the lockfiles.

For every `source.type == "git"` entry in `frameworks/registry.json`, downloads
the exact commit (`source.ref`, a 40-character SHA) from GitHub's codeload
endpoint into `.pack_cache/<key>/<sha>/`. Third-party content is never written
into the repository: `.pack_cache/` is gitignored.

Pack tooling (for example the OpenSpec CLI) is installed into
`.pack_cache/<key>/_tools/` at the pinned version when node/npm exist; when they
do not, the lockfile marks the tool unavailable so the report can disclose it.

Then hashes every loaded file (the exact set `bench.frameworks` loads) and
writes `frameworks/packs.lock.json` (public) and, for
`frameworks/registry_internal.json` local sources, `packs_internal.lock.json`.

Usage:
  python3 fetch_packs.py                 # fetch missing packs, write lockfiles
  python3 fetch_packs.py --verify        # check cache + lockfiles, no writes
  python3 fetch_packs.py --only openspec # restrict to some keys
  python3 fetch_packs.py --resolve REPO REF   # print the commit SHA for a tag
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bench import frameworks as fw  # pylint: disable=g-import-not-at-top

_USER_AGENT = "cdd-sdd-benchmark-fetch-packs"
_TIMEOUT_S = 120


def _http_get(url: str) -> bytes:
  req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
  token = os.environ.get("GITHUB_TOKEN")
  if token and url.startswith("https://api.github.com/"):
    req.add_header("Authorization", f"Bearer {token}")
  with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
    return resp.read()


def _owner_repo(repo_url: str) -> str:
  prefix = "https://github.com/"
  if not repo_url.startswith(prefix):
    raise fw.PackError(f"only GitHub repos are supported: {repo_url}")
  return repo_url[len(prefix):].rstrip("/").removesuffix(".git")


def resolve_ref(repo_url: str, ref: str) -> str:
  """Resolves a tag/branch to a commit SHA via the GitHub API."""
  data = json.loads(_http_get(
      f"https://api.github.com/repos/{_owner_repo(repo_url)}/commits/{ref}"))
  return data["sha"]


def _safe_extract(data: bytes, dest: str) -> None:
  """Extracts a codeload tarball, stripping the top dir, rejecting escapes."""
  with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
    for member in tar.getmembers():
      parts = member.name.split("/", 1)
      if len(parts) < 2 or not parts[1]:
        continue
      rel = parts[1]
      if rel.startswith("/") or ".." in rel.split("/"):
        raise fw.PackError(f"unsafe path in archive: {member.name}")
      target = os.path.join(dest, rel)
      if member.isdir():
        os.makedirs(target, exist_ok=True)
      elif member.isfile():
        os.makedirs(os.path.dirname(target), exist_ok=True)
        src = tar.extractfile(member)
        if src is None:
          continue
        with open(target, "wb") as f:
          shutil.copyfileobj(src, f)
      # Symlinks, devices, and hardlinks are skipped on purpose.


def fetch_git(entry: Dict[str, Any], cache_dir: str) -> str:
  """Downloads the pinned commit if not cached; returns the pack root."""
  src = entry["source"]
  ref = src["ref"]
  if len(ref) != 40 or any(c not in "0123456789abcdef" for c in ref):
    raise fw.PackError(f"{entry['key']}: source.ref must be a 40-char commit SHA")
  root = fw.source_root(entry, cache_dir)
  marker = os.path.join(root, ".fetched")
  if os.path.isfile(marker):
    return root
  url = f"https://codeload.github.com/{_owner_repo(src['repo'])}/tar.gz/{ref}"
  print(f"[fetch] {entry['key']}: {url}")
  data = _http_get(url)
  os.makedirs(os.path.dirname(root), exist_ok=True)
  tmp = tempfile.mkdtemp(prefix=".tmp-", dir=os.path.dirname(root))
  try:
    _safe_extract(data, tmp)
    if os.path.isdir(root):
      shutil.rmtree(root)
    os.replace(tmp, root)
  finally:
    if os.path.isdir(tmp):
      shutil.rmtree(tmp, ignore_errors=True)
  with open(marker, "w", encoding="utf-8") as f:
    f.write(json.dumps({"repo": src["repo"], "ref": ref,
                        "archive_sha256": fw.sha256_bytes(data)}) + "\n")
  os.utime(marker, None)
  return root


def verify_git_deep(
    entry: Dict[str, Any], cache_dir: str, lock_files: Dict[str, str]
) -> List[str]:
  """Re-downloads a git pack archive and compares lockfile/cached file hashes."""
  probs: List[str] = list(fw.check_git_pack_mtime(entry, cache_dir))
  src = entry["source"]
  ref = src["ref"]
  url = f"https://codeload.github.com/{_owner_repo(src['repo'])}/tar.gz/{ref}"
  print(f"[deep-verify] {entry['key']}: {url}")
  data = _http_get(url)
  root = fw.source_root(entry, cache_dir)
  tmp = tempfile.mkdtemp(prefix=".deep-verify-")
  try:
    _safe_extract(data, tmp)
    for rel, locked_sha in sorted(lock_files.items()):
      if rel.startswith("generated:"):
        continue
      fresh_path = os.path.join(tmp, rel)
      cached_path = os.path.join(root, rel)
      msg = f"cache modified after fetch: {entry['key']}/{rel}"
      if not os.path.isfile(fresh_path) or not os.path.isfile(cached_path):
        if msg not in probs:
          probs.append(msg)
        continue
      fresh_sha = fw.sha256_file(fresh_path)
      cached_sha = fw.sha256_file(cached_path)
      if cached_sha != fresh_sha or locked_sha != fresh_sha:
        if msg not in probs:
          probs.append(msg)
  finally:
    shutil.rmtree(tmp, ignore_errors=True)
  return probs


def install_tools(entry: Dict[str, Any], cache_dir: str) -> Dict[str, Any]:
  """Installs pinned pack CLIs; returns lock metadata per tool."""
  tools: Dict[str, Any] = {}
  for spec in entry.get("pack_commands", []):
    kind = spec["kind"]
    if kind == "node_cli":
      pkg, version = spec["npm_package"], spec["npm_version"]
      tdir = fw.tools_dir(entry, cache_dir)
      binary = os.path.join(tdir, "node_modules", ".bin", spec["bin"])
      info: Dict[str, Any] = {"kind": kind, "package": pkg, "version": version}
      npm, node = shutil.which("npm"), shutil.which("node")
      if not os.path.isfile(binary) and npm and node:
        os.makedirs(tdir, exist_ok=True)
        print(f"[tools] {entry['key']}: npm install {pkg}@{version}")
        proc = subprocess.run(
            [npm, "install", "--prefix", tdir, f"{pkg}@{version}", "--no-audit",
             "--no-fund", "--ignore-scripts", "--loglevel=error"],
            capture_output=True, text=True, timeout=600, check=False)
        if proc.returncode != 0:
          info["install_error"] = proc.stderr[-2000:]
      if os.path.isfile(binary) and node:
        proc = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=60,
            check=False, env={**os.environ, **spec.get("env", {})})
        reported = proc.stdout.strip().splitlines()[-1:] or [""]
        info["available"] = reported[0] == version
        info["reported_version"] = reported[0]
        info["node_version"] = subprocess.run(
            [node, "--version"], capture_output=True, text=True,
            check=False).stdout.strip()
        lock_file = os.path.join(tdir, "package-lock.json")
        if os.path.isfile(lock_file):
          info["package_lock_sha256"] = fw.sha256_file(lock_file)
      else:
        info["available"] = False
        info["unavailable_reason"] = (
            "node/npm not found on the fetch host" if not (npm and node)
            else "install failed")
        print(f"[tools] WARNING {entry['key']}: {spec['bin']} CLI UNAVAILABLE "
              f"({info['unavailable_reason']}); the report must disclose this.",
              file=sys.stderr)
      tools[spec["id"]] = info
    elif kind in ("bash_script", "python_script"):
      interp = "bash" if kind == "bash_script" else "python3"
      tools[spec["id"]] = {"kind": kind, "interpreter": interp,
                           "available": shutil.which(interp) is not None,
                           "path_globs": spec.get("path_globs", [])}
  return tools


def lock_entry(pack: fw.FrameworkPack, tools: Dict[str, Any]) -> Dict[str, Any]:
  src = dict(pack.entry["source"])
  stats = pack.size_stats()
  out: Dict[str, Any] = {
      "source": src,
      "ref": src.get("ref"),
      "visibility": pack.visibility,
      "files": dict(sorted(pack.file_hashes().items())),
      "tools": tools,
      "stats": stats,
  }
  if src.get("type") == "local_path":
    git_head, dirty_files = fw.git_working_tree_state(pack.root)
    out["git_head"] = git_head
    out["dirty_files"] = dirty_files
  return out


def process_registry(path: str, cache_dir: str, only: Optional[List[str]],
                     verify_only: bool, deep: bool = False) -> int:
  """Fetches/verifies one registry; returns the number of problems."""
  if not os.path.isfile(path):
    return 0
  lock_path = fw.lock_path_for(path)
  old = fw.read_lock(lock_path)
  new: Dict[str, Any] = {}
  excluded: Dict[str, str] = {}
  problems = 0
  for entry in fw.read_registry(path):
    key = entry["key"]
    if entry.get("excluded"):
      excluded[key] = entry.get("exclude_reason", "")
      continue
    if only and key not in only:
      if key in old:
        new[key] = old[key]
      continue
    try:
      if entry["source"]["type"] == "git" and not verify_only:
        fetch_git(entry, cache_dir)
      root = fw.source_root(entry, cache_dir)
      if not os.path.isdir(root):
        raise fw.PackError(f"{key}: not fetched ({root})")
      pack = fw.FrameworkPack(entry, root, None, cache_dir, verify=False)
      tools = (old.get(key, {}).get("tools", {}) if verify_only
               else install_tools(entry, cache_dir))
      new[key] = lock_entry(pack, tools)
      if entry["source"]["type"] == "git" and (verify_only or deep):
        mtime_probs = fw.check_git_pack_mtime(entry, cache_dir)
        deep_probs = (
            verify_git_deep(
                entry,
                cache_dir,
                old.get(key, {}).get("files") or new[key]["files"],
            )
            if deep
            else []
        )
        all_git_probs = list(dict.fromkeys(mtime_probs + deep_probs))
        if all_git_probs:
          for gp in all_git_probs:
            print(gp)
          raise fw.PackIntegrityError(all_git_probs[0])
      if verify_only:
        if key not in old:
          raise fw.PackIntegrityError(f"{key}: missing from {lock_path}")
        if old[key].get("files") != new[key]["files"]:
          raise fw.PackIntegrityError(f"{key}: files differ from {lock_path}")
      print(f"[ok] {key}: {len(new[key]['files'])} files, always-on "
            f"~{new[key]['stats']['always_on_tokens_est']} tok, total "
            f"~{new[key]['stats']['total_pack_tokens_est']} tok")
    except (fw.PackError, OSError, ValueError) as e:
      problems += 1
      print(f"[error] {e}", file=sys.stderr)
      if key in old:
        new[key] = old[key]
  if not verify_only:
    out = {"comment": "Generated by fetch_packs.py. Do not edit by hand.",
           "registry": os.path.basename(path), "frameworks": new,
           "excluded": excluded}
    with open(lock_path, "w", encoding="utf-8") as f:
      json.dump(out, f, indent=2, sort_keys=False)
      f.write("\n")
    print(f"[lock] wrote {lock_path}")
  return problems


def main(argv: Optional[List[str]] = None) -> int:
  parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
  parser.add_argument("--registry", action="append",
                      help="registry path(s); default: public + internal")
  parser.add_argument("--cache-dir", default=fw.PACK_CACHE_DIR)
  parser.add_argument("--only", action="append", help="framework key(s)")
  parser.add_argument("--verify", action="store_true",
                      help="verify cache against lockfiles without writing")
  parser.add_argument("--deep", action="store_true",
                      help="re-download git archives and compare against lockfile")
  parser.add_argument("--resolve", nargs=2, metavar=("REPO_URL", "REF"),
                      help="print the commit SHA for a tag or branch and exit")
  args = parser.parse_args(argv)
  if args.resolve:
    print(resolve_ref(*args.resolve))
    return 0
  paths = args.registry or fw.default_registry_paths()
  verify_only = bool(args.verify or args.deep)
  problems = sum(
      process_registry(p, args.cache_dir, args.only, verify_only, deep=args.deep)
      for p in paths
  )
  return 1 if problems else 0


if __name__ == "__main__":
  sys.exit(main())
