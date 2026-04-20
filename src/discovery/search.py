from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
import time
from typing import Any

import numpy as np
import pandas as pd

from src.discovery.model import DiscoveryCompartmentModel, DiscoveryRegularizationConfig
from src.discovery.rules import StructureSpec, generate_neighbors, validate_structure
from src.evaluation.metrics import point_metrics
from src.evaluation.rolling import (
    rolling_blocked_metric_summary,
    mean_rolling_metric,
    rolling_error_stability,
    rolling_metrics_by_horizon,
    rolling_origin_forecasts,
)
from src.models.base import FitConfig
from src.utils.io import ensure_dir, write_json, write_yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchConfig:
    beam_width: int = 5
    max_rounds: int = 20
    patience: int = 5
    rolling_horizons: tuple[int, ...] = (1, 2, 4)
    multi_split_blocks: int = 3
    score_param_weight: float = 0.01
    score_compartment_weight: float = 0.02
    score_fractional_weight: float = 0.015
    score_observation_weight: float = 0.005
    score_recurrence_weight: float = 0.01
    score_stability_weight: float = 0.2
    score_multi_split_std_weight: float = 0.5
    raw_l2_weight: float = 5.0e-4
    seasonality_l2_weight: float = 5.0e-3
    rho_l2_weight: float = 2.0e-3
    init_l2_weight: float = 2.0e-3
    fractional_alpha_weight: float = 2.0e-3
    use_age_prior: bool = True
    age_prior_simple_bonus: float = 0.01
    age_prior_recurrence_bonus: float = 0.01
    age_prior_fractional_bonus: float = 0.005


@dataclass
class SearchOutcome:
    best_spec: StructureSpec
    leaderboard: pd.DataFrame
    best_record: dict[str, Any]


def _stable_seed(seed: int, key: str) -> int:
    digest = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) % (2**32 - 1)


def discovery_regularization_config(search_config: SearchConfig) -> DiscoveryRegularizationConfig:
    """Build discovery fit regularization from search config."""
    return DiscoveryRegularizationConfig(
        raw_l2_weight=search_config.raw_l2_weight,
        seasonality_l2_weight=search_config.seasonality_l2_weight,
        rho_l2_weight=search_config.rho_l2_weight,
        init_l2_weight=search_config.init_l2_weight,
        fractional_alpha_weight=search_config.fractional_alpha_weight,
    )


def discovery_complexity_penalty(
    spec: StructureSpec,
    param_count: int,
    num_compartments: int,
    search_config: SearchConfig,
) -> float:
    """Structured validation-time penalty for flexible discovered models."""
    penalty = search_config.score_param_weight * param_count
    penalty += search_config.score_compartment_weight * num_compartments
    if spec.fractional:
        penalty += search_config.score_fractional_weight
    if spec.observation_map == "I+H":
        penalty += search_config.score_observation_weight
    if spec.structure_name == "SEIRS":
        penalty += search_config.score_recurrence_weight
    return float(penalty)


def age_structure_prior_penalty(
    series_name: str,
    spec: StructureSpec,
    search_config: SearchConfig,
) -> float:
    """Age-group-specific score adjustment for discovery candidates."""
    if not search_config.use_age_prior:
        return 0.0

    simple_bonus = search_config.age_prior_simple_bonus
    recurrence_bonus = search_config.age_prior_recurrence_bonus
    fractional_bonus = search_config.age_prior_fractional_bonus

    if series_name in {"Overall", "18-49 yr", "50-64 yr"}:
        penalty = 0.0
        if spec.structure_name == "SIR":
            penalty -= simple_bonus
        elif spec.structure_name == "SEIR":
            penalty -= 0.5 * simple_bonus
        if spec.structure_name == "SEIRS":
            penalty += recurrence_bonus
        if spec.fractional:
            penalty += fractional_bonus
        return float(penalty)

    if series_name == "0-4 yr":
        penalty = 0.0
        if spec.structure_name == "SEIRS":
            penalty -= recurrence_bonus
        elif spec.structure_name == "SEIR":
            penalty -= 0.5 * recurrence_bonus
        if spec.fractional:
            penalty += 0.5 * fractional_bonus
        return float(penalty)

    if series_name == "5-17 yr":
        penalty = 0.0
        if spec.structure_name == "SEIRS":
            penalty -= recurrence_bonus
        if spec.fractional:
            penalty -= 0.5 * fractional_bonus
        return float(penalty)

    if series_name == ">= 65 yr":
        penalty = 0.0
        if spec.structure_name == "SEIRS":
            penalty -= 0.5 * recurrence_bonus
        if spec.fractional:
            penalty -= 0.5 * fractional_bonus
        if spec.structure_name == "SIR":
            penalty += 0.5 * simple_bonus
        return float(penalty)

    return 0.0


def run_structure_search(
    series_name: str,
    y_train: np.ndarray,
    y_val: np.ndarray,
    fit_config: FitConfig,
    search_config: SearchConfig,
    artifact_dir: Path,
    seed: int,
) -> SearchOutcome:
    """Run the constrained propose-fit-verify-refine loop."""
    ensure_dir(artifact_dir)
    start_spec = StructureSpec("SEIR", fractional=False, observation_map="I")
    beam = [start_spec]
    expanded: set[str] = set()
    evaluated_records: dict[str, dict[str, Any]] = {}
    regularization_config = discovery_regularization_config(search_config)

    best_score = float("inf")
    best_record: dict[str, Any] | None = None
    stagnant_rounds = 0
    logger.info(
        "Search start series=%s train_obs=%d val_obs=%d beam_width=%d max_rounds=%d",
        series_name,
        len(y_train),
        len(y_val),
        search_config.beam_width,
        search_config.max_rounds,
    )

    for round_idx in range(1, search_config.max_rounds + 1):
        round_start_best = best_score
        candidate_specs: list[StructureSpec] = []
        for spec in beam:
            if spec.spec_key not in expanded:
                candidate_specs.append(spec)
                candidate_specs.extend(generate_neighbors(spec))

        unique_candidates = {candidate.spec_key: candidate for candidate in candidate_specs}.values()
        any_new = False
        logger.info(
            "Search round=%d beam=%s candidate_count=%d",
            round_idx,
            [spec.spec_key for spec in beam],
            len(list({candidate.spec_key: candidate for candidate in candidate_specs}.values())),
        )

        for spec in unique_candidates:
            if spec.spec_key in evaluated_records:
                continue
            validation = validate_structure(spec)
            if not validation.valid:
                continue

            any_new = True
            candidate_start = time.perf_counter()
            logger.info("Search candidate start round=%d spec=%s", round_idx, spec.spec_key)
            candidate_seed = _stable_seed(seed, spec.spec_key)
            candidate_rng = np.random.default_rng(candidate_seed)
            combined_series = np.concatenate([y_train, y_val])
            model_factory = lambda: DiscoveryCompartmentModel(spec, fit_config, regularization_config)

            model = model_factory()
            fit_result = model.fit(y_train, candidate_rng)
            rollout = model.simulate(fit_result.raw_params, len(combined_series))
            train_pred = rollout.predictions[: len(y_train)]
            val_pred = rollout.predictions[len(y_train) :]
            train_metrics = point_metrics(y_train, train_pred)
            val_metrics = point_metrics(y_val, val_pred)

            rolling_frame = rolling_origin_forecasts(
                model_factory=model_factory,
                y=combined_series,
                horizons=list(search_config.rolling_horizons),
                seed=_stable_seed(seed + 991, spec.spec_key),
                initial_train_size=len(y_train),
            )
            rolling_metrics = rolling_metrics_by_horizon(rolling_frame)
            rolling_mean_mae = mean_rolling_metric(rolling_frame, "mae")
            rolling_mean_rmse = mean_rolling_metric(rolling_frame, "rmse")
            blocked_summary = rolling_blocked_metric_summary(
                rolling_frame,
                metric_name="mae",
                num_blocks=search_config.multi_split_blocks,
            )
            multi_split_mean_mae = blocked_summary["mean"]
            multi_split_std_mae = blocked_summary["std"]
            rolling_error_std = rolling_error_stability(rolling_frame)
            multi_split_penalty = search_config.score_multi_split_std_weight * multi_split_std_mae
            stability_penalty = search_config.score_stability_weight * rolling_error_std
            complexity_penalty = discovery_complexity_penalty(
                spec=spec,
                param_count=fit_result.param_count,
                num_compartments=len(model.compartment_names),
                search_config=search_config,
            )
            age_prior_penalty = age_structure_prior_penalty(series_name, spec, search_config)
            score = multi_split_mean_mae + multi_split_penalty + stability_penalty + complexity_penalty + age_prior_penalty

            record = {
                "round": round_idx,
                "spec_key": spec.spec_key,
                "structure_name": spec.structure_name,
                "fractional": spec.fractional,
                "observation_map": spec.observation_map,
                "num_free_params": fit_result.param_count,
                "num_compartments": len(model.compartment_names),
                "train_objective": fit_result.objective,
                "train_mae": train_metrics["mae"],
                "train_rmse": train_metrics["rmse"],
                "val_mae": val_metrics["mae"],
                "val_rmse": val_metrics["rmse"],
                "val_smape": val_metrics["smape"],
                "rolling_val_mean_mae": rolling_mean_mae,
                "rolling_val_mean_rmse": rolling_mean_rmse,
                "multi_split_blocks": search_config.multi_split_blocks,
                "multi_split_val_mean_mae": multi_split_mean_mae,
                "multi_split_val_std_mae": multi_split_std_mae,
                "multi_split_penalty": multi_split_penalty,
                "rolling_val_error_std": rolling_error_std,
                "rolling_val_metrics": rolling_metrics,
                "stability_penalty": stability_penalty,
                "complexity_penalty": complexity_penalty,
                "age_prior_penalty": age_prior_penalty,
                "score": score,
                "params": fit_result.params,
            }
            evaluated_records[spec.spec_key] = record
            logger.info(
                "Search candidate done round=%d spec=%s score=%.6f multi_split_mae=%.6f multi_split_std=%.6f rolling_mae=%.6f stability=%.6f val_mae=%.6f age_prior=%.4f elapsed=%.1fs",
                round_idx,
                spec.spec_key,
                score,
                multi_split_mean_mae,
                multi_split_std_mae,
                rolling_mean_mae,
                rolling_error_std,
                val_metrics["mae"],
                age_prior_penalty,
                time.perf_counter() - candidate_start,
            )

            if score < best_score:
                best_score = score
                best_record = record

        for spec in beam:
            expanded.add(spec.spec_key)

        if not any_new:
            stagnant_rounds += 1
        elif best_score < round_start_best - 1.0e-12:
            stagnant_rounds = 0
        else:
            stagnant_rounds += 1

        leaderboard = pd.DataFrame(evaluated_records.values()).sort_values("score", ascending=True).reset_index(drop=True)
        if leaderboard.empty:
            raise RuntimeError("Structure discovery did not evaluate any valid candidate.")

        beam = [
            StructureSpec(
                structure_name=row["structure_name"],
                fractional=bool(row["fractional"]),
                observation_map=row["observation_map"],
            )
            for _, row in leaderboard.head(search_config.beam_width).iterrows()
        ]
        logger.info(
            "Search round=%d complete best_score=%.6f next_beam=%s",
            round_idx,
            best_score,
            [spec.spec_key for spec in beam],
        )

        if stagnant_rounds >= search_config.patience:
            logger.info("Search early stop round=%d stagnant_rounds=%d", round_idx, stagnant_rounds)
            break

    if best_record is None:
        raise RuntimeError("Structure discovery failed to find a best candidate.")

    leaderboard = pd.DataFrame(evaluated_records.values()).sort_values("score", ascending=True).reset_index(drop=True)
    best_spec = StructureSpec(
        structure_name=str(best_record["structure_name"]),
        fractional=bool(best_record["fractional"]),
        observation_map=str(best_record["observation_map"]),
    )

    leaderboard.to_csv(artifact_dir / "leaderboard.csv", index=False)
    write_json(best_record, artifact_dir / "best_model_spec.json")
    write_yaml(best_record, artifact_dir / "best_model_spec.yaml")
    logger.info("Search finished best_spec=%s leaderboard=%s", best_spec.spec_key, artifact_dir / "leaderboard.csv")
    return SearchOutcome(best_spec=best_spec, leaderboard=leaderboard, best_record=best_record)
