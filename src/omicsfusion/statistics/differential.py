"""Generic two-group differential analysis framework (spec section 10).

One statistical engine serves every modality: the underlying test
(Welch's t-test by default, Mann-Whitney U for non-parametric use) and
multiple-testing correction are shared, while the *interpretation* of the
fold-change direction adapts to whether the data is already log-transformed
(transcriptomics/proteomics after log2, metabolomics after log) or still on
a raw/linear scale.

This is a defensible general-purpose default, not a replacement for
modality-specific tools with more statistical power (DESeq2/edgeR for raw
RNA-seq counts, limma for proteomics) — see ``R/differential/`` for those.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from omicsfusion.core.dataset import Dataset
from omicsfusion.core.logging_config import get_logger

logger = get_logger("statistics.differential")

_LOG_SCALE_METHODS = {"log", "log2", "log10", "vst", "clr", "zscore"}


@dataclass
class DifferentialResult:
    modality: str
    condition_column: str
    group: str
    reference: str
    method: str
    correction: str
    table: (
        pd.DataFrame
    )  # feature, log2FC, p_value, adjusted_p_value, effect_size, mean_group, mean_reference

    def significant(self, alpha: float = 0.05) -> pd.DataFrame:
        return self.table[self.table["adjusted_p_value"] < alpha].sort_values(
            "adjusted_p_value"
        )


def differential_analysis(
    dataset: Dataset,
    metadata: pd.DataFrame,
    condition_column: str,
    group: str,
    reference: str,
    sample_id_column: str = "sample_id",
    method: str = "ttest",
    correction: str = "fdr_bh",
    min_group_size: int = 2,
) -> DifferentialResult:
    """Compare ``group`` vs ``reference`` levels of ``condition_column``.

    Raises ``ValueError`` if either group has fewer than ``min_group_size``
    samples after intersecting with the dataset — an underpowered
    comparison should fail loudly rather than emit unreliable p-values.
    """
    if condition_column not in metadata.columns:
        raise ValueError(
            f"Condition column '{condition_column}' not found in metadata."
        )

    meta = metadata.copy()
    if sample_id_column in meta.columns:
        meta = meta.set_index(sample_id_column)

    common = [s for s in dataset.samples if s in meta.index]
    if not common:
        raise ValueError("No overlapping samples between dataset and metadata.")

    meta = meta.loc[common]
    group_samples = meta.index[meta[condition_column] == group].tolist()
    reference_samples = meta.index[meta[condition_column] == reference].tolist()

    if len(group_samples) < min_group_size or len(reference_samples) < min_group_size:
        raise ValueError(
            f"Insufficient samples for comparison '{group}' (n={len(group_samples)}) vs "
            f"'{reference}' (n={len(reference_samples)}); need >= {min_group_size} each."
        )

    matrix = dataset.matrix
    group_data = matrix[group_samples]
    ref_data = matrix[reference_samples]
    is_log_scale = dataset.info.normalization in _LOG_SCALE_METHODS

    rows = []
    for feature in matrix.index:
        g = group_data.loc[feature].dropna().to_numpy(dtype=float)
        r = ref_data.loc[feature].dropna().to_numpy(dtype=float)
        if len(g) < min_group_size or len(r) < min_group_size:
            continue

        if method == "ttest":
            stat, p_value = stats.ttest_ind(g, r, equal_var=False)
        elif method == "mannwhitney":
            stat, p_value = stats.mannwhitneyu(g, r, alternative="two-sided")
        else:
            raise ValueError(
                f"Unknown method '{method}'. Use 'ttest' or 'mannwhitney'."
            )

        mean_g, mean_r = g.mean(), r.mean()
        if is_log_scale:
            log2fc = mean_g - mean_r
        else:
            log2fc = np.log2((mean_g + 1e-9) / (mean_r + 1e-9))

        pooled_sd = np.sqrt(((g.std(ddof=1) ** 2) + (r.std(ddof=1) ** 2)) / 2)
        effect_size = (mean_g - mean_r) / pooled_sd if pooled_sd > 0 else 0.0

        rows.append(
            {
                "feature": feature,
                "log2FC": log2fc,
                "p_value": p_value,
                "effect_size": effect_size,
                "mean_group": mean_g,
                "mean_reference": mean_r,
                "statistic": stat,
            }
        )

    if not rows:
        raise ValueError("No features had sufficient non-missing data in both groups.")

    table = pd.DataFrame(rows)
    method_map = {"fdr_bh": "fdr_bh", "bonferroni": "bonferroni"}
    if correction not in method_map:
        raise ValueError(
            f"Unknown correction '{correction}'. Use 'fdr_bh' or 'bonferroni'."
        )
    _, adj_p, _, _ = multipletests(
        table["p_value"].to_numpy(), method=method_map[correction]
    )
    table["adjusted_p_value"] = adj_p
    table = table.sort_values("p_value").reset_index(drop=True)

    logger.info(
        "Differential[%s]: %s vs %s, %d features tested, %d significant (FDR<0.05)",
        dataset.info.modality,
        group,
        reference,
        len(table),
        int((table["adjusted_p_value"] < 0.05).sum()),
    )

    return DifferentialResult(
        modality=str(dataset.info.modality),
        condition_column=condition_column,
        group=group,
        reference=reference,
        method=method,
        correction=correction,
        table=table,
    )
