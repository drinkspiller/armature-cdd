#!/usr/bin/env python3
"""SkillOpt Runner for Three-Altitude UI/UX Elicitation & Design CDD (ADR 0022).

Evaluates:
- UI-only scoping & product.md audience reuse
- Interleaved Step 5 UX pattern + UI Stack + technical grilling (zero hex/px
leaks)
- Adaptive 2-Gate (no DESIGN.md) vs 1-Gate (existing DESIGN.md) routing
- Flow Spec Altitude linter (validate_flow_specs.py) compliance
- /arm-review Token Drift detection & Deliberate vs Drift classification
- /arm-drift Altitude leak + Token Drift detection in --check mode

Usage:
  python3 evals/skillopt/run_ui_elicitation_opt.py --verify_schema
  python3 evals/skillopt/run_ui_elicitation_opt.py --phase eval --seeds 3
  python3 evals/skillopt/run_ui_elicitation_opt.py --phase baseline --seeds 3
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import re
import subprocess
import sys
import time
from typing import Any
import urllib.error
import urllib.request

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
ARMATURE_ROOT = os.path.abspath(os.path.join(EVALS_DIR, "..", ".."))
TRAIN_PATH = os.path.join(EVALS_DIR, "tasks", "train_ui_elicitation.jsonl")
VAL_PATH = os.path.join(EVALS_DIR, "tasks", "val_ui_elicitation.jsonl")
RESULTS_PATH = os.path.join(EVALS_DIR, "ui_elicitation_eval_results.json")
SCRIPTS_DIR = os.path.join(ARMATURE_ROOT, "skills", "arm-new-track", "scripts")

if SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)
import validate_flow_specs as vfs  # noqa: E402

TARGET_MODELS = ["gemini-flash-latest", "gemini-3-flash-preview"]
API_KEY = os.environ.get("GEMINI_API_KEY")
_FILE_PATH_RE = re.compile(
    r"[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)+\.[a-zA-Z]{1,6}"
)

TOOL_DECLARATIONS = [{
    "functionDeclarations": [
        {
            "name": "ask_question",
            "description": "Ask the user multiple-choice questions via modal.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "questions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "question": {"type": "STRING"},
                                "options": {
                                    "type": "ARRAY",
                                    "items": {"type": "STRING"},
                                },
                            },
                            "required": ["question", "options"],
                        },
                    }
                },
                "required": ["questions"],
            },
        },
        {
            "name": "write_to_file",
            "description": "Write content to a file.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "TargetFile": {"type": "STRING"},
                    "CodeContent": {"type": "STRING"},
                },
                "required": ["TargetFile", "CodeContent"],
            },
        },
        {
            "name": "replace_file_content",
            "description": "Replace text in an existing file.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "TargetFile": {"type": "STRING"},
                    "TargetContent": {"type": "STRING"},
                    "ReplacementContent": {"type": "STRING"},
                },
                "required": [
                    "TargetFile",
                    "TargetContent",
                    "ReplacementContent",
                ],
            },
        },
    ]
}]


def load_tasks(path: str) -> list[dict[str, Any]]:
  """Loads and validates JSONL SkillOpt task records from disk."""
  tasks: list[dict[str, Any]] = []
  with open(path, "r", encoding="utf-8") as f:
    for line_no, raw in enumerate(f, start=1):
      raw = raw.strip()
      if not raw:
        continue
      obj = json.loads(raw)
      for req in ("id", "skill", "prompt", "invariants"):
        if req not in obj:
          raise ValueError(f"{path}:{line_no} missing required key '{req}'")
      tasks.append(obj)
  return tasks


def check_disjoint(
    train_tasks: list[dict[str, Any]], val_tasks: list[dict[str, Any]]
) -> None:
  """Asserts train and validation task IDs and fixture file paths are disjoint."""
  train_ids = {t["id"] for t in train_tasks}
  val_ids = {t["id"] for t in val_tasks}
  if train_ids & val_ids:
    raise ValueError(f"Overlapping task IDs: {train_ids & val_ids}")
  train_paths: set[str] = set()
  for t in train_tasks:
    for p in _FILE_PATH_RE.findall(t["prompt"]):
      if not p.startswith("armature/"):
        train_paths.add(p)
  val_paths: set[str] = set()
  for t in val_tasks:
    for p in _FILE_PATH_RE.findall(t["prompt"]):
      if not p.startswith("armature/"):
        val_paths.add(p)
  if train_paths & val_paths:
    raise ValueError(
        "Overlapping fixture file paths between train and val:"
        f" {train_paths & val_paths}"
    )
  if len(train_tasks) < 5 or len(val_tasks) < 5:
    raise ValueError("Expected at least 5 train and 5 val tasks.")


def evaluate_invariants(
    task: dict[str, Any], response_text: str, tool_calls: list[dict[str, Any]]
) -> dict[str, bool]:
  """Deterministic invariant scorer for UI elicitation rollouts."""
  written_files: dict[str, str] = {}
  asked_questions: list[dict[str, Any]] = []
  for tc in tool_calls:
    name = tc.get("name", "")
    args = tc.get("args", {})
    if name == "write_to_file":
      written_files[args.get("TargetFile", "")] = args.get("CodeContent", "")
    elif name == "ask_question":
      asked_questions.extend(args.get("questions", []))

  spec_text = next(
      (c for p, c in written_files.items() if p.endswith("spec.md")), ""
  )
  all_ask_text = " ".join(
      q.get("question", "") + " " + " ".join(q.get("options", []))
      for q in asked_questions
  )
  options_text = " ".join(
      " ".join(q.get("options", [])) for q in asked_questions
  )
  combined = (response_text + "\n" + all_ask_text).lower()
  results: dict[str, bool] = {}

  for inv in task["invariants"]:
    if inv == "writes_draft_spec":
      results[inv] = bool(spec_text and "status: draft" in spec_text.lower())
    elif inv == "writes_spec_and_manual_testing":
      has_mt = any(p.endswith("manual_testing.md") for p in written_files)
      results[inv] = bool(spec_text and has_mt)
    elif inv == "calls_ask_question":
      results[inv] = len(asked_questions) > 0
    elif inv == "does_not_reask_audience":
      reask = re.search(
          r"who (?:are|is) the (?:target )?(?:user|audience)",
          all_ask_text,
          re.I,
      )
      results[inv] = not bool(reask)
    elif inv == "asks_ux_pattern_or_behavior_not_hex":
      visual_leak = any(
          vfs.HEX_RE.search(txt) or vfs.PX_REM_RE.search(txt)
          for txt in (response_text, all_ask_text, spec_text)
      )
      has_pattern_opts = any(
          len(q.get("options", [])) >= 2 for q in asked_questions
      ) and bool(
          re.search(
              r"drawer|modal|split[- ]?pane|split[-"
              r" ]?view|inline|popup|overlay|toast|"
              r"expandable|card|feed|tab|panel|route|empty|loading|error",
              options_text,
              re.I,
          )
      )
      results[inv] = (not visual_leak) and has_pattern_opts
    elif inv == "spec_passes_flow_linter":
      results[inv] = bool(
          spec_text
          and vfs.lint_flow_spec_text(spec_text, require_flows=True)["ok"]
      )
    elif inv == "no_variant_redesign":
      results[inv] = not bool(
          re.search(r"3 contrasting.*variant|pick a visual look", combined)
      )
    elif inv == "skips_ui_flow_and_look":
      leaked_ui = bool(
          re.search(
              r"design\.md|375px|visual variant|user flow|ui stack", combined
          )
      )
      results[inv] = not leaked_ui
    elif inv == "flags_token_drift":
      rogue_hexes = [h.lower() for h in task.get("expected_rogue_hexes", [])]
      has_hex = any(h in combined for h in rogue_hexes) if rogue_hexes else True
      results[inv] = has_hex and bool(
          re.search(
              r"token drift|not declared in design\.md|unapproved.*hex",
              combined,
          )
      )
    elif inv == "flags_altitude_leak":
      results[inv] = bool(
          re.search(
              r"altitude_leak|altitude"
              r" leak|hex.*flow|px.*flow|border-radius.*flow",
              combined,
          )
      )
    elif inv == "proposes_deliberate_vs_drift":
      results[inv] = (
          "deliberate" in all_ask_text.lower()
          and "drift" in all_ask_text.lower()
      )
    elif inv == "does_not_silently_overwrite_spec":
      results[inv] = not any(p.endswith("spec.md") for p in written_files)
    else:
      raise ValueError(f"Unknown invariant: {inv}")
  return results


def _load_system_prompt(skill_name: str, phase: str) -> str:
  """Loads rules and SKILL.md for baseline (origin/main) or eval (working copy)."""
  files = [
      "rules/armature_protocol.md",
      "rules/armature_antigravity.md",
      "rules/armature_cdd_protocols.md",
      f"skills/{skill_name}/SKILL.md",
  ]
  parts: list[str] = [
      f"You are an AI coding agent running the Armature `/{skill_name}` skill"
      " with tool declarations enabled (`ask_question`, `write_to_file`,"
      " `replace_file_content`). Follow the rules and skill below verbatim."
      " When a turn requires file drafts/materialization or an interactive"
      " `ask_question` modal, emit visible markdown prose first AND invoke"
      " those function calls in the response rather than stopping after prose."
  ]
  for rel in files:
    if phase == "baseline":
      loaded = None
      last_err = ""
      for rev in ("origin/main", "HEAD~1"):
        proc = subprocess.run(
            ["git", "show", f"{rev}:{rel}"],
            cwd=ARMATURE_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
          loaded = proc.stdout
          break
        last_err = proc.stderr.strip()
      if loaded is None:
        raise RuntimeError(
            f"Failed to load baseline '{rel}' from origin/main or HEAD~1:"
            f" {last_err}"
        )
      parts.append(loaded)
    else:
      full = os.path.join(ARMATURE_ROOT, rel)
      if not os.path.exists(full):
        raise FileNotFoundError(f"Missing candidate file: {full}")
      with open(full, "r", encoding="utf-8") as f:
        parts.append(f.read())
  return "\n\n---\n\n".join(parts)


def _call_gemini(
    prompt: str, system_instruction: str, seed: int, max_retries: int = 2
) -> tuple[str, list[dict[str, Any]]]:
  """Calls Gemini with multi-step tool loop and transient error backoff."""
  if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set.")
  payload: dict[str, Any] = {
      "systemInstruction": {"parts": [{"text": system_instruction}]},
      "contents": [{"role": "user", "parts": [{"text": prompt}]}],
      "tools": TOOL_DECLARATIONS,
      "generationConfig": {
          "temperature": 0.2,
          "seed": seed,
          "maxOutputTokens": 16384,
      },
      "safetySettings": [
          {"category": c, "threshold": "BLOCK_NONE"}
          for c in (
              "HARM_CATEGORY_HARASSMENT",
              "HARM_CATEGORY_HATE_SPEECH",
              "HARM_CATEGORY_SEXUALLY_EXPLICIT",
              "HARM_CATEGORY_DANGEROUS_CONTENT",
              "HARM_CATEGORY_CIVIC_INTEGRITY",
          )
      ],
  }
  all_texts: list[str] = []
  all_calls: list[dict[str, Any]] = []
  for _ in range(4):
    raw_body = json.dumps(payload).encode("utf-8")
    last_err: Exception | None = None
    data: dict[str, Any] = {}
    succeeded = False
    for model in TARGET_MODELS:
      url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
      for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            url,
            data=raw_body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": API_KEY,
            },
            method="POST",
        )
        try:
          with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
          succeeded = True
          break
        except urllib.error.HTTPError as err:
          last_err = err
          if (
              err.code not in (429, 500, 502, 503, 504)
              or attempt == max_retries
          ):
            break
        except (TimeoutError, urllib.error.URLError) as err:
          last_err = err
          if attempt == max_retries:
            break
        time.sleep(min(15.0, (2 ** (attempt + 1)) + random.uniform(0.2, 1.0)))
      if succeeded:
        break
    if not succeeded and last_err is not None:
      raise last_err
    cands = data.get("candidates") or []
    if not cands or "content" not in cands[0]:
      break
    model_content = cands[0]["content"]
    step_calls: list[dict[str, Any]] = []
    for p in model_content.get("parts", []):
      if "text" in p and not p.get("thought"):
        all_texts.append(p["text"])
      if "functionCall" in p:
        fc = p["functionCall"]
        step_calls.append(fc)
        all_calls.append(fc)
    if not step_calls or any(
        fc.get("name") == "ask_question" for fc in step_calls
    ):
      break
    if not all(
        fc.get("name") in ("write_to_file", "replace_file_content")
        for fc in step_calls
    ):
      break
    payload["contents"].append(model_content)
    payload["contents"].append({
        "role": "user",
        "parts": [
            {
                "functionResponse": {
                    "name": fc["name"],
                    "response": {"result": "ok"},
                }
            }
            for fc in step_calls
        ],
    })
  return "\n".join(all_texts), all_calls


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(
      description="SkillOpt UI Elicitation Eval Runner"
  )
  parser.add_argument(
      "--verify_schema",
      action="store_true",
      help="Validate train/val schemas offline",
  )
  parser.add_argument("--phase", choices=["baseline", "eval"], default="eval")
  parser.add_argument(
      "--split", choices=["train", "val", "both"], default="both"
  )
  parser.add_argument("--seeds", type=int, default=1)
  args = parser.parse_args(argv)

  train_tasks = load_tasks(TRAIN_PATH)
  val_tasks = load_tasks(VAL_PATH)
  check_disjoint(train_tasks, val_tasks)

  if args.verify_schema:
    print(
        f"Schema Verification PASSED: {len(train_tasks)} train tasks and"
        f" {len(val_tasks)} val tasks valid & disjoint."
    )
    return 0

  if not API_KEY:
    print(
        "GEMINI_API_KEY is not set; cannot execute live Gemini API rollouts.",
        file=sys.stderr,
    )
    return 2

  if args.split == "train":
    tasks = train_tasks
  elif args.split == "val":
    tasks = val_tasks
  else:
    tasks = train_tasks + val_tasks
  records: list[dict[str, Any]] = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    futures = []
    for task in tasks:
      sys_prompt = _load_system_prompt(task["skill"], args.phase)
      for seed in range(42, 42 + args.seeds):
        futures.append((
            task,
            seed,
            pool.submit(_call_gemini, task["prompt"], sys_prompt, seed),
        ))
    for task, seed, fut in futures:
      text, calls = fut.result()
      inv = evaluate_invariants(task, text, calls)
      passed_ok = all(inv.values())
      print(
          f"  [{args.phase}] {task['id']} seed={seed}:"
          f" {'PASS' if passed_ok else 'FAIL'} {inv}",
          file=sys.stderr,
          flush=True,
      )
      records.append({
          "id": task["id"],
          "seed": seed,
          "passed": passed_ok,
          "invariants": inv,
      })

  passed = sum(1 for r in records if r["passed"])
  summary = {
      "phase": args.phase,
      "total": len(records),
      "passed": passed,
      "rate": passed / max(1, len(records)),
      "records": records,
  }
  with open(RESULTS_PATH, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
  print(
      json.dumps(
          {
              "phase": args.phase,
              "total": summary["total"],
              "passed": passed,
              "rate": summary["rate"],
          },
          indent=2,
      )
  )
  return 0


if __name__ == "__main__":
  sys.exit(main())
