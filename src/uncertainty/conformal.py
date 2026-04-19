from __future__ import annotations

import numpy as np

from src.evaluation.metrics import scale_interval_map


def conformal_quantile(scores: np.ndarray, nominal_coverage: float) -> float:
    """Return the finite-sample conformal quantile for a target coverage level."""
    finite_scores = np.asarray(scores, dtype=float)
    finite_scores = finite_scores[np.isfinite(finite_scores)]
    if finite_scores.size == 0:
        raise ValueError("Conformal quantile requested with no finite calibration scores.")

    ordered = np.sort(finite_scores)
    rank = int(np.ceil((len(ordered) + 1) * float(nominal_coverage)))
    rank = min(max(rank, 1), len(ordered))
    return float(ordered[rank - 1])


def apply_raw_interval(
    lower_raw: np.ndarray,
    upper_raw: np.ndarray,
    lower_bound: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return raw intervals with lower-bound clipping."""
    lower = np.maximum(np.asarray(lower_raw, dtype=float), lower_bound)
    upper = np.asarray(upper_raw, dtype=float)
    return np.minimum(lower, upper), np.maximum(lower, upper)


def apply_scale_calibrated_interval(
    center: np.ndarray,
    lower_raw: np.ndarray,
    upper_raw: np.ndarray,
    scale: float,
    lower_bound: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Scale interval widths around the center forecast."""
    scaled = scale_interval_map(
        {"level": (np.asarray(lower_raw, dtype=float), np.asarray(upper_raw, dtype=float))},
        center=np.asarray(center, dtype=float),
        scale=float(scale),
    )["level"]
    lower = np.maximum(scaled[0], lower_bound)
    upper = scaled[1]
    return np.minimum(lower, upper), np.maximum(lower, upper)


def apply_absolute_conformal(
    center: np.ndarray,
    q: float,
    lower_bound: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply absolute-residual conformal calibration around the point forecast."""
    center = np.asarray(center, dtype=float)
    lower = np.maximum(center - float(q), lower_bound)
    upper = center + float(q)
    return np.minimum(lower, upper), np.maximum(lower, upper)


def apply_standardized_conformal(
    center: np.ndarray,
    lower_raw: np.ndarray,
    upper_raw: np.ndarray,
    q: float,
    eps: float = 1.0e-8,
    lower_bound: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply conformal scaling to raw half-widths."""
    center = np.asarray(center, dtype=float)
    lower_raw = np.asarray(lower_raw, dtype=float)
    upper_raw = np.asarray(upper_raw, dtype=float)
    half_width = np.maximum((upper_raw - lower_raw) / 2.0, eps)
    lower = np.maximum(center - float(q) * half_width, lower_bound)
    upper = center + float(q) * half_width
    return np.minimum(lower, upper), np.maximum(lower, upper)


def apply_asymmetric_conformal(
    lower_raw: np.ndarray,
    upper_raw: np.ndarray,
    q_lower: float,
    q_upper: float,
    lower_bound: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Expand raw intervals asymmetrically without shrinking them."""
    lower_raw = np.asarray(lower_raw, dtype=float)
    upper_raw = np.asarray(upper_raw, dtype=float)
    lower = np.maximum(lower_raw - max(float(q_lower), 0.0), lower_bound)
    upper = upper_raw + max(float(q_upper), 0.0)
    return np.minimum(lower, upper), np.maximum(lower, upper)


def interval_score(
    y_true: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    nominal_coverage: float,
) -> np.ndarray:
    """Compute the interval score for one nominal coverage level."""
    y_true = np.asarray(y_true, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    alpha = 1.0 - float(nominal_coverage)
    if alpha <= 0.0:
        raise ValueError("Nominal coverage must be less than 1.0.")

    width = upper - lower
    below_penalty = (2.0 / alpha) * np.maximum(lower - y_true, 0.0)
    above_penalty = (2.0 / alpha) * np.maximum(y_true - upper, 0.0)
    return width + below_penalty + above_penalty
