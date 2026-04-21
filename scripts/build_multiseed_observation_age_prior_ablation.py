from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.ablation import write_multiseed_observation_age_prior_ablation


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build multi-seed observation age-prior ablation summaries from two artifact roots."
    )
    parser.add_argument(
        "--age-prior-root",
        type=str,
        default="artifacts_multiseed_age_robustness_observation",
        help="Artifact root for the age-prior-enabled observation-aware multiseed run.",
    )
    parser.add_argument(
        "--no-age-prior-root",
        type=str,
        default="artifacts_multiseed_age_robustness_observation_no_age_prior",
        help="Artifact root for the no-age-prior observation-aware multiseed run.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="artifacts_multiseed_observation_age_prior_ablation",
        help="Directory where the ablation CSV outputs will be written.",
    )
    parser.add_argument(
        "--report",
        type=str,
        default="reports/multiseed_observation_age_prior_ablation_report.md",
        help="Markdown report output path.",
    )
    args = parser.parse_args()

    write_multiseed_observation_age_prior_ablation(
        age_prior_root=REPO_ROOT / args.age_prior_root,
        no_age_prior_root=REPO_ROOT / args.no_age_prior_root,
        output_root=REPO_ROOT / args.output_root,
        report_path=REPO_ROOT / args.report,
    )


if __name__ == "__main__":
    main()
