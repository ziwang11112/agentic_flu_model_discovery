# agentic_flu_model_discovery

Reproducible Python benchmark for weekly influenza hospitalization-rate forecasting and constrained epidemic-model structure discovery on a FluSurv-NET export.

## What This Runs

The benchmark compares four model families on the primary FluSurv-NET series:

1. Manual deterministic SEIR
2. Manual probabilistic SEIR with Student-t observation noise
3. Manual fractional SEIR
4. Constrained EPIAGENT-style structure discovery over a small epidemic grammar

The primary series uses:

- `CATCHMENT == "Entire Network"`
- `AGE CATEGORY == "Overall"`
- `SEX CATEGORY == "Overall"`
- `RACE CATEGORY == "Overall"`
- `VIRUS TYPE CATEGORY == "Overall"`
- target column `WEEKLY RATE`

Optional age-group robustness runs are implemented behind `data.include_age_robustness` in `configs/default.yaml`.

## Numerical Notes

- All models use normalized population units with total mass near `1.0`.
- Deterministic and probabilistic baselines use weekly discrete SEIR updates.
- The fractional SEIR and fractional discovery variants use a Caputo-style L1 discrete-memory approximation.
- The discovery loop is programmatic only: propose, verify, fit, rank, refine. There is no LLM in the modeling loop.
- Discovery ranking uses rolling-origin validation across horizons `1`, `2`, and `4` weeks, plus explicit complexity penalties, an error-stability penalty, and discovery-specific parameter regularization.
- The probabilistic SEIR baseline supports both Laplace and bootstrap uncertainty; the default configs now use bootstrap intervals.

## Repository Layout

```text
agentic_flu_model_discovery/
  data/
    raw/
    processed/
  src/
    data/
    discovery/
    evaluation/
    models/
    plotting/
    utils/
  configs/
  artifacts/
  tests/
  run_experiment.py
  README.md
  requirements.txt
```

## Reproduction

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the full benchmark:

```bash
python run_experiment.py --config configs/default.yaml
```

Run the age-group robustness benchmark:

```bash
python run_experiment.py --config configs/age_robustness.yaml
```

Run the unit tests:

```bash
pytest tests -q
```

In the current shared workspace, the default `python` environment is broken outside this repo due an unrelated NumPy installation issue. The benchmark was verified locally with:

```bash
/home/zwang/miniconda3/envs/myenv2/bin/python run_experiment.py --config configs/default.yaml
/home/zwang/miniconda3/envs/myenv2/bin/python -m pytest tests -q
```

## Outputs

Primary outputs are written under `artifacts/overall/`:

- `deterministic_seir/`
- `probabilistic_seir/`
- `fractional_seir/`
- `constrained_structure_discovery/`

Each model folder contains:

- `metrics.json`
- `forecast_trace.csv`
- `rolling_origin_forecasts.csv`
- `full_series_fit.png`
- `rolling_origin.png`
- `residuals.png`

The discovery folder also contains:

- `leaderboard.csv`
- `leaderboard.png`
- `best_model_spec.json`
- `best_model_spec.yaml`
- `best_structure.png`

Processed benchmark-ready data are written to:

- `data/processed/flusurv_benchmark_series.csv`
- `data/processed/flusurv_primary_overall.csv`

Top-level aggregate outputs are written to:

- `artifacts/benchmark_leaderboard.csv`
- `artifacts/benchmark_model_summary.csv`
- `artifacts/benchmark_series_winners.csv`
- `artifacts/age_group_recommendation.csv`
- `artifacts/run_summary.json`

## Configuration

Main runtime controls live in [`configs/default.yaml`](/home/zwang/agentic_flu_model_discovery/configs/default.yaml):

- `fitting.n_restarts`: main fitting restart count
- `fitting.rolling_n_restarts`: rolling-origin restart count
- `fitting.maxiter`: optimizer iteration cap
- `evaluation.horizons`: rolling-origin horizons
- `discovery.beam_width`, `discovery.max_rounds`, `discovery.patience`
- `discovery.rolling_horizons`: horizons used for discovery-time rolling-origin model selection
- `discovery.score_*`: structure-complexity penalties used in discovery ranking
- `discovery.score_stability_weight`: rolling-origin error-variance penalty in discovery ranking
- `discovery.*_l2_weight`: discovery-time parameter regularization strengths
- `discovery.age_prior_*`: age-aware structure priors used to lightly favor simple or recurrent structures by series
- `fitting.uncertainty_method`: `laplace` or `bootstrap` for probabilistic intervals
- `fitting.bootstrap_draws`: number of bootstrap predictive draws
- `fitting.bootstrap_n_restarts`: extra restarts used inside each bootstrap refit
- `data.include_age_robustness`: optional age-group reruns

## Tests

The test suite covers:

- data filtering
- time sorting
- mass conservation checks
- deterministic SEIR forward simulation
- discovery-rule validation
