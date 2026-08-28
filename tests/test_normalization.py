import numpy as np
import pytest

from omicsfusion.normalization.normalize import normalize_dataset


@pytest.mark.parametrize(
    "method",
    [
        "none",
        "log",
        "log2",
        "log10",
        "zscore",
        "minmax",
        "quantile",
        "median",
        "vst",
        "clr",
        "tmm",
    ],
)
def test_normalize_dataset_runs_and_preserves_shape(transcriptomics_dataset, method):
    result = normalize_dataset(transcriptomics_dataset, method)
    assert result.matrix.shape == transcriptomics_dataset.matrix.shape
    assert result.info.normalization == method
    assert f"normalization:{method}" in result.info.preprocessing
    # original untouched
    assert transcriptomics_dataset.info.normalization is None


def test_normalize_zscore_centers_features(transcriptomics_dataset):
    result = normalize_dataset(transcriptomics_dataset, "zscore")
    means = result.matrix.mean(axis=1)
    assert np.allclose(means, 0, atol=1e-8)


def test_normalize_minmax_bounds(transcriptomics_dataset):
    result = normalize_dataset(transcriptomics_dataset, "minmax")
    assert result.matrix.min().min() >= -1e-9
    assert result.matrix.max().max() <= 1 + 1e-9


def test_normalize_unknown_method_raises(transcriptomics_dataset):
    with pytest.raises(ValueError):
        normalize_dataset(transcriptomics_dataset, "not_a_method")
