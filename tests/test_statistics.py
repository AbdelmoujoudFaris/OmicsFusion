import pytest

from omicsfusion.normalization.normalize import normalize_dataset
from omicsfusion.statistics.correlation import cross_omics_correlation
from omicsfusion.statistics.differential import differential_analysis


def test_differential_analysis_finds_signal(transcriptomics_dataset, metadata):
    normalized = normalize_dataset(transcriptomics_dataset, "zscore")
    result = differential_analysis(
        normalized, metadata, "condition", "treated", "control"
    )
    assert set(result.table.columns) >= {
        "feature",
        "log2FC",
        "p_value",
        "adjusted_p_value",
        "effect_size",
    }
    significant = result.significant(alpha=0.05)
    # the first 10 features carry the simulated effect
    signal_features = {f"feat_{i:03d}" for i in range(10)}
    assert len(signal_features & set(significant["feature"])) > 0


def test_differential_analysis_missing_condition_column(
    transcriptomics_dataset, metadata
):
    with pytest.raises(ValueError, match="not found in metadata"):
        differential_analysis(
            transcriptomics_dataset, metadata, "nonexistent", "a", "b"
        )


def test_differential_analysis_insufficient_samples(transcriptomics_dataset, metadata):
    tiny_meta = metadata.iloc[:1]
    with pytest.raises(ValueError, match="Insufficient samples"):
        differential_analysis(
            transcriptomics_dataset, tiny_meta, "condition", "treated", "control"
        )


def test_cross_omics_correlation(transcriptomics_dataset, proteomics_dataset):
    result = cross_omics_correlation(
        transcriptomics_dataset, proteomics_dataset, top_n_variable=10
    )
    assert not result.table.empty
    assert {
        "feature_a",
        "feature_b",
        "correlation",
        "p_value",
        "adjusted_p_value",
    } <= set(result.table.columns)


def test_cross_omics_correlation_insufficient_overlap(
    transcriptomics_dataset, proteomics_dataset
):
    proteomics_dataset.matrix.columns = [
        f"OTHER_{i}" for i in range(proteomics_dataset.n_samples)
    ]
    with pytest.raises(ValueError, match="shared samples"):
        cross_omics_correlation(transcriptomics_dataset, proteomics_dataset)
