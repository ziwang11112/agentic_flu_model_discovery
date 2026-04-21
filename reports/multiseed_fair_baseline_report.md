# Fair Baselines and Multi-Seed Point-Forecast Report

## Scope

This report summarizes the current point-forecast state of the repository after:

- adding fair hospitalization-aware manual baselines
- aggregating performance over five seeds
- comparing model families under age-aware evaluation

The main reference outputs are:

- [`artifacts_multiseed_age_robustness/multiseed_model_summary.csv`](../artifacts_multiseed_age_robustness/multiseed_model_summary.csv)
- [`artifacts_multiseed_age_robustness/multiseed_age_group_recommendation.csv`](../artifacts_multiseed_age_robustness/multiseed_age_group_recommendation.csv)
- [`artifacts_multiseed_age_robustness/multiseed_discovery_structure_frequency.csv`](../artifacts_multiseed_age_robustness/multiseed_discovery_structure_frequency.csv)

This is the strengthened non-LLM control benchmark before explicit observation-structure search is added to the discovery grammar.

## What Changed Relative To The Original Four-Family Benchmark

Two manual baselines were added to make the hospitalization target comparison fairer:

- [`hospitalized_seihr`](../src/models/seihr_hospitalized.py): `S,E,I,H,R` with `y_hat = rho * H`
- [`delayed_observation_seir`](../src/models/seir_delayed_observation.py): standard SEIR dynamics with `y_hat[t] = rho * I[t-d]`, where `d` is selected on validation only

The key practical effect is that discovery is no longer being compared only against `rho * I` baselines.

## Age-Prior Ablation

The current single-seed age-prior ablation summary is:

- [`artifacts_age_prior_ablation/age_prior_ablation_summary.csv`](../artifacts_age_prior_ablation/age_prior_ablation_summary.csv)

Current result:

- `use_age_prior=true` and `use_age_prior=false` produced the same selected discovery structures and the same discovery MAE values for all six series in the current single-seed benchmark

Interpretation:

- the earlier structure pattern is not being trivially forced by the current age prior in the existing single-seed pipeline
- a multi-seed no-age-prior ablation is still useful, but the simplest “the prior wrote the answer” criticism is already weakened

## Five-Seed Model Summary

The main aggregate output is:

- [`artifacts_multiseed_age_robustness/multiseed_model_summary.csv`](../artifacts_multiseed_age_robustness/multiseed_model_summary.csv)

### Stable Discovery Win

`0-4 yr` remains the clearest stable discovery result in the repository.

From the five-seed summary:

- `constrained_structure_discovery`: mean test MAE `0.09083`, std `0.00058`, test win rate `1.0`, rolling win rate `1.0`

Interpretation:

- discovery is not merely competitive here; it is the most stable winner under both held-out and rolling-origin criteria

### Fair Baselines Change The Story

`Overall`

- `delayed_observation_seir`: mean test MAE `0.03506`, test win rate `0.6`
- `deterministic_seir`: mean rolling MAE `0.08190`, rolling win rate `0.4`
- `delayed_observation_seir`: mean rolling MAE `0.08178`, rolling win rate `0.4`

Interpretation:

- once observation delay is modeled explicitly, the overall best-baseline story changes materially
- the practical interpretation becomes “observation-aware baselines are extremely competitive and often stronger on held-out test,” not “deterministic SEIR is the default overall winner”

`18-49 yr`

- `hospitalized_seihr`: mean test MAE `0.04484`, test win rate `0.6`
- `deterministic_seir`: mean rolling MAE `0.07293`, rolling win rate `0.6`

Interpretation:

- discovery is not the main story for this age group
- the main comparison is between a hospitalization-aware baseline and a stability-oriented SEIR baseline

### Split-Sensitive Cases

`5-17 yr`

- `constrained_structure_discovery`: mean test MAE `0.00549`, test win rate `0.8`
- `probabilistic_seir`: mean rolling MAE `0.04202`, rolling win rate `1.0`

Interpretation:

- discovery remains a strong held-out candidate
- probabilistic SEIR remains the most stable rolling-origin model
- this age group should be treated as stability-sensitive rather than discovery-dominated

`>= 65 yr`

- `deterministic_seir`: mean test MAE `0.11967`, test win rate `0.6`
- `constrained_structure_discovery`: mean rolling MAE `0.16187`, rolling win rate `1.0`

Interpretation:

- older adults still show a meaningful split between held-out test winner and rolling-origin winner
- discovery seems to capture useful structural signal, but it is not yet the dominant held-out point-forecast winner

### 50-64 yr Is No Longer A Clean Discovery-Wins Case

`50-64 yr`

- `constrained_structure_discovery`: mean test MAE `0.03716`, test win rate `0.6`
- `hospitalized_seihr`: mean test MAE `0.03733`, test win rate `0.4`
- `delayed_observation_seir`: mean rolling MAE `0.05502`, rolling win rate `0.8`

Interpretation:

- discovery remains competitive and slightly stronger on mean held-out test MAE
- however, stronger manual baselines make this a much less decisive discovery win than it looked in the earlier four-family comparison

## Multi-Seed Recommendation Summary

Recommendation aggregation is written to:

- [`artifacts_multiseed_age_robustness/multiseed_age_group_recommendation.csv`](../artifacts_multiseed_age_robustness/multiseed_age_group_recommendation.csv)

Current recommendation modes:

- `0-4 yr` -> `constrained_structure_discovery`
- `18-49 yr` -> `deterministic_seir`
- `5-17 yr` -> `constrained_structure_discovery`, but rolling winner remains `probabilistic_seir`
- `50-64 yr` -> no single dominant recommendation; discovery and strengthened manual baselines are both plausible
- `>= 65 yr` -> `deterministic_seir`
- `Overall` -> `delayed_observation_seir`

Interpretation:

- only `0-4 yr` currently has a truly clean discovery recommendation
- `18-49 yr` and `Overall` point more strongly toward hospitalization-aware or delay-aware manual baselines
- `50-64 yr`, `5-17 yr`, and `>= 65 yr` remain heterogeneous and should be described carefully

## Discovery Structure Stability

Structure frequencies are written to:

- [`artifacts_multiseed_age_robustness/multiseed_discovery_structure_frequency.csv`](../artifacts_multiseed_age_robustness/multiseed_discovery_structure_frequency.csv)

Stable patterns:

- `Overall`: `SIR|fractional=0|obs=I` at frequency `1.0`
- `18-49 yr`: `SIR|fractional=0|obs=I` at frequency `1.0`
- `50-64 yr`: `SIR|fractional=0|obs=I` at frequency `1.0`
- `>= 65 yr`: `SEIRS|fractional=1|obs=I` at frequency `1.0`
- `0-4 yr`: `SEIRS` family at frequency `1.0` overall, mostly non-fractional
- `5-17 yr`: always `SEIRS`, with fractional toggle variation across seeds

Interpretation:

- the selected discovery structure is often more stable than the final model winner
- this supports a structure-discovery claim even when point-forecast superiority is not universal

## Figures

Recommended plots:

- [`artifacts_multiseed_age_robustness/multiseed_test_mae_errorbars.png`](../artifacts_multiseed_age_robustness/multiseed_test_mae_errorbars.png)
- [`artifacts_multiseed_age_robustness/multiseed_rolling_mae_errorbars.png`](../artifacts_multiseed_age_robustness/multiseed_rolling_mae_errorbars.png)

## Current Interpretation

The repository should now be summarized as follows:

1. A single globally best point-forecast model is not supported.
2. `0-4 yr` is the clearest stable success case for non-LLM constrained discovery.
3. Fair hospitalization-aware baselines materially change the comparison, especially for `Overall` and `18-49 yr`.
4. The strongest current framing is age-aware model selection under structural and observation uncertainty.
5. The current discovery pattern remains interesting because the structures themselves are stable even when the winning model family is not.
