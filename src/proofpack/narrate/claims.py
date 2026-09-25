"""The claims list (D1 section 4.4) built from a run document (build day 8, E8).

A claim binds one sentence skeleton (:mod:`proofpack.narrate.templates`) to the Numbers it
reports, by RFC 6901 JSON pointers into ``run.json`` (``/subgroups/4/metrics/op1/
sensitivity/number``). It carries **no number and no prose**: every ``{slot}`` in the
skeleton is filled by the renderer from the Number the pointer resolves to; ``free_text``
is ``null`` at launch (the checker forbids digits, ``%``, the verdict words, the section
sign, ``CFR`` and ``guidance`` in it whenever it is not).

Shape of one claim (every key present; ``schema/claims_schema.json`` closes the object)::

    {"claim_id": "CL-0031", "template_id": "SUBGROUP_ESTIMATE_WITH_DIFF",
     "metric_id": "sensitivity", "operating_point": "op1",
     "subgroup": {"attribute": "sex", "level": "F"},
     "reference": {"attribute": "sex", "level": "M"},
     "comparator_id": "diff_vs_reference",
     "criterion_index": null, "criterion_id": null, "status": null,
     "relation": "within",
     "value_refs": ["/subgroups/4/metrics/op1/sensitivity/number",
                    "/subgroups/4/diff_vs_reference/op1/sensitivity/number"],
     "guidance_ref": "FDA_AIDSF_SUBGROUP_PERF", "free_text": null}

``relation`` is the engine's own reading of the bound Numbers: ``estimate`` for a
quantity with an interval; ``above`` / ``below`` / ``within`` for a difference whose
interval lies above zero, below zero, or spans it; ``not_assessable`` when the Number
bound carries a typed reason or is suppressed. The checker recomputes it from the same
Numbers and rejects a claim whose stated relation differs (``relation_mismatch``).

**How a claim addresses a criteria row: by position**, ``criterion_index`` into
``criteria_results`` (E7 carried item 24: two criteria may share an ``id`` and ``level:
"*"`` repeats one; the row, not the id, is the unit). ``criterion_id`` is carried beside
it as an echo the checker compares with the row's (``criterion_id_mismatch``); a claim
that names an id and no index is rejected (``criterion_index_missing``). ``status`` is
copied from the row and the checker compares it again (``status_mismatch``) and
recomputes ``met`` / ``not_met`` from the bound Number with the row's statistic,
comparator and value (``status_recomputation_mismatch``). ``comparator_id`` on a
criterion claim is the row's comparator (``>=``, ``>``, ``<=``, ``<``); on a difference
claim it is the difference block the second pointer reads (``diff_vs_reference`` or
``diff_vs_complement``).

What is claimed, in this order, one claim per: overall metric at each operating point
(``OVERALL_ESTIMATE``), the overall AUROC (``AUROC_ESTIMATE``), each subgroup row's five
proportions at each operating point (``SUBGROUP_ESTIMATE_WITH_DIFF`` with the
difference-vs-reference cell when the row has one, ``SUBGROUP_ESTIMATE`` otherwise - the
reference row and levels without a reference), the calibration block
(``CALIB_HIERARCHY``; ``CALIB_NA`` when it is null with the reason
``score_not_probability``; nothing when it is null with another reason - repair 4), each
fairness gap at each
operating point (``FAIRNESS_GAP``), and each criteria row (``CRITERION_STATUS``).
``claim_id`` is ``CL-`` and a four-digit sequence in that order, so two runs of the same
document give the same ids.
"""

from __future__ import annotations

from typing import Any

from proofpack.narrate.templates import LIBRARY

#: The operating-point metrics claimed, in the order they are claimed (those present in
#: the block; ``ppa`` / ``npa`` stand in for sensitivity / specificity under a comparator).
OVERALL_METRIC_ORDER: tuple[str, ...] = (
    "sensitivity",
    "ppa",
    "specificity",
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
    "prevalence",
)
SUBGROUP_METRIC_ORDER: tuple[str, ...] = (
    "sensitivity",
    "ppa",
    "specificity",
    "npa",
    "ppv",
    "npv",
    "accuracy",
)
FAIRNESS_GAP_ORDER: tuple[str, ...] = ("tpr_gap", "fpr_gap", "ppv_gap", "auroc_gap")
CALIBRATION_REFS: tuple[str, ...] = ("oe", "slope", "intercept", "brier", "brier_ref", "ipa")
#: The one ``calibration_suppressed_reason.reason`` the ``CALIB_NA`` sentence states.
CALIB_NA_REASON = "score_not_probability"
RELATIONS: tuple[str, ...] = ("estimate", "above", "below", "within", "not_assessable")
#: ``diff_vs_prior`` (build day 10, E10): the block a ``PAIRED_DIFF`` claim reads, the
#: version comparison's difference cells under ``comparison.differences``.
COMPARATOR_IDS: tuple[str, ...] = (
    "diff_vs_reference",
    "diff_vs_complement",
    "diff_vs_prior",
    ">=",
    ">",
    "<=",
    "<",
)
#: The order the version-comparison claims report the paired differences in (E10): the
#: three conditioned proportions per operating point, then the threshold-free keys.
COMPARISON_OP_METRIC_ORDER: tuple[str, ...] = (
    "sensitivity",
    "ppa",
    "specificity",
    "npa",
    "accuracy",
)
COMPARISON_FREE_KEYS: tuple[tuple[str, str], ...] = (
    ("auroc", "auroc"),
    ("brier", "brier"),
    ("slope", "calibration_slope"),
)


def pointer(*parts: Any) -> str:
    """An RFC 6901 pointer from path parts (``~`` and ``/`` escaped)."""
    out = []
    for p in parts:
        s = str(p).replace("~", "~0").replace("/", "~1")
        out.append(s)
    return "/" + "/".join(out)


def relation_of(number: dict[str, Any] | None, *, difference: bool = False) -> str:
    """The engine's reading of one Number: see the module docstring."""
    if not isinstance(number, dict):
        return "not_assessable"
    if number.get("suppressed") or number.get("not_estimable_reason") is not None:
        return "not_assessable"
    lo, hi = number.get("ci_lo"), number.get("ci_hi")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (lo, hi)):
        # no interval, or one that is not a number (a ci_lo of "-0.1": repair 1, lens RG-N1)
        return "not_assessable"
    if not difference:
        return "estimate"
    if lo > 0:
        return "above"
    if hi < 0:
        return "below"
    return "within"


def _claim(
    seq: int,
    template_id: str,
    *,
    metric_id: str | None = None,
    operating_point: str | None = None,
    subgroup: dict[str, str] | None = None,
    reference: dict[str, str] | None = None,
    comparator_id: str | None = None,
    criterion_index: int | None = None,
    criterion_id: str | None = None,
    status: str | None = None,
    relation: str,
    value_refs: list[str],
) -> dict[str, Any]:
    return {
        "claim_id": f"CL-{seq:04d}",
        "template_id": template_id,
        "metric_id": metric_id,
        "operating_point": operating_point,
        "subgroup": subgroup,
        "reference": reference,
        "comparator_id": comparator_id,
        "criterion_index": criterion_index,
        "criterion_id": criterion_id,
        "status": status,
        "relation": relation,
        "value_refs": list(value_refs),
        "guidance_ref": LIBRARY[template_id].guidance_ref,
        "free_text": None,
    }


def _overall_claims(doc: dict[str, Any], seq: int) -> tuple[list[dict[str, Any]], int]:
    out: list[dict[str, Any]] = []
    overall = doc.get("overall")
    if not isinstance(overall, dict):
        return out, seq
    ops = [k for k in overall if k != "threshold_free"]
    for op in ops:
        block = overall[op] or {}
        for metric in OVERALL_METRIC_ORDER:
            if metric not in block:
                continue
            seq += 1
            out.append(
                _claim(
                    seq,
                    "OVERALL_ESTIMATE",
                    metric_id=metric,
                    operating_point=op,
                    relation=relation_of(block[metric]),
                    value_refs=[pointer("overall", op, metric)],
                )
            )
    tf = overall.get("threshold_free") or {}
    if "auroc" in tf:
        seq += 1
        out.append(
            _claim(
                seq,
                "AUROC_ESTIMATE",
                metric_id="auroc",
                relation=relation_of(tf["auroc"]),
                value_refs=[pointer("overall", "threshold_free", "auroc")],
            )
        )
    return out, seq


def _reference_levels(doc: dict[str, Any]) -> dict[str, str | None]:
    return {
        str(a.get("attribute")): a.get("reference_level")
        for a in doc.get("subgroup_attributes") or []
        if isinstance(a, dict)
    }


def _subgroup_claims(doc: dict[str, Any], seq: int) -> tuple[list[dict[str, Any]], int]:
    out: list[dict[str, Any]] = []
    refs = _reference_levels(doc)
    for i, row in enumerate(doc.get("subgroups") or []):
        attribute, level = str(row["attribute"]), str(row["level"])
        subgroup = {"attribute": attribute, "level": level}
        ref_level = refs.get(attribute)
        diff = row.get("diff_vs_reference")
        metrics = row.get("metrics") or {}
        for op, block in metrics.items():
            if op in ("auroc", "brier") or not isinstance(block, dict):
                continue
            for metric in SUBGROUP_METRIC_ORDER:
                if metric not in block:
                    continue
                est_ref = pointer("subgroups", i, "metrics", op, metric, "number")
                d_cell = (diff or {}).get(op, {}).get(metric) if isinstance(diff, dict) else None
                seq += 1
                if d_cell is not None and ref_level is not None and not row.get("is_reference"):
                    out.append(
                        _claim(
                            seq,
                            "SUBGROUP_ESTIMATE_WITH_DIFF",
                            metric_id=metric,
                            operating_point=op,
                            subgroup=subgroup,
                            reference={"attribute": attribute, "level": str(ref_level)},
                            comparator_id="diff_vs_reference",
                            relation=relation_of(d_cell.get("number"), difference=True),
                            value_refs=[
                                est_ref,
                                pointer("subgroups", i, "diff_vs_reference", op, metric, "number"),
                            ],
                        )
                    )
                else:
                    out.append(
                        _claim(
                            seq,
                            "SUBGROUP_ESTIMATE",
                            metric_id=metric,
                            operating_point=op,
                            subgroup=subgroup,
                            relation=relation_of(block[metric].get("number")),
                            value_refs=[est_ref],
                        )
                    )
    return out, seq


def calibration_suppression(doc: dict[str, Any]) -> Any:
    """``calibration_suppressed_reason.reason`` of ``doc``, or ``None``."""
    reason = doc.get("calibration_suppressed_reason")
    return reason.get("reason") if isinstance(reason, dict) else None


def _calibration_claims(doc: dict[str, Any], seq: int) -> tuple[list[dict[str, Any]], int]:
    cal = doc.get("calibration")
    if not isinstance(cal, dict):
        # repair 4, lens-4 FA-B3: CALIB_NA's sentence ("the score was declared as
        # {score_type}, not a probability") states the reason score_not_probability; on
        # no_score_column and score_not_positive_class_probability no calibration claim
        # is made (a template for each is open question 2 of the repair-3 note)
        if calibration_suppression(doc) != CALIB_NA_REASON:
            return [], seq
        seq += 1
        return [_claim(seq, "CALIB_NA", relation="not_assessable", value_refs=[])], seq
    seq += 1
    refs = [pointer("calibration", key, "number") for key in CALIBRATION_REFS if key in cal]
    primary = (cal.get("oe") or {}).get("number")
    return [
        _claim(
            seq,
            "CALIB_HIERARCHY",
            metric_id="oe",
            relation=relation_of(primary),
            value_refs=refs,
        )
    ], seq


def _fairness_claims(doc: dict[str, Any], seq: int) -> tuple[list[dict[str, Any]], int]:
    out: list[dict[str, Any]] = []
    fairness = doc.get("fairness")
    if not isinstance(fairness, dict):
        return out, seq
    attribute = str(fairness.get("attribute"))
    ref_level = fairness.get("reference_level")
    for j, gap in enumerate(fairness.get("gaps") or []):
        level = str(gap.get("level"))
        for op, per_op in (gap.get("operating_points") or {}).items():
            refs = [
                pointer("fairness", "gaps", j, "operating_points", op, key, "number")
                for key in FAIRNESS_GAP_ORDER
                if key != "auroc_gap" and key in per_op
            ]
            refs.append(pointer("fairness", "gaps", j, "auroc_gap", "number"))
            seq += 1
            out.append(
                _claim(
                    seq,
                    "FAIRNESS_GAP",
                    metric_id="tpr_gap",
                    operating_point=op,
                    subgroup={"attribute": attribute, "level": level},
                    reference=(
                        None
                        if ref_level is None
                        else {"attribute": attribute, "level": str(ref_level)}
                    ),
                    comparator_id="diff_vs_reference",
                    relation=relation_of(
                        (per_op.get("tpr_gap") or {}).get("number"), difference=True
                    ),
                    value_refs=refs,
                )
            )
    return out, seq


def _dotted_to_pointer(metric_ref: str | None) -> str | None:
    """``subgroups[3].metrics.op1.sensitivity.number`` -> ``/subgroups/3/metrics/op1/...``"""
    if not metric_ref:
        return None
    parts: list[str] = []
    for token in metric_ref.split("."):
        while "[" in token:
            head, rest = token.split("[", 1)
            idx, token = rest.split("]", 1)
            if head:
                parts.append(head)
            parts.append(idx)
        if token:
            parts.append(token)
    return pointer(*parts)


_AMBIGUOUS = object()


def metric_ref_pointers(doc: dict[str, Any]) -> dict[str, str]:
    """Each dotted path :mod:`proofpack.criteria` writes as ``metric_ref`` for a Number of
    ``doc``, mapped to the RFC 6901 pointer of that Number (repair 4, lens-4 FA-B1).

    The map is built from the document's own keys and the forms ``criteria`` writes
    (``overall.<op>.<metric>``, ``overall.threshold_free.<metric>``,
    ``calibration.<key>.number``, ``subgroups[i].metrics.<op>.<metric>.number``,
    ``subgroups[i].metrics.<auroc|brier>.number``,
    ``fairness.gaps[j].operating_points.<op>.<gap>.number``,
    ``fairness.gaps[j].auroc_gap.number``); the dotted string is looked up, never split,
    so an operating-point id holding ``.``, ``[`` or ``]`` is read as the whole id. A path
    two Numbers would share is left out."""
    table: dict[str, Any] = {}

    def add(dotted: str, *parts: Any) -> None:
        ptr = pointer(*parts)
        table[dotted] = ptr if table.get(dotted, ptr) == ptr else _AMBIGUOUS

    overall = doc.get("overall")
    if isinstance(overall, dict):
        for op, block in overall.items():
            if isinstance(block, dict):
                for metric in block:
                    add(f"overall.{op}.{metric}", "overall", op, metric)
    cal = doc.get("calibration")
    if isinstance(cal, dict):
        for key in cal:
            add(f"calibration.{key}.number", "calibration", key, "number")
    subgroups = doc.get("subgroups")
    for i, row in enumerate(subgroups if isinstance(subgroups, list) else []):
        metrics = row.get("metrics") if isinstance(row, dict) else None
        for name, block in (metrics if isinstance(metrics, dict) else {}).items():
            if name in ("auroc", "brier"):
                add(
                    f"subgroups[{i}].metrics.{name}.number",
                    "subgroups",
                    i,
                    "metrics",
                    name,
                    "number",
                )
            elif isinstance(block, dict):
                for metric in block:
                    add(
                        f"subgroups[{i}].metrics.{name}.{metric}.number",
                        *("subgroups", i, "metrics", name, metric, "number"),
                    )
    fairness = doc.get("fairness")
    if isinstance(fairness, dict):
        gaps = fairness.get("gaps")
        for j, gap in enumerate(gaps if isinstance(gaps, list) else []):
            if not isinstance(gap, dict):
                continue
            add(
                f"fairness.gaps[{j}].auroc_gap.number", "fairness", "gaps", j, "auroc_gap", "number"
            )
            per_ops = gap.get("operating_points")
            for op, per_op in (per_ops if isinstance(per_ops, dict) else {}).items():
                for metric in per_op if isinstance(per_op, dict) else ():
                    add(
                        f"fairness.gaps[{j}].operating_points.{op}.{metric}.number",
                        *("fairness", "gaps", j, "operating_points", op, metric, "number"),
                    )
    # build day 10 (E10): the version comparison's difference cells, the Numbers a
    # paired_difference_vs_prior criterion reads (proofpack.criteria._resolve_comparison)
    comparison = doc.get("comparison")
    if isinstance(comparison, dict):
        _add_difference_paths(
            add,
            "comparison.differences",
            ("comparison", "differences"),
            comparison.get("differences"),
        )
        entries = comparison.get("subgroups")
        for i, entry in enumerate(entries if isinstance(entries, list) else []):
            if isinstance(entry, dict):
                _add_difference_paths(
                    add,
                    f"comparison.subgroups[{i}].differences",
                    ("comparison", "subgroups", i, "differences"),
                    entry.get("differences"),
                )
    return {k: v for k, v in table.items() if v is not _AMBIGUOUS}


def _add_difference_paths(add: Any, dotted: str, parts: tuple[Any, ...], block: Any) -> None:
    if not isinstance(block, dict):
        return
    for key, value in block.items():
        if key in ("auroc", "brier", "slope"):
            add(f"{dotted}.{key}.number", *parts, key, "number")
        elif isinstance(value, dict):
            for metric in value:
                add(f"{dotted}.{key}.{metric}.number", *parts, key, metric, "number")


def criteria_row_pointers(doc: dict[str, Any]) -> list[str | None]:
    """The pointer of each ``criteria_results`` row's ``metric_ref``, by position, through
    :func:`metric_ref_pointers` (``None`` where the row names no Number)."""
    table = metric_ref_pointers(doc)
    rows = doc.get("criteria_results")
    out: list[str | None] = []
    for row in rows if isinstance(rows, list) else []:
        ref = row.get("metric_ref") if isinstance(row, dict) else None
        out.append(table.get(ref) if isinstance(ref, str) else None)
    return out


def _criteria_claims(doc: dict[str, Any], seq: int) -> tuple[list[dict[str, Any]], int]:
    out: list[dict[str, Any]] = []
    row_refs = criteria_row_pointers(doc)
    # build day 10 (E10): on a compare document (T2) every not_met row also gets the
    # PCCP record sentence, CRITERION_NOT_MET_RECORD ("T2 only", D4 section 8)
    record = isinstance(doc.get("comparison"), dict)
    for i, row in enumerate(doc.get("criteria_results") or []):
        ref = row_refs[i]
        scope = row.get("scope")
        subgroup = (
            {"attribute": str(scope["attribute"]), "level": str(scope["level"])}
            if isinstance(scope, dict)
            else None
        )
        templates = ["CRITERION_STATUS"]
        if record and row.get("status") == "not_met":
            templates.append("CRITERION_NOT_MET_RECORD")
        for template_id in templates:
            seq += 1
            out.append(
                _claim(
                    seq,
                    template_id,
                    metric_id=row.get("metric"),
                    operating_point=row.get("operating_point"),
                    subgroup=subgroup,
                    comparator_id=row.get("comparator"),
                    criterion_index=i,
                    criterion_id=row.get("criterion_id"),
                    status=row.get("status"),
                    relation="estimate"
                    if row.get("status") in ("met", "not_met")
                    else "not_assessable",
                    value_refs=[] if ref is None else [ref],
                )
            )
    return out, seq


def _difference_claim(
    seq: int,
    *,
    metric_id: str,
    operating_point: str | None,
    subgroup: dict[str, str] | None,
    cell: Any,
    ref: str,
) -> dict[str, Any]:
    number = cell.get("number") if isinstance(cell, dict) else None
    return _claim(
        seq,
        "PAIRED_DIFF",
        metric_id=metric_id,
        operating_point=operating_point,
        subgroup=subgroup,
        comparator_id="diff_vs_prior",
        relation=relation_of(number, difference=True),
        value_refs=[ref, pointer("comparison", "n_pairs")],
    )


def _comparison_claims(doc: dict[str, Any], seq: int) -> tuple[list[dict[str, Any]], int]:
    """The version-comparison claims (build day 10, E10; D4 section 3's list): on an
    unpaired comparison the ``UNPAIRED_LABEL`` sentence alone stands for the differences
    (they are not like-for-like and the table carries them); on a paired one a
    ``PAIRED_DIFF`` per conditioned proportion per operating point, then AUROC, Brier and
    slope, a ``MCNEMAR_RESULT`` per operating point (the per-subgroup differences are Table
    T2-4's and carry no sentence); then the ledger statement (and the warning when the
    declared limit is reached), the impact-assessment note and the monitoring pointer."""
    out: list[dict[str, Any]] = []
    comparison = doc.get("comparison")
    if not isinstance(comparison, dict):
        return out, seq
    if not comparison.get("paired"):
        seq += 1
        out.append(_claim(seq, "UNPAIRED_LABEL", relation="not_assessable", value_refs=[]))
    else:
        differences = comparison.get("differences") or {}
        ops = [k for k in differences if k not in ("auroc", "brier", "slope")]
        for op in ops:
            block = differences.get(op) or {}
            for metric in COMPARISON_OP_METRIC_ORDER:
                if metric not in block:
                    continue
                seq += 1
                out.append(
                    _difference_claim(
                        seq,
                        metric_id=metric,
                        operating_point=op,
                        subgroup=None,
                        cell=block[metric],
                        ref=pointer("comparison", "differences", op, metric, "number"),
                    )
                )
        for key, metric in COMPARISON_FREE_KEYS:
            if key not in differences:
                continue
            seq += 1
            out.append(
                _difference_claim(
                    seq,
                    metric_id=metric,
                    operating_point=None,
                    subgroup=None,
                    cell=differences[key],
                    ref=pointer("comparison", "differences", key, "number"),
                )
            )
        for op in ops:
            if op not in (comparison.get("mcnemar") or {}):
                continue
            seq += 1
            out.append(
                _claim(
                    seq,
                    "MCNEMAR_RESULT",
                    metric_id="accuracy",
                    operating_point=op,
                    relation="not_assessable",
                    value_refs=[
                        pointer("comparison", "mcnemar", op, key) for key in ("b", "c", "p")
                    ],
                )
            )
        # the per-subgroup paired differences are Table T2-4's; no sentence is generated
        # for them in E10 (the PAIRED_DIFF skeleton names no subgroup; recorded in the note)
    ledger = comparison.get("ledger") or {}
    seq += 1
    out.append(
        _claim(
            seq,
            "LEDGER_STATEMENT",
            relation="not_assessable",
            value_refs=[pointer("comparison", "ledger", "prior_acceptance_runs")],
        )
    )
    if ledger.get("limit_reached"):
        seq += 1
        out.append(_claim(seq, "LEDGER_WARNING", relation="not_assessable", value_refs=[]))
    seq += 1
    out.append(_claim(seq, "IMPACT_INPUTS_NOTE", relation="not_assessable", value_refs=[]))
    seq += 1
    out.append(_claim(seq, "MONITORING_POINTER", relation="not_assessable", value_refs=[]))
    return out, seq


def build_claims(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Every claim the engine makes about ``doc``, in the documented order."""
    claims: list[dict[str, Any]] = []
    seq = 0
    for builder in (
        _overall_claims,
        _subgroup_claims,
        _calibration_claims,
        _fairness_claims,
        _comparison_claims,
        _criteria_claims,
    ):
        got, seq = builder(doc, seq)
        claims.extend(got)
    return claims


def slot_key(claim: dict[str, Any]) -> tuple[Any, ...]:
    """The slot a claim occupies: what the deterministic substitute is looked up by."""
    sub = claim.get("subgroup")
    return (
        claim.get("template_id"),
        claim.get("metric_id"),
        claim.get("operating_point"),
        None if not isinstance(sub, dict) else (str(sub.get("attribute")), str(sub.get("level"))),
        claim.get("criterion_index"),
    )
