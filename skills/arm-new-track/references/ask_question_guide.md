# `ask_question` Two-Part Turn & Modal Formatting Guide

This reference covers the native `ask_question` tool contract across
Antigravity and compatible agent hosts.

## 1. Atomic Two-Part Turn Contract (`ADR 0004`)

Whenever `ask_question` is invoked (interview turns, Need-More-Context re-tees,
Devil's Advocate findings, ADR triage, or spec/plan review gates), the response
MUST include **both** parts in the **same turn**:

1.  **Visible Markdown Body First (`content`):** Emit the full user-facing
    Markdown text into `content` before calling any tool. Never draft the
    explanation only inside internal `thinking` and then emit `ask_question`
    with empty `content: ""`.
2.  **Structured `ask_question` Call Second:** Call `ask_question` wrapped in
    the top-level `questions` array:
    ```json
    {
      "questions": [
        {
          "question": "Single concise sentence (<= 15 words, no markdown)?",
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

1.  **1-to-1 `<Option name>` Mapping:** Copy each `<Option name>` (the phrase
    before `:` in `1. <Option name>: <benefit>; <cost>`) into `options` in exact
    1-to-1 order, prefixing Option 1 with `"(Recommended) "`. Never substitute
    the `- Pick N if …` sentences as option labels.
2.  **No Markdown in `question` or `options`:** The modal renders raw
    characters; keep `question` `<= 15` words without backticks or bolding.
3.  **No Manual `"Other"` Option:** The UI modal provides a built-in write-in
    field automatically.
4.  **Streaming Flush Before Heavy `write_file` Calls (Step 6 & Step 7):** Keep
    the visible chat summary concise (`40-200` words) and end with a flushed
    paragraph break (`\n\n_Materializing the track artifacts and opening the
    approval prompt..._\n\n`) before calling `write_file` and `ask_question`.
