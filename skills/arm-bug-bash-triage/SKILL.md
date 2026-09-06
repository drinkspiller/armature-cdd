---
name: arm-bug-bash-triage
description: Triage, deduplicate, and file GitHub Issues from bug bash logs and live tracking boards, and seal sessions into living repository runbooks. Reconciles GitHub Tracking Issue comments with per-user JSONL/Markdown logs, clusters duplicate findings, queries existing issues for duplicates, files paced GitHub Issues (with TRIAGED_ISSUES.md fallback), and codifies verified failure modes into manual_testing/. Use after a bug bash session or when executing /arm-bug-bash-triage.
persona: Armature Triage Specialist
---

# /arm-bug-bash-triage — Post-Bash Triage, Deduplication & Sealing

**Purpose:** Provide post-bash triage, deduplication, and issue filing. Reconciles findings between the live GitHub Tracking Issue and per-user JSONL/Markdown logs, clusters duplicate reports across teammates, searches existing repository issues for duplicates, creates enriched issues with rate-limit protection (or exports structured Markdown payloads for non-GitHub trackers), and permanently codifies newly discovered failure modes into living domain runbooks.

## Architectural Principles

1. **Intelligent Tracker & Environment Detection:** Automatically inspects `session.json`, `git remote get-url origin`, and `gh auth status`:
   - **GitHub + `gh` Authenticated (Primary Path):** Searches existing issues via `gh issue list --search "<keywords>" --state all` for duplicate detection and files confirmed defects via `gh issue create` with a mandatory **2-second pacing delay (`sleep 2`)** between requests to prevent GitHub secondary rate-limit (`HTTP 403`) lockouts.
   - **GitHub + `gh` Unauthenticated OR Non-GitHub VCS / External Tracker (GitLab, Bitbucket, Jira, Linear):** Gracefully bypasses live `gh` API calls without errors and generates `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/TRIAGED_ISSUES.md` containing deduplicated issue dossiers ready for import or copy-pasting.
2. **Two-Stage Deduplication:** Eliminates duplicate filing debt through intra-bash clustering (merging multi-reporter instances of the same defect) followed by live issue search.
3. **Closing the Knowledge Loop:** High-severity failure modes that uncovered real defects are automatically promoted into `{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md`, turning temporary bug bash findings into permanent regression guards.

---

## Protocol

### 1. Initialization & Multi-Source Reconciliation

1. **Context Resolution:**
   - Resolve `{PROJECT_ROOT}` and `{PROJECT_CONTEXT_DIR}` (`armature` or `conductor`) per `armature_protocol.md` §7.

2. **Session Discovery:**
   - Check user arguments for `--session=<slug>`. If omitted, scan `{PROJECT_CONTEXT_DIR}/bug-bash/` for directories containing `session.json` and prompt via `ask_question`.
   - Read `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/session.json`.

3. **Multi-Source Ingestion:**
   - Read all per-user append-only JSONL logs in `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/logs/*.jsonl` and Markdown summaries in `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/*.md`.
   - If `"tracker.type": "github_issue"` and `gh auth status` succeeds, fetch comments from the GitHub Tracking Issue via `gh issue view <issue_number> --comments`.
   - Consolidate all reported defects into a unified triage queue.

---

### 2. Two-Stage Deduplication Engine

1. **Stage A: Intra-Bash Clustering:**
   - Group incoming defect reports by matching feature tracks, error message substrings, and semantic descriptions.
   - When multiple testers report the same issue, merge them into a single consolidated candidate combining all unique reproduction steps, error traces, and reporter handles.

2. **Stage B: Live Repository Issue Search:**
   - Check `git remote get-url origin` and `gh auth status`.
   - If GitHub + `gh` authenticated, query open and closed issues for each consolidated candidate:
     ```bash
     gh issue list --search "<core keywords>" --state all --limit 5
     ```
   - If a matching issue is found (e.g., `#142`), attach it as a potential duplicate.

---

### 3. Interactive Triage Gate

Present each consolidated defect candidate to the facilitator sequentially via `ask_question`:
- Display defect title, severity (`P0`–`P3`), reporters, reproduction steps, and any potential existing duplicate issue (`#<num>`).
- Options:
  - `(Recommended) File new issue`
  - `Mark as duplicate of existing issue #<num>`
  - `Adjust severity / title before filing`
  - `Discard / Works as intended`

---

### 4. Paced Issue Filing & Fallback Export

1. **GitHub + `gh` Authenticated Path (Paced Batch Creation):**
   - For each approved defect candidate, create a GitHub Issue via `gh issue create`:
     ```bash
     gh issue create \
       --title "[<Severity>] <Title>" \
       --body "<Consolidated Reproduction Steps, Expected vs Actual, Evidence & Reporters>" \
       --label "bug,bug-bash"
     sleep 2
     ```
   - **Rate-Limit Resilience Invariant:** Always enforce a **2-second delay (`sleep 2`)** between sequential `gh issue create` calls to prevent GitHub secondary rate-limit (`HTTP 403`) lockouts.
   - Post a summary comment on the GitHub Tracking Issue listing all created issue numbers (`#145`, `#146`, etc.).

2. **Unauthenticated / Non-GitHub Tracker Path (`TRIAGED_ISSUES.md` Fallback):**
   - If `gh` CLI is unauthenticated or the repository uses an external tracker (Jira, Linear, GitLab), generate `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/TRIAGED_ISSUES.md` containing:
     - Structured Markdown issue cards (Title, Priority, Labels, Description, Reproduction Steps) ready for copy-pasting or CSV/JSON import.
     - Ready-to-execute `gh issue create` commands in a collapsible code block.

---

### 5. Sealing & Living Runbook Promotion

1. **Promote Regression Scenarios:**
   - For every confirmed `P0` or `P1` defect, append a regression verification scenario to `{PROJECT_CONTEXT_DIR}/manual_testing/<domain>.md`.
2. **Generate Session Summary:**
   - Write `{PROJECT_CONTEXT_DIR}/bug-bash/<slug>/SUMMARY.md` documenting total participants, scenarios covered, issues filed, and promoted runbook checks.
