# LLM-V1 OpenAI Selected Repeat Report

This report aggregates three controlled live-provider LLM-V1 repeats for `0-4 yr`, `5-17 yr`, and `>= 65 yr`.

Live repeats are controlled evaluations. Candidate budgets are still not matched, and these results must not be used to claim that LLM-V1 globally beats non-LLM discovery.

The same V1 protocol is used in every repeat: OpenAI live provider, no-test-leakage guard, hard validation before execution, validation/rolling selection, and post-selection test evaluation only.

## Aggregate Validity

- Total raw proposals: `112`
- Total hard-valid proposals: `112`
- Mean hard-valid rate over all selected repeats: `1.000`
- Leakage status across repeat artifacts: `PASS`

## Structure Stability

The non-LLM score-rate column is `n/a` when the reference discovery candidate budget/score is unavailable. Non-LLM test and rolling deltas below are descriptive MAE differences, not matched-budget efficiency evidence.

| series_name | repeats | v1_over_v0_rate | v1_over_nonllm_score_rate | mean_v1_score | std_v1_score | mean_v1_minus_nonllm_test_mae | mean_v1_minus_nonllm_rolling_mae | dominant_selected_spec | mean_valid_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | 3 | 0.333 | n/a | 0.346 | 0.002 | 0.001 | 0.016 | SEIRS|fractional=0|obs=delayed_I|delay=1 | 1.000 |
| 5-17 yr | 3 | 1.000 | n/a | 0.278 | 0.019 | 0.047 | 0.014 | SEIRS|fractional=0|obs=delayed_I|delay=2 | 1.000 |
| >= 65 yr | 3 | 1.000 | n/a | 0.510 | 0.005 | 0.128 | 0.059 | SEIRS|fractional=1|obs=delayed_I|delay=2 | 1.000 |

## Per-Repeat Outputs

- `artifacts_llm_v1_openai_selected_repeats_summary\live_repeat_summary.csv`
- `artifacts_llm_v1_openai_selected_repeats_summary\live_repeat_structure_stability.csv`
- `artifacts_llm_v1_openai_selected_repeats_summary\live_repeat_validity_summary.csv`

## Interpretation Boundary

These repeats test live-provider stability on selected informative series. They do not replace the frozen all-series evaluation and do not establish broad generalization beyond the current single-season proof of concept.
The observation-aware non-LLM constrained discovery baseline remains the stronger overall reference unless repeat evidence shows otherwise under matched or explicitly analyzed candidate budgets.
