from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.run_flusurvnet_multiseason_seasonal_benchmark import (
    _completed_seasons,
    _parse_series_name,
    build_seasonal_recommendation_summary,
)


def test_completed_seasons_filters_to_complete_status_and_optional_splits(tmp_path: Path) -> None:
    path = tmp_path / "recommended_completed_seasons.csv"
    pd.DataFrame(
        [
            {"season": "2018-19", "status": "complete", "recommended_split": "train"},
            {"season": "2019-20", "status": "complete", "recommended_split": "validation"},
            {"season": "2020-21", "status": "incomplete", "recommended_split": ""},
            {"season": "2021-22", "status": "complete", "recommended_split": "test"},
        ]
    ).to_csv(path, index=False)

    assert _completed_seasons(path) == ["2018-19", "2019-20", "2021-22"]
    assert _completed_seasons(path, splits=["validation", "test"]) == ["2019-20", "2021-22"]


def test_parse_series_name_splits_season_and_age_group() -> None:
    assert _parse_series_name("2023-24 / >= 65 yr") == ("2023-24", ">= 65 yr")
    assert _parse_series_name("Overall") == ("", "Overall")


def test_build_seasonal_recommendation_summary_counts_modes_by_age_group() -> None:
    recommendations = pd.DataFrame(
        [
            {
                "series_name": "2018-19 / Overall",
                "recommended_model": "deterministic_seir",
                "best_test_model": "deterministic_seir",
                "best_rolling_model": "delayed_observation_seir",
            },
            {
                "series_name": "2019-20 / Overall",
                "recommended_model": "deterministic_seir",
                "best_test_model": "fractional_seir",
                "best_rolling_model": "delayed_observation_seir",
            },
            {
                "series_name": "2018-19 / 0-4 yr",
                "recommended_model": "constrained_structure_discovery",
                "best_test_model": "constrained_structure_discovery",
                "best_rolling_model": "constrained_structure_discovery",
            },
        ]
    )

    summary = build_seasonal_recommendation_summary(recommendations)

    overall = summary.loc[summary["age_group"] == "Overall"].iloc[0]
    assert overall["num_seasons"] == 2
    assert overall["recommended_model_mode"] == "deterministic_seir"
    assert overall["recommended_model_frequency"] == 1.0
    assert overall["best_rolling_model_mode"] == "delayed_observation_seir"

    child = summary.loc[summary["age_group"] == "0-4 yr"].iloc[0]
    assert child["recommended_model_mode"] == "constrained_structure_discovery"
