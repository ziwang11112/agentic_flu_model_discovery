from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from src.llm.config import load_llm_config
from src.llm.reporting import write_llm_v1_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the LLM-V1 iterative report.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--artifact-root", default="artifacts_llm_v1")
    parser.add_argument("--output", default="reports/llm_v1_iterative_report.md")
    args = parser.parse_args()

    llm_config = load_llm_config(REPO_ROOT / args.config)
    summary = pd.read_csv(REPO_ROOT / args.artifact_root / "llm_v1_vs_v0_vs_nonllm_summary.csv")
    improvement = pd.read_csv(REPO_ROOT / args.artifact_root / "llm_v1_refinement_improvement.csv")
    write_llm_v1_report(summary, improvement, REPO_ROOT / args.output, llm_config)


if __name__ == "__main__":
    main()
