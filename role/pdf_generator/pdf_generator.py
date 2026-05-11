#!/usr/bin/env python3
"""Problem-agnostic executable scaffold for the pdf_generator role."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROLE = "pdf_generator"
PURPOSE = "Typeset approved artifacts only; do not add facts or conclusions."
SCHEMA_REFS = ["schemas/report_spec.schema.json"]


def load_request(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def trace_id_from_request(request: dict[str, Any]) -> str:
    return str(request.get("trace_id") or "smoke_planarity")


def pdf_bytes(title: str) -> bytes:
    text = title.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 14 Tf 72 720 Td ({text}) Tj ET\n"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream.encode('ascii'))} >>\nstream\n{stream}endstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{index} 0 obj\n{obj}\nendobj\n".encode("ascii"))
    xref_offset = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    body.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode("ascii")
    )
    return bytes(body)


def build_response(request: dict[str, Any]) -> dict[str, Any]:
    if "trace_id" not in request:
        return {
            "role": ROLE,
            "status": "ready",
            "purpose": PURPOSE,
            "schema_refs": SCHEMA_REFS,
            "next_step": "provide an approved report_spec JSON to run PDF fallback"
        }

    trace_id = trace_id_from_request(request)
    report_dir = Path("projects") / trace_id / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    if request.get("approved_by_reviewer") is not True:
        return {
            "role": ROLE,
            "status": "blocked",
            "trace_id": trace_id,
            "reason": "pdf_generator requires approved_by_reviewer=true",
            "artifact_refs": [],
        }

    approved_content = report_dir / "approved_content.md"
    final_pdf = report_dir / "final.pdf"
    sections = request.get("sections") if isinstance(request.get("sections"), list) else []
    approved_content.write_text(
        "# Smoke-test research memo\n\n"
        "This fallback memo was generated only to test the OpenClaw role chain.\n\n"
        "Sections requested:\n"
        + "".join(f"- {section}\n" for section in sections)
        + "\nNo new facts or conclusions were added by pdf_generator.\n",
        encoding="utf-8",
    )
    final_pdf.write_bytes(pdf_bytes("OpenClaw smoke-test research memo"))

    return {
        "role": ROLE,
        "status": "ok",
        "purpose": PURPOSE,
        "schema_refs": SCHEMA_REFS,
        "trace_id": trace_id,
        "approved_by_reviewer": request.get("approved_by_reviewer"),
        "pdf_path": final_pdf.as_posix(),
        "artifact_refs": [approved_content.as_posix(), final_pdf.as_posix()],
        "constraints_observed": {
            "no_new_facts": True,
            "no_new_conclusions": True,
            "only_approved_artifacts": True,
        },
        "notes": [
            "Fallback generated a minimal PDF shell only; replace with real typesetting later.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=PURPOSE)
    parser.add_argument("--request", help="Path to report spec JSON")
    parser.add_argument("--output", help="Path to write response JSON")
    args = parser.parse_args()

    response = build_response(load_request(args.request))
    payload = json.dumps(response, indent=2, sort_keys=True) + "\n"

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
