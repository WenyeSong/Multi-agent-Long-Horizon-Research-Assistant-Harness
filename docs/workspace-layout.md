# Per-Task Workspace Layout

Each task gets a separate workspace:

```text
projects/<trace_id>/
  input/
    problem.pdf
    user_request.json
  state/
    state.json
    plan.json
    decisions.jsonl
  literature/
    search_queries.json
    candidate_papers.json
    selected_10_papers.json
    method_matrix.csv
    literature_synthesis.md
  execution/
    execution_plan.json
    src/
    figures/
    results.json
    tests.json
    environment.json
  review/
    review.json
    issues.json
    pass_fail_history.jsonl
  report/
    report_spec.json
    approved_content.md
    final.pdf
  provenance/
    artifact_manifest.json
    citations.json
    audit_log.jsonl
```

Do not pass complete source materials, complete chat history, or full paper
texts to every worker. Workers receive artifact references only for the files
they need.

## Bootstrap

```bash
scripts/create_project_workspace.sh catam_2026_001
```

This creates the directory tree and a starter `state/state.json` in
`study_assistant` mode.
