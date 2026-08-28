# Microbiome / metagenomics

## Expected input

A taxon (OTU/ASV/species) abundance or count matrix: taxa as rows, samples
as columns. Microbiome data is **compositional** (each sample sums to an
arbitrary total, so absolute values aren't directly comparable across
samples) — this drives the recommended normalization and correlation
choices below.

## Normalization

`clr` (centered log-ratio, default for `microbiome`/`metagenomics` in
`analysis.normalization`) is the standard compositional-data transform: it
maps the simplex onto real space so that standard multivariate methods
(PCA, correlation, ML) are valid. It assumes strictly positive values —
zeros are replaced with a small pseudocount, which is a common but
imperfect solution; for a rigorous zero-replacement/compositional workflow
use R's `zCompositions` + `vegan` via a custom R bridge script.

## Diversity and QC

The current MVP's generic QC engine (missingness, PCA, sample correlation,
CV) applies, but **does not yet implement** alpha diversity (Shannon,
Simpson), beta diversity (Bray-Curtis, Jaccard, PCoA), or PERMANOVA — these
are the standard microbiome-specific QC/analysis steps from `scikit-bio`
(Python; not installed by default on Windows, see `pyproject.toml`) and R
`vegan`. This is tracked on the roadmap (`docs/reproducibility.md` /
README "Roadmap"); until then, run these directly:

```python
import skbio.diversity as diversity
alpha = diversity.alpha_diversity("shannon", counts_matrix.T.values, ids=counts_matrix.columns)
```

or via R `vegan::diversity()` / `vegan::vegdist()` / `vegan::adonis2()`.

## Differential abundance

Standard t-tests on raw relative abundance are not appropriate for
compositional data (spec-flagged pitfall: "Pearson correlation on
untransformed count data"). Apply `clr` normalization first, then the
generic differential-analysis framework (`omicsfusion differential`)
operates validly on the transformed values.

## Limitations

- No PERMANOVA/PCoA/beta-diversity module yet (roadmap).
- CLR's zero-handling (pseudocount) is a simplification; for sparse, zero-heavy count tables consider a more principled zero-replacement method before CLR.
