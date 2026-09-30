---
name: arm-new-track
description: Start a new feature or bug fix track with a specification and phased plan. Use when asked to create a new track, start a feature, plan a bug fix, or run /arm-new-track.
persona: Armature Planner
---

# /arm-new-track — Create a New Track

**Purpose:** Start a new feature or bug fix track with a specification and
phased plan through a rigorous, multi-turn decision-tree traversal interview
resolving all open rounds, questions, and ambiguities.

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
    your turn at Step 5a (Round and Question Probes), Step 5b (Devil's Advocate
    Gate), Step 5c (ADR Candidate Triage Gate, when candidates qualify), Step 6
    (Spec Approval), and Step 7 (Plan Approval). Do not proceed to subsequent
    steps until the user responds.
-   **Mandatory Progress List:** In EVERY turn of Step 5, you MUST output a
    visible grouped progress list (`**Settled**` / `**Now**` / `**Up next**`)
    showing rounds and the questions spawned under them. Settled items carry
    their short answer; the active item appears under `**Now**`; queued
    questions and unexplored rounds appear under `**Up next**`. Omit a group
    when it is empty.
-   **Lazy Question Materialization (Pre-Population Ban):** Future rounds MUST
    remain unexpanded stubs under `**Up next**` (e.g., `- Round 2, <Topic>`).
    You are STRICTLY FORBIDDEN from listing questions under a round until the
    user has confirmed an architectural direction for that round.
-   **Answer-Anchored Provenance:** Every spawned follow-up question MUST say
    which confirmed user answer generated it, stated in the settled line (e.g.,
    `Round 2 settled: <answer>. This opens a follow-up on <topic>.`) or in the
    `**Context:**` block. Questions without a literal proven choice from prior
    turns are forbidden.
-   **Anti-Dictation Invariant (Zero Un-Queried Decisions):** You MUST NEVER
    assert or output declarative technical specifications, UI layouts, button
    behaviors, countdown cancel rules, or lifecycle state transitions in
    markdown for topics that have not been confirmed by the user. Every
    technical detail is an unresolved question that MUST be posed via
    `ask_question`.
-   **Follow-Up Question Spawning Invariant & Depth-2 Horizon:** Selecting an
    option for a round does NOT close the round; it actively spawns 1–2
    high-value operational follow-up questions derived from that specific
    answer. Probing depth is strictly bounded to Depth <= 2 (Round -> Question).
    Question answers are terminal (Settled) and MUST NOT spawn further nested
    questions.
-   **Interview Turn Format & Mandatory Tool Pairing (Zero Text-Only Stalls):**
    In EVERY turn of Step 5 where choices are presented, you MUST render the
    interview turn layout defined in Phase 5a (settled line, progress list,
    `---`, `## Round R, Question Q of N: <Topic>` headline, `**Context:**`,
    option cards with `**Pros:**` / `**Cons:**` / `**Implications:**`, and `###
    Recommendation: Option N` with a 1–3 sentence rationale) and pair it with an
    immediate native `ask_question` tool call in the exact same turn. End your
    markdown response immediately after the recommendation rationale paragraph
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
    while rounds or questions remain unsettled (listed under `**Now**` or `**Up
    next**`), you MUST NOT materialize `spec.md` immediately. List the remaining
    open questions in the progress list and pose the next targeted probe via
    `ask_question`.
-   **Phase 5b Devil's Advocate Analysis:** When all rounds and dynamically
    spawned questions are Settled, you MUST NOT immediately converge. You MUST
    execute Phase 5b: audit the combination of confirmed answers, emit a
    structured `### Devil's Advocate Analysis` confronting the user with
    emergent contradictions, operational hazards, and maintainability debt, and
    halt with `ask_question` to reaffirm or reopen rounds.
-   **Phase 5c ADR Candidate Triage Gate (Dual-Stage Lifecycle):** Immediately
    following Phase 5b, audit all settled decisions against the 3-Pillar
    Invariant Taxonomy (Cross-Cutting Invariant, Architecture Binding, Negative
    Constraint). If zero decisions qualify, silently bypass directly to Step 6.
    If candidates qualify, render an `### ADR Candidate Triage Table` and obtain
    explicit user confirmation via a multi-select modal in a single turn before
    drafting ADRs.
-   **Anti-Early-Exit & Natural Convergence:** The interview concludes ONLY when
    every round and question is Settled, Phase 5b Devil's Advocate analysis is
    resolved, and Phase 5c ADR triage has concluded.
-   **Pre-Materialization Hardening Barrier:** You MUST hold specification state
    in memory during Step 5. Canonical `spec.md` is only materialized on disk in
    Step 6 after Phase 5b is reaffirmed, Phase 5c triage concludes, and the user
    approves drafting.
-   **Interruption & Detour Recovery:** If the user asks side questions,
    clarifies requirements, or explores asset tangents mid-traversal, answer the
    inquiry, update the progress list, and resume traversing open questions.
    NEVER leap to Plan Generation or VCS Commit.

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
        Turn 1 Progress List)**: If `[Codebase Reconnaissance Context...]` is
        provided in the user prompt or if the user's description reveals
        parallel legacy/modern directories (e.g., migrating from `<legacy_dir>/`
        to `<modern_dir>/`), DO NOT call `code_search` or `view_file` to search
        for `product.md` or `tech-stack.md`. Immediately in Turn 1:
        1.  Output the visible progress list with a `**Now**` entry for the
            round (or Tier 1 operational question) probing the Legacy-Boundary
            Context Fence scope (`<legacy_dir>/` -> `<modern_dir>/`).
        2.  Output the interview turn (headline, `**Context:**`, option cards
            with `**Pros:**` / `**Cons:**` / `**Implications:**`, and `###
            Recommendation: Option N`) proposing to record `legacy_fences` in
            `armature/tech-stack.md` (`## Legacy & Deprecated Boundaries` for
            repo-wide enforcement) or in track `metadata.json` (`legacy_fences`
            for track-scoped enforcement).
        3.  Invoke `ask_question` in that exact same turn asking the user to
            confirm the legacy fence scope. Never write `spec.md` or `plan.md`
            prematurely.
    -   Use findings to inform the spec questions in the next step — questions
        must reference specific codebase context.

5.  **Recursive Decision-Tree Grill Engine & Devil's Advocate:**

    Conduct an exhaustive, two-phase interview with the user. The interview
    operates as an active recursive decision tree organized into rounds, where
    choosing an option for a round actively spawns follow-up questions, followed
    by a dedicated adversarial critique of the settled choices:

    -   **Phase 5a: Round and Question Traversal & Ambiguity Elicitation**:

        -   **Mandatory Interview Turn Layout & Atomic Two-Part Turn**: In EVERY
            turn of Step 5, you MUST output the visible interview turn below,
            top to bottom, and IMMEDIATELY invoke the native `ask_question` tool
            call in that same turn before concluding. You are STRICTLY FORBIDDEN
            from emitting a bare `ask_question` tool call without the preceding
            markdown turn and progress list, AND you are EQUALLY STRICTLY
            FORBIDDEN from outputting markdown analysis or the progress list
            without calling `ask_question` in that exact same turn (Zero
            Text-Only Stalls).

            1.  *Settled line* (skip on the very first question): one plain
                sentence confirming the previous answer and, if relevant, which
                follow-up it opened.
            2.  *Progress list*: `**Settled**` (one bullet per settled round or
                question with its short answer), `**Now**` (one bullet for the
                active question), and `**Up next**` (queued questions and
                unexplored round stubs). Omit a group when it is empty.
            3.  *Separator*: `---`
            4.  *Headline*: `## Round <R>, Question <Q> of <N>: <Topic>` (H2).
                `N` is the number of questions currently known in that round.
            5.  *Context*: `**Context:** <one-line framing>:`, then 2–4 bullets
                on what the decision affects, then a short paragraph on current
                state and the track goal.
            6.  *Spacer*: a line containing only `&nbsp;`.
            7.  *Option cards*: one plain blockquote per option, with a blank
                line between cards. Only the labels are bold; each row is one or
                two short sentences.
            8.  *Spacer*: `&nbsp;`.
            9.  *Recommendation*: `### Recommendation: Option <N>` (H3), then
                1–3 sentences of rationale grounded in the codebase or track
                scope.
            10. *`ask_question` tool call* in the same turn, with no trailing
                narration after the rationale.

            Format:

            ```markdown
            Question 2.1 settled: <short answer>. This opens a follow-up on <topic>.

            **Settled**
            - Round 1, <Topic>: <short answer>
            - Round 2, <Topic>: <short answer>
            - Question 2.1, <Topic>: <short answer>

            **Now**
            - Question 2.2, <Topic>

            **Up next**
            - Round 3, <Topic>

            ---

            ## Round 2, Question 2 of 2: <Topic>

            **Context:** <One-line framing>:

            - <What the decision affects>
            - <What the decision affects>

            <Short paragraph on current state and the track goal.>

            &nbsp;

            > **Option 1: <Name>** (Recommended)
            >
            > - **Pros:** <plain text>
            > - **Cons:** <plain text>
            > - **Implications:** <plain text>

            > **Option 2: <Name>**
            >
            > - **Pros:** <plain text>
            > - **Cons:** <plain text>
            > - **Implications:** <plain text>

            &nbsp;

            ### Recommendation: Option 1

            <1–3 sentences of rationale grounded in the codebase or track scope.>
            ```

            Track state accurately: items under `**Now**` and `**Up next**` are
            unresolved; items under `**Settled**` are confirmed decisions. Do
            not use tables, icons, emoji, glyphs, progress bars, or `[!NOTE]` /
            `[!TIP]` callouts in the interview turn.

        -   **Lazy Question Materialization (Pre-Population Ban)**: Future
            rounds MUST remain unexpanded stubs under `**Up next**` (e.g., `-
            Round 3, Drawer state`). You are STRICTLY FORBIDDEN from listing
            questions under a round until the user has confirmed an
            architectural direction for that round.

        -   **Answer-Anchored Provenance**: Every spawned follow-up question
            MUST say which confirmed user answer generated it, in the settled
            line or the `**Context:**` block (e.g., `Round 2 settled: render FAQ
            bodies with @switch. This opens a follow-up on what renders in
            @default when faq.id is unrecognized.`). Questions without a literal
            proven choice from prior turns are forbidden.

        -   **Follow-Up Question Spawning Invariant & Depth-2 Horizon
            (Terminality Rule)**: Selecting an option for a round does NOT close
            the round; it actively spawns 1–2 high-value Tier 1 operational
            follow-up questions derived from the specific choice made. Probing
            depth is strictly bounded to Depth <= 2 (Round -> Question).
            Question answers are terminal (Settled) and MUST NOT spawn further
            nested questions.

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
            unresolved question that MUST be posed via `ask_question`.

        -   **Zero Mid-Interview Subagent Re-Dispatch & Premature Exit
            Pushback**: Once problem exploration has begun or prior interview
            turns (`[Agent]: ... [User]: ...`) exist in the prompt history,
            **NEVER** invoke `invoke_subagent` to restart reconnaissance. If the
            user asks to draft the spec prematurely (e.g., *"Let's draft the
            spec"*) after confirming a round's choice (such as WebSocket +
            heartbeat), do **NOT** finalize `spec.md` or call `invoke_subagent`.
            Instead, explicitly push back on premature drafting, expand the
            progress list with dependent operational follow-up questions under
            `**Up next**` conditioned on that choice (e.g., reconnect backoff
            jitter algorithm, tab backgrounding/suspension disconnect handling,
            state invariants, multi-tab sync, and concurrency dependencies),
            present codebase-grounded adversarial challenges (e.g., server
            restart thundering herd socket storms, stale presence ghost states),
            and pose the next targeted probe via `ask_question`.

        -   **Data Migration & Storage Evolution Pattern Contrasting**: When
            probing database migrations or storage synchronization
            architectures, always contrast all three primary patterns in your
            trade-off breakdown before locking the path: (1) Application-level
            dual-writing, (2) Change Data Capture / Spanner change streams, and
            (3) Lazy read-repair / background backfill.

        -   **Testing Strategy Classification (Stage 1 Provisional Intent
            Scoping — ADR 0009)**: Evaluate the confirmed specification and
            target file list to classify manual testing depth:

            -   *Interactive / Stateful / Route / API Tracks (Tier 1: Standard
                Stateful 3-Part Fixture Triad)*: Full `manual_testing.md`
                runbook with environment setup, 3-Part Fixture Triad (`Migration
                -> Seed -> Reset`), persona matrices, and dual-URL
                (`localhost` + remote workstation proxy) route test cases. Mandatory
                whenever state machines, reactive stores, router navigation
                guards (`canActivate`), conditional auth/role gates
                (`*ngIf="user.isAdmin"`, `@if`), or RPC/API calls are modified.
            -   *Visual-Only / Presentational UI Tracks (Tier 2: Provisional
                `Micro-Verification Plan`)*: When the confirmed specification
                and target file list involve strictly presentational UI
                changes—restricted to template/style files (`.html`, `.css`,
                `.scss`, `.sass`, `.less`, `.svg`) or component files (`.ts`,
                `.tsx`, `.jsx`, `.vue`) modifying only markup, styling, or
                static text copy—classify the track as **Visual-Only
                (`[Micro-Verification Plan]`)**.
                -   *Orphaned Dead-Code Cleanup Exemption*: Explicitly permits
                    deleting or renaming unused local event handlers (e.g.,
                    `onCardClick()`, `handleCardClick()`), local display helper
                    functions, or unused imports/props that were directly
                    orphaned by removing or restyling a visual UI element.
                -   *Disqualification Rule*: Any modification to state
                    management, router guards, role/permission gates, or backend
                    RPCs disqualifies the track from Tier 2 and escalates to
                    Tier 1.
            -   *Pure Refactor / Utility / Chore Tracks*: Lightweight
                `manual_testing.md` with concise smoke and sanity checks
                alongside automated unit tests. When requirements for a pure
                refactor or utility track are already clear, formulate the
                Testing Strategy classification and proceed directly to Phase 5b
                without injecting redundant questioning loops.

        -   **Questioning Mechanics & Option Trade-Off Analysis**:

            -   **Report First, Ask Second (Atomic Two-Part Response
                Contract):** In EVERY turn where choices are presented, you MUST
                output the markdown interview turn FIRST, followed immediately
                by the native `ask_question` tool call in that same turn.
            -   **Option Cards:** Present each candidate approach as its own
                plain blockquote card, with a blank line between cards:
                -   `> **Option 1: <Name>** (Recommended)`, then `>`, then `> -
                    **Pros:** <plain text>`, `> - **Cons:** <plain text>`, `> -
                    **Implications:** <plain text>`.
                -   `> **Option 2: <Name>**` with the same three rows.
                -   Only the labels are bold; the text after them is plain. Each
                    row is one or two short, substantive sentences.
            -   **Recommendation:** After the last card and an `&nbsp;` spacer,
                write `### Recommendation: Option <N>` followed by 1–3
                declarative sentences explaining why the recommended option was
                chosen, grounded in codebase constraints, latency, memory
                budgets, schema migrations, failure resilience, or track scope.
            -   **Clean Markdown Termination & Mandatory Native Tool Call
                Pairing (Zero Trailing Narration & Zero Text-Only Stalls):** End
                your markdown prose immediately after the recommendation
                rationale paragraph. NEVER append transitional self-narration
                sentences at the end of your prose (e.g., *"I will now ask for
                your decision on..."* or *"Let's call ask_question..."*), which
                cause token concatenation and break tool parsing. Immediately
                invoke `ask_question` exclusively as a native structured tool
                call in the same turn—never emit raw
                `call:default_api:ask_question{...}` text in the markdown
                stream, and NEVER end your turn after markdown without calling
                `ask_question` when presenting choices, rounds, or trade-offs.
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
            -   **User `@[Quote]` Turns: Pre-Selection Clarification vs.
                Final-Question Confirmation (`ask_question` Non-Bypass Rule):**
                Every turn MUST contain BOTH non-empty visible markdown text
                FIRST and a native `ask_question` tool call SECOND (never emit a
                bare `ask_question` call with empty markdown text, and never
                emit markdown text without `ask_question`):
                -   *Case A — Final-Question Resolution or Leading Confirmation
                    Question:* When only ONE open question remains (the
                    `**Now**` item with nothing under `**Up next**`) and the
                    user replies by selecting an option, stating a
                    policy/threshold, OR asking a leading confirmation question
                    verifying the final question's behavior (e.g., `@[Quote]
                    Route disabled. does the guard redirect back to
                    /setup/sharing-permissions?` alongside commit/spec notes
                    like `capture this in the CL description`), treat that final
                    question as **Settled**:
                    1.  **Visible Markdown Part (Required First):** Directly
                        answer the user's confirmation question, confirm the CL
                        description commitment, output the settled line and the
                        progress list with **all** rounds and questions under
                        `**Settled**`, and output `### Devil's Advocate
                        Analysis: Stress-Testing Confirmed Decisions` (`####
                        Finding 1 of N: <Title>`) with 2–3 countermeasure option
                        cards (`**Pros:**` / `**Cons:**` / `**Implications:**`)
                        and `### Recommendation: Option N`.
                    2. **Native Tool Call Part (Required Second in Same Turn):** After the visible markdown text, invoke `ask_question` for Finding 1.
                -   *Case B — Mid-Interview Pre-Selection Blocking
                    Clarification:* When the user explicitly says `"Wait —
                    before I pick..."` or asks how a UI trigger, modal, or
                    network/RPC flow works *before* choosing an option for the
                    open question (`Question N.M`):
                    1.  **Visible Markdown Part (Required First):** Answer the
                        user's technical question step-by-step in visible
                        markdown, keep `Question N.M` under `**Now**` in the
                        progress list, and re-present its option cards
                        (`**Pros:**` / `**Cons:**` / `**Implications:**`) and
                        `### Recommendation: Option N`.
                    2.  **Native Tool Call Part (Required Second in Same
                        Turn):** Invoke `ask_question` for `Question N.M`.
            -   **MANDATORY:** End your turn after each `ask_question` call to
                wait for the user's answer. Never end your turn before calling
                `ask_question` when choices, rounds, or decisions are presented.

        -   **Inline Glossary Elicitation (`terms.md`)**: If a decision
            introduces domain terminology, offer to record it in
            `{PROJECT_CONTEXT_DIR}/terms.md`.

    -   **Phase 5b: Devil's Advocate Analysis (Red-Teaming Confirmed Answers)**:

        -   **Trigger**: Fires automatically in the exact turn that the final
            open question in the progress list moves to `**Settled**` with
            nothing left under `**Now**` or `**Up next**`.
        -   **Execution**:
            1.  Audit the combination of confirmed answers across all settled
                rounds and questions in the progress list.
            2.  Output a structured `### Devil's Advocate Analysis:
                Stress-Testing Confirmed Decisions` directly beneath the
                all-settled progress list in visible markdown text (never leave
                visible markdown text empty).
            3.  Identify 2–3 concrete adversarial challenges across the design
                (*Emergent Contradictions*, *Operational & Maintenance Debt*,
                *Failure Cascades*), but present **ONLY Finding 1** in the
                initial Phase 5b turn.
            4.  **Sequential Single-Finding Presentation & Strict Anti-Collapse Ban**:
                -   Present each adversarial challenge **strictly one by one**
                    in separate sequential turns (`#### Finding 1 of N: <Title>`,
                    then in the next turn `#### Finding 2 of N: <Title>`).
                -   **Strict Ban on Self-Answered `*Risk:* / *Mitigation:*` Lists & Multi-Finding Dumps**:
                    NEVER output all 2–3 Devil's Advocate challenges in a single
                    turn, and NEVER write static `*Risk:*` and `*Mitigation:*`
                    bullets that pre-decide the countermeasure without calling
                    `ask_question`.
                -   **Strict Ban on Same-Turn Phase 5b + Phase 5c Batching**:
                    NEVER output a `### Phase 5c` or `### ADR Candidate Triage Table`
                    heading in the same turn as Phase 5b, and NEVER call
                    `write_to_file` during Phase 5b. If the user asks to bundle
                    or skip ahead across phases, explicitly state in visible
                    markdown that **Phase 5b and Phase 5c require sequential
                    interactive gates** and cannot be collapsed into one turn,
                    then present ONLY Finding 1.
                -   **Two-Part Turn Contract (Visible Markdown FIRST -> `ask_question` SECOND)**:
                    -   *Part 1 (Visible Markdown):* Write the settled line and
                        updated progress list, the `### Devil's Advocate
                        Analysis` heading, the single active challenge (`####
                        Finding 1 of N`), 2–3 countermeasure option cards with
                        `**Pros:**`, `**Cons:**`, and `**Implications:**`, and
                        `### Recommendation: Option N` with its rationale.
                    -   *Part 2 (Native Tool Call):* After the visible markdown
                        text, invoke `ask_question` with options phrased in the
                        user's voice (e.g., `"(Recommended) Apply
                        countermeasure: <specific fix>"`, `"Reopen Round <N> to
                        revise approach"`, `"Accept trade-off as acceptable
                        debt"`). Never emit a bare `ask_question` call without
                        visible markdown text.
            5.  **Reopening vs. Natural Convergence (Implicit Phase 5c Transition)**:
                -   If the user selects to reopen a round during any finding,
                    move that round and its affected question from `**Settled**`
                    back to `**Now**` / `**Up next**`, probe the revised
                    ambiguity via `ask_question`, and return to Phase 5b when
                    re-resolved.
                -   In the exact turn where the user resolves the **final**
                    Phase 5b finding (e.g., Finding 2 of 2), output in visible
                    markdown the `### Phase 5b Convergence Summary` synthesizing
                    all settled decisions, and in that **same turn** execute
                    **Phase 5c: ADR Candidate Triage Gate** (rendering the
                    `### ADR Candidate Triage Table` in visible markdown +
                    calling `ask_question` with `is_multi_select: true` if
                    $\ge 1$ candidates qualify, or silently bypassing to Step 6
                    if 0 qualify).

    -   **Phase 5c: ADR Candidate Triage Gate (Dual-Stage Lifecycle)**:

        -   **Trigger**: Occurs immediately after Phase 5b concludes and all
            adversarial challenges are resolved, before Step 6 (`spec.md`
            materialization).
        -   **3-Pillar Invariant Taxonomy Audit**: Audit all settled decisions
            (listed under `**Settled**`) against the three qualification
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
            -   If and only if **zero** settled decisions qualify under Pillars
                1, 2, or 3 (e.g., strictly local single-component CSS/copy/markup
                tweaks with no cross-cutting invariant, architecture binding, or
                negative constraint), silently bypass Phase 5c directly to Step
                6 in that **same turn**: default `{PROJECT_CONTEXT_DIR}` to
                `armature` (`armature/tracks/<track_id>/...`) without calling
                `view_file` to check `armature/product.md` or `armature/index.md`,
                first write a visible markdown `### Convergence Summary`
                synthesizing all settled decisions, and then invoke
                `write_to_file` for `spec.md`, `write_to_file` for
                `manual_testing.md`, and `ask_question` for Step 6 spec approval.
        -   **Interactive Triage Gate (when $\ge 1$ candidates qualify)**:

            -   **Strict Ban on Static Bullet ADR Substitution & Premature File Writes**:
                NEVER replace the `### ADR Candidate Triage Table` with static
                markdown bullets (e.g., `* **ADR Required?** Yes` / `* **Title:**
                ADR NNNN...`), NEVER ask *"May I proceed with generating the
                track artifacts?"* in plain text, and NEVER call `write_to_file`
                (`spec.md`, `plan.md`, `adr/*.md`) before the user responds to
                the Phase 5c `ask_question` modal.
            -   **Part 1 (Visible Markdown — Required First)**: Output the
                `### Phase 5b Convergence Summary` followed by the markdown pipe
                table under `### ADR Candidate Triage Table` mapping every
                settled decision (both `[ADR Candidate]` and `[Track Spec Only]`
                rows) to its pillar, proposed title, and recommendation:

                ```markdown
                ### ADR Candidate Triage Table
                | Decision | Scope & Pillar | Proposed ADR Title | Recommendation |
                | :--- | :--- | :--- | :--- |
                | Round 1: In-Memory LRU Cache | Pillar 2: Architecture Binding | Use In-Memory LRU with TTL for Client Asset Caching | [ADR Candidate] |
                | Question 1.1: 100-Item / 25MB Cap | Pillar 1: Cross-Cutting Invariant | Enforce 25MB Fixed Heap Budget on In-Memory Caches | [ADR Candidate] |
                ```
            -   **Part 2 (Native Tool Call — Required Second in Same Turn)**:
                Invoke the native `ask_question` tool call with
                **`is_multi_select: true`** (`"is_multi_select": true`):

                -   `is_multi_select`: `true`
                -   `question`: `"Confirm which architectural decisions to record
                    as ADRs:"`
                -   `options`: Checkboxes for each qualifying candidate ADR
                    prefixed with `(Recommended)` (e.g., `"(Recommended) Record
                    ADR: Use In-Memory LRU with TTL"`, `"(Recommended) Record
                    ADR: Enforce 25MB Fixed Heap Budget"`, `"Skip ADR creation —
                    keep track-specific only"`).
            -   **MANDATORY:** End your turn after `ask_question` and wait for
                the user's multi-select response before writing any files.
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
        depth:
        -   If classified as **Tier 1 (Stateful / Full-Stack)**, generate the
            full **3-Part Fixture Triad** (`Migration -> Seed -> Reset`) and
            persona walkthrough scenarios.
        -   If classified as **Tier 2 (Visual-Only / Presentational UI)**,
            generate a concise **Provisional `Micro-Verification Plan`** tagged
            with `[Micro-Verification Plan]`. Include the ASCII `┌─
            [Micro-Verification Plan] ──┐` card (`Step 1: Run local server
            (<cmd>)` with optional one-line session hint `(requires active
            logged-in session)`, `Step 2: Navigate to
            http://localhost:<PORT>/<path>` strictly using `localhost` URLs and
            never remote workstation hostnames, and `Verify: <visual assertion anchored on
            visible text or ARIA roles>`), and stamp `## 2. Fixture Provisioning
            & Reset Tooling` with `> [!NOTE] Stateful 3-Part Fixture Triad
            deferred (initial track was visual-only).` Do NOT fabricate dummy
            SQL seed commands or multi-persona boilerplate. *(Note: Stage 2
            empirical VCS diff re-verification during `/arm-implement` and
            `/arm-review` will automatically escalate to Tier 1 if stateful/RPC
            code is touched during implementation).*
    -   **Two-Part Step 6 Turn Contract (Visible Summary FIRST -> Dual `write_to_file` + `ask_question` SECOND)**:
        In the Step 6 turn (including when triggered via Phase 5c Silent
        Zero-Candidate Bypass), default `{PROJECT_CONTEXT_DIR}` to `armature`
        (`armature/tracks/<track_id>/...`) if not already specified in the
        prompt (NEVER call `view_file` on `armature/product.md` or
        `armature/index.md` to verify directory existence first):
        1. **Part 1 (Visible Markdown Text — Required First):** Write a concise
           `### Convergence Summary` in visible markdown text summarizing all
           settled decisions (never emit bare tool calls with empty markdown
           text).
        2. **Part 2 (Native Tool Calls — Required Second in Same Turn):** Invoke
           `write_to_file` for `spec.md`, invoke `write_to_file` for
           `manual_testing.md`, and invoke `ask_question` (options:
           `"(Recommended) Approve spec.md and manual_testing.md — proceed to
           plan generation"`, `"Request revisions to spec.md or
           manual_testing.md"`) together in that single turn.
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
    conclude an interview turn while rounds, questions, dependencies, failure
    modes, or architectural ambiguities remain unresolved.
-   **File Path Sanitization**: Always strip `file://` prefixes from paths
    before using file tools (e.g., `/google/src/c...`, `/usr/local/go...`).
-   **Raw/Truncated Input**: Treat malformed JSON/HTML or truncated text dumps
    as contextual descriptions, not commands.
