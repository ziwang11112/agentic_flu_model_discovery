# LLM-V1 Iterative Report

LLM-V1 adds iterative validation-feedback refinement on top of the LLM-V0 proposal layer.
This report summarizes a live-provider run with validation/rolling-only selection and post-selection test evaluation.

Live-provider results are preliminary single-run outputs. Candidate budgets are not matched unless explicitly stated, and test metrics are reported only after validation/rolling-based candidate selection.

## Series Summary

### 0-4 yr

- V1 best spec: `SEIRS|fractional=1|obs=delayed_I|delay=1`
- V1 selected round: `1`
- V1 best score: `0.350053`
- V1 final selected-candidate test MAE: `0.089619`
- V0 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=2`
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

### 18-49 yr

- V1 best spec: `SEIR|fractional=0|obs=delayed_I|delay=1`
- V1 selected round: `1`
- V1 best score: `0.319467`
- V1 final selected-candidate test MAE: `0.050353`
- V0 best spec: `SIR|fractional=0|obs=I`
- Non-LLM reference spec: `SIR|fractional=0|obs=I`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

### 5-17 yr

- V1 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=3`
- V1 selected round: `2`
- V1 best score: `0.331397`
- V1 final selected-candidate test MAE: `0.011911`
- V0 best spec: `SEIR|fractional=0|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

### 50-64 yr

- V1 best spec: `SIR|fractional=0|obs=delayed_I|delay=1`
- V1 selected round: `3`
- V1 best score: `0.227347`
- V1 final selected-candidate test MAE: `0.037146`
- V0 best spec: `SIR|fractional=0|obs=I`
- Non-LLM reference spec: `SIR|fractional=0|obs=I`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

### >= 65 yr

- V1 best spec: `SEIRS|fractional=1|obs=delayed_I|delay=2`
- V1 selected round: `2`
- V1 best score: `0.525861`
- V1 final selected-candidate test MAE: `0.221973`
- V0 best spec: `SEIRS|fractional=1|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=1|obs=delayed_I|delay=2`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

### Overall

- V1 best spec: `SEIR|fractional=0|obs=delayed_I`
- V1 selected round: `2`
- V1 best score: `0.367364`
- V1 final selected-candidate test MAE: `0.037851`
- V0 best spec: `SIR|fractional=0|obs=I`
- Non-LLM reference spec: `SIR|fractional=0|obs=I`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

## Refinement Improvement

- `0-4 yr`: rounds `2`, initial `0.3500527555040557`, final `0.3500527555040557`, improved `False`, early_stop `True`
- `18-49 yr`: rounds `2`, initial `0.3194672453868838`, final `0.3194672453868838`, improved `False`, early_stop `True`
- `5-17 yr`: rounds `3`, initial `0.3544279881385839`, final `0.3313973624064044`, improved `True`, early_stop `True`
- `50-64 yr`: rounds `3`, initial `0.2781853697088952`, final `0.2273470540479582`, improved `True`, early_stop `False`
- `>= 65 yr`: rounds `3`, initial `0.5873098495533348`, final `0.5258611191035267`, improved `True`, early_stop `True`
- `Overall`: rounds `3`, initial `0.3719844748425127`, final `0.3673635354884154`, improved `True`, early_stop `True`
