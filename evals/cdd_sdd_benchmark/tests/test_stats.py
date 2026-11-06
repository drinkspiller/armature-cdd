"""Synthetic-data tests for bench/stats.py and bench/report.py."""

from __future__ import annotations

import os
import random
import statistics
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench import report  # pylint: disable=g-import-not-at-top
from bench import schema  # pylint: disable=g-import-not-at-top
from bench import stats  # pylint: disable=g-import-not-at-top

MODELS = ("gemini-3-flash-preview", "gemini-3.5-flash")
J1, J2 = stats.PRIMARY_JUDGES


def _scenarios(n_per_set=10):
  out = []
  for st in schema.SETS:
    for i in range(n_per_set):
      out.append(schema.Scenario(
          id=f"{st}_{i:02d}", set=st, pillar=schema.PILLARS[i % 5],
          intent="hotfix", description="d", fixture={}, mocks=[],
          sessions=[{"turns": ["x"]}], checks=[], judge_criteria=["c"]))
  return out


def _record(fw, sc, seed, model, p_pass, rng, n_checks=4, vis="public",
            status="ok", judge_votes=None):
  checks = [schema.CheckResult(id=f"k{i}", type="x",
                               passed=rng.random() < p_pass, detail="")
            for i in range(n_checks)]
  votes = judge_votes or {J1: rng.random() < p_pass,
                          J2: rng.random() < p_pass}
  valid = [v for v in votes.values() if v is not None]
  score = sum(valid) / len(valid) if len(valid) >= 2 else None
  return schema.RolloutRecord(
      run_id="run", config_hash="h", framework=fw, framework_visibility=vis,
      scenario_id=sc.id, set=sc.set, pillar=sc.pillar, seed=seed, model=model,
      status=status, error="HarnessError: empty" if status != "ok" else None,
      checks=checks if status == "ok" else [],
      sessions=[schema.SessionRecord(turns=[schema.TurnRecord(
          user="u", user_raw="u", assistant_text="a", tool_calls=[], steps=1,
          finish_reasons=["STOP"],
          ended_by="max_steps" if sc.id.endswith("_00") else "text",
          usage=schema.Usage())])],
      judge=([schema.JudgeResult(criterion="c", votes=votes, reasons={},
                                 score=score)] if status == "ok" else []),
      usage=schema.Usage(input_tokens=1000, output_tokens=100,
                         thinking_tokens=50, api_calls=3, latency_s=2.0))


class KappaTest(unittest.TestCase):

  def test_known_value(self):
    pairs = ([(True, True)] * 20 + [(True, False)] * 5 +
             [(False, True)] * 10 + [(False, False)] * 15)
    self.assertAlmostEqual(stats.cohen_kappa(pairs), 0.4)

  def test_perfect_and_undefined(self):
    self.assertAlmostEqual(
        stats.cohen_kappa([(True, True), (False, False)] * 5), 1.0)
    self.assertIsNone(stats.cohen_kappa([(True, True)] * 10))
    self.assertIsNone(stats.cohen_kappa([]))

  def test_chance_level_near_zero(self):
    rng = random.Random(3)
    pairs = [(rng.random() < 0.5, rng.random() < 0.5) for _ in range(4000)]
    self.assertLess(abs(stats.cohen_kappa(pairs)), 0.06)

  def test_bootstrap_kappa_ci_contains_point(self):
    rng = random.Random(4)
    clusters = {}
    for c in range(30):
      for _ in range(4):
        a = rng.random() < 0.6
        b = a if rng.random() < 0.8 else not a
        clusters.setdefault(c, []).append((a, b))
    r = stats.bootstrap_kappa(clusters, n_boot=500)
    self.assertLessEqual(r["ci_lo"], r["kappa"])
    self.assertGreaterEqual(r["ci_hi"], r["kappa"])
    self.assertEqual(r["n_clusters"], 30)


class BootstrapCoverageTest(unittest.TestCase):
  """The two-level cluster CI should cover the true mean about 95% of the time.

  Data: scenario difficulty varies a lot (strong clustering), seeds add noise.
  An i.i.d. CI over all rollouts ignores clustering and undercovers badly;
  that was the v1 failure.
  """

  def _draw(self, rng, n_scen=30, n_seeds=5, mu=0.6, tau=0.2, sigma=0.1):
    data = {}
    for s in range(n_scen):
      eff = mu + rng.gauss(0, tau)
      data[f"s{s}"] = [(eff + rng.gauss(0, sigma), None, None)
                       for _ in range(n_seeds)]
    return data

  def test_coverage(self):
    rng = random.Random(11)
    mu = 0.6
    reps = 120
    cluster_hits = 0
    iid_hits = 0
    for rep in range(reps):
      data = self._draw(rng, mu=mu)
      scen = sorted(data)
      boots = stats.cluster_bootstrap({"fw": data}, [scen], 400,
                                      random.Random(rep))
      lo, hi = stats.ci95(boots["fw"][0])
      cluster_hits += lo <= mu <= hi
      flat = [u[0] for v in data.values() for u in v]
      m = statistics.mean(flat)
      se = statistics.stdev(flat) / len(flat) ** 0.5
      iid_hits += (m - 1.96 * se) <= mu <= (m + 1.96 * se)
    cov = cluster_hits / reps
    self.assertGreaterEqual(cov, 0.85, cov)
    self.assertLessEqual(cov, 0.995, cov)
    # The naive i.i.d. interval undercovers under clustering.
    self.assertLess(iid_hits / reps, cov - 0.1)

  def test_deterministic_given_seed(self):
    data = self._draw(random.Random(1))
    a = stats.cluster_bootstrap({"fw": data}, [sorted(data)], 200,
                                random.Random(5))
    b = stats.cluster_bootstrap({"fw": data}, [sorted(data)], 200,
                                random.Random(5))
    self.assertEqual(a, b)


class PairedAndTierTest(unittest.TestCase):

  def test_pairing_detects_consistent_small_gap(self):
    # Huge between-scenario spread, but B is always 0.05 below A.
    rng = random.Random(2)
    a, b = {}, {}
    for s in range(30):
      base = rng.uniform(0.1, 0.9)
      a[f"s{s}"] = [(base + 0.05, None, None)] * 3
      b[f"s{s}"] = [(base, None, None)] * 3
    boots = stats.cluster_bootstrap({"A": a, "B": b}, [sorted(a)], 1000,
                                    random.Random(0))
    a_lo, _ = stats.ci95(boots["A"][0])
    _, b_hi = stats.ci95(boots["B"][0])
    self.assertLess(a_lo, b_hi)  # Marginal CIs overlap...
    d = stats.paired_diff(boots["A"][0], boots["B"][0])
    self.assertGreater(d["ci_lo"], 0.0)  # ...but the paired diff excludes 0.
    tiers = stats.assign_tiers({"A": 0.55, "B": 0.5},
                               {"A": boots["A"][0], "B": boots["B"][0]})
    self.assertEqual(tiers, {"A": 1, "B": 2})

  def test_tiers_end_to_end(self):
    rng = random.Random(7)
    scen = _scenarios(10)
    recs = []
    for fw, p in (("hi1", 0.85), ("hi2", 0.84), ("lo", 0.2)):
      for model in MODELS:
        for sc in scen:
          for seed in range(3):
            recs.append(_record(fw, sc, seed, model, p, rng))
    out = stats.compute(recs, scen, n_boot=300)
    tiers = out["cells"][stats.POOLED_MODEL]["all"]["tiers"]["outcome"]
    self.assertEqual(tiers["hi1"], 1)
    self.assertEqual(tiers["hi2"], 1)
    self.assertEqual(tiers["lo"], 2)
    self.assertNotIn("rank", " ".join(out.keys()).lower())

  def test_indistinguishable_all_tier_one(self):
    rng = random.Random(8)
    scen = _scenarios(10)
    recs = [_record(fw, sc, seed, MODELS[0], 0.5, rng)
            for fw in ("a", "b", "c") for sc in scen for seed in range(3)]
    out = stats.compute(recs, scen, n_boot=300)
    tiers = out["cells"][MODELS[0]]["all"]["tiers"]["outcome"]
    self.assertEqual(set(tiers.values()), {1})


class ExclusionAndReportTest(unittest.TestCase):

  def setUp(self):
    rng = random.Random(9)
    self.scen = _scenarios(6)
    self.recs = []
    for fw, vis in (("pub_a", "public"), ("pub_b", "public"),
                    ("int_c", "internal")):
      for model in MODELS:
        for sc in self.scen:
          for seed in range(2):
            self.recs.append(_record(fw, sc, seed, model, 0.6, rng, vis=vis))
    # 3 of 24 pub_a/model0 rollouts are harness errors (12.5% > 5%).
    for i in range(3):
      sc = self.scen[i]
      self.recs.append(_record("pub_a", sc, 99, MODELS[0], 0.0, rng,
                               status="harness_error"))
    # A criterion with < 2 valid votes must be excluded from judge score.
    self.recs.append(_record("pub_b", self.scen[0], 7, MODELS[0], 1.0, rng,
                             judge_votes={J1: True, J2: None}))
    self.manifest = {
        "run_id": "run", "config_hash": "h", "publish": True,
        "frameworks": [
            {"key": "pub_a", "display_name": "Pub A", "visibility": "public",
             "source": {"type": "git", "repo": "https://example.com/a",
                        "ref": "a" * 40}},
            {"key": "pub_b", "display_name": "Pub B", "visibility": "public",
             "source": {"type": "git", "repo": "https://example.com/b",
                        "ref": "b" * 40}},
            {"key": "int_c", "display_name": "Internal C",
             "visibility": "internal",
             "source": {"type": "local", "path": "x"}}]}

  def test_harness_errors_excluded_and_flagged(self):
    out = stats.compute(self.recs, self.scen, n_boot=100)
    h = out["harness"]["cells"]["pub_a"][MODELS[0]]
    self.assertEqual(h["errors"], 3)
    self.assertTrue(h["over_threshold"])
    self.assertTrue(out["harness"]["invalid"])
    # Harness-error rollouts (all checks failed) must not drag the score.
    n = out["cells"][MODELS[0]]["all"]["frameworks"]["pub_a"]["n_rollouts"]
    self.assertEqual(n, 24)
    self.assertEqual(out["judge"]["criteria_excluded"], 1)
    te = out["turn_endings"]["pub_b"][MODELS[1]]
    self.assertAlmostEqual(te["max_steps_rate"], 2 / 12)  # 2 of 6 scen x 2.

  def test_public_drops_internal(self):
    out = stats.compute(self.recs, self.scen, visibility="public", n_boot=100)
    self.assertNotIn("int_c", out["frameworks"])
    md = report.render(out, self.manifest, "public")
    self.assertNotIn("int_c", md)
    self.assertNotIn("Internal C", md)
    full = stats.compute(self.recs, self.scen, n_boot=100)
    with self.assertRaises(ValueError):
      report.render(full, self.manifest, "public")
    explo = dict(self.manifest, publish=False)
    with self.assertRaises(ValueError):
      report.render(out, explo, "public")
    self.assertNotIn("internal monorepo", md.lower())

  def test_exploratory_banner(self):
    out = stats.compute(self.recs, self.scen, n_boot=50)
    md = report.render(out, dict(self.manifest, publish=False), "internal")
    self.assertIn("EXPLORATORY", md)
    md = report.render(out, self.manifest, "internal")
    self.assertNotIn("EXPLORATORY", md)

  def test_primary_judge_invalid_banner(self):
    rng = random.Random(42)
    degraded_recs = [
        _record(
            "pub_a",
            sc,
            1,
            MODELS[0],
            0.8,
            rng,
            judge_votes={J1: True, J2: None},
        )
        for sc in self.scen
    ]
    out = stats.compute(degraded_recs, self.scen, n_boot=50)
    md = report.render(out, self.manifest, "internal")
    self.assertIn("INCOMPLETE PRIMARY JUDGE PANEL", md)
    self.assertIn(J2, md)

  def test_report_contents(self):
    out = stats.compute(self.recs, self.scen, n_boot=100)
    md = report.render(out, self.manifest, "internal")
    for needle in ("## Executive summary",
                   "### Quick guide: how to read the metrics",
                   "**How to read it:**", "Run id", "Config hash",
                   "opus-5.5-low", "gemini-3.1-pro-preview",
                   "gemma-4-31b-it", "Seeds", "Tier",
                   "Outcome score [95% CI]", "Judge score",
                   "closest competitor", "Per-pillar", "Core vs held-out",
                   "Cross-model swing", "Thinking tok", "Harness errors",
                   "INVALID", "## Limitations", "not human-calibrated",
                   "How turns ended", "max_steps rate",
                   "cross-family", "agent-host", "mocks",
                   "Claude-family agents", "modeling choice"):
      self.assertIn(needle, md)
    self.assertGreaterEqual(md.count("**How to read it:**"), 8)
    self.assertNotRegex(md, r"(?i)rank\s*#")
    self.assertNotIn("composite", md.lower())
    rng = random.Random(99)
    err_recs = [
        _record("pub_a", sc, 1, MODELS[0], 0.0, rng, status="harness_error")
        for sc in self.scen
    ]
    err_out = stats.compute(err_recs, self.scen, n_boot=20)
    err_md = report.render(err_out, self.manifest, "internal")
    self.assertNotIn("Tier 1 Leaders", err_md)


if __name__ == "__main__":
  unittest.main()
