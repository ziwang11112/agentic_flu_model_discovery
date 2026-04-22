from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.discovery.rules import StructureSpec, validate_structure
from src.llm.schema import LLMStructureProposal, proposal_to_structure_spec


CHAIN_NEIGHBORS = {
    "SIR": ("SEIR",),
    "SEIR": ("SIR", "SEIRS"),
    "SEIRS": ("SEIR",),
}


def _make_proposal(
    structure_name: str,
    fractional: bool,
    observation_map: str,
    delay_weeks: int,
    rationale: str,
    expected_failure_mode: str,
) -> LLMStructureProposal:
    return LLMStructureProposal(
        structure_name=structure_name,
        fractional=fractional,
        observation_map=observation_map,
        delay_weeks=delay_weeks,
        rationale=rationale,
        expected_failure_mode=expected_failure_mode,
    )


def _normalize_observation_for_structure(
    structure_name: str,
    observation_map: str,
    delay_weeks: int,
) -> tuple[str, int]:
    if structure_name != "SEIHR" and observation_map in {"H", "I+H"}:
        return "delayed_I", max(1, delay_weeks or 1)
    if observation_map != "delayed_I":
        return observation_map, 0
    return observation_map, max(1, min(int(delay_weeks), 3))


def is_legal_small_edit(base_spec: StructureSpec, candidate_spec: StructureSpec) -> bool:
    if base_spec.spec_key == candidate_spec.spec_key:
        return True

    changes = 0
    if base_spec.fractional != candidate_spec.fractional:
        changes += 1

    structure_changed = base_spec.structure_name != candidate_spec.structure_name
    if structure_changed:
        if base_spec.structure_name in CHAIN_NEIGHBORS and candidate_spec.structure_name in CHAIN_NEIGHBORS[base_spec.structure_name]:
            changes += 1
        elif "SEIHR" in {base_spec.structure_name, candidate_spec.structure_name}:
            changes += 1
        else:
            return False

    observation_changed = base_spec.observation_map != candidate_spec.observation_map
    if observation_changed:
        allowed_pairs = {
            ("I", "delayed_I"),
            ("delayed_I", "I"),
            ("I", "H"),
            ("I", "I+H"),
            ("delayed_I", "H"),
            ("delayed_I", "I+H"),
            ("H", "I"),
            ("H", "delayed_I"),
            ("I+H", "I"),
            ("I+H", "delayed_I"),
        }
        if (base_spec.observation_map, candidate_spec.observation_map) not in allowed_pairs:
            return False
        changes += 1

    if base_spec.observation_map == "delayed_I" and candidate_spec.observation_map == "delayed_I":
        if abs(int(base_spec.delay_weeks) - int(candidate_spec.delay_weeks)) > 1:
            return False
        if base_spec.delay_weeks != candidate_spec.delay_weeks:
            changes += 1
    elif base_spec.delay_weeks != candidate_spec.delay_weeks:
        if base_spec.observation_map != "delayed_I" or candidate_spec.observation_map != "delayed_I":
            if abs(int(base_spec.delay_weeks) - int(candidate_spec.delay_weeks)) > 1:
                return False

    return changes <= 2


def build_refinement_proposals(
    base_spec: StructureSpec,
    series_name: str,
    max_candidates: int,
    analyst_feedback: dict[str, Any] | None = None,
) -> list[LLMStructureProposal]:
    del series_name
    analyst_feedback = analyst_feedback or {}
    instruction = str(analyst_feedback.get("proposer_instruction", "")).lower()
    constraints = " ".join(str(item).lower() for item in analyst_feedback.get("next_round_constraints", []))

    candidates: list[LLMStructureProposal] = [
        _make_proposal(
            base_spec.structure_name,
            base_spec.fractional,
            base_spec.observation_map,
            base_spec.delay_weeks,
            "Carry forward the previous best structure as the local anchor.",
            "May fail to improve if the previous round already saturated the local neighborhood.",
        )
    ]

    candidates.append(
        _make_proposal(
            base_spec.structure_name,
            not base_spec.fractional,
            base_spec.observation_map,
            base_spec.delay_weeks,
            "Toggle fractional memory as a bounded one-step refinement.",
            "May overfit if fractional memory is unnecessary.",
        )
    )

    if base_spec.observation_map == "I":
        candidates.append(
            _make_proposal(
                base_spec.structure_name,
                base_spec.fractional,
                "delayed_I",
                1,
                "Switch from direct infectious observation to a one-week delayed observation.",
                "May add unnecessary lag if admissions track incidence closely.",
            )
        )
    elif base_spec.observation_map == "delayed_I":
        candidates.append(
            _make_proposal(
                base_spec.structure_name,
                base_spec.fractional,
                "I",
                0,
                "Drop delayed observation and test direct infectious observation.",
                "May miss hospitalization reporting lag.",
            )
        )
        for delta in (-1, 1):
            next_delay = int(base_spec.delay_weeks) + delta
            if 1 <= next_delay <= 3:
                candidates.append(
                    _make_proposal(
                        base_spec.structure_name,
                        base_spec.fractional,
                        "delayed_I",
                        next_delay,
                        "Adjust delayed_I by one week as a bounded temporal refinement.",
                        "May move the observation lag away from the effective admission timing.",
                    )
                )
    elif base_spec.observation_map in {"H", "I+H"}:
        candidates.append(
            _make_proposal(
                base_spec.structure_name,
                base_spec.fractional,
                "delayed_I",
                1,
                "Drop explicit hospitalization observation in favor of delayed infectious observation.",
                "May lose explicit hospitalization semantics.",
            )
        )

    if base_spec.structure_name in CHAIN_NEIGHBORS:
        for structure_name in CHAIN_NEIGHBORS[base_spec.structure_name]:
            observation_map, delay_weeks = _normalize_observation_for_structure(
                structure_name,
                base_spec.observation_map,
                int(base_spec.delay_weeks),
            )
            candidates.append(
                _make_proposal(
                    structure_name,
                    base_spec.fractional,
                    observation_map,
                    delay_weeks,
                    "Move one step along the SIR/SEIR/SEIRS chain while preserving the current observation hypothesis.",
                    "May trade structural fit for parsimony or vice versa.",
                )
            )

    if base_spec.structure_name != "SEIHR":
        seirh_observation = "H" if "delay" in instruction or "hospital" in constraints or "h" in instruction.split() else "I"
        candidates.append(
            _make_proposal(
                "SEIHR",
                base_spec.fractional,
                seirh_observation,
                0,
                "Try an explicit hospitalization compartment as a bounded structural edit.",
                "May be weakly identifiable in short single-season data.",
            )
        )
    else:
        fallback_structure = "SEIR" if base_spec.observation_map in {"H", "I+H"} else "SEIRS"
        fallback_obs, fallback_delay = _normalize_observation_for_structure(fallback_structure, "delayed_I", 1)
        candidates.append(
            _make_proposal(
                fallback_structure,
                base_spec.fractional,
                fallback_obs,
                fallback_delay,
                "Drop the H compartment if explicit hospitalization observation appears unstable.",
                "May oversimplify genuine hospitalization dynamics.",
            )
        )

    deduped: dict[str, LLMStructureProposal] = {}
    for proposal in candidates:
        spec = proposal_to_structure_spec(proposal)
        if not validate_structure(spec).valid:
            continue
        if not is_legal_small_edit(base_spec, spec):
            continue
        deduped.setdefault(spec.spec_key, proposal)

    ordered = list(deduped.values())
    if "delay" in instruction or "delayed" in instruction:
        ordered.sort(key=lambda proposal: 0 if proposal.observation_map == "delayed_I" else 1)
    elif "simpler" in instruction or "drop" in constraints:
        ordered.sort(key=lambda proposal: (proposal.structure_name == "SEIHR", proposal.fractional))

    return ordered[:max_candidates]
