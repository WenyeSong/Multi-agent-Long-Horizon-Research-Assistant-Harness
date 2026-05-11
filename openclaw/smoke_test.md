# OpenClaw Smoke Test

Use this when the worker roles are still scaffolds and you want a quick
end-to-end sanity check.

## Gateway

Check the gateway:

```bash
openclaw gateway health
```

Start it if needed:

```bash
nohup openclaw gateway run --force > /tmp/openclaw-gateway-background.log 2>&1 &
```

## Agent CLI

From this repository root, send a local OpenClaw turn:

```bash
openclaw agent --local --agent main --thinking low --message "Smoke-test this planner. Use the existing worker roles only. Topic: methods for checking finite graph planarity. Compliance mode: study_assistant. GitHub sync: off."
```

Or send through the running gateway:

```bash
openclaw agent --agent main --thinking low --message "Smoke-test this planner. Use the existing worker roles only. Topic: methods for checking finite graph planarity. Compliance mode: study_assistant. GitHub sync: off."
```

## Worker Fallbacks

The worker modules currently emit fallback artifacts under
`projects/<trace_id>/`. These outputs are intentionally minimal and should be
replaced by real role implementations later.

## Sample Proposal

I want a research memo on methods for checking finite graph planarity. Please
compare obstruction-based criteria such as Kuratowski-style certificates with
embedding-based algorithms, discuss how to validate outputs on small known
graphs like trees, cycles, `K5`, and `K3,3`, and propose a safe study-assistant
workflow that produces notes, tests, and figures without creating submit-ready
coursework code or a final student report.
