#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TEXT_EXTENSIONS = {
    ".csv",
    ".json",
    ".log",
    ".md",
    ".py",
    ".txt",
    ".tsv",
    ".yaml",
    ".yml",
}

ARTIFACT_EXTENSIONS = TEXT_EXTENSIONS | {
    ".ipynb",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
}

PATH_KEY_HINTS = (
    "artifact",
    "csv",
    "dir",
    "evidence",
    "file",
    "figure",
    "log",
    "manifest",
    "matrix",
    "output",
    "path",
    "pdf",
    "result",
    "state",
)


class ReviewError(RuntimeError):
    """Raised for script-level reviewer utility errors."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_review_id() -> str:
    return "review_" + uuid.uuid4().hex[:12]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ReviewError(f"JSON root must be an object: {path}")
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_workspace(workspace: Path) -> None:
    for name in ("inbox", "scratch", "outbox", "logs"):
        (workspace / name).mkdir(parents=True, exist_ok=True)


def is_url(value: str) -> bool:
    return "://" in value


def looks_like_path(value: str) -> bool:
    stripped = value.strip()
    if not stripped or is_url(stripped):
        return False
    if re.search(r"\s", stripped) and not (
        stripped.startswith(("./", "../", "projects/", "/projects/", "role/"))
        or re.match(r"^[A-Za-z]:[\\/]", stripped)
    ):
        return False
    return bool(
        re.search(r"[\\/]", stripped)
        or stripped.startswith(("./", "../", "projects/", "/projects/"))
        or re.match(r"^[A-Za-z]:[\\/]", stripped)
    )


def resolve_ref(path_value: str, repo_root: Path) -> Path:
    value = path_value.strip()
    normalized = value.replace("\\", "/")
    if normalized.startswith("/projects/"):
        return (repo_root / normalized.lstrip("/")).resolve(strict=False)
    if normalized.startswith("./projects/"):
        return (repo_root / normalized[2:]).resolve(strict=False)
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (repo_root / candidate).resolve(strict=False)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve(strict=False)).as_posix()
    except ValueError:
        return str(path)


def allowed_read_roots(repo_root: Path, reviewer_workspace: Path) -> list[Path]:
    roots = [
        repo_root / "projects",
        repo_root / "role" / "research-planner" / "workspace" / "outbox",
        repo_root / "role" / "research_planner" / "workspace" / "outbox",
        repo_root / "role" / "literature_reviewer" / "workspace" / "outbox",
        repo_root / "role" / "executor" / "workspace" / "outbox",
        repo_root / "role" / "executor" / "workspace" / "artifacts",
        repo_root / "role" / "executor" / "workspace" / "logs",
        repo_root / "role" / "pdf_generator" / "workspace" / "outbox",
        reviewer_workspace / "inbox",
    ]
    return [root.resolve(strict=False) for root in roots]


def path_allowed(path: Path, roots: Iterable[Path]) -> bool:
    return any(is_relative_to(path, root) for root in roots)


def extract_path_refs(payload: Any, *, parent_key: str = "") -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            refs.extend(extract_path_refs(value, parent_key=key_text))
    elif isinstance(payload, list):
        for value in payload:
            refs.extend(extract_path_refs(value, parent_key=parent_key))
    elif isinstance(payload, str):
        key_lower = parent_key.lower()
        stripped = payload.strip().replace("\\", "/")
        has_path_key = any(hint in key_lower for hint in PATH_KEY_HINTS)
        has_known_prefix = stripped.startswith(("./", "../", "projects/", "/projects/", "role/"))
        has_absolute_prefix = bool(re.match(r"^[A-Za-z]:/", stripped))
        if looks_like_path(payload) and (has_path_key or has_known_prefix or has_absolute_prefix):
            refs.append({"key": parent_key, "path": payload})
    return refs


def get_path_from_packet(packet: dict[str, Any], *names: str) -> str | None:
    paths = packet.get("paths")
    if isinstance(paths, dict):
        for name in names:
            value = paths.get(name)
            if isinstance(value, str) and value.strip():
                return value
    for name in names:
        value = packet.get(name)
        if isinstance(value, str) and value.strip():
            return value
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_artifact_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and child.suffix.lower() in ARTIFACT_EXTENSIONS:
                    files.append(child)
        elif path.is_file() and path.suffix.lower() in ARTIFACT_EXTENSIONS:
            files.append(path)
    return sorted(set(files), key=lambda item: str(item).lower())


def read_text_limited(path: Path, max_chars: int = 6000) -> str:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[...truncated...]"


def load_env_files(paths: Iterable[Path]) -> None:
    for path in paths:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def normalize_issue(issue: Any, severity: str) -> dict[str, Any]:
    data = issue if isinstance(issue, dict) else {}
    owner = data.get("owner") if data.get("owner") in {
        "planner",
        "literature_reviewer",
        "executor",
        "main",
        "pdf_generator",
    } else "planner"
    return {
        "severity": data.get("severity") or severity,
        "owner": owner,
        "evidence": data.get("evidence") or "No concrete evidence supplied.",
        "reason": data.get("reason") or data.get("message") or "Reviewer identified an issue.",
        "recommended_fix": data.get("recommended_fix") or "Planner should request a targeted repair.",
        **({"confidence": data["confidence"]} if data.get("confidence") in {"high", "medium", "low"} else {}),
    }


def normalize_report(report: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    def as_list(value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    decision = str(report.get("decision") or "INCONCLUSIVE").upper()
    if decision not in {"PASS", "REVISE", "REPLAN", "BLOCK", "INCONCLUSIVE"}:
        decision = "INCONCLUSIVE"
    route = str(report.get("route_suggestion") or "none")
    if route not in {"planner", "literature_reviewer", "executor", "main", "pdf_generator", "none"}:
        route = "planner" if decision in {"REPLAN", "INCONCLUSIVE"} else "none"
    if decision == "PASS":
        route = "none"
    if decision == "REPLAN":
        route = "planner"
    if decision == "BLOCK" and route not in {"main", "planner"}:
        route = "main"

    task_id = str(report.get("task_id") or packet.get("task_id") or packet.get("trace_id") or "task_unknown")
    state_version = str(report.get("state_version") or packet.get("state_version") or "unknown")
    normalized = {
        "task_id": task_id,
        "state_version": state_version,
        "decision": decision,
        "confidence": report.get("confidence") if report.get("confidence") in {"high", "medium", "low"} else "low",
        "route_suggestion": route,
        "summary": str(report.get("summary") or "Reviewer could not form a complete judgment."),
        "blocking_issues": [normalize_issue(item, "blocking") for item in as_list(report.get("blocking_issues", []))],
        "major_issues": [normalize_issue(item, "major") for item in as_list(report.get("major_issues", []))],
        "advisory_notes": [normalize_issue(item, "advisory") for item in as_list(report.get("advisory_notes", []))],
        "checked_artifacts": as_list(report.get("checked_artifacts", [])),
        "requirement_map_summary": {
            "explicit_required_checked": as_list(
                (report.get("requirement_map_summary") or {}).get("explicit_required_checked", [])
            ),
            "implied_required_checked": as_list(
                (report.get("requirement_map_summary") or {}).get("implied_required_checked", [])
            ),
            "optional_not_blocking": as_list(
                (report.get("requirement_map_summary") or {}).get("optional_not_blocking", [])
            ),
        },
        "verification": report.get("verification") or {
            "ran_commands": [],
            "status": "not_run",
            "notes": ["No verification was run."],
        },
        "scope_audit": report.get("scope_audit") or {
            "status": "warning",
            "notes": ["Scope audit was not supplied."],
        },
        "pass_token_issued": bool(report.get("pass_token_issued", False)),
    }
    if packet.get("trace_id") or report.get("trace_id"):
        normalized["trace_id"] = str(report.get("trace_id") or packet.get("trace_id"))
    if report.get("review_id"):
        normalized["review_id"] = str(report["review_id"])
    return normalized


def render_review_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Review Report",
        "",
        f"Decision: {report['decision']}",
        f"Route suggestion: {report['route_suggestion']}",
        f"Confidence: {report['confidence']}",
        "",
        "## Summary",
        report["summary"],
        "",
    ]

    def add_section(title: str, issues: list[dict[str, Any]]) -> None:
        lines.append(f"## {title}")
        if not issues:
            lines.append("None.")
            lines.append("")
            return
        for index, issue in enumerate(issues, start=1):
            lines.append(f"{index}. [{issue['owner']}] {issue['reason']}")
            lines.append(f"Evidence: `{issue['evidence']}`")
            lines.append(f"Required fix: {issue['recommended_fix']}")
            lines.append("")

    add_section("Blocking Issues", report["blocking_issues"])
    add_section("Major Issues", report["major_issues"])
    add_section("Advisory Notes", report["advisory_notes"])
    lines.append("## Suggested Recovery")
    if report["decision"] == "PASS":
        lines.append("Planner may proceed to pdf_generator using the pass token.")
    elif report["decision"] == "REVISE":
        lines.append(f"Planner should route this back to {report['route_suggestion']}.")
    elif report["decision"] == "REPLAN":
        lines.append("Planner should revise decomposition, success criteria, or experiment design.")
    elif report["decision"] == "BLOCK":
        lines.append("Planner should escalate to main or human review.")
    else:
        lines.append("Planner should provide the missing packet material and rerun review.")
    lines.append("")
    return "\n".join(lines)
