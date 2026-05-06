# Paper Update Summary After Supplemental Experiments

## 1. Preflight Status

- Pytest result: `PASS` (`python -m pytest -q`, 100 tests passed).
- Git commit at preflight: `e3b37966c72f54d7ed9bc956db8829bf1318cc86`.
- Dirty files before writing this summary: missing-data/key notes under `reports/`.
- Frozen artifact roots checked and not modified.

## 2. Budget Diagnostic

- Diagnostic command completed successfully.
- Output report: `reports/llm_budget_diagnostic_report.md`.
- Output table: `artifacts_llm_budget_diagnostic/budget_matched_comparison.csv`.
- `efficiency_claim_allowed`: `false`.
- Reason: non-LLM candidate evaluation order metadata is unavailable, so LLM and non-LLM candidate budgets/order are not matched.

Exact paper sentence to use:

> Candidate-efficiency evidence is not supported under the current artifacts because non-LLM candidate evaluation order is unavailable; we therefore report candidate counts descriptively and make no LLM efficiency claim.

## 3. Multi-Season FluSurv-NET Audit

- Expected CSV exists: `false`.
- Expected path: `data/raw/flusurvnet_multiseason_full.csv`.
- Audit run: `no`.
- Missing-data note: `reports/flusurvnet_multiseason_missing_data_note.md`.
- Seasons available: not assessed.
- Complete seasons: not assessed.
- Age-group coverage: not assessed.
- Recommended train/validation/test split: not assessed.
- Ready for model experiments: `no`, pending the multi-season CSV and audit.

Until the CSV is added and model experiments are run, the paper should not claim cross-season generalization.

## 4. Dengue Audit And Smoke

- Expected dengue data exists: `false`.
- Expected path: `data/raw/National_extract_V1_3.csv`.
- Dengue audit run: `no`.
- Dengue non-LLM smoke run: `no`.
- Missing-data note: `reports/dengue_missing_data_note.md`.
- Recommended placement: future work for now. After the extract is added, audited, and smoked, dengue may be suitable as an appendix-level secondary surveillance benchmark.

Dengue is vector-borne and should be framed as a secondary surveillance structure-selection benchmark, not evidence that the flu hospitalization SEIR mechanism directly transfers to dengue.

## 5. Selected OpenAI Live Repeats

- `OPENAI_API_KEY` present in the current shell: `false`.
- Selected live repeats run: `no`.
- Missing-key note: `reports/llm_selected_repeats_missing_key_note.md`.
- Repeats completed: `0`.
- Leakage status: not assessed for new selected repeats.
- Valid proposal rates: not assessed for new selected repeats.
- V1-over-V0 stability by series: not assessed.
- V1-over-nonLLM stability by series: not assessed.
- Selected structure stability: not assessed.

OpenAI selected repeats should be run only after non-API diagnostics and data audits pass and a valid `OPENAI_API_KEY` is available.

## 6. Paper-Safe Claims

- LLM-V1 live all-series freeze is operational and validated, but it should be described as sometimes useful rather than globally superior.
- Candidate-efficiency claims are not supported by the current diagnostic because non-LLM candidate order is unavailable.
- Budget comparisons should be reported descriptively unless a future diagnostic sets `efficiency_claim_allowed=true`.
- Multi-season FluSurv-NET support is implemented, but cross-season empirical claims require the missing multi-season CSV, audit, and model experiments.
- Dengue support is a secondary benchmark layer; no dengue result is available from this run because the extract was missing.

## 7. Forbidden Claims

- Do not claim “LLM globally beats non-LLM.”
- Do not claim “LLM is more efficient” while the budget diagnostic blocks efficiency claims.
- Do not claim fractional SEIR is the main contribution.
- Do not claim the current result generalizes across seasons until multi-season experiments are actually run.
- Do not claim the flu hospitalization SEIR mechanism directly transfers to dengue.
