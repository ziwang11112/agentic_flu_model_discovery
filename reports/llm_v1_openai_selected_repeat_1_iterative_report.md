# LLM-V1 Iterative Report

LLM-V1 adds iterative validation-feedback refinement on top of the LLM-V0 proposal layer.
This report summarizes a live-provider run with validation/rolling-only selection and post-selection test evaluation.

Live-provider results are preliminary single-run outputs. Candidate budgets are not matched unless explicitly stated, and test metrics are reported only after validation/rolling-based candidate selection.

## Series Summary

### 0-4 yr

- V1 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=1`
- V1 selected round: `2`
- V1 best score: `0.347111`
- V1 final selected-candidate test MAE: `0.091118`
- V0 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=2`
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Candidate budget note: Reference discovery candidate budget unavailable.

### 5-17 yr

- V1 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=2`
- V1 selected round: `1`
- V1 best score: `0.282888`
- V1 final selected-candidate test MAE: `0.081809`
- V0 best spec: `SEIR|fractional=0|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Candidate budget note: Reference discovery candidate budget unavailable.

### >= 65 yr

- V1 best spec: `SEIRS|fractional=1|obs=delayed_I`
- V1 selected round: `3`
- V1 best score: `0.515838`
- V1 final selected-candidate test MAE: `0.247663`
- V0 best spec: `SEIRS|fractional=1|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=1|obs=delayed_I|delay=2`
- Candidate budget note: Reference discovery candidate budget unavailable.

## Refinement Improvement

- `0-4 yr`: rounds `3`, initial `0.3491701172037518`, final `0.3471105234216841`, improved `True`, early_stop `True`
- `5-17 yr`: rounds `2`, initial `0.2828882526605073`, final `0.2828882526605073`, improved `False`, early_stop `True`
- `>= 65 yr`: rounds `3`, initial `0.5745554277231055`, final `0.5158384610624661`, improved `True`, early_stop `False`
