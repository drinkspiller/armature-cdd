---
trigger: always_on
description: Armature Antigravity UX adapter - maps interaction requirements onto Antigravity native rendering
---

# Armature Antigravity UX Adapter (View Layer)

This platform rule informs the agent how to optimally map universal Armature
interaction requirements onto Antigravity's native visual rendering
capabilities.

## Interactive Interview Rendering

-   **Dynamic Tool Detection & Two-Part Turn Contract:** When `ask_question` is
    available, EVERY interactive question, brownfield setup gate,
    Need-More-Context / `"zoom out"` / `"too vague"` clarification re-tee,
    Devil's Advocate finding, ADR triage gate, and spec/plan review gate MUST
    include **BOTH** parts in the **same response**:
    1.  **Visible markdown text first (Mandatory First Output — Never Start With
        a Tool Call):** Your response output MUST ALWAYS begin directly with the
        non-empty visible markdown turn body (starting with `## Round …`, the
        settled confirmation + `**Settled**` / `**Now**` list, or the
        plain-English zoom-out explanation + `---` + rewritten `## Round …`
        block) ending cleanly on the final `- Pick K if …` bullet with zero
        transitional self-narration sentences. NEVER emit `ask_question` as the
        first or only item in your response without writing the full markdown
        body above it first (an empty message body hides all context,
        trade-offs, recommendations, and `- Pick N if …` guidance from the
        user), **AND**
    2.  **Native `ask_question` tool call second:** Invoke the structured
        `ask_question` tool call in that **same turn**. Never conclude an
        interactive turn with markdown prose alone, and never emit a bare
        `ask_question` call without the visible markdown body. If `ask_question`
        is unavailable in the environment, fall back to clean sequential text.

## `ask_question` Best Practices

The `ask_question` modal renders text with **limited formatting** - markdown
syntax displays as raw characters. Follow these rules:

1.  **Short questions only.** The `question` field must be a single concise
    sentence (15 words or fewer). Never put analysis, findings, code references,
    or multi-line content in the question.
2.  **Report first, ask second (in the same turn).** ALWAYS output your full
    visible markdown body FIRST before calling `ask_question` in that same turn.
    Never ask the user to evaluate or choose from items that were only described
    in internal thinking (`thought`) or summarized inside option labels.
3.  **Options match `<Option name>` in 1:1 order.** Place the recommended option
    first (`1.`), copy each plain-English `<Option name>` (the phrase before `:`)
    into `ask_question` options `1..K` in exact 1:1 order (prefixing Option 1
    with `"(Recommended) "`), and never substitute `Pick N if …` clauses.
4.  **Go beyond binary.** Prefer 2-3 concise options (at most 4) over Yes/No.
5.  **No explicit 'Other' option needed** - the UI always provides a write-in.
6.  **Clean markdown boundary & mandatory tool invocation.** Finish the visible
    markdown response directly on the final `- Pick K if …` bullet without
    transitional self-narration (never write *"I will now ask..."* or *"Let's
    call ask_question..."*), and immediately invoke the native structured
    `ask_question` tool call in the exact same turn. NEVER output raw
    `call:default_api:ask_question{...}` strings inside the markdown stream, and
    NEVER end a turn with markdown prose alone when presenting choices or
    re-tees.

### Examples

**BAD - analysis dumped into question:**

```
question: "A brownfield project detected. Found package.json with React 18,
TypeScript 5.3, 47 source files in src/, 12 test files, BUILD files present.
Should I scan only current files or also search past conversations and commits?"
options: ["Current files only", "Search past conversations and commits"]
```

**GOOD - stakes, numbered options, recommendation, and Pick recap as text,
question is short:**

First, output the Interview Turn v2 body as regular markdown (headline and
unlabeled opener in plain everyday English anchored directly in familiar domain
nouns from the user's request with zero code identifiers or backend systems
jargon, numbered one-line options placing the recommended option first at `1.`
whose `<Option name>` states what happens in everyday words, a `Safe to ignore
for now` line, a one-sentence `### Recommendation: Option 1`, and one bulleted
`- Pick N if …` recap line per numbered option; no blockquote cards, tables,
icons, emoji, or `[!NOTE]` / `[!TIP]` callouts inside the interview turn block):

```markdown
## Round 1, Question 1 of 1: How setup gathers context

This project already has a commit history and past sessions. If setup reads only
the checked-out files, the reasons behind reverted approaches and undocumented
trade-offs never make it into the setup docs and get rediscovered the hard way
later.

The choice here is which sources setup reads before drafting. Here are some options:

1. Search past conversations, commit history, and current codebase (Deep Retroactive Archaeology): mines history in one batch pass; adds a few minutes before review
2. Look only at current codebase contents (Current Snapshot Only): fast and bounded to checked-out files; misses the history behind discarded approaches

Safe to ignore for now: transcript parsing, memory search ranking.

### Recommendation: Option 1
Commit history is where the project's real invariants and discarded approaches live.

- Pick 1 if setup docs should capture why the codebase works the way it does.
- Pick 2 if a quick file-only starting point is enough.
```

Then call `ask_question` matching `<Option name>` from `1..K` directly in 1:1
order (never replacing `<Option name>` with the `Pick N if` sentences):

```
question: "How should Armature gather context to initialize this brownfield project?"
options: [
  "(Recommended) Search past conversations, commit history, and current codebase (Deep Retroactive Archaeology)",
  "Look only at current codebase contents (Current Snapshot Only)",
  "Customize scan sources (e.g., commits + files only, or manual description)",
  "I need more context, zoom out and give examples"
]
```

When the user selects `"I need more context, zoom out and give examples"` or
writes in that an option is too vague / asks to explain or zoom out, answer
directly from conversation context with **zero `view_file` / `code_search`
calls**, **omit `**Settled**` / `**Now**` / `**Up next**` completely** (so
nothing splits the explanation from the re-teed question), explain why the
decision arises in the workflow with 1–2 concrete named domain examples, output
`---`, and **rewrite** the headline, opener, numbered options (`1..K` matching
`ask_question` directly), and bulleted `- Pick N if …` lines in plain everyday
domain words (never copy-pasting the prior turn's wording verbatim) followed by
`ask_question`. The full `**Pros:**` / `**Cons:**` / `**Implications:**`
blockquote cards are the Zoom-In View and render strictly when the user
explicitly writes in `"zoom in"`.

**More examples:**

```
question: "How should I draft product.md?"
options: [
  "Interactive - walk me through questions",
  "Autogenerate from project context",
  "Start from a template I'll customize"
]
```

```
question: "Here's the draft. What do you think?"
options: [
  "Approve - looks good",
  "Suggest changes - I'll describe them",
  "Start over with a different approach"
]
```

## Artifact Rendering

Use rich markdown in artifacts: **tables**, **alerts** (`[!NOTE]`, `[!TIP]`,
`[!IMPORTANT]`, `[!WARNING]`), **file links** (`[file.ts](file:///path)`),
**mermaid diagrams**, and **code blocks**.

## Dual Artifact Strategy

When creating Armature artifacts (spec.md, plan.md, etc.):

1.  Write the **canonical version** to `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/`
    (committed to VCS)
2.  Create a **symlink** in the Antigravity artifact directory pointing to the
    canonical file for interactive review

## Asynchronous Subagent Delegation & Conversational Responsiveness

Synchronous tool execution suspends the model thread until all tools in the turn
return. For heavy operations (e.g., video/screencast decoding via `view_file`,
deep multi-repository search, lengthy compilation/benchmarks, or multi-phase
track implementations), running synchronously on the main thread locks the chat
UI and traps queued user messages in the inbox.

Phase-level routing rules (parallel isolated worktree subagents for independent
disjoint phases vs. a single worker for sequential coupled phases) are defined
in `skills/arm-implement/SKILL.md`:

1.  **Parallel Isolated Worktrees — Independent Disjoint Phases:**
    -   Use when an implementation phase contains multiple independent tasks
        operating on non-overlapping source and test directories.
    -   **Antigravity**: Dispatch parallel `worker` subagents in a single
        `invoke_subagent` call with `Workspace: "share"` for each entry to
        provision isolated working copies, and arm
        `schedule(DurationSeconds=90, TimerCondition="any")`.
    -   **Claude Code**: Dispatch parallel `Task(prompt="...",
        subagent_type="worker")` subagents in isolated `git worktree` checkouts.
    -   **Coordinator-Only Updates to Shared Track Files**: Parallel workers
        must only edit their assigned source and test files and must NEVER
        modify shared track files (`plan.md`, `metadata.json`, `tracks.md`, or
        `.api_surface_cache.json`). Only the orchestrator updates `plan.md`
        checkboxes and refreshes `.api_surface_cache.json` after merging and
        verifying worker worktrees at phase completion.
2.  **Single Worker — Sequential Coupled Phases & Standalone Heavy
    Investigations:**
    -   Use when phase tasks share state dependencies or touch overlapping
        files, or when offloading standalone heavy multimodal inputs (e.g.,
        screencast `.webm` files) or broad codebase discovery:
        -   **Claude Code**: Dispatch via `Task(prompt="...",
            subagent_type="explorer")` (or `subagent_type="worker"`).
        -   **OpenCode**: Route deep codebase exploration to `@explore` or
            `@scout`.
        -   **OpenAI Codex**: Delegate discovery or implementation work to
            `explorer` (`role="explorer"`) or `worker` (`role="worker"`).
        -   **Antigravity**: Dispatch via `invoke_subagent(TypeName='explorer',
            ...)` (or `TypeName='worker'`) and concurrently call
            `schedule(DurationSeconds=90, TimerCondition="<subagent_id>",
            Prompt="Check subagent progress and post a 20-block progress bar
            update in main chat.")` in the same turn. On each 90-second wakeup
            while a worker remains active (or on user status inquiries), inspect
            `manage_subagents(Action='list')` and recent steps in the active
            worker `transcript.jsonl`, output a leading blank line (`\n\n`), ``
            `▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░ XX%` (Task X of Y)``, a blank line (`\n\n`),
            and a 1–2 sentence status summary in main chat, and re-arm the
            90-second conditional `schedule` timer. When using 1-stage `self`
            subagents, instruct the worker to relay `[Progress]` updates via
            `send_message` and echo them in main chat.
        -   **Single-Threaded Harnesses (Cursor, Aider)**: Execute long-running
            jobs in the background (`run_in_background` or terminal `command & >
            /tmp/task.log`) with proactive status logging.
3.  **Context Window Hygiene & Reactive Re-engagement:** Isolating heavy
    multimodal frame extraction, compiler logs, or multi-file coding cycles
    inside background workers keeps thousands of transient tokens out of the
    parent context window. When the subagent or background task completes
    (automatically cancelling any pending conditional `schedule` timer),
    synthesize the verified results in the main conversational thread.
