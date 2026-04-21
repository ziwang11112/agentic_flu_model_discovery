from __future__ import annotations

import numpy as np

import pandas as pd

from src.discovery.model import DiscoveryCompartmentModel, DiscoveryRegularizationConfig
from src.discovery.rules import StructureSpec, generate_neighbors, validate_structure
from src.discovery.search import SearchConfig, age_structure_prior_penalty, discovery_complexity_penalty, run_structure_search
from src.evaluation.rolling import rolling_blocked_metric_summary, rolling_error_stability
from src.models.base import FitConfig, FitResult, SimulationResult


def test_validate_structure_accepts_valid_spec() -> None:
    result = validate_structure(StructureSpec("SEIHR", fractional=True, observation_map="I+H"))
    assert result.valid


def test_validate_structure_rejects_h_observation_without_h_compartment() -> None:
    result = validate_structure(StructureSpec("SIR", fractional=False, observation_map="H"))
    assert not result.valid
    assert result.reason == "observation_map_requires_h"


def test_validate_structure_rejects_invalid_observation_map() -> None:
    result = validate_structure(StructureSpec("SIR", fractional=False, observation_map="I+H"))
    assert not result.valid
    assert result.reason == "observation_map_requires_h"


def test_validate_structure_rejects_invalid_delay() -> None:
    result = validate_structure(StructureSpec("SEIR", fractional=False, observation_map="delayed_I", delay_weeks=4))
    assert not result.valid
    assert result.reason == "invalid_delay"


def test_spec_key_includes_delay_for_delayed_i() -> None:
    spec = StructureSpec("SEIR", fractional=False, observation_map="delayed_I", delay_weeks=2)

    assert spec.spec_key == "SEIR|fractional=0|obs=delayed_I|delay=2"


def test_generate_neighbors_stays_in_allowed_grammar() -> None:
    neighbors = generate_neighbors(StructureSpec("SEIR", fractional=False, observation_map="I"))
    neighbor_keys = {neighbor.spec_key for neighbor in neighbors}

    assert "SIR|fractional=0|obs=I" in neighbor_keys
    assert "SEIHR|fractional=0|obs=I" in neighbor_keys
    assert "SEIR|fractional=0|obs=delayed_I|delay=1" in neighbor_keys
    assert "SEIR|fractional=1|obs=I" in neighbor_keys


def test_discovery_delayed_i_observation_uses_max_t_minus_delay() -> None:
    model = DiscoveryCompartmentModel(
        StructureSpec("SEIR", fractional=False, observation_map="delayed_I", delay_weeks=2),
        FitConfig(),
        DiscoveryRegularizationConfig(),
    )
    raw_params = np.array(
        [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            np.log(1.0),
            -2.0,
            -3.0,
        ],
        dtype=float,
    )

    simulation = model.simulate(raw_params, n_steps=5)

    assert np.isclose(simulation.predictions[0], simulation.states[0, 2])
    assert np.isclose(simulation.predictions[1], simulation.states[0, 2])
    assert np.isclose(simulation.predictions[4], simulation.states[2, 2])


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


def test_age_structure_prior_penalty_disabled_when_config_off() -> None:
    config = SearchConfig(use_age_prior=False)

    penalty = age_structure_prior_penalty("0-4 yr", StructureSpec("SEIRS", fractional=False, observation_map="I"), config)

    assert penalty == 0.0


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


def test_search_leaderboard_contains_delay_weeks(monkeypatch, tmp_path) -> None:
    def fake_fit(self, y_train, rng, warm_start=None, n_restarts=None):
        del y_train, rng, warm_start, n_restarts
        raw_params = np.zeros(self.raw_parameter_dim, dtype=float)
        simulation = self.simulate(raw_params, 8)
        return FitResult(
            model_name=self.model_name,
            raw_params=raw_params,
            params=self.transform_parameters(raw_params),
            simulation=simulation,
            objective=0.0,
            success=True,
            message="ok",
            param_count=self.raw_parameter_dim,
        )

    def fake_simulate(self, raw_params, n_steps):
        del raw_params
        states = np.full((n_steps, len(self.compartment_names)), 0.05, dtype=float)
        if "I" in self.compartment_names:
            i_index = self.compartment_names.index("I")
            states[:, i_index] = np.linspace(0.1, 0.2, n_steps)
        predictions = np.linspace(0.1, 0.2, n_steps)
        return SimulationResult(
            compartments=self.compartment_names,
            states=states,
            predictions=predictions,
            penalties={"negative": 0.0, "mass": 0.0},
        )

    def fake_rolling_origin_forecasts(*args, **kwargs):
        del args, kwargs
        return pd.DataFrame(
            {
                "horizon": [1, 1, 2, 2],
                "target_t": [5, 6, 5, 6],
                "actual": [0.1, 0.1, 0.1, 0.1],
                "prediction": [0.1, 0.1, 0.1, 0.1],
                "mae": [0.0, 0.0, 0.0, 0.0],
                "rmse": [0.0, 0.0, 0.0, 0.0],
                "smape": [0.0, 0.0, 0.0, 0.0],
                "abs_error": [0.0, 0.0, 0.0, 0.0],
            }
        )

    monkeypatch.setattr(DiscoveryCompartmentModel, "fit", fake_fit)
    monkeypatch.setattr(DiscoveryCompartmentModel, "simulate", fake_simulate)
    monkeypatch.setattr("src.discovery.search.rolling_origin_forecasts", fake_rolling_origin_forecasts)
    monkeypatch.setattr("src.discovery.search.rolling_metrics_by_horizon", lambda frame: {1: {"mae": 0.0}})
    monkeypatch.setattr("src.discovery.search.mean_rolling_metric", lambda frame, metric: 0.0)
    monkeypatch.setattr(
        "src.discovery.search.rolling_blocked_metric_summary",
        lambda frame, metric_name, num_blocks: {"num_blocks": 1, "mean": 0.0, "std": 0.0, "details": pd.DataFrame()},
    )
    monkeypatch.setattr("src.discovery.search.rolling_error_stability", lambda frame: 0.0)

    outcome = run_structure_search(
        series_name="Overall",
        y_train=np.linspace(0.1, 0.2, 8),
        y_val=np.linspace(0.1, 0.15, 4),
        fit_config=FitConfig(n_restarts=1, maxiter=5),
        search_config=SearchConfig(beam_width=8, max_rounds=1, patience=1),
        artifact_dir=tmp_path,
        seed=42,
    )

    assert "delay_weeks" in outcome.leaderboard.columns
    delayed_rows = outcome.leaderboard.loc[outcome.leaderboard["observation_map"] == "delayed_I"]
    assert not delayed_rows.empty
    assert set(delayed_rows["delay_weeks"].astype(int).tolist()).issubset({1, 2, 3})
