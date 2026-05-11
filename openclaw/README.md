# OpenClaw Roles

This folder contains OpenClaw-native role workspaces. These are not standalone
Python worker modules.

`research_planner/` is the planner/orchestrator sub-agent. It owns the state
machine and delegates work to the executable worker roles under `role/`.
