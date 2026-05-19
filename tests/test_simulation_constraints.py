from __future__ import annotations

import numpy as np

from src.models.base import FitConfig
from src.models.seir_deterministic import DeterministicSEIRModel
from src.models.simulators import mass_conservation_penalty


def _inverse_softplus(value: float) -> float:
    return float(np.log(np.expm1(value)))


def test_mass_conservation_penalty_identifies_drift() -> None:
    conserved = np.array([[0.7, 0.2, 0.1], [0.6, 0.2, 0.2]], dtype=float)
    drifting = np.array([[0.7, 0.2, 0.1], [0.6, 0.2, 0.3]], dtype=float)

    assert np.isclose(mass_conservation_penalty(conserved), 0.0)
    assert mass_conservation_penalty(drifting) > 0.0


def test_deterministic_seir_forward_step_matches_update_equations() -> None:
    model = DeterministicSEIRModel(FitConfig())
    raw_params = np.array(
        [
            _inverse_softplus(0.2),
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            np.log(0.1 / 0.8),
            np.log(0.1 / 0.8),
        ],
        dtype=float,
    )

    simulation = model.simulate(raw_params, n_steps=2)
    initial = simulation.states[0]
    next_state = simulation.states[1]

    beta = 0.2
    sigma = 0.5
    gamma = 0.5
    s0, e0, i0, r0 = initial
    infection = beta * s0 * i0
    expected = np.array(
        [
            s0 - infection,
            e0 + infection - sigma * e0,
            i0 + sigma * e0 - gamma * i0,
            r0 + gamma * i0,
        ],
        dtype=float,
    )

    assert np.allclose(next_state, expected)


def test_fit_with_zero_restarts_still_samples_when_no_warm_start() -> None:
    model = DeterministicSEIRModel(FitConfig(n_restarts=0, maxiter=2))
    result = model.fit(np.array([0.1, 0.2, 0.3], dtype=float), np.random.default_rng(123))

    assert result.raw_params.shape == (model.raw_parameter_dim,)
