# LLM-V1 Iterative Report

LLM-V1 adds iterative validation-feedback refinement on top of the LLM-V0 proposal layer.
This report summarizes a live-provider run with validation/rolling-only selection and post-selection test evaluation.

Live-provider results are preliminary single-run outputs. Candidate budgets are not matched unless explicitly stated, and test metrics are reported only after validation/rolling-based candidate selection.

## Series Summary

### 0-4 yr

- V1 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=2`
- V1 selected round: `1`
- V1 best score: `0.346891`
- V1 final selected-candidate test MAE: `0.091124`
- V0 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=2`
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Candidate budget note: Reference discovery candidate budget unavailable.

### 5-17 yr

- V1 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=2`
- V1 selected round: `2`
- V1 best score: `0.293479`
- V1 final selected-candidate test MAE: `0.007435`
- V0 best spec: `SEIR|fractional=0|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Candidate budget note: Reference discovery candidate budget unavailable.

### >= 65 yr

- V1 best spec: `SEIRS|fractional=1|obs=delayed_I|delay=2`
- V1 selected round: `1`
- V1 best score: `0.506413`
- V1 final selected-candidate test MAE: `0.260029`
- V0 best spec: `SEIRS|fractional=1|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=1|obs=delayed_I|delay=2`
- Candidate budget note: Reference discovery candidate budget unavailable.

## Refinement Improvement

- `0-4 yr`: rounds `2`, initial `0.346890822019625`, final `0.346890822019625`, improved `False`, early_stop `True`
- `5-17 yr`: rounds `3`, initial `0.3081525762553898`, final `0.2934792795548411`, improved `True`, early_stop `True`
- `>= 65 yr`: rounds `2`, initial `0.5064129126973504`, final `0.5064129126973504`, improved `False`, early_stop `True`
