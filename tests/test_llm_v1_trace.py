from __future__ import annotations

from dataclasses import replace
import json

import numpy as np

from src.data.split import make_chronological_split
from src.discovery.search import SearchConfig
from src.llm.orchestrator import run_llm_iterative_refinement
from src.models.base import FitConfig
from tests.test_llm_orchestrator import _llm_config


def test_v1_trace_exists_and_contains_no_test_metrics(tmp_path) -> None:
    llm_config = replace(
        _llm_config(tmp_path),
        output_root=tmp_path / "artifacts_llm_v1",
        max_rounds=2,
        early_stop_patience=1,
        min_score_improvement=1.0,
    )
    y = np.array([0.08, 0.12, 0.15, 0.20, 0.25, 0.18, 0.13, 0.11, 0.09, 0.10, 0.08, 0.07], dtype=float)
    split = make_chronological_split(len(y))
    artifact_dir = tmp_path / "artifacts_llm_v1" / "overall"
    run_llm_iterative_refinement(
        series_name="Overall",
        y=y,
        split=split,
        fit_config=FitConfig(n_restarts=1, rolling_n_restarts=1, maxiter=5, calibrate_intervals=False),
        search_config=SearchConfig(max_rounds=1, beam_width=3, patience=1),
        llm_config=llm_config,
        artifact_dir=artifact_dir,
        seed=42,
    )
    trace_path = artifact_dir / "llm_refinement_trace.jsonl"
    assert trace_path.exists()
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    for line in lines:
        assert "test_mae" not in line
        assert "test_rmse" not in line
        payload = json.loads(line)
        assert {"series_name", "round_id", "new_specs", "round_best_spec", "early_stop"}.issubset(payload.keys())
        assert payload["series_name"] == "Overall"
