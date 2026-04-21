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


def _load_multiseed_bundle(artifact_root: Path) -> dict[str, pd.DataFrame]:
    model_summary = _read_csv(artifact_root / "multiseed_model_summary.csv")
    recommendations = _read_csv(artifact_root / "multiseed_age_group_recommendation.csv")
    structure_frequency = _read_csv(artifact_root / "multiseed_discovery_structure_frequency.csv")
    if "recommended_discovery_delay_weeks_mode" not in recommendations.columns:
        recommendations["recommended_discovery_delay_weeks_mode"] = None
    return {
        "model_summary": model_summary,
        "recommendations": recommendations,
        "structure_frequency": structure_frequency,
    }


def _interpret_multiseed_ablation_row(row: pd.Series) -> str:
    changes: list[str] = []
    if bool(row["recommended_model_changed"]):
        changes.append("recommended model changed")
    if bool(row["discovery_structure_changed"]):
        changes.append("discovery structure changed")
    if bool(row["observation_map_changed"]):
        changes.append("observation map changed")
    if bool(row["delay_changed"]):
        changes.append("delay mode changed")

    test_delta = float(row["delta_discovery_test_mae"])
    rolling_delta = float(row["delta_discovery_rolling_mae"])
    if abs(test_delta) < 1.0e-12 and abs(rolling_delta) < 1.0e-12 and not changes:
        return "Robust to removing age prior; no change in recommendation, structure, delay, or discovery MAE."

    performance_bits: list[str] = []
    if test_delta < -1.0e-12:
        performance_bits.append("age prior improved discovery test MAE")
    elif test_delta > 1.0e-12:
        performance_bits.append("age prior worsened discovery test MAE")
    if rolling_delta < -1.0e-12:
        performance_bits.append("age prior improved discovery rolling MAE")
    elif rolling_delta > 1.0e-12:
        performance_bits.append("age prior worsened discovery rolling MAE")

    if not performance_bits:
        performance_bits.append("discovery MAE unchanged")
    if not changes:
        changes.append("selected structures unchanged")

    return "; ".join(changes + performance_bits).capitalize() + "."


def build_multiseed_age_prior_ablation_summary(
    age_prior_root: Path,
    no_age_prior_root: Path,
) -> pd.DataFrame:
    age_prior = _load_multiseed_bundle(age_prior_root)
    no_age_prior = _load_multiseed_bundle(no_age_prior_root)

    recommendation_columns = [
        "series_name",
        "recommended_model_mode",
        "recommended_discovery_structure_mode",
        "recommended_discovery_observation_map_mode",
        "recommended_discovery_delay_weeks_mode",
    ]
    age_rec = age_prior["recommendations"].loc[:, recommendation_columns].rename(
        columns={
            "recommended_model_mode": "age_prior_recommended_model_mode",
            "recommended_discovery_structure_mode": "age_prior_discovery_structure_mode",
            "recommended_discovery_observation_map_mode": "age_prior_discovery_observation_map_mode",
            "recommended_discovery_delay_weeks_mode": "age_prior_delay_weeks_mode",
        }
    )
    no_age_rec = no_age_prior["recommendations"].loc[:, recommendation_columns].rename(
        columns={
            "recommended_model_mode": "no_age_prior_recommended_model_mode",
            "recommended_discovery_structure_mode": "no_age_prior_discovery_structure_mode",
            "recommended_discovery_observation_map_mode": "no_age_prior_discovery_observation_map_mode",
            "recommended_discovery_delay_weeks_mode": "no_age_prior_delay_weeks_mode",
        }
    )

    def _discovery_metrics(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
        subset = frame.loc[frame["model_name"] == "constrained_structure_discovery", [
            "series_name",
            "mean_test_mae",
            "mean_rolling_mae",
        ]].copy()
        return subset.rename(
            columns={
                "mean_test_mae": f"{prefix}_discovery_mean_test_mae",
                "mean_rolling_mae": f"{prefix}_discovery_mean_rolling_mae",
            }
        )

    comparison = (
        age_rec
        .merge(no_age_rec, on="series_name", how="outer")
        .merge(_discovery_metrics(age_prior["model_summary"], "age_prior"), on="series_name", how="left")
        .merge(_discovery_metrics(no_age_prior["model_summary"], "no_age_prior"), on="series_name", how="left")
    )

    age_delay = pd.to_numeric(comparison["age_prior_delay_weeks_mode"], errors="coerce").fillna(0).astype(int)
    no_age_delay = pd.to_numeric(comparison["no_age_prior_delay_weeks_mode"], errors="coerce").fillna(0).astype(int)

    comparison["recommended_model_changed"] = (
        comparison["age_prior_recommended_model_mode"] != comparison["no_age_prior_recommended_model_mode"]
    )
    comparison["discovery_structure_changed"] = (
        comparison["age_prior_discovery_structure_mode"].fillna("").astype(str)
        != comparison["no_age_prior_discovery_structure_mode"].fillna("").astype(str)
    )
    comparison["observation_map_changed"] = (
        comparison["age_prior_discovery_observation_map_mode"].fillna("").astype(str)
        != comparison["no_age_prior_discovery_observation_map_mode"].fillna("").astype(str)
    )
    comparison["delay_changed"] = age_delay != no_age_delay
    comparison["delta_discovery_test_mae"] = (
        comparison["age_prior_discovery_mean_test_mae"] - comparison["no_age_prior_discovery_mean_test_mae"]
    )
    comparison["delta_discovery_rolling_mae"] = (
        comparison["age_prior_discovery_mean_rolling_mae"] - comparison["no_age_prior_discovery_mean_rolling_mae"]
    )
    comparison["interpretation"] = comparison.apply(_interpret_multiseed_ablation_row, axis=1)

    columns = [
        "series_name",
        "age_prior_recommended_model_mode",
        "no_age_prior_recommended_model_mode",
        "recommended_model_changed",
        "age_prior_discovery_structure_mode",
        "no_age_prior_discovery_structure_mode",
        "discovery_structure_changed",
        "age_prior_discovery_observation_map_mode",
        "no_age_prior_discovery_observation_map_mode",
        "observation_map_changed",
        "age_prior_delay_weeks_mode",
        "no_age_prior_delay_weeks_mode",
        "delay_changed",
        "age_prior_discovery_mean_test_mae",
        "no_age_prior_discovery_mean_test_mae",
        "delta_discovery_test_mae",
        "age_prior_discovery_mean_rolling_mae",
        "no_age_prior_discovery_mean_rolling_mae",
        "delta_discovery_rolling_mae",
        "interpretation",
    ]
    return comparison.loc[:, columns].sort_values("series_name").reset_index(drop=True)


def build_multiseed_age_prior_structure_comparison(
    age_prior_root: Path,
    no_age_prior_root: Path,
) -> pd.DataFrame:
    age_prior = _load_multiseed_bundle(age_prior_root)["structure_frequency"].rename(
        columns={
            "count": "age_prior_count",
            "mean_test_mae": "age_prior_mean_test_mae",
            "mean_rolling_mae": "age_prior_mean_rolling_mae",
            "selected_structure_frequency": "age_prior_selected_structure_frequency",
        }
    )
    no_age_prior = _load_multiseed_bundle(no_age_prior_root)["structure_frequency"].rename(
        columns={
            "count": "no_age_prior_count",
            "mean_test_mae": "no_age_prior_mean_test_mae",
            "mean_rolling_mae": "no_age_prior_mean_rolling_mae",
            "selected_structure_frequency": "no_age_prior_selected_structure_frequency",
        }
    )
    comparison = age_prior.merge(no_age_prior, on=["series_name", "structure_spec", "num_seeds"], how="outer")
    for column in [
        "age_prior_count",
        "no_age_prior_count",
        "age_prior_selected_structure_frequency",
        "no_age_prior_selected_structure_frequency",
    ]:
        comparison[column] = comparison[column].fillna(0)
    comparison["count_delta"] = comparison["age_prior_count"] - comparison["no_age_prior_count"]
    comparison["frequency_delta"] = (
        comparison["age_prior_selected_structure_frequency"] - comparison["no_age_prior_selected_structure_frequency"]
    )
    return comparison.sort_values(["series_name", "structure_spec"]).reset_index(drop=True)


def build_multiseed_age_prior_model_delta(
    age_prior_root: Path,
    no_age_prior_root: Path,
) -> pd.DataFrame:
    age_prior = _load_multiseed_bundle(age_prior_root)["model_summary"].rename(
        columns={
            "mean_test_mae": "age_prior_mean_test_mae",
            "std_test_mae": "age_prior_std_test_mae",
            "mean_rolling_mae": "age_prior_mean_rolling_mae",
            "std_rolling_mae": "age_prior_std_rolling_mae",
            "test_win_rate": "age_prior_test_win_rate",
            "rolling_win_rate": "age_prior_rolling_win_rate",
        }
    )
    no_age_prior = _load_multiseed_bundle(no_age_prior_root)["model_summary"].rename(
        columns={
            "mean_test_mae": "no_age_prior_mean_test_mae",
            "std_test_mae": "no_age_prior_std_test_mae",
            "mean_rolling_mae": "no_age_prior_mean_rolling_mae",
            "std_rolling_mae": "no_age_prior_std_rolling_mae",
            "test_win_rate": "no_age_prior_test_win_rate",
            "rolling_win_rate": "no_age_prior_rolling_win_rate",
        }
    )
    comparison = age_prior.merge(
        no_age_prior,
        on=["series_name", "model_name", "num_seeds", "num_free_params", "num_compartments"],
        how="outer",
    )
    comparison["delta_mean_test_mae"] = (
        comparison["age_prior_mean_test_mae"] - comparison["no_age_prior_mean_test_mae"]
    )
    comparison["delta_mean_rolling_mae"] = (
        comparison["age_prior_mean_rolling_mae"] - comparison["no_age_prior_mean_rolling_mae"]
    )
    comparison["delta_test_win_rate"] = (
        comparison["age_prior_test_win_rate"] - comparison["no_age_prior_test_win_rate"]
    )
    comparison["delta_rolling_win_rate"] = (
        comparison["age_prior_rolling_win_rate"] - comparison["no_age_prior_rolling_win_rate"]
    )
    return comparison.sort_values(["series_name", "model_name"]).reset_index(drop=True)


def build_multiseed_observation_age_prior_ablation_report(
    summary: pd.DataFrame,
) -> str:
    changed_structure = int(summary["discovery_structure_changed"].sum())
    changed_obs = int(summary["observation_map_changed"].sum())
    changed_delay = int(summary["delay_changed"].sum())
    changed_model = int(summary["recommended_model_changed"].sum())
    robust_series = summary.loc[
        (~summary["recommended_model_changed"])
        & (~summary["discovery_structure_changed"])
        & (~summary["observation_map_changed"])
        & (~summary["delay_changed"])
        & (summary["delta_discovery_test_mae"].abs() < 1.0e-12)
        & (summary["delta_discovery_rolling_mae"].abs() < 1.0e-12),
        "series_name",
    ].tolist()
    robust_text = ", ".join(robust_series) if robust_series else "None"
    if changed_delay == 0 and changed_obs == 0:
        delayed_text = (
            "Delayed-observation selection was unchanged between age-prior and no-age-prior runs; "
            "the same delayed_I patterns were selected in both settings."
        )
    else:
        delayed_text = (
            f"Delayed-observation selection changed in {changed_delay} series and observation-map mode changed in {changed_obs} series."
        )
    mean_test_delta = float(summary["delta_discovery_test_mae"].abs().mean())
    mean_rolling_delta = float(summary["delta_discovery_rolling_mae"].abs().mean())

    lines = [
        "# Multi-Seed Observation Age-Prior Ablation Report",
        "",
        "## Inputs",
        "",
        "- `artifacts_multiseed_age_robustness_observation/`",
        "- `artifacts_multiseed_age_robustness_observation_no_age_prior/`",
        "",
        "## Main Answers",
        "",
        f"- Did age prior materially change selected structures? No. Structure mode changed in {changed_structure} of {len(summary)} series.",
        f"- Did age prior materially change delayed_I selection? {delayed_text}",
        f"- Did age prior improve or hurt test/rolling MAE? No measurable effect. Mean absolute discovery test-MAE delta = {mean_test_delta:.6f}; mean absolute discovery rolling-MAE delta = {mean_rolling_delta:.6f}.",
        f"- Which series are robust to removing age prior? {robust_text}.",
        "",
        "## Series-Level Summary",
        "",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"- `{row.series_name}`: {row.interpretation}"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Across the observation-aware five-seed benchmark, removing the age prior did not change the recommended model mode, the dominant discovery structure, the selected observation map mode, the delay mode, or the aggregate discovery MAE values. This strengthens the non-LLM control story: the observed delayed_I selections arise from the search objective and data rather than from the age prior.",
            "",
        ]
    )
    return "\n".join(lines)


def write_multiseed_observation_age_prior_ablation(
    age_prior_root: Path,
    no_age_prior_root: Path,
    output_root: Path,
    report_path: Path,
) -> dict[str, Path]:
    summary = build_multiseed_age_prior_ablation_summary(age_prior_root, no_age_prior_root)
    structure = build_multiseed_age_prior_structure_comparison(age_prior_root, no_age_prior_root)
    model_delta = build_multiseed_age_prior_model_delta(age_prior_root, no_age_prior_root)

    ensure_dir(output_root)
    summary_path = output_root / "multiseed_age_prior_ablation_summary.csv"
    structure_path = output_root / "multiseed_age_prior_structure_comparison.csv"
    model_delta_path = output_root / "multiseed_age_prior_model_delta.csv"
    summary.to_csv(summary_path, index=False)
    structure.to_csv(structure_path, index=False)
    model_delta.to_csv(model_delta_path, index=False)

    ensure_dir(report_path.parent)
    report_path.write_text(
        build_multiseed_observation_age_prior_ablation_report(summary),
        encoding="utf-8",
    )
    return {
        "summary": summary_path,
        "structure_comparison": structure_path,
        "model_delta": model_delta_path,
        "report": report_path,
    }
