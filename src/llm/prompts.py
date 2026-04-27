from __future__ import annotations

import json
from typing import Any

from src.llm.config import LLMConfig
from src.llm.schema import proposal_to_dict, LLMStructureProposal
from src.llm.summary import PromptSafeSeriesSummary


def assert_no_banned_terms(text: str, banned_terms: tuple[str, ...]) -> None:
    lowered = text.lower()
    for term in banned_terms:
        if term.lower() in lowered:
            raise ValueError(f"prompt_contains_banned_term:{term}")


def _safe_json(payload: dict[str, Any], banned_terms: tuple[str, ...]) -> str:
    text = json.dumps(payload, indent=2, sort_keys=True)
    assert_no_banned_terms(text, banned_terms)
    return text


def build_proposer_prompt(
    series_summary: PromptSafeSeriesSummary,
    semantics_summary: dict[str, Any],
    llm_config: LLMConfig,
    previous_feedback: dict[str, Any] | None = None,
) -> str:
    prompt = f"""You are a public-health time-series model-template proposer.

This task uses aggregate weekly hospitalization-rate time series only. It does
not involve lab work, pathogen engineering, transmission optimization,
individual-level data, clinical advice, or intervention guidance.

You must propose candidate compartment-template specifications for forecasting
aggregate weekly influenza hospitalization rates.

You do not fit parameters.
You do not write Python code.
You do not use test metrics.
You only propose JSON model specifications under the allowed DSL.

Allowed structures:
{", ".join(llm_config.allowed_structures)}

Allowed observation maps:
{", ".join(llm_config.allowed_observation_maps)}

Rules:
- obs=H requires SEIHR
- obs=I+H requires SEIHR
- obs=delayed_I requires delay_weeks in {{1,2,3}}
- non-delayed observations must use delay_weeks=0
- keep proposals compatible with the DSL and parsimonious
- return strict JSON only

Series summary:
{_safe_json(series_summary.to_prompt_dict(), llm_config.banned_prompt_terms)}

Surveillance semantics:
{_safe_json(semantics_summary, llm_config.banned_prompt_terms)}

Previous feedback:
{_safe_json(previous_feedback or {}, llm_config.banned_prompt_terms)}

Return:
{{
  "series_name": "...",
  "proposals": [
    {{
      "structure_name": "...",
      "fractional": false,
      "observation_map": "...",
      "delay_weeks": 0,
      "rationale": "...",
      "expected_failure_mode": "..."
    }}
  ]
}}
"""
    assert_no_banned_terms(prompt, llm_config.banned_prompt_terms)
    return prompt


def build_critic_prompt(
    series_summary: PromptSafeSeriesSummary,
    semantics_summary: dict[str, Any],
    proposals: list[LLMStructureProposal],
    llm_config: LLMConfig,
) -> str:
    payload = {
        "series_name": series_summary.series_name,
        "proposals": [proposal_to_dict(proposal) for proposal in proposals],
    }
    prompt = f"""You are a critic for public-health time-series model-template proposals.

This task uses aggregate weekly hospitalization-rate time series only. It does
not involve lab work, pathogen engineering, transmission optimization,
individual-level data, clinical advice, or intervention guidance.

Your job is to review candidate templates before numerical fitting.

Do not use test metrics.
Do not choose final winners.
Do not invent new structure types.
Do not write code.

Check:
- observation-target alignment
- over-complexity
- identifiability risk
- whether delayed_I is more plausible than H for short single-season data
- whether fractional memory is justified or likely overfitting

Series summary:
{_safe_json(series_summary.to_prompt_dict(), llm_config.banned_prompt_terms)}

Surveillance semantics:
{_safe_json(semantics_summary, llm_config.banned_prompt_terms)}

Candidate proposals:
{_safe_json(payload, llm_config.banned_prompt_terms)}

Return strict JSON:
{{
  "accepted": [
    {{
      "proposal_index": 0,
      "priority": "high",
      "reason": "..."
    }}
  ],
  "rejected": [
    {{
      "proposal_index": 1,
      "reason": "..."
    }}
  ],
  "suggested_edits": [
    {{
      "from_proposal_index": 2,
      "edit": "..."
    }}
  ]
}}
"""
    assert_no_banned_terms(prompt, llm_config.banned_prompt_terms)
    return prompt
