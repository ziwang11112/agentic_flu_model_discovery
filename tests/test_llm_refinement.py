from __future__ import annotations

from src.discovery.rules import StructureSpec, validate_structure
from src.llm.refinement import build_refinement_proposals, is_legal_small_edit
from src.llm.schema import proposal_to_structure_spec


def test_small_edit_refinements_are_legal_and_bounded() -> None:
    base_spec = StructureSpec("SEIRS", fractional=False, observation_map="delayed_I", delay_weeks=2)
    proposals = build_refinement_proposals(
        base_spec=base_spec,
        series_name="5-17 yr",
        max_candidates=8,
        analyst_feedback={"proposer_instruction": "Prefer delayed_I or simpler edits.", "next_round_constraints": []},
    )
    assert proposals
    for proposal in proposals:
        spec = proposal_to_structure_spec(proposal)
        assert is_legal_small_edit(base_spec, spec)
        assert validate_structure(spec).valid
        if base_spec.observation_map == "delayed_I" and spec.observation_map == "delayed_I":
            assert abs(spec.delay_weeks - base_spec.delay_weeks) <= 1
