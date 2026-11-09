#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
RUN_ID="${1:?usage: ./release.sh <run_id> [--smoke]}"
MODE="${2:-}"
OUT="/tmp/armature_bench/${RUN_ID}"
STAGE="results/${RUN_ID}"

echo "=== Stage 1: Unit Tests & Leakage Audit ==="
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
mkdir -p "$OUT"
PYTHONDONTWRITEBYTECODE=1 python3 leakage_audit.py --out-json "$OUT/leakage.json"

if [[ "$MODE" == "--smoke" ]]; then
  echo "=== Stage 2: Smoke Matrix Rollouts (90 cells) ==="
  PYTHONDONTWRITEBYTECODE=1 python3 run_benchmark.py run \
    --run-id "$RUN_ID" --smoke --concurrency 16 --out "$OUT"

  echo "=== Stage 3: Retry Harness Errors & Verify Matrix ==="
  PYTHONDONTWRITEBYTECODE=1 python3 run_benchmark.py run \
    --run-id "$RUN_ID" --out "$OUT" --retry-harness-errors --concurrency 8
  PYTHONDONTWRITEBYTECODE=1 python3 run_benchmark.py verify --out "$OUT" --strict-config

  echo "=== Stage 4: Render Reports & Enforce Smoke Gate ==="
  PYTHONDONTWRITEBYTECODE=1 python3 run_benchmark.py report \
    --out "$OUT" --stage-to "$STAGE" --smoke-gate
  cp "$OUT/leakage.json" "$STAGE/leakage.json"
  echo "=== Smoke Gate Complete: $STAGE ==="
  exit 0
fi

echo "=== Stage 2: Full Matrix Rollouts ==="
PYTHONDONTWRITEBYTECODE=1 python3 run_benchmark.py run \
  --run-id "$RUN_ID" --seeds 3 --publish --concurrency 16 --out "$OUT"

echo "=== Stage 3: Retry Harness Errors & Verify Matrix ==="
PYTHONDONTWRITEBYTECODE=1 python3 run_benchmark.py run \
  --run-id "$RUN_ID" --out "$OUT" --retry-harness-errors --concurrency 8
PYTHONDONTWRITEBYTECODE=1 python3 run_benchmark.py verify --out "$OUT" --strict-config

echo "=== Stage 4: Blinded Cross-Family Judge Ensemble ==="
PYTHONDONTWRITEBYTECODE=1 python3 run_benchmark.py judge --out "$OUT"

echo "=== Stage 5: Render & Stage Reports ==="
PYTHONDONTWRITEBYTECODE=1 python3 run_benchmark.py report --out "$OUT" --stage-to "$STAGE"
PYTHONDONTWRITEBYTECODE=1 python3 run_benchmark.py report --out "$OUT" --public-only --stage-to "$STAGE/public"
cp "$OUT/leakage.json" "$STAGE/leakage.json"

echo "=== Stage 6: Automated Calibration & Agreement ==="
PYTHONDONTWRITEBYTECODE=1 python3 run_benchmark.py calibrate \
  --out "$OUT" --stage-to "$STAGE" --labeler-model gemini-3.1-pro-preview --concurrency 10

echo "=== Release Complete: $STAGE ==="
