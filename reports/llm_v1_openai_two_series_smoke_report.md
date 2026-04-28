# LLM-V1 Iterative Report

LLM-V1 adds iterative validation-feedback refinement on top of the LLM-V0 proposal layer.
This report summarizes a live-provider run with validation/rolling-only selection and post-selection test evaluation.

Live-provider results are preliminary single-run outputs. Candidate budgets are not matched unless explicitly stated, and test metrics are reported only after validation/rolling-based candidate selection.

## Series Summary

### 5-17 yr

- V1 best spec: `SEIRS|fractional=0|obs=delayed_I|delay=1`
- V1 selected round: `2`
- V1 best score: `0.265873`
- V1 final selected-candidate test MAE: `0.004371`
- V0 best spec: `SEIR|fractional=0|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=0|obs=I`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

### >= 65 yr

- V1 best spec: `SEIRS|fractional=1|obs=delayed_I|delay=1`
- V1 selected round: `1`
- V1 best score: `0.508230`
- V1 final selected-candidate test MAE: `0.252573`
- V0 best spec: `SEIRS|fractional=1|obs=I`
- Non-LLM reference spec: `SEIRS|fractional=1|obs=delayed_I|delay=2`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.

## Refinement Improvement

- `5-17 yr`: rounds `3`, initial `0.3110057666524671`, final `0.2658734727840189`, improved `True`, early_stop `True`
- `>= 65 yr`: rounds `2`, initial `0.5082302679235179`, final `0.5082302679235179`, improved `False`, early_stop `True`
