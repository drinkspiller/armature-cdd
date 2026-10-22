# Armature: Structural Permanence for AI Coding Agents

> [!NOTE]
> **Conductor is now Armature (v0.19.3)**  
> Conductor has been officially rebranded to **Armature**. Existing repositories with a `conductor/` directory continue operating seamlessly via Transparent Dual-Discovery with zero file migrations required.


## Fluid on the Outside, Rigid Underneath

In stop-motion animation, puppets look soft and pliable on the outside, but their movement is held together by an internal steel armature with adjustable tension joints. Without the armature, studio heat turns clay into a puddle.

Autonomous agents without structural boundaries do the exact same thing. When an agent gets an execution loop, it moves fast. Without an internal structural skeleton, models deform architecture, accumulate synonyms, and drift off spec.

**Conductor is now Armature.**

Armature gives agents full creative fluidity on the outside while anchoring them to deterministic structural boundaries underneath.

### Why Code Alone Isn't the Single Source of Truth

Code shows what syntax exists today, but never why it was built that way or what constraints must not be broken. Without architectural context, an AI agent treats legacy workarounds and technical debt as intentional design—and faithfully replicates them.

Most agentic harnesses trap project memory, learned patterns, and scratchpad context in local SQLite caches or user-directory configs on an individual developer's machine. When a teammate pulls the branch or an agent runs in CI, that hard-won context evaporates.

Armature stores architectural decisions, domain terminology, and verification runbooks directly in the repository (`armature/`). Context travels with the codebase, versions alongside your git commits, and stays immediately shared across the entire team.

---

## Table of Contents

- [Quickstart](#quickstart)
- [Basic Workflow](#basic-workflow)
- [Structural Joints for Autonomous Agents](#structural-joints-for-autonomous-agents)
  - [The Grill Engine (`/arm-new-track`)](#the-grill-engine-arm-new-track)
  - [Architectural Decision Records (`adr/`)](#architectural-decision-records-adr)
  - [Domain Glossary (`terms.md`)](#domain-glossary-termsmd)
  - [Living Runbooks (`manual_testing/`)](#living-runbooks-manual_testing)
  - [Self-Updating Documentation (`/arm-drift`)](#self-updating-documentation-arm-drift)
  - [Quick-Fix Bypass (*Bypass*)](#quick-fix-bypass-bypass)
- [Armature Commands](#armature-commands)
- [Evaluation Results & Benchmark](#evaluation-results--benchmark)
- [What Gets Installed](#what-gets-installed)
- [Installation Details & Flags](#installation-details--flags)
- [Origins & Compatibility](#origins--compatibility)

---

## Quickstart

Install Armature globally across your development environments:

```bash
# Install fresh via curl
curl -fsSL https://raw.githubusercontent.com/drinkspiller/armature-cdd/main/install.sh | bash

# Or update an existing installation
bash install.sh --update
```

## Basic Workflow

For day-to-day feature development and bug fixes _across any part of the stack_, follow this three-step workflow in your AI coding assistant:

### 1. Plan the task (`/arm-new-track`)

For every new task, start a chat by invoking `/arm-new-track`, followed by the path to your project's `armature` directory and your task description or issue link:

**Example 1 — Describing what you want to make or change:**

```text
/arm-new-track your/project/root/directory/armature <prompt of what you want to make/change>
```

**Example 2 — Pasting an issue link directly:**

```text
/arm-new-track your/project/root/directory/armature https://github.com/org/repo/issues/1234
```

Armature walks you through targeted questions to clarify requirements and edge cases, then generates two artifacts inside your track directory:

- **`spec.md`** — Detailed requirements and acceptance criteria.
- **`plan.md`** — Phased implementation tasks to fulfill the spec.

When `/arm-new-track` finishes, you receive a confirmation message with your auto-generated track ID:

> ✅ Track `add-user-auth-backend` created! Run `/arm-implement` to start working through the plan.

### 2. Build the implementation (`/arm-implement`)

Next, run the command shown in the confirmation message:

```text
/arm-implement <name-of-the-created-track>
```

For example, the completion message from track creation above named the track `add-user-auth-backend`, so you implement it using:

```text
/arm-implement add-user-auth-backend
```

Armature executes the spec step-by-step according to `plan.md`. Because you started the session with `/arm-new-track` and pointed to your project's `armature` directory, the agent automatically applies all accumulated project context—including Architecture Decision Records (`adr/`), domain terminology (`terms.md`), legacy code boundaries (`tech-stack.md`), and coding conventions.

### 3. Verify the result (`/arm-review`)

When implementation finishes, run:

```text
/arm-review
```

Armature walks you step-by-step through guided manual verification scenarios so you can interactively confirm that everything works as expected.

### Quick questions and trivial changes (`/arm-chat`)

For most tasks, use `/arm-new-track`. However, for project _questions_ or _extremely trivial_ changes that don't require the full interview, spec, and plan—but still benefit from your project's accumulated knowledge—use `/arm-chat`:

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

Autonomous coding agents move fast when given an execution loop, but velocity without constraints quickly degrades codebase integrity. Without architectural guardrails, models introduce conflicting abstractions, resurrect discarded patterns, and let documentation drift away from real interfaces. Armature establishes six structural joints that keep autonomous execution aligned with system design:

### The Grill Engine (`/arm-new-track`)
Most AI coding agents jump straight from a short prompt into file edits. When given underspecified requirements, models make silent assumptions about architecture, pick the first familiar pattern that emerges in their context window, and begin generating code without probing failure modes.

The Grill Engine enforces a structured round-and-question interview before any implementation plan is drafted:
- **Scannable Interview Turns (v2)**: Each turn opens with a one-line note on the last answer and a short progress list (Settled, Now, Up next; at most five settled items shown, omitted on pre-selection clarification turns), then a `Round R, Question Q of N` headline grounded in familiar domain nouns from the request, a plain-English opener free of code symbols and backend jargon, `The choice here is … Here are some options:`, numbered one-line options placing the recommended option first (`1. <Option name>: <benefit>; <cost>`), a `Safe to ignore for now` line, a one-sentence `Recommendation: Option 1`, and bulleted `- Pick N if …` recap lines. Modal choices match `<Option name>` in 1-to-1 order followed by `"I need more context, zoom out and give examples"`, which steps back with concrete workflow examples before re-teeing a rewritten question; full `Pros` / `Cons` / `Implications` cards render on explicit `"zoom in"` write-ins.
- **Dynamic Question Traversal**: Traverses edge cases, concurrency boundaries, error recovery, and security scope up to Depth 2 without unconfirmed dictation.
- **Post-Interview Devil's Advocate (Phase 5b)**: When all rounds and sub-questions resolve, stress-tests the confirmed design against emergent contradictions, operational hazards, and failure cascades one-by-one.
- **Pre-Spec ADR Triage Gate (Phase 5c)**: Audits settled decisions against the 3-Pillar Invariant Taxonomy before drafting `spec.md`, offering immediate formalization.

### Architectural Decision Records (`adr/`)
Code only records the implementation that survived; it never records the alternatives that were considered and rejected. Without a record of past architectural decisions, an AI agent examining a codebase sees an un-cached database query, a missing abstraction, or a manual loop and assumes it is an oversight—often re-implementing the exact pattern the team intentionally discarded.

Armature captures architectural trade-offs, rationale, and negative constraints as version-controlled markdown records in `adr/` via a **Dual-Stage Lifecycle**:
1. **Pre-Spec Triage Gate (Stage 1)**: Interactively triages settled track decisions against the **3-Pillar Invariant Taxonomy**:
   - *Cross-Cutting Invariants*: Conventions, contracts, or state invariants constraining future tracks.
   - *Architecture / Dependency Bindings*: Storage engines, transport protocols, or libraries costly to replace.
   - *Negative Constraints*: Rejected standard patterns due to subtle gotchas or race conditions.
2. **Closeout Diff Harvest (Stage 2)**: Proactively scans the final VCS diff, public API surface cache, and verified runbooks during track closeout (`/arm-implement`) to capture emergent invariants.

Each record includes an active verification checklist that is automatically injected into implementation tasks, preventing regression into known architectural dead ends.

### Domain Glossary (`terms.md`)
As codebases grow and multiple agent sessions touch different files, terminology naturally fragments. One agent may refer to a core entity as a `workspace`, another as a `board`, and a third as a `canvas`. This vocabulary drift breaks semantic search, degrades codebase grep accuracy, and forces human developers to write increasingly verbose disambiguation prompts.

Armature maintains a central domain glossary in `terms.md` that defines canonical ubiquitous language for the project and explicitly lists banned synonyms. The agent is bound to this vocabulary across specifications, code symbols, and documentation, ensuring consistent naming conventions across the entire lifecycle.

### Living Runbooks (`manual_testing/`)
Automated unit and integration tests are necessary, but they often fail to capture end-to-end user workflows, environmental prerequisites, and stateful side effects. At the same time, manual testing instructions in READMEs or runbooks typically rot within weeks of being written, as interfaces shift and commands fall out of date.

Armature pairs every development track with an active verification runbook. When an implementation task is completed, steady-state manual test scenarios, reproduction steps, and fixture setup commands are automatically synchronized into permanent domain runbooks under `manual_testing/<domain>.md`. Verification instructions stay aligned with the code as it evolves.

### Self-Updating Documentation (`/arm-drift`)
Documentation drift occurs incrementally. When an engineer or an agent renames an exported symbol, alters a CLI parameter, or updates a package dependency, the corresponding documentation often remains unchanged. Over time, specs and guides become inaccurate, misleading both human contributors and future AI sessions.

`/arm-drift` acts as an automated tripwire by extracting AST symbols and public API surfaces directly from the source code and comparing them against project documentation, ADRs, and packaging manifests. It detects mechanical and semantic discrepancies before changes are committed, automatically reconciling straightforward documentation drift and alerting developers to deeper divergences.

### Quick-Fix Bypass (*Bypass*)
Heavyweight specification workflows are counterproductive for trivial modifications. Enforcing multi-turn interviews, architectural records, and phased implementation plans for single-line bug fixes or styling adjustments adds unnecessary friction and slows down routine maintenance.

The Quick-Fix Bypass establishes a ceremony-free fast path for surgical changes of five lines or fewer that carry zero architectural ripple. The agent directly inspects the target component, applies the minimal required diff, and verifies the change against relevant tests without generating track artifacts or approval gates.

---

## Armature Commands

Once installed, the `/arm-*` commands are available globally in chat:

| Command | Purpose |
| :--- | :--- |
| `/arm-setup` | Initialize a project's `armature/` context (or adopt legacy `conductor/`) |
| `/arm-new-track` | Create a new feature or bug fix track via continuous decision trees |
| `/arm-implement` | Execute the current track's plan with pre-closeout review-and-repair and drift checks |
| `/arm-status` | View trajectory and contract health across all active tracks (auto-updates mechanical drift) |
| `/arm-review` | Multi-expert iterative review-and-repair loop against living runbooks and ADRs |
| `/arm-drift` | Continuous 3-tier drift tripwire with automatic Tier 1 mechanical auto-update and Tier 2 semantic gating |
| `/arm-chat` | Ceremony-free context ingestion with automatic glossary sync |
| `/arm-undo` | VCS-aware surgical task, phase, or track rollback |

### Experimental Commands (Beta — Opt-In via `--experimental`)

| Command | Status | Purpose |
| :--- | :---: | :--- |
| `/arm-new-bug-bash` | 🧪 **BETA** | Interactive scoping interview and reproducible environment setup for Bug Bash tracks |
| `/arm-bash` | 🧪 **BETA** | Autonomous multi-turn bug bash execution loop with adversarial verification |
| `/arm-bug-bash-triage` | 🧪 **BETA** | Interactive findings triage, deduplication, and track conversion |

---

## Evaluation Results & Benchmark

Armature is benchmarked against alternative Spec-Driven Development (SDD) and Context-Driven Development (CDD) frameworks across a 30-scenario stratified engineering battery (120 criteria across 5 pillars) using live model rollouts and LLM Meta-Judging.

| Rank | Framework | Composite Score | Pass Rate (95% CI) | Avg Tokens / Task | Key Takeaway |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **#1** | **Armature (OSS)** *(this)* | **75.8 / 100** | **75.8%** (91/120, ±7.7%) | 4436 tokens | Leads in detour resilience (100.0%), drift governance (91.7%), and surgical velocity (70.8%); higher token footprint per task. |
| **#2** | **BMAD Method** | **70.8 / 100** | **70.8%** (85/120, ±8.1%) | 4031 tokens | Strongest execution safety guardrails (83.3%) and drift governance (83.3%); high multi-role ceremony on surgical micro-fixes. |
| **#3** | **OpenSpec** | **63.3 / 100** | **63.3%** (76/120, ±8.6%) | 2234 tokens | Lowest token footprint (2234 avg) and strong detour resilience (95.8%); weak upfront contract gating (37.5%) and proposal overhead on trivial edits. |
| **#4** | **Conductor (Canonical Upstream CLI)** | **61.7 / 100** | **61.7%** (74/120, ±8.7%) | 2972 tokens | Consistent detour handling (91.7%) and balanced token usage; lacks destructive-teardown refusal gates and multi-turn trade-off resolution. |
| **#5** | **GitHub Spec Kit** | **60.0 / 100** | **60.0%** (72/120, ±8.8%) | 3441 tokens | Highest specification and plan gating (62.5%) with strong detour handling (91.7%); heavy PRD ceremony on single-line hotfixes (16.7% velocity). |
| **#6** | **Memory Bank (Cline / Roo Code)** | **59.2 / 100** | **59.2%** (71/120, ±8.8%) | 3711 tokens | Reliable context retention across technical detours (95.8%); bypasses upfront specification gates (25.0%) with markdown churn on micro-patches. |
| **#7** | **Wayfinder** | **49.2 / 100** | **49.2%** (59/120, ±8.9%) | 3099 tokens | Strong detour context preservation (95.8%); planning-only stance penalizes surgical velocity (25.0%) and destructive-command safety gates (29.2%). |

---

## What Gets Installed

Armature installs as a modular plugin bundle containing skills, rule protocols, assets, and packaging manifests:

### Plugin Manifest & Core Skills

| File | Location in Plugin Bundle | Agent Persona | Purpose |
| :--- | :--- | :--- | :--- |
| `plugin.json` | `plugin.json` | — | Plugin package manifest (name, version, metadata) |
| `marketplace.json` | `.claude-plugin/marketplace.json` | — | Claude Code plugin manifest |
| `arm-setup/` | `skills/arm-setup/` | Armature Architect | `/arm-setup` — Initialize project context, glossary, ADR directory, and living runbooks |
| `workflow_template.md` | `skills/arm-setup/assets/` | — | Bundled project workflow template copied during `/arm-setup` |
| `adr_template.md` | `skills/arm-setup/assets/` | — | Bundled project ADR template copied during `/arm-setup` |
| `manual_testing_template.md` | `skills/arm-setup/assets/` | — | Bundled manual testing guide template copied during `/arm-setup` |
| `.armature_version` | `.armature_version` | — | Version stamp for update detection |
| `arm-new-track/` | `skills/arm-new-track/` | Armature Planner | `/arm-new-track` — Start a new feature or bug fix with continuous decision-tree elicitation |
| `arm-implement/` | `skills/arm-implement/` | Armature Implementer | `/arm-implement` — Execute plan tasks with pre-closeout multi-expert review-and-repair and phase checkpoint drift audits |
| `arm-status/` | `skills/arm-status/` | Armature Observer | `/arm-status` — View project trajectory with ambient contract health monitoring and automatic Tier 1 drift reconciliation |
| `arm-review/` | `skills/arm-review/` | Armature Reviewer | `/arm-review` — Multi-expert iterative code review-and-repair loop and guided interactive manual verification walkthroughs |
| `arm-undo/` | `skills/arm-undo/` | Armature Surgeon | `/arm-undo` — Surgical rollbacks with destructive operation shielding |
| `arm-drift/` | `skills/arm-drift/` | Armature Drift Auditor | `/arm-drift` — Continuous 3-tier drift auditing with default Tier 1 mechanical auto-update and Tier 2 semantic gating |
| `arm-chat/` | `skills/arm-chat/` | Armature Guide | `/arm-chat` — Ceremony-free context ingestion with automatic glossary sync |

### Experimental Command Skills (Beta — Opt-In via `--experimental`)

| File | Location in Plugin Bundle | Agent Persona | Purpose |
| :--- | :--- | :--- | :--- |
| `arm-new-bug-bash/` | `skills/arm-new-bug-bash/` | Bug Bash Scoper | `/arm-new-bug-bash` — `[BETA]` Interactive scoping interview and reproducible environment setup |
| `arm-bash/` | `skills/arm-bash/` | Bug Bash Hunter | `/arm-bash` — `[BETA]` Autonomous multi-turn bug bash execution loop with adversarial verification |
| `arm-bug-bash-triage/` | `skills/arm-bug-bash-triage/` | Bug Bash Triager | `/arm-bug-bash-triage` — `[BETA]` Interactive findings triage, deduplication, and track conversion |

### Rules (MVC Architecture)

| File | Type | Location in Plugin Bundle | Purpose |
| :--- | :--- | :--- | :--- |
| `armature_protocol.md` | Core Model | `rules/` | Always-on: directory structure, transparent dual-discovery (§7), guardrails, interaction standards |
| `armature_antigravity.md` | View / Controller Adapter | `rules/` | Always-on: Antigravity CLI and multi-agent interaction adapter (`ask_question`, artifact rendering) |
| `armature_adr_preflight.md` | Dynamic Interceptor | `rules/` | On-demand: ADR preflight interceptor for brownfield projects |
| `armature_cdd_protocols.md` | CDD Engine | `rules/` | On-demand: Drift scan, ADR capture, per-directory context rules |

### Supported Environments

- **Antigravity / Antigravity CLI**: Installs to `~/.gemini/config/plugins/armature-cdd/` (auto-discovered via plugin registry).
- **Claude Code**: Discoverable via `.claude-plugin/marketplace.json` or `.agents/skills/`.
- **Windsurf**: Discoverable via `.windsurf/` or `.agents/rules/`.
- **Custom / Other Harnesses**: Use `--target=<path>` to install to any custom plugin or skills directory.

---

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

| Flag | Description |
| :--- | :--- |
| `--dry_run` | Preview changes without writing or deleting files |
| `--experimental` | Include experimental Beta skills (`/arm-bash`, `/arm-new-bug-bash`, `/arm-bug-bash-triage`) |
| `--no-experimental` | Explicitly exclude or prune experimental Beta skills |
| `--force` | Overwrite existing files without creating `.bak` backups |
| `--uninstall` | Remove all installed Armature plugin and legacy files |
| `--update` | Update to the latest version (implies `--force`; preserves existing Beta skills state) |
| `--target=<path>` | Custom install target directory (defaults to global plugin directory `~/.gemini/config/plugins/armature-cdd`) |
| `--release_notes` | Show release notes for the current version from `CHANGELOG.md` |
| `--help` | Show usage information |

---

## Origins & Compatibility

### Lineage

Armature was inspired by and forked from the [Conductor](https://github.com/gemini-cli-extensions/conductor/) extension (`github.com/gemini-cli-extensions/conductor`), which pioneered structured track-based task orchestration for AI coding assistants. 

Armature builds directly upon Conductor's foundational lifecycle, extending it with living Architecture Decision Records (ADRs), ubiquitous language domain glossaries (`terms.md`), continuous decision-tree traversal, living manual verification runbooks, and automated multi-tier drift auditing.

### Backwards Compatibility w/ Conductor

Armature preserves **transparent dual-discovery**:
- **Primary (`armature/`)**: Greenfield projects initialized via `/arm-setup` create `armature/`.
- **Legacy Fallback (`conductor/`)**: Projects with existing `conductor/` directories continue operating seamlessly with zero file migrations required.

---

## Version

Current: **v0.33.0** — See [CHANGELOG.md](CHANGELOG.md) for release notes.

