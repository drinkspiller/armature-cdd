# CDD / SDD Evaluation Benchmark v2 — Methodology & Limitations

This document describes the design, execution protocol, statistical methodology, and known limitations of the v2 Context-Driven Development (CDD) and Spec-Driven Development (SDD) benchmark (`evals/cdd_sdd_benchmark/`).

The v2 benchmark replaces the legacy v1 harness (`legacy_v1/`) from the ground up to address twelve methodological flaws identified during an independent audit of the v1 evaluation.

---

## 1. Why v1 Was Archived (`legacy_v1/`)

The v1 harness exhibited twelve structural validity defects that made its headline leaderboard scores scientifically uninterpretable:

| # | v1 Defect | Impact on v1 Scores | v2 Remediation |
| :--- | :--- | :--- | :--- |
| 1 | **Hand-authored strawman system prompts** | Competitor frameworks were represented by ~900–1,400 byte author-written summaries inside `run_benchmark.py`, while Armature received a 6,000+ byte prompt tailored to the scenario taxonomy. | Every framework loads its **actual shipped prompt pack** from a pinned upstream git commit (`frameworks/packs.lock.json`) or repository path (`frameworks/packs_internal.lock.json`) via `fetch_packs.py`. |
| 2 | **Single-turn text generation instead of an agent loop** | Models had no tools, no filesystem, no shell, and no multi-session boundary; the benchmark graded what a model *promised* to do in prose rather than what an agent actually did. | Each rollout runs a multi-turn, multi-session tool-calling loop (`bench/agent_loop.py`) inside an isolated git + SQLite + mock-CLI sandbox (`bench/sandbox.py`). |
| 3 | **100% LLM-as-judge scoring with zero outcome checks** | Formatting compliance and verbose markdown checklists were rewarded even when no files were inspected or modified. | **Deterministic outcome checks (`bench/checks.py`) are the primary metric (`outcome_score`).** The LLM judge (`judge_score`) is secondary and always reported separately. |
| 4 | **Criteria written in Armature's own vocabulary** | v1 rubrics explicitly demanded Armature-named concepts (` Blast Radius `, ` Need More Context `, ` legacy_fences `, ` Impact Table `). | Core (`tasks/core_v2.jsonl`, 30 scenarios) and held-out (`tasks/heldout_v2.jsonl`, 30 scenarios) tasks use framework-neutral criteria verified by an automated n-gram leakage audit (`leakage_audit.py`). |
| 5 | **No held-out scenario set** | Prompts and scenarios were co-developed in the same repository without a blind evaluation split. | 30 held-out scenarios (`tasks/heldout_v2.jsonl`) were authored in an isolated worker session blocked from reading any framework prompt pack (`tasks/HELDOUT_AUTHORING.md`). |
| 6 | **Self-preference and unblinded judging** | The target model (`gemini-3-flash-preview`) graded its own outputs, and transcripts contained literal `armature/`, `/arm-new-track`, and `spec.md` strings. | Target models never judge (`assert_not_target`). Transcripts pass through longest-first regex scrubbing (`bench/blinding.py`) and omit `read_file`/`list_dir`/pack-tool bodies before reaching a **cross-family judge panel** (`gemini-3.1-pro-preview` + `opus-5.5-low`, with `gemma-4-31b-it` as tiebreak). |
| 7 | **Zero human calibration of the LLM judge** | v1 reported no human agreement metric or error bars on judge reliability. | `calibration/sample_for_labeling.py` exports a blinded 100-item human labeling page, and `calibration/compute_agreement.py` computes judge-vs-human and inter-judge Cohen's $\kappa$ with 95% bootstrap confidence intervals. |
| 8 | **Single rollout ($n = 1$) and invalid i.i.d. binomial CIs** | v1 treated 72 correlated criteria across 20 scenarios from a single seed as independent Bernoulli trials. | Publishable runs execute $k \ge 3$ seeds across 2 target models (`gemini-3-flash-preview` and `gemini-3.5-flash`) and compute **scenario-cluster bootstrap** 95% confidence intervals (10,000 resamples over scenarios), paired bootstrap differences, Holm-Bonferroni adjusted $p$-values, and TOST equivalence tests ($\pm 2\%$). |
| 9 | **Selective re-runs and cross-model result splicing** | v1 spliced new single-framework runs into frozen competitor JSON files and mixed models across frameworks. | `run_benchmark.py verify --strict-config` enforces a single `config_hash` across the entire $\text{frameworks} \times \text{scenarios} \times \text{seeds} \times \text{models}$ matrix before `report` will render a publishable report. |
| 10 | **API transport failures scored as `0.0%` framework failures** | Empty HTTP responses (`finishReason=STOP` with 0 tokens) were recorded as `0/4` rubric failures for competitors. | `gemini_client.py` retries transient transport errors and empty responses with seed perturbation; any rollout that still fails is marked `status="harness_error"`, excluded from framework denominators, and reported in a dedicated **Harness Errors & Data Hygiene** table. A cell exceeding 5% harness errors is marked `INVALID`. |
| 11 | **Input + history tokens misreported as response length** | v1 plotted `totalTokenCount` (which sums system prompt, multi-turn history, and output) as "avg tokens per turn". | `schema.Usage` tracks `input_tokens`, `output_tokens`, `thinking_tokens`, `cached_tokens`, `api_calls`, and `wall_time_s` separately, plus retry overhead in `retry_usage`. |
| 12 | **Single-number composite ranking without equivalence tiers** | v1 ranked frameworks `#1` through `#9` on point estimates whose confidence intervals overlapped by $\pm 5\text{--}10\%$. | Reports group frameworks into **equivalence tiers** (frameworks whose paired scenario-cluster bootstrap 95% CI against the top scorer includes 0) and never assign ordinal rank numbers (`#1`, `#2`) or merge outcome and judge scores into a single composite rank. |

---

## 2. Evaluated Frameworks & Real Prompt Packs

Every evaluated framework is loaded from its actual shipped files and locked by SHA-256 digest:

### Public Frameworks (`frameworks/registry.json` & `frameworks/packs.lock.json`)

1. **Armature OSS (`armature_oss`)** — `https://github.com/drinkspiller/armature-cdd` (`b9ca72bf`)
2. **GitHub Spec Kit (`github_spec_kit`)** — `https://github.com/github/spec-kit` (`f42ac92b`), including `.specify/` templates and `scripts/bash/*.sh` CLI tools
3. **OpenSpec (`openspec`)** — `https://github.com/Fission-AI/OpenSpec` (`c5accbe1`), rendered via the upstream TypeScript template generators (`opsx-*` skills and `.claude/commands/opsx/*.md`)
4. **BMAD-METHOD (`bmad_method`)** — `https://github.com/bmad-code-org/BMAD-METHOD` (`0fd9bf46`), including core agent definitions and workflow instructions
5. **Cline Memory Bank (`memory_bank`)** — `https://github.com/cline/prompts` (`054ef9b9`), `.clinerules/memory-bank.md`
6. **Canonical Conductor (`canonical_conductor`)** — `https://github.com/gemini-cli-extensions/conductor` (`329cbbff`), `commands/conductor/*.toml`
7. **Wayfinder (`wayfinder`)** — `https://github.com/wayfinder-ai/wayfinder` (`481f383e`), `.wayfinder/` rules and skills

### Google-Internal Frameworks (`frameworks/registry_internal.json` & `frameworks/packs_internal.lock.json`)


Public reports (`--visibility public`) exclude internal frameworks and verify that zero internal identifiers or paths appear in the generated artifacts.

---

## 3. Agentic Sandbox & Multi-Session Execution (`bench/sandbox.py`, `bench/agent_loop.py`)

Each rollout creates an isolated temporary workspace under `/tmp/cddbench/sbx_<random>/work` (an opaque directory prefix that shares no tokens with any framework name) initialized as a real Git repository with an initial commit (`baseline`), an in-process SQLite database (`sandbox.db`), and any scenario-defined fixture files.

During each turn, the target model interacts with the sandbox through five tools:
- `read_file(path, start_line, end_line)`
- `write_file(path, content)`
- `edit_file(path, old_str, new_str)`
- `list_dir(path)`
- `run_command(command)`
- `ask_user(question, options)`

### Command Execution Policy
- **Safe read-only and local inspection commands** (`git status/diff/log/show`, `ls`, `cat`, `head`, `tail`, `wc`, `sqlite3 -readonly`, `python3 -m unittest`, `pytest`) execute against the real sandbox filesystem.
- **Framework pack CLI scripts** declared in `pack_commands` (such as Spec Kit's `create-new-feature.sh`, `setup-plan.sh`, `check-prerequisites.sh`, and `update-agent-context.sh`) execute in bash inside the sandbox with `source="pack_tool"`.
- **Scenario mock commands** (such as `kubectl`, `terraform`, `gcloud`, `psql`, `redis-cli`, `curl`, `systemctl`, or custom test runners) match ordered regex rules in `scenario.mocks`, recording whether a destructive command or database mutation was executed (`executed=True`, `destructive=True`, `rows_changed`).
- **Turn budget and graceful wrap-up:** Each turn allows up to `MAX_STEPS_PER_TURN = 40` tool-calling steps. If the model is still calling tools at step 39, step 40 appends a wrap-up prompt with tool declarations kept in `AUTO` mode (allowing `ask_user`, which ends the turn, while refusing non-terminal tools once before requesting a final text response) so models that emit thought signatures alongside tool calls never fail with HTTP 400.

---

## 4. Primary Metric: Deterministic Outcome Checks (`bench/checks.py`)

Every scenario defines at least two deterministic checks evaluated directly against the post-rollout sandbox state, git diff, SQLite tables, and structured action log:

1. `file_exists`, `file_not_exists`, `file_Unchanged`, `no_files_modified_outside`
2. `file_contains`, `file_not_contains`
3. `git_clean_or_scoped`, `diff_scope` (`max_files`, `max_changed_lines`, `min_changed_lines`, `forbidden_globs`)
4. `command_not_executed`, `command_executed`, `command_order`
5. `asked_clarifying_question` (`before_any_write`, `before_destructive_command`, `min_questions`, `max_questions`)
6. `planning_artifact_written` (checks whether any non-source Markdown/YAML/JSON/TXT artifact was created or updated prior to source edits, with optional `regex` content assertions and zero hardcoded framework directory names)
7. `db_state` (SQL query assertions and `max_rows_affected_in_any_single_command`)
8. `json_Yaml_valid`, `test_suite_passes`
9. `session_Picked_up_state` (verifies that Session 2 read an artifact created in Session 1 before modifying source files)

The **outcome score** for a rollout is the fraction of deterministic checks passed. It is the **primary metric** of the benchmark.

---

## 5. Secondary Metric: Blinded Cross-Family Judge Ensemble (`bench/judge.py`, `bench/blinding.py`)

Each scenario also defines up to three qualitative `judge_criteria` for properties that cannot be reduced to a regex or file check (for example, whether a clarifying question addressed the actual ambiguity in the prompt, or whether a handoff note captured the root cause discovered in Session 1).

### Blinding Pipeline
Before any judge sees a rollout:
1. The judge receives the scenario description, the authoritative harness action log, and the conversation transcript containing only `turn.user_raw` (never host-expanded slash command bodies).
2. `read_file`, `list_dir`, and `pack_tool` outputs are replaced with `-> (N chars returned; content omitted)` so framework skill files and script banners cannot leak into the transcript.
3. `blinding.blind()` scrubs all framework names, slash commands, context directories, and distinctive skill prefixes (`arm-`, `speckit-`, `opsx-`, `bmad-`, `conductor:`, `wayfinder`, `internal_sdd-`) longest-first and case-insensitively into neutral placeholders (`[FRAMEWORK]`, `[COMMAND]`, `[CONTEXT_DIR]`, `[CONTEXT_FILE]`).

### Cross-Family Panel & Tiebreak
- **Primary Judge 1 (Google Gemini family):** `gemini-3.1-pro-preview` via the Gemini REST API (`temperature=0.0`, `seed=0`, `responseMimeType="application/json"`).
- **Primary Judge 2 (Anthropic Claude family):** `opus-5.5-low` (`Claude Opus 5.5 (Low)`, enum `MODEL_PLACEHOLDER_M369`), resolved via `subagent_router` (`mms.models.select` with quota guard) and executed as an isolated host-agent conversation via `host-agent-cli` on a deterministic 50% stratified subsample of `(scenario_id, seed)` cells shared identically across all frameworks and models. Every conversation is audited post-hoc via `audit_host_transcript` (any tool call other than reading `prompt.txt` and writing `verdict.json` voids the verdict) and verified against the SQLite trajectory metadata via `mms.transcript.trajectory_models`.
- **Tiebreak Judge (Google Gemma family):** `gemma-4-31b-it` via REST, invoked **only** when both primary judges return valid verdicts that disagree (`True` vs `False`).
- **Panel collision guard:** Every judge call records its served model version in `RESOLVED_VERSIONS` and raises `PanelCollisionError` if any alias resolves to another panel member or to a target/Flash model.

---

## 6. Statistical Aggregation (`bench/stats.py`)

- **Scenario-cluster bootstrap:** All confidence intervals resample scenarios with replacement ($B = 10,000$, deterministic RNG seed), preserving correlation across seeds, criteria, and checks within each scenario.
- **Paired comparisons & multiplicity control:** Pairwise differences $\Delta(A, B)$ are computed on matched `(scenario_id, seed)` cells, with two-sided paired bootstrap $p$-values adjusted across all pairs using the **Holm-Bonferroni** step-down procedure.
- **Equivalence testing (TOST) & Tiers:** Two frameworks are declared statistically equivalent within $\pm \delta = \pm 2.0\%$ when the 90% paired bootstrap confidence interval for $\Delta(A, B)$ lies entirely within $[-0.02, +0.02]$. Frameworks whose 95% paired difference CI against the top-scoring framework includes $0$ share **Tier 1**.

---

## 7. Known Limitations

1. **Claude judge host environment:** Because no standalone Anthropic API key is provisioned in this environment, the `opus-5.5-low` judge executes inside a host-agent agent-host conversation that injects the operator's global rules and memory index. Although the judge prompt instructs the model to ignore all external rules and every conversation transcript is audited to ensure no files outside `prompt.txt` and `verdict.json` are accessed, residual familiarity with Armature conventions cannot be completely ruled out. Furthermore, host-dispatched conversations use the host's default sampling temperature rather than `temperature=0.0`.
2. **Subsampled second judge:** To respect Anthropic quota limits (`opus-5.5-low`), the second primary judge evaluates a deterministic 50% stratified subsample of `(scenario_id, seed)` cells. Because the subsample key depends only on `(run_id, scenario_id, seed)`, every framework and target model is evaluated on the exact same subset of cells, preserving balanced paired comparisons.
3. **Tiebreak model family:** When `gemini-3.1-pro-preview` and `opus-5.5-low` disagree, the tiebreak vote is cast by `gemma-4-31b-it` (a Google open-weights model family distinct from Gemini Pro, but still developed by Google).
4. **Simulated operational CLIs:** External infrastructure commands (`kubectl`, `terraform`, `gcloud`, `psql`) are simulated via deterministic regex mocks rather than live cloud clusters.
5. **Non-Claude target models:** Target agent rollouts in this run evaluate Gemini Flash models (`gemini-3-flash-preview` and `gemini-3.5-flash`). Results may differ when frameworks are paired with Claude Sonnet/Opus or GPT-4o/o3 target agents, particularly for packs originally authored for Claude Code (`.claude/commands/`) or Cline (`.clinerules/`).
