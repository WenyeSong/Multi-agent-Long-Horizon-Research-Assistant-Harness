#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from review_utils import load_json, resolve_ref, write_json


def _tail(value: str, limit: int = 2000) -> str:
    return value[-limit:] if len(value) > limit else value


def extract_commands(packet: dict[str, Any]) -> list[dict[str, Any]]:
    raw = packet.get("verify_commands", packet.get("verify_command"))
    if raw is None and isinstance(packet.get("executor"), dict):
        raw = packet["executor"].get("verify_commands", packet["executor"].get("verify_command"))
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    commands: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, str):
            commands.append({"command": item})
        elif isinstance(item, dict) and item.get("command"):
            commands.append(dict(item))
    return commands


def run_optional_verify(packet_path: Path, repo_root: Path, default_timeout: int = 60) -> dict[str, Any]:
    packet = load_json(packet_path) if packet_path.exists() else {}
    commands = extract_commands(packet)
    if not commands:
        return {
            "ran_commands": [],
            "status": "not_run",
            "notes": ["No verify command was provided; this is not a failure by itself."],
        }

    results: list[dict[str, Any]] = []
    for command in commands:
        cwd_ref = command.get("cwd") or "."
        cwd = resolve_ref(str(cwd_ref), repo_root)
        timeout = int(command.get("timeout_seconds") or default_timeout)
        if not cwd.exists() or not cwd.is_dir():
            results.append(
                {
                    "command": str(command["command"]),
                    "cwd": str(cwd),
                    "status": "failed",
                    "exit_code": None,
                    "stdout_tail": "",
                    "stderr_tail": "verify cwd does not exist",
                }
            )
            continue
        try:
            completed = subprocess.run(
                str(command["command"]),
                cwd=cwd,
                shell=True,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            status = "passed" if completed.returncode == 0 else "failed"
            results.append(
                {
                    "command": str(command["command"]),
                    "cwd": str(cwd),
                    "status": status,
                    "exit_code": completed.returncode,
                    "stdout_tail": _tail(completed.stdout),
                    "stderr_tail": _tail(completed.stderr),
                }
            )
        except subprocess.TimeoutExpired as exc:
            results.append(
                {
                    "command": str(command["command"]),
                    "cwd": str(cwd),
                    "status": "timeout",
                    "exit_code": None,
                    "stdout_tail": _tail(exc.stdout or ""),
                    "stderr_tail": _tail(exc.stderr or ""),
                }
            )

    aggregate = "passed" if all(item["status"] == "passed" for item in results) else "failed"
    return {
        "ran_commands": results,
        "status": aggregate,
        "notes": ["Executor-provided verify command was run."],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run optional executor verification commands.")
    parser.add_argument("--packet", default="role/reviewer/workspace/inbox/review_packet.json")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output = run_optional_verify(
        packet_path=Path(args.packet).resolve(),
        repo_root=Path(args.repo_root).resolve(),
        default_timeout=args.timeout_seconds,
    )
    if args.output:
        write_json(Path(args.output), output)
    else:
        print(json.dumps(output, indent=2, sort_keys=True))
    return 1 if output["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
