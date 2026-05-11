# Role Workspaces

Each folder is an independent, problem-agnostic worker workspace that OpenClaw
roles can execute or adapt.

Included executable worker roles:

- `literature_reviewer`
- `executor`
- `reviewer`
- `pdf_generator`

There is no separate `research_planner` worker. The current OpenClaw agent is
both main and planner, as described in `openclaw/`.

Each role contains:

- `<role>.py` - minimal executable Python module
- `system_prompt.md` - role boundary and behavior
- `skills.md` - concise local skills inventory
- `mcp.json` - placeholder MCP configuration

Example:

```bash
python role/literature_reviewer/literature_reviewer.py \
  --request projects/example/input/request.json \
  --output /tmp/literature_reviewer_result.json
```

The Python modules are scaffolds. They do not solve a specific problem; they
load a JSON request, return a role envelope, and make the workspace replaceable.

The OpenClaw planner should employ these existing worker roles rather than
create new roles. If it needs internet access, paper search, citation checking,
or live source verification, it should call `literature_reviewer`.

`reviewer` enforces the five-round cap. On review round 5 it returns an
explicit forced `PASS` and preserves unresolved issues in the review artifact.
