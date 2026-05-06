from __future__ import annotations

from pathlib import Path

from src.data.loader import build_processed_series, filter_series, load_flu_surv_data, resolve_data_path


CSV_TEXT = """metadata line 1
metadata line 2
CATCHMENT,NETWORK,YEAR,YEAR,WEEK,AGE CATEGORY,SEX CATEGORY,RACE CATEGORY,VIRUS TYPE CATEGORY,CUMULATIVE RATE,WEEKLY RATE,AGE ADJUSTED CUMULATIVE RATE,AGE ADJUSTED WEEKLY RATE, LOWER, MEDIAN, UPPER
Entire Network,FluSurv-NET,2023-24,2024,2,Overall,Overall,Overall,Overall,1.2,0.8,1.2,0.8,null,null,null
Entire Network,FluSurv-NET,2023-24,2023,40,Overall,Overall,Overall,Overall,0.2,0.2,0.2,0.2,null,null,null
Entire Network,FluSurv-NET,2023-24,2023,41,0-4 yr,Overall,Overall,Overall,0.4,0.2,0.4,0.2,null,null,null
Entire Network,FluSurv-NET,2023-24,2023,41,Overall,Male,Overall,Overall,0.4,0.2,0.4,0.2,null,null,null
Entire Network,FluSurv-NET,2024-25,2024,40,Overall,Overall,Overall,Overall,0.1,0.1,0.1,0.1,null,null,null
Entire Network,FluSurv-NET,2024-25,2024,41,0-4 yr,Overall,Overall,Overall,0.3,0.3,0.3,0.3,null,null,null
Disclaimer row,,,,,,,,,,,,,,,
"""


def test_load_flu_surv_data_drops_footer_and_sorts(tmp_path: Path) -> None:
    csv_path = tmp_path / "flu.csv"
    csv_path.write_text(CSV_TEXT, encoding="utf-8")

    frame = load_flu_surv_data(csv_path)

    assert frame["YEAR.1"].tolist() == [2023, 2023, 2023, 2024, 2024, 2024]
    assert frame["WEEK"].tolist() == [40, 41, 41, 2, 40, 41]
    assert frame["t"].tolist() == [0, 1, 2, 3, 4, 5]
    assert frame["season"].tolist() == ["2023-24", "2023-24", "2023-24", "2023-24", "2024-25", "2024-25"]


def test_filter_series_applies_primary_overall_filters(tmp_path: Path) -> None:
    csv_path = tmp_path / "flu.csv"
    csv_path.write_text(CSV_TEXT, encoding="utf-8")

    frame = load_flu_surv_data(csv_path)
    overall = filter_series(frame, age_category="Overall")
    age_group = filter_series(frame, age_category="0-4 yr")

    assert overall["WEEKLY RATE"].tolist() == [0.2, 0.8, 0.1]
    assert overall["SEX CATEGORY"].tolist() == ["Overall", "Overall", "Overall"]
    assert age_group["WEEKLY RATE"].tolist() == [0.2, 0.3]
    assert age_group["AGE CATEGORY"].tolist() == ["0-4 yr", "0-4 yr"]


def test_filter_series_can_select_specific_flu_seasons(tmp_path: Path) -> None:
    csv_path = tmp_path / "flu.csv"
    csv_path.write_text(CSV_TEXT, encoding="utf-8")

    frame = load_flu_surv_data(csv_path)
    overall = filter_series(frame, age_category="Overall", seasons=["2024-25"])

    assert overall["season"].tolist() == ["2024-25"]
    assert overall["WEEKLY RATE"].tolist() == [0.1]
    assert overall["t"].tolist() == [0]


def test_build_processed_series_can_keep_seasons_separate(tmp_path: Path) -> None:
    csv_path = tmp_path / "flu.csv"
    csv_path.write_text(CSV_TEXT, encoding="utf-8")

    frame = load_flu_surv_data(csv_path)
    processed = build_processed_series(
        frame,
        include_age_groups=True,
        age_groups=["0-4 yr"],
        season_mode="separate",
    )

    assert sorted(processed["series_name"].unique().tolist()) == [
        "2023-24 / 0-4 yr",
        "2023-24 / Overall",
        "2024-25 / 0-4 yr",
        "2024-25 / Overall",
    ]
    assert processed.loc[processed["series_name"] == "2024-25 / Overall", "t"].tolist() == [0]


def test_resolve_data_path_falls_back_to_data_raw(tmp_path: Path) -> None:
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    expected = raw_dir / "flu.csv"
    expected.write_text("x", encoding="utf-8")

    assert resolve_data_path(tmp_path, "flu.csv") == expected
