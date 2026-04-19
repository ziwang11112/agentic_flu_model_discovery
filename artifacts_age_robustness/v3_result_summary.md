# V3 Result Summary

This report summarizes the current benchmark outputs for the reproducible influenza forecasting pipeline.

## Headline

The current results support age-aware model selection rather than a single globally best model family.

## Overall Series Ranking

| model_name | test_mae | rolling_mean_mae | num_free_params | num_compartments |
| --- | --- | --- | --- | --- |
| deterministic_seir | 0.0356 | 0.0816 | 8 | 4 |
| probabilistic_seir | 0.0368 | 0.0957 | 9 | 4 |
| constrained_structure_discovery | 0.0370 | 0.0889 | 6 | 3 |
| fractional_seir | 0.1230 | 0.1371 | 9 | 4 |

## Age-Group Winners

| series_name | best_test_model | best_test_mae | best_rolling_model | best_rolling_mean_mae |
| --- | --- | --- | --- | --- |
| 0-4 yr | constrained_structure_discovery | 0.0911 | constrained_structure_discovery | 0.1137 |
| 18-49 yr | deterministic_seir | 0.0449 | deterministic_seir | 0.0732 |
| 5-17 yr | constrained_structure_discovery | 0.0110 | probabilistic_seir | 0.0385 |
| 50-64 yr | constrained_structure_discovery | 0.0372 | constrained_structure_discovery | 0.0540 |
| >= 65 yr | deterministic_seir | 0.1197 | constrained_structure_discovery | 0.1824 |
| Overall | deterministic_seir | 0.0356 | deterministic_seir | 0.0816 |

## Recommended Models

| series_name | recommended_model | decision_type | best_test_model | best_rolling_model |
| --- | --- | --- | --- | --- |
| 0-4 yr | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 18-49 yr | deterministic_seir | consensus | deterministic_seir | deterministic_seir |
| 5-17 yr | probabilistic_seir | stability_preferred | constrained_structure_discovery | probabilistic_seir |
| 50-64 yr | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| >= 65 yr | deterministic_seir | test_preferred | deterministic_seir | constrained_structure_discovery |
| Overall | deterministic_seir | consensus | deterministic_seir | deterministic_seir |

## Recommendation Tally

- `constrained_structure_discovery` recommended for 2 series
- `deterministic_seir` recommended for 3 series
- `probabilistic_seir` recommended for 1 series

## Probabilistic Calibration

| series_name | interval_level | empirical_coverage | nominal_coverage | coverage_gap | average_interval_width |
| --- | --- | --- | --- | --- | --- |
| 0-4 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 0.7184 |
| 0-4 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 0.9580 |
| 18-49 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 0.4732 |
| 18-49 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 0.6698 |
| 5-17 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 0.4376 |
| 5-17 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 0.6988 |
| 50-64 yr | 80 | 0.8182 | 0.8000 | 0.0182 | 0.3308 |
| 50-64 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 0.7765 |
| >= 65 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 1.2531 |
| >= 65 yr | 95 | 0.9091 | 0.9500 | -0.0409 | 1.6843 |
| Overall | 80 | 1.0000 | 0.8000 | 0.2000 | 0.4786 |
| Overall | 95 | 0.9091 | 0.9500 | -0.0409 | 0.6754 |

## Interpretation

- `deterministic_seir` remains the strongest default baseline for the overall series and several adult groups.
- `constrained_structure_discovery` is already useful in selected age groups, especially when simpler discovered structures outperform larger hand-specified models.
- `probabilistic_seir` is best interpreted as a stability and uncertainty baseline rather than the primary point-forecast winner.
- The next research step is to strengthen stability-aware selection across multiple validation splits rather than further increasing raw structural flexibility.
