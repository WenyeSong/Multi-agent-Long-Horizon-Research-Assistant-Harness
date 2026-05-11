# Executor Workspace Contract

The executor must operate inside a planner-assigned workspace. The workspace boundary is part of the security and reproducibility model.

## Required Workspace Fields

Each executor request must provide:

- `workspace.root`: logical root for the execution run;
- `workspace.read_paths`: explicit read-only input locations;
- `workspace.write_path`: single writable output directory.

## Recommended Layout

```text
role/executor/workspaces/
  <request_id>/
    inputs/          # optional copied or linked read-only inputs
    work/            # scratch code and intermediate files
    figures/         # generated plots
    tables/          # generated CSV or JSON tables
    logs/            # execution and validation logs
    results.json
    tests.json
    environment.json
    artifacts.json
    notes.md
```

For the MVP, the planner should create the run directory before invoking the executor.

## Read Contract

The executor may read only:

- paths explicitly listed in `workspace.read_paths`;
- artifacts explicitly listed in `inputs`;
- files under its own `workspace.write_path`.

Planner-provided inputs are read-only. If the executor needs to transform an input, it must write a derived copy under `workspace.write_path`.

## Write Contract

The executor may write only under `workspace.write_path`.

Required output filenames should be stable so the planner can collect them:

- `results.json`;
- `tests.json`;
- `environment.json`;
- `artifacts.json`;
- `notes.md`;
- `figures/*`;
- `tables/*`;
- `logs/*`.

The executor must not write to:

- repository root;
- planner workspace;
- literature reviewer workspace;
- reviewer workspace;
- Report generator workspace;
- system temp directories unless the sandbox maps them into the execution workspace;
- credential or configuration directories.

## Artifact References

The executor response should return artifact references, not embedded large payloads.

Each artifact reference should include:

- artifact id;
- path;
- kind;
- short description.

## Cleanup

The executor should preserve enough intermediate material for auditability. It may delete temporary files only if they are not needed to reproduce or understand the final result.

## Reproducibility

The executor should record:

- relevant random seeds;
- Python version;
- package versions;
- operating system;
- key command summaries;
- input artifact ids;
- generated artifact ids.

## Artifact Manifest

The executor should write `artifacts.json` when it produces more than the three core JSON files. The manifest should list figures, tables, logs, source files, and notes with stable ids, paths, formats, roles, and short descriptions.
