# Epidemic DSL Skill

Allowed structures:

- SIR
- SEIR
- SEIRS
- SEIHR
- SEIAR

Allowed observation maps:

- I
- H
- I+H
- delayed_I

Rules:

- H and I+H require SEIHR.
- delayed_I requires delay_weeks in {1,2,3} when used as a delayed observation.
- Non-delayed observations must have delay_weeks = 0.
- Do not invent new compartments.
- Do not output Python code.
