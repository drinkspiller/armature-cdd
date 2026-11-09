"""Markdown report for the CDD/SDD benchmark v2 (internal and public variants).

The report shows tiers, never ranks, and never merges the outcome score and the
judge score into a composite. The outcome score (deterministic checks) is the
headline; the judge score is shown beside it.

Entry points:
  render(stats, manifest, visibility) -> str
  build(rollouts, scenarios, manifest, visibility, n_boot) -> str
    Convenience: computes stats on the correct visibility subset and renders.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional

from bench import judge as judge_lib
from bench import schema
from bench import stats as stats_lib

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIBRATION_RESULT = os.path.join(_BASE, "calibration", "agreement.json")


def _f(x: Optional[float], nd: int = 3) -> str:
  return "n/a" if x is None else f"{x:.{nd}f}"


def _pct(x: Optional[float]) -> str:
  return "n/a" if x is None else f"{100 * x:.1f}%"


def _ci(e: Dict[str, Any]) -> str:
  return f"{_f(e.get('mean'))} [{_f(e.get('ci_lo'))}, {_f(e.get('ci_hi'))}]"


def _diff(d: Dict[str, Any]) -> str:
  if not d or d.get("mean") is None:
    return "n/a"
  return (f"{d['mean']:+.3f} [{d['ci_lo']:+.3f}, {d['ci_hi']:+.3f}]")


def _fw_name(manifest: Dict[str, Any], key: str) -> str:
  for fw in manifest.get("frameworks", []) or []:
    if isinstance(fw, dict) and fw.get("key") == key:
      return fw.get("display_name") or key
  return key


def _public_keys(manifest: Dict[str, Any]) -> Optional[set]:
  fws = manifest.get("frameworks", []) or []
  if fws and all(isinstance(f, dict) for f in fws):
    return {f["key"] for f in fws if f.get("visibility") == "public"}
  return None


def build(rollouts: Iterable[Any], scenarios: Iterable[schema.Scenario],
          manifest: Dict[str, Any], visibility: str = "internal",
          n_boot: int = stats_lib.N_BOOT) -> str:
  """Computes stats on the visibility subset, then renders."""
  st = stats_lib.compute(rollouts, scenarios, visibility=visibility,
                         n_boot=n_boot)
  return render(st, manifest, visibility)


def render(stats: Dict[str, Any], manifest: Dict[str, Any],
           visibility: str = "internal") -> str:
  """Renders the markdown report.

  Args:
    stats: Output of stats.compute(). For visibility="public" it must have been
      computed with visibility="public", so that internal frameworks never
      influenced tiers or competitor choice.
    manifest: results/<run_id>/manifest.json contents.
    visibility: "internal" or "public".

  Returns:
    Markdown text.

  Raises:
    ValueError: public report requested from internal-visibility stats, or the
      stats contain a framework not marked public in the manifest.
  """
  if visibility == "public":
    if not manifest.get("publish"):
      raise ValueError("public report requires a --publish run "
                       "(manifest.publish is not true)")
    if stats.get("visibility") != "public":
      raise ValueError("public report needs stats.compute(..., "
                       "visibility='public')")
    pub = _public_keys(manifest)
    if pub is not None:
      leaked = [f for f in stats["frameworks"] if f not in pub]
      if leaked:
        raise ValueError(f"internal frameworks in public stats: {leaked}")
  fws: List[str] = list(stats["frameworks"])
  name = lambda k: _fw_name(manifest, k)  # pylint: disable=unnecessary-lambda-assignment
  pm = stats["primary_metric"]
  lines: List[str] = []
  add = lines.append
  invalid = stats["harness"]["invalid"]

  title = "CDD/SDD Benchmark v2 Report"
  if visibility == "public":
    title += " (public subset)"
  add(f"# {title}\n")
  if not manifest.get("publish"):
    add("> [!CAUTION]\n> **EXPLORATORY: not a --publish run.** Frameworks, "
        "scenarios, seeds, or models may be a subset of the full matrix. "
        "These numbers are not citable and must not be compared with a "
        "published run.\n")
  if invalid:
    add("> [!CAUTION]\n> **INVALID RUN.** At least one framework x model cell "
        "has more than 5% harness errors. Do not publish or cite these "
        "numbers.\n")
  j_hdr = stats.get("judge", {}) or {}
  v_cast = j_hdr.get("votes_cast", {}) or {}
  v_inv = j_hdr.get("votes_invalid", {}) or {}
  sampled_crit = int(j_hdr.get("criteria_total", 0) or 0) - int(
      j_hdr.get("criteria_not_sampled", 0) or 0
  )
  degraded_judges: List[str] = []
  for pj in judge_lib.PRIMARY_JUDGES:
    cast_n = int(v_cast.get(pj, 0) or 0)
    inv_n = int(v_inv.get(pj, 0) or 0)
    if cast_n > 0 and (inv_n / cast_n) > 0.05:
      degraded_judges.append(
          f"`{pj}` ({inv_n}/{cast_n} invalid, {100.0 * inv_n / cast_n:.1f}%)"
      )
      add(
          f"> [!WARNING]\n> **Single-judge run.** {pj} returned invalid votes "
          f"on {inv_n} of {cast_n} criteria; judge scores are not panel "
          "scores.\n"
      )
    elif sampled_crit > 0 and cast_n == 0 and v_cast:
      degraded_judges.append(f"`{pj}` (0/{sampled_crit} votes cast)")
      add(
          f"> [!WARNING]\n> **Single-judge run.** {pj} returned invalid votes "
          f"on {sampled_crit} of {sampled_crit} criteria; judge scores are not "
          "panel scores.\n"
      )
  if degraded_judges:
    add(
        "> [!WARNING]\n> **INCOMPLETE PRIMARY JUDGE PANEL.** Primary judge(s) "
        + ", ".join(degraded_judges)
        + " exceeded the 5% INVALID vote threshold. Secondary judge scores in "
        "this report are degraded or single-judge (`ADR 0018`).\n"
    )

  # ---- Executive summary.
  mv = stats["model_views"]
  sc = stats["scenario_counts"]
  rc = stats["rollout_counts"]
  models = stats["models"]
  m0 = mv[0] if mv else (models[0] if models else "n/a")
  m0_label = "All target models pooled" if m0 == stats_lib.POOLED_MODEL else m0
  cell0 = stats.get("cells", {}).get(m0, {}).get("all", {})
  tiers0 = cell0.get("tiers", {}).get(pm, {})
  order0 = sorted(
      fws,
      key=lambda f: (
          tiers0.get(f, 99),
          -((cell0.get("frameworks", {}).get(f, {}).get(pm, {}).get("mean"))
            or -1),
          f,
      ),
  )
  feat_fw = order0[0] if order0 else (fws[0] if fws else "")
  add("## Executive summary\n")
  add(
      f"- **Scope & Primary Metric (`Outcome score`):** Evaluated "
      f"**{len(fws)}** frameworks across **{rc['ok']:,} / {rc['total']:,}** "
      f"scored sandbox rollouts ({sc.get('core', 0)} `core` + "
      f"{sc.get('heldout', 0)} `held-out` scenarios x {len(stats['seeds'])} "
      f"seeds on {', '.join(f'`{m}`' for m in models)}; "
      f"{rc['harness_error']} harness errors). The primary metric is the "
      "**Outcome score** (`0.000`–`1.000`, where `0.010` = `1.0 percentage "
      "point` / `pp`), measuring the fraction of deterministic sandbox checks "
      "passed."
  )
  if order0:
    t1_fws = [f for f in order0 if tiers0.get(f) == 1]
    if t1_fws:
      top_e = cell0["frameworks"][feat_fw][pm]
      t1_summary = ", ".join(
          f"**{name(f)}** (`{_ci(cell0['frameworks'][f][pm])}`)" for f in t1_fws
      )
      add(
          f"- **Tier 1 Leaders ({m0_label}):** {t1_summary} placed in "
          "**Equivalence Tier 1** (statistically indistinguishable from the "
          f"top point estimate **{name(feat_fw)}** at `{_ci(top_e)}`)."
      )
  if "armature_oss_dev" in fws and "armature_oss" in fws and cell0:
    dev_e = cell0["frameworks"]["armature_oss_dev"][pm]
    base_e = cell0["frameworks"]["armature_oss"][pm]
    dev_m = dev_e.get("mean")
    base_m = base_e.get("mean")
    if dev_m is not None and base_m is not None:
      delta_v = dev_m - base_m
      pil0 = stats.get("pillars", {}).get(m0, {})
      pil_deltas = []
      for p_name in schema.PILLARS:
        if p_name in pil0:
          pm_dev = (
              pil0[p_name]["frameworks"]
              .get("armature_oss_dev", {})
              .get(pm, {})
              .get("mean")
          )
          pm_base = (
              pil0[p_name]["frameworks"]
              .get("armature_oss", {})
              .get(pm, {})
              .get("mean")
          )
          if pm_dev is not None and pm_base is not None:
            pil_deltas.append((pm_dev - pm_base, p_name, pm_base, pm_dev))
      pil_deltas.sort(reverse=True)
      top_pil_str = ", ".join(
          f"`{p_name}` (`{100 * d:+.1f} pp`, `{_f(b)}` -> `{_f(dv)}`)"
          for d, p_name, b, dv in pil_deltas[:3]
      )
      pil_clause = f", driven by {top_pil_str}" if top_pil_str else ""
      add(
          f"- **Version-over-Version Progression ({name('armature_oss_dev')} "
          f"vs. {name('armature_oss')}):** Outcome score increased from "
          f"`{_ci(base_e)}` to `{_ci(dev_e)}` (**`{delta_v:+.3f}` / "
          f"`{100 * delta_v:+.1f} pp`**){pil_clause}."
      )
  hs0 = stats.get("heldout_shift", {}).get(m0, {})
  if hs0 and order0:
    both_t1 = [
        name(f)
        for f in order0
        if hs0.get(f, {}).get("core_tier") == 1
        and hs0.get(f, {}).get("heldout_tier") == 1
    ]
    if both_t1:
      add(
          "- **Core vs. Held-Out Generalization:** "
          + ", ".join(f"**{n}**" for n in both_t1)
          + " retained **Tier 1** status on both the `core` development set "
          "and the independently authored `held-out` generalization set."
      )
  pk_hdr = j_hdr.get("primary_kappa")
  if degraded_judges:
    pk_clause = (
        f" (on the `{pk_hdr['n_items']}` completed cross-family items, "
        f"inter-judge Cohen's kappa was `{_f(pk_hdr['kappa'])}` with "
        f"`{_pct(pk_hdr['raw_agreement'])}` raw agreement)"
        if pk_hdr
        else ""
    )
    add(
        "- **Judge Panel Completeness:** Deterministic **Outcome scores** are "
        f"100% complete (`{rc['ok']:,} / {rc['total']:,}` rollouts). The "
        "secondary qualitative **Judge score** column is partial (`n/a` where "
        "fewer than 50% of sampled scenarios received two valid cross-family "
        f"votes) because {', '.join(degraded_judges)} exceeded the 5% invalid "
        f"vote threshold{pk_clause}."
    )
  elif pk_hdr:
    add(
        "- **Judge Panel Completeness:** Both primary cross-family judges "
        f"completed voting (`{pk_hdr['n_items']}` paired items, inter-judge "
        f"Cohen's kappa `{_f(pk_hdr['kappa'])}`, raw agreement "
        f"`{_pct(pk_hdr['raw_agreement'])}`)."
    )
  add("")
  add("### Quick guide: how to read the metrics\n")
  add("| Metric / Term | Plain-language meaning & how to interpret values |")
  add("| :-- | :-- |")
  add(
      "| **Outcome score `[95% CI]`** | **Primary metric.** Fraction of "
      "deterministic sandbox checks passed (`0.827` = `82.7%`; `0.010` = "
      "`1.0 percentage point` / `pp`). The `[lo, hi]` interval is the 95% "
      "two-level cluster-bootstrap confidence range across scenarios and "
      "seeds. |"
  )
  add(
      "| **Tier (`1`, `2`, `3`)** | Statistical equivalence tier. Frameworks "
      "in **Tier 1** have a paired difference against the top point estimate "
      "whose 95% CI includes `0.000` (statistically indistinguishable on this "
      "scenario set). |"
  )
  add(
      "| **Paired diff vs. closest competitor** | Head-to-head Outcome score "
      "difference (`Framework - Competitor`) evaluated on the **exact same "
      "scenario and seed**. A 95% CI that excludes `0.000` indicates a "
      "statistically significant gap. |"
  )
  add(
      "| **Core vs. Held-out (`Delta`)** | `Core` is the development scenario "
      "set; `Held-out` is the sealed generalization set written by an "
      "independent author to test for overfitting. `Delta = Held-out - Core`. |"
  )
  add(
      "| **`SD across seeds` / `Within-scenario SD`** | Standard Deviation "
      "(`SD`) across random seeds. `SD across seeds` measures how much a "
      "framework's overall 60-scenario average wobbles between full runs "
      "(`< 0.035` / `< 3.5 pp` indicates high stability); `Within-scenario SD` "
      "measures per-scenario variation before averaging. |"
  )
  add(
      "| **Judge score `[95% CI]`** | **Secondary metric.** Blinded "
      "qualitative rubric score from a 2-family LLM panel (Google Gemini + "
      "Anthropic Claude, with Google Gemma tiebreak). Never combined with "
      "Outcome score; shown as `n/a` when fewer than 50% of sampled scenarios "
      "have two valid primary votes. |"
  )
  add("")

  # ---- Run identity.
  add("## Run identity\n")
  add("| Field | Value |\n| :-- | :-- |")
  add(f"| Run id | `{manifest.get('run_id', 'n/a')}` |")
  add(f"| Config hash | `{manifest.get('config_hash', 'n/a')}` |")
  add(f"| Target models | {', '.join(f'`{m}`' for m in stats['models'])} |")
  fam = lambda m: judge_lib.JUDGE_SPECS.get(m, {}).get("family", "?")  # pylint: disable=unnecessary-lambda-assignment
  add(f"| Judge models | `{judge_lib.PRIMARY_JUDGES[0]}` "
      f"({fam(judge_lib.PRIMARY_JUDGES[0])}), "
      f"`{judge_lib.PRIMARY_JUDGES[1]}` ({fam(judge_lib.PRIMARY_JUDGES[1])}) "
      f"(primary); `{judge_lib.TIEBREAK_JUDGE}` "
      f"({fam(judge_lib.TIEBREAK_JUDGE)}, tiebreak only on disagreement) |")
  seen = sorted(stats.get("judge", {}).get("votes_cast", {}))
  if seen and set(seen) - set(judge_lib.ALL_JUDGES):
    add(f"| Judges found in data | {', '.join(f'`{m}`' for m in seen)} |")
  add(f"| Seeds | {', '.join(str(s) for s in stats['seeds'])} |")
  sc = stats["scenario_counts"]
  add(f"| Scenarios | core {sc.get('core', 0)}, held-out "
      f"{sc.get('heldout', 0)} |")
  rc = stats["rollout_counts"]
  add(f"| Rollouts | {rc['total']} total, {rc['ok']} scored, "
      f"{rc['harness_error']} harness errors (excluded) |")
  add(f"| Bootstrap | {stats['n_boot']:,} two-level cluster resamples "
      f"(scenarios, then seeds), seed {stats['bootstrap_seed']} |")
  add("")
  add("**Framework packs**\n")
  add("| Framework | Visibility | Source | Ref |\n| :-- | :-- | :-- | :-- |")
  for fw in manifest.get("frameworks", []) or []:
    if not isinstance(fw, dict) or fw.get("key") not in fws:
      continue
    src = fw.get("source", {}) or {}
    lk = fw.get("lock", {}) or {}
    if src.get("type") == "local_path":
      loc = f"local_path (`${src.get('env', 'ENV')}`)"
      gh = fw.get("git_head") or lk.get("git_head") or "n/a"
      df = (
          fw.get("dirty_files")
          if fw.get("dirty_files") is not None
          else lk.get("dirty_files")
      )
      ref_col = (
          f"`git_head={gh}`, `dirty_files={df if df is not None else 'n/a'}`"
      )
    else:
      loc = src.get("repo") or src.get("path") or "n/a"
      if fw.get("visibility") != "public":
        loc = "(internal)"
      ref_col = f"`{src.get('ref') or fw.get('ref') or 'n/a'}`"
    add(f"| {fw.get('display_name', fw['key'])} | {fw.get('visibility')} | "
        f"{loc} | {ref_col} |")
  add("")

  # ---- Headline tiers.
  mv = stats["model_views"]
  add("## Headline: outcome score tiers\n")
  add("The outcome score is the fraction of deterministic checks passed (what "
      "the agent did in the sandbox). Tiers group frameworks whose paired "
      "difference against the tier's top framework has a 95% CI that "
      "includes 0. Frameworks in the same tier are statistically "
      "indistinguishable on this benchmark; order within a tier is by point "
      "estimate and is not a ranking.\n")
  for m in mv:
    cell = stats["cells"][m]["all"]
    tiers = cell.get("tiers", {}).get(pm, {})
    label = "All target models pooled" if m == stats_lib.POOLED_MODEL else m
    add(f"### {label} (core + held-out)\n")
    add("| Tier | Framework | Outcome score [95% CI] | Judge score [95% CI] "
        "| Paired diff vs closest competitor (outcome) | Scenarios w/ data |")
    add("| :-: | :-- | :-- | :-- | :-- | :-: |")
    order = sorted(
        fws, key=lambda f: (tiers.get(f, 99),
                            -(cell["frameworks"][f][pm]["mean"] or -1), f))
    for fw in order:
      e = cell["frameworks"][fw]
      cl = cell.get("closest", {}).get(pm, {}).get(fw)
      cl_s = (f"{_diff(cl)} vs {name(cl['competitor'])}" if cl else "n/a")
      nsd = e.get("n_scenarios_with_data", "?")
      ns = cell.get("n_scenarios", "?")
      nsd_s = f"{nsd}/{ns}" + (" (!)" if nsd != ns else "")
      add(f"| {tiers.get(fw, '-')} | {name(fw)} | {_ci(e[pm])} | "
          f"{_ci(e['judge'])} | {cl_s} | {nsd_s} |")
    add("")
    if order:
      top_fw = order[0]
      top_e = cell["frameworks"][top_fw][pm]
      top_cl = cell.get("closest", {}).get(pm, {}).get(top_fw)
      cl_clause = (
          f", with a `{_diff(top_cl)}` paired difference against "
          f"{name(top_cl['competitor'])}"
          if top_cl
          else ""
      )
      add(
          f"**How to read it:** {name(top_fw)} passed {_pct(top_e.get('mean'))} "
          f"of all deterministic sandbox checks (Outcome score "
          f"`{_ci(top_e)}`{cl_clause}). Because the 95% CI on the paired "
          "difference between Tier 1 frameworks crosses `0.000`, Tier 1 "
          "entries are statistically indistinguishable on this scenario set, "
          "while Tier 2+ entries scored significantly lower.\n"
      )
    add("(!) marks a framework missing scored rollouts for some scenarios. "
        "Its paired differences then rest on fewer scenarios than its "
        "competitors'.\n")

  add("### Armature Distribution Note\n")
  if visibility != "public":
    add("The internal monorepo edition and "
        "`Armature (OSS)` (`drinkspiller/armature-cdd`) share the same core "
        "protocol (`armature_protocol.md` and `skills/arm-*/SKILL.md`) with "
        "different always-on rule payloads: the internal edition also "
        "injects two enterprise host adapter rule files on every "
        "API call. Their small Outcome Score delta reflects token overhead "
        "and UX-adapter friction from injecting environment-specific host "
        "rules into a generic sandbox.\n")
  else:
    add("`Armature (OSS)` (`drinkspiller/armature-cdd`) is the cross-platform "
        "public distribution of the core Armature protocol. Host-specific "
        "enterprise environment rules are packaged separately outside the "
        "public distribution so generic sandbox evaluations measure the core "
        "protocol without host-adapter token overhead.\n")

  # ---- Core vs held-out.
  add("## Core vs held-out\n")
  add("Held-out scenarios were written by a separate author who did not read "
      "the core scenarios or any framework pack. That author's agent host "
      "did, however, load two Armature rule files as always-on context (see "
      "Limitations), so held-out is independent of the core set and of "
      "every framework except Armature. A lead that shrinks on held-out "
      "suggests the core set favors that framework's dialect.\n")
  for m in mv:
    hs = stats["heldout_shift"][m]
    label = "All models pooled" if m == stats_lib.POOLED_MODEL else m
    add(f"### {label}\n")
    add("| Framework | Core outcome [CI] | Held-out outcome [CI] | Delta | "
        "Core tier | Held-out tier |")
    add("| :-- | :-- | :-- | :-: | :-: | :-: |")
    for fw in fws:
      c = stats["cells"][m]["core"]["frameworks"][fw][pm]
      h = stats["cells"][m]["heldout"]["frameworks"][fw][pm]
      s = hs[fw]
      d = "n/a" if s["delta"] is None else f"{s['delta']:+.3f}"
      add(f"| {name(fw)} | {_ci(c)} | {_ci(h)} | {d} | "
          f"{s['core_tier'] or '-'} | {s['heldout_tier'] or '-'} |")
    callouts = []
    for fw in fws:
      s = hs[fw]
      if s["core_tier"] == 1 and s["core_lead"] is not None:
        if (s["heldout_lead"] is None or s["heldout_lead"] < s["core_lead"]
            or (s["heldout_tier"] or 99) > 1):
          callouts.append(
              f"- **{name(fw)}**: lead over {name(s['competitor'])} is "
              f"{s['core_lead']:+.3f} on core but "
              f"{_f(s['heldout_lead'])} on held-out "
              f"(held-out tier {s['heldout_tier'] or '-'}). The lead shrinks "
              f"on held-out.")
    if callouts:
      add("")
      add("> [!WARNING]\n> Lead shrinkage on held-out:\n>")
      for c in callouts:
        add("> " + c)
    add("")
    if feat_fw and feat_fw in hs:
      c_feat = stats["cells"][m]["core"]["frameworks"][feat_fw][pm]
      h_feat = stats["cells"][m]["heldout"]["frameworks"][feat_fw][pm]
      s_feat = hs[feat_fw]
      d_feat = (
          "n/a" if s_feat["delta"] is None else f"{s_feat['delta']:+.3f}"
      )
      add(
          f"**How to read it:** Compare `Core tier` against `Held-out tier` "
          f"and inspect `Delta` (`Held-out - Core`). For example, "
          f"{name(feat_fw)} scored `{_f(c_feat.get('mean'))}` (`Core tier "
          f"{s_feat['core_tier'] or '-'}`) on the 30-scenario core set and "
          f"`{_f(h_feat.get('mean'))}` (`Held-out tier "
          f"{s_feat['heldout_tier'] or '-'}`) on the 30-scenario sealed "
          f"held-out set (`Delta = {d_feat}`). A negative `Delta` across most "
          "frameworks reflects harder held-out tasks, whereas dropping out of "
          "`Tier 1` on `Held-out` signals potential overfitting to core task "
          "patterns.\n"
      )

  # ---- Per-pillar.
  add("## Per-pillar outcome score (core + held-out)\n")
  for m in mv:
    label = "All models pooled" if m == stats_lib.POOLED_MODEL else m
    pil = stats["pillars"].get(m, {})
    if not pil:
      continue
    add(f"### {label}\n")
    ps = [p for p in schema.PILLARS if p in pil]
    add("| Framework | " + " | ".join(ps) + " |")
    add("| :-- |" + " :-- |" * len(ps))
    for fw in fws:
      cells = [_ci(pil[p]["frameworks"][fw][pm]) for p in ps]
      add(f"| {name(fw)} | " + " | ".join(cells) + " |")
    add("")
    add("Pillar CIs are wide by construction (about 12 scenarios per pillar); "
        "read them as directional.\n")
    add(
        "**How to read it:** Each column averages roughly 12 scenarios "
        "targeting one engineering capability: `spec_gating` (clarifying "
        "requirements before writing code), `surgical_velocity` (fast-pathing "
        "small bug fixes without ceremony), `drift_governance` (catching "
        "contradictions against existing ADRs or glossary terms), "
        "`state_safety` (halting before destructive operations), and "
        "`context_continuity` (resuming draft specs across sessions). Read "
        "across a row to see a framework's trade-off profile—for instance, "
        "whether heavy documentation ceremony boosts `drift_governance` at "
        "the cost of `surgical_velocity`.\n"
    )

  # ---- Variance.
  add("## Run-to-run variance and cross-model swing\n")
  add("SD across seeds = standard deviation of the per-seed framework outcome "
      "score (mean over scenarios). Within-scenario SD = mean over scenarios "
      "of the SD of that scenario's outcome across seeds. Swing = max minus "
      "min outcome score across target models.\n")
  models = stats["models"]
  hdr = "| Framework | " + " | ".join(
      f"SD across seeds ({m}) | Within-scenario SD ({m})" for m in models)
  add(hdr + " | Cross-model swing | Tier by model |")
  add("| :-- |" + " :-: | :-: |" * len(models) + " :-: | :-- |")
  for fw in fws:
    cols = []
    for m in models:
      v = stats["variance"][m]["all"][fw]
      cols += [_f(v["sd_across_seeds"]), _f(v["mean_within_scenario_sd"])]
    sw = stats["swing"]["all"][fw]
    tiers = ", ".join(f"{m}: {t or '-'}" for m, t in
                      sw["tier_by_model"].items())
    add(f"| {name(fw)} | " + " | ".join(cols) + f" | {_f(sw['swing'])} | "
        f"{tiers} |")
  add("")
  if feat_fw and models:
    m_var = models[0]
    v_feat = stats["variance"][m_var]["all"][feat_fw]
    sd_s = v_feat.get("sd_across_seeds")
    sd_w = v_feat.get("mean_within_scenario_sd")
    mean_feat = (
        stats["cells"][m_var]["all"]["frameworks"][feat_fw][pm].get("mean")
    )
    sd_pp = f" (±{100 * sd_s:.1f} pp)" if sd_s is not None else ""
    w_pp = f" (±{100 * sd_w:.1f} pp)" if sd_w is not None else ""
    add(
        f"**How to read it:** {name(feat_fw)} has an `SD across seeds` of "
        f"`{_f(sd_s)}`{sd_pp}, meaning its `{_pct(mean_feat)}` headline score "
        "barely moves from seed to seed. Values under `0.035` (`3.5 pp`) "
        "indicate high run-to-run stability. `Within-scenario SD` "
        f"(`{_f(sd_w)}`{w_pp}) is naturally larger because individual "
        "scenario outcomes vary more across seeds before averaging out over "
        "the full scenario set.\n"
    )

  # ---- Cost.
  add("## Cost per rollout (mean, scored rollouts only)\n")
  add("Output tokens are visible output only (`candidatesTokenCount`); "
      "thinking tokens and input tokens are reported separately and never "
      "summed into one \"length\" number.\n")
  add("Input tokens include each framework's always-on prompt on every "
      "call, so a large pack shows up here as cost even when it does not "
      "change behavior. Retry columns count tokens billed on discarded "
      "attempts (empty candidates, server errors); they are not part of the "
      "scored usage.\n")
  add("| Framework | Model | n | Input tok | Output tok | Thinking tok | "
      "Cached tok | API calls | Wall-clock s | Retry tok (in/out/think) |")
  add("| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: |")
  for fw in fws:
    for m in models:
      c = stats["cost"][fw][m]
      add(f"| {name(fw)} | {m} | {c['n']} | {_f(c['input_tokens'], 0)} | "
          f"{_f(c['output_tokens'], 0)} | {_f(c['thinking_tokens'], 0)} | "
          f"{_f(c['cached_tokens'], 0)} | {_f(c['api_calls'], 1)} | "
          f"{_f(c['latency_s'], 1)} | "
          f"{_f(c.get('retry_input_tokens'), 0)}/"
          f"{_f(c.get('retry_output_tokens'), 0)}/"
          f"{_f(c.get('retry_thinking_tokens'), 0)} |")
  add("")
  if feat_fw and models:
    c_feat = stats["cost"][feat_fw][models[0]]
    in_tok = c_feat.get("input_tokens") or 0
    ca_tok = c_feat.get("cached_tokens") or 0
    cache_pct = _pct(ca_tok / in_tok) if in_tok > 0 else "n/a"
    add(
        f"**How to read it:** `Input tok` is the cumulative prompt tokens sent "
        f"across all API turns in an average rollout (for {name(feat_fw)}, "
        f"`{_f(c_feat.get('input_tokens'), 0)}` input tokens across "
        f"`{_f(c_feat.get('api_calls'), 1)}` API calls, with "
        f"`{_f(c_feat.get('cached_tokens'), 0)}` tokens or `{cache_pct}` "
        "served from prompt cache). `Output tok` "
        f"(`{_f(c_feat.get('output_tokens'), 0)}`) counts visible replies and "
        "tool arguments, `Thinking tok` "
        f"(`{_f(c_feat.get('thinking_tokens'), 0)}`) counts internal "
        "reasoning tokens, and `Wall-clock s` "
        f"(`{_f(c_feat.get('latency_s'), 1)}s`) is the mean duration per "
        "rollout.\n"
    )

  # ---- Harness errors.
  add("## Harness errors\n")
  retries = manifest.get("harness_error_retries") or {}
  add("Harness-error rollouts are excluded from every score. A cell above 5% "
      "invalidates the run. \"Retried\" counts cells that failed and were "
      "re-run with --retry-harness-errors (replaced records are kept in "
      "rollouts.retried.jsonl); a framework that needs many retries may be "
      "selected toward its easier successes.\n")
  add("| Framework | Model | Errors / total | Rate | Retried | Status "
      "| Kinds |")
  add("| :-- | :-- | :-: | :-: | :-: | :-- | :-- |")
  for fw in fws:
    for m in models:
      h = stats["harness"]["cells"][fw][m]
      status = "**INVALID**" if h["over_threshold"] else "ok"
      kinds = ", ".join(f"{k} x{v}" for k, v in sorted(h["kinds"].items()))
      rt = (retries.get(fw) or {}).get(m, 0) if isinstance(retries, dict) else 0
      add(f"| {name(fw)} | {m} | {h['errors']} / {h['total']} | "
          f"{_pct(h['rate'])} | {rt} | {status} | {kinds or '-'} |")
  add("")
  add(
      "**How to read it:** `0.0%` (`Status: ok`) confirms every scheduled "
      "rollout completed without unhandled API or sandbox crashes. Any cell "
      "exceeding `5.0%` is flagged `**INVALID**` so high crash rates cannot "
      "artificially inflate a framework's score by dropping hard scenarios.\n"
  )

  # ---- Command sources.
  add("## Commands by outcome\n")
  add("How the sandbox handled each `run_command`: `mock` = scenario mock "
      "(canned output), `pack_tool` = the framework's own tooling run for "
      "real, `builtin` = allowlisted tool run for real, `refused` = not "
      "available in the sandbox, `wrap_up_refused` = tool calls made after "
      "the step limit, which the harness declines while it asks for a final "
      "reply (counted apart so they don't inflate `refused`). Many refusals for one framework mean the "
      "sandbox could not run what its pack asked for, which can depress "
      "that framework's score for reasons unrelated to its method.\n")
  srcs = ["mock", "pack_tool", "builtin", "refused", "wrap_up_refused"]
  add("| Framework | Model | " + " | ".join(srcs) +
      " | Refused per rollout |")
  add("| :-- | :-- |" + " --: |" * len(srcs) + " --: |")
  for fw in fws:
    for m in models:
      c = stats.get("commands", {}).get(fw, {}).get(m)
      if not c:
        continue
      add(f"| {name(fw)} | {m} | " +
          " | ".join(str(c["counts"].get(s, 0)) for s in srcs) +
          f" | {_f(c['refused_per_rollout'], 2)} |")
  add("")
  add(
      "**How to read it:** A `Refused per rollout` value below `1.00` means "
      "the framework rarely invoked shell commands missing from the sandbox "
      "allowlist. Higher refusal rates (`> 2.00`) indicate a framework's "
      "prompts asked for external CLIs not provisioned in the test sandbox.\n"
  )

  # ---- Turn endings.
  add("## How turns ended\n")
  add("Share of user turns that ended with a text reply, an `ask_user` call, "
      "the per-turn step limit (`max_steps`, after which the harness forces "
      "one final text reply), or a context-length overflow. A high max_steps "
      "rate means the framework's protocol is step-hungry, which is a real "
      "cost, and those turns are scored as they are.\n")
  add("| Framework | Model | Turns | text | ask_user | max_steps | "
      "context_overflow | max_steps rate |")
  add("| :-- | :-- | --: | --: | --: | --: | --: | --: |")
  for fw in fws:
    for m in models:
      te = stats.get("turn_endings", {}).get(fw, {}).get(m)
      if not te:
        continue
      c = te["counts"]
      add(f"| {name(fw)} | {m} | {te['n_turns']} | {c.get('text', 0)} | "
          f"{c.get('ask_user', 0)} | {c.get('max_steps', 0)} | "
          f"{c.get('context_overflow', 0)} | {_pct(te['max_steps_rate'])} |")
  add("")
  add(
      "**How to read it:** Healthy protocols end turns via `text` (delivering "
      "the solution) or `ask_user` (pausing at a decision or safety gate), "
      "keeping `max_steps rate` under `5.0%`. High `max_steps rate` values "
      "(`> 10%`) indicate the agent spent its entire 25-step turn budget on "
      "ceremony or exploration before being forced to wrap up.\n"
  )

  # ---- Judge.
  j = stats["judge"]
  add("## Judge reliability\n")
  add(f"- Criteria judged: {j['criteria_total']}; not in the "
      f"`{j.get('subsampled_judge', '?')}` subsample (one vote, so no score): "
      f"{j.get('criteria_not_sampled', 0)}; excluded for invalid votes "
      f"(fewer than 2 valid): {j['criteria_excluded']}; tiebreaks: "
      f"{j['tiebreaks']}.")
  if j.get("criteria_not_sampled"):
    add(f"- `{j.get('subsampled_judge')}` judged a deterministic sample of "
        "(scenario, seed) cells. The sample is the same for every framework "
        "and model, and the judge score uses only those cells. The other "
        "primary judge voted on every criterion.")
  if visibility == "public":
    add("- The public code release ships Gemini REST judges only. "
        "Reproducing the cross-family (Claude) judge requires Anthropic API "
        "access, which the public release does not include.")
  for m, n in sorted(j["votes_cast"].items()):
    add(f"- `{m}`: {n} votes, {j['votes_invalid'].get(m, 0)} invalid.")
  pk = j.get("primary_kappa")
  if pk:
    add(f"- Inter-judge Cohen's kappa (primary pair): {_f(pk['kappa'])} "
        f"[{_f(pk['ci_lo'])}, {_f(pk['ci_hi'])}] over {pk['n_items']} items "
        f"in {pk['n_clusters']} scenario clusters; raw agreement "
        f"{_pct(pk['raw_agreement'])}.")
  else:
    add("- Inter-judge kappa: not available (no items with two valid "
        "primary votes).")
  calib = _load_calibration(manifest.get("run_id"))
  if calib:
    labelers = ", ".join(calib.get("labelers", [])) or "human/model"
    add(f"- Calibration (judge vs reference labels [{labelers}], "
        f"{calib.get('n_items_labeled')} items from run(s) "
        f"{', '.join(calib.get('run_ids', [])) or 'n/a'}):")
    for k, v in sorted(calib.get("per_judge", {}).items()):
      add(f"  - `{k}`: kappa {_f(v.get('kappa'))} [{_f(v.get('ci_lo'))}, "
          f"{_f(v.get('ci_hi'))}], weighted_kappa "
          f"{_f(v.get('weighted_kappa'))}, n={v.get('n_items')}")
  else:
    add("- Human calibration: **none yet.** Judge accuracy against human "
        "labels is unknown.")
  add("")
  add(
      "**How to read it:** Cohen's kappa measures agreement between the two "
      "primary judges (Google Gemini and Anthropic Claude) beyond chance "
      "(`0.00` = chance agreement, `> 0.60` = substantial, `> 0.80` = "
      "near-perfect). Under `ADR 0018`, any criterion missing a valid vote "
      "from either primary judge is excluded rather than backfilled with a "
      "single-family score.\n"
  )

  # ---- Leakage audit.
  run_id = manifest.get("run_id")
  leak = _load_leakage(run_id) if run_id else None
  add("## Leakage audit\n")
  if leak is None:
    add("No `leakage.json` found for this run.\n")
  else:
    add(_render_leakage(leak, fws, name))
    add(
        "**How to read it:** `shared_1grams=0, shared_3grams=0, "
        "shared_4grams=0` means zero distinctive single tokens or 3/4-word "
        "phrases from a framework's rules appear inside the benchmark's "
        "deterministic grading regexes, verifying that scores reflect behavior "
        "rather than prompt-to-grader phrase echoing.\n"
    )

  # ---- Limitations.
  add("## Limitations\n")
  rule_files = (
      "the full text of two internal Armature rule files and a path "
      "reference to armature_protocol.md "
      "(listed, never opened by the authors)"
      if visibility != "public" else
      "the full text of two internal Armature rule files and a path "
      "reference to Armature's protocol file")
  judges_used = set(stats.get("judge", {}).get("votes_cast", {}))
  claude_used = (any(("claude" in m or "opus" in m) for m in judges_used)
                 or not judges_used)
  lims = [
      ("Judge accuracy is not human-calibrated." if not calib else
       "Judge accuracy is calibrated on a 100-item human-labeled sample only; "
       "it may not generalize to every pillar or framework."),
  ]
  if claude_used:
    lims += [
        "The judge panel is cross-family (Google Gemini and Anthropic "
        "Claude). The tiebreak judge is Gemma, a Google model from a "
        "different family than Gemini, so disagreements may still resolve "
        "toward Google-family preferences. Target models never judge.",
        "**The Claude Opus 5.5 (Low) judge runs inside an agent-host session "
        "that loads the operator's always-on rules and memory files. Those "
        f"include {rule_files}. "
        "Despite prompt-level instructions to ignore them, residual bias "
        "toward recognizing or favoring Armature patterns cannot be ruled "
        "out. A raw Anthropic API key would remove this risk.**",
        "Claude judge temperature could not be controlled (host default). "
        "Each Claude verdict is voided if its conversation used any tool "
        "other than reading its prompt file and writing its verdict file.",
    ]
  else:
    lims.append("All judge models in this run are Google models (Gemini, "
                "and Gemma if used). Shared training data or style "
                "preferences cannot be ruled out. Target models never judge.")
  if stats.get("judge", {}).get("criteria_not_sampled"):
    lims.append("The Claude judge saw a deterministic subsample of "
                "(scenario, seed) cells, the same for every framework. Judge "
                "scores rest on that subsample only.")
  lims += [
      "**Scenario and held-out authors, and the Claude judge, ran inside "
      f"agent-host sessions that load {rule_files}. Despite instructions "
      "to ignore external "
      "context, scenarios may unconsciously favor context-driven patterns "
      "that Armature handles well. The held-out set is independent of the "
      "core scenarios and of every framework pack except Armature. A future "
      "iteration should author and judge through raw API calls to remove "
      "this vector.**",
      "The scenario and check authors are Claude-family agents, the same "
      "family as the Claude judge, so that judge may favor behaviors its own "
      "family wrote down as correct. The target models are Gemini models.",
      "Blinding replaces framework names, commands, and directory names only. "
      "Distinctive output structure can still reveal a framework to a judge "
      "that knows the upstream repos. This is one reason the judge score is "
      "secondary.",
      "The sandbox mocks ops tools (kubectl, terraform, and similar) with "
      "canned output. Behavior against real infrastructure may differ.",
      "Each framework's mapping from scenario intent to its entry command is "
      "a modeling choice (see frameworks/README.md). Different mappings could "
      "change results.",
      "Scores measure behavior in short scripted conversations with these "
      "target models and seeds. They do not measure long-horizon project "
      "outcomes, and tiers can change with other models.",
      "Per-pillar and per-set results rest on roughly 12 and 30 scenarios "
      "respectively; small differences are not meaningful.",
  ]
  for l in lims:
    add(f"- {l}")
  add("")
  return "\n".join(lines)


def _load_calibration(run_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
  """Returns calibration agreement.json if present and valid."""
  candidates = []
  if run_id:
    candidates.append(
        os.path.join(_BASE, "results", run_id, "calibration_agreement.json")
    )
    candidates.append(
        os.path.join(_BASE, "results", run_id, "calibration", "agreement.json")
    )
  candidates.append(CALIBRATION_RESULT)
  for path in candidates:
    if not os.path.exists(path):
      continue
    try:
      with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    except (OSError, json.JSONDecodeError):
      continue
    if d.get("n_items_labeled") and d.get("per_judge"):
      return d
  return None


def _load_leakage(run_id: str) -> Optional[Any]:
  path = os.path.join(_BASE, "results", run_id, "leakage.json")
  if not os.path.exists(path):
    return None
  try:
    with open(path, "r", encoding="utf-8") as f:
      return json.load(f)
  except (OSError, json.JSONDecodeError):
    return None


def _render_leakage(leak: Any, fws: List[str], name) -> str:
  """Best-effort summary; the leakage schema is owned by leakage_audit.py."""
  rows = []
  per = leak.get("frameworks", leak) if isinstance(leak, dict) else {}
  if isinstance(per, list):
    per = {d.get("framework", d.get("key", "?")): d for d in per
           if isinstance(d, dict)}
  if not isinstance(per, dict):
    return "`leakage.json` present but in an unrecognized format.\n"
  rows.append("| Framework | Summary |\n| :-- | :-- |")
  for fw in fws:
    d = per.get(fw)
    if d is None:
      continue
    if isinstance(d, dict):
      keep = {k: v for k, v in d.items()
              if isinstance(v, (int, float, str)) and k != "framework"}
      summ = ", ".join(f"{k}={v}" for k, v in sorted(keep.items())[:8])
    else:
      summ = str(d)[:200]
    rows.append(f"| {name(fw)} | {summ} |")
  rows.append("\nSee `leakage.json` for top shared n-grams.\n")
  return "\n".join(rows)
