# Transcriptomics (RNA-seq)

## Expected input

Raw (or lightly filtered) gene-level count matrix: genes as rows, samples
as columns, non-negative integers. Do not pre-normalize before loading —
normalization is a configured pipeline step (`analysis.normalization.transcriptomics`).

## QC (`omicsfusion qc`)

- Library size per sample, flagged if CV > 100% across samples (a sign library-size correction is needed)
- PCA on the (transformed) matrix, with outlier flagging at >3 SD from the centroid on PC1/PC2
- Sample-sample Spearman correlation
- Per-feature coefficient of variation

## Normalization

| Method | When to use | Limitation |
|---|---|---|
| `vst` (default) | General-purpose variance stabilisation for count data | The Python implementation is an *approximation* (median-of-ratios size factors + log2); for the exact DESeq2 VST, use the R bridge |
| `log2` | Simple fold-change-oriented scaling | Does not correct for library size on its own — combine with a size-factor step first if library sizes vary a lot |
| `tmm` | Between-sample scaling robust to a few very highly expressed genes | Simplified single-factor approximation of edgeR's TMM; use R edgeR for the full algorithm |

## Differential expression

The pure-Python path (`omicsfusion.statistics.differential`) runs a
Welch's t-test or Mann-Whitney U per gene on the *normalized* matrix — a
defensible general-purpose default, but **not** a substitute for a proper
count-based model when statistical power matters. For rigorous RNA-seq
differential expression, use raw counts with the R bridge:

```bash
Rscript R/differential/deseq2_differential.R \
    --counts examples/demo/transcriptomics.csv \
    --metadata examples/demo/metadata.csv \
    --condition condition --reference control --group treated \
    --output differential_deseq2.csv
```

DESeq2/edgeR model the mean-variance relationship of count data directly
and are the standard, peer-reviewed choice; they require R + Bioconductor
(see `docs/installation.md`).

## Assumptions and limitations

- The framework assumes one condition column with two levels per comparison; multi-factor designs (e.g. batch + condition + interaction) require the R bridge's `~batch + condition` DESeq2 design directly.
- Small group sizes (<4 per group) make count-based dispersion estimation unreliable regardless of tool — OmicsFusion's differential module requires ≥2 per group but will warn/refuse below common practical minimums.
