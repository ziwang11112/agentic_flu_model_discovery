# Fair Baselines, Age-Prior Ablation, and Multi-Seed Report

## Scope

This report summarizes the current point-forecast state of the repository after three additions:

- fair hospitalization-aware manual baselines
- single-seed age-prior ablation
- five-seed robustness aggregation

The goal of this stage was to determine whether the earlier discovery results survive stronger manual baselines and seed variation.

## What Changed

Two manual baselines were added to make the hospitalization target comparison fairer:

- [`hospitalized_seihr`](../src/models/seihr_hospitalized.py): `S,E,I,H,R` with `y_hat = rho * H`
- [`delayed_observation_seir`](../src/models/seir_delayed_observation.py): standard SEIR dynamics with `y_hat[t] = rho * I[t-d]`, where `d` is selected from validation only

The discovery loop also now supports explicit age-prior ablation:

- [`configs/age_robustness_age_prior.yaml`](../configs/age_robustness_age_prior.yaml)
- [`configs/age_robustness_no_age_prior.yaml`](../configs/age_robustness_no_age_prior.yaml)

Finally, the repository now supports five-seed aggregation through:

- [`scripts/run_multiseed_benchmark.py`](../scripts/run_multiseed_benchmark.py)
- [`configs/age_robustness_multiseed.yaml`](../configs/age_robustness_multiseed.yaml)

## Age-Prior Ablation

The current single-seed ablation summary is:

- [`artifacts_age_prior_ablation/age_prior_ablation_summary.csv`](../artifacts_age_prior_ablation/age_prior_ablation_summary.csv)

Current result:

- `use_age_prior=true` and `use_age_prior=false` produced the same selected discovery structures and the same discovery MAE values for all six series in the current run

Interpretation:

- the currently observed structure pattern is not being trivially forced by the age prior in the existing single-seed benchmark
- a future multi-seed no-age-prior run is still valuable, but the single-seed result already weakens the simplest “the prior wrote the answer” criticism

## Five-Seed Model Summary

The main aggregate output is:

- [`artifacts_multiseed_age_robustness/multiseed_model_summary.csv`](../artifacts_multiseed_age_robustness/multiseed_model_summary.csv)

### Stable Discovery Win

`0-4 yr` is the clearest stable discovery result in the repository.

From the multi-seed summary:

- `constrained_structure_discovery`: mean test MAE `0.09083`, std `0.00058`, test win rate `1.0`, rolling win rate `1.0`

Interpretation:

- discovery is not merely competitive here; it is the most stable winner under both held-out and rolling-origin criteria

### Stronger Manual Baselines Matter

The new baselines materially changed the interpretation for several series.

`Overall`

- `delayed_observation_seir`: mean test MAE `0.03506`, test win rate `0.6`
- `deterministic_seir`: mean rolling MAE `0.08190`, rolling win rate `0.4`
- `delayed_observation_seir`: mean rolling MAE `0.08178`, rolling win rate `0.4`

Interpretation:

- once observation delay is modeled explicitly, the “overall best baseline” story changes
- the current overall conclusion is no longer “deterministic SEIR is the default winner,” but rather “observation-aware baselines are extremely competitive and often stronger on held-out test”

`18-49 yr`

- `hospitalized_seihr`: mean test MAE `0.04484`, test win rate `0.6`
- `deterministic_seir`: mean rolling MAE `0.07293`, rolling win rate `0.6`

Interpretation:

- discovery is not the main story for this age group
- the meaningful comparison is between a hospitalization-aware manual baseline and a stability-oriented SEIR baseline

### Split-Sensitive Cases

`5-17 yr`

- `constrained_structure_discovery`: mean test MAE `0.00549`, test win rate `0.8`
- `probabilistic_seir`: mean rolling MAE `0.04202`, rolling win rate `1.0`

Interpretation:

- discovery remains a strong held-out candidate
- probabilistic SEIR remains the most stable rolling-origin model
- this age group should still be treated as stability-sensitive

`>= 65 yr`

- `deterministic_seir`: mean test MAE `0.11967`, test win rate `0.6`
- `constrained_structure_discovery`: mean rolling MAE `0.16187`, rolling win rate `1.0`

Interpretation:

- older adults still show a meaningful split between held-out test winner and rolling-origin winner
- discovery seems to capture useful structural signal, but it is not yet the dominant point-forecast winner on the fixed held-out split

### 50-64 yr Is No Longer a Clean Discovery-Wins Case

`50-64 yr`

- `constrained_structure_discovery`: mean test MAE `0.03716`, test win rate `0.6`
- `hospitalized_seihr`: mean test MAE `0.03733`, test win rate `0.4`
- `delayed_observation_seir`: mean rolling MAE `0.05502`, rolling win rate `0.8`

Interpretation:

- discovery remains competitive and slightly stronger on mean held-out test MAE
- however, the new manual baselines make this much less of a decisive discovery win than it looked in the earlier four-family comparison

## Multi-Seed Recommendation Summary

Recommendation aggregation is written to:

- [`artifacts_multiseed_age_robustness/multiseed_age_group_recommendation.csv`](../artifacts_multiseed_age_robustness/multiseed_age_group_recommendation.csv)

Current recommendation modes:

- `0-4 yr` -> `constrained_structure_discovery` with frequency `1.0`
- `18-49 yr` -> `deterministic_seir` with frequency `0.8`
- `5-17 yr` -> `constrained_structure_discovery` with frequency `1.0`, but rolling winner remains `probabilistic_seir` with frequency `1.0`
- `50-64 yr` -> no single dominant recommendation; current mode is `constrained_structure_discovery` with frequency `0.4`
- `>= 65 yr` -> `deterministic_seir` with frequency `0.6`
- `Overall` -> `delayed_observation_seir` with frequency `0.4`

Interpretation:

- only `0-4 yr` currently has a truly clean discovery recommendation
- `18-49 yr` and `Overall` now point more strongly toward hospitalization-aware or delay-aware manual baselines
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

## Current Repository Interpretation

The repository should now be summarized as follows:

1. A single globally best point-forecast model is not supported.
2. `0-4 yr` is the clearest stable success case for non-LLM constrained discovery.
3. Fair hospitalization-aware baselines materially change the comparison, especially for `Overall` and `18-49 yr`.
4. The strongest current project framing is age-aware model selection under structural and observation uncertainty.
5. The current discovery pattern remains interesting because the structures themselves are stable even when the winning model family is not.

## Next Experimental Priority

Given the current state, the next high-value experiments are:

1. multi-seed no-age-prior ablation
2. LLM-V0 structure proposal against the strengthened non-LLM control baseline
3. optional rerun of the single-series overall benchmark with the two new manual baselines written into the canonical `artifacts/` leaderboard
