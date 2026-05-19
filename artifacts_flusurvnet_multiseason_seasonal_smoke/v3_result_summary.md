# V3 Result Summary

This report summarizes the current benchmark outputs for the reproducible influenza forecasting pipeline.

## Headline

The current results support age-aware model selection rather than a single globally best model family.

## Overall Series Ranking

No overall-series summary was found.

## Age-Group Winners

| series_name | best_test_model | best_test_mae | best_rolling_model | best_rolling_mean_mae |
| --- | --- | --- | --- | --- |
| 2018-19 / Overall | delayed_observation_seir | 3.1477 | constrained_structure_discovery | 0.8783 |
| 2019-20 / Overall | constrained_structure_discovery | 2.2617 | constrained_structure_discovery | 0.8346 |
| 2021-22 / Overall | constrained_structure_discovery | 0.2927 | constrained_structure_discovery | 0.3293 |
| 2022-23 / Overall | constrained_structure_discovery | 0.1585 | constrained_structure_discovery | 0.1495 |
| 2023-24 / Overall | deterministic_seir | 0.0352 | constrained_structure_discovery | 0.0756 |
| 2024-25 / Overall | constrained_structure_discovery | 0.2585 | constrained_structure_discovery | 0.8421 |

## Recommended Models

| series_name | recommended_model | decision_type | best_test_model | best_rolling_model |
| --- | --- | --- | --- | --- |
| 2018-19 / Overall | delayed_observation_seir | test_preferred | delayed_observation_seir | constrained_structure_discovery |
| 2019-20 / Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2021-22 / Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2022-23 / Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2023-24 / Overall | deterministic_seir | test_preferred | deterministic_seir | constrained_structure_discovery |
| 2024-25 / Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |

## Recommendation Tally

- `constrained_structure_discovery` recommended for 4 series
- `delayed_observation_seir` recommended for 1 series
- `deterministic_seir` recommended for 1 series

## Interpretation

- `deterministic_seir` remains the strongest default baseline for the overall series and several adult groups.
- `constrained_structure_discovery` is already useful in selected age groups, especially when simpler discovered structures outperform larger hand-specified models.
- `probabilistic_seir` is best interpreted as a stability and uncertainty baseline rather than the primary point-forecast winner.
- The next research step is to strengthen stability-aware selection across multiple validation splits rather than further increasing raw structural flexibility.
