# Reproducibility Snapshot: LLM-V1 Mock Freeze

## Git Snapshot

- git commit hash at validation time: `f4491d0affcf678cd79ae19c98a0aaa1b8150b3a`
- branch: `main`
- note: this snapshot freezes the mock-provider engineering artifacts in `artifacts_llm_v1/`. Live-provider smoke artifacts are separate and should not be interpreted as part of the mock freeze.

## Validation Results

- pytest result: `75 passed in 13.76s`
- V1 artifact validation result: `PASS`
- artifact validation summary:
  - artifact root: `artifacts_llm_v1`
  - series checked: `6`
  - rounds checked: `13`
  - files checked: `153`
  - leakage check status: `PASS`
  - missing files: `none`
  - invalid columns / schema failures: `none`
  - trace failures: `none`

## Commands Used For V1 Mock Run

```bash
python scripts/run_llm_iterative_refinement.py \
  --config configs/llm_v1_iterative.yaml \
  --all-series \
  --provider mock \
  --log-level INFO
```

```bash
python scripts/build_llm_v1_report.py \
  --config configs/llm_v1_iterative.yaml \
  --artifact-root artifacts_llm_v1 \
  --output reports/llm_v1_iterative_report.md
```

```bash
python scripts/validate_llm_v1_artifacts.py \
  --artifact-root artifacts_llm_v1 \
  --report reports/llm_v1_artifact_validation_report.md
```

```bash
python -m pytest -q
```

## Artifact Roots

- frozen mock artifacts: `artifacts_llm_v1/`
- frozen mock report: `reports/llm_v1_iterative_report.md`
- frozen mock validation report: `reports/llm_v1_artifact_validation_report.md`

## Provider Scope

- frozen provider: `mock`
- scientific_claim_allowed: `false`
- Mock-provider V1 validates orchestration, schema parsing, leakage guards, hard validation, candidate execution, trace generation, and artifact protocol.
- Mock-provider results are engineering validation only and should not be interpreted as evidence of live LLM reasoning quality.
- Live-provider smoke runs must use separate artifact roots, such as `artifacts_llm_v1_openai_two_series_smoke/`.
