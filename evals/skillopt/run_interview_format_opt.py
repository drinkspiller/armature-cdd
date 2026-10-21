#!/usr/bin/env python3
"""SkillOpt harness for the Armature Interview Turn v2 format.

Evaluates and optimizes the compact interview turn (unlabeled stakes opener,
numbered one-line options, ignore line, one-sentence recommendation, Pick-if
recap, mirrored ask_question options) across K seeds with a Two-Tier rubric:
deterministic [INVARIANT] vetoes plus LLM-judged [QUALITY] partial credit.

Phases:
  --phase baseline   Score the pre-change files (origin/main, falling back to
                     HEAD~1 when no remote-tracking branch is available).
  --phase eval       Score the working copy.
  --phase optimize   Run reflection epochs that patch arm-new-track/SKILL.md,
                     promoting a candidate only when the K-seed lower bound on
                     held-out validation beats the current best with 0 vetoes.
"""

import argparse
import concurrent.futures
import datetime
import difflib
import json
import math
import os
import random
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

socket.setdefaulttimeout(120)

TARGET_MODELS = ["gemini-flash-latest", "gemini-3.7-flash", "gemini-3.5-flash"]
JUDGE_MODELS = ["gemini-3.1-pro-preview", "gemini-pro-latest", "gemini-flash-latest"]
OPTIMIZER_MODELS = [
    "gemini-3.1-pro-preview",
    "gemini-pro-latest",
    "gemini-flash-latest",
]
API_KEY = os.environ.get("GEMINI_API_KEY")

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
ARMATURE_ROOT = os.path.abspath(os.path.join(EVALS_DIR, "..", ".."))
SKILL_REL = "skills/arm-new-track/SKILL.md"
PROTOCOL_REL = "rules/armature_protocol.md"
ANTIGRAVITY_REL = "rules/armature_antigravity.md"
TRAIN_PATH = os.path.join(EVALS_DIR, "tasks", "train_interview_format.jsonl")
VAL_PATH = os.path.join(EVALS_DIR, "tasks", "val_interview_format.jsonl")
RESULTS_JSON_PATH = os.path.join(EVALS_DIR, "interview_format_eval_results.json")
REPORT_MD_PATH = os.path.join(EVALS_DIR, "skillopt_report_interview_format.md")

BASE_TOOL_DECLARATIONS = [{
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
    ]
}]

READ_TOOL_DECLARATIONS = [{
    "functionDeclarations": (
        BASE_TOOL_DECLARATIONS[0]["functionDeclarations"]
        + [
            {
                "name": "view_file",
                "description": (
                    "View the contents of a file from the local filesystem."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "AbsolutePath": {"type": "STRING"},
                    },
                    "required": ["AbsolutePath"],
                },
            },
            {
                "name": "code_search",
                "description": "Search source files in the codebase.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "Query": {"type": "STRING"},
                    },
                    "required": ["Query"],
                },
            },
        ]
    )
}]


# --------------------------------------------------------------------------
# Gemini transport
# --------------------------------------------------------------------------
def call_gemini(
    models,
    prompt,
    system_instruction=None,
    temperature=0.2,
    use_tools=False,
    include_read_tools=False,
    max_retries=6,
    max_output_tokens=8192,
    json_mode=False,
):
  if not API_KEY:
    sys.exit("ERROR: GEMINI_API_KEY is not set.")
  for model in models:
    for attempt in range(1, max_retries + 1):
      url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
             f"{model}:generateContent?key={API_KEY}")
      gen_cfg = {"temperature": temperature, "maxOutputTokens": max_output_tokens}
      if json_mode:
        gen_cfg["responseMimeType"] = "application/json"
      payload = {
          "contents": [{"parts": [{"text": prompt}]}],
          "generationConfig": gen_cfg,
          "safetySettings": [
              {"category": c, "threshold": "BLOCK_NONE"} for c in (
                  "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                  "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                  "HARM_CATEGORY_DANGEROUS_CONTENT",
                  "HARM_CATEGORY_CIVIC_INTEGRITY")
          ],
      }
      if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
      if use_tools:
        payload["tools"] = (
            READ_TOOL_DECLARATIONS
            if include_read_tools
            else BASE_TOOL_DECLARATIONS
        )
      data = json.dumps(payload).encode("utf-8")
      try:
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
          res_json = json.loads(resp.read().decode("utf-8"))
        candidates = res_json.get("candidates", [])
        if not candidates or "content" not in candidates[0]:
          return "", []
        text_out, tool_calls = [], []
        for p in candidates[0]["content"].get("parts", []):
          if p.get("text"):
            text_out.append(p["text"])
          if "functionCall" in p:
            tool_calls.append(p["functionCall"])
        return "\n".join(text_out), tool_calls
      except urllib.error.HTTPError as e:
        if e.code == 404:
          print(
              f"  [transport] {model} -> HTTP 404; trying next model",
              file=sys.stderr,
              flush=True,
          )
          break
        if e.code in (429, 503) and attempt >= (5 if use_tools else 2):
          print(
              f"  [transport] {model} -> HTTP {e.code} after {attempt}"
              " attempts; trying next model",
              file=sys.stderr,
              flush=True,
          )
          break
        if attempt == max_retries:
          return f"[ERROR: HTTP {e.code}]", []
        time.sleep(
            min(12.0, 1.5 * (2 ** (attempt - 1))) + random.uniform(0.1, 0.9)
        )
      except Exception as e:  # pylint: disable=broad-except
        if attempt == max_retries:
          return f"[ERROR: {e}]", []
        time.sleep(2 ** attempt)
  return "[ERROR: all models failed]", []


# --------------------------------------------------------------------------
# Deterministic invariant checks
# --------------------------------------------------------------------------
HEADLINE_RE = re.compile(r"^#{2,4}\s+(?:Round\s+\d+,\s+Question\s+\d+\s+of\s+\d+|(?:Phase 5b,\s*)?Finding\s+\d+(?:\s+of\s+\d+)?):\s*\S", re.M)
ROUND_HEADLINE_RE = re.compile(r"^##\s+Round\s+\d+,\s+Question\s+\d+\s+of\s+\d+:\s*\S", re.M)
BAD_HEADLINE_RE = re.compile(r"^##\s+Round\s+\d+,\s+Question\s+\d+\.\d+\s+of", re.M)
NUMBERED_RE = re.compile(r"^\s*(\d+)\.\s+\S", re.M)
PICK_RE = re.compile(r"^\s*(?:-\s+)?Pick\s+\d+\s+if\b", re.M)
BULLETED_PICK_RE = re.compile(r"^\s*-\s+Pick\s+\d+\s+if\b", re.M)
REC_HEADING_RE = re.compile(
    r"^###\s+Recommendation:\s+Option\s+(\d+)\s*$", re.M
)
IGNORE_RE = re.compile(r"^\s*Safe to ignore for now:", re.M)
CARD_RE = re.compile(r"^>\s*\*\*Option\s+\d+", re.M)
LABEL_LINE_RE = re.compile(r"^\s*\*\*[A-Za-z][A-Za-z /]{1,30}:\*\*", re.M)
CONTEXT_OPT_RE = re.compile(
    r"^i need more context,\s*zoom out and give examples$", re.I
)
LEGACY_ELAB_RE = re.compile(r"compare technical trade-offs", re.I)
AUX_MODAL_OPT_RE = re.compile(
    r"^(?:reopen\s+round\b|customize\s+scan\s+sources\b)", re.I
)
CODE_ID_RE = re.compile(r"`|[A-Za-z]\w*_\w+|\b\w+\(\)|\b\w+\.\w+\(")
SYSTEMS_JARGON_RE = re.compile(
    r"\b(?:blob\w*|copy-on-write|refcount\w*|reference[- ]count\w*"
    r"|monotonic\w*|in-flight|file handle\w*|stream handle\w*"
    r"|in-place overwrite\w*|mint an?\b|idempoten\w*|fan-out"
    r"|race"
    r" condition\w*|mid-\w+\s+race\b|couples?\s+\w*\s*deletion|mutex\w*)\b",
    re.I,
)


def _extract_chat_option_name(line):
  s = re.sub(r"^\s*\d+\.\s*", "", line).strip()
  s = s.split(":", 1)[0].strip()
  s = re.sub(r"^\*\*|\*\*$", "", s).strip()
  return s


def _norm_opt(s):
  s = re.sub(r"^\(Recommended\)\s*", "", s, flags=re.I).strip()
  s = re.sub(r"\s*\(Option\s+\d+\)\s*$", "", s, flags=re.I).strip()
  s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
  return s


def _pre_retee_region(text):
  """Extracts the plain zoom-out explanation preceding '---' or the re-teed headline."""
  candidates = []
  for pat in (
      re.compile(r"^---\s*$", re.M),
      re.compile(r"^###\s+Devil's Advocate", re.M),
      re.compile(r"^\*\*(?:Settled|Now)\*\*", re.M),
      HEADLINE_RE,
  ):
    m = pat.search(text)
    if m:
      candidates.append(m.start())
  if not candidates:
    return ""
  return text[: min(candidates)].strip()


def _asq_options(tool_calls):
  opts = []
  for tc in tool_calls:
    if tc.get("name") != "ask_question":
      continue
    for q in tc.get("args", {}).get("questions", []) or []:
      opts.extend(q.get("options", []) or [])
  return opts


def _headline_and_body_region(text):
  """Returns (headline_line, opener_region, headline_to_last_pick_region)."""
  matches = list(HEADLINE_RE.finditer(text))
  if not matches:
    return "", "", ""
  hm = matches[-1]
  line_end = text.find("\n", hm.start())
  line_end = len(text) if line_end == -1 else line_end
  headline_line = text[hm.start() : line_end]
  after = text[line_end:]
  nm = NUMBERED_RE.search(after)
  opener = after[: nm.start()] if nm else after
  picks = list(PICK_RE.finditer(text[hm.start() :]))
  if picks:
    last = picks[-1]
    abs_end = hm.start() + last.end()
    end = text.find("\n", abs_end)
    end = len(text) if end == -1 else end
    body = text[hm.start() : end]
  else:
    body = text[hm.start() :]
  return headline_line, opener, body


def _body_region(text):
  """Returns (opener_region, headline_to_last_pick_region)."""
  _, opener, body = _headline_and_body_region(text)
  return opener, body


def evaluate_invariants(task, text, tool_calls):
  vetoes = []
  headline_line, opener, body = _headline_and_body_region(text)
  target_body = body or text
  numbered = NUMBERED_RE.findall(target_body)
  numbered_lines = [l for l in target_body.splitlines() if NUMBERED_RE.match(l)]
  picks = PICK_RE.findall(target_body)
  asq_opts = _asq_options(tool_calls)
  nonempty = [l for l in text.splitlines() if l.strip()]
  last_line = nonempty[-1] if nonempty else ""

  for inv in task.get("invariants", []):
    if inv == "has_ask_question_tool":
      if not any(tc.get("name") == "ask_question" for tc in tool_calls):
        vetoes.append(f"{inv}: no native ask_question call")
    elif inv == "no_read_search_tools":
      bad_tools = [
          tc.get("name")
          for tc in tool_calls
          if tc.get("name") in ("view_file", "code_search", "grep_search")
      ]
      if bad_tools:
        vetoes.append(
            f"{inv}: called {bad_tools} instead of answering from conversation"
            " context"
        )
    elif inv == "has_pre_turn_explanation":
      pre = _pre_retee_region(text)
      if len(pre.split()) < 25:
        vetoes.append(
            f"{inv}: fewer than 25 words of explanation before the re-teed"
            f" question ({len(pre.split())} words)"
        )
    elif inv == "has_concrete_example_before_progress":
      pre = _pre_retee_region(text)
      if len(pre.split()) < 35:
        vetoes.append(
            f"{inv}: fewer than 35 words of workflow zoom-out and concrete"
            f" examples before the re-teed question ({len(pre.split())} words)"
        )
      elif CARD_RE.search(pre):
        vetoes.append(
            f"{inv}: rendered blockquote Pros/Cons cards instead of plain"
            " workflow zoom-out and examples"
        )
    elif inv == "no_settled_on_clarification_retee":
      if re.search(
          r"^\s*\*\*(?:Settled|Now|Up next)\*\*", text, re.M
      ) or re.search(
          r"^(?:Round|Question)\s+\d+(?:\.\d+)?\s+settled:", text, re.M
      ):
        vetoes.append(
            f"{inv}: re-printed Settled/Now/Up next progress list on a"
            " clarification re-tee when zero items newly settled"
        )
    elif inv == "no_systems_jargon_in_turn":
      turn_surface = f"{headline_line}\n{opener}\n" + "\n".join(numbered_lines)
      jm = SYSTEMS_JARGON_RE.search(turn_surface)
      if jm:
        vetoes.append(
            f"{inv}: un-translated systems jargon '{jm.group(0)}' in Pass-1"
            " headline, opener, or numbered options"
        )
    elif inv == "grounds_familiar_domain_nouns":
      combined = f"{headline_line}\n{opener}"
      for group in task.get("expected_domain_noun_groups", []):
        if not any(
            re.search(rf"\b{re.escape(w)}\b", combined, re.I) for w in group
        ):
          vetoes.append(
              f"{inv}: headline/opener omitted familiar domain concept {group}"
          )
      for bad in task.get("unanchored_phrases", []):
        if re.search(re.escape(bad), combined, re.I):
          vetoes.append(
              f"{inv}: headline/opener used generic placeholder '{bad}'"
          )
    elif inv == "rewrites_vague_option_names":
      for phrase in task.get("forbidden_phrases", []):
        if re.search(re.escape(phrase), target_body, re.I) or any(
            re.search(re.escape(phrase), o, re.I) for o in asq_opts
        ):
          vetoes.append(
              f"{inv}: repeated vague phrase '{phrase}' verbatim in rewritten"
              " options"
          )
    elif inv == "headline_round_question_format":
      if not ROUND_HEADLINE_RE.search(text) or BAD_HEADLINE_RE.search(text):
        vetoes.append(f"{inv}: headline missing or uses 'Question R.Q of N'")
    elif inv == "no_labeled_opener":
      if not opener.strip():
        vetoes.append(f"{inv}: no opener paragraph between headline and options")
      elif LABEL_LINE_RE.search(opener):
        vetoes.append(f"{inv}: opener carries a bold label")
    elif inv == "no_problem_label":
      if re.search(r"\*\*Problem:?\*\*", text):
        vetoes.append(f"{inv}: found a Problem label")
    elif inv == "has_choice_sentence_some_options":
      if not re.search(r"The choice here is", text):
        vetoes.append(f"{inv}: missing 'The choice here is …'")
      if not re.search(r"Here are some options:", text):
        vetoes.append(f"{inv}: missing 'Here are some options:'")
      if re.search(r"Here are the options:", text):
        vetoes.append(f"{inv}: used 'the options' (implies exhaustive)")
    elif inv == "has_numbered_options":
      if len(numbered) < 2:
        vetoes.append(f"{inv}: fewer than 2 numbered options")
    elif inv == "no_numbered_tradeoff_options":
      if re.search(r"Here are some options:", text) or REC_HEADING_RE.search(text):
        vetoes.append(f"{inv}: rendered design options on a procedural gate")
    elif inv == "no_recommended_tag_in_list":
      if any("(Recommended)" in l for l in numbered_lines):
        vetoes.append(f"{inv}: '(Recommended)' tag inside the numbered list")
    elif inv == "has_ignore_line":
      if not IGNORE_RE.search(text):
        vetoes.append(f"{inv}: missing 'Safe to ignore for now:'")
    elif inv in ("has_recommendation_heading", "has_recommendation_heading_one_sentence"):
      m = REC_HEADING_RE.search(text)
      if not m:
        vetoes.append(f"{inv}: missing '### Recommendation: Option N'")
      elif inv.endswith("one_sentence"):
        tail = text[m.end():]
        pm = PICK_RE.search(tail)
        rationale = (tail[:pm.start()] if pm else tail).strip()
        sentences = len(re.findall(r"[.!?](?:\s|$)", rationale))
        if sentences != 1:
          vetoes.append(f"{inv}: rationale has {sentences} sentences, expected 1")
    elif inv == "has_pick_recap":
      bulleted_picks = BULLETED_PICK_RE.findall(target_body)
      if len(picks) < 2:
        vetoes.append(f"{inv}: fewer than 2 'Pick N if' lines")
      elif len(numbered) and len(picks) != len(numbered):
        vetoes.append(f"{inv}: {len(picks)} Pick lines for {len(numbered)} options")
      elif len(bulleted_picks) != len(picks):
        vetoes.append(
            f"{inv}: Pick lines must be formatted as Markdown bullets"
            " ('- Pick N if ...') so CommonMark renders each on its own line"
        )
    elif inv == "no_pick_recap":
      if picks:
        vetoes.append(f"{inv}: Pick recap rendered on a procedural gate")
    elif inv == "ends_with_pick_line":
      if not PICK_RE.match(last_line):
        vetoes.append(f"{inv}: trailing text after the last Pick line")
    elif inv == "no_blockquote_cards_default":
      if CARD_RE.search(text) or re.search(r"\*\*Pros:\*\*", text):
        vetoes.append(f"{inv}: rendered Pros/Cons blockquote cards in default turn")
    elif inv == "zoom_in_renders_cards":
      if len(CARD_RE.findall(text)) < 2 or not all(
          re.search(rf"\*\*{k}:\*\*", text) for k in ("Pros", "Cons", "Implications")):
        vetoes.append(f"{inv}: zoom-in did not render Pros/Cons/Implications cards")
    elif inv == "no_code_identifiers_in_opener":
      if CODE_ID_RE.search(opener):
        vetoes.append(f"{inv}: code identifier in opener")
    elif inv == "word_budget_200":
      limit = (
          260
          if "rewrites_vague_option_names" in task.get("invariants", [])
          else 200
      )
      n = len(body.split())
      if n > limit:
        vetoes.append(f"{inv}: {n} words from headline to last Pick line")
    elif inv in (
        "modal_options_match_chat_options",
        "modal_options_mirror_pick",
    ):
      if any(LEGACY_ELAB_RE.search(o) for o in asq_opts):
        vetoes.append(
            f"{inv}: used legacy 'Compare technical trade-offs...' modal option"
        )
      chat_names = [_extract_chat_option_name(l) for l in numbered_lines]
      core = [
          o
          for o in asq_opts
          if not CONTEXT_OPT_RE.search(o.strip())
          and not LEGACY_ELAB_RE.search(o)
          and not AUX_MODAL_OPT_RE.search(o.strip())
      ]
      rm = REC_HEADING_RE.search(text)
      if rm and rm.group(1) != "1":
        vetoes.append(
            f"{inv}: Recommendation must place Option 1 first (got Option"
            f" {rm.group(1)}) so modal and chat stay in 1:1 order"
        )
      if len(core) != len(chat_names):
        vetoes.append(
            f"{inv}: {len(core)} core modal options for {len(chat_names)}"
            " numbered chat options"
        )
      elif core:
        if not core[0].lstrip().startswith("(Recommended)"):
          vetoes.append(
              f"{inv}: first modal option missing '(Recommended)' prefix"
          )
        for idx, (m_opt, c_name) in enumerate(zip(core, chat_names), 1):
          sim = difflib.SequenceMatcher(
              None, _norm_opt(m_opt), _norm_opt(c_name)
          ).ratio()
          if sim < 0.80:
            vetoes.append(
                f"{inv}: modal option {idx} ('{m_opt}') did not match chat"
                f" Option {idx} name ('{c_name}')"
            )
    elif inv == "has_settled_now_list":
      if not re.search(r"\*\*Now\*\*", text):
        vetoes.append(f"{inv}: missing the Now progress group")
    elif inv == "settled_capped_at_five":
      m = re.search(r"\*\*Settled\*\*\s*\n((?:\s*-\s.*\n?)+)", text)
      bullets = [l for l in (m.group(1).splitlines() if m else []) if l.strip().startswith("-")]
      if len(bullets) > 6 or not any("earlier settled" in b for b in bullets):
        vetoes.append(f"{inv}: {len(bullets)} Settled bullets without a fold line")
      elif any(re.match(r"^\s*-\s*\+\s*\d+", b) for b in bullets):
        vetoes.append(
            f"{inv}: used nested double-bullet '- + N earlier settled' instead"
            " of '- (+N earlier settled)'"
        )
    elif inv in (
        "no_context_option_in_modal",
        "no_elaboration_option_in_modal",
    ):
      if any(
          CONTEXT_OPT_RE.search(o.strip()) or LEGACY_ELAB_RE.search(o)
          for o in asq_opts
      ):
        vetoes.append(
            f"{inv}: trailing context/elaboration option on an exempt decision"
        )
    elif inv in (
        "has_context_option_in_modal",
        "has_elaboration_option_in_modal",
    ):
      if any(LEGACY_ELAB_RE.search(o) for o in asq_opts):
        vetoes.append(
            f"{inv}: used deprecated 'Compare technical trade-offs...' instead"
            " of 'I need more context, zoom out and give examples'"
        )
      elif not any(CONTEXT_OPT_RE.search(o.strip()) for o in asq_opts):
        vetoes.append(
            f"{inv}: missing trailing 'I need more context, zoom out and give"
            " examples' modal option"
        )
    elif inv == "no_self_answered_risk_mitigation":
      if re.search(r"\*{1,2}(Risk|Mitigation):\*{1,2}", text):
        vetoes.append(f"{inv}: self-answered Risk/Mitigation list")
    elif inv == "no_bare_tool_call":
      if len(text.strip()) < 300:
        vetoes.append(f"{inv}: markdown shorter than a full interview turn")
  return vetoes


# --------------------------------------------------------------------------
# LLM judge for [QUALITY] criteria
# --------------------------------------------------------------------------
def judge_qualities(task, text, tool_calls):
  qualities = task.get("qualities", [])
  if not qualities:
    return 1.0, [], "", False
  prompt = f"""You are an impartial, rigorous evaluation judge. Score whether the agent's response satisfies each quality criterion.

Task Prompt:
{task['prompt']}

Agent Markdown Response:
{text}

Agent Tool Calls:
{json.dumps(tool_calls, indent=2)}

Quality Criteria (1.0 fully met, 0.5 partially met, 0.0 not met):
"""
  for i, q in enumerate(qualities, 1):
    prompt += f"{i}. {q}\n"
  prompt += """
Return JSON only:
{"scores": [{"criterion_index": 1, "score": 1.0, "reason": "brief"}],
 "optimizer_feedback": "One or two plain-language sentences describing the user-visible behavior gap, with no literal regexes, labels, or check names."}
"""
  for _ in range(2):
    out, _ = call_gemini(JUDGE_MODELS, prompt, temperature=0.0, json_mode=True)
    if out.startswith("[ERROR:"):
      continue
    try:
      parsed = json.loads(re.search(r"\{[\s\S]*\}", out).group(0))
      scores = parsed.get("scores", [])
      if scores and len(scores) == len(qualities):
        avg = sum(float(s.get("score", 0.0)) for s in scores) / len(qualities)
        return (
            min(1.0, max(0.0, avg)),
            scores,
            parsed.get("optimizer_feedback", ""),
            False,
        )
    except Exception:  # pylint: disable=broad-except
      continue
  return (
      0.0,
      [],
      "judge evaluation error (failed to parse structured rubric output)",
      True,
  )


# --------------------------------------------------------------------------
# Rollouts
# --------------------------------------------------------------------------
def build_system_instruction(protocol_text, antigravity_text, skill_text):
  return (
      "You are an AI coding agent running the Armature `/arm-new-track` skill "
      "inside an agentic IDE. Obey the rules and the skill below exactly. The "
      "project context directory is `armature/`; Steps 1-4 are already done "
      "unless the prompt says otherwise.\n\n"
      "# RULE: armature_protocol.md\n\n" + protocol_text +
      "\n\n# RULE: armature_antigravity.md\n\n" + antigravity_text +
      "\n\n# SKILL: arm-new-track/SKILL.md\n\n" + skill_text
  )


def evaluate_single_rollout(system_instruction, task, seed):
  inc_read = "no_read_search_tools" in task.get("invariants", [])
  text, tool_calls = call_gemini(
      TARGET_MODELS,
      task["prompt"],
      system_instruction=system_instruction,
      temperature=0.2 + 0.05 * (seed - 1),
      use_tools=True,
      include_read_tools=inc_read,
  )
  if text.startswith("[ERROR:"):
    return {
        "task_id": task["id"],
        "seed": seed,
        "vetoes": [f"transport_error: {text}"],
        "quality_score": 0.0,
        "final_score": 0.0,
        "passed": False,
        "transport_error": True,
        "judge_error": False,
        "optimizer_feedback": "",
        "text_preview": text[:600],
        "tool_calls": tool_calls,
    }
  vetoes = evaluate_invariants(task, text, tool_calls)
  if vetoes:
    return {
        "task_id": task["id"],
        "seed": seed,
        "vetoes": vetoes,
        "quality_score": 0.0,
        "final_score": 0.0,
        "passed": False,
        "transport_error": False,
        "judge_error": False,
        "optimizer_feedback": "",
        "text_preview": text[:600],
        "tool_calls": tool_calls,
    }
  q, details, fb, j_err = judge_qualities(task, text, tool_calls)
  return {
      "task_id": task["id"],
      "seed": seed,
      "vetoes": [],
      "quality_score": q,
      "final_score": q,
      "passed": (not j_err) and q >= 0.85,
      "transport_error": False,
      "judge_error": j_err,
      "q_details": details,
      "optimizer_feedback": fb,
      "text_preview": text[:600],
      "tool_calls": tool_calls,
  }


def evaluate_split(system_instruction, tasks, split_name, num_seeds, workers):
  total = len(tasks) * num_seeds
  print(f"[{split_name}] {len(tasks)} tasks x K={num_seeds} seeds = {total} rollouts",
        flush=True)
  rollouts, jobs = [], []
  task_by_id = {t["id"]: t for t in tasks}
  with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
    for seed in range(1, num_seeds + 1):
      for task in tasks:
        jobs.append(ex.submit(evaluate_single_rollout, system_instruction, task, seed))
    for n, fut in enumerate(concurrent.futures.as_completed(jobs), 1):
      r = fut.result()
      rollouts.append(r)
      print(f"[{split_name}] {n}/{total} {r['task_id']} seed={r['seed']} "
            f"score={r['final_score']:.2f} vetoes={len(r['vetoes'])}", flush=True)
  # Deflated Baseline Shield: retry transient transport/judge failures once.
  err_idxs = [
      i
      for i, r in enumerate(rollouts)
      if r.get("transport_error") or r.get("judge_error")
  ]
  if err_idxs:
    print(
        f"[{split_name}] Retrying {len(err_idxs)} transient error"
        " rollout(s)...",
        flush=True,
    )
    for i in err_idxs:
      old = rollouts[i]
      rollouts[i] = evaluate_single_rollout(
          system_instruction, task_by_id[old["task_id"]], old["seed"]
      )
  seed_scores = []
  for seed in range(1, num_seeds + 1):
    rs = [r for r in rollouts if r["seed"] == seed]
    seed_scores.append(sum(r["final_score"] for r in rs) / max(1, len(rs)))
  mean = sum(seed_scores) / len(seed_scores)
  var = sum((s - mean) ** 2 for s in seed_scores) / max(1, len(seed_scores) - 1)
  sd = math.sqrt(var)
  t_val = {2: 2.920, 3: 1.886, 4: 1.638, 5: 1.533}.get(num_seeds, 1.645)
  lb = mean - t_val * (sd / math.sqrt(num_seeds)) if num_seeds > 1 else mean
  vetoes = sum(len(r["vetoes"]) for r in rollouts)
  t_errs = sum(1 for r in rollouts if r.get("transport_error"))
  j_errs = sum(1 for r in rollouts if r.get("judge_error"))
  return {
      "split": split_name,
      "mean_score": mean,
      "std_dev": sd,
      "lb_90": lb,
      "seed_scores": seed_scores,
      "total_vetoes": vetoes,
      "transport_errors": t_errs,
      "judge_errors": j_errs,
      "pass_rate": (
          sum(1 for r in rollouts if r["passed"]) / max(1, len(rollouts))
      ),
      "rollouts": sorted(rollouts, key=lambda r: (r["task_id"], r["seed"])),
  }


# --------------------------------------------------------------------------
# Optimizer (reflection -> bounded find/replace patches on SKILL.md)
# --------------------------------------------------------------------------
def collect_feedback(split_result):
  notes = []
  for r in split_result["rollouts"]:
    if r["passed"]:
      continue
    gaps = []
    for v in r["vetoes"]:
      name = v.split(":", 1)[0]
      gaps.append(PLAIN_LANGUAGE.get(name, name.replace("_", " ")))
    if r.get("optimizer_feedback"):
      gaps.append(r["optimizer_feedback"])
    if gaps:
      notes.append(f"- Scenario kind '{r['task_id'].split('_', 3)[-1].lower()}': "
                   + "; ".join(sorted(set(gaps))))
  return "\n".join(sorted(set(notes)))


PLAIN_LANGUAGE = {
    "has_ask_question_tool": (
        "ended the turn without asking the user via the question modal"
    ),
    "no_read_search_tools": (
        "called a file-read or code-search tool when asked for more context or"
        " option clarification instead of answering from conversation context"
    ),
    "has_pre_turn_explanation": (
        "did not unpack the options in concrete everyday terms before the"
        " progress list when the user asked for clarification"
    ),
    "has_concrete_example_before_progress": (
        "when asked for more context, did not step back above the progress list"
        " to explain why the decision arises in the workflow with concrete"
        " domain examples"
    ),
    "grounds_familiar_domain_nouns": (
        "used generic placeholders or unanchored state qualifiers in the"
        " headline or opener instead of naming the familiar domain objects from"
        " the user's request"
    ),
    "rewrites_vague_option_names": (
        "copy-pasted the prior turn's vague option names verbatim instead of"
        " rewriting them in plain user-action terms"
    ),
    "headline_round_question_format": (
        "the round headline was missing or numbered the question like a"
        " sub-section"
    ),
    "no_labeled_opener": (
        "the opening paragraph was missing or started with a bold label"
    ),
    "no_problem_label": "framed a preference question as a problem",
    "has_choice_sentence_some_options": (
        "did not state the decision in one sentence followed by a"
        " non-exhaustive options lead-in"
    ),
    "has_numbered_options": "options were not a short numbered list",
    "no_numbered_tradeoff_options": (
        "offered design options on a step that only needed approval"
    ),
    "no_recommended_tag_in_list": (
        "tagged an option in the list as recommended instead of using the"
        " recommendation heading"
    ),
    "has_ignore_line": (
        "did not tell the reader which mechanics are safe to ignore"
    ),
    "has_recommendation_heading": "no recommendation heading",
    "has_recommendation_heading_one_sentence": (
        "the recommendation rationale was longer than one sentence or missing"
    ),
    "has_pick_recap": (
        "did not close with one bulleted '- Pick N if' line per option"
    ),
    "no_pick_recap": "added a pick recap to an approval step",
    "ends_with_pick_line": "added narration after the pick recap",
    "no_blockquote_cards_default": (
        "rendered the long pros/cons cards instead of keeping the compact turn"
    ),
    "zoom_in_renders_cards": (
        "did not expand to the detailed pros/cons cards when the user"
        " explicitly wrote in zoom-in"
    ),
    "no_code_identifiers_in_opener": "used code names in the opening paragraph",
    "no_systems_jargon_in_turn": (
        "leaked backend systems jargon (such as blob, copy-on-write, refcount,"
        " in-flight, or file handles) into a first-pass interview turn"
    ),
    "word_budget_200": (
        "the body from headline to the last pick line was too long"
    ),
    "modal_options_match_chat_options": (
        "the modal choices did not match the numbered option names in 1:1"
        " order, put the recommended option first, or replace deprecated"
        " context wording"
    ),
    "modal_options_mirror_pick": (
        "the modal choices did not match the numbered option names in 1:1"
        " order, put the recommended option first, or replace deprecated"
        " context wording"
    ),
    "has_settled_now_list": (
        "dropped the Settled / Now progress list mid-interview"
    ),
    "no_settled_on_clarification_retee": (
        "repeated the Settled / Now progress list inside a clarification"
        " re-tee instead of omitting it"
    ),
    "settled_capped_at_five": (
        "listed more than five settled items without folding older ones"
    ),
    "no_context_option_in_modal": (
        "offered a trailing context option on a pure copy choice or procedural"
        " gate"
    ),
    "no_elaboration_option_in_modal": (
        "offered a trailing context option on a pure copy choice or procedural"
        " gate"
    ),
    "has_context_option_in_modal": (
        "omitted the trailing request-more-context option on a substantive"
        " decision modal or used deprecated wording"
    ),
    "has_elaboration_option_in_modal": (
        "omitted the trailing request-more-context option on a substantive"
        " decision modal or used deprecated wording"
    ),
    "no_self_answered_risk_mitigation": (
        "answered its own devil's-advocate finding with a risk/mitigation list"
        " instead of asking"
    ),
    "no_bare_tool_call": (
        "emitted a bare modal without re-rendering the interview turn"
    ),
}


def propose_patch(skill_text, feedback, baseline_val, epoch):
  step = ("Prefer adding a short, explicit rule or a worked example near the "
          "existing interview-turn layout." if baseline_val < 0.70 else
          "Make minimal, surgical phrasing edits; do not add new sections.")
  prompt = f"""You are optimizing an agent skill document (Markdown) so that an LLM agent following it renders interview turns correctly.

Observed behavior gaps on training scenarios (plain language, no test internals):
{feedback or '- (none recorded)'}

Guidance for this epoch ({epoch}): {step}
Constraints:
- Return at most 6 edits as JSON: {{"edits": [{{"find": "<exact existing substring>", "replace": "<replacement>"}}], "rationale": "<one sentence>"}}
- Each "find" must appear exactly once in the document and be copied verbatim (including whitespace).
- Keep edits inside the Step 5 interview sections. Do not touch YAML frontmatter or headings above Step 5.
- Express fixes as universal interaction principles, never as scenario-specific keywords or domain names.
- Wrap prose at ~80 columns like the surrounding text. Avoid first-person plural.

Document:
<<<SKILL
{skill_text}
SKILL>>>
"""
  out, _ = call_gemini(OPTIMIZER_MODELS, prompt, temperature=0.4,
                       max_output_tokens=16384, json_mode=True)
  try:
    parsed = json.loads(re.search(r"\{[\s\S]*\}", out).group(0))
  except Exception:  # pylint: disable=broad-except
    return None, "optimizer returned non-JSON"
  new_text = skill_text
  applied = 0
  for e in parsed.get("edits", [])[:6]:
    f, r = e.get("find", ""), e.get("replace", "")
    if f and new_text.count(f) == 1:
      new_text = new_text.replace(f, r)
      applied += 1
  if applied == 0:
    return None, "no edit matched exactly once"
  return new_text, parsed.get("rationale", "")


def guard_metrics(seed_text, cand_text):
  st, ct = re.split(r"\s+", seed_text.strip()), re.split(r"\s+", cand_text.strip())
  ratio = 1.0 - difflib.SequenceMatcher(None, st, ct).ratio()
  tokens = len(ct) / max(1, len(st))
  ok_front = cand_text.startswith("---") and "\nname: arm-new-track" in cand_text[:400]
  return {"token_diff_ratio": ratio, "token_ratio": tokens,
          "frontmatter_ok": ok_front,
          "passed": ratio <= 0.35 and tokens <= 1.20 and ok_front}


# --------------------------------------------------------------------------
# File access
# --------------------------------------------------------------------------
def read_working(rel):
  with open(os.path.join(ARMATURE_ROOT, rel), "r", encoding="utf-8") as f:
    return f.read()


def read_parent(rel):
  """Reads the pre-change baseline of a file from git.

  Prefers ``origin/main`` so the baseline is the last published revision;
  falls back to ``HEAD~1`` when no remote-tracking branch exists.
  """
  for ref in ("origin/main", "HEAD~1"):
    proc = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=ARMATURE_ROOT,
                          capture_output=True, text=True)
    if proc.returncode == 0:
      return proc.stdout
  raise RuntimeError(f"Could not read baseline for {rel} from origin/main or HEAD~1")


def load_tasks(path):
  with open(path, "r", encoding="utf-8") as f:
    return [json.loads(l) for l in f if l.strip()]


def load_results():
  if os.path.exists(RESULTS_JSON_PATH):
    with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
      return json.load(f)
  return {}


def save_results(data):
  with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)


def summarize(label, res):
  print(f"{label}: train {res['train']['mean_score']:.4f} "
        f"(vetoes {res['train']['total_vetoes']}) | val {res['val']['mean_score']:.4f} "
        f"LB90 {res['val']['lb_90']:.4f} (vetoes {res['val']['total_vetoes']})",
        flush=True)


def write_report(data):
  lines = ["# SkillOpt Report: Interview Turn v2 (`arm-new-track` + protocol rules)", ""]
  lines.append(f"Generated: {datetime.datetime.now().isoformat(timespec='seconds')}")
  lines.append("")
  lines.append("| Pass | Train mean | Train vetoes | Val mean | Val LB90 | Val vetoes | Val pass rate |")
  lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
  for key in ("baseline", "candidate", "best"):
    if key in data:
      t, v = data[key]["train"], data[key]["val"]
      lines.append(f"| {key} | {t['mean_score']:.4f} | {t['total_vetoes']} | "
                   f"{v['mean_score']:.4f} | {v['lb_90']:.4f} | {v['total_vetoes']} | "
                   f"{v['pass_rate']*100:.1f}% |")
  lines.append("")
  for key in ("baseline", "candidate", "best"):
    if key not in data:
      continue
    lines.append(f"## {key}: per-task vetoes")
    lines.append("")
    for split in ("train", "val"):
      for r in data[key][split]["rollouts"]:
        if r["vetoes"]:
          lines.append(f"- `{r['task_id']}` seed {r['seed']}: " + "; ".join(r["vetoes"]))
    lines.append("")
  if data.get("epochs"):
    lines.append("## Optimization epochs")
    lines.append("")
    for e in data["epochs"]:
      lines.append(f"- Epoch {e['epoch']}: {e['status']} — {e.get('rationale','')} "
                   f"(val LB90 {e.get('val_lb_90', float('nan')):.4f}, "
                   f"diff {e.get('token_diff_ratio', float('nan')):.3f}, "
                   f"tokens {e.get('token_ratio', float('nan')):.3f})")
    lines.append("")
  with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))


# --------------------------------------------------------------------------
def main():
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--phase", choices=["baseline", "eval", "optimize"], required=True)
  ap.add_argument("--seeds", type=int, default=3)
  ap.add_argument("--epochs", type=int, default=2)
  ap.add_argument("--workers", type=int, default=6)
  ap.add_argument("--apply", action="store_true",
                  help="optimize: write the promoted candidate back to SKILL.md")
  args = ap.parse_args()

  train, val = load_tasks(TRAIN_PATH), load_tasks(VAL_PATH)
  data = load_results()
  print(f"=== Interview Turn v2 harness | phase={args.phase} | K={args.seeds} ===",
        flush=True)

  if args.phase == "baseline":
    si = build_system_instruction(read_parent(PROTOCOL_REL), read_parent(ANTIGRAVITY_REL),
                                  read_parent(SKILL_REL))
    data["baseline"] = {
        "train": evaluate_split(si, train, "TRAIN_BASE", args.seeds, args.workers),
        "val": evaluate_split(si, val, "VAL_BASE", args.seeds, args.workers)}
    summarize("BASELINE (origin/main)", data["baseline"])
    save_results(data); write_report(data)
    return

  protocol, antigravity = read_working(PROTOCOL_REL), read_working(ANTIGRAVITY_REL)
  skill = read_working(SKILL_REL)

  if args.phase == "eval":
    si = build_system_instruction(protocol, antigravity, skill)
    data["candidate"] = {
        "train": evaluate_split(si, train, "TRAIN_CAND", args.seeds, args.workers),
        "val": evaluate_split(si, val, "VAL_CAND", args.seeds, args.workers)}
    summarize("CANDIDATE (working copy)", data["candidate"])
    save_results(data); write_report(data)
    return

  # optimize
  if "candidate" not in data:
    si = build_system_instruction(protocol, antigravity, skill)
    data["candidate"] = {
        "train": evaluate_split(si, train, "TRAIN_CAND", args.seeds, args.workers),
        "val": evaluate_split(si, val, "VAL_CAND", args.seeds, args.workers)}
    summarize("CANDIDATE (working copy)", data["candidate"])
    save_results(data)
  best_text, best = skill, data["candidate"]
  data.setdefault("epochs", [])
  for epoch in range(1, args.epochs + 1):
    feedback = collect_feedback(best["train"])
    if not feedback and best["train"]["total_vetoes"] == 0 and best["train"]["mean_score"] >= 0.99:
      print(f"Epoch {epoch}: training already converged; stopping.", flush=True)
      break
    cand_text, rationale = propose_patch(best_text, feedback, best["val"]["mean_score"], epoch)
    rec = {"epoch": epoch, "rationale": rationale}
    if cand_text is None:
      rec["status"] = "REJECTED (no applicable patch)"
      data["epochs"].append(rec); save_results(data); continue
    g = guard_metrics(skill, cand_text)
    rec.update({"token_diff_ratio": g["token_diff_ratio"], "token_ratio": g["token_ratio"]})
    if not g["passed"]:
      rec["status"] = "REJECTED (guard)"
      data["epochs"].append(rec); save_results(data)
      print(f"Epoch {epoch}: rejected by guard {g}", flush=True); continue
    si = build_system_instruction(protocol, antigravity, cand_text)
    tr = evaluate_split(si, train, f"TRAIN_E{epoch}", args.seeds, args.workers)
    va = evaluate_split(si, val, f"VAL_E{epoch}", args.seeds, args.workers)
    rec["val_lb_90"] = va["lb_90"]
    promoted = va["total_vetoes"] == 0 and va["lb_90"] > best["val"]["mean_score"] \
        and tr["mean_score"] >= best["train"]["mean_score"]
    rec["status"] = "PROMOTED" if promoted else "REJECTED (validation gate)"
    data["epochs"].append(rec)
    print(f"Epoch {epoch}: {rec['status']} | train {tr['mean_score']:.4f} | "
          f"val {va['mean_score']:.4f} LB90 {va['lb_90']:.4f} vetoes {va['total_vetoes']}",
          flush=True)
    if promoted:
      best_text, best = cand_text, {"train": tr, "val": va}
      data["best"] = best
      tmp_dir = "/tmp/armature_skillopt_backups"
      os.makedirs(tmp_dir, exist_ok=True)
      with open(
          os.path.join(tmp_dir, "best_arm_new_track_SKILL.md"),
          "w",
          encoding="utf-8",
      ) as f:
        f.write(best_text)
    save_results(data)
  if args.apply and best_text != skill:
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    tmp_dir = "/tmp/armature_skillopt_backups"
    os.makedirs(tmp_dir, exist_ok=True)
    bak = os.path.join(tmp_dir, f"arm_new_track_SKILL.md.bak_{stamp}")
    with open(bak, "w", encoding="utf-8") as f:
      f.write(skill)
    with open(os.path.join(ARMATURE_ROOT, SKILL_REL), "w", encoding="utf-8") as f:
      f.write(best_text)
    print(f"Applied promoted candidate to {SKILL_REL} (backup: {bak})", flush=True)
  write_report(data)
  print("=== DONE ===", flush=True)


if __name__ == "__main__":
  main()
