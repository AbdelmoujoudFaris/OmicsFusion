# Proteomics

## Expected input

Protein (or peptide, pre-rolled up to protein level) intensity matrix:
proteins as rows, samples as columns. Missingness is common and
informative (often not-missing-at-random, e.g. below detection limit) —
OmicsFusion reports missingness per sample/feature in QC but does not
impute it silently; imputation is a deliberate, documented choice you make
before differential analysis if needed.

## QC

Same generic engine as transcriptomics (`omicsfusion.qc.common.run_qc`):
missingness, PCA, sample correlation, per-feature CV. Proteomics data
typically shows higher missingness and CV than RNA-seq — treat the
CV/missingness numbers as diagnostic, not universal thresholds.

## Normalization

`log2` (default) is standard for intensity data. `median` normalization
(dividing each sample by its median intensity, scaled to a common
reference) is a robust alternative when a large, stable majority of
proteins are expected to be unchanged between conditions.

## Differential analysis

The pure-Python t-test/Mann-Whitney path operates directly on
log-transformed intensities. For a linear-model approach with proper
moderated variance shrinkage (recommended for typical proteomics sample
sizes), use the R bridge:

```bash
Rscript R/differential/limma_differential.R \
    --matrix normalized_proteomics.csv --metadata metadata.csv \
    --condition condition --reference control --group treated \
    --output differential_limma.csv
```

## Limitations

- Peptide-to-protein rollup (choosing a summarisation rule for multiple peptides per protein) is assumed to have already happened upstream; OmicsFusion works at whatever feature granularity the input matrix uses.
- Batch effects are flagged in QC (library-size CV, PCA structure) but not automatically corrected — apply an explicit batch-correction step (e.g. ComBat via the R bridge) if QC shows batch-driven clustering.
