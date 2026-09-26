"""A-P4 item 4 (build day 10, lane A): figures F2-F5 as PNG through matplotlib
(:mod:`proofpack.render.figures_png`; D4 section 6; D5 section 3.4).

**The parity test and the map it names.** For each figure the DATA coordinates handed to
matplotlib are read back from the artists (``Line2D.get_xydata()`` for the series, the
reference and criterion lines, the interval bars and the estimate markers; the histogram
``Rectangle`` patches' ``get_x`` / ``get_width`` / ``get_height``) and compared with the
SVG's parsed points put through the inverse of E9's documented linear map -
``figures.PlotMap``: ``px = x0 + (x - xmin) / (xmax - xmin) * w``, ``py = y0 + h - (y -
ymin) / (ymax - ymin) * h``, its eight constants read from the figure's own ``data-map``
attribute (``test_render_figures._Inverse``) - to :data:`TOL` = 1e-9. Pixels are never
compared. The SVG side is the same one ``tests/test_render_figures.py`` inverts to the
arrays of ``run.json``, so the three agree pairwise.

Also: no figure is drawn where the HTML prints a no-data line (F3 without a ``pr`` array,
F4 for a logit score, the whole set for a document without figures); the PNG bytes of two
renders are identical (Agg, fixed dpi, metadata stripped) - measured, not assumed; each
PNG is 300 dpi and 160 mm wide (the ``pHYs`` chunk and the pixel width), carries no text
chunk; the backend is Agg; every figure has at most two labelled series, each with its own
dash pattern and a text label (colour is never the only encoding), in the theme's colours;
F5's criterion line only where a ``ci_lower_bound`` criterion names the attribute.
"""

from __future__ import annotations

import copy
import re
import struct
import zlib
from typing import Any

import pytest

from ap4_docx import needs_extra, synthetic_document
from assembler import assemble
from conftest import make_cohort, make_criteria
from proofpack.render import anchors, figures, theme
from proofpack.render import t1 as render_t1
from test_render_figures import _criterion, _figure, _path_d, _plot, _points

pytestmark = [pytest.mark.day10, pytest.mark.ap4, needs_extra]

TOL = 1e-9
MAP_NAME = (
    "figures.PlotMap (E9): px = x0 + (x - xmin)/(xmax - xmin)*w, "
    "py = y0 + h - (y - ymin)/(ymax - ymin)*h"
)


@pytest.fixture(scope="module")
def png():
    from proofpack.render import figures_png

    return figures_png


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    return synthetic_document()


@pytest.fixture(scope="module")
def page(document) -> str:
    return render_t1.render_t1(document)


@pytest.fixture(scope="module")
def refs(document):
    ids = [r["id"] for r in document.get("guidance_refs") or []]
    return {r["id"]: r for r in anchors.resolve(ids)}


@pytest.fixture(scope="module")
def figs(png, document, refs):
    return png.all_figures(document, refs)


def _close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(float(a) - float(b)) <= tol


def _by_gid(fig, prefix: str) -> list[Any]:
    out = []
    for ax in fig.axes:
        for artist in list(ax.lines) + list(ax.patches):
            gid = artist.get_gid() or ""
            if gid == prefix or gid.startswith(prefix + ":"):
                out.append(artist)
    return out


def _xy(line) -> list[tuple[float, float]]:
    return [(float(x), float(y)) for x, y in line.get_xydata()]


def _same(got: list[tuple[float, float]], want: list[tuple[float, float]]) -> None:
    assert len(got) == len(want), (len(got), len(want))
    for (gx, gy), (wx, wy) in zip(got, want, strict=True):
        assert _close(gx, wx) and _close(gy, wy), (gx, gy, wx, wy)


# ------------------------------------------------------------------ the tolerance


def test_the_tolerance_is_one_nano_and_bites():
    assert TOL == 1e-9
    assert _close(0.5, 0.5 + 5e-10) and not _close(0.5, 0.5 + 1e-8)
    assert not _close(0.5, 0.5 + 2e-9)


# ------------------------------------------------------------------ F2


def test_f2_series_and_operating_points_equal_the_svg_through_the_map(figs, page, document):
    fig = figs["f2"]
    assert fig is not None
    svg = _figure(page, "F2")
    inv, plot = _plot(svg)
    (series_d,) = _path_d(plot, "series")
    svg_pts = [(inv.x(a), inv.y(b)) for a, b in _points(series_d)]
    (series,) = _by_gid(fig, "series")
    mpl_pts = _xy(series)
    assert len(mpl_pts) == len(svg_pts) == len(document["overall"]["threshold_free"]["roc"])
    for (mx, my), (sx, sy) in zip(mpl_pts, svg_pts, strict=True):
        assert _close(mx, sx) and _close(my, sy), (mx, my, sx, sy)
    (ref,) = _by_gid(fig, "reference")
    (ref_d,) = _path_d(plot, "reference")
    _same(_xy(ref), [(inv.x(a), inv.y(b)) for a, b in _points(ref_d)])
    markers = re.findall(r'data-op="([^"]+)" cx="([^"]+)" cy="([^"]+)"', plot)
    points = _by_gid(fig, "operating-point")
    assert [p.get_gid().split(":", 1)[1] for p in points] == [m[0] for m in markers] == ["op1"]
    for p, (_, cx, cy) in zip(points, markers, strict=True):
        ((mx, my),) = _xy(p)
        assert _close(mx, inv.x(float(cx))) and _close(my, inv.y(float(cy)))


# ------------------------------------------------------------------ F3


def test_f3_planted_pr_array_equals_the_svg_and_is_absent_without_one(png, document, refs):
    assert png.f3_figure(document, refs) is None  # the synthetic run carries no pr array
    assert figures.F3_ABSENT in render_t1.render_t1(document)
    doc = copy.deepcopy(document)
    doc["overall"]["threshold_free"]["pr"] = [
        [0.0, 1.0, None],
        [0.25, 0.8, 0.9],
        [0.5, 0.6, 0.7],
        [1.0, 0.32, 0.1],
    ]
    fig = png.f3_figure(doc, refs)
    svg = _figure(render_t1.render_t1(doc), "F3")
    inv, plot = _plot(svg)
    (series_d,) = _path_d(plot, "series")
    (series,) = _by_gid(fig, "series")
    _same(_xy(series), [(inv.x(a), inv.y(b)) for a, b in _points(series_d)])
    (ref,) = _by_gid(fig, "reference")
    (ref_d,) = _path_d(plot, "reference")
    _same(_xy(ref), [(inv.x(a), inv.y(b)) for a, b in _points(ref_d)])
    prev = doc["overall"]["threshold_free"]["prevalence"]["est"]
    assert all(_close(y, prev) for _, y in _xy(ref))


# ------------------------------------------------------------------ F4


def test_f4_deciles_intervals_and_strip_equal_the_svg_through_both_maps(figs, page, document):
    fig = figs["f4"]
    assert fig is not None
    svg = _figure(page, "F4")
    inv, plot = _plot(svg)
    circles = re.findall(r'data-role="decile" data-bin="(\d+)" cx="([^"]+)" cy="([^"]+)"', plot)
    deciles = _by_gid(fig, "decile")
    assert len(deciles) == len(circles) == 10
    for artist, (b, cx, cy) in zip(deciles, circles, strict=True):
        assert artist.get_gid() == f"decile:{b}"
        ((mx, my),) = _xy(artist)
        assert _close(mx, inv.x(float(cx))) and _close(my, inv.y(float(cy)))
    bars = _path_d(plot, "interval")
    intervals = _by_gid(fig, "interval")
    assert len(intervals) == len(bars) == 10
    for artist, d in zip(intervals, bars, strict=True):
        _same(_xy(artist), [(inv.x(a), inv.y(b)) for a, b in _points(d)])
    (ref,) = _by_gid(fig, "reference")
    (ref_d,) = _path_d(plot, "reference")
    _same(_xy(ref), [(inv.x(a), inv.y(b)) for a, b in _points(ref_d)])
    # the histogram strip through its own map (the strip's data-map)
    sinv, strip = _plot(svg, "fig-strip")
    rects = re.findall(
        r'<rect class="fig-hist" data-bin="(\d+)" x="([^"]+)" y="([^"]+)" width="([^"]+)" '
        r'height="([^"]+)"/>',
        strip,
    )
    hist = _by_gid(fig, "hist")
    assert len(hist) == len(rects) == 10
    for patch, (b, x, y, w, h) in zip(hist, rects, strict=True):
        assert patch.get_gid() == f"hist:{b}"
        x, y, w, h = float(x), float(y), float(w), float(h)
        assert _close(patch.get_x(), sinv.x(x))
        assert _close(patch.get_x() + patch.get_width(), sinv.x(x + w))
        assert _close(patch.get_height(), sinv.y(y) - sinv.y(y + h))
        assert _close(patch.get_y(), 0.0)


def test_f4_is_not_drawn_for_a_logit_score_and_the_reason_is_text(png):
    crit = make_criteria(
        criteria=[], fairness=None, score={"type": "logit", "orientation": "higher_is_positive"}
    )
    doc = assemble(make_cohort(n=160), crit)
    refs = {}
    assert png.f4_figure(doc, refs) is None
    assert figures.f4_calibration(doc, refs) is None
    out = render_t1.render_t1(doc)
    assert 'id="F4"' not in out
    assert "F4 (calibration) is omitted: calibration is null (score_not_probability)." in out
    figs = png.all_figures(doc, refs)
    assert figs["f4"] is None and figs["f2"] is not None


# ------------------------------------------------------------------ F5


def test_f5_rows_reference_line_and_labels_equal_the_svg_for_every_attribute_and_metric(
    figs, page, document
):
    specs = figures.f5_forest(document, {})
    for attribute, per_metric in figs["f5"].items():
        for fig, spec in zip(per_metric, specs[attribute], strict=True):
            svg = _figure(page, spec["id"])
            inv, plot = _plot(svg)
            circles = re.findall(r'data-role="estimate" cx="([^"]+)"', plot)
            bars = _path_d(plot, "interval")
            estimates = _by_gid(fig, "estimate")
            intervals = _by_gid(fig, "interval")
            assert len(estimates) == len(circles) and len(intervals) == len(bars), spec["id"]
            for artist, cx in zip(estimates, circles, strict=True):
                ((mx, _),) = _xy(artist)
                assert _close(mx, inv.x(float(cx))), spec["id"]
            for artist, d in zip(intervals, bars, strict=True):
                (x1, _), (x2, _) = _points(d)
                (mx1, _), (mx2, _) = _xy(artist)
                assert _close(mx1, inv.x(x1)) and _close(mx2, inv.x(x2)), spec["id"]
            # rows in the SVG's order: the reference level first, the label text the same
            labels = re.findall(r'<text class="fig-text" x="10" y="[^"]+">([^<]+)</text>', plot)
            ax = fig.axes[0]
            assert [t.get_text() for t in ax.get_yticklabels()] == labels, spec["id"]
            ref_d = _path_d(plot, "reference")
            refs_mpl = _by_gid(fig, "reference")
            assert len(refs_mpl) == len(ref_d) <= 1
            for artist, d in zip(refs_mpl, ref_d, strict=True):
                pairs = zip(_xy(artist), _points(d), strict=True)
                assert all(_close(x, inv.x(a)) for (x, _), (a, _) in pairs)
            assert _by_gid(fig, "criterion") == []  # no ci_lower_bound criterion names these


def test_f5_criterion_line_only_where_a_lower_bound_criterion_names_the_attribute(png):
    cols = make_cohort(n=240)
    doc = assemble(cols, make_criteria(criteria=[_criterion()], fairness=None))
    page = render_t1.render_t1(doc)
    figs = png.all_figures(doc, {})
    specs = figures.f5_forest(doc, {})
    seen = 0
    for attribute, per_metric in figs["f5"].items():
        for fig, spec in zip(per_metric, specs[attribute], strict=True):
            svg = _figure(page, spec["id"])
            inv, plot = _plot(svg)
            lines = _path_d(plot, "criterion")
            crit = _by_gid(fig, "criterion")
            assert len(crit) == len(lines), spec["id"]
            for artist, d in zip(crit, lines, strict=True):
                seen += 1
                pairs = zip(_xy(artist), _points(d), strict=True)
                assert all(_close(x, inv.x(a)) for (x, _), (a, _) in pairs)
                assert all(_close(x, 0.65) for x, _ in _xy(artist))
                assert "customer criterion C_sex (Dr A., 2026-03-01): 0.65" in artist.get_label()
                assert artist.get_linestyle() != "-"
    assert seen == 1  # F5-sex-sensitivity alone
    # a point-estimate criterion draws no line
    doc2 = assemble(cols, make_criteria(criteria=[_criterion(statistic="point_estimate")]))
    figs2 = png.all_figures(doc2, {})
    assert all(_by_gid(f, "criterion") == [] for per in figs2["f5"].values() for f in per)


# ------------------------------------------------------------------ the set


def test_a_figure_exactly_where_the_html_has_one(figs, page):
    n_svg = len(re.findall(r"<svg ", page))
    drawn = [f for f in (figs["f2"], figs["f3"], figs["f4"]) if f is not None]
    drawn += [f for per in figs["f5"].values() for f in per]
    assert len(drawn) == n_svg == 11
    assert figs["f3"] is None and figures.F3_ABSENT in page


# ------------------------------------------------------------------ the PNG


def _chunks(data: bytes) -> list[tuple[str, bytes]]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    out, i = [], 8
    while i < len(data):
        (length,) = struct.unpack(">I", data[i : i + 4])
        ctype = data[i + 4 : i + 8].decode("ascii")
        out.append((ctype, data[i + 8 : i + 8 + length]))
        i += 12 + length
    return out


def test_png_bytes_are_identical_across_two_renders_and_carry_no_metadata(png, document, refs):
    first = png.all_figures(document, refs)
    second = png.all_figures(document, refs)

    def flat(f):
        yield f["f2"]
        yield f["f4"]
        for per in f["f5"].values():
            yield from per

    pairs = list(zip(flat(first), flat(second), strict=True))
    assert len(pairs) == 11
    for a, b in pairs:
        da, db = png.png_bytes(a), png.png_bytes(b)
        assert da == db and len(da) > 1000
        types = [c for c, _ in _chunks(da)]
        assert not {"tEXt", "iTXt", "zTXt", "tIME"} & set(types), types
        ihdr = next(body for c, body in _chunks(da) if c == "IHDR")
        width, height = struct.unpack(">II", ihdr[:8])
        assert abs(width - png.WIDTH_MM / 25.4 * png.DPI) < 1.0, width
        assert height > 100
        phys = next(body for c, body in _chunks(da) if c == "pHYs")
        ppx, ppy, unit = struct.unpack(">IIB", phys)
        assert unit == 1 and ppx == ppy == round(png.DPI / 0.0254)
    assert png.DPI == 300 and png.WIDTH_MM == 160.0
    assert zlib.crc32(png.png_bytes(first["f2"])) == zlib.crc32(png.png_bytes(second["f2"]))


def test_the_backend_is_agg_and_pyplot_is_not_used(png):
    import matplotlib

    assert matplotlib.get_backend().lower() == "agg"
    src = open(png.__file__, encoding="utf-8").read()
    assert 'matplotlib.use("Agg")' in src and "pyplot" not in src.replace("no ``pyplot``", "")
    assert "FigureCanvasAgg" in src


def test_two_labelled_series_at_most_each_with_its_own_dash_pattern_in_the_tokens(figs):
    tokens = {theme.color(n).lower() for n in ("ink", "ink-soft", "ink-faint", "line", "bg")}
    from matplotlib.colors import to_hex

    def flat(f):
        yield f["f2"]
        yield f["f4"]
        for per in f["f5"].values():
            yield from per

    for fig in flat(figs):
        for ax in fig.axes:
            labelled = [
                ln for ln in ax.lines if ln.get_label() and not ln.get_label().startswith("_")
            ]
            series = [ln for ln in labelled if ln.get_gid() in ("series", "reference")]
            assert len(series) <= 2
            styles = [ln.get_linestyle() for ln in labelled if ln.get_marker() in ("None", "")]
            assert len(styles) == len(set(styles)), styles  # a dash pattern each
            for ln in labelled:
                assert ln.get_label().strip()
            for ln in ax.lines:
                assert to_hex(ln.get_color()).lower() in tokens, ln.get_gid()
            for patch in ax.patches:
                assert to_hex(patch.get_facecolor()).lower() in tokens
