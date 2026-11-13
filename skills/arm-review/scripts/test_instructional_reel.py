#!/usr/bin/env python3
"""Unit and integration tests for `instructional_reel.py` (ADR 0020)."""

import functools
import http.server
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest

import cdp_screencast_recorder
import instructional_reel as reel

FIXTURE_APP = """<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="Content-Security-Policy" content="require-trusted-types-for 'script';">
  <title>Orders fixture (__VARIANT__)</title>
  <style>
    body { margin: 0; font: 16px system-ui, sans-serif; background: #f6f7f9; }
    header { height: 64px; background: #fff; display: flex; align-items: center;
             padding: 0 24px; border-bottom: 1px solid #ddd; }
    main { padding: 24px 32px; }
    .bar { display: flex; gap: 12px; align-items: center; }
    h1 { margin: 0 auto 0 0; font-size: 26px; }
    button { height: 40px; padding: 0 18px; border-radius: 20px; border: 1px solid #bbb;
             background: #fff; font: inherit; }
    #export { background: #1a73e8; color: #fff; border: 0; }
    #count { display: inline-block; margin: 14px 0; color: #555; }
    #toast { position: fixed; right: 24px; bottom: 24px; background: #202124; color: #fff;
             padding: 12px 18px; border-radius: 8px; display: none; }
    #name { height: 36px; width: 240px; }
  </style>
</head>
<body>
  <header>Storefront Admin</header>
  <main>
    <div class="bar"><h1>Orders</h1>
      <button id="filter">All statuses</button>
      <button id="export">Export CSV</button></div>
    <div id="count">Showing 1,284 orders</div>
    <div><input id="name" name="note" placeholder="Note"></div>
    <input id="secret" type="password" value="hunter2">
  </main>
  <div id="toast"></div>
  <script>
    const VARIANT = '__VARIANT__';
    let filtered = false;
    window.__exported = false;
    const render = () => {
      document.getElementById('filter').textContent =
          filtered ? 'Status: Pending' : 'All statuses';
      document.getElementById('count').textContent =
          filtered ? 'Showing 42 of 1,284 orders' : 'Showing 1,284 orders';
    };
    document.getElementById('filter').addEventListener('click', () => {
      filtered = !filtered; render();
    });
    document.getElementById('export').addEventListener('click', () => {
      const rows = filtered ? 42 : 1284;
      if (VARIANT === 'baseline') { filtered = false; render(); }
      const t = document.getElementById('toast');
      t.textContent = 'orders.csv downloaded \\u00b7 ' + rows + ' rows';
      t.style.display = 'block';
      setTimeout(() => { window.__exported = true; }, 900);
    });
    if (location.search.includes('filtered=1')) { filtered = true; }
    render();
  </script>
</body>
</html>
"""


def _serve(directory: str) -> tuple[http.server.ThreadingHTTPServer, int]:
  """Serves `directory` over HTTP on a free port in a daemon thread."""
  handler = functools.partial(
      http.server.SimpleHTTPRequestHandler, directory=directory
  )
  handler.log_message = lambda *a, **k: None  # type: ignore[assignment]
  server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
  threading.Thread(target=server.serve_forever, daemon=True).start()
  return server, server.server_address[1]


def _words(n: int) -> str:
  """Returns `n` placeholder words."""
  return " ".join(["word"] * n)


class PacingAndTokensTest(unittest.TestCase):
  """Pacing formulas, token contrast, and overlay script hygiene."""

  def test_coach_hold_matches_spec_examples(self):
    self.assertAlmostEqual(reel.coach_hold_seconds(_words(19)), 5.4)
    self.assertEqual(reel.coach_hold_seconds("Short."), 2.0)
    self.assertEqual(reel.beat_hold_seconds("Selecting Standard Preset..."), 1.3)
    self.assertAlmostEqual(reel.beat_hold_seconds(_words(8)), 2.5)

  def test_card_hold_ignores_kicker_and_has_floor(self):
    self.assertAlmostEqual(reel.card_hold_seconds(_words(23)), 1.0 + 23 / 4.5)
    self.assertEqual(reel.card_hold_seconds("Hi"), 2.7)

  def test_recap_and_override_only_raise(self):
    self.assertEqual(reel.recap_hold_seconds("Tiny."), 3.3)
    self.assertEqual(reel.resolve_hold(5.0, 2.0), 5.0)
    self.assertEqual(reel.resolve_hold(5.0, 7.5), 7.5)
    self.assertEqual(reel.resolve_hold(5.0, None), 5.0)

  def test_cursor_travel_is_clamped_linear(self):
    self.assertAlmostEqual(reel.cursor_travel_seconds(50), 0.4)
    self.assertAlmostEqual(reel.cursor_travel_seconds(700), 0.575)
    self.assertAlmostEqual(reel.cursor_travel_seconds(5000), 0.75)

  def test_every_token_pair_meets_its_contrast_minimum(self):
    """Every text pair in CONTRAST_PAIRS meets its minimum ratio."""
    expected = {
        "coach primary": 13.3,
        "coach secondary": 10.5,
        "coach eyebrow": 9.1,
        "beat hint text": 13.3,
        "coach BEFORE badge": 13.3,
        "coach AFTER badge": 9.5,
        "BEFORE badge": 13.1,
        "AFTER badge": 9.4,
        "card headline": 21.0,
        "card body": 13.0,
        "card number and kicker": 15.0,
        "chip text": 13.3,
        "fast-forward elapsed clock": 10.5,
        "outro check": 8.2,
        "recap BEFORE swatch": 13.1,
        "recap AFTER swatch": 9.4,
        "active step dot (non-text)": 13.3,
    }
    report = {e["label"]: e for e in reel.token_contrast_report()}
    self.assertEqual(set(report), set(expected))
    for label, ratio in expected.items():
      self.assertTrue(report[label]["passes"], label)
      self.assertAlmostEqual(report[label]["ratio"], ratio, delta=0.1)

  def test_overlay_and_card_js_have_no_html_string_sinks(self):
    for js in (reel.REEL_OVERLAY_JS, reel.REEL_CARD_JS):
      self.assertNotIn("innerHTML", js)
      self.assertNotIn("outerHTML", js)
      self.assertNotIn("insertAdjacentHTML", js)
      self.assertNotIn("__TOKENS__", js)
    self.assertNotIn("cdp-demo-overlay-root", reel.REEL_OVERLAY_JS)
    self.assertIn("armature-rec-coach", reel.REEL_OVERLAY_JS)
    self.assertIn("armature-rec-beat", reel.REEL_OVERLAY_JS)
    self.assertEqual(reel.DESIGN_TOKENS["color"]["chip.bg"], "#FDD663")
    self.assertEqual(reel.DESIGN_TOKENS["color"]["chip.text"], "#181200")


class ValidationTest(unittest.TestCase):
  """Recipe validation errors and warnings."""

  def _base(self):
    """Returns a minimal valid current-only recipe."""
    return {
        "reel": {
            "title": "Filtering orders",
            "summary": "One scenario.",
            "scenarios": [{
                "id": "filter",
                "title": "Filter",
                "goal": "Filter the list.",
                "watch_for": "the count.",
                "url": "http://localhost:1/",
                "steps": [{"action": "narrate", "text": "Hi."}],
            }],
            "outro": {"items": ["Filter works"]},
        }
    }

  def test_valid_current_only_spec(self):
    errors, warnings = reel.validate_reel_spec(self._base())
    self.assertEqual(errors, [])
    self.assertEqual(warnings, [])

  def test_compare_requires_both_variants_and_takeaway(self):
    spec = self._base()
    sc = spec["reel"]["scenarios"][0]
    sc["compare"] = {"before": {"url": "http://localhost:1/", "steps": []}}
    errors, _ = reel.validate_reel_spec(spec)
    self.assertIn(
        "reel.scenarios[0].compare.before.steps must be a non-empty list",
        errors,
    )
    self.assertIn("reel.scenarios[0].compare.after.url is required", errors)
    self.assertIn("reel.scenarios[0].compare.takeaway is required", errors)

  def test_length_limits_warn(self):
    spec = self._base()
    spec["reel"]["scenarios"][0]["steps"][0]["text"] = "x" * 95
    _, warnings = reel.validate_reel_spec(spec)
    self.assertTrue(any("coach.primary" in w for w in warnings))

  def test_eval_screenshot_and_narrate_shapes_are_validated(self):
    """Steps that would crash run_reel are rejected up front."""
    spec = self._base()
    spec["reel"]["scenarios"][0]["steps"] = [
        {"action": "eval"},
        {"action": "screenshot"},
        {"action": "click", "selector": "#a", "narrate": "See it?"},
        {"action": "type", "selector": "#b", "value": "x", "narrate": {}},
    ]
    errors, _ = reel.validate_reel_spec(spec)
    self.assertEqual(len(errors), 4, errors)

  def test_unknown_action_and_missing_selector_are_errors(self):
    spec = self._base()
    spec["reel"]["scenarios"][0]["steps"] = [
        {"action": "dance"},
        {"action": "click"},
        {"action": "beat"},
        {"action": "beat", "selector": "#a"},
        {"action": "click", "selector": "#a", "beat": ""},
    ]
    errors, _ = reel.validate_reel_spec(spec)
    self.assertEqual(len(errors), 6, errors)

  def test_copy_hygiene_warns_on_code_jargon_and_ai_filler(self):
    """Warns when user-facing screencast text leaks jargon or AI filler."""
    spec = self._base()
    sc = spec["reel"]["scenarios"][0]
    sc["title"] = "Run _internal_helper with __EXPORT_FLAG"
    sc["goal"] = "Call load_or_synthesize_raw_spec() and pass UNVERIFIED_CLEAN."
    sc["steps"] = [
        {
            "action": "beat",
            "selector": "#btn",
            "text": "Seamlessly hitting /v1/alerts/dryrun",
        },
        {
            "action": "narrate",
            "text": 'Reading "/api/v2/reconcile" status.',
        },
        {
            "action": "click",
            "selector": "#btn",
            "beat": "Selecting Standard Preset...",
        },
    ]
    errors, warnings = reel.validate_reel_spec(spec)
    self.assertEqual(errors, [])
    joined = "\n".join(warnings)
    self.assertIn("load_or_synthesize_raw_spec", joined)
    self.assertIn("_internal_helper", joined)
    self.assertIn("__EXPORT_FLAG", joined)
    self.assertIn("UNVERIFIED_CLEAN", joined)
    self.assertIn("/v1/alerts/dryrun", joined)
    self.assertIn("/api/v2/reconcile", joined)
    self.assertIn("AI-filler", joined)
    self.assertNotIn("Selecting Standard Preset", joined)

  def test_copy_hygiene_warns_on_backend_and_state_jargon(self):
    """Warns on lowercase backend/test jargon and passes plain UX copy."""
    spec = self._base()
    spec["reel"]["summary"] = "Build latches once on first open"
    sc = spec["reel"]["scenarios"][0]
    sc["title"] = "Project reads stay read-only"
    sc["goal"] = "Solid mesh part where status stays at none"
    sc["steps"] = [
        {"action": "narrate", "text": "Step 2 has an unmatched part."}
    ]
    errors, warnings = reel.validate_reel_spec(spec)
    self.assertEqual(errors, [])
    joined = "\n".join(warnings)
    for term in (
        "read-only",
        "latches",
        "mesh",
        "status stays at none",
        "unmatched",
    ):
      self.assertIn(term, joined)

    plain = self._base()
    plain["reel"]["scenarios"][0][
        "title"
    ] = "Open Build to refresh an outdated guide"
    plain["reel"]["scenarios"][0]["goal"] = (
        "Skips creating a guide for a one-piece 3D part"
    )
    p_errors, p_warnings = reel.validate_reel_spec(plain)
    self.assertEqual(p_errors, [])
    self.assertEqual(p_warnings, [])

  def test_beat_does_not_increment_coach_step_total(self):
    steps = [
        {"action": "beat", "selector": "#a", "text": "Selecting Standard Preset..."},
        {"action": "click", "selector": "#b", "beat": "Opening draft..."},
        {"action": "narrate", "text": "New parts start in a safe local draft."},
    ]
    self.assertEqual(reel.coach_step_total(steps), 1)


@unittest.skipUnless(
    cdp_screencast_recorder.resolve_chrome_binary() and shutil.which("ffmpeg"),
    "requires Chrome and ffmpeg",
)
class ReelIntegrationTest(unittest.TestCase):
  """End-to-end reel against baseline and current fixture servers."""

  def setUp(self):
    super().setUp()
    self.tmp = tempfile.mkdtemp(prefix="reel_test_")
    self.servers = []
    ports = {}
    for variant in ("baseline", "current"):
      d = os.path.join(self.tmp, variant)
      os.makedirs(d)
      with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
        f.write(FIXTURE_APP.replace("__VARIANT__", variant))
      server, port = _serve(d)
      self.servers.append(server)
      ports[variant] = port
    self.base = f"http://127.0.0.1:{ports['baseline']}/index.html"
    self.cur = f"http://127.0.0.1:{ports['current']}/index.html"

  def tearDown(self):
    for s in self.servers:
      s.shutdown()
    if not os.environ.get("KEEP_REEL_OUTPUT"):
      shutil.rmtree(self.tmp, ignore_errors=True)
    super().tearDown()

  def _spec(self):
    """Returns a two-scenario recipe (current-only + compare)."""
    export_steps = lambda url: [
        {
            "action": "narrate",
            "selector": "#count",
            "text": "Here's the list, filtered to 42 pending orders.",
        },
        {
            "action": "click",
            "selector": "#export",
            "narrate": {
                "selector": "#count",
                "text": "See what happens to the filter?",
                "secondary": "Check the toast for the row count.",
            },
        },
        {
            "action": "wait_for_js",
            "predicate_js": "window.__exported === true",
            "timeout_s": 10,
            "capture_interval_s": 0.3,
        },
    ]
    return {
        "name": "fixture_reel",
        "out_dir": (
            os.environ.get("KEEP_REEL_OUTPUT") or os.path.join(self.tmp, "out")
        ),
        "width": 1280,
        "height": 720,
        "reel": {
            "title": "Filtering and exporting orders",
            "summary": "Filter the list, then export it with the filter kept.",
            "scenarios": [
                {
                    "id": "filter",
                    "title": "Filter orders by status",
                    "goal": "Narrow the list to pending orders.",
                    "watch_for": "the row count under the title.",
                    "url": self.cur,
                    "steps": [
                        {
                            "action": "narrate",
                            "selector": "#count",
                            "text": "Here's the Orders list with all orders.",
                        },
                        {
                            "action": "beat",
                            "selector": "#filter",
                            "text": "Narrowing to pending orders...",
                        },
                        {
                            "action": "click",
                            "selector": "#filter",
                            "beat": "Filtering list...",
                            "narrate": {
                                "selector": "#count",
                                "text": "See how it now shows 42 orders?",
                            },
                        },
                        {
                            "action": "type",
                            "selector": "#name",
                            "value": "rush",
                            "narrate": {
                                "text": "All updates stay local to this draft.",
                            },
                        },
                    ],
                },
                {
                    "id": "export",
                    "title": "Export respects the active filter",
                    "goal": "Export the filtered list, old then new.",
                    "watch_for": "the row count in the toast.",
                    "compare": {
                        "before": {
                            "url": self.base + "?filtered=1",
                            "steps": export_steps(self.base),
                        },
                        "after": {
                            "url": self.cur + "?filtered=1",
                            "steps": export_steps(self.cur),
                        },
                        "before_label": "Filter cleared",
                        "after_label": "Filter kept",
                        "takeaway": "Export no longer resets the filter.",
                    },
                },
            ],
            "outro": {
                "items": ["Filter narrows the list", "Export keeps the filter"]
            },
        },
    }

  def test_reel_structure_pacing_and_modes(self):
    """Segments, readability, scenario modes, and 30 fps output."""
    res = cdp_screencast_recorder.run_spec_file(self._write(self._spec()))
    for key in ("mp4", "webm", "gif"):
      self.assertGreater(os.path.getsize(res[key]), 0, key)
    labels = [os.path.basename(p).split(".")[0] for p in res["segments"]]
    self.assertEqual(
        [l.split("_", 1)[1] for l in labels],
        [
            "intro",
            "s1_card",
            "s1_current",
            "s2_card",
            "s2_before",
            "s2_switch",
            "s2_after",
            "s2_recap",
            "outro",
        ],
    )
    with open(res["frame_log"], encoding="utf-8") as f:
      log = json.load(f)["entries"]
    self.assertEqual(reel.readability_violations(log), [])
    current = [e for e in log if e.get("segment") == "s1_current"]
    self.assertTrue(current)
    for e in current:
      self.assertIsNone(e.get("badge"))
      self.assertNotIn("BEFORE", e["chip"])
      self.assertNotIn("AFTER", e["chip"])
    before = [e for e in log if e.get("segment") == "s2_before"]
    after = [e for e in log if e.get("segment") == "s2_after"]
    self.assertTrue(all(e["badge"] == "before" for e in before))
    self.assertTrue(all(e["badge"] == "after" for e in after))
    self.assertTrue(any(e["kind"] == "interstitial" for e in log))
    self.assertTrue(any(e["kind"] == "recap" for e in log))
    beat_entries = [e for e in log if e.get("kind") == "beat"]
    self.assertGreaterEqual(len(beat_entries), 2)
    self.assertEqual({e.get("tailed") for e in beat_entries}, {True})
    stage_entries = [
        e
        for e in current
        if e.get("kind") == "coach" and e.get("placement") == "center"
    ]
    self.assertTrue(stage_entries)
    self.assertEqual({e.get("tailed") for e in stage_entries}, {False})
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate",
            "-of",
            "csv=p=0",
            res["segments"][0],
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    self.assertEqual(probe.stdout.strip(), "30/1")

  def test_coach_never_overlaps_ring_near_any_edge(self):
    """Coach placement stays clear of the ring box at all four frame edges."""
    page = os.path.join(self.tmp, "current", "edges.html")
    spots = {
        "tl": "left:8px;top:8px",
        "tr": "right:8px;top:8px",
        "bl": "left:8px;bottom:8px",
        "br": "right:8px;bottom:8px",
        "wide": "left:200px;right:200px;top:300px;height:80px",
        "tall": "left:560px;width:160px;top:40px;bottom:40px",
    }
    with open(page, "w", encoding="utf-8") as f:
      f.write(
          "<!DOCTYPE html><html><body style='margin:0'>"
          + "".join(
              f"<button id='{k}' style='position:fixed;{v};"
              "min-width:120px;min-height:40px'>x</button>"
              for k, v in spots.items()
          )
          + "</body></html>"
      )
    rec = reel.ReelRecorder(
        name="edges",
        out_dir=os.path.join(self.tmp, "e"),
        width=1280,
        height=720,
    )
    try:
      rec.open_fresh_tab()
      rec.navigate(self.cur.replace("index.html", "edges.html"))
      ring = (
          reel.DESIGN_TOKENS["layout"]["spot.pad"]
          + reel.DESIGN_TOKENS["layout"]["spot.stroke"]
      ) * rec.scale
      for sel in spots:
        placed = rec.show_coach(
            "#" + sel,
            "Here is a fairly long line of narration text.",
            "And a secondary line.",
            1,
            1,
            None,
        )
        r = rec.eval_js(f"window.__armRec.rect('#{sel}')")
        box = (
            r["left"] - ring,
            r["top"] - ring,
            r["right"] + ring,
            r["bottom"] + ring,
        )
        c = (
            placed["left"],
            placed["top"],
            placed["left"] + placed["width"],
            placed["top"] + placed["height"],
        )
        overlap = not (
            c[2] <= box[0] or c[0] >= box[2] or c[3] <= box[1] or c[1] >= box[3]
        )
        self.assertFalse(
            overlap, f"{sel}: coach {c} overlaps ring {box} ({placed['side']})"
        )
        self.assertGreaterEqual(c[0], 0, sel)
        self.assertGreaterEqual(c[1], 0, sel)
        self.assertLessEqual(c[2], 1280, sel)
        self.assertLessEqual(c[3], 720, sel)
        self.assertTrue(placed["tailed"], sel)
        beat_placed = rec.show_beat("#" + sel, "Selecting Standard Preset...")
        self.assertTrue(beat_placed["tailed"], sel)
        if beat_placed["side"] in ("left", "right"):
          tail_geom = rec.eval_js(
              "(() => { const b = document.getElementById('armature-rec-beat');"
              " const t = b.firstElementChild;"
              " return {top: parseFloat(t.style.top), bh: b.offsetHeight,"
              " ts: t.offsetHeight}; })()"
          )
          expected_top = (tail_geom["bh"] - tail_geom["ts"]) / 2
          self.assertAlmostEqual(
              tail_geom["top"], expected_top, delta=1.5, msg=sel
          )
      unanchored = rec.show_coach(None, "All checks passed.", None, 1, 1, None)
      self.assertEqual(unanchored["side"], "center")
      self.assertFalse(unanchored["tailed"])
      rec.set_chip("Scenario 1 of 1", "before")
      rec.eval_js("window.__armRec.ff('Fast-forward ×9', '12s')")
      chip_styles = rec.eval_js(
          "(() => { const c = document.getElementById('armature-rec-chip');"
          " const f = document.getElementById('armature-rec-ff-chip');"
          " const cs = getComputedStyle(c);"
          " const fs = getComputedStyle(f);"
          " const dot = c.firstElementChild;"
          " return {cBg: cs.backgroundColor, cColor: cs.color,"
          " fBg: fs.backgroundColor, fColor: fs.color,"
          " fClockColor: getComputedStyle(f.lastElementChild).color,"
          " dotBorder: dot ? getComputedStyle(dot).borderTopColor : null}; })()"
      )
      self.assertEqual(chip_styles["cBg"], "rgb(253, 214, 99)")
      self.assertEqual(chip_styles["cColor"], "rgb(24, 18, 0)")
      self.assertEqual(chip_styles["fBg"], "rgb(253, 214, 99)")
      self.assertEqual(chip_styles["fColor"], "rgb(24, 18, 0)")
      self.assertEqual(chip_styles["fClockColor"], "rgb(51, 39, 0)")
      self.assertEqual(chip_styles["dotBorder"], "rgb(24, 18, 0)")
      rec.set_chip("Scenario 1 of 1 \u00b7 AFTER", "after")
      after_dot = rec.eval_js(
          "(() => { const d ="
          " document.getElementById('armature-rec-chip').firstElementChild;"
          " const s = getComputedStyle(d);"
          " return {bg: s.backgroundColor, border: s.borderTopColor}; })()"
      )
      self.assertEqual(after_dot["bg"], "rgb(129, 201, 149)")
      self.assertEqual(after_dot["border"], "rgb(24, 18, 0)")
    finally:
      rec.close()

  def test_fast_forward_accepts_dom_node_predicates(self):
    """A predicate returning a DOM node counts as true."""
    rec = reel.ReelRecorder(
        name="ff", out_dir=os.path.join(self.tmp, "f"), width=1280, height=720
    )
    try:
      rec.begin_segment("ff")
      rec.open_fresh_tab()
      rec.navigate(self.cur)
      elapsed = rec.fast_forward_wait(
          "document.querySelector('#count');",
          timeout_s=5,
          capture_interval_s=0.2,
      )
      self.assertLess(elapsed, 5)
    finally:
      rec.close()

  def _write(self, spec):
    """Writes `spec` to a temp JSON file and returns its path."""
    path = os.path.join(self.tmp, "spec.json")
    with open(path, "w", encoding="utf-8") as f:
      json.dump(spec, f)
    return path


if __name__ == "__main__":
  unittest.main()
