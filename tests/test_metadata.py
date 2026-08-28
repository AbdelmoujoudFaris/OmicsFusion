import pandas as pd

from omicsfusion.metadata.validator import validate_metadata


def test_validate_metadata_clean(metadata, transcriptomics_dataset):
    report = validate_metadata(metadata, {"transcriptomics": transcriptomics_dataset})
    assert report.is_valid
    assert not report.errors


def test_validate_metadata_detects_duplicate_ids(metadata):
    dup = metadata.copy()
    dup.loc[1, "sample_id"] = dup.loc[0, "sample_id"]
    report = validate_metadata(dup)
    assert not report.is_valid
    assert any("Duplicate sample IDs" in e for e in report.errors)


def test_validate_metadata_missing_from_metadata(metadata, transcriptomics_dataset):
    truncated = metadata.iloc[:-1]  # drop the last sample from metadata
    report = validate_metadata(truncated, {"transcriptomics": transcriptomics_dataset})
    assert not report.is_valid
    assert "transcriptomics" in report.missing_from_metadata


def test_validate_metadata_missing_from_omics_is_warning_not_error(
    metadata, transcriptomics_dataset
):
    extra = pd.concat(
        [
            metadata,
            pd.DataFrame(
                [{"sample_id": "S99", "condition": "control", "batch": "B1", "age": 40}]
            ),
        ],
        ignore_index=True,
    )
    report = validate_metadata(extra, {"transcriptomics": transcriptomics_dataset})
    assert report.is_valid
    assert "transcriptomics" in report.missing_from_omics
    assert any("absent from omics data" in w for w in report.warnings)


def test_validate_metadata_no_sample_id_column_warns():
    df = pd.DataFrame({"condition": ["a", "b"]})
    report = validate_metadata(df)
    assert any("not found" in w for w in report.warnings)
