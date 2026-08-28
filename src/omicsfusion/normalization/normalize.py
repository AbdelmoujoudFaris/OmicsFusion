"""Modality-aware normalisation (spec section 9).

Normalisation is never applied blindly: each method below documents what it
assumes about the input (e.g. CLR assumes strictly positive compositional
data; TMM assumes count data) and :func:`normalize_dataset` records the
chosen method plus a plain-language reason on the dataset's provenance
trail, so a report can show *what* was done and *why*.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from omicsfusion.core.dataset import Dataset
from omicsfusion.core.logging_config import get_logger

logger = get_logger("normalization.normalize")

METHOD_RATIONALE = {
    "zscore": "Centers and scales each feature to mean 0 / SD 1; assumes roughly symmetric, "
    "already-transformed data. Standard for metabolomics after log transform.",
    "log": "Natural-log(x + 1); stabilises variance for strictly non-negative, right-skewed data.",
    "log2": "log2(x + 1); conventional for expression/intensity fold-change interpretation.",
    "log10": "log10(x + 1); used when fold changes are reported on a base-10 scale.",
    "minmax": "Rescales each feature to [0, 1]; sensitive to outliers, use after outlier QC.",
    "quantile": "Forces each sample to share the same feature-value distribution; removes "
    "technical scale differences but also removes genuine global shifts.",
    "median": "Divides each sample by its median (or median ratio to a reference); a robust "
    "library-size correction for intensity data with a stable majority of unchanged features.",
    "vst": "Approximate variance-stabilising transform: log2(x + 1) applied to size-factor-"
    "scaled counts. For a rigorous VST, use DESeq2 in R (see R/differential/).",
    "clr": "Centered log-ratio: log(x / geometric_mean(x)) per sample. Assumes strictly "
    "positive, compositional data (e.g. microbiome relative abundance); zeros are replaced "
    "with a small pseudocount.",
    "tmm": "Approximate Trimmed Mean of M-values: a simplified single-factor version of "
    "edgeR's TMM for library-size scaling of count data. For the full algorithm, use "
    "R edgeR (see R/differential/).",
    "none": "No transformation applied.",
}


def normalize_dataset(
    dataset: Dataset, method: str, pseudocount: float = 1.0
) -> Dataset:
    """Return a new, normalised :class:`Dataset`; the input is left untouched."""
    if method not in METHOD_RATIONALE:
        raise ValueError(
            f"Unknown normalization method '{method}'. Known: {list(METHOD_RATIONALE)}"
        )

    out = dataset.copy()
    matrix = out.matrix

    if method == "none":
        pass
    elif method == "log":
        out.matrix = np.log(matrix.clip(lower=0) + pseudocount)
    elif method == "log2":
        out.matrix = np.log2(matrix.clip(lower=0) + pseudocount)
    elif method == "log10":
        out.matrix = np.log10(matrix.clip(lower=0) + pseudocount)
    elif method == "zscore":
        out.matrix = matrix.sub(matrix.mean(axis=1), axis=0).div(
            matrix.std(axis=1).replace(0, np.nan), axis=0
        )
    elif method == "minmax":
        rmin, rmax = matrix.min(axis=1), matrix.max(axis=1)
        span = (rmax - rmin).replace(0, np.nan)
        out.matrix = matrix.sub(rmin, axis=0).div(span, axis=0)
    elif method == "quantile":
        out.matrix = _quantile_normalize(matrix)
    elif method == "median":
        sample_medians = matrix.median(axis=0)
        reference = sample_medians.median()
        out.matrix = matrix.div(sample_medians.replace(0, np.nan), axis=1) * reference
    elif method == "vst":
        size_factors = _median_of_ratios_size_factors(matrix)
        scaled = matrix.div(size_factors, axis=1)
        out.matrix = np.log2(scaled.clip(lower=0) + pseudocount)
    elif method == "clr":
        out.matrix = _clr(
            matrix, pseudocount=pseudocount * 1e-6 if pseudocount >= 1 else pseudocount
        )
    elif method == "tmm":
        size_factors = _simplified_tmm_factors(matrix)
        out.matrix = matrix.div(size_factors, axis=1)

    out.record_step(f"normalization:{method}")
    out.info.normalization = method
    logger.info(
        "Normalized dataset '%s' with method=%s (%s)",
        out.info.id,
        method,
        METHOD_RATIONALE[method],
    )
    return out


def explain(method: str) -> str:
    """Human-readable rationale for a normalisation method, for reports/UI."""
    return METHOD_RATIONALE.get(method, "Unknown method.")


def _quantile_normalize(matrix: pd.DataFrame) -> pd.DataFrame:
    # Standard quantile normalisation: sort each column, average across columns
    # to get a reference distribution, then reassign values by each column's rank.
    sorted_df = pd.DataFrame(
        np.sort(matrix.values, axis=0), index=matrix.index, columns=matrix.columns
    )
    mean_sorted = sorted_df.mean(axis=1).values
    ranks = matrix.rank(method="min").astype(int) - 1
    ranks = ranks.clip(lower=0, upper=len(mean_sorted) - 1)
    out = ranks.apply(lambda col: mean_sorted[col.values])
    out.index = matrix.index
    out.columns = matrix.columns
    return out


def _median_of_ratios_size_factors(matrix: pd.DataFrame) -> pd.Series:
    log_matrix = np.log(matrix.replace(0, np.nan))
    log_geo_mean = log_matrix.mean(axis=1)
    valid = log_geo_mean.replace([np.inf, -np.inf], np.nan).notna()
    ratios = log_matrix.loc[valid].sub(log_geo_mean.loc[valid], axis=0)
    size_factors = np.exp(ratios.median(axis=0, skipna=True))
    return size_factors.replace(0, np.nan).fillna(1.0)


def _simplified_tmm_factors(matrix: pd.DataFrame) -> pd.Series:
    lib_sizes = matrix.sum(axis=0)
    reference = lib_sizes.median()
    cpm = matrix.div(lib_sizes, axis=1) * 1e6
    log_ref = np.log2(cpm.mean(axis=1).replace(0, np.nan))
    log_ratios = np.log2(cpm.replace(0, np.nan)).sub(log_ref, axis=0)
    trimmed_mean = log_ratios.apply(lambda col: _trimmed_mean(col.dropna(), 0.3))
    factors = 2**trimmed_mean
    return (factors * lib_sizes / reference).replace(0, np.nan).fillna(1.0)


def _trimmed_mean(series: pd.Series, trim: float) -> float:
    if series.empty:
        return 0.0
    lower = series.quantile(trim / 2)
    upper = series.quantile(1 - trim / 2)
    trimmed = series[(series >= lower) & (series <= upper)]
    return float(trimmed.mean()) if not trimmed.empty else float(series.mean())


def _clr(matrix: pd.DataFrame, pseudocount: float) -> pd.DataFrame:
    shifted = matrix.clip(lower=0) + pseudocount
    log_matrix = np.log(shifted)
    geo_mean_log = log_matrix.mean(axis=0)
    return log_matrix.sub(geo_mean_log, axis=1)
