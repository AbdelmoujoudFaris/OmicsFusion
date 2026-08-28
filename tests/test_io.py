import pandas as pd

from omicsfusion.io.loaders import (
    detect_id_columns,
    detect_matrix_orientation,
    load_table,
    sniff_modality,
)


def test_load_table_csv_sets_index(tmp_path):
    path = tmp_path / "genes.csv"
    pd.DataFrame({"gene_id": ["A", "B"], "S1": [1, 2], "S2": [3, 4]}).to_csv(
        path, index=False
    )
    df = load_table(path)
    assert df.index.name == "gene_id"
    assert list(df.columns) == ["S1", "S2"]


def test_load_table_tsv(tmp_path):
    path = tmp_path / "genes.tsv"
    pd.DataFrame({"gene_id": ["A", "B"], "S1": [1, 2]}).to_csv(
        path, sep="\t", index=False
    )
    df = load_table(path)
    assert df.shape == (2, 1)


def test_load_table_unsupported_extension(tmp_path):
    path = tmp_path / "genes.bad"
    path.write_text("nonsense")
    try:
        load_table(path)
        assert False, "should have raised"
    except ValueError:
        pass


def test_load_table_missing_file(tmp_path):
    try:
        load_table(tmp_path / "missing.csv")
        assert False, "should have raised"
    except FileNotFoundError:
        pass


def test_detect_matrix_orientation_features_as_rows():
    df = pd.DataFrame({"S1": range(100), "S2": range(100)})
    assert detect_matrix_orientation(df) == "features_as_rows"


def test_detect_matrix_orientation_features_as_columns():
    df = pd.DataFrame({f"gene_{i}": [1, 2, 3] for i in range(100)})
    assert detect_matrix_orientation(df) == "features_as_columns"


def test_sniff_modality_from_filename(tmp_path):
    path = tmp_path / "rnaseq_counts.csv"
    assert sniff_modality(path) == "transcriptomics"


def test_sniff_modality_unknown(tmp_path):
    path = tmp_path / "unrelated_file_xyz.csv"
    assert sniff_modality(path) is None


def test_detect_id_columns():
    df = pd.DataFrame(
        {
            "sample_id": ["a", "b", "c"],
            "condition": ["x", "x", "y"],
            "age": [1.0, 2.0, 3.0],
        }
    )
    kinds = detect_id_columns(df)
    assert kinds["identifier"] == ["sample_id"]
    assert kinds["categorical"] == ["condition"]
    assert kinds["numeric"] == ["age"]
