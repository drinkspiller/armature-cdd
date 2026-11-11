#!/usr/bin/env python3
"""Flow Spec Altitude & Design Token Drift Validator (ADR 0021).

Validates behavioral UI Flow Specs (User Flows + UI Stack Edge Cases) against
the Three-Altitude Rule and checks unified VCS diffs against DESIGN.md tokens.
Zero third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

HEX_RE = re.compile(
    r"(?<![&\w/])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|(?=[0-9a-fA-F]{4}\b)(?=.*[a-fA-F])[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b"
)
PX_REM_RE = re.compile(r"\b\d+(?:\.\d+)?(?:px|rem)\b", re.IGNORECASE)
_HEX_RE = HEX_RE
_PX_REM_RE = PX_REM_RE
_CSS_PROP_RE = re.compile(
    r"\b(?:border-radius|background-color|font-size|padding|margin|rgba?)\s*[:(]",
    re.IGNORECASE,
)
_REQ_ID_RE = re.compile(r"\b(?:REQ-[A-Z0-9-]+|R\d+)\b")
_UI_EXTS = (
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".html",
    ".tsx",
    ".jsx",
    ".vue",
    ".ts",
    ".js",
)
_UI_STACK_STATES = ("empty", "loading", "partial", "error")
_NON_COLOR_STRIP_RE = re.compile(
    r"//.*$|/\*.*?\*/|(?:href|xlink:href|src)\s*=\s*['\"]#[^'\"]*['\"]|"
    r"url\(\s*['\"]?#[^)'\"]*['\"]?\s*\)|"
    r"querySelector(?:All)?\(\s*['\"][^'\"]*#[A-Za-z0-9_-]+[^'\"]*['\"]\s*\)",
    re.IGNORECASE,
)


def _extract_section(text: str, heading_pattern: str) -> str:
  """Extracts body under the first matching level-2 Markdown heading."""
  lines = text.splitlines()
  in_section = False
  captured: list[str] = []
  header_re = re.compile(
      rf"^##\s+(?:\d+(?:\.\d+)*\.?\s+)?{heading_pattern}\b", re.IGNORECASE
  )
  for line in lines:
    if re.match(r"^##\s+", line):
      if header_re.match(line):
        in_section = True
        continue
      if in_section:
        break
    elif in_section:
      captured.append(line)
  return "\n".join(captured)


def _check_altitude_line(line: str, line_no: int) -> list[dict[str, Any]]:
  """Checks a single behavioral flow line for visual/pixel leaks."""
  findings: list[dict[str, Any]] = []
  for regex, label in (
      (_HEX_RE, "hex color literal"),
      (_PX_REM_RE, "pixel/rem dimension"),
      (_CSS_PROP_RE, "CSS styling property"),
  ):
    for match in regex.finditer(line):
      findings.append({
          "severity": "ERROR",
          "code": "ALTITUDE_LEAK",
          "line": line_no,
          "message": (
              f"Behavioral flow line contains {label} '{match.group(0)}'; "
              "move visual styling to DESIGN.md or plan.md."
          ),
      })
  return findings


def _split_flow_steps(flows_body: str) -> list[tuple[str, str]]:
  """Splits a User Flows body into individual step or flow blocks."""
  lines = flows_body.splitlines()
  has_step_headings = any(
      re.match(r"^#{3,4}\s+(?:Step|Flow)\s+\S", ln.strip(), re.IGNORECASE)
      for ln in lines
  )
  if has_step_headings:
    step_re = re.compile(r"^#{3,4}\s+(?:Step|Flow)\s+\S.*", re.IGNORECASE)
    strip_match = True
  elif any(re.match(r"^\d+\.\s+", ln) for ln in lines):
    step_re = re.compile(r"^\d+\.\s+.*")
    strip_match = False
  else:
    step_re = re.compile(r"^-\s+\*\*(?:Flow|Step)\b.*", re.IGNORECASE)
    strip_match = False
  blocks: list[tuple[str, list[str]]] = []
  for line in lines:
    target = line.strip() if strip_match else line
    if step_re.match(target):
      blocks.append((line.strip(), [line]))
    elif blocks:
      blocks[-1][1].append(line)
  return [(title, "\n".join(lines)) for title, lines in blocks]


def _check_step_4q(title: str, block: str) -> list[dict[str, Any]]:
  """Verifies Want / See / Do / Happens coverage on a single flow step."""
  checks = {
      "Want": re.compile(
          r"\b(?:what\s+they\s+want|want)[*_`)]*\s*:", re.IGNORECASE
      ),
      "See": re.compile(
          r"\b(?:what\s+they\s+see|see)[*_`)]*\s*:", re.IGNORECASE
      ),
      "Do": re.compile(r"\b(?:what\s+they\s+do|do)[*_`)]*\s*:", re.IGNORECASE),
      "Happens": re.compile(
          r"\b(?:what\s+happens|happens)[*_`)]*\s*:", re.IGNORECASE
      ),
  }
  missing = [name for name, pat in checks.items() if not pat.search(block)]
  if not missing:
    return []
  return [{
      "severity": "ERROR",
      "code": "INCOMPLETE_FLOW_STEP",
      "message": (
          f"Flow step '{title}' is missing 4-question field(s):"
          f" {', '.join(missing)}."
      ),
  }]


def _check_coverage(text: str, flows_body: str) -> list[dict[str, Any]]:
  """Validates Covers: IDs against ## Requirements when both exist."""
  req_body = _extract_section(text, r"Requirements")
  declared = set(_REQ_ID_RE.findall(req_body))
  covers_matches = re.findall(
      r"(?:^|\*\*|-)\s*\*?\*?Covers[*_`]*\s*:\s*(.+)",
      flows_body,
      re.MULTILINE | re.IGNORECASE,
  )
  req_ids: list[str] = []
  for raw in covers_matches:
    req_ids.extend(_REQ_ID_RE.findall(raw))
  if not covers_matches or not req_ids:
    return [{
        "severity": "WARNING",
        "code": "MISSING_COVERS",
        "message": "Flow section has no 'Covers: R#' traceability IDs.",
    }]
  findings: list[dict[str, Any]] = []
  if declared:
    for req_id in req_ids:
      if req_id not in declared:
        findings.append({
            "severity": "ERROR",
            "code": "UNKNOWN_COVERAGE_ID",
            "message": (
                f"Flow references '{req_id}' which is absent from ##"
                " Requirements."
            ),
        })
  return findings


def _check_ui_stack(text: str) -> list[dict[str, Any]]:
  """Checks Edge Cases / UI Stack section for Empty, Loading, Partial, Error."""
  edge_body = _extract_section(
      text, r"(?:Edge Cases(?:\s*\([^)]*\))?|UI Stack)"
  )
  if not edge_body.strip():
    return [{
        "severity": "WARNING",
        "code": "MISSING_UI_STACK_STATE",
        "message": (
            "No ## Edge Cases / UI Stack section found for UI flow states"
            " (Empty, Loading, Partial, Error)."
        ),
    }]
  lower = edge_body.lower()
  findings: list[dict[str, Any]] = []
  for state in _UI_STACK_STATES:
    aliases = (state, "blank") if state == "empty" else (state,)
    if not any(re.search(rf"\b{a}\b", lower) for a in aliases):
      findings.append({
          "severity": "WARNING",
          "code": "MISSING_UI_STACK_STATE",
          "message": (
              f"UI Stack state '{state.title()}' not covered in ## Edge Cases"
              " (add row or mark N/A)."
          ),
      })
  return findings


def lint_flow_spec_text(
    text: str, require_flows: bool = False
) -> dict[str, Any]:
  """Lints a specification Markdown document for Flow Spec and Altitude compliance."""
  flows_body = _extract_section(text, r"User Flows?")
  errors: list[dict[str, Any]] = []
  warnings: list[dict[str, Any]] = []

  if not flows_body.strip():
    if require_flows:
      errors.append({
          "severity": "ERROR",
          "code": "MISSING_USER_FLOWS",
          "message": "UI track requires a ## User Flows section.",
      })
    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}

  all_lines = text.splitlines()
  in_flows = False
  flows_hdr_re = re.compile(
      r"^##\s+(?:\d+(?:\.\d+)*\.?\s+)?User Flows?\b", re.IGNORECASE
  )
  for idx, line in enumerate(all_lines, start=1):
    if re.match(r"^##\s+", line):
      in_flows = bool(flows_hdr_re.match(line))
      continue
    if in_flows and not line.lstrip().startswith("#"):
      errors.extend(_check_altitude_line(line, idx))

  steps = _split_flow_steps(flows_body)
  if not steps:
    errors.append({
        "severity": "ERROR",
        "code": "EMPTY_USER_FLOWS",
        "message": "## User Flows contains no numbered or ### Step entries.",
    })
  for title, block in steps:
    errors.extend(_check_step_4q(title, block))

  for item in _check_coverage(text, flows_body) + _check_ui_stack(text):
    (errors if item["severity"] == "ERROR" else warnings).append(item)

  return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}


def _normalize_hex(raw: str) -> str:
  """Normalizes 3-digit (#rgb) and 4-digit (#rgba) hex literals to 6/8-digit lowercase."""
  h = raw.lower()
  if len(h) in (4, 5):
    return "#" + "".join(c * 2 for c in h[1:])
  return h


def audit_design_token_drift(
    diff_text: str, design_md_text: str
) -> dict[str, Any]:
  """Detects added raw hex literals in UI diff lines that are absent from DESIGN.md."""
  allowed_hex = {
      _normalize_hex(m.group(0)) for m in _HEX_RE.finditer(design_md_text)
  }
  findings: list[dict[str, Any]] = []
  current_file = ""
  for line in diff_text.splitlines():
    if line.startswith("+++ "):
      path = line[4:].split("\t", 1)[0].strip()
      current_file = path[2:] if path.startswith("b/") else path
      continue
    if not line.startswith("+") or line.startswith("+++"):
      continue
    if not current_file.lower().endswith(_UI_EXTS):
      continue
    added = _NON_COLOR_STRIP_RE.sub(" ", line[1:])
    for match in _HEX_RE.finditer(added):
      norm = _normalize_hex(match.group(0))
      if norm not in allowed_hex:
        findings.append({
            "severity": "WARNING",
            "code": "TOKEN_DRIFT",
            "file": current_file,
            "hex": match.group(0),
            "message": (
                f"[WARNING] Token Drift in {current_file}: added raw hex "
                f"'{match.group(0)}' is not declared in DESIGN.md."
            ),
        })
  return {"ok": len(findings) == 0, "findings": findings}


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(
      description="Validate Armature UI Flow Specs and Design Token Drift."
  )
  parser.add_argument(
      "spec_path", nargs="?", help="Path to spec.md or flow spec markdown file"
  )
  parser.add_argument(
      "--require-flows",
      action="store_true",
      help="Fail if ## User Flows is absent",
  )
  parser.add_argument(
      "--diff",
      dest="diff_path",
      help="Unified diff file to audit against --design-md",
  )
  parser.add_argument(
      "--design-md",
      dest="design_md_path",
      help="Path to DESIGN.md for token drift audit",
  )
  parser.add_argument("--json", action="store_true", help="Emit JSON output")
  args = parser.parse_args(argv)

  if args.diff_path or args.design_md_path:
    if not (args.diff_path and args.design_md_path):
      print(
          "[ERROR] INVALID_ARGS: --diff and --design-md must be passed"
          " together.",
          file=sys.stderr,
      )
      return 2
    try:
      with (
          open(args.diff_path, "r", encoding="utf-8") as df,
          open(args.design_md_path, "r", encoding="utf-8") as dm,
      ):
        result = audit_design_token_drift(df.read(), dm.read())
    except OSError as exc:
      print(f"[ERROR] FILE_NOT_FOUND: {exc}", file=sys.stderr)
      return 2
    if args.json:
      print(json.dumps(result, indent=2))
    else:
      for item in result["findings"]:
        print(item["message"])
      if result["ok"]:
        print(f"PASS: zero token drift vs {args.design_md_path}")
    return 0 if result["ok"] else 1

  if not args.spec_path:
    parser.error(
        "spec_path is required unless --diff and --design-md are specified"
    )
  try:
    with open(args.spec_path, "r", encoding="utf-8") as f:
      text = f.read()
  except OSError as exc:
    print(f"[ERROR] FILE_NOT_FOUND: {exc}", file=sys.stderr)
    return 2

  result = lint_flow_spec_text(text, require_flows=args.require_flows)
  if args.json:
    print(json.dumps(result, indent=2))
  else:
    for err in result["errors"]:
      print(f"[ERROR] {err['code']}: {err['message']}")
    for warn in result["warnings"]:
      print(f"[WARNING] {warn['code']}: {warn['message']}")
    if result["ok"]:
      print(f"PASS: {args.spec_path} ({len(result['warnings'])} warning(s))")
  return 0 if result["ok"] else 1


if __name__ == "__main__":
  sys.exit(main())
