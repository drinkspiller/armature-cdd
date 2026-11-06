# CDD & SDD Evaluation Synthesis Report
## Comprehensive Benchmark & Architectural Analysis for Armature v0.19.0

**Date:** August 25, 2026  
**Author:** Staff Engineer & User Advocate  
**Target Assistant:** Armature (v0.19.0 Migration from Conductor)  
**Paradigms Evaluated:** Context-Driven Development (CDD) vs. Spec-Driven Development (SDD)  
**Scenarios:** 30 Scenarios per Framework (totaling 180 test runs across 6 open-source frameworks)

---

## 1. Executive Summary & Scorecard

The comprehensive CDD/SDD evaluation has completed. Across the 30 evaluation scenarios representing real-world brownfield development, conversational detours, surgical hotfixes, document drift audits, and destructive safety checks, the frameworks achieved the following final standings:

| Rank | Framework Configuration | Paradigm | Passed / Total | Pass Rate (95% CI) | Avg Tokens / Task |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **#1** | **Armature (OSS)** *(this)* | Context-Driven Development (CDD) | **102 / 120** | **85.0%** (±6.4%) | 2263 tokens |
| **#2** | **BMAD Method** | Multi-Agent Agile SDD | **79 / 120** | **65.8%** (±8.5%) | 2634 tokens |
| **#3** | **GitHub Spec Kit** | Spec-Driven Development (SDD) | **76 / 120** | **63.3%** (±8.6%) | 2835 tokens |
| **#4** | **Conductor (Canonical Upstream CLI)** | Context-Driven Development (CDD) | **59 / 120** | **49.2%** (±8.9%) | 2346 tokens |
| **#5** | **OpenSpec** | Lightweight SDD | **48 / 120** | **40.0%** (±8.8%) | 1597 tokens |
| **#6** | **Memory Bank (Cline / Roo Code)** | Stateful Agent Memory | **47 / 120** | **39.2%** (±8.7%) | 2703 tokens |

---

## 2. Core Paradigm Findings & Architectural Trade-offs

The evaluation highlighted a fundamental architectural divide:

### A. The "Rigid SDD" Penalty (Coordination Tax vs. Surgical Velocity)
SDD frameworks (`GitHub Spec Kit`, `BMAD Method`) excel at **Spec Gating (Pillar 1)** and **Drift Governance (Pillar 4)**, but suffer from severe overhead on minor fixes. 
*   **Surgical Hotfix Failures (SCEN_13 - SCEN_18):** When tasked with a 1-line environment variable rename or a minor composite database index column reordering, SDD agents generated multi-page PRDs, C4 architecture diagrams, and forced multi-role agile ceremony (PM, Solution Architect, Scrum Master sign-offs).
*   **Token Friction:** This coordination tax resulted in token usage that was 2x to 3x higher than necessary and introduced severe developer friction via interactive question gates for trivial changes.

### B. The "Stateful Memory" Trap (Memory Bank / Cline)
Stateful memory agents (`Memory Bank`) perform well at preserving task context across long detours. However:
*   **Decoupled State:** They frequently fall into a trap where the internal "Memory Bank" markdown files become decoupled from filesystem reality.
*   **Drift Blindness (0% Drift Governance):** Memory Bank failed to detect out-of-band changes that directly violated ADR-0003 (Transaction Isolation) or ADR-0007 (Retired Services) because it only read its own memory bank instead of scanning the workspace files and ASTs directly.

### C. Context-Driven Development (CDD) Success
Advanced CDD frameworks (`Armature OSS`) successfully bridged this gap by implementing **Ceremony Scaling**. 
*   **Dynamic Ceremony:** They skipped spec-drafting and formal gating for surgical fixes (<5 lines of change), generating direct and minimal diffs.
*   **AST and Workspace Scanning:** They enforced drift auditing by cross-referencing workspace diffs directly against living repository artifacts, ADRs, and term registries.

---

## 3. Reconciliation of Key Scenario Failures

To ensure Armature v0.19.0 retains a rigorous quality standard, we reconciled key scenario failures:

### SCEN_03_GRAPHQL_FEDERATION_SCHEMA_MERGE (Directives & Circular Dependency)
*   **Challenge:** Apollo Federation entity `@key` directives require `@shareable` or `@provides` directives to safely split fields between product and inventory subgraphs, plus checking circular dependency risks.
*   **Resolution:** Armature's schema migration rules mandate a structured checklist for federation merges, parsing GraphQL schema fields and checking field duplication rules before planning.

### SCEN_05_REST_V1_TO_V2_AUTH_CUTOVER (RFC 6750 & 401/403 Distinction)
*   **Challenge:** Distinguishing between returning 401 Unauthorized (missing/invalid tokens) vs. 403 Forbidden (deprecated credentials) with RFC 6750 Bearer token compliance and dual-support grace periods.
*   **Resolution:** Armature's protocol references RFC 6750 standards and mandates a dual-support rollover grace period.

### SCEN_06_OPENAPI_CONTRACT_TYPEGEN_GATE (Consistency & Sign-off)
*   **Challenge:** Generated TypeScript types must be validated against OpenAPI specs for nullable vs optional property parity before disk mutation.
*   **Resolution:** Introduced strict gating in the code generation flow: generated files representing API boundaries must be presented in markdown first for user verification.

### SCEN_09_DATABASE_LOCK_DEADLOCK_DETOUR (OCC Trade-offs & Verifiable Artifacts)
*   **Challenge:** Explaining deterministic locking order (sorting entity IDs) alongside Optimistic Concurrency Control (OCC) trade-offs without hallucinating undefined tables.
*   **Resolution:** Enforced completeness checks ensuring all proposed entities are defined in the active data model before proceeding to implementation.

### SCEN_25_DESTRUCTIVE_EXECUTION_SAFETY (Refusal Barriers & Additive Testing)
*   **Challenge:** Autonomous execution of destructive commands (drops, purges, node drains) without explicit secondary confirmation.
*   **Resolution:** Reinforced the documentation-only command policy. Armature strictly refuses autonomous execution of destructive database or environment operations, requiring pre-verification `SELECT COUNT(*)` checks and explicit user confirmation.

---

## 4. Architectural Invariants for Armature v0.19.0

1.  **Preserve Backward Compatibility (§7):**
    *   Transparently discover `{PROJECT_ROOT}/armature/` (primary) and `{PROJECT_ROOT}/conductor/` (legacy fallback) with zero mandatory migrations.
2.  **Ceremony Scaling:**
    *   Dynamically scale process overhead: surgical fixes (≤5 lines) bypass spec gating and emit minimal diffs with test commands.
3.  **Active Workspace Auditing (No Amnesia):**
    *   Verify active code and AST surfaces against local Architecture Decision Records (`adr/`) and ubiquitous terminology (`terms.md`).
4.  **Enforce Safe Execution Boundaries:**
    *   Mandate confirmation gates for all destructive operations. Output commands as documentation runbooks rather than executing autonomously.
