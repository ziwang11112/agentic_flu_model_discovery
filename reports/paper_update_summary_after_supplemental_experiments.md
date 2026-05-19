# Paper Update Summary After Supplemental Experiments

## 1. Preflight Status

- Pytest result: `PASS` (`python -m pytest tests -q`, 105 tests passed).
- Git commit at preflight: `cf1d0d416c5cbe41756d7a4d0fbfec6bfea06e9f`.
- Frozen artifact roots checked and not modified.
- No OpenAI live repeat was run in this pass.

## 2. Budget Diagnostic

- Diagnostic report: `reports/llm_budget_diagnostic_report.md`.
- Output table: `artifacts_llm_budget_diagnostic/budget_matched_comparison.csv`.
- `efficiency_claim_allowed`: `false`.
- Reason: non-LLM candidate evaluation order metadata is unavailable, so LLM and non-LLM candidate budgets/order are not matched.

Paper sentence to use:

> Candidate-efficiency evidence is not supported under the current artifacts because non-LLM candidate evaluation order is unavailable; we therefore report candidate counts descriptively and make no LLM efficiency claim.

## 3. Multi-Season FluSurv-NET Audit

- Multi-season CSV exists: `true`.
- Prepared path: `data/raw/flusurvnet_multiseason_full.csv`.
- Audit report: `reports/flusurvnet_multiseason_audit.md`.
- Normalized rows: `9,884`.
- Available seasons: `2018-19`, `2019-20`, `2020-21`, `2021-22`, `2022-23`, `2023-24`, `2024-25`, `2025-26`.
- Complete main-benchmark seasons: `2018-19`, `2019-20`, `2021-22`, `2022-23`, `2023-24`, `2024-25`.
- Excluded seasons: `2020-21` is missing required age-group rows; `2025-26` is current/preliminary.
- Recommended split: train = `2018-19`, `2019-20`, `2021-22`, `2022-23`; validation = `2023-24`; test = `2024-25`.

## 4. Multi-Season Seasonal Benchmark

- Selected benchmark report: `reports/flusurvnet_multiseason_seasonal_selected_report.md`.
- Artifact root: `artifacts_flusurvnet_multiseason_seasonal_selected`.
- Scope: 18 season/age trajectories = 6 complete seasons x `Overall`, `0-4 yr`, `>= 65 yr`.
- Models: deterministic SEIR, probabilistic SEIR, hospitalized SEIHR, delayed-observation SEIR, fractional SEIR, constrained structure discovery.
- Rolling horizons: 1, 2, and 4 weeks.
- Interpretation: season-separated within-season robustness. This is not a direct previous-season-to-future-season transfer forecast.

Main selected-result patterns:

- `0-4 yr`: constrained structure discovery is the recommended model in 5/6 seasons, best test model in 4/6 seasons, and best rolling model in 5/6 seasons.
- `Overall`: constrained structure discovery is the recommended model in 4/6 seasons and best rolling model in 5/6 seasons; best test model is more mixed once all six model families are included.
- `>= 65 yr`: no model has a stable majority. Deterministic SEIR is the recommendation mode at only 2/6 seasons, and best-test/rolling winners are heterogeneous.

Paper sentence to use:

> In a season-separated FluSurv-NET robustness benchmark over six complete seasons and three representative age strata, constrained structure discovery is most consistently selected for pediatric and overall series, but the high-risk older-adult stratum remains heterogeneous; these results support age- and season-aware model selection rather than a single globally dominant model family.

## 5. Dengue Audit And Smoke

- Expected dengue data exists: `false`.
- Expected path: `data/raw/National_extract_V1_3.csv`.
- Dengue audit run: `no`.
- Dengue non-LLM smoke run: `no`.
- Missing-data note: `reports/dengue_missing_data_note.md`.

Dengue remains future-work or appendix-preparation only until the national extract is added, audited, and smoked.

## 6. Selected OpenAI Live Repeats

- `.env` OpenAI key-load check: `PASS`.
- Selected live repeats run: `yes`.
- Aggregate report: `reports/llm_v1_openai_selected_repeat_report.md`.
- Repeats completed in this pass: `3`.
- Series repeated: `0-4 yr`, `5-17 yr`, `>= 65 yr`.
- Total raw proposals: `112`.
- Total hard-valid proposals: `112`.
- Mean hard-valid rate: `1.000`.
- Artifact validation: all three repeat roots `PASS`.
- Leakage status: `PASS`.

Main selected-repeat patterns:

- `0-4 yr`: V1 beat V0 by selection score in `1/3` repeats; dominant selected spec was `SEIRS|fractional=0|obs=delayed_I|delay=1`.
- `5-17 yr`: V1 beat V0 by selection score in `3/3` repeats; dominant selected spec was `SEIRS|fractional=0|obs=delayed_I|delay=2`.
- `>= 65 yr`: V1 beat V0 by selection score in `3/3` repeats; dominant selected spec was `SEIRS|fractional=1|obs=delayed_I|delay=2`.
- Non-LLM reference discovery score is unavailable because the reference discovery candidate budget is unavailable. Non-LLM test and rolling deltas are descriptive MAE differences only, not matched-budget efficiency evidence.

Paper sentence to use:

> Across three controlled OpenAI live repeats on selected informative age strata, all 112 raw proposals passed hard validation and all repeat artifacts passed leakage checks. V1 improved over the V0 LLM baseline by validation/rolling selection score for `5-17 yr` and `>= 65 yr`, but not consistently for `0-4 yr`; comparisons with non-LLM discovery remain descriptive because reference discovery candidate budgets are not matched.

## 7. Paper-Safe Claims

- Multi-season FluSurv-NET data preparation, audit, and a selected season-separated benchmark have now been run.
- The safest multi-season claim is cross-season robustness of the evaluation protocol and conditional usefulness of constrained discovery, especially for `0-4 yr` and `Overall`.
- LLM-V1 live all-series freeze and selected live repeats are operational and validated, but they should be described as sometimes useful rather than globally superior.
- Budget comparisons should be descriptive unless a future diagnostic sets `efficiency_claim_allowed=true`.
- Dengue remains a planned secondary surveillance benchmark; no dengue result is available from this run.

## 8. Forbidden Claims

- Do not claim "LLM globally beats non-LLM."
- Do not claim "LLM is more efficient" while the budget diagnostic blocks efficiency claims.
- Do not claim fractional SEIR is the main contribution.
- Do not claim direct previous-season-to-future-season transfer forecasting from the season-separated benchmark.
- Do not claim the older-adult FluSurv-NET stratum has a single stable winning model.
- Do not claim the flu hospitalization SEIR mechanism directly transfers to dengue.
