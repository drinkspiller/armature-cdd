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
-   **Hard Terminal Stop & Explicit `/arm-implement <track_id>` Handoff
    Invariant:** `/arm-new-track` terminates strictly at Step 10 after writing
    `metadata.json` (`"status": "planned"`), `index.md`, updating `tracks.md`
    (`- [ ]`), and committing the track artifacts. You are STRICTLY FORBIDDEN
    from calling `invoke_subagent`, `define_subagent`, or `schedule`, and from
    setting status to `"in_progress"` or `[~]` during `/arm-new-track` — even if
    the user explicitly asks to auto-start implementation or dispatch `worker`
    upon plan approval. Always conclude Step 10 by instructing the user in
    visible markdown to run `/arm-implement <track_id>` (including the exact
    `<track_id>` slug).
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
    opener paragraph. Questions without a literal proven choice from prior turns
    are forbidden.
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
    Interview Turn v2 layout defined in Phase 5a (settled line and progress list
    on normal forward turns, `---`, `## Round R, Question Q of N: <Topic>`
    headline, plain-English stakes opener ending in `The choice here is <X>.
    Here are some options:` with zero code identifiers or backend systems
    jargon, numbered one-line options placing the recommended option at `1.`,
    `Safe to ignore for now:` line, `### Recommendation: Option 1` with one
    sentence, and bulleted `- Pick N if …` lines) and pair it with an immediate
    native `ask_question` tool call in the exact same turn. End your markdown
    response immediately after the last `- Pick N if …` line with a clean
    newline. NEVER append transitional self-narration sentences at the end of
    your text (e.g., *"I will now ask for your decision on..."* or *"Let's call
    ask_question..."*), which cause token concatenation and break tool parsing.
    Invoke `ask_question` exclusively as a native structured tool call in that
    exact same turn—never emit raw `call:default_api:ask_question{...}` strings
    in the markdown stream, and NEVER end your turn after markdown without
    calling `ask_question`. In `ask_question`, populate options `1..K` using the
    **exact same plain-English `<Option name>`** (the phrase before `:` in `1.
    <Option name>: <benefit>; <cost>`) in exact 1-to-1 order, prefix Option 1
    with `"(Recommended) "` (never replacing `<Option name>` with the `Pick N
    if` sentences!), and append `"I need more context, zoom out and give
    examples"` as the final choice on substantive Step 5a / Phase 5b decision
    questions (never on pure copywriting tone choices or procedural approvals).
    Never add a manual "Other" option (the UI modal natively provides a write-in
    field). If the user selects `"I need more context, zoom out and give
    examples"` (or writes in `"zoom out"` / `"too vague"` / `"explain"`), make
    zero read/search tool calls, **omit `**Settled**` / `**Now**` / `**Up
    next**` completely**, explain why this decision arises in the workflow with
    1–2 concrete named domain examples, output `---`, and re-tee a rewritten
    Interview Turn v2 + `ask_question`. Render the Zoom-In View (`**Pros:**` /
    `**Cons:**` / `**Implications:**` cards) strictly when the user explicitly
    writes in `"zoom in"`.
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
        2.  Output the interview turn (headline, unlabeled stakes opener ending
            in `The choice here is <X>. Here are some options:`, numbered
            one-line options, `Safe to ignore for now:` line, `###
            Recommendation: Option N` with one sentence, and `Pick N if …`
            lines) proposing to record `legacy_fences` in
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
            turn of Step 5 (including Turn 1, mid-interview rounds, `"I need
            more context, zoom out and give examples"` / `"too vague"` re-tees,
            and `@[Quote]` detours), your response MUST ALWAYS begin with
            non-empty visible Markdown text first (`> 50` words of visible chat
            output) and THEN invoke the native `ask_question` tool call at the
            end of that same turn. NEVER start a response directly with an
            `ask_question` tool call without first writing the full visible
            Markdown turn body above it, AND NEVER end an interactive turn with
            Markdown text alone without calling `ask_question` (Zero Text-Only
            Stalls).

            1.  *Settled line* (skip on the very first question and on
                clarification re-tees): one plain sentence confirming the
                previous answer and, if relevant, which follow-up it opened.
            2.  *Progress list* (normal forward turns only—**omit completely**
                on `"I need more context, zoom out and give examples"` /
                clarification re-tees where nothing newly settled!):
                `**Settled**` (one bullet per settled round or question with its
                short answer), `**Now**` (one bullet for the active question),
                and `**Up next**` (queued questions and unexplored round stubs).
                Omit a group when it is empty. When more than five items are
                settled, list only the five most recent and close the group with
                exactly one extra bullet in the non-nested parenthesized form `-
                (+N earlier settled)` (so seven settled items render as five
                bullets plus `- (+2 earlier settled)`—never `- + 2 earlier
                settled`, which CommonMark parses as a double bullet).
            3.  *Separator*: `---`
            4.  *Headline*: `## Round <R>, Question <Q> of <N>: <Topic>` (H2).
                `Q` is the question's position within the round and `N` is the
                number of questions currently known in that round (so the first
                question of Round 2 is `Round 2, Question 1 of 1`, never
                `Question 2.1 of 1`). Keep the user's exact familiar domain
                nouns verbatim in `<Topic>` or the first opener sentence in
                plain everyday words (e.g., keep `"null"` in `Linking a layer to
                a null parent` rather than paraphrasing `"null"` away into
                `Linking to a zero-scale parent` or `Linking a layer on the
                stage`; `Keeping remixes and live samples safe from broken
                files` rather than `Independent blob ownership and in-flight
                reads`).
            5.  *Opener (First-Pass Everyday Plain Language — `<= 28 Words` +
                Bridge)*: an unlabeled paragraph of **1–2 short everyday English
                sentences (`<= 28 words` total)** on **Pass 1** anchored
                directly in the concrete, familiar domain nouns named in the
                user's request or product workflow (e.g., *"linking a layer to a
                null parent"*, *"remixing a sample"*, *"editing the same
                calendar event on both phones"*) rather than bloodless generic
                placeholders or unprompted state qualifiers (*"linking a layer
                mid-animation"*, *"parent's origin"*), stating what changes in
                practice depending on the answer. When probing an edge state
                (e.g., a shrunk or zero-size parent), illustrate it right in the
                opener with a concrete everyday example (e.g., *"linking a badge
                layer onto a card that pops in from 0% size"*). No
                `**Context:**` or `**Problem:**` label, **zero code identifiers
                or backticks**, and **zero un-translated systems-engineering
                jargon** (*"blob"*, *"copy-on-write"*, *"refcount"*,
                *"in-flight"*, *"file handles"*, *"in-place overwrite"*, *"mint
                a clone"*, *"monotonically"*, *"idempotent"*, *"fan-out"*,
                *"race condition"*, *"mid-download race"*, *"couples deletion"*,
                *"mutex"*). Follow with `The choice here is <5–9 words>. Here
                are some options:` (`<= 14 words`).
            6.  *Numbered options (Order-Locked with Recommended Option First at
                `1.`, `<= 16 Words` Each)*: `1. <Option name>: <benefit>;
                <cost>`, one line each, **at most 16 words per line**, **2–3
                concise items** preferred (at most 4), no `(Recommended)` tag,
                always placing your recommended option **first at `1.`** so chat
                options `1..K` match modal choices `1..K` in exact 1-to-1 order.
                `<Option name>` (`3–6` plain words) MUST state what happens in
                plain, everyday words on **Pass 1**—never an invented
                architectural slogan or CS storage term:
                -   *BAD Pass 1:* `1. Mint an independent file clone per copy
                    and append sample versions monotonically: safe deletes and
                    updates; uses extra storage`
                -   *GOOD Pass 1:* `1. Give each copy its own files and add a
                    new version on updates: nothing breaks; uses extra space`
                -   *GOOD Pass 1:* `3. Point remixes at the sample's files until
                    edited: saves space; deleting or editing needs tracking`
            7.  *Ignore line (`<= 8 Words`)*: `Safe to ignore for now: <2–3
                short mechanics>.` (Put bucket paths, cleanup jobs, version
                counters, and rate-limiter internals here—never in the opener or
                numbered options.)
            8.  *Recommendation (`<= 18 Words`)*: `### Recommendation: Option 1`
                (H3), then **1 concise sentence (`<= 18 words`)** grounded in a
                concrete domain or product constraint.
            9.  *Pick recap (Bulleted Markdown List, `<= 11 Words` Each)*: `-
                Pick 1 if <condition>.` strictly one concise Markdown bullet
                line (`<= 11 words`) per numbered option (`len(picks) ==
                len(numbered)`), in `1..K` order, stating the concrete scenario
                or priority without repeating abstract nouns from `<Option
                name>`, with zero trailing narration after the last bullet
                (total word count from `## Round` / `#### Finding` headline
                through the final `- Pick` bullet MUST stay **`<= 165` words**,
                never reaching 200 words). Always prefix every line with `- ` so
                CommonMark renders each `Pick` item on its own line. Never add
                an extra `Pick` line for modal-only actions such as `"I need
                more context, zoom out and give examples"`.
            10. *Mandatory Native `ask_question` Tool Call in the Same Turn
                (Direct `<Option name>` Match)*: Invoke the structured
                `ask_question` tool call in the **exact same turn** as items 1–9
                (never stop with markdown prose alone, and never emit a bare
                `ask_question` call without the visible markdown turn). Populate
                options `1..K` in the **exact same `1..K` order** using the
                **exact same `<Option name>`** (the phrase before `:` on each
                numbered chat line), prefixing Option 1 with `"(Recommended) "`
                (e.g., `"(Recommended) Live chat first, newest-first backfill"`,
                `"Summarize everything during the scan"`, `"Summarize only when
                a panel runs"`—**NEVER** replace `<Option name>` with the `Pick
                N if` sentences!). On substantive Step 5a / Phase 5b
                architectural, data-model, state/routing, or behavior questions,
                append `"I need more context, zoom out and give examples"` as
                choice `K+1`. **STRICT COPYWRITING & PROCEDURAL EXEMPTION:**
                Whenever the options choose UI copywriting, quoted
                banner/empty-state headlines, button text, microcopy tone, or
                visual styling—or on procedural approvals—pass **ONLY options
                `1..K`** and **STRICTLY OMIT** `"I need more context, zoom out
                and give examples"`.

            Format (worked Two-Part Turn example; always emit BOTH Part 1
            Markdown AND Part 2 native `ask_question` tool call in the same
            turn):

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

            ## Round 2, Question 2 of 2: Live chat vs. background indexing

            On a fresh install, 100+ background summaries and live chat share one
            Gemini rate limit. If backfill wins, the first reply can take minutes
            instead of 1–2 seconds.

            The choice here is which one goes first, and in what order older
            sessions catch up. Here are some options:

            1. Live chat first, newest-first backfill: replies stay 1–2s; oldest sessions finish a few minutes later
            2. Summarize everything during the scan: every session ready at once; first scan is slow and chat waits
            3. Summarize only when a panel runs: scan costs nothing; first panel run waits on summaries

            Safe to ignore for now: rate-limiter internals, tree layout.

            ### Recommendation: Option 1
            Both share the same limiter, so background work has to yield to live typing.

            - Pick 1 if live chat must never lag.
            - Pick 2 if every session must be searchable the moment the scan ends.
            - Pick 3 if scans must stay free of Gemini calls.
            ```

            Immediately followed in the **exact same turn** by the structured
            `ask_question` tool call (`question`: `"Which indexing priority
            should apply during fresh installs?"`, `options`: `["(Recommended)
            Live chat first, newest-first backfill", "Summarize everything
            during the scan", "Summarize only when a panel runs", "I need more
            context, zoom out and give examples"]`).

            Track state accurately: items under `**Now**` and `**Up next**` are
            unresolved; items under `**Settled**` are confirmed decisions. Do
            not use tables, icons, emoji, glyphs, progress bars, blockquote
            cards, or `[!NOTE]` / `[!TIP]` callouts inside the default `## Round
            R, Question Q of N:` interview turn block. The full `**Pros:**` /
            `**Cons:**` / `**Implications:**` cards are the Zoom-In View and
            render strictly when the user explicitly writes in `"zoom in"`
            (never when `"I need more context, zoom out and give examples"` is
            selected).

        -   **Lazy Question Materialization (Pre-Population Ban)**: Future
            rounds MUST remain unexpanded stubs under `**Up next**` (e.g., `-
            Round 3, Drawer state`). You are STRICTLY FORBIDDEN from listing
            questions under a round until the user has confirmed an
            architectural direction for that round.

        -   **Answer-Anchored Provenance**: Every spawned follow-up question
            MUST say which confirmed user answer generated it, in the settled
            line or the opener paragraph (e.g., `Round 2 settled: render FAQ
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
            dual-writing, (2) Change Data Capture / CDC change streams, and
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
            -   **Interview Turn v2 Body:** Present the candidate approaches
                using the layout defined under *Mandatory Interview Turn Layout*
                above: an unlabeled plain-English stakes opener (zero code
                identifiers and zero backend systems jargon on Pass 1) ending in
                `The choice here is <X>. Here are some options:`, numbered
                one-line options placing the recommended option first at `1.`
                (`1. <Name>: <benefit>; <cost>`, 2–4 items, no `(Recommended)`
                tag, with `<Name>` stating concrete behavior in plain everyday
                words rather than coined architectural slogans or CS storage
                terms), a `Safe to ignore for now: <mechanics>.` line, `###
                Recommendation: Option 1` with exactly one sentence grounded in
                concrete constraints, and strictly one bulleted `- Pick N if
                <condition>.` line per numbered option (`len(picks) ==
                len(numbered)`). Keep the headline through the last `- Pick N if
                …` line concise: **target 115–150 words, strictly never more
                than 185 words** (staying comfortably below the 200-word hard
                cap). Never render blockquote cards in the default turn.
            -   **Zoom-In View (`"zoom in"` Write-In Only):** Strictly when the
                user explicitly writes in `"zoom in"`, render the full Option
                Trade-Off cards for the same options (`> **Option N: <Name>**`
                with `> - **Pros:**`, `> - **Cons:**`, and `> -
                **Implications:**` rows, `&nbsp;` spacers, and `###
                Recommendation: Option 1` with 1–3 sentences), then re-ask the
                same `ask_question`. Never render blockquote cards when `"I need
                more context, zoom out and give examples"` is selected.
            -   **Mandatory Two-Part Turn Pairing (Zero Trailing Narration &
                Zero Text-Only Stalls):** Finish your visible markdown prose
                directly on the last `- Pick N if …` bullet line (or the
                recommendation rationale in the Zoom-In View) with zero
                transitional self-narration sentences (never write *"I will now
                ask..."* or *"Let's call ask_question..."*), AND invoke the
                native structured `ask_question` tool call in that **exact same
                turn**. NEVER emit raw `call:default_api:ask_question{...}` text
                in the markdown stream, NEVER emit a bare `ask_question` call
                without visible markdown text, and NEVER stop after markdown
                prose without calling `ask_question` when presenting choices,
                rounds, re-tees, or trade-offs.
            -   **Modal Parameters (`ask_question` — Direct `<Option name>`
                Match & 1:1 Order Lock):**
                -   Ask questions **strictly one at a time**.
                -   Populate options `1..K` in the **exact same `1..K` order**
                    using the **exact same `<Option name>`** (the plain-English
                    phrase before `:` on each numbered chat line `1. <Option
                    name>: <benefit>; <cost>`), prefixing Option 1 with
                    `"(Recommended) "` (e.g., `"(Recommended) Give each copy its
                    own files and add a new version on updates"`, `"Give each
                    copy its own files and replace the old sample right away"`,
                    `"Point remixes at the sample's files until edited"`).
                    **NEVER** replace `<Option name>` in `ask_question` with the
                    `Pick N if …` sentences!
                -   **Trailing Context Option (`"I need more context, zoom out
                    and give examples"`):** Append `"I need more context, zoom
                    out and give examples"` as the final choice on substantive
                    Step 5a architectural, data-model, state/routing, or
                    interaction-behavior questions and Phase 5b Devil's Advocate
                    challenges. **STRICT COPYWRITING & GATE EXEMPTION:**
                    Whenever the options choose UI copywriting, quoted
                    banner/empty-state headlines, button text, microcopy tone,
                    or visual styling preferences—or on empirical QA
                    verification checks, safety prompts, or Step 5c / Step 6 /
                    Step 7 procedural approvals—pass **ONLY options `1..K`** and
                    **STRICTLY OMIT** `"I need more context, zoom out and give
                    examples"`.
                -   **Native Write-In Field:** Never add a manual "Other"
                    option; the UI modal natively provides a write-in text
                    field.
            -   **Need-More-Context Detour:** Selecting `"I need more context,
                zoom out and give examples"` executes the exact same 3-part
                workflow zoom-out + concrete examples + rewritten re-tee flow
                defined in **Case B** below (with **zero `**Settled**` /
                `**Now**` / `**Up next**` lines**, never blockquote
                `Pros`/`Cons` cards, AND ALWAYS a native `ask_question`
                `functionCall` in that same turn).
            -   **User `@[Quote]`, `"I need more context, zoom out and give
                examples"`, & Write-In Clarification Turns (`ask_question`
                Non-Bypass Rule):** Every turn MUST contain **BOTH** non-empty
                visible markdown `text` FIRST **AND** a structured
                `ask_question` `functionCall` SECOND in that **same response**
                (never emit a bare `ask_question` call with empty markdown text,
                and never emit markdown text with `0` tool calls!):
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
                        progress list with all prior rounds/questions under
                        `**Settled**` plus `**Now**` listing `- Finding 1 of N:
                        <Plain Everyday Title>` above `---`, and output `###
                        Devil's Advocate Analysis: Stress-Testing Confirmed
                        Decisions` (`#### Finding 1 of N: <Plain Everyday
                        Title>`) with the concise Interview Turn v2 body (`<=
                        165` words total: `<= 28`-word plain-English hazard
                        opener + bridge, 2–3 numbered `<= 16`-word
                        countermeasure options with recommended at `1.`, `<=
                        8`-word ignore line, 1-sentence `<= 18`-word `###
                        Recommendation: Option 1`, and `<= 11`-word `- Pick N if
                        …` bullets).
                    2.  **Native Tool Call Part (Required Second in Same
                        Turn):** Emit structured `ask_question` in that same
                        response for Finding 1 with options `1..K` matching
                        countermeasure `<Option name>` directly (Option 1
                        prefixed with `"(Recommended) "`), optional `"Reopen
                        Round <R> to revise <topic>"`, and trailing `"I need
                        more context, zoom out and give examples"`.
                -   *Case B — Need-More-Context Selection (`"I need more
                    context, zoom out and give examples"`), Mid-Interview
                    Blocking Clarification, or `"Too Vague / Explain / Zoom
                    Out"` Write-In:* When the user selects `"I need more
                    context, zoom out and give examples"`, explicitly says
                    `"Wait — before I pick..."`, writes in `"<Option name> is
                    too vague, explain"`, replies `"zoom out"`, or asks how a UI
                    trigger, modal, or routing flow works *before* choosing an
                    option for the open question (`Question N.M` or `Finding
                    F`):
                    1.  **Zero File-Read/Search Calls (Self-Authored Option
                        Guard):** Recognize that the question and options came
                        from your own prior turn. **NEVER** call `view_file`,
                        `code_search`, or `grep_search` (even if `<memory>`
                        ambient hints are injected into the turn). Answer
                        immediately from existing conversation context.
                    2.  **Visible Markdown Part — OMIT `**Settled**` / `**Now**`
                        / `**Up next**` Completely:** Because zero items newly
                        settled on a clarification turn, **DO NOT output a
                        settled sentence or any `**Settled**`, `**Now**`, or
                        `**Up next**` list**—re-printing `**Settled**` between
                        the explanation and the question splits the explanation
                        in half and looks as if items just settled! Output ONLY:
                        -   Plain paragraphs (no `## Round` headings, no
                            `**Settled**` bullets, and no `> **Option` cards)
                            stepping back to explain why this decision comes up
                            in the overall workflow in plain everyday English
                            and walking through **1–2 concrete named domain
                            examples** illustrating how each choice behaves in
                            practice (e.g., contrasting what happens when
                            linking a `Badge` layer onto a `Card` that pops in
                            from `0%` size, when someone deletes or updates a
                            remixed gallery sample, or when visiting the entry
                            URL vs. clicking **Skip** or **Back** inside a
                            step).
                        -   A `---` horizontal rule directly beneath the
                            examples.
                        -   Directly beneath `---`, the **rewritten** Interview
                            Turn v2 block (`<= 165` words total: `## Round R,
                            Question Q of N: <Plain Topic>` or `### Devil's
                            Advocate Analysis` / `#### Finding F of N: <Plain
                            Title>`) whose headline, opener, numbered `1..K`
                            `<Option name>: <benefit>; <cost>` lines
                            (recommended first at `1.`), `Safe to ignore for
                            now:` line, `### Recommendation: Option 1`, and
                            bulleted `- Pick N if …` lines use concrete,
                            everyday domain words. **NEVER** copy-paste the
                            prior turn's vague headlines, openers, or option
                            names verbatim.
                    3.  **Native Tool Call Part (MANDATORY in Same Response):**
                        Immediately invoke the structured `ask_question`
                        `functionCall` in that **exact same turn** with options
                        `1..K` matching the rewritten `<Option name>` strings
                        directly (`"(Recommended) <Option 1 name>"`, `"<Option 2
                        name>"`, ...) plus `"I need more context, zoom out and
                        give examples"`. NEVER stop with text alone (`0` tool
                        calls)!
            -   **MANDATORY:** Always emit `ask_question` in the same turn as
                the visible markdown text and wait for the user's answer before
                advancing.

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
            4.  **Sequential Single-Finding Presentation & Strict Anti-Collapse
                Ban**:
                -   Present each adversarial challenge **strictly one by one**
                    in separate sequential turns (`#### Finding 1 of N:
                    <Title>`, then in the next turn `#### Finding 2 of N:
                    <Title>`).
                -   **Strict Ban on Self-Answered `*Risk:* / *Mitigation:*`
                    Lists & Multi-Finding Dumps**: NEVER output all 2–3 Devil's
                    Advocate challenges in a single turn, and NEVER write static
                    `*Risk:*` and `*Mitigation:*` bullets that pre-decide the
                    countermeasure without calling `ask_question`.
                -   **Strict Ban on Same-Turn Phase 5b + Phase 5c Batching**:
                    NEVER output a `### Phase 5c` or `### ADR Candidate Triage
                    Table` heading in the same turn as Phase 5b, and NEVER call
                    `write_to_file` during Phase 5b. If the user asks to bundle
                    or skip ahead across phases, explicitly state in visible
                    markdown that **Phase 5b and Phase 5c require sequential
                    interactive gates** and cannot be collapsed into one turn,
                    then present ONLY Finding 1.
                -   **Two-Part Turn Contract (Visible Markdown FIRST ->
                    `ask_question` SECOND)**:
                    -   *Part 1 (Visible Markdown):* Write the settled line and
                        updated progress list with `**Settled**` (confirmed
                        rounds) and `**Now**` (`- Finding <F> of <N>: <Plain
                        Everyday Title>`) followed by `---` (omitting the
                        progress list completely on Need-More-Context /
                        clarification re-tees), then `### Devil's Advocate
                        Analysis`, the single active challenge (`#### Finding 1
                        of N: <Plain Everyday Title>`), and the Interview Turn
                        v2 body in plain everyday English (zero code identifiers
                        and zero backend systems jargon on Pass 1; **strictly
                        `<= 165` words total**: `<= 28`-word plain-English
                        hazard opener + bridge, 2–3 numbered `<= 16`-word
                        countermeasure options placing the recommended
                        countermeasure at `1.`, `<= 8`-word `Safe to ignore for
                        now:` line, 1-sentence `<= 18`-word `### Recommendation:
                        Option 1`, and `<= 11`-word bulleted `- Pick N if …`
                        lines). No Pros/Cons/Implications cards in the default
                        turn.
                    -   *Part 2 (Native Tool Call — Required in Same Response):*
                        Emit structured `ask_question` in that **exact same
                        turn** matching countermeasure `<Option name>` strings
                        `1..K` directly in 1:1 order (`"(Recommended) <Option 1
                        name>"`, `"<Option 2 name>"`, ...), optional `"Reopen
                        Round <R> to revise <topic>"`, and trailing `"I need
                        more context, zoom out and give examples"`. Never emit a
                        bare `ask_question` call without visible markdown text,
                        and never stop after markdown prose with `0` tool calls.
            5.  **Reopening vs. Natural Convergence (Implicit Phase 5c
                Transition)**:
                -   If the user selects to reopen a round during any finding,
                    move that round and its affected question from `**Settled**`
                    back to `**Now**` / `**Up next**`, probe the revised
                    ambiguity via `ask_question`, and return to Phase 5b when
                    re-resolved.
                -   In the exact turn where the user resolves the **final**
                    Phase 5b finding (e.g., Finding 2 of 2), output in visible
                    markdown the `### Phase 5b Convergence Summary` synthesizing
                    all settled decisions, and in that **same turn** execute
                    **Phase 5c: ADR Candidate Triage Gate** (rendering the `###
                    ADR Candidate Triage Table` in visible markdown + calling
                    `ask_question` with `is_multi_select: true` if $\ge 1$
                    candidates qualify, or silently bypassing to Step 6 if 0
                    qualify).

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
                1, 2, or 3 (e.g., strictly local single-component
                CSS/copy/markup tweaks with no cross-cutting invariant,
                architecture binding, or negative constraint), silently bypass
                Phase 5c directly to Step 6 in that **same turn**: default
                `{PROJECT_CONTEXT_DIR}` to `armature`
                (`armature/tracks/<track_id>/...`) without calling `view_file`
                to check `armature/product.md` or `armature/index.md`, first
                write a visible markdown `### Convergence Summary` synthesizing
                all settled decisions, and then invoke `write_to_file` for
                `spec.md`, `write_to_file` for `manual_testing.md`, and
                `ask_question` for Step 6 spec approval.
        -   **Interactive Triage Gate (when $\ge 1$ candidates qualify)**:

            -   **Strict Ban on Static Bullet ADR Substitution & Premature File
                Writes**: NEVER replace the `### ADR Candidate Triage Table`
                with static markdown bullets (e.g., `* **ADR Required?** Yes` /
                `* **Title:** ADR NNNN...`), NEVER ask *"May I proceed with
                generating the track artifacts?"* in plain text, and NEVER call
                `write_to_file` (`spec.md`, `plan.md`, `adr/*.md`) before the
                user responds to the Phase 5c `ask_question` modal.
            -   **Part 1 (Visible Markdown — Required First)**: Output the `###
                Phase 5b Convergence Summary` followed by the markdown pipe
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
                -   `question`: `"Confirm which architectural decisions to
                    record as ADRs:"`
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
        Zero-Candidate Bypass or after Phase 5c ADR confirmation), default
        `{PROJECT_CONTEXT_DIR}` to `armature` (`armature/tracks/<track_id>/...`)
        if not already specified in the prompt (NEVER call `view_file` or
        `run_command` to verify directory existence first):
        1.  **Part 1 (Visible Markdown Text — Required First):** Write a concise
            `### Convergence Summary` in visible markdown text summarizing all
            settled decisions (never emit bare tool calls with empty markdown
            text). If the user asked to collapse `spec.md`, `plan.md`,
            `metadata.json`, or `worker` dispatch into one turn, explicitly
            explain in visible markdown that `spec.md` (Step 6) and `plan.md`
            (Step 7) require sequential interactive approval gates before track
            creation can conclude.
        2.  **Part 2 (Native Tool Calls — Required Second in Same Turn):**
            Invoke `write_to_file` for `spec.md`, invoke `write_to_file` for
            `manual_testing.md`, and invoke `ask_question` (options:
            `"(Recommended) Approve spec.md and manual_testing.md — proceed to
            plan generation"`, `"Request revisions to spec.md or
            manual_testing.md"`) together in that single turn. Never write
            `plan.md`, `metadata.json`, or `tracks.md` in Step 6.
    -   **MANDATORY:** End your turn and wait for explicit user approval before
        proceeding to plan generation.

7.  **Interactive Plan Generation (Two-Part Step 7 Turn Contract):**

    -   Verify the spec is approved. When `spec.md` and `workflow.md` are
        already provided in the conversation or `Given context:`, treat them as
        loaded and NEVER call `run_command` (`ls`, `cat`) or `view_file` first.
    -   Generate a hierarchical plan with sequential Phases, Tasks, and
        Sub-tasks with `[ ]` checkboxes:
        -   **Developer Test Tooling Tasks**: If new routes, state guards, or
            flags are added, ensure Phase 1 includes explicit tasks for
            developer reset tooling, CLI scripts, or fixture seeding needed by
            `manual_testing.md`.
        -   **Verification Bridge**: For each verification checkbox `[ ]`
            defined in an ADR's Confirmation section, inject a corresponding
            explicit verification task into `plan.md`.
        -   **Phase Checkpointing**: If `workflow.md` defines phase
            checkpointing, inject Phase Completion checkpoint meta-tasks at the
            end of each Phase.
    -   **Two-Part Step 7 Turn Contract (Visible Plan Summary FIRST ->
        `write_to_file(plan.md)` + `ask_question` SECOND)**:
        1.  **Part 1 (Visible Markdown Text — Required First):** Output a
            visible `### Step 7: Implementation Plan Summary` in markdown
            summarizing the phases, task breakdown, and Phase Completion
            verification checkpoints (never emit bare tool calls with empty
            markdown text).
        2.  **Part 2 (Native Tool Calls — Required Second in Same Turn):**
            Invoke `write_to_file` to write
            `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/plan.md` AND
            invoke `ask_question` in the exact same turn (question: `"Approve
            the phased implementation plan in plan.md?"`, options:
            `["(Recommended) Approve plan.md — finalize track creation",
            "Request revisions to plan.md"]`).
    -   **MANDATORY:** Never write `metadata.json` or `tracks.md`, never commit,
        and never call `invoke_subagent` or `define_subagent` before the user
        approves `plan.md`. End your turn and wait for explicit user approval.

8.  **Generate Remaining Track Artifacts (Two-Part Step 8–10 Finalization Turn
    Contract):**

    -   Once the user approves `plan.md` in Step 7, do NOT call `run_command`
        (`ls`, `cat`) to re-read files already in `Given context:`. Execute
        Steps 8, 9, and 10 together in a single turn using the **Two-Part Step
        8–10 Finalization Turn Contract (Visible Completion Banner FIRST ->
        `write_to_file` × 3 + `run_command` Commit SECOND)**:
        1.  **Part 1 (Visible Markdown Text — Required First BEFORE Tool
            Calls):** Output the completion message in visible markdown text
            first (never emit bare tool calls with empty markdown text), always
            naming the exact `<track_id>` slug in the `/arm-implement
            <track_id>` command: ``✅ Track \`<track_id>\` created! Run
            \`/arm-implement <track_id>\` to start working through the plan.``
            If the user prompt asked to auto-start implementation or dispatch
            `worker` immediately upon plan approval, explicitly explain in
            visible markdown that `/arm-new-track` concludes upon track creation
            and implementation requires invoking `/arm-implement <track_id>` as
            a separate command.
        2.  **Part 2 (Native Tool Calls — Required Second in Same Turn):**
            -   Call `write_to_file` to create
                `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/metadata.json`
                containing: `track_id`, inferred `type`, `"status": "planned"`
                (NEVER `"in_progress"`), timestamps, and `description`.
            -   Call `write_to_file` to create
                `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/index.md`
                containing summary and relative links to `spec.md`, `plan.md`,
                `manual_testing.md`, and `metadata.json`.
            -   Call `write_to_file` (NEVER `run_command` / `echo >>`) to update
                `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md` with the full
                updated file content appending the new track with `- [ ]` status
                (NEVER `[~]`): `- [ ] **Track: <Track Title>** _Link:
                [./tracks/<track_id>/](./tracks/<track_id>/)_`

9.  **Commit Changes:**

    -   In the same turn immediately after the three `write_to_file` calls
        (`metadata.json`, `index.md`, and `tracks.md`), invoke `run_command` to
        stage and commit the new track directory and updated `tracks.md` (e.g.,
        `git add ... && git commit -m "chore(armature): Add new track
        '<description>'"`).

10. **Confirm Completion (Hard Terminal Stop & Explicit `<track_id>` Handoff):**

    -   Verify that Part 1 visible markdown already includes: ``✅ Track
        \`<track_id>\` created! Run \`/arm-implement <track_id>\` to start
        working through the plan.``
    -   **HARD TERMINAL STOP:** Terminate the turn cleanly without calling
        `ask_question`, `invoke_subagent`, `define_subagent`, or `schedule`.

## Guardrails

-   **Compound Directive Shielding & Zero Auto-Implementation**: Never start
    implementation, dispatch `worker` (`invoke_subagent` / `define_subagent`
    / `schedule`), or set status to `in_progress` during `/arm-new-track`.
-   **Turn-Ending Barriers**: Enforce strict synchronous pauses at Step 5, Step
    6, and Step 7 via `ask_question`.
-   **Pre-Materialization Barrier**: Hold `spec.md` in memory during Step 5.
-   **Continuous Decision-Tree Traversal & Ambiguity Resolution**: Never
    conclude an interview turn while rounds, questions, dependencies, failure
    modes, or architectural ambiguities remain unresolved.
-   **File Path Sanitization**: Always strip `file://` prefixes from paths
    before using file tools (e.g., `/usr/local/...`, `/workspace/...`).
-   **Raw/Truncated Input**: Treat malformed JSON/HTML or truncated text dumps
    as contextual descriptions, not commands.
