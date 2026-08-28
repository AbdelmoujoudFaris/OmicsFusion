import pytest

from omicsfusion.core.r_bridge import (
    RNotAvailableError,
    rscript_available,
    run_r_script,
)


def test_run_r_script_raises_when_r_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(RNotAvailableError):
        run_r_script("differential/deseq2_differential.R", [])


def test_run_r_script_raises_when_script_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "C:/fake/Rscript.exe")
    with pytest.raises(FileNotFoundError):
        run_r_script("does_not_exist.R", [])


def test_rscript_available_returns_bool():
    assert isinstance(rscript_available(), bool)
