"""End-to-end pipeline orchestration for ``omicsfusion run``.

This module is the single place that wires together I/O, metadata
validation, QC, normalisation, differential analysis, integration, ML,
pathway analysis, and reporting according to a :class:`ProjectConfig`. The
CLI's individual subcommands (``qc``, ``normalize``, ...) call the same
underlying module functions directly for a-la-carte use; ``run`` calls this
orchestrator for the full pipeline described in spec section 1.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from omicsfusion.core.config import ProjectConfig
from omicsfusion.core.dataset import Dataset
from omicsfusion.core.logging_config import get_logger, setup_logging
from omicsfusion.core.versions import write_versions_file
from omicsfusion.integration.methods import early_integration, pca_consensus_integration
from omicsfusion.machine_learning.models import run_ml
from omicsfusion.metadata.validator import validate_metadata
from omicsfusion.normalization.normalize import normalize_dataset
from omicsfusion.qc.common import run_qc
from omicsfusion.reporting.report import ReportBuilder
from omicsfusion.statistics.correlation import cross_omics_correlation
from omicsfusion.statistics.differential import differential_analysis
from omicsfusion.validation.builders import load_metadata_table, load_project_datasets
from omicsfusion.visualization.plots import (
    plot_correlation_heatmap,
    plot_feature_importance,
    plot_pca,
    plot_volcano,
)

logger = get_logger("core.pipeline")


def run_pipeline(config: ProjectConfig, config_path: str | Path | None = None) -> dict:
    """Run the full OmicsFusion pipeline for one project and write results/report.

    Returns a summary dict (also used by the CLI to print a final status
    table). Failures in optional stages (integration, ML, pathways) are
    logged and recorded in the report rather than aborting the whole run,
    since a researcher may still want QC/differential results from a
    partially-configured project; failures in required stages (loading,
    metadata validation) raise.
    """
    outdir = Path(config.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    setup_logging(log_file=outdir / "omicsfusion.log")

    report = ReportBuilder(project_name=config.project.name)
    summary: dict = {"project": config.project.name, "stages": {}}

    report.add_text(
        "Project information",
        [
            f"<b>Name:</b> {config.project.name}",
            f"<b>Organism:</b> {config.project.organism or 'not specified'}",
            f"<b>Output directory:</b> <code>{outdir}</code>",
        ],
    )

    logger.info("Loading input datasets")
    datasets = load_project_datasets(config)
    metadata = load_metadata_table(config)
    report.add_text(
        "Input datasets",
        [
            f"<b>{m}</b>: {ds.n_features} features x {ds.n_samples} samples (source: {ds.info.source})"
            for m, ds in datasets.items()
        ],
    )
    summary["stages"]["input"] = {m: ds.to_summary() for m, ds in datasets.items()}

    meta_report = validate_metadata(metadata, datasets)
    report.add_status(
        "Metadata validation",
        {"overall": "ok" if meta_report.is_valid else "error"},
    )
    if meta_report.errors:
        report.add_html(
            "Metadata validation — errors",
            "<ul class='plain'>"
            + "".join(f"<li>{e}</li>" for e in meta_report.errors)
            + "</ul>",
        )
    if meta_report.warnings:
        report.add_html(
            "Metadata validation — warnings",
            "<ul class='plain'>"
            + "".join(f"<li>{w}</li>" for w in meta_report.warnings)
            + "</ul>",
        )
    summary["stages"]["metadata"] = meta_report.to_dict()
    if not meta_report.is_valid:
        raise ValueError(
            "Metadata validation failed with errors; fix the input data/metadata before "
            f"proceeding. Errors: {meta_report.errors}"
        )

    sample_id_col = (
        "sample_id" if "sample_id" in metadata.columns else metadata.columns[0]
    )
    color_by = None
    if (
        config.analysis.differential
        and config.analysis.differential.condition in metadata.columns
    ):
        meta_indexed = (
            metadata.set_index(sample_id_col)
            if sample_id_col in metadata.columns
            else metadata
        )
        color_by = meta_indexed[config.analysis.differential.condition]

    if config.analysis.qc:
        for modality, dataset in datasets.items():
            qc = run_qc(dataset)
            summary["stages"].setdefault("qc", {})[modality] = qc.to_dict()
            report.add_status(
                f"QC — {modality}", {"status": "warn" if qc.warnings else "ok"}
            )
            if qc.pca_scores is not None:
                fig = plot_pca(
                    qc.pca_scores,
                    qc.pca_variance_ratio,
                    color_by,
                    title=f"{modality} PCA",
                )
                report.add_figure(f"QC PCA — {modality}", fig)
            if qc.warnings:
                report.add_html(
                    f"QC warnings — {modality}",
                    "<ul class='plain'>"
                    + "".join(f"<li>{w}</li>" for w in qc.warnings)
                    + "</ul>",
                )

    normalized: dict[str, Dataset] = {}
    norm_config = config.analysis.normalization.model_dump()
    for modality, dataset in datasets.items():
        method = norm_config.get(modality, "none")
        normalized[modality] = normalize_dataset(dataset, method)
    report.add_text(
        "Normalization",
        [f"<b>{m}</b>: <code>{norm_config.get(m, 'none')}</code>" for m in datasets],
    )
    summary["stages"]["normalization"] = {
        m: norm_config.get(m, "none") for m in datasets
    }

    if config.analysis.differential:
        diff_cfg = config.analysis.differential
        for modality, dataset in normalized.items():
            try:
                result = differential_analysis(
                    dataset,
                    metadata,
                    condition_column=diff_cfg.condition,
                    group=(
                        _other_level(metadata, diff_cfg.condition, diff_cfg.reference)
                        if diff_cfg.group is None
                        else diff_cfg.group
                    ),
                    reference=diff_cfg.reference,
                    sample_id_column=sample_id_col,
                    correction=(
                        "fdr_bh" if diff_cfg.correction == "fdr_bh" else "bonferroni"
                    ),
                )
                out_csv = outdir / f"differential_{modality}.csv"
                result.table.to_csv(out_csv, index=False)
                fig = plot_volcano(
                    result.table,
                    alpha=diff_cfg.alpha,
                    title=f"{modality}: {result.group} vs {result.reference}",
                )
                report.add_figure(f"Differential analysis — {modality}", fig)
                report.add_table(
                    f"Top differential features — {modality}",
                    result.significant(diff_cfg.alpha),
                    note=f"{result.group} vs {result.reference}, {diff_cfg.correction}, alpha={diff_cfg.alpha}",
                )
                summary["stages"].setdefault("differential", {})[modality] = {
                    "n_significant": len(result.significant(diff_cfg.alpha))
                }
            except ValueError as exc:
                logger.warning(
                    "Differential analysis skipped for %s: %s", modality, exc
                )
                report.add_html(
                    f"Differential analysis — {modality}",
                    f"<p class='muted'>Skipped: {exc}</p>",
                )

    if len(normalized) >= 2:
        modality_pairs = list(normalized.items())
        for i in range(len(modality_pairs)):
            for j in range(i + 1, len(modality_pairs)):
                (mod_a, ds_a), (mod_b, ds_b) = modality_pairs[i], modality_pairs[j]
                try:
                    corr = cross_omics_correlation(ds_a, ds_b)
                    fig = plot_correlation_heatmap(
                        corr.table.pivot(
                            index="feature_a", columns="feature_b", values="correlation"
                        ),
                        title=f"{mod_a} vs {mod_b} correlation",
                    )
                    report.add_figure(
                        f"Cross-omics correlation — {mod_a} vs {mod_b}", fig
                    )
                    corr.table.to_csv(
                        outdir / f"correlation_{mod_a}_{mod_b}.csv", index=False
                    )
                except ValueError as exc:
                    logger.warning(
                        "Correlation skipped for %s/%s: %s", mod_a, mod_b, exc
                    )

        for method in config.analysis.integration.methods:
            try:
                if method == "early_concat":
                    integration_result = early_integration(normalized)
                elif method == "pca_consensus":
                    integration_result = pca_consensus_integration(normalized)
                else:
                    report.add_html(
                        f"Integration — {method}",
                        "<p class='muted'>This method requires the R bridge "
                        "(MOFA2/mixOmics) and is not run by the pure-Python pipeline. "
                        "See docs/integration.md.</p>",
                    )
                    continue
                integration_result.combined.to_csv(outdir / f"integration_{method}.csv")
                report.add_table(
                    f"Integration — {method}",
                    integration_result.combined,
                    note=f"{len(integration_result.samples)} samples x "
                    f"{integration_result.combined.shape[1]} combined features/components",
                )
                summary["stages"].setdefault("integration", {})[method] = {
                    "n_samples": len(integration_result.samples),
                    "n_features": integration_result.combined.shape[1],
                }
            except ValueError as exc:
                logger.warning("Integration '%s' skipped: %s", method, exc)
                report.add_html(
                    f"Integration — {method}", f"<p class='muted'>Skipped: {exc}</p>"
                )

    if config.analysis.machine_learning.enabled:
        ml_cfg = config.analysis.machine_learning
        try:
            X = (
                early_integration(normalized).combined
                if len(normalized) >= 2
                else next(iter(normalized.values())).matrix.T
            )
            meta_indexed = (
                metadata.set_index(sample_id_col)
                if sample_id_col in metadata.columns
                else metadata
            )
            y = meta_indexed[ml_cfg.target].reindex(X.index)
            ml_result = run_ml(
                X,
                y,
                task=ml_cfg.task,
                models=ml_cfg.models,
                cv_folds=ml_cfg.cv_folds,
                test_size=ml_cfg.test_size,
                random_state=ml_cfg.random_state,
            )
            for model_result in ml_result.results:
                report.add_html(
                    f"ML — {model_result.model}",
                    f"<p>Test metrics: <code>{json.dumps(model_result.test_metrics)}</code></p>"
                    f"<p>CV metrics: <code>{json.dumps(model_result.cv_metrics)}</code></p>",
                )
                if model_result.feature_importance is not None:
                    fig = plot_feature_importance(
                        model_result.feature_importance,
                        title=f"{model_result.model} feature importance",
                    )
                    report.add_figure(
                        f"ML feature importance — {model_result.model}", fig
                    )
            summary["stages"]["machine_learning"] = {
                r.model: r.test_metrics for r in ml_result.results
            }
        except (ValueError, KeyError) as exc:
            logger.warning("Machine learning skipped: %s", exc)
            report.add_html("Machine learning", f"<p class='muted'>Skipped: {exc}</p>")

    report.add_reproducibility_section()
    report_path = report.render(outdir / "report.html")
    write_versions_file(str(outdir / "software_versions.txt"))
    if config_path is not None:
        config.to_yaml(outdir / "analysis_config.yaml")

    summary["report"] = str(report_path)
    with open(outdir / "run_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    logger.info("Pipeline complete. Report: %s", report_path)
    return summary


def _other_level(metadata: pd.DataFrame, column: str, reference: str) -> str:
    """Pick the first level of ``column`` that isn't ``reference`` as the comparison group."""
    levels = [lvl for lvl in metadata[column].dropna().unique() if lvl != reference]
    if not levels:
        raise ValueError(
            f"No level of '{column}' other than reference '{reference}' found."
        )
    return levels[0]
