from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluation.ablation import build_age_prior_ablation_summary


def _write_bundle(
    root: Path,
    winners: list[dict[str, object]],
    recommendations: list[dict[str, object]],
    summary: list[dict[str, object]],
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(winners).to_csv(root / "benchmark_series_winners.csv", index=False)
    pd.DataFrame(recommendations).to_csv(root / "age_group_recommendation.csv", index=False)
    pd.DataFrame(summary).to_csv(root / "benchmark_model_summary.csv", index=False)


def test_build_age_prior_ablation_summary_compares_variants(tmp_path: Path) -> None:
    age_prior_root = tmp_path / "age_prior"
    no_age_prior_root = tmp_path / "no_age_prior"

    _write_bundle(
        age_prior_root,
        winners=[
            {
                "series_name": "0-4 yr",
                "best_test_model": "constrained_structure_discovery",
                "best_test_mae": 0.09,
                "best_rolling_model": "constrained_structure_discovery",
                "best_rolling_mean_mae": 0.11,
            }
        ],
        recommendations=[
            {
                "series_name": "0-4 yr",
                "recommended_model": "constrained_structure_discovery",
                "decision_type": "consensus",
                "best_test_model": "constrained_structure_discovery",
                "best_test_mae": 0.09,
                "best_rolling_model": "constrained_structure_discovery",
                "best_rolling_mean_mae": 0.11,
                "recommended_discovery_structure_name": "SEIRS",
                "recommended_discovery_fractional": False,
                "recommended_discovery_observation_map": "I",
            }
        ],
        summary=[
            {
                "series_name": "0-4 yr",
                "model_name": "constrained_structure_discovery",
                "test_mae": 0.09,
                "rolling_mean_mae": 0.11,
                "discovery_structure_name": "SEIRS",
                "discovery_fractional": False,
                "discovery_observation_map": "I",
            }
        ],
    )

    _write_bundle(
        no_age_prior_root,
        winners=[
            {
                "series_name": "0-4 yr",
                "best_test_model": "deterministic_seir",
                "best_test_mae": 0.10,
                "best_rolling_model": "deterministic_seir",
                "best_rolling_mean_mae": 0.12,
            }
        ],
        recommendations=[
            {
                "series_name": "0-4 yr",
                "recommended_model": "deterministic_seir",
                "decision_type": "consensus",
                "best_test_model": "deterministic_seir",
                "best_test_mae": 0.10,
                "best_rolling_model": "deterministic_seir",
                "best_rolling_mean_mae": 0.12,
                "recommended_discovery_structure_name": "",
                "recommended_discovery_fractional": "",
                "recommended_discovery_observation_map": "",
            }
        ],
        summary=[
            {
                "series_name": "0-4 yr",
                "model_name": "constrained_structure_discovery",
                "test_mae": 0.12,
                "rolling_mean_mae": 0.15,
                "discovery_structure_name": "SIR",
                "discovery_fractional": False,
                "discovery_observation_map": "I",
            }
        ],
    )

    summary = build_age_prior_ablation_summary(age_prior_root, no_age_prior_root)

    assert summary["series_name"].tolist() == ["0-4 yr"]
    assert summary["recommended_model_changed"].tolist() == [True]
    assert summary["discovery_structure_changed"].tolist() == [True]
    assert summary["age_prior_discovery_wins_test"].tolist() == [True]
    assert summary["no_age_prior_discovery_wins_test"].tolist() == [False]
