# Paper Draft

This directory contains a LaTeX paper scaffold focused on the current non-LLM
experimental story and the transition to the next LLM phase.

Current sections:

- `sections/introduction.tex`
- `sections/method.tex`
- `sections/experiments.tex`
- `sections/results.tex`

Main entry point:

- `main.tex`

If `latexmk` is available, compile from this directory with:

```bash
latexmk -pdf main.tex
```

The draft currently assumes figures live in the repository root artifacts directories and are referenced with relative paths such as `../artifacts_multiseed_age_robustness_observation/...`.
