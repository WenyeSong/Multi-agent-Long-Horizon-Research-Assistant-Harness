# Planner-Centered Multi-Agent Architecture

This project uses a strict parent-child orchestration model:

```text
user / attachments / problem
  -> OpenClaw main
  -> research-planner
  -> literature_reviewer
  -> executor
  -> reviewer
  -> pdf_generator
  -> research-planner
  -> OpenClaw main
```

Workers never communicate laterally. Every worker receives a bounded request
from `research-planner` and returns structured artifacts to `research-planner`.

## Agent Responsibilities

| Agent | Does | Does not do |
| --- | --- | --- |
| `main` | User intake, material registration, compliance mode selection, final user reply | Direct final report writing |
| `research-planner` | Problem analysis, finite-state orchestration, state updates, worker spawning | Literature search, code execution, PDF generation |
| `literature_reviewer` | Search and select papers, summarize methods, create evidence matrix | Code, final conclusions, spawning agents |
| `executor` | Algorithm design, experiments, plots, validation, reproducibility notes | Literature search, final report writing |
| `reviewer` | Validate math, citations, code/results, figures, compliance, PASS/REVISE/BLOCK | Rewriting the report or spawning agents |
| `pdf_generator` | Typeset already-approved content into PDF | New facts, new conclusions, math fixes |

## State Machine

`research-planner` may only move through these phases:

- `S0_intake`
- `S1_problem_analysis`
- `S2_lit_review`
- `S3_lit_synthesis`
- `S4_execution_plan`
- `S5_execution`
- `S6_review`
- `S7_revise`
- `S8_pdf_generate`
- `S9_final`

At each transition the planner reads only:

1. `state/state.json`
2. the latest worker result artifact
3. schemas in `schemas/`

The planner then chooses exactly one value from `allowed_next_actions`.

## Compliance Mode

Default mode is `study_assistant`.

Allowed in this mode:

- explain the task
- summarize background papers
- produce pseudocode
- propose tests and visualizations
- point out errors
- generate research notes

Not allowed in this mode:

- generate a directly submit-ready final report
- generate directly submit-ready final source code
- package AI output as a student's own answer
- work around a course AI policy

`independent_research` may be used only after explicit user declaration.

## Reviewer Gate

`pdf_generator` may run only after `reviewer` returns `verdict: "PASS"`.

PASS requires:

1. traceable citations
2. ten paper summaries without obvious hallucination
3. math methods matching the problem
4. reproducible numerical results
5. titled/labeled figures with axes, units, or parameters
6. consistency between code results and text
7. no packaging as student final coursework
8. no unreviewed claims added by the PDF step

If the reviewer returns `REVISE`, the planner routes back to literature,
execution, or PDF formatting. If the reviewer returns `BLOCK`, human
intervention is required.
