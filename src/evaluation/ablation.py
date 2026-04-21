from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.io import ensure_dir


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"Required ablation input is missing: {path}")
    return pd.read_csv(path)


def _load_benchmark_bundle(artifact_root: Path) -> dict[str, pd.DataFrame]:
    summary = _read_csv(artifact_root / "benchmark_model_summary.csv")
    recommendations = _read_csv(artifact_root / "age_group_recommendation.csv")
    if "discovery_delay_weeks" not in summary.columns:
        summary["discovery_delay_weeks"] = None
    if "recommended_discovery_delay_weeks" not in recommendations.columns:
        recommendations["recommended_discovery_delay_weeks"] = None
    return {
        "summary": summary,
        "winners": _read_csv(artifact_root / "benchmark_series_winners.csv"),
        "recommendations": recommendations,
    }


def build_age_prior_ablation_summary(
    age_prior_root: Path,
    no_age_prior_root: Path,
) -> pd.DataFrame:
    age_prior = _load_benchmark_bundle(age_prior_root)
    no_age_prior = _load_benchmark_bundle(no_age_prior_root)

    recommendation_columns = [
        "series_name",
        "recommended_model",
        "decision_type",
        "recommended_discovery_structure_name",
        "recommended_discovery_fractional",
        "recommended_discovery_observation_map",
        "recommended_discovery_delay_weeks",
    ]

    def _discovery_subset(summary: pd.DataFrame, prefix: str) -> pd.DataFrame:
        frame = summary.loc[summary["model_name"] == "constrained_structure_discovery"].copy()
        columns = {
            "series_name": "series_name",
            "test_mae": f"{prefix}_discovery_test_mae",
            "rolling_mean_mae": f"{prefix}_discovery_rolling_mean_mae",
            "discovery_structure_name": f"{prefix}_discovery_structure_name",
            "discovery_fractional": f"{prefix}_discovery_fractional",
            "discovery_observation_map": f"{prefix}_discovery_observation_map",
            "discovery_delay_weeks": f"{prefix}_discovery_delay_weeks",
        }
        return frame.loc[:, columns.keys()].rename(columns=columns)

    age_prior_rows = (
        age_prior["winners"]
        .merge(age_prior["recommendations"].loc[:, recommendation_columns], on="series_name", how="left")
        .merge(_discovery_subset(age_prior["summary"], "age_prior"), on="series_name", how="left")
        .rename(
            columns={
                "best_test_model": "age_prior_best_test_model",
                "best_test_mae": "age_prior_best_test_mae",
                "best_rolling_model": "age_prior_best_rolling_model",
                "best_rolling_mean_mae": "age_prior_best_rolling_mean_mae",
                "recommended_model": "age_prior_recommended_model",
                "decision_type": "age_prior_decision_type",
                "recommended_discovery_structure_name": "age_prior_recommended_discovery_structure_name",
                "recommended_discovery_fractional": "age_prior_recommended_discovery_fractional",
                "recommended_discovery_observation_map": "age_prior_recommended_discovery_observation_map",
                "recommended_discovery_delay_weeks": "age_prior_recommended_discovery_delay_weeks",
            }
        )
    )

    no_age_prior_rows = (
        no_age_prior["winners"]
        .merge(no_age_prior["recommendations"].loc[:, recommendation_columns], on="series_name", how="left")
        .merge(_discovery_subset(no_age_prior["summary"], "no_age_prior"), on="series_name", how="left")
        .rename(
            columns={
                "best_test_model": "no_age_prior_best_test_model",
                "best_test_mae": "no_age_prior_best_test_mae",
                "best_rolling_model": "no_age_prior_best_rolling_model",
                "best_rolling_mean_mae": "no_age_prior_best_rolling_mean_mae",
                "recommended_model": "no_age_prior_recommended_model",
                "decision_type": "no_age_prior_decision_type",
                "recommended_discovery_structure_name": "no_age_prior_recommended_discovery_structure_name",
                "recommended_discovery_fractional": "no_age_prior_recommended_discovery_fractional",
                "recommended_discovery_observation_map": "no_age_prior_recommended_discovery_observation_map",
                "recommended_discovery_delay_weeks": "no_age_prior_recommended_discovery_delay_weeks",
            }
        )
    )

    comparison = age_prior_rows.merge(no_age_prior_rows, on="series_name", how="outer")
    age_recommended_delay = pd.to_numeric(
        comparison["age_prior_recommended_discovery_delay_weeks"], errors="coerce"
    ).fillna(0).astype(int)
    no_age_recommended_delay = pd.to_numeric(
        comparison["no_age_prior_recommended_discovery_delay_weeks"], errors="coerce"
    ).fillna(0).astype(int)
    age_discovery_delay = pd.to_numeric(
        comparison["age_prior_discovery_delay_weeks"], errors="coerce"
    ).fillna(0).astype(int)
    no_age_discovery_delay = pd.to_numeric(
        comparison["no_age_prior_discovery_delay_weeks"], errors="coerce"
    ).fillna(0).astype(int)
    age_recommended_signature = (
        comparison["age_prior_recommended_discovery_structure_name"].fillna("").astype(str)
        + "|obs="
        + comparison["age_prior_recommended_discovery_observation_map"].fillna("").astype(str)
        + "|delay="
        + age_recommended_delay.astype(str)
    )
    no_age_recommended_signature = (
        comparison["no_age_prior_recommended_discovery_structure_name"].fillna("").astype(str)
        + "|obs="
        + comparison["no_age_prior_recommended_discovery_observation_map"].fillna("").astype(str)
        + "|delay="
        + no_age_recommended_delay.astype(str)
    )
    age_discovery_signature = (
        comparison["age_prior_discovery_structure_name"].fillna("").astype(str)
        + "|obs="
        + comparison["age_prior_discovery_observation_map"].fillna("").astype(str)
        + "|delay="
        + age_discovery_delay.astype(str)
    )
    no_age_discovery_signature = (
        comparison["no_age_prior_discovery_structure_name"].fillna("").astype(str)
        + "|obs="
        + comparison["no_age_prior_discovery_observation_map"].fillna("").astype(str)
        + "|delay="
        + no_age_discovery_delay.astype(str)
    )

    comparison["recommended_model_changed"] = (
        comparison["age_prior_recommended_model"] != comparison["no_age_prior_recommended_model"]
    )
    comparison["recommended_discovery_structure_changed"] = (
        age_recommended_signature != no_age_recommended_signature
    )
    comparison["discovery_structure_changed"] = (
        age_discovery_signature != no_age_discovery_signature
    )
    comparison["age_prior_discovery_wins_test"] = (
        comparison["age_prior_best_test_model"] == "constrained_structure_discovery"
    )
    comparison["no_age_prior_discovery_wins_test"] = (
        comparison["no_age_prior_best_test_model"] == "constrained_structure_discovery"
    )
    comparison["age_prior_discovery_wins_rolling"] = (
        comparison["age_prior_best_rolling_model"] == "constrained_structure_discovery"
    )
    comparison["no_age_prior_discovery_wins_rolling"] = (
        comparison["no_age_prior_best_rolling_model"] == "constrained_structure_discovery"
    )
    comparison["discovery_test_mae_delta"] = (
        comparison["age_prior_discovery_test_mae"] - comparison["no_age_prior_discovery_test_mae"]
    )
    comparison["discovery_rolling_mae_delta"] = (
        comparison["age_prior_discovery_rolling_mean_mae"] - comparison["no_age_prior_discovery_rolling_mean_mae"]
    )

    return comparison.sort_values("series_name").reset_index(drop=True)


def write_age_prior_ablation_summary(
    age_prior_root: Path,
    no_age_prior_root: Path,
    output_path: Path,
) -> pd.DataFrame:
    summary = build_age_prior_ablation_summary(age_prior_root, no_age_prior_root)
    ensure_dir(output_path.parent)
    summary.to_csv(output_path, index=False)
    return summary
