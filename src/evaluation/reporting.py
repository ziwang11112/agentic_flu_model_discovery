from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.plotting.robustness_plots import plot_metric_bars, plot_metric_heatmap


MODEL_DIRECTORIES = {
    "deterministic_seir",
    "probabilistic_seir",
    "fractional_seir",
    "constrained_structure_discovery",
}


def collect_benchmark_model_summary(artifact_root: Path) -> pd.DataFrame:
    """Collect per-series per-model metrics from benchmark artifacts."""
    records: list[dict[str, object]] = []

    for metrics_path in sorted(artifact_root.glob("**/metrics.json")):
        model_dir = metrics_path.parent.name
        if model_dir not in MODEL_DIRECTORIES:
            continue

        data = json.loads(metrics_path.read_text(encoding="utf-8"))
        row: dict[str, object] = {
            "series_name": data["series_name"],
            "model_name": data["model_name"],
            "test_mae": data["test_metrics"]["mae"],
            "test_rmse": data["test_metrics"]["rmse"],
            "test_smape": data["test_metrics"]["smape"],
            "rolling_mean_mae": data["rolling_origin_summary"]["mean_mae"],
            "rolling_mean_rmse": data["rolling_origin_summary"]["mean_rmse"],
            "num_free_params": data["complexity"]["num_free_params"],
            "num_compartments": data["complexity"]["num_compartments"],
            "artifact_dir": str(metrics_path.parent),
        }

        best_spec = data.get("best_spec")
        if best_spec is not None:
            row["discovery_structure_name"] = best_spec["structure_name"]
            row["discovery_fractional"] = best_spec["fractional"]
            row["discovery_observation_map"] = best_spec["observation_map"]
        else:
            row["discovery_structure_name"] = None
            row["discovery_fractional"] = None
            row["discovery_observation_map"] = None

        records.append(row)

    summary = pd.DataFrame.from_records(records)
    if summary.empty:
        return summary

    summary = summary.sort_values(["series_name", "test_mae", "rolling_mean_mae", "model_name"]).reset_index(drop=True)
    return summary


def collect_benchmark_series_winners(summary: pd.DataFrame) -> pd.DataFrame:
    """Summarize best models per series for point and rolling metrics."""
    winners: list[dict[str, object]] = []

    for series_name, subset in summary.groupby("series_name"):
        best_test = subset.sort_values(["test_mae", "test_rmse"]).iloc[0]
        best_rolling = subset.sort_values(["rolling_mean_mae", "rolling_mean_rmse"]).iloc[0]
        winners.append(
            {
                "series_name": series_name,
                "best_test_model": best_test["model_name"],
                "best_test_mae": best_test["test_mae"],
                "best_rolling_model": best_rolling["model_name"],
                "best_rolling_mean_mae": best_rolling["rolling_mean_mae"],
            }
        )

    return pd.DataFrame(winners).sort_values("series_name").reset_index(drop=True)


def collect_age_group_recommendations(summary: pd.DataFrame) -> pd.DataFrame:
    """Build one recommendation row per series using balanced test/rolling ranks."""
    recommendations: list[dict[str, object]] = []

    for series_name, subset in summary.groupby("series_name"):
        ranked = subset.copy()
        ranked["test_rank"] = ranked["test_mae"].rank(method="dense", ascending=True)
        ranked["rolling_rank"] = ranked["rolling_mean_mae"].rank(method="dense", ascending=True)
        ranked["rank_score"] = ranked["test_rank"] + ranked["rolling_rank"]
        recommended = ranked.sort_values(
            ["rank_score", "rolling_rank", "test_rank", "rolling_mean_mae", "test_mae", "model_name"]
        ).iloc[0]
        best_test = ranked.sort_values(["test_mae", "test_rmse", "model_name"]).iloc[0]
        best_rolling = ranked.sort_values(["rolling_mean_mae", "rolling_mean_rmse", "model_name"]).iloc[0]

        if best_test["model_name"] == best_rolling["model_name"] == recommended["model_name"]:
            decision_type = "consensus"
        elif recommended["model_name"] == best_rolling["model_name"]:
            decision_type = "stability_preferred"
        elif recommended["model_name"] == best_test["model_name"]:
            decision_type = "test_preferred"
        else:
            decision_type = "balanced_tradeoff"

        recommendations.append(
            {
                "series_name": series_name,
                "recommended_model": recommended["model_name"],
                "decision_type": decision_type,
                "recommended_test_rank": int(recommended["test_rank"]),
                "recommended_rolling_rank": int(recommended["rolling_rank"]),
                "rank_score": float(recommended["rank_score"]),
                "best_test_model": best_test["model_name"],
                "best_test_mae": best_test["test_mae"],
                "best_rolling_model": best_rolling["model_name"],
                "best_rolling_mean_mae": best_rolling["rolling_mean_mae"],
                "recommended_discovery_structure_name": recommended["discovery_structure_name"],
                "recommended_discovery_fractional": recommended["discovery_fractional"],
                "recommended_discovery_observation_map": recommended["discovery_observation_map"],
            }
        )

    return pd.DataFrame(recommendations).sort_values("series_name").reset_index(drop=True)


def write_benchmark_reports(artifact_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Write benchmark-wide summary tables and cross-series plots."""
    summary = collect_benchmark_model_summary(artifact_root)
    if summary.empty:
        raise RuntimeError(f"No benchmark metrics found under {artifact_root}")

    winners = collect_benchmark_series_winners(summary)
    recommendations = collect_age_group_recommendations(summary)
    summary.to_csv(artifact_root / "benchmark_model_summary.csv", index=False)
    winners.to_csv(artifact_root / "benchmark_series_winners.csv", index=False)
    recommendations.to_csv(artifact_root / "age_group_recommendation.csv", index=False)

    if summary["series_name"].nunique() > 1:
        plot_metric_heatmap(
            summary=summary,
            metric_column="test_mae",
            title="Age-Group Benchmark | Test MAE",
            path=artifact_root / "benchmark_test_mae_heatmap.png",
        )
        plot_metric_heatmap(
            summary=summary,
            metric_column="rolling_mean_mae",
            title="Age-Group Benchmark | Rolling Mean MAE",
            path=artifact_root / "benchmark_rolling_mae_heatmap.png",
        )
        plot_metric_bars(
            summary=summary,
            metric_column="test_mae",
            title="Age-Group Benchmark | Test MAE",
            path=artifact_root / "benchmark_test_mae_bars.png",
        )
        plot_metric_bars(
            summary=summary,
            metric_column="rolling_mean_mae",
            title="Age-Group Benchmark | Rolling Mean MAE",
            path=artifact_root / "benchmark_rolling_mae_bars.png",
        )

    return summary, winners, recommendations
