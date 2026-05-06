from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.flusurvnet_multiseason_loader import (  # noqa: E402
    BENCHMARK_AGE_GROUPS,
    BENCHMARK_FILTERS,
    build_flusurvnet_season_series_catalog,
    current_flu_season_label,
    load_flusurvnet_multiseason_csv,
    sorted_seasons,
)

MIN_COMPLETED_WEEKS = 20

SEASON_STATUS_COLUMNS = [
    "season",
    "status",
    "reason",
    "has_all_required_age_groups",
    "present_age_groups",
    "observed_week_count_min",
    "observed_week_count_max",
    "expected_week_count_max",
    "missing_week_count",
    "duplicate_row_count",
    "min_year_label",
    "min_week",
    "max_year_label",
    "max_week",
]

RECOMMENDED_COLUMNS = SEASON_STATUS_COLUMNS + ["recommended_split"]


def _resolve_repo_path(path: str | Path) -> Path:
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    return REPO_ROOT / resolved


def _category_values(frame: pd.DataFrame, column: str) -> list[str]:
    if column not in frame.columns:
        return []
    values = frame[column].dropna().astype(str).unique()
    return sorted(values)


def classify_seasons(
    catalog: pd.DataFrame,
    today: date | None = None,
    min_completed_weeks: int = MIN_COMPLETED_WEEKS,
) -> pd.DataFrame:
    """Classify seasons conservatively for benchmark split selection."""
    current_season = current_flu_season_label(today)
    rows = []

    for season in sorted_seasons(catalog["season"].dropna().unique()):
        season_catalog = catalog.loc[catalog["season"] == season].copy()
        required = season_catalog.loc[season_catalog["age_group"].isin(BENCHMARK_AGE_GROUPS)].copy()
        present = required.loc[required["row_count"] > 0, "age_group"].astype(str).tolist()
        has_all_required_age_groups = set(BENCHMARK_AGE_GROUPS).issubset(set(present))

        observed_counts = required.loc[required["row_count"] > 0, "observed_week_count"]
        expected_counts = required.loc[required["row_count"] > 0, "expected_week_count"]
        observed_min = int(observed_counts.min()) if not observed_counts.empty else 0
        observed_max = int(observed_counts.max()) if not observed_counts.empty else 0
        expected_max = int(expected_counts.max()) if not expected_counts.empty else 0
        missing_week_count = int(required["missing_week_count"].sum())
        duplicate_row_count = int(required["duplicate_row_count"].sum())

        non_empty = required.loc[required["row_count"] > 0].copy()
        if non_empty.empty:
            min_year_label = pd.NA
            min_week = pd.NA
            max_year_label = pd.NA
            max_week = pd.NA
        else:
            first = non_empty.sort_values(["min_year_label", "min_week"], kind="mergesort").iloc[0]
            last = non_empty.sort_values(["max_year_label", "max_week"], kind="mergesort").iloc[-1]
            min_year_label = first["min_year_label"]
            min_week = first["min_week"]
            max_year_label = last["max_year_label"]
            max_week = last["max_week"]

        reasons: list[str] = []
        if not has_all_required_age_groups:
            missing_age_groups = [age for age in BENCHMARK_AGE_GROUPS if age not in set(present)]
            reasons.append("missing required age groups: " + ", ".join(missing_age_groups))
        if observed_min < min_completed_weeks:
            reasons.append(f"fewer than {min_completed_weeks} observed weeks in at least one age group")
        if missing_week_count:
            reasons.append("internal missing weeks detected")
        if duplicate_row_count:
            reasons.append("duplicate season/week/age rows detected")
        if season == current_season:
            reasons.append("current surveillance season; treat as preliminary")

        if not reasons:
            status = "complete"
            reason = "passes required age, missing-week, duplicate, and preliminary checks"
        elif season == current_season:
            status = "preliminary"
            reason = "; ".join(reasons)
        else:
            status = "incomplete"
            reason = "; ".join(reasons)

        rows.append(
            {
                "season": season,
                "status": status,
                "reason": reason,
                "has_all_required_age_groups": bool(has_all_required_age_groups),
                "present_age_groups": "; ".join(present),
                "observed_week_count_min": observed_min,
                "observed_week_count_max": observed_max,
                "expected_week_count_max": expected_max,
                "missing_week_count": missing_week_count,
                "duplicate_row_count": duplicate_row_count,
                "min_year_label": min_year_label,
                "min_week": min_week,
                "max_year_label": max_year_label,
                "max_week": max_week,
            }
        )

    return pd.DataFrame(rows, columns=SEASON_STATUS_COLUMNS)


def build_recommended_completed_seasons(season_status: pd.DataFrame) -> pd.DataFrame:
    recommended = season_status.loc[season_status["status"] == "complete"].copy()
    order = {season: index for index, season in enumerate(sorted_seasons(recommended["season"].dropna().unique()))}
    recommended = recommended.sort_values("season", key=lambda series: series.map(order))
    recommended = recommended.reset_index(drop=True)
    recommended["recommended_split"] = ""

    n_complete = len(recommended)
    if n_complete >= 3:
        recommended.loc[: n_complete - 3, "recommended_split"] = "train"
        recommended.loc[n_complete - 2, "recommended_split"] = "validation"
        recommended.loc[n_complete - 1, "recommended_split"] = "test"
    elif n_complete == 2:
        recommended.loc[0, "recommended_split"] = "train"
        recommended.loc[1, "recommended_split"] = "test"
    elif n_complete == 1:
        recommended.loc[0, "recommended_split"] = "train"

    return recommended.loc[:, RECOMMENDED_COLUMNS]


def _markdown_table(frame: pd.DataFrame, columns: Iterable[str] | None = None, max_rows: int = 20) -> str:
    if columns is not None:
        frame = frame.loc[:, list(columns)]
    if frame.empty:
        return "_None._"

    shown = frame.head(max_rows).copy()
    shown = shown.fillna("")
    headers = list(shown.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in shown.itertuples(index=False):
        values = [str(value).replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    if len(frame) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(frame)} rows._")
    return "\n".join(lines)


def _format_list(values: Iterable[str]) -> str:
    values = list(values)
    return ", ".join(values) if values else "_None found._"


def build_audit_report(
    frame: pd.DataFrame,
    catalog: pd.DataFrame,
    season_status: pd.DataFrame,
    recommended: pd.DataFrame,
    csv_path: Path,
    catalog_path: Path,
    recommended_path: Path,
) -> str:
    age_categories = _category_values(frame, "AGE CATEGORY")
    available_seasons = sorted_seasons(frame["season"].dropna().unique())

    missing = catalog.loc[catalog["missing_week_count"] > 0].copy()
    duplicates = catalog.loc[catalog["duplicate_row_count"] > 0].copy()
    complete = season_status.loc[season_status["status"] == "complete"].copy()
    not_complete = season_status.loc[season_status["status"] != "complete"].copy()

    lines = [
        "# FluSurv-NET Multi-Season Audit",
        "",
        f"Input CSV: `{csv_path}`",
        f"Total normalized rows: {len(frame)}",
        f"Available seasons: {_format_list(available_seasons)}",
        "",
        "## Main Benchmark Filters",
        "",
        "The audit applies these filters for season-age coverage checks:",
        "",
    ]
    for column, value in BENCHMARK_FILTERS.items():
        lines.append(f"- `{column} == {value}`")
    lines.extend(
        [
            f"- `AGE CATEGORY in {BENCHMARK_AGE_GROUPS}`",
            "- target column: `WEEKLY RATE`",
            "",
            "## Category Coverage",
            "",
            f"Age categories available: {_format_list(age_categories)}",
            f"Virus type categories: {_format_list(_category_values(frame, 'VIRUS TYPE CATEGORY'))}",
            f"Sex categories: {_format_list(_category_values(frame, 'SEX CATEGORY'))}",
            f"Race categories: {_format_list(_category_values(frame, 'RACE CATEGORY'))}",
            f"Catchment categories: {_format_list(_category_values(frame, 'CATCHMENT'))}",
            "",
            "## Season Coverage",
            "",
            _markdown_table(
                season_status,
                columns=[
                    "season",
                    "status",
                    "has_all_required_age_groups",
                    "observed_week_count_min",
                    "observed_week_count_max",
                    "min_year_label",
                    "min_week",
                    "max_year_label",
                    "max_week",
                    "reason",
                ],
                max_rows=50,
            ),
            "",
            "## Weeks Per Season And Age Group",
            "",
            f"Catalog written to `{catalog_path}`.",
            "",
            _markdown_table(
                catalog,
                columns=[
                    "season",
                    "age_group",
                    "observed_week_count",
                    "expected_week_count",
                    "missing_week_count",
                    "duplicate_row_count",
                    "min_year_label",
                    "min_week",
                    "max_year_label",
                    "max_week",
                ],
                max_rows=50,
            ),
            "",
            "## Missing Weeks",
            "",
            _markdown_table(
                missing,
                columns=["season", "age_group", "missing_week_count", "missing_weeks"],
                max_rows=50,
            ),
            "",
            "## Duplicate Season/Week/Age Rows",
            "",
            _markdown_table(
                duplicates,
                columns=["season", "age_group", "duplicate_week_count", "duplicate_row_count"],
                max_rows=50,
            ),
            "",
            "## Completed vs Incomplete Seasons",
            "",
            "Appears complete:",
            "",
            _markdown_table(complete, columns=["season", "observed_week_count_min", "observed_week_count_max"], max_rows=50),
            "",
            "Incomplete or preliminary:",
            "",
            _markdown_table(not_complete, columns=["season", "status", "reason"], max_rows=50),
            "",
            "## Recommended Split",
            "",
            f"Completed-season recommendations written to `{recommended_path}`.",
            "",
        ]
    )

    if recommended.empty:
        lines.append(
            "No completed seasons passed the conservative checks, so no train/validation/test split is recommended yet."
        )
    else:
        lines.append(_markdown_table(recommended, columns=["season", "recommended_split", "reason"], max_rows=50))
        lines.append("")
        lines.append(
            "Use the latest completed season as the main test season, the prior completed season as validation "
            "when available, and older completed seasons for training. Preliminary current-season data should be "
            "kept out of the main benchmark unless the experiment is explicitly labeled preliminary."
        )

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a multi-season FluSurv-NET custom CSV export.")
    parser.add_argument("--csv", required=True, help="Path to the FluSurv-NET multi-season custom CSV.")
    parser.add_argument("--output-dir", required=True, help="Directory for processed audit CSV outputs.")
    parser.add_argument("--report", required=True, help="Markdown audit report path.")
    args = parser.parse_args()

    csv_path = _resolve_repo_path(args.csv)
    output_dir = _resolve_repo_path(args.output_dir)
    report_path = _resolve_repo_path(args.report)
    catalog_path = output_dir / "season_series_catalog.csv"
    recommended_path = output_dir / "recommended_completed_seasons.csv"

    frame = load_flusurvnet_multiseason_csv(csv_path)
    catalog = build_flusurvnet_season_series_catalog(frame)
    season_status = classify_seasons(catalog)
    recommended = build_recommended_completed_seasons(season_status)

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    catalog.to_csv(catalog_path, index=False)
    recommended.to_csv(recommended_path, index=False)
    report_path.write_text(
        build_audit_report(frame, catalog, season_status, recommended, csv_path, catalog_path, recommended_path),
        encoding="utf-8",
    )

    print("Wrote FluSurv-NET multi-season audit outputs:")
    print(f"- report: {report_path}")
    print(f"- catalog: {catalog_path}")
    print(f"- recommended completed seasons: {recommended_path}")


if __name__ == "__main__":
    main()
