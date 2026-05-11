# Executor Tool Policy

This document defines the executor's MVP tool boundary.

The executor is allowed to run code, but it is not allowed to become a general-purpose autonomous agent. Tool access must be narrower than the planner's access.

## Tool Classes

| Tool class | Policy | Notes |
| --- | --- | --- |
| read | Allow | Only planner-authorised input artifacts and files inside the execution workspace. |
| write | Allow | Only inside the assigned execution workspace. |
| exec | Allow | Must be sandboxed and bounded by the request budget. |
| llm_inference | Allow narrow | Only the configured OpenAI-compatible inference endpoint for bounded code planning/generation. |
| browser | Deny | No web, literature, documentation, or repository search. |
| sessions_spawn | Deny | Executor must not create sub-agents or additional sessions. |
| external_post | Deny | No uploads, emails, remote writes, API posting, or publishing. |

## Allowed Read Operations

The executor may read:

- files listed in `workspace.read_paths`;
- artifacts listed in the request `inputs`;
- files it created inside `workspace.write_path`;
- local runtime metadata needed for `environment.json`.

The executor must not read:

- parent directories outside the authorised workspace;
- hidden credentials;
- global user configuration;
- unrelated project files;
- other agents' private workspaces.

## Allowed Write Operations

The executor may write:

- `results.json`;
- `tests.json`;
- `environment.json`;
- generated figures;
- logs;
- temporary files;
- local code prototypes used for the assigned experiment.

All writes must stay under `workspace.write_path`.

## Execution Rules

Execution must:

- run in a sandbox or equivalent restricted environment;
- respect `budget.max_attempts`;
- respect `budget.max_wall_time_minutes`;
- avoid network access;
- allow only the configured LLM inference call when LLM-backed code generation is enabled;
- avoid background services unless explicitly allowed by the planner request;
- log commands or high-level execution steps in the output artifacts.

## Denied Behaviours

The executor must not:

- install dependencies from the network unless the planner and sandbox policy explicitly allow a pre-approved package source;
- open URLs;
- use browser tools;
- call remote APIs other than the configured LLM inference endpoint;
- post data externally;
- spawn other agents;
- modify planner, reviewer, literature reviewer, or PDF generator files;
- overwrite planner-provided inputs.

## Policy Failure Handling

If the task cannot be completed without violating this policy, the executor must stop and return:

- `status: "blocked"` if required resources or permissions are missing;
- `status: "rejected"` if the planner request itself asks for disallowed behaviour.
