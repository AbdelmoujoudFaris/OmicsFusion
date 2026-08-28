"""OmicsFusion Streamlit GUI — entry point (spec section 26).

Design principle: the GUI never analyses data directly. Every action here
edits an in-memory :class:`ProjectConfig`, and "Run analysis" serialises it
to ``project.yaml`` and calls the exact same ``run_pipeline`` the CLI uses.
This guarantees a GUI-driven run is reproducible from its config file alone,
exactly like a CLI run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))  # allow `from state import ...` in pages/

from state import get_project_state  # noqa: E402

st.set_page_config(page_title="OmicsFusion", page_icon="🧬", layout="wide")

state = get_project_state()

st.title("🧬 OmicsFusion")
st.caption("Multi-omics analysis from raw tables to integrated biological insight.")

st.markdown(
    """
Use the pages in the sidebar to work through a project:

1. **Upload Data** — provide transcriptomics/proteomics/metabolomics/... files and metadata.
2. **Metadata** — review sample metadata and consistency checks.
3. **QC & Normalization** — inspect quality metrics and choose normalization methods.
4. **Differential Analysis** — configure and run a two-group comparison.
5. **Integration & ML** — configure multi-omics integration and machine learning.
6. **Run & Report** — execute the pipeline and view/download the HTML report.

Every choice you make here is written into a `project.yaml` config file — the
same file the command line `omicsfusion run --config project.yaml` uses — so
a GUI-driven analysis is exactly as reproducible as a CLI-driven one.
"""
)

st.subheader("Current project")
col1, col2 = st.columns(2)
with col1:
    state.config.project.name = st.text_input("Project name", state.config.project.name)
with col2:
    state.config.project.organism = st.text_input("Organism", state.config.project.organism or "")

st.info(
    f"Datasets loaded: {len(state.datasets)} | "
    f"Metadata loaded: {'yes' if state.metadata is not None else 'no'}"
)
