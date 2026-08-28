# bin/

The primary entry point is the `omicsfusion` console script installed by
`pip install -e .` (see `pyproject.toml`'s `[project.scripts]`) — there is
no separate launcher script to run here.

This directory is reserved for future standalone utility scripts that
don't belong inside the `omicsfusion` package itself (e.g. one-off data
conversion helpers). The Nextflow-specific helper script lives at
`workflows/bin/make_project_config.py` instead, since Nextflow only
auto-adds a pipeline-local `bin/` to `PATH`.
