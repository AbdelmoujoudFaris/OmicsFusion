# Metabolomics

## Expected input

Metabolite abundance matrix: metabolites as rows, samples as columns.
Feature IDs are whatever the acquisition/annotation pipeline produced
(compound names, HMDB/KEGG IDs, or feature-detection IDs like m/z_RT) —
see `docs/integration.md` and `omicsfusion.annotation` for mapping feature
IDs to database identifiers.

## QC

Same generic engine as other modalities: missingness, PCA, sample
correlation, CV. Metabolomics runs are often organised in batches
(acquisition order/plate) — check the `batch` column against PCA structure
via the Metadata page/`validate_metadata`'s batch-imbalance warning.

## Normalization

`zscore` (default) assumes the data has already been made roughly
symmetric (e.g. via a prior log transform during peak processing). If your
abundances are still strongly right-skewed, apply `log` or `log2` first —
`zscore` on raw skewed abundances will not fix the skew, only rescale it.

## Differential analysis

The pure-Python t-test/Mann-Whitney path is generally appropriate for
metabolomics after normalization; there is no dedicated R script bundled
for metabolomics-specific differential testing in this MVP (limma via the
R bridge also works on log-scale metabolomics data — see `docs/proteomics.md`
for the invocation, it is modality-agnostic).

## Annotation

Point `omicsfusion.annotation.LocalMappingClient` at a two-column
(or wider) mapping table you export from HMDB/KEGG/PubChem/ChEBI (feature
ID → name/pathway/formula/...) — no database content is bundled with
OmicsFusion; see `docs/integration.md`'s "Feature annotation" section.

## Limitations

- No built-in metabolite identification/annotation database — bring your own mapping table.
- Batch effect correction is not automatic; inspect QC PCA against `batch` and apply an explicit correction step if needed.
