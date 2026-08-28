"""Quality-control metrics shared across omics modalities (spec section 8).

Rather than one QC function per modality with duplicated logic, this module
implements the generic metrics (library size, missingness, PCA, sample
correlation, coefficient of variation, outlier flagging) once, and modality
wrappers (see ``qc.transcriptomics`` etc. accessed via ``run_qc``) select
which subset is meaningful for that data type. Count data and intensity
data have different QC needs; a caller should not assume every metric
applies to every modality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from omicsfusion.core.dataset import Dataset
from omicsfusion.core.logging_config import get_logger

logger = get_logger("qc.common")

# Modalities where each column is a library-size-normalisable count/intensity
# sum (library size is meaningless for e.g. clinical data).
_LIBRARY_SIZE_MODALITIES = {
    "transcriptomics",
    "proteomics",
    "metabolomics",
    "metagenomics",
    "microbiome",
    "lipidomics",
}


@dataclass
class QCReport:
    modality: str
    n_features: int
    n_samples: int
    missing_fraction: float
    missing_by_sample: dict[str, float] = field(default_factory=dict)
    missing_by_feature_max: float = 0.0
    library_sizes: dict[str, float] | None = None
    cv_by_feature_median: float | None = None
    sample_correlation: pd.DataFrame | None = None
    pca_scores: pd.DataFrame | None = None
    pca_variance_ratio: list[float] | None = None
    outlier_samples: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "modality": self.modality,
            "n_features": self.n_features,
            "n_samples": self.n_samples,
            "missing_fraction": self.missing_fraction,
            "missing_by_feature_max": self.missing_by_feature_max,
            "cv_by_feature_median": self.cv_by_feature_median,
            "pca_variance_ratio": self.pca_variance_ratio,
            "outlier_samples": self.outlier_samples,
            "warnings": self.warnings,
        }
        return d


def run_qc(dataset: Dataset, outlier_sd: float = 3.0) -> QCReport:
    """Compute standard QC metrics for a dataset.

    ``outlier_sd`` sets the Mahalanobis-like flag threshold on the first two
    PCA dimensions: samples further than ``outlier_sd`` standard deviations
    from the centroid are flagged for review (not removed automatically —
    removing samples silently would hide a real batch or handling problem).
    """
    matrix = dataset.matrix
    modality = dataset.info.modality

    report = QCReport(
        modality=modality,
        n_features=dataset.n_features,
        n_samples=dataset.n_samples,
        missing_fraction=float(matrix.isna().mean().mean()),
        missing_by_sample={c: float(v) for c, v in matrix.isna().mean().items()},
        missing_by_feature_max=(
            float(matrix.isna().mean(axis=1).max()) if len(matrix) else 0.0
        ),
    )

    if modality in _LIBRARY_SIZE_MODALITIES:
        report.library_sizes = matrix.sum(axis=0, skipna=True).to_dict()
        sizes = np.array(list(report.library_sizes.values()), dtype=float)
        if sizes.size and sizes.mean() > 0 and (sizes.std() / sizes.mean()) > 1.0:
            report.warnings.append(
                "Library sizes vary by more than 100% CV across samples; "
                "consider library-size normalisation before downstream analysis."
            )

    numeric = matrix.dropna(how="all", axis=0).fillna(
        matrix.mean(axis=1, skipna=True), axis=0
    )
    numeric = numeric.dropna(how="any", axis=0)
    if numeric.shape[0] >= 2:
        row_mean = numeric.mean(axis=1)
        row_std = numeric.std(axis=1)
        cv = (row_std / row_mean.replace(0, np.nan)).abs()
        report.cv_by_feature_median = float(cv.median(skipna=True))

    if numeric.shape[0] >= 2 and numeric.shape[1] >= 2:
        report.sample_correlation = numeric.corr(method="spearman")

    if numeric.shape[0] >= 2 and numeric.shape[1] >= 3:
        n_components = min(2, numeric.shape[1] - 1, numeric.shape[0])
        pca = PCA(n_components=n_components)
        scores = pca.fit_transform(numeric.T.values)
        cols = [f"PC{i + 1}" for i in range(scores.shape[1])]
        report.pca_scores = pd.DataFrame(scores, index=numeric.columns, columns=cols)
        report.pca_variance_ratio = pca.explained_variance_ratio_.tolist()

        if scores.shape[1] >= 2:
            centroid = scores[:, :2].mean(axis=0)
            dist = np.linalg.norm(scores[:, :2] - centroid, axis=1)
            threshold = (
                dist.mean() + outlier_sd * dist.std() if dist.std() > 0 else np.inf
            )
            outlier_mask = dist > threshold
            report.outlier_samples = list(numeric.columns[outlier_mask])
            if report.outlier_samples:
                report.warnings.append(
                    f"Potential outlier samples (>{outlier_sd} SD from PCA centroid): "
                    f"{report.outlier_samples}"
                )

    logger.info(
        "QC[%s]: %d features x %d samples, missing=%.1f%%, %d warning(s)",
        modality,
        report.n_features,
        report.n_samples,
        report.missing_fraction * 100,
        len(report.warnings),
    )
    return report
