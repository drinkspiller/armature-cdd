---
name: arm-new-track
description: Start a new feature or bug fix track with a specification and phased plan. Use when asked to create a new track, start a feature, plan a bug fix, or run /arm-new-track.
persona: Armature Planner
---

# /arm-new-track — Create a New Track

**Purpose:** Start a new feature or bug fix track with a specification and
phased plan through a rigorous, multi-turn decision-tree traversal interview
resolving all open branches and ambiguities.

## Mandatory Execution Guardrails

-   **File Path Sanitization:** When resolving `{PROJECT_ROOT}` or constructing
    file paths for tools (e.g., `write_to_file`, `read_file`), you MUST
    aggressively strip any `file://` prefix. Use standard absolute or relative
    paths to prevent tool execution errors (e.g., use `/google/src/c...` or
    `/usr/local/go...` instead of `file:///google/src/c...` or
    `file:///usr/local/go...`). NEVER pass a `file://` URI to a file operation
    tool.
-   **Raw/Truncated Input Handling:** If the user request contains raw JSON,
    HTML snippets, or truncated text dumps (e.g., `{"activeScroller": "HTML",
    "mainScrollbarWidth": 15, "mainScrollHeight":` or `@[Quote] nalyzer
    description: Lint warnings. Owner: [linter-team@google.com](mailto:l)`),
    treat it purely as contextual description. Do not crash, do not attempt to
    parse it as a command, and do not fail if it is malformed. If the
    description is incomplete, gracefully ask for clarification via
    `ask_question` before proceeding.
-   **Strict Interactive Discipline:** You MUST NEVER generate track artifacts
    (`spec.md`, `plan.md`) or write code in a single autonomous turn. Every
    track requires step-by-step user alignment.
-   **Synchronous Turn-Ending Barrier:** You MUST invoke `ask_question` and end
    your turn at Step 5a (Leaf Probes), Step 5b (Post-Ledger Devil's Advocate
    Gate), Step 5c (ADR Candidate Triage Gate, when candidates qualify), Step 6
    (Spec Approval), and Step 7 (Plan Approval). Do not proceed to subsequent
    steps until the user responds.
-   **Mandatory Decision Tree Ledger:** In EVERY turn of Step 5, you MUST output
    a visible `### Decision Tree Ledger` block showing root branches and their
    spawned child leaves with explicit `[ ]` (OPEN) and `[x]` (Resolved)
    markers.
-   **Lazy Leaf Materialization (Pre-Population Ban):** Future root branches
    MUST remain unexpanded stubs in the ledger (e.g., `- [ ] Branch 2: <Topic>
    (UNEXPLORED)`). You are STRICTLY FORBIDDEN from pre-populating child leaves
    under a branch until the user has confirmed an architectural direction for
    that branch.
-   **Answer-Anchored Provenance Tags:** Every spawned child leaf MUST
    explicitly cite the confirmed user choice that generated it: `- [ ] Leaf
    2.1: <Ambiguity> (Spawned by '<choice>': <question>)`. Leaves without a
    literal proven choice from prior turns are forbidden.
-   **Anti-Dictation Invariant (Zero Un-Queried Decisions):** You MUST NEVER
    assert or output declarative technical specifications, UI layouts, button
    behaviors, countdown cancel rules, or lifecycle state transitions in
    markdown for topics that have not been confirmed by the user. Every
    technical detail is an unresolved leaf ambiguity that MUST be posed via
    `ask_question`.
-   **Child Leaf Spawning Invariant & Depth-2 Horizon:** Selecting an option at
    the root of a branch does NOT close the branch; it actively spawns 1–2
    high-value operational child leaves derived from that specific answer.
    Probing depth is strictly bounded to Depth <= 2 (Root Topic -> Operational
    Child Leaf). Operational leaf answers are terminal (`[x]`) and MUST NOT
    spawn Level 2 grandchildren.
-   **Option Trade-Off Formatting & Mandatory Tool Pairing (Zero Text-Only Stalls):**
    In EVERY turn of Step 5 where choices are presented, you MUST pair a punchy,
    itemized bulleted trade-off breakdown (1–2 concise `Pros` and 1–2 `Cons` per
    candidate approach, plus a 1–2 sentence `Recommendation Rationale`) with an
    immediate native `ask_question` tool call in the exact same turn. End your
    markdown response immediately after the `Recommendation Rationale` paragraph
    with a clean newline. NEVER append transitional self-narration sentences at
    the end of your text (e.g., *"I will now ask for your decision on..."* or
    *"Let's call ask_question..."*), which cause token concatenation and break
    tool parsing. Invoke `ask_question` exclusively as a native structured tool
    call in that exact same turn—never emit raw
    `call:default_api:ask_question{...}` strings in the markdown stream, and
    NEVER end your turn after markdown without calling `ask_question`. In
    `ask_question`, list the recommended choice first with `(Recommended)` and
    append a trailing choice: `"Elaborate on trade-offs and failure modes
    between these options"` (systems and architecture decisions only). Never add
    a manual "Other" option (the UI modal natively provides a write-in field).
    If the user selects elaboration, provide a deep-dive analysis and re-prompt
    the concrete options.
-   **Compound Directive Shielding:** If the user invokes `/arm-new-track`
    alongside other instructions (e.g., `/diagnose`, `Fix`, or implementation
    tasks), you MUST explicitly refuse to write code or generate `plan.md`
    prematurely. Complete all interactive track creation milestones sequentially
    before starting downstream execution.
-   **Premature Draft Command Shielding:** If the user issues commands like
    "Draft the spec", "Looks good, write the spec", or "Proceed to drafting"
    while decision branches or child leaves remain `[ ]` (OPEN), you MUST NOT
    materialize `spec.md` immediately. List the remaining open leaves in the
    ledger and pose the next targeted probe via `ask_question`.
-   **Phase 5b Post-Ledger Devil's Advocate Analysis:** When all branches and
    dynamically spawned leaves reach `[x]`, you MUST NOT immediately converge.
    You MUST execute Phase 5b: audit the combination of confirmed answers, emit
    a structured `### Devil's Advocate Analysis` confronting the user with
    emergent contradictions, operational hazards, and maintainability debt, and
    halt with `ask_question` to reaffirm or reopen branches.
-   **Phase 5c ADR Candidate Triage Gate (Dual-Stage Lifecycle):** Immediately
    following Phase 5b, audit all settled ledger decisions against the 3-Pillar
    Invariant Taxonomy (Cross-Cutting Invariant, Architecture Binding, Negative
    Constraint). If zero decisions qualify, silently bypass directly to Step 6.
    If candidates qualify, render an `### ADR Candidate Triage Table` and obtain
    explicit user confirmation via a multi-select modal in a single turn before
    drafting ADRs.
-   **Anti-Early-Exit & Natural Convergence:** The interview concludes ONLY when
    every branch and child leaf is marked `[x]` (Resolved), Phase 5b Devil's
    Advocate analysis is resolved, and Phase 5c ADR triage has concluded.
-   **Pre-Materialization Hardening Barrier:** You MUST hold specification state
    in memory during Step 5. Canonical `spec.md` is only materialized on disk in
    Step 6 after Phase 5b is reaffirmed, Phase 5c triage concludes, and the user
    approves drafting.
-   **Interruption & Detour Recovery:** If the user asks side questions,
    clarifies requirements, or explores asset tangents mid-traversal, answer the
    inquiry, update the ledger, and resume traversing open leaves. NEVER leap to
    Plan Generation or VCS Commit.

## Protocol

1.  **Context Resolution & Setup Check:**

    -   Resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (armature or
        conductor) per `armature_protocol.md` §7. **CRITICAL:** Strip any
        `file://` prefix from `{PROJECT_ROOT}` before using it in any file
        operations (e.g., `/google/src/c...` or `/usr/local/go...`).
    -   Verify that the following files exist:
        -   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/product.md`
        -   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tech-stack.md`
        -   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/workflow.md`
    -   If ANY of these files are missing, halt immediately with the message:
        "Please run `/arm-setup` first to initialize Armature for this project."

2.  **Get Description & Infer Type:**

    -   If a description was provided in the initial prompt, use it. (Note:
        Handle raw JSON, HTML, or truncated text dumps gracefully as context. Do
        not fail on malformed input like `{"activeScroller": "HTML"...` or
        `@[Quote] nalyzer...`).
    -   If no description was provided, ask via `ask_question`: "What feature or
        bug would you like to work on? Describe it in 1-2 sentences."
    -   Analyze the description to infer the track type (Feature vs. Bug/Chore).
        Do NOT ask the user to classify the type.

3.  **Duplicate Track Check & Initialization:**

    -   Before generating a track ID, check the
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/` directory to ensure no
        existing track has a conflicting name.
    -   Generate a unique, short, descriptive `track_id` based on the
        description (e.g., `dark-mode-toggle`).
    -   Create the directory:
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/`

4.  **Codebase Reconnaissance:**

    -   Read `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tech-stack.md` and
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/product.md` for architectural
        context.
    -   Read `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/terms.md` (if it exists) to
        ground term usage and prevent symbol/concept drift.
    -   Scan the `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/` directory listing
        (filenames only) to build awareness of existing architectural decisions.
    -   Read ALL existing track specs by scanning
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/` for `*/spec.md` files.
    -   If the user's description references specific code areas, scan those
        files/directories to understand existing patterns, interfaces, and
        constraints.
    -   **Proactive Legacy Boundary Discovery (Migration Detection & Immediate
        Turn 1 Ledger)**: If `[Codebase Reconnaissance Context...]` is provided
        in the user prompt or if the user's description reveals parallel
        legacy/modern directories (e.g., migrating from `<legacy_dir>/` to
        `<modern_dir>/`), DO NOT call `grep_search` or `view_file` to search for
        `product.md` or `tech-stack.md`. Immediately in Turn 1:
        1.  Output a visible `### Decision Tree Ledger` containing a Tier 1
            Operational Child Leaf (or root branch) probing the Legacy-Boundary
            Context Fence scope (`<legacy_dir>/` -> `<modern_dir>/`).
        2.  Output Markdown Option Trade-Off Analysis (Candidate Approaches with
            Pros/Cons + Recommendation Rationale) proposing to record
            `legacy_fences` in `armature/tech-stack.md` (`## Legacy & Deprecated
            Boundaries` for repo-wide enforcement) or in track `metadata.json`
            (`legacy_fences` for track-scoped enforcement).
        3.  Invoke `ask_question` in that exact same turn asking the user to
            confirm the legacy fence scope. Never write `spec.md` or `plan.md`
            prematurely.
    -   Use findings to inform the spec questions in the next step — questions
        must reference specific codebase context.

5.  **Recursive Decision-Tree Grill Engine & Post-Ledger Devil's Advocate:**

    Conduct an exhaustive, two-phase interview with the user. The interview
    operates as an active recursive decision tree where choosing an option at
    the root of a branch actively spawns child leaf ambiguities, followed by a
    dedicated post-ledger adversarial critique of the settled choices:

    -   **Phase 5a: Dynamic Leaf Traversal & Ambiguity Elicitation**:

        -   **Mandatory Decision Tree Ledger Block & Atomic Two-Part Turn**:
            In EVERY turn of Step 5, you MUST output a visible `### Decision
            Tree Ledger` block at the top of your markdown response, followed by
            markdown analysis and candidate approaches for the active branch,
            and IMMEDIATELY invoke the native `ask_question` tool call in that
            same turn before concluding. You are STRICTLY FORBIDDEN from
            emitting a bare `ask_question` tool call without preceding markdown
            text and the ledger block, AND you are EQUALLY STRICTLY FORBIDDEN
            from outputting markdown analysis or ledger branches without calling
            `ask_question` in that exact same turn (Zero Text-Only Stalls). Format:

            ```markdown
            ### Decision Tree Ledger
            - [x] Branch 1: <Root Topic> (Confirmed: <Confirmed approach>)
              - [x] Leaf 1.1: <Failure / Error Mode> (Resolved: <Confirmed decision>)
              - [x] Leaf 1.2: <Concurrency / Boundary> (Resolved: <Confirmed decision>)
            - [ ] Branch 2: <Root Topic> (OPEN — probing now)
              - [ ] Leaf 2.1: <Ambiguity> (Spawned by '<choice>': <question>) (OPEN — probing now)
            - [ ] Branch 3: <Root Topic> (UNEXPLORED)
            ```

            Track state accurately: `[ ]` indicates an unresolved root or child
            leaf; `[x]` indicates a confirmed decision.

        -   **Lazy Leaf Materialization (Pre-Population Ban)**: Future root
            branches MUST remain unexpanded stubs in the ledger (e.g., `- [ ]
            Branch 3: Drawer State (UNEXPLORED)`). You are STRICTLY FORBIDDEN
            from pre-populating child leaves under a branch until the user has
            confirmed an architectural direction for that branch.

        -   **Answer-Anchored Provenance Tags**: Every spawned child leaf MUST
            explicitly cite the confirmed user choice that generated it: `- [ ]
            Leaf 2.1: Fallback handling (Spawned by '@switch': What renders in
            @default if faq.id is unrecognized?)`. Leaves without a literal
            proven choice from prior turns are forbidden.

        -   **Child Leaf Spawning Invariant & Depth-2 Horizon (Terminality
            Rule)**: Selecting an option at the root of a branch does NOT close
            the branch; it actively spawns 1–2 high-value Tier 1 operational
            child leaves derived from the specific choice made. Probing depth is
            strictly bounded to Depth <= 2 (Root Topic -> Operational Child
            Leaf). Operational child leaf answers are terminal (`[x]`) and MUST
            NOT spawn Level 2 grandchildren.

            -   *Tier 1 (Mandatory Operational Probes)*: Failure modes,
                network/RPC drops, timeout thresholds, degraded fallback states,
                payload/token bounds, multi-tab sync, concurrency races, schema
                evolution contracts.
            -   *Tier 2 (Deferred Implementation Details — Prune from
                Interview)*: Pure cosmetic styling (exact pixel padding, hex
                colors), micro-copy variations, internal helper function naming.
                *Rule:* Do NOT spawn interactive interview questions for Tier 2
                items. Defer them as sensible defaults in `plan.md`.

        -   **Anti-Dictation Invariant (Zero Un-Queried Decisions)**: You are
            STRICTLY FORBIDDEN from asserting or outputting declarative
            implementation designs, button placements, countdown rules, or
            lifecycle state transitions in markdown for topics that have not
            been confirmed via `ask_question`. Every technical detail is an
            unresolved leaf ambiguity that MUST be posed via `ask_question`.

        -   **Testing Strategy Classification**: Classify manual testing depth:

            -   *Interactive / Stateful / Route / API Tracks*: Full
                `manual_testing.md` runbook with environment setup, CLI reset
                tooling, persona matrices, and sequential route test cases.
            -   *Pure Refactor / Utility / Chore Tracks*: Lightweight
                `manual_testing.md` with concise smoke and sanity checks
                alongside automated unit tests. When requirements for a pure
                refactor or utility track are already clear, formulate the
                Testing Strategy classification and proceed directly to Phase 5b
                without injecting redundant questioning loops.

        -   **Questioning Mechanics & Option Trade-Off Analysis**:

            -   **Report First, Ask Second (Atomic Two-Part Response Contract):**
                In EVERY turn where choices are presented, you MUST output the
                markdown analysis and candidate breakdown FIRST, followed
                immediately by the native `ask_question` tool call in that same
                turn.
            -   **Itemized Bulleted Hierarchy:** Format candidate approaches
                using punchy, high-signal bullets:
                -   `**Option 1: <Name>** *(Recommended)*`
                    -   `*Pros:*` 1–2 punchy, substantive bullet points.
                    -   `*Cons:*` 1–2 punchy, substantive bullet points.
                -   `**Option 2: <Name>**`
                    -   `*Pros:*` 1–2 punchy, substantive bullet points.
                    -   `*Cons:*` 1–2 punchy, substantive bullet points.
            -   **Recommendation Rationale:** Conclude with 1–2 declarative
                sentences explaining why the recommended option was chosen,
                grounded in codebase constraints, latency, memory budgets,
                schema migrations, or failure resilience.
            -   **Clean Markdown Termination & Mandatory Native Tool Call Pairing
                (Zero Trailing Narration & Zero Text-Only Stalls):** End your
                markdown prose immediately after the `Recommendation Rationale`
                paragraph. NEVER append transitional self-narration sentences at
                the end of your prose (e.g., *"I will now ask for your decision
                on..."* or *"Let's call ask_question..."*), which cause token
                concatenation and break tool parsing. Immediately invoke
                `ask_question` exclusively as a native structured tool call in
                the same turn—never emit raw `call:default_api:ask_question{...}`
                text in the markdown stream, and NEVER end your turn after
                markdown without calling `ask_question` when presenting choices,
                branches, or trade-offs.
            -   **Modal Parameters (`ask_question`):**
                -   Ask questions **strictly one at a time**.
                -   List the recommended option first with `(Recommended)` and
                    provide 2–4 calibrated domain options.
                -   **Trailing Elaboration Option (Systems & Architecture
                    Only):** Append a trailing on-demand elaboration option
                    (`"Compare technical trade-offs and failure modes in
                    detail"`) **ONLY** when evaluating complex systems, data
                    model, or infrastructure architecture decisions where
                    deep-dive performance or failure analysis adds value.
                    **NEVER** append an elaboration option to `ask_question` for
                    UX copywriting, visual presentation, layout styling, or
                    simple product preferences.
                -   **Native Write-In Field:** Never add a manual "Other"
                    option; the UI modal natively provides a write-in text
                    field.
            -   **Elaboration Detour:** If the user selects the elaboration
                option, output a deep-dive analysis (comparative trade-off
                matrix, failure cascades, memory bounds, migration costs) and
                re-prompt the concrete choices.
            -   **MANDATORY:** End your turn after each `ask_question` call to
                wait for the user's answer. Never end your turn before calling
                `ask_question` when choices, branches, or decisions are presented.

        -   **Inline Glossary Elicitation (`terms.md`)**: If a decision
            introduces domain terminology, offer to record it in
            `{PROJECT_CONTEXT_DIR}/terms.md`.

    -   **Phase 5b: Post-Ledger Devil's Advocate Analysis (Red-Teaming Confirmed
        Answers)**:

        -   **Trigger**: Occurs if and only if EVERY branch and dynamically
            spawned child leaf in the Decision Tree Ledger is marked `[x]`
            (Resolved) with zero open items.
        -   **Execution**:
            1.  Audit the combination of confirmed answers across all resolved
                branches in the ledger.
            2.  Output a structured `### Devil's Advocate Analysis:
                Stress-Testing Confirmed Decisions` directly beneath the
                resolved ledger.
            3.  Formulate 2–3 concrete adversarial challenges targeting:
                -   *Emergent Contradictions*: Unintended friction or mismatch
                    between separate confirmed choices.
                -   *Operational & Maintenance Debt*: Hardcoded template markup
                    vs headless schemas, excessive client-side state, DOM bloat.
                -   *Failure Cascades*: Degraded network scenarios, rapid user
                    interrupts, timeout recovery under load.
            4.  **Sequential Single-Finding Presentation (Strict One-at-a-Time
                Rule)**:
                -   Present each adversarial challenge **strictly one by one**
                    in sequential turns.
                -   For each challenge:
                    -   Report the concrete trade-off, specific hazard, and 2–3
                        actionable countermeasure options in markdown first.
                    -   Call `ask_question` with options formatted in the user's
                        voice (e.g., "(Recommended) Apply countermeasure:
                        <specific fix>", "Reopen Branch <N> to revise approach",
                        "Accept trade-off as acceptable debt").
                    -   **MANDATORY:** End your turn and collect the user's
                        decision for that specific finding before presenting any
                        subsequent challenge.
            5.  **Reopening vs. Natural Convergence**:
                -   If the user selects to reopen a branch during any finding,
                    flip that branch and its consequence leaf back to `[ ]`
                    (OPEN), probe the revised ambiguity, and return to Phase 5b
                    when re-resolved.
                -   Once all challenges have been resolved individually, ONLY
                    THEN present the structured **Convergence Summary** in
                    markdown synthesizing all settled decisions, and proceed to
                    **Phase 5c: ADR Candidate Triage Gate**.

    -   **Phase 5c: ADR Candidate Triage Gate (Dual-Stage Lifecycle)**:

        -   **Trigger**: Occurs immediately after Phase 5b concludes and all
            adversarial challenges are resolved, before Step 6 (`spec.md`
            materialization).
        -   **3-Pillar Invariant Taxonomy Audit**: Audit all settled decisions
            (`[x]`) in the Decision Tree Ledger against the three qualification
            pillars:
            1.  *Cross-Cutting Invariant:* Establishes a convention, contract,
                or state invariant that constrains future tracks or touches
                multiple components (e.g., optimistic UI rollback rules,
                error-envelope schemas, multi-tab sync).
            2.  *Architecture / Dependency Binding:* Binds the repository to a
                storage engine, transport protocol, or third-party library that
                would be costly to rip out later (e.g., SQLite WAL, WebSocket
                vs. SSE, Protobuf vs. JSON).
            3.  *Negative Constraint (Discarded Alternative):* Rejects an
                obvious, standard pattern due to a subtle project gotcha or race
                condition (e.g., forbidding `sessionStorage` because it does not
                sync across tabs).
            4.  Decisions failing all three (local component markup, single
                route slugs, error strings, styling) are classified as `[Track
                Spec Only]`.
        -   **Silent Zero-Candidate Bypass**:
            -   If zero settled decisions qualify under the 3-Pillar Taxonomy,
                the agent MUST silently bypass Phase 5c directly to Step 6 Spec
                Materialization without generating an extra modal prompt or
                callout note.
        -   **Interactive Triage Gate (when $\ge 1$ candidates qualify)**:

            -   Render an `### ADR Candidate Triage Table` mapping each
                qualifying decision to its pillar, proposed title, and one-line
                rationale:

                ```markdown
                ### ADR Candidate Triage Table
                | Decision | Scope & Pillar | Proposed ADR Title | Recommendation |
                | :--- | :--- | :--- | :--- |
                | Branch 1: In-Memory LRU Cache | Pillar 2: Architecture Binding | Use In-Memory LRU with TTL for Client Asset Caching | [ADR Candidate] |
                | Leaf 1.1: 100-Item / 25MB Cap | Pillar 1: Cross-Cutting Invariant | Enforce 25MB Fixed Heap Budget on In-Memory Caches | [ADR Candidate] |
                ```
            -   Call `ask_question` with a multi-select prompt allowing the user
                to confirm which ADRs to materialize:

                -   `question`: "Confirm which architectural decisions to record
                    as ADRs:"
                -   `options`: Checkboxes for each candidate ADR (e.g.,
                    `"(Recommended) Record ADR: Use In-Memory LRU with TTL"`,
                    `"(Recommended) Record ADR: Enforce 25MB Fixed Heap
                    Budget"`, `"Skip ADR creation — keep track-specific only"`).
            -   **MANDATORY:** End your turn and wait for the user's response.
            -   For each confirmed candidate:

                -   Determine the next sequential number (e.g.,
                    `adr/0004-slug.md`).
                -   Draft the ADR in standard MADR format (`Status: ACCEPTED`,
                    `Context`, `Decision`, `Consequences`, `Confirmation`
                    checklist).
                -   Write to
                    `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/NNNN-slug.md`
                    using `write_to_file`.

6.  **Spec & Manual Testing Materialization & Final Confirmation:**

    -   ONLY NOW, write the canonical specification to
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/spec.md` using
        `write_to_file`.
    -   Write
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md`
        based on `manual_testing_template.md` tailored to the classified testing
        depth.
    -   Present `spec.md` and `manual_testing.md` via `notify_user` with
        `PathsToReview`.
    -   Present options using `ask_question`: "Approve" (Proceed to planning),
        "Revise" (Suggest manual edits).
    -   **MANDATORY:** End your turn and wait for explicit user approval before
        proceeding to plan generation.

7.  **Interactive Plan Generation:**

    -   Verify the spec is approved.
    -   Read confirmed spec and
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/workflow.md`.
    -   Generate hierarchical plan with Phases, Tasks, and Sub-tasks with `[ ]`
        checkboxes.
    -   **Developer Test Tooling Tasks**: If new routes, state guards, or flags
        are added, ensure Phase 1 includes explicit tasks for developer reset
        tooling, CLI scripts, or fixture seeding needed by `manual_testing.md`.
    -   **Verification Bridge**: For each verification checkbox `[ ]` defined in
        an ADR's Confirmation section, inject a corresponding explicit
        verification task into `plan.md`.
    -   **Phase Checkpointing**: If `workflow.md` defines phase checkpointing,
        inject Phase Completion meta-tasks at the end of each Phase.
    -   Write to
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/plan.md` using
        `write_to_file`.
    -   Present via `notify_user` with `PathsToReview` and `ask_question`:
        "Approve", "Revise".
    -   **MANDATORY:** End your turn and wait for explicit user approval.

8.  **Generate Remaining Track Artifacts:**

    -   Create
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/metadata.json`
        containing: `track_id`, inferred `type`, `status` (`planned`),
        timestamps, and `description`.
    -   Write `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/index.md`
        containing summary and relative links to `spec.md`, `plan.md`,
        `manual_testing.md`, and `metadata.json`.
    -   Append new track to `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md`: `-
        [ ] **Track: <Track Title>** _Link:
        [./tracks/<track_id>/](./tracks/<track_id>/)_`

9.  **Commit Changes:**

    -   Commit the new track directory and updated `tracks.md` using VCS
        commands.
    -   Commit message: `chore(armature): Add new track '<description>'`

10. **Confirm Completion:**

    -   Display: "✅ Track `<track_id>` created! Run `/arm-implement` to start
        working through the plan."

## Guardrails

-   **Compound Directive Shielding**: Never start implementation or write code
    prematurely.
-   **Turn-Ending Barriers**: Enforce strict synchronous pauses at Step 5, Step
    6, and Step 7 via `ask_question`.
-   **Pre-Materialization Barrier**: Hold `spec.md` in memory during Step 5.
-   **Continuous Decision-Tree Traversal & Ambiguity Resolution**: Never
    conclude an interview turn while decision branches, dependencies, failure
    modes, or architectural ambiguities remain unresolved.
-   **File Path Sanitization**: Always strip `file://` prefixes from paths
    before using file tools (e.g., `/google/src/c...`, `/usr/local/go...`).
-   **Raw/Truncated Input**: Treat malformed JSON/HTML or truncated text dumps
    as contextual descriptions, not commands.
