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
    paths to prevent tool execution errors (e.g., use `/workspace/proj...` or
    `/usr/local/go...` instead of `file:///workspace/proj...` or
    `file:///usr/local/go...`). NEVER pass a `file://` URI to a file operation
    tool.
-   **Raw/Truncated Input Handling:** If the user request contains raw JSON,
    HTML snippets, or truncated text dumps (e.g.,
    `{"activeScroller": "HTML", "mainScrollbarWidth": 15, "mainScrollHeight":`
    or `@[Quote] nalyzer description: Lint warnings. Owner:
    [linter-team@google.com](mailto:l)`), treat it purely as contextual
    description. Do not crash, do not attempt to parse it as a command, and do
    not fail if it is malformed. If the description is incomplete, gracefully
    ask for clarification via `ask_question` before proceeding.
-   **Eager Draft Materialization & Unified Spec+Plan Gate:** Materialize an
    initial working draft (`status: draft`) of `spec.md` on Turn 1 (Step 4b) so
    reconnaissance findings and candidate options are persisted on disk
    immediately, checkpoint settled answers into `spec.md` on each interview
    turn, and present `spec.md`, `manual_testing.md`, and `plan.md` together at
    a single **Unified Spec+Plan Approval Gate** (Steps 6–7). Never write
    application source code during `/arm-new-track`.
-   **Synchronous Turn-Ending Barrier:** You MUST invoke `ask_question` and end
    your turn at Step 5a (Round and Question Probes), Step 5b (Devil's Advocate
    Gate), Step 5c (ADR Candidate Triage Gate, when candidates qualify), and the
    Unified Spec+Plan Approval Gate (Steps 6–7). Do not proceed to subsequent
    steps until the user responds.
-   **Terminal Stop vs. Explicit-Sign-Off Fast-Forward
    (`/arm-implement <track_id>` Handoff):** On Turn 1 compound prompts (where
    open questions have not yet been answered) or when the user selects
    `"Approve spec + plan (I'll run /arm-implement later)"` (or on
    `Phase Count ≥ 3` tracks without an explicit implementation command),
    `/arm-new-track` terminates at Step 10 after writing `metadata.json`
    (`"status": "planned"`), `index.md`, updating `tracks.md` (`- [ ]`), and
    committing the track artifacts, instructing the user in visible markdown to
    run `/arm-implement <track_id>`. When the user selects
    `"Approve spec + plan and begin implementation"` at the Unified Gate (or
    issues an explicit `"implement"` / `"go ahead"` / `"do it now"` /
    `"build it"` / `"start coding"` sign-off after answering all questions),
    finalize `spec.md` and `plan.md` to `status: approved`, write
    `metadata.json`, `index.md`, and `tracks.md`, and transition directly into
    `/arm-implement <track_id>` in the same turn.
-   **Silent On-Disk State Checkpointing (Zero Chat Progress-List Clutter):**
    Persist settled decisions and remaining open questions strictly on disk in
    `spec.md` (`status: draft`, under `## Settled Decisions` and
    `## Open Questions`) and `armature/active_context.md`. **NEVER** output
    `Round X settled:` lines or `**Settled**`, `**Now**`, or `**Up next**` lists
    in chat so the user can focus exclusively on the active question.
-   **Lazy Question Materialization (Pre-Population Ban):** Keep future rounds
    as unexpanded stubs in `spec.md` `## Open Questions` (e.g.,
    `- Round 2: <Topic>`). Don't list sub-questions under a round until the user
    has confirmed a direction for that round, because the sub-questions depend
    on that answer.
-   **Answer-Anchored Provenance:** Every spawned follow-up question MUST weave
    which confirmed user answer generated it naturally into the opening clause
    of the orientation paragraph (e.g., *"Because new uploads stay private in
    staging until scanning passes, the scanner now sits directly between
    uploading a file and sharing its link..."*). Follow-up questions without a
    clear link to a confirmed prior choice are forbidden.
-   **Anti-Dictation (Don't Decide for the User):** Don't present technical
    designs, UI layouts, button behaviors, or lifecycle rules as decided when
    the user has not confirmed them; raise them as questions instead.
-   **Settled Decisions Are Agreed Intent (`ADR 0022`):** A settled decision, or
    a batch the user labels *"already agreed, treat them as answered"*, records
    what the user wants, not a literal rule to amplify. User-approved concepts
    or drafts bind as a whole (never diff who authored which sentence). Before
    writing a settled decision into `spec.md` (draft or approved), cross-check
    it semantically against existing skill/controller descriptions, prompts,
    docs, and sibling contracts—not just whether symbol names exist. Treat
    universal words (`only`, `never`, `every`, `remove all`) in user shorthand
    as scope flags. If a literal or absolute reading would remove, forbid, or
    override something the user probably didn't intend (e.g., *"Pi 5 only for
    on-device ML"* read as banning all other hardware, or *"remove all sibling
    part names"* also removing names other code depends on), ask one short
    **Interpretation Check** question that states the literal consequence and
    the narrower reading. Record the user's wording in `## Settled Decisions`
    and don't make it stricter than stated.
-   **Follow-Up Question Spawning Invariant & Depth-2 Horizon:** Selecting an
    option for a round does NOT close the round; it actively spawns 1–2
    high-value operational follow-up questions derived from that specific
    answer. Probing depth is strictly bounded to Depth <= 2 (Round -> Question).
    Question answers are terminal (Settled) and MUST NOT spawn further nested
    questions.
-   **Full-Context Question Box Interview Format & Mandatory Tool Pairing (Zero
    Text-Only Stalls):** In EVERY turn of Step 5 where choices are presented,
    write **only one short lead-in sentence in chat** naming the topic (no
    option cards or `- Pick` bullets in chat), run any working-draft updates,
    and invoke `ask_question` natively in that exact same step with the full
    structured Markdown decision inside `questions[0].question` (see
    `rules/armature_antigravity.md`, `rules/armature_protocol.md`,
    `skills/arm-new-track/references/interview_formatting.md`, and
    `skills/arm-new-track/references/ask_question_guide.md`: `## <Topic>`
    headline without `Round R, Question Q` prefixes and with zero fenced `text`
    ASCII flow diagrams, an unlabeled 2–3 sentence plain-English overview ending
    in `The choice here is <X>.` with zero prose code identifiers or backend
    systems jargon, `Options` eyebrow (`<div>` in Antigravity GUI HTML or
    `#### OPTIONS` in Pure CommonMark), 2–4 container-free flush-left numbered
    options placing the recommended option at `1.` with a `Recommended`
    badge/tag, an indented one-sentence plain-English summary per option folding
    operational impact and Option 1's rationale, and indented bold `Pros:` /
    `Cons:`—omitting `Implications:`, redundant bottom `Recommendation:` blocks,
    and `Safe to ignore for now:` footers, targeting `160-250` visible words and
    staying `<= 300` words by default with **zero `**Settled**` / `**Now**` /
    `**Up next**` lists**). NEVER emit raw `call:default_api:ask_question{...}`
    strings in the markdown stream, and don't end your turn after markdown
    without calling `ask_question` unless Plain-Text Question Mode applies. In
    `ask_question`, populate `options` `1..K` using the **exact same
    plain-English `<Option name>`** titles from `question` in exact 1-to-1
    order, prefix Option 1 with `"(Recommended) "`, and append
    `"I need more context, zoom out and give examples"` as the final choice on
    substantive Step 5a / Phase 5b decision questions (never on pure copywriting
    tone choices or procedural approvals). Never add a manual "Other" option
    (the UI modal natively provides a write-in field). If the user selects
    `"I need more context, zoom out and give examples"` (or writes in
    `"zoom out"` / `"too vague"` / `"explain"`), make zero read/search tool
    calls, write a one-line chat lead-in, and inside `ask_question`'s `question`
    field walk through 1–2 concrete named domain examples in plain everyday
    English above the divider (`<div class="border-t border-border my-2"></div>`
    in GUI HTML or `---` in Pure Markdown—never option lists above the divider)
    and re-tee the rewritten decision below it. If the user asks a purely
    informational follow-up question (no open decision), answer directly in chat
    starting with an `# <Topic>` H1 heading and do not call `ask_question`; if a
    decision remains open, put `## <Follow-Up Topic>`, the answer, the divider,
    and the re-teed decision inside `ask_question`'s `question` field with a
    one-line chat lead-in. When Plain-Text Question Mode applies
    (`rules/armature_antigravity.md`: the user asked for chat questions,
    `ask_question` is unavailable, or a recovery box also came back blank),
    render `# <Topic>`, overview, `#### OPTIONS`, the Pure CommonMark nested
    ordered list options, and `- Pick N if …` lines directly in chat and end the
    turn without calling `ask_question`; that is not a text-only stall.
-   **Compound Directive Shielding:** If the user invokes `/arm-new-track`
    alongside other instructions (e.g., `/diagnose`, `Fix`, or implementation
    tasks) on Turn 1 before a specification and plan have been drafted, refuse
    to write application source code on Turn 1. Complete Step 4 reconnaissance,
    materialize the working draft `spec.md` (`status: draft`) in Step 4b, and
    pose the high-leverage architectural ambiguity via `ask_question`.
-   **Premature Draft Command Shielding & Explicit-Sign-Off Fast-Forward:** If
    critical architectural ambiguities remain unsettled in `spec.md`
    `## Open Questions` and the user has NOT selected a concrete option or
    authorized recommended defaults, briefly note that open architectural
    questions remain and pose the next targeted probe via `ask_question`.
    However, if a working draft `spec.md` (`status: draft`) already exists on
    disk from Step 4b and the user replies with a concrete option selection plus
    an explicit sign-off directive (e.g., *"Use Option 1, approve the spec and
    plan, and proceed"* or *"Approve defaults and finalize the track"*), record
    the selected option and recommended defaults for any remaining routine
    questions, promote `spec.md`, `plan.md`, and `manual_testing.md` to
    `status: approved`, and proceed to Step 7/8 without forcing redundant modal
    rounds.
-   **Phase 5b Devil's Advocate Analysis:** When all rounds and dynamically
    spawned questions are Settled, you MUST NOT immediately converge. You MUST
    execute Phase 5b: audit the combination of confirmed answers, emit a
    structured `# Devil's Advocate: <Topic>` (and `### Finding 1 of N: <Title>`)
    confronting the user with emergent contradictions, operational hazards, and
    maintainability debt, and halt with `ask_question` to reaffirm or reopen
    rounds.
-   **Phase 5c ADR Candidate Triage Gate (Dual-Stage Lifecycle):** Immediately
    following Phase 5b, audit all settled decisions against the 3-Pillar
    Invariant Taxonomy (Cross-Cutting Invariant, Architecture Binding, Negative
    Constraint). If zero decisions qualify, silently bypass directly to Step 6.
    If candidates qualify, render an `### ADR Candidate Triage Table` and obtain
    explicit user confirmation via a multi-select modal in a single turn before
    drafting ADRs.
-   **Anti-Early-Exit & Natural Convergence:** The interview concludes when all
    rounds and questions are Settled, Phase 5b Devil's Advocate analysis is
    resolved, and Phase 5c ADR triage has concluded (or via the Step 5d
    Complexity Classifier & Explicit-Sign-Off Fast-Forward when the user
    explicitly signs off on a Step 4b working draft).
-   **Eager Working Draft & Post-Convergence Promotion Barrier:** Materialize
    `spec.md` on Turn 1 (Step 4b) with YAML frontmatter `status: draft` and
    update it in-place as rounds settle. Promote `spec.md`, `plan.md`, and
    `manual_testing.md` from `status: draft` to `status: approved` in Step 7
    only after the user approves the Unified Spec+Plan Gate (or gives explicit
    sign-off).
-   **Audience Pivot & Execution-Ready Spec/Plan Grounding Standard (`ADR 0016`
    — Sufficient Detail for a Smaller Model Without Writing Code):** While Step
    5 (the human decision interview) strictly uses everyday plain language with
    zero code identifiers so the human engineer can focus on product and
    architectural trade-offs, **Step 6 (`spec.md`) and Step 7 (`plan.md`) pivot
    audience**: their primary consumer is a downstream execution agent
    (potentially a smaller or lesser model running with zero prior conversation
    history in an isolated worktree or `worker` subagent). **By
    default**—without waiting for the user to ask *"Is there sufficient detail
    for a lesser model?"*—every `spec.md` and `plan.md` MUST translate settled
    plain-English decisions into verified codebase symbols, exact 1-line
    method/RPC signatures with parameter types and argument arity, explicit
    prerequisite tasks to expose private methods/getters/setters, bidirectional
    UI/client `<->` wire/backend field mappings and defaults, server-side
    validation preconditions, reload/hydration echo-suppression guards,
    self-contained state machines/timers for any referenced sibling pattern, and
    unit-test bundle/fixture overrides. **Strict "Blueprint, Not Implementation
    Code" Boundary:** Express all contracts via inline backtick signatures,
    bulleted field bijections, and declarative state-transition rules—**NEVER**
    embed multi-line fenced implementation code blocks (`.ts`, `.py`, `.go`,
    `.rs`, `.kt`, `.java`) or function bodies inside `spec.md` or `plan.md`, and
    **NEVER** modify application source files during `/arm-new-track`.
    **Precision applies to verified facts, not amplified shorthand:** the
    grounding standard covers facts checked against the codebase (paths,
    symbols, signatures, validators, tests). Carry settled decisions into
    `spec.md` as the user's agreed intent; don't turn brief answers into
    absolute rules, and run an Interpretation Check when a literal reading would
    have surprising consequences.
-   **Interruption & Detour Recovery:** If the user asks side questions,
    clarifies requirements, or explores asset tangents mid-traversal, answer the
    inquiry briefly and resume probing the remaining `## Open Questions` from
    `spec.md` using the Focus + Succinct `/zoom-out` turn layout. NEVER leap to
    Plan Generation or VCS Commit.

## Protocol

1.  **Context Resolution & Setup Check:**

    -   Resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (armature or
        conductor) per `armature_protocol.md` §7. **CRITICAL:** Strip any
        `file://` prefix from `{PROJECT_ROOT}` before using it in any file
        operations (e.g., `/workspace/proj...` or `/usr/local/go...`).
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
    -   **UI Footprint & Design Contract Check (`ADR 0021`):** Detect whether
        target files or requirements touch user-facing UI (`.html`, `.css`,
        `.scss`, `.tsx`, `.jsx`, `.vue`, client views, or routes). On non-UI
        tracks (backend, CLI, infra, pure refactors), skip UI Flow Specs and
        visual gating completely. On UI tracks:
        -   Pull `audience` / target personas directly from `product.md` (do NOT
            re-ask who the user is unless scoping a narrower sub-persona).
        -   Check whether `{PROJECT_CONTEXT_DIR}/DESIGN.md` exists and is locked
            (treat a template stub containing `<e.g.,` placeholders as unlocked;
            fall back to `product-guidelines.md` UI notes if legacy) and note
            `--redesign` or `--fast` flags for Adaptive 2-Gate / 1-Gate routing.
    -   Read `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/terms.md` (if it exists) to
        ground term usage and prevent symbol/concept drift.
    -   Scan the `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/` directory listing
        (filenames only) to build awareness of existing architectural decisions.
    -   Read ALL existing track specs by scanning
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/` for `*/spec.md` files.
    -   If the user's description references specific code areas, scan those
        files/directories to understand existing patterns, interfaces, and
        constraints.
    -   **Symbol, Signature, Arity, Validator, & Build-Rule Inventory (For Step
        6/7 Grounding)**: From the reconnaissance scan (or directly from
        `[Codebase Reconnaissance Context...]` when provided inline in the
        prompt—never re-running `code_search` or `view_file` on inline context),
        catalog and hold in memory for Step 6 (`spec.md`) and Step 7
        (`plan.md`):
        1.  **Exact Proto / Schema / Interface Symbols & Setter/Getter Names**:
            Verify actual generated message/class names, field names, and
            setter/getter methods (e.g., distinguishing whether a response
            returns `repeated Project projects = 1` vs. a hypothetical wrapper
            type, or whether a request setter is `setSampleProjectId(id)` vs.
            `setSampleId(id)`).
        2.  **Exact Method Signatures, Parameter Arity & Visibility**: Record
            full 1-line signatures including parameter names, types, return
            types, exact argument count (e.g., 2-arg
            `applyHydratedPartVisibility(hiddenPartSlugs: ReadonlySet<string>,
            seeThroughPartSlugs: ReadonlySet<string>): void` vs. 1-arg), and
            whether required state/methods on target classes are currently
            `private` and need explicit public exposure tasks in `plan.md`.
        3.  **Cross-Layer Field Bijections & Server Validator Preconditions**:
            Note every field-by-field mapping between client/UI state and
            wire/storage protos (including default values for non-toggled
            fields, unit conversions, or boolean inversions like
            `inverted <-> flipped`) and any server-side validator preconditions
            (e.g., unit-length normal vector check `|n| = 1.0`, numeric range
            clamping, or required `FieldMask` paths).
        4.  **Non-Obvious Imports, Build Targets, Generated Files & Test
            Overrides**: Note exact import paths and `BUILD` / `package.json` /
            `Cargo.toml` / `go.mod` dependency targets (e.g., well-known proto
            imports and `BUILD` deps), distinguish build-time generated
            artifacts (e.g., `.binarypb` / `.binpb` generated by build rules)
            from checked-in source files, and identify unit-test fixture/bundle
            overrides needed when flipping shared config defaults.
        5.  **Verified Tool References**: For every checker, validator, linter,
            or CLI the plan will tell a worker to run, confirm its exact
            repository path (search the whole repository; never assume it lives
            under the project) and read its usage/docstring to confirm it
            accepts or scans the target files. Run it during planning **only**
            if it is fast (seconds), read-only, and either used outside its home
            package or used as a pass/fail gate. Otherwise, make the first
            `plan.md` task for that phase capture its output **before any
            edits**, and define pass as "no new findings vs. that baseline"
            rather than "fix any findings".
    -   **Proactive Legacy Boundary Discovery (Migration Detection & Immediate
        Turn 1 Probe)**: If `[Codebase Reconnaissance Context...]` is provided
        in the user prompt or if the user's description reveals parallel
        legacy/modern directories (e.g., migrating from `<legacy_dir>/` to
        `<modern_dir>/`), DO NOT call `code_search` or `view_file` to search for
        `product.md` or `tech-stack.md`. Immediately in Turn 1:
        1.  Write a one-line chat lead-in noting the parallel legacy/modern
            directories detected and invoke `ask_question` in that exact same
            step with the full-context editorial decision inside
            `questions[0].question` (`## <Topic>` headline without `Round R,
            Question Q` prefixes, unlabeled plain-English overview ending in
            `The choice here is <X>.`, `Options` eyebrow, 2–3 flush-left
            numbered options with a `Recommended` badge/tag on Option 1,
            indented one-sentence summaries, and indented bold `Pros:` /
            `Cons:`—with zero `Implications:`, zero bottom `Recommendation:`,
            zero `Safe to ignore for now:`, and zero `**Settled**` / `**Now**` /
            `**Up next**` lists) proposing to record `legacy_fences` in
            `armature/tech-stack.md` (`## Legacy & Deprecated Boundaries` for
            repo-wide enforcement) or in track `metadata.json` (`legacy_fences`
            for track-scoped enforcement). Never finalize `spec.md` to
            `status: approved` or write `plan.md` prematurely.
    -   Use findings to inform the spec questions in the next step — questions
        must reference specific codebase context.

4b. **Initialize Working Draft (`Eager Turn-1 Materialization`):**

````
-   **Exception for Inline Reconnaissance & Legacy-Fence Turn-1 Benchmarks**:
    If `[Codebase Reconnaissance Context...]` is provided inline in the
    prompt or if Step 4 triggered **Proactive Legacy Boundary Discovery**
    (where Turn 1 must make zero file tool calls and only call
    `ask_question`), hold the initial draft in memory on Turn 1 and write it
    on the subsequent turn.
-   **Standard Brownfield & Greenfield Sessions (`Visible Markdown FIRST ->
    Draft File Writes SECOND -> ask_question THIRD`)**: Never emit
    `write_to_file` / `write_file` BEFORE the visible Markdown interview
    turn—starting a response with `write_to_file` suppresses subsequent
    visible `text` parts and leaves chat blank (`content: ""`). On Turn 1,
    ALWAYS emit the complete visible `# <Topic>` Focus + Succinct
    `/zoom-out` Markdown body into `content` **FIRST**, then invoke
    `write_to_file` / `write_file` **SECOND** to write an initial working
    draft of `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/spec.md`
    (and invoke `ask_question` **THIRD** in that same turn), stamped
    with YAML frontmatter:
    ```yaml
    ---
    track_id: <track_id>
    status: draft
    updated_at: <YYYY-MM-DDTHH:MM:SSZ>
    ---
    ```
    Populate the working draft with:
    1.  **Reconnaissance Inventory**: Exact target file paths, existing
        function/class/proto/wire signatures, and backward-compatibility or
        caller constraints discovered in Step 4.
    2.  **Candidate Design Options & Trade-Offs**: The candidate approaches
        and trade-offs for the open rounds (`[OPEN — Round 1]`, `[OPEN —
        Round 2]`, etc.) plus recommended defaults.
    3.  **Initial Test & Edge-Case Matrix**: Edge cases (empty/null inputs,
        boundary values, error paths, wire-format invariants) identified
        during reconnaissance.
-   Write `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/metadata.json`
    with `"status": "draft"`, `track_id`, inferred `type`, timestamps, and
    `description`.
-   Also create or update `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/active_context.md`
    (<= 60 lines) recording the active `<track_id>`, `status: draft`,
    target files, and open questions so any session resumption or tool check
    sees the live specification immediately.
-   **Strict Draft Execution Lock**: `status: draft` is a working artifact
    for transparency and continuity, NOT authorization to implement code.
    `/arm-implement` refuses to execute any track whose `spec.md` or
    `plan.md` still has `status: draft`.
````

5.  **Recursive Decision-Tree Grill Engine & Devil's Advocate:**

    Conduct an interactive decision-tree interview with the user (referencing
    `skills/arm-new-track/references/interview_formatting.md` and
    `skills/arm-new-track/references/ask_question_guide.md` for turn layout and
    modal pairing). The interview operates as an active decision tree organized
    into rounds, checkpointing each settled decision into the working draft
    `spec.md` (`status: draft`):

    -   **Phase 5a: Round and Question Traversal & Ambiguity Elicitation**:

        -   **Mandatory Interview Turn Layout & Full-Context Question Box**: In
            EVERY turn of Step 5 (including Turn 1, mid-interview rounds,
            `"I need more context, zoom out and give examples"` / `"too vague"`
            re-tees, and `@[Quote]` detours), write **only one short lead-in
            sentence in chat** (no option cards or `- Pick` lines in chat), run
            any draft `write_file`/`edit_file` updates, and invoke
            `ask_question` in that same step with the full structured Markdown
            turn inside `questions[0].question`. The one exception is Plain-Text
            Question Mode (`rules/armature_antigravity.md`), where the full
            `# <Topic>` Pure CommonMark nested-list layout
            (`rules/armature_protocol.md`) renders directly in chat with no tool
            call.

            1.  *Zero Progress-List Clutter*: **NEVER** output
                `Round X settled:` lines or `**Settled**`, `**Now**`, or
                `**Up next**` lists in chat or in the box. Persist settled
                decisions and remaining open questions strictly on disk in
                `spec.md` (`status: draft`, under `## Settled Decisions` and
                `## Open Questions`) and `armature/active_context.md`.
            2.  *Clean Topic Headline (`## <Topic>` inside `question`)*:
                `## <Topic>` (or `## Devil's Advocate: <Topic>` /
                `## Finding <F> of <N>: <Subtitle>` in Phase 5b). Do **NOT**
                include `Round <R>, Question <Q> of <N>:` bookkeeping prefixes
                in the headline, and NEVER render fenced `text` ASCII flow
                diagram blocks beneath the headline. Keep the user's exact
                familiar domain nouns verbatim in `<Topic>` or the first
                overview sentence in plain everyday words (e.g., keep `"null"`
                in `## Linking a Layer to a Null Parent` rather than
                paraphrasing `"null"` away into `Linking to a Zero-Scale Parent`
                or `Linking a Layer on the Stage`;
                `## Keeping Remixes and Live Samples Safe from Broken Files`
                rather than `Independent Blob Ownership and In-Flight Reads`).
            3.  *Unlabeled Plain-English Overview (`2–3` Sentences + Bridge)*:
                Directly beneath `## <Topic>`, write an unlabeled paragraph of
                **2–3 everyday English sentences (`<= 55 words` total)** on
                **Pass 1** anchored directly in the concrete, familiar domain
                nouns named in the user's request or product workflow (e.g.,
                *"linking a layer to a null parent"*, *"remixing a sample"*,
                *"editing the same calendar event on both phones"*), situating
                what happens right before and right after this moment in the
                flow so the user has the altitude needed to decide. On follow-up
                questions spawned by a prior choice, weave that prior choice
                naturally into the opening clause (e.g., *"Because new uploads
                stay private until scanning passes, the scanner now sits
                directly between uploading a file and sharing its link..."*).
                When probing an edge state (e.g., a shrunk or zero-size parent),
                illustrate it right in the overview with a concrete everyday
                example (e.g., *"linking a badge layer onto a card that pops in
                from 0% size"*). No `**Context:**` or `**Problem:**` label,
                **zero code identifiers or inline backticks**, and **zero
                un-translated systems-engineering jargon** (*"blob"*,
                *"copy-on-write"*, *"refcount"*, *"in-flight"*, *"file
                handles"*, *"in-place overwrite"*, *"mint a clone"*,
                *"monotonically"*, *"idempotent"*, *"fan-out"*, *"race
                condition"*, *"mid-download race"*, *"couples deletion"*,
                *"mutex"*). End with `The choice here is <5–9 words>.`
            4.  *`Options` Eyebrow + Container-Free Numbered Options
                (Order-Locked with Recommended Option First at Option 1)*:
                Render the `Options` eyebrow (`<div class="mt-5 mb-1 ...">Options</div>`
                in Antigravity GUI HTML per `rules/armature_antigravity.md`,
                or `#### OPTIONS` in Pure CommonMark per
                `rules/armature_protocol.md`) followed by **2–4 container-free
                flush-left numbered options** (`1..K`), always placing the
                recommended option first at Option 1 with the `Recommended`
                pill/tag so `question` options `1..K` match `options` `1..K` in
                exact 1-to-1 order. Under each numbered heading (`3–8` plain
                words stating what happens in everyday words on **Pass 1**),
                indent a **one-sentence plain-English summary** explaining what
                that choice does and what happens (folding operational impact—
                and on Option 1, the recommendation rationale—into this
                sentence), followed by indented bold **`Pros:`** (single clause)
                and bold **`Cons:`** (single clause), keeping visible copy
                between `160-250` words (`<= 300` words by default). Permanently
                omit `Implications:` rows, redundant bottom `Recommendation:`
                blocks/rails, and `Safe to ignore for now:` footers. Never use
                enclosing option card containers or `+`/`-` symbols.
            5.  *Mandatory Native `ask_question` Tool Call in the Same Step
                (Direct `<Option name>` Match & Incremental Working-Draft
                Checkpointing)*: Write the one-line chat lead-in, run any
                working-draft `spec.md` (`status: draft`) + `active_context.md`
                updates, and invoke `ask_question` in that **exact same step**
                with the full structured turn inside `questions[0].question`
                (never stop on prose alone unless Plain-Text Question Mode
                applies). Populate `options` `1..K` in the **exact same `1..K`
                order** using the **exact same `<Option name>`** titles from
                `question` (stripping `Recommended`), prefixing Option 1 with
                `"(Recommended) "`. On substantive Step 5a / Phase 5b
                architectural, data-model, state/routing, or behavior questions,
                append `"I need more context, zoom out and give examples"` as
                choice `K+1`. **STRICT COPYWRITING & PROCEDURAL EXEMPTION:**
                Whenever the options choose UI copywriting, quoted
                banner/empty-state headlines, button text, microcopy tone, or
                visual styling—or on procedural approvals—pass **ONLY options
                `1..K`** and **STRICTLY OMIT**
                `"I need more context, zoom out and give examples"`.

            Example (`ask_question` call payload — Pure CommonMark universal
            twin; in Antigravity GUI panels use the exact `15px` HTML
            template from `rules/armature_antigravity.md`):

            ```json
            {
              "questions": [
                {
                  "question": "## Live Chat vs. Background Indexing\n\nFresh installs scan 100+ past sessions in the background, and those summaries share the same model rate limit as live chat. Without a priority rule, backfill bursts stall a user's first reply for minutes. The choice here is which work goes first.\n\n#### OPTIONS\n\n1. **Live chat first, newest-first backfill** *(Recommended)*\n\n   Live chat and background summaries share one rate limit, so background workers pause whenever an interactive reply is active.\n\n   - **Pros:** Live chat replies stay at 1-2s and recent sessions appear first.\n   - **Cons:** Oldest sessions take a few extra minutes to finish indexing.\n\n2. **Summarize everything during the scan**\n\n   Batch summaries use full model quota ahead of live prompts until the initial scan completes.\n\n   - **Pros:** Every past session is searchable as soon as scanning completes.\n   - **Cons:** First scan is slow and stalls active chat typing.\n\n3. **Summarize only when a panel runs**\n\n   Background scans stay free of model calls and summarize unindexed sessions on demand when opened.\n\n   - **Pros:** Background scans finish quickly with zero model quota use.\n   - **Cons:** Opening a panel waits while unindexed sessions summarize on demand.",
                  "options": [
                    "(Recommended) Live chat first, newest-first backfill",
                    "Summarize everything during the scan",
                    "Summarize only when a panel runs",
                    "I need more context, zoom out and give examples"
                  ]
                }
              ]
            }
            ```

            Track state accurately on disk in `spec.md` (`## Settled Decisions`
            and `## Open Questions`) and `armature/active_context.md`—never
            print `**Settled**`, `**Now**`, or `**Up next**` lists in chat or in
            the box. Do not use tables, icons, emoji, glyphs, progress bars, or
            fenced `text` ASCII flow diagrams inside the default decision block.
            Expanded multi-sentence `Pros:` / `Cons:` detail is the Zoom-In View
            and renders inside `question` only when the user explicitly writes
            in `"zoom in"` (never render option lists above the divider when
            `"I need more context, zoom out and give examples"` is selected).

        -   **Lazy Question Materialization (Pre-Population Ban)**: Future
            rounds MUST remain unexpanded stubs in `spec.md` `## Open Questions`
            (e.g., `- Round 3: Drawer state`). You are STRICTLY FORBIDDEN from
            listing sub-questions under a round until the user has confirmed an
            architectural direction for that round.

        -   **Answer-Anchored Provenance**: Every spawned follow-up question
            MUST weave which confirmed user answer generated it into the opening
            clause of the orientation paragraph (e.g., *"Because FAQ bodies
            switch by question type, an unrecognized FAQ entry now needs a safe
            fallback display..."*). Follow-up questions without a clear link to
            a confirmed prior choice are forbidden.

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
                evolution contracts. On UI tracks, interleave **UX Pattern
                Selection** (propose competing interaction patterns such as
                drawer vs. modal vs. inline job in plain English) and **5-State
                UI Stack** probes (`Ideal`, `Empty`, `Loading`, `Partial`,
                `Error`) directly inside Step 5a alongside technical probes
                since UX patterns and technical failure modes co-constrain each
                other. Order UI Flow Specs by **Red Routes**
                (`frequency of use x consequence of failure`) so foundational
                flows constrain later ones.
            -   *Tier 2 (Three-Altitude Visual Deferral — Prune Pixels from Step
                5a)*: Pure pixel/cosmetic details (exact hex colors, pixel
                padding, corner radii), internal helper function naming, and
                minor micro-copy variations (including whether 1–2 extra
                sentences affect pacing/latency, micro-copy phrasing, or minor
                UI polish) MUST NOT intrude into Step 5a behavioral Flow Specs
                (`ALTITUDE_LEAK`) or spawn interactive interview questions.
                Route project-wide visual direction to Step 5.5 (`DESIGN.md`) or
                reuse existing `DESIGN.md` tokens by name and sensible defaults
                in `plan.md`.

        -   **Anti-Dictation (Don't Decide for the User)**: Don't present
            implementation designs, button placements, countdown rules, or
            lifecycle state transitions as decided when the user has not
            confirmed them; pose them as questions. Once confirmed, record them
            as agreed intent (see *Settled Decisions Are Agreed Intent* above)
            rather than expanding them into stricter rules.

        -   **Zero Mid-Interview Subagent Re-Dispatch & Premature Exit
            Pushback**: Once problem exploration has begun or prior interview
            turns (`[Agent]: ... [User]: ...`) exist in the prompt history,
            **NEVER** invoke `invoke_subagent` to restart reconnaissance. If the
            user asks to draft the spec prematurely (e.g., *"Let's draft the
            spec"*) after confirming a round's choice (such as WebSocket +
            heartbeat), do **NOT** finalize `spec.md` to `status: approved` or
            call `invoke_subagent`. Instead, explicitly push back on premature
            drafting, record dependent operational follow-up questions in
            `spec.md` `## Open Questions` conditioned on that choice (e.g.,
            reconnect backoff jitter algorithm, tab backgrounding/suspension
            disconnect handling, state invariants, multi-tab sync, and
            concurrency dependencies), present codebase-grounded adversarial
            challenges (e.g., server restart thundering herd socket storms,
            stale presence ghost states), and pose the next targeted probe via
            `ask_question`.

        -   **Data Migration & Storage Evolution Pattern Contrasting**: When
            probing database migrations or storage synchronization
            architectures, always contrast all three primary patterns in your
            trade-off breakdown before locking the path: (1) Application-level
            dual-writing, (2) Change Data Capture / CDC change streams, and (3)
            Lazy read-repair / background backfill.

        -   **Testing Strategy Classification (Stage 1 Provisional Intent
            Scoping — ADR 0009)**: Evaluate the confirmed specification and
            target file list to classify manual testing depth:

            -   *Interactive / Stateful / Route / API Tracks (Tier 1: Standard
                Stateful 3-Part Fixture Triad)*: Full `manual_testing.md`
                runbook with environment setup, 3-Part Fixture Triad
                (`Migration -> Seed -> Reset`), persona matrices, and dual-URL
                (`localhost` + remote workstation proxy) route test cases.
                Mandatory whenever state machines, reactive stores, router
                navigation guards (`canActivate`), conditional auth/role gates
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

            -   **Report First, Ask Second (Same-Step Visible Text):** The user
                sees only visible chat text and the question box; `thinking` /
                `thought` is never shown. Write the interview turn as visible
                text on the same response step that calls `ask_question`. If
                your reasoning already summarizes the options and
                recommendation, that summary still has to appear as visible
                text. If the user reports missing chat text or skips a blank
                box, follow Blank-Box Recovery
                (`rules/armature_antigravity.md`): explain in visible text and
                ask again with the box.
            -   **Full-Context Question Box Body:** Present the candidate
                approaches inside `ask_question`'s `questions[0].question` field
                (with only a one-line lead-in sentence in chat) using the layout
                defined under *Mandatory Interview Turn Layout* above: a clean
                `## <Topic>` headline (no `Round R, Question Q` prefixes and
                zero fenced `text` ASCII flow diagrams), an unlabeled 2–3
                sentence plain-English overview (zero prose code identifiers and
                zero backend systems jargon on Pass 1) ending in
                `The choice here is <X>.`, the `Options` eyebrow (`<div>` in
                Antigravity GUI HTML or `#### OPTIONS` in Pure Markdown),
                and 2–4 container-free flush-left numbered options placing the
                recommended option first at `1.` with the `Recommended`
                badge/tag, each with an indented one-sentence plain-English
                summary (folding operational impact and Option 1's rationale)
                and indented bold `Pros:` / `Cons:`—omitting `Implications:`,
                bottom `Recommendation:` blocks, and `Safe to ignore for now:`
                footers. Target `160-250` visible words (`<= 300` words by
                default; exceed 300 only when cutting a critical safety caveat
                would mislead the user). Don't render `**Settled**` / `**Now**`
                / `**Up next**` lists or fenced `text` ASCII flow diagrams.
            -   **Zoom-In View (`"zoom in"` Write-In Only):** Strictly when the
                user explicitly writes in `"zoom in"`, expand each option's
                indented summary, `Pros:`, and `Cons:` inside `ask_question`'s
                `question` field with deeper multi-detail failure modes and
                re-ask the same `ask_question`. Never render option lists above
                the divider when
                `"I need more context, zoom out and give examples"` is selected.
            -   **Mandatory Full-Context `ask_question` Delivery (Zero Text-Only
                Stalls):** Write only the one-line chat lead-in and invoke the
                native structured `ask_question` tool call in that **exact same
                step** with the full structured Markdown decision inside
                `questions[0].question`. NEVER emit raw
                `call:default_api:ask_question{...}` text in the markdown
                stream, and don't stop after markdown prose without calling
                `ask_question` when presenting choices, rounds, re-tees, or
                trade-offs, unless Plain-Text Question Mode applies.
            -   **Modal Parameters (`ask_question` — Direct `<Option name>`
                Match & 1:1 Order Lock):**
                -   Ask questions **strictly one at a time**.
                -   Populate options `1..K` in the **exact same `1..K` order**
                    using the **exact same `<Option name>`** titles from
                    `question` (stripping `Recommended`), prefixing Option 1
                    with `"(Recommended) "` (e.g., `"(Recommended) Give each
                    copy its own files and add a new version on updates"`,
                    `"Give each copy its own files and replace the old sample
                    right away"`, `"Point remixes at the sample's files until
                    edited"`). **NEVER** replace `<Option name>` in `ask_question` with the
                    `Pick N if …` sentences!
                -   **Trailing Context Option
                    (`"I need more context, zoom out and give examples"`):**
                    Append `"I need more context, zoom out and give examples"`
                    as the final choice on substantive Step 5a architectural,
                    data-model, state/routing, or interaction-behavior questions
                    and Phase 5b Devil's Advocate challenges. **STRICT
                    COPYWRITING & GATE EXEMPTION:** Whenever the options choose
                    UI copywriting, quoted banner/empty-state headlines, button
                    text, microcopy tone, or visual styling preferences—or on
                    empirical QA verification checks, safety prompts, or Step 5c
                    / Step 6 / Step 7 procedural approvals—pass **ONLY options
                    `1..K`** and **STRICTLY OMIT**
                    `"I need more context, zoom out and give examples"`.
                -   **Native Write-In Field:** Never add a manual "Other"
                    option; the UI modal natively provides a write-in text
                    field.
            -   **Need-More-Context Detour:** Selecting
                `"I need more context, zoom out and give examples"` executes the
                exact same 3-part workflow zoom-out + concrete examples +
                rewritten re-tee flow defined in **Case B** below (with **zero
                `**Settled**` / `**Now**` / `**Up next**` lines**, no option
                lists above the divider, AND a native `ask_question` call in
                that same step).
            -   **User `@[Quote]`,
                `"I need more context, zoom out and give examples"`, & Write-In
                Clarification Turns (`ask_question` Non-Bypass Rule):** Write a
                one-line lead-in in chat and put the full answer + decision
                inside `ask_question`'s `question` field on that same step (do
                not stop with chat text alone unless Plain-Text Question Mode
                applies):
                -   *Case A — Final-Question Resolution or Leading Confirmation
                    Question:* When only ONE open question remains in `spec.md`
                    `## Open Questions` and the user replies by selecting an
                    option, stating a policy/threshold, OR asking a leading
                    confirmation question verifying the final question's
                    behavior (e.g., `@[Quote] Route disabled. does the guard
                    redirect back to /setup/sharing-permissions?` alongside
                    commit/spec notes like
                    `capture this in the commit description`), treat that final
                    question as **Settled** on disk:
                    1.  Write a one-line chat lead-in naming Finding 1, update
                        `spec.md` / `active_context.md`, and invoke
                        `ask_question` in that same step.
                    2.  Inside `questions[0].question`, answer the confirmation
                        question and commit-description commitment in 1–2 plain
                        sentences above the divider
                        (`<div class="border-t border-border my-2"></div>` in
                        GUI panels or `---` in Pure Markdown), then present
                        `## Devil's Advocate: Finding 1 of N — <Plain Title>`
                        with the full-context options (`Options` eyebrow,
                        numbered options with `Recommended` on Option 1,
                        indented one-sentence summaries, bold `Pros:` / `Cons:`;
                        no `Implications:`, no bottom `Recommendation:`, no
                        `Safe to ignore for now:`). Populate `options` `1..K`
                        1:1 (including `"Reopen Round <R> to revise <topic>"`
                        inside `question` too if warranted) plus trailing
                        `"I need more context, zoom out and give examples"`.
                -   *Case B — Need-More-Context Selection
                    (`"I need more context, zoom out and give examples"`),
                    Mid-Interview Blocking Clarification, or
                    `"Too Vague / Explain / Zoom Out"` Write-In:* When the user
                    selects `"I need more context, zoom out and give examples"`,
                    explicitly says `"Wait — before I pick..."`, writes in
                    `"<Option name> is too vague, explain"`, replies
                    `"zoom out"`, or asks how a UI trigger, modal, or routing
                    flow works *before* choosing an option for the open question
                    or `Finding F`:
                    1.  **Zero File-Read/Search Calls (Self-Authored Option
                        Guard):** Recognize that the question and options came
                        from your own prior turn. **NEVER** call `view_file`,
                        `code_search`, or `grep_search` (even if `<memory>`
                        ambient hints are injected into the turn). Answer
                        immediately from existing conversation context.
                    2.  **One-Line Lead-In + Full Context Inside `question`
                        (Deeper Examples Above Divider, Rewritten Decision
                        Below):** Never output `Round X settled:` or
                        `**Settled**` / `**Now**` / `**Up next**` lists. Write a
                        one-line chat lead-in, and inside
                        `questions[0].question`:
                        -   Begin with `## <Topic>` describing the topic being
                            followed up on, then plain paragraphs (no option
                            lists above the divider) stepping back to explain
                            why this decision comes up in the workflow in plain
                            everyday English and walking through **1–2 concrete
                            named domain examples** illustrating how each choice
                            behaves in practice.
                        -   A crisp divider directly beneath the examples
                            (`<div class="border-t border-border my-2"></div>`
                            in GUI panels; `---` in Pure Markdown).
                        -   Directly beneath the divider, the **rewritten**
                            `## <Plain Topic>` decision (overview, `Options`
                            eyebrow, flush-left numbered options with
                            `Recommended` on Option 1, indented one-sentence
                            summaries, and bold `Pros:` / `Cons:`) in concrete
                            everyday domain words. **NEVER** copy-paste the
                            prior turn's vague headlines, overviews, or option
                            names verbatim.
                    3.  **Matching Modal Options:** Populate `options` `1..K`
                        matching the rewritten `<Option name>` strings directly
                        (`"(Recommended) <Option 1 name>"`, `"<Option 2 name>"`,
                        ...) plus
                        `"I need more context, zoom out and give examples"`.
                        Don't stop with text alone (`0` tool calls) unless
                        Plain-Text Question Mode applies.
            -   **MANDATORY:** Always invoke `ask_question` with the full
                context inside `question` and a one-line chat lead-in (or, in
                Plain-Text Question Mode, render `# <Topic>`, plain overview,
                `#### OPTIONS`, the pure CommonMark nested ordered list options,
                and `- Pick N if …` lines in chat without `ask_question`) and
                wait for the user's answer before advancing.

        -   **Inline Glossary Elicitation (`terms.md`)**: If a decision
            introduces domain terminology, offer to record it in
            `{PROJECT_CONTEXT_DIR}/terms.md`.

    -   **Phase 5b: Devil's Advocate Analysis (Red-Teaming Confirmed Answers)**:

        -   **Trigger**: Fires automatically in the exact turn that the final
            open question in `spec.md` `## Open Questions` settles.
        -   **Execution**:
            1.  Audit the combination of confirmed answers across all settled
                decisions recorded in `spec.md` (`## Settled Decisions`).
            2.  Write a one-line chat lead-in naming the Devil's Advocate
                challenge and put `## Devil's Advocate: <Topic>` followed by
                `Finding 1 of N: <Subtitle>` directly at the top of
                `questions[0].question` (never printing `**Settled**` /
                `**Now**` / `**Up next**` lists; in Plain-Text Question Mode,
                render `# Devil's Advocate: <Topic>` in chat without calling
                `ask_question`).
            3.  Identify 2–3 concrete adversarial challenges across the design
                (*Emergent Contradictions*, *Operational & Maintenance Debt*,
                *Failure Cascades*), but present **ONLY Finding 1** in the
                initial Phase 5b turn.
            4.  **Sequential Single-Finding Presentation & Strict Anti-Collapse
                Ban**:
                -   Present each adversarial challenge **strictly one by one**
                    in separate sequential turns (`## Finding 1 of N: <Title>`,
                    then in the next turn `## Finding 2 of N: <Title>`).
                -   **Strict Ban on Self-Answered `*Risk:* / *Mitigation:*`
                    Lists & Multi-Finding Dumps**: NEVER output all 2–3 Devil's
                    Advocate challenges in a single turn, and NEVER write static
                    `*Risk:*` and `*Mitigation:*` bullets that pre-decide the
                    countermeasure without calling `ask_question`.
                -   **Strict Ban on Same-Turn Phase 5b + Phase 5c Batching**:
                    NEVER output a `### Phase 5c` or
                    `### ADR Candidate Triage Table` heading in the same turn as
                    Phase 5b, and NEVER call `write_to_file` during Phase 5b
                    (except updating `spec.md` `status: draft` /
                    `active_context.md`). If the user asks to bundle or skip
                    ahead across phases, explicitly state in the chat lead-in
                    that **Phase 5b and Phase 5c require sequential interactive
                    gates** and cannot be collapsed into one turn, then present
                    ONLY Finding 1.
                -   **Full-Context Question Box Turn Contract (One-Line Chat
                    Lead-In -> Full Content Inside `ask_question`)**:
                    -   *Chat Lead-In:* Output a single plain-English lead-in
                        sentence naming the active Devil's Advocate finding (no
                        option cards or `- Pick` lines in chat unless Plain-Text
                        Question Mode applies).
                    -   *Native `ask_question` Call (Required in Same Step):*
                        Put the full structured challenge inside
                        `questions[0].question`
                        (`## Devil's Advocate: <Plain Everyday Title>` with zero
                        `**Settled**` / `**Now**` / `**Up next**` lists,
                        `Finding 1 of N: <Plain Everyday Subtitle>`,
                        plain-English hazard overview with zero prose code
                        identifiers or backend systems jargon and zero fenced
                        `text` ASCII diagrams on Pass 1, `Options` eyebrow, and
                        2–3 flush-left numbered countermeasure options with
                        `Recommended` on Option 1, indented one-sentence
                        summaries folding in operational impact and Option 1's
                        rationale, and bold `Pros:` / `Cons:`—with zero
                        `Implications:`, zero bottom `Recommendation:`, and zero
                        `Safe to ignore for now:`, targeting `160-250` words of
                        visible copy, `<= 300` words by default). Match
                        `options` `1..K` directly in 1:1 order
                        (`"(Recommended) <Option 1 name>"`, `"<Option 2 name>"`,
                        ...; if reopening a prior decision is warranted, include
                        `"Reopen Round <R> to revise <topic>"` as one of the
                        `1..K` options inside `question` rather than adding an
                        extra `"Reopen..."` option to `options` alone) and
                        trailing
                        `"I need more context, zoom out and give examples"`.
                        Never emit a bare `ask_question` call without full
                        context inside `question`, and do not stop after chat
                        prose with `0` tool calls unless Plain-Text Question
                        Mode applies.
            5.  **Reopening vs. Natural Convergence (Implicit Phase 5c
                Transition)**:
                -   If the user selects to reopen a round during any finding,
                    move that topic back into `spec.md` `## Open Questions` on
                    disk, probe the revised ambiguity via `ask_question`, and
                    return to Phase 5b when re-resolved.
                -   In the exact turn where the user resolves the **final**
                    Phase 5b finding (e.g., Finding 2 of 2), execute **Phase 5c:
                    ADR Candidate Triage Gate** in that **same turn** (write a
                    one-line chat lead-in and put the
                    `### Phase 5b Convergence Summary` and
                    `### ADR Candidate Triage Table` inside `ask_question`'s
                    `question` field with `is_multi_select: true` if $\ge 1$
                    candidates qualify, or silently bypass to Step 5.5 / Phase
                    5d — Complexity Classifier: Unified Spec+Plan Gate when
                    `Phase Count ≤ 2` and not a `2-Gate` UI track, or Sequential
                    Step 6 when `Phase Count ≥ 3` — if 0 qualify, putting
                    `### Convergence Summary` inside that approval gate's
                    `question` field).

    -   **Phase 5c: ADR Candidate Triage Gate (Dual-Stage Lifecycle)**:

        -   **Trigger**: Occurs immediately after Phase 5b concludes and all
            adversarial challenges are resolved, before Step 6 (`spec.md`
            materialization).
        -   **3-Pillar Invariant Taxonomy Audit**: Audit all settled decisions
            recorded in `spec.md` (`## Settled Decisions`) against the three
            qualification pillars:
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
                route slugs, error strings, styling) are classified as
                `[Track Spec Only]`.
        -   **Silent Zero-Candidate Bypass**:
            -   If and only if **zero** settled decisions qualify under Pillars
                1, 2, or 3 (e.g., strictly local single-component
                CSS/copy/markup tweaks with no cross-cutting invariant,
                architecture binding, or negative constraint), silently bypass
                Phase 5c directly to **Step 5.5 / Phase 5d (Complexity
                Classifier)** in that **same turn** (routing to the **Unified
                Spec+Plan Gate (Steps 6–7)** when `Phase Count ≤ 2` and not a
                `2-Gate` UI track without a locked `DESIGN.md`, or **Sequential
                Step 6** when `Phase Count ≥ 3`): default
                `{PROJECT_CONTEXT_DIR}` to `armature`
                (`armature/tracks/<track_id>/...`) without calling `view_file`
                to check `armature/product.md` or `armature/index.md`, write a
                one-line chat lead-in, and invoke `write_to_file` for `spec.md`,
                `write_to_file` for `manual_testing.md` (plus `write_to_file`
                for `plan.md` when routing to the Unified Spec+Plan Gate), and
                `ask_question` with a concise `### Convergence Summary`
                synthesizing all settled decisions and planned phases directly
                inside `questions[0].question`.
        -   **Interactive Triage Gate (when $\ge 1$ candidates qualify)**:

            -   **Strict Ban on Static Bullet ADR Substitution & Premature File
                Writes**: NEVER replace the `### ADR Candidate Triage Table`
                with static markdown bullets (e.g., `* **ADR Required?** Yes` /
                `* **Title:** ADR NNNN...`), NEVER ask *"May I proceed with
                generating the track artifacts?"* in plain text, and NEVER call
                `write_to_file` (`spec.md`, `plan.md`, `adr/*.md`) before the
                user responds to the Phase 5c `ask_question` modal.
            -   **Full-Context Phase 5c Turn Contract (One-Line Chat Lead-In ->
                Full Triage Table Inside `ask_question`)**: Write a one-line
                chat lead-in naming the ADR triage gate, and invoke the native
                `ask_question` tool call wrapped in the required top-level
                `questions` array with **`is_multi_select: true`** putting the
                `### Phase 5b Convergence Summary` and the
                `### ADR Candidate Triage Table` (mapping every settled
                decision—both `[ADR Candidate]` and `[Track Spec Only]` rows—to
                its pillar, proposed title, and recommendation) directly inside
                `questions[0].question` above
                `"Confirm which architectural decisions to record as ADRs:"` (in
                Plain-Text Question Mode, render the summary and table in chat
                without calling `ask_question`):

                ```markdown
                ### ADR Candidate Triage Table
                | Decision | Scope & Pillar | Proposed ADR Title | Recommendation |
                | :--- | :--- | :--- | :--- |
                | Round 1: In-Memory LRU Cache | Pillar 2: Architecture Binding | Use In-Memory LRU with TTL for Client Asset Caching | [ADR Candidate] |
                | Question 1.1: 100-Item / 25MB Cap | Pillar 1: Cross-Cutting Invariant | Enforce 25MB Fixed Heap Budget on In-Memory Caches | [ADR Candidate] |
                ```

                -   `questions[0].is_multi_select`: `true`
                -   `questions[0].options`: Checkboxes for each qualifying
                    candidate ADR prefixed with `(Recommended)` (e.g.,
                    `"(Recommended) Record ADR: Use In-Memory LRU with TTL"`,
                    `"(Recommended) Record ADR: Enforce 25MB Fixed Heap Budget"`,
                    `"Skip ADR creation — keep track-specific only"`).
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

    -   **Step 5.5 (Conditional UI `Lock the Look` & Adaptive 2-Gate / 1-Gate —
        `ADR 0021`):**

        -   *Skip on non-UI tracks* and *skip on Day-2 UI tracks* where a locked
            `{PROJECT_CONTEXT_DIR}/DESIGN.md` already exists (without `<e.g.,`
            stub placeholders and unless `--redesign` is requested), flowing
            directly into Phase 5d / Step 6 as **1-Gate** referencing existing
            `DESIGN.md` token names.
        -   *When UI track has no locked `DESIGN.md` (or `--redesign` is
            passed):*
            -   **Default (`2-Gate` — exempt from Unified Spec+Plan Gate):**
                -   *Gate 1:* Run Step 6 (`spec.md` approval with
                    `## User Flows` + `## Edge Cases`, plus `manual_testing.md`)
                    first so behavior and all 5 UI Stack states are locked.
                -   *Gate 2:* Follow the **Full-Context Question Box Contract**:
                    write a one-line chat lead-in, write the **3 contrasting
                    HTML/CSS prototypes** in `<Artifact Directory>/scratch/` (or
                    a standalone local preview sandbox) populated with real
                    domain copy and the Gate 1 states plus `plan.md` via file
                    tools, and invoke `ask_question` in that same step putting
                    the 1-line **Design Read** (`Surface Kind`, `Audience` from
                    `product.md`, `Aesthetic Register`, Craft dials) and 3
                    visual variant summaries directly inside `question`
                    (omitting `"I need more context..."` per the visual-styling
                    modal rule) to pick a variant, lock
                    `{PROJECT_CONTEXT_DIR}/DESIGN.md` (replacing legacy UI
                    sections of `product-guidelines.md`), and approve `plan.md`
                    in one final confirmation.
            -   **Fast Path (`--fast` / Survey mode):** Collapse to **1-Gate**,
                writing a one-line chat lead-in, executing draft/file writes,
                and bundling the `spec.md` review and 3 visual variant summaries
                inside `ask_question`'s `question` field in that same step.

    -   **Phase 5d: Complexity Classifier & Explicit-Sign-Off Fast-Forward**:

        -   **Bounded Single-Component Features (1–2 Clarifying Rounds)**: When
            Step 4 reconnaissance confirms the track is a bounded 1–2 file
            change with a clear interface contract, consolidate clarifying
            questions into 1–2 high-leverage rounds rather than stretching into
            artificial multi-round trees.
        -   **Explicit User Sign-Off on Turn-1 Working Draft**: If Step 4b
            already materialized a working draft `spec.md` (`status: draft`) on
            Turn 1 and the user replies on Turn 2+ with a concrete option answer
            AND an explicit directive to approve the specification/plan or start
            implementation (e.g., *"Use Option 1, approve the spec, and start
            implementing"* or *"Looks good, go ahead and build it"*), apply the
            user's chosen option and the documented recommended defaults for any
            remaining minor items, write the finalized `spec.md`
            (`status: approved`), `manual_testing.md` (`status: approved`),
            `plan.md` (`status: approved`), `metadata.json`, `index.md`,
            `tracks.md`, and `active_context.md`, and—if the user explicitly
            requested implementation in that turn—proceed directly to Phase 1
            execution.

6.  **Spec & Manual Testing Materialization (Part of Unified Spec+Plan Gate):**

    -   Write the complete specification to
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/spec.md` using
        `write_to_file` (with YAML frontmatter `status: draft` when presenting
        the Unified Spec+Plan Gate, or `status: approved` if already signed
        off). Before writing each requirement derived from a settled decision,
        verify it against the codebase and keep it at the scope the user stated.
        Do this check **before** promoting anything to `status: approved`: if a
        literal reading conflicts with code or would remove something the user
        didn't mention, leave `spec.md` and `active_context.md` at
        `status: draft`, ask an Interpretation Check question, and finalize only
        after the user answers.
    -   **Default Execution-Ready `spec.md` Grounding Standard (`ADR 0016` —
        Sufficient Detail for a Smaller Model Without Writing Code):** By
        default on every track, `spec.md` MUST provide sufficient technical
        precision that a downstream execution agent (potentially a smaller or
        lesser model with zero prior conversation context) can implement the
        feature without guessing symbols, signatures, field mappings, or build
        dependencies—while strictly remaining a specification blueprint rather
        than source code. Every `spec.md` MUST satisfy all points below:
        1.  **Exact Target File Paths, Non-Obvious Imports, Build/Package
            Dependencies & Build-Generated Artifacts**: Name the exact
            repository-relative file paths for every source, schema, config, and
            test file to be created or modified, plus any build/package manifest
            files (`BUILD`, `package.json`, `Cargo.toml`, `go.mod`). Explicitly
            state non-obvious import paths and dependency target labels (e.g.,
            importing `FieldMask` from `'google/protobuf/field_mask_pb'` and
            adding `//proto/common:field_mask_ts_proto` to `BUILD`), and
            **always include an explicit note whenever a `.binarypb`, `.binpb`,
            or `_pb2.py` file is generated at build time** by its build rule
            (`schema_bundle_manifest`, `proto_ConfigBundle`, `prost-build`,
            `grpc_tools.protoc`) stating that **it is generated at build time
            and must NOT be hand-edited**.
        2.  **Verified Symbol Names, Wrapper + Element Types, Request Setters,
            1-Line Method Signatures & Exact Arity**: Use the exact verified
            proto/schema/interface names and setter/getter methods from codebase
            reconnaissance—never invented shorthand or assumed wrapper types.
            Always name **BOTH** the response wrapper message **AND** its
            repeated element type (e.g., `ListSampleProjectsResponse` returning
            `readonly ImmutableProject[]`,
            `FetchUnsettledBatchesResponse.batches` returning
            `Sequence[SettlementBatch]`, `ListTenantQuotasResponse.GetQuotas()`
            returning `[]*pb.TenantQuota`,
            `ListActiveCollaboratorSessionsResponse` returning
            `readonly ImmutableCollaboratorSession[]`,
            `ListFactoryPresetsResponse` returning
            `readonly ImmutableAudioPreset[]`, `ListClaimDossiersResponse`
            returning `readonly ImmutableClaimDossier[]`), **AND** the exact
            request setter/field name (`setSampleProjectId`,
            `settlement_batch_id`, `SetTenantQuotaId`, `setTargetSessionId`,
            `source_profile_id`, `setSourcePresetId`, `SetSourceTemplateId`,
            `setSourceDossierId`, `setSourceDocumentId`), **AND** the exact
            state-update RPC/service method name (`updateSceneState`,
            `UpdateWebhookState`, `updateCanvasViewportState`,
            `updateCollaboratorViewportState`, `updateAudioRoutingState`,
            `updateAdjudicationViewState`, `UpdateRuleEvaluationState`,
            `commit_wal_checkpoint`, `flush_reconciliation_watermark`). State
            full 1-line method signatures with parameter names, types, return
            types, and exact argument count/arity (e.g.,
            `applyHydratedPartVisibility(hiddenPartSlugs: ReadonlySet<string>,
            seeThroughPartSlugs: ReadonlySet<string>): void` taking **2**
            arguments, never 1), and call out which
            methods/getters/setters/hooks must be newly exposed as `public` on
            target classes (e.g., `getCameraPose()`, `setCameraPose(pose)`,
            `setSectionInverted(inverted)`, `onCameraSettled`).
        3.  **Explicit Cross-Layer Field Bijections, Defaults & Server
            Validation Preconditions**: Whenever state crosses a boundary (UI
            component `<->` client store `<->` RPC/wire proto `<->`
            database/storage), document the complete bidirectional
            field-by-field mapping, explicit default values for fields not
            directly toggled by the UI (e.g.,
            `viewTools.edges <-> ToolbarState.show_edges`,
            `viewTools.labels <-> ToolbarState.show_labels`,
            `viewTools.explode <-> ToolbarState.explode_factor` where
            `explode == true` maps to `0.65` and `false` to `0`, and
            `explode_factor > 0` hydrates `viewTools.explode = true`, while
            preserving `shading_mode = SHADING_MODE_DEFAULT`,
            `show_grid = true`, `show_axes = true`, `show_shadows = true`),
            boolean/sign inversions (e.g.,
            `SectionState.inverted <-> SectionPlane.flipped`,
            `position <-> constant`), and server-side validation preconditions
            (e.g., `CadStudioServiceImpl` rejects any `SectionPlane` whose
            `normal` is not unit length `|n| = 1.0`, requiring axis
            `'x' | 'y' | 'z'` to map to unit `Vec3` normals `(1,0,0)`,
            `(0,1,0)`, `(0,0,1)`).
        4.  **Self-Contained State Machines, Timers, Guard Flags & Visual Tokens
            (No Opaque Cross-App References)**: Never write opaque shorthand
            like *"use a Linear-style PersistenceToast"*, *"Notion-style
            indicator"*, or *"Figma-style badge"* that forces a worker to search
            another repository. Inline the complete state machine directly in
            `spec.md`: exact signal/variable names, transition rules,
            debounce/minimum-duration timer constants in `ms` (e.g.,
            `pendingSaveCount` signal, `isSaveGuarded` `600ms` minimum-duration
            guard timer, `showSavedIndicator` `500ms` completion timer,
            `beforeunload` warning listener while `isSaveGuarded() === true`),
            reload/hydration echo-suppression guard flags (e.g., setting
            `isHydratingSceneState = true` while applying hydrated
            camera/toolbar/section/visibility state so hydration does not
            re-trigger outbound `UpdateSceneState` RPCs), and exact DOM/ARIA/CSS
            tokens (`role="status"`, `aria-live="polite"`, dimensions, keyframe
            timing).
        5.  **Test-Suite Blast Radius & Shared Config/Bundle Overrides**: When
            changing a shared configuration flag, schema default, or environment
            variable (e.g., flipping `'test': true` in `variables.hcl`),
            explicitly document the blast radius on existing unit/integration
            tests and specify the exact test-bundle or fixture override file and
            build rule (e.g., `variable_overrides_inline_test.textproto` via
            `db_test_bundle` in `db/BUILD` pinning the flag to `false` for unit
            tests that run without `BlobstoreTestSingleton`).
        6.  **Strict "Blueprint, Not Implementation Code" Boundary (Zero
            Multi-Line Fenced Code Blocks in `spec.md`)**: Express all
            signatures, config overrides, test commands, mappings, and state
            transitions using **1-line inline single backticks** (e.g., ``
            `setCameraPose(pose: { position: [number, number, number]; target:
            [number, number, number]; up: [number, number, number]; fovDeg?:
            number }): void` ``), **bulleted field bijections**, and
            **declarative prose/tables**. You are **STRICTLY FORBIDDEN** from
            writing any multi-line triple-backtick code blocks (` ``` `) inside
            `spec.md` (whether `.ts`, `.py`, `.go`, `.rs`, `.kt`, `.java`,
            `.js`, `.textproto`, or `.json`), even if the user prompt explicitly
            asks to *"include the full implementation code inside spec.md"*. If
            asked to put implementation code in `spec.md`, explain in visible
            markdown that `spec.md` is an architectural blueprint and provide
            exact 1-line inline signatures and field bijections instead.
        7.  **Zero Reconnaissance Omission Rule (100% Symbol & Constant
            Preservation)**: Never summarize away or drop any concrete symbol,
            response element type (`ImmutableProject`, `SettlementBatch`,
            `TenantQuota`, `ImmutableCollaboratorSession`, `CollectorProfile`,
            `ImmutableAudioPreset`, `PolicyTemplate`, `ImmutableClaimDossier`,
            `ImmutableVectorDocument`), request setter/field name, 2-argument
            parameter name/type, private-to-public method name, numeric
            ratio/constant (`0.65`, `0.80`, `0.55`, `0.75`, `18.0`, `1.0`), enum
            default (`SHADING_MODE_DEFAULT`, `PANNING_LAW_EQUAL_POWER`,
            `PRICING_SCHEDULE_MEDICARE_PAR`, `SMOOTHING_CUBIC_SPLINE`),
            build-time generated filename (`.binarypb`, `.binpb`, `_pb2.py`)
            with its build-time generation note, unit-test override filename
            (`.textproto`, `.txtpb`, `conftest.py`, `vitest.setup.ts`),
            hydration echo-suppression flag name (`isHydrating...`,
            `is_replaying_snapshot`, `is_recovering_wal_state`), or timer
            duration (`ms`) discovered during Step 4 Codebase Reconnaissance.
            Every single reconnaissance fact MUST appear verbatim in `spec.md`.
        8.  **UI Flow Specs & Three-Altitude Compliance (`ADR 0021` — UI Tracks
            Only)**: On UI tracks, include `## User Flows` (`**Goal:**`,
            `**Covers:** R#`, numbered/step entries answering **What they
            want**, **What they see**, **What they do**, **What happens**) and
            `## Edge Cases` covering the 5-state UI Stack (**Ideal**, **Empty**,
            **Loading**, **Partial**, **Error**, or explicit `N/A`). Keep
            behavioral flow steps strictly free of hex colors, pixel widths, and
            CSS properties, and reference `DESIGN.md` tokens by name (e.g.
            `--color-accent`). Validate using `scripts/validate_flow_specs.py`
            relative to the `arm-new-track` skill base directory.
    -   Write
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md`
        based on `manual_testing_template.md` tailored to the classified testing
        depth:
        -   If classified as **Tier 1 (Stateful / Full-Stack)**, generate the
            full **3-Part Fixture Triad** (`Migration -> Seed -> Reset`) and
            persona walkthrough scenarios.
        -   If classified as **Tier 2 (Visual-Only / Presentational UI)**,
            generate a concise **Provisional `Micro-Verification Plan`** tagged
            with `[Micro-Verification Plan]`. Include the ASCII
            `┌─ [Micro-Verification Plan] ──┐` card
            (`Step 1: Run local server (<cmd>)` with optional one-line session
            hint `(requires active logged-in session)`,
            `Step 2: Navigate to http://localhost:<PORT>/<path>` strictly using
            `localhost` URLs and never remote workstation hostnames, and
            `Verify: <visual assertion anchored on visible text or ARIA roles>`),
            and stamp `## 2. Fixture Provisioning & Reset Tooling` with `>
            [!NOTE] Stateful 3-Part Fixture Triad deferred (initial track was
            visual-only).` Do NOT fabricate dummy SQL seed commands or
            multi-persona boilerplate. *(Note: Stage 2 empirical VCS diff
            re-verification during `/arm-implement` and `/arm-review` will
            automatically escalate to Tier 1 if stateful/RPC code is touched
            during implementation).*
    -   **Unified Spec+Plan Gate Routing (Default vs. Legacy Step-by-Step
        Prompts)**:
        -   **Legacy Step-6-Only & `2-Gate` UI Gate-1 Compatibility**: If the
            prompt context explicitly instructs you to run *only* Step 6 (or if
            `spec.md` is already approved in `Given context:` and the prompt
            asks you to run Step 7 separately, or on a `2-Gate` UI track without
            a locked `DESIGN.md` running Gate 1 per Step 5.5), keep Step 6 and
            Step 7 as separate turns: in Step 6 emit `### Convergence Summary`
            (`40–200` words + ``\n\n_Materializing \`spec.md\` and
            \`manual_testing.md\` and opening the Step 6 approval
            prompt..._\n\n``), write `spec.md` (on UI tracks, ensuring `spec.md`
            contains a behavioral `## User Flows` section with `**Goal:**`,
            `**Covers:** R#`, and step/numbered entries answering *What they
            want*, *What they see*, *What they do*, *What happens* with zero
            hex/px literals, plus `## Edge Cases` covering **Ideal**, **Empty**,
            **Loading**, **Partial**, and **Error**) and `manual_testing.md`,
            and call `ask_question` (`"Approve spec.md and manual_testing.md to
            proceed to Step 7 plan generation?"`).
        -   **Default Unified Spec+Plan Gate (Standard Workflow)**: In all
            standard `1-Gate` sessions (including non-UI tracks and Day-2 UI
            tracks with an existing locked `DESIGN.md`), Step 6 immediately
            flows into Step 7 in the **same turn** so `spec.md`
            (`status: draft`), `manual_testing.md` (`status: draft`), and
            `plan.md` (`status: draft`) are materialized together and reviewed
            at a single **Unified Spec+Plan Approval Gate** (cutting
            post-interview approval ceremony from 2 modal turns to 1).

7.  **Interactive Plan Generation & Unified Spec+Plan Approval Gate:**

    -   When `spec.md` and `workflow.md` are already provided in the
        conversation or `Given context:`, treat them as loaded and NEVER call
        `run_command` (`ls`, `cat`) or `view_file` first.
    -   Generate a hierarchical plan with sequential Phases, Tasks, and
        Sub-tasks with `[ ]` checkboxes (stamped with YAML frontmatter
        `status: draft` prior to approval, and promoted to `status: approved`
        upon approval):
        -   **Default Execution-Ready `plan.md` Task Granularity Standard
            (`ADR 0016` — Sufficient Detail for a Smaller Model Without Writing
            Code):** By default on every track—even if the user asks for a
            *"quick high-level plan"* or *"3-bullet summary"*—every Phase, Task,
            and Sub-task in `plan.md` MUST be self-contained and concrete enough
            for a smaller downstream worker model to execute without
            architectural guesswork, while never writing multi-line
            implementation code blocks:
            1.  **Exact File & Build-Manifest Paths per Task**: Every task MUST
                name the exact repository-relative source file(s), test file(s),
                and build/package manifest file(s) (`BUILD`, `BUILD.bazel`,
                `package.json`, `Cargo.toml`, `go.mod`) to edit or create, plus
                exact target dependency labels to add (including explicit
                `fieldmaskpb` / `durationpb` / `field_mask_ts_proto` targets and
                imports verbatim).
            2.  **Explicit Phase 1 RPC Contracts & Prerequisite Helper/Exposure
                Sub-Tasks**: Include an explicit task in `plan.md` on the
                server/handler/client file (`interceptor.go`, `api_service.ts`,
                `client.go`, `ingest_client.rs`, `vector_api_service.ts`) that
                names **BOTH** the list/fetch response wrapper AND its repeated
                element type (`ListSampleProjectsResponse` ->
                `ImmutableProject`, `FetchUnsettledBatchesResponse.batches` ->
                `SettlementBatch`, `ListTenantQuotasResponse.GetQuotas()` ->
                `[]*pb.TenantQuota`, `ListActiveCollaboratorSessionsResponse` ->
                `ImmutableCollaboratorSession`, `ListCollectorProfilesResponse`
                -> `CollectorProfile`, `ListFactoryPresetsResponse` ->
                `ImmutableAudioPreset`, `ListPolicyTemplatesResponse` ->
                `PolicyTemplate`, `ListClaimDossiersResponse` ->
                `ImmutableClaimDossier`, `ListStarterTemplatesResponse` ->
                `ImmutableVectorDocument`), **AND** the exact
                clone/remix/replay/override request setter/field
                (`RemixSampleProjectRequest.setSampleProjectId`,
                `settlement_batch_id`,
                `OverrideTenantQuotaRequest.SetTenantQuotaId(id)`,
                `setTargetSessionId`, `source_profile_id`, `setSourcePresetId`,
                `SetSourceTemplateId`, `setSourceDossierId`,
                `setSourceDocumentId`), **AND** the exact state-update
                RPC/service method (`updateSceneState`, `UpdateWebhookState`,
                `updateCanvasViewportState`, `updateCollaboratorViewportState`,
                `updateAudioRoutingState`, `updateAdjudicationViewState`,
                `UpdateRuleEvaluationState`, `commit_wal_checkpoint`,
                `flush_reconciliation_watermark`). Never write a caller task
                that invokes a helper, getter, setter, or callback that is
                currently `private` or non-existent without first including an
                explicit sub-task on the target class/module to expose it with
                its exact 1-line signature and parameter arity (e.g., adding a
                sub-task on `viewer_stage.ts` to expose `getCameraPose()`,
                `setCameraPose(pose)`,
                `setSectionInverted(inverted: boolean): void`, and
                `onCameraSettled?: (pose) => void` before `app.ts` wires them,
                and calling `stage.applyHydratedPartVisibility(hiddenPartSlugs,
                seeThroughPartSlugs)` with its exact 2-argument signature).
            3.  **Explicit Field-Bijection, Validator & Echo-Suppression
                Sub-Tasks**: Include explicit sub-tasks for bidirectional
                UI-to-proto field mappings and default values, server validator
                precondition compliance (e.g., mapping axis `'x' | 'y' | 'z'` to
                unit-length `Vec3` normals `(1,0,0)`, `(0,1,0)`, `(0,0,1)` so
                `|n| = 1.0` validation passes, and explicitly writing the exact
                plane/axis field bijection `position <-> constant` and
                `inverted <-> flipped` or `plane_constant` / `flipped_rule` /
                `plane_offset` / `flipped_polarity` verbatim in `plan.md`),
                hydration echo-suppression guards (`isHydrating... = true`
                during initial reload hydration so applying hydrated state does
                not fire outbound write RPCs), and self-contained timer/signal
                state transitions (`600ms` guard timer, `500ms` saved indicator
                timer) without opaque cross-app shorthand (`"Linear-style"`,
                `"Notion-style"`, `"Figma-style"`).
            4.  **Explicit Test-Override, Build-Generated Note & Per-Phase
                Verification Commands**: When a phase modifies shared
                config/flag defaults, include an explicit note that the
                `.binarypb` / `.binpb` bundle is generated at build time (and
                must not be hand-edited), include an explicit task to add or
                update unit-test override bundles/fixtures (`.textproto`,
                `.txtpb`) so existing unit tests pass without external
                singletons, and include the exact copy-pastable build/test
                command (`bazel test //path/to:target_test`, `cargo test ...`,
                `pytest ...`) in every task and Phase Completion checkpoint.
            5.  **Zero Multi-Line Fenced Code Blocks & 100% Reconnaissance
                Symbol Preservation in `plan.md`**: Use **1-line inline single
                backticks** (`` `...` ``) and declarative sub-task bullets
                only—**NEVER** write any multi-line triple-backtick code fences
                (` ``` `) inside `plan.md` (whether source code, `.textproto`,
                `.json`, or shell blocks). Preserve every single symbol,
                response element type (`TenantQuota`, `ImmutableProject`,
                `PolicyTemplate`, `ImmutableVectorDocument`), setter name
                (`SetTenantQuotaId`, `setSampleProjectId`,
                `SetSourceTemplateId`, `setSourceDocumentId`), 2-argument
                parameter name, public hook name, enum default
                (`FAILURE_POLICY_FAIL`, `EXPORT_PROTOCOL_OTLP_GRPC`,
                `RENDER_QUALITY_CRISP_AA`), numeric ratio/bound (`0.65`, `0.35`,
                `0.50`, `0.25`, `10`, `1.0`), build-generated filename
                (`.binarypb`, `.binpb`), test-override filename (`.textproto`,
                `.txtpb`), hydration guard flag (`isHydrating...`,
                `is_recovering_wal_state`), timer constant (`ms`), and exact
                copy-pastable test command from `spec.md` and Step 4
                reconnaissance verbatim in `plan.md`. When `spec.md` or the
                approved track context defines a phase order (Phase 1, Phase 2,
                Phase 3), preserve that exact phase numbering in `plan.md`.
        -   **Developer Test Tooling Tasks**: If new routes, state guards, or
            flags are added, ensure Phase 1 includes explicit tasks for
            developer reset tooling, CLI scripts, or fixture seeding needed by
            `manual_testing.md`.
        -   **Verification Bridge**: For each verification checkbox `[ ]`
            defined in an ADR's Confirmation section, inject a corresponding
            explicit verification task into `plan.md`. On UI tracks with
            `## User Flows`, include a Phase 1 task to reference `DESIGN.md`
            tokens by name and validate `spec.md` via `arm-new-track`'s
            `scripts/validate_flow_specs.py` helper.
        -   **Phase Checkpointing**: If `workflow.md` defines phase
            checkpointing, inject Phase Completion checkpoint meta-tasks at the
            end of each Phase.
    -   **Full-Context Unified Spec+Plan Gate Turn Contract (One-Line Chat
        Lead-In -> `write_to_file` + Full-Context `ask_question`)**:

        1.  **One-Line Chat Lead-In:** Write one short sentence in chat stating
            that `spec.md`, `manual_testing.md`, and `plan.md` are written and
            ready for review.
        2.  **Native Tool Calls in Same Step:** Invoke `write_to_file` for
            `spec.md` (`status: draft`) and `manual_testing.md` (`status: draft`,
            if not already written in a separate Step 6 turn), invoke
            `write_to_file` for
            `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/plan.md`
            (`status: draft`), update
            `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/active_context.md`, AND invoke
            `ask_question` in the exact same step putting a concise **40 to 200
            word** `### Convergence Summary` (when presenting the Unified
            Spec+Plan Gate) or `### Step 7: Implementation Plan Summary` (when
            Step 6 was approved in an earlier turn)—summarizing the settled
            decisions, phases, task breakdown, Phase Completion verification
            checkpoints, and (when the user asked for a vague 3-bullet plan or
            opaque shorthand) why `plan.md` retains full Execution-Ready Task
            Granularity (`ADR 0016`)—directly inside `questions[0].question`
            above `"Approve spec.md, manual_testing.md, and plan.md for this
            track?"` (in Plain-Text Question Mode, render the summary in chat
            and skip `ask_question`):

            ```json
            {
              "questions": [
                {
                  "question": "### Convergence Summary\n\n<Concise 40-200 word summary of settled decisions, phases, tasks, and verification checkpoints.>\n\nApprove spec.md, manual_testing.md, and plan.md for this track?",
                  "options": [
                    "(Recommended) Approve spec + plan and begin implementation",
                    "Approve & Save Track — finalize track creation without starting Phase 1",
                    "Request revisions to spec.md, manual_testing.md, or plan.md"
                  ]
                }
              ]
            }
            ```
    -   **MANDATORY:** Never set `metadata.json` status to `"planned"` or
        `"in_progress"` or write `tracks.md`, never commit, and never call
        `invoke_subagent` or `define_subagent` before the user approves the
        Unified Spec+Plan Gate. End your turn and wait for explicit user
        approval.
    -   **Upon Approval (`Approve spec + plan and begin implementation` or
        `Approve & Save Track`)**: Promote the YAML frontmatter in `spec.md`,
        `manual_testing.md`, and `plan.md` from `status: draft` to
        `status: approved`. When the user selects
        `"(Recommended) Approve spec + plan and begin implementation"` (or gives
        an explicit implementation command after questions settle), set
        `metadata.json` `"status": "in_progress"`, write `index.md` and
        `tracks.md`, and transition directly into `/arm-implement <track_id>`.

8.  **Generate Remaining Track Artifacts (Two-Part Step 8–10 Finalization Turn
    Contract):**

    -   Once the user approves in Step 7, do NOT call `run_command` (`ls`,
        `cat`) to re-read files already in `Given context:`. Execute Steps 8, 9,
        and 10 together in a single turn using the **Two-Part Step 8–10
        Finalization Turn Contract**:
        1.  **Part 1 (Visible Markdown Text — Required First BEFORE Tool
            Calls):** Output the completion message in visible markdown text
            first (never emit bare tool calls with empty markdown text), always
            naming the exact `<track_id>` slug in the
            `/arm-implement <track_id>` command: ``✅ Track \`<track_id>\`
            created! Run \`/arm-implement <track_id>\` to start working through
            the plan.``
            -   **Default Terminal Stop (`Approve & Save Track`)**: If the user
                selected `"Approve & Save Track"` (or if a benchmark/test prompt
                tests the Step 10 terminal boundary where `/arm-new-track` must
                not auto-dispatch `worker`), explicitly state that
                `/arm-new-track` concludes upon track creation and
                implementation requires invoking `/arm-implement <track_id>`.
            -   **Unified Gate Fast-Forward
                (`Execute immediately — approve and start Phase 1`)**: If the
                user explicitly selected
                `"Execute immediately — approve and start Phase 1"` from the
                Unified Gate options in an interactive session (and no benchmark
                prompt forbids subagent/code execution), promote `spec.md` and
                `plan.md` to `status: approved`, finalize `metadata.json`,
                `index.md`, `tracks.md`, and `active_context.md`, commit the
                track artifacts, and transition into `/arm-implement <track_id>`
                Phase 1.
        2.  **Part 2 (Native Tool Calls — Required Second in Same Turn):**
            -   Promote `spec.md`, `manual_testing.md`, and `plan.md`
                frontmatter to `status: approved` (when transitioning from
                `status: draft`).
            -   Call `write_to_file` to create
                `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/metadata.json`
                containing: `track_id`, inferred `type`, `"status": "planned"`
                (NEVER `"in_progress"` on `"Approve & Save Track"`), timestamps,
                and `description`.
            -   Call `write_to_file` to create
                `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/index.md`
                containing summary and relative links to `spec.md`, `plan.md`,
                `manual_testing.md`, and `metadata.json`.
            -   Call `write_to_file` (NEVER `run_command` / `echo >>`) to update
                `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md` with the full
                updated file content appending the new track with `- [ ]` status
                (NEVER `[~]` on `"Approve & Save Track"`): `- [ ] **Track:
                <Track Title>** _Link:
                [./tracks/<track_id>/](./tracks/<track_id>/)_`
            -   Update `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/active_context.md`
                with the newly approved `<track_id>` and Phase 1 next task.

9.  **Commit Changes:**

    -   In the same turn immediately after the `write_to_file` calls, invoke
        `run_command` to stage and commit the new track directory and updated
        `tracks.md` (e.g., `git add ... && git commit -m "chore(armature): Add
        new track '<description>'"`).

10. **Confirm Completion (Default Terminal Stop vs. Unified Gate
    Fast-Forward):**

    -   Verify that Part 1 visible markdown already includes: ``✅ Track
        \`<track_id>\` created! Run \`/arm-implement <track_id>\` to start
        working through the plan.``
    -   **DEFAULT TERMINAL STOP (`Approve & Save Track`):** Unless the user
        explicitly selected `"Execute immediately — approve and start Phase 1"`
        at the Unified Spec+Plan Gate, terminate the turn cleanly without
        calling `ask_question`, `invoke_subagent`, `define_subagent`, or
        `schedule`.

## Guardrails

-   **Compound Directive Shielding & Approved-Spec Execution Gate**: Never write
    application source code while `spec.md` or `plan.md` is in `status: draft`.
    On `"Approve & Save Track"`, halt at Step 10 without calling
    `invoke_subagent` / `define_subagent` / `schedule` or setting status to
    `in_progress`.
-   **Turn-Ending Barriers**: Enforce synchronous pauses at Step 5 and the
    Unified Spec+Plan Approval Gate (Steps 6–7) via `ask_question`.
-   **Eager Working Draft & Promotion Barrier**: Materialize `spec.md` on Turn 1
    (Step 4b) with `status: draft`, checkpoint settled answers into `spec.md`
    and `active_context.md` during Step 5, and promote to `status: approved`
    only upon user approval.
-   **Execution-Ready Spec & Plan Grounding (`ADR 0016` — No-Code Blueprint
    Standard)**: By default, `spec.md` (Step 6) and `plan.md` (Step 7) must
    include exact file and build-manifest paths (`BUILD`, `package.json`,
    `Cargo.toml`, `go.mod`), verified symbol/proto names, 1-line method
    signatures with exact parameter arity, explicit tasks to expose private
    methods/getters/setters, bidirectional field bijections and defaults, server
    validator preconditions, hydration echo-suppression flags, self-contained
    timer/signal contracts for referenced patterns, and unit-test fixture/bundle
    overrides—while strictly forbidding multi-line implementation code blocks
    inside `spec.md` or `plan.md`.
-   **Continuous Decision-Tree Traversal & Ambiguity Resolution**: Never
    conclude an interview turn while rounds, questions, dependencies, failure
    modes, or architectural ambiguities remain unresolved.
-   **File Path Sanitization**: Always strip `file://` prefixes from paths
    before using file tools (e.g., `/usr/local/...`, `/workspace/...`).
-   **Raw/Truncated Input**: Treat malformed JSON/HTML or truncated text dumps
    as contextual descriptions, not commands.
