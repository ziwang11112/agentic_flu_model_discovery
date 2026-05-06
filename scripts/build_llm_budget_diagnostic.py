from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.budget import DEFAULT_BUDGETS, write_llm_budget_diagnostic


FORBIDDEN_OUTPUT_ROOTS = {
    "artifacts_llm_v1_openai_all_series_freeze",
    "artifacts_llm_v1_openai_two_series_smoke",
    "artifacts_llm_v1",
    "artifacts_multiseed_age_robustness_observation",
    "artifacts_v5_conformal_v3",
}


def _resolve_repo_path(path: str | Path | None) -> Path | None:
    if path is None:
        return None
    resolved = Path(path)
    return resolved if resolved.is_absolute() else REPO_ROOT / resolved


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def _assert_not_forbidden_output(path: Path) -> None:
    resolved = path.resolve()
    for root_name in FORBIDDEN_OUTPUT_ROOTS:
        forbidden = (REPO_ROOT / root_name).resolve()
        if resolved == forbidden or forbidden in resolved.parents:
            raise ValueError(f"Refusing to write budget diagnostic output under frozen artifact root: {root_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an order-aware LLM-vs-nonLLM candidate budget diagnostic.")
    parser.add_argument("--llm-root", default="artifacts_llm_v1_openai_all_series_freeze")
    parser.add_argument("--nonllm-root", default="artifacts_multiseed_age_robustness_observation")
    parser.add_argument("--output-root", default="artifacts_llm_budget_diagnostic")
    parser.add_argument("--report", default="reports/llm_budget_diagnostic_report.md")
    parser.add_argument("--budgets", type=int, nargs="+", default=list(DEFAULT_BUDGETS))
    parser.add_argument(
        "--selected-repeats-summary",
        default=None,
        help="Optional selected-repeat summary path for report context only.",
    )
    args = parser.parse_args()

    llm_root = _resolve_repo_path(args.llm_root)
    nonllm_root = _resolve_repo_path(args.nonllm_root)
    output_root = _resolve_repo_path(args.output_root)
    report_path = _resolve_repo_path(args.report)
    selected_repeats_summary = _resolve_repo_path(args.selected_repeats_summary)
    assert llm_root is not None
    assert nonllm_root is not None
    assert output_root is not None
    assert report_path is not None

    _assert_not_forbidden_output(output_root)
    _assert_not_forbidden_output(report_path)

    outputs = write_llm_budget_diagnostic(
        llm_root=llm_root,
        nonllm_root=nonllm_root,
        output_root=output_root,
        report_path=report_path,
        budgets=args.budgets,
        selected_repeats_summary_path=selected_repeats_summary,
    )
    print("Wrote LLM budget diagnostic outputs:")
    for name, path in outputs.items():
        print(f"- {name}: {_relative(path)}")


if __name__ == "__main__":
    main()
