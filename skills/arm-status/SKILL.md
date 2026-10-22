---
name: arm-status
description: Get a high-level overview of project progress across all tracks. Use when asked for project status, track progress, what's done, or run /arm-status.
persona: Armature Observer
---

<!-- disableFinding(LINE_OVER_80) -->

# /arm-status — View Project Progress

**Purpose:** Get a high-level overview of project progress.

## Protocol

> [!IMPORTANT] **Mandatory Single-Turn Execution & Dual Output**: When
> `/arm-status` is invoked (especially when workspace context is already
> provided inline in the prompt), you MUST complete all steps in a **single
> turn**: (1) output your visible markdown status summary in chat first, AND (2)
> in that **exact same turn**, invoke `write_to_file` / `replace_file_content`
> to auto-update any Tier A mechanical/documentation drift
> (`armature/tracks.md`, `armature/index.md`), invoke
> `write_to_file(TargetFile="arm_status.md", ...)` to write the status artifact,
> and invoke `ask_question` for Step 6 Next Steps! Never stop with markdown text
> alone without emitting the required tool calls, and never emit bare tool calls
> without visible markdown text.

1.  **Context Resolution & Setup Check:**
    -   Resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (armature or conductor) per `armature_protocol.md` §7.
    -   Verify that the following core files exist:
        -   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md`
        -   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/product.md`
        -   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tech-stack.md`
        -   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/workflow.md`

    If any of these files are missing, halt execution and inform the user that
    the Armature context is incomplete.

2.  **Read and Parse Tracks:**

    -   Read `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md`.
    -   Parse the tracks. You must support BOTH the standard format (`- [ ] **Track:`) AND the legacy format (`## [ ] Track:`).
    -   Note the status of each track based on its checkbox:
        -   `[x]` = ✅ Complete
        -   `[~]` = 🔄 In Progress
        -   `[ ]` = ⬜ Pending

3.  **Analyze Task-Level Progress:**

    -   For each track, read its
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/plan.md` to get task-level
        progress.
    -   Extract current phase and task (marked `[~]`), next pending task
        (marked `[ ]`), and explicitly noted blockers.

4.  **Auto-Update & Notify Mechanical Drift by Default (Pre-Report Auto-Heal):**

    -   Before generating `arm_status.md`, audit
        `{PROJECT_CONTEXT_DIR}/tracks.md`, `{PROJECT_CONTEXT_DIR}/index.md`, and
        track `plan.md` / `metadata.json` files for **Tier A — Mechanical &
        Deterministic Documentation Drift**:
        1.  **Stale Track Status Reconciliation:** A track is marked `[~]` (In
            Progress / In Review) in `tracks.md` or `"in_progress"` in
            `metadata.json`, yet 100% of tasks in its `plan.md` are marked `[x]`
            and its implementation commit is already merged on `HEAD`.
        2.  **Markdown Table Wrapping & Formatter Guards:** A Markdown table in
            `tracks.md` or `index.md` was wrapped into multi-line `: :` grid
            continuations by `mdformat` or lacks
            `<!-- mdformat off(prevent table wrapping) -->` /
            `<!-- disableFinding(LINE_OVER_80) -->` guards.
        3.  **Missing Registry / Index Links:** Track directories in
            `{PROJECT_CONTEXT_DIR}/tracks/<track_id>/` or ADR files in
            `{PROJECT_CONTEXT_DIR}/adr/NNNN-*.md` exist on disk (or in a known
            synced sibling workspace) but are missing from `tracks.md` or
            `index.md`.
        4.  **Additive API Surface Cache Freshness:** `.api_surface_cache.json`
            is out of date with respect to newly added public exports (with zero
            breaking symbol removals).
    -   **Default Action — Auto-Update & Notify in the Same Turn (Zero
        Permission Prompt):** Unless `--check` or `--report-only` was explicitly
        passed, you MUST **automatically apply all Tier A mechanical fixes
        in-place** using `replace_file_content` or `write_to_file` in the
        **exact same turn** before writing `arm_status.md`.
        -   **NEVER** act as a passive detect-only observer for mechanical
            drift, **NEVER** leave Tier A drift unapplied with a `"⚠️ Drift
            Detected — run /arm-drift"` warning, and **NEVER** ask the user for
            permission to fix mechanical status/table/index drift.
        -   In both `arm_status.md` and your visible chat markdown response,
            report: `**Fixpoint Health:** ✅ Fixpoint Reached (N mechanical drift
            issue(s) auto-updated)` followed by a concise bulleted list of the
            exact updates applied (e.g., `- Auto-updated track <track_id> status
            [~] → [x] Completed in tracks.md`, `- Restored single-line Markdown
            table formatting with <!-- mdformat off --> in tracks.md`).
    -   **Tier B — Semantic / Architectural Contradictions (Never Silently
        Overwritten):** If the workspace contains a **Tier B** semantic
        contradiction (e.g., source code violating an approved `ADR` or
        `spec.md`, a breaking public API removal, or an unauthorized edit inside
        a legacy-fenced `<deprecated_path>`), auto-apply all Tier A mechanical
        fixes first, never auto-overwrite approved `spec.md` / `adr/*.md` files,
        and report `**Fixpoint Health:** ⚠️ Semantic Drift Requires Decision (M
        issue(s); N mechanical issue(s) auto-updated)`.

5.  **Generate the Enhanced Status Summary:** Write the status summary as an
    artifact (`arm_status.md`, `ArtifactType: walkthrough` using
    `write_to_file`) and present via `notify_user` with `PathsToReview`.

    Include the following structured information in the artifact:

    **Overview:**

    -   **Current Date/Time:** `<current timestamp>`
    -   **Project Status:** High-level assessment ("On Track", "Behind
        Schedule", "Blocked") based on tasks and blockers
    -   **Fixpoint Health:** Current drift health status after auto-healing Tier
        A mechanical drift (`"✅ Fixpoint Reached (0 drift)"`, `"✅ Fixpoint
        Reached (N mechanical drift issue(s) auto-updated)"` with a bulleted
        list of applied fixes, or `"⚠️ Semantic Drift Requires Decision (M
        issue(s))"` for Tier B architectural contradictions)
    -   **Current Phase and Task:** The specific phase/task marked `[~]` in the
        active track
    -   **Next Action Needed:** The next `[ ]` pending task
    -   **Blockers:** Items explicitly marked as blockers
    -   **Phases:** Total phases
    -   **Tasks:** Total tasks
    -   **Progress:** tasks_completed / tasks_total (percentage%)

    **Track Registry Summary:** Display in single-line Markdown table format
    (never use ambiguous commit parentheticals on unstarted tracks; use
    `⬜ Pending (Specs Only — Not Started)` when a track has specs/plans only and
    `0` completed implementation tasks):

    ```markdown
    ## Project Status

    ### Track Registry
    | # | Track | Status |
    |---|-------|--------|
    | 1 | <Track Title> | ✅ Complete |
    | 2 | <Track Title> | 🔄 In Progress |
    | 3 | <Track Title> | ⬜ Pending (Specs Only — Not Started) |
    ```

    **Phase/Task Breakdown:** For each in-progress track, display the plan
    structure:

    ```markdown
    ### Active Track: <track_name>
    - Phase 1: ✅ Complete
    - Phase 2: 🔄 In Progress
      - [x] Task 1
      - [x] Task 2
      - [~] Task 3 (current)
      - [ ] Task 4
      - [ ] Task 5
    - Phase 3: ⬜ Pending
    ```

    **Summary Statistics:** Total tracks: N, Completed: N, In progress: N, Pending: N.

6.  **Next Steps:** Use `ask_question` to present structured choices (since Tier
    A mechanical drift is already auto-updated in Step 4, recommend the next
    productive engineering step first):

    1.  (Recommended) Implement the current/next track (/arm-implement)
    2.  Start a new track (/arm-new-track)
    3.  Review completed work (/arm-review)
    4.  Run full 3-tier fixpoint audit (/arm-drift)
