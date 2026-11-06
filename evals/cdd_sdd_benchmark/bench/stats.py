"""Scoring and statistics for the CDD/SDD benchmark v2.

Implements DESIGN.md "Scoring and statistics":

- Per rollout: `outcome` = fraction of deterministic checks passed (PRIMARY);
  `judge` = mean of valid criterion scores; `combined` = mean of all items
  (checks and valid criteria weighted equally).
- Per (framework, model, set): scenario score = mean over seeds; framework
  score = mean over scenarios.
- CIs: two-level cluster bootstrap (resample scenarios with replacement, then
  seeds with replacement within each resampled scenario). The scenario
  resample is SHARED across frameworks in a cell, so paired differences are
  computed on the same resampled scenarios. The `all` set resamples core and
  held-out scenarios separately (stratified) and pools them.
- Tiers, not ranks: tier 1 = top framework plus every framework whose paired
  difference CI against it includes 0; repeat on the remainder.
- Run-to-run SD across seeds, cross-model swing, per-pillar breakdown, cost,
  harness errors, and inter-judge Cohen's kappa.

Harness-error rollouts and `None` criteria are excluded everywhere except the
harness-error table.
"""

from __future__ import annotations

import hashlib
import math
import random
import statistics
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from bench import judge as judge_lib
from bench import schema

METRICS = ("outcome", "judge", "combined")
PRIMARY_METRIC = "outcome"
N_BOOT = 10_000
BASE_SEED = 20261104
HARNESS_ERROR_THRESHOLD = 0.05
POOLED_MODEL = "all_models"
SET_VIEWS = ("core", "heldout", "all")
PRIMARY_JUDGES = judge_lib.PRIMARY_JUDGES


# --------------------------------------------------------------------------
# Small numeric helpers.
# --------------------------------------------------------------------------


def _mean(xs: Sequence[float]) -> Optional[float]:
  return sum(xs) / len(xs) if xs else None


def percentile(sorted_xs: Sequence[float], q: float) -> Optional[float]:
  """Linear-interpolated percentile of an already sorted list (q in [0,1])."""
  if not sorted_xs:
    return None
  if len(sorted_xs) == 1:
    return sorted_xs[0]
  pos = q * (len(sorted_xs) - 1)
  lo = int(math.floor(pos))
  hi = min(lo + 1, len(sorted_xs) - 1)
  frac = pos - lo
  return sorted_xs[lo] * (1 - frac) + sorted_xs[hi] * frac


def ci95(samples: Iterable[Optional[float]]) -> Tuple[Optional[float],
                                                       Optional[float]]:
  xs = sorted(x for x in samples if x is not None)
  return percentile(xs, 0.025), percentile(xs, 0.975)


def _rng(*key: Any) -> random.Random:
  """Deterministic RNG per cell, independent of evaluation order."""
  h = hashlib.sha256(repr((BASE_SEED,) + key).encode()).hexdigest()
  return random.Random(int(h[:16], 16))


def cohen_kappa(pairs: Sequence[Tuple[bool, bool]]) -> Optional[float]:
  """Cohen's kappa for two binary raters. None when undefined (p_e == 1)."""
  n = len(pairs)
  if n == 0:
    return None
  po = sum(1 for a, b in pairs if a == b) / n
  pa = sum(1 for a, _ in pairs if a) / n
  pb = sum(1 for _, b in pairs if b) / n
  pe = pa * pb + (1 - pa) * (1 - pb)
  if pe >= 1.0:
    return None
  return (po - pe) / (1 - pe)


def bootstrap_kappa(clusters: Dict[Any, List[Tuple[bool, bool]]],
                    n_boot: int = 2000, seed: int = BASE_SEED
                    ) -> Dict[str, Any]:
  """Kappa with a cluster bootstrap CI (clusters = scenarios)."""
  keys = [k for k, v in clusters.items() if v]
  allpairs = [p for k in keys for p in clusters[k]]
  point = cohen_kappa(allpairs)
  rng = random.Random(seed)
  samples = []
  for _ in range(n_boot if keys else 0):
    draw = rng.choices(keys, k=len(keys))
    k = cohen_kappa([p for c in draw for p in clusters[c]])
    if k is not None:
      samples.append(k)
  lo, hi = ci95(samples)
  agree = (sum(1 for a, b in allpairs if a == b) / len(allpairs)
           if allpairs else None)
  return {"kappa": point, "ci_lo": lo, "ci_hi": hi, "n_items": len(allpairs),
          "n_clusters": len(keys), "raw_agreement": agree}


# --------------------------------------------------------------------------
# Per-rollout scores.
# --------------------------------------------------------------------------


def rollout_scores(r: schema.RolloutRecord) -> Dict[str, Optional[float]]:
  checks = [1.0 if c.passed else 0.0 for c in r.checks]
  crit = [j.score for j in r.judge if j.score is not None]
  items = checks + crit
  return {
      "outcome": _mean(checks),
      "judge": _mean(crit),
      "combined": _mean(items),
  }


def _as_record(r: Any) -> schema.RolloutRecord:
  return r if isinstance(r, schema.RolloutRecord) else (
      schema.RolloutRecord.from_dict(r))


# --------------------------------------------------------------------------
# Cluster bootstrap.
# --------------------------------------------------------------------------

# Unit = one rollout's (outcome, judge, combined) tuple.
Unit = Tuple[Optional[float], Optional[float], Optional[float]]
# Cell data: fw -> scenario_id -> list of units (seeds, or model x seed).
CellData = Dict[str, Dict[str, List[Unit]]]


def _point(data: Dict[str, List[Unit]], scen: Sequence[str], mi: int
           ) -> Optional[float]:
  per = []
  for sid in scen:
    vals = [u[mi] for u in data.get(sid, []) if u[mi] is not None]
    if vals:
      per.append(sum(vals) / len(vals))
  return _mean(per)


def cluster_bootstrap(cell: CellData, strata: Sequence[Sequence[str]],
                      n_boot: int, rng: random.Random
                      ) -> Dict[str, List[List[Optional[float]]]]:
  """Two-level cluster bootstrap with shared scenario resamples.

  Args:
    cell: fw -> scenario -> units.
    strata: Lists of scenario ids; each stratum is resampled separately with
      its own size, then pooled (one stratum for a single set).
    n_boot: Number of bootstrap samples.
    rng: Seeded RNG.

  Returns:
    fw -> [metric_index] -> list of n_boot framework scores (None when no data).
  """
  fws = sorted(cell)
  out = {fw: [[None] * n_boot for _ in METRICS] for fw in fws}
  strata = [list(s) for s in strata if s]
  nm = len(METRICS)
  for b in range(n_boot):
    sampled: List[str] = []
    for st in strata:
      sampled.extend(rng.choices(st, k=len(st)))
    for fw in fws:
      data = cell[fw]
      sums = [0.0] * nm
      cnts = [0] * nm
      for sid in sampled:
        units = data.get(sid)
        if not units:
          continue
        draw = rng.choices(units, k=len(units)) if len(units) > 1 else units
        for mi in range(nm):
          s = 0.0
          c = 0
          for u in draw:
            v = u[mi]
            if v is not None:
              s += v
              c += 1
          if c:
            sums[mi] += s / c
            cnts[mi] += 1
      for mi in range(nm):
        if cnts[mi]:
          out[fw][mi][b] = sums[mi] / cnts[mi]
  return out


def paired_diff(a: List[Optional[float]], b: List[Optional[float]]
                ) -> Dict[str, Optional[float]]:
  diffs = [x - y for x, y in zip(a, b) if x is not None and y is not None]
  lo, hi = ci95(diffs)
  return {
      "mean": _mean(diffs),
      "ci_lo": lo,
      "ci_hi": hi,
      "p_gt_0": ((sum(1 for d in diffs if d > 0) / len(diffs))
                 if diffs else None),
  }


def assign_tiers(points: Dict[str, Optional[float]],
                 boots: Dict[str, List[Optional[float]]]) -> Dict[str, int]:
  """Tier 1 = top + all whose paired-diff CI vs top includes 0; repeat."""
  remaining = [f for f, p in points.items() if p is not None]
  tiers: Dict[str, int] = {}
  tier = 1
  while remaining:
    top = max(remaining, key=lambda f: (points[f], f))
    members = [top]
    for f in remaining:
      if f == top:
        continue
      d = paired_diff(boots[top], boots[f])
      if d["ci_lo"] is None or d["ci_lo"] <= 0.0:
        members.append(f)
    for f in members:
      tiers[f] = tier
      remaining.remove(f)
    tier += 1
  return tiers


# --------------------------------------------------------------------------
# Main entry point.
# --------------------------------------------------------------------------


def _summarize_cell(cell: CellData, strata: Sequence[Sequence[str]],
                    n_boot: int, rng: random.Random,
                    with_pairs: bool = True) -> Dict[str, Any]:
  """Point estimates, CIs, tiers, and pairwise diffs for one cell."""
  scen_all = [s for st in strata for s in st]
  boots = cluster_bootstrap(cell, strata, n_boot, rng)
  fws = sorted(cell)
  res: Dict[str, Any] = {"frameworks": {}, "n_scenarios": len(scen_all)}
  for fw in fws:
    entry = {}
    for mi, m in enumerate(METRICS):
      lo, hi = ci95(boots[fw][mi])
      entry[m] = {"mean": _point(cell[fw], scen_all, mi), "ci_lo": lo,
                  "ci_hi": hi}
    entry["n_rollouts"] = sum(len(v) for v in cell[fw].values())
    entry["n_scenarios_with_data"] = sum(1 for v in cell[fw].values() if v)
    res["frameworks"][fw] = entry
  if not with_pairs:
    return res
  for mi, m in enumerate(METRICS):
    points = {fw: res["frameworks"][fw][m]["mean"] for fw in fws}
    mb = {fw: boots[fw][mi] for fw in fws}
    tiers = assign_tiers(points, mb)
    pairs = {}
    for a in fws:
      for b in fws:
        if a != b:
          pairs[f"{a}|{b}"] = paired_diff(mb[a], mb[b])
    closest = {}
    for fw in fws:
      if points[fw] is None:
        continue
      others = [o for o in fws if o != fw and points[o] is not None]
      if others:
        o = min(others, key=lambda x: (abs(points[x] - points[fw]), x))
        closest[fw] = {"competitor": o, **pairs[f"{fw}|{o}"]}
    res.setdefault("tiers", {})[m] = tiers
    res.setdefault("paired", {})[m] = pairs
    res.setdefault("closest", {})[m] = closest
  return res


def compute(rollouts: Iterable[Any], scenarios: Iterable[schema.Scenario],
            visibility: str = "internal", n_boot: int = N_BOOT
            ) -> Dict[str, Any]:
  """Computes every statistic the report needs.

  Args:
    rollouts: RolloutRecords (or dicts) from one run.
    scenarios: The run's scenarios.
    visibility: "internal" (all frameworks) or "public" (drops frameworks whose
      framework_visibility is not "public" BEFORE any statistic, so tiers and
      closest competitors are computed among public frameworks only).
    n_boot: Bootstrap samples (10,000 for published reports).

  Returns:
    A JSON-serializable dict.
  """
  recs = [_as_record(r) for r in rollouts]
  if visibility == "public":
    recs = [r for r in recs if r.framework_visibility == "public"]
  scen = {s.id: s for s in scenarios}
  ok = [r for r in recs if r.status == "ok"]
  models = sorted({r.model for r in recs})
  fws = sorted({r.framework for r in recs})
  seeds = sorted({r.seed for r in recs})

  rows = []
  for r in ok:
    sc = rollout_scores(r)
    rows.append({"fw": r.framework, "model": r.model, "set": r.set,
                 "sid": r.scenario_id, "pillar": r.pillar, "seed": r.seed,
                 "unit": (sc["outcome"], sc["judge"], sc["combined"])})

  set_ids = {st: sorted(s.id for s in scen.values() if s.set == st)
             for st in schema.SETS}

  def strata_for(set_view: str, pillar: Optional[str] = None):
    sets = schema.SETS if set_view == "all" else (set_view,)
    out = []
    for st in sets:
      ids = [i for i in set_ids.get(st, [])
             if pillar is None or scen[i].pillar == pillar]
      out.append(ids)
    return out

  def cell_data(model: str, set_view: str, pillar: Optional[str] = None
                ) -> CellData:
    cd: CellData = {fw: {} for fw in fws}
    for row in rows:
      if model != POOLED_MODEL and row["model"] != model:
        continue
      if set_view != "all" and row["set"] != set_view:
        continue
      if pillar is not None and row["pillar"] != pillar:
        continue
      cd[row["fw"]].setdefault(row["sid"], []).append(row["unit"])
    return cd

  model_views = models + ([POOLED_MODEL] if len(models) > 1 else [])
  cells: Dict[str, Dict[str, Any]] = {}
  for m in model_views:
    cells[m] = {}
    for sv in SET_VIEWS:
      cells[m][sv] = _summarize_cell(cell_data(m, sv), strata_for(sv), n_boot,
                                     _rng("cell", m, sv))

  pillars: Dict[str, Dict[str, Any]] = {}
  for m in model_views:
    pillars[m] = {}
    for p in schema.PILLARS:
      st = strata_for("all", p)
      if not any(st):
        continue
      pillars[m][p] = _summarize_cell(cell_data(m, "all", p), st, n_boot,
                                      _rng("pillar", m, p), with_pairs=False)

  # Run-to-run variance: per-seed framework score (mean over scenarios), SD
  # across seeds; plus mean within-scenario SD across seeds.
  variance: Dict[str, Any] = {}
  for m in models:
    variance[m] = {}
    for sv in SET_VIEWS:
      variance[m][sv] = {}
      for fw in fws:
        per_seed = []
        per_scen: Dict[str, List[float]] = {}
        for sd in seeds:
          vals: Dict[str, List[float]] = {}
          for row in rows:
            if (row["fw"] == fw and row["model"] == m and row["seed"] == sd
                and (sv == "all" or row["set"] == sv)
                and row["unit"][0] is not None):
              vals.setdefault(row["sid"], []).append(row["unit"][0])
          if vals:
            per_seed.append(_mean([_mean(v) for v in vals.values()]))
            for sid, v in vals.items():
              per_scen.setdefault(sid, []).append(_mean(v))
        within = [statistics.stdev(v) for v in per_scen.values() if len(v) > 1]
        variance[m][sv][fw] = {
            "per_seed_scores": per_seed,
            "sd_across_seeds": (statistics.stdev(per_seed)
                                if len(per_seed) > 1 else None),
            "mean_within_scenario_sd": _mean(within),
        }

  # Cross-model swing (primary metric).
  swing: Dict[str, Any] = {}
  for sv in SET_VIEWS:
    swing[sv] = {}
    for fw in fws:
      by_model = {m: cells[m][sv]["frameworks"][fw][PRIMARY_METRIC]["mean"]
                  for m in models}
      tiers = {m: cells[m][sv].get("tiers", {}).get(PRIMARY_METRIC, {}).get(fw)
               for m in models}
      vals = [v for v in by_model.values() if v is not None]
      swing[sv][fw] = {"by_model": by_model, "tier_by_model": tiers,
                       "swing": (max(vals) - min(vals)) if len(vals) > 1
                                else None}

  # Held-out shift: core vs held-out per model view.
  heldout_shift: Dict[str, Any] = {}
  for m in model_views:
    c = cells[m]["core"]
    h = cells[m]["heldout"]
    heldout_shift[m] = {}
    for fw in fws:
      cm = c["frameworks"][fw][PRIMARY_METRIC]["mean"]
      hm = h["frameworks"][fw][PRIMARY_METRIC]["mean"]
      cc = c.get("closest", {}).get(PRIMARY_METRIC, {}).get(fw, {})
      # Lead vs the SAME competitor on held-out, for an apples-to-apples view.
      comp = cc.get("competitor")
      hc = (h.get("paired", {}).get(PRIMARY_METRIC, {}).get(f"{fw}|{comp}", {})
            if comp else {})
      heldout_shift[m][fw] = {
          "core": cm, "heldout": hm,
          "delta": (hm - cm) if cm is not None and hm is not None else None,
          "core_tier": c.get("tiers", {}).get(PRIMARY_METRIC, {}).get(fw),
          "heldout_tier": h.get("tiers", {}).get(PRIMARY_METRIC, {}).get(fw),
          "competitor": comp,
          "core_lead": cc.get("mean"),
          "heldout_lead": hc.get("mean"),
      }

  # Cost (ok rollouts only), reported separately per framework x model.
  cost: Dict[str, Any] = {}
  for fw in fws:
    cost[fw] = {}
    for m in models:
      rs = [r for r in ok if r.framework == fw and r.model == m]
      cost[fw][m] = {
          "n": len(rs),
          "input_tokens": _mean([r.usage.input_tokens for r in rs]),
          "output_tokens": _mean([r.usage.output_tokens for r in rs]),
          "thinking_tokens": _mean([r.usage.thinking_tokens for r in rs]),
          "cached_tokens": _mean([r.usage.cached_tokens for r in rs]),
          "api_calls": _mean([r.usage.api_calls for r in rs]),
          "latency_s": _mean([r.usage.latency_s for r in rs]),
          # Tokens billed on discarded attempts (empty candidates, 5xx),
          # kept apart from scored usage.
          "retry_input_tokens": _mean(
              [getattr(r, "retry_usage", schema.Usage()).input_tokens
               for r in rs]),
          "retry_output_tokens": _mean(
              [getattr(r, "retry_usage", schema.Usage()).output_tokens
               for r in rs]),
          "retry_thinking_tokens": _mean(
              [getattr(r, "retry_usage", schema.Usage()).thinking_tokens
               for r in rs]),
      }

  # Harness errors (all rollouts).
  harness: Dict[str, Any] = {"cells": {}, "invalid": False}
  for fw in fws:
    harness["cells"][fw] = {}
    for m in models:
      rs = [r for r in recs if r.framework == fw and r.model == m]
      errs = [r for r in rs if r.status != "ok"]
      rate = len(errs) / len(rs) if rs else 0.0
      bad = rate > HARNESS_ERROR_THRESHOLD
      harness["invalid"] = harness["invalid"] or bad
      kinds: Dict[str, int] = {}
      for r in errs:
        k = (r.error or "unknown").split(":")[0][:60]
        kinds[k] = kinds.get(k, 0) + 1
      harness["cells"][fw][m] = {"total": len(rs), "errors": len(errs),
                                 "rate": rate, "over_threshold": bad,
                                 "kinds": kinds}

  # Judge coverage and inter-judge agreement.
  judge_stats = _judge_agreement(ok)

  # run_command outcomes by source (mock | pack_tool | builtin | refused), so
  # the report can show frameworks whose own tooling was refused.
  commands: Dict[str, Any] = {}
  for fw in fws:
    commands[fw] = {}
    for m in models:
      rs = [r for r in ok if r.framework == fw and r.model == m]
      counts: Dict[str, int] = {}
      for r in rs:
        for a in r.action_log:
          if a.type != "run_command":
            continue
          src = getattr(a, "source", None) or (
              "mock" if a.mock_id else
              ("builtin" if a.executed else "refused"))
          counts[src] = counts.get(src, 0) + 1
      commands[fw][m] = {"n_rollouts": len(rs), "counts": counts,
                         "refused_per_rollout": (counts.get("refused", 0) /
                                                 len(rs)) if rs else None}

  # How turns ended (text | ask_user | max_steps | context_overflow). A high
  # max_steps rate means a framework's protocol is step-hungry.
  turn_endings: Dict[str, Any] = {}
  for fw in fws:
    turn_endings[fw] = {}
    for m in models:
      ends: Dict[str, int] = {}
      for r in ok:
        if r.framework != fw or r.model != m:
          continue
        for s in r.sessions:
          for t in s.turns:
            ends[t.ended_by] = ends.get(t.ended_by, 0) + 1
      n = sum(ends.values())
      turn_endings[fw][m] = {
          "n_turns": n, "counts": ends,
          "max_steps_rate": (ends.get("max_steps", 0) / n) if n else None,
          "context_overflow_rate": ((ends.get("context_overflow", 0) / n)
                                    if n else None),
      }

  return {
      "visibility": visibility,
      "n_boot": n_boot,
      "bootstrap_seed": BASE_SEED,
      "primary_metric": PRIMARY_METRIC,
      "frameworks": fws,
      "models": models,
      "model_views": model_views,
      "seeds": seeds,
      "scenario_counts": {st: len(set_ids.get(st, [])) for st in schema.SETS},
      "rollout_counts": {"total": len(recs), "ok": len(ok),
                         "harness_error": len(recs) - len(ok)},
      "cells": cells,
      "pillars": pillars,
      "variance": variance,
      "swing": swing,
      "heldout_shift": heldout_shift,
      "cost": cost,
      "harness": harness,
      "commands": commands,
      "turn_endings": turn_endings,
      "judge": judge_stats,
  }


def _judge_agreement(ok: List[schema.RolloutRecord]) -> Dict[str, Any]:
  """Inter-judge kappa (cluster bootstrap by scenario) and vote coverage."""
  total = 0
  excluded = 0
  not_sampled = 0
  invalid: Dict[str, int] = {}
  cast: Dict[str, int] = {}
  tiebreaks = 0
  pair_clusters: Dict[str, Dict[str, List[Tuple[bool, bool]]]] = {}
  for r in ok:
    for j in r.judge:
      total += 1
      if any(v == judge_lib.NOT_SAMPLED for v in (j.reasons or {}).values()):
        not_sampled += 1
      elif j.score is None:
        excluded += 1
      if len(j.votes) > 2:
        tiebreaks += 1
      for m, v in j.votes.items():
        cast[m] = cast.get(m, 0) + 1
        if v is None:
          invalid[m] = invalid.get(m, 0) + 1
      judges = sorted(j.votes)
      for i, a in enumerate(judges):
        for b in judges[i + 1:]:
          va, vb = j.votes[a], j.votes[b]
          if va is None or vb is None:
            continue
          pair_clusters.setdefault(f"{a}|{b}", {}).setdefault(
              r.scenario_id, []).append((va, vb))
  pairs = {k: bootstrap_kappa(v, seed=BASE_SEED)
           for k, v in sorted(pair_clusters.items())}
  primary_key = "|".join(sorted(PRIMARY_JUDGES))
  return {
      "criteria_total": total,
      "criteria_excluded": excluded,
      "criteria_not_sampled": not_sampled,
      "subsampled_judge": judge_lib.SUBSAMPLED_JUDGE,
      "tiebreaks": tiebreaks,
      "votes_cast": cast,
      "votes_invalid": invalid,
      "pairwise_kappa": pairs,
      "primary_kappa": pairs.get(primary_key),
      "note": ("Tiebreak-judge pairs are computed only on items where the "
               "primary judges disagreed, so their kappa is biased low and is "
               "not a measure of overall reliability."),
  }
