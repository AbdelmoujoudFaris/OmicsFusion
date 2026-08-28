import pytest

from omicsfusion.pathways.ora import load_gmt, over_representation_analysis


def test_load_gmt(tmp_path):
    gmt = tmp_path / "sets.gmt"
    gmt.write_text("SET_A\tdesc\tg1\tg2\tg3\nSET_B\tdesc\tg4\tg5\n")
    gene_sets = load_gmt(gmt)
    assert gene_sets["SET_A"] == {"g1", "g2", "g3"}
    assert gene_sets["SET_B"] == {"g4", "g5"}


def test_load_gmt_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_gmt(tmp_path / "missing.gmt")


def test_ora_finds_enriched_term():
    gene_sets = {
        "SIGNAL": {f"g{i}" for i in range(10)},
        "NOISE": {f"n{i}" for i in range(10)},
    }
    background = (
        {f"g{i}" for i in range(10)}
        | {f"n{i}" for i in range(10)}
        | {f"x{i}" for i in range(80)}
    )
    query = [f"g{i}" for i in range(8)]  # strong overlap with SIGNAL, none with NOISE

    result = over_representation_analysis(
        query, gene_sets, background=background, min_term_size=3
    )
    top = result.table.iloc[0]
    assert top["term"] == "SIGNAL"
    assert top["adjusted_p_value"] < 0.05


def test_ora_empty_query_raises():
    with pytest.raises(ValueError, match="empty"):
        over_representation_analysis([], {"A": {"g1"}})
