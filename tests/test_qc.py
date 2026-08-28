from omicsfusion.qc.common import run_qc


def test_run_qc_basic(transcriptomics_dataset):
    report = run_qc(transcriptomics_dataset)
    assert report.n_features == 60
    assert report.n_samples == 20
    assert report.missing_fraction == 0.0
    assert report.pca_scores is not None
    assert report.pca_variance_ratio is not None
    assert report.sample_correlation.shape == (20, 20)


def test_run_qc_flags_missing_values(transcriptomics_dataset):
    transcriptomics_dataset.matrix.iloc[0, 0] = float("nan")
    report = run_qc(transcriptomics_dataset)
    assert report.missing_fraction > 0
