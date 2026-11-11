# Design System Contract (`DESIGN.md`)

> Single source of truth for visual tokens, component anatomy, and anti-slop
> rules across UI tracks. Generated via `/arm-setup` or `/arm-new-track` Step
> 5.5 (`ADR 0022`). Replaces UI visual sections of `product-guidelines.md` while
> keeping prose voice and CLI rules there.

## 1. Design Read & Register

-   **Surface Kind:** `<e.g., Web Workspace / Dashboard / Editor>`
-   **Audience (from `product.md`):** `<Target persona(s)>`
-   **Aesthetic Register:**
    `<e.g., Blueprint Studio / Editorial Paper / Tactile Darkroom>`
-   **Craft Dials (1–10):** Variance `<N>` · Motion `<N>` · Density `<N>`
-   **Source / Migration Notes:** `<e.g., Locked via 3-variant harness |
    Extracted from src/styles/tokens.css | Migrated from product-guidelines.md>`

## 2. Color Palette & Semantic Roles

Token Name                 | Hex       | Role                                          | Min Contrast Pair
:------------------------- | :-------- | :-------------------------------------------- | :----------------
`--color-bg`               | `#0f131a` | Canvas background                             | `--color-text` (>= 7:1)
`--color-surface`          | `#161b24` | Primary card / drawer surface                 | `--color-text` (>= 7:1)
`--color-surface-elevated` | `#1d2431` | Nested tonal container (no box-in-box stroke) | `--color-text` (>= 4.5:1)
`--color-text`             | `#edf2f8` | Primary readable text                         | `--color-surface`
`--color-text-muted`       | `#9aa7bc` | Secondary labels / captions                   | `--color-surface` (>= 4.5:1)
`--color-accent`           | `#7cc4fa` | Primary CTA & active selection                | `--color-on-accent` (>= 4.5:1)
`--color-on-accent`        | `#062840` | Text/icon on primary accent                   | `--color-accent`
`--color-success`          | `#8fd9a8` | Verified / healthy / chosen state             | `--color-surface`
`--color-warning`          | `#f5c373` | Partial / non-blocking caution                | `--color-surface`
`--color-error`            | `#f28b82` | Failure / destructive guard                   | `--color-surface`

## 3. Typography Scale

-   **Display / Headings:** `<Font Family, e.g., Inter or Plus Jakarta Sans>`, weights `500`,
    `600`; tight heading tracking `-0.015em`.
-   **Body Copy:** `<Font Family, e.g., Inter or system-ui>`, `14px` base (`1.5`
    line-height), max measure `68ch`.
-   **Monospace / Telemetry:** `<Font Family, e.g., JetBrains Mono or ui-monospace>`,
    `11.5px-12.5px` for IDs, counts, and status chips.

## 4. Spacing, Layout & Concentric Radii

-   **Spacing Rhythm:** `4px` base unit (`8px`, `12px`, `16px`, `24px`).
-   **Concentric Radius Law:** `R_inner = max(0, R_outer - padding)` (e.g.,
    `18px` card with `10px` padding -> `8px` inner rows).
-   **Multi-Line Lozenge Ban:** Never apply `9999px` pill radius to wrapping
    toolbars or multi-line banners; reserve pills strictly for fixed-height
    single-line buttons/chips (`height <= 40px`, `white-space: nowrap`).

## 5. Component Anatomy & Interactive States

-   **Required UI Stack Coverage:** Every key view/control must handle
    **Ideal**, **Empty**, **Loading**, **Partial**, and **Error** states.
-   **Interactive Physics:** Scope transitions explicitly (`transform`,
    `opacity`, `background-color`, `box-shadow` — never `transition: all`);
    active press feedback `translateY(1px) scale(0.985)` at `0ms`.
-   **Responsive Breakpoints:** Verify at `375px` mobile and `1280px` desktop
    with keyboard navigation and real `404`/empty fallbacks.

## 6. Banned Patterns (Anti-Slop Guardrails)

-   No raw hex literals in component styles or specs (reference `--color-*`
    tokens by name).
-   No 4-sided contrasting stroke boxes inside already bordered cards ("nested
    box fatigue").
-   No unrequested marketing carousels, generic purple gradients, or placeholder
    lorem-ipsum copy.
