from __future__ import annotations

from pathlib import Path

from src.llm.config import load_llm_config
from src.llm.prompts import build_critic_prompt, build_proposer_prompt
from src.llm.schema import LLMStructureProposal
from src.llm.semantics import build_surveillance_semantics_summary
from src.llm.summary import build_prompt_safe_series_summary


def test_llm_prompts_exclude_banned_terms() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    llm_config = load_llm_config(repo_root / "configs" / "llm_v0.yaml")
    summary = build_prompt_safe_series_summary(
        series_name="Overall",
        y_train=[0.1, 0.2, 0.3],
        y_val=[0.2, 0.1],
        structure_frequency_path=repo_root / "artifacts_multiseed_age_robustness_observation" / "multiseed_discovery_structure_frequency.csv",
    )
    semantics = build_surveillance_semantics_summary().to_dict()
    proposer_prompt = build_proposer_prompt(summary, semantics, llm_config)
    critic_prompt = build_critic_prompt(
        summary,
        semantics,
        [LLMStructureProposal("SEIR", False, "I", 0, "", "")],
        llm_config,
    )
    for term in llm_config.banned_prompt_terms:
        assert term.lower() not in proposer_prompt.lower()
        assert term.lower() not in critic_prompt.lower()
