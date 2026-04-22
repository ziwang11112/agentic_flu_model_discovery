# No Test Leakage Skill

Never include test-derived fields in LLM prompts.

Banned examples:

- test_policy_model
- best_test_model
- test_mae
- test_rmse
- test_smape
- benchmark_series_winners
- final test winner
- held-out test winner

Allowed examples:

- training summary
- validation summary
- rolling-validation summary
- allowed grammar
- static surveillance semantics
