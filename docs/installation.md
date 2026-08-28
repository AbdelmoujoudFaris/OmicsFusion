# Installation

## Requirements

- Python 3.11+
- (Optional) R 4.3+ with Bioconductor, for the R-backed methods in `R/` (DESeq2, limma, MOFA2, mixOmics, fgsea)
- (Optional) Nextflow 23.04+ and Java 17+, to run the workflow in `workflows/`
- (Optional) Docker or Singularity/Apptainer, for containerised execution

The Python core (I/O, QC, normalization, differential analysis, correlation,
early/PCA-consensus integration, ML, pathway ORA, networks, reporting, GUI)
works standalone with no R, Nextflow, or GPU required.

## pip (Python only)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[gui,dev]"
```

Optional extras:

```bash
pip install -e ".[deep]"   # PyTorch, for the optional multi-omics autoencoder
pip install -e ".[umap]"   # umap-learn
```

## conda (Python + R)

```bash
conda env create -f environment.yml
conda activate omicsfusion
pip install -e .
```

This also installs the Bioconductor packages the R bridge (`R/`) calls via
`Rscript`: DESeq2, edgeR, limma, ComplexHeatmap, fgsea, MOFA2, mixOmics, vegan.

## Docker

```bash
docker build -t omicsfusion:latest .
docker run --rm omicsfusion:latest --help
```

The image includes the Python stack and a base R installation; see
`Dockerfile` to extend it with Bioconductor packages for the R bridge.

## Verify the install

```bash
omicsfusion --version
python examples/demo/generate_demo_data.py
omicsfusion validate --config examples/demo/config.yaml
```

## Nextflow (optional)

```bash
curl -s https://get.nextflow.io | bash
./nextflow run workflows/main.nf --help
```

See `docs/workflows.md`.
