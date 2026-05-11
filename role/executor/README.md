# Executor Role

This directory is the GitHub-facing executor role package expected at:

```text
role/executor
```

The executor is a planner-controlled worker. It designs bounded experiments, runs reproducibility checks, creates visualisations, validates results, and returns execution artifacts to the planner.

It must not search literature, spawn agents, call reviewer/PDF roles, decide the global research route, or write final report prose. In `study_assistant` mode, it must not produce directly submit-ready coursework source code.

## Required Role Files

```text
executor.py
mcp.json
skills.md
system_prompt.md
schemas/execution_request.schema.json
schemas/execution_result.schema.json
```

## Supporting Files

```text
examples/example_request.json
examples/example_response.json
handoff/planner_handoff.md
docs/
```

## Current Status

The runtime now supports an LLM-backed MVP loop:

```text
planner request -> LLM/fallback generates experiment code -> executor runs code -> artifacts + response
```

Run without requiring network credentials:

```powershell
py -3 role\executor\executor.py --request role\executor\examples\example_request.json --output role\executor\workspaces\exec_001\executor_response.json --llm off
```

Run with LLM generation when credentials are available:

```powershell
py -3 role\executor\executor.py --request role\executor\examples\example_request.json --output role\executor\workspaces\exec_001\executor_response.json --llm auto
```

`--llm auto` reads local config or environment variables. Do not commit real API keys. Use `role/executor/llm_config.example.json` as a template for a local ignored `role/executor/llm_config.json`, or set `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, or `EXECUTOR_LLM_API_KEY`.

When using an OpenAI key directly, set `EXECUTOR_LLM_MODEL` if you want a specific model:

```powershell
$env:OPENAI_API_KEY="..."
$env:EXECUTOR_LLM_MODEL="gpt-4o-mini"
```
