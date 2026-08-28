import pytest
from pydantic import ValidationError

from omicsfusion.core.config import ProjectConfig


def test_config_roundtrip_yaml(tmp_path):
    config = ProjectConfig(
        project={"name": "test_project"},
        inputs={"transcriptomics": "a.csv", "metadata": "meta.csv"},
    )
    path = tmp_path / "project.yaml"
    config.to_yaml(path)
    loaded = ProjectConfig.from_yaml(path)
    assert loaded.project.name == "test_project"
    assert loaded.inputs.transcriptomics == "a.csv"
    assert loaded.analysis.normalization.transcriptomics == "log2"


def test_config_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ProjectConfig.from_yaml(tmp_path / "missing.yaml")


def test_config_requires_metadata():
    with pytest.raises(ValidationError):
        ProjectConfig(project={"name": "x"}, inputs={"transcriptomics": "a.csv"})


def test_omics_paths_excludes_metadata_and_none():
    config = ProjectConfig(
        project={"name": "x"},
        inputs={"transcriptomics": "a.csv", "proteomics": None, "metadata": "meta.csv"},
    )
    paths = config.inputs.omics_paths()
    assert paths == {"transcriptomics": "a.csv"}
