# Quick start

This walks through the bundled demo dataset end-to-end.

## 1. Generate the demo data

```bash
python examples/demo/generate_demo_data.py
```

Writes a synthetic 40-sample case/control (`treated` vs `control`) study to
`examples/demo/`: `transcriptomics.csv` (300 genes), `proteomics.csv` (150
proteins), `metabolomics.csv` (80 metabolites), and `metadata.csv`. The
first 20 features of each omics layer carry a real (simulated) treatment
effect, so downstream results are non-trivial. See `examples/demo/README.md`.

## 2. Inspect the config

`examples/demo/config.yaml` declares the inputs, normalization method per
modality, the `treated` vs `control` differential comparison, two
integration methods, and a random-forest/elastic-net ML classifier
predicting `condition`. This one file drives everything below — see
`docs/input_data.md` for the full schema.

## 3. Validate

```bash
omicsfusion validate --config examples/demo/config.yaml
```

Checks that every sample in the omics files has matching metadata (and
vice versa), flags duplicate IDs, missing values, and batch/condition
confounding, before any analysis runs.

## 4. Run the full pipeline

```bash
omicsfusion run --config examples/demo/config.yaml
```

Produces, in `examples/demo/results/`:

- `qc_<modality>.json` equivalent metrics embedded in `report.html`'s QC sections
- `differential_<modality>.csv` — per-feature log2FC / p-value / adjusted p-value
- `correlation_<modality_a>_<modality_b>.csv` — cross-omics feature correlations
- `integration_early_concat.csv`, `integration_pca_consensus.csv`
- `report.html` — the full interactive report
- `analysis_config.yaml`, `software_versions.txt`, `omicsfusion.log`, `run_summary.json`

## 5. Open the report

Open `examples/demo/results/report.html` in a browser. It contains the
project summary, input dataset shapes, metadata validation outcome, QC PCA
plots, normalization choices (with rationale), volcano plots and top-hit
tables per modality, cross-omics correlation heatmaps, the combined
integration matrix, ML model metrics and feature importances, and a
reproducibility section with exact software versions.

## 6. Try the GUI instead

```bash
streamlit run app/streamlit/Home.py
```

Upload the same three CSVs and `metadata.csv` from `examples/demo/`,
configure the same choices interactively, and run — the GUI writes an
equivalent `project.yaml` you can download and rerun from the CLI.

## Next steps

- Point `inputs:` in a copy of `config.yaml` at your own data (`omicsfusion init my_project` scaffolds one).
- Read `docs/input_data.md` and `docs/metadata.md` for your data's expected shape.
- See `docs/workflows.md` to run the same analysis through Nextflow.
