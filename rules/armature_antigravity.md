---
trigger: always_on
description: Armature Antigravity UX adapter - maps interaction requirements onto Antigravity native rendering
---

# Armature Antigravity UX Adapter (View Layer)

## Interactive Interview & `ask_question` Contract

-   **End Waiting Turns With a Question:** Whenever a turn ends waiting on the
    user (a decision, a confirmation, or an action only the user can take, such
    as restarting a tunnel, approving an upload, or choosing between next
    steps), end it with `ask_question`, or with a plain-text question when
    Plain-Text Question Mode applies. Never end a turn on `- Pick N if …`
    bullets, numbered options, or *"let me know when"* with `0` tool calls;
    writing options in chat does NOT ask the user unless `ask_question` is
    invoked at the end of that same step. Give options that cover the expected
    replies (for example, "Tunnel is back, continue" or "Work from the local
    copy instead"). This applies in any conversation, not only during Armature
    interviews.
-   **The User Must See the Explanation (Same-Step Visible Text &
    End-of-`thinking` Cue):** The user sees only visible chat text and the
    question box; internal reasoning (`thinking` / `thought`) is never shown.
    The response step that calls `ask_question` must itself carry the visible
    explanation in `content`, even when earlier steps in the same turn already
    wrote draft files or ran commands (visible text from an earlier step does
    not count if it was empty). Write the options, trade-offs, and
    recommendation as visible text, not as a summary inside `thinking`. If you
    realize you have just written the user-facing explanation inside `thinking`,
    write it again as visible text before calling the tool. Always finish
    `thinking` by explicitly planning both parts (e.g., *"Now emit visible
    `content` first, then any draft writes, then call `ask_question`"*); never
    end `thinking` on option trade-offs or word-count checks alone, which causes
    models to stop after the `- Pick` bullets and drop the `ask_question` tool
    call. Order within that step: visible text, then any draft writes, then
    `ask_question` with `{"questions": [{"question": "...", "options": [...]}]}`
    (Option 1 prefixed with `"(Recommended) "`, options matching the numbered
    `<Option name>` lines 1:1, no manual `"Other"` option).
-   **Question First, Bookkeeping in the Same Step:** When a turn has to record
    something (append a settled decision, update a draft, run a quick command)
    and then ask, don't spend separate steps on the bookkeeping first. Put the
    whole visible turn (the `# <Topic>` heading and body) at the start of one
    step, then the bookkeeping calls, then `ask_question`, all in that step.
    Don't check whether a draft file exists before asking; create or append to
    it in the asking step. If earlier steps in the turn already ran tools,
    write the asking step's visible text as if it were the whole reply,
    starting with the `# <Topic>` heading. A first-person summary of the
    options or recommendation in `thinking` (*"I'm recommending option 1..."*)
    means the explanation went to the wrong place: put it in visible text
    before calling the tool.
-   **Self-Contained Question Box:** Some models and hosts drop or hide the chat
    text next to the box, so the box must stand on its own. Use `question` for
    one or two plain sentences (up to about 40 words, no markdown) that name the
    decision and the recommendation. Keep each option label the same as its
    numbered chat option name, and make those names concrete enough to read
    alone (say what happens, not a slogan). Put extra context in `question`, not
    in the options.
-   **Blank-Box Recovery (Box Stays the Default):** The `ask_question` box is
    the preferred way to ask. If a box came back `User Skipped` or empty, or the
    user says they couldn't see the explanation (*"I only see the question
    box"*, *"you didn't answer me in chat"*), give the full explanation as
    visible text and ask again with `ask_question` on that same step. Keep using
    the box for later questions.
-   **Plain-Text Question Mode (Fallback Only):** Ask as numbered plain text in
    chat, without `ask_question`, only when the user asks you to stop using the
    box or to ask in chat (keep doing so until they ask for the box again), when
    `ask_question` is unavailable, or when a recovery box also came back blank
    or skipped (for that one question), including when the Armature
    `ask_question` guard hook blocks a blank box a second time. End the turn
    after the question so the
    user can reply. Plain-text mode replaces only the delivery; the content
    (options, recommendation, one question at a time) stays the same.
-   **Streaming Flush Before Heavy `write_file` Calls:** Keep Step 6/7 visible
    chat summaries concise (`40-200` words) and end with `\n\n_Materializing the
    track artifacts and opening the approval prompt..._\n\n` before calling
    `write_file` and `ask_question`.

## Dual Artifact Strategy & Async Delegation

-   **Dual Artifact Strategy:** Write canonical track files (`spec.md`,
    `plan.md`, `manual_testing.md`) to `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/`
    and symlink them into the artifact directory for review.
-   **Asynchronous Delegation (Orchestrator-Worker Invariant):** Keep the
    primary conversation responsive by routing parallel disjoint phases and
    heavy multimodal or codebase discovery tasks to isolated workers, where only
    the orchestrator updates shared track files (`plan.md`, `metadata.json`,
    `tracks.md`, `.api_surface_cache.json`):
    -   *Claude Code*: `Task(prompt="...", subagent_type="worker")` (or
        `subagent_type="explorer"`) in isolated `git worktree` checkouts.
    -   *OpenCode*: `@explore` or `@scout`.
    -   *OpenAI Codex*: `explorer` (`role="explorer"`) or `worker`
        (`role="worker"`).
    -   *Antigravity*: `invoke_subagent` with `Workspace: "share"` for parallel
        disjoint phases, or a 90-second conditional `schedule` timer for
        sequential and heavy multimodal tasks.
    -   *Single-Threaded Harnesses (Cursor, Aider)*: Background shell execution
        (`&`) with status logging.
