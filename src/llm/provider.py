from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from openai import OpenAI

from src.discovery.rules import StructureSpec
from src.llm.config import LLMConfig
from src.llm.refinement import build_refinement_proposals


@dataclass(frozen=True)
class ProviderResponse:
    payload: dict[str, Any]
    raw_response: dict[str, Any]
    raw_response_text: str
    attempt_count: int
    provider: str
    provider_is_mock: bool
    scientific_claim_allowed: bool

    def to_record(self) -> dict[str, Any]:
        return {
            "payload": self.payload,
            "raw_response": self.raw_response,
            "raw_response_text": self.raw_response_text,
            "attempt_count": self.attempt_count,
            "provider": self.provider,
            "provider_is_mock": self.provider_is_mock,
            "scientific_claim_allowed": self.scientific_claim_allowed,
        }


class JSONProvider(Protocol):
    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ProviderResponse: ...


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_repo_env() -> None:
    env_path = _repo_root() / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


class MockLLMProvider:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @staticmethod
    def _extract_series_name(prompt: str) -> str:
        match = re.search(r'"series_name":\s*"([^"]+)"', prompt)
        if match is None:
            raise ValueError("series_name_missing_from_prompt")
        return match.group(1)

    def _proposal_payload(self, series_name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        round_id = int(context.get("round_id", 1))
        library = {
            "Overall": [
                {"structure_name": "SIR", "fractional": False, "observation_map": "I", "delay_weeks": 0},
                {"structure_name": "SEIR", "fractional": False, "observation_map": "delayed_I", "delay_weeks": 1},
            ],
            "0-4 yr": [
                {"structure_name": "SEIRS", "fractional": False, "observation_map": "delayed_I", "delay_weeks": 2},
                {"structure_name": "SEIRS", "fractional": False, "observation_map": "I", "delay_weeks": 0},
            ],
            "5-17 yr": [
                {"structure_name": "SEIRS", "fractional": False, "observation_map": "delayed_I", "delay_weeks": 2},
                {"structure_name": "SEIR", "fractional": False, "observation_map": "I", "delay_weeks": 0},
            ],
            "18-49 yr": [
                {"structure_name": "SIR", "fractional": False, "observation_map": "I", "delay_weeks": 0},
                {"structure_name": "SEIR", "fractional": False, "observation_map": "delayed_I", "delay_weeks": 1},
            ],
            "50-64 yr": [
                {"structure_name": "SEIR", "fractional": False, "observation_map": "delayed_I", "delay_weeks": 1},
                {"structure_name": "SIR", "fractional": False, "observation_map": "I", "delay_weeks": 0},
            ],
            ">= 65 yr": [
                {"structure_name": "SEIRS", "fractional": True, "observation_map": "delayed_I", "delay_weeks": 2},
                {"structure_name": "SEIRS", "fractional": True, "observation_map": "I", "delay_weeks": 0},
            ],
        }
        if round_id == 1 or not context.get("previous_best_spec"):
            proposal_records = library.get(series_name, library["Overall"])[: self.config.max_candidate_specs]
        else:
            previous_best = context["previous_best_spec"]
            base_spec = StructureSpec(
                structure_name=str(previous_best["structure_name"]),
                fractional=bool(previous_best["fractional"]),
                observation_map=str(previous_best["observation_map"]),
                delay_weeks=int(previous_best.get("delay_weeks", 0)),
            )
            proposal_records = [
                {
                    "structure_name": proposal.structure_name,
                    "fractional": proposal.fractional,
                    "observation_map": proposal.observation_map,
                    "delay_weeks": proposal.delay_weeks,
                    "rationale": proposal.rationale,
                    "expected_failure_mode": proposal.expected_failure_mode,
                }
                for proposal in build_refinement_proposals(
                    base_spec=base_spec,
                    series_name=series_name,
                    max_candidates=self.config.max_candidate_specs,
                    analyst_feedback=context.get("analyst_feedback"),
                )
            ]

        proposals = []
        for record in proposal_records:
            proposals.append(
                {
                    **record,
                    "rationale": record.get("rationale", "Mock provider engineering smoke-test proposal."),
                    "expected_failure_mode": record.get(
                        "expected_failure_mode",
                        "May underperform validation or rolling stability.",
                    ),
                }
            )
        return {"series_name": series_name, "proposals": proposals}

    def _critic_payload(self, series_name: str, prompt: str) -> dict[str, Any]:
        proposal_count = len(re.findall(r'"structure_name":', prompt))
        accepted = []
        for index in range(proposal_count):
            accepted.append(
                {
                    "proposal_index": index,
                    "priority": "high" if index == 0 else "medium",
                    "reason": f"Mock critic review for {series_name}.",
                }
            )
        return {"series_name": series_name, "accepted": accepted, "rejected": [], "suggested_edits": []}

    def _analyst_payload(self, series_name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        previous_best = context.get("previous_best_spec", {})
        leaderboard = context.get("round_leaderboard", [])
        best_row = leaderboard[0] if leaderboard else {}

        failure_modes: list[str] = []
        constraints: list[str] = []
        instruction = "Refine the previous best with one-step edits and preserve parsimony."

        if best_row:
            val_mae = float(best_row.get("val_mae", 0.0))
            rolling_mae = float(best_row.get("rolling_val_mean_mae", 0.0))
            if rolling_mae > val_mae + 0.02:
                failure_modes.append("rolling_instability")
                constraints.append("prefer simpler or more delay-aware edits")
                instruction = "Try local edits that improve rolling stability without inventing new structures."
            if float(best_row.get("complexity_penalty", 0.0)) > 0.15:
                failure_modes.append("excess_complexity")
                constraints.append("drop unnecessary complexity")

        if previous_best.get("observation_map") in {"H", "I+H"}:
            failure_modes.append("h_identifiability_risk")
            constraints.append("drop H if weakly identifiable")
            instruction = "Prefer delayed_I or I over explicit H if rolling evidence is weak."
        elif series_name in {"0-4 yr", "5-17 yr", ">= 65 yr"}:
            constraints.append("consider delayed_I around the current best")
            instruction = "Refine around the current best and keep delayed observation on the table."

        if not failure_modes:
            failure_modes.append("local_search")

        return {
            "series_name": series_name,
            "observed_failure_modes": failure_modes,
            "next_round_constraints": constraints,
            "proposer_instruction": instruction,
        }

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        del system_prompt
        context = context or {}
        series_name = context.get("series_name") or self._extract_series_name(prompt)
        lowered = prompt.lower()
        role = str(context.get("role", "")).lower()
        if role == "analyst" or "you are a result analyst" in lowered:
            payload = self._analyst_payload(series_name, context)
        elif role == "critic" or "critic for epidemic model structure proposals" in lowered:
            payload = self._critic_payload(series_name, prompt)
        else:
            payload = self._proposal_payload(series_name, context)
        raw_text = json.dumps(payload, sort_keys=True)
        return ProviderResponse(
            payload=payload,
            raw_response={"mock_payload": payload},
            raw_response_text=raw_text,
            attempt_count=1,
            provider="mock",
            provider_is_mock=True,
            scientific_claim_allowed=False,
        )


class OpenAIJSONProvider:
    def __init__(self, config: LLMConfig, client: Any | None = None) -> None:
        self.config = config
        _load_repo_env()
        if client is None:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is required for provider=openai")
            client = OpenAI(api_key=api_key)
        self.client = client
        self.model = os.getenv("OPENAI_MODEL", config.model)
        self.max_retries = 2

    @staticmethod
    def _extract_series_name(prompt: str) -> str:
        match = re.search(r'"series_name":\s*"([^"]+)"', prompt)
        if match is None:
            raise ValueError("series_name_missing_from_prompt")
        return match.group(1)

    def _schema_for_role(self, role: str) -> dict[str, Any]:
        if role == "critic":
            return {
                "name": "critic_review",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "series_name": {"type": "string"},
                        "accepted": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "proposal_index": {"type": "integer"},
                                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                                    "reason": {"type": "string"},
                                },
                                "required": ["proposal_index", "priority", "reason"],
                            },
                        },
                        "rejected": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "proposal_index": {"type": "integer"},
                                    "reason": {"type": "string"},
                                },
                                "required": ["proposal_index", "reason"],
                            },
                        },
                        "suggested_edits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "from_proposal_index": {"type": "integer"},
                                    "edit": {"type": "string"},
                                },
                                "required": ["from_proposal_index", "edit"],
                            },
                        },
                    },
                    "required": ["series_name", "accepted", "rejected", "suggested_edits"],
                },
            }
        if role == "analyst":
            return {
                "name": "analyst_feedback",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "series_name": {"type": "string"},
                        "observed_failure_modes": {"type": "array", "items": {"type": "string"}},
                        "next_round_constraints": {"type": "array", "items": {"type": "string"}},
                        "proposer_instruction": {"type": "string"},
                    },
                    "required": [
                        "series_name",
                        "observed_failure_modes",
                        "next_round_constraints",
                        "proposer_instruction",
                    ],
                },
            }
        return {
            "name": "structure_proposals",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "series_name": {"type": "string"},
                    "proposals": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "structure_name": {"type": "string", "enum": list(self.config.allowed_structures)},
                                "fractional": {"type": "boolean"},
                                "observation_map": {"type": "string", "enum": list(self.config.allowed_observation_maps)},
                                "delay_weeks": {"type": "integer", "enum": list(self.config.allowed_delay_weeks)},
                                "rationale": {"type": "string"},
                                "expected_failure_mode": {"type": "string"},
                            },
                            "required": [
                                "structure_name",
                                "fractional",
                                "observation_map",
                                "delay_weeks",
                                "rationale",
                                "expected_failure_mode",
                            ],
                        },
                    },
                },
                "required": ["series_name", "proposals"],
            },
        }

    @staticmethod
    def _messages(prompt: str, system_prompt: str | None = None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def _response_text(response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        raise ValueError("openai_response_missing_output_text")

    def _request_once(self, prompt: str, system_prompt: str | None, schema: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        response = self.client.responses.create(
            model=self.model,
            input=self._messages(prompt, system_prompt),
            temperature=0,
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema["name"],
                    "strict": True,
                    "schema": schema["schema"],
                }
            },
        )
        raw_response = response.model_dump() if hasattr(response, "model_dump") else {"repr": repr(response)}
        return self._response_text(response), raw_response

    @staticmethod
    def _repair_prompt(previous_raw_text: str, role: str) -> str:
        return (
            "Return strict JSON only. Your previous response was invalid or unparsable JSON.\n"
            f"Role: {role}\n"
            "Repair the response so that it is valid JSON matching the required schema.\n"
            "Do not include markdown, prose, or code fences.\n"
            "Previous response:\n"
            f"{previous_raw_text}"
        )

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        context = context or {}
        role = str(context.get("role", "proposer")).lower()
        schema = self._schema_for_role(role)
        prompt_to_send = prompt
        raw_attempts: list[dict[str, Any]] = []
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 2):
            raw_text, raw_response = self._request_once(prompt_to_send, system_prompt, schema)
            raw_attempts.append({"attempt": attempt, "raw_response": raw_response, "raw_response_text": raw_text})
            try:
                payload = json.loads(raw_text)
                return ProviderResponse(
                    payload=payload,
                    raw_response={"attempts": raw_attempts},
                    raw_response_text=raw_text,
                    attempt_count=attempt,
                    provider="openai",
                    provider_is_mock=False,
                    scientific_claim_allowed=True,
                )
            except json.JSONDecodeError as exc:
                last_error = exc
                if attempt > self.max_retries:
                    break
                prompt_to_send = self._repair_prompt(raw_text, role)

        raise ValueError(
            f"openai_provider_invalid_json_after_{self.max_retries + 1}_attempts:"
            f" {last_error}"
        )


def build_provider(config: LLMConfig) -> JSONProvider:
    if config.provider == "mock":
        return MockLLMProvider(config)
    if config.provider == "openai":
        return OpenAIJSONProvider(config)
    raise NotImplementedError(f"Unsupported LLM provider: {config.provider}")
