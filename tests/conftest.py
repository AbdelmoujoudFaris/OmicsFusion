"""Shared pytest fixtures: small, fast, in-memory synthetic multi-omics data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from omicsfusion.core.dataset import Dataset, DatasetInfo


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(0)


@pytest.fixture
def sample_ids() -> list[str]:
    return [f"S{i:02d}" for i in range(1, 21)]


@pytest.fixture
def metadata(sample_ids) -> pd.DataFrame:
    groups = ["treated"] * 10 + ["control"] * 10
    return pd.DataFrame(
        {
            "sample_id": sample_ids,
            "condition": groups,
            "batch": ["B1", "B2"] * 10,
            "age": np.linspace(30, 70, 20),
        }
    )


def _make_matrix(rng, sample_ids, n_features, signal_features, effect):
    n = len(sample_ids)
    is_treated = np.array([1.0 if i < n // 2 else 0.0 for i in range(n)])
    data = rng.normal(loc=10, scale=2, size=(n_features, n))
    for i in range(signal_features):
        data[i] += effect * is_treated
    return pd.DataFrame(
        np.abs(data),
        index=[f"feat_{i:03d}" for i in range(n_features)],
        columns=sample_ids,
    )


@pytest.fixture
def transcriptomics_dataset(rng, sample_ids) -> Dataset:
    matrix = _make_matrix(
        rng, sample_ids, n_features=60, signal_features=10, effect=8.0
    )
    info = DatasetInfo(
        id="transcriptomics", name="transcriptomics", modality="transcriptomics"
    )
    return Dataset(matrix, info)


@pytest.fixture
def proteomics_dataset(rng, sample_ids) -> Dataset:
    matrix = _make_matrix(
        rng, sample_ids, n_features=40, signal_features=10, effect=6.0
    )
    info = DatasetInfo(id="proteomics", name="proteomics", modality="proteomics")
    return Dataset(matrix, info)
