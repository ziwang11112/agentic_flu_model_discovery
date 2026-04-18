from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

from src.data.split import ChronologicalSplit
from src.discovery.model import DiscoveryCompartmentModel
from src.discovery.search import SearchConfig, discovery_regularization_config, run_structure_search
from src.evaluation.metrics import point_metrics, summarise_probabilistic_metrics
from src.evaluation.rolling import mean_rolling_metric, rolling_metrics_by_horizon, rolling_origin_forecasts
from src.models.base import BaseEpidemicModel, FitConfig
from src.plotting.plots import (
    plot_full_series_fit,
    plot_leaderboard,
    plot_residuals,
    plot_rolling_forecasts,
    plot_structure_diagram,
)
from src.utils.io import ensure_dir, write_json

logger = logging.getLogger(__name__)


def _forecast_frame(
    y: np.ndarray,
    full_predictions: np.ndarray,
    split: ChronologicalSplit,
    test_predictions: np.ndarray,
    interval_map: dict[str, tuple[np.ndarray, np.ndarray]] | None = None,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "t": np.arange(len(y)),
            "actual": y,
            "full_fit_prediction": full_predictions,
            "test_forecast_prediction": test_predictions,
            "segment": np.where(
                np.arange(len(y)) < split.train_end,
                "train",
                np.where(np.arange(len(y)) < split.val_end, "validation", "test"),
            ),
        }
    )

    if interval_map is not None:
        for level, (lower, upper) in interval_map.items():
            frame[f"lower_{level}"] = lower
            frame[f"upper_{level}"] = upper
    return frame


def run_model_family(
    model_factory: Callable[[], BaseEpidemicModel],
    series_name: str,
    y: np.ndarray,
    split: ChronologicalSplit,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    """Fit, evaluate, and persist one model family."""
    ensure_dir(artifact_dir)
    rng = np.random.default_rng(seed)
    model_start = time.perf_counter()
    model_name = model_factory().model_name
    logger.info("Model family start model=%s series=%s", model_name, series_name)

    train_model = model_factory()
    train_fit = train_model.fit(y[split.train_slice], rng)
    validation_rollout = train_model.simulate(train_fit.raw_params, split.val_end)
    train_predictions = validation_rollout.predictions[split.train_slice]
    validation_predictions = validation_rollout.predictions[split.val_slice]

    trainval_model = model_factory()
    trainval_fit = trainval_model.fit(y[: split.val_end], rng, warm_start=train_fit.raw_params)
    test_rollout = trainval_model.simulate(trainval_fit.raw_params, len(y))
    test_predictions = test_rollout.predictions[split.test_slice]

    full_model = model_factory()
    full_fit = full_model.fit(
        y,
        rng,
        warm_start=trainval_fit.raw_params,
        n_restarts=full_model.fit_config.rolling_n_restarts,
    )
    full_predictions = full_fit.simulation.predictions
    residuals = y - full_predictions

    interval_map_full: dict[str, tuple[np.ndarray, np.ndarray]] | None = None
    probabilistic_metrics = summarise_probabilistic_metrics(y[split.test_slice], None, None)

    if hasattr(trainval_model, "predictive_summary"):
        predictive = trainval_model.predictive_summary(y[: split.val_end], trainval_fit, len(y), rng)  # type: ignore[attr-defined]
        interval_map_full = predictive["intervals"]
        interval_map_test = {
            level: (bounds[0][split.test_slice], bounds[1][split.test_slice])
            for level, bounds in interval_map_full.items()
        }
        test_scale = trainval_fit.params["obs_scale"]
        nll = float(
            -np.sum(
                student_t.logpdf(
                    y[split.test_slice],
                    df=getattr(trainval_model, "df"),
                    loc=test_rollout.predictions[split.test_slice],
                    scale=test_scale,
                )
            )
        )
        probabilistic_metrics = summarise_probabilistic_metrics(y[split.test_slice], nll, interval_map_test)
        probabilistic_metrics["uncertainty_method"] = predictive["method"]
        probabilistic_metrics["uncertainty_draws"] = predictive["draw_count"]

    logger.info("Model family rolling-origin start model=%s series=%s", train_model.model_name, series_name)
    rolling_frame = rolling_origin_forecasts(
        model_factory=model_factory,
        y=y,
        horizons=horizons,
        seed=seed + 101,
        initial_train_size=split.train_end,
    )
    rolling_frame.to_csv(artifact_dir / "rolling_origin_forecasts.csv", index=False)

    forecast_frame = _forecast_frame(y, full_predictions, split, test_rollout.predictions, interval_map_full)
    forecast_frame.to_csv(artifact_dir / "forecast_trace.csv", index=False)

    plot_full_series_fit(
        np.arange(len(y)),
        y,
        full_predictions,
        split,
        title=f"{series_name}: {train_model.model_name} full-series fit",
        path=artifact_dir / "full_series_fit.png",
    )
    plot_residuals(
        np.arange(len(y)),
        residuals,
        title=f"{series_name}: {train_model.model_name} residuals",
        path=artifact_dir / "residuals.png",
    )
    plot_rolling_forecasts(
        rolling_frame,
        title=f"{series_name}: {train_model.model_name}",
        path=artifact_dir / "rolling_origin.png",
    )

    summary = {
        "model_name": train_model.model_name,
        "series_name": series_name,
        "complexity": {
            "num_free_params": train_fit.param_count,
            "num_compartments": len(train_model.compartment_names),
        },
        "train_metrics": point_metrics(y[split.train_slice], train_predictions),
        "validation_metrics": point_metrics(y[split.val_slice], validation_predictions),
        "test_metrics": point_metrics(y[split.test_slice], test_predictions),
        "probabilistic_metrics": probabilistic_metrics,
        "rolling_origin_metrics": rolling_metrics_by_horizon(rolling_frame),
        "rolling_origin_summary": {
            "mean_mae": mean_rolling_metric(rolling_frame, "mae"),
            "mean_rmse": mean_rolling_metric(rolling_frame, "rmse"),
        },
        "fit_objectives": {
            "train": train_fit.objective,
            "train_plus_validation": trainval_fit.objective,
            "full_series": full_fit.objective,
        },
        "best_full_params": full_fit.params,
    }
    write_json(summary, artifact_dir / "metrics.json")
    logger.info(
        "Model family done model=%s series=%s test_mae=%.6f rolling_mean_mae=%.6f elapsed=%.1fs",
        train_model.model_name,
        series_name,
        summary["test_metrics"]["mae"],
        summary["rolling_origin_summary"]["mean_mae"],
        time.perf_counter() - model_start,
    )
    return {
        "summary": summary,
        "comparison_row": {
            "model_name": train_model.model_name,
            "test_mae": summary["test_metrics"]["mae"],
            "test_rmse": summary["test_metrics"]["rmse"],
            "test_smape": summary["test_metrics"]["smape"],
            "num_free_params": summary["complexity"]["num_free_params"],
            "num_compartments": summary["complexity"]["num_compartments"],
        },
    }


def run_discovery_family(
    y: np.ndarray,
    series_name: str,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    """Run the constrained search and then evaluate the best discovered model."""
    ensure_dir(artifact_dir)
    discovery_start = time.perf_counter()
    logger.info("Discovery search start series=%s artifacts=%s", series_name, artifact_dir)
    outcome = run_structure_search(
        series_name=series_name,
        y_train=y[split.train_slice],
        y_val=y[split.val_slice],
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
    )
    plot_leaderboard(outcome.leaderboard, artifact_dir / "leaderboard.png")
    plot_structure_diagram(outcome.best_spec, artifact_dir / "best_structure.png")
    logger.info(
        "Discovery search done series=%s best_spec=%s elapsed=%.1fs",
        series_name,
        outcome.best_spec.spec_key,
        time.perf_counter() - discovery_start,
    )
    regularization_config = discovery_regularization_config(search_config)

    def model_factory() -> BaseEpidemicModel:
        return DiscoveryCompartmentModel(outcome.best_spec, fit_config, regularization_config)

    run_result = run_model_family(
        model_factory=model_factory,
        series_name=series_name,
        y=y,
        split=split,
        horizons=horizons,
        artifact_dir=artifact_dir,
        seed=seed + 307,
    )
    summary = run_result["summary"]
    summary["model_name"] = "constrained_structure_discovery"
    summary["best_spec"] = {
        "structure_name": outcome.best_spec.structure_name,
        "fractional": outcome.best_spec.fractional,
        "observation_map": outcome.best_spec.observation_map,
    }
    summary["search_best_record"] = outcome.best_record
    write_json(summary, artifact_dir / "metrics.json")

    run_result["summary"] = summary
    run_result["comparison_row"]["model_name"] = "constrained_structure_discovery"
    return run_result
