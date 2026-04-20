from __future__ import annotations

import argparse
import logging
import shutil
import time
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.data.loader import build_processed_series, filter_series, load_flu_surv_data, save_processed_outputs
from src.data.split import make_chronological_split
from src.discovery.search import SearchConfig
from src.evaluation.pipeline import run_delayed_observation_family, run_discovery_family, run_model_family
from src.evaluation.reporting import write_benchmark_reports
from src.models.base import FitConfig
from src.models.seihr_hospitalized import HospitalizedSEIHRModel
from src.models.seir_delayed_observation import DelayedObservationSEIRModel
from src.models.seir_deterministic import DeterministicSEIRModel
from src.models.seir_fractional import FractionalSEIRModel
from src.models.seir_probabilistic import ProbabilisticSEIRModel
from src.plotting.plots import plot_model_comparison
from src.utils.io import ensure_dir, write_json
from src.utils.logging_utils import configure_logging
from src.utils.random import set_global_seed

logger = logging.getLogger(__name__)


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _benchmark_level_conformal_enabled(config: dict[str, Any]) -> bool:
    conformal = config.get("uncertainty", {}).get("conformal", {})
    return bool(conformal.get("enabled", False))


def _fit_config(config: dict[str, Any]) -> FitConfig:
    fitting = config["fitting"]
    calibrate_intervals = bool(fitting.get("calibrate_intervals", True))
    if _benchmark_level_conformal_enabled(config) and calibrate_intervals:
        calibrate_intervals = False
    return FitConfig(
        n_restarts=int(fitting["n_restarts"]),
        rolling_n_restarts=int(fitting["rolling_n_restarts"]),
        maxiter=int(fitting["maxiter"]),
        negative_penalty=float(fitting["negative_penalty"]),
        mass_penalty=float(fitting["mass_penalty"]),
        prior_weight=float(fitting["prior_weight"]),
        laplace_draws=int(fitting["laplace_draws"]),
        uncertainty_method=str(fitting.get("uncertainty_method", "laplace")),
        bootstrap_draws=int(fitting.get("bootstrap_draws", 40)),
        bootstrap_n_restarts=int(fitting.get("bootstrap_n_restarts", 0)),
        calibrate_intervals=calibrate_intervals,
        interval_calibration_method=str(fitting.get("interval_calibration_method", "conformal")),
        calibration_draws=int(fitting.get("calibration_draws", 12)),
        calibration_scale_min=float(fitting.get("calibration_scale_min", 0.25)),
        calibration_scale_max=float(fitting.get("calibration_scale_max", 1.25)),
        calibration_scale_grid_size=int(fitting.get("calibration_scale_grid_size", 41)),
        seed=int(config["seed"]),
    )


def _search_config(config: dict[str, Any]) -> SearchConfig:
    discovery = config["discovery"]
    return SearchConfig(
        beam_width=int(discovery["beam_width"]),
        max_rounds=int(discovery["max_rounds"]),
        patience=int(discovery["patience"]),
        rolling_horizons=tuple(int(value) for value in discovery["rolling_horizons"]),
        multi_split_blocks=int(discovery.get("multi_split_blocks", 3)),
        score_param_weight=float(discovery["score_param_weight"]),
        score_compartment_weight=float(discovery["score_compartment_weight"]),
        score_fractional_weight=float(discovery["score_fractional_weight"]),
        score_observation_weight=float(discovery["score_observation_weight"]),
        score_recurrence_weight=float(discovery["score_recurrence_weight"]),
        score_stability_weight=float(discovery["score_stability_weight"]),
        score_multi_split_std_weight=float(discovery.get("score_multi_split_std_weight", 0.5)),
        raw_l2_weight=float(discovery["raw_l2_weight"]),
        seasonality_l2_weight=float(discovery["seasonality_l2_weight"]),
        rho_l2_weight=float(discovery["rho_l2_weight"]),
        init_l2_weight=float(discovery["init_l2_weight"]),
        fractional_alpha_weight=float(discovery["fractional_alpha_weight"]),
        use_age_prior=bool(discovery.get("use_age_prior", True)),
        age_prior_simple_bonus=float(discovery["age_prior_simple_bonus"]),
        age_prior_recurrence_bonus=float(discovery["age_prior_recurrence_bonus"]),
        age_prior_fractional_bonus=float(discovery["age_prior_fractional_bonus"]),
    )


def _slugify(text: str) -> str:
    return (
        text.lower()
        .replace(">=", "ge_")
        .replace("<", "lt_")
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def _run_series_benchmark(
    series_name: str,
    series_frame: pd.DataFrame,
    fit_config: FitConfig,
    search_config: SearchConfig,
    artifact_root: Path,
    horizons: list[int],
    seed: int,
) -> pd.DataFrame:
    y = series_frame["WEEKLY RATE"].to_numpy(dtype=float)
    split = make_chronological_split(len(y))
    series_artifact_root = ensure_dir(artifact_root / _slugify(series_name))
    series_start = time.perf_counter()
    logger.info(
        "Starting series=%s n_obs=%d train_end=%d val_end=%d artifacts=%s",
        series_name,
        len(y),
        split.train_end,
        split.val_end,
        series_artifact_root,
    )

    results = []
    logger.info("Running model=deterministic_seir series=%s", series_name)
    deterministic = run_model_family(
        model_factory=lambda: DeterministicSEIRModel(fit_config),
        series_name=series_name,
        y=y,
        split=split,
        horizons=horizons,
        artifact_dir=series_artifact_root / "deterministic_seir",
        seed=seed,
    )
    results.append(deterministic["comparison_row"])
    logger.info(
        "Completed model=deterministic_seir series=%s test_mae=%.6f",
        series_name,
        deterministic["comparison_row"]["test_mae"],
    )

    logger.info("Running model=probabilistic_seir series=%s", series_name)
    probabilistic = run_model_family(
        model_factory=lambda: ProbabilisticSEIRModel(fit_config),
        series_name=series_name,
        y=y,
        split=split,
        horizons=horizons,
        artifact_dir=series_artifact_root / "probabilistic_seir",
        seed=seed + 11,
    )
    results.append(probabilistic["comparison_row"])
    logger.info(
        "Completed model=probabilistic_seir series=%s test_mae=%.6f",
        series_name,
        probabilistic["comparison_row"]["test_mae"],
    )

    logger.info("Running model=hospitalized_seihr series=%s", series_name)
    hospitalized = run_model_family(
        model_factory=lambda: HospitalizedSEIHRModel(fit_config),
        series_name=series_name,
        y=y,
        split=split,
        horizons=horizons,
        artifact_dir=series_artifact_root / "hospitalized_seihr",
        seed=seed + 17,
    )
    results.append(hospitalized["comparison_row"])
    logger.info(
        "Completed model=hospitalized_seihr series=%s test_mae=%.6f",
        series_name,
        hospitalized["comparison_row"]["test_mae"],
    )

    logger.info("Running model=delayed_observation_seir series=%s", series_name)
    delayed = run_delayed_observation_family(
        series_name=series_name,
        y=y,
        split=split,
        fit_config=fit_config,
        horizons=horizons,
        artifact_dir=series_artifact_root / "delayed_observation_seir",
        seed=seed + 19,
    )
    results.append(delayed["comparison_row"])
    logger.info(
        "Completed model=delayed_observation_seir series=%s test_mae=%.6f",
        series_name,
        delayed["comparison_row"]["test_mae"],
    )

    logger.info("Running model=fractional_seir series=%s", series_name)
    fractional = run_model_family(
        model_factory=lambda: FractionalSEIRModel(fit_config),
        series_name=series_name,
        y=y,
        split=split,
        horizons=horizons,
        artifact_dir=series_artifact_root / "fractional_seir",
        seed=seed + 23,
    )
    results.append(fractional["comparison_row"])
    logger.info(
        "Completed model=fractional_seir series=%s test_mae=%.6f",
        series_name,
        fractional["comparison_row"]["test_mae"],
    )

    logger.info("Running model=constrained_structure_discovery series=%s", series_name)
    discovery = run_discovery_family(
        y=y,
        series_name=series_name,
        split=split,
        fit_config=fit_config,
        search_config=search_config,
        horizons=horizons,
        artifact_dir=series_artifact_root / "constrained_structure_discovery",
        seed=seed + 37,
    )
    results.append(discovery["comparison_row"])
    logger.info(
        "Completed model=constrained_structure_discovery series=%s test_mae=%.6f",
        series_name,
        discovery["comparison_row"]["test_mae"],
    )

    leaderboard = pd.DataFrame(results).sort_values(["test_mae", "test_rmse"], ascending=[True, True]).reset_index(drop=True)
    leaderboard.insert(0, "series_name", series_name)
    leaderboard.to_csv(series_artifact_root / "leaderboard.csv", index=False)
    plot_model_comparison(leaderboard, series_artifact_root / "model_comparison.png")
    logger.info(
        "Finished series=%s winner=%s elapsed=%.1fs leaderboard=%s",
        series_name,
        leaderboard.iloc[0]["model_name"],
        time.perf_counter() - series_start,
        series_artifact_root / "leaderboard.csv",
    )
    return leaderboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the influenza forecasting benchmark.")
    parser.add_argument("--config", type=str, required=True, help="Path to the YAML config.")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging verbosity: DEBUG, INFO, WARNING.")
    args = parser.parse_args()
    configure_logging(args.log_level)

    repo_root = Path(__file__).resolve().parent
    logger.info("Benchmark start config=%s repo_root=%s", args.config, repo_root)
    config = _load_config(repo_root / args.config)
    set_global_seed(int(config["seed"]))
    logger.info("Global seed=%d", int(config["seed"]))

    raw_csv_path = repo_root / config["data"]["raw_csv"]
    raw_output_dir = ensure_dir(repo_root / "data" / "raw")
    copied_raw_csv = raw_output_dir / raw_csv_path.name
    if raw_csv_path.exists() and raw_csv_path.resolve() != copied_raw_csv.resolve():
        shutil.copy2(raw_csv_path, copied_raw_csv)

    frame = load_flu_surv_data(raw_csv_path)
    processed = build_processed_series(
        frame=frame,
        include_age_groups=bool(config["data"]["include_age_robustness"]),
        age_groups=config["data"]["age_groups"],
    )
    save_processed_outputs(processed, repo_root / config["data"]["processed_dir"])
    logger.info(
        "Processed data saved to %s with series=%s",
        repo_root / config["data"]["processed_dir"],
        sorted(processed["series_name"].unique().tolist()),
    )

    if _benchmark_level_conformal_enabled(config) and bool(config["fitting"].get("calibrate_intervals", True)):
        logger.info(
            "Benchmark-level conformal postprocess is enabled; disabling fitting-level interval calibration to avoid double calibration."
        )

    fit_config = _fit_config(config)
    search_config = _search_config(config)
    horizons = [int(value) for value in config["evaluation"]["horizons"]]
    artifact_root = ensure_dir(repo_root / config["artifacts"]["root_dir"])

    benchmark_leaderboards = []
    overall_series = filter_series(frame, age_category="Overall")
    overall_board = _run_series_benchmark(
        series_name="Overall",
        series_frame=overall_series,
        fit_config=fit_config,
        search_config=search_config,
        artifact_root=artifact_root,
        horizons=horizons,
        seed=int(config["seed"]),
    )
    benchmark_leaderboards.append(overall_board)
    combined_so_far = pd.concat(benchmark_leaderboards, ignore_index=True)
    combined_so_far.to_csv(artifact_root / "benchmark_leaderboard_partial.csv", index=False)
    logger.info("Wrote partial leaderboard=%s", artifact_root / "benchmark_leaderboard_partial.csv")

    if bool(config["data"]["include_age_robustness"]):
        for age_group in config["data"]["age_groups"]:
            logger.info("Starting age-group robustness series=%s", age_group)
            age_series = filter_series(frame, age_category=age_group)
            age_board = _run_series_benchmark(
                series_name=age_group,
                series_frame=age_series,
                fit_config=fit_config,
                search_config=search_config,
                artifact_root=artifact_root / "robustness",
                horizons=horizons,
                seed=int(config["seed"]) + 1000 + len(benchmark_leaderboards),
            )
            benchmark_leaderboards.append(age_board)
            combined_so_far = pd.concat(benchmark_leaderboards, ignore_index=True)
            combined_so_far.to_csv(artifact_root / "benchmark_leaderboard_partial.csv", index=False)
            logger.info(
                "Completed age-group series=%s partial_leaderboard=%s",
                age_group,
                artifact_root / "benchmark_leaderboard_partial.csv",
            )

    combined_board = pd.concat(benchmark_leaderboards, ignore_index=True)
    combined_board.to_csv(artifact_root / "benchmark_leaderboard.csv", index=False)
    summary_frame, winners_frame, recommendation_frame, calibration_frame = write_benchmark_reports(artifact_root)
    write_json(
        {
            "seed": int(config["seed"]),
            "series_evaluated": combined_board["series_name"].unique().tolist(),
            "leaderboard_path": str(artifact_root / "benchmark_leaderboard.csv"),
            "summary_path": str(artifact_root / "benchmark_model_summary.csv"),
            "winners_path": str(artifact_root / "benchmark_series_winners.csv"),
            "recommendation_path": str(artifact_root / "age_group_recommendation.csv"),
            "v3_summary_path": str(artifact_root / "v3_result_summary.md"),
            "probabilistic_calibration_path": str(artifact_root / "probabilistic_calibration_summary.csv"),
        },
        artifact_root / "run_summary.json",
    )
    logger.info(
        "Benchmark completed series_count=%d leaderboard=%s summary=%s winners=%s recommendations=%s v3_summary=%s",
        len(combined_board["series_name"].unique()),
        artifact_root / "benchmark_leaderboard.csv",
        artifact_root / "benchmark_model_summary.csv",
        artifact_root / "benchmark_series_winners.csv",
        artifact_root / "age_group_recommendation.csv",
        artifact_root / "v3_result_summary.md",
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Benchmark interrupted by user.")
        raise
    except Exception:
        logger.exception("Benchmark failed.")
        raise
