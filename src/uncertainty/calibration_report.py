from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.evaluation.metrics import average_interval_width, interval_coverage, learn_interval_scales
from src.uncertainty.conformal import (
    apply_absolute_conformal,
    apply_asymmetric_conformal,
    apply_raw_interval,
    apply_scale_calibrated_interval,
    apply_standardized_conformal,
    conformal_quantile,
    interval_score,
)
from src.uncertainty.residual_bank import DEFAULT_AGE_FAMILIES, ResidualBank, build_residual_bank
from src.utils.io import ensure_dir


logger = logging.getLogger(__name__)


def resolve_conformal_config(config: dict[str, Any], output_root: Path | None = None) -> dict[str, Any]:
    uncertainty = config.get("uncertainty", {})
    conformal = uncertainty.get("conformal", {})
    resolved = {
        "enabled": bool(conformal.get("enabled", True)),
        "output_dir": str(output_root) if output_root is not None else str(conformal.get("output_dir", "artifacts_v5_conformal")),
        "calibration_kinds": list(
            conformal.get(
                "calibration_kinds",
                ["raw", "scale_calibrated", "conformal_absolute", "conformal_standardized", "conformal_asymmetric"],
            )
        ),
        "interval_levels": [int(level) for level in conformal.get("interval_levels", [50, 80, 95])],
        "residual_source": str(conformal.get("residual_source", "rolling_validation")),
        "prefer_horizon_specific": bool(conformal.get("prefer_horizon_specific", True)),
        "horizon_fallback": str(conformal.get("horizon_fallback", "pooled_across_horizons")),
        "min_calibration_points": int(conformal.get("min_calibration_points", 20)),
        "fallback_pooling": str(conformal.get("fallback_pooling", "age_family")),
        "eps": float(conformal.get("eps", 1.0e-8)),
        "lower_bound": float(conformal.get("lower_bound", 0.0)),
        "winner_split": str(conformal.get("winner_split", "validation")),
        "test_is_evaluation_only": bool(conformal.get("test_is_evaluation_only", True)),
        "winner_undercoverage_floor": float(conformal.get("winner_undercoverage_floor", -0.05)),
        "winner_interval_score_weight": float(conformal.get("winner_interval_score_weight", 0.25)),
        "age_families": conformal.get("age_families", DEFAULT_AGE_FAMILIES),
        "calibration_draws": int(config.get("fitting", {}).get("calibration_draws", 12)),
        "calibration_scale_min": float(config.get("fitting", {}).get("calibration_scale_min", 0.25)),
        "calibration_scale_max": float(config.get("fitting", {}).get("calibration_scale_max", 1.25)),
        "calibration_scale_grid_size": int(config.get("fitting", {}).get("calibration_scale_grid_size", 41)),
    }
    return resolved


def _required_artifact_paths(prob_dir: Path) -> dict[str, Path]:
    return {
        "metrics": prob_dir / "metrics.json",
        "forecast_trace": prob_dir / "forecast_trace.csv",
        "validation_forecast_trace": prob_dir / "validation_forecast_trace.csv",
        "rolling_origin_forecasts": prob_dir / "rolling_origin_forecasts.csv",
    }


def _load_probabilistic_artifacts(artifact_root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    del config
    bundles: list[dict[str, Any]] = []
    missing: list[str] = []

    for metrics_path in sorted(artifact_root.glob("**/probabilistic_seir/metrics.json")):
        prob_dir = metrics_path.parent
        required = _required_artifact_paths(prob_dir)
        for label, path in required.items():
            if not path.exists():
                missing.append(f"{prob_dir}: missing {label} -> {path.name}")
        if any(not path.exists() for path in required.values()):
            continue

        metrics = json.loads(required["metrics"].read_text(encoding="utf-8"))
        forecast_frame = pd.read_csv(required["forecast_trace"])
        validation_frame = pd.read_csv(required["validation_forecast_trace"])
        rolling_frame = pd.read_csv(required["rolling_origin_forecasts"])
        validation_targets = set(validation_frame["t"].astype(int).tolist())
        rolling_validation_frame = rolling_frame.loc[rolling_frame["target_t"].isin(validation_targets)].copy()
        test_frame = forecast_frame.loc[forecast_frame["segment"] == "test"].copy()
        if test_frame.empty:
            missing.append(f"{prob_dir}: no test rows in forecast_trace.csv")
            continue

        bundles.append(
            {
                "series_name": metrics["series_name"],
                "model_name": metrics["model_name"],
                "artifact_dir": prob_dir,
                "metrics": metrics,
                "validation_frame": validation_frame,
                "test_frame": test_frame,
                "rolling_validation_frame": rolling_validation_frame,
            }
        )

    if missing:
        missing_text = "\n".join(f"- {item}" for item in missing)
        raise RuntimeError(
            "Conformal postprocess requires raw probabilistic forecast artifacts that are not available.\n"
            f"{missing_text}\n"
            "Rerun the benchmark with the current pipeline to regenerate probabilistic artifacts, then rerun the postprocess."
        )

    if not bundles:
        raise RuntimeError(f"No probabilistic benchmark artifacts found under {artifact_root}.")
    return bundles


def evaluate_calibrated_intervals(
    frame: pd.DataFrame,
    lower: np.ndarray,
    upper: np.ndarray,
    nominal_coverage: float,
) -> dict[str, float]:
    y_true = frame["actual"].to_numpy(dtype=float)
    scores = interval_score(y_true, lower, upper, nominal_coverage=nominal_coverage)
    empirical = interval_coverage(y_true, lower, upper)
    width = average_interval_width(lower, upper)
    gap = empirical - nominal_coverage
    return {
        "nominal_coverage": float(nominal_coverage),
        "empirical_coverage": float(empirical),
        "coverage_gap": float(gap),
        "abs_coverage_gap": float(abs(gap)),
        "average_interval_width": float(width),
        "interval_score_mean": float(np.mean(scores)),
        "interval_score_median": float(np.median(scores)),
    }


def _frame_center(frame: pd.DataFrame) -> np.ndarray:
    if "point_prediction" in frame.columns:
        return frame["point_prediction"].to_numpy(dtype=float)
    if "test_forecast_prediction" in frame.columns:
        return frame["test_forecast_prediction"].to_numpy(dtype=float)
    raise RuntimeError("Forecast frame is missing a point prediction column.")


def _raw_bounds(frame: pd.DataFrame, level: int) -> tuple[np.ndarray, np.ndarray]:
    lower_col = f"raw_lower_{level}"
    upper_col = f"raw_upper_{level}"
    if lower_col not in frame.columns or upper_col not in frame.columns:
        fallback_lower = f"lower_{level}"
        fallback_upper = f"upper_{level}"
        if fallback_lower not in frame.columns or fallback_upper not in frame.columns:
            raise RuntimeError(f"Frame is missing raw interval columns for level {level}.")
        return (
            frame[fallback_lower].to_numpy(dtype=float),
            frame[fallback_upper].to_numpy(dtype=float),
        )
    return (
        frame[lower_col].to_numpy(dtype=float),
        frame[upper_col].to_numpy(dtype=float),
    )


def _apply_calibration_kind(
    kind: str,
    series_name: str,
    interval_level: int,
    split_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    residual_bank: ResidualBank,
    conformal_config: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    lower_bound = float(conformal_config["lower_bound"])
    nominal = int(interval_level) / 100.0
    center = _frame_center(split_frame)
    validation_center = _frame_center(validation_frame)
    lower_raw, upper_raw = _raw_bounds(split_frame, interval_level)
    validation_lower_raw, validation_upper_raw = _raw_bounds(validation_frame, interval_level)

    if kind == "raw":
        lower, upper = apply_raw_interval(lower_raw, upper_raw, lower_bound=lower_bound)
        return lower, upper, {
            "residual_source_used": "none",
            "calibration_points": 0,
            "pooled_horizons_used": False,
            "pooled_age_family_used": False,
            "global_pooling_used": False,
        }

    if kind == "scale_calibrated":
        scale_fit = learn_interval_scales(
            y_true=validation_frame["actual"].to_numpy(dtype=float),
            center=validation_center,
            interval_map={str(interval_level): (validation_lower_raw, validation_upper_raw)},
            scale_min=conformal_config["calibration_scale_min"],
            scale_max=conformal_config["calibration_scale_max"],
            grid_size=conformal_config["calibration_scale_grid_size"],
        )
        scale = float(scale_fit["scales"][str(interval_level)])
        lower, upper = apply_scale_calibrated_interval(
            center=center,
            lower_raw=lower_raw,
            upper_raw=upper_raw,
            scale=scale,
            lower_bound=lower_bound,
        )
        return lower, upper, {
            "residual_source_used": "same_series_static_validation",
            "calibration_points": int(len(validation_frame)),
            "pooled_horizons_used": False,
            "pooled_age_family_used": False,
            "global_pooling_used": False,
        }

    if kind == "conformal_absolute":
        scores, metadata = residual_bank.get_calibration_scores(
            series_name=series_name,
            interval_level=interval_level,
            horizon="static",
            method=kind,
            config=conformal_config,
        )
        q = conformal_quantile(scores, nominal_coverage=nominal)
        lower, upper = apply_absolute_conformal(center=center, q=q, lower_bound=lower_bound)
        return lower, upper, metadata

    if kind == "conformal_standardized":
        scores, metadata = residual_bank.get_calibration_scores(
            series_name=series_name,
            interval_level=interval_level,
            horizon="static",
            method=kind,
            config=conformal_config,
        )
        q = conformal_quantile(scores, nominal_coverage=nominal)
        lower, upper = apply_standardized_conformal(
            center=center,
            lower_raw=lower_raw,
            upper_raw=upper_raw,
            q=q,
            eps=conformal_config["eps"],
            lower_bound=lower_bound,
        )
        return lower, upper, metadata

    if kind == "conformal_asymmetric":
        lower_scores, metadata = residual_bank.get_calibration_scores(
            series_name=series_name,
            interval_level=interval_level,
            horizon="static",
            method=kind,
            config=conformal_config,
            side="lower",
        )
        upper_scores, _ = residual_bank.get_calibration_scores(
            series_name=series_name,
            interval_level=interval_level,
            horizon="static",
            method=kind,
            config=conformal_config,
            side="upper",
        )
        q_lower = conformal_quantile(lower_scores, nominal_coverage=nominal)
        q_upper = conformal_quantile(upper_scores, nominal_coverage=nominal)
        lower, upper = apply_asymmetric_conformal(
            lower_raw=lower_raw,
            upper_raw=upper_raw,
            q_lower=q_lower,
            q_upper=q_upper,
            lower_bound=lower_bound,
        )
        return lower, upper, metadata

    raise ValueError(f"Unsupported calibration kind: {kind}")


def build_calibration_comparison(
    artifact_root: Path,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, ResidualBank]:
    conformal_config = resolve_conformal_config(config)
    bundles = _load_probabilistic_artifacts(artifact_root, config)
    residual_bank = build_residual_bank(bundles, {"uncertainty": {"conformal": conformal_config}})
    rows: list[dict[str, Any]] = []

    for bundle in bundles:
        series_name = bundle["series_name"]
        age_family = residual_bank.get_age_family(series_name)
        model_name = bundle["model_name"]
        metrics = bundle["metrics"]
        validation_frame = bundle["validation_frame"].copy()
        validation_frame["horizon"] = "static"
        test_frame = bundle["test_frame"].copy()
        test_frame["horizon"] = "static"
        for split_name, frame in (("validation", validation_frame), ("test", test_frame)):
            for interval_level in conformal_config["interval_levels"]:
                nominal = int(interval_level) / 100.0
                for kind in conformal_config["calibration_kinds"]:
                    lower, upper, metadata = _apply_calibration_kind(
                        kind=kind,
                        series_name=series_name,
                        interval_level=int(interval_level),
                        split_frame=frame,
                        validation_frame=validation_frame,
                        residual_bank=residual_bank,
                        conformal_config=conformal_config,
                    )
                    evaluation = evaluate_calibrated_intervals(frame, lower, upper, nominal)
                    rows.append(
                        {
                            "series_name": series_name,
                            "age_family": age_family,
                            "model_name": model_name,
                            "split": split_name,
                            "horizon": "static",
                            "calibration_kind": kind,
                            "interval_level": int(interval_level),
                            **evaluation,
                            "residual_source_used": metadata["residual_source_used"],
                            "calibration_points": metadata["calibration_points"],
                            "pooled_horizons_used": metadata["pooled_horizons_used"],
                            "pooled_age_family_used": metadata["pooled_age_family_used"],
                            "global_pooling_used": metadata["global_pooling_used"],
                            "uncertainty_method": metrics.get("probabilistic_metrics", {}).get("uncertainty_method"),
                            "uncertainty_draws": metrics.get("probabilistic_metrics", {}).get("uncertainty_draws"),
                            "artifact_dir": str(bundle["artifact_dir"]),
                        }
                    )

    comparison = pd.DataFrame.from_records(rows).sort_values(
        ["series_name", "split", "interval_level", "calibration_kind"]
    ).reset_index(drop=True)
    return comparison, residual_bank


def select_validation_winners(comparison: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    conformal_config = resolve_conformal_config(config)
    validation_rows = comparison.loc[comparison["split"] == conformal_config["winner_split"]].copy()
    winners: list[dict[str, Any]] = []

    for _, subset in validation_rows.groupby(["series_name", "model_name", "horizon", "interval_level"], sort=True):
        eligible = subset.loc[subset["coverage_gap"] >= conformal_config["winner_undercoverage_floor"]].copy()
        candidate_subset = eligible if not eligible.empty else subset.copy()

        score_values = candidate_subset["interval_score_mean"].to_numpy(dtype=float)
        gap_values = candidate_subset["abs_coverage_gap"].to_numpy(dtype=float)

        def _normalize(values: np.ndarray) -> np.ndarray:
            if len(values) == 1 or float(np.max(values) - np.min(values)) <= 1.0e-12:
                return np.zeros(len(values), dtype=float)
            return (values - np.min(values)) / (np.max(values) - np.min(values))

        normalized_scores = _normalize(score_values)
        normalized_gaps = _normalize(gap_values)

        candidate_subset = candidate_subset.copy()
        candidate_subset["selection_score"] = (
            normalized_gaps
            + conformal_config["winner_interval_score_weight"] * normalized_scores
        )
        selected = candidate_subset.sort_values(
            ["selection_score", "abs_coverage_gap", "interval_score_mean", "average_interval_width", "calibration_kind"]
        ).iloc[0]
        rule_used = "coverage_floor_then_balanced_score" if not eligible.empty else "balanced_score_no_floor_fallback"

        winners.append(
            {
                "series_name": selected["series_name"],
                "age_family": selected["age_family"],
                "model_name": selected["model_name"],
                "horizon": selected["horizon"],
                "interval_level": int(selected["interval_level"]),
                "selected_calibration_kind": selected["calibration_kind"],
                "validation_empirical_coverage": selected["empirical_coverage"],
                "validation_coverage_gap": selected["coverage_gap"],
                "validation_average_interval_width": selected["average_interval_width"],
                "validation_interval_score_mean": selected["interval_score_mean"],
                "validation_selection_score": selected["selection_score"],
                "selection_rule_used": rule_used,
                "residual_source_used": selected["residual_source_used"],
                "calibration_points": int(selected["calibration_points"]),
            }
        )

    return pd.DataFrame.from_records(winners).sort_values(
        ["series_name", "horizon", "interval_level"]
    ).reset_index(drop=True)


def build_selected_test_report(comparison: pd.DataFrame, winners: pd.DataFrame) -> pd.DataFrame:
    test_rows = comparison.loc[comparison["split"] == "test"].copy()
    merged = winners.merge(
        test_rows,
        left_on=["series_name", "model_name", "horizon", "interval_level", "selected_calibration_kind"],
        right_on=["series_name", "model_name", "horizon", "interval_level", "calibration_kind"],
        how="left",
        suffixes=("_validation", "_test"),
    )
    report = pd.DataFrame(
        {
            "series_name": merged["series_name"],
            "age_family": merged["age_family_validation"],
            "model_name": merged["model_name"],
            "horizon": merged["horizon"],
            "interval_level": merged["interval_level"],
            "selected_calibration_kind": merged["selected_calibration_kind"],
            "test_empirical_coverage": merged["empirical_coverage"],
            "test_coverage_gap": merged["coverage_gap"],
            "test_average_interval_width": merged["average_interval_width"],
            "test_interval_score_mean": merged["interval_score_mean"],
            "validation_coverage_gap": merged["validation_coverage_gap"],
            "validation_interval_score_mean": merged["validation_interval_score_mean"],
        }
    )
    return report.sort_values(["series_name", "horizon", "interval_level"]).reset_index(drop=True)


def _plot_metric_by_method(comparison: pd.DataFrame, split: str, metric: str, path: Path, title: str) -> None:
    subset = comparison.loc[comparison["split"] == split].copy()
    grouped = subset.groupby(["interval_level", "calibration_kind"])[metric].mean().unstack(fill_value=np.nan)
    fig, ax = plt.subplots(figsize=(10, 5))
    grouped.plot(kind="bar", ax=ax)
    ax.set_title(title)
    ax.set_xlabel("Interval level")
    ax.set_ylabel(metric.replace("_", " ").title())
    ax.legend(title="Calibration kind", loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _plot_gap_vs_width(comparison: pd.DataFrame, split: str, path: Path, title: str) -> None:
    subset = comparison.loc[comparison["split"] == split].copy()
    fig, ax = plt.subplots(figsize=(8, 6))
    for method, method_rows in subset.groupby("calibration_kind"):
        ax.scatter(
            method_rows["average_interval_width"],
            method_rows["coverage_gap"],
            label=method,
            alpha=0.8,
        )
    ax.axhline(0.0, color="black", linestyle="--", linewidth=1.0)
    ax.axhline(-0.05, color="gray", linestyle=":", linewidth=1.0)
    ax.set_xlabel("Average interval width")
    ax.set_ylabel("Coverage gap")
    ax.set_title(title)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _plot_selected_method_heatmap(winners: pd.DataFrame, path: Path) -> None:
    pivot = winners.pivot(index="series_name", columns="interval_level", values="selected_calibration_kind")
    methods = sorted(pd.unique(winners["selected_calibration_kind"]))
    method_to_code = {method: index for index, method in enumerate(methods)}
    code_matrix = pivot.applymap(lambda value: method_to_code[value]).to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(code_matrix, aspect="auto", cmap="tab20")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([str(value) for value in pivot.columns])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index.tolist())
    ax.set_xlabel("Interval level")
    ax.set_title("Selected calibration method by series")
    for row_index, series_name in enumerate(pivot.index):
        for col_index, interval_level in enumerate(pivot.columns):
            ax.text(col_index, row_index, pivot.loc[series_name, interval_level], ha="center", va="center", fontsize=8)
    cbar = fig.colorbar(im, ax=ax, ticks=list(method_to_code.values()))
    cbar.ax.set_yticklabels(methods)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def write_calibration_outputs(
    artifact_root: Path,
    output_root: Path,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ensure_dir(output_root)
    comparison, _ = build_calibration_comparison(artifact_root, config)
    winners = select_validation_winners(comparison, config)
    selected_test = build_selected_test_report(comparison, winners)

    comparison.to_csv(output_root / "probabilistic_calibration_comparison.csv", index=False)
    winners.to_csv(output_root / "calibration_method_winners.csv", index=False)
    selected_test.to_csv(output_root / "calibration_selected_test_report.csv", index=False)

    _plot_metric_by_method(
        comparison, "validation", "empirical_coverage", output_root / "calibration_validation_coverage_by_method.png",
        "Validation empirical coverage by calibration kind",
    )
    _plot_metric_by_method(
        comparison, "test", "empirical_coverage", output_root / "calibration_test_coverage_by_method.png",
        "Test empirical coverage by calibration kind",
    )
    _plot_metric_by_method(
        comparison, "validation", "average_interval_width", output_root / "calibration_validation_width_by_method.png",
        "Validation interval width by calibration kind",
    )
    _plot_metric_by_method(
        comparison, "test", "average_interval_width", output_root / "calibration_test_width_by_method.png",
        "Test interval width by calibration kind",
    )
    _plot_metric_by_method(
        comparison,
        "validation",
        "interval_score_mean",
        output_root / "calibration_validation_interval_score_by_method.png",
        "Validation interval score by calibration kind",
    )
    _plot_metric_by_method(
        comparison,
        "test",
        "interval_score_mean",
        output_root / "calibration_test_interval_score_by_method.png",
        "Test interval score by calibration kind",
    )
    _plot_gap_vs_width(
        comparison, "validation", output_root / "calibration_gap_vs_width_validation.png", "Validation coverage gap vs width"
    )
    _plot_gap_vs_width(
        comparison, "test", output_root / "calibration_gap_vs_width_test.png", "Test coverage gap vs width"
    )
    _plot_selected_method_heatmap(winners, output_root / "selected_method_by_series_heatmap.png")

    logger.info(
        "Conformal calibration outputs written comparison=%s winners=%s selected_test=%s",
        output_root / "probabilistic_calibration_comparison.csv",
        output_root / "calibration_method_winners.csv",
        output_root / "calibration_selected_test_report.csv",
    )
    return comparison, winners, selected_test
