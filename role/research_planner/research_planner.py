#!/usr/bin/env python3
"""Problem-agnostic executable scaffold for the research_planner role."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROLE = "research_planner"
PURPOSE = "Finite-state orchestrator. Reads state, dispatches workers, records decisions."
SCHEMA_REFS = ["schemas/state.schema.json"]
WORKER_ROLES = ["literature_reviewer", "executor", "reviewer", "pdf_generator"]


def load_request(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_response(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": ROLE,
        "status": "ready",
        "purpose": PURPOSE,
        "schema_refs": SCHEMA_REFS,
        "worker_roles": WORKER_ROLES,
        "request_trace_id": request.get("trace_id"),
        "next_step": "implement planner state transition logic here"
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=PURPOSE)
    parser.add_argument("--request", help="Path to planner request JSON")
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
