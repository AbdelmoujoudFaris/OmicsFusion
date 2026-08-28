import numpy as np
import pandas as pd
from click.testing import CliRunner

from omicsfusion.cli.main import cli


def _write_project(tmp_path):
    rng = np.random.default_rng(1)
    samples = [f"S{i:02d}" for i in range(1, 17)]
    groups = ["treated"] * 8 + ["control"] * 8

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    rna = pd.DataFrame(
        rng.normal(20, 3, size=(30, 16)),
        index=[f"gene_{i}" for i in range(30)],
        columns=samples,
    )
    rna.iloc[:5, :8] += 10  # signal in first 5 genes for treated samples
    rna.index.name = "gene_id"
    rna.to_csv(data_dir / "rna.csv")

    proteins = pd.DataFrame(
        rng.normal(15, 2, size=(20, 16)),
        index=[f"prot_{i}" for i in range(20)],
        columns=samples,
    )
    proteins.index.name = "protein_id"
    proteins.to_csv(data_dir / "proteomics.csv")

    metadata = pd.DataFrame({"sample_id": samples, "condition": groups})
    metadata.to_csv(data_dir / "metadata.csv", index=False)

    config_path = tmp_path / "project.yaml"
    config_path.write_text(
        f"""
project:
  name: cli_test_project
inputs:
  transcriptomics: {data_dir / 'rna.csv'}
  proteomics: {data_dir / 'proteomics.csv'}
  metadata: {data_dir / 'metadata.csv'}
analysis:
  differential:
    condition: condition
    reference: control
    group: treated
  integration:
    methods: [early_concat]
  machine_learning:
    enabled: true
    target: condition
    task: classification
    models: [random_forest]
    cv_folds: 3
outdir: {tmp_path / 'results'}
""",
        encoding="utf-8",
    )
    return config_path


def test_cli_validate(tmp_path):
    config_path = _write_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--config", str(config_path)])
    assert result.exit_code == 0, result.output


def test_cli_init(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path / "new_project")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "new_project" / "project.yaml").exists()


def test_cli_run_end_to_end(tmp_path):
    config_path = _write_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "results" / "report.html").exists()
    assert (tmp_path / "results" / "run_summary.json").exists()


def test_cli_qc(tmp_path):
    config_path = _write_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["qc", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "results" / "qc_transcriptomics.json").exists()
