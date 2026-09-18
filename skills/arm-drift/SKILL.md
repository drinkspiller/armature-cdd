---
name: arm-drift
description: Audit and resolve documentation drift, spec divergence, and packaging inconsistencies across Armature and Conductor projects. Use when asked to audit drift, check fixpoint, run /arm-drift, or verify spec-to-code alignment.
persona: Armature Fixpoint Auditor
---

# /arm-drift — Fixpoint Auditor

**Purpose:** Audit project documentation, active specifications, Architecture
Decision Records (ADRs), domain manual testing runbooks, API surfaces, and
installer packaging for divergence. Coordinates automated and guided
reconciliation until the project reaches a verified **Fixpoint Reached** state.

## Protocol

> [!IMPORTANT] **Execution & Tooling Guardrails (Zero Delegation / Mandatory
> Dual Output)**: 1. **FORBIDDEN TOOLS ON INITIAL AUDIT**: NEVER invoke
> `invoke_subagent` or `ask_question` when `/arm-drift` is invoked. Do NOT
> delegate workspace scans to subagents and do NOT ask the user for scope/mode
> confirmation. 2. **MANDATORY VISIBLE CHAT MARKDOWN SUMMARY**: You MUST output
> visible markdown text in your chat response summarizing: (a) the VCS diff
> against the last checkpoint commit, (b) the audit of uncommitted changes
> against ADR scopes (`adr/*.md`), local rules (`GEMINI.md`, `AGENTS.md`), and
> manual testing runbooks (`manual_testing/*.md`), and (c) the drift findings or
> `Fixpoint Reached` status. Never emit tool calls alone without visible chat
> markdown text! 3. **MANDATORY TOOL CALLS (`run_command` & `write_to_file`)**:
> Alongside your visible markdown summary in the exact same turn, invoke
> `run_command` to execute the VCS diff against the last checkpoint commit
> (e.g., `git diff` or `hg diff`) AND invoke
> `write_to_file(TargetFile="arm_drift.md", CodeContent="...")` to generate the
> structured `arm_drift.md` report artifact.

### Step 1: Scope & Mode Resolution

1.  **Parse Arguments**:
    -   `--doc-only`: Phase 1 only (audit `product.md`, `tech-stack.md`, `workflow.md`, `terms.md`, `adr/*.md`, `manual_testing/*.md`, and active track specs without scanning code).
    -   `--code-only`: Phase 2 only (audit `.api_surface_cache.json`, public exports, and per-directory context boundaries).
    -   `--meta`: Phase 3 only (audit `install.sh`, `install.bat`, `plugin.json`, `marketplace.json`, and `README.md` packaging arrays and version agreement).
    -   `--scope=phase`: Incremental phase checkpoint mode. Scopes the audit to
        the files modified in the active track's current implementation phase
        (determined by reading the active track's `plan.md` and/or using VCS
        diff). Audits these changed files against touched ADRs and runbook
        scenarios.
    -   `--fix`: Automatically apply mechanical auto-fixes (installer arrays, version alignment, table freshness, and `.api_surface_cache.json` refresh).
    -   `--check`: Non-interactive CI / pre-submit validation mode (verifies fixpoint state and outputs pass/fail status).
    -   **Default Full-Sweep Execution (Zero-Argument Invocation)**: When
        `/arm-drift` is invoked without arguments (e.g., `/arm-drift`), default
        immediately to a **Full 3-Tier Audit** across all tiers. **NEVER** call
        `ask_question` to ask the user which scope/mode to run, what the active
        context directory is, or whether uncommitted changes exist. Immediately
        execute Step 2 (running the VCS diff against the last checkpoint commit,
        auditing uncommitted changes against ADR scopes, local rules, and manual
        testing runbooks, generating `arm_drift.md` via `write_to_file`, and
        summarizing drift items in chat).
2.  **Resolve Project Root**: Follow Armature Protocol Rule 7 to locate `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (armature or conductor).

### Step 2: Native 3-Tier Scan Execution

Execute the audit directly on the primary agent turn across the three tiers (or
the requested scope) using native file and VCS inspection tools (**NEVER**
delegate `/arm-drift` scans to `invoke_subagent`):

0.  **Direct VCS Diff & Uncommitted Change Audit (Mandatory First Step)**:

    -   Run or inspect the VCS diff (`hg diff`, `git diff`, `hg status`, `git
        status`) against the last checkpoint commit.
    -   Explicitly audit all uncommitted changes and modified files against
        active ADR scopes (`{PROJECT_CONTEXT_DIR}/adr/*.md`), local rules
        (`GEMINI.md`, `AGENTS.md`), and manual testing runbooks
        (`{PROJECT_CONTEXT_DIR}/manual_testing/*.md`).
    -   Generate the structured drift audit report file (`arm_drift.md` or
        `{ARTIFACT_DIR}/arm_drift.md`) via `write_to_file` and summarize all
        drift items (or Fixpoint status) directly in your visible chat response.

1.  **Incremental Phase Checkpoint Mode (`--scope=phase`)**:
    -   Determine which files and directories were modified or added in the
        active track's current phase (using the active track's `plan.md` and/or
        VCS diff).
    -   For each changed file:
        -   Identify matching ADRs in `{PROJECT_CONTEXT_DIR}/adr/` and directory context
            files (`GEMINI.md`, etc.). Verify that any new architectural
            decisions or constraints introduced by the changes are recorded as
            ADRs.
        -   Identify matching manual testing runbook scenarios in the active
            track's `manual_testing.md` or domain guides in
            `{PROJECT_CONTEXT_DIR}/manual_testing/`.
        -   If a new route handler, state guard, or major logic flow was added,
            verify it has corresponding manual verification test cases. If
            missing, report a `[WARNING]`.
        -   **Diff-to-Tag Cross-Verification (ADR 0010)**: Cross-check the
            empirical VCS diff (`hg diff` / `git diff`) against the active
            track's `manual_testing.md` scope tag. If `manual_testing.md` claims
            `[Micro-Verification Plan]` (or `Stateful 3-Part Fixture Triad
            deferred`) but the VCS diff modifies backend handlers (e.g., `.go`,
            `.py`, `.kt`), state machines, reactive stores, router navigation
            guards (`canActivate`), conditional auth/role gates
            (`*ngIf="user.isAdmin"`), or RPC/API callers, you MUST output an
            explicit warning line in your visible chat markdown prefixed with
            the literal tag `[WARNING]` (e.g., `- **[WARNING] Diff-to-Tag
            Mismatch:** Stateful/backend diff detected under visual-only
            [Micro-Verification Plan] tag...`) flagging the stateful/backend
            diff under a visual-only tag and recommending escalation of
            `manual_testing.md` to the **3-Part Fixture Triad**. Do NOT report a
            false `Fixpoint Reached` when this mismatch exists.
        -   Audit modified source tree context files for standard boundary tags.
    -   Report all findings in visible chat markdown with explicit `[WARNING]`
        tags without blocking work-in-progress code execution.

2.  **Phase 1: Project Documentation Fixpoint**:
    -   Verify minimum viable project files exist (`product.md`, `tech-stack.md`, `workflow.md`, `tracks.md`).
    -   Audit ADR sequence numbers, filename format (`NNNN-slug.md`), and MADR section schemas (`## Context`, `## Decision`, `## Confirmation`).
    -   Audit domain manual testing runbooks
        (`{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md`) and track runbooks
        (`{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md`) for
        standard `### Test <Domain>.<ID>` headers.
    -   **Scope-Aware Fixture Exemption (`[Micro-Verification Plan]` & Deferred
        Stamping — ADR 0010)**: Recognize explicit scope markers:
        `[Micro-Verification Plan]` in track runbooks and `Stateful 3-Part
        Fixture Triad deferred` in domain runbooks. When either marker is
        present, **exempt** the runbook from missing **3-Part Fixture Triad**
        (`Migration -> Seed -> Reset`) errors. Instead, validate that the
        runbook contains valid clickable `localhost` target URLs
        (`http://localhost:<PORT>/<path>`) and explicit visual assertions
        anchored on visible text or semantic ARIA roles.
    -   Audit active track specifications
        (`{PROJECT_CONTEXT_DIR}/tracks/<track_id>/spec.md`) for required `##
        Manual Verification Plan` (or verification strategy) sections.

3.  **Phase 2: Codebase & Implementation Fixpoint**:
    -   Compare public exported symbols against `.api_surface_cache.json` and `{PROJECT_CONTEXT_DIR}/terms.md`. Flag untracked API symbols.
    -   Inspect source tree context files (`GEMINI.md`, `CLAUDE.md`, `AGENTS.md`, `AGENT.md`) for standard `START`/`END` boundary tags and valid ADR references (accepting Armature Context and Conductor Context).
    -   **Pre-Closeout Diff-to-Tag Cross-Verification**: Cross-verify the active
        track's cumulative VCS diff against its `manual_testing.md` scope tag.
        If backend, state, auth-guard, or RPC files were modified under a
        `[Micro-Verification Plan]` tag, output an explicit `[WARNING]` line in
        chat markdown requiring runbook escalation to the 3-Part Fixture Triad.
    -   **Fixture & Schema Conformance**: Audit test fixtures, reset utilities,
        seed scripts, and migration files against schema definitions (Protobuf,
        SQL DDL, ORM models, TypeScript interfaces) to verify enum values, field
        names, and column constraints. Flag invalid enum strings and missing
        schema fields (exempting visual-only runbooks tagged with
        `[Micro-Verification Plan]` or `Stateful 3-Part Fixture Triad
        deferred`).
    -   **CLI Execution Constraints**: Verify that helper scripts wrapping
        database or service CLI tools respect process execution constraints
        (e.g., single-statement execution vs batch piping, authentication
        guards, timeouts).
    -   **Contract & Mutation Invariant Audit**: Cross-reference API/RPC
        precondition checks and handler validation rules with active ADRs and
        track specifications to verify required payload invariants.
4.  **Phase 3: Meta, Packaging & Release Manifest Fixpoint (Developer Mode)**:
    -   Verify all sub-skills in `skills/` are registered in `install.sh` (`SUB_SKILL_NAMES`), `install.bat`, and `README.md`.
    -   Verify rule files in `rules/` are in `RULE_FILE_NAMES` / `ALL_TARGET_FILES`.
    -   Verify setup asset templates in `skills/arm-setup/assets/` are in installer target arrays.
    -   Verify 100% version agreement across `install.sh` (`VERSION=`), `install.bat` (`set "VERSION="`), `plugin.json` (`"version"`), `.claude-plugin/marketplace.json`, and `CHANGELOG.md`.
5.  **Phase 4: Legacy-Boundary Context Fence Diff Firewall & Stale Fence Garbage
    Collection**:
    -   *Immediate Turn 1 Markdown Report First (Zero Tool-Only Stalls)*: When
        `[Workspace Context...]`, `[Cumulative Branch Diff...]`, or `[Filesystem
        Check...]` is provided in the user prompt, you are STRICTLY FORBIDDEN
        from calling `view_file` or `grep_search` on any file (including
        modified modern files like `new_component.ts`, `tech-stack.md`, or
        `product.md`) without outputting your complete Fixpoint Audit Report in
        markdown first! You MUST output your complete markdown Fixpoint Audit
        Report—including the active Deprecated Code Boundary banner (Adaptive
        Verbosity: full `> [!NOTE] **Working in ...**` callout on Turn 1 or
        compact `> 🛡️ **Deprecated code boundary active:** ...` on Turn 2+),
        explicit
        confirmation that cumulative branch changes (`git diff main...HEAD` or
        `git diff main...HEAD`) were audited, explicit statement that whole-file
        deletions (`status R/!/D`) inside legacy-fenced directories are exempt
        to support decommissioning cleanup, and a clean Fixpoint pass (`✅
        [Fixpoint Reached]`)—directly in your text response on Turn 1!
    -   **Cumulative Branch Diff Auditing**: Always audit cumulative branch
        changes against the base revision (`git diff main...HEAD` in Git/Mercurial
        or `git diff main...HEAD` in Git) against active legacy fences in
        `{PROJECT_CONTEXT_DIR}/tech-stack.md` (`## Legacy & Deprecated
        Boundaries`) and active track `metadata.json` (`legacy_fences`).
    -   **Unauthorized Additions/Modifications**: Any added (`A`) or modified
        (`M` with $>0$ added lines) file inside an active legacy-fenced
        directory without an explicit entry in `fence_overrides` MUST be flagged
        as a **`[BLOCKING] Legacy Fence Violation`**, directing remediation to
        the `<modern_replacement>`.
    -   **Decommissioning & Deletion Exemption (CRITICAL)**: Whole-file
        deletions (`status R` removed or `!` missing/deleted in Mercurial;
        `status D` deleted in Git) and pure line removals (`0` added lines /
        dead-code cleanup) inside legacy-fenced directories are **automatically
        exempt** from Legacy Fence violations to support frictionless
        decommissioning cleanup CLs (`hg rm` / `git rm`). Explicitly state in
        your markdown response that whole-file deletions (`status R/!/D`) inside
        legacy-fenced directories are exempt and report a clean Fixpoint pass
        for decommissioning deletions.
    -   **Stale Fence Garbage Collection (`VAL_LF_04`)**: Check whether each
        fenced `Deprecated Path` in `tech-stack.md` or `metadata.json` still
        exists on disk (`[ ! -d "<deprecated_path>" ]`). If a fenced directory
        no longer exists on disk:
        1.  Output a **`[DRIFT] Stale Legacy Fence`** alert in your markdown
            report clearly identifying which legacy fence is stale
            (`<deprecated_path>`) and explicitly stating that all active fences
            whose directories still exist on disk (e.g.,
            `packages/legacy_app/`) are **preserved** and remain
            active.
        2.  Invoke `ask_question` in that exact same turn offering 1-click
            auto-pruning to remove the obsolete entry from
            `armature/tech-stack.md` (`"(Recommended) Auto-prune stale legacy
            fence <deprecated_path> from armature/tech-stack.md"`).

**Render the Fixpoint Audit Report**: Always print the complete audit results
directly in your markdown chat response before any tool call:

-   If no discrepancies exist: Print `✅ [Fixpoint Reached] Zero drift detected
    across all tiers.` (or in the active phase scope).
-   If discrepancies exist: Group findings by phase/scope and prefix every
    finding line with its literal bracketed severity tag (`[ERROR]`,
    `[WARNING]`, `[INFO]`) and indicate `[Auto-Fixable]` status. Never omit the
    literal `[WARNING]` or `[ERROR]` tag string when reporting a discrepancy or
    calling `ask_question`.

### Step 3: Interactive Reconciliation & Remediation

1.  **Zero Drift Detected**:
    -   Display: `✅ [Fixpoint Reached] Zero drift detected.`
    -   Conclude execution.

2.  **Mechanical Drift Detected**:
    -   Display detected mechanical issues.
    -   If `--fix` flag was provided, apply fixes directly using file editing tools.
    -   Otherwise, prompt user via `ask_question`: "Mechanical drift detected in packaging/manifests. Apply automatic fixes?" with options `["(Recommended) Apply mechanical fixes", "Review discrepancies first", "Skip for now"]`.
    -   Apply approved fixes surgically.

3.  **Semantic / Architectural Drift Detected**:
    -   Display architectural divergence findings with file paths, code snippets, and matching ADR/rule quotes.
    -   Prompt via `ask_question` with structured options: `["Update code to match ADR", "Update ADR to reflect new decision", "Acknowledge as tech debt in spec.md", "Show me the details"]`.
    -   Apply chosen resolution and re-run check to verify.
