"""The criteria engine (build day 7, E7): ``criteria.yaml`` criteria against the run document.

Where this lives and why: it reads the *assembled document* (``overall``, ``subgroups``,
``calibration``, ``fairness``) by path and compares one field of one Number to one value
the customer wrote. It computes no statistic, so it is not a ``stats`` module; it is the
run's last step before the document is written, beside ``gates`` in the package root.

What it does, and only this (D1 section 2 rules; CLAUDE.md "no vendor-set acceptance
criteria or verdicts"):

* every value compared to comes from ``criteria.yaml`` - ``statistic``, ``comparator`` and
  ``value`` are required by ``schema/criteria_schema.json`` and no default exists here for
  any of them; a criterion the schema rejects is H08 naming the field (``io.declare``), a
  criterion naming an unknown metric, operating point, attribute or level is H09 there;
* every criterion yields **exactly one** of ``met`` / ``not_met`` / ``not_assessable``
  with a machine ``reason_code`` from :data:`REASON_CODES`; the words themselves appear
  in the document only under ``criteria_results`` (the day-5/6/7 verdict greps check the
  rest of the document for them);
* the statistic named is the one compared, literally: ``ci_lower_bound`` is the Number's
  ``ci_lo`` whatever the comparator, ``ci_upper_bound`` its ``ci_hi``, ``point_estimate``
  its ``est``. The engine does not swap to "the conservative end" for a ``<=`` criterion,
  because that would be the engine choosing the statistic; a customer who wants the
  upper end of the interval names ``ci_upper_bound`` (an addition to D1 section 2's two
  values, recorded in the E7 build note). T8's column heading says which end was read;
* :func:`_row` routes on the Number's ``method`` and ``not_estimable_reason`` *before* it
  reads any statistic: a Number with ``method: none`` (a typed ``not_estimable_reason``,
  no interval) is ``not_assessable`` / ``no_interval`` with the reason in ``detail`` under
  each of the three statistics, ``point_estimate`` included, and a suppressed one is
  ``not_assessable`` / ``suppressed``. Inspected by ``tests/test_criteria.py::
  test_a_number_with_method_none_is_not_assessable_under_each_of_the_three_statistics``
  (a hand-built Number ``est 0.90``, ``single_class``) and ``tests/test_run_cli.py::
  test_point_estimate_criteria_on_f1_and_mcc_read_method_none_as_not_assessable`` (the
  synthetic run's ``overall.op1.f1`` and ``mcc``, ``analytic_ci_unavailable``). At
  ``ab729d3`` both were compared on ``est`` (lens 1 of 21 September, B1);
* ``attainable_at_n`` / ``max_lower_bound_at_n`` (``stats.attainability``) are touched
  only for a ``ci_lower_bound`` criterion on a proportion metric (``PROPORTION_METRICS``);
  under any other statistic or metric both are ``null`` and ``detail`` carries no
  attainability key. For that criterion, :func:`_row` inspects the Number's ``method``
  and ``n``: both fields are filled when ``method`` is ``wilson`` (the interval the k = n
  figure is a case of) and ``n`` is an ``int`` above 0; when ``method`` is anything else
  (``cluster_bootstrap_percentile``, ``none``) both are ``null`` and
  ``detail.attainability_not_computed`` is ``method_not_wilson``, whatever ``n`` (0 and
  ``null`` included); a ``wilson`` Number whose ``n`` is not an ``int`` above 0 leaves
  both ``null`` with no annotation (the guard as written: ``isinstance(n, int) and
  n > 0``). Inspected by ``tests/test_criteria.py::
  test_a_cluster_bootstrap_cell_gets_no_attainability_flag`` (at ``ab729d3`` a ``met``
  row on ``ci_lo 0.9`` carried ``attainable_at_n false`` against ``0.8865`` at n = 30: a
  cluster-bootstrap lower bound is not bounded by the Wilson k = n figure) and
  ``::test_a_method_none_number_at_n_zero_or_n_null_is_annotated_method_not_wilson``
  (at ``02d00c5`` the annotation sat under ``n > 0``, so a ``zero_denominator`` Number at
  n = 0 carried none). No sample-size advice.

Which field each criterion reads
--------------------------------

``overall`` metrics are D1 section 4.1 Numbers directly (``overall.op1.sensitivity``);
subgroup, calibration and fairness quantities are day-4 cells ``{number, analytic, ...}``
and the criterion reads ``number`` - the Number the renderer prints - never ``analytic``
(the companion refusal or the analytic Number that was replaced). ``metric_ref`` is the
JSON path of the Number read, in the form D1 section 4.2 shows
(``subgroups[3].metrics.op1.sensitivity``), with ``.number`` appended for a cell.

============================ ==================================================== ====
metric                       read from                                            op
============================ ==================================================== ====
sensitivity, specificity,    ``overall.<op>.<metric>`` (Number);                  yes
ppa, npa, ppv, npv,          ``subgroups[i].metrics.<op>.<metric>.number``
accuracy
balanced_accuracy, f1, mcc,  ``overall.<op>.<metric>`` only; a subgroup scope is   yes
lr_pos, lr_neg, dor, youden  ``metric_not_computed_for_scope`` (day-5 rows carry
                             the five proportions above)
auroc                        ``overall.threshold_free.auroc``;                    no
                             ``subgroups[i].metrics.auroc.number``
prevalence                   ``overall.threshold_free.prevalence``                no
brier                        ``calibration.brier.number``;                        no
                             ``subgroups[i].metrics.brier.number``
ipa, oe, calibration_slope,  ``calibration.<ipa|oe|slope|intercept>.number``;     no
calibration_intercept        a subgroup scope is ``metric_not_computed_for_scope``
tpr_gap, fpr_gap, ppv_gap,   ``fairness.gaps[j].operating_points.<op>.<gap>.number`` yes
npv_gap                      on the fairness attribute's levels only
auroc_gap                    ``fairness.gaps[j].auroc_gap.number``                no
ece, auprc, psi, ks_d and    ``not_assessable`` / ``metric_not_computed`` (no       no
the lite ids                 Number with an interval exists for them in v1)
============================ ==================================================== ====

A ``scope`` of ``overall`` reads the overall / calibration block; ``{attribute, level}``
with ``level: "*"`` yields one row per tabulated level of the attribute (the explicit
``Unknown/missing`` row excluded - the customer names it to include it); a named level
yields one row. A gap criterion's scope must name a level; the reference level has no gap
and is ``not_assessable`` / ``level_is_reference``.

The fairness block's ``bound`` is evaluated the same way on the declared
``criterion_of_interest`` of every non-reference level, with the ``statistic`` and
``comparator`` the customer wrote beside the bound (both required by the schema when a
bound is present); ``calibration_by_group`` is ``not_assessable`` until calibration by
group is computed. Without a bound the block is descriptive and no row is emitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from proofpack.io.declare import Declarations
from proofpack.stats.attainability import PROPORTION_METRICS, attainable, max_lower_bound_at_n

STATUSES: tuple[str, ...] = ("met", "not_met", "not_assessable")

#: Closed set of machine reasons. ``statistic_compared`` is the reason on every ``met`` /
#: ``not_met`` row; the rest are the ``not_assessable`` reasons (D1 section 2: "metric not
#: computed, cell suppressed, CI not estimable, comparator not like-for-like").
REASON_CODES: dict[str, str] = {
    "statistic_compared": "the named statistic was compared with the comparator to value",
    "no_interval": "the Number carries a typed not_estimable_reason and no interval",
    "suppressed": "the Number is suppressed (k-suppression)",
    "metric_not_computed": "no Number with an interval exists for this metric id in v1",
    "metric_not_computed_for_scope": "the metric is computed overall but not for a subgroup",
    "calibration_suppressed": "the calibration block is null (score not a probability)",
    "no_calibration_block": "the calibration block is absent (no score column)",
    "level_absent": "the attribute has no tabulated level in scope",
    "level_is_reference": "a gap is a difference against the reference level, which has none",
    "gap_requires_fairness_attribute": "gap metrics are computed on the fairness attribute",
    "no_fairness_block": "no fairness block was declared, so no gaps exist",
    "requires_compare": "a paired_difference_vs_prior criterion is evaluated by compare",
    "overall_not_computed": "the overall block is null in this document",
    "not_estimable_this_run": "the quantity is reported without an interval in v1",
    # build day 10 (E10, compare): a paired_difference_vs_prior criterion on an unpaired
    # comparison (H12 with --allow-unpaired; D1 section 2: "comparator not like-for-like")
    "not_like_for_like": "the comparison is unpaired, so no paired difference exists",
    # a paired criterion whose scope the comparison block carries no difference for
    "comparison_not_computed_for_scope": "the comparison carries no paired difference in scope",
}

STATISTICS: tuple[str, ...] = ("ci_lower_bound", "ci_upper_bound", "point_estimate")
COMPARATORS: tuple[str, ...] = (">=", ">", "<=", "<")
#: The one ``method`` string whose interval ``max_lower_bound_at_n`` (the Wilson lower
#: bound at k = n) is a case of; on any other method the attainability fields are ``null``
#: and ``detail.attainability_not_computed`` says so.
ATTAINABILITY_METHOD = "wilson"

#: Metrics read at an operating point (``operating_point`` required; H09 otherwise).
THRESHOLD_METRICS: frozenset[str] = frozenset(
    {
        "sensitivity",
        "specificity",
        "ppa",
        "npa",
        "ppv",
        "npv",
        "accuracy",
        "balanced_accuracy",
        "f1",
        "mcc",
        "lr_pos",
        "lr_neg",
        "dor",
        "youden",
        "tpr_gap",
        "fpr_gap",
        "ppv_gap",
        "npv_gap",
    }
)
#: The five proportions the day-5 subgroup rows carry per operating point.
SUBGROUP_OP_METRICS: frozenset[str] = frozenset(
    {"sensitivity", "specificity", "ppa", "npa", "ppv", "npv", "accuracy"}
)
GAP_METRICS: frozenset[str] = frozenset({"tpr_gap", "fpr_gap", "ppv_gap", "npv_gap"})
CALIBRATION_KEYS: dict[str, str] = {
    "brier": "brier",
    "ipa": "ipa",
    "oe": "oe",
    "calibration_slope": "slope",
    "calibration_intercept": "intercept",
}
#: Metric ids the run computes no Number with an interval for (v1): ``not_assessable``.
NOT_COMPUTED_METRICS: frozenset[str] = frozenset(
    {
        "ece",  # descriptive, no interval (R2: "treat ECE as descriptive")
        "auprc",  # v1.1
        "psi",
        "ks_d",  # monitor (drift), not run
        "kappa",
        "macro_auroc",
        "bias",
        "loa_low",
        "loa_high",
        "mae",
        "rmse",
        "ccc",
        "dice_mean",
        "dice_median",  # lite tasks, descriptive only
    }
)


def needs_operating_point(metric: str) -> bool:
    return metric in THRESHOLD_METRICS


@dataclass(frozen=True)
class _Read:
    """One resolved Number (or the reason none could be read)."""

    number: dict[str, Any] | None
    metric_ref: str | None
    reason: str | None = None
    detail: dict[str, Any] | None = None


def _compare(statistic_value: float, comparator: str, value: float) -> bool:
    if comparator == ">=":
        return statistic_value >= value
    if comparator == ">":
        return statistic_value > value
    if comparator == "<=":
        return statistic_value <= value
    if comparator == "<":
        return statistic_value < value
    raise ValueError(f"unknown comparator {comparator!r}")


def _statistic_of(number: dict[str, Any], statistic: str) -> float | None:
    if statistic == "ci_lower_bound":
        return number.get("ci_lo")
    if statistic == "ci_upper_bound":
        return number.get("ci_hi")
    if statistic == "point_estimate":
        return number.get("est")
    raise ValueError(f"unknown statistic {statistic!r}")


def _cell_number(cell: Any, ref: str) -> _Read:
    """The ``number`` of a day-4 cell at ``ref``, or a typed reason."""
    if cell is None:
        return _Read(None, ref, "metric_not_computed")
    if not isinstance(cell, dict) or "number" not in cell:
        return _Read(None, ref, "metric_not_computed")
    return _Read(cell["number"], ref + ".number")


def _resolve_overall(doc: dict[str, Any], metric: str, op: str | None) -> _Read:
    if metric in CALIBRATION_KEYS:
        cal = doc.get("calibration")
        if cal is None:
            reason = doc.get("calibration_suppressed_reason")
            if reason is None:
                return _Read(None, None, "no_calibration_block")
            return _Read(None, None, "calibration_suppressed", dict(reason))
        key = CALIBRATION_KEYS[metric]
        return _cell_number(cal.get(key), f"calibration.{key}")
    if metric in GAP_METRICS or metric == "auroc_gap":
        return _Read(None, None, "gap_requires_fairness_attribute")
    overall = doc.get("overall")
    if overall is None:
        return _Read(None, None, "overall_not_computed")
    if metric in ("auroc", "prevalence"):
        tf = overall.get("threshold_free") or {}
        num = tf.get(metric)
        if num is None:
            return _Read(None, None, "metric_not_computed")
        return _Read(num, f"overall.threshold_free.{metric}")
    block = overall.get(op) if op is not None else None
    if not block or metric not in block:
        return _Read(None, None, "metric_not_computed")
    return _Read(block[metric], f"overall.{op}.{metric}")


def _subgroup_rows(doc: dict[str, Any], attribute: str, level: Any) -> list[tuple[int, dict]]:
    rows = doc.get("subgroups") or []
    out = []
    for i, r in enumerate(rows):
        if r.get("attribute") != attribute:
            continue
        if level == "*":
            if r.get("is_unknown_row"):
                continue
            out.append((i, r))
        elif str(r.get("level")) == str(level):
            out.append((i, r))
    return out


def _resolve_subgroup(i: int, row: dict[str, Any], metric: str, op: str | None) -> _Read:
    metrics = row.get("metrics") or {}
    if metric in SUBGROUP_OP_METRICS:
        block = metrics.get(op) if op is not None else None
        if not block or metric not in block:
            return _Read(None, None, "metric_not_computed_for_scope")
        return _cell_number(block[metric], f"subgroups[{i}].metrics.{op}.{metric}")
    if metric in ("auroc", "brier"):
        return _cell_number(metrics.get(metric), f"subgroups[{i}].metrics.{metric}")
    return _Read(None, None, "metric_not_computed_for_scope")


def _resolve_gap(
    doc: dict[str, Any], attribute: str, level: str, metric: str, op: str | None
) -> _Read:
    fairness = doc.get("fairness")
    if fairness is None:
        return _Read(None, None, "no_fairness_block")
    if fairness.get("attribute") != attribute:
        return _Read(None, None, "gap_requires_fairness_attribute")
    if fairness.get("reference_level") is not None and str(level) == str(
        fairness["reference_level"]
    ):
        return _Read(None, None, "level_is_reference")
    for j, g in enumerate(fairness.get("gaps") or []):
        if str(g.get("level")) != str(level):
            continue
        if metric == "auroc_gap":
            return _cell_number(g.get("auroc_gap"), f"fairness.gaps[{j}].auroc_gap")
        per_op = (g.get("operating_points") or {}).get(op) if op is not None else None
        if not per_op or metric not in per_op:
            return _Read(None, None, "metric_not_computed")
        return _cell_number(per_op[metric], f"fairness.gaps[{j}].operating_points.{op}.{metric}")
    return _Read(None, None, "level_absent")


def _row(
    criterion_id: str,
    *,
    scope: Any,
    metric: str,
    op: str | None,
    statistic: str,
    comparator: str,
    value: float,
    read: _Read,
    level: float,
    declaration_index: int | None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "criterion_id": criterion_id,
        # the position of the criteria.yaml entry this row was evaluated from (repair 1,
        # lens FA-N1: two entries sharing an id printed both authors on both rows); null
        # on the fairness-bound rows, which come from the fairness block
        "declaration_index": declaration_index,
        "metric": metric,
        "operating_point": op,
        "scope": scope,
        "statistic": statistic,
        "comparator": comparator,
        "value": float(value),
        "metric_ref": read.metric_ref,
        "compared_value": None,
        "n": None,
        "method": None,
        "attainable_at_n": None,
        "max_lower_bound_at_n": None,
        "status": "not_assessable",
        "reason_code": read.reason,
        "detail": dict(read.detail) if read.detail else {},
    }
    number = read.number
    if number is None:
        return out
    method = number.get("method")
    out["method"] = method
    n = number.get("n")
    out["n"] = n
    if statistic == "ci_lower_bound" and metric in PROPORTION_METRICS:
        if method == ATTAINABILITY_METHOD and isinstance(n, int) and n > 0:
            out["max_lower_bound_at_n"] = max_lower_bound_at_n(n, level)
            out["attainable_at_n"] = attainable(value, n, comparator, level)
        elif method != ATTAINABILITY_METHOD:
            # whatever n: at 02d00c5 this sat under `n > 0`, so a zero_denominator Number
            # (n 0) carried no annotation (lens 2 of 21 September, FA-N1 / RG-N1)
            out["detail"]["attainability_not_computed"] = "method_not_wilson"
    if number.get("suppressed"):
        out["reason_code"] = "suppressed"
        return out
    reason = number.get("not_estimable_reason")
    if reason is not None or method == "none":
        # routed before any statistic is read: est is not compared on a Number that
        # carries no interval, whatever the statistic named
        out["reason_code"] = "no_interval"
        if reason is not None:
            out["detail"]["not_estimable_reason"] = reason
        return out
    compared = _statistic_of(number, statistic)
    if compared is None:
        out["reason_code"] = "no_interval"
        return out
    out["compared_value"] = float(compared)
    out["status"] = "met" if _compare(float(compared), comparator, float(value)) else "not_met"
    out["reason_code"] = "statistic_compared"
    return out


#: The ``comparison.differences`` key each threshold-free metric id is read from (build
#: day 10): the calibration slope's key is ``slope``, as in the calibration block.
COMPARISON_KEYS: dict[str, str] = {"auroc": "auroc", "brier": "brier", "calibration_slope": "slope"}


def _comparison_cell(block: Any, path: str, key: str) -> _Read:
    if not isinstance(block, dict) or key not in block:
        return _Read(None, None, "comparison_not_computed_for_scope")
    return _cell_number(block[key], f"{path}.{key}")


def _resolve_comparison(doc: dict[str, Any], metric: str, op: str | None, scope: Any) -> _Read:
    """A ``paired_difference_vs_prior`` criterion reads the paired difference of its
    metric from ``comparison.differences`` (overall scope) or from the matching
    ``comparison.subgroups[i].differences`` entry (a subgroup scope; the list is parallel
    to ``subgroups``), and compares the customer's statistic of that Number with the
    customer's margin. On an unpaired comparison no paired difference exists and every
    such criterion is ``not_assessable`` / ``not_like_for_like`` (D1 section 2)."""
    comparison = doc.get("comparison")
    if not isinstance(comparison, dict):
        return _Read(None, None, "requires_compare")
    if not comparison.get("paired"):
        return _Read(None, None, "not_like_for_like")
    if scope == "overall":
        block = comparison.get("differences") or {}
        path = "comparison.differences"
    else:
        rows = doc.get("subgroups") or []
        entries = comparison.get("subgroups") or []
        block, path = None, ""
        for i, r in enumerate(rows):
            if (
                isinstance(r, dict)
                and str(r.get("attribute")) == str(scope.get("attribute"))
                and str(r.get("level")) == str(scope.get("level"))
                and i < len(entries)
                and isinstance(entries[i], dict)
            ):
                block = entries[i].get("differences")
                path = f"comparison.subgroups[{i}].differences"
                break
        if block is None:
            return _Read(None, None, "comparison_not_computed_for_scope")
    if metric in COMPARISON_KEYS:
        return _comparison_cell(block, path, COMPARISON_KEYS[metric])
    if metric in SUBGROUP_OP_METRICS and op is not None:
        per_op = block.get(op) if isinstance(block, dict) else None
        return _comparison_cell(per_op, f"{path}.{op}", metric)
    return _Read(None, None, "metric_not_computed")


def _reads_for(c: dict[str, Any], doc: dict[str, Any]) -> list[tuple[_Read, Any]]:
    """The (read, scope) pairs one criterion resolves to: one per level in scope."""
    metric = c["metric"]
    op = None if c.get("operating_point") is None else str(c["operating_point"])
    scope = c.get("scope", "overall")
    if c.get("type") == "paired_difference_vs_prior":
        # build day 10: evaluated by compare (the document carries a comparison block);
        # outside compare the row stays not_assessable / requires_compare
        if not isinstance(doc.get("comparison"), dict):
            return [(_Read(None, None, "requires_compare"), scope)]
        if scope == "overall" or scope.get("level") != "*":
            return [(_resolve_comparison(doc, metric, op, scope), scope)]
        attribute = str(scope["attribute"])
        matched = _subgroup_rows(doc, attribute, "*")
        if not matched:
            return [(_Read(None, None, "level_absent"), scope)]
        return [
            (
                _resolve_comparison(
                    doc, metric, op, {"attribute": attribute, "level": str(r["level"])}
                ),
                {"attribute": attribute, "level": str(r["level"])},
            )
            for _, r in matched
        ]
    if metric in NOT_COMPUTED_METRICS:
        return [(_Read(None, None, "metric_not_computed"), scope)]
    if scope == "overall":
        return [(_resolve_overall(doc, metric, op), scope)]
    attribute, lvl = str(scope["attribute"]), scope["level"]
    if metric in GAP_METRICS or metric == "auroc_gap":
        if lvl != "*":
            return [(_resolve_gap(doc, attribute, str(lvl), metric, op), scope)]
        fairness = doc.get("fairness")
        if fairness is None or fairness.get("attribute") != attribute:
            return [(_Read(None, None, "gap_requires_fairness_attribute"), scope)]
        out = []
        for g in fairness.get("gaps") or []:
            if g.get("is_unknown_row"):
                continue
            lv = str(g["level"])
            read = _resolve_gap(doc, attribute, lv, metric, op)
            out.append((read, {"attribute": attribute, "level": lv}))
        return out or [(_Read(None, None, "level_absent"), scope)]
    matched = _subgroup_rows(doc, attribute, lvl)
    if not matched:
        return [(_Read(None, None, "level_absent"), scope)]
    return [
        (_resolve_subgroup(i, r, metric, op), {"attribute": attribute, "level": str(r["level"])})
        for i, r in matched
    ]


def evaluate(decl: Declarations, doc: dict[str, Any], *, level: float = 0.95) -> list[dict]:
    """Every ``criteria`` entry and the fairness bound against ``doc``; JSON-ready rows."""
    rows: list[dict[str, Any]] = []
    for k, c in enumerate(decl.criteria):
        op = None if c.get("operating_point") is None else str(c["operating_point"])
        for read, scope_out in _reads_for(c, doc):
            rows.append(
                _row(
                    str(c["id"]),
                    scope=scope_out,
                    metric=c["metric"],
                    op=op,
                    statistic=c["statistic"],
                    comparator=c["comparator"],
                    value=c["value"],
                    read=read,
                    level=level,
                    declaration_index=k,
                )
            )
    rows.extend(_fairness_rows(decl, doc, level))
    return rows


def _fairness_rows(decl: Declarations, doc: dict[str, Any], level: float) -> list[dict]:
    f = decl.fairness
    if f is None or f.get("bound") is None:
        return []
    metric = f["criterion_of_interest"]
    attribute = str(f["attribute"])
    statistic, comparator, bound = f["statistic"], f["comparator"], float(f["bound"])
    cid = f"fairness:{metric}"
    fairness = doc.get("fairness")
    out: list[dict[str, Any]] = []
    ops = [op.id for op in decl.operating_points] if metric in GAP_METRICS else [None]
    levels = (
        [str(g["level"]) for g in (fairness.get("gaps") or []) if not g.get("is_unknown_row")]
        if fairness is not None
        else []
    )
    for op in ops:
        for lv in levels:
            if metric == "calibration_by_group":
                read = _Read(None, None, "not_estimable_this_run")
            else:
                read = _resolve_gap(doc, attribute, lv, metric, op)
            out.append(
                _row(
                    cid,
                    scope={"attribute": attribute, "level": lv},
                    metric=metric,
                    op=op,
                    statistic=statistic,
                    comparator=comparator,
                    value=bound,
                    read=read,
                    level=level,
                    declaration_index=None,
                )
            )
    if not levels:
        out.append(
            _row(
                cid,
                scope={"attribute": attribute, "level": "*"},
                metric=metric,
                op=None,
                statistic=statistic,
                comparator=comparator,
                value=bound,
                read=_Read(None, None, "no_fairness_block" if fairness is None else "level_absent"),
                level=level,
                declaration_index=None,
            )
        )
    return out
