#!/usr/bin/env python3
"""SkillOpt Multi-Seed Evaluation & Optimization Runner for Two-Tier Drift Auto-Update.

Evaluates Auto-Update & Notify by Default on Tier A Mechanical Drift and
Tier B Semantic/Boundary Safeguards across:
  - rules/armature_protocol.md
  - rules/armature_cdd_protocols.md
  - rules/armature_workspace.md
  - skills/arm-status/SKILL.md
  - skills/arm-drift/SKILL.md
  - skills/arm-implement/SKILL.md

Supports:
  --phase baseline : Evaluates parent commit version via `git show` across K=3
  seeds.
  --phase eval     : Evaluates current working copy across K=3 seeds.
  --phase both     : Runs both baseline and candidate evaluation across K=3
  seeds.
"""

import argparse
import concurrent.futures
import difflib
import json
import math
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

# pylint: disable=broad-exception-caught,missing-function-docstring,g-bare-generic

socket.setdefaulttimeout(90)

TARGET_MODEL = "gemini-3.5-flash"
FALLBACK_TARGET_MODEL = "gemini-flash-latest"
JUDGE_MODEL = "gemini-3.1-pro-preview"
FALLBACK_JUDGE_MODEL = "gemini-3.5-flash"
API_KEY = os.environ.get("GEMINI_API_KEY")

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
ARMATURE_ROOT = os.path.abspath(os.path.join(EVALS_DIR, "..", ".."))

PROTOCOL_REL = "rules/armature_protocol.md"
CDD_PROTOCOLS_REL = "rules/armature_cdd_protocols.md"
GOOGLE3_REL = "rules/armature_workspace.md"
ARM_STATUS_REL = "skills/arm-status/SKILL.md"
ARM_DRIFT_REL = "skills/arm-drift/SKILL.md"
ARM_IMPLEMENT_REL = "skills/arm-implement/SKILL.md"

TRAIN_PATH = os.path.join(EVALS_DIR, "tasks", "train_drift_auto_update.jsonl")
VAL_PATH = os.path.join(EVALS_DIR, "tasks", "val_drift_auto_update.jsonl")
RESULTS_JSON_PATH = os.path.join(
    EVALS_DIR, "drift_auto_update_eval_results.json"
)
REPORT_MD_PATH = os.path.join(EVALS_DIR, "skillopt_report_drift_auto_update.md")

TOOL_DECLARATIONS = [{
    "functionDeclarations": [
        {
            "name": "ask_question",
            "description": (
                "Ask the user one or more multiple-choice questions via"
                " interactive UI modal."
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
            "description": "Create or overwrite a file with new content.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "TargetFile": {"type": "STRING"},
                    "CodeContent": {"type": "STRING"},
                    "Overwrite": {"type": "BOOLEAN"},
                },
                "required": ["TargetFile", "CodeContent"],
            },
        },
        {
            "name": "replace_file_content",
            "description": "Replace a substring in an existing file.",
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
        {
            "name": "run_command",
            "description": (
                "Execute a non-interactive shell command (e.g., VCS"
                " diff/status)."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "CommandLine": {"type": "STRING"},
                },
                "required": ["CommandLine"],
            },
        },
        {
            "name": "invoke_subagent",
            "description": "Launch a background subagent.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "TypeName": {"type": "STRING"},
                    "Role": {"type": "STRING"},
                    "Prompt": {"type": "STRING"},
                },
                "required": ["TypeName", "Role", "Prompt"],
            },
        },
        {
            "name": "swarm",
            "description": "Manage a multi-agent swarm.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "action": {"type": "STRING"},
                    "name": {"type": "STRING"},
                    "brief": {"type": "STRING"},
                },
                "required": ["action"],
            },
        },
    ]
}]


def load_file_version(rel_path: str, use_hg_cat: bool = False) -> str:
  abs_path = os.path.join(ARMATURE_ROOT, rel_path)
  if use_hg_cat:
    try:
      out = subprocess.check_output(
          ["git", "show", f"origin/main:{rel_path}"],
          cwd=ARMATURE_ROOT,
          stderr=subprocess.DEVNULL,
      )
      return out.decode("utf-8")
    except Exception:
      pass
  with open(abs_path, "r", encoding="utf-8") as f:
    return f.read()


def load_bundle(use_hg_cat: bool = False) -> dict[str, str]:
  return {
      "protocol": load_file_version(PROTOCOL_REL, use_hg_cat=use_hg_cat),
      "cdd_protocols": load_file_version(
          CDD_PROTOCOLS_REL, use_hg_cat=use_hg_cat
      ),
      "workspace": load_file_version(GOOGLE3_REL, use_hg_cat=use_hg_cat),
      "arm-status": load_file_version(ARM_STATUS_REL, use_hg_cat=use_hg_cat),
      "arm-drift": load_file_version(ARM_DRIFT_REL, use_hg_cat=use_hg_cat),
      "arm-implement": load_file_version(
          ARM_IMPLEMENT_REL, use_hg_cat=use_hg_cat
      ),
  }


def _single_gemini_request(
    model: str,
    contents: list[dict],
    system_instruction: str | None = None,
    temperature: float = 0.2,
    use_tools: bool = False,
    json_mode: bool = False,
    seed: int | None = None,
    max_retries: int = 6,
) -> tuple[list[str], list[dict], list[dict]]:
  if not API_KEY:
    sys.exit("ERROR: Missing GEMINI_API_KEY in environment.")
  for attempt in range(1, max_retries + 1):
    active_model = model
    if attempt >= 2:
      active_model = (
          FALLBACK_JUDGE_MODEL if json_mode else FALLBACK_TARGET_MODEL
      )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={API_KEY}"
    gen_cfg: dict[str, object] = {
        "temperature": temperature,
        "maxOutputTokens": 8192,
    }
    if seed is not None:
      gen_cfg["seed"] = seed
    if json_mode:
      gen_cfg["responseMimeType"] = "application/json"
    payload: dict[str, object] = {
        "contents": contents,
        "generationConfig": gen_cfg,
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
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
      payload["tools"] = TOOL_DECLARATIONS

    data = json.dumps(payload).encode("utf-8")
    try:
      req = urllib.request.Request(
          url, data=data, headers={"Content-Type": "application/json"}
      )
      with urllib.request.urlopen(req, timeout=90) as resp:
        res_json = json.loads(resp.read().decode("utf-8"))
        candidates = res_json.get("candidates", [])
        if candidates and "content" in candidates[0]:
          parts = candidates[0]["content"].get("parts", [])
          text_out = []
          tool_calls = []
          for p in parts:
            if "text" in p and p["text"]:
              text_out.append(p["text"])
            if "functionCall" in p:
              tool_calls.append(p["functionCall"])
          return text_out, tool_calls, parts
        return [], [], []
    except Exception as e:
      if attempt == max_retries:
        print(f"API error on {active_model}: {e}", file=sys.stderr)
        return [f"[ERROR: {e}]"], [], []
      time.sleep(5 * attempt)
  return [], [], []


def call_gemini(
    model: str,
    prompt: str,
    system_instruction: str | None = None,
    temperature: float = 0.2,
    use_tools: bool = False,
    json_mode: bool = False,
    seed: int | None = None,
    max_retries: int = 5,
) -> tuple[str, list[dict]]:
  contents: list[dict] = [{"role": "user", "parts": [{"text": prompt}]}]
  all_texts, all_tool_calls, raw_parts = _single_gemini_request(
      model=model,
      contents=contents,
      system_instruction=system_instruction,
      temperature=temperature,
      use_tools=use_tools,
      json_mode=json_mode,
      seed=seed,
      max_retries=max_retries,
  )
  # Simulate up to 2 continuation turns if the model emitted initial tool calls
  # (e.g., run_command or partial file edits) or emitted markdown text first
  # before emitting the required write_to_file / ask_question tool calls.
  is_read_only_check = "--check" in prompt or "--report-only" in prompt
  for _ in range(2):
    if not (use_tools and raw_parts):
      break
    has_visible_text = len("\n".join(all_texts).strip()) >= 120
    only_ran_cmd = all_tool_calls and all(
        tc.get("name") == "run_command" for tc in all_tool_calls
    )
    has_file_op = any(
        tc.get("name") in ("write_to_file", "replace_file_content")
        for tc in all_tool_calls
    )
    mutated_targets = [
        tc.get("args", {}).get("TargetFile", "")
        for tc in all_tool_calls
        if tc.get("name") in ("write_to_file", "replace_file_content")
    ]
    missing_report_artifact = (not is_read_only_check) and not any(
        "arm_drift.md" in t or "arm_status.md" in t for t in mutated_targets
    )
    combined_text_so_far = "\n".join(all_texts)
    needs_ask_question = (
        not is_read_only_check
        and any(
            kw in combined_text_so_far
            for kw in (
                "[DRIFT] Stale Legacy Fence",
                "Stale Legacy Fence",
                "Semantic Drift Requires Decision",
                "ADR 0003",
                "ADR 0002",
            )
        )
        and not any(tc.get("name") == "ask_question" for tc in all_tool_calls)
    )
    last_turn_tcs = [
        p["functionCall"] for p in raw_parts if "functionCall" in p
    ]
    if (
        only_ran_cmd
        or (all_tool_calls and not has_visible_text)
        or (has_visible_text and (not has_file_op) and (not is_read_only_check))
        or (has_file_op and missing_report_artifact)
        or (has_file_op and needs_ask_question)
    ):
      if last_turn_tcs:
        fn_responses = []
        for tc in last_turn_tcs:
          fn_responses.append({
              "functionResponse": {
                  "name": tc.get("name"),
                  "response": {
                      "status": "success",
                      "output": (
                          "Command/tool succeeded. Now complete this turn by"
                          " outputting your full visible markdown report in"
                          " chat (if not yet printed), applying all required"
                          " file updates via write_to_file /"
                          " replace_file_content (including Tier A mechanical"
                          " drift files and arm_drift.md / arm_status.md), and"
                          " invoking ask_question if required by the"
                          " protocol."
                      ),
                  },
              }
          })
        contents.append({"role": "model", "parts": raw_parts})
        contents.append({"role": "user", "parts": fn_responses})
      else:
        contents.append({"role": "model", "parts": raw_parts})
        contents.append({
            "role": "user",
            "parts": [{
                "text": (
                    "[System Harness Reminder: Emit the required native tool"
                    " call(s) (write_to_file / replace_file_content for Tier A"
                    " mechanical auto-updates and arm_drift.md / arm_status.md,"
                    " plus ask_question if required) to complete this turn.]"
                )
            }],
        })
      more_texts, more_tcs, raw_parts = _single_gemini_request(
          model=model,
          contents=contents,
          system_instruction=system_instruction,
          temperature=temperature,
          use_tools=use_tools,
          json_mode=json_mode,
          seed=seed,
          max_retries=max_retries,
      )
      all_texts.extend(more_texts)
      all_tool_calls.extend(more_tcs)
    else:
      break
  return "\n".join(all_texts), all_tool_calls


def evaluate_invariants(
    task: dict, text: str, tool_calls: list[dict]
) -> list[str]:
  vetoes = []
  inv_list = task.get("invariants", [])
  combined_surface = text + "\n" + json.dumps(tool_calls)

  mutated_files = []
  mutated_payloads = []
  for tc in tool_calls:
    if tc.get("name") in ("write_to_file", "replace_file_content"):
      args = tc.get("args", {})
      tf = args.get("TargetFile", "")
      if tf:
        mutated_files.append(tf)
        mutated_payloads.append((
            tf,
            args.get("CodeContent", "")
            + "\n"
            + args.get("ReplacementContent", ""),
        ))

  for inv in inv_list:
    if inv == "mutates_tracks_md":
      tracks_edits = [
          content for tf, content in mutated_payloads if "tracks.md" in tf
      ]
      if not tracks_edits:
        vetoes.append(
            "mutates_tracks_md: Did not call write_to_file or"
            " replace_file_content on armature/tracks.md to auto-update"
            " mechanical drift"
        )
      elif not any("[x]" in c for c in tracks_edits):
        vetoes.append(
            "mutates_tracks_md: Mutated tracks.md but did not update completed"
            " track status to [x]"
        )
    elif inv == "writes_arm_status_md":
      if not any("arm_status.md" in mf for mf in mutated_files):
        vetoes.append(
            "writes_arm_status_md: Did not call write_to_file on arm_status.md"
        )
    elif inv == "writes_arm_drift_md":
      if not any("arm_drift.md" in mf for mf in mutated_files):
        vetoes.append(
            "writes_arm_drift_md: Did not call write_to_file on arm_drift.md"
        )
    elif inv == "mutates_mechanical_drift_files":
      mech_targets = [
          mf
          for mf in mutated_files
          if any(
              k in mf
              for k in (
                  "index.md",
                  "terms.md",
                  ".api_surface_cache.json",
                  "install.sh",
                  "plugin.json",
              )
          )
      ]
      if len(set(mech_targets)) < 2:
        vetoes.append(
            "mutates_mechanical_drift_files: Did not auto-update mechanical"
            f" drift files in-place (mutated: {mutated_files})"
        )
    elif inv == "refreshes_arm_status_md_in_lockstep":
      status_edits = [
          content for tf, content in mutated_payloads if "arm_status.md" in tf
      ]
      if not status_edits:
        vetoes.append(
            "refreshes_arm_status_md_in_lockstep: Did not update arm_status.md"
            " in lockstep"
        )
      elif not any(
          re.search(r"(?i)fixpoint\s+reached", c) for c in status_edits
      ):
        vetoes.append(
            "refreshes_arm_status_md_in_lockstep: Updated arm_status.md but did"
            " not set Fixpoint Health to Fixpoint Reached"
        )
    elif inv == "reports_auto_updated_fixpoint":
      has_fixpoint = bool(
          re.search(r"(?i)fixpoint\s+reached", combined_surface)
      )
      has_auto_note = bool(
          re.search(
              r"(?i)auto[- ]?(?:updat|heal|fix|reconcil|appl)",
              combined_surface,
          )
      )
      has_passive_punt = bool(
          re.search(
              r"(?i)drift\s+detected\s*\([^)]*run\s+`?/arm-drift`?",
              combined_surface,
          )
      )
      if not (has_fixpoint and has_auto_note) or has_passive_punt:
        vetoes.append(
            "reports_auto_updated_fixpoint: Missing 'Fixpoint Reached' with"
            " auto-updated notification or left passive 'Drift Detected — run"
            " /arm-drift' warning"
        )
    elif inv == "unambiguous_pending_specs_only_status":
      if not re.search(r"(?i)specs\s+only|not\s+started", combined_surface):
        vetoes.append(
            "unambiguous_pending_specs_only_status: Missing unambiguous"
            " 'Pending (Specs Only — Not Started)' status label on unstarted"
            " track"
        )
    elif inv == "has_ask_question_tool":
      if not any(tc.get("name") == "ask_question" for tc in tool_calls):
        vetoes.append(
            "has_ask_question_tool: Missing required ask_question tool call"
        )
    elif inv in ("no_ask_question_on_tier_a_drift", "no_ask_question_tool"):
      if any(tc.get("name") == "ask_question" for tc in tool_calls):
        vetoes.append(
            f"{inv}: Illegally invoked ask_question permission modal when"
            " prohibited"
        )
    elif inv == "no_spec_or_adr_mutation":
      bad = [
          mf
          for mf in mutated_files
          if "spec.md" in mf
          or "/adr/" in mf
          or "0002" in mf
          or "0003" in mf
          or "0005" in mf
      ]
      if bad:
        vetoes.append(
            "no_spec_or_adr_mutation: Illegally mutated approved spec/ADR:"
            f" {bad}"
        )
    elif inv == "zero_repo_file_mutations":
      bad = [
          mf
          for mf in mutated_files
          if any(
              k in mf
              for k in (
                  "tracks.md",
                  "install.sh",
                  "index.md",
                  "terms.md",
                  "plugin.json",
              )
          )
      ]
      if bad:
        vetoes.append(
            "zero_repo_file_mutations: Illegally mutated repository files"
            f" during read-only --check mode: {bad}"
        )
    elif inv == "reports_ci_check_failure":
      if not re.search(r"\[(?:ERROR|WARNING)\]", combined_surface):
        vetoes.append(
            "reports_ci_check_failure: Missing [ERROR] or [WARNING] drift tag"
            " in --check report"
        )
    elif inv == "has_legacy_fence_banner":
      if not re.search(r"(?i)Working\s+in\s+`?[^`\n]+`?", text):
        vetoes.append(
            "has_legacy_fence_banner: Missing once-per-session Turn 1 legacy"
            " fence callout banner"
        )
    elif inv == "mutates_index_md_only":
      if not any("index.md" in mf for mf in mutated_files):
        vetoes.append(
            "mutates_index_md_only: Did not auto-update Tier A"
            " armature/index.md"
        )
      bad = [
          mf
          for mf in mutated_files
          if any(
              k in mf
              for k in (
                  ".api_surface_cache.json",
                  "legacy_v1_auth",
                  "tech-stack.md",
                  "v1_soap_calendar",
              )
          )
      ]
      if bad:
        vetoes.append(
            "mutates_index_md_only: Illegally mutated Tier B / fenced file(s)"
            f" without authorization: {bad}"
        )
    elif inv == "flags_breaking_api_major_semver":
      if not (
          re.search(r"verifyTenantSignature", combined_surface)
          and re.search(r"(?i)MAJOR|BREAKING\s+CHANGE", combined_surface)
      ):
        vetoes.append(
            "flags_breaking_api_major_semver: Did not flag removed"
            " verifyTenantSignature with MAJOR / BREAKING CHANGE version bump"
        )
    elif inv == "flags_blocking_legacy_fence":
      if not re.search(
          r"(?i)\[BLOCKING\].*Legacy\s+Fence|Legacy\s+Fence\s+Violation",
          combined_surface,
      ):
        vetoes.append(
            "flags_blocking_legacy_fence: Missing [BLOCKING] Legacy Fence"
            " Violation alert"
        )
    elif inv == "flags_diff_to_tag_warning":
      if not (
          re.search(r"\[WARNING\]", combined_surface)
          and re.search(
              r"(?i)Diff-to-Tag|3-Part\s+Fixture\s+Triad", combined_surface
          )
      ):
        vetoes.append(
            "flags_diff_to_tag_warning: Missing [WARNING] Diff-to-Tag Mismatch"
            " escalating to 3-Part Fixture Triad"
        )
    elif inv == "flags_stale_legacy_fence_and_preserves_active":
      if not (
          re.search(r"(?i)Stale\s+Legacy\s+Fence", combined_surface)
          and re.search(r"v1_soap_calendar", combined_surface)
          and re.search(r"legacy_hl7_adapter", combined_surface)
      ):
        vetoes.append(
            "flags_stale_legacy_fence_and_preserves_active: Missing [DRIFT]"
            " Stale Legacy Fence alert or active fence preservation note"
        )
    elif inv == "reports_tier_a_auto_updated_and_tier_b_decision_needed":
      has_tier_a = bool(
          re.search(r"001-mutating-webhook-tls", combined_surface)
          and re.search(r"(?i)auto[- ]?(?:updat|heal|fix)", combined_surface)
      )
      has_tier_b = bool(
          re.search(
              r"(?i)0002|FailurePolicy|Semantic\s+Drift", combined_surface
          )
      )
      if not (has_tier_a and has_tier_b):
        vetoes.append(
            "reports_tier_a_auto_updated_and_tier_b_decision_needed: Did not"
            " report both the auto-updated Tier A track and the Tier B ADR"
            " contradiction"
        )
    elif inv == "no_subagent_or_swarm_dispatch":
      bad_tc = [
          tc.get("name")
          for tc in tool_calls
          if tc.get("name") in ("invoke_subagent", "swarm")
      ]
      if bad_tc:
        vetoes.append(
            f"no_subagent_or_swarm_dispatch: Illegally dispatched {bad_tc} on"
            " micro-task"
        )
    elif inv == "no_bare_tool_call":
      if len(text.strip()) < 120:
        vetoes.append(
            "no_bare_tool_call: Emitted bare tool call with insufficient"
            " visible markdown text"
        )
  return vetoes


def judge_qualities(
    task: dict, text: str, tool_calls: list[dict]
) -> tuple[float, list[dict]]:
  qualities = task.get("qualities", [])
  if not qualities:
    return 1.0, []
  judge_prompt = f"""You are an impartial, rigorous evaluation judge. Evaluate whether the agent's response and tool calls satisfy each quality criterion.

Task Prompt:
{task['prompt']}

Agent Markdown Response:
{text}

Agent Tool Calls:
{json.dumps(tool_calls, indent=2)}

Quality Criteria to evaluate (return 1.0 if fully met, 0.5 if partially met, 0.0 if not met):
"""
  for idx, q in enumerate(qualities):
    judge_prompt += f"{idx+1}. {q}\n"
  judge_prompt += """
Respond ONLY with valid JSON matching this schema:
{"scores": [{"criterion_index": 1, "score": 1.0, "reason": "brief explanation"}]}
"""
  out, _ = call_gemini(
      JUDGE_MODEL,
      judge_prompt,
      temperature=0.0,
      use_tools=False,
      json_mode=True,
  )
  try:
    decoder = json.JSONDecoder(strict=False)
    for m in re.finditer(r"\{", out):
      try:
        parsed, _ = decoder.raw_decode(out[m.start() :])
        if isinstance(parsed, dict) and "scores" in parsed:
          scores_list = parsed.get("scores", [])
          if scores_list and len(scores_list) == len(qualities):
            avg_q = sum(float(s.get("score", 0.0)) for s in scores_list) / len(
                qualities
            )
            return min(1.0, max(0.0, avg_q)), scores_list
      except Exception:
        continue
  except Exception as e:
    print(f"Judge parse error on {task['id']}: {e}", file=sys.stderr)
  return 0.0, [
      {"criterion_index": 0, "score": 0.0, "reason": "Judge parse failure"}
  ]


def evaluate_single_rollout(
    bundle: dict[str, str], task: dict, seed: int
) -> dict:
  skill_name = task.get("target_skill", "arm-drift")
  skill_text = bundle.get(skill_name, bundle["arm-drift"])
  sys_prompt = f"""You are an AI coding agent operating inside a multi-service Armature workspace. Follow these rules and skill instructions strictly:

=== UNIVERSAL PROTOCOL (rules/armature_protocol.md) ===
{bundle['protocol']}

=== CDD PROTOCOLS (rules/armature_cdd_protocols.md) ===
{bundle['cdd_protocols']}

=== GOOGLE3 HOST ADAPTER (rules/armature_workspace.md) ===
{bundle['workspace']}

=== ACTIVE SKILL ({skill_name}) ===
{skill_text}
"""
  text, tool_calls = call_gemini(
      TARGET_MODEL,
      task["prompt"],
      system_instruction=sys_prompt,
      temperature=0.15,
      use_tools=True,
      seed=seed,
  )
  vetoes = evaluate_invariants(task, text, tool_calls)
  if vetoes:
    return {
        "task_id": task["id"],
        "seed": seed,
        "vetoes": vetoes,
        "quality_score": 0.0,
        "final_score": 0.0,
        "passed": False,
        "text_preview": text[:450],
    }
  q_score, q_details = judge_qualities(task, text, tool_calls)
  return {
      "task_id": task["id"],
      "seed": seed,
      "vetoes": [],
      "quality_score": q_score,
      "final_score": q_score,
      "passed": q_score >= 0.85,
      "q_details": q_details,
      "text_preview": text[:450],
  }


def evaluate_split(
    bundle: dict[str, str],
    tasks: list[dict],
    split_name: str,
    num_seeds: int = 3,
) -> dict:
  print(
      f"[{split_name}] Launching {len(tasks)} tasks across K={num_seeds} seeds"
      f" ({len(tasks)*num_seeds} rollouts)...",
      flush=True,
  )
  rollouts = []
  jobs = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    for seed in range(1, num_seeds + 1):
      for task in tasks:
        jobs.append(
            executor.submit(evaluate_single_rollout, bundle, task, seed)
        )
    completed = 0
    total = len(jobs)
    for future in concurrent.futures.as_completed(jobs):
      res = future.result()
      rollouts.append(res)
      completed += 1
      print(
          f"[{split_name}] Completed {completed}/{total} rollouts (Last:"
          f" {res['task_id']} seed={res['seed']}"
          f" score={res['final_score']:.2f} vetoes={len(res['vetoes'])})",
          flush=True,
      )
      if res["vetoes"]:
        print(f"  -> VETOES on {res['task_id']}: {res['vetoes']}", flush=True)

  seed_scores = []
  seed_vetoes = []
  for seed in range(1, num_seeds + 1):
    s_rolls = [r for r in rollouts if r["seed"] == seed]
    mean_s = sum(r["final_score"] for r in s_rolls) / len(s_rolls)
    seed_scores.append(mean_s)
    seed_vetoes.append(sum(len(r["vetoes"]) for r in s_rolls))

  overall_mean = sum(seed_scores) / len(seed_scores)
  variance = sum((s - overall_mean) ** 2 for s in seed_scores) / max(
      1, len(seed_scores) - 1
  )
  std_dev = math.sqrt(variance)
  t_val = 1.886 if num_seeds == 3 else 1.645
  lb_90 = overall_mean - t_val * (std_dev / math.sqrt(num_seeds))

  return {
      "split": split_name,
      "mean_score": overall_mean,
      "std_dev": std_dev,
      "lb_90": lb_90,
      "seed_scores": seed_scores,
      "seed_vetoes": seed_vetoes,
      "total_vetoes": sum(seed_vetoes),
      "rollouts": rollouts,
  }


def load_tasks(path: str) -> list[dict]:
  tasks = []
  with open(path, "r", encoding="utf-8") as f:
    for line in f:
      if line.strip():
        tasks.append(json.loads(line))
  return tasks


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "--phase",
      choices=["baseline", "eval", "both"],
      default="both",
      help="Which evaluation phase to run.",
  )
  parser.add_argument("--seeds", type=int, default=3)
  args = parser.parse_args()

  train_tasks = load_tasks(TRAIN_PATH)
  val_tasks = load_tasks(VAL_PATH)

  results: dict[str, object] = {}
  if os.path.exists(RESULTS_JSON_PATH):
    try:
      with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
        results = json.load(f)
    except Exception:
      results = {}

  if args.phase in ("baseline", "both"):
    print(
        "=== RUNNING BASELINE EVALUATION (git show origin/main) ===",
        flush=True,
    )
    base_bundle = load_bundle(use_hg_cat=True)
    base_train = evaluate_split(
        base_bundle, train_tasks, "TRAIN_BASE", num_seeds=args.seeds
    )
    base_val = evaluate_split(
        base_bundle, val_tasks, "VAL_BASE", num_seeds=args.seeds
    )
    results["baseline"] = {"train": base_train, "val": base_val}
    with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
      json.dump(results, f, indent=2)
    print(
        f"Baseline Train Mean: {base_train['mean_score']:.4f} (Vetoes:"
        f" {base_train['total_vetoes']})",
        flush=True,
    )
    print(
        f"Baseline Val Mean:   {base_val['mean_score']:.4f} (LB90:"
        f" {base_val['lb_90']:.4f}, Vetoes: {base_val['total_vetoes']})",
        flush=True,
    )

  if args.phase in ("eval", "both"):
    print("=== RUNNING CANDIDATE EVALUATION (working copy) ===", flush=True)
    cand_bundle = load_bundle(use_hg_cat=False)
    base_bundle = load_bundle(use_hg_cat=True)
    cand_train = evaluate_split(
        cand_bundle, train_tasks, "TRAIN_CAND", num_seeds=args.seeds
    )
    cand_val = evaluate_split(
        cand_bundle, val_tasks, "VAL_CAND", num_seeds=args.seeds
    )
    results["candidate"] = {"train": cand_train, "val": cand_val}

    base_tokens = sum(len(v.split()) for v in base_bundle.values())
    cand_tokens = sum(len(v.split()) for v in cand_bundle.values())
    token_ratio = cand_tokens / max(1, base_tokens)

    base_lines = "\n".join(base_bundle.values()).splitlines()
    cand_lines = "\n".join(cand_bundle.values()).splitlines()
    similarity = difflib.SequenceMatcher(None, base_lines, cand_lines).ratio()
    edit_ratio = 1.0 - similarity

    base_val_mean = (
        results.get("baseline", {}).get("val", {}).get("mean_score", 0.0)
    )
    results["guard_metrics"] = {
        "base_tokens": base_tokens,
        "cand_tokens": cand_tokens,
        "token_ratio": token_ratio,
        "line_similarity": similarity,
        "line_edit_ratio": edit_ratio,
        "passed_clip_guard": edit_ratio <= 0.35,
        "passed_token_bloat_guard": token_ratio <= 1.20,
        "passed_val_gating": (
            cand_val["lb_90"] >= base_val_mean and cand_val["total_vetoes"] == 0
        ),
    }
    with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
      json.dump(results, f, indent=2)
    print(
        f"Candidate Train Mean: {cand_train['mean_score']:.4f} (Vetoes:"
        f" {cand_train['total_vetoes']})",
        flush=True,
    )
    print(
        f"Candidate Val Mean:   {cand_val['mean_score']:.4f} (LB90:"
        f" {cand_val['lb_90']:.4f}, Vetoes: {cand_val['total_vetoes']})",
        flush=True,
    )
    print(
        f"Token Ratio: {token_ratio:.4f} (<=1.20) | Line Edit Ratio:"
        f" {edit_ratio:.4f} (<=0.35)",
        flush=True,
    )


if __name__ == "__main__":
  main()
