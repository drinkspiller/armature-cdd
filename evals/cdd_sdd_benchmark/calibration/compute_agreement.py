"""Judge-vs-human agreement for the calibration sample.

Usage (from the benchmark root):

  python3 calibration/compute_agreement.py \
      --key /tmp/armature_bench/calibration/<run_id>/key.csv \
      --labels labels_alice.csv --labels labels_bob.csv \
      [--out calibration/agreement.json]

For each judge model and for the ensemble (score > 0.5 = pass; exact 0.5 ties
are excluded) this reports Cohen's kappa against the human label with a 95%
cluster-bootstrap CI (clusters = scenarios), raw agreement, n, and a
population-weighted kappa using the sampling weights in key.csv. With more
than one labeler it also reports human-human kappa on overlapping items, and
uses the per-item majority as the human label (ties excluded).

It refuses to run without real human labels. It never invents labels.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
  sys.path.insert(0, _BASE)

from bench import stats  # pylint: disable=g-import-not-at-top


def weighted_kappa(triples: List[Tuple[bool, bool, float]]) -> Optional[float]:
  """Cohen's kappa with per-item weights (population-weighted estimate)."""
  tw = sum(w for _, _, w in triples)
  if tw <= 0:
    return None
  po = sum(w for a, b, w in triples if a == b) / tw
  pa = sum(w for a, _, w in triples if a) / tw
  pb = sum(w for _, b, w in triples if b) / tw
  pe = pa * pb + (1 - pa) * (1 - pb)
  if pe >= 1.0:
    return None
  return (po - pe) / (1 - pe)


def read_labels(paths: List[str]) -> Dict[str, Dict[str, bool]]:
  """Returns item_id -> {labeler: label}. Rejects malformed rows."""
  out: Dict[str, Dict[str, bool]] = {}
  for p in paths:
    with open(p, "r", newline="", encoding="utf-8") as f:
      for row in csv.DictReader(f):
        v = (row.get("human_label") or "").strip()
        if v == "":
          continue
        if v not in ("0", "1"):
          raise ValueError(f"{p}: bad human_label {v!r} for {row}")
        who = (row.get("labeler") or os.path.basename(p)).strip()
        out.setdefault(row["item_id"], {})[who] = v == "1"
  return out


def human_consensus(labels: Dict[str, Dict[str, bool]]) -> Dict[str, bool]:
  out = {}
  for item, by in labels.items():
    yes = sum(1 for v in by.values() if v)
    no = len(by) - yes
    if yes != no:
      out[item] = yes > no
  return out


def inter_human(labels: Dict[str, Dict[str, bool]], key: Dict[str, Dict]
                ) -> Dict[str, Any]:
  labelers = sorted({w for by in labels.values() for w in by})
  res = {}
  for i, a in enumerate(labelers):
    for b in labelers[i + 1:]:
      clusters: Dict[str, List[Tuple[bool, bool]]] = {}
      for item, by in labels.items():
        if a in by and b in by and item in key:
          clusters.setdefault(key[item]["scenario_id"], []).append(
              (by[a], by[b]))
      if clusters:
        res[f"{a}|{b}"] = stats.bootstrap_kappa(clusters)
  return res


def agreement(key: Dict[str, Dict], human: Dict[str, bool],
              n_boot: int = 2000) -> Dict[str, Any]:
  """Per-judge and ensemble kappa vs human."""
  per: Dict[str, Dict[str, List[Tuple[bool, bool]]]] = {}
  weighted: Dict[str, List[Tuple[bool, bool, float]]] = {}
  for item, h in human.items():
    k = key.get(item)
    if k is None:
      continue
    votes = json.loads(k["votes_json"])
    preds: Dict[str, Optional[bool]] = dict(votes)
    s = k.get("ensemble_score", "")
    if s not in ("", None):
      sv = float(s)
      preds["ensemble"] = None if sv == 0.5 else sv > 0.5
    w = float(k.get("weight") or 1.0)
    for judge, p in preds.items():
      if p is None:
        continue
      per.setdefault(judge, {}).setdefault(k["scenario_id"], []).append(
          (bool(p), h))
      weighted.setdefault(judge, []).append((bool(p), h, w))
  out = {}
  for judge, clusters in sorted(per.items()):
    r = stats.bootstrap_kappa(clusters, n_boot=n_boot)
    r["weighted_kappa"] = weighted_kappa(weighted[judge])
    out[judge] = r
  return out


def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--key", required=True)
  ap.add_argument("--labels", action="append", required=True)
  ap.add_argument("--out", default=os.path.join(_BASE, "calibration",
                                                "agreement.json"))
  ap.add_argument("--n-boot", type=int, default=2000)
  a = ap.parse_args(argv)
  with open(a.key, "r", newline="", encoding="utf-8") as f:
    key = {row["item_id"]: row for row in csv.DictReader(f)}
  labels = read_labels(a.labels)
  if not labels:
    print("No human labels found. Label items in labeling.html first; this "
          "tool never fabricates labels.", file=sys.stderr)
    return 1
  unknown = [i for i in labels if i not in key]
  if unknown:
    print(f"Labels reference unknown items: {unknown[:5]}", file=sys.stderr)
    return 1
  human = human_consensus(labels)
  result = {
      "run_ids": sorted({key[i]["run_id"] for i in labels}),
      "n_items_sampled": len(key),
      "n_items_labeled": len(labels),
      "n_items_with_consensus": len(human),
      "labelers": sorted({w for by in labels.values() for w in by}),
      "per_judge": agreement(key, human, a.n_boot),
      "inter_human": inter_human(labels, key),
      "note": ("kappa/CI are on the stratified sample (disagreement strata "
               "are oversampled); weighted_kappa re-weights to the run's "
               "population of judged criteria."),
  }
  os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
  with open(a.out, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
  for j, r in result["per_judge"].items():
    print(f"{j:28s} kappa={r['kappa']} CI=[{r['ci_lo']}, {r['ci_hi']}] "
          f"n={r['n_items']} weighted={r['weighted_kappa']}")
  print(f"Wrote {a.out}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
