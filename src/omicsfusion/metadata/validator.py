"""Metadata consistency checks (spec section 7).

Cross-checks sample metadata against one or more omics matrices and reports
every issue found — it never silently drops or fixes samples, since doing
so invisibly would undermine reproducibility. Downstream steps decide how to
react to a report that contains errors (e.g. by refusing to proceed).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from omicsfusion.core.dataset import Dataset
from omicsfusion.core.logging_config import get_logger
from omicsfusion.io.loaders import detect_id_columns

logger = get_logger("metadata.validator")


@dataclass
class MetadataValidationReport:
    n_metadata_samples: int
    n_omics_samples: dict[str, int] = field(default_factory=dict)
    missing_from_metadata: dict[str, list[str]] = field(default_factory=dict)
    missing_from_omics: dict[str, list[str]] = field(default_factory=dict)
    duplicate_sample_ids: list[str] = field(default_factory=list)
    missing_values: dict[str, int] = field(default_factory=dict)
    batch_imbalance: dict[str, dict[str, int]] = field(default_factory=dict)
    categorical_columns: list[str] = field(default_factory=list)
    numeric_columns: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        return {
            "n_metadata_samples": self.n_metadata_samples,
            "n_omics_samples": self.n_omics_samples,
            "missing_from_metadata": self.missing_from_metadata,
            "missing_from_omics": self.missing_from_omics,
            "duplicate_sample_ids": self.duplicate_sample_ids,
            "missing_values": self.missing_values,
            "batch_imbalance": self.batch_imbalance,
            "categorical_columns": self.categorical_columns,
            "numeric_columns": self.numeric_columns,
            "errors": self.errors,
            "warnings": self.warnings,
            "is_valid": self.is_valid,
        }


def validate_metadata(
    metadata: pd.DataFrame,
    datasets: dict[str, Dataset] | None = None,
    sample_id_column: str = "sample_id",
    batch_column: str | None = "batch",
) -> MetadataValidationReport:
    """Validate a metadata table, optionally cross-checked against datasets.

    Parameters
    ----------
    metadata:
        Sample-level metadata, one row per sample.
    datasets:
        Mapping of modality name -> :class:`Dataset` to cross-check sample
        overlap against. Optional so metadata can be validated standalone.
    sample_id_column:
        Column in ``metadata`` holding sample identifiers. If absent, the
        index is used instead.
    batch_column:
        Column to check for batch-size imbalance across categorical
        variables, if present.
    """
    report = MetadataValidationReport(n_metadata_samples=len(metadata))

    if sample_id_column in metadata.columns:
        sample_ids = metadata[sample_id_column].astype(str)
    else:
        report.warnings.append(
            f"Column '{sample_id_column}' not found; using DataFrame index as sample ID."
        )
        sample_ids = metadata.index.astype(str).to_series(index=metadata.index)

    dupes = sample_ids[sample_ids.duplicated()].unique().tolist()
    if dupes:
        report.duplicate_sample_ids = dupes
        report.errors.append(f"Duplicate sample IDs in metadata: {dupes}")

    if sample_ids.isna().any() or (sample_ids.astype(str).str.strip() == "").any():
        report.errors.append("Metadata contains missing or blank sample IDs.")

    missing_counts = metadata.isna().sum()
    report.missing_values = {c: int(n) for c, n in missing_counts.items() if n > 0}

    kinds = detect_id_columns(metadata)
    report.categorical_columns = kinds["categorical"]
    report.numeric_columns = kinds["numeric"]

    if batch_column and batch_column in metadata.columns:
        for col in report.categorical_columns:
            if col == batch_column:
                continue
            crosstab = pd.crosstab(metadata[batch_column], metadata[col])
            if (crosstab.sum(axis=1) > 0).sum() > 1 and crosstab.to_numpy().min() == 0:
                report.batch_imbalance[col] = crosstab.sum(axis=0).to_dict()
                report.warnings.append(
                    f"Potential batch/condition confounding: not all levels of '{col}' "
                    f"appear in every '{batch_column}' batch."
                )

    sample_id_set = set(sample_ids)
    if datasets:
        for modality, dataset in datasets.items():
            omics_samples = set(dataset.samples)
            report.n_omics_samples[modality] = len(omics_samples)

            missing_meta = sorted(omics_samples - sample_id_set)
            missing_omics = sorted(sample_id_set - omics_samples)

            if missing_meta:
                report.missing_from_metadata[modality] = missing_meta
                report.errors.append(
                    f"[{modality}] {len(missing_meta)} sample(s) present in omics data "
                    f"but absent from metadata: {missing_meta[:10]}"
                    + (" ..." if len(missing_meta) > 10 else "")
                )
            if missing_omics:
                report.missing_from_omics[modality] = missing_omics
                report.warnings.append(
                    f"[{modality}] {len(missing_omics)} sample(s) present in metadata "
                    f"but absent from omics data: {missing_omics[:10]}"
                    + (" ..." if len(missing_omics) > 10 else "")
                )

    logger.info(
        "Metadata validation: %d errors, %d warnings",
        len(report.errors),
        len(report.warnings),
    )
    return report
