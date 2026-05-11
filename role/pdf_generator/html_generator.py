#!/usr/bin/env python3
"""html_generator — typeset approved artifacts into an interactive HTML report."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROLE = "html_generator"
PURPOSE = "Typeset approved artifacts into an interactive HTML report."
SCHEMA_REFS = ["schemas/report_spec.schema.json"]

CONFIDENCE_COLOR = {"high": "#22c55e", "medium": "#f59e0b", "low": "#ef4444"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _read_text(path: Path, max_chars: int = 20000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[:max_chars]


def _render_csv_table(csv_text: str, max_rows: int = 12) -> str:
    if not csv_text.strip():
        return ""
    rows = list(csv.reader(csv_text.splitlines()))
    if not rows:
        return ""
    head = "".join(f"<th>{_esc(cell)}</th>" for cell in rows[0])
    body_rows = []
    for row in rows[1:max_rows + 1]:
        body_rows.append("<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in row) + "</tr>")
    return (
        "<table class='matrix-table'><thead><tr>"
        + head
        + "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table>"
    )


def _render_matrix_html(papers: list[dict], sections: list[str]) -> str:
    if "Appendix: evidence matrix" not in sections:
        return ""
    rows = []
    for i, p in enumerate(papers):
        conf  = p.get("source_confidence", "low")
        color = CONFIDENCE_COLOR.get(conf, "#6b7280")
        rows.append(
            f'<tr><td>{i+1}</td>'
            f'<td>{_esc(p.get("title",""))}</td>'
            f'<td>{p.get("year","")}</td>'
            f'<td>{_esc(p.get("method_summary","")[:120])}...</td>'
            f'<td><span style="color:{color};font-weight:600">{conf}</span></td></tr>'
        )
    return (
        "<div class='section' id='matrix'>"
        "<div class='section-title'>Evidence Matrix</div>"
        "<table class='matrix-table'><thead><tr>"
        "<th>#</th><th>Title</th><th>Year</th><th>Method summary</th><th>Confidence</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _render_references_html(papers: list[dict], sections: list[str]) -> str:
    if "References" not in sections:
        return ""
    items = []
    for i, p in enumerate(papers):
        authors  = _esc(", ".join(p.get("authors", [])))
        year     = p.get("year", "")
        title    = _esc(p.get("title", ""))
        venue    = _esc(p.get("venue", ""))
        url      = _esc(p.get("url", ""))
        doi      = _esc(p.get("doi_or_arxiv", ""))
        doi_part = f'<a href="{url}" target="_blank" class="doi-link">{doi}</a>' if url else doi
        items.append(
            f'<div class="ref-item">[{i+1}] {authors}&nbsp;({year}).&nbsp;'
            f'<em>{title}</em>.&nbsp;{venue}.&nbsp;{doi_part}</div>'
        )
    return (
        "<div class='section' id='references'>"
        "<div class='section-title'>References</div>"
        + "".join(items) + "</div>"
    )


def _render_execution_html(artifacts: dict[str, Any], sections: list[str]) -> str:
    if "Computational experiments" not in sections and "Validation" not in sections:
        return ""

    response = artifacts.get("executor_response")
    children = artifacts.get("_execution_artifacts", {})
    results = children.get("results_main", {}).get("json") or artifacts.get("results", {})
    tests = children.get("tests_main", {}).get("json") or artifacts.get("tests", {})
    notes = children.get("notes_main", {}).get("text", "")
    metrics = (
        results.get("generated_payload", {}).get("metrics")
        or (results.get("attempts") or [{}])[0].get("metrics")
        or {}
    )
    task = results.get("task", {}) if isinstance(results, dict) else {}
    limitations = _as_list(response.get("limitations") if isinstance(response, dict) else []) + _as_list(
        results.get("llm", {}).get("limitations") if isinstance(results, dict) else []
    )

    metric_cards = ""
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            shown = f"{value:.6g}"
        else:
            shown = str(value)
        metric_cards += (
            "<div class='metric-card'>"
            f"<div class='metric-value'>{_esc(shown)}</div>"
            f"<div class='metric-label'>{_esc(key.replace('_', ' '))}</div>"
            "</div>"
        )

    artifact_rows = ""
    if isinstance(response, dict):
        for artifact in _as_list(response.get("artifacts")):
            if not isinstance(artifact, dict):
                continue
            artifact_rows += (
                "<tr>"
                f"<td>{_esc(artifact.get('artifact_id', ''))}</td>"
                f"<td>{_esc(artifact.get('kind', ''))}</td>"
                f"<td>{_esc(artifact.get('description', ''))}</td>"
                f"<td><code>{_esc(artifact.get('path', ''))}</code></td>"
                "</tr>"
            )

    checks_html = ""
    for check in _as_list(tests.get("checks") if isinstance(tests, dict) else []):
        if not isinstance(check, dict):
            continue
        status = check.get("status", "unknown")
        checks_html += (
            "<li class='check-item'>"
            f"<span class='check-status'>{_esc(status)}</span>"
            f"<span>{_esc(check.get('criterion_id', 'criterion'))}: "
            f"{_esc(check.get('evidence', 'No evidence supplied.'))}</span>"
            "</li>"
        )

    figure_html = ""
    for artifact_id, payload in children.items():
        if payload.get("format") == "svg" and payload.get("text"):
            figure_html = (
                "<div class='figure-box'>"
                f"<div class='subtle-label'>{_esc(artifact_id)}</div>"
                f"{payload['text']}"
                "</div>"
            )
            break

    table_html = ""
    for payload in children.values():
        if payload.get("format") == "csv" and payload.get("text"):
            table_html = _render_csv_table(payload["text"])
            break

    experiment = ""
    if "Computational experiments" in sections:
        experiment = (
            "<div class='section' id='experiments'>"
            "<div class='section-title'>Computational Experiments</div>"
            f"<p class='body-copy'>{_esc(response.get('summary', '') if isinstance(response, dict) else '')}</p>"
            f"<p class='body-copy'><strong>Task:</strong> {_esc(task.get('title', 'Execution artifact review'))}. "
            f"{_esc(task.get('objective', ''))}</p>"
            f"<p class='body-copy'><strong>Scope:</strong> {_esc(task.get('scope', 'not specified'))}</p>"
            f"<div class='metric-grid'>{metric_cards}</div>"
            f"{figure_html}"
            f"{table_html}"
            "</div>"
        )

    validation = ""
    if "Validation" in sections:
        validation = (
            "<div class='section' id='validation'>"
            "<div class='section-title'>Validation</div>"
            f"<p class='body-copy'><strong>Overall:</strong> {_esc(tests.get('overall', 'unknown') if isinstance(tests, dict) else 'unknown')}</p>"
            f"<ul class='check-list'>{checks_html}</ul>"
            + ("<p class='body-copy'><strong>Executor notes:</strong> " + _esc(notes) + "</p>" if notes else "")
            + ("<p class='body-copy'><strong>Limitations:</strong> " + _esc('; '.join(str(item) for item in limitations)) + "</p>" if limitations else "")
            + (
                "<table class='matrix-table'><thead><tr><th>Artifact</th><th>Kind</th><th>Description</th><th>Path</th></tr></thead>"
                f"<tbody>{artifact_rows}</tbody></table>"
                if artifact_rows else ""
            )
            + "</div>"
        )

    return experiment + validation


# ── HTML builder ──────────────────────────────────────────────────────────────

def build_html(spec: dict[str, Any], artifacts: dict[str, Any]) -> str:
    lit     = artifacts.get("literature_result", {})
    papers  = lit.get("selected_papers", [])
    themes  = lit.get("theme_analysis", {}).get("themes", [])
    methods = lit.get("theme_analysis", {}).get("method_families", [])
    risks   = lit.get("risks", [])
    executor_response = artifacts.get("executor_response")
    sections    = spec.get("sections", [])
    report_type = spec.get("report_type", "research_memo")
    generated   = datetime.now().strftime("%Y-%m-%d %H:%M")

    # paper cards
    paper_cards = ""
    for i, p in enumerate(papers):
        relevance  = float(p.get("relevance_score", 0))
        conf       = p.get("source_confidence", "low")
        conf_color = CONFIDENCE_COLOR.get(conf, "#6b7280")
        authors_str = ", ".join(p.get("authors", [])[:3])
        if len(p.get("authors", [])) > 3:
            authors_str += " et al."
        url      = _esc(p.get("url", ""))
        doi      = _esc(p.get("doi_or_arxiv", ""))
        doi_link = f'<a href="{url}" target="_blank" class="doi-link">{doi}</a>' if url else doi

        assumptions = "".join(f"<li>{_esc(a)}</li>" for a in p.get("assumptions", []))
        limitations = "".join(f"<li>{_esc(l)}</li>" for l in p.get("limitations", []))
        equations   = "".join(f"<li><code>{_esc(e)}</code></li>" for e in p.get("key_equations", []))

        paper_cards += (
            f'<div class="paper-card" id="paper-{i+1}">'
            f'<div class="paper-header" onclick="togglePaper({i})">'
            f'<div class="paper-number">{i+1}</div>'
            f'<div class="paper-main">'
            f'<div class="paper-title">{_esc(p.get("title",""))}</div>'
            f'<div class="paper-meta">{_esc(authors_str)} &middot; {p.get("year","")} &middot; <em>{_esc(p.get("venue",""))}</em></div>'
            f'</div>'
            f'<div class="paper-right">'
            f'<div class="relevance-bar-wrap"><div class="relevance-bar" style="width:{int(relevance*100)}%"></div></div>'
            f'<div class="relevance-label">{int(relevance*100)}%</div>'
            f'<span class="conf-badge" style="background:{conf_color}">{conf}</span>'
            f'<span class="chevron" id="chevron-{i}">&#9660;</span>'
            f'</div></div>'
            f'<div class="paper-body" id="body-{i}" style="display:none">'
            f'<p class="connection">{_esc(p.get("connection_to_problem",""))}</p>'
            f'<p class="method-summary">{_esc(p.get("method_summary",""))}</p>'
            f'<div class="detail-grid">'
            + (f'<div><strong>Key equations</strong><ul>{equations}</ul></div>' if equations else '')
            + (f'<div><strong>Assumptions</strong><ul>{assumptions}</ul></div>' if assumptions else '')
            + (f'<div><strong>Limitations</strong><ul>{limitations}</ul></div>' if limitations else '')
            + f'</div>'
            + (f'<div class="doi-row">{doi_link}</div>' if doi else '')
            + f'</div></div>'
        )

    chart_labels = json.dumps([p.get("title", "")[:40] + "..." for p in papers])
    chart_data   = json.dumps([float(p.get("relevance_score", 0)) * 100 for p in papers])

    theme_tags  = "".join(f'<span class="tag tag-theme">{_esc(t)}</span>' for t in themes)
    method_tags = "".join(f'<span class="tag tag-method">{_esc(m)}</span>' for m in methods)
    risk_items  = "".join(
        f'<li class="risk-item"><span class="risk-icon">&#9888;</span>{_esc(r)}</li>'
        for r in risks
    )

    section_nav = {
        "Problem overview":          ("overview",   "Overview"),
        "Literature review":         ("papers",     "Papers"),
        "Methodological synthesis":  ("synthesis",  "Methods"),
        "Computational experiments": ("experiments","Experiments"),
        "Validation":                ("validation", "Validation"),
        "Limitations":               ("limitations","Risks"),
        "References":                ("references", "References"),
        "Appendix: evidence matrix": ("matrix",     "Matrix"),
    }
    nav_links = "".join(
        f'<a href="#{anchor}" class="nav-link">{label}</a>'
        for sec, (anchor, label) in section_nav.items()
        if sec in sections
    )

    overview_html = (
        "<div class='section' id='overview'>"
        "<div class='section-title'>Problem Overview</div>"
        "<p style='color:var(--muted);font-size:.875rem'>"
        + _esc(
            spec.get("problem_overview")
            or (
                "This report summarizes approved literature and execution artifacts."
                if executor_response else
                "See literature review and methodological synthesis below."
            )
        )
        + "</p></div>"
        if "Problem overview" in sections else ""
    )

    synthesis_html = (
        "<div class='section' id='synthesis'>"
        "<div class='section-title'>Themes &amp; Methods</div>"
        "<div style='margin-bottom:1rem'>"
        "<strong style='font-size:.8rem;color:var(--muted);display:block;margin-bottom:.5rem'>RESEARCH THEMES</strong>"
        + theme_tags +
        "</div><div>"
        "<strong style='font-size:.8rem;color:var(--muted);display:block;margin-bottom:.5rem'>METHOD FAMILIES</strong>"
        + method_tags + "</div></div>"
        if "Methodological synthesis" in sections else ""
    )

    risks_html = (
        "<div class='section' id='limitations' style='margin-bottom:0'>"
        "<div class='section-title'>Risks &amp; Open Problems</div>"
        f"<ul class='risk-list'>{risk_items}</ul></div>"
        if "Limitations" in sections else ""
    )

    papers_html = (
        "<div class='section' id='papers'>"
        "<div class='section-title'>Selected Papers</div>"
        "<div class='search-wrap'>"
        "<span class='search-icon'>&#128269;</span>"
        "<input class='search-input' id='paperSearch' type='text' "
        "placeholder='Search papers...' oninput='filterPapers()'></div>"
        f"<div id='paperList'>{paper_cards}</div></div>"
        if "Literature review" in sections else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Research Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root {{
    --navy:#0f172a; --blue:#3b82f6; --light-blue:#eff6ff;
    --gray:#f8fafc; --border:#e2e8f0; --text:#1e293b; --muted:#64748b;
  }}
  *{{ box-sizing:border-box; margin:0; padding:0; }}
  body{{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
         background:var(--gray); color:var(--text); }}
  nav{{ position:sticky; top:0; z-index:100; background:var(--navy);
        padding:0 2rem; display:flex; align-items:center; gap:1.5rem; height:56px; }}
  nav .brand{{ color:white; font-weight:700; font-size:1rem; margin-right:auto; }}
  .nav-link{{ color:#94a3b8; text-decoration:none; font-size:.875rem;
              padding:.25rem .5rem; border-radius:4px; transition:all .15s; }}
  .nav-link:hover{{ color:white; background:rgba(255,255,255,.1); }}
  .hero{{ background:linear-gradient(135deg,var(--navy) 0%,#1e3a5f 100%);
          color:white; padding:3rem 2rem 2.5rem; }}
  .hero h1{{ font-size:2rem; font-weight:800; margin-bottom:.5rem; }}
  .hero .meta{{ color:#94a3b8; font-size:.875rem; margin-bottom:1.5rem; }}
  .hero .badge{{ display:inline-block; background:rgba(59,130,246,.3);
                 border:1px solid rgba(59,130,246,.5); color:#93c5fd;
                 padding:.25rem .75rem; border-radius:999px; font-size:.75rem; }}
  .container{{ max-width:1100px; margin:0 auto; padding:2rem 1.5rem; }}
  .section{{ background:white; border-radius:12px; padding:1.75rem;
             margin-bottom:1.5rem; border:1px solid var(--border); }}
  .section-title{{ font-size:1.125rem; font-weight:700; color:var(--navy);
                   margin-bottom:1.25rem; display:flex; align-items:center; gap:.5rem; }}
  .section-title::before{{ content:""; display:block; width:4px; height:20px;
                            background:var(--blue); border-radius:2px; }}
  .stats{{ display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin-bottom:1.5rem; }}
  .stat-card{{ background:white; border-radius:10px; padding:1.25rem;
               border:1px solid var(--border); text-align:center; }}
  .stat-value{{ font-size:2rem; font-weight:800; color:var(--blue); }}
  .stat-label{{ font-size:.75rem; color:var(--muted); margin-top:.25rem; }}
  .tag{{ display:inline-block; padding:.3rem .75rem; border-radius:999px;
         font-size:.8rem; font-weight:500; margin:.2rem; }}
  .tag-theme{{ background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe; }}
  .tag-method{{ background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; }}
  .risk-list{{ list-style:none; }}
  .risk-item{{ display:flex; align-items:flex-start; gap:.75rem; padding:.75rem;
               border-radius:8px; margin-bottom:.5rem; background:#fff7ed;
               border:1px solid #fed7aa; font-size:.875rem; }}
  .risk-icon{{ color:#f59e0b; font-size:1rem; flex-shrink:0; }}
  .chart-wrap{{ position:relative; height:260px; }}
  .two-col{{ display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1.5rem; }}
  .two-col .section{{ margin-bottom:0; }}
  .paper-card{{ border:1px solid var(--border); border-radius:10px;
                margin-bottom:.75rem; overflow:hidden; transition:box-shadow .15s; }}
  .paper-card:hover{{ box-shadow:0 4px 12px rgba(0,0,0,.08); }}
  .paper-header{{ display:flex; align-items:center; gap:1rem; padding:1rem 1.25rem;
                  cursor:pointer; user-select:none; }}
  .paper-number{{ width:28px; height:28px; border-radius:50%; background:var(--light-blue);
                  color:var(--blue); font-size:.8rem; font-weight:700;
                  display:flex; align-items:center; justify-content:center; flex-shrink:0; }}
  .paper-main{{ flex:1; min-width:0; }}
  .paper-title{{ font-weight:600; font-size:.9rem; color:var(--navy);
                 white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .paper-meta{{ font-size:.78rem; color:var(--muted); margin-top:.2rem; }}
  .paper-right{{ display:flex; align-items:center; gap:.75rem; flex-shrink:0; }}
  .relevance-bar-wrap{{ width:80px; height:6px; background:#e2e8f0;
                         border-radius:3px; overflow:hidden; }}
  .relevance-bar{{ height:100%; background:var(--blue); border-radius:3px; }}
  .relevance-label{{ font-size:.75rem; color:var(--muted); width:30px; }}
  .conf-badge{{ font-size:.7rem; font-weight:600; color:white;
                padding:.15rem .5rem; border-radius:999px; }}
  .chevron{{ color:var(--muted); font-size:.75rem; transition:transform .2s; }}
  .paper-body{{ padding:0 1.25rem 1.25rem 3.75rem; border-top:1px solid var(--border); }}
  .connection{{ font-size:.875rem; font-weight:500; color:var(--navy); margin:.75rem 0 .5rem; }}
  .method-summary{{ font-size:.825rem; color:var(--muted); line-height:1.6; }}
  .detail-grid{{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
                 gap:1rem; margin-top:1rem; }}
  .detail-grid ul{{ padding-left:1.2rem; font-size:.8rem; line-height:1.7; }}
  .detail-grid strong{{ font-size:.8rem; color:var(--navy); display:block; margin-bottom:.3rem; }}
  code{{ background:#f1f5f9; padding:.1rem .3rem; border-radius:3px;
         font-family:monospace; font-size:.78rem; }}
  .doi-row{{ margin-top:.75rem; font-size:.8rem; }}
  .doi-link{{ color:var(--blue); text-decoration:none; }}
  .doi-link:hover{{ text-decoration:underline; }}
  .search-wrap{{ margin-bottom:1rem; position:relative; }}
  .search-input{{ width:100%; padding:.6rem 1rem .6rem 2.5rem;
                  border:1px solid var(--border); border-radius:8px;
                  font-size:.875rem; outline:none; transition:border-color .15s; }}
  .search-input:focus{{ border-color:var(--blue); }}
  .search-icon{{ position:absolute; left:.75rem; top:50%; transform:translateY(-50%);
                 color:var(--muted); pointer-events:none; }}
  .matrix-table{{ width:100%; border-collapse:collapse; font-size:.8rem; }}
  .matrix-table th{{ background:var(--navy); color:white; padding:.6rem .75rem;
                      text-align:left; font-weight:600; }}
  .matrix-table td{{ padding:.6rem .75rem; border-bottom:1px solid var(--border); vertical-align:top; }}
  .matrix-table tr:nth-child(even) td{{ background:var(--gray); }}
  .ref-item{{ font-size:.825rem; padding:.6rem 0; border-bottom:1px solid var(--border); line-height:1.6; }}
  .ref-item:last-child{{ border-bottom:none; }}
  .body-copy{{ color:var(--muted); font-size:.9rem; line-height:1.65; margin-bottom:1rem; }}
  .metric-grid{{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:.75rem; margin:1rem 0; }}
  .metric-card{{ background:#f8fafc; border:1px solid var(--border); border-radius:8px; padding:1rem; }}
  .metric-value{{ font-size:1.35rem; font-weight:800; color:var(--navy); }}
  .metric-label{{ font-size:.75rem; color:var(--muted); text-transform:capitalize; margin-top:.25rem; }}
  .figure-box{{ overflow:auto; background:white; border:1px solid var(--border); border-radius:8px; padding:1rem; margin:1rem 0; }}
  .figure-box svg{{ max-width:100%; height:auto; }}
  .subtle-label{{ font-size:.72rem; color:var(--muted); margin-bottom:.5rem; text-transform:uppercase; letter-spacing:.04em; }}
  .check-list{{ list-style:none; margin:0 0 1rem; }}
  .check-item{{ display:flex; gap:.6rem; align-items:flex-start; padding:.55rem 0; border-bottom:1px solid var(--border); font-size:.875rem; }}
  .check-status{{ color:#166534; background:#dcfce7; border:1px solid #bbf7d0; border-radius:999px; padding:.1rem .45rem; font-size:.72rem; font-weight:700; }}
  @media(max-width:600px){{
    .stats{{ grid-template-columns:1fr 1fr; }}
    .two-col{{ grid-template-columns:1fr; }}
    .paper-right{{ display:none; }}
  }}
</style>
</head>
<body>

<nav>
  <span class="brand">&#128196; Research Report</span>
  {nav_links}
</nav>

<div class="hero">
  <h1>Research Report</h1>
  <div class="meta">Generated {generated} &nbsp;&middot;&nbsp; {_esc(report_type.replace("_"," ").title())}</div>
  <span class="badge">&#10003; Reviewer approved</span>
</div>

<div class="container">

  <div class="stats">
    <div class="stat-card">
      <div class="stat-value">{len(papers)}</div>
      <div class="stat-label">Papers selected</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{len(themes)}</div>
      <div class="stat-label">Key themes</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{len(risks)}</div>
      <div class="stat-label">Open risks</div>
    </div>
  </div>

  {overview_html}
  {synthesis_html}
  {_render_execution_html(artifacts, sections)}

  <div class="two-col">
    <div class="section">
      <div class="section-title">Relevance Scores</div>
      <div class="chart-wrap"><canvas id="relevanceChart"></canvas></div>
    </div>
    {risks_html}
  </div>

  {papers_html}

  {_render_references_html(papers, sections)}
  {_render_matrix_html(papers, sections)}

</div>

<script>
const ctx = document.getElementById('relevanceChart').getContext('2d');
new Chart(ctx, {{
  type: 'bar',
  data: {{
    labels: {chart_labels},
    datasets: [{{
      label: 'Relevance %',
      data: {chart_data},
      backgroundColor: 'rgba(59,130,246,0.7)',
      borderColor: 'rgba(59,130,246,1)',
      borderWidth: 1,
      borderRadius: 4,
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ min:0, max:100, ticks:{{ font:{{ size:10 }} }} }},
      y: {{ ticks:{{ font:{{ size:9 }} }} }}
    }}
  }}
}});

function togglePaper(i) {{
  const body    = document.getElementById('body-' + i);
  const chevron = document.getElementById('chevron-' + i);
  const open    = body.style.display === 'none';
  body.style.display      = open ? 'block' : 'none';
  chevron.style.transform = open ? 'rotate(180deg)' : '';
}}

function filterPapers() {{
  const q = document.getElementById('paperSearch').value.toLowerCase();
  document.querySelectorAll('.paper-card').forEach(card => {{
    card.style.display = card.innerText.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""


# ── Artifact loader ───────────────────────────────────────────────────────────

def load_artifacts(artifact_refs: list[str]) -> dict[str, Any]:
    loaded: dict[str, Any] = {"_execution_artifacts": {}}
    for ref in artifact_refs:
        path = Path(ref)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                loaded[path.stem] = data
                if path.stem in {"executor_response", "execution_result"} and isinstance(data, dict):
                    loaded["executor_response"] = data
                    for artifact in _as_list(data.get("artifacts")):
                        if not isinstance(artifact, dict) or not artifact.get("path"):
                            continue
                        artifact_path = Path(str(artifact["path"]))
                        artifact_id = str(artifact.get("artifact_id") or artifact_path.stem)
                        payload = {
                            "path": artifact_path.as_posix(),
                            "kind": artifact.get("kind", ""),
                            "format": artifact.get("format", artifact_path.suffix.lstrip(".")),
                            "description": artifact.get("description", ""),
                        }
                        if artifact_path.exists() and payload["format"] == "json":
                            payload["json"] = json.loads(artifact_path.read_text(encoding="utf-8"))
                        elif artifact_path.exists() and payload["format"] in {"csv", "md", "txt", "svg"}:
                            payload["text"] = _read_text(artifact_path)
                        loaded["_execution_artifacts"][artifact_id] = payload
            except Exception as exc:
                print(f"[{ROLE}] Warning: could not load {ref}: {exc}", file=sys.stderr)
        else:
            print(f"[{ROLE}] Warning: artifact not found: {ref}", file=sys.stderr)
    return loaded


def has_meaningful_content(spec: dict[str, Any], artifacts: dict[str, Any]) -> bool:
    lit = artifacts.get("literature_result", {})
    if isinstance(lit, dict) and lit.get("selected_papers"):
        return True
    executor_response = artifacts.get("executor_response")
    if isinstance(executor_response, dict) and executor_response.get("artifacts"):
        return True
    return bool(spec.get("approved_content"))


# ── Core logic ────────────────────────────────────────────────────────────────

def run_html_generator(request: dict[str, Any]) -> dict[str, Any]:
    trace_id = request.get("trace_id", "unknown")

    if not request.get("approved_by_reviewer"):
        return {
            "role": ROLE,
            "trace_id": trace_id,
            "status": "blocked",
            "error": "approved_by_reviewer must be true",
        }

    project_id = request.get("project_id", "project")
    html_path  = f"projects/{project_id}/output/report.html"
    Path(html_path).parent.mkdir(parents=True, exist_ok=True)

    artifacts = load_artifacts(request.get("artifact_refs", []))
    if not has_meaningful_content(request, artifacts):
        return {
            "role": ROLE,
            "trace_id": trace_id,
            "status": "blocked",
            "error": "No meaningful approved literature or execution artifacts were available for report rendering.",
            "artifact_refs": request.get("artifact_refs", []),
        }

    html      = build_html(request, artifacts)
    Path(html_path).write_text(html, encoding="utf-8")
    print(f"[{ROLE}] HTML saved to {html_path}", file=sys.stderr)

    return {
        "role": ROLE,
        "trace_id": trace_id,
        "status": "ok",
        "final_html": html_path,
        "report_type": request.get("report_type", "research_memo"),
        "sections_rendered": request.get("sections", []),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

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
    response = run_html_generator(request)
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
