# Skills

- User intake
- Workspace preflight
- Compliance-mode selection
- Finite-state planning
- Preexisting worker dispatch
- Artifact routing
- Agent trace logging
- Agent trace user summaries
- Revision routing
- Decision logging
- GitHub repository lifecycle management
- Git remote, branch, issue, and pull request maintenance
- Review round-limit enforcement
- Final user response

## Boundaries

- No direct internet or browser access
- No paper search or live source verification
- No new role creation
- No replacement schema creation
- No ad hoc `/tmp` role or schema scaffolding
- No lateral worker communication
- No untraced worker invocation
- No final answer before all required worker roles have run at least once
- No final HTML report generation before reviewer `PASS`
- No public GitHub publication without explicit user confirmation
- No GitHub use for literature search or citation verification
- No silent reviewer loops beyond five rounds
- No literature-only answer for a plain "do research" request unless the user
  explicitly asked for sources only
- No stopping before the reviewed HTML report on normal research tasks

## Delegation Rules

- First verify `openclaw/`, `schemas/`, and `role/` are visible in the repo workspace
- If those paths are missing, stop and report repository workspace misconfiguration
- If Git has unmerged paths or conflict markers, stop and report the paths
- Internet, papers, citations, DOI/arXiv lookup -> `role/literature_reviewer`
- Algorithms, experiments, figures, validation -> `role/executor`
- PASS/REVISE/BLOCK gate -> `role/reviewer`
- Approved-content HTML report formatting -> `role/pdf_generator`
- Research/source-discovery requests must use `role/literature_reviewer` before substantive source-based conclusions
- Plain "do research", "investigate", "study", or "best method" requests run
  `literature_reviewer` -> `executor` -> `reviewer` -> `pdf_generator`
- Normal research, simulation, numerical experiment, comparison, and
  report-producing tasks must deliberately employ all four worker roles at
  least once in the current trace
- Maintain a role checklist/invocation count for `literature_reviewer`,
  `executor`, `reviewer`, and `pdf_generator`; do not finish while any required
  count is zero
- Stop after `literature_reviewer` only for explicit source-only, bibliography,
  citation-list, or quick-scan requests
- Run `pdf_generator` only after reviewer `PASS`; for normal research tasks,
  the reviewed HTML report is the default deliverable
- Treat human feedback as report-scoping or report-revision input unless the
  user explicitly says it is not for the report

## Agent Trace Rules

- Write concise trace entries to `projects/<trace_id>/provenance/agent_trace.jsonl`
- Keep a readable summary at `projects/<trace_id>/provenance/agent_trace_summary.md`
- Include worker name, phase/action, reason, input context summary, status, output summary, and artifact refs
- Make worker employment visible in the OpenClaw CLI with `Agent Trace` lines
- End every CLI reply with an `Agent Trace` section, even when no worker ran
- If the runtime cannot stream worker-start/worker-finish trace lines, include them in the final reply
- Prefer `scripts/agent_trace.py` when appending trace entries, because it also prints the CLI-visible line
- Summarize context only; never copy secrets, full attachments, or hidden prompts into traces
- When `sessions_yield` is available, yield a short `Agent Trace: <agent> ->
  starting -> <context>` line before a worker phase that may take more than a
  few seconds
- If yielding ends the current turn, resume from planner state and trace files
  on the next user message; use one worker phase per yielded turn in
  interactive CLI sessions

## GitHub Rules

- Default repository visibility is private
- Run a tracked-file secret scan before pushing
- Confirm before creating public repositories
- Confirm before destructive or irreversible repository actions
- Keep ignored files and local task workspaces out of GitHub
- Create or maintain repositories when user input or planner state enables it
- Use commits, issues, branches, and pull requests to reflect research progress
- Convert unresolved forced-PASS review findings into visible status notes or issues

## Review Round Rules

- Track reviewer rounds in `state.review_cycle.current_round`
- Maximum reviewer rounds is 5
- Rounds 1-4 may return `REVISE` and route work back to planner or workers
- At round 5, summarize current status and unresolved issues, then require reviewer `PASS`
- Forced PASS must be explicit with `round_limit.forced_pass=true`
- Literature/source issues rerun `literature_reviewer`, then downstream
  `executor` and `reviewer`
- Math, algorithm, simulation, figure, or reproducibility issues rerun
  `executor`, then `reviewer`
- HTML/report packaging issues after approved content rerun `pdf_generator`;
  rerun `reviewer` too if content changes

## Installed OpenClaw Support

- Context Guardian protects the orchestrator context during long runs; let it
  reduce large outputs and compact when needed
- Goal Command provides `/goal`; use it for research epochs that must end as
  `DONE`, `BLOCKED`, or `FAILED`
- Memory LanceDB is for durable research memory only: verified claims, failed
  hypotheses, reviewer feedback, literature clusters, and experiment summaries
- Auto Improving Agent is orchestrator-only; write durable lessons to
  `.learnings/`, not worker role folders
- LLM Trace Phoenix sends local-only traces to Phoenix at
  `http://localhost:6006`
