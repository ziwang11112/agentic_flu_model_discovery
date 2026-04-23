from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.llm.config import LLMConfig
from src.llm.prompts import build_critic_prompt
from src.llm.provider import JSONProvider
from src.llm.schema import LLMStructureProposal
from src.llm.summary import PromptSafeSeriesSummary


@dataclass(frozen=True)
class CriticDecision:
    prompt_text: str
    response_payload: dict[str, Any]
    annotations: dict[int, dict[str, Any]]
    rejected_ids: set[int]


def run_critic(
    series_summary: PromptSafeSeriesSummary,
    semantics_summary: dict[str, Any],
    proposals: list[LLMStructureProposal],
    llm_config: LLMConfig,
    provider: JSONProvider,
) -> CriticDecision:
    prompt_text = build_critic_prompt(series_summary, semantics_summary, proposals, llm_config)
    response = provider.generate_json(
        prompt_text,
        context={"role": "critic", "series_name": series_summary.series_name},
    )
    payload = response.payload
    annotations: dict[int, dict[str, Any]] = {}
    for accepted in payload.get("accepted", []):
        index = int(accepted["proposal_index"])
        annotations[index] = {
            "critic_priority": str(accepted.get("priority", "medium")),
            "critic_risk_flags": "",
        }
    for rejected in payload.get("rejected", []):
        index = int(rejected["proposal_index"])
        annotations[index] = {
            "critic_priority": "low",
            "critic_risk_flags": str(rejected.get("reason", "")),
        }
    for index in range(len(proposals)):
        annotations.setdefault(index, {"critic_priority": "medium", "critic_risk_flags": ""})
    return CriticDecision(
        prompt_text=prompt_text,
        response_payload=response.to_record(),
        annotations=annotations,
        rejected_ids={int(item["proposal_index"]) for item in payload.get("rejected", [])},
    )
