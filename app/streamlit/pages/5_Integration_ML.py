from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from state import get_project_state  # noqa: E402

from omicsfusion.integration.methods import early_integration, pca_consensus_integration
from omicsfusion.machine_learning.models import run_ml
from omicsfusion.normalization.normalize import normalize_dataset
from omicsfusion.visualization.plots import plot_feature_importance, plot_pca

st.set_page_config(page_title="Integration & ML — OmicsFusion", page_icon="🧩", layout="wide")
st.title("🧩 Multi-Omics Integration & Machine Learning")

state = get_project_state()

if len(state.datasets) < 2:
    st.warning("Upload at least 2 omics datasets to run integration.")
    st.stop()

normalized = {
    m: normalize_dataset(ds, getattr(state.config.analysis.normalization, m, "none"))
    for m, ds in state.datasets.items()
}

st.header("Integration")
method = st.radio(
    "Integration method",
    ["early_concat", "pca_consensus"],
    format_func=lambda m: {"early_concat": "Early integration (scaled concatenation)",
                            "pca_consensus": "PCA consensus (intermediate integration)"}[m],
)
state.config.analysis.integration.methods = [method]

try:
    result = early_integration(normalized) if method == "early_concat" else pca_consensus_integration(normalized)
    st.success(f"{result.combined.shape[0]} samples x {result.combined.shape[1]} combined features")
    if method == "pca_consensus":
        pc_cols = [c for c in result.combined.columns if c.endswith("PC1") or c.endswith("PC2")]
        if len(pc_cols) >= 2:
            fig = plot_pca(result.combined[pc_cols[:2]], title="Integrated PCA (first modality PCs)")
            st.plotly_chart(fig, use_container_width=True)
    st.dataframe(result.combined.head(20), use_container_width=True)
    st.download_button(
        "Download combined matrix (CSV)", result.combined.to_csv(), file_name=f"integration_{method}.csv"
    )
except ValueError as exc:
    st.error(str(exc))
    result = None

st.divider()
st.header("Machine Learning")

if state.metadata is None:
    st.info("Upload metadata to enable ML target selection.")
    st.stop()

sample_id_col = "sample_id" if "sample_id" in state.metadata.columns else state.metadata.columns[0]
candidate_targets = [c for c in state.metadata.columns if c != sample_id_col]
target = st.selectbox("Target variable", candidate_targets)
task = st.radio("Task", ["classification", "regression"])
models = st.multiselect(
    "Models", ["random_forest", "elastic_net", "logistic_regression", "svm"], default=["random_forest"]
)
cv_folds = st.slider("CV folds", 2, 10, 5)

if st.button("Train models") and result is not None and models:
    meta_indexed = state.metadata.set_index(sample_id_col)
    y = meta_indexed[target].reindex(result.combined.index)
    try:
        ml_result = run_ml(result.combined, y, task=task, models=models, cv_folds=cv_folds)
        for model_result in ml_result.results:
            st.subheader(model_result.model)
            st.json(model_result.test_metrics)
            if model_result.feature_importance is not None:
                fig = plot_feature_importance(model_result.feature_importance, title=f"{model_result.model} feature importance")
                st.plotly_chart(fig, use_container_width=True)
    except ValueError as exc:
        st.error(str(exc))
