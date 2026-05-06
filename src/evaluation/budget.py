from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


DEFAULT_BUDGETS = (4, 8, 12, 16)
ORDER_COLUMNS = ("evaluation_order", "candidate_order", "eval_order", "order", "candidate_index")
BUDGET_COMPARISON_COLUMNS = [
    "series_name",
    "budget_k",
    "llm_best_score_at_k",
    "nonllm_best_score_at_k",
    "llm_better_at_k",
    "llm_order_available",
    "nonllm_order_available",
    "order_matched",
    "efficiency_claim_allowed",
    "note",
]


@dataclass(frozen=True)
class CandidateSequence:
    series_name: str
    frame: pd.DataFrame
    order_available: bool
    score_available: bool
    comparable_order: bool
    note: str
    source_paths: tuple[str, ...]

    @property
    def count(self) -> int:
        return int(len(self.frame))


def _slug_to_series_name(slug: str) -> str:
    mapping = {
        "overall": "Overall",
        "0_4_yr": "0-4 yr",
        "5_17_yr": "5-17 yr",
        "18_49_yr": "18-49 yr",
        "50_64_yr": "50-64 yr",
        "ge__65_yr": ">= 65 yr",
    }
    return mapping.get(slug, slug)


def _as_bool_or_na(value: bool | None) -> object:
    return pd.NA if value is None else bool(value)


def _score_column_available(frame: pd.DataFrame) -> bool:
    if "score" not in frame.columns:
        return False
    scores = pd.to_numeric(frame["score"], errors="coerce")
    return bool(scores.notna().all())


def _explicit_order_column(frame: pd.DataFrame) -> str | None:
    for column in ORDER_COLUMNS:
        if column in frame.columns:
            return column
    return None


def _prepare_ordered_frame(frame: pd.DataFrame, order_columns: list[str]) -> pd.DataFrame:
    ordered = frame.copy()
    ordered["score"] = pd.to_numeric(ordered["score"], errors="coerce")
    ordered = ordered.sort_values(order_columns, kind="mergesort").reset_index(drop=True)
    ordered["evaluation_index"] = range(1, len(ordered) + 1)
    return ordered


def _llm_series_from_path(path: Path) -> str:
    return _slug_to_series_name(path.parents[2].name)


def _nonllm_series_from_path(path: Path) -> str:
    return _slug_to_series_name(path.parents[1].name)


def _build_llm_sequence(series_name: str, frames: list[pd.DataFrame], paths: list[Path]) -> CandidateSequence:
    if not frames:
        return CandidateSequence(series_name, pd.DataFrame(), False, False, False, "No LLM leaderboards found.", ())

    combined = pd.concat(frames, ignore_index=True)
    score_available = _score_column_available(combined)
    if {"round_id", "proposal_id"}.issubset(combined.columns):
        ordered = _prepare_ordered_frame(combined, ["round_id", "proposal_id", "spec_key"])
        return CandidateSequence(
            series_name=series_name,
            frame=ordered,
            order_available=score_available,
            score_available=score_available,
            comparable_order=score_available,
            note="LLM order reconstructed from round_id and proposal_id.",
            source_paths=tuple(str(path) for path in paths),
        )

    explicit_order = _explicit_order_column(combined)
    if explicit_order is not None and score_available:
        ordered = _prepare_ordered_frame(combined, [explicit_order])
        return CandidateSequence(
            series_name=series_name,
            frame=ordered,
            order_available=True,
            score_available=True,
            comparable_order=True,
            note=f"LLM order read from {explicit_order}.",
            source_paths=tuple(str(path) for path in paths),
        )

    return CandidateSequence(
        series_name=series_name,
        frame=combined,
        order_available=False,
        score_available=score_available,
        comparable_order=False,
        note="LLM candidate order is unavailable or score column is missing.",
        source_paths=tuple(str(path) for path in paths),
    )


def load_llm_candidate_sequences(llm_root: Path) -> dict[str, CandidateSequence]:
    """Load evaluated LLM candidate sequences by series from V1 round leaderboards."""
    frames_by_series: dict[str, list[pd.DataFrame]] = {}
    paths_by_series: dict[str, list[Path]] = {}
    for path in sorted(llm_root.glob("*/rounds/round_*/llm_leaderboard.csv")):
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        series_name = str(frame["series_name"].iloc[0]) if "series_name" in frame.columns else _llm_series_from_path(path)
        frames_by_series.setdefault(series_name, []).append(frame)
        paths_by_series.setdefault(series_name, []).append(path)
    return {
        series_name: _build_llm_sequence(series_name, frames, paths_by_series[series_name])
        for series_name, frames in frames_by_series.items()
    }


def _build_nonllm_sequence(series_name: str, frames: list[pd.DataFrame], paths: list[Path]) -> CandidateSequence:
    if not frames:
        return CandidateSequence(series_name, pd.DataFrame(), False, False, False, "No non-LLM leaderboards found.", ())

    if len(frames) > 1:
        combined = pd.concat(frames, ignore_index=True)
        return CandidateSequence(
            series_name=series_name,
            frame=combined,
            order_available=bool(_explicit_order_column(combined)),
            score_available=_score_column_available(combined),
            comparable_order=False,
            note="Multiple non-LLM candidate sequences were found; a single order-matched sequence is unavailable.",
            source_paths=tuple(str(path) for path in paths),
        )

    frame = frames[0].copy()
    score_available = _score_column_available(frame)
    explicit_order = _explicit_order_column(frame)
    if explicit_order is None:
        return CandidateSequence(
            series_name=series_name,
            frame=frame,
            order_available=False,
            score_available=score_available,
            comparable_order=False,
            note="Non-LLM leaderboard lacks an explicit candidate evaluation-order column.",
            source_paths=(str(paths[0]),),
        )
    if not score_available:
        return CandidateSequence(
            series_name=series_name,
            frame=frame,
            order_available=False,
            score_available=False,
            comparable_order=False,
            note="Non-LLM leaderboard lacks a numeric score column.",
            source_paths=(str(paths[0]),),
        )
    ordered = _prepare_ordered_frame(frame, [explicit_order])
    return CandidateSequence(
        series_name=series_name,
        frame=ordered,
        order_available=True,
        score_available=True,
        comparable_order=True,
        note=f"Non-LLM order read from {explicit_order}.",
        source_paths=(str(paths[0]),),
    )


def load_nonllm_candidate_sequences(nonllm_root: Path) -> dict[str, CandidateSequence]:
    """Load non-LLM constrained discovery candidate sequences when order metadata exists."""
    frames_by_series: dict[str, list[pd.DataFrame]] = {}
    paths_by_series: dict[str, list[Path]] = {}
    for path in sorted(nonllm_root.glob("**/constrained_structure_discovery/leaderboard.csv")):
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        series_name = str(frame["series_name"].iloc[0]) if "series_name" in frame.columns else _nonllm_series_from_path(path)
        frames_by_series.setdefault(series_name, []).append(frame)
        paths_by_series.setdefault(series_name, []).append(path)
    return {
        series_name: _build_nonllm_sequence(series_name, frames, paths_by_series[series_name])
        for series_name, frames in frames_by_series.items()
    }


def _load_summary_counts(llm_root: Path) -> dict[str, dict[str, float]]:
    path = llm_root / "llm_v1_vs_v0_vs_nonllm_summary.csv"
    if not path.exists():
        return {}
    summary = pd.read_csv(path)
    counts: dict[str, dict[str, float]] = {}
    for _, row in summary.iterrows():
        series_name = str(row["series_name"])
        counts[series_name] = {
            "llm": float(row["v1_num_candidates_evaluated"])
            if "v1_num_candidates_evaluated" in row and pd.notna(row["v1_num_candidates_evaluated"])
            else float("nan"),
            "nonllm": float(row["nonllm_num_candidates_evaluated"])
            if "nonllm_num_candidates_evaluated" in row and pd.notna(row["nonllm_num_candidates_evaluated"])
            else float("nan"),
        }
    return counts


def _best_score_at_k(sequence: CandidateSequence | None, budget_k: int) -> float | None:
    if sequence is None or not sequence.order_available or not sequence.score_available:
        return None
    if sequence.count < budget_k:
        return None
    return float(sequence.frame.head(budget_k)["score"].min())


def _diagnostic_note(
    *,
    budget_k: int,
    llm_sequence: CandidateSequence | None,
    nonllm_sequence: CandidateSequence | None,
    llm_order_available: bool,
    nonllm_order_available: bool,
    order_matched: bool,
) -> str:
    if not llm_order_available:
        return "LLM candidate order unavailable; no candidate-efficiency claim is supported."
    if nonllm_sequence is None:
        return "Non-LLM candidate order unavailable; descriptive candidate counts only; no candidate-efficiency claim is supported."
    if not nonllm_order_available:
        return f"{nonllm_sequence.note} Descriptive candidate counts only; no candidate-efficiency claim is supported."
    if not order_matched:
        llm_count = 0 if llm_sequence is None else llm_sequence.count
        nonllm_count = nonllm_sequence.count
        return (
            f"Candidate order is available, but at least one side has fewer than K={budget_k} evaluated candidates "
            f"(LLM={llm_count}, non-LLM={nonllm_count}); no efficiency claim for this budget."
        )
    return "Candidate order and score are comparable at this K; row-level efficiency comparison is allowed."


def build_budget_matched_comparison(
    llm_root: Path,
    nonllm_root: Path,
    budgets: Iterable[int] = DEFAULT_BUDGETS,
) -> pd.DataFrame:
    """Build K-budget best-score comparisons only when order metadata is comparable."""
    llm_sequences = load_llm_candidate_sequences(llm_root)
    nonllm_sequences = load_nonllm_candidate_sequences(nonllm_root)
    summary_counts = _load_summary_counts(llm_root)
    series_names = sorted(set(llm_sequences) | set(nonllm_sequences) | set(summary_counts))
    rows: list[dict[str, Any]] = []

    for series_name in series_names:
        llm_sequence = llm_sequences.get(series_name)
        nonllm_sequence = nonllm_sequences.get(series_name)
        for budget_k in budgets:
            budget_k = int(budget_k)
            llm_order_available = bool(
                llm_sequence is not None
                and llm_sequence.order_available
                and llm_sequence.score_available
                and llm_sequence.comparable_order
            )
            nonllm_order_available = bool(
                nonllm_sequence is not None
                and nonllm_sequence.order_available
                and nonllm_sequence.score_available
                and nonllm_sequence.comparable_order
            )
            llm_best = _best_score_at_k(llm_sequence, budget_k)
            nonllm_best = _best_score_at_k(nonllm_sequence, budget_k)
            order_matched = bool(
                llm_order_available
                and nonllm_order_available
                and llm_best is not None
                and nonllm_best is not None
            )
            efficiency_claim_allowed = order_matched
            llm_better = None if llm_best is None or nonllm_best is None else bool(llm_best < nonllm_best)
            rows.append(
                {
                    "series_name": series_name,
                    "budget_k": budget_k,
                    "llm_best_score_at_k": llm_best,
                    "nonllm_best_score_at_k": nonllm_best,
                    "llm_better_at_k": _as_bool_or_na(llm_better),
                    "llm_order_available": llm_order_available,
                    "nonllm_order_available": nonllm_order_available,
                    "order_matched": order_matched,
                    "efficiency_claim_allowed": efficiency_claim_allowed,
                    "note": _diagnostic_note(
                        budget_k=budget_k,
                        llm_sequence=llm_sequence,
                        nonllm_sequence=nonllm_sequence,
                        llm_order_available=llm_order_available,
                        nonllm_order_available=nonllm_order_available,
                        order_matched=order_matched,
                    ),
                }
            )

    return pd.DataFrame(rows, columns=BUDGET_COMPARISON_COLUMNS).sort_values(
        ["series_name", "budget_k"]
    ).reset_index(drop=True)


def build_candidate_count_summary(llm_root: Path, nonllm_root: Path) -> pd.DataFrame:
    """Build descriptive candidate counts, using summaries when ordered leaderboards are absent."""
    llm_sequences = load_llm_candidate_sequences(llm_root)
    nonllm_sequences = load_nonllm_candidate_sequences(nonllm_root)
    summary_counts = _load_summary_counts(llm_root)
    series_names = sorted(set(llm_sequences) | set(nonllm_sequences) | set(summary_counts))
    rows: list[dict[str, Any]] = []
    for series_name in series_names:
        llm_count = llm_sequences[series_name].count if series_name in llm_sequences else summary_counts.get(series_name, {}).get("llm")
        nonllm_count = (
            nonllm_sequences[series_name].count
            if series_name in nonllm_sequences
            else summary_counts.get(series_name, {}).get("nonllm")
        )
        if llm_count is None or nonllm_count is None or pd.isna(llm_count) or pd.isna(nonllm_count):
            relation = "unknown"
        elif float(llm_count) < float(nonllm_count):
            relation = "fewer"
        elif float(llm_count) > float(nonllm_count):
            relation = "more"
        else:
            relation = "same"
        rows.append(
            {
                "series_name": series_name,
                "llm_num_candidates_evaluated": llm_count,
                "nonllm_num_candidates_evaluated": nonllm_count,
                "llm_vs_nonllm_candidate_count": relation,
            }
        )
    return pd.DataFrame(rows).sort_values("series_name").reset_index(drop=True)


def _format_float(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.3f}"


def _format_count(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    numeric = float(value)
    return str(int(numeric)) if numeric.is_integer() else f"{numeric:.1f}"


def build_budget_diagnostic_report(
    comparison: pd.DataFrame,
    candidate_counts: pd.DataFrame,
    *,
    selected_repeats_summary_path: Path | None = None,
) -> str:
    """Render a conservative markdown report for LLM-vs-nonLLM candidate budgets."""
    efficiency_allowed = bool(comparison["efficiency_claim_allowed"].any()) if not comparison.empty else False
    unmatched = comparison.loc[~comparison["efficiency_claim_allowed"]].copy()
    note_counts = Counter(unmatched["note"].astype(str).tolist()) if not unmatched.empty else Counter()
    fewer = int((candidate_counts["llm_vs_nonllm_candidate_count"] == "fewer").sum()) if not candidate_counts.empty else 0
    more = int((candidate_counts["llm_vs_nonllm_candidate_count"] == "more").sum()) if not candidate_counts.empty else 0
    same = int((candidate_counts["llm_vs_nonllm_candidate_count"] == "same").sum()) if not candidate_counts.empty else 0
    unknown = int((candidate_counts["llm_vs_nonllm_candidate_count"] == "unknown").sum()) if not candidate_counts.empty else 0

    lines = [
        "# LLM-vs-nonLLM Budget Diagnostic",
        "",
        "This diagnostic checks whether candidate-efficiency claims are supported under fixed candidate budgets `K in {4, 8, 12, 16}`.",
        "",
        "## Claim Status",
        "",
        f"- Candidate-efficiency claims allowed: `{'true' if efficiency_allowed else 'false'}`",
    ]
    if efficiency_allowed:
        allowed_rows = int(comparison["efficiency_claim_allowed"].sum())
        lines.append(f"- Order-matched rows available: `{allowed_rows}`")
    else:
        lines.append("- No candidate-efficiency claim is supported by these artifacts.")
        lines.append("- Reason: LLM and non-LLM candidate budgets/order are not matched with comparable evaluation order metadata.")

    lines.extend(
        [
            "",
            "## Descriptive Candidate Counts",
            "",
            f"- LLM evaluated fewer candidates than non-LLM in `{fewer}` series.",
            f"- LLM evaluated more candidates than non-LLM in `{more}` series.",
            f"- LLM evaluated the same number of candidates as non-LLM in `{same}` series.",
            f"- Candidate count relation is unknown in `{unknown}` series.",
            "",
            "| series_name | llm_candidates | nonllm_candidates | relation |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in candidate_counts.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["series_name"]),
                    _format_count(row["llm_num_candidates_evaluated"]),
                    _format_count(row["nonllm_num_candidates_evaluated"]),
                    str(row["llm_vs_nonllm_candidate_count"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Budget-Matched Rows",
            "",
            "| series_name | K | llm_best_score_at_k | nonllm_best_score_at_k | llm_better_at_k | order_matched | efficiency_claim_allowed |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in comparison.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["series_name"]),
                    str(int(row["budget_k"])),
                    _format_float(row["llm_best_score_at_k"]),
                    _format_float(row["nonllm_best_score_at_k"]),
                    "" if pd.isna(row["llm_better_at_k"]) else str(bool(row["llm_better_at_k"])),
                    str(bool(row["order_matched"])),
                    str(bool(row["efficiency_claim_allowed"])),
                ]
            )
            + " |"
        )

    if note_counts:
        lines.extend(["", "## Why Claims Are Blocked", ""])
        for note, count in sorted(note_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{count}` rows: {note}")

    if selected_repeats_summary_path is not None:
        lines.extend(
            [
                "",
                "## Selected Repeats",
                "",
                f"Selected-repeat summary supplied: `{selected_repeats_summary_path}`.",
                "Repeats are useful for stability context, but they do not by themselves create an order-matched non-LLM candidate budget.",
            ]
        )

    if not efficiency_allowed:
        lines.extend(
            [
                "",
                "## Caveat",
                "",
                "The comparison is unmatched. Report only descriptive candidate counts and selected-candidate outcomes; do not claim candidate efficiency.",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def write_llm_budget_diagnostic(
    llm_root: Path,
    nonllm_root: Path,
    output_root: Path,
    report_path: Path,
    budgets: Iterable[int] = DEFAULT_BUDGETS,
    selected_repeats_summary_path: Path | None = None,
) -> dict[str, Path]:
    """Write the order-aware budget diagnostic CSV and markdown report."""
    comparison = build_budget_matched_comparison(llm_root, nonllm_root, budgets)
    candidate_counts = build_candidate_count_summary(llm_root, nonllm_root)
    output_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_path = output_root / "budget_matched_comparison.csv"
    comparison.to_csv(comparison_path, index=False)
    report_path.write_text(
        build_budget_diagnostic_report(
            comparison,
            candidate_counts,
            selected_repeats_summary_path=selected_repeats_summary_path,
        ),
        encoding="utf-8",
    )
    return {"comparison": comparison_path, "report": report_path}
