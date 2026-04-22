from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from src.utils.io import ensure_dir


@dataclass(frozen=True)
class RoundTraceRecord:
    round_id: int
    previous_best_spec: str | None
    previous_best_score: float | None
    analyst_feedback_summary: str
    new_specs: list[str]
    round_best_spec: str | None
    round_best_score: float | None
    score_improvement: float | None
    early_stop: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_refinement_trace_jsonl(records: list[RoundTraceRecord], path: Path) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")


def write_refinement_trace_markdown(records: list[RoundTraceRecord], path: Path) -> None:
    lines = ["# LLM V1 Refinement Trace", ""]
    for record in records:
        lines.extend(
            [
                f"## Round {record.round_id}",
                "",
                f"- previous_best_spec: `{record.previous_best_spec}`",
                f"- previous_best_score: `{record.previous_best_score}`",
                f"- analyst_feedback_summary: {record.analyst_feedback_summary}",
                f"- new_specs: `{'; '.join(record.new_specs)}`",
                f"- round_best_spec: `{record.round_best_spec}`",
                f"- round_best_score: `{record.round_best_score}`",
                f"- score_improvement: `{record.score_improvement}`",
                f"- early_stop: `{record.early_stop}`",
                "",
            ]
        )
    ensure_dir(path.parent)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
