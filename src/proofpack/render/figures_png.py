"""Figures F2-F5 as PNG through matplotlib, for the DOCX (D4 section 6; D5 section 3.4;
A-P4, build day 10, lane A).

The second drawer of one source: every coordinate handed to matplotlib here is a **data**
coordinate from the data-level functions of :mod:`proofpack.render.figures` (``f2_data``,
``f3_data``, ``f4_data``, ``f5_data``), which select what is drawn from the arrays of
``run.json`` once for both drawers; the captions, legends and axis labels are the same
strings the SVG specs carry. Nothing is computed here. ``tests/test_ap4_figures.py`` reads
the coordinates back from the matplotlib artists (``Line2D.get_xydata()``, the histogram
``Rectangle`` patches) and compares them with the SVG's parsed points put through the
inverse of E9's documented linear map (``figures.PlotMap``: ``px = x0 + (x - xmin) /
(xmax - xmin) * w``, ``py = y0 + h - (y - ymin) / (ymax - ymin) * h``, read from each
figure's ``data-map`` attribute), to 1e-9; never pixels.

Rules kept from the SVG drawer: at most two series per figure; colour is never the only
encoding (every series has a dash pattern and a text label in the legend); the colours
are the theme's tokens (``design/tokens.json`` through :mod:`proofpack.render.theme`); no
shaded region; F4 is omitted for a score that is not a probability (the reason prints as
text in the document, not here); F5's criterion line only where a ``ci_lower_bound``
criterion names the attribute, metric and operating point (:func:`figures.criterion_values`).

The backend is **Agg**, forced at import (``matplotlib.use`` below) and used explicitly
through :class:`FigureCanvasAgg`: no display, no ``pyplot``, no global figure state. PNGs
are 300 dpi, 160 mm wide (:data:`DPI`, :data:`WIDTH_MM`; the height keeps the SVG's aspect
ratio), with the metadata chunks stripped (``metadata={"Software": None}``): two renders
of one document give identical bytes on one machine (measured, ``tests/test_ap4_figures.py
::test_png_bytes_are_identical_across_two_renders_and_carry_no_metadata``). Byte identity
across platforms is not claimed: the raster depends on the FreeType and font versions
matplotlib finds.

matplotlib is imported here only (the ``[docx]`` extra): ``import proofpack.render``,
``import proofpack.render.html`` and an HTML render never import this module.
"""

from __future__ import annotations

import io
from typing import Any

import matplotlib

matplotlib.use("Agg")  # the DOCX drawer never opens a window and never reads a display

from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from proofpack.render import figures, theme  # noqa: E402

DPI = 300
WIDTH_MM = 160.0
#: The SVG view box is 600 units wide; a figure's height in mm keeps its aspect ratio.
VIEW_W = float(figures.VIEW_W)
#: Dash patterns (on, off) in points: the reference lines, the criterion line.
REFERENCE_DASHES = (6, 4)
CRITERION_DASHES = (10, 4)
FONT_PT = 9.0


def _colours() -> dict[str, str]:
    return {
        "ink": theme.color("ink"),
        "ink_soft": theme.color("ink-soft"),
        "ink_faint": theme.color("ink-faint"),
        "line": theme.color("line"),
        "bg": theme.color("bg"),
    }


def _mm(view_units: float) -> float:
    return WIDTH_MM * float(view_units) / VIEW_W


def _figure(height_mm: float) -> Figure:
    fig = Figure(figsize=(WIDTH_MM / 25.4, height_mm / 25.4), dpi=DPI)
    FigureCanvasAgg(fig)
    fig.set_facecolor(_colours()["bg"])
    return fig


def _style_axes(ax: Any, c: dict[str, str]) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(c["ink_soft"])
    ax.tick_params(colors=c["ink"], labelsize=FONT_PT)
    ax.set_facecolor(c["bg"])


def png_bytes(fig: Figure) -> bytes:
    """The figure as PNG bytes at :data:`DPI`, metadata stripped."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, metadata={"Software": None})
    return buf.getvalue()


# ------------------------------------------------------------------ F2 / F3


def _curve_figure(
    spec: dict[str, Any],
    curve: list[tuple[float, float]],
    reference: list[tuple[float, float]],
    markers: list[tuple[str, float, float]],
    reference_label: str,
) -> Figure:
    c = _colours()
    fig = _figure(_mm(spec["height"]))
    ax = fig.add_axes([0.12, 0.13, 0.84, 0.82])
    _style_axes(ax, c)
    ax.plot(
        [x for x, _ in reference],
        [y for _, y in reference],
        color=c["ink_faint"],
        linestyle=(0, REFERENCE_DASHES),
        linewidth=1.0,
        label=reference_label,
        gid="reference",
    )
    ax.plot(
        [x for x, _ in curve],
        [y for _, y in curve],
        color=c["ink"],
        linestyle="-",
        linewidth=2.0,
        label=spec["legend"],
        gid="series",
    )
    for op, fx, ty in markers:
        ax.plot(
            [fx],
            [ty],
            linestyle="none",
            color=c["ink"],
            marker="o",
            markersize=6,
            markerfacecolor="none",
            markeredgecolor=c["ink"],
            markeredgewidth=1.5,
            gid=f"operating-point:{op}",
        )
        ax.annotate(op, (fx, ty), textcoords="offset points", xytext=(6, 6), fontsize=FONT_PT)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_xticks([0.0, 0.5, 1.0])
    ax.set_yticks([0.0, 0.5, 1.0])
    ax.set_xlabel(spec["xlabel"], fontsize=FONT_PT, color=c["ink"])
    ax.set_ylabel(spec["ylabel"], fontsize=FONT_PT, color=c["ink"])
    ax.legend(loc="lower right", fontsize=FONT_PT, frameon=False)
    return fig


def f2_figure(document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]) -> Figure | None:
    """F2 (ROC) with its declared operating points, or ``None`` when the SVG omits it."""
    spec = figures.f2_roc(document, refs_by_id)
    data = figures.f2_data(document)
    if spec is None or data is None:
        return None
    return _curve_figure(
        spec, data["roc"], [(0.0, 0.0), (1.0, 1.0)], data["markers"], "chance (dashed)"
    )


def f3_figure(document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]) -> Figure | None:
    """F3 (precision-recall) with the prevalence baseline, or ``None`` when the SVG omits it."""
    spec = figures.f3_pr(document, refs_by_id)
    data = figures.f3_data(document)
    if spec is None or data is None:
        return None
    prev = data["prevalence"]
    return _curve_figure(
        spec, data["pr"], [(0.0, prev), (1.0, prev)], [], "prevalence baseline (dashed)"
    )


# ------------------------------------------------------------------ F4


def f4_figure(document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]) -> Figure | None:
    """F4 (calibration by decile) with the histogram strip, or ``None`` when the SVG omits
    it (``calibration`` null: the reason is printed as text in the document)."""
    spec = figures.f4_calibration(document, refs_by_id)
    data = figures.f4_data(document)
    if spec is None or data is None:
        return None
    c = _colours()
    fig = _figure(_mm(spec["height"]))
    # the plot takes the SVG's share of the height; the strip sits below it
    ax = fig.add_axes([0.12, 0.40, 0.84, 0.56])
    strip = fig.add_axes([0.12, 0.14, 0.84, 0.08])
    _style_axes(ax, c)
    _style_axes(strip, c)
    ax.plot(
        [0.0, 1.0],
        [0.0, 1.0],
        color=c["ink_faint"],
        linestyle=(0, REFERENCE_DASHES),
        linewidth=1.0,
        label="identity (dashed)",
        gid="reference",
    )
    for b, mean_pred, est, lo, hi in data["points"]:
        ax.plot(
            [mean_pred, mean_pred],
            [lo, hi],
            color=c["ink"],
            linewidth=1.5,
            linestyle="-",
            gid=f"interval:{b}",
        )
        ax.plot(
            [mean_pred],
            [est],
            linestyle="none",
            color=c["ink"],
            marker="o",
            markersize=5,
            markerfacecolor="none",
            markeredgecolor=c["ink"],
            markeredgewidth=1.5,
            gid=f"decile:{b}",
            label=spec["legend"] if b == data["points"][0][0] else None,
        )
    for b, score_min, score_max, n in data["strip"]:
        strip.bar(
            score_min,
            n,
            width=score_max - score_min,
            align="edge",
            color=c["line"],
            edgecolor="none",
            gid=f"hist:{b}",
        )
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_xticks([0.0, 0.5, 1.0])
    ax.set_yticks([0.0, 0.5, 1.0])
    ax.set_xlabel(spec["xlabel"], fontsize=FONT_PT, color=c["ink"])
    ax.set_ylabel(spec["ylabel"], fontsize=FONT_PT, color=c["ink"])
    if spec.get("flag_short"):
        ax.text(0.03, 0.93, spec["flag_short"], fontsize=FONT_PT, color=c["ink"])
    # below the plot, between the axis label and the strip, so no series is covered; in
    # figure coordinates so the legend's one long line has the figure's whole width
    fig.legend(loc="upper left", bbox_to_anchor=(0.02, 0.31), fontsize=7.5, frameon=False)
    strip.set_xlim(0.0, 1.0)
    strip.set_ylim(0.0, float(data["n_max"]))
    strip.set_yticks([])
    strip.set_xticks([0.0, 0.5, 1.0])
    strip.set_xlabel(
        "Histogram strip: predicted risks per decile bin (bar height n)",
        fontsize=FONT_PT,
        color=c["ink"],
    )
    return fig


# ------------------------------------------------------------------ F5


def f5_figures(
    document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]
) -> dict[str, list[Figure]]:
    """``{attribute: [figure per metric]}`` in the order of :func:`figures.f5_forest`."""
    specs = figures.f5_forest(document, refs_by_id)
    data = figures.f5_data(document)
    c = _colours()
    out: dict[str, list[Figure]] = {}
    for attribute, data_figs in data.items():
        figs = []
        for spec, d in zip(specs[attribute], data_figs, strict=True):
            n_rows = len(d["rows"])
            fig = _figure(_mm(float(spec["height"])))
            ax = fig.add_axes([0.30, 0.16, 0.38, 0.72])
            _style_axes(ax, c)
            if d["reference"] is not None:
                ax.axvline(
                    d["reference"],
                    color=c["ink_faint"],
                    linestyle=(0, REFERENCE_DASHES),
                    linewidth=1.0,
                    label="overall estimate (dashed)",
                    gid="reference",
                )
            for k, crit in enumerate(d["criteria"]):
                ax.axvline(
                    crit["value"],
                    color=c["ink_faint"],
                    linestyle=(0, CRITERION_DASHES),
                    linewidth=2.5,
                    label=f"{crit['label']}: {crit['value_text']} (heavy dashed)",
                    gid=f"criterion:{k}",
                )
            for j, row in enumerate(d["rows"]):
                if row["drawn"]:
                    ax.plot(
                        [row["ci_lo"], row["ci_hi"]],
                        [j, j],
                        color=c["ink"],
                        linewidth=1.5,
                        linestyle="-",
                        gid=f"interval:{j}",
                    )
                    ax.plot(
                        [row["est"]],
                        [j],
                        linestyle="none",
                        color=c["ink"],
                        marker="o",
                        markersize=5,
                        markerfacecolor="none",
                        markeredgecolor=c["ink"],
                        markeredgewidth=1.5,
                        gid=f"estimate:{j}",
                    )
                ax.text(
                    1.03,
                    j,
                    row["value"],
                    transform=ax.get_yaxis_transform(),
                    fontsize=FONT_PT,
                    color=c["ink"],
                    va="center",
                )
            ax.set_yticks(list(range(n_rows)))
            ax.set_yticklabels([r["label"] for r in d["rows"]], fontsize=FONT_PT)
            ax.set_ylim(n_rows - 0.5, -0.5)  # the first row at the top, as the SVG
            ax.set_xlim(0.0, 1.0)
            ax.set_xticks([0.0, 0.5, 1.0])
            ax.set_xlabel(spec["title"], fontsize=FONT_PT, color=c["ink"])
            if d["reference"] is not None or d["criteria"]:
                ax.legend(
                    loc="upper center",
                    bbox_to_anchor=(0.5, 1.16),
                    fontsize=FONT_PT,
                    frameon=False,
                    ncol=1,
                )
            figs.append(fig)
        out[attribute] = figs
    return out


def all_figures(document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """``{"f2": Figure | None, "f3": ..., "f4": ..., "f5": {attribute: [Figure]}}`` - a
    figure exactly where :func:`figures.figures` has a spec, and ``None`` where the HTML
    prints a no-data line instead."""
    return {
        "f2": f2_figure(document, refs_by_id),
        "f3": f3_figure(document, refs_by_id),
        "f4": f4_figure(document, refs_by_id),
        "f5": f5_figures(document, refs_by_id),
    }
