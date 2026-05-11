#!/usr/bin/env python3
"""pdf_generator — typeset approved artifacts into a PDF report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)

ROLE = "pdf_generator"
PURPOSE = "Typeset approved artifacts only; do not add facts or conclusions."
SCHEMA_REFS = ["schemas/report_spec.schema.json"]

# Sections the PDF generator knows how to render, in display order
SECTION_RENDERERS: list[str] = [
    "Problem overview",
    "Literature review",
    "Methodological synthesis",
    "Computational experiments",
    "Validation",
    "Limitations",
    "References",
    "Appendix: evidence matrix",
]


# ── Styles ─────────────────────────────────────────────────────────────────────

def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"],
        fontSize=20, textColor=colors.HexColor("#1a1a2e"), spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader", parent=styles["Heading1"],
        fontSize=13, textColor=colors.HexColor("#16213e"),
        spaceBefore=14, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="BulletItem", parent=styles["Normal"],
        fontSize=10, leftIndent=14, spaceAfter=3, leading=14,
    ))
    styles.add(ParagraphStyle(
        name="ReportBody", parent=styles["Normal"],
        fontSize=10, leading=15, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Caption", parent=styles["Normal"],
        fontSize=8, textColor=colors.HexColor("#666666"), spaceAfter=4,
    ))
    return styles


def _safe(text: str) -> str:
    """Escape XML special chars and replace Unicode glyphs unsupported by reportlab's default font."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    replacements = {
        "‑": "-",   # non-breaking hyphen
        "‒": "-",   # figure dash
        "–": "-",   # en dash
        "—": "--",  # em dash
        "‘": "'",   # left single quote
        "’": "'",   # right single quote
        "“": '"',   # left double quote
        "”": '"',   # right double quote
        "•": "*",   # bullet
        "…": "...", # ellipsis
        " ": " ",   # non-breaking space
        "−": "-",   # minus sign
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Drop any remaining non-latin1 characters reportlab can't render
    return text.encode("latin-1", errors="replace").decode("latin-1")


def section_header(title: str, styles) -> list:
    return [
        Spacer(1, 8),
        Paragraph(_safe(title), styles["SectionHeader"]),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")),
        Spacer(1, 4),
    ]


def bullet_list(items: list[str], styles) -> list:
    return [Paragraph(f"• {_safe(item)}", styles["BulletItem"]) for item in items]


# ── Section builders ───────────────────────────────────────────────────────────

def render_problem_overview(artifacts: dict, spec: dict, styles) -> list:
    story = section_header("Problem Overview", styles)
    problem = artifacts.get("state", {}).get("problem", {})
    goal = problem.get("research_goal") or spec.get("research_goal", "")
    domain = problem.get("domain", "")
    if goal:
        story.append(Paragraph(_safe(f"Research goal: {goal}"), styles["ReportBody"]))
    if domain:
        story.append(Paragraph(_safe(f"Domain: {domain}"), styles["Caption"]))
    return story


def render_literature_review(artifacts: dict, styles) -> list:
    story = section_header("Literature Review", styles)
    lit = artifacts.get("literature_result", {})
    theme_analysis = lit.get("theme_analysis", {})

    themes = theme_analysis.get("themes", [])
    if themes:
        story.append(Paragraph("Key themes:", styles["ReportBody"]))
        story += bullet_list(themes, styles)

    papers = lit.get("selected_papers", [])
    if papers:
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"Selected papers ({len(papers)}):", styles["ReportBody"]))
        for p in papers:
            title   = _safe(p.get("title", "Untitled"))
            authors = ", ".join(p.get("authors", []))
            year    = str(p.get("year", ""))
            venue   = _safe(p.get("venue", ""))
            story.append(Paragraph(
                f"<b>{title}</b> — {_safe(authors)} ({year}). {venue}",
                styles["BulletItem"]
            ))
            if p.get("connection_to_problem"):
                story.append(Paragraph(
                    _safe(p["connection_to_problem"]), styles["Caption"]
                ))
    return story


def render_methodological_synthesis(artifacts: dict, styles) -> list:
    story = section_header("Methodological Synthesis", styles)
    lit = artifacts.get("literature_result", {})
    methods = lit.get("theme_analysis", {}).get("method_families", [])
    if methods:
        story.append(Paragraph("Method families identified:", styles["ReportBody"]))
        story += bullet_list(methods, styles)
    risks = lit.get("risks", [])
    if risks:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Open risks / gaps:", styles["ReportBody"]))
        story += bullet_list(risks, styles)
    return story


def render_computational_experiments(artifacts: dict, styles) -> list:
    story = section_header("Computational Experiments", styles)
    exe = artifacts.get("execution_result", {})
    findings = exe.get("results", {}).get("main_findings", [])
    if findings:
        story += bullet_list(findings, styles)
    else:
        story.append(Paragraph("No execution results available.", styles["Caption"]))
    return story


def render_validation(artifacts: dict, styles) -> list:
    story = section_header("Validation", styles)
    exe = artifacts.get("execution_result", {})
    checks = exe.get("results", {}).get("numerical_checks", [])
    story += bullet_list(checks, styles) if checks else [
        Paragraph("No validation results available.", styles["Caption"])
    ]
    return story


def render_limitations(artifacts: dict, styles) -> list:
    story = section_header("Limitations", styles)
    items: list[str] = []
    items += artifacts.get("literature_result", {}).get("risks", [])
    items += artifacts.get("execution_result", {}).get("limitations", [])
    story += bullet_list(items, styles) if items else [
        Paragraph("No limitations recorded.", styles["Caption"])
    ]
    return story


def render_references(artifacts: dict, styles) -> list:
    story = section_header("References", styles)
    papers = artifacts.get("literature_result", {}).get("selected_papers", [])
    for i, p in enumerate(papers, 1):
        authors = ", ".join(p.get("authors", []))
        year    = p.get("year", "")
        title   = _safe(p.get("title", ""))
        venue   = _safe(p.get("venue", ""))
        doi     = _safe(p.get("doi_or_arxiv", ""))
        ref_line = f"[{i}] {_safe(authors)} ({year}). {title}. <i>{venue}</i>."
        if doi:
            ref_line += f" {doi}"
        story.append(Paragraph(ref_line, styles["BulletItem"]))
    return story


def render_evidence_matrix(artifacts: dict, styles) -> list:
    story = section_header("Appendix: Evidence Matrix", styles)
    papers = artifacts.get("literature_result", {}).get("selected_papers", [])
    if not papers:
        story.append(Paragraph("No papers available.", styles["Caption"]))
        return story

    header = ["Title", "Year", "Method", "Confidence"]
    rows = [header]
    for p in papers:
        rows.append([
            _safe(p.get("title", "")[:60]),
            str(p.get("year", "")),
            _safe(p.get("method_summary", "")[:80]),
            p.get("source_confidence", ""),
        ])
    table = Table(rows, colWidths=[7*cm, 1.5*cm, 6*cm, 2*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#f5f5f5"), colors.white]),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
    ]))
    story += [table, Spacer(1, 8)]
    return story


SECTION_MAP = {
    "Problem overview":          render_problem_overview,
    "Literature review":         render_literature_review,
    "Methodological synthesis":  render_methodological_synthesis,
    "Computational experiments": render_computational_experiments,
    "Validation":                render_validation,
    "Limitations":               render_limitations,
    "References":                render_references,
    "Appendix: evidence matrix": render_evidence_matrix,
}


# ── Artifact loader ────────────────────────────────────────────────────────────

def load_artifacts(artifact_refs: list[str]) -> dict[str, Any]:
    """Read each artifact_ref JSON file; key by filename stem."""
    loaded: dict[str, Any] = {}
    for ref in artifact_refs:
        path = Path(ref)
        if path.exists():
            try:
                loaded[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                print(f"[{ROLE}] Warning: could not load {ref}: {exc}", file=sys.stderr)
        else:
            print(f"[{ROLE}] Warning: artifact not found: {ref}", file=sys.stderr)
    return loaded


# ── Core PDF builder ───────────────────────────────────────────────────────────

def build_pdf(spec: dict[str, Any], pdf_path: str) -> str:
    styles   = build_styles()
    artifacts = load_artifacts(spec.get("artifact_refs", []))
    sections  = spec.get("sections", SECTION_RENDERERS)

    story: list = []
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Research Report", styles["ReportTitle"]))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
        f"Type: {spec.get('report_type', 'research_memo')}",
        styles["Caption"],
    ))
    story.append(HRFlowable(width="100%", thickness=1,
                            color=colors.HexColor("#16213e")))

    for section_name in SECTION_RENDERERS:
        if section_name not in sections:
            continue
        renderer = SECTION_MAP.get(section_name)
        if not renderer:
            continue
        if section_name in ("Problem overview",):
            story += renderer(artifacts, spec, styles)
        else:
            story += renderer(artifacts, styles)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2*cm,    bottomMargin=2*cm,
    )
    doc.build(story)
    print(f"[{ROLE}] PDF saved to {pdf_path}", file=sys.stderr)
    return pdf_path


# ── Core logic ─────────────────────────────────────────────────────────────────

def run_pdf_generator(request: dict[str, Any]) -> dict[str, Any]:
    trace_id = request.get("trace_id", "unknown")

    if not request.get("approved_by_reviewer"):
        return {
            "role": ROLE,
            "trace_id": trace_id,
            "status": "blocked",
            "error": "approved_by_reviewer must be true — reviewer PASS required before PDF generation",
        }

    project_id = request.get("project_id", "project")
    pdf_path   = f"projects/{project_id}/output/report.pdf"
    Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)

    build_pdf(request, pdf_path)

    return {
        "role": ROLE,
        "trace_id": trace_id,
        "status": "ok",
        "final_pdf": pdf_path,
        "report_type": request.get("report_type", "research_memo"),
        "sections_rendered": request.get("sections", SECTION_RENDERERS),
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

def load_request(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description=PURPOSE)
    parser.add_argument("--request", help="Path to report spec JSON")
    parser.add_argument("--output",  help="Path to write response JSON")
    args = parser.parse_args()

    request  = load_request(args.request)
    response = run_pdf_generator(request)
    payload  = json.dumps(response, indent=2, ensure_ascii=False) + "\n"

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload, encoding="utf-8")
        print(f"[{ROLE}] Response written to {args.output}", file=sys.stderr)
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
