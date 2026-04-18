# agentic_flu_model_discovery

Reproducible Python benchmark for weekly influenza hospitalization-rate forecasting and constrained epidemic-model structure discovery from a FluSurv-NET CSV export.

This repository implements a proof-of-concept forecasting benchmark that compares standard hand-specified compartmental models against a constrained, programmatic structure-discovery loop. The goal is not to build a full agent-based simulator or use an LLM inside model fitting. Instead, the project asks a narrower and more practical question:

Can a reproducible propose-fit-verify-refine search over a small epidemic-model grammar discover useful structure for short-horizon weekly hospitalization-rate forecasting?

## Why This Repository Exists

Epidemic forecasting projects often face a tradeoff between simple, interpretable compartmental models and highly flexible models that are difficult to audit or reproduce. This project is designed to sit in between those extremes.

It provides:

- a clean, end-to-end benchmark for weekly FluSurv-NET hospitalization-rate forecasting
- direct comparisons among deterministic, probabilistic, fractional, and discovered epidemic models
- a constrained "agentic" structure-discovery loop with explicit biological validity checks
- reproducible outputs, plots, metrics, and tests that can be rerun from one command

The repository is intentionally scoped as a single-season proof of concept. It is meant to be extended later to multiple seasons, multiple catchments, or richer hierarchical settings.

## What "Agentic" Means Here

In this repository, "agentic" does not mean an LLM is choosing equations during training.

The agentic component is a deterministic program loop:

1. propose a candidate epidemic structure
2. verify the candidate against explicit structural rules
3. fit the candidate to data
4. score the candidate on validation-time forecasting behavior
5. keep the strongest candidates in a beam
6. refine by exploring local structural edits

This gives a search process that is transparent, reproducible, and auditable.

## Benchmark Overview

The benchmark compares four model families:

1. `deterministic_seir`
2. `probabilistic_seir`
3. `fractional_seir`
4. `constrained_structure_discovery`

The core forecasting task is weekly hospitalization-rate prediction from a FluSurv-NET CSV using chronological train, validation, and test splits plus rolling-origin forecasting at horizons 1, 2, and 4 weeks.

### Primary Research Question

Does constrained epidemic-model structure discovery provide useful forecasting gains relative to strong manual baselines, and if so, for which age groups and under what stability criteria?

### Main Design Principles

- normalized population units with total mass near `1.0`
- latent epidemic states with a learned observation scaling coefficient `rho`
- non-negativity constraints for compartments
- mass-conservation penalties for models without deaths
- multiple random restarts for fitting
- fixed global seed `42`
- artifact-first workflow with all outputs written to disk

## Data Pipeline

The input data are expected to be a FluSurv-NET CSV export.

The benchmark performs the following preprocessing steps:

- reads the file with `skiprows=2`
- drops disclaimer/footer rows with missing `WEEK` or missing `YEAR.1`
- sorts rows by `YEAR.1` and then `WEEK`
- creates a continuous integer time index `t = 0, 1, ..., T-1`

### Primary Series Filter

The main benchmark series uses:

- `CATCHMENT == "Entire Network"`
- `AGE CATEGORY == "Overall"`
- `SEX CATEGORY == "Overall"`
- `RACE CATEGORY == "Overall"`
- `VIRUS TYPE CATEGORY == "Overall"`
- target column `WEEKLY RATE`

### Optional Age-Group Robustness

The same pipeline is also implemented for:

- `0-4 yr`
- `5-17 yr`
- `18-49 yr`
- `50-64 yr`
- `>= 65 yr`

while keeping the remaining categories at `Overall`.

## Models

### 1. Manual Deterministic SEIR

This is the baseline compartmental model with weekly discrete updates over `S`, `E`, `I`, and `R`.

The transmission rate is seasonal:

`beta_t = softplus(b0 + b1*sin(2*pi*t/52) + b2*cos(2*pi*t/52))`

The observation model is:

`y_hat[t] = rho * I[t]`

Fitting uses mean squared error plus penalties for negative states and mass-conservation violations.

### 2. Manual Probabilistic SEIR

This model shares the same latent SEIR dynamics as the deterministic baseline but uses a Student-t observation model:

`y[t] ~ StudentT(df=5, loc=rho * I[t], scale=s)`

The implementation fits by MAP estimation and then generates predictive intervals. The code supports both:

- Laplace approximation
- bootstrap predictive uncertainty

The default configs now use bootstrap intervals.

### 3. Manual Fractional SEIR

This model keeps the same `S`, `E`, `I`, `R` compartments but adds a shared fractional order `alpha` constrained to `0.7 <= alpha <= 1.0`.

The current implementation uses a Caputo-style L1 discrete-memory approximation as a stable numerical baseline.

### 4. Constrained Structure Discovery

This is the main experimental component.

The search space includes:

- `SIR`
- `SEIR`
- `SEIRS`
- `SEIHR`
- `SEIAR`

with toggles for:

- fractional on or off
- observation map `rho*I` or `rho*(I+H)` when `H` exists

Candidate structures are filtered through explicit validity rules such as:

- infection must originate from `S`
- infectious-like compartments must eventually lead to `R`
- no isolated compartments
- no biologically nonsensical self-loops
- maximum of 5 compartments
- approximate conservation of total mass

The discovery score is built from:

- rolling-origin validation performance
- model-complexity penalties
- a rolling-error stability penalty
- age-aware structure priors

The result is a controlled search that favors structures that are not only accurate on one split, but also reasonably stable.

## Evaluation Protocol

### Chronological Split

Each series is partitioned in order:

- first `60%` for train
- next `20%` for validation
- final `20%` for test

### Rolling-Origin Forecasting

The benchmark also evaluates expanding-window forecasts for:

- 1 week ahead
- 2 weeks ahead
- 4 weeks ahead

### Point Forecast Metrics

- MAE
- RMSE
- sMAPE

### Probabilistic Metrics

- negative log-likelihood
- 80% interval coverage
- 95% interval coverage
- average interval width

## Current Headline Results

The repository already contains benchmark outputs from the current proof-of-concept season.

### Overall Series

From [`artifacts/benchmark_leaderboard.csv`](artifacts/benchmark_leaderboard.csv):

| Model | Test MAE | Test RMSE | Free Params | Compartments |
| --- | ---: | ---: | ---: | ---: |
| `fractional_seir` | `0.03511` | `0.04106` | 9 | 4 |
| `deterministic_seir` | `0.03523` | `0.04128` | 8 | 4 |
| `probabilistic_seir` | `0.03682` | `0.04443` | 9 | 4 |
| `constrained_structure_discovery` | `0.03697` | `0.04466` | 6 | 3 |

Interpretation:

- the main series is still well served by a strong manual baseline
- discovery is competitive, but not the top performer on this held-out overall split
- the fractional baseline can be very strong on the final overall test split, but was less stable across rolling-origin validation

### Age-Group Robustness

From [`artifacts_age_robustness/benchmark_series_winners.csv`](artifacts_age_robustness/benchmark_series_winners.csv) and [`artifacts_age_robustness/age_group_recommendation.csv`](artifacts_age_robustness/age_group_recommendation.csv):

| Series | Best Test Model | Best Rolling Model | Recommended Model | Decision Type |
| --- | --- | --- | --- | --- |
| `Overall` | `deterministic_seir` | `deterministic_seir` | `deterministic_seir` | `consensus` |
| `0-4 yr` | `constrained_structure_discovery` | `constrained_structure_discovery` | `constrained_structure_discovery` | `consensus` |
| `5-17 yr` | `constrained_structure_discovery` | `probabilistic_seir` | `probabilistic_seir` | `stability_preferred` |
| `18-49 yr` | `deterministic_seir` | `deterministic_seir` | `deterministic_seir` | `consensus` |
| `50-64 yr` | `constrained_structure_discovery` | `constrained_structure_discovery` | `constrained_structure_discovery` | `consensus` |
| `>= 65 yr` | `deterministic_seir` | `constrained_structure_discovery` | `deterministic_seir` | `test_preferred` |

This is the most important empirical takeaway so far:

- discovery is not a universal replacement for hand-built models
- discovery is clearly useful for some age groups
- the best strategy is age-aware model selection rather than forcing a single model family to win everywhere

### Practical Summary of the Results

At the current stage, the repository supports the following conclusion:

Constrained structure discovery already shows meaningful value in selected age groups, but the strongest next step is age-aware model selection and stability-aware discovery, not simply increasing model complexity everywhere.

## Repository Layout

```text
agentic_flu_model_discovery/
  data/
    raw/
    processed/
    processed_age_robustness/
  src/
    data/
    discovery/
    evaluation/
    models/
    plotting/
    utils/
  configs/
  artifacts/
  artifacts_age_robustness/
  tests/
  run_experiment.py
  README.md
  requirements.txt
```

## Installation

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

If you are using the shared environment from development, the verified interpreter was:

```bash
/home/zwang/miniconda3/envs/myenv2/bin/python
```

## Reproducing the Benchmark

### Run the Main Benchmark

```bash
python run_experiment.py --config configs/default.yaml
```

### Run the Age-Group Robustness Benchmark

```bash
python run_experiment.py --config configs/age_robustness.yaml
```

### Run with Explicit Logging

```bash
python run_experiment.py --config configs/age_robustness.yaml --log-level INFO
```

### Run the Unit Tests

```bash
pytest tests -q
```

### Verified Commands in the Shared Workspace

```bash
/home/zwang/miniconda3/envs/myenv2/bin/python run_experiment.py --config configs/default.yaml
/home/zwang/miniconda3/envs/myenv2/bin/python run_experiment.py --config configs/age_robustness.yaml --log-level INFO
/home/zwang/miniconda3/envs/myenv2/bin/python -m pytest tests -q
```

## Outputs

### Per-Model Outputs

Each fitted model writes a directory containing:

- `metrics.json`
- `forecast_trace.csv`
- `rolling_origin_forecasts.csv`
- `full_series_fit.png`
- `rolling_origin.png`
- `residuals.png`

The discovery model also writes:

- `leaderboard.csv`
- `leaderboard.png`
- `best_model_spec.json`
- `best_model_spec.yaml`
- `best_structure.png`

### Top-Level Summary Outputs

The repository writes benchmark-wide summaries such as:

- `artifacts/benchmark_leaderboard.csv`
- `artifacts/benchmark_model_summary.csv`
- `artifacts/benchmark_series_winners.csv`
- `artifacts/age_group_recommendation.csv`
- `artifacts/run_summary.json`

and for age robustness:

- `artifacts_age_robustness/benchmark_leaderboard.csv`
- `artifacts_age_robustness/benchmark_model_summary.csv`
- `artifacts_age_robustness/benchmark_series_winners.csv`
- `artifacts_age_robustness/age_group_recommendation.csv`
- `artifacts_age_robustness/benchmark_test_mae_heatmap.png`
- `artifacts_age_robustness/benchmark_rolling_mae_heatmap.png`

## Configuration Guide

Main runtime controls live in [`configs/default.yaml`](configs/default.yaml) and [`configs/age_robustness.yaml`](configs/age_robustness.yaml).

Important knobs include:

- `fitting.n_restarts`: number of optimization restarts for the main fit
- `fitting.rolling_n_restarts`: restarts used during rolling-origin refits
- `fitting.maxiter`: optimizer iteration cap
- `fitting.uncertainty_method`: `laplace` or `bootstrap`
- `fitting.bootstrap_draws`: number of predictive bootstrap draws
- `fitting.bootstrap_n_restarts`: additional optimization restarts inside each bootstrap refit
- `evaluation.horizons`: rolling-origin horizons used for standard reporting
- `discovery.beam_width`: beam size in structure search
- `discovery.max_rounds`: maximum propose-fit-verify-refine rounds
- `discovery.patience`: early-stopping patience
- `discovery.rolling_horizons`: horizons used during discovery-time model ranking
- `discovery.score_param_weight`: penalty on the number of free parameters
- `discovery.score_compartment_weight`: penalty on the number of compartments
- `discovery.score_stability_weight`: penalty on unstable rolling-origin error behavior
- `discovery.age_prior_*`: light age-group priors over simpler, recurrent, or fractional structures
- `data.include_age_robustness`: toggle for rerunning all age-specific series

## Testing

The test suite currently covers:

- data filtering
- time sorting
- mass conservation checks
- deterministic SEIR forward simulation
- discovery-rule validation
- discovery scoring helpers
- reporting outputs
- probabilistic bootstrap uncertainty shape checks

## Limitations

This repository is intentionally narrow in scope.

Current limitations include:

- only one uploaded season is used in the current proof-of-concept benchmark
- the work does not establish broad epidemiological generalization
- discovery is still based on a small grammar rather than a large mechanistic search space
- the probabilistic model is useful but not yet the strongest point-forecast baseline
- fractional dynamics help in some settings but are not yet a universally stable winner

## Recommended Next Steps

The most valuable next extensions are:

- multi-season evaluation
- shared cross-age priors or hierarchical fitting
- stronger stability-aware discovery objectives
- calibration-focused probabilistic diagnostics
- broader grammar extensions with still-auditable biological constraints

## Reproducibility Notes

- global random seed is fixed at `42`
- all benchmark artifacts are written to disk
- the discovery loop is deterministic conditional on config and seed
- local testing in the shared workspace passed with `pytest`

## Citation and Use

If you reuse this repository, please cite the project URL and describe it as a proof-of-concept benchmark for constrained epidemic-model structure discovery on FluSurv-NET weekly hospitalization-rate forecasting.
