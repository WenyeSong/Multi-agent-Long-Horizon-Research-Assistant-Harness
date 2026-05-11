#!/usr/bin/env python3
"""Manage named OpenClaw sessions for this repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def validate_session_name(name: str) -> None:
    if not SESSION_RE.match(name):
        raise SystemExit(
            "Invalid session name. Use letters, digits, underscore, dot, or "
            "hyphen, and do not include path separators."
        )


def openclaw_state_dir() -> Path:
    state_dir = os.environ.get("OPENCLAW_STATE_DIR")
    if state_dir:
        return Path(state_dir).expanduser()
    return Path.home() / ".openclaw"


def sessions_dir(agent: str, state_dir: Path | None = None) -> Path:
    root = state_dir or openclaw_state_dir()
    return root / "agents" / agent / "sessions"


def project_dir(session_name: str) -> Path:
    return repo_root() / "projects" / session_name


def session_file_candidates(directory: Path, session_id: str) -> list[Path]:
    suffixes = [
        ".jsonl",
        ".trajectory.jsonl",
        ".trajectory-path.json",
    ]
    candidates = [directory / f"{session_id}{suffix}" for suffix in suffixes]
    if directory.exists():
        candidates.extend(directory.glob(f"{session_id}.jsonl.bak-*"))
    return sorted(set(candidates))


def load_sessions_index(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Cannot parse {path}: {exc}") from exc


def write_sessions_index(path: Path, data: dict, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def matching_session_ids(index: dict, agent: str, name: str) -> tuple[set[str], list[str]]:
    keys = {
        f"agent:{agent}:{name}",
        f"agent:{agent}:explicit:{name}",
    }
    session_ids: set[str] = {name}
    matching_keys: list[str] = []

    for key, value in index.items():
        session_id = value.get("sessionId") if isinstance(value, dict) else None
        session_key = value.get("sessionKey") if isinstance(value, dict) else None
        if key in keys or session_key in keys or session_id == name:
            matching_keys.append(key)
            if session_id:
                session_ids.add(session_id)

    return session_ids, matching_keys


def start_session(args: argparse.Namespace) -> int:
    validate_session_name(args.name)

    if args.one_shot:
        if not args.message:
            raise SystemExit("--one-shot requires --message")
        command = [
            args.openclaw,
            "agent",
            "--local",
            "--agent",
            args.agent,
            "--session-id",
            args.name,
            "--thinking",
            args.thinking,
            "--message",
            args.message,
        ]
    else:
        command = [
            args.openclaw,
            "chat",
            "--local",
            "--session",
            args.name,
            "--thinking",
            args.thinking,
        ]
        if args.message:
            command.extend(["--message", args.message])

    if args.dry_run:
        print(" ".join(command))
        return 0

    project_dir(args.name).mkdir(parents=True, exist_ok=True)
    return subprocess.run(command, cwd=repo_root(), check=False).returncode


def delete_session(args: argparse.Namespace) -> int:
    validate_session_name(args.name)
    directory = sessions_dir(args.agent, Path(args.state_dir).expanduser() if args.state_dir else None)
    index_path = directory / "sessions.json"
    index = load_sessions_index(index_path)
    session_ids, keys = matching_session_ids(index, args.agent, args.name)

    files: list[Path] = []
    for session_id in session_ids:
        files.extend(session_file_candidates(directory, session_id))

    files = [path for path in sorted(set(files)) if path.exists()]
    target_project = project_dir(args.name)

    print(f"Session name: {args.name}")
    print(f"OpenClaw sessions dir: {directory}")
    if keys:
        print("Registry entries:")
        for key in keys:
            print(f"  {key}")
    if files:
        print("Session files:")
        for path in files:
            print(f"  {path}")
    if args.project and target_project.exists():
        print(f"Project workspace: {target_project}")

    if args.dry_run:
        print("Dry run only; nothing deleted.")
        return 0

    for key in keys:
        index.pop(key, None)
    if keys or index_path.exists():
        write_sessions_index(index_path, index, dry_run=False)

    for path in files:
        path.unlink()

    if args.project and target_project.exists():
        shutil.rmtree(target_project)

    print("Done.")
    return 0


def list_sessions(args: argparse.Namespace) -> int:
    directory = sessions_dir(args.agent, Path(args.state_dir).expanduser() if args.state_dir else None)
    index = load_sessions_index(directory / "sessions.json")
    if not index:
        print(f"No session registry entries found in {directory}.")
        return 0

    for key, value in sorted(index.items()):
        session_id = value.get("sessionId", "?") if isinstance(value, dict) else "?"
        print(f"{key} -> {session_id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", default="main", help="OpenClaw agent id (default: main)")
    parser.add_argument(
        "--state-dir",
        help="OpenClaw state dir (default: OPENCLAW_STATE_DIR or ~/.openclaw)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start or continue a named OpenClaw session")
    start.add_argument("name", help="Session name")
    start.add_argument("--message", help="Optional initial message")
    start.add_argument("--thinking", default="low", help="OpenClaw thinking level")
    start.add_argument("--openclaw", default="openclaw", help="OpenClaw executable")
    start.add_argument("--one-shot", action="store_true", help="Use `openclaw agent` instead of chat")
    start.add_argument("--dry-run", action="store_true", help="Print the command without running it")
    start.set_defaults(func=start_session)

    delete = subparsers.add_parser("delete", help="Delete a named OpenClaw session")
    delete.add_argument("name", help="Session name")
    delete.add_argument(
        "--project",
        action="store_true",
        help="Also delete the matching projects/<session_name>/ workspace",
    )
    delete.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    delete.set_defaults(func=delete_session)

    listing = subparsers.add_parser("list", help="List known OpenClaw sessions")
    listing.set_defaults(func=list_sessions)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
