"""T1, the FDA AI-DSF performance evidence attachment set, as HTML (D4 section 2; E9 item 3).

Fifteen sections and the cover, in D4 section 2's order, through the same ``base.html``
furniture as T8 and T7. What each section prints, and where it comes from (the section
to table map recorded in the E9 build note):

====  =====================================  ============================================
 §    Section (anchor)                       Tables and prose
====  =====================================  ============================================
 0    Cover, guidance versions, long         cover block, cover stamp (the manifest's own
      disclaimer (page 2)                    marks), CT-01, CT-02
 1    Scope and declarations (PP_SCOPE)      Table T1-1 (T8's declaration rows)
 2    Data management                        CT-03; T1-2 flow (5.10); T1-3 Table 1 (5.4)
 3    Test-set independence                  CT-04; T1-4 overlap, or the no-data box
 4    Site diversity (+ 2007 by site)        CT-05; T1-5 per-site (5.3)
 5    Representativeness                     CT-06; T1-3 (shared)
 6    Reference standard (+ PPA/NPA)         the declaration as Manufacturer text; CT-07
 7    Performance per operating point        CT-08; T1-6 two-by-two (5.1); T1-7 metrics
                                             (5.2); T1-8 threshold-free; F2, F3; the
                                             OVERALL_ESTIMATE / AUROC_ESTIMATE sentences
 8    Calibration                            CT-09; T1-9 (5.5) with the IPA tier (DEC-35)
                                             and the decile table; or ``calibration: null``
                                             beside its reason (DEC-36); F4; CALIB_*
 9    Subgroups (+ 2007 by site)             CT-10 (the declared sources); per attribute
                                             T1-10 (5.3), T1-11 differences (5.3b, never
                                             a consistency verdict), the exploratory
                                             footnote, F5; SUBGROUP_* sentences
 10   Fairness (descriptive)                 T1-13 gaps; FAIRNESS_GAP sentences
 11   Robustness                             the no-data box (no robustness block, v1.1)
 12   Acceptance criteria                    T1-17 = the criteria table exactly as T8
                                             prints it (one macro); CRITERION_STATUS
 13   Monitoring                             CT-11; the no-data box (T3 is v1.1)
 14   Public summary inputs                  the supplement-only note; T1-18
 15   Model card                             D4's heading note; the no-data box (v1.1)
====  =====================================  ============================================

**The placeholder rule.** A customer-text slot with no text prints
:data:`proofpack.scope.PLACEHOLDER` in the placeholder box (``pack_text.yaml`` is not
read in this build, so CT-01..CT-09 and CT-11 are outstanding on every run; CT-10 is
filled from ``criteria.yaml``'s subgroup sources); a section whose data the run document
does not carry prints the engine's one line in the same box - never an empty heading.
The cover stamp counts the outstanding slots (``INCOMPLETE - customer sections
outstanding: n``).

**Prose.** Every sentence is a claim of ``run.json`` (the checked list: accepted claims,
and for a rejected one the deterministic template claim of its slot) rendered by
:mod:`proofpack.render.sentences`; no other prose is generated. Sections whose D4
templates have no engine claim in v1 carry their tables and captions only.

**Numbers.** Every Number cell carries ``data-ref`` (the RFC 6901 pointer of the Number
it prints), ``data-kind`` and ``data-facet``, so ``tests/test_render_t1.py`` resolves the
pointer in ``run.json`` and compares the cell with :mod:`proofpack.render.format`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from markupsafe import Markup, escape

from proofpack.narrate import claims as claims_mod
from proofpack.narrate.checker import resolve_pointer
from proofpack.narrate.templates import LIBRARY, METRIC_NAMES
from proofpack.render import anchors, sentences
from proofpack.render import format as fmt
from proofpack.render import html as render_html
from proofpack.render.t7 import flow_rows
from proofpack.scope import PLACEHOLDER

T1_FILE = "T1.html"

#: The anchors each section's margin notes cite (D4 section 2, the section column).
T1_ANCHORS: dict[str, tuple[str, ...]] = {
    "s1": ("PP_SCOPE",),
    "s2": ("FDA_AIDSF_DATA_MGMT",),
    "s3": ("FDA_AIDSF_TEST_INDEPENDENCE",),
    "s4": ("FDA_AIDSF_SITE_DIVERSITY", "FDA_STAT2007_BY_SITE"),
    "s5": ("FDA_AIDSF_REPRESENTATIVENESS",),
    "s6": ("FDA_AIDSF_REF_STANDARD", "FDA_STAT2007_PPA_NPA"),
    "s7": (
        "FDA_AIDSF_PERF_VALIDATION",
        "FDA_STAT2007_CI",
        "FDA_STAT2007_INDETERMINATE",
        "FDA_AIDSF_LABELING_METRICS",
    ),
    "s8": ("FDA_AIDSF_CALIBRATION",),
    "s9": ("FDA_AIDSF_SUBGROUP_PERF", "FDA_STAT2007_BY_SITE"),
    "s10": ("FDA_AIDSF_SUBGROUP_PERF",),
    "s11": ("FDA_AIDSF_PERF_VALIDATION",),
    "s12": ("FDA_AIDSF_PERF_VALIDATION",),
    "s13": ("FDA_AIDSF_MONITORING",),
    "s14": ("FDA_AIDSF_PUBLIC_SUMMARY",),
    "s15": ("FDA_AIDSF_MODEL_CARD",),
}

#: T1's customer-text slots (D4 section 2's column), in order.
CUSTOMER_TEXT_SLOTS: tuple[tuple[str, str], ...] = (
    ("CT-01", "manufacturer name and address"),
    ("CT-02", "device name and intended use (one paragraph)"),
    ("CT-03", "data collection method, cleaning, annotation and storage"),
    ("CT-04", "test-set sequestration and governance statement"),
    ("CT-05", "site characteristics, US and non-US"),
    ("CT-06", "intended-use population description"),
    (
        "CT-07",
        "how the reference standard was established: uncertainty, grading, blinding, number "
        "and qualification of clinicians",
    ),
    ("CT-08", "statistical analysis plan reference and pre-specified primary endpoint"),
    ("CT-09", "calibration method used in development, if any"),
    ("CT-10", "pre-specification source of each subgroup attribute"),
    ("CT-11", "monitoring plan summary"),
)
#: D4 section 2 row 14, the supplement-only note, verbatim.
PUBLIC_SUMMARY_NOTE = (
    "the 510(k) Summary is the submitter's document under 21 CFR 807.92; this table supplies "
    "numbers, not the summary"
)
#: D4 section 2 row 15, the model-card heading note, verbatim.
MODEL_CARD_NOTE = (
    "model cards are not required per draft guidance (Jan 2025), not for implementation"
)
COVER_NOTE = (
    "Attachment set prepared for the manufacturer's own submission or record. Not a "
    "submission. No regulator has endorsed this tool."
)

_SE_SP = {
    "reference_standard": ("sensitivity", "specificity"),
    "comparator": ("ppa", "npa"),
}


# ------------------------------------------------------------------ cells


def cell(document: dict[str, Any], pointer: str, kind: str, facet: str = "cell") -> dict:
    """One Number cell: the text D4 section 1.2 prints for ``facet`` of the Number at
    ``pointer``, and the pointer, kind and facet the tests read back. ``facet`` is
    ``cell`` (the whole ``fmt.number``), ``est``, ``ci`` (``[lo, hi]``), ``kn`` (``k/n``)
    or ``method``."""
    found, num = resolve_pointer(document, pointer)
    num = num if found and isinstance(num, dict) else None
    if facet == "cell":
        text = fmt.number(num, kind)
    elif facet == "est":
        # the table's Estimate column: the unit sign lives in the header (D4 section 5.2)
        if num is not None and fmt.has_interval(num):
            text = fmt.bound(float(num["est"]), kind) + fmt.tiers(num)
        else:
            text = fmt.estimate(num, kind)
    elif facet == "ci":
        inner = fmt.interval(num, kind)
        text = inner if inner == "no interval" else f"[{inner}]"
    elif facet == "kn":
        text = (
            f"{fmt.count(num['k'])}/{fmt.count(num['n'])}"
            if num is not None and num.get("k") is not None and num.get("n") is not None
            else "—"
        )
    elif facet == "method":
        text = fmt.method(num)
    else:
        raise ValueError(f"unknown facet {facet!r}")
    return {"text": text, "ref": pointer, "kind": kind, "facet": facet, "present": num is not None}


def _p(*parts: Any) -> str:
    return claims_mod.pointer(*parts)


# ------------------------------------------------------------------ sentences


def sentence_html(claim: dict[str, Any], document: dict[str, Any]) -> Markup:
    """One claim as HTML: the manufacturer's words inside ``.customer-text``, the status
    word inside ``.status``, everything escaped."""
    out = Markup("")
    for part in sentences.claim_parts(claim, document):
        if part.kind == "customer":
            out += Markup('<span class="customer-text inline">') + escape(part.text)
            out += Markup("</span>")
        elif part.kind == "status":
            out += Markup('<span class="status">') + escape(part.text) + Markup("</span>")
        else:
            out += escape(part.text)
    return out


def claim_sentences(
    document: dict[str, Any], templates: set[str], **match: Any
) -> list[dict[str, Any]]:
    """The claims of ``templates`` (optionally matching an attribute), as sentences."""
    out = []
    for claim in document.get("claims") or []:
        if claim.get("template_id") not in templates:
            continue
        sub = claim.get("subgroup")
        if "attribute" in match:
            if not isinstance(sub, dict) or sub.get("attribute") != match["attribute"]:
                continue
        if "operating_point" in match and claim.get("operating_point") != match["operating_point"]:
            continue
        out.append({"id": claim.get("claim_id"), "html": sentence_html(claim, document)})
    return out


# ------------------------------------------------------------------ sections


def _slots(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every CT slot: its placeholder text, or the customer's text when the engine has it
    (CT-10 from the subgroups' declared sources)."""
    out: dict[str, dict[str, Any]] = {}
    subs = (document.get("declarations") or {}).get("subgroups") or []
    sources = [
        (fmt.text(s.get("attribute")), fmt.text(s.get("source")))
        for s in subs
        if isinstance(s, dict) and s.get("source")
    ]
    for slot_id, title in CUSTOMER_TEXT_SLOTS:
        text = None
        if slot_id == "CT-10" and sources and len(sources) == len(subs):
            text = "; ".join(f"{a}: {s}" for a, s in sources)
        out[slot_id] = {
            "id": slot_id,
            "title": title,
            "filled": text is not None,
            "text": text if text is not None else PLACEHOLDER.format(title=title),
        }
    return out


def _level_order(document: dict[str, Any], attribute: str) -> list[str]:
    for a in document.get("subgroup_attributes") or []:
        if isinstance(a, dict) and a.get("attribute") == attribute and a.get("level_order"):
            return [str(x) for x in a["level_order"]]
    return []


def table1_rows(document: dict[str, Any]) -> list[dict[str, str]]:
    """Table T1-3 (D4 section 5.4): attribute, level, test n (%); the attributes sorted by
    name, the levels in the engine's level order, an Unknown/missing row on every
    attribute (its count from ``subgroup_attributes``)."""
    t1 = (document.get("table1") or {}).get("test") or {}
    attrs = {
        a.get("attribute"): a
        for a in document.get("subgroup_attributes") or []
        if isinstance(a, dict)
    }
    rows: list[dict[str, str]] = []
    for attribute in sorted(t1):
        levels = t1[attribute] or {}
        order = _level_order(document, attribute) or sorted(levels)
        order += [lv for lv in sorted(levels) if lv not in order]
        first = True
        for level in order:
            if level not in levels:
                continue
            entry = levels[level] or {}
            rows.append(
                {
                    "attribute": attribute if first else "",
                    "level": level,
                    "n": fmt.count(entry.get("n")),
                    "pct": fmt.percent(entry["pct"]) if entry.get("pct") is not None else "—",
                }
            )
            first = False
        if not any(str(lv).lower().startswith("unknown") for lv in levels):
            meta = attrs.get(attribute) or {}
            rows.append(
                {
                    "attribute": "",
                    "level": "Unknown/missing",
                    "n": fmt.count(meta.get("n_unknown_missing", 0)),
                    "pct": "—",
                }
            )
    return rows


def _ops(document: dict[str, Any]) -> list[str]:
    return [k for k in (document.get("overall") or {}) if k != "threshold_free"]


def _declared_op(document: dict[str, Any], op: str) -> dict[str, Any]:
    for o in (document.get("declarations") or {}).get("operating_points") or []:
        if isinstance(o, dict) and o.get("id") == op:
            return o
    return {}


def _provenance(op_decl: dict[str, Any]) -> str:
    phrases = (LIBRARY["THRESH_PROVENANCE"].phrases or {})["provenance_phrase"]
    key = op_decl.get("provenance")
    if key in phrases:
        return phrases[key].replace("{source}", fmt.text(op_decl.get("source")))
    return f"provenance {fmt.text(key)} ({fmt.text(op_decl.get('source'))})"


def performance_blocks(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Section 7, per operating point: T1-6 (5.1), T1-7 (5.2), the caption facts."""
    decl = document.get("declarations") or {}
    ref_type = (decl.get("reference_standard") or {}).get("type") or "reference_standard"
    se, sp = _SE_SP.get(ref_type, _SE_SP["reference_standard"])
    word = "Comparator" if ref_type == "comparator" else "Reference"
    out = []
    for op in _ops(document):
        block = (document.get("overall") or {}).get(op) or {}
        tbt = block.get("two_by_two") or {}

        def n_of(key: str, _block=block) -> str:
            num = _block.get(key)
            return fmt.count(num.get("n")) if isinstance(num, dict) and num.get("n") else "—"

        two_by_two = {
            "row_pos": f"{word} positive",
            "row_neg": f"{word} negative",
            "tp": fmt.count(tbt.get("tp")),
            "fn": fmt.count(tbt.get("fn")),
            "fp": fmt.count(tbt.get("fp")),
            "tn": fmt.count(tbt.get("tn")),
            "n_pos": n_of(se),
            "n_neg": n_of(sp),
            "d_pos": n_of("ppv"),
            "d_neg": n_of("npv"),
            "total": n_of("accuracy"),
        }
        rows = []
        main_rows = [
            (METRIC_NAMES[se].capitalize() if se == "sensitivity" else "PPA", se),
            (METRIC_NAMES[sp].capitalize() if sp == "specificity" else "NPA", sp),
            ("PPV (study prevalence)", "ppv"),
            ("NPV (study prevalence)", "npv"),
            ("Accuracy", "accuracy"),
            ("LR+", "lr_pos"),
            ("LR−", "lr_neg"),
        ]
        supplementary = [
            ("F1", "f1"),
            ("MCC", "mcc"),
            ("DOR", "dor"),
            ("Youden J", "youden"),
            ("Balanced accuracy", "balanced_accuracy"),
        ]
        for label, key in main_rows + supplementary:
            if key not in block:
                continue
            kind = fmt.kind_for(key)
            ptr = _p("overall", op, key)
            rows.append(
                {
                    "label": label,
                    "supplementary": key in dict((k, 1) for _, k in supplementary),
                    "kn": cell(document, ptr, kind, "kn"),
                    "est": cell(document, ptr, kind, "est"),
                    "ci": cell(document, ptr, kind, "ci"),
                    "method": cell(document, ptr, kind, "method"),
                }
            )
        prev_rows = []
        for j, item in enumerate(block.get("ppv_at_prevalence") or []):
            for key in ("ppv", "npv"):
                ptr = _p("overall", op, "ppv_at_prevalence", j, key)
                prev_rows.append(
                    {
                        "label": f"{key.upper()} at π = {fmt.declared(item.get('value'))} "
                        f"({fmt.text(item.get('label'))})",
                        "est": cell(document, ptr, "proportion", "est"),
                        "ci": cell(document, ptr, "proportion", "ci"),
                        "method": cell(document, ptr, "proportion", "method"),
                    }
                )
        od = _declared_op(document, op)
        out.append(
            {
                "op": op,
                "threshold": fmt.declared(od.get("threshold")),
                "rule": fmt.text(od.get("rule")),
                "provenance": _provenance(od),
                "derived": od.get("provenance") == "derived_from_this_dataset",
                "two_by_two": two_by_two,
                "rows": rows,
                "prev_rows": prev_rows,
                "indeterminate_both_ways": (
                    (decl.get("indeterminates") or {}).get("policy") == "report_both_ways"
                ),
                "sentences": claim_sentences(document, {"OVERALL_ESTIMATE"}, operating_point=op),
            }
        )
    return out


def threshold_free_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for label, key, kind in (
        ("AUROC", "auroc", "three_dp"),
        ("AUPRC", "auprc", "three_dp"),
        ("Prevalence", "prevalence", "proportion"),
    ):
        ptr = _p("overall", "threshold_free", key)
        c = cell(document, ptr, kind, "cell")
        if not c["present"]:
            c["text"] = "not computed in this run" + (" (v1.1)" if key == "auprc" else "")
        rows.append({"label": label, "cell": c, "method": cell(document, ptr, kind, "method")})
    return rows


CALIBRATION_ROWS: tuple[tuple[str, str], ...] = (
    ("O:E ratio", "oe"),
    ("Calibration-in-the-large (a | b = 1)", "intercept_large"),
    ("Calibration slope (b)", "slope"),
    ("Intercept (joint fit)", "intercept"),
    ("Brier score", "brier"),
    ("Reference Brier", "brier_ref"),
    ("IPA", "ipa"),
    ("ECE, ten equal-width bins (supplementary)", "ece_equal_width_10"),
    ("ECE, ten equal-mass bins (supplementary)", "ece_equal_mass_10"),
)


def calibration_block(document: dict[str, Any]) -> dict[str, Any]:
    cal = document.get("calibration")
    reason = document.get("calibration_suppressed_reason")
    if not isinstance(cal, dict):
        return {
            "present": False,
            "reason": (
                {
                    "reason": fmt.text(reason.get("reason")),
                    "score_type": fmt.text(reason.get("score_type")),
                    "orientation": fmt.text(reason.get("orientation")),
                }
                if isinstance(reason, dict)
                else None
            ),
            "sentences": claim_sentences(document, {"CALIB_NA"}),
        }
    rows = []
    for label, key in CALIBRATION_ROWS:
        if key not in cal:
            continue
        ptr = _p("calibration", key, "number")
        rows.append(
            {
                "label": label,
                "key": key,
                "cell": cell(document, ptr, "three_dp", "cell"),
                "method": cell(document, ptr, "three_dp", "method"),
            }
        )
    deciles = []
    for j, b in enumerate(cal.get("decile_curve") or []):
        ptr = _p("calibration", "decile_curve", j, "observed", "number")
        deciles.append(
            {
                "bin": fmt.count(b.get("bin")),
                "n": fmt.count(b.get("n")),
                "mean_pred": fmt.scalar(b.get("mean_pred")),
                "observed": cell(document, ptr, "proportion", "cell"),
            }
        )
    flag = cal.get("curve_flag")
    return {
        "present": True,
        "rows": rows,
        "deciles": deciles,
        "curve_note": fmt.text(flag.get("note")) if isinstance(flag, dict) else None,
        "clustered": bool((document.get("flow") or {}).get("clustered")),
        "ipa_tiers": fmt.tiers((cal.get("ipa") or {}).get("number") or {}),
        "sentences": claim_sentences(document, {"CALIB_HIERARCHY", "CALIB_NA"}),
    }


def _tier_mark(tier: Any) -> str:
    if not tier:
        return ""
    return fmt.TIER_SUPERSCRIPTS.get(str(tier), str(tier))


def subgroup_blocks(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Section 9 (and section 4's site table): per attribute and operating point, T1-10
    (5.3) with the reference level first, the other levels in the engine's order, the
    Unknown/missing row and Overall last; T1-11 (5.3b) differences against the reference
    level with each criterion scoped on the attribute; the exploratory footnote."""
    decl = document.get("declarations") or {}
    ref_type = (decl.get("reference_standard") or {}).get("type") or "reference_standard"
    se, sp = _SE_SP.get(ref_type, _SE_SP["reference_standard"])
    rows_all = document.get("subgroups") or []
    crit_rows = document.get("criteria_results") or []
    out = []
    for meta in sorted(
        (a for a in document.get("subgroup_attributes") or [] if isinstance(a, dict)),
        key=lambda a: str(a.get("attribute")),
    ):
        attribute = str(meta.get("attribute"))
        idx = [i for i, r in enumerate(rows_all) if str(r.get("attribute")) == attribute]
        ref_level = meta.get("reference_level")
        order = [str(x) for x in meta.get("level_order") or []]

        def rank(i: int, _order=order, _ref=ref_level) -> tuple[int, int, str]:
            r = rows_all[i]
            lv = str(r.get("level"))
            if r.get("is_reference") or lv == str(_ref):
                return (0, 0, lv)
            if r.get("is_unknown_row"):
                return (2, 0, lv)
            return (1, _order.index(lv) if lv in _order else len(_order), lv)

        idx.sort(key=rank)
        per_op = []
        for op in _ops(document):
            table = []
            diffs = []
            for i in idx:
                r = rows_all[i]
                lv = str(r.get("level"))
                table.append(
                    {
                        "level": lv,
                        "is_reference": bool(r.get("is_reference")),
                        "is_unknown": bool(r.get("is_unknown_row")),
                        "n": fmt.count(r.get("n")),
                        "events": fmt.count(r.get("events")),
                        "se": cell(
                            document, _p("subgroups", i, "metrics", op, se, "number"), "proportion"
                        ),
                        "sp": cell(
                            document, _p("subgroups", i, "metrics", op, sp, "number"), "proportion"
                        ),
                        "auroc": cell(
                            document, _p("subgroups", i, "metrics", "auroc", "number"), "three_dp"
                        ),
                        "prespecified": "yes" if r.get("prespecified") else "no",
                        "tier": _tier_mark(r.get("tier")),
                    }
                )
                if r.get("is_reference"):
                    continue
                crits = []
                for k, row in enumerate(crit_rows):
                    scope = row.get("scope")
                    if (
                        isinstance(scope, dict)
                        and str(scope.get("attribute")) == attribute
                        and str(scope.get("level")) == lv
                    ):
                        crits.append(
                            {
                                "position": k + 1,
                                "id": fmt.text(row.get("criterion_id")),
                                "status_word": render_html.STATUS_WORDS[row["status"]],
                                "max_lb": fmt.scalar(row.get("max_lower_bound_at_n")),
                                "n": fmt.count(row.get("n")) if row.get("n") is not None else "—",
                                "attainable": fmt.scalar(row.get("attainable_at_n")),
                            }
                        )
                diffs.append(
                    {
                        "level": lv,
                        "se": cell(
                            document,
                            _p("subgroups", i, "diff_vs_reference", op, se, "number"),
                            "difference_pp",
                        ),
                        "sp": cell(
                            document,
                            _p("subgroups", i, "diff_vs_reference", op, sp, "number"),
                            "difference_pp",
                        ),
                        "auroc": cell(
                            document,
                            _p("subgroups", i, "diff_vs_reference", "auroc", "number"),
                            "difference_3dp",
                        ),
                        "criteria": crits,
                    }
                )
            overall = (document.get("overall") or {}).get(op) or {}
            tests = [
                {
                    "metric": fmt.text(t.get("metric")),
                    "test": fmt.text(t.get("test")),
                    "p_raw": fmt.p_value(t.get("p_raw")),
                    "p_holm": fmt.p_value(t.get("p_holm")),
                    "reason": fmt.text(t.get("not_estimable_reason")),
                }
                for t in ((meta.get("heterogeneity") or {}).get("tests") or [])
                if t.get("operating_point") in (op, None)
            ]
            per_op.append(
                {
                    "op": op,
                    "table": table,
                    "overall": {
                        "n": fmt.count((overall.get("accuracy") or {}).get("n")),
                        "events": fmt.count((overall.get(se) or {}).get("n")),
                        "se": cell(document, _p("overall", op, se), "proportion"),
                        "sp": cell(document, _p("overall", op, sp), "proportion"),
                        "auroc": cell(
                            document, _p("overall", "threshold_free", "auroc"), "three_dp"
                        ),
                    },
                    "diffs": diffs,
                    "has_criteria": any(d["criteria"] for d in diffs),
                    "tests": tests,
                    "sentence": fmt.text((meta.get("heterogeneity") or {}).get("sentence")),
                    "route": fmt.text((meta.get("heterogeneity") or {}).get("clustering_route")),
                }
            )
        out.append(
            {
                "attribute": attribute,
                "reference_level": fmt.text(ref_level),
                "reference_rule": fmt.text(meta.get("reference_rule")),
                "prespecified": bool(meta.get("prespecified")),
                "source": fmt.text(meta.get("source")),
                "ops": per_op,
                "sentences": claim_sentences(
                    document,
                    {"SUBGROUP_ESTIMATE", "SUBGROUP_ESTIMATE_WITH_DIFF"},
                    attribute=attribute,
                ),
            }
        )
    return out


def fairness_block(document: dict[str, Any]) -> dict[str, Any] | None:
    f = document.get("fairness")
    if not isinstance(f, dict):
        return None
    ops = _ops(document)
    gaps = []
    for j, g in enumerate(f.get("gaps") or []):
        for op in ops:
            base = ("fairness", "gaps", j, "operating_points", op)
            gaps.append(
                {
                    "level": fmt.text(g.get("level")),
                    "op": op,
                    "tpr": cell(document, _p(*base, "tpr_gap", "number"), "difference_pp"),
                    "fpr": cell(document, _p(*base, "fpr_gap", "number"), "difference_pp"),
                    "ppv": cell(document, _p(*base, "ppv_gap", "number"), "difference_pp"),
                    "npv": cell(document, _p(*base, "npv_gap", "number"), "difference_pp"),
                    "auroc": cell(
                        document, _p("fairness", "gaps", j, "auroc_gap", "number"), "difference_3dp"
                    ),
                    "selection": cell(
                        document, _p(*base, "selection_rate_gap", "number"), "difference_pp"
                    ),
                    "calibration_reason": fmt.text(
                        (g.get("calibration") or {}).get("not_estimable_reason")
                    ),
                }
            )
    return {
        "attribute": fmt.text(f.get("attribute")),
        "reference_level": fmt.text(f.get("reference_level")),
        "criterion_of_interest": fmt.text(f.get("criterion_of_interest")),
        "bound": fmt.declared(f.get("bound")),
        "author": fmt.text(f.get("author")),
        "date": fmt.text(f.get("date")),
        "justification": fmt.text(f.get("justification")),
        "citation": fmt.text(f.get("impossibility_citation")),
        "gaps": gaps,
        "sentences": claim_sentences(document, {"FAIRNESS_GAP"}),
    }


def public_summary_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Table T1-18 (D4 section 2 row 14): Metric, estimate, 95% CI, n."""
    decl = document.get("declarations") or {}
    ref_type = (decl.get("reference_standard") or {}).get("type") or "reference_standard"
    se, sp = _SE_SP.get(ref_type, _SE_SP["reference_standard"])
    rows = []
    for op in _ops(document):
        for key in (se, sp, "ppv", "npv", "accuracy"):
            if key not in ((document.get("overall") or {}).get(op) or {}):
                continue
            ptr = _p("overall", op, key)
            found, num = resolve_pointer(document, ptr)
            rows.append(
                {
                    "metric": f"{METRIC_NAMES.get(key, key)} ({op})",
                    "op": op,
                    "est": cell(document, ptr, "proportion", "est"),
                    "ci": cell(document, ptr, "proportion", "ci"),
                    "n": fmt.count(num.get("n")) if found and isinstance(num, dict) else "—",
                }
            )
    ptr = _p("overall", "threshold_free", "auroc")
    found, num = resolve_pointer(document, ptr)
    if found and isinstance(num, dict):
        n = (
            f"{fmt.count(num.get('n_pos'))} + {fmt.count(num.get('n_neg'))}"
            if num.get("n_pos") is not None
            else "—"
        )
        rows.append(
            {
                "metric": "AUROC",
                "op": None,
                "est": cell(document, ptr, "three_dp", "est"),
                "ci": cell(document, ptr, "three_dp", "ci"),
                "n": n,
            }
        )
    return rows


def t1_context(document: dict[str, Any], guidance_map: Any = None) -> dict[str, Any]:
    ids = [r["id"] for r in document.get("guidance_refs") or [] if isinstance(r, dict)]
    for group in T1_ANCHORS.values():
        ids += list(group)
    ids += list(render_html.T8_ANCHORS.values())
    refs = anchors.resolve(ids, guidance_map)
    by_id = {r["id"]: r for r in refs}
    slots = _slots(document)
    outstanding = sum(1 for s in slots.values() if not s["filled"])
    decl = document.get("declarations") or {}
    model = decl.get("model") or {}
    m = document["manifest"]
    t1 = document.get("table1") or {}
    not_computed = t1.get("not_computed") or {}
    ref_std = decl.get("reference_standard") or {}
    crit_rows = render_html.criteria_rows(document)
    ctx: dict[str, Any] = {
        "template_name": "T1 · FDA AI-DSF performance evidence attachment set",
        "document": document,
        "cover_note": COVER_NOTE,
        "model": {
            "name": fmt.text(model.get("name")),
            "version": fmt.text(model.get("version")),
        },
        "cover_rows": [
            ("Run id", fmt.text(m.get("run_id")), True),
            ("Engine version", fmt.text(m.get("engine_version")), False),
            ("Reference platform", fmt.scalar(m.get("reference_platform")), False),
            ("Dataset SHA-256", fmt.text(m.get("input_sha256")) or "not recorded", True),
        ],
        "long_form_title": render_html.LONG_FORM_TITLE,
        "long_form_items": render_html.LONG_FORM_ITEMS,
        "slots": slots,
        "outstanding": outstanding,
        "anchors": {k: [by_id[i] for i in v] for k, v in T1_ANCHORS.items()},
        "declaration_rows": render_html.declaration_rows(document),
        "flow_rows": flow_rows(document),
        "table1_rows": table1_rows(document),
        "dev_note": (
            "development-set summary not supplied - dev-vs-test similarity not assessed"
            if t1.get("dev") is None
            else None
        ),
        "overlap_note": (
            "Test-set independence was not assessed in this run: table1.overlap is null "
            f"(not computed: {fmt.text(not_computed.get('overlap')) or 'no reason recorded'})."
            if t1.get("overlap") is None
            else None
        ),
        "reference_standard": {
            "type": fmt.text(ref_std.get("type")),
            "description": fmt.text(ref_std.get("description")),
        },
        "performance": performance_blocks(document),
        "threshold_free": threshold_free_rows(document),
        "auroc_sentences": claim_sentences(document, {"AUROC_ESTIMATE"}),
        "calibration": calibration_block(document),
        "subgroups": subgroup_blocks(document),
        "fairness": fairness_block(document),
        "criteria_rows": crit_rows,
        "has_criteria": bool(document.get("criteria_results")) or bool(decl.get("criteria")),
        "criterion_sentences": claim_sentences(document, {"CRITERION_STATUS"}),
        "public_summary_note": PUBLIC_SUMMARY_NOTE,
        "public_summary": public_summary_rows(document),
        "model_card_note": MODEL_CARD_NOTE,
        "tier_legend": (
            ("ᵃ", "n < 10: not evaluable, shown for transparency"),
            ("ᵇ", "10 <= n < 30 or events < 5: very low precision"),
            ("ᶜ", "Wilson half-width > 0.10: imprecise"),
        ),
        "guidance_refs": refs,
        "figures": {},
    }
    site = next((s for s in ctx["subgroups"] if s["attribute"] == "site"), None)
    ctx["site_block"] = site
    ctx.update(render_html.furniture(document, "T1", refs, outstanding))
    return ctx


def render_t1(document: dict[str, Any], *, guidance_map: Any = None) -> str:
    env = render_html.environment()
    html = env.get_template(T1_FILE).render(**t1_context(document, guidance_map))
    return render_html.neutralise_bidi(html)


def write_t1(document: dict[str, Any], out_dir: str | Path) -> Path:
    target = Path(out_dir) / T1_FILE
    target.write_bytes(render_t1(document).encode("utf-8"))
    return target
