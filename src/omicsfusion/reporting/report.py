"""Reproducible HTML report generation (spec section 28).

A report is assembled section-by-section from whatever a run actually
produced — a section is included only if that stage ran, so a report never
implies an analysis happened when it did not. Sections embed Plotly figures
as self-contained HTML fragments (no external file dependency) so the
report is a single portable file.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape

from omicsfusion.core.logging_config import get_logger
from omicsfusion.core.versions import collect_versions

logger = get_logger("reporting.report")

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_ANCHOR_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class _Section:
    title: str
    anchor: str
    html: str


@dataclass
class ReportBuilder:
    project_name: str
    sections: list[_Section] = field(default_factory=list)

    def _anchor(self, title: str) -> str:
        return _ANCHOR_RE.sub("-", title.lower()).strip("-")

    def add_html(self, title: str, html: str) -> None:
        self.sections.append(
            _Section(title=title, anchor=self._anchor(title), html=html)
        )

    def add_text(self, title: str, paragraphs: list[str]) -> None:
        html = "".join(f"<p>{p}</p>" for p in paragraphs)
        self.add_html(title, html)

    def add_table(
        self, title: str, df: pd.DataFrame, max_rows: int = 50, note: str | None = None
    ) -> None:
        html = ""
        if note:
            html += f'<p class="muted">{note}</p>'
        if len(df) > max_rows:
            html += f'<p class="muted">Showing top {max_rows} of {len(df)} rows.</p>'
            df = df.head(max_rows)
        html += df.to_html(classes="", border=0, index=True, na_rep="—")
        self.add_html(title, html)

    def add_figure(self, title: str, fig: go.Figure) -> None:
        fragment = fig.to_html(full_html=False, include_plotlyjs="cdn")
        self.add_html(title, f'<div class="figure">{fragment}</div>')

    def add_status(self, title: str, statuses: dict[str, str]) -> None:
        """statuses: label -> one of 'ok', 'warn', 'error', 'pending'."""
        items = []
        for label, status in statuses.items():
            css = status if status in ("ok", "warn", "error") else "warn"
            symbol = {
                "ok": "done",
                "warn": "attention",
                "error": "failed",
                "pending": "pending",
            }.get(status, status)
            items.append(f'<li>{label}: <span class="badge {css}">{symbol}</span></li>')
        self.add_html(title, f'<ul class="plain">{"".join(items)}</ul>')

    def add_reproducibility_section(self) -> None:
        versions = collect_versions()
        rows = "".join(
            f"<tr><td>{k}</td><td><code>{v}</code></td></tr>"
            for k, v in versions.items()
        )
        html = f"<table><thead><tr><th>Component</th><th>Version</th></tr></thead><tbody>{rows}</tbody></table>"
        self.add_html("Reproducibility", html)

    def render(self, output_path: str | Path) -> Path:
        env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        template = env.get_template("report.html.j2")
        rendered = template.render(
            project_name=self.project_name,
            generated_at=dt.datetime.now()
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S %Z"),
            sections=self.sections,
        )
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        logger.info(
            "Report written to %s (%d sections)", output_path, len(self.sections)
        )
        return output_path
