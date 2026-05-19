# V3 Result Summary

This report summarizes the current benchmark outputs for the reproducible influenza forecasting pipeline.

## Headline

The current results support age-aware model selection rather than a single globally best model family.

## Overall Series Ranking

No overall-series summary was found.

## Age-Group Winners

| series_name | best_test_model | best_test_mae | best_rolling_model | best_rolling_mean_mae |
| --- | --- | --- | --- | --- |
| 2018-19 / 0-4 yr | fractional_seir | 2.2124 | constrained_structure_discovery | 1.2170 |
| 2018-19 / >= 65 yr | deterministic_seir | 4.4090 | delayed_observation_seir | 7.7006 |
| 2018-19 / Overall | delayed_observation_seir | 1.0110 | constrained_structure_discovery | 1.7190 |
| 2019-20 / 0-4 yr | probabilistic_seir | 1.4107 | constrained_structure_discovery | 2.1300 |
| 2019-20 / >= 65 yr | hospitalized_seihr | 7.1492 | deterministic_seir | 6.6316 |
| 2019-20 / Overall | probabilistic_seir | 1.3225 | constrained_structure_discovery | 1.2580 |
| 2021-22 / 0-4 yr | constrained_structure_discovery | 0.4100 | constrained_structure_discovery | 0.4607 |
| 2021-22 / >= 65 yr | constrained_structure_discovery | 1.0218 | constrained_structure_discovery | 1.3125 |
| 2021-22 / Overall | constrained_structure_discovery | 0.2927 | constrained_structure_discovery | 0.4635 |
| 2022-23 / 0-4 yr | constrained_structure_discovery | 0.1962 | fractional_seir | 0.1989 |
| 2022-23 / >= 65 yr | probabilistic_seir | 0.3514 | deterministic_seir | 0.4034 |
| 2022-23 / Overall | fractional_seir | 0.1575 | constrained_structure_discovery | 0.1597 |
| 2023-24 / 0-4 yr | constrained_structure_discovery | 0.1002 | constrained_structure_discovery | 0.1579 |
| 2023-24 / >= 65 yr | constrained_structure_discovery | 0.1317 | delayed_observation_seir | 0.2337 |
| 2023-24 / Overall | deterministic_seir | 0.0350 | deterministic_seir | 0.0774 |
| 2024-25 / 0-4 yr | constrained_structure_discovery | 0.3300 | constrained_structure_discovery | 2.1830 |
| 2024-25 / >= 65 yr | probabilistic_seir | 0.4288 | constrained_structure_discovery | 9.0007 |
| 2024-25 / Overall | constrained_structure_discovery | 0.2358 | constrained_structure_discovery | 1.5419 |

## Recommended Models

| series_name | recommended_model | decision_type | best_test_model | best_rolling_model |
| --- | --- | --- | --- | --- |
| 2018-19 / 0-4 yr | constrained_structure_discovery | stability_preferred | fractional_seir | constrained_structure_discovery |
| 2018-19 / >= 65 yr | delayed_observation_seir | stability_preferred | deterministic_seir | delayed_observation_seir |
| 2018-19 / Overall | delayed_observation_seir | test_preferred | delayed_observation_seir | constrained_structure_discovery |
| 2019-20 / 0-4 yr | deterministic_seir | balanced_tradeoff | probabilistic_seir | constrained_structure_discovery |
| 2019-20 / >= 65 yr | deterministic_seir | stability_preferred | hospitalized_seihr | deterministic_seir |
| 2019-20 / Overall | constrained_structure_discovery | stability_preferred | probabilistic_seir | constrained_structure_discovery |
| 2021-22 / 0-4 yr | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2021-22 / >= 65 yr | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2021-22 / Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2022-23 / 0-4 yr | constrained_structure_discovery | test_preferred | constrained_structure_discovery | fractional_seir |
| 2022-23 / >= 65 yr | deterministic_seir | stability_preferred | probabilistic_seir | deterministic_seir |
| 2022-23 / Overall | constrained_structure_discovery | stability_preferred | fractional_seir | constrained_structure_discovery |
| 2023-24 / 0-4 yr | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2023-24 / >= 65 yr | constrained_structure_discovery | test_preferred | constrained_structure_discovery | delayed_observation_seir |
| 2023-24 / Overall | deterministic_seir | consensus | deterministic_seir | deterministic_seir |
| 2024-25 / 0-4 yr | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2024-25 / >= 65 yr | hospitalized_seihr | balanced_tradeoff | probabilistic_seir | constrained_structure_discovery |
| 2024-25 / Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |

## Recommendation Tally

- `constrained_structure_discovery` recommended for 11 series
- `delayed_observation_seir` recommended for 2 series
- `deterministic_seir` recommended for 4 series
- `hospitalized_seihr` recommended for 1 series

## Probabilistic Calibration

| series_name | interval_level | empirical_coverage | nominal_coverage | coverage_gap | average_interval_width |
| --- | --- | --- | --- | --- | --- |
| 2018-19 / 0-4 yr | 80 | 0.0000 | 0.8000 | -0.8000 | 0.9594 |
| 2018-19 / 0-4 yr | 95 | 0.0000 | 0.9500 | -0.9500 | 1.2648 |
| 2018-19 / >= 65 yr | 80 | 0.0000 | 0.8000 | -0.8000 | 9.7015 |
| 2018-19 / >= 65 yr | 95 | 0.0000 | 0.9500 | -0.9500 | 21.1362 |
| 2018-19 / Overall | 80 | 0.1429 | 0.8000 | -0.6571 | 48.1411 |
| 2018-19 / Overall | 95 | 0.2857 | 0.9500 | -0.6643 | 120.0655 |
| 2019-20 / 0-4 yr | 80 | 0.1429 | 0.8000 | -0.6571 | 1.8865 |
| 2019-20 / 0-4 yr | 95 | 0.1429 | 0.9500 | -0.8071 | 2.3807 |
| 2019-20 / >= 65 yr | 80 | 0.0000 | 0.8000 | -0.8000 | 2.7504 |
| 2019-20 / >= 65 yr | 95 | 0.0000 | 0.9500 | -0.9500 | 4.2550 |
| 2019-20 / Overall | 80 | 0.0000 | 0.8000 | -0.8000 | 1.4402 |
| 2019-20 / Overall | 95 | 0.0000 | 0.9500 | -0.9500 | 1.8931 |
| 2021-22 / 0-4 yr | 80 | 0.0000 | 0.8000 | -0.8000 | 0.1939 |
| 2021-22 / 0-4 yr | 95 | 0.0000 | 0.9500 | -0.9500 | 0.2987 |
| 2021-22 / >= 65 yr | 80 | 0.0000 | 0.8000 | -0.8000 | 0.8755 |
| 2021-22 / >= 65 yr | 95 | 0.0000 | 0.9500 | -0.9500 | 1.2470 |
| 2021-22 / Overall | 80 | 0.7500 | 0.8000 | -0.0500 | 20.2129 |
| 2021-22 / Overall | 95 | 1.0000 | 0.9500 | 0.0500 | 77.0186 |
| 2022-23 / 0-4 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 0.3721 |
| 2022-23 / 0-4 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 0.6186 |
| 2022-23 / >= 65 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 1.4271 |
| 2022-23 / >= 65 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 1.8548 |
| 2022-23 / Overall | 80 | 0.7143 | 0.8000 | -0.0857 | 0.2722 |
| 2022-23 / Overall | 95 | 0.8571 | 0.9500 | -0.0929 | 0.3244 |
| 2023-24 / 0-4 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 0.5268 |
| 2023-24 / 0-4 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 0.7325 |
| 2023-24 / >= 65 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 1.1631 |
| 2023-24 / >= 65 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 1.4592 |
| 2023-24 / Overall | 80 | 1.0000 | 0.8000 | 0.2000 | 0.3973 |
| 2023-24 / Overall | 95 | 1.0000 | 0.9500 | 0.0500 | 0.5342 |
| 2024-25 / 0-4 yr | 80 | 0.5714 | 0.8000 | -0.2286 | 0.9081 |
| 2024-25 / 0-4 yr | 95 | 0.5714 | 0.9500 | -0.3786 | 1.1105 |
| 2024-25 / >= 65 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 3.0939 |
| 2024-25 / >= 65 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 4.6619 |
| 2024-25 / Overall | 80 | 0.8571 | 0.8000 | 0.0571 | 1.5740 |
| 2024-25 / Overall | 95 | 1.0000 | 0.9500 | 0.0500 | 2.1664 |

## Interpretation

- `deterministic_seir` remains the strongest default baseline for the overall series and several adult groups.
- `constrained_structure_discovery` is already useful in selected age groups, especially when simpler discovered structures outperform larger hand-specified models.
- `probabilistic_seir` is best interpreted as a stability and uncertainty baseline rather than the primary point-forecast winner.
- The next research step is to strengthen stability-aware selection across multiple validation splits rather than further increasing raw structural flexibility.
