from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd

BENCHMARK_AGE_GROUPS = ["Overall", "0-4 yr", "5-17 yr", "18-49 yr", "50-64 yr", ">= 65 yr"]

BENCHMARK_FILTERS = {
    "CATCHMENT": "Entire Network",
    "SEX CATEGORY": "Overall",
    "RACE CATEGORY": "Overall",
    "VIRUS TYPE CATEGORY": "Overall",
}

EXPECTED_COLUMNS = [
    "CATCHMENT",
    "NETWORK",
    "YEAR",
    "YEAR.1",
    "WEEK",
    "AGE CATEGORY",
    "SEX CATEGORY",
    "RACE CATEGORY",
    "VIRUS TYPE CATEGORY",
    "CUMULATIVE RATE",
    "WEEKLY RATE",
    "AGE ADJUSTED CUMULATIVE RATE",
    "AGE ADJUSTED WEEKLY RATE",
]

SEASON_SERIES_COLUMNS = [
    "season",
    "age_group",
    "year_label",
    "week",
    "t",
    "y",
    "missing_week_flag",
    "original_row_count",
]

SEASON_CATALOG_COLUMNS = [
    "season",
    "age_group",
    "row_count",
    "observed_week_count",
    "expected_week_count",
    "missing_week_count",
    "missing_weeks",
    "duplicate_row_count",
    "duplicate_week_count",
    "target_non_null_count",
    "min_year_label",
    "min_week",
    "max_year_label",
    "max_week",
    "appears_complete",
]


def _normalize_columns(columns: Iterable[object]) -> list[str]:
    return [str(column).replace("\ufeff", "").strip() for column in columns]


def _find_header_row(path: Path) -> int:
    header_markers = {"CATCHMENT", "WEEK", "AGE CATEGORY"}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for index, row in enumerate(reader):
            normalized = {cell.replace("\ufeff", "").strip().upper() for cell in row}
            if header_markers.issubset(normalized) and "YEAR" in normalized:
                return index
    raise ValueError(f"Could not find a FluSurv-NET header row in {path}")


def _format_missing_columns(columns: Iterable[str]) -> str:
    return ", ".join(sorted(columns))


def _coerce_string_columns(frame: pd.DataFrame) -> pd.DataFrame:
    string_columns = [
        "CATCHMENT",
        "NETWORK",
        "YEAR",
        "AGE CATEGORY",
        "SEX CATEGORY",
        "RACE CATEGORY",
        "VIRUS TYPE CATEGORY",
    ]
    for column in string_columns:
        if column in frame.columns:
            frame[column] = frame[column].astype("string").str.strip()
            frame[column] = frame[column].replace("", pd.NA)
    return frame


def _coerce_numeric_columns(frame: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = [
        "YEAR.1",
        "WEEK",
        "CUMULATIVE RATE",
        "WEEKLY RATE",
        "AGE ADJUSTED CUMULATIVE RATE",
        "AGE ADJUSTED WEEKLY RATE",
    ]
    for column in numeric_columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def load_flusurvnet_multiseason_csv(path: str | Path) -> pd.DataFrame:
    """Load and normalize a multi-season FluSurv-NET custom CSV export."""
    csv_path = Path(path)
    header_row = _find_header_row(csv_path)
    frame = pd.read_csv(csv_path, skiprows=header_row)
    frame.columns = _normalize_columns(frame.columns)

    missing_columns = set(EXPECTED_COLUMNS).difference(frame.columns)
    if missing_columns:
        missing = _format_missing_columns(missing_columns)
        raise ValueError(f"Missing required FluSurv-NET columns: {missing}")

    frame = _coerce_string_columns(frame)
    frame = _coerce_numeric_columns(frame)
    frame = frame.dropna(subset=["YEAR", "YEAR.1", "WEEK", "AGE CATEGORY"]).copy()
    frame["YEAR.1"] = frame["YEAR.1"].astype(int)
    frame["WEEK"] = frame["WEEK"].astype(int)
    frame["season"] = frame["YEAR"].astype("string").str.strip()
    frame["year_label"] = frame["YEAR.1"].astype(int)

    frame = frame.sort_values(["season", "year_label", "WEEK"], kind="mergesort").reset_index(drop=True)
    return frame


def _mmwr_year_start(mmwr_year: int) -> date:
    jan4 = date(mmwr_year, 1, 4)
    days_since_sunday = (jan4.weekday() + 1) % 7
    return jan4 - timedelta(days=days_since_sunday)


def _mmwr_weeks_in_year(mmwr_year: int) -> int:
    start = _mmwr_year_start(mmwr_year)
    next_start = _mmwr_year_start(mmwr_year + 1)
    return (next_start - start).days // 7


def _mmwr_year_week(day: date) -> tuple[int, int]:
    candidate_year = day.year
    start = _mmwr_year_start(candidate_year)
    if day < start:
        candidate_year -= 1
        start = _mmwr_year_start(candidate_year)
    next_start = _mmwr_year_start(candidate_year + 1)
    if day >= next_start:
        candidate_year += 1
        start = next_start
    week = ((day - start).days // 7) + 1
    return candidate_year, week


def current_flu_season_label(today: date | None = None) -> str:
    """Return the current surveillance season label, e.g. 2025-26."""
    mmwr_year, mmwr_week = _mmwr_year_week(today or date.today())
    start_year = mmwr_year if mmwr_week >= 40 else mmwr_year - 1
    end_year = start_year + 1
    return f"{start_year}-{str(end_year)[-2:]}"


def _iter_mmwr_weeks(
    start_year: int,
    start_week: int,
    end_year: int,
    end_week: int,
) -> list[tuple[int, int]]:
    if (end_year, end_week) < (start_year, start_week):
        raise ValueError(
            f"Invalid MMWR week range: {start_year}-W{start_week:02d} to {end_year}-W{end_week:02d}"
        )

    weeks: list[tuple[int, int]] = []
    for year in range(start_year, end_year + 1):
        first_week = start_week if year == start_year else 1
        last_week = end_week if year == end_year else _mmwr_weeks_in_year(year)
        for week in range(first_week, last_week + 1):
            weeks.append((year, week))
    return weeks


def _format_week(year_label: int, week: int) -> str:
    return f"{year_label}-W{week:02d}"


def _season_sort_key(season: object) -> tuple[int, str]:
    text = str(season)
    token = text.split("-", 1)[0]
    try:
        return int(token), text
    except ValueError:
        return 0, text


def sorted_seasons(seasons: Iterable[object]) -> list[str]:
    unique = {str(season) for season in seasons if pd.notna(season)}
    return sorted(unique, key=_season_sort_key)


def _ensure_normalized_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = _normalize_columns(normalized.columns)
    normalized = _coerce_string_columns(normalized)

    missing_columns = {"YEAR", "YEAR.1", "WEEK", "AGE CATEGORY"}.difference(normalized.columns)
    if missing_columns:
        missing = _format_missing_columns(missing_columns)
        raise ValueError(f"Missing required FluSurv-NET columns: {missing}")

    if "season" not in normalized.columns:
        normalized["season"] = normalized["YEAR"].astype("string").str.strip()
    if "year_label" not in normalized.columns:
        normalized["year_label"] = pd.to_numeric(normalized["YEAR.1"], errors="coerce")
    normalized["year_label"] = pd.to_numeric(normalized["year_label"], errors="coerce")
    normalized["week"] = pd.to_numeric(normalized["WEEK"], errors="coerce")
    normalized = normalized.dropna(subset=["season", "year_label", "week"]).copy()
    normalized["season"] = normalized["season"].astype("string").str.strip()
    normalized["year_label"] = normalized["year_label"].astype(int)
    normalized["week"] = normalized["week"].astype(int)
    return normalized


def _filtered_benchmark_rows(
    frame: pd.DataFrame,
    season: str,
    age_group: str,
    target_col: str,
) -> pd.DataFrame:
    normalized = _ensure_normalized_columns(frame)
    missing_filter_columns = set(BENCHMARK_FILTERS).difference(normalized.columns)
    if missing_filter_columns:
        missing = _format_missing_columns(missing_filter_columns)
        raise ValueError(f"Missing required FluSurv-NET filter columns: {missing}")
    if target_col not in normalized.columns:
        raise ValueError(f"Missing target column: {target_col}")

    mask = (normalized["season"] == season) & (normalized["AGE CATEGORY"] == age_group)
    for column, value in BENCHMARK_FILTERS.items():
        mask &= normalized[column] == value

    filtered = normalized.loc[mask].copy()
    filtered[target_col] = pd.to_numeric(filtered[target_col], errors="coerce")
    return filtered.sort_values(["year_label", "week"], kind="mergesort").reset_index(drop=True)


def _duplicate_counts(filtered: pd.DataFrame) -> tuple[int, int]:
    if filtered.empty:
        return 0, 0
    counts = filtered.groupby(["year_label", "week"], dropna=False).size()
    duplicate_groups = counts.loc[counts > 1]
    duplicate_week_count = int(len(duplicate_groups))
    duplicate_row_count = int((duplicate_groups - 1).sum())
    return duplicate_row_count, duplicate_week_count


def _expected_week_pairs(filtered: pd.DataFrame) -> list[tuple[int, int]]:
    if filtered.empty:
        return []
    observed = filtered.loc[:, ["year_label", "week"]].drop_duplicates()
    observed = observed.sort_values(["year_label", "week"], kind="mergesort")
    first = observed.iloc[0]
    last = observed.iloc[-1]
    return _iter_mmwr_weeks(
        int(first["year_label"]),
        int(first["week"]),
        int(last["year_label"]),
        int(last["week"]),
    )


def build_flusurvnet_season_series(
    df: pd.DataFrame,
    season: str,
    age_group: str,
    target_col: str = "WEEKLY RATE",
) -> pd.DataFrame:
    """Build one season-age time series with explicit flagged missing weeks."""
    filtered = _filtered_benchmark_rows(df, season=season, age_group=age_group, target_col=target_col)
    duplicate_row_count, _ = _duplicate_counts(filtered)
    if duplicate_row_count:
        raise ValueError(
            "Duplicate FluSurv-NET rows found for "
            f"season={season!r}, age_group={age_group!r}; aggregate explicitly before building a series."
        )

    expected_pairs = _expected_week_pairs(filtered)
    if not expected_pairs:
        return pd.DataFrame(columns=SEASON_SERIES_COLUMNS)

    indexed = filtered.set_index(["year_label", "week"], drop=False)
    rows = []
    for t, (year_label, week) in enumerate(expected_pairs):
        if (year_label, week) in indexed.index:
            row = indexed.loc[(year_label, week)]
            rows.append(
                {
                    "season": season,
                    "age_group": age_group,
                    "year_label": int(year_label),
                    "week": int(week),
                    "t": t,
                    "y": row[target_col],
                    "missing_week_flag": False,
                    "original_row_count": 1,
                }
            )
        else:
            rows.append(
                {
                    "season": season,
                    "age_group": age_group,
                    "year_label": int(year_label),
                    "week": int(week),
                    "t": t,
                    "y": pd.NA,
                    "missing_week_flag": True,
                    "original_row_count": 0,
                }
            )
    return pd.DataFrame(rows, columns=SEASON_SERIES_COLUMNS)


def build_flusurvnet_multiseason_panel(
    df: pd.DataFrame,
    seasons: list[str],
    age_groups: list[str],
    target_col: str = "WEEKLY RATE",
) -> pd.DataFrame:
    """Build a benchmark panel for selected seasons and age groups."""
    series_frames = [
        build_flusurvnet_season_series(df, season=season, age_group=age_group, target_col=target_col)
        for season in seasons
        for age_group in age_groups
    ]
    if not series_frames:
        return pd.DataFrame(columns=SEASON_SERIES_COLUMNS)
    return pd.concat(series_frames, ignore_index=True)


def build_flusurvnet_season_series_catalog(
    df: pd.DataFrame,
    age_groups: Iterable[str] = BENCHMARK_AGE_GROUPS,
    target_col: str = "WEEKLY RATE",
) -> pd.DataFrame:
    """Summarize season-age coverage, missing weeks, and duplicate rows."""
    normalized = _ensure_normalized_columns(df)
    seasons = sorted_seasons(normalized["season"].dropna().unique())
    rows = []

    for season in seasons:
        for age_group in age_groups:
            filtered = _filtered_benchmark_rows(
                normalized,
                season=season,
                age_group=age_group,
                target_col=target_col,
            )
            duplicate_row_count, duplicate_week_count = _duplicate_counts(filtered)
            observed = filtered.loc[:, ["year_label", "week"]].drop_duplicates()
            expected_pairs = _expected_week_pairs(filtered)
            observed_pairs = {(int(row.year_label), int(row.week)) for row in observed.itertuples(index=False)}
            missing_pairs = [pair for pair in expected_pairs if pair not in observed_pairs]

            if observed.empty:
                min_year_label = pd.NA
                min_week = pd.NA
                max_year_label = pd.NA
                max_week = pd.NA
            else:
                observed_sorted = observed.sort_values(["year_label", "week"], kind="mergesort")
                first = observed_sorted.iloc[0]
                last = observed_sorted.iloc[-1]
                min_year_label = int(first["year_label"])
                min_week = int(first["week"])
                max_year_label = int(last["year_label"])
                max_week = int(last["week"])

            rows.append(
                {
                    "season": season,
                    "age_group": age_group,
                    "row_count": int(len(filtered)),
                    "observed_week_count": int(len(observed)),
                    "expected_week_count": int(len(expected_pairs)),
                    "missing_week_count": int(len(missing_pairs)),
                    "missing_weeks": "; ".join(_format_week(year, week) for year, week in missing_pairs),
                    "duplicate_row_count": duplicate_row_count,
                    "duplicate_week_count": duplicate_week_count,
                    "target_non_null_count": int(filtered[target_col].notna().sum()) if target_col in filtered else 0,
                    "min_year_label": min_year_label,
                    "min_week": min_week,
                    "max_year_label": max_year_label,
                    "max_week": max_week,
                    "appears_complete": bool(
                        len(filtered) > 0 and not missing_pairs and duplicate_row_count == 0
                    ),
                }
            )

    return pd.DataFrame(rows, columns=SEASON_CATALOG_COLUMNS)
