# Focus + Succinct Zoom-Out Interview Turn Standard

This reference defines the visual layout and everyday plain-language rules for
interactive interview turns in `/arm-new-track` (Step 5) and `/arm-setup`.

## 1. Everyday Plain-Language Standard (Zero Code Identifiers in Step 5)

During Step 5 (the human decision interview), questions, options, and trade-offs
must be written in everyday plain English anchored in familiar domain nouns from
the user's request:

- **Zero code identifiers or inline backticks** in prose (the orientation
  paragraph, numbered option lines, recommendation, or `Pick N if …` bullets).
- **Zero un-translated backend jargon** (*"blob"*, *"copy-on-write"*,
  *"refcount"*, *"in-flight"*, *"idempotent"*, *"fan-out"*, *"mutex"*).
- **Silent On-Disk State Checkpointing (Zero Chat Ledger Clutter):** Persist
  settled decisions and remaining open questions strictly on disk in `spec.md`
  (`status: draft`, under `## Settled Decisions` and `## Open Questions`) and
  `armature/active_context.md`. **Never** output `Round X settled:` lines or
  `**Settled**`, `**Now**`, or `**Up next**` lists in chat so the user can focus
  entirely on the active question.
- **Audience Pivot at Step 6/7 (`ADR 0016`):** Once the interview converges and
  drafts `spec.md` (Step 6) and `plan.md` (Step 7), pivot audience to the
  downstream execution agent and ground every settled decision into verified
  codebase symbols, 1-line method signatures, field bijections, and test
  commands.

## 2. Canonical Focus + Succinct Zoom-Out Turn Structure

Every Step 5 decision turn must render the following visible Markdown structure
in `content` before invoking `ask_question`:

1. **Clean topic headline:** `# <Topic>` (H1 — or `# Devil's Advocate: <Topic>`
   followed by `### Finding <F> of <N>: <Subtitle>` in Phase 5b). Omit `Round <R>,
   Question <Q> of <N>:` bookkeeping prefixes from the headline, and never
   render fenced `text` ASCII flow diagram blocks beneath the headline.
2. **Unlabeled succinct orientation (`2-3` plain-English sentences + bridge):**
   adult plain-English sentences anchored in familiar domain nouns stating what
   happens right before and right after this moment in the workflow (when a
   follow-up question was opened by the user's prior choice, weave that prior
   choice naturally into the opening clause rather than printing a separate
   settled line), followed by `The choice here is <5-9 words>. Here are some
   options:`.
3. **Concise blockquote option cards (`1..K`, recommended first at Option 1):**
   render one compact blockquote card per option (separated by `&nbsp;` or a
   blank line) with single-clause inline `Pros`, `Cons`, and `Implications`:

   ```markdown
   > **Option 1: <Option name> (Recommended)**
   > - **Pros:** <concise 1-clause benefit>
   > - **Cons:** <concise 1-clause trade-off or cost>
   > - **Implications:** <concise 1-clause operational or design impact>
   ```
4. **Deferred mechanics line:** `Safe to ignore for now: <2-3 low-level details>.`
5. **Recommendation (strictly 1 sentence):**
   `### Recommendation: Option 1` followed by strictly a single plain-English
   sentence (never 2 sentences).
6. **Decision recap bullets (exact `- Pick N if ` prefix):**
   `- Pick N if <short condition>.` (strictly one bullet per option card `1..K`
   using the exact words `- Pick N if `, never `- Pick N to `; target `160-280`
   words total from headline through the final `- Pick` bullet, `<= 300` words
   by default unless a critical safety caveat requires a few extra words).
   Never insert unnumbered options (such as `"Reopen Round <R>..."`) into
   `ask_question` alone—if reopening a prior decision is warranted in Phase 5b,
   include it as one of the `1..K` option cards in chat so chat `1..K` and modal
   `1..K` match strictly 1:1 (Option 1 prefixed with `"(Recommended) "`).
   Always emit the full visible Markdown block into `content` on the **same
   step** that calls `ask_question` (before any draft `write_file`/`edit_file`
   calls in that step). In Plain-Text Question Mode
   (`rules/armature_antigravity.md`), render the same block in chat and end the
   turn without `ask_question`.

These layout rules are defaults (`ADR 0022`): if following one literally would
hide a needed caveat or make the question harder to understand, say so and
adjust.

## 3. Follow-Up Questions, Zoom-Out & Zoom-In Handling

- **Follow-Up Questions (`# <Topic>` H1 Heading):** Whenever the user asks a
  follow-up question (about a term, option, or consequence), **always start the
  response with an `# <Topic>` H1 heading describing the topic being followed up
  on** (never a bare numbered or H3 heading), answer clearly in plain English,
  and if a decision remains open, append `---` followed by the re-teed
  `# <Decision Topic>` H1 turn + option cards + `ask_question`.
- **Need More Context (`"I need more context, zoom out and give examples"` /
  `"too vague"` / `"zoom out"`):** Make zero read/search tool calls, step back
  further in plain everyday English (starting with an `# <Topic>` H1 heading
  above plain paragraphs, **no blockquote cards above `---`**) to walk through
  1–2 concrete named domain examples above a `---` separator, and rewrite the
  Focus + Succinct Zoom-Out interview turn (with rewritten concise option cards)
  in simpler everyday words followed by `ask_question`.
- **Zoom-In (`"zoom in"`):** Expand the blockquote `**Pros:**` / `**Cons:**` /
  `**Implications:**` rows with deeper failure-mode and architectural detail
  when explicitly requested, and re-ask `ask_question`.
