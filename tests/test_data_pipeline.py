from __future__ import annotations

from pathlib import Path

from src.data.loader import filter_series, load_flu_surv_data


CSV_TEXT = """metadata line 1
metadata line 2
CATCHMENT,NETWORK,YEAR,YEAR,WEEK,AGE CATEGORY,SEX CATEGORY,RACE CATEGORY,VIRUS TYPE CATEGORY,CUMULATIVE RATE,WEEKLY RATE,AGE ADJUSTED CUMULATIVE RATE,AGE ADJUSTED WEEKLY RATE, LOWER, MEDIAN, UPPER
Entire Network,FluSurv-NET,2023-24,2024,2,Overall,Overall,Overall,Overall,1.2,0.8,1.2,0.8,null,null,null
Entire Network,FluSurv-NET,2023-24,2023,40,Overall,Overall,Overall,Overall,0.2,0.2,0.2,0.2,null,null,null
Entire Network,FluSurv-NET,2023-24,2023,41,0-4 yr,Overall,Overall,Overall,0.4,0.2,0.4,0.2,null,null,null
Entire Network,FluSurv-NET,2023-24,2023,41,Overall,Male,Overall,Overall,0.4,0.2,0.4,0.2,null,null,null
Disclaimer row,,,,,,,,,,,,,,,
"""


def test_load_flu_surv_data_drops_footer_and_sorts(tmp_path: Path) -> None:
    csv_path = tmp_path / "flu.csv"
    csv_path.write_text(CSV_TEXT, encoding="utf-8")

    frame = load_flu_surv_data(csv_path)

    assert frame["YEAR.1"].tolist() == [2023, 2023, 2023, 2024]
    assert frame["WEEK"].tolist() == [40, 41, 41, 2]
    assert frame["t"].tolist() == [0, 1, 2, 3]


def test_filter_series_applies_primary_overall_filters(tmp_path: Path) -> None:
    csv_path = tmp_path / "flu.csv"
    csv_path.write_text(CSV_TEXT, encoding="utf-8")

    frame = load_flu_surv_data(csv_path)
    overall = filter_series(frame, age_category="Overall")
    age_group = filter_series(frame, age_category="0-4 yr")

    assert overall["WEEKLY RATE"].tolist() == [0.2, 0.8]
    assert overall["SEX CATEGORY"].tolist() == ["Overall", "Overall"]
    assert age_group["WEEKLY RATE"].tolist() == [0.2]
    assert age_group["AGE CATEGORY"].tolist() == ["0-4 yr"]
