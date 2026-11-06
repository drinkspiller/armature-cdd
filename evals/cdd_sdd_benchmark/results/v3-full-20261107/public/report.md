# CDD/SDD Benchmark v2 Report (public subset)

> [!WARNING]
> **Single-judge run.** opus-5.5-low returned invalid votes on 954 of 1328 criteria; judge scores are not panel scores.

> [!WARNING]
> **INCOMPLETE PRIMARY JUDGE PANEL.** Primary judge(s) `opus-5.5-low` (954/1328 invalid, 71.8%) exceeded the 5% INVALID vote threshold. Secondary judge scores in this report are degraded or single-judge (`ADR 0018`).

## Executive summary

- **Scope & Primary Metric (`Outcome score`):** Evaluated **8** frameworks across **1,440 / 1,440** scored sandbox rollouts (30 `core` + 30 `held-out` scenarios x 3 seeds on `gemini-3.5-flash`; 0 harness errors). The primary metric is the **Outcome score** (`0.000`–`1.000`, where `0.010` = `1.0 percentage point` / `pp`), measuring the fraction of deterministic sandbox checks passed.
- **Tier 1 Leaders (gemini-3.5-flash):** **Armature (OSS, unreleased working tree)** (`0.825 [0.765, 0.884]`), **Wayfinder (mattpocock/skills)** (`0.814 [0.750, 0.874]`), **Cline Memory Bank** (`0.780 [0.719, 0.837]`), **BMAD Method** (`0.767 [0.701, 0.831]`) placed in **Equivalence Tier 1** (statistically indistinguishable from the top point estimate **Armature (OSS, unreleased working tree)** at `0.825 [0.765, 0.884]`).
- **Version-over-Version Progression (Armature (OSS, unreleased working tree) vs. Armature (OSS)):** Outcome score increased from `0.679 [0.602, 0.755]` to `0.825 [0.765, 0.884]` (**`+0.146` / `+14.6 pp`**), driven by `context_continuity` (`+35.1 pp`, `0.399` -> `0.750`), `spec_gating` (`+22.0 pp`, `0.451` -> `0.671`), `state_safety` (`+9.4 pp`, `0.766` -> `0.860`).
- **Core vs. Held-Out Generalization:** **Armature (OSS, unreleased working tree)**, **Wayfinder (mattpocock/skills)** retained **Tier 1** status on both the `core` development set and the independently authored `held-out` generalization set.
- **Judge Panel Completeness:** Deterministic **Outcome scores** are 100% complete (`1,440 / 1,440` rollouts). The secondary qualitative **Judge score** column is partial (`n/a` where fewer than 50% of sampled scenarios received two valid cross-family votes) because `opus-5.5-low` (954/1328 invalid, 71.8%) exceeded the 5% invalid vote threshold (on the `374` completed cross-family items, inter-judge Cohen's kappa was `0.867` with `93.6%` raw agreement).

### Quick guide: how to read the metrics

| Metric / Term | Plain-language meaning & how to interpret values |
| :-- | :-- |
| **Outcome score `[95% CI]`** | **Primary metric.** Fraction of deterministic sandbox checks passed (`0.827` = `82.7%`; `0.010` = `1.0 percentage point` / `pp`). The `[lo, hi]` interval is the 95% two-level cluster-bootstrap confidence range across scenarios and seeds. |
| **Tier (`1`, `2`, `3`)** | Statistical equivalence tier. Frameworks in **Tier 1** have a paired difference against the top point estimate whose 95% CI includes `0.000` (statistically indistinguishable on this scenario set). |
| **Paired diff vs. closest competitor** | Head-to-head Outcome score difference (`Framework - Competitor`) evaluated on the **exact same scenario and seed**. A 95% CI that excludes `0.000` indicates a statistically significant gap. |
| **Core vs. Held-out (`Delta`)** | `Core` is the development scenario set; `Held-out` is the sealed generalization set written by an independent author to test for overfitting. `Delta = Held-out - Core`. |
| **`SD across seeds` / `Within-scenario SD`** | Standard Deviation (`SD`) across random seeds. `SD across seeds` measures how much a framework's overall 60-scenario average wobbles between full runs (`< 0.035` / `< 3.5 pp` indicates high stability); `Within-scenario SD` measures per-scenario variation before averaging. |
| **Judge score `[95% CI]`** | **Secondary metric.** Blinded qualitative rubric score from a 2-family LLM panel (Google Gemini + Anthropic Claude, with Google Gemma tiebreak). Never combined with Outcome score; shown as `n/a` when fewer than 50% of sampled scenarios have two valid primary votes. |

## Run identity

| Field | Value |
| :-- | :-- |
| Run id | `v3-full-20261107` |
| Config hash | `39b7dcdaec5697bbfbfb3a44351524e6331a07223bcdc1a50b0fb502ea0fe960` |
| Target models | `gemini-3.5-flash` |
| Judge models | `gemini-3.1-pro-preview` (Google Gemini), `opus-5.5-low` (Anthropic Claude) (primary); `gemma-4-31b-it` (Google Gemma, tiebreak only on disagreement) |
| Seeds | 1, 2, 3 |
| Scenarios | core 30, held-out 30 |
| Rollouts | 1440 total, 1440 scored, 0 harness errors (excluded) |
| Bootstrap | 10,000 two-level cluster resamples (scenarios, then seeds), seed 20261104 |

**Framework packs**

| Framework | Visibility | Source | Ref |
| :-- | :-- | :-- | :-- |
| Armature (OSS) | public | https://github.com/drinkspiller/armature-cdd | `3639baa7499cd8a1f354e19e0783e997b0651ad1` |
| GitHub Spec Kit | public | https://github.com/github/spec-kit | `34a0d388eac671d656eb05b125ad3ed6056168ed` |
| OpenSpec | public | https://github.com/Fission-AI/OpenSpec | `27c0515724decc633818c735ee596481eec78a8b` |
| BMAD Method | public | https://github.com/bmad-code-org/BMAD-METHOD | `bab9082c3e884e0d72c759bcd1a6d90bcc01be84` |
| Cline Memory Bank | public | https://github.com/cline/prompts | `2fc3b77a8fe39553ac424bfc7cdc9883e4a21e1f` |
| Conductor (Gemini CLI extension) | public | https://github.com/gemini-cli-extensions/conductor | `7a5c560a4fdf5297be58594cc37527eb12790272` |
| Wayfinder (mattpocock/skills) | public | https://github.com/mattpocock/skills | `d1478fcb140db0b93c0c8df17bcfd311844749d0` |
| Armature (OSS, unreleased working tree) | public | local_path (`$CDD_BENCH_ARMATURE_OSS_ROOT`) | `git_head=6877d8e55a23ecc4adf5d2fd048e01cc2454d49f`, `dirty_files=4` |

## Headline: outcome score tiers

The outcome score is the fraction of deterministic checks passed (what the agent did in the sandbox). Tiers group frameworks whose paired difference against the tier's top framework has a 95% CI that includes 0. Frameworks in the same tier are statistically indistinguishable on this benchmark; order within a tier is by point estimate and is not a ranking.

### gemini-3.5-flash (core + held-out)

| Tier | Framework | Outcome score [95% CI] | Judge score [95% CI] | Paired diff vs closest competitor (outcome) | Scenarios w/ data |
| :-: | :-- | :-- | :-- | :-- | :-: |
| 1 | Armature (OSS, unreleased working tree) | 0.825 [0.765, 0.884] | n/a [n/a, n/a] | +0.011 [-0.061, +0.086] vs Wayfinder (mattpocock/skills) | 60/60 |
| 1 | Wayfinder (mattpocock/skills) | 0.814 [0.750, 0.874] | n/a [n/a, n/a] | -0.011 [-0.086, +0.061] vs Armature (OSS, unreleased working tree) | 60/60 |
| 1 | Cline Memory Bank | 0.780 [0.719, 0.837] | n/a [n/a, n/a] | +0.013 [-0.059, +0.090] vs BMAD Method | 60/60 |
| 1 | BMAD Method | 0.767 [0.701, 0.831] | n/a [n/a, n/a] | -0.013 [-0.090, +0.059] vs Cline Memory Bank | 60/60 |
| 2 | OpenSpec | 0.743 [0.672, 0.812] | 0.608 [0.423, 0.839] | +0.012 [-0.029, +0.054] vs GitHub Spec Kit | 60/60 |
| 2 | GitHub Spec Kit | 0.731 [0.658, 0.800] | 0.672 [0.568, 0.786] | -0.012 [-0.054, +0.029] vs OpenSpec | 60/60 |
| 2 | Armature (OSS) | 0.679 [0.602, 0.755] | 0.566 [0.444, 0.677] | +0.009 [-0.058, +0.081] vs Conductor (Gemini CLI extension) | 60/60 |
| 3 | Conductor (Gemini CLI extension) | 0.670 [0.591, 0.748] | n/a [n/a, n/a] | -0.009 [-0.081, +0.058] vs Armature (OSS) | 60/60 |

**How to read it:** Armature (OSS, unreleased working tree) passed 82.5% of all deterministic sandbox checks (Outcome score `0.825 [0.765, 0.884]`, with a `+0.011 [-0.061, +0.086]` paired difference against Wayfinder (mattpocock/skills)). Because the 95% CI on the paired difference between Tier 1 frameworks crosses `0.000`, Tier 1 entries are statistically indistinguishable on this scenario set, while Tier 2+ entries scored significantly lower.

(!) marks a framework missing scored rollouts for some scenarios. Its paired differences then rest on fewer scenarios than its competitors'.

### Armature Distribution Note

`Armature (OSS)` (`drinkspiller/armature-cdd`) is the cross-platform public distribution of the core Armature protocol. Host-specific enterprise environment rules are packaged separately outside the public distribution so generic sandbox evaluations measure the core protocol without host-adapter token overhead.

## Core vs held-out

Held-out scenarios were written by a separate author who did not read the core scenarios or any framework pack. That author's agent host did, however, load two Armature rule files as always-on context (see Limitations), so held-out is independent of the core set and of every framework except Armature. A lead that shrinks on held-out suggests the core set favors that framework's dialect.

### gemini-3.5-flash

| Framework | Core outcome [CI] | Held-out outcome [CI] | Delta | Core tier | Held-out tier |
| :-- | :-- | :-- | :-: | :-: | :-: |
| Armature (OSS) | 0.729 [0.622, 0.831] | 0.630 [0.513, 0.739] | -0.099 | 2 | 2 |
| Armature (OSS, unreleased working tree) | 0.896 [0.822, 0.959] | 0.755 [0.655, 0.847] | -0.141 | 1 | 1 |
| BMAD Method | 0.779 [0.695, 0.860] | 0.755 [0.648, 0.852] | -0.024 | 2 | 1 |
| Conductor (Gemini CLI extension) | 0.669 [0.572, 0.764] | 0.671 [0.544, 0.792] | +0.002 | 3 | 2 |
| GitHub Spec Kit | 0.785 [0.697, 0.867] | 0.678 [0.556, 0.789] | -0.107 | 2 | 2 |
| Cline Memory Bank | 0.799 [0.725, 0.870] | 0.762 [0.662, 0.854] | -0.037 | 2 | 1 |
| OpenSpec | 0.818 [0.733, 0.894] | 0.668 [0.550, 0.780] | -0.151 | 2 | 2 |
| Wayfinder (mattpocock/skills) | 0.816 [0.729, 0.896] | 0.812 [0.712, 0.901] | -0.004 | 1 | 1 |

**How to read it:** Compare `Core tier` against `Held-out tier` and inspect `Delta` (`Held-out - Core`). For example, Armature (OSS, unreleased working tree) scored `0.896` (`Core tier 1`) on the 30-scenario core set and `0.755` (`Held-out tier 1`) on the 30-scenario sealed held-out set (`Delta = -0.141`). A negative `Delta` across most frameworks reflects harder held-out tasks, whereas dropping out of `Tier 1` on `Held-out` signals potential overfitting to core task patterns.

## Per-pillar outcome score (core + held-out)

### gemini-3.5-flash

| Framework | spec_gating | surgical_velocity | drift_governance | state_safety | context_continuity |
| :-- | :-- | :-- | :-- | :-- | :-- |
| Armature (OSS) | 0.451 [0.361, 0.542] | 0.993 [0.972, 1.000] | 0.787 [0.653, 0.912] | 0.766 [0.652, 0.872] | 0.399 [0.243, 0.565] |
| Armature (OSS, unreleased working tree) | 0.671 [0.549, 0.792] | 1.000 [1.000, 1.000] | 0.845 [0.718, 0.956] | 0.860 [0.734, 0.968] | 0.750 [0.639, 0.840] |
| BMAD Method | 0.623 [0.551, 0.688] | 0.986 [0.958, 1.000] | 0.778 [0.653, 0.896] | 0.754 [0.576, 0.911] | 0.694 [0.516, 0.861] |
| Conductor (Gemini CLI extension) | 0.639 [0.556, 0.708] | 0.976 [0.943, 1.000] | 0.644 [0.486, 0.803] | 0.694 [0.500, 0.879] | 0.399 [0.242, 0.568] |
| GitHub Spec Kit | 0.576 [0.431, 0.694] | 0.968 [0.929, 1.000] | 0.806 [0.667, 0.931] | 0.617 [0.433, 0.795] | 0.689 [0.557, 0.807] |
| Cline Memory Bank | 0.574 [0.484, 0.681] | 0.749 [0.706, 0.782] | 0.917 [0.840, 0.979] | 0.725 [0.523, 0.904] | 0.938 [0.861, 1.000] |
| OpenSpec | 0.597 [0.451, 0.708] | 0.982 [0.950, 1.000] | 0.796 [0.657, 0.926] | 0.707 [0.524, 0.878] | 0.632 [0.514, 0.729] |
| Wayfinder (mattpocock/skills) | 0.775 [0.648, 0.896] | 0.983 [0.956, 1.000] | 0.812 [0.660, 0.944] | 0.737 [0.556, 0.903] | 0.763 [0.626, 0.888] |

Pillar CIs are wide by construction (about 12 scenarios per pillar); read them as directional.

**How to read it:** Each column averages roughly 12 scenarios targeting one engineering capability: `spec_gating` (clarifying requirements before writing code), `surgical_velocity` (fast-pathing small bug fixes without ceremony), `drift_governance` (catching contradictions against existing ADRs or glossary terms), `state_safety` (halting before destructive operations), and `context_continuity` (resuming draft specs across sessions). Read across a row to see a framework's trade-off profile—for instance, whether heavy documentation ceremony boosts `drift_governance` at the cost of `surgical_velocity`.

## Run-to-run variance and cross-model swing

SD across seeds = standard deviation of the per-seed framework outcome score (mean over scenarios). Within-scenario SD = mean over scenarios of the SD of that scenario's outcome across seeds. Swing = max minus min outcome score across target models.

| Framework | SD across seeds (gemini-3.5-flash) | Within-scenario SD (gemini-3.5-flash) | Cross-model swing | Tier by model |
| :-- | :-: | :-: | :-: | :-- |
| Armature (OSS) | 0.007 | 0.072 | n/a | gemini-3.5-flash: 2 |
| Armature (OSS, unreleased working tree) | 0.032 | 0.061 | n/a | gemini-3.5-flash: 1 |
| BMAD Method | 0.006 | 0.081 | n/a | gemini-3.5-flash: 1 |
| Conductor (Gemini CLI extension) | 0.007 | 0.046 | n/a | gemini-3.5-flash: 3 |
| GitHub Spec Kit | 0.017 | 0.075 | n/a | gemini-3.5-flash: 2 |
| Cline Memory Bank | 0.008 | 0.070 | n/a | gemini-3.5-flash: 1 |
| OpenSpec | 0.030 | 0.062 | n/a | gemini-3.5-flash: 2 |
| Wayfinder (mattpocock/skills) | 0.032 | 0.072 | n/a | gemini-3.5-flash: 1 |

**How to read it:** Armature (OSS, unreleased working tree) has an `SD across seeds` of `0.032` (±3.2 pp), meaning its `82.5%` headline score barely moves from seed to seed. Values under `0.035` (`3.5 pp`) indicate high run-to-run stability. `Within-scenario SD` (`0.061` (±6.1 pp)) is naturally larger because individual scenario outcomes vary more across seeds before averaging out over the full scenario set.

## Cost per rollout (mean, scored rollouts only)

Output tokens are visible output only (`candidatesTokenCount`); thinking tokens and input tokens are reported separately and never summed into one "length" number.

Input tokens include each framework's always-on prompt on every call, so a large pack shows up here as cost even when it does not change behavior. Retry columns count tokens billed on discarded attempts (empty candidates, server errors); they are not part of the scored usage.

| Framework | Model | n | Input tok | Output tok | Thinking tok | Cached tok | API calls | Wall-clock s | Retry tok (in/out/think) |
| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| Armature (OSS) | gemini-3.5-flash | 180 | 712441 | 1174 | 4381 | 581416 | 28.1 | 51.5 | 0/0/0 |
| Armature (OSS, unreleased working tree) | gemini-3.5-flash | 180 | 661345 | 2349 | 4809 | 525919 | 35.7 | 61.6 | 0/0/0 |
| BMAD Method | gemini-3.5-flash | 180 | 395477 | 2266 | 6213 | 285541 | 34.9 | 58.0 | 60/14/77 |
| Conductor (Gemini CLI extension) | gemini-3.5-flash | 180 | 137090 | 1073 | 3338 | 70156 | 20.4 | 37.0 | 29/0/0 |
| GitHub Spec Kit | gemini-3.5-flash | 180 | 285673 | 2920 | 5512 | 179857 | 31.7 | 66.5 | 0/0/0 |
| Cline Memory Bank | gemini-3.5-flash | 180 | 245364 | 2622 | 6935 | 123160 | 40.2 | 68.5 | 128/30/61 |
| OpenSpec | gemini-3.5-flash | 180 | 498196 | 3000 | 5104 | 363411 | 42.8 | 72.9 | 0/0/0 |
| Wayfinder (mattpocock/skills) | gemini-3.5-flash | 180 | 315756 | 2088 | 6152 | 187721 | 35.3 | 60.3 | 0/0/0 |

**How to read it:** `Input tok` is the cumulative prompt tokens sent across all API turns in an average rollout (for Armature (OSS, unreleased working tree), `661345` input tokens across `35.7` API calls, with `525919` tokens or `79.5%` served from prompt cache). `Output tok` (`2349`) counts visible replies and tool arguments, `Thinking tok` (`4809`) counts internal reasoning tokens, and `Wall-clock s` (`61.6s`) is the mean duration per rollout.

## Harness errors

Harness-error rollouts are excluded from every score. A cell above 5% invalidates the run. "Retried" counts cells that failed and were re-run with --retry-harness-errors (replaced records are kept in rollouts.retried.jsonl); a framework that needs many retries may be selected toward its easier successes.

| Framework | Model | Errors / total | Rate | Retried | Status | Kinds |
| :-- | :-- | :-: | :-: | :-: | :-- | :-- |
| Armature (OSS) | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |
| Armature (OSS, unreleased working tree) | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |
| BMAD Method | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |
| Conductor (Gemini CLI extension) | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |
| GitHub Spec Kit | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |
| Cline Memory Bank | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |
| OpenSpec | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |
| Wayfinder (mattpocock/skills) | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |

**How to read it:** `0.0%` (`Status: ok`) confirms every scheduled rollout completed without unhandled API or sandbox crashes. Any cell exceeding `5.0%` is flagged `**INVALID**` so high crash rates cannot artificially inflate a framework's score by dropping hard scenarios.

## Commands by outcome

How the sandbox handled each `run_command`: `mock` = scenario mock (canned output), `pack_tool` = the framework's own tooling run for real, `builtin` = allowlisted tool run for real, `refused` = not available in the sandbox, `wrap_up_refused` = tool calls made after the step limit, which the harness declines while it asks for a final reply (counted apart so they don't inflate `refused`). Many refusals for one framework mean the sandbox could not run what its pack asked for, which can depress that framework's score for reasons unrelated to its method.

| Framework | Model | mock | pack_tool | builtin | refused | wrap_up_refused | Refused per rollout |
| :-- | :-- | --: | --: | --: | --: | --: | --: |
| Armature (OSS) | gemini-3.5-flash | 289 | 0 | 406 | 76 | 1 | 0.42 |
| Armature (OSS, unreleased working tree) | gemini-3.5-flash | 459 | 0 | 649 | 110 | 1 | 0.61 |
| BMAD Method | gemini-3.5-flash | 620 | 119 | 908 | 596 | 6 | 3.31 |
| Conductor (Gemini CLI extension) | gemini-3.5-flash | 329 | 0 | 592 | 141 | 1 | 0.78 |
| GitHub Spec Kit | gemini-3.5-flash | 680 | 150 | 850 | 325 | 1 | 1.81 |
| Cline Memory Bank | gemini-3.5-flash | 976 | 0 | 852 | 296 | 4 | 1.64 |
| OpenSpec | gemini-3.5-flash | 570 | 1679 | 763 | 197 | 4 | 1.09 |
| Wayfinder (mattpocock/skills) | gemini-3.5-flash | 783 | 0 | 1118 | 283 | 5 | 1.57 |

**How to read it:** A `Refused per rollout` value below `1.00` means the framework rarely invoked shell commands missing from the sandbox allowlist. Higher refusal rates (`> 2.00`) indicate a framework's prompts asked for external CLIs not provisioned in the test sandbox.

## How turns ended

Share of user turns that ended with a text reply, an `ask_user` call, the per-turn step limit (`max_steps`, after which the harness forces one final text reply), or a context-length overflow. A high max_steps rate means the framework's protocol is step-hungry, which is a real cost, and those turns are scored as they are.

| Framework | Model | Turns | text | ask_user | max_steps | context_overflow | max_steps rate |
| :-- | :-- | --: | --: | --: | --: | --: | --: |
| Armature (OSS) | gemini-3.5-flash | 324 | 232 | 89 | 3 | 0 | 0.9% |
| Armature (OSS, unreleased working tree) | gemini-3.5-flash | 324 | 222 | 91 | 11 | 0 | 3.4% |
| BMAD Method | gemini-3.5-flash | 324 | 246 | 35 | 43 | 0 | 13.3% |
| Conductor (Gemini CLI extension) | gemini-3.5-flash | 324 | 119 | 198 | 7 | 0 | 2.2% |
| GitHub Spec Kit | gemini-3.5-flash | 324 | 297 | 11 | 16 | 0 | 4.9% |
| Cline Memory Bank | gemini-3.5-flash | 324 | 264 | 14 | 46 | 0 | 14.2% |
| OpenSpec | gemini-3.5-flash | 324 | 298 | 13 | 13 | 0 | 4.0% |
| Wayfinder (mattpocock/skills) | gemini-3.5-flash | 324 | 250 | 53 | 21 | 0 | 6.5% |

**How to read it:** Healthy protocols end turns via `text` (delivering the solution) or `ask_user` (pausing at a decision or safety gate), keeping `max_steps rate` under `5.0%`. High `max_steps rate` values (`> 10%`) indicate the agent spent its entire 25-step turn budget on ceremony or exploration before being forced to wrap up.

## Judge reliability

- Criteria judged: 2736; not in the `opus-5.5-low` subsample (one vote, so no score): 1408; excluded for invalid votes (fewer than 2 valid): 954; tiebreaks: 24.
- `opus-5.5-low` judged a deterministic sample of (scenario, seed) cells. The sample is the same for every framework and model, and the judge score uses only those cells. The other primary judge voted on every criterion.
- The public code release ships Gemini REST judges only. Reproducing the cross-family (Claude) judge requires Anthropic API access, which the public release does not include.
- `gemini-3.1-pro-preview`: 1328 votes, 1 invalid.
- `gemma-4-31b-it`: 24 votes, 0 invalid.
- `opus-5.5-low`: 1328 votes, 954 invalid.
- Inter-judge Cohen's kappa (primary pair): 0.867 [0.799, 0.930] over 374 items in 51 scenario clusters; raw agreement 93.6%.
- Human calibration: **none yet.** Judge accuracy against human labels is unknown.

**How to read it:** Cohen's kappa measures agreement between the two primary judges (Google Gemini and Anthropic Claude) beyond chance (`0.00` = chance agreement, `> 0.60` = substantial, `> 0.80` = near-perfect). Under `ADR 0018`, any criterion missing a valid vote from either primary judge is excluded rather than backfilled with a single-family score.

## Leakage audit

| Framework | Summary |
| :-- | :-- |
| Armature (OSS) | display_name=Armature (OSS), exclusive_3grams=0, exclusive_4grams=0, pack_chars=361276, rule_1gram_hits=0, shared_1grams=0, shared_3grams=0, shared_4grams=0 |
| Armature (OSS, unreleased working tree) | display_name=Armature (OSS, unreleased working tree), exclusive_3grams=0, exclusive_4grams=0, pack_chars=307598, rule_1gram_hits=0, shared_1grams=0, shared_3grams=0, shared_4grams=0 |
| BMAD Method | display_name=BMAD Method, exclusive_3grams=2, exclusive_4grams=0, pack_chars=1432422, rule_1gram_hits=118, shared_1grams=118, shared_3grams=2, shared_4grams=0 |
| Conductor (Gemini CLI extension) | display_name=Conductor (Gemini CLI extension), exclusive_3grams=0, exclusive_4grams=0, pack_chars=152546, rule_1gram_hits=23, shared_1grams=23, shared_3grams=0, shared_4grams=0 |
| GitHub Spec Kit | display_name=GitHub Spec Kit, exclusive_3grams=1, exclusive_4grams=0, pack_chars=225545, rule_1gram_hits=54, shared_1grams=54, shared_3grams=2, shared_4grams=0 |
| Cline Memory Bank | display_name=Cline Memory Bank, exclusive_3grams=0, exclusive_4grams=0, pack_chars=3871, rule_1gram_hits=3, shared_1grams=3, shared_3grams=0, shared_4grams=0 |
| OpenSpec | display_name=OpenSpec, exclusive_3grams=0, exclusive_4grams=0, pack_chars=94758, rule_1gram_hits=42, shared_1grams=42, shared_3grams=1, shared_4grams=0 |
| Wayfinder (mattpocock/skills) | display_name=Wayfinder (mattpocock/skills), exclusive_3grams=2, exclusive_4grams=0, pack_chars=215243, rule_1gram_hits=101, shared_1grams=101, shared_3grams=2, shared_4grams=0 |

See `leakage.json` for top shared n-grams.

**How to read it:** `shared_1grams=0, shared_3grams=0, shared_4grams=0` means zero distinctive single tokens or 3/4-word phrases from a framework's rules appear inside the benchmark's deterministic grading regexes, verifying that scores reflect behavior rather than prompt-to-grader phrase echoing.

## Limitations

- Judge accuracy is not human-calibrated.
- The judge panel is cross-family (Google Gemini and Anthropic Claude). The tiebreak judge is Gemma, a Google model from a different family than Gemini, so disagreements may still resolve toward Google-family preferences. Target models never judge.
- **The Claude Opus 5.5 (Low) judge runs inside an agent-host session that loads the operator's always-on rules and memory files. Those include the full text of two internal Armature rule files and a path reference to Armature's protocol file. Despite prompt-level instructions to ignore them, residual bias toward recognizing or favoring Armature patterns cannot be ruled out. A raw Anthropic API key would remove this risk.**
- Claude judge temperature could not be controlled (host default). Each Claude verdict is voided if its conversation used any tool other than reading its prompt file and writing its verdict file.
- The Claude judge saw a deterministic subsample of (scenario, seed) cells, the same for every framework. Judge scores rest on that subsample only.
- **Scenario and held-out authors, and the Claude judge, ran inside agent-host sessions that load the full text of two internal Armature rule files and a path reference to Armature's protocol file. Despite instructions to ignore external context, scenarios may unconsciously favor context-driven patterns that Armature handles well. The held-out set is independent of the core scenarios and of every framework pack except Armature. A future iteration should author and judge through raw API calls to remove this vector.**
- The scenario and check authors are Claude-family agents, the same family as the Claude judge, so that judge may favor behaviors its own family wrote down as correct. The target models are Gemini models.
- Blinding replaces framework names, commands, and directory names only. Distinctive output structure can still reveal a framework to a judge that knows the upstream repos. This is one reason the judge score is secondary.
- The sandbox mocks ops tools (kubectl, terraform, and similar) with canned output. Behavior against real infrastructure may differ.
- Each framework's mapping from scenario intent to its entry command is a modeling choice (see frameworks/README.md). Different mappings could change results.
- Scores measure behavior in short scripted conversations with these target models and seeds. They do not measure long-horizon project outcomes, and tiers can change with other models.
- Per-pillar and per-set results rest on roughly 12 and 30 scenarios respectively; small differences are not meaningful.
