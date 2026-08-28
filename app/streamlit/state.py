"""Shared Streamlit session state for the OmicsFusion GUI.

All pages read/write the same :class:`ProjectState` object stored in
``st.session_state`` so that data uploaded on one page is available on the
next without re-uploading.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from omicsfusion.core.config import AnalysisConfig, InputsConfig, ProjectConfig, ProjectMeta
from omicsfusion.core.dataset import Dataset


@dataclass
class ProjectState:
    config: ProjectConfig
    datasets: dict[str, Dataset] = field(default_factory=dict)
    metadata: pd.DataFrame | None = None
    metadata_path: str | None = None
    dataset_paths: dict[str, str] = field(default_factory=dict)


def _default_config() -> ProjectConfig:
    return ProjectConfig(
        project=ProjectMeta(name="untitled_project"),
        inputs=InputsConfig(metadata="metadata.csv"),
        analysis=AnalysisConfig(),
        outdir="results",
    )


def get_project_state() -> ProjectState:
    if "project_state" not in st.session_state:
        st.session_state["project_state"] = ProjectState(config=_default_config())
    return st.session_state["project_state"]
