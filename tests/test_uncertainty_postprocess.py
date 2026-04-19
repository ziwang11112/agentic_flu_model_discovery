from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.uncertainty.calibration_report import select_validation_winners
from src.uncertainty.conformal import (
    apply_absolute_conformal,
    apply_asymmetric_conformal,
    apply_standardized_conformal,
    conformal_quantile,
    interval_score,
)
from src.uncertainty.residual_bank import build_residual_bank


def _config(interval_levels: list[int] | None = None, min_points: int = 3) -> dict:
    return {
        "uncertainty": {
            "conformal": {
                "interval_levels": [80] if interval_levels is None else interval_levels,
                "min_calibration_points": min_points,
                "prefer_horizon_specific": True,
                "fallback_pooling": "age_family",
                "winner_undercoverage_floor": -0.05,
                "winner_interval_score_weight": 0.25,
                "age_families": {
                    "children": ["0-4 yr", "5-17 yr"],
                    "adults": ["18-49 yr", "50-64 yr"],
                    "older_adults": [">= 65 yr"],
                    "overall": ["Overall"],
                },
            }
        }
    }


def _validation_frame(series_name: str, values: list[float]) -> pd.DataFrame:
    center = np.array(values, dtype=float)
    return pd.DataFrame(
        {
            "t": np.arange(len(values)) + 31,
            "actual": center,
            "point_prediction": center,
            "raw_lower_80": center - 0.1,
            "raw_upper_80": center + 0.1,
        }
    )


def _rolling_frame(horizon_values: list[tuple[int, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "origin_end": [30 + idx for idx, _ in enumerate(horizon_values)],
            "target_t": [31 + idx for idx, _ in enumerate(horizon_values)],
            "horizon": [item[0] for item in horizon_values],
            "actual": [item[1] for item in horizon_values],
            "prediction": [item[2] for item in horizon_values],
            "error": [item[2] - item[1] for item in horizon_values],
            "abs_error": [abs(item[2] - item[1]) for item in horizon_values],
        }
    )


def _bundle(series_name: str, validation_values: list[float], horizon_values: list[tuple[int, float, float]]) -> dict:
    return {
        "series_name": series_name,
        "model_name": "probabilistic_seir",
        "validation_frame": _validation_frame(series_name, validation_values),
        "rolling_validation_frame": _rolling_frame(horizon_values),
    }


def test_conformal_quantile_uses_finite_sample_index() -> None:
    scores = np.arange(1, 11, dtype=float)
    assert conformal_quantile(scores, nominal_coverage=0.8) == 9.0


def test_no_test_leakage_in_winner_selection() -> None:
    comparison = pd.DataFrame(
        {
            "series_name": ["Overall"] * 4,
            "age_family": ["overall"] * 4,
            "model_name": ["probabilistic_seir"] * 4,
            "split": ["validation", "validation", "test", "test"],
            "horizon": ["static"] * 4,
            "calibration_kind": ["method_a", "method_b", "method_a", "method_b"],
            "interval_level": [80] * 4,
            "empirical_coverage": [0.8, 0.95, 0.7, 0.85],
            "coverage_gap": [0.0, 0.15, -0.1, 0.05],
            "abs_coverage_gap": [0.0, 0.15, 0.1, 0.05],
            "average_interval_width": [0.4, 0.8, 0.4, 0.3],
            "interval_score_mean": [0.4, 0.9, 1.2, 0.2],
            "residual_source_used": ["none"] * 4,
            "calibration_points": [10] * 4,
        }
    )

    winners = select_validation_winners(comparison, _config())

    assert winners["selected_calibration_kind"].tolist() == ["method_a"]


def test_winner_selection_prioritizes_closest_nominal_coverage() -> None:
    comparison = pd.DataFrame(
        {
            "series_name": ["Overall", "Overall"],
            "age_family": ["overall", "overall"],
            "model_name": ["probabilistic_seir", "probabilistic_seir"],
            "split": ["validation", "validation"],
            "horizon": ["static", "static"],
            "calibration_kind": ["method_a", "method_b"],
            "interval_level": [80, 80],
            "empirical_coverage": [0.8, 0.95],
            "coverage_gap": [0.0, 0.15],
            "abs_coverage_gap": [0.0, 0.15],
            "average_interval_width": [0.6, 0.2],
            "interval_score_mean": [0.9, 0.2],
            "residual_source_used": ["none", "none"],
            "calibration_points": [10, 10],
        }
    )

    winners = select_validation_winners(comparison, _config())

    assert winners["selected_calibration_kind"].tolist() == ["method_a"]
    assert winners["selection_rule_used"].tolist() == ["coverage_floor_then_balanced_score"]


def test_winner_selection_uses_balanced_score_within_coverage_floor() -> None:
    comparison = pd.DataFrame(
        {
            "series_name": ["Overall", "Overall"],
            "age_family": ["overall", "overall"],
            "model_name": ["probabilistic_seir", "probabilistic_seir"],
            "split": ["validation", "validation"],
            "horizon": ["static", "static"],
            "calibration_kind": ["method_a", "method_b"],
            "interval_level": [80, 80],
            "empirical_coverage": [0.82, 0.80],
            "coverage_gap": [0.02, 0.0],
            "abs_coverage_gap": [0.02, 0.0],
            "average_interval_width": [0.9, 0.4],
            "interval_score_mean": [1.0, 0.2],
            "residual_source_used": ["none", "none"],
            "calibration_points": [10, 10],
        }
    )

    winners = select_validation_winners(comparison, _config())

    assert winners["selected_calibration_kind"].tolist() == ["method_b"]
    assert winners["selection_rule_used"].tolist() == ["coverage_floor_then_balanced_score"]


def test_winner_selection_falls_back_when_all_methods_break_coverage_floor() -> None:
    comparison = pd.DataFrame(
        {
            "series_name": ["Overall", "Overall"],
            "age_family": ["overall", "overall"],
            "model_name": ["probabilistic_seir", "probabilistic_seir"],
            "split": ["validation", "validation"],
            "horizon": ["static", "static"],
            "calibration_kind": ["method_a", "method_b"],
            "interval_level": [80, 80],
            "empirical_coverage": [0.65, 0.70],
            "coverage_gap": [-0.15, -0.10],
            "abs_coverage_gap": [0.15, 0.10],
            "average_interval_width": [0.5, 0.7],
            "interval_score_mean": [0.1, 0.3],
            "residual_source_used": ["none", "none"],
            "calibration_points": [10, 10],
        }
    )

    winners = select_validation_winners(comparison, _config())

    assert winners["selected_calibration_kind"].tolist() == ["method_b"]
    assert winners["selection_rule_used"].tolist() == ["balanced_score_no_floor_fallback"]


def test_benchmark_level_pooling_uses_age_family_when_series_count_is_low() -> None:
    bundles = [
        _bundle("0-4 yr", [0.1, 0.2], []),
        _bundle("5-17 yr", [0.1, 0.2, 0.3, 0.4, 0.5], []),
    ]
    bank = build_residual_bank(bundles, _config(min_points=4))
    scores, metadata = bank.get_calibration_scores("0-4 yr", 80, "static", "conformal_standardized", _config(min_points=4))

    assert len(scores) >= 4
    assert metadata["pooled_age_family_used"] is True


def test_horizon_specific_residuals_are_used_first() -> None:
    bundles = [
        _bundle(
            "Overall",
            [0.1, 0.2, 0.3],
            [(1, 0.2, 0.1), (1, 0.3, 0.2), (1, 0.4, 0.3), (4, 0.5, 0.1)],
        )
    ]
    bank = build_residual_bank(bundles, _config(min_points=3))
    scores, metadata = bank.get_calibration_scores("Overall", 80, 1, "conformal_absolute", _config(min_points=3))

    assert len(scores) == 3
    assert metadata["pooled_horizons_used"] is False
    assert metadata["residual_source_used"] == "same_series_same_horizon"


def test_horizon_fallback_pools_across_horizons_when_needed() -> None:
    bundles = [
        _bundle(
            "Overall",
            [0.1, 0.2, 0.3],
            [(1, 0.2, 0.1), (4, 0.3, 0.2), (4, 0.4, 0.3)],
        )
    ]
    bank = build_residual_bank(bundles, _config(min_points=3))
    scores, metadata = bank.get_calibration_scores("Overall", 80, 1, "conformal_absolute", _config(min_points=3))

    assert len(scores) == 3
    assert metadata["pooled_horizons_used"] is True


def test_absolute_conformal_interval_shape() -> None:
    lower, upper = apply_absolute_conformal(np.array([0.1, 0.0]), q=0.2, lower_bound=0.0)
    assert np.all(lower <= upper)
    assert np.all(lower >= 0.0)


def test_standardized_conformal_gives_wider_intervals_when_raw_intervals_are_wider() -> None:
    center = np.array([0.5, 0.5], dtype=float)
    lower, upper = apply_standardized_conformal(
        center=center,
        lower_raw=np.array([0.45, 0.10]),
        upper_raw=np.array([0.55, 0.90]),
        q=1.2,
        eps=1.0e-8,
        lower_bound=0.0,
    )
    widths = upper - lower
    assert widths[1] > widths[0]


def test_asymmetric_conformal_never_shrinks_raw_intervals_and_clips_lower_bound() -> None:
    lower_raw = np.array([0.05, 0.20])
    upper_raw = np.array([0.50, 0.60])
    lower, upper = apply_asymmetric_conformal(lower_raw, upper_raw, q_lower=0.2, q_upper=0.1, lower_bound=0.0)

    assert np.all(lower >= 0.0)
    assert np.all(lower <= lower_raw)
    assert np.all(upper >= upper_raw)


def test_interval_score_penalty_increases_outside_interval() -> None:
    inside = interval_score(np.array([0.5]), np.array([0.4]), np.array([0.6]), nominal_coverage=0.8)[0]
    outside = interval_score(np.array([0.9]), np.array([0.4]), np.array([0.6]), nominal_coverage=0.8)[0]

    assert outside > inside


def test_static_horizon_compatibility() -> None:
    bundles = [_bundle("Overall", [0.1, 0.2, 0.3], [])]
    bank = build_residual_bank(bundles, _config(min_points=2))
    scores, metadata = bank.get_calibration_scores("Overall", 80, "static", "conformal_standardized", _config(min_points=2))

    assert len(scores) == 3
    assert metadata["residual_source_used"] == "same_series_static"
