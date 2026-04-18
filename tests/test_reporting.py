from __future__ import annotations

from pathlib import Path

from src.evaluation.reporting import (
    collect_age_group_recommendations,
    collect_benchmark_model_summary,
    collect_benchmark_series_winners,
    write_benchmark_reports,
)
from src.utils.io import write_json


def _write_metrics(
    root: Path,
    series_name: str,
    model_name: str,
    test_mae: float,
    rolling_mean_mae: float,
    discovery_structure_name: str | None = None,
) -> None:
    metrics = {
        "series_name": series_name,
        "model_name": model_name,
        "test_metrics": {"mae": test_mae, "rmse": test_mae + 0.01, "smape": 0.1},
        "rolling_origin_summary": {"mean_mae": rolling_mean_mae, "mean_rmse": rolling_mean_mae + 0.02},
        "complexity": {"num_free_params": 4, "num_compartments": 3},
    }
    if discovery_structure_name is not None:
        metrics["best_spec"] = {
            "structure_name": discovery_structure_name,
            "fractional": False,
            "observation_map": "I",
        }

    write_json(metrics, root / series_name / model_name / "metrics.json")


def test_reporting_collects_summary_and_winners(tmp_path: Path) -> None:
    _write_metrics(tmp_path, "Overall", "deterministic_seir", test_mae=0.10, rolling_mean_mae=0.11)
    _write_metrics(tmp_path, "Overall", "constrained_structure_discovery", test_mae=0.09, rolling_mean_mae=0.12, discovery_structure_name="SIR")
    _write_metrics(tmp_path, "0-4 yr", "deterministic_seir", test_mae=0.20, rolling_mean_mae=0.22)
    _write_metrics(tmp_path, "0-4 yr", "constrained_structure_discovery", test_mae=0.18, rolling_mean_mae=0.17, discovery_structure_name="SEIRS")

    summary = collect_benchmark_model_summary(tmp_path)
    winners = collect_benchmark_series_winners(summary)

    assert sorted(summary["series_name"].unique().tolist()) == ["0-4 yr", "Overall"]
    assert "discovery_structure_name" in summary.columns
    assert winners.loc[winners["series_name"] == "Overall", "best_test_model"].item() == "constrained_structure_discovery"
    assert winners.loc[winners["series_name"] == "0-4 yr", "best_rolling_model"].item() == "constrained_structure_discovery"

    recommendations = collect_age_group_recommendations(summary)
    assert recommendations.loc[recommendations["series_name"] == "Overall", "recommended_model"].item() == "deterministic_seir"
    assert recommendations.loc[recommendations["series_name"] == "0-4 yr", "decision_type"].item() == "consensus"


def test_reporting_writes_summary_files_and_plots(tmp_path: Path) -> None:
    _write_metrics(tmp_path, "Overall", "deterministic_seir", test_mae=0.10, rolling_mean_mae=0.11)
    _write_metrics(tmp_path, "Overall", "probabilistic_seir", test_mae=0.12, rolling_mean_mae=0.13)
    _write_metrics(tmp_path, "Overall", "fractional_seir", test_mae=0.14, rolling_mean_mae=0.15)
    _write_metrics(tmp_path, "Overall", "constrained_structure_discovery", test_mae=0.09, rolling_mean_mae=0.12, discovery_structure_name="SIR")
    _write_metrics(tmp_path, "0-4 yr", "deterministic_seir", test_mae=0.20, rolling_mean_mae=0.22)
    _write_metrics(tmp_path, "0-4 yr", "probabilistic_seir", test_mae=0.19, rolling_mean_mae=0.21)
    _write_metrics(tmp_path, "0-4 yr", "fractional_seir", test_mae=0.25, rolling_mean_mae=0.26)
    _write_metrics(tmp_path, "0-4 yr", "constrained_structure_discovery", test_mae=0.18, rolling_mean_mae=0.17, discovery_structure_name="SEIRS")

    write_benchmark_reports(tmp_path)

    assert (tmp_path / "benchmark_model_summary.csv").exists()
    assert (tmp_path / "benchmark_series_winners.csv").exists()
    assert (tmp_path / "age_group_recommendation.csv").exists()
    assert (tmp_path / "benchmark_test_mae_heatmap.png").exists()
    assert (tmp_path / "benchmark_rolling_mae_bars.png").exists()
