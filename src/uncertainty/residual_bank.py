from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_AGE_FAMILIES = {
    "children": ["0-4 yr", "5-17 yr"],
    "adults": ["18-49 yr", "50-64 yr"],
    "older_adults": [">= 65 yr"],
    "overall": ["Overall"],
}


@dataclass
class ResidualRecord:
    series_name: str
    age_family: str
    model_name: str
    split: str
    horizon: str
    origin_index: int | None
    target_time_index: int
    y_true: float
    yhat: float
    lower_raw: float | None
    upper_raw: float | None
    interval_level: int
    nominal_coverage: float
    residual_abs: float
    raw_half_width: float | None
    standardized_abs_residual: float | None
    lower_miss_score: float | None
    upper_miss_score: float | None
    source_type: str


def _invert_age_families(age_families: dict[str, list[str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for family_name, series_names in age_families.items():
        for series_name in series_names:
            mapping[series_name] = family_name
    return mapping


def _conformal_config(config: dict[str, Any]) -> dict[str, Any]:
    uncertainty = config.get("uncertainty", {})
    conformal = uncertainty.get("conformal", {})
    resolved = {
        "min_calibration_points": int(conformal.get("min_calibration_points", 20)),
        "prefer_horizon_specific": bool(conformal.get("prefer_horizon_specific", True)),
        "horizon_fallback": str(conformal.get("horizon_fallback", "pooled_across_horizons")),
        "fallback_pooling": str(conformal.get("fallback_pooling", "age_family")),
        "interval_levels": [int(level) for level in conformal.get("interval_levels", [50, 80, 95])],
        "age_families": conformal.get("age_families", DEFAULT_AGE_FAMILIES),
    }
    return resolved


class ResidualBank:
    """Benchmark-level residual bank with hierarchical fallback selection."""

    def __init__(self, records: pd.DataFrame, config: dict[str, Any]) -> None:
        self.records = records.copy()
        self.config = _conformal_config(config)
        self.age_family_lookup = _invert_age_families(self.config["age_families"])

    def get_age_family(self, series_name: str) -> str:
        return self.age_family_lookup.get(series_name, "overall")

    def _select_rows_with_fallback(
        self,
        series_name: str,
        interval_level: int,
        horizon: str | int,
        required_column: str,
        prefer_rolling: bool,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        frame = self.records.loc[
            (self.records["split"] == "validation")
            & (self.records["interval_level"] == int(interval_level))
            & self.records[required_column].notna()
        ].copy()
        if frame.empty:
            raise RuntimeError(f"No validation residuals available for interval level {interval_level}.")

        age_family = self.get_age_family(series_name)
        target_horizon = str(horizon)
        min_points = int(self.config["min_calibration_points"])
        candidates: list[tuple[str, pd.DataFrame, bool, bool, bool]] = []

        def append_candidate(
            label: str,
            subset: pd.DataFrame,
            pooled_horizons: bool,
            pooled_age_family: bool,
            global_pooling: bool,
        ) -> None:
            if not subset.empty:
                candidates.append((label, subset, pooled_horizons, pooled_age_family, global_pooling))

        same_series = frame.loc[frame["series_name"] == series_name]
        if prefer_rolling and target_horizon != "static":
            append_candidate(
                "same_series_same_horizon",
                same_series.loc[
                    (same_series["source_type"] == "rolling") & (same_series["horizon"] == target_horizon)
                ],
                False,
                False,
                False,
            )
        if prefer_rolling:
            append_candidate(
                "same_series_pooled_horizons",
                same_series.loc[same_series["source_type"] == "rolling"],
                True,
                False,
                False,
            )
        append_candidate(
            "same_series_static",
            same_series.loc[same_series["source_type"] == "static"],
            target_horizon != "static",
            False,
            False,
        )

        if self.config["fallback_pooling"] == "age_family":
            family_rows = frame.loc[frame["age_family"] == age_family]
            if prefer_rolling and target_horizon != "static":
                append_candidate(
                    "age_family_same_horizon",
                    family_rows.loc[
                        (family_rows["source_type"] == "rolling") & (family_rows["horizon"] == target_horizon)
                    ],
                    False,
                    True,
                    False,
                )
            if prefer_rolling:
                append_candidate(
                    "age_family_pooled_horizons",
                    family_rows.loc[family_rows["source_type"] == "rolling"],
                    True,
                    True,
                    False,
                )
            append_candidate(
                "age_family_static",
                family_rows.loc[family_rows["source_type"] == "static"],
                True,
                True,
                False,
            )

        append_candidate("global_pooled", frame, True, True, True)

        selected: tuple[str, pd.DataFrame, bool, bool, bool] | None = None
        best_count = -1
        for candidate in candidates:
            if len(candidate[1]) >= min_points:
                selected = candidate
                break
            if len(candidate[1]) > best_count:
                selected = candidate
                best_count = len(candidate[1])

        if selected is None or selected[1].empty:
            raise RuntimeError(
                f"Unable to find calibration residuals for series={series_name}, level={interval_level}, horizon={target_horizon}."
            )

        label, subset, pooled_horizons, pooled_age_family, global_pooling = selected
        metadata = {
            "residual_source_used": label,
            "calibration_points": int(len(subset)),
            "pooled_horizons_used": bool(pooled_horizons),
            "pooled_age_family_used": bool(pooled_age_family),
            "global_pooling_used": bool(global_pooling),
        }
        return subset.reset_index(drop=True), metadata

    def get_calibration_scores(
        self,
        series_name: str,
        interval_level: int,
        horizon: str | int,
        method: str,
        config: dict[str, Any],
        side: str = "main",
    ) -> tuple[np.ndarray, dict[str, Any]]:
        del config
        if method == "conformal_absolute":
            subset, metadata = self._select_rows_with_fallback(
                series_name,
                interval_level,
                horizon,
                required_column="residual_abs",
                prefer_rolling=True,
            )
            return subset["residual_abs"].to_numpy(dtype=float), metadata

        if method == "conformal_standardized":
            subset, metadata = self._select_rows_with_fallback(
                series_name,
                interval_level,
                horizon,
                required_column="standardized_abs_residual",
                prefer_rolling=False,
            )
            return subset["standardized_abs_residual"].to_numpy(dtype=float), metadata

        if method == "conformal_asymmetric":
            column = "lower_miss_score" if side == "lower" else "upper_miss_score"
            subset, metadata = self._select_rows_with_fallback(
                series_name,
                interval_level,
                horizon,
                required_column=column,
                prefer_rolling=False,
            )
            return subset[column].to_numpy(dtype=float), metadata

        raise ValueError(f"Unsupported conformal method for residual lookup: {method}")


def build_residual_bank(forecast_tables: list[dict[str, Any]], config: dict[str, Any]) -> ResidualBank:
    """Build a benchmark-level residual bank from validation and rolling forecasts."""
    resolved = _conformal_config(config)
    age_family_lookup = _invert_age_families(resolved["age_families"])
    interval_levels = [int(level) for level in resolved["interval_levels"]]
    records: list[dict[str, Any]] = []

    for bundle in forecast_tables:
        series_name = bundle["series_name"]
        model_name = bundle["model_name"]
        age_family = age_family_lookup.get(series_name, "overall")
        validation_frame: pd.DataFrame = bundle["validation_frame"]
        rolling_frame: pd.DataFrame = bundle["rolling_validation_frame"]

        for level in interval_levels:
            lower_col = f"raw_lower_{level}"
            upper_col = f"raw_upper_{level}"
            if lower_col in validation_frame.columns and upper_col in validation_frame.columns:
                for row in validation_frame.itertuples(index=False):
                    lower_raw = float(getattr(row, lower_col))
                    upper_raw = float(getattr(row, upper_col))
                    half_width = max((upper_raw - lower_raw) / 2.0, 1.0e-8)
                    center = float(row.point_prediction)
                    y_true = float(row.actual)
                    records.append(
                        asdict(
                            ResidualRecord(
                                series_name=series_name,
                                age_family=age_family,
                                model_name=model_name,
                                split="validation",
                                horizon="static",
                                origin_index=None,
                                target_time_index=int(row.t),
                                y_true=y_true,
                                yhat=center,
                                lower_raw=lower_raw,
                                upper_raw=upper_raw,
                                interval_level=level,
                                nominal_coverage=level / 100.0,
                                residual_abs=abs(y_true - center),
                                raw_half_width=half_width,
                                standardized_abs_residual=abs(y_true - center) / half_width,
                                lower_miss_score=max(lower_raw - y_true, 0.0),
                                upper_miss_score=max(y_true - upper_raw, 0.0),
                                source_type="static",
                            )
                        )
                    )

            for row in rolling_frame.itertuples(index=False):
                records.append(
                    asdict(
                        ResidualRecord(
                            series_name=series_name,
                            age_family=age_family,
                            model_name=model_name,
                            split="validation",
                            horizon=str(int(row.horizon)),
                            origin_index=int(row.origin_end),
                            target_time_index=int(row.target_t),
                            y_true=float(row.actual),
                            yhat=float(row.prediction),
                            lower_raw=None,
                            upper_raw=None,
                            interval_level=level,
                            nominal_coverage=level / 100.0,
                            residual_abs=float(abs(row.actual - row.prediction)),
                            raw_half_width=None,
                            standardized_abs_residual=None,
                            lower_miss_score=None,
                            upper_miss_score=None,
                            source_type="rolling",
                        )
                    )
                )

    return ResidualBank(pd.DataFrame.from_records(records), config)
