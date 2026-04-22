from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml
from src.data.loader import ROBUSTNESS_AGE_GROUPS, filter_series, load_flu_surv_data
from src.data.split import make_chronological_split
from src.discovery.search import SearchConfig
from src.llm import load_llm_config, run_llm_structure_search
from src.llm.orchestrator import write_llm_global_outputs
from src.models.base import FitConfig
from src.utils.io import ensure_dir
from src.utils.logging_utils import configure_logging

logger = logging.getLogger(__name__)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _fit_config(config: dict[str, Any]) -> FitConfig:
    fitting = config["fitting"]
    return FitConfig(
        n_restarts=int(fitting["n_restarts"]),
        rolling_n_restarts=int(fitting["rolling_n_restarts"]),
        maxiter=int(fitting["maxiter"]),
        negative_penalty=float(fitting["negative_penalty"]),
        mass_penalty=float(fitting["mass_penalty"]),
        prior_weight=float(fitting["prior_weight"]),
        laplace_draws=int(fitting["laplace_draws"]),
        uncertainty_method=str(fitting.get("uncertainty_method", "bootstrap")),
        bootstrap_draws=int(fitting.get("bootstrap_draws", 30)),
        bootstrap_n_restarts=int(fitting.get("bootstrap_n_restarts", 0)),
        calibrate_intervals=bool(fitting.get("calibrate_intervals", False)),
        interval_calibration_method=str(fitting.get("interval_calibration_method", "conformal")),
        calibration_draws=int(fitting.get("calibration_draws", 12)),
        calibration_scale_min=float(fitting.get("calibration_scale_min", 0.25)),
        calibration_scale_max=float(fitting.get("calibration_scale_max", 1.25)),
        calibration_scale_grid_size=int(fitting.get("calibration_scale_grid_size", 41)),
        seed=int(config.get("seed", 42)),
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
        score_delay_weight=float(discovery["score_delay_weight"]),
        score_h_observation_weight=float(discovery["score_h_observation_weight"]),
        score_recurrence_weight=float(discovery["score_recurrence_weight"]),
        score_stability_weight=float(discovery["score_stability_weight"]),
        score_multi_split_std_weight=float(discovery["score_multi_split_std_weight"]),
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LLM-V0 structure proposal search.")
    parser.add_argument("--config", required=True, help="Path to configs/llm_v0.yaml")
    parser.add_argument("--series", type=str, default=None, help='Single series name, for example "0-4 yr".')
    parser.add_argument("--all-series", action="store_true", help="Run Overall plus all configured age groups.")
    parser.add_argument("--provider", type=str, default=None, help="Override llm.provider")
    parser.add_argument("--log-level", type=str, default="INFO")
    args = parser.parse_args()
    configure_logging(args.log_level)

    repo_root = REPO_ROOT
    config_path = repo_root / args.config
    config = _load_yaml(config_path)
    llm_config = load_llm_config(config_path)
    if args.provider is not None and args.provider != llm_config.provider:
        raise NotImplementedError("LLM-V0 only implements provider=mock in this PR.")

    if not args.series and not args.all_series:
        raise ValueError("Specify either --series or --all-series.")

    raw_csv = repo_root / config["data"]["raw_csv"]
    frame = load_flu_surv_data(raw_csv)
    fit_config = _fit_config(config)
    search_config = _search_config(config)
    output_root = ensure_dir(llm_config.output_root)

    series_names = [args.series] if args.series else ["Overall", *config["data"].get("age_groups", ROBUSTNESS_AGE_GROUPS)]
    series_outputs = []
    for offset, series_name in enumerate(series_names):
        logger.info("LLM-V0 start series=%s", series_name)
        series_frame = filter_series(frame, age_category=series_name)
        y = series_frame["WEEKLY RATE"].to_numpy(dtype=float)
        split = make_chronological_split(len(y))
        series_output = run_llm_structure_search(
            series_name=series_name,
            y=y,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            llm_config=llm_config,
            artifact_dir=output_root / _slugify(series_name),
            seed=int(config.get("seed", 42)) + offset,
        )
        series_outputs.append(series_output)

    outputs = write_llm_global_outputs(series_outputs, llm_config, output_root)
    logger.info("LLM-V0 outputs written to %s", output_root)
    for name, path in outputs.items():
        logger.info("- %s: %s", name, path)


if __name__ == "__main__":
    main()
