#!/usr/bin/env python3
"""Compatibility entrypoint for the legacy pdf_generator role.

The role name remains ``pdf_generator`` for planner compatibility, but the
current implementation emits an HTML research report through html_generator.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from html_generator import run_html_generator
except ImportError:  # pragma: no cover - used when imported as a package
    from .html_generator import run_html_generator

ROLE = "pdf_generator"
PURPOSE = "Legacy-named report generator; emits approved HTML, not PDF."
SCHEMA_REFS = ["schemas/report_spec.schema.json"]


def run_pdf_generator(request: dict[str, Any]) -> dict[str, Any]:
    """Render approved artifacts as HTML while preserving the old role contract."""
    response = run_html_generator(request)
    response["role"] = ROLE
    response["renderer"] = "html_generator"
    response["output_format"] = "html"
    return response


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render an approved research memo as HTML via the legacy pdf_generator role."
    )
    parser.add_argument("request_json", help="Path to report_spec JSON")
    args = parser.parse_args()

    request_path = Path(args.request_json)
    with request_path.open("r", encoding="utf-8") as handle:
        request = json.load(handle)

    json.dump(run_pdf_generator(request), sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
