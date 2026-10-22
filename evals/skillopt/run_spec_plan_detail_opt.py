#!/usr/bin/env python3
"""Focused SkillOpt Runner for Execution-Ready Specification & Plan Grounding (ADR 0016).

Evaluates /arm-new-track Step 6 (spec.md) and Step 7 (plan.md) across:
- Baseline (pre-ADR 0016 hg cat of skills/arm-new-track/SKILL.md and
rules/armature_protocol.md)
- Candidate (working copy with the 6-Point Execution-Ready Spec & Plan Grounding
Standard)

Includes:
1. Deterministic [INVARIANT] Vetoes inspecting tool calls and the written
spec.md / plan.md
   CodeContent (including strict multi-line implementation code block veto,
   verified symbol
   and 2-argument method arity checks, cross-layer field bijection & validator
   checks,
   hydration echo-suppression guard & timer checks, and build-generated /
   test-override checks).
2. LLM-as-Judge [QUALITY] scoring across K=3 seeds (seeds 42, 43, 44).
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import functools
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
  zshrc_path = os.path.expanduser("~/.zshrc")
  if os.path.exists(zshrc_path):
    with open(zshrc_path, "r", encoding="utf-8", errors="ignore") as f:
      for line in f:
        m = re.search(
            r'export\s+GEMINI_API_KEY=["\']?([A-Za-z0-9_\-]+)["\']?', line
        )
        if m:
          API_KEY = m.group(1)
          break

if not API_KEY:
  sys.exit("ERROR: GEMINI_API_KEY not found in environment or ~/.zshrc")

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TARGET_MODEL = "gemini-3-flash-preview"
JUDGE_MODEL = "gemini-3-flash-preview"

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
ARMATURE_ROOT = os.path.abspath(os.path.join(EVALS_DIR, "../.."))
TRAIN_PATH = os.path.join(EVALS_DIR, "tasks/train_spec_plan_detail.jsonl")
VAL_PATH = os.path.join(EVALS_DIR, "tasks/val_spec_plan_detail.jsonl")
RESULTS_PATH = os.path.join(EVALS_DIR, "spec_plan_detail_eval_results.json")

TARGET_TOOLS = [{
    "functionDeclarations": [
        {
            "name": "ask_question",
            "description": (
                "Ask the user one or more multiple-choice questions and wait"
                " for answers."
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
            "description": "Write content to a file on disk.",
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
            "description": "Edit an existing file on disk.",
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
            "name": "view_file",
            "description": "Read a file from disk.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"AbsolutePath": {"type": "STRING"}},
                "required": ["AbsolutePath"],
            },
        },
        {
            "name": "code_search",
            "description": "Search code in workspace.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"Query": {"type": "STRING"}},
                "required": ["Query"],
            },
        },
        {
            "name": "run_command",
            "description": "Run a shell command.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"CommandLine": {"type": "STRING"}},
                "required": ["CommandLine"],
            },
        },
        {
            "name": "invoke_subagent",
            "description": "Invoke a background subagent.",
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


def call_gemini(
    model: str,
    prompt: str,
    system_instruction: str = None,
    temperature: float = 0.2,
    json_mode: bool = False,
    seed: int = None,
    tools: list = None,
) -> str:
  url = f"{BASE_URL}/{model}:generateContent?key={API_KEY}"
  gen_config = {"temperature": temperature}
  if seed is not None:
    gen_config["seed"] = seed
  if json_mode and not tools:
    gen_config["responseMimeType"] = "application/json"

  payload = {
      "contents": [{"role": "user", "parts": [{"text": prompt}]}],
      "generationConfig": gen_config,
  }
  if system_instruction:
    payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
  if tools:
    payload["tools"] = tools

  data = json.dumps(payload).encode("utf-8")
  req = urllib.request.Request(
      url, data=data, headers={"Content-Type": "application/json"}
  )
  for attempt in range(1, 4):
    try:
      with urllib.request.urlopen(req, timeout=45) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        cands = res.get("candidates", [])
        if not cands:
          return ""
        parts = cands[0].get("content", {}).get("parts", [])
        out = []
        for p in parts:
          if "text" in p:
            out.append(p["text"])
          if "functionCall" in p:
            fc = p["functionCall"]
            out.append(
                f"\n[NATIVE_FUNCTION_CALL: {fc.get('name')}("
                f"{json.dumps(fc.get('args', {}), ensure_ascii=False)})]"
            )
        return "\n".join(out)
    except Exception as e:  # pylint: disable=broad-exception-caught
      if attempt == 3:
        print(f"API Error: {e}", file=sys.stderr)
        return ""
      time.sleep(1.5 * attempt)
  return ""


@functools.lru_cache(maxsize=None)
def get_file_content(rel_path: str, use_baseline: bool) -> str:
  full_path = os.path.join(ARMATURE_ROOT, rel_path)
  if use_baseline:
    try:
      out = subprocess.check_output(
          ["hg", "cat", full_path],
          cwd=ARMATURE_ROOT,
          stderr=subprocess.DEVNULL,
          timeout=15,
      )
      return out.decode("utf-8")
    except Exception:  # pylint: disable=broad-exception-caught
      pass
  if os.path.exists(full_path):
    with open(full_path, "r", encoding="utf-8") as f:
      return f.read()
  return ""


def extract_written_artifacts(rollout: str) -> dict[str, str]:
  """Extracts TargetFile -> CodeContent from [NATIVE_FUNCTION_CALL: write_to_file(...)] blocks."""
  artifacts = {}
  marker = "[NATIVE_FUNCTION_CALL: write_to_file("
  idx = 0
  while True:
    pos = rollout.find(marker, idx)
    if pos == -1:
      break
    json_start = pos + len(marker)
    end_pos = rollout.find(")]", json_start)
    if end_pos == -1:
      break
    raw_json = rollout[json_start:end_pos]
    try:
      args = json.loads(raw_json)
      target = args.get("TargetFile", "")
      content = args.get("CodeContent", "")
      artifacts[target] = content
    except Exception:  # pylint: disable=broad-exception-caught
      pass
    idx = end_pos + 2
  return artifacts


def has_multiline_implementation_code_block(md_text: str) -> tuple[bool, str]:
  """Checks if markdown text contains a multi-line fenced code block with implementation code."""
  code_block_re = re.compile(
      r"```(ts|typescript|js|javascript|py|python|go|golang|rs|rust|kt|kotlin|java|c|cpp)\s*\n(.*?)```",
      re.IGNORECASE | re.DOTALL,
  )
  for m in code_block_re.finditer(md_text):
    lang = m.group(1).lower()
    body = m.group(2).strip()
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if len(lines) >= 2:
      return True, f"Found {len(lines)}-line ```{lang} code block in artifact"
  return False, ""


TASK_REQUIRED_TOKENS = {
    "SPD_TRAIN_01": {
        "symbols_and_arity": [
            "ImmutableProject",
            "setSampleProjectId",
            "field_mask",
            "applyHydratedPartVisibility",
            "seeThroughPartSlugs",
            "getCameraPose",
            "setCameraPose",
            "setSectionInverted",
        ],
        "bijections_and_validators": [
            "0.65",
            "SHADING_MODE_DEFAULT",
            "constant",
            "flipped",
            "1.0",
        ],
        "echo_and_overrides": [
            "isHydratingSceneState",
            "600",
            "500",
            "variables_data.binarypb",
            "variable_overrides_inline_test.textproto",
        ],
    },
    "SPD_TRAIN_02": {
        "symbols_and_arity": [
            "ImmutableProject",
            "setSampleProjectId",
            "field_mask_ts_proto",
            "applyHydratedPartVisibility",
            "seeThroughPartSlugs",
            "getCameraPose",
            "setCameraPose",
            "setSectionInverted",
        ],
        "bijections_and_validators": [
            "0.65",
            "constant",
            "flipped",
            "1.0",
        ],
        "echo_and_overrides": [
            "isHydratingSceneState",
            "600",
            "500",
            "variables_data.binarypb",
            "variable_overrides_inline_test.textproto",
        ],
    },
    "SPD_TRAIN_03": {
        "symbols_and_arity": [
            "SettlementBatch",
            "settlement_batch_id",
            "apply_hydrated_account_holds",
            "review_account_ids",
            "acquire_row_fence",
            "get_watermark_seq",
            "set_watermark_seq",
        ],
        "bijections_and_validators": [
            "amount_minor_units",
            "fee_bps",
            "voided",
            "1.0",
        ],
        "echo_and_overrides": [
            "is_replaying_snapshot",
            "400",
            "600",
            "settlement_pb2.py",
            "USE_STRICT_LEDGER_FENCE",
        ],
    },
    "SPD_TRAIN_04": {
        "symbols_and_arity": [
            "TenantQuota",
            "SetTenantQuotaId",
            "fieldmaskpb",
            "ApplyHydratedTenantOverrides",
            "shadowedTenants",
            "SelectBucketShard",
            "GetBurstWatermark",
            "SetBurstWatermark",
        ],
        "bijections_and_validators": [
            "MaxTokens",
            "ShadowMode",
            "10",
            "1.0",
        ],
        "echo_and_overrides": [
            "isHydratingQuotaSnapshot",
            "500",
            "400",
            "limits_bundle.binarypb",
            "limits_inmemory_test_override.textproto",
        ],
    },
    "SPD_TRAIN_05": {
        "symbols_and_arity": [
            "ImmutableCollaboratorSession",
            "setTargetSessionId",
            "field_mask",
            "applyHydratedLayerHighlights",
            "lockedByPeerLayerIds",
            "getViewportMatrix",
            "setViewportMatrix",
            "setAxisMirrored",
        ],
        "bijections_and_validators": [
            "0.75",
            "SMOOTHING_CUBIC_SPLINE",
            "plane_constant",
            "inverted_normal",
            "1.0",
        ],
        "echo_and_overrides": [
            "isHydratingPeerViewport",
            "750",
            "1200",
            "collab_flags_data.binarypb",
            "collab_flags_loopback_test_override.textproto",
        ],
    },
    "SPD_TRAIN_06": {
        "symbols_and_arity": [
            "CollectorProfile",
            "source_profile_id",
            "FieldMask",
            "apply_hydrated_partition_masks",
            "trace_only_shards",
            "get_cursor_watermark",
            "set_cursor_watermark",
            "set_sampling_inverted",
        ],
        "bijections_and_validators": [
            "0.25",
            "EXPORT_PROTOCOL_OTLP_GRPC",
            "plane_offset",
            "flipped_polarity",
            "1.0",
        ],
        "echo_and_overrides": [
            "is_recovering_wal_state",
            "600",
            "500",
            "telemetry_defaults.binpb",
            "test_uncompressed_override.txtpb",
        ],
    },
    "SPD_VAL_01": {
        "symbols_and_arity": [
            "ImmutableAudioPreset",
            "setSourcePresetId",
            "field_mask",
            "applyHydratedStemRouting",
            "soloedStemIds",
            "getMasterEnvelope",
            "setMasterEnvelope",
            "setBandBypassed",
        ],
        "bijections_and_validators": [
            "0.80",
            "PANNING_LAW_EQUAL_POWER",
            "center_frequency_hz",
            "muted",
            "18.0",
        ],
        "echo_and_overrides": [
            "isHydratingAudioGraph",
            "550",
            "450",
            "dsp_flags_data.binarypb",
            "dsp_flags_heap_test_override.textproto",
        ],
    },
    "SPD_VAL_02": {
        "symbols_and_arity": [
            "PolicyTemplate",
            "SetSourceTemplateId",
            "fieldmaskpb",
            "ApplyHydratedNamespaceExemptions",
            "auditOnlyNamespaces",
            "GetCompiledRevision",
            "SetCompiledRevision",
            "SetRulePolarityInverted",
        ],
        "bijections_and_validators": [
            "0.35",
            "FAILURE_POLICY_FAIL",
            "plane_constant",
            "flipped_rule",
            "1.0",
        ],
        "echo_and_overrides": [
            "isHydratingPolicyState",
            "800",
            "300",
            "policy_flags_data.binarypb",
            "policy_flags_inmemory_test_override.textproto",
        ],
    },
    "SPD_VAL_03": {
        "symbols_and_arity": [
            "ImmutableClaimDossier",
            "setSourceDossierId",
            "field_mask",
            "applyHydratedLineItemFlags",
            "heldLineIds",
            "getScrollAnchor",
            "setScrollAnchor",
            "setAuditPolarityInverted",
        ],
        "bijections_and_validators": [
            "0.55",
            "PRICING_SCHEDULE_MEDICARE_PAR",
            "constant",
            "flipped",
            "1.0",
        ],
        "echo_and_overrides": [
            "isHydratingAdjudicationView",
            "650",
            "400",
            "adjudication_flags_data.binarypb",
            "adjudication_flags_local_test_override.textproto",
        ],
    },
    "SPD_VAL_04": {
        "symbols_and_arity": [
            "ImmutableVectorDocument",
            "setSourceDocumentId",
            "field_mask_ts_proto",
            "applyHydratedLayerLocks",
            "outlineOnlyLayerSlugs",
            "getViewportTransform",
            "setViewportTransform",
            "setGuideInverted",
        ],
        "bijections_and_validators": [
            "0.50",
            "RENDER_QUALITY_CRISP_AA",
            "constant",
            "flipped",
            "1.0",
        ],
        "echo_and_overrides": [
            "isHydratingCanvasState",
            "500",
            "350",
            "editor_flags_data.binarypb",
            "editor_flags_canvas2d_test_override.textproto",
        ],
    },
}


def check_deterministic_invariants(task: dict, rollout: str) -> list[dict]:
  """Evaluates deterministic [INVARIANT] checks on the rollout and written artifacts."""
  results = []
  invariants = task.get("invariants", [])
  task_id = task["id"]
  visible_text = rollout.split("[NATIVE_FUNCTION_CALL:")[0].strip()
  artifacts = extract_written_artifacts(rollout)

  primary_artifact_text = ""
  for path, content in artifacts.items():
    if path.endswith("spec.md") or path.endswith("plan.md"):
      primary_artifact_text += "\n" + content

  req_tokens = TASK_REQUIRED_TOKENS.get(task_id, {})

  for inv in invariants:
    passed = True
    reason = "Deterministic invariant satisfied."

    if inv == "no_bare_tool_call":
      passed = len(visible_text.split()) >= 20
      if not passed:
        reason = (
            "Response started with a bare tool call or insufficient visible"
            f" markdown ({len(visible_text.split())} words)."
        )
    elif inv == "has_ask_question_tool":
      passed = "[NATIVE_FUNCTION_CALL: ask_question(" in rollout
      if not passed:
        reason = "Did not invoke ask_question as a native tool call."
    elif inv == "writes_spec_and_manual_testing_md":
      wrote_spec = any(p.endswith("spec.md") for p in artifacts)
      wrote_mt = any(p.endswith("manual_testing.md") for p in artifacts)
      wrote_plan = any(p.endswith("plan.md") for p in artifacts)
      wrote_meta = any(p.endswith("metadata.json") for p in artifacts)
      passed = wrote_spec and wrote_mt and not wrote_plan and not wrote_meta
      if not passed:
        reason = (
            f"Step 6 write mismatch: spec={wrote_spec},"
            f" manual_testing={wrote_mt}, premature_plan={wrote_plan},"
            f" premature_meta={wrote_meta}."
        )
    elif inv == "writes_plan_md_only":
      wrote_plan = any(p.endswith("plan.md") for p in artifacts)
      wrote_meta = any(p.endswith("metadata.json") for p in artifacts)
      wrote_tracks = any(p.endswith("tracks.md") for p in artifacts)
      passed = wrote_plan and not wrote_meta and not wrote_tracks
      if not passed:
        reason = (
            f"Step 7 write mismatch: plan={wrote_plan},"
            f" premature_meta={wrote_meta}, premature_tracks={wrote_tracks}."
        )
    elif inv == "no_multiline_code_in_spec_or_plan":
      has_code, code_msg = has_multiline_implementation_code_block(
          primary_artifact_text
      )
      passed = bool(primary_artifact_text.strip()) and not has_code
      if not passed:
        reason = (
            code_msg
            if has_code
            else "No spec.md or plan.md content written via write_to_file."
        )
    elif inv == "grounds_verified_symbols_and_arity":
      needed = req_tokens.get("symbols_and_arity", [])
      missing = [tok for tok in needed if tok not in primary_artifact_text]
      passed = len(missing) == 0 and bool(primary_artifact_text.strip())
      if not passed:
        reason = f"Artifact missing verified symbols/arity tokens: {missing}"
    elif inv == "grounds_bijections_and_validators":
      needed = req_tokens.get("bijections_and_validators", [])
      missing = [tok for tok in needed if tok not in primary_artifact_text]
      passed = len(missing) == 0 and bool(primary_artifact_text.strip())
      if not passed:
        reason = (
            "Artifact missing cross-layer bijection/validator tokens:"
            f" {missing}"
        )
    elif inv == "grounds_echo_guard_and_test_override":
      needed = req_tokens.get("echo_and_overrides", [])
      missing = [tok for tok in needed if tok not in primary_artifact_text]
      passed = len(missing) == 0 and bool(primary_artifact_text.strip())
      if not passed:
        reason = (
            "Artifact missing hydration echo guard, timers, or test override"
            f" tokens: {missing}"
        )

    results.append({
        "criterion": f"[INVARIANT] {inv}",
        "type": "INVARIANT",
        "passed": passed,
        "reason": reason,
    })
  return results


def evaluate_task(task: dict, use_baseline: bool, seed: int = None) -> dict:
  skill_name = task["skill"]
  skill_content = get_file_content(
      f"skills/{skill_name}/SKILL.md", use_baseline
  )
  protocol_content = get_file_content(
      "rules/armature_protocol.md", use_baseline
  )
  jetski_content = get_file_content("rules/armature_antigravity.md", use_baseline)

  sys_inst = (
      "You are an AI engineering assistant, an AI engineering assistant executing the Armature"
      " framework.\nFollow the active Armature Protocol and Skill instructions"
      " strictly.\n\n=== ARMATURE PROTOCOL"
      f" ===\n{protocol_content}\n\n=== ARMATURE JETSKI UX ADAPTER"
      f" ===\n{jetski_content}\n\n=== ACTIVE SKILL ({skill_name})"
      f" ===\n{skill_content}\n"
  )

  rollout = call_gemini(
      TARGET_MODEL,
      task["prompt"],
      system_instruction=sys_inst,
      temperature=0.2,
      seed=seed,
      tools=TARGET_TOOLS,
  )

  inv_results = check_deterministic_invariants(task, rollout)
  inv_passed = all(r["passed"] for r in inv_results)

  qualities = task.get("expected_behaviors", task.get("qualities", []))
  judge_prompt = f"""You are an impartial expert evaluator grading an AI agent's execution of /{skill_name} Step 6 (`spec.md`) or Step 7 (`plan.md`).

Task ID: {task['id']} ({task['scenario']})
User Prompt:
{task['prompt']}

Agent Response & Tool Calls:
{rollout}

Evaluate each of the following Quality Criteria:
{json.dumps(qualities, indent=2)}

Return a JSON object with a single key "evaluations" containing a list of objects, one per criterion in exact order:
{{
  "evaluations": [
    {{
      "criterion": "<criterion string>",
      "passed": true/false,
      "reason": "<1 concise sentence citing evidence from the response>"
    }}
  ]
}}"""

  judge_raw = call_gemini(
      JUDGE_MODEL, judge_prompt, temperature=0.0, json_mode=True, seed=seed
  )
  qual_results = []
  try:
    parsed = json.loads(judge_raw)
    for item in parsed.get("evaluations", []):
      qual_results.append({
          "criterion": f"[QUALITY] {item.get('criterion', '')}",
          "type": "QUALITY",
          "passed": bool(item.get("passed", False)),
          "reason": item.get("reason", ""),
      })
  except Exception as e:  # pylint: disable=broad-exception-caught
    for q in qualities:
      qual_results.append({
          "criterion": f"[QUALITY] {q}",
          "type": "QUALITY",
          "passed": False,
          "reason": f"Judge parse error: {e}",
      })

  if not inv_passed:
    score = 0.0
  else:
    passed_q = sum(1 for r in qual_results if r["passed"])
    score = passed_q / len(qual_results) if qual_results else 1.0

  return {
      "task_id": task["id"],
      "skill": skill_name,
      "scenario": task["scenario"],
      "score": score,
      "invariants_passed": inv_passed,
      "eval_results": inv_results + qual_results,
      "rollout_sample": rollout[:2000],
  }


def run_split(
    tasks: list[dict], split_name: str, use_baseline: bool, seed: int
) -> tuple[float, list[dict]]:
  print(f"\n--- Running {split_name} (seed={seed}) ---", flush=True)
  # Pre-warm file cache on main thread so worker threads never spawn concurrent `hg cat` processes.
  for rel in (
      "skills/arm-new-track/SKILL.md",
      "rules/armature_protocol.md",
      "rules/armature_antigravity.md",
  ):
    get_file_content(rel, use_baseline)
  results_map = {}
  with ThreadPoolExecutor(max_workers=6) as pool:
    futs = {
        pool.submit(evaluate_task, t, use_baseline, seed): t["id"]
        for t in tasks
    }
    for fut in as_completed(futs):
      res = fut.result()
      results_map[res["task_id"]] = res
      status = "✅ PASS" if res["score"] == 1.0 else f"❌ {res['score']:.2f}"
      print(
          f"  [{res['task_id']}] ({res['skill']}): {status}"
          f" (inv={res['invariants_passed']})",
          flush=True,
      )
      for er in res["eval_results"]:
        if not er["passed"]:
          print(f"    - FAIL {er['criterion']}: {er['reason']}", flush=True)

  ordered = [results_map[t["id"]] for t in tasks]
  mean_score = statistics.mean(r["score"] for r in ordered) if ordered else 0.0
  print(f"=> {split_name} Mean Score: {mean_score:.4f}", flush=True)
  return mean_score, ordered


def compute_stats(scores: list[float]) -> dict:
  n = len(scores)
  if n == 0:
    return {"mean": 0.0, "sd": 0.0, "ci_95_half_width": 0.0}
  mean = statistics.mean(scores)
  sd = statistics.stdev(scores) if n > 1 else 0.0
  t_crit = 4.303 if n == 3 else (2.776 if n == 5 else 1.96)
  hw = t_crit * (sd / math.sqrt(n)) if n > 1 else 0.0
  return {
      "mean": round(mean, 4),
      "sd": round(sd, 4),
      "ci_95_half_width": round(hw, 4),
      "scores": [round(s, 4) for s in scores],
  }


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "--phase",
      choices=["baseline", "candidate", "both"],
      default="both",
  )
  parser.add_argument("--seeds", type=int, default=3)
  args = parser.parse_args()

  with open(TRAIN_PATH, "r", encoding="utf-8") as f:
    train_tasks = [json.loads(line) for line in f if line.strip()]
  with open(VAL_PATH, "r", encoding="utf-8") as f:
    val_tasks = [json.loads(line) for line in f if line.strip()]

  seeds = [42 + i for i in range(args.seeds)]
  output = {}
  if os.path.exists(RESULTS_PATH):
    try:
      with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        output = json.load(f)
    except Exception:  # pylint: disable=broad-exception-caught
      output = {}

  if args.phase in ("baseline", "both"):
    print("\n================ BASELINE EVALUATION (hg cat) ================")
    b_train_scores, b_val_scores, b_runs = [], [], []
    for s in seeds:
      ts, tr = run_split(train_tasks, "BASELINE TRAIN", True, s)
      vs, vr = run_split(val_tasks, "BASELINE VAL", True, s)
      b_train_scores.append(ts)
      b_val_scores.append(vs)
      b_runs.append({"seed": s, "train": tr, "val": vr})
    output["baseline"] = {
        "train_stats": compute_stats(b_train_scores),
        "val_stats": compute_stats(b_val_scores),
        "runs": b_runs,
    }

  if args.phase in ("candidate", "both"):
    print(
        "\n================ CANDIDATE EVALUATION (Working Copy)"
        " ================"
    )
    c_train_scores, c_val_scores, c_runs = [], [], []
    for s in seeds:
      ts, tr = run_split(train_tasks, "CANDIDATE TRAIN", False, s)
      vs, vr = run_split(val_tasks, "CANDIDATE VAL", False, s)
      c_train_scores.append(ts)
      c_val_scores.append(vs)
      c_runs.append({"seed": s, "train": tr, "val": vr})
    output["candidate"] = {
        "train_stats": compute_stats(c_train_scores),
        "val_stats": compute_stats(c_val_scores),
        "runs": c_runs,
    }

  with open(RESULTS_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
  print(f"\nSaved evaluation results to {RESULTS_PATH}")


if __name__ == "__main__":
  main()
