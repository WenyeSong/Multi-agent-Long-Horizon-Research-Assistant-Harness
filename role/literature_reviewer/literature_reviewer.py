#!/usr/bin/env python3
"""literature_reviewer — find papers, build evidence matrix, return structured artifact."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI

ROLE = "literature_reviewer"
PURPOSE = "Find and summarize papers, then return structured literature artifacts."
SCHEMA_REFS = ["schemas/literature_result.schema.json"]

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ.get("OPENAI_BASE_URL"),
)
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

MAX_RETRIES = 2   # how many times judge can send SearchAgent back for revision

THRESHOLDS = {
    "relevance":      7,
    "falsifiability": 7,
    "coherence":      6,
    "parsimony":      6,
}


# ── LLM helper ────────────────────────────────────────────────────────────────

def _call_llm(messages: list[dict], temperature: float) -> str:
    kwargs = dict(model=MODEL, messages=messages, temperature=temperature)
    try:
        resp = client.chat.completions.create(
            **kwargs, response_format={"type": "json_object"}
        )
    except Exception:
        resp = client.chat.completions.create(**kwargs)

    content = resp.choices[0].message.content or ""
    if "```" in content:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if m:
            content = m.group(1).strip()
    return content


# ── SearchAgent ────────────────────────────────────────────────────────────────

class SearchAgent:
    """Finds 10 relevant papers with full citation metadata."""

    SYSTEM_PROMPT = (
        "You are a scientific literature search specialist. "
        "Return exactly 10 papers with complete, accurate metadata. "
        "Always respond in valid JSON."
    )

    PROMPT = """Research goal: "{goal}"
Domain: {domain}

Find exactly 10 highly relevant academic papers. Follow these selection rules:

Selection rules:
- Do NOT select two papers from the same simulation project or research group (e.g. only one IllustrisTNG paper, only one EAGLE paper). Each paper must add distinct insight.
- Include at least one foundational or classic paper (published before 2010) that established the field.
- Prefer papers that represent diverse methodological approaches (simulations, observations, theory, semi-analytic models).

For each paper provide all fields accurately.
If you are uncertain about a DOI or URL, use an empty string — do not fabricate.

For source_confidence use these criteria:
- "high": published in a top venue (Nature, Science, ApJ, MNRAS, A&A) AND either well-established (>3 years old) or widely cited
- "medium": recent paper (<3 years) in a top venue, or older paper in a mid-tier venue
- "low": preprint only, or you are uncertain about the citation details
{feedback}
Respond in JSON:
{{
  "papers": [
    {{
      "title": "Full paper title",
      "authors": ["Author One", "Author Two"],
      "year": 2023,
      "venue": "Journal or Conference Name",
      "doi_or_arxiv": "10.xxxx/xxxx or arxiv:XXXX.XXXXX",
      "url": "https://...",
      "relevance_score": 0.95,
      "method_summary": "One paragraph describing the method used",
      "key_equations": ["equation 1 in plain text", "equation 2"],
      "assumptions": ["assumption 1", "assumption 2"],
      "limitations": ["limitation 1", "limitation 2"],
      "connection_to_problem": "How this paper directly relates to the research goal",
      "source_confidence": "high"
    }}
  ]
}}"""

    def run(self, goal: str, domain: str, feedback: str = "") -> list[dict]:
        feedback_block = (
            f"\nPrevious attempt was rejected. Fix these issues:\n{feedback}\n"
            if feedback else ""
        )
        print(
            f"[SearchAgent] Searching (feedback={'yes' if feedback else 'none'})...",
            file=sys.stderr,
        )
        content = _call_llm([
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user",   "content": self.PROMPT.format(
                goal=goal, domain=domain, feedback=feedback_block
            )},
        ], temperature=0.3)
        result = json.loads(content)
        return result.get("papers", [])


# ── SummaryAgent ───────────────────────────────────────────────────────────────

class SummaryAgent:
    """Synthesises themes, method families, and risks from a paper list."""

    SYSTEM_PROMPT = (
        "You are a scientific research synthesiser. "
        "Given a list of papers, extract cross-cutting themes, method families, and risks. "
        "Always respond in valid JSON."
    )

    PROMPT = """Research goal: "{goal}"

Papers found:
{papers}

Extract:
1. Major research themes (3-6 short phrases)
2. Method families used across these papers (e.g. "transformer-based NLP", "RCT", "fMRI")
3. Risks or open problems identified in the literature

Respond in JSON:
{{
  "themes": ["theme 1", "theme 2", "theme 3"],
  "method_families": ["method family 1", "method family 2"],
  "risks": ["risk or open problem 1", "risk 2"]
}}"""

    def run(self, goal: str, papers: list[dict]) -> dict:
        print("[SummaryAgent] Synthesising themes and risks...", file=sys.stderr)
        paper_text = "\n".join(
            f"- {p.get('title', '')} ({p.get('year', '')}): {p.get('method_summary', '')}"
            for p in papers
        )
        content = _call_llm([
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user",   "content": self.PROMPT.format(goal=goal, papers=paper_text)},
        ], temperature=0.5)
        return json.loads(content)


# ── JudgeAgent ────────────────────────────────────────────────────────────────

class JudgeAgent:
    """Scores paper selection on 4 dimensions and returns failing reasons."""

    PROMPT = """Evaluate this literature review output for: "{goal}"

Themes: {themes}
Method families: {method_families}
Risks: {risks}

Papers:
{papers}

Score each dimension 0-10 and give one sentence reason:
1. relevance (Optimist): high-impact, directly addresses goal?
2. falsifiability (Skeptic): risks specific and grounded, hidden assumptions exposed?
3. coherence (Historian): missing classics, contradictions with established knowledge?
4. parsimony (Minimalist): non-redundant, each paper adds distinct value?

JSON only:
{{
  "relevance":      {{"score": <int>, "reason": "..."}},
  "falsifiability": {{"score": <int>, "reason": "..."}},
  "coherence":      {{"score": <int>, "reason": "..."}},
  "parsimony":      {{"score": <int>, "reason": "..."}}
}}"""

    def evaluate(self, goal: str, papers: list[dict], synthesis: dict) -> dict:
        print("[JudgeAgent] Evaluating paper selection...", file=sys.stderr)
        papers_text = "\n".join(
            f"[{i+1}] {p['title']} ({p['year']}) [{p['source_confidence']}]\n"
            f"     {p['connection_to_problem'][:100]}"
            for i, p in enumerate(papers)
        )
        content = _call_llm([
            {"role": "user", "content": self.PROMPT.format(
                goal=goal,
                themes=synthesis.get("themes", []),
                method_families=synthesis.get("method_families", []),
                risks=synthesis.get("risks", []),
                papers=papers_text,
            )},
        ], temperature=0.0)
        return json.loads(content)

    def failing_feedback(self, scores: dict) -> str:
        """Return a string listing which dimensions failed and why."""
        lines = []
        for dim, threshold in THRESHOLDS.items():
            s = scores[dim]["score"]
            if s < threshold:
                lines.append(
                    f"- {dim} scored {s}/{threshold}: {scores[dim]['reason']}"
                )
        return "\n".join(lines)

    def passed(self, scores: dict) -> bool:
        return all(scores[dim]["score"] >= THRESHOLDS[dim] for dim in THRESHOLDS)


# ── Paper normaliser ──────────────────────────────────────────────────────────

PAPER_DEFAULTS: dict[str, Any] = {
    "title": "", "authors": [], "year": 0, "venue": "", "doi_or_arxiv": "",
    "url": "", "relevance_score": 0.0, "method_summary": "", "key_equations": [],
    "assumptions": [], "limitations": [], "connection_to_problem": "",
    "source_confidence": "low",
}

def _normalise_paper(p: dict) -> dict:
    return {**PAPER_DEFAULTS, **p}


# ── Core logic (feedback loop) ────────────────────────────────────────────────

def run_literature_reviewer(request: dict[str, Any]) -> dict[str, Any]:
    trace_id   = request.get("trace_id", "unknown")
    goal       = request.get("research_goal", "")
    domain     = request.get("domain", "general")
    project_id = request.get("project_id", "project")

    search  = SearchAgent()
    summary = SummaryAgent()
    judge   = JudgeAgent()

    feedback   = ""
    last_scores: dict = {}

    for attempt in range(1, MAX_RETRIES + 2):   # attempts: 1, 2, 3 (initial + retries)
        print(f"[LiteratureReviewer] Attempt {attempt}/{MAX_RETRIES + 1}", file=sys.stderr)

        papers = [_normalise_paper(p) for p in search.run(goal, domain, feedback)]
        synthesis = summary.run(goal, papers)

        last_scores = judge.evaluate(goal, papers, synthesis)

        _print_scores(last_scores, attempt)

        if judge.passed(last_scores):
            print("[LiteratureReviewer] Judge PASS — done.", file=sys.stderr)
            break

        if attempt <= MAX_RETRIES:
            feedback = judge.failing_feedback(last_scores)
            print(
                f"[LiteratureReviewer] Judge FAIL — retrying with feedback:\n{feedback}",
                file=sys.stderr,
            )
        else:
            print(
                "[LiteratureReviewer] Max retries reached — using best result.",
                file=sys.stderr,
            )

    status = "ok" if len(papers) >= 10 else ("partial" if papers else "blocked")
    artifact_ref = f"projects/{project_id}/artifacts/literature_result.json"

    return {
        "trace_id": trace_id,
        "status": status,
        "selected_papers": papers[:10],
        "theme_analysis": {
            "themes": synthesis.get("themes", []),
            "method_families": synthesis.get("method_families", []),
        },
        "risks": synthesis.get("risks", []),
        "artifact_refs": [artifact_ref],
        "_judge_scores": last_scores,   # kept for debugging; planner can inspect
    }


def _print_scores(scores: dict, attempt: int) -> None:
    print(f"\n  [Judge scores — attempt {attempt}]", file=sys.stderr)
    for dim, thr in THRESHOLDS.items():
        s = scores[dim]["score"]
        tag = "ok" if s >= thr else "FAIL"
        print(f"    {tag} {dim:15s} {s}/10  {scores[dim]['reason'][:80]}",
              file=sys.stderr)
    print(file=sys.stderr)


# ── CLI ────────────────────────────────────────────────────────────────────────

def load_request(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description=PURPOSE)
    parser.add_argument("--request", help="Path to worker request JSON")
    parser.add_argument("--output",  help="Path to write response JSON")
    args = parser.parse_args()

    request  = load_request(args.request)
    response = run_literature_reviewer(request)
    payload  = json.dumps(response, indent=2, ensure_ascii=False) + "\n"

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload, encoding="utf-8")
        print(f"[{ROLE}] Written to {args.output}", file=sys.stderr)
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
