from __future__ import annotations

from src.llm.schema import parse_structure_proposal, validate_llm_proposal_payload


def test_llm_schema_accepts_valid_proposal() -> None:
    proposal = parse_structure_proposal(
        {
            "structure_name": "SEIRS",
            "fractional": False,
            "observation_map": "delayed_I",
            "delay_weeks": 2,
        }
    )
    assert proposal.structure_name == "SEIRS"
    assert proposal.delay_weeks == 2


def test_llm_schema_rejects_invalid_structure_name() -> None:
    try:
        parse_structure_proposal(
            {
                "structure_name": "SEIXX",
                "fractional": False,
                "observation_map": "I",
                "delay_weeks": 0,
            }
        )
    except ValueError as exc:
        assert "invalid_structure_name" in str(exc)
    else:
        raise AssertionError("Expected invalid structure name to raise.")


def test_llm_schema_rejects_invalid_observation_map() -> None:
    try:
        parse_structure_proposal(
            {
                "structure_name": "SEIR",
                "fractional": False,
                "observation_map": "X",
                "delay_weeks": 0,
            }
        )
    except ValueError as exc:
        assert "invalid_observation_map" in str(exc)
    else:
        raise AssertionError("Expected invalid observation map to raise.")


def test_llm_schema_rejects_invalid_delay() -> None:
    try:
        parse_structure_proposal(
            {
                "structure_name": "SEIR",
                "fractional": False,
                "observation_map": "delayed_I",
                "delay_weeks": 5,
            }
        )
    except ValueError as exc:
        assert "invalid_delay_weeks" in str(exc)
    else:
        raise AssertionError("Expected invalid delay to raise.")


def test_hard_validator_rejects_h_without_seihr() -> None:
    result = validate_llm_proposal_payload(
        {
            "structure_name": "SEIR",
            "fractional": False,
            "observation_map": "H",
            "delay_weeks": 0,
        }
    )
    assert result.schema_valid is True
    assert result.hard_valid is False
    assert result.invalid_reason == "observation_map_requires_h"
