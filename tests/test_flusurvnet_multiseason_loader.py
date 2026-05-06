from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data.flusurvnet_multiseason_loader import (
    SEASON_CATALOG_COLUMNS,
    build_flusurvnet_season_series,
    build_flusurvnet_season_series_catalog,
    load_flusurvnet_multiseason_csv,
)


CSV_TEXT = """FluSurv-NET custom export
Downloaded metadata line
CATCHMENT,NETWORK,YEAR,YEAR,WEEK,AGE CATEGORY,SEX CATEGORY,RACE CATEGORY,VIRUS TYPE CATEGORY,CUMULATIVE RATE,WEEKLY RATE,AGE ADJUSTED CUMULATIVE RATE,AGE ADJUSTED WEEKLY RATE
Entire Network,FluSurv-NET,2022-23,2022,40,Overall,Overall,Overall,Overall,0.10,0.10,0.10,0.10
Entire Network,FluSurv-NET,2022-23,2022,42,Overall,Overall,Overall,Overall,0.30,0.20,0.30,0.20
Other Catchment,FluSurv-NET,2022-23,2022,41,Overall,Overall,Overall,Overall,9.00,9.00,9.00,9.00
Entire Network,FluSurv-NET,2022-23,2022,41,Overall,Male,Overall,Overall,8.00,8.00,8.00,8.00
Entire Network,FluSurv-NET,2022-23,2022,41,Overall,Overall,Overall,A,7.00,7.00,7.00,7.00
Entire Network,FluSurv-NET,2022-23,2022,40,0-4 yr,Overall,Overall,Overall,0.20,0.20,0.20,0.20
Entire Network,FluSurv-NET,2022-23,2022,42,0-4 yr,Overall,Overall,Overall,0.50,0.30,0.50,0.30
Disclaimer row,,,,,,,,,,,,
"""


def _write_csv(tmp_path: Path, text: str = CSV_TEXT) -> Path:
    csv_path = tmp_path / "flusurvnet_multiseason.csv"
    csv_path.write_text(text, encoding="utf-8")
    return csv_path


def test_loader_handles_metadata_prefixed_csv(tmp_path: Path) -> None:
    frame = load_flusurvnet_multiseason_csv(_write_csv(tmp_path))

    assert "YEAR.1" in frame.columns
    assert frame["season"].unique().tolist() == ["2022-23"]
    assert frame["year_label"].tolist() == [2022, 2022, 2022, 2022, 2022, 2022, 2022]
    assert "Disclaimer row" not in frame["CATCHMENT"].astype(str).tolist()


def test_series_applies_entire_network_overall_filters(tmp_path: Path) -> None:
    frame = load_flusurvnet_multiseason_csv(_write_csv(tmp_path))
    series = build_flusurvnet_season_series(frame, season="2022-23", age_group="Overall")

    assert series["y"].dropna().tolist() == [0.10, 0.20]
    assert 7.00 not in series["y"].dropna().tolist()
    assert 8.00 not in series["y"].dropna().tolist()
    assert 9.00 not in series["y"].dropna().tolist()


def test_series_creates_t_index_and_explicit_missing_weeks(tmp_path: Path) -> None:
    frame = load_flusurvnet_multiseason_csv(_write_csv(tmp_path))
    series = build_flusurvnet_season_series(frame, season="2022-23", age_group="Overall")

    assert series["week"].tolist() == [40, 41, 42]
    assert series["t"].tolist() == [0, 1, 2]
    assert series["missing_week_flag"].tolist() == [False, True, False]
    assert series["original_row_count"].tolist() == [1, 0, 1]
    assert pd.isna(series.loc[series["week"] == 41, "y"].iloc[0])


def test_series_rejects_duplicate_rows_unless_aggregated_beforehand(tmp_path: Path) -> None:
    duplicate_text = CSV_TEXT.replace(
        "Entire Network,FluSurv-NET,2022-23,2022,42,Overall,Overall,Overall,Overall,0.30,0.20,0.30,0.20",
        "\n".join(
            [
                "Entire Network,FluSurv-NET,2022-23,2022,42,Overall,Overall,Overall,Overall,0.30,0.20,0.30,0.20",
                "Entire Network,FluSurv-NET,2022-23,2022,42,Overall,Overall,Overall,Overall,0.31,0.21,0.31,0.21",
            ]
        ),
    )
    frame = load_flusurvnet_multiseason_csv(_write_csv(tmp_path, duplicate_text))

    with pytest.raises(ValueError, match="Duplicate FluSurv-NET rows"):
        build_flusurvnet_season_series(frame, season="2022-23", age_group="Overall")


def test_catalog_contains_expected_columns_and_missing_week_counts(tmp_path: Path) -> None:
    frame = load_flusurvnet_multiseason_csv(_write_csv(tmp_path))
    catalog = build_flusurvnet_season_series_catalog(frame, age_groups=["Overall", "0-4 yr"])

    assert set(SEASON_CATALOG_COLUMNS).issubset(catalog.columns)

    overall = catalog.loc[(catalog["season"] == "2022-23") & (catalog["age_group"] == "Overall")].iloc[0]
    child = catalog.loc[(catalog["season"] == "2022-23") & (catalog["age_group"] == "0-4 yr")].iloc[0]

    assert overall["missing_week_count"] == 1
    assert overall["missing_weeks"] == "2022-W41"
    assert child["observed_week_count"] == 2
