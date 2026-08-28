import pandas as pd
import pytest
from pydantic import ValidationError

from omicsfusion.core.dataset import Dataset, DatasetInfo


def test_dataset_info_rejects_empty_id():
    with pytest.raises(ValidationError):
        DatasetInfo(id="", name="x", modality="transcriptomics")


def test_dataset_rejects_empty_matrix():
    info = DatasetInfo(id="rna", name="rna", modality="transcriptomics")
    with pytest.raises(ValueError):
        Dataset(pd.DataFrame(), info)


def test_dataset_rejects_duplicate_samples():
    matrix = pd.DataFrame({"S1": [1, 2], "S1_dup": [3, 4]})
    matrix.columns = ["S1", "S1"]
    info = DatasetInfo(id="rna", name="rna", modality="transcriptomics")
    with pytest.raises(ValueError, match="duplicate sample columns"):
        Dataset(matrix, info)


def test_dataset_rejects_duplicate_features():
    matrix = pd.DataFrame({"S1": [1, 2], "S2": [3, 4]}, index=["g1", "g1"])
    info = DatasetInfo(id="rna", name="rna", modality="transcriptomics")
    with pytest.raises(ValueError, match="duplicate feature IDs"):
        Dataset(matrix, info)


def test_dataset_record_step_and_summary(transcriptomics_dataset):
    transcriptomics_dataset.record_step("normalized:log2")
    summary = transcriptomics_dataset.to_summary()
    assert "normalized:log2" in summary["preprocessing"]
    assert summary["n_features"] == 60
    assert summary["n_samples"] == 20


def test_dataset_copy_is_independent(transcriptomics_dataset):
    copy = transcriptomics_dataset.copy()
    copy.matrix.iloc[0, 0] = 999
    copy.record_step("mutated")
    assert transcriptomics_dataset.matrix.iloc[0, 0] != 999
    assert "mutated" not in transcriptomics_dataset.info.preprocessing
