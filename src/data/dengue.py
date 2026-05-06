from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


VALUE_COLUMN_CANDIDATES = ("cases", "case_count", "weekly_cases", "incidence", "rate", "value")
SERIES_COLUMN_CANDIDATES = ("series_name", "location", "site", "city", "region", "state")
YEAR_COLUMN_CANDIDATES = ("year", "epi_year", "calendar_year", "YEAR")
WEEK_COLUMN_CANDIDATES = ("week", "epi_week", "mmwr_week", "WEEK")
DATE_COLUMN_CANDIDATES = ("date", "week_start", "week_ending", "report_date")


def _column_lookup(frame: pd.DataFrame) -> dict[str, str]:
    return {column.strip().lower(): column for column in frame.columns}


def _resolve_column(
    frame: pd.DataFrame,
    configured: str | None,
    candidates: Iterable[str],
    role: str,
    required: bool = True,
) -> str | None:
    lookup = _column_lookup(frame)
    if configured:
        key = configured.strip().lower()
        if key not in lookup:
            raise ValueError(f"Configured dengue {role} column is missing: {configured}")
        return lookup[key]
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in lookup:
            return lookup[key]
    if required:
        raise ValueError(f"Could not infer dengue {role} column from candidates: {', '.join(candidates)}")
    return None


def load_dengue_surveillance_data(
    csv_path: str | Path,
    *,
    series_column: str | None = None,
    value_column: str | None = None,
    year_column: str | None = None,
    week_column: str | None = None,
    date_column: str | None = None,
    default_series_name: str = "Dengue",
) -> pd.DataFrame:
    """Load a tidy dengue weekly surveillance table into the benchmark schema."""
    frame = pd.read_csv(csv_path)
    frame.columns = [column.strip() for column in frame.columns]

    resolved_value = _resolve_column(frame, value_column, VALUE_COLUMN_CANDIDATES, "value")
    resolved_series = _resolve_column(frame, series_column, SERIES_COLUMN_CANDIDATES, "series", required=False)
    resolved_year = _resolve_column(frame, year_column, YEAR_COLUMN_CANDIDATES, "year", required=False)
    resolved_week = _resolve_column(frame, week_column, WEEK_COLUMN_CANDIDATES, "week", required=False)
    resolved_date = _resolve_column(frame, date_column, DATE_COLUMN_CANDIDATES, "date", required=False)

    normalized = pd.DataFrame(index=frame.index)
    normalized["series_name"] = (
        frame[resolved_series].astype(str).str.strip() if resolved_series is not None else default_series_name
    )
    normalized["observed_value"] = pd.to_numeric(frame[resolved_value], errors="coerce")

    if resolved_year is not None and resolved_week is not None:
        normalized["YEAR"] = pd.to_numeric(frame[resolved_year], errors="coerce")
        normalized["WEEK"] = pd.to_numeric(frame[resolved_week], errors="coerce")
    elif resolved_date is not None:
        parsed_dates = pd.to_datetime(frame[resolved_date], errors="coerce")
        iso = parsed_dates.dt.isocalendar()
        normalized["YEAR"] = iso["year"].astype("Float64")
        normalized["WEEK"] = iso["week"].astype("Float64")
    else:
        raise ValueError("Dengue data must include either year/week columns or a date column.")

    normalized = normalized.dropna(subset=["series_name", "observed_value", "YEAR", "WEEK"]).copy()
    normalized["observed_value"] = normalized["observed_value"].astype(float)
    if (normalized["observed_value"] < 0).any():
        raise ValueError("Dengue observed values must be non-negative.")
    normalized["YEAR"] = normalized["YEAR"].astype(int)
    normalized["WEEK"] = normalized["WEEK"].astype(int)
    normalized["target"] = "weekly dengue count or incidence"
    normalized = normalized.sort_values(["series_name", "YEAR", "WEEK"], kind="mergesort").reset_index(drop=True)
    normalized["t"] = normalized.groupby("series_name").cumcount()
    return normalized.loc[:, ["series_name", "YEAR", "WEEK", "t", "observed_value", "target"]]


def build_dengue_processed_series(
    frame: pd.DataFrame,
    *,
    selected_series: Iterable[str] | None = None,
    min_observations: int = 12,
) -> pd.DataFrame:
    """Filter dengue series for a smoke benchmark and preserve a continuous index."""
    processed = frame.copy()
    selected = {str(value) for value in selected_series or []}
    if selected:
        processed = processed.loc[processed["series_name"].astype(str).isin(selected)].copy()
    counts = processed.groupby("series_name")["observed_value"].transform("count")
    processed = processed.loc[counts >= int(min_observations)].copy()
    processed = processed.sort_values(["series_name", "YEAR", "WEEK"], kind="mergesort").reset_index(drop=True)
    processed["t"] = processed.groupby("series_name").cumcount()
    return processed


def save_dengue_processed_outputs(processed: pd.DataFrame, output_dir: Path) -> None:
    """Persist benchmark-ready dengue tables."""
    output_dir.mkdir(parents=True, exist_ok=True)
    processed.to_csv(output_dir / "dengue_benchmark_series.csv", index=False)
