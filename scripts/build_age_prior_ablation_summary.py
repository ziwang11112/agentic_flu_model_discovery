from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.ablation import write_age_prior_ablation_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build age-prior ablation summary from two benchmark artifact roots.")
    parser.add_argument(
        "--age-prior-root",
        type=str,
        default="artifacts_age_robustness_age_prior",
        help="Artifact root for the age-prior-enabled run.",
    )
    parser.add_argument(
        "--no-age-prior-root",
        type=str,
        default="artifacts_age_robustness_no_age_prior",
        help="Artifact root for the no-age-prior run.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts_age_prior_ablation/age_prior_ablation_summary.csv",
        help="Output CSV path.",
    )
    args = parser.parse_args()

    write_age_prior_ablation_summary(
        age_prior_root=REPO_ROOT / args.age_prior_root,
        no_age_prior_root=REPO_ROOT / args.no_age_prior_root,
        output_path=REPO_ROOT / args.output,
    )


if __name__ == "__main__":
    main()
