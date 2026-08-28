from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from state import get_project_state  # noqa: E402

from omicsfusion.normalization.normalize import normalize_dataset
from omicsfusion.statistics.differential import differential_analysis
from omicsfusion.visualization.plots import plot_volcano

st.set_page_config(page_title="Differential Analysis — OmicsFusion", page_icon="📈", layout="wide")
st.title("📈 Differential Analysis")

state = get_project_state()

if not state.datasets or state.metadata is None:
    st.warning("Upload data and metadata first (Upload Data page).")
    st.stop()

diff_cfg = state.config.analysis.differential
if diff_cfg is None:
    st.warning("Configure a condition/reference/group comparison on the **Metadata** page first.")
    st.stop()

st.info(f"Comparing **{diff_cfg.group}** vs **{diff_cfg.reference}** on column `{diff_cfg.condition}`")
alpha = st.slider("Significance threshold (adjusted p-value)", 0.001, 0.25, diff_cfg.alpha, step=0.005)

for modality, dataset in state.datasets.items():
    st.header(modality)
    method = getattr(state.config.analysis.normalization, modality, "none")
    normalized = normalize_dataset(dataset, method)
    try:
        result = differential_analysis(
            normalized, state.metadata, diff_cfg.condition, diff_cfg.group, diff_cfg.reference,
            correction=diff_cfg.correction,
        )
    except ValueError as exc:
        st.error(f"{modality}: {exc}")
        continue

    sig = result.significant(alpha)
    st.metric("Significant features", len(sig))
    fig = plot_volcano(result.table, alpha=alpha, title=f"{modality}: {diff_cfg.group} vs {diff_cfg.reference}")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sig.sort_values("adjusted_p_value").head(50), use_container_width=True)
    st.download_button(
        f"Download full {modality} results (CSV)",
        result.table.to_csv(index=False),
        file_name=f"differential_{modality}.csv",
        mime="text/csv",
    )
