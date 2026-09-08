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
4. **Execution Mode Selection Prompt (Upfront Mode Gate):**
   - If `--auto`, `--debug-port`, or `--watch` is explicitly provided via CLI arguments, proceed directly to the specified mode.
   - Otherwise, prompt the participant via `ask_question` to select their execution mode before scenario selection:
     - *Question:* "How would you like to run this bug bash session?"
     - *Options:*
       - `"(Recommended) Manual Interactive Guided Mode — Step-by-step co-pilot with exploratory HUD"`
       - `"Automated / Assisted Browser Mode (Playwright CDP) — Connect to local Chrome on port 9222 and record trace/video evidence"`

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

4. **Automated & Assisted Browser Execution Modes (Playwright CDP):**
   When executable `recipes/<scenario_id>.json` files are present (or the user passes `--auto`, `--debug-port=9222`, or `--watch`), `/arm-bash` supports browser automation powered by Playwright (`playwright.chromium.connectOverCDP('http://localhost:9222')`):
   - **Mode A: Autonomous Headless Execution (`--auto`):**
     - **Upfront Failure-Handling Policy Gate (`--on-fail=log|prompt|fix`):** Before starting an automated batch sweep, if `--on-fail` is not specified via CLI flags, prompt the user via `ask_question` to select their failure policy:
       1. `(Recommended) Log & Continue Sweep (Batch Mode)` — Record trace, video, and screenshot evidence for all failing scenarios without modifying source code mid-sweep.
       2. `Pause & Prompt on Failure (Interactive Fixer Mode)` — Halt immediately on any failed assertion, display the recorded evidence, and ask whether to self-fix the code and re-run or log and continue.
       3. `Autonomous Self-Fix & Re-Verify (Solo Polish Mode)` — Attempt a localized code fix (capped at 1 retry), re-run to verify, and log the defect if the retry does not pass.
     - Runs Playwright with `--headless=new` (reserving `chrome-headless-shell` strictly for resource-constrained CI matrix runners).
     - Automatically records video (`evidence/<scenario_id>_execution.webm`), captures a final screenshot (`evidence/<scenario_id>_final.png`), and evaluates DOM/console invariants (`evidence/<scenario_id>_dom_state.json`).
   - **Mode B: Local Workstation Chrome CDP (`localhost:9222`):**
     - When Automated or Assisted Browser Mode is selected, assume the engineer is running on a local development workstation (Linux/macOS) and output instructions to launch Chrome locally with remote debugging enabled:
       ```bash
       google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug "<target_url>"
       ```
     - **Mandatory Port `9222` Connectivity Probe:** Before connecting Playwright via `chromium.connectOverCDP('http://localhost:9222')`, run `curl -s --max-time 3 http://localhost:9222/json/version` via terminal.
       - If the probe succeeds (returns JSON with `"Browser"` version), proceed immediately to connect Playwright.
       - If the probe fails or times out, pause and ask the user via `ask_question`: *"Port 9222 is not reachable on localhost. Have you launched Chrome with `--remote-debugging-port=9222`?"*
   - **Mode C: Exploratory Instant Capture (*"Capture this bug"*):**
     - While testing interactively in a browser tab connected via CDP, if the user reports an unexpected bug, immediately capture the screenshot (`evidence/exploratory_<N>.png`) and console error traces via Playwright CDP without manual DevTools copying.
   - **Mode D: Continuous Regression Watch (`--watch`):**
     - Continuously monitors selectors or network responses during the bug bash session.

---

### 5. Session Wrap-Up & Handoff

1. When the participant finishes testing:
   - Commit their personal log files:
     ```bash
     git add {PROJECT_CONTEXT_DIR}/bug-bash/<slug>/logs/<handle>_findings.jsonl {PROJECT_CONTEXT_DIR}/bug-bash/<slug>/<handle>_<slug>.md
     git commit -m "docs(bug-bash): log <slug> findings for <handle>"
     ```
   - Remind the participant that their findings are safely recorded and ready for post-bash triage via `/arm-bug-bash-triage`.
