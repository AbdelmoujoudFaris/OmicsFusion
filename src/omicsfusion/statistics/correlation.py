"""Cross-omics feature correlation (spec section 19).

Correlating two omics layers only makes sense on comparable, appropriately
transformed values on a common sample axis — this module intersects samples
explicitly and lets the caller pick Pearson (linear, assumes
roughly-normal, transformed data) or Spearman (rank-based, robust to
non-normality and outliers, the safer default for untransformed or
compositional data).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from omicsfusion.core.dataset import Dataset
from omicsfusion.core.logging_config import get_logger

logger = get_logger("statistics.correlation")


@dataclass
class CorrelationResult:
    modality_a: str
    modality_b: str
    method: str
    table: pd.DataFrame  # feature_a, feature_b, correlation, p_value, adjusted_p_value


def cross_omics_correlation(
    dataset_a: Dataset,
    dataset_b: Dataset,
    method: str = "spearman",
    top_n_variable: int = 50,
    correction: str = "fdr_bh",
    min_samples: int = 4,
) -> CorrelationResult:
    """All-pairs correlation between the most variable features of two datasets.

    ``top_n_variable`` caps runtime and the multiple-testing burden by
    restricting to the most variable features per dataset (variance carries
    the most information for exploratory correlation; low-variance features
    are dominated by noise). Set higher for smaller feature sets.
    """
    common_samples = [s for s in dataset_a.samples if s in dataset_b.samples]
    if len(common_samples) < min_samples:
        raise ValueError(
            f"Only {len(common_samples)} shared samples between "
            f"'{dataset_a.info.id}' and '{dataset_b.info.id}'; need >= {min_samples}."
        )

    mat_a = dataset_a.matrix[common_samples]
    mat_b = dataset_b.matrix[common_samples]

    var_a = mat_a.var(axis=1).sort_values(ascending=False)
    var_b = mat_b.var(axis=1).sort_values(ascending=False)
    features_a = var_a.head(top_n_variable).index
    features_b = var_b.head(top_n_variable).index

    corr_fn = stats.pearsonr if method == "pearson" else stats.spearmanr
    if method not in ("pearson", "spearman"):
        raise ValueError("method must be 'pearson' or 'spearman'")

    rows = []
    for fa, fb in product(features_a, features_b):
        x = mat_a.loc[fa].to_numpy(dtype=float)
        y = mat_b.loc[fb].to_numpy(dtype=float)
        mask = ~(np.isnan(x) | np.isnan(y))
        if mask.sum() < min_samples:
            continue
        r, p = corr_fn(x[mask], y[mask])
        rows.append({"feature_a": fa, "feature_b": fb, "correlation": r, "p_value": p})

    if not rows:
        raise ValueError(
            "No feature pairs had sufficient overlapping non-missing data."
        )

    table = pd.DataFrame(rows)
    _, adj_p, _, _ = multipletests(table["p_value"].to_numpy(), method=correction)
    table["adjusted_p_value"] = adj_p
    table = table.sort_values("p_value").reset_index(drop=True)

    logger.info(
        "Correlation[%s vs %s]: %d pairs tested (%s), %d significant (FDR<0.05)",
        dataset_a.info.id,
        dataset_b.info.id,
        len(table),
        method,
        int((table["adjusted_p_value"] < 0.05).sum()),
    )

    return CorrelationResult(
        modality_a=str(dataset_a.info.id),
        modality_b=str(dataset_b.info.id),
        method=method,
        table=table,
    )
