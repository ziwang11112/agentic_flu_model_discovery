from __future__ import annotations

from src.llm.proposer import generate_proposals
from src.llm.provider import ProviderResponse
from src.llm.semantics import build_surveillance_semantics_summary
from src.llm.summary import build_prompt_safe_series_summary
from tests.test_llm_orchestrator import _llm_config


class _InvalidProposalProvider:
    def generate_json(self, prompt, system_prompt=None, context=None) -> ProviderResponse:
        del prompt, system_prompt, context
        payload = {
            "series_name": "Overall",
            "proposals": [
                {
                    "structure_name": "SIR",
                    "fractional": False,
                    "observation_map": "I",
                    "delay_weeks": 1,
                    "rationale": "Intentionally invalid conditional delay for regression coverage.",
                    "expected_failure_mode": "Should be schema-invalid but auditable.",
                }
            ],
        }
        return ProviderResponse(
            payload=payload,
            raw_response={"fake": True},
            raw_response_text="{}",
            attempt_count=1,
            provider="openai",
            provider_is_mock=False,
            scientific_claim_allowed=True,
        )


def test_generate_proposals_preserves_schema_invalid_raw_proposals(tmp_path) -> None:
    llm_config = _llm_config(tmp_path)
    summary = build_prompt_safe_series_summary(
        series_name="Overall",
        y_train=[0.1, 0.2, 0.3],
        y_val=[0.2, 0.1],
        structure_frequency_path=llm_config.structure_frequency_path,
    )
    batch = generate_proposals(
        series_summary=summary,
        semantics_summary=build_surveillance_semantics_summary().to_dict(),
        llm_config=llm_config,
        provider=_InvalidProposalProvider(),
    )

    assert batch.proposals[0]["observation_map"] == "I"
    assert batch.proposals[0]["delay_weeks"] == 1
