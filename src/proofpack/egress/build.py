"""The two egress documents, built from ``run.json``'s document and validated before
they are returned (D1 section 6).

:func:`build_payload` - the telemetry document, D1 section 6's literal payload::

    {"schema": "proofpack-telemetry/1", "licence_id": "lic_...", "run_id": "uuid",
     "engine_version": "0.1.0.dev1", "platform": "linux-x86_64-cp312",
     "manifest_sha256": "...", "duration_s": 41.2, "halt_code": null,
     "row_count_bucket": "10k-100k", "timestamp": "2026-10-...T...Z"}

*No column names, no counts below bucket level, no metric values* (D1 section 6; v2
section 2 "manifest hash only"). ``manifest_sha256`` is the SHA-256 of the canonical JSON
bytes of the document's ``manifest`` block (:func:`manifest_sha256`); ``row_count_bucket``
buckets ``flow.rows_read`` (:data:`ROW_COUNT_BUCKETS`); ``licence_id`` is the manifest's
when the licence verified (``ok``, ``grace``, ``expired``) and null otherwise, so an id
read out of a tampered or unknown-key file is never reported as a licence; ``halt_code``
is null on every document the engine sends today because a HALT writes nothing and the
single call site runs after ``run.json`` is written.

**The keys D2 section 5.1 and D3 section 4 name (``manifest_hash``, ``duration_ms``, an
exit code) are not added** (build day 8 decision, recorded in the A-P2 note): the DPA's
clause 2.1 and the trust page's field list already promise D1's ten keys "and no others",
and the site's vendored schema at the pinned engine commit carries exactly these ten; a
key added here would make those sentences false until the pin moves. The site's ``runs``
table therefore has the ten columns the payload has, named as the payload names them.

:func:`build_aggregates` - the ``proofpack-aggregates/1`` document (the deferred
narrative call's shape; no code path sends it at launch): the overall Numbers per
operating point and threshold-free, the overall two-by-two tables, the subgroup rows'
Numbers, the calibration Numbers and decile bins, and the fairness gaps - each cell
k-suppressed (:mod:`.suppress`), each level pseudonymised (:mod:`.pseudonymise`), the
whole projected onto the schema (:mod:`.whitelist`) and validated. The ROC curve
(``overall.threshold_free.roc``, every distinct score value - E7 lens RG-N8), the
per-threshold arrays, the level labels, the declarations, the original headers, the
dates, the ledger key, the mapping hash and the claims text have no key in the schema and
do not survive the projection; ``tests/test_egress.py`` asserts their absence on the bytes.

Both builders raise :class:`EgressError` when the document they built does not project
(a :class:`~proofpack.egress.whitelist.WhitelistError` is re-raised as one) or does not
validate. That is a typed error and the caller sends nothing; at 7b2ca2a-plus-the-first-
draft a licence id outside the pattern escaped as a WhitelistError and turned the run's
exit into 5 (measured on the smoke run, 22 September), which is why the two are one class
here and ``run_telemetry`` catches it.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

import jsonschema

from proofpack.egress import pseudonymise, suppress, whitelist
from proofpack.errors import ProofPackError
from proofpack.manifest import canonical_json, utc_now_iso
from proofpack.resources import load_json_schema

TELEMETRY_SCHEMA = "proofpack-telemetry/1"
AGGREGATES_SCHEMA = "proofpack-aggregates/1"

#: ``(name, lower bound inclusive, upper bound exclusive)`` on ``flow.rows_read``; the
#: names are the schema's ``row_count_bucket`` enum in order (D1 section 6's example is
#: ``10k-100k``). ``tests/test_egress.py`` holds the enum and this tuple equal.
ROW_COUNT_BUCKETS: tuple[tuple[str, int, int | None], ...] = (
    ("<1k", 0, 1_000),
    ("1k-10k", 1_000, 10_000),
    ("10k-100k", 10_000, 100_000),
    (">100k", 100_000, None),
)

#: The overall-block metric ids projected (D1 section 4.3 ids that are Numbers there;
#: ``ppv_at_prevalence`` and ``two_by_two`` are not Numbers and are handled apart).
OVERALL_METRICS = (
    "sensitivity",
    "specificity",
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
SUBGROUP_OP_METRICS = ("sensitivity", "specificity", "ppv", "npv", "accuracy")
SUBGROUP_METRICS = ("auroc", "brier")
CALIBRATION_METRICS = (
    ("slope", "calibration_slope"),
    ("intercept", "calibration_intercept"),
    ("oe", "oe"),
    ("brier", "brier"),
    ("ipa", "ipa"),
)
GAP_METRICS = ("tpr_gap", "fpr_gap", "ppv_gap", "npv_gap")
#: Licence statuses under which the manifest's ``licence_id`` was read from a file whose
#: signature verified (``proofpack.licence.verify``).
VERIFIED_LICENCE_STATUSES = frozenset({"ok", "grace", "expired"})


class EgressError(ProofPackError):
    """A built egress document failed schema validation. Nothing is sent."""

    exit_code = 5

    def __init__(self, which: str, message: str) -> None:
        self.which = which
        super().__init__(f"{which} document failed egress_schema.json: {message}")


def egress_schema() -> dict[str, Any]:
    return load_json_schema("egress_schema.json")


def _validate(which: str, document: Mapping[str, Any], definition: str) -> None:
    schema = egress_schema()
    sub = {"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]}
    validator = jsonschema.Draft202012Validator(sub)
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        where = "/".join(str(p) for p in first.path) or "<root>"
        raise EgressError(which, f"{len(errors)} error(s); first at {where}: {first.message}")


def row_count_bucket(rows: int) -> str:
    """The bucket name for a row count; a negative count is refused."""
    if not isinstance(rows, int) or isinstance(rows, bool) or rows < 0:
        raise EgressError(TELEMETRY_SCHEMA, f"row count {rows!r} cannot be bucketed")
    for name, lo, hi in ROW_COUNT_BUCKETS:
        if rows >= lo and (hi is None or rows < hi):
            return name
    raise EgressError(TELEMETRY_SCHEMA, f"row count {rows!r} outside every bucket")


def manifest_sha256(manifest: Mapping[str, Any]) -> str:
    """SHA-256 (hex) of ``canonical_json(manifest)`` - the bytes ``run.json`` holds for
    the block, so a customer can recompute it from their own file."""
    return hashlib.sha256(canonical_json(dict(manifest))).hexdigest()


def build_payload(
    document: Mapping[str, Any],
    *,
    licence_status: str | None = None,
    halt_code: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """The telemetry document for one written run (module docstring). ``licence_status``
    is the run's ``LicenceResult.status``; without it the manifest's ``licence_id`` is
    sent only when the manifest also records a ``tier`` (set only from a verified file).
    Validated against ``$defs/telemetry``; :class:`EgressError` on failure."""
    manifest = document.get("manifest") or {}
    flow = document.get("flow") or {}
    if licence_status is None:
        verified = manifest.get("tier") is not None
    else:
        verified = licence_status in VERIFIED_LICENCE_STATUSES
    candidate = {
        "schema": TELEMETRY_SCHEMA,
        "licence_id": manifest.get("licence_id") if verified else None,
        "run_id": manifest.get("run_id"),
        "engine_version": manifest.get("engine_version"),
        "platform": manifest.get("platform"),
        "manifest_sha256": manifest_sha256(manifest),
        "duration_s": manifest.get("duration_s"),
        "halt_code": halt_code,
        "row_count_bucket": row_count_bucket(flow.get("rows_read")),
        "timestamp": timestamp if timestamp is not None else utc_now_iso(),
    }
    schema = egress_schema()
    try:
        payload = whitelist.project(candidate, schema, schema["$defs"]["telemetry"])
    except whitelist.WhitelistError as exc:
        raise EgressError("telemetry", str(exc)) from exc
    _validate("telemetry", payload, "telemetry")
    return payload


# ------------------------------------------------------------------------- aggregates


def _cell(metric_id: str, op: str | None, attribute: str | None, level: str | None, number):
    return {
        "metric_id": metric_id,
        "operating_point": op,
        "attribute": attribute,
        "level": level,
        "number": number,
    }


def _two_by_two(op: str, attribute, level, t: Mapping[str, Any], thresholds) -> dict:
    tp, fn, fp, tn = (t.get(k) for k in ("tp", "fn", "fp", "tn"))
    counts = [tp, fn, fp, tn]
    if not all(isinstance(c, int) for c in counts):
        n = events = nonevents = None
    else:
        n, events, nonevents = sum(counts), tp + fn, fp + tn
    if suppress.is_suppressed(n, events, nonevents, thresholds):
        return {
            "operating_point": op,
            "attribute": attribute,
            "level": level,
            "tp": None,
            "fn": None,
            "fp": None,
            "tn": None,
            "suppressed": True,
        }
    return {
        "operating_point": op,
        "attribute": attribute,
        "level": level,
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "suppressed": False,
    }


def _number_of(block: Any) -> Mapping[str, Any] | None:
    """A day-4 cell carries the rendered Number under ``number``; a day-2 Number is the
    dict itself."""
    if not isinstance(block, Mapping):
        return None
    if "number" in block and isinstance(block["number"], Mapping | type(None)):
        return block["number"]
    return block if "est" in block else None


def build_aggregates(
    document: Mapping[str, Any], thresholds: suppress.Thresholds | None = None
) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    """``(payload, pseudonym_map)`` - the ``proofpack-aggregates/1`` document and the map
    that was applied to it (the map goes to ``pseudonyms.json``, never into the payload).
    Validated against ``$defs/aggregates``; :class:`EgressError` on failure."""
    t = thresholds if thresholds is not None else suppress.DEFAULT_THRESHOLDS
    pmap = pseudonymise.build_map(document)
    cells: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    bins: list[dict[str, Any]] = []

    # overall (i.i.d. only; None on a clustered plan)
    overall = document.get("overall") or {}
    for op, block in overall.items():
        if op == "threshold_free":
            for metric in ("auroc", "prevalence"):
                cells.append(
                    _cell(metric, None, None, None, suppress.project_number(block.get(metric), t))
                )
            continue
        for metric in OVERALL_METRICS:
            if metric in block:
                cells.append(
                    _cell(metric, op, None, None, suppress.project_number(block.get(metric), t))
                )
        if isinstance(block.get("two_by_two"), Mapping):
            tables.append(_two_by_two(op, None, None, block["two_by_two"], t))

    # subgroup rows: the row's n / events decide the row; each Number then decides itself
    for row in document.get("subgroups") or []:
        attribute, level = row.get("attribute"), row.get("level")
        if not isinstance(attribute, str) or not isinstance(level, str):
            continue
        n, events = row.get("n"), row.get("events")
        nonevents = n - events if isinstance(n, int) and isinstance(events, int) else None
        row_suppressed = suppress.is_suppressed(n, events, nonevents, t)
        label = pseudonymise.pseudonym(pmap, attribute, level)
        metrics = row.get("metrics") or {}
        for metric in SUBGROUP_METRICS:
            if metric in metrics:
                cells.append(
                    _cell(
                        metric,
                        None,
                        attribute,
                        label,
                        suppress.project_number(
                            _number_of(metrics[metric]), t, row_suppressed=row_suppressed
                        ),
                    )
                )
        for op, opblock in metrics.items():
            if op in SUBGROUP_METRICS or not isinstance(opblock, Mapping):
                continue
            for metric in SUBGROUP_OP_METRICS:
                if metric in opblock:
                    cells.append(
                        _cell(
                            metric,
                            op,
                            attribute,
                            label,
                            suppress.project_number(
                                _number_of(opblock[metric]), t, row_suppressed=row_suppressed
                            ),
                        )
                    )

    # calibration: the block's Numbers and the decile bins
    cal = document.get("calibration")
    if isinstance(cal, Mapping):
        for key, metric_id in CALIBRATION_METRICS:
            if key in cal:
                cells.append(
                    _cell(
                        metric_id,
                        None,
                        None,
                        None,
                        suppress.project_number(_number_of(cal[key]), t),
                    )
                )
        for b in cal.get("decile_curve") or []:
            n, events = b.get("n"), b.get("events")
            nonevents = n - events if isinstance(n, int) and isinstance(events, int) else None
            hidden = suppress.is_suppressed(n, events, nonevents, t)
            bins.append(
                {
                    "bin": b.get("bin"),
                    "n": None if hidden else n,
                    "events": None if hidden else events,
                    "mean_pred": None if hidden else b.get("mean_pred"),
                    "observed": suppress.project_number(
                        _number_of(b.get("observed")), t, row_suppressed=hidden
                    ),
                    "suppressed": hidden,
                }
            )

    # fairness gaps: the level's row decides, then each Number
    fairness = document.get("fairness") or {}
    f_attr = fairness.get("attribute")
    rows_by_level = {
        (r.get("attribute"), r.get("level")): r for r in document.get("subgroups") or []
    }
    for gap in fairness.get("gaps") or []:
        level = gap.get("level")
        if not isinstance(f_attr, str) or not isinstance(level, str):
            continue
        row = rows_by_level.get((f_attr, level), {})
        n, events = row.get("n", gap.get("n")), row.get("events")
        nonevents = n - events if isinstance(n, int) and isinstance(events, int) else None
        row_suppressed = suppress.is_suppressed(n, events, nonevents, t)
        label = pseudonymise.pseudonym(pmap, f_attr, level)
        if "auroc_gap" in gap:
            cells.append(
                _cell(
                    "auroc_gap",
                    None,
                    f_attr,
                    label,
                    suppress.project_number(
                        _number_of(gap["auroc_gap"]), t, row_suppressed=row_suppressed
                    ),
                )
            )
        for op, opblock in (gap.get("operating_points") or {}).items():
            for metric in GAP_METRICS:
                if isinstance(opblock, Mapping) and metric in opblock:
                    cells.append(
                        _cell(
                            metric,
                            op,
                            f_attr,
                            label,
                            suppress.project_number(
                                _number_of(opblock[metric]), t, row_suppressed=row_suppressed
                            ),
                        )
                    )

    candidate = {
        "schema": AGGREGATES_SCHEMA,
        "cells": cells,
        "two_by_two": tables,
        "calibration_bins": bins,
    }
    schema = egress_schema()
    try:
        payload = whitelist.project(candidate, schema, schema["$defs"]["aggregates"])
    except whitelist.WhitelistError as exc:
        raise EgressError("aggregates", str(exc)) from exc
    _validate("aggregates", payload, "aggregates")
    return payload, pmap
