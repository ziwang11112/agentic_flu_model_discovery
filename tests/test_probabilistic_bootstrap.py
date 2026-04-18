from __future__ import annotations

import numpy as np

from src.models.base import FitConfig, FitResult
from src.models.seir_probabilistic import ProbabilisticSEIRModel


def test_probabilistic_bootstrap_predictive_summary_shapes(monkeypatch) -> None:
    model = ProbabilisticSEIRModel(
        FitConfig(
            n_restarts=1,
            maxiter=5,
            uncertainty_method="bootstrap",
            bootstrap_draws=3,
            bootstrap_n_restarts=0,
        )
    )
    raw_params = np.zeros(model.raw_parameter_dim, dtype=float)
    y_train = np.array([0.1, 0.2, 0.15, 0.12], dtype=float)
    fit_result = FitResult(
        model_name=model.model_name,
        raw_params=raw_params,
        params=model.transform_parameters(raw_params),
        simulation=model.simulate(raw_params, len(y_train)),
        objective=1.0,
        success=True,
        message="ok",
        param_count=model.raw_parameter_dim,
    )

    def fake_fit(
        y_train_inner: np.ndarray,
        rng: np.random.Generator,
        warm_start: np.ndarray | None = None,
        n_restarts: int | None = None,
    ) -> FitResult:
        del y_train_inner, rng, warm_start, n_restarts
        return FitResult(
            model_name=model.model_name,
            raw_params=raw_params,
            params=model.transform_parameters(raw_params),
            simulation=model.simulate(raw_params, len(y_train)),
            objective=1.0,
            success=True,
            message="ok",
            param_count=model.raw_parameter_dim,
        )

    monkeypatch.setattr(model, "fit", fake_fit)
    summary = model.predictive_summary(y_train, fit_result, 6, np.random.default_rng(0), n_draws=3, method="bootstrap")

    assert summary["method"] == "bootstrap"
    assert summary["draw_count"] == 3
    assert summary["draws"].shape == (3, 6)
    assert summary["intervals"]["80"][0].shape == (6,)
