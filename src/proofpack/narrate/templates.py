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
                "derived_from_this_dataset": (
                    "derived from this dataset and is therefore optimistically biased"
                ),
            }
        },
    ),
    Template(
        "FLOW_COUNTS",
        "{rows_read} rows were read; {excluded_missing_label} lacked a label and "
        "{excluded_missing_score} lacked a score and were excluded; {indeterminate} were "
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
        "For {attribute} = {level}, {metric_name} was {k}/{n} ({est}) [{ci}], a difference of "
        "{diff} percentage points [{diff_ci}] versus {reference_level}.",
        refs=(2, 2),
        guidance_ref="FDA_AIDSF_SUBGROUP_PERF",
    ),
    Template(
        "SUBGROUP_ESTIMATE",
        "For {attribute} = {level}, {metric_name} was {k}/{n} ({est}) [{ci}].",
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
        "For {level} versus {reference_level}: TPR gap {tpr_gap} [{ci}], FPR gap {fpr_gap} "
        "[{ci}], PPV gap {ppv_gap} [{ci}], AUROC gap {auroc_gap} [{ci}].",
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
