from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from typing import Any

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from run_experiment import _fit_config, _search_config, _slugify
from src.data.dengue import (
    build_dengue_processed_series,
    load_dengue_surveillance_data,
    save_dengue_processed_outputs,
)
from src.data.loader import resolve_data_path
from src.data.split import make_chronological_split
from src.evaluation.pipeline import run_delayed_observation_family, run_discovery_family, run_model_family
from src.evaluation.reporting import write_benchmark_reports
from src.models.seir_deterministic import DeterministicSEIRModel
from src.models.seir_fractional import FractionalSEIRModel
from src.models.seir_probabilistic import ProbabilisticSEIRModel
from src.plotting.plots import plot_model_comparison
from src.utils.io import ensure_dir, write_json
from src.utils.logging_utils import configure_logging

logger = logging.getLogger(__name__)


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _run_dengue_series(
    *,
    series_name: str,
    series_frame: pd.DataFrame,
    config: dict[str, Any],
    artifact_root: Path,
    seed: int,
) -> pd.DataFrame:
    fit_config = _fit_config(config)
    search_config = _search_config(config)
    horizons = [int(value) for value in config["evaluation"]["horizons"]]
    models = [str(value) for value in config.get("benchmark", {}).get("models", ["deterministic_seir", "constrained_structure_discovery"])]
    y = series_frame["observed_value"].to_numpy(dtype=float)
    split = make_chronological_split(len(y))
    series_root = ensure_dir(artifact_root / _slugify(series_name))
    results: list[dict[str, Any]] = []

    for offset, model_name in enumerate(models):
        logger.info("Dengue smoke start series=%s model=%s", series_name, model_name)
        if model_name == "deterministic_seir":
            result = run_model_family(
                model_factory=lambda: DeterministicSEIRModel(fit_config),
                series_name=series_name,
                y=y,
                split=split,
                horizons=horizons,
                artifact_dir=series_root / model_name,
                seed=seed + offset,
            )
        elif model_name == "probabilistic_seir":
            result = run_model_family(
                model_factory=lambda: ProbabilisticSEIRModel(fit_config),
                series_name=series_name,
                y=y,
                split=split,
                horizons=horizons,
                artifact_dir=series_root / model_name,
                seed=seed + offset,
            )
        elif model_name == "delayed_observation_seir":
            result = run_delayed_observation_family(
                series_name=series_name,
                y=y,
                split=split,
                fit_config=fit_config,
                horizons=horizons,
                artifact_dir=series_root / model_name,
                seed=seed + offset,
            )
        elif model_name == "fractional_seir":
            result = run_model_family(
                model_factory=lambda: FractionalSEIRModel(fit_config),
                series_name=series_name,
                y=y,
                split=split,
                horizons=horizons,
                artifact_dir=series_root / model_name,
                seed=seed + offset,
            )
        elif model_name == "constrained_structure_discovery":
            result = run_discovery_family(
                y=y,
                series_name=series_name,
                split=split,
                fit_config=fit_config,
                search_config=search_config,
                horizons=horizons,
                artifact_dir=series_root / model_name,
                seed=seed + offset,
            )
        else:
            raise ValueError(f"Unsupported dengue smoke model: {model_name}")
        results.append(result["comparison_row"])

    leaderboard = pd.DataFrame(results).sort_values(["test_mae", "test_rmse"], ascending=[True, True]).reset_index(drop=True)
    leaderboard.insert(0, "series_name", series_name)
    leaderboard.to_csv(series_root / "leaderboard.csv", index=False)
    plot_model_comparison(leaderboard, series_root / "model_comparison.png")
    return leaderboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a non-LLM dengue smoke benchmark on tidy weekly data.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    configure_logging(args.log_level)

    repo_root = REPO_ROOT
    config = _load_config(repo_root / args.config)
    data_config = config["data"]
    raw_csv = resolve_data_path(repo_root, data_config["raw_csv"])
    raw_frame = load_dengue_surveillance_data(
        raw_csv,
        series_column=data_config.get("series_column"),
        value_column=data_config.get("value_column"),
        year_column=data_config.get("year_column"),
        week_column=data_config.get("week_column"),
        date_column=data_config.get("date_column"),
        default_series_name=str(data_config.get("default_series_name", "Dengue")),
    )
    processed = build_dengue_processed_series(
        raw_frame,
        selected_series=data_config.get("series"),
        min_observations=int(data_config.get("min_observations", 12)),
    )
    if processed.empty:
        raise RuntimeError("No dengue series passed the configured selection and min_observations filters.")

    processed_dir = repo_root / data_config.get("processed_dir", "data/processed_dengue_smoke")
    save_dengue_processed_outputs(processed, processed_dir)
    artifact_root = ensure_dir(repo_root / config.get("artifacts", {}).get("root_dir", "artifacts_dengue_smoke"))

    leaderboards = []
    for offset, (series_name, series_frame) in enumerate(processed.groupby("series_name", sort=True)):
        leaderboards.append(
            _run_dengue_series(
                series_name=str(series_name),
                series_frame=series_frame,
                config=config,
                artifact_root=artifact_root,
                seed=int(config.get("seed", 42)) + offset,
            )
        )

    combined = pd.concat(leaderboards, ignore_index=True)
    combined.to_csv(artifact_root / "benchmark_leaderboard.csv", index=False)
    summary, winners, recommendations, _ = write_benchmark_reports(artifact_root)
    write_json(
        {
            "seed": int(config.get("seed", 42)),
            "data_source": "dengue",
            "series_evaluated": combined["series_name"].unique().tolist(),
            "processed_path": str(processed_dir / "dengue_benchmark_series.csv"),
            "leaderboard_path": str(artifact_root / "benchmark_leaderboard.csv"),
            "summary_path": str(artifact_root / "benchmark_model_summary.csv"),
            "winners_path": str(artifact_root / "benchmark_series_winners.csv"),
            "recommendation_path": str(artifact_root / "age_group_recommendation.csv"),
            "num_summary_rows": int(len(summary)),
            "num_winner_rows": int(len(winners)),
            "num_recommendation_rows": int(len(recommendations)),
        },
        artifact_root / "run_summary.json",
    )


if __name__ == "__main__":
    main()
