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
    -   `--both` or `--comprehensive`: Run Full Review (Static Code Audit +
        Guided Manual Testing).
    -   `--manual` or `--interactive`: Run Guided Manual Testing only.
    -   `--static`: Run Static Code Audit only.
2.  **Auto-detect Track:** Read `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md`
    and look for an in-progress track (`[~]`).
3.  If no track is specified or found, prompt the user for the track name.
4.  **Stage 2 Empirical VCS Diff Classification (ADR 0009):** Before executing
    review or manual testing, inspect the actual VCS diff (`hg status` / `hg
    diff` or `git diff`) using the **Hybrid AST + Diff Classifier**:
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
5.  **Review Mode Gate:** If no mode flag was provided in the arguments, present
    the review mode choice using `ask_question`:
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

#### 2.3 Smart Chunking & Review Process (Code Audit)

*(Skipped if mode is Interactive Testing only)*

1.  **Volume check:** Run VCS diff stat.
2.  Determine diff size:
    -   **Small/Medium (<300 lines):** Perform a single-pass review by reading the full diff output.
    -   **Large (>300 lines):** Confirm with user via `ask_question`: "Iterative Review Mode may take longer. Proceed?"
        -   If yes: Review each source file individually using `view_file` (skip lock files and assets). Store per-file findings and aggregate them.
        -   If no: Attempt a high-level summary review or ask user to narrow scope.

#### 2.4 Analysis Checklist (Code Audit)

*(Skipped if mode is Interactive Testing only)*

Evaluate the changed code against the following criteria:

-   **Intent verification:** Does the implementation fulfill requirements in `plan.md` and `spec.md`?
-   **ADR compliance:** For each ADR in `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/` active in the modified modules, verify adherence to the recorded decision and its confirmation checklist.
-   **Style compliance:** Are `product-guidelines.md` and `code_styleguides/*.md` rules followed?
-   **Correctness & safety:** Check for bugs, race conditions, null risks, hardcoded secrets, or PII.
-   **Automated testing:** Check for new automated tests covering changes. Run test suite.
-   **Legacy-Boundary Context Fence Diff Firewall (`VAL_LF_02`):** When
    `[Workspace Context...]` and `[Cumulative Branch Diff...]` are provided in
    the prompt, DO NOT call `code_search` or `view_file` to search for
    `tracks.md` or `tech-stack.md`. Immediately evaluate the cumulative branch
    diff (`hg status --rev p4base` or `git diff main...HEAD`) against active
    legacy fences and output the complete Code Audit report in markdown in that
    same turn:
    -   **Blocking Violations (`+` Added Lines):** If any file inside a
        legacy-fenced directory has status `A` (added) or status `M` (modified)
        with $>0$ added lines (e.g., `client/legacy_canvas/widget.ts` with `+15
        lines added`) and is not listed in `fence_overrides`, you MUST flag it
        in markdown as a **`[BLOCKING] Legacy Fence Violation`** and explicitly
        direct remediation to the modern replacement directory
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
-   **Skill-specific checks:** Apply specialized guidelines from relevant installed skills.

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
                to perform and where in order to test (e.g., `1. In the CC
                Settings UI, select...`, `2. Click Delete Group...`).
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
        -   *Guardrail (Empirical Verification Only):* Verification gates test empirical application state, not architectural trade-offs. Do **NOT** output Pros/Cons matrices or append the `"Elaborate on trade-offs..."` option to scenario verification prompts.
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

#### 3.1 Report & Decision

Generate review report as a Antigravity artifact (save to `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_name>/review.md` using `write_to_file`).

Use the following strict output format for the report:

```markdown
# Code Review Report: Track <track_name>

## Executive Summary
{1-2 paragraphs summarizing the review outcome, key strengths, manual verification results, and overall readiness}

## Verification Checks
- **Automated Testing:** [Pass / Fail / Warnings]
- **Manual Testing Runbook:** [Pass / Fail / Warnings]
- **Interactive Manual Testing:** [Verified: X/Y Passed, Z Resolved In-Flight, W Tech Debt | Not Executed (Static Audit Only)]
- **ADR Compliance:** [Pass / Fail / Warnings]
- **Style & Standards:** [Pass / Fail / Warnings]
- **Fixpoint Audit:** [Pass / Fail]

## Interactive Verification Log
*(Included when Interactive Manual Testing is executed)*
| Scenario ID | Persona / Title | Status | Environment Setup | Verification Notes |
| :--- | :--- | :--- | :--- | :--- |
| Test Auth.01 | Guest / Landing View | Verified | Cleared local user records | Saw 'Join Waitlist' CTA |
| Test Auth.02 | Waitlisted User | Fixed & Verified | Seeded waitlist=true | Fixed button routing; confirmed /waitlist |

## Detailed Findings
{Numbered findings categorized by severity: [BLOCKING], [WARNING], [NOTE]}

## Recommendation
{Clear recommendation: Approve / Approve with Minor Edits / Revise Required}
```

#### 3.2 Resolution & Next Steps

Use `ask_question` to present structured next steps:

1. "Approve and proceed to track completion (/arm-implement Step 5)"
2. "Address findings and re-review"
3. "Acknowledge findings as tech debt"
