---
name: arm-chat
description: Load all Armature or Conductor project context (product, tech-stack, guidelines, workflow, active tracks) and proceed immediately to the user's task. Use when asked to "use armature context", "load armature", "armature chat", or when the user wants to work with context without creating tracks or running the full ceremony.
persona: Armature Guide
---

# /arm-chat — Context-Primed Freeform Agent

**Purpose:** Rapidly ingest all Armature/Conductor project knowledge into context and
then proceed directly to the user's task — no follow-up questions, no new
tracks, no approval gates. This is the lightweight complement to the full
Armature workflow.

## When to Use

-   The user wants to leverage existing project knowledge to inform a
    coding task, research question, or design decision.
-   The user wants to "just go" with project context without the ceremony of
    creating tracks, specs, or plans.
-   The user invokes `/arm-chat` or asks to "load armature context."

## Protocol

### Step 1: Locate the Context Directory

> [!NOTE] Project root resolution is handled by `armature_protocol.md` §7.
> If protocol §7 has already resolved `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}`, skip directly to Step 2.

1.  **Resolve Context Directory**: Follow `armature_protocol.md` §7 to resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (armature or conductor).
2.  **Validate** that at least `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/product.md` exists. If not, suggest running `/arm-setup`.

### Step 2: Tiered Context Loading

Load the project context in two tiers. Read files silently — do NOT produce
artifacts, summaries, or status reports for the loading process itself.

#### Tier 1: Core Context (always loaded)

Read the following files in order:

1.  `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/product.md` — Product definition & vision
2.  `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/product-guidelines.md` — Tone, visual identity, UX
3.  `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tech-stack.md` — Technical choices & frameworks
4.  `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/workflow.md` — Task workflow & coding practices
5.  `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md` — Track registry

#### Tier 2: Active Track Context (loaded selectively)

1.  Parse `tracks.md` for all tracks. Identify tracks marked as in-progress (`[~]`) or pending (`[ ]`).
2.  For each active or pending track, read `spec.md` and `plan.md`.
3.  Skip archived tracks unless requested.

#### Tier 2b: Code Style Guides (loaded if present)

If `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/code_styleguides/` exists, read all files in it.

#### Tier 2c: Manual Testing Runbooks (loaded on demand)

If the user's task touches files mapped to a specific domain (or active domain terms from `terms.md`), load `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md` on demand.

### Step 3: Act on the User's Task

After context is loaded, determine next action:

-   **If prompt contains a task/question:** Proceed immediately to fulfilling it using standard agent tools.
-   **Continuous Manual Testing Maintenance**: Whenever implementation introduces new functionality or route changes:
    -   Update `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md` (or track `manual_testing.md`).
    -   Use structured scenario headers (`### Test <Domain>.<ID>: <Scenario Title>`).
    -   **Documentation-Only Invariant**: Do NOT execute mutative database or reset commands autonomously.
    -   Write updated guide as artifact (`arm_manual_testing_<domain>.md`).
    -   In response, provide clickable markdown link to the file.
-   **If no accompanying prompt:** Announce context is loaded and ask what the user would like to work on.

## Guardrails

-   **Permitted File Updates**: You are explicitly permitted to update `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md`.
-   **Read-Only Files**: Do NOT modify `product.md`, `tech-stack.md`,
    `product-guidelines.md`, `tracks.md`, or track `spec.md`/`plan.md` unless
    requested (or when persisting a Legacy Fence via the Reactive Self-Healing
    Steering Hook).
-   **No Ceremony**: Do NOT create artifacts for the loading process.
-   **Legacy-Boundary Context Fences (Mandatory Single-Turn Execution Rules)**:
    -   *Prompt-Provided Context Invariant*: If `[Workspace Context...]` is
        provided in the prompt, NEVER call `grep_search` or `view_file` to look
        up `product.md` or `tech-stack.md`. Act immediately on the user request
        in the same turn.
    *   **Session Banner (Adaptive Verbosity)**: Whenever `tech-stack.md` (`##
        Legacy & Deprecated Boundaries`) or active track `metadata.json`
        (`legacy_fences`) defines active legacy fences, you MUST render an
        explanatory user-facing banner at the very top of your response using
        **Adaptive Verbosity**:
        -   **First turn in a session (Turn 1 — Full Callout):**
            ```markdown
            > [!NOTE]
            > **Working in `<active_replacement_basename>/`:**
            > * `<active_replacement_full_path>`
            >
            > **Skipping <N> deprecated folder(s):**
            > * `<deprecated_path_1>`
            > * `<deprecated_path_2>`
            >
            > _Code boundaries defined in `<source_config_file>`. Want to add/edit an ignored folder? Just ask!_
            ```
        -   **Subsequent turns in the same session (Turn 2+ — Compact 1-Line Reminder):**
            ```markdown
            > 🛡️ **Deprecated code boundary active:** Working in `<active_replacement_basename>/` (ignoring `<deprecated_basename_1>/`, `<deprecated_basename_2>/`).
            ```
    *   **Query-Time Negative Search Exclusion & Modern Scope (`TRAIN_LF_01`)**:
        -   State explicitly in your markdown text that you are directing
            analysis and search exclusively to the modern replacement path
            `<modern_replacement>`.
        -   When calling `grep_search`, include BOTH the modern scope and the
            anchored RE2 negative file filter in `Query`: e.g. `Query: "<symbol>
            f:<modern_replacement> -f:^<deprecated_path>"`.
        -   When calling `grep_search`, set `SearchPath: "<modern_replacement>"`
            and include `Excludes: ["**/<deprecated_path>/**"]`.
        -   NEVER call `view_file` on any file inside `<deprecated_path>` unless
            authorized by Direct Cross-Boundary Import Exemption or explicit
            user unlock.
    *   **Zero-Match Fallback Protocol (`VAL_LF_01`)**:
        -   If a search in active modern code (`<modern_replacement>`) returns
            `0 matches` and matches exist in `<deprecated_path>`, DO NOT call
            `view_file` on the legacy file.
        -   State clearly in markdown that `0 matches were found in active
            modern code (<modern_replacement>), but matches exist in
            legacy-fenced <deprecated_path>`, and invoke `ask_question` in the
            same turn:
            -   Prompt: `"Are you sure you want to proceed?"`
            -   Options:
                1.  `"(Recommended) Redirect analysis to modern replacement
                    (<modern_replacement>)"`
                2.  `"Yes, unlock READ access to <deprecated_path> for the
                    remainder of this chat session"`
                3.  `"No, skip legacy files"`
    *   **Direct Cross-Boundary Import Read Exemption (`TRAIN_LF_03`)**:
        -   If an active modern file in `<modern_replacement>` explicitly
            imports (`import`, `require`, `#include`) a file located inside a
            fenced `<deprecated_path>`, do NOT halt with an `ask_question` modal
            and do NOT call `grep_search` on the modern file.
        -   Immediately output markdown text containing the exact inline
            provenance badge `[Legacy Dependency Read: <full_legacy_file_path>]`
            explaining that direct cross-boundary imports are permitted in
            Read-Only Reference Mode, AND call `view_file` directly on that
            imported legacy file (`AbsolutePath: "<full_legacy_file_path>"`) in
            the exact same turn. Strictly forbid calling `replace_file_content`
            or `write_to_file` on that legacy file.
    *   **Reactive Self-Healing Steering Hook (`TRAIN_LF_04`)**:
        -   When a user steers you away from a deprecated/legacy path mid-prompt
            (e.g., *"Wait—`old_portal/` is deprecated, check `new_portal/`
            instead!"*), you MUST in the **exact same single turn**:
            1.  Immediately pivot to the modern replacement
                (`packages/new_portal/avatar.ts`) and provide the
                **definitive technical answer** (e.g., explaining that
                `user_avatar` was replaced by camelCase `avatarUrl` in
                `AvatarProps`) in your markdown text response FIRST without
                stalling or deferring investigation.
            2.  Invoke `view_file` (or search) on the modern replacement
                (`packages/new_portal/avatar.ts`).
            3.  Invoke `ask_question` at the end of that exact same turn
                offering to persist the newly discovered legacy boundary
                (`packages/old_portal/ -> packages/new_portal/`) with
                exact options:
                -   `"(Recommended) Save as Repository-Wide Legacy Fence in
                    armature/tech-stack.md"`
                -   `"Save as Track-Only Legacy Fence in metadata.json"`
                -   `"Keep for this chat session only (do not write to files)"`
