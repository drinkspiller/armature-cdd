---
trigger: always_on
description: Armature Antigravity UX adapter - maps interaction requirements onto Antigravity native rendering
---

# Armature Antigravity UX Adapter (View Layer)

This platform rule informs the agent how to optimally map universal Armature
interaction requirements onto Antigravity's native visual rendering capabilities.

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
6.  **Clean markdown termination (Zero trailing meta-narration & Anti-Text-Only Stall).**
    End your markdown response immediately after the final analysis or
    rationale paragraph without transitional self-narration (e.g., never say
    *"I will now ask for your decision on..."* or *"Let's call ask_question..."*),
    and IMMEDIATELY emit the native `ask_question` tool call in the exact same
    turn. You are STRICTLY FORBIDDEN from ending your turn with markdown prose
    alone when presenting choices, branches, or trade-offs.
7.  **Native structured tool invocation only.** Invoke `ask_question`
    exclusively as a structured tool call in the same turn as your markdown
    analysis. NEVER output raw `call:ask_question{...}` strings
    inside the markdown text stream, and NEVER omit `ask_question` when user
    input or a decision is required.

### Examples

**BAD - analysis dumped into question:**

```
question: "A brownfield project detected. Found package.json with React 18,
TypeScript 5.3, 47 source files in src/, 12 test files, BUILD files present.
May I perform a read-only scan of the codebase to extract the tech stack?"
options: ["Yes", "No"]
```

**GOOD - analysis as text, question is short:**

First, output findings as regular markdown:

> **Brownfield project detected.** I found `package.json` with React 18,
> TypeScript 5.3, 47 source files in `src/`, and BUILD files present.

Then call `ask_question`:

```
question: "May I perform a read-only codebase scan?"
options: [
  "Yes, scan everything",
  "Yes, but skip test files",
  "No, I'll describe the stack manually",
  "Show me what directories you'd scan first"
]
```

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

1.  Write the **canonical version** to `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/` (committed to
    VCS)
2.  Create a **symlink** in the Antigravity artifact directory pointing to the
    canonical file for interactive review

## Asynchronous Subagent Delegation & Conversational Responsiveness

Synchronous tool execution suspends the model thread until all tools in the turn
return. For heavy operations (e.g., video/screencast decoding via `view_file`,
deep multi-repository search, or lengthy compilation/benchmarks), running
synchronously on the main thread locks the chat UI and traps queued user
messages in the inbox for minutes or tens of minutes.

Follow these operational standards:

1.  **Immediate Dispatch & Turn Yield (Orchestrator-Worker Primacy):** When
    encountering heavy multimodal inputs (e.g., screencast `.webm` files), broad
    codebase discovery, or indeterminate tasks (>30s), the primary conversational
    agent MUST dispatch a background worker and immediately conclude its turn
    with a visible chat message confirming the worker has been started:
    -   **Claude Code**: Dispatch via `Task(prompt="...", subagent_type="explorer")`.
    -   **OpenCode**: Route deep codebase exploration to `@explore` or `@scout`.
    -   **OpenAI Codex**: Delegate discovery work to `explorer` (`role="explorer"`).
    -   **Antigravity**: Dispatch via `invoke_subagent(TypeName='DeepInvestigator', ...)` (or configured worker agent).
    -   **Single-Threaded Harnesses (Cursor, Aider)**: Execute long-running jobs in the
        background (`run_in_background` or terminal `command & > /tmp/task.log`) with
        proactive status logging.
2.  **Conversational Availability:** Because background subagents and processes
    return immediately to the dispatching loop, the primary conversational agent
    remains unblocked. When the user asks for progress (e.g., `"status?"`,
    `"what are you doing?"`), the agent inspects worker state in seconds
    (e.g., `manage_subagents(Action='list')` in Antigravity, step inspection
    in Claude Code, or checking background logs/process table in single-threaded
    setups) rather than letting the user wait in silence.
3.  **Context Window Hygiene:** Isolating heavy multimodal frame extraction,
    compiler logs, or sprawling search traces inside a subagent worker keeps
    thousands of transient tokens from polluting the primary conversation's
    context window.
4.  **Reactive Re-engagement:** When the subagent or background task completes,
    synthesize the worker's findings and present them to the user in the main
    conversational thread.
