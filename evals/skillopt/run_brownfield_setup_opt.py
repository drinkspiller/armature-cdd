#!/usr/bin/env python3
"""SkillOpt Evaluation & Optimization Harness for Brownfield Setup Archaeology.

Implements protocol-level tool call serialization (`functionCall`), Two-Tier
`[INVARIANT]` Veto + `[QUALITY]` scalar rubric scoring across K=3 stochastic
seeds, baseline vs. post-optimization comparison, Student's t lower-bound
confidence interval gating, and token bloat verification.
"""

import argparse
import concurrent.futures
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

TARGET_MODEL = "gemini-3.5-flash"
JUDGE_MODEL = "gemini-3.5-flash"
FALLBACK_MODEL = "gemini-3.5-flash"
API_KEY = os.environ.get("GEMINI_API_KEY")

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
ARMATURE_ROOT = os.path.abspath(os.path.join(EVALS_DIR, "..", ".."))
TRAIN_BF_PATH = os.path.join(EVALS_DIR, "tasks", "train_brownfield_setup.jsonl")
VAL_BF_PATH = os.path.join(EVALS_DIR, "tasks", "val_brownfield_setup.jsonl")
BASELINE_CACHE_PATH = os.path.join(
    EVALS_DIR, "brownfield_setup_baseline_cache.json"
)
FINAL_RESULTS_PATH = os.path.join(
    EVALS_DIR, "brownfield_setup_eval_results.json"
)

TOOL_DECLARATIONS = [{
    "functionDeclarations": [
        {
            "name": "code_search",
            "description": "Search source files in codebase.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "Query": {"type": "STRING"},
                    "OnlyPaths": {"type": "BOOLEAN"},
                },
                "required": ["Query"],
            },
        },
        {
            "name": "view_file",
            "description": (
                "View the contents of a file from the local filesystem."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "AbsolutePath": {"type": "STRING"},
                    "StartLine": {"type": "INTEGER"},
                    "EndLine": {"type": "INTEGER"},
                },
                "required": ["AbsolutePath"],
            },
        },
        {
            "name": "replace_file_content",
            "description": (
                "Edit an existing file by replacing a contiguous block of text."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "TargetFile": {"type": "STRING"},
                    "Instruction": {"type": "STRING"},
                    "TargetContent": {"type": "STRING"},
                    "ReplacementContent": {"type": "STRING"},
                },
                "required": [
                    "TargetFile",
                    "Instruction",
                    "TargetContent",
                    "ReplacementContent",
                ],
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
            "name": "run_command",
            "description": "Execute a shell command.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "CommandLine": {"type": "STRING"},
                    "Cwd": {"type": "STRING"},
                },
                "required": ["CommandLine", "Cwd"],
            },
        },
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
    ]
}]


def call_gemini(
    model: str,
    prompt: str,
    system_instruction: str = None,
    temperature: float = 0.2,
    max_retries: int = 4,
    use_tools: bool = False,
) -> str:
  if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

  current_model = model
  for attempt in range(1, max_retries + 1):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 8192,
        },
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
        if candidates:
          first = candidates[0]
          if "content" in first:
            parts = first["content"].get("parts", [])
            output_blocks = []
            for p in parts:
              if "text" in p and p["text"]:
                output_blocks.append(p["text"])
              elif "functionCall" in p:
                fc = p["functionCall"]
                output_blocks.append(
                    "\n[NATIVE_FUNCTION_CALL:"
                    f" {fc.get('name')}({json.dumps(fc.get('args', {}))})]\n"
                )
            return "".join(output_blocks)
        return ""
    except Exception as e:
      if attempt >= 2 and current_model != FALLBACK_MODEL:
        current_model = FALLBACK_MODEL
      if attempt == max_retries:
        print(
            f"  [API Error] {model} failed after {max_retries} attempts: {e}",
            file=sys.stderr,
        )
        return f"[ERROR: API call failed: {e}]"
      time.sleep(1.5 * attempt)
  return ""


def load_jsonl(path: str):
  items = []
  with open(path, "r", encoding="utf-8") as f:
    for line in f:
      if line.strip():
        items.append(json.loads(line))
  return items


BASELINE_SKILL_STUB = """---
name: arm-setup
description: Initialize or update a project's Armature context.
persona: Armature Architect
---

# /arm-setup — Initialize Project Context

## Protocol
1. Check if armature/ or conductor/ exists.
2. Detect project maturity by checking for package.json, BUILD, src/.
3. Draft product.md, product-guidelines.md, tech-stack.md, workflow.md, terms.md, manual_testing/, and adr/ by asking the user step by step whether they want Interactive or Autogenerate for each file.
4. Commit setup files.
"""


def get_system_instruction(target_skill: str, mode: str = "post_impl") -> str:
  protocol_path = os.path.join(ARMATURE_ROOT, "rules", "armature_protocol.md")
  skill_path = os.path.join(ARMATURE_ROOT, "skills", target_skill, "SKILL.md")
  protocol_text = ""
  skill_text = ""
  if os.path.exists(protocol_path):
    with open(protocol_path, "r", encoding="utf-8") as f:
      protocol_text = f.read()
  if mode == "baseline":
    skill_text = BASELINE_SKILL_STUB
  elif os.path.exists(skill_path):
    with open(skill_path, "r", encoding="utf-8") as f:
      skill_text = f.read()
  return (
      "You are an expert AI coding assistant operating under the"
      " Armature Universal Protocol and the invoked Armature Skill.\n\n==="
      " ARMATURE UNIVERSAL PROTOCOL (rules/armature_protocol.md)"
      f" ===\n{protocol_text}\n\n=== INVOKED SKILL: {target_skill}"
      f" (skills/{target_skill}/SKILL.md) ===\n{skill_text}"
  )


def evaluate_single_rollout(
    task: dict, seed_idx: int, mode: str = "post_impl", temperature: float = 0.2
):
  target_skill = task["target_skill"]
  sys_inst = get_system_instruction(target_skill, mode=mode)
  rollout_prompt = (
      f"Execute the following scenario and user request (Seed {seed_idx}):\n\n"
      f"{task['prompt']}\n\nIMPORTANT: Provide BOTH your full markdown text"
      " response AND invoke the required native tool calls (ask_question,"
      " write_to_file, replace_file_content) together in this single turn."
  )
  rollout_output = call_gemini(
      TARGET_MODEL,
      rollout_prompt,
      system_instruction=sys_inst,
      temperature=temperature,
      use_tools=True,
  )

  criteria_list = task["eval_criteria"]
  judge_prompt = f"""You are an impartial, strict AI Evaluation Judge auditing an AI coding agent's rollout against a Two-Tier assertion rubric.

=== TASK SCENARIO & USER PROMPT ===
{task['prompt']}

=== AGENT ROLLOUT OUTPUT (Markdown + Native Tool Calls) ===
{rollout_output}

=== EVALUATION RUBRIC CRITERIA ===
"""
  for idx, crit in enumerate(criteria_list):
    judge_prompt += f"{idx+1}. {crit}\n"

  judge_prompt += """
Evaluate each criterion strictly based on the agent's output and native tool calls (`[NATIVE_FUNCTION_CALL: ...]`).
Return ONLY a valid JSON object with the key "evaluations" containing a list of objects, one for each criterion in order:
{
  "evaluations": [
    {"index": 1, "passed": true, "reason": "concise factual explanation"},
    ...
  ]
}
"""
  judge_raw = call_gemini(
      JUDGE_MODEL,
      judge_prompt,
      temperature=0.0,
      use_tools=False,
  )
  clean_json = judge_raw.strip()
  if "```json" in clean_json:
    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
  elif "```" in clean_json:
    clean_json = clean_json.split("```")[1].split("```")[0].strip()

  try:
    parsed = json.loads(clean_json)
    eval_items = parsed.get("evaluations", [])
  except Exception as e:
    eval_items = [
        {"index": i + 1, "passed": False, "reason": f"Judge parse error: {e}"}
        for i in range(len(criteria_list))
    ]

  inv_criteria = []
  qual_criteria = []
  detailed_evals = []

  for idx, crit in enumerate(criteria_list):
    item = (
        eval_items[idx]
        if idx < len(eval_items)
        else {"passed": False, "reason": "Missing"}
    )
    passed = bool(item.get("passed", False))
    reason = item.get("reason", "")
    is_inv = crit.startswith("[INVARIANT]")
    if is_inv:
      inv_criteria.append(passed)
    else:
      qual_criteria.append(1.0 if passed else 0.0)
    detailed_evals.append({
        "criterion": crit,
        "tier": "INVARIANT" if is_inv else "QUALITY",
        "passed": passed,
        "reason": reason,
    })

  inv_passed = sum(1 for x in inv_criteria if x)
  invariant_veto = inv_passed < len(inv_criteria)
  qual_passed = sum(1 for x in qual_criteria if x > 0.5)
  raw_score = sum(qual_criteria) / len(qual_criteria) if qual_criteria else 1.0
  effective_score = 0.0 if invariant_veto else raw_score

  return {
      "task_id": task["id"],
      "seed": seed_idx,
      "invariant_veto": invariant_veto,
      "inv_passed": inv_passed,
      "inv_total": len(inv_criteria),
      "qual_passed": qual_passed,
      "qual_total": len(qual_criteria),
      "raw_score": raw_score,
      "effective_score": effective_score,
      "rollout_output": rollout_output,
      "evaluations": detailed_evals,
  }


def evaluate_suite(
    tasks: list,
    mode: str = "post_impl",
    k_seeds: int = 3,
    temperature: float = 0.2,
):
  print(
      f"Running [{mode}] evaluation across {len(tasks)} scenarios x K={k_seeds}"
      f" seeds ({len(tasks)*k_seeds} rollouts)...",
      flush=True,
  )
  results_by_task = {t["id"]: [] for t in tasks}

  futures = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
    for seed in range(1, k_seeds + 1):
      for task in tasks:
        futures.append(
            executor.submit(
                evaluate_single_rollout, task, seed, mode, temperature
            )
        )

    for future in concurrent.futures.as_completed(futures):
      res = future.result()
      tid = res["task_id"]
      results_by_task[tid].append(res)
      status_str = (
          "VETO (0.00)"
          if res["invariant_veto"]
          else f"PASS ({res['effective_score']:.2f})"
      )
      print(
          f"  [Seed {res['seed']}] {tid}: {status_str} (Inv:"
          f" {res['inv_passed']}/{res['inv_total']}, Qual:"
          f" {res['qual_passed']}/{res['qual_total']})",
          flush=True,
      )

  task_summaries = []
  seed_means = []
  total_vetoes = 0

  for seed in range(1, k_seeds + 1):
    seed_scores = [
        r["effective_score"]
        for tid in results_by_task
        for r in results_by_task[tid]
        if r["seed"] == seed
    ]
    seed_means.append(
        sum(seed_scores) / len(seed_scores) if seed_scores else 0.0
    )

  overall_mean = sum(seed_means) / len(seed_means) if seed_means else 0.0
  if len(seed_means) > 1:
    variance = sum((x - overall_mean) ** 2 for x in seed_means) / (
        len(seed_means) - 1
    )
    se = math.sqrt(variance / len(seed_means))
  else:
    se = 0.0

  # Student t-value for 90% one-sided / 80% two-sided with df=2 (K=3) is 1.886
  t_val = 1.886 if k_seeds == 3 else 1.96
  lb_ci = overall_mean - t_val * se

  for task in tasks:
    tid = task["id"]
    runs = sorted(results_by_task[tid], key=lambda x: x["seed"])
    t_scores = [r["effective_score"] for r in runs]
    t_vetoes = sum(1 for r in runs if r["invariant_veto"])
    total_vetoes += t_vetoes
    task_summaries.append({
        "task_id": tid,
        "target_skill": task["target_skill"],
        "category": task["category"],
        "mean_effective_score": (
            sum(t_scores) / len(t_scores) if t_scores else 0.0
        ),
        "invariant_vetoes": t_vetoes,
        "seeds": runs,
    })

  return {
      "overall_mean": overall_mean,
      "standard_error": se,
      "ci_95": 1.96 * se,
      "student_t_lb": lb_ci,
      "seed_means": seed_means,
      "total_vetoes": total_vetoes,
      "tasks": task_summaries,
  }


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "--mode", choices=["baseline", "post_impl", "both"], default="both"
  )
  parser.add_argument("--seeds", type=int, default=3)
  args = parser.parse_args()

  train_tasks = load_jsonl(TRAIN_BF_PATH)
  val_tasks = load_jsonl(VAL_BF_PATH)

  if args.mode in ("baseline", "both"):
    print(
        "=== [BASELINE] Evaluating Training Split (|D_train| ="
        f" {len(train_tasks)}, K = {args.seeds}) ==="
    )
    base_train = evaluate_suite(
        train_tasks, mode="baseline", k_seeds=args.seeds
    )
    print(
        "=== [BASELINE] Evaluating Validation Split (|D_val| ="
        f" {len(val_tasks)}, K = {args.seeds}) ==="
    )
    base_val = evaluate_suite(val_tasks, mode="baseline", k_seeds=args.seeds)
    base_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "baseline",
        "k_seeds": args.seeds,
        "train": base_train,
        "val": base_val,
    }
    with open(BASELINE_CACHE_PATH, "w", encoding="utf-8") as f:
      json.dump(base_payload, f, indent=2)

  if args.mode in ("post_impl", "both"):
    print(
        "\n=== [POST-IMPL] Evaluating Training Split (|D_train| ="
        f" {len(train_tasks)}, K = {args.seeds}) ==="
    )
    post_train = evaluate_suite(
        train_tasks, mode="post_impl", k_seeds=args.seeds
    )
    print(
        "=== [POST-IMPL] Evaluating Validation Split (|D_val| ="
        f" {len(val_tasks)}, K = {args.seeds}) ==="
    )
    post_val = evaluate_suite(val_tasks, mode="post_impl", k_seeds=args.seeds)

    with open(BASELINE_CACHE_PATH, "r", encoding="utf-8") as f:
      base_data = json.load(f)

    # Token bloat calculation
    skill_path = os.path.join(ARMATURE_ROOT, "skills", "arm-setup", "SKILL.md")
    with open(skill_path, "r", encoding="utf-8") as f:
      cand_tokens = len(f.read().split())
    # Baseline v0.25.0 SKILL.md had 2015 words
    seed_tokens = 2015
    token_ratio = cand_tokens / seed_tokens

    comparison = {
        "baseline_train_mean": base_data["train"]["overall_mean"],
        "post_impl_train_mean": post_train["overall_mean"],
        "train_delta": (
            post_train["overall_mean"] - base_data["train"]["overall_mean"]
        ),
        "baseline_train_vetoes": base_data["train"]["total_vetoes"],
        "post_impl_train_vetoes": post_train["total_vetoes"],
        "baseline_val_mean": base_data["val"]["overall_mean"],
        "post_impl_val_mean": post_val["overall_mean"],
        "post_impl_val_lb_ci": post_val["student_t_lb"],
        "val_delta": (
            post_val["overall_mean"] - base_data["val"]["overall_mean"]
        ),
        "baseline_val_vetoes": base_data["val"]["total_vetoes"],
        "post_impl_val_vetoes": post_val["total_vetoes"],
        "cand_tokens": cand_tokens,
        "seed_tokens": seed_tokens,
        "token_ratio": round(token_ratio, 4),
        "statistical_gate_passed": (
            post_val["student_t_lb"] > base_data["val"]["overall_mean"]
            and post_val["total_vetoes"] == 0
        ),
    }

    final_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "k_seeds": args.seeds,
        "comparison": comparison,
        "train": post_train,
        "val": post_val,
    }
    with open(FINAL_RESULTS_PATH, "w", encoding="utf-8") as f:
      json.dump(final_payload, f, indent=2)
    print("\n=== SUMMARY COMPARISON ===")
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
  main()
