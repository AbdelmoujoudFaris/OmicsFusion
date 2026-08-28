"""Feature annotation via configurable, cached lookups (spec section 17).

No external database content (HMDB, KEGG, Ensembl, UniProt, ...) is
embedded in this repository. Instead, :class:`LocalMappingClient` loads a
user-supplied identifier-mapping table (a two-column TSV/CSV the user
exports from HMDB/Ensembl/UniProt/etc., or that a lab already maintains)
and caches lookups in memory and, optionally, on disk via
:class:`AnnotationCache`. This keeps the platform usable offline and avoids
redistributing licensed database content, while still giving a real,
working annotation path rather than a stub.

To add a live API-backed client (e.g. querying the HMDB or KEGG REST APIs),
implement :class:`AnnotationClient` and use :class:`AnnotationCache` to
avoid refetching the same identifier across runs.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from omicsfusion.core.logging_config import get_logger

logger = get_logger("annotation.clients")


class AnnotationCache:
    """A simple JSON-backed cache mapping identifier -> annotation dict."""

    def __init__(self, cache_path: str | Path | None = None):
        self.cache_path = Path(cache_path) if cache_path else None
        self._store: dict[str, dict] = {}
        if self.cache_path and self.cache_path.exists():
            self._store = json.loads(self.cache_path.read_text(encoding="utf-8"))

    def get(self, key: str) -> dict | None:
        return self._store.get(key)

    def set(self, key: str, value: dict) -> None:
        self._store[key] = value

    def save(self) -> None:
        if self.cache_path is None:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self._store, indent=2), encoding="utf-8")

    def __contains__(self, key: str) -> bool:
        return key in self._store


class AnnotationClient(ABC):
    """Interface for a feature annotation source (local table or live API)."""

    @abstractmethod
    def annotate(self, feature_id: str) -> dict | None:
        """Return an annotation dict for one feature ID, or None if unknown."""

    def annotate_many(self, feature_ids: list[str]) -> pd.DataFrame:
        rows = []
        for fid in feature_ids:
            annotation = self.annotate(fid) or {}
            rows.append({"feature_id": fid, **annotation})
        return pd.DataFrame(rows).set_index("feature_id")


class LocalMappingClient(AnnotationClient):
    """Annotate features using a user-provided identifier-mapping table.

    The table must have the feature ID as its first column; every other
    column becomes an annotation field (e.g. gene_symbol, description,
    pathway, hmdb_id, kegg_id).
    """

    def __init__(self, mapping_path: str | Path, cache: AnnotationCache | None = None):
        mapping_path = Path(mapping_path)
        if not mapping_path.exists():
            raise FileNotFoundError(
                f"Annotation mapping file not found: {mapping_path}"
            )

        sep = "\t" if mapping_path.suffix.lower() in (".tsv", ".txt") else ","
        df = pd.read_csv(mapping_path, sep=sep, dtype=str)
        id_col = df.columns[0]
        self._mapping = df.set_index(id_col).to_dict(orient="index")
        self.cache = cache or AnnotationCache()
        logger.info(
            "Loaded %d annotation records from %s", len(self._mapping), mapping_path
        )

    def annotate(self, feature_id: str) -> dict | None:
        if feature_id in self.cache:
            return self.cache.get(feature_id)
        record = self._mapping.get(feature_id)
        if record is not None:
            self.cache.set(feature_id, record)
        return record
