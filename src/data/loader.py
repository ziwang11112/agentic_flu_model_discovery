from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

PRIMARY_FILTERS = {
    "CATCHMENT": "Entire Network",
    "AGE CATEGORY": "Overall",
    "SEX CATEGORY": "Overall",
    "RACE CATEGORY": "Overall",
    "VIRUS TYPE CATEGORY": "Overall",
}

ROBUSTNESS_AGE_GROUPS = ["0-4 yr", "5-17 yr", "18-49 yr", "50-64 yr", ">= 65 yr"]


def load_flu_surv_data(csv_path: str | Path) -> pd.DataFrame:
    """Load the FluSurv-NET export and normalize its weekly index."""
    frame = pd.read_csv(csv_path, skiprows=2)
    frame.columns = [column.strip() for column in frame.columns]
    frame = frame.dropna(subset=["WEEK", "YEAR.1"]).copy()

    numeric_columns = ["WEEK", "YEAR.1", "WEEKLY RATE", "CUMULATIVE RATE"]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=["WEEK", "YEAR.1", "WEEKLY RATE"]).copy()
    frame["WEEK"] = frame["WEEK"].astype(int)
    frame["YEAR.1"] = frame["YEAR.1"].astype(int)
    frame = frame.sort_values(["YEAR.1", "WEEK"], kind="mergesort").reset_index(drop=True)
    frame["t"] = range(len(frame))
    return frame


def filter_series(
    frame: pd.DataFrame,
    age_category: str = "Overall",
    catchment: str = "Entire Network",
    sex_category: str = "Overall",
    race_category: str = "Overall",
    virus_category: str = "Overall",
) -> pd.DataFrame:
    """Filter to one benchmark series and rebuild a continuous weekly index."""
    mask = (
        (frame["CATCHMENT"] == catchment)
        & (frame["AGE CATEGORY"] == age_category)
        & (frame["SEX CATEGORY"] == sex_category)
        & (frame["RACE CATEGORY"] == race_category)
        & (frame["VIRUS TYPE CATEGORY"] == virus_category)
    )
    series = frame.loc[mask].copy()
    series = series.dropna(subset=["WEEKLY RATE"]).copy()
    series = series.sort_values(["YEAR.1", "WEEK"], kind="mergesort").reset_index(drop=True)
    series["t"] = range(len(series))
    series["series_name"] = age_category
    return series


def build_processed_series(
    frame: pd.DataFrame,
    include_age_groups: bool,
    age_groups: Iterable[str],
) -> pd.DataFrame:
    """Build the primary series and optional robustness slices in one table."""
    series_frames = [filter_series(frame, age_category="Overall")]
    if include_age_groups:
        for age_group in age_groups:
            series_frames.append(filter_series(frame, age_category=age_group))

    combined = pd.concat(series_frames, ignore_index=True)
    columns = [
        "series_name",
        "YEAR",
        "YEAR.1",
        "WEEK",
        "t",
        "CATCHMENT",
        "AGE CATEGORY",
        "SEX CATEGORY",
        "RACE CATEGORY",
        "VIRUS TYPE CATEGORY",
        "WEEKLY RATE",
        "CUMULATIVE RATE",
    ]
    return combined.loc[:, columns]


def save_processed_outputs(
    processed: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Persist the benchmark-ready processed tables."""
    output_dir.mkdir(parents=True, exist_ok=True)
    processed.to_csv(output_dir / "flusurv_benchmark_series.csv", index=False)
    overall = processed.loc[processed["series_name"] == "Overall"].copy()
    overall.to_csv(output_dir / "flusurv_primary_overall.csv", index=False)
