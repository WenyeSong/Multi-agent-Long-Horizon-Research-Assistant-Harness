# Routing Policy

The reviewer does not schedule follow-up work. It gives the planner a clear
recovery route.

## Owner Mapping

- Problem decomposition missing a subquestion: `planner`
- Task metric or acceptance logic is wrong: `planner`
- Executor followed an incorrect goal from planner: `planner`
- Code does not run: `executor`
- Figure and data disagree: `executor`
- Mathematical derivation is wrong: `executor`
- Conclusion exceeds experiment evidence: `executor`
- Literature does not support a claim: `literature_reviewer`
- Citation is missing, nonexistent, or irrelevant: `literature_reviewer`
- User material or compliance conditions are unclear: `main`
- Post-PASS PDF formatting problem: `pdf_generator`

## Decision To Route

- `PASS`: planner may call `pdf_generator`
- `REVISE`: planner should call the suggested worker owner
- `REPLAN`: planner should update state, success criteria, or experiment design
- `BLOCK`: planner should return to `main` or human review
- `INCONCLUSIVE`: planner should provide missing packet material or collect
  enough artifacts for review

## Stuck Recovery

If the same owner receives two unresolved `REVISE` decisions for the same core
issue, planner should refine the instruction.

If the same core issue survives three review cycles, planner should pivot method,
success criteria, or ownership instead of looping.
