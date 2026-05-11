# OpenClaw Plugins

This workspace keeps the existing architecture: OpenClaw is the main
orchestrator, and the worker roles under `role/` remain unchanged as the
planner-dispatched role workspaces. These plugins and the installed skill add
support around the orchestrator only.

## Installed

- `context-guardian` from `clawhub:openclaw-context-guardian`
- `openclaw-goal-command` from `clawhub:openclaw-goal-command`
- `memory-lancedb` from `clawhub:@openclaw/memory-lancedb`
- `llm-trace-phoenix` from `clawhub:llm-trace-phoenix`
- `self-improving-agent` skill from `openclaw skills install auto-improving-agent`

## Intended Use

Context Guardian protects the OpenClaw orchestrator context during long research
runs. Let it reduce large tool outputs and compact when context pressure rises.

Goal Command provides `/goal` for closed research epochs. Use it when a research
step needs an explicit loop with one terminal state: `DONE`, `BLOCKED`, or
`FAILED`.

Memory LanceDB is long-term research memory. Store only useful research state:
verified claims, failed hypotheses, reviewer feedback, literature clusters, and
experiment summaries. Do not treat raw conversations or unverified outputs as
trusted memory.

Auto Improving Agent is for the OpenClaw orchestrator only. It may record durable
lessons, repeated failures, and missing capabilities under `.learnings/`. Do not
install or copy it into every worker role.

LLM Trace Phoenix traces orchestrator LLM calls and research decisions to the
local Phoenix instance. Keep Phoenix local at `http://localhost:6006`.

## Phoenix

No `docker-compose.yml` file exists in this repository. Phoenix was started as a
local-only Docker container with ports bound to `127.0.0.1`.

If a Compose file is added later, use this minimal service:

```yaml
phoenix:
  image: arizephoenix/phoenix:latest
  ports:
    - "127.0.0.1:6006:6006"
    - "127.0.0.1:4317:4317"
    - "127.0.0.1:4318:4318"
  environment:
    PHOENIX_WORKING_DIR: /phoenix_data
  volumes:
    - phoenix-data:/phoenix_data
  restart: unless-stopped

volumes:
  phoenix-data:
```

## Verification

Run:

```bash
openclaw plugins list
openclaw skills list
openclaw gateway restart
openclaw gateway status
```

Check plugin config:

```bash
openclaw config get plugins.entries.context-guardian.enabled
openclaw config get plugins.slots.memory
openclaw config get plugins.entries.llm-trace-phoenix.config
```

Check Phoenix:

```bash
curl -I http://127.0.0.1:6006
docker ps --format '{{.Names}} {{.Image}} {{.Ports}}'
```

Expected state:

- Context Guardian is enabled.
- `/goal` is available through Goal Command.
- Memory slot is `memory-lancedb`.
- `self-improving-agent` appears in `openclaw skills list`.
- Phoenix opens locally at `http://localhost:6006`.
- After one successful OpenClaw LLM interaction, traces appear in the Phoenix
  `openclaw` project.

On this WSL setup, `openclaw gateway restart` may report that the systemd user
service is disabled. In that case, use the local embedded agent or start the
gateway manually with `openclaw gateway run --force`.
