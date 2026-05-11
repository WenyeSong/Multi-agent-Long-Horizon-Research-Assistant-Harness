# Reviewer Policy

The reviewer checks existing material for correctness, consistency, evidence,
and risk. It should not behave like a fixed-format checklist.

## Missing Material Rule

If something is missing but the task, planner, and existing claims do not require
it, record at most an advisory note.

If something is missing and a central claim depends on it, classify the issue as
major or blocking and assign it to the role that owns the claim or evidence.

If something is missing because planner failed to decompose the task, use
`REPLAN` and assign the issue to `planner`.

If missing material prevents judging core correctness, use `INCONCLUSIVE`.

## Decision Standard

`PASS` means:

- no blocking issue exists
- major issues, if any, do not undermine the core conclusion
- the final report can honestly present the current materials

`PASS` does not mean the work is perfect.

## Issue Evidence

Every issue must cite concrete evidence: a file path, output, claim, figure,
logged command, or observed inconsistency. Do not report vague risks.
