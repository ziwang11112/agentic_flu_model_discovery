# Reproducibility Snapshot: LLM-V1 Mock Run

## Git Snapshot

- committed snapshot hash: `dc30b7c`
- note: the working tree is not clean; the current `git status --short` is captured below exactly as observed during snapshot creation

```text
 M artifacts_age_robustness/overall/deterministic_seir/forecast_trace.csv
 M artifacts_age_robustness/overall/deterministic_seir/full_series_fit.png
 M artifacts_age_robustness/overall/deterministic_seir/metrics.json
 M artifacts_age_robustness/overall/deterministic_seir/residuals.png
 M artifacts_age_robustness/overall/deterministic_seir/rolling_origin.png
 M artifacts_age_robustness/overall/deterministic_seir/rolling_origin_forecasts.csv
 M artifacts_llm_v1/0_4_yr/llm_refinement_trace.jsonl
 M artifacts_llm_v1/18_49_yr/llm_refinement_trace.jsonl
 M artifacts_llm_v1/50_64_yr/llm_refinement_trace.jsonl
 M artifacts_llm_v1/5_17_yr/llm_refinement_trace.jsonl
 M artifacts_llm_v1/ge__65_yr/llm_refinement_trace.jsonl
 M artifacts_llm_v1/overall/llm_refinement_trace.jsonl
 M artifacts_multiseed_age_robustness/multiseed_age_group_recommendation.csv
 M src/llm/orchestrator.py
 M src/llm/trace.py
 M tests/test_llm_v1_trace.py
?? artifacts/overall/delayed_observation_seir/
?? artifacts/overall/hospitalized_seihr/
?? artifacts/overall/probabilistic_seir/validation_forecast_trace.csv
?? artifacts_age_robustness_age_prior/
?? artifacts_age_robustness_no_age_prior/
?? artifacts_multiseed_age_robustness_observation/seed_runs/
?? artifacts_multiseed_age_robustness_observation/temp_configs/
?? artifacts_multiseed_age_robustness_observation_no_age_prior/
?? artifacts_v5_conformal/
?? artifacts_v5_conformal_v2/
?? reports/llm_v1_artifact_validation_report.md
?? scripts/validate_llm_v1_artifacts.py
```

## Runtime Environment

- Python version: `Python 3.11.11`
- pytest result: `71 passed`
- provider: `mock`
- scientific_claim_allowed: `false`

## Exact Commands Used

```bash
python scripts/run_llm_iterative_refinement.py --config configs/llm_v1_iterative.yaml --all-series --provider mock --log-level INFO
python scripts/build_llm_v1_report.py --config configs/llm_v1_iterative.yaml --artifact-root artifacts_llm_v1 --output reports/llm_v1_iterative_report.md
python scripts/validate_llm_v1_artifacts.py --artifact-root artifacts_llm_v1 --report reports/llm_v1_artifact_validation_report.md
```

## Artifact Roots

- `artifacts_llm_v1/`
- `reports/llm_v1_iterative_report.md`

## Notes

- This snapshot corresponds to the mock-only LLM-V1 iterative refinement pipeline.
- Mock provider results are engineering smoke tests and should not be interpreted as evidence of LLM reasoning quality.
- Final artifact validation passed; see `reports/llm_v1_artifact_validation_report.md`.
