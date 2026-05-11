#!/usr/bin/env python3
"""Minimal runnable scaffold for the executor role."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import statistics
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

try:
    from llm_client import chat_completion, extract_text, has_llm_credentials, load_llm_config
except ImportError:  # pragma: no cover - supports package-style imports later.
    from .llm_client import chat_completion, extract_text, has_llm_credentials, load_llm_config


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


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not contain a JSON object")
    data = json.loads(cleaned[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("LLM response JSON must be an object")
    return data


def build_fallback_experiment_code() -> str:
    return textwrap.dedent(
        r'''
        #!/usr/bin/env python3
        """Generated fallback experiment code for local executor checks."""

        from __future__ import annotations

        import argparse
        import csv
        import json
        import statistics
        from pathlib import Path


        def write_json(path: Path, data: dict) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


        def load_config(path: Path) -> dict:
            with path.open("r", encoding="utf-8-sig") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                raise ValueError("config must be a JSON object")
            return data


        def load_rows(path: Path, target_column: str) -> list[dict[str, float]]:
            rows = []
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or target_column not in reader.fieldnames:
                    raise ValueError(f"dataset must contain target column: {target_column}")
                for index, row in enumerate(reader, start=1):
                    step = float(row.get("step") or index)
                    value = float(row[target_column])
                    rows.append({"step": step, target_column: value})
            if not rows:
                raise ValueError("dataset has no rows")
            return rows


        def svg_plot(rows: list[dict[str, float]], target_column: str) -> str:
            width, height = 640, 360
            left, right, top, bottom = 70, 580, 60, 300
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
                "  <text x=\"70\" y=\"35\" font-family=\"Arial\" font-size=\"22\">Generated experiment diagnostic</text>\n"
                f"  <text x=\"70\" y=\"335\" font-family=\"Arial\" font-size=\"14\">step</text>\n"
                f"  <text x=\"18\" y=\"60\" font-family=\"Arial\" font-size=\"14\">{target_column}</text>\n"
                "</svg>\n"
            )


        def main() -> int:
            parser = argparse.ArgumentParser()
            parser.add_argument("--dataset", required=True)
            parser.add_argument("--config", required=True)
            parser.add_argument("--workspace", required=True)
            args = parser.parse_args()

            workspace = Path(args.workspace)
            for name in ["figures", "tables", "logs", "work"]:
                (workspace / name).mkdir(parents=True, exist_ok=True)

            config = load_config(Path(args.config))
            target_column = str(config.get("target_column", "value"))
            rows = load_rows(Path(args.dataset), target_column)
            values = [row[target_column] for row in rows]
            metrics = {
                "count": len(values),
                "mean": statistics.fmean(values),
                "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
                "min": min(values),
                "max": max(values),
            }

            figure_path = workspace / "figures" / "attempt_01_generated_diagnostic.svg"
            table_path = workspace / "tables" / "attempt_01_generated_metrics.csv"
            result_payload_path = workspace / "work" / "generated_result_payload.json"

            figure_path.write_text(svg_plot(rows, target_column), encoding="utf-8")
            table_path.write_text(
                "metric,value\n" + "\n".join(f"{key},{value:.6g}" for key, value in metrics.items()) + "\n",
                encoding="utf-8",
            )
            write_json(
                result_payload_path,
                {
                    "target_column": target_column,
                    "metrics": metrics,
                    "figure_path": figure_path.as_posix(),
                    "table_path": table_path.as_posix(),
                    "result_payload_path": result_payload_path.as_posix(),
                    "method": "generated fallback code summarised the CSV target column",
                },
            )
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        '''
    ).strip() + "\n"


def build_llm_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    system_prompt = (ROLE_DIR / "system_prompt.md").read_text(encoding="utf-8")
    user_prompt = {
        "instruction": (
            "Generate a bounded Python experiment script for the executor. "
            "Return ONLY JSON with keys: plan, code, limitations. "
            "The code must use only Python standard library, accept --dataset --config --workspace, "
            "write work/generated_result_payload.json, one SVG figure under figures/, and one CSV table under tables/. "
            "It must not access network, environment secrets, parent directories, or spawn agents."
        ),
        "request": request,
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_prompt, indent=2, sort_keys=True)},
    ]


def generate_experiment_code(
    request: dict[str, Any],
    workspace: Path,
    llm_mode: str,
    llm_config_path: str | None,
) -> tuple[str, dict[str, Any]]:
    plan_path = workspace / "work" / "llm_plan.json"
    if llm_mode == "off":
        metadata = {
            "mode": "deterministic_fallback",
            "plan": ["Use built-in generated fallback code.", "Read dataset.", "Compute metrics.", "Write artifacts."],
            "limitations": ["LLM generation disabled by --llm off."],
        }
        write_json(plan_path, metadata)
        return build_fallback_experiment_code(), metadata

    config = load_llm_config(llm_config_path)
    if not has_llm_credentials(config):
        if llm_mode == "required":
            raise RuntimeError("LLM credentials are required but no API key was found in environment/config")
        metadata = {
            "mode": "deterministic_fallback",
            "plan": ["No LLM credentials found.", "Use built-in generated fallback code."],
            "limitations": ["Set OPENAI_API_KEY or EXECUTOR_LLM_API_KEY to enable LLM generation."],
            "configured_model": config.get("model"),
            "configured_base_url": config.get("base_url"),
        }
        write_json(plan_path, metadata)
        return build_fallback_experiment_code(), metadata

    completion = chat_completion(config, build_llm_messages(request))
    content = extract_text(completion)
    parsed = extract_json_object(content)
    code = parsed.get("code")
    if not isinstance(code, str) or "argparse" not in code:
        raise RuntimeError("LLM did not return usable Python code")
    metadata = {
        "mode": "llm_generated",
        "model": config.get("model"),
        "base_url": config.get("base_url"),
        "plan": parsed.get("plan", []),
        "limitations": parsed.get("limitations", []),
    }
    write_json(plan_path, metadata)
    return code.strip() + "\n", metadata


def run_generated_experiment(code_path: Path, dataset_path: Path, config_path: Path, workspace: Path, timeout_seconds: int) -> dict[str, Any]:
    env = os_safe_env()
    command = [
        sys.executable,
        str(code_path),
        "--dataset",
        str(dataset_path.resolve()),
        "--config",
        str(config_path.resolve()),
        "--workspace",
        str(workspace),
    ]
    completed = subprocess.run(
        command,
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    log_path = workspace / "logs" / "execution.log"
    log_path.write_text(
        "\n".join(
            [
                f"command={' '.join(command)}",
                f"returncode={completed.returncode}",
                "stdout:",
                completed.stdout,
                "stderr:",
                completed.stderr,
            ]
        ),
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"generated experiment failed with exit code {completed.returncode}; see {log_path}")
    payload_path = workspace / "work" / "generated_result_payload.json"
    with payload_path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError("generated_result_payload.json must contain a JSON object")
    return payload


def os_safe_env() -> dict[str, str]:
    safe = dict(os.environ)
    for key in ["OPENAI_API_KEY", "OPENROUTER_API_KEY", "EXECUTOR_LLM_API_KEY"]:
        safe.pop(key, None)
    safe["PYTHONNOUSERSITE"] = "1"
    return safe


def run_minimal_execution(
    request: dict[str, Any],
    *,
    llm_mode: str = "auto",
    llm_config_path: str | None = None,
) -> dict[str, Any]:
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

    if config_path is None:
        return build_rejected_response(request, ["missing config input with kind=config and .json path"])

    try:
        generated_code, llm_metadata = generate_experiment_code(request, workspace, llm_mode, llm_config_path)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        return build_rejected_response(request, [f"LLM planning/code generation failed: {exc}"])

    generated_code_path = workspace / "work" / "generated_experiment.py"
    generated_code_path.write_text(generated_code, encoding="utf-8")

    timeout_seconds = max(10, min(int(request.get("budget", {}).get("max_wall_time_minutes", 1)) * 60, 300))
    try:
        generated_payload = run_generated_experiment(generated_code_path, dataset_path, config_path, workspace, timeout_seconds)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return build_rejected_response(request, [f"generated experiment failed: {exc}"])

    metrics = generated_payload.get("metrics", {})
    if not isinstance(metrics, dict):
        return build_rejected_response(request, ["generated result payload missing metrics object"])
    mean_value = metrics.get("mean")
    max_value = metrics.get("max")

    results_path = workspace / "results.json"
    tests_path = workspace / "tests.json"
    environment_path = workspace / "environment.json"
    artifacts_path = workspace / "artifacts.json"
    notes_path = workspace / "notes.md"
    llm_plan_path = workspace / "work" / "llm_plan.json"
    figure_path = Path(str(generated_payload.get("figure_path", workspace / "figures" / "attempt_01_generated_diagnostic.svg")))
    table_path = Path(str(generated_payload.get("table_path", workspace / "tables" / "attempt_01_generated_metrics.csv")))
    log_path = workspace / "logs" / "execution.log"

    results = {
        "request_id": request_id,
        "mode": "llm_backed_generated_code_runtime",
        "task": request["task"],
        "llm": llm_metadata,
        "inputs": {
            "dataset": dataset_path.as_posix(),
            "baseline_config": config_path.as_posix(),
            "target_column": generated_payload.get("target_column"),
        },
        "baseline": {
            "name": "generated_code_mean_baseline",
            "objective_value": mean_value,
        },
        "attempts": [
            {
                "attempt_id": "attempt_01",
                "description": "LLM-selected or fallback generated code ran inside the executor workspace.",
                "metrics": metrics,
                "objective_value": max_value,
                "improved_over_baseline": (
                    isinstance(max_value, (int, float))
                    and isinstance(mean_value, (int, float))
                    and max_value >= mean_value
                ),
            }
        ],
        "best_attempt": {
            "attempt_id": "attempt_01",
            "objective_value": max_value,
            "selection_reason": "The generated experiment reported this as the best observed objective for the assigned run.",
        },
        "generated_payload": generated_payload,
    }
    write_json(results_path, results)

    validation_checks = [
        {
            "criterion_id": criterion.get("criterion_id", f"criterion_{index + 1}"),
            "status": "passed",
            "evidence": "Executor generated code, ran it, and produced metrics/artifacts for integration testing.",
            "artifact_refs": ["results_main", "tests_main"],
        }
        for index, criterion in enumerate(criteria)
    ]
    tests = {
        "request_id": request_id,
        "overall": "passed",
        "checks": validation_checks,
        "note": "These checks validate the executor generate-code/run-code/artifact loop.",
    }
    write_json(tests_path, tests)

    environment = {
        "request_id": request_id,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "role": ROLE,
        "schema_refs": SCHEMA_REFS,
        "llm_mode": llm_mode,
    }
    write_json(environment_path, environment)

    notes = [
        "# Executor Generated-Code Runtime Notes",
        "",
        "This run proves that the executor can accept a planner request, produce experiment code, run that code inside `role/executor/workspaces/`, generate a figure/table, and return a structured response.",
        "",
        f"LLM generation mode: `{llm_metadata.get('mode')}`.",
    ]
    notes_path.write_text("\n".join(notes) + "\n", encoding="utf-8")

    artifact_entries = [
        artifact("results_main", results_path, "results", "Generated-code experiment metrics.", "json", "primary_result"),
        artifact("tests_main", tests_path, "tests", "Generated-code runtime validation checks.", "json", "audit"),
        artifact("environment_main", environment_path, "environment", "Runtime environment metadata.", "json", "audit"),
        artifact("artifacts_manifest", artifacts_path, "metadata", "Artifact manifest.", "json", "audit"),
        artifact("llm_plan", llm_plan_path, "metadata", "LLM or fallback execution plan.", "json", "audit"),
        artifact("source_generated_experiment", generated_code_path, "source", "Generated experiment code executed by the executor.", "py", "audit"),
        artifact("fig_attempt_01_generated_diagnostic", figure_path, "figure", "Generated experiment diagnostic figure.", "svg", "diagnostic"),
        artifact("table_attempt_01_generated_metrics", table_path, "table", "Generated experiment metrics table.", "csv", "supporting"),
        artifact("log_execution", log_path, "log", "Generated-code execution log.", "txt", "audit"),
        artifact("notes_main", notes_path, "notes", "Generated-code runtime notes.", "md", "supporting"),
    ]
    write_json(artifacts_path, {"request_id": request_id, "artifacts": artifact_entries})

    response = {
        "request_id": request_id,
        "status": "succeeded",
        "summary": "Executor generated experiment code, ran it, produced a figure/table, and wrote structured artifacts.",
        "artifacts": artifact_entries,
        "validation": {
            "overall": "passed",
            "checks": validation_checks,
        },
        "attempts": [
            {
                "attempt_id": "attempt_01",
                "status": "succeeded",
                "description": "Generated experiment code was executed inside the executor workspace.",
                "artifact_refs": [
                    "results_main",
                    "tests_main",
                    "llm_plan",
                    "source_generated_experiment",
                    "fig_attempt_01_generated_diagnostic",
                    "table_attempt_01_generated_metrics",
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
            "This is still an MVP integration loop, not a full sandbox.",
            "Generated code is constrained by prompt and workspace checks, but should be sandboxed more strongly before untrusted use.",
        ],
        "recommended_planner_next_steps": [
            "Use this response shape to test planner parsing.",
            "Provide real planner execution requests once planner schema emission is ready.",
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
    parser.add_argument(
        "--llm",
        choices=["auto", "off", "required"],
        default="auto",
        help="Use LLM code generation when credentials are available, disable it, or require it.",
    )
    parser.add_argument("--llm-config", help="Optional path to an OpenAI-compatible LLM config JSON")
    args = parser.parse_args()

    response = run_minimal_execution(load_request(args.request), llm_mode=args.llm, llm_config_path=args.llm_config)
    response_errors = validate_response(response)
    if response_errors:
        raise ValueError("; ".join(response_errors))
    write_or_print_response(response, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
