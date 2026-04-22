from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from src.data.split import make_chronological_split
from src.discovery.search import SearchConfig
from src.llm.orchestrator import run_llm_iterative_refinement
from src.models.base import FitConfig
from tests.test_llm_orchestrator import _llm_config


def test_v1_prompt_files_exclude_banned_terms(tmp_path) -> None:
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
    prompt_files = list((artifact_dir / "rounds").glob("round_*/*prompt.txt"))
    assert prompt_files
    for prompt_path in prompt_files:
        content = prompt_path.read_text(encoding="utf-8").lower()
        for term in llm_config.banned_prompt_terms:
            assert term.lower() not in content

    for leaderboard_path in (artifact_dir / "rounds").glob("round_*/llm_leaderboard.csv"):
        text = leaderboard_path.read_text(encoding="utf-8").lower()
        assert "test_mae" not in text
        assert "test_rmse" not in text

    assert (artifact_dir / "final_selected_test_report.csv").exists()
