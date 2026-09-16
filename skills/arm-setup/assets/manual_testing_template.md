# Manual Testing Guide: {Domain / Feature Name}

> **Verification Scoping Policy**: Select **Tier 1** for stateful, route-guard,
> API, or database-mutating tracks. Select **Tier 2 (`[Micro-Verification
> Plan]`)** when the change footprint is strictly visual/presentational
> (HTML/CSS/SCSS or presentational JSX/TSX with Orphaned Dead-Code Cleanup
> Exemption).

--------------------------------------------------------------------------------

## Tier 1: Standard Stateful 3-Part Fixture Triad (Stateful / Full-Stack Footprints)

### 1. Environment & Prerequisites

-   **Service Stack**: `{Local dev server command, e.g., ./run.sh or npm run
    dev}`
-   **Required Environment Variables**: `{Key env vars or feature flags}`

### 2. Fixture Provisioning & Reset Tooling

Whenever database migrations or environment state mutations are involved,
document all three commands of the **3-Part Fixture Triad** in sequence:

```bash
# 1. Migration Command
{Exact command to apply schema or state migrations}

# 2. Seed / Fixture Setup
{Exact command to seed deterministic test fixtures}

# 3. Teardown / Reset Script
{Exact command to tear down test state and restore clean baseline}
```

### 3. Persona & Scenario Runbooks

#### Persona: {Persona Name (e.g., Unauthenticated Guest, Admin, Invited Member)}

##### Preconditions & State Setup

```bash
{Exact command to establish or reset state for this persona}
```

##### Test {Domain}.{ID}: {Scenario Title}

-   **Action**:
    {Exact URL (`http://localhost:<PORT>/<path>` and `http://<REMOTE_HOST>.example.internal:<PORT>/<path>`), CLI command, or UI action}
-   **Expected Outcome**:
    {Expected route, visual state, HTTP response, or database mutation}
-   **Barrier Checks**:
    {Negative verification proving unauthorized forward hops or invalid actions are blocked}

### 4. Resilience, Error Handling & Telemetry

--------------------------------------------------------------------------------

## Tier 2: Micro-Verification Plan (Visual-Only Footprints)

**Scope Tag:** `[Micro-Verification Plan]`

### 1. Environment & Prerequisites

-   **Local Dev Server**: `{Exact startup command, e.g., ./run.sh}`
-   **Session Hint**: `{Optional one-line session hint, e.g., Requires active
    logged-in session}`

### 2. Fixture Provisioning & Reset Tooling

> [!NOTE] Stateful 3-Part Fixture Triad deferred (initial track was
> visual-only).

### 3. Visual Verification Card & Scenarios

```text
┌─ [Micro-Verification Plan] ────────────────────────┐
│ Change detected: Visual-only (HTML/SCSS)           │
│                                                    │
│ [•] Step 1: Run local server (`./run.sh`) (requires active logged-in session) │
│ [•] Step 2: Navigate to `http://localhost:<PORT>/<path>` │
│ [•] Verify: {Visual assertion anchored on visible text / ARIA role} │
│                                                    │
│ (Database seeding and API testing skipped)         │
└────────────────────────────────────────────────────┘
```

#### Test {Domain}.{ID}: {Visual Scenario Title}

-   **Step 1 (Server & Session)**: `Step 1: Run local server (<cmd>) (requires
    active logged-in session)`
-   **Step 2 (Target URL)**: `http://localhost:<PORT>/<path>` *(Strictly use
    `localhost` URLs; never use remote workstation hostnames)*
-   **Verify (Visual Assertion)**:
    {Concise assertion anchored on visible text labels or semantic ARIA roles rather than brittle CSS classes}
-   **Inline Escape Hatch**: During `/arm-review`, the verification prompt
    provides an inline escape hatch option: `"Run full domain runbook instead
    (execute database seed & multi-role scenarios)"`.
