#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from review_utils import display_path, ensure_workspace, is_relative_to, write_json


def git_changed_paths(repo_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return []
    paths = []
    for line in result.stdout.splitlines():
        if len(line) > 3:
            paths.append(line[3:].strip())
    return paths


def run_scope_audit(
    repo_root: Path,
    reviewer_workspace: Path,
    include_git_status: bool = False,
) -> dict[str, Any]:
    ensure_workspace(reviewer_workspace)
    notes: list[str] = []
    violations: list[str] = []
    workspace = reviewer_workspace.resolve(strict=False)
    for child in reviewer_workspace.rglob("*"):
        if child.is_file() and not is_relative_to(child, workspace):
            violations.append(f"reviewer output escaped workspace: {child}")

    if include_git_status:
        for raw in git_changed_paths(repo_root):
            path = (repo_root / raw).resolve(strict=False)
            if not is_relative_to(path, workspace):
                notes.append(f"git worktree has non-reviewer change: {raw}")

    status = "clean"
    if violations:
        status = "violation"
    elif notes:
        status = "warning"
    if not notes and not violations:
        notes.append("Reviewer writes are confined to reviewer workspace.")
    return {
        "status": status,
        "notes": notes + violations,
        "reviewer_workspace": display_path(reviewer_workspace, repo_root),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit reviewer role write scope.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--workspace", default="role/reviewer/workspace")
    parser.add_argument("--include-git-status", action="store_true")
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    output = run_scope_audit(
        repo_root=repo_root,
        reviewer_workspace=(repo_root / args.workspace).resolve(),
        include_git_status=args.include_git_status,
    )
    if args.output:
        write_json(Path(args.output), output)
    else:
        print(json.dumps(output, indent=2, sort_keys=True))
    return 1 if output["status"] == "violation" else 0


if __name__ == "__main__":
    raise SystemExit(main())
