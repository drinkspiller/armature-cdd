#!/usr/bin/env python3
"""Instructional reel engine for `/arm-review` screencasts (ADR 0020).

Builds self-explaining demo reels on top of the ADR 0019 CDP recorder:

  1. Reel structure: intro card, a numbered title card on black before every
     scenario, narrated footage, and an outro card, with fades to and from black
     at every seam. Scenarios show the current implementation by default; a
     scenario may opt into a before/after comparison (`compare`).
  2. Reading-time pacing (`PACING`): every coach mark and card stays on screen
     for a duration computed from its word count. Explicit holds only raise the
     computed value.
  3. One design system (`DESIGN_TOKENS`): Direction C title cards and Direction
     B in-app layers (spotlight ring + coach-mark bubble), all text >= 7:1
     contrast.

In-app overlays are built only with `document.createElement`,
`document.createElementNS`, `.textContent`, and `.style` (TrustedTypes-safe).
The authoritative spec is
`armature/tracks/screencast-instructional-layer/design_spec.md`.
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import time
import urllib.request

import cdp_screencast_recorder as cdp

REFERENCE_WIDTH = 1920
REFERENCE_HEIGHT = 1080

DESIGN_TOKENS: dict[str, dict[str, object]] = {
    "color": {
        "card.bg": "#000000",
        "card.text": "#FFFFFF",
        "card.text-secondary": "#C8CCD4",
        "accent": "#8AB4F8",
        "coach.bg": "#FFFFFF",
        "coach.text": "#111318",
        "coach.text-secondary": "#3C4043",
        "coach.step-on": "#1A73E8",
        "coach.step-off": "#DADCE0",
        "state.before": "#FDD663",
        "state.after": "#81C995",
        "on-state": "#1B1300",
        "on-state.swatch": "#141414",
        "on-check": "#0D2614",
        "chip.bg": "rgba(0,0,0,0.70)",
        "chip.text": "#FFFFFF",
        "spot.ring": "#FFFFFF",
        "spot.glow": "rgba(138,180,248,0.55)",
        "spot.scrim": "rgba(0,0,0,0.57)",
        "cursor.fill": "#FFFFFF",
        "cursor.stroke": "#111111",
    },
    "font": {
        "family": (
            '"Google Sans Text", "Google Sans", system-ui, -apple-system,'
            ' "Segoe UI", Roboto, sans-serif'
        ),
        "mono": '"Google Sans Mono", ui-monospace, "SF Mono", Menlo, monospace',
    },
    # name: [size_px, line_height, weight, tracking_em]
    "type": {
        "card.number": [300, 1.0, 700, -0.04],
        "card.kicker": [20, 1.3, 700, 0.16],
        "card.headline": [70, 1.08, 700, -0.015],
        "card.body": [30, 1.45, 400, 0.0],
        "card.watch": [26, 1.4, 400, 0.0],
        "outro.item": [30, 1.3, 400, 0.0],
        "recap.header": [20, 1.3, 500, 0.14],
        "recap.label": [26, 1.3, 500, 0.0],
        "recap.takeaway": [34, 1.3, 500, 0.0],
        "coach.eyebrow": [16, 1.3, 700, 0.10],
        "coach.badge": [16, 1.0, 700, 0.06],
        "coach.primary": [30, 1.3, 500, 0.0],
        "coach.secondary": [22, 1.45, 400, 0.0],
        "chip": [18, 1.0, 500, 0.0],
    },
    "radius": {
        "coach": 18,
        "spot": 14,
        "recap.thumb": 14,
        "recap.swatch": 8,
        "pill": 999,
        "step": 3,
    },
    "shadow": {
        "coach": "0 16px 48px rgba(0,0,0,0.45)",
        "cursor": "drop-shadow(0 2px 4px rgba(0,0,0,0.40))",
    },
    "motion": {
        "ease.ui": "cubic-bezier(0.2, 0, 0, 1)",
        "fast_ms": 160,
        "base_ms": 240,
        "slow_ms": 400,
        "ripple_ms": 450,
    },
    "layout": {
        "card.pad_x": 160,
        "card.number_col": 520,
        "card.col_gap": 72,
        "coach.width": 640,
        "coach.pad": [26, 28, 22, 28],
        "coach.gap": 36,
        "coach.margin": 40,
        "coach.below_threshold": 500,
        "spot.pad": 8,
        "spot.stroke": 4,
        "spot.glow_blur": 32,
        "spot.glow_spread": 8,
        "chip.top": 32,
        "chip.height": 38,
        "chip.pad_x": 16,
        "chip.gap": 10,
        "chip.dot": 10,
        "cursor.size": 34,
        "cursor.hotspot": 0.55,
        "recap.pad": [72, 96, 64, 96],
        "recap.gap": 36,
        "recap.col_gap": 40,
    },
}

# (foreground token, background token, minimum ratio, label). A background of
# "chip.bg@white" means `chip.bg` composited over white (worst case).
CONTRAST_PAIRS: list[tuple[str, str, float, str]] = [
    ("coach.text", "coach.bg", 7.0, "coach primary"),
    ("coach.text-secondary", "coach.bg", 7.0, "coach secondary"),
    ("on-state", "state.before", 7.0, "BEFORE badge"),
    ("on-state", "state.after", 7.0, "AFTER badge"),
    ("card.text", "card.bg", 7.0, "card headline"),
    ("card.text-secondary", "card.bg", 7.0, "card body"),
    ("accent", "card.bg", 7.0, "card number and kicker"),
    ("chip.text", "chip.bg@white", 7.0, "chip over light app"),
    ("on-check", "state.after", 7.0, "outro check"),
    ("on-state.swatch", "state.before", 7.0, "recap BEFORE swatch"),
    ("on-state.swatch", "state.after", 7.0, "recap AFTER swatch"),
    ("coach.step-on", "coach.bg", 3.0, "active step dot (non-text)"),
]

PACING: dict[str, float] = {
    "coach.min": 3.0,
    "coach.settle": 1.0,
    "coach.wpm": 160.0,
    "card.min": 4.0,
    "card.settle": 1.5,
    "card.wpm": 180.0,
    "recap.min": 5.0,
    "recap.settle": 2.5,
    "recap.wpm": 140.0,
    "interstitial.hold": 2.0,
    "cursor.min_s": 0.6,
    "cursor.max_s": 1.1,
    "cursor.near_px": 200.0,
    "cursor.far_px": 1200.0,
    "click.dwell": 0.8,
    "click.observe_min": 1.5,
    "click.result_delay": 0.5,
    "type.cps": 12.0,
    "scene.settle": 1.0,
    "ff.margin": 1.0,
    "ff.sample_default": 0.6,
    "fade.in": 0.5,
    "fade.out": 0.6,
    "fade.through": 0.4,
    "fps.capture": 10.0,
    "fps.output": 30.0,
}

CONTENT_LIMITS: dict[str, int] = {
    "card.headline": 48,
    "card.body": 100,
    "card.watch": 80,
    "coach.primary": 90,
    "coach.secondary": 120,
    "recap.takeaway": 110,
    "outro.item": 60,
}

STEP_ACTIONS = (
    "narrate",
    "click",
    "type",
    "wait_for_js",
    "navigate",
    "mask_secrets",
    "eval",
    "screenshot",
)


# --------------------------------------------------------------------------
# Pacing
# --------------------------------------------------------------------------


def word_count(*texts: str | None) -> int:
  """Counts whitespace-separated words across `texts`, ignoring `None`."""
  return sum(len((t or "").split()) for t in texts)


def coach_hold_seconds(primary: str, secondary: str | None = None) -> float:
  """Returns the reading hold for a coach mark (design spec Section 5)."""
  words = word_count(primary, secondary)
  return max(
      PACING["coach.min"],
      PACING["coach.settle"] + words / PACING["coach.wpm"] * 60.0,
  )


def card_hold_seconds(
    headline: str,
    body: str | None = None,
    watch: str | None = None,
    items: list[str] | tuple[str, ...] = (),
) -> float:
  """Returns the reading hold for a title card; the kicker is not counted."""
  words = word_count(headline, body, watch, *items)
  return max(
      PACING["card.min"],
      PACING["card.settle"] + words / PACING["card.wpm"] * 60.0,
  )


def recap_hold_seconds(takeaway: str) -> float:
  """Returns the reading hold for a compare recap card."""
  words = word_count(takeaway)
  return max(
      PACING["recap.min"],
      PACING["recap.settle"] + words / PACING["recap.wpm"] * 60.0,
  )


def resolve_hold(computed: float, override: float | None) -> float:
  """Applies an explicit hold, which may only raise the computed value."""
  if override is None:
    return computed
  return max(computed, float(override))


def cursor_travel_seconds(distance_ref_px: float) -> float:
  """Maps cursor travel distance (reference px) to 0.6-1.1 s, linear."""
  near, far = PACING["cursor.near_px"], PACING["cursor.far_px"]
  frac = min(1.0, max(0.0, (distance_ref_px - near) / (far - near)))
  return PACING["cursor.min_s"] + frac * (
      PACING["cursor.max_s"] - PACING["cursor.min_s"]
  )


# --------------------------------------------------------------------------
# Contrast
# --------------------------------------------------------------------------


def _parse_color(value: str) -> tuple[float, float, float, float]:
  """Parses `#RRGGBB` or `rgba(r,g,b,a)` into 0-255 channels plus alpha."""
  v = value.strip()
  if v.startswith("#"):
    h = v[1:]
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
  if v.startswith("rgba(") and v.endswith(")"):
    parts = [p.strip() for p in v[5:-1].split(",")]
    return (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
  raise ValueError(f"Unsupported color: {value!r}")


def _composite(fg: str, bg_hex: str) -> str:
  """Composites a possibly translucent `fg` over an opaque `bg_hex`."""
  r, g, b, a = _parse_color(fg)
  br, bgc, bb, _ = _parse_color(bg_hex)
  mix = [round(c * a + d * (1 - a)) for c, d in ((r, br), (g, bgc), (b, bb))]
  return "#{:02X}{:02X}{:02X}".format(*mix)


def _relative_luminance(hex_color: str) -> float:
  """Computes WCAG relative luminance for an opaque color."""
  r, g, b, _ = _parse_color(hex_color)

  def channel(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(fg: str, bg: str) -> float:
  """Returns the WCAG contrast ratio between two opaque colors."""
  la, lb = sorted(
      (_relative_luminance(fg), _relative_luminance(bg)), reverse=True
  )
  return (la + 0.05) / (lb + 0.05)


def token_contrast_report() -> list[dict[str, object]]:
  """Computes the contrast ratio of every pair in `CONTRAST_PAIRS`."""
  colors = DESIGN_TOKENS["color"]
  report = []
  for fg_key, bg_key, minimum, label in CONTRAST_PAIRS:
    if bg_key.endswith("@white"):
      bg = _composite(str(colors[bg_key[: -len("@white")]]), "#FFFFFF")
    else:
      bg = str(colors[bg_key])
    ratio = contrast_ratio(str(colors[fg_key]), bg)
    report.append({
        "label": label,
        "fg": fg_key,
        "bg": bg_key,
        "ratio": round(ratio, 1),
        "minimum": minimum,
        "passes": ratio >= minimum,
    })
  return report


# --------------------------------------------------------------------------
# Recipe validation
# --------------------------------------------------------------------------


def _check_len(
    warnings: list[str], where: str, limit_key: str, text: str | None
) -> None:
  """Adds a warning when `text` exceeds its content limit."""
  if text and len(text) > CONTENT_LIMITS[limit_key]:
    warnings.append(
        f"{where}: {len(text)} chars exceeds {limit_key} limit"
        f" {CONTENT_LIMITS[limit_key]}"
    )


def _validate_steps(
    steps: object, where: str, errors: list[str], warnings: list[str]
) -> None:
  """Validates a step list and its narration lengths."""
  if not isinstance(steps, list) or not steps:
    errors.append(f"{where}.steps must be a non-empty list")
    return
  for i, step in enumerate(steps):
    loc = f"{where}.steps[{i}]"
    if not isinstance(step, dict) or step.get("action") not in STEP_ACTIONS:
      errors.append(f"{loc}: unknown or missing action")
      continue
    action = step["action"]
    if action in ("click", "type"):
      if not step.get("selector"):
        errors.append(f"{loc}: {action} requires selector")
    if action == "narrate" and not step.get("text"):
      errors.append(f"{loc}: narrate requires text")
    if action == "type" and "value" not in step:
      errors.append(f"{loc}: type requires value")
    if action == "wait_for_js" and not step.get("predicate_js"):
      errors.append(f"{loc}: wait_for_js requires predicate_js")
    if action == "navigate" and not step.get("url"):
      errors.append(f"{loc}: navigate requires url")
    if action == "eval" and not step.get("expression"):
      errors.append(f"{loc}: eval requires expression")
    if action == "screenshot" and not step.get("path"):
      errors.append(f"{loc}: screenshot requires path")
    if action in ("click", "type") and step.get("narrate") is not None:
      nar = step["narrate"]
      if not isinstance(nar, dict) or not nar.get("text"):
        errors.append(f"{loc}: narrate must be an object with text")
    narration = step.get("narrate") if action != "narrate" else step
    if isinstance(narration, dict):
      _check_len(warnings, loc, "coach.primary", narration.get("text"))
      _check_len(warnings, loc, "coach.secondary", narration.get("secondary"))


def validate_reel_spec(spec: dict[str, object]) -> tuple[list[str], list[str]]:
  """Validates a v2 `reel` recipe and returns `(errors, warnings)`."""
  errors: list[str] = []
  warnings: list[str] = []
  reel = spec.get("reel")
  if not isinstance(reel, dict):
    return (["missing top-level 'reel' object"], [])
  for key in ("title", "summary"):
    if not reel.get(key):
      errors.append(f"reel.{key} is required")
  _check_len(warnings, "reel.title", "card.headline", reel.get("title"))
  _check_len(warnings, "reel.summary", "card.body", reel.get("summary"))
  scenarios = reel.get("scenarios")
  if not isinstance(scenarios, list) or not scenarios:
    errors.append("reel.scenarios must be a non-empty list")
    scenarios = []
  seen_ids: set[str] = set()
  for k, sc in enumerate(scenarios):
    where = f"reel.scenarios[{k}]"
    if not isinstance(sc, dict):
      errors.append(f"{where} must be an object")
      continue
    for key in ("id", "title", "goal", "watch_for"):
      if not sc.get(key):
        errors.append(f"{where}.{key} is required")
    if sc.get("id") in seen_ids:
      errors.append(f"{where}.id {sc.get('id')!r} is duplicated")
    seen_ids.add(str(sc.get("id")))
    _check_len(warnings, f"{where}.title", "card.headline", sc.get("title"))
    _check_len(warnings, f"{where}.goal", "card.body", sc.get("goal"))
    _check_len(
        warnings, f"{where}.watch_for", "card.watch", sc.get("watch_for")
    )
    compare = sc.get("compare")
    if compare is not None:
      if not isinstance(compare, dict):
        errors.append(f"{where}.compare must be an object")
        continue
      for side in ("before", "after"):
        variant = compare.get(side)
        if not isinstance(variant, dict) or not variant.get("url"):
          errors.append(f"{where}.compare.{side}.url is required")
          continue
        _validate_steps(
            variant.get("steps"), f"{where}.compare.{side}", errors, warnings
        )
      if not compare.get("takeaway"):
        errors.append(f"{where}.compare.takeaway is required")
      _check_len(
          warnings,
          f"{where}.compare.takeaway",
          "recap.takeaway",
          compare.get("takeaway"),
      )
    else:
      if not sc.get("url"):
        errors.append(f"{where}.url is required unless compare is set")
      _validate_steps(sc.get("steps"), where, errors, warnings)
  outro = reel.get("outro")
  items = outro.get("items") if isinstance(outro, dict) else None
  if not isinstance(items, list) or not items:
    errors.append("reel.outro.items must be a non-empty list")
  else:
    if len(items) > 6:
      warnings.append("reel.outro.items: more than 6 items")
    for i, item in enumerate(items):
      _check_len(warnings, f"reel.outro.items[{i}]", "outro.item", item)
  return (errors, warnings)


def coach_step_total(steps: list[dict[str, object]]) -> int:
  """Counts steps that show a coach mark (`narrate`, or narrated click/type)."""
  total = 0
  for step in steps:
    action = step.get("action")
    if action == "narrate" or (
        action in ("click", "type") and isinstance(step.get("narrate"), dict)
    ):
      total += 1
  return total


# --------------------------------------------------------------------------
# Browser-side overlay (Direction B) and cards (Direction C)
# --------------------------------------------------------------------------

_OVERLAY_JS_TEMPLATE = r"""
(() => {
  const T = __TOKENS__;
  if (window.__armRec && document.getElementById('armature-rec-root')) {
    return true;
  }
  const s = () => window.innerHeight / 1080;
  const px = (v) => (v * s()).toFixed(2) + 'px';
  const C = T.color, Y = T.type, L = T.layout, R = T.radius, M = T.motion;
  const font = (k) => {
    const t = Y[k];
    return 'font:' + t[2] + ' ' + px(t[0]) + '/' + t[1] + ' ' +
        T.font.family + ';letter-spacing:' + t[3] + 'em;';
  };

  const root = document.createElement('div');
  root.id = 'armature-rec-root';
  root.style.cssText = 'position:fixed;inset:0;pointer-events:none;' +
      'z-index:2147483646;';
  const style = document.createElement('style');
  style.textContent = `
    @keyframes armRecCoachIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: none; }
    }
    @keyframes armRecRipple {
      from { opacity: 0.6; transform: translate(-50%, -50%) scale(0.4); }
      to { opacity: 0; transform: translate(-50%, -50%) scale(1.6); }
    }
    .cdp-demo-masked-secret,
    input[type="password"],
    [data-secret],
    [name*="token" i],
    [name*="secret" i],
    [name*="key" i],
    [name*="password" i] {
      -webkit-text-security: disc !important;
      filter: blur(5px) !important;
    }
  `;
  root.appendChild(style);

  const spot = document.createElement('div');
  spot.id = 'armature-rec-spot';
  spot.style.cssText = 'position:fixed;display:none;border-radius:' +
      px(R.spot) + ';box-shadow:0 0 0 9999px ' + C['spot.scrim'] +
      ',0 0 0 ' + px(L['spot.stroke']) + ' ' + C['spot.ring'] + ',0 0 ' +
      px(L['spot.glow_blur']) + ' ' + px(L['spot.glow_spread']) + ' ' +
      C['spot.glow'] + ';transition:left ' + M.slow_ms + 'ms ' +
      M['ease.ui'] + ',top ' + M.slow_ms + 'ms ' + M['ease.ui'] +
      ',width ' + M.slow_ms + 'ms ' + M['ease.ui'] + ',height ' +
      M.slow_ms + 'ms ' + M['ease.ui'] + ';';
  root.appendChild(spot);

  const chips = document.createElement('div');
  chips.style.cssText = 'position:fixed;left:50%;transform:translateX(-50%);' +
      'top:' + px(L['chip.top']) + ';display:flex;gap:' + px(L['chip.gap']) +
      ';';
  const mkChip = (id) => {
    const c = document.createElement('div');
    c.id = id;
    c.style.cssText = 'display:none;align-items:center;gap:' +
        px(L['chip.gap'] - 2) + ';height:' + px(L['chip.height']) +
        ';padding:0 ' + px(L['chip.pad_x']) + ';border-radius:999px;' +
        'background:' + C['chip.bg'] + ';color:' + C['chip.text'] + ';' +
        font('chip') + 'white-space:nowrap;';
    chips.appendChild(c);
    return c;
  };
  const chip = mkChip('armature-rec-chip');
  const ffChip = mkChip('armature-rec-ff-chip');
  root.appendChild(chips);

  const coach = document.createElement('div');
  coach.id = 'armature-rec-coach';
  const pad = L['coach.pad'];
  coach.style.cssText = 'position:fixed;display:none;box-sizing:border-box;' +
      'width:' + px(L['coach.width']) + ';padding:' + px(pad[0]) + ' ' +
      px(pad[1]) + ' ' + px(pad[2]) + ' ' + px(pad[3]) + ';background:' +
      C['coach.bg'] + ';color:' + C['coach.text'] + ';border-radius:' +
      px(R.coach) + ';box-shadow:' + T.shadow.coach + ';';
  root.appendChild(coach);

  const NS = 'http://www.w3.org/2000/svg';
  const cursor = document.createElementNS(NS, 'svg');
  cursor.id = 'armature-rec-cursor';
  cursor.setAttribute('viewBox', '0 0 24 24');
  cursor.style.cssText = 'position:fixed;left:0;top:0;width:' +
      px(L['cursor.size']) + ';height:' + px(L['cursor.size']) +
      ';filter:' + T.shadow.cursor + ';transform:translate(-3px,-2px);';
  const path = document.createElementNS(NS, 'path');
  path.setAttribute('d', 'M4 2l15 11-6.5 1.2L16 21l-3 1.4-3.6-6.8L4 20z');
  path.setAttribute('fill', C['cursor.fill']);
  path.setAttribute('stroke', C['cursor.stroke']);
  path.setAttribute('stroke-width', '1.4');
  path.setAttribute('stroke-linejoin', 'round');
  cursor.appendChild(path);
  root.appendChild(cursor);

  (document.body || document.documentElement).appendChild(root);

  const rectOf = (sel) => {
    if (!sel) return null;
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return null;
    return {left: r.left, top: r.top, right: r.right, bottom: r.bottom,
            width: r.width, height: r.height};
  };

  const api = {
    rect: rectOf,
    cursor(x, y, pressed) {
      cursor.style.left = x + 'px';
      cursor.style.top = y + 'px';
      cursor.style.transform = pressed ?
          'translate(-3px,-2px) scale(0.9)' : 'translate(-3px,-2px)';
      return true;
    },
    ripple(x, y) {
      const r = document.createElement('div');
      const d = 44 * s();
      r.style.cssText = 'position:fixed;left:' + x + 'px;top:' + y +
          'px;width:' + d + 'px;height:' + d + 'px;border-radius:50%;' +
          'border:' + px(3) + ' solid ' + C.accent + ';animation:armRecRipple ' +
          M.ripple_ms + 'ms ' + M['ease.ui'] + ' forwards;';
      root.appendChild(r);
      setTimeout(() => r.remove(), M.ripple_ms + 50);
      return true;
    },
    spot(sel) {
      const r = rectOf(sel);
      if (!r) { spot.style.display = 'none'; return null; }
      const p = L['spot.pad'] * s();
      spot.style.display = 'block';
      spot.style.left = (r.left - p) + 'px';
      spot.style.top = (r.top - p) + 'px';
      spot.style.width = (r.width + 2 * p) + 'px';
      spot.style.height = (r.height + 2 * p) + 'px';
      return r;
    },
    chip(text, state) {
      chip.replaceChildren();
      if (!text) { chip.style.display = 'none'; return true; }
      if (state) {
        const dot = document.createElement('span');
        const d = px(L['chip.dot']);
        dot.style.cssText = 'width:' + d + ';height:' + d +
            ';border-radius:50%;background:' + C['state.' + state] + ';';
        chip.appendChild(dot);
      }
      const label = document.createElement('span');
      label.textContent = text;
      chip.appendChild(label);
      chip.style.display = 'inline-flex';
      return true;
    },
    ff(text, elapsed) {
      ffChip.replaceChildren();
      if (!text) { ffChip.style.display = 'none'; return true; }
      const label = document.createElement('span');
      label.textContent = text;
      const clock = document.createElement('span');
      clock.textContent = elapsed || '';
      clock.style.cssText = 'font-family:' + T.font.mono + ';opacity:0.85;';
      ffChip.appendChild(label);
      ffChip.appendChild(clock);
      ffChip.style.display = 'inline-flex';
      return true;
    },
    coach(o) {
      coach.replaceChildren();
      const eyebrow = document.createElement('div');
      eyebrow.id = 'armature-rec-coach-eyebrow';
      eyebrow.style.cssText = 'display:flex;align-items:center;gap:' +
          px(10) + ';margin-bottom:' + px(10) + ';color:' +
          C['coach.text-secondary'] + ';text-transform:uppercase;' +
          font('coach.eyebrow');
      if (o.state) {
        const badge = document.createElement('span');
        badge.id = 'armature-rec-coach-badge';
        badge.textContent = o.state === 'before' ? 'BEFORE' : 'AFTER';
        badge.style.cssText = 'display:inline-flex;align-items:center;' +
            'height:' + px(26) + ';padding:0 ' + px(10) + ';border-radius:' +
            '999px;background:' + C['state.' + o.state] + ';color:' +
            C['on-state'] + ';' + font('coach.badge');
        eyebrow.appendChild(badge);
      }
      const stepText = document.createElement('span');
      stepText.textContent = 'Step ' + o.step + ' of ' + o.steps;
      eyebrow.appendChild(stepText);
      coach.appendChild(eyebrow);
      const primary = document.createElement('div');
      primary.id = 'armature-rec-coach-primary';
      primary.textContent = o.primary;
      primary.style.cssText = font('coach.primary') + 'color:' +
          C['coach.text'] + ';';
      coach.appendChild(primary);
      if (o.secondary) {
        const sec = document.createElement('div');
        sec.id = 'armature-rec-coach-secondary';
        sec.textContent = o.secondary;
        sec.style.cssText = font('coach.secondary') + 'color:' +
            C['coach.text-secondary'] + ';margin-top:' + px(8) + ';';
        coach.appendChild(sec);
      }
      const dots = document.createElement('div');
      dots.id = 'armature-rec-coach-steps';
      dots.style.cssText = 'display:flex;gap:' + px(6) + ';margin-top:' +
          px(18) + ';';
      for (let i = 1; i <= o.steps; i++) {
        const d = document.createElement('i');
        d.style.cssText = 'display:block;width:' + px(26) + ';height:' +
            px(5) + ';border-radius:' + px(R.step) + ';background:' +
            (i <= o.step ? C['coach.step-on'] : C['coach.step-off']) + ';';
        dots.appendChild(d);
      }
      coach.appendChild(dots);
      coach.style.display = 'block';
      coach.style.animation = 'none';
      void coach.offsetHeight;
      coach.style.animation = 'armRecCoachIn ' + M.base_ms + 'ms ' +
          M['ease.ui'] + ' both';
      return api.place(o.selector);
    },
    place(sel) {
      const W = window.innerWidth, H = window.innerHeight, k = s();
      const cw = L['coach.width'] * k, gap = L['coach.gap'] * k;
      const m = L['coach.margin'] * k, ch = coach.offsetHeight;
      const r = rectOf(sel);
      let left, top, side = 'center';
      if (!r) {
        left = (W - cw) / 2;
        top = H - ch - m;
      } else {
        // Keep clear of the painted ring box (target + pad + stroke).
        const ring = (L['spot.pad'] + L['spot.stroke']) * k;
        const box = {left: r.left - ring, top: r.top - ring,
                     right: r.right + ring, bottom: r.bottom + ring};
        const hLeft = Math.min(W - cw - m, Math.max(m, r.right - cw));
        const vTop = Math.min(H - ch - m,
                              Math.max(m, (box.top + box.bottom - ch) / 2));
        const fits = (y) => y >= m && y + ch <= H - m;
        const belowY = box.bottom + gap, aboveY = box.top - ch - gap;
        const rightX = box.right + gap, leftX = box.left - cw - gap;
        const order = r.top < L['coach.below_threshold'] * k ?
            ['below', 'above'] : ['above', 'below'];
        const cands = {
          below: fits(belowY) ? [hLeft, belowY] : null,
          above: fits(aboveY) ? [hLeft, aboveY] : null,
          right: rightX + cw <= W - m ? [rightX, vTop] : null,
          left: leftX >= m ? [leftX, vTop] : null,
        };
        const roomR = W - box.right, roomL = box.left;
        order.push(roomR >= roomL ? 'right' : 'left',
                   roomR >= roomL ? 'left' : 'right');
        side = order.find((name) => cands[name]);
        if (side) {
          [left, top] = cands[side];
        } else {
          // Nothing fits outside the ring (target nearly fills the frame):
          // pin to the edge with the most vertical room.
          side = 'overlap';
          left = hLeft;
          top = (box.top - m) > (H - m - box.bottom) ? m : H - ch - m;
        }
      }
      coach.style.left = left + 'px';
      coach.style.top = top + 'px';
      return {left, top, width: cw, height: ch, side};
    },
    clearCoach() {
      coach.style.display = 'none';
      spot.style.display = 'none';
      return true;
    },
    setVisible(v) {
      root.style.display = v ? '' : 'none';
      return true;
    },
  };
  window.__armRec = api;
  return true;
})()
"""

_CARD_JS_TEMPLATE = r"""
(() => {
  const T = __TOKENS__;
  window.__armRecCard = (spec) => {
    const s = window.innerHeight / 1080;
    const px = (v) => (v * s).toFixed(2) + 'px';
    const C = T.color, Y = T.type, L = T.layout, R = T.radius;
    const font = (k) => {
      const t = Y[k];
      return 'font:' + t[2] + ' ' + px(t[0]) + '/' + t[1] + ' ' +
          T.font.family + ';letter-spacing:' + t[3] + 'em;';
    };
    const el = (tag, css, text) => {
      const e = document.createElement(tag);
      if (css) e.style.cssText = css;
      if (text != null) e.textContent = text;
      return e;
    };
    document.documentElement.style.cssText = 'background:' + C['card.bg'] + ';';
    document.body.replaceChildren();
    document.body.style.cssText = 'margin:0;background:' + C['card.bg'] +
        ';color:' + C['card.text'] + ';overflow:hidden;';
    const root = el('div', 'position:fixed;inset:0;background:' +
        C['card.bg'] + ';');
    root.id = 'armature-rec-card';
    document.body.appendChild(root);

    const textColumn = () => {
      const col = el('div', '');
      if (spec.kicker) {
        col.appendChild(el('div', font('card.kicker') +
            'text-transform:uppercase;color:' + C.accent + ';', spec.kicker));
      }
      if (spec.headline) {
        col.appendChild(el('h1', font('card.headline') + 'margin:' + px(16) +
            ' 0 ' + px(22) + ';color:' + C['card.text'] + ';',
            spec.headline));
      }
      if (spec.body) {
        col.appendChild(el('p', font('card.body') + 'margin:0;color:' +
            C['card.text-secondary'] + ';', spec.body));
      }
      if (spec.watch) {
        const w = el('div', font('card.watch') + 'margin-top:' + px(26) +
            ';padding-left:' + px(18) + ';border-left:' + px(4) + ' solid ' +
            C.accent + ';color:' + C['card.text'] + ';');
        const b = el('b', 'font-weight:700;', 'Watch for: ');
        w.appendChild(b);
        w.appendChild(document.createTextNode(spec.watch));
        col.appendChild(w);
      }
      if (spec.items) {
        const ul = el('ul', 'list-style:none;padding:0;margin:' + px(28) +
            ' 0 0;display:grid;gap:' + px(16) + ';');
        for (const item of spec.items) {
          const li = el('li', 'display:flex;align-items:center;gap:' +
              px(16) + ';' + font('outro.item') + 'color:' + C['card.text'] +
              ';');
          const d = px(40);
          li.appendChild(el('span', 'flex:none;width:' + d + ';height:' + d +
              ';border-radius:50%;background:' + C['state.after'] + ';color:' +
              C['on-check'] + ';display:grid;place-items:center;font:700 ' +
              px(22) + ' ' + T.font.family + ';', '\u2713'));
          li.appendChild(document.createTextNode(item));
          ul.appendChild(li);
        }
        col.appendChild(ul);
      }
      return col;
    };

    if (spec.type === 'recap') {
      const p = L['recap.pad'];
      const wrap = el('div', 'position:absolute;inset:0;display:grid;' +
          'align-content:center;gap:' + px(L['recap.gap']) + ';padding:' +
          px(p[0]) + ' ' + px(p[1]) + ' ' + px(p[2]) + ' ' + px(p[3]) + ';');
      wrap.appendChild(el('div', font('recap.header') +
          'text-transform:uppercase;color:' + C['card.text-secondary'] + ';',
          spec.header));
      const pair = el('div', 'display:grid;grid-template-columns:1fr 1fr;' +
          'gap:' + px(L['recap.col_gap']) + ';');
      for (const side of ['before', 'after']) {
        const fig = el('figure', 'margin:0;display:grid;gap:' + px(16) + ';');
        const img = el('img', 'width:100%;aspect-ratio:16/9;object-fit:cover;' +
            'object-position:top left;border-radius:' + px(R['recap.thumb']) +
            ';background:#222;display:block;');
        img.alt = side;
        img.src = spec[side + '_image'];
        fig.appendChild(img);
        const cap = el('figcaption', 'display:flex;align-items:center;gap:' +
            px(12) + ';' + font('recap.label') + 'color:' + C['card.text'] +
            ';');
        cap.appendChild(el('span', 'display:inline-flex;align-items:center;' +
            'height:' + px(32) + ';padding:0 ' + px(12) + ';border-radius:' +
            px(R['recap.swatch']) + ';background:' + C['state.' + side] +
            ';color:' + C['on-state.swatch'] + ';font:700 ' + px(18) + ' ' +
            T.font.family + ';letter-spacing:0.08em;',
            side === 'before' ? 'BEFORE' : 'AFTER'));
        cap.appendChild(document.createTextNode(spec[side + '_label'] || ''));
        fig.appendChild(cap);
        pair.appendChild(fig);
      }
      wrap.appendChild(pair);
      wrap.appendChild(el('div', font('recap.takeaway') + 'max-width:' +
          px(1500) + ';color:' + C['card.text'] + ';', spec.takeaway));
      root.appendChild(wrap);
    } else if (spec.type === 'numbered') {
      const grid = el('div', 'position:absolute;inset:0;display:grid;' +
          'grid-template-columns:' + px(L['card.number_col']) + ' 1fr;' +
          'align-items:center;column-gap:' + px(L['card.col_gap']) +
          ';padding:0 ' + px(L['card.pad_x']) + ';');
      grid.appendChild(el('div', font('card.number') + 'color:' + C.accent +
          ';text-align:right;', spec.number));
      grid.appendChild(textColumn());
      root.appendChild(grid);
    } else {
      const solo = el('div', 'position:absolute;inset:0;display:grid;' +
          'align-content:center;padding:0 ' + px(L['card.pad_x']) + ';');
      solo.appendChild(textColumn());
      root.appendChild(solo);
    }
    const waits = [document.fonts ? document.fonts.ready : null];
    for (const img of root.querySelectorAll('img')) {
      waits.push(img.decode ? img.decode().catch(() => null) : null);
    }
    return Promise.all(waits).then(() => true);
  };
  return true;
})()
"""


def build_overlay_js(tokens: dict[str, dict[str, object]] | None = None) -> str:
  """Returns the in-app overlay bootstrap JS with `tokens` inlined."""
  return _OVERLAY_JS_TEMPLATE.replace(
      "__TOKENS__", json.dumps(tokens or DESIGN_TOKENS)
  )


def build_card_js(tokens: dict[str, dict[str, object]] | None = None) -> str:
  """Returns the card renderer bootstrap JS with `tokens` inlined."""
  return _CARD_JS_TEMPLATE.replace(
      "__TOKENS__", json.dumps(tokens or DESIGN_TOKENS)
  )


REEL_OVERLAY_JS = build_overlay_js()
REEL_CARD_JS = build_card_js()


# --------------------------------------------------------------------------
# Recorder
# --------------------------------------------------------------------------


class ReelRecorder(cdp.CDPRecorder):
  """CDP recorder with Direction B overlays, cards, segments, and fades."""

  def __init__(self, *args, **kwargs):
    """Initializes the recorder and its segment staging directory.

    Args:
      *args: Positional arguments forwarded to `CDPRecorder`.
      **kwargs: Keyword arguments forwarded to `CDPRecorder`.
    """
    super().__init__(*args, **kwargs)
    self.segment_root = os.path.join(
        os.path.dirname(self.frame_dir), f"{self.name}_segments"
    )
    if os.path.exists(self.segment_root):
      shutil.rmtree(self.segment_root)
    os.makedirs(self.segment_root, exist_ok=True)
    self.segments: list[str] = []
    self.frame_log: list[dict[str, object]] = []
    self._segment_label = ""
    self._segment_count = 0
    self._chip_text = ""
    self._chip_state: str | None = None
    self.scenario_id: str | None = None

  # ---- overlay plumbing -------------------------------------------------

  @property
  def scale(self) -> float:
    """Returns the reference-to-viewport scale factor (height / 1080)."""
    return self.height / REFERENCE_HEIGHT

  def ensure_overlay(self) -> None:
    """Mounts the Direction B overlay and restores cursor and chip state."""
    self.eval_js(REEL_OVERLAY_JS)
    self.eval_js(
        f"window.__armRec.cursor({self.cur_x:.1f}, {self.cur_y:.1f}, false)"
    )
    if self._chip_text:
      self.eval_js(
          f"window.__armRec.chip({json.dumps(self._chip_text)},"
          f" {json.dumps(self._chip_state)})"
      )

  def highlight(self, selector: str | None = None) -> None:
    """Shows the spotlight ring around `selector`, or clears it."""
    self.ensure_overlay()
    self.eval_js(f"window.__armRec.spot({json.dumps(selector or '')})")

  def save_clean_screenshot(self, out_path: str) -> str:
    """Captures a PNG with the reel overlay hidden."""
    with open(out_path, "wb") as f:
      f.write(self.clean_png())
    return out_path

  def clean_png(self) -> bytes:
    """Returns PNG bytes of the page with the overlay temporarily hidden."""
    self.eval_js("window.__armRec && window.__armRec.setVisible(false)")
    shot = self.call("Page.captureScreenshot", {"format": "png"})
    self.eval_js("window.__armRec && window.__armRec.setVisible(true)")
    return base64.b64decode(str(shot["data"]))

  def set_chip(self, text: str, state: str | None = None) -> None:
    """Sets the persistent scenario chip (state dot only in compare mode)."""
    self._chip_text, self._chip_state = text, state
    # Never draw into a tab the recorder did not create (for example the
    # user's own tab when attached with `attach_port`).
    if getattr(self, "_page_target_id", None) is not None:
      self.ensure_overlay()

  # ---- segments ---------------------------------------------------------

  def begin_segment(self, label: str) -> None:
    """Starts a new segment with its own frame directory."""
    self._segment_count += 1
    self._segment_label = label
    self.frame_dir = os.path.join(
        self.segment_root, f"{self._segment_count:02d}_{label}_frames"
    )
    os.makedirs(self.frame_dir, exist_ok=True)
    self.frame_idx = 0

  def end_segment(self, fade_in: float, fade_out: float) -> str | None:
    """Encodes the current segment at the output frame rate with fades."""
    if self.frame_idx == 0:
      return None
    duration = self.frame_idx / self.fps
    fade_out_start = max(0.0, duration - fade_out)
    out_fps = int(PACING["fps.output"])
    vf = (
        f"fps={out_fps},fade=t=in:st=0:d={fade_in:.3f},"
        f"fade=t=out:st={fade_out_start:.3f}:d={fade_out:.3f}"
    )
    target = os.path.join(
        self.segment_root,
        f"{self._segment_count:02d}_{self._segment_label}.mp4",
    )
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-framerate",
            str(self.fps),
            "-i",
            os.path.join(self.frame_dir, "frame_%04d.png"),
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-r",
            str(out_fps),
            target,
        ],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    self.segments.append(target)
    return target

  def _log(
      self,
      kind: str,
      text: str,
      computed: float,
      frames: int,
      fades: float = 0.0,
      **extra: object,
  ) -> None:
    """Appends a readability record for a coach mark or card."""
    held = frames / self.fps
    entry: dict[str, object] = {
        "segment": self._segment_label,
        "kind": kind,
        "text": text,
        "computed_hold_s": round(computed, 3),
        "held_s": round(held, 3),
        "readable_s": round(held - fades, 3),
        "chip": self._chip_text,
        "scenario_id": self.scenario_id,
    }
    entry.update(extra)
    self.frame_log.append(entry)

  def hold_frames(self, seconds: float) -> int:
    """Holds the current frame for `seconds` and returns frames written."""
    count = max(1, int(round(seconds * self.fps)))
    self.snap_frame(repeat=count)
    return count

  # ---- cursor and input ---------------------------------------------------

  def move_to(self, x: float, y: float, steps: int | None = None) -> None:
    """Moves the cursor with distance-scaled `easeInOutCubic` travel."""
    x0, y0 = self.cur_x, self.cur_y
    dist_ref = ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5 / self.scale
    if steps is None:
      steps = max(1, int(round(cursor_travel_seconds(dist_ref) * self.fps)))
    for i in range(1, steps + 1):
      t = i / steps
      ease = 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
      self.cur_x = x0 + (x - x0) * ease
      self.cur_y = y0 + (y - y0) * ease
      self.eval_js(
          f"window.__armRec.cursor({self.cur_x:.1f}, {self.cur_y:.1f}, false)"
      )
      self.snap_frame(repeat=1)

  def _hotspot(self, selector: str) -> tuple[float, float]:
    """Returns the click hotspot (55% / 55%) inside `selector`."""
    rect = self.eval_js(f"window.__armRec.rect({json.dumps(selector)})")
    if not isinstance(rect, dict):
      where = self.eval_js("location.href + ' (' + document.readyState + ')'")
      raise RuntimeError(f"Target not found or hidden: {selector} on {where}")
    k = float(DESIGN_TOKENS["layout"]["cursor.hotspot"])
    return (
        float(rect["left"]) + float(rect["width"]) * k,
        float(rect["top"]) + float(rect["height"]) * k,
    )

  def _dispatch_click(self, x: float, y: float) -> None:
    """Dispatches a real left click at viewport `(x, y)`."""
    for kind in ("mousePressed", "mouseReleased"):
      self.call(
          "Input.dispatchMouseEvent",
          {"type": kind, "x": x, "y": y, "button": "left", "clickCount": 1},
      )

  # ---- narration ----------------------------------------------------------

  def show_coach(
      self,
      selector: str | None,
      text: str,
      secondary: str | None,
      step: int,
      steps: int,
      state: str | None,
  ) -> dict[str, object]:
    """Spotlights `selector` and shows the coach mark beside it."""
    self.ensure_overlay()
    if selector:
      self.eval_js(f"window.__armRec.spot({json.dumps(selector)})")
    else:
      self.eval_js("window.__armRec.spot('')")
    placement = self.eval_js(
        "window.__armRec.coach("
        + json.dumps({
            "selector": selector or "",
            "primary": text,
            "secondary": secondary or "",
            "step": step,
            "steps": steps,
            "state": state,
        })
        + ")"
    )
    self._capture_transition()
    return placement if isinstance(placement, dict) else {}

  def _capture_transition(self) -> None:
    """Records the coach entrance and spotlight move until they settle.

    Screenshots are taken in real time, so holding the first frame right
    after showing the coach would freeze it mid-fade.
    """
    settle_s = (
        max(
            float(DESIGN_TOKENS["motion"]["base_ms"]),
            float(DESIGN_TOKENS["motion"]["slow_ms"]),
        )
        / 1000.0
        + 0.05
    )
    step = 1.0 / self.fps
    start = time.time()
    while time.time() - start < settle_s:
      self.snap_frame(repeat=1)
      time.sleep(step / 2)

  def narrate(
      self,
      selector: str | None,
      text: str,
      secondary: str | None,
      step: int,
      steps: int,
      state: str | None = None,
      hold_seconds: float | None = None,
      travel: bool = True,
  ) -> float:
    """Shows a coach mark and holds it for its computed reading time."""
    self.ensure_overlay()
    self.eval_js("window.__armRec.clearCoach()")
    if selector:
      x, y = self._hotspot(selector)
      self.eval_js(f"window.__armRec.spot({json.dumps(selector)})")
      if travel:
        self.move_to(x, y)
    placement = self.show_coach(selector, text, secondary, step, steps, state)
    computed = resolve_hold(coach_hold_seconds(text, secondary), hold_seconds)
    frames = self.hold_frames(computed)
    self._log(
        "coach",
        text,
        computed,
        frames,
        badge=state,
        placement=placement.get("side"),
    )
    return computed

  def click(
      self,
      selector: str,
      narration: dict[str, object] | None,
      step: int,
      steps: int,
      state: str | None = None,
      observe: bool = True,
  ) -> None:
    """Travel, dwell with spotlight, click, then observe (and narrate)."""
    self.ensure_overlay()
    self.eval_js("window.__armRec.clearCoach()")
    x, y = self._hotspot(selector)
    self.eval_js(f"window.__armRec.spot({json.dumps(selector)})")
    self.move_to(x, y)
    self.hold_frames(PACING["click.dwell"])
    self.eval_js(
        f"window.__armRec.cursor({x:.1f}, {y:.1f}, true);"
        f" window.__armRec.ripple({x:.1f}, {y:.1f});"
    )
    self._dispatch_click(x, y)
    self.snap_frame(repeat=2)
    self.eval_js(f"window.__armRec.cursor({x:.1f}, {y:.1f}, false)")
    self.eval_js("window.__armRec.spot('')")
    if not narration:
      if observe:
        self.hold_frames(PACING["click.observe_min"])
      return
    self.hold_frames(PACING["click.result_delay"])
    self.ensure_overlay()
    target = narration.get("selector")
    text = str(narration.get("text", ""))
    secondary = narration.get("secondary")
    placement = self.show_coach(
        str(target) if target else None,
        text,
        str(secondary) if secondary else None,
        step,
        steps,
        state,
    )
    computed = resolve_hold(
        max(
            PACING["click.observe_min"],
            coach_hold_seconds(text, str(secondary or "")),
        ),
        narration.get("hold_seconds"),
    )
    frames = self.hold_frames(computed)
    self._log(
        "coach",
        text,
        computed,
        frames,
        badge=state,
        placement=placement.get("side"),
    )

  def type_text(
      self,
      selector: str,
      value: str,
      narration: dict[str, object] | None,
      step: int,
      steps: int,
      state: str | None = None,
  ) -> None:
    """Clicks into `selector`, types `value` at `type.cps`, then observes."""
    self.click(selector, None, step, steps, state, observe=False)
    written = 0
    for i, ch in enumerate(value):
      self.call("Input.insertText", {"text": ch})
      due = int(round((i + 1) / PACING["type.cps"] * self.fps))
      while written < due:
        self.snap_frame(repeat=1)
        written += 1
    if not narration:
      self.hold_frames(PACING["click.observe_min"])
      return
    target = str(narration.get("selector") or selector)
    self.narrate(
        target,
        str(narration.get("text", "")),
        narration.get("secondary"),
        step,
        steps,
        state,
        narration.get("hold_seconds"),
        travel=target != selector,
    )

  def fast_forward_wait(
      self,
      predicate_js: str,
      timeout_s: float = 300.0,
      capture_interval_s: float | None = None,
      phase_expr_js: str | None = None,
      fatal_error_selector: str | None = None,
  ) -> float:
    """Captures a labeled fast-forward segment until `predicate_js` is true."""
    interval = capture_interval_s or PACING["ff.sample_default"]
    speedup = max(1, round(interval * self.fps))
    self.ensure_overlay()
    self.eval_js("window.__armRec.clearCoach()")
    self.hold_frames(PACING["ff.margin"])
    start = time.time()
    while True:
      elapsed = time.time() - start
      phase = ""
      if phase_expr_js:
        try:
          phase = str(self.eval_js(phase_expr_js) or "")
        except RuntimeError:
          phase = ""
      label = f"Fast-forward \u00d7{speedup}" + (
          f" \u00b7 {phase}" if phase else ""
      )
      self.eval_js(
          f"window.__armRec.ff({json.dumps(label)},"
          f" {json.dumps(f'{int(elapsed)}s')})"
      )
      self.snap_frame(repeat=1)
      if fatal_error_selector and self.eval_js(
          "(() => { const el = document.querySelector("
          + json.dumps(fatal_error_selector)
          + "); if (!el) return false; const r = el.getBoundingClientRect();"
          " return r.width > 0 || r.height > 0; })()"
      ):
        self._diagnostic("fatal error banner visible")
        raise RuntimeError(
            f"Fatal error banner visible: {fatal_error_selector}"
        )
      if self.eval_js(f"Boolean(({predicate_js.strip().rstrip(';')}))"):
        break
      if elapsed > timeout_s:
        self._diagnostic(f"timed out after {timeout_s:.0f}s")
        raise TimeoutError(f"wait_for_js timed out after {timeout_s:.0f}s")
      time.sleep(interval)
    self.eval_js("window.__armRec.ff('', '')")
    self.hold_frames(PACING["ff.margin"])
    return time.time() - start

  def _diagnostic(self, reason: str) -> str:
    """Saves a diagnostic PNG for a stalled or failed wait."""
    target = os.path.join(self.out_dir, f"{self.name}_diagnostic.png")
    shot = self.call("Page.captureScreenshot", {"format": "png"})
    with open(target, "wb") as f:
      f.write(base64.b64decode(str(shot["data"])))
    self.frame_log.append(
        {"kind": "diagnostic", "reason": reason, "path": target}
    )
    return target

  # ---- tabs ---------------------------------------------------------------

  def _new_target(self) -> str:
    """Creates an `about:blank` page target and returns its id."""
    req = urllib.request.Request(
        f"http://127.0.0.1:{self.port}/json/new?about:blank", method="PUT"
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
      return str(json.loads(resp.read().decode("utf-8"))["id"])

  def _close_target(self, target_id: str | None) -> None:
    """Closes a page target, ignoring errors."""
    if not target_id:
      return
    try:
      urllib.request.urlopen(
          f"http://127.0.0.1:{self.port}/json/close/{target_id}", timeout=3.0
      ).close()
    except OSError:
      pass

  def open_fresh_tab(self) -> None:
    """Moves recording to a new tab before loading the next variant.

    Each footage variant starts in its own tab so scenarios never share app
    state, and so the first load of every variant is a fresh navigation
    (managed Chrome can reject a later cross-origin `Page.navigate` in a tab
    that already handled input, with `net::ERR_BLOCKED_BY_ADMINISTRATOR`).
    """
    old_id = getattr(self, "_page_target_id", None)
    if old_id is None and self.attach_port is None:
      # First variant in a recorder-launched browser: retire its initial tab.
      with urllib.request.urlopen(
          f"http://127.0.0.1:{self.port}/json/list", timeout=5.0
      ) as resp:
        targets = json.loads(resp.read().decode("utf-8"))
      card_id = getattr(self, "_card_target_id", None)
      for target in targets:
        if target.get("type") == "page" and target.get("id") != card_id:
          old_id = str(target.get("id"))
          break
    new_id = self._new_target()
    if self.ws is not None:
      self.ws.close()
    self.ws = cdp.open_cdp_page_ws(self.port, new_id)
    self._page_target_id = new_id
    self.call("Page.bringToFront")
    self.call("Page.enable")
    self.call("Runtime.enable")
    self.call(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": self.width,
            "height": self.height,
            "deviceScaleFactor": 1,
            "mobile": False,
        },
    )
    # Only ever closes tabs this recorder created (or the initial tab of a
    # browser it launched); an attached user browser keeps its own tabs.
    self._close_target(old_id)

  # ---- cards --------------------------------------------------------------

  def _card_tab(self) -> cdp.MiniCDPWebSocket:
    """Returns (creating on first use) the dedicated card tab's socket.

    Cards render in their own `about:blank` tab, so the recording tab and its
    app state are never touched by card rendering.
    """
    if getattr(self, "_card_ws", None) is not None:
      return self._card_ws
    self._card_target_id = self._new_target()
    ws = cdp.open_cdp_page_ws(self.port, self._card_target_id)
    ws.call("Page.enable")
    ws.call("Runtime.enable")
    ws.call(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": self.width,
            "height": self.height,
            "deviceScaleFactor": 1,
            "mobile": False,
        },
    )
    self._card_ws = ws
    self._card_eval(REEL_CARD_JS)
    return ws

  def _card_eval(self, expr: str) -> object:
    """Evaluates `expr` in the card tab and returns its value."""
    res = self._card_ws.call(
        "Runtime.evaluate",
        {"expression": expr, "returnByValue": True, "awaitPromise": True},
    )
    if res.get("exceptionDetails"):
      raise RuntimeError(f"Card render failed: {res['exceptionDetails']}")
    result = res.get("result")
    return result.get("value") if isinstance(result, dict) else None

  def render_card(
      self,
      card: dict[str, object],
      computed: float,
      fade_in: float,
      fade_out: float,
      kind: str,
  ) -> None:
    """Renders a Direction C card in the card tab and holds it.

    The hold is extended by the fade durations so readable time stays at
    least `computed`.

    Args:
      card: Card spec passed to `window.__armRecCard` (type, text, images).
      computed: Reading-time hold in seconds before fades are added.
      fade_in: Fade-in duration of the enclosing segment, in seconds.
      fade_out: Fade-out duration of the enclosing segment, in seconds.
      kind: Frame-log kind (`card`, `interstitial`, or `recap`).
    """
    ws = self._card_tab()
    # Background tabs do not paint in headless Chrome, so screenshots of a
    # hidden card tab never resolve; bring it to the front first.
    ws.call("Page.bringToFront")
    self._card_eval("window.__armRecCard(" + json.dumps(card) + ")")
    time.sleep(0.05)
    shot = ws.call("Page.captureScreenshot", {"format": "png"})
    png = base64.b64decode(str(shot["data"]))
    count = max(1, int(round((computed + fade_in + fade_out) * self.fps)))
    for _ in range(count):
      path = os.path.join(self.frame_dir, f"frame_{self.frame_idx:04d}.png")
      with open(path, "wb") as f:
        f.write(png)
      self.frame_idx += 1
    text = str(card.get("headline") or card.get("takeaway") or "")
    self._log(kind, text, computed, count, fades=fade_in + fade_out)

  def close(self) -> None:
    """Closes the card tab and any recorder-created page tab, then Chrome."""
    ws = getattr(self, "_card_ws", None)
    if ws is not None:
      ws.close()
      self._card_ws = None
      self._close_target(self._card_target_id)
    page_id = getattr(self, "_page_target_id", None)
    if page_id is not None:
      if self.ws is not None:
        self.ws.close()
        self.ws = None
      self._close_target(page_id)
      self._page_target_id = None
    super().close()


# --------------------------------------------------------------------------
# Reel runner
# --------------------------------------------------------------------------


def _run_variant(
    rec: ReelRecorder,
    url: str,
    steps: list[dict[str, object]],
    state: str | None,
) -> bytes:
  """Runs one footage variant and returns a clean PNG of its final state."""
  total = coach_step_total(steps)
  n = 0
  rec.open_fresh_tab()
  rec.navigate(url)
  rec.hold_frames(PACING["scene.settle"])
  for step in steps:
    action = step["action"]
    if action == "narrate":
      n += 1
      rec.narrate(
          step.get("selector"),
          str(step["text"]),
          step.get("secondary"),
          n,
          total,
          state,
          step.get("hold_seconds"),
      )
    elif action == "click":
      narration = (
          step.get("narrate") if isinstance(step.get("narrate"), dict) else None
      )
      if narration:
        n += 1
      rec.click(
          str(step["selector"]), narration, max(n, 1), max(total, 1), state
      )
    elif action == "type":
      narration = (
          step.get("narrate") if isinstance(step.get("narrate"), dict) else None
      )
      if narration:
        n += 1
      rec.type_text(
          str(step["selector"]),
          str(step["value"]),
          narration,
          max(n, 1),
          max(total, 1),
          state,
      )
    elif action == "wait_for_js":
      rec.fast_forward_wait(
          str(step["predicate_js"]),
          timeout_s=float(step.get("timeout_s", 300.0)),
          capture_interval_s=step.get("capture_interval_s"),
          phase_expr_js=step.get("phase_expr_js"),
          fatal_error_selector=step.get("fatal_error_selector"),
      )
    elif action == "navigate":
      rec.navigate(str(step["url"]))
      rec.hold_frames(PACING["scene.settle"])
    elif action == "mask_secrets":
      rec.mask_sensitive_dom(step.get("extra_selectors"))
    elif action == "eval":
      rec.eval_js(str(step["expression"]))
    elif action == "screenshot":
      rec.save_clean_screenshot(str(step["path"]))
  final = rec.clean_png()
  rec.hold_frames(PACING["fade.out"])
  return final


def run_reel(spec: dict[str, object]) -> dict[str, object]:
  """Records a v2 instructional reel and returns output paths and logs."""
  errors, warnings = validate_reel_spec(spec)
  if errors:
    raise ValueError("Invalid reel spec:\n  " + "\n  ".join(errors))
  reel = spec["reel"]
  assert isinstance(reel, dict)
  name = str(spec.get("name", "reel"))
  out_dir = os.path.abspath(str(spec.get("out_dir", "/tmp/armature_reels")))
  os.makedirs(out_dir, exist_ok=True)
  fi, fo, ft = PACING["fade.in"], PACING["fade.out"], PACING["fade.through"]
  rec = ReelRecorder(
      name=name,
      out_dir=out_dir,
      scratch_dir=spec.get("scratch_dir"),
      width=int(spec.get("width", 1440)),
      height=int(spec.get("height", 900)),
      fps=int(PACING["fps.capture"]),
      attach_port=spec.get("attach_port"),
  )
  scenarios = list(reel["scenarios"])
  total = len(scenarios)
  try:
    rec.begin_segment("intro")
    intro = {
        "type": "solo",
        "kicker": str(reel.get("kicker") or "Armature review"),
        "headline": reel["title"],
        "body": reel["summary"],
    }
    rec.render_card(
        intro, card_hold_seconds(reel["title"], reel["summary"]), fi, fo, "card"
    )
    rec.end_segment(fi, fo)

    for k, sc in enumerate(scenarios, start=1):
      rec.scenario_id = str(sc["id"])
      rec.set_chip("")
      rec.begin_segment(f"s{k}_card")
      card = {
          "type": "numbered",
          "number": f"{k:02d}",
          "kicker": f"Scenario {k} of {total}",
          "headline": sc["title"],
          "body": sc["goal"],
          "watch": sc["watch_for"],
      }
      rec.render_card(
          card,
          card_hold_seconds(sc["title"], sc["goal"], sc["watch_for"]),
          fi,
          fo,
          "card",
      )
      rec.end_segment(fi, fo)
      compare = sc.get("compare")
      if not compare:
        rec.begin_segment(f"s{k}_current")
        rec.set_chip(f"Scenario {k} of {total}", None)
        _run_variant(rec, sc["url"], sc["steps"], None)
        rec.end_segment(fi, fo)
        continue
      rec.begin_segment(f"s{k}_before")
      rec.set_chip(f"Scenario {k} of {total} \u00b7 BEFORE", "before")
      before_png = _run_variant(
          rec, compare["before"]["url"], compare["before"]["steps"], "before"
      )
      rec.end_segment(fi, ft)
      rec.set_chip("")
      rec.begin_segment(f"s{k}_switch")
      rec.render_card(
          {
              "type": "solo",
              "kicker": "Switching versions",
              "headline": "Now the new version",
          },
          PACING["interstitial.hold"],
          ft,
          ft,
          "interstitial",
      )
      rec.end_segment(ft, ft)
      rec.begin_segment(f"s{k}_after")
      rec.set_chip(f"Scenario {k} of {total} \u00b7 AFTER", "after")
      after_png = _run_variant(
          rec, compare["after"]["url"], compare["after"]["steps"], "after"
      )
      rec.end_segment(ft, fo)
      rec.set_chip("")
      if compare.get("recap", True):
        rec.begin_segment(f"s{k}_recap")
        recap = {
            "type": "recap",
            "header": f"Scenario {k} recap",
            "before_image": (
                "data:image/png;base64,"
                + base64.b64encode(before_png).decode("ascii")
            ),
            "after_image": (
                "data:image/png;base64,"
                + base64.b64encode(after_png).decode("ascii")
            ),
            "before_label": str(compare.get("before_label", "")),
            "after_label": str(compare.get("after_label", "")),
            "takeaway": compare["takeaway"],
        }
        rec.render_card(
            recap, recap_hold_seconds(compare["takeaway"]), fi, fo, "recap"
        )
        rec.end_segment(fi, fo)

    outro_cfg = reel.get("outro") or {}
    items = list(outro_cfg.get("items", []))
    outro_title = str(outro_cfg.get("title") or "What this reel verified")
    rec.begin_segment("outro")
    rec.render_card(
        {
            "type": "solo",
            "kicker": "Summary",
            "headline": outro_title,
            "items": items,
        },
        card_hold_seconds(outro_title, items=items),
        fi,
        fo,
        "card",
    )
    rec.end_segment(fi, fo)

    stitched = cdp.stitch_scenario_clips(
        clip_paths=rec.segments,
        out_mp4=os.path.join(out_dir, f"{name}.mp4"),
        out_webm=os.path.join(out_dir, f"{name}.webm"),
        out_gif=os.path.join(out_dir, f"{name}.gif"),
        gif_width=int(spec.get("gif_width", 1080)),
        fps=int(spec.get("gif_fps", 15)),
    )
    log_path = os.path.join(out_dir, f"{name}_frame_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
      json.dump({"warnings": warnings, "entries": rec.frame_log}, f, indent=2)
    return {
        "name": name,
        "mp4": stitched["mp4"],
        "webm": stitched.get("webm"),
        "gif": stitched.get("gif"),
        "segments": list(rec.segments),
        "frame_log": log_path,
        "warnings": warnings,
    }
  finally:
    rec.close()


def readability_violations(frame_log: list[dict[str, object]]) -> list[str]:
  """Lists coach marks or cards that were readable for less than computed."""
  problems = []
  for e in frame_log:
    if e.get("kind") in ("coach", "card", "interstitial", "recap"):
      readable = float(e.get("readable_s", 0.0))
      # One frame of tolerance for rounding to the capture frame rate.
      if readable + 1.0 / PACING["fps.capture"] < float(e["computed_hold_s"]):
        problems.append(
            f"{e.get('segment')}: {e.get('text')!r} readable {readable}s <"
            f" computed {e['computed_hold_s']}s"
        )
  return problems


def main() -> None:
  """CLI entry point: records a v2 reel from a JSON recipe."""
  parser = argparse.ArgumentParser(description="Record an instructional reel.")
  parser.add_argument("--spec", required=True, help="Path to JSON reel recipe.")
  parser.add_argument(
      "--validate_only",
      action="store_true",
      help="Validate the recipe and exit.",
  )
  args = parser.parse_args()
  with open(args.spec, "r", encoding="utf-8") as f:
    spec = json.load(f)
  if args.validate_only:
    errors, warnings = validate_reel_spec(spec)
    print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
    raise SystemExit(1 if errors else 0)
  print(json.dumps(run_reel(spec), indent=2))


if __name__ == "__main__":
  main()
