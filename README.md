# OmicsFusion

**Multi-omics analysis from raw tables to integrated biological insight.**

OmicsFusion is a modular, reproducible platform for analysing and
integrating transcriptomics, proteomics, metabolomics, microbiome, and
clinical data. It combines a Python core (pandas/scikit-learn/statsmodels)
with an R bridge for methods where the Bioconductor ecosystem is stronger
(DESeq2, limma, MOFA2, mixOmics/DIABLO, fgsea), orchestrated end-to-end by
Nextflow, driven by a single YAML config from either the CLI or the
Streamlit GUI.

```text
Raw Data → Detection → Metadata Validation → QC → Normalization →
Per-Omics Analysis → Cross-Omics Integration → ML → Pathways →
Visualization → Reproducible HTML Report
```

## Architecture

```text
        User / Researcher
               │
        ┌──────┴──────┐
        │ CLI  │  GUI │  (Streamlit)         every action here
        └──────┬──────┘                       writes/edits ↓
               ▼
         project.yaml   ← single source of truth for a run
               │
               ▼
       Nextflow workflow engine  (workflows/main.nf)
               │
   ┌───────────┼────────────┐
   ▼           ▼            ▼
 Python     R bridge     ML / DL
 modules    (R/*.R via   modules
 (src/)     Rscript)     (sklearn/
                          torch)
   └───────────┬────────────┘
               ▼
     Multi-omics integration layer
   (early / PCA-consensus / MOFA2 / DIABLO)
               │
   ┌───────────┼────────────┐
   ▼           ▼            ▼
Pathways    Networks   Machine Learning
   └───────────┬────────────┘
               ▼
     Interactive results + report.html
```

Every module (`src/omicsfusion/<module>/`) has defined inputs/outputs,
config, validation, logging, and records its own provenance on the
dataset it processes — see `docs/` for the module-by-module reference.

## Installation

```bash
git clone <this-repo> && cd OmicsFusion
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[gui,dev]"
```

Or with conda (also installs the R/Bioconductor stack used by the R bridge):

```bash
conda env create -f environment.yml
conda activate omicsfusion
pip install -e .
```

See `docs/installation.md` for Docker and Nextflow setup.

## Quick start

```bash
# Generate the bundled demo dataset (40-sample synthetic case/control study)
python examples/demo/generate_demo_data.py

# Validate metadata against the omics inputs
omicsfusion validate --config examples/demo/config.yaml

# Run the full pipeline: QC → normalization → differential → integration → ML → report
omicsfusion run --config examples/demo/config.yaml

# Open the report
open examples/demo/results/report.html   # or start it, on Windows
```

See `docs/quickstart.md` for a walkthrough of the results.

## CLI usage

```text
omicsfusion init <dir>                 Scaffold a new project.yaml
omicsfusion validate --config c.yaml   Metadata/omics consistency check
omicsfusion qc --config c.yaml         Per-modality QC metrics
omicsfusion normalize --config c.yaml  Modality-aware normalization
omicsfusion differential --config c.yaml
omicsfusion integrate --config c.yaml
omicsfusion ml --config c.yaml
omicsfusion report --config c.yaml     Full pipeline + HTML report
omicsfusion run --config c.yaml        Full pipeline (alias-equivalent to report)
```

## GUI usage

```bash
pip install -e ".[gui]"
streamlit run app/streamlit/Home.py
```

Walk through Upload Data → Metadata → QC & Normalization → Differential
Analysis → Integration & ML → Run & Report. Every GUI choice is written
into a `project.yaml` you can download and rerun from the CLI — the GUI
never analyses data through a path the CLI can't reproduce.

## Configuration (`project.yaml`)

```yaml
project:
  name: cancer_multiomics
  organism: human

inputs:
  transcriptomics: data/rna.csv
  proteomics: data/proteomics.csv
  metabolomics: data/metabolomics.csv
  metadata: data/metadata.csv

analysis:
  qc: true
  normalization:
    transcriptomics: vst
    proteomics: log2
    metabolomics: zscore
  differential:
    condition: treatment
    reference: control
  integration:
    methods: [early_concat, pca_consensus]
  machine_learning:
    enabled: true
    target: treatment
    models: [random_forest, elastic_net]

outdir: results
```

Full schema: `docs/input_data.md`, `docs/metadata.md`.

## Supported omics & analysis modules

| Layer | Module | Status |
|---|---|---|
| Transcriptomics, proteomics, metabolomics, microbiome, metagenomics, epigenomics, lipidomics, clinical | `io`, `validation`, `metadata` | Working |
| QC (PCA, library size, correlation, CV, outliers) | `qc` | Working |
| Normalization (log/log2/log10/zscore/minmax/quantile/median/VST/CLR/TMM) | `normalization` | Working |
| Differential analysis (t-test/Mann-Whitney + FDR/Bonferroni; DESeq2/limma via R bridge) | `statistics`, `R/differential` | Working |
| Cross-omics correlation | `statistics.correlation` | Working |
| Integration: early concat, PCA consensus (pure Python); MOFA2, DIABLO (R bridge) | `integration`, `R/integration` | Working |
| Machine learning (RF, elastic net, logistic regression, SVM, optional XGBoost) | `machine_learning` | Working |
| Pathway ORA (hypergeometric, user-supplied `.gmt`); GSEA/fgsea via R bridge | `pathways`, `R/pathways` | Working |
| Networks (correlation graphs, GraphML/GEXF/CSV export) | `networks` | Working |
| Feature annotation (local mapping tables + cache; bring-your-own HMDB/KEGG/Ensembl export) | `annotation` | Working |
| Reporting (self-contained interactive HTML) | `reporting` | Working |
| Deep learning (multi-omics autoencoder) | — | Roadmap, optional (`pip install -e ".[deep]"`) |

## Workflow (Nextflow)

```bash
cd workflows
nextflow run main.nf \
    --rna ../examples/demo/transcriptomics.csv \
    --proteomics ../examples/demo/proteomics.csv \
    --metabolomics ../examples/demo/metabolomics.csv \
    --metadata ../examples/demo/metadata.csv \
    --differential-condition condition --differential-reference control \
    --outdir ../examples/demo/results_nf \
    -profile docker
```

See `docs/workflows.md` for the module structure and current limitations
(intermediate stages currently recompute from raw inputs rather than
passing intermediate artifacts between Nextflow processes — see the
roadmap).

## Reproducibility

Every `omicsfusion run` writes, alongside the results:

- `analysis_config.yaml` — the exact resolved config used
- `software_versions.txt` — Python/R/Nextflow/package versions actually installed
- `omicsfusion.log` — full run log
- `run_summary.json` — machine-readable stage summary

See `docs/reproducibility.md`.

## Docker

```bash
docker build -t omicsfusion:latest .
docker run --rm -v "$PWD":/data omicsfusion:latest run --config /data/project.yaml
```

## Testing

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

## Contributing

See `CONTRIBUTING.md`. Please read `CODE_OF_CONDUCT.md` before opening an issue or PR.

## Citation

See `CITATION.cff`.

## License

MIT — see `LICENSE`.

## Roadmap

- Fine-grained Nextflow caching: split `core.pipeline.run_pipeline` into per-stage processes with intermediate file contracts (see `docs/workflows.md`).
- Microbiome alpha/beta diversity and PERMANOVA (scikit-bio / R vegan) — see `docs/microbiome.md`.
- GSEA/ORA results wired directly into the HTML report (currently available as a standalone module, `omicsfusion.pathways`).
- Optional multi-omics autoencoder/VAE/GNN module (`pip install -e ".[deep]"` scaffold exists; model not yet implemented).
- Live annotation API clients (HMDB/KEGG/Ensembl REST) on top of the existing `AnnotationClient` interface, alongside the local-mapping-table client.
- Late-integration consensus-signal automation across independent per-modality differential results.

## References

See `REFERENCES.md` for the literature and prior-art this design draws on
(nf-core, scikit-bio, HMDB, and others).
