# Observation-Structure Multi-Seed Report

## Scope

This report summarizes the latest five-seed benchmark rerun after making observation structure a first-class part of constrained discovery.

The updated grammar now allows discovery to choose among:

- `obs=I`
- `obs=H`
- `obs=I+H`
- `obs=delayed_I` with `delay_weeks in {1,2,3}`

The corresponding aggregate outputs are:

- [`artifacts_multiseed_age_robustness_observation/multiseed_model_summary.csv`](../artifacts_multiseed_age_robustness_observation/multiseed_model_summary.csv)
- [`artifacts_multiseed_age_robustness_observation/multiseed_age_group_recommendation.csv`](../artifacts_multiseed_age_robustness_observation/multiseed_age_group_recommendation.csv)
- [`artifacts_multiseed_age_robustness_observation/multiseed_discovery_structure_frequency.csv`](../artifacts_multiseed_age_robustness_observation/multiseed_discovery_structure_frequency.csv)

## What Changed In This Rerun

Three changes define this stage:

1. The manual `hospitalized_seihr` baseline was corrected so `I` can flow both to `H` and directly to `R`.
2. Discovery now searches over observation maps and observation delay, not only over compartment topology and the fractional toggle.
3. The full five-seed benchmark was rerun in a fresh output root so the results do not overwrite older multi-seed aggregates.

The purpose of this stage was to answer a narrower question before adding LLM agents:

Can the non-LLM grammar itself discover useful observation structure for hospitalization-rate forecasting?

## Main Result

The answer is partially yes, but in a selective way.

- Discovery now selects `delayed_I` in multiple age groups.
- Discovery does not select `H` or `I+H` in the current season-level benchmark.
- The strongest repository claim therefore shifts from “discovery finds better compartment structures” to “discovery can recover age-dependent observation semantics, especially delayed observation.”

## Five-Seed Model Summary

From [`artifacts_multiseed_age_robustness_observation/multiseed_model_summary.csv`](../artifacts_multiseed_age_robustness_observation/multiseed_model_summary.csv):

### Stable Discovery Win

`0-4 yr`

- `constrained_structure_discovery`: mean test MAE `0.09060`, std `0.00105`
- test win rate `1.0`
- rolling win rate `1.0`

Interpretation:

- `0-4 yr` remains the clearest stable non-LLM discovery success case in the repository
- the new observation grammar does not weaken this result

### Manual Baselines Stay Very Strong

`Overall`

- `delayed_observation_seir`: mean test MAE `0.03506`, test win rate `0.8`
- `deterministic_seir`: mean rolling MAE `0.08190`, rolling win rate `0.4`
- `delayed_observation_seir`: mean rolling MAE `0.08178`, rolling win rate `0.4`

Interpretation:

- for the overall series, manual delay-aware observation remains stronger than discovery

`18-49 yr`

- `deterministic_seir`: mean test MAE `0.04486`, rolling win rate `0.6`
- `hospitalized_seihr`: mean test MAE `0.04689`, test win rate `0.4`

Interpretation:

- discovery is not competitive here
- the important comparison remains between strong hand-designed baselines

`50-64 yr`

- `hospitalized_seihr`: test win rate `0.6`
- `delayed_observation_seir`: rolling win rate `0.8`
- `constrained_structure_discovery`: test win rate `0.4`, rolling win rate `0.2`

Interpretation:

- once observation-aware baselines are in place, `50-64 yr` no longer looks like a clean discovery-wins series

### Split-Sensitive Groups Remain

`5-17 yr`

- `constrained_structure_discovery`: mean test MAE `0.00680`, test win rate `0.8`
- `probabilistic_seir`: mean rolling MAE `0.04202`, rolling win rate `1.0`

`>= 65 yr`

- `deterministic_seir`: mean test MAE `0.11967`, test win rate `0.6`
- `constrained_structure_discovery`: mean rolling MAE `0.18638`, rolling win rate `0.8`

Interpretation:

- these groups still separate “best fixed held-out split” from “best rolling-origin stability”
- the new observation grammar changes which structures discovery chooses, but it does not eliminate the stability split

## Which Observation Maps Were Selected?

The full answer is in:

- [`artifacts_multiseed_age_robustness_observation/multiseed_discovery_structure_frequency.csv`](../artifacts_multiseed_age_robustness_observation/multiseed_discovery_structure_frequency.csv)

### Discovery Selected `delayed_I`

`0-4 yr`

- `SEIRS|fractional=1|obs=delayed_I|delay=1`: `1/5`
- `SEIRS|fractional=0|obs=delayed_I|delay=2`: `1/5`

`5-17 yr`

- `SEIRS|fractional=0|obs=delayed_I|delay=2`: `1/5`
- `SEIRS|fractional=0|obs=delayed_I|delay=3`: `1/5`

`>= 65 yr`

- `SEIRS|fractional=1|obs=delayed_I|delay=2`: `3/5`

Interpretation:

- children and older adults are the groups where explicit observation delay now emerges from the non-LLM search

### Discovery Did Not Select `H` Or `I+H`

No selected discovery winner across the five seeds uses:

- `obs=H`
- `obs=I+H`

Interpretation:

- in the current proof-of-concept season, hospitalization semantics are better captured by observation delay than by explicitly choosing `H` as the discovered observation target
- that does not mean `H` is useless; it means the present benchmark does not yet provide evidence that discovery prefers it

### Series With Stable `obs=I`

`Overall`, `18-49 yr`, and `50-64 yr` remain:

- `SIR|fractional=0|obs=I`

Interpretation:

- the new observation grammar does not force more complex observation maps where the simpler one is adequate

## Recommendation Summary

From [`artifacts_multiseed_age_robustness_observation/multiseed_age_group_recommendation.csv`](../artifacts_multiseed_age_robustness_observation/multiseed_age_group_recommendation.csv):

- `0-4 yr` -> `constrained_structure_discovery`
- `18-49 yr` -> `deterministic_seir`
- `5-17 yr` -> `constrained_structure_discovery`, but rolling winner remains `probabilistic_seir`
- `50-64 yr` -> `delayed_observation_seir`
- `>= 65 yr` -> `deterministic_seir`
- `Overall` -> `deterministic_seir` by recommendation mode, though the best held-out test model is usually `delayed_observation_seir`

Interpretation:

- the current story is not “discovery globally wins once observation is added”
- the current story is “observation-aware baselines and observation-aware discovery both matter, but in different age groups”

## Observation-Aware No-Age-Prior Ablation

The corresponding no-age-prior comparison is summarized in:

- [`artifacts_multiseed_observation_age_prior_ablation/multiseed_age_prior_ablation_summary.csv`](../artifacts_multiseed_observation_age_prior_ablation/multiseed_age_prior_ablation_summary.csv)
- [`artifacts_multiseed_observation_age_prior_ablation/multiseed_age_prior_structure_comparison.csv`](../artifacts_multiseed_observation_age_prior_ablation/multiseed_age_prior_structure_comparison.csv)
- [`artifacts_multiseed_observation_age_prior_ablation/multiseed_age_prior_model_delta.csv`](../artifacts_multiseed_observation_age_prior_ablation/multiseed_age_prior_model_delta.csv)
- [`reports/multiseed_observation_age_prior_ablation_report.md`](../reports/multiseed_observation_age_prior_ablation_report.md)

Current result:

- removing the age prior changes none of the six recommended model modes
- removing the age prior changes none of the six dominant discovery structure modes
- removing the age prior changes none of the dominant observation-map modes
- removing the age prior changes none of the dominant delay modes
- discovery mean test MAE and discovery mean rolling MAE are numerically unchanged for all six series

Interpretation:

- the observation-aware discovery results, including the newly selected `delayed_I` structures, are not being driven by the current age prior
- this substantially strengthens the non-LLM control condition for future LLM proposal experiments

## Objective-Aware Policy Layer

The tie-aware objective-policy summary is now available in:

- [`artifacts_multiseed_age_robustness_observation/multiseed_objective_policy.csv`](../artifacts_multiseed_age_robustness_observation/multiseed_objective_policy.csv)
- [`artifacts_multiseed_age_robustness_observation/pairwise_model_differences.csv`](../artifacts_multiseed_age_robustness_observation/pairwise_model_differences.csv)
- [`reports/objective_aware_policy_report.md`](../reports/objective_aware_policy_report.md)

This layer applies a practical tie rule separately to `mean_test_mae` and
`mean_rolling_mae`:

- `abs(model_metric - best_metric) <= max(0.001, 0.02 * best_metric)`

Current result:

- `4/6` series show an explicit conflict between held-out-test and rolling-origin objectives
- `4/6` series still admit a shared parsimonious compromise model
- only `5-17 yr` and `>= 65 yr` remain fully objective-dependent under the current tie rule

Examples:

- `Overall`: `delayed_observation_seir` is the test-policy winner, but `deterministic_seir` is the rolling-policy winner and also the parsimonious compromise because both are practically tied
- `50-64 yr`: `hospitalized_seihr` is the test-policy winner, `delayed_observation_seir` is the rolling-policy winner, and `constrained_structure_discovery` remains the simplest shared compromise inside both tie sets
- `0-4 yr`: all three policies agree on `constrained_structure_discovery`

Interpretation:

- the current observation-aware benchmark is better described as age-aware and objective-aware than as a single leaderboard race
- this makes the non-LLM control stronger, because future LLM experiments can be evaluated against both fixed-objective winners and tie-aware practical policies

## Figures

- [`artifacts_multiseed_age_robustness_observation/multiseed_test_mae_errorbars.png`](../artifacts_multiseed_age_robustness_observation/multiseed_test_mae_errorbars.png)
- [`artifacts_multiseed_age_robustness_observation/multiseed_rolling_mae_errorbars.png`](../artifacts_multiseed_age_robustness_observation/multiseed_rolling_mae_errorbars.png)

## Current Repository Interpretation

The latest benchmark evidence supports the following interpretation:

1. Observation structure should be treated as a first-class modeling choice.
2. Non-LLM discovery can recover delayed-observation semantics in some age groups.
3. The current season-level benchmark does not support a claim that discovery prefers hospitalization observation maps such as `H` or `I+H`.
4. The observation-aware discovery results remain unchanged when the age prior is removed in the five-seed benchmark.
5. The strongest overall framing remains age-aware model selection under structural and observation uncertainty.
6. This observation-aware grammar is now a stronger non-LLM control baseline for future LLM proposal experiments.
