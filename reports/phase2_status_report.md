# Current Benchmark Status Report

## Executive Summary

The repository now has three stable deliverables:

- a reproducible influenza hospitalization-rate forecasting benchmark across four epidemic-model families
- a benchmark-level conformal uncertainty postprocess for the probabilistic baseline
- a strengthened point-forecast benchmark with fair hospitalization-aware baselines, age-prior ablation, and five-seed aggregation

The current evidence does not support a single globally best forecasting model or a single globally best interval-adjustment rule. The main project conclusion remains:

- point-forecast model choice should be age-aware
- uncertainty calibration should be benchmark-level and validation-selected

## Project Objective

The practical goal of the repository is to determine when hand-specified epidemic models are sufficient and when constrained structure discovery adds value for weekly influenza hospitalization-rate forecasting.

The uncertainty-calibration work extends that goal from point forecasts to interval forecasts. The question is no longer only "which model predicts best," but also "which uncertainty postprocess yields intervals that are closer to nominal coverage without becoming unnecessarily wide."

## What Was Added In Phase 2

Phase 2 added benchmark-level conformal calibration on top of the existing probabilistic SEIR artifacts.

Implemented calibration kinds:

- `raw`
- `scale_calibrated`
- `conformal_absolute`
- `conformal_standardized`
- `conformal_asymmetric`

Important constraints that are now enforced:

- point forecasts are unchanged
- conformal processing is benchmark-level, not series-local
- calibration winners are selected using validation rows only
- test rows are evaluation-only
- residual pooling can fall back from same-series to age-family to global pools when calibration counts are small

Main code entry points:

- benchmark CLI: [`run_experiment.py`](../run_experiment.py)
- conformal CLI: [`scripts/run_conformal_postprocess.py`](../scripts/run_conformal_postprocess.py)
- uncertainty package: [`src/uncertainty/`](../src/uncertainty)

## Current Benchmark Results

### Overall Series

From [`artifacts/benchmark_leaderboard.csv`](../artifacts/benchmark_leaderboard.csv):

- `fractional_seir`: test MAE `0.03511`
- `deterministic_seir`: test MAE `0.03523`
- `probabilistic_seir`: test MAE `0.03682`
- `constrained_structure_discovery`: test MAE `0.03697`

Interpretation:

- the overall held-out split is extremely close between `fractional_seir` and `deterministic_seir`
- rolling-origin behavior still makes `deterministic_seir` the more stable practical recommendation

### Updated Point-Forecast Interpretation

The most current point-forecast picture is now in the five-seed aggregation:

- [`artifacts_multiseed_age_robustness/multiseed_model_summary.csv`](../artifacts_multiseed_age_robustness/multiseed_model_summary.csv)
- [`artifacts_multiseed_age_robustness/multiseed_age_group_recommendation.csv`](../artifacts_multiseed_age_robustness/multiseed_age_group_recommendation.csv)
- [`reports/multiseed_fair_baseline_report.md`](../reports/multiseed_fair_baseline_report.md)

Current high-confidence points:

- `0-4 yr`: discovery is the stable winner on both held-out and rolling-origin metrics across all five seeds
- `Overall`: `delayed_observation_seir` is now the strongest held-out test baseline
- `18-49 yr`: `hospitalized_seihr` is now the strongest held-out test baseline
- `5-17 yr`: discovery wins held-out test most often, but probabilistic SEIR wins rolling-origin MAE in every seed
- `>= 65 yr`: deterministic SEIR wins held-out test most often, but discovery wins rolling-origin MAE in every seed

### Single-Seed Age-Group Winners

From [`artifacts_age_robustness/benchmark_series_winners.csv`](../artifacts_age_robustness/benchmark_series_winners.csv):

- `0-4 yr`: discovery wins on both held-out test and rolling-origin MAE
- `18-49 yr`: deterministic SEIR wins on both
- `5-17 yr`: discovery wins on held-out test, but probabilistic SEIR wins on rolling-origin MAE
- `50-64 yr`: discovery wins on both
- `>= 65 yr`: deterministic wins on held-out test, discovery wins on rolling-origin MAE
- `Overall`: deterministic wins on both

From [`artifacts_age_robustness/age_group_recommendation.csv`](../artifacts_age_robustness/age_group_recommendation.csv), the current recommendations are:

- `0-4 yr` -> `constrained_structure_discovery`
- `18-49 yr` -> `deterministic_seir`
- `5-17 yr` -> `probabilistic_seir`
- `50-64 yr` -> `constrained_structure_discovery`
- `>= 65 yr` -> `deterministic_seir`
- `Overall` -> `deterministic_seir`

Single-seed practical conclusion:

- discovery is clearly valuable for `0-4 yr`
- `50-64 yr`, `5-17 yr`, and `>= 65 yr` remain stability-sensitive once fair baselines are added
- the strengthened manual baselines matter materially for `Overall` and `18-49 yr`

### Age-Prior Ablation

The current age-prior ablation summary is:

- [`artifacts_age_prior_ablation/age_prior_ablation_summary.csv`](../artifacts_age_prior_ablation/age_prior_ablation_summary.csv)

Current result:

- in the present single-seed run, `use_age_prior=true` and `use_age_prior=false` give the same selected discovery structures and the same discovery MAE values for all six series

Interpretation:

- the observed structure pattern does not appear to be trivially imposed by the current age prior in the existing single-seed benchmark

## Conformal Calibration Results

The current recommended conformal result set is:

- comparison table: [`artifacts_v5_conformal_v3/probabilistic_calibration_comparison.csv`](../artifacts_v5_conformal_v3/probabilistic_calibration_comparison.csv)
- validation-selected winners: [`artifacts_v5_conformal_v3/calibration_method_winners.csv`](../artifacts_v5_conformal_v3/calibration_method_winners.csv)
- selected test report: [`artifacts_v5_conformal_v3/calibration_selected_test_report.csv`](../artifacts_v5_conformal_v3/calibration_selected_test_report.csv)
- rule-comparison table: [`artifacts_v5_conformal_v3/conformal_rule_comparison.csv`](../artifacts_v5_conformal_v3/conformal_rule_comparison.csv)

### Selection Rule Comparison

Three validation-only winner rules were evaluated over the same calibration outputs.

`V1`

- mean absolute coverage gap: `0.189394`
- mean interval score: `0.460618`
- mean interval width: `0.451670`

`V2`

- mean absolute coverage gap: `0.183838`
- mean interval score: `0.484247`
- mean interval width: `0.473100`

`V3`

- mean absolute coverage gap: `0.184343`
- mean interval score: `0.465319`
- mean interval width: `0.456298`

Interpretation:

- `V1` is too interval-score-driven
- `V2` is too coverage-gap-driven
- `V3` is the best current compromise

### Current Recommended Winner Rule

The repository currently treats `V3` as the preferred conformal-selection rule.

Rule:

- filter out methods with validation `coverage_gap < -0.05`
- then minimize `normalized_abs_coverage_gap + 0.25 * normalized_interval_score`
- then minimize interval width
- if all methods fail the under-coverage floor, fall back to the balanced score without the floor

### V3 Selected Calibration Kinds

From [`artifacts_v5_conformal_v3/calibration_method_winners.csv`](../artifacts_v5_conformal_v3/calibration_method_winners.csv):

- `0-4 yr`: `conformal_asymmetric` for `50/80/95`
- `18-49 yr`: `scale_calibrated` for `50`, `conformal_asymmetric` for `80/95`
- `5-17 yr`: `conformal_asymmetric` for `50`, `scale_calibrated` for `80`, `conformal_absolute` for `95`
- `50-64 yr`: `scale_calibrated` for `50/80`, `conformal_absolute` for `95`
- `>= 65 yr`: `scale_calibrated` for `50/80`, `conformal_absolute` for `95`
- `Overall`: `conformal_asymmetric` for `50`, `conformal_standardized` for `80`, `conformal_absolute` for `95`

Winner counts:

- `conformal_asymmetric`: `7`
- `scale_calibrated`: `6`
- `conformal_absolute`: `4`
- `conformal_standardized`: `1`

### Test-Set Interpretation

The current results do not support a single uniformly best calibration kind across all age groups and interval levels.

Instead:

- lower-confidence intervals often benefit from `conformal_asymmetric` or `scale_calibrated`
- many 95% intervals favor `conformal_absolute`
- age group strongly affects which calibration kind is preferred

This mirrors the point-forecast result: age-aware selection remains more useful than searching for a single globally dominant method.

## Figures Worth Opening First

- overall benchmark comparison: [`artifacts/overall/model_comparison.png`](../artifacts/overall/model_comparison.png)
- age-group rolling MAE heatmap: [`artifacts_age_robustness/benchmark_rolling_mae_heatmap.png`](../artifacts_age_robustness/benchmark_rolling_mae_heatmap.png)
- conformal selected-method heatmap: [`artifacts_v5_conformal_v3/selected_method_by_series_heatmap.png`](../artifacts_v5_conformal_v3/selected_method_by_series_heatmap.png)
- conformal validation coverage by method: [`artifacts_v5_conformal_v3/calibration_validation_coverage_by_method.png`](../artifacts_v5_conformal_v3/calibration_validation_coverage_by_method.png)
- conformal test gap-vs-width view: [`artifacts_v5_conformal_v3/calibration_gap_vs_width_test.png`](../artifacts_v5_conformal_v3/calibration_gap_vs_width_test.png)

## Current Repository Recommendation

The current repository state should be interpreted as follows:

1. Use age-aware point-forecast model selection rather than a single global winner.
2. Treat `0-4 yr` as the clearest stable discovery success case in the current repository.
3. Treat `artifacts_v5_conformal_v3/` as the recommended conformal result set.
4. Keep conformal calibration as uncertainty-only postprocessing; do not mix it into model fitting or fitting-time interval calibration.
5. Treat `V3` as the default winner-selection rule until a later experiment demonstrates a clearly better tradeoff.

## Reproduction

Run the benchmark:

```bash
python run_experiment.py --config configs/age_robustness.yaml --log-level INFO
```

Then run conformal postprocessing:

```bash
python scripts/run_conformal_postprocess.py --config configs/age_robustness.yaml --artifact-root artifacts_age_robustness --output-root artifacts_v5_conformal_v3 --log-level INFO
```
