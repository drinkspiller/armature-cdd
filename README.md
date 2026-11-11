# Armature: Structural Permanence for AI Coding Agents

> [!NOTE] **Conductor is now Armature (v0.19.3)** \
> Conductor has been officially rebranded to **Armature**. Existing repositories
> with a `conductor/` directory continue operating seamlessly via Transparent
> Dual-Discovery with zero file migrations required.

## Fluid on the Outside, Rigid Underneath

In stop-motion animation, puppets look soft and pliable on the outside, but
their movement is held together by an internal steel armature with adjustable
tension joints. Without the armature, studio heat turns clay into a puddle.

Autonomous agents without structural boundaries do the exact same thing. When an
agent gets an execution loop, it moves fast. Without an internal structural
skeleton, models deform architecture, accumulate synonyms, and drift off spec.

**Conductor is now Armature.**

Armature gives agents full creative fluidity on the outside while anchoring them
to deterministic structural boundaries underneath.

### Why Code Alone Isn't the Single Source of Truth

Code shows what syntax exists today, but never why it was built that way or what
constraints must not be broken. Without architectural context, an AI agent
treats legacy workarounds and technical debt as intentional design—and
faithfully replicates them.

Most agentic harnesses trap project memory, learned patterns, and scratchpad
context in local SQLite caches or user-directory configs on an individual
developer's machine. When a teammate pulls the branch or an agent runs in CI,
that hard-won context evaporates.

Armature stores architectural decisions, domain terminology, and verification
runbooks directly in the repository (`armature/`). Context travels with the
codebase, versions alongside your git commits, and stays immediately shared
across the entire team.

--------------------------------------------------------------------------------

## Table of Contents

-   [Quickstart](#quickstart)
-   [Basic Workflow](#basic-workflow)
-   [Structural Joints for Autonomous Agents](#structural-joints-for-autonomous-agents)
    -   [The Grill Engine (`/arm-new-track`)](#the-grill-engine-arm-new-track)
    -   [Architectural Decision Records (`adr/`)](#architectural-decision-records-adr)
    -   [Domain Glossary (`terms.md`)](#domain-glossary-termsmd)
    -   [Living Runbooks (`manual_testing/`)](#living-runbooks-manual_testing)
    -   [Self-Updating Documentation (`/arm-drift`)](#self-updating-documentation-arm-drift)
    -   [Quick-Fix Bypass (*Bypass*)](#quick-fix-bypass-bypass)
-   [Armature Commands](#armature-commands)
-   [Evaluation Results & Benchmark](#evaluation-results--benchmark)
-   [What Gets Installed](#what-gets-installed)
-   [Installation Details & Flags](#installation-details--flags)
-   [Origins & Compatibility](#origins--compatibility)

--------------------------------------------------------------------------------

## Quickstart

Install Armature globally across your development environments:

```bash
# Install fresh via curl
curl -fsSL https://raw.githubusercontent.com/drinkspiller/armature-cdd/main/install.sh | bash

# Or update an existing installation
bash install.sh --update
```

## Basic Workflow

For day-to-day feature development and bug fixes *across any part of the stack*,
follow this three-step workflow in your AI coding assistant:

### 1. Plan the task (`/arm-new-track`)

For every new task, start a chat by invoking `/arm-new-track`, followed by the
path to your project's `armature` directory and your task description or issue
link:

**Example 1 — Describing what you want to make or change:**

```text
/arm-new-track your/project/root/directory/armature <prompt of what you want to make/change>
```

**Example 2 — Pasting an issue link directly:**

```text
/arm-new-track your/project/root/directory/armature https://github.com/org/repo/issues/1234
```

Armature walks you through targeted questions to clarify requirements and edge
cases, then generates two artifacts inside your track directory:

-   **`spec.md`** — Detailed requirements and acceptance criteria.
-   **`plan.md`** — Phased implementation tasks to fulfill the spec.

When `/arm-new-track` finishes, you receive a confirmation message with your
auto-generated track ID:

> ✅ Track `add-user-auth-backend` created! Run `/arm-implement` to start working
> through the plan.

### 2. Build the implementation (`/arm-implement`)

Next, run the command shown in the confirmation message:

```text
/arm-implement <name-of-the-created-track>
```

For example, the completion message from track creation above named the track
`add-user-auth-backend`, so you implement it using:

```text
/arm-implement add-user-auth-backend
```

Armature executes the spec step-by-step according to `plan.md`. Because you
started the session with `/arm-new-track` and pointed to your project's
`armature` directory, the agent automatically applies all accumulated project
context—including Architecture Decision Records (`adr/`), domain terminology
(`terms.md`), legacy code boundaries (`tech-stack.md`), and coding conventions.

### 3. Verify the result (`/arm-review`)

When implementation finishes, run:

```text
/arm-review
```

Armature walks you step-by-step through guided manual verification scenarios so
you can interactively confirm that everything works as expected. With
`--record` (or on UI tracks), `/arm-review --record` also captures an
instructional walkthrough reel with Warm Amber callout cards, compact beat hints,
and optional before/after comparison:

![Armature /arm-review live walkthrough demo](https://github.com/drinkspiller/armature-cdd/releases/download/armature-media/drawdb_fk_audit_demo.gif)

Watch the full-resolution recordings from
[armature-media](https://github.com/drinkspiller/armature-cdd/releases/tag/armature-media):
[MP4 (1080p)](https://github.com/drinkspiller/armature-cdd/releases/download/armature-media/drawdb_fk_audit_demo.mp4)
·
[WebM (1080p)](https://github.com/drinkspiller/armature-cdd/releases/download/armature-media/drawdb_fk_audit_demo.webm)
·
[GIF (1080px)](https://github.com/drinkspiller/armature-cdd/releases/download/armature-media/drawdb_fk_audit_demo.gif).

### Quick questions and trivial changes (`/arm-chat`)

For most tasks, use `/arm-new-track`. However, for project *questions* or
*extremely trivial* changes that don't require the full interview, spec, and
plan—but still benefit from your project's accumulated knowledge—use
`/arm-chat`:

```text
/arm-chat your/project/root/directory/armature <your question or task>
```

**Example 1 — Asking a project question:**

```text
/arm-chat your/project/root/directory/armature does the frontend adhere to a 12-column grid?
```

**Example 2 — Making an extremely trivial change:**

```text
/arm-chat your/project/root/directory/armature change the font size for the headline on the such and such page to 24px
```

## Structural Joints for Autonomous Agents

Autonomous coding agents move fast when given an execution loop, but velocity
without constraints quickly degrades codebase integrity. Without architectural
guardrails, models introduce conflicting abstractions, resurrect discarded
patterns, and let documentation drift away from real interfaces. Armature
establishes six structural joints that keep autonomous execution aligned with
system design:

### The Grill Engine (`/arm-new-track`)

Most AI coding agents jump straight from a short prompt into file edits. When
given underspecified requirements, models make silent assumptions about
architecture, pick the first familiar pattern that emerges in their context
window, and begin generating code without probing failure modes.

The Grill Engine enforces a structured round-and-question interview before any
implementation plan is drafted:

-   **Focus + Succinct `/zoom-out` Interview Turns**: Settled decisions and
    upcoming open questions are checkpointed silently on disk (`spec.md`
    `status: draft` and `armature/active_context.md`) rather than reprinted at
    the top of every chat message. Each turn opens directly with a clean
    `# <Topic>` headline grounded in familiar domain nouns from the request and
    a 2–3 sentence plain-English orientation free of code symbols, backend
    jargon, and fenced `text` ASCII flow diagram blocks, followed by
    `The choice here is … Here are some options:`, numbered one-line options
    placing the recommended option first
    (`1. <Option name>: <benefit>; <cost>`), a `Safe to ignore for now` line, a
    one-sentence `Recommendation: Option 1`, and bulleted `- Pick N if …` recap
    lines. Modal choices match `<Option name>` in 1-to-1 order followed by
    `"I need more context, zoom out and give examples"`, which steps back with
    concrete workflow examples above `---` before re-teeing a rewritten
    question; full `Pros` / `Cons` / `Implications` cards render on explicit
    `"zoom in"` write-ins.
-   **Dynamic Question Traversal**: Traverses edge cases, concurrency
    boundaries, error recovery, and security scope up to Depth 2 without
    unconfirmed dictation.
-   **Post-Interview Devil's Advocate (Phase 5b)**: When all rounds and
    sub-questions resolve, stress-tests the confirmed design against emergent
    contradictions, operational hazards, and failure cascades one-by-one.
-   **Execution-Ready Specification & Plan Grounding Standard (`ADR 0016`)**:
    While the Step 5 human interview stays strictly in plain everyday English
    with zero code identifiers, Step 6 (`spec.md`) and Step 7 (`plan.md`) pivot
    audience to the downstream execution agent (potentially a smaller or faster
    worker model operating with zero prior conversation context). By default,
    `spec.md` and `plan.md` translate settled plain-English choices into
    verified target file paths, non-obvious imports and build/package manifests,
    verified symbol/wrapper/element types, 1-line method signatures with exact
    parameter arity, prerequisite sub-tasks to expose `private`
    methods/getters/hooks, bidirectional UI-to-wire field bijections and server
    validation preconditions, self-contained state machines with reload
    echo-suppression flags, and unit-test fixture overrides—while strictly
    forbidding multi-line implementation code blocks inside `spec.md` or
    `plan.md`.
-   **Pre-Spec ADR Triage Gate (Phase 5c)**: Audits settled decisions against
    the 3-Pillar Invariant Taxonomy before drafting `spec.md`, offering
    immediate formalization.

### Architectural Decision Records (`adr/`)

Code only records the implementation that survived; it never records the
alternatives that were considered and rejected. Without a record of past
architectural decisions, an AI agent examining a codebase sees an un-cached
database query, a missing abstraction, or a manual loop and assumes it is an
oversight—often re-implementing the exact pattern the team intentionally
discarded.

Armature captures architectural trade-offs, rationale, and negative constraints
as version-controlled markdown records in `adr/` via a **Dual-Stage Lifecycle**:

1.  **Pre-Spec Triage Gate (Stage 1)**: Interactively triages settled track
    decisions against the **3-Pillar Invariant Taxonomy**:
    -   *Cross-Cutting Invariants*: Conventions, contracts, or state invariants
        constraining future tracks.
    -   *Architecture / Dependency Bindings*: Storage engines, transport
        protocols, or libraries costly to replace.
    -   *Negative Constraints*: Rejected standard patterns due to subtle gotchas
        or race conditions.
2.  **Closeout Diff Harvest (Stage 2)**: Proactively scans the final VCS diff,
    public API surface cache, and verified runbooks during track closeout
    (`/arm-implement`) to capture emergent invariants.

Each record includes an active verification checklist that is automatically
injected into implementation tasks, preventing regression into known
architectural dead ends.

### Domain Glossary (`terms.md`)

As codebases grow and multiple agent sessions touch different files, terminology
naturally fragments. One agent may refer to a core entity as a `workspace`,
another as a `board`, and a third as a `canvas`. This vocabulary drift breaks
semantic search, degrades codebase grep accuracy, and forces human developers to
write increasingly verbose disambiguation prompts.

Armature maintains a central domain glossary in `terms.md` that defines
canonical ubiquitous language for the project and explicitly lists banned
synonyms. The agent is bound to this vocabulary across specifications, code
symbols, and documentation, ensuring consistent naming conventions across the
entire lifecycle.

### Living Runbooks (`manual_testing/`)

Automated unit and integration tests are necessary, but they often fail to
capture end-to-end user workflows, environmental prerequisites, and stateful
side effects. At the same time, manual testing instructions in READMEs or
runbooks typically rot within weeks of being written, as interfaces shift and
commands fall out of date.

Armature pairs every development track with an active verification runbook. When
an implementation task is completed, steady-state manual test scenarios,
reproduction steps, and fixture setup commands are automatically synchronized
into permanent domain runbooks under `manual_testing/<domain>.md`. Verification
instructions stay aligned with the code as it evolves.

### Self-Updating Documentation (`/arm-drift`)

Documentation drift occurs incrementally. When an engineer or an agent renames
an exported symbol, alters a CLI parameter, or updates a package dependency, the
corresponding documentation often remains unchanged. Over time, specs and guides
become inaccurate, misleading both human contributors and future AI sessions.

`/arm-drift` acts as an automated tripwire by extracting AST symbols and public
API surfaces directly from the source code and comparing them against project
documentation, ADRs, and packaging manifests. It detects mechanical and semantic
discrepancies before changes are committed, automatically reconciling
straightforward documentation drift and alerting developers to deeper
divergences.

### Quick-Fix Bypass (*Bypass*)

Heavyweight specification workflows are counterproductive for trivial
modifications. Enforcing multi-turn interviews, architectural records, and
phased implementation plans for single-line bug fixes or styling adjustments
adds unnecessary friction and slows down routine maintenance.

The Quick-Fix Bypass establishes a ceremony-free fast path for surgical changes
of five lines or fewer that carry zero architectural ripple. The agent directly
inspects the target component, applies the minimal required diff, and verifies
the change against relevant tests without generating track artifacts or approval
gates.

--------------------------------------------------------------------------------

## Armature Commands

Once installed, the `/arm-*` commands are available globally in chat:

| Command          | Purpose                                                 |
| :--------------- | :------------------------------------------------------ |
| `/arm-setup`     | Initialize a project's `armature/` context (or adopt    |
:                  : legacy `conductor/`)                                    :
| `/arm-new-track` | Create a new feature or bug fix track via continuous    |
:                  : decision trees                                          :
| `/arm-implement` | Execute the current track's plan with pre-closeout      |
:                  : review-and-repair and drift checks                      :
| `/arm-status`    | View trajectory and contract health across all active   |
:                  : tracks (auto-updates mechanical drift)                  :
| `/arm-review`    | Multi-expert iterative review-and-repair loop against   |
:                  : living runbooks and ADRs                                :
| `/arm-drift`     | Continuous 3-tier drift tripwire with automatic Tier 1  |
:                  : mechanical auto-update and Tier 2 semantic gating       :
| `/arm-chat`      | Ceremony-free context ingestion with automatic glossary |
:                  : sync                                                    :
| `/arm-undo`      | VCS-aware surgical task, phase, or track rollback       |

### Experimental Commands (Beta — Opt-In via `--experimental`)

| Command                | Status     | Purpose                                |
| :--------------------- | :--------: | :------------------------------------- |
| `/arm-new-bug-bash`    | 🧪 **BETA** | Interactive scoping interview and      |
:                        :            : reproducible environment setup for Bug :
:                        :            : Bash tracks                            :
| `/arm-bash`            | 🧪 **BETA** | Autonomous multi-turn bug bash         |
:                        :            : execution loop with adversarial        :
:                        :            : verification                           :
| `/arm-bug-bash-triage` | 🧪 **BETA** | Interactive findings triage,           |
:                        :            : deduplication, and track conversion    :

--------------------------------------------------------------------------------

## Evaluation Results & Benchmark

Armature is evaluated against alternative Spec-Driven Development (SDD) and
Context-Driven Development (CDD) frameworks on the **CDD/SDD Benchmark v2**
(`v2-full-20261104`, public subset: `2,520` sandboxed tool-use rollouts across
`7` public frameworks × `60` scenarios [`30` core + `30` held-out] × `2` target
models [`gemini-3-flash-preview`, `gemini-3.5-flash`] × `3` seeds, with `0.0%`
harness errors and `10,000` two-level cluster-bootstrap resamples). Primary
scoring uses `180` deterministic sandbox outcome checks (`Outcome Score`),
paired with a blinded cross-family judge ensemble (`gemini-3.1-pro-preview` +
`opus-5.5-low` + `gemma-4-31b-it` tiebreak; inter-judge Cohen's $\kappa = 0.945$
`[0.895, 0.981]`). Frameworks in the same tier have paired outcome differences
whose 95% cluster-bootstrap CI includes `0`.

| Pooled | Framework               | Pooled    | `3-flash` | `3.5-flash` | Cross-Family | Key Empirical        |
: Tier   :                         : Outcome   : Outcome   : Outcome     : Judge [95%   : Takeaway             :
:        :                         : [95% CI]  : (Tier)    : (Tier)      : CI]          :                      :
| :----: | :---------------------- | :-------: | :-------: | :---------: | :----------: | :------------------- |
| **Tier | **Wayfinder             | **0.770** | `0.730`   | `0.811`     | `0.679       | #1 in `spec_gating`  |
: 1**    : (`mattpocock/skills`)** : `[0.710,  : (Tier 1)  : (Tier 1)    : [0.312,      : (`0.837`) and        :
:        :                         : 0.826]`   :           :             : 1.000]`      : `surgical_velocity`  :
:        :                         :           :           :             :              : (`0.938`); writes    :
:        :                         :           :           :             :              : draft specs on Turn  :
:        :                         :           :           :             :              : 1 before pausing     :
:        :                         :           :           :             :              : (`276k-313k` input   :
:        :                         :           :           :             :              : tok).                :
| **Tier | **BMAD Method**         | **0.761** | `0.727`   | `0.795`     | `0.619       | #2 in                |
: 1**    :                         : `[0.705,  : (Tier 1)  : (Tier 1)    : [0.250,      : `surgical_velocity`  :
:        :                         : 0.813]`   :           :             : 1.000]`      : (`0.932`) and        :
:        :                         :           :           :             :              : `context_continuity` :
:        :                         :           :           :             :              : (`0.811`); lowest    :
:        :                         :           :           :             :              : `state_safety`       :
:        :                         :           :           :             :              : (`0.580`) and        :
:        :                         :           :           :             :              : highest `max_steps`  :
:        :                         :           :           :             :              : exhaustion           :
:        :                         :           :           :             :              : (`13.3%-20.1%`).     :
| **Tier | **Cline Memory Bank**   | **0.748** | `0.711`   | `0.785`     | `0.500       | #1 in                |
: 1**    :                         : `[0.689,  : (Tier 1)  : (Tier 1)    : [0.143,      : `context_continuity` :
:        :                         : 0.806]`   :           :             : 0.875]`      : (`0.941`) and        :
:        :                         :           :           :             :              : `drift_governance`   :
:        :                         :           :           :             :              : (`0.878`) with a     :
:        :                         :           :           :             :              : lean `207k-237k`     :
:        :                         :           :           :             :              : input token          :
:        :                         :           :           :             :              : footprint; weakest   :
:        :                         :           :           :             :              : `surgical_velocity`  :
:        :                         :           :           :             :              : (`0.689`).           :
| **Tier | **GitHub Spec Kit**     | **0.718** | `0.672`   | `0.764`     | `0.464       | Strong               |
: 1**    :                         : `[0.654,  : (Tier 1)  : (Tier 1)    : [0.167,      : `surgical_velocity`  :
:        :                         : 0.780]`   :           :             : 0.750]`      : (`0.931`); drops     :
:        :                         :           :           :             :              : `-13.7 pp` from core :
:        :                         :           :           :             :              : (`0.777`, Tier 1) to :
:        :                         :           :           :             :              : held-out (`0.658`,   :
:        :                         :           :           :             :              : Tier 2).             :
| **Tier | **Armature (OSS)**      | **0.689** | `0.687`   | `0.691`     | `0.417       | **Tier 1 pooled      |
: 1**    : *(this)*                : `[0.613,  : (Tier 1)  : (Tier 2)    : [0.083,      : (`0.689`) and on     :
:        :                         : 0.762]`   :           :             : 0.750]`      : `3-flash`            :
:        :                         :           :           :             :              : (`0.687`)**, **#1 in :
:        :                         :           :           :             :              : `state_safety`       :
:        :                         :           :           :             :              : (`0.831`)**, #2 in   :
:        :                         :           :           :             :              : `drift_governance`   :
:        :                         :           :           :             :              : (`0.801`), and       :
:        :                         :           :           :             :              : `0.917`              :
:        :                         :           :           :             :              : `surgical_velocity`; :
:        :                         :           :           :             :              : multi-step modal     :
:        :                         :           :           :             :              : approval gates       :
:        :                         :           :           :             :              : depress              :
:        :                         :           :           :             :              : `spec_gating`        :
:        :                         :           :           :             :              : (`0.490`) and        :
:        :                         :           :           :             :              : `context_continuity` :
:        :                         :           :           :             :              : (`0.408`).           :
| **Tier | **OpenSpec**            | **0.680** | `0.617`   | `0.743`     | `0.357       | Largest cross-model  |
: 2**    :                         : `[0.616,  : (Tier 2)  : (Tier 1)    : [0.062,      : gain (`+0.126` from  :
:        :                         : 0.743]`   :           :             : 0.667]`      : `3-flash` to         :
:        :                         :           :           :             :              : `3.5-flash`), but    :
:        :                         :           :           :             :              : largest              :
:        :                         :           :           :             :              : core-to-held-out     :
:        :                         :           :           :             :              : drop (`-0.144`).     :
| **Tier | **Conductor (Gemini CLI | **0.627** | `0.589`   | `0.665`     | `0.083       | Lowest input token   |
: 2**    : extension)**            : `[0.553,  : (Tier 2)  : (Tier 2)    : [0.000,      : cost (`120k-146k`)   :
:        :                         : 0.699]`   :           :             : 0.333]`      : and `0.901`          :
:        :                         :           :           :             :              : `surgical_velocity`; :
:        :                         :           :           :             :              : lowest               :
:        :                         :           :           :             :              : `drift_governance`   :
:        :                         :           :           :             :              : (`0.640`) and        :
:        :                         :           :           :             :              : `context_continuity` :
:        :                         :           :           :             :              : (`0.388`).           :

### Per-Pillar Outcome Score Breakdown (All Target Models Pooled, Core + Held-Out)

| Framework               | `spec_gating` | `surgical_velocity` | `drift_governance` | `state_safety` | `context_continuity` | Mean Input  |
:                         : [95% CI]      : [95% CI]            : [95% CI]           : [95% CI]       : [95% CI]             : / Output    :
:                         :               :                     :                    :                :                      : Tok (`3.0`  :
:                         :               :                     :                    :                :                      : / `3.5`)    :
| :---------------------- | :-----------: | :-----------------: | :----------------: | :------------: | :------------------: | :---------: |
| **Wayfinder             | **0.837**     | **0.938** `[0.911,  | `0.759 [0.622,     | `0.624 [0.463, | `0.693 [0.582,       | `276k/1.9k` |
: (`mattpocock/skills`)** : `[0.760,      : 0.964]`             : 0.884]`            : 0.773]`        : 0.806]`              : ·           :
:                         : 0.912]`       :                     :                    :                :                      : `313k/2.0k` :
| **BMAD Method**         | `0.693        | `0.932 [0.897,      | `0.789 [0.676,     | `0.580 [0.428, | `0.811 [0.723,       | `449k/2.7k` |
:                         : [0.618,       : 0.962]`             : 0.898]`            : 0.721]`        : 0.894]`              : ·           :
:                         : 0.764]`       :                     :                    :                :                      : `414k/2.3k` :
| **Cline Memory Bank**   | `0.589        | `0.689 [0.622,      | **0.878** `[0.799, | `0.644 [0.468, | **0.941** `[0.868,   | `207k/2.7k` |
:                         : [0.483,       : 0.748]`             : 0.951]`            : 0.802]`        : 0.993]`              : ·           :
:                         : 0.713]`       :                     :                    :                :                      : `237k/2.5k` :
| **GitHub Spec Kit**     | `0.620        | `0.931 [0.902,      | `0.777 [0.644,     | `0.621 [0.462, | `0.640 [0.515,       | `272k/3.1k` |
:                         : [0.503,       : 0.958]`             : 0.896]`            : 0.769]`        : 0.759]`              : ·           :
:                         : 0.721]`       :                     :                    :                :                      : `288k/2.9k` :
| **Armature (OSS)**      | `0.490        | `0.917 [0.862,      | `0.801 [0.668,     | **0.831**      | `0.408 [0.253,       | `662k/1.3k` |
: *(this)*                : [0.398,       : 0.963]`             : 0.926]`            : `[0.727,       : 0.580]`              : ·           :
:                         : 0.573]`       :                     :                    : 0.924]`        :                      : `711k/1.2k` :
| **OpenSpec**            | `0.565        | `0.857 [0.755,      | `0.751 [0.618,     | `0.604 [0.468, | `0.622 [0.483,       | `383k/2.8k` |
:                         : [0.431,       : 0.938]`             : 0.878]`            : 0.737]`        : 0.750]`              : ·           :
:                         : 0.674]`       :                     :                    :                :                      : `494k/3.0k` :
| **Conductor (Gemini CLI | `0.611        | `0.901 [0.844,      | `0.640 [0.481,     | `0.593 [0.431, | `0.388 [0.242,       | `120k/1.0k` |
: extension)**            : [0.514,       : 0.945]`             : 0.792]`            : 0.741]`        : 0.544]`              : ·           :
:                         : 0.698]`       :                     :                    :                :                      : `146k/1.1k` :

For full v2 methodology, limitations disclosure, per-model tables, and
reproduction commands, see
[evals/cdd_sdd_benchmark/results/v2-full-20261104/public/report.md](evals/cdd_sdd_benchmark/results/v2-full-20261104/public/report.md)
and [evals/README.md](evals/README.md).

--------------------------------------------------------------------------------

## What Gets Installed

Armature installs as a modular plugin bundle containing skills, rule protocols,
assets, and packaging manifests:

### Plugin Manifest & Core Skills

| File                         | Location in Plugin Bundle         | Agent       | Purpose           |
:                              :                                   : Persona     :                   :
| :--------------------------- | :-------------------------------- | :---------- | :---------------- |
| `plugin.json`                | `plugin.json`                     | —           | Plugin package    |
:                              :                                   :             : manifest (name,   :
:                              :                                   :             : version,          :
:                              :                                   :             : metadata)         :
| `marketplace.json`           | `.claude-plugin/marketplace.json` | —           | Claude Code       |
:                              :                                   :             : plugin manifest   :
| `arm-setup/`                 | `skills/arm-setup/`               | Armature    | `/arm-setup` —    |
:                              :                                   : Architect   : Initialize        :
:                              :                                   :             : project context,  :
:                              :                                   :             : glossary, ADR     :
:                              :                                   :             : directory, and    :
:                              :                                   :             : living runbooks   :
| `workflow_template.md`       | `skills/arm-setup/assets/`        | —           | Bundled project   |
:                              :                                   :             : workflow template :
:                              :                                   :             : copied during     :
:                              :                                   :             : `/arm-setup`      :
| `adr_template.md`            | `skills/arm-setup/assets/`        | —           | Bundled project   |
:                              :                                   :             : ADR template      :
:                              :                                   :             : copied during     :
:                              :                                   :             : `/arm-setup`      :
| `manual_testing_template.md` | `skills/arm-setup/assets/`        | —           | Bundled manual    |
:                              :                                   :             : testing guide     :
:                              :                                   :             : template copied   :
:                              :                                   :             : during            :
:                              :                                   :             : `/arm-setup`      :
| `design_template.md`         | `skills/arm-setup/assets/`        | —           | Bundled UI        |
:                              :                                   :             : `DESIGN.md`       :
:                              :                                   :             : contract template :
:                              :                                   :             : copied during     :
:                              :                                   :             : `/arm-setup`      :
| `.armature_version`          | `.armature_version`               | —           | Version stamp for |
:                              :                                   :             : update detection  :
| `arm-new-track/`             | `skills/arm-new-track/`           | Armature    | `/arm-new-track`  |
:                              :                                   : Planner     : — Start a new     :
:                              :                                   :             : feature or bug    :
:                              :                                   :             : fix with          :
:                              :                                   :             : continuous        :
:                              :                                   :             : decision-tree     :
:                              :                                   :             : elicitation       :
| `arm-implement/`             | `skills/arm-implement/`           | Armature    | `/arm-implement`  |
:                              :                                   : Implementer : — Execute plan    :
:                              :                                   :             : tasks with        :
:                              :                                   :             : pre-closeout      :
:                              :                                   :             : multi-expert      :
:                              :                                   :             : review-and-repair :
:                              :                                   :             : and phase         :
:                              :                                   :             : checkpoint drift  :
:                              :                                   :             : audits            :
| `arm-status/`                | `skills/arm-status/`              | Armature    | `/arm-status` —   |
:                              :                                   : Observer    : View project      :
:                              :                                   :             : trajectory with   :
:                              :                                   :             : ambient contract  :
:                              :                                   :             : health monitoring :
:                              :                                   :             : and automatic     :
:                              :                                   :             : Tier 1 drift      :
:                              :                                   :             : reconciliation    :
| `arm-review/`                | `skills/arm-review/`              | Armature    | `/arm-review` —   |
:                              :                                   : Reviewer    : Multi-expert      :
:                              :                                   :             : iterative code    :
:                              :                                   :             : review-and-repair :
:                              :                                   :             : loop and guided   :
:                              :                                   :             : interactive       :
:                              :                                   :             : manual            :
:                              :                                   :             : verification      :
:                              :                                   :             : walkthroughs      :
| `arm-undo/`                  | `skills/arm-undo/`                | Armature    | `/arm-undo` —     |
:                              :                                   : Surgeon     : Surgical          :
:                              :                                   :             : rollbacks with    :
:                              :                                   :             : destructive       :
:                              :                                   :             : operation         :
:                              :                                   :             : shielding         :
| `arm-drift/`                 | `skills/arm-drift/`               | Armature    | `/arm-drift` —    |
:                              :                                   : Drift       : Continuous 3-tier :
:                              :                                   : Auditor     : drift auditing    :
:                              :                                   :             : with default Tier :
:                              :                                   :             : 1 mechanical      :
:                              :                                   :             : auto-update and   :
:                              :                                   :             : Tier 2 semantic   :
:                              :                                   :             : gating            :
| `arm-chat/`                  | `skills/arm-chat/`                | Armature    | `/arm-chat` —     |
:                              :                                   : Guide       : Ceremony-free     :
:                              :                                   :             : context ingestion :
:                              :                                   :             : with automatic    :
:                              :                                   :             : glossary sync     :

### Experimental Command Skills (Beta — Opt-In via `--experimental`)

| File                   | Location in Plugin Bundle     | Agent   | Purpose                |
:                        :                               : Persona :                        :
| :--------------------- | :---------------------------- | :------ | :--------------------- |
| `arm-new-bug-bash/`    | `skills/arm-new-bug-bash/`    | Bug     | `/arm-new-bug-bash` —  |
:                        :                               : Bash    : `[BETA]` Interactive   :
:                        :                               : Scoper  : scoping interview and  :
:                        :                               :         : reproducible           :
:                        :                               :         : environment setup      :
| `arm-bash/`            | `skills/arm-bash/`            | Bug     | `/arm-bash` — `[BETA]` |
:                        :                               : Bash    : Autonomous multi-turn  :
:                        :                               : Hunter  : bug bash execution     :
:                        :                               :         : loop with adversarial  :
:                        :                               :         : verification           :
| `arm-bug-bash-triage/` | `skills/arm-bug-bash-triage/` | Bug     | `/arm-bug-bash-triage` |
:                        :                               : Bash    : — `[BETA]` Interactive :
:                        :                               : Triager : findings triage,       :
:                        :                               :         : deduplication, and     :
:                        :                               :         : track conversion       :

### Rules (MVC Architecture)

| File                        | Type        | Location in   | Purpose          |
:                             :             : Plugin Bundle :                  :
| :-------------------------- | :---------- | :------------ | :--------------- |
| `armature_protocol.md`      | Core Model  | `rules/`      | Always-on:       |
:                             :             :               : directory        :
:                             :             :               : structure,       :
:                             :             :               : transparent      :
:                             :             :               : dual-discovery   :
:                             :             :               : (§7),            :
:                             :             :               : guardrails,      :
:                             :             :               : interaction      :
:                             :             :               : standards        :
| `armature_antigravity.md`   | View /      | `rules/`      | Always-on:       |
:                             : Controller  :               : Antigravity CLI  :
:                             : Adapter     :               : and multi-agent  :
:                             :             :               : interaction      :
:                             :             :               : adapter          :
:                             :             :               : (`ask_question`, :
:                             :             :               : artifact         :
:                             :             :               : rendering)       :
| `armature_adr_preflight.md` | Dynamic     | `rules/`      | On-demand: ADR   |
:                             : Interceptor :               : preflight        :
:                             :             :               : interceptor for  :
:                             :             :               : brownfield       :
:                             :             :               : projects         :
| `armature_cdd_protocols.md` | CDD Engine  | `rules/`      | On-demand: Drift |
:                             :             :               : scan, ADR        :
:                             :             :               : capture,         :
:                             :             :               : per-directory    :
:                             :             :               : context rules    :

### Supported Environments

-   **Antigravity / Antigravity CLI**: Installs to
    `~/.gemini/config/plugins/armature-cdd/` (auto-discovered via plugin
    registry).
-   **Claude Code**: Discoverable via `.claude-plugin/marketplace.json` or
    `.agents/skills/`.
-   **Windsurf**: Discoverable via `.windsurf/` or `.agents/rules/`.
-   **Custom / Other Harnesses**: Use `--target=<path>` to install to any custom
    plugin or skills directory.

--------------------------------------------------------------------------------

## Installation Details & Flags

```bash
# Preview what will happen (no files written)
bash install.sh --dry_run

# Include experimental Beta skills (/arm-bash, /arm-new-bug-bash, /arm-bug-bash-triage)
bash install.sh --experimental

# Overwrite without creating backups
bash install.sh --force

# Update to latest version (auto-preserves existing Beta skills state)
bash install.sh --update

# Update and explicitly disable Beta skills
bash install.sh --update --no-experimental

# Windows installation
install.bat

# Uninstall
bash install.sh --uninstall
```

### Flags

| Flag                | Description                              |
| :------------------ | :--------------------------------------- |
| `--dry_run`         | Preview changes without writing or       |
:                     : deleting files                           :
| `--experimental`    | Include experimental Beta skills         |
:                     : (`/arm-bash`, `/arm-new-bug-bash`,       :
:                     : `/arm-bug-bash-triage`)                  :
| `--no-experimental` | Explicitly exclude or prune experimental |
:                     : Beta skills                              :
| `--force`           | Overwrite existing files without         |
:                     : creating `.bak` backups                  :
| `--uninstall`       | Remove all installed Armature plugin and |
:                     : legacy files                             :
| `--update`          | Update to the latest version (implies    |
:                     : `--force`; preserves existing Beta       :
:                     : skills state)                            :
| `--target=<path>`   | Custom install target directory          |
:                     : (defaults to global plugin directory     :
:                     : `~/.gemini/config/plugins/armature-cdd`) :
| `--release_notes`   | Show release notes for the current       |
:                     : version from `CHANGELOG.md`              :
| `--help`            | Show usage information                   |

--------------------------------------------------------------------------------

## Origins & Compatibility

### Lineage

Armature was inspired by and forked from the
[Conductor](https://github.com/gemini-cli-extensions/conductor/) extension
(`github.com/gemini-cli-extensions/conductor`), which pioneered structured
track-based task orchestration for AI coding assistants.

Armature builds directly upon Conductor's foundational lifecycle, extending it
with living Architecture Decision Records (ADRs), ubiquitous language domain
glossaries (`terms.md`), continuous decision-tree traversal, living manual
verification runbooks, and automated multi-tier drift auditing.

### Backwards Compatibility w/ Conductor

Armature preserves **transparent dual-discovery**:

-   **Primary (`armature/`)**: Greenfield projects initialized via `/arm-setup`
    create `armature/`.
-   **Legacy Fallback (`conductor/`)**: Projects with existing `conductor/`
    directories continue operating seamlessly with zero file migrations
    required.

--------------------------------------------------------------------------------

## Version

Current: **v0.39.0** — See [CHANGELOG.md](CHANGELOG.md) for release notes.
