# Multi-Agent Hackathon

Workspace for multi-agent hackathon experiments.

## Repository Hygiene

This repository intentionally excludes:

- local API keys and model configuration files
- `.env` files
- OpenClaw/Codex local state
- the current scratch Python files in this folder
- virtual environments and generated Python artifacts

Use `.env.example` and `llm_config.example.json` as templates for local setup.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
```

Fill `.env` with local credentials, then create local model config files from
the example as needed.
