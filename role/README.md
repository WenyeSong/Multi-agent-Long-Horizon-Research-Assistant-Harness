# Role Workspaces

Each folder is an independent, problem-agnostic agent workspace that OpenClaw
roles can execute or adapt.

Included roles:

- `research_planner`
- `literature_reviewer`
- `executor`
- `reviewer`
- `pdf_generator`

Each role contains:

- `<role>.py` - minimal executable Python module
- `system_prompt.md` - role boundary and behavior
- `skills.md` - concise local skills inventory
- `mcp.json` - placeholder MCP configuration

Example:

```bash
python role/research_planner/research_planner.py \
  --request projects/example/input/request.json \
  --output /tmp/research_planner_result.json
```

The Python modules are scaffolds. They do not solve a specific problem; they
load a JSON request, return a role envelope, and make the workspace replaceable.
