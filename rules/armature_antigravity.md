---
trigger: always_on
description: Armature Antigravity UX adapter - maps interaction requirements onto Antigravity native rendering
---

# Armature Antigravity UX Adapter (View Layer)

## Interactive Interview & `ask_question` Contract

-   **Two-Part Turn Contract & Strict Part Ordering (`content` -> Draft Writes
    -> `ask_question`):** Every interactive question, brownfield setup gate,
    Need-More-Context / `"zoom out"` / `"too vague"` clarification re-tee,
    Devil's Advocate finding, ADR triage gate, shared-environment /
    destructive-command safety gate, and spec/plan review gate MUST include in
    the **same response** in strict order:
    1.  **Visible markdown text FIRST (`content` — Never Start With a Tool
        Call):** Always emit the complete visible markdown turn body into
        `content` **before** calling ANY tool (`write_file`, `write_to_file`,
        `edit_file`, `replace_file_content`, or `ask_question`). Once any tool
        call begins, no visible `content` can follow in that turn. Internal
        reasoning (`thinking` / `thought`) is invisible to the user—keep
        `thinking` to a brief outline (never draft the full markdown turn
        verbatim inside `thinking`), and always end `thinking` with *"Now emit
        visible `content` first, then any draft file writes, then
        `ask_question`"* (never end `thinking` on word-count math alone).
    2.  **Working-draft file writes SECOND (when applicable) & native
        `ask_question` LAST (`questions: [...]` Wrapper):** After emitting
        visible `content`, invoke any `spec.md` / `metadata.json` /
        `active_context.md` draft writes, and invoke `ask_question` with
        `{"questions": [{"question": "...", "options": [...]}]}` (`question`
        $\le 15$ words, no markdown; Option 1 prefixed with `"(Recommended) "`
        and options `1..K` matching `<Option name>` in 1:1 order, never
        `Pick N if …` sentences; no manual `"Other"` option). Never end an
        interactive or safety-confirmation turn with markdown prose alone.
-   **Zero `ask_question` Abandonment Recovery:** If the user reports *"you
    didn't answer me in chat"* or *"I only see the question box"*, re-emit the
    visible markdown explanation into `content` AND invoke `ask_question` in the
    same turn. Never fall back to plain-text prompts like *"Reply with 1, 2, or
    3 in chat"*.
-   **Streaming Flush Before Heavy `write_file` Calls:** Keep Step 6/7 visible
    chat summaries concise (`40-200` words) and end with `\n\n_Materializing the
    track artifacts and opening the approval prompt..._\n\n` before calling
    `write_file` and `ask_question`.

## Dual Artifact Strategy & Async Delegation

-   **Dual Artifact Strategy:** Write canonical track files (`spec.md`,
    `plan.md`, `manual_testing.md`) to `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/`
    and symlink them into the Antigravity artifact directory for review.
-   **Asynchronous Delegation:** Route parallel disjoint phases to isolated
    worktree subagents (`workspace: "share"` / `Task`) where only the
    orchestrator updates shared track files (`plan.md`, `metadata.json`,
    `tracks.md`, `.api_surface_cache.json`), and route sequential phases or
    heavy multimodal tasks to `invoke_subagent` with a 90-second conditional
    `schedule` timer.
