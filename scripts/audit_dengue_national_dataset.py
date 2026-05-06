from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.dengue_loader import (  # noqa: E402
    build_dengue_series_catalog,
    load_dengue_national_csv,
    recommend_first_wave_dengue_series,
)


def _resolve_repo_path(path: str | Path) -> Path:
    resolved = Path(path)
    return resolved if resolved.is_absolute() else REPO_ROOT / resolved


def _markdown_table(frame: pd.DataFrame, columns: Iterable[str] | None = None, max_rows: int = 30) -> str:
    if columns is not None:
        frame = frame.loc[:, list(columns)].copy()
    if frame.empty:
        return "_None._"
    shown = frame.head(max_rows).fillna("")
    lines = [
        "| " + " | ".join(shown.columns.astype(str).tolist()) + " |",
        "| " + " | ".join(["---"] * len(shown.columns)) + " |",
    ]
    for row in shown.itertuples(index=False):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    if len(frame) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(frame)} rows._")
    return "\n".join(lines)


def _date_range_text(frame: pd.DataFrame) -> str:
    dates = frame["calendar_start_date"].dropna()
    if dates.empty:
        return "unknown"
    return f"{dates.min().date().isoformat()} to {dates.max().date().isoformat()}"


def _duplicate_count(frame: pd.DataFrame) -> int:
    weekly = frame.loc[frame["T_res"] == "Week"].copy()
    if weekly.empty:
        return 0
    grouped = weekly.groupby(["country", "calendar_start_date", "case_definition_standardised"], dropna=False).size()
    duplicates = grouped.loc[grouped > 1]
    return int((duplicates - 1).sum())


def build_audit_report(
    frame: pd.DataFrame,
    catalog: pd.DataFrame,
    recommended: pd.DataFrame,
    csv_path: Path,
    catalog_path: Path,
    recommended_path: Path,
) -> str:
    temporal_counts = frame["T_res"].fillna("missing").astype(str).value_counts(dropna=False).rename_axis("T_res").reset_index(name="row_count")
    case_counts = (
        frame["case_definition_standardised"]
        .fillna("missing")
        .astype(str)
        .value_counts(dropna=False)
        .rename_axis("case_definition_standardised")
        .reset_index(name="row_count")
    )
    weekly_catalog = catalog.copy()
    usable = weekly_catalog.loc[weekly_catalog["observed_week_count"] >= 156].copy()
    weekly_countries = sorted(frame.loc[frame["T_res"] == "Week", "country"].dropna().astype(str).unique().tolist())
    usable_countries = sorted(usable["country"].dropna().astype(str).unique().tolist())
    duplicate_count = _duplicate_count(frame)

    lines = [
        "# Dengue National Dataset Audit",
        "",
        f"Input CSV: `{csv_path}`",
        "",
        "## Dataset Summary",
        "",
        f"- Row count: `{len(frame)}`",
        f"- Number of countries: `{frame['country'].nunique()}`",
        f"- Date range: `{_date_range_text(frame)}`",
        f"- Weekly countries: `{len(weekly_countries)}`",
        f"- Countries with >=156 weekly observations: `{len(usable_countries)}`",
        f"- Duplicate country/date/case-definition rows: `{duplicate_count}`",
        "",
        "## Temporal Resolution Counts",
        "",
        _markdown_table(temporal_counts),
        "",
        "## Case Definition Counts",
        "",
        _markdown_table(case_counts),
        "",
        "## Weekly Series Catalog",
        "",
        f"Catalog written to `{catalog_path}`.",
        "",
        _markdown_table(
            weekly_catalog,
            columns=[
                "country",
                "case_definition_standardised",
                "observed_week_count",
                "expected_week_count",
                "zero_fraction",
                "missing_week_fraction",
                "duplicate_country_date_case_definition_rows",
                "meets_min_weeks",
            ],
            max_rows=50,
        ),
        "",
        "## Recommended First-Wave Benchmark Countries",
        "",
        f"Recommended series table written to `{recommended_path}`.",
        "",
        _markdown_table(
            recommended,
            columns=[
                "recommended_order",
                "country",
                "case_definition_standardised",
                "recommended",
                "observed_week_count",
                "missing_week_fraction",
                "zero_fraction",
                "reason",
            ],
            max_rows=20,
        ),
        "",
        "## Interpretation Boundary",
        "",
        "Dengue is vector-borne. This audit prepares a secondary surveillance benchmark for structure-selection reuse; it does not imply that the flu hospitalization SEIR mechanism directly transfers to dengue.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the national dengue extract for weekly benchmark readiness.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    csv_path = _resolve_repo_path(args.csv)
    output_dir = _resolve_repo_path(args.output_dir)
    report_path = _resolve_repo_path(args.report)
    catalog_path = output_dir / "dengue_series_catalog.csv"
    recommended_path = output_dir / "dengue_recommended_weekly_series.csv"

    frame = load_dengue_national_csv(csv_path)
    catalog = build_dengue_series_catalog(frame, min_weeks=156)
    recommended = recommend_first_wave_dengue_series(catalog, min_weeks=156)

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    catalog.to_csv(catalog_path, index=False)
    recommended.to_csv(recommended_path, index=False)
    report_path.write_text(
        build_audit_report(frame, catalog, recommended, csv_path, catalog_path, recommended_path),
        encoding="utf-8",
    )
    print("Wrote dengue audit outputs:")
    print(f"- report: {report_path}")
    print(f"- catalog: {catalog_path}")
    print(f"- recommended weekly series: {recommended_path}")


if __name__ == "__main__":
    main()
