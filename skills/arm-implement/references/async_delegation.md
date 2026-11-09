# Asynchronous Subagent Delegation & Phase Execution Routing

This reference defines phase-level subagent routing (`ADR 0013`) for `/arm-implement`.

## 1. Parallel Isolated Worktrees — Independent Disjoint Phases

- Use when an implementation phase contains multiple independent tasks operating
  on non-overlapping source and test directories.
- **Antigravity**: Dispatch parallel `worker` subagents in a single
  `invoke_subagent` call with `Workspace: "share"` for each entry to provision
  isolated working copies, and arm `schedule(DurationSeconds=90,
  TimerCondition="any")`.
- **Claude Code**: Dispatch parallel `Task(prompt="...",
  subagent_type="worker")` subagents in isolated `git worktree` checkouts.
- **Coordinator-Only Updates to Shared Track Files:** Parallel workers must only
  edit their assigned source and test files and must NEVER modify shared track
  files (`plan.md`, `metadata.json`, `tracks.md`, or `.api_surface_cache.json`).
  Only the orchestrator updates `plan.md` checkboxes and refreshes
  `.api_surface_cache.json` after merging and verifying worker worktrees at
  phase completion.

## 2. Single Worker — Sequential Coupled Phases & Heavy Investigations

- Use when phase tasks share state dependencies or touch overlapping files, or
  when offloading standalone heavy multimodal inputs (e.g., screencast `.webm`
  files) or broad codebase discovery:
  - **Claude Code**: Dispatch via `Task(prompt="...", subagent_type="explorer")`
    (or `subagent_type="worker"`).
  - **OpenCode**: Route deep codebase exploration to `@explore` or `@scout`.
  - **OpenAI Codex**: Delegate discovery or implementation work to `explorer`
    (`role="explorer"`) or `worker` (`role="worker"`).
  - **Antigravity**: Dispatch via `invoke_subagent(TypeName='explorer', ...)`
    (or `TypeName='worker'`) and concurrently call `schedule(DurationSeconds=90,
    TimerCondition="<subagent_id>", Prompt="Check subagent progress and post a
    20-block progress bar update in main chat.")` in the same turn.
  - **Single-Threaded Harnesses (Cursor, Aider)**: Execute long-running jobs in
    the background (`run_in_background` or terminal `command & > /tmp/task.log`)
    with proactive status logging.
