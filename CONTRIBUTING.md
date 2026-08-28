# Contributing to OmicsFusion

Thank you for considering a contribution.

## Development setup

```bash
git clone <this-repo> && cd OmicsFusion
python -m venv .venv && source .venv/bin/activate
pip install -e ".[gui,dev]"
pytest
```

## Adding a new analysis module

OmicsFusion is built as independent, self-contained modules under
`src/omicsfusion/<module>/` (spec section 2). A new module should:

1. Have clearly defined inputs and outputs (prefer a `Dataset` in, a typed result dataclass out).
2. Validate its inputs and raise a clear `ValueError` on invalid/insufficient data rather than silently producing a degenerate result.
3. Log key decisions via `omicsfusion.core.logging_config.get_logger(__name__)`.
4. Document, in its module docstring: what the method does, when it should be used, its assumptions, and its limitations (see any existing module, e.g. `omicsfusion/normalization/normalize.py`, for the expected style).
5. Come with tests in `tests/` covering the happy path, at least one invalid-input path, and any documented edge case.
6. If it wraps an R method, add the R script under `R/<category>/` and invoke it via `omicsfusion.core.r_bridge.run_r_script`, never via ad-hoc `subprocess` calls elsewhere.

## Code style

```bash
ruff check src tests
black --check src tests
mypy src
```

- Type hints on public function signatures.
- No hard-coded external database content (see spec section 17/§35) — annotation/pathway modules must accept user-supplied data files, not embed a copy of GO/KEGG/HMDB/etc.
- Avoid introducing a Python dependency when the R/Bioconductor ecosystem already has the standard tool for a task (spec section 3) — add an R bridge script instead.

## Tests

```bash
pytest                 # full suite
pytest tests/test_x.py -v
pytest --cov=omicsfusion
```

Tests must not require network access or a real (large) biological
dataset — use small synthetic fixtures (see `tests/conftest.py`).

## Pull requests

- Keep PRs focused on one module/fix.
- Update the relevant `docs/*.md` file when behavior changes.
- Add a `CHANGELOG.md` entry under "Unreleased".

## Reporting bugs / requesting features

Open a GitHub issue with a minimal reproducible example where possible.
