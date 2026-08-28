"""Multi-omics integration strategies (spec section 12).

Implements the two integration strategies that have a defensible pure-Python
implementation for the MVP:

* **Early integration** — scale and concatenate feature matrices on their
  common samples. Simple and interpretable, but treats all modalities as
  one feature space and can let a high-dimensional modality dominate.
* **PCA consensus (intermediate integration)** — reduce each modality to
  its own principal components first, then concatenate scores. This limits
  any one modality's dimensionality from dominating the joint space and is
  a lightweight, dependency-free stand-in for factor-analysis methods.

Rigorous latent-factor methods (MOFA2, DIABLO/mixOmics) require the R
ecosystem and are implemented as an R bridge in ``R/integration/`` — see
``docs/integration.md``. This module raises clearly rather than faking
those methods in Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from omicsfusion.core.dataset import Dataset
from omicsfusion.core.logging_config import get_logger

logger = get_logger("integration.methods")


@dataclass
class IntegrationResult:
    method: str
    samples: list[str]
    combined: pd.DataFrame  # samples x features (or samples x components)
    modality_boundaries: dict[str, list[str]] = field(default_factory=dict)
    variance_explained: dict[str, list[float]] | None = None


def _common_samples(datasets: dict[str, Dataset]) -> list[str]:
    sample_sets = [set(ds.samples) for ds in datasets.values()]
    common = set.intersection(*sample_sets) if sample_sets else set()
    if len(common) < 3:
        raise ValueError(
            f"Only {len(common)} samples shared across all {len(datasets)} modalities; "
            "need >= 3 for integration."
        )
    order = next(iter(datasets.values())).samples
    return [s for s in order if s in common]


def early_integration(
    datasets: dict[str, Dataset], scale: bool = True
) -> IntegrationResult:
    """Scale each modality independently, then concatenate on shared samples."""
    if len(datasets) < 2:
        raise ValueError("Early integration requires at least 2 modalities.")

    samples = _common_samples(datasets)
    blocks = []
    boundaries: dict[str, list[str]] = {}

    for modality, dataset in datasets.items():
        block = dataset.matrix[samples].T  # samples x features
        block = block.fillna(block.mean(axis=0))
        if scale:
            values = StandardScaler().fit_transform(block.values)
        else:
            values = block.values
        col_names = [f"{modality}::{f}" for f in block.columns]
        blocks.append(pd.DataFrame(values, index=samples, columns=col_names))
        boundaries[modality] = col_names

    combined = pd.concat(blocks, axis=1)
    logger.info(
        "Early integration: %d samples x %d combined features across %d modalities",
        combined.shape[0],
        combined.shape[1],
        len(datasets),
    )
    return IntegrationResult(
        method="early_concat",
        samples=samples,
        combined=combined,
        modality_boundaries=boundaries,
    )


def pca_consensus_integration(
    datasets: dict[str, Dataset], n_components_per_modality: int = 5
) -> IntegrationResult:
    """Reduce each modality to its own PCs, then concatenate the scores.

    A dependency-free approximation of intermediate integration; for a
    proper joint latent-factor model with cross-view variance decomposition,
    use the MOFA2 R bridge (``docs/integration.md``).
    """
    if len(datasets) < 2:
        raise ValueError("PCA consensus integration requires at least 2 modalities.")

    samples = _common_samples(datasets)
    blocks = []
    boundaries: dict[str, list[str]] = {}
    variance_explained: dict[str, list[float]] = {}

    for modality, dataset in datasets.items():
        block = dataset.matrix[samples].T
        block = block.fillna(block.mean(axis=0))
        n_comp = min(n_components_per_modality, block.shape[0] - 1, block.shape[1])
        n_comp = max(n_comp, 1)
        scaled = StandardScaler().fit_transform(block.values)
        pca = PCA(n_components=n_comp)
        scores = pca.fit_transform(scaled)
        col_names = [f"{modality}::PC{i + 1}" for i in range(n_comp)]
        blocks.append(pd.DataFrame(scores, index=samples, columns=col_names))
        boundaries[modality] = col_names
        variance_explained[modality] = pca.explained_variance_ratio_.tolist()

    combined = pd.concat(blocks, axis=1)
    logger.info(
        "PCA consensus integration: %d samples x %d components across %d modalities",
        combined.shape[0],
        combined.shape[1],
        len(datasets),
    )
    return IntegrationResult(
        method="pca_consensus",
        samples=samples,
        combined=combined,
        modality_boundaries=boundaries,
        variance_explained=variance_explained,
    )


def cross_view_correlation_matrix(result: IntegrationResult) -> pd.DataFrame:
    """Pearson correlation matrix across all combined components/features."""
    return result.combined.corr(method="pearson")
