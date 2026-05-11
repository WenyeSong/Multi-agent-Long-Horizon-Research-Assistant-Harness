#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from review_utils import load_json, new_review_id, utc_now


HEADER = [
    "review_id",
    "task_id",
    "state_version",
    "decision",
    "route",
    "blocking_count",
    "major_count",
    "advisory_count",
    "summary",
    "created_at",
]


def append_review_record(report: dict[str, Any], log_path: Path) -> str:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    review_id = str(report.get("review_id") or new_review_id())
    report["review_id"] = review_id
    row = {
        "review_id": review_id,
        "task_id": report.get("task_id", "task_unknown"),
        "state_version": report.get("state_version", "unknown"),
        "decision": report.get("decision", "INCONCLUSIVE"),
        "route": report.get("route_suggestion", "planner"),
        "blocking_count": len(report.get("blocking_issues", [])),
        "major_count": len(report.get("major_issues", [])),
        "advisory_count": len(report.get("advisory_notes", [])),
        "summary": str(report.get("summary", "")).replace("\t", " ").replace("\n", " "),
        "created_at": utc_now(),
    }
    should_write_header = not log_path.exists() or log_path.stat().st_size == 0
    with log_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER, delimiter="\t")
        if should_write_header:
            writer.writeheader()
        writer.writerow(row)
    return review_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append a reviewer TSV log row.")
    parser.add_argument("--report", default="role/reviewer/workspace/outbox/review_report.json")
    parser.add_argument("--log", default="role/reviewer/workspace/logs/review.tsv")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = load_json(Path(args.report))
    review_id = append_review_record(report, Path(args.log))
    print(review_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
