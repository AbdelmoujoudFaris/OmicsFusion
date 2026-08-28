"""Molecular network construction and export (spec section 20).

Builds a NetworkX graph from a :class:`~omicsfusion.statistics.correlation.CorrelationResult`,
thresholded on adjusted significance and minimum absolute correlation so the
network reflects statistically supported relationships rather than every
pairwise value.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from omicsfusion.core.logging_config import get_logger
from omicsfusion.statistics.correlation import CorrelationResult

logger = get_logger("networks.builder")


def build_correlation_network(
    result: CorrelationResult, alpha: float = 0.05, min_abs_correlation: float = 0.5
) -> nx.Graph:
    graph = nx.Graph()
    sig = result.table[
        (result.table["adjusted_p_value"] < alpha)
        & (result.table["correlation"].abs() >= min_abs_correlation)
    ]

    for _, row in sig.iterrows():
        node_a = f"{result.modality_a}::{row['feature_a']}"
        node_b = f"{result.modality_b}::{row['feature_b']}"
        graph.add_node(node_a, modality=result.modality_a)
        graph.add_node(node_b, modality=result.modality_b)
        graph.add_edge(
            node_a,
            node_b,
            weight=float(abs(row["correlation"])),
            correlation=float(row["correlation"]),
            adjusted_p_value=float(row["adjusted_p_value"]),
        )

    logger.info(
        "Correlation network: %d nodes, %d edges (alpha=%s, |r|>=%s)",
        graph.number_of_nodes(),
        graph.number_of_edges(),
        alpha,
        min_abs_correlation,
    )
    return graph


def export_network(graph: nx.Graph, path: str | Path, fmt: str = "graphml") -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "graphml":
        nx.write_graphml(graph, path)
    elif fmt == "gexf":
        nx.write_gexf(graph, path)
    elif fmt == "csv":
        import csv

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["source", "target", "correlation", "adjusted_p_value"])
            for u, v, data in graph.edges(data=True):
                writer.writerow(
                    [u, v, data.get("correlation"), data.get("adjusted_p_value")]
                )
    else:
        raise ValueError(
            f"Unknown network export format '{fmt}'. Use graphml, gexf, or csv."
        )

    logger.info("Exported network to %s (%s)", path, fmt)
