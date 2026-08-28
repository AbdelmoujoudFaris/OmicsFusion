"""OmicsFusion command-line interface (spec section 24).

Each subcommand (``qc``, ``normalize``, ``differential``, ``integrate``,
``ml``) runs that single stage a-la-carte from a project config, useful for
debugging or Nextflow module wrapping. ``run`` executes the full pipeline
in ``core.pipeline.run_pipeline`` and always produces the HTML report.
``report`` is an alias for ``run`` in the pure-Python path (there is no
partial-state cache outside of Nextflow's own resume mechanism — see
docs/workflows.md).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from omicsfusion import __version__
from omicsfusion.core.config import ProjectConfig
from omicsfusion.core.logging_config import setup_logging
from omicsfusion.core.pipeline import run_pipeline
from omicsfusion.integration.methods import early_integration, pca_consensus_integration
from omicsfusion.machine_learning.models import run_ml
from omicsfusion.metadata.validator import validate_metadata
from omicsfusion.normalization.normalize import normalize_dataset
from omicsfusion.qc.common import run_qc
from omicsfusion.statistics.differential import differential_analysis
from omicsfusion.validation.builders import load_metadata_table, load_project_datasets

console = Console()


@click.group()
@click.version_option(__version__, prog_name="omicsfusion")
@click.option("--log-level", default="INFO", show_default=True)
def cli(log_level: str) -> None:
    """OmicsFusion: modular multi-omics analysis and integration."""
    setup_logging(level=log_level)


@cli.command()
@click.argument("target_dir", type=click.Path(file_okay=False), default=".")
@click.option("--name", default="my_multiomics_project", show_default=True)
def init(target_dir: str, name: str) -> None:
    """Scaffold a new project.yaml in TARGET_DIR."""
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    config_path = target / "project.yaml"
    if config_path.exists():
        console.print(
            f"[yellow]{config_path} already exists; not overwriting.[/yellow]"
        )
        sys.exit(1)

    template = ProjectConfig(
        project={"name": name, "organism": "human"},
        inputs={
            "transcriptomics": "data/rna.csv",
            "proteomics": "data/proteomics.csv",
            "metabolomics": "data/metabolomics.csv",
            "metadata": "data/metadata.csv",
        },
        analysis={"differential": {"condition": "condition", "reference": "control"}},
        outdir="results",
    )
    template.to_yaml(config_path)
    console.print(
        f"[green]Created {config_path}[/green]. Edit the input paths, then run:"
    )
    console.print(f"  omicsfusion validate --config {config_path}")


@cli.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def validate(config_path: str) -> None:
    """Load inputs and validate metadata consistency, without running analysis."""
    config = ProjectConfig.from_yaml(config_path)
    datasets = load_project_datasets(config)
    metadata = load_metadata_table(config)
    report = validate_metadata(metadata, datasets)

    table = Table(title="Metadata validation")
    table.add_column("Check")
    table.add_column("Result")
    table.add_row("Metadata samples", str(report.n_metadata_samples))
    for modality, n in report.n_omics_samples.items():
        table.add_row(f"{modality} samples", str(n))
    table.add_row("Errors", str(len(report.errors)))
    table.add_row("Warnings", str(len(report.warnings)))
    console.print(table)

    for e in report.errors:
        console.print(f"[red]ERROR:[/red] {e}")
    for w in report.warnings:
        console.print(f"[yellow]WARNING:[/yellow] {w}")

    sys.exit(0 if report.is_valid else 1)


@cli.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def qc(config_path: str) -> None:
    """Run quality control on every configured omics dataset."""
    config = ProjectConfig.from_yaml(config_path)
    datasets = load_project_datasets(config)
    outdir = Path(config.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for modality, dataset in datasets.items():
        result = run_qc(dataset)
        out_path = outdir / f"qc_{modality}.json"
        out_path.write_text(
            json.dumps(result.to_dict(), indent=2, default=str), encoding="utf-8"
        )
        console.print(
            f"[bold]{modality}[/bold]: {result.n_features}x{result.n_samples}, "
            f"missing={result.missing_fraction:.1%}, warnings={len(result.warnings)} -> {out_path}"
        )


@cli.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def normalize(config_path: str) -> None:
    """Normalize every configured omics dataset per the config."""
    config = ProjectConfig.from_yaml(config_path)
    datasets = load_project_datasets(config)
    outdir = Path(config.outdir) / "normalized"
    outdir.mkdir(parents=True, exist_ok=True)
    norm_config = config.analysis.normalization.model_dump()

    for modality, dataset in datasets.items():
        method = norm_config.get(modality, "none")
        normalized = normalize_dataset(dataset, method)
        out_path = outdir / f"{modality}.csv"
        normalized.matrix.to_csv(out_path)
        console.print(
            f"[bold]{modality}[/bold]: normalized with '{method}' -> {out_path}"
        )


@cli.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def differential(config_path: str) -> None:
    """Run differential analysis for every omics dataset per the config."""
    config = ProjectConfig.from_yaml(config_path)
    if not config.analysis.differential:
        console.print("[red]No 'analysis.differential' section in config.[/red]")
        sys.exit(1)
    diff_cfg = config.analysis.differential
    datasets = load_project_datasets(config)
    metadata = load_metadata_table(config)
    outdir = Path(config.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    norm_config = config.analysis.normalization.model_dump()

    for modality, dataset in datasets.items():
        normalized = normalize_dataset(dataset, norm_config.get(modality, "none"))
        group = diff_cfg.group
        if group is None:
            levels = [
                lvl
                for lvl in metadata[diff_cfg.condition].dropna().unique()
                if lvl != diff_cfg.reference
            ]
            if not levels:
                console.print(
                    f"[yellow]{modality}: no comparison level found, skipping.[/yellow]"
                )
                continue
            group = levels[0]
        try:
            result = differential_analysis(
                normalized,
                metadata,
                diff_cfg.condition,
                group,
                diff_cfg.reference,
                correction=diff_cfg.correction,
            )
        except ValueError as exc:
            console.print(f"[yellow]{modality}: {exc}[/yellow]")
            continue
        out_path = outdir / f"differential_{modality}.csv"
        result.table.to_csv(out_path, index=False)
        n_sig = len(result.significant(diff_cfg.alpha))
        console.print(
            f"[bold]{modality}[/bold]: {group} vs {diff_cfg.reference}, "
            f"{n_sig} significant features -> {out_path}"
        )


@cli.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def integrate(config_path: str) -> None:
    """Run configured multi-omics integration methods."""
    config = ProjectConfig.from_yaml(config_path)
    datasets = load_project_datasets(config)
    norm_config = config.analysis.normalization.model_dump()
    normalized = {
        m: normalize_dataset(ds, norm_config.get(m, "none"))
        for m, ds in datasets.items()
    }
    outdir = Path(config.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for method in config.analysis.integration.methods:
        if method == "early_concat":
            result = early_integration(normalized)
        elif method == "pca_consensus":
            result = pca_consensus_integration(normalized)
        else:
            console.print(
                f"[yellow]{method}: requires the R bridge, see docs/integration.md.[/yellow]"
            )
            continue
        out_path = outdir / f"integration_{method}.csv"
        result.combined.to_csv(out_path)
        console.print(
            f"[bold]{method}[/bold]: {result.combined.shape[0]}x{result.combined.shape[1]} -> {out_path}"
        )


@cli.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def ml(config_path: str) -> None:
    """Train and evaluate configured machine learning models."""
    config = ProjectConfig.from_yaml(config_path)
    ml_cfg = config.analysis.machine_learning
    if not ml_cfg.enabled:
        console.print(
            "[red]analysis.machine_learning.enabled is false in config.[/red]"
        )
        sys.exit(1)

    datasets = load_project_datasets(config)
    metadata = load_metadata_table(config)
    norm_config = config.analysis.normalization.model_dump()
    normalized = {
        m: normalize_dataset(ds, norm_config.get(m, "none"))
        for m, ds in datasets.items()
    }

    X = (
        early_integration(normalized).combined
        if len(normalized) >= 2
        else next(iter(normalized.values())).matrix.T
    )
    sample_id_col = (
        "sample_id" if "sample_id" in metadata.columns else metadata.columns[0]
    )
    meta_indexed = metadata.set_index(sample_id_col)
    y = meta_indexed[ml_cfg.target].reindex(X.index)

    result = run_ml(
        X,
        y,
        task=ml_cfg.task,
        models=ml_cfg.models,
        cv_folds=ml_cfg.cv_folds,
        test_size=ml_cfg.test_size,
        random_state=ml_cfg.random_state,
    )

    table = Table(title=f"ML results ({ml_cfg.task}, target={ml_cfg.target})")
    table.add_column("Model")
    table.add_column("Test metrics")
    for r in result.results:
        table.add_row(
            r.model, json.dumps({k: round(v, 3) for k, v in r.test_metrics.items()})
        )
    console.print(table)


@cli.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def report(config_path: str) -> None:
    """Run the full pipeline and (re)generate the HTML report."""
    config = ProjectConfig.from_yaml(config_path)
    summary = run_pipeline(config, config_path=config_path)
    console.print(f"[green]Report generated:[/green] {summary['report']}")


@cli.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def run(config_path: str) -> None:
    """Run the full OmicsFusion pipeline end-to-end."""
    config = ProjectConfig.from_yaml(config_path)
    console.rule(f"[bold]OmicsFusion — {config.project.name}[/bold]")
    try:
        summary = run_pipeline(config, config_path=config_path)
    # CLI boundary: report cleanly instead of a raw traceback.
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Pipeline failed:[/red] {exc}")
        sys.exit(1)

    table = Table(title="Run summary")
    table.add_column("Stage")
    table.add_column("Status")
    for stage in summary["stages"]:
        table.add_row(stage, "[green]done[/green]")
    console.print(table)
    console.print(f"[green]Report:[/green] {summary['report']}")


if __name__ == "__main__":
    cli()
