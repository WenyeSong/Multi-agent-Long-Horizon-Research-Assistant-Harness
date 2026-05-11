#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from review_utils import (
    allowed_read_roots,
    display_path,
    ensure_workspace,
    extract_path_refs,
    get_path_from_packet,
    load_json,
    path_allowed,
    resolve_ref,
    write_json,
)


def run_preflight(packet_path: Path, repo_root: Path, reviewer_workspace: Path) -> dict[str, Any]:
    ensure_workspace(reviewer_workspace)
    blockers: list[str] = []
    warnings: list[str] = []
    checked_paths: list[dict[str, Any]] = []

    if not packet_path.exists():
        return {
            "status": "failed",
            "blockers": [f"review packet is missing: {packet_path}"],
            "warnings": [],
            "checked_paths": [],
            "required_paths": {},
        }

    packet = load_json(packet_path)
    roots = allowed_read_roots(repo_root, reviewer_workspace)
    required = {
        "planner_state": get_path_from_packet(packet, "planner_state", "state", "state_path"),
        "executor_output_dir": get_path_from_packet(
            packet,
            "executor_output_dir",
            "executor_artifacts_dir",
            "executor_outbox",
        ),
    }
    requires_literature = bool(packet.get("requires_literature", packet.get("literature_required", False)))
    evidence_matrix = get_path_from_packet(packet, "evidence_matrix", "method_matrix", "literature_evidence_matrix")
    if requires_literature:
        required["evidence_matrix"] = evidence_matrix

    for name, raw in required.items():
        if not raw:
            blockers.append(f"required path is not declared: {name}")
            continue
        resolved = resolve_ref(raw, repo_root)
        exists = resolved.exists()
        allowed = path_allowed(resolved, roots)
        checked_paths.append(
            {
                "name": name,
                "path": display_path(resolved, repo_root),
                "exists": exists,
                "allowed": allowed,
            }
        )
        if not exists:
            blockers.append(f"required path does not exist: {name}={raw}")
        if not allowed:
            blockers.append(f"required path is outside reviewer read scope: {name}={raw}")

    for ref in extract_path_refs(packet):
        raw = ref["path"]
        resolved = resolve_ref(raw, repo_root)
        if not path_allowed(resolved, roots):
            blockers.append(f"declared read path is outside reviewer read scope: {raw}")
            checked_paths.append(
                {
                    "name": ref["key"],
                    "path": display_path(resolved, repo_root),
                    "exists": resolved.exists(),
                    "allowed": False,
                }
            )

    status = "passed"
    if blockers:
        status = "failed"
    elif warnings:
        status = "warning"
    return {
        "status": status,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "checked_paths": checked_paths,
        "required_paths": required,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reviewer packet/path preflight.")
    parser.add_argument("--packet", default="role/reviewer/workspace/inbox/review_packet.json")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--workspace", default="role/reviewer/workspace")
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    output = run_preflight(
        packet_path=Path(args.packet).resolve(),
        repo_root=repo_root,
        reviewer_workspace=(repo_root / args.workspace).resolve(),
    )
    if args.output:
        write_json(Path(args.output), output)
    else:
        print(json.dumps(output, indent=2, sort_keys=True))
    return 1 if output["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
