#!/usr/bin/env python3
"""TrustedTypes-Safe Headless CDP Screencast & Variable-Speed Timelapse Recorder.

Implements the ADR 0019 `AttachedCDPRecorder` / `CDPRecorder` standard for
`/arm-review`:
  1. Live Server Attachment Over CDP (`http://localhost:<PORT>/...` or HTTPS
     local dev server; rejects `file://` and `data:` mocks unless
     `allow_prototype_harness=True`).
  2. 100% TrustedTypes / CSP-Safe DOM & SVG Overlays constructed exclusively via
     `document.createElement` and `document.createElementNS` (zero `.innerHTML`
     or `.outerHTML` sinks).
  3. Dual-Pacing Variable-Speed Timelapse Engine (`fps=10`):
     - `explain_and_hold(seconds >= 1.9)` for `1x` interactive inspection beats.
     - `wait_for_js(..., capture_interval_s=0.9)` for `5x-10x` timelapse async
       waits with live HUD elapsed-time and phase updates and fatal error banner
       fast-fail.
  4. Pre-Capture Secret & Token Masking (`mask_sensitive_dom`), Stalled-Wait
     Diagnostic Frame Capture (`save_diagnostic_frame`), Per-Scenario Clip
     Staging & Stitching (`stitch_scenario_clips`), Prerequisite Pre-Flight
     Checking (`check_recording_prerequisites`), and Git-Host-Agnostic OSS Media
     Publishing (`publish_oss_media`).
"""

import argparse
import base64
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import time
import urllib.parse
import urllib.request

OVERLAY_INIT_JS = r"""
(() => {
  if (document.getElementById('cdp-demo-overlay-root')) return true;
  const root = document.createElement('div');
  root.id = 'cdp-demo-overlay-root';
  root.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:999999;overflow:hidden;';

  const style = document.createElement('style');
  style.textContent = `
    #cdp-demo-cursor {
      position: fixed;
      left: 720px;
      top: 450px;
      width: 34px;
      height: 34px;
      transform: translate(-4px, -2px);
      pointer-events: none;
      z-index: 1000003;
      filter: drop-shadow(0 4px 10px rgba(0,0,0,0.65));
      transition: transform 80ms ease;
    }
    #cdp-demo-cursor.clicking {
      transform: translate(-4px, -2px) scale(0.85);
    }
    #cdp-demo-cursor-halo {
      position: absolute;
      left: -10px;
      top: -10px;
      width: 30px;
      height: 30px;
      border-radius: 50%;
      background: rgba(250, 204, 21, 0.34);
      border: 2.2px solid rgba(245, 158, 11, 0.92);
      box-shadow: 0 0 14px rgba(250, 204, 21, 0.55);
      transition: all 80ms ease;
    }
    #cdp-demo-cursor.clicking #cdp-demo-cursor-halo {
      background: rgba(56, 189, 248, 0.55);
      border-color: #38bdf8;
      box-shadow: 0 0 20px rgba(56, 189, 248, 0.85);
    }
    .cdp-demo-ripple {
      position: fixed;
      width: 54px;
      height: 54px;
      margin-left: -27px;
      margin-top: -27px;
      border-radius: 50%;
      border: 3px solid #38bdf8;
      background: rgba(56, 189, 248, 0.28);
      box-shadow: 0 0 20px rgba(56, 189, 248, 0.75);
      pointer-events: none;
      z-index: 1000002;
      animation: cdpDemoRippleAnim 480ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    @keyframes cdpDemoRippleAnim {
      0% { transform: scale(0.28); opacity: 1; }
      100% { transform: scale(1.75); opacity: 0; }
    }
    #cdp-demo-target-box {
      position: fixed;
      left: -200px;
      top: -200px;
      width: 0;
      height: 0;
      border-radius: 8px;
      border: 2.5px solid #38bdf8;
      box-shadow: 0 0 0 5px rgba(56, 189, 248, 0.26), 0 0 18px rgba(56, 189, 248, 0.55);
      pointer-events: none;
      z-index: 1000001;
      opacity: 0;
      transition: opacity 120ms ease;
    }
    #cdp-demo-caption-hud {
      position: fixed;
      left: 50%;
      bottom: 20px;
      transform: translateX(-50%);
      min-width: 540px;
      max-width: 920px;
      padding: 13px 24px 14px;
      border-radius: 16px;
      background: rgba(10, 15, 28, 0.95);
      border: 2px solid rgba(56, 189, 248, 0.72);
      box-shadow: 0 16px 42px rgba(0, 0, 0, 0.78), 0 0 28px rgba(56, 189, 248, 0.26);
      color: #f8fafc;
      font-family: Inter, system-ui, -apple-system, sans-serif;
      pointer-events: none;
      z-index: 1000004;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    #cdp-demo-caption-hud.pos-top {
      bottom: auto;
      top: 56px;
    }
    .cdp-demo-hud-top-row {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .cdp-demo-pill {
      padding: 3px 10px;
      border-radius: 6px;
      background: rgba(56, 189, 248, 0.22);
      border: 1px solid rgba(56, 189, 248, 0.62);
      color: #7dd3fc;
      font: 700 12.5px/1.25 'JetBrains Mono', ui-monospace, monospace;
      letter-spacing: 0.02em;
      flex-shrink: 0;
    }
    .cdp-demo-title {
      font-size: 16.5px;
      font-weight: 700;
      line-height: 1.28;
      color: #ffffff;
      letter-spacing: -0.01em;
    }
    .cdp-demo-subtitle {
      font-size: 14px;
      font-weight: 500;
      line-height: 1.45;
      color: #e2e8f0;
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

  const targetBox = document.createElement('div');
  targetBox.id = 'cdp-demo-target-box';
  root.appendChild(targetBox);

  const cursor = document.createElement('div');
  cursor.id = 'cdp-demo-cursor';
  const halo = document.createElement('div');
  halo.id = 'cdp-demo-cursor-halo';
  cursor.appendChild(halo);

  const svgNs = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNs, 'svg');
  svg.setAttribute('width', '28');
  svg.setAttribute('height', '28');
  svg.setAttribute('viewBox', '0 0 28 28');
  svg.setAttribute('fill', 'none');
  svg.style.position = 'relative';

  const path = document.createElementNS(svgNs, 'path');
  path.setAttribute('d', 'M4 2L4 22L9.5 16.8L13.5 25L17 23.3L13 15.2L20.5 15.2L4 2Z');
  path.setAttribute('fill', '#0f172a');
  path.setAttribute('stroke', '#ffffff');
  path.setAttribute('stroke-width', '2.2');
  path.setAttribute('stroke-linejoin', 'round');
  svg.appendChild(path);

  const circle = document.createElementNS(svgNs, 'circle');
  circle.setAttribute('cx', '4.5');
  circle.setAttribute('cy', '3.2');
  circle.setAttribute('r', '2.2');
  circle.setAttribute('fill', '#38bdf8');
  svg.appendChild(circle);
  cursor.appendChild(svg);
  root.appendChild(cursor);

  const hud = document.createElement('div');
  hud.id = 'cdp-demo-caption-hud';
  const topRow = document.createElement('div');
  topRow.className = 'cdp-demo-hud-top-row';
  const pillSpan = document.createElement('span');
  pillSpan.className = 'cdp-demo-pill';
  pillSpan.id = 'cdp-demo-pill';
  pillSpan.textContent = 'DEMO';
  const titleSpan = document.createElement('span');
  titleSpan.className = 'cdp-demo-title';
  titleSpan.id = 'cdp-demo-title';
  titleSpan.textContent = 'Interactive Feature Walkthrough';
  topRow.appendChild(pillSpan);
  topRow.appendChild(titleSpan);

  const subDiv = document.createElement('div');
  subDiv.className = 'cdp-demo-subtitle';
  subDiv.id = 'cdp-demo-subtitle';
  subDiv.textContent = 'Watch the cursor and highlighted controls to see how each tool works.';
  hud.appendChild(topRow);
  hud.appendChild(subDiv);
  root.appendChild(hud);

  (document.body || document.documentElement).appendChild(root);

  window.__cdpDemoState = { x: 720, y: 450 };
  window.__cdpDemoSetCursor = (x, y, clicking) => {
    window.__cdpDemoState.x = x;
    window.__cdpDemoState.y = y;
    const c = document.getElementById('cdp-demo-cursor');
    if (c) {
      c.style.left = `${Math.round(x)}px`;
      c.style.top = `${Math.round(y)}px`;
      c.classList.toggle('clicking', Boolean(clicking));
    }
  };
  window.__cdpDemoPulseRipple = (x, y) => {
    const r = document.createElement('div');
    r.className = 'cdp-demo-ripple';
    r.style.left = `${Math.round(x)}px`;
    r.style.top = `${Math.round(y)}px`;
    root.appendChild(r);
    setTimeout(() => { r.remove(); }, 520);
  };
  window.__cdpDemoHighlightSelector = (selector) => {
    const box = document.getElementById('cdp-demo-target-box');
    if (!box) return;
    if (!selector) {
      box.style.opacity = '0';
      return;
    }
    const el = document.querySelector(selector);
    if (!el) {
      box.style.opacity = '0';
      return;
    }
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) {
      box.style.opacity = '0';
      return;
    }
    const pad = 4;
    box.style.left = `${Math.round(r.left - pad)}px`;
    box.style.top = `${Math.round(r.top - pad)}px`;
    box.style.width = `${Math.round(r.width + pad * 2)}px`;
    box.style.height = `${Math.round(r.height + pad * 2)}px`;
    box.style.opacity = '1';
  };
  window.__cdpDemoSetCaption = (badge, title, subtitle, position) => {
    const h = document.getElementById('cdp-demo-caption-hud');
    if (!h) return;
    if (!badge && !title && !subtitle) {
      h.style.display = 'none';
      return;
    }
    h.style.display = 'flex';
    h.classList.toggle('pos-top', position === 'top');
    const pillEl = document.getElementById('cdp-demo-pill');
    const titleEl = document.getElementById('cdp-demo-title');
    const subEl = document.getElementById('cdp-demo-subtitle');
    if (pillEl) pillEl.textContent = badge || 'STEP';
    if (titleEl) titleEl.textContent = title || '';
    if (subEl) {
      subEl.textContent = subtitle || '';
      subEl.style.display = subtitle ? 'block' : 'none';
    }
  };
  return true;
})();
"""


class MiniCDPWebSocket:
  """Minimal stdlib RFC 6455 WebSocket client for Chrome DevTools Protocol."""

  def __init__(self, sock: socket.socket, timeout: float = 30.0):
    self.sock = sock
    self.sock.settimeout(timeout)
    self._next_id = 1

  def send_text(self, text: str) -> None:
    """Sends a masked UTF-8 text frame over the CDP WebSocket."""
    payload = text.encode("utf-8")
    mask_key = os.urandom(4)
    header = bytearray([0x81])
    length = len(payload)
    if length < 126:
      header.append(0x80 | length)
    elif length < 65536:
      header.append(0x80 | 126)
      header.extend(struct.pack("!H", length))
    else:
      header.append(0x80 | 127)
      header.extend(struct.pack("!Q", length))
    header.extend(mask_key)
    masked = bytearray(payload[i] ^ mask_key[i % 4] for i in range(length))
    self.sock.sendall(header + masked)

  def _recv_exact(self, n: int) -> bytes:
    """Reads `n` bytes from the WebSocket socket."""
    buf = bytearray()
    while len(buf) < n:
      chunk = self.sock.recv(n - len(buf))
      if not chunk:
        raise ConnectionError("CDP WebSocket closed unexpectedly")
      buf.extend(chunk)
    return bytes(buf)

  def recv_text(self) -> str:
    """Receives the next text frame from the CDP WebSocket."""
    while True:
      b1, b2 = self._recv_exact(2)
      opcode = b1 & 0x0F
      masked = bool(b2 & 0x80)
      length = b2 & 0x7F
      if length == 126:
        length = struct.unpack("!H", self._recv_exact(2))[0]
      elif length == 127:
        length = struct.unpack("!Q", self._recv_exact(8))[0]
      mask_key = self._recv_exact(4) if masked else b""
      payload = self._recv_exact(length)
      if masked:
        payload = bytes(payload[i] ^ mask_key[i % 4] for i in range(length))
      if opcode == 0x8:
        raise ConnectionError("CDP WebSocket closed by peer")
      if opcode == 0x9:
        pong_mask = os.urandom(4)
        pong_masked = bytearray(
            payload[i] ^ pong_mask[i % 4] for i in range(len(payload))
        )
        pong = bytearray([0x8A, 0x80 | len(payload)]) + pong_mask + pong_masked
        self.sock.sendall(pong)
        continue
      if opcode in (0x1, 0x2):
        return payload.decode("utf-8", errors="replace")

  def call(
      self, method: str, params: dict[str, object] | None = None
  ) -> dict[str, object]:
    """Invokes a CDP RPC method and returns its result dictionary."""
    msg_id = self._next_id
    self._next_id += 1
    self.send_text(
        json.dumps({"id": msg_id, "method": method, "params": params or {}})
    )
    while True:
      raw = self.recv_text()
      data = json.loads(raw)
      if data.get("id") == msg_id:
        if "error" in data:
          raise RuntimeError(f"CDP {method} error: {data['error']}")
        return data.get("result", {})

  def close(self) -> None:
    """Closes the underlying WebSocket connection."""
    try:
      self.sock.close()
    except OSError:
      pass


def open_cdp_page_ws(
    port: int, target_id: str | None = None
) -> MiniCDPWebSocket:
  """Connects to a `page` target on `127.0.0.1:<port>`.

  Args:
    port: Chrome remote debugging port.
    target_id: Optional page target id; defaults to the first inspectable page.

  Returns:
    A connected `MiniCDPWebSocket` for the selected page.

  Raises:
    RuntimeError: If no matching page target exists or the handshake fails.
  """
  with urllib.request.urlopen(
      f"http://127.0.0.1:{port}/json/list", timeout=5.0
  ) as resp:
    targets = json.loads(resp.read().decode("utf-8"))
  ws_url = None
  for t in targets:
    if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
      if target_id is not None and t.get("id") != target_id:
        continue
      ws_url = t["webSocketDebuggerUrl"]
      break
  if not ws_url:
    raise RuntimeError(f"No inspectable page target on CDP port {port}")
  path = "/" + ws_url.split("/", 3)[-1]
  sock = socket.create_connection(("127.0.0.1", port), timeout=10.0)
  try:
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: 127.0.0.1:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(req.encode("ascii"))
    resp_buf = b""
    while b"\r\n\r\n" not in resp_buf:
      chunk = sock.recv(1024)
      if not chunk:
        raise RuntimeError("Handshake EOF from Chrome CDP")
      resp_buf += chunk
    accept_src = (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
    digest = hashlib.sha1(accept_src).digest()
    expected_accept = base64.b64encode(digest).decode("ascii")
    if expected_accept.encode("ascii") not in resp_buf:
      raise RuntimeError("Invalid Sec-WebSocket-Accept from Chrome CDP")
    return MiniCDPWebSocket(sock)
  except Exception:
    sock.close()
    raise


def find_free_port() -> int:
  """Returns an ephemeral free TCP port on `127.0.0.1`."""
  with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    return s.getsockname()[1]


def resolve_chrome_binary(preferred: str | None = None) -> str | None:
  """Resolves an executable Chrome or Chromium binary path."""
  candidates: list[str] = []
  if preferred:
    candidates.append(preferred)
  for b in (
      "/usr/bin/google-chrome",
      "google-chrome",
      "chromium",
      "chromium-browser",
  ):
    if b not in candidates:
      candidates.append(b)
  for cand in candidates:
    resolved = shutil.which(cand)
    if resolved:
      return resolved
    if os.path.isfile(cand) and os.access(cand, os.X_OK):
      return cand
  return None


def check_recording_prerequisites(
    mode: str, target_url: str, adapter_tier: str = "auto"
) -> dict[str, object]:
  """Verifies live localhost reachability and required browser/encoding binaries."""
  parsed = urllib.parse.urlparse(target_url)
  scheme = (parsed.scheme or "").lower()
  if scheme not in ("http", "https") or not parsed.hostname:
    return {
        "ok": False,
        "server_reachable": False,
        "missing_binaries": [],
        "install_commands": [],
        "server_start_hint": (
            f"Rejected synthetic URL '{target_url}'. Live server (http:// or"
            " https://) required."
        ),
    }
  host = parsed.hostname
  port = parsed.port or (443 if scheme == "https" else 80)
  server_reachable = False
  try:
    with socket.create_connection((host, port), timeout=1.5):
      server_reachable = True
  except OSError:
    server_reachable = False

  missing_binaries: list[str] = []
  install_commands: list[str] = []
  chrome_exists = resolve_chrome_binary() is not None
  if not chrome_exists:
    missing_binaries.append("google-chrome / playwright-chromium")
    install_commands.append("npx playwright install chromium")

  if mode == "screencast":
    if not shutil.which("ffmpeg"):
      missing_binaries.append("ffmpeg")
      install_commands.append(
          "sudo apt-get update && sudo apt-get install -y ffmpeg"
      )
    if adapter_tier == "oss" and not shutil.which("gifsicle"):
      missing_binaries.append("gifsicle")
      install_commands.append("sudo apt-get install -y gifsicle")

  server_hint = ""
  if not server_reachable:
    server_hint = (
        f"Start local application server listening on {host}:{port}"
        " (e.g., ./run.sh or npm run dev)"
    )
  return {
      "ok": server_reachable and not missing_binaries,
      "server_reachable": server_reachable,
      "missing_binaries": missing_binaries,
      "install_commands": install_commands,
      "server_start_hint": server_hint,
  }


class CDPRecorder:
  """Records live application interactions over CDP with TrustedTypes-safe overlays and variable-speed timelapse."""

  def __init__(
      self,
      name: str,
      out_dir: str,
      scratch_dir: str | None = None,
      width: int = 1440,
      height: int = 900,
      fps: int = 10,
      min_hold_sec: float = 1.9,
      allow_prototype_harness: bool = False,
      chrome_bin: str = "/usr/bin/google-chrome",
      attach_port: int | None = None,
  ):
    self.name = name
    self.out_dir = os.path.abspath(out_dir)
    os.makedirs(self.out_dir, exist_ok=True)
    base_scratch = scratch_dir or os.path.join(
        self.out_dir, "scratch", "frames"
    )
    self.frame_dir = os.path.join(base_scratch, name)
    if os.path.exists(self.frame_dir):
      shutil.rmtree(self.frame_dir)
    os.makedirs(self.frame_dir, exist_ok=True)
    self.width = width
    self.height = height
    self.fps = fps
    self.min_hold_sec = min_hold_sec
    self.allow_prototype_harness = allow_prototype_harness
    self.frame_idx = 0
    self.attach_port = attach_port
    self.proc: subprocess.Popen[bytes] | None = None
    self.ws: MiniCDPWebSocket | None = None
    self.cur_x = width / 2.0
    self.cur_y = height / 2.0
    if attach_port is not None:
      self.port = attach_port
    else:
      resolved_chrome = resolve_chrome_binary(chrome_bin)
      if not resolved_chrome:
        raise FileNotFoundError(
            f"No Chrome or Chromium binary found (checked {chrome_bin!r} and"
            " PATH)"
        )
      self.port = find_free_port()
      self.proc = subprocess.Popen(
          [
              resolved_chrome,
              "--headless=new",
              "--no-sandbox",
              "--disable-gpu",
              "--disable-dev-shm-usage",
              "--password-store=basic",
              f"--remote-debugging-port={self.port}",
              f"--window-size={width},{height}",
              "about:blank",
          ],
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
      )
    try:
      self._connect()
    except Exception:
      self.close()
      raise

  def _connect(self) -> None:
    """Connects the WebSocket to the Chrome CDP page target and enables domains."""
    last_err = None
    for _ in range(60):
      try:
        self.ws = open_cdp_page_ws(self.port)
        break
      except Exception as e:  # pylint: disable=broad-except
        last_err = e
        time.sleep(0.1)
    if self.ws is None:
      raise RuntimeError(f"Failed to connect to headless Chrome: {last_err}")
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

  def call(
      self, method: str, params: dict[str, object] | None = None
  ) -> dict[str, object]:
    """Invokes a CDP command on the active page session."""
    assert self.ws is not None
    return self.ws.call(method, params or {})

  def eval_js(self, expr: str):
    """Evaluates a JavaScript expression in the page and returns its value."""
    res = self.call(
        "Runtime.evaluate",
        {"expression": expr, "returnByValue": True, "awaitPromise": True},
    )
    result_dict = res.get("result")
    exc = res.get("exceptionDetails") or (
        result_dict.get("exceptionDetails")
        if isinstance(result_dict, dict)
        else None
    )
    if isinstance(exc, dict) and exc:
      exc_obj = exc.get("exception")
      desc = (
          exc_obj.get("description")
          if isinstance(exc_obj, dict)
          else exc.get("text") or str(exc)
      )
      raise RuntimeError(f"JavaScript evaluation failed: {desc}")
    return result_dict.get("value") if isinstance(result_dict, dict) else None

  def ensure_overlay(self) -> None:
    """Initializes the TrustedTypes-safe DOM overlay if not already mounted."""
    self.eval_js(OVERLAY_INIT_JS)
    self.eval_js(
        f"window.__cdpDemoSetCursor({self.cur_x:.1f}, {self.cur_y:.1f}, false);"
    )

  def mask_sensitive_dom(self, extra_selectors: list[str] | None = None) -> int:
    """Masks password/token DOM inputs and scrubs sensitive URL query parameters before capture."""
    self.ensure_overlay()
    selectors = [
        'input[type="password"]',
        "[data-secret]",
        '[name*="token" i]',
        '[name*="secret" i]',
        '[name*="key" i]',
        '[name*="password" i]',
    ]
    if extra_selectors:
      selectors.extend(extra_selectors)
    combined = ", ".join(selectors)
    count = self.eval_js(f"""
      (() => {{
        let masked = 0;
        const nodes = document.querySelectorAll({json.dumps(combined)});
        for (const el of nodes) {{
          el.classList.add('cdp-demo-masked-secret');
          if ((el.tagName === 'INPUT' && el.type !== 'password') || el.tagName === 'TEXTAREA') {{
            el.setAttribute('data-masked-by-cdp', 'true');
          }}
          masked++;
        }}
        try {{
          const url = new URL(window.location.href);
          let mutated = false;
          for (const k of Array.from(url.searchParams.keys())) {{
            if (/(token|key|secret|password|auth|session)/i.test(k)) {{
              url.searchParams.set(k, 'REDACTED');
              mutated = true;
            }}
          }}
          if (url.hash && /(token|key|secret|password|auth|session)=/i.test(url.hash)) {{
            url.hash = url.hash.replace(
                /((?:token|key|secret|password|auth|session)[^=&]*)=([^&]*)/gi,
                '$1=REDACTED'
            );
            mutated = true;
          }}
          if (mutated && window.history && window.history.replaceState) {{
            window.history.replaceState(null, '', url.toString());
          }}
        }} catch (_e) {{}}
        return masked;
      }})()
    """)
    return int(count or 0)

  def set_caption(
      self,
      badge: str,
      title: str,
      subtitle: str = "",
      position: str = "bottom",
  ) -> None:
    """Sets the two-line explanatory overlay card (`badge` + `title` + `subtitle`)."""
    self.ensure_overlay()
    self.eval_js(
        f"window.__cdpDemoSetCaption({json.dumps(badge)}, {json.dumps(title)},"
        f" {json.dumps(subtitle)}, {json.dumps(position)});"
    )

  def highlight(self, selector: str | None = None) -> None:
    """Draws or clears a glowing spotlight ring around a target CSS selector."""
    self.ensure_overlay()
    self.eval_js(
        f"window.__cdpDemoHighlightSelector({json.dumps(selector or '')});"
    )

  def explain_and_hold(
      self,
      badge: str,
      title: str,
      subtitle: str,
      seconds: float = 1.9,
      highlight_selector: str | None = None,
      position: str = "bottom",
  ) -> None:
    """Updates the two-line explanatory overlay, optionally highlights a control, and holds at 1x."""
    self.set_caption(badge, title, subtitle, position=position)
    if highlight_selector is not None:
      self.highlight(highlight_selector)
    self.hold(max(self.min_hold_sec, seconds))

  def save_diagnostic_frame(
      self, reason: str, out_path: str | None = None
  ) -> str:
    """Captures a diagnostic PNG frame with an ERROR / TIMEOUT HUD banner on failure."""
    target = out_path or os.path.join(
        self.out_dir, f"{self.name}_diagnostic.png"
    )
    self.set_caption("ERROR / TIMEOUT", f"Recording Halted: {reason}", target)
    shot = self.call("Page.captureScreenshot", {"format": "png"})
    with open(target, "wb") as f:
      f.write(base64.b64decode(shot["data"]))
    return target

  def wait_for_js(
      self,
      predicate_js: str,
      timeout_s: float = 300.0,
      capture_interval_s: float = 0.9,
      badge: str = "TIMELAPSE",
      title: str = "Waiting for async operation",
      phase_expr_js: str | None = None,
      fatal_error_selector: str | None = None,
      position: str = "bottom",
  ) -> dict[str, object]:
    """Polls `predicate_js` at `capture_interval_s` (`0.5s-1.0s`), snapping 1 frame per interval for 4x-10x timelapse."""
    interval = max(0.5, min(1.0, float(capture_interval_s)))
    speedup = round(interval * self.fps, 1)
    start_ts = time.monotonic()
    frames_captured = 0
    last_phase = "RUNNING"
    while True:
      elapsed = time.monotonic() - start_ts
      if fatal_error_selector:
        err_text = self.eval_js(f"""
          (() => {{
            const el = document.querySelector({json.dumps(fatal_error_selector)});
            if (!el) return null;
            const r = el.getBoundingClientRect();
            if (r.width === 0 && r.height === 0) return null;
            return (el.textContent || 'Fatal error banner detected').trim();
          }})()
        """)
        if err_text:
          diag_path = self.save_diagnostic_frame(f"Fatal UI error: {err_text}")
          raise RuntimeError(
              f"Fatal error selector '{fatal_error_selector}' matched"
              f" ('{err_text}'); diagnostic saved to {diag_path}"
          )
      if phase_expr_js:
        phase_val = self.eval_js(phase_expr_js)
        if phase_val:
          last_phase = str(phase_val)
      subtitle = (
          f"Elapsed: {elapsed:.1f}s · Phase: {last_phase} (~{speedup:g}x"
          " timelapse)"
      )
      self.set_caption(badge, title, subtitle, position=position)
      self.snap_frame(repeat=1)
      frames_captured += 1
      clean_pred = predicate_js.strip().rstrip(";").strip()
      done = self.eval_js(f"Boolean(({clean_pred}))")
      if done:
        return {
            "completed": True,
            "elapsed_s": round(elapsed, 2),
            "frames_captured": frames_captured,
            "last_phase": last_phase,
        }
      if elapsed >= timeout_s:
        diag_path = self.save_diagnostic_frame(
            f"Timed out after {timeout_s:.0f}s ({last_phase})"
        )
        raise RuntimeError(
            f"wait_for_js timed out after {timeout_s:.1f}s; diagnostic saved"
            f" to {diag_path}"
        )
      time.sleep(interval)

  def snap_frame(self, repeat: int = 1) -> str:
    """Captures a PNG frame and writes it `repeat` times to the frame sequence."""
    shot = self.call("Page.captureScreenshot", {"format": "png"})
    png_bytes = base64.b64decode(str(shot["data"]))
    last_path = ""
    for _ in range(max(1, repeat)):
      last_path = os.path.join(
          self.frame_dir, f"frame_{self.frame_idx:04d}.png"
      )
      with open(last_path, "wb") as f:
        f.write(png_bytes)
      self.frame_idx += 1
    return last_path

  def save_clean_screenshot(self, out_path: str) -> str:
    """Captures a clean PNG screenshot with the cursor/HUD overlay temporarily hidden."""
    self.mask_sensitive_dom()
    self.eval_js(
        "(() => { const el = document.getElementById('cdp-demo-overlay-root');"
        " if (el) el.style.display = 'none'; })()"
    )
    shot = self.call("Page.captureScreenshot", {"format": "png"})
    with open(out_path, "wb") as f:
      f.write(base64.b64decode(str(shot["data"])))
    self.eval_js(
        "(() => { const el = document.getElementById('cdp-demo-overlay-root');"
        " if (el) el.style.display = ''; })()"
    )
    return out_path

  def hold(self, seconds: float) -> None:
    """Holds the current frame for `seconds` at `self.fps`."""
    count = max(1, int(round(seconds * self.fps)))
    self.snap_frame(repeat=count)

  def move_to(self, x: float, y: float, steps: int = 5) -> None:
    """Smoothly interpolates the overlay cursor to `(x, y)` over `steps` frames."""
    self.ensure_overlay()
    x0, y0 = self.cur_x, self.cur_y
    for i in range(1, max(1, steps) + 1):
      t = i / max(1, steps)
      ease = 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
      cx = x0 + (x - x0) * ease
      cy = y0 + (y - y0) * ease
      self.cur_x, self.cur_y = cx, cy
      self.eval_js(f"window.__cdpDemoSetCursor({cx:.1f}, {cy:.1f}, false);")
      self.snap_frame(repeat=1)

  def get_center(self, selector: str) -> dict[str, float] | None:
    """Returns the viewport center `{x, y}` of `selector`, or `None` if hidden."""
    return self.eval_js(f"""
      (() => {{
        const el = document.querySelector({json.dumps(selector)});
        if (!el) return null;
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return null;
        return {{ x: r.left + r.width / 2, y: r.top + r.height / 2 }};
      }})()
    """)

  def move_to_selector(
      self, selector: str, steps: int = 5, highlight_target: bool = True
  ) -> dict[str, float] | None:
    """Moves the cursor to the center of `selector` and optionally highlights it."""
    if highlight_target:
      self.highlight(selector)
    pt = self.get_center(selector)
    if pt:
      self.move_to(pt["x"], pt["y"], steps=steps)
    return pt

  def click_at(
      self,
      x: float,
      y: float,
      real_click_selector: str | None = None,
      steps: int = 5,
      hold_after: float = 0.0,
  ) -> None:
    """Moves to `(x, y)`, renders a click ripple, and dispatches a click."""
    if real_click_selector:
      self.highlight(real_click_selector)
    self.move_to(x, y, steps=steps)
    self.eval_js(
        f"window.__cdpDemoSetCursor({x:.1f}, {y:.1f}, true);"
        f" window.__cdpDemoPulseRipple({x:.1f}, {y:.1f});"
    )
    if real_click_selector:
      self.eval_js(f"""
        (() => {{
          const el = document.querySelector({json.dumps(real_click_selector)});
          if (el) el.click();
        }})()
      """)
    else:
      self.call(
          "Input.dispatchMouseEvent",
          {
              "type": "mousePressed",
              "x": x,
              "y": y,
              "button": "left",
              "clickCount": 1,
          },
      )
      self.call(
          "Input.dispatchMouseEvent",
          {
              "type": "mouseReleased",
              "x": x,
              "y": y,
              "button": "left",
              "clickCount": 1,
          },
      )
    self.snap_frame(repeat=2)
    self.eval_js(f"window.__cdpDemoSetCursor({x:.1f}, {y:.1f}, false);")
    self.snap_frame(repeat=2)
    if hold_after > 0:
      self.hold(hold_after)

  def click_selector(
      self, selector: str, steps: int = 5, hold_after: float = 0.0
  ) -> dict[str, float] | None:
    """Moves to `selector`, highlights it, and clicks it."""
    pt = self.get_center(selector)
    if pt:
      self.click_at(
          pt["x"],
          pt["y"],
          real_click_selector=selector,
          steps=steps,
          hold_after=hold_after,
      )
    return pt

  def drag(
      self,
      x0: float,
      y0: float,
      x1: float,
      y1: float,
      steps: int = 7,
      modifiers: int = 0,
      hold_after: float = 0.0,
  ) -> None:
    """Performs a visible mouse drag from (x0, y0) to (x1, y1) via CDP mouse events."""
    self.move_to(x0, y0, steps=4)
    self.eval_js(
        f"window.__cdpDemoSetCursor({x0:.1f}, {y0:.1f}, true);"
        f" window.__cdpDemoPulseRipple({x0:.1f}, {y0:.1f});"
    )
    self.call(
        "Input.dispatchMouseEvent",
        {
            "type": "mousePressed",
            "x": x0,
            "y": y0,
            "button": "left",
            "buttons": 1,
            "clickCount": 1,
            "modifiers": modifiers,
        },
    )
    self.snap_frame(repeat=1)
    for i in range(1, max(1, steps) + 1):
      t = i / max(1, steps)
      ease = 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
      cx = x0 + (x1 - x0) * ease
      cy = y0 + (y1 - y0) * ease
      self.cur_x, self.cur_y = cx, cy
      self.call(
          "Input.dispatchMouseEvent",
          {
              "type": "mouseMoved",
              "x": cx,
              "y": cy,
              "button": "left",
              "buttons": 1,
              "modifiers": modifiers,
          },
      )
      self.eval_js(f"window.__cdpDemoSetCursor({cx:.1f}, {cy:.1f}, true);")
      self.snap_frame(repeat=1)
    self.call(
        "Input.dispatchMouseEvent",
        {
            "type": "mouseReleased",
            "x": x1,
            "y": y1,
            "button": "left",
            "buttons": 0,
            "clickCount": 1,
            "modifiers": modifiers,
        },
    )
    self.eval_js(f"window.__cdpDemoSetCursor({x1:.1f}, {y1:.1f}, false);")
    self.snap_frame(repeat=2)
    if hold_after > 0:
      self.hold(hold_after)

  def navigate(self, url: str, wait_sec: float = 1.1) -> None:
    """Navigates to a live `http://` or `https://` URL, mounts overlays, and masks secrets."""
    parsed = urllib.parse.urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https") and not self.allow_prototype_harness:
      raise ValueError(
          f"Refusing to record simulated/static URL '{url}'. Screen recordings "
          "of implemented functionality MUST load the live running application "
          "server (http:// or https://) in a real headless browser."
      )
    self.call("Page.navigate", {"url": url})
    time.sleep(wait_sec)
    self.ensure_overlay()
    self.mask_sensitive_dom()

  def encode_mp4(self, out_mp4: str | None = None) -> str:
    """Encodes the captured PNG frame sequence into an H.264 `.mp4` video."""
    target = out_mp4 or os.path.join(self.out_dir, f"{self.name}.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-framerate",
            str(self.fps),
            "-i",
            os.path.join(self.frame_dir, "frame_%04d.png"),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-movflags",
            "+faststart",
            target,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return target

  def encode_webm(self, out_webm: str | None = None) -> str:
    """Encodes the captured PNG frame sequence into a VP9 `.webm` video."""
    target = out_webm or os.path.join(self.out_dir, f"{self.name}.webm")
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-framerate",
            str(self.fps),
            "-i",
            os.path.join(self.frame_dir, "frame_%04d.png"),
            "-an",
            "-c:v",
            "libvpx-vp9",
            "-deadline",
            "realtime",
            "-cpu-used",
            "6",
            "-row-mt",
            "1",
            "-b:v",
            "2M",
            "-pix_fmt",
            "yuv420p",
            target,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return target

  def encode_gif(
      self, out_gif: str | None = None, width: int = 1080, fps: int = 10
  ) -> str:
    """Encodes the captured PNG frame sequence into a 2-pass Lanczos `.gif`."""
    target = out_gif or os.path.join(self.out_dir, f"{self.name}.gif")
    vf = (
        f"scale={width}:-1:flags=lanczos,split[s0][s1];"
        "[s0]palettegen=max_colors=128:stats_mode=diff[p];"
        "[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            os.path.join(self.frame_dir, "frame_%04d.png"),
            "-vf",
            vf,
            "-loop",
            "0",
            target,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return target

  def close(self) -> None:
    """Closes the CDP WebSocket and terminates any spawned Chrome process."""
    if self.ws:
      self.ws.close()
      self.ws = None
    if self.proc is not None:
      try:
        self.proc.kill()
      except OSError:
        pass
      try:
        self.proc.wait(timeout=5.0)
      except (OSError, subprocess.TimeoutExpired):
        pass
      self.proc = None


AttachedCDPRecorder = CDPRecorder


def stitch_scenario_clips(
    clip_paths: list[str],
    out_mp4: str,
    out_webm: str | None = None,
    out_gif: str | None = None,
    gif_width: int = 1080,
    fps: int = 10,
) -> dict[str, str]:
  """Concatenates per-scenario `.mp4` clips into a combined `.mp4`, `.webm`, and 2-pass Lanczos `.gif`."""
  if not clip_paths:
    raise ValueError("clip_paths must contain at least one scenario clip")
  out_dir = os.path.dirname(os.path.abspath(out_mp4))
  os.makedirs(out_dir, exist_ok=True)
  manifest_path = os.path.join(out_dir, "concat_list.txt")
  try:
    with open(manifest_path, "w", encoding="utf-8") as f:
      for p in clip_paths:
        escaped = os.path.abspath(p).replace("'", "'\\''")
        f.write(f"file '{escaped}'\n")
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            manifest_path,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-movflags",
            "+faststart",
            out_mp4,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
  finally:
    if os.path.exists(manifest_path):
      try:
        os.remove(manifest_path)
      except OSError:
        pass
  result = {"mp4": out_mp4}
  if out_webm:
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-i",
            out_mp4,
            "-c:v",
            "libvpx-vp9",
            "-deadline",
            "realtime",
            "-cpu-used",
            "6",
            "-row-mt",
            "1",
            "-b:v",
            "2M",
            "-pix_fmt",
            "yuv420p",
            out_webm,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    result["webm"] = out_webm
  if out_gif:
    vf = (
        f"fps={fps},scale={gif_width}:-1:flags=lanczos,split[s0][s1];"
        "[s0]palettegen=max_colors=128:stats_mode=diff[p];"
        "[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-i",
            out_mp4,
            "-vf",
            vf,
            "-loop",
            "0",
            out_gif,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    result["gif"] = out_gif
  return result


def publish_oss_media(
    file_paths: list[str],
    track_recordings_dir: str,
    git_host_mode: str = "local",
    release_tag: str = "armature-media",
) -> dict[str, object]:
  """Copies media into `<track_dir>/recordings/` and optionally uploads via Git-host CLI (`gh`, `tea`, `glab`)."""
  os.makedirs(track_recordings_dir, exist_ok=True)
  staged_paths: list[str] = []
  for src in file_paths:
    if os.path.exists(src):
      dst = os.path.join(track_recordings_dir, os.path.basename(src))
      if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copy2(src, dst)
      if dst.endswith(".gif") and shutil.which("gifsicle"):
        subprocess.run(
            ["gifsicle", "-O3", "--lossy=80", "-b", dst],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
      staged_paths.append(dst)

  uploaded_urls: list[str] = []
  if not staged_paths:
    return {
        "local_paths": staged_paths,
        "git_host_mode": git_host_mode,
        "uploaded": uploaded_urls,
    }
  if git_host_mode == "github" and shutil.which("gh"):
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            release_tag,
            "--prerelease",
            "--title",
            "Armature Review Media",
            "--notes",
            "Automated review recordings",
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    res = subprocess.run(
        ["gh", "release", "upload", release_tag, "--clobber"] + staged_paths,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode == 0:
      uploaded_urls.extend(staged_paths)
  elif git_host_mode == "gitea" and shutil.which("tea"):
    for p in staged_paths:
      res = subprocess.run(
          ["tea", "release", "asset", "create", release_tag, p],
          capture_output=True,
          text=True,
          check=False,
      )
      if res.returncode == 0:
        uploaded_urls.append(p)
  elif git_host_mode == "gitlab" and shutil.which("glab"):
    res = subprocess.run(
        ["glab", "release", "upload", release_tag] + staged_paths,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode == 0:
      uploaded_urls.extend(staged_paths)

  return {
      "local_paths": staged_paths,
      "git_host_mode": git_host_mode,
      "uploaded": uploaded_urls,
  }


def run_spec_file(spec_path: str) -> dict[str, object]:
  """Executes a declarative JSON recording recipe and returns output paths."""
  with open(spec_path, "r", encoding="utf-8") as f:
    spec = json.load(f)
  if "reel" in spec:
    # v2 instructional reels (ADR 0020) live in a sibling module; imported
    # lazily to avoid a circular import.
    import instructional_reel  # pylint: disable=g-import-not-at-top

    return instructional_reel.run_reel(spec)
  out_dir = os.path.abspath(spec.get("out_dir", "/tmp/cdp_screencasts"))
  os.makedirs(out_dir, exist_ok=True)
  name = spec["name"]
  fps = int(spec.get("fps", 10))
  gif_width = int(spec.get("gif_width", 1080))
  scenario_clips = spec.get("scenario_clips") or []
  steps = spec.get("steps") or []
  if scenario_clips and not steps:
    stitched = stitch_scenario_clips(
        clip_paths=list(scenario_clips),
        out_mp4=os.path.join(out_dir, f"{name}.mp4"),
        out_webm=os.path.join(out_dir, f"{name}.webm"),
        out_gif=os.path.join(out_dir, f"{name}.gif"),
        gif_width=gif_width,
        fps=int(spec.get("gif_fps", fps)),
    )
    return {
        "name": name,
        "mp4": stitched["mp4"],
        "webm": stitched["webm"],
        "gif": stitched["gif"],
    }
  rec = CDPRecorder(
      name=name,
      out_dir=out_dir,
      scratch_dir=spec.get("scratch_dir"),
      width=int(spec.get("width", 1440)),
      height=int(spec.get("height", 900)),
      fps=fps,
      min_hold_sec=float(spec.get("min_hold_sec", 1.9)),
      attach_port=spec.get("attach_port"),
  )
  try:
    for step in spec.get("steps", []):
      action = step.get("action")
      if action == "navigate":
        rec.navigate(step["url"], wait_sec=float(step.get("wait_sec", 1.1)))
      elif action == "mask_secrets":
        rec.mask_sensitive_dom(step.get("extra_selectors"))
      elif action == "caption":
        rec.explain_and_hold(
            badge=step.get("badge", "STEP"),
            title=step.get("title", step.get("text", "")),
            subtitle=step.get("subtitle", ""),
            seconds=float(step.get("hold_seconds", 1.9)),
            highlight_selector=step.get("highlight_selector"),
            position=step.get("position", "bottom"),
        )
      elif action == "wait_for_js":
        rec.wait_for_js(
            predicate_js=step["predicate_js"],
            timeout_s=float(step.get("timeout_s", 300.0)),
            capture_interval_s=float(step.get("capture_interval_s", 0.9)),
            badge=step.get("badge", "TIMELAPSE"),
            title=step.get("title", "Waiting for async operation"),
            phase_expr_js=step.get("phase_expr_js"),
            fatal_error_selector=step.get("fatal_error_selector"),
            position=step.get("position", "bottom"),
        )
      elif action == "highlight":
        rec.highlight(step.get("selector"))
      elif action == "eval":
        rec.eval_js(step["expression"])
      elif action == "hold":
        rec.hold(float(step.get("seconds", 1.9)))
      elif action == "move":
        if "selector" in step:
          rec.move_to_selector(
              step["selector"],
              steps=int(step.get("steps", 5)),
              highlight_target=bool(step.get("highlight", True)),
          )
        else:
          rec.move_to(
              float(step["x"]),
              float(step["y"]),
              steps=int(step.get("steps", 5)),
          )
      elif action == "click":
        if "selector" in step:
          rec.click_selector(
              step["selector"],
              steps=int(step.get("steps", 5)),
              hold_after=float(step.get("hold_after", 1.9)),
          )
        else:
          rec.click_at(
              float(step["x"]),
              float(step["y"]),
              real_click_selector=step.get("real_click_selector"),
              steps=int(step.get("steps", 5)),
              hold_after=float(step.get("hold_after", 1.9)),
          )
      elif action == "drag":
        rec.drag(
            float(step["x0"]),
            float(step["y0"]),
            float(step["x1"]),
            float(step["y1"]),
            steps=int(step.get("steps", 7)),
            modifiers=int(step.get("modifiers", 0)),
            hold_after=float(step.get("hold_after", 1.9)),
        )
      elif action == "screenshot":
        rec.save_clean_screenshot(step["path"])
    mp4_path = rec.encode_mp4()
    webm_path = rec.encode_webm()
    gif_path = rec.encode_gif(
        width=int(spec.get("gif_width", 1080)),
        fps=int(spec.get("gif_fps", 10)),
    )
    return {
        "name": spec["name"],
        "mp4": mp4_path,
        "webm": webm_path,
        "gif": gif_path,
    }
  finally:
    rec.close()


def main() -> None:
  """CLI entry point for declarative JSON screencast recording."""
  parser = argparse.ArgumentParser(
      description=(
          "Record headless Chrome UI screencasts with TrustedTypes-safe"
          " overlays and variable-speed timelapse."
      )
  )
  parser.add_argument(
      "--spec", required=True, help="Path to JSON recording spec file."
  )
  args = parser.parse_args()
  res = run_spec_file(args.spec)
  print(json.dumps(res, indent=2))


if __name__ == "__main__":
  main()
