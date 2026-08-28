import pytest

from omicsfusion.integration.methods import early_integration, pca_consensus_integration


def test_early_integration_shapes(transcriptomics_dataset, proteomics_dataset):
    result = early_integration(
        {"transcriptomics": transcriptomics_dataset, "proteomics": proteomics_dataset}
    )
    assert result.combined.shape[0] == 20
    assert result.combined.shape[1] == 60 + 40
    assert set(result.modality_boundaries) == {"transcriptomics", "proteomics"}


def test_early_integration_requires_two_modalities(transcriptomics_dataset):
    with pytest.raises(ValueError, match="at least 2"):
        early_integration({"transcriptomics": transcriptomics_dataset})


def test_pca_consensus_integration_shapes(transcriptomics_dataset, proteomics_dataset):
    result = pca_consensus_integration(
        {"transcriptomics": transcriptomics_dataset, "proteomics": proteomics_dataset},
        n_components_per_modality=3,
    )
    assert result.combined.shape == (20, 6)
    assert result.variance_explained is not None


def test_integration_requires_shared_samples(
    transcriptomics_dataset, proteomics_dataset
):
    proteomics_dataset.matrix.columns = [
        f"OTHER_{i}" for i in range(proteomics_dataset.n_samples)
    ]
    with pytest.raises(ValueError, match="shared across"):
        early_integration(
            {
                "transcriptomics": transcriptomics_dataset,
                "proteomics": proteomics_dataset,
            }
        )
