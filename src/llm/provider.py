from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.discovery.rules import StructureSpec
from src.llm.config import LLMConfig
from src.llm.refinement import build_refinement_proposals


@dataclass(frozen=True)
class ProviderResponse:
    payload: dict[str, Any]
    provider: str
    provider_is_mock: bool
    scientific_claim_allowed: bool


class MockLLMProvider:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @staticmethod
    def _extract_series_name(prompt: str) -> str:
        match = re.search(r'"series_name":\s*"([^"]+)"', prompt)
        if match is None:
            raise ValueError("series_name_missing_from_prompt")
        return match.group(1)

    def _proposal_payload(self, series_name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        round_id = int(context.get("round_id", 1))
        library = {
            "Overall": [
                {"structure_name": "SIR", "fractional": False, "observation_map": "I", "delay_weeks": 0},
                {"structure_name": "SEIR", "fractional": False, "observation_map": "delayed_I", "delay_weeks": 1},
            ],
            "0-4 yr": [
                {"structure_name": "SEIRS", "fractional": False, "observation_map": "delayed_I", "delay_weeks": 2},
                {"structure_name": "SEIRS", "fractional": False, "observation_map": "I", "delay_weeks": 0},
            ],
            "5-17 yr": [
                {"structure_name": "SEIRS", "fractional": False, "observation_map": "delayed_I", "delay_weeks": 2},
                {"structure_name": "SEIR", "fractional": False, "observation_map": "I", "delay_weeks": 0},
            ],
            "18-49 yr": [
                {"structure_name": "SIR", "fractional": False, "observation_map": "I", "delay_weeks": 0},
                {"structure_name": "SEIR", "fractional": False, "observation_map": "delayed_I", "delay_weeks": 1},
            ],
            "50-64 yr": [
                {"structure_name": "SEIR", "fractional": False, "observation_map": "delayed_I", "delay_weeks": 1},
                {"structure_name": "SIR", "fractional": False, "observation_map": "I", "delay_weeks": 0},
            ],
            ">= 65 yr": [
                {"structure_name": "SEIRS", "fractional": True, "observation_map": "delayed_I", "delay_weeks": 2},
                {"structure_name": "SEIRS", "fractional": True, "observation_map": "I", "delay_weeks": 0},
            ],
        }
        if round_id == 1 or not context.get("previous_best_spec"):
            proposal_records = library.get(series_name, library["Overall"])[: self.config.max_candidate_specs]
        else:
            previous_best = context["previous_best_spec"]
            base_spec = StructureSpec(
                structure_name=str(previous_best["structure_name"]),
                fractional=bool(previous_best["fractional"]),
                observation_map=str(previous_best["observation_map"]),
                delay_weeks=int(previous_best.get("delay_weeks", 0)),
            )
            proposal_records = [
                {
                    "structure_name": proposal.structure_name,
                    "fractional": proposal.fractional,
                    "observation_map": proposal.observation_map,
                    "delay_weeks": proposal.delay_weeks,
                    "rationale": proposal.rationale,
                    "expected_failure_mode": proposal.expected_failure_mode,
                }
                for proposal in build_refinement_proposals(
                    base_spec=base_spec,
                    series_name=series_name,
                    max_candidates=self.config.max_candidate_specs,
                    analyst_feedback=context.get("analyst_feedback"),
                )
            ]

        proposals = []
        for record in proposal_records:
            proposals.append(
                {
                    **record,
                    "rationale": record.get("rationale", "Mock provider engineering smoke-test proposal."),
                    "expected_failure_mode": record.get(
                        "expected_failure_mode",
                        "May underperform validation or rolling stability.",
                    ),
                }
            )
        return {"series_name": series_name, "proposals": proposals}

    def _critic_payload(self, series_name: str, prompt: str) -> dict[str, Any]:
        proposal_count = len(re.findall(r'"structure_name":', prompt))
        accepted = []
        for index in range(proposal_count):
            accepted.append(
                {
                    "proposal_index": index,
                    "priority": "high" if index == 0 else "medium",
                    "reason": f"Mock critic review for {series_name}.",
                }
            )
        return {"series_name": series_name, "accepted": accepted, "rejected": [], "suggested_edits": []}

    def _analyst_payload(self, series_name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        previous_best = context.get("previous_best_spec", {})
        leaderboard = context.get("round_leaderboard", [])
        best_row = leaderboard[0] if leaderboard else {}

        failure_modes: list[str] = []
        constraints: list[str] = []
        instruction = "Refine the previous best with one-step edits and preserve parsimony."

        if best_row:
            val_mae = float(best_row.get("val_mae", 0.0))
            rolling_mae = float(best_row.get("rolling_val_mean_mae", 0.0))
            if rolling_mae > val_mae + 0.02:
                failure_modes.append("rolling_instability")
                constraints.append("prefer simpler or more delay-aware edits")
                instruction = "Try local edits that improve rolling stability without inventing new structures."
            if float(best_row.get("complexity_penalty", 0.0)) > 0.15:
                failure_modes.append("excess_complexity")
                constraints.append("drop unnecessary complexity")

        if previous_best.get("observation_map") in {"H", "I+H"}:
            failure_modes.append("h_identifiability_risk")
            constraints.append("drop H if weakly identifiable")
            instruction = "Prefer delayed_I or I over explicit H if rolling evidence is weak."
        elif series_name in {"0-4 yr", "5-17 yr", ">= 65 yr"}:
            constraints.append("consider delayed_I around the current best")
            instruction = "Refine around the current best and keep delayed observation on the table."

        if not failure_modes:
            failure_modes.append("local_search")

        return {
            "series_name": series_name,
            "observed_failure_modes": failure_modes,
            "next_round_constraints": constraints,
            "proposer_instruction": instruction,
        }

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        del system_prompt
        context = context or {}
        series_name = context.get("series_name") or self._extract_series_name(prompt)
        lowered = prompt.lower()
        role = str(context.get("role", "")).lower()
        if role == "analyst" or "you are a result analyst" in lowered:
            payload = self._analyst_payload(series_name, context)
        elif role == "critic" or "critic for epidemic model structure proposals" in lowered:
            payload = self._critic_payload(series_name, prompt)
        else:
            payload = self._proposal_payload(series_name, context)
        return ProviderResponse(
            payload=payload,
            provider="mock",
            provider_is_mock=True,
            scientific_claim_allowed=False,
        )


def build_provider(config: LLMConfig) -> MockLLMProvider:
    if config.provider != "mock":
        raise NotImplementedError("This PR implements provider=mock only for the LLM stack.")
    return MockLLMProvider(config)
