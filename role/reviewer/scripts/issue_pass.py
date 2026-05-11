#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from review_utils import load_json, sha256_file, utc_now, write_json


def issue_pass_token(report: dict[str, Any], manifest: dict[str, Any], output_path: Path) -> dict[str, Any] | None:
    if report.get("decision") != "PASS":
        return None
    artifacts = manifest.get("artifacts", [])
    if not artifacts:
        return None
    token = {
        "version": 1,
        "task_id": report["task_id"],
        "state_version": report["state_version"],
        "review_id": report.get("review_id"),
        "issued_at": utc_now(),
        "decision": "PASS",
        "artifact_hashes": [
            {
                "path": artifact["path"],
                "sha256": artifact["sha256"],
            }
            for artifact in artifacts
        ],
    }
    report_path = output_path.parent / "review_report.json"
    if report_path.exists():
        token["review_report_sha256"] = sha256_file(report_path)
    write_json(output_path, token)
    return token


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Issue pass token for PASS review reports.")
    parser.add_argument("--report", default="role/reviewer/workspace/outbox/review_report.json")
    parser.add_argument("--manifest", default="role/reviewer/workspace/scratch/artifact_manifest.json")
    parser.add_argument("--output", default="role/reviewer/workspace/outbox/pass_token.json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    token = issue_pass_token(load_json(Path(args.report)), load_json(Path(args.manifest)), Path(args.output))
    if token is None:
        print("no pass token issued")
        return 1
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
