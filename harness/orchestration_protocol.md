# Orchestration Protocol

LLM-V0 uses one round only:

1. Build prompt-safe summary
2. Build semantics summary
3. Generate JSON structure proposals
4. Critic annotates proposals
5. Schema validation
6. Hard validation with existing discovery rules
7. Execute all hard-valid candidates
8. Select best candidate by validation/rolling score
9. Compute test metrics only after selection is fixed
