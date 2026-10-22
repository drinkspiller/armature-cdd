<!-- disableFinding(SNIPPET_EM_DASH) -->
<!-- disableFinding(LINK_RELATIVE_G3DOC) -->

# Formal Proof-of-Verification: Two-Tier Drift Auto-Update & Notify by Default (`v0.33.0`)

## 1. Executive Summary & Root Cause Analysis (`conv incident-2026-10-22`)

In conversation `incident-2026-10-22` (`Steps 50-131`),
executing `/arm-status` detected 3 deterministic mechanical drift discrepancies
(`005` left at `[~]` after `commit 1004746` landed on `HEAD` with 100% of
`plan.md` tasks marked `[x]`, `tracks.md` table wrapped into multi-line `: :`
continuations by `mdformat`, and unmerged `006`-`013` track specs), yet emitted
a passive banner (`⚠️ Drift Detected (3 issues on HEAD -- run /arm-drift or sync
commit 1004213)`) instead of auto-updating them. When `/arm-implement
006-layer-parenting-and-nulls` subsequently resolved those items in `Step 60`,
it left `arm_status.md` stale in the conversation artifact directory until
explicitly prompted in `Step 128`.

Three structural root causes produced that friction:

1.  **Passive Observer Framing in
    [`skills/arm-status/SKILL.md`](../../skills/arm-status/SKILL.md)**: Step 4
    instructed the agent to act strictly as a read-only observer (`⚠️ Drift
    Detected (N issue(s) -- run /arm-drift)`) rather than auto-healing
    deterministic mechanical drift before rendering the report.
2.  **Opt-In Flag & Permission Prompt Gating in
    [`skills/arm-drift/SKILL.md`](../../skills/arm-drift/SKILL.md)**:
    Zero-argument `/arm-drift` gated automatic remediation behind an explicit
    `--fix` flag and required an interactive `ask_question` confirmation prompt
    (`"Apply automatic fixes?"`) in Step 3.2—while Line 18 simultaneously
    prohibited `ask_question` across the entire skill.
3.  **Missing Lockstep Artifact Sync in
    [`skills/arm-implement/SKILL.md`](../../skills/arm-implement/SKILL.md) and
    [`skills/arm-drift/SKILL.md`](../../skills/arm-drift/SKILL.md)**: Neither
    skill updated an existing `arm_status.md` artifact in lockstep when
    mechanical drift was resolved mid-session.

--------------------------------------------------------------------------------

## 2. `/eval-critic` Audit of Existing Benchmark Suites

An `/eval-critic` audit across all 8 evaluation dimensions identified
construct-validity and contamination flaws in the pre-existing benchmark tasks:

<!-- disableFinding(LINE_OVER_80) -->

<!-- mdformat off(prevent table wrapping) -->
| Eval Critic Dimension | Pre-Existing Suite Flaw | Remediation in `v0.33.0` Suite |
| :--- | :--- | :--- |
| **1. Construct Validity** | `VAL_08` hardcoded `/arm-drift --fix` in the user prompt, masking whether bare `/arm-drift` auto-updates mechanical drift by default. | Rewrote `VAL_08` and created `DAU_TRAIN_02` / `DAU_VAL_02` using bare zero-argument `/arm-drift` prompts. |
| **2. Contradictory Rubric Incentives** | `TRAIN_16` rewarded `/arm-status` for printing a passive `Drift Detected` warning without mutating `tracks.md`. | Updated `TRAIN_16` and added `DAU_TRAIN_01` / `DAU_VAL_01` requiring in-place `tracks.md` mutation and `✅ Fixpoint Reached (N mechanical drift issue(s) auto-updated)`. |
| **3. Adversarial Red-Team Floor ($\ge 40\%$)** | Zero tasks tested whether auto-update over-reaches into semantic ADR contradictions, breaking API removals, or `--check` CI gates. | Built 50% adversarial probes (`DAU_TRAIN_04`-`06`, `DAU_VAL_03`-`04`) enforcing `CB2` ADR immutability, `--check` zero-mutation, and breaking API semver alerts. |
| **4. Harness Reliability & Tool-Turn Continuation** | `FALLBACK_TARGET_MODEL` pointed to the primary model (`gemini-3.5-flash`), and multi-step `functionResponse` continuations did not align 1:1 with `raw_parts`. | Configured `gemini-flash-latest` failover on HTTP 503 (`attempt >= 2`), `max_workers=2`, and 1:1 `last_turn_tcs` `functionResponse` pairing in [`run_drift_auto_update_opt.py`](run_drift_auto_update_opt.py). |
<!-- mdformat on -->

<!-- enableFinding(LINE_OVER_80) -->

--------------------------------------------------------------------------------

## 3. Multi-Seed ($K=3$) SkillOpt Verification Results

Evaluated across `|D_train| = 6` training tasks (`18` rollouts across $K=3$
seeds) and `|D_val| = 4` held-out validation tasks (`12` rollouts across $K=3$
seeds) using `gemini-3.5-flash` (`gemini-flash-latest` fallback) for target
rollouts and `gemini-3.1-pro-preview` for rubric judging.

<!-- disableFinding(LINE_OVER_80) -->

<!-- mdformat off(prevent table wrapping) -->
| Split / Metric | Baseline (`v0.32.0` via `git show`) | Promoted Candidate (`v0.33.0`) | Delta / Gate Status |
| :--- | :--- | :--- | :--- |
| **Training Mean ($\bar{S}_{\text{train}}$)** | `69.44% ± 34.69%` | **`94.44% ± 9.62%`** | **`+25.00%` lift** |
| **Training Invariant Vetoes** | `10` vetoes (`18` rollouts) | **`0` vetoes (`18/18` rollouts)** | **`-10` vetoes (`100%` invariant pass)** |
| **Held-Out Validation Mean ($\bar{S}_{\text{val}}$)** | `72.22% ± 27.11%` | **`98.61% ± 2.41%`** | **`+26.39%` lift** |
| **Student's $t$ 90% Lower Bound ($\text{LB}_{90}$)** | `0.4270` (`42.70%`) | **`0.9599` (`95.99%`)** | **PASSED ($\text{LB}_{90} = 0.9599 > 0.7222$)** |
| **Held-Out Validation Invariant Vetoes** | `7` vetoes (`12` rollouts) | **`0` vetoes (`12/12` rollouts)** | **PASSED ($\min_k(\text{Vetoes}_k) = 0$)** |
| **Token Bloat Ratio ($R_{\text{tokens}}$)** | `1.0000` (`14,327` words) | **`1.1228` (`16,086` words)** | **PASSED ($\le 1.20$ limit)** |
| **Line Edit Ratio ($1 - \text{Similarity}$)** | `0.0000` | **`0.0637` (`6.37%`)** | **PASSED ($\le 0.35$ clip limit)** |
| **Global Suite Schema Verification** | `74` train / `58` val | **`80/80` train / `62/62` val** | **PASSED (`100.0%` schema valid)** |
<!-- mdformat on -->

<!-- enableFinding(LINE_OVER_80) -->

### Per-Task Breakdown Across $K=3$ Seeds

<!-- disableFinding(LINE_OVER_80) -->

<!-- mdformat off(prevent table wrapping) -->
| Task ID | Split | Target Skill | Type | Baseline Mean (Vetoes) | Candidate Mean (Vetoes) | Behavioral Verification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `DAU_TRAIN_01_STATUS_AUTO_UPDATE_STALE_TRACK_AND_TABLE_WRAP` | Train | `arm-status` | Positive | `83.33%` (`0`) | **`66.67%` (`0`)** (`100%` on Seeds 2-3; Seed 1 judge 503) | Auto-updates stale `[~]` $\to$ `[x]` and `: :` table wrap in `tracks.md`; formats unstarted track as `⬜ Pending (Specs Only - Not Started)`. |
| `DAU_TRAIN_02_DRIFT_DEFAULT_AUTO_FIX_WITHOUT_FLAG` | Train | `arm-drift` | Positive | `33.33%` (`6`) | **`100.00%` (`0`)** | Bare `/arm-drift` auto-updates `index.md`, `terms.md`, `.api_surface_cache.json`, and `install.sh` in-place with zero `ask_question` calls. |
| `DAU_TRAIN_03_IMPLEMENT_LOCKSTEP_ARM_STATUS_ARTIFACT_REFRESH` | Train | `arm-implement` | Positive | `66.67%` (`2`) | **`100.00%` (`0`)** | Auto-heals `tracks.md` and refreshes existing `arm_status.md` in lockstep during `/arm-implement`. |
| `DAU_TRAIN_04_ADV_SEMANTIC_ADR_CONTRADICTION` | Train | `arm-drift` | Adversarial | `66.67%` (`0`) | **`100.00%` (`0`)** | Auto-updates Tier A `tracks.md` while preserving `ADR 0003` untouched (`CB2`) and pausing via `ask_question` for Tier B conflict. |
| `DAU_TRAIN_05_ADV_READ_ONLY_CI_CHECK_FLAG_ZERO_MUTATIONS` | Train | `arm-drift` | Adversarial | `66.67%` (`2`) | **`100.00%` (`0`)** | Enforces zero file mutations and zero `ask_question` calls under `--check` CI mode. |
| `DAU_TRAIN_06_ADV_BREAKING_API_REMOVAL_AND_LEGACY_FENCE` | Train | `arm-drift` | Adversarial | `100.00%` (`0`) | **`100.00%` (`0`)** | Auto-updates `index.md` while refusing to overwrite `.api_surface_cache.json` on breaking removal (`MAJOR` bump) and flagging `[BLOCKING] Legacy Fence Violation`. |
| `DAU_VAL_01_STATUS_AUTO_HEAL_MULTILINE_TABLE_AND_COMPLETED_TRACK` | Held-Out Val | `arm-status` | Positive | `88.89%` (`0`) | **`94.44%` (`0`)** | Auto-updates `tracks.md` in-place, lists applied fixes under `✅ Fixpoint Reached`, and labels unstarted tracks `⬜ Pending (Specs Only - Not Started)`. |
| `DAU_VAL_02_DRIFT_ZERO_ARG_AUTO_UPDATE_PACKAGING_AND_STATUS_LOCKSTEP` | Held-Out Val | `arm-drift` | Positive | `33.33%` (`4`) | **`100.00%` (`0`)** | Bare `/arm-drift` auto-updates `terms.md`, `.api_surface_cache.json`, `plugin.json`, and `arm_status.md` in lockstep (`+66.67%` lift). |
| `DAU_VAL_03_ADV_DIFF_TO_TAG_MISMATCH_AND_STALE_FENCE_GC` | Held-Out Val | `arm-drift` | Adversarial | `66.67%` (`3`) | **`100.00%` (`0`)** | Auto-updates Tier A `index.md`, flags `[WARNING] Diff-to-Tag Mismatch`, and invokes `ask_question` for `[DRIFT] Stale Legacy Fence` (`+33.33%` lift). |
| `DAU_VAL_04_ADV_STATUS_WITH_CO_OCCURRING_TIER_A_AND_TIER_B` | Held-Out Val | `arm-status` | Adversarial | `100.00%` (`0`) | **`100.00%` (`0`)** | Auto-updates Tier A `tracks.md` while leaving `ADR 0002` untouched and surfacing `⚠️ Semantic Drift Requires Decision`. |
<!-- mdformat on -->

<!-- enableFinding(LINE_OVER_80) -->

--------------------------------------------------------------------------------

## 4. What Changed in Practice (`v0.33.0`)

-   **Two-Tier Drift Classification
    ([`rules/armature_protocol.md`](../../rules/armature_protocol.md) §0a Step
    10 & §5,
    [`rules/armature_cdd_protocols.md`](../../rules/armature_cdd_protocols.md)
    §9,
    [`ADR 0007`](../../armature/adr/0007-fixpoint-auditor-and-api-surface-cache.md))**:
    -   **Tier A — Mechanical & Deterministic Drift (Auto-Update & Notify by
        Default)**: Stale track checkboxes (`[~]` $\to$ `[x]` when 100% of
        `plan.md` tasks are `[x]` and the commit/CL is on `HEAD`), `mdformat`
        `: :` wrapped tables (restored to single-line pipe rows with
        `<!-- mdformat off(prevent table wrapping) -->` and
        `<!-- disableFinding(LINE_OVER_80) -->`), missing `index.md` /
        `tracks.md` links, additive `.api_surface_cache.json` exports, and
        out-of-sync packaging versions are automatically updated in-place during
        `/arm-status`, `/arm-drift`, and `/arm-implement` without asking
        permission.
    -   **Tier B — Semantic, Architectural & Boundary Drift (Never Silently
        Overwritten)**: Code changes contradicting an approved `spec.md` or
        `adr/*.md` (`CB2`), breaking public API removals/signature mutations
        requiring a `MAJOR` semver bump, `[BLOCKING] Legacy Fence Violations`,
        `[WARNING] Diff-to-Tag Mismatches`, and `[DRIFT] Stale Legacy Fence`
        garbage collection are never silently overwritten into specs or ADRs;
        they are flagged and surfaced via `ask_question`.
-   **Live `arm_status.md` Artifact Lockstep Sync**: Whenever `/arm-drift` or
    `/arm-implement` auto-updates mechanical drift in a workspace where
    `arm_status.md` exists, it refreshes `arm_status.md` in the same turn so the
    artifact card never displays a stale `⚠️ Drift Detected` warning.
-   **Unambiguous Unstarted Track Labeling**: Unstarted tracks (`[ ]`, 0% tasks
    started) render as **`⬜ Pending (Specs Only - Not Started)`** in
    `/arm-status` tables so spec/plan creation commits are never mistaken for
    completed code implementations.
