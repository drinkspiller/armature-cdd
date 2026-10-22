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
> Dual Output)**: 1. **FORBIDDEN DELEGATION & SCOPE PROMPTS**: NEVER invoke
> `invoke_subagent` when `/arm-drift` is invoked, and NEVER invoke
> `ask_question` to ask the user which scope/mode to run or whether to apply
> Tier A mechanical fixes (Tier A fixes auto-update in-place by default!). Only
> invoke `ask_question` at the end of the turn when **Tier B Semantic /
> Architectural Contradictions (`Step 3.3`)** or **Stale Legacy Fence Garbage
> Collection (`VAL_LF_04`)** require human decision. 2. **MANDATORY VISIBLE CHAT
> MARKDOWN SUMMARY**: You MUST output visible markdown text in your chat
> response summarizing: (a) the VCS diff against the last checkpoint commit, (b)
> the audit of uncommitted changes against ADR scopes (`adr/*.md`), local rules
> (`GEMINI.md`, `AGENTS.md`), and manual testing runbooks
> (`manual_testing/*.md`), and (c) the auto-updated Tier A fixes, remaining Tier
> B findings, or `Fixpoint Reached` status. Never emit tool calls alone without
> visible chat markdown text! 3. **MANDATORY SAME-TURN TOOL CALLS (Tier A
> Auto-Update + `arm_drift.md`)**: Unless `--check` / `--report-only` was
> passed, in the **exact same turn** alongside your visible markdown summary,
> you MUST invoke `write_to_file` or `replace_file_content` to **auto-update all
> detected Tier A mechanical/documentation drift files in-place** (`tracks.md`,
> `index.md`, `terms.md`, `.api_surface_cache.json`, `install.sh`,
> `plugin.json`, and `arm_status.md` if present) AND invoke
> `write_to_file(TargetFile="arm_drift.md", CodeContent="...")` to generate the
> structured `arm_drift.md` report artifact (plus `run_command` for VCS diff
> when diff context is not already provided inline). Never stop with markdown
> text alone when file mutations are required!

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
    -   `--fix`: Explicit alias for the default behavior — automatically apply
        all Tier A mechanical and deterministic documentation auto-updates
        in-place (stale track statuses, Markdown table single-line formatting,
        missing `index.md` / `tracks.md` links, `.api_surface_cache.json`
        refresh, additive `terms.md` symbol sync, and installer/packaging
        manifest arrays) and notify the user.
    -   `--check` (or `--report-only` / `--dry-run`): Non-interactive read-only
        CI / pre-submit validation mode. Verifies fixpoint state, outputs
        pass/fail status, and performs **zero** repository file mutations (never
        calling `replace_file_content` or `write_to_file` on repository files).
    -   **Default Full-Sweep & Auto-Update Execution (Zero-Argument
        Invocation)**: When `/arm-drift` is invoked without `--check` /
        `--report-only` (e.g., bare `/arm-drift`), default immediately to a
        **Full 3-Tier Audit with Automatic Tier A Mechanical Remediation &
        Notification**. **NEVER** call `ask_question` to ask the user which
        scope/mode to run, whether to apply mechanical fixes, what the active
        context directory is, or whether uncommitted changes exist. Immediately
        execute Step 2 and Step 3 in a single turn: run the VCS diff against the
        last checkpoint commit, audit uncommitted changes against ADR scopes,
        local rules, and manual testing runbooks, **auto-update all Tier A
        mechanical/documentation drift in-place** via `write_to_file` /
        `replace_file_content`, generate `arm_drift.md`, refresh
        `{ARTIFACT_DIR}/arm_status.md` if present, and summarize all applied
        updates and remaining Tier B findings in chat.
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
    -   *Immediate Turn 1 Markdown Report & Same-Turn Execution First (Zero
        Tool-Only Stalls)*: When `[Workspace Context...]`, `[Cumulative Branch
        Diff...]`, or `[Filesystem Check...]` is provided in the user prompt,
        you are STRICTLY FORBIDDEN from calling `view_file` or `grep_search` on
        any file (including modified modern files like `new_component.ts`,
        `tech-stack.md`, or `product.md`) without outputting your complete
        Fixpoint Audit Report in markdown first! You MUST output your complete
        markdown Fixpoint Audit Report—including the active Deprecated Code
        Boundary banner on Turn 1 if not yet shown in the session (`> [!NOTE]
        **Working in ...**` callout on Turn 1 only; strictly silent on Turn 2+
        and intermediate tool steps), explicit confirmation that cumulative
        branch changes (`git diff main...HEAD`) were audited, explicit statement
        that whole-file deletions (`status R/!/D`) inside legacy-fenced
        directories are exempt to support decommissioning cleanup, and a clean
        Fixpoint pass (`✅ [Fixpoint Reached]`)—directly in your text response on
        Turn 1, AND in that **exact same turn** invoke `write_to_file` /
        `replace_file_content` to auto-update any Tier A mechanical drift files,
        write `arm_drift.md`, and refresh `arm_status.md` (if present)! Never
        stop with markdown text alone when file mutations or `ask_question` (for
        Tier B semantic contradictions or Stale Fence GC) are required.
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
        decommissioning cleanup commits (`git rm` / `hg rm`). Explicitly state in
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

### Step 3: Automatic Mechanical Remediation & Semantic Disambiguation

1.  **Zero Drift Detected**:
    -   Display: `✅ [Fixpoint Reached] Zero drift detected.`
    -   Conclude execution.

2.  **Tier A — Mechanical & Deterministic Documentation Drift Detected
    (Auto-Update & Notify by Default)**:

    -   **Included Tier A Drift Categories**:
        1.  **Stale Track Statuses**: Track marked `[~]` (In Progress / In
            Review) in `tracks.md` or `"in_progress"` in `metadata.json` when
            100% of tasks in its `plan.md` are marked `[x]` and its
            implementation commit/CL is already submitted on `HEAD` ->
            automatically update to `[x]` (`Completed`).
        2.  **Markdown Table Wrapping & Formatter Guards**: Tables in
            `tracks.md` or `index.md` wrapped into multi-line `: :` grid
            continuations by `mdformat` -> automatically restore single-line
            pipe rows (`| col | col |`) wrapped in
            `<!-- mdformat off(prevent table wrapping) -->` and
            `<!-- disableFinding(LINE_OVER_80) -->`.
        3.  **Missing Registry / Index Links**: Existing track folders
            (`tracks/<track_id>/`) or ADR files (`adr/NNNN-*.md`) missing from
            `tracks.md` or `index.md` -> automatically synchronize rows and
            links.
        4.  **Additive API Surface Cache & Glossary Sync**: Newly added public
            exported symbols missing from `.api_surface_cache.json` or
            `terms.md` (with zero breaking removals) -> automatically update
            `.api_surface_cache.json` and append symbol definitions to
            `terms.md`.
        5.  **Packaging & Release Manifest Arrays**: Out-of-sync installer
            arrays (`SUB_SKILL_NAMES`, `RULE_FILE_NAMES`, `ALL_TARGET_FILES`) or
            version strings across `install.sh`, `install.bat`, `plugin.json`,
            `.claude-plugin/marketplace.json`, and `README.md` -> automatically
            align arrays and versions.
        6.  **Live `arm_status.md` Artifact Lockstep Sync**: If
            `{ARTIFACT_DIR}/arm_status.md` (or `arm_status.md`) exists in the
            conversation session and reported prior drift, automatically update
            `arm_status.md` so `Fixpoint Health` reflects `✅ Fixpoint Reached (N
            mechanical drift issue(s) auto-updated)`.
    -   **Default Action (When `--check` / `--report-only` Is NOT Passed)**:
        -   **Automatically apply all Tier A fixes in-place** using
            `replace_file_content` or `write_to_file` in the **exact same turn**
            (`--fix` is the default behavior on `/arm-drift`; never call
            `ask_question` to ask permission to apply Tier A mechanical fixes).
        -   Notify the user in both visible chat markdown and `arm_drift.md`
            with: `✅ [Fixpoint Reached] Auto-updated N mechanical drift
            issue(s):` followed by a bulleted list of every file and adjustment
            applied.
    -   **Read-Only CI Mode (`--check` / `--report-only` / `--dry-run`)**:
        -   When `--check` or `--report-only` is passed, perform **zero**
            repository file mutations (never call `replace_file_content` or
            `write_to_file` on repository files) and report the detected Tier A
            / Tier B drift items with a non-zero / failing check status.

3.  **Tier B — Semantic / Architectural Contradictions, Breaking Removals &
    Fence Decisions (Never Silently Overwritten)**:

    -   **Included Tier B Categories**:
        1.  **Code-vs-ADR or Code-vs-Spec Contradiction (`CB2`)**: Source code
            violates an active ADR in `adr/*.md` or an approved `spec.md` (e.g.,
            adding a direct REST mutation where ADR mandates WebSocket). Never
            silently rewrite an approved `ADR` or `spec.md` to mask code
            divergence.
        2.  **Breaking Public API Symbol Removal**: A previously exported public
            symbol in `.api_surface_cache.json` was removed or incompatibly
            altered (`[ERROR] Breaking API Surface Change` requiring a **MAJOR**
            semantic version bump recommendation).
        3.  **Diff-to-Tag Mismatch (`ADR 0010`)**: Stateful/backend/guard/RPC
            changes under a `[Micro-Verification Plan]` tag (`[WARNING]
            Diff-to-Tag Mismatch` requiring escalation of `manual_testing.md` to
            the **3-Part Fixture Triad**).
        4.  **Legacy Fence Violations (`[BLOCKING]`) & Stale Fence Garbage
            Collection (`[DRIFT] Stale Legacy Fence`, `VAL_LF_04`)**:
            Unauthorized additions/edits inside `<deprecated_path>` (`CB1`:
            never auto-edit fenced files) or a fenced directory deleted from
            disk (`VAL_LF_04`: prompt via `ask_question` to confirm 1-click
            auto-pruning from `tech-stack.md` while preserving active fences).
    -   **Action**: Auto-apply any co-occurring Tier A mechanical fixes first,
        display the Tier B architectural/semantic findings with file paths, code
        snippets, and matching ADR/rule quotes, and (when interactive resolution
        is required) prompt via `ask_question` with structured options:
        `["(Recommended) Update code to match ADR", "Update ADR to reflect new
        decision", "Acknowledge as tech debt in spec.md", "Show me the
        details"]`.
