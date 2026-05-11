# Executor Artifact Contract

This document defines the expected output artifact style for executor runs.

The executor should return references to artifacts, not large embedded payloads. The planner should be able to inspect the artifact list and understand which files are primary results, which are diagnostics, and which exist only for auditability.

## Core Output Set

Every successful or partially successful executor run should try to produce:

```text
results.json
tests.json
environment.json
artifacts.json
notes.md
```

Use these purposes:

| File | Purpose |
| --- | --- |
| `results.json` | Main numerical or structured result summary. |
| `tests.json` | Validation checks mapped to planner success criteria. |
| `environment.json` | Runtime, package, platform, and seed information. |
| `artifacts.json` | Manifest of all generated artifacts. |
| `notes.md` | Short human-readable notes, limitations, and interpretation boundaries. |

## Figure Outputs

Figures should go under:

```text
figures/
```

Recommended naming:

```text
figures/<attempt_id>_<figure_role>.<ext>
```

Examples:

```text
figures/attempt_01_loss_curve.png
figures/attempt_01_residual_diagnostic.png
figures/attempt_02_parameter_sweep.svg
```

Use stable, descriptive names. Avoid names like `plot.png`, `final.png`, or `image1.png`.

## Figure Formats

Preferred formats:

- `png` for standard plots, heatmaps, screenshots, and raster diagnostics.
- `svg` for line plots or diagrams where vector quality matters.
- `pdf` only if the planner explicitly requests publication-quality figure export.

For the MVP, `png` is the safest default.

## Figure Metadata

Every figure should be referenced in `artifacts.json` with:

- `artifact_id`;
- `path`;
- `kind: "figure"`;
- `format`;
- `role`;
- `title`;
- `description`;
- `created_from_attempt`;
- `related_result_keys`;
- `limitations`.

Example:

```json
{
  "artifact_id": "fig_attempt_01_loss_curve",
  "path": "figures/attempt_01_loss_curve.png",
  "kind": "figure",
  "format": "png",
  "role": "diagnostic",
  "title": "Loss curve for attempt 01",
  "description": "Shows training loss by iteration for the first parameter setting.",
  "created_from_attempt": "attempt_01",
  "related_result_keys": ["attempts.attempt_01.metrics.loss"],
  "limitations": ["Single run only; no confidence interval."]
}
```

## Table Outputs

Tables should go under:

```text
tables/
```

Recommended naming:

```text
tables/<attempt_id>_<table_role>.csv
tables/<attempt_id>_<table_role>.json
```

Use `csv` for simple rectangular data and `json` for nested structured data.

Examples:

```text
tables/attempt_01_metrics.csv
tables/attempt_02_parameter_sweep.csv
tables/all_attempts_summary.json
```

## Logs

Logs should go under:

```text
logs/
```

Recommended files:

```text
logs/execution.log
logs/validation.log
```

Logs should contain enough information for planner audit, but they should not contain credentials, private paths outside the workspace, or excessive raw output.

## Source And Scratch Outputs

If the executor creates code prototypes, put them under:

```text
work/
```

Only reference source artifacts in the final output if they are needed to reproduce the result.

Do not present scratch code as final coursework code. It is experimental evidence for planner review.

## Artifact Roles

Use one of these roles where possible:

- `primary_result`: required for planner decision-making.
- `diagnostic`: useful for checking quality, convergence, error, or plausibility.
- `audit`: supports reproducibility or traceability.
- `supporting`: helpful but not central.
- `debug`: produced during failed or partial attempts.

## Artifact Manifest Shape

`artifacts.json` should use this MVP shape:

```json
{
  "request_id": "exec_001",
  "artifacts": [
    {
      "artifact_id": "results_main",
      "path": "results.json",
      "kind": "results",
      "format": "json",
      "role": "primary_result",
      "description": "Main result metrics for the run."
    },
    {
      "artifact_id": "fig_attempt_01_loss_curve",
      "path": "figures/attempt_01_loss_curve.png",
      "kind": "figure",
      "format": "png",
      "role": "diagnostic",
      "description": "Loss curve for attempt 01."
    }
  ]
}
```

## What Goes In Summary Versus Artifacts

The executor response `summary` should stay short. It should not contain raw tables, base64 images, long logs, or detailed experiment dumps.

Put detailed material in artifacts:

- metrics and parameters in `results.json`;
- pass/fail checks in `tests.json`;
- plots in `figures/`;
- tables in `tables/`;
- command and validation notes in `logs/`;
- concise interpretation boundaries in `notes.md`.

The executor response should only reference these files.
