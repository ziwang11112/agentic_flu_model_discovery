# FluSurv-NET Multi-Season Smoke Plan

## Data Placement

Download a FluSurv-NET custom CSV containing all seasons intended for the benchmark and place it at:

`data/raw/flusurvnet_multiseason_full.csv`

The expected columns match the current single-season custom download, including `YEAR`, `YEAR.1`, `WEEK`, demographic category columns, and `WEEKLY RATE`.

## Audit Command

Run:

```bash
python scripts/audit_flusurvnet_multiseason.py \
  --csv data/raw/flusurvnet_multiseason_full.csv \
  --output-dir data/processed_flusurvnet_multiseason \
  --report reports/flusurvnet_multiseason_audit.md
```

The audit writes:

- `reports/flusurvnet_multiseason_audit.md`
- `data/processed_flusurvnet_multiseason/season_series_catalog.csv`
- `data/processed_flusurvnet_multiseason/recommended_completed_seasons.csv`

## Audit Checks

The audit reports row counts, available seasons, min/max week ranges, observed and expected weeks by season and age group, missing weeks, duplicate season/week/age rows, demographic category coverage, virus type coverage, and whether the benchmark age groups are all present.

The benchmark coverage checks use `Entire Network`, `Overall` sex, `Overall` race, `Overall` virus type, and the `Overall` plus five age-specific groups. Missing weeks are flagged explicitly; they are not interpolated.

## Completed-Season Use

Main experiments should use completed seasons only. The recommended split keeps the latest completed season for test, the previous completed season for validation when available, and earlier completed seasons for training. Current-season data is treated as preliminary and should only be used in an explicitly labeled preliminary experiment.

## Pooled-Mode Caveat

`season_mode=pooled` concatenates selected seasons into one chronological sequence. That mode is acceptable for smoke tests and descriptive checks, but it should not be used for paper-level generalization claims. For paper claims, prefer `season_mode=separate` or an explicit season-level train/validation/test design using completed seasons.

## Why This Addresses The Limitation

The current paper evaluates a single-season proof of concept. The multi-season loader and audit layer will let the benchmark train, validate, and test across distinct flu seasons, making it possible to measure generalization across years instead of only within one season trajectory.
