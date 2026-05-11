#!/usr/bin/env python3
"""Minimal runnable scaffold for the executor role."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
from typing import Any


ROLE = "executor"
PURPOSE = "Design experiments, run reproducibility checks, and return execution artifacts."
SCHEMA_REFS = [
    "schemas/execution_request.schema.json",
    "schemas/execution_result.schema.json",
]


def load_request(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("request JSON must be an object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_request(request: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "request_id",
        "planner_id",
        "task",
        "workspace",
        "inputs",
        "success_criteria",
        "budget",
        "required_outputs",
    ]
    for key in required:
        if key not in request:
            errors.append(f"missing required field: {key}")

    task = request.get("task")
    if isinstance(task, dict):
        for key in ["title", "objective", "scope"]:
            if not task.get(key):
                errors.append(f"missing required task field: {key}")
    elif "task" in request:
        errors.append("task must be an object")

    workspace = request.get("workspace")
    if isinstance(workspace, dict):
        for key in ["root", "read_paths", "write_path"]:
            if key not in workspace:
                errors.append(f"missing required workspace field: {key}")
        if "read_paths" in workspace and not isinstance(workspace["read_paths"], list):
            errors.append("workspace.read_paths must be a list")
    elif "workspace" in request:
        errors.append("workspace must be an object")

    budget = request.get("budget")
    if isinstance(budget, dict):
        if not isinstance(budget.get("max_attempts"), int):
            errors.append("budget.max_attempts must be an integer")
        if not isinstance(budget.get("max_wall_time_minutes"), int):
            errors.append("budget.max_wall_time_minutes must be an integer")
    elif "budget" in request:
        errors.append("budget must be an object")

    if "inputs" in request and not isinstance(request["inputs"], list):
        errors.append("inputs must be a list")
    if "success_criteria" in request and not isinstance(request["success_criteria"], list):
        errors.append("success_criteria must be a list")
    if "required_outputs" in request and not isinstance(request["required_outputs"], list):
        errors.append("required_outputs must be a list")
    return errors


def resolve_workspace(write_path: str) -> Path:
    path = Path(write_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    root = Path.cwd().resolve()
    resolved = path.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"workspace.write_path must stay inside repository root: {write_path}")
    return resolved


def artifact(
    artifact_id: str,
    path: Path,
    kind: str,
    description: str,
    file_format: str,
    role: str,
) -> dict[str, Any]:
    try:
        display_path = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        display_path = path.as_posix()
    return {
        "artifact_id": artifact_id,
        "path": display_path,
        "kind": kind,
        "description": description,
        "format": file_format,
        "role": role,
        "created_by_executor": True,
    }


def build_rejected_response(request: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    request_id = request.get("request_id") if isinstance(request.get("request_id"), str) else "unknown"
    return {
        "request_id": request_id,
        "status": "rejected",
        "summary": "Execution request failed minimal validation.",
        "artifacts": [],
        "validation": {"overall": "not_run", "checks": []},
        "attempts": [],
        "policy_observance": {
            "browser_used": False,
            "sessions_spawned": False,
            "external_post_performed": False,
            "write_scope_respected": True,
            "notes": "No execution was attempted.",
        },
        "limitations": errors,
    }


def run_minimal_execution(request: dict[str, Any]) -> dict[str, Any]:
    errors = validate_request(request)
    if errors:
        return build_rejected_response(request, errors)

    try:
        workspace = resolve_workspace(request["workspace"]["write_path"])
    except ValueError as exc:
        return build_rejected_response(request, [str(exc)])
    for name in ["work", "figures", "tables", "logs"]:
        (workspace / name).mkdir(parents=True, exist_ok=True)

    request_id = request["request_id"]
    criteria = request.get("success_criteria", [])
    read_paths = request["workspace"].get("read_paths", [])
    missing_inputs = [path for path in read_paths if not Path(path).exists()]

    results_path = workspace / "results.json"
    tests_path = workspace / "tests.json"
    environment_path = workspace / "environment.json"
    artifacts_path = workspace / "artifacts.json"
    notes_path = workspace / "notes.md"
    figure_path = workspace / "figures" / "attempt_01_placeholder_diagnostic.svg"
    table_path = workspace / "tables" / "attempt_01_placeholder_metrics.csv"
    log_path = workspace / "logs" / "execution.log"

    results = {
        "request_id": request_id,
        "mode": "minimal_runtime_placeholder",
        "task": request["task"],
        "baseline": {
            "name": "placeholder_baseline",
            "objective_value": 0.71,
        },
        "attempts": [
            {
                "attempt_id": "attempt_01",
                "description": "Placeholder execution used to test planner-executor wiring.",
                "objective_value": 0.78,
                "improved_over_baseline": True,
            }
        ],
        "best_attempt": {
            "attempt_id": "attempt_01",
            "objective_value": 0.78,
        },
    }
    write_json(results_path, results)

    validation_checks = [
        {
            "criterion_id": criterion.get("criterion_id", f"criterion_{index + 1}"),
            "status": "passed",
            "evidence": "Minimal runtime produced placeholder artifacts for integration testing.",
            "artifact_refs": ["results_main", "tests_main"],
        }
        for index, criterion in enumerate(criteria)
    ]
    tests = {
        "request_id": request_id,
        "overall": "passed",
        "checks": validation_checks,
        "note": "These are placeholder checks for runtime wiring, not real experiment validation.",
    }
    write_json(tests_path, tests)

    environment = {
        "request_id": request_id,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "role": ROLE,
        "schema_refs": SCHEMA_REFS,
    }
    write_json(environment_path, environment)

    figure_path.write_text(
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"640\" height=\"360\" viewBox=\"0 0 640 360\">\n"
        "  <rect width=\"640\" height=\"360\" fill=\"#ffffff\"/>\n"
        "  <line x1=\"80\" y1=\"300\" x2=\"580\" y2=\"300\" stroke=\"#222\"/>\n"
        "  <line x1=\"80\" y1=\"300\" x2=\"80\" y2=\"60\" stroke=\"#222\"/>\n"
        "  <polyline points=\"100,250 220,220 340,180 460,135 560,110\" fill=\"none\" stroke=\"#2563eb\" stroke-width=\"4\"/>\n"
        "  <text x=\"80\" y=\"35\" font-family=\"Arial\" font-size=\"22\">Placeholder diagnostic</text>\n"
        "  <text x=\"80\" y=\"335\" font-family=\"Arial\" font-size=\"14\">attempt_01</text>\n"
        "</svg>\n",
        encoding="utf-8",
    )

    table_path.write_text(
        "attempt_id,objective_value,improved_over_baseline\n"
        "baseline,0.71,false\n"
        "attempt_01,0.78,true\n",
        encoding="utf-8",
    )

    log_lines = [
        f"request_id={request_id}",
        "mode=minimal_runtime_placeholder",
        f"workspace={workspace}",
        f"missing_authorised_inputs={missing_inputs}",
        "browser_used=false",
        "sessions_spawned=false",
        "external_post_performed=false",
    ]
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    notes = [
        "# Executor Minimal Runtime Notes",
        "",
        "This run proves that the executor can accept a planner request, create a workspace, write artifacts, and return a structured response.",
        "",
        "The numerical values are placeholders. They must not be treated as real experiment results.",
    ]
    if missing_inputs:
        notes.extend(["", "Missing authorised input paths during this local smoke test:"])
        notes.extend(f"- `{path}`" for path in missing_inputs)
    notes_path.write_text("\n".join(notes) + "\n", encoding="utf-8")

    artifact_entries = [
        artifact("results_main", results_path, "results", "Placeholder result metrics.", "json", "primary_result"),
        artifact("tests_main", tests_path, "tests", "Placeholder validation checks.", "json", "audit"),
        artifact("environment_main", environment_path, "environment", "Runtime environment metadata.", "json", "audit"),
        artifact("artifacts_manifest", artifacts_path, "metadata", "Artifact manifest.", "json", "audit"),
        artifact("fig_attempt_01_placeholder_diagnostic", figure_path, "figure", "Placeholder diagnostic figure.", "svg", "diagnostic"),
        artifact("table_attempt_01_placeholder_metrics", table_path, "table", "Placeholder metrics table.", "csv", "supporting"),
        artifact("log_execution", log_path, "log", "Minimal runtime execution log.", "txt", "audit"),
        artifact("notes_main", notes_path, "notes", "Minimal runtime limitations and notes.", "md", "supporting"),
    ]
    write_json(artifacts_path, {"request_id": request_id, "artifacts": artifact_entries})

    response = {
        "request_id": request_id,
        "status": "succeeded",
        "summary": "Minimal executor runtime completed. Placeholder artifacts were written for planner integration testing.",
        "artifacts": artifact_entries,
        "validation": {
            "overall": "passed",
            "checks": validation_checks,
        },
        "attempts": [
            {
                "attempt_id": "attempt_01",
                "status": "succeeded",
                "description": "Created placeholder artifacts to test the executor runtime contract.",
                "artifact_refs": [
                    "results_main",
                    "tests_main",
                    "fig_attempt_01_placeholder_diagnostic",
                    "table_attempt_01_placeholder_metrics",
                ],
            }
        ],
        "policy_observance": {
            "browser_used": False,
            "sessions_spawned": False,
            "external_post_performed": False,
            "write_scope_respected": True,
            "notes": "All generated files were written under workspace.write_path.",
        },
        "limitations": [
            "This is a placeholder runtime for integration testing, not a real experiment.",
            "Missing authorised input paths are logged but do not block this smoke test.",
        ],
        "recommended_planner_next_steps": [
            "Use this response shape to test planner parsing.",
            "Replace placeholder execution with a planner-approved real experiment hook.",
        ],
    }
    write_json(workspace / "executor_response.json", response)
    return response


def validate_response(response: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "request_id",
        "status",
        "summary",
        "artifacts",
        "validation",
        "attempts",
        "policy_observance",
    ]
    for key in required:
        if key not in response:
            errors.append(f"missing response field: {key}")
    if response.get("status") not in {"succeeded", "failed", "partial", "rejected", "blocked"}:
        errors.append("response.status is not an allowed value")
    if not isinstance(response.get("artifacts"), list):
        errors.append("response.artifacts must be a list")
    if not isinstance(response.get("attempts"), list):
        errors.append("response.attempts must be a list")
    validation = response.get("validation")
    if not isinstance(validation, dict) or "overall" not in validation or "checks" not in validation:
        errors.append("response.validation must include overall and checks")
    policy = response.get("policy_observance")
    if isinstance(policy, dict):
        for key in ["browser_used", "sessions_spawned", "external_post_performed", "write_scope_respected"]:
            if key not in policy:
                errors.append(f"missing policy_observance field: {key}")
    else:
        errors.append("response.policy_observance must be an object")
    return errors


def write_or_print_response(response: dict[str, Any], output_path: str | None) -> None:
    payload = json.dumps(response, indent=2, sort_keys=True) + "\n"
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


def main() -> int:
    parser = argparse.ArgumentParser(description=PURPOSE)
    parser.add_argument("--request", help="Path to worker request JSON")
    parser.add_argument("--output", help="Path to write response JSON")
    args = parser.parse_args()

    response = run_minimal_execution(load_request(args.request))
    response_errors = validate_response(response)
    if response_errors:
        raise ValueError("; ".join(response_errors))
    write_or_print_response(response, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
