#!/usr/bin/env python3
"""Problem-agnostic executable scaffold for the literature_reviewer role."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROLE = "literature_reviewer"
PURPOSE = "Find and summarize papers, then return structured literature artifacts."
SCHEMA_REFS = ["schemas/literature_result.schema.json"]


def load_request(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def trace_id_from_request(request: dict[str, Any]) -> str:
    return str(request.get("trace_id") or "smoke_planarity")


def problem_summary_from_request(request: dict[str, Any]) -> str:
    return str(
        request.get("problem_summary")
        or request.get("task")
        or "methods for checking finite graph planarity"
    )


def build_response(request: dict[str, Any]) -> dict[str, Any]:
    """Return a schema-shaped fallback result for smoke tests.

    This scaffold deliberately avoids claiming real source discovery. Replace
    this function when the real browser-backed literature workflow is ready.
    """
    trace_id = trace_id_from_request(request)
    problem_summary = problem_summary_from_request(request)
    literature_dir = Path("projects") / trace_id / "literature"
    literature_dir.mkdir(parents=True, exist_ok=True)

    source_note = literature_dir / "smoke_source_note.md"
    method_matrix = literature_dir / "method_matrix.csv"
    selected_papers = literature_dir / "selected_papers.json"
    synthesis = literature_dir / "literature_synthesis.md"

    source_note.write_text(
        "# Smoke-test literature note\n\n"
        "This is a local placeholder. No browser, DOI, arXiv, or citation "
        "lookup was performed.\n",
        encoding="utf-8",
    )
    method_matrix.write_text(
        "topic,method_family,smoke_note\n"
        "finite graph planarity,embedding and obstruction tests,"
        "placeholder only; replace with real literature matrix\n",
        encoding="utf-8",
    )
    synthesis.write_text(
        "# Smoke-test synthesis\n\n"
        f"Problem summary: {problem_summary}\n\n"
        "Likely method families to investigate include Kuratowski-style "
        "obstruction checks, DFS/embedding algorithms, and certificate-based "
        "planarity validation. This is not a real literature review.\n",
        encoding="utf-8",
    )

    paper = {
        "title": "Smoke-test placeholder source for finite graph planarity",
        "authors": ["OpenClaw smoke scaffold"],
        "year": 2026,
        "venue": "Local smoke-test artifact",
        "doi_or_arxiv": "local-placeholder",
        "url": source_note.as_posix(),
        "relevance_score": 0.1,
        "method_summary": "Placeholder for planarity methods; no external source lookup was performed.",
        "key_equations": [],
        "assumptions": ["The planner is running a local smoke test."],
        "limitations": ["Not a real citation.", "Must be replaced by browser-backed literature review."],
        "connection_to_problem": f"Marks the intended literature direction for: {problem_summary}",
        "source_confidence": "low",
    }
    selected_papers.write_text(json.dumps([paper], indent=2) + "\n", encoding="utf-8")

    return {
        "trace_id": trace_id,
        "status": "partial",
        "selected_papers": [paper],
        "theme_analysis": {
            "themes": ["planarity certificates", "graph embeddings", "forbidden minors"],
            "method_families": ["Kuratowski obstruction checks", "DFS embedding tests", "Boyer-Myrvold-style algorithms"],
        },
        "risks": [
            "Smoke-test fallback only; selected_papers contains placeholders, not verified literature.",
            "The real literature_reviewer must replace this with cited sources before research use.",
        ],
        "artifact_refs": [
            method_matrix.as_posix(),
            selected_papers.as_posix(),
            synthesis.as_posix(),
        ],
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
