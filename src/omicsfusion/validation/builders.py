"""Turns raw input files + a :class:`ProjectConfig` into validated Datasets.

This is the boundary where untrusted, arbitrarily-shaped user files become
strictly-typed :class:`~omicsfusion.core.dataset.Dataset` objects. Numeric
coercion and orientation decisions happen exactly once, here, so every
downstream module can assume a clean feature-by-sample numeric matrix.
"""

from __future__ import annotations

import pandas as pd

from omicsfusion.core.config import ProjectConfig
from omicsfusion.core.dataset import Dataset, DatasetInfo, Modality
from omicsfusion.core.logging_config import get_logger
from omicsfusion.io.loaders import detect_matrix_orientation, load_table

logger = get_logger("validation.builders")


def build_dataset(path: str, modality: str) -> Dataset:
    """Load one omics file into a validated :class:`Dataset`.

    Raises ``ValueError`` if the matrix cannot be coerced to numeric —
    a non-numeric cell almost always means the file's orientation or
    header was mis-detected, and silently dropping such columns would
    hide a data-integrity problem rather than surface it.
    """
    df = load_table(path)

    orientation = detect_matrix_orientation(df)
    if orientation == "features_as_columns":
        df = df.T
        logger.info(
            "%s: transposed to features-as-rows (was features-as-columns)", path
        )

    numeric_df = df.apply(pd.to_numeric, errors="coerce")
    bad_fraction = numeric_df.isna().mean().mean() - df.isna().mean().mean()
    if bad_fraction > 0.01:
        raise ValueError(
            f"'{path}': more than 1% of values could not be parsed as numeric after "
            "orientation detection. Check that the file has features as rows (or columns) "
            "with a header row of sample IDs."
        )

    info = DatasetInfo(
        id=modality,
        name=modality,
        modality=Modality(modality),
        source=str(path),
    )
    dataset = Dataset(numeric_df, info)
    dataset.record_step(f"loaded:{orientation}")
    logger.info("Built dataset '%s': %s", modality, dataset)
    return dataset


def load_project_datasets(config: ProjectConfig) -> dict[str, Dataset]:
    """Load every omics input declared in a project config."""
    datasets: dict[str, Dataset] = {}
    for modality, path in config.inputs.omics_paths().items():
        datasets[modality] = build_dataset(path, modality)
    return datasets


def load_metadata_table(config: ProjectConfig) -> pd.DataFrame:
    """Load the sample metadata table, keeping the sample ID as a real column.

    Unlike omics matrices (where the first column becomes the feature-ID
    index), metadata is sample-per-row data that downstream code expects to
    filter/group on by column, so any index :func:`load_table` inferred is
    restored as a normal column.
    """
    df = load_table(config.inputs.metadata)
    if df.index.name is not None:
        df = df.reset_index()
    return df
