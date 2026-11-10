# Automated Live-App Screencast Recording & Host Adapter (`ADR 0019`)

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

## 3. Core Recording Mechanics (`AttachedCDPRecorder` Standard)

### 3.1 TrustedTypes / CSP-Safe DOM & SVG Overlays (Zero `.innerHTML`)

To prevent `TypeError: This document requires 'TrustedHTML' assignment` in
Angular, React, and strict-CSP applications:

-   Construct `#cdp-demo-overlay-root`, `#cdp-demo-caption-hud`,
    `.cdp-demo-pill`, `.cdp-demo-title`, `.cdp-demo-subtitle`,
    `#cdp-demo-target-box`, `#cdp-demo-cursor`, `#cdp-demo-cursor-halo`, and
    `.cdp-demo-ripple` exclusively via `document.createElement(...)`,
    `document.createElementNS('http://www.w3.org/2000/svg', 'svg' | 'path' |
    'circle')`, `.setAttribute(...)`, `.textContent = ...`, and
    `.style.cssText = ...`.
-   **Strict Ban:** Never use `.innerHTML`, `.outerHTML`, or
    `insertAdjacentHTML` anywhere in overlay injection scripts.
-   **Elements & Pointer Choreography:**
    -   **Two-Line HUD (`#cdp-demo-caption-hud`):** Fixed bottom (or `pos-top`
        when interacting near the bottom edge) card with monospace phase pill
        (`.cdp-demo-pill`), bold step headline (`.cdp-demo-title`), and
        plain-English secondary subtitle (`.cdp-demo-subtitle`).
    -   **Target Spotlight (`#cdp-demo-target-box`):** Aligned to
        `getBoundingClientRect()` with `4px` padding before and during clicks.
    -   **Cursor & Click Ripple (`#cdp-demo-cursor`, `.cdp-demo-ripple`):**
        Interpolates pointer movement along an `easeInOutCubic` curve and emits
        an expanding radial click ripple on mouse press.

### 3.2 Dual-Pacing Variable-Speed Timelapse Engine (`fps = 10`)

Emit all frames onto a fixed `10 fps` (`fps=10`) playback timeline:

-   **Interactive / Inspection Beats (`1x` Readability):**
    -   Call `explain_and_hold(badge, title, subtitle, seconds >= 2.8,
        highlight_selector=...)` before and after key UI interactions, repeating
        the settled PNG frame (`snap_frame(repeat=round(seconds * fps))`,
        `28-35` frames at `10 fps`).
-   **Extended Asynchronous Waits (`4x-10x` Timelapse Compression):**
    -   Call `wait_for_js(predicate_js, timeout_s=300.0, capture_interval_s=0.6,
        badge="TIMELAPSE", title=..., phase_expr_js=...,
        fatal_error_selector=...)`.
    -   Polls every `0.5s-1.0s` (default `0.6s`, yielding `~6x` compression at
        `10 fps`), capturing `1` live PNG frame per interval while updating
        `#cdp-demo-caption-hud` in real time with elapsed seconds and observed
        UI/network phase transitions (`IDLE -> GENERATING -> COMPLETED`).

### 3.3 Stalled-Wait Recovery, Secret Scrubbing & Per-Scenario Staging

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
    -   **H.264 MP4:** `ffmpeg -y -framerate 10 -i frame_%04d.png -c:v libx264
        -pix_fmt yuv420p -preset fast -crf 20 -movflags +faststart <out>.mp4`
    -   **VP9 WebM:** `ffmpeg -y -framerate 10 -i frame_%04d.png -c:v libvpx-vp9
        -deadline realtime -cpu-used 6 -row-mt 1 -b:v 2M -pix_fmt yuv420p
        <out>.webm`
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
