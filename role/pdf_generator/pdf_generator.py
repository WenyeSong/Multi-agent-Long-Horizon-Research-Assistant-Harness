#!/usr/bin/env python3
"""Problem-agnostic executable scaffold for the pdf_generator role."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROLE = "pdf_generator"
PURPOSE = "Typeset approved artifacts only; do not add facts or conclusions."
SCHEMA_REFS = ["schemas/report_spec.schema.json"]


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
        "approved_by_reviewer": request.get("approved_by_reviewer"),
        "next_step": "implement approved-content-only PDF generation here"
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=PURPOSE)
    parser.add_argument("--request", help="Path to report spec JSON")
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
