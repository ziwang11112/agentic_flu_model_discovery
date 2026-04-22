from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data.split import make_chronological_split
from src.discovery.search import SearchConfig
from src.llm.config import LLMConfig
from src.llm.orchestrator import run_llm_structure_search, write_llm_global_outputs
from src.models.base import FitConfig


def _llm_config(tmp_path: Path) -> LLMConfig:
    reference_root = tmp_path / "reference"
    v0_reference_root = tmp_path / "v0_reference"
    reference_root.mkdir(parents=True, exist_ok=True)
    v0_reference_root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "series_name": "Overall",
                "model_name": "constrained_structure_discovery",
                "num_seeds": 5,
                "mean_test_mae": 0.10,
                "std_test_mae": 0.01,
                "mean_rolling_mae": 0.12,
                "std_rolling_mae": 0.02,
                "test_win_count": 2,
                "rolling_win_count": 2,
                "num_free_params": 9,
                "num_compartments": 3,
                "test_win_rate": 0.4,
                "rolling_win_rate": 0.4,
                "discovery_structure_name": "SIR",
            }
        ]
    ).to_csv(reference_root / "multiseed_model_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "series_name": "Overall",
                "test_policy_model": "deterministic_seir",
                "rolling_policy_model": "deterministic_seir",
                "parsimony_policy_model": "deterministic_seir",
                "objective_conflict_flag": False,
                "test_tie_models": "deterministic_seir",
                "rolling_tie_models": "deterministic_seir",
                "test_best_mae": 0.1,
                "rolling_best_mae": 0.12,
                "recommended_reason": "Reference note.",
            }
        ]
    ).to_csv(reference_root / "multiseed_objective_policy.csv", index=False)
    pd.DataFrame(
        [
            {
                "series_name": "Overall",
                "structure_spec": "SIR|fractional=0|obs=I",
                "count": 5,
                "mean_test_mae": 0.10,
                "mean_rolling_mae": 0.12,
                "num_seeds": 5,
                "selected_structure_frequency": 1.0,
            }
        ]
    ).to_csv(reference_root / "multiseed_discovery_structure_frequency.csv", index=False)
    seed_leaderboard_dir = reference_root / "seed_runs" / "seed_0" / "overall" / "constrained_structure_discovery"
    seed_leaderboard_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"spec_key": "SIR|fractional=0|obs=I", "score": 0.12},
            {"spec_key": "SEIR|fractional=0|obs=I", "score": 0.14},
        ]
    ).to_csv(seed_leaderboard_dir / "leaderboard.csv", index=False)
    pd.DataFrame(
        [
            {
                "series_name": "Overall",
                "llm_best_spec": "SIR|fractional=0|obs=I",
                "llm_best_score": 0.13,
                "llm_best_rolling_mean_mae": 0.13,
                "llm_best_test_mae": 0.11,
                "llm_num_candidates_evaluated": 2,
            }
        ]
    ).to_csv(v0_reference_root / "llm_vs_nonllm_summary.csv", index=False)

    return LLMConfig(
        enabled=True,
        method_name="llm_structure_proposal_search",
        provider="mock",
        model="gpt-5.2",
        cheap_model="gpt-5-mini",
        temperature=0.0,
        max_candidate_specs=8,
        use_critic=True,
        use_semantics_agent=True,
        max_rounds=1,
        allow_test_metrics=False,
        output_root=tmp_path / "artifacts_llm_v0",
        compare_against="constrained_structure_discovery",
        critic_hard_filter=False,
        early_stop_patience=1,
        min_score_improvement=1.0e-4,
        feedback_metric="score",
        nonllm_reference_root=reference_root,
        nonllm_reference_method="constrained_structure_discovery",
        v0_reference_root=v0_reference_root,
        objective_policy_path=reference_root / "multiseed_objective_policy.csv",
        structure_frequency_path=reference_root / "multiseed_discovery_structure_frequency.csv",
        allowed_structures=("SIR", "SEIR", "SEIRS", "SEIHR", "SEIAR"),
        allowed_observation_maps=("I", "H", "I+H", "delayed_I"),
        allowed_delay_weeks=(0, 1, 2, 3),
        banned_prompt_terms=(
            "test_policy_model",
            "best_test_model",
            "test_mae",
            "test_rmse",
            "test_smape",
            "test coverage",
            "benchmark_series_winners",
            "final test winner",
            "held-out test winner",
        ),
    )


def test_run_llm_structure_search_mock_mode(tmp_path: Path) -> None:
    llm_config = _llm_config(tmp_path)
    y = np.array([0.08, 0.12, 0.15, 0.20, 0.25, 0.18, 0.13, 0.11, 0.09, 0.10, 0.08, 0.07], dtype=float)
    split = make_chronological_split(len(y))
    result = run_llm_structure_search(
        series_name="Overall",
        y=y,
        split=split,
        fit_config=FitConfig(n_restarts=1, rolling_n_restarts=1, maxiter=5, calibrate_intervals=False),
        search_config=SearchConfig(max_rounds=1, beam_width=3, patience=1),
        llm_config=llm_config,
        artifact_dir=tmp_path / "artifacts_llm_v0" / "overall",
        seed=42,
    )
    assert (tmp_path / "artifacts_llm_v0" / "overall" / "proposal_audit.csv").exists()
    assert (tmp_path / "artifacts_llm_v0" / "overall" / "llm_leaderboard.csv").exists()
    assert (tmp_path / "artifacts_llm_v0" / "overall" / "proposer_prompt.txt").exists()
    assert (tmp_path / "artifacts_llm_v0" / "overall" / "critic_prompt.txt").exists()
    assert not result["llm_leaderboard"].empty
    assert {"round_id", "proposal_id", "role_source", "critic_priority", "schema_valid", "hard_valid", "invalid_reason"}.issubset(
        result["llm_leaderboard"].columns
    )

    outputs = write_llm_global_outputs([result], llm_config, llm_config.output_root)
    assert outputs["summary"].exists()
    summary = pd.read_csv(outputs["summary"])
    assert {
        "llm_num_candidates_evaluated",
        "nonllm_num_candidates_evaluated",
        "llm_best_score",
        "nonllm_best_score",
        "llm_valid_proposal_rate",
        "candidate_efficiency_note",
    }.issubset(summary.columns)
