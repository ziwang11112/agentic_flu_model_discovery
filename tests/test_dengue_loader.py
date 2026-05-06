from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.dengue_loader import (
    build_dengue_series_catalog,
    build_weekly_dengue_series,
    dengue_series_quality,
    load_dengue_national_csv,
)


def _write_national_csv(tmp_path: Path) -> Path:
    path = tmp_path / "National_extract_V1_3.csv"
    pd.DataFrame(
        [
            {
                "country": "Brazil",
                "T_res": "Month",
                "case_definition_standardised": "Total",
                "calendar_start_date": "2020-01-01",
                "dengue_total": 999,
            },
            {
                "country": "Brazil",
                "T_res": "Week",
                "case_definition_standardised": "Total",
                "calendar_start_date": "2020-01-06",
                "dengue_total": 0,
            },
            {
                "country": "Brazil",
                "T_res": "Week",
                "case_definition_standardised": "Total",
                "calendar_start_date": "2020-01-20",
                "dengue_total": 10,
            },
            {
                "country": "Brazil",
                "T_res": "Week",
                "case_definition_standardised": "Total",
                "calendar_start_date": "2020-01-20",
                "dengue_total": 5,
            },
            {
                "country": "Singapore",
                "T_res": "Week",
                "case_definition_standardised": "Confirmed",
                "calendar_start_date": "2020-01-06",
                "dengue_total": 2,
            },
            {
                "country": "Singapore",
                "T_res": "Week",
                "case_definition_standardised": "Confirmed",
                "calendar_start_date": "2020-01-13",
                "dengue_total": 3,
            },
        ]
    ).to_csv(path, index=False)
    return path


def test_load_dengue_national_csv_filters_weekly_rows_in_series_builder(tmp_path: Path) -> None:
    frame = load_dengue_national_csv(_write_national_csv(tmp_path))
    series = build_weekly_dengue_series(frame, "Brazil", min_weeks=2)

    assert frame["T_res"].value_counts().to_dict() == {"Week": 5, "Month": 1}
    assert series["calendar_start_date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2020-01-06",
        "2020-01-13",
        "2020-01-20",
    ]
    assert series["y_raw"].dropna().tolist() == [0.0, 15.0]


def test_build_weekly_dengue_series_builds_continuous_weekly_index(tmp_path: Path) -> None:
    frame = load_dengue_national_csv(_write_national_csv(tmp_path))
    series = build_weekly_dengue_series(frame, "Brazil", min_weeks=2)

    assert series["t"].tolist() == [0, 1, 2]
    assert series.loc[1, "calendar_start_date"].strftime("%Y-%m-%d") == "2020-01-13"


def test_build_weekly_dengue_series_preserves_missing_week_indicator(tmp_path: Path) -> None:
    frame = load_dengue_national_csv(_write_national_csv(tmp_path))
    series = build_weekly_dengue_series(frame, "Brazil", min_weeks=2)

    assert series["missing_week_indicator"].tolist() == [False, True, False]
    assert pd.isna(series.loc[1, "y_raw"])


def test_build_weekly_dengue_series_handles_total_and_confirmed_case_definitions(tmp_path: Path) -> None:
    frame = load_dengue_national_csv(_write_national_csv(tmp_path))
    total = build_weekly_dengue_series(frame, "Brazil", case_definition="Total", min_weeks=2)
    confirmed = build_weekly_dengue_series(frame, "Singapore", case_definition="Total", min_weeks=2)

    assert total["case_definition_standardised"].unique().tolist() == ["Total"]
    assert confirmed["case_definition_standardised"].unique().tolist() == ["Confirmed"]


def test_dengue_quality_metrics_include_zero_and_missing_week_fractions(tmp_path: Path) -> None:
    frame = load_dengue_national_csv(_write_national_csv(tmp_path))
    series = build_weekly_dengue_series(frame, "Brazil", min_weeks=2)
    quality = dengue_series_quality(series)
    catalog = build_dengue_series_catalog(frame, min_weeks=2)
    brazil_row = catalog.loc[
        (catalog["country"] == "Brazil") & (catalog["case_definition_standardised"] == "Total")
    ].iloc[0]

    assert quality["zero_fraction"] == 1 / 2
    assert quality["missing_week_fraction"] == 1 / 3
    assert brazil_row["zero_fraction"] == 1 / 2
    assert brazil_row["missing_week_fraction"] == 1 / 3
    assert brazil_row["duplicate_country_date_case_definition_rows"] == 1
