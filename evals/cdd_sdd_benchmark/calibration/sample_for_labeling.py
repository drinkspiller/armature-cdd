"""Draws a stratified sample of judged criteria for human labeling.

Usage (from the benchmark root):

  python3 calibration/sample_for_labeling.py \
      --rollouts results/<run_id>/rollouts.jsonl \
      --scenarios tasks/core_v2.jsonl --scenarios tasks/heldout_v2.jsonl \
      --registry frameworks/registry.json \
      --out /tmp/armature_bench/calibration/<run_id> [--n 100] [--seed 0]

Writes to --out:
  labeling.html  Single-file labeling page (blinded transcripts, criterion,
                 yes/no buttons, CSV export). Shows no framework, model, or
                 judge verdict, so labelers are blind to all three.
  items.csv      item_id, criterion (what labelers see, minus transcripts).
  key.csv        item_id -> run/framework/model/scenario/seed/pillar,
                 stratum, sampling weight, and judge votes. Labelers must not
                 open this file; compute_agreement.py joins on item_id.

Strata are pillar x framework x judge agreement (agree / disagree / invalid).
Allocation is round-robin across non-empty strata (equal allocation), so rare
strata such as judge disagreements are represented; each item carries an
inverse-probability weight so compute_agreement.py can also report a
population-weighted kappa.

This script never writes labels. Labels come only from humans via the page.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import random
import sys
from typing import Any, Dict, List

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
  sys.path.insert(0, _BASE)

from bench import blinding  # pylint: disable=g-import-not-at-top
from bench import judge as judge_lib  # pylint: disable=g-import-not-at-top
from bench import schema  # pylint: disable=g-import-not-at-top


def agreement_class(votes: Dict[str, Any]) -> str:
  prim = [votes.get(m) for m in judge_lib.PRIMARY_JUDGES]
  if any(v is None for v in prim):
    return "invalid"
  return "agree" if prim[0] == prim[1] else "disagree"


def load_identifiers(registries: List[str]) -> List[str]:
  """Union of identifiers across all frameworks in the given registries."""
  if not registries:
    print("WARNING: no --registry given; blinding uses defaults only.",
          file=sys.stderr)
    return []
  from bench import frameworks  # pylint: disable=g-import-not-at-top
  idents: List[str] = []
  try:
    for pack in frameworks.load_registry(registries):
      idents.extend(pack.identifiers())
  except Exception:  # pylint: disable=broad-except
    for reg_path in registries:
      if not os.path.exists(reg_path):
        continue
      with open(reg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
      for entry in data.get("frameworks", []):
        if isinstance(entry, dict):
          idents.extend(entry.get("identifiers", []))
          for k in ("key", "display_name"):
            if entry.get(k):
              idents.append(str(entry[k]))
  return sorted(set(idents))


def stratified_sample(items: List[Dict[str, Any]], n: int, seed: int
                      ) -> List[Dict[str, Any]]:
  """Equal-allocation round-robin sample across strata with IPW weights."""
  rng = random.Random(seed)
  strata: Dict[str, List[Dict[str, Any]]] = {}
  for it in items:
    strata.setdefault(it["stratum"], []).append(it)
  for v in strata.values():
    rng.shuffle(v)
  keys = sorted(strata)
  rng.shuffle(keys)
  picked: Dict[str, List[Dict[str, Any]]] = {k: [] for k in keys}
  total = 0
  while total < n and any(len(picked[k]) < len(strata[k]) for k in keys):
    for k in keys:
      if total >= n:
        break
      if len(picked[k]) < len(strata[k]):
        picked[k].append(strata[k][len(picked[k])])
        total += 1
  out = []
  for k in keys:
    for it in picked[k]:
      it = dict(it)
      it["weight"] = len(strata[k]) / len(picked[k])
      out.append(it)
  rng.shuffle(out)
  for i, it in enumerate(out):
    it["item_id"] = f"item_{i + 1:03d}"
  return out


def build_items(rollouts: List[schema.RolloutRecord],
                scenarios: Dict[str, schema.Scenario],
                identifiers: List[str]) -> List[Dict[str, Any]]:
  items = []
  for r in rollouts:
    if r.status != "ok" or r.scenario_id not in scenarios:
      continue
    sc = scenarios[r.scenario_id]
    for ci, j in enumerate(r.judge):
      if (j.reasons or {}).get(judge_lib.SUBSAMPLED_JUDGE) == judge_lib.NOT_SAMPLED:
        continue
      ag = agreement_class(j.votes)
      items.append({
          "rollout": r, "scenario": sc, "criterion_index": ci,
          "criterion": j.criterion, "votes": j.votes, "score": j.score,
          "agreement": ag,
          "stratum": f"{r.pillar}|{r.framework}|{ag}",
      })
  return items


_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Judge calibration labeling</title>
<style>
body{font:14px/1.45 system-ui,sans-serif;margin:0;display:flex;height:100vh}
#nav{width:220px;overflow:auto;border-right:1px solid #ccc;padding:8px}
#nav div{cursor:pointer;padding:2px 4px}#nav .done{color:#888}
#nav .cur{background:#e8eefc}
#main{flex:1;overflow:auto;padding:16px}
pre{white-space:pre-wrap;background:#f6f6f6;padding:8px;max-height:45vh;
overflow:auto}
#crit{font-size:16px;font-weight:600;background:#fff8dc;padding:8px}
button{font-size:15px;padding:6px 16px;margin-right:8px}
</style></head><body>
<div id="nav"></div><div id="main">
<p>Labeler: <input id="who" placeholder="your name"> &nbsp;
<button onclick="exportCsv()">Export labels CSV</button>
<span id="prog"></span></p>
<p>Decide whether the agent satisfied the criterion, using the action log as
the authoritative record. Ignore formatting. Tokens like [FRAMEWORK] are
blinded names.</p>
<div id="crit"></div>
<p><button onclick="setLabel(1)">Yes (met)</button>
<button onclick="setLabel(0)">No (not met)</button>
<button onclick="setLabel('')">Clear</button>
<button onclick="go(1)">Next &rarr;</button>
Notes: <input id="notes" size="50" onchange="saveNotes()"></p>
<b>Current label:</b> <span id="cur"></span>
<h3>Situation</h3><pre id="sit"></pre>
<h3>Action log</h3><pre id="act"></pre>
<h3>Transcript</h3><pre id="tr"></pre>
</div>
<script>
const ITEMS = __ITEMS__;
const KEY = "calib_" + __RUNKEY__;
let st = JSON.parse(localStorage.getItem(KEY) || "{}");
let i = 0;
function save(){localStorage.setItem(KEY, JSON.stringify(st));}
function nav(){const n=document.getElementById("nav");n.innerHTML="";
 ITEMS.forEach((it,k)=>{const d=document.createElement("div");
 const l=(st[it.item_id]||{}).label;
 d.textContent=it.item_id+(l===undefined||l===""?"":(l?" yes":" no"));
 d.className=(k===i?"cur ":"")+(l===undefined||l===""?"":"done");
 d.onclick=()=>{i=k;show();};n.appendChild(d);});
 const done=ITEMS.filter(it=>{const l=(st[it.item_id]||{}).label;
 return l!==undefined&&l!=="";}).length;
 document.getElementById("prog").textContent=
   done+" / "+ITEMS.length+" labeled";}
function show(){const it=ITEMS[i];
 document.getElementById("crit").textContent=it.item_id+": "+it.criterion;
 document.getElementById("sit").textContent=it.situation;
 document.getElementById("act").textContent=it.actions;
 document.getElementById("tr").textContent=it.transcript;
 const s=st[it.item_id]||{};
 document.getElementById("cur").textContent=
   s.label===undefined||s.label===""?"(none)":(s.label?"yes":"no");
 document.getElementById("notes").value=s.notes||"";nav();}
function setLabel(v){const id=ITEMS[i].item_id;st[id]=st[id]||{};
 st[id].label=v;save();show();}
function saveNotes(){const id=ITEMS[i].item_id;st[id]=st[id]||{};
 st[id].notes=document.getElementById("notes").value;save();}
function go(d){i=Math.max(0,Math.min(ITEMS.length-1,i+d));show();}
function q(s){return '"'+String(s).replace(/"/g,'""')+'"';}
function exportCsv(){const who=document.getElementById("who").value.trim();
 if(!who){alert("Enter your name first.");return;}
 let out="item_id,human_label,labeler,notes\\n";
 ITEMS.forEach(it=>{const s=st[it.item_id]||{};
  if(s.label===undefined||s.label==="")return;
  out+=[it.item_id,s.label,q(who),q(s.notes||"")].join(",")+"\\n";});
 const a=document.createElement("a");
 a.href=URL.createObjectURL(new Blob([out],{type:"text/csv"}));
 a.download="labels_"+who.replace(/\\W+/g,"_")+".csv";a.click();}
show();
</script></body></html>
"""


def write_outputs(sample: List[Dict[str, Any]], identifiers: List[str],
                  out_dir: str, run_id: str) -> None:
  os.makedirs(out_dir, exist_ok=True)
  page_items = []
  for it in sample:
    r, sc = it["rollout"], it["scenario"]
    page_items.append({
        "item_id": it["item_id"],
        "criterion": it["criterion"],
        "situation": blinding.blind(sc.description, identifiers),
        "actions": blinding.blind(judge_lib.render_action_log(r), identifiers),
        "transcript": blinding.blind(judge_lib.render_transcript(r),
                                     identifiers),
    })
  # Escape "</" so transcript text cannot terminate the script element.
  blob = json.dumps(page_items, ensure_ascii=False).replace("</", "<\\/")
  page = (_HTML.replace("__ITEMS__", blob)
          .replace("__RUNKEY__", json.dumps(html.escape(run_id))))
  with open(os.path.join(out_dir, "labeling.html"), "w",
            encoding="utf-8") as f:
    f.write(page)
  with open(os.path.join(out_dir, "items.csv"), "w", newline="",
            encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["item_id", "criterion"])
    for it in sample:
      w.writerow([it["item_id"], it["criterion"]])
  with open(os.path.join(out_dir, "items.jsonl"), "w",
            encoding="utf-8") as f:
    for item_obj in page_items:
      f.write(json.dumps(item_obj, ensure_ascii=False) + "\n")
  with open(os.path.join(out_dir, "key.csv"), "w", newline="",
            encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["item_id", "run_id", "framework", "model", "scenario_id",
                "set", "pillar", "seed", "criterion_index", "stratum",
                "weight", "agreement", "ensemble_score", "votes_json"])
    for it in sample:
      r = it["rollout"]
      w.writerow([it["item_id"], r.run_id, r.framework, r.model,
                  r.scenario_id, r.set, r.pillar, r.seed,
                  it["criterion_index"], it["stratum"],
                  f"{it['weight']:.6f}", it["agreement"],
                  "" if it["score"] is None else it["score"],
                  json.dumps(it["votes"])])


def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--rollouts", required=True)
  ap.add_argument("--scenarios", action="append", required=True)
  ap.add_argument("--registry", action="append", default=[])
  ap.add_argument("--out", required=True)
  ap.add_argument("--n", type=int, default=100)
  ap.add_argument("--seed", type=int, default=0)
  ap.add_argument("--include-internal", action="store_true",
                  help="Include internal-visibility frameworks.")
  a = ap.parse_args(argv)
  bench_root = os.path.realpath(
      os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  )
  if os.path.realpath(a.out).startswith(bench_root + os.sep):
    print("Refusing to write blinded transcripts into the repository checkout; "
          "use a /tmp path.", file=sys.stderr)
    return 2
  scen = {}
  for p in a.scenarios:
    for s in schema.load_scenarios(p):
      scen[s.id] = s
  recs = []
  with open(a.rollouts, "r", encoding="utf-8") as f:
    for line in f:
      if line.strip():
        r = schema.RolloutRecord.from_dict(json.loads(line))
        if a.include_internal or r.framework_visibility == "public":
          recs.append(r)
  run_ids = {r.run_id for r in recs}
  if len(run_ids) != 1:
    print(f"Expected exactly one run_id, got {sorted(run_ids)}",
          file=sys.stderr)
    return 1
  idents = load_identifiers(a.registry) + sorted({r.framework for r in recs})
  items = build_items(recs, scen, idents)
  if not items:
    print("No judged criteria found; run the judge first.", file=sys.stderr)
    return 1
  sample = stratified_sample(items, a.n, a.seed)
  write_outputs(sample, idents, a.out, run_ids.pop())
  strata = sorted({it["stratum"] for it in sample})
  print(f"Wrote {len(sample)} items from {len(items)} judged criteria "
        f"({len(strata)} strata) to {a.out}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
