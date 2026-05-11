#!/usr/bin/env bash
set -euo pipefail

trace_id="${1:-}"
if [[ -z "$trace_id" ]]; then
  echo "usage: scripts/create_project_workspace.sh <trace_id>" >&2
  exit 2
fi

if [[ ! "$trace_id" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,127}$ ]]; then
  echo "invalid trace_id: $trace_id" >&2
  exit 2
fi

root="projects/$trace_id"

mkdir -p \
  "$root/input" \
  "$root/state" \
  "$root/literature" \
  "$root/execution/src" \
  "$root/execution/figures" \
  "$root/review" \
  "$root/report" \
  "$root/provenance"

if [[ ! -f "$root/state/state.json" ]]; then
  cat > "$root/state/state.json" <<JSON
{
  "trace_id": "$trace_id",
  "phase": "S0_intake",
  "compliance_mode": "study_assistant",
  "problem": {
    "domain": "unknown",
    "project_id": "unknown",
    "research_goal": "unknown",
    "summary": "",
    "assessment_context": {
      "is_coursework": true,
      "source_policy_refs": [],
      "marking_weights": {
        "program_runs_and_figures": 0.4,
        "mathematical_answers_and_observations": 0.5,
        "report_clarity": 0.1
      }
    }
  },
  "completed": {
    "problem_analysis": false,
    "literature_review": false,
    "lit_synthesis": false,
    "execution_plan": false,
    "execution": false,
    "review": false,
    "pdf": false
  },
  "artifacts": {
    "input": "$root/input/user_request.json",
    "plan": "$root/state/plan.json"
  },
  "allowed_next_actions": [
    "spawn_literature_reviewer",
    "block_for_human"
  ],
  "decision_history_refs": [
    "$root/state/decisions.jsonl"
  ]
}
JSON
fi

touch \
  "$root/state/decisions.jsonl" \
  "$root/provenance/audit_log.jsonl"

echo "$root"
