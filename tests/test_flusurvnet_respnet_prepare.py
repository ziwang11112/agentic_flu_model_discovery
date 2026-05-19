from __future__ import annotations

from scripts.prepare_flusurvnet_multiseason_from_respnet import build_custom_export_rows


def test_respnet_rows_are_mapped_to_custom_flusurvnet_export_shape() -> None:
    source_rows = [
        {
            "surveillance_network": "FluSurv-NET",
            "season": "2324",
            "mmwr_year": "2023",
            "mmwr_week": "40",
            "age_group": "65+ yr",
            "sex": "Overall",
            "race_ethnicity": "Overall",
            "site": "Overall",
            "weekly_rate": "0.2",
            "cumulative_rate": "0.2",
            "rate_type": "Observed",
        },
        {
            "surveillance_network": "FluSurv-NET",
            "season": "2324",
            "mmwr_year": "2023",
            "mmwr_week": "40",
            "age_group": "65+ yr",
            "sex": "Overall",
            "race_ethnicity": "Overall",
            "site": "Overall",
            "weekly_rate": "0.3",
            "cumulative_rate": "0.3",
            "rate_type": "Age-Adjusted",
        },
        {
            "surveillance_network": "FluSurv-NET",
            "season": "2526",
            "mmwr_year": "2026",
            "mmwr_week": "18",
            "age_group": "Overall",
            "sex": "Overall",
            "race_ethnicity": "Overall",
            "site": "Overall",
            "weekly_rate": "0.1",
            "cumulative_rate": "",
            "rate_type": "Estimated",
        },
    ]

    rows = build_custom_export_rows(source_rows)

    assert len(rows) == 1
    assert rows[0]["YEAR"] == "2023-24"
    assert rows[0]["YEAR.1"] == "2023"
    assert rows[0]["WEEK"] == "40"
    assert rows[0]["AGE CATEGORY"] == ">= 65 yr"
    assert rows[0]["CATCHMENT"] == "Entire Network"
    assert rows[0]["VIRUS TYPE CATEGORY"] == "Overall"
    assert rows[0]["WEEKLY RATE"] == "0.2"
    assert rows[0]["AGE ADJUSTED WEEKLY RATE"] == "0.3"
