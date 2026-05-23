# GPT Pro Handoff: Phase 0 + Phase 1 Baseline/Reproducibility Work

## Summary

This branch implements the requested Phase 0 + Phase 1 scope only: reproducibility hygiene plus opt-in forecasting baselines. The historical default benchmark behavior is preserved. If `benchmark.models` is absent, `configs/default.yaml` still runs only the original six core models.

## What Changed

- Added SHA-256 stable seed generation in `src/llm/executor.py`, matching discovery search seed semantics.
- Added `src/utils/paths.py::repo_relative_path` and used it for generated `run_summary.json` paths.
- Added `fit_status` and `numerical_diagnostics` to `run_model_family` metrics output.
- Updated benchmark reporting to read both old and new metrics schemas, include optional `model_family` and fit/numerical columns, and write artifact-root-relative `artifact_dir` values.
- Added opt-in forecasting baselines in `src/baselines/forecasting.py`:
  - `last_observed`
  - `rolling_mean_2wk`
  - `rolling_mean_4wk`
  - `arima_auto_small`
  - `lagged_ridge`
  - `lagged_gradient_boosting`
- Added `src/evaluation/baseline_pipeline.py` to write baseline `metrics.json`, `forecast_trace.csv`, and `rolling_origin_forecasts.csv`.
- Added conservative `equal_weight_point_ensemble`, opt-in only, excluding itself, missing members, and members with `numerical_failure_flag=true`.
- Added opt-in configs:
  - `configs/baseline_ablation_smoke.yaml`
  - `configs/baseline_ablation.yaml`
- Added `statsmodels>=0.14` and `scikit-learn>=1.4` to `requirements.txt`.

## Behavior Notes

- `python run_experiment.py --config configs/default.yaml` remains the old six-model benchmark because `configs/default.yaml` does not define `benchmark.models`.
- New baselines run only when a config explicitly lists them under `benchmark.models`.
- If `equal_weight_point_ensemble` is listed before its members, the benchmark moves it to the end with a warning so member artifacts exist.
- ARIMA selection uses validation MAE only, then refits on train+validation before computing test metrics.
- ARIMA falls back to `last_observed` if all candidate orders fail.
- Ridge and gradient boosting fall back to `rolling_mean_4wk` when data is too short or fitting fails.

## Validation Performed

- Phase 0 focused tests:
  - `python -m pytest tests/test_reproducibility_hygiene.py --basetemp .codex/pytest-tmp -o cache_dir=.codex/pytest-cache`
- New baseline and regression tests:
  - `python -m pytest tests/test_reproducibility_hygiene.py tests/test_forecast_baselines.py --basetemp .codex/pytest-tmp -o cache_dir=.codex/pytest-cache`
  - `python -m pytest tests/test_reporting.py tests/test_run_experiment_config.py tests/test_flusurvnet_multiseason_seasonal_benchmark.py --basetemp .codex/pytest-tmp -o cache_dir=.codex/pytest-cache`
- Full test suite:
  - `python -m pytest --basetemp .codex/pytest-tmp -o cache_dir=.codex/pytest-cache`
  - Result: `115 passed`
- Smoke benchmark:
  - `python run_experiment.py --config configs/baseline_ablation_smoke.yaml --log-level WARNING`
  - Result: completed successfully.
  - Generated smoke artifacts were checked for local absolute paths and then removed so heavy artifacts are not part of the commit.

## Files To Review First

- `run_experiment.py`
- `src/baselines/forecasting.py`
- `src/evaluation/baseline_pipeline.py`
- `src/evaluation/pipeline.py`
- `src/evaluation/reporting.py`
- `tests/test_forecast_baselines.py`
- `tests/test_reproducibility_hygiene.py`

## Out Of Scope

- Discovery ablation baselines were not implemented.
- Paired bootstrap/statistical comparison report was not implemented.
- Heavy generated artifacts were not committed.
