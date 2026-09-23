"""Build day 9 (E9 item 5): figures F2-F5 as inline SVG in T1.

The oracle is ``run.json`` itself: every plotted coordinate is parsed out of the SVG and
put back through the inverse of **the documented linear map** (``figures.PlotMap``:
``px = x0 + (x - xmin) / (xmax - xmin) * w``, ``py = y0 + h - (y - ymin) / (ymax - ymin)
* h``), whose eight constants the test reads from the figure's own ``data-map``
attribute, and compared with the arrays of the document to 1e-9:

* F2: every vertex of the ROC polyline equals ``overall.threshold_free.roc`` in order;
  each operating-point circle is a vertex of that array and equals ``(1 - specificity,
  sensitivity)`` of ``overall.<op>``;
* F4: each decile circle equals ``(mean_pred, observed.est)``, each bar ``observed.ci_lo``
  to ``ci_hi``, each histogram rectangle spans ``score_min`` to ``score_max`` with the
  bin's ``n`` as its height under the strip's map; F4 is absent for a logit score;
* F5: each estimate circle and interval equals the subgroup row's Number; the reference
  line is the overall estimate; a criterion line appears only on the attribute and
  metric a ``ci_lower_bound`` criterion names;
* no ``<rect>`` other than the histogram strip, no ``<path>`` or ``<circle>`` with a
  fill, one series per figure; every caption carries n, the interval method and the
  guidance anchor.
"""

from __future__ import annotations

import copy
import re
from typing import Any

import pytest

from assembler import assemble
from conftest import make_cohort, make_criteria
from proofpack.render import figures
from proofpack.render import t1 as render_t1
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site

pytestmark = pytest.mark.day9
TOL = 1e-9


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    return assemble(cohort_with_a_thirty_row_site(), crit)


@pytest.fixture(scope="module")
def page(document) -> str:
    return render_t1.render_t1(document)


def _figure(page: str, fig_id: str) -> str:
    m = re.search(
        rf'<figure class="figure" id="{re.escape(fig_id)}"[^>]*>(.*?)</figure>', page, re.S
    )
    assert m, fig_id
    return m.group(1)


class _Inverse:
    """The inverse of the documented linear map, from a ``data-map`` attribute."""

    def __init__(self, attr: str) -> None:
        self.x0, self.y0, self.w, self.h, self.xmin, self.xmax, self.ymin, self.ymax = (
            float(v) for v in attr.split()
        )

    def x(self, px: float) -> float:
        return self.xmin + (px - self.x0) / self.w * (self.xmax - self.xmin)

    def y(self, py: float) -> float:
        return self.ymin + (self.y0 + self.h - py) / self.h * (self.ymax - self.ymin)


def _plot(svg: str, cls: str = "fig-plot") -> tuple[_Inverse, str]:
    m = re.search(rf'<g class="{cls}" data-map="([^"]+)">(.*?)</g>', svg, re.S)
    assert m, cls
    return _Inverse(m.group(1)), m.group(2)


def _points(d: str) -> list[tuple[float, float]]:
    return [(float(a), float(b)) for a, b in re.findall(r"[ML](-?[\d.e+-]+),(-?[\d.e+-]+)", d)]


def _path_d(block: str, role: str) -> list[str]:
    return re.findall(
        rf'<path class="[^"]+" fill="none" data-role="{role}"[^>]* d="([^"]+)"', block
    )


def test_f2_vertices_and_operating_points_invert_to_the_roc_array(page, document):
    svg = _figure(page, "F2")
    inv, plot = _plot(svg)
    roc = document["overall"]["threshold_free"]["roc"]
    (series,) = _path_d(plot, "series")
    pts = _points(series)
    assert len(pts) == len(roc) == 401
    for (px, py), (fpr, tpr, _) in zip(pts, roc, strict=True):
        assert abs(inv.x(px) - fpr) <= TOL and abs(inv.y(py) - tpr) <= TOL
    (ref,) = _path_d(plot, "reference")
    assert [(inv.x(a), inv.y(b)) for a, b in _points(ref)] == pytest.approx(
        [(0, 0), (1, 1)], abs=TOL
    )
    markers = re.findall(r'data-op="([^"]+)" cx="([^"]+)" cy="([^"]+)"', plot)
    assert [m[0] for m in markers] == ["op1"]
    for op, cx, cy in markers:
        fx, ty = inv.x(float(cx)), inv.y(float(cy))
        block = document["overall"][op]
        assert abs(ty - block["sensitivity"]["est"]) <= TOL
        assert abs(fx - (1 - block["specificity"]["est"])) <= TOL
        assert any(abs(f - fx) <= TOL and abs(t - ty) <= TOL for f, t, _ in roc)
    assert re.search(r"<text class=\"fig-text\"[^>]*>op1</text>", plot)  # labelled with its id
    # the legend prints AUROC [CI] as the table does
    assert "AUROC 0.835 [0.795, 0.876]" in svg


def test_f4_points_bars_and_strip_invert_to_the_decile_curve(page, document):
    svg = _figure(page, "F4")
    inv, plot = _plot(svg)
    bins = document["calibration"]["decile_curve"]
    circles = re.findall(r'data-role="decile" data-bin="(\d+)" cx="([^"]+)" cy="([^"]+)"', plot)
    assert len(circles) == len(bins) == 10
    for (b, cx, cy), bin_ in zip(circles, bins, strict=True):
        obs = bin_["observed"]["number"]
        assert int(b) == bin_["bin"]
        assert abs(inv.x(float(cx)) - bin_["mean_pred"]) <= TOL
        assert abs(inv.y(float(cy)) - obs["est"]) <= TOL
    bars = _path_d(plot, "interval")
    assert len(bars) == 10
    for d, bin_ in zip(bars, bins, strict=True):
        (x1, y1), (x2, y2) = _points(d)
        obs = bin_["observed"]["number"]
        assert (
            abs(inv.x(x1) - bin_["mean_pred"]) <= TOL and abs(inv.x(x2) - bin_["mean_pred"]) <= TOL
        )
        assert abs(inv.y(y1) - obs["ci_lo"]) <= TOL and abs(inv.y(y2) - obs["ci_hi"]) <= TOL
    (ref,) = _path_d(plot, "reference")
    assert [(inv.x(a), inv.y(b)) for a, b in _points(ref)] == pytest.approx(
        [(0, 0), (1, 1)], abs=TOL
    )
    sinv, strip = _plot(svg, "fig-strip")
    rects = re.findall(
        r'<rect class="fig-hist" data-bin="(\d+)" x="([^"]+)" y="([^"]+)" width="([^"]+)" '
        r'height="([^"]+)"/>',
        strip,
    )
    assert len(rects) == 10
    for (_, x, y, w, h), bin_ in zip(rects, bins, strict=True):
        x, y, w, h = float(x), float(y), float(w), float(h)
        assert abs(sinv.x(x) - bin_["score_min"]) <= TOL
        assert abs(sinv.x(x + w) - bin_["score_max"]) <= TOL
        assert abs(sinv.y(y) - bin_["n"]) <= TOL and abs(sinv.y(y + h) - 0) <= TOL
    # slope and intercept in the legend; the 200/200 flag on the plot (events 128 < 200)
    assert "slope 1.349 [1.056, 1.642]" in svg and "200/200 convention" in svg


def test_f4_is_absent_for_a_logit_score():
    crit = make_criteria(
        criteria=[], fairness=None, score={"type": "logit", "orientation": "higher_is_positive"}
    )
    doc = assemble(make_cohort(n=160), crit)
    out = render_t1.render_t1(doc)
    assert 'id="F4"' not in out and 'class="fig-hist"' not in out
    assert "F4 (calibration) is omitted: calibration is null (score_not_probability)." in out


def test_f5_rows_and_the_overall_line_invert_to_the_subgroup_numbers(page, document):
    for fig_id, attribute, metric in (
        ("F5-sex-sensitivity", "sex", "sensitivity"),
        ("F5-age-specificity", "age", "specificity"),
        ("F5-site-auroc", "site", "auroc"),
    ):
        svg = _figure(page, fig_id)
        inv, plot = _plot(svg)
        rows = [r for r in document["subgroups"] if r["attribute"] == attribute]
        order = [r for r in rows if r["is_reference"]] + [r for r in rows if not r["is_reference"]]
        labels = re.findall(r'<text class="fig-text" x="10" y="[^"]+">([^<]+)</text>', plot)
        assert [lb.split(" (ref)")[0].rstrip("ᵃᵇᶜ") for lb in labels] == [r["level"] for r in order]
        assert labels[0].startswith(f"{order[0]['level']} (ref)")
        circles = re.findall(r'data-role="estimate" cx="([^"]+)"', plot)
        bars = _path_d(plot, "interval")
        assert len(circles) == len(bars) == len(order)
        for cx, d, r in zip(circles, bars, order, strict=True):
            num = (
                r["metrics"]["auroc"]["number"]
                if metric == "auroc"
                else r["metrics"]["op1"][metric]["number"]
            )
            assert abs(inv.x(float(cx)) - num["est"]) <= TOL
            (x1, _), (x2, _) = _points(d)
            assert abs(inv.x(x1) - num["ci_lo"]) <= TOL and abs(inv.x(x2) - num["ci_hi"]) <= TOL
        (ref,) = _path_d(plot, "reference")
        overall = (
            document["overall"]["threshold_free"]["auroc"]
            if metric == "auroc"
            else document["overall"]["op1"][metric]
        )
        assert all(abs(inv.x(a) - overall["est"]) <= TOL for a, _ in _points(ref))


def _criterion(**kw) -> dict[str, Any]:
    base = {
        "id": "C_sex",
        "metric": "sensitivity",
        "operating_point": "op1",
        "scope": {"attribute": "sex", "level": "*"},
        "statistic": "ci_lower_bound",
        "comparator": ">=",
        "value": 0.65,
        "author": "Dr A.",
        "date": "2026-03-01",
        "justification": "test fixture",
    }
    base.update(kw)
    return base


def test_f5_draws_the_criterion_line_only_where_a_lower_bound_criterion_names_it():
    cols = make_cohort(n=240)
    with_c = assemble(cols, make_criteria(criteria=[_criterion()], fairness=None))
    out = render_t1.render_t1(with_c)
    sex_se = _figure(out, "F5-sex-sensitivity")
    inv, plot = _plot(sex_se)
    (line,) = _path_d(plot, "criterion")
    assert all(abs(inv.x(a) - 0.65) <= TOL for a, _ in _points(line))
    assert "customer criterion C_sex (Dr A., 2026-03-01): 0.65" in sex_se
    for other in (
        "F5-sex-specificity",
        "F5-sex-auroc",
        "F5-age-sensitivity",
        "F5-site-sensitivity",
    ):
        assert 'data-role="criterion"' not in _figure(out, other), other
    # no criterion, or a point-estimate criterion: no line anywhere, never a shaded region
    for crit in ([], [_criterion(statistic="point_estimate")]):
        doc = assemble(cols, make_criteria(criteria=crit, fairness=None))
        assert 'data-role="criterion"' not in render_t1.render_t1(doc)


def test_f3_draws_a_planted_pr_array_with_its_prevalence_baseline(document):
    doc = copy.deepcopy(document)
    tf = doc["overall"]["threshold_free"]
    pr = [[0.0, 1.0, None], [0.25, 0.8, 0.9], [0.5, 0.6, 0.7], [1.0, 0.32, 0.1]]
    tf["pr"] = pr
    out = render_t1.render_t1(doc)
    svg = _figure(out, "F3")
    inv, plot = _plot(svg)
    (series,) = _path_d(plot, "series")
    got = [(inv.x(a), inv.y(b)) for a, b in _points(series)]
    assert got == pytest.approx([(r, p) for r, p, _ in pr], abs=TOL)
    (ref,) = _path_d(plot, "reference")
    assert all(abs(inv.y(b) - tf["prevalence"]["est"]) <= TOL for _, b in _points(ref))
    # the synthetic run carries no pr array: F3 is the no-data line
    assert figures.F3_ABSENT in render_t1.render_t1(document)


def test_no_filled_mark_but_the_histogram_strip_and_one_series_per_figure(page):
    svgs = re.findall(r"<svg .*?</svg>", page, re.S)
    assert len(svgs) == 11  # F2, F4 and nine F5 (three attributes by three metrics)
    for svg in svgs:
        for m in re.finditer(r"<(path|circle)\b([^>]*)>", svg):
            assert 'fill="none"' in m.group(2), m.group(0)[:80]
        for m in re.finditer(r"<rect\b([^>]*)>", svg):
            assert 'class="fig-hist"' in m.group(1)
        assert "<polygon" not in svg and "<ellipse" not in svg and "opacity" not in svg
        assert len(re.findall(r'data-role="series"', svg)) <= 1
        fills = set(re.findall(r'fill="([^"]*)"', svg))
        assert fills <= {"none"}, fills
        assert "<title" in svg and "<desc" in svg


def test_every_caption_repeats_n_the_interval_method_and_the_anchor(page):
    captions = re.findall(r"<figcaption>(.*?)</figcaption>", page, re.S)
    assert len(captions) == 11
    for c in captions:
        assert re.search(r"\bn\b", c) and "interval" in c
        assert "not for implementation" in c  # every figure anchor is an AI-DSF draft row
