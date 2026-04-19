from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.uncertainty.calibration_report import resolve_conformal_config, write_calibration_outputs
from src.utils.logging_utils import configure_logging


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run benchmark-level conformal calibration postprocess.")
    parser.add_argument("--config", type=str, required=True, help="Path to the benchmark YAML config.")
    parser.add_argument("--artifact-root", type=str, required=True, help="Existing benchmark artifact root to read from.")
    parser.add_argument("--output-root", type=str, default=None, help="Output root for conformal calibration artifacts.")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging verbosity.")
    args = parser.parse_args()

    configure_logging(args.log_level)
    repo_root = REPO_ROOT
    config = _load_config(repo_root / args.config)
    conformal_config = resolve_conformal_config(
        config,
        output_root=None if args.output_root is None else repo_root / args.output_root,
    )
    artifact_root = repo_root / args.artifact_root
    output_root = repo_root / conformal_config["output_dir"]
    write_calibration_outputs(artifact_root=artifact_root, output_root=output_root, config=config)


if __name__ == "__main__":
    main()
