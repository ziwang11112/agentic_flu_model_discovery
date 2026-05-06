from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


FIRST_WAVE_DENGUE_SERIES = [
    {"country": "Nicaragua", "case_definition": "Total"},
    {"country": "Colombia", "case_definition": "Total"},
    {"country": "Brazil", "case_definition": "Total"},
    {"country": "Mexico", "case_definition": "Total"},
    {"country": "Sri Lanka", "case_definition": "Total"},
    {"country": "Taiwan", "case_definition": "Total"},
    {"country": "Malaysia", "case_definition": "Total"},
    {"country": "Singapore", "case_definition": "Confirmed"},
]

COUNTRY_COLUMN_CANDIDATES = ("country", "Country", "adm_0_name", "adm0_name", "location")
TEMPORAL_RESOLUTION_COLUMN_CANDIDATES = ("T_res", "t_res", "temporal_resolution")
CASE_DEFINITION_COLUMN_CANDIDATES = (
    "case_definition_standardised",
    "case_definition",
    "case_definition_standardized",
)
DATE_COLUMN_CANDIDATES = ("calendar_start_date", "start_date", "date", "week_start")
TARGET_COLUMN_CANDIDATES = ("dengue_total", "cases", "case_count", "value")

DENGUE_REQUIRED_CANONICAL_COLUMNS = [
    "country",
    "T_res",
    "case_definition_standardised",
    "calendar_start_date",
    "dengue_total",
]


@dataclass(frozen=True)
class DengueSeriesSpec:
    country: str
    case_definition: str = "Total"
    min_weeks: int = 156
    log1p_transform: bool = False


def _normalize_columns(columns: Iterable[object]) -> list[str]:
    return [str(column).replace("\ufeff", "").strip() for column in columns]


def _find_column(frame: pd.DataFrame, candidates: Iterable[str], role: str) -> str:
    lookup = {str(column).strip().lower(): column for column in frame.columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in lookup:
            return str(lookup[key])
    raise ValueError(f"Missing dengue {role} column; tried: {', '.join(candidates)}")


def _normalize_case_definition(value: object) -> str:
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    lowered = text.lower()
    if lowered == "total":
        return "Total"
    if lowered == "confirmed":
        return "Confirmed"
    return text


def _normalize_temporal_resolution(value: object) -> str:
    text = str(value).strip()
    if text.lower() in {"week", "weekly", "wk"}:
        return "Week"
    return text


def load_dengue_national_csv(path: str | Path) -> pd.DataFrame:
    """Load the national dengue extract and normalize columns used by the benchmark."""
    csv_path = Path(path)
    frame = pd.read_csv(csv_path)
    frame.columns = _normalize_columns(frame.columns)

    country_col = _find_column(frame, COUNTRY_COLUMN_CANDIDATES, "country")
    resolution_col = _find_column(frame, TEMPORAL_RESOLUTION_COLUMN_CANDIDATES, "temporal resolution")
    case_col = _find_column(frame, CASE_DEFINITION_COLUMN_CANDIDATES, "case definition")
    date_col = _find_column(frame, DATE_COLUMN_CANDIDATES, "calendar start date")
    target_col = _find_column(frame, TARGET_COLUMN_CANDIDATES, "target")

    normalized = frame.copy()
    normalized["country"] = frame[country_col].astype("string").str.strip()
    normalized["T_res"] = frame[resolution_col].map(_normalize_temporal_resolution)
    normalized["case_definition_standardised"] = frame[case_col].map(_normalize_case_definition)
    normalized["calendar_start_date"] = pd.to_datetime(frame[date_col], errors="coerce")
    normalized["dengue_total"] = pd.to_numeric(frame[target_col], errors="coerce")
    normalized = normalized.dropna(subset=["country", "T_res", "case_definition_standardised", "calendar_start_date"]).copy()
    normalized = normalized.sort_values(["country", "calendar_start_date"], kind="mergesort").reset_index(drop=True)
    return normalized


def _weekly_rows(df: pd.DataFrame, country: str) -> pd.DataFrame:
    required_missing = set(DENGUE_REQUIRED_CANONICAL_COLUMNS).difference(df.columns)
    if required_missing:
        raise ValueError(f"Dengue frame is missing normalized columns: {', '.join(sorted(required_missing))}")
    mask = (df["T_res"] == "Week") & (df["country"].astype(str) == country)
    return df.loc[mask].copy()


def _select_case_definition(weekly: pd.DataFrame, requested: str, country: str) -> str:
    available = set(weekly["case_definition_standardised"].dropna().astype(str))
    requested = _normalize_case_definition(requested)
    if requested in available:
        return requested
    if requested == "Total" and "Confirmed" in available:
        return "Confirmed"
    if country == "Singapore" and "Confirmed" in available:
        return "Confirmed"
    raise ValueError(
        f"No weekly dengue rows for country={country!r} with case_definition={requested!r}; "
        f"available={sorted(available)}"
    )


def _continuous_week_index(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(start=start.normalize(), end=end.normalize(), freq="7D")


def build_weekly_dengue_series(
    df: pd.DataFrame,
    country: str,
    case_definition: str = "Total",
    min_weeks: int = 156,
    log1p_transform: bool = False,
) -> pd.DataFrame:
    """Build one continuous weekly dengue surveillance series with explicit missing-week flags."""
    weekly = _weekly_rows(df, country)
    selected_case_definition = _select_case_definition(weekly, case_definition, country)
    selected = weekly.loc[weekly["case_definition_standardised"] == selected_case_definition].copy()
    selected = selected.dropna(subset=["calendar_start_date"]).copy()
    selected = selected.sort_values("calendar_start_date", kind="mergesort")
    if selected.empty:
        raise ValueError(f"No weekly dengue rows after filtering country={country!r}")

    grouped = (
        selected.groupby("calendar_start_date", as_index=False)
        .agg(
            y_raw=("dengue_total", "sum"),
            source_row_count=("dengue_total", "size"),
        )
        .sort_values("calendar_start_date", kind="mergesort")
    )
    grouped["duplicate_row_count"] = grouped["source_row_count"].clip(lower=1) - 1
    observed_weeks = int(grouped["calendar_start_date"].nunique())
    if observed_weeks < int(min_weeks):
        raise ValueError(
            f"country={country!r} case_definition={selected_case_definition!r} has {observed_weeks} weekly observations; "
            f"requires at least {int(min_weeks)}"
        )

    expected_dates = _continuous_week_index(grouped["calendar_start_date"].min(), grouped["calendar_start_date"].max())
    continuous = pd.DataFrame({"calendar_start_date": expected_dates})
    continuous = continuous.merge(grouped, on="calendar_start_date", how="left")
    continuous["country"] = country
    continuous["case_definition_standardised"] = selected_case_definition
    continuous["t"] = range(len(continuous))
    continuous["missing_week_indicator"] = continuous["y_raw"].isna()
    continuous["source_row_count"] = continuous["source_row_count"].fillna(0).astype(int)
    continuous["duplicate_row_count"] = continuous["duplicate_row_count"].fillna(0).astype(int)
    continuous["y_raw"] = pd.to_numeric(continuous["y_raw"], errors="coerce")
    continuous["y"] = np.log1p(continuous["y_raw"]) if log1p_transform else continuous["y_raw"]
    continuous["target_transform"] = "log1p" if log1p_transform else "identity"
    columns = [
        "country",
        "case_definition_standardised",
        "calendar_start_date",
        "t",
        "y",
        "y_raw",
        "missing_week_indicator",
        "source_row_count",
        "duplicate_row_count",
        "target_transform",
    ]
    return continuous.loc[:, columns]


def _coerce_series_spec(spec: DengueSeriesSpec | dict[str, Any]) -> DengueSeriesSpec:
    if isinstance(spec, DengueSeriesSpec):
        return spec
    return DengueSeriesSpec(
        country=str(spec["country"]),
        case_definition=str(spec.get("case_definition", "Total")),
        min_weeks=int(spec.get("min_weeks", 156)),
        log1p_transform=bool(spec.get("log1p_transform", False)),
    )


def build_dengue_benchmark_panel(
    df: pd.DataFrame,
    series_specs: Iterable[DengueSeriesSpec | dict[str, Any]],
) -> pd.DataFrame:
    """Build a panel from explicit country/case-definition dengue series specs."""
    frames: list[pd.DataFrame] = []
    for raw_spec in series_specs:
        spec = _coerce_series_spec(raw_spec)
        series = build_weekly_dengue_series(
            df,
            country=spec.country,
            case_definition=spec.case_definition,
            min_weeks=spec.min_weeks,
            log1p_transform=spec.log1p_transform,
        )
        series["series_name"] = series["country"] + " / " + series["case_definition_standardised"]
        frames.append(series)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def dengue_series_quality(series: pd.DataFrame) -> dict[str, float]:
    """Compute audit-friendly quality metrics for one continuous weekly series."""
    y = pd.to_numeric(series["y_raw"], errors="coerce")
    total_weeks = int(len(series))
    return {
        "observed_week_count": float(y.notna().sum()),
        "expected_week_count": float(total_weeks),
        "zero_fraction": float((y.dropna() == 0.0).mean()) if y.notna().any() else 0.0,
        "missing_week_fraction": float(series["missing_week_indicator"].astype(bool).mean()) if total_weeks else 0.0,
        "duplicate_row_count": float(pd.to_numeric(series["duplicate_row_count"], errors="coerce").fillna(0).sum()),
    }


def build_dengue_series_catalog(df: pd.DataFrame, min_weeks: int = 156) -> pd.DataFrame:
    """Summarize weekly dengue coverage by country and case definition."""
    weekly = df.loc[df["T_res"] == "Week"].copy()
    rows: list[dict[str, Any]] = []
    for (country, case_definition), subset in weekly.groupby(["country", "case_definition_standardised"], dropna=False):
        subset = subset.dropna(subset=["calendar_start_date"]).copy()
        if subset.empty:
            continue
        grouped = subset.groupby("calendar_start_date", as_index=False).agg(
            y_raw=("dengue_total", "sum"),
            source_row_count=("dengue_total", "size"),
        )
        expected_dates = _continuous_week_index(grouped["calendar_start_date"].min(), grouped["calendar_start_date"].max())
        expected = pd.DataFrame({"calendar_start_date": expected_dates}).merge(grouped, on="calendar_start_date", how="left")
        expected["missing_week_indicator"] = expected["y_raw"].isna()
        expected["duplicate_row_count"] = expected["source_row_count"].fillna(0).clip(lower=1) - 1
        y = pd.to_numeric(expected["y_raw"], errors="coerce")
        expected_week_count = int(len(expected))
        observed_week_count = int(y.notna().sum())
        rows.append(
            {
                "country": str(country),
                "case_definition_standardised": str(case_definition),
                "row_count": int(len(subset)),
                "observed_week_count": observed_week_count,
                "expected_week_count": expected_week_count,
                "min_date": grouped["calendar_start_date"].min().date().isoformat(),
                "max_date": grouped["calendar_start_date"].max().date().isoformat(),
                "zero_fraction": float((y.dropna() == 0.0).mean()) if y.notna().any() else 0.0,
                "missing_week_count": int(expected["missing_week_indicator"].sum()),
                "missing_week_fraction": float(expected["missing_week_indicator"].mean()) if expected_week_count else 0.0,
                "duplicate_country_date_case_definition_rows": int(expected["duplicate_row_count"].sum()),
                "meets_min_weeks": bool(observed_week_count >= int(min_weeks)),
            }
        )
    columns = [
        "country",
        "case_definition_standardised",
        "row_count",
        "observed_week_count",
        "expected_week_count",
        "min_date",
        "max_date",
        "zero_fraction",
        "missing_week_count",
        "missing_week_fraction",
        "duplicate_country_date_case_definition_rows",
        "meets_min_weeks",
    ]
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["meets_min_weeks", "country", "case_definition_standardised"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def recommend_first_wave_dengue_series(
    catalog: pd.DataFrame,
    min_weeks: int = 156,
    first_wave_specs: Iterable[dict[str, str]] = FIRST_WAVE_DENGUE_SERIES,
) -> pd.DataFrame:
    """Recommend the predeclared first-wave dengue smoke series if coverage is sufficient."""
    rows: list[dict[str, Any]] = []
    for index, spec in enumerate(first_wave_specs, start=1):
        country = spec["country"]
        requested = spec.get("case_definition", "Total")
        country_rows = catalog.loc[catalog["country"] == country].copy()
        usable = country_rows.loc[country_rows["observed_week_count"] >= int(min_weeks)].copy()
        selected = usable.loc[usable["case_definition_standardised"] == requested]
        if selected.empty and requested == "Total":
            selected = usable.loc[usable["case_definition_standardised"] == "Confirmed"]
        if selected.empty:
            rows.append(
                {
                    "recommended_order": index,
                    "country": country,
                    "case_definition_standardised": requested,
                    "recommended": False,
                    "reason": f"No {requested} weekly series with >= {int(min_weeks)} observations.",
                    "observed_week_count": 0,
                    "missing_week_fraction": pd.NA,
                    "zero_fraction": pd.NA,
                }
            )
            continue
        row = selected.sort_values(
            ["case_definition_standardised", "missing_week_fraction", "observed_week_count"],
            ascending=[True, True, False],
        ).iloc[0]
        selected_case = str(row["case_definition_standardised"])
        reason = "Requested first-wave series is usable."
        if selected_case != requested:
            reason = f"{requested} unavailable; using {selected_case} as allowed fallback."
        rows.append(
            {
                "recommended_order": index,
                "country": country,
                "case_definition_standardised": selected_case,
                "recommended": True,
                "reason": reason,
                "observed_week_count": int(row["observed_week_count"]),
                "missing_week_fraction": float(row["missing_week_fraction"]),
                "zero_fraction": float(row["zero_fraction"]),
            }
        )
    return pd.DataFrame(rows).sort_values("recommended_order").reset_index(drop=True)
