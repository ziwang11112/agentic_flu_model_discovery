from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from src.llm.config import load_llm_config
from src.llm.reporting import write_llm_v0_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the LLM-V0 markdown report.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--artifact-root", default="artifacts_llm_v0")
    args = parser.parse_args()

    repo_root = REPO_ROOT
    llm_config = load_llm_config(repo_root / args.config)
    summary = pd.read_csv(repo_root / args.artifact_root / "llm_vs_nonllm_summary.csv")
    write_llm_v0_report(summary, repo_root / "reports" / "llm_v0_report.md", llm_config)


if __name__ == "__main__":
    main()
