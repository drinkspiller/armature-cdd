# `ask_question` Full-Context Box & Modal Formatting Guide

This reference covers the native `ask_question` tool contract across
Antigravity and compatible agent hosts (`ADR 0004`, amended by `ADR 0022`).

## 1. Full-Context Box With One-Line Chat Lead-In

`ask_question`'s `question` field renders multi-paragraph Markdown inside a
scrollable card and is the one channel every model family populates reliably
without harness hooks. Whenever `ask_question` is invoked (interview turns,
Need-More-Context re-tees, Devil's Advocate findings, ADR triage, or spec/plan
review gates):

1.  **One-Line Lead-In in Chat (`content`):** Emit **only one short lead-in
    sentence** naming the topic (e.g., `"One decision to settle before moving
    on: how background indexing shares the rate limit."`). Do **not** print
    option cards, `Pros`/`Cons` lists, or `- Pick N if …` bullets in chat—full
    chat cards cause Gemini-family models to treat the turn as finished and drop
    `ask_question`, while Claude models often drop chat text next to tool calls.
2.  **Full Turn Inside `questions[0].question`:** Put the complete interview
    turn inside `question` (target `~160-250` words of visible copy, default cap
    `~300` words unless a safety caveat needs more). Omit `Implications:`,
    redundant bottom `Recommendation:` blocks, and `Safe to ignore for now:`
    lines—fold operational impact (and Option 1's rationale) into each option's
    indented one-sentence summary.

    -   **Antigravity GUI Panels (Antigravity IDE, Hub, Desktop, and compatible
        rich-HTML chat hosts):**

        ```json
        {
          "questions": [
            {
              "question": "## Live Chat vs. Background Indexing\n\n<span style=\"font-size: 15px;\">Fresh installs scan 100+ past sessions in the background, and those summaries share the same rate limit as live chat. Without a priority rule, backfill bursts can stall a user's first reply for minutes. The choice here is which work goes first.</span>\n\n<div class=\"mt-5 mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground\">Options</div>\n\n<div class=\"flex flex-col gap-4\">\n<div class=\"flex flex-col gap-1\">\n<p class=\"text-lg font-semibold text-foreground\">1. Live chat first, newest-first backfill <span style=\"font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: 999px; background: color-mix(in srgb, var(--success) 16%, transparent); color: var(--success); margin-left: 6px; vertical-align: middle;\">Recommended</span></p>\n<div class=\"pl-5 flex flex-col gap-1.5\">\n\nLive chat and background summaries share one rate limit, so background workers pause whenever an interactive reply is active.\n\n<div class=\"flex flex-col gap-1 text-secondary-foreground\">\n\n<span style=\"color: var(--foreground); font-weight: 600;\">Pros:</span> Live chat replies stay at 1-2s and recent sessions appear first.\n\n<span style=\"color: var(--foreground); font-weight: 600;\">Cons:</span> Oldest sessions take a few extra minutes to finish indexing.\n\n</div>\n</div>\n</div>\n<div class=\"flex flex-col gap-1\">\n<p class=\"text-lg font-semibold text-foreground\">2. Summarize everything during the scan</p>\n<div class=\"pl-5 flex flex-col gap-1.5\">\n\nBatch summaries use full model quota ahead of live prompts until the initial scan completes.\n\n<div class=\"flex flex-col gap-1 text-secondary-foreground\">\n\n<span style=\"color: var(--foreground); font-weight: 600;\">Pros:</span> Every past session is searchable as soon as scanning completes.\n\n<span style=\"color: var(--foreground); font-weight: 600;\">Cons:</span> First scan is slow and stalls active chat typing.\n\n</div>\n</div>\n</div>\n</div>",
              "options": [
                "(Recommended) Live chat first, newest-first backfill",
                "Summarize everything during the scan",
                "I need more context, zoom out and give examples"
              ]
            }
          ]
        }
        ```

    -   **Universal Pure CommonMark Twin (CLIs & Plain-Markdown Harnesses):**

        ```json
        {
          "questions": [
            {
              "question": "## Live Chat vs. Background Indexing\n\nFresh installs scan 100+ past sessions in the background, and those summaries share the same rate limit as live chat. Without a priority rule, backfill bursts can stall a user's first reply for minutes. The choice here is which work goes first.\n\n#### OPTIONS\n\n1. **Live chat first, newest-first backfill** *(Recommended)*\n\n   Live chat and background summaries share one rate limit, so background workers pause whenever an interactive reply is active.\n\n   - **Pros:** Live chat replies stay at 1-2s and recent sessions appear first.\n   - **Cons:** Oldest sessions take a few extra minutes to finish indexing.\n\n2. **Summarize everything during the scan**\n\n   Batch summaries use full model quota ahead of live prompts until the initial scan completes.\n\n   - **Pros:** Every past session is searchable as soon as scanning completes.\n   - **Cons:** First scan is slow and stalls active chat typing.",
              "options": [
                "(Recommended) Live chat first, newest-first backfill",
                "Summarize everything during the scan",
                "I need more context, zoom out and give examples"
              ]
            }
          ]
        }
        ```

## 2. Option Mapping & Modal Rules

1.  **1-to-1 `<Option name>` Mapping:** Copy each numbered `<Option name>` title
    from `question` into `options` in exact 1-to-1 order, prefixing Option 1
    with `"(Recommended) "`. Make option names concrete enough to read alone.
    Never substitute `Pick N if …` sentences as option labels.
2.  **Surface Hygiene Inside `question`:** Use `## <Topic>`, an `Options`
    eyebrow (`<div>` in GUI HTML; `#### OPTIONS` in Pure Markdown), flush-left
    numbered titles with `Recommended` on Option 1, and an indented one-sentence
    summary plus bold `Pros:` / `Cons:` (no enclosing cards, no `+`/`-`, no
    `Implications:`, no bottom `Recommendation:`, no `Safe to ignore for now:`).
    On follow-ups and zoom-outs, use
    `<div class="border-t border-border my-2"></div>` in GUI panels or `---` in
    Pure Markdown (avoid `<hr>` / `---` in GUI panels where default rule spacing
    adds 48px of vertical gap). Avoid fenced code blocks
    inside the box.
3.  **No Manual `"Other"` Option:** The UI modal provides a built-in write-in
    field automatically.
4.  **Blank-Box Recovery & Plain-Text Fallback:** The box is the default. If a
    box came back `User Skipped` or empty, or the user says they could not see
    the explanation, put the full explanation inside `ask_question`'s `question`
    field (with a one-line chat lead-in) and ask again. Use **Plain-Text
    Question Mode** (full `# <Topic>` + `#### OPTIONS` pure CommonMark nested
    ordered list + `- Pick N if …` lines in chat, no `ask_question` call) only
    when the user explicitly asks to stop using the box / ask in chat, when
    `ask_question` is unavailable, or when a recovery box also failed (see
    `rules/armature_antigravity.md`).
5.  **Heavy `write_file` Calls (Step 6 & Step 7):** Emit the one-line chat
    lead-in, write the track artifacts (`write_file`), and pass the concise
    spec/plan summary and approval options inside `ask_question` in the same
    step.
