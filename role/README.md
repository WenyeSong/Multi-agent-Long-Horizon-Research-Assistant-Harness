# Role Workspaces

Each folder is an independent, problem-agnostic worker workspace that OpenClaw
roles can execute or adapt.

Included executable worker roles:

- `literature_reviewer`
- `executor`
- `reviewer`
- `pdf_generator` (legacy name; current output is HTML)

There is no separate `research_planner` worker. The current OpenClaw agent is
both main and planner, as described in `openclaw/`.

Each role contains:

- `<role>.py` - minimal executable Python module
- `system_prompt.md` - role boundary and behavior
- `skills.md` - concise local skills inventory
- `mcp.json` - placeholder MCP configuration

`role/reviewer/` additionally contains:

- `SKILL.md` - reviewer workflow and script map
- `references/` - review, routing, logic, visualization, and compliance policy
- `workspace/` - inbox, scratch, outbox, and logs directories for runtime review
  artifacts

Example:

```bash
python role/literature_reviewer/literature_reviewer.py \
  --request projects/example/input/request.json \
  --output /tmp/literature_reviewer_result.json
```

Most Python modules are scaffolds. The reviewer module is a runnable gate:
it builds mechanical evidence, asks an LLM for the review decision when
configured, writes `review_report.json`, and issues `pass_token.json` only for
`PASS`.

The OpenClaw planner should employ these existing worker roles rather than
create new roles. If it needs internet access, paper search, citation checking,
or live source verification, it should call `literature_reviewer`.

`reviewer` enforces the five-round cap. On review round 5 it returns an
explicit forced `PASS` and preserves unresolved issues in the review artifact.
