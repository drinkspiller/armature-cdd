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

#### 2.1 Scope & Review Mode Identification

1.  Check for user-provided arguments describing what to review and mode flags:
    -   `--both` or `--comprehensive`: Run Full Review (Static Code Audit +
        Guided Manual Testing).
    -   `--manual` or `--interactive`: Run Guided Manual Testing only.
    -   `--static`: Run Static Code Audit only.
2.  **Auto-detect Track:** Read `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md`
    and look for an in-progress track (`[~]`).
3.  If no track is specified or found, prompt the user for the track name.
4.  **Review Mode Gate:** If no mode flag was provided in the arguments, present
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
    the prompt, DO NOT call `grep_search` or `view_file` to search for
    `tracks.md` or `tech-stack.md`. Immediately evaluate the cumulative branch
    diff (`git diff main...HEAD` or `git diff main...HEAD`) against active
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

1.  **Scenario Extraction:**
    -   Parse
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_name>/manual_testing.md`
        for personas and scenarios:
        -   Preconditions & State Setup commands (`bash`, `sql`, CLI scripts).
        -   Test Scenario Title (`### Test <Domain>.<ID>: <Title>`).
        -   Action steps (URLs, routes, screens, buttons, CLI invocations).
        -   Expected outcomes and barrier checks.
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
            `clean`, `wipe`, `reseed`, `kill`), pause execution and call
            `ask_question`:
            -   *Question:* "Setup step has destructive commands: `<command>`.
                Proceed with execution?"
            -   *Options:*
                -   `"(Recommended) Yes, execute the setup command"`
                -   `"No, skip automated execution (I'll prepare state
                    manually)"`
                -   `"Skip this scenario"`
        -   *Non-Destructive Execution*: Standard fixtures (inserting test
            records, starting dev servers, minting tokens, exporting env vars)
            execute automatically via `run_command` with progress streaming.
        -   Verify command exit code 0 before prompting the user.
    -   **Sequential Guidance Presentation:** Output markdown describing the
        active scenario:

        -   `#### Scenario <ID>: <Title> (Persona: <Persona>)`
        -   `##### Prerequisites`:
            -   Explicitly document all development server startup commands,
                background daemon commands, or environmental state prerequisites
                (e.g., `./run.sh`, `npm run dev`, `python server.py`) inside a
                fenced code block.
            -   Explicitly instruct the user to ensure the local server or
                background stack is running before attempting to navigate.
            -   List required account personas, session tokens, or seeded
                database state established in this step.
        -   `##### Target URLs & Navigation`:

            -   **NEVER** provide partial routes alone (e.g., `/landing` or
                `/waitlist`).
            -   **MANDATORY DUAL-URL CODE BLOCKS**: For web destinations, you
                MUST always provide **BOTH** complete, fully qualified URLs in
                separate fenced code blocks for easy copy-pasting:

                -   **Localhost URL**:

                    ```
                    http://localhost:<PORT>/<path>
                    ```

                    *(or `https://localhost.local:<PORT>/<path>`)*
                -   **Cloudtop Proxy URL**:

                    ```
                    http://127.0.0.1:<PORT>/<path>
                    ```

                    *(or `https://<HOSTNAME>.local:<PORT>/<path>`)*
        -   `##### Manual Verification Steps`:

            -   Numbered steps telling the user exactly what actions to trigger
                on the page, UI component, or CLI.
        -   `##### Expected Outcome & Barrier Checks`:

            -   Concrete visual states, CSS layout assertions, HTTP response
                codes, or unauthorized route rejections to verify.
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

Generate review report as a artifact (save to `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_name>/review.md` using `write_to_file`).

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
