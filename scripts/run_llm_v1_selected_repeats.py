from __future__ import annotations

import argparse
from collections import Counter
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]

SELECTED_SERIES = ["0-4 yr", "5-17 yr", ">= 65 yr"]
REPEAT_IDS = [1, 2, 3]
SUMMARY_ROOT = REPO_ROOT / "artifacts_llm_v1_openai_selected_repeats_summary"
AGGREGATE_REPORT = REPO_ROOT / "reports" / "llm_v1_openai_selected_repeat_report.md"
FORBIDDEN_ARTIFACT_ROOTS = {
    "artifacts_llm_v1_openai_all_series_freeze",
    "artifacts_llm_v1_openai_two_series_smoke",
    "artifacts_llm_v1",
    "artifacts_multiseed_age_robustness_observation",
    "artifacts_v5_conformal_v3",
}


def _load_repo_env() -> None:
    env_path = REPO_ROOT / ".env"
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


def _require_openai_api_key(load_dotenv: bool = True) -> None:
    if load_dotenv:
        _load_repo_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is required for selected live repeats with provider=openai. "
            "Set it in the environment or in the repository .env file before running this script."
        )


def _config_path(repeat_id: int) -> Path:
    return REPO_ROOT / "configs" / f"llm_v1_iterative_openai_selected_repeat_{repeat_id}.yaml"


def _artifact_root(repeat_id: int) -> Path:
    return REPO_ROOT / "artifacts_llm_v1_openai_selected_repeats" / f"run_{repeat_id}"


def _iterative_report_path(repeat_id: int) -> Path:
    return REPO_ROOT / "reports" / f"llm_v1_openai_selected_repeat_{repeat_id}_iterative_report.md"


def _validation_report_path(repeat_id: int) -> Path:
    return REPO_ROOT / "reports" / f"llm_v1_openai_selected_repeat_{repeat_id}_artifact_validation_report.md"


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _assert_not_forbidden_output(path: Path) -> None:
    resolved = path.resolve()
    for root_name in FORBIDDEN_ARTIFACT_ROOTS:
        forbidden = (REPO_ROOT / root_name).resolve()
        if resolved == forbidden or forbidden in resolved.parents:
            raise RuntimeError(f"Refusing to write selected-repeat output under frozen artifact root: {root_name}")


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _nullable_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _parse_leakage_status(report_path: Path) -> str:
    if not report_path.exists():
        return "MISSING"
    text = report_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"leakage_check_status:\s*`([^`]+)`", text)
    if match:
        return match.group(1)
    status_match = re.search(r"- status:\s*`([^`]+)`", text)
    return status_match.group(1) if status_match else "UNKNOWN"


def _slug_to_series_name(slug: str) -> str:
    mapping = {
        "0_4_yr": "0-4 yr",
        "5_17_yr": "5-17 yr",
        "ge__65_yr": ">= 65 yr",
    }
    return mapping.get(slug, slug)


def _audit_counts(artifact_root: Path) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {
        series_name: {"proposal_count": 0, "hard_valid_count": 0}
        for series_name in SELECTED_SERIES
    }
    for audit_path in sorted(artifact_root.glob("*/rounds/round_*/proposal_audit.csv")):
        frame = pd.read_csv(audit_path)
        if frame.empty:
            series_name = _slug_to_series_name(audit_path.parents[2].name)
        else:
            series_name = str(frame.iloc[0]["series_name"])
        proposal_count = int(len(frame))
        hard_valid_count = int(frame["hard_valid"].map(_parse_bool).sum()) if "hard_valid" in frame else 0
        counts.setdefault(series_name, {"proposal_count": 0, "hard_valid_count": 0})
        counts[series_name]["proposal_count"] += proposal_count
        counts[series_name]["hard_valid_count"] += hard_valid_count
    return counts


def _parse_spec(spec: str) -> dict[str, Any]:
    pieces = spec.split("|")
    parsed: dict[str, Any] = {
        "selected_structure_name": pieces[0],
        "selected_fractional": False,
        "selected_observation_map": "",
        "selected_delay_weeks": 0,
    }
    for piece in pieces[1:]:
        if piece.startswith("fractional="):
            parsed["selected_fractional"] = piece.split("=", 1)[1] in {"1", "true", "True"}
        elif piece.startswith("obs="):
            parsed["selected_observation_map"] = piece.split("=", 1)[1]
        elif piece.startswith("delay="):
            parsed["selected_delay_weeks"] = int(piece.split("=", 1)[1])
    return parsed


def _dominant(values: pd.Series) -> Any:
    cleaned = [value for value in values.tolist() if pd.notna(value)]
    if not cleaned:
        return None
    return sorted(Counter(cleaned).items(), key=lambda item: (-item[1], str(item[0])))[0][0]


def _run_repeat(repeat_id: int, log_level: str, rerun_existing: bool) -> None:
    config_path = _config_path(repeat_id)
    artifact_root = _artifact_root(repeat_id)
    _assert_not_forbidden_output(artifact_root)
    summary_path = artifact_root / "llm_v1_vs_v0_vs_nonllm_summary.csv"

    if not config_path.exists():
        raise RuntimeError(f"Missing repeat config: {_relative(config_path)}")

    if summary_path.exists() and not rerun_existing:
        print(f"Skipping live repeat {repeat_id}; existing summary found at {_relative(summary_path)}")
    else:
        command = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_llm_iterative_refinement.py"),
            "--config",
            _relative(config_path),
            "--provider",
            "openai",
            "--log-level",
            log_level,
        ]
        for series_name in SELECTED_SERIES:
            command.extend(["--series", series_name])
        _run(command)

    if not summary_path.exists():
        raise RuntimeError(f"Repeat {repeat_id} did not produce {_relative(summary_path)}")

    _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "build_llm_v1_report.py"),
            "--config",
            _relative(config_path),
            "--artifact-root",
            _relative(artifact_root),
            "--output",
            _relative(_iterative_report_path(repeat_id)),
        ]
    )
    _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_llm_v1_artifacts.py"),
            "--artifact-root",
            _relative(artifact_root),
            "--iterative-report",
            _relative(_iterative_report_path(repeat_id)),
            "--report",
            _relative(_validation_report_path(repeat_id)),
        ]
    )


def _load_repeat_rows(repeat_id: int) -> list[dict[str, Any]]:
    artifact_root = _artifact_root(repeat_id)
    summary_path = artifact_root / "llm_v1_vs_v0_vs_nonllm_summary.csv"
    if not summary_path.exists():
        raise RuntimeError(f"Missing repeat summary: {_relative(summary_path)}")

    summary = pd.read_csv(summary_path)
    counts = _audit_counts(artifact_root)
    leakage_status = _parse_leakage_status(_validation_report_path(repeat_id))
    rows: list[dict[str, Any]] = []

    for _, row in summary.iterrows():
        series_name = str(row["series_name"])
        if series_name not in SELECTED_SERIES:
            continue
        selected_spec = str(row["v1_best_spec"])
        v1_score = float(row["v1_best_score"])
        v0_score = float(row["v0_best_score"])
        nonllm_score = _nullable_float(row["nonllm_best_score"])
        v1_minus_nonllm_score = None if nonllm_score is None else v1_score - nonllm_score
        v1_better_than_nonllm = None if nonllm_score is None else bool(v1_score < nonllm_score)
        v1_minus_nonllm_test_mae = _nullable_float(row.get("v1_minus_nonllm_test_mae"))
        v1_minus_nonllm_rolling_mae = _nullable_float(row.get("v1_minus_nonllm_rolling_mae"))
        proposal_count = int(counts.get(series_name, {}).get("proposal_count", 0))
        hard_valid_count = int(counts.get(series_name, {}).get("hard_valid_count", 0))
        valid_rate = None if proposal_count == 0 else hard_valid_count / proposal_count
        rows.append(
            {
                "series_name": series_name,
                "repeat_id": repeat_id,
                "selected_spec": selected_spec,
                "selected_round": int(row["v1_selected_round_id"]),
                "v1_score": v1_score,
                "v0_score": v0_score,
                "nonllm_score": nonllm_score,
                "v1_minus_v0_score": v1_score - v0_score,
                "v1_minus_nonllm_score": v1_minus_nonllm_score,
                "v1_better_than_v0": bool(v1_score < v0_score),
                "v1_better_than_nonllm": v1_better_than_nonllm,
                "v1_minus_nonllm_test_mae": v1_minus_nonllm_test_mae,
                "v1_minus_nonllm_rolling_mae": v1_minus_nonllm_rolling_mae,
                "v1_better_than_nonllm_test_mae": None
                if v1_minus_nonllm_test_mae is None
                else bool(v1_minus_nonllm_test_mae < 0),
                "v1_better_than_nonllm_rolling_mae": None
                if v1_minus_nonllm_rolling_mae is None
                else bool(v1_minus_nonllm_rolling_mae < 0),
                "proposal_count": proposal_count,
                "hard_valid_count": hard_valid_count,
                "valid_rate": valid_rate,
                "leakage_status": leakage_status,
                **_parse_spec(selected_spec),
            }
        )
    return rows


def _build_structure_stability(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for series_name, subset in summary.groupby("series_name", sort=True):
        nonllm_score_available = subset["v1_better_than_nonllm"].dropna()
        rows.append(
            {
                "series_name": series_name,
                "repeats": int(subset["repeat_id"].nunique()),
                "v1_over_v0_rate": float(subset["v1_better_than_v0"].mean()),
                "v1_over_nonllm_score_rate": None
                if nonllm_score_available.empty
                else float(nonllm_score_available.mean()),
                "mean_v1_score": float(subset["v1_score"].mean()),
                "std_v1_score": float(subset["v1_score"].std(ddof=1)) if len(subset) > 1 else 0.0,
                "mean_v1_minus_v0": float(subset["v1_minus_v0_score"].mean()),
                "mean_v1_minus_nonllm_score": None
                if subset["v1_minus_nonllm_score"].dropna().empty
                else float(subset["v1_minus_nonllm_score"].mean()),
                "mean_v1_minus_nonllm_test_mae": float(subset["v1_minus_nonllm_test_mae"].mean()),
                "mean_v1_minus_nonllm_rolling_mae": float(subset["v1_minus_nonllm_rolling_mae"].mean()),
                "dominant_selected_spec": _dominant(subset["selected_spec"]),
                "dominant_observation_map": _dominant(subset["selected_observation_map"]),
                "dominant_fractional": _dominant(subset["selected_fractional"]),
                "dominant_delay_weeks": _dominant(subset["selected_delay_weeks"]),
                "mean_valid_rate": float(subset["valid_rate"].mean()),
            }
        )
    return pd.DataFrame(rows)


def _build_validity_summary(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, subset in summary.groupby(["repeat_id", "series_name"], sort=True):
        repeat_id, series_name = keys
        rows.append(
            {
                "repeat_id": int(repeat_id),
                "series_name": series_name,
                "proposal_count": int(subset["proposal_count"].sum()),
                "hard_valid_count": int(subset["hard_valid_count"].sum()),
                "valid_rate": float(subset["valid_rate"].mean()),
                "leakage_status": _dominant(subset["leakage_status"]),
            }
        )
    for repeat_id, subset in summary.groupby("repeat_id", sort=True):
        proposal_count = int(subset["proposal_count"].sum())
        hard_valid_count = int(subset["hard_valid_count"].sum())
        rows.append(
            {
                "repeat_id": int(repeat_id),
                "series_name": "ALL",
                "proposal_count": proposal_count,
                "hard_valid_count": hard_valid_count,
                "valid_rate": None if proposal_count == 0 else hard_valid_count / proposal_count,
                "leakage_status": "PASS" if set(subset["leakage_status"]) == {"PASS"} else _dominant(subset["leakage_status"]),
            }
        )
    return pd.DataFrame(rows)


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_No rows available._"]
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.loc[:, columns].iterrows():
        values = []
        for column in columns:
            value = row[column]
            if pd.isna(value):
                values.append("n/a")
            elif isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return rows


def _write_aggregate_report(summary: pd.DataFrame, stability: pd.DataFrame, validity: pd.DataFrame) -> None:
    AGGREGATE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    total_proposals = int(validity.loc[validity["series_name"] == "ALL", "proposal_count"].sum())
    total_valid = int(validity.loc[validity["series_name"] == "ALL", "hard_valid_count"].sum())
    overall_valid_rate = 0.0 if total_proposals == 0 else total_valid / total_proposals
    all_leakage_pass = bool((summary["leakage_status"] == "PASS").all()) if not summary.empty else False

    lines = [
        "# LLM-V1 OpenAI Selected Repeat Report",
        "",
        "This report aggregates three controlled live-provider LLM-V1 repeats for `0-4 yr`, `5-17 yr`, and `>= 65 yr`.",
        "",
        "Live repeats are controlled evaluations. Candidate budgets are still not matched, and these results must not be used to claim that LLM-V1 globally beats non-LLM discovery.",
        "",
        "The same V1 protocol is used in every repeat: OpenAI live provider, no-test-leakage guard, hard validation before execution, validation/rolling selection, and post-selection test evaluation only.",
        "",
        "## Aggregate Validity",
        "",
        f"- Total raw proposals: `{total_proposals}`",
        f"- Total hard-valid proposals: `{total_valid}`",
        f"- Mean hard-valid rate over all selected repeats: `{overall_valid_rate:.3f}`",
        f"- Leakage status across repeat artifacts: `{'PASS' if all_leakage_pass else 'CHECK'}`",
        "",
        "## Structure Stability",
        "",
        "The non-LLM score-rate column is `n/a` when the reference discovery candidate budget/score is unavailable. Non-LLM test and rolling deltas below are descriptive MAE differences, not matched-budget efficiency evidence.",
        "",
    ]
    columns = [
        "series_name",
        "repeats",
        "v1_over_v0_rate",
        "v1_over_nonllm_score_rate",
        "mean_v1_score",
        "std_v1_score",
        "mean_v1_minus_nonllm_test_mae",
        "mean_v1_minus_nonllm_rolling_mae",
        "dominant_selected_spec",
        "mean_valid_rate",
    ]
    lines.extend(_markdown_table(stability, columns))
    lines.extend(
        [
            "",
            "## Per-Repeat Outputs",
            "",
            f"- `{_relative(SUMMARY_ROOT / 'live_repeat_summary.csv')}`",
            f"- `{_relative(SUMMARY_ROOT / 'live_repeat_structure_stability.csv')}`",
            f"- `{_relative(SUMMARY_ROOT / 'live_repeat_validity_summary.csv')}`",
            "",
            "## Interpretation Boundary",
            "",
            "These repeats test live-provider stability on selected informative series. They do not replace the frozen all-series evaluation and do not establish broad generalization beyond the current single-season proof of concept.",
            "The observation-aware non-LLM constrained discovery baseline remains the stronger overall reference unless repeat evidence shows otherwise under matched or explicitly analyzed candidate budgets.",
        ]
    )
    AGGREGATE_REPORT.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def aggregate_outputs(repeats: list[int]) -> dict[str, Path]:
    _assert_not_forbidden_output(SUMMARY_ROOT)
    rows: list[dict[str, Any]] = []
    for repeat_id in repeats:
        rows.extend(_load_repeat_rows(repeat_id))
    summary = pd.DataFrame(rows).sort_values(["series_name", "repeat_id"]).reset_index(drop=True)
    stability = _build_structure_stability(summary)
    validity = _build_validity_summary(summary)

    SUMMARY_ROOT.mkdir(parents=True, exist_ok=True)
    summary_path = SUMMARY_ROOT / "live_repeat_summary.csv"
    stability_path = SUMMARY_ROOT / "live_repeat_structure_stability.csv"
    validity_path = SUMMARY_ROOT / "live_repeat_validity_summary.csv"
    summary.to_csv(summary_path, index=False)
    stability.to_csv(stability_path, index=False)
    validity.to_csv(validity_path, index=False)
    _write_aggregate_report(summary, stability, validity)
    return {
        "summary": summary_path,
        "structure_stability": stability_path,
        "validity_summary": validity_path,
        "report": AGGREGATE_REPORT,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run selected-series OpenAI live repeats for LLM-V1.")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--repeat-ids",
        type=int,
        nargs="+",
        default=REPEAT_IDS,
        help="Repeat IDs to run or aggregate, for example: --repeat-ids 1 2 3.",
    )
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument(
        "--rerun-existing",
        action="store_true",
        help="Rerun a repeat even if its global summary already exists. Existing repeat roots are not deleted first.",
    )
    args = parser.parse_args()

    repeats = [int(value) for value in args.repeat_ids]
    if not set(repeats).issubset(set(REPEAT_IDS)):
        raise ValueError(f"Supported repeats are {REPEAT_IDS}")

    if not args.aggregate_only:
        _require_openai_api_key()
        for repeat_id in repeats:
            _run_repeat(repeat_id, args.log_level, args.rerun_existing)

    outputs = aggregate_outputs(repeats)
    print("Wrote selected repeat outputs:")
    for name, path in outputs.items():
        print(f"- {name}: {_relative(path)}")


if __name__ == "__main__":
    main()
