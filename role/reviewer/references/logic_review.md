# Logic And Evidence Review

Review current claims against current evidence.

## Questions

- Does the answer address the actual task?
- Do mathematical claims follow from assumptions, derivations, or experiments?
- Are edge cases or parameter regimes handled when the task requires them?
- Do raw results, processed results, figures, and prose agree?
- Are claims stronger than the evidence?

## Requirement Map

Classify findings with:

- `explicit_required`: stated by user, problem, or planner
- `implied_required`: needed because an existing claim depends on it
- `optional_recommendation`: useful but not required

Do not turn optional recommendations into blocking issues.

## Hard Issues

Blocking or major issues include:

- contradiction between text and data
- code result that cannot support a stated result
- unsupported convergence, optimality, or correctness claim
- missing raw evidence for a central numerical claim
- fabricated-looking or hardcoded outputs
