# FluSurv-NET Multi-Season Seasonal Benchmark

This benchmark evaluates each completed FluSurv-NET season as its own within-season trajectory.
It is intended as a cross-season robustness supplement, not as a direct previous-season-to-future-season transfer forecast.

Artifact root: `D:\Projects\agentic_flu_model_discovery\artifacts_flusurvnet_multiseason_seasonal_smoke`
Completed seasons included: 2018-19, 2019-20, 2021-22, 2022-23, 2023-24, 2024-25
Models: deterministic_seir, delayed_observation_seir, constrained_structure_discovery

## Age-Group Recommendation Modes

| age_group | num_seasons | recommended_model_mode | recommended_model_frequency | best_test_model_mode | best_test_model_frequency | best_rolling_model_mode | best_rolling_model_frequency |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Overall | 6 | constrained_structure_discovery | 0.6667 | constrained_structure_discovery | 0.6667 | constrained_structure_discovery | 1.0000 |

## Season-Level Recommendations

| series_name | season | age_group | recommended_model | decision_type | best_test_model | best_rolling_model |
| --- | --- | --- | --- | --- | --- | --- |
| 2018-19 / Overall | 2018-19 | Overall | delayed_observation_seir | test_preferred | delayed_observation_seir | constrained_structure_discovery |
| 2019-20 / Overall | 2019-20 | Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2021-22 / Overall | 2021-22 | Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2022-23 / Overall | 2022-23 | Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
| 2023-24 / Overall | 2023-24 | Overall | deterministic_seir | test_preferred | deterministic_seir | constrained_structure_discovery |
| 2024-25 / Overall | 2024-25 | Overall | constrained_structure_discovery | consensus | constrained_structure_discovery | constrained_structure_discovery |
