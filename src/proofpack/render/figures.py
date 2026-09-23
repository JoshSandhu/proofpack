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
  named in the caption and not drawn), labelled with its id; ``AUROC [CI]`` in the
  legend. Not drawn when the array is empty.
* **F3 PR** - ``overall.threshold_free.pr`` ``[[recall, precision, thr], ...]`` and the
  prevalence baseline at ``overall.threshold_free.prevalence.est``. The engine emits no
  ``pr`` array in this build (AUPRC is v1.1), so on every v1 run F3 is the no-data line.
* **F4 calibration** - each ``calibration.decile_curve`` bin at ``(mean_pred,
  observed.est)`` with its Wilson (or cluster-bootstrap) bar ``observed.ci_lo`` to
  ``ci_hi``, the identity line ``ink-faint`` dashed, slope and intercept in the legend,
  the 200/200 note on the plot when ``curve_flag`` is set, and the histogram strip: one
  bar per bin from ``score_min`` to ``score_max`` whose height is the bin's ``n`` under
  the strip's own linear map, filled ``line`` (the only filled mark in any figure).
  **Omitted** when ``calibration`` is null (a score that is not a probability): the
  reason prints instead.
* **F5 forest** - per attribute and per metric (sensitivity, specificity, AUROC): one row
  per level, the reference level first and Unknown/missing last, each a point with its
  interval; a vertical ``ink-faint`` dashed line at the overall estimate; a heavier
  dashed line at a criterion's declared value **only** when a ``ci_lower_bound``
  criterion scoped on that attribute and metric exists, labelled with its id, author and
  date; tier superscripts beside the labels; never a shaded region.

Every series has a dash pattern and a text label, so colour is never the only encoding;
every caption repeats n, the CI method and the guidance anchor.
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


def _anchor_label(refs_by_id: dict[str, dict[str, Any]], internal_id: str) -> str:
    ref = refs_by_id.get(internal_id)
    return ref["label"] if ref else internal_id


# ------------------------------------------------------------------ F2


def f2_roc(document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]) -> dict | None:
    tf = (document.get("overall") or {}).get("threshold_free") or {}
    roc = [r for r in tf.get("roc") or [] if _is_num(r[0]) and _is_num(r[1])]
    if not roc:
        return None
    m = PlotMap(X0, Y0, W, H)
    markers, missing = [], []
    for op, block in (document.get("overall") or {}).items():
        if op == "threshold_free" or not isinstance(block, dict):
            continue
        se = (block.get("sensitivity") or block.get("ppa") or {}).get("est")
        sp = (block.get("specificity") or block.get("npa") or {}).get("est")
        vertex = None
        if _is_num(se) and _is_num(sp):
            for fpr, tpr, *_ in roc:
                if abs(tpr - se) <= MATCH_TOL and abs(fpr - (1.0 - sp)) <= MATCH_TOL:
                    vertex = (fpr, tpr)
                    break
        if vertex is None:
            missing.append(op)
            continue
        markers.append(
            {
                "op": op,
                "cx": _num(m.x(vertex[0])),
                "cy": _num(m.y(vertex[1])),
                "lx": _num(m.x(vertex[0]) + 8),
                "ly": _num(m.y(vertex[1]) - 8),
            }
        )
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
        "curve": _path([(m.x(f), m.y(t)) for f, t, *_ in roc]),
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
            + _anchor_label(refs_by_id, "FDA_AIDSF_PERF_VALIDATION")
        ),
    }


# ------------------------------------------------------------------ F3


F3_ABSENT = (
    "F3 (precision-recall) is not drawn: the run document carries no precision-recall "
    "array; AUPRC is computed from v1.1."
)


def f3_pr(document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]) -> dict | None:
    tf = (document.get("overall") or {}).get("threshold_free") or {}
    pr = [r for r in tf.get("pr") or [] if _is_num(r[0]) and _is_num(r[1])]
    prev = (tf.get("prevalence") or {}).get("est")
    if not pr or not _is_num(prev):
        return None
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
        "curve": _path([(m.x(r), m.y(p)) for r, p, *_ in pr]),
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


def f4_calibration(document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]) -> dict | None:
    cal = document.get("calibration")
    if not isinstance(cal, dict) or not cal.get("decile_curve"):
        return None
    m = PlotMap(X0, Y0, W, H)
    bins = cal["decile_curve"]
    points, bars, strip = [], [], []
    n_max = max(int(b.get("n") or 0) for b in bins) or 1
    s = PlotMap(X0, STRIP_Y0, W, STRIP_H, 0.0, 1.0, 0.0, float(n_max))
    for b in bins:
        obs = (b.get("observed") or {}).get("number") or {}
        if _is_num(b.get("mean_pred")) and _is_num(obs.get("est")):
            x = m.x(b["mean_pred"])
            points.append({"cx": _num(x), "cy": _num(m.y(obs["est"])), "bin": b.get("bin")})
            if _is_num(obs.get("ci_lo")) and _is_num(obs.get("ci_hi")):
                bars.append(
                    {
                        "d": _path([(x, m.y(obs["ci_lo"])), (x, m.y(obs["ci_hi"]))]),
                        "bin": b.get("bin"),
                    }
                )
        if _is_num(b.get("score_min")) and _is_num(b.get("score_max")):
            left, right = s.x(b["score_min"]), s.x(b["score_max"])
            top = s.y(int(b.get("n") or 0))
            strip.append(
                {
                    "x": _num(left),
                    "y": _num(top),
                    "width": _num(right - left),
                    "height": _num(s.y0 + s.h - top),
                    "bin": b.get("bin"),
                }
            )
    slope = (cal.get("slope") or {}).get("number")
    intercept = (cal.get("intercept") or {}).get("number")
    flag = cal.get("curve_flag")
    first = ((bins[0].get("observed") or {}).get("number") or {}).get("method")
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
        "xlabel": "Mean predicted risk",
        "ylabel": "Observed proportion",
        "caption": (
            f"n = {fmt.count(cal.get('n'))} rows ({fmt.count(cal.get('events'))} events) in "
            f"{len(bins)} equal-mass bins; bar interval: "
            f"{METHOD_PHRASES.get(str(first), fmt.text(first))}; "
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


def _criterion_lines(
    document: dict[str, Any], attribute: str, metric: str, m: PlotMap
) -> list[dict[str, Any]]:
    decl = document.get("declarations") or {}
    entries = decl.get("criteria") or []
    seen: set[tuple[str, float]] = set()
    out = []
    for row in document.get("criteria_results") or []:
        scope = row.get("scope")
        if not (
            isinstance(scope, dict)
            and str(scope.get("attribute")) == attribute
            and row.get("metric") == metric
            and row.get("statistic") == "ci_lower_bound"
            and _is_num(row.get("value"))
        ):
            continue
        key = (str(row.get("criterion_id")), float(row["value"]))
        if key in seen:
            continue
        seen.add(key)
        i = row.get("declaration_index")
        entry = entries[i] if isinstance(i, int) and 0 <= i < len(entries) else {}
        x = m.x(row["value"])
        out.append(
            {
                "d": _path([(x, m.y0), (x, m.y0 + m.h)]),
                "x": _num(x),
                "label": (
                    f"customer criterion {fmt.text(row.get('criterion_id'))} "
                    f"({fmt.text(entry.get('author'))}, {fmt.text(entry.get('date'))})"
                ),
                "value": fmt.declared(row["value"]),
            }
        )
    return out


def f5_forest(
    document: dict[str, Any], refs_by_id: dict[str, dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """``{attribute: [figure per metric]}``."""
    rows_all = document.get("subgroups") or []
    overall_op = next((k for k in (document.get("overall") or {}) if k != "threshold_free"), None)
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
        for metric, label in F5_METRICS:
            height = Y0 + ROW_H * len(idx) + 60
            m = PlotMap(FOREST_X0, Y0, FOREST_W, ROW_H * len(idx))
            rows = []
            methods = set()
            for j, i in enumerate(idx):
                r = rows_all[i]
                if metric == "auroc":
                    num = ((r.get("metrics") or {}).get("auroc") or {}).get("number") or {}
                else:
                    cellv = ((r.get("metrics") or {}).get(overall_op) or {}).get(metric) or {}
                    num = cellv.get("number") or {}
                cy = Y0 + ROW_H * (j + 0.5)
                row = {
                    "label": str(r.get("level"))
                    + (" (ref)" if r.get("is_reference") else "")
                    + fmt.tiers(num),
                    "cy": _num(cy),
                    "ty": _num(cy + 4),
                    "drawn": fmt.has_interval(num) if num else False,
                }
                if row["drawn"]:
                    methods.add(str(num.get("method")))
                    row.update(
                        {
                            "cx": _num(m.x(num["est"])),
                            "d": _path([(m.x(num["ci_lo"]), cy), (m.x(num["ci_hi"]), cy)]),
                            "value": fmt.number(
                                num, "proportion" if metric != "auroc" else "three_dp"
                            ),
                        }
                    )
                else:
                    row["value"] = fmt.number(
                        num or None, "proportion" if metric != "auroc" else "three_dp"
                    )
                rows.append(row)
            if metric == "auroc":
                ref_num = ((document.get("overall") or {}).get("threshold_free") or {}).get(
                    "auroc"
                ) or {}
            else:
                ref_num = ((document.get("overall") or {}).get(overall_op) or {}).get(metric) or {}
            reference = None
            if _is_num(ref_num.get("est")):
                rx = m.x(ref_num["est"])
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
                    "95% interval; the dashed line is the overall estimate.",
                    "height": _num(height),
                    "map": m.attr(),
                    "rows": rows,
                    "reference": reference,
                    "criteria": _criterion_lines(document, attribute, metric, m),
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
                        + "; reference line: the overall estimate; "
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
