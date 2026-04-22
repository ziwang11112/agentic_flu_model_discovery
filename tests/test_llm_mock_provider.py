from __future__ import annotations

from pathlib import Path

from src.llm.config import load_llm_config
from src.llm.provider import build_provider


def test_llm_mock_provider_is_deterministic() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    llm_config = load_llm_config(repo_root / "configs" / "llm_v0.yaml")
    provider = build_provider(llm_config)
    prompt = '{"series_name": "0-4 yr"}'
    response_a = provider.generate_json(prompt)
    response_b = provider.generate_json(prompt)
    assert response_a.payload == response_b.payload


def test_llm_mock_provider_returns_valid_candidate_by_default() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    llm_config = load_llm_config(repo_root / "configs" / "llm_v0.yaml")
    provider = build_provider(llm_config)
    response = provider.generate_json('{"series_name": ">= 65 yr"}')
    assert response.provider_is_mock is True
    assert response.scientific_claim_allowed is False
    assert len(response.payload["proposals"]) >= 1
