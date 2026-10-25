---
name: arm-review
description: Review completed work against specifications, guidelines, and quality gates, or run guided interactive manual testing across documented scenarios. Use when asked to review a track, test scenarios interactively, run acceptance criteria, or run /arm-review.
persona: Armature Reviewer
---

# /arm-review — Review Completed Work & Interactive Testing

**Purpose:** Review completed work against specifications and guidelines to
ensure code quality, correctness, and adherence to project standards, or guide
the developer through automated interactive manual testing across scenarios.

## Protocol

### 1. Initialization

1.  **Context Resolution & Setup Check:**
    -   Resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (armature or conductor) per `armature_protocol.md` §7.
    -   Verify that core files exist: `tracks.md`, `product.md`, `tech-stack.md`, `workflow.md`, `product-guidelines.md`.
    -   If any are missing, halt execution and inform the user that Armature is not fully initialized.

### 2. Execution Phase

#### 2.1 Scope, Empirical Diff Classification & Review Mode Identification

1.  Check for user-provided arguments describing what to review and mode flags:
    -   `--both` or `--comprehensive`: Run Full Review (Iterative Multi-Expert
        Review-and-Repair Loop + Guided Manual Testing).
    -   `--manual` or `--interactive`: Run Guided Manual Testing only.
    -   `--static`: Run Iterative Multi-Expert Review-and-Repair Loop (Code
        Audit) only.
    -   `--loop`: Explicitly enable the Multi-Expert Review-and-Repair Loop (up
        to `MAX_ITERATIONS = 3`; enabled by default whenever Code Audit runs).
    -   `--report-only`: Run a single-pass read-only Code Audit
        (`MAX_ITERATIONS = 1`) with zero automatic code mutations, writing all
        findings directly to `review.md`.
2.  **Auto-detect Track:** Read `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md`
    and look for an in-progress track (`[~]`).
3.  If no track is specified or found, prompt the user for the track name.
4.  **Stage 2 Empirical VCS Diff Classification (ADR 0009):** Before executing
    review or manual testing, inspect the actual VCS diff (`git status` /
    `git diff`) using the **Hybrid AST + Diff Classifier**:
    -   **Visual-Only Qualification (`[Micro-Verification Plan]`)**:
        -   Changes restricted to template/style files (`.html`, `.css`,
            `.scss`, `.sass`, `.less`, `.svg`) or component files (`.ts`,
            `.tsx`, `.jsx`, `.vue`) modifying only JSX/HTML structure, CSS class
            bindings, static text copy, or inline styles.
        -   **Orphaned Dead-Code Cleanup Exemption**: Deleting or renaming
            unused local event handlers (e.g., `onCardClick()`,
            `handleCardClick()`), display helper functions, or unused
            imports/props directly attached to a removed or restyled visual UI
            element explicitly qualifies as visual-only.
    -   **Stateful / Full Runbook Disqualification Triggers (Strict
        Escalation)**:
        -   Any modification to state machines, reactive stores, signals, or
            data-fetching hooks.
        -   Any modification to router navigation guards (`canActivate`),
            authentication checks, or role/permission conditional rendering
            gates (`*ngIf="user.isAdmin"`, `*ngIf="user.role ===
            'SUPER_ADMIN'"`, `@if (hasPermission)`).
        -   Any modification to RPC/API service callers (e.g., `await
            api.deleteAccount()`), backend handlers, Protobuf definitions, or
            database schemas/migrations.
        -   *Adversarial Trap Guardrail*: If a template or component diff alters
            an auth/role gate or invokes an RPC mutation, you MUST strictly
            disqualify it from Micro-Verification, explain why multi-persona or
            stateful verification is required, and enforce the full **3-Part
            Fixture Triad** runbook.
5.  **Gray-Zone Prototype vs. Live-Server Disambiguation Gate (Preempts Review
    Mode Gate):** Before presenting the generic Review Mode Gate, check whether
    the user's prompt mixes verifying implemented track code with exploring
    alternative UI layouts or asks to spin up a standalone/mock HTML page:
    -   **Strict Refusal of Simulated Review Harnesses & In-Repo Prototype
        Routes:** Explicitly state in visible markdown that post-implementation
        `/arm-review` verification and review videos NEVER use simulated
        standalone HTML harnesses (`file://` or `data:`), and design
        explorations NEVER add temporary `?variant=` routes inside the
        application repository.
    -   **Explain Both Clean Paths & Disambiguate via `ask_question`:** Clearly
        explain both valid workflows in visible markdown — **(1) Live-Server
        Track Verification:** launch the project's canonical runner (e.g.,
        `./scripts/run.sh` / `./run.sh` on `http://localhost:<PORT>/...`) in
        headless Chrome / Playwright to review and record the implemented track,
        or **(2) Standalone Sandbox Exploration:** build an isolated prototype
        in `<ArtifactDir>/scratch/` (or a local static preview server) to
        compare alternative layouts — and **immediately invoke `ask_question`**
        (in place of the generic Review Mode Gate) so the user can choose which
        path to run first:
        -   *Question:* `"Should this session verify the implemented track on the live server or explore layout options in a scratch sandbox?"`
        -   *Options:*
            -   `"(Recommended) Verify implemented track on the live server (<runner> on localhost)"`
            -   `"Explore alternative UI layouts in an isolated <ArtifactDir>/scratch/ sandbox first"`
6.  **Review Mode Gate:** Otherwise, if no mode flag was provided in the
    arguments, present the review mode choice using `ask_question`:
    -   *Question:* "How would you like to review track '<track_name>'?"
    -   *Options:*
        -   `"(Recommended) Full Review: Check code and tests, then walk through
            manual scenarios together"`
        -   `"Interactive Testing only: Prepare the environment and guide me
            through manual scenarios"`
        -   `"Code Audit only: Inspect diff, automated tests, style guides, and
            architecture records"`

#### 2.2 Context Retrieval

1.  Load the track's `plan.md` and `spec.md`. Extract commit SHAs/revisions from
    `plan.md`.
2.  Determine the revision range for the review based on the plan and current
    workspace state.
3.  **If mode includes Code Audit (Full Review or Code Audit only):**
    -   Load `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/product-guidelines.md` and
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tech-stack.md`.
    -   Load ALL files in
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/code_styleguides/`. Treat these as
        "Law".
    -   Check for installed skills and enable specialized feedback if relevant.
4.  **If mode includes Interactive Testing (Full Review or Interactive Testing
    only):**
    -   Load
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_name>/manual_testing.md`.
    -   If domain runbooks exist in
        `{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md` mapped to touched
        areas or domain terms, load them.

#### 2.3 Multi-Expert Review Panel & Iterative Repair Loop (Code Audit — ADR 0015)

*(Skipped if mode is Interactive Testing only)*

Execute an iterative **Review $\to$ Deduplicate $\to$ Repair $\to$ Re-Verify**
loop across up to **`MAX_ITERATIONS = 3`** passes (`iteration = 1..3`, or `1`
pass with zero file edits when `--report-only` is specified):

1.  **3-Tier Runtime-Polymorphic Review Dispatch:**

    -   **Tier 1 — Host Review-Loop Adapter:** When an active platform rule
        provides a **Review Loop Host Adapter**, invoke the host adapter
        (`start_new_loop=true` on `iteration == 1`, `start_new_loop=false` on
        `iteration > 1`; counting comments strictly via `len(comments)` from the
        top-level JSON array) in parallel with the **Armature CDD Context
        Verifier** (`spec_and_adr_verifier`).
    -   **Tier 2 — Cross-Platform Multi-Agent Panel (Parallel Read-Only
        Subagents):** When no host adapter is active and multi-agent delegation
        is available, fan out three read-only reviewers (`workspace: "inherit"`)
        plus deterministic linters:
        1.  `spec_and_adr_verifier` (`include_intent: true`): Receives the VCS
            diff plus `spec.md`, `plan.md`, `adr/*.md`, `terms.md`,
            `manual_testing.md`, and active `legacy_fences`.
        2.  `code_taste_style_verifier` (`include_intent: false`): **Blinded to
            author commit messages and track rationale** to prevent confirmation
            bias; audits modularity, readability, `product-guidelines.md`, and
            `code_styleguides/*.md`.
        3.  `correctness_security_verifier` (`include_intent: false`): **Blinded
            to author intent**; audits concurrency/race conditions, null/error
            handling, hardcoded secrets/PII/XSS, and unit test coverage gaps.
        4.  `deterministic_linter_runner`: Executes the repository's configured
            formatter and linter checks from `tech-stack.md` / `workflow.md`.
    -   **Tier 3 — Single-Agent Sequential Multi-Perspective Pass:** On
        single-threaded harnesses (or small diffs where subagent fan-out is
        unavailable), evaluate the three verifier rubrics
        (`spec_and_adr_verifier` with intent; `code_taste_style_verifier` and
        `correctness_security_verifier` blinded to author self-justification)
        and deterministic linters sequentially.

2.  **Cross-Reviewer Deduplication, 2D `P0–P3` $\times$ `S0–S3` Ordering &
    Spec/ADR Precedence:**

    -   Merge overlapping findings across reviewers and sort by **Priority**
        (`P0` Architectural / Contract $\to$ `P1` Functional / Module $\to$ `P2`
        Local Implementation $\to$ `P3` Formatting / Polish) and **Severity**
        (`S0` Blocker $\to$ `S1` Critical $\to$ `S2` Improvement $\to$ `S3`
        Nit).
    -   **Accurate Top-Level `len(comments)` Counting:** Always compute each
        iteration's `Total Comments` strictly from the top-level `len(comments)`
        array. Never use `execution_metadata.reviewer_comments_count`, which
        double-counts skill-based reviewers and inflates the `Review Loop
        Iteration Breakdown` table.
    -   **Spec/ADR Precedence Rule (`status: skipped_spec_adr_precedence`):**
        Whenever a finding from a blinded reviewer (`code_taste_style_verifier`
        or `correctness_security_verifier` running with `include_intent: false`
        to prevent confirmation bias) conflicts with an explicit requirement in
        `spec.md` or an architectural invariant in `adr/*.md`, the approved
        Spec/ADR automatically takes precedence during cross-reviewer
        deduplication. Do **NOT** apply the conflicting style suggestion and do
        **NOT** modify `spec.md` or `adr/*.md`; record the suppressed suggestion
        under `Unapplied Comments & Rationale` (`status:
        skipped_spec_adr_precedence`), explicitly stating that the reviewer ran
        blinded (`include_intent: false` to prevent confirmation bias) and was
        overridden during cross-reviewer deduplication by the governing
        `spec.md` section or ADR number.
    -   **Convergence Check:** If `len(comments) == 0` (zero actionable findings
        remain), exit the repair loop immediately.

3.  **Ordered Auto-Repair & Four Safety Circuit Breakers (Skipped if
    `--report-only`):**

    -   Apply fixes strictly in `P0 -> P1 -> P2 -> P3` order (and `S0 -> S3`
        within each priority tier) so structural and contract changes settle
        before local implementation or formatting polish.
    -   **Circuit Breaker 1 — Legacy-Boundary Context Fence Firewall (`status:
        blocked_by_legacy_fence`):** Never auto-edit any file inside an active
        legacy-fenced directory (`<deprecated_path>` without `fence_overrides`)
        during the repair loop. Redirect the remediation to
        `<modern_replacement>` or record the comment under `Unapplied Comments &
        Rationale` (`status: blocked_by_legacy_fence`).
    -   **Circuit Breaker 2 — Approved Spec & ADR Immutability (`status:
        deferred_spec_conflict`):** Never mutate user-approved `spec.md`,
        `plan.md`, or `adr/*.md` files to silence a code review comment. Log
        genuine design contradictions under `Unapplied Comments & Rationale`
        (`status: deferred_spec_conflict`).
    -   **Circuit Breaker 3 — Unit-Test Regression Reversion & Anti-Oscillation
        Ledger (`status: reverted_test_regression`):** After applying repairs in
        Iteration $N$, run the affected automated unit test target(s). If a
        repair breaks any existing or new unit test and cannot be resolved
        cleanly in-pass, **immediately revert that broken repair**, record
        `(file_path, line_range, reviewer_category,
        status="reverted_test_regression")` in the **Anti-Oscillation Ledger**
        under `Unapplied Comments & Rationale`, and **NEVER re-attempt that
        fix** in Iteration $N+1$.
    -   **Circuit Breaker 4 — Surgical Scope & Final-Pass Application
        Guarantee:** Restrict `S2`/`S3` improvements strictly to lines modified
        by the track diff (never refactor untouched surrounding code or extract
        speculative single-use helpers), and **always apply valid, test-passing
        fixes discovered on the final iteration (`iteration ==
        MAX_ITERATIONS`)** before exiting the loop.

#### 2.4 Analysis Checklist & Pre-Manual-Testing Blocker Gate (Code Audit)

*(Skipped if mode is Interactive Testing only)*

Across each pass of the review loop, verify:

-   **Intent verification (`spec_and_adr_verifier` — Execution-Ready Grounding
    Audit per `ADR 0016`):** Does the implementation fulfill every requirement
    in `plan.md` and `spec.md`, including exact verified symbol/proto names,
    method signature arity, private-to-public helper exposures, bidirectional UI
    `<->` wire field bijections and default values, server validator
    preconditions, hydration echo-suppression guards, self-contained
    timer/signal state machines, and unit-test fixture/bundle overrides?
-   **ADR compliance (`spec_and_adr_verifier`):** For each ADR in
    `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/` active in the modified modules,
    verify adherence to the recorded decision and its confirmation checklist.
-   **Style compliance (`code_taste_style_verifier` — Blinded):** Are
    `product-guidelines.md` and `code_styleguides/*.md` rules followed without
    violating approved `spec.md` / `adr/*.md` constraints?
-   **Correctness & safety (`correctness_security_verifier` — Blinded):** Check
    for bugs, race conditions, null risks, hardcoded secrets, or PII.
-   **Automated testing:** Check for automated tests covering changes and verify
    the test suite passes after each repair iteration.
-   **Legacy-Boundary Context Fence Diff Firewall (`VAL_LF_02`):** When
    `[Workspace Context...]` and `[Cumulative Branch Diff...]` are provided in
    the prompt, DO NOT call `code_search` or `view_file` to search for
    `tracks.md` or `tech-stack.md`. Immediately evaluate the cumulative branch
    diff (`git diff main...HEAD`) against active legacy fences and output the
    complete Code Audit report in markdown in that same turn:
    -   **Blocking Violations (`+` Added Lines):** If any file inside a
        legacy-fenced directory has status `A` (added) or status `M` (modified)
        with $>0$ added lines (e.g., `client/legacy_canvas/widget.ts` with `+15
        lines added`) and is not listed in `fence_overrides`, you MUST flag it
        in markdown as a **`[BLOCKING] Legacy Fence Violation`** (`P0/S0`),
        refuse auto-editing the fenced file (`status: blocked_by_legacy_fence`),
        and explicitly direct remediation to the modern replacement directory
        (`<modern_replacement>`, e.g., `client/react_scf/`).
    -   **Decommissioning & Pure Line Removal Exemption (`0` Added Lines / `R` /
        `D`):** Explicitly distinguish in your markdown analysis between
        unauthorized code additions (`+` added lines) and permitted
        decommissioning/dead-code removals (`0` added lines). Modified files
        with **`0` added lines** (`+0 lines added, -N lines removed` — pure
        dead-code line removal, e.g., `client/legacy_canvas/dead_helper.ts`) and
        whole-file deletions (`status R`, `!`, `D`) inside legacy-fenced
        directories MUST be explicitly **EXEMPT** from blocking violations.
-   **Manual testing runbook:** Audit changed routes, navigation guards, persona
    transitions, and error handlers against
    `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_name>/manual_testing.md`.
-   **Pre-Manual-Testing Unapplied Blocker Gate (Transition to Step 2.5):**
    -   When the review mode includes Interactive Manual Testing (`Full Review`)
        and the repair loop finishes:
        -   **Case A — Unapplied `S0` or `S1` Blockers Remain (Mandatory
            Same-Turn `ask_question` Modal — Never End Turn With Text Alone):**
            If $\ge 1$ blocking (`S0` or `S1`) findings remain unapplied (e.g.,
            due to a reverted unit-test regression `reverted_test_regression`, a
            `deferred_spec_conflict`, or a `blocked_by_legacy_fence` violation),
            **halt before Step 2.5**, do **NOT** call `write_to_file` on
            `review.md` yet, output the `## Review Loop Iteration Breakdown`
            markdown table and `## Unapplied Comments & Rationale` in visible
            markdown, and **IMMEDIATELY invoke the native `ask_question` tool in
            that exact same turn** (you are strictly forbidden from ending the
            turn with markdown prose alone):
            -   *Question:* `"Unapplied S0/S1 blocking findings remain after the
                repair loop. How should we proceed?"`
            -   *Options:*
                1.  `"(Recommended) Inspect and resolve the unapplied S0/S1
                    blocker(s) before manual testing"`
                2.  `"Proceed to Step 2.5 Interactive Manual Testing anyway
                    (treat as false positive / tech debt)"`
                3.  `"Stop after Code Audit and write review.md now"`
        -   **Case B — Zero Unapplied `S0`/`S1` Blockers Remain (Mandatory
            Same-Turn Transition Into Step 2.5 Scenario 1 + `ask_question`):**
            If `0` unapplied `S0`/`S1` findings remain (even if non-blocking
            `S2`/`S3` suggestions were skipped via `skipped_spec_adr_precedence`
            or surgical scope filtering), do **NOT** pause at the blocker gate
            and do **NOT** write `review.md` yet. In that **single response
            turn**, render the `## Review Loop Iteration Breakdown` markdown
            table at the top of your chat response, proceed **directly into Step
            2.5** by rendering **Scenario 1** (using the canonical 6-part
            structure with sanitized `localhost` URL and `##### Expected
            Observations`), and **IMMEDIATELY invoke the native `ask_question`
            tool in the same turn** asking `"Did Scenario 1 meet the expected
            outcome?"` with the Step 2.5 verification options (`"(Recommended)
            Verified: ..."`, `"Didn't match expectation (I will describe what
            occurred)"`, `"Skip to next scenario"`).

#### 2.5 Interactive Verification Phase (Guided Manual Testing)

*(Skipped if mode is Code Audit only)*

> [!IMPORTANT] **MANDATORY STEP 2.5 EXECUTION BARRIERS (ZERO BARE TOOL CALLS &
> ZERO PREMATURE `review.md` WRITES):**
> 1. **Never Write `review.md` Before Verification Completes:** During Step 2.5, do **NOT** call `write_to_file` to generate `review.md`. You MUST present the interactive verification walkthrough in chat and pause via `ask_question` to collect the user's empirical verification result first.
> 2. **Strict Zero-Echo Sanitization Invariant (Never Quote Legacy Draft Strings):** When reading an input `manual_testing.md` draft that contains remote workstation hostnames (`<REMOTE_HOST>.example.com`), `"Expected Observables"` headers, or un-reproduced snippet instructions (`"paste the snippet from Scenario 1"`), **NEVER** echo, quote, or mention those forbidden strings anywhere in your chat response (not even to explain that you replaced them). Silently output **ONLY** the sanitized `localhost` URL (`http://localhost:<PORT>/<path>` or `http://localhost:<PORT>/<path>`), the exact `##### Expected Observations` header, and the complete inline copy-pastable code snippet. When disqualifying a stateful/auth/RPC diff from Micro-Verification, explain the disqualification in plain English without rendering or quoting the `┌─ [Micro-Verification Plan]` ASCII box header.
> 3. **Mandatory Markdown Walkthrough Before Every `ask_question` Call:** Never emit a bare `ask_question` tool call without a complete markdown response in the exact same turn:
>    - For **Path A (Visual-Only)**, always render the full `┌─ [Micro-Verification Plan] ──┐` ASCII card in chat text before calling `ask_question` with the exact escape hatch option `"Run full domain runbook instead (execute database seed & multi-role scenarios)"`.
>    - For **Path B (Stateful / Disqualified Diffs)**, even when a setup command triggers the Hybrid Smart Gate confirmation prompt or when disqualifying a false-visual diff (e.g. an `*ngIf` auth guard or RPC mutation), you MUST first output the complete **6-Part Scenario Structure** in markdown before invoking `ask_question`:
>
>      ```markdown
>      #### Scenario <ID>: <Title> — <Synopsis>
>
>      <1–2 sentence verification synopsis explaining what behavior, timeout, or state transition is verified.>
>
>      ##### Prerequisites
>      Ensure your local development server is running:
>      ```bash
>      <exact dev server startup command, e.g. ./run.sh>
>      ```
>
>      ##### Target URL
>      Navigate to the target view in Google Chrome:
>      `http://localhost:<PORT>/<path>`
>
>      ##### Step-by-Step Setup
>      1. <Step-by-step setup instruction>
>      2. <Complete, self-contained copy-pastable setup snippet reproduced inline:>
>      ```javascript
>      <complete self-contained snippet, e.g. window.__appSim = ...; window.__appSim.enable();>
>      ```
>      *(<Concise italicized explanation of what the snippet simulates.>)*
>
>      ##### Action Steps
>      1. <Action step 1 (what to do and where)>
>      2. <Action step 2>
>
>      ##### Expected Observations
>      * **UI Behavior**:
>        * <Concrete visual state, spinner duration, toast message, or route update>
>      * **DevTools Console Log**:
>        * <Concrete log message or RPC status>
>      ```
> 4. **Intent-Scoped Live Application Server Verification (vs. Standalone Prototyping) & Per-Track Deliverable Mapping:**
>    - **Verification = Live Server Only (Zero Simulated HTML Harnesses):** Whenever post-implementation `/arm-review`, `/arm-bash`, design-mock audits, or PR/runbook screenshot and screencast capture runs, it MUST start the real application server via the project's canonical runner (e.g., `./scripts/run.sh`, `./run.sh`, or `npm run dev`) and load the live `localhost` URL (`http://localhost:<PORT>/<path>`) in headless Chrome / Playwright. **NEVER** create or render a standalone HTML harness (`file://` or `data:`) to mock implemented UI views.
>    - **Exploration = Standalone Sandboxes Only:** Pre-implementation design exploration (`/prototype`, `/sandbox-preview`) lives strictly outside application repositories in an isolated scratch directory (`<ArtifactDir>/scratch/`) or local static preview server (never temporary `?variant=` routes inside application repositories). If a user prompt is ambiguous between exploring design options in a standalone sandbox vs. verifying implemented code on the live application server, pause and disambiguate via `ask_question` first.
>    - **Multi-Track 1-to-1 Deliverable Unit & Configuration Reference:** When reviewing or delivering multiple tracks, maintain a strict 1-to-1 mapping: each track ships in its own standalone commit/PR (including its `manual_testing.md` and `review.md`), URL bookmark (`.url.json` when supported), and dedicated live runbook walkthrough video, paired with a comprehensive per-track engineering & external configuration report documenting exact feature flags, service/client IDs, runtime bootstrap config keys (e.g., `window.__APP_CONFIG__` / environment variables), storage buckets, log/telemetry scrubbing allowlists, verified file/line links, and repository code vs. external admin console setup.

Route execution based on the **Stage 2 Empirical VCS Diff Classification** (Step
2.1):

##### Path A: Automatic Micro-Verification Walkthrough (Visual-Only Footprints)

When the empirical VCS diff qualifies as **Visual-Only** (including the
**Orphaned Dead-Code Cleanup Exemption**):

1.  **Zero-Latency Documentation-Only Execution (Skip DB Seeding & Probes)**:
    -   Do **NOT** execute any **Hybrid Smart Gate** database migrations, SQL
        seed commands (`INSERT`, `DROP`, `span sql`, `seed_users.js`), API token
        minting, or shell dev-server probes.
    -   Briefly note the presentational qualification in markdown (and
        explicitly mention the Orphaned Dead-Code Cleanup Exemption if an unused
        event handler or local display helper was deleted alongside a removed UI
        element).
2.  **Automatic Micro-Verification Card Rendering**:

    -   Render the canonical ASCII `┌─ [Micro-Verification Plan] ──┐` card
        directly in chat:

        ```text
        ┌─ [Micro-Verification Plan] ────────────────────────┐
        │ Change detected: Visual-only (HTML/SCSS)           │
        │                                                    │
        │ [•] Step 1: Run local server (`./run.sh`) (requires active logged-in session) │
        │ [•] Step 2: Navigate to `http://localhost:8080/groups` │
        │ [•] Verify: Only "Email Forwarding" card is visible│
        │                                                    │
        │ (Database seeding and API testing skipped)         │
        └────────────────────────────────────────────────────┘
        ```
    -   **Route Guard Session Hint (`Step 1`)**: Inspect route guards or parent
        data containers. If the route requires authentication, append a concise
        one-line session hint to `Step 1`: `(requires active logged-in session)`
        (e.g., `[•] Step 1: Run local server (./run.sh) (requires active
        logged-in session)`).
    -   **Strict `localhost` URL Standard (`Step 2`)**: All target URLs in `Step
        2` MUST strictly use complete, clickable
        `http://localhost:<PORT>/<path>` (or
        `http://localhost:<PORT>/<path>`) formatting. **NEVER**
        output bare partial routes (e.g., `/groups`) and **NEVER** output
        remote workstation hostnames (`<REMOTE_HOST>.example.com`) in Micro-Verification
        cards.
    -   **Semantic Visual Assertions (`Verify`)**: Anchor assertions on visible
        text labels or semantic ARIA roles rather than brittle CSS classes.
3.  **Multi-Route Consolidation vs. Sequential Walkthroughs**:

    -   Inspect SCSS `@mixin` or global theme token edits for multi-route blast
        radius.
    -   If visual changes span multiple routes (e.g., `/groups` and `/settings`)
        that share a **common dev-server and session setup state**, consolidate
        all affected `localhost` URLs and visual assertions into a **SINGLE
        consolidated `┌─ [Micro-Verification Plan] ──┐` card** and a **SINGLE
        `ask_question` turn**.
    -   Step through sequential walkthrough turns **only** if distinct setup
        states are required across routes.
4.  **Inline Override Escape Hatch (`ask_question` Modal Gate)**:

    -   Immediately following the card, call `ask_question` with the mandatory
        inline escape hatch:
        -   *Question:* `"Did the visual verification match the expected
            outcome?"`
        -   *Options:*
            1.  `"(Recommended) Verified: <concise expected visual outcome>"`
            2.  `"Run full domain runbook instead (execute database seed &
                multi-role scenarios)"`
            3.  `"Didn't match expectation (I will describe what occurred)"`
    -   If the user selects `"Run full domain runbook instead..."`, immediately
        transition to **Path B** below to execute full database seeding and
        multi-persona scenarios.

##### Path B: Standard Stateful Walkthrough (Stateful / Full-Stack Footprints or User Override)

When the diff modifies state, auth guards, or RPCs (or when the user selects
`"Run full domain runbook instead"`):

1.  **Scenario Extraction:**
    -   Parse
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_name>/manual_testing.md`
        for personas and scenarios:
        -   Preconditions & State Setup commands (`bash`, `sql`, CLI scripts).
        -   Test Scenario Title & Synopsis (`#### Scenario <ID>: <Title> — <Synopsis>`).
        -   Action steps (URLs, routes, screens, buttons, CLI invocations).
        -   Expected Observations and barrier checks.
    -   Maintain a real-time `### Manual Testing Verification Ledger` in chat
        throughout execution:
        -   `[ ]` Pending
        -   `[x]` Verified
        -   `[!]` Logged Issue
        -   `[~]` Requires Quick Re-check (flagged if a subsequent in-flight
            hotfix modifies code)
2.  **Sequential Scenario Walkthrough (Iterate 1 to N):** For each scenario:

    -   **Environment Preparation (Hybrid Smart Gate):**
        -   Inspect the precondition/setup command.
        -   *Destructive Safety Filter*: If the command or script contains
            destructive operations (matching keywords in commands, script names,
            or arguments: `DROP`, `DELETE`, `TRUNCATE`, `rm -rf`, `reset`,
            `clean`, `wipe`, `reseed`, `kill`), you MUST first output the
            complete markdown **6-Part Scenario Structure** below so the user has
            full context, and then call `ask_question`:
            -   *Question:* "Setup step has destructive commands: `<command>`.
                Proceed with execution?"
            -   *Options:*
                -   `"(Recommended) Yes, execute the setup command"`
                -   `"No, skip automated execution (I'll prepare state
                    manually)"`
                -   `"Skip this scenario"`
        -   *Non-Destructive Execution*: Standard fixtures (inserting test
            records, running seed scripts like `node scripts/seed_users.js`,
            minting tokens, exporting env vars) execute **automatically** via
            the Hybrid Smart Gate. You MUST explicitly state in your chat
            response that the Hybrid Smart Gate executed the non-destructive
            setup command automatically and stream its execution status (e.g.,
            ``**[Hybrid Smart Gate] Automatically executed setup:** \`node
            scripts/seed_users.js\` -> Status: Completed (Exit code 0)``).
            **NEVER** instruct the user to manually run non-destructive seed or
            setup scripts in their terminal.
        -   Verify command exit code 0 before prompting the user.
    -   **Sequential Guidance Presentation (Canonical 6-Part Scenario Structure):**
        Output markdown describing the active scenario using strictly this
        6-part structure:

        -   **1. Scenario Heading with Name & Synopsis**:
            `#### Scenario <ID>: <Title> — <Synopsis>`
            *(Include `(Persona: <Persona>)` when testing multi-role permissions).*
        -   **2. Succinct Verification Synopsis**:
            Immediately beneath the heading, write a concise 1–2 sentence
            paragraph stating what specific end-to-end behavior, timeout,
            concurrency guard, or state transition is being verified.
        -   **3. `##### Prerequisites`**:
            -   Explicitly document all long-running development server startup
                commands or background daemon commands (e.g., `./run.sh`, `npm
                run dev`, `./scripts/run.sh`) inside a
                copy-pastable `bash` fenced code block.
                *(Note: One-off seed/setup commands executed automatically by
                the Hybrid Smart Gate must be reported as completed setup steps
                above, NOT listed as manual commands for the user to run).*
            -   Explicitly instruct the user to ensure the local development
                server is running before navigating.
        -   **4. `##### Target URL`**:
            -   Provide the exact browser destination using **strictly the
                complete `localhost` URL form** inside a code block or prominent
                link:
                `http://localhost:<PORT>/<path>` or
                `http://localhost:<PORT>/<path>`.
            -   **Strict Localhost-Only Invariant (Zero remote workstation Hostname Leaks)**:
                **NEVER** output bare partial routes alone (e.g., `/settings`)
                and **NEVER** show or include remote workstation host URLs
                (`<REMOTE_HOST>.example.com:<PORT>`) in chat responses, links,
                or runbooks. If an input `manual_testing.md` file contains a
                remote workstation hostname URL, automatically normalize and replace it
                with the corresponding `localhost` URL.
        -   **5. `##### Step-by-Step Setup` (or `##### Simulation Setup`)**:
            -   Numbered step-by-step instructions guiding DevTools console,
                mock state, or environment setup prior to triggering the UI
                action.
            -   **Self-Contained Copy-Pasteable Snippet Invariant (Zero Clipboard Hunting)**:
                Whenever a step requires pasting or running a JavaScript console
                snippet, simulation mock, payload, or CLI command (e.g.,
                `window.__appSim.enable()`), you MUST reproduce the **complete,
                self-contained, copy-pastable code block directly inline** in
                that scenario's setup section. **NEVER** write instructions like
                *"paste the snippet you loaded earlier"* or *"use the snippet
                from Scenario 1"* without reproducing the full code block, as
                the user's clipboard may no longer contain it. Below the code
                block, include a concise italicized note explaining what the
                snippet configures or simulates.
        -   **6. `##### Action Steps`**:
            -   Numbered, imperative steps telling the user exactly what actions
                to perform and where in order to test (e.g., `1. In the
                Workspace Settings UI, select...`, `2. Click Delete Group...`).
        -   **7. `##### Expected Observations`**:
            -   **Strict Terminology Invariant (Never Use `"Expected Observables"`)**:
                Always title this section `##### Expected Observations`.
                **NEVER** use the heading `"Expected Observables"` (even if the
                draft runbook contains it), because `"Observables"` is easily
                confused with RxJS `Observable` streams.
            -   Categorize expected observations by domain where applicable
                (e.g., `**UI Behavior:**`, `**DevTools Console Log:**`,
                `**Network / Telemetry:**`, `**Database / Backend State:**`),
                listing concrete visual states, timing milestones (`t = 10s`),
                toast strings, or log lines to observe.
    -   **Verification Gate (`ask_question`):**

        -   *Question:* "Did Scenario <ID> meet the expected outcome?"
        -   *Options:*
            -   `"(Recommended) Verified: <brief expected result observed>"`
            -   `"Didn't match expectation (I will describe what occurred)"`
            -   `"Skip to next scenario"`
        -   *Guardrail (Empirical Verification Only):* Verification gates test
            empirical application state, not architectural trade-offs. Do
            **NOT** output the Interview Turn v2 body (stakes opener, numbered
            options, `### Recommendation: Option N`, `Pick N if …` lines), the
            Zoom-In View cards (`**Pros:**` / `**Cons:**` /
            `**Implications:**`), or the `"I need more context, zoom out and
            give examples"` option on scenario verification prompts.
    -   **In-Flight Discrepancy Triage:**

        -   If the user reports a mismatch, enter diagnostic mode: inspect
            relevant code and logs to identify the root cause.
        -   Explain the diagnosis in markdown and prompt via `ask_question`:
            -   *Question:* "Discrepancy diagnosed. How should we proceed?"
            -   *Options:*
                -   `"(Recommended) Apply targeted fix now, re-run setup, and
                    re-verify"`
                -   `"Log this issue and continue to the next scenario"`
                -   `"Update the runbook expectation (code is correct, spec was
                    outdated)"`
        -   *In-Flight Hotfix & Cascade Invalidation*: If the user chooses to
            fix the code now:
            -   Apply the minimal targeted fix.
            -   Re-run the scenario setup command and prompt the user to
                re-verify.
            -   **Cascade Invalidation Tracking**: Mark previously verified
                scenarios in the ledger as `[~] Requires Quick Re-check`. Before
                completing testing, offer a rapid re-run of affected scenarios.
        -   *Logging Discrepancies*: If the user chooses to log the issue,
            record it in the ledger as `[!] Logged Issue: <notes>` and continue
            to the next scenario.
3.  **Mandatory Post-Testing Reconciliation Gate:**

    -   If ANY scenario remains marked `[!] Logged Issue` or `[~] Requires Quick
        Re-check` after the walkthrough:
    -   The agent **strictly halts** before report completion and outputs: `###
        Logged Discrepancies Requiring Attention` listing all open issues.
    -   Prompt via `ask_question`:
        -   *Question:* "Interactive testing has N open issues. How should we
            resolve them?"
        -   *Options:*
            -   `"(Recommended) Triage and resolve logged issues now"`
            -   `"Record as [BLOCKING] review findings in review.md (requires
                re-review)"`
            -   `"Acknowledge as [WARNING] tech debt in review.md and proceed"`
    -   If the user chooses to resolve now, step through the logged items, apply
        fixes, re-test, and mark them `[x] Verified`.
4.  **Living Runbook Synchronization:**

    -   If setup commands, URLs, or barrier checks were corrected or refined
        during testing:
    -   Automatically update
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_name>/manual_testing.md`
        with the verified working commands so future runs stay synchronized.

### 3. Review & Resolution

> [!IMPORTANT] **MANDATORY SINGLE-TURN ATOMIC REPORT & COMPLETION GATE INVARIANT
> (`STEP 3.1` + `STEP 3.2`):** Whenever generating the review report (e.g., on
> `--static` / `Code Audit only`, `--report-only`, or after Step 2.5 Interactive
> Manual Testing completes), you MUST execute **Step 3.1 AND Step 3.2 atomically
> in the exact same turn**. You are **STRICTLY FORBIDDEN** from splitting
> `write_to_file` and `ask_question` across separate turns, emitting
> `write_to_file` with empty visible chat text, or ending the turn with markdown
> prose alone without tool calls. In that single turn, you MUST emit all
> three: 1. **Visible Markdown Report in Chat:** Print the complete markdown
> report directly in your visible chat response (starting with the
> once-per-session Turn 1 legacy fence callout banner if `legacy_fences` exist
> and have not yet been shown in the session, the `##
> Review Loop Iteration Breakdown` markdown table counting `Total Comments`
> strictly from top-level `len(comments)`, `## Summary of Applied Fixes`
> explicitly ordered in strict `P0 -> P1 -> P2 -> P3` priority order and
> explicitly stating when a final-pass fix was applied per the **Final-Pass
> Application Guarantee** (`iteration == MAX_ITERATIONS`), and `## Unapplied
> Comments & Rationale` documenting exact status codes
> `reverted_test_regression`, `skipped_spec_adr_precedence` with
> `include_intent: false` confirmation-bias and deduplication rationale,
> `blocked_by_legacy_fence`, and `deferred_spec_conflict`). 2. **Persist
> `review.md` via `write_to_file`:** Call
> `write_to_file(TargetFile="{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_name>/review.md",
> CodeContent="...")` in the same turn. 3. **Invoke `ask_question` for Step
> 3.2:** Concurrently call the native `ask_question` tool in the **exact same
> turn** alongside `write_to_file` to present the Step 3.2 Review Report
> Completion Gate (even when `0` open findings remain after repair).

#### 3.1 Report & Decision

Generate the review report as an Antigravity artifact (save to
`{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_name>/review.md` using
`write_to_file`, and write the full per-iteration comment log to
`{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_name>/review_loop_details.md`
when the multi-expert review loop executed).

Always render the `## Review Loop Iteration Breakdown` table directly in your
visible chat response alongside the artifact link (Dual Rendering Invariant).
Use the following strict output format for `review.md`:

```markdown
# Code Review Report: Track <track_name>

## Executive Summary
{1-2 paragraphs summarizing the review outcome, multi-expert repair loop convergence, manual verification results, and overall readiness}

## Verification Checks
- **Automated Testing:** [Pass / Fail / Warnings]
- **Multi-Expert Review Loop:** [Converged in N Iteration(s) | Completed Max Iterations (N Applied, M Unapplied) | Single-Pass (--report-only)]
- **Manual Testing Runbook:** [Pass / Fail / Warnings]
- **Interactive Manual Testing:** [Verified: X/Y Passed, Z Resolved In-Flight, W Tech Debt | Not Executed (Static Audit Only)]
- **ADR Compliance:** [Pass / Fail / Warnings]
- **Style & Standards:** [Pass / Fail / Warnings]
- **Fixpoint Audit:** [Pass / Fail]

## Review Loop Iteration Breakdown
| Iteration | Reviewers Executed | Reviewer Skipped | Total Comments | Applied | Unapplied |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | spec_and_adr_verifier, code_taste_style_verifier, correctness_security_verifier, deterministic_linter_runner | None | 4 | 3 | 1 |
| 2 | spec_and_adr_verifier, code_taste_style_verifier, correctness_security_verifier, deterministic_linter_runner | None | 0 | 0 | 0 |

## Summary of Applied Fixes
- **[P0 / S0] `<file_path>:<line>` (`<reviewer>`):** <Concise description of the architectural/contract fix applied and verified by unit tests>
- **[P2 / S2] `<file_path>:<line>` (`<reviewer>`):** <Concise description of the local implementation or readability fix applied>

## Unapplied Comments & Rationale (Anti-Oscillation Ledger)
- **[P1 / S1] `<file_path>:<line>` (`<reviewer>`) — `status: reverted_test_regression`:** <Explanation of which unit test broke when this fix was attempted, why the hunk was reverted, and why it was locked in the Anti-Oscillation Ledger>
- **[P2 / S2] `<file_path>:<line>` (`<reviewer>`) — `status: skipped_spec_adr_precedence`:** <Explanation of why the blinded style suggestion was suppressed in favor of explicit `spec.md` / `ADR NNNN` requirements>
- **[P0 / S0] `<deprecated_path>:<line>` (`<reviewer>`) — `status: blocked_by_legacy_fence`:** <Explanation that auto-editing `<deprecated_path>` is prohibited by the Legacy-Boundary Context Fence Firewall; remediation directed to `<modern_replacement>`>
- **[P1 / S1] `<file_path>:<line>` (`<reviewer>`) — `status: deferred_spec_conflict`:** <Explanation of the specification contradiction preserved for human decision without mutating approved `spec.md` / `adr/*.md`>

## Analysis of Repeated Comments
{Brief analysis of any comments that recurred across iterations or were suppressed by the Anti-Oscillation Ledger, or "None — all applied fixes resolved cleanly on re-verification."}

## Interactive Verification Log
*(Included when Interactive Manual Testing is executed)*
| Scenario ID | Persona / Title | Status | Environment Setup | Verification Notes |
| :--- | :--- | :--- | :--- | :--- |
| Test Auth.01 | Guest / Landing View | Verified | Cleared local user records | Saw 'Join Waitlist' CTA |
| Test Auth.02 | Waitlisted User | Fixed & Verified | Seeded waitlist=true | Fixed button routing; confirmed /waitlist |

## Detailed Findings
{Numbered remaining open findings categorized by severity: [BLOCKING] (`S0`/`S1`), [WARNING] (`S2`), [NOTE] (`S3`), or "No open blocking findings remain."}

## Recommendation
{Clear recommendation: Approve / Approve with Minor Edits / Revise Required}
```

#### 3.2 Resolution & Next Steps (Review Report Completion Gate)

Use `ask_question` to present structured next steps:

1. "Approve and proceed to track completion (/arm-implement Step 5)"
2. "Address findings and re-review"
3. "Acknowledge findings as tech debt"
