"""Publication-quality, interactive figures (spec section 11).

Built on Plotly so every figure is interactive in the HTML report and the
Streamlit GUI, and exportable to static PNG/PDF/SVG via :func:`save_figure`
(which requires the optional ``kaleido`` package for static export — HTML
export always works with no extra dependency).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from omicsfusion.core.logging_config import get_logger

logger = get_logger("visualization.plots")

_TEMPLATE = "plotly_white"


def save_figure(fig: go.Figure, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".html":
        fig.write_html(path, include_plotlyjs="cdn")
    elif suffix in (".png", ".pdf", ".svg"):
        try:
            fig.write_image(path)
        except ValueError as exc:
            raise RuntimeError(
                f"Static export to {suffix} requires the optional 'kaleido' package "
                "(pip install kaleido)."
            ) from exc
    else:
        raise ValueError(f"Unsupported figure export format '{suffix}'.")
    logger.info("Saved figure to %s", path)


def plot_pca(
    pca_scores: pd.DataFrame,
    variance_ratio: list[float] | None = None,
    color_by: pd.Series | None = None,
    title: str = "PCA",
) -> go.Figure:
    df = pca_scores.copy()
    df["sample"] = df.index
    color = None
    if color_by is not None:
        df["group"] = color_by.reindex(df.index)
        color = "group"

    x_label = "PC1" + (f" ({variance_ratio[0]:.1%})" if variance_ratio else "")
    y_label = "PC2" + (
        f" ({variance_ratio[1]:.1%})"
        if variance_ratio and len(variance_ratio) > 1
        else ""
    )

    fig = px.scatter(
        df,
        x=df.columns[0],
        y=df.columns[1] if df.shape[1] > 2 else df.columns[0],
        color=color,
        hover_name="sample",
        title=title,
        template=_TEMPLATE,
    )
    fig.update_layout(xaxis_title=x_label, yaxis_title=y_label)
    return fig


def plot_volcano(
    table: pd.DataFrame,
    alpha: float = 0.05,
    log2fc_threshold: float = 1.0,
    title: str = "Volcano plot",
) -> go.Figure:
    df = table.copy()
    df["neg_log10_p"] = -np.log10(df["adjusted_p_value"].clip(lower=1e-300))

    def classify(row):
        if row["adjusted_p_value"] >= alpha:
            return "not significant"
        if row["log2FC"] >= log2fc_threshold:
            return "up"
        if row["log2FC"] <= -log2fc_threshold:
            return "down"
        return "not significant"

    df["direction"] = df.apply(classify, axis=1)
    fig = px.scatter(
        df,
        x="log2FC",
        y="neg_log10_p",
        color="direction",
        color_discrete_map={
            "up": "#d62728",
            "down": "#1f77b4",
            "not significant": "#b0b0b0",
        },
        hover_name="feature",
        title=title,
        template=_TEMPLATE,
        labels={"neg_log10_p": "-log10(adjusted p-value)"},
    )
    fig.add_hline(y=-np.log10(alpha), line_dash="dash", line_color="gray")
    fig.add_vline(x=log2fc_threshold, line_dash="dash", line_color="gray")
    fig.add_vline(x=-log2fc_threshold, line_dash="dash", line_color="gray")
    return fig


def plot_correlation_heatmap(
    matrix: pd.DataFrame, title: str = "Correlation"
) -> go.Figure:
    fig = px.imshow(
        matrix,
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title=title,
        template=_TEMPLATE,
        aspect="auto",
    )
    return fig


def plot_boxplot(
    matrix: pd.DataFrame, feature: str, groups: pd.Series, title: str | None = None
) -> go.Figure:
    values = matrix.loc[feature]
    df = pd.DataFrame({"value": values, "group": groups.reindex(values.index)})
    fig = px.box(
        df,
        x="group",
        y="value",
        points="all",
        title=title or f"{feature}",
        template=_TEMPLATE,
    )
    return fig


def plot_feature_importance(
    importance: pd.Series, top_n: int = 20, title: str = "Feature importance"
) -> go.Figure:
    top = importance.sort_values(ascending=False).head(top_n).sort_values()
    fig = px.bar(
        x=top.values,
        y=top.index,
        orientation="h",
        title=title,
        template=_TEMPLATE,
        labels={"x": "Importance", "y": "Feature"},
    )
    return fig
