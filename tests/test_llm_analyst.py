from __future__ import annotations

import numpy as np
import pandas as pd

from src.llm.analyst import build_analyst_prompt, run_analyst
from src.llm.provider import build_provider
from src.llm.summary import build_prompt_safe_series_summary
from tests.test_llm_orchestrator import _llm_config


def test_analyst_prompt_excludes_banned_terms(tmp_path) -> None:
    llm_config = _llm_config(tmp_path)
    summary = build_prompt_safe_series_summary(
        series_name="Overall",
        y_train=np.array([0.1, 0.2, 0.3], dtype=float),
        y_val=np.array([0.15, 0.12], dtype=float),
        structure_frequency_path=llm_config.structure_frequency_path,
    )
    leaderboard = pd.DataFrame(
        [
            {
                "series_name": "Overall",
                "round_id": 1,
                "proposal_id": 0,
                "structure_name": "SIR",
                "fractional": False,
                "observation_map": "I",
                "delay_weeks": 0,
                "val_mae": 0.1,
                "val_rmse": 0.12,
                "rolling_val_mean_mae": 0.14,
                "rolling_val_mean_rmse": 0.16,
                "rolling_val_std_mae": 0.02,
                "score": 0.25,
                "complexity_penalty": 0.08,
                "stability_penalty": 0.04,
                "age_prior_penalty": 0.0,
                "multi_split_penalty": 0.02,
            }
        ]
    )
    prompt = build_analyst_prompt(
        series_summary=summary,
        llm_config=llm_config,
        round_id=1,
        previous_best_spec={"structure_name": "SIR", "fractional": False, "observation_map": "I", "delay_weeks": 0},
        round_leaderboard=leaderboard,
    )
    for term in llm_config.banned_prompt_terms:
        assert term.lower() not in prompt.lower()


def test_analyst_feedback_parses_strict_json(tmp_path) -> None:
    llm_config = _llm_config(tmp_path)
    provider = build_provider(llm_config)
    summary = build_prompt_safe_series_summary(
        series_name=">= 65 yr",
        y_train=np.array([0.3, 0.4, 0.5, 0.45], dtype=float),
        y_val=np.array([0.42, 0.38], dtype=float),
        structure_frequency_path=llm_config.structure_frequency_path,
    )
    leaderboard = pd.DataFrame(
        [
            {
                "series_name": ">= 65 yr",
                "round_id": 1,
                "proposal_id": 0,
                "structure_name": "SEIRS",
                "fractional": True,
                "observation_map": "I",
                "delay_weeks": 0,
                "val_mae": 0.12,
                "val_rmse": 0.14,
                "rolling_val_mean_mae": 0.18,
                "rolling_val_mean_rmse": 0.20,
                "rolling_val_std_mae": 0.03,
                "score": 0.41,
                "complexity_penalty": 0.1,
                "stability_penalty": 0.07,
                "age_prior_penalty": -0.002,
                "multi_split_penalty": 0.04,
            }
        ]
    )
    decision = run_analyst(
        series_summary=summary,
        llm_config=llm_config,
        provider=provider,
        round_id=1,
        previous_best_spec={"structure_name": "SEIRS", "fractional": True, "observation_map": "I", "delay_weeks": 0},
        round_leaderboard=leaderboard,
    )
    assert isinstance(decision.feedback.observed_failure_modes, list)
    assert isinstance(decision.feedback.next_round_constraints, list)
    assert isinstance(decision.feedback.proposer_instruction, str)
