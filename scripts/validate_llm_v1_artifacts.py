from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


BANNED_TERMS = [
    "test_policy_model",
    "best_test_model",
    "test_mae",
    "test_rmse",
    "test_smape",
    "test coverage",
    "benchmark_series_winners",
    "final test winner",
    "held-out test winner",
]

ROUND_BANNED_COLUMNS = {
    "test_mae",
    "test_rmse",
    "test_smape",
    "best_test_model",
    "test_policy_model",
}

REQUIRED_GLOBAL_FILES = [
    "llm_v1_vs_v0_vs_nonllm_summary.csv",
    "llm_v1_valid_proposal_rate_by_round.csv",
    "llm_v1_candidate_efficiency.csv",
    "llm_v1_refinement_improvement.csv",
    "llm_v1_semantic_alignment.csv",
]

REQUIRED_SERIES_FILES = [
    "series_summary.json",
    "semantics_summary.json",
    "llm_refinement_trace.jsonl",
    "llm_refinement_trace.md",
    "best_validation_candidate.json",
    "final_selected_candidate.json",
    "final_selected_test_report.csv",
]

REQUIRED_ROUND_FILES = [
    "proposer_prompt.txt",
    "proposer_response.json",
    "critic_prompt.txt",
    "critic_response.json",
    "proposal_audit.csv",
    "llm_leaderboard.csv",
    "round_summary.json",
]

REQUIRED_ROUND_GE2_FILES = [
    "analyst_prompt.txt",
    "analyst_feedback.json",
]

REQUIRED_PROPOSAL_AUDIT_COLUMNS = {
    "series_name",
    "round_id",
    "proposal_id",
    "provider",
    "provider_is_mock",
    "scientific_claim_allowed",
    "raw_structure_name",
    "raw_fractional",
    "raw_observation_map",
    "raw_delay_weeks",
    "schema_valid",
    "hard_valid",
    "invalid_reason",
    "critic_priority",
    "critic_risk_flags",
    "evaluated",
}

REQUIRED_LEADERBOARD_COLUMNS = {
    "series_name",
    "round_id",
    "proposal_id",
    "spec_key",
    "structure_name",
    "fractional",
    "observation_map",
    "delay_weeks",
    "val_mae",
    "val_rmse",
    "rolling_val_mean_mae",
    "rolling_val_std_mae",
    "score",
    "complexity_penalty",
    "stability_penalty",
    "provider",
    "provider_is_mock",
    "scientific_claim_allowed",
}

REQUIRED_TRACE_KEYS = {
    "series_name",
    "round_id",
    "previous_best_spec",
    "previous_best_score",
    "analyst_feedback_summary",
    "new_specs",
    "round_best_spec",
    "round_best_score",
    "score_improvement",
    "early_stop",
}

MOCK_DISCLAIMER = (
    "Mock provider results are engineering smoke tests and should not be interpreted as evidence of LLM reasoning quality."
)
LIVE_PROVIDER_NOTE = "Live-provider results are preliminary single-run outputs."


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _round_sort_key(path: Path) -> tuple[int, str]:
    try:
        return (int(path.name.split("_")[-1]), path.name)
    except ValueError:
        return (10**9, path.name)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _contains_banned_term(text: str) -> list[str]:
    lowered = text.lower()
    return [term for term in BANNED_TERMS if term.lower() in lowered]


def _append_missing(missing: list[str], path: Path) -> None:
    missing.append(_relative(path))


def _load_csv_columns(path: Path) -> set[str]:
    return set(pd.read_csv(path, nrows=0).columns)


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _validate_trace_file(
    path: Path,
    leakage_failures: list[str],
    trace_failures: list[str],
) -> None:
    text = _read_text(path)
    banned = _contains_banned_term(text)
    if banned:
        leakage_failures.append(f"{_relative(path)} contains banned terms: {', '.join(banned)}")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            trace_failures.append(f"{_relative(path)} line {line_number}: invalid JSON ({exc})")
            continue
        missing_keys = sorted(REQUIRED_TRACE_KEYS - set(payload.keys()))
        if missing_keys:
            trace_failures.append(
                f"{_relative(path)} line {line_number}: missing trace keys {', '.join(missing_keys)}"
            )


def _write_report(
    *,
    report_path: Path,
    final_ok: bool,
    artifact_root: Path,
    series_dirs: list[Path],
    rounds_checked: int,
    files_checked: int,
    missing_files: list[str],
    leakage_failures: list[str],
    invalid_columns: list[str],
    trace_failures: list[str],
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    recommendations: list[str] = []
    if missing_files:
        recommendations.append(
            "Rerun `python scripts/run_llm_iterative_refinement.py --config configs/llm_v1_iterative.yaml --all-series --provider mock --log-level INFO` to regenerate missing artifacts."
        )
    if leakage_failures:
        recommendations.append(
            "Inspect prompt-safe summary generation, prompt builders, analyst inputs, and round artifact writers before freezing the run."
        )
    if invalid_columns:
        recommendations.append(
            "Align proposal audit / leaderboard schemas with the LLM-V1 protocol and regenerate artifacts."
        )
    if trace_failures:
        recommendations.append(
            "Regenerate `llm_refinement_trace.jsonl` after fixing trace serialization and rerun V1 artifact generation."
        )
    if not recommendations:
        recommendations.append("Artifacts satisfy the LLM-V1 validation protocol for the current run.")

    lines = [
        "# LLM V1 Artifact Validation Report",
        "",
        f"- status: `{'PASS' if final_ok else 'FAIL'}`",
        f"- artifact_root: `{_relative(artifact_root)}`",
        f"- series_checked: `{len(series_dirs)}`",
        f"- rounds_checked: `{rounds_checked}`",
        f"- files_checked: `{files_checked}`",
        f"- leakage_check_status: `{'PASS' if not leakage_failures else 'FAIL'}`",
        "",
        "## Series Checked",
        "",
    ]
    if series_dirs:
        lines.extend(f"- `{series_dir.name}`" for series_dir in series_dirs)
    else:
        lines.append("- none")

    lines.extend(["", "## Missing Files", ""])
    if missing_files:
        lines.extend(f"- `{item}`" for item in missing_files)
    else:
        lines.append("- none")

    lines.extend(["", "## Leakage Check Failures", ""])
    if leakage_failures:
        lines.extend(f"- {item}" for item in leakage_failures)
    else:
        lines.append("- none")

    lines.extend(["", "## Invalid Columns / Schema Failures", ""])
    if invalid_columns:
        lines.extend(f"- {item}" for item in invalid_columns)
    else:
        lines.append("- none")

    lines.extend(["", "## Trace Failures", ""])
    if trace_failures:
        lines.extend(f"- {item}" for item in trace_failures)
    else:
        lines.append("- none")

    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {item}" for item in recommendations)
    report_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate LLM-V1 artifact protocol compliance.")
    parser.add_argument("--artifact-root", default="artifacts_llm_v1")
    parser.add_argument("--report", default="reports/llm_v1_artifact_validation_report.md")
    parser.add_argument("--iterative-report", default="reports/llm_v1_iterative_report.md")
    args = parser.parse_args()

    artifact_root = (REPO_ROOT / args.artifact_root).resolve()
    report_path = (REPO_ROOT / args.report).resolve()
    iterative_report = (REPO_ROOT / args.iterative_report).resolve()

    missing_files: list[str] = []
    leakage_failures: list[str] = []
    invalid_columns: list[str] = []
    trace_failures: list[str] = []
    files_checked = 0
    rounds_checked = 0

    if not artifact_root.exists():
        _append_missing(missing_files, artifact_root)

    for relative_name in REQUIRED_GLOBAL_FILES:
        path = artifact_root / relative_name
        if path.exists():
            files_checked += 1
        else:
            _append_missing(missing_files, path)

    provider_is_mock = True
    summary_path = artifact_root / "llm_v1_vs_v0_vs_nonllm_summary.csv"
    if summary_path.exists():
        try:
            summary_head = pd.read_csv(summary_path, usecols=["provider_is_mock"])
            if not summary_head.empty:
                provider_is_mock = bool(summary_head["provider_is_mock"].map(_parse_bool).all())
        except (ValueError, TypeError):
            provider_is_mock = True
    if iterative_report.exists():
        files_checked += 1
        report_text = _read_text(iterative_report)
        if provider_is_mock and MOCK_DISCLAIMER not in report_text:
            leakage_failures.append(f"{_relative(iterative_report)} is missing the required mock disclaimer")
        if not provider_is_mock and LIVE_PROVIDER_NOTE not in report_text:
            leakage_failures.append(f"{_relative(iterative_report)} is missing the required live-provider note")
    else:
        _append_missing(missing_files, iterative_report)

    series_dirs = sorted(
        [path for path in artifact_root.iterdir() if path.is_dir()],
        key=lambda path: path.name,
    ) if artifact_root.exists() else []

    for series_dir in series_dirs:
        for name in REQUIRED_SERIES_FILES:
            path = series_dir / name
            if path.exists():
                files_checked += 1
            else:
                _append_missing(missing_files, path)

        for leak_name in ["series_summary.json", "semantics_summary.json"]:
            path = series_dir / leak_name
            if path.exists():
                banned = _contains_banned_term(_read_text(path))
                if banned:
                    leakage_failures.append(f"{_relative(path)} contains banned terms: {', '.join(banned)}")

        trace_path = series_dir / "llm_refinement_trace.jsonl"
        if trace_path.exists():
            _validate_trace_file(trace_path, leakage_failures, trace_failures)

        rounds_root = series_dir / "rounds"
        if not rounds_root.exists():
            _append_missing(missing_files, rounds_root)
            continue

        round_dirs = sorted([path for path in rounds_root.iterdir() if path.is_dir()], key=_round_sort_key)
        if not round_dirs:
            _append_missing(missing_files, rounds_root)
            continue

        for round_dir in round_dirs:
            rounds_checked += 1
            round_number = _round_sort_key(round_dir)[0]
            for name in REQUIRED_ROUND_FILES:
                path = round_dir / name
                if path.exists():
                    files_checked += 1
                else:
                    _append_missing(missing_files, path)

            if round_number >= 2:
                for name in REQUIRED_ROUND_GE2_FILES:
                    path = round_dir / name
                    if path.exists():
                        files_checked += 1
                    else:
                        _append_missing(missing_files, path)

            for leak_name in ["proposer_prompt.txt", "critic_prompt.txt", "proposal_audit.csv", "llm_leaderboard.csv"]:
                path = round_dir / leak_name
                if path.exists():
                    banned = _contains_banned_term(_read_text(path))
                    if banned:
                        leakage_failures.append(f"{_relative(path)} contains banned terms: {', '.join(banned)}")
            analyst_prompt = round_dir / "analyst_prompt.txt"
            if analyst_prompt.exists():
                banned = _contains_banned_term(_read_text(analyst_prompt))
                if banned:
                    leakage_failures.append(f"{_relative(analyst_prompt)} contains banned terms: {', '.join(banned)}")

            proposal_audit_path = round_dir / "proposal_audit.csv"
            if proposal_audit_path.exists():
                columns = _load_csv_columns(proposal_audit_path)
                missing = sorted(REQUIRED_PROPOSAL_AUDIT_COLUMNS - columns)
                if missing:
                    invalid_columns.append(
                        f"{_relative(proposal_audit_path)} missing required columns: {', '.join(missing)}"
                    )

            leaderboard_path = round_dir / "llm_leaderboard.csv"
            if leaderboard_path.exists():
                columns = _load_csv_columns(leaderboard_path)
                missing = sorted(REQUIRED_LEADERBOARD_COLUMNS - columns)
                if missing:
                    invalid_columns.append(
                        f"{_relative(leaderboard_path)} missing required columns: {', '.join(missing)}"
                    )
                banned_columns = sorted(ROUND_BANNED_COLUMNS.intersection({column.lower() for column in columns}))
                if banned_columns:
                    invalid_columns.append(
                        f"{_relative(leaderboard_path)} contains forbidden round-level columns: {', '.join(banned_columns)}"
                    )

    final_ok = not (missing_files or leakage_failures or invalid_columns or trace_failures)
    _write_report(
        report_path=report_path,
        final_ok=final_ok,
        artifact_root=artifact_root,
        series_dirs=series_dirs,
        rounds_checked=rounds_checked,
        files_checked=files_checked,
        missing_files=missing_files,
        leakage_failures=leakage_failures,
        invalid_columns=invalid_columns,
        trace_failures=trace_failures,
    )

    if not final_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
