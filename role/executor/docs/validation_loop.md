# Executor Validation Loop

The executor follows a simple auditable loop:

```text
baseline -> attempt -> verify -> guard -> log
```

This loop keeps the executor bounded, measurable, and planner-controlled.

## 1. Input Validation

Before running experiments, validate that the request includes:

- request id;
- planner id;
- task objective and scope;
- authorised read paths;
- single write path;
- success criteria;
- execution budget;
- required outputs.

Return `rejected` if the request asks for disallowed behaviour.

Return `blocked` if the request is valid but cannot be executed because required inputs, permissions, or dependencies are unavailable.

## 2. Baseline

Create or identify a baseline before making attempts.

The baseline may be:

- planner-provided code;
- a simple reference implementation;
- previous result artifacts;
- a no-change measurement;
- a deterministic sanity-check case.

The baseline should be recorded in `results.json` or `notes.md`.

## 3. Attempt

Run a limited experimental attempt within the planner budget.

Each attempt should record:

- attempt id;
- changed parameters or method;
- command or high-level execution summary;
- produced artifacts;
- observed metrics;
- failure reason if any.

Do not exceed `budget.max_attempts`.

## 4. Verify

Compare each attempt against the planner-provided success criteria.

Verification may include:

- metric threshold checks;
- unit tests;
- property checks;
- reproducibility checks;
- visual output existence checks;
- planner-required manual review markers.

Write check outcomes to `tests.json`.

## 5. Guard

After verification, check that the attempt stayed within boundaries:

- no browser usage;
- no sessions spawned;
- no external posting;
- no writes outside `workspace.write_path`;
- no reads outside authorised inputs;
- no expansion beyond task scope;
- no unsupported claims in the summary.

Policy failures should produce `failed`, `blocked`, or `rejected` status depending on cause and severity.

## 6. Log

Log enough evidence for planner review:

- baseline summary;
- attempts;
- validation outcomes;
- generated artifact paths;
- environment metadata;
- limitations and unresolved issues.

## 7. Final Status

Use these statuses:

- `succeeded`: required success criteria passed and required outputs were produced.
- `partial`: some useful artifacts were produced, but not all required criteria passed.
- `failed`: execution completed but did not meet success criteria.
- `blocked`: execution could not proceed under current resources or permissions.
- `rejected`: request asked for disallowed behaviour or invalid scope.

## 8. Planner Handoff

The final executor response must return structured artifact references to the planner. It may suggest local follow-up checks, but it must not decide the global research route.
