# Phase 2 Experiment Plan

## Purpose

Phase 2 is intended to convert the current proof-of-concept benchmark into a more disciplined experimental program.

The main lesson from the current benchmark is clear:

- a single globally best model family does not emerge across all age groups
- constrained structure discovery is already useful in selected age groups
- deterministic SEIR remains the strongest default baseline for the overall series and several adult groups
- the probabilistic model currently produces intervals that are too wide and too conservative

Because of that, Phase 2 should not focus on adding more model families. It should focus on strengthening the credibility, calibration, and decision logic of the existing benchmark.

## Phase 2 Goal

The Phase 2 goal is:

To improve the reliability of age-aware model selection by tightening probabilistic calibration, strengthening stability-aware evaluation, and reducing split-sensitive conclusions.

## What Phase 2 Is Not

Phase 2 is not intended to:

- introduce a large new epidemic-model grammar
- add neural-network or black-box forecasting models
- build a full agent-based model
- optimize for one lucky held-out split at the expense of stability
- expand the repository into a broad generalization study before the current benchmark is stabilized

## Current Baseline Conclusions

The current benchmark supports the following working conclusions:

- `deterministic_seir` is the default strong baseline for `Overall` and `18-49 yr`
- `constrained_structure_discovery` is clearly valuable for `0-4 yr` and `50-64 yr`
- `5-17 yr` remains a stability-sensitive case where discovery wins on held-out test MAE but `probabilistic_seir` is preferred by stability-aware recommendation logic
- `>= 65 yr` remains a mixed case where deterministic wins on held-out test MAE and discovery wins on rolling-origin behavior
- probabilistic intervals are consistently over-conservative, with empirical coverage often near `1.0` for nominal `80%` and `95%` intervals

## Main Phase 2 Workstreams

### Workstream 1: Probabilistic Calibration Tightening

This is the highest-priority modeling task in Phase 2.

#### Problem

The current bootstrap-based probabilistic intervals are too wide. Coverage is systematically above nominal levels, which means the model is not yet well calibrated.

#### Objective

Bring empirical interval coverage closer to nominal coverage without destroying useful uncertainty ordering.

#### Proposed Changes

1. Add validation-based interval rescaling.
   Use the validation segment to learn a post-hoc scale multiplier for predictive intervals.

2. Add explicit calibration diagnostics to the fitting loop.
   Track validation interval coverage for `50%`, `80%`, and `95%` intervals.

3. Compare raw bootstrap intervals against calibrated bootstrap intervals.
   Keep both in the artifacts so the effect of calibration is directly measurable.

4. Add age-group-specific calibration summaries.
   Low-incidence groups and high-incidence groups should be compared separately.

#### Success Criteria

- `80%` empirical coverage is materially closer to `0.80`
- `95%` empirical coverage is materially closer to `0.95`
- interval widths shrink meaningfully in over-conservative age groups
- probabilistic point metrics do not degrade dramatically

### Workstream 2: Stronger Stability-Aware Discovery Evaluation

This is the highest-priority discovery task in Phase 2.

#### Problem

Current discovery search already uses rolling-origin and multi-split logic, but the benchmark still shows series where:

- held-out test winner and rolling winner disagree
- recommendations remain sensitive to small score differences

#### Objective

Make discovery selection more robust to split variation and less dependent on a single validation configuration.

#### Proposed Changes

1. Expand blocked validation scoring.
   Keep the current multi-split MAE summary but log the per-block values more explicitly.

2. Add an explicit stability-aware score term based on block-level variance.
   The score should reward candidates that are not only accurate on average, but also consistent across blocked validation windows.

3. Add search diagnostics per candidate.
   Store:
   - mean blocked MAE
   - standard deviation of blocked MAE
   - mean rolling MAE
   - rolling error stability
   - final total score

4. Inspect edge cases where discovery and deterministic SEIR are nearly tied.
   These are the most informative series for Phase 2.

#### Success Criteria

- discovery recommendations become less split-sensitive in borderline age groups
- leaderboards become easier to interpret from stored diagnostics
- best discovered structures remain stable under repeated reruns with the same configuration

### Workstream 3: Recommendation Logic Consolidation

This is the main reporting and decision layer task.

#### Problem

The benchmark already supports age-aware recommendations, but the recommendation logic should become a formal output of the experiment rather than an informal interpretation step.

#### Objective

Treat recommendation generation as a first-class artifact.

#### Proposed Changes

1. Preserve `age_group_recommendation.csv` as the main downstream decision table.

2. Add explicit rationale columns where needed.
   For example:
   - `consensus`
   - `stability_preferred`
   - `test_preferred`

3. Add a short phase summary markdown file for each major run.
   This already started in `v3_result_summary.md`; Phase 2 should make it a stable deliverable.

#### Success Criteria

- every benchmark run ends with an explicit recommendation table
- recommendation logic is easy to explain in one paragraph
- downstream presentation no longer requires manual interpretation of multiple CSV files

## Recommended Experimental Order

Phase 2 should be run in the following order.

### Step 1

Freeze the current benchmark outputs and treat them as the pre-Phase-2 baseline.

Artifacts to preserve:

- `artifacts_age_robustness/benchmark_leaderboard.csv`
- `artifacts_age_robustness/benchmark_series_winners.csv`
- `artifacts_age_robustness/age_group_recommendation.csv`
- `artifacts_age_robustness/probabilistic_calibration_summary.csv`
- `artifacts_age_robustness/v3_result_summary.md`

### Step 2

Implement probabilistic calibration tightening only.

Do not change discovery at the same time. This isolates whether interval calibration improves without confounding effects.

### Step 3

Rerun the full age-group robustness benchmark and compare:

- interval coverage
- average interval width
- point metrics
- recommendation changes

### Step 4

After calibration tightening is evaluated, update discovery scoring only if necessary.

This keeps cause and effect separate.

### Step 5

Run a new benchmark summary and compare Phase 2 against the current baseline.

## Metrics to Watch Closely

Phase 2 should emphasize the following metrics.

### Point Forecasting

- test MAE
- rolling mean MAE
- rolling blocked MAE variance

### Probabilistic Quality

- empirical coverage at `50%`, `80%`, and `95%`
- coverage gap relative to nominal
- average interval width
- negative log-likelihood

### Recommendation Stability

- whether the recommended model changes by age group
- whether discovery remains preferred in `0-4 yr` and `50-64 yr`
- whether probabilistic SEIR becomes a cleaner recommendation in `5-17 yr`
- whether `>= 65 yr` remains split-sensitive

## Concrete Deliverables

By the end of Phase 2, the repository should produce:

1. A calibrated probabilistic baseline with narrower, better-calibrated intervals
2. A clearer stability-aware discovery leaderboard
3. A benchmark summary markdown report for each full run
4. A final age-aware recommendation table that can be used directly in presentation or reporting

## Decision Rule for Phase 2 Completion

Phase 2 should be considered successful if all of the following are true:

- probabilistic coverage is materially closer to nominal targets
- the benchmark still supports age-aware model selection
- discovery continues to provide value in selected age groups
- recommendation logic becomes easier to justify from stored artifacts

If those conditions are met, the project will be ready for a more ambitious Phase 3 that can consider broader validation scope, richer structural grammars, or multi-season extensions.
