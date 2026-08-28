# Metadata

## Expected shape

One row per sample, with a `sample_id` column matching the column names
used in every omics matrix:

```text
sample_id | condition | batch | tissue | timepoint
S01       | control   | B1    | liver  | T0
S02       | control   | B1    | liver  | T1
S03       | treated   | B2    | liver  | T0
```

If there is no `sample_id` column, the first column is used and a warning
is logged (`omicsfusion.metadata.validator.validate_metadata`).

## Consistency checks

`omicsfusion validate --config project.yaml` (or `validate_metadata()`
directly) checks:

| Check | Severity |
|---|---|
| Duplicate sample IDs in metadata | error |
| Missing/blank sample IDs | error |
| Samples present in an omics file but absent from metadata | error |
| Samples present in metadata but absent from an omics file | warning |
| Missing values per column | reported |
| A categorical column's levels not present in every batch (confounding) | warning |

A run (`omicsfusion run`) refuses to proceed while any **error** remains —
mismatched samples between metadata and omics data almost always indicate
a labelling mistake, and running the pipeline anyway would silently drop
or misalign samples.

## Variable types

Columns are classified automatically
(`omicsfusion.io.loaders.detect_id_columns`):

- **identifier-like**: every value unique — treated as a sample/patient ID, not an analysis variable
- **categorical**: repeated non-numeric values — usable as a differential-analysis condition or an ML classification target
- **numeric**: usable as an ML regression target or a continuous covariate

## Using metadata downstream

- `analysis.differential.condition` / `.reference` / `.group` in `project.yaml` must name a categorical metadata column and two of its levels.
- `analysis.machine_learning.target` must name any metadata column (categorical for `task: classification`, numeric for `task: regression`).
