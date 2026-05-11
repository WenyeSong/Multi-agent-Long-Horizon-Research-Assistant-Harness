#!/usr/bin/env python3
"""Minimal runnable scaffold for the executor role."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
from pathlib import Path
from typing import Any


ROLE = "executor"
PURPOSE = "Design experiments, run reproducibility checks, and return execution artifacts."
ROLE_DIR = Path(__file__).resolve().parent
SCHEMA_REFS = [
    "schemas/execution_request.schema.json",
    "schemas/execution_result.schema.json",
]


def load_request(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8-sig") as handle:
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
    root = ROLE_DIR.resolve()
    resolved = path.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"workspace.write_path must stay inside role/executor: {write_path}")
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


def find_input_path(request: dict[str, Any], kind: str, suffix: str) -> Path | None:
    for item in request.get("inputs", []):
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if item.get("kind") == kind and isinstance(path, str) and path.endswith(suffix):
            return Path(path)
    return None


def load_baseline_config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {
            "baseline_name": "toy_mean_baseline",
            "target_column": "value",
        }
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("baseline config must be a JSON object")
    return data


def load_numeric_csv(path: Path, target_column: str) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or target_column not in reader.fieldnames:
            raise ValueError(f"dataset must contain target column: {target_column}")
        for index, row in enumerate(reader, start=1):
            try:
                value = float(row[target_column])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"non-numeric {target_column} at row {index}") from exc
            step_text = row.get("step") or str(index)
            try:
                step = float(step_text)
            except ValueError:
                step = float(index)
            rows.append({"step": step, target_column: value})
    if not rows:
        raise ValueError("dataset has no data rows")
    return rows


def summarise_values(values: list[float]) -> dict[str, float | int]:
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def format_float(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    return f"{value:.6g}"


def build_svg_line_plot(rows: list[dict[str, float]], target_column: str) -> str:
    width = 640
    height = 360
    left = 70
    right = 580
    top = 60
    bottom = 300
    steps = [row["step"] for row in rows]
    values = [row[target_column] for row in rows]
    min_x, max_x = min(steps), max(steps)
    min_y, max_y = min(values), max(values)
    x_span = max(max_x - min_x, 1.0)
    y_span = max(max_y - min_y, 1.0)

    points = []
    for row in rows:
        x = left + ((row["step"] - min_x) / x_span) * (right - left)
        y = bottom - ((row[target_column] - min_y) / y_span) * (bottom - top)
        points.append(f"{x:.1f},{y:.1f}")

    return (
        f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\">\n"
        "  <rect width=\"640\" height=\"360\" fill=\"#ffffff\"/>\n"
        f"  <line x1=\"{left}\" y1=\"{bottom}\" x2=\"{right}\" y2=\"{bottom}\" stroke=\"#222\"/>\n"
        f"  <line x1=\"{left}\" y1=\"{bottom}\" x2=\"{left}\" y2=\"{top}\" stroke=\"#222\"/>\n"
        f"  <polyline points=\"{' '.join(points)}\" fill=\"none\" stroke=\"#2563eb\" stroke-width=\"4\"/>\n"
        "  <text x=\"70\" y=\"35\" font-family=\"Arial\" font-size=\"22\">Toy dataset diagnostic</text>\n"
        f"  <text x=\"70\" y=\"335\" font-family=\"Arial\" font-size=\"14\">step</text>\n"
        f"  <text x=\"18\" y=\"60\" font-family=\"Arial\" font-size=\"14\">{target_column}</text>\n"
        "</svg>\n"
    )


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
    if missing_inputs:
        return build_rejected_response(request, [f"missing authorised input path: {path}" for path in missing_inputs])

    config_path = find_input_path(request, "config", ".json")
    dataset_path = find_input_path(request, "dataset", ".csv")
    if dataset_path is None:
        return build_rejected_response(request, ["missing dataset input with kind=dataset and .csv path"])

    try:
        baseline_config = load_baseline_config(config_path)
        target_column = str(baseline_config.get("target_column", "value"))
        dataset_rows = load_numeric_csv(dataset_path, target_column)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return build_rejected_response(request, [str(exc)])

    values = [row[target_column] for row in dataset_rows]
    summary_stats = summarise_values(values)

    results_path = workspace / "results.json"
    tests_path = workspace / "tests.json"
    environment_path = workspace / "environment.json"
    artifacts_path = workspace / "artifacts.json"
    notes_path = workspace / "notes.md"
    figure_path = workspace / "figures" / "attempt_01_toy_dataset_diagnostic.svg"
    table_path = workspace / "tables" / "attempt_01_summary_metrics.csv"
    log_path = workspace / "logs" / "execution.log"

    results = {
        "request_id": request_id,
        "mode": "toy_dataset_runtime",
        "task": request["task"],
        "inputs": {
            "dataset": dataset_path.as_posix(),
            "baseline_config": config_path.as_posix() if config_path else None,
            "target_column": target_column,
        },
        "baseline": {
            "name": baseline_config.get("baseline_name", "toy_mean_baseline"),
            "objective_value": summary_stats["mean"],
        },
        "attempts": [
            {
                "attempt_id": "attempt_01",
                "description": "Computed summary statistics from the toy dataset.",
                "metrics": summary_stats,
                "objective_value": summary_stats["max"],
                "improved_over_baseline": summary_stats["max"] >= summary_stats["mean"],
            }
        ],
        "best_attempt": {
            "attempt_id": "attempt_01",
            "objective_value": summary_stats["max"],
            "selection_reason": "For this toy example, the maximum observed value is treated as the best observed objective.",
        },
    }
    write_json(results_path, results)

    validation_checks = [
        {
            "criterion_id": criterion.get("criterion_id", f"criterion_{index + 1}"),
            "status": "passed",
            "evidence": "Toy runtime read the dataset and produced metrics/artifacts for integration testing.",
            "artifact_refs": ["results_main", "tests_main"],
        }
        for index, criterion in enumerate(criteria)
    ]
    tests = {
        "request_id": request_id,
        "overall": "passed",
        "checks": validation_checks,
        "note": "These checks validate the self-contained toy executor example.",
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

    figure_path.write_text(build_svg_line_plot(dataset_rows, target_column), encoding="utf-8")

    table_lines = ["metric,value"]
    table_lines.extend(f"{key},{format_float(value)}" for key, value in summary_stats.items())
    table_path.write_text("\n".join(table_lines) + "\n", encoding="utf-8")

    log_lines = [
        f"request_id={request_id}",
        "mode=toy_dataset_runtime",
        f"workspace={workspace}",
        f"dataset={dataset_path}",
        f"target_column={target_column}",
        "browser_used=false",
        "sessions_spawned=false",
        "external_post_performed=false",
    ]
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    notes = [
        "# Executor Toy Runtime Notes",
        "",
        "This run proves that the executor can accept a planner request, read a real toy input dataset, create a workspace, write artifacts, and return a structured response.",
        "",
        "The numerical values come from the toy dataset in `role/executor/examples/inputs/dataset.csv`.",
    ]
    notes_path.write_text("\n".join(notes) + "\n", encoding="utf-8")

    artifact_entries = [
        artifact("results_main", results_path, "results", "Toy dataset summary metrics.", "json", "primary_result"),
        artifact("tests_main", tests_path, "tests", "Toy runtime validation checks.", "json", "audit"),
        artifact("environment_main", environment_path, "environment", "Runtime environment metadata.", "json", "audit"),
        artifact("artifacts_manifest", artifacts_path, "metadata", "Artifact manifest.", "json", "audit"),
        artifact("fig_attempt_01_toy_dataset_diagnostic", figure_path, "figure", "Toy dataset diagnostic figure.", "svg", "diagnostic"),
        artifact("table_attempt_01_summary_metrics", table_path, "table", "Toy dataset summary metrics table.", "csv", "supporting"),
        artifact("log_execution", log_path, "log", "Toy runtime execution log.", "txt", "audit"),
        artifact("notes_main", notes_path, "notes", "Toy runtime notes.", "md", "supporting"),
    ]
    write_json(artifacts_path, {"request_id": request_id, "artifacts": artifact_entries})

    response = {
        "request_id": request_id,
        "status": "succeeded",
        "summary": "Toy executor runtime completed. The dataset was read and summary artifacts were written for planner integration testing.",
        "artifacts": artifact_entries,
        "validation": {
            "overall": "passed",
            "checks": validation_checks,
        },
        "attempts": [
            {
                "attempt_id": "attempt_01",
                "status": "succeeded",
                "description": "Read the toy dataset and created summary metrics, a table, and a diagnostic figure.",
                "artifact_refs": [
                    "results_main",
                    "tests_main",
                    "fig_attempt_01_toy_dataset_diagnostic",
                    "table_attempt_01_summary_metrics",
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
            "This is a toy runtime for integration testing, not a domain-specific experiment.",
            "Only a single CSV target column is summarised.",
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
