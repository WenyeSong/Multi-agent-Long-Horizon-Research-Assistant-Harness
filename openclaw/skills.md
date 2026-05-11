# Skills

- User intake
- Workspace preflight
- Compliance-mode selection
- Finite-state planning
- Preexisting worker dispatch
- Artifact routing
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
- No PDF generation before reviewer `PASS`
- No public GitHub publication without explicit user confirmation
- No GitHub use for literature search or citation verification
- No silent reviewer loops beyond five rounds

## Delegation Rules

- First verify `openclaw/`, `schemas/`, and `role/` are visible in the repo workspace
- If those paths are missing, stop and report sandbox/workspace misconfiguration
- If Git has unmerged paths or conflict markers, stop and report the paths
- Internet, papers, citations, DOI/arXiv lookup -> `role/literature_reviewer`
- Algorithms, experiments, figures, validation -> `role/executor`
- PASS/REVISE/BLOCK gate -> `role/reviewer`
- Approved-content PDF formatting -> `role/pdf_generator`

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
