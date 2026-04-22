# LLM-V0 Report

LLM-V0 is a proposal-only layer.
It does not perform iterative refinement.
It does not make final scientific claims from mock-provider results.
It is intended to validate schema, leakage guards, hard validation, candidate execution, and comparison against non-LLM discovery.

Mock provider results are engineering smoke tests and should not be interpreted as evidence of LLM reasoning quality.

## Series Summary

### 0-4 yr

- LLM best spec: `SEIRS|fractional=0|obs=delayed_I|delay=2`
- LLM validation/rolling score: `0.346885`
- LLM selected-candidate test MAE: `0.107255`
- Non-LLM reference method: `constrained_structure_discovery`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.
- Objective-aware reference note: Test and rolling objectives agree on constrained_structure_discovery within the practical tie threshold.

### 18-49 yr

- LLM best spec: `SIR|fractional=0|obs=I`
- LLM validation/rolling score: `0.250177`
- LLM selected-candidate test MAE: `0.048017`
- Non-LLM reference method: `constrained_structure_discovery`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.
- Objective-aware reference note: Test and rolling objectives agree on deterministic_seir within the practical tie threshold.

### 5-17 yr

- LLM best spec: `SEIR|fractional=0|obs=I`
- LLM validation/rolling score: `0.335852`
- LLM selected-candidate test MAE: `0.043357`
- Non-LLM reference method: `constrained_structure_discovery`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.
- Objective-aware reference note: Use constrained_structure_discovery for held-out test MAE and probabilistic_seir for rolling-origin stability.

### 50-64 yr

- LLM best spec: `SIR|fractional=0|obs=I`
- LLM validation/rolling score: `0.222208`
- LLM selected-candidate test MAE: `0.037161`
- Non-LLM reference method: `constrained_structure_discovery`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.
- Objective-aware reference note: Test and rolling objectives differ, but constrained_structure_discovery is practically tied for both and is the simplest shared compromise.

### >= 65 yr

- LLM best spec: `SEIRS|fractional=1|obs=I`
- LLM validation/rolling score: `0.536832`
- LLM selected-candidate test MAE: `0.161342`
- Non-LLM reference method: `constrained_structure_discovery`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.
- Objective-aware reference note: Use deterministic_seir for held-out test MAE and constrained_structure_discovery for rolling-origin stability.

### Overall

- LLM best spec: `SIR|fractional=0|obs=I`
- LLM validation/rolling score: `0.317918`
- LLM selected-candidate test MAE: `0.036967`
- Non-LLM reference method: `constrained_structure_discovery`
- Candidate budget note: Budgets not matched; do not interpret as an efficiency claim.
- Objective-aware reference note: Test and rolling objectives differ, but deterministic_seir is practically tied for both and is the simplest shared compromise.
