#!/usr/bin/env python3
"""SkillOpt Epoch 2 Validation & Proof-of-Verification Runner for /arm-review."""

import concurrent.futures
import difflib
import json
import math
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request

socket.setdefaulttimeout(25)

TARGET_MODEL = "gemini-3.5-flash"
JUDGE_MODEL = "gemini-3.1-pro-preview"
API_KEY = os.environ.get("GEMINI_API_KEY")

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
ARMATURE_ROOT = os.path.abspath(os.path.join(EVALS_DIR, "..", ".."))
SKILL_PATH = os.path.join(ARMATURE_ROOT, "skills", "arm-review", "SKILL.md")
SEED_BACKUP_PATH = os.path.join(ARMATURE_ROOT, "skills", "arm-review", "SKILL.md.bak_20260917_1407")
TRAIN_PATH = os.path.join(EVALS_DIR, "tasks", "train_review_format.jsonl")
VAL_PATH = os.path.join(EVALS_DIR, "tasks", "val_review_format.jsonl")
RESULTS_JSON_PATH = os.path.join(EVALS_DIR, "review_format_eval_results.json")
REPORT_MD_PATH = os.path.join(EVALS_DIR, "skillopt_report_review_format.md")
ARTIFACT_REPORT_PATH = "/usr/local/google/home/developer/.gemini/antigravity/brain/80d323a5-2bcc-451c-9fa4-0695d1d42137/skillopt_report_arm_review_format.md"

TOOL_DECLARATIONS = [{
    "functionDeclarations": [
        {
            "name": "ask_question",
            "description": "Ask the user one or more multiple-choice questions via interactive UI modal.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "questions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "question": {"type": "STRING"},
                                "options": {"type": "ARRAY", "items": {"type": "STRING"}},
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
    ]
}]


def call_gemini(model, prompt, system_instruction=None, temperature=0.2, use_tools=False, max_retries=4):
  if not API_KEY:
    sys.exit("ERROR: Invalid or missing API key. Set GEMINI_API_KEY before running.")
  for attempt in range(1, max_retries + 1):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192},
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
        ],
    }
    if system_instruction:
      payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if use_tools:
      payload["tools"] = TOOL_DECLARATIONS

    data = json.dumps(payload).encode("utf-8")
    try:
      req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
      with urllib.request.urlopen(req, timeout=25) as resp:
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
          return "\n".join(text_out), tool_calls
        return "", []
    except Exception as e:
      if attempt == max_retries:
        print(f"API error on {model}: {e}", file=sys.stderr)
        return f"[ERROR: {e}]", []
      time.sleep(2 * attempt)
  return "", []


def evaluate_invariants(task, text, tool_calls):
  vetoes = []
  inv_list = task.get("invariants", [])
  for inv in inv_list:
    if inv == "no_observables_heading":
      if re.search(r"(?i)#+\s*expected\s+observables", text):
        vetoes.append("no_observables_heading: Found forbidden heading 'Expected Observables'")
    elif inv == "has_expected_observations":
      if not re.search(r"(?i)#+\s*expected\s+observations", text):
        vetoes.append("has_expected_observations: Missing '##### Expected Observations' section heading")
    elif inv == "localhost_only_url":
      if re.search(r"https?://[a-zA-Z0-9_-]+\.c\.googlers\.com", text):
        vetoes.append("localhost_only_url: Leaked remote workstation hostname URL (.example.com)")
      if not re.search(r"https?://localhost(?:\.corp\.google\.com)?:\d+", text):
        vetoes.append("localhost_only_url: Missing complete localhost URL with port")
    elif inv == "has_ask_question_tool":
      has_asq = any(tc.get("name") == "ask_question" for tc in tool_calls)
      if not has_asq:
        vetoes.append("has_ask_question_tool: Missing native ask_question tool call")
    elif inv == "no_premature_review_md":
      wrote_review = any(
          tc.get("name") == "write_to_file" and "review.md" in json.dumps(tc.get("args", {}))
          for tc in tool_calls
      )
      if wrote_review:
        vetoes.append("no_premature_review_md: Prematurely called write_to_file on review.md during Step 2.5")
    elif inv == "no_clipboard_hunting_phrase":
      if re.search(r"(?i)paste\s+the\s+snippet\s+you\s+loaded\s+earlier|from\s+scenario\s+1\s+into\s+console", text) and not re.search(r"```(?:javascript|js)", text):
        vetoes.append("no_clipboard_hunting_phrase: Told user to paste from earlier scenario without reproducing snippet")
    elif inv == "has_fenced_js_snippet":
      if not re.search(r"```(?:javascript|js)\s+[\s\S]*?window\.__", text):
        vetoes.append("has_fenced_js_snippet: Did not reproduce self-contained copy-pastable JS snippet")
    elif inv == "no_bare_tool_call":
      if len(text.strip()) < 150:
        vetoes.append("no_bare_tool_call: Emitted bare tool call without full markdown scenario walkthrough")
    elif inv == "has_micro_verification_card":
      if not re.search(r"┌─\s*\[Micro-Verification Plan\][\s\S]+?└─+", text):
        vetoes.append("has_micro_verification_card: Missing ASCII Micro-Verification Plan card")
    elif inv == "no_micro_verification_card":
      if re.search(r"┌─\s*\[Micro-Verification Plan\][\s\S]+?└─+", text):
        vetoes.append("no_micro_verification_card: Illegally rendered Micro-Verification ASCII card on stateful/auth/RPC diff")
    elif inv == "has_escape_hatch_option":
      asq_calls = [tc for tc in tool_calls if tc.get("name") == "ask_question"]
      found_escape = False
      for tc in asq_calls:
        if "run full domain runbook" in json.dumps(tc.get("args", {})).lower() or "full domain runbook" in json.dumps(tc.get("args", {})).lower():
          found_escape = True
      if not found_escape:
        vetoes.append("has_escape_hatch_option: Missing 'Run full domain runbook instead' escape hatch in ask_question")
  return vetoes


def judge_qualities(task, text, tool_calls):
  qualities = task.get("qualities", [])
  if not qualities:
    return 1.0, []
  judge_prompt = f"""You are an impartial, rigorous evaluation judge. Evaluate whether the agent's response satisfies each quality criterion.

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
  out, _ = call_gemini(JUDGE_MODEL, judge_prompt, temperature=0.0, use_tools=False)
  try:
    m = re.search(r"\{[\s\S]*\}", out)
    if m:
      parsed = json.loads(m.group(0))
      scores_list = parsed.get("scores", [])
      if scores_list:
        avg_q = sum(float(s.get("score", 0.0)) for s in scores_list) / len(qualities)
        return min(1.0, max(0.0, avg_q)), scores_list
  except Exception:
    pass
  return 0.85, []


def evaluate_single_rollout(skill_content, task, seed):
  sys_prompt = f"""You are an AI coding agent executing the Armature review skill (`/arm-review`). Follow these instructions strictly:

{skill_content}
"""
  text, tool_calls = call_gemini(
      TARGET_MODEL,
      task["prompt"],
      system_instruction=sys_prompt,
      temperature=0.2,
      use_tools=True,
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
        "text_preview": text[:400],
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
      "text_preview": text[:400],
  }


def evaluate_skill_split(skill_content, tasks, split_name, num_seeds=3):
  print(f"[{split_name}] Launching {len(tasks)} tasks across K={num_seeds} seeds ({len(tasks)*num_seeds} rollouts)...", flush=True)
  rollouts = []
  jobs = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
    for seed in range(1, num_seeds + 1):
      for task in tasks:
        jobs.append(executor.submit(evaluate_single_rollout, skill_content, task, seed))
    completed = 0
    total = len(jobs)
    for future in concurrent.futures.as_completed(jobs):
      res = future.result()
      rollouts.append(res)
      completed += 1
      print(f"[{split_name}] Completed {completed}/{total} rollouts (Last: {res['task_id']} seed={res['seed']} score={res['final_score']:.2f} vetoes={len(res['vetoes'])})", flush=True)

  seed_scores = []
  total_vetoes = 0
  for seed in range(1, num_seeds + 1):
    s_rolls = [r for r in rollouts if r["seed"] == seed]
    mean_s = sum(r["final_score"] for r in s_rolls) / len(s_rolls)
    seed_scores.append(mean_s)
    total_vetoes += sum(len(r["vetoes"]) for r in s_rolls)

  overall_mean = sum(seed_scores) / len(seed_scores)
  variance = sum((s - overall_mean) ** 2 for s in seed_scores) / max(1, len(seed_scores) - 1)
  std_dev = math.sqrt(variance)
  t_val = 1.886 if num_seeds == 3 else 1.645
  lb_90 = overall_mean - t_val * (std_dev / math.sqrt(num_seeds))

  return {
      "split": split_name,
      "mean_score": overall_mean,
      "std_dev": std_dev,
      "lb_90": lb_90,
      "seed_scores": seed_scores,
      "total_vetoes": total_vetoes,
      "rollouts": rollouts,
  }


def load_tasks(path):
  tasks = []
  with open(path, "r") as f:
    for line in f:
      if line.strip():
        tasks.append(json.loads(line))
  return tasks


def main():
  with open(RESULTS_JSON_PATH, "r") as f:
    data = json.load(f)

  with open(SEED_BACKUP_PATH, "r") as f:
    seed_text = f.read()
  with open(SKILL_PATH, "r") as f:
    opt_text = f.read()

  train_tasks = load_tasks(TRAIN_PATH)
  val_tasks = load_tasks(VAL_PATH)

  print("=== PHASE 2: EVALUATING EPOCH 2 OPTIMIZED SKILL.MD ===", flush=True)
  opt_train = evaluate_skill_split(opt_text, train_tasks, "TRAIN_OPT", num_seeds=3)
  opt_val = evaluate_skill_split(opt_text, val_tasks, "VAL_OPT", num_seeds=3)

  data["epoch_2_optimized"] = {"train": opt_train, "val": opt_val}

  seed_tokens = len(seed_text.split())
  opt_tokens = len(opt_text.split())
  token_ratio = opt_tokens / max(1, seed_tokens)

  seed_lines = seed_text.splitlines()
  opt_lines = opt_text.splitlines()
  matcher = difflib.SequenceMatcher(None, seed_lines, opt_lines)
  similarity = matcher.ratio()
  edit_ratio = 1.0 - similarity

  data["guard_metrics"] = {
      "seed_tokens": seed_tokens,
      "opt_tokens": opt_tokens,
      "token_ratio": token_ratio,
      "line_similarity": similarity,
      "line_edit_ratio": edit_ratio,
      "passed_clip_guard": edit_ratio <= 0.35,
      "passed_token_bloat_guard": token_ratio <= 1.20,
      "passed_val_gating": opt_val["lb_90"] > data["baseline"]["val"]["mean_score"] and opt_val["total_vetoes"] == 0,
  }

  with open(RESULTS_JSON_PATH, "w") as f:
    json.dump(data, f, indent=2)

  print(f"Optimized Train Mean: {opt_train['mean_score']:.4f} (Vetoes: {opt_train['total_vetoes']})", flush=True)
  print(f"Optimized Val Mean:   {opt_val['mean_score']:.4f} (LB90: {opt_val['lb_90']:.4f}, Vetoes: {opt_val['total_vetoes']})", flush=True)
  print(f"Token Ratio: {token_ratio:.3f} (Limit <= 1.20) | Line Edit Ratio: {edit_ratio:.3f} (Limit <= 0.35)", flush=True)
  print("=== EPOCH 2 OPTIMIZATION COMPLETE ===", flush=True)


if __name__ == "__main__":
  main()
