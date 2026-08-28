# Multi-omics integration

OmicsFusion implements three tiers of integration (spec section 12).

## Early integration (`early_concat`)

`omicsfusion.integration.methods.early_integration`: scale each modality
independently (z-score per feature) then concatenate on shared samples
into one wide matrix. Simple and interpretable, feeds directly into ML.
**Limitation**: treats every feature as equally weighted regardless of
modality dimensionality — a 10,000-feature transcriptome will dominate a
50-feature metabolome in downstream distance-based methods (e.g. k-NN,
some clustering) unless you account for that explicitly.

## Intermediate integration

### PCA consensus (`pca_consensus`, pure Python)

`omicsfusion.integration.methods.pca_consensus_integration`: reduce each
modality to its own top principal components first, then concatenate the
scores. This bounds each modality's contribution to a fixed number of
dimensions regardless of its original feature count — a lightweight,
dependency-free stand-in for a joint factor model.

### MOFA2 (R bridge, recommended for rigorous factor analysis)

Fits one probabilistic latent-factor model jointly across all views, with
proper per-view variance-explained decomposition (spec section 13):

```bash
Rscript R/integration/mofa2_integration.R \
    --views rna=normalized_rna.csv,protein=normalized_protein.csv \
    --n-factors 10 --outdir mofa_results/
```

Outputs `sample_factors.csv`, `weights_<view>.csv` per view, and
`variance_explained.csv`.

### DIABLO / mixOmics (R bridge, supervised)

Finds molecular signatures across views that jointly discriminate a known
outcome (spec section 14) — use this instead of MOFA2 when you have a
labelled outcome and want a classifier-style signature, not exploratory
factors:

```bash
Rscript R/integration/diablo_integration.R \
    --views rna=normalized_rna.csv,protein=normalized_protein.csv \
    --metadata metadata.csv --outcome condition --n-features 10 \
    --outdir diablo_results/
```

## Late integration

Run each modality's differential analysis independently
(`omicsfusion differential`), then compare result tables directly (shared
significant pathways, directionally consistent features) — this MVP does
not yet automate a "consensus signal" step across independent per-modality
results; combine the CSVs manually or see the roadmap.

## Cross-omics correlation & networks

`omicsfusion.statistics.correlation.cross_omics_correlation` computes
all-pairs correlation between the most variable features of two datasets
(Pearson or Spearman, FDR-corrected). Feed the result into
`omicsfusion.networks.build_correlation_network` to get a NetworkX graph
of statistically supported cross-omics relationships, exportable to
GraphML/GEXF/CSV.

## Feature annotation

No external database content ships with OmicsFusion. Point
`omicsfusion.annotation.LocalMappingClient` at an ID-mapping table you
already have (or exported from HMDB/KEGG/Ensembl/UniProt) to annotate
features by ID; lookups are cached (`AnnotationCache`) to avoid recompute
across runs.

## Choosing a method

| Question | Method |
|---|---|
| "I just want everything in one matrix for ML" | `early_concat` |
| "I want per-modality dimensionality reduction before combining, no R needed" | `pca_consensus` |
| "I want a rigorous joint variance decomposition across views" | MOFA2 (R bridge) |
| "I have a known outcome and want a joint discriminative signature" | DIABLO (R bridge) |
