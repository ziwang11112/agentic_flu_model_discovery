from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.data.split import ChronologicalSplit
from src.discovery.model import DiscoveryCompartmentModel
from src.discovery.rules import StructureSpec, observation_family
from src.discovery.search import (
    SearchConfig,
    age_structure_prior_penalty,
    discovery_complexity_penalty_components,
    discovery_regularization_config,
)
from src.evaluation.metrics import point_metrics
from src.evaluation.rolling import (
    mean_rolling_metric,
    rolling_blocked_metric_summary,
    rolling_error_stability,
    rolling_metrics_by_horizon,
    rolling_origin_forecasts,
)
from src.models.base import FitConfig
from src.utils.io import ensure_dir, write_json, write_yaml


def _stable_seed(seed: int, key: str) -> int:
    return abs(hash(f"{seed}:{key}")) % (2**32 - 1)


def evaluate_llm_candidate_specs(
    series_name: str,
    specs: list[StructureSpec],
    y: np.ndarray,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    artifact_dir: Path,
    seed: int,
    proposal_metadata: dict[str, dict[str, Any]],
    provider_info: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    ensure_dir(artifact_dir)
    records: list[dict[str, Any]] = []
    regularization_config = discovery_regularization_config(search_config)
    rolling_fit_config = replace(fit_config, rolling_n_restarts=max(1, fit_config.rolling_n_restarts))
    y_train = y[split.train_slice]
    y_val = y[split.val_slice]
    combined_series = y[: split.val_end]

    for spec in specs:
        metadata = proposal_metadata[spec.spec_key]
        model_factory = lambda: DiscoveryCompartmentModel(spec, fit_config, regularization_config)
        rolling_model_factory = lambda: DiscoveryCompartmentModel(spec, rolling_fit_config, regularization_config)
        model = model_factory()
        rng = np.random.default_rng(_stable_seed(seed, spec.spec_key))
        fit_result = model.fit(y_train, rng)
        rollout = model.simulate(fit_result.raw_params, len(combined_series))
        train_pred = rollout.predictions[: len(y_train)]
        val_pred = rollout.predictions[len(y_train) :]
        train_metrics = point_metrics(y_train, train_pred)
        val_metrics = point_metrics(y_val, val_pred)
        rolling_frame = rolling_origin_forecasts(
            model_factory=rolling_model_factory,
            y=combined_series,
            horizons=list(search_config.rolling_horizons),
            seed=_stable_seed(seed + 991, spec.spec_key),
            initial_train_size=len(y_train),
        )
        rolling_metrics = rolling_metrics_by_horizon(rolling_frame)
        rolling_mean_mae = mean_rolling_metric(rolling_frame, "mae")
        rolling_mean_rmse = mean_rolling_metric(rolling_frame, "rmse")
        rolling_val_std_mae = float(np.std([metrics["mae"] for metrics in rolling_metrics.values()])) if rolling_metrics else float("nan")
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
        complexity_components = discovery_complexity_penalty_components(
            spec=spec,
            param_count=fit_result.param_count,
            num_compartments=len(model.compartment_names),
            search_config=search_config,
        )
        complexity_penalty = float(complexity_components["complexity_penalty"])
        age_prior_penalty = age_structure_prior_penalty(series_name, spec, search_config)
        score = multi_split_mean_mae + multi_split_penalty + stability_penalty + complexity_penalty + age_prior_penalty
        records.append(
            {
                "series_name": series_name,
                "round_id": metadata["round_id"],
                "proposal_id": metadata["proposal_id"],
                "role_source": metadata["role_source"],
                "critic_priority": metadata["critic_priority"],
                "critic_risk_flags": metadata["critic_risk_flags"],
                "provider": provider_info["provider"],
                "provider_is_mock": provider_info["provider_is_mock"],
                "scientific_claim_allowed": provider_info["scientific_claim_allowed"],
                "schema_valid": True,
                "hard_valid": True,
                "invalid_reason": "",
                "spec_key": spec.spec_key,
                "structure_name": spec.structure_name,
                "fractional": spec.fractional,
                "observation_map": spec.observation_map,
                "delay_weeks": int(spec.delay_weeks),
                "observation_family": observation_family(spec),
                "num_free_params": fit_result.param_count,
                "num_compartments": len(model.compartment_names),
                "train_mae": train_metrics["mae"],
                "val_mae": val_metrics["mae"],
                "val_rmse": val_metrics["rmse"],
                "val_smape": val_metrics["smape"],
                "rolling_val_mean_mae": rolling_mean_mae,
                "rolling_val_mean_rmse": rolling_mean_rmse,
                "rolling_val_std_mae": rolling_val_std_mae,
                "multi_split_val_mean_mae": multi_split_mean_mae,
                "multi_split_val_std_mae": multi_split_std_mae,
                "multi_split_penalty": multi_split_penalty,
                "rolling_val_error_std": rolling_error_std,
                "rolling_val_metrics": rolling_metrics,
                "stability_penalty": stability_penalty,
                "complexity_penalty": complexity_penalty,
                "complexity_penalty_params": complexity_components["param_penalty"],
                "complexity_penalty_compartments": complexity_components["compartment_penalty"],
                "complexity_penalty_fractional": complexity_components["fractional_penalty"],
                "complexity_penalty_observation": complexity_components["observation_penalty"],
                "complexity_penalty_h_observation": complexity_components["h_observation_penalty"],
                "complexity_penalty_delay": complexity_components["delay_penalty"],
                "complexity_penalty_recurrence": complexity_components["recurrence_penalty"],
                "age_prior_penalty": age_prior_penalty,
                "score": score,
            }
        )

    leaderboard = pd.DataFrame.from_records(records).sort_values("score", ascending=True).reset_index(drop=True)
    leaderboard.to_csv(artifact_dir / "llm_leaderboard.csv", index=False)

    best_row = leaderboard.iloc[0].to_dict()
    best_spec = StructureSpec(
        structure_name=str(best_row["structure_name"]),
        fractional=bool(best_row["fractional"]),
        observation_map=str(best_row["observation_map"]),
        delay_weeks=int(best_row.get("delay_weeks", 0)),
    )
    selection_artifact = {
        "series_name": series_name,
        "best_spec": {
            "structure_name": best_spec.structure_name,
            "fractional": best_spec.fractional,
            "observation_map": best_spec.observation_map,
            "delay_weeks": best_spec.delay_weeks,
        },
        "selection_score": float(best_row["score"]),
        "selection_validation_mae": float(best_row["val_mae"]),
        "selection_rolling_mean_mae": float(best_row["rolling_val_mean_mae"]),
        **provider_info,
    }
    write_json(selection_artifact, artifact_dir / "best_llm_model_spec.json")
    write_yaml(selection_artifact, artifact_dir / "best_llm_model_spec.yaml")
    return leaderboard, selection_artifact


def evaluate_selected_spec_on_test(
    spec: StructureSpec,
    y: np.ndarray,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    seed: int,
) -> dict[str, Any]:
    regularization_config = discovery_regularization_config(search_config)
    model = DiscoveryCompartmentModel(spec, fit_config, regularization_config)
    rng = np.random.default_rng(_stable_seed(seed + 4099, spec.spec_key))
    fit_result = model.fit(y[: split.val_end], rng)
    rollout = model.simulate(fit_result.raw_params, len(y))
    test_metrics = point_metrics(y[split.test_slice], rollout.predictions[split.test_slice])
    return {
        "test_mae": float(test_metrics["mae"]),
        "test_rmse": float(test_metrics["rmse"]),
        "test_smape": float(test_metrics["smape"]),
    }
