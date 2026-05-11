# Executor Handoff For Planner Agent

This document is the integration handoff for any planner-side agent or teammate that needs to call the executor.

The executor is a bounded execution worker. It performs algorithm design, numerical experiments, visualisation, and result validation only when the planner gives it a concrete execution request.

The executor does not choose the global research route, search literature, call reviewers, generate PDFs, or publish anything externally.

## Files To Read First

Planner-side integration should start with these files:

```text
role/executor/schemas/execution_request.schema.json
role/executor/schemas/execution_result.schema.json
role/executor/examples/example_request.json
role/executor/examples/example_response.json
role/executor/docs/planner_integration_checklist.md
```

Supporting contracts:

```text
role/executor/docs/workspace_contract.md
role/executor/docs/artifact_contract.md
role/executor/docs/tool_policy.md
role/executor/docs/runtime_contract.md
```

## System Position

Expected architecture:

```text
main
  -> research-planner
       -> literature_reviewer
       -> executor
       -> reviewer
       -> pdf_generator
```

The executor only talks to `research-planner`.

Planner owns:

- task selection;
- global research route;
- deciding which agent to call;
- choosing authorised inputs;
- defining success criteria;
- allocating workspace;
- deciding what to do with executor output.

Executor owns:

- bounded execution;
- experiment attempts;
- visualisation;
- validation against planner criteria;
- artifact generation;
- structured response back to planner.

## Minimum Planner Request

The planner must emit a request matching:

```text
role/executor/schemas/execution_request.schema.json
```

The request must include:

- `request_id`: unique id for this executor call.
- `planner_id`: id of the parent planner run.
- `task.title`: short task name.
- `task.objective`: concrete execution objective.
- `task.scope`: what executor is allowed to do.
- `task.non_goals`: optional explicit exclusions.
- `workspace.root`: logical root for this execution run.
- `workspace.read_paths`: authorised read-only paths.
- `workspace.write_path`: only writable directory.
- `inputs`: authorised input artifacts.
- `success_criteria`: checks executor must validate.
- `budget.max_attempts`: maximum attempts.
- `budget.max_wall_time_minutes`: wall-clock budget.
- `required_outputs`: expected artifact categories.
- `tool_policy_ref`: policy reference.

Concrete example:

```text
role/executor/examples/example_request.json
```

## Minimum Executor Response

Planner should expect a response matching:

```text
role/executor/schemas/execution_result.schema.json
```

The response will include:

- `request_id`;
- `status`;
- `summary`;
- `artifacts`;
- `validation`;
- `attempts`;
- `policy_observance`;
- optional `limitations`;
- optional `recommended_planner_next_steps`.

Concrete example:

```text
role/executor/examples/example_response.json
```

## Status Meanings

Planner should interpret executor statuses as follows:

| Status | Meaning |
| --- | --- |
| `succeeded` | Required criteria passed and required outputs were produced. |
| `partial` | Some useful artifacts were produced, but not all required criteria passed. |
| `failed` | Execution completed but did not meet success criteria. |
| `blocked` | Execution could not proceed because resources, files, dependencies, or permissions were missing. |
| `rejected` | Request was invalid, unsafe, or outside executor responsibility. |

Planner should handle `blocked` and `rejected` differently:

- `blocked` may be fixed by providing missing files, workspace, dependencies, or permissions.
- `rejected` means the request itself violates the executor contract.

## Workspace Contract

Planner should allocate the workspace before calling executor.

Recommended layout:

```text
role/executor/workspaces/
  <request_id>/
    inputs/
    work/
    figures/
    tables/
    logs/
    results.json
    tests.json
    environment.json
    artifacts.json
    notes.md
```

Planner should pass paths consistently. For the MVP, prefer paths relative to repository root.

Executor may read:

- `workspace.read_paths`;
- artifacts listed in `inputs`;
- files it created under `workspace.write_path`.

Executor may write only under:

```text
workspace.write_path
```

Planner should not expect executor to modify planner files, input artifacts, reviewer files, PDF generator files, or repository-level configuration.

## Artifact Contract

Executor returns artifact references, not large embedded payloads.

Core expected files:

```text
results.json
tests.json
environment.json
artifacts.json
notes.md
```

Expected directories:

```text
figures/
tables/
logs/
work/
```

Figure naming convention:

```text
figures/<attempt_id>_<figure_role>.<ext>
```

Examples:

```text
figures/attempt_01_loss_curve.png
figures/attempt_01_residual_diagnostic.png
figures/attempt_02_parameter_sweep.svg
```

Table naming convention:

```text
tables/<attempt_id>_<table_role>.csv
tables/<attempt_id>_<table_role>.json
```

Planner should inspect `artifacts.json` and the response `artifacts` array to find generated files.

Artifact roles may include:

- `primary_result`;
- `diagnostic`;
- `audit`;
- `supporting`;
- `debug`.

## Success Criteria Guidance

Planner should provide success criteria that are concrete enough for executor validation.

Good criteria:

```text
Produce results.json with baseline, attempts, and best_attempt keys.
Generate at least one diagnostic figure under figures/.
At least one attempt improves objective_value over baseline.
Run the provided validation script and report pass/fail in tests.json.
```

Weak criteria:

```text
Try to improve the algorithm.
Make good plots.
Check if it works.
Do some experiments.
```

If criteria are vague, executor may return `blocked` or produce only partial evidence.

## Tool Policy

Executor should be configured with this policy:

| Tool class | Policy |
| --- | --- |
| read | Allow, only authorised inputs and execution workspace. |
| write | Allow, only `workspace.write_path`. |
| exec | Allow, sandboxed and budgeted. |
| browser | Deny. |
| sessions_spawn | Deny. |
| external_post | Deny. |

Executor must not:

- search the web;
- search literature;
- install dependencies from the network unless explicitly pre-approved;
- spawn sub-agents;
- call reviewer or PDF generator;
- upload or post data externally;
- write outside its workspace.

## Runtime Expectation

The runtime is not implemented yet, but the intended contract is:

```text
executor request -> executor runtime -> executor response + artifacts
```

Possible CLI shape:

```text
python -m executor.runtime run execution_request.json
```

Possible OpenClaw shape:

```text
research-planner
  -> spawn executor sub-agent with request JSON
  -> executor writes artifacts under workspace.write_path
  -> executor returns response JSON
```

Transport can change. The input schema, output schema, workspace contract, artifact contract, and tool policy should remain stable.

## Planner Integration Checklist

Before connecting planner to executor, confirm:

- Planner can generate a request shaped like `examples/example_request.json`.
- Planner request validates against `schemas/execution_request.schema.json`.
- Planner creates or allocates `workspace.write_path`.
- Planner lists every input artifact in both `inputs` and `workspace.read_paths`.
- Planner provides concrete `success_criteria`.
- Planner provides a bounded `budget`.
- Planner expects artifact refs, not embedded files.
- Planner can parse a response shaped like `examples/example_response.json`.
- Planner handles `succeeded`, `partial`, `failed`, `blocked`, and `rejected`.
- Planner does not ask executor to browse, spawn agents, review, generate PDFs, or decide the global research route.

## Common Failure Modes

Avoid these integration mistakes:

- Request has an objective but no success criteria.
- Request gives file paths in inconsistent formats.
- Request provides read paths but forgets input artifact metadata.
- Planner expects executor to create global project structure.
- Planner expects executor to search for missing context.
- Executor output is treated as final coursework submission without planner or reviewer checks.
- Planner ignores `policy_observance`.
- Planner assumes every `partial` response is useless.
- Planner assumes every generated plot is a final report figure.

## Practical Handoff Message

Planner-side agent can use this summary:

```text
Please emit executor requests matching role/executor/schemas/execution_request.schema.json and parse executor responses matching role/executor/schemas/execution_result.schema.json.

Use role/executor/examples/example_request.json as the concrete request template and role/executor/examples/example_response.json as the expected response shape.

Planner owns task selection, workspace allocation, authorised inputs, success criteria, budget, and next-step decisions.

Executor only performs bounded execution inside workspace.write_path, generates artifacts, validates against success_criteria, and returns artifact refs plus validation results.

Executor must not browse, spawn agents, call reviewer/PDF generator, decide the global research route, or write outside workspace.write_path.
```


