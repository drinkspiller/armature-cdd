# CDD Protocols (Drift Scan, ADR Capture, Per-Directory Context)

> Loaded on demand by Armature skills. Not an always-on rule.

## 9. Pre-Execution Drift Scan

After completing context loading (items 1–7), and before executing the invoked
skill's primary protocol, perform a lightweight drift check:

1.  **Diff stat:** Run a VCS diff stat (`git diff --stat` / `hg diff --stat`)
    against the last Armature / Conductor checkpoint commit (or HEAD if no checkpoint
    exists). This yields the list of files with uncommitted or recent changes.
2.  **Scope matching:** For each changed file, scan the loaded ADRs in
    `{PROJECT_CONTEXT_DIR}/adr/*.md` and directory context files for scope annotations that
    reference the changed file or its parent directory.
3.  **Targeted read:** For each scope match, read the changed file and the
    matching ADR decision statement or confirmation rule. Check for surface-level
    contradictions (e.g., ADR says "use WebSocket for mutations" but the file
    adds a direct REST call).
4.  **Fixture & Schema Conformance:** For database mutation scripts, reset
    utilities, or test fixtures, verify table names, column types, and enum
    literals against authoritative schema declarations (Protobuf definitions,
    SQL DDL, ORM models, or type interfaces). Verify that CLI tool wrappers obey
    execution constraints (e.g., single-statement execution vs batch piping).
5.  **Resolution:** If drift is detected:
    -   Present a `> [!WARNING]` callout naming the ADR/rule, the file, and
        the contradiction.
    -   Use `ask_question` with a randomized prompt:
        *   "Drift detected against {source}. How to handle?"
        *   "The code diverges from {source}. What's the call?"
        *   *Options*: `["Fix the code now", "Update the ADR",
            "Acknowledge as tech debt and proceed", "Show me the details"]`
    -   Handle the selection:
        -   **Fix the code now**: Apply a targeted fix before proceeding with
            the originally invoked command.
        -   **Update the ADR**: Draft an update or amendment to the relevant ADR
            and enter a Draft Review Loop.
        -   **Acknowledge as tech debt**: Log the divergence in the active
            track's `spec.md` under a `## Tech Debt` section (create if absent)
            and proceed.
        -   **Show me the details**: Display the full ADR text and the
            relevant diff, then re-present the resolution options.
5.  **No drift:** If no scope matches are found or no contradictions are
    detected, proceed silently — no output overhead.

## 10. ADR Capture Protocol

Architectural decisions and non-negotiable behavioral contracts (ordering
constraints, null-check requirements, state guards, initialization rules)
must be recorded in `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/NNNN-slug.md`.

### 3-Pillar Invariant Taxonomy

To prevent both missed architectural records (spec enclosure) and ADR hyper-inflation (bloat), decisions must satisfy at least one of three qualification pillars:

1.  **Cross-Cutting Invariant:** Establishes a convention, contract, or state
    invariant that constrains future tracks or touches multiple components
    (e.g., optimistic UI rollback rules, error-envelope schemas, multi-tab sync).
2.  **Architecture / Dependency Binding:** Binds the repository to a storage
    engine, transport protocol, or third-party library that would be costly to
    rip out later (e.g., SQLite WAL, WebSocket vs. SSE, Protobuf vs. JSON).
3.  **Negative Constraint (Discarded Alternative):** Rejects an obvious, standard
    pattern due to a subtle project gotcha or race condition (e.g., forbidding
    `sessionStorage` because it does not sync across tabs).

Decisions failing all three (local component markup, single route slugs, error strings, styling) are classified as `[Track Spec Only]`.

### Capture Triggers

ADR capture operates across a dual-stage lifecycle alongside targeted in-flight hooks:

1.  **Phase 5c Pre-Spec ADR Triage Gate** (`/arm-new-track` Step 5c):
    Immediately after Phase 5b Devil's Advocate resolves, the agent audits all
    settled decisions (listed under `**Settled**` in the progress list) against
    the 3-Pillar Taxonomy.
    -   *Silent Zero-Candidate Bypass:* If zero decisions qualify, the agent
        silently transitions to Step 6 without an extra modal turn.
    -   *Interactive Triage Table:* If candidates qualify, outputs `### ADR
        Candidate Triage Table` and prompts via a multi-select `ask_question`
        modal in a single turn.
2.  **Stage 2 Track Closeout Harvest** (`/arm-implement` Step 4): During living
    documentation sync, the agent scans the final diff and verified test
    runbooks for emergent invariants introduced during implementation, offering
    to capture them or update ADR confirmation checklists.
3.  **During implementation** (`/arm-implement` Step 3): when the agent writes a
    guard, assertion, or safety constraint that extends beyond the active track.
4.  **During review** (`/arm-review` § 2.4): when a correctness finding implies an
    architectural rule or race condition fix.
5.  **User-initiated**: when the user explicitly states a non-negotiable rule.

### In-Flight Capture Interaction

At in-flight trigger points (triggers 3–5), the agent follows this protocol:

1.  Identify the architectural decision or behavioral contract (ordering
    constraint, state guard, initialization requirement).
2.  Present via `ask_question` with a randomized prompt:
    *   "This establishes an architectural rule: '{description}'. Record an ADR?"
    *   "A load-bearing constraint worth preserving: '{description}'. Capture it as an ADR?"
    *   *Options*: `["Yes — draft an ADR", "Yes, but rephrase it", "No — track-specific only"]`
3.  If accepted:
    -   Find the next sequential number (e.g., `0003-slug.md`).
    -   Draft the ADR following standard MADR format (`Status`, `Context`,
        `Decision`, `Consequences`, `Confirmation`).
    -   Save to `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/NNNN-slug.md`.

## 11. Per-Directory Context Protocol

For complex project modules, per-directory context reduces the context loading
tax by scoping what the agent reads to what's relevant for the current task.

### Section Format

Armature manages a `## Armature Context` (or legacy `## Conductor Context`) section inside existing agent context
files (`GEMINI.md`, `CLAUDE.md`, `AGENTS.md`, or `AGENT.md`). The section is
delimited by boundary comments:

```markdown
<!-- Armature Context: START (manual edits go above this line) -->
## Armature Context

### Purpose
{1-2 sentences describing the directory's role}

### Local Rules
{Directory-scoped rules, handler conventions, and failure handling policies}

### Relevant ADRs
- [ADR-NNNN: Title](file:///armature/adr/NNNN-slug.md)

### Key Types
{Primary exported types, classes, and functions}

### Term Overrides
{Terms used differently in this directory vs project-level terms.md}
<!-- Armature Context: END (manual edits go below this line) -->
```

### Multi-File Discovery & Creation

Before modifying files in a directory for the first time in a track, check
case-insensitively for existing agent context files: `GEMINI.md`, `CLAUDE.md`,
`AGENTS.md`, or `AGENT.md`.

-   **Discovery**: If any of these files exist and contain a `## Armature Context` or `## Conductor Context` section, use that file and do NOT prompt to create a new one.
-   **Appending**: If exactly one of those files exists but lacks a context section, append the `## Armature Context` section to that existing file rather than creating a second context file.
-   **Creation & Architectural Justification**: Do NOT automatically prompt to
    create a context file based on arbitrary file counts. Only prompt if there
    is a concrete architectural justification (multiple interacting services,
    complex stateful controllers, subtle local rules, or domain gotchas).
    If multiple files exist without a context section or if creating a new file
    from scratch, prompt the user via `ask_question` to select their preferred
    filename (`GEMINI.md`, `AGENTS.md`, `AGENT.md`, `CLAUDE.md`).
-   **Simple Directories**: If the directory is simple (straightforward UI
    components, simple utilities, or basic CRUD wrappers), skip prompting
    entirely.

### Loading

See context loading item 8 in `armature_protocol.md` §0a. The agent reads the
nearest context file (`GEMINI.md`, `CLAUDE.md`, `AGENTS.md`, or `AGENT.md`)
containing a `## Armature Context` or `## Conductor Context` section in the parent directory chain of
each file the current task touches. Innermost directory wins.

### Updates

At phase checkpoints, if the agent added new exports or discovered new local
rules in a directory, propose appending them to the directory's context file
section. Only modify content between the START and END boundary comments.
