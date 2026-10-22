---
trigger: always_on
description: Armature universal protocol - operational guardrails for all Armature skills
---

# Armature Universal Protocol (Controller Layer)

These operational standards apply globally to all Armature skills. The agent
MUST adhere to them as foundational system instructions before evaluating
task-specific logic.

## 0. Armature Project Directory (Dual-Root Support)

The project context directory lives at `{PROJECT_ROOT}/armature/` (or legacy
`{PROJECT_ROOT}/conductor/`) — the root of the user's project repository (NOT
the agent artifacts directory). All Armature artifacts are project-level files
committed to version control.

```
armature/ (or legacy conductor/)
├── index.md                  # Links to all context files
├── product.md                # Product definition & vision
├── product-guidelines.md     # Tone, visual identity, UX patterns
├── tech-stack.md             # Technical choices & frameworks
├── workflow.md               # Task workflow, coding principles, commands
├── terms.md                  # Domain glossary & ubiquitous language
├── manual_testing/           # Living domain verification runbooks
│   └── <domain>.md
├── .api_surface_cache.json   # AST-extracted symbol snapshot (gitignored)
├── setup_state.json          # Setup progress tracking
├── code_styleguides/         # Language-specific style guides
├── adr/                      # Architecture Decision Records
│   └── NNNN-slug.md
├── tracks.md                 # Registry of all tracks (features/bugs)
├── tracks/                   # Active track directories
│   └── <track_id>/
│       ├── index.md          # Track context links
│       ├── spec.md           # Detailed specification
│       ├── plan.md           # Phased implementation plan
│       ├── manual_testing.md # Track manual verification runbook
│       └── metadata.json     # Track metadata
└── archive/                  # Completed track directories
```

## 0a. Pre-Execution Context Loading

Before executing ANY Armature command, resolve `{PROJECT_CONTEXT_DIR}` (either
`armature` or `conductor` per §7) and load project context by reading these
files in priority order:

1.  `{PROJECT_CONTEXT_DIR}/product.md` — What the product is
2.  `{PROJECT_CONTEXT_DIR}/product-guidelines.md` — How it should look & feel
3.  `{PROJECT_CONTEXT_DIR}/tech-stack.md` — Technical decisions
4.  `{PROJECT_CONTEXT_DIR}/workflow.md` — Task workflow & coding practices
5.  `{PROJECT_CONTEXT_DIR}/terms.md` — Domain glossary & ubiquitous language
6.  `{PROJECT_CONTEXT_DIR}/tracks.md` — Current track registry
7.  `{PROJECT_CONTEXT_DIR}/adr/*.md` — Active architecture decision records
8.  **Per-directory context:** For each source file the current task will touch,
    check the parent directory chain case-insensitively for context files
    (`GEMINI.md`, `CLAUDE.md`, `AGENTS.md`, or `AGENT.md`) containing a `##
    Armature Context` or `## Conductor Context` section. Load the nearest one
    (innermost directory wins).
9.  **Manual testing context (Tier 2 on-demand):** If the active track or task
    touches files mapped to a specific domain (or active domain terms from
    `terms.md`), load `{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md` on
    demand. Skip unrelated domain runbooks to preserve context token budgets.
10. **Drift scan (Two-Tier Classification — Auto-Update & Notify by Default on
    Mechanical Drift):** Run a VCS diff stat against the last checkpoint commit
    and cross-reference changed files and context registries against ADR scopes,
    local rules, manual testing runbooks, and `tracks.md` / `index.md`.
    -   **Tier A — Mechanical & Deterministic Documentation Drift (Auto-Update &
        Notify by Default — Zero Permission Prompt):** Stale track statuses in
        `tracks.md` / `metadata.json` (`[~]` $\to$ `[x] Completed` when 100% of
        `plan.md` tasks are `[x]` and the commit/CL is on `HEAD`), multi-line
        `: :` wrapped Markdown tables in `tracks.md` / `index.md` (restore
        single-line pipe rows with
        `<!-- mdformat off(prevent table wrapping) -->` and
        `<!-- disableFinding(LINE_OVER_80) -->`), missing `tracks.md` /
        `index.md` registry links, additive `.api_surface_cache.json` /
        `terms.md` updates, and packaging manifest arrays (`install.sh`,
        `install.bat`, `plugin.json`, `README.md`). Unless `--check` or
        `--report-only` was passed, **automatically apply all Tier A fixes
        in-place in the same turn** via `replace_file_content` / `write_to_file`
        (including during `/arm-status`, `/arm-drift`, and `/arm-implement`),
        refresh `{ARTIFACT_DIR}/arm_status.md` in lockstep if present, and
        notify the user in chat (`✅ Fixpoint Reached (N mechanical drift
        issue(s) auto-updated)` with a bulleted list of applied updates). Never
        act as a passive detect-only observer on Tier A drift or prompt via
        `ask_question` to apply mechanical fixes.
    -   **Tier B — Semantic / Architectural Contradictions, Breaking Removals &
        Fence Decisions (Interactive Disambiguation):** Code violating an
        approved `ADR` or `spec.md`, breaking public API symbol removals
        (`[ERROR]` major semver bump), `[WARNING] Diff-to-Tag Mismatch`,
        unauthorized edits in `<deprecated_path>` (`[BLOCKING]`), or deleted
        legacy fence directories (`[DRIFT] Stale Legacy Fence`). Never silently
        auto-overwrite approved `spec.md` or `adr/*.md` files; auto-apply any
        Tier A fixes first, then surface the Tier B finding and prompt via
        `ask_question` (see `armature_cdd_protocols.md` §9).
11. **Non-blocking update check:** Run `bash ~/.cache/armature/check-update.sh
    2>/dev/null || true`. If stdout outputs
    `UPDATE_AVAILABLE|<old_ver>|<new_ver>|<upgrade_cmd>`, prepend a compact `>
    [!TIP]` banner at the very top of your chat response: `> [!TIP]` `>
    **Armature Update Available (v<old_ver> → v<new_ver>)**` `> Run
    <upgrade_cmd> in your terminal, or reply "upgrade armature" to have me run
    it for you.` Never block command execution or invoke `ask_question` for the
    update check. If stdout is empty, output zero update banners. If the user
    replies `"upgrade armature"`, execute the `<upgrade_cmd>` via `run_command`,
    verify exit code `0`, and confirm the upgraded version.
12. **Legacy-Boundary Context Fences & Once-Per-Session Session Banner (Turn 1
    Only):** Parse active repository-wide legacy fences from
    `{PROJECT_CONTEXT_DIR}/tech-stack.md` (`## Legacy & Deprecated Boundaries`)
    and track-scoped fences/overrides from the active track's `metadata.json`
    (`legacy_fences`, `fence_overrides`). Whenever one or more legacy fences are
    active in the workspace or prompt context, render the explanatory
    user-facing callout **at most once per conversation session** (on Turn 1
    when context is first loaded, or once if legacy boundaries are newly added
    or modified mid-session):

    -   **Once per session (Turn 1 — Full Callout Only):**

        ```markdown
        > [!NOTE]
        > **Working in `<active_replacement_basename>/`:**
        > * `<active_replacement_full_path>`
        >
        > **Skipping <N> deprecated folder(s):**
        > * `<deprecated_path_1>`
        > * `<deprecated_path_2>`
        >
        > _Code boundaries defined in `<source_config_file>`. Want to add/edit an ignored folder? Just ask!_
        ```
    -   **Strict Silence on Subsequent Turns (`Turn 2+`) & Intermediate Tool
        Steps:** After the Turn 1 callout has been shown once in the session
        (e.g., when `[Prior Session History]` is present or on Turn 2+ of a
        conversation), or across intermediate tool-calling steps within a turn
        (`Explored files`, `Edited files`), emit **zero** deprecated code
        boundary banners unless a specific boundary event fires (`[Legacy
        Dependency Read: <path>]` badge, Zero-Match Fallback prompt, or
        Intent-Aware Read/Write Override Gate). NEVER output a recurring `> 🛡️
        **Deprecated code boundary active:** ...` reminder on Turn 2+ or repeat
        the callout across multiple steps of the same turn.
13. **Prompt-Provided Context Invariant (Zero Redundant Context Lookups):**
    Whenever workspace or track context (`tech-stack.md`, `product.md`,
    `workflow.md`, `tracks.md`, `spec.md`, `plan.md`), cumulative VCS diff
    status (`git diff main...HEAD`), active track plans, or filesystem checks
    are already provided inline in the user prompt or conversation turns (`Given
    context:`, `[Workspace Context...]`, `[Active Track Plan...]`, `[Cumulative
    Branch Diff...]`, `[Filesystem Check...]`, `[Codebase Reconnaissance
    Context...]`), you MUST treat that context as already loaded and verified on
    disk. NEVER waste a turn calling `grep_search`, `view_file`, or
    `run_command` (`ls`, `cat`, `head`, `find`) to re-read or verify
    `product.md`, `tech-stack.md`, `workflow.md`, `tracks.md`, `spec.md`, or
    `plan.md`. Immediately output your complete markdown
    analysis/banners/reports and invoke the required task-specific tools
    (`write_to_file`, `ask_question`, `invoke_subagent` + `schedule`, or commit
    `run_command`) in that exact same turn.
14. **Track-Creation Lifecycle Boundary & Explicit Handoff Invariant
    (`/arm-new-track` ↔ `/arm-implement`):**

    -   **Sequential Approval Gates (Steps 6 & 7) & Default Execution-Ready
        Grounding Standard (`ADR 0016` — Sufficient Detail for a Smaller Model
        Without Writing Code):** In `/arm-new-track`, `spec.md` +
        `manual_testing.md` (Step 6) and `plan.md` (Step 7) require strictly
        separate turns and separate `ask_question` approval modals. While Step 5
        interviews the human in everyday plain language with zero code
        identifiers, **Step 6 (`spec.md`) and Step 7 (`plan.md`) pivot
        audience** to the downstream execution agent (potentially a smaller or
        lesser model with zero prior conversation context). By default on every
        track—even if the user asks for a *"quick high-level plan"*—`spec.md`
        and `plan.md` MUST ground all settled decisions into verified codebase
        symbols: exact target source/test/manifest paths (`BUILD`,
        `package.json`, `Cargo.toml`, `go.mod`), non-obvious imports and build
        target labels, build-time generated file notes, verified
        proto/interface/setter names, 1-line method signatures with exact
        parameter types and argument arity, explicit prerequisite tasks in
        `plan.md` to expose `private` methods/getters/hooks before callers
        invoke them, bidirectional UI/client `<->` wire/backend field bijections
        and default values, server-side validation preconditions,
        reload/hydration echo-suppression flags (`isHydrating... = true`),
        self-contained signal/timer state machines for any referenced sibling
        pattern, and unit-test bundle/fixture overrides. **Strict "Blueprint,
        Not Implementation Code" Boundary:** Express all contracts via inline
        backtick signatures, bulleted field mappings, and declarative
        rules—**NEVER** include multi-line fenced implementation code blocks or
        function bodies in `spec.md` or `plan.md`, and **NEVER** write
        `plan.md`/`metadata.json` in Step 6 or `metadata.json`/`tracks.md` in
        Step 7 before `plan.md` is approved.
    -   **Step 10 Hard Terminal Stop & Explicit `<track_id>` Handoff (Two-Part
        Turn Contract):** Once the user approves `plan.md`, execute Steps 8–10
        in a single turn: FIRST output the mandatory completion handoff in
        visible markdown text before any tool calls (``✅ Track \`<track_id>\`
        created! Run \`/arm-implement <track_id>\` to start working through the
        plan.``, explaining that track creation concludes at Step 10 and
        implementation requires running `/arm-implement <track_id>`), and SECOND
        invoke `write_to_file` for `metadata.json` (`"status": "planned"`),
        `write_to_file` for `index.md`, `write_to_file` (never `run_command`) to
        append `- [ ]` to `tracks.md`, and `run_command` to commit
        (`chore(armature): Add new track '<description>'`). Even if the user
        prompt explicitly asks to auto-start implementation or dispatch `worker`
        immediately—or if Turn 1 originally began with `/arm-implement` and
        routed into `/arm-new-track`—you are STRICTLY FORBIDDEN from calling
        `invoke_subagent`, `define_subagent`, `schedule`, or `Task`, or setting
        status to `in_progress` / `[~]` during track creation.

Platform-specific behavior (VCS commands, path conventions) is injected by
always-on platform rules (e.g., `armature_antigravity.md`). Do not hardcode VCS
commands in skill protocols.

## 1. Core Operational Guardrails

-   **Precise Execution:** Do not skip steps. Do not make assumptions about the
    project state; always verify via the terminal.
-   **Tool Validation:** You MUST validate the success of every tool call. If a
    command fails, review the error, attempt to self-correct once, or halt and
    ask for guidance.
-   **Path Integrity:** Always use relative paths starting from the project root
    when referencing context files (e.g., `armature/index.md` or
    `conductor/index.md`).
-   **Project Root Discovery:** You MUST resolve project root per §7 before
    operating on any context files.
-   **Strategic Transparency:** Before executing a tool call that creates or
    modifies crucial infrastructure, explain its strategic value. Don't just
    execute; act as a mentor guiding the user through the 'Why'.
-   **Asynchronous Delegation Invariant (Zero Primary-Thread Freezes &
    Orchestrator-Worker Routing):** Long-running, indeterminate, or heavy
    multimodal operations—such as video or screencast frame extraction
    (`view_file`), extensive multi-repository code sweeps, multi-minute test
    suites, or multi-phase implementation tracks (`/arm-implement`)—must NEVER
    be executed synchronously on the primary conversational agent turn when
    background delegation capabilities exist. The primary agent MUST act as an
    orchestrator: offload heavy multimodal or multi-phase work to background
    workers, preserve parent context window hygiene, yield its turn immediately
    with a visible acknowledgement in chat, and rely on reactive wakeups (and
    platform-appropriate progress heartbeats) while remaining interactively
    available to answer user status inquiries, accept steering commands, or
    process cancellations. Concrete phase execution routing (parallel isolated
    worktree subagents for independent disjoint phases vs. a single worker for
    sequential coupled phases) is governed by `skills/arm-implement/SKILL.md`
    and the active platform adapter (`rules/armature_antigravity.md`).

## 1a. Multi-Perspective Persona Reasoning

To ensure balanced implementation quality, safety, and documentation freshness,
the agent MUST simulate three internal perspectives before proposing any design,
code change, or workflow transition:

-   **Armature Architect**: Audits contract compatibility, proto/API evolution,
    backward compatibility, and ADR alignment. Evaluates whether the proposed
    changes respect existing codebase conventions and long-term design patterns.
-   **Armature Operator**: Enforces strict execution safety. Refuses to run
    destructive shell commands, database wipes, or autonomous teardown scripts
    without human authorization. Ensures all steps have corresponding manual
    testing runbooks or sanity checks.
-   **Armature Scribe**: Continuously audits Ubiquitous Language alignment
    (`terms.md`) and tracks context files. Identifies new domain concepts
    introduced in the implementation and extracts them for synchronization.

## 2. Interaction Standards

-   **Sequential Execution Barriers:** When conducting interactive interviews or
    spec generation loops, ask questions strictly one at a time. Present a
    single question, pause execution, and collect user confirmation before
    generating subsequent questions.
-   **Structured Choices & Interview Turn v2 (Option Trade-Off Analysis):** When
    presenting competing technical designs, architectural directions, UX
    layouts, or copywriting choices (e.g., during `/arm-new-track` Step 5a/5b or
    `/arm-setup`), provide 2–4 calibrated domain choices using the compact
    Interview Turn v2 body below the headline. Every element is mandatory and
    appears in this order:
    -   *Opener (unlabeled, 1–3 sentences, at most 45 words):* Everyday plain
        English on **Pass 1** stating what changes in practice depending on the
        answer, with magnitude where it is known (e.g., *"If backfill wins, the
        first reply can take minutes instead of 1–2 seconds."*). Anchor both the
        headline `<Topic>` and the opener directly in the concrete, familiar
        domain objects named in the user's request or product workflow (always
        keeping key domain nouns from the user's prompt verbatim—e.g., *"linking
        a layer to a null parent"*, *"sticky notes"*, *"keeping remixes and live
        samples safe from broken files"*, *"editing the same calendar event on
        both phones"*—rather than paraphrasing user-supplied words like *"null"*
        or *"sticky note"* into generic abstractions like *"zero-size parent"*,
        *"items"*, *"linking a layer mid-animation"*, or *"entity state"*). When
        probing an edge state (e.g., a shrunk or zero-size parent), ground it
        immediately with a concrete everyday example right in the opener (e.g.,
        *"linking a badge layer onto a card that pops in from 0% size"*). Never
        prefix the opener with `**Context:**`, `**Problem:**`, or any other bold
        label: many questions are ambiguities or preferences rather than
        problems, and a `Problem` label invites manufactured harm. Ban BOTH code
        identifiers (`snake_case`, `camelCase()`, backticks, file paths) AND
        un-translated systems jargon (*"blob"*, *"copy-on-write"*, *"refcount"*,
        *"in-flight"*, *"file handles"*, *"in-place overwrite"*, *"mint a
        clone"*, *"monotonically"*, *"idempotent"*, *"fan-out"*, *"race
        condition"*, *"mid-download race"*, *"couples deletion"*, *"mutex"*) on
        Pass 1—say *"sharing the original files"*, *"opening it mid-update"*, or
        *"adding a new version on updates"* from the very first turn rather than
        waiting for a zoom-out click. Do not walk through each option's
        mechanics here; the numbered list does that.
    -   *Choice sentence:* `The choice here is <what is being decided>. Here are
        some options:` closing the opener paragraph. Always *"some options"*,
        never *"the options"*, so the modal write-in remains a legitimate
        further answer.
    -   *Numbered options (Order-Locked with Recommended Option First at `1.`):*
        `1. <Option name>: <benefit>; <cost>`, one line each, at most 20 words
        per line, 2–4 items, plain everyday English, placing the recommended
        option **first (`1.`)** so chat items `1..K` match modal items `1..K` in
        exact 1-to-1 order. `<Option name>` MUST state what happens in plain
        everyday words (e.g., *"Give each copy its own files and add a new
        version on updates"*, *"Point remixes at the sample's files until
        edited"*, *"Resume at entry only, allow free Skip and Back inside"*),
        never an invented compound-noun architectural slogan or CS storage term
        (*"Entry-only resume with permissive step guards"*, *"Mint an
        independent clone and append versions monotonically"*, *"Copy-on-write
        shared blobs"*). No `(Recommended)` tag on the chat list; `###
        Recommendation: Option 1` states it below.
    -   *Ignore line:* `Safe to ignore for now: <2–3 implementation mechanics>.`
        This is where limiter internals, bucket paths, cleanup jobs, version
        counters, retry math, and helper names go instead of the opener or the
        numbered options.
    -   *Recommendation:* `### Recommendation: Option 1` followed by exactly one
        sentence of rationale grounded in a concrete constraint (cognitive load,
        latency bound, storage simplicity, failure resilience, dialog
        footprint).
    -   *Pick recap (Bulleted Markdown List):* `- Pick 1 if <condition>.`,
        strictly one Markdown bullet line per numbered option in list order
        (`len(picks) == len(numbered)`), each naming the concrete scenario or
        priority that makes that option right without repeating abstract nouns
        from `<Option name>`. Always prefix each line with `- ` so CommonMark
        renders every `Pick` line on its own bullet line rather than collapsing
        adjacent lines into a single paragraph. Never add an extra `Pick` line
        for modal-only actions such as `"I need more context, zoom out and give
        examples"`.
    -   *Strict Per-Section Word Caps (Total `<= 165` Words, Hard Ceiling `<
        200` Words):* Enforce tight per-element limits from the headline through
        the final `- Pick K if …` bullet so the turn stays crisp and NEVER
        crosses 200 words:
        -   Headline (`## Round R, Question Q of N: <Topic>` or `#### Finding F
            of N: <Title>`): **`<= 10 words`**.
        -   Unlabeled Opener: **1–2 short sentences (`<= 28 words` total)** +
            `The choice here is <5-9 words>. Here are some options:` (**`<= 14
            words`**).
        -   Numbered Options (`2-3` concise options preferred): **`<= 16 words`
            total per numbered line** (`1. <3-6 word plain name>: <short
            benefit>; <short cost>`).
        -   `Safe to ignore for now:`: **`<= 8 words` total** (`2-3` brief
            terms).
        -   `### Recommendation: Option 1`: **1 short sentence (`<= 18
            words`)**.
        -   Bulleted `- Pick N if …` lines: **`<= 11 words` per bullet**.
    -   *Plain Presentation:* Do not use tables, icons, emoji, glyphs, progress
        bars, blockquote cards, or `[!NOTE]` / `[!TIP]` callouts inside the
        default `## Round R, Question Q of N:` interview turn block.
    -   *Need-More-Context Detour (When `"I need more context, zoom out and give
        examples"` Is Selected or User Writes `"zoom out"` / `"too vague"` /
        `"explain"`):* Make **zero** `view_file`, `code_search`, or
        `grep_search` calls (even if `<memory>` ambient hints are injected) and
        answer immediately from conversation context. **OMIT `**Settled**`,
        `**Now**`, and `**Up next**` completely** on this turn—because zero
        decisions newly settled, re-printing `**Settled**` mid-clarification
        splits the explanation from the question and creates false-settled
        noise. Emit **BOTH** Part 1 markdown AND Part 2 structured
        `ask_question` tool call in the **exact same response**:
        1.  Plain-English workflow zoom-out explaining why this decision arises
            in the overall feature plus **1–2 concrete named domain examples**
            showing how each choice behaves in practice (never blockquote
            `Pros`/`Cons` cards),
        2.  A `---` horizontal rule,
        3.  Directly beneath `---`, the **rewritten** Interview Turn v2 block
            (`<= 165` words total: headline, opener, numbered `<Option name>:
            <benefit>; <cost>` lines with recommended option at `1.`, `Safe to
            ignore for now:` line, one-sentence `### Recommendation: Option 1`,
            and 1:1 bulleted `- Pick N if …` lines) anchored in familiar
            everyday words—never copy-pasting prior vague headlines, openers, or
            option names verbatim, **AND**
        4.  Native structured `ask_question` tool call in that **same turn**
            (never stopping with text alone). Resume rendering `**Settled**` /
            `**Now**` / `**Up next**` on the next turn after the user picks an
            answer.
    -   *Zoom-In View (`"zoom in"` Write-In Only):* Strictly when the user
        explicitly writes in *"zoom in"*, render the full Option Trade-Off cards
        for the same options: one plain blockquote per option (`> **Option N:
        <Name>**`, with ` (Recommended)` after Option 1's title) with `> -
        **Pros:** ...`, `> - **Cons:** ...`, and `> - **Implications:** ...`
        rows (code identifiers are allowed only in `Implications`), `&nbsp;`
        spacers before the first card and after the last, then `###
        Recommendation: Option 1` with 1–3 sentences, PLUS the native
        `ask_question` tool call in that same turn. Never render the cards in
        the default turn or when `"I need more context, zoom out and give
        examples"` is selected.
    -   *Mandatory Two-Part Turn Pairing (Zero Trailing Narration & Zero
        Text-Only Stalls):* Finish your visible markdown response directly on
        the last `- Pick K if …` bullet (or, in the zoom-in view, on the
        recommendation rationale) with zero transitional self-narration (never
        write *"I will now ask..."* or *"Let's call ask_question..."*), and
        immediately invoke `ask_question` as a native structured tool call in
        that exact same turn. NEVER output raw
        `call:default_api:ask_question{...}` text in the markdown stream, NEVER
        emit a bare `ask_question` call without the visible markdown body, and
        NEVER conclude a turn with markdown prose alone when presenting choices,
        re-tees, or trade-offs.
    -   *Modal Parameters (`ask_question` — Direct `<Option name>` Match & 1:1
        Order Lock):*
        -   Populate options `1..K` in the **exact same `1..K` order** using the
            **exact same `<Option name>`** (the plain-English phrase before `:`
            on each numbered chat line `1. <Option name>: <benefit>; <cost>`),
            prefixing Option 1 with `"(Recommended) "` (e.g., `"(Recommended)
            Give each copy its own files and add a new version on updates"`,
            `"Give each copy its own files and replace the old sample right
            away"`, `"Point remixes at the sample's files until edited"`).
            **NEVER** replace `<Option name>` in `ask_question` with the `Pick N
            if …` condition sentences, which causes modal choices to mismatch
            the numbered options shown in chat above.
        -   *Trailing Context Option (`"I need more context, zoom out and give
            examples"`):* Append `"I need more context, zoom out and give
            examples"` as the final choice on substantive Interview Turn v2
            decision questions (architectural, data model, state/routing,
            interaction behavior, brownfield setup scope, and Phase 5b Devil's
            Advocate challenges); selecting it triggers the Need-More-Context
            Detour above. **STRICT COPYWRITING & GATE EXEMPTION:** Whenever the
            options select UI copywriting, quoted banner/empty-state headlines,
            button text, microcopy tone, or visual styling preferences—or on
            empirical QA verification checks, safety confirmations, or
            procedural approvals—pass **ONLY options `1..K`** to `ask_question`
            and **STRICTLY OMIT** `"I need more context, zoom out and give
            examples"`.
    -   *Strict Exemption for Empirical & Procedural Gates:* Do **NOT** generate
        the Interview Turn v2 body, option cards, or `"I need more context, zoom
        out and give examples"` option for:
        1.  **Empirical QA Verification Checkpoints** (`/arm-review` scenario
            checks: *"Did Scenario N meet the expected outcome?"* where choices
            are `Verified`, `Didn't match expectation`, `Skip`).
        2.  **Safety & Environment Confirmations** (Hybrid Smart Gate
            destructive command prompts).
        3.  **Lifecycle & Procedural Approvals** (`spec.md`/`plan.md`
            confirmation gates, ADR multi-select triage checkboxes). For these
            gates, present crisp context followed by direct status or action
            options.
-   **Mid-Interview Context Persistence & Zero File-Read/Search Calls on Option
    Clarifications:** Once an interactive interview is in progress (prior
    conversation turns already contain a `**Settled**` / `**Now**` / `**Up
    next**` progress list or `### Devil's Advocate Analysis`), project context
    (`armature/index.md`, `armature/tracks.md`, `product.md`, `tech-stack.md`)
    is already loaded and `{PROJECT_CONTEXT_DIR}` defaults to `armature`. Never
    call `view_file` to check `armature/index.md`, `armature/product.md`, or
    `armature/tracks.md` during Step 5a, Phase 5b, Phase 5c, or Step 6
    transitions. Furthermore, when the user selects `"I need more context, zoom
    out and give examples"` or replies with a write-in clarification (`"<Option
    name> is too vague, explain"`, `"what does Option 1 mean?"`, or `"zoom
    out"`), recognize that the quoted phrase came from your own prior turn:
    **NEVER** call `view_file`, `code_search`, or `grep_search` (even if
    `<memory>` ambient hints are injected) to look up your own option wording.
    Answer directly from conversation context, **omit `**Settled**` / `**Now**`
    / `**Up next**` completely**, explain why the decision arises in the
    workflow with 1–2 concrete domain examples, output `---`, **rewrite** the
    headline, opener, numbered options (`1..K` matching `ask_question`
    directly), and bulleted `- Pick N if …` lines in plain everyday domain words
    (never copy-pasting the prior turn's wording verbatim), and call
    `ask_question` in that same turn.
-   **Two-Part Turn Contract (Non-Empty Visible Markdown FIRST + Native
    `ask_question` SECOND):** Every interactive interview or gate turn MUST
    contain BOTH (1) non-empty visible markdown text (answering any inline
    `@[Quote]` or write-in clarification questions and rendering the required
    progress list and interview turn, `### Devil's Advocate Analysis`, `### ADR
    Candidate Triage Table`, or `### Convergence Summary`) FIRST, and (2) the
    native `ask_question` tool call SECOND in that same turn. Never emit a bare
    `ask_question` or `write_to_file` call with empty visible markdown text
    (`""`), and never end a turn with a conversational prose question
    (`tools=[]`).
-   **Single-Gate Phase Isolation (`/arm-new-track` Phase 5a → 5b → 5c → Step
    6):** Never collapse multiple interactive gates into a single turn.
    Resolving the final open question in Phase 5a transitions in that turn to
    **Phase 5b Finding 1** (one challenge per turn with the Interview Turn v2
    body: numbered countermeasure options + `### Recommendation: Option N` +
    `Pick N if …` lines + `ask_question`, never a self-answered
    `*Risk:*`/`*Mitigation:*` list). Resolving the final Phase 5b challenge
    transitions in that turn to **Phase 5c** (`### ADR Candidate Triage Table` +
    `ask_question` with `is_multi_select: true` whenever $\ge 1$ candidates
    qualify, or silent bypass to Step 6 visible `### Convergence Summary` +
    `write_to_file` (`spec.md` & `manual_testing.md`) + `ask_question` when 0
    qualify).
-   **Human-Readable Navigation:** Always refer to process steps and documents
    by their human-readable names. Do not expose internal section numbers.

## 3. Artifact Output Convention

Whenever an Armature command produces structured output requiring user review -
clarifying questions, reports, summaries, specs, plans, or confirmation prompts:

1.  **Write as an artifact** using `write_to_file`
2.  **Present via `notify_user`** with `PathsToReview` pointing to the file
3.  **Use appropriate ArtifactType**: `walkthrough` for reports/status,
    `implementation_plan` for specs/plans, `other` for questions/prompts
4.  **Set `BlockedOnUser: true`** when the artifact requires approval before
    proceeding

Artifact filenames follow: `arm_<command>_<context>.md`

## 4. VCS Operations

Armature skills are VCS-agnostic by default. Platform-specific VCS behavior
(Git, Mercurial, Jujutsu) is injected by platform rules (e.g., `platform
rules`). When no platform rule overrides VCS behavior, default to Git:

-   `git status` to check for changes
-   `git add` / `git commit` for commits
-   `git diff` for diffs
-   `git log` for history

**IMPORTANT:** Before creating any commit, ALWAYS check for actual changes
first. Do NOT create empty commits.

## 5. Armature Guardrails

-   **Never modify context files outside the active track** — only update files
    in `{PROJECT_CONTEXT_DIR}/tracks/<active_track_id>/` and
    `{PROJECT_CONTEXT_DIR}/tracks.md` during implementation. **Exceptions:**
    `{PROJECT_CONTEXT_DIR}/adr/*.md`, `{PROJECT_CONTEXT_DIR}/terms.md`,
    `{PROJECT_CONTEXT_DIR}/manual_testing/*.md`,
    `{PROJECT_CONTEXT_DIR}/.api_surface_cache.json`, and source-tree context
    files (`GEMINI.md`, `AGENTS.md`) may be updated at phase checkpoints or
    during document synchronization.
-   **Always confirm before overwriting user-approved specs or plans.**
-   **Ask before destructive operations** — do not delete tracks, revert
    commits, or remove artifacts without explicit user confirmation.
-   **Spec and plan approval gates** — always present specs and plans for
    explicit user approval before proceeding.
-   **Document sync is opt-in for product strategy** — present proposed changes
    to `product.md` and `product-guidelines.md` as diffs for user approval.
-   **Autonomous living documentation & glossary synchronization** — During
    track completion (`/arm-implement` Step 4), merging verified steady-state
    test scenarios from
    `{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md` into
    `{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md` is fully autonomous and
    non-gated. In addition, the agent must proactively scan the final diff for
    newly introduced domain terms, entities, and exported symbols, append their
    definitions to `{PROJECT_CONTEXT_DIR}/terms.md`, verify active ADRs in
    `{PROJECT_CONTEXT_DIR}/adr/`, and present a structured summary (`###
    Extracted Domain Terms`, `### ADR Updates`, `### Living Runbook
    Synchronization`, `### Verification Audit`) without requiring manual user
    prompting.
-   **Ceremony scaling on micro-tasks (Fast-Path Bypass)** — If a task is a
    surgical hotfix, single-line bug fix, or minor attribute toggle (≤5 lines of
    changed code with zero architectural ripple and no schema changes), execute
    the operational fast path: bypass track creation, multi-turn PRDs, specs,
    and interview modals (`ask_question`). Directly inspect the target
    component, propose ONLY the minimal targeted diff with zero extraneous
    refactoring (do not modernize adjacent error comparisons, reformat error
    strings, or rename unrelated variables), and provide the exact test
    verification command in ≤1000 tokens (do not exceed token boundaries).
-   **Recursive Decision-Tree Grill Engine & Devil's Advocate** — During track
    creation (`/arm-new-track` Step 5), the agent MUST open every interview turn
    with a one-line settled sentence (skipped on the first question) and a
    visible grouped progress list (`**Settled**` with short answers, `**Now**`
    for the active question, `**Up next**` for queued questions and unexplored
    rounds), followed by `---` and a `## Round R, Question Q of N: <Topic>`
    headline. The interview operates in two strictly sequenced phases:
    1.  *Phase 5a (Round and Question Traversal & Ambiguity Elicitation)*:
        Selecting an architectural direction for a round does NOT close the
        round; it actively spawns 1–2 high-value Tier 1 operational follow-up
        questions derived from that specific choice. Probing depth is strictly
        bounded to Depth <= 2 (Round -> Question). Question answers are terminal
        (Settled) and MUST NOT spawn further nested questions (Tier 2 styling,
        micro-copy, and internal helpers are pruned and deferred to `plan.md`).
        Future rounds MUST remain unexpanded stubs under `**Up next**` until
        probed (Lazy Question Materialization); listing questions under
        unconfirmed rounds is strictly forbidden. Every spawned follow-up
        question MUST state which confirmed answer spawned it, in the settled
        line or the opener paragraph (Answer-Anchored Provenance). Furthermore,
        the agent is strictly forbidden from asserting declarative technical
        designs, button configurations, countdown cancel behaviors, or state
        transitions in markdown for topics unconfirmed by the user via
        `ask_question`. Every turn presenting choices MUST pair markdown
        analysis and the progress list with an immediate native `ask_question`
        tool call in the exact same turn; ending a turn with text alone when
        choices are presented or emitting bare `ask_question` without markdown
        text are both strictly forbidden.
    2.  *Phase 5b (Devil's Advocate Analysis — Sequential Single-Finding
        Execution)*: When every round and question is Settled, the agent MUST
        NOT immediately converge and MUST NOT dump all emergent findings into a
        single compound prompt. It MUST output `### Devil's Advocate Analysis:
        Stress-Testing Confirmed Decisions` presenting each emergent
        cross-cutting contradiction, operational hazard, and maintainability
        debt finding **one-by-one**. For each finding, the agent MUST state the
        specific risk in the opener, offer numbered countermeasure options with
        `### Recommendation: Option N` and `Pick N if …` lines (Interview Turn
        v2), and pause execution for human decision via `ask_question`
        individually before presenting subsequent findings. Only after all
        devil's advocate findings have been evaluated individually does the
        agent present the final convergence gate before proceeding to Phase 5c.
    3.  *Phase 5c (ADR Candidate Triage Gate — Dual-Stage Lifecycle)*:
        Immediately after Phase 5b Devil's Advocate concludes and before
        materializing `spec.md`, the agent MUST audit all settled decisions
        (listed under `**Settled**`) against the **3-Pillar Invariant
        Taxonomy**:
        -   *Pillar 1 (Cross-Cutting Invariant):* Establishes a convention,
            contract, or state invariant that constrains future tracks or
            touches multiple components (e.g., optimistic UI rollback rules,
            error-envelope schemas).
        -   *Pillar 2 (Architecture / Dependency Binding):* Binds the repository
            to a storage engine, transport protocol, or third-party library that
            would be costly to rip out later (e.g., SQLite WAL, WebSocket vs.
            SSE).
        -   *Pillar 3 (Negative Constraint / Discarded Alternative):* Rejects an
            obvious, standard pattern due to a subtle project gotcha or race
            condition (e.g., forbidding `sessionStorage` because it does not
            sync across tabs).
        -   *Silent Zero-Candidate Bypass:* If zero settled decisions meet the
            3-Pillar Taxonomy (i.e. all decisions are localized UI layouts,
            styling, route slugs, or chore configs), the agent MUST silently
            transition directly to Step 6 Spec Confirmation without generating
            an extra modal prompt or noise.
        -   *Interactive Triage Gate:* If one or more decisions qualify, the
            agent MUST output an `### ADR Candidate Triage Table` mapping each
            candidate decision to its qualification pillar, proposed title, and
            rationale. The agent halts execution with a multi-select
            `ask_question` allowing the user to confirm which ADRs to
            materialize. For each confirmed ADR, the agent drafts
            `{PROJECT_CONTEXT_DIR}/adr/NNNN-slug.md` in standard MADR format.
-   **Proto schema evolution & GraphQL federation probing** — During Step 5
    Recursive Decision-Tree Traversal (exploring dependent failure modes,
    boundary edge cases, and adversarial challenges) on protocol, GraphQL
    federation, or protobuf migrations, explicitly analyze and challenge schema
    directives (`@key`, `@shareable`, `@provides`), field deprecation paths,
    gateway circular dependencies, and service downtime mitigation, as well as
    proto3 default zero-values vs unset fields in partial updates, wire-format
    breaks, and FieldMask requirements before generating plans.
-   **3-Part Fixture Triad & Additive Manual Testing Verification** — Manual
    testing runbooks are strictly additive to automated unit and integration
    tests. In phase checkpoints, track closeouts, and review workflows, the
    agent must audit both automated CI test passes and reproducible manual
    fixture runbooks concurrently. Whenever database migrations or environment
    state changes are involved, the runbook must explicitly document all three
    commands in sequence: $$\text{Migration Command} \longrightarrow \text{Seed
    / Fixture Setup} \longrightarrow \text{Teardown / Reset Script}$$
-   **Documentation-only fixture policy & Hybrid Smart Gate** — Manual testing
    runbooks must specify exact setup, SQL mutation, and reset commands. During
    autonomous phase checkpoints (`/arm-implement`), the agent must NEVER
    execute mutative database, environment reset, or teardown commands
    autonomously (documentation-only policy). However, during user-authorized
    interactive manual testing sessions (`/arm-review`), the agent operates
    under the **Hybrid Smart Gate**: standard, non-destructive fixture commands
    (inserting test records, generating auth tokens, starting local servers,
    exporting test environment variables) execute automatically and stream their
    status, while potentially destructive commands (flagged by keywords in
    commands or script names/arguments: `DROP`, `DELETE`, `TRUNCATE`, `rm -rf`,
    `reset`, `clean`, `wipe`, `reseed`, `kill`) MUST prompt the user with the
    exact command for explicit confirmation via `ask_question` before running.
-   **Contiguous Scenario Numbering (Zero Gaps on Struck Scenarios)** — Whenever
    a manual testing scenario is struck (`[-]`) or removed during track
    execution or `/arm-review` (e.g., due to an ADR or architectural change
    invalidating the test premise), completely remove the struck scenario from
    the final commit/PR description's `Tested:` section and living manual
    testing runbooks, and renumber all remaining scenarios sequentially
    (`Scenario 1, Scenario 2, Scenario 3...`) with zero gaps.
-   **Interactive Manual Testing Protocol & Living Runbook Sync** — When guided
    manual testing is selected during `/arm-review`, the agent executes the
    scenarios documented in
    `{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md` sequentially.
    For each scenario, the agent prepares the environment under the Hybrid Smart
    Gate and presents a structured walkthrough in chat using the canonical
    **6-Part Scenario Format**:
    1.  `#### Scenario <ID>: <Title> — <Synopsis>` followed immediately by a
        succinct 1–2 sentence verification synopsis paragraph explaining what
        behavior or failure mode is under test.
    2.  `##### Prerequisites` providing exact dev-server startup commands (e.g.,
        `./run.sh`, `npm run dev`) inside a copy-pastable `bash` code block,
        instructing the user to ensure the service stack is running.
    3.  `##### Target URL` presenting complete, clickable `localhost` URLs
        (`http://localhost:<PORT>/<path>` or `https://localhost:<PORT>/<path>`).
        **Strict Localhost-Only Invariant**: Never output bare partial routes or
        remote workstation hostnames (`<REMOTE_HOST>.example.com`).
    4.  `##### Step-by-Step Setup` (or `##### Simulation Setup`) providing
        numbered setup instructions. **Self-Contained Copy-Pasteable Snippet
        Invariant**: Whenever setup requires a console snippet, mock script, or
        CLI payload, reproduce the complete copy-pastable code block directly
        inline—never instruct the user to *"paste the snippet you loaded
        earlier"* or hunt through clipboard history across scenarios.
    5.  `##### Action Steps` specifying numbered, imperative UI or CLI actions.
    6.  `##### Expected Observations` (strictly titled `Expected Observations`,
        never `"Expected Observables"` to prevent confusion with RxJS
        `Observable` streams), categorized by domain (e.g., `**UI Behavior:**`,
        `**DevTools Console Log:**`). The agent validates results via
        `ask_question`. If a discrepancy occurs, the agent offers in-flight
        triage (fix now vs. log and continue). If an in-flight hotfix modifies
        code, the agent applies **Cascade Invalidation Tracking**, flagging
        previously verified scenarios for quick re-checking. A mandatory
        **Post-Testing Reconciliation Gate** blocks review completion until all
        open issues are resolved or triaged. Upon completion, empirical outcomes
        are logged in `review.md` (`## Interactive Verification Log`) and
        working setup commands are synchronized back into `manual_testing.md`.
-   **Change-Aware Verification Scoping & Micro-Verification Protocol** — To
    prevent verification fatigue on purely presentational changes, manual
    verification dynamically scales using a **Two-Stage Hybrid AST + Diff
    Classifier**:
    1.  *Stage 1: Provisional Intent Scoping (`/arm-new-track` Step 5a & Step
        6)*: Evaluates the confirmed specification and target file list. If
        changes are strictly presentational/visual, classifies the track as
        **Visual-Only (`Micro-Verification`)** and generates a concise
        `Micro-Verification Plan` in `tracks/<track_id>/manual_testing.md` using
        the Tier 2 template without database seed boilerplate.
    2.  *Stage 2: Empirical VCS Diff Re-Verification (`/arm-implement` Step 3.6
        & `/arm-review` Step 2.1/2.5)*: Inspects actual VCS diffs (`git diff`).
        Diffs restricted to template/style files (`.html`, `.css`, `.scss`,
        `.sass`, `.less`, `.svg`) or component files (`.ts`, `.tsx`, `.jsx`,
        `.vue`) that modify only JSX/HTML structure, CSS class bindings, static
        text copy, or inline styles qualify as visual-only.
    3.  *Orphaned Dead-Code Cleanup Exemption*: Deleting or renaming an unused
        local click handler (e.g., `onCardClick()`, `handleCardClick()`), local
        display helper function, or unused import/prop directly attached to a
        removed or restyled UI element explicitly qualifies as visual-only.
        Conversely, modifying state machines, reactive stores/signals, router
        navigation guards (`canActivate`), conditional auth/role rendering gates
        (`*ngIf="user.isAdmin"`, `@if (hasPermission)`), or RPC/API service
        calls strictly disqualifies the change and escalates to full **3-Part
        Fixture Triad** runbooks.
    4.  *Zero-Latency Documentation-Only Card Contract (`┌─ [Micro-Verification
        Plan] ──┐`)*: When reviewing visual-only changes in `/arm-review`, the
        agent skips all database seeding, SQL migrations, API token minting, and
        shell dev-server probes, rendering the canonical ASCII card directly in
        chat:
        -   `Step 1: Run local server (<cmd>)` — appends a one-line route-guard
            session hint (`(requires active logged-in session)`) if protected by
            an auth guard or parent data container.
        -   `Step 2: Navigate to http://localhost:<PORT>/<path>` — strictly uses
            clickable `http://localhost:<PORT>/<path>` (or
            `https://localhost:<PORT>/<path>`) URL formatting, never bare
            partial routes or remote workstation hostnames
            (`<REMOTE_HOST>.example.internal`).
        -   `Verify: <visual assertion>` — anchors assertions on visible text
            labels or semantic ARIA roles rather than brittle CSS class names.
    5.  *Multi-Route Consolidation*: Multi-route visual checks sharing a common
        dev-server/session setup state consolidate into a single
        Micro-Verification card and a single `ask_question` turn; sequential
        walkthrough turns are used only when distinct setup states are required.
    6.  *Inline Modal Escape Hatch*: Immediately following the card, the agent
        calls `ask_question` with:
        1.  `"(Recommended) Verified: <concise expected visual outcome>"`
        2.  `"Run full domain runbook instead (execute database seed &
            multi-role scenarios)"`
        3.  `"Didn't match expectation (I will describe what occurred)"`
    7.  *Surgical Assertion Delta Sync, Whole-Scenario Pruning & Cold-Start
        Stamping (`/arm-implement` Step 4.5 & `/arm-drift`)*: When synchronizing
        a visual-only track into persistent living runbooks
        (`{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md`), the agent updates
        modified visual assertions in-place (anchored on visible text or ARIA
        roles) while strictly preserving existing database seed and persona
        setup blocks (**Surgical Assertion Delta Sync**). If a visual change
        completely removes the primary UI entry point of an existing scenario,
        the agent cleanly prunes the entire obsolete scenario block including
        its coupled setup step (**Whole-Scenario Pruning**) and logs the pruned
        scenario ID. If `<domain>.md` does not exist yet, the agent initializes
        it with the verified `localhost` visual baseline and stamps `## 2.
        Fixture Provisioning & Reset Tooling` with `> [!NOTE] Stateful 3-Part
        Fixture Triad deferred (initial track was visual-only).` (**Cold-Start
        Deferred Fixture Stamping**). `/arm-drift` recognizes
        `[Micro-Verification Plan]` and `Stateful 3-Part Fixture Triad deferred`
        markers, exempting them from missing 3-Part Fixture Triad errors while
        cross-checking VCS diffs to flag a `[WARNING]` if backend/state code was
        modified under a visual-only tag.
-   **Safe Key and Secret Rotation** — For credentials, keys, or JWT rotations,
    strictly refuse immediate deletion of legacy keys to prevent service or
    session disruption. Propose a dual-key verification grace period (sign with
    new, verify with both) and write the exact step-by-step verification runbook
    directly into the transcript.
-   **Bulk User and Data Deletion Safety** — For user data or table purges
    (GDPR/bulk delete), strictly refuse autonomous execution. Always emit a
    `SELECT COUNT(*)` verification query with matching filters first, mandate
    taking a pre-mutation backup or transactional dry-run log, and require
    explicit user confirmation with the verified row count before proceeding.
-   **Execution-Ready Specification & Plan Grounding Standard (`ADR 0016` —
    Sufficient Detail for a Smaller Model Without Writing Code)** — During
    `/arm-new-track`, Step 5 (the human decision interview) intentionally bans
    code identifiers and backend systems jargon so the engineer can reason about
    product and architectural trade-offs without cognitive overload. Once all
    rounds settle, **Step 6 (`spec.md`) and Step 7 (`plan.md`) change
    audience**: their primary consumer is a downstream execution worker
    (frequently a smaller or faster model operating in an isolated worktree or
    `worker` subagent with zero access to the planning conversation). By default
    on every track, `spec.md` and `plan.md` must satisfy the **6-Point
    Execution-Ready Grounding Standard**:
    1.  *Exact Target File Paths, Non-Obvious Imports & Build/Package
        Dependencies*: Every requirement in `spec.md` and every task in
        `plan.md` names exact repository-relative source, schema, config, test,
        and build/package manifest paths (`BUILD`, `package.json`, `Cargo.toml`,
        `go.mod`), exact non-obvious import paths and target labels, and notes
        build-time generated files vs. checked-in files.
    2.  *Verified Symbol Names, 1-Line Method Signatures & Exact Arity*: Uses
        verified proto/schema/interface names and setter/getter methods (never
        invented wrapper types), full 1-line method signatures with parameter
        names, types, return types, and exact argument count/arity, and includes
        explicit prerequisite sub-tasks in `plan.md` to expose `private`
        methods, getters, setters, or callbacks before callers invoke them.
    3.  *Explicit Cross-Layer Field Bijections, Defaults & Server Validation
        Preconditions*: Documents complete bidirectional `UI/Client State <->
        Wire/Backend/Storage State` field mappings, default values for
        non-toggled fields, boolean/sign inversions, and server-side validation
        invariants (e.g., unit-length normal vector `|n| = 1.0`, numeric bounds,
        required `FieldMask` paths).
    4.  *Self-Contained State Machines, Timers & Echo-Suppression Guards*:
        Inlines exact signal/variable names, transition rules, debounce/guard
        timer constants in `ms`, reload/hydration echo-suppression flags
        (`isHydrating... = true` to prevent initial hydration from firing
        outbound write RPCs), and DOM/ARIA/CSS tokens whenever referencing a UI
        or sibling-app pattern so the worker never needs to inspect another
        repository.
    5.  *Test-Suite Blast Radius & Per-Phase Verification Commands*: Identifies
        unit/integration tests affected by shared config/flag/schema switches,
        specifies required test-bundle or fixture overrides so existing tests
        stay green, and includes exact copy-pastable test commands in every task
        and Phase Completion checkpoint.
    6.  *Strict "Blueprint, Not Implementation Code" Boundary*: Expresses all
        contracts via inline backtick signatures, bulleted field bijections, and
        declarative prose/tables—strictly forbidding multi-line fenced
        implementation code blocks or function bodies inside `spec.md` or
        `plan.md`.
-   **Fixpoint and Drift Auditing (Two-Tier Classification — Auto-Update &
    Notify by Default on Mechanical Drift)** — A feature or track achieves
    completion only when the Fixpoint Auditor reports a "Fixpoint Reached"
    state. At pre-execution context checks, `/arm-status` checks, phase
    checkpoints, track closeout, and `/arm-drift` runs, the agent classifies
    drift into two tiers:
    1.  *Tier A — Mechanical & Deterministic Documentation Drift (Auto-Update &
        Notify by Default — Zero Permission Prompt)*: Stale track statuses in
        `tracks.md` / `metadata.json` (`[~]` $\to$ `[x] Completed` when 100% of
        `plan.md` tasks are `[x]` and the commit/CL is on `HEAD`), multi-line
        `: :` wrapped Markdown tables in `tracks.md` / `index.md` missing
        `<!-- mdformat off(prevent table wrapping) -->` /
        `<!-- disableFinding(LINE_OVER_80) -->`, missing `tracks.md` /
        `index.md` links, additive `.api_surface_cache.json` and `terms.md`
        updates, and installer/packaging manifest arrays (`install.sh`,
        `install.bat`, `plugin.json`, `README.md`). Unless `--check` or
        `--report-only` was passed, the agent MUST automatically apply all Tier
        A fixes in-place via `replace_file_content` / `write_to_file` in the
        exact same turn, update `{ARTIFACT_DIR}/arm_status.md` in lockstep if
        present, and notify the user in chat (`✅ Fixpoint Reached (N mechanical
        drift issue(s) auto-updated)` with a bulleted list of applied updates).
    2.  *Tier B — Semantic / Architectural Contradictions, Breaking Removals &
        Fence Decisions (Interactive Disambiguation)*: Source code violating an
        approved `ADR` or `spec.md` (`CB2`), breaking public API symbol removals
        compared against `{PROJECT_CONTEXT_DIR}/.api_surface_cache.json`
        (`[ERROR] Breaking API Surface Change` requiring a semantic versioning
        major bump recommendation), `[WARNING] Diff-to-Tag Mismatch` (`ADR
        0010`), unauthorized edits inside `<deprecated_path>` (`[BLOCKING]`,
        `CB1`), or deleted legacy fence directories (`[DRIFT] Stale Legacy
        Fence`, `VAL_LF_04`). Never silently auto-overwrite approved `spec.md`
        or `adr/*.md` files; auto-apply any co-occurring Tier A fixes first,
        then surface the Tier B finding and prompt via `ask_question`.
-   **Iterative Multi-Expert Review & Closed-Loop Repair (`ADR 0015`)** — In
    `/arm-review` (`Steps 2.3–2.4`, up to `MAX_ITERATIONS = 3`, or `1` read-only
    pass with `--report-only`) and `/arm-implement` (`Step 3.6` Pre-Closeout
    Gate, up to `MAX_ITERATIONS = 2` before `Step 4: Document Synchronization`
    on behavioral tracks; skipped on $\le 5$-line micro-tasks and visual-only
    `[Micro-Verification Plan]` tracks), execute an iterative **Review $\to$
    Deduplicate $\to$ Repair $\to$ Re-Verify** loop:
    1.  *3-Tier Runtime-Polymorphic Review Panel*:
        -   **Tier 1 (Host Review-Loop Adapter):** Run the active platform
            rule's adapter (`start_new_loop=true` on Pass 1, `false` on Pass
            $>1$; count comments strictly via top-level `len(comments)`) in
            parallel with `spec_and_adr_verifier` (`include_intent: true`).
        -   **Tier 2 (Multi-Agent Panel via Read-Only Subagents):**
            Fan out read-only (`workspace: "inherit"`) `spec_and_adr_verifier`
            (`include_intent: true`), `code_taste_style_verifier`
            (`include_intent: false` — blinded to author rationale to prevent
            confirmation bias), `correctness_security_verifier`
            (`include_intent: false` — blinded to author intent), and
            `deterministic_linter_runner`.
        -   **Tier 3 (Single-Agent Sequential Pass):** Evaluate the three
            verifier rubrics and deterministic linters sequentially.
    2.  *2D Ordering (`P0–P3` $\times$ `S0–S3`) & Spec/ADR Precedence*: Sort
        deduplicated findings by Priority (`P0` Architectural/Contract $\to$
        `P1` Functional $\to$ `P2` Local $\to$ `P3` Polish) and Severity (`S0`
        Blocker $\to$ `S1` Critical $\to$ `S2` Improvement $\to$ `S3` Nit).
        Approved `spec.md` and `adr/*.md` invariants automatically override
        conflicting blinded `S2`/`S3` style suggestions during deduplication
        (`status: skipped_spec_adr_precedence`).
    3.  *Four Repair Safety Circuit Breakers & Anti-Oscillation Ledger*:
        -   **CB1 (`blocked_by_legacy_fence`):** Never auto-edit files in
            `<deprecated_path>`; redirect to `<modern_replacement>` or log as
            unapplied.
        -   **CB2 (`deferred_spec_conflict`):** Never auto-mutate `spec.md`,
            `plan.md`, or `adr/*.md` during repair.
        -   **CB3 (`reverted_test_regression`):** Re-run unit tests after each
            pass; immediately revert any repair that breaks a test, lock it in
            the **Anti-Oscillation Ledger**, and never re-attempt it in later
            passes.
        -   **CB4 (Surgical Scope & Final-Pass Application Guarantee):** Scope
            `S2`/`S3` edits strictly to modified diff lines, and always apply
            valid, test-passing fixes found on `iteration == MAX_ITERATIONS`.
    4.  *Pre-Manual-Testing Unapplied Blocker Gate (`/arm-review` Step 2.4 $\to$
        2.5)*: Pause via `ask_question` before Step 2.5 only when $\ge 1$
        unapplied `S0`/`S1` findings remain; when `0` unapplied `S0`/`S1`
        blockers remain, proceed directly into Step 2.5.
-   **Legacy-Boundary Context Fencing, Intent-Aware Override Gates & Subagent
    Propagation** — Whenever repository-wide fences
    (`{PROJECT_CONTEXT_DIR}/tech-stack.md` under `## Legacy & Deprecated
    Boundaries`) or track-scoped fences (`metadata.json` under `legacy_fences`)
    are active:

    -   *Session Banner Indicator (Adaptive Verbosity)*: At the top of your
        response whenever any legacy fence is active in context, display:

        -   **Once per session (Turn 1 — Full Callout Only):**

            ```markdown
            > [!NOTE]
            > **Working in `<active_replacement_basename>/`:**
            > * `<active_replacement_full_path>`
            >
            > **Skipping <N> deprecated folder(s):**
            > * `<deprecated_path_1>`
            > * `<deprecated_path_2>`
            >
            > _Code boundaries defined in `<source_config_file>`. Want to add/edit an ignored folder? Just ask!_
            ```
        -   **Strict Silence on Subsequent Turns (`Turn 2+`) & Intermediate Tool
            Steps:** Do **NOT** repeat the boundary callout or emit any `> 🛡️
            **Deprecated code boundary active:** ...` reminder on `Turn 2+`
            (such as when `[Prior Session History]` is present) or across
            intermediate tool-calling steps within a turn. Stay completely
            silent about code boundaries after Turn 1 unless a specific boundary
            event fires (`[Legacy Dependency Read: <path>]`, Zero-Match
            Fallback, or Intent-Aware Read/Write Override Gate).
    -   *Query-Time Negative Search Filtering (RE2 Anchored)*: When invoking
        `grep_search`, you MUST append anchored RE2 negative file filters
        (`-f:^<deprecated_path>` or `-f:^<deprecated_path>`) to `Query`. When
        invoking `grep_search`, populate `Excludes:
        ["**/<deprecated_path>/**"]`. Never call `view_file` on any file inside
        `<deprecated_path>` unless authorized by Direct Import Read Exemption or
        an explicit user session unlock. Direct analysis and search exclusively
        to `<modern_replacement>`.
    -   *Zero-Match Fallback Protocol*: If a search in active modern code
        (`<modern_replacement>`) returns `0 matches`, perform a secondary
        path-only check inside `<deprecated_path>`. If matches exist in the
        fenced directory, DO NOT call `view_file` on the legacy file. Instead,
        explicitly state in markdown that `0 matches were found in active modern
        code (<modern_replacement>), but matches exist in legacy-fenced
        <deprecated_path>`, and invoke `ask_question` with prompt `"Are you sure
        you want to proceed?"` and options:

        1.  `"(Recommended) Redirect analysis to modern replacement
            (<modern_replacement>)"`
        2.  `"Yes, unlock READ access to <deprecated_path> for the remainder of
            this chat session"`
        3.  `"No, skip legacy files"`
    -   *Direct Cross-Boundary Import Read Exemption*: If an active modern file
        explicitly imports (`import`, `require`, `#include`) a file located
        inside a fenced `<deprecated_path>`, do NOT halt with an `ask_question`
        popup. Instead, call `view_file` on that imported legacy file in
        **Read-Only Reference Mode**, output the inline badge `[Legacy
        Dependency Read: <path>]` in your chat response, and strictly forbid
        calling `replace_file_content` or `write_to_file` on that legacy file.
    -   *Intent-Aware Override Gates (READ vs. WRITE Escalation)*: Approving
        Option 2 in the Read Warning Gate unlocks session `READ` access only.
        Session `READ` access NEVER authorizes write mutations. If the user
        requests modifying, updating, or fixing a file inside
        `<deprecated_path>` (or if you attempt `replace_file_content` /
        `write_to_file` on a fenced file)—even when session `READ` access was
        previously approved—you MUST NOT call `replace_file_content` or
        `write_to_file`. Halt immediately and invoke `ask_question`:

        -   Prompt: `"WARNING: Modifying files in legacy-fenced directory
            (<deprecated_path>). Are you sure you want to proceed?"`
        -   Options:
            1.  `"(Recommended) Apply changes to modern replacement
                (<modern_replacement>) instead"`
            2.  `"Yes, authorize WRITE modifications to <deprecated_path> for
                this task"`
            3.  `"Cancel modification"`
    -   *Background Subagent Propagation (`invoke_subagent`)*: When delegating
        work via `invoke_subagent` (`worker` or `explorer`), you MUST include an
        explicit `[ACTIVE_LEGACY_FENCES & SESSION_UNLOCKS]` block inside the
        subagent `Prompt` specifying fenced paths, session read unlocks, and the
        strict rule: `"NEVER call ask_question from a background worker. Never
        modify fenced files (<deprecated_path>). If unapproved fence access or
        write access is required, halt immediately and return a structured
        escalation request to the parent orchestrator."` Concurrently call
        `schedule(DurationSeconds=90, TimerCondition="<subagent_id>",
        Prompt="Check subagent progress and post a 20-block progress bar update
        in main chat.")` (or `TimerCondition="any"` for parallel subagents) and
        yield the turn with a chat confirmation (preceded by ``
        `▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░ XX%` (Task X of Y)``) naming the dispatched
        subagent and active legacy fence status.
    -   *Reactive Self-Healing Steering Hook*: When a user steers you away from
        a deprecated/legacy path mid-session (e.g., *"Wait—`old_portal/` is
        deprecated, check `new_portal/` instead!"*), you MUST: (1) Immediately
        pivot to the modern replacement (`new_portal/`) via `view_file` or
        search and answer the user's technical question FIRST in the same turn
        without stalling; and (2) At the very end of the turn, invoke
        `ask_question` offering to persist the newly discovered boundary
        (`<deprecated_path> -> <modern_replacement>`) with options:

        1.  `"(Recommended) Save as Repository-Wide Legacy Fence in
            armature/tech-stack.md"`
        2.  `"Save as Track-Only Legacy Fence in metadata.json"`
        3.  `"Keep for this chat session only (do not write to files)"`
    -   *Cumulative Branch Diff Firewall & Decommissioning Exemptions
        (`/arm-drift` & `/arm-review`)*: Audit cumulative branch changes against
        the base revision (`git diff main...HEAD`). Flag any added (`A`) or
        modified (`M` with $>0$ added lines) file inside an active fenced path
        (without `fence_overrides`) as a **`[BLOCKING] Legacy Fence
        Violation`**, directing remediation to `<modern_replacement>`.
        Whole-file deletions (`status D` in Git) and pure line removals (`0`
        added lines / dead-code deletion) inside fenced directories are
        **automatically exempt** from violations. If a fenced `Deprecated Path`
        no longer exists on disk (`[ ! -d "<deprecated_path>" ]`), flag
        **`[DRIFT] Stale Legacy Fence`** (preserving active fences that still
        exist) and invoke `ask_question` offering 1-click auto-pruning from
        `armature/tech-stack.md`.

## 6. ADR & Glossary Preflight Interceptor

Full protocol in `armature_adr_preflight.md` (loaded on demand by skills).
Triggers when any Armature skill runs against a brownfield project with no
existing ADR files — sweeps docs for undocumented trade-offs and offers to
formalize them before proceeding.

## 7. Project Root & Context Directory Resolution (Transparent Dual-Discovery)

Before operating on any Armature files, resolve `{PROJECT_ROOT}` and
`{PROJECT_CONTEXT_DIR}` using this tiered heuristic:

1.  **Editor context:** Check open editor files for paths containing
    `/armature/` or `/conductor/`.
    -   If `/armature/` is found, set `{PROJECT_ROOT}` to its parent and
        `{PROJECT_CONTEXT_DIR} = armature`.
    -   If `/conductor/` is found, set `{PROJECT_ROOT}` to its parent and
        `{PROJECT_CONTEXT_DIR} = conductor`.
2.  **Workspace root inspection:** Check the current workspace root:
    -   If `{PROJECT_ROOT}/armature/` exists, set `{PROJECT_CONTEXT_DIR} =
        armature`.
    -   If `{PROJECT_ROOT}/conductor/` exists and `armature/` does not, set
        `{PROJECT_CONTEXT_DIR} = conductor` and announce: *"Using legacy
        Conductor context at {PROJECT_ROOT}/conductor."*
    -   If both exist, `{PROJECT_ROOT}/armature/` takes precedence.
3.  **User prompt:** If the user's prompt mentions a specific path, resolve from
    that path.
4.  **Confidence gate:**
    -   If exactly ONE candidate is found, use it and announce: *"Using Armature
        context at {PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}."*
    -   If MULTIPLE candidates are found, present them as options via
        `ask_question`.
    -   If NO candidate is found:
        -   For `/arm-setup`: Default to `{PROJECT_ROOT}/armature/`.
        -   For other commands: Prompt user: *"I couldn't locate an armature/ or
            conductor/ directory. Please specify the project root path or run
            /arm-setup."*

Once resolved, `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` persist for the
duration of the session. Sub-skills reference them directly.

## 8. Minimum Viable Project Files

The following files constitute a valid Armature project. All Armature commands
(except `/arm-setup`) MUST verify these exist before proceeding:

-   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/product.md`
-   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tech-stack.md`
-   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/workflow.md`
-   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md`

Individual skills may require additional files (e.g., `/arm-review` requires
`product-guidelines.md`), but the base set above is the minimum gate. If any are
missing, halt execution with: *"Armature context is incomplete. Please run
`/arm-setup` first."*

## 9. CDD Protocols (Drift Scan, ADR Capture, Per-Directory Context)

Full protocols in `armature_cdd_protocols.md` (loaded on demand by skills).
Covers:

-   **§9 Pre-Execution Drift Scan**: Cross-reference uncommitted changes against
    ADR scopes and local rules; flag contradictions before the skill proceeds.
-   **§10 ADR Capture Protocol**: Triggers and interaction flow for capturing
    unwritten architectural decisions and behavioral contracts in
    `{PROJECT_CONTEXT_DIR}/adr/`.
-   **§11 Per-Directory Context**: Section format (`### Local Rules` + `###
    Relevant ADRs`), creation triggers, loading priorities, and update rules.
