# Multi-Agent Hackathon

Workspace for a planner-centered OpenClaw multi-agent research assistant.

The design is deliberately not a many-agent chat room. `main` talks to the
user, `research-planner` orchestrates, and all workers return artifacts to the
planner.

## Repository Hygiene

This repository intentionally excludes:

- local API keys and model configuration files
- `.env` files
- OpenClaw/Codex local state
- the current scratch Python files in this folder
- virtual environments and generated Python artifacts

Use `.env.example` and `llm_config.example.json` as templates for local setup.

Task workspaces under `projects/` are ignored by Git because they can contain
user attachments, generated artifacts, and assessment context.

## Architecture

- `docs/architecture.md` describes the agent topology, finite-state planner,
  reviewer gate, and compliance rules.
- `docs/workspace-layout.md` describes the per-task artifact tree.
- `config/openclaw.agents.example.json` contains an example OpenClaw agent
  policy layout.
- `prompts/` contains the system prompts for each agent role.
- `schemas/` contains the JSON contracts that planner and workers exchange.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
```

Fill `.env` with local credentials, then create local model config files from
the example as needed.

Create a task workspace:

```bash
scripts/create_project_workspace.sh catam_2026_001
```

Validate the generated state with your preferred JSON Schema validator against
`schemas/state.schema.json`.
