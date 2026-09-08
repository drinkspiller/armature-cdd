---
trigger: always_on
description: Armature universal protocol - operational guardrails for all Armature skills
---

# Armature Universal Protocol (Controller Layer)

These operational standards apply globally to all Armature skills. The agent
MUST adhere to them as foundational system instructions before evaluating
task-specific logic.

## 0. Armature Project Directory (Dual-Root Support)

The project context directory lives at `{PROJECT_ROOT}/armature/` (or legacy `{PROJECT_ROOT}/conductor/`) — the root of the
user's project repository (NOT the Antigravity brain/artifacts directory). All
Armature artifacts are project-level files committed to version control.

```
armature/ (or legacy conductor/)
├── index.md                  # Links to all context files
├── product.md                # Product definition & vision
├── product-guidelines.md     # Tone, visual identity, UX patterns
├── tech-stack.md             # Technical choices & frameworks
├── workflow.md               # Task workflow, coding principles, commands
├── terms.md                  # Domain glossary & ubiquitous language
├── manual_testing/           # Living domain verification runbooks
│   └── <domain>.md
├── .api_surface_cache.json   # AST-extracted symbol snapshot (gitignored)
├── setup_state.json          # Setup progress tracking
├── code_styleguides/         # Language-specific style guides
├── adr/                      # Architecture Decision Records
│   └── NNNN-slug.md
├── tracks.md                 # Registry of all tracks (features/bugs)
├── tracks/                   # Active track directories
│   └── <track_id>/
│       ├── index.md          # Track context links
│       ├── spec.md           # Detailed specification
│       ├── plan.md           # Phased implementation plan
│       ├── manual_testing.md # Track manual verification runbook
│       └── metadata.json     # Track metadata
└── archive/                  # Completed track directories
```

## 0a. Pre-Execution Context Loading

Before executing ANY Armature command, resolve `{PROJECT_CONTEXT_DIR}` (either `armature` or `conductor` per §7) and load project context by reading these files in priority order:

1.  `{PROJECT_CONTEXT_DIR}/product.md` — What the product is
2.  `{PROJECT_CONTEXT_DIR}/product-guidelines.md` — How it should look & feel
3.  `{PROJECT_CONTEXT_DIR}/tech-stack.md` — Technical decisions
4.  `{PROJECT_CONTEXT_DIR}/workflow.md` — Task workflow & coding practices
5.  `{PROJECT_CONTEXT_DIR}/terms.md` — Domain glossary & ubiquitous language
6.  `{PROJECT_CONTEXT_DIR}/tracks.md` — Current track registry
7.  `{PROJECT_CONTEXT_DIR}/adr/*.md` — Active architecture decision records
8.  **Per-directory context:** For each source file the current task will touch,
    check the parent directory chain case-insensitively for context files
    (`GEMINI.md`, `CLAUDE.md`, `AGENTS.md`, or `AGENT.md`) containing a `##
    Armature Context` or `## Conductor Context` section. Load the nearest one (innermost directory wins).
9.  **Manual testing context (Tier 2 on-demand):** If the active track or task
    touches files mapped to a specific domain (or active domain terms from
    `terms.md`), load `{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md` on demand. Skip
    unrelated domain runbooks to preserve context token budgets.
10. **Drift scan:** Run a VCS diff stat against the last checkpoint commit.
    Cross-reference changed files against ADR scopes, local rules, and manual
    testing runbooks. Flag contradictions or invoke `/arm-drift` before
    proceeding (see `armature_cdd_protocols.md` §9).
11. **Non-blocking update check:** Run `bash ~/.cache/armature/check-update.sh 2>/dev/null || true`.
    If stdout outputs `UPDATE_AVAILABLE|<old_ver>|<new_ver>|<upgrade_cmd>`, prepend
    a compact `> [!TIP]` banner at the very top of your chat response:
    `> [!TIP]`
    `> **Armature Update Available (v<old_ver> → v<new_ver>)**`
    `> Run <upgrade_cmd> in your terminal, or reply "upgrade armature" to have me run it for you.`
    Never block command execution or invoke `ask_question` for the update check. If stdout is empty, output zero update banners.
    If the user replies `"upgrade armature"`, execute the `<upgrade_cmd>` via `run_command`, verify exit code `0`, and confirm the upgraded version.

Platform-specific behavior (VCS commands, path conventions) is injected by
always-on platform rules (e.g., `armature_enterprise.md`). Do not hardcode VCS
commands in skill protocols.

## 1. Core Operational Guardrails

-   **Precise Execution:** Do not skip steps. Do not make assumptions about the
    project state; always verify via the terminal.
-   **Tool Validation:** You MUST validate the success of every tool call. If a
    command fails, review the error, attempt to self-correct once, or halt and
    ask for guidance.
-   **Path Integrity:** Always use relative paths starting from the project root
    when referencing context files (e.g., `armature/index.md` or `conductor/index.md`).
-   **Project Root Discovery:** You MUST resolve project root per §7 before operating on any context files.
-   **Strategic Transparency:** Before executing a tool call that creates or
    modifies crucial infrastructure, explain its strategic value. Don't just
    execute; act as a mentor guiding the user through the 'Why'.
-   **Asynchronous Delegation Invariant (Zero Primary-Thread Freezes):**
    Long-running, indeterminate, or heavy multimodal operations—such as video or
    screencast frame extraction (`view_file`), extensive multi-repository code
    sweeps, or multi-minute test suites—must NEVER be executed synchronously on
    the primary conversational agent turn when background delegation
    capabilities exist. The primary agent MUST act as an orchestrator: dispatch
    a background worker, yield its turn immediately with a visible
    acknowledgement in chat, and remain interactively available to answer user
    status inquiries, accept steering commands, or process cancellations.

## 1a. Multi-Perspective Persona Reasoning

To ensure balanced implementation quality, safety, and documentation freshness,
the agent MUST simulate three internal perspectives before proposing any design,
code change, or workflow transition:

-   **Armature Architect**: Audits contract compatibility, proto/API evolution,
    backward compatibility, and ADR alignment. Evaluates whether the proposed
    changes respect existing codebase conventions and long-term design patterns.
-   **Armature Operator**: Enforces strict execution safety. Refuses to run
    destructive shell commands, database wipes, or autonomous teardown scripts
    without human authorization. Ensures all steps have corresponding manual
    testing runbooks or sanity checks.
-   **Armature Scribe**: Continuously audits Ubiquitous Language alignment
    (`terms.md`) and tracks context files. Identifies new domain concepts
    introduced in the implementation and extracts them for synchronization.

## 2. Interaction Standards

-   **Sequential Execution Barriers:** When conducting interactive interviews or
    spec generation loops, ask questions strictly one at a time. Present a
    single question, pause execution, and collect user confirmation before
    generating subsequent questions.
-   **Structured Choices & Option Trade-Off Analysis:**
    When presenting competing technical designs, architectural directions, UX layouts, or copywriting choices (e.g., during `/arm-new-track` Step 5a/5b or `/arm-setup`), provide 2–4 calibrated domain choices:
    -   *Markdown Trade-Off Breakdown (All Design, UX & Architecture Choices):* Precede the `ask_question` call with a punchy, itemized bulleted trade-off breakdown in chat:
        -   *Candidate Approaches:* For each option, list 1–2 punchy, substantive `Pros` and 1–2 `Cons`. Avoid vague generalities or superficial one-word clauses.
        -   *Recommendation Rationale:* Conclude with a 1–2 sentence declarative justification explaining why the recommended option was chosen, grounded in domain constraints (e.g., cognitive load, dialog footprint, latency bounds, or failure resilience).
        -   *Clean Markdown Termination & Mandatory Tool Call Pair (Zero Trailing Narration & Zero Text-Only Stalls):*
            End your markdown response immediately after the `Recommendation
            Rationale` paragraph. NEVER append transitional self-narration
            sentences at the end of your prose (e.g., *"I will now ask for your
            decision on..."* or *"Let's call ask_question..."*), which cause
            token concatenation and break tool parsing. Immediately invoke
            `ask_question` exclusively as a native structured tool call in the
            same turn—never emit raw `call:ask_question{...}` text in the
            markdown stream, and NEVER end your turn after markdown without
            invoking `ask_question` when choices, branches, or trade-offs are
            presented.
    -   *Modal Parameters (`ask_question`):*
        -   List the recommended option first with `(Recommended)`, followed by alternative approaches phrased cleanly in the user's voice.
        -   *Trailing Elaboration Option (Systems & Architecture Only):* Append a trailing choice (`"Compare technical trade-offs and failure modes in detail"`) **ONLY** for complex systems, data model, or infrastructure architecture decisions where deep-dive performance or failure analysis adds value. **NEVER** append an elaboration option to `ask_question` for UX copywriting, visual presentation, layout styling, empirical QA verification checks, safety confirmations, or procedural approvals.
    -   *Strict Exemption for Empirical & Procedural Gates:* Do **NOT** generate Pros/Cons breakdowns or append elaboration options for:
        1. **Empirical QA Verification Checkpoints** (`/arm-review` scenario checks: *"Did Scenario N meet the expected outcome?"* where choices are `Verified`, `Didn't match expectation`, `Skip`).
        2. **Safety & Environment Confirmations** (Hybrid Smart Gate destructive command prompts).
        3. **Lifecycle & Procedural Approvals** (`spec.md`/`plan.md` confirmation gates, ADR multi-select triage checkboxes).
        For these gates, present crisp context followed by direct status or action options.
-   **Human-Readable Navigation:** Always refer to process steps and documents
    by their human-readable names. Do not expose internal section numbers.

## 3. Artifact Output Convention

Whenever an Armature command produces structured output requiring user review -
clarifying questions, reports, summaries, specs, plans, or confirmation prompts:

1.  **Write as a Antigravity artifact** using `write_to_file`
2.  **Present via `notify_user`** with `PathsToReview` pointing to the file
3.  **Use appropriate ArtifactType**: `walkthrough` for reports/status,
    `implementation_plan` for specs/plans, `other` for questions/prompts
4.  **Set `BlockedOnUser: true`** when the artifact requires approval before
    proceeding

Artifact filenames follow: `arm_<command>_<context>.md`

## 4. VCS Operations

Armature skills are VCS-agnostic by default. Platform-specific VCS behavior
(Git, Mercurial, Mercurial/SVN) is injected by platform rules (e.g.,
`armature_enterprise.md`). When no platform rule overrides VCS behavior, default
to Git:

-   `git status` to check for changes
-   `git add` / `git commit` for commits
-   `git diff` for diffs
-   `git log` for history

**IMPORTANT:** Before creating any commit, ALWAYS check for actual changes
first. Do NOT create empty commits.

## 5. Armature Guardrails

-   **Never modify context files outside the active track** — only update
    files in `{PROJECT_CONTEXT_DIR}/tracks/<active_track_id>/` and `{PROJECT_CONTEXT_DIR}/tracks.md`
    during implementation. **Exceptions:** `{PROJECT_CONTEXT_DIR}/adr/*.md`,
    `{PROJECT_CONTEXT_DIR}/terms.md`, `{PROJECT_CONTEXT_DIR}/manual_testing/*.md`,
    `{PROJECT_CONTEXT_DIR}/.api_surface_cache.json`, and source-tree context files
    (`GEMINI.md`, `AGENTS.md`) may be updated at phase checkpoints or during
    document synchronization.
-   **Always confirm before overwriting user-approved specs or plans.**
-   **Ask before destructive operations** — do not delete tracks, revert
    commits, or remove artifacts without explicit user confirmation.
-   **Spec and plan approval gates** — always present specs and plans for
    explicit user approval before proceeding.
-   **Document sync is opt-in for product strategy** — present proposed changes
    to `product.md` and `product-guidelines.md` as diffs for user approval.
-   **Autonomous living documentation & glossary synchronization** — During
    track completion (`/arm-implement` Step 4), merging verified
    steady-state test scenarios from
    `{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md` into
    `{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md` is fully autonomous and non-gated. In
    addition, the agent must proactively scan the final diff for newly
    introduced domain terms, entities, and exported symbols, append their
    definitions to `{PROJECT_CONTEXT_DIR}/terms.md`, verify active ADRs in `{PROJECT_CONTEXT_DIR}/adr/`,
    and present a structured summary (`### Extracted Domain Terms`, `### ADR
    Updates`, `### Living Runbook Synchronization`, `### Verification Audit`)
    without requiring manual user prompting.
-   **Ceremony scaling on micro-tasks (Fast-Path Bypass)** — If a task is a
    surgical hotfix, single-line bug fix, or minor attribute toggle (≤5 lines of
    changed code with zero architectural ripple and no schema changes), execute
    the operational fast path: bypass track creation, multi-turn PRDs, specs, and
    interview modals (`ask_question`). Directly inspect the target component,
    propose ONLY the minimal targeted diff with zero extraneous refactoring (do
    not modernize adjacent error comparisons, reformat error strings, or rename
    unrelated variables), and provide the exact test verification command in ≤1000
    tokens (do not exceed token boundaries).
-   **Recursive Decision-Tree Grill Engine & Post-Ledger Devil's Advocate** —
    During track creation (`/arm-new-track` Step 5), the agent MUST maintain a
    visible `### Decision Tree Ledger` tracking root branches and spawned child
    leaves (`[ ]` OPEN, `[x]` Resolved). The interview operates in two strictly
    sequenced phases:
    1.  *Phase 5a (Dynamic Leaf Traversal & Ambiguity Elicitation)*: Selecting
        an architectural direction at the root of a branch does NOT close the
        branch; it actively spawns 1–2 high-value Tier 1 operational child
        leaves derived from that specific choice. Probing depth is strictly
        bounded to Depth <= 2 (Root Topic -> Operational Child Leaf).
        Operational child leaf answers are terminal (`[x]`) and MUST NOT spawn
        Level 2 grandchildren (Tier 2 styling, micro-copy, and internal helpers
        are pruned and deferred to `plan.md`). Future root branches MUST remain
        unexpanded stubs in the ledger until probed (Lazy Leaf Materialization);
        pre-populating leaves under unconfirmed branches is strictly forbidden.
        Every spawned child leaf MUST carry an Answer-Anchored Provenance Tag
        citing the confirmed choice: `- [ ] Leaf N.M: ... (Spawned by
        '<choice>': ...)`. Furthermore, the agent is strictly forbidden from
        asserting declarative technical designs, button configurations,
        countdown cancel behaviors, or state transitions in markdown for topics
        unconfirmed by the user via `ask_question`. Every turn presenting choices
        MUST pair markdown analysis and the Decision Tree Ledger with an immediate
        native `ask_question` tool call in the exact same turn; ending a turn with
        text alone when choices are presented or emitting bare `ask_question`
        without markdown text are both strictly forbidden.
    2.  *Phase 5b (Post-Ledger Devil's Advocate Analysis — Sequential
        Single-Finding Execution)*: When every branch and child leaf reaches
        `[x]`, the agent MUST NOT immediately converge and MUST NOT dump all
        emergent findings into a single compound prompt. It MUST output `###
        Devil's Advocate Analysis: Stress-Testing Confirmed Decisions`
        presenting each emergent cross-cutting contradiction, operational
        hazard, and maintainability debt finding **one-by-one**. For each
        finding, the agent MUST state the specific risk, offer concrete
        countermeasure options, and pause execution for human decision via
        `ask_question` individually before presenting subsequent findings. Only
        after all devil's advocate findings have been evaluated individually
        does the agent present the final convergence gate before proceeding to
        Phase 5c.
    3.  *Phase 5c (ADR Candidate Triage Gate — Dual-Stage Lifecycle)*:
        Immediately after Phase 5b Devil's Advocate concludes and before
        materializing `spec.md`, the agent MUST audit all settled decisions (`[x]`)
        in the Decision Tree Ledger against the **3-Pillar Invariant Taxonomy**:
        - *Pillar 1 (Cross-Cutting Invariant):* Establishes a convention, contract,
          or state invariant that constrains future tracks or touches multiple
          components (e.g., optimistic UI rollback rules, error-envelope schemas).
        - *Pillar 2 (Architecture / Dependency Binding):* Binds the repository to a
          storage engine, transport protocol, or third-party library that would be
          costly to rip out later (e.g., SQLite WAL, WebSocket vs. SSE).
        - *Pillar 3 (Negative Constraint / Discarded Alternative):* Rejects an
          obvious, standard pattern due to a subtle project gotcha or race condition
          (e.g., forbidding `sessionStorage` because it does not sync across tabs).
        - *Silent Zero-Candidate Bypass:* If zero settled decisions meet the 3-Pillar
          Taxonomy (i.e. all decisions are localized UI layouts, styling, route slugs,
          or chore configs), the agent MUST silently transition directly to Step 6
          Spec Confirmation without generating an extra modal prompt or noise.
        - *Interactive Triage Gate:* If one or more decisions qualify, the agent
          MUST output an `### ADR Candidate Triage Table` mapping each candidate
          decision to its qualification pillar, proposed title, and rationale. The
          agent halts execution with a multi-select `ask_question` allowing the user
          to confirm which ADRs to materialize. For each confirmed ADR, the agent
          drafts `{PROJECT_CONTEXT_DIR}/adr/NNNN-slug.md` in standard MADR format.
-   **Proto schema evolution & GraphQL federation probing** — During Step 5
    Recursive Decision-Tree Traversal (exploring dependent failure modes,
    boundary edge cases, and adversarial challenges) on protocol, GraphQL
    federation, or protobuf migrations, explicitly analyze and challenge schema
    directives (`@key`, `@shareable`, `@provides`), field deprecation paths,
    gateway circular dependencies, and service downtime mitigation, as well as
    proto3 default zero-values vs unset fields in partial updates, wire-format
    breaks, and FieldMask requirements before generating plans.
-   **3-Part Fixture Triad & Additive Manual Testing Verification** — Manual
    testing runbooks are strictly additive to automated unit and integration
    tests. In phase checkpoints, track closeouts, and review workflows, the
    agent must audit both automated CI test passes and reproducible manual
    fixture runbooks concurrently. Whenever database migrations or environment
    state changes are involved, the runbook must explicitly document all three
    commands in sequence: $$\text{Migration Command} \longrightarrow \text{Seed
    / Fixture Setup} \longrightarrow \text{Teardown / Reset Script}$$
-   **Documentation-only fixture policy & Hybrid Smart Gate** — Manual testing
    runbooks must specify exact setup, SQL mutation, and reset commands. During
    autonomous phase checkpoints (`/arm-implement`), the agent must NEVER
    execute mutative database, environment reset, or teardown commands
    autonomously (documentation-only policy). However, during user-authorized
    interactive manual testing sessions (`/arm-review`), the agent operates
    under the **Hybrid Smart Gate**: standard, non-destructive fixture commands
    (inserting test records, generating auth tokens, starting local servers,
    exporting test environment variables) execute automatically and stream their
    status, while potentially destructive commands (flagged by keywords in
    commands or script names/arguments: `DROP`, `DELETE`, `TRUNCATE`, `rm -rf`,
    `reset`, `clean`, `wipe`, `reseed`, `kill`) MUST prompt the user with the
    exact command for explicit confirmation via `ask_question` before running.
-   **Interactive Manual Testing Protocol & Living Runbook Sync** — When guided
    manual testing is selected during `/arm-review`, the agent executes the
    scenarios documented in
    `{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md` sequentially.
    For each scenario, the agent prepares the environment via the Hybrid Smart
    Gate. Before directing the user to navigate, the agent MUST output an
    explicit `##### Prerequisites` section providing exact server startup
    commands (e.g., `./run.sh`, `npm run dev`, background daemon scripts) inside
    a fenced code block, instructing the user to ensure the service stack is
    running. Furthermore, all target destinations MUST be presented as complete,
    fully qualified, copy-pastable URLs inside code blocks (providing both
    `http://localhost:<PORT>/<path>` and
    `http://<HOSTNAME>.dev.local:<PORT>/<path>`), never bare partial
    routes. The agent guides the user with exact navigation steps and expected
    outcomes, and validates results via `ask_question`. If a discrepancy occurs,
    the agent offers in-flight triage (fix now vs. log and continue). If an
    in-flight hotfix modifies code, the agent applies **Cascade Invalidation
    Tracking**, flagging previously verified scenarios for quick re-checking. A
    **Mandatory Post-Testing Reconciliation Gate** strictly enforces that all
    logged discrepancies are resolved, recorded as `[BLOCKING]` review findings,
    or accepted as `[WARNING]` tech debt before track approval. The agent
    injects the verified results into `review.md` (`## Interactive Verification
    Log`) and synchronizes refined commands back to
    `{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md`.
-   **Safe Key and Secret Rotation** — For credentials, keys, or JWT rotations,
    strictly refuse immediate deletion of legacy keys to prevent service or session
    disruption. Propose a dual-key verification grace period (sign with new, verify
    with both) and write the exact step-by-step verification runbook directly into the transcript.
-   **Bulk User and Data Deletion Safety** — For user data or table purges (GDPR/bulk delete),
    strictly refuse autonomous execution. Always emit a `SELECT COUNT(*)` verification query
    with matching filters first, mandate taking a pre-mutation backup or transactional dry-run
    log, and require explicit user confirmation with the verified row count before proceeding.
-   **Fixpoint and Drift Auditing** — A feature or track achieves completion
    only when the Fixpoint Auditor reports a "Fixpoint Reached" state. At phase
    checkpoints, track closeout, and pre-submit release gates, the agent audits
    code, ADRs, manual testing runbooks, API surfaces, and packaging manifests
    for divergence. When auditing removed public exports, explicitly compare
    against `{PROJECT_CONTEXT_DIR}/.api_surface_cache.json` and mandate semantic
    versioning major bump recommendations.

## 6. ADR & Glossary Preflight Interceptor

Full protocol in `armature_adr_preflight.md` (loaded on demand by skills).
Triggers when any Armature skill runs against a brownfield project with no
existing ADR files — sweeps docs for undocumented trade-offs and offers to
formalize them before proceeding.

## 7. Project Root & Context Directory Resolution (Transparent Dual-Discovery)

Before operating on any Armature files, resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` using this tiered heuristic:

1.  **Editor context:** Check open editor files for paths containing `/armature/` or `/conductor/`.
    - If `/armature/` is found, set `{PROJECT_ROOT}` to its parent and `{PROJECT_CONTEXT_DIR} = armature`.
    - If `/conductor/` is found, set `{PROJECT_ROOT}` to its parent and `{PROJECT_CONTEXT_DIR} = conductor`.
2.  **Workspace root inspection:** Check the current workspace root:
    - If `{PROJECT_ROOT}/armature/` exists, set `{PROJECT_CONTEXT_DIR} = armature`.
    - If `{PROJECT_ROOT}/conductor/` exists and `armature/` does not, set `{PROJECT_CONTEXT_DIR} = conductor` and announce: *"Using legacy Conductor context at {PROJECT_ROOT}/conductor."*
    - If both exist, `{PROJECT_ROOT}/armature/` takes precedence.
3.  **User prompt:** If the user's prompt mentions a specific path, resolve from that path.
4.  **Confidence gate:**
    - If exactly ONE candidate is found, use it and announce: *"Using Armature context at {PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}."*
    - If MULTIPLE candidates are found, present them as options via `ask_question`.
    - If NO candidate is found:
      - For `/arm-setup`: Default to `{PROJECT_ROOT}/armature/`.
      - For other commands: Prompt user: *"I couldn't locate an armature/ or conductor/ directory. Please specify the project root path or run /arm-setup."*

Once resolved, `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` persist for the duration of the session. Sub-skills reference them directly.

## 8. Minimum Viable Project Files

The following files constitute a valid Armature project. All Armature commands
(except `/arm-setup`) MUST verify these exist before proceeding:

-   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/product.md`
-   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tech-stack.md`
-   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/workflow.md`
-   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md`

Individual skills may require additional files (e.g., `/arm-review`
requires `product-guidelines.md`), but the base set above is the minimum gate.
If any are missing, halt execution with: *"Armature context is incomplete.
Please run `/arm-setup` first."*

## 9. CDD Protocols (Drift Scan, ADR Capture, Per-Directory Context)

Full protocols in `armature_cdd_protocols.md` (loaded on demand by skills).
Covers:

-   **§9 Pre-Execution Drift Scan**: Cross-reference uncommitted changes against
    ADR scopes and local rules; flag contradictions before the skill proceeds.
-   **§10 ADR Capture Protocol**: Triggers and interaction flow for capturing
    unwritten architectural decisions and behavioral contracts in `{PROJECT_CONTEXT_DIR}/adr/`.
-   **§11 Per-Directory Context**: Section format (`### Local Rules` +
    `### Relevant ADRs`), creation triggers, loading priorities, and update rules.
