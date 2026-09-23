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
(``CALIB_HIERARCHY``, or ``CALIB_NA`` when it is null), each fairness gap at each
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
RELATIONS: tuple[str, ...] = ("estimate", "above", "below", "within", "not_assessable")
COMPARATOR_IDS: tuple[str, ...] = ("diff_vs_reference", "diff_vs_complement", ">=", ">", "<=", "<")


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


def _calibration_claims(doc: dict[str, Any], seq: int) -> tuple[list[dict[str, Any]], int]:
    cal = doc.get("calibration")
    seq += 1
    if not isinstance(cal, dict):
        return [_claim(seq, "CALIB_NA", relation="not_assessable", value_refs=[])], seq
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


def _criteria_claims(doc: dict[str, Any], seq: int) -> tuple[list[dict[str, Any]], int]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(doc.get("criteria_results") or []):
        ref = _dotted_to_pointer(row.get("metric_ref"))
        scope = row.get("scope")
        subgroup = (
            {"attribute": str(scope["attribute"]), "level": str(scope["level"])}
            if isinstance(scope, dict)
            else None
        )
        seq += 1
        out.append(
            _claim(
                seq,
                "CRITERION_STATUS",
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


def build_claims(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Every claim the engine makes about ``doc``, in the documented order."""
    claims: list[dict[str, Any]] = []
    seq = 0
    for builder in (
        _overall_claims,
        _subgroup_claims,
        _calibration_claims,
        _fairness_claims,
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
