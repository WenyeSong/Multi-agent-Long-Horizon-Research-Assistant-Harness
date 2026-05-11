# OpenClaw Agent

This folder describes the current OpenClaw agent for this workspace.

There is no separate `main` agent and `research_planner` agent. The current
OpenClaw agent is both the user-facing main agent and the research planner.

Executable worker roles live under `role/`.

The planner should run with the repository mounted in its sandbox:
`workspaceAccess=rw` and
`workspaceRoot=/home/akame/mphildis/events/multi-agent-hackathon`. Inside the
sandbox, the repo may appear as the current working directory or `/workspace`;
the planner should verify relative paths like `openclaw/system_prompt.md`,
`schemas/state.schema.json`, and `role/`. If that workspace is not visible, it
must stop rather than scaffold replacement roles or schemas elsewhere.

The planner owns GitHub repository lifecycle work when requested or when
planner state enables GitHub sync. It still delegates all internet-backed
research to `role/literature_reviewer`.

Reviewer loops are capped at five rounds. Round five is an explicit forced
`PASS` with unresolved issues preserved for planner and user status.
