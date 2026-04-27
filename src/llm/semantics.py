from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SurveillanceSemanticsSummary:
    target_semantics: str
    recommended_observation_maps: list[str]
    mechanistic_note: str
    risk_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_surveillance_semantics_summary() -> SurveillanceSemanticsSummary:
    return SurveillanceSemanticsSummary(
        target_semantics="hospitalization_rate",
        recommended_observation_maps=["delayed_I", "H", "I+H"],
        mechanistic_note="Hospital admissions may lag the latent I-state proxy, so delayed_I is a plausible observation structure.",
        risk_note="An explicit H compartment may be weakly identifiable in short single-season series.",
    )
