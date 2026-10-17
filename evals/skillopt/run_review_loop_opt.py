#!/usr/bin/env python3
"""SkillOpt Multi-Seed Evaluation & Optimization Runner for ADR 0015 Review Loop.

Evaluates the 3-Tier Multi-Expert Review-and-Repair Loop across:
  - rules/armature_protocol.md
  - skills/arm-review/SKILL.md
  - skills/arm-implement/SKILL.md

Supports:
  --phase baseline : Evaluates parent commit version via `git show` across K=3 seeds.
  --phase eval     : Evaluates current working copy across K=3 seeds.
  --phase both     : Evaluates both baseline and working copy.
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

socket.setdefaulttimeout(90)

TARGET_MODEL = "gemini-3.5-flash"
FALLBACK_TARGET_MODEL = "gemini-3.5-flash"
JUDGE_MODEL = "gemini-3.1-pro-preview"
FALLBACK_JUDGE_MODEL = "gemini-3.5-flash"
API_KEY = os.environ.get("GEMINI_API_KEY")

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
ARMATURE_ROOT = os.path.abspath(os.path.join(EVALS_DIR, "..", ".."))

PROTOCOL_REL = "rules/armature_protocol.md"
ARM_REVIEW_REL = "skills/arm-review/SKILL.md"
ARM_IMPLEMENT_REL = "skills/arm-implement/SKILL.md"

TRAIN_PATH = os.path.join(EVALS_DIR, "tasks", "train_review_loop.jsonl")
VAL_PATH = os.path.join(EVALS_DIR, "tasks", "val_review_loop.jsonl")
RESULTS_JSON_PATH = os.path.join(EVALS_DIR, "review_loop_eval_results.json")
REPORT_MD_PATH = os.path.join(EVALS_DIR, "skillopt_report_review_loop.md")

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
    ]
}]


def load_file_version(rel_path: str, use_git_base: bool = False) -> str:
  abs_path = os.path.join(ARMATURE_ROOT, rel_path)
  if use_git_base:
    for ref in ("origin/main", "HEAD~1"):
      try:
        out = subprocess.check_output(
            ["git", "show", f"{ref}:{rel_path}"],
            cwd=ARMATURE_ROOT,
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8")
      except Exception:
        continue
  with open(abs_path, "r", encoding="utf-8") as f:
    return f.read()


def load_bundle(use_git_base: bool = False) -> dict[str, str]:
  return {
      "protocol": load_file_version(PROTOCOL_REL, use_git_base=use_git_base),
      "arm-review": load_file_version(
          ARM_REVIEW_REL, use_git_base=use_git_base
      ),
      "arm-implement": load_file_version(
          ARM_IMPLEMENT_REL, use_git_base=use_git_base
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
    max_retries: int = 5,
) -> tuple[list[str], list[dict], list[dict]]:
  if not API_KEY:
    sys.exit("ERROR: Missing GEMINI_API_KEY in environment.")
  for attempt in range(1, max_retries + 1):
    active_model = model
    if attempt >= 3:
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
  if use_tools and raw_parts:
    has_asq = any(tc.get("name") == "ask_question" for tc in all_tool_calls)
    has_file_op = any(
        tc.get("name") in ("write_to_file", "replace_file_content")
        for tc in all_tool_calls
    )
    has_visible_text = len("\n".join(all_texts).strip()) >= 120
    if (
        (has_file_op and (not has_asq or not has_visible_text))
        or (all_tool_calls and not has_visible_text)
        or (not has_asq and not has_file_op and has_visible_text)
    ):
      if all_tool_calls and (not has_asq or not has_visible_text):
        fn_responses = []
        for tc in all_tool_calls:
          fn_responses.append({
              "functionResponse": {
                  "name": tc.get("name"),
                  "response": {
                      "status": "success",
                      "message": (
                          f"Executed {tc.get('name')}. Now complete the turn by"
                          " outputting the full visible markdown report/tables"
                          " in chat (if not yet printed) and invoking the"
                          " required ask_question tool call."
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
                    " call(s) (e.g. write_to_file and/or ask_question) to"
                    " complete this turn.]"
                )
            }],
        })
      more_texts, more_tcs, _ = _single_gemini_request(
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
  return "\n".join(all_texts), all_tool_calls


def evaluate_invariants(
    task: dict, text: str, tool_calls: list[dict]
) -> list[str]:
  vetoes = []
  inv_list = task.get("invariants", [])
  combined_surface = text + "\n" + json.dumps(tool_calls)

  mutated_files = []
  for tc in tool_calls:
    if tc.get("name") in ("write_to_file", "replace_file_content"):
      args = tc.get("args", {})
      tf = args.get("TargetFile", "")
      if tf:
        mutated_files.append(tf)

  for inv in inv_list:
    if inv == "has_iteration_breakdown_table_in_chat":
      has_heading = bool(
          re.search(r"(?i)(?:review\s+loop\s+)?iteration\s+breakdown", text)
      )
      has_table_row = bool(
          re.search(
              r"\|\s*[*`]*(?:Iteration\s*|Pass\s*)?1[*`]*\s*\|[^|]+\|",
              text,
              re.IGNORECASE,
          )
      )
      if not (has_heading and has_table_row):
        vetoes.append(
            "has_iteration_breakdown_table_in_chat: Missing 'Review Loop"
            " Iteration Breakdown' markdown table in chat text"
        )
    elif inv == "writes_review_md":
      wrote_review = any("review.md" in mf for mf in mutated_files)
      if not wrote_review:
        vetoes.append(
            "writes_review_md: Did not call write_to_file on review.md"
        )
    elif inv == "has_ask_question_tool":
      if not any(tc.get("name") == "ask_question" for tc in tool_calls):
        vetoes.append(
            "has_ask_question_tool: Missing native ask_question tool call"
        )
    elif inv == "no_bare_tool_call":
      if len(text.strip()) < 120:
        vetoes.append(
            "no_bare_tool_call: Emitted bare tool call with insufficient"
            " visible markdown text"
        )
    elif inv == "has_reverted_test_regression_status":
      if not re.search(
          r"(?i)reverted_test_regression|anti-oscillation\s+ledger",
          combined_surface,
      ):
        vetoes.append(
            "has_reverted_test_regression_status: Missing"
            " 'reverted_test_regression' or Anti-Oscillation Ledger entry"
        )
    elif inv == "has_skipped_spec_adr_precedence_status":
      if not re.search(r"(?i)skipped_spec_adr_precedence", combined_surface):
        vetoes.append(
            "has_skipped_spec_adr_precedence_status: Missing"
            " 'skipped_spec_adr_precedence' status for blinded style vs"
            " Spec/ADR conflict"
        )
    elif inv == "has_blocked_by_legacy_fence_status":
      if not re.search(r"(?i)blocked_by_legacy_fence", combined_surface):
        vetoes.append(
            "has_blocked_by_legacy_fence_status: Missing"
            " 'blocked_by_legacy_fence' status for legacy-fenced file"
        )
    elif inv == "no_spec_or_adr_mutation":
      bad = [
          mf
          for mf in mutated_files
          if "spec.md" in mf or "/adr/" in mf or "0004" in mf or "0007" in mf
      ]
      if bad:
        vetoes.append(
            "no_spec_or_adr_mutation: Illegally mutated spec/ADR file(s):"
            f" {bad}"
        )
    elif inv == "no_source_file_mutation":
      bad = [
          mf
          for mf in mutated_files
          if not (
              mf.endswith("review.md") or mf.endswith("review_loop_details.md")
          )
      ]
      if bad:
        vetoes.append(
            "no_source_file_mutation: Illegally mutated source file(s) during"
            f" report finalization: {bad}"
        )
    elif inv == "no_fenced_file_mutation":
      bad = [
          mf
          for mf in mutated_files
          if "legacy_v1_resolver" in mf or "v1_tesseract_adapter" in mf
      ]
      if bad:
        vetoes.append(
            "no_fenced_file_mutation: Illegally mutated legacy-fenced"
            f" file(s): {bad}"
        )
    elif inv == "has_legacy_fence_banner":
      if not re.search(
          r"(?i)(?:Working\s+in\s+`?[^`\n]+`?|Deprecated\s+code\s+boundary\s+active)",
          text,
      ):
        vetoes.append(
            "has_legacy_fence_banner: Missing Adaptive Verbosity legacy fence"
            " banner in chat"
        )
    elif inv == "no_premature_review_md":
      if any("review.md" in mf for mf in mutated_files):
        vetoes.append(
            "no_premature_review_md: Prematurely wrote review.md before"
            " resolving Pre-Manual-Testing Blocker Gate or Step 2.5"
        )
    elif inv == "has_blocker_gate_options":
      asq_calls = [tc for tc in tool_calls if tc.get("name") == "ask_question"]
      asq_dump = json.dumps(asq_calls).lower()
      if not (
          ("s0" in asq_dump or "blocker" in asq_dump or "resolve" in asq_dump)
          and ("manual testing" in asq_dump or "step 2.5" in asq_dump)
      ):
        vetoes.append(
            "has_blocker_gate_options: ask_question modal does not present the"
            " Pre-Manual-Testing Unapplied Blocker Gate options"
        )
    elif inv == "has_step4_headings":
      for h in (
          "Extracted Domain Terms",
          "ADR Updates",
          "Living Runbook Synchronization",
          "Verification Audit",
      ):
        if not re.search(rf"(?i)#+\s*{re.escape(h)}", text):
          vetoes.append(
              f"has_step4_headings: Missing mandatory Step 4 heading '{h}'"
          )
    elif inv == "writes_terms_or_runbook":
      if not any(
          "terms.md" in mf or "manual_testing" in mf for mf in mutated_files
      ):
        vetoes.append(
            "writes_terms_or_runbook: Did not call write_to_file on terms.md or"
            " manual_testing/<domain>.md"
        )
    elif inv == "has_accurate_len_comments_3_not_9":
      m = re.search(
          r"\|\s*(?:Iteration\s*|Pass\s*)?1\s*\|(?:[^|]+\|){0,2}\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
          combined_surface,
          re.IGNORECASE,
      )
      if not m:
        vetoes.append(
            "has_accurate_len_comments_3_not_9: Could not parse Iteration 1"
            " row in Review Loop Iteration Breakdown table"
        )
      else:
        total_c = m.group(1)
        if total_c != "3":
          vetoes.append(
              "has_accurate_len_comments_3_not_9: Iteration 1 Total Comments"
              f" was {total_c} instead of len(comments)==3 (used inflated"
              " reviewer_comments_count=9)"
          )
    elif inv == "no_observables_heading":
      if re.search(r"(?i)#+\s*expected\s+observables", text):
        vetoes.append(
            "no_observables_heading: Found forbidden heading 'Expected"
            " Observables'"
        )
    elif inv == "has_expected_observations":
      if not re.search(r"(?i)#+\s*expected\s+observations", text):
        vetoes.append(
            "has_expected_observations: Missing '##### Expected Observations'"
            " heading"
        )
    elif inv == "localhost_only_url":
      if re.search(
          r"https?://[a-zA-Z0-9_-]+\.example\.(?:com|internal)", text
      ):
        vetoes.append(
            "localhost_only_url: Leaked remote workstation hostname URL"
        )
      if not re.search(r"https?://localhost:\d+", text):
        vetoes.append(
            "localhost_only_url: Missing complete localhost URL with port"
        )
    elif inv == "has_fenced_js_snippet":
      if not re.search(r"```(?:javascript|js)\s+[\s\S]*?window\.__", text):
        vetoes.append(
            "has_fenced_js_snippet: Did not reproduce self-contained"
            " copy-pastable JS snippet"
        )
    elif inv == "has_scenario1_verification_ask_question":
      asq_calls = [tc for tc in tool_calls if tc.get("name") == "ask_question"]
      asq_dump = json.dumps(asq_calls).lower()
      if "scenario 1" not in asq_dump and "verified" not in asq_dump:
        vetoes.append(
            "has_scenario1_verification_ask_question: Did not transition"
            " directly to Scenario 1 verification ask_question"
        )
    elif inv == "skips_step_3_6_for_visual_only":
      if not re.search(
          r"(?i)step\s*3\.6[\s\S]{0,120}(?:skip|bypass)|(?:skip|bypass)[\s\S]{0,120}step\s*3\.6",
          text,
      ):
        vetoes.append(
            "skips_step_3_6_for_visual_only: Did not explicitly state that"
            " Step 3.6 Pre-Closeout Review Loop was skipped for the"
            " Visual-Only track"
        )
    elif inv in ("no_subagent_dispatch", "no_subagent_or_swarm_dispatch"):
      bad_tc = [
          tc.get("name")
          for tc in tool_calls
          if tc.get("name") == "invoke_subagent"
      ]
      if bad_tc:
        vetoes.append(
            "no_subagent_dispatch: Illegally dispatched subagent on a"
            f" Visual-Only track closeout: {bad_tc}"
        )
    elif inv == "has_deferred_fixture_stamp":
      if not re.search(
          r"(?i)Stateful\s+3-Part\s+Fixture\s+Triad\s+deferred",
          combined_surface,
      ):
        vetoes.append(
            "has_deferred_fixture_stamp: Missing cold-start 'Stateful 3-Part"
            " Fixture Triad deferred' stamp"
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
  skill_name = task.get("target_skill", "arm-review")
  skill_text = bundle.get(skill_name, bundle["arm-review"])
  sys_prompt = f"""You are an AI coding agent operating inside an Armature workspace. Follow these rules and skill instructions strictly:

=== UNIVERSAL PROTOCOL (rules/armature_protocol.md) ===
{bundle['protocol']}

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
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
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
        "=== RUNNING BASELINE EVALUATION (git base revision) ===",
        flush=True,
    )
    base_bundle = load_bundle(use_git_base=True)
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
    cand_bundle = load_bundle(use_git_base=False)
    base_bundle = load_bundle(use_git_base=True)
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
            cand_val["lb_90"] > base_val_mean and cand_val["total_vetoes"] == 0
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
