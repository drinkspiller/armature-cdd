# CDD/SDD Benchmark v2 Report (public subset)

## Run identity

| Field | Value |
| :-- | :-- |
| Run id | `v2-full-20261104` |
| Config hash | `569f2474dcd905a32bcfd5272861baa0f0a6ab8dea6bc481856bf8262bc5e5cf` |
| Target models | `gemini-3-flash-preview`, `gemini-3.5-flash` |
| Judge models | `gemini-3.1-pro-preview` (Google Gemini), `opus-5.5-low` (Anthropic Claude) (primary); `gemma-4-31b-it` (Google Gemma, tiebreak only on disagreement) |
| Seeds | 1, 2, 3 |
| Scenarios | core 30, held-out 30 |
| Rollouts | 2520 total, 2520 scored, 0 harness errors (excluded) |
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

## Headline: outcome score tiers

The outcome score is the fraction of deterministic checks passed (what the agent did in the sandbox). Tiers group frameworks whose paired difference against the tier's top framework has a 95% CI that includes 0. Frameworks in the same tier are statistically indistinguishable on this benchmark; order within a tier is by point estimate and is not a ranking.

### gemini-3-flash-preview (core + held-out)

| Tier | Framework | Outcome score [95% CI] | Judge score [95% CI] | Paired diff vs closest competitor (outcome) | Scenarios w/ data |
| :-: | :-- | :-- | :-- | :-- | :-: |
| 1 | Wayfinder (mattpocock/skills) | 0.730 [0.664, 0.794] | 0.714 [0.200, 1.000] | +0.003 [-0.053, +0.058] vs BMAD Method | 60/60 |
| 1 | BMAD Method | 0.727 [0.665, 0.788] | 0.643 [0.125, 1.000] | -0.003 [-0.058, +0.053] vs Wayfinder (mattpocock/skills) | 60/60 |
| 1 | Cline Memory Bank | 0.711 [0.641, 0.780] | 0.500 [0.000, 1.000] | -0.016 [-0.093, +0.058] vs BMAD Method | 60/60 |
| 1 | Armature (OSS) | 0.687 [0.611, 0.759] | 0.333 [0.000, 0.833] | +0.015 [-0.062, +0.095] vs GitHub Spec Kit | 60/60 |
| 1 | GitHub Spec Kit | 0.672 [0.601, 0.739] | 0.429 [0.000, 0.875] | -0.015 [-0.095, +0.062] vs Armature (OSS) | 60/60 |
| 2 | OpenSpec | 0.617 [0.547, 0.686] | 0.214 [0.000, 0.643] | +0.028 [-0.039, +0.095] vs Conductor (Gemini CLI extension) | 60/60 |
| 2 | Conductor (Gemini CLI extension) | 0.589 [0.516, 0.660] | 0.000 [0.000, 0.000] | -0.028 [-0.095, +0.039] vs OpenSpec | 60/60 |

(!) marks a framework missing scored rollouts for some scenarios. Its paired differences then rest on fewer scenarios than its competitors'.

### gemini-3.5-flash (core + held-out)

| Tier | Framework | Outcome score [95% CI] | Judge score [95% CI] | Paired diff vs closest competitor (outcome) | Scenarios w/ data |
| :-: | :-- | :-- | :-- | :-- | :-: |
| 1 | Wayfinder (mattpocock/skills) | 0.811 [0.746, 0.871] | 0.643 [0.125, 1.000] | +0.016 [-0.040, +0.071] vs BMAD Method | 60/60 |
| 1 | BMAD Method | 0.795 [0.735, 0.853] | 0.595 [0.167, 1.000] | +0.011 [-0.053, +0.072] vs Cline Memory Bank | 60/60 |
| 1 | Cline Memory Bank | 0.785 [0.725, 0.841] | 0.500 [0.100, 0.900] | -0.011 [-0.072, +0.053] vs BMAD Method | 60/60 |
| 1 | GitHub Spec Kit | 0.764 [0.694, 0.830] | 0.500 [0.125, 0.900] | -0.020 [-0.096, +0.051] vs Cline Memory Bank | 60/60 |
| 1 | OpenSpec | 0.743 [0.671, 0.811] | 0.500 [0.125, 0.875] | -0.021 [-0.066, +0.025] vs GitHub Spec Kit | 60/60 |
| 2 | Armature (OSS) | 0.691 [0.614, 0.767] | 0.417 [0.000, 0.800] | +0.027 [-0.040, +0.097] vs Conductor (Gemini CLI extension) | 60/60 |
| 2 | Conductor (Gemini CLI extension) | 0.665 [0.585, 0.742] | 0.333 [0.333, 0.333] | -0.027 [-0.097, +0.040] vs Armature (OSS) | 60/60 |

(!) marks a framework missing scored rollouts for some scenarios. Its paired differences then rest on fewer scenarios than its competitors'.

### All target models pooled (core + held-out)

| Tier | Framework | Outcome score [95% CI] | Judge score [95% CI] | Paired diff vs closest competitor (outcome) | Scenarios w/ data |
| :-: | :-- | :-- | :-- | :-- | :-: |
| 1 | Wayfinder (mattpocock/skills) | 0.770 [0.710, 0.826] | 0.679 [0.312, 1.000] | +0.009 [-0.036, +0.055] vs BMAD Method | 60/60 |
| 1 | BMAD Method | 0.761 [0.705, 0.813] | 0.619 [0.250, 1.000] | -0.009 [-0.055, +0.036] vs Wayfinder (mattpocock/skills) | 60/60 |
| 1 | Cline Memory Bank | 0.748 [0.689, 0.806] | 0.500 [0.143, 0.875] | -0.013 [-0.075, +0.048] vs BMAD Method | 60/60 |
| 1 | GitHub Spec Kit | 0.718 [0.654, 0.780] | 0.464 [0.167, 0.750] | +0.028 [-0.042, +0.097] vs Armature (OSS) | 60/60 |
| 1 | Armature (OSS) | 0.689 [0.613, 0.762] | 0.417 [0.083, 0.750] | +0.009 [-0.060, +0.079] vs OpenSpec | 60/60 |
| 2 | OpenSpec | 0.680 [0.616, 0.743] | 0.357 [0.062, 0.667] | -0.009 [-0.079, +0.060] vs Armature (OSS) | 60/60 |
| 2 | Conductor (Gemini CLI extension) | 0.627 [0.553, 0.699] | 0.083 [0.000, 0.333] | -0.053 [-0.112, +0.003] vs OpenSpec | 60/60 |

(!) marks a framework missing scored rollouts for some scenarios. Its paired differences then rest on fewer scenarios than its competitors'.

### Armature Distribution Note

`Armature (OSS)` (`drinkspiller/armature-cdd`) is the cross-platform public distribution of the core Armature protocol. Host-specific enterprise environment rules are packaged separately outside the public distribution so generic sandbox evaluations measure the core protocol without host-adapter token overhead.

## Core vs held-out

Held-out scenarios were written by a separate author who did not read the core scenarios or any framework pack. That author's agent host did, however, load two Armature rule files as always-on context (see Limitations), so held-out is independent of the core set and of every framework except Armature. A lead that shrinks on held-out suggests the core set favors that framework's dialect.

### gemini-3-flash-preview

| Framework | Core outcome [CI] | Held-out outcome [CI] | Delta | Core tier | Held-out tier |
| :-- | :-- | :-- | :-: | :-: | :-: |
| Armature (OSS) | 0.723 [0.617, 0.824] | 0.651 [0.540, 0.756] | -0.072 | 1 | 1 |
| BMAD Method | 0.723 [0.634, 0.806] | 0.731 [0.642, 0.815] | +0.009 | 1 | 1 |
| Conductor (Gemini CLI extension) | 0.582 [0.490, 0.674] | 0.595 [0.481, 0.703] | +0.013 | 2 | 2 |
| GitHub Spec Kit | 0.740 [0.649, 0.826] | 0.603 [0.493, 0.704] | -0.138 | 1 | 2 |
| Cline Memory Bank | 0.744 [0.659, 0.827] | 0.679 [0.566, 0.787] | -0.065 | 1 | 1 |
| OpenSpec | 0.709 [0.618, 0.797] | 0.525 [0.418, 0.631] | -0.184 | 1 | 2 |
| Wayfinder (mattpocock/skills) | 0.751 [0.662, 0.837] | 0.708 [0.610, 0.798] | -0.043 | 1 | 1 |

> [!WARNING]
> Lead shrinkage on held-out:
>
> - **Armature (OSS)**: lead over BMAD Method is +0.000 on core but -0.082 on held-out (held-out tier 1). The lead shrinks on held-out.
> - **GitHub Spec Kit**: lead over Cline Memory Bank is -0.004 on core but -0.077 on held-out (held-out tier 2). The lead shrinks on held-out.
> - **OpenSpec**: lead over BMAD Method is -0.013 on core but -0.207 on held-out (held-out tier 2). The lead shrinks on held-out.

### gemini-3.5-flash

| Framework | Core outcome [CI] | Held-out outcome [CI] | Delta | Core tier | Held-out tier |
| :-- | :-- | :-- | :-: | :-: | :-: |
| Armature (OSS) | 0.717 [0.604, 0.826] | 0.666 [0.556, 0.773] | -0.051 | 1 | 2 |
| BMAD Method | 0.782 [0.695, 0.866] | 0.808 [0.717, 0.889] | +0.026 | 1 | 1 |
| Conductor (Gemini CLI extension) | 0.649 [0.547, 0.750] | 0.681 [0.557, 0.797] | +0.032 | 2 | 2 |
| GitHub Spec Kit | 0.814 [0.736, 0.889] | 0.714 [0.594, 0.823] | -0.100 | 1 | 2 |
| Cline Memory Bank | 0.791 [0.714, 0.865] | 0.779 [0.681, 0.864] | -0.013 | 1 | 1 |
| OpenSpec | 0.795 [0.711, 0.872] | 0.691 [0.572, 0.806] | -0.104 | 1 | 2 |
| Wayfinder (mattpocock/skills) | 0.796 [0.708, 0.879] | 0.826 [0.728, 0.911] | +0.030 | 1 | 1 |

> [!WARNING]
> Lead shrinkage on held-out:
>
> - **Armature (OSS)**: lead over BMAD Method is -0.066 on core but -0.142 on held-out (held-out tier 2). The lead shrinks on held-out.
> - **GitHub Spec Kit**: lead over Wayfinder (mattpocock/skills) is +0.018 on core but -0.112 on held-out (held-out tier 2). The lead shrinks on held-out.
> - **OpenSpec**: lead over Wayfinder (mattpocock/skills) is -0.001 on core but -0.135 on held-out (held-out tier 2). The lead shrinks on held-out.

### All models pooled

| Framework | Core outcome [CI] | Held-out outcome [CI] | Delta | Core tier | Held-out tier |
| :-- | :-- | :-- | :-: | :-: | :-: |
| Armature (OSS) | 0.720 [0.614, 0.821] | 0.658 [0.555, 0.760] | -0.062 | 1 | 1 |
| BMAD Method | 0.752 [0.673, 0.828] | 0.770 [0.689, 0.838] | +0.017 | 1 | 1 |
| Conductor (Gemini CLI extension) | 0.615 [0.525, 0.706] | 0.638 [0.526, 0.741] | +0.023 | 2 | 2 |
| GitHub Spec Kit | 0.777 [0.703, 0.847] | 0.658 [0.556, 0.753] | -0.119 | 1 | 2 |
| Cline Memory Bank | 0.768 [0.693, 0.840] | 0.729 [0.631, 0.818] | -0.039 | 1 | 1 |
| OpenSpec | 0.752 [0.675, 0.827] | 0.608 [0.506, 0.705] | -0.144 | 1 | 2 |
| Wayfinder (mattpocock/skills) | 0.774 [0.694, 0.849] | 0.767 [0.679, 0.844] | -0.006 | 1 | 1 |

> [!WARNING]
> Lead shrinkage on held-out:
>
> - **GitHub Spec Kit**: lead over Wayfinder (mattpocock/skills) is +0.004 on core but -0.109 on held-out (held-out tier 2). The lead shrinks on held-out.
> - **Cline Memory Bank**: lead over Wayfinder (mattpocock/skills) is -0.005 on core but -0.039 on held-out (held-out tier 1). The lead shrinks on held-out.
> - **OpenSpec**: lead over BMAD Method is -0.000 on core but -0.161 on held-out (held-out tier 2). The lead shrinks on held-out.

## Per-pillar outcome score (core + held-out)

### gemini-3-flash-preview

| Framework | spec_gating | surgical_velocity | drift_governance | state_safety | context_continuity |
| :-- | :-- | :-- | :-- | :-- | :-- |
| Armature (OSS) | 0.562 [0.444, 0.660] | 0.848 [0.763, 0.919] | 0.785 [0.646, 0.917] | 0.849 [0.715, 0.961] | 0.392 [0.225, 0.569] |
| BMAD Method | 0.741 [0.630, 0.847] | 0.870 [0.819, 0.920] | 0.780 [0.669, 0.887] | 0.453 [0.307, 0.614] | 0.791 [0.690, 0.893] |
| Conductor (Gemini CLI extension) | 0.597 [0.493, 0.688] | 0.814 [0.732, 0.883] | 0.627 [0.472, 0.780] | 0.513 [0.335, 0.688] | 0.392 [0.239, 0.551] |
| GitHub Spec Kit | 0.593 [0.451, 0.720] | 0.869 [0.829, 0.913] | 0.748 [0.611, 0.882] | 0.536 [0.352, 0.718] | 0.612 [0.464, 0.763] |
| Cline Memory Bank | 0.556 [0.438, 0.688] | 0.622 [0.537, 0.705] | 0.861 [0.764, 0.944] | 0.552 [0.362, 0.754] | 0.965 [0.903, 1.000] |
| OpenSpec | 0.569 [0.431, 0.688] | 0.752 [0.600, 0.882] | 0.697 [0.556, 0.833] | 0.483 [0.346, 0.634] | 0.583 [0.417, 0.743] |
| Wayfinder (mattpocock/skills) | 0.866 [0.785, 0.938] | 0.895 [0.859, 0.933] | 0.727 [0.604, 0.843] | 0.511 [0.346, 0.680] | 0.651 [0.512, 0.785] |

Pillar CIs are wide by construction (about 12 scenarios per pillar); read them as directional.

### gemini-3.5-flash

| Framework | spec_gating | surgical_velocity | drift_governance | state_safety | context_continuity |
| :-- | :-- | :-- | :-- | :-- | :-- |
| Armature (OSS) | 0.417 [0.340, 0.493] | 0.986 [0.951, 1.000] | 0.817 [0.681, 0.944] | 0.813 [0.704, 0.907] | 0.424 [0.274, 0.589] |
| BMAD Method | 0.646 [0.569, 0.715] | 0.993 [0.972, 1.000] | 0.799 [0.667, 0.917] | 0.707 [0.521, 0.880] | 0.831 [0.716, 0.933] |
| Conductor (Gemini CLI extension) | 0.625 [0.528, 0.715] | 0.987 [0.961, 1.000] | 0.653 [0.486, 0.812] | 0.673 [0.484, 0.842] | 0.385 [0.239, 0.544] |
| GitHub Spec Kit | 0.648 [0.542, 0.734] | 0.993 [0.972, 1.000] | 0.806 [0.660, 0.924] | 0.705 [0.502, 0.894] | 0.668 [0.535, 0.785] |
| Cline Memory Bank | 0.623 [0.498, 0.757] | 0.756 [0.692, 0.801] | 0.896 [0.819, 0.965] | 0.735 [0.535, 0.906] | 0.917 [0.826, 0.986] |
| OpenSpec | 0.560 [0.421, 0.674] | 0.963 [0.915, 1.000] | 0.806 [0.660, 0.938] | 0.726 [0.532, 0.888] | 0.660 [0.542, 0.771] |
| Wayfinder (mattpocock/skills) | 0.808 [0.701, 0.910] | 0.982 [0.953, 1.000] | 0.792 [0.625, 0.931] | 0.737 [0.551, 0.903] | 0.735 [0.608, 0.854] |

Pillar CIs are wide by construction (about 12 scenarios per pillar); read them as directional.

### All models pooled

| Framework | spec_gating | surgical_velocity | drift_governance | state_safety | context_continuity |
| :-- | :-- | :-- | :-- | :-- | :-- |
| Armature (OSS) | 0.490 [0.398, 0.573] | 0.917 [0.862, 0.963] | 0.801 [0.668, 0.926] | 0.831 [0.727, 0.924] | 0.408 [0.253, 0.580] |
| BMAD Method | 0.693 [0.618, 0.764] | 0.932 [0.897, 0.962] | 0.789 [0.676, 0.898] | 0.580 [0.428, 0.721] | 0.811 [0.723, 0.894] |
| Conductor (Gemini CLI extension) | 0.611 [0.514, 0.698] | 0.901 [0.844, 0.945] | 0.640 [0.481, 0.792] | 0.593 [0.431, 0.741] | 0.388 [0.242, 0.544] |
| GitHub Spec Kit | 0.620 [0.503, 0.721] | 0.931 [0.902, 0.958] | 0.777 [0.644, 0.896] | 0.621 [0.462, 0.769] | 0.640 [0.515, 0.759] |
| Cline Memory Bank | 0.589 [0.483, 0.713] | 0.689 [0.622, 0.748] | 0.878 [0.799, 0.951] | 0.644 [0.468, 0.802] | 0.941 [0.868, 0.993] |
| OpenSpec | 0.565 [0.431, 0.674] | 0.857 [0.755, 0.938] | 0.751 [0.618, 0.878] | 0.604 [0.468, 0.737] | 0.622 [0.483, 0.750] |
| Wayfinder (mattpocock/skills) | 0.837 [0.760, 0.912] | 0.938 [0.911, 0.964] | 0.759 [0.622, 0.884] | 0.624 [0.463, 0.773] | 0.693 [0.582, 0.806] |

Pillar CIs are wide by construction (about 12 scenarios per pillar); read them as directional.

## Run-to-run variance and cross-model swing

SD across seeds = standard deviation of the per-seed framework outcome score (mean over scenarios). Within-scenario SD = mean over scenarios of the SD of that scenario's outcome across seeds. Swing = max minus min outcome score across target models.

| Framework | SD across seeds (gemini-3-flash-preview) | Within-scenario SD (gemini-3-flash-preview) | SD across seeds (gemini-3.5-flash) | Within-scenario SD (gemini-3.5-flash) | Cross-model swing | Tier by model |
| :-- | :-: | :-: | :-: | :-: | :-: | :-- |
| Armature (OSS) | 0.023 | 0.072 | 0.016 | 0.070 | 0.004 | gemini-3-flash-preview: 1, gemini-3.5-flash: 2 |
| BMAD Method | 0.017 | 0.122 | 0.013 | 0.096 | 0.068 | gemini-3-flash-preview: 1, gemini-3.5-flash: 1 |
| Conductor (Gemini CLI extension) | 0.020 | 0.040 | 0.023 | 0.053 | 0.076 | gemini-3-flash-preview: 2, gemini-3.5-flash: 2 |
| GitHub Spec Kit | 0.008 | 0.103 | 0.008 | 0.063 | 0.092 | gemini-3-flash-preview: 1, gemini-3.5-flash: 1 |
| Cline Memory Bank | 0.027 | 0.061 | 0.012 | 0.054 | 0.074 | gemini-3-flash-preview: 1, gemini-3.5-flash: 1 |
| OpenSpec | 0.015 | 0.104 | 0.022 | 0.059 | 0.126 | gemini-3-flash-preview: 2, gemini-3.5-flash: 1 |
| Wayfinder (mattpocock/skills) | 0.028 | 0.111 | 0.023 | 0.068 | 0.081 | gemini-3-flash-preview: 1, gemini-3.5-flash: 1 |

## Cost per rollout (mean, scored rollouts only)

Output tokens are visible output only (`candidatesTokenCount`); thinking tokens and input tokens are reported separately and never summed into one "length" number.

Input tokens include each framework's always-on prompt on every call, so a large pack shows up here as cost even when it does not change behavior. Retry columns count tokens billed on discarded attempts (empty candidates, server errors); they are not part of the scored usage.

| Framework | Model | n | Input tok | Output tok | Thinking tok | Cached tok | API calls | Wall-clock s | Retry tok (in/out/think) |
| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| Armature (OSS) | gemini-3-flash-preview | 180 | 662353 | 1326 | 2947 | 567610 | 22.4 | 48.7 | 0/0/0 |
| Armature (OSS) | gemini-3.5-flash | 180 | 710678 | 1173 | 4501 | 567117 | 24.4 | 62.1 | 0/0/0 |
| BMAD Method | gemini-3-flash-preview | 180 | 448786 | 2655 | 5433 | 291941 | 40.8 | 76.0 | 629/0/0 |
| BMAD Method | gemini-3.5-flash | 180 | 414027 | 2321 | 6362 | 297812 | 33.4 | 90.1 | 115/0/60 |
| Conductor (Gemini CLI extension) | gemini-3-flash-preview | 180 | 119651 | 1017 | 2660 | 54625 | 19.2 | 32.7 | 52/0/1 |
| Conductor (Gemini CLI extension) | gemini-3.5-flash | 180 | 146216 | 1095 | 3195 | 75369 | 22.4 | 96.4 | 0/0/0 |
| GitHub Spec Kit | gemini-3-flash-preview | 180 | 271590 | 3139 | 4355 | 166968 | 30.4 | 63.8 | 499/0/0 |
| GitHub Spec Kit | gemini-3.5-flash | 180 | 287537 | 2946 | 5432 | 182205 | 30.6 | 82.0 | 0/0/0 |
| Cline Memory Bank | gemini-3-flash-preview | 180 | 207107 | 2685 | 6036 | 88146 | 38.9 | 66.6 | 0/0/0 |
| Cline Memory Bank | gemini-3.5-flash | 180 | 237013 | 2535 | 6708 | 115359 | 39.4 | 113.6 | 20/0/0 |
| OpenSpec | gemini-3-flash-preview | 180 | 383123 | 2840 | 3996 | 255031 | 35.8 | 64.7 | 131/0/0 |
| OpenSpec | gemini-3.5-flash | 180 | 493875 | 2957 | 5883 | 356093 | 39.6 | 97.7 | 0/0/0 |
| Wayfinder (mattpocock/skills) | gemini-3-flash-preview | 180 | 276403 | 1911 | 4639 | 154788 | 33.8 | 58.5 | 118/0/0 |
| Wayfinder (mattpocock/skills) | gemini-3.5-flash | 180 | 313296 | 1953 | 5995 | 180880 | 36.3 | 162.2 | 37/0/1 |

## Harness errors

Harness-error rollouts are excluded from every score. A cell above 5% invalidates the run. "Retried" counts cells that failed and were re-run with --retry-harness-errors (replaced records are kept in rollouts.retried.jsonl); a framework that needs many retries may be selected toward its easier successes.

| Framework | Model | Errors / total | Rate | Retried | Status | Kinds |
| :-- | :-- | :-: | :-: | :-: | :-- | :-- |
| Armature (OSS) | gemini-3-flash-preview | 0 / 180 | 0.0% | 0 | ok | - |
| Armature (OSS) | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |
| BMAD Method | gemini-3-flash-preview | 0 / 180 | 0.0% | 0 | ok | - |
| BMAD Method | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |
| Conductor (Gemini CLI extension) | gemini-3-flash-preview | 0 / 180 | 0.0% | 0 | ok | - |
| Conductor (Gemini CLI extension) | gemini-3.5-flash | 0 / 180 | 0.0% | 32 | ok | - |
| GitHub Spec Kit | gemini-3-flash-preview | 0 / 180 | 0.0% | 0 | ok | - |
| GitHub Spec Kit | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |
| Cline Memory Bank | gemini-3-flash-preview | 0 / 180 | 0.0% | 0 | ok | - |
| Cline Memory Bank | gemini-3.5-flash | 0 / 180 | 0.0% | 7 | ok | - |
| OpenSpec | gemini-3-flash-preview | 0 / 180 | 0.0% | 0 | ok | - |
| OpenSpec | gemini-3.5-flash | 0 / 180 | 0.0% | 0 | ok | - |
| Wayfinder (mattpocock/skills) | gemini-3-flash-preview | 0 / 180 | 0.0% | 0 | ok | - |
| Wayfinder (mattpocock/skills) | gemini-3.5-flash | 0 / 180 | 0.0% | 25 | ok | - |

## Commands by outcome

How the sandbox handled each `run_command`: `mock` = scenario mock (canned output), `pack_tool` = the framework's own tooling run for real, `builtin` = allowlisted tool run for real, `refused` = not available in the sandbox, `wrap_up_refused` = tool calls made after the step limit, which the harness declines while it asks for a final reply (counted apart so they don't inflate `refused`). Many refusals for one framework mean the sandbox could not run what its pack asked for, which can depress that framework's score for reasons unrelated to its method.

| Framework | Model | mock | pack_tool | builtin | refused | wrap_up_refused | Refused per rollout |
| :-- | :-- | --: | --: | --: | --: | --: | --: |
| Armature (OSS) | gemini-3-flash-preview | 289 | 0 | 933 | 299 | 0 | 1.66 |
| Armature (OSS) | gemini-3.5-flash | 270 | 0 | 359 | 96 | 4 | 0.53 |
| BMAD Method | gemini-3-flash-preview | 528 | 125 | 1618 | 1188 | 1 | 6.60 |
| BMAD Method | gemini-3.5-flash | 613 | 131 | 949 | 577 | 7 | 3.21 |
| Conductor (Gemini CLI extension) | gemini-3-flash-preview | 415 | 0 | 756 | 309 | 0 | 1.72 |
| Conductor (Gemini CLI extension) | gemini-3.5-flash | 380 | 0 | 635 | 147 | 3 | 0.82 |
| GitHub Spec Kit | gemini-3-flash-preview | 435 | 204 | 1202 | 526 | 3 | 2.92 |
| GitHub Spec Kit | gemini-3.5-flash | 701 | 146 | 844 | 329 | 2 | 1.83 |
| Cline Memory Bank | gemini-3-flash-preview | 778 | 0 | 1201 | 432 | 1 | 2.40 |
| Cline Memory Bank | gemini-3.5-flash | 1013 | 0 | 913 | 288 | 4 | 1.60 |
| OpenSpec | gemini-3-flash-preview | 522 | 1411 | 962 | 373 | 2 | 2.07 |
| OpenSpec | gemini-3.5-flash | 557 | 1653 | 750 | 208 | 5 | 1.16 |
| Wayfinder (mattpocock/skills) | gemini-3-flash-preview | 663 | 0 | 1529 | 389 | 1 | 2.16 |
| Wayfinder (mattpocock/skills) | gemini-3.5-flash | 773 | 0 | 1172 | 288 | 3 | 1.60 |

## How turns ended

Share of user turns that ended with a text reply, an `ask_user` call, the per-turn step limit (`max_steps`, after which the harness forces one final text reply), or a context-length overflow. A high max_steps rate means the framework's protocol is step-hungry, which is a real cost, and those turns are scored as they are.

| Framework | Model | Turns | text | ask_user | max_steps | context_overflow | max_steps rate |
| :-- | :-- | --: | --: | --: | --: | --: | --: |
| Armature (OSS) | gemini-3-flash-preview | 324 | 102 | 212 | 10 | 0 | 3.1% |
| Armature (OSS) | gemini-3.5-flash | 324 | 237 | 83 | 4 | 0 | 1.2% |
| BMAD Method | gemini-3-flash-preview | 324 | 246 | 13 | 65 | 0 | 20.1% |
| BMAD Method | gemini-3.5-flash | 324 | 255 | 26 | 43 | 0 | 13.3% |
| Conductor (Gemini CLI extension) | gemini-3-flash-preview | 324 | 109 | 199 | 16 | 0 | 4.9% |
| Conductor (Gemini CLI extension) | gemini-3.5-flash | 324 | 116 | 198 | 10 | 0 | 3.1% |
| GitHub Spec Kit | gemini-3-flash-preview | 324 | 283 | 8 | 33 | 0 | 10.2% |
| GitHub Spec Kit | gemini-3.5-flash | 324 | 290 | 14 | 20 | 0 | 6.2% |
| Cline Memory Bank | gemini-3-flash-preview | 324 | 261 | 6 | 57 | 0 | 17.6% |
| Cline Memory Bank | gemini-3.5-flash | 324 | 269 | 17 | 38 | 0 | 11.7% |
| OpenSpec | gemini-3-flash-preview | 324 | 293 | 7 | 24 | 0 | 7.4% |
| OpenSpec | gemini-3.5-flash | 324 | 298 | 10 | 16 | 0 | 4.9% |
| Wayfinder (mattpocock/skills) | gemini-3-flash-preview | 324 | 237 | 51 | 36 | 0 | 11.1% |
| Wayfinder (mattpocock/skills) | gemini-3.5-flash | 324 | 243 | 54 | 27 | 0 | 8.3% |

## Judge reliability

- Criteria judged: 4788; not in the `opus-5.5-low` subsample (one vote, so no score): 4620; excluded for invalid votes (fewer than 2 valid): 22; tiebreaks: 3.
- `opus-5.5-low` judged a deterministic sample of (scenario, seed) cells. The sample is the same for every framework and model, and the judge score uses only those cells. The other primary judge voted on every criterion.
- The public code release ships Gemini REST judges only. Reproducing the cross-family (Claude) judge requires Anthropic API access, which the public release does not include.
- `gemini-3.1-pro-preview`: 168 votes, 22 invalid.
- `gemma-4-31b-it`: 3 votes, 0 invalid.
- `opus-5.5-low`: 168 votes, 0 invalid.
- Inter-judge Cohen's kappa (primary pair): 0.959 [0.927, 0.986] over 146 items in 7 scenario clusters; raw agreement 97.9%.
- Human calibration: **none yet.** Judge accuracy against human labels is unknown.

## Leakage audit

| Framework | Summary |
| :-- | :-- |
| Armature (OSS) | display_name=Armature (OSS), exclusive_3grams=0, exclusive_4grams=0, pack_chars=361276, shared_3grams=0, shared_4grams=0, units_with_3gram=0, units_with_4gram=0 |
| BMAD Method | display_name=BMAD Method, exclusive_3grams=2, exclusive_4grams=0, pack_chars=1432422, shared_3grams=2, shared_4grams=0, units_with_3gram=2, units_with_4gram=0 |
| Conductor (Gemini CLI extension) | display_name=Conductor (Gemini CLI extension), exclusive_3grams=0, exclusive_4grams=0, pack_chars=152546, shared_3grams=0, shared_4grams=0, units_with_3gram=0, units_with_4gram=0 |
| GitHub Spec Kit | display_name=GitHub Spec Kit, exclusive_3grams=1, exclusive_4grams=0, pack_chars=225545, shared_3grams=2, shared_4grams=0, units_with_3gram=2, units_with_4gram=0 |
| Cline Memory Bank | display_name=Cline Memory Bank, exclusive_3grams=0, exclusive_4grams=0, pack_chars=3871, shared_3grams=0, shared_4grams=0, units_with_3gram=0, units_with_4gram=0 |
| OpenSpec | display_name=OpenSpec, exclusive_3grams=0, exclusive_4grams=0, pack_chars=94758, shared_3grams=1, shared_4grams=0, units_with_3gram=1, units_with_4gram=0 |
| Wayfinder (mattpocock/skills) | display_name=Wayfinder (mattpocock/skills), exclusive_3grams=2, exclusive_4grams=0, pack_chars=215243, shared_3grams=2, shared_4grams=0, units_with_3gram=2, units_with_4gram=0 |

See `leakage.json` for top shared n-grams.

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
