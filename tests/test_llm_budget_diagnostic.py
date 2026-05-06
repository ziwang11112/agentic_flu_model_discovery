from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluation.budget import (
    build_budget_diagnostic_report,
    build_budget_matched_comparison,
    build_candidate_count_summary,
    write_llm_budget_diagnostic,
)


def _write_llm_order(root: Path, series_slug: str = "overall", scores: list[float] | None = None) -> None:
    scores = scores or [0.50, 0.30, 0.40, 0.20]
    path = root / series_slug / "rounds" / "round_1" / "llm_leaderboard.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "series_name": ["Overall"] * len(scores),
            "round_id": [1] * len(scores),
            "proposal_id": list(range(len(scores))),
            "spec_key": [f"llm_{index}" for index in range(len(scores))],
            "score": scores,
        }
    ).to_csv(path, index=False)


def _write_nonllm_order(root: Path, scores: list[float] | None = None, include_order: bool = True) -> None:
    scores = scores or [0.45, 0.35, 0.25, 0.15]
    path = root / "overall" / "constrained_structure_discovery" / "leaderboard.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        {
            "series_name": ["Overall"] * len(scores),
            "spec_key": [f"nonllm_{index}" for index in range(len(scores))],
            "score": scores,
        }
    )
    if include_order:
        frame.insert(0, "evaluation_order", list(range(1, len(scores) + 1)))
    frame.to_csv(path, index=False)


def _write_summary_counts(llm_root: Path, llm_count: int = 4, nonllm_count: int = 6) -> None:
    pd.DataFrame(
        [
            {
                "series_name": "Overall",
                "v1_num_candidates_evaluated": llm_count,
                "nonllm_num_candidates_evaluated": nonllm_count,
            }
        ]
    ).to_csv(llm_root / "llm_v1_vs_v0_vs_nonllm_summary.csv", index=False)


def test_matched_order_computes_best_at_k_correctly(tmp_path: Path) -> None:
    llm_root = tmp_path / "llm"
    nonllm_root = tmp_path / "nonllm"
    _write_llm_order(llm_root, scores=[0.50, 0.30, 0.40, 0.20])
    _write_nonllm_order(nonllm_root, scores=[0.45, 0.35, 0.25, 0.15], include_order=True)

    comparison = build_budget_matched_comparison(llm_root, nonllm_root, budgets=[2, 4])

    row_k2 = comparison.loc[comparison["budget_k"] == 2].iloc[0]
    row_k4 = comparison.loc[comparison["budget_k"] == 4].iloc[0]
    assert row_k2["llm_best_score_at_k"] == 0.30
    assert row_k2["nonllm_best_score_at_k"] == 0.35
    assert bool(row_k2["llm_better_at_k"])
    assert bool(row_k2["order_matched"])
    assert bool(row_k2["efficiency_claim_allowed"])
    assert row_k4["llm_best_score_at_k"] == 0.20
    assert row_k4["nonllm_best_score_at_k"] == 0.15
    assert not bool(row_k4["llm_better_at_k"])


def test_missing_nonllm_order_blocks_efficiency_claim(tmp_path: Path) -> None:
    llm_root = tmp_path / "llm"
    nonllm_root = tmp_path / "nonllm"
    _write_llm_order(llm_root)
    _write_nonllm_order(nonllm_root, include_order=False)

    comparison = build_budget_matched_comparison(llm_root, nonllm_root, budgets=[4])
    row = comparison.iloc[0]

    assert bool(row["llm_order_available"])
    assert not bool(row["nonllm_order_available"])
    assert not bool(row["order_matched"])
    assert not bool(row["efficiency_claim_allowed"])
    assert "no candidate-efficiency claim is supported" in row["note"]


def test_report_includes_caveat_when_unmatched(tmp_path: Path) -> None:
    llm_root = tmp_path / "llm"
    nonllm_root = tmp_path / "nonllm"
    _write_llm_order(llm_root)
    _write_summary_counts(llm_root, llm_count=4, nonllm_count=12)

    comparison = build_budget_matched_comparison(llm_root, nonllm_root, budgets=[4])
    counts = build_candidate_count_summary(llm_root, nonllm_root)
    report = build_budget_diagnostic_report(comparison, counts)

    assert "Candidate-efficiency claims allowed: `false`" in report
    assert "No candidate-efficiency claim is supported" in report
    assert "The comparison is unmatched" in report
    assert "LLM evaluated fewer candidates than non-LLM in `1` series." in report


def test_write_llm_budget_diagnostic_uses_requested_output_names(tmp_path: Path) -> None:
    llm_root = tmp_path / "llm"
    nonllm_root = tmp_path / "nonllm"
    _write_llm_order(llm_root)
    _write_nonllm_order(nonllm_root, include_order=True)

    outputs = write_llm_budget_diagnostic(
        llm_root=llm_root,
        nonllm_root=nonllm_root,
        output_root=tmp_path / "out",
        report_path=tmp_path / "report.md",
        budgets=[4],
    )

    assert outputs["comparison"] == tmp_path / "out" / "budget_matched_comparison.csv"
    assert outputs["comparison"].exists()
    assert outputs["report"].exists()
