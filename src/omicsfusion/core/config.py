"""Project configuration schema.

A single ``project.yaml`` file is the source of truth for a run — whether
that run is launched from the CLI, the Streamlit GUI, or Nextflow. The GUI
never analyses data directly: every GUI action edits and re-serialises this
schema, which is what actually gets executed, so any run is reproducible
from its config file alone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

NormalizationMethod = Literal[
    "zscore",
    "log",
    "log2",
    "log10",
    "minmax",
    "quantile",
    "median",
    "vst",
    "clr",
    "tmm",
    "none",
]
IntegrationMethod = Literal[
    "early_concat", "mofa", "diablo", "correlation", "pca_consensus"
]
MLModel = Literal[
    "random_forest", "elastic_net", "logistic_regression", "svm", "xgboost"
]


class ProjectMeta(BaseModel):
    name: str
    organism: str | None = None
    description: str | None = None


class InputsConfig(BaseModel):
    transcriptomics: str | None = None
    proteomics: str | None = None
    metabolomics: str | None = None
    metagenomics: str | None = None
    microbiome: str | None = None
    epigenomics: str | None = None
    lipidomics: str | None = None
    clinical: str | None = None
    metadata: str

    def omics_paths(self) -> dict[str, str]:
        """All configured omics inputs, excluding metadata, keyed by modality."""
        data = self.model_dump(exclude={"metadata"})
        return {k: v for k, v in data.items() if v}


class NormalizationConfig(BaseModel):
    transcriptomics: NormalizationMethod = "log2"
    proteomics: NormalizationMethod = "log2"
    metabolomics: NormalizationMethod = "zscore"
    metagenomics: NormalizationMethod = "clr"
    microbiome: NormalizationMethod = "clr"
    epigenomics: NormalizationMethod = "zscore"
    lipidomics: NormalizationMethod = "log2"
    clinical: NormalizationMethod = "none"


class DifferentialConfig(BaseModel):
    condition: str
    reference: str
    group: str | None = None
    method: str | None = None
    alpha: float = 0.05
    correction: Literal["fdr_bh", "bonferroni"] = "fdr_bh"


class IntegrationConfig(BaseModel):
    methods: list[IntegrationMethod] = Field(default_factory=lambda: ["early_concat"])
    n_factors: int = 10


class MachineLearningConfig(BaseModel):
    enabled: bool = False
    target: str | None = None
    task: Literal["classification", "regression"] = "classification"
    models: list[MLModel] = Field(default_factory=lambda: ["random_forest"])
    cv_folds: int = 5
    test_size: float = 0.25
    random_state: int = 42


class PathwayConfig(BaseModel):
    enabled: bool = False
    organism: str = "human"
    gene_sets: list[str] = Field(default_factory=lambda: ["GO_Biological_Process"])
    method: Literal["ora", "gsea"] = "ora"


class AnalysisConfig(BaseModel):
    qc: bool = True
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)
    differential: DifferentialConfig | None = None
    integration: IntegrationConfig = Field(default_factory=IntegrationConfig)
    machine_learning: MachineLearningConfig = Field(
        default_factory=MachineLearningConfig
    )
    pathways: PathwayConfig = Field(default_factory=PathwayConfig)


class ProjectConfig(BaseModel):
    """Root schema for ``project.yaml``."""

    project: ProjectMeta
    inputs: InputsConfig
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    outdir: str = "results"
    random_seed: int = 42

    @field_validator("outdir")
    @classmethod
    def _not_absolute_hint(cls, v: str) -> str:
        return v

    @classmethod
    def from_yaml(cls, path: str | Path) -> ProjectConfig:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        return cls.model_validate(raw)

    def to_yaml(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(
                self.model_dump(mode="json", exclude_none=False), fh, sort_keys=False
            )
