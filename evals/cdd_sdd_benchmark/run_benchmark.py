#!/usr/bin/env python3
"""CDD/SDD benchmark v2 command-line driver.

Subcommands:

  run     Execute the framework x scenario x model x seed matrix (resumable).
  judge   Add judge-ensemble verdicts to the rollouts of a run.
  report  Verify the run, compute statistics, and write report.md
          (`--visibility public` also writes a filtered public/ copy).
  verify  Full-matrix enforcement (DESIGN.md); exits 1 on any violation.

Rollouts from different run ids or config hashes are never mixed, and there is
no flag to merge runs. See DESIGN.md.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import datetime
import glob
import hashlib
import json
import os
import platform
import shutil
import sys
import threading
from typing import Any, Dict, Iterable, List, Optional, Tuple

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
  sys.path.insert(0, BASE)

# pylint: disable=g-import-not-at-top,wrong-import-position
from bench import agent_loop
from bench import frameworks as frameworks_lib
from bench import gemini_client
from bench import sandbox as sandbox_lib
from bench import schema
# pylint: enable=g-import-not-at-top,wrong-import-position

TASK_FILES = {
    "core": os.path.join("tasks", "core_v2.jsonl"),
    "heldout": os.path.join("tasks", "heldout_v2.jsonl"),
}
DEFAULT_REGISTRIES = [
    os.path.join("frameworks", "registry.json"),
    os.path.join("frameworks", "registry_internal.json"),
]
LOCKFILE = os.path.join("frameworks", "packs.lock.json")
RESULTS_DIR = os.path.join(BASE, "results")
DEFAULT_MODELS = "gemini-3.5-flash"
HARNESS_ERROR_MAX_RATE = 0.05

CellKey = Tuple[str, str, str, int]  # (framework, scenario_id, model, seed)


def _rel(path: str) -> str:
  """Path relative to BASE (manifests never carry absolute checkout paths)."""
  ap = os.path.abspath(path)
  if ap.startswith(BASE + os.sep):
    return os.path.relpath(ap, BASE)
  return os.path.basename(ap)


def _abs(path: str) -> str:
  return path if os.path.isabs(path) else os.path.join(BASE, path)


def _now() -> str:
  return datetime.datetime.now(datetime.timezone.utc).strftime(
      "%Y-%m-%dT%H:%M:%SZ")


def _key(r: schema.RolloutRecord) -> CellKey:
  return (r.framework, r.scenario_id, r.model, int(r.seed))


# ------------------------------------------------------------------ loading


def load_packs(registries: List[str]) -> List[Any]:
  from bench import frameworks  # pylint: disable=g-import-not-at-top
  return frameworks.load_registry([_abs(p) for p in registries])


def load_scenario_sets(sets: List[str]
                       ) -> Tuple[Dict[str, schema.Scenario], Dict[str, str]]:
  """Loads and validates scenarios. Returns ({id: scenario}, {set: relpath})."""
  scenarios: Dict[str, schema.Scenario] = {}
  files: Dict[str, str] = {}
  errors: List[str] = []
  for s in sets:
    if s not in TASK_FILES:
      raise SystemExit(f"unknown set {s!r}; expected one of {list(TASK_FILES)}")
    path = _abs(TASK_FILES[s])
    if not os.path.exists(path):
      raise SystemExit(f"scenario file missing for set {s}: {TASK_FILES[s]}")
    files[s] = TASK_FILES[s]
    with open(path, "r", encoding="utf-8") as f:
      for n, line in enumerate(f, 1):
        line = line.strip()
        if not line:
          continue
        d = json.loads(line)
        errs = schema.validate_scenario(d)
        if d.get("set") != s:
          errs.append(f"{d.get('id')}: set {d.get('set')!r} in {TASK_FILES[s]}")
        if errs:
          errors.extend(f"{TASK_FILES[s]}:{n}: {e}" for e in errs)
          continue
        sc = schema.Scenario.from_dict(d)
        if sc.id in scenarios:
          errors.append(f"duplicate scenario id {sc.id}")
        scenarios[sc.id] = sc
  if errors:
    raise SystemExit("scenario validation failed:\n  " + "\n  ".join(errors))
  return scenarios, files


def load_rollouts(path: str) -> List[schema.RolloutRecord]:
  out: List[schema.RolloutRecord] = []
  if not os.path.exists(path):
    return out
  with open(path, "r", encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if line:
        out.append(schema.RolloutRecord.from_dict(json.loads(line)))
  return out


def write_rollouts_atomic(path: str,
                          rollouts: Iterable[schema.RolloutRecord]) -> None:
  tmp = path + ".tmp"
  with open(tmp, "w", encoding="utf-8") as f:
    for r in rollouts:
      f.write(r.to_json() + "\n")
  os.replace(tmp, path)


def write_json_atomic(path: str, data: Any) -> None:
  tmp = path + ".tmp"
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False,
              default=str)
    f.write("\n")
  os.replace(tmp, path)


# -------------------------------------------------------------- config hash


def compute_config_hash(
    scenario_files: Iterable[str],
    packs: Iterable[Any],
    pack_hashes_override: Optional[Dict[str, Any]] = None,
) -> str:
  """sha256 over lockfile + scenario files + bench/*.py + base prompt.

  Also covers this driver and every loaded pack's file hashes (so local-source
  packs that change between runs change the hash).
  """
  h = hashlib.sha256()

  def feed(label: str, data: bytes) -> None:
    h.update(label.encode() + b"\0" + str(len(data)).encode() + b"\0")
    h.update(data)

  def read(path: str) -> bytes:
    with open(path, "rb") as f:
      return f.read()

  lock = _abs(LOCKFILE)
  feed("lockfile", read(lock) if os.path.exists(lock) else b"<missing>")
  for path in sorted(glob.glob(os.path.join(BASE, "frameworks",
                                            "*.lock.json"))):
    if os.path.abspath(path) != lock:
      feed(f"lockfile:{os.path.basename(path)}", read(path))
  for rel in sorted(set(scenario_files)):
    feed(f"scenarios:{rel}", read(_abs(rel)))
  for path in sorted(glob.glob(os.path.join(BASE, "bench", "*.py"))):
    feed(f"bench:{os.path.basename(path)}", read(path))
  feed("driver", read(os.path.abspath(__file__)))
  feed("base_prompt", agent_loop.BASE_PROMPT.encode("utf-8"))
  pack_hashes = {}
  for p in packs:
    fh = getattr(p, "file_hashes", None)
    pack_hashes[p.key] = fh() if callable(fh) else None
  if pack_hashes_override:
    for k, v in pack_hashes_override.items():
      if k in pack_hashes and v is not None:
        pack_hashes[k] = v
  feed("packs", json.dumps(pack_hashes, sort_keys=True).encode())
  return h.hexdigest()


# ----------------------------------------------------------------- manifest


def _pack_entry(p: Any, lock: Dict[str, Any]) -> Dict[str, Any]:
  fh_fn = getattr(p, "file_hashes", None)
  raw_fh = fh_fn() if callable(fh_fn) else None
  pack_fh = dict(raw_fh) if isinstance(raw_fh, dict) else None
  entry: Dict[str, Any] = {
      "key": p.key,
      "display_name": p.display_name,
      "paradigm": getattr(p, "paradigm", None),
      "visibility": p.visibility,
      "pack_sha256": schema.pack_sha256_from_hashes(pack_fh),
  }
  src = getattr(p, "source", None) or (getattr(p, "entry", None) or {}).get(
      "source")
  if isinstance(src, dict):
    entry["source"] = {
        k: v
        for k, v in src.items()
        if k in ("type", "repo", "ref", "path", "env")
    }
    if p.visibility != "public":
      entry["source"].pop("path", None)
  lk = lock.get(p.key)
  if isinstance(lk, dict):
    entry["lock"] = {k: v for k, v in lk.items()
                     if not isinstance(v, (dict, list))}
    files = lk.get("files")
    if isinstance(files, (dict, list)):
      entry["lock"]["n_files"] = len(files)
  if isinstance(src, dict) and src.get("type") == "local_path":
    lk_dict = entry.setdefault("lock", {})
    if "git_head" not in lk_dict or "dirty_files" not in lk_dict:
      root_dir = getattr(p, "root", None)
      if isinstance(root_dir, str) and os.path.isdir(root_dir):
        gh, df = frameworks_lib.git_working_tree_state(root_dir)
        lk_dict.setdefault("git_head", gh)
        lk_dict.setdefault("dirty_files", df)
    entry["git_head"] = lk_dict.get("git_head")
    entry["dirty_files"] = lk_dict.get("dirty_files")
  return entry


def build_manifest(run_id: str, config_hash: str, args: argparse.Namespace,
                   all_packs: List[Any], packs: List[Any],
                   scenarios: Dict[str, schema.Scenario],
                   scenario_files: Dict[str, str], models: List[str],
                   seeds: List[int]) -> Dict[str, Any]:
  lock: Dict[str, Any] = {}
  for path in sorted(glob.glob(os.path.join(BASE, "frameworks",
                                            "*.lock.json"))):
    with open(path, "r", encoding="utf-8") as f:
      data = json.load(f)
    if isinstance(data, dict):
      lock.update(data.get("frameworks", data) or {})
  ids: Dict[str, List[str]] = {s: [] for s in scenario_files}
  for sc in scenarios.values():
    ids[sc.set].append(sc.id)
  pack_digests: Dict[str, str] = {}
  for p in packs:
    fh_fn = getattr(p, "file_hashes", None)
    raw_fh = fh_fn() if callable(fh_fn) else None
    if isinstance(raw_fh, dict):
      pack_digests[p.key] = hashlib.sha256(
          json.dumps(raw_fh, sort_keys=True).encode("utf-8")
      ).hexdigest()
  return {
      "run_id": run_id,
      "config_hash": config_hash,
      "created_at": _now(),
      "updated_at": _now(),
      "status": "running",
      "publish": bool(args.publish),
      "registries": [_rel(_abs(r)) for r in args.registry],
      "registry_frameworks": sorted(p.key for p in all_packs),
      "frameworks": [_pack_entry(p, lock) for p in packs],
      "pack_digests": pack_digests,
      "lockfile_present": os.path.exists(_abs(LOCKFILE)),
      "sets": sorted(scenario_files),
      "scenario_files": scenario_files,
      "scenario_ids": {s: sorted(v) for s, v in ids.items()},
      "models": models,
      "seeds": seeds,
      "generation_config": {
          "temperature": agent_loop.TEMPERATURE,
          "maxOutputTokens": agent_loop.MAX_OUTPUT_TOKENS,
          "seed": "rollout seed",
          "thinking": "model default",
      },
      "max_steps_per_turn": agent_loop.MAX_STEPS_PER_TURN,
      "base_prompt_sha256": hashlib.sha256(
          agent_loop.BASE_PROMPT.encode()).hexdigest(),
      "harness": {"python": platform.python_version()},
      "cells": {},
  }


def expected_cells(manifest: Dict[str, Any]) -> List[CellKey]:
  ids = [i for s in manifest["sets"] for i in manifest["scenario_ids"][s]]
  return [(fw["key"], sid, m, int(seed))
          for fw in manifest["frameworks"] for sid in ids
          for m in manifest["models"] for seed in manifest["seeds"]]


def cell_counts(manifest: Dict[str, Any],
                rollouts: List[schema.RolloutRecord]) -> Dict[str, Any]:
  by_key = {_key(r): r for r in rollouts}
  out: Dict[str, Dict[str, Dict[str, int]]] = {}
  for fw, sid, m, seed in expected_cells(manifest):
    c = out.setdefault(fw, {}).setdefault(
        m, {"expected": 0, "ok": 0, "harness_error": 0, "missing": 0})
    c["expected"] += 1
    r = by_key.get((fw, sid, m, seed))
    if r is None:
      c["missing"] += 1
    elif r.status == "ok":
      c["ok"] += 1
    else:
      c["harness_error"] += 1
  return out


def _matrix(manifest: Dict[str, Any]) -> Dict[str, Any]:
  return {
      "frameworks": sorted(f["key"] for f in manifest["frameworks"]),
      "scenario_ids": manifest["scenario_ids"],
      "models": manifest["models"],
      "seeds": manifest["seeds"],
      "publish": manifest["publish"],
  }


# ---------------------------------------------------------------------- run


def _apply_smoke_config(
    args: argparse.Namespace,
    all_packs: List[frameworks_lib.FrameworkPack],
) -> Tuple[
    List[frameworks_lib.FrameworkPack],
    Dict[str, schema.Scenario],
    Dict[str, str],
    List[str],
    List[int],
]:
  """Selects the stratified smoke subset defined in `smoke_config.json`."""
  cfg_path = _abs(getattr(args, "smoke_config", "") or "smoke_config.json")
  with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)
  fw_wanted = set(cfg.get("frameworks", []))
  packs = [p for p in all_packs if p.key in fw_wanted] if fw_wanted else list(all_packs)
  scenarios_all, scenario_files = load_scenario_sets(["core"])
  per_pillar = int(cfg.get("scenarios_per_pillar", 3))
  pillars = cfg.get("pillars", list(schema.PILLARS))
  selected: Dict[str, schema.Scenario] = {}
  for pil in pillars:
    cands = sorted(
        (sc for sc in scenarios_all.values() if sc.pillar == pil),
        key=lambda s: s.id,
    )
    for sc in cands[:per_pillar]:
      selected[sc.id] = sc
  models = (
      [m.strip() for m in args.models.split(",") if m.strip()]
      if args.models and args.models != DEFAULT_MODELS
      else list(cfg.get("models", ["gemini-3.5-flash"]))
  )
  seeds = [int(s) for s in cfg.get("seeds", [1])]
  return packs, selected, scenario_files, models, seeds


def cmd_run(args: argparse.Namespace) -> int:
  from bench import checks  # pylint: disable=g-import-not-at-top

  if not args.registry:
    args.registry = [
        _abs(r) for r in DEFAULT_REGISTRIES if os.path.exists(_abs(r))
    ]
  all_packs = load_packs(args.registry)
  keys = [p.key for p in all_packs]
  if len(set(keys)) != len(keys):
    raise SystemExit(f"duplicate framework keys across registries: {keys}")
  prev_manifest: Optional[Dict[str, Any]] = None
  if args.out and os.path.exists(os.path.join(_abs(args.out), "manifest.json")):
    with open(
        os.path.join(_abs(args.out), "manifest.json"), "r", encoding="utf-8"
    ) as f:
      prev_manifest = json.load(f)

  if args.retry_harness_errors and prev_manifest is not None:
    prev_fw_keys = [fw["key"] for fw in prev_manifest.get("frameworks", [])]
    packs = [p for p in all_packs if p.key in prev_fw_keys]
    sets = list(prev_manifest.get("sets", ["core", "heldout"]))
    scenarios_all, scenario_files = load_scenario_sets(sets)
    wanted_sc = {
        sid
        for s in sets
        for sid in (prev_manifest.get("scenario_ids") or {}).get(s, [])
    }
    scenarios = (
        {k: v for k, v in scenarios_all.items() if k in wanted_sc}
        if wanted_sc
        else scenarios_all
    )
    models = list(prev_manifest.get("models", DEFAULT_MODELS.split(",")))
    seeds = [int(s) for s in prev_manifest.get("seeds", [1])]
    args.publish = bool(prev_manifest.get("publish", False))
  elif getattr(args, "smoke", False):
    packs, scenarios, scenario_files, models, seeds = _apply_smoke_config(
        args, all_packs
    )
    sets = ["core"]
  else:
    if args.frameworks and args.frameworks != "all":
      wanted = [k.strip() for k in args.frameworks.split(",") if k.strip()]
      unknown = sorted(set(wanted) - set(keys))
      if unknown:
        raise SystemExit(f"unknown frameworks: {unknown}")
      packs = [p for p in all_packs if p.key in wanted]
    else:
      packs = list(all_packs)
    sets = [s.strip() for s in args.sets.split(",") if s.strip()]
    scenarios, scenario_files = load_scenario_sets(sets)
    if args.scenarios:
      wanted_sc = [s.strip() for s in args.scenarios.split(",") if s.strip()]
      missing = sorted(set(wanted_sc) - set(scenarios))
      if missing:
        raise SystemExit(f"unknown scenarios: {missing}")
      scenarios = {k: v for k, v in scenarios.items() if k in wanted_sc}
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    seeds = list(range(1, args.seeds + 1))

  if args.publish:
    problems = []
    if {p.key for p in packs} != set(keys):
      problems.append("--publish requires every framework in the registries "
                      "(do not pass a --frameworks subset)")
    if args.scenarios:
      problems.append("--publish does not allow a --scenarios subset")
    if set(sets) != set(TASK_FILES):
      problems.append("--publish requires --sets core,heldout")
    if not os.path.exists(_abs(LOCKFILE)):
      problems.append(f"--publish requires {LOCKFILE}")
    if problems:
      raise SystemExit("refusing to publish:\n  " + "\n  ".join(problems))

  for p in packs:
    entry_d = getattr(p, "entry", None)
    if (
        isinstance(entry_d, dict)
        and (entry_d.get("source") or {}).get("type") == "git"
    ):
      cdir = getattr(p, "_cache_dir", frameworks_lib.PACK_CACHE_DIR)
      mtime_probs = frameworks_lib.check_git_pack_mtime(entry_d, cdir)
      if mtime_probs:
        raise SystemExit(
            "aborting run: git pack cache modified after fetch:\n  "
            + "\n  ".join(mtime_probs)
        )

  run_id = (
      args.run_id
      or (prev_manifest.get("run_id") if prev_manifest is not None else None)
      or datetime.datetime.now(datetime.timezone.utc).strftime(
          "v2-%Y%m%d-%H%M%S"
      )
  )
  out = _abs(args.out) if args.out else os.path.join(RESULTS_DIR, run_id)
  os.makedirs(out, exist_ok=True)
  config_hash = compute_config_hash(scenario_files.values(), all_packs)
  manifest = build_manifest(run_id, config_hash, args, all_packs, packs,
                            scenarios, scenario_files, models, seeds)
  manifest_path = os.path.join(out, "manifest.json")
  rollouts_path = os.path.join(out, "rollouts.jsonl")

  if os.path.exists(manifest_path):
    with open(manifest_path, "r", encoding="utf-8") as f:
      prev = json.load(f)
    if prev.get("run_id") != run_id:
      raise SystemExit(f"{out} belongs to run {prev.get('run_id')}; use a new "
                       "--out or the same --run-id")
    if prev.get("config_hash") != config_hash:
      raise SystemExit(
          "config hash changed since this run started (code, prompts, packs, "
          "or scenarios differ). Rollouts are never reused across configs: "
          "start a new --run-id.")
    if _matrix(prev) != _matrix(manifest):
      raise SystemExit("matrix differs from the existing manifest of this run; "
                       "resume with identical arguments or start a new run")
    manifest["created_at"] = prev.get("created_at", manifest["created_at"])
    manifest["harness_error_retries"] = prev.get("harness_error_retries", {})

  existing = load_rollouts(rollouts_path)
  for r in existing:
    if r.run_id != run_id or r.config_hash != config_hash:
      raise SystemExit(f"{rollouts_path} contains rollouts from another run or "
                       "config; refusing to mix")
  latest: Dict[CellKey, schema.RolloutRecord] = {}
  for r in existing:
    latest[_key(r)] = r
  manifest.setdefault("harness_error_retries", {})
  todo = []
  replaced: List[schema.RolloutRecord] = []
  for fw, sid, m, seed in expected_cells(manifest):
    prev_r = latest.get((fw, sid, m, seed))
    if prev_r is None:
      todo.append((fw, sid, m, seed))
    elif args.retry_harness_errors and prev_r.status != "ok":
      todo.append((fw, sid, m, seed))
      replaced.append(prev_r)
  if replaced:
    # Retries are disclosed, never hidden: keep the replaced records and a
    # cumulative per framework x model count for the report.
    with open(os.path.join(out, "rollouts.retried.jsonl"), "a",
              encoding="utf-8") as f:
      for r in replaced:
        f.write(r.to_json() + "\n")
        by_model = manifest["harness_error_retries"].setdefault(r.framework,
                                                                {})
        by_model[r.model] = by_model.get(r.model, 0) + 1
  write_json_atomic(manifest_path, manifest)
  print(f"run {run_id} config {config_hash[:12]}: {len(todo)} rollouts to run "
        f"({len(latest)} already present)", file=sys.stderr)

  gemini_client.set_concurrency(args.concurrency)
  client = gemini_client.GeminiClient() if todo else None
  pack_by_key = {p.key: p for p in packs}
  sandbox_root = sandbox_lib.SANDBOX_BASE
  # Opaque sandbox dirs (the agent sees them); keep the mapping for debugging.
  dirs_path = os.path.join(out, "sandbox_dirs.json")
  dirs = {}
  if os.path.exists(dirs_path):
    with open(dirs_path, "r", encoding="utf-8") as f:
      dirs = json.load(f)
  for fw, sid, m, seed in todo:
    dirs["|".join((fw, sid, m, str(seed)))] = agent_loop.rollout_dir(
        sandbox_root, run_id, fw, m, sid, seed)
  write_json_atomic(dirs_path, dirs)
  lock = threading.Lock()

  def one(cell: CellKey) -> schema.RolloutRecord:
    fw, sid, m, seed = cell
    sc = scenarios[sid]
    p = pack_by_key[fw]
    rec = agent_loop.run_rollout(p, sc, m, seed, run_id,
                                 config_hash, sandbox_root, client=client,
                                 keep_sandbox=args.keep_sandboxes)
    if not rec.pack_digest or rec.pack_file_hashes is None:
      fh_fn = getattr(p, "file_hashes", None)
      raw_fh = fh_fn() if callable(fh_fn) else None
      if isinstance(raw_fh, dict):
        if rec.pack_file_hashes is None:
          rec.pack_file_hashes = dict(raw_fh)
        if not rec.pack_digest:
          rec.pack_digest = hashlib.sha256(
              json.dumps(raw_fh, sort_keys=True).encode("utf-8")
          ).hexdigest()
    if rec.pack_sha256 is None and rec.pack_file_hashes is not None:
      rec.pack_sha256 = schema.pack_sha256_from_hashes(rec.pack_file_hashes)
    if rec.status == "ok":
      try:
        rec.checks = checks.run_checks(rec, sc)
      except Exception as e:  # pylint: disable=broad-except
        rec.status = "harness_error"
        rec.error = f"checks failed: {type(e).__name__}: {e}"
    return rec

  done = 0
  with concurrent.futures.ThreadPoolExecutor(args.concurrency) as ex:
    futs = {ex.submit(one, c): c for c in todo}
    for fut in concurrent.futures.as_completed(futs):
      rec = fut.result()
      with lock:
        with open(rollouts_path, "a", encoding="utf-8") as f:
          f.write(rec.to_json() + "\n")
        latest[_key(rec)] = rec
        done += 1
      print(f"[{done}/{len(todo)}] {agent_loop.rollout_summary(rec)}",
            file=sys.stderr)

  # Compact: exactly one record per cell (retried harness errors replaced).
  ordered = [latest[c] for c in expected_cells(manifest) if c in latest]
  write_rollouts_atomic(rollouts_path, ordered)
  manifest["cells"] = cell_counts(manifest, ordered)
  missing = sum(c["missing"] for fw in manifest["cells"].values()
                for c in fw.values())
  manifest["status"] = "complete" if missing == 0 else "incomplete"
  manifest["updated_at"] = _now()
  write_json_atomic(manifest_path, manifest)
  if getattr(args, "persist_rollouts", True):
    durable_dir = os.path.join(RESULTS_DIR, run_id)
    if os.path.abspath(out) != os.path.abspath(durable_dir):
      os.makedirs(durable_dir, exist_ok=True)
      shutil.copy2(rollouts_path, os.path.join(durable_dir, "rollouts.jsonl"))
      shutil.copy2(manifest_path, os.path.join(durable_dir, "manifest.json"))
  problems = verify(out)
  for p in problems:
    print(f"VERIFY: {p}", file=sys.stderr)
  print(json.dumps(manifest["cells"], indent=1))
  return 1 if (args.publish and problems) else 0


# -------------------------------------------------------------------- verify


def verify(out: str, strict_config: bool = False) -> List[str]:
  """Full-matrix enforcement. Returns a list of violations (empty = valid)."""
  problems: List[str] = []
  manifest_path = os.path.join(out, "manifest.json")
  if not os.path.exists(manifest_path):
    return [f"missing {manifest_path}"]
  with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)
  rollouts = load_rollouts(os.path.join(out, "rollouts.jsonl"))
  run_ids = {r.run_id for r in rollouts}
  hashes = {r.config_hash for r in rollouts}
  if len(run_ids) > 1:
    problems.append(f"rollouts carry {len(run_ids)} run_ids: {sorted(run_ids)}")
  if len(hashes) > 1:
    problems.append(f"rollouts carry {len(hashes)} config hashes")
  if run_ids and run_ids != {manifest["run_id"]}:
    problems.append("rollout run_id differs from manifest")
  if hashes and hashes != {manifest["config_hash"]}:
    problems.append("rollout config_hash differs from manifest")

  expected = set(expected_cells(manifest))
  seen: Dict[CellKey, int] = {}
  for r in rollouts:
    seen[_key(r)] = seen.get(_key(r), 0) + 1
  dups = [k for k, n in seen.items() if n > 1]
  if dups:
    problems.append(f"{len(dups)} cells have duplicate rollouts, e.g. {dups[0]}"
                    " (re-run `run` with the same arguments to compact)")
  extra = sorted(set(seen) - expected)
  if extra:
    problems.append(f"{len(extra)} rollouts are outside the manifest matrix, "
                    f"e.g. {extra[0]}")
  missing = sorted(expected - set(seen))
  if missing:
    problems.append(f"{len(missing)} of {len(expected)} cells are missing, "
                    f"e.g. {missing[0]}")
  vis = {f["key"]: f["visibility"] for f in manifest["frameworks"]}
  manifest_pack_sha = {
      f["key"]: f.get("pack_sha256")
      for f in manifest["frameworks"]
      if isinstance(f, dict) and f.get("pack_sha256")
  }
  manifest_pack_digests = dict(manifest.get("pack_digests") or {})
  by_fw_digests: Dict[str, set] = {}
  by_fw_has_none: Dict[str, bool] = {}
  by_fw_pack_digests: Dict[str, set] = {}
  by_fw_empty_pack_digest: Dict[str, bool] = {}
  rollout_pack_hashes: Dict[str, Dict[str, str]] = {}
  for r in rollouts:
    if r.framework in vis and r.framework_visibility != vis[r.framework]:
      problems.append(f"visibility mismatch for {r.framework}")
      break
  for r in rollouts:
    if r.pack_digest:
      by_fw_pack_digests.setdefault(r.framework, set()).add(r.pack_digest)
      exp_digest = manifest_pack_digests.get(r.framework)
      if exp_digest and r.pack_digest != exp_digest:
        problems.append(
            f"rollout pack_digest for {r.framework} differs from manifest "
            "pack_digests"
        )
    else:
      by_fw_empty_pack_digest[r.framework] = True
    computed_sha = (
        schema.pack_sha256_from_hashes(r.pack_file_hashes)
        if r.pack_file_hashes is not None
        else r.pack_sha256
    )
    if (
        r.pack_sha256 is not None
        and r.pack_file_hashes is not None
        and r.pack_sha256 != computed_sha
    ):
      problems.append(
          f"rollout pack_sha256 disagrees with pack_file_hashes for "
          f"{r.framework} ({r.scenario_id} seed {r.seed})"
      )
    if computed_sha is None:
      by_fw_has_none[r.framework] = True
    else:
      by_fw_digests.setdefault(r.framework, set()).add(computed_sha)
      if isinstance(r.pack_file_hashes, dict):
        rollout_pack_hashes.setdefault(r.framework, r.pack_file_hashes)
      exp_sha = manifest_pack_sha.get(r.framework)
      if exp_sha and computed_sha != exp_sha:
        problems.append(
            f"rollout pack_sha256 for {r.framework} differs from manifest "
            "pack_sha256 (spliced or hash-rewritten run)"
        )
  for fw, p_digests in sorted(by_fw_pack_digests.items()):
    if len(p_digests) > 1 or by_fw_empty_pack_digest.get(fw):
      problems.append(
          f"rollouts of {fw} carry more than one distinct pack_digest "
          "(spliced run)"
      )
  if by_fw_empty_pack_digest:
    print(
        "WARNING: rollouts have empty pack_digest for "
        f"{sorted(by_fw_empty_pack_digest)} (legacy run)",
        file=sys.stderr,
    )
  for fw, digests in sorted(by_fw_digests.items()):
    if len(digests) > 1 or by_fw_has_none.get(fw):
      problems.append(
          f"spliced run: {fw} rollouts carry inconsistent pack_sha256 / "
          "pack_file_hashes across cells"
      )

  counts = cell_counts(manifest, rollouts)
  for fw, by_model in sorted(counts.items()):
    for m, c in sorted(by_model.items()):
      done = c["ok"] + c["harness_error"]
      if done and c["harness_error"] / c["expected"] > HARNESS_ERROR_MAX_RATE:
        problems.append(
            f"harness errors {fw} x {m}: {c['harness_error']}/{c['expected']} "
            f"> {HARNESS_ERROR_MAX_RATE:.0%} (INVALID)")

  if manifest.get("publish"):
    fw_keys = sorted(f["key"] for f in manifest["frameworks"])
    if fw_keys != sorted(manifest.get("registry_frameworks", [])):
      problems.append("publish run does not cover every registry framework")
    if not manifest.get("lockfile_present"):
      problems.append("publish run had no packs.lock.json")
  else:
    print("NOTE: not a --publish run (exploratory; not publishable)",
          file=sys.stderr)

  try:
    packs = load_packs(manifest.get("registries", DEFAULT_REGISTRIES))
    now = compute_config_hash(manifest["scenario_files"].values(), packs)
    if rollout_pack_hashes:
      rollout_cfg = compute_config_hash(
          manifest["scenario_files"].values(),
          packs,
          pack_hashes_override=rollout_pack_hashes,
      )
      pack_by_key = {p.key: p for p in packs}
      for fw, r_fh in sorted(rollout_pack_hashes.items()):
        p = pack_by_key.get(fw)
        fh_fn = getattr(p, "file_hashes", None) if p is not None else None
        cur_fh = fh_fn() if callable(fh_fn) else None
        if strict_config and cur_fh is not None and dict(cur_fh) != dict(r_fh):
          problems.append(
              f"rollout pack_file_hashes for {fw} differ from current pack "
              "(hash-rewritten or spliced run)"
          )
      if (strict_config or now == manifest["config_hash"]) and (
          rollout_cfg != manifest["config_hash"]
      ):
        problems.append(
            "recorded rollout pack_file_hashes do not hash to manifest "
            "config_hash (config_hash was rewritten after pack edits)"
        )
    if now != manifest["config_hash"]:
      msg = ("current code/packs/scenarios hash differs from the run's "
             "config_hash (files changed after the run)")
      if strict_config:
        problems.append(msg)
      else:
        print(f"WARNING: {msg}", file=sys.stderr)
  except (Exception, SystemExit) as e:  # pylint: disable=broad-except
    print(f"WARNING: could not recompute config hash: {e}", file=sys.stderr)
  return problems


def cmd_verify(args: argparse.Namespace) -> int:
  problems = verify(_abs(args.out), strict_config=args.strict_config)
  if problems:
    print("INVALID:\n  " + "\n  ".join(problems))
    return 1
  print("VALID: full matrix, single run_id and config_hash, harness errors "
        f"<= {HARNESS_ERROR_MAX_RATE:.0%} per framework x model")
  return 0


# --------------------------------------------------------------------- judge


def _run_scenarios(manifest: Dict[str, Any]) -> Dict[str, schema.Scenario]:
  scenarios: Dict[str, schema.Scenario] = {}
  for s, rel in manifest["scenario_files"].items():
    for sc in schema.load_scenarios(_abs(rel)):
      if sc.id in manifest["scenario_ids"].get(s, []):
        scenarios[sc.id] = sc
  return scenarios


def cmd_judge(args: argparse.Namespace) -> int:
  from bench import judge  # pylint: disable=g-import-not-at-top

  out = _abs(args.out)
  with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as f:
    manifest = json.load(f)
  rollouts_path = os.path.join(out, "rollouts.jsonl")
  rollouts = load_rollouts(rollouts_path)
  scenarios = _run_scenarios(manifest)
  packs = load_packs(manifest.get("registries", DEFAULT_REGISTRIES))
  identifiers = sorted({i for p in packs for i in p.identifiers()})
  todo = [i for i, r in enumerate(rollouts)
          if r.status == "ok" and (args.rejudge or not r.judge)
          and scenarios[r.scenario_id].judge_criteria]
  print(f"judging {len(todo)} rollouts", file=sys.stderr)
  gemini_client.set_concurrency(args.concurrency)
  lock = threading.Lock()
  done = 0

  def one(i: int) -> Tuple[int, List[schema.JudgeResult]]:
    r = rollouts[i]
    return i, judge.judge_rollout(r, scenarios[r.scenario_id], identifiers)

  with concurrent.futures.ThreadPoolExecutor(args.concurrency) as ex:
    for fut in concurrent.futures.as_completed(
        [ex.submit(one, i) for i in todo]):
      i, res = fut.result()
      with lock:
        rollouts[i].judge = res
        done += 1
        if done % 250 == 0 or done == len(todo):
          write_rollouts_atomic(rollouts_path, rollouts)
          print(f"[{done}/{len(todo)}] judged", file=sys.stderr, flush=True)
        elif done % 25 == 0:
          print(f"[{done}/{len(todo)}] judged (in-memory)",
                file=sys.stderr, flush=True)
  write_rollouts_atomic(rollouts_path, rollouts)
  manifest["judged_at"] = _now()
  write_json_atomic(os.path.join(out, "manifest.json"), manifest)
  return 0


# -------------------------------------------------------------------- report


def public_subset(manifest: Dict[str, Any],
                  rollouts: List[schema.RolloutRecord]
                  ) -> Tuple[Dict[str, Any], List[schema.RolloutRecord]]:
  """Filters a run to its public frameworks (zero internal records)."""
  public = {f["key"] for f in manifest["frameworks"]
            if f.get("visibility") == "public"}
  pub_rollouts = [r for r in rollouts if r.framework in public
                  and r.framework_visibility == "public"]
  m = json.loads(json.dumps(manifest))
  m["frameworks"] = [f for f in m["frameworks"] if f["key"] in public]
  m["registry_frameworks"] = sorted(
      k for k in m.get("registry_frameworks", []) if k in public)
  m["registries"] = [r for r in m.get("registries", [])
                     if "internal" not in os.path.basename(r)]
  m["cells"] = {k: v for k, v in m.get("cells", {}).items() if k in public}
  m["harness_error_retries"] = {
      k: v for k, v in m.get("harness_error_retries", {}).items()
      if k in public}
  if "pack_digests" in m and isinstance(m["pack_digests"], dict):
    m["pack_digests"] = {
        k: v for k, v in m["pack_digests"].items() if k in public
    }
  m["visibility"] = "public"
  assert all(r.framework_visibility == "public" for r in pub_rollouts)
  return m, pub_rollouts


def cmd_report(args: argparse.Namespace) -> int:
  from bench import report  # pylint: disable=g-import-not-at-top
  from bench import stats  # pylint: disable=g-import-not-at-top

  out = _abs(args.out)
  with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as f:
    publish = bool(json.load(f).get("publish"))
  # A published report must be produced by exactly the code that ran.
  problems = verify(out, strict_config=publish)
  if problems:
    print("refusing to report; run is INVALID:\n  " + "\n  ".join(problems))
    return 1
  with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as f:
    manifest = json.load(f)
  rollouts_src = os.path.join(out, "rollouts.jsonl")
  rollouts = load_rollouts(rollouts_src)
  scenarios = list(_run_scenarios(manifest).values())
  visibility = (
      "public" if getattr(args, "public_only", False) else args.visibility
  )
  stage_to = _abs(args.stage_to) if getattr(args, "stage_to", "") else ""
  if visibility == "public":
    if not manifest.get("publish"):
      print("refusing to write a public report: this is not a --publish run "
            "(exploratory runs never get public artifacts)")
      return 1
    m, rs = public_subset(manifest, rollouts)
    dest = stage_to or os.path.join(out, "public")
    os.makedirs(dest, exist_ok=True)
    write_rollouts_atomic(os.path.join(dest, "rollouts.jsonl"), rs)
    write_json_atomic(os.path.join(dest, "manifest.json"), m)
    st = stats.compute(rs, scenarios, visibility="public", n_boot=args.n_boot)
    md = report.render(st, m, "public")
    path = os.path.join(dest, "report.md")
  else:
    dest = stage_to or out
    os.makedirs(dest, exist_ok=True)
    st = stats.compute(rollouts, scenarios, visibility="internal",
                       n_boot=args.n_boot)
    md = report.render(st, manifest, "internal")
    path = os.path.join(dest, "report.md")
    if os.path.abspath(dest) != os.path.abspath(out):
      shutil.copy2(
          os.path.join(out, "manifest.json"),
          os.path.join(dest, "manifest.json"),
      )
      if os.path.exists(rollouts_src):
        shutil.copy2(rollouts_src, os.path.join(dest, "rollouts.jsonl"))
      leak_src = os.path.join(out, "leakage.json")
      if os.path.exists(leak_src):
        shutil.copy2(leak_src, os.path.join(dest, "leakage.json"))
  with open(path, "w", encoding="utf-8") as f:
    f.write(md)
  write_json_atomic(os.path.join(os.path.dirname(path), "stats.json"), st)
  print(f"wrote {_rel(path)}")
  if getattr(args, "smoke_gate", False):
    return _check_smoke_gate(out, st, args)
  return 0


def _select_pillar_view(
    st_dict: Dict[str, Any], cfg: Dict[str, Any]
) -> Dict[str, Any]:
  """Selects the single-model or pooled ('all_models') pillar dictionary."""
  pillars_by_model = st_dict.get("pillars") or {}
  for candidate in (
      list(cfg.get("models", ["gemini-3.5-flash"]))
      + ["all_models", "__all_models__"]
      + list(pillars_by_model.keys())
  ):
    if candidate in pillars_by_model and isinstance(
        pillars_by_model[candidate], dict
    ):
      return pillars_by_model[candidate]
  return {}


def _check_smoke_gate(
    out: str, st: Dict[str, Any], args: argparse.Namespace
) -> int:
  """Verifies zero n-gram leakage and checks Armature pillar regressions."""
  from bench import frameworks as fw_loader  # pylint: disable=g-import-not-at-top
  import leakage_audit  # pylint: disable=g-import-not-at-top

  cfg_path = _abs(getattr(args, "smoke_config", "") or "smoke_config.json")
  cfg: Dict[str, Any] = {}
  if os.path.exists(cfg_path):
    with open(cfg_path, "r", encoding="utf-8") as f:
      cfg = json.load(f)
  max_reg_pp = float(cfg.get("max_regression_pp", 3.0))
  if getattr(args, "max_regression_pp", None) is not None:
    max_reg_pp = float(args.max_regression_pp)
  armature_fws = [
      fw for fw in cfg.get("frameworks", ["armature_oss"])
      if "armature" in fw
  ] or ["armature_oss"]

  leak_path = os.path.join(out, "leakage.json")
  if os.path.exists(leak_path):
    with open(leak_path, "r", encoding="utf-8") as f:
      leak = json.load(f)
  else:
    task_paths = sorted(glob.glob(os.path.join(BASE, "tasks", "*.jsonl")))
    units = leakage_audit.scenario_units_v2(task_paths)
    reg_paths = [
        _abs(r) for r in DEFAULT_REGISTRIES if os.path.exists(_abs(r))
    ]
    pack_texts = leakage_audit.pack_texts_v2(
        reg_paths, fw_loader.PACK_CACHE_DIR, verify=False
    )
    dist_1grams = leakage_audit.scenario_distinctive_tokens_v2(task_paths)
    leak = leakage_audit.audit(
        pack_texts, units, distinctive_1grams=dist_1grams
    )
  leak_keys = (
      "shared_1grams",
      "shared_3grams",
      "exclusive_3grams",
      "units_with_3gram",
      "shared_4grams",
      "units_with_4gram",
      "rule_1gram_hits",
      "core_3gram_hits",
      "core_4gram_hits",
      "heldout_3gram_hits",
      "heldout_4gram_hits",
  )
  frameworks_leak = leak.get("frameworks") or {}
  for fw in armature_fws:
    entry = frameworks_leak.get(fw) or {}
    for key in leak_keys:
      if int(entry.get(key, 0) or 0) > 0:
        print(f"SMOKE GATE FAILED: leakage {fw} {key}={entry.get(key)}",
              file=sys.stderr)
        return 1

  baseline_arg = getattr(args, "baseline", "")
  baseline_path = (
      _abs(baseline_arg)
      if baseline_arg
      else os.path.join(RESULTS_DIR, "v2-full-20261104", "stats.json")
  )
  if os.path.exists(baseline_path):
    with open(baseline_path, "r", encoding="utf-8") as f:
      base_st = json.load(f)
    cur_pillars = _select_pillar_view(st, cfg)
    base_pillars = _select_pillar_view(base_st, cfg)
    for fw in armature_fws:
      for pil, pdata in cur_pillars.items():
        cur_fw = (pdata.get("frameworks") or {}).get(fw, {})
        base_fw = (
            (base_pillars.get(pil) or {}).get("frameworks") or {}
        ).get(fw, {})
        cur_out = cur_fw.get("outcome") or {}
        base_out = base_fw.get("outcome") or {}
        cur_pt = (
            cur_out.get("mean")
            if cur_out.get("mean") is not None
            else cur_out.get("point")
        )
        base_pt = (
            base_out.get("mean")
            if base_out.get("mean") is not None
            else base_out.get("point")
        )
        if cur_pt is not None and base_pt is not None:
          drop_pp = (float(base_pt) - float(cur_pt)) * 100.0
          if drop_pp > max_reg_pp and float(cur_pt) < 0.90:
            print(
                f"SMOKE GATE FAILED: {fw} pillar {pil} regressed by "
                f"{drop_pp:.2f} pp (baseline {base_pt:.3f} -> {cur_pt:.3f}, "
                f"max allowed {max_reg_pp:.2f} pp)",
                file=sys.stderr,
            )
            return 1
  print("SMOKE GATE PASSED: zero n-gram leakage and pillar regressions within "
        f"<= {max_reg_pp:.2f} pp")
  return 0


# ------------------------------------------------------------------ calibrate


def cmd_calibrate(args: argparse.Namespace) -> int:
  """Runs end-to-end sampling, model labeling, and kappa agreement."""
  from bench import report  # pylint: disable=g-import-not-at-top
  from calibration import auto_label  # pylint: disable=g-import-not-at-top
  from calibration import compute_agreement  # pylint: disable=g-import-not-at-top
  from calibration import sample_for_labeling  # pylint: disable=g-import-not-at-top

  out = _abs(args.out)
  manifest_path = os.path.join(out, "manifest.json")
  rollouts_path = os.path.join(out, "rollouts.jsonl")
  if not os.path.exists(manifest_path) or not os.path.exists(rollouts_path):
    print(f"calibrate requires manifest.json and rollouts.jsonl in {out}",
          file=sys.stderr)
    return 1
  with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)
  run_id = manifest["run_id"]
  work_dir = (
      os.path.abspath(args.work_dir)
      if getattr(args, "work_dir", "")
      else os.path.join("/tmp/armature_bench/calibration", run_id)
  )
  os.makedirs(work_dir, exist_ok=True)

  sample_argv = ["--rollouts", rollouts_path, "--out", work_dir,
                 "--n", str(args.n), "--seed", str(args.seed)]
  for rel in manifest.get("scenario_files", {}).values():
    sample_argv.extend(["--scenarios", _abs(rel)])
  for reg in manifest.get("registries", DEFAULT_REGISTRIES):
    if os.path.exists(_abs(reg)):
      sample_argv.extend(["--registry", _abs(reg)])
  if getattr(args, "include_internal", True):
    sample_argv.append("--include-internal")

  rc = sample_for_labeling.main(sample_argv)
  if rc != 0:
    return rc

  items_path = os.path.join(work_dir, "items.jsonl")
  labels_csv = os.path.join(work_dir, "model_labels.csv")
  items = auto_label.load_calibration_items(items_path)
  auto_label.label_items(
      items,
      labels_csv,
      model=args.labeler_model,
      concurrency=args.concurrency,
      client=getattr(args, "_client", None),
  )

  run_agreement = os.path.join(out, "calibration_agreement.json")
  rc = compute_agreement.main([
      "--key", os.path.join(work_dir, "key.csv"),
      "--labels", labels_csv,
      "--out", run_agreement,
      "--n-boot", str(args.n_boot),
  ])
  if rc != 0:
    return rc

  if not getattr(args, "no_update_global", False):
    global_agreement = os.path.join(BASE, "calibration", "agreement.json")
    os.makedirs(os.path.dirname(global_agreement), exist_ok=True)
    shutil.copy2(run_agreement, global_agreement)

  stats_path = os.path.join(out, "stats.json")
  report_path = os.path.join(out, "report.md")
  if os.path.exists(stats_path) and os.path.exists(report_path):
    with open(stats_path, "r", encoding="utf-8") as f:
      st = json.load(f)
    md = report.render(st, manifest, manifest.get("visibility", "internal"))
    with open(report_path, "w", encoding="utf-8") as f:
      f.write(md)
  return 0


# ---------------------------------------------------------------------- main


def build_parser() -> argparse.ArgumentParser:
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawTextHelpFormatter)
  sub = ap.add_subparsers(dest="cmd", required=True)

  r = sub.add_parser("run", help="run the rollout matrix (resumable)")
  r.add_argument("--registry", action="append", default=None,
                 help="registry JSON (repeatable); default: public + internal")
  r.add_argument("--frameworks", default="",
                 help="comma-separated subset (not allowed with --publish)")
  r.add_argument("--sets", default="core,heldout")
  r.add_argument("--scenarios", default="",
                 help="comma-separated scenario ids (debug; not with --publish)")
  r.add_argument("--models", default=DEFAULT_MODELS)
  r.add_argument("--seeds", type=int, default=5)
  r.add_argument("--concurrency", type=int, default=8)
  r.add_argument("--run-id", default="")
  r.add_argument("--out", default="", help="default: results/<run_id>")
  r.add_argument(
      "--persist-rollouts",
      action=argparse.BooleanOptionalAction,
      default=True,
      help="persist rollouts.jsonl to results/<run_id>/ (default: True)",
  )
  r.add_argument("--publish", action="store_true")
  r.add_argument("--smoke", action="store_true",
                 help="run the 90-rollout stratified CI smoke subset from "
                      "smoke_config.json")
  r.add_argument("--smoke-config", default="",
                 help="optional path to smoke_config.json")
  r.add_argument("--retry-harness-errors", action="store_true",
                 help="re-run cells whose recorded rollout is a harness error")
  r.add_argument("--keep-sandboxes", action="store_true")
  r.set_defaults(func=cmd_run)

  j = sub.add_parser("judge", help="judge the rollouts of a run")
  j.add_argument("--out", required=True)
  j.add_argument("--concurrency", type=int, default=4)
  j.add_argument("--rejudge", action="store_true")
  j.set_defaults(func=cmd_judge)

  p = sub.add_parser("report", help="verify, compute stats, write report")
  p.add_argument("--out", required=True)
  p.add_argument("--visibility", choices=("internal", "public"),
                 default="internal")
  p.add_argument("--public-only", action="store_true",
                 help="shorthand for --visibility public")
  p.add_argument("--stage-to", default="",
                 help="stage report.md, stats.json, manifest.json, "
                      "leakage.json, and rollouts.jsonl to this directory")
  p.add_argument("--smoke-gate", action="store_true",
                 help="fail if n-gram leakage > 0 or Armature pillar "
                      "regression exceeds max_regression_pp")
  p.add_argument("--baseline", default="",
                 help="baseline stats.json for --smoke-gate comparison")
  p.add_argument("--max-regression-pp", type=float, default=None,
                 help="override max_regression_pp for --smoke-gate")
  p.add_argument("--n-boot", type=int, default=10_000)
  p.set_defaults(func=cmd_report)

  c = sub.add_parser("calibrate",
                     help="sample, auto-label, and compute judge calibration")
  c.add_argument("--out", required=True, help="run directory (results/<run_id>)")
  c.add_argument("--labeler-model", default="gemini-3.1-pro-preview")
  c.add_argument("--concurrency", type=int, default=10)
  c.add_argument("--n", type=int, default=100)
  c.add_argument("--seed", type=int, default=0)
  c.add_argument("--n-boot", type=int, default=2000)
  c.add_argument("--work-dir", default="",
                 help="scratch dir for blinded items (default: /tmp/...)")
  c.add_argument("--no-update-global", action="store_true",
                 help="do not overwrite calibration/agreement.json")
  c.set_defaults(func=cmd_calibrate)

  v = sub.add_parser("verify", help="full-matrix enforcement")
  v.add_argument("--out", required=True)
  v.add_argument("--strict-config", action="store_true",
                 help="also fail when current files no longer hash to the "
                      "run's config_hash")
  v.set_defaults(func=cmd_verify)
  return ap


def main(argv: Optional[List[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  if getattr(args, "registry", "unset") is None:
    args.registry = [r for r in DEFAULT_REGISTRIES if os.path.exists(_abs(r))]
  return args.func(args)


if __name__ == "__main__":
  sys.exit(main())
