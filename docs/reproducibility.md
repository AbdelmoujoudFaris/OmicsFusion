# Reproducibility

Every `omicsfusion run` (CLI, GUI, or Nextflow) writes, into `outdir`:

| File | Contents |
|---|---|
| `analysis_config.yaml` | The exact resolved `ProjectConfig`, including every default that wasn't explicitly set |
| `software_versions.txt` | Python, pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib, plotly, networkx, pydantic, R, and Nextflow versions **actually installed**, not just the pinned requirement ranges (`omicsfusion.core.versions.collect_versions`) |
| `omicsfusion.log` | Full run log (also echoed to the console) |
| `run_summary.json` | Machine-readable per-stage summary (sample counts, significant feature counts, ML metrics, ...) |
| `report.html` | The full interactive report, including a "Reproducibility" section with the same version table |

## Determinism

- `random_seed` in `project.yaml` (default 42) is threaded through ML train/test splits and cross-validation folds (`analysis.machine_learning.random_state`).
- The demo dataset generator (`examples/demo/generate_demo_data.py`) uses a fixed `numpy.random.default_rng(42)` seed, so it is byte-for-byte reproducible.
- Model training (random forest, elastic net, ...) uses the configured `random_state` for every estimator.

## What is *not* yet pinned

- R package versions are whatever your R/Bioconductor environment resolves to; `environment.yml` pins major packages but not exact Bioconductor release dates. For strict R-side reproducibility, pin a Bioconductor release version in your own environment.
- Nextflow's own execution report/timeline/trace (`pipeline_info/`) captures per-process resource usage and exact commands when run through `workflows/main.nf`, complementing (not replacing) `software_versions.txt`.

## Provenance on data objects

Every `Dataset` (`omicsfusion.core.dataset.Dataset`) accumulates a
`preprocessing` list as it moves through the pipeline (e.g.
`["loaded:features_as_rows", "normalization:vst"]`) — inspect
`dataset.to_summary()` or the "Input datasets"/"Normalization" report
sections to see exactly what happened to a given matrix before any
downstream statistic was computed from it.
