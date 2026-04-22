from __future__ import annotations

from pathlib import Path


def test_saved_prompt_files_do_not_contain_banned_terms(tmp_path: Path) -> None:
    from tests.test_llm_orchestrator import _llm_config
    import numpy as np

    from src.data.split import make_chronological_split
    from src.discovery.search import SearchConfig
    from src.llm.orchestrator import run_llm_structure_search
    from src.models.base import FitConfig

    llm_config = _llm_config(tmp_path)
    y = np.array([0.08, 0.12, 0.15, 0.20, 0.25, 0.18, 0.13, 0.11, 0.09, 0.10, 0.08, 0.07], dtype=float)
    split = make_chronological_split(len(y))
    artifact_dir = tmp_path / "artifacts_llm_v0" / "overall"
    run_llm_structure_search(
        series_name="Overall",
        y=y,
        split=split,
        fit_config=FitConfig(n_restarts=1, rolling_n_restarts=1, maxiter=5, calibrate_intervals=False),
        search_config=SearchConfig(max_rounds=1, beam_width=3, patience=1),
        llm_config=llm_config,
        artifact_dir=artifact_dir,
        seed=42,
    )
    proposer_prompt = (artifact_dir / "proposer_prompt.txt").read_text(encoding="utf-8").lower()
    critic_prompt = (artifact_dir / "critic_prompt.txt").read_text(encoding="utf-8").lower()
    for term in llm_config.banned_prompt_terms:
        assert term.lower() not in proposer_prompt
        assert term.lower() not in critic_prompt
