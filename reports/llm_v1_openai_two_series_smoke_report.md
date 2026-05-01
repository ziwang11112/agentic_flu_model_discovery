# LLM-V1 OpenAI Two-Series Smoke Report

This report summarizes the clean two-series live-provider smoke run under:

`artifacts_llm_v1_openai_two_series_smoke/`

The run used `provider=openai` and preserved the same V1 protocol as the frozen mock-provider run: prompt-safe summaries, validation/rolling-only selection, hard validation before execution, and post-selection test evaluation only after the validation-selected candidate was fixed.

Live-provider results are preliminary single-run outputs. Candidate budgets are not matched, and these results should not be interpreted as evidence that LLM-V1 is globally more efficient or globally better than non-LLM discovery.

## Artifact Validation

- Series completed: `5-17 yr`, `>= 65 yr`
- Artifact/leakage validation: PASS
- Series directories checked: 2
- Rounds checked: 5
- Files checked: 61
- Leakage status: PASS
- Round-level leaderboards contain no test-metric columns.
- Proposal audits, prompts, analyst traces, and refinement traces passed the banned-term leakage guard.

## Series Summary

### 5-17 yr

- Proposals: 15 raw, 15 schema-valid, 15 hard-valid, 15 evaluated
- Valid proposal rate: 1.000
- Selected V1 spec: `SEIRS|fractional=0|obs=delayed_I|delay=1`
- Selected round: 2
- V1 score: 0.265873
- V1 validation MAE: 0.245400
- V1 rolling mean MAE: 0.058201
- Post-selection test MAE: 0.004371
- V0 best spec: `SEIR|fractional=0|obs=I`
- V0 score: 0.335852
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Non-LLM score: 0.273314
- Refinement improved after round 1: yes

For this series, live V1 improved the validation/rolling score relative to both the V0 one-shot reference and the non-LLM reference score. The selected candidate also uses a delayed infectious observation map, which is semantically aligned with a hospitalization-rate target. This is the strongest positive smoke-test result, but it remains a two-series live-provider result rather than an all-series claim.

### >= 65 yr

- Proposals: 8 raw, 8 schema-valid, 8 hard-valid, 8 evaluated
- Valid proposal rate: 1.000
- Selected V1 spec: `SEIRS|fractional=1|obs=delayed_I|delay=1`
- Selected round: 1
- V1 score: 0.508230
- V1 validation MAE: 0.386864
- V1 rolling mean MAE: 0.236946
- Post-selection test MAE: 0.252573
- V0 best spec: `SEIRS|fractional=1|obs=I`
- V0 score: 0.536832
- Non-LLM reference spec: `SEIRS|fractional=1|obs=delayed_I|delay=2`
- Non-LLM score: 0.493660
- Refinement improved after round 1: no

For this series, live V1 improved over the V0 one-shot reference score but did not improve over the non-LLM discovery reference. The selected structure is still semantically plausible and close to the non-LLM reference: both are fractional SEIRS models with delayed infectious observation, differing only in delay length.

## Interpretation

The two-series smoke run supports three limited conclusions:

- The live provider can produce strict, hard-valid JSON proposals under the current leakage guard.
- The existing executor can evaluate live-provider proposals without changing non-LLM benchmark code.
- Iterative refinement can improve validation/rolling score in at least one difficult series (`5-17 yr`).

It does not support a global scientific claim that LLM-V1 beats non-LLM discovery. The next required step for paper-level live-provider evidence is an all-series live-provider freeze in a fresh artifact root, followed by the same artifact/leakage validation.
