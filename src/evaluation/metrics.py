from __future__ import annotations

from typing import Any

import numpy as np


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(y_true - y_pred))))


def smape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1.0e-8) -> float:
    denom = np.abs(y_true) + np.abs(y_pred) + eps
    return float(np.mean(2.0 * np.abs(y_pred - y_true) / denom))


def point_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "smape": smape(y_true, y_pred),
    }


def interval_coverage(y_true: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    inside = (y_true >= lower) & (y_true <= upper)
    return float(np.mean(inside))


def average_interval_width(lower: np.ndarray, upper: np.ndarray) -> float:
    return float(np.mean(upper - lower))


def summarise_probabilistic_metrics(
    y_true: np.ndarray,
    nll: float | None,
    interval_map: dict[str, tuple[np.ndarray, np.ndarray]] | None,
) -> dict[str, Any]:
    if interval_map is None:
        return {
            "negative_log_likelihood": nll,
            "coverage_80": None,
            "coverage_95": None,
            "average_interval_width_80": None,
            "average_interval_width_95": None,
        }

    lower80, upper80 = interval_map["80"]
    lower95, upper95 = interval_map["95"]
    return {
        "negative_log_likelihood": nll,
        "coverage_80": interval_coverage(y_true, lower80, upper80),
        "coverage_95": interval_coverage(y_true, lower95, upper95),
        "average_interval_width_80": average_interval_width(lower80, upper80),
        "average_interval_width_95": average_interval_width(lower95, upper95),
    }
