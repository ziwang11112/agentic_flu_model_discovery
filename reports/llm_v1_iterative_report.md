# LLM-V1 Iterative Report

LLM-V1 adds iterative validation-feedback refinement on top of the LLM-V0 proposal layer.
It still does not make final scientific claims from mock-provider results.

Mock provider results are engineering smoke tests and should not be interpreted as evidence of LLM reasoning quality.

## Series Summary

### 0-4 yr

- V1 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=2`
- V1 selected round: `1`
- V1 best score: `0.348676`
- V1 final selected-candidate test MAE: `0.091131`
- V0 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=2`
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

### 18-49 yr

- V1 best spec: `SIR|fractional=0|obs=I`
- V1 selected round: `1`
- V1 best score: `0.260602`
- V1 final selected-candidate test MAE: `0.048017`
- V0 best spec: `SIR|fractional=0|obs=I`
- Non-LLM reference spec: `SIR|fractional=0|obs=I`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

### 5-17 yr

- V1 best spec: `SIR|fractional=0|obs=I`
- V1 selected round: `2`
- V1 best score: `0.322741`
- V1 final selected-candidate test MAE: `0.053427`
- V0 best spec: `SEIR|fractional=0|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

### 50-64 yr

- V1 best spec: `SIR|fractional=0|obs=I`
- V1 selected round: `1`
- V1 best score: `0.222214`
- V1 final selected-candidate test MAE: `0.037161`
- V0 best spec: `SIR|fractional=0|obs=I`
- Non-LLM reference spec: `SIR|fractional=0|obs=I`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

### >= 65 yr

- V1 best spec: `SEIRS|fractional=1|obs=delayed_I|delay=2`
- V1 selected round: `1`
- V1 best score: `0.568661`
- V1 final selected-candidate test MAE: `0.157595`
- V0 best spec: `SEIRS|fractional=1|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=1|obs=delayed_I|delay=2`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

### Overall

- V1 best spec: `SIR|fractional=0|obs=I`
- V1 selected round: `1`
- V1 best score: `0.317917`
- V1 final selected-candidate test MAE: `0.036967`
- V0 best spec: `SIR|fractional=0|obs=I`
- Non-LLM reference spec: `SIR|fractional=0|obs=I`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

## Refinement Improvement

- `0-4 yr`: rounds `2`, initial `0.3486759046758869`, final `0.3486759046758869`, improved `False`, early_stop `True`
- `18-49 yr`: rounds `2`, initial `0.2606019410268697`, final `0.2606019410268697`, improved `False`, early_stop `True`
- `5-17 yr`: rounds `3`, initial `0.3358605016460927`, final `0.322741082676521`, improved `True`, early_stop `True`
- `50-64 yr`: rounds `2`, initial `0.2222143655002109`, final `0.2222143655002109`, improved `False`, early_stop `True`
- `>= 65 yr`: rounds `2`, initial `0.568660507469542`, final `0.568660507469542`, improved `False`, early_stop `True`
- `Overall`: rounds `2`, initial `0.3179169862989722`, final `0.3179169862989722`, improved `False`, early_stop `True`
