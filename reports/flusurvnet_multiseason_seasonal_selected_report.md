# FluSurv-NET Multi-Season Seasonal Benchmark

This benchmark evaluates each completed FluSurv-NET season as its own within-season trajectory.
It is intended as a cross-season robustness supplement, not as a direct previous-season-to-future-season transfer forecast.

Artifact root: `D:\Projects\agentic_flu_model_discovery\artifacts_flusurvnet_multiseason_seasonal_selected`
Completed seasons included: 2018-19, 2019-20, 2021-22, 2022-23, 2023-24, 2024-25
Models: deterministic_seir, probabilistic_seir, hospitalized_seihr, delayed_observation_seir, fractional_seir, constrained_structure_discovery

## Age-Group Recommendation Modes

| age_group | num_seasons | recommended_model_mode | recommended_model_frequency | best_test_model_mode | best_test_model_frequency | best_rolling_model_mode | best_rolling_model_frequency |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | 6 | constrained_structure_discovery | 0.8333 | constrained_structure_discovery | 0.6667 | constrained_structure_discovery | 0.8333 |
| >= 65 yr | 6 | deterministic_seir | 0.3333 | constrained_structure_discovery | 0.3333 | delayed_observation_seir | 0.3333 |
| Overall | 6 | constrained_structure_discovery | 0.6667 | constrained_structure_discovery | 0.3333 | constrained_structure_discovery | 0.8333 |

## Season-Level Recommendations

| series_name | season | age_group | recommended_model | decision_type | best_test_model | best_rolling_model |
| --- | --- | --- | --- | --- | --- | --- |
| 2018-19 / 0-4 yr | 2018-19 | 0-4 yr | constrained_structure_discovery | stability_preferred | fractional_seir | constrained_structure_discovery |
| 2018-19 / >= 65 yr | 2018-19 | >= 65 yr | delayed_observation_seir | stability_preferred | deterministic_seir | delayed_observation_seir |
| 2018-19 / Overall | 2018-19 | Overall | delayed_observation_seir | test_preferred | delayed_observation_seir | constrained_structure_discovery |
| 2019-20 / 0-4 yr | 2019-20 | 0-4 yr | deterministic_seir | balanced_tradeoff | probabilistic_seir | constrained_structure_discovery |
| 2019-20 / >= 65 yr | 2019-20 | >= 65 yr | deterministic_seir | stability_preferred | hospitalized_seihr | deterministic_seir |
| 2019-20 / Overall | 2019-20 | Overall | constrained_structure_discovery | stability_preferred | probabilistic_seir | constrained_structure_discovery |
| 2021-22 / 0-4 yr | 2021-22 | 0-4 yr | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2021-22 / >= 65 yr | 2021-22 | >= 65 yr | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2021-22 / Overall | 2021-22 | Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2022-23 / 0-4 yr | 2022-23 | 0-4 yr | constrained_structure_discovery | test_preferred | constrained_structure_discovery | fractional_seir |
| 2022-23 / >= 65 yr | 2022-23 | >= 65 yr | deterministic_seir | stability_preferred | probabilistic_seir | deterministic_seir |
| 2022-23 / Overall | 2022-23 | Overall | constrained_structure_discovery | stability_preferred | fractional_seir | constrained_structure_discovery |
| 2023-24 / 0-4 yr | 2023-24 | 0-4 yr | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2023-24 / >= 65 yr | 2023-24 | >= 65 yr | constrained_structure_discovery | test_preferred | constrained_structure_discovery | delayed_observation_seir |
| 2023-24 / Overall | 2023-24 | Overall | deterministic_seir | consensus | deterministic_seir | deterministic_seir |
| 2024-25 / 0-4 yr | 2024-25 | 0-4 yr | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2024-25 / >= 65 yr | 2024-25 | >= 65 yr | hospitalized_seihr | balanced_tradeoff | probabilistic_seir | constrained_structure_discovery |
| 2024-25 / Overall | 2024-25 | Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
