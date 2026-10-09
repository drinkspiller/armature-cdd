---
trigger: always_on
description: Armature Antigravity UX adapter - maps interaction requirements onto Antigravity native rendering
---

# Armature Antigravity UX Adapter (View Layer)

This platform rule informs the agent how to optimally map universal Armature
interaction requirements onto Antigravity's native visual rendering
capabilities.

## Interactive Interview Rendering

-   **Dynamic Tool Detection:** When presenting choices to the user, inspect
    your tool capabilities. If `ask_question` is available, MUST use it for
    interactive UI modals. If unavailable, fall back to clean sequential text
    formatting.

## `ask_question` Best Practices

The `ask_question` modal renders text with **limited formatting** - markdown
syntax displays as raw characters. Follow these rules:

1.  **Short questions only.** The `question` field must be a single concise
    sentence (15 words or fewer). Never put analysis, findings, code references,
    or multi-line content in the question.
2.  **Report first, ask second.** ALWAYS print your full analysis, findings,
    candidate item lists, context, and code/spec quotes as regular markdown text
    in your chat response FIRST before calling `ask_question`. Never ask the
    user to evaluate or choose from items that were only described in your
    internal thinking (`thought`) or summarized inside option labels. The modal
    prompt must only ask the decision question.
3.  **Options are the user's voice.** Each option reads as something the user
    would say.
4.  **Go beyond binary.** Prefer 3-4 meaningful options over Yes/No.
5.  **No explicit 'Other' option needed** - the UI always provides a write-in.
6.  **Clean markdown termination (Zero trailing meta-narration & Anti-Text-Only
    Stall).** End your markdown response immediately after the final analysis or
    rationale paragraph without transitional self-narration (e.g., never say *"I
    will now ask for your decision on..."* or *"Let's call ask_question..."*),
    and IMMEDIATELY emit the native `ask_question` tool call in the exact same
    turn. You are STRICTLY FORBIDDEN from ending your turn with markdown prose
    alone when presenting choices, rounds, or trade-offs.
7.  **Native structured tool invocation only.** Invoke `ask_question`
    exclusively as a structured tool call in the same turn as your markdown
    analysis. NEVER output raw `call:ask_question{...}` strings inside the
    markdown text stream, and NEVER omit `ask_question` when user input or a
    decision is required.

### Examples

**BAD - analysis dumped into question:**

```
question: "A brownfield project detected. Found package.json with React 18,
TypeScript 5.3, 47 source files in src/, 12 test files, BUILD files present.
Should I scan only current files or also search past conversations and commits?"
options: ["Current files only", "Search past conversations and commits"]
```

**GOOD - stakes, numbered options, recommendation, and Pick recap as text, question is short:**

First, output the Interview Turn v2 body as regular markdown (unlabeled opener
that says what changes for the user, numbered one-line options, a `Safe to
ignore for now` line, a one-sentence recommendation, and a `Pick N if …` recap;
no blockquote cards, tables, icons, emoji, or `[!NOTE]` / `[!TIP]` callouts):

```markdown
## Round 1, Question 1 of 1: How setup gathers context

This project already has a commit history and past sessions. If setup reads only
the checked-out files, the reasons behind reverted approaches and undocumented
trade-offs never make it into `product.md`, `tech-stack.md`, or the ADRs, and
they get rediscovered the hard way later.

The choice here is which sources setup reads before drafting. Here are some options:

1. Deep retroactive archaeology: mines commits and past transcripts in one pass; adds a few minutes before drafting
2. Current snapshot only: fast and bounded to checked-out files; misses the history behind discarded approaches

Safe to ignore for now: transcript parsing, memory search ranking.

### Recommendation: Option 1
Commit history is where the project's real invariants and discarded approaches live.

Pick 1 if you want setup artifacts that explain why the code looks the way it does.
Pick 2 if you only need a quick, file-based starting point.
```

Then call `ask_question`:

```
question: "How should Armature gather context to initialize this brownfield project?"
options: [
  "(Recommended) I want artifacts that explain why the code looks this way (Option 1)",
  "A quick file-based starting point is enough (Option 2)",
  "Customize scan sources (e.g., commits + files only, or manual description)"
]
```

The full `**Pros:**` / `**Cons:**` / `**Implications:**` blockquote cards are
the Zoom-In View: render them only when the user selects the trailing
"Compare technical trade-offs and failure modes in detail" option or replies
"zoom in".

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
deep multi-repository search, or lengthy compilation/benchmarks), running
synchronously on the main thread locks the chat UI and traps queued user
messages in the inbox for minutes or tens of minutes.

Follow these operational standards:

1.  **Immediate Dispatch, Conditional 90s Heartbeat & Turn Yield
    (Orchestrator-Worker Primacy):** When encountering heavy multimodal inputs
    (e.g., screencast `.webm` files), broad codebase discovery, or indeterminate
    tasks (>30s), the primary conversational agent MUST dispatch a background
    worker and immediately conclude its turn with a visible chat message
    confirming the worker has been started:
    -   **Claude Code**: Dispatch via `Task(prompt="...",
        subagent_type="explorer")`.
    -   **OpenCode**: Route deep codebase exploration to `@explore` or `@scout`.
    -   **OpenAI Codex**: Delegate discovery work to `explorer`
        (`role="explorer"`).
    -   **Antigravity**: Dispatch via `invoke_subagent(TypeName='explorer',
        ...)` (or `TypeName='worker'`) and concurrently call
        `schedule(DurationSeconds=90, TimerCondition="<subagent_id>",
        Prompt="Check subagent progress and post a 20-block progress bar update
        in main chat.")` (or `TimerCondition="any"` when multiple parallel
        subagents are dispatched) in the same turn.
    -   **Single-Threaded Harnesses (Cursor, Aider)**: Execute long-running jobs
        in the background (`run_in_background` or terminal `command & >
        /tmp/task.log`) with proactive status logging.
2.  **Periodic Progress Bar Relay & Conversational Availability:** Because
    background subagents and processes return immediately to the dispatching
    loop, the primary conversational agent remains unblocked. On each 90-second
    timer wakeup while a subagent is still running, or when the user asks for
    progress (e.g., `"status?"`, `"what are you doing?"`), the agent inspects
    worker state and recent step transcripts in seconds (e.g.,
    `manage_subagents(Action='list')` and the active worker `transcript.jsonl`
    in Antigravity, step inspection in Claude Code, or checking background
    logs/process table in single-threaded setups), prints a concise status
    update in main chat formatted with a leading blank line (`\n\n`), ``
    `▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░ XX%` (Task X of Y)``, a blank line (`\n\n`), and a 1–2
    sentence functional summary of completed and active work, and re-arms the
    90-second conditional `schedule` timer in the same turn rather than letting
    the user wait in silence. When using 1-stage custom or `self` subagents
    equipped with `send_message`, instruct the subagent in its `Prompt` to push
    ``[Progress]\n\n`▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░ XX%` (Task X of Y)\n\n<1-2 sentence
    summary>`` via `send_message(Recipient="<parent_id>", ...)` alongside its
    next tool call every ~3–4 turns or ~10 tool calls, and echo each incoming
    `[Progress]` message in main chat before yielding.
3.  **Context Window Hygiene:** Isolating heavy multimodal frame extraction,
    compiler logs, or sprawling search traces inside a subagent worker keeps
    thousands of transient tokens from polluting the primary conversation's
    context window.
4.  **Reactive Re-engagement:** When the subagent or background task completes
    (which automatically cancels any pending conditional `schedule` timer),
    synthesize the worker's findings and present them to the user in the main
    conversational thread.
