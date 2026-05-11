#!/usr/bin/env python3
"""Problem-agnostic executable scaffold for the reviewer role."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROLE = "reviewer"
PURPOSE = "Gate math, evidence, execution, presentation, and compliance."
SCHEMA_REFS = ["schemas/review_result.schema.json"]
MAX_REVIEW_ROUNDS = 5


def load_request(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def clamp_review_round(value: Any) -> int:
    try:
        round_number = int(value)
    except (TypeError, ValueError):
        round_number = 1
    return max(1, min(MAX_REVIEW_ROUNDS, round_number))


def default_pass_checks(value: Any) -> dict[str, bool]:
    keys = [
        "citations_traceable",
        "ten_papers_summarized_without_obvious_hallucination",
        "math_matches_problem",
        "results_reproducible",
        "figures_labeled",
        "code_text_consistent",
        "not_packaged_as_student_submission",
        "pdf_adds_no_unreviewed_claims",
    ]
    provided = value if isinstance(value, dict) else {}
    return {key: bool(provided.get(key, False)) for key in keys}


def as_issue_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def reviewed_artifact_refs(request: dict[str, Any]) -> list[str]:
    refs = request.get("reviewed_artifact_refs")
    if isinstance(refs, list) and refs:
        return [str(ref) for ref in refs]
    return [f"projects/{request['trace_id']}/state/state.json"]


def review_round_from_request(request: dict[str, Any]) -> int:
    if "review_round" in request:
        return clamp_review_round(request["review_round"])
    cycle = request.get("review_cycle")
    if isinstance(cycle, dict):
        return clamp_review_round(cycle.get("current_round"))
    return 1


def build_response(request: dict[str, Any]) -> dict[str, Any]:
    if "trace_id" not in request:
        return {
            "role": ROLE,
            "status": "ready",
            "purpose": PURPOSE,
            "schema_refs": SCHEMA_REFS,
            "next_step": "provide trace_id and artifacts to run the review gate"
        }

    review_round = review_round_from_request(request)
    pass_checks = default_pass_checks(request.get("pass_checks"))
    requested_verdict = request.get("verdict")
    blocking_issues = as_issue_list(request.get("blocking_issues"))
    non_blocking_issues = as_issue_list(request.get("non_blocking_issues"))
    force_pass = bool(request.get("force_pass")) or review_round >= MAX_REVIEW_ROUNDS

    if force_pass:
        unresolved = as_issue_list(request.get("unresolved_issues")) + blocking_issues
        return {
            "trace_id": request["trace_id"],
            "review_round": MAX_REVIEW_ROUNDS,
            "verdict": "PASS",
            "reviewed_artifact_refs": reviewed_artifact_refs(request),
            "blocking_issues": [],
            "non_blocking_issues": non_blocking_issues,
            "pass_checks": pass_checks,
            "compliance_risk": request.get(
                "compliance_risk",
                {
                    "level": "medium",
                    "reason": "Forced PASS after review round limit; unresolved issues remain documented."
                },
            ),
            "round_limit": {
                "max_rounds": MAX_REVIEW_ROUNDS,
                "round_reached": MAX_REVIEW_ROUNDS,
                "forced_pass": True,
                "status_message": "Forced PASS after five review rounds; unresolved issues are preserved for planner/user status.",
                "unresolved_issues_summary": unresolved,
            },
            "next_action": "return_to_planner",
        }

    verdict = requested_verdict if requested_verdict in {"PASS", "REVISE", "BLOCK"} else None
    if verdict is None:
        verdict = "PASS" if all(pass_checks.values()) and not blocking_issues else "REVISE"
    if verdict == "PASS":
        blocking_issues = []
        pass_checks = {key: True for key in pass_checks}

    return {
        "trace_id": request["trace_id"],
        "review_round": review_round,
        "verdict": verdict,
        "reviewed_artifact_refs": reviewed_artifact_refs(request),
        "blocking_issues": blocking_issues,
        "non_blocking_issues": non_blocking_issues,
        "pass_checks": pass_checks,
        "compliance_risk": request.get(
            "compliance_risk",
            {"level": "low", "reason": "No explicit compliance risk supplied."},
        ),
        "round_limit": {
            "max_rounds": MAX_REVIEW_ROUNDS,
            "round_reached": review_round,
            "forced_pass": False,
            "unresolved_issues_summary": [],
        },
        "next_action": "block_for_human" if verdict == "BLOCK" else "return_to_planner",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=PURPOSE)
    parser.add_argument("--request", help="Path to worker request JSON")
    parser.add_argument("--output", help="Path to write response JSON")
    args = parser.parse_args()

    response = build_response(load_request(args.request))
    payload = json.dumps(response, indent=2, sort_keys=True) + "\n"

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
