# LLM-V1 OpenAI All-Series Freeze Report

This report summarizes the clean all-series live-provider freeze under:

`artifacts_llm_v1_openai_all_series_freeze/`

The run used `provider=openai` and preserved the same V1 protocol as the frozen mock-provider and two-series smoke runs: prompt-safe summaries, validation/rolling-only selection, hard validation before execution, and post-selection test evaluation only after the validation-selected candidate was fixed.

Live-provider results are preliminary single-run outputs. Candidate budgets are not matched, and these results should not be interpreted as evidence that LLM-V1 is globally more efficient or globally better than non-LLM discovery.

## Artifact Validation

- Series completed: `Overall`, `0-4 yr`, `5-17 yr`, `18-49 yr`, `50-64 yr`, `>= 65 yr`
- Artifact/leakage validation: PASS
- Series directories checked: 6
- Rounds checked: 15
- Files checked: 171
- Leakage status: PASS
- Missing files: none
- Invalid columns or schema failures: none
- Trace failures: none

## Candidate Validity

Across all six series, the live provider generated 71 raw proposals. Of these, 69 were schema-valid, hard-valid, and evaluated, for an aggregate hard-valid/evaluated proposal rate of 69/71 = 0.972. The only degraded round was `18-49 yr` round 2, where 2 of 4 proposals remained valid and evaluated.

This passes the main V1 live-provider engineering target: the system can obtain valid JSON, apply schema and hard validation, execute valid candidates, and write auditable round-aware artifacts without test leakage.

## Series Summary

| series | selected V1 spec | round | V1 score | V0 score | non-LLM score | refinement improved? |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Overall | `SEIR|fractional=0|obs=delayed_I|delay=1` | 1 | 0.369973 | 0.317918 | 0.317918 | no |
| 0-4 yr | `SEIRS|fractional=0|obs=I` | 2 | 0.341377 | 0.346885 | 0.344818 | yes |
| 5-17 yr | `SEIRS|fractional=0|obs=delayed_I|delay=2` | 2 | 0.288766 | 0.335852 | 0.273314 | yes |
| 18-49 yr | `SEIR|fractional=0|obs=delayed_I|delay=2` | 1 | 0.325325 | 0.250177 | 0.260602 | no |
| 50-64 yr | `SEIR|fractional=0|obs=I` | 3 | 0.266879 | 0.222208 | 0.222209 | yes |
| >= 65 yr | `SEIRS|fractional=1|obs=delayed_I|delay=1` | 1 | 0.530717 | 0.536832 | 0.493660 | no |

Lower scores are better. V1 improves over the V0 score for three of six series: `0-4 yr`, `5-17 yr`, and `>= 65 yr`. V1 improves over the non-LLM reference score only for `0-4 yr`. This means the live-provider V1 loop is operational and sometimes useful, but the non-LLM observation-aware discovery baseline remains stronger overall.

## Refinement Behavior

Refinement improved the selected validation/rolling score in three series:

- `0-4 yr`: 0.434743 -> 0.341377
- `5-17 yr`: 0.323247 -> 0.288766
- `50-64 yr`: 0.273996 -> 0.266879

The other three series stopped without improvement:

- `Overall`: selected round 1
- `18-49 yr`: selected round 1
- `>= 65 yr`: selected round 1

This is a useful result for the agentic claim: the refinement loop is not merely decorative, but it also does not reliably dominate a strong non-LLM search.

## Observation Semantics

The live provider frequently proposed delayed infectious observation. Selected V1 candidates used `delayed_I` for `Overall`, `5-17 yr`, `18-49 yr`, and `>= 65 yr`. The `0-4 yr` and `50-64 yr` selected candidates used direct `I` observation. No final selected V1 candidate used `H` or `I+H`.

This is directionally consistent with the non-LLM discovery results: explicit observation delay appears more useful in this single-season benchmark than directly observing the hospitalization compartment.

## Interpretation

The all-series live-provider freeze supports four limited conclusions:

- The OpenAI provider path works end-to-end under strict no-test-leakage constraints.
- Live V1 generates mostly valid, executable candidate structures.
- Iterative refinement can improve validation/rolling score on some age groups.
- Non-LLM observation-aware constrained discovery remains the stronger benchmark reference overall.

The current result should therefore be framed as evidence for a reliable agentic structure-refinement protocol, not as evidence that the live LLM globally beats non-LLM discovery.
