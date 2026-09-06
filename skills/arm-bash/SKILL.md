---
name: arm-bash
description: Guide bug bash participants through interactive testing scenarios, balance coverage across feature areas, manage environment setup via the Hybrid Smart Gate, capture off-script bugs, and log findings without VCS conflicts. Use when participating in a team bug bash, running bug bash scenarios, or executing /arm-bash.
persona: Armature QA Facilitator
---

# /arm-bash — Interactive Bug Bash Facilitator & Coverage Balancer

**Purpose:** Act as an interactive pair-testing copilot for engineers participating in a bug bash. Loads session charters from `session.json`, balances test coverage across teammates, sets up local or preview test environments safely via the Hybrid Smart Gate, captures both scripted and exploratory bugs, and logs findings to conflict-free per-user files and live GitHub Tracking Issues.

## Architectural Principles

1. **Conflict-Free Per-User Logging:** Multiple engineers running `/arm-bash` concurrently must never hit Git merge conflicts. All findings are appended to per-user logs (`{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/logs/<github_handle>_findings.jsonl`) and per-user Markdown summaries (`{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/<github_handle>_<slug>.md`).
2. **Intelligent Live Tracker Updates:** Automatically checks `session.json` and `gh auth status`:
   - If `"tracker.type": "github_issue"` and `gh` CLI is authenticated, posts structured claim and finding updates to the GitHub Tracking Issue via `gh issue comment <issue_number>`.
   - If `gh` CLI is unauthenticated or `"tracker.type": "local_markdown"`, records all updates locally without failing or interrupting the testing flow.
3. **Hybrid Smart Gate Environment Setup:** Standard read-only or seed commands execute automatically, while any destructive command (`DROP`, `DELETE`, `TRUNCATE`, `rm -rf`, `reset`, `clean`, `wipe`) halts for explicit confirmation via `ask_question`.

---

## Protocol

### 1. Session Discovery & Participant Identity

1. **Resolve Project Root:**
   - Resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (`armature` or `conductor`) per `armature_protocol.md` §7.
2. **Identify Session:**
   - Check user arguments for `--session=<slug>`. If omitted, scan `{PROJECT_CONTEXT_DIR}/bug-bash/` for active sessions (`session.json`) and prompt via `ask_question`.
3. **Resolve Participant Handle:**
   - Detect Git/GitHub identity via `git config user.name` or `gh api user --jq .login 2>/dev/null` to name the participant's log files (`<handle>_findings.jsonl`).

---

### 2. Coverage Balancing & Scenario Selection

1. **Load Matrix & Existing Claims:**
   - Read `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/matrix.md` and scan existing participant logs in `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/logs/`.
   - If `"tracker.type": "github_issue"` and `gh` CLI is authenticated, check recent comments on the GitHub Tracking Issue (`gh issue view <issue_number> --comments`).
2. **Recommend Unclaimed Scenarios:**
   - Highlight scenarios with zero coverage first, followed by high-priority (`P0`/`P1`) charters.
   - Ask the participant which scenario they want to claim via `ask_question`.

---

### 3. Hybrid Smart Gate Environment Preparation

1. **Prerequisites & Service Startup:**
   - Display a clear `##### Prerequisites` block with exact startup commands (e.g., `npm run dev`, `docker compose up`) and fully qualified copy-pastable URLs (`http://localhost:<PORT>/<path>` or Preview URL).
2. **Execute Safe Setup / Gate Destructive Commands:**
   - Run non-destructive seed/setup commands automatically.
   - If a setup command contains destructive keywords (`reset`, `clean`, `wipe`, `DROP`, `DELETE`, `rm -rf`), prompt the user via `ask_question` before running.

---

### 4. Interactive Testing Loop & Defect Capture

1. **Step-by-Step Guidance:**
   - Walk the participant through the selected scenario's steps and expected outcomes.
   - Ask via `ask_question` whether the scenario passed (`Verified — works as expected`), failed (`Found a bug`), or uncovered an off-script defect (`Log an exploratory bug`).
2. **Structured Bug Capture:**
   - When a defect is reported, capture:
     - `title`: Crisp one-line summary
     - `severity`: `P0 (Blocker)`, `P1 (High)`, `P2 (Medium)`, `P3 (Low)`
     - `steps_to_reproduce`: Numbered steps
     - `expected_vs_actual`: Clear contrast
     - `evidence`: Console error traces, network logs, or screenshot/video paths
3. **Dual Write (Local JSONL + Live GitHub Comment):**
   - Append the JSON record to `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/logs/<handle>_findings.jsonl`.
   - Append a human-readable section to `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/<handle>_<slug>.md`.
   - If `"tracker.type": "github_issue"` and `gh auth status` succeeds, post a formatted update comment to the GitHub Tracking Issue:
     ```bash
     gh issue comment <issue_number> --body "🐛 **[<severity>] <title>** (found by @<handle> in Scenario <ID>)"
     ```

---

### 5. Session Wrap-Up & Handoff

1. When the participant finishes testing:
   - Commit their personal log files:
     ```bash
     git add {PROJECT_CONTEXT_DIR}/bug-bash/<slug>/logs/<handle>_findings.jsonl {PROJECT_CONTEXT_DIR}/bug-bash/<slug>/<handle>_<slug>.md
     git commit -m "docs(bug-bash): log <slug> findings for <handle>"
     ```
   - Remind the participant that their findings are safely recorded and ready for post-bash triage via `/arm-bug-bash-triage`.
