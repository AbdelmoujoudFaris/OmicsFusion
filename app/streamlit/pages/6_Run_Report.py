from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from state import get_project_state  # noqa: E402

from omicsfusion.core.pipeline import run_pipeline

st.set_page_config(page_title="Run & Report — OmicsFusion", page_icon="🚀", layout="wide")
st.title("🚀 Run & Report")

state = get_project_state()

st.markdown(
    "This runs the exact same pipeline as `omicsfusion run --config project.yaml`, "
    "built from every choice made on the previous pages. The generated `project.yaml` "
    "is available below so this run can be reproduced from the command line."
)

if not state.config.inputs.omics_paths():
    st.warning("Upload at least one omics dataset first (Upload Data page).")
    st.stop()

outdir = st.text_input("Output directory", state.config.outdir)
state.config.outdir = outdir

config_yaml_path = Path(tempfile.gettempdir()) / "omicsfusion_gui_project.yaml"
state.config.to_yaml(config_yaml_path)

with st.expander("Generated project.yaml"):
    st.code(config_yaml_path.read_text(encoding="utf-8"), language="yaml")
    st.download_button(
        "Download project.yaml", config_yaml_path.read_text(encoding="utf-8"), file_name="project.yaml"
    )

if st.button("Run full pipeline", type="primary"):
    with st.spinner("Running OmicsFusion pipeline..."):
        try:
            summary = run_pipeline(state.config, config_path=config_yaml_path)
        except Exception as exc:  # surfaced to the user, not swallowed
            st.error(f"Pipeline failed: {exc}")
            st.stop()

    st.success("Pipeline complete.")
    st.json(summary["stages"])

    report_path = Path(summary["report"])
    if report_path.exists():
        st.download_button(
            "Download HTML report",
            report_path.read_text(encoding="utf-8"),
            file_name="report.html",
            mime="text/html",
        )
        st.components.v1.html(report_path.read_text(encoding="utf-8"), height=800, scrolling=True)
