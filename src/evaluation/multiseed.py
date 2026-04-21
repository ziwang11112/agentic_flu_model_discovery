from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from src.plotting.multiseed_plots import plot_multiseed_errorbars
from src.utils.io import ensure_dir


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"Required multi-seed input is missing: {path}")
    return pd.read_csv(path)


def _stable_mode(values: pd.Series) -> tuple[object, int]:
    cleaned = [value for value in values.tolist() if pd.notna(value)]
    if not cleaned:
        return None, 0
    counts = Counter(cleaned)
    winner, count = sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))[0]
    return winner, count


def _seed_bundle(seed: int, artifact_root: Path) -> dict[str, pd.DataFrame]:
    return {
        "seed": seed,
        "summary": _read_csv(artifact_root / "benchmark_model_summary.csv"),
        "winners": _read_csv(artifact_root / "benchmark_series_winners.csv"),
        "recommendations": _read_csv(artifact_root / "age_group_recommendation.csv"),
    }


def load_multiseed_tables(seed_artifact_roots: dict[int, Path]) -> dict[str, pd.DataFrame]:
    summary_frames: list[pd.DataFrame] = []
    winner_frames: list[pd.DataFrame] = []
    recommendation_frames: list[pd.DataFrame] = []

    for seed, artifact_root in sorted(seed_artifact_roots.items()):
        bundle = _seed_bundle(seed, artifact_root)
        if "discovery_delay_weeks" not in bundle["summary"].columns:
            bundle["summary"]["discovery_delay_weeks"] = None
        if "recommended_discovery_delay_weeks" not in bundle["recommendations"].columns:
            bundle["recommendations"]["recommended_discovery_delay_weeks"] = None
        summary_frames.append(bundle["summary"].assign(seed=seed))
        winner_frames.append(bundle["winners"].assign(seed=seed))
        recommendation_frames.append(bundle["recommendations"].assign(seed=seed))

    return {
        "summary": pd.concat(summary_frames, ignore_index=True),
        "winners": pd.concat(winner_frames, ignore_index=True),
        "recommendations": pd.concat(recommendation_frames, ignore_index=True),
    }


def build_multiseed_model_summary(seed_artifact_roots: dict[int, Path]) -> pd.DataFrame:
    tables = load_multiseed_tables(seed_artifact_roots)
    summary = tables["summary"]
    winners = tables["winners"]

    test_winners = winners.loc[:, ["seed", "series_name", "best_test_model"]].rename(
        columns={"best_test_model": "model_name"}
    )
    test_winners["test_win"] = 1
    rolling_winners = winners.loc[:, ["seed", "series_name", "best_rolling_model"]].rename(
        columns={"best_rolling_model": "model_name"}
    )
    rolling_winners["rolling_win"] = 1

    summary = summary.merge(test_winners, on=["seed", "series_name", "model_name"], how="left")
    summary = summary.merge(rolling_winners, on=["seed", "series_name", "model_name"], how="left")
    summary["test_win"] = summary["test_win"].fillna(0).astype(int)
    summary["rolling_win"] = summary["rolling_win"].fillna(0).astype(int)

    grouped = (
        summary.groupby(["series_name", "model_name"], as_index=False)
        .agg(
            num_seeds=("seed", "nunique"),
            mean_test_mae=("test_mae", "mean"),
            std_test_mae=("test_mae", lambda values: float(pd.Series(values).std(ddof=0))),
            mean_rolling_mae=("rolling_mean_mae", "mean"),
            std_rolling_mae=("rolling_mean_mae", lambda values: float(pd.Series(values).std(ddof=0))),
            test_win_count=("test_win", "sum"),
            rolling_win_count=("rolling_win", "sum"),
            num_free_params=("num_free_params", "first"),
            num_compartments=("num_compartments", "first"),
        )
    )
    grouped["test_win_rate"] = grouped["test_win_count"] / grouped["num_seeds"]
    grouped["rolling_win_rate"] = grouped["rolling_win_count"] / grouped["num_seeds"]
    return grouped.sort_values(["series_name", "mean_test_mae", "mean_rolling_mae", "model_name"]).reset_index(drop=True)


def build_multiseed_age_group_recommendation(seed_artifact_roots: dict[int, Path]) -> pd.DataFrame:
    recommendations = load_multiseed_tables(seed_artifact_roots)["recommendations"]
    rows: list[dict[str, object]] = []

    for series_name, subset in recommendations.groupby("series_name"):
        recommended_model, recommended_count = _stable_mode(subset["recommended_model"])
        best_test_model, best_test_count = _stable_mode(subset["best_test_model"])
        best_rolling_model, best_rolling_count = _stable_mode(subset["best_rolling_model"])
        decision_type, decision_count = _stable_mode(subset["decision_type"])
        recommended_structure, structure_count = _stable_mode(subset["recommended_discovery_structure_name"])
        fractional_mode, fractional_count = _stable_mode(subset["recommended_discovery_fractional"])
        observation_mode, observation_count = _stable_mode(subset["recommended_discovery_observation_map"])
        delay_mode, delay_count = _stable_mode(subset["recommended_discovery_delay_weeks"])
        total = int(subset["seed"].nunique())
        rows.append(
            {
                "series_name": series_name,
                "num_seeds": total,
                "recommended_model_mode": recommended_model,
                "recommended_model_frequency": recommended_count / total if total else 0.0,
                "best_test_model_mode": best_test_model,
                "best_test_model_frequency": best_test_count / total if total else 0.0,
                "best_rolling_model_mode": best_rolling_model,
                "best_rolling_model_frequency": best_rolling_count / total if total else 0.0,
                "decision_type_mode": decision_type,
                "decision_type_frequency": decision_count / total if total else 0.0,
                "recommended_discovery_structure_mode": recommended_structure,
                "recommended_discovery_structure_frequency": structure_count / total if total else 0.0,
                "recommended_discovery_fractional_mode": fractional_mode,
                "recommended_discovery_fractional_frequency": fractional_count / total if total else 0.0,
                "recommended_discovery_observation_map_mode": observation_mode,
                "recommended_discovery_observation_map_frequency": observation_count / total if total else 0.0,
                "recommended_discovery_delay_weeks_mode": delay_mode,
                "recommended_discovery_delay_weeks_frequency": delay_count / total if total else 0.0,
            }
        )

    return pd.DataFrame(rows).sort_values("series_name").reset_index(drop=True)


def build_multiseed_discovery_structure_frequency(seed_artifact_roots: dict[int, Path]) -> pd.DataFrame:
    summary = load_multiseed_tables(seed_artifact_roots)["summary"]
    discovery = summary.loc[summary["model_name"] == "constrained_structure_discovery"].copy()
    delay_series = discovery["discovery_delay_weeks"].apply(
        lambda value: int(value) if pd.notna(value) else 0
    )
    fractional_flag = discovery["discovery_fractional"].apply(
        lambda value: "1" if pd.notna(value) and bool(value) else "0"
    )
    discovery["structure_spec"] = (
        discovery["discovery_structure_name"].fillna("unknown").astype(str)
        + "|fractional="
        + fractional_flag
        + "|obs="
        + discovery["discovery_observation_map"].fillna("unknown").astype(str)
        + delay_series.apply(lambda value: f"|delay={value}" if value > 0 else "")
    )
    frequency = (
        discovery.groupby(["series_name", "structure_spec"], as_index=False)
        .agg(
            count=("seed", "count"),
            mean_test_mae=("test_mae", "mean"),
            mean_rolling_mae=("rolling_mean_mae", "mean"),
        )
    )
    seed_counts = discovery.groupby("series_name")["seed"].nunique().rename("num_seeds").reset_index()
    frequency = frequency.merge(seed_counts, on="series_name", how="left")
    frequency["selected_structure_frequency"] = frequency["count"] / frequency["num_seeds"]
    return frequency.sort_values(
        ["series_name", "selected_structure_frequency", "mean_test_mae", "structure_spec"],
        ascending=[True, False, True, True],
    ).reset_index(drop=True)


def write_multiseed_outputs(seed_artifact_roots: dict[int, Path], output_root: Path) -> dict[str, Path]:
    output_root = ensure_dir(output_root)
    model_summary = build_multiseed_model_summary(seed_artifact_roots)
    recommendation_summary = build_multiseed_age_group_recommendation(seed_artifact_roots)
    structure_frequency = build_multiseed_discovery_structure_frequency(seed_artifact_roots)

    model_summary_path = output_root / "multiseed_model_summary.csv"
    recommendation_path = output_root / "multiseed_age_group_recommendation.csv"
    structure_path = output_root / "multiseed_discovery_structure_frequency.csv"
    model_summary.to_csv(model_summary_path, index=False)
    recommendation_summary.to_csv(recommendation_path, index=False)
    structure_frequency.to_csv(structure_path, index=False)

    plot_multiseed_errorbars(
        summary=model_summary,
        mean_column="mean_test_mae",
        std_column="std_test_mae",
        title="Multi-Seed Test MAE by Series and Model",
        ylabel="mean_test_mae",
        path=output_root / "multiseed_test_mae_errorbars.png",
    )
    plot_multiseed_errorbars(
        summary=model_summary,
        mean_column="mean_rolling_mae",
        std_column="std_rolling_mae",
        title="Multi-Seed Rolling MAE by Series and Model",
        ylabel="mean_rolling_mae",
        path=output_root / "multiseed_rolling_mae_errorbars.png",
    )

    return {
        "model_summary": model_summary_path,
        "age_group_recommendation": recommendation_path,
        "discovery_structure_frequency": structure_path,
        "test_mae_plot": output_root / "multiseed_test_mae_errorbars.png",
        "rolling_mae_plot": output_root / "multiseed_rolling_mae_errorbars.png",
    }
