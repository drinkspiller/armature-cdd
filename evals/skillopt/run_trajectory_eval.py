#!/usr/bin/env python3
"""Multi-Turn Trajectory Evaluation Runner for Armature Decision-Tree Traversal.

Evaluates Armature skills against multi-turn interactive conversational
scenarios,
measuring tree leaf depth, anti-dictation compliance, ledger fidelity, and
natural convergence.

Usage:
  python3 evals/skillopt/run_trajectory_eval.py
  python3 evals/skillopt/run_trajectory_eval.py
  --target=skills/arm-new-track/SKILL.md
  --output=evals/skillopt/trajectory_eval_results.json
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

TARGET_MODEL = "gemini-3.5-flash"
SIMULATOR_MODEL = "gemini-3.1-pro-preview"
API_KEY = os.environ.get("GEMINI_API_KEY")

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
ARMATURE_ROOT = os.path.abspath(os.path.join(EVALS_DIR, "..", ".."))
TRAJECTORIES_PATH = os.path.join(EVALS_DIR, "tasks", "trajectories.jsonl")
DEFAULT_RESULTS_PATH = os.path.join(EVALS_DIR, "trajectory_eval_results.json")


def call_gemini(
    model: str,
    contents,
    system_instruction: str = None,
    temperature: float = 0.1,
    max_retries: int = 5,
) -> str:
  """Calls Gemini generateContent API supporting either string prompt or native multi-turn contents list."""
  if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is required.")

  url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
  tools = [{
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
      ]
  }]

  if isinstance(contents, str):
    formatted_contents = [{"role": "user", "parts": [{"text": contents}]}]
  else:
    formatted_contents = contents

  payload = {
      "contents": formatted_contents,
      "tools": tools,
      "generationConfig": {
          "temperature": temperature,
          "maxOutputTokens": 8192,
      },
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

  data = json.dumps(payload).encode("utf-8")

  for attempt in range(1, max_retries + 1):
    try:
      req = urllib.request.Request(
          url, data=data, headers={"Content-Type": "application/json"}
      )
      with urllib.request.urlopen(req, timeout=90) as resp:
        res_json = json.loads(resp.read().decode("utf-8"))
        candidates = res_json.get("candidates", [])
        if candidates and "content" in candidates[0]:
          parts = candidates[0]["content"].get("parts", [])
          texts = []
          for p in parts:
            if "text" in p and p["text"]:
              t = p["text"]
              if re.search(r"call:(?:[a-zA-Z0-9_]+:)?ask_question|ask_question\s*\{", t):
                t += "\n[PROTOCOL_VIOLATION: RAW_TOOL_TEXT_LEAK_DETECTED]"
              if re.search(r"I will now ask[^\n]*$", t.strip()):
                t += "\n[PROTOCOL_VIOLATION: TRAILING_NARRATION_DETECTED]"
              texts.append(t)
            elif "functionCall" in p:
              fc = p["functionCall"]
              texts.append(
                  "\n\n[TOOL_CALL:"
                  f" {fc.get('name')}({json.dumps(fc.get('args', {}))})]\n\n"
              )
            elif "thought" in p and p["thought"]:
              texts.append(p["thought"])
          if texts:
            return "".join(texts)
        if candidates and "finishReason" in candidates[0]:
          finish_reason = candidates[0]["finishReason"]
          if finish_reason not in ("STOP", "MAX_TOKENS"):
            print(
                f"  [API Warning] finishReason: {finish_reason}",
                file=sys.stderr,
                flush=True,
            )
        return ""
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
      if attempt == max_retries:
        if isinstance(e, urllib.error.HTTPError) and e.code in (500, 502, 503, 504) and model != "gemini-3.5-flash":
          print(f"  [Fallback] Model {model} returned {e.code}. Falling back to gemini-3.5-flash...", file=sys.stderr, flush=True)
          return call_gemini("gemini-3.5-flash", contents, system_instruction, temperature, max_retries)
        raise
      sleep_time = min(30, 2 ** attempt)
      print(f"  [API Retry] Attempt {attempt}/{max_retries} failed ({e}), sleeping {sleep_time}s...", file=sys.stderr, flush=True)
      time.sleep(sleep_time)
  return ""


def parse_agent_turn(turn_text: str):
  """Extracts tool calls, ledger presence, questions, and potential dictations from an agent turn."""
  has_protocol_violation = "[PROTOCOL_VIOLATION:" in turn_text
  has_ask_question = (
      not has_protocol_violation
      and "[TOOL_CALL: ask_question" in turn_text
  )
  has_ledger = bool(
      re.search(
          r"###?\s+(?:Active\s+)?Decision Tree (?:Ledger|Status)",
          turn_text,
          re.IGNORECASE,
      )
  )
  wrote_spec = bool(
      re.search(
          r"write_to_file.*?spec\.md|Created file.*?spec\.md",
          turn_text,
          re.IGNORECASE | re.DOTALL,
      )
  )
  has_devil_advocate = bool(
      re.search(
          r"###?\s*(?:Phase\s*5b:\s*)?Devil's Advocate Analysis",
          turn_text,
          re.IGNORECASE,
      )
  )
  has_phase_5c_triage = bool(
      re.search(
          r"###?\s*(?:Phase\s*5c:\s*)?ADR Candidate Triage|ADR Candidate Triage Table",
          turn_text,
          re.IGNORECASE,
      )
  )
  has_pros = bool(re.search(r"[-*#]\s+\*{0,2}Pros\*{0,2}:?", turn_text, re.IGNORECASE))
  has_cons = bool(re.search(r"[-*#]\s+\*{0,2}Cons\*{0,2}:?", turn_text, re.IGNORECASE))
  has_recommendation_rationale = bool(
      re.search(
          r"(?:###|####|\*{0,2})\s*Recommendation Rationale\*{0,2}:?",
          turn_text,
          re.IGNORECASE,
      )
  )
  has_option_trade_offs = has_pros and has_cons and has_recommendation_rationale
  has_elaboration_option = bool(
      re.search(r"Elaborate on (?:the )?trade-offs", turn_text, re.IGNORECASE)
  )
  has_provenance = bool(
      re.search(r"\(Spawned by ['\"].+?['\"]", turn_text, re.IGNORECASE)
  )

  # Count branches and leaves in ledger if present
  ledger_branches_raw = re.findall(
      r"-\s*\[([ xX])\]\s*(?:\*\*|\*|__|_)?\s*Branch\s*([\d\.]*):\s*([^\n]+)",
      turn_text,
      re.IGNORECASE,
  )
  ledger_branches = []
  for status, bnum, btext in ledger_branches_raw:
    clean_b = re.sub(r"[\*_]+", "", btext)
    clean_b = re.split(
        r"\s+\((?:Confirmed|Resolved|OPEN|UNEXPLORED)",
        clean_b,
        flags=re.IGNORECASE,
    )[0].strip()
    branch_key = f"Branch {bnum}: {clean_b}" if bnum else clean_b
    ledger_branches.append((status, branch_key))

  ledger_leaves_raw = re.findall(
      r"\s+-\s*\[([ xX])\]\s*(?:\*\*|\*|__|_)?\s*Leaf\s*[\d\.]*:\s*([^\n]+)",
      turn_text,
      re.IGNORECASE,
  )
  ledger_leaves = []
  for status, ltext in ledger_leaves_raw:
    clean_l = re.sub(r"[\*_]+", "", ltext)
    clean_l = re.split(
        r"\s+\((?:Confirmed|Resolved|OPEN|UNEXPLORED|Spawned by)",
        clean_l,
        flags=re.IGNORECASE,
    )[0].strip()
    ledger_leaves.append((status, clean_l))

  # Check if there are open items left in the current ledger
  open_branches = [b for status, b in ledger_branches if status.strip() == ""]
  open_leaves = [l for status, l in ledger_leaves if status.strip() == ""]

  is_convergence = (
      not has_devil_advocate
      and not has_phase_5c_triage
      and len(open_branches) == 0
      and len(open_leaves) == 0
      and bool(
          re.search(
              r"###?\s*(?:Step\s*6:\s*)?Convergence Summary|Ready to materialize (?:the )?(?:track )?spec|Confirm and materialize|Final Confirmation.*spec",
              turn_text,
              re.IGNORECASE,
          )
      )
  )

  return {
      "has_ask_question": has_ask_question,
      "has_ledger": has_ledger,
      "wrote_spec": wrote_spec,
      "is_convergence": is_convergence,
      "has_devil_advocate": has_devil_advocate,
      "has_phase_5c_triage": has_phase_5c_triage,
      "has_option_trade_offs": has_option_trade_offs,
      "has_recommendation_rationale": has_recommendation_rationale,
      "has_elaboration_option": has_elaboration_option,
      "has_provenance": has_provenance,
      "ledger_branches": ledger_branches,
      "ledger_leaves": ledger_leaves,
      "open_branches_count": len(open_branches),
      "open_leaves_count": len(open_leaves),
      "raw_text": turn_text,
  }


def get_user_response(
    scenario: dict,
    turn_idx: int,
    agent_output: str,
    history: list,
    used_indices: set = None,
    parsed: dict = None,
) -> str:
  """Retrieves scripted user response or simulates dynamic engineer reply."""
  if used_indices is None:
    used_indices = set()
  user_script = scenario.get("user_responses", [])
  agent_lower = agent_output.lower()

  # Identify special phase indices
  triage_indices = [
      i
      for i, item in enumerate(user_script)
      if any(
          m in ["triage", "adr", "candidate", "record adr"]
          for m in item.get("matches", [])
      )
  ]
  devil_indices = [
      i
      for i, item in enumerate(user_script)
      if any(
          m in ["devil", "reaffirm", "address the devil"]
          for m in item.get("matches", [])
      )
  ]
  convergence_indices = [
      i
      for i, item in enumerate(user_script)
      if any(
          m in ["ready", "materialize", "convergence", "summary", "spec"]
          for m in item.get("matches", [])
      )
  ]
  special_indices = set(triage_indices + devil_indices + convergence_indices)

  # Check special phases first
  if parsed:
    if (
        parsed.get("has_phase_5c_triage")
        or "adr candidate triage" in agent_lower
    ):
      for idx in triage_indices:
        if idx not in used_indices:
          used_indices.add(idx)
          return user_script[idx]["response"]

    if parsed.get("has_devil_advocate") or "devil's advocate" in agent_lower:
      for idx in devil_indices:
        if idx not in used_indices:
          used_indices.add(idx)
          return user_script[idx]["response"]

    if (
        parsed.get("is_convergence")
        or "materialize spec" in agent_lower
        or "ready to materialize" in agent_lower
    ):
      for idx in convergence_indices:
        if idx not in used_indices:
          used_indices.add(idx)
          return user_script[idx]["response"]

  # For standard interview turns, match against unconsumed regular items
  for idx, item in enumerate(user_script):
    if idx in used_indices or idx in special_indices:
      continue
    matches = item.get("matches", [])
    if any(m.lower() in agent_lower for m in matches):
      used_indices.add(idx)
      return item["response"]

  # Fallback to next unconsumed regular scripted response
  for idx, item in enumerate(user_script):
    if idx not in used_indices and idx not in special_indices:
      used_indices.add(idx)
      return item["response"]

  # Fallback simulator model call if scripted responses exhausted
  sim_prompt = f"""You are a senior software engineer participating in a requirements interview with an AI architect.
Scenario Goal: {scenario['description']}
Initial Request: {scenario['prompt']}

Conversation History:
{json.dumps(history, indent=2)}

Agent's Latest Turn:
{agent_output}

Provide a concise, realistic, pragmatic technical answer (1-2 sentences) picking the recommended option or clarifying technical constraints.
"""
  return call_gemini(SIMULATOR_MODEL, sim_prompt, temperature=0.2).strip()


def run_trajectory(
    scenario: dict, skill_text: str, max_turns: int = 12
) -> dict:
  """Runs a full multi-turn conversational trajectory and computes deterministic metrics."""
  # Unconfounded system instruction: Pure skill text without redundant duplicate prompt rules
  system_instruction = (
      "You are an expert AI software architect running the Armature"
      " context-driven development system in enterprise monorepo.\nExecute the following"
      f" skill instructions strictly:\n\n{skill_text}"
  )

  contents = []
  history = []
  transcript = []
  current_prompt = f"User Request: {scenario['prompt']}"

  total_turns = 0
  interview_turns = 0
  ledger_turns = 0
  interactive_question_turns = 0
  dictation_violations = 0
  premature_spec_writes = 0
  convergence_reached = False
  used_response_indices = set()

  root_branches_observed = set()
  child_leaves_observed = set()
  devil_advocate_observed = False
  phase_5c_triage_observed = False
  sequence_barrier_violations = 0
  option_trade_off_turns = 0
  question_turns_total = 0
  prepopulation_violations = 0
  provenance_tags_count = 0

  anti_dict_targets = scenario.get("anti_dictation_targets", [])

  for turn_idx in range(1, max_turns + 1):
    total_turns += 1

    contents.append({"role": "user", "parts": [{"text": current_prompt}]})

    try:
      agent_output = call_gemini(
          TARGET_MODEL,
          contents,
          system_instruction=system_instruction,
          temperature=0.1,
      )
    except Exception as e:
      agent_output = f"[Error: {e}]"

    contents.append({"role": "model", "parts": [{"text": agent_output}]})

    parsed = parse_agent_turn(agent_output)

    if parsed["has_ask_question"]:
      interactive_question_turns += 1
      if (
          not parsed["is_convergence"]
          and not parsed["has_devil_advocate"]
          and not parsed["has_phase_5c_triage"]
      ):
        question_turns_total += 1
        if parsed["has_option_trade_offs"]:
          option_trade_off_turns += 1

    if parsed["has_devil_advocate"]:
      devil_advocate_observed = True

    if parsed["has_phase_5c_triage"]:
      phase_5c_triage_observed = True

    # Sequence barrier check: spec must not be written before devil's advocate and phase 5c
    if parsed["wrote_spec"]:
      if not devil_advocate_observed or (
          not phase_5c_triage_observed and not parsed["has_phase_5c_triage"]
      ):
        sequence_barrier_violations += 1

    if parsed["has_provenance"]:
      provenance_tags_count += 1

    # Count turns where decision tree ledger is expected (interview turns before convergence/spec writing, excluding devil's advocate and phase 5c triage)
    if (
        parsed["has_ask_question"]
        and not parsed["wrote_spec"]
        and not parsed["is_convergence"]
        and not parsed["has_devil_advocate"]
        and not parsed["has_phase_5c_triage"]
    ):
      interview_turns += 1

    # Check for Decision Tree Ledger
    if parsed["has_ledger"]:
      ledger_turns += 1
      for status, bname in parsed["ledger_branches"]:
        root_branches_observed.add(bname.strip())
      for status, lname in parsed["ledger_leaves"]:
        child_leaves_observed.add(lname.strip())

      # Turn 1 pre-population check: strictly bound leaves to active branch (at most 2)
      if turn_idx == 1:
        turn1_leaves = len(parsed["ledger_leaves"])
        if turn1_leaves > 2:
          prepopulation_violations += turn1_leaves - 2

    # Check for Anti-Dictation violations (declaring implementation targets without prior question)
    user_inputs = [current_prompt] + [
        t["content"] for t in history if t.get("role") == "USER"
    ]
    for target in anti_dict_targets:
      target_mentioned = any(target.lower() in u.lower() for u in user_inputs)
      if not target_mentioned and " " in target:
        target_words = target.lower().split()
        target_mentioned = any(
            all(w in u.lower() for w in target_words) for u in user_inputs
        )

      if target.lower() in agent_output.lower() and not target_mentioned:
        # If target appears as an option choice in ask_question (or tool call arguments), it is a valid probe, not dictation
        in_options = bool(
            re.search(
                r'["\']?options["\']?\s*:\s*\[.*?' + re.escape(target),
                agent_output,
                re.IGNORECASE | re.DOTALL,
            )
        )
        if in_options or parsed["is_convergence"]:
          continue

        # Check if declared in declarative non-ledger bullet format
        for line in agent_output.splitlines():
          line_str = line.strip()
          # Skip ledger items: e.g. - [ ], - [x], * [ ], * [x], or (Resolved: ...)
          if (
              re.match(r"^[-*]\s*\[[ xX]\]", line_str)
              or "(Resolved:" in line_str
          ):
            continue
          # If it is a regular bullet asserting the target as fact outside the ledger
          if (
              re.match(r"^[-*]\s+", line_str)
              and target.lower() in line_str.lower()
          ):
            dictation_violations += 1
            break

    # Check for Premature spec write (spec written before interview complete, devil's advocate, or with open items)
    if parsed["wrote_spec"]:
      if (
          not devil_advocate_observed
          or (
              not phase_5c_triage_observed and not parsed["has_phase_5c_triage"]
          )
          or parsed.get("open_branches_count", 0) > 0
          or parsed.get("open_leaves_count", 0) > 0
      ):
        premature_spec_writes += 1

    transcript.append({
        "turn": turn_idx,
        "user_input": current_prompt,
        "agent_output": agent_output,
        "parsed": parsed,
    })

    history.append(
        {"turn": turn_idx, "role": "USER", "content": current_prompt}
    )
    history.append({"turn": turn_idx, "role": "AGENT", "content": agent_output})

    # Natural convergence is confirmed when convergence summary / confirmation is emitted or spec is written after interview completion
    if parsed["is_convergence"] or (
        parsed["wrote_spec"]
        and devil_advocate_observed
        and phase_5c_triage_observed
    ):
      convergence_reached = True

    if parsed["wrote_spec"]:
      break

    # Get next simulated user reply
    current_prompt = get_user_response(
        scenario,
        turn_idx,
        agent_output,
        history,
        used_indices=used_response_indices,
        parsed=parsed,
    )

  # Compute Metrics
  num_roots = max(
      len(root_branches_observed),
      len(scenario.get("required_root_branches", [])),
  )
  num_leaves = len(child_leaves_observed)
  leaf_depth_ratio = (num_leaves / num_roots) if num_roots > 0 else 0.0
  ledger_fidelity = (
      min(1.0, (ledger_turns / interview_turns))
      if interview_turns > 0
      else ((ledger_turns / total_turns) if total_turns > 0 else 0.0)
  )

  depth_passed = leaf_depth_ratio >= scenario.get("min_leaf_depth", 1.5)
  dictation_passed = dictation_violations == 0
  ledger_passed = ledger_fidelity >= 0.8
  premature_passed = premature_spec_writes == 0
  convergence_passed = convergence_reached
  adversarial_passed = devil_advocate_observed
  prepopulation_passed = prepopulation_violations == 0
  phase_5c_passed = phase_5c_triage_observed
  sequence_barrier_passed = sequence_barrier_violations == 0

  overall_passed = (
      depth_passed
      and dictation_passed
      and ledger_passed
      and premature_passed
      and convergence_passed
      and adversarial_passed
      and prepopulation_passed
      and phase_5c_passed
      and sequence_barrier_passed
  )

  return {
      "id": scenario["id"],
      "domain": scenario["domain"],
      "total_turns": total_turns,
      "interactive_question_turns": interactive_question_turns,
      "num_roots": num_roots,
      "num_leaves": num_leaves,
      "leaf_depth_ratio": round(leaf_depth_ratio, 2),
      "dictation_violations": dictation_violations,
      "ledger_fidelity": round(ledger_fidelity, 2),
      "premature_spec_writes": premature_spec_writes,
      "convergence_reached": convergence_reached,
      "adversarial_observed": devil_advocate_observed,
      "phase_5c_triage_observed": phase_5c_triage_observed,
      "sequence_barrier_violations": sequence_barrier_violations,
      "option_trade_off_turns": option_trade_off_turns,
      "question_turns_total": question_turns_total,
      "prepopulation_violations": prepopulation_violations,
      "provenance_tags_count": provenance_tags_count,
      "metrics": {
          "depth_passed": depth_passed,
          "dictation_passed": dictation_passed,
          "ledger_passed": ledger_passed,
          "premature_passed": premature_passed,
          "convergence_passed": convergence_passed,
          "adversarial_passed": adversarial_passed,
          "prepopulation_passed": prepopulation_passed,
          "phase_5c_passed": phase_5c_passed,
          "sequence_barrier_passed": sequence_barrier_passed,
      },
      "passed": overall_passed,
      "transcript": transcript,
  }


def main():
  parser = argparse.ArgumentParser(
      description="Multi-Turn Trajectory Evaluation Runner"
  )
  parser.add_argument(
      "--target",
      default="skills/arm-new-track/SKILL.md",
      help="Path to target skill markdown file",
  )
  parser.add_argument(
      "--scenarios", default=TRAJECTORIES_PATH, help="Path to scenarios jsonl"
  )
  parser.add_argument(
      "--output",
      default=DEFAULT_RESULTS_PATH,
      help="Path to output results JSON",
  )
  parser.add_argument(
      "--max_turns", type=int, default=14, help="Max turns per scenario"
  )
  args = parser.parse_args()

  skill_file = (
      os.path.join(ARMATURE_ROOT, args.target)
      if not os.path.isabs(args.target)
      else args.target
  )
  if not os.path.exists(skill_file):
    print(
        f"Error: Skill file not found at {skill_file}",
        file=sys.stderr,
        flush=True,
    )
    sys.exit(1)

  with open(skill_file, "r", encoding="utf-8") as f:
    skill_text = f.read()

  with open(args.scenarios, "r", encoding="utf-8") as f:
    scenarios = [json.loads(line.strip()) for line in f if line.strip()]

  print(
      f"\n================================================================================",
      flush=True,
  )
  print(
      "🚀 Running Multi-Turn Trajectory Evaluation on"
      f" {os.path.basename(skill_file)}",
      flush=True,
  )
  print(
      f"Target Model: {TARGET_MODEL} | Total Scenarios: {len(scenarios)} | Max"
      f" Turns: {args.max_turns}",
      flush=True,
  )
  print(
      f"================================================================================\n",
      flush=True,
  )

  results = []
  for sc in scenarios:
    print(f"▶ Evaluating Scenario [{sc['id']}]: {sc['domain']}...", flush=True)
    res = run_trajectory(sc, skill_text, max_turns=args.max_turns)
    status_icon = "✅ PASS" if res["passed"] else "❌ FAIL"
    print(
        f"  {status_icon} | Turns: {res['total_turns']} | Q-Turns:"
        f" {res['interactive_question_turns']} | Roots: {res['num_roots']} |"
        f" Leaves: {res['num_leaves']} | Depth Ratio: {res['leaf_depth_ratio']}"
        f" | Pre-pop Violations: {res['prepopulation_violations']} |"
        " Adversarial Critique:"
        f" {'YES' if res['adversarial_observed'] else 'NO'} | Phase 5c Triage:"
        f" {'YES' if res['phase_5c_triage_observed'] else 'NO'} | Seq Violations:"
        f" {res['sequence_barrier_violations']} | Dictations:"
        f" {res['dictation_violations']} | Ledger:"
        f" {int(res['ledger_fidelity']*100)}%",
        flush=True,
    )
    results.append(res)

  passed_count = sum(1 for r in results if r["passed"])
  total_count = len(results)
  pass_rate = (passed_count / total_count) * 100

  print(
      f"\n================================================================================",
      flush=True,
  )
  print(
      f"📊 Trajectory Evaluation Summary: {passed_count}/{total_count} Passed"
      f" ({pass_rate:.1f}%)",
      flush=True,
  )
  print(
      f"================================================================================",
      flush=True,
  )
  for r in results:
    icon = "✅" if r["passed"] else "❌"
    print(
        f" {icon} {r['id']:<42} | Depth: {r['leaf_depth_ratio']:<4} | Pre-pop:"
        f" {r['prepopulation_violations']} | Devil:"
        f" {'YES' if r['adversarial_observed'] else 'NO':<3} | P5c:"
        f" {'YES' if r['phase_5c_triage_observed'] else 'NO':<3} | SeqViol:"
        f" {r['sequence_barrier_violations']:<2} | Dictations:"
        f" {r['dictation_violations']} | Ledger:"
        f" {int(r['ledger_fidelity']*100)}%",
        flush=True,
    )

  with open(args.output, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

  print(f"\nDetailed trajectory results saved to: {args.output}\n", flush=True)


if __name__ == "__main__":
  main()
