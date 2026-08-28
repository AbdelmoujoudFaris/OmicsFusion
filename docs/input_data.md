# Input data

## Supported file formats

CSV, TSV, TXT (tab-delimited), XLSX, Parquet, HDF5 (`.h5`), AnnData (`.h5ad`,
requires `pip install anndata`). See `omicsfusion.io.loaders.load_table`.

## Expected shape

Omics matrices should have **features as rows and samples as columns**,
with a header row of sample IDs and a first column of feature IDs:

```text
gene_id | sample_01 | sample_02 | sample_03
TP53    | 125       | 230       | 98
EGFR    | 512       | 410       | 720
```

If a file is samples-as-rows instead, `detect_matrix_orientation` guesses
the orientation from the matrix shape (features almost always outnumber
samples) and `build_dataset` transposes automatically — this is logged, so
check the log if a load looks wrong.

## Detection

`omicsfusion.io.loaders.sniff_modality` guesses the omics type from the
filename and column names (keywords like `rna`, `protein`, `metabol`,
`otu`/`taxa`, `methyl`, ...). It returns `None` when nothing matches — the
config's `inputs:` mapping is always the authoritative source of the
modality (you assign a file to `transcriptomics:`, `proteomics:`, etc.
explicitly), so a failed guess never silently mislabels data.

## Numeric validation

`build_dataset` coerces every value to numeric after orientation detection
and raises if more than 1% of values fail to parse — this almost always
means the file's header/orientation was misread (e.g. an extra label
column), not "a few bad cells to silently drop".

## Duplicate/empty checks

`Dataset` rejects matrices with duplicate sample columns, duplicate feature
rows, or that are empty, at construction time (`omicsfusion.core.dataset`).

## Metadata

See `docs/metadata.md`.
