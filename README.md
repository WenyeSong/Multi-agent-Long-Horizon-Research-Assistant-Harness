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

- the current OpenClaw agent is both `main` and the research planner.
- workers do not talk to each other.
- all worker outputs return to the OpenClaw planner as JSON artifact refs.
- the OpenClaw planner does not access the internet directly.
- internet-backed research is delegated to `role/literature_reviewer/`.
- `pdf_generator` can run only after `reviewer` returns `PASS` and issues a
  pass token bound to reviewed artifact hashes.
- default compliance mode is `study_assistant`.

## Role Workspaces

`openclaw/` describes the current OpenClaw agent. It is both the user-facing
main agent and the research planner.

`role/` contains concise, problem-agnostic Python workspaces for the executable
worker roles:

- `role/literature_reviewer/`
- `role/executor/`
- `role/reviewer/`
- `role/pdf_generator/`

Each role folder has a runnable Python module, `system_prompt.md`, `skills.md`,
and `mcp.json`. Most modules are intentionally small scaffolds so they can be
executed by OpenClaw roles and replaced later.

The reviewer role is now more concrete: it uses LLM-led judgment plus lightweight
scripts for packet preflight, artifact hashing, optional executor verification,
scope audit, review logging, route suggestion, and pass-token issuance.

The OpenClaw planner should employ these existing roles rather than create new
ones.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
```

Fill `.env` with local credentials, then create local model config files from
the example as needed.

## Next Step

Next integration step: wire the planner to create
`role/reviewer/workspace/inbox/review_packet.json`, call the reviewer role, and
only create `report_spec.json` when `review_report.json` has `decision == PASS`
and `pass_token.json` exists.
