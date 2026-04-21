from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluation.ablation import (
    build_age_prior_ablation_summary,
    build_multiseed_age_prior_ablation_summary,
    build_multiseed_age_prior_model_delta,
    build_multiseed_age_prior_structure_comparison,
)


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
                "recommended_discovery_delay_weeks": 0,
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
                "discovery_delay_weeks": 0,
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
                "recommended_discovery_delay_weeks": "",
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
                "discovery_delay_weeks": 0,
            }
        ],
    )

    summary = build_age_prior_ablation_summary(age_prior_root, no_age_prior_root)

    assert summary["series_name"].tolist() == ["0-4 yr"]
    assert summary["recommended_model_changed"].tolist() == [True]
    assert summary["discovery_structure_changed"].tolist() == [True]
    assert summary["age_prior_discovery_wins_test"].tolist() == [True]
    assert summary["no_age_prior_discovery_wins_test"].tolist() == [False]


def _write_multiseed_bundle(
    root: Path,
    recommendations: list[dict[str, object]],
    model_summary: list[dict[str, object]],
    structure_frequency: list[dict[str, object]],
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(recommendations).to_csv(root / "multiseed_age_group_recommendation.csv", index=False)
    pd.DataFrame(model_summary).to_csv(root / "multiseed_model_summary.csv", index=False)
    pd.DataFrame(structure_frequency).to_csv(root / "multiseed_discovery_structure_frequency.csv", index=False)


def test_build_multiseed_observation_age_prior_ablation_outputs(tmp_path: Path) -> None:
    age_prior_root = tmp_path / "age_prior_multiseed"
    no_age_prior_root = tmp_path / "no_age_prior_multiseed"

    recommendations = [
        {
            "series_name": "0-4 yr",
            "num_seeds": 5,
            "recommended_model_mode": "constrained_structure_discovery",
            "recommended_model_frequency": 1.0,
            "best_test_model_mode": "constrained_structure_discovery",
            "best_test_model_frequency": 1.0,
            "best_rolling_model_mode": "constrained_structure_discovery",
            "best_rolling_model_frequency": 1.0,
            "decision_type_mode": "consensus",
            "decision_type_frequency": 1.0,
            "recommended_discovery_structure_mode": "SEIRS",
            "recommended_discovery_structure_frequency": 1.0,
            "recommended_discovery_fractional_mode": False,
            "recommended_discovery_fractional_frequency": 0.8,
            "recommended_discovery_observation_map_mode": "I",
            "recommended_discovery_observation_map_frequency": 0.6,
            "recommended_discovery_delay_weeks_mode": 0,
            "recommended_discovery_delay_weeks_frequency": 0.6,
        }
    ]
    model_summary = [
        {
            "series_name": "0-4 yr",
            "model_name": "constrained_structure_discovery",
            "num_seeds": 5,
            "mean_test_mae": 0.0905961813,
            "std_test_mae": 0.0010,
            "mean_rolling_mae": 0.1233439122,
            "std_rolling_mae": 0.0159,
            "test_win_count": 5,
            "rolling_win_count": 5,
            "num_free_params": 9,
            "num_compartments": 4,
            "test_win_rate": 1.0,
            "rolling_win_rate": 1.0,
        }
    ]
    structure_frequency = [
        {
            "series_name": "0-4 yr",
            "structure_spec": "SEIRS|fractional=0|obs=I",
            "count": 3,
            "mean_test_mae": 0.0911181662,
            "mean_rolling_mae": 0.1222348437,
            "num_seeds": 5,
            "selected_structure_frequency": 0.6,
        }
    ]

    _write_multiseed_bundle(age_prior_root, recommendations, model_summary, structure_frequency)
    _write_multiseed_bundle(no_age_prior_root, recommendations, model_summary, structure_frequency)

    summary = build_multiseed_age_prior_ablation_summary(age_prior_root, no_age_prior_root)
    structure = build_multiseed_age_prior_structure_comparison(age_prior_root, no_age_prior_root)
    model_delta = build_multiseed_age_prior_model_delta(age_prior_root, no_age_prior_root)

    assert summary["recommended_model_changed"].tolist() == [False]
    assert summary["discovery_structure_changed"].tolist() == [False]
    assert summary["observation_map_changed"].tolist() == [False]
    assert summary["delay_changed"].tolist() == [False]
    assert summary["delta_discovery_test_mae"].tolist() == [0.0]
    assert summary["delta_discovery_rolling_mae"].tolist() == [0.0]
    assert "Robust to removing age prior" in summary.loc[0, "interpretation"]

    assert structure["count_delta"].tolist() == [0]
    assert structure["frequency_delta"].tolist() == [0.0]

    assert model_delta["delta_mean_test_mae"].tolist() == [0.0]
    assert model_delta["delta_mean_rolling_mae"].tolist() == [0.0]
