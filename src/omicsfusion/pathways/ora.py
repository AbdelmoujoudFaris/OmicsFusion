"""Over-representation analysis against user-supplied gene/feature sets.

Spec section 17 explicitly requires *not* hard-coding external database
content (GO/KEGG/Reactome/HMDB). This module implements the statistical
engine — the hypergeometric test with multiple-testing correction — against
any gene-set collection the user supplies in the standard ``.gmt`` format
(one set per line: ``name<TAB>description<TAB>member1<TAB>member2...``),
which is exactly what MSigDB, Enrichr, and most pathway databases export.
Point it at a locally downloaded GO/KEGG/Reactome ``.gmt`` file to run a
real enrichment; no network access or embedded database is required.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from omicsfusion.core.logging_config import get_logger

logger = get_logger("pathways.ora")


@dataclass
class EnrichmentResult:
    table: (
        pd.DataFrame
    )  # term, overlap, term_size, query_size, p_value, adjusted_p_value, genes

    def significant(self, alpha: float = 0.05) -> pd.DataFrame:
        return self.table[self.table["adjusted_p_value"] < alpha].sort_values(
            "adjusted_p_value"
        )


def load_gmt(path: str | Path) -> dict[str, set[str]]:
    """Parse a ``.gmt`` gene-set file into ``{term_name: {members...}}``."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Gene-set file not found: {path}")

    gene_sets: dict[str, set[str]] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            name, _description, *members = parts
            gene_sets[name] = {m.strip() for m in members if m.strip()}
    if not gene_sets:
        raise ValueError(f"No valid gene sets parsed from {path}")
    return gene_sets


def over_representation_analysis(
    query_features: list[str],
    gene_sets: dict[str, set[str]],
    background: set[str] | None = None,
    correction: str = "fdr_bh",
    min_term_size: int = 3,
) -> EnrichmentResult:
    """Hypergeometric over-representation test of ``query_features`` against ``gene_sets``.

    ``background`` should be every feature that was measurable/testable in
    the assay (e.g. all detected genes), not the whole genome — using the
    wrong background is the single most common ORA mistake and inflates
    significance.
    """
    query = set(query_features)
    if not query:
        raise ValueError("query_features is empty.")

    if background is None:
        background = set().union(*gene_sets.values()) | query
        logger.warning(
            "No background provided; using the union of all gene-set members plus the "
            "query as background. Supply the actual assay background for valid p-values."
        )
    N = len(background)
    query = query & background

    rows = []
    for term, members in gene_sets.items():
        term_in_bg = members & background
        K = len(term_in_bg)
        if K < min_term_size:
            continue
        overlap = query & term_in_bg
        k = len(overlap)
        n = len(query)
        if k == 0:
            continue
        # Hypergeometric survival function: P(X >= k)
        p_value = stats.hypergeom.sf(k - 1, N, K, n)
        rows.append(
            {
                "term": term,
                "overlap": k,
                "term_size": K,
                "query_size": n,
                "background_size": N,
                "p_value": p_value,
                "genes": ",".join(sorted(overlap)),
            }
        )

    if not rows:
        raise ValueError("No gene sets met min_term_size and had a non-zero overlap.")

    table = pd.DataFrame(rows)
    _, adj_p, _, _ = multipletests(table["p_value"].to_numpy(), method=correction)
    table["adjusted_p_value"] = adj_p
    table = table.sort_values("p_value").reset_index(drop=True)

    logger.info(
        "ORA: %d terms tested, %d significant (FDR<0.05)",
        len(table),
        int((table["adjusted_p_value"] < 0.05).sum()),
    )
    return EnrichmentResult(table=table)
