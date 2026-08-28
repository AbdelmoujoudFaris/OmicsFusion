"""Unified internal data model for an omics dataset.

Every dataset loaded into OmicsFusion (regardless of original file format)
is wrapped in a :class:`Dataset`, which pairs a feature-by-sample matrix
with strictly-validated provenance metadata (modality, units, normalisation
state, ...). Downstream modules (QC, normalisation, statistics, integration)
depend on this contract rather than on raw DataFrames, so they can validate
assumptions (e.g. "has this been normalised?") before running.
"""

from __future__ import annotations

import datetime as _dt
from enum import Enum
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Modality(str, Enum):
    TRANSCRIPTOMICS = "transcriptomics"
    PROTEOMICS = "proteomics"
    METABOLOMICS = "metabolomics"
    METAGENOMICS = "metagenomics"
    MICROBIOME = "microbiome"
    EPIGENOMICS = "epigenomics"
    LIPIDOMICS = "lipidomics"
    CLINICAL = "clinical"


class DatasetInfo(BaseModel):
    """Provenance and processing-state metadata for one omics dataset."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    name: str
    modality: Modality
    organism: str | None = None
    genome_build: str | None = None
    platform: str | None = None
    units: str | None = None
    feature_id_type: str | None = None
    sample_id_column: str = "sample_id"
    preprocessing: list[str] = Field(default_factory=list)
    normalization: str | None = None
    source: str | None = None
    created_at: _dt.datetime = Field(default_factory=_dt.datetime.now)
    software_versions: dict[str, str] = Field(default_factory=dict)

    @field_validator("id", "name")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be a non-empty string")
        return v


class Dataset:
    """A feature x sample matrix bundled with validated :class:`DatasetInfo`.

    Convention: rows are features (genes, proteins, metabolites, taxa),
    columns are sample IDs. This matches how most omics quantification tools
    emit tables and keeps the sample axis consistent with metadata joins.
    """

    def __init__(self, matrix: pd.DataFrame, info: DatasetInfo):
        if matrix.empty:
            raise ValueError(f"Dataset '{info.id}' matrix is empty")
        if matrix.columns.duplicated().any():
            dupes = matrix.columns[matrix.columns.duplicated()].tolist()
            raise ValueError(
                f"Dataset '{info.id}' has duplicate sample columns: {dupes}"
            )
        if matrix.index.duplicated().any():
            dupes = matrix.index[matrix.index.duplicated()].tolist()[:10]
            raise ValueError(
                f"Dataset '{info.id}' has duplicate feature IDs: {dupes} ..."
            )
        self.matrix = matrix
        self.info = info

    @property
    def n_features(self) -> int:
        return self.matrix.shape[0]

    @property
    def n_samples(self) -> int:
        return self.matrix.shape[1]

    @property
    def samples(self) -> list[str]:
        return list(self.matrix.columns)

    @property
    def features(self) -> list[str]:
        return list(self.matrix.index)

    def record_step(self, step: str) -> None:
        """Append a processing step to the provenance trail."""
        self.info.preprocessing.append(step)

    def to_summary(self) -> dict[str, Any]:
        return {
            "id": self.info.id,
            "modality": self.info.modality,
            "n_features": self.n_features,
            "n_samples": self.n_samples,
            "normalization": self.info.normalization,
            "preprocessing": list(self.info.preprocessing),
            "missing_fraction": float(self.matrix.isna().mean().mean()),
        }

    def copy(self) -> Dataset:
        return Dataset(self.matrix.copy(), self.info.model_copy(deep=True))

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return (
            f"Dataset(id={self.info.id!r}, modality={self.info.modality}, "
            f"features={self.n_features}, samples={self.n_samples})"
        )
