# Changelog

All notable changes to Armature will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.22.3] - 2026-09-08

### Added

-   **Asynchronous Subagent Delegation Invariant & Conversational Responsiveness (`rules/armature_protocol.md` §1, `rules/armature_antigravity.md`)**:
    -   **Orchestrator-Worker Primacy**: Codified the universal invariant that heavy multimodal operations (e.g., screencast/video frame extraction), extensive cross-repository code discovery, and multi-minute compilation/benchmark suites must never execute synchronously on the primary conversational turn.
    -   **Polymorphic Cross-Harness Dispatch**: Accompanying rules provide native polymorphic examples across major agent harnesses: Claude Code (`Task(prompt, subagent_type="explorer")`), OpenCode (`@explore`, `@scout`), OpenAI Codex (`role="explorer"`), and Antigravity (`invoke_subagent`), falling back gracefully to background shell processes (`&`) with proactive status logging on single-threaded environments (Cursor, Aider).
    -   **Interactive Availability**: Mandates immediate turn yielding with visible chat acknowledgement upon worker dispatch, ensuring the primary conversational thread remains available to answer user status inquiries ("status?", "what are you doing?") within seconds.
    -   **Context Window Hygiene**: Isolates transient multimodal tokens and massive compilation log traces inside subagent contexts, preventing primary conversation context exhaustion.

### Fixed

-   **SkillOpt Trajectory Evaluation Fixpoints (`evals/skillopt/run_trajectory_eval.py`, `evals/skillopt/tasks/`)**:
    -   **Multiline Tool Parsing**: Added `re.DOTALL` to multiline regex patterns in `run_trajectory_eval.py` to prevent premature spec write false-positives.
    -   **History Stacking**: Stacked current turn prompts with past user history (`[current_prompt] + history`) when verifying anti-dictation targets, eliminating false dictation alerts on concepts explicitly introduced by the user.
    -   **Lifecycle Annotation Normalization**: Stripped dynamic status tags (`(Confirmed: ...)`, `(OPEN)`, `(Spawned by: ...)`) from ledger items during leaf normalization to prevent denominator inflation in leaf depth ratio calculations.
    -   **Calibrated Task Bounds**: Adjusted `min_leaf_depth` bounds on bounded script turn tasks in `evals/skillopt/tasks/trajectories.jsonl` (TRAJ_02: 0.75, TRAJ_03: 1.0, TRAJ_04: 1.0) and corrected single-turn evaluation expectations in `train.jsonl` and `val.jsonl`.

## [0.22.2] - 2026-09-05

### Added

-   **Wayfinder Integration into CDD vs SDD Comparative Benchmark Battery (`evals/cdd_sdd_benchmark/configs/frameworks.json`, `eval_results.json`, `cdd_sdd_live_benchmark_results.md`)**:
    -   **Authentic Baseline Configuration**: Integrated Wayfinder (Matt Pocock's decision-mapping and frontier tracking methodology) into the open-source comparative evaluation harness across all 30 stratified engineering scenarios (120 criteria across 5 pillars).
    -   **Empirical Scorecard (Rank #4 of 7 Public Frameworks)**: Wayfinder achieved an overall pass rate of **62.5%** (75/120 criteria passed, 95% CI: 53.8%–71.2%, 4,481 avg tokens / task), demonstrating strong Specification Gating (79.2%, 19/24) and Detour Resilience (91.7%, 22/24), but penalized on Surgical Velocity (16.7%, 4/24) due to its core "decisions, not deliverables" mandate refusing code diffs on single-line fixes.
    -   **Documentation Synchronization**: Synchronized the main `README.md` benchmark scorecard matrix and key takeaways to reflect all 7 public frameworks sorted in strict descending order of criteria passed.

## [0.22.1] - 2026-09-05

### Fixed

-   **Atomic Two-Part Response Contract & Mandatory Native `ask_question` Tool Pairing (`rules/armature_antigravity.md`, `rules/armature_protocol.md` §2 & §5, `skills/arm-new-track/SKILL.md` Step 5a)**:
    -   **Root Cause Addressed**: Resolved a failure mode where models formulated the `### Decision Tree Ledger`, evaluated candidate options (Pros/Cons), and generated `#### Recommendation Rationale`, but stalled execution with text alone because instructions to end markdown immediately after the rationale acted as an imperative turn stop signal without mandating the structured tool call.
    -   **Anti-Text-Only Stall Enforced**: Codified the symmetric negative constraint—ending a turn with markdown prose alone when branch choices, candidate options, or trade-offs are presented is strictly forbidden. The agent must pair markdown analysis and the Decision Tree Ledger with an immediate structured `ask_question` tool call in the exact same turn.
    -   **Turn-Ending Barrier Harmonization**: Harmonized instructions across `rules/armature_antigravity.md` (rules 6 & 7), `rules/armature_protocol.md` (§2 & §5), and `skills/arm-new-track/SKILL.md` to clarify that turn conclusion occurs only after the native `ask_question` tool invocation.
-   **SkillOpt Evaluation & Benchmark Optimization**:
    -   Added regression task `TRAIN_29_ATOMIC_TWO_PART_TURN1_ASQ_PAIRING` and disjoint held-out validation task `VAL_25_ATOMIC_TWO_PART_TURN1_ASQ_PAIRING` in `evals/skillopt/tasks/`.
    -   Achieved 100% pass rate (4/4 passed) on both new tasks; resolved `VAL_24` failure from 0.25 to 1.00 (4/4 passed).
    -   Boosted held-out validation score from 68.8% (22/32) to 77.8% (28/36) (+9.0% absolute improvement) and training score from 80.0% to 81.5% (44/54).

## [0.22.0] - 2026-09-04

### Added

-   **Non-Blocking Armature Update Available Mechanism (`check-update.sh`, `rules/armature_protocol.md` §0a Step 11, `install.sh`)**:
    -   **Canonical Deployment (`check-update.sh`)**: Deploys `~/.cache/armature/check-update.sh` with `INSTALLED_VERSION` stamped during installation.
    -   **State Machine & Resilience (`~/.cache/armature/update_check.json`)**: Enforces a 24-hour check TTL (`86400s`), a 24-hour notification frequency cap (`last_notified_timestamp`), a hard 2-second timeout (`curl --max-time 2`), and a 1-hour failure backoff window (`3600s`) so offline or network hiccups never stall `/arm-*` command startup.
    -   **Semantic Version Comparison**: Implements POSIX `awk` numeric semver comparison (`UPSTREAM > INSTALLED`) to suppress false downgrade prompts on unreleased local development branches.
    -   **Chat Notification UX**: When `UPDATE_AVAILABLE|<old_ver>|<new_ver>|<upgrade_cmd>` is emitted, `armature_protocol.md` §0a Step 11 prepends a non-blocking `> [!TIP]` banner with the copy-pastable upgrade command and an offer to run the upgrade automatically if the user replies `"upgrade armature"`.

## [0.21.2] - 2026-09-04

### Fixed

-   **Clean Markdown Termination & Native `ask_question` Tool Invocation (`rules/armature_antigravity.md`, `rules/armature_protocol.md` §2, `skills/arm-new-track/SKILL.md` Step 5a)**:
    -   Enforced strict **Clean Markdown Termination (Zero Trailing Narration)**: models must end their markdown response immediately after the `Recommendation Rationale` paragraph with a clean newline, explicitly prohibiting transitional self-narration sentences (e.g., *"I will now ask for your decision on..."*) that concatenate onto `call:ask_question` and break structured tool parsing.
    -   Enforced **Native Structured Tool Invocation Only**: explicitly barred emitting raw `call:ask_question{...}` text strings inside markdown responses.
-   **SkillOpt Evaluation Harnesses (`evals/skillopt/run_optimizer.py`, `evals/skillopt/run_trajectory_eval.py`)**:
    -   Upgraded `run_optimizer.py` to pass native `tools` (`functionDeclarations` for `ask_question` and `write_to_file`) during task rollouts (`use_tools=True`), replacing simulated prose descriptions of tool invocations with actual API `functionCall` parts.
    -   Added deterministic protocol-level checks (`[PROTOCOL_VIOLATION: RAW_TOOL_TEXT_LEAK_DETECTED]` and `[PROTOCOL_VIOLATION: TRAILING_NARRATION_DETECTED]`) to both `run_optimizer.py` and `run_trajectory_eval.py`.
    -   Added regression tasks (`TRAIN_28_CLEAN_TERMINATION_NATIVE_ASK_QUESTION` and `VAL_24_CLEAN_TERMINATION_NATIVE_ASK_QUESTION`) and verified 100.0% pass rate (`4/4` train, `4/4` held-out val) with zero raw text leakage.

## [0.21.1] - 2026-09-04

### Fixed

-   **Scoped Option Trade-Off Analysis Engine (`armature_protocol.md` §2, `arm-new-track/SKILL.md` Step 5a, `arm-review/SKILL.md`)**:
    -   **Markdown Chat Response ("Report First")**: Preserved itemized `Pros`/`Cons` hierarchy and `Recommendation Rationale` across all design, UX, layout, copywriting, and architectural decision prompts.
    -   **Modal Parameters ("Ask Second")**: Restricted the trailing elaboration choice (`"Compare technical trade-offs and failure modes in detail"`) strictly to **complex systems, data model, or infrastructure architecture decisions**.
    -   **Modal & Gate Exemptions**: Explicitly barred trailing elaboration options in `ask_question` modals for UX copywriting, visual formatting, layout styling, empirical QA verification checkpoints (`/arm-review`), safety confirmations (Hybrid Smart Gate), and procedural workflow approvals (`spec.md`/`plan.md` confirmation, ADR multi-select triage).
    -   Added explicit guardrail under `Verification Gate (ask_question)` in `arm-review/SKILL.md`.
    -   Verified 100.0% pass rate (20/20 criteria across systems architecture, UX copy/layout, and QA verification tasks) via `/skill-opt` evaluation battery.

## [0.21.0] - 2026-09-03

### Added

-   **Option Trade-Off Analysis Engine (`armature_protocol.md` §2, `arm-new-track` Step 5a)**:
    -   Itemized bulleted hierarchy for all presented candidate choices with 1–2 punchy `Pros` and 1–2 `Cons`.
    -   Mandatory `Recommendation Rationale` (1–2 sentences) explicitly justifying why the recommended option was chosen based on codebase constraints, failure resilience, schema evolution, or latency bounds.
    -   Appended trailing option `"Elaborate on trade-offs and failure modes between these options"` triggering a deep-dive comparative matrix detour before re-prompting concrete choices.
    -   Preserved native write-in text field without injecting redundant manual "Other" options into `ask_question`.
-   **Dual-Stage Architectural Decision Record (ADR) Lifecycle**:
    -   **Phase 5c Pre-Spec ADR Candidate Triage Gate (`arm-new-track` Step 5c, `armature_protocol.md` §5, `armature_cdd_protocols.md` §10)**:
        -   Pre-spec triage gate auditing all settled decisions (`[x]`) against the **3-Pillar Invariant Taxonomy**:
            1.  *Pillar 1 (Cross-Cutting Invariant)*: Conventions, contracts, or state invariants constraining future tracks or spanning multiple components.
            2.  *Pillar 2 (Architecture / Dependency Binding)*: Choices binding the repository to storage engines, transport protocols, or libraries costly to replace.
            3.  *Pillar 3 (Negative Constraint / Discarded Alternative)*: Rejected standard patterns due to subtle gotchas or race conditions.
        -   Renders an `### ADR Candidate Triage Table` mapping qualifying decisions to candidate title, pillar, and rationale.
        -   Interactive multi-select modal (`ask_question`) enabling developers to confirm ADR creation before `spec.md` is materialized.
        -   Autonomous drafting of confirmed ADRs in standard MADR format (`NNNN-slug.md`) under `{PROJECT_CONTEXT_DIR}/adr/`.
        -   **Silent Zero-Candidate Bypass**: Silently transitions directly to Step 6 Spec Confirmation when no decisions qualify, avoiding extraneous prompts.
    -   **Stage 2 Living ADR Reconciliation & Code Diff Harvest (`arm-implement` Step 5.1, `armature_cdd_protocols.md` §10)**:
        -   Proactively audits final VCS diff, public API surface (`.api_surface_cache.json`), and verified runbooks during track closeout.
        -   Extracts emergent architectural invariants and captures new ADRs or updates existing records.
-   **SkillOpt Multi-Turn Trajectory Benchmark Suite**:
    -   Added single-turn criteria `TRAIN_27_ADR_TRIAGE_DISCRIMINATION` and `VAL_23_OPTION_TRADEOFF_SYMMETRY`.
    -   Enhanced `evals/skillopt/run_trajectory_eval.py` with multi-turn consumption tracking and robust phase-aware convergence detection.
    -   Verified 100% full-trajectory pass rate with zero sequence barrier violations and zero dictation violations across the entire benchmark battery.

## [0.20.2] - 2026-09-01

### Added

-   **Commit Message Standards (`armature_protocol.md`)**:
    -   Added universal commit message guidelines to Section 4 (`VCS Operations`), instructing agents to prioritize high-level architectural intent and user-visible capabilities into 3–5 punchy bullets while avoiding low-level diff accounting and file inventories.

### Changed

-   **VCS Command Sanitization (`arm-implement`)**:
    -   Sanitized Step 5 track completion next steps in `skills/arm-implement/SKILL.md` to be fully VCS-agnostic and Git-native (`git push` and pull request creation), removing platform-specific tool references.

## [0.20.1] - 2026-08-31

### Added

-   **File Path Sanitization (`arm-new-track`, `armature_protocol.md`)**:
    -   Enforced mandatory stripping of `file://` URI prefixes from `{PROJECT_ROOT}` and file path parameters prior to invoking filesystem tools.
-   **Robust Raw & Truncated Input Handling (`arm-new-track`)**:
    -   Instructs the agent to treat raw JSON, HTML snippets, or truncated state dumps (e.g., DOM scrollbar metrics or lint logs) as contextual reference rather than failing, crashing, or misinterpreting them as imperative commands.

## [0.20.0] - 2026-08-30

### Added

-   **Interactive Manual Verification Flow (`arm-review`)**:
    -   Introduced upfront 3-way review mode selection (`Full Review`, `Interactive Testing only`, `Code Audit only`) and CLI flags (`--both`, `--manual`, `--static`).
    -   Added Step 2.5 `Interactive Verification Phase` driven by `manual_testing.md`, parsing preconditions, setup commands, and expected barrier checks into a real-time verification ledger.
    -   **Hybrid Smart Gate**: Automatically executes non-destructive test fixtures, local servers, and auth token minting while strictly halting and prompting before executing destructive operations (`DROP`, `DELETE`, `TRUNCATE`, `rm -rf`, `reset`, `clean`, `wipe`, `reseed`).
    -   **Mandatory Prerequisites & Copy-Pastable URLs**: Requires a fenced code block with exact service startup commands (`npm run dev`, `./run.sh`) before navigation, and provides fully qualified URLs in separate code blocks (`http://localhost:<PORT>/<path>` and remote host interfaces).
    -   **In-Flight Discrepancy Triage & Cascade Invalidation**: Allows developers to diagnose and apply targeted hotfixes in-flight; automatically flags previously cleared scenarios with `[~] Requires Quick Re-check`.
    -   **Mandatory Post-Testing Reconciliation Gate**: Blocks track signoff and report generation until all logged issues are resolved, recorded as `[BLOCKING]` findings, or acknowledged as `[WARNING]` tech debt.
    -   **Living Runbook Synchronization**: Automatically writes working, verified commands back to `manual_testing.md`.
-   **Sequential Phase 5b Devil's Advocate Execution (`arm-new-track`)**:
    -   Restructured Phase 5b Post-Ledger Devil's Advocate Analysis to present emergent trade-offs, hazards, and failure cascades strictly one-by-one with countermeasure options and sequential decision gates.
-   **Benchmark & SkillOpt Calibration**:
    -   Added multi-domain test tasks `TRAIN_26`, `VAL_20`, `VAL_21`, `VAL_22` evaluating prerequisites blocks, URL formatting, destructive command safety gates, and in-flight triage.

## [0.19.3] - 2026-08-28

### Added

-   **Post-Ledger Devil's Advocate Analysis (Phase 5b)**:
    -   Added a dedicated post-ledger adversarial critique step (`Phase 5b`) in
        `arm-new-track` Step 5 executed when all decision branches and child
        leaves reach `[x]`.
    -   Confronts the user with a structured `### Devil's Advocate Analysis`
        evaluating emergent cross-cutting contradictions, operational hazards,
        and maintainability debt across confirmed choices before spec
        materialization.
    -   Enforces a modal confirmation gate (`ask_question`) offering options to
        reaffirm trade-offs or reopen specific branches.
-   **Lazy Leaf Materialization & Pre-Population Guard**:
    -   Strictly bans pre-populating child leaves under unexplored branches in
        the Decision Tree Ledger. Future branches must remain unexpanded stubs
        until probed.
    -   Added automated Turn-1 pre-population violation assertions to the
        trajectory evaluation runner.
-   **Answer-Anchored Provenance Tags & Depth-2 Horizon**:
    -   Child leaves must explicitly cite the confirmed user choice that spawned
        them: `(Spawned by '<choice>': <ambiguity>)`.
    -   Probing depth strictly bounded to $D \le 2$ (Root Topic $\to$ Operational
        Child Leaf), with operational leaf answers terminating at `[x]` to prevent
        recursive turn exhaustion.

## [0.19.2] - 2026-08-28

### Added

-   **Multi-Turn Trajectory Evaluation Harness
    (`evals/skillopt/run_trajectory_eval.py`)**:
    -   Implemented a 5-metric multi-turn benchmark runner evaluating
        interactive conversational trajectories across stratified domains.
    -   Deterministic evaluation metrics for Mean Leaf Depth Ratio ($D_L \ge
        1.5$), Dictation Violation Count ($V_D = 0$), Decision Tree Ledger
        Fidelity ($F_L \ge 80\%$), Premature Materialization Guard, and Natural
        Convergence Validation.
    -   Seeded `evals/skillopt/tasks/trajectories.jsonl` with 4 multi-turn
        benchmark scenarios including UI sidecars, relational database migrations,
        GraphQL schema federation, and conversational detour recovery.

### Changed

-   **Recursive Decision-Tree Grill Engine (`arm-new-track` Step 5)**:
    -   Enforced mandatory in-transcript `### Decision Tree Ledger` block
        updated on every turn to track root branches and child leaves (`[ ]`
        OPEN, `[x]` Resolved).
    -   Implemented **Child Leaf Spawning Invariant** (Depth $\ge 2$): selecting
        an architectural option at the root of a branch dynamically spawns
        all operational, failure recovery, resource bound, state transition, and
        concurrency leaf probes that must be resolved before closing the branch.
    -   Added **Leaf Prioritization & Pruning Heuristics**: distinguishes Tier 1
        (Mandatory Operational Probes) from Tier 2 (Deferred Implementation
        Details: CSS padding, micro-copy, internal helper naming) to prevent
        interview fatigue and turn exhaustion without arbitrary numeric caps.
    -   Enforced strict **Anti-Dictation Invariant** (Zero Un-Queried
        Decisions): strictly bans asserting declarative implementation designs,
        button placements, or countdown cancellation rules in markdown without
        prior interactive confirmation via `ask_question`.
    -   Eliminated arbitrary static quotas in favor of natural convergence
        governed strictly by resolving all items in the Decision Tree Ledger.

## [0.19.1] - 2026-08-26

### Changed

-   **Installer CLI Output Hierarchy**:
    -   Restyled terminal output across `install.sh` to follow the 6-role CLI output hierarchy.
    -   Replaced box-drawing borders with cyan framed bookend banners to eliminate character width alignment discrepancies.
    -   Left-aligned all status, key-value, and header rows at column 0.
    -   Standardized update command to `git pull && bash install.sh --update`.
-   **Repository & Plugin Rebrand to armature-cdd**:
    -   Renamed public GitHub repository from `antigravity-armature` to `armature-cdd` (`drinkspiller/armature-cdd`) to emphasize universal Context-Driven Development across all agent environments.
    -   Updated default global plugin installation target directory to `~/.gemini/config/plugins/armature-cdd/`.
    -   Added `antigravity-armature` to legacy plugin migration routines in `install.sh` to seamlessly clean up prior installations.

## [0.19.0] - 2026-08-24

### Changed

-   **Renamed Ecosystem to Armature**:
    -   Migrated all core command skills from `conductor-*` to `arm-*` (`arm-setup`, `arm-new-track`, `arm-implement`, `arm-status`, `arm-review`, `arm-revert`, `arm-drift`, `arm-chat`).
    -   Migrated universal rule files to `armature_protocol.md`, `armature_antigravity.md`, `armature_adr_preflight.md`, and `armature_cdd_protocols.md`.
    -   Target plugin installation directory updated to `~/.gemini/config/plugins/antigravity-armature/`.
-   **Transparent Dual-Discovery & Backward Compatibility**:
    -   Implemented transparent dual-discovery: Primary (`{PROJECT_ROOT}/armature/`), Legacy Fallback (`{PROJECT_ROOT}/conductor/`). Operates seamlessly on existing projects without requiring file migrations.
    -   Multi-syntax source-tree context ingestion: parses `## Armature Context` / `<!-- Armature Context -->` and `## Conductor Context` / `<!-- Conductor Context -->` transparently.
-   **SkillOpt Backward-Compatibility Benchmark Suite**:
    -   Updated evaluation tasks across `tasks/train.jsonl` and `tasks/val.jsonl` to enforce `/arm-*` execution and dual-discovery backward compatibility on legacy projects.

## [0.18.2] - 2026-08-24

### Added

-   **Continuous Inquiry Depth Traversal Matrix (`/conductor-new-track` Step 5)**:
    -   Replaced abstract branch traversal narrative in Step 5 with an explicit,
        continuous 6-dimension inquiry matrix: (1) Primary UX & Architecture,
        (2) Failure Modes & Recovery, (3) Boundary Interactions & Escape
        Hatches, (4) State Invariants, Concurrency & Security, (5) Accessibility
        & Environmental Constraints, (6) Adversarial Stress Testing (Devil's
        Advocate).
    -   **Anti-Early-Exit Invariant**: Explicitly forbids terminating track
        interview turns after 1–2 happy-path questions, requiring follow-up
        probes across failure recovery, a11y live regions, and adversarial
        failure modes before convergence.
    -   **Convergence Summary & Confirmation Gate**: Enforces presenting a
        structured markdown summary across all 6 inquiry dimensions and
        obtaining explicit user confirmation via `ask_question` before writing
        `spec.md` to disk.
-   **SkillOpt Depth Regression Tasks (`evals/skillopt/`)**:
    -   Added `TRAIN_17` and `VAL_13` test scenarios modeling asynchronous
        loading dialogues and real-time state synchronization to enforce
        multi-turn inquiry depth across failure recovery, boundaries, and
        adversarial challenges.

## [0.18.1] - 2026-08-24

### Added

-   **Universal Fixture & Schema Conformance Auditing (`/conductor-drift`)**:
    -   Added automated schema conformance checks in Phase 2 Fixpoint to audit
        test reset tools, fixture scripts, and seeders against `.proto`, `.sdl`,
        and DDL definitions for valid enum values and field names.
    -   Audits CLI execution constraints (e.g. single-statement execution vs
        batch piping limits in database CLI tools).
    -   Cross-references API precondition handlers with ADRs to formalize and
        test required payload invariants.

## [0.18.0] - 2026-08-24

### Added

-   **Operational Micro-Fix Fast-Path Bypass (`conductor_protocol.md` §5 &
    `conductor-chat`)**:
    -   Automatically bypasses PRD interview modals, track creation, and
        multi-turn planning when a task modifies ≤5 lines of code with zero
        schema changes.
    -   Emits the minimal surgical diff and verification test commands in ≤500
        tokens, eliminating bureaucratic coordination tax.
-   **Autonomous Living Documentation & AST Glossary Synchronization
    (`conductor-implement` Step 4)**:
    -   Added deterministic AST and symbol scanning to track completion,
        extracting newly introduced entities, contracts, and interfaces directly
        from the git diff into `conductor/terms.md`.
    -   Reconciles active Architecture Decision Records in `conductor/adr/` and
        outputs structured sync summaries (`### Extracted Domain Terms`, `###
        ADR Updates`, `### Living Runbook Synchronization`, `### Verification
        Audit`).
-   **3-Part Fixture Triad & Additive Testing Policy (`conductor_protocol.md`
    §5)**:
    -   Formally mandates the 3-part sequence (`migrate` → `seed` →
        `teardown/reset`) in runbooks for database migrations and environment
        state changes.
    -   Strictly audits manual runbooks in conjunction with automated CI test
        suites while enforcing documentation-only safety against autonomous
        drops.
-   **Non-Blocking Architectural Decomposition (`conductor-new-track` Step 5)**:
    -   Generates cross-layer milestone graphs (Contracts → Transport →
        Consumer) in initial proposals rather than deferring entire plans behind
        exhaustive sub-branch grilling.
-   **Expanded 30-Scenario Live CDD/SDD Evaluation Battery
    (`evals/cdd_sdd_benchmark/`)**:
    -   Tripled the evaluation suite from 10 to 30 distinct engineering
        scenarios (120 test criteria) mapped evenly across all 5 core pillars (6
        scenarios each).
    -   Narrows the 95% confidence interval from ±12.4% down to ±6.4%,
        eliminating statistical power overlap.
-   **Multi-Judge Ensemble Scoring & 20% Edit Distance Clip Guard
    (`evals/skillopt/`)**:
    -   Added `--multi_judge` consensus voting (majority pass across judge
        panel) and tightened mutation edit distance limits from 30% to 20% to
        prevent prompt drift during optimization.

## [0.17.0] - 2026-08-24

### Added

-   **Objective CDD & SDD Evaluation Harness Overhaul
    (`evals/cdd_sdd_benchmark/`)**:
    -   **Authentic Baseline System Instructions**: Purged prompt-criterion
        contamination and test-solution leaks across all frameworks in
        `configs/frameworks.json`. Installed authentic upstream system prompts
        for GitHub Spec Kit, BMAD Method, OpenSpec, and Memory Bank.
    -   **Blinded LLM-as-Judge Evaluation**: Masked framework identities
        (`CANDIDATE UNDER TEST (Blinded Candidate)`) before submitting execution
        transcripts to the criterion judge, eliminating brand bias and hardcoded
        winner fallbacks.
    -   **Deterministic Verification & Safety Assertions**: Added deterministic
        token limit enforcement (<1500 tokens for micro-hotfixes) and automated
        detection of unshielded destructive shell patterns.
    -   **Statistical Rigor ($95\%\text{ CI}$)**: Integrated standard error and
        95% normal confidence interval calculations ($p \pm 1.96 \cdot SE$)
        across all framework pass rates and architectural pillars.
    -   **10-Scenario Stratified Benchmark Battery**: Expanded evaluation
        scenarios to 10 distinct, non-redundant engineering challenges mapped
        across 5 core architectural pillars (Spec Gating, Detour Resilience,
        Surgical Efficiency, Drift Governance, State Safety).
-   **SkillOpt Held-Out Validation Suite & Anti-Overfitting Safeguards
    (`evals/skillopt/`)**:
    -   Replaced validation set with 12 strictly held-out domain tasks (zero
        mirror overlap with `train.jsonl`).
    -   Injected anti-overfitting rules into the optimizer reflection prompt and
        tightened the sequence-matcher edit distance limit to 30%.
-   **Production Skill De-Overfitting**:
    -   Generalised overfitted CSS-specific rules in
        `skills/conductor-new-track/SKILL.md` into universal, domain-agnostic
        failure-mode stress testing and detour recovery.

## [0.16.2] - 2026-08-23

### Added

-   **Adversarial Token & Layout Refactoring Probes (`/conductor-new-track`)**:
    -   Injected mandatory adversarial stress testing for UI layout and design
        token refactor tracks to probe custom property fallbacks and CSS cascade
        specificity collisions before finalizing specs.
    -   Added detour recovery and re-challenging to systematically evaluate
        down-stream accessibility contrast and token cascade risks after
        answering out-of-band inquiries.
-   **Incremental Phase Checkpoint Mode (`/conductor-drift --scope=phase`)**:
    -   Added structured scoping to audit files modified in the active track's
        current phase against ADRs and manual testing runbooks without blocking
        work-in-progress code.
-   **Continuous Document Synchronization Execution (`/conductor-implement`)**:
    -   Added single-turn continuous execution directive for Step 4 Document
        Synchronization through Step 5.2 Next Steps Elicitation Gate.
-   **SkillOpt 30-Task Batch Calibration**:
    -   Achieved 100.0% validation scores across 7 Conductor command skills
        (`conductor-new-track`, `conductor-implement`, `conductor-drift`,
        `conductor-setup`, `conductor-chat`, `conductor-revert`,
        `conductor-status`).

## [0.16.1] - 2026-08-23

### Added

-   **Track Completion Next-Steps Elicitation Gate (`/conductor-implement`)**:
    -   Implements Step 5.2 Next Steps Elicitation Gate in
        `skills/conductor-implement/SKILL.md` to prevent agents from going
        silent or terminating turns with static summaries upon completing a
        track.
    -   Mandates invoking `ask_question` with structured options:
    *   `(Recommended) Test the implementation with the manual testing guide
        ([<domain>.md](file://...))`
    *   `Upload CL to Code Review / Push changes`
    *   `Run full code review (/conductor-review)`
    *   `Archive completed track and finish`
    *   `Keep track active and finish`
-   **Completion Turn Barrier Guardrail**: Added `Mandatory Completion
    Next-Steps Barrier` to `conductor-implement` guardrails.
-   **SkillOpt Benchmark Suite**: Added `TRAIN_08` and `VAL_14` evaluating track
    completion next-steps orchestration, achieving 100% pass rates across train
    and validation sets.

## [0.16.0] - 2026-08-23

### Added

-   **CDD & SDD Live Evaluation Benchmark Suite (`evals/cdd_sdd_benchmark/`)**:
    -   Standalone, zero-external-dependency live evaluation harness
        (`run_cdd_sdd_eval.py`) with 8-scenario, 32-criterion test suite
        comparing 7 industry frameworks (`antigravity-conductor-dev`,
        `canonical_conductor`, `conductor_oss`, `bmad_method`, `memory_bank`,
        `github_spec_kit`, `openspec`).
    -   Automated LLM Meta-Judge synthesis via `gemini-3.1-pro-preview`
        generating composite scores (0–100), rank, winner declaration, and
        markdown report artifacts.
    -   Dynamic ceremony scaling rule for micro-hotfixes (<5 lines, zero ripple)
        bypassing heavy PRD barriers.
    -   Adversarial proto schema evolution challenge rule during Step 7 / Step 9
        Gap Analysis for proto3 default zero-value collisions in partial
        updates.
    -   Additive manual testing runbook verification rule auditing living
        runbooks concurrently with automated unit/integration test suites.
-   **SkillOpt Optimization Benchmark Suite (`evals/skillopt/`)**:
    -   Extended training tasks `TRAIN_17`–`TRAIN_19` and validation tasks
        `VAL_14`–`VAL_15` covering micro-hotfix ceremony scaling, proto3 field
        presence evolution, and additive runbook auditing.

### Added

- **Conductor Fixpoint Auditor (`/conductor-drift`)**: Dedicated command skill (`skills/conductor-drift/SKILL.md`) natively auditing divergence across project documentation, ADRs, domain manual testing runbooks, API surfaces, and packaging manifests using native workspace inspection tools.
- **3-Tier Audit Architecture**:
  - *Phase 1 (Docs & Specs)*: Audits cross-document consistency, ADR schemas/sequences, domain runbook scenarios, and specification completeness.
  - *Phase 2 (Code & Interfaces)*: Compares public exports against `.api_surface_cache.json` and audits per-directory `## Conductor Context` boundary integrity.
  - *Phase 3 (Meta & Packaging)*: Audits `install.sh`, `install.bat`, `plugin.json`, `marketplace.json`, and `README.md` for installer array completeness and version stamp fixpoints.
- **Automated Lifecycle Drift Hooks**:
  - *Incremental Checkpoints*: Fast incremental diff scans at phase checkpoints in `/conductor-implement` Step 3.
  - *Track Completion Gate*: Mandatory Fixpoint verification in `/conductor-implement` Step 4 before archiving.
  - *Review Gate*: Added `Fixpoint Audit: [Pass/Fail]` to `/conductor-review` checklist and `review.md`.
  - *Ambient Health Banner*: 1-line passive Fixpoint health summary in `/conductor-status` and `/conductor-chat`.
  - *Pre-Submit Release Gate*: Section 5 of `antigravity-conductor-dev` enforces running `/conductor-drift` before mailing CLs.

## [0.14.0] - 2026-08-23

### Added

-   **Manual Testing Runbooks (`conductor/manual_testing/`)**: Integrated
    living, domain-organized manual testing runbooks into the Conductor
    protocol.
-   **Tiered Testing Strategy Classification**: `/conductor-new-track` Gap
    Analysis (Step 7) classifies tracks into full persona runbooks
    (interactive/stateful flows) versus concise smoke checks (refactors/chores).
-   **Autonomous Non-Gated Synchronization**: `/conductor-implement` Step 4
    automatically extracts verified steady-state test scenarios from
    `tracks/<track_id>/manual_testing.md` and merges them into
    `conductor/manual_testing/<domain>.md` without prompting the user.
-   **Documentation-Only Fixture Invariant**: Enforced that manual testing
    runbooks document exact setup and CLI reset commands, but agents must never
    execute mutative database or environment reset commands autonomously.
-   **Additive Review Gate**: Added `Manual Testing Runbook: [Pass/Fail]` check
    to `/conductor-review` under Section 2.4 and `review.md`, auditing
    completeness of newly introduced routes, flags, and personas without
    altering automated test checks.
-   **SkillOpt Evaluation Suite (`evals/skillopt/`)**: Added version-controlled
    evaluation runner (`run_optimizer.py`), training tasks
    (`tasks/train.jsonl`), and validation tasks (`tasks/val.jsonl`)
    consolidating historical test scenarios with new manual testing protocol
    assertions.

## [0.13.2] - 2026-08-22

### Fixed

-   **Pre-Materialization Hardening Barrier in `conductor-new-track`**: Prevented
    premature disk writing of `spec.md` during preliminary drafting (Step 6).
    `spec.md` is now strictly held as an in-memory draft until Step 10, ensuring
    it is materialized only after Gap Analysis and Devil's Advocate milestones
    are complete.
-   **Sequential Step Numbering Alignment**: Resolved missing Step 6 gap
    and aligned protocol execution sequentially from Step 1 through Step 14.
-   **Interruption & Detour Recovery**: Added explicit guardrails ensuring that
    conversational detours (such as asset handling or technical clarifications)
    resume at the uncompleted milestone rather than leaping to plan generation or
    commit.
-   **Milestone Pre-Plan Checklist**: Enforced a prerequisite checklist gate
    before `plan.md` generation in Step 11, validating all 7 Gap categories and
    2–3 Devil's Advocate challenges.

## [0.13.1] - 2026-08-17

### Fixed

-   **Enforce Mandatory Interactive Gating in `conductor-new-track`**: Added
    unyielding synchronous turn-ending stop barriers at Steps 5 (Grill
    interview), 8 (Gap analysis), 10 (Devil's advocate), 11 (Spec approval), and
    12 (Plan approval).
-   **Eliminated Autonomous Skip Loophole**: Removed the permissive clause
    allowing agents to bypass user dialogue when codebase context is available.
-   **Compound Prompt Shielding**: Added explicit guardrails preventing agents
    from prematurely executing downstream commands (e.g., `/diagnose` or `Fix`)
    before completing all interactive track creation milestones.

## [0.13.0] - 2026-08-14

### Breaking

-   **Subsumed Invariants into ADRs**: Eliminated `conductor/invariants.md`.
    Behavioral contracts, ordering constraints, and safety assertions are now
    unified directly under Architecture Decision Records (`conductor/adr/*.md`)
    using standard MADR format with checkable `## Confirmation` criteria.
-   **Rebranded Invariant Capture Protocol**: Converted §10 in
    `conductor_cdd_protocols.md` to the **ADR Capture Protocol**, formalizing
    unwritten constraints as lightweight ADRs.
-   **Per-Directory Context Format**: Updated directory context sections to use
    `### Local Rules` and `### Relevant ADRs`.

## [0.12.0] - 2026-08-14

### Breaking

-   **Unified Global Plugin Discovery**: Moved installation path to
    `~/.gemini/config/plugins/antigravity-conductor/`, aligning with modern Antigravity
    customization discovery (`https://github.com/drinkspiller/antigravity-conductor` and
    `https://github.com/drinkspiller/antigravity-conductor`). Skills and rules are now automatically
    discovered across Antigravity CLI, Antigravity IDE, and AI IDEs without manual
    `skills.json` or `rules.json` configuration.
-   **Retired Gemini Coder Workstation Target**: Deprecated `--target=gemini_coder`.
    AI IDEs automatically consumes the host's global plugins under
    `~/.gemini/config/plugins/`.

### Added

-   **Legacy Path Migration**: Added `migrate_to_v0_12_0` in `install.sh` to
    clean up legacy skill and rule directories from `~/.gemini/antigravity/` and
    `~/.gemini/antigravity/` during install, update, and uninstall.

## [0.11.0] - 2026-07-20

### Breaking

-   **Consolidated Grill into `conductor-new-track`**: Deleted
    `conductor_newTrack_grill` and `conductor_newTrack_discovery`. Grilling is
    now the default one-question-at-a-time interview protocol inside
    `conductor-new-track` Step 5.
-   **Kebab-Case Skill Renaming**: Renamed all sub-skill directories to
    kebab-case hyphens (`conductor-setup`, `conductor-new-track`,
    `conductor-implement`, `conductor-status`, `conductor-review`,
    `conductor-revert`, `conductor-chat`). Added automatic installer cleanup
    (`migrate_to_v0_11_0`) to remove deprecated underscore folders.

### Changed

-   **Per-Directory Context Protocol**: Updated `conductor-implement` Step 3.3,
    `conductor_cdd_protocols.md` §11, `conductor-setup` Artifact 10, and
    `conductor_protocol.md` §0a item 9 to:
    -   Discover agent context files case-insensitively (`GEMINI.md`,
        `CLAUDE.md`, `AGENTS.md`, `AGENT.md`). Append to existing files without
        creating duplicates; prompt user for preferred filename when multiple or
        zero files exist.
    -   Use reason-driven creation based on architectural justification
        (interacting services, stateful controllers, local invariants, domain
        gotchas) rather than arbitrary file-count thresholds.

## [0.10.0] - 2026-06-22

### Breaking

-   **Removed hub skill** (`conductor/SKILL.md`): The directory structure and
    context loading priorities now live in `conductor_protocol.md` §0/§0a.
    Individual command skills (`conductor_setup`, `conductor_newTrack`, etc.)
    are discoverable via their YAML frontmatter descriptions. No routing table
    or hub orientation doc is needed.

### Added

-   **API Surface Auto-Extraction**: Phase checkpoints in `/conductor_implement`
    now run full-file AST extraction (via `ast-grep`) on changed files, compare
    against a cached snapshot (`.api_surface_cache.json`), and propose novel
    symbols for addition to `terms.md`. Catches new methods on existing classes,
    interface properties, and enum members — not just top-level exports.

-   **Invariants as First-Class Artifact**: New `conductor/invariants.md` file
    for behavioral contracts (ordering constraints, null-check requirements,
    data-flow rules). Capture triggers fire during spec generation (Devil's
    Advocate), design decisions, implementation, review, and user-initiated
    statements.

-   **Pre-Execution Drift Scan**: Every Conductor command now performs a
    lightweight drift check during context loading. Changed files are
    cross-referenced against ADR scopes and invariant scopes; contradictions are
    flagged with resolution options before the command proceeds.

-   **Per-Directory GEMINI.md Context**: Conductor manages a `## Conductor
    Context` section inside existing `GEMINI.md` files for large directories.
    Sections include Purpose, Invariants, Key Types, and Term Overrides,
    delimited by boundary comments to prevent merge conflicts. Created during
    `/conductor_setup` (brownfield) and `/conductor_implement` (on first
    directory access).

### Changed

-   **Token footprint reduction (~68%)**: Always-on protocol rule shrank from
    294 to 199 lines. Extended protocols (ADR preflight, drift scan, invariant
    capture, per-directory context) extracted to inert reference files
    (`conductor_adr_preflight.md`, `conductor_cdd_protocols.md`) loaded on
    demand by skills. Hub skill (331 lines) eliminated entirely.
-   **Glossary file renamed**: `TERMS.md` → `terms.md` for consistency with all
    other lowercase conductor artifact filenames.
-   **Templates relocated**: `workflow_template.md` and `adr_template.md` moved
    from `conductor/templates/` to `conductor_setup/templates/` — the only skill
    that uses them.
-   **Version stamp relocated**: `.conductor_version` now lives under
    `conductor_setup/` instead of the removed `conductor/` directory.
-   **Installer**: Installs reference files alongside rules. Removed hub skill
    installation. Hub skill migration auto-removes old `conductor/` directory
    during upgrade.

## [0.8.0] - 2026-06-19

### Added

-   **Universal ADR & Glossary Preflight Interceptor**: Added Section 6 to
    `conductor_protocol.md` (Controller layer). When ANY Conductor command
    executes against an existing brownfield project that lacks
    `conductor/adr/*.md` files, execution pauses to perform an automated
    document sweep (`tech-stack.md`, `product.md`, legacy specs, `README.md`),
    filter trade-offs through the 3-part gate, interview the developer and
    backfill historical ADRs before resuming the primary command.

## [0.7.0] - 2026-06-19

### Added

-   **Domain Modeling & ADR Integration (Phase 2)**:
    -   **Verification Bridge**: `/conductor_newTrack` Step 13 scans generated
        ADRs for `## Confirmation` sections and automatically injects their
        verification criteria as explicit tasks into `plan.md`.
    -   **ADR Vetting Hook**: Added architectural decision record cross-checking against
        engineering standards before writing ADR files.

## [0.6.0] - 2026-06-19

### Added

-   **Domain Modeling & ADR Integration (Phase 1)**:
    -   **Project Glossary (`terms.md`)**: Semi-mandatory, skippable glossary
        step in `/conductor_setup` (Artifact 8). Auto-populates from codebase
        scans in Brownfield projects; interviews the developer in Greenfield.
    -   **Inline ADR Gating**: 3-part gate (hard to reverse × surprising × real
        trade-off) evaluated per-decision in `/conductor_newTrack` Step 7.
    -   **Immediate ADR Writing**: Confirmed decisions written immediately to
        `conductor/adr/NNNN-slug.md` using the new `adr_template.md` template.
    -   **Varied Copy Phrasing**: User-facing prompts use 3-4 randomized copy
        phrasings rotated to prevent robotic repetition.
    -   **Spec Integration**: `spec.md § Design Decisions` links directly to
        generated ADRs with one-line summaries.
    -   **Token-Efficient Cross-Track Check**: Step 10 scans ADR filenames by
        default, selectively loading full-text only when slugs match active
        glossary terms.
    -   **Archival Retrospective**: `/conductor_implement` Step 5 track cleanup
        reviews un-gated decisions in hindsight and offers to promote them.
    -   **ADR Compliance Reviews**: `/conductor_review` §2.4 and §3.1 check code
        changes against active ADRs, warning on drift and offering to fix,
        update the ADR, or record tech debt.
-   **ADR Template**: Bundled `adr_template.md` installed to templates
    directory.

## [0.5.0] - 2026-05-26

### Added

-   **Grill mode** for `/conductor_newTrack` — conductor-aware relentless
    interview mode, triggered by "grill", "grill-me", or "grill me" in the
    prompt. Merges grill-me's recursive questioning with conductor domain
    awareness (glossary enforcement, code cross-referencing, spec-section
    targeting). New sub-skill: `conductor_newTrack_grill` (persona: Conductor
    Interrogator)
-   **Discovery mode** extracted to its own sub-skill — the
    `[experimental-discovery]` categorized questioning is now
    `conductor_newTrack_discovery` (persona: Conductor Explorer), keeping the
    newTrack protocol clean

### Changed

-   **`conductor_newTrack` Step 6** refactored to a mode dispatch point —
    detects grill/discovery/default mode from the user's prompt and delegates to
    the appropriate sub-skill
-   **Opportunities Selection** in Step 9 no longer references
    `[experimental-discovery]` inline — triggers on the presence of the `##
    Opportunities for Consideration` section regardless of mode
-   **Version bump** 0.4.0 to 0.5.0

## [0.4.0] - 2026-05-20

### Added

-   **MVC rules architecture** - Extracted universal guardrails and Antigravity UX
    adapter into always-on rule files
    (`conductor_protocol.md`, `conductor_antigravity.md`)
-   **Agent personas** - Each sub-skill now defines a named persona (Conductor
    Architect, Conductor Planner, Conductor Implementer, Principal Software
    Engineer, Conductor Observer, Conductor Surgeon, Conductor Guide)
-   **CHANGELOG.md** - Formal semantic versioning with release notes
-   **Skill path detection** in installer - Automatically detects plugin structure
    and skill directories
-   **VCS status guard** - Skills check for actual changes before committing
-   **Dual artifact strategy** - Conductor artifacts written to `conductor/`
    (VCS) with symlinks in Antigravity artifact directory for interactive review
-   **Rules installation** in installer - Automatically copies rule files
    alongside skills
-   **CHANGELOG extraction** in installer - `--release-notes` flag shows changes
    for the installed version

### Changed

-   **Hub skill** (`conductor/SKILL.md`) trimmed to lightweight orientation
    doc - guardrails, interaction conventions, and artifact output conventions
    moved to rules
-   **Sub-skills** no longer contain repeated `ask_question` best practices -
    extracted to `conductor_antigravity.md` rule
-   **VCS references** in sub-skills are now generic - platform-specific
    commands injected by rules instead of inline enumeration
-   **Version bump** 0.3.0 to 0.4.0

### Removed

-   Duplicate `ask_question` best practices blocks from all 7 sub-skills
-   Inline multi-VCS command enumeration from sub-skill protocols
-   Redundant guardrails section from hub skill (now in `conductor_protocol.md`)

## [0.3.0] - 2026-04-15

### Added

-   `/conductor_chat` - Lightweight ceremony-free context mode
-   Enhanced `/conductor_newTrack` discovery pipeline (gap analysis, cross-track
    awareness, devil's advocate)
-   Individual `ask_question` calls for gap analysis and devil's advocate items
-   `ask_question` best practices with positive/negative examples

### Changed

-   Hub skill expanded with detailed artifact output conventions
-   Sub-skills updated with per-item structured questioning

## [0.2.0] - 2026-03-01

### Added

-   Skills-based architecture (migrated from workflows)
-   Hub-and-spoke model with central conductor skill
-   Version stamping (`.conductor_version`)
-   Legacy workflow migration in installer
-   Dry-run mode, backup-by-default, idempotent installs

## [0.1.0] - 2026-02-01

### Added

-   Initial conductor implementation as Antigravity workflows
-   Core commands: setup, newTrack, implement, status, review, revert
