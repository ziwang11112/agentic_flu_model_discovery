# LLM-vs-nonLLM Budget Diagnostic

This diagnostic checks whether candidate-efficiency claims are supported under fixed candidate budgets `K in {4, 8, 12, 16}`.

## Claim Status

- Candidate-efficiency claims allowed: `false`
- No candidate-efficiency claim is supported by these artifacts.
- Reason: LLM and non-LLM candidate budgets/order are not matched with comparable evaluation order metadata.

## Descriptive Candidate Counts

- LLM evaluated fewer candidates than non-LLM in `6` series.
- LLM evaluated more candidates than non-LLM in `0` series.
- LLM evaluated the same number of candidates as non-LLM in `0` series.
- Candidate count relation is unknown in `0` series.

| series_name | llm_candidates | nonllm_candidates | relation |
| --- | --- | --- | --- |
| 0-4 yr | 14 | 24 | fewer |
| 18-49 yr | 7 | 23.8 | fewer |
| 5-17 yr | 13 | 24.6 | fewer |
| 50-64 yr | 13 | 21 | fewer |
| >= 65 yr | 12 | 27 | fewer |
| Overall | 10 | 25.2 | fewer |

## Budget-Matched Rows

| series_name | K | llm_best_score_at_k | nonllm_best_score_at_k | llm_better_at_k | order_matched | efficiency_claim_allowed |
| --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | 4 | 0.435 |  |  | False | False |
| 0-4 yr | 8 | 0.345 |  |  | False | False |
| 0-4 yr | 12 | 0.341 |  |  | False | False |
| 0-4 yr | 16 |  |  |  | False | False |
| 18-49 yr | 4 | 0.325 |  |  | False | False |
| 18-49 yr | 8 |  |  |  | False | False |
| 18-49 yr | 12 |  |  |  | False | False |
| 18-49 yr | 16 |  |  |  | False | False |
| 5-17 yr | 4 | 0.323 |  |  | False | False |
| 5-17 yr | 8 | 0.323 |  |  | False | False |
| 5-17 yr | 12 | 0.289 |  |  | False | False |
| 5-17 yr | 16 |  |  |  | False | False |
| 50-64 yr | 4 | 0.274 |  |  | False | False |
| 50-64 yr | 8 | 0.274 |  |  | False | False |
| 50-64 yr | 12 | 0.267 |  |  | False | False |
| 50-64 yr | 16 |  |  |  | False | False |
| >= 65 yr | 4 | 0.531 |  |  | False | False |
| >= 65 yr | 8 | 0.531 |  |  | False | False |
| >= 65 yr | 12 | 0.531 |  |  | False | False |
| >= 65 yr | 16 |  |  |  | False | False |
| Overall | 4 | 0.370 |  |  | False | False |
| Overall | 8 | 0.370 |  |  | False | False |
| Overall | 12 |  |  |  | False | False |
| Overall | 16 |  |  |  | False | False |

## Why Claims Are Blocked

- `24` rows: Non-LLM candidate order unavailable; descriptive candidate counts only; no candidate-efficiency claim is supported.

## Caveat

The comparison is unmatched. Report only descriptive candidate counts and selected-candidate outcomes; do not claim candidate efficiency.
