from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from state import get_project_state  # noqa: E402

from omicsfusion.io.loaders import sniff_modality
from omicsfusion.validation.builders import build_dataset

st.set_page_config(page_title="Upload Data — OmicsFusion", page_icon="📤", layout="wide")
st.title("📤 Upload Data")

state = get_project_state()
upload_dir = Path(tempfile.gettempdir()) / "omicsfusion_gui_uploads"
upload_dir.mkdir(exist_ok=True)

MODALITIES = [
    "transcriptomics", "proteomics", "metabolomics", "metagenomics",
    "microbiome", "epigenomics", "lipidomics", "clinical",
]

st.markdown(
    "Upload one file per omics layer. Supported formats: CSV, TSV, TXT, XLSX, Parquet. "
    "The app guesses the omics type from the filename — confirm or correct it before loading."
)

uploaded = st.file_uploader(
    "Omics data file(s)", type=["csv", "tsv", "txt", "xlsx", "parquet"], accept_multiple_files=True
)

if uploaded:
    for file in uploaded:
        guess = sniff_modality(file.name) or "transcriptomics"
        cols = st.columns([3, 2, 1])
        cols[0].write(f"**{file.name}**")
        modality = cols[1].selectbox(
            f"Modality for {file.name}", MODALITIES, index=MODALITIES.index(guess), key=f"mod_{file.name}"
        )
        if cols[2].button("Load", key=f"load_{file.name}"):
            dest = upload_dir / file.name
            dest.write_bytes(file.getvalue())
            try:
                dataset = build_dataset(str(dest), modality)
                state.datasets[modality] = dataset
                state.dataset_paths[modality] = str(dest)
                setattr(state.config.inputs, modality, str(dest))
                st.success(f"Loaded {modality}: {dataset.n_features} features x {dataset.n_samples} samples")
            except ValueError as exc:
                st.error(f"Could not load {file.name}: {exc}")

st.subheader("Metadata")
metadata_file = st.file_uploader("Sample metadata file", type=["csv", "tsv", "txt", "xlsx"], key="metadata")
if metadata_file is not None:
    dest = upload_dir / metadata_file.name
    dest.write_bytes(metadata_file.getvalue())
    from omicsfusion.io.loaders import load_table

    df = load_table(dest)
    if df.index.name is not None:
        df = df.reset_index()
    state.metadata = df
    state.metadata_path = str(dest)
    state.config.inputs.metadata = str(dest)
    st.success(f"Loaded metadata: {df.shape[0]} samples x {df.shape[1]} columns")
    st.dataframe(df.head(10))

if state.datasets:
    st.subheader("Loaded datasets")
    for modality, ds in state.datasets.items():
        st.write(f"- **{modality}**: {ds.n_features} features x {ds.n_samples} samples ({ds.info.source})")
