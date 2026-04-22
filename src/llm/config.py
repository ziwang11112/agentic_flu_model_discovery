from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_BANNED_PROMPT_TERMS = [
    "test_policy_model",
    "best_test_model",
    "test_mae",
    "test_rmse",
    "test_smape",
    "test coverage",
    "benchmark_series_winners",
    "final test winner",
    "held-out test winner",
]


@dataclass(frozen=True)
class LLMConfig:
    enabled: bool
    method_name: str
    provider: str
    model: str
    cheap_model: str
    temperature: float
    max_candidate_specs: int
    use_critic: bool
    use_semantics_agent: bool
    max_rounds: int
    allow_test_metrics: bool
    output_root: Path
    compare_against: str
    critic_hard_filter: bool
    early_stop_patience: int
    min_score_improvement: float
    feedback_metric: str
    nonllm_reference_root: Path
    nonllm_reference_method: str
    v0_reference_root: Path
    objective_policy_path: Path
    structure_frequency_path: Path
    allowed_structures: tuple[str, ...]
    allowed_observation_maps: tuple[str, ...]
    allowed_delay_weeks: tuple[int, ...]
    banned_prompt_terms: tuple[str, ...] = field(default_factory=lambda: tuple(DEFAULT_BANNED_PROMPT_TERMS))


def _repo_root_from_config_path(config_path: Path) -> Path:
    return config_path.resolve().parent.parent


def load_llm_config(config_path: Path) -> LLMConfig:
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    repo_root = _repo_root_from_config_path(config_path)
    llm = raw["llm"]
    leakage_guard = llm.get("leakage_guard", {})
    return LLMConfig(
        enabled=bool(llm.get("enabled", True)),
        method_name=str(llm.get("method_name", "llm_structure_proposal_search")),
        provider=str(llm.get("provider", "mock")),
        model=str(llm.get("model", "gpt-5.2")),
        cheap_model=str(llm.get("cheap_model", "gpt-5-mini")),
        temperature=float(llm.get("temperature", 0.0)),
        max_candidate_specs=int(llm.get("max_candidate_specs", 8)),
        use_critic=bool(llm.get("use_critic", True)),
        use_semantics_agent=bool(llm.get("use_semantics_agent", True)),
        max_rounds=int(llm.get("max_rounds", 1)),
        allow_test_metrics=bool(llm.get("allow_test_metrics", False)),
        output_root=repo_root / str(llm.get("output_root", "artifacts_llm_v0")),
        compare_against=str(llm.get("compare_against", "constrained_structure_discovery")),
        critic_hard_filter=bool(llm.get("critic_hard_filter", False)),
        early_stop_patience=int(llm.get("early_stop_patience", 1)),
        min_score_improvement=float(llm.get("min_score_improvement", 1.0e-4)),
        feedback_metric=str(llm.get("feedback_metric", "score")),
        nonllm_reference_root=repo_root / str(llm["nonllm_reference_root"]),
        nonllm_reference_method=str(llm.get("nonllm_reference_method", "constrained_structure_discovery")),
        v0_reference_root=repo_root / str(llm.get("v0_reference_root", "artifacts_llm_v0")),
        objective_policy_path=repo_root / str(llm["objective_policy_path"]),
        structure_frequency_path=repo_root / str(llm["structure_frequency_path"]),
        allowed_structures=tuple(str(value) for value in llm["allowed_structures"]),
        allowed_observation_maps=tuple(str(value) for value in llm["allowed_observation_maps"]),
        allowed_delay_weeks=tuple(int(value) for value in llm["allowed_delay_weeks"]),
        banned_prompt_terms=tuple(str(term) for term in leakage_guard.get("banned_prompt_terms", DEFAULT_BANNED_PROMPT_TERMS)),
    )


def provider_metadata(config: LLMConfig) -> dict[str, Any]:
    provider_is_mock = config.provider == "mock"
    return {
        "provider": config.provider,
        "provider_is_mock": provider_is_mock,
        "scientific_claim_allowed": not provider_is_mock,
    }
