from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from state import get_project_state  # noqa: E402

from omicsfusion.normalization.normalize import METHOD_RATIONALE, normalize_dataset
from omicsfusion.qc.common import run_qc
from omicsfusion.visualization.plots import plot_correlation_heatmap, plot_pca

st.set_page_config(page_title="QC & Normalization — OmicsFusion", page_icon="🔬", layout="wide")
st.title("🔬 Quality Control & Normalization")

state = get_project_state()

if not state.datasets:
    st.warning("Upload at least one omics dataset on the **Upload Data** page first.")
    st.stop()

norm_config = state.config.analysis.normalization

for modality, dataset in state.datasets.items():
    st.header(modality)
    qc = run_qc(dataset)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Features", qc.n_features)
    c2.metric("Samples", qc.n_samples)
    c3.metric("Missing", f"{qc.missing_fraction:.1%}")
    c4.metric("Warnings", len(qc.warnings))

    for w in qc.warnings:
        st.warning(w)

    if qc.pca_scores is not None:
        color_by = None
        if state.metadata is not None and state.config.analysis.differential:
            cond = state.config.analysis.differential.condition
            if cond in state.metadata.columns:
                id_col = "sample_id" if "sample_id" in state.metadata.columns else state.metadata.columns[0]
                color_by = state.metadata.set_index(id_col)[cond]
        fig = plot_pca(qc.pca_scores, qc.pca_variance_ratio, color_by, title=f"{modality} PCA")
        st.plotly_chart(fig, use_container_width=True)

    if qc.sample_correlation is not None:
        fig = plot_correlation_heatmap(qc.sample_correlation, title=f"{modality} sample correlation")
        st.plotly_chart(fig, use_container_width=True)

    method = st.selectbox(
        f"Normalization method for {modality}",
        list(METHOD_RATIONALE),
        index=list(METHOD_RATIONALE).index(getattr(norm_config, modality, "none")),
        key=f"norm_{modality}",
    )
    st.caption(METHOD_RATIONALE[method])
    setattr(norm_config, modality, method)
    st.divider()
