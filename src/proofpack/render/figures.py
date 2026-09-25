"""Figures F2-F5 as inline SVG (D4 section 6; D5 section 3.4; build day 9, E9 item 5).

The HTML drawer: this module turns the run document's arrays into plot coordinates and
``templates/_figures.html`` draws them. No matplotlib (the DOCX drawer is A-P4's), no
statistic is computed here: every plotted coordinate is a value of ``run.json`` put
through **the documented linear map** :class:`PlotMap`::

    px = x0 + (x - xmin) / (xmax - xmin) * w
    py = y0 + h - (y - ymin) / (ymax - ymin) * h

whose eight constants each figure writes on its plot group as ``data-map`` (``x0 y0 w h
xmin xmax ymin ymax``), so ``tests/test_render_figures.py`` inverts the map from the SVG
alone and compares the result with the arrays to 1e-9. Coordinates are written with
``repr`` (the shortest decimal that reads back to the same double).

What each figure reads:

* **F2 ROC** - ``overall.threshold_free.roc`` ``[[fpr, tpr, thr], ...]`` as one polyline;
  the chance diagonal ``ink-faint`` dashed; each declared operating point a hollow circle
  at **the roc vertex** whose ``(fpr, tpr)`` equals ``(1 - specificity, sensitivity)`` of
  ``overall.<op>`` to 1e-9 (the marker's coordinates are the vertex's, read from the
  array; an operating point with no such vertex - a clustered or ``y_pred``-only run - is
  named in the caption and not drawn; one whose sensitivity or specificity has no
  interval (``format.has_interval`` false) is named in the caption with what that Number
  prints, and not drawn), labelled with its id; ``AUROC [CI]`` in the legend. Not drawn
  when the array is empty.
* **F3 PR** - ``overall.threshold_free.pr`` ``[[recall, precision, thr], ...]`` and the
  prevalence baseline at ``overall.threshold_free.prevalence.est``. The engine emits no
  ``pr`` array in this build (AUPRC is v1.1), so on every v1 run F3 is the no-data line.
* **F4 calibration** - each ``calibration.decile_curve`` bin whose observed Number has an
  interval at ``(mean_pred, observed.est)`` with its bar ``observed.ci_lo`` to ``ci_hi``
  (the caption names the bars' methods from those Numbers, and names each bin not drawn
  with what its Number prints), the identity line ``ink-faint`` dashed, slope and
  intercept in the legend, the note on the plot when ``curve_flag`` is set (its figures
  read from ``curve_flag.minimum``), and the histogram strip: one
  bar per bin from ``score_min`` to ``score_max`` whose height is the bin's ``n`` under
  the strip's own linear map, filled ``line`` (the only filled mark in any figure).
  **Omitted** when ``calibration`` is null (a score that is not a probability): the
  reason prints instead.
* **F5 forest** - per attribute and per metric (sensitivity, specificity, AUROC): one row
  per level, the reference level first and Unknown/missing last, each a point with its
  interval; a vertical ``ink-faint`` dashed line at the overall estimate when that Number
  has an interval (otherwise the caption prints what it prints, and no line); a heavier
  dashed line at a criterion's declared value **only** when a ``ci_lower_bound``
  criterion scoped on that attribute and metric, and declared on the operating point the
  plot draws (none for AUROC), exists, labelled with its id, author and date; tier
  superscripts beside the labels; never a shaded region.

Every series has a dash pattern and a text label, so colour is never the only encoding;
every caption repeats n, the CI method and the guidance anchor.

**One source, two drawers** (D4 section 6; A-P4, build day 10). The selection of what is
drawn - which ROC vertices, which operating point marks a vertex, which decile bins have
an interval, which subgroup rows, the reference and criterion values - is made once, in
the data-level functions :func:`f2_data`, :func:`f3_data`, :func:`f4_data` and
:func:`f5_data`, on the arrays of ``run.json`` and nothing else. This module's SVG
functions put those data coordinates through :class:`PlotMap`;
:mod:`proofpack.render.figures_png` hands the same data coordinates to matplotlib.
``tests/test_ap4_figures.py`` reads the coordinates back from the matplotlib artists and
compares them with the SVG's parsed points through the inverse of the documented map,
to 1e-9.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from proofpack.narrate.templates import METHOD_PHRASES
from proofpack.render import format as fmt

VIEW_W = 600
#: The ROC, PR and calibration plot area inside a 600-wide view box.
X0, Y0, W, H = 70.0, 20.0, 480.0, 320.0
STRIP_Y0, STRIP_H = 372.0, 40.0
ROW_H = 26.0
#: F5: level labels left of the plot, the printed cell right of it.
FOREST_X0, FOREST_W = 190.0, 230.0
MATCH_TOL = 1e-9


@dataclass(frozen=True)
class PlotMap:
    """The documented linear map from data to SVG user units (see the module docstring)."""

    x0: float
    y0: float
    w: float
    h: float
    xmin: float = 0.0
    xmax: float = 1.0
    ymin: float = 0.0
    ymax: float = 1.0

    def x(self, v: float) -> float:
        return self.x0 + (float(v) - self.xmin) / (self.xmax - self.xmin) * self.w

    def y(self, v: float) -> float:
        return self.y0 + self.h - (float(v) - self.ymin) / (self.ymax - self.ymin) * self.h

    def attr(self) -> str:
        return " ".join(
            repr(float(v))
            for v in (self.x0, self.y0, self.w, self.h, self.xmin, self.xmax, self.ymin, self.ymax)
        )


def _num(v: float) -> str:
    return repr(float(v))


def _path(points: list[tuple[float, float]]) -> str:
    return " ".join(
        f"{'M' if i == 0 else 'L'}{_num(x)},{_num(y)}" for i, (x, y) in enumerate(points)
    )


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _ticks(m: PlotMap) -> dict[str, Any]:
    return {
        "x": [{"pos": _num(m.x(t)), "label": f"{t:.1f}"} for t in (0.0, 0.5, 1.0)],
        "y": [{"pos": _num(m.y(t)), "label": f"{t:.1f}"} for t in (0.0, 0.5, 1.0)],
        "left": _num(m.x0),
        "right": _num(m.x0 + m.w),
        "top": _num(m.y0),
        "bottom": _num(m.y0 + m.h),
    }


def method_list(nums: list[dict[str, Any]]) -> str:
    """The distinct ``method`` of ``nums``, each by its :data:`METHOD_PHRASES` phrase (the
    id itself when the map has none), sorted by id and joined with ``; ``."""
    ids = sorted({str(n.get("method")) for n in nums if isinstance(n, dict)})
    return "; ".join(METHOD_PHRASES.get(m, m) for m in ids) or "no Number printed"


def _anchor_label(refs_by_id: dict[str, dict[str, Any]], internal_id: str) -> str:
    ref = refs_by_id.get(internal_id)
    return ref["label"] if ref else internal_id


# ------------------------------------------------------------------ F2


def f2_data(document: dict[str, Any]) -> dict[str, Any] | None:
    """F2's data coordinates: the ROC vertices ``[(fpr, tpr), ...]`` in array order, the
    operating points drawn ``[(op, fpr, tpr)]`` (each at its matching vertex), and the
    two lists the caption names (``missing``: no matching vertex; ``typed``: a Number
    without an interval). ``None`` when the array is empty."""
    tf = (document.get("overall") or {}).get("threshold_free") or {}
    roc = [r for r in tf.get("roc") or [] if _is_num(r[0]) and _is_num(r[1])]
    if not roc:
        return None
    markers, missing, typed = [], [], []
    for op, block in (document.get("overall") or {}).items():
        if op == "threshold_free" or not isinstance(block, dict):
            continue
        se_key = "sensitivity" if block.get("sensitivity") else "ppa"
        sp_key = "specificity" if block.get("specificity") else "npa"
        se_num = block.get(se_key) or {}
        sp_num = block.get(sp_key) or {}
        if not (fmt.has_interval(se_num) and fmt.has_interval(sp_num)):
            # a typed reason prints the reason, never a bare estimate (E9 repair 1, FA-B3)
            printed = [
                f"{name} {fmt.number(num or None, 'proportion')}"
                for name, num in ((se_key, se_num), (sp_key, sp_num))
                if not fmt.has_interval(num)
            ]
            typed.append(f"{op} ({', '.join(printed)})")
            continue
        se = se_num.get("est")
        sp = sp_num.get("est")
        vertex = None
        if _is_num(se) and _is_num(sp):
            for fpr, tpr, *_ in roc:
                if abs(tpr - se) <= MATCH_TOL and abs(fpr - (1.0 - sp)) <= MATCH_TOL:
                    vertex = (fpr, tpr)
                    break
        if vertex is None:
            missing.append(op)
            continue
        markers.append((op, float(vertex[0]), float(vertex[1])))
    return {
        "roc": [(float(f), float(t)) for f, t, *_ in roc],
        "markers": markers,
        "missing": missing,
        "typed": typed,
    }


def f2_roc(document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]) -> dict | None:
    data = f2_data(document)
    if data is None:
        return None
    tf = (document.get("overall") or {}).get("threshold_free") or {}
    m = PlotMap(X0, Y0, W, H)
    missing, typed = data["missing"], data["typed"]
    markers = [
        {
            "op": op,
            "cx": _num(m.x(fx)),
            "cy": _num(m.y(ty)),
            "lx": _num(m.x(fx) + 8),
            "ly": _num(m.y(ty) - 8),
        }
        for op, fx, ty in data["markers"]
    ]
    auroc = tf.get("auroc") or {}
    n_pos, n_neg = auroc.get("n_pos"), auroc.get("n_neg")
    method = METHOD_PHRASES.get(str(auroc.get("method")), fmt.text(auroc.get("method")))
    clustered = bool((document.get("flow") or {}).get("clustered"))
    return {
        "id": "F2",
        "title": "F2 - ROC curve",
        "desc": "False positive rate on the horizontal axis, true positive rate on the "
        "vertical; the dashed line is chance; hollow circles mark the declared operating "
        "points.",
        "height": 380,
        "map": m.attr(),
        "ticks": _ticks(m),
        "curve": _path([(m.x(f), m.y(t)) for f, t in data["roc"]]),
        "reference": _path([(m.x(0), m.y(0)), (m.x(1), m.y(1))]),
        "markers": markers,
        "legend": f"ROC curve (solid); AUROC {fmt.number(auroc or None, 'three_dp')}",
        # below the chance diagonal, where a curve above chance does not run
        "legend_x": 250,
        "legend_y": 300,
        "xlabel": "False positive rate (1 - specificity)",
        "ylabel": "True positive rate (sensitivity)",
        "caption": (
            f"n = {fmt.count(n_pos)} positive and {fmt.count(n_neg)} negative rows; AUROC "
            f"interval: {method}; "
            + ("clustered path (cases resampled); " if clustered else "independent rows; ")
            + (
                "operating point(s) with no matching curve vertex, not drawn: "
                + ", ".join(missing)
                + "; "
                if missing
                else ""
            )
            + (
                "operating point(s) not drawn, a Number without an interval: "
                + ", ".join(typed)
                + "; "
                if typed
                else ""
            )
            + _anchor_label(refs_by_id, "FDA_AIDSF_PERF_VALIDATION")
        ),
    }


# ------------------------------------------------------------------ F3


F3_ABSENT = (
    "F3 (precision-recall) is not drawn: the run document carries no precision-recall "
    "array; AUPRC is computed from v1.1."
)


def f3_data(document: dict[str, Any]) -> dict[str, Any] | None:
    """F3's data coordinates: the PR vertices ``[(recall, precision), ...]`` and the
    prevalence baseline's value; ``None`` without a ``pr`` array or a prevalence."""
    tf = (document.get("overall") or {}).get("threshold_free") or {}
    pr = [r for r in tf.get("pr") or [] if _is_num(r[0]) and _is_num(r[1])]
    prev = (tf.get("prevalence") or {}).get("est")
    if not pr or not _is_num(prev):
        return None
    return {"pr": [(float(r), float(p)) for r, p, *_ in pr], "prevalence": float(prev)}


def f3_pr(document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]) -> dict | None:
    data = f3_data(document)
    if data is None:
        return None
    tf = (document.get("overall") or {}).get("threshold_free") or {}
    pr, prev = data["pr"], data["prevalence"]
    m = PlotMap(X0, Y0, W, H)
    prevalence = tf.get("prevalence") or {}
    return {
        "id": "F3",
        "title": "F3 - precision-recall curve",
        "desc": "Recall on the horizontal axis, precision on the vertical; the dashed line "
        "is the prevalence baseline.",
        "height": 380,
        "map": m.attr(),
        "ticks": _ticks(m),
        "curve": _path([(m.x(r), m.y(p)) for r, p in pr]),
        "reference": _path([(m.x(0), m.y(prev)), (m.x(1), m.y(prev))]),
        "markers": [],
        "legend": "PR curve (solid); prevalence baseline (dashed) "
        + fmt.number(prevalence, "proportion"),
        "legend_x": 90,
        "legend_y": 330,
        "xlabel": "Recall (sensitivity)",
        "ylabel": "Precision (PPV)",
        "caption": (
            f"n = {fmt.count(prevalence.get('n'))} rows; prevalence interval: "
            f"{METHOD_PHRASES.get(str(prevalence.get('method')), '')}; "
            + _anchor_label(refs_by_id, "FDA_AIDSF_PERF_VALIDATION")
        ),
    }


# ------------------------------------------------------------------ F4


def f4_data(document: dict[str, Any]) -> dict[str, Any] | None:
    """F4's data coordinates: each drawn bin as ``(bin, mean_pred, est, ci_lo, ci_hi)``,
    each histogram bar as ``(bin, score_min, score_max, n)`` with ``n_max`` the strip's
    ceiling, the Numbers drawn (for the caption's methods) and the bins not drawn (with
    what their Number prints). ``None`` when ``calibration`` is null or has no bins."""
    cal = document.get("calibration")
    if not isinstance(cal, dict) or not cal.get("decile_curve"):
        return None
    bins = cal["decile_curve"]
    points, strip, not_drawn, drawn_nums = [], [], [], []
    n_max = max(int(b.get("n") or 0) for b in bins) or 1
    for b in bins:
        obs = (b.get("observed") or {}).get("number") or {}
        if _is_num(b.get("mean_pred")) and fmt.has_interval(obs) and _is_num(obs.get("est")):
            drawn_nums.append(obs)
            points.append(
                (
                    b.get("bin"),
                    float(b["mean_pred"]),
                    float(obs["est"]),
                    float(obs["ci_lo"]),
                    float(obs["ci_hi"]),
                )
            )
        else:
            # a typed reason prints the reason, never a bare estimate (E9 repair 1, FA-B3)
            not_drawn.append(
                f"bin {fmt.count(b.get('bin'))} {fmt.number(obs or None, 'proportion')}"
            )
        if _is_num(b.get("score_min")) and _is_num(b.get("score_max")):
            strip.append(
                (b.get("bin"), float(b["score_min"]), float(b["score_max"]), int(b.get("n") or 0))
            )
    return {
        "points": points,
        "strip": strip,
        "n_max": n_max,
        "drawn_nums": drawn_nums,
        "not_drawn": not_drawn,
    }


def f4_calibration(document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]) -> dict | None:
    data = f4_data(document)
    if data is None:
        return None
    cal = document["calibration"]
    bins = cal["decile_curve"]
    m = PlotMap(X0, Y0, W, H)
    s = PlotMap(X0, STRIP_Y0, W, STRIP_H, 0.0, 1.0, 0.0, float(data["n_max"]))
    not_drawn, drawn_nums = data["not_drawn"], data["drawn_nums"]
    points, bars, strip = [], [], []
    for b, mean_pred, est, lo, hi in data["points"]:
        x = m.x(mean_pred)
        points.append({"cx": _num(x), "cy": _num(m.y(est)), "bin": b})
        bars.append({"d": _path([(x, m.y(lo)), (x, m.y(hi))]), "bin": b})
    for b, score_min, score_max, n in data["strip"]:
        left, right = s.x(score_min), s.x(score_max)
        top = s.y(n)
        strip.append(
            {
                "x": _num(left),
                "y": _num(top),
                "width": _num(right - left),
                "height": _num(s.y0 + s.h - top),
                "bin": b,
            }
        )
    slope = (cal.get("slope") or {}).get("number")
    intercept = (cal.get("intercept") or {}).get("number")
    flag = cal.get("curve_flag")
    minimum = flag.get("minimum") if isinstance(flag, dict) else None
    return {
        "id": "F4",
        "title": "F4 - calibration by decile",
        "desc": "Mean predicted risk on the horizontal axis, observed proportion on the "
        "vertical, one point per decile with its interval; the dashed line is identity; "
        "the strip below shows where the predicted risks lie.",
        "height": 430,
        "map": m.attr(),
        "strip_map": s.attr(),
        "ticks": _ticks(m),
        "points": points,
        "bars": bars,
        "strip": strip,
        "strip_top": _num(STRIP_Y0),
        "reference": _path([(m.x(0), m.y(0)), (m.x(1), m.y(1))]),
        "legend": (
            f"deciles (points, solid bars); slope {fmt.number(slope, 'three_dp')}; "
            f"intercept {fmt.number(intercept, 'three_dp')}"
        ),
        "flag": fmt.text(flag.get("note")) if isinstance(flag, dict) else None,
        # the on-plot line reads curve_flag.minimum; no number is typed into the template
        # (E9 repair 1, lens RG-B1)
        "flag_short": (
            f"{fmt.count(minimum)}/{fmt.count(minimum)} convention: fewer than "
            f"{fmt.count(minimum)} events or non-events"
            if isinstance(flag, dict) and _is_num(minimum)
            else None
        ),
        "xlabel": "Mean predicted risk",
        "ylabel": "Observed proportion",
        "caption": (
            f"n = {fmt.count(cal.get('n'))} rows ({fmt.count(cal.get('events'))} events) in "
            f"{len(bins)} equal-mass bins; "
            # E9 repair 2 (lens-2 FA-N7): with no bin drawn, method_list's empty value
            # ("no Number printed") sat beside the n.e. Numbers this caption prints
            + (f"bar interval: {method_list(drawn_nums)}; " if drawn_nums else "no bar drawn; ")
            + ("not drawn, no interval: " + ", ".join(not_drawn) + "; " if not_drawn else "")
            + _anchor_label(refs_by_id, "FDA_AIDSF_CALIBRATION")
        ),
    }


def f4_absent_note(document: dict[str, Any]) -> str | None:
    cal = document.get("calibration")
    if isinstance(cal, dict):
        return None
    reason = document.get("calibration_suppressed_reason")
    code = reason.get("reason") if isinstance(reason, dict) else None
    return f"F4 (calibration) is omitted: calibration is null ({code or 'no reason recorded'})."


# ------------------------------------------------------------------ F5


F5_METRICS: tuple[tuple[str, str], ...] = (
    ("sensitivity", "Sensitivity"),
    ("specificity", "Specificity"),
    ("auroc", "AUROC"),
)
#: Under a declared comparator the subgroup rows carry PPA / NPA (FDA 2007; D4 5.2).
F5_METRICS_COMPARATOR: tuple[tuple[str, str], ...] = (
    ("ppa", "PPA"),
    ("npa", "NPA"),
    ("auroc", "AUROC"),
)


def criterion_values(
    document: dict[str, Any], attribute: str, metric: str, op: str | None
) -> list[dict[str, Any]]:
    """The criterion lines of one F5 plot as data: ``[{value, label, value_text}]``. ``op``
    is the operating point the plot
    draws, or ``None`` for the AUROC plot. This reads each criteria row's
    ``operating_point`` and draws the row only when it equals ``op``. The ``None`` case
    follows D1 section 2's H09 rules as io/declare.py applies them: an operating point on
    an ``auroc`` criterion is H09 (``test_criteria.py::
    test_a_threshold_free_metric_with_an_operating_point_is_h09``) and a threshold
    metric's criterion without one is H09 (``test_a_threshold_metric_without_an_
    operating_point_is_h09``). E9 repair 3, lens-3 FA-B1: before this, a criterion
    declared on op2 was drawn on the plot captioned op1
    (``test_e9_repair3.py::test_an_op2_criterion_draws_no_line_on_the_op1_f5_plot``).

    The criteria row carries no ``type``; it is read from the declaration entry the row's
    ``declaration_index`` names, and a row whose entry declares ``type:
    paired_difference_vs_prior`` is not drawn. E9 repair 4, lens-4 FA-B1: before this,
    ``Cpd`` (sensitivity, op1, sex = F, value -0.05) was drawn at x = 178.5 on the op1
    sensitivity plot and ``Cauc_pd`` (auroc, 0.55) on the AUROC plot
    (``test_e9_repair4.py::test_a_paired_difference_criterion_draws_no_f5_line``)."""
    decl = document.get("declarations") or {}
    entries = decl.get("criteria") or []
    seen: set[tuple[str, float]] = set()
    out: list[dict[str, Any]] = []
    for row in document.get("criteria_results") or []:
        scope = row.get("scope")
        row_op = row.get("operating_point")
        i = row.get("declaration_index")
        entry = entries[i] if isinstance(i, int) and 0 <= i < len(entries) else {}
        if not (
            isinstance(scope, dict)
            and str(scope.get("attribute")) == attribute
            and row.get("metric") == metric
            and (None if row_op is None else str(row_op)) == op
            and row.get("statistic") == "ci_lower_bound"
            and _is_num(row.get("value"))
            and entry.get("type") != "paired_difference_vs_prior"
        ):
            continue
        key = (str(row.get("criterion_id")), float(row["value"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "value": float(row["value"]),
                "label": (
                    f"customer criterion {fmt.text(row.get('criterion_id'))} "
                    f"({fmt.text(entry.get('author'))}, {fmt.text(entry.get('date'))})"
                ),
                "value_text": fmt.declared(row["value"]),
            }
        )
    return out


def _criterion_lines(
    document: dict[str, Any], attribute: str, metric: str, op: str | None, m: PlotMap
) -> list[dict[str, Any]]:
    """:func:`criterion_values` through the map: the dashed lines of one F5 plot."""
    out = []
    for c in criterion_values(document, attribute, metric, op):
        x = m.x(c["value"])
        out.append(
            {
                "d": _path([(x, m.y0), (x, m.y0 + m.h)]),
                "x": _num(x),
                "label": c["label"],
                "value": c["value_text"],
            }
        )
    return out


def f5_data(document: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """F5's data, ``{attribute: [per metric]}``: each entry carries ``metric``, ``label``,
    ``op`` (the operating point drawn; ``None`` for AUROC), ``rows`` - one per subgroup
    row in plot order (the reference level first, Unknown/missing last) as ``{label,
    drawn, est, ci_lo, ci_hi, value, method}`` (``est`` and the bounds ``None`` when not
    drawn; ``value`` is what the row's Number prints), ``reference`` (the overall
    estimate, or ``None`` when that Number has no interval), ``ref_num`` and the
    criterion values of :func:`criterion_values`."""
    rows_all = document.get("subgroups") or []
    overall_op = next((k for k in (document.get("overall") or {}) if k != "threshold_free"), None)
    ref_type = ((document.get("declarations") or {}).get("reference_standard") or {}).get("type")
    metrics = F5_METRICS if ref_type != "comparator" else F5_METRICS_COMPARATOR
    out: dict[str, list[dict[str, Any]]] = {}
    for meta in sorted(
        (a for a in document.get("subgroup_attributes") or [] if isinstance(a, dict)),
        key=lambda a: str(a.get("attribute")),
    ):
        attribute = str(meta.get("attribute"))
        order = [str(x) for x in meta.get("level_order") or []]
        idx = [i for i, r in enumerate(rows_all) if str(r.get("attribute")) == attribute]

        def rank(i: int, _order=order) -> tuple[int, int, str]:
            r = rows_all[i]
            lv = str(r.get("level"))
            if r.get("is_reference"):
                return (0, 0, lv)
            if r.get("is_unknown_row"):
                return (2, 0, lv)
            return (1, _order.index(lv) if lv in _order else len(_order), lv)

        idx.sort(key=rank)
        figs = []
        for metric, label in metrics:
            kind = "proportion" if metric != "auroc" else "three_dp"
            rows = []
            for i in idx:
                r = rows_all[i]
                if metric == "auroc":
                    num = ((r.get("metrics") or {}).get("auroc") or {}).get("number") or {}
                else:
                    cellv = ((r.get("metrics") or {}).get(overall_op) or {}).get(metric) or {}
                    num = cellv.get("number") or {}
                drawn = fmt.has_interval(num) if num else False
                rows.append(
                    {
                        "label": str(r.get("level"))
                        + (" (ref)" if r.get("is_reference") else "")
                        + fmt.tiers(num),
                        "drawn": drawn,
                        "est": float(num["est"]) if drawn else None,
                        "ci_lo": float(num["ci_lo"]) if drawn else None,
                        "ci_hi": float(num["ci_hi"]) if drawn else None,
                        "value": fmt.number(num or None, kind),
                        "method": str(num.get("method")) if drawn else None,
                    }
                )
            if metric == "auroc":
                ref_num = ((document.get("overall") or {}).get("threshold_free") or {}).get(
                    "auroc"
                ) or {}
            else:
                ref_num = ((document.get("overall") or {}).get(overall_op) or {}).get(metric) or {}
            reference = (
                float(ref_num["est"])
                if fmt.has_interval(ref_num) and _is_num(ref_num.get("est"))
                else None
            )
            op = None if metric == "auroc" else overall_op
            figs.append(
                {
                    "metric": metric,
                    "label": label,
                    "op": op,
                    "rows": rows,
                    "reference": reference,
                    "ref_num": ref_num,
                    "criteria": criterion_values(document, attribute, metric, op),
                }
            )
        out[attribute] = figs
    return out


def f5_forest(
    document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """``{attribute: [figure per metric]}``: :func:`f5_data` through the map."""
    overall_op = next((k for k in (document.get("overall") or {}) if k != "threshold_free"), None)
    out: dict[str, list[dict[str, Any]]] = {}
    for attribute, data_figs in f5_data(document).items():
        figs = []
        for d in data_figs:
            metric, label = d["metric"], d["label"]
            n_rows = len(d["rows"])
            height = Y0 + ROW_H * n_rows + 60
            m = PlotMap(FOREST_X0, Y0, FOREST_W, ROW_H * n_rows)
            rows = []
            methods = set()
            for j, dr in enumerate(d["rows"]):
                cy = Y0 + ROW_H * (j + 0.5)
                row = {
                    "label": dr["label"],
                    "cy": _num(cy),
                    "ty": _num(cy + 4),
                    "drawn": dr["drawn"],
                }
                if row["drawn"]:
                    methods.add(dr["method"])
                    row.update(
                        {
                            "cx": _num(m.x(dr["est"])),
                            "d": _path([(m.x(dr["ci_lo"]), cy), (m.x(dr["ci_hi"]), cy)]),
                            "value": dr["value"],
                        }
                    )
                else:
                    row["value"] = dr["value"]
                rows.append(row)
            ref_num = d["ref_num"]
            reference = None
            if d["reference"] is not None:
                rx = m.x(d["reference"])
                reference = {
                    "d": _path([(rx, m.y0), (rx, m.y0 + m.h)]),
                    "x": _num(rx),
                }
            figs.append(
                {
                    "id": f"F5-{attribute}-{metric}",
                    "attribute": attribute,
                    "metric": metric,
                    "title": f"F5 - {label} by {attribute}",
                    "desc": f"One row per level of {attribute}: the point estimate and its "
                    "95% interval"
                    + ("; the dashed line is the overall estimate." if reference else "."),
                    "height": _num(height),
                    "map": m.attr(),
                    "rows": rows,
                    "reference": reference,
                    "criteria": _criterion_lines(document, attribute, metric, d["op"], m),
                    "axis": {
                        "left": _num(m.x0),
                        "right": _num(m.x0 + m.w),
                        "values_x": _num(m.x0 + m.w + 10),
                        "y": _num(m.y0 + m.h),
                        "ticks": [
                            {"pos": _num(m.x(t)), "label": f"{t:.1f}"} for t in (0.0, 0.5, 1.0)
                        ],
                    },
                    "caption": (
                        f"{label} by {attribute}"
                        + (f" at operating point {overall_op}" if metric != "auroc" else "")
                        + "; n per level as in Table T1-10; interval: "
                        + (", ".join(sorted(METHOD_PHRASES.get(x, x) for x in methods)) or "none")
                        + (
                            "; reference line: the overall estimate; "
                            if reference is not None
                            else "; no reference line: the overall estimate is "
                            + fmt.number(
                                ref_num or None, "proportion" if metric != "auroc" else "three_dp"
                            )
                            + "; "
                        )
                        + _anchor_label(refs_by_id, "FDA_AIDSF_SUBGROUP_PERF")
                    ),
                }
            )
        out[attribute] = figs
    return out


def figures(document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The figure specs T1 draws (the no-data lines where a figure is not drawn)."""
    return {
        "f2": f2_roc(document, refs_by_id),
        "f3": f3_pr(document, refs_by_id),
        "f3_note": F3_ABSENT,
        "f4": f4_calibration(document, refs_by_id),
        "f4_note": f4_absent_note(document),
        "f5": f5_forest(document, refs_by_id),
    }
