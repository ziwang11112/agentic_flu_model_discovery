# Objective-Aware Policy Report

## Scope

This report summarizes tie-aware recommendation logic for the observation-aware five-seed benchmark.
The practical tie threshold is applied separately to `mean_test_mae` and `mean_rolling_mae`: 

- `abs(model_metric - best_metric) <= max(0.001, 0.02 * best_metric)`

Objective-specific policies then break ties using win rate, seed-level variability, parameter count, and model simplicity priority.

## Summary

- Objective conflicts appear in `4` of `6` series.
- A shared parsimonious compromise exists in `4` series.

## Series Policies

### 0-4 yr

- test policy: `constrained_structure_discovery`
- rolling policy: `constrained_structure_discovery`
- parsimony policy: `constrained_structure_discovery`
- test tie set: `constrained_structure_discovery`
- rolling tie set: `constrained_structure_discovery`
- reason: Test and rolling objectives agree on constrained_structure_discovery within the practical tie threshold.

### 18-49 yr

- test policy: `deterministic_seir`
- rolling policy: `deterministic_seir`
- parsimony policy: `deterministic_seir`
- test tie set: `deterministic_seir;delayed_observation_seir`
- rolling tie set: `deterministic_seir;delayed_observation_seir;hospitalized_seihr`
- reason: Test and rolling objectives agree on deterministic_seir within the practical tie threshold.

### 5-17 yr

- test policy: `constrained_structure_discovery`
- rolling policy: `probabilistic_seir`
- parsimony policy: `objective_dependent`
- test tie set: `constrained_structure_discovery`
- rolling tie set: `probabilistic_seir`
- reason: Use constrained_structure_discovery for held-out test MAE and probabilistic_seir for rolling-origin stability.

### 50-64 yr

- test policy: `hospitalized_seihr`
- rolling policy: `delayed_observation_seir`
- parsimony policy: `constrained_structure_discovery`
- test tie set: `hospitalized_seihr;constrained_structure_discovery;deterministic_seir;probabilistic_seir;delayed_observation_seir`
- rolling tie set: `delayed_observation_seir;constrained_structure_discovery`
- reason: Test and rolling objectives differ, but constrained_structure_discovery is practically tied for both and is the simplest shared compromise.

### >= 65 yr

- test policy: `deterministic_seir`
- rolling policy: `constrained_structure_discovery`
- parsimony policy: `objective_dependent`
- test tie set: `deterministic_seir;delayed_observation_seir`
- rolling tie set: `constrained_structure_discovery`
- reason: Use deterministic_seir for held-out test MAE and constrained_structure_discovery for rolling-origin stability.

### Overall

- test policy: `delayed_observation_seir`
- rolling policy: `deterministic_seir`
- parsimony policy: `deterministic_seir`
- test tie set: `delayed_observation_seir;deterministic_seir`
- rolling tie set: `deterministic_seir;delayed_observation_seir`
- reason: Test and rolling objectives differ, but deterministic_seir is practically tied for both and is the simplest shared compromise.

## Closest Pairwise Comparisons

### 0-4 yr

- `rolling_mean_mae`: `deterministic_seir` vs `hospitalized_seihr` (mean diff `-0.000036`, practical tie `True`)
- `test_mae`: `delayed_observation_seir` vs `deterministic_seir` (mean diff `-0.000237`, practical tie `True`)

### 18-49 yr

- `test_mae`: `delayed_observation_seir` vs `deterministic_seir` (mean diff `0.000052`, practical tie `True`)
- `rolling_mean_mae`: `delayed_observation_seir` vs `deterministic_seir` (mean diff `0.000148`, practical tie `True`)

### 5-17 yr

- `rolling_mean_mae`: `constrained_structure_discovery` vs `hospitalized_seihr` (mean diff `-0.000520`, practical tie `True`)
- `test_mae`: `delayed_observation_seir` vs `deterministic_seir` (mean diff `0.000822`, practical tie `True`)

### 50-64 yr

- `test_mae`: `delayed_observation_seir` vs `deterministic_seir` (mean diff `-0.000091`, practical tie `True`)
- `test_mae`: `constrained_structure_discovery` vs `hospitalized_seihr` (mean diff `-0.000119`, practical tie `True`)

### >= 65 yr

- `test_mae`: `delayed_observation_seir` vs `deterministic_seir` (mean diff `0.000045`, practical tie `True`)
- `rolling_mean_mae`: `delayed_observation_seir` vs `deterministic_seir` (mean diff `-0.000185`, practical tie `True`)

### Overall

- `rolling_mean_mae`: `constrained_structure_discovery` vs `probabilistic_seir` (mean diff `0.000043`, practical tie `True`)
- `rolling_mean_mae`: `delayed_observation_seir` vs `deterministic_seir` (mean diff `-0.000120`, practical tie `True`)
