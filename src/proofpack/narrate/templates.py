"""The claim template library (D4 section 8): fixed sentence skeletons keyed by
``template_id``, transcribed from D4 section 8's table. A claim names one of these ids
(:mod:`proofpack.narrate.claims`); the checker rejects any other id
(``template_unknown``); the renderer fills every ``{slot}`` from the Number the claim's
``value_refs`` resolve to, or from the fixed phrase maps below. Nothing here computes,
rounds or reformats a number: a skeleton is text with holes.

The library carries, per template, how many ``value_refs`` a claim under it must bind
(``refs``: an inclusive range) and the guidance anchor it cites by default
(``guidance_ref``, an ``internal_id`` of ``design/guidance_map_v1.csv`` or ``None``).
Every FDA AI-DSF anchor is a draft: the label the page prints for it comes from the map
row, never from a template (``proofpack.render.anchors``), and the checker refuses a
draft row whose status lacks the "not for implementation" qualifier.

One id is an engine addition to D4's table, recorded here and in the E8 build note:
``SUBGROUP_ESTIMATE`` - D4 has no sentence for the reference level's own row (its
``diff_vs_reference`` is null by construction) and for a level whose attribute has no
reference; the skeleton is ``SUBGROUP_ESTIMATE_WITH_DIFF`` without the difference clause.

Skeletons whose text differs from D4 section 8's, read on 23 September 2026 against spec
``74837c8`` (repair 4, lens-4 FA-N3): ``FLOW_COUNTS`` adds "(on a table without a score
column, a y_pred)" after "lacked a score" (repair 3, lens FA-N4: since repair 2
``flow.excluded_missing_score`` counts blank ``y_pred`` cells on a table without a score
column, and D4's words named a score only); ``CRITERION_STATUS`` prints " - " where D4
has an em dash; ``KS_RESULT`` prints "Kolmogorov-Smirnov" where D4 has an en dash.
``REF_STD_TYPE_NOTE`` carries D4's two sentences as a phrase map.
``SUBGROUP_ESTIMATE_WITH_DIFF``, ``SUBGROUP_ESTIMATE`` (and their not-estimable variants)
add " at operating point {op_id}" after the group (E9 repair 2, lens-2 FA-B1: on a run
declaring op1 and op2, T1 printed "For age = 0-40, sensitivity was 30/38" and "... was
36/38" with nothing naming which operating point each figure belongs to; the claim already
carries ``operating_point``). ``FAIRNESS_GAP`` reads "For {level} versus {reference_level}:
at operating point {op_id}, TPR gap ..., FPR gap ..., PPV gap ...; AUROC gap (no operating
point) ..." (E9 repair 3, lens-3 FA-N1: repair 2's "For F versus M at operating point op1:
... AUROC gap +0.079" placed the gap read from ``/fairness/gaps/0/auroc_gap/number``, a
pointer with no operating point, at op1, and printed it again at op2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Template:
    template_id: str
    skeleton: str
    refs: tuple[int, int] = (0, 0)
    guidance_ref: str | None = None
    #: The phrase maps a slot draws from (fixed text, never free text).
    phrases: dict[str, dict[str, str]] | None = None
    note: str = ""


_T: list[Template] = [
    Template(
        "DECL_ECHO",
        "{declaration_title}: {value} (declared by {author}, {date}; source: {source}).",
    ),
    Template(
        "THRESH_PROVENANCE",
        "Operating point {op_id} (threshold {threshold}, rule {rule}) was {provenance_phrase}.",
        phrases={
            "provenance_phrase": {
                "prespecified_sap": "pre-specified in the statistical analysis plan ({source})",
                # D4 section 8 prints "and is therefore optimistically biased"; "biased"
                # is a verdict word (checker.VERDICT_WORDS) and no rendered page may carry
                # one (E9 repair 1, lens FA-B1). The sentence states what was done instead.
                "derived_from_this_dataset": (
                    "derived from this dataset: the threshold was chosen on the same data "
                    "its performance is estimated on"
                ),
            }
        },
    ),
    Template(
        "FLOW_COUNTS",
        "{rows_read} rows were read; {excluded_missing_label} lacked a label and "
        "{excluded_missing_score} lacked a score (on a table without a score column, a "
        "y_pred) and were excluded; {indeterminate} were "
        "indeterminate; {analysed} rows from {n_cases} cases across {n_sites} sites were "
        "analysed.",
        refs=(0, 7),
        guidance_ref="FDA_AIDSF_DATA_MGMT",
    ),
    Template(
        "TABLE1_INTRO",
        "Table {ref} reports the distribution of {attribute_list} in the test set{dev_clause}.",
        guidance_ref="FDA_AIDSF_REPRESENTATIVENESS",
    ),
    Template(
        "SIMILARITY_SUMMARY",
        "The largest standardised difference between development and test sets was "
        "{max_std_diff} for {attribute}.",
        refs=(1, 1),
        guidance_ref="FDA_AIDSF_TEST_INDEPENDENCE",
    ),
    Template(
        "OVERLAP_RESULT",
        "{shared_ids} case identifiers and {shared_sites} site identifiers were present in "
        "both development and test tables.",
        refs=(0, 2),
        guidance_ref="FDA_AIDSF_TEST_INDEPENDENCE",
    ),
    Template(
        "SITE_COUNT",
        "The test set comprises {n_sites} site(s).{lt3_clause}",
        refs=(0, 1),
        guidance_ref="FDA_AIDSF_SITE_DIVERSITY",
        note="lt3_clause from fixed text keyed to FDA_AIDSF_SITE_DIVERSITY",
    ),
    Template(
        "REPRESENT_ROW",
        "{attribute}: {level_count} levels; largest {level_max} ({pct_max}); Unknown/missing "
        "{pct_unknown}.",
        guidance_ref="FDA_AIDSF_REPRESENTATIVENESS",
    ),
    Template(
        "UNKNOWN_ROW_NOTE",
        "Rows with a missing value of {attribute} are reported as a separate Unknown/missing "
        "group and are not excluded.",
    ),
    Template(
        "REF_STD_TYPE_NOTE",
        "{ref_std_phrase}",
        guidance_ref="FDA_AIDSF_REF_STANDARD",
        phrases={
            "ref_std_phrase": {
                "comparator": (
                    "The labels derive from a comparator rather than a reference standard; "
                    "agreement is therefore reported as positive and negative percent "
                    "agreement, not sensitivity and specificity."
                ),
                "reference": (
                    "Labels derive from the declared reference standard ({description_ref})."
                ),
            }
        },
    ),
    Template(
        "RATER_COLS_NOTE",
        "{k} rater columns were present; they were not analysed in this version and were not "
        "used to construct the label.",
        guidance_ref="FDA_AIDSF_REF_STANDARD",
    ),
    Template(
        "OVERALL_ESTIMATE",
        "{metric_name} at operating point {op_id} was {k}/{n} ({est}), 95% CI {ci_lo} to "
        "{ci_hi} ({method}).",
        refs=(1, 1),
        guidance_ref="FDA_AIDSF_PERF_VALIDATION",
    ),
    Template(
        "INDET_BOTH_WAYS",
        "With indeterminate results allocated as positive, {metric_name} was {est_pos} [{ci}]; "
        "allocated as negative, {est_neg} [{ci}].",
        refs=(2, 2),
        guidance_ref="FDA_STAT2007_INDETERMINATE",
    ),
    Template(
        "PPV_AT_PREVALENCE",
        "At the declared intended-use prevalence of {pi} ({label}; source {source}), PPV was "
        "{ppv} [{ci}] and NPV {npv} [{ci}].",
        refs=(2, 2),
        guidance_ref="FDA_STAT2007_CI",
    ),
    Template(
        "PREV_MISMATCH_FLAG",
        "Observed prevalence {obs} differs from the declared intended-use prevalence {pi} by "
        "more than {tol}; predictive values are reported at both.",
        refs=(1, 1),
    ),
    Template(
        "AUROC_ESTIMATE",
        "AUROC was {est} [{ci_lo}, {ci_hi}] ({method_phrase}).",
        refs=(1, 1),
        guidance_ref="FDA_AIDSF_PERF_VALIDATION",
        phrases={
            "method_phrase": {
                "iid": "DeLong, logit-transformed interval",
                "clustered": (
                    "cluster bootstrap over {n_cases} cases; DeLong not used because rows are "
                    "clustered"
                ),
                # E9: the engine's i.i.d. AUROC Number carries delong_wald (the synthetic
                # run's), so D4's "logit-transformed" phrase would misstate it; the key
                # is chosen from the Number's own method (proofpack.render.sentences)
                "iid_wald": "DeLong, Wald interval",
            }
        },
    ),
    Template(
        "CALIB_HIERARCHY",
        "The observed-to-expected ratio was {oe} [{ci}]; calibration slope {slope} [{ci}]; "
        "intercept {intercept} [{ci}]; Brier {brier} (reference {brier_ref}; IPA {ipa}).",
        refs=(4, 6),
        guidance_ref="FDA_AIDSF_CALIBRATION",
    ),
    Template(
        "CALIB_CURVE_FLAG",
        "A flexible calibration curve is not shown because events or non-events are below the "
        "ProofPack convention of two hundred each (after Van Calster and colleagues, 2019); "
        "the decile table is reported instead.",
        guidance_ref="FDA_AIDSF_CALIBRATION",
    ),
    Template(
        "CALIB_NA",
        "Calibration statistics are not computed because the score was declared as "
        "{score_type}, not a probability.",
        guidance_ref="FDA_AIDSF_CALIBRATION",
    ),
    Template(
        "SUBGROUP_TABLE_INTRO",
        "Table {ref} reports {metric_list} by {attribute} at operating point {op_id}; the "
        "reference level is {reference_level} ({pre_spec_phrase}).",
        guidance_ref="FDA_AIDSF_SUBGROUP_PERF",
    ),
    Template(
        "SUBGROUP_ESTIMATE_WITH_DIFF",
        "For {attribute} = {level} at operating point {op_id}, {metric_name} was {k}/{n} ({est}) "
        "[{ci}], a difference of {diff} percentage points [{diff_ci}] versus {reference_level}.",
        refs=(2, 2),
        guidance_ref="FDA_AIDSF_SUBGROUP_PERF",
    ),
    Template(
        "SUBGROUP_ESTIMATE",
        "For {attribute} = {level} at operating point {op_id}, {metric_name} was {k}/{n} ({est}) "
        "[{ci}].",
        refs=(1, 1),
        guidance_ref="FDA_AIDSF_SUBGROUP_PERF",
        note=(
            "engine addition to D4 section 8: the reference level's own row and a level "
            "without a reference have no difference clause"
        ),
    ),
    Template(
        "PRESPEC_FLAG",
        "This subgroup analysis was {pre_spec_phrase}.",
        phrases={
            "pre_spec_phrase": {
                "prespecified": "pre-specified ({source})",
                "exploratory": "not pre-specified and is reported as exploratory",
            }
        },
    ),
    Template(
        "LOW_N_CAVEAT",
        "{level_list} contain fewer than {tier_threshold} rows or events; estimates for these "
        "groups are shown for transparency and carry very low precision.",
    ),
    Template(
        "HETERO_EXPLORATORY_FOOTNOTE",
        "An exploratory test of homogeneity across levels of {attribute} gave p = {p} "
        "(Holm-adjusted {p_adj}); no conclusion about subgroup consistency is drawn from this "
        "test.",
        refs=(0, 2),
    ),
    Template(
        "CRITERION_STATUS",
        "Criterion {criterion_id} ({metric_name}, {scope}, {statistic} {comparator} {value}; "
        "{author}, {date}): observed {est} [{ci}] - {status_word}{reason_clause}.",
        refs=(0, 1),
        phrases={
            "status_word": {
                "met": "criterion met",
                "not_met": "criterion not met",
                "not_assessable": "not assessable",
            }
        },
    ),
    Template(
        "CRITERION_NOT_MET_RECORD",
        "Record of criterion not met: {criterion_id}, {scope}, observed {est} [{ci}] against "
        "{comparator} {value}.",
        refs=(0, 1),
        guidance_ref="FDA_PCCP_MP3_PERF_EVAL",
        note="T2 only",
    ),
    Template(
        "ATTAINABILITY_NOTE",
        "At the observed n of {n}, the largest lower confidence bound attainable for "
        "{metric_name} is {max_lb}; criterion {criterion_id} is {attainable_phrase} at this "
        "sample size.",
        refs=(0, 2),
        phrases={
            "attainable_phrase": {"true": "attainable", "false": "not attainable"},
        },
    ),
    Template(
        "FAIRNESS_INTRO",
        "The declared fairness criterion of interest is {criterion_of_interest} for "
        "{attribute} ({author}, {date}); all other gap statistics are descriptive and are not "
        "targets.",
        guidance_ref="FDA_AIDSF_SUBGROUP_PERF",
    ),
    Template(
        "FAIRNESS_GAP",
        "For {level} versus {reference_level}: at operating point {op_id}, TPR gap {tpr_gap} "
        "[{ci}], FPR gap {fpr_gap} [{ci}], PPV gap {ppv_gap} [{ci}]; AUROC gap (no operating "
        "point) {auroc_gap} [{ci}].",
        refs=(4, 4),
        guidance_ref="FDA_AIDSF_SUBGROUP_PERF",
    ),
    Template(
        "SELECTION_RATE_LABEL",
        "Selection-rate (demographic parity) differences are reported for completeness and are "
        "not a target for diagnostic devices.",
    ),
    Template(
        "IMPOSSIBILITY_STATEMENT",
        "Equalised error rates and calibration by group cannot in general hold simultaneously "
        "when base rates differ between groups; see the Methods Appendix for the statement and "
        "citations.",
        guidance_ref="PP_METHODS",
    ),
    Template(
        "LOSO_RESULT",
        "Excluding {site}, {metric_name} was {est} [{ci}] (change {delta} percentage points).",
        refs=(1, 2),
    ),
    Template(
        "THRESH_SENS",
        "At thresholds of {thr_minus} and {thr_plus}, sensitivity was {se_minus} and {se_plus} "
        "and specificity {sp_minus} and {sp_plus}; this is a sensitivity analysis, not a "
        "criterion.",
        refs=(4, 4),
    ),
    Template(
        "MISSINGNESS_SENS",
        "{metric_name} was {est_complete} [{ci}] in rows with complete attributes and "
        "{est_missing} [{ci}] in rows with any missing attribute.",
        refs=(2, 2),
    ),
    Template(
        "DUPLICATES_NOTE",
        "{n_dup} duplicate case identifiers were detected{conflict_clause}.",
        refs=(0, 1),
    ),
    Template(
        "MONITORING_POINTER",
        "Post-market performance monitoring analyses are produced separately (T3) and are not "
        "part of this attachment set.",
        guidance_ref="FDA_AIDSF_MONITORING",
    ),
    Template(
        "PUBLIC_SUMMARY_NUMBERS",
        "Plain-language performance figures for the submitter's own summary: "
        "{metric_list_with_ci}.",
        refs=(1, 12),
        guidance_ref="FDA_AIDSF_PUBLIC_SUMMARY",
    ),
    Template(
        "MODEL_CARD_LIMITS",
        "Limitations evident from the data: {limit_list}.",
        guidance_ref="FDA_AIDSF_MODEL_CARD",
        phrases={
            "limit_item": {
                "sites": "fewer than three sites",
                "small_subgroups": "subgroups with fewer than thirty rows: {levels}",
                "missing_attribute": "no {attribute} attribute supplied",
                "no_dev": "development-set summary not supplied",
            }
        },
    ),
    Template(
        "PAIRED_DIFF",
        "{metric_name} changed by {diff} percentage points [{ci}] from version {prior} to {new} "
        "on {n_pairs} paired cases ({method}).",
        refs=(1, 1),
        guidance_ref="FDA_PCCP_MP3_PERF_EVAL",
    ),
    Template(
        "MCNEMAR_RESULT",
        "{b} cases were correct under the prior version only and {c} under the new version "
        "only (McNemar {method}, p = {p}).",
        refs=(0, 3),
        guidance_ref="FDA_PCCP_MP3_PERF_EVAL",
    ),
    Template(
        "UNPAIRED_LABEL",
        "Versions were evaluated on different cases; the comparison is not like-for-like and "
        "uses unpaired methods.",
        guidance_ref="FDA_PCCP_MP3_PERF_EVAL",
    ),
    Template(
        "LEDGER_STATEMENT",
        "This test set has been used in {n_prior} prior version comparisons recorded in the "
        "local ledger; the manufacturer's declared limit is {limit}.",
        refs=(0, 2),
        guidance_ref="FDA_PCCP_MP1_DATA",
    ),
    Template(
        "LEDGER_WARNING",
        "The declared limit on comparisons against this test set has been reached or exceeded.",
        guidance_ref="FDA_PCCP_MP1_DATA",
    ),
    Template(
        "IMPACT_INPUTS_NOTE",
        "The quantitative differences above are inputs to the manufacturer's impact "
        "assessment; no benefit-risk conclusion is drawn here.",
        guidance_ref="FDA_PCCP_IMPACT",
    ),
    Template(
        "MONITORING_RULE_ECHO",
        "The control rule applied is: {rule_text} ({author}, {date}); effect-size tiers for "
        "PSI: {tiers}.",
        guidance_ref="FDA_AIDSF_MONITORING",
    ),
    Template(
        "PSI_RESULT",
        "PSI for {variable} was {psi} against a critical value of {crit} at α = {alpha} "
        "for {B} bins with n = {n} and m = {m} (p = {p}); tier: {tier}.",
        refs=(1, 1),
        guidance_ref="FDA_AIDSF_MONITORING",
    ),
    Template(
        "KS_RESULT",
        "Kolmogorov-Smirnov D for {variable} was {d} (p = {p}).",
        refs=(1, 1),
        guidance_ref="FDA_AIDSF_MONITORING",
    ),
    Template(
        "PREVALENCE_SHIFT",
        "Observed prevalence moved from {ref} [{ci}] to {cur} [{ci}].",
        refs=(2, 2),
        guidance_ref="FDA_AIDSF_MONITORING",
    ),
    Template(
        "PERIOD_METRIC_ROW",
        "In {period}, {metric_name} was {k}/{n} ({est}) [{ci}].",
        refs=(1, 1),
        guidance_ref="FDA_AIDSF_MONITORING",
    ),
    Template(
        "CONTROL_RULE_STATUS",
        "The declared control rule was {triggered_phrase} in {period}.",
        guidance_ref="FDA_AIDSF_MONITORING",
        phrases={
            "triggered_phrase": {
                "triggered": "triggered",
                "not_triggered": "not triggered",
                "not_assessable": "not assessable ({reason})",
            }
        },
    ),
    Template(
        "SUBGROUP_TREND_ROW",
        "In {period}, {metric_name} was {k}/{n} ({est}) [{ci}].",
        refs=(1, 1),
        guidance_ref="FDA_AIDSF_MONITORING",
        note="same shape as PERIOD_METRIC_ROW with the relevant metric name",
    ),
    Template(
        "AGREEMENT_RATE_ROW",
        "In {period}, {metric_name} was {k}/{n} ({est}) [{ci}].",
        refs=(1, 1),
        guidance_ref="FDA_AIDSF_MONITORING",
        note="same shape as PERIOD_METRIC_ROW with the relevant metric name",
    ),
    Template(
        "INDET_RATE_ROW",
        "In {period}, {metric_name} was {k}/{n} ({est}) [{ci}].",
        refs=(1, 1),
        guidance_ref="FDA_AIDSF_MONITORING",
        note="same shape as PERIOD_METRIC_ROW with the relevant metric name",
    ),
    Template(
        "ATTR_DRIFT_ROW",
        "In {period}, {metric_name} was {k}/{n} ({est}) [{ci}].",
        refs=(1, 1),
        guidance_ref="FDA_AIDSF_MONITORING",
        note="same shape as PERIOD_METRIC_ROW with the relevant metric name",
    ),
    Template(
        "SUMMARY_POINTER",
        "Conclusions, corrective actions and risk analysis are the manufacturer's and are not "
        "drafted here.",
    ),
]

LIBRARY: dict[str, Template] = {t.template_id: t for t in _T}
assert len(LIBRARY) == len(_T), "duplicate template id"

#: The footer under every narrative block (D1 section 4.4; D4 section 1.4), verbatim.
NARRATIVE_FOOTER = (
    "Machine-drafted; requires review by the manufacturer's statistician and regulatory lead."
)

#: The words the renderer prints for a criterion row's status (D4 section 1.2), the only
#: map from the enum to prose. ``CRITERION_STATUS``'s ``status_word`` slot reads it.
STATUS_WORDS: dict[str, str] = LIBRARY["CRITERION_STATUS"].phrases["status_word"]  # type: ignore[index]


def template_ids() -> tuple[str, ...]:
    return tuple(LIBRARY)


def slots(template_id: str) -> tuple[str, ...]:
    """The ``{slot}`` names in a skeleton, in order of appearance."""
    import string

    out: list[str] = []
    for _, field, _, _ in string.Formatter().parse(LIBRARY[template_id].skeleton):
        if field is not None and field not in out:
            out.append(field)
    return tuple(out)


def as_dict() -> dict[str, dict[str, Any]]:
    """The library as JSON-ready data (for T8 and the enum-agreement test)."""
    return {
        t.template_id: {
            "skeleton": t.skeleton,
            "refs": list(t.refs),
            "guidance_ref": t.guidance_ref,
            "slots": list(slots(t.template_id)),
        }
        for t in _T
    }


# ------------------------------------------------------------ slot facets (build day 9, E9)
#
# D1 section 3.1 keys the library ``{template_id, metric_id, subgroup_id, comparator_id,
# status}``; D4 section 8 names the slots. E9 adds, per template, **what each slot takes**
# (E8 carried rows 51 and 52: a slot is filled by the facet of the pointer it names, not
# by the pointer's position, so a claim binding a subset of a family's pointers leaves the
# missing slots visibly unfilled instead of shifting a number into the wrong slot).
#
# The facet-slot syntax (recorded in the E9 build note): a Number slot binds a string
# ``<selector>.<facet>``, one string per occurrence of the slot in the skeleton (so the
# three ``{ci}`` of ``CALIB_HIERARCHY`` bind ``oe.ci``, ``slope.ci`` and
# ``intercept.ci``). The **selector** names a bound pointer by what its path reads,
# through :func:`proofpack.narrate.checker.pointer_facets`: ``value`` (the one Number
# the claim reports, not a difference block), ``diff`` (a ``diff_vs_*`` cell), a metric
# id of a family (``oe``, ``slope``, ``tpr_gap``, ``auroc_gap``, ...) or a documented
# scalar's last path segment (``rows_read``, ``n_sites``, ``max_lower_bound_at_n``).
# The other selectors (``pos``, ``neg``, ``ppv``, ``npv``, ``ref``, ``cur``,
# ``complete``, ``missing``, ``se_minus`` ...) name Numbers of templates no v1 claim binds
# (the checker's ``BOUND_TEMPLATES``): they are filled only when a caller passes them by
# name, as the per-skeleton tests do. The **facet** is one of :data:`FACETS`:
#
# ``est``     the estimate by D4 section 1.2's rule for the metric (``30.8%``, ``0.795``,
#             ``+7.0``), tier superscripts appended; a typed reason prints
#             ``n.e. (<reason>)`` and no digit from ``est``; suppressed prints the
#             suppression marker;
# ``ci_lo`` / ``ci_hi``  one bound by the same rule (``25.5%`` for a proportion);
# ``ci``      the two bounds as a table cell prints them inside brackets (``25.5, 36.6``);
# ``estci``   the whole cell as the tables print it (``0.159 [0.140, 0.181]``);
# ``k`` / ``n``  counts (the only bare integers), an em dash when the Number has none;
# ``method``  the method phrase from :data:`METHOD_PHRASES`;
# ``reason``  the typed reason code (the "not estimable" wording is the skeleton's);
# ``count``   a documented scalar printed as a count; ``p`` a p-value (3 dp, ``<0.001``);
#             ``scalar`` an engine scalar at 3 dp.
#
# A slot with no binding here is a text slot, filled from the context the renderer
# builds for the claim; :data:`CUSTOMER_SLOTS` are the manufacturer's words (printed
# inside ``.customer-text``, DEC-62), :data:`DECLARED_SLOTS` are numbers the manufacturer
# declared (printed by :func:`proofpack.render.format.declared`, every digit), and a slot
# with a phrase map takes its text from that map only.

FACETS: tuple[str, ...] = (
    "est",
    "ci_lo",
    "ci_hi",
    "ci",
    "estci",
    "k",
    "n",
    "method",
    "reason",
    "count",
    "p",
    "scalar",
)

_V = "value"
_ROW_FACETS: dict[str, tuple[str, ...]] = {
    "k": (f"{_V}.k",),
    "n": (f"{_V}.n",),
    "est": (f"{_V}.est",),
    "ci": (f"{_V}.ci",),
}
FACET_BINDINGS: dict[str, dict[str, tuple[str, ...]]] = {
    "FLOW_COUNTS": {
        "rows_read": ("rows_read.count",),
        "excluded_missing_label": ("excluded_missing_label.count",),
        "excluded_missing_score": ("excluded_missing_score.count",),
        "indeterminate": ("indeterminate.count",),
        "analysed": ("analysed.count",),
        "n_cases": ("n_cases.count",),
        "n_sites": ("n_sites.count",),
    },
    "SIMILARITY_SUMMARY": {"max_std_diff": (f"{_V}.estci",)},
    "OVERLAP_RESULT": {
        "shared_ids": ("shared_ids.count",),
        "shared_sites": ("shared_sites.count",),
    },
    "SITE_COUNT": {"n_sites": ("n_sites.count",)},
    "OVERALL_ESTIMATE": {
        "k": (f"{_V}.k",),
        "n": (f"{_V}.n",),
        "est": (f"{_V}.est",),
        "ci_lo": (f"{_V}.ci_lo",),
        "ci_hi": (f"{_V}.ci_hi",),
        "method": (f"{_V}.method",),
    },
    "INDET_BOTH_WAYS": {
        "est_pos": ("pos.est",),
        "ci": ("pos.ci", "neg.ci"),
        "est_neg": ("neg.est",),
    },
    "PPV_AT_PREVALENCE": {"ppv": ("ppv.est",), "ci": ("ppv.ci", "npv.ci"), "npv": ("npv.est",)},
    "PREV_MISMATCH_FLAG": {"obs": ("prevalence.estci",)},
    "AUROC_ESTIMATE": {
        "est": (f"{_V}.est",),
        "ci_lo": (f"{_V}.ci_lo",),
        "ci_hi": (f"{_V}.ci_hi",),
    },
    "CALIB_HIERARCHY": {
        "oe": ("oe.est",),
        "ci": ("oe.ci", "slope.ci", "intercept.ci"),
        "slope": ("slope.est",),
        "intercept": ("intercept.est",),
        # D4's skeleton gives these three no interval slot; every number on the page
        # carries its interval (CLAUDE.md), so each prints as the table cell does
        "brier": ("brier.estci",),
        "brier_ref": ("brier_ref.estci",),
        "ipa": ("ipa.estci",),
    },
    "SUBGROUP_ESTIMATE_WITH_DIFF": {
        **_ROW_FACETS,
        "diff": ("diff.est",),
        "diff_ci": ("diff.ci",),
    },
    "SUBGROUP_ESTIMATE": dict(_ROW_FACETS),
    "HETERO_EXPLORATORY_FOOTNOTE": {"p": ("p_raw.p",), "p_adj": ("p_holm.p",)},
    "CRITERION_STATUS": {"est": (f"{_V}.est",), "ci": (f"{_V}.ci",)},
    "CRITERION_NOT_MET_RECORD": {"est": (f"{_V}.est",), "ci": (f"{_V}.ci",)},
    "ATTAINABILITY_NOTE": {"n": ("n.count",), "max_lb": ("max_lower_bound_at_n.scalar",)},
    "FAIRNESS_GAP": {
        "tpr_gap": ("tpr_gap.est",),
        "ci": ("tpr_gap.ci", "fpr_gap.ci", "ppv_gap.ci", "auroc_gap.ci"),
        "fpr_gap": ("fpr_gap.est",),
        "ppv_gap": ("ppv_gap.est",),
        "auroc_gap": ("auroc_gap.est",),
    },
    "LOSO_RESULT": {"est": (f"{_V}.est",), "ci": (f"{_V}.ci",), "delta": ("diff.est",)},
    "THRESH_SENS": {
        "se_minus": ("se_minus.estci",),
        "se_plus": ("se_plus.estci",),
        "sp_minus": ("sp_minus.estci",),
        "sp_plus": ("sp_plus.estci",),
    },
    "MISSINGNESS_SENS": {
        "est_complete": ("complete.est",),
        "ci": ("complete.ci", "missing.ci"),
        "est_missing": ("missing.est",),
    },
    "DUPLICATES_NOTE": {"n_dup": ("n_dup.count",)},
    "PAIRED_DIFF": {
        "diff": ("diff.est",),
        "ci": ("diff.ci",),
        "n_pairs": ("n_pairs.count",),
        "method": ("diff.method",),
    },
    "MCNEMAR_RESULT": {"b": ("b.count",), "c": ("c.count",), "p": ("p.p",)},
    "LEDGER_STATEMENT": {"n_prior": ("n_prior.count",), "limit": ("limit.count",)},
    "PSI_RESULT": {
        "psi": ("psi.estci",),
        "crit": ("crit.scalar",),
        "B": ("B.count",),
        "n": ("n.count",),
        "m": ("m.count",),
        "p": ("p.p",),
    },
    "KS_RESULT": {"d": ("d.estci",), "p": ("p.p",)},
    "PREVALENCE_SHIFT": {
        "ref": ("ref.est",),
        "ci": ("ref.ci", "cur.ci"),
        "cur": ("cur.est",),
    },
    **{
        tid: dict(_ROW_FACETS)
        for tid in (
            "PERIOD_METRIC_ROW",
            "SUBGROUP_TREND_ROW",
            "AGREEMENT_RATE_ROW",
            "INDET_RATE_ROW",
            "ATTR_DRIFT_ROW",
        )
    },
}

#: Slots whose text is the manufacturer's (DEC-62): printed verbatim, escaped, inside
#: ``.customer-text``, so the verdict grep reads them as the customer's words.
CUSTOMER_SLOTS: frozenset[str] = frozenset(
    {
        "value",
        "author",
        "date",
        "source",
        "op_id",
        "level",
        "reference_level",
        "level_max",
        "level_list",
        "levels",
        "criterion_id",
        "scope",
        "label",
        "description_ref",
        "site",
        "rule_text",
        "tiers",
        "prior",
        "new",
        "period",
        "variable",
        "declaration_title",
        "attribute",
        "attribute_list",
        "criterion_of_interest",
    }
)
#: Numbers the manufacturer declared: printed with every digit ``run.json`` carries.
DECLARED_SLOTS: frozenset[str] = frozenset(
    {"threshold", "pi", "tol", "thr_minus", "thr_plus", "alpha"}
)

#: Method phrases (fixed text) for the ``method`` facet, one per ``Number.method``.
METHOD_PHRASES: dict[str, str] = {
    "wilson": "Wilson score, no continuity correction",
    "wilson_cc": "Wilson score with continuity correction",
    "clopper_pearson": "Clopper-Pearson exact",
    "newcombe10": "Newcombe method 10",
    "newcombe11": "Newcombe method 11",
    "newcombe_paired": "Newcombe paired",
    "delong_logit": "DeLong, logit-transformed interval",
    "delong_wald": "DeLong, Wald interval",
    "cluster_bootstrap_percentile": "cluster bootstrap, percentile interval",
    "bootstrap_percentile": "bootstrap, percentile interval",
    "bootstrap_bca": "bootstrap, BCa interval",
    "irls_wald": "IRLS, Wald interval",
    "log_delta": "delta method on the log scale",
    "logit_delta": "delta method on the logit scale",
    "chi2_psi": "chi-square critical value",
    "exact_mcnemar": "exact McNemar",
    "cc_mcnemar": "continuity-corrected McNemar",
    "none": "no interval method",
}

#: The name a sentence prints for a metric id (D1 section 4.3's enum plus the two the
#: engine emits). A sentence that begins with ``{metric_name}`` capitalises its first
#: letter; the name itself is fixed text.
METRIC_NAMES: dict[str, str] = {
    "sensitivity": "sensitivity",
    "specificity": "specificity",
    "ppa": "positive percent agreement",
    "npa": "negative percent agreement",
    "ppv": "PPV",
    "npv": "NPV",
    "accuracy": "accuracy",
    "balanced_accuracy": "balanced accuracy",
    "f1": "F1",
    "mcc": "MCC",
    "lr_pos": "LR+",
    "lr_neg": "LR-",
    "dor": "diagnostic odds ratio",
    "youden": "Youden J",
    "auroc": "AUROC",
    "auprc": "AUPRC",
    "brier": "Brier score",
    "ipa": "IPA",
    "oe": "observed-to-expected ratio",
    "calibration_slope": "calibration slope",
    "calibration_intercept": "calibration intercept",
    "ece": "ECE",
    "tpr_gap": "TPR gap",
    "fpr_gap": "FPR gap",
    "ppv_gap": "PPV gap",
    "npv_gap": "NPV gap",
    "auroc_gap": "AUROC gap",
    "psi": "PSI",
    "ks_d": "KS D",
    "prevalence": "prevalence",
    "selection_rate": "selection rate",
    "calibration_by_group": "calibration by group",
}
STATISTIC_NAMES: dict[str, str] = {
    "ci_lower_bound": "CI lower bound",
    "ci_upper_bound": "CI upper bound",
    "point_estimate": "point estimate",
}


@dataclass(frozen=True)
class Variant:
    """A skeleton selected by the library key instead of the template's own. ``None`` in
    a field matches anything; a variant matches when every non-``None`` field holds the
    key's value. The first matching variant, in declaration order, wins."""

    name: str
    skeleton: str
    facets: dict[str, tuple[str, ...]]
    metric_ids: frozenset[str] | None = None
    statuses: frozenset[str] | None = None
    subgroup: bool | None = None
    comparator_ids: frozenset[str] | None = None


#: Metric ids an ``OVERALL_ESTIMATE`` prints without ``k/n (...)``: the Numbers that are
#: not proportions (D4 section 1.2's three-decimal rule and the recorded choices).
NON_PROPORTION_OVERALL: frozenset[str] = frozenset(
    {"balanced_accuracy", "f1", "mcc", "lr_pos", "lr_neg", "dor", "youden"}
)
_NA = frozenset({"not_assessable"})

VARIANTS: dict[str, tuple[Variant, ...]] = {
    "OVERALL_ESTIMATE": (
        Variant(
            "not_estimable",
            "{metric_name} at operating point {op_id} was not estimable with an interval "
            "({reason}).",
            {"reason": (f"{_V}.reason",)},
            statuses=_NA,
        ),
        Variant(
            "not_a_proportion",
            "{metric_name} at operating point {op_id} was {est}, 95% CI {ci_lo} to {ci_hi} "
            "({method}).",
            {
                "est": (f"{_V}.est",),
                "ci_lo": (f"{_V}.ci_lo",),
                "ci_hi": (f"{_V}.ci_hi",),
                "method": (f"{_V}.method",),
            },
            metric_ids=NON_PROPORTION_OVERALL,
        ),
    ),
    "AUROC_ESTIMATE": (
        Variant(
            "not_estimable",
            "AUROC was not estimable with an interval ({reason}).",
            {"reason": (f"{_V}.reason",)},
            statuses=_NA,
        ),
    ),
    "SUBGROUP_ESTIMATE": (
        Variant(
            "not_estimable",
            "For {attribute} = {level} at operating point {op_id}, {metric_name} was not estimable "
            "with an interval ({reason}).",
            {"reason": (f"{_V}.reason",)},
            statuses=_NA,
        ),
    ),
    "SUBGROUP_ESTIMATE_WITH_DIFF": (
        Variant(
            "difference_not_estimable",
            "For {attribute} = {level} at operating point {op_id}, {metric_name} was {k}/{n} "
            "({est}) [{ci}]; the difference versus {reference_level} was not estimable with an "
            "interval ({reason}).",
            {**_ROW_FACETS, "reason": ("diff.reason",)},
            statuses=_NA,
        ),
    ),
    "CRITERION_STATUS": (
        Variant(
            "not_assessable",
            "Criterion {criterion_id} ({metric_name}, {scope}, {statistic} {comparator} "
            "{value}; {author}, {date}): {status_word}{reason_clause}.",
            {},
            statuses=_NA,
        ),
    ),
}


def lookup(
    template_id: str,
    metric_id: str | None = None,
    subgroup_id: Any = None,
    comparator_id: str | None = None,
    status: str | None = None,
) -> tuple[str, dict[str, tuple[str, ...]], str]:
    """The skeleton, its facet bindings and the variant name (``base`` for the template's
    own) for one library key (D1 section 3.1: ``{template_id, metric_id, subgroup_id,
    comparator_id, status}``). ``status`` is the criterion status on a criterion claim and
    ``not_assessable`` on any other claim whose ``relation`` is ``not_assessable``.
    ``KeyError`` on an unknown template id."""
    template = LIBRARY[template_id]
    for v in VARIANTS.get(template_id, ()):
        if v.metric_ids is not None and metric_id not in v.metric_ids:
            continue
        if v.statuses is not None and status not in v.statuses:
            continue
        if v.subgroup is not None and (subgroup_id is not None) is not v.subgroup:
            continue
        if v.comparator_ids is not None and comparator_id not in v.comparator_ids:
            continue
        return v.skeleton, v.facets, v.name
    return template.skeleton, FACET_BINDINGS.get(template_id, {}), "base"


def occurrences(skeleton: str) -> tuple[str, ...]:
    """Every ``{slot}`` of a skeleton in order, repeats included."""
    import string

    return tuple(f for _, f, _, _ in string.Formatter().parse(skeleton) if f is not None)


def all_skeletons() -> list[tuple[str, str, str]]:
    """``(template_id, variant, text)`` for every skeleton the library can print and every
    phrase-map text (``phrase:<slot>:<key>``): the forbidden grep's input."""
    out: list[tuple[str, str, str]] = []
    for t in _T:
        out.append((t.template_id, "base", t.skeleton))
        for v in VARIANTS.get(t.template_id, ()):
            out.append((t.template_id, v.name, v.skeleton))
        for slot, table in (t.phrases or {}).items():
            for key, text in table.items():
                out.append((t.template_id, f"phrase:{slot}:{key}", text))
    return out
