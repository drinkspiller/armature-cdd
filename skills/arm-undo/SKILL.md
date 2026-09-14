---
name: arm-undo
description: Undo work from a track, phase, or task using VCS-aware rollback. Use when asked to undo a track, undo changes, roll back work, or run /arm-undo.
persona: Armature Surgeon
---

# /arm-undo — Undo Work

**Purpose:** Undo work from a track, phase, or task using VCS-aware rollback.

## Protocol

### 1. Setup Check

1.  **Context Resolution & Tracks Check:**
    -   Resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (armature or conductor) per `armature_protocol.md` §7.
    -   Verify `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md` exists and is not empty. If missing or empty, halt execution and inform user that Armature is not initialized or there are no tracks to undo.

### 2. Interactive Target Selection

Determine what the user wants to undo.

*   **PATH A (Direct):** If the user provided a target argument (e.g., a task description or track name), find it in `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks.md` or the active `plan.md`. Present a structured choice to the user via `ask_question` to confirm:
    *   1. Yes, undo this target.
    *   2. No, select something else.
*   **PATH B (Guided Menu):** If no argument was provided, or if the user chose to select something else:
    *   Scan ALL `tracks.md` AND every track's `plan.md`.
    *   Prioritize in-progress items (`[~]`).
    *   Fallback to the 3 most recently completed items (`[x]`).
    *   Present a unified hierarchical menu (max 4 items) as a structured choice via `ask_question`.

Wait for the user to make a selection.

### 3. VCS Reconciliation

Once the target is selected, gather the commits to revert from VCS history.

1.  **Find Primary SHAs:** Locate primary SHA(s) or revisions recorded in `plan.md` for the target.
2.  **Handle "Ghost" Commits:** If a recorded SHA is missing (e.g., rewritten from rebase or squash), search VCS log for a similar commit message. If found, ask user to confirm using new SHA via `ask_question`.
3.  **Find Associated Updates:** Find associated plan-update commits (commits that modified `plan.md` after each implementation commit).
4.  **Find Track Creation Commits:** For TRACK level undo operations, also find track creation commit.
5.  **Compile List:** Compile full list of commits to revert. Check for merge commits and cherry-pick duplicates to avoid duplicate revert operations.

### 4. Final Execution Plan

Before executing the rollback, present a plan to the user using an Antigravity artifact.

1.  **Preview the Undo:** Write an undo preview as an Antigravity artifact (`arm_undo_preview.md` using `write_to_file`). The artifact should contain:
    *   The target being undone.
    *   The total number of commits.
    *   List of each SHA/revision with its commit message.
    *   The planned action: reverting commits in reverse order.
2.  **Ask for Approval:** Present artifact to the user and offer options via `ask_question`: "Approve", "Revise".

    **Do not execute the rollback without explicit confirmation.**

### 5. Execution & Verification

1.  **Execute the Rollback:** Use VCS commands to revert each commit, working from most recent to oldest.
2.  **Handle Conflicts:** If merge conflicts occur during the revert process, halt execution immediately and provide user with manual resolution instructions. Do not attempt to auto-resolve complex revert conflicts.
3.  **Verify Plan State:** After successful revert operations, read `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/plan.md` to ensure reverted items are correctly reset (e.g., tasks back to `[ ]`, SHAs removed).
4.  **Fix Plan State:** If the revert operations did not correctly reset `plan.md` or `tracks.md` state, manually edit files to reflect reverted state and commit correction with message: `armature(undo): Manually fix plan state for <target>`.
5.  **Confirm Completion:** Inform the user: "✅ Undo complete. The target has been reset. Run `/arm-status` to see current state."
