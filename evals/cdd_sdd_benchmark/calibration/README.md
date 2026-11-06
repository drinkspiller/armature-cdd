# Judge calibration

The LLM judge score is secondary to the deterministic outcome score, and until
humans label a sample, nobody knows how accurate the judge is. Until then, the
report says so in its Limitations section. This directory holds the tools to
measure judge accuracy against human labels.

## Workflow

1.  **Judge a run.** `run_benchmark.py judge` fills `judge[]` in
    `results/<run_id>/rollouts.jsonl`.

2.  **Draw the sample.** From the benchmark root:

    ```bash
    python3 calibration/sample_for_labeling.py \
        --rollouts results/<run_id>/rollouts.jsonl \
        --scenarios tasks/core_v2.jsonl --scenarios tasks/heldout_v2.jsonl \
        --registry frameworks/registry.json \
        --out /tmp/armature_bench/calibration/<run_id>
    ```

    This draws 100 judged criteria stratified by pillar x framework x judge
    agreement (agree, disagree, or invalid), using equal allocation across
    strata so that rare strata such as disagreements show up. By default it
    includes public frameworks only (`--include-internal` adds the rest).
    Output goes to `/tmp` because it contains full transcripts. The script
    refuses to write into a source workspace.

    - `labeling.html`: a single static page. Open it in a browser (no
      server needed). Labels are kept in the browser's localStorage.
    - `items.csv`: item ids and criteria.
    - `key.csv`: the mapping from item id to framework, model, scenario, seed,
      stratum, sampling weight, and judge votes. **Labelers must not open it.**

3.  **Label.** Each labeler opens `labeling.html`, enters a name, marks every
    item Yes (criterion met) or No, and clicks **Export labels CSV**. The page
    shows the blinded transcript, the action log, and the criterion. It does
    not show the framework, the target model, or any judge verdict, so labels
    are not anchored on the judge. Two or more labelers are recommended; the
    tool reports human-human kappa when they overlap.

4.  **Compute agreement.**

    ```bash
    python3 calibration/compute_agreement.py \
        --key /tmp/armature_bench/calibration/<run_id>/key.csv \
        --labels labels_alice.csv --labels labels_bob.csv
    ```

    This writes `calibration/agreement.json` with, for each judge model and
    the ensemble (score > 0.5 counts as pass, ties excluded):

    - Cohen's kappa vs the human label, with a 95% CI from a bootstrap that
      resamples whole scenarios.
    - Raw agreement and the number of items.
    - A population-weighted kappa that undoes the stratified oversampling.
    - Human-human kappa for each pair of labelers.

    The human label for an item is the majority across labelers. Ties are
    excluded.

5.  **Re-render the report.** `bench/report.py` picks up
    `calibration/agreement.json` when it contains real labels, and replaces the
    "not human-calibrated" limitation with the measured agreement and the run
    it came from.

## Rules

- Never fabricate, impute, or model-generate labels. `compute_agreement.py`
  exits non-zero when it finds no human labels.
- Calibration from one run applies to the judge models and prompt used in that
  run. When `bench/judge.py` changes its prompt or models, label a new sample.
- Commit only `agreement.json` (and, optionally, the label CSVs, which contain
  only item ids, yes/no labels, and notes). Do not commit `labeling.html` or
  any file that contains transcripts.
