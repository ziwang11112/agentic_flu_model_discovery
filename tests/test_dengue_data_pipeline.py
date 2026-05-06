from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data.dengue import build_dengue_processed_series, load_dengue_surveillance_data, save_dengue_processed_outputs


def test_load_dengue_surveillance_data_normalizes_weekly_schema(tmp_path: Path) -> None:
    csv_path = tmp_path / "dengue.csv"
    pd.DataFrame(
        {
            "city": ["B", "A", "A", "A"],
            "year": [2024, 2024, 2024, 2024],
            "week": [1, 2, 1, 3],
            "cases": [5, 2, 1, 3],
        }
    ).to_csv(csv_path, index=False)

    frame = load_dengue_surveillance_data(csv_path, series_column="city", value_column="cases")

    assert frame["series_name"].tolist() == ["A", "A", "A", "B"]
    assert frame.loc[frame["series_name"] == "A", "t"].tolist() == [0, 1, 2]
    assert frame.loc[frame["series_name"] == "A", "observed_value"].tolist() == [1.0, 2.0, 3.0]


def test_load_dengue_surveillance_data_can_infer_iso_week_from_date(tmp_path: Path) -> None:
    csv_path = tmp_path / "dengue.csv"
    pd.DataFrame(
        {
            "location": ["Metro", "Metro"],
            "week_start": ["2024-01-01", "2024-01-08"],
            "incidence": [0.4, 0.7],
        }
    ).to_csv(csv_path, index=False)

    frame = load_dengue_surveillance_data(csv_path)

    assert frame["YEAR"].tolist() == [2024, 2024]
    assert frame["WEEK"].tolist() == [1, 2]
    assert frame["observed_value"].tolist() == [0.4, 0.7]


def test_build_dengue_processed_series_filters_selection_and_min_length(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "series_name": ["A", "A", "A", "B"],
            "YEAR": [2024, 2024, 2024, 2024],
            "WEEK": [1, 2, 3, 1],
            "t": [0, 1, 2, 0],
            "observed_value": [1.0, 2.0, 3.0, 9.0],
            "target": ["weekly dengue count or incidence"] * 4,
        }
    )

    processed = build_dengue_processed_series(frame, selected_series=["A", "B"], min_observations=2)

    assert processed["series_name"].unique().tolist() == ["A"]
    assert processed["t"].tolist() == [0, 1, 2]


def test_load_dengue_surveillance_data_rejects_negative_values(tmp_path: Path) -> None:
    csv_path = tmp_path / "dengue.csv"
    pd.DataFrame({"year": [2024], "week": [1], "cases": [-1]}).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="non-negative"):
        load_dengue_surveillance_data(csv_path)


def test_save_dengue_processed_outputs_writes_expected_csv(tmp_path: Path) -> None:
    processed = pd.DataFrame(
        {
            "series_name": ["A"],
            "YEAR": [2024],
            "WEEK": [1],
            "t": [0],
            "observed_value": [1.0],
            "target": ["weekly dengue count or incidence"],
        }
    )

    save_dengue_processed_outputs(processed, tmp_path)

    assert (tmp_path / "dengue_benchmark_series.csv").exists()
