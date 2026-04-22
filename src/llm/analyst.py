from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.llm.config import LLMConfig
from src.llm.prompts import assert_no_banned_terms
from src.llm.provider import MockLLMProvider
from src.llm.summary import PromptSafeSeriesSummary


@dataclass(frozen=True)
class AnalystFeedback:
    observed_failure_modes: list[str]
    next_round_constraints: list[str]
    proposer_instruction: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_failure_modes": self.observed_failure_modes,
            "next_round_constraints": self.next_round_constraints,
            "proposer_instruction": self.proposer_instruction,
        }


@dataclass(frozen=True)
class AnalystDecision:
    prompt_text: str
    response_payload: dict[str, Any]
    feedback: AnalystFeedback


def build_analyst_prompt(
    series_summary: PromptSafeSeriesSummary,
    llm_config: LLMConfig,
    round_id: int,
    previous_best_spec: dict[str, Any],
    round_leaderboard: pd.DataFrame,
) -> str:
    safe_columns = [
        "series_name",
        "round_id",
        "proposal_id",
        "structure_name",
        "fractional",
        "observation_map",
        "delay_weeks",
        "val_mae",
        "val_rmse",
        "rolling_val_mean_mae",
        "rolling_val_mean_rmse",
        "rolling_val_std_mae",
        "score",
        "complexity_penalty",
        "stability_penalty",
        "age_prior_penalty",
        "multi_split_penalty",
    ]
    leaderboard_payload = round_leaderboard.loc[:, [column for column in safe_columns if column in round_leaderboard.columns]]
    prompt = (
        "You are a result analyst for iterative epidemic structure search.\n\n"
        "You read validation and rolling-only round results and produce refinement feedback.\n"
        "Do not use test metrics.\n"
        "Do not choose final winners.\n"
        "Do not write code.\n\n"
        f"Round id: {round_id}\n\n"
        f"Series summary:\n{series_summary.to_prompt_dict()}\n\n"
        f"Previous best spec:\n{previous_best_spec}\n\n"
        f"Round leaderboard (validation/rolling only):\n{leaderboard_payload.to_dict(orient='records')}\n\n"
        "Return strict JSON with keys:\n"
        "- observed_failure_modes\n"
        "- next_round_constraints\n"
        "- proposer_instruction\n"
    )
    assert_no_banned_terms(prompt, llm_config.banned_prompt_terms)
    return prompt


def parse_analyst_feedback(payload: dict[str, Any]) -> AnalystFeedback:
    return AnalystFeedback(
        observed_failure_modes=[str(item) for item in payload.get("observed_failure_modes", [])],
        next_round_constraints=[str(item) for item in payload.get("next_round_constraints", [])],
        proposer_instruction=str(payload.get("proposer_instruction", "")),
    )


def run_analyst(
    series_summary: PromptSafeSeriesSummary,
    llm_config: LLMConfig,
    provider: MockLLMProvider,
    round_id: int,
    previous_best_spec: dict[str, Any],
    round_leaderboard: pd.DataFrame,
) -> AnalystDecision:
    prompt_text = build_analyst_prompt(
        series_summary=series_summary,
        llm_config=llm_config,
        round_id=round_id,
        previous_best_spec=previous_best_spec,
        round_leaderboard=round_leaderboard,
    )
    response = provider.generate_json(
        prompt_text,
        context={
            "role": "analyst",
            "series_name": series_summary.series_name,
            "round_id": round_id,
            "previous_best_spec": previous_best_spec,
            "round_leaderboard": round_leaderboard.loc[
                :,
                [column for column in round_leaderboard.columns if not column.startswith("test_")],
            ].to_dict(orient="records"),
        },
    )
    feedback = parse_analyst_feedback(response.payload)
    return AnalystDecision(prompt_text=prompt_text, response_payload=response.payload, feedback=feedback)
