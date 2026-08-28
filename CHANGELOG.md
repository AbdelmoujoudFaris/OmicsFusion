# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [0.1.0] - 2026-08-28

Initial functional MVP.

### Added

- Core: `ProjectConfig` (pydantic YAML schema), `Dataset`/`DatasetInfo` unified data model, logging, software-version capture, R bridge.
- I/O: multi-format table loading (CSV/TSV/XLSX/Parquet/HDF5), matrix-orientation and modality detection.
- Metadata validation with duplicate/mismatch/batch-imbalance checks.
- QC: PCA, sample correlation, library size, coefficient of variation, outlier flagging.
- Normalization: zscore, log/log2/log10, minmax, quantile, median, VST (approx.), CLR, TMM (approx.), each with a documented rationale.
- Statistics: two-group differential analysis (t-test/Mann-Whitney, BH/Bonferroni correction), cross-omics correlation.
- Integration: early concatenation, PCA-consensus; R bridge scripts for MOFA2 and DIABLO/mixOmics.
- Machine learning: leakage-safe pipelines for random forest, elastic net, logistic regression, SVM, optional XGBoost; classification and regression.
- Pathway over-representation analysis (hypergeometric, user-supplied `.gmt`); R bridge script for fgsea/GSEA.
- Networks: correlation-graph construction and GraphML/GEXF/CSV export.
- Annotation: local mapping-table client with caching (no embedded database content).
- Visualization: PCA, volcano, correlation heatmap, boxplot, feature-importance plots (Plotly).
- Reporting: self-contained interactive HTML report.
- CLI (`omicsfusion init|validate|qc|normalize|differential|integrate|ml|report|run`).
- Streamlit GUI (Upload Data, Metadata, QC & Normalization, Differential Analysis, Integration & ML, Run & Report), config-file-driven end to end.
- Nextflow workflow (`workflows/main.nf`) wrapping the CLI, with local/docker/singularity/conda profiles.
- R bridge scripts: DESeq2, limma, MOFA2, DIABLO, fgsea, ComplexHeatmap.
- Demo dataset (synthetic 40-sample case/control multi-omics study) and full documentation set.
- Docker image, pytest suite (61 tests), CI workflows.
