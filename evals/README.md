# Armature Evaluation Suite (v2 / v3)

Automated evaluation harnesses to objectively test, benchmark, and calibrate
Armature and alternative Context-Driven Development (CDD) and Spec-Driven
Development (SDD) frameworks. The suite measures how agent frameworks handle
real-world software engineering friction, specification gating, surgical hotfix
velocity, architectural drift governance, state safety, and multi-session
context continuity inside real Git sandboxes.

--------------------------------------------------------------------------------

## Making Updates: Light Smoke Run, Full Release Run & Updating Docs

Whenever modifying any Armature rule (`rules/*.md`) or skill
(`skills/*/SKILL.md`), follow this 3-stage evaluation and documentation update
workflow:

### Stage 1: Fast Smoke Gate During Iteration (~10–12 min)

Use the smoke suite while iterating on prompt, rule, or skill changes before
running a full multi-seed comparative benchmark:

1.  **Refresh working-tree pack lockfile & run zero-leakage + unit-test gates**:

    ```bash
    # Refresh local working-tree pack lockfile (registry_dev.json)
    CDD_BENCH_ARMATURE_OSS_ROOT="$PWD" python3 evals/cdd_sdd_benchmark/fetch_packs.py \
      --registry evals/cdd_sdd_benchmark/frameworks/registry_dev.json \
      --only armature_oss_dev

    # Verify 192 unit tests and zero 1-gram / 3-gram / 4-gram scenario leakage
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s evals/cdd_sdd_benchmark/tests
    CDD_BENCH_ARMATURE_OSS_ROOT="$PWD" python3 evals/cdd_sdd_benchmark/leakage_audit.py \
      --registry evals/cdd_sdd_benchmark/frameworks/registry_dev.json
    ```

2.  **Run targeted SkillOpt validation (when changing a specific skill
    contract)**:

    ```bash
    python3 evals/skillopt/run_optimizer.py --verify_schema
    python3 evals/skillopt/run_interview_format_opt.py --phase eval --seeds 3 --workers 6
    ```

3.  **Run the 90-rollout stratified CI smoke gate** (`15` core scenarios x `6`
    frameworks x `1` seed, enforcing `<= 3.0 pp` per-pillar regression and `0`
    n-gram leakage via `--smoke-gate`):

    ```bash
    CDD_BENCH_ARMATURE_OSS_ROOT="$PWD" \
      ./evals/cdd_sdd_benchmark/release.sh v3-smoke-$(date +%Y%m%d) --smoke
    ```

### Stage 2: Full Comparative Release Evaluation (Before Releasing)

Once the smoke gate passes, run a fresh pre-registered full benchmark across all
60 scenarios (`30` `core` + `30` `heldout` — never read `tasks/heldout_v2.jsonl`
prose during prompt authoring, and never splice cells across `--run-id`s):

1.  **Pre-register pass/fail gates** in
    `evals/cdd_sdd_benchmark/results/<RUN_ID>/PREREGISTRATION.md` before
    launching (specifying target slice, seeds, primary `Outcome Score` metric,
    and decision thresholds).
2.  **Run the full 6-stage `--publish` release pipeline** (all frameworks x 60
    scenarios x 3 seeds on `gemini-3.5-flash`, blinded cross-family judge panel,
    public reports, and calibration):

    ```bash
    CDD_BENCH_ARMATURE_OSS_ROOT="$PWD" ./evals/cdd_sdd_benchmark/release.sh <RUN_ID>
    ```

3.  **Verify strict run provenance and pack digests**:

    ```bash
    CDD_BENCH_ARMATURE_OSS_ROOT="$PWD" \
      python3 evals/cdd_sdd_benchmark/run_benchmark.py verify \
      --out /tmp/armature_bench/<RUN_ID> --strict-config
    ```

### Stage 3: Updating Repository Documentation with New Eval Results

After a full `--publish` run passes `verify --strict-config`, update repository
documentation in lockstep:

1.  **Stage verified public run artifacts**: Commit
    `evals/cdd_sdd_benchmark/results/<RUN_ID>/public/{manifest.json,stats.json,leakage.json,report.md}`.
2.  **Update `README.md`**: Refresh `## Evaluation Results & Benchmark`
    (leaderboard table, Equivalence Tiers, 95% two-level cluster-bootstrap CIs,
    per-pillar scores, and token metrics in strict descending order of score)
    from `results/<RUN_ID>/public/report.md`.
3.  **Update `evals/README.md` & `CHANGELOG.md`**: Update the canonical
    `<RUN_ID>` pointers in `evals/README.md`, add the release entry under
    `## [<VERSION>] - YYYY-MM-DD` in `CHANGELOG.md` (matching `VERSION=` in
    `install.sh` and `"version"` in `plugin.json`), and include an
    `## Evaluation & Benchmark Results` summary in the PR description.

--------------------------------------------------------------------------------

## Evaluation Architecture & Scientific Guardrails

The benchmark (`evals/cdd_sdd_benchmark/`) replaces the legacy text-only v1
runner (`evals/cdd_sdd_benchmark/legacy_v1/`) with a hermetic, tool-using
evaluation harness backed by 192 unit tests (`evals/cdd_sdd_benchmark/tests/`):

### 1. Vendored Verbatim Upstream Packs & Leakage Gate

All candidate frameworks (`Armature (OSS)`, `Wayfinder`, `BMAD Method`,
`Cline Memory Bank`, `GitHub Spec Kit`, `OpenSpec`, and `Conductor`) are loaded
from verbatim upstream skill and rule files pinned in
`frameworks/packs.lock.json` and `frameworks/packs_dev.lock.json` (verified via
`fetch_packs.py --verify --deep`). Before scoring, `leakage_audit.py` audits
distinctive 1-gram scenario tokens plus 3-gram and 4-gram overlap between every
framework pack and all 455 scenario text units (`0` shared 1-grams, `0` shared
3-grams, and `0` shared 4-grams for `Armature (OSS)`).

### 2. Sandboxed Multi-Turn Tool Execution

Each rollout executes in an isolated temporary Git repository
(`bench/sandbox.py`) seeded with a realistic brownfield fixture (`tasks/`) and
structured tools (`read_file`, `write_file`, `edit_file`, `list_dir`, `search`,
`run_command`, and `ask_user`) paired with a deterministic user simulator.

### 3. Deterministic Outcome Score Primary + Cross-Family Judge Secondary

-   **Primary Metric (`Outcome Score`)**: Programmatic sandbox checks across 60
    scenarios (`bench/checks.py`) verifying file existence, AST/regex
    invariants, `git status` / `git diff` bounds, command execution logs, and
    turn behavior.
-   **Secondary Metric (`Cross-Family Judge Score`)**: Deep regex blinding
    (`bench/blinding.py`, 722 framework-identifying patterns scrubbed across
    messages, tool calls, and diffs) followed by a cross-family judge panel
    (`gemini-3.1-pro-preview` + `opus-5.5-low` primary, with `gemma-4-31b-it`
    tiebreak on disagreement). Target rollout models (`gemini-3.5-flash`,
    `gemini-3-flash-preview`) never judge, and any run where a primary judge has
    `> 5%` invalid votes automatically emits an `INCOMPLETE PRIMARY JUDGE PANEL`
    disclosure banner.

### 4. Cluster-Bootstrap Inference, Equivalence Tiers & Held-Out Split

-   **60 Scenarios (`30` Core + `30` Held-Out)**: Evaluates generalization from
    the 30 core scenarios (`tasks/core_v2.jsonl`) to 30 independently authored
    held-out scenarios (`tasks/heldout_v2.jsonl`) and reports lead shrinkage.
-   **Two-Level Cluster Bootstrap**: Computes 95% confidence intervals and
    paired framework differences across 10,000 two-level cluster-bootstrap
    resamples (resampling scenarios, then seeds within scenario) and groups
    statistically indistinguishable frameworks into **Equivalence Tiers**
    (`bench/stats.py`).
-   **Separated Cost & Error Accounting**: Reports `input_tokens`, visible
    `output_tokens` (`candidatesTokenCount`), `thinking_tokens`, and
    `cached_tokens` separately. Retries transient API errors with exponential
    backoff and invalidates any run whose harness error rate exceeds `5%` in any
    framework x model cell (`run_benchmark.py verify`).

--------------------------------------------------------------------------------

## The 5 Core Evaluation Pillars (60 Scenarios: 30 Core + 30 Held-Out)

1.  **Specification & Plan Gating (`spec_gating`, 12 scenarios)**: Evaluates
    codebase inspection, backward-compatibility analysis, wire-format edge
    cases, clarifying question precision, and transitions from specification
    sign-off to implementation.
2.  **Surgical Velocity & Token Efficiency (`surgical_velocity`, 12
    scenarios)**: Measures fast-path execution on micro-hotfixes (`<= 5` lines
    of code across `<= 2` files), ensuring minimal diff scope and zero
    bureaucratic spec/track ceremony.
3.  **Code & Doc Drift Governance (`drift_governance`, 12 scenarios)**: Assesses
    detection and resolution of contradictions between uncommitted workspace
    diffs, Architecture Decision Records (`adr/`), API surface baselines, and
    domain glossaries (`terms.md`).
4.  **State Safety & Execution Guardrails (`state_safety`, 12 scenarios)**:
    Tests refusal of autonomous destructive commands (`DROP TABLE`,
    `kubectl drain`, `terraform destroy`, unshielded bulk `DELETE`) while
    verifying safe read-only pre-checks (`SELECT COUNT(*)`) and runbook
    documentation.
5.  **Context Continuity & Detour Resilience (`context_continuity`, 12
    scenarios)**: Evaluates preservation of settled decisions across technical
    detours, session handoffs, and multi-turn resumption using on-disk project
    context.

--------------------------------------------------------------------------------

## Directory Layout

```
evals/
├── README.md                           # Unified evaluation guide & update runbook
├── cdd_sdd_benchmark/                  # Track 1: Sandboxed CDD/SDD Benchmark
│   ├── DESIGN.md                       # Architectural specification
│   ├── METHODOLOGY.md                  # Scoring, blinding, bootstrap, and threat model
│   ├── run_benchmark.py                # Unified CLI (run, verify, judge, report, calibrate)
│   ├── release.sh                      # Single-command 6-stage release & smoke script
│   ├── smoke_config.json               # 90-rollout CI smoke gate configuration
│   ├── fetch_packs.py                  # Verbatim git/local pack fetcher & SHA lockfile verifier
│   ├── leakage_audit.py                # Automated 1-gram/3-gram/4-gram pack-vs-scenario audit
│   ├── bench/                          # Core sandbox, runner, checks, blinding, judge, stats
│   ├── frameworks/                     # Public/dev registries & pack SHA lockfiles
│   ├── tasks/                          # 30 core (core_v2.jsonl) + 30 held-out (heldout_v2.jsonl)
│   ├── calibration/                    # 100-item blinded calibration sampler, auto-labeler & kappa
│   ├── results/v3-full-20261107/       # Canonical v0.35.0 public reports, stats, and leakage JSON
│   ├── results/v2-full-20261104/       # Historical v0.34.4 public baseline artifacts
│   ├── tests/                          # 192 stdlib unit tests covering all invariants
│   └── legacy_v1/                      # Archived v1 text-only runner & historical snapshots
└── skillopt/                           # Track 2: Prompt optimization & validation loop
    ├── README.md                       # Optimizer usage and validation gates
    ├── run_optimizer.py                # Automated prompt mutation engine & schema verifier
    ├── run_interview_format_opt.py     # Multi-seed protocol-level interview layout evaluator
    ├── run_trajectory_eval.py          # Multi-turn decision-tree trajectory evaluator
    └── tasks/                          # Disjoint training & held-out validation tasks
```

--------------------------------------------------------------------------------

## Step-by-Step Benchmark CLI Reference

`./evals/cdd_sdd_benchmark/release.sh <RUN_ID> [--smoke]` automates all 6 stages
below; individual subcommands can also be run directly:

```bash
# 1. Unit tests & n-gram leakage audit
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s evals/cdd_sdd_benchmark/tests
PYTHONDONTWRITEBYTECODE=1 python3 evals/cdd_sdd_benchmark/leakage_audit.py \
  --out-json /tmp/armature_bench/v3-full-20261107/leakage.json

# 2. Execute sandboxed rollouts (resumable; --smoke runs the 90-cell smoke slice)
PYTHONDONTWRITEBYTECODE=1 python3 evals/cdd_sdd_benchmark/run_benchmark.py run \
  --run-id v3-full-20261107 --seeds 3 --publish --concurrency 16 \
  --out /tmp/armature_bench/v3-full-20261107

# 3. Retry transient harness errors & verify strict config/pack provenance
PYTHONDONTWRITEBYTECODE=1 python3 evals/cdd_sdd_benchmark/run_benchmark.py run \
  --run-id v3-full-20261107 --out /tmp/armature_bench/v3-full-20261107 \
  --retry-harness-errors --concurrency 8
PYTHONDONTWRITEBYTECODE=1 python3 evals/cdd_sdd_benchmark/run_benchmark.py verify \
  --out /tmp/armature_bench/v3-full-20261107 --strict-config

# 4. Blinded cross-family judge ensemble
PYTHONDONTWRITEBYTECODE=1 python3 evals/cdd_sdd_benchmark/run_benchmark.py judge \
  --out /tmp/armature_bench/v3-full-20261107

# 5. Render public statistical report (with executive summary)
PYTHONDONTWRITEBYTECODE=1 python3 evals/cdd_sdd_benchmark/run_benchmark.py report \
  --out /tmp/armature_bench/v3-full-20261107 --public-only \
  --stage-to evals/cdd_sdd_benchmark/results/v3-full-20261107/public

# 6. Automated calibration sampling, labeling & inter-rater agreement (kappa)
PYTHONDONTWRITEBYTECODE=1 python3 evals/cdd_sdd_benchmark/run_benchmark.py calibrate \
  --out /tmp/armature_bench/v3-full-20261107 \
  --stage-to evals/cdd_sdd_benchmark/results/v3-full-20261107 \
  --labeler-model gemini-3.1-pro-preview --concurrency 10
```
