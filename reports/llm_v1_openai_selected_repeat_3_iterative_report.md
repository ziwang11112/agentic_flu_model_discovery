# LLM-V1 Iterative Report

LLM-V1 adds iterative validation-feedback refinement on top of the LLM-V0 proposal layer.
This report summarizes a live-provider run with validation/rolling-only selection and post-selection test evaluation.

Live-provider results are preliminary single-run outputs. Candidate budgets are not matched unless explicitly stated, and test metrics are reported only after validation/rolling-based candidate selection.

## Series Summary

### 0-4 yr

- V1 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=1`
- V1 selected round: `2`
- V1 best score: `0.343078`
- V1 final selected-candidate test MAE: `0.091128`
- V0 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=2`
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Candidate budget note: Reference discovery candidate budget unavailable.

### 5-17 yr

- V1 best spec: `SEIRS|fractional=0|obs=I`
- V1 selected round: `3`
- V1 best score: `0.256262`
- V1 final selected-candidate test MAE: `0.071736`
- V0 best spec: `SEIR|fractional=0|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Candidate budget note: Reference discovery candidate budget unavailable.

### >= 65 yr

- V1 best spec: `SEIRS|fractional=1|obs=delayed_I|delay=2`
- V1 selected round: `2`
- V1 best score: `0.506354`
- V1 final selected-candidate test MAE: `0.256501`
- V0 best spec: `SEIRS|fractional=1|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=1|obs=delayed_I|delay=2`
- Candidate budget note: Reference discovery candidate budget unavailable.

## Refinement Improvement

- `0-4 yr`: rounds `3`, initial `0.3497651938865062`, final `0.3430781275555657`, improved `True`, early_stop `True`
- `5-17 yr`: rounds `3`, initial `0.3589864435600685`, final `0.2562622197187475`, improved `True`, early_stop `False`
- `>= 65 yr`: rounds `3`, initial `0.7053093513002403`, final `0.5063536508184849`, improved `True`, early_stop `True`
