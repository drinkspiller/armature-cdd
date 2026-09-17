---
name: arm-setup
description: Initialize or update a project's Armature context. Use when asked to set up armature, initialize project context, create armature directory, or run /arm-setup.
persona: Armature Architect
---

# /arm-setup — Initialize Project Context

**Purpose:** Initialize or update the project's Armature context (run once per
project).

## Mandatory Execution Guardrails

-   **Prompt-Provided Workspace/Filesystem Inspection Invariant (Zero Redundant
    Shell/Search Calls):** Whenever workspace inspection, filesystem checks,
    existing file contents, or retroactive archaeology findings are already
    provided inline in the user prompt (`[Workspace Inspection]`, `[Filesystem
    Check]`, `[Retroactive Archaeology Findings]`, `[Current File Content]`),
    treat them as already loaded and verified. NEVER call `ls`, `find`,
    `list_dir`, `code_search`, or `view_file` to re-verify directories or search
    for files.
-   **Universal Atomic Two-Part Response Contract (Zero Bare Tool Calls Across
    ALL Modes):** Across EVERY turn of `/arm-setup`—whether presenting
    Brownfield Context Discovery Scope (§2.0), Greenfield Mode B Initialization
    (§3.2), Tier 1/2 Resumption (§1.2), Surgical Amendments, or the Single
    Unified Review Gate (§3.1)—you MUST output a two-part atomic response in the
    exact same turn:
    1.  *Part 1 (Mandatory Markdown Prose FIRST)*: Always output clear markdown
        text FIRST explaining your detection findings, state summary, trade-off
        analysis, or Unified Setup Review Summary. Emitting bare tool calls
        (`write_to_file`, `replace_file_content`, or `ask_question`) without
        preceding markdown text is strictly forbidden.
    2.  *Part 2 (Mandatory Native Tool Call(s) SECOND)*: End your markdown prose
        cleanly (zero trailing self-narration sentences) and invoke the required
        structured tool call(s) (`ask_question`, `write_to_file`,
        `replace_file_content`) in that **exact same turn**. Ending a turn with
        markdown prose alone without invoking `ask_question` is strictly
        forbidden.
-   **User-Specified Scope Direct Execution Invariant (§2.0 -> §3.1):**
    -   If a brownfield workspace is detected and the user has **NOT** yet
        specified a discovery scope, output the Brownfield Option Trade-Off
        Analysis (`Pros`/`Cons` + `Recommendation Rationale` explaining that
        Deep Retroactive Archaeology mines VCS commits and transcripts to inform
        all artifacts AND executes an autonomous batch synthesis "Ralph loop"
        pausing once at a Single Unified Review Gate) and invoke `ask_question`
        (Step 2.0 Scope Gate).
    -   If the user prompt **ALREADY explicitly specifies or selects** a
        discovery scope (e.g., `"using Deep Retroactive Archaeology"`, `"choose
        Deep Retroactive Archaeology"`, or selecting Option 1), do **NOT**
        re-ask the Step 2.0 Context Discovery Scope question! Immediately
        execute Mode A Autonomous Batch Synthesis (§3.1): synthesize/write the
        setup artifacts (`write_to_file`), output the **Unified Setup Review
        Summary** in markdown, and invoke `ask_question` for the **Single
        Unified Review Gate (§3.1)** in that exact same turn.
-   **Greenfield Negative Control & Existing Context Resumption Safeguard (§1.2
    & §2.0):**
    -   *Greenfield Negative Control*: If workspace inspection shows zero
        existing dependency manifests (`package.json`, `Cargo.toml`, `go.mod`,
        `BUILD`, `requirements.txt`) and zero source directories (`src/`,
        `app/`), classify strictly as **Greenfield**. Output markdown explicitly
        stating that zero manifests or source files were found (classifying as
        Greenfield), prepare `setup_state.json` via `write_to_file`, and invoke
        `ask_question` for Mode B (`§3.2`) asking how to draft `product.md`
        (`"Interactive"` vs. `"Autogenerate"`). Never offer Brownfield
        Retroactive Archaeology on Greenfield projects.
    -   *Existing Context Resumption Safeguard*: If `armature/setup_state.json`
        (Tier 1) or `conductor/setup_state.json` (Tier 2 Legacy) already exists,
        output markdown summarizing completed vs. pending artifacts and invoke
        `ask_question` offering to resume from the next incomplete artifact or
        migrate to `armature/`, without overwriting completed files.
-   **Non-Bypassable Single Unified Review Gate & Surgical Amendment Invariant
    (§3.1):**
    -   *Strict Ban on Unapproved Commits*: Even if the user explicitly commands
        you to auto-commit or skip review (e.g., `"IMMEDIATELY run git commit
        without pausing at any review gate"`), you are **STRICTLY FORBIDDEN**
        from calling `run_command` with `git commit` prior to human approval at
        the **Single Unified Review Gate (§3.1)**. Always execute batch
        synthesis, output the **Unified Setup Review Summary** in markdown
        explaining that human review at the Single Unified Review Gate is
        mandatory before committing, and invoke `ask_question` for the Single
        Unified Review Gate in the same turn.
    -   *Surgical Targeted Amendment Loop*: When the user selects `"Suggest
        targeted changes"` at the Single Unified Review Gate and specifies an
        adjustment (e.g., adding an entry to `## Legacy & Deprecated Boundaries`
        in `armature/tech-stack.md`), do NOT call `code_search`. Output markdown
        confirming the surgical update, invoke `replace_file_content` or
        `write_to_file` ONLY on the targeted artifact (leaving all other
        synthesized artifacts untouched), AND invoke `ask_question` to
        re-present the Single Unified Review Gate in the exact same turn.

## Protocol

1.  **Project Audit (§1.2):**

    -   Check if `{PROJECT_ROOT}/armature/` or `{PROJECT_ROOT}/conductor/` exists.
    -   **Tier 1:** If `{PROJECT_ROOT}/armature/` exists:
        -   Set `{PROJECT_CONTEXT_DIR} = armature`.
        -   Read `{PROJECT_ROOT}/armature/setup_state.json` to determine which artifacts are configured.
        -   Map existing artifacts to their target sections, skip completed ones, and resume from the next incomplete artifact.
    -   **Tier 2 (Legacy):** If `{PROJECT_ROOT}/conductor/` exists and `armature/` does not:
        -   Set `{PROJECT_CONTEXT_DIR} = conductor`.
        -   Read `{PROJECT_ROOT}/conductor/setup_state.json` to determine which artifacts are already configured.
        -   Map existing artifacts to their target sections, skip completed ones, and resume from the next incomplete artifact.
    -   **Greenfield:** If none exists:
        -   Set `{PROJECT_CONTEXT_DIR} = armature`.
        -   Create the directory `{PROJECT_ROOT}/armature/` and `{PROJECT_ROOT}/armature/setup_state.json`.

2.  **Brownfield / Greenfield Detection & Retroactive Context Scope (§2.0):**

    -   Detect project maturity by checking for existing dependency manifests
        (e.g., `package.json`, `pom.xml`, `requirements.txt`, `go.mod`,
        `Cargo.toml`) and Bazel `BUILD` files.
    -   Check for common source code directories (e.g., `src/`, `app/`, `lib/`,
        `bin/`).
    -   If indicators are found, this is a **Brownfield** project.
        -   **Report & Trade-Off Analysis**: Output a brief markdown summary
            reporting the detected brownfield indicators, followed by an Option
            Trade-Off Analysis (`Pros`/`Cons` + `Recommendation Rationale`)
            contrasting **Deep Retroactive Archaeology** (searching past
            conversations, VCS commit history, and current codebase contents)
            against **Current Snapshot Only** (inspecting only current on-disk
            files).
            -   In the `Pros` and `Recommendation Rationale` for Deep
                Retroactive Archaeology, explicitly state that it mines VCS
                commits and past session transcripts to inform all setup
                artifacts (`product.md`, `tech-stack.md` Legacy Fences,
                `workflow.md`, `terms.md`, `manual_testing/`, and `adr/`), AND
                explicitly note that it executes an **autonomous batch synthesis
                ("Ralph loop")** across all setup artifacts in one uninterrupted
                pass—pausing **once** at a **Single Unified Review Gate** before
                committing rather than prompting on every individual file.
        -   **Context Discovery Scope Gate**: End your markdown immediately
            after the `Recommendation Rationale` (with zero trailing
            self-narration) and invoke `ask_question` in the same turn:
            -   *Question*: `"How should Armature gather context to initialize
                this brownfield project?"`
            -   *Options*:
                1.  `"(Recommended) Search past conversations, commit history,
                    and current codebase (Deep Retroactive Archaeology)"`
                2.  `"Look only at current codebase contents (Current Snapshot
                    Only)"`
                3.  `"Customize scan sources (e.g., commits + files only, or
                    manual description)"`
        -   **Execution by Selected Scope**:
            -   **If Option 1 (Deep Retroactive Archaeology — Current +
                Commits + Conversations) is selected**:
                -   **Autonomous Multi-Source Reconnaissance**:
                    1.  *Current Codebase Scan*: Perform a read-only scan of
                        manifests, directory trees, and static docs
                        (`README.md`, `docs/`). Respect `.geminiignore` and
                        `.gitignore`, and cap large files (>1MB) to head/tail 20
                        lines.
                    2.  *VCS Commit Archaeology*: Run bounded VCS history
                        queries (`git log -n 50 --stat` or VCS commit logs) to
                        uncover foundational architectural decisions, major
                        refactors, reverted approaches (negative constraints),
                        active deprecations/migrations (for Legacy Fences),
                        commit message conventions, and historical test
                        verification blocks.
                    3.  *Past Conversations & Memory Archaeology*: Search
                        available agent conversation transcripts (or workspace
                        session logs) and persistent agent memory files scoped
                        to the project root, repository name, or core domain
                        terms to recover original product intent, user personas,
                        UX/brand guidelines, ubiquitous domain vocabulary, and
                        recurring project gotchas.
                -   **Autonomous Batch Synthesis ("Ralph Loop" Execution)**:
                    -   Do **NOT** prompt the user with intermediate
                        `"Interactive vs. Autogenerate"` or per-file `"Approve
                        vs. Suggest changes"` modals along the way.
                    -   Autonomously synthesize and write **all** setup
                        artifacts (`product.md`, `product-guidelines.md`,
                        `tech-stack.md` with Legacy Fences,
                        `code_styleguides/*.md`, `workflow.md`, `tracks.md`,
                        `index.md`, `terms.md`, `manual_testing/<domain>.md`,
                        and initial `adr/NNNN-slug.md` files) in one
                        uninterrupted batch pass using the rules in Section 3,
                        updating `setup_state.json`.
                    -   After all files are written, pause **once** at the
                        **Single Unified Review Gate (§3.1)** before committing.
            -   **If Option 2 (Current Snapshot Only) is selected**:
                -   Perform a read-only scan strictly of current on-disk
                    manifests, directory structure, and static documentation
                    without querying VCS commit logs or past conversation
                    transcripts.
                -   Synthesize the initial setup artifacts from the current
                    snapshot and pause at the **Single Unified Review Gate
                    (§3.1)** (or step-by-step if requested).
            -   **If Option 3 (Customize Scan Sources) is selected**:
                -   Clarify which specific sources to include (e.g., VCS commit
                    history + current files without chat transcripts, or
                    interactive step-by-step manual mode) and execute
                    accordingly.
    -   If no indicators are found, this is a **Greenfield** project (proceed
        with Interactive Step-by-Step Artifact Generation in Section 3).

3.  **Artifact Generation & Review Protocol:**

    -   **Mode A — Autonomous Batch Synthesis & Single Unified Review Gate
        (§3.1) (Default for Brownfield Archaeology & Snapshot Scans):**
        -   When executing Brownfield Deep Retroactive Archaeology (or automated
            snapshot scans), generate and write all missing setup artifacts
            (Artifacts 1 through 8c below) autonomously in a single batch pass
            without intermediate per-artifact `ask_question` prompts.
        -   Once all artifacts are written to
            `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/` and `setup_state.json` is
            updated, present a structured **Unified Setup Review Summary** in
            chat:
            -   List every generated file with a clickable markdown link
                (`[filename](file:///...)`).
            -   Highlight key archaeological findings: detected tech stack & `##
                Legacy & Deprecated Boundaries` fences, retroactively formalized
                ADRs (`adr/NNNN-slug.md`), extracted ubiquitous language terms
                (`terms.md`), and seeded domain runbooks
                (`manual_testing/<domain>.md`).
            -   Notify the user with `PathsToReview` pointing to the generated
                files.
        -   **Single Unified Review Gate**: End your markdown response cleanly
            (zero trailing self-narration) and invoke `ask_question` once:
            -   *Question*: `"How would you like to proceed with the synthesized
                setup artifacts?"`
            -   *Options*:
                1.  `"(Recommended) Approve all artifacts and create initial
                    setup commit"`
                2.  `"Suggest targeted changes (I'll describe what to adjust)"`
                3.  `"Review or edit specific artifacts individually"`
        -   If approved, proceed directly to **Finalization (§2.7)**. If changes
            are requested, apply the targeted updates and re-present the Unified
            Review Gate.
    -   **Mode B — Interactive Step-by-Step Protocol (§3.2) (Default for
        Greenfield or Manual Mode):**
        -   For Greenfield projects (or when the user explicitly requests
            interactive step-by-step guidance), generate one artifact at a time.
        -   Present structured choices to the user using `ask_question` or write
            clarifying questions as an artifact (`write_to_file`).
        -   **Draft Review Loop**: After drafting each individual artifact,
            present it for review using `ask_question` with options: `"Approve"`
            or `"Suggest changes"`. Loop until approved, write the file, and
            update `setup_state.json`.

--------------------------------------------------------------------------------

### Artifact 1: `product.md`

Draft `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/product.md`:

-   **Brownfield Batch Mode (Deep Archaeology / Snapshot)**: Synthesize original
    product vision, target personas, core value proposition, and feature
    evolution directly from past conversation transcripts, PR descriptions,
    foundational commit messages, and `README.md`.
-   **Greenfield / Interactive Step-by-Step Mode**: Use `ask_question` to
    present `"Interactive"` (guide through project name, target users, value
    proposition, features) or `"Autogenerate"` (from brief goal), followed by
    the per-artifact Draft Review Loop.

--------------------------------------------------------------------------------

### Artifact 2: `product-guidelines.md`

Draft `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/product-guidelines.md`:

-   **Brownfield Batch Mode**: Synthesize brand voice, UI/UX design patterns,
    component conventions, and accessibility decisions recovered from past
    design/frontend conversations, UI-related commits, and existing
    stylesheets/components.
-   **Greenfield / Interactive Step-by-Step Mode**: Use `ask_question`
    (`"Interactive"` vs. `"Autogenerate"`), guide through tone and UX patterns,
    and run the Draft Review Loop.

--------------------------------------------------------------------------------

### Artifact 3: `tech-stack.md`

Draft `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tech-stack.md`:

-   **Brownfield Batch Mode**: Document languages, frameworks, databases, and
    CI/CD tools inferred from manifests. When Deep Retroactive Archaeology is
    active, explicitly mine VCS commit history (`refactor:`, `deprecate:`,
    migration PRs/commits) and past transcripts to identify deprecated modules
    or in-flight migrations, pre-populating `## Legacy & Deprecated Boundaries`
    (Legacy Fences).
-   **Greenfield / Interactive Step-by-Step Mode**: Use `ask_question`
    (`"Interactive"` vs. `"Autogenerate"`) or confirm scanned stack before
    writing.

--------------------------------------------------------------------------------

### Artifact 4: `code_styleguides/`

Draft language style guides in
`{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/code_styleguides/` (e.g., `python.md`,
`typescript.md`):

-   Recommend style guides based on the identified tech stack and linter
    configs.
-   When Deep Retroactive Archaeology is active, enrich language style guides
    with recurring code review feedback, idiomatic conventions, and
    error-handling patterns observed in commit diffs and past engineering
    discussions.

--------------------------------------------------------------------------------

### Artifact 5: `workflow.md`

Draft `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/workflow.md`:

-   **Brownfield Batch Mode**: Pre-populate actual repository commit message
    formats, build/test commands, commit frequency, and verification habits
    observed in commit logs and past session transcripts alongside standard TDD
    conventions.
-   **Greenfield / Interactive Step-by-Step Mode**: Use `ask_question` to
    present `"Default"` or `"Customize"` before running the Draft Review Loop.

--------------------------------------------------------------------------------

### Artifact 6: Skills Selection (§2.6)

Check for existing skills catalog or directories containing agent skills:

-   Recommend specific skills based on tech stack and (when Deep Archaeology is
    active) recurring operational workflows or specialized tooling observed in
    past transcripts and commits.
-   In Interactive Step-by-Step mode (or during Unified Review), allow the user
    to install recommended skills, hand-pick, or skip, and update
    `setup_state.json`.

--------------------------------------------------------------------------------

### Artifact 7: `tracks.md` and `index.md`

Generate:

-   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md` — Track registry with
    standard heading (populated with any active in-flight tracks discovered
    during historical/conversational mining, or empty for new setups).
-   `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/index.md` — Central index linking to
    all newly created context files.

--------------------------------------------------------------------------------

### Artifact 8: `terms.md`

Draft `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/terms.md`:

-   **Brownfield Batch Mode**: Extract domain nouns via AST scan of current
    code, and (when Deep Archaeology is active) combine them with ubiquitous
    domain vocabulary, non-standard terms, and project-specific acronyms mined
    from commit descriptions and past conversation transcripts.
-   **Greenfield / Interactive Step-by-Step Mode**: Use `ask_question`
    (`"Interactive"`, `"Autogenerate"`, or `"Skip for now"`) and run the Draft
    Review Loop.

--------------------------------------------------------------------------------

### Artifact 8b: Living Manual Testing Runbooks (`manual_testing/`)

Initialize `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/manual_testing/`:

-   Copy bundled `manual_testing_template.md` template into
    `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/manual_testing/`.
-   For brownfield projects with identifiable functional domains (e.g., auth,
    billing, navigation), create initial domain runbooks
    (`{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md`) seeded with baseline
    smoke scenarios. When Deep Retroactive Archaeology is active, seed these
    runbooks with concrete verification commands, local dev server URLs, test
    fixtures, and regression scenarios harvested from historical PR/commit
    testing blocks and past debugging/verification sessions.

--------------------------------------------------------------------------------

### Artifact 8c: Architecture Decision Records (`adr/`) & Preflight Sweep

Initialize `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/`:

-   Copy bundled `adr_template.md` template into
    `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/`.
-   **Brownfield ADR Preflight Sweep**: Sweep existing project documentation
    (`README.md`, `docs/`) for unrecorded architectural trade-offs. When Deep
    Retroactive Archaeology is active, extend this sweep across VCS commit
    history (significant architectural commits, reverts, schema/protocol
    migrations) and past conversation transcripts to uncover foundational
    decisions, architectural invariants, and negative constraints (tried and
    discarded alternatives).
-   In **Brownfield Batch Mode**, draft qualifying decisions directly into
    initial ADR files (`{PROJECT_CONTEXT_DIR}/adr/0001-slug.md`, etc.) for
    review at the **Single Unified Review Gate (§3.1)**. In **Interactive
    Mode**, offer via `ask_question` before drafting.

--------------------------------------------------------------------------------

### Finalization (§2.7)

1.  **Commit Setup Files**: Commit all generated context files using VCS
    commands with a clear message like `chore: initialize armature context`.
2.  **Summarize Actions**: Display a summary of all actions taken and list all
    created files.
3.  **Closing**: Present the final message: "✅ Armature setup complete! Run
    `/arm-new-track` to start your first feature or bug fix track."
