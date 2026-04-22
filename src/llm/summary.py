from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PromptSafeSeriesSummary:
    series_name: str
    target: str
    n_train: int
    n_val: int
    rate_scale: str
    peakiness: str
    zero_fraction: float
    validation_mean: float
    validation_std: float
    current_discovery_patterns: list[str]

    def to_prompt_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReportSeriesSummary:
    series_name: str
    target: str
    n_train: int
    n_val: int
    rate_scale: str
    peakiness: str
    zero_fraction: float
    current_discovery_patterns: list[str]
    objective_policy: dict[str, Any] | None = None

    def to_report_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rate_scale(y_train: np.ndarray) -> str:
    peak = float(np.max(y_train)) if len(y_train) else 0.0
    if peak >= 1.0:
        return "high"
    if peak >= 0.25:
        return "moderate"
    return "low"


def _peakiness(y_train: np.ndarray) -> str:
    if len(y_train) == 0:
        return "unknown"
    mean = float(np.mean(y_train))
    peak = float(np.max(y_train))
    if mean <= 0:
        return "flat"
    ratio = peak / mean
    if ratio >= 3.0:
        return "high"
    if ratio >= 1.8:
        return "moderate"
    return "low"


def _current_discovery_patterns(series_name: str, structure_frequency_path: Path, limit: int = 3) -> list[str]:
    if not structure_frequency_path.exists():
        raise RuntimeError(f"Required LLM reference artifact is missing: {structure_frequency_path}")
    frame = pd.read_csv(structure_frequency_path)
    subset = frame.loc[frame["series_name"] == series_name].copy()
    if subset.empty:
        return []
    ordered = subset.sort_values(
        ["selected_structure_frequency", "count", "structure_spec"],
        ascending=[False, False, True],
    )
    return ordered["structure_spec"].head(limit).astype(str).tolist()


def build_prompt_safe_series_summary(
    series_name: str,
    y_train: np.ndarray,
    y_val: np.ndarray,
    structure_frequency_path: Path,
) -> PromptSafeSeriesSummary:
    return PromptSafeSeriesSummary(
        series_name=series_name,
        target="weekly hospitalization rate",
        n_train=int(len(y_train)),
        n_val=int(len(y_val)),
        rate_scale=_rate_scale(y_train),
        peakiness=_peakiness(y_train),
        zero_fraction=float(np.mean(y_train == 0.0)) if len(y_train) else 0.0,
        validation_mean=float(np.mean(y_val)) if len(y_val) else 0.0,
        validation_std=float(np.std(y_val)) if len(y_val) else 0.0,
        current_discovery_patterns=_current_discovery_patterns(series_name, structure_frequency_path),
    )


def build_report_series_summary(
    prompt_safe_summary: PromptSafeSeriesSummary,
    objective_policy_row: dict[str, Any] | None = None,
) -> ReportSeriesSummary:
    return ReportSeriesSummary(
        series_name=prompt_safe_summary.series_name,
        target=prompt_safe_summary.target,
        n_train=prompt_safe_summary.n_train,
        n_val=prompt_safe_summary.n_val,
        rate_scale=prompt_safe_summary.rate_scale,
        peakiness=prompt_safe_summary.peakiness,
        zero_fraction=prompt_safe_summary.zero_fraction,
        current_discovery_patterns=prompt_safe_summary.current_discovery_patterns,
        objective_policy=objective_policy_row,
    )
