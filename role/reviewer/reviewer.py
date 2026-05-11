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
        "request_trace_id": request.get("trace_id"),
        "next_step": "implement PASS/REVISE/BLOCK gate here"
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
