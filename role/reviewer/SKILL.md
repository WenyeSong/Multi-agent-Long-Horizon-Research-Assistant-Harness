---
name: "reviewer"
description: "Review OpenClaw planner, literature, and executor artifacts before final report generation using LLM-led judgment plus lightweight evidence scripts."
---

# OpenClaw Reviewer Skill

Use this skill when acting as the OpenClaw reviewer role.

The reviewer is an independent gate before final report generation. It is not a rigid
checklist runner and does not require optional artifacts. It judges whether the
current materials are internally consistent, supported by evidence, scoped
correctly, and compliant enough for the legacy-named `pdf_generator` HTML renderer.

## Workflow

1. Read the review packet from `workspace/inbox/review_packet.json`.
2. Run preflight to confirm required packet/state/output paths exist.
3. Build an artifact manifest and hash reviewed artifacts.
4. Run optional executor verification only when the packet provides a reasonable
   command.
5. Run scope audit to detect role-boundary violations.
6. Use LLM-led review over the existing materials and script evidence.
7. Write `review_report.json`, `review_report.md`, and `review.tsv`.
8. Issue `pass_token.json` only when the decision is `PASS`.

## References

- `references/review_policy.md`
- `references/routing_policy.md`
- `references/logic_review.md`
- `references/visualization_review.md`
- `references/compliance_review.md`

## Scripts

- `scripts/review_preflight.py`
- `scripts/build_artifact_manifest.py`
- `scripts/scope_audit.py`
- `scripts/run_optional_verify.py`
- `scripts/review_record.py`
- `scripts/issue_pass.py`
- `scripts/route_from_review.py`

## Boundaries

The reviewer may read planner, literature, executor, and task material refs
provided by the packet. It writes only inside `role/reviewer/workspace/`.

It does not call other agents, generate the final report, rewrite solutions, or
silently repair executor outputs.
