from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from src.data.split import make_chronological_split
from src.discovery.search import SearchConfig
from src.llm.orchestrator import run_llm_iterative_refinement, write_llm_v1_global_outputs
from src.models.base import FitConfig
from tests.test_llm_orchestrator import _llm_config


def test_v1_single_series_mock_run_completes(tmp_path) -> None:
    llm_config = replace(
        _llm_config(tmp_path),
        output_root=tmp_path / "artifacts_llm_v1",
        max_rounds=3,
        early_stop_patience=1,
        min_score_improvement=1.0,
        feedback_metric="score",
    )
    y = np.array([0.08, 0.12, 0.15, 0.20, 0.25, 0.18, 0.13, 0.11, 0.09, 0.10, 0.08, 0.07], dtype=float)
    split = make_chronological_split(len(y))
    result = run_llm_iterative_refinement(
        series_name="Overall",
        y=y,
        split=split,
        fit_config=FitConfig(n_restarts=1, rolling_n_restarts=1, maxiter=5, calibrate_intervals=False),
        search_config=SearchConfig(max_rounds=1, beam_width=3, patience=1),
        llm_config=llm_config,
        artifact_dir=tmp_path / "artifacts_llm_v1" / "overall",
        seed=42,
    )
    assert (tmp_path / "artifacts_llm_v1" / "overall" / "llm_refinement_trace.jsonl").exists()
    assert (tmp_path / "artifacts_llm_v1" / "overall" / "final_selected_test_report.csv").exists()
    assert result["trace_records"]
    assert any(record.early_stop for record in result["trace_records"][1:]) or len(result["trace_records"]) == 1
    for round_output in result["round_outputs"]:
        assert "test_mae" not in round_output["llm_leaderboard"].columns
        assert "test_rmse" not in round_output["llm_leaderboard"].columns

    outputs = write_llm_v1_global_outputs([result], llm_config, llm_config.output_root)
    assert outputs["summary"].exists()
    summary = pd.read_csv(outputs["summary"])
    assert {
        "v1_best_spec",
        "v0_best_spec",
        "nonllm_best_spec",
        "v1_num_candidates_evaluated",
        "v0_num_candidates_evaluated",
    }.issubset(summary.columns)
