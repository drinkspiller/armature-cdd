---
name: arm-implement
description: Execute the plan for the current active track via autonomous subagent delegation, with TDD lifecycle and phase checkpointing. Use when asked to implement, execute the plan, work on the next task, or run /arm-implement.
persona: Armature Orchestrator
---

# /arm-implement — Execute the Plan

**Purpose:** Execute the plan for the current active track via phase execution
routing (parallel isolated worktree subagents for independent disjoint phases
and a single worker for sequential coupled phases), verifying phase
deliverables, synchronizing documentation, and managing track cleanup.

## Protocol

### Step 1: Setup Check

1.  Resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (armature or conductor)
    per `armature_protocol.md` §7.
2.  Verify the existence of the core context files (`product.md`,
    `tech-stack.md`, `workflow.md`).
3.  If core context files exist in the workspace or are provided in the prompt
    context, proceed immediately. If files are missing and cannot be located,
    halt and inform the user.

### Step 2: Track Selection & Milestone Routing

1.  **Direct Milestone Routing**: If the user prompt specifically instructs you
    to execute a particular milestone or phase (e.g., "Execute Phase N
    checkpoint", "Finalize and synchronize documentation", "Proceed to Step 5",
    "Proceed to track closeout", or "What should we do now?"), jump directly to
    that targeted step without pausing for exploratory file listing or selection
    confirmation.
2.  **New-Track Design Intent Mismatch & Cross-Skill Routing Invariant
    (`/arm-implement` → `/arm-new-track`)**:
    -   **Turn 1 Mismatch Routing**: If `/arm-implement` is invoked with a
        prompt that requests thinking through, designing, reworking, or scoping
        a new feature or architecture (e.g., `"Let's think through..."`, `"Let's
        design..."`, `"Rework..."`) AND no matching planned/active track exists
        in `tracks.md` (e.g., `tracks.md` contains `_No active tracks._`), you
        MUST NOT call `run_command` (`ls`, `cat`, `find`), MUST NOT pack
        multiple questions into `ask_question`, MUST NOT write `spec.md` or
        `plan.md`, and MUST NOT call `invoke_subagent` or `define_subagent`.
        Instead, in that exact turn:
        1.  Explicitly state in visible markdown that no active track exists in
            `tracks.md` for this request, so Armature is routing into
            `/arm-new-track` one-question-at-a-time planning (and will halt upon
            track creation so the user can run `/arm-implement <track_id>`).
        2.  Render the canonical `/arm-new-track` Turn 1 layout in visible
            markdown:
            -   Grouped progress list (`**Now**\n- Round 1, <Topic>` and `**Up
                next**\n- Round 2, <Topic>\n- Round 3, <Topic>`)
            -   Horizontal rule (`---`)
            -   Headline (`## Round 1, Question 1 of 1: <Topic>`)
            -   Unlabeled stakes opener (1–3 plain-English sentences, no
                `**Context:**` label, no code identifiers) ending in `The
                choice here is <X>. Here are some options:`
            -   Numbered one-line options (`1. <Name>: <benefit>; <cost>`, 2–4
                items, no `(Recommended)` tag)
            -   `Safe to ignore for now: <2–3 mechanics>.`
            -   `### Recommendation: Option 1` with exactly one sentence
            -   `Pick N if <condition>.` one line per option
        3.  Invoke `ask_question` natively in the same turn with strictly ONE
            question (`len(questions) == 1`) and 3–4 options.
    -   **Post-Interview Step 10 Terminal Stop Preservation (Two-Part Step 8–10
        Turn Contract)**: When a session that originally started with
        `/arm-implement` in Turn 1 was routed into `/arm-new-track` and reaches
        Step 7 `plan.md` approval, it remains governed by `/arm-new-track` Steps
        8–10. Upon `plan.md` approval, do NOT call `run_command` (`ls`, `cat`)
        to re-read files already in `Given context:`. Execute ONLY
        `/arm-new-track` Steps 8–10 in a single turn using the Two-Part Turn
        Contract:
        1.  **Part 1 (Visible Markdown Text — Required First BEFORE Tool
            Calls):** Output in visible markdown text first (never emit bare
            tool calls with empty markdown text): ``✅ Track \`<track_id>\`
            created! Run \`/arm-implement <track_id>\` to start working through
            the plan.`` (and explain that `/arm-new-track` concludes upon track
            creation and implementation requires invoking `/arm-implement
            <track_id>` as a separate command).
        2.  **Part 2 (Native Tool Calls — Required Second in Same Turn):** Call
            `write_to_file` for `metadata.json` (`"status": "planned"` — NEVER
            `"in_progress"`), call `write_to_file` for `index.md`, call
            `write_to_file` (NEVER `run_command` / `echo >>`) to update
            `tracks.md` with `- [ ]`, and invoke `run_command` to commit (`git
            add ... && git commit -m "chore(armature): Add new track
            '<description>'"`).
        3.  **Hard Terminal Stop:** HALT immediately after the commit tool call.
            Even if the user asks to start Phase 1 immediately with `worker`,
            NEVER call `invoke_subagent`, `define_subagent`, or `schedule`, and
            NEVER set status to `in_progress` or `[~]` in the track-creation
            completion turn.
3.  Otherwise, inspect `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md` (using
    inline prompt context if provided).
4.  If an existing track name was provided:
    -   Find the exact match in `tracks.md`.
    -   **Autonomous Execution Invariant (Zero-Permission Turn 1 Dispatch)**:
        When an existing track name is provided or an active track is requested,
        you are STRICTLY FORBIDDEN from prompting the user with an
        `ask_question` modal to confirm starting. Immediately proceed to Step 3,
        audit `plan.md`, and dispatch Phase 1 (or parallel disjoint phases) via
        `invoke_subagent` on Turn 1.
5.  If no track name was provided and no new-track design prompt was given:
    -   Find the first non-completed track (marked `[ ]` or `[~]`).
    -   If an active track (`[~]`) exists, autonomously resume it without
        prompting.
    -   Only if multiple ambiguous tracks exist and none was specified, prompt
        via `ask_question`: "Which track would you like to implement?"
6.  If no incomplete tracks exist, announce that all tracks are complete and
    halt.

### Step 3: Track Implementation & Phase Checkpoints

1.  **Pre-Execution Mechanical Drift Auto-Heal & Live `arm_status.md` Lockstep
    Sync:**
    -   Before starting tasks, update the selected track's status to `[~]` in
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md`.
    -   Concurrently inspect `{PROJECT_CONTEXT_DIR}/tracks.md`,
        `{PROJECT_CONTEXT_DIR}/index.md`, and completed prior tracks for any
        **Tier A — Mechanical & Deterministic Documentation Drift** (e.g., an
        earlier completed track left at `[~]` after 100% of its `plan.md` tasks
        are `[x]` and its commit landed on `HEAD`, `mdformat`-wrapped `: :`
        tables missing `<!-- mdformat off(prevent table wrapping) -->` /
        `<!-- disableFinding(LINE_OVER_80) -->`, or missing track/ADR index
        links) and **auto-update them in-place immediately** without asking for
        permission.
    -   **Live `arm_status.md` Artifact Lockstep Sync (Mandatory):** Whenever
        `/arm-implement` auto-heals mechanical drift in `tracks.md` / `index.md`
        or transitions track status (`[ ]` $\to$ `[~]` $\to$ `[x]`) in a session
        where `arm_status.md` already exists in the conversation artifact
        directory (`{ARTIFACT_DIR}/arm_status.md`), you MUST **also update
        `arm_status.md` in lockstep in that exact same turn** (`Fixpoint Health:
        ✅ Fixpoint Reached (N mechanical drift issue(s) auto-updated)`) so the
        user never sees a stale `⚠️ Drift Detected` banner on the status
        artifact card!
2.  Load the track context (`spec.md`, `plan.md`, `workflow.md`).
3.  **Phase Coupling Classification & Execution Routing (Parallel Worktrees vs.
    Single Worker)**:
    -   *Fast-Path Solo Exception (Ceremony Scaling)*: If the task is a verified
        micro-task (≤5 lines of code, single-file hotfix, single-line
        configuration, timeout, constant update, or typo fix with zero
        architectural ripple and no schema changes), the agent MUST bypass
        subagent delegation and execute the change directly in Solo mode on the
        main thread. Run the targeted test and finish cleanly.
    -   *Autonomous Delegation Routine (Default)*: All standard implementation
        tracks (multi-task, multi-phase, >5 lines) MUST execute via autonomous
        subagent delegation rather than executing heavy file mutations on the
        main thread. At the start of each phase, the orchestrator checks task
        coupling in `plan.md`:
    -   **1. Phase Coupling Classification (Independent/Disjoint vs.
        Sequential/Coupled)**:
        *   Inspect the tasks in the current phase (and across uncompleted
            phases) in `plan.md`.
        *   **Independent (Disjoint)**: Classify a phase (or set of uncompleted
            phases) as **Independent (Disjoint)** if it has $\ge 2$ tasks/slices
            operating on non-overlapping source and test directories with no
            intra-phase sequential output or imported contract dependencies
            (e.g., Phase 1 touches `landing/` and Phase 2 touches `settings/`).
        *   **Sequential (Coupled)**: Classify a phase (or set of phases) as
            **Sequential (Coupled)** if tasks share state dependencies, touch
            overlapping files, or if Task/Phase N+1 imports or depends on
            symbols/types produced by Task/Phase N (e.g., `frontend/` importing
            types modified in `backend/`). For coupled phases, strictly refuse
            parallel dispatch and execute them pipelined: dispatch Phase N
            first, and upon automated test pass, autonomously advance to Phase
            N+1 without halting for intermediate confirmation modals.
    -   **2. Parallel Isolated Worktrees (Independent/Disjoint Phases)**:
        *   When a phase (or set of phases) is **Independent (Disjoint)**:
            -   **On Antigravity**: Dispatch parallel `worker` subagents in a
                single `invoke_subagent` call with `Workspace: "share"` for each
                entry and arm `schedule(DurationSeconds=90,
                TimerCondition="any")`.
            -   **On Claude Code**: Dispatch parallel `Task` subagents in
                isolated `git worktree` checkouts.
            -   **On Single-Threaded Harnesses**: Fall back to sequential
                execution.
        *   Pass `[ACTIVE_LEGACY_FENCES & SESSION_UNLOCKS]`, applicable ADR
            summaries, and canonical `spec.md`/`plan.md` paths in each worker's
            prompt, along with strict `Owned Files` vs. `Forbidden Files`
            boundaries.
    -   **3. Single Worker (Sequential/Coupled Phases or Single-Task Phases)**:
        *   When a phase is **Sequential (Coupled)** or contains a single task
            slice:
            -   **On Antigravity**: Dispatch a single `worker` via
                `invoke_subagent` with a 90-second conditional
                `schedule(DurationSeconds=90, TimerCondition="<subagent_id>")`
                heartbeat (or `self` with `[Progress]` `send_message` relay).
            -   **On Claude Code**: Dispatch a single `Task` subagent.
    -   **4. Coordinator-Only Updates to Shared Track Files**:
        *   Parallel worktree workers (`Workspace: "share"` / `git worktree`)
            are strictly scoped to their assigned disjoint source and test files
            and are **FORBIDDEN** from mutating
            `armature/tracks/<track_id>/plan.md`, `metadata.json`, `tracks.md`,
            or `.api_surface_cache.json`.
        *   Only the orchestrator updates task checkboxes (`[x]`) in `plan.md`
            and refreshes `.api_surface_cache.json` after merging and verifying
            worker worktrees at phase completion.
4.  **Phase Worker Dispatch (`worker` & `explorer`) & Legacy Fence
    Propagation**:

    -   **Intent-Aware Write Escalation Gate (Mandatory Pre-Mutation Check)**:
        Even if session `READ` access was previously unlocked by the user for a
        legacy-fenced directory (`tech-stack.md` under `## Legacy & Deprecated
        Boundaries` or track `metadata.json` under `legacy_fences`), session
        `READ` access NEVER authorizes write mutations (`replace_file_content`,
        `write_to_file`). If the user requests modifying, updating, or fixing a
        file inside a legacy-fenced directory (`<deprecated_path>`), you MUST
        NOT call `replace_file_content` or `write_to_file` on that file. Halt
        immediately and invoke `ask_question`:
        -   Prompt: `"WARNING: Modifying files in legacy-fenced directory
            (<deprecated_path>). Are you sure you want to proceed?"`
        -   Options:
            1.  `"(Recommended) Apply changes to modern replacement
                (<modern_replacement>) instead"`
            2.  `"Yes, authorize WRITE modifications to <deprecated_path> for
                this task"`
            3.  `"Cancel modification"`
    -   **Context Preparation & Execution-Ready Contract Propagation (`ADR
        0016`)**: Collect the track root, spec path, plan path, specific phase
        task numbers (e.g. `Tasks 1.1, 1.2, 1.3`), detailed requirements,
        applicable ADR summaries, and any local directory rules (`GEMINI.md` /
        `AGENTS.md`). Because background workers (`worker` or `Task` subagents)
        may run on smaller models with zero prior conversation context, always
        pass the exact target file and build-manifest paths (`BUILD`,
        `package.json`, `Cargo.toml`, `go.mod`), verified 1-line method/RPC
        signatures and parameter arity, prerequisite private-to-public helper
        exposure tasks, bidirectional UI `<->` wire field bijections and server
        validator preconditions, hydration echo-suppression flags,
        self-contained signal/timer constants, and unit-test bundle/fixture
        overrides from `spec.md` and `plan.md` directly in the worker `Prompt`.
    -   **Subagent Fence Injection (`[ACTIVE_LEGACY_FENCES &
        SESSION_UNLOCKS]`)**: When dispatching background workers via
        `invoke_subagent`, you MUST inject an explicit `[ACTIVE_LEGACY_FENCES &
        SESSION_UNLOCKS]` block inside the subagent `Prompt`:

        ```markdown
        [ACTIVE_LEGACY_FENCES & SESSION_UNLOCKS]
        - Fenced Paths (Excluded from Search & Edit): <deprecated_path> -> Replacement: <modern_replacement>
        - Session Read Unlocks: [None | <unlocked_paths>]
        - Subagent Rule: NEVER call ask_question from a background worker. Never modify fenced files (<deprecated_path>). If unapproved fence access or write access is required, halt immediately and return a structured escalation request to the parent orchestrator.
        ```

    -   **Immediate Turn 1 Dispatch & Conditional 90s Heartbeat (Zero Redundant
        Search / No `find` or `ls` Probing)**: When track plan and/or legacy
        fence context are provided in the user prompt (e.g. `[Active Track Plan

        -   Phase 1]: ...`or`Plan contains Phase 1: ..., Phase 2: ...`), you are
            STRICTLY FORBIDDEN from calling`grep_search`, `view_file`,
            or`run_command` (`find`, `ls`, `cat`, `head`) to search for the
            track name,`tracks.md`, `plan.md`, or directory contents before
            dispatching. Immediately in Turn 1:

        1.  Output markdown chat text starting with the 20-block progress bar
            (`` `▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░ XX%` (Task X of Y)`` followed by `\n\n`
            and a 1–2 sentence status summary) confirming delegation of the
            phase(s) to `worker` (naming each dispatched subagent and assigned
            phase, plus the active deprecated code boundary banner once on Turn
            1 when legacy fences are present and have not yet been shown in the
            session: once-per-session `> [!NOTE] **Working in ...**` callout on
            Turn 1; strictly silent on Turn 2+ when `[Prior Session History]` is
            present and across intermediate tool steps).
        2.  **Intent-Aware Write Escalation Gate on Fenced Targets (`TRAIN_LF_02`)**:
            If the active plan task or user request targets a file inside an
            active legacy-fenced directory (`<deprecated_path>`) without a prior
            `WRITE` override in `metadata.json` (`fence_overrides`), do **NOT**
            call `replace_file_content`, `write_to_file`, or `invoke_subagent`
            to modify the fenced file. Instead, explain the high-risk legacy
            mutation warning in markdown (directing new work to
            `<modern_replacement>`, without repeating the general session banner
            if `[Prior Session History]` shows Turn 1 already rendered it) and
            immediately invoke `ask_question` in the same turn with the
            Intent-Aware Write Escalation Gate options (`"(Recommended) Apply
            changes to modern replacement (<modern_replacement>) instead"`,
            `"Yes, unlock WRITE access to <deprecated_path> and record in track
            metadata.json"`, `"Abort task"`).
        3.  Invoke `invoke_subagent` with `TypeName: "worker"` (whose `Prompt`
            contains the literal `[ACTIVE_LEGACY_FENCES & SESSION_UNLOCKS]`
            block when legacy fences are active) AND concurrently invoke
            `schedule(DurationSeconds=90, TimerCondition="<subagent_id>",
            Prompt="Check subagent progress and post a 20-block progress bar
            update in main chat.")` (or `TimerCondition="any"` when dispatching
            multiple parallel `worker` subagents) in the exact same turn: `json
            invoke_subagent(Subagents=[{ "TypeName": "worker", "Role": "worker",
            "Workspace": "share", "Prompt": "Task: Execute Phase N of the
            implementation plan for track '<track_id>'.\n\n[ACTIVE_LEGACY_FENCES
            & SESSION_UNLOCKS]\n- Fenced Paths (Excluded from Search & Edit):
            <deprecated_path> -> Replacement: <modern_replacement>\n- Session
            Read Unlocks: <unlocked_paths>\n- Subagent Rule: NEVER call
            ask_question from a background worker. Never modify fenced files
            (<deprecated_path>). If unapproved fence access or write access is
            required, halt immediately and return a structured escalation
            request to the parent orchestrator.\n\nContext:\n1. Follow TDD
            Red/Green/Refactor. Edit only your assigned source/test files; do
            not modify shared track files (plan.md, metadata.json, tracks.md,
            or .api_surface_cache.json) when running in parallel worktrees." }])
            schedule( DurationSeconds=90, TimerCondition="subagent-worker-1",
            Prompt="Check subagent progress and post a 20-block progress bar
            update in main chat." )`

    -   **Periodic 90s Progress Relay & On-Demand Status Inspection (Atomic
        Progress Bar + Tool Turn)**:

        -   On each 90-second conditional `schedule` timer wakeup while a
            `worker` subagent remains active, or when the user asks `"status?"`
            / `"what is the subagent working on?"` while a `worker` subagent is
            running, you MUST execute an **Atomic Progress Bar + Tool Turn**
            (NEVER emit bare tool calls with empty markdown text):
            1.  **Visible Chat Progress Bar & Functional Summary (Mandatory in
                Every Turn)**: Output a leading blank line (`\n\n`), the
                20-block progress bar `` `▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░ XX%` (Task X of
                Y)``, a blank line (`\n\n`), and a 1–2 sentence light functional
                summary of what the subagent finished and what component/file it
                is currently editing (avoiding raw variable names and low-level
                code mechanics). If the user prompt already includes the active
                subagent transcript summary (e.g., `transcript shows it finished
                ... and is currently editing ...`), synthesize and print that
                functional summary immediately in your markdown response
                alongside your tool calls in the same turn!
            2.  **Concurrent Inspection & Conditional Timer Re-Arm**: In the
                same turn, call `manage_subagents(Action="list")` (and inspect
                the active worker `transcript.jsonl` if not already provided)
                AND re-arm `schedule(DurationSeconds=90,
                TimerCondition="<subagent_id>", Prompt="Check subagent progress
                and post a 20-block progress bar update in main chat.")` (or
                `TimerCondition="any"` for multiple active subagents) so updates
                continue until all workers finish.
        -   When using 1-stage custom or `self` subagents equipped with
            `send_message`, instruct the subagent in its `Prompt` to push
            ``[Progress]\n\n`▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░ XX%` (Task X of Y)\n\n<1-2
            sentence summary>`` via `send_message(Recipient="<parent_id>", ...)`
            alongside its next tool call every ~3–4 turns or ~10 tool calls all
            the way until completion, and echo each incoming `[Progress]`
            message in main chat before yielding.
5.  **Phase Checkpointing & Autonomous Continuous Advance**: When `worker`
    completes all tasks in a phase:

    -   Inspect resulting workspace changes (`git status`, `git diff`).
    -   Run the automated test suite (`npm test`, `pytest`, etc.).
    -   **API Surface Extraction**: Extract public symbols for changed files and
        update `.api_surface_cache.json`.
    -   **Per-Directory Rule Reconciliation**: Reconcile local directory rules
        in `GEMINI.md` / `AGENTS.md`.
    -   **Manual Verification Protocol Generation & Stage 2 Empirical Diff
        Re-Verification (ADR 0009)**:
        -   Inspect the empirical phase VCS diff (`git status` / `git diff`)
            against the **Hybrid AST + Diff Classifier**:
            -   If `manual_testing.md` was provisionally classified as a Tier 2
                **`[Micro-Verification Plan]`**, verify that the phase diff
                remained strictly presentational/visual (or qualified under the
                **Orphaned Dead-Code Cleanup Exemption**).
            -   **Automatic Tier 1 Escalation**: If the phase diff touched any
                state machines, reactive stores/signals, router navigation
                guards (`canActivate`), conditional auth/role gates
                (`*ngIf="user.isAdmin"`, `@if`), or RPC/API callers, you MUST
                **automatically escalate** `manual_testing.md` from a
                provisional `Micro-Verification Plan` to a full **Tier 1
                Standard Stateful 3-Part Fixture Triad** runbook (`Migration ->
                Seed -> Reset` and multi-persona scenarios).
            -   If the phase diff remained visual-only, maintain the concise
                Tier 2 `Micro-Verification Plan` card (`Step 1: Run local server
                (<cmd>)` with optional one-line session hint, `Step 2: Navigate
                to http://localhost:<PORT>/<path>`, and `Verify: <visual
                assertion>`).
        -   Update
            `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md`
            with the verified reproduction steps, URLs, and assertions for the
            phase deliverables.
        -   **Documentation-Only Invariant**: Document the exact commands with
            precision, but do NOT execute mutative SQL, database resets, or
            environment teardowns autonomously.
    -   **Incremental Drift Audit**: Perform an incremental drift check on
        modified files against touched ADRs and runbooks (`/arm-drift
        --scope=phase`).
    -   **Walkthrough Artifact**: Write
        `{ARTIFACT_DIR}/arm_implement_phase_N_verification.md` using
        `write_to_file`.
    -   **Autonomous Continuous Pipelining (Zero Intermediate Modals)**:
        -   If automated tests pass and zero drift is detected: Output a concise
            phase completion confirmation in chat with a link to
            `arm_implement_phase_N_verification.md`, and **immediately advance
            to dispatch the next phase**. Do NOT pause with an interactive
            `ask_question` modal between phases. Human verification modals are
            reserved strictly for track completion (Step 5.2).
        -   *Escalation Exception*: If automated tests fail or drift is
            detected, pause execution and prompt the user via `ask_question`:
            "Phase N tests failed or drift was detected. How should we proceed?"
            (`["(Recommended) Triage and fix failure in-flight", "Revise phase
            implementation", "Roll back phase"]`).

6.  **Step 3.6: Pre-Closeout Inner-Loop Review & Repair Gate (`ADR 0015`)**:
    When all phases in `plan.md` are marked `[x]` and automated unit tests pass,
    execute the **Pre-Closeout Inner-Loop Review & Repair Gate** *before*
    running `Step 4: Document Synchronization` so that AST symbol extraction
    (`.api_surface_cache.json`), `terms.md`, and `adr/*.md` synchronize against
    the final post-repair codebase:

    -   **Ceremony Scaling & Automatic Bypass Rules (Skip When Visual-Only or
        Micro-Task):**
        -   **Skip on Micro-Tasks ($\le 5$ Lines):** If the cumulative track
            diff modifies $\le 5$ lines of code in a single file with zero
            schema or architectural changes, **skip Step 3.6** and finish via
            the Fast-Path Solo Exception.
        -   **Skip on Visual-Only Tracks (`[Micro-Verification Plan]`):** If the
            Stage 2 Empirical VCS Diff Classifier (`Step 3.5`) confirms the
            track is strictly presentational/visual (`[Micro-Verification
            Plan]`, including the Orphaned Dead-Code Cleanup Exemption with zero
            state, auth-guard, or RPC changes), **skip Step 3.6** and advance
            directly to `Step 4: Document Synchronization`, noting in your chat
            summary under `### Verification Audit`: `"Step 3.6 Pre-Closeout
            Review Loop skipped (Visual-Only [Micro-Verification Plan]
            track)."`.
    -   **2-Pass Multi-Expert Review-and-Repair Execution (`MAX_ITERATIONS = 2`
        on Behavioral Code Tracks):**

        -   On all behavioral, stateful, backend, API, or multi-file code
            tracks, run up to **`MAX_ITERATIONS = 2`** passes of the **3-Tier
            Runtime-Polymorphic Review-and-Repair Adapter**
            (`armature_protocol.md` §5): Tier 1 Host Adapter +
            `spec_and_adr_verifier` (`include_intent: true`), Tier 2 Multi-Agent
            Panel (`spec_and_adr_verifier` with `include_intent: true`;
            `code_taste_style_verifier` and `correctness_security_verifier` with
            `include_intent: false` blinded to author rationale;
            `deterministic_linter_runner`), or Tier 3 Sequential Pass.
        -   Apply repairs in `P0 -> P1 -> P2 -> P3` order while enforcing all
            **Four Repair Safety Circuit Breakers**: CB1
            `blocked_by_legacy_fence`, CB2 `deferred_spec_conflict`, CB3
            `reverted_test_regression` (revert broken test fix & lock in
            Anti-Oscillation Ledger), and CB4 Final-Pass Application Guarantee
            (`iteration == 2`).
        -   **Mandatory Markdown Table Under `### Verification Audit`:**
            Whenever Step 3.6 executes on a behavioral track, you MUST render
            the `#### Review Loop Iteration Breakdown` markdown table directly
            in your visible chat response under `### Verification Audit`:

            ```markdown
            #### Review Loop Iteration Breakdown
            | Iteration | Reviewers Executed | Reviewer Skipped | Total Comments | Applied | Unapplied |
            | :--- | :--- | :--- | :--- | :--- | :--- |
            | 1 | spec_and_adr_verifier, code_taste_style_verifier, correctness_security_verifier, deterministic_linter_runner | None | 2 | 2 | 0 |
            | 2 | spec_and_adr_verifier, code_taste_style_verifier, correctness_security_verifier, deterministic_linter_runner | None | 0 | 0 | 0 |
            ```

            Below the table under `### Verification Audit`, explicitly state:

            1.  That `Step 3.6` (`MAX_ITERATIONS = 2`) ran **before** `Step 4:
                Document Synchronization` so `.api_surface_cache.json` and
                `terms.md` captured the post-repair symbols.
            2.  The selective author-intent blinding configuration
                (`include_intent: true` for `spec_and_adr_verifier`;
                `include_intent: false` for `code_taste_style_verifier` and
                `correctness_security_verifier`).

### Step 4: Document Synchronization

**Mandatory Single-Turn Continuous Execution:** When asked to
finalize/synchronize documentation (or when transitioning from completing all
tasks), you MUST execute all steps of Step 4 AND Step 5.1 & Step 5.2 in a single
turn. Execute all file operations (`write_to_file`), edits, commits, and
retrospective review tasks autonomously without pausing to ask intermediate
questions before Step 5.2. **CRITICAL (Mandatory Same-Turn Markdown Summary):**
You MUST output the structured markdown summary sections (`### Extracted Domain
Terms`, `### ADR Updates & Alignment`, `### Living Runbook Synchronization`, and
`### Verification Audit`) directly in your visible chat markdown response in the
**exact same turn** alongside your `write_to_file` tool calls—never emit bare
`write_to_file` tool calls without accompanying markdown text.

When all tasks in the track are complete (or when asked to finalize and
synchronize documentation):

1.  **Deterministic AST & Symbol Extraction for Ubiquitous Language
    (`terms.md`)**:
    -   Proactively scan the workspace git diff, new interface exports, proto
        definitions, and entity models for newly introduced domain terminology
        and symbols.
    -   Append newly identified definitions to
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/terms.md` and present the updated
        glossary diff to the user.
2.  **Autonomous ADR Reconciliation**:
    -   Cross-reference newly introduced patterns or modifications against
        active ADRs in `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/`.
    -   If an architectural trade-off was formalized, capture or update the
        relevant ADR.
3.  **Structured Synchronization Output (Always Print in Chat)**:
    -   Always print document synchronization progress in your visible chat
        markdown response using these exact headings in the same turn as file
        updates:
        *   `### Extracted Domain Terms`
        *   `### ADR Updates & Alignment`
        *   `### Living Runbook Synchronization` (MUST explicitly list any
            pruned scenario IDs, e.g., `- **Pruned Obsolete Scenario**: Test
            <Domain>.<ID> (<Title>)`, or state any cold-start deferred fixture
            stamps applied)
        *   `### Verification Audit` (When Step 3.6 executed on a behavioral
            track, you MUST render a `#### Review Loop Iteration Breakdown`
            markdown table `| Iteration | Reviewers Executed | Reviewer Skipped
            | Total Comments | Applied | Unapplied |` in chat under this
            heading; when Step 3.6 was skipped for a visual-only
            `[Micro-Verification Plan]` track or micro-task, explicitly state
            the bypass reason under this heading)
4.  **Tech Stack & Guidelines Sync**:
    -   If tech stack / workflow altered: update `tech-stack.md` /
        `workflow.md`.
    -   If product capabilities / UX guidelines changed: update `product.md` /
        `product-guidelines.md` (present diff for approval).
5.  **Living Manual Testing Runbook Synchronization
    (`manual_testing/<domain>.md` — ADR 0010)**:
    -   **Autonomous Sync Policy**: Extract verified steady-state test scenarios
        from
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md`.
    -   Reconcile into
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md` using
        structured headings (`### Test <Domain>.<ID>`) without an `ask_question`
        confirmation gate. Verify `git status` before and after
        writing to prevent silent workspace write-back races.
    -   **Surgical Assertion Delta Sync (Visual-Only Tracks)**:
        -   When synchronizing a visual-only track into an existing
            `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md`,
            update modified visual assertions **in-place** (anchoring on visible
            text labels or semantic ARIA roles rather than brittle CSS class
            names) while **strictly preserving** all existing database seed,
            migration (`3-Part Fixture Triad`), and persona setup blocks. Never
            overwrite or delete existing database seed scripts when syncing a
            visual-only track.
    -   **Whole-Scenario Pruning for Removed UI Entry Points**:
        -   If a visual change completely removes the primary UI entry point of
            an existing domain scenario (e.g., removing a `"Legacy Export"` card
            where `Test <Domain>.<ID>` tested only that card), cleanly **prune
            the entire obsolete scenario block** (including its coupled setup or
            precondition step) from `manual_testing/<domain>.md` rather than
            leaving broken ghost instructions.
        -   **Mandatory Chat & Artifact Reporting**: Whenever a scenario is
            pruned, you MUST explicitly report the exact pruned scenario ID
            (e.g., `Test Groups.03`) under a `### Living Runbook
            Synchronization` heading BOTH in your visible chat markdown text
            (printed before your tool calls) AND at the bottom of the updated
            `manual_testing/<domain>.md` / artifact file.
    -   **Cold-Start Domain Runbook Seeding & Deferred Fixture Stamping**:
        -   If `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md`
            does not exist yet when syncing a visual-only track, create the file
            with the verified `localhost` visual baseline and stamp `## 2.
            Fixture Provisioning & Reset Tooling` with: `> [!NOTE] Stateful
            3-Part Fixture Triad deferred (initial track was visual-only).`
        -   Do **NOT** fabricate or hallucinate speculative SQL seed commands
            for a cold-start visual domain.
        -   **Mandatory Chat & Artifact Reporting**: Whenever a cold-start
            domain runbook is initialized with a deferred fixture stamp, you
            MUST explicitly report the created domain file, verified `localhost`
            visual baseline URL, and the exact cold-start deferred fixture stamp
            (`Stateful 3-Part Fixture Triad deferred`) under the `### Living
            Runbook Synchronization` heading in your visible chat markdown text
            (printed before your tool calls).
    -   **Artifact Generation & Chat Reference**: Write the finalized domain
        manual testing runbook as an artifact
        (`{ARTIFACT_DIR}/arm_manual_testing_<domain>.md`).
    -   **Chat Notification**: In your response to the user, you MUST explicitly
        state that the manual testing guide artifact has been created and
        provide a clickable markdown link to the file (e.g.,
        `[arm_manual_testing_<domain>.md](file://...)`).
6.  **Fixpoint Verification Gate**: Run the full 3-tier Fixpoint Audit
    (`/arm-drift --check`) to verify zero drift.
7.  Commit documentation changes: `docs(armature): Synchronize docs for track
    '<description>'`.

### Step 5: Track Completion & Next Steps Orchestration

This step occurs **only** after all plan tasks are marked `[x]` and Document
Synchronization has been handled.

1.  **Stage 2 Living ADR Reconciliation & Code Diff Harvest**:
    -   Audit the final code diff (`git diff`), touched directories,
        and completed `spec.md` against the **3-Pillar Invariant Taxonomy**:
        1.  *Cross-Cutting Invariant:* New conventions, state invariants, or
            safety guards extending beyond this track.
        2.  *Architecture / Dependency Binding:* Unplanned dependencies or
            storage patterns introduced during implementation.
        3.  *Negative Constraint:* Discarded patterns or discovered gotchas.
    -   Reconcile active ADRs: Audit checkboxes under `## Confirmation` in
        existing ADRs affected by this track, checking off satisfied rules.
    -   If qualifying emergent invariants were introduced that lack an ADR:
        -   **Print Candidates First**: Output the candidate decisions, citing
            concrete code diff lines, file paths, and qualification pillars in
            chat.
        -   Then invoke `ask_question` with `is_multi_select: true` to confirm:
            "The implementation established new architectural invariants. Record
            them as ADRs?"
        -   For accepted items, draft
            `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/NNNN-slug.md` and commit.
    -   *Zero-Candidate ADR Bypass:* If all decisions are already captured or
        local-only, skip the Step 5.1 ADR modal and advance directly to Step 5.2
        (while ensuring you still print the Step 4 markdown summary sections in
        your chat response text).
2.  **Next Steps Elicitation Gate (Mandatory Turn Barrier)**:
    -   First, output the Step 4 markdown summary sections (`### Extracted
        Domain Terms`, `### ADR Updates & Alignment`, `### Living Runbook
        Synchronization` listing any pruned scenario IDs or deferred fixture
        stamps, and `### Verification Audit`) in your visible chat response
        text.
    -   Immediately after the markdown summary text in the same turn, invoke
        `ask_question` to ask the user what they want to do next:
    -   *Question:* "All tasks and documentation for track '<track_name>' are
        complete. What would you like to do next?"
    -   *Options:*
        *   `"(Recommended) Test the implementation with the manual testing
            guide ([<domain>.md](file://...))"`
        *   `"Upload CL to system / Push changes"`
        *   `"Run full code review (/arm-review)"`
        *   `"Archive completed track and finish"`
        *   `"Keep track active and finish"`
    -   **MANDATORY:** End your turn immediately after calling `ask_question`.
3.  **Execution of Selected Next Step**:
    -   If **Test with Manual Testing Guide**: Present the specific verification
        scenarios from
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md` with
        CLI setup/reset commands and walk the user through testing.
    -   If **Upload / Push**: Execute formatting checks, verify `git status`,
        and push via `git push`.
    -   If **Review**: Transition directly into `/arm-review`.
    -   If **Archive**: Move track folder to `{PROJECT_CONTEXT_DIR}/archive/`,
        remove from `tracks.md`, and commit.
    -   If **Keep Track Active**: Leave the track folder in place.

## Guardrails

-   **Autonomous Delegation Default**: Multi-phase or multi-task tracks delegate
    phase execution via phase coupling routing (parallel isolated worktree
    subagents for independent disjoint slices, and a single worker for
    sequential coupled phases). The primary agent operates as an orchestrator,
    never monopolizing the main conversational thread for heavy code edits.
-   **Coordinator-Only Updates to Shared Track Files**: Parallel worktree
    workers (`Workspace: "share"` / `git worktree`) are strictly forbidden from
    editing `armature/tracks/<track_id>/plan.md`, `metadata.json`, `tracks.md`,
    or `.api_surface_cache.json`. Only the orchestrator updates `plan.md` task
    checkboxes and `.api_surface_cache.json` after merging worker worktrees at
    phase completion.
-   **Documentation-Only Manual Testing Invariant**: Document exact setup, seed,
    and reset commands in manual testing runbooks, but NEVER execute mutative
    database, environment reset, or teardown commands autonomously.
-   **Mandatory Completion Next-Steps Barrier**: When all plan tasks are `[x]`
    and document synchronization is complete, you MUST NOT go silent after
    printing summaries or draft commit descriptions. You MUST invoke
    `ask_question` to offer the user clear next steps (Manual testing with the
    guide, Pushing changes, Running `/arm-review`, or Archiving the track).
