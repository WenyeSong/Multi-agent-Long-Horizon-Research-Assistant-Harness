# Compliance Review

The default mode is `study_assistant`.

Allowed in `study_assistant`:

- explain the task
- summarize background papers
- provide pseudocode
- suggest tests and visualizations
- point out errors
- generate research notes

Not allowed in `study_assistant`:

- generate a directly submit-ready report
- generate directly submit-ready source code
- package AI output as a student's own final answer
- bypass course AI policy

## Blocking Risks

Use `BLOCK` for severe compliance, integrity, or privacy risks:

- policy forbids the requested output
- artifacts appear designed for direct submission despite restrictions
- provenance is missing for central claims
- user-provided private material is copied beyond allowed scope
- evidence appears fabricated

For ambiguous compliance context, use `INCONCLUSIVE` or route to `main`.
