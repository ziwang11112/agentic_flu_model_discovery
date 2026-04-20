from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.multiseed import write_multiseed_outputs
from src.utils.io import ensure_dir, write_yaml


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _seed_artifact_root(multiseed_root: Path, seed: int) -> Path:
    return multiseed_root / "seed_runs" / f"seed_{seed}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run and aggregate multi-seed influenza benchmarks.")
    parser.add_argument("--config", type=str, required=True, help="Path to the YAML config.")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging verbosity passed to run_experiment.py")
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help="Skip benchmark runs and only aggregate existing per-seed artifacts.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip seed runs whose benchmark_model_summary.csv already exists.",
    )
    args = parser.parse_args()

    repo_root = REPO_ROOT
    config_path = repo_root / args.config
    config = _load_config(config_path)
    experiment = config.get("experiment", {})
    seeds = [int(value) for value in experiment.get("seeds", [int(config["seed"])])]
    multiseed_root = ensure_dir(repo_root / experiment.get("multiseed_output_root", "artifacts_multiseed"))
    temp_config_root = ensure_dir(multiseed_root / "temp_configs")

    seed_artifact_roots: dict[int, Path] = {}
    for seed in seeds:
        seed_artifact_root = _seed_artifact_root(multiseed_root, seed)
        seed_artifact_roots[seed] = seed_artifact_root
        if args.aggregate_only:
            continue

        summary_path = seed_artifact_root / "benchmark_model_summary.csv"
        if args.skip_existing and summary_path.exists():
            continue

        seed_config = yaml.safe_load(yaml.safe_dump(config))
        seed_config["seed"] = seed
        seed_config.setdefault("artifacts", {})
        seed_config["artifacts"]["root_dir"] = str(seed_artifact_root.relative_to(repo_root))
        temp_config_path = temp_config_root / f"{config_path.stem}_seed_{seed}.yaml"
        write_yaml(seed_config, temp_config_path)

        subprocess.run(
            [
                sys.executable,
                str(repo_root / "run_experiment.py"),
                "--config",
                str(temp_config_path),
                "--log-level",
                args.log_level,
            ],
            cwd=repo_root,
            check=True,
        )

    outputs = write_multiseed_outputs(seed_artifact_roots, multiseed_root)
    print("Wrote multi-seed outputs:")
    for key, value in outputs.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
