#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from review_utils import load_json, write_json


def route_from_review(report: dict[str, Any]) -> dict[str, str]:
    decision = report.get("decision")
    route = report.get("route_suggestion") or "planner"
    if decision == "PASS":
        return {"next_action": "spawn_pdf_generator", "target": "pdf_generator"}
    if decision == "REVISE":
        target = route if route in {"executor", "literature_reviewer", "pdf_generator"} else "planner"
        return {"next_action": f"revise_{target}", "target": target}
    if decision == "REPLAN":
        return {"next_action": "revise_plan", "target": "planner"}
    if decision == "BLOCK":
        return {"next_action": "block_for_human", "target": "main"}
    return {"next_action": "collect_missing_review_material", "target": "planner"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Map reviewer decision to planner route.")
    parser.add_argument("--report", default="role/reviewer/workspace/outbox/review_report.json")
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    route = route_from_review(load_json(Path(args.report)))
    if args.output:
        write_json(Path(args.output), route)
    else:
        print(json.dumps(route, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
