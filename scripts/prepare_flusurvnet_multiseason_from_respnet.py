from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]

DATASET_ID = "kvib-3txy"
SOURCE_URL = f"https://data.cdc.gov/resource/{DATASET_ID}.csv"
SOURCE_PAGE = f"https://data.cdc.gov/w/{DATASET_ID}"

OUTPUT_COLUMNS = [
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

BENCHMARK_AGE_MAP = {
    "65+ yr": ">= 65 yr",
    "75+ yr": ">= 75",
    "85+ yr": ">= 85",
}


def _repo_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def _season_label(code: str) -> str:
    text = str(code).strip()
    if len(text) != 4 or not text.isdigit():
        return text
    start_year = 2000 + int(text[:2])
    end_suffix = text[2:]
    return f"{start_year}-{end_suffix}"


def _season_sort_key(label: str) -> tuple[int, str]:
    try:
        return int(str(label).split("-", 1)[0]), str(label)
    except ValueError:
        return 0, str(label)


def _age_label(label: str) -> str:
    return BENCHMARK_AGE_MAP.get(label.strip(), label.strip())


def _catchment_label(site: str) -> str:
    site = site.strip()
    return "Entire Network" if site == "Overall" else site


def _download_csv(limit: int) -> list[dict[str, str]]:
    params = {
        "$limit": str(limit),
        "$order": "season, mmwr_year, mmwr_week, age_group, sex, race_ethnicity, site, rate_type",
        "surveillance_network": "FluSurv-NET",
    }
    url = f"{SOURCE_URL}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "agentic-flu-model-discovery data preparation"})
    with urlopen(request, timeout=120) as response:
        text = response.read().decode("utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def _format_rate(value: str) -> str:
    return "" if value is None else str(value).strip()


def build_custom_export_rows(source_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str, str, str, str], dict[str, str]] = {}
    rate_type_counts: Counter[str] = Counter()

    for row in source_rows:
        rate_type = row.get("rate_type", "").strip()
        rate_type_counts[rate_type] += 1
        if rate_type not in {"Observed", "Age-Adjusted"}:
            continue

        season = _season_label(row.get("season", ""))
        year = row.get("mmwr_year", "").strip()
        week = row.get("mmwr_week", "").strip()
        age = _age_label(row.get("age_group", ""))
        sex = row.get("sex", "").strip()
        race = row.get("race_ethnicity", "").strip()
        catchment = _catchment_label(row.get("site", ""))
        key = (season, year, week, age, sex, race, catchment)

        output = grouped.setdefault(
            key,
            {
                "CATCHMENT": catchment,
                "NETWORK": "FluSurv-NET",
                "YEAR": season,
                "YEAR.1": year,
                "WEEK": week,
                "AGE CATEGORY": age,
                "SEX CATEGORY": sex,
                "RACE CATEGORY": race,
                "VIRUS TYPE CATEGORY": "Overall",
                "CUMULATIVE RATE": "",
                "WEEKLY RATE": "",
                "AGE ADJUSTED CUMULATIVE RATE": "",
                "AGE ADJUSTED WEEKLY RATE": "",
            },
        )

        if rate_type == "Observed":
            output["CUMULATIVE RATE"] = _format_rate(row.get("cumulative_rate", ""))
            output["WEEKLY RATE"] = _format_rate(row.get("weekly_rate", ""))
        elif rate_type == "Age-Adjusted":
            output["AGE ADJUSTED CUMULATIVE RATE"] = _format_rate(row.get("cumulative_rate", ""))
            output["AGE ADJUSTED WEEKLY RATE"] = _format_rate(row.get("weekly_rate", ""))

    rows = list(grouped.values())
    rows.sort(
        key=lambda row: (
            _season_sort_key(row["YEAR"]),
            int(row["YEAR.1"]) if row["YEAR.1"].isdigit() else 0,
            int(row["WEEK"]) if row["WEEK"].isdigit() else 0,
            row["CATCHMENT"],
            row["AGE CATEGORY"],
            row["SEX CATEGORY"],
            row["RACE CATEGORY"],
        )
    )
    return rows


def write_custom_export(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(
            "Influenza Hospitalization Rates (per 100,000 population) for the FluSurv-NET "
            f"Network (transformed from CDC RESP-NET dataset {DATASET_ID} on {today})\n"
        )
        handle.write(
            f"Source: {SOURCE_PAGE}; rows filtered to Surveillance Network == FluSurv-NET; "
            "Observed rows fill WEEKLY/CUMULATIVE RATE and Age-Adjusted rows fill age-adjusted columns.\n"
        )
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _summarize(rows: list[dict[str, str]]) -> str:
    seasons = sorted({row["YEAR"] for row in rows}, key=_season_sort_key)
    benchmark_ages = {"Overall", "0-4 yr", "5-17 yr", "18-49 yr", "50-64 yr", ">= 65 yr"}
    by_season_age: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if (
            row["CATCHMENT"] == "Entire Network"
            and row["SEX CATEGORY"] == "Overall"
            and row["RACE CATEGORY"] == "Overall"
            and row["AGE CATEGORY"] in benchmark_ages
        ):
            by_season_age[row["YEAR"]].add(row["AGE CATEGORY"])

    complete_age_seasons = [
        season for season in seasons if benchmark_ages.issubset(by_season_age.get(season, set()))
    ]
    return "\n".join(
        [
            f"rows_written: {len(rows)}",
            f"seasons: {', '.join(seasons)}",
            f"seasons_with_required_benchmark_ages: {', '.join(complete_age_seasons)}",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare the repo's FluSurv-NET multi-season CSV from the official CDC RESP-NET dataset."
    )
    parser.add_argument("--output", default="data/raw/flusurvnet_multiseason_full.csv")
    parser.add_argument("--limit", type=int, default=50000, help="Socrata row limit for FluSurv-NET source rows.")
    args = parser.parse_args()

    source_rows = _download_csv(limit=args.limit)
    output_rows = build_custom_export_rows(source_rows)
    output_path = _repo_path(args.output)
    write_custom_export(output_rows, output_path)

    print(f"Wrote {output_path}")
    print(_summarize(output_rows))


if __name__ == "__main__":
    main()
