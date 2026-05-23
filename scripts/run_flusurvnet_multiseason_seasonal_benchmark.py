from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "agentic_flu_model_discovery_matplotlib"))

from run_experiment import _fit_config, _search_config, _slugify  # noqa: E402
from src.baselines.forecasting import FORECAST_BASELINE_NAMES, create_forecast_baseline  # noqa: E402
from src.data.loader import (  # noqa: E402
    SEASON_MODE_SEPARATE,
    build_flu_series_frames,
    build_processed_series,
    load_flu_surv_data,
    resolve_data_path,
    save_processed_outputs,
)
from src.data.split import make_chronological_split  # noqa: E402
from src.evaluation.baseline_pipeline import run_equal_weight_point_ensemble_family, run_forecast_baseline_family  # noqa: E402
from src.evaluation.pipeline import (  # noqa: E402
    run_delayed_observation_family,
    run_discovery_family,
    run_exhaustive_discovery_family,
    run_model_family,
    run_no_observation_search_discovery_family,
    run_no_stability_discovery_family,
    run_random_discovery_family,
    run_validation_only_discovery_family,
)
from src.evaluation.reporting import write_benchmark_reports  # noqa: E402
from src.models.seihr_hospitalized import HospitalizedSEIHRModel  # noqa: E402
from src.models.seir_delayed_observation import DelayedObservationSEIRModel  # noqa: E402
from src.models.seir_deterministic import DeterministicSEIRModel  # noqa: E402
from src.models.seir_fractional import FractionalSEIRModel  # noqa: E402
from src.models.seir_probabilistic import ProbabilisticSEIRModel  # noqa: E402
from src.plotting.plots import plot_model_comparison  # noqa: E402
from src.utils.io import ensure_dir, write_json  # noqa: E402
from src.utils.logging_utils import configure_logging  # noqa: E402
from src.utils.paths import repo_relative_path  # noqa: E402

logger = logging.getLogger(__name__)


DEFAULT_MODELS = [
    "deterministic_seir",
    "probabilistic_seir",
    "hospitalized_seihr",
    "delayed_observation_seir",
    "fractional_seir",
    "constrained_structure_discovery",
]


def _repo_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _completed_seasons(path: Path, splits: Iterable[str] | None = None) -> list[str]:
    frame = pd.read_csv(path)
    selected = frame.loc[frame["status"] == "complete"].copy()
    if splits:
        requested = {str(split) for split in splits}
        selected = selected.loc[selected["recommended_split"].astype(str).isin(requested)].copy()
    return selected["season"].astype(str).tolist()


def _parse_series_name(series_name: str) -> tuple[str, str]:
    if " / " not in series_name:
        return "", series_name
    season, age_group = series_name.split(" / ", 1)
    return season, age_group


def _model_names(config: dict[str, Any]) -> list[str]:
    configured = config.get("benchmark", {}).get("models")
    if configured is None:
        return list(DEFAULT_MODELS)
    model_names = [str(value) for value in configured]
    if "equal_weight_point_ensemble" in model_names and model_names[-1] != "equal_weight_point_ensemble":
        logger.warning("Moving equal_weight_point_ensemble to the end of benchmark.models so member artifacts exist.")
        model_names = [name for name in model_names if name != "equal_weight_point_ensemble"]
        model_names.append("equal_weight_point_ensemble")
    return model_names


def _selected_series_filter(config: dict[str, Any]) -> set[str]:
    return {str(value) for value in config.get("benchmark", {}).get("series", [])}


def _ensemble_members(config: dict[str, Any]) -> list[str] | None:
    configured = config.get("benchmark", {}).get("ensemble_members")
    if configured is None:
        return None
    return [str(value) for value in configured]


def _run_one_model(
    *,
    model_name: str,
    series_name: str,
    y,
    split,
    fit_config,
    search_config,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
    ensemble_members: list[str] | None = None,
) -> dict[str, Any]:
    if model_name in FORECAST_BASELINE_NAMES:
        return run_forecast_baseline_family(
            baseline_factory=lambda model_name=model_name, seed=seed: create_forecast_baseline(model_name, seed=seed),
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "equal_weight_point_ensemble":
        return run_equal_weight_point_ensemble_family(
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
            ensemble_members=ensemble_members,
        )
    if model_name == "deterministic_seir":
        return run_model_family(
            model_factory=lambda: DeterministicSEIRModel(fit_config),
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "probabilistic_seir":
        return run_model_family(
            model_factory=lambda: ProbabilisticSEIRModel(fit_config),
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "hospitalized_seihr":
        return run_model_family(
            model_factory=lambda: HospitalizedSEIHRModel(fit_config),
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "delayed_observation_seir":
        return run_delayed_observation_family(
            series_name=series_name,
            y=y,
            split=split,
            fit_config=fit_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "fractional_seir":
        return run_model_family(
            model_factory=lambda: FractionalSEIRModel(fit_config),
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "constrained_structure_discovery":
        return run_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "random_structure_discovery":
        return run_random_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "exhaustive_structure_discovery":
        return run_exhaustive_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "validation_only_structure_selection":
        return run_validation_only_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "no_observation_search_discovery":
        return run_no_observation_search_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "no_stability_discovery":
        return run_no_stability_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    raise ValueError(f"Unsupported model for FluSurv-NET multi-season benchmark: {model_name}")


def _run_series(
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
    split = make_chronological_split(len(series_frame))
    y = series_frame["WEEKLY RATE"].to_numpy(dtype=float)
    series_root = ensure_dir(artifact_root / _slugify(series_name))
    series_frame.to_csv(series_root / "input_series.csv", index=False)
    ensemble_members = _ensemble_members(config)

    results: list[dict[str, Any]] = []
    for offset, model_name in enumerate(_model_names(config)):
        logger.info("Multi-season seasonal series=%s model=%s", series_name, model_name)
        result = _run_one_model(
            model_name=model_name,
            series_name=series_name,
            y=y,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=series_root / model_name,
            seed=seed + offset * 101,
            ensemble_members=ensemble_members,
        )
        results.append(result["comparison_row"])

    leaderboard = pd.DataFrame(results).sort_values(["test_mae", "test_rmse"], ascending=[True, True]).reset_index(drop=True)
    leaderboard.insert(0, "series_name", series_name)
    leaderboard.to_csv(series_root / "leaderboard.csv", index=False)
    plot_model_comparison(leaderboard, series_root / "model_comparison.png")
    return leaderboard


def build_seasonal_recommendation_summary(recommendations: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if recommendations.empty:
        return pd.DataFrame()

    enriched = recommendations.copy()
    parsed = enriched["series_name"].map(_parse_series_name)
    enriched["season"] = parsed.map(lambda item: item[0])
    enriched["age_group"] = parsed.map(lambda item: item[1])

    for age_group, subset in enriched.groupby("age_group", sort=True):
        recommended_counts = Counter(subset["recommended_model"].astype(str).tolist())
        best_test_counts = Counter(subset["best_test_model"].astype(str).tolist())
        best_rolling_counts = Counter(subset["best_rolling_model"].astype(str).tolist())
        rows.append(
            {
                "age_group": age_group,
                "num_seasons": int(subset["season"].nunique()),
                "recommended_model_mode": recommended_counts.most_common(1)[0][0],
                "recommended_model_frequency": recommended_counts.most_common(1)[0][1] / len(subset),
                "best_test_model_mode": best_test_counts.most_common(1)[0][0],
                "best_test_model_frequency": best_test_counts.most_common(1)[0][1] / len(subset),
                "best_rolling_model_mode": best_rolling_counts.most_common(1)[0][0],
                "best_rolling_model_frequency": best_rolling_counts.most_common(1)[0][1] / len(subset),
            }
        )

    return pd.DataFrame(rows).sort_values("age_group").reset_index(drop=True)


def _markdown_table(frame: pd.DataFrame, max_rows: int = 30) -> str:
    if frame.empty:
        return "_None._"
    shown = frame.head(max_rows).copy()
    lines = [
        "| " + " | ".join(shown.columns.astype(str)) + " |",
        "| " + " | ".join(["---"] * len(shown.columns)) + " |",
    ]
    for _, row in shown.iterrows():
        values = []
        for value in row.tolist():
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append("" if pd.isna(value) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    if len(frame) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(frame)} rows._")
    return "\n".join(lines)


def write_multiseason_report(
    *,
    report_path: Path,
    seasons: list[str],
    models: list[str],
    recommendations: pd.DataFrame,
    seasonal_summary: pd.DataFrame,
    artifact_root: Path,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    recommendation_view = recommendations.copy()
    if not recommendation_view.empty:
        parsed = recommendation_view["series_name"].map(_parse_series_name)
        recommendation_view.insert(1, "season", parsed.map(lambda item: item[0]))
        recommendation_view.insert(2, "age_group", parsed.map(lambda item: item[1]))
        recommendation_view = recommendation_view.loc[
            :,
            [
                "series_name",
                "season",
                "age_group",
                "recommended_model",
                "decision_type",
                "best_test_model",
                "best_rolling_model",
            ],
        ]

    lines = [
        "# FluSurv-NET Multi-Season Seasonal Benchmark",
        "",
        "This benchmark evaluates each completed FluSurv-NET season as its own within-season trajectory.",
        "It is intended as a cross-season robustness supplement, not as a direct previous-season-to-future-season transfer forecast.",
        "",
        f"Artifact root: `{repo_relative_path(artifact_root, REPO_ROOT)}`",
        f"Completed seasons included: {', '.join(seasons)}",
        f"Models: {', '.join(models)}",
        "",
        "## Age-Group Recommendation Modes",
        "",
        _markdown_table(seasonal_summary),
        "",
        "## Season-Level Recommendations",
        "",
        _markdown_table(recommendation_view),
        "",
    ]
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run season-separated FluSurv-NET multi-season benchmark.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--max-series", type=int, default=None, help="Optional smoke-test cap on number of season/age series.")
    args = parser.parse_args()
    configure_logging(args.log_level)

    config = _load_config(REPO_ROOT / args.config)
    data_config = config["data"]
    raw_csv = resolve_data_path(REPO_ROOT, data_config["raw_csv"])
    completed_path = _repo_path(data_config.get("completed_seasons_path", "data/processed_flusurvnet_multiseason/recommended_completed_seasons.csv"))
    seasons = _completed_seasons(completed_path, splits=data_config.get("recommended_splits"))
    if not seasons:
        raise RuntimeError(f"No completed seasons found in {completed_path}")

    frame = load_flu_surv_data(raw_csv)
    processed = build_processed_series(
        frame=frame,
        include_age_groups=bool(data_config.get("include_age_robustness", True)),
        age_groups=data_config["age_groups"],
        seasons=seasons,
        season_mode=SEASON_MODE_SEPARATE,
    )
    save_processed_outputs(processed, _repo_path(data_config["processed_dir"]))

    artifact_root = ensure_dir(_repo_path(config["artifacts"]["root_dir"]))
    selected_series = _selected_series_filter(config)
    series_items = build_flu_series_frames(
        frame=frame,
        include_age_groups=bool(data_config.get("include_age_robustness", True)),
        age_groups=data_config["age_groups"],
        seasons=seasons,
        season_mode=SEASON_MODE_SEPARATE,
    )
    if selected_series:
        series_items = [item for item in series_items if str(item["series_name"]) in selected_series]
    if args.max_series is not None:
        series_items = series_items[: args.max_series]

    leaderboards = []
    for index, item in enumerate(series_items):
        series_frame = item["frame"]
        if bool(series_frame.empty):  # type: ignore[union-attr]
            logger.warning("Skipping empty series=%s", item["series_name"])
            continue
        leaderboards.append(
            _run_series(
                series_name=str(item["series_name"]),
                series_frame=series_frame,  # type: ignore[arg-type]
                config=config,
                artifact_root=artifact_root,
                seed=int(config.get("seed", 42)) + index * 1009,
            )
        )

    if not leaderboards:
        raise RuntimeError("No FluSurv-NET multi-season series were evaluated.")

    combined = pd.concat(leaderboards, ignore_index=True)
    combined.to_csv(artifact_root / "benchmark_leaderboard.csv", index=False)
    summary, winners, recommendations, calibration = write_benchmark_reports(artifact_root)
    seasonal_summary = build_seasonal_recommendation_summary(recommendations)
    seasonal_summary.to_csv(artifact_root / "multiseason_age_recommendation_modes.csv", index=False)
    write_multiseason_report(
        report_path=_repo_path(config["artifacts"].get("report", "reports/flusurvnet_multiseason_seasonal_benchmark_report.md")),
        seasons=seasons,
        models=_model_names(config),
        recommendations=recommendations,
        seasonal_summary=seasonal_summary,
        artifact_root=artifact_root,
    )
    write_json(
        {
            "seed": int(config.get("seed", 42)),
            "data_source": "FluSurv-NET RESP-NET transformed multi-season CSV",
            "completed_seasons_path": repo_relative_path(completed_path, REPO_ROOT),
            "seasons": seasons,
            "models": _model_names(config),
            "series_evaluated": combined["series_name"].unique().tolist(),
            "leaderboard_path": repo_relative_path(artifact_root / "benchmark_leaderboard.csv", REPO_ROOT),
            "summary_path": repo_relative_path(artifact_root / "benchmark_model_summary.csv", REPO_ROOT),
            "winners_path": repo_relative_path(artifact_root / "benchmark_series_winners.csv", REPO_ROOT),
            "recommendation_path": repo_relative_path(artifact_root / "age_group_recommendation.csv", REPO_ROOT),
            "seasonal_modes_path": repo_relative_path(
                artifact_root / "multiseason_age_recommendation_modes.csv",
                REPO_ROOT,
            ),
            "calibration_rows": int(len(calibration)),
            "summary_rows": int(len(summary)),
            "winner_rows": int(len(winners)),
            "recommendation_rows": int(len(recommendations)),
        },
        artifact_root / "run_summary.json",
    )


if __name__ == "__main__":
    main()
