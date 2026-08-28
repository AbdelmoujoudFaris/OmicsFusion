import pandas as pd
import pytest

from omicsfusion.machine_learning.models import run_ml


def test_run_ml_classification(transcriptomics_dataset, metadata):
    X = transcriptomics_dataset.matrix.T
    y = metadata.set_index("sample_id")["condition"]
    result = run_ml(
        X, y, task="classification", models=["random_forest"], cv_folds=3, test_size=0.3
    )
    assert result.n_samples == 20
    assert len(result.results) == 1
    model_result = result.results[0]
    assert "accuracy" in model_result.test_metrics
    assert model_result.feature_importance is not None
    assert len(model_result.feature_importance) == X.shape[1]


def test_run_ml_regression(transcriptomics_dataset, metadata):
    X = transcriptomics_dataset.matrix.T
    y = metadata.set_index("sample_id")["age"]
    result = run_ml(
        X, y, task="regression", models=["random_forest"], cv_folds=3, test_size=0.3
    )
    assert "r2" in result.results[0].test_metrics


def test_run_ml_insufficient_samples(transcriptomics_dataset):
    X = transcriptomics_dataset.matrix.T.iloc[:4]
    y = pd.Series(["a", "b", "a", "b"], index=X.index)
    with pytest.raises(ValueError, match="Only 4 labelled"):
        run_ml(X, y, task="classification", cv_folds=5)


def test_run_ml_invalid_task(transcriptomics_dataset, metadata):
    X = transcriptomics_dataset.matrix.T
    y = metadata.set_index("sample_id")["condition"]
    with pytest.raises(ValueError, match="task must be"):
        run_ml(X, y, task="clustering")
