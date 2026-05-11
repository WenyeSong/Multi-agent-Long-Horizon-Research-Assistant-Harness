# Executor Role

This directory is the GitHub-facing executor role package expected at:

```text
role/executor
```

The executor is a planner-controlled worker. It designs bounded experiments, runs reproducibility checks, creates visualisations, validates results, and returns execution artifacts to the planner.

It must not search literature, spawn agents, call reviewer/PDF roles, decide the global research route, or write final report prose. In `study_assistant` mode, it must not produce directly submit-ready coursework source code.

## Required Role Files

```text
executor.py
mcp.json
skills.md
system_prompt.md
schemas/execution_request.schema.json
schemas/execution_result.schema.json
```

## Supporting Files

```text
examples/example_request.json
examples/example_response.json
handoff/planner_handoff.md
docs/
```

## Current Status

This is still a design and integration scaffold. The runtime does not yet perform real experiments. The next implementation step is to make `executor.py` validate an execution request and emit a schema-valid placeholder execution result.
