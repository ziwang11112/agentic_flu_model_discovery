from __future__ import annotations

from dataclasses import replace

from src.llm.provider import OpenAIJSONProvider
from tests.test_llm_orchestrator import _llm_config


class _FakeOpenAIResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text

    def model_dump(self) -> dict[str, object]:
        return {"output_text": self.output_text}


class _FakeResponsesAPI:
    def __init__(self, output_texts: list[str]) -> None:
        self.output_texts = output_texts
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.output_texts:
            raise AssertionError("No fake responses remaining")
        return _FakeOpenAIResponse(self.output_texts.pop(0))


class _FakeClient:
    def __init__(self, output_texts: list[str]) -> None:
        self.responses = _FakeResponsesAPI(output_texts)


def test_openai_provider_parses_valid_json_response(tmp_path) -> None:
    llm_config = replace(_llm_config(tmp_path), provider="openai")
    client = _FakeClient(
        [
            (
                '{"series_name":"5-17 yr","proposals":[{"structure_name":"SEIRS",'
                '"fractional":false,"observation_map":"delayed_I","delay_weeks":2,'
                '"rationale":"Valid test proposal.","expected_failure_mode":"May underperform."}]}'
            )
        ]
    )
    provider = OpenAIJSONProvider(llm_config, client=client)
    response = provider.generate_json(
        '{"series_name":"5-17 yr"}',
        context={"role": "proposer", "series_name": "5-17 yr"},
    )

    assert response.provider == "openai"
    assert response.provider_is_mock is False
    assert response.scientific_claim_allowed is True
    assert response.attempt_count == 1
    assert response.payload["series_name"] == "5-17 yr"
    assert response.payload["proposals"][0]["observation_map"] == "delayed_I"
    assert len(client.responses.calls) == 1


def test_openai_provider_retries_with_json_repair_prompt(tmp_path) -> None:
    llm_config = replace(_llm_config(tmp_path), provider="openai")
    client = _FakeClient(
        [
            "not-json-at-all",
            (
                '{"series_name":"5-17 yr","accepted":[{"proposal_index":0,"priority":"high",'
                '"reason":"Recovered after repair."}],"rejected":[],"suggested_edits":[]}'
            ),
        ]
    )
    provider = OpenAIJSONProvider(llm_config, client=client)
    response = provider.generate_json(
        '{"series_name":"5-17 yr"}',
        context={"role": "critic", "series_name": "5-17 yr"},
    )

    assert response.attempt_count == 2
    assert response.payload["accepted"][0]["proposal_index"] == 0
    assert len(client.responses.calls) == 2
    second_call_input = client.responses.calls[1]["input"]
    assert isinstance(second_call_input, list)
    assert "invalid or unparsable json" in str(second_call_input[-1]["content"]).lower()
