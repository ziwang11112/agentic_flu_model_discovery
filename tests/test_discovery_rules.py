from __future__ import annotations

import numpy as np

import pandas as pd

from src.discovery.model import DiscoveryCompartmentModel, DiscoveryRegularizationConfig
from src.discovery.rules import StructureSpec, generate_neighbors, validate_structure
from src.discovery.search import SearchConfig, age_structure_prior_penalty, discovery_complexity_penalty
from src.evaluation.rolling import rolling_blocked_metric_summary, rolling_error_stability
from src.models.base import FitConfig


def test_validate_structure_accepts_valid_spec() -> None:
    result = validate_structure(StructureSpec("SEIHR", fractional=True, observation_map="I+H"))
    assert result.valid


def test_validate_structure_rejects_invalid_observation_map() -> None:
    result = validate_structure(StructureSpec("SIR", fractional=False, observation_map="I+H"))
    assert not result.valid
    assert result.reason == "observation_map_requires_h"


def test_generate_neighbors_stays_in_allowed_grammar() -> None:
    neighbors = generate_neighbors(StructureSpec("SEIR", fractional=False, observation_map="I"))
    neighbor_keys = {neighbor.spec_key for neighbor in neighbors}

    assert "SIR|fractional=0|obs=I" in neighbor_keys
    assert "SEIHR|fractional=0|obs=I" in neighbor_keys
    assert "SEIR|fractional=1|obs=I" in neighbor_keys


def test_discovery_regularization_penalizes_extreme_parameters() -> None:
    model = DiscoveryCompartmentModel(
        StructureSpec("SEIR", fractional=True, observation_map="I"),
        FitConfig(),
        DiscoveryRegularizationConfig(),
    )
    moderate = np.zeros(model.raw_parameter_dim, dtype=float)
    extreme = np.full(model.raw_parameter_dim, 6.0, dtype=float)

    assert model.discovery_regularization_penalty(extreme) > model.discovery_regularization_penalty(moderate)


def test_discovery_complexity_penalty_prefers_simpler_structure() -> None:
    config = SearchConfig()
    simple = discovery_complexity_penalty(StructureSpec("SIR", fractional=False, observation_map="I"), 6, 3, config)
    complex_value = discovery_complexity_penalty(
        StructureSpec("SEIRS", fractional=True, observation_map="I"),
        10,
        4,
        config,
    )

    assert complex_value > simple


def test_age_structure_prior_penalty_matches_series_pattern() -> None:
    config = SearchConfig()

    overall_simple = age_structure_prior_penalty("Overall", StructureSpec("SIR", fractional=False, observation_map="I"), config)
    overall_recurrent = age_structure_prior_penalty("Overall", StructureSpec("SEIRS", fractional=False, observation_map="I"), config)
    pediatric_recurrent = age_structure_prior_penalty("0-4 yr", StructureSpec("SEIRS", fractional=False, observation_map="I"), config)
    pediatric_fractional = age_structure_prior_penalty("5-17 yr", StructureSpec("SEIRS", fractional=True, observation_map="I"), config)

    assert overall_simple < 0.0
    assert overall_recurrent > 0.0
    assert pediatric_recurrent < 0.0
    assert pediatric_fractional < pediatric_recurrent


def test_rolling_error_stability_penalizes_variable_candidates() -> None:
    stable = pd.DataFrame(
        {
            "horizon": [1, 1, 2, 2],
            "actual": [1.0, 1.0, 1.0, 1.0],
            "prediction": [0.9, 1.1, 0.95, 1.05],
            "abs_error": [0.1, 0.1, 0.05, 0.05],
        }
    )
    unstable = pd.DataFrame(
        {
            "horizon": [1, 1, 2, 2],
            "actual": [1.0, 1.0, 1.0, 1.0],
            "prediction": [1.0, 0.2, 1.0, 0.1],
            "abs_error": [0.0, 0.8, 0.0, 0.9],
        }
    )

    assert rolling_error_stability(unstable) > rolling_error_stability(stable)


def test_rolling_blocked_metric_summary_returns_mean_and_std() -> None:
    frame = pd.DataFrame(
        {
            "horizon": [1, 1, 1, 1, 2, 2, 2, 2],
            "target_t": [10, 11, 12, 13, 10, 11, 12, 13],
            "actual": [1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0],
            "prediction": [0.9, 1.1, 0.8, 1.2, 2.1, 1.9, 2.2, 1.8],
            "abs_error": [0.1, 0.1, 0.2, 0.2, 0.1, 0.1, 0.2, 0.2],
        }
    )

    summary = rolling_blocked_metric_summary(frame, metric_name="mae", num_blocks=2)

    assert summary["num_blocks"] == 4
    assert summary["mean"] >= 0.0
    assert summary["std"] >= 0.0
    assert list(summary["details"].columns) == ["horizon", "block", "count", "mae", "rmse", "smape"]
