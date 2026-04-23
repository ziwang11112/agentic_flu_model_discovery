from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.llm.config import LLMConfig
from src.llm.prompts import build_proposer_prompt
from src.llm.provider import JSONProvider, ProviderResponse
from src.llm.schema import LLMStructureProposal, parse_structure_proposal
from src.llm.summary import PromptSafeSeriesSummary


@dataclass(frozen=True)
class ProposalBatch:
    prompt_text: str
    response_payload: dict[str, Any]
    provider_metadata: dict[str, Any]
    proposals: list[LLMStructureProposal]


def generate_proposals(
    series_summary: PromptSafeSeriesSummary,
    semantics_summary: dict[str, Any],
    llm_config: LLMConfig,
    provider: JSONProvider,
    round_id: int = 1,
    previous_feedback: dict[str, Any] | None = None,
) -> ProposalBatch:
    prompt_text = build_proposer_prompt(series_summary, semantics_summary, llm_config, previous_feedback=previous_feedback)
    provider_response: ProviderResponse = provider.generate_json(
        prompt_text,
        context={
            "role": "proposer",
            "series_name": series_summary.series_name,
            "round_id": round_id,
            "previous_feedback": previous_feedback or {},
            "previous_best_spec": (previous_feedback or {}).get("previous_best_spec"),
            "analyst_feedback": (previous_feedback or {}).get("analyst_feedback"),
        },
    )
    payload = provider_response.payload
    proposals = [parse_structure_proposal(item) for item in payload.get("proposals", [])]
    return ProposalBatch(
        prompt_text=prompt_text,
        response_payload=provider_response.to_record(),
        provider_metadata={
            "provider": provider_response.provider,
            "provider_is_mock": provider_response.provider_is_mock,
            "scientific_claim_allowed": provider_response.scientific_claim_allowed,
        },
        proposals=proposals,
    )
