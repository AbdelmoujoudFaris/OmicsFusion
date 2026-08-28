"""Format-agnostic table loading and lightweight dataset-type detection.

Researchers hand OmicsFusion tables in whatever shape their upstream
pipeline produced them (CSV/TSV/TXT/XLSX/Parquet, features-as-rows or
samples-as-rows). This module normalises that into a single loading path
and provides *heuristics* — not guarantees — for the modality and the
feature/sample orientation, which the caller should surface to the user for
confirmation rather than trust blindly.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from omicsfusion.core.logging_config import get_logger

logger = get_logger("io.loaders")

SUPPORTED_EXTENSIONS = {
    ".csv",
    ".tsv",
    ".txt",
    ".xlsx",
    ".xls",
    ".parquet",
    ".h5",
    ".h5ad",
}

# Keyword hints used by sniff_modality, checked against filename + column names.
_MODALITY_KEYWORDS: dict[str, list[str]] = {
    "transcriptomics": ["rna", "rnaseq", "gene", "transcript", "counts", "expr"],
    "proteomics": ["protein", "proteo", "peptide", "uniprot"],
    "metabolomics": ["metabol", "hmdb", "lipid_", "compound"],
    "lipidomics": ["lipid", "lipidom"],
    "metagenomics": ["metagenom", "mag", "contig"],
    "microbiome": ["otu", "asv", "taxa", "taxon", "microbiome", "abundance"],
    "epigenomics": ["methyl", "cpg", "atac", "chip", "epigen"],
    "clinical": ["clinical", "metadata", "phenotype", "sample_info"],
}


def load_table(path: str | Path, sheet_name: str | int | None = 0) -> pd.DataFrame:
    """Load a tabular file into a DataFrame, dispatching on extension.

    The first column is used as the index only when it is non-numeric and
    unique (a typical feature/sample identifier column); otherwise a
    default RangeIndex is kept and the caller is responsible for orienting
    the table.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{suffix}' for {path.name}. "
            f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in (".tsv", ".txt"):
        df = pd.read_csv(path, sep="\t")
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path, sheet_name=sheet_name)
    elif suffix == ".parquet":
        df = pd.read_parquet(path)
    elif suffix in (".h5", ".h5ad"):
        df = _load_hdf(path)
    else:  # pragma: no cover - guarded above
        raise ValueError(f"Unhandled extension: {suffix}")

    first_col = df.columns[0]
    if not pd.api.types.is_numeric_dtype(df[first_col]) and df[first_col].is_unique:
        df = df.set_index(first_col)

    logger.info("Loaded %s: %d rows x %d columns", path.name, df.shape[0], df.shape[1])
    return df


def _load_hdf(path: Path) -> pd.DataFrame:
    if path.suffix == ".h5ad":
        try:
            import anndata as ad
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "Reading .h5ad files requires the optional 'anndata' package."
            ) from exc
        adata = ad.read_h5ad(path)
        return pd.DataFrame(adata.X.T, index=adata.var_names, columns=adata.obs_names)
    return pd.read_hdf(path)


def detect_matrix_orientation(df: pd.DataFrame) -> str:
    """Guess whether rows or columns represent features.

    Heuristic: omics feature counts (genes, proteins, metabolites, taxa)
    typically far outnumber the sample count. Returns ``"features_as_rows"``
    or ``"features_as_columns"``.
    """
    n_rows, n_cols = df.shape
    if n_rows >= n_cols:
        return "features_as_rows"
    return "features_as_columns"


def sniff_modality(path: str | Path, df: pd.DataFrame | None = None) -> str | None:
    """Best-effort guess of the omics modality from filename and column names.

    Returns ``None`` when no keyword matches, signalling that the caller
    (CLI/GUI) must ask the user to specify the modality explicitly rather
    than silently assume one.
    """
    path = Path(path)
    haystack = path.stem.lower()
    if df is not None:
        haystack += " " + " ".join(str(c).lower() for c in df.columns[:20])

    scores = {
        modality: sum(1 for kw in keywords if kw in haystack)
        for modality, keywords in _MODALITY_KEYWORDS.items()
    }
    best_modality = max(scores, key=lambda k: scores[k])
    if scores[best_modality] == 0:
        return None
    return best_modality


def detect_id_columns(df: pd.DataFrame) -> dict[str, list[str]]:
    """Classify metadata columns as identifier-like, categorical, or numeric.

    Used by the metadata validator to flag likely sample/patient ID columns
    versus experimental grouping variables, without hard-coding column names.
    """
    id_like: list[str] = []
    categorical: list[str] = []
    numeric: list[str] = []

    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            numeric.append(col)
            continue
        n_unique = series.nunique(dropna=True)
        if n_unique == len(series) and n_unique > 1:
            id_like.append(col)
        else:
            categorical.append(col)

    return {"identifier": id_like, "categorical": categorical, "numeric": numeric}
