# LLM-V1 Experiment Protocol

## Scope

This document defines the intended comparison protocol for the LLM-guided structure-search layer.
LLM-V0 is a proposal-only engineering baseline.
LLM-V1 adds iterative refinement over validation and rolling feedback.
The non-LLM control is the observation-aware constrained structure-discovery benchmark already implemented in the repository.

The current repository state supports:
- `provider=mock` for engineering validation
- `provider=openai` for controlled live-provider smoke or evaluation runs
- V0 proposal-only comparison
- V1 iterative refinement comparison

It now includes a validated all-series live-provider freeze.
That freeze supports feasibility and protocol claims about live LLM-V1 orchestration, but it should not be framed as a global performance win over non-LLM discovery because the non-LLM reference remains stronger on most series.

## Comparison Design

The primary design is a three-way comparison:

1. **LLM-V0**
   - proposal-only
   - one round
   - proposer -> critic -> hard validator -> executor

2. **LLM-V1**
   - iterative refinement
   - round 1: summary -> semantics -> proposer -> critic -> hard validator -> executor
   - round 2+: analyst -> bounded refinement proposals -> critic -> hard validator -> executor
   - early stopping on validation/rolling score

3. **Non-LLM constrained discovery**
   - observation-aware constrained search
   - same mechanistic DSL
   - same numerical executor family
   - same validation/rolling-oriented selection principle

The comparison is intended to answer:
- whether an agentic refinement loop produces cleaner proposal traces than one-shot proposal-only behavior,
- whether it reaches better validation-selected candidates under the same hard mechanistic rules,
- whether it proposes semantically aligned observation structures,
- and whether it does so without violating no-test-leakage constraints.

## Metrics

The comparison should report the following metrics.

### Search quality

- **valid proposal rate**
  - fraction of raw proposals that become hard-valid candidates
- **candidate efficiency**
  - number of evaluated candidates relative to the reference non-LLM search budget
  - no efficiency claim should be made unless the comparison is explicitly budget-matched
- **best validation score**
  - best composite validation/rolling discovery score achieved in the run

### Forecast-oriented validation

- **rolling validation MAE**
  - mean rolling-origin validation MAE for the selected candidate
- **selected-candidate test MAE after validation selection**
  - held-out test MAE computed only after the final candidate is fixed by validation/rolling criteria

### Semantic behavior

- **semantic alignment**
  - whether proposed observation structures are consistent with the hospitalization-rate target
  - example questions:
    - does the agent propose `delayed_I` when delay semantics are plausible?
    - does it try `H` or `I+H` when hospitalization semantics justify them?
    - does the critic warn when `H` is likely weakly identifiable?

## Leakage Guard

All LLM-facing inputs must be prompt-safe.

The proposer, critic, and analyst must not see:
- `test_mae`
- `test_rmse`
- `test_smape`
- `test_policy_model`
- `best_test_model`
- `benchmark_series_winners`
- any held-out test winner or test-derived recommendation

Allowed LLM-facing information includes:
- series identity
- training summary
- validation summary
- rolling validation summary
- surveillance semantics
- current non-test discovery structure modes
- previous-round validation/rolling feedback

The protocol therefore distinguishes between:
- **prompt-safe summaries** for agent inputs
- **report summaries** for post-selection evaluation and final write-up

## Provider Distinction

### Mock provider

`provider=mock` is **engineering validation** only.
It is used to verify:
- JSON schema handling
- prompt construction
- leakage guards
- hard validation
- executor reuse
- round-aware artifact generation
- report writing

Mock-provider outputs may be used to confirm that the orchestration works end-to-end, but they must not be used as scientific evidence of LLM reasoning quality.

### Live provider

An external API-backed configuration such as `provider=openai` is the **scientific evaluation** setting.
Only that setting should be used for claims about:
- whether LLM reasoning improves proposal quality,
- whether iterative refinement improves candidate selection,
- whether semantic proposal quality is meaningfully better than non-LLM search under matched conditions.

However, live-provider results should not be treated as frozen scientific evidence until the run is validated, its artifacts are checked, and the exact provider/model configuration is recorded alongside the benchmark outputs.

The current all-series OpenAI freeze satisfies this protocol for all six benchmark series.
It is evidence that live-provider orchestration, strict JSON parsing, hard validation, and artifact leakage checks work in practice.
It is not evidence of global LLM superiority over the non-LLM constrained discovery baseline.

## Reporting Language

The following sentence should appear anywhere mock-provider V1 results are discussed in the paper draft:

> Mock-provider V1 validates the orchestration and artifact protocol; live-provider evaluation is required for scientific claims about LLM reasoning.

This sentence is mandatory because the current V1 implementation is intended to validate infrastructure, not to establish a scientific performance claim.
