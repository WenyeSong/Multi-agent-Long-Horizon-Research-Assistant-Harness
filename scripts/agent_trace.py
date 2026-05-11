#!/usr/bin/env python3
"""Append a planner worker-invocation trace and print a CLI-visible line."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record an OpenClaw worker role trace.")
    parser.add_argument("--trace-id", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--input-context", required=True)
    parser.add_argument("--output-summary", required=True)
    parser.add_argument("--input-artifact-ref", action="append", default=[])
    parser.add_argument("--output-artifact-ref", action="append", default=[])
    return parser


def read_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def write_summary(path: Path, entries: list[dict[str, Any]]) -> None:
    lines = ["# Agent Trace", ""]
    for entry in entries:
        refs = entry.get("output_artifact_refs") or []
        ref_text = ", ".join(refs) if refs else "no output refs"
        lines.append(
            f"- `{entry['agent']}` -> {entry['reason']} -> "
            f"{entry['status']}: {entry['output_summary']} -> {ref_text}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    provenance_dir = Path("projects") / args.trace_id / "provenance"
    provenance_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = provenance_dir / "agent_trace.jsonl"
    summary_path = provenance_dir / "agent_trace_summary.md"

    timestamp = utc_now()
    entry = {
        "trace_event_id": f"{timestamp}:{args.agent}",
        "agent": args.agent,
        "phase": args.phase,
        "action": args.action,
        "status": args.status,
        "reason": args.reason,
        "input_context_summary": args.input_context,
        "input_artifact_refs": args.input_artifact_ref,
        "output_summary": args.output_summary,
        "output_artifact_refs": args.output_artifact_ref,
        "completed_at": timestamp,
    }
    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")

    entries = read_entries(jsonl_path)
    write_summary(summary_path, entries)

    refs = ", ".join(args.output_artifact_ref) if args.output_artifact_ref else "no output refs"
    print(
        f"[Agent Trace] {args.agent} -> {args.reason} -> "
        f"{args.status}: {args.output_summary} -> {refs}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
