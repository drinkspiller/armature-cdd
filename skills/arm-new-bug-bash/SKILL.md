---
name: arm-new-bug-bash
description: Plan, scaffold, and launch structured team bug bash sessions. Automates test scenario generation from active feature tracks, provisions live tracking boards (GitHub Tracking Issues or VCS-native Markdown ledgers), configures test environments and accounts, and generates team launch invitations. Use when organizing a bug bash, preparing team QA charters, or executing /arm-new-bug-bash.
persona: Armature QA Architect
---

# /arm-new-bug-bash — Bug Bash Session Architect & Scaffolding

**Purpose:** Transform bug bashes from ad-hoc manual setup into structured, repository-grounded QA campaigns. Automatically extracts high-value test charters from active tracks, detects repository tracker capabilities (GitHub Issues via `gh` CLI vs. local VCS-native Markdown ledgers), codifies environment setup and test persona credentials, and produces a ready-to-share team launch invitation.

## Architectural Principles

1. **Intelligent GitHub & Tracker Environment Detection:** Automatically inspects `git remote get-url origin` and `gh auth status` at session creation:
   - **GitHub + `gh` Authenticated (Primary Path):** Provisions a pinned **GitHub Tracking Issue** (`gh issue create`) containing the scenario matrix and live claim board.
   - **GitHub + `gh` Unauthenticated:** Notifies the facilitator that `gh auth status` is inactive and gracefully falls back to a local VCS-native Markdown tracker (`TRACKER.md`) + per-user append-only JSONL logs (`.armature/bug_bash/<slug>/logs/`), allowing live GitHub sync to be enabled anytime via `gh auth login`.
   - **Non-GitHub VCS / External Issue Tracker (GitLab, Bitbucket, Jira, Linear):** Gracefully detects non-GitHub remotes without erroring on `gh` CLI calls, automatically configuring repository-native Markdown/JSONL tracking (`TRACKER.md`).
2. **Track-Grounded Scenarios:** Test charters are derived directly from `{PROJECT_CONTEXT_DIR}/tracks/` specifications, acceptance criteria, and living `manual_testing/` runbooks—never generic boilerplate.
3. **Strict Separation of Environment Tiers:** Preview/Dev deployments and Staging/QA tiers represent distinct release stages with different data persistence and debug flags. Never combine them into a single option.

---

## Protocol

### 1. Context & Track Discovery

1. **Resolve Project Root:**
   - Resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (`armature` or `conductor`) per `armature_protocol.md` §7.
2. **Scan Feature Tracks:**
   - Read `{PROJECT_CONTEXT_DIR}/tracks.md` and scan active/recent track directories under `{PROJECT_CONTEXT_DIR}/tracks/`.
   - Present a concise summary of candidate feature areas and ask the user which features or tracks to target for the bug bash.

---

### 2. Session Naming & Slug

1. Propose a descriptive session title (e.g., `"2026-09 Checkout & Cart Bug Bash"`) and a URL-safe slug (e.g., `2026-09-checkout-bash`).
2. Confirm or customize via `ask_question`.

---

### 3. Environment Tier & Persona Configuration

1. **Target Environment Selection:**
   Prompt the facilitator via `ask_question` to select the primary testing environment:
   - `(Recommended) Preview / Dev Branch Deployment (continuous branch preview URL)`
   - `Staging / QA Tier (release candidate soak environment)`
   - `Production Canary (live production verification)`
   - `Local Dev Server (localhost:<PORT> with local seed fixtures)`

   > **Strict Separation Invariant:** Preview/Dev Branch Deployments and Staging/QA Tiers MUST ALWAYS be presented as separate, distinct choices. Never merge them into a single option (e.g. never write `"Preview / Staging URL"`).

2. **Test Accounts & Fixtures:**
   - Prompt for test account credentials, seed commands, or feature flags participants need to activate the target scenarios.

---

### 4. Intelligent Tracker Provisioning

1. **Detect Repository & Tracker Capabilities:**
   Execute `git remote get-url origin 2>/dev/null || true` and `gh auth status 2>/dev/null || true`.
   - **Case A: GitHub Remote + `gh` CLI Authenticated:**
     - Create a dedicated **GitHub Tracking Issue** via `gh issue create`:
       ```bash
       gh issue create \
         --title "[Bug Bash] <Display Name>" \
         --body "<Generated Scenario Matrix & Instructions>" \
         --label "bug-bash"
       ```
     - Record the issue number and URL in `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/session.json` under `"tracker": { "type": "github_issue", "issue_number": <num>, "url": "<url>" }`.
   - **Case B: GitHub Remote + `gh` CLI Unauthenticated:**
     - Inform the facilitator: *"Detected GitHub repository, but `gh` CLI is not authenticated. Provisioning VCS-native tracker (`TRACKER.md` + per-user JSONL logs). Run `gh auth login` anytime to enable live GitHub Issue sync."*
     - Create `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/TRACKER.md` and set `"tracker": { "type": "local_markdown", "path": "{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/TRACKER.md" }`.
   - **Case C: Non-GitHub VCS / External Issue Tracker:**
     - Inform the facilitator: *"Detected non-GitHub remote/tracker. Using VCS-native tracking (`TRACKER.md` + conflict-free per-user JSONL logs)."*
     - Create `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/TRACKER.md` and set `"tracker": { "type": "local_markdown", "path": "{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/TRACKER.md" }`.

---

### 5. Scenario Matrix & Session Manifest Generation

1. **Write `matrix.md`:**
   - Generate `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/matrix.md` with categorized test scenarios (`ID`, `Feature Area`, `Scenario Title`, `Steps & Expected Outcome`, `Priority`).
2. **Write `session.json`:**
   - Save session configuration (`slug`, `title`, `environment`, `tracker`, `created_at`, `scenarios`) to `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/session.json`.

---

### 6. Launch Invitation & Handoff

1. **Generate Copy-Pasteable Team Invitation:**
   Output a clean markdown block ready to paste into Slack, Discord, or GitHub Discussions:
   - Include session title, target URL/environment, test credentials, live tracker link (GitHub Issue URL or `TRACKER.md`), and the exact participant command:
     ```markdown
     /arm-bash --session=<slug>
     ```
   - **Command Syntax Invariant:** The launch instruction MUST strictly display `/arm-bash --session=<slug>`. NEVER prefix the command with `@agent`, `@assistant`, or tool-specific handles.
