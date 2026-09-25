"""T2, the PCCP performance-evaluation report, as HTML (D4 section 3; build day 10, E10).

Nine sections and the cover, in D4 section 3's slot-ownership order, through the same
``base.html`` furniture as T1, T7 and T8 (E9: the cover stamp, the footer on every page,
the margin notes from the guidance-map rows, the Manufacturer-text block and the
placeholder box for every absent customer-text slot). The section to table map:

====  ======================================  ==========================================
 §    Section (anchor)                        Tables and prose
====  ======================================  ==========================================
 0    Cover; PCCP identity (FDA_PCCP_LABELING) cover block (model, version, prior version,
                                              UDI-DI, the two dataset hashes, run id,
                                              engine version, guidance versions), CT-20;
                                              page 2: the long disclaimer
 1    Description of modifications             CT-21; Table T2-1 (no modification list is
      (FDA_PCCP_DESC_MODS)                     read in this build: the no-data box names
                                              Table T2-2 as the criteria evaluated)
 2    MP (1) Data management                   CT-22, CT-23; Table T2-flow for both
      (FDA_PCCP_MP1_DATA)                      versions (5.10); Table 1 of the new
                                              version's test set (5.4); the pair count
 3    MP (2) Re-training practices             CT-24; the version fields echo
      (FDA_PCCP_MP2_RETRAIN)
 4    MP (3) Performance evaluation            CT-25, CT-26; 4.1 Table T2-2 (5.6, with the
      (FDA_PCCP_MP3_PERF_EVAL)                 declared type); 4.2 Table T2-3 (5.7) per
                                              operating point plus the AUROC, Brier and
                                              slope rows; PAIRED_DIFF / MCNEMAR_RESULT
                                              sentences; 4.3 Table T2-4 per subgroup with
                                              the criterion column; 4.4 the calibration
                                              rows of T2-3; 4.5 the AUROC row of T2-3;
                                              4.6 UNPAIRED_LABEL when not like-for-like;
                                              4.7 CRITERION_STATUS and
                                              CRITERION_NOT_MET_RECORD sentences
 5    MP (4) Update procedures                 CT-27; the version stamp;
      (FDA_PCCP_MP4_UPDATE, FDA_PCCP_PMS_PLANS) MONITORING_POINTER
 6    Impact assessment inputs (FDA_PCCP_IMPACT) CT-28, CT-29; Table T2-5 quantitative
                                              deltas with the verbatim caption;
                                              IMPACT_INPUTS_NOTE
 7    Test-set ledger (FDA_PCCP_MP1_DATA)      LEDGER_STATEMENT; LEDGER_WARNING banner
 8    Traceability skeleton                    Table T2-6, one row per criteria row
      (FDA_PCCP_TRACEABILITY)
====  ======================================  ==========================================

**Status words.** The status cells print the engine's three words through
``STATUS_WORDS`` and, on a ``not_met`` row of Table T2-3 and T2-4, :data:`NOT_MET_RECORD`
(D4 section 1.2's fourth permitted string, T2 only). Both live inside ``.status``
elements and nowhere else on the page (``tests/test_e10_t2.py``).

**Margins.** The Margin column prints the customer's declared value of every
``paired_difference_vs_prior`` criterion that names the row's metric, operating point
and scope, one line per criterion with its id, and the Status column that criterion's
status on the same line (E10 repair 2, lens 1 FA-N2 / lens 2 FA-F5: at 667a201 the row
printed the first such criterion only, so a second criterion's ``not_met`` status and
its record string reached no table); the Margin and Status columns are absent from T2-3
when no such criterion is declared (D4 section 5.7: no default margin exists).

**Numbers.** Every Number cell carries ``data-ref``, ``data-kind`` and ``data-facet`` as
T1's do, so the E9 parse test's shape traces each printed figure to ``run.json``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from proofpack.narrate.templates import METRIC_NAMES, STATUS_WORDS
from proofpack.render import anchors
from proofpack.render import format as fmt
from proofpack.render import html as render_html
from proofpack.render.t1 import _p, cell, claim_sentences, table1_rows
from proofpack.render.t7 import flow_rows
from proofpack.scope import PLACEHOLDER

T2_FILE = "T2.html"
TEMPLATE_NAME = "T2 · PCCP performance-evaluation report"
#: D4 section 1.2 / D1 section 2: the one further status string T2 may print.
NOT_MET_RECORD = "record of criterion not met (PCCP §VII.B(3) requires recording)"
#: D4 section 3 row 6, verbatim, on Table T2-5.
IMPACT_CAPTION = (
    "inputs to the manufacturer's impact assessment; no benefit-risk conclusion is drawn"
)
#: The anchors each section's margin notes cite (D4 section 3, the anchor column).
T2_ANCHORS: dict[str, tuple[str, ...]] = {
    "s0": ("FDA_PCCP_LABELING",),
    "scope": ("PP_SCOPE",),
    "s1": ("FDA_PCCP_DESC_MODS",),
    "s2": ("FDA_PCCP_MP1_DATA",),
    "s3": ("FDA_PCCP_MP2_RETRAIN",),
    "s4": ("FDA_PCCP_MP3_PERF_EVAL",),
    "s5": ("FDA_PCCP_MP4_UPDATE", "FDA_PCCP_PMS_PLANS"),
    "s6": ("FDA_PCCP_IMPACT",),
    "s7": ("FDA_PCCP_MP1_DATA",),
    "s8": ("FDA_PCCP_TRACEABILITY",),
}
#: T2's customer-text slots (D4 section 3's column), in order.
CUSTOMER_TEXT_SLOTS: tuple[tuple[str, str], ...] = (
    ("CT-20", "PCCP title and version as authorised or proposed; authorisation number if any"),
    (
        "CT-21",
        "list of modifications: id, description, rationale, automatic or manual, and the "
        "criteria each is verified by",
    ),
    ("CT-22", "reference-standard process for the evaluation set"),
    ("CT-23", "sequestration statement for the evaluation set"),
    ("CT-24", "re-training method"),
    ("CT-25", "study design summary"),
    (
        "CT-26",
        "the manufacturer's own definition of performance that would halt the update",
    ),
    ("CT-27", "update frequency, versioning, user communication and roll-back"),
    ("CT-28", "benefit-risk discussion"),
    ("CT-29", "interaction between modifications"),
)
COVER_NOTE = (
    "Performance-evaluation record prepared for the manufacturer's own PCCP submission or "
    "record. Not a submission. No regulator has accepted, authorised or endorsed this "
    "report or the plan it evaluates."
)
T2_1_NOTE = (
    "No modification list (CT-21) is read in this build, so Table T2-1 lists no "
    "modification; the criteria evaluated for this comparison are Table T2-2, and Table "
    "T2-6 carries their traceability rows."
)
PAIRED_TYPE = "paired_difference_vs_prior"
_SE_SP = {
    "reference_standard": ("sensitivity", "specificity"),
    "comparator": ("ppa", "npa"),
}


def customer_slots(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every CT-20..CT-29 slot: the placeholder box (no ``pack_text.yaml`` is read in
    this build; the engine drafts none of them)."""
    del document
    return {
        slot_id: {
            "id": slot_id,
            "title": title,
            "filled": False,
            "text": PLACEHOLDER.format(title=title),
        }
        for slot_id, title in CUSTOMER_TEXT_SLOTS
    }


def _paired_rows(document: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    """The criteria rows evaluated from a ``paired_difference_vs_prior`` entry, by
    position (the type is read from the declaration entry the row names)."""
    entries = (document.get("declarations") or {}).get("criteria") or []
    out = []
    for i, row in enumerate(document.get("criteria_results") or []):
        k = row.get("declaration_index")
        entry = entries[k] if isinstance(k, int) and 0 <= k < len(entries) else {}
        if isinstance(entry, dict) and entry.get("type") == PAIRED_TYPE:
            out.append((i, row))
    return out


def _margins_for(
    paired: list[tuple[int, dict[str, Any]]], metric: str, op: str | None, scope: Any
) -> list[dict[str, Any]]:
    """Every paired criterion row on this metric, operating point and scope, in
    criteria-table order (``tests/test_e10_criterion.py::
    test_two_paired_criteria_on_the_accuracy_cell_both_print_on_the_t2_3_row``)."""
    out: list[dict[str, Any]] = []
    for i, row in paired:
        row_scope = row.get("scope")
        same_scope = (
            row_scope == scope
            if not isinstance(scope, dict)
            else isinstance(row_scope, dict)
            and str(row_scope.get("attribute")) == str(scope.get("attribute"))
            and str(row_scope.get("level")) == str(scope.get("level"))
        )
        if row.get("metric") == metric and row.get("operating_point") == op and same_scope:
            out.append(
                {
                    "position": i + 1,
                    "id": fmt.text(row.get("criterion_id")),
                    "statistic": fmt.text(row.get("statistic")).replace("_", " "),
                    "comparator": fmt.text(row.get("comparator")),
                    "value": fmt.declared(row.get("value")),
                    "status": row.get("status"),
                    "status_word": STATUS_WORDS[row["status"]],
                    "reason_code": fmt.text(row.get("reason_code")),
                    "record": row.get("status") == "not_met",
                }
            )
    return out


def _difference_kind(metric: str) -> str:
    return fmt.kind_for(metric, difference=True)


def comparison_tables(document: dict[str, Any]) -> dict[str, Any]:
    """Table T2-3 per operating point plus the threshold-free and calibration rows, and
    Table T2-4 per subgroup entry (D4 sections 5.7 and 5.3 + paired columns)."""
    comparison = document.get("comparison") or {}
    decl = document.get("declarations") or {}
    ref_type = (decl.get("reference_standard") or {}).get("type") or "reference_standard"
    se, sp = _SE_SP.get(ref_type, _SE_SP["reference_standard"])
    paired = bool(comparison.get("paired"))
    paired_rows = _paired_rows(document)
    has_margin = bool(paired_rows)
    differences = comparison.get("differences") or {}
    ops = [k for k in differences if k not in ("auroc", "brier", "slope")]
    mcnemar = comparison.get("mcnemar") or {}
    unpaired = comparison.get("unpaired_rows") or {}
    excluded = sum(int(unpaired.get(k) or 0) for k in ("new_only", "prior_only", "label_mismatch"))
    if paired:
        caption = (
            f"n pairs = {fmt.count(comparison.get('n_pairs'))} (row_id join); unpaired rows "
            f"excluded: {fmt.count(excluded)}"
        )
    else:
        caption = (
            "UNPAIRED - not like-for-like; Newcombe 10 / unpaired DeLong "
            f"(new version rows: {fmt.count(comparison.get('n_new'))}; prior version rows: "
            f"{fmt.count(comparison.get('n_prior'))}; rows in one version only: "
            f"{fmt.count(excluded)})"
        )

    def row(label: str, metric: str, op: str | None, prior_ref: str, new_ref: str, diff_ref: str):
        kind = "proportion" if metric in fmt.PROPORTION_IDS else "three_dp"
        # the McNemar test is on the accuracy discordants at the operating point: its
        # b / c and p print on the Accuracy row only (recorded in the E10 note)
        mc = mcnemar.get(op) if op is not None and paired and metric == "accuracy" else None
        margins = _margins_for(paired_rows, metric, op, "overall")
        return {
            "label": label,
            "metric": metric,
            "op": op,
            "prior": cell(document, prior_ref, kind),
            "new": cell(document, new_ref, kind),
            "delta": cell(document, diff_ref, _difference_kind(metric)),
            "method": cell(document, diff_ref, _difference_kind(metric), "method"),
            "b": fmt.count(mc.get("b")) if mc else "—",
            "c": fmt.count(mc.get("c")) if mc else "—",
            "p": fmt.p_value(mc.get("p")) if mc else "—",
            "mcnemar_method": (
                {"exact_mcnemar": "exact", "cc_mcnemar": "continuity-corrected chi-square"}.get(
                    str(mc.get("method")), fmt.text(mc.get("method"))
                )
                if mc
                else "—"
            ),
            "margins": margins,
        }

    per_op = []
    for op in ops:
        rows = [
            row(
                METRIC_NAMES[m].capitalize() if m in (se, sp) else "Accuracy",
                m,
                op,
                _p("comparison", "prior", "overall", op, m),
                _p("overall", op, m),
                _p("comparison", "differences", op, m, "number"),
            )
            for m in (se, sp, "accuracy")
            if m in (differences.get(op) or {})
        ]
        per_op.append({"op": op, "rows": rows})
    free_rows = []
    if "auroc" in differences:
        free_rows.append(
            row(
                "AUROC",
                "auroc",
                None,
                _p("comparison", "prior", "overall", "threshold_free", "auroc"),
                _p("overall", "threshold_free", "auroc"),
                _p("comparison", "differences", "auroc", "number"),
            )
        )
    calibration_rows = []
    for key, metric, label in (
        ("brier", "brier", "Brier score"),
        ("slope", "calibration_slope", "Calibration slope"),
    ):
        if key in differences:
            calibration_rows.append(
                row(
                    label,
                    metric,
                    None,
                    _p("comparison", "prior", "calibration", key, "number"),
                    _p("calibration", key, "number"),
                    _p("comparison", "differences", key, "number"),
                )
            )
    # Table T2-4: per subgroup entry (parallel to document.subgroups)
    subgroup_rows = []
    doc_rows = document.get("subgroups") or []
    for i, entry in enumerate(comparison.get("subgroups") or []):
        if not isinstance(entry, dict):
            continue
        scope = {"attribute": str(entry.get("attribute")), "level": str(entry.get("level"))}
        diffs = entry.get("differences")
        meta = doc_rows[i] if i < len(doc_rows) and isinstance(doc_rows[i], dict) else {}
        crits = []
        for k, r in paired_rows:
            rs = r.get("scope")
            if (
                isinstance(rs, dict)
                and str(rs.get("attribute")) == scope["attribute"]
                and str(rs.get("level")) == scope["level"]
            ):
                crits.append(
                    {
                        "position": k + 1,
                        "id": fmt.text(r.get("criterion_id")),
                        "op": fmt.text(r.get("operating_point")) or "—",
                        "status": r.get("status"),
                        "status_word": STATUS_WORDS[r["status"]],
                        "record": r.get("status") == "not_met",
                        "attainable": fmt.scalar(r.get("attainable_at_n")),
                    }
                )
        per_op_cells = []
        for op in ops:
            base = _p("comparison", "subgroups", i, "differences", op)
            per_op_cells.append(
                {
                    "op": op,
                    "se": cell(document, f"{base}/{se}/number", _difference_kind(se)),
                    "sp": cell(document, f"{base}/{sp}/number", _difference_kind(sp)),
                }
            )
        subgroup_rows.append(
            {
                "attribute": scope["attribute"],
                "level": scope["level"],
                "is_unknown": bool(meta.get("is_unknown_row")),
                "n_pairs": fmt.count(entry.get("n_pairs")),
                "computed": isinstance(diffs, dict),
                "reason": fmt.text(entry.get("not_computed_reason")),
                "ops": per_op_cells,
                "auroc": cell(
                    document,
                    _p("comparison", "subgroups", i, "differences", "auroc", "number"),
                    "difference_3dp",
                ),
                "criteria": crits,
            }
        )
    return {
        "paired": paired,
        "label": fmt.text(comparison.get("label")),
        "caption": caption,
        "has_margin": has_margin,
        "per_op": per_op,
        "free_rows": free_rows,
        "calibration_rows": calibration_rows,
        "subgroup_rows": subgroup_rows,
        "subgroups_not_computed": fmt.text(comparison.get("subgroups_not_computed")),
        "se_label": "Sensitivity" if se == "sensitivity" else "PPA",
        "sp_label": "Specificity" if sp == "specificity" else "NPA",
        "n_pairs": fmt.count(comparison.get("n_pairs")),
        "n_new": fmt.count(comparison.get("n_new")),
        "n_prior": fmt.count(comparison.get("n_prior")),
        "excluded": fmt.count(excluded),
        "unpaired_rows": {k: fmt.count(v) for k, v in unpaired.items()},
        "clustering_route": fmt.text(comparison.get("clustering_route")),
        "bootstrap": {
            k: (fmt.text(v) if isinstance(v, str) else fmt.scalar(v))
            for k, v in (comparison.get("bootstrap") or {}).items()
        },
    }


def impact_rows(document: dict[str, Any], tables: dict[str, Any]) -> list[dict[str, Any]]:
    """Table T2-5: Metric · scope · prior [CI] · new [CI] · Δ [CI], the overall rows of
    T2-3 then each subgroup difference (the prior version's subgroup estimates are not
    computed in this build, so those rows print a dash in the prior and new columns and
    the paired difference alone)."""
    out = []
    for block in tables["per_op"]:
        for r in block["rows"]:
            out.append(
                {
                    "metric": r["label"],
                    "scope": f"overall, {r['op']}",
                    "prior": r["prior"],
                    "new": r["new"],
                    "delta": r["delta"],
                }
            )
    for r in tables["free_rows"] + tables["calibration_rows"]:
        out.append(
            {
                "metric": r["label"],
                "scope": "overall",
                "prior": r["prior"],
                "new": r["new"],
                "delta": r["delta"],
            }
        )
    dash = {"text": "—", "ref": "", "kind": "", "facet": "cell", "present": False}
    for s in tables["subgroup_rows"]:
        if not s["computed"]:
            continue
        for o in s["ops"]:
            for label, key in ((tables["se_label"], "se"), (tables["sp_label"], "sp")):
                out.append(
                    {
                        "metric": label,
                        "scope": f"{s['attribute']} = {s['level']}, {o['op']}",
                        "prior": dash,
                        "new": dash,
                        "delta": o[key],
                    }
                )
        out.append(
            {
                "metric": "AUROC",
                "scope": f"{s['attribute']} = {s['level']}",
                "prior": dash,
                "new": dash,
                "delta": s["auroc"],
            }
        )
    return out


def traceability_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Table T2-6: one row per criteria row, by position."""
    entries = (document.get("declarations") or {}).get("criteria") or []
    out = []
    for i, row in enumerate(document.get("criteria_results") or []):
        k = row.get("declaration_index")
        entry = entries[k] if isinstance(k, int) and 0 <= k < len(entries) else {}
        paired = isinstance(entry, dict) and entry.get("type") == PAIRED_TYPE
        out.append(
            {
                "position": i + 1,
                "modification": "—",
                "mp_section": "4.2 (paired comparison)" if paired else "4.1 (criteria echo)",
                "criterion_id": fmt.text(row.get("criterion_id")),
                "status_word": STATUS_WORDS[row["status"]],
                "impact_slot": "CT-28; Table T2-5",
                "monitoring": "—",
            }
        )
    return out


def version_rows(document: dict[str, Any]) -> list[tuple[str, str]]:
    model = (document.get("declarations") or {}).get("model") or {}
    comparison = document.get("comparison") or {}
    return [
        ("Model", fmt.text(model.get("name"))),
        ("Version evaluated (new)", fmt.text(model.get("version"))),
        (
            "Prior version",
            fmt.text(comparison.get("prior_version", model.get("prior_version"))) or "not declared",
        ),
        ("UDI-DI", fmt.text(model.get("udi_di")) or "not declared"),
    ]


def t2_context(document: dict[str, Any], guidance_map: Any = None) -> dict[str, Any]:
    if not isinstance(document.get("comparison"), dict):
        raise ValueError("T2 is rendered from a compare document (it carries no comparison block)")
    ids = [r["id"] for r in document.get("guidance_refs") or [] if isinstance(r, dict)]
    for group in T2_ANCHORS.values():
        ids += list(group)
    refs = anchors.resolve(ids, guidance_map)
    by_id = {r["id"]: r for r in refs}
    slots = customer_slots(document)
    outstanding = sum(1 for s in slots.values() if not s["filled"])
    m = document["manifest"]
    comparison = document["comparison"]
    tables = comparison_tables(document)
    ledger = comparison.get("ledger") or {}
    prior = comparison.get("prior") or {}
    ctx: dict[str, Any] = {
        "template_name": TEMPLATE_NAME,
        "document": document,
        "cover_note": COVER_NOTE,
        "version_rows": version_rows(document),
        "cover_rows": [
            ("Run id", fmt.text(m.get("run_id")), True),
            ("Engine version", fmt.text(m.get("engine_version")), False),
            ("Reference platform", fmt.scalar(m.get("reference_platform")), False),
            (
                "Dataset SHA-256 (new version)",
                fmt.text(m.get("input_sha256")) or "not recorded",
                True,
            ),
            (
                "Dataset SHA-256 (prior version)",
                fmt.text(m.get("prior_input_sha256")) or "not recorded",
                True,
            ),
        ],
        "long_form_title": render_html.LONG_FORM_TITLE,
        "long_form_items": render_html.LONG_FORM_ITEMS,
        "slots": slots,
        "outstanding": outstanding,
        "anchors": {
            k: [anchors.with_note_fields(by_id[i], guidance_map) for i in v]
            for k, v in T2_ANCHORS.items()
        },
        "t2_1_note": T2_1_NOTE,
        "flow_rows": flow_rows(document),
        "prior_flow_rows": flow_rows(prior) if prior.get("flow") else [],
        "table1_rows": table1_rows(document),
        "tables": tables,
        "criteria_rows": render_html.criteria_rows(document),
        "has_criteria": bool(document.get("criteria_results"))
        or bool((document.get("declarations") or {}).get("criteria")),
        "not_met_record": NOT_MET_RECORD,
        "comparison_sentences": claim_sentences(document, {"PAIRED_DIFF", "MCNEMAR_RESULT"}),
        "unpaired_sentences": claim_sentences(document, {"UNPAIRED_LABEL"}),
        "criterion_sentences": claim_sentences(
            document, {"CRITERION_STATUS", "CRITERION_NOT_MET_RECORD"}
        ),
        "monitoring_sentences": claim_sentences(document, {"MONITORING_POINTER"}),
        "impact_sentences": claim_sentences(document, {"IMPACT_INPUTS_NOTE"}),
        "ledger_sentences": claim_sentences(document, {"LEDGER_STATEMENT", "LEDGER_WARNING"}),
        "impact_caption": IMPACT_CAPTION,
        "impact_rows": impact_rows(document, tables),
        "traceability_rows": traceability_rows(document),
        "ledger": {
            "test_set_sha256": fmt.text(ledger.get("test_set_sha256")),
            "short": fmt.text(ledger.get("test_set_sha256"))[:12],
            "prior_runs": fmt.count(ledger.get("prior_acceptance_runs")),
            "warn_limit": (
                "no limit declared"
                if ledger.get("warn_limit") is None
                else fmt.count(ledger.get("warn_limit"))
            ),
            "limit_reached": bool(ledger.get("limit_reached")),
        },
        "guidance_refs": refs,
    }
    ctx.update(render_html.furniture(document, "T2", refs, outstanding))
    return ctx


def render_t2(document: dict[str, Any], *, guidance_map: Any = None) -> str:
    env = render_html.environment()
    html = env.get_template(T2_FILE).render(**t2_context(document, guidance_map))
    return render_html.neutralise_bidi(html)


def write_t2(document: dict[str, Any], out_dir: str | Path) -> Path:
    target = Path(out_dir) / T2_FILE
    target.write_bytes(render_t2(document).encode("utf-8"))
    return target
