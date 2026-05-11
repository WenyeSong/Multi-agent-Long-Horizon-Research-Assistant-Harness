# OpenClaw Agent

This folder describes the current OpenClaw agent for this workspace.

There is no separate `main` agent and `research_planner` agent. The current
OpenClaw agent is both the user-facing main agent and the research planner.

Executable worker roles live under `role/`.

Sandbox mode is off for this workspace. Start OpenClaw from the repository root
so the planner can verify relative paths like `openclaw/system_prompt.md`,
`schemas/state.schema.json`, and `role/`. If the real repository is not visible,
it must stop rather than scaffold replacement roles or schemas elsewhere.

## CLI Usage

`openclaw agent` is a one-shot command and always requires `--message`.

For an interactive terminal session, use:

```bash
openclaw chat --local --session research-main --thinking low
```

You can also start the interactive session with an initial request:

```bash
openclaw chat --local --session research-main --thinking low \
  --message "Do research on finding a human-readable proof of the four colour theorem."
```

For one-shot runs, use:

```bash
openclaw agent --local --agent main --session-id research-main --thinking low \
  --message "Do research on finding a human-readable proof of the four colour theorem."
```

The planner owns GitHub repository lifecycle work when requested or when
planner state enables GitHub sync. It still delegates all internet-backed
research to `role/literature_reviewer`.

Every worker invocation should be auditable. The planner writes trace entries to
`projects/<trace_id>/provenance/agent_trace.jsonl`, maintains a readable
`agent_trace_summary.md`, mirrors current entries in planner state, and includes
a concise `Agent Trace` section in CLI replies after workers run.

Plain "do research on ..." requests use the full HTML-report pipeline by
default: `literature_reviewer` -> `executor` -> `reviewer` -> `pdf_generator`.
The planner stops after `literature_reviewer` only for explicit source-only
requests. The legacy `pdf_generator` role runs only after reviewer `PASS`.
Human feedback is treated as report-scoping or report-revision input by default.

For interactive CLI progress, the planner should use `sessions_yield` before
long worker phases when available. This makes role employment visible as
`Agent Trace: <agent> -> starting -> <context>`. If yielding ends the current
turn, continue the same session; the planner resumes from saved state and trace
files.

Reviewer loops are capped at five rounds. Round five is an explicit forced
`PASS` with unresolved issues preserved for planner and user status.

The legacy-named `role/pdf_generator` currently emits an HTML report. Keep
planner routes pointed at `pdf_generator` until the role name is migrated.
