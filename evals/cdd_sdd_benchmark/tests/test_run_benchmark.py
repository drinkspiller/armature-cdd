"""Unit tests for rollouts.jsonl persistence in run_benchmark.py."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
  sys.path.insert(0, BASE)

# pylint: disable=g-import-not-at-top,wrong-import-position
from bench import agent_loop
from bench import gemini_client
from bench import sandbox as sandbox_lib
from bench import schema
import run_benchmark
from tests import test_core
# pylint: enable=g-import-not-at-top,wrong-import-position

TMP_BASE = os.path.join(sandbox_lib.SANDBOX_BASE, "unittest_persist")


class RolloutsPersistenceTest(unittest.TestCase):
  """Verifies rollouts.jsonl is persisted to results/ during run and report."""

  def setUp(self):
    super().setUp()
    os.makedirs(TMP_BASE, exist_ok=True)
    self.root = tempfile.mkdtemp(dir=TMP_BASE)
    self.work_out = os.path.join(self.root, "work")
    self.results_dir = os.path.join(self.root, "results")

  def tearDown(self):
    shutil.rmtree(self.root, ignore_errors=True)
    super().tearDown()

  def _fake_rollout(self, pack, sc, model, seed, run_id, config_hash, root,
                    **kw):
    del root, kw
    return schema.RolloutRecord(
        run_id=run_id,
        config_hash=config_hash,
        framework=pack.key,
        framework_visibility="public",
        scenario_id=sc.id,
        set=sc.set,
        pillar=sc.pillar,
        seed=seed,
        model=model,
        status="ok",
        checks=[
            schema.CheckResult(id="c1", type="x", passed=True, detail="ok")
        ],
    )

  def test_rollouts_persist_on_run_and_report_stage_to(self):
    sc = test_core._scenario()  # pylint: disable=protected-access
    argv_run = [
        "run",
        "--registry", "x.json",
        "--sets", "core",
        "--models", "m",
        "--seeds", "1",
        "--concurrency", "1",
        "--run-id", "persist-run",
        "--out", self.work_out,
    ]
    with mock.patch.object(run_benchmark, "RESULTS_DIR", self.results_dir), \
         mock.patch.object(run_benchmark, "load_packs",
                           return_value=[test_core.StubPack()]), \
         mock.patch.object(run_benchmark, "load_scenario_sets",
                           return_value=({sc.id: sc}, {
                               "core": "tests/fixtures/smoke.jsonl"})), \
         mock.patch.object(agent_loop, "run_rollout",
                           side_effect=self._fake_rollout), \
         mock.patch.object(gemini_client, "GeminiClient", return_value=None), \
         mock.patch("bench.checks.run_checks",
                    return_value=[schema.CheckResult(
                        id="c1", type="x", passed=True, detail="ok")]):
      rc = run_benchmark.main(argv_run)
    self.assertEqual(rc, 0)

    # 1. Verify --persist-rollouts (default True) wrote rollouts.jsonl to
    #    results/<run_id>/rollouts.jsonl even when --out pointed elsewhere.
    durable_rollouts = os.path.join(
        self.results_dir, "persist-run", "rollouts.jsonl")
    self.assertTrue(os.path.isfile(durable_rollouts))
    persisted = run_benchmark.load_rollouts(durable_rollouts)
    self.assertEqual(len(persisted), 1)
    self.assertEqual(persisted[0].run_id, "persist-run")

    # 2. Verify cmd_report with --stage-to copies rollouts.jsonl, manifest.json,
    #    leakage.json, stats.json, and report.md into the staged directory.
    with open(os.path.join(self.work_out, "leakage.json"), "w",
              encoding="utf-8") as f:
      json.dump({"frameworks": {}}, f)
    staged_dir = os.path.join(self.root, "staged_results")
    with mock.patch.object(run_benchmark, "verify", return_value=[]), \
         mock.patch.object(run_benchmark, "_run_scenarios",
                           return_value={sc.id: sc}):
      rc_rep = run_benchmark.main([
          "report",
          "--out", self.work_out,
          "--stage-to", staged_dir,
          "--n-boot", "20",
      ])
    self.assertEqual(rc_rep, 0)
    for fname in ("rollouts.jsonl", "manifest.json", "leakage.json",
                  "stats.json", "report.md"):
      self.assertTrue(
          os.path.isfile(os.path.join(staged_dir, fname)),
          f"missing {fname} in {staged_dir}",
      )
    staged_recs = run_benchmark.load_rollouts(
        os.path.join(staged_dir, "rollouts.jsonl"))
    self.assertEqual(len(staged_recs), 1)
    self.assertTrue(staged_recs[0].pack_digest)

  def test_pack_digest_verification_shared_passes_and_mismatches_fail(self):
    sc = test_core._scenario()  # pylint: disable=protected-access
    argv_run = [
        "run",
        "--registry", "x.json",
        "--sets", "core",
        "--models", "m",
        "--seeds", "2",
        "--concurrency", "1",
        "--run-id", "digest-run",
        "--out", self.work_out,
    ]
    with mock.patch.object(run_benchmark, "RESULTS_DIR", self.results_dir), \
         mock.patch.object(run_benchmark, "load_packs",
                           return_value=[test_core.StubPack()]), \
         mock.patch.object(run_benchmark, "load_scenario_sets",
                           return_value=({sc.id: sc}, {
                               "core": "tests/fixtures/smoke.jsonl"})), \
         mock.patch.object(agent_loop, "run_rollout",
                           side_effect=self._fake_rollout), \
         mock.patch.object(gemini_client, "GeminiClient", return_value=None), \
         mock.patch("bench.checks.run_checks",
                    return_value=[schema.CheckResult(
                        id="c1", type="x", passed=True, detail="ok")]):
      rc = run_benchmark.main(argv_run)
    self.assertEqual(rc, 0)
    self.assertEqual(run_benchmark.verify(self.work_out), [])

    rollouts_path = os.path.join(self.work_out, "rollouts.jsonl")
    manifest_path = os.path.join(self.work_out, "manifest.json")
    recs = run_benchmark.load_rollouts(rollouts_path)
    self.assertEqual(len(recs), 2)
    orig_digest = recs[0].pack_digest
    self.assertTrue(orig_digest)
    self.assertEqual(recs[0].pack_digest, recs[1].pack_digest)

    # (a) One row's pack_digest differs -> fails with multiple distinct digests.
    recs[1].pack_digest = "f" * 64
    run_benchmark.write_rollouts_atomic(rollouts_path, recs)
    probs_a = run_benchmark.verify(self.work_out)
    self.assertTrue(
        any("more than one distinct pack_digest" in p for p in probs_a),
        probs_a,
    )

    # (b) Both rows share a digest, but manifest["pack_digests"] disagrees.
    recs[1].pack_digest = orig_digest
    run_benchmark.write_rollouts_atomic(rollouts_path, recs)
    with open(manifest_path, "r", encoding="utf-8") as f:
      manifest = json.load(f)
    manifest["pack_digests"]["stub"] = "0" * 64
    run_benchmark.write_json_atomic(manifest_path, manifest)
    probs_b = run_benchmark.verify(self.work_out)
    self.assertTrue(
        any("pack_digest for stub differs from manifest" in p for p in probs_b),
        probs_b,
    )


if __name__ == "__main__":
  unittest.main()
