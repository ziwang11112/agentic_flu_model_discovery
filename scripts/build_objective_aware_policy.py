from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.multiseed import (  # noqa: E402
    build_objective_aware_policy_report,
    build_pairwise_model_differences,
    build_multiseed_model_summary,
    build_multiseed_objective_policy,
)
from src.utils.io import ensure_dir  # noqa: E402


def _seed_artifact_roots(multiseed_root: Path) -> dict[int, Path]:
    seed_root = multiseed_root / "seed_runs"
    if not seed_root.exists():
        raise RuntimeError(f"Missing seed_runs directory: {seed_root}")

    roots: dict[int, Path] = {}
    for path in sorted(seed_root.glob("seed_*")):
        try:
            seed = int(path.name.split("_", 1)[1])
        except (IndexError, ValueError) as exc:
            raise RuntimeError(f"Could not parse seed directory name: {path.name}") from exc
        roots[seed] = path
    if not roots:
        raise RuntimeError(f"No seed directories found under: {seed_root}")
    return roots


def main() -> None:
    parser = argparse.ArgumentParser(description="Build tie-aware and objective-aware multi-seed policy outputs.")
    parser.add_argument(
        "--input-root",
        default="artifacts_multiseed_age_robustness_observation",
        help="Multi-seed artifact root containing seed_runs/ and multiseed_model_summary.csv.",
    )
    parser.add_argument(
        "--report-path",
        default="reports/objective_aware_policy_report.md",
        help="Markdown report output path.",
    )
    args = parser.parse_args()

    input_root = REPO_ROOT / args.input_root
    report_path = REPO_ROOT / args.report_path
    seed_artifact_roots = _seed_artifact_roots(input_root)

    model_summary = build_multiseed_model_summary(seed_artifact_roots)
    objective_policy = build_multiseed_objective_policy(model_summary)
    pairwise = build_pairwise_model_differences(seed_artifact_roots)
    objective_policy_path = input_root / "multiseed_objective_policy.csv"
    pairwise_path = input_root / "pairwise_model_differences.csv"
    objective_policy.to_csv(objective_policy_path, index=False)
    pairwise.to_csv(pairwise_path, index=False)

    ensure_dir(report_path.parent)
    report_path.write_text(build_objective_aware_policy_report(objective_policy, pairwise), encoding="utf-8")

    print("Wrote objective-aware policy outputs:")
    print(f"- policy: {objective_policy_path}")
    print(f"- pairwise: {pairwise_path}")
    print(f"- report: {report_path}")


if __name__ == "__main__":
    main()
