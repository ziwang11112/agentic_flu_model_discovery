# Multi-Seed Observation Age-Prior Ablation Report

## Inputs

- `artifacts_multiseed_age_robustness_observation/`
- `artifacts_multiseed_age_robustness_observation_no_age_prior/`

## Main Answers

- Did age prior materially change selected structures? No. Structure mode changed in 0 of 6 series.
- Did age prior materially change delayed_I selection? Delayed-observation selection was unchanged between age-prior and no-age-prior runs; the same delayed_I patterns were selected in both settings.
- Did age prior improve or hurt test/rolling MAE? No measurable effect. Mean absolute discovery test-MAE delta = 0.000000; mean absolute discovery rolling-MAE delta = 0.000000.
- Which series are robust to removing age prior? 0-4 yr, 18-49 yr, 5-17 yr, 50-64 yr, >= 65 yr, Overall.

## Series-Level Summary

- `0-4 yr`: Robust to removing age prior; no change in recommendation, structure, delay, or discovery MAE.
- `18-49 yr`: Robust to removing age prior; no change in recommendation, structure, delay, or discovery MAE.
- `5-17 yr`: Robust to removing age prior; no change in recommendation, structure, delay, or discovery MAE.
- `50-64 yr`: Robust to removing age prior; no change in recommendation, structure, delay, or discovery MAE.
- `>= 65 yr`: Robust to removing age prior; no change in recommendation, structure, delay, or discovery MAE.
- `Overall`: Robust to removing age prior; no change in recommendation, structure, delay, or discovery MAE.

## Interpretation

Across the observation-aware five-seed benchmark, removing the age prior did not change the recommended model mode, the dominant discovery structure, the selected observation map mode, the delay mode, or the aggregate discovery MAE values. This strengthens the non-LLM control story: the observed delayed_I selections arise from the search objective and data rather than from the age prior.
