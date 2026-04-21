from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluation.multiseed import (
    build_multiseed_age_group_recommendation,
    build_multiseed_discovery_structure_frequency,
    build_multiseed_model_summary,
    write_multiseed_outputs,
)


def _write_seed_bundle(root: Path, rows: dict[str, list[dict[str, object]]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows["summary"]).to_csv(root / "benchmark_model_summary.csv", index=False)
    pd.DataFrame(rows["winners"]).to_csv(root / "benchmark_series_winners.csv", index=False)
    pd.DataFrame(rows["recommendations"]).to_csv(root / "age_group_recommendation.csv", index=False)


def test_multiseed_model_summary_computes_win_rates(tmp_path: Path) -> None:
    seed0 = tmp_path / "seed0"
    seed1 = tmp_path / "seed1"
    base_summary = [
        {
            "series_name": "Overall",
            "model_name": "deterministic_seir",
            "test_mae": 0.10,
            "rolling_mean_mae": 0.12,
            "num_free_params": 8,
            "num_compartments": 4,
            "discovery_structure_name": None,
            "discovery_fractional": None,
            "discovery_observation_map": None,
            "discovery_delay_weeks": None,
        },
        {
            "series_name": "Overall",
            "model_name": "constrained_structure_discovery",
            "test_mae": 0.09,
            "rolling_mean_mae": 0.11,
            "num_free_params": 9,
            "num_compartments": 3,
            "discovery_structure_name": "SIR",
            "discovery_fractional": False,
            "discovery_observation_map": "I",
            "discovery_delay_weeks": 0,
        },
    ]
    _write_seed_bundle(
        seed0,
        {
            "summary": base_summary,
            "winners": [
                {
                    "series_name": "Overall",
                    "best_test_model": "constrained_structure_discovery",
                    "best_test_mae": 0.09,
                    "best_rolling_model": "constrained_structure_discovery",
                    "best_rolling_mean_mae": 0.11,
                }
            ],
            "recommendations": [
                {
                    "series_name": "Overall",
                    "recommended_model": "constrained_structure_discovery",
                    "decision_type": "consensus",
                    "best_test_model": "constrained_structure_discovery",
                    "best_test_mae": 0.09,
                    "best_rolling_model": "constrained_structure_discovery",
                    "best_rolling_mean_mae": 0.11,
                    "recommended_discovery_structure_name": "SIR",
                    "recommended_discovery_fractional": False,
                    "recommended_discovery_observation_map": "I",
                    "recommended_discovery_delay_weeks": 0,
                }
            ],
        },
    )
    summary_seed1 = [dict(base_summary[0], test_mae=0.08, rolling_mean_mae=0.10), dict(base_summary[1], test_mae=0.11, rolling_mean_mae=0.13)]
    _write_seed_bundle(
        seed1,
        {
            "summary": summary_seed1,
            "winners": [
                {
                    "series_name": "Overall",
                    "best_test_model": "deterministic_seir",
                    "best_test_mae": 0.08,
                    "best_rolling_model": "deterministic_seir",
                    "best_rolling_mean_mae": 0.10,
                }
            ],
            "recommendations": [
                {
                    "series_name": "Overall",
                    "recommended_model": "deterministic_seir",
                    "decision_type": "consensus",
                    "best_test_model": "deterministic_seir",
                    "best_test_mae": 0.08,
                    "best_rolling_model": "deterministic_seir",
                    "best_rolling_mean_mae": 0.10,
                    "recommended_discovery_structure_name": None,
                    "recommended_discovery_fractional": None,
                    "recommended_discovery_observation_map": None,
                    "recommended_discovery_delay_weeks": None,
                }
            ],
        },
    )

    summary = build_multiseed_model_summary({0: seed0, 1: seed1})
    discovery_row = summary.loc[summary["model_name"] == "constrained_structure_discovery"].iloc[0]
    deterministic_row = summary.loc[summary["model_name"] == "deterministic_seir"].iloc[0]
    assert discovery_row["test_win_rate"] == 0.5
    assert discovery_row["rolling_win_rate"] == 0.5
    assert deterministic_row["test_win_rate"] == 0.5
    assert deterministic_row["rolling_win_rate"] == 0.5


def test_multiseed_age_group_recommendation_uses_mode_frequency(tmp_path: Path) -> None:
    seed0 = tmp_path / "seed0"
    seed1 = tmp_path / "seed1"
    common_summary = [
        {
            "series_name": "Overall",
            "model_name": "deterministic_seir",
            "test_mae": 0.1,
            "rolling_mean_mae": 0.1,
            "num_free_params": 8,
            "num_compartments": 4,
            "discovery_structure_name": None,
            "discovery_fractional": None,
            "discovery_observation_map": None,
            "discovery_delay_weeks": None,
        }
    ]
    common_winners = [
        {
            "series_name": "Overall",
            "best_test_model": "deterministic_seir",
            "best_test_mae": 0.1,
            "best_rolling_model": "deterministic_seir",
            "best_rolling_mean_mae": 0.1,
        }
    ]
    _write_seed_bundle(
        seed0,
        {
            "summary": common_summary,
            "winners": common_winners,
            "recommendations": [
                {
                    "series_name": "Overall",
                    "recommended_model": "deterministic_seir",
                    "decision_type": "consensus",
                    "best_test_model": "deterministic_seir",
                    "best_test_mae": 0.1,
                    "best_rolling_model": "deterministic_seir",
                    "best_rolling_mean_mae": 0.1,
                    "recommended_discovery_structure_name": None,
                    "recommended_discovery_fractional": None,
                    "recommended_discovery_observation_map": None,
                    "recommended_discovery_delay_weeks": None,
                }
            ],
        },
    )
    _write_seed_bundle(
        seed1,
        {
            "summary": common_summary,
            "winners": common_winners,
            "recommendations": [
                {
                    "series_name": "Overall",
                    "recommended_model": "deterministic_seir",
                    "decision_type": "stability_preferred",
                    "best_test_model": "deterministic_seir",
                    "best_test_mae": 0.1,
                    "best_rolling_model": "deterministic_seir",
                    "best_rolling_mean_mae": 0.1,
                    "recommended_discovery_structure_name": "SIR",
                    "recommended_discovery_fractional": False,
                    "recommended_discovery_observation_map": "I",
                    "recommended_discovery_delay_weeks": 0,
                }
            ],
        },
    )

    summary = build_multiseed_age_group_recommendation({0: seed0, 1: seed1})
    row = summary.iloc[0]
    assert row["recommended_model_mode"] == "deterministic_seir"
    assert row["recommended_model_frequency"] == 1.0
    assert row["decision_type_mode"] == "consensus"
    assert row["decision_type_frequency"] == 0.5


def test_multiseed_discovery_structure_frequency_counts_selection(tmp_path: Path) -> None:
    seed0 = tmp_path / "seed0"
    seed1 = tmp_path / "seed1"
    _write_seed_bundle(
        seed0,
        {
            "summary": [
                {
                    "series_name": "Overall",
                    "model_name": "constrained_structure_discovery",
                    "test_mae": 0.1,
                    "rolling_mean_mae": 0.1,
                    "num_free_params": 9,
                    "num_compartments": 3,
                    "discovery_structure_name": "SIR",
                    "discovery_fractional": False,
                    "discovery_observation_map": "I",
                    "discovery_delay_weeks": 0,
                }
            ],
            "winners": [
                {
                    "series_name": "Overall",
                    "best_test_model": "constrained_structure_discovery",
                    "best_test_mae": 0.1,
                    "best_rolling_model": "constrained_structure_discovery",
                    "best_rolling_mean_mae": 0.1,
                }
            ],
            "recommendations": [
                {
                    "series_name": "Overall",
                    "recommended_model": "constrained_structure_discovery",
                    "decision_type": "consensus",
                    "best_test_model": "constrained_structure_discovery",
                    "best_test_mae": 0.1,
                    "best_rolling_model": "constrained_structure_discovery",
                    "best_rolling_mean_mae": 0.1,
                    "recommended_discovery_structure_name": "SIR",
                    "recommended_discovery_fractional": False,
                    "recommended_discovery_observation_map": "I",
                    "recommended_discovery_delay_weeks": 0,
                }
            ],
        },
    )
    _write_seed_bundle(
        seed1,
        {
            "summary": [
                {
                    "series_name": "Overall",
                    "model_name": "constrained_structure_discovery",
                    "test_mae": 0.2,
                    "rolling_mean_mae": 0.2,
                    "num_free_params": 10,
                    "num_compartments": 4,
                    "discovery_structure_name": "SEIRS",
                    "discovery_fractional": True,
                    "discovery_observation_map": "I",
                    "discovery_delay_weeks": 0,
                }
            ],
            "winners": [
                {
                    "series_name": "Overall",
                    "best_test_model": "constrained_structure_discovery",
                    "best_test_mae": 0.2,
                    "best_rolling_model": "constrained_structure_discovery",
                    "best_rolling_mean_mae": 0.2,
                }
            ],
            "recommendations": [
                {
                    "series_name": "Overall",
                    "recommended_model": "constrained_structure_discovery",
                    "decision_type": "consensus",
                    "best_test_model": "constrained_structure_discovery",
                    "best_test_mae": 0.2,
                    "best_rolling_model": "constrained_structure_discovery",
                    "best_rolling_mean_mae": 0.2,
                    "recommended_discovery_structure_name": "SEIRS",
                    "recommended_discovery_fractional": True,
                    "recommended_discovery_observation_map": "I",
                    "recommended_discovery_delay_weeks": 0,
                }
            ],
        },
    )

    summary = build_multiseed_discovery_structure_frequency({0: seed0, 1: seed1})
    assert set(summary["structure_spec"]) == {"SEIRS|fractional=1|obs=I", "SIR|fractional=0|obs=I"}
    assert set(summary["selected_structure_frequency"]) == {0.5}


def test_write_multiseed_outputs_creates_csvs_and_plots(tmp_path: Path) -> None:
    seed0 = tmp_path / "seed0"
    seed1 = tmp_path / "seed1"
    rows = {
        "summary": [
            {
                "series_name": "Overall",
                "model_name": "deterministic_seir",
                "test_mae": 0.1,
                "rolling_mean_mae": 0.1,
                "num_free_params": 8,
                "num_compartments": 4,
                "discovery_structure_name": None,
                "discovery_fractional": None,
                "discovery_observation_map": None,
                "discovery_delay_weeks": None,
            }
        ],
        "winners": [
            {
                "series_name": "Overall",
                "best_test_model": "deterministic_seir",
                "best_test_mae": 0.1,
                "best_rolling_model": "deterministic_seir",
                "best_rolling_mean_mae": 0.1,
            }
        ],
        "recommendations": [
            {
                "series_name": "Overall",
                "recommended_model": "deterministic_seir",
                "decision_type": "consensus",
                "best_test_model": "deterministic_seir",
                "best_test_mae": 0.1,
                "best_rolling_model": "deterministic_seir",
                "best_rolling_mean_mae": 0.1,
                "recommended_discovery_structure_name": None,
                "recommended_discovery_fractional": None,
                "recommended_discovery_observation_map": None,
                "recommended_discovery_delay_weeks": None,
            }
        ],
    }
    _write_seed_bundle(seed0, rows)
    _write_seed_bundle(seed1, rows)
    outputs = write_multiseed_outputs({0: seed0, 1: seed1}, tmp_path / "out")
    for path in outputs.values():
        assert path.exists()
