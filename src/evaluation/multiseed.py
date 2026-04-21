from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd

from src.plotting.multiseed_plots import plot_multiseed_errorbars
from src.utils.io import ensure_dir


MODEL_SIMPLICITY_PRIORITY = [
    "deterministic_seir",
    "delayed_observation_seir",
    "hospitalized_seihr",
    "probabilistic_seir",
    "constrained_structure_discovery",
    "fractional_seir",
]
MODEL_SIMPLICITY_RANK = {model_name: index for index, model_name in enumerate(MODEL_SIMPLICITY_PRIORITY)}


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


def _practical_tie_tolerance(best_metric: float) -> float:
    return max(0.001, 0.02 * float(best_metric))


def _with_simplicity_rank(summary: pd.DataFrame) -> pd.DataFrame:
    ranked = summary.copy()
    ranked["simplicity_rank"] = ranked["model_name"].map(MODEL_SIMPLICITY_RANK).fillna(len(MODEL_SIMPLICITY_PRIORITY))
    return ranked


def _select_tie_set(summary: pd.DataFrame, metric_column: str) -> tuple[pd.DataFrame, float]:
    best_metric = float(summary[metric_column].min())
    tolerance = _practical_tie_tolerance(best_metric)
    tied = summary.loc[summary[metric_column] <= best_metric + tolerance].copy()
    return tied, best_metric


def _sort_policy_candidates(summary: pd.DataFrame, objective: str) -> pd.DataFrame:
    ranked = _with_simplicity_rank(summary)
    if objective == "test":
        return ranked.sort_values(
            [
                "test_win_rate",
                "std_test_mae",
                "num_free_params",
                "simplicity_rank",
                "mean_test_mae",
                "model_name",
            ],
            ascending=[False, True, True, True, True, True],
        ).reset_index(drop=True)
    if objective == "rolling":
        return ranked.sort_values(
            [
                "rolling_win_rate",
                "std_rolling_mae",
                "num_free_params",
                "simplicity_rank",
                "mean_rolling_mae",
                "model_name",
            ],
            ascending=[False, True, True, True, True, True],
        ).reset_index(drop=True)
    raise ValueError(f"Unknown objective: {objective}")


def _select_parsimony_model(summary: pd.DataFrame) -> str:
    ranked = _with_simplicity_rank(summary).copy()
    ranked["combined_mae"] = ranked["mean_test_mae"] + ranked["mean_rolling_mae"]
    ranked["combined_win_rate"] = ranked["test_win_rate"] + ranked["rolling_win_rate"]
    ranked = ranked.sort_values(
        ["num_free_params", "simplicity_rank", "combined_mae", "combined_win_rate", "model_name"],
        ascending=[True, True, True, False, True],
    ).reset_index(drop=True)
    return str(ranked.iloc[0]["model_name"])


def build_multiseed_objective_policy(model_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for series_name, subset in model_summary.groupby("series_name"):
        test_ties, test_best = _select_tie_set(subset, "mean_test_mae")
        rolling_ties, rolling_best = _select_tie_set(subset, "mean_rolling_mae")

        test_sorted = _sort_policy_candidates(test_ties, "test")
        rolling_sorted = _sort_policy_candidates(rolling_ties, "rolling")

        test_policy_model = str(test_sorted.iloc[0]["model_name"])
        rolling_policy_model = str(rolling_sorted.iloc[0]["model_name"])
        test_tie_models = ";".join(test_sorted["model_name"].tolist())
        rolling_tie_models = ";".join(rolling_sorted["model_name"].tolist())

        shared_models = sorted(set(test_ties["model_name"]).intersection(rolling_ties["model_name"]))
        if shared_models:
            shared_subset = subset.loc[subset["model_name"].isin(shared_models)].copy()
            parsimony_policy_model = _select_parsimony_model(shared_subset)
        else:
            parsimony_policy_model = "objective_dependent"

        objective_conflict = test_policy_model != rolling_policy_model
        if not objective_conflict:
            recommended_reason = (
                f"Test and rolling objectives agree on {test_policy_model} within the practical tie threshold."
            )
        elif parsimony_policy_model != "objective_dependent":
            recommended_reason = (
                f"Test and rolling objectives differ, but {parsimony_policy_model} is practically tied for both "
                "and is the simplest shared compromise."
            )
        else:
            recommended_reason = (
                f"Use {test_policy_model} for held-out test MAE and {rolling_policy_model} for rolling-origin stability."
            )

        rows.append(
            {
                "series_name": series_name,
                "test_policy_model": test_policy_model,
                "rolling_policy_model": rolling_policy_model,
                "parsimony_policy_model": parsimony_policy_model,
                "objective_conflict_flag": bool(objective_conflict),
                "test_tie_models": test_tie_models,
                "rolling_tie_models": rolling_tie_models,
                "test_best_mae": test_best,
                "rolling_best_mae": rolling_best,
                "recommended_reason": recommended_reason,
            }
        )

    return pd.DataFrame(rows).sort_values("series_name").reset_index(drop=True)


def build_pairwise_model_differences(seed_artifact_roots: dict[int, Path]) -> pd.DataFrame:
    seed_summary = load_multiseed_tables(seed_artifact_roots)["summary"]
    rows: list[dict[str, object]] = []

    for series_name, series_subset in seed_summary.groupby("series_name"):
        for metric in ["test_mae", "rolling_mean_mae"]:
            for model_a, model_b in combinations(sorted(series_subset["model_name"].unique()), 2):
                a_subset = series_subset.loc[series_subset["model_name"] == model_a, ["seed", metric]].rename(
                    columns={metric: "metric_a"}
                )
                b_subset = series_subset.loc[series_subset["model_name"] == model_b, ["seed", metric]].rename(
                    columns={metric: "metric_b"}
                )
                merged = a_subset.merge(b_subset, on="seed", how="inner")
                if merged.empty:
                    continue

                differences = merged["metric_a"] - merged["metric_b"]
                mean_a = float(merged["metric_a"].mean())
                mean_b = float(merged["metric_b"].mean())
                best_metric = min(mean_a, mean_b)
                practical_tie = abs(mean_a - mean_b) <= _practical_tie_tolerance(best_metric)

                rows.append(
                    {
                        "series_name": series_name,
                        "model_a": model_a,
                        "model_b": model_b,
                        "metric": metric,
                        "mean_difference": float(differences.mean()),
                        "median_difference": float(differences.median()),
                        "num_seeds_model_a_better": int((differences < 0).sum()),
                        "num_seeds_model_b_better": int((differences > 0).sum()),
                        "practical_tie_flag": bool(practical_tie),
                    }
                )

    columns = [
        "series_name",
        "model_a",
        "model_b",
        "metric",
        "mean_difference",
        "median_difference",
        "num_seeds_model_a_better",
        "num_seeds_model_b_better",
        "practical_tie_flag",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["series_name", "metric", "model_a", "model_b"]
    ).reset_index(drop=True)


def build_objective_aware_policy_report(policy: pd.DataFrame, pairwise: pd.DataFrame) -> str:
    total_series = int(policy["series_name"].nunique()) if not policy.empty else 0
    objective_conflicts = int(policy["objective_conflict_flag"].sum()) if not policy.empty else 0
    shared_compromises = int((policy["parsimony_policy_model"] != "objective_dependent").sum()) if not policy.empty else 0

    lines = [
        "# Objective-Aware Policy Report",
        "",
        "## Scope",
        "",
        "This report summarizes tie-aware recommendation logic for the observation-aware five-seed benchmark.",
        "The practical tie threshold is applied separately to `mean_test_mae` and `mean_rolling_mae`: ",
        "",
        "- `abs(model_metric - best_metric) <= max(0.001, 0.02 * best_metric)`",
        "",
        "Objective-specific policies then break ties using win rate, seed-level variability, parameter count, and model simplicity priority.",
        "",
        "## Summary",
        "",
        f"- Objective conflicts appear in `{objective_conflicts}` of `{total_series}` series.",
        f"- A shared parsimonious compromise exists in `{shared_compromises}` series.",
        "",
        "## Series Policies",
        "",
    ]

    for _, row in policy.sort_values("series_name").iterrows():
        lines.extend(
            [
                f"### {row['series_name']}",
                "",
                f"- test policy: `{row['test_policy_model']}`",
                f"- rolling policy: `{row['rolling_policy_model']}`",
                f"- parsimony policy: `{row['parsimony_policy_model']}`",
                f"- test tie set: `{row['test_tie_models']}`",
                f"- rolling tie set: `{row['rolling_tie_models']}`",
                f"- reason: {row['recommended_reason']}",
                "",
            ]
        )

    if not pairwise.empty:
        lines.extend(["## Closest Pairwise Comparisons", ""])
        for series_name, subset in pairwise.groupby("series_name"):
            closest = subset.assign(abs_mean_difference=subset["mean_difference"].abs()).sort_values(
                ["abs_mean_difference", "metric", "model_a", "model_b"]
            ).head(2)
            lines.append(f"### {series_name}")
            lines.append("")
            for _, row in closest.iterrows():
                lines.append(
                    f"- `{row['metric']}`: `{row['model_a']}` vs `{row['model_b']}` "
                    f"(mean diff `{row['mean_difference']:.6f}`, practical tie `{row['practical_tie_flag']}`)"
                )
            lines.append("")

    return "\n".join(lines).strip() + "\n"


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
    objective_policy = build_multiseed_objective_policy(model_summary)
    pairwise_differences = build_pairwise_model_differences(seed_artifact_roots)

    model_summary_path = output_root / "multiseed_model_summary.csv"
    recommendation_path = output_root / "multiseed_age_group_recommendation.csv"
    structure_path = output_root / "multiseed_discovery_structure_frequency.csv"
    objective_policy_path = output_root / "multiseed_objective_policy.csv"
    pairwise_differences_path = output_root / "pairwise_model_differences.csv"
    model_summary.to_csv(model_summary_path, index=False)
    recommendation_summary.to_csv(recommendation_path, index=False)
    structure_frequency.to_csv(structure_path, index=False)
    objective_policy.to_csv(objective_policy_path, index=False)
    pairwise_differences.to_csv(pairwise_differences_path, index=False)

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
        "objective_policy": objective_policy_path,
        "pairwise_model_differences": pairwise_differences_path,
        "test_mae_plot": output_root / "multiseed_test_mae_errorbars.png",
        "rolling_mae_plot": output_root / "multiseed_rolling_mae_errorbars.png",
    }
