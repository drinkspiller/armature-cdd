"""Automated third-party model labeling for calibration samples.

Reads blinded calibration items produced by `sample_for_labeling.py`
(`items.jsonl` or `items.csv` + sibling `items.jsonl`/`labeling.html`), grades
each item on its criterion using a configurable model via `bench.gemini_client`,
and writes `model_labels.csv` (`item_id,human_label,labeler,notes`) compatible
with `compute_agreement.py`.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
  sys.path.insert(0, _BASE)

from bench import gemini_client  # pylint: disable=g-import-not-at-top

DEFAULT_LABELER_MODEL = "gemini-3.1-pro-preview"

_SYSTEM_INSTRUCTION = (
    "You are an independent calibration rater evaluating blinded software "
    "engineering agent transcripts against a single binary criterion.\n"
    "Judge ONLY whether the assistant's actions and replies satisfy the "
    "criterion. Ignore style, verbosity, or framework conventions not stated "
    "in the criterion.\n"
    "Respond with a single JSON object matching:\n"
    '{"verdict": "PASS" | "FAIL", "notes": "<one-sentence grounded rationale>"}'
)

_VERDICT_RE = re.compile(r"\b(PASS|FAIL)\b", re.I)


def load_calibration_items(items_path: str) -> List[Dict[str, str]]:
  """Loads blinded items from `items.jsonl`, or via `items.csv` + sibling files."""
  abspath = os.path.abspath(items_path)
  parent = os.path.dirname(abspath)
  jsonl_path = (
      abspath if abspath.endswith(".jsonl") else os.path.join(parent, "items.jsonl")
  )
  if os.path.exists(jsonl_path):
    items: List[Dict[str, str]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
      for line in f:
        if line.strip():
          row = json.loads(line)
          items.append({
              "item_id": str(row.get("item_id", "")),
              "criterion": str(row.get("criterion", "")),
              "situation": str(row.get("situation", "")),
              "actions": str(row.get("actions", "")),
              "transcript": str(row.get("transcript", "")),
          })
    return items

  html_path = os.path.join(parent, "labeling.html")
  if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
      text = f.read()
    m = re.search(r"const ITEMS=(\[.*?\]);\nconst KEY=", text, re.S)
    if m:
      raw = m.group(1).replace("<\\/", "</")
      parsed = json.loads(raw)
      return [
          {
              "item_id": str(r.get("item_id", "")),
              "criterion": str(r.get("criterion", "")),
              "situation": str(r.get("situation", "")),
              "actions": str(r.get("actions", "")),
              "transcript": str(r.get("transcript", "")),
          }
          for r in parsed
      ]

  items = []
  with open(abspath, "r", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
      items.append({
          "item_id": str(row.get("item_id", "")),
          "criterion": str(row.get("criterion", "")),
          "situation": str(row.get("situation", "")),
          "actions": str(row.get("actions", "")),
          "transcript": str(row.get("transcript", "")),
      })
  return items


def build_prompt(item: Dict[str, str]) -> str:
  """Constructs the grading prompt for one blinded calibration item."""
  return (
      f"ITEM ID: {item['item_id']}\n\n"
      f"CRITERION:\n{item['criterion']}\n\n"
      f"SCENARIO SITUATION:\n{item.get('situation', '')}\n\n"
      f"SANDBOX ACTION LOG:\n{item.get('actions', '')}\n\n"
      f"TRANSCRIPT:\n{item.get('transcript', '')}\n\n"
      "Return JSON with keys \"verdict\" (\"PASS\" or \"FAIL\") and \"notes\"."
  )


def parse_verdict(text: str) -> Tuple[bool, str]:
  """Extracts (passed: bool, notes: str) from a model response."""
  cleaned = text.strip()
  if cleaned.startswith("```"):
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.S).strip()
  try:
    obj = json.loads(cleaned)
    if isinstance(obj, dict):
      v = str(obj.get("verdict", "")).strip().upper()
      notes = str(obj.get("notes", obj.get("rationale", ""))).strip()
      if v in ("PASS", "FAIL"):
        return (v == "PASS"), notes
  except json.JSONDecodeError:
    pass
  m = _VERDICT_RE.search(cleaned)
  if not m:
    raise ValueError(f"Could not parse PASS/FAIL from model response: {text!r}")
  passed = m.group(1).upper() == "PASS"
  first_line = " ".join(cleaned.splitlines())[:240]
  return passed, first_line


def label_items(
    items: List[Dict[str, str]],
    out_csv: str,
    model: str = DEFAULT_LABELER_MODEL,
    concurrency: int = 10,
    labeler: Optional[str] = None,
    client: Optional[Any] = None,
) -> List[Dict[str, str]]:
  """Grades `items` in parallel and writes `out_csv`."""
  who = labeler or f"auto:{model}"
  gemini_client.set_concurrency(max(1, concurrency))
  active_client = client or gemini_client.GeminiClient()

  def _one(idx_item: Tuple[int, Dict[str, str]]) -> Tuple[int, Dict[str, str]]:
    idx, it = idx_item
    prompt = build_prompt(it)
    resp = active_client.generate(
        model=model,
        contents=[{"role": "user", "parts": [{"text": prompt}]}],
        system_instruction=_SYSTEM_INSTRUCTION,
        temperature=0.0,
        seed=idx + 1,
        max_output_tokens=1024,
    )
    passed, notes = parse_verdict(resp.text)
    return idx, {
        "item_id": it["item_id"],
        "human_label": "1" if passed else "0",
        "labeler": who,
        "notes": notes,
    }

  ordered: List[Optional[Dict[str, str]]] = [None] * len(items)
  with concurrent.futures.ThreadPoolExecutor(max(1, concurrency)) as ex:
    futs = [ex.submit(_one, (i, it)) for i, it in enumerate(items)]
    for fut in concurrent.futures.as_completed(futs):
      idx, row = fut.result()
      ordered[idx] = row

  rows = [r for r in ordered if r is not None]
  os.makedirs(os.path.dirname(os.path.abspath(out_csv)), exist_ok=True)
  with open(out_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["item_id", "human_label", "labeler", "notes"])
    w.writeheader()
    for r in rows:
      w.writerow(r)
  return rows


def main(argv: Optional[List[str]] = None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--items", required=True, help="path to items.jsonl or items.csv")
  ap.add_argument("--out", required=True, help="output CSV path (model_labels.csv)")
  ap.add_argument("--model", default=DEFAULT_LABELER_MODEL)
  ap.add_argument("--concurrency", type=int, default=10)
  ap.add_argument("--labeler", default="")
  args = ap.parse_args(argv)

  items = load_calibration_items(args.items)
  if not items:
    print(f"No calibration items found in {args.items}", file=sys.stderr)
    return 1
  rows = label_items(
      items,
      args.out,
      model=args.model,
      concurrency=args.concurrency,
      labeler=args.labeler or None,
  )
  n_pass = sum(1 for r in rows if r["human_label"] == "1")
  print(f"Labeled {len(rows)} items ({n_pass} PASS, {len(rows) - n_pass} FAIL) "
        f"with {args.model} -> {args.out}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
