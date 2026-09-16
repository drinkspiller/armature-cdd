---
name: arm-implement
description: Execute the plan for the current active track via autonomous subagent delegation, streaming active progress every 20s, with TDD lifecycle and phase checkpointing. Use when asked to implement, execute the plan, work on the next task, or run /arm-implement.
persona: Armature Orchestrator
---

# /arm-implement — Execute the Plan

**Purpose:** Execute the plan for the current active track via autonomous
subagent delegation (`worker`), actively streaming progress updates every 20
seconds, verifying phase deliverables, synchronizing documentation, and managing
track cleanup.

## Protocol

### Step 1: Setup Check

1.  Resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (armature or conductor) per `armature_protocol.md` §7.
2.  Verify the existence of the core context files (`product.md`,
    `tech-stack.md`, `workflow.md`).
3.  If core context files exist in the workspace or are provided in the prompt
    context, proceed immediately. If files are missing and cannot be located,
    halt and inform the user.

### Step 2: Track Selection & Milestone Routing

1.  **Direct Milestone Routing**: If the user prompt specifically instructs you to execute a particular milestone or phase (e.g., "Execute Phase N checkpoint", "Finalize and synchronize documentation", "Proceed to Step 5", "Proceed to track closeout", or "What should we do now?"), jump directly to that targeted step without pausing for exploratory file listing or selection confirmation.
2.  Otherwise, read `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md`.
3.  If a track name was provided:
    -   Find the exact match in `tracks.md`.
    -   **Autonomous Execution Invariant (Zero-Permission Turn 1 Dispatch)**:
        When a track name is provided or an active track is requested, you are
        STRICTLY FORBIDDEN from prompting the user with an `ask_question` modal
        to confirm starting. Immediately proceed to Step 3, audit `plan.md`, and
        dispatch Phase 1 (or parallel disjoint phases) via `invoke_subagent` on
        Turn 1.
4.  If no track name was provided:
    -   Find the first non-completed track (marked `[ ]` or `[~]`).
    -   If an active track (`[~]`) exists, autonomously resume it without prompting.
    -   Only if multiple ambiguous tracks exist and none was specified, prompt
        via `ask_question`: "Which track would you like to implement?"
5.  If no incomplete tracks exist, announce that all tracks are complete and
    halt.

### Step 3: Track Implementation & Phase Checkpoints

1.  Before starting tasks, update the selected track's status to `[~]` in
    `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md`.
2.  Load the track context (`spec.md`, `plan.md`, `workflow.md`).
3.  **Execution Topology & Dependency Audit**:
    -   *Fast-Path Solo Exception (Ceremony Scaling)*: If the task is a
        verified micro-task (≤5 lines of code, single-file hotfix, single-line
        configuration, timeout, constant update, or typo fix with zero
        architectural ripple and no schema changes), the agent MUST bypass
        subagent delegation and execute the change directly in Solo mode on the
        main thread. Run the targeted test and finish cleanly.
    -   *Autonomous Delegation Routine (Default)*: All standard implementation
        tracks (multi-task, multi-phase, >5 lines) MUST execute via autonomous
        subagent delegation. The primary agent acts as orchestrator: it decomposes
        the implementation plan by phase and delegates execution to background
        `worker` workers rather than executing file mutations on the main
        thread.
    -   *Disjoint Phase Concurrency Audit*: The orchestrator audits the
        uncompleted phases in `plan.md` to map touched file scopes and interface
        dependencies:
        *   **Disjoint Phases (Parallel Execution)**: If two or more phases touch
            completely disjoint file sets with zero contract dependencies (e.g.,
            Phase 1 touches `landing/` and Phase 2 touches `settings/`), the
            orchestrator dispatches separate `worker` subagents
            simultaneously, specifying `Workspace: "share"` for each to isolate
            working copies.
        *   **Coupled Phases (Continuous Pipelined Execution)**: If Phase N+1
            imports or depends on symbols produced by Phase N (or imports types
            defined in Phase 1's package), the orchestrator strictly refuses
            parallel dispatch and executes them pipelined: it dispatches Phase N
            first. Upon successful phase completion and automated test pass, the
            orchestrator autonomously advances to Phase N+1 without halting for
            intermediate confirmation modals.
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
    -   **Context Preparation**: Collect the track root, spec path, plan path,
        specific phase task numbers (e.g. `Tasks 1.1, 1.2, 1.3`), detailed
        requirements, and any local directory rules (`GEMINI.md` / `AGENTS.md`).
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
    -   **Immediate Turn 1 Dispatch (Zero Redundant Search)**: When track plan
        and legacy fence context are provided in the user prompt (e.g. `[Active
        Track Plan - Phase 1]: ...`), NEVER call `grep_search` or `view_file` to
        search for the track name or `tracks.md`. Immediately in Turn 1:

        1.  Output markdown chat text confirming delegation of the phase to
            `worker` and displaying the active legacy fence HUD status (`🚧
            Legacy Fence Active: [<deprecated_path>] excluded ──► Target:
            [<modern_replacement>]`).
        2.  Invoke `invoke_subagent` with `TypeName: "worker"` whose `Prompt`
            contains the literal `[ACTIVE_LEGACY_FENCES & SESSION_UNLOCKS]`
            block:
        ```json
        invoke_subagent(Subagents=[{
          "TypeName": "worker",
          "Role": "worker",
          "Workspace": "share",
          "Prompt": "Task: Execute Phase N of the implementation plan for track '<track_id>'.\n\n[ACTIVE_LEGACY_FENCES & SESSION_UNLOCKS]\n- Fenced Paths (Excluded from Search & Edit): <deprecated_path> -> Replacement: <modern_replacement>\n- Session Read Unlocks: <unlocked_paths>\n- Subagent Rule: NEVER call ask_question from a background worker. Never modify fenced files (<deprecated_path>). If unapproved fence access or write access is required, halt immediately and return a structured escalation request to the parent orchestrator.\n\nContext:\n1. Follow TDD Red/Green/Refactor. Mark completed tasks [x] in plan.md."
        }])
        ```

        3.  Concurrently invoke `schedule(DurationSeconds=20, Prompt="Check
            subagent progress and stream a visible status update",
            TimerCondition="worker")` in that exact same turn!
5.  **Mandatory Active Heartbeat & Progress Streaming Loop (20-Second Cadence)**:
    -   **Proactive Heartbeat Timer**: Concurrently with or immediately upon
        dispatching the subagent, schedule a 20-second heartbeat timer:
        `schedule(DurationSeconds=20,
        TimerCondition="<subagent-conversation-id>", Prompt="Check subagent
        progress and stream a visible status update")`.
    -   **Periodic Status Updates**: The orchestrator is strictly forbidden from
        waiting in silence. On each timer wake-up:
        1. Call `manage_subagents(Action='list')` to inspect worker state and
           `stateDetail`.
        2. Inspect recent tool calls from the subagent's transcript log.
        3. Output a concise, visible progress update in chat following the canonical 4-element telemetry structure:
           - **How Far Along (Dynamic Altitude & Task Progress)**:
             * Calculate and display an advancing progress bar, percentage, and active task count across the track: `[▓▓▓▓░░░░░░] 45%` **Phase N/M (X/Y tasks):** `<track_id>`
             * **Never use static combined headers** like `Progress Update (Phases 2–4)`—this makes execution appear frozen. The header MUST resolve and display the *single currently active phase* and sub-task count so progress moves visually on every 20-second tick.
             * Omit redundant chat boilerplate like "Next update in 20 seconds." (the UI timer already signals liveness).
           - **High-Level Task**: The deliverable/capability achieved (`The subagent finished <functional capability> in <TargetComponent> (<target_file>):`).
           - **Specific Updates Made**: Light-level bullets explaining what was done and why, avoiding raw variable names and low-level code mechanics.
           - **Forward Transition**: Natural, varied forward-looking transition to the next step (e.g., "Next up: ...", "Switching focus to ...", "Now moving on to ...", "Advancing to ...").
           ```markdown
           `[▓▓▓▓░░░░░░] 45%` **Phase 2/4 (3/7 tasks):** `simplify-conductor-routes`

           The subagent finished container verification in `CcGroups`:
           * Bootstrapped the component with proper Angular injection context to fix isolated test failures.
           * Verified that all state test cases in `cc_groups_test` now pass cleanly.

           Switching focus to Phase 3: removing legacy setup route guards in `routes.ts`.

           ```
        4. **Mandatory Two-Part Heartbeat Turn**: Every heartbeat turn MUST output
           the visible 4-element markdown progress card in chat AND concurrently
           call `schedule` to re-arm the 20-second timer. You are STRICTLY
           FORBIDDEN from emitting `schedule` in isolation without printing the
           visible progress card in the chat response.
        5. If the subagent remains active, immediately reschedule the 20-second
           heartbeat timer before ending the turn.
    -   **Automatic Timer Cancellation**: When the subagent completes or sends a
        message, the timer is automatically cancelled by `TimerCondition`.
6.  **Phase Checkpointing & Autonomous Continuous Advance**:
    When `worker` completes all tasks in a phase:
    -   Inspect resulting workspace changes (`hg status`, `hg diff`).
    -   Run the automated test suite (`blaze test ...`).
    -   **API Surface Extraction**: Extract public symbols for changed files and
        update `.api_surface_cache.json`.
    -   **Per-Directory Rule Reconciliation**: Reconcile local directory rules
        in `GEMINI.md` / `AGENTS.md`.
    -   **Manual Verification Protocol Generation & Stage 2 Empirical Diff
        Re-Verification (ADR 0009)**:
        -   Inspect the empirical phase VCS diff (`hg status` / `hg diff` or
            `git diff`) against the **Hybrid AST + Diff Classifier**:
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
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/terms.md` and present the updated glossary
        diff to the user.
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
        *   `### Verification Audit`
4.  **Tech Stack & Guidelines Sync**:
    -   If tech stack / workflow altered: update `tech-stack.md` /
        `workflow.md`.
    -   If product capabilities / UX guidelines changed: update `product.md` /
        `product-guidelines.md` (present diff for approval).
5.  **Living Manual Testing Runbook Synchronization
    (`manual_testing/<domain>.md` — ADR 0010)**:
    -   **Autonomous Sync Policy**: Extract verified steady-state test scenarios
        from `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md`.
    -   Reconcile into
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md` using
        structured headings (`### Test <Domain>.<ID>`) without an `ask_question`
        confirmation gate. Verify `hg status` (or `git status`) before and after
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
    -   Audit the final code diff (`hg diff` / `git diff`), touched directories,
        and completed `spec.md` against the **3-Pillar Invariant Taxonomy**:
        1.  *Cross-Cutting Invariant:* New conventions, state invariants, or
            safety guards extending beyond this track.
        2.  *Architecture / Dependency Binding:* Unplanned dependencies or storage
            patterns introduced during implementation.
        3.  *Negative Constraint:* Discarded patterns or discovered gotchas.
    -   Reconcile active ADRs: Audit checkboxes under `## Confirmation` in
        existing ADRs affected by this track, checking off satisfied rules.
    -   If qualifying emergent invariants were introduced that lack an ADR:
        -   **Print Candidates First**: Output the candidate decisions, citing
            concrete code diff lines, file paths, and qualification pillars in chat.
        -   Then invoke `ask_question` with `is_multi_select: true` to confirm:
            "The implementation established new architectural invariants. Record them as ADRs?"
        -   For accepted items, draft `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/NNNN-slug.md`
            and commit.
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
        scenarios from `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md`
        with CLI setup/reset commands and walk the user through testing.
    -   If **Upload CL / Push**: Execute formatting checks (`hg fix`), verify
        `hg status`, and upload to system via `hg upload` (or git push).
    -   If **Review**: Transition directly into `/arm-review`.
    -   If **Archive**: Move track folder to `{PROJECT_CONTEXT_DIR}/archive/`, remove from
        `tracks.md`, and commit.
    -   If **Keep Track Active**: Leave the track folder in place.

## Guardrails

-   **Autonomous Delegation Default**: Multi-phase or multi-task tracks must
    always delegate phase execution to `worker` subagents. The primary agent
    operates as an orchestrator, never monopolizing the main conversational
    thread for heavy code edits.
-   **Mandatory 20-Second Active Heartbeat Streaming**: The orchestrator must
    never remain silent while subagents execute. Maintain an active 20-second
    `schedule` heartbeat loop, streaming visible status updates in chat on every
    interval.
-   **Documentation-Only Manual Testing Invariant**: Document exact setup, seed,
    and reset commands in manual testing runbooks, but NEVER execute mutative
    database, environment reset, or teardown commands autonomously.
-   **Mandatory Completion Next-Steps Barrier**: When all plan tasks are `[x]`
    and document synchronization is complete, you MUST NOT go silent after
    printing summaries or draft CL descriptions. You MUST invoke `ask_question`
    to offer the user clear next steps (Manual testing with the guide, Uploading
    the CL / Pushing, Running `/arm-review`, or Archiving the track).
