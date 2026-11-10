#!/usr/bin/env python3
"""Unit and integration tests for `cdp_screencast_recorder.py` (ADR 0019)."""

import http.server
import json
import os
import tempfile
import threading
import unittest

import cdp_screencast_recorder

AttachedCDPRecorder = cdp_screencast_recorder.AttachedCDPRecorder
CDPRecorder = cdp_screencast_recorder.CDPRecorder
OVERLAY_INIT_JS = cdp_screencast_recorder.OVERLAY_INIT_JS
check_recording_prerequisites = (
    cdp_screencast_recorder.check_recording_prerequisites
)
publish_oss_media = cdp_screencast_recorder.publish_oss_media
resolve_chrome_binary = cdp_screencast_recorder.resolve_chrome_binary
run_spec_file = cdp_screencast_recorder.run_spec_file
stitch_scenario_clips = cdp_screencast_recorder.stitch_scenario_clips


TRUSTED_TYPES_TEST_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="Content-Security-Policy" content="require-trusted-types-for 'script';">
  <title>TrustedTypes Recorder Test</title>
</head>
<body>
  <input id="secret-pass" type="password" value="super-secret-123" />
  <input id="api-token" name="api_token" value="tok_live_abcdef" />
  <button id="start-btn" onclick="window.__phase='GENERATING'; setTimeout(() => { window.__phase='COMPLETED'; window.__done=true; }, 1200);">Start Job</button>
  <div id="fatal-banner" style="display:none;width:200px;height:40px;">Fatal backend crash</div>
  <script>
    window.__phase = 'IDLE';
    window.__done = false;
  </script>
</body>
</html>
"""


class _Handler(http.server.BaseHTTPRequestHandler):
  """Minimal HTTP handler serving the TrustedTypes CSP test page."""

  def do_GET(self):  # pylint: disable=invalid-name
    """Serves the TrustedTypes HTML fixture with CSP header."""
    body = TRUSTED_TYPES_TEST_HTML.encode("utf-8")
    self.send_response(200)
    self.send_header(
        "Content-Security-Policy", "require-trusted-types-for 'script'"
    )
    self.send_header("Content-Type", "text/html; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def log_message(self, format, *args):  # pylint: disable=redefined-builtin
    """Suppresses default HTTP server stderr logging during unit tests."""
    pass


class CDPScreencastRecorderTest(unittest.TestCase):
  """End-to-end tests for TrustedTypes overlays, secret masking, and timelapse."""

  def test_overlay_init_js_has_zero_inner_html(self):
    """Verifies OVERLAY_INIT_JS uses createElementNS and zero innerHTML sinks."""
    self.assertNotIn("innerHTML", OVERLAY_INIT_JS)
    self.assertNotIn("outerHTML", OVERLAY_INIT_JS)
    self.assertIn("createElementNS", OVERLAY_INIT_JS)
    self.assertIs(AttachedCDPRecorder, CDPRecorder)

  def test_prerequisite_check_rejects_file_and_data_urls(self):
    """Verifies pre-flight checks reject synthetic schemes and find Chrome."""
    res_file = check_recording_prerequisites(
        "screencast", "file:///tmp/mock.html"
    )
    self.assertFalse(res_file["ok"])
    self.assertIn("Rejected synthetic URL", str(res_file["server_start_hint"]))

    res_data = check_recording_prerequisites(
        "screenshot", "data:text/html,<h1>Mock</h1>"
    )
    self.assertFalse(res_data["ok"])

    res_upper = check_recording_prerequisites(
        "screencast", "FILE:///tmp/mock.html"
    )
    self.assertFalse(res_upper["ok"])

    res_about = check_recording_prerequisites("screencast", "about:blank")
    self.assertFalse(res_about["ok"])

    self.assertIsNotNone(resolve_chrome_binary())

  def test_live_server_trusted_types_timelapse_masking_and_stitching(self):
    """Verifies live-server CDP recording, masking, timelapse, and stitching."""
    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
      prereq = check_recording_prerequisites(
          "screencast", f"http://127.0.0.1:{port}/index.html"
      )
      self.assertTrue(prereq["server_reachable"])

      with tempfile.TemporaryDirectory() as tmp_dir:
        rec = CDPRecorder(
            name="scenario_1",
            out_dir=tmp_dir,
            width=800,
            height=600,
            fps=10,
            min_hold_sec=0.2,
        )
        try:
          with self.assertRaises(ValueError):
            rec.navigate("file:///tmp/fake.html")
          with self.assertRaises(ValueError):
            rec.navigate("FILE:///tmp/fake.html")
          with self.assertRaises(ValueError):
            rec.navigate("about:blank")

          rec.navigate(
              f"http://127.0.0.1:{port}/index.html?token=secret123&auth_token=jwt999&view=main#access_token=hashsecret",
              wait_sec=0.3,
          )
          has_overlay = rec.eval_js(
              "Boolean(document.getElementById('cdp-demo-overlay-root') &&"
              " document.getElementById('cdp-demo-cursor') &&"
              " document.getElementById('cdp-demo-caption-hud'))"
          )
          self.assertTrue(has_overlay)

          href = rec.eval_js("window.location.href")
          self.assertIn("token=REDACTED", href)
          self.assertIn("auth_token=REDACTED", href)
          self.assertIn("access_token=REDACTED", href)
          has_masked_class = rec.eval_js(
              "document.getElementById('api-token').classList.contains('cdp-demo-masked-secret')"
          )
          self.assertTrue(has_masked_class)

          with self.assertRaises(RuntimeError):
            rec.eval_js("throw new Error('synthetic js error')")

          rec.explain_and_hold(
              badge="STEP 1",
              title="Trigger Async Job",
              subtitle="Click Start Job and compress the async wait.",
              seconds=0.2,
              highlight_selector="#start-btn",
          )
          rec.click_selector("#start-btn", steps=2, hold_after=0.1)
          wait_res = rec.wait_for_js(
              predicate_js="window.__done === true;",
              timeout_s=10.0,
              capture_interval_s=0.5,
              badge="TIMELAPSE",
              title="Generating CAD Geometry",
              phase_expr_js="window.__phase",
              fatal_error_selector="#fatal-banner",
          )
          self.assertTrue(wait_res["completed"])
          self.assertEqual(wait_res["last_phase"], "COMPLETED")
          self.assertGreaterEqual(int(wait_res["frames_captured"]), 2)

          clip1 = rec.encode_mp4(os.path.join(tmp_dir, "scenario_1.mp4"))
          self.assertTrue(os.path.exists(clip1))

          # Trigger fatal error selector and verify diagnostic frame capture
          rec.eval_js(
              "document.getElementById('fatal-banner').style.display = 'block';"
              " window.__done = false;"
          )
          with self.assertRaises(RuntimeError):
            rec.wait_for_js(
                predicate_js="window.__done === true",
                timeout_s=3.0,
                capture_interval_s=0.5,
                fatal_error_selector="#fatal-banner",
            )
          self.assertTrue(
              os.path.exists(os.path.join(tmp_dir, "scenario_1_diagnostic.png"))
          )
        finally:
          rec.close()

        stitched = stitch_scenario_clips(
            [clip1],
            out_mp4=os.path.join(tmp_dir, "final_reel.mp4"),
            out_gif=os.path.join(tmp_dir, "final_reel.gif"),
            gif_width=480,
            fps=10,
        )
        self.assertTrue(os.path.exists(stitched["mp4"]))
        self.assertTrue(os.path.exists(stitched["gif"]))
        self.assertFalse(
            os.path.exists(os.path.join(tmp_dir, "concat_list.txt"))
        )

        spec_file = os.path.join(tmp_dir, "stitch_spec.json")
        with open(spec_file, "w", encoding="utf-8") as f:
          json.dump(
              {
                  "name": "spec_stitched",
                  "out_dir": tmp_dir,
                  "gif_width": 320,
                  "fps": 10,
                  "scenario_clips": [clip1],
              },
              f,
          )
        spec_res = run_spec_file(spec_file)
        self.assertTrue(os.path.exists(str(spec_res["mp4"])))
        self.assertTrue(os.path.exists(str(spec_res["webm"])))
        self.assertTrue(os.path.exists(str(spec_res["gif"])))

        pub = publish_oss_media(
            [stitched["mp4"], stitched["gif"]],
            track_recordings_dir=os.path.join(tmp_dir, "recordings"),
            git_host_mode="local",
        )
        self.assertEqual(len(pub["local_paths"]), 2)
        empty_pub = publish_oss_media(
            [],
            track_recordings_dir=os.path.join(tmp_dir, "recordings"),
            git_host_mode="github",
        )
        self.assertEqual(empty_pub["local_paths"], [])
    finally:
      server.shutdown()
      server.server_close()


if __name__ == "__main__":
  unittest.main()
