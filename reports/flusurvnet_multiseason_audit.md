# FluSurv-NET Multi-Season Audit

Input CSV: `D:\Projects\agentic_flu_model_discovery\data\raw\flusurvnet_multiseason_full.csv`
Total normalized rows: 9884
Available seasons: 2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26

## Main Benchmark Filters

The audit applies these filters for season-age coverage checks:

- `CATCHMENT == Entire Network`
- `SEX CATEGORY == Overall`
- `RACE CATEGORY == Overall`
- `VIRUS TYPE CATEGORY == Overall`
- `AGE CATEGORY in ['Overall', '0-4 yr', '5-17 yr', '18-49 yr', '50-64 yr', '>= 65 yr']`
- target column: `WEEKLY RATE`

## Category Coverage

Age categories available: 0-4 yr, 0-<1 yr, 1-4 yr, 12-17 yr, 18-29 yr, 18-49 yr, 30-39 yr, 40-49 yr, 5-11 yr, 5-17 yr, 50-64 yr, 65-74 yr, 75-84 yr, >= 65 yr, >= 75, >= 85, Adults, Overall, Pediatrics
Virus type categories: Overall
Sex categories: Female, Male, Overall
Race categories: American Indian/Alaska Native, NH, Asian/Pacific Islander, NH, Black, NH, Hispanic, Overall, White, NH
Catchment categories: California, Colorado, Connecticut, Entire Network, Georgia, Iowa, Maryland, Michigan, Minnesota, New Mexico, New York, North Carolina, Ohio, Oregon, Tennessee, Utah, Washington

## Season Coverage

| season | status | has_all_required_age_groups | observed_week_count_min | observed_week_count_max | min_year_label | min_week | max_year_label | max_week | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2018-19 | complete | True | 31 | 31 | 2018 | 40 | 2019 | 18 | passes required age, missing-week, duplicate, and preliminary checks |
| 2019-20 | complete | True | 31 | 31 | 2019 | 40 | 2020 | 18 | passes required age, missing-week, duplicate, and preliminary checks |
| 2020-21 | incomplete | False | 31 | 31 | 2020 | 40 | 2021 | 17 | missing required age groups: 0-4 yr, 5-17 yr, 18-49 yr, 50-64 yr, >= 65 yr |
| 2021-22 | complete | True | 36 | 36 | 2021 | 40 | 2022 | 23 | passes required age, missing-week, duplicate, and preliminary checks |
| 2022-23 | complete | True | 31 | 31 | 2022 | 40 | 2023 | 18 | passes required age, missing-week, duplicate, and preliminary checks |
| 2023-24 | complete | True | 52 | 52 | 2023 | 40 | 2024 | 39 | passes required age, missing-week, duplicate, and preliminary checks |
| 2024-25 | complete | True | 31 | 31 | 2024 | 40 | 2025 | 18 | passes required age, missing-week, duplicate, and preliminary checks |
| 2025-26 | preliminary | True | 32 | 32 | 2025 | 40 | 2026 | 18 | current surveillance season; treat as preliminary |

## Weeks Per Season And Age Group

Catalog written to `D:\Projects\agentic_flu_model_discovery\data\processed_flusurvnet_multiseason\season_series_catalog.csv`.

| season | age_group | observed_week_count | expected_week_count | missing_week_count | duplicate_row_count | min_year_label | min_week | max_year_label | max_week |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2018-19 | Overall | 31 | 31 | 0 | 0 | 2018 | 40 | 2019 | 18 |
| 2018-19 | 0-4 yr | 31 | 31 | 0 | 0 | 2018 | 40 | 2019 | 18 |
| 2018-19 | 5-17 yr | 31 | 31 | 0 | 0 | 2018 | 40 | 2019 | 18 |
| 2018-19 | 18-49 yr | 31 | 31 | 0 | 0 | 2018 | 40 | 2019 | 18 |
| 2018-19 | 50-64 yr | 31 | 31 | 0 | 0 | 2018 | 40 | 2019 | 18 |
| 2018-19 | >= 65 yr | 31 | 31 | 0 | 0 | 2018 | 40 | 2019 | 18 |
| 2019-20 | Overall | 31 | 31 | 0 | 0 | 2019 | 40 | 2020 | 18 |
| 2019-20 | 0-4 yr | 31 | 31 | 0 | 0 | 2019 | 40 | 2020 | 18 |
| 2019-20 | 5-17 yr | 31 | 31 | 0 | 0 | 2019 | 40 | 2020 | 18 |
| 2019-20 | 18-49 yr | 31 | 31 | 0 | 0 | 2019 | 40 | 2020 | 18 |
| 2019-20 | 50-64 yr | 31 | 31 | 0 | 0 | 2019 | 40 | 2020 | 18 |
| 2019-20 | >= 65 yr | 31 | 31 | 0 | 0 | 2019 | 40 | 2020 | 18 |
| 2020-21 | Overall | 31 | 31 | 0 | 0 | 2020 | 40 | 2021 | 17 |
| 2020-21 | 0-4 yr | 0 | 0 | 0 | 0 |  |  |  |  |
| 2020-21 | 5-17 yr | 0 | 0 | 0 | 0 |  |  |  |  |
| 2020-21 | 18-49 yr | 0 | 0 | 0 | 0 |  |  |  |  |
| 2020-21 | 50-64 yr | 0 | 0 | 0 | 0 |  |  |  |  |
| 2020-21 | >= 65 yr | 0 | 0 | 0 | 0 |  |  |  |  |
| 2021-22 | Overall | 36 | 36 | 0 | 0 | 2021 | 40 | 2022 | 23 |
| 2021-22 | 0-4 yr | 36 | 36 | 0 | 0 | 2021 | 40 | 2022 | 23 |
| 2021-22 | 5-17 yr | 36 | 36 | 0 | 0 | 2021 | 40 | 2022 | 23 |
| 2021-22 | 18-49 yr | 36 | 36 | 0 | 0 | 2021 | 40 | 2022 | 23 |
| 2021-22 | 50-64 yr | 36 | 36 | 0 | 0 | 2021 | 40 | 2022 | 23 |
| 2021-22 | >= 65 yr | 36 | 36 | 0 | 0 | 2021 | 40 | 2022 | 23 |
| 2022-23 | Overall | 31 | 31 | 0 | 0 | 2022 | 40 | 2023 | 18 |
| 2022-23 | 0-4 yr | 31 | 31 | 0 | 0 | 2022 | 40 | 2023 | 18 |
| 2022-23 | 5-17 yr | 31 | 31 | 0 | 0 | 2022 | 40 | 2023 | 18 |
| 2022-23 | 18-49 yr | 31 | 31 | 0 | 0 | 2022 | 40 | 2023 | 18 |
| 2022-23 | 50-64 yr | 31 | 31 | 0 | 0 | 2022 | 40 | 2023 | 18 |
| 2022-23 | >= 65 yr | 31 | 31 | 0 | 0 | 2022 | 40 | 2023 | 18 |
| 2023-24 | Overall | 52 | 52 | 0 | 0 | 2023 | 40 | 2024 | 39 |
| 2023-24 | 0-4 yr | 52 | 52 | 0 | 0 | 2023 | 40 | 2024 | 39 |
| 2023-24 | 5-17 yr | 52 | 52 | 0 | 0 | 2023 | 40 | 2024 | 39 |
| 2023-24 | 18-49 yr | 52 | 52 | 0 | 0 | 2023 | 40 | 2024 | 39 |
| 2023-24 | 50-64 yr | 52 | 52 | 0 | 0 | 2023 | 40 | 2024 | 39 |
| 2023-24 | >= 65 yr | 52 | 52 | 0 | 0 | 2023 | 40 | 2024 | 39 |
| 2024-25 | Overall | 31 | 31 | 0 | 0 | 2024 | 40 | 2025 | 18 |
| 2024-25 | 0-4 yr | 31 | 31 | 0 | 0 | 2024 | 40 | 2025 | 18 |
| 2024-25 | 5-17 yr | 31 | 31 | 0 | 0 | 2024 | 40 | 2025 | 18 |
| 2024-25 | 18-49 yr | 31 | 31 | 0 | 0 | 2024 | 40 | 2025 | 18 |
| 2024-25 | 50-64 yr | 31 | 31 | 0 | 0 | 2024 | 40 | 2025 | 18 |
| 2024-25 | >= 65 yr | 31 | 31 | 0 | 0 | 2024 | 40 | 2025 | 18 |
| 2025-26 | Overall | 32 | 32 | 0 | 0 | 2025 | 40 | 2026 | 18 |
| 2025-26 | 0-4 yr | 32 | 32 | 0 | 0 | 2025 | 40 | 2026 | 18 |
| 2025-26 | 5-17 yr | 32 | 32 | 0 | 0 | 2025 | 40 | 2026 | 18 |
| 2025-26 | 18-49 yr | 32 | 32 | 0 | 0 | 2025 | 40 | 2026 | 18 |
| 2025-26 | 50-64 yr | 32 | 32 | 0 | 0 | 2025 | 40 | 2026 | 18 |
| 2025-26 | >= 65 yr | 32 | 32 | 0 | 0 | 2025 | 40 | 2026 | 18 |

## Missing Weeks

_None._

## Duplicate Season/Week/Age Rows

_None._

## Completed vs Incomplete Seasons

Appears complete:

| season | observed_week_count_min | observed_week_count_max |
| --- | --- | --- |
| 2018-19 | 31 | 31 |
| 2019-20 | 31 | 31 |
| 2021-22 | 36 | 36 |
| 2022-23 | 31 | 31 |
| 2023-24 | 52 | 52 |
| 2024-25 | 31 | 31 |

Incomplete or preliminary:

| season | status | reason |
| --- | --- | --- |
| 2020-21 | incomplete | missing required age groups: 0-4 yr, 5-17 yr, 18-49 yr, 50-64 yr, >= 65 yr |
| 2025-26 | preliminary | current surveillance season; treat as preliminary |

## Recommended Split

Completed-season recommendations written to `D:\Projects\agentic_flu_model_discovery\data\processed_flusurvnet_multiseason\recommended_completed_seasons.csv`.

| season | recommended_split | reason |
| --- | --- | --- |
| 2018-19 | train | passes required age, missing-week, duplicate, and preliminary checks |
| 2019-20 | train | passes required age, missing-week, duplicate, and preliminary checks |
| 2021-22 | train | passes required age, missing-week, duplicate, and preliminary checks |
| 2022-23 | train | passes required age, missing-week, duplicate, and preliminary checks |
| 2023-24 | validation | passes required age, missing-week, duplicate, and preliminary checks |
| 2024-25 | test | passes required age, missing-week, duplicate, and preliminary checks |

Use the latest completed season as the main test season, the prior completed season as validation when available, and older completed seasons for training. Preliminary current-season data should be kept out of the main benchmark unless the experiment is explicitly labeled preliminary.
