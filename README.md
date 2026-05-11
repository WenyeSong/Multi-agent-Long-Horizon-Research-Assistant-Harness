# Multi-Agent Hackathon

Workspace for a planner-centered OpenClaw multi-agent research assistant.

This repo is currently at the schema-first stage. The five JSON contracts in
`schemas/` define the planner state and worker outputs before any agent prompts
or OpenClaw runtime config are added.

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

## Contracts

The initial implementation fixes these contracts:

- `schemas/state.schema.json`
- `schemas/literature_result.schema.json`
- `schemas/execution_result.schema.json`
- `schemas/review_result.schema.json`
- `schemas/report_spec.schema.json`

The architecture implied by these schemas is:

- `main` is the user-facing entrypoint.
- `research-planner` is the only orchestrator.
- workers do not talk to each other.
- all worker outputs return to `research-planner` as JSON artifact refs.
- `pdf_generator` can run only after `reviewer` returns `PASS`.
- default compliance mode is `study_assistant`.

## Role Workspaces

`role/` contains concise, problem-agnostic workspaces for the non-OpenClaw
roles:

- `role/research_planner/`
- `role/literature_reviewer/`
- `role/executor/`
- `role/reviewer/`
- `role/pdf_generator/`

Each role folder has a runnable Python module, `system_prompt.md`, `skills.md`,
and `mcp.json`. The modules are intentionally small scaffolds so they can be
executed by OpenClaw roles and replaced later.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
```

Fill `.env` with local credentials, then create local model config files from
the example as needed.

## Next Step

After these schemas are reviewed, add OpenClaw agent configuration and system
prompts that enforce the schema contracts and tool boundaries.
