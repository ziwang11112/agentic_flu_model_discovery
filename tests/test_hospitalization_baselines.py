from __future__ import annotations

import numpy as np

from src.data.split import make_chronological_split
from src.evaluation.pipeline import select_delayed_observation_delay
from src.models.base import FitConfig, FitResult, SimulationResult
from src.models.seihr_hospitalized import HospitalizedSEIHRModel
from src.models.seir_delayed_observation import DelayedObservationSEIRModel


def _inverse_softplus(value: float) -> float:
    return float(np.log(np.expm1(value)))


def _logit(probability: float) -> float:
    probability = min(max(probability, 1.0e-6), 1.0 - 1.0e-6)
    return float(np.log(probability / (1.0 - probability)))


def test_hospitalized_seihr_prediction_tracks_h_compartment() -> None:
    model = HospitalizedSEIHRModel(FitConfig())
    raw_params = np.array(
        [
            _inverse_softplus(0.2),
            0.0,
            0.0,
            _logit(0.5),
            _logit(0.25),
            _logit(0.5),
            np.log(2.0),
            np.log(0.1 / 0.7),
            np.log(0.1 / 0.7),
            np.log(0.1 / 0.7),
        ],
        dtype=float,
    )

    simulation = model.simulate(raw_params, n_steps=3)

    assert np.allclose(simulation.predictions, 2.0 * simulation.states[:, 3])


def test_delayed_observation_seir_uses_fixed_delay() -> None:
    model = DelayedObservationSEIRModel(FitConfig(), fixed_delay=2)
    raw_params = np.array(
        [
            _inverse_softplus(0.2),
            0.0,
            0.0,
            _logit(0.5),
            _logit(0.5),
            np.log(1.0),
            np.log(0.1 / 0.8),
            np.log(0.1 / 0.8),
        ],
        dtype=float,
    )

    simulation = model.simulate(raw_params, n_steps=5)

    assert np.isclose(simulation.predictions[0], simulation.states[0, 2])
    assert np.isclose(simulation.predictions[1], simulation.states[0, 2])
    assert np.isclose(simulation.predictions[2], simulation.states[0, 2])
    assert np.isclose(simulation.predictions[4], simulation.states[2, 2])


def test_select_delayed_observation_delay_uses_validation_mae(monkeypatch) -> None:
    y = np.linspace(0.1, 1.2, 12, dtype=float)
    split = make_chronological_split(len(y))

    def fake_fit(self: DelayedObservationSEIRModel, y_train: np.ndarray, rng: np.random.Generator, warm_start=None, n_restarts=None) -> FitResult:
        del y_train, rng, warm_start, n_restarts
        raw_params = np.zeros(self.raw_parameter_dim, dtype=float)
        simulation = self.simulate(raw_params, split.train_end)
        return FitResult(
            model_name=self.model_name,
            raw_params=raw_params,
            params=self.transform_parameters(raw_params),
            simulation=simulation,
            objective=float(self.fixed_delay),
            success=True,
            message="ok",
            param_count=self.raw_parameter_dim,
        )

    monkeypatch.setattr(DelayedObservationSEIRModel, "fit", fake_fit)

    def fake_simulation(self: DelayedObservationSEIRModel, raw_params: np.ndarray, n_steps: int) -> SimulationResult:
        del raw_params
        predictions = np.zeros(n_steps, dtype=float)
        val_start = split.train_end
        val_stop = min(split.val_end, n_steps)
        if val_stop > val_start:
            if self.fixed_delay == 2:
                predictions[val_start:val_stop] = y[val_start:val_stop]
            else:
                predictions[val_start:val_stop] = y[val_start:val_stop] + 0.5 + 0.1 * self.fixed_delay
        states = np.zeros((n_steps, 4), dtype=float)
        return SimulationResult(
            compartments=self.compartment_names,
            states=states,
            predictions=predictions,
            penalties={"negative": 0.0, "mass": 0.0},
        )

    monkeypatch.setattr(DelayedObservationSEIRModel, "simulate", fake_simulation)

    selected_delay, table = select_delayed_observation_delay(y, split, FitConfig(n_restarts=1, maxiter=5), seed=42)

    assert selected_delay == 2
    assert int(table.iloc[0]["delay"]) == 2
