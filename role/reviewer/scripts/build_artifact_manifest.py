#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from review_utils import (
    display_path,
    ensure_workspace,
    extract_path_refs,
    iter_artifact_files,
    load_json,
    resolve_ref,
    sha256_file,
    utc_now,
    write_json,
)


def build_manifest(packet_path: Path, repo_root: Path, reviewer_workspace: Path) -> dict[str, Any]:
    ensure_workspace(reviewer_workspace)
    packet = load_json(packet_path) if packet_path.exists() else {}
    refs = [resolve_ref(ref["path"], repo_root) for ref in extract_path_refs(packet)]
    if not refs:
        refs = [
            repo_root / "role" / "literature_reviewer" / "workspace" / "outbox",
            repo_root / "role" / "executor" / "workspace" / "outbox",
            repo_root / "role" / "executor" / "workspace" / "artifacts",
        ]
    artifacts = []
    for path in iter_artifact_files(refs):
        try:
            stat = path.stat()
        except OSError:
            continue
        artifacts.append(
            {
                "path": display_path(path, repo_root),
                "sha256": sha256_file(path),
                "size_bytes": stat.st_size,
                "modified_utc": utc_now(),
                "kind": path.suffix.lower().lstrip(".") or "file",
            }
        )
    return {
        "generated_at": utc_now(),
        "task_id": packet.get("task_id") or packet.get("trace_id") or "task_unknown",
        "state_version": packet.get("state_version") or "unknown",
        "artifacts": artifacts,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build reviewer artifact manifest with hashes.")
    parser.add_argument("--packet", default="role/reviewer/workspace/inbox/review_packet.json")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--workspace", default="role/reviewer/workspace")
    parser.add_argument("--output", default="role/reviewer/workspace/scratch/artifact_manifest.json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    manifest = build_manifest(
        packet_path=Path(args.packet).resolve(),
        repo_root=repo_root,
        reviewer_workspace=(repo_root / args.workspace).resolve(),
    )
    write_json(repo_root / args.output, manifest)
    print(f"wrote {args.output} with {len(manifest['artifacts'])} artifact(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
