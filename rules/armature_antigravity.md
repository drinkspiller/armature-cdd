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
    Plain-Text Question Mode applies. Never end a turn on option cards,
    `- Pick N if …` bullets, or *"let me know when"* with `0` tool calls;
    writing options in chat does not ask the user unless `ask_question` is
    called in that same step. Give options that cover the expected replies (for
    example, "Tunnel is back, continue" or "Work from the local copy instead").
    This applies in any conversation, not only during Armature interviews.
-   **Full-Context Question Box (One-Line Chat Lead-In):** `ask_question`'s
    `question` field renders Markdown and sanitized HTML inside a scrollable
    Antigravity chat UI card (across Antigravity IDE, Hub, and Desktop) and is
    the one channel every model family fills reliably without hooks. Whenever a
    turn calls `ask_question`:

    -   **Chat (`content`):** Write **only one short lead-in sentence** naming
        the topic (for example, `"One decision to settle before moving on: how
        background indexing shares the rate limit."`). Do **not** print option
        cards, `Pros`/`Cons` lists, or `- Pick N if …` bullets in chat—writing
        full option cards in chat causes Gemini-family models to treat the turn
        as finished and skip `ask_question`, while Claude models often drop chat
        text next to tool calls.
    -   **Question box (`questions[0].question`, Antigravity GUI HTML):**
        Put the full turn inside `question` (target `~160-250` words of visible
        copy, default cap `~300` words unless a safety caveat needs more; omit
        `Implications:`, redundant bottom `Recommendation:` blocks, and
        `Safe to ignore for now:` lines; fold each option's operational impact—
        and on Option 1, the recommendation rationale—into its indented
        one-sentence summary):

        ```html
        ## <Topic>

        <span style="font-size: 15px;">2-3 sentence plain-English overview (no code identifiers on Pass 1; weave any prior settled choice into the opening clause) ending with The choice here is <X>.</span>

        <div class="mt-5 mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Options</div>

        <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
        <p class="text-lg font-semibold text-foreground">1. <Option 1 name> <span style="font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: 999px; background: color-mix(in srgb, var(--success) 16%, transparent); color: var(--success); margin-left: 6px; vertical-align: middle;">Recommended</span></p>
        <div class="pl-5 flex flex-col gap-1.5">

        <One-sentence plain-English summary explaining what Option 1 does and why it is recommended.>

        <div class="flex flex-col gap-1 text-secondary-foreground">

        <span style="color: var(--foreground); font-weight: 600;">Pros:</span> <single-clause benefit>

        <span style="color: var(--foreground); font-weight: 600;">Cons:</span> <single-clause trade-off>

        </div>
        </div>
        </div>
        <div class="flex flex-col gap-1">
        <p class="text-lg font-semibold text-foreground">2. <Option 2 name></p>
        <div class="pl-5 flex flex-col gap-1.5">

        <One-sentence plain-English summary explaining what Option 2 does and what happens.>

        <div class="flex flex-col gap-1 text-secondary-foreground">

        <span style="color: var(--foreground); font-weight: 600;">Pros:</span> <single-clause benefit>

        <span style="color: var(--foreground); font-weight: 600;">Cons:</span> <single-clause trade-off>

        </div>
        </div>
        </div>
        </div>
        ```

        Render the `Options` eyebrow as a `<div>` (not `<p>`, because the panel
        resets `<p>` vertical margins) and keep options container-free with bold
        `Pros:`/`Cons:` (never `+`/`-`). **CLI / Plain-Markdown Fallback:** In
        terminal/CLI sessions (Antigravity CLI, Claude Code, Codex, Gemini CLI,
        OpenCode) or plain-Markdown editors (Cursor), use the Pure CommonMark
        nested-list template in `armature_protocol.md` instead of HTML.
    -   **Option labels (`questions[0].options`):** Match the `<Option name>`
        titles inside `question` 1:1 in the same order, prefixing Option 1 with
        `"(Recommended) "`. Make option names concrete enough to read alone.
        Append `"I need more context, zoom out and give examples"` on
        substantive decision turns. Never add a manual `"Other"` option.
-   **Follow-Up Questions & Need-More-Context Zoom-Outs:**

    -   *Informational follow-up (no open decision):* Answer directly in chat
        starting with an `# <Topic>` H1 heading (never a bare numbered or H3
        heading) and do not call `ask_question`.
    -   *Follow-up or zoom-out while a decision remains open:* Write a one-line
        lead-in in chat, and put the complete answer plus the re-teed decision
        inside `ask_question`'s `question` field: start with
        `## <Follow-Up Topic>` and plain-English explanation (or 1–2 concrete
        named domain examples on zoom-out, with zero file-read/search calls),
        then `<div class="border-t border-border my-2"></div>` (or `---` in
        CLI/Pure-Markdown fallback; never `---` in GUI panels where `<hr>` adds
        48px of dead space), then the rewritten `## <Decision Topic>`, overview,
        `Options`, and choices.
-   **Question First, Bookkeeping in the Same Step:** When a turn has to record
    something (append a settled decision, update a draft, run a quick command)
    and then ask, run the bookkeeping calls and `ask_question` in the same step
    right after the one-line chat lead-in rather than spending extra turns on
    bookkeeping first.
-   **Blank-Box Recovery (Box Stays the Default):** The `ask_question` box is
    the preferred way to ask. If a box came back `User Skipped` or empty, or the
    user says they could not see the explanation, put the full explanation
    inside `ask_question`'s `question` field (with a one-line chat lead-in) and
    ask again. Keep using the box for later questions.
-   **Plain-Text Question Mode (Fallback Only):** Ask directly in chat without
    `ask_question` only when the user asks to stop using the box or to ask in
    chat (keep doing so until they ask for the box again), when `ask_question`
    is unavailable, or when a recovery box also came back blank or skipped (for
    that one question). End the turn after the question so the user can reply.
    In Plain-Text Question Mode, render `# <Topic>`, plain overview,
    `#### OPTIONS`, the pure CommonMark nested ordered list options from
    `armature_protocol.md`, and `- Pick N if …` lines in chat.
-   **Heavy `write_file` Calls (Steps 6–7 Approval Gates):** Keep the chat
    lead-in to one short sentence, write the track artifacts (`write_file`), and
    put the concise spec/plan summary and approval choices inside `ask_question`
    in the same step.

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
