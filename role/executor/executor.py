#!/usr/bin/env python3
"""Problem-agnostic executable scaffold for the executor role."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROLE = "executor"
PURPOSE = "Design experiments, run reproducibility checks, and return execution artifacts."
SCHEMA_REFS = [
    "schemas/execution_result.schema.json",
    "role/executor/schemas/execution_request.schema.json",
    "role/executor/schemas/execution_result.schema.json",
]


def load_request(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def trace_id_from_request(request: dict[str, Any]) -> str:
    return str(request.get("trace_id") or request.get("request_id") or "smoke_planarity")


def compliance_mode_from_request(request: dict[str, Any]) -> str:
    mode = request.get("compliance_mode")
    return str(mode) if mode in {"study_assistant", "independent_research"} else "study_assistant"


def build_response(request: dict[str, Any]) -> dict[str, Any]:
    """Return a schema-shaped fallback result for smoke tests.

    This does not run real experiments. Replace this function when the sandboxed
    execution runtime is ready.
    """
    trace_id = trace_id_from_request(request)
    compliance_mode = compliance_mode_from_request(request)
    execution_mode = "independent_research" if compliance_mode == "independent_research" else "research_support"
    execution_dir = Path("projects") / trace_id / "execution"
    src_dir = execution_dir / "src"
    figures_dir = execution_dir / "figures"
    src_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    notes_path = src_dir / "planarity_methods_pseudocode.md"
    figure_path = figures_dir / "planarity_decision_flow.txt"
    results_path = execution_dir / "results.json"
    tests_path = execution_dir / "tests.json"
    environment_path = execution_dir / "environment.json"

    notes_path.write_text(
        "# Smoke-test executor notes\n\n"
        "Suggested planarity checks:\n\n"
        "1. Reject obvious non-planar dense graphs with the edge bound "
        "`m <= 3n - 6` for simple graphs with `n >= 3`.\n"
        "2. Run an embedding-based planarity algorithm for the real check.\n"
        "3. Validate certificates with known cases: trees are planar; `K5` "
        "and `K3,3` are non-planar.\n\n"
        "This is pseudocode guidance only, not submit-ready source code.\n",
        encoding="utf-8",
    )
    figure_path.write_text(
        "Input graph -> simple checks -> embedding attempt -> certificate validation -> result\n",
        encoding="utf-8",
    )

    result_payload = {
        "smoke_test": True,
        "topic": "methods for checking finite graph planarity",
        "known_cases": ["trees: planar", "K5: non-planar", "K3,3: non-planar"],
    }
    results_path.write_text(json.dumps(result_payload, indent=2) + "\n", encoding="utf-8")
    tests_path.write_text(
        json.dumps(
            {
                "smoke_test": True,
                "checks": [
                    "Use K5 and K3,3 as negative controls.",
                    "Use paths, cycles, and trees as positive controls.",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    environment_path.write_text(
        json.dumps({"runtime": "fallback", "real_experiments_run": False}, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "trace_id": trace_id,
        "status": "partial",
        "compliance_mode": compliance_mode,
        "execution_mode": execution_mode,
        "algorithm_plan": (
            "Smoke-test plan: compare simple necessary conditions, "
            "embedding-based planarity tests, and certificate validation on "
            "small known graphs. No real experiment was run."
        ),
        "code_artifacts": [
            {
                "path": notes_path.as_posix(),
                "purpose": "Fallback pseudocode notes for planarity checking methods.",
                "submission_safe": True,
            }
        ],
        "figures": [
            {
                "path": figure_path.as_posix(),
                "caption": "Text-only smoke-test decision flow for planarity checking.",
                "axes_described": True,
                "parameters_described": True,
            }
        ],
        "results": {
            "main_findings": [
                "Fallback scaffold identified method families but did not run algorithms.",
                "Known examples for validation should include planar trees and non-planar K5/K3,3.",
            ],
            "numerical_checks": ["No numerical checks were run in fallback mode."],
            "known_case_validation": ["Suggested but not executed: trees, cycles, K5, K3,3."],
            "reproducibility_notes": [
                f"Smoke artifacts were written under {execution_dir.as_posix()}."
            ],
        },
        "limitations": [
            "Fallback executor does not execute code or verify graph embeddings.",
            "Replace this scaffold before relying on computational findings.",
        ],
        "coursework_safety": {
            "direct_submission_artifacts": [],
            "notes": [
                "Artifacts are research-support placeholders and not submit-ready source code.",
            ],
        },
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
