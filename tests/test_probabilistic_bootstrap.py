from __future__ import annotations

import numpy as np

from src.evaluation.metrics import learn_conformal_interval_scales, learn_interval_scales, scale_interval_map
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


def test_interval_calibration_learns_level_specific_shrinking_scales_for_overwide_intervals() -> None:
    y_true = np.array([0.0, 0.0, 0.0, 0.0], dtype=float)
    center = np.zeros_like(y_true)
    raw_interval_map = {
        "50": (np.full(4, -1.0), np.full(4, 1.0)),
        "80": (np.full(4, -2.0), np.full(4, 2.0)),
        "95": (np.full(4, -3.0), np.full(4, 3.0)),
    }

    calibration = learn_interval_scales(y_true, center, raw_interval_map, scale_min=0.1, scale_max=1.0, grid_size=10)
    calibrated = scale_interval_map(raw_interval_map, center, calibration["scales"])

    assert set(calibration["scales"]) == {"50", "80", "95"}
    assert all(scale < 1.0 for scale in calibration["scales"].values())
    assert np.all(np.abs(calibrated["80"][0]) < np.abs(raw_interval_map["80"][0]))


def test_conformal_interval_calibration_shrinks_overwide_intervals() -> None:
    y_true = np.array([0.0, 0.0, 0.0, 0.0], dtype=float)
    center = np.zeros_like(y_true)
    raw_interval_map = {
        "80": (np.full(4, -2.0), np.full(4, 2.0)),
        "95": (np.full(4, -3.0), np.full(4, 3.0)),
    }

    calibration = learn_conformal_interval_scales(y_true, center, raw_interval_map)
    calibrated = scale_interval_map(raw_interval_map, center, calibration["scales"])

    assert all(scale < 1.0 for scale in calibration["scales"].values())
    assert np.all(np.abs(calibrated["80"][0]) < np.abs(raw_interval_map["80"][0]))


def test_conformal_interval_calibration_expands_underwide_intervals() -> None:
    y_true = np.array([2.0, 2.0, 2.0, 2.0], dtype=float)
    center = np.zeros_like(y_true)
    raw_interval_map = {
        "80": (np.full(4, -1.0), np.full(4, 1.0)),
        "95": (np.full(4, -1.5), np.full(4, 1.5)),
    }

    calibration = learn_conformal_interval_scales(y_true, center, raw_interval_map)
    calibrated = scale_interval_map(raw_interval_map, center, calibration["scales"])

    assert all(scale > 1.0 for scale in calibration["scales"].values())
    assert np.all(np.abs(calibrated["80"][1]) > np.abs(raw_interval_map["80"][1]))
