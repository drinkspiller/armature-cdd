# Automated Live-App Screencast Recording & Host Adapter (`ADR 0019`, `ADR 0020`)

This reference defines the risk-scoped live-application screencast and
screenshot capture protocol, variable-speed timelapse engine, TrustedTypes-safe
DOM overlay contract, prerequisite pre-flight checker, and Host Screencast
Adapter boundary used by `/arm-review` (`Steps 2.1, 2.5, 3.1, and 3.2`).

## 1. Risk-Scoped Trigger Matrix (`ADR 0010` + `ADR 0019`)

Recording behavior scales automatically with the Stage 2 Empirical VCS Diff
Classification (`ADR 0010`) unless overridden by `--record` (force enable) or
`--no-record` (force disable):

<!-- mdformat off(prevent table wrapping) -->
| Empirical Footprint Tier | Default `/arm-review` Behavior | Capture Artifact Scope |
| :--- | :--- | :--- |
| **Tier 0: Non-UI (Docs, Config, Backend Refactor, CLI)** | Skip recording prompt automatically (unless `--record` is passed) | None (`0` browser launches) |
| **Tier 2: Visual-Only (`[Micro-Verification Plan]`)** | Auto-suggest static screenshot capture (or single-clip spot check when CSS animations/transitions are modified) | High-resolution PNG screenshot (or single `1x` `.mp4`/`.gif` clip for motion tweaks) |
| **Tier 1: Stateful / Full-Stack UI & End-to-End Flows** | Auto-suggest full multi-scenario timelapse screencast reel | Per-scenario staged `.mp4` clips stitched into H.264 `.mp4`, VP9 `.webm`, and `1080px` Lanczos 2-pass `.gif` |
<!-- mdformat on -->

## 2. Prerequisite Pre-Flight Checks & Confirmation-Gated Setup

Before launching a recording or screenshot capture:

1.  **Run Pre-Flight Check (`check_recording_prerequisites`):**
    -   **Live Local Server Reachability:** Verify TCP/HTTP reachability of the
        target `http://localhost:<PORT>/<path>` or
        `https://localhost:<PORT>/<path>` endpoint. Reject `file://` and `data:`
        URLs during `/arm-review` (`allow_prototype_harness=False`).
    -   **Required Binaries & Libraries:**
        -   For `mode == "screenshot"`: Headless Chrome/Chromium or Playwright
            Chromium.
        -   For `mode == "screencast"`: Headless Chrome/Chromium or Playwright
            Chromium + `ffmpeg` (with `libx264`, `libvpx-vp9`, `palettegen`, and
            `paletteuse` filters) + optional `gifsicle` (`-O3 --lossy=80`) and
            `Pillow`.
2.  **Confirmation-Gated Auto-Install & Server Startup (`ask_question`):**
    -   If the local server is unreachable or any required binary/package is
        missing, display the exact missing prerequisites and copy-ready setup or
        startup commands in visible markdown first, then invoke `ask_question`:
        -   *Question:* `"Recording prerequisites are missing or the local
            server is not running. Proceed with setup?"`
        -   *Options:*
            1.  `"(Recommended) Install missing tools / start local server now
                and record"`
            2.  `"I will start the server / install tools manually, then retry"`
            3.  `"Skip recording and continue with interactive manual
                walkthrough"`
    -   When Option 1 is confirmed, install the missing binaries and/or start
        the local dev server in the background, recording `spawned_server_pid`
        so the session can clean it up on exit or timeout.

## 3. Core Recording Mechanics (Instructional Reels, `ADR 0020`)

v2 recordings use `scripts/instructional_reel.py` (`run_reel`, or
`cdp_screencast_recorder.py --spec` with a top-level `reel` object). The
authoritative tokens, pacing, and content limits are `DESIGN_TOKENS`,
`PACING`, and `CONTENT_LIMITS` in `scripts/instructional_reel.py`. v1 recipes (top-level `steps`) still
run through the legacy `CDPRecorder` path unchanged.

### 3.1 Reel Structure & Scenario Modes

-   Intro card → for each scenario: numbered scenario card (Direction C) →
    narrated footage → fade to black → outro checklist card.
-   **Current-only (default):** one footage segment of the current
    implementation. No BEFORE/AFTER labels, interstitial, recap, or second
    server.
-   **Compare (opt-in per scenario via `compare`):** BEFORE footage (baseline
    server) → "Now the new version" interstitial → AFTER footage → side-by-side
    recap card with the takeaway line. Propose it only when the old behavior is
    needed to understand the change.
-   Each footage variant starts in a fresh tab, and cards render in a dedicated
    card tab, so the recording tab never shares app state across scenarios.

### 3.2 TrustedTypes / CSP-Safe Overlays (Direction B, Zero `.innerHTML`)

-   In-app overlays (`#armature-rec-root`, `#armature-rec-spot`,
    `#armature-rec-coach` and its eyebrow/badge/primary/secondary/steps
    children, `#armature-rec-cursor`, `#armature-rec-chip`,
    `#armature-rec-ff-chip`) are built only with `document.createElement`,
    `document.createElementNS`, `.textContent`, and `.style.cssText`.
-   **Strict Ban:** Never use `.innerHTML`, `.outerHTML`, or
    `insertAdjacentHTML` in overlay or card scripts.
-   Spotlight ring around the live target rect (positions are always read from
    `getBoundingClientRect()` at render time), a white coach-mark bubble beside
    it (flips above/below, then to the side, never covering the ring), a
    top-center scenario chip, and a fast-forward chip during extended waits.

### 3.3 Reading-Time Pacing & Timelapse

-   Coach-mark bubbles hold for `max(3.0, 1.0 + words / 160 × 60)` s and cards
    for `max(4.0, 1.5 + words / 180 × 60)` s (kicker excluded). Explicit
    `hold_seconds` may only raise these values.
-   Clicks: distance-scaled cursor travel (0.6–1.1 s), 0.8 s dwell on the
    spotlighted target, click ripple, then the result coach after 0.5 s.
-   Extended async waits (`wait_for_js`) capture one frame per `0.5-1.0s`
    interval behind a `Fast-forward ×N` chip with elapsed seconds, with 1.0 s
    real-time holds before and after.
-   Capture at 10 fps, encode segments at 30 fps with fades (0.5 s in, 0.6 s
    out, 0.4 s per side through black), then stitch.
-   After recording, `readability_violations(frame_log)` must return no entries.

### 3.4 Before/After Baseline Sourcing (Compare Scenarios Only)

-   Start the baseline ("before") server from the change's base revision on
    `PORT+1`, alongside the current dev server on `PORT`. Host recipes are in
    Section 4.
-   Fallbacks: a feature-flag or query-param toggle on one server, then
    after-only with a still "before" screenshot.
-   Starting the baseline server is confirmation-gated like any other
    review-spawned server.

### 3.5 Browser Environment Notes

-   Every `ffmpeg` call passes `-nostdin` (and `stdin=DEVNULL`); without it a
    backgrounded run blocks forever waiting on terminal input.
-   Headless Chrome does not paint background tabs, so the card tab is brought
    to the front before each card capture.
-   Some managed Chrome builds reject a later cross-origin `Page.navigate` in a
    tab that already handled input (`net::ERR_BLOCKED_BY_ADMINISTRATOR`).
    Starting every variant in a fresh tab keeps each load a first navigation.

### 3.6 Stalled-Wait Recovery, Secret Scrubbing & Per-Scenario Staging

-   **Pre-Capture Secret & Token Masking (`mask_sensitive_dom`):**
    -   Automatically mask `input[type="password"]`, `[data-secret]`,
        `[name*="token" i]`, `[name*="secret" i]`, `[name*="key" i]`, and
        `[name*="password" i]` elements (`-webkit-text-security: disc` / blurred
        text replacement) and scrub sensitive URL query and hash parameters
        (`token`, `key`, `secret`, `password`, `auth`, `session`) via
        `history.replaceState` before capturing frames.
-   **Stalled-Wait Diagnostic Frame & Server Cleanup
    (`save_diagnostic_frame`):**
    -   If server startup or `wait_for_js` exceeds `timeout_s` or matches
        `fatal_error_selector`, immediately capture `<name>_diagnostic.png` with
        the error state visible, terminate `spawned_server_pid` if started by
        the review session, and prompt via `ask_question` to apply an in-flight
        fix and retry or continue manually.
-   **Per-Scenario Clip Staging & Cascade Re-Recording
    (`stitch_scenario_clips`):**
    -   Record each scenario into a separate staged clip (`scenario_<id>.mp4`)
        in scratch storage.
    -   If an in-flight code fix during Scenario $M$ flags an earlier Scenario
        $K < M$ as `[~] Requires Quick Re-check` (Cascade Invalidation
        Tracking), re-record **only** `scenario_<K>.mp4` and stitch all passing
        scenario clips (`ffmpeg -f concat`) at the end of Step 2.5.
-   **Deterministic Post-Processing (`ffmpeg`):**
    -   **H.264 MP4:** `ffmpeg -nostdin -y -framerate 10 -i frame_%04d.png -c:v
        libx264 -pix_fmt yuv420p -preset fast -crf 20 -movflags +faststart
        <out>.mp4`
    -   **VP9 WebM:** `ffmpeg -nostdin -y -framerate 10 -i frame_%04d.png -c:v
        libvpx-vp9 -deadline realtime -cpu-used 6 -row-mt 1 -b:v 2M -pix_fmt
        yuv420p <out>.webm`
    -   **1080px 2-Pass Lanczos GIF:**
        `scale=1080:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle`
-   **Pre-Upload Manual Inspection Gate (`ask_question`):**
    -   Always surface local preview paths first and ask for explicit user
        confirmation via `ask_question` that the recording is free of sensitive
        data before executing any remote upload.

## 4. Host Screencast & Media Publishing Stack

-   **Browser & CDP Control:** **Playwright** (`playwright` Python/Node, Apache
    2.0) via `page.context().new_cdp_session(page)` (or `CDPRecorder` raw stdlib
    CDP client in `skills/arm-review/scripts/cdp_screencast_recorder.py`) for
    frame-accurate `Page.captureScreenshot` timelapse loops, native auto-waiting
    locators, Shadow DOM traversal, and TrustedTypes-safe
    `document.createElement` HUD injection (falling back to Playwright
    `record_video_dir` only when timelapse compression is disabled).
-   **Video & Palette-GIF Encoding:** `ffmpeg` (`libx264`, `libvpx-vp9`,
    `palettegen`+`paletteuse`), `Pillow` (MIT/HPND, optional crop/annotation
    checks), and `gifsicle` (`gifsicle -O3 --lossy=80` to keep animated GIFs
    under `10 MiB`).
-   **Local Default & Git-Host-Agnostic Publishing (`publish_oss_media`):**
    1.  **Local Gitignored Default (`<track_dir>/recordings/`):** Save `.mp4`,
        `.webm`, `.gif`, and `.png` artifacts to
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/recordings/` and
        ensure `**/recordings/*.mp4`, `**/recordings/*.webm`,
        `**/recordings/*.gif`, and `**/recordings/*.png` are listed in
        `.gitignore` unless Git LFS is active.
    2.  **Optional Git-Host Remote Publishing (After Pre-Upload Confirmation):**
        Auto-detect the repository's Git remote (`git remote get-url origin`) or
        configured host CLI:
        -   **GitHub (`gh` CLI):**
            `gh release upload armature-media <files> --clobber` (creating
            pre-release tag `armature-media` on first use).
        -   **Gitea / Forgejo (`tea` CLI or REST API):**
            `tea release asset create armature-media <files>` or
            `POST /api/v1/repos/<owner>/<repo>/releases/<id>/assets` using
            `GITEA_TOKEN`.
        -   **GitLab (`glab` CLI):**
            `glab release upload armature-media <files>`.
        -   **Bitbucket (`Downloads` REST API):** `curl -X POST
            https://api.bitbucket.org/2.0/repositories/<workspace>/<repo>/downloads
            -F files=@<file>`.
        -   **Universal Git Fallback (Git LFS or `armature-media` Orphan
            Branch):** Track `recordings/*` via `git lfs track` when Git LFS is
            enabled, or push media artifacts to an isolated
            `origin/armature-media` orphan branch so `main` commit history stays
            free of binary blobs.
        -   **GitHub Actions CI:** Emit `<track_dir>/recordings/` for
            `actions/upload-artifact@v4`.
    3.  **Runbook & Review Report Embedding:** Write verified media links into
        both
        `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/manual_testing.md`
        and `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/tracks/<track_id>/review.md`
        (`## Recorded Verification Media`).

#### Baseline Server (Compare Scenarios Only)

-   `git worktree add ../<repo>-baseline origin/main`, start its dev server on
    `PORT+1`, and point `compare.before.url` at it. Remove the worktree after
    recording (`git worktree remove ../<repo>-baseline`).
