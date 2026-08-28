from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from state import get_project_state  # noqa: E402

from omicsfusion.core.config import DifferentialConfig
from omicsfusion.metadata.validator import validate_metadata

st.set_page_config(page_title="Metadata — OmicsFusion", page_icon="🗂️", layout="wide")
st.title("🗂️ Metadata")

state = get_project_state()

if state.metadata is None:
    st.warning("Upload a metadata file on the **Upload Data** page first.")
    st.stop()

st.dataframe(state.metadata, use_container_width=True)

st.subheader("Consistency checks")
report = validate_metadata(state.metadata, state.datasets)

col1, col2, col3 = st.columns(3)
col1.metric("Metadata samples", report.n_metadata_samples)
col2.metric("Errors", len(report.errors))
col3.metric("Warnings", len(report.warnings))

if report.errors:
    st.error("Errors found:")
    for e in report.errors:
        st.write(f"- {e}")
if report.warnings:
    st.warning("Warnings:")
    for w in report.warnings:
        st.write(f"- {w}")
if report.is_valid and not report.warnings:
    st.success("Metadata is consistent with all loaded omics datasets.")

st.subheader("Differential comparison")
if report.categorical_columns:
    condition_col = st.selectbox("Condition column", report.categorical_columns)
    levels = sorted(state.metadata[condition_col].dropna().unique().tolist())
    if len(levels) >= 2:
        reference = st.selectbox("Reference level", levels, index=0)
        group = st.selectbox("Comparison level", [l for l in levels if l != reference], index=0)
        if st.button("Save as differential configuration"):
            state.config.analysis.differential = DifferentialConfig(
                condition=condition_col, reference=reference, group=group,
            )
            st.success(f"Configured: {group} vs {reference} on '{condition_col}'")
else:
    st.info("No categorical columns detected in metadata for a differential comparison.")
