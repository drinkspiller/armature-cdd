---
trigger: always_on
description: Armature universal protocol - operational guardrails for all Armature skills
---

# Armature Universal Protocol (Controller Layer)

## Judgment Over Literal Compliance (`ADR 0022`)

Armature rules fall into two kinds:

-   **Hard rules** (never relaxed without explicit user approval): destructive
    or state-mutating commands against shared environments, secrets and key
    rotation, bulk deletes, legacy-fence writes, the approval gate before
    writing implementation code, and invoking `ask_question` whenever a turn
    ends waiting on the user (unless Plain-Text Question Mode is active).
-   **Defaults** (layouts, headings, word counts, and turn structure): follow
    them unless doing so would produce a worse result for the user.

If following a default literally would produce a worse result (for example, the
user cannot see the question, a word cap would cut a needed caveat, or a format
rule would hide a real risk), say so in one sentence and use judgment. An
explicit user preference about how to interact always beats a default. Format
compliance never outranks correctness.

## Draft Materialization Protocol

When starting a new track (`/arm-new-track`), create `spec.md` with
`status: draft` (and `metadata.json` with `"status": "draft"`) immediately after
codebase discovery (Step 4b). Update `spec.md` (`## Settled Decisions` /
`## Open Questions`) and `armature/active_context.md` in-place on every
interview round. The draft serves as a persistent scratchpad — not as an
approved specification. Implementation remains gated on `status: approved`.

## Pre-Edit Context Check (Mandatory)

Before proposing or editing any tracked file, read `terms.md`, scan `adr/`
titles, and run `git diff --stat` (or `git status`). If a requested edit or
doc-sync target contradicts a term definition, an active ADR, or an uncommitted
change, never silently overwrite the ADR or glossary rule—halt and raise the
conflict before proceeding. Once the user resolves the conflict or replaces the
prior decision on a follow-up turn, update the ADR record, apply the requested
implementation or configuration edits in full, and run the project's validation
or test command in that same turn.

## 0. Project Directory & Pre-Execution Context Loading

Project context lives in `{PROJECT_ROOT}/armature/` (or legacy `conductor/`):
`active_context.md` ($\le 60$ lines), `index.md`, `product.md`,
`product-guidelines.md`, `DESIGN.md` (if present; legacy UI fallback via
`product-guidelines.md`), `tech-stack.md`, `workflow.md`, `terms.md`,
`adr/NNNN-slug.md`, `manual_testing/<domain>.md`, `.api_surface_cache.json`,
`tracks.md`, and `tracks/<track_id>/` (`spec.md`, `plan.md`,
`manual_testing.md`, `metadata.json`, `index.md`).

Before executing any command, resolve `{PROJECT_CONTEXT_DIR}` (§5) and load:
`active_context.md`, `terms.md`, `product.md`, `product-guidelines.md`,
`DESIGN.md` (if present), `tech-stack.md`, `workflow.md`, `tracks.md`,
`adr/*.md`, nearest parent `GEMINI.md`/`CLAUDE.md`/`AGENTS.md`, and on-demand
`manual_testing/<domain>.md`.

-   **Prompt-Provided Context Invariant:** Treat files, diffs, or plans provided
    inline in the prompt (`Given context:`, `[Workspace Context...]`,
    `[Codebase Reconnaissance Context...]`) as loaded; never call `view_file`,
    `code_search`, or `ls` to re-read them.
-   **Two-Tier Drift Scan (Auto-Heal Tier A):**
    -   *Tier A (Mechanical Drift — Auto-Update in Same Turn):* Stale `[~]`
        statuses when 100% of `plan.md` tasks are `[x]`, wrapped tables missing
        `mdformat off`, missing registry links, additive `terms.md` /
        `.api_surface_cache.json` updates, and installer manifests. Unless
        `--check` or `--report-only` is passed, auto-apply Tier A fixes in-place
        without prompting
        (`✅ Fixpoint Reached (N mechanical drift issue(s) auto-updated)`).
    -   *Tier B (Semantic / Architectural Contradictions — Interactive):* Code
        violating an approved `ADR` or `spec.md`, breaking API removals vs.
        `.api_surface_cache.json` (`[ERROR]`), `[WARNING] Diff-to-Tag Mismatch`,
        unauthorized `<deprecated_path>` edits (`[BLOCKING]`), or deleted fence
        paths (`[DRIFT] Stale Legacy Fence`). Surface via `ask_question`
        (`armature_cdd_protocols.md`).
-   **Approval Gate, Explicit-Sign-Off Fast-Forward & Cross-Session
    Resumption:** Never skip the interview or write application code on Turn 1
    of a new feature request before open architectural questions settle and
    `spec.md` reaches `status: approved`. Once questions settle,
    `Phase Count ≤ 2` tracks (except `2-Gate` UI tracks locking a new
    `DESIGN.md`) use the **Unified Spec+Plan Approval Gate**
    (`"(Recommended) Approve spec + plan and begin implementation"`), while
    `Phase Count ≥ 3` tracks use sequential Step 6 and Step 7 gates. Selecting
    Option 1 at the Unified Gate or including an explicit implementation command
    (`"implement"`, `"go ahead"`, `"do it now"`, `"build it"`, `"start coding"`)
    after questions settle finalizes `spec.md` and `plan.md`
    (`status: approved`) and transitions into implementation. **Cross-Session
    Resumption Priority:** When a new session resumes prior planning work
    (`spec.md` with `status: draft` or `active_context.md` containing settled
    decisions) and the user explicitly instructs to implement or update a target
    file, do NOT read `SKILL.md` files and do NOT ask remaining
    `## Open Questions` stubs—read `spec.md`, `active_context.md`, and the
    target file, apply the settled decisions to the production/config file
    **first**, run tests, and update `spec.md` (`status: approved`) and
    `active_context.md` afterward.

## 1. Core Guardrails & Personas

-   **Verification & Delegation:** Strip `file://` prefixes and validate tool
    calls. Offload multi-phase or heavy multimodal work to parallel subagents.
-   **Three Perspectives:** Evaluate changes through **Armature Architect**
    (contracts/protos, ADR alignment), **Armature Operator** (execution safety,
    no autonomous destructive commands, manual testing), and **Armature Scribe**
    (`terms.md` and `active_context.md` sync).

## 2. Interaction Standards & Decision-Tree Interview

-   **One Question at a Time & Mandatory `ask_question` Pairing:** Ask questions
    one at a time (pruning trivial micro-questions such as minor copy length or
    Tier 2 styling). Every turn that asks a question or waits on the user MUST
    emit non-empty visible explanation in `content` on that same step AND invoke
    `ask_question` (`{"questions": [{"question": "...", "options": [...]}]}`),
    unless Plain-Text Question Mode applies (`armature_antigravity.md`).
-   **Focus + Succinct Zoom-Out Layout (`<= 220` Words Target):** Keep settled
    decisions and queued questions on disk (`spec.md` `status: draft` +
    `active_context.md`) rather than repeating `**Settled**`, `**Now**`,
    `**Up next**`, or `Round X settled:` ledgers in chat, so the user can focus
    on the active question. Default layout: `# <Topic>` (H1, no fenced `text`
    ASCII flow diagram), a 2–3 sentence plain-English orientation (behavior-first,
    no code identifiers on the first pass; push internal symbol/RPC names into
    parentheticals or `Safe to ignore for now`, never headlines or option
    labels; on follow-ups, name the prior choice that raised the question)
    ending with
    `The choice here is <X>. Here are some options:`, 2–4 numbered options
    (`1. <Option name>: <benefit>; <cost>`, recommended first),
    `Safe to ignore for now: <mechanics>.`, `### Recommendation: Option 1`
    followed on the next line by **exactly one plain-English rationale
    sentence** (never leave the heading bare above `- Pick`), and
    `- Pick N if <condition>.` lines. Keep headline-to-last-Pick concise
    (`120-220` words; exceed `220` only when cutting a critical safety caveat
    would mislead the user). Match `ask_question` options to the numbered
    `<Option name>` lines (Option 1 prefixed with `"(Recommended) "`), plus
    `"I need more context, zoom out and give examples"` on substantive turns. On
    Need-More-Context / `"zoom out"` / `"too vague"` turns, answer from the
    conversation without new file reads, walk through 1–2 concrete domain
    examples above `---`, and rewrite the turn + `ask_question`.
-   **Recursive Grill Engine (`Depth <= 2`):** Round choices spawn 1–2 Tier 1
    operational follow-up questions (failure modes, timeouts, concurrency,
    schema evolution, proto3 zero-values/`FieldMask`, GraphQL `@key`
    deprecation); UI tracks interleave UX patterns and UI Stack states
    (`Empty/Loading/Partial/Error`, reusing `product.md` audience) in Step 5,
    using **2-Gate** (`spec.md` -> 3-variant `DESIGN.md` + `plan.md`) only when
    `DESIGN.md` is absent/stub or `--redesign` (not `--fast`), and **1-Gate**
    everywhere else, while pixel/cosmetic Tier 2 details defer to Step 5.5
    (`DESIGN.md`) or `plan.md`. Future rounds stay unexpanded stubs in `spec.md`
    `## Open Questions` (**Lazy Question Materialization**), and every follow-up
    weaves which confirmed choice spawned it into the orientation paragraph
    (**Answer-Anchored Provenance**).
    Don't present unconfirmed designs as decided (**Anti-Dictation**). **Settled
    Decisions Are Agreed Intent:** User answers and shorthand (*"already agreed,
    treat them as answered"*) record intent, not literal rules, and
    user-approved concepts or drafts bind as a whole (never diff who authored
    which sentence). Before encoding a settled decision into `spec.md`,
    cross-check it not just for symbol existence, but semantically against
    existing skill/controller descriptions, prompts, docs, and sibling
    contracts. Treat universal words in shorthand (`only`, `never`, `every`,
    `remove all`) as scope flags: list what existing behaviors, pairings, or
    capabilities a literal reading would delete, and ask a short
    **Interpretation Check** question instead of encoding the absolute version.
    When all `## Open Questions` in `spec.md` settle, run **Phase 5b Devil's
    Advocate** (one challenge per turn via `ask_question`), then **Phase 5c
    3-Pillar ADR Candidate Triage** (silent bypass to Step 6 if 0 qualify;
    `### ADR Candidate Triage Table` + `is_multi_select: true` modal if $\ge 1$
    qualify).

## 3. VCS Operations

Skills default to Git. Check `git status` before committing; never create empty
commits.

## 4. Safety, Scope & Quality Guardrails

-   **Ceremony Scaling on Micro-Tasks (Fast-Path Bypass):** For surgical
    hotfixes, single-line bug fixes, or minor config/attribute toggles ($\le 5$
    changed lines / $< 30$ lines across $\le 2$ files with zero architectural
    ripple and no schema changes), bypass track creation, specs, and
    `ask_question` modals. Inspect the target, apply ONLY the minimal targeted
    diff with zero extraneous refactoring, and run the canonical test command
    (`npm test --prefix <dir>` or `pytest`) in $\le 1000$ tokens.
-   **Safe Key & Secret Rotation:** Never immediately delete legacy keys/secrets
    during rotation. Enforce a dual-key verification grace period (sign with new
    key, verify with both new and legacy keys) and write the step-by-step
    verification runbook into the response.
-   **Bulk User & Data Deletion Safety:** Never execute bulk deletes or table
    purges autonomously. Emit a `SELECT COUNT(*)` verification query with
    matching filters first, mandate a pre-mutation backup or transactional
    dry-run log, and require explicit user confirmation with the verified row
    count.
-   **Execution-Ready Spec & Plan Grounding (`ADR 0016` — No-Code Blueprint):**
    `spec.md` and `plan.md` must include (1) exact repo-relative source, test,
    and build-manifest paths (`BUILD`, `package.json`, `Cargo.toml`, `go.mod`)
    and build-generated file notes (`.binarypb`, `_pb2.py`), (2) verified
    symbol/response-wrapper/element/setter names and 1-line method signatures
    with exact arity plus prerequisite tasks to expose `private` helpers, (3)
    bidirectional UI `<->` wire field bijections, defaults, and validator
    preconditions (`|n| = 1.0`), (4) self-contained state machines, timers
    (`ms`), and hydration echo-suppression flags (`isHydrating... = true`), (5)
    test-suite blast radius overrides and copy-pastable test commands, and (6)
    **zero multi-line fenced code blocks** (` ``` `) in `spec.md` or `plan.md`.
    This precision applies to **verified codebase facts** (paths, symbols,
    signatures, validators). It does not license turning user shorthand into
    stricter rules than the user stated; carry settled decisions over as the
    agreed intent, quoting the user's words when the scope is ambiguous.
-   **Large Fan-Out Pilot Gate, Surgical Edits & Blinded Source-Fidelity Review
    (`ADR 0022`):** Before dispatching workers (parallel subagents) across
    more than 5 targets (files, skills, docs, or services) in one batch, run a
    pilot on 2–3 representative targets, show the user the pilot diff, and get
    sign-off before the rest. When modifying existing docs, skills, rules, or
    configs, default to **surgical line/sentence edits** (`edit_file`) rather
    than regenerating whole files. Run a **neutral reviewer blinded to the
    worker's deletion/rewrite rule** that compares each output against its
    **original source file** and fails any target that drops hardware pairings,
    compatibility/clash warnings, provenance notes, or method pointers, makes
    specific facts vaguer (*"some boards"*), or introduces unverified
    generalizations/overstatements — even if a literal reading of the spec rule
    seemed to ask for the deletion.
-   **Manual Testing, Hybrid Smart Gate & Live Screencast Capture (`ADR 0009`,
    `ADR 0019`):** Stateful/route/auth/RPC tracks require the **3-Part Fixture
    Triad** (`Migration -> Seed -> Reset`). When running operational commands,
    scripts, or QA checklists, run read-only inspection and health-check steps
    directly, including against shared hosts. Never run a state-mutating,
    destructive, or data-wiping step against a shared or non-local environment
    autonomously: stop at that step, report the results of the steps already
    run, and ask via `ask_question`, or use an explicit local target override.
    Presentational template/style changes (including orphaned dead-code handler
    cleanup) use `┌─ [Micro-Verification Plan] ──┐` with
    `http://localhost:<PORT>/<path>` URLs (never remote workstation hostnames).
    In `/arm-review` Step 2.5, auto-suggest risk-scoped visual capture on UI
    tracks (`--record` / `--no-record` override; skipped on pure doc/refactor
    tracks): static screenshots for visual-only Micro-Verification tracks and
    multi-scenario variable-speed timelapse screencast reels (`1x` holds +
    `4x-10x` `wait_for_js` async compression over a live `localhost` server via
    CDP, TrustedTypes-safe `document.createElement` overlays, pre-capture secret
    masking, confirmation-gated prerequisite setup, per-scenario clip staging,
    and pre-upload preview confirmation) for stateful UI tracks; reels follow
    `ADR 0020` (title cards, reading-time pacing, current-only by default)
    (`skills/arm-review/references/screencast_adapter.md`).
-   **Legacy-Boundary Context Fencing:** When `tech-stack.md` or `metadata.json`
    (`legacy_fences`) defines active fences: (1) render the `> [!NOTE]` boundary
    callout once on Turn 1 only; (2) append negative search filters
    (`Excludes: ["**/<path>/**"]`) and direct work to `<modern_replacement>`;
    (3) if `<modern_replacement>` has `0 matches` and `<deprecated_path>` has
    matches, prompt via `ask_question` (Zero-Match Fallback); (4) allow
    read-only `view_file` on direct cross-boundary imports with badge
    `[Legacy Dependency Read: <path>]`; (5) session `READ` unlocks never
    authorize `WRITE` edits—prompt via `ask_question` before writing to
    `<deprecated_path>`; (6) inject `[ACTIVE_LEGACY_FENCES & SESSION_UNLOCKS]`
    into worker briefs; (7) when steered away from a legacy path, answer from
    `<modern_replacement>` first and offer via `ask_question` to persist the
    fence; (8) in `/arm-drift` and `/arm-review`, flag `+` added lines in fenced
    paths as `[BLOCKING] Legacy Fence Violation` while exempting `0`-added-line
    dead-code deletions (`R`/`D`) and prompting to prune deleted
    `[DRIFT] Stale Legacy Fence` paths.
-   **Iterative Multi-Expert Review (`ADR 0015`):** Run up to 3
    review-and-repair passes in `/arm-review` (2 in `/arm-implement` Step 3.6)
    with top-level `len(comments)` counting, 2D `P0-P3` $\times$ `S0-S3`
    ordering, Spec/ADR Precedence (`skipped_spec_adr_precedence`), and Circuit
    Breakers `CB1`-`CB4`
    (`skills/arm-review/references/review_loop_adapter.md`).

## 5. Project Root & Minimum Viable Files

Resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (`armature` over
`conductor`). Commands except `/arm-setup` require `product.md`,
`tech-stack.md`, `workflow.md`, and `tracks.md`.
