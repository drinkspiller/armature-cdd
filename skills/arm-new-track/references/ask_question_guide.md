# `ask_question` Two-Part Turn & Modal Formatting Guide

This reference covers the native `ask_question` tool contract across Antigravity
and compatible agent hosts.

## 1. Same-Step Visible Text (`ADR 0004`, amended by `ADR 0022`)

Whenever `ask_question` is invoked (interview turns, Need-More-Context re-tees,
Devil's Advocate findings, ADR triage, or spec/plan review gates), the
**response step that calls `ask_question`** must include both parts:

1.  **Visible Markdown Body First (`content`):** Emit the full user-facing
    Markdown text into `content` on that step. Text written in `thinking` is
    never shown to the user, and text from an earlier step in the turn doesn't
    count if that step's `content` was empty.
2.  **Structured `ask_question` Call Second:** Call `ask_question` wrapped in
    the top-level `questions` array:

    ```json
    {
      "questions": [
        {
          "question": "One or two plain sentences naming the decision and the recommendation (up to about 40 words, no markdown)?",
          "options": [
            "(Recommended) <Option 1 name>",
            "<Option 2 name>",
            "I need more context, zoom out and give examples"
          ]
        }
      ]
    }
    ```

## 2. Option Mapping & Modal Rules

1.  **1-to-1 `<Option name>` Mapping:** Copy each `<Option name>` (the title
    phrase inside `> **Option N: <Option name>**`, stripping `(Recommended)`)
    into `options` in exact 1-to-1 order, prefixing Option 1 with
    `"(Recommended) "`. Never substitute the `- Pick N if …` sentences as option
    labels.
2.  **Self-Contained Box, No Markdown:** The modal renders raw characters and
    some hosts hide the chat text next to it, so `question` should stand on its
    own: one or two plain sentences without backticks or bolding. Keep option
    labels identical to the chat option card titles (make the names concrete
    rather than longer), and put any extra context in `question`.
3.  **No Manual `"Other"` Option:** The UI modal provides a built-in write-in
    field automatically.
4.  **Blank-Box Recovery & Plain-Text Fallback:** The box is the default. If a
    box came back `User Skipped` or empty, or the user says they can't see the
    explanation, explain in visible text and ask again with the box on that same
    step. Use numbered plain text only when the user asks for chat questions,
    `ask_question` is unavailable, or the recovery box also failed (see
    `rules/armature_antigravity.md`).
5.  **Streaming Flush Before Heavy `write_file` Calls (Step 6 & Step 7):** Keep
    the visible chat summary concise (`40-200` words) and end with a flushed
    paragraph break (`\n\n_Materializing the track artifacts and opening the
    approval prompt..._\n\n`) before calling `write_file` and `ask_question`.
