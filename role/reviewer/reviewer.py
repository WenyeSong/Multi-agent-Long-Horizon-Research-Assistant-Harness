#!/usr/bin/env python3
"""Executable runner for the OpenClaw reviewer role."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROLE_DIR.parents[1]
SCRIPTS_DIR = ROLE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_artifact_manifest import build_manifest
from issue_pass import issue_pass_token
from review_preflight import run_preflight
from review_record import append_review_record
from review_utils import (
    display_path,
    ensure_workspace,
    load_env_files,
    load_json,
    normalize_issue,
    normalize_report,
    read_text_limited,
    render_review_markdown,
    utc_now,
    write_json,
)
from run_optional_verify import run_optional_verify
from scope_audit import run_scope_audit


ROLE = "reviewer"
PURPOSE = "LLM-led review of correctness, evidence, scope, and compliance."
DEFAULT_MODEL = "gpt-5.4-nano"


def read_role_text() -> str:
    parts = [(ROLE_DIR / "system_prompt.md").read_text(encoding="utf-8")]
    for path in sorted((ROLE_DIR / "references").glob("*.md")):
        parts.append(f"\n\n# Reference: {path.name}\n" + path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[...truncated...]"


def artifact_excerpts(manifest: dict[str, Any], repo_root: Path, max_chars: int) -> list[dict[str, str]]:
    excerpts: list[dict[str, str]] = []
    remaining = max_chars
    for artifact in manifest.get("artifacts", []):
        path = repo_root / artifact["path"]
        text = read_text_limited(path, max_chars=min(4000, remaining))
        if text:
            excerpts.append({"path": artifact["path"], "text": text})
            remaining -= len(text)
        else:
            excerpts.append({"path": artifact["path"], "text": f"[binary or non-text artifact: {artifact.get('kind', 'file')}]"})
        if remaining <= 0:
            break
    return excerpts


def build_llm_context(
    *,
    packet: dict[str, Any],
    preflight: dict[str, Any],
    manifest: dict[str, Any],
    verification: dict[str, Any],
    scope_audit: dict[str, Any],
    repo_root: Path,
    max_chars: int,
) -> str:
    context = {
        "review_packet": packet,
        "script_evidence": {
            "preflight": preflight,
            "artifact_manifest": manifest,
            "verification": verification,
            "scope_audit": scope_audit,
        },
        "artifact_excerpts": artifact_excerpts(manifest, repo_root, max_chars=max_chars),
        "json_output_instruction": (
            "Return exactly one JSON object matching required_json_shape. "
            "Do not include Markdown, prose, analysis, or code fences."
        ),
        "required_json_shape": {
            "task_id": "string",
            "state_version": "string",
            "decision": "PASS | REVISE | REPLAN | BLOCK | INCONCLUSIVE",
            "confidence": "high | medium | low",
            "route_suggestion": "planner | literature_reviewer | executor | main | pdf_generator | none",
            "report_output_format": "html when routing to the legacy pdf_generator role",
            "summary": "short reviewer judgment",
            "blocking_issues": [],
            "major_issues": [],
            "advisory_notes": [],
            "requirement_map_summary": {
                "explicit_required_checked": [],
                "implied_required_checked": [],
                "optional_not_blocking": [],
            },
        },
    }
    return truncate(json.dumps(context, indent=2, sort_keys=True), max_chars)


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        preview = text.strip().replace("\n", " ")[:500]
        raise ValueError(f"LLM response was not valid JSON. Preview: {preview}") from exc
    if not isinstance(payload, dict):
        raise ValueError("LLM response JSON root is not an object")
    return payload


def response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "\n".join(chunks)


def call_openai_review(system_text: str, user_text: str, model: str, max_tokens: int) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not available")
    base_url = (os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    body = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_text}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_text}],
            },
        ],
        "max_output_tokens": max_tokens,
    }
    request = urllib.request.Request(
        f"{base_url}/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as handle:
            payload = json.loads(handle.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI request failed: HTTP {exc.code} {detail}") from exc
    text = response_text(payload)
    if not text:
        raise RuntimeError("OpenAI response did not contain output_text")
    return extract_json_object(text)


def fallback_report(
    packet: dict[str, Any],
    *,
    reason: str,
    preflight: dict[str, Any],
    verification: dict[str, Any],
    scope_audit: dict[str, Any],
) -> dict[str, Any]:
    if scope_audit.get("status") == "violation":
        decision = "BLOCK"
        route = "main"
        owner = "main"
    elif preflight.get("status") == "failed":
        decision = "INCONCLUSIVE"
        route = "planner"
        owner = "planner"
    elif verification.get("status") == "failed":
        decision = "REVISE"
        route = "executor"
        owner = "executor"
    else:
        decision = "INCONCLUSIVE"
        route = "planner"
        owner = "planner"
    report = {
        "task_id": packet.get("task_id") or packet.get("trace_id") or "task_unknown",
        "trace_id": packet.get("trace_id"),
        "state_version": packet.get("state_version") or "unknown",
        "decision": decision,
        "confidence": "low",
        "route_suggestion": route,
        "summary": reason,
        "blocking_issues": [
            normalize_issue(
                {
                    "owner": owner,
                    "evidence": reason,
                    "reason": reason,
                    "recommended_fix": "Provide a complete review packet or run reviewer with LLM access.",
                },
                "blocking",
            )
        ],
        "major_issues": [],
        "advisory_notes": [],
        "requirement_map_summary": {
            "explicit_required_checked": [],
            "implied_required_checked": [],
            "optional_not_blocking": [],
        },
    }
    return report


def apply_script_guardrails(
    report: dict[str, Any],
    *,
    preflight: dict[str, Any],
    manifest: dict[str, Any],
    verification: dict[str, Any],
    scope_audit: dict[str, Any],
) -> dict[str, Any]:
    report = dict(report)
    report["verification"] = verification
    report["scope_audit"] = {"status": scope_audit["status"], "notes": scope_audit["notes"]}
    report["checked_artifacts"] = [
        {
            "path": artifact["path"],
            "sha256": artifact["sha256"],
            "kind": artifact.get("kind", "file"),
        }
        for artifact in manifest.get("artifacts", [])
    ]

    if preflight.get("status") == "failed":
        report["decision"] = "INCONCLUSIVE"
        report["confidence"] = "low"
        report["route_suggestion"] = "planner"
        for blocker in preflight.get("blockers", []):
            report.setdefault("blocking_issues", []).append(
                normalize_issue(
                    {
                        "owner": "planner",
                        "evidence": blocker,
                        "reason": "Reviewer packet preflight failed.",
                        "recommended_fix": "Planner should provide the missing or in-scope review material.",
                    },
                    "blocking",
                )
            )

    if scope_audit.get("status") == "violation":
        report["decision"] = "BLOCK"
        report["confidence"] = "high"
        report["route_suggestion"] = "main"
        report.setdefault("blocking_issues", []).append(
            normalize_issue(
                {
                    "owner": "main",
                    "evidence": "; ".join(scope_audit.get("notes", [])),
                    "reason": "Reviewer scope audit found a role-boundary violation.",
                    "recommended_fix": "Stop and inspect role workspace permissions before continuing.",
                    "confidence": "high",
                },
                "blocking",
            )
        )

    if verification.get("status") == "failed" and report.get("decision") == "PASS":
        report["decision"] = "REVISE"
        report["confidence"] = "high"
        report["route_suggestion"] = "executor"
        report.setdefault("blocking_issues", []).append(
            normalize_issue(
                {
                    "owner": "executor",
                    "evidence": "Executor-provided verification command failed.",
                    "reason": "A provided verification command is direct evidence of a code or result failure.",
                    "recommended_fix": "Fix the executor artifact or update the stated result and rerun verification.",
                    "confidence": "high",
                },
                "blocking",
            )
        )

    if report.get("decision") == "PASS" and not manifest.get("artifacts"):
        report["decision"] = "INCONCLUSIVE"
        report["confidence"] = "low"
        report["route_suggestion"] = "planner"
        report.setdefault("blocking_issues", []).append(
            normalize_issue(
                {
                    "owner": "planner",
                    "evidence": "artifact_manifest.json contains no reviewed artifacts",
                    "reason": "PASS requires reviewed artifact hashes for the pass token.",
                    "recommended_fix": "Provide concrete executor/literature artifacts in the review packet.",
                },
                "blocking",
            )
        )

    if report.get("decision") == "PASS":
        report["blocking_issues"] = []
        report["route_suggestion"] = "none"
        report["pass_token_issued"] = True
    else:
        report["pass_token_issued"] = False
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=PURPOSE)
    parser.add_argument("--request", help="Compatibility alias for --packet")
    parser.add_argument("--packet", help="Path to review packet JSON")
    parser.add_argument("--output", help="Optional extra path to write review_report.json")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--workspace", default="role/reviewer/workspace")
    parser.add_argument("--llm-mode", choices=["auto", "require", "off"], default="auto")
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-context-chars", type=int, default=30000)
    parser.add_argument("--max-output-tokens", type=int, default=2200)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    workspace = (repo_root / args.workspace).resolve()
    ensure_workspace(workspace)
    packet_path = Path(args.packet or args.request or workspace / "inbox" / "review_packet.json").resolve()

    load_env_files([repo_root / ".env", repo_root.parent / ".env"])

    packet = load_json(packet_path) if packet_path.exists() else {}
    preflight = run_preflight(packet_path, repo_root, workspace)
    manifest = build_manifest(packet_path, repo_root, workspace)
    manifest_path = workspace / "scratch" / "artifact_manifest.json"
    write_json(manifest_path, manifest)
    verification = run_optional_verify(packet_path, repo_root)
    write_json(workspace / "scratch" / "optional_verify.json", verification)
    scope = run_scope_audit(repo_root, workspace)
    write_json(workspace / "scratch" / "scope_audit.json", scope)

    llm_error: str | None = None
    llm_report: dict[str, Any] | None = None
    model = args.model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL
    if args.llm_mode != "off" and packet_path.exists():
        try:
            llm_report = call_openai_review(
                read_role_text(),
                build_llm_context(
                    packet=packet,
                    preflight=preflight,
                    manifest=manifest,
                    verification=verification,
                    scope_audit=scope,
                    repo_root=repo_root,
                    max_chars=args.max_context_chars,
                ),
                model=model,
                max_tokens=args.max_output_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced in report
            llm_error = str(exc)
            if args.llm_mode == "require":
                raise

    if llm_report is None:
        reason = "LLM review was not run."
        if llm_error:
            reason = f"LLM review failed: {llm_error}"
        elif not packet_path.exists():
            reason = f"Review packet not found: {display_path(packet_path, repo_root)}"
        report = fallback_report(
            packet,
            reason=reason,
            preflight=preflight,
            verification=verification,
            scope_audit=scope,
        )
    else:
        report = llm_report

    report = normalize_report(report, packet)
    report = apply_script_guardrails(
        report,
        preflight=preflight,
        manifest=manifest,
        verification=verification,
        scope_audit=scope,
    )
    report["generated_at"] = utc_now()
    report["reviewer_model"] = model if llm_report is not None else "script_fallback"

    review_id = append_review_record(report, workspace / "logs" / "review.tsv")
    report["review_id"] = review_id

    report_path = workspace / "outbox" / "review_report.json"
    markdown_path = workspace / "outbox" / "review_report.md"
    write_json(report_path, report)
    markdown_path.write_text(render_review_markdown(report), encoding="utf-8")

    if report["decision"] == "PASS":
        issue_pass_token(report, manifest, workspace / "outbox" / "pass_token.json")

    if args.output:
        write_json(Path(args.output), report)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
