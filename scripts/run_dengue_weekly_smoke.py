from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from run_experiment import _fit_config, _search_config, _slugify  # noqa: E402
from src.data.dengue_loader import build_dengue_benchmark_panel, load_dengue_national_csv  # noqa: E402
from src.data.split import make_chronological_split  # noqa: E402
from src.discovery.model import DiscoveryCompartmentModel  # noqa: E402
from src.discovery.search import discovery_regularization_config, run_structure_search  # noqa: E402
from src.models.seir_deterministic import DeterministicSEIRModel  # noqa: E402
from src.utils.io import ensure_dir, write_json  # noqa: E402
from src.utils.logging_utils import configure_logging  # noqa: E402

logger = logging.getLogger(__name__)


def _resolve_repo_path(path: str | Path) -> Path:
    resolved = Path(path)
    return resolved if resolved.is_absolute() else REPO_ROOT / resolved


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _fill_missing_for_model(series: pd.Series) -> np.ndarray:
    filled = pd.to_numeric(series, errors="coerce").interpolate(limit_direction="both").fillna(0.0)
    return filled.clip(lower=0.0).to_numpy(dtype=float)


def _observed_metric_mask(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    return np.isfinite(y_true) & np.isfinite(y_pred)


def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = _observed_metric_mask(y_true, y_pred)
    return float(np.mean(np.abs(y_true[mask] - y_pred[mask]))) if mask.any() else float("nan")


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = _observed_metric_mask(y_true, y_pred)
    return float(np.sqrt(np.mean(np.square(y_true[mask] - y_pred[mask])))) if mask.any() else float("nan")


def _mase(y_true: np.ndarray, y_pred: np.ndarray, y_train: np.ndarray) -> float:
    train = y_train[np.isfinite(y_train)]
    if len(train) < 2:
        scale = 1.0
    else:
        scale = float(np.mean(np.abs(np.diff(train))))
        if not np.isfinite(scale) or scale <= 1.0e-12:
            scale = 1.0
    return _mae(y_true, y_pred) / scale


def _log1p_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = _observed_metric_mask(y_true, y_pred)
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs(np.log1p(np.clip(y_pred[mask], 0.0, None)) - np.log1p(np.clip(y_true[mask], 0.0, None)))))


def _seasonal_naive_prediction(y: np.ndarray, start: int, end: int, seasonal_period: int) -> np.ndarray:
    predictions = np.zeros(end - start, dtype=float)
    fallback_history = y[:start]
    fallback_values = fallback_history[np.isfinite(fallback_history)]
    fallback = float(fallback_values[-1]) if len(fallback_values) else 0.0
    for idx, t in enumerate(range(start, end)):
        lag = t - seasonal_period
        predictions[idx] = y[lag] if lag >= 0 and np.isfinite(y[lag]) else fallback
    return np.clip(predictions, 0.0, None)


def _student_t_prediction(y: np.ndarray, start: int, end: int, seasonal_period: int) -> np.ndarray:
    baseline = _seasonal_naive_prediction(y, start, end, seasonal_period)
    residuals = []
    for t in range(seasonal_period, start):
        if np.isfinite(y[t]) and np.isfinite(y[t - seasonal_period]):
            residuals.append(y[t] - y[t - seasonal_period])
    correction = float(np.median(residuals)) if residuals else 0.0
    return np.clip(baseline + correction, 0.0, None)


def _rolling_naive_mae(y: np.ndarray, test_start: int, seasonal_period: int, max_origins: int) -> float:
    origins = list(range(test_start, len(y)))
    if max_origins > 0:
        origins = origins[:max_origins]
    errors = []
    for t in origins:
        if not np.isfinite(y[t]):
            continue
        pred = _seasonal_naive_prediction(y, t, t + 1, seasonal_period)[0]
        errors.append(abs(y[t] - pred))
    return float(np.mean(errors)) if errors else float("nan")


def _model_metrics(
    y_true_full: np.ndarray,
    y_pred_full: np.ndarray,
    split_train_end: int,
    split_val_end: int,
    rolling_mae: float,
) -> dict[str, float]:
    y_test = y_true_full[split_val_end:]
    pred_test = y_pred_full[split_val_end:]
    return {
        "mae": _mae(y_test, pred_test),
        "rmse": _rmse(y_test, pred_test),
        "mase": _mase(y_test, pred_test, y_true_full[:split_train_end]),
        "rolling_mae": float(rolling_mae),
        "log1p_mae": _log1p_mae(y_test, pred_test),
    }


def _rolling_model_mae(
    *,
    y_model: np.ndarray,
    y_true: np.ndarray,
    split_val_end: int,
    max_origins: int,
    model_factory: Any,
    seed: int,
) -> float:
    origins = list(range(split_val_end, len(y_true)))
    if max_origins > 0:
        origins = origins[:max_origins]
    errors = []
    rng = np.random.default_rng(seed)
    for t in origins:
        if not np.isfinite(y_true[t]):
            continue
        model = model_factory()
        fit = model.fit(y_model[:t], rng)
        prediction = model.simulate(fit.raw_params, t + 1).predictions[t]
        errors.append(abs(float(y_true[t]) - float(prediction)))
    return float(np.mean(errors)) if errors else float("nan")


def _run_seasonal_naive(
    y_model: np.ndarray,
    y_true: np.ndarray,
    split: Any,
    seasonal_period: int,
    max_rolling_origins: int,
) -> tuple[np.ndarray, dict[str, Any], float]:
    predictions = np.full_like(y_model, fill_value=np.nan, dtype=float)
    predictions[split.val_end :] = _seasonal_naive_prediction(y_model, split.val_end, len(y_model), seasonal_period)
    rolling_mae = _rolling_naive_mae(y_true, split.val_end, seasonal_period, max_rolling_origins)
    return predictions, {}, rolling_mae


def _run_student_t(
    y_model: np.ndarray,
    y_true: np.ndarray,
    split: Any,
    seasonal_period: int,
    max_rolling_origins: int,
) -> tuple[np.ndarray, dict[str, Any], float]:
    predictions = np.full_like(y_model, fill_value=np.nan, dtype=float)
    predictions[split.val_end :] = _student_t_prediction(y_model, split.val_end, len(y_model), seasonal_period)
    rolling_mae = _rolling_naive_mae(y_true, split.val_end, seasonal_period, max_rolling_origins)
    residuals = []
    for t in range(seasonal_period, split.val_end):
        residuals.append(y_model[t] - y_model[t - seasonal_period])
    metadata = {"student_t_residual_scale": float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0}
    return predictions, metadata, rolling_mae


def _run_deterministic_seir_like(
    y_model: np.ndarray,
    y_true: np.ndarray,
    split: Any,
    fit_config: Any,
    max_rolling_origins: int,
    seed: int,
) -> tuple[np.ndarray, dict[str, Any], float]:
    rng = np.random.default_rng(seed)
    model = DeterministicSEIRModel(fit_config)
    fit = model.fit(y_model[: split.val_end], rng)
    predictions = model.simulate(fit.raw_params, len(y_model)).predictions
    rolling_mae = _rolling_model_mae(
        y_model=y_model,
        y_true=y_true,
        split_val_end=split.val_end,
        max_origins=max_rolling_origins,
        model_factory=lambda: DeterministicSEIRModel(fit_config),
        seed=seed + 101,
    )
    return np.clip(predictions, 0.0, None), {"num_free_params": model.raw_parameter_dim}, rolling_mae


def _run_discovery(
    y_model: np.ndarray,
    y_true: np.ndarray,
    split: Any,
    fit_config: Any,
    search_config: Any,
    artifact_dir: Path,
    max_rolling_origins: int,
    seed: int,
) -> tuple[np.ndarray, dict[str, Any], float]:
    outcome = run_structure_search(
        series_name=artifact_dir.parent.name,
        y_train=y_model[split.train_slice],
        y_val=y_model[split.val_slice],
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir / "search",
        seed=seed,
    )
    regularization_config = discovery_regularization_config(search_config)
    rng = np.random.default_rng(seed + 17)
    model_factory = lambda: DiscoveryCompartmentModel(outcome.best_spec, fit_config, regularization_config)
    model = model_factory()
    fit = model.fit(y_model[: split.val_end], rng)
    predictions = model.simulate(fit.raw_params, len(y_model)).predictions
    rolling_mae = _rolling_model_mae(
        y_model=y_model,
        y_true=y_true,
        split_val_end=split.val_end,
        max_origins=max_rolling_origins,
        model_factory=model_factory,
        seed=seed + 503,
    )
    metadata = {
        "best_spec": outcome.best_spec.spec_key,
        "best_structure_name": outcome.best_spec.structure_name,
        "best_fractional": bool(outcome.best_spec.fractional),
        "best_observation_map": outcome.best_spec.observation_map,
        "best_delay_weeks": int(outcome.best_spec.delay_weeks),
    }
    return np.clip(predictions, 0.0, None), metadata, rolling_mae


def _write_forecast_trace(path: Path, series: pd.DataFrame, predictions: np.ndarray, split: Any) -> None:
    trace = series.loc[:, ["calendar_start_date", "t", "y_raw", "missing_week_indicator"]].copy()
    trace["prediction"] = predictions
    trace["segment"] = np.where(
        trace["t"] < split.train_end,
        "train",
        np.where(trace["t"] < split.val_end, "validation", "test"),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    trace.to_csv(path, index=False)


def _run_series(
    series_name: str,
    series: pd.DataFrame,
    config: dict[str, Any],
    artifact_root: Path,
    seed: int,
) -> pd.DataFrame:
    series_root = ensure_dir(artifact_root / _slugify(series_name))
    fit_config = _fit_config(config)
    search_config = _search_config(config)
    evaluation = config["evaluation"]
    seasonal_period = int(evaluation.get("seasonal_period", 52))
    max_rolling_origins = int(evaluation.get("max_rolling_origins", 12))
    y_true = pd.to_numeric(series["y_raw"], errors="coerce").to_numpy(dtype=float)
    y_model = _fill_missing_for_model(series["y_raw"])
    split = make_chronological_split(
        len(y_model),
        train_fraction=float(evaluation.get("train_fraction", 0.6)),
        val_fraction=float(evaluation.get("val_fraction", 0.2)),
    )
    rows: list[dict[str, Any]] = []

    for offset, model_name in enumerate(config["models"]):
        model_dir = ensure_dir(series_root / model_name)
        logger.info("Dengue smoke start series=%s model=%s", series_name, model_name)
        if model_name == "seasonal_naive":
            predictions, metadata, rolling_mae = _run_seasonal_naive(
                y_model, y_true, split, seasonal_period, max_rolling_origins
            )
        elif model_name == "probabilistic_student_t":
            predictions, metadata, rolling_mae = _run_student_t(
                y_model, y_true, split, seasonal_period, max_rolling_origins
            )
        elif model_name == "deterministic_seir_like":
            predictions, metadata, rolling_mae = _run_deterministic_seir_like(
                y_model, y_true, split, fit_config, max_rolling_origins, seed + offset
            )
        elif model_name == "constrained_structure_discovery":
            predictions, metadata, rolling_mae = _run_discovery(
                y_model,
                y_true,
                split,
                fit_config,
                search_config,
                model_dir,
                max_rolling_origins,
                seed + offset,
            )
        else:
            raise ValueError(f"Unsupported dengue smoke model: {model_name}")

        metrics = _model_metrics(y_true, predictions, split.train_end, split.val_end, rolling_mae)
        row = {"series_name": series_name, "model_name": model_name, **metrics, **metadata}
        rows.append(row)
        _write_forecast_trace(model_dir / "forecast_trace.csv", series, predictions, split)
        write_json(row, model_dir / "metrics.json")

    leaderboard = pd.DataFrame(rows).sort_values(["mae", "rolling_mae", "mase", "model_name"]).reset_index(drop=True)
    leaderboard.to_csv(series_root / "leaderboard.csv", index=False)
    return leaderboard


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_None._"
    shown = frame.loc[:, columns].copy().fillna("")
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in shown.itertuples(index=False):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _write_report(summary: pd.DataFrame, panel: pd.DataFrame, report_path: Path) -> None:
    winners = summary.sort_values(["series_name", "mae", "rolling_mae"]).groupby("series_name", as_index=False).first()
    model_win_counts = winners["model_name"].value_counts().to_dict()
    dominance = "No single model dominates all countries."
    if len(model_win_counts) == 1 and len(winners) > 0:
        dominance = f"`{next(iter(model_win_counts))}` wins all evaluated countries by MAE."
    discovery = summary.loc[summary["model_name"] == "constrained_structure_discovery"].copy()
    delayed_count = int((discovery.get("best_observation_map", pd.Series(dtype=object)) == "delayed_I").sum()) if not discovery.empty else 0
    fractional_count = int(discovery.get("best_fractional", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if not discovery.empty else 0
    useful_count = 0
    for series_name, subset in summary.groupby("series_name"):
        discovery_rows = subset.loc[subset["model_name"] == "constrained_structure_discovery"]
        if discovery_rows.empty:
            continue
        best_mae = float(subset["mae"].min())
        discovery_mae = float(discovery_rows.iloc[0]["mae"])
        if discovery_mae <= best_mae + max(0.001, 0.02 * best_mae):
            useful_count += 1

    usable = panel.groupby(["country", "case_definition_standardised"], as_index=False).agg(
        observed_weeks=("y_raw", lambda values: int(pd.Series(values).notna().sum())),
        missing_week_fraction=("missing_week_indicator", "mean"),
    )
    lines = [
        "# Dengue Weekly Smoke Report",
        "",
        "Dengue is vector-borne. This smoke benchmark tests whether the DSL, hard validation, and structure-selection protocol can be reused on a different surveillance task. It is not a claim that the flu hospitalization SEIR mechanism directly transfers to dengue.",
        "",
        "## Usable Weekly Series",
        "",
        _markdown_table(usable, ["country", "case_definition_standardised", "observed_weeks", "missing_week_fraction"]),
        "",
        "## Model Leaderboard",
        "",
        _markdown_table(summary, ["series_name", "model_name", "mae", "rmse", "mase", "rolling_mae", "log1p_mae"]),
        "",
        "## Answers",
        "",
        f"- Which countries have usable weekly series? `{', '.join(usable['country'].astype(str).tolist())}`.",
        f"- Does any single model dominate? {dominance}",
        f"- Does delayed observation appear useful? Discovery selected `delayed_I` for `{delayed_count}` of `{len(discovery)}` evaluated series.",
        f"- Is fractional memory selected conditionally? Discovery selected fractional memory for `{fractional_count}` of `{len(discovery)}` evaluated series.",
        f"- Are dengue results consistent with structure selection being useful? Constrained discovery is within a practical MAE tie of the best model in `{useful_count}` of `{panel['series_name'].nunique()}` series.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the non-LLM weekly dengue smoke benchmark.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    configure_logging(args.log_level)

    config_path = _resolve_repo_path(args.config)
    config = _load_config(config_path)
    raw_csv = _resolve_repo_path(config["data"]["raw_csv"])
    frame = load_dengue_national_csv(raw_csv)
    specs = []
    for spec in config["data"]["series"]:
        enriched = dict(spec)
        enriched.setdefault("min_weeks", int(config["data"].get("min_weeks", 156)))
        enriched.setdefault("log1p_transform", bool(config["data"].get("log1p_transform", False)))
        specs.append(enriched)
    panel = build_dengue_benchmark_panel(frame, specs)
    if panel.empty:
        raise RuntimeError("No dengue weekly benchmark series were built.")
    processed_dir = ensure_dir(_resolve_repo_path(config["data"]["processed_dir"]))
    panel.to_csv(processed_dir / "dengue_weekly_benchmark_panel.csv", index=False)

    artifact_root = ensure_dir(_resolve_repo_path(config["artifacts"]["root_dir"]))
    leaderboards = []
    for offset, (series_name, series) in enumerate(panel.groupby("series_name", sort=True)):
        leaderboards.append(_run_series(series_name, series, config, artifact_root, int(config["seed"]) + offset))
    summary = pd.concat(leaderboards, ignore_index=True).sort_values(["series_name", "mae", "rolling_mae"]).reset_index(drop=True)
    summary.to_csv(artifact_root / "dengue_weekly_model_summary.csv", index=False)
    winners = summary.groupby("series_name", as_index=False).first()
    winners.to_csv(artifact_root / "dengue_weekly_series_winners.csv", index=False)
    _write_report(summary, panel, _resolve_repo_path(config["artifacts"]["report"]))
    write_json(
        {
            "series_evaluated": summary["series_name"].unique().tolist(),
            "models": list(config["models"]),
            "headline_metrics": list(config["metrics"]["headline"]),
            "smape_headline_metric": False,
            "interpretation": "secondary surveillance structure-selection benchmark; not mechanistic dengue transmission evidence",
        },
        artifact_root / "run_summary.json",
    )


if __name__ == "__main__":
    main()
