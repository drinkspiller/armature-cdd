#!/usr/bin/env python3
"""Armature SkillOpt Evaluation & Optimization Runner.

A zero-external-dependency benchmarking and optimization runner for the
Armature skill suite. Evaluates skills against structured task suites and
optionally optimizes instructions using Gemini model reflection.

Usage:
  # Run benchmark on all tasks across all skills:
  python3 evals/skillopt/run_optimizer.py --eval_only

  # Run benchmark for a specific skill:
  python3 evals/skillopt/run_optimizer.py \
      --target=skills/arm-new-track/SKILL.md --eval_only

  # Run full optimization loop on a skill:
  python3 evals/skillopt/run_optimizer.py \
      --target=skills/arm-new-track/SKILL.md --optimize
"""

import argparse
import difflib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

TARGET_MODEL = "gemini-3.5-flash"
OPTIMIZER_MODEL = "gemini-3.1-pro-preview"
API_KEY = os.environ.get("GEMINI_API_KEY")

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
ARMATURE_ROOT = os.path.abspath(os.path.join(EVALS_DIR, "..", ".."))
TRAIN_PATH = os.path.join(EVALS_DIR, "tasks", "train.jsonl")
VAL_PATH = os.path.join(EVALS_DIR, "tasks", "val.jsonl")
RESULTS_PATH = os.path.join(EVALS_DIR, "eval_results.json")


import concurrent.futures
import math
import statistics


def call_gemini(
    model: str,
    prompt: str,
    system_instruction: str = None,
    temperature: float = 0.2,
    max_retries: int = 5,
    use_tools: bool = False,
    seed: int = None,
) -> str:
  if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Set GEMINI_API_KEY environment variable."
    )

  url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
  gen_config = {
      "temperature": temperature,
      "maxOutputTokens": 8192,
  }
  if seed is not None:
    gen_config["seed"] = seed
  payload = {
      "contents": [{"parts": [{"text": prompt}]}],
      "generationConfig": gen_config,
      "safetySettings": [
          {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
          {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
          {
              "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
              "threshold": "BLOCK_NONE",
          },
          {
              "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
              "threshold": "BLOCK_NONE",
          },
          {
              "category": "HARM_CATEGORY_CIVIC_INTEGRITY",
              "threshold": "BLOCK_NONE",
          },
      ],
  }
  if system_instruction:
    payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

  if use_tools:
    payload["tools"] = [{
        "functionDeclarations": [
            {
                "name": "ask_question",
                "description": (
                    "Ask the user one or more multiple-choice questions."
                ),
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
                                    "is_multi_select": {"type": "BOOLEAN"},
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
                "description": (
                    "Write specification or code content to a target file path."
                ),
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
                "name": "invoke_subagent",
                "description": (
                    "Invokes one or more subagents by name with a single tool"
                    " call."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "Subagents": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "TypeName": {"type": "STRING"},
                                    "Role": {"type": "STRING"},
                                    "Prompt": {"type": "STRING"},
                                    "Workspace": {"type": "STRING"},
                                },
                                "required": ["TypeName", "Role", "Prompt"],
                            },
                        }
                    },
                    "required": ["Subagents"],
                },
            },
            {
                "name": "schedule",
                "description": (
                    "Schedule a one-shot timer or recurring cron job."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "DurationSeconds": {"type": "INTEGER"},
                        "Prompt": {"type": "STRING"},
                        "TimerCondition": {"type": "STRING"},
                    },
                    "required": ["DurationSeconds", "Prompt"],
                },
            },
            {
                "name": "run_command",
                "description": (
                    "Execute a shell command (e.g., VCS diff, non-destructive"
                    " setup script)."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "CommandLine": {"type": "STRING"},
                    },
                    "required": ["CommandLine"],
                },
            },
        ]
    }]

  data = json.dumps(payload).encode("utf-8")

  for attempt in range(1, max_retries + 1):
    try:
      req = urllib.request.Request(
          url, data=data, headers={"Content-Type": "application/json"}
      )
      with urllib.request.urlopen(req, timeout=90) as resp:
        res_json = json.loads(resp.read().decode("utf-8"))
        candidates = res_json.get("candidates", [])
        if candidates:
          first = candidates[0]
          if "content" in first:
            parts = first["content"].get("parts", [])
            output_blocks = []
            for p in parts:
              if "text" in p and p["text"]:
                t = p["text"]
                if re.search(
                    r"call:(?:default_api:)?ask_question|ask_question\s*\{", t
                ):
                  t += "\n[PROTOCOL_VIOLATION: RAW_TOOL_TEXT_LEAK_DETECTED]"
                if re.search(r"I will now ask[^\n]*$", t.strip()):
                  t += "\n[PROTOCOL_VIOLATION: TRAILING_NARRATION_DETECTED]"
                output_blocks.append(t)
              elif "functionCall" in p:
                fc = p["functionCall"]
                output_blocks.append(
                    "\n[NATIVE_FUNCTION_CALL:"
                    f" {fc.get('name')}({json.dumps(fc.get('args', {}))})]\n"
                )
            return "".join(output_blocks)
          else:
            finish_reason = first.get("finishReason", "UNKNOWN")
            print(
                f"  [API Warning] {model} finished with reason:"
                f" {finish_reason}",
                file=sys.stderr,
                flush=True,
            )
        return ""
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
      print(
          f"  [API Warning] {model} call failed (attempt"
          f" {attempt}/{max_retries}): {e}",
          file=sys.stderr,
          flush=True,
      )
      if attempt == max_retries:
        raise
      time.sleep(2 * attempt)
  return ""


def verify_jsonl_schema(
    filepath: str, expected_count: int = None
) -> tuple[bool, list]:
  """Verifies JSONL syntax and task schema integrity across all tasks in filepath."""
  errors = []
  if not os.path.exists(filepath):
    return False, [f"File not found: {filepath}"]

  seen_ids = set()
  tasks = []
  required_keys = {"id", "target_skill", "category", "prompt", "eval_criteria"}
  phase2_prefixes = (
      "TRAIN_35",
      "TRAIN_36",
      "TRAIN_37",
      "TRAIN_38",
      "TRAIN_39",
      "TRAIN_40",
      "VAL_31",
      "VAL_32",
      "VAL_33",
      "VAL_34",
  )

  with open(filepath, "r", encoding="utf-8") as f:
    for line_num, raw_line in enumerate(f, start=1):
      line = raw_line.strip()
      if not line:
        continue
      try:
        obj = json.loads(line)
      except json.JSONDecodeError as e:
        errors.append(f"{filepath}:{line_num} - Invalid JSON syntax: {e}")
        continue

      if not isinstance(obj, dict):
        errors.append(f"{filepath}:{line_num} - Expected JSON object (dict)")
        continue

      missing = required_keys - set(obj.keys())
      if missing:
        errors.append(
            f"{filepath}:{line_num} (id={obj.get('id')}) - Missing required"
            f" keys: {sorted(missing)}"
        )

      task_id = obj.get("id")
      if not isinstance(task_id, str) or not task_id.strip():
        errors.append(f"{filepath}:{line_num} - Invalid or empty 'id'")
      elif task_id in seen_ids:
        errors.append(f"{filepath}:{line_num} - Duplicate task id: '{task_id}'")
      else:
        seen_ids.add(task_id)

      for str_key in ("target_skill", "category", "prompt"):
        val = obj.get(str_key)
        if not isinstance(val, str) or not val.strip():
          errors.append(
              f"{filepath}:{line_num} (id={task_id}) - Invalid or empty"
              f" '{str_key}'"
          )

      target_skill = obj.get("target_skill")
      if isinstance(target_skill, str) and target_skill.strip():
        skill_path = os.path.join(
            ARMATURE_ROOT, "skills", target_skill.strip(), "SKILL.md"
        )
        if not os.path.exists(skill_path):
          errors.append(
              f"{filepath}:{line_num} (id={task_id}) - Target skill SKILL.md"
              f" not found: {skill_path}"
          )

      criteria = obj.get("eval_criteria")
      if not isinstance(criteria, list) or not criteria:
        errors.append(
            f"{filepath}:{line_num} (id={task_id}) - 'eval_criteria' must be a"
            " non-empty list"
        )
      else:
        has_inv = False
        has_qual = False
        is_phase2 = isinstance(task_id, str) and task_id.startswith(
            phase2_prefixes
        )
        for idx, c in enumerate(criteria):
          if not isinstance(c, str) or not c.strip():
            errors.append(
                f"{filepath}:{line_num} (id={task_id}) - Criterion #{idx} is"
                " not a valid non-empty string"
            )
          elif is_phase2:
            if c.startswith("[INVARIANT]"):
              has_inv = True
            elif c.startswith("[QUALITY]"):
              has_qual = True
            else:
              errors.append(
                  f"{filepath}:{line_num} (id={task_id}) - Phase 2 criterion"
                  f" #{idx} must start with '[INVARIANT]' or '[QUALITY]': {c}"
              )
        if is_phase2 and (not has_inv or not has_qual):
          errors.append(
              f"{filepath}:{line_num} (id={task_id}) - Phase 2 task must have"
              " at least one [INVARIANT] and one [QUALITY] criterion"
          )

      tasks.append(obj)

  if expected_count is not None and len(tasks) != expected_count:
    errors.append(
        f"{filepath} - Expected {expected_count} tasks, found {len(tasks)}"
    )

  return len(errors) == 0, errors


def sanitize_json_backslashes(s: str) -> str:
  """Escapes stray backslashes that are not valid JSON escape sequences using left-to-right token consumption."""
  return re.sub(
      r'\\(["\\/bfnrt]|u[0-9a-fA-F]{4})|\\',
      lambda m: m.group(0) if m.group(1) else r"\\\\",
      s,
  )


def parse_judge_json_safely(judge_raw: str, criteria: list) -> list:
  """Hardened JSON parser for LLM judge output handling stray backslashes and bracketed preambles."""
  candidates = []
  # 1. Prioritize fenced code block containing a JSON array of objects
  fenced_matches = re.findall(
      r"```(?:json)?\s*(\[\s*\{.*?\}\s*\])\s*```", judge_raw, re.DOTALL
  )
  candidates.extend(fenced_matches)

  # 2. Match array of objects [ { ... } ] directly without grabbing preamble brackets
  obj_array_match = re.search(r"\[\s*\{.*\}\s*\]", judge_raw, re.DOTALL)
  if obj_array_match:
    candidates.append(obj_array_match.group(0))

  # 3. Fallback to outermost brackets
  fallback_match = re.search(r"\[.*\]", judge_raw, re.DOTALL)
  if fallback_match:
    candidates.append(fallback_match.group(0))

  parsed = None
  for raw_candidate in candidates:
    for candidate_str in (
        raw_candidate,
        sanitize_json_backslashes(raw_candidate),
    ):
      try:
        attempt = json.loads(candidate_str, strict=False)
        if isinstance(attempt, list) and any(
            isinstance(x, dict) for x in attempt
        ):
          parsed = attempt
          break
      except json.JSONDecodeError:
        continue
    if parsed is not None:
      break

  if not isinstance(parsed, list):
    return [
        {
            "criterion": c,
            "passed": False,
            "reason": (
                "Failed to parse judge JSON (even after backslash sanitization)"
            ),
            "tier": "INVARIANT" if "[INVARIANT]" in c else "QUALITY",
        }
        for c in criteria
    ]

  results = []
  claimed_indices = set()
  for idx, c in enumerate(criteria):
    tier = "INVARIANT" if "[INVARIANT]" in c else "QUALITY"
    matched_item = None
    matched_idx = None

    # First: exact match by criterion text
    for item_idx, item in enumerate(parsed):
      if (
          item_idx not in claimed_indices
          and isinstance(item, dict)
          and item.get("criterion") == c
      ):
        matched_item = item
        matched_idx = item_idx
        break

    # Second: normalized text match (ignoring case/whitespace/tier prefix differences)
    if matched_item is None:
      norm_c = re.sub(r"^\[(?:INVARIANT|QUALITY)\]\s*", "", c).strip().lower()
      for item_idx, item in enumerate(parsed):
        if item_idx not in claimed_indices and isinstance(item, dict):
          item_crit = str(item.get("criterion", ""))
          norm_item = (
              re.sub(r"^\[(?:INVARIANT|QUALITY)\]\s*", "", item_crit)
              .strip()
              .lower()
          )
          if (
              norm_c
              and norm_item
              and (
                  norm_c == norm_item
                  or norm_c in norm_item
                  or norm_item in norm_c
              )
          ):
            matched_item = item
            matched_idx = item_idx
            break

    # Third: positional fallback only if array lengths match and index is unclaimed
    if (
        matched_item is None
        and len(parsed) == len(criteria)
        and idx not in claimed_indices
        and isinstance(parsed[idx], dict)
    ):
      matched_item = parsed[idx]
      matched_idx = idx

    if matched_item is not None:
      if matched_idx is not None:
        claimed_indices.add(matched_idx)
      results.append({
          "criterion": c,
          "passed": bool(matched_item.get("passed", False)),
          "reason": str(matched_item.get("reason", "")),
          "tier": tier,
      })
    else:
      results.append({
          "criterion": c,
          "passed": False,
          "reason": "Criterion missing from judge output array",
          "tier": tier,
      })
  return results


ZERO_SQL_CRITERIA_PHRASES = (
    "does not execute or output any database seed or sql",
    "does not execute any database seed or sql",
    "without fabricating dummy sql seed",
    "does not fabricate or hallucinate speculative sql seed",
    "does not escalate to a full stateful database seed",
)


def annotate_protocol_signals(task: dict, rollout_output: str) -> str:
  """Appends deterministic protocol verification/violation signals for visual-only runs."""
  criteria = task.get("eval_criteria") or task.get("criteria", [])
  annotated = rollout_output

  # Extract full single-line native function calls emitted by call_gemini
  all_tool_calls = re.findall(
      r"\[NATIVE_FUNCTION_CALL:[^\n]*\}\)\]", rollout_output
  )
  ask_question_calls = [tc for tc in all_tool_calls if "ask_question(" in tc]

  # 1. Check inline override escape hatch ('Run full domain runbook instead') inside ask_question tool call
  requires_escape_hatch = any(
      "run full domain runbook instead" in c.lower() for c in criteria
  )
  if requires_escape_hatch:
    has_escape_in_fc = any(
        "run full domain runbook instead" in tc.lower()
        for tc in ask_question_calls
    )
    if has_escape_in_fc:
      annotated += "\n[PROTOCOL_VERIFIED: INLINE_OVERRIDE_ESCAPE_HATCH_PRESENT]"
    else:
      annotated += (
          "\n[PROTOCOL_VIOLATION: MISSING_INLINE_OVERRIDE_ESCAPE_HATCH]"
      )

  # 2. Check SQL seed leakage strictly on visual-only zero-SQL tasks
  requires_zero_sql = any(
      any(p in c.lower() for p in ZERO_SQL_CRITERIA_PHRASES) for c in criteria
  )
  if requires_zero_sql:
    code_blocks = re.findall(r"```.*?```", rollout_output, re.DOTALL)
    step_lines = re.findall(
        r"(?m)^\s*(?:[•\-\*1-9]|\[\•\])\s*Step\s+\d+:.*$", rollout_output
    )
    sql_leak_pattern = re.compile(
        r"(?:\bINSERT\s+INTO\b|\bDROP\s+TABLE\b|\bTRUNCATE\s+TABLE\b|\bspan\s+sql\b|seed_users\.js)",
        re.IGNORECASE,
    )
    leaked_in_blocks = any(sql_leak_pattern.search(b) for b in code_blocks)
    leaked_in_tools = any(sql_leak_pattern.search(t) for t in all_tool_calls)
    leaked_in_steps = any(sql_leak_pattern.search(s) for s in step_lines)
    if leaked_in_blocks or leaked_in_tools or leaked_in_steps:
      annotated += "\n[PROTOCOL_VIOLATION: SQL_SEED_LEAKED_IN_VISUAL_ONLY_MODE]"
    else:
      annotated += "\n[PROTOCOL_VERIFIED: ZERO_SQL_SEED_LEAKED]"

  # 3. Check adversarial trap disqualification (VETO against Micro-Verification)
  is_adversarial_veto = any(
      "veto:" in c.lower() and "micro-verification" in c.lower()
      for c in criteria
  )
  if is_adversarial_veto:
    if re.search(r"┌─\s*\[Micro-Verification Plan\]", rollout_output):
      annotated += (
          "\n[PROTOCOL_VIOLATION: ILLEGAL_MICRO_VERIFICATION_ON_STATEFUL_DIFF]"
      )
    else:
      annotated += (
          "\n[PROTOCOL_VERIFIED: ADVERSARIAL_TRAP_SUCCESSFULLY_DISQUALIFIED]"
      )

  # 4. Check localhost URL formatting and remote workstation hostname prohibition
  for c in criteria:
    c_lower = c.lower()
    if "localhost" in c_lower and "[invariant]" in c_lower:
      expected_urls = re.findall(r"http://localhost:\d+/[a-zA-Z0-9_\-/]*", c)
      missing_url = any(u not in rollout_output for u in expected_urls)
      has_cloudtop = (
          "remote workstation hostname" in c_lower
          and ".example.internal" in rollout_output.lower()
      )
      if missing_url or has_cloudtop:
        annotated += "\n[PROTOCOL_VIOLATION: INVALID_OR_MISSING_LOCALHOST_URL]"
      else:
        annotated += "\n[PROTOCOL_VERIFIED: LOCALHOST_URL_VALIDATED]"

  # 5. Check multi-route consolidation into a SINGLE Micro-Verification card
  requires_single_card = any(
      "single consolidated" in c.lower()
      and "[micro-verification plan]" in c.lower()
      for c in criteria
  )
  if requires_single_card:
    card_count = len(
        re.findall(r"┌─\s*\[Micro-Verification Plan\]", rollout_output)
    )
    if card_count != 1:
      annotated += (
          "\n[PROTOCOL_VIOLATION:"
          f" EXPECTED_SINGLE_CONSOLIDATED_CARD_FOUND_{card_count}]"
      )
    else:
      annotated += "\n[PROTOCOL_VERIFIED: SINGLE_CONSOLIDATED_CARD_CONFIRMED]"

  # 6. Check cold-start deferred stamp when required by [INVARIANT]
  requires_deferred_stamp = any(
      "stateful 3-part fixture triad deferred" in c.lower()
      and "[invariant]" in c.lower()
      for c in criteria
  )
  if requires_deferred_stamp:
    if "stateful 3-part fixture triad deferred" not in rollout_output.lower():
      annotated += "\n[PROTOCOL_VIOLATION: MISSING_DEFERRED_FIXTURE_STAMP]"
    else:
      annotated += "\n[PROTOCOL_VERIFIED: DEFERRED_FIXTURE_STAMP_PRESENT]"

  # 7. Check drift diff-to-tag mismatch warning when required by [INVARIANT]
  requires_drift_warning = any(
      "[warning]" in c.lower() and "diff-to-tag mismatch" in c.lower()
      for c in criteria
  )
  if requires_drift_warning:
    has_warn = "[warning]" in rollout_output.lower()
    has_false_fixpoint = (
        "fixpoint reached" in rollout_output.lower()
        or "zero drift detected" in rollout_output.lower()
    )
    if not has_warn or has_false_fixpoint:
      annotated += "\n[PROTOCOL_VIOLATION: DRIFT_MISMATCH_WARNING_VIOLATED]"
    else:
      annotated += "\n[PROTOCOL_VERIFIED: DRIFT_MISMATCH_WARNING_VALIDATED]"

  return annotated


def enforce_deterministic_protocol_overrides(
    rollout_output: str, eval_results: list
) -> list:
  """Enforces deterministic protocol failures over LLM judge results when hard violations occur."""
  for r in eval_results:
    crit_lower = r.get("criterion", "").lower()

    if (
        "[PROTOCOL_VIOLATION: MISSING_INLINE_OVERRIDE_ESCAPE_HATCH]"
        in rollout_output
        and "run full domain runbook instead" in crit_lower
    ):
      r["passed"] = False
      r["reason"] = (
          "Deterministic protocol assertion failed: 'Run full domain runbook"
          " instead' option missing from ask_question tool call."
      )

    if (
        "[PROTOCOL_VIOLATION: SQL_SEED_LEAKED_IN_VISUAL_ONLY_MODE]"
        in rollout_output
        and any(p in crit_lower for p in ZERO_SQL_CRITERIA_PHRASES)
    ):
      r["passed"] = False
      r["reason"] = (
          "Deterministic protocol assertion failed: SQL/seed command leaked in"
          " visual-only mode."
      )

    if (
        "[PROTOCOL_VIOLATION: ILLEGAL_MICRO_VERIFICATION_ON_STATEFUL_DIFF]"
        in rollout_output
        and (
            "veto:" in crit_lower
            or "does not render a '[micro-verification plan]'" in crit_lower
            or "refuses to use the documentation-only micro-verification card"
            in crit_lower
        )
    ):
      r["passed"] = False
      r["reason"] = (
          "Deterministic protocol assertion failed: Micro-Verification card"
          " illegally rendered for stateful/adversarial diff."
      )

    if (
        "[PROTOCOL_VIOLATION: INVALID_OR_MISSING_LOCALHOST_URL]"
        in rollout_output
        and "localhost" in crit_lower
        and "[invariant]" in crit_lower
    ):
      r["passed"] = False
      r["reason"] = (
          "Deterministic protocol assertion failed: Required complete localhost"
          " URL missing or forbidden remote workstation hostname used."
      )

    if (
        "[PROTOCOL_VIOLATION: EXPECTED_SINGLE_CONSOLIDATED_CARD_FOUND_"
        in rollout_output
        and "single consolidated" in crit_lower
    ):
      r["passed"] = False
      r["reason"] = (
          "Deterministic protocol assertion failed: Did not consolidate into"
          " a single Micro-Verification Plan card."
      )

    if (
        "[PROTOCOL_VIOLATION: MISSING_DEFERRED_FIXTURE_STAMP]" in rollout_output
        and "stateful 3-part fixture triad deferred" in crit_lower
        and "[invariant]" in crit_lower
    ):
      r["passed"] = False
      r["reason"] = (
          "Deterministic protocol assertion failed: Missing required 'Stateful"
          " 3-Part Fixture Triad deferred' stamp."
      )

    if (
        "[PROTOCOL_VIOLATION: DRIFT_MISMATCH_WARNING_VIOLATED]"
        in rollout_output
        and (
            "[warning]" in crit_lower
            or "does not report 'fixpoint reached'" in crit_lower
        )
    ):
      r["passed"] = False
      r["reason"] = (
          "Deterministic protocol assertion failed: Missing '[WARNING]' tag or"
          " falsely reported Fixpoint Reached on diff-to-tag mismatch."
      )

    if (
        "[PROTOCOL_VIOLATION: RAW_TOOL_TEXT_LEAK_DETECTED]" in rollout_output
        and "raw_tool_text_leak_detected" in crit_lower
    ):
      r["passed"] = False
      r["reason"] = (
          "Deterministic protocol assertion failed: Raw tool text leaked in"
          " markdown stream."
      )

    if (
        "[PROTOCOL_VIOLATION: TRAILING_NARRATION_DETECTED]" in rollout_output
        and "trailing_narration_detected" in crit_lower
    ):
      r["passed"] = False
      r["reason"] = (
          "Deterministic protocol assertion failed: Trailing self-narration"
          " detected after rationale."
      )

  return eval_results


def load_tasks(
    filepath: str, target_skill: str = None, task_filter: str = None
):
  tasks = []
  if not os.path.exists(filepath):
    return tasks
  target_skills_set = None
  if target_skill and target_skill != "all":
    raw_targets = [t.strip() for t in target_skill.split(",") if t.strip()]
    target_skills_set = set()
    for t in raw_targets:
      s_name = (
          os.path.basename(os.path.dirname(t)) if t.endswith("SKILL.md") else t
      )
      target_skills_set.add(s_name)

  filter_prefixes = None
  if task_filter:
    filter_prefixes = [p.strip() for p in task_filter.split(",") if p.strip()]

  with open(filepath, "r", encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      task = json.loads(line)
      if target_skills_set is not None:
        if (
            task.get("target_skill")
            and task.get("target_skill") not in target_skills_set
        ):
          continue
      if filter_prefixes is not None:
        tid = task.get("id", "")
        if not any(tid.startswith(p) or p in tid for p in filter_prefixes):
          continue
      tasks.append(task)
  return tasks


def resolve_skill_path(target_arg: str) -> str:
  if os.path.isabs(target_arg):
    return target_arg
  direct_path = os.path.join(ARMATURE_ROOT, target_arg)
  if os.path.exists(direct_path):
    return direct_path
  skill_dir = os.path.join(ARMATURE_ROOT, "skills", target_arg, "SKILL.md")
  if os.path.exists(skill_dir):
    return skill_dir
  return direct_path


def get_skill_text_for_task(
    task: dict, default_skill_text: str, default_skill_name: str
) -> str:
  task_target = task.get("target_skill")
  if not task_target or task_target == default_skill_name:
    if default_skill_text:
      return default_skill_text
  skill_path = resolve_skill_path(f"skills/{task_target}/SKILL.md")
  if os.path.exists(skill_path):
    with open(skill_path, "r", encoding="utf-8") as f:
      return f.read()
  return default_skill_text


def evaluate_task(
    task: dict,
    default_skill_text: str,
    default_skill_name: str,
    seed: int = None,
):
  skill_text = get_skill_text_for_task(
      task, default_skill_text, default_skill_name
  )
  target_skill_name = task.get("target_skill", default_skill_name)

  system_instruction = (
      "You are an AI assistant executing instructions in the Armature"
      f" '{target_skill_name}' skill document"
      f" strictly:\n\n```markdown\n{skill_text}\n```\n\nFollow all guardrails,"
      " turn-ending barriers, step sequencing, and interaction protocols"
      " exactly."
  )

  rollout_prompt = (
      "Execute the following user request and"
      f" scenario:\n\n{task['prompt']}\n\nRespond to the user following all"
      " skill rules and invoke native tool calls (e.g. ask_question,"
      " write_to_file) when required."
  )

  rollout_temp = 0.15 if seed is not None else 0.1
  try:
    rollout_output = call_gemini(
        TARGET_MODEL,
        rollout_prompt,
        system_instruction=system_instruction,
        temperature=rollout_temp,
        use_tools=True,
        seed=seed,
    )
  except Exception as e:
    print(f"  [Rollout Error] Task {task['id']} failed: {e}", flush=True)
    rollout_output = f"[ERROR: Execution failed with exception: {e}]"

  rollout_output = annotate_protocol_signals(task, rollout_output)

  criteria = task.get("eval_criteria") or task.get("criteria", [])
  judge_prompt = f"""You are a strict evaluator assessing whether an agent's execution rollout satisfies each required criterion.

Task Scenario:
{task['prompt']}

Target Skill: {target_skill_name}

Agent Rollout Output:
\"\"\"
{rollout_output}
\"\"\"

Evaluation Criteria to assess:
{json.dumps(criteria, indent=2)}

For each criterion in the list above, output a JSON object with:
- "criterion": the exact text of the criterion
- "passed": boolean (true if satisfied, false if violated or skipped)
- "reason": 1-sentence explanation of evidence from the rollout output

Respond with ONLY a valid JSON array of objects:
[
  {{"criterion": "...", "passed": true/false, "reason": "..."}},
  ...
]
"""
  try:
    judge_raw = call_gemini(
        OPTIMIZER_MODEL, judge_prompt, temperature=0.0, seed=seed
    )
    eval_results = parse_judge_json_safely(judge_raw, criteria)
  except Exception as e:
    print(f"  [Judge Error] Task {task['id']} judge failed: {e}", flush=True)
    eval_results = [
        {
            "criterion": c,
            "passed": False,
            "reason": str(e),
            "tier": "INVARIANT" if "[INVARIANT]" in c else "QUALITY",
        }
        for c in criteria
    ]

  eval_results = enforce_deterministic_protocol_overrides(
      rollout_output, eval_results
  )

  passed_count = sum(1 for r in eval_results if r.get("passed", False))
  total_count = len(criteria)
  raw_score = passed_count / total_count if total_count > 0 else 0.0

  invariant_failures = [
      r
      for r in eval_results
      if r.get("tier") == "INVARIANT" and not r.get("passed", False)
  ]
  invariant_veto = len(invariant_failures) > 0

  if invariant_veto:
    score = 0.0
    effective_passed_count = 0
  else:
    score = raw_score
    effective_passed_count = passed_count

  return {
      "task_id": task["id"],
      "target_skill": target_skill_name,
      "category": task.get("category", ""),
      "seed": seed,
      "score": score,
      "raw_score": raw_score,
      "invariant_veto": invariant_veto,
      "passed_count": passed_count,
      "effective_passed_count": effective_passed_count,
      "total_count": total_count,
      "eval_results": eval_results,
      "rollout_sample": rollout_output[:1000],
  }


def run_benchmark(
    default_skill_text: str,
    default_skill_name: str,
    tasks: list,
    split_name: str,
    seed: int = None,
    max_workers: int = 8,
):
  seed_label = f" [Seed={seed}]" if seed is not None else ""
  print(
      f"\n--- Running Benchmark on {split_name}{seed_label} ({len(tasks)}"
      f" tasks, workers={max_workers}) ---",
      flush=True,
  )
  task_results = [None] * len(tasks)
  total_passed = 0
  total_criteria = 0

  with concurrent.futures.ThreadPoolExecutor(
      max_workers=max_workers
  ) as executor:
    future_to_idx = {
        executor.submit(
            evaluate_task, task, default_skill_text, default_skill_name, seed
        ): idx
        for idx, task in enumerate(tasks)
    }
    for future in concurrent.futures.as_completed(future_to_idx):
      idx = future_to_idx[future]
      task_results[idx] = future.result()

  for res in task_results:
    total_passed += res.get("effective_passed_count", res["passed_count"])
    total_criteria += res["total_count"]
    veto_banner = (
        " [VETOED BY INVARIANT FAILURE]" if res.get("invariant_veto") else ""
    )
    print(
        f"  Task {res['task_id']} [{res['target_skill']}] ({res['category']}):"
        f" Score = {res['score']:.2f}{veto_banner}"
        f" (raw passed: {res['passed_count']}/{res['total_count']})",
        flush=True,
    )
    for r in res["eval_results"]:
      status = "PASS" if r.get("passed") else "FAIL"
      crit_text = r.get("criterion", "")
      tier_str = r.get("tier", "QUALITY")
      prefix = "" if crit_text.startswith(f"[{tier_str}]") else f"[{tier_str}] "
      print(
          f"    [{status}] {prefix}{crit_text}: {r.get('reason')}",
          flush=True,
      )

  aggregate_score = total_passed / total_criteria if total_criteria > 0 else 0.0
  print(
      f"-> {split_name}{seed_label} Aggregate Score: {aggregate_score:.4f}"
      f" ({total_passed}/{total_criteria})",
      flush=True,
  )
  return aggregate_score, task_results


def validate_syntax_and_clip(
    seed_text: str, candidate_text: str
) -> tuple[bool, str]:
  if not (
      candidate_text.startswith("---")
      and "\nname:" in candidate_text
      and "\ndescription:" in candidate_text
  ):
    return False, "Malformed YAML frontmatter"

  seed_lines = seed_text.splitlines()
  cand_lines = candidate_text.splitlines()
  matcher = difflib.SequenceMatcher(None, seed_lines, cand_lines)
  ratio = matcher.ratio()
  diff_pct = (1.0 - ratio) * 100
  if diff_pct > 35.0:
    return (
        False,
        f"Edit distance too large: {diff_pct:.1f}% modified (limit is 35%)",
    )

  return True, f"Valid (diff: {diff_pct:.1f}%)"


def reflect_and_mutate(
    current_skill: str, failed_traces: list, val_score: float
) -> str:
  print(
      "\n--- Reflecting on Failure Traces & Synthesizing Generalized Patch ---",
      flush=True,
  )
  step_sizing = (
      "Current performance is below 0.70. Perform structural additions, missing"
      " procedural steps, and strict prerequisite barriers."
      if val_score < 0.70
      else (
          "Current performance is >= 0.70. Perform minimal surgical edits"
          " (targeted phrasing, single-line constraints, strict sequencing"
          " guards) while preserving working sections."
      )
  )

  reflection_prompt = f"""You are an expert prompt engineer and Skill Optimizer optimizing an Armature skill markdown file.

Failed Task Traces & Violated Criteria:
{json.dumps(failed_traces, indent=2)}

Optimization Guidelines:
{step_sizing}

Anti-Overfitting Rules:
1. NEVER inject scenario-specific keywords, concrete variable names, specific CSS classes, or test-specific strings into SKILL.md.
2. Formulate all additions as universal architectural principles, step sequencing constraints, or interaction protocols applicable across any project or domain.
3. Preserve all existing guardrails, step alignments, and interaction barriers.

Current SKILL.md Content:
\"\"\"markdown
{current_skill}
\"\"\"

Requirements for Candidate Mutation:
1. Maintain valid YAML frontmatter (name, description, persona).
2. Fix the underlying procedural or architectural gaps without overfitting to individual task strings.
3. Output the FULL updated SKILL.md in a single ```markdown ... ``` block without conversational preamble.
"""
  candidate_raw = call_gemini(
      OPTIMIZER_MODEL, reflection_prompt, temperature=0.2
  )
  match = re.search(r"```markdown\s*\n(.*?)\n```", candidate_raw, re.DOTALL)
  if match:
    return match.group(1).strip()
  match = re.search(r"```\s*\n(.*?)\n```", candidate_raw, re.DOTALL)
  if match:
    return match.group(1).strip()
  return candidate_raw.strip()


def compute_multi_seed_stats(scores: list) -> dict:
  if not scores:
    return {"mean": 0.0, "sd": 0.0, "ci_95_lower": 0.0, "ci_95_upper": 0.0}
  mean = statistics.mean(scores)
  sd = statistics.stdev(scores) if len(scores) > 1 else 0.0
  # t-critical value for K=3 (df=2) at 95% two-tailed is 4.303; for general K use 4.303 if K=3 else 1.96
  t_crit = (
      4.3027 if len(scores) == 3 else (2.7764 if len(scores) == 5 else 1.96)
  )
  margin = t_crit * (sd / math.sqrt(len(scores))) if len(scores) > 1 else 0.0
  return {
      "mean": mean,
      "sd": sd,
      "ci_95_lower": max(0.0, mean - margin),
      "ci_95_upper": min(1.0, mean + margin),
  }


def main():
  parser = argparse.ArgumentParser(
      description="Armature SkillOpt Benchmarking & Optimization"
  )
  parser.add_argument(
      "--target",
      default="all",
      help=(
          "Target skill path relative to armature root, skill name, or"
          " comma-separated list of skill names (e.g."
          " 'arm-review,arm-new-track' or 'all')"
      ),
  )
  parser.add_argument(
      "--eval_only",
      action="store_true",
      help="Run evaluation benchmarks without mutation",
  )
  parser.add_argument(
      "--optimize",
      action="store_true",
      help="Run full SkillOpt optimization loop",
  )
  parser.add_argument(
      "--epochs",
      type=int,
      default=2,
      help="Number of optimization epochs (default: 2)",
  )
  parser.add_argument(
      "--seeds",
      type=int,
      default=1,
      help="Number of distinct random seeds / evaluation passes (default: 1)",
  )
  parser.add_argument(
      "--workers",
      type=int,
      default=8,
      help="Number of concurrent worker threads (default: 8)",
  )
  parser.add_argument(
      "--task_filter",
      default=None,
      help="Optional comma-separated task ID prefixes/substrings to evaluate",
  )
  parser.add_argument(
      "--verify_schema",
      action="store_true",
      help=(
          "Verify JSONL syntax and task schema integrity across train.jsonl and"
          " val.jsonl"
      ),
  )
  args = parser.parse_args()

  train_ok, train_errs = verify_jsonl_schema(TRAIN_PATH, expected_count=46)
  val_ok, val_errs = verify_jsonl_schema(VAL_PATH, expected_count=38)

  if not train_ok or not val_ok:
    print("❌ [Schema Verification FAILED]", file=sys.stderr)
    for err in train_errs + val_errs:
      print(f"  - {err}", file=sys.stderr)
    sys.exit(1)

  if args.verify_schema:
    print(
        "✅ [Schema Verification PASSED] All 46 train tasks and 38 val tasks"
        " valid."
    )
    sys.exit(0)

  target_skill_name = "all"
  skill_text = ""
  target_path = args.target

  if args.target != "all" and "," not in args.target:
    target_path = resolve_skill_path(args.target)
    if not os.path.exists(target_path):
      sys.exit(f"Target skill path does not exist: {target_path}")
    target_skill_name = (
        os.path.basename(os.path.dirname(target_path))
        if target_path.endswith("SKILL.md")
        else args.target
    )
    with open(target_path, "r", encoding="utf-8") as f:
      skill_text = f.read()

  print("=== Armature SkillOpt Evaluation Runner ===", flush=True)
  print(
      f"Target: {target_path} | Seeds: {args.seeds} | Workers: {args.workers}"
  )
  print(f"Target Model: {TARGET_MODEL} | Optimizer Model: {OPTIMIZER_MODEL}")

  train_tasks = load_tasks(TRAIN_PATH, args.target, args.task_filter)
  val_tasks = load_tasks(VAL_PATH, args.target, args.task_filter)
  print(
      f"Loaded {len(train_tasks)} train tasks and {len(val_tasks)} val tasks."
  )

  seed_list = [42 + i for i in range(args.seeds)] if args.seeds > 1 else [None]

  all_train_scores = []
  all_val_scores = []
  seed_runs = []

  for idx, seed_val in enumerate(seed_list, start=1):
    seed_tag = (
        f"Seed {idx} (seed={seed_val})"
        if seed_val is not None
        else "Single Pass"
    )
    print(f"\n================ {seed_tag} ================", flush=True)
    tr_score, tr_res = run_benchmark(
        skill_text,
        target_skill_name,
        train_tasks,
        f"TRAIN ({seed_tag})",
        seed=seed_val,
        max_workers=args.workers,
    )
    v_score, v_res = run_benchmark(
        skill_text,
        target_skill_name,
        val_tasks,
        f"VAL ({seed_tag})",
        seed=seed_val,
        max_workers=args.workers,
    )
    all_train_scores.append(tr_score)
    all_val_scores.append(v_score)
    seed_runs.append({
        "seed_index": idx,
        "seed": seed_val,
        "train_score": tr_score,
        "val_score": v_score,
        "train_results": tr_res,
        "val_results": v_res,
    })

  train_stats = compute_multi_seed_stats(all_train_scores)
  val_stats = compute_multi_seed_stats(all_val_scores)

  print("\n=== Multi-Seed Statistical Summary ===", flush=True)
  print(
      f"TRAIN ({len(seed_list)} seeds): Mean = {train_stats['mean']:.4f} ±"
      f" {train_stats['sd']:.4f} | 95% CI = [{train_stats['ci_95_lower']:.4f},"
      f" {train_stats['ci_95_upper']:.4f}]",
      flush=True,
  )
  print(
      f"VAL   ({len(seed_list)} seeds): Mean = {val_stats['mean']:.4f} ±"
      f" {val_stats['sd']:.4f} | 95% CI = [{val_stats['ci_95_lower']:.4f},"
      f" {val_stats['ci_95_upper']:.4f}]",
      flush=True,
  )

  results = {
      "target": target_path,
      "seeds": args.seeds,
      "train_stats": train_stats,
      "val_stats": val_stats,
      "baseline": {
          "train_score": train_stats["mean"],
          "val_score": val_stats["mean"],
      },
      "seed_runs": seed_runs,
      "train_results": seed_runs[0]["train_results"] if seed_runs else [],
      "val_results": seed_runs[0]["val_results"] if seed_runs else [],
  }

  with open(RESULTS_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

  print(f"\nResults saved to: {RESULTS_PATH}", flush=True)

  train_score = train_stats["mean"]
  val_score = val_stats["mean"]
  train_res = seed_runs[0]["train_results"] if seed_runs else []

  if (
      args.optimize
      and args.target != "all"
      and "," not in args.target
      and val_score < 1.0
  ):
    best_skill = skill_text
    best_val_score = val_score

    for epoch in range(1, args.epochs + 1):
      print(f"\n=== Optimization Epoch {epoch}/{args.epochs} ===")
      failed_traces = []
      for sr in seed_runs:
        for tr in sr["train_results"]:
          failed_criteria = [
              r for r in tr["eval_results"] if not r.get("passed", False)
          ]
          if failed_criteria:
            failed_traces.append({
                "task_id": tr["task_id"],
                "seed": sr["seed"],
                "category": tr["category"],
                "failed_criteria": failed_criteria,
                "rollout_sample": tr["rollout_sample"],
            })

      if not failed_traces:
        print("All train criteria passed across all seeds.")
        break

      candidate = reflect_and_mutate(best_skill, failed_traces, best_val_score)
      valid, msg = validate_syntax_and_clip(best_skill, candidate)
      print(f"Syntax & Clip Guard: {msg}")
      if not valid:
        continue

      cand_val_scores = []
      for s_val in seed_list:
        cv_score, _ = run_benchmark(
            candidate,
            target_skill_name,
            val_tasks,
            f"VAL (Candidate Epoch {epoch}, seed={s_val})",
            seed=s_val,
            max_workers=args.workers,
        )
        cand_val_scores.append(cv_score)
      cand_val_mean = statistics.mean(cand_val_scores)
      if cand_val_mean > best_val_score:
        print(
            f"Accepted candidate: {best_val_score:.4f} -> {cand_val_mean:.4f}"
        )
        best_skill = candidate
        best_val_score = cand_val_mean

    best_out_path = os.path.join(EVALS_DIR, f"best_{target_skill_name}.md")
    with open(best_out_path, "w", encoding="utf-8") as f:
      f.write(best_skill)
    print(f"Optimized skill written to: {best_out_path}")


if __name__ == "__main__":
  main()
