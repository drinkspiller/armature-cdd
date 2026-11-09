#!/usr/bin/env python3
"""N-gram leakage audit: does any framework's pack text echo the scenarios?

v1's Armature prompt contained near-verbatim answers to several judge criteria
while competitor prompts shared almost nothing with them. This audit measures
that overlap for every pack the benchmark loads, against every scenario text
the agent or judge sees:

* scenario units: each user turn, each judge criterion, each check
  description (one unit each);
* pack text: every file the pack loads (always-on, skills, commands, extra
  files, generated install files), exactly as placed in the sandbox.

Text is lower-cased, tokenized into words, and stopwords are dropped; 3-grams
and 4-grams are formed over the remaining content words. For each framework it
reports: shared distinctive 3-/4-grams (unique), how many scenario units share
at least one 3-gram / 4-gram, n-grams shared with this pack and no other pack
("exclusive"), and the top matches with an example unit.

Usage:
  python3 leakage_audit.py                       # tasks/*.jsonl vs registries
  python3 leakage_audit.py --out-json results/<run_id>/leakage.json \
      --out-md results/<run_id>/leakage.md
  python3 leakage_audit.py --legacy              # v1 data, reproduces v1 finding
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

sys.dont_write_bytecode = True
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from bench import frameworks as fw  # pylint: disable=g-import-not-at-top

# Standard English function words plus a few chat fillers. Content words such
# as "approval", "rollback", or "backward" are deliberately kept.
STOPWORDS = frozenset("""
a about above after again against all also am an and any are aren't as at be
because been before being below between both but by can can't cannot could
couldn't did didn't do does doesn't doing don't down during each either else
etc even ever every few for from further get gets got had hadn't has hasn't
have haven't having he her here hers herself him himself his how however i if
in into is isn't it it's its itself just let let's like may me might more most
must mustn't my myself need needs no nor not now of off on once one only or
other others otherwise our ours ourselves out over own per please rather re
same shall she should shouldn't since so some such than that that's the their
theirs them themselves then there there's these they this those through thus
to too under until up upon us use used using very via was wasn't we were
weren't what when where whether which while who whom whose why will with
within without won't would wouldn't yes yet you your yours yourself
yourselves e g i.e e.g vs
""".split())

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_'.-]*[a-z0-9]|[a-z0-9]")


def tokenize(text: str) -> List[str]:
  """Lower-cased content-word tokens (stopwords and 1-char tokens removed)."""
  toks = _TOKEN_RE.findall(text.lower())
  return [t for t in toks if t not in STOPWORDS and len(t) > 1]


def ngrams(tokens: Sequence[str], n: int) -> Set[Tuple[str, ...]]:
  return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def _text_ngrams(text: str, n: int) -> Set[Tuple[str, ...]]:
  # N-grams never span paragraph/line boundaries, so list items stay separate.
  out: Set[Tuple[str, ...]] = set()
  for line in re.split(r"[\n\r]+|(?<=[.!?;:])\s+", text):
    out |= ngrams(tokenize(line), n)
  return out


# ---------------------------------------------------------------------------
# Inputs.
# ---------------------------------------------------------------------------


def scenario_units_v2(paths: Iterable[str]) -> List[Dict[str, str]]:
  """Units from v2 scenario files: user turns, judge criteria, check descs."""
  units = []
  for path in paths:
    with open(path, "r", encoding="utf-8") as f:
      for line in f:
        line = line.strip()
        if not line:
          continue
        d = json.loads(line)
        sid = d.get("id", "?")
        for si, s in enumerate(d.get("sessions", [])):
          for ti, t in enumerate(s.get("turns", [])):
            units.append({"scenario": sid, "kind": "turn",
                          "where": f"s{si}t{ti}", "text": t})
        for ci, c in enumerate(d.get("judge_criteria", [])):
          units.append({"scenario": sid, "kind": "criterion",
                        "where": f"c{ci}", "text": c})
        for c in d.get("checks", []):
          units.append({"scenario": sid, "kind": "check",
                        "where": c.get("id", "?"),
                        "text": c.get("description", "")})
  return units


def scenario_units_legacy(path: str) -> List[Dict[str, str]]:
  """Units from v1 `scenarios.jsonl`: user turns and eval criteria."""
  units = []
  with open(path, "r", encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      d = json.loads(line)
      sid = d.get("id", "?")
      for ti, t in enumerate(d.get("turns", [])):
        if t.get("role") == "user":
          units.append({"scenario": sid, "kind": "turn", "where": f"t{ti}",
                        "text": t.get("content", "")})
      for ci, c in enumerate(d.get("eval_criteria", [])):
        units.append({"scenario": sid, "kind": "criterion", "where": f"c{ci}",
                      "text": c})
  return units


def pack_texts_v2(registry_paths: List[str], cache_dir: str,
                  verify: bool) -> Dict[str, Dict[str, Any]]:
  """framework key -> {display_name, visibility, text, always_on_text}."""
  out = {}
  for pack in fw.load_registry(registry_paths, cache_dir=cache_dir, verify=verify):
    texts = list(pack.sandbox_files().values())
    always_on_fn = getattr(pack, "always_on", None)
    ao_items = always_on_fn() if callable(always_on_fn) else []
    ao_text = "\n\n".join(
        txt for item in ao_items
        for txt in ([item[1]] if isinstance(item, tuple) else [str(item)])
    )
    skill_texts = [ao_text] if ao_text else []
    raw_text_fn = getattr(pack, "raw_text", None)
    if callable(raw_text_fn) and isinstance(getattr(pack, "entry", None), dict):
      for rel in (pack.entry.get("skills_index") or {}).values():
        st = raw_text_fn(rel)
        if st:
          skill_texts.append(st)
    out[pack.key] = {
        "display_name": pack.display_name,
        "visibility": pack.visibility,
        "text": "\n\n".join(texts),
        "always_on_text": ao_text,
        "always_on_and_skills_text": "\n\n".join(skill_texts) or "\n\n".join(texts),
    }
  return out


DEFAULT_GENERIC_TERMS_PATH = os.path.join(
    fw.FRAMEWORKS_DIR, "generic_terms.txt"
)
_SCENARIO_TOKEN_RE = re.compile(r"[A-Za-z0-9_.:/-]{4,}")


def load_generic_terms(path: Optional[str] = None) -> Set[str]:
  """Loads lower-cased generic engineering terms from `generic_terms.txt`."""
  target = path or DEFAULT_GENERIC_TERMS_PATH
  terms: Set[str] = set(STOPWORDS)
  if os.path.isfile(target):
    with open(target, "r", encoding="utf-8") as f:
      for raw in f:
        line = raw.split("#", 1)[0].strip().lower()
        if not line:
          continue
        terms.add(line)
        terms.add(line.strip(".:/-_"))
        for m in _SCENARIO_TOKEN_RE.finditer(line):
          tok = m.group(0).strip(".:/-_")
          if len(tok) >= 4:
            terms.add(tok)
  return terms


def _expand_mock_regex_tokens(pat: str) -> str:
  """Expands simple regex alternations and strips escapes for 1-gram scanning."""
  s = re.sub(r"\(\?[a-zA-Z]+\)", " ", pat or "")
  s = s.replace(r"\.", ".")
  s = re.sub(r"\\[bBsSdDwW]|[\^$*+?\[\]{}]|\.\*|\.\+", " ", s)

  def _repl(m: re.Match[str]) -> str:
    prefix, alts, suffix = m.group(1), m.group(2), m.group(3)
    return " ".join(f"{prefix}{alt}{suffix}" for alt in alts.split("|"))

  s = re.sub(
      r"([A-Za-z0-9_.:/-]*)\(([A-Za-z0-9_.:/|-]+)\)([A-Za-z0-9_.:/-]*)",
      _repl,
      s,
  )
  return s


def _extract_candidate_1grams(text: str) -> List[str]:
  """Extracts candidate 1-gram tokens (`[A-Za-z0-9_.:/-]{4,}`) from text."""
  out: List[str] = []
  for m in _SCENARIO_TOKEN_RE.finditer(text):
    raw = m.group(0).lower()
    cleaned = raw.strip(".:/-_")
    if len(cleaned) >= 4:
      out.append(cleaned)
      if cleaned.endswith(".internal") and cleaned != "internal":
        out.append(".internal")
    if raw.startswith(".") and len(raw.rstrip(".:/-_")) >= 4:
      out.append(raw.rstrip(".:/-_"))
  return out


def distinctive_scenario_tokens(
    units_or_paths: Iterable[Any],
    generic_terms_path: Optional[str] = None,
    max_scenarios: int = 3,
) -> Dict[str, str]:
  """Collects distinctive 1-gram scenario tokens appearing in <= 3 scenarios.

  Collects runs of `[A-Za-z0-9_.:/-]` of length >= 4 from scenario
  `mocks[].match` regex literals, fixture file paths, fixture file contents,
  and user turns (or unit dicts). Keeps tokens that appear in `<= max_scenarios`
  scenarios and are not in `frameworks/generic_terms.txt` (`ADR 0018` R5).

  Args:
    units_or_paths: Scenario JSONL file paths, scenario dicts, or unit dicts.
    generic_terms_path: Optional override path to `generic_terms.txt`.
    max_scenarios: Maximum scenario document frequency (default 3).

  Returns:
    Mapping of `distinctive_token_lower -> "<scenario_id>:<source>"`.
  """
  generic = load_generic_terms(generic_terms_path)
  scen_df: Dict[str, Set[str]] = collections.defaultdict(set)
  first_src: Dict[str, str] = {}

  def _record(tok: str, sid: str, src: str) -> None:
    tl = tok.lower()
    if (
        len(tl) < 4
        or tl in generic
        or (not tl.startswith(".") and tl.strip(".:/-_") in generic)
    ):
      return
    if tl.isdigit():
      return
    scen_df[tl].add(sid)
    first_src.setdefault(tl, f"{sid}:{src}")

  def _scan_scenario_dict(d: Dict[str, Any]) -> None:
    sid = str(d.get("id", "?"))
    files = (d.get("fixture") or {}).get("files") or {}
    for rel, content in files.items():
      rel_clean = str(rel).strip("./")
      for tok in _extract_candidate_1grams(rel_clean):
        _record(tok, sid, f"fixture:{rel}")
      for tok in _extract_candidate_1grams(str(content)):
        _record(tok, sid, f"fixture:{rel}")
    for mk in d.get("mocks") or []:
      expanded = _expand_mock_regex_tokens(mk.get("match", ""))
      for tok in _extract_candidate_1grams(expanded.replace("\\", " ")):
        _record(tok, sid, f"mock:{mk.get('id')}")
    for si, sess in enumerate(d.get("sessions") or []):
      for ti, turn_text in enumerate(sess.get("turns") or []):
        for tok in _extract_candidate_1grams(str(turn_text)):
          _record(tok, sid, f"turn:s{si}t{ti}")

  for item in units_or_paths:
    if isinstance(item, str):
      if not os.path.exists(item):
        continue
      with open(item, "r", encoding="utf-8") as f:
        for line in f:
          line = line.strip()
          if line:
            _scan_scenario_dict(json.loads(line))
    elif isinstance(item, dict):
      if "sessions" in item or "fixture" in item or "mocks" in item:
        _scan_scenario_dict(item)
      elif "text" in item and item.get("kind") in (
          "turn",
          "fixture",
          "mock",
          None,
      ):
        sid = str(item.get("scenario", "?"))
        where = str(item.get("where", "unit"))
        for tok in _extract_candidate_1grams(str(item.get("text", ""))):
          _record(tok, sid, where)

  return {
      tok: first_src[tok]
      for tok, sids in sorted(scen_df.items())
      if 1 <= len(sids) <= max_scenarios
  }


def scenario_distinctive_tokens_v2(
    paths: Iterable[str],
    generic_terms_path: Optional[str] = None,
) -> Dict[str, str]:
  """Alias for `distinctive_scenario_tokens` over v2 scenario JSONL paths."""
  return distinctive_scenario_tokens(
      paths, generic_terms_path=generic_terms_path
  )


def pack_texts_legacy(path: str) -> Dict[str, Dict[str, Any]]:
  """v1 frameworks.json: system_instruction plus inline context files."""
  with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
  out = {}
  for key, v in data.items():
    parts = [v.get("system_instruction", "")]
    ctx = v.get("context_files")
    if isinstance(ctx, dict):
      parts += [str(x) for x in ctx.values()]
    elif isinstance(ctx, list):
      parts += [json.dumps(x) if not isinstance(x, str) else x for x in ctx]
    out[key] = {"display_name": v.get("name", key), "visibility": "legacy",
                "text": "\n\n".join(parts)}
  return out


# ---------------------------------------------------------------------------
# Audit.
# ---------------------------------------------------------------------------


def audit(
    packs: Dict[str, Dict[str, Any]],
    units: List[Dict[str, str]],
    top_k: int = 10,
    distinctive_1grams: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
  """Computes per-framework overlap statistics.

  Args:
    packs: key -> {"display_name", "visibility", "text", optional
      "always_on_text"}.
    units: Scenario text units.
    top_k: Number of top matches to report per framework.
    distinctive_1grams: Optional mapping of distinctive scenario 1-gram tokens
      to their scenario provenance string (`ADR 0018`).

  Returns:
    JSON-serializable result dict.
  """
  unit_grams = [{n: _text_ngrams(u["text"], n) for n in (3, 4)} for u in units]
  pack_grams = {k: {n: _text_ngrams(p["text"], n) for n in (3, 4)}
                for k, p in packs.items()}
  # How many packs contain each n-gram, for the "exclusive" column.
  pack_df: Dict[int, collections.Counter] = {3: collections.Counter(),
                                             4: collections.Counter()}
  for g in pack_grams.values():
    for n in (3, 4):
      pack_df[n].update(g[n])
  kinds = collections.Counter(u["kind"] for u in units)
  results: Dict[str, Any] = {
      "units": len(units),
      "units_by_kind": dict(kinds),
      "scenarios": len({u["scenario"] for u in units}),
      "distinctive_1grams": len(distinctive_1grams or {}),
      "frameworks": {},
  }
  for key, p in packs.items():
    pg = pack_grams[key]
    row: Dict[str, Any] = {"display_name": p["display_name"],
                           "visibility": p["visibility"],
                           "pack_chars": len(p["text"])}
    for n in (3, 4):
      shared: Set[Tuple[str, ...]] = set()
      hit_units = collections.Counter()
      gram_units: Dict[Tuple[str, ...], List[int]] = collections.defaultdict(list)
      for i, ug in enumerate(unit_grams):
        inter = ug[n] & pg[n]
        if inter:
          shared |= inter
          hit_units[units[i]["kind"]] += 1
          for g in inter:
            gram_units[g].append(i)
      exclusive = {g for g in shared if pack_df[n][g] == 1}
      row[f"shared_{n}grams"] = len(shared)
      row[f"exclusive_{n}grams"] = len(exclusive)
      row[f"units_with_{n}gram"] = sum(hit_units.values())
      row[f"units_with_{n}gram_by_kind"] = dict(hit_units)
      if n == 3:
        ranked = sorted(gram_units.items(),
                        key=lambda kv: (-len(kv[1]), -(kv[0] in exclusive), kv[0]))
        row["top_matches"] = [
            {"ngram": " ".join(g), "units": len(idx),
             "exclusive": g in exclusive,
             "example": f"{units[idx[0]]['scenario']}:{units[idx[0]]['where']}"}
            for g, idx in ranked[:top_k]
        ]
    scan_text = (
        p.get("always_on_and_skills_text")
        or p.get("always_on_text")
        or p["text"]
    ).lower()
    pack_1gram_set = set(_extract_candidate_1grams(scan_text))
    hits_1g: List[Tuple[str, str]] = []
    if distinctive_1grams and scan_text:
      for tok, src in sorted(distinctive_1grams.items()):
        if tok in pack_1gram_set:
          hits_1g.append((tok, src))
        else:
          pat = r"(?<![a-z0-9_./-])" + re.escape(tok) + r"(?![a-z0-9_./-])"
          if re.search(pat, scan_text):
            hits_1g.append((tok, src))
    row["shared_1grams"] = len(hits_1g)
    row["shared_1gram_tokens"] = [tok for tok, _ in hits_1g]
    row["shared_1gram_matches"] = [
        {"token": tok, "source": src} for tok, src in hits_1g[:top_k]
    ]
    row["rule_1gram_hits"] = len(hits_1g)
    row["rule_1gram_matches"] = row["shared_1gram_matches"]
    results["frameworks"][key] = row
  return results


def to_markdown(res: Dict[str, Any], title: str) -> str:
  kinds = ", ".join(f"{v} {k}s" for k, v in sorted(res["units_by_kind"].items()))
  lines = [
      f"# {title}",
      "",
      f"Scenario units: {res['units']} across {res['scenarios']} scenarios "
      f"({kinds}). N-grams are over stopword-filtered content words, within a "
      "sentence or line. \"Units w/ 3-gram\" counts scenario units sharing at "
      "least one 3-gram with the pack; \"exclusive\" n-grams occur in this pack "
      "and no other pack in the audit.",
      "",
      "| Framework | Pack chars | Shared 1-grams | Shared 3-grams | Exclusive 3-grams | Units w/ 3-gram | Criteria w/ 3-gram | Shared 4-grams | Units w/ 4-gram |",
      "| :-- | --: | --: | --: | --: | --: | --: | --: | --: |",
  ]
  n_crit = res["units_by_kind"].get("criterion", 0)
  for key, r in sorted(res["frameworks"].items(),
                       key=lambda kv: -kv[1]["units_with_3gram"]):
    crit = r["units_with_3gram_by_kind"].get("criterion", 0)
    lines.append(
        f"| {r['display_name']} (`{key}`) | {r['pack_chars']:,} | "
        f"{r.get('shared_1grams', 0)} | "
        f"{r['shared_3grams']} | {r['exclusive_3grams']} | "
        f"{r['units_with_3gram']}/{res['units']} | {crit}/{n_crit} | "
        f"{r['shared_4grams']} | {r['units_with_4gram']}/{res['units']} |")
  lines += ["", "## Top shared 3-grams per framework", ""]
  for key, r in sorted(res["frameworks"].items()):
    if not r["top_matches"]:
      lines.append(f"- **{key}**: none")
      continue
    items = "; ".join(
        f"`{m['ngram']}` x{m['units']}{' (excl.)' if m['exclusive'] else ''} "
        f"[{m['example']}]" for m in r["top_matches"])
    lines.append(f"- **{key}**: {items}")
  lines += ["", "## Shared 1-gram scenario tokens per framework", ""]
  for key, r in sorted(res["frameworks"].items()):
    m1 = r.get("shared_1gram_matches") or []
    if not m1:
      lines.append(f"- **{key}**: none")
      continue
    items = "; ".join(f"`{m['token']}` [{m['source']}]" for m in m1)
    lines.append(f"- **{key}** ({r.get('shared_1grams', 0)}): {items}")
  lines += [
      "",
      "Interpretation: high overlap with judge criteria or check descriptions "
      "means a pack may contain the expected answer in the scenario's own "
      "words. Large packs share more generic engineering phrases by chance; "
      "compare exclusive n-grams and inspect the top matches before drawing "
      "conclusions.",
      "",
  ]
  return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
  parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
  parser.add_argument("--tasks", nargs="*",
                      help="scenario jsonl files (default: tasks/*.jsonl)")
  parser.add_argument("--registry", action="append",
                      help="registry json(s) (default: public + internal)")
  parser.add_argument("--cache-dir", default=fw.PACK_CACHE_DIR)
  parser.add_argument("--no-verify", action="store_true",
                      help="skip lockfile verification of packs")
  parser.add_argument("--public-only", action="store_true",
                      help="audit only the public registry")
  parser.add_argument("--legacy", action="store_true",
                      help="audit legacy_v1 scenarios vs legacy_v1 prompts")
  parser.add_argument("--legacy-scenarios",
                      default=os.path.join(BASE_DIR, "legacy_v1", "scenarios.jsonl"))
  parser.add_argument("--legacy-frameworks",
                      default=os.path.join(BASE_DIR, "legacy_v1", "configs",
                                           "frameworks.json"))
  parser.add_argument("--top", type=int, default=10)
  parser.add_argument("--out-json")
  parser.add_argument("--out-md")
  args = parser.parse_args(argv)

  if args.legacy:
    units = scenario_units_legacy(args.legacy_scenarios)
    packs = pack_texts_legacy(args.legacy_frameworks)
    dist_1grams: Dict[str, str] = {}
    title = "Leakage audit (legacy v1 prompts vs v1 scenarios)"
  else:
    paths = args.tasks or sorted(glob.glob(os.path.join(BASE_DIR, "tasks", "*.jsonl")))
    if not paths:
      print("no scenario files found", file=sys.stderr)
      return 1
    units = scenario_units_v2(paths)
    dist_1grams = scenario_distinctive_tokens_v2(paths)
    regs = args.registry or (
        [os.path.join(fw.FRAMEWORKS_DIR, "registry.json")] if args.public_only
        else fw.default_registry_paths())
    packs = pack_texts_v2(regs, args.cache_dir, verify=not args.no_verify)
    title = "Leakage audit (v2 packs vs v2 scenarios)"
  res = audit(packs, units, args.top, distinctive_1grams=dist_1grams)
  res["inputs"] = {"legacy": args.legacy}
  md = to_markdown(res, title)
  if args.out_json:
    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
      json.dump(res, f, indent=2)
  if args.out_md:
    os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
    with open(args.out_md, "w", encoding="utf-8") as f:
      f.write(md)
  print(md)
  return 0


if __name__ == "__main__":
  sys.exit(main())
