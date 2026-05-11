# Executor Runtime Contract

This document defines the expected runtime shape before any implementation exists.

The executor runtime should be a small adapter around the design contract. It should not contain planner logic, literature search, review logic, or final report generation.

## Runtime Boundary

The runtime accepts one executor request and returns one executor response.

```text
executor request -> executor runtime -> executor response + artifacts
```

The planner owns when to call the executor. The executor owns what happens inside the assigned execution workspace.

## Minimal Invocation Shape

For a CLI-style MVP, the intended shape is:

```text
python -m executor.runtime run execution_request.json
```

Expected behaviour:

```text
Input:
  execution_request.json

Outputs:
  executor_response.json
  artifacts under workspace.write_path
```

This command is a contract proposal, not implemented runtime code.

## OpenClaw Sub-Agent Shape

For an OpenClaw sub-agent MVP, the same logical contract should apply:

```text
research-planner
  -> spawn executor sub-agent with request JSON
  -> executor writes artifacts under workspace.write_path
  -> executor returns response JSON
```

The transport can change, but the input schema, output schema, workspace contract, and artifact contract should stay stable.

## Runtime Steps

The first runtime skeleton should do only this:

1. Load one execution request.
2. Validate it against `schemas/execution_request.schema.json`.
3. Check tool policy assumptions.
4. Check or create allowed output subdirectories under `workspace.write_path`.
5. Run the bounded execution workflow.
6. Write required artifacts.
7. Validate the response against `schemas/execution_result.schema.json`.
8. Return or write `executor_response.json`.

## First Skeleton Behaviour

The first code skeleton should be deliberately boring:

- validate request;
- create `figures/`, `tables/`, `logs/`, and `work/`;
- write placeholder `results.json`;
- write placeholder `tests.json`;
- write `environment.json`;
- write `artifacts.json`;
- write `notes.md`;
- return a schema-valid `executor_response.json`.

Do not implement real experiments until this skeleton works end to end with planner.

## Error Status Rules

Use these statuses consistently:

- `rejected`: request is invalid, disallowed, or outside executor responsibility.
- `blocked`: request is valid but cannot run because resources, files, dependencies, or permissions are missing.
- `failed`: execution ran but success criteria failed.
- `partial`: some useful artifacts exist but required criteria did not all pass.
- `succeeded`: required criteria passed and required outputs exist.

## Path Resolution

Planner and executor must agree whether paths are:

- absolute paths; or
- paths relative to repository root; or
- paths relative to `workspace.root`.

For the MVP, prefer paths relative to the repository root in JSON examples, and resolve them before execution.

## Non-Goals For Runtime

The runtime must not:

- implement planner scheduling;
- call reviewer or report generator;
- search literature;
- use browser tools;
- spawn sub-agents;
- publish externally;
- silently install dependencies from the network;
- write outside `workspace.write_path`.

## Readiness Gate

The executor runtime is ready for planner integration when:

- it accepts `examples/example_request.json`;
- it produces a response shaped like `examples/example_response.json`;
- all generated files stay under `workspace.write_path`;
- JSON schema validation passes for input and output;
- policy observance is explicitly reported.
