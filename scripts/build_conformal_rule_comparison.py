from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.uncertainty.calibration_report import write_conformal_rule_comparison


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a conformal winner-rule comparison table from existing outputs.")
    parser.add_argument("--v1-root", type=str, default="artifacts_v5_conformal", help="Artifact root for v1 outputs.")
    parser.add_argument("--v2-root", type=str, default="artifacts_v5_conformal_v2", help="Artifact root for v2 outputs.")
    parser.add_argument("--v3-root", type=str, default="artifacts_v5_conformal_v3", help="Artifact root for v3 outputs.")
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts_v5_conformal_v3/conformal_rule_comparison.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--selected-default",
        type=str,
        default="v3",
        help="Rule name to mark as the current default.",
    )
    args = parser.parse_args()

    write_conformal_rule_comparison(
        rule_roots={
            "v1": REPO_ROOT / args.v1_root,
            "v2": REPO_ROOT / args.v2_root,
            "v3": REPO_ROOT / args.v3_root,
        },
        output_path=REPO_ROOT / args.output,
        selected_default=args.selected_default,
    )


if __name__ == "__main__":
    main()
