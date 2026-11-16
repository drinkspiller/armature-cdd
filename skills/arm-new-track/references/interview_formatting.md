# Focus + Succinct Zoom-Out Interview Turn Standard

This reference defines the visual layout and everyday plain-language rules for
interactive interview turns in `/arm-new-track` (Step 5) and `/arm-setup`.

## 1. Everyday Plain-Language Standard (Zero Code Identifiers in Step 5)

During Step 5 (the human decision interview), questions, options, and trade-offs
must be written in everyday plain English anchored in familiar domain nouns from
the user's request:

-   **Zero code identifiers or inline backticks** in prose (the overview
    paragraph, option names, one-sentence option summaries, or `Pros:` /
    `Cons:`).
-   **Zero un-translated backend jargon** (*"blob"*, *"copy-on-write"*,
    *"refcount"*, *"in-flight"*, *"idempotent"*, *"fan-out"*, *"mutex"*).
-   **Silent On-Disk State Checkpointing (Zero Ledger Clutter):** Persist
    settled decisions and remaining open questions strictly on disk in `spec.md`
    (`status: draft`, under `## Settled Decisions` and `## Open Questions`) and
    `armature/active_context.md`. **Never** output `Round X settled:` lines or
    `**Settled**`, `**Now**`, or `**Up next**` lists in chat or in the question
    box so the user can focus entirely on the active question.
-   **Audience Pivot at Step 6/7 (`ADR 0016`):** Once the interview converges
    and drafts `spec.md` (Step 6) and `plan.md` (Step 7), pivot audience to the
    downstream execution agent and ground every settled decision into verified
    codebase symbols, 1-line method signatures, field bijections, and test
    commands.

## 2. Canonical Full-Context Question Box Structure (Default)

On every Step 5 decision turn (when Plain-Text Question Mode is not active),
write **only one short lead-in sentence in chat** naming the topic (no option
cards or `- Pick` bullets in chat), and put the full structured turn inside
`ask_question`'s `questions[0].question` field (target `160-250` words of
visible copy, default cap `<= 300` words unless a safety caveat needs more).

### Shared Content Model (All Harnesses)

1.  **Clean topic headline (`## <Topic>`):** `## <Topic>` (or
    `## Devil's Advocate: <Topic>` / `## Finding <F> of <N>: <Subtitle>` in
    Phase 5b). Omit `Round <R>, Question <Q> of <N>:` bookkeeping prefixes, and
    do **not** include fenced `text` ASCII flow diagram blocks.
2.  **Unlabeled succinct overview (`2-3` plain-English sentences + bridge):**
    directly beneath `## <Topic>`, write everyday plain-English sentences
    anchored in familiar domain nouns stating what happens right before and
    right after this moment in the workflow (weaving any prior settled choice
    naturally into the opening clause), ending with
    `The choice here is <5-9 words>.`
3.  **`Options` section eyebrow + flush-left numbered options (`1..K`,
    recommended first):**
    -   Numbered short name flush left (`1. <Option name>`); **Option 1**
        carries the `Recommended` pill/tag.
    -   Indented **one-sentence plain-English summary** explaining what that
        choice does and what happens (folding operational impact—and on Option
        1, the recommendation rationale—into this sentence).
    -   Indented bold **`Pros:`** (single clause) and bold **`Cons:`** (single
        clause). Never use enclosing option card containers or `+`/`-` symbols.
    -   **Permanent Omissions:** Never emit `Implications:` lines, redundant
        bottom `Recommendation:` blocks/rails, or `Safe to ignore for now:`
        footers.
4.  **Modal option labels (`questions[0].options`):** match the `<Option name>`
    titles `1..K` in exact 1-to-1 order, prefixing Option 1 with
    `"(Recommended) "`. Append
    `"I need more context, zoom out and give examples"` on substantive decision
    turns; omit it on copywriting, styling, or procedural approval gates. Never
    insert unnumbered options into `options` alone—if reopening a prior decision
    is warranted in Phase 5b, include it as one of the `1..K` options inside
    `question` too.

### Surface Rendering Templates

-   **Antigravity GUI Panels (Antigravity IDE, Hub, Desktop — see
    `rules/armature_antigravity.md`):** Use the `15px` white overview `<span>`,
    `<div class="mt-5 mb-1 ...">Options</div>` eyebrow (`div`, not `p`),
    `text-lg font-semibold text-foreground` flush-left headings with the green
    `Recommended` pill on Option 1, `pl-5` hanging indent, and bold white
    `Pros:`/`Cons:` over `text-secondary-foreground` copy.
-   **Universal Pure CommonMark Twin (CLIs & Plain-Markdown Harnesses — see
    `rules/armature_protocol.md`):**

    ```markdown
    ## <Topic>

    2-3 sentence plain-English overview ending with The choice here is <X>.

    #### OPTIONS

    1. **<Option 1 name>** *(Recommended)*

       <One-sentence plain-English summary explaining what Option 1 does and why it is recommended.>

       - **Pros:** <single-clause benefit>
       - **Cons:** <single-clause trade-off>

    2. **<Option 2 name>**

       <One-sentence plain-English summary explaining what Option 2 does and what happens.>

       - **Pros:** <single-clause benefit>
       - **Cons:** <single-clause trade-off>
    ```

These layout rules are defaults (`ADR 0022`): if following one literally would
hide a needed caveat or make the question harder to understand, say so and
adjust.

## 3. Plain-Text Question Mode Layout (Fallback Only)

When Plain-Text Question Mode applies (`rules/armature_antigravity.md`: the user
asked to stop using the box, `ask_question` is unavailable, or a recovery box
also failed), render the same content directly in chat without calling
`ask_question`: `# <Topic>` (H1), plain overview ending in
`The choice here is <X>.`, `#### OPTIONS`, the pure CommonMark nested ordered
list options above (no `Implications:`, no bottom `Recommendation:`, no
`Safe to ignore for now:`), and `- Pick N if <condition>.` bullets.

## 4. Follow-Up Questions, Zoom-Out & Zoom-In Handling

-   **Informational Follow-Up (No Open Decision):** Answer directly in chat
    starting with an `# <Topic>` H1 heading (never a bare numbered or H3
    heading) and do not call `ask_question`.
-   **Follow-Up Question While a Decision Remains Open:** Write a one-line
    lead-in in chat, and inside `ask_question`'s `question` field start with
    `## <Follow-Up Topic>` answering clearly in plain English, append
    `<div class="border-t border-border my-2"></div>` (GUI panels) or `---`
    (Pure Markdown), and follow with the re-teed `## <Decision Topic>`,
    overview, `Options`, and choices.
-   **Need More Context (`"I need more context, zoom out and give examples"` /
    `"too vague"` / `"zoom out"`):** Make zero read/search tool calls, write a
    one-line lead-in in chat, and inside `ask_question`'s `question` field open
    with `## <Topic>`, walk through 1–2 concrete named domain examples in plain
    paragraphs above the divider (no option lists above the divider), and
    rewrite the decision and option names in simpler everyday words below it.
-   **Zoom-In (`"zoom in"`):** Expand each option's indented summary, `Pros:`,
    and `Cons:` inside `ask_question`'s `question` field with deeper
    failure-mode and architectural detail when explicitly requested, and re-ask.
