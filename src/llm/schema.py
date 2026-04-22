from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.discovery.rules import StructureSpec, validate_structure


ALLOWED_STRUCTURES = {"SIR", "SEIR", "SEIRS", "SEIHR", "SEIAR"}
ALLOWED_OBSERVATION_MAPS = {"I", "H", "I+H", "delayed_I"}
ALLOWED_DELAY_WEEKS = {0, 1, 2, 3}


@dataclass(frozen=True)
class LLMStructureProposal:
    structure_name: str
    fractional: bool
    observation_map: str
    delay_weeks: int = 0
    rationale: str = ""
    expected_failure_mode: str = ""


@dataclass(frozen=True)
class ProposalValidationResult:
    proposal: LLMStructureProposal | None
    schema_valid: bool
    hard_valid: bool
    invalid_reason: str | None
    structure_spec: StructureSpec | None


def parse_structure_proposal(payload: dict[str, Any]) -> LLMStructureProposal:
    structure_name = str(payload["structure_name"])
    observation_map = str(payload["observation_map"])
    delay_weeks = int(payload.get("delay_weeks", 0))
    fractional = bool(payload["fractional"])

    if structure_name not in ALLOWED_STRUCTURES:
        raise ValueError(f"invalid_structure_name:{structure_name}")
    if observation_map not in ALLOWED_OBSERVATION_MAPS:
        raise ValueError(f"invalid_observation_map:{observation_map}")
    if delay_weeks not in ALLOWED_DELAY_WEEKS:
        raise ValueError(f"invalid_delay_weeks:{delay_weeks}")
    if observation_map != "delayed_I" and delay_weeks != 0:
        raise ValueError("non_delayed_observation_requires_zero_delay")

    return LLMStructureProposal(
        structure_name=structure_name,
        fractional=fractional,
        observation_map=observation_map,
        delay_weeks=delay_weeks,
        rationale=str(payload.get("rationale", "")),
        expected_failure_mode=str(payload.get("expected_failure_mode", "")),
    )


def proposal_to_structure_spec(proposal: LLMStructureProposal) -> StructureSpec:
    return StructureSpec(
        structure_name=proposal.structure_name,
        fractional=proposal.fractional,
        observation_map=proposal.observation_map,
        delay_weeks=int(proposal.delay_weeks),
    )


def validate_llm_proposal_payload(payload: dict[str, Any]) -> ProposalValidationResult:
    try:
        proposal = parse_structure_proposal(payload)
    except Exception as exc:
        return ProposalValidationResult(
            proposal=None,
            schema_valid=False,
            hard_valid=False,
            invalid_reason=str(exc),
            structure_spec=None,
        )

    spec = proposal_to_structure_spec(proposal)
    validation = validate_structure(spec)
    return ProposalValidationResult(
        proposal=proposal,
        schema_valid=True,
        hard_valid=bool(validation.valid),
        invalid_reason=None if validation.valid else validation.reason,
        structure_spec=spec if validation.valid else None,
    )


def proposal_to_dict(proposal: LLMStructureProposal) -> dict[str, Any]:
    return asdict(proposal)
