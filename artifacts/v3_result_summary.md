# V3 Result Summary

This report summarizes the current benchmark outputs for the reproducible influenza forecasting pipeline.

## Headline

The current results support age-aware model selection rather than a single globally best model family.

## Overall Series Ranking

| model_name | test_mae | rolling_mean_mae | num_free_params | num_compartments |
| --- | --- | --- | --- | --- |
| fractional_seir | 0.0351 | 0.1340 | 9 | 4 |
| deterministic_seir | 0.0352 | 0.0815 | 8 | 4 |
| probabilistic_seir | 0.0368 | 0.0956 | 9 | 4 |
| constrained_structure_discovery | 0.0370 | 0.0889 | 6 | 3 |

## Probabilistic Calibration

| series_name | interval_level | empirical_coverage | nominal_coverage | coverage_gap | average_interval_width |
| --- | --- | --- | --- | --- | --- |

## Interpretation

- `deterministic_seir` remains the strongest default baseline for the overall series and several adult groups.
- `constrained_structure_discovery` is already useful in selected age groups, especially when simpler discovered structures outperform larger hand-specified models.
- `probabilistic_seir` is best interpreted as a stability and uncertainty baseline rather than the primary point-forecast winner.
- The next research step is to strengthen stability-aware selection across multiple validation splits rather than further increasing raw structural flexibility.
