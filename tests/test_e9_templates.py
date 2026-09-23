"""Build day 9 (E9 item 1): the claim template library and the sentence renderer.

* **one test per skeleton**: every skeleton D4 section 8 lists, and every variant the
  library key selects (:data:`proofpack.narrate.templates.VARIANTS`), is rendered from
  literal Numbers written out below and compared with the exact sentence, typed here by
  hand from D4 section 1.2's rules. The proportion is D4 section 1.2's own example
  ``81/263 (30.8%) [25.5, 36.6]``; the difference is its ``-3.2 [-6.1, -0.4]``;
* a Number carrying a typed reason prints the reason and **no digit from ``est``**;
* the **forbidden grep** over the text of every skeleton, variant and phrase is zero
  (``test_the_forbidden_grep_over_every_skeleton_variant_and_phrase_is_zero``, reusing the
  checker's own ``VERDICT_WORDS`` and ``CERTIFICATION_WORDS`` and D4 section 1.2's list);
* slot filling **by pointer facet** (E8 carried rows 51 and 52): a ``CALIB_HIERARCHY``
  claim binding a subset of the family's pointers prints ``not reported`` in the missing
  slots and the right figure in each other slot, whatever the pointer order;
* every claim the synthetic run generates renders, and each figure the sentence prints
  equals :mod:`proofpack.render.format` of the Number its pointer names.
"""

from __future__ import annotations

import copy
import re
import string
from typing import Any

import pytest

from assembler import assemble
from conftest import make_criteria
from proofpack.narrate import checker
from proofpack.narrate import templates as lib
from proofpack.render import format as fmt
from proofpack.render import sentences
from proofpack.stats.number import METHODS
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site

pytestmark = pytest.mark.day9


def _num(est, lo, hi, method="wilson", **kw) -> dict[str, Any]:
    out = {
        "est": est,
        "ci_lo": lo,
        "ci_hi": hi,
        "ci_level": 0.95,
        "method": method,
        "flags": [],
        "suppressed": False,
        "not_estimable_reason": None,
    }
    out.update(kw)
    return out


def _ne(reason: str, est: float | None = 0.4444, **kw) -> dict[str, Any]:
    return _num(est, None, None, "none", not_estimable_reason=reason, **kw)


#: D4 section 1.2's example cell, 81/263 (30.8%) [25.5, 36.6]
PROP = _num(0.30798, 0.25497, 0.36623, n=263, k=81)
PROP2 = _num(0.27376, 0.22343, 0.33052, n=263, k=72)
PROP_TIER = _num(0.30798, 0.25497, 0.36623, n=263, k=81, flags=["imprecise"])
AUROC = _num(0.79512, 0.74219, 0.84071, "delong_wald", n_pos=81, n_neg=182)
#: D4 section 1.2's example difference, -3.2 [-6.1, -0.4]
DIFF = _num(-0.03204, -0.06111, -0.00398, "newcombe10", n=263)
DIFF_PAIRED = _num(-0.03204, -0.06111, -0.00398, "newcombe_paired", n=250)
#: D4 section 5.3b's AUROC difference, -0.012 [-0.041, 0.017] (signed here: +0.017)
DIFF3 = _num(-0.01212, -0.04108, 0.01702, "delong_wald")
OE = _num(1.14432, 0.98761, 1.32588, "log_delta")
SLOPE = _num(1.19512, 0.90217, 1.48806, "irls_wald")
INTERCEPT = _num(0.50044, 0.10233, 0.89856, "irls_wald")
BRIER = _num(0.15912, 0.14022, 0.18107, "bootstrap_percentile")
BRIER_REF = _ne("fixed_by_outcome_stratification", est=0.24)
IPA = _num(
    0.33851, -0.02903, 0.61482, "bootstrap_percentile", flags=["very_low_precision", "imprecise"]
)
TPR = _num(0.07033, -0.07936, 0.21705, "newcombe10")
FPR = _num(-0.04814, -0.14842, 0.05399, "newcombe10")
PPVG = _num(0.08872, -0.06161, 0.23312, "newcombe10")
PPV_PI = _num(0.12341, 0.09876, 0.15321, "logit_delta")
NPV_PI = _num(0.98771, 0.98012, 0.99231, "logit_delta")
LR = _num(3.09112, 2.45013, 3.90018, "log_delta")
STDDIFF = _num(0.21034, 0.08811, 0.33257, "bootstrap_percentile")
PSI = _num(0.05812, 0.03101, 0.08944, "chi2_psi")
KS = _num(0.14021, 0.08233, 0.19809, "bootstrap_percentile")

PROP_TXT = "81/263 (30.8%) [25.5, 36.6]"
PROP2_TXT = "72/263 (27.4%) [22.3, 33.1]"
AUTHOR = {"author": "Dr A. B.", "date": "2026-03-01"}
CRIT = {
    "criterion_id": "C1",
    "scope": "overall, op1",
    "statistic": "CI lower bound",
    "comparator": ">=",
    **AUTHOR,
}

#: (case id, template, variant, kwargs for render_parts, the exact sentence)
CASES: list[tuple[str, str, str, dict[str, Any], str]] = [
    (
        "decl_echo",
        "DECL_ECHO",
        "base",
        {
            "text": {
                "declaration_title": "Positive class",
                "value": "1",
                "source": "SAP v2",
                **AUTHOR,
            }
        },
        "Positive class: 1 (declared by Dr A. B., 2026-03-01; source: SAP v2).",
    ),
    (
        "thresh_prespecified",
        "THRESH_PROVENANCE",
        "base",
        {
            "text": {
                "op_id": "op1",
                "threshold": 0.4275,
                "rule": ">=",
                "provenance_phrase": "prespecified_sap",
                "source": "SAP v2 section 4",
            }
        },
        "Operating point op1 (threshold 0.4275, rule >=) was pre-specified in the statistical "
        "analysis plan (SAP v2 section 4).",
    ),
    (
        "thresh_derived",
        "THRESH_PROVENANCE",
        "base",
        {
            "text": {
                "op_id": "t0.5",
                "threshold": 0.5,
                "rule": ">",
                "provenance_phrase": "derived_from_this_dataset",
            }
        },
        "Operating point t0.5 (threshold 0.5, rule >) was derived from this dataset and is "
        "therefore optimistically biased.",
    ),
    (
        "flow_counts",
        "FLOW_COUNTS",
        "base",
        {
            "numbers": {
                "rows_read": 400,
                "excluded_missing_label": 3,
                "excluded_missing_score": 2,
                "indeterminate": 5,
                "analysed": 390,
                "n_cases": 130,
                "n_sites": 3,
            }
        },
        "400 rows were read; 3 lacked a label and 2 lacked a score (on a table without a score "
        "column, a y_pred) and were excluded; 5 were indeterminate; 390 rows from 130 cases "
        "across 3 sites were analysed.",
    ),
    (
        "table1_intro",
        "TABLE1_INTRO",
        "base",
        {"text": {"ref": "T1-3", "attribute_list": "sex, age and site", "dev_clause": ""}},
        "Table T1-3 reports the distribution of sex, age and site in the test set.",
    ),
    (
        "similarity",
        "SIMILARITY_SUMMARY",
        "base",
        {"numbers": {"value": STDDIFF}, "text": {"attribute": "age"}},
        "The largest standardised difference between development and test sets was 0.210 "
        "[0.088, 0.333] for age.",
    ),
    (
        "overlap",
        "OVERLAP_RESULT",
        "base",
        {"numbers": {"shared_ids": 0, "shared_sites": 1}},
        "0 case identifiers and 1 site identifiers were present in both development and test "
        "tables.",
    ),
    (
        "site_count",
        "SITE_COUNT",
        "base",
        {"numbers": {"n_sites": 2}, "text": {"lt3_clause": ""}},
        "The test set comprises 2 site(s).",
    ),
    (
        "represent_row",
        "REPRESENT_ROW",
        "base",
        {
            "text": {
                "attribute": "sex",
                "level_count": "3",
                "level_max": "F",
                "pct_max": "48.2%",
                "pct_unknown": "2.1%",
            }
        },
        "sex: 3 levels; largest F (48.2%); Unknown/missing 2.1%.",
    ),
    (
        "unknown_row",
        "UNKNOWN_ROW_NOTE",
        "base",
        {"text": {"attribute": "race"}},
        "Rows with a missing value of race are reported as a separate Unknown/missing group and "
        "are not excluded.",
    ),
    (
        "ref_std_comparator",
        "REF_STD_TYPE_NOTE",
        "base",
        {"text": {"ref_std_phrase": "comparator"}},
        "The labels derive from a comparator rather than a reference standard; agreement is "
        "therefore reported as positive and negative percent agreement, not sensitivity and "
        "specificity.",
    ),
    (
        "ref_std_reference",
        "REF_STD_TYPE_NOTE",
        "base",
        {"text": {"ref_std_phrase": "reference", "description_ref": "adjudicated histopathology"}},
        "Labels derive from the declared reference standard (adjudicated histopathology).",
    ),
    (
        "rater_cols",
        "RATER_COLS_NOTE",
        "base",
        {"text": {"k": "2"}},
        "2 rater columns were present; they were not analysed in this version and were not used "
        "to construct the label.",
    ),
    (
        "overall",
        "OVERALL_ESTIMATE",
        "base",
        {"metric_id": "sensitivity", "numbers": {"value": PROP}, "text": {"op_id": "op1"}},
        "Sensitivity at operating point op1 was 81/263 (30.8%), 95% CI 25.5% to 36.6% (Wilson "
        "score, no continuity correction).",
    ),
    (
        "overall_not_estimable",
        "OVERALL_ESTIMATE",
        "not_estimable",
        {
            "metric_id": "f1",
            "status": "not_assessable",
            "numbers": {"value": _ne("analytic_ci_unavailable")},
            "text": {"op_id": "op1"},
        },
        "F1 at operating point op1 was not estimable with an interval (analytic_ci_unavailable).",
    ),
    (
        "overall_not_a_proportion",
        "OVERALL_ESTIMATE",
        "not_a_proportion",
        {"metric_id": "lr_pos", "numbers": {"value": LR}, "text": {"op_id": "op1"}},
        "LR+ at operating point op1 was 3.091, 95% CI 2.450 to 3.900 (delta method on the log "
        "scale).",
    ),
    (
        "indet_both_ways",
        "INDET_BOTH_WAYS",
        "base",
        {"metric_id": "sensitivity", "numbers": {"pos": PROP, "neg": PROP2}},
        "With indeterminate results allocated as positive, sensitivity was 30.8% [25.5, 36.6]; "
        "allocated as negative, 27.4% [22.3, 33.1].",
    ),
    (
        "ppv_at_prevalence",
        "PPV_AT_PREVALENCE",
        "base",
        {
            "numbers": {"ppv": PPV_PI, "npv": NPV_PI},
            "text": {"pi": 0.05, "label": "intended-use, primary care", "source": "registry 2024"},
        },
        "At the declared intended-use prevalence of 0.05 (intended-use, primary care; source "
        "registry 2024), PPV was 12.3% [9.9, 15.3] and NPV 98.8% [98.0, 99.2].",
    ),
    (
        "prev_mismatch",
        "PREV_MISMATCH_FLAG",
        "base",
        {"numbers": {"prevalence": PROP}, "text": {"pi": 0.05, "tol": 0.1}},
        f"Observed prevalence {PROP_TXT} differs from the declared intended-use prevalence 0.05 "
        "by more than 0.1; predictive values are reported at both.",
    ),
    (
        "auroc_iid_wald",
        "AUROC_ESTIMATE",
        "base",
        {"metric_id": "auroc", "numbers": {"value": AUROC}, "text": {"method_phrase": "iid_wald"}},
        "AUROC was 0.795 [0.742, 0.841] (DeLong, Wald interval).",
    ),
    (
        "auroc_iid",
        "AUROC_ESTIMATE",
        "base",
        {"metric_id": "auroc", "numbers": {"value": AUROC}, "text": {"method_phrase": "iid"}},
        "AUROC was 0.795 [0.742, 0.841] (DeLong, logit-transformed interval).",
    ),
    (
        "auroc_clustered",
        "AUROC_ESTIMATE",
        "base",
        {
            "metric_id": "auroc",
            "numbers": {"value": AUROC},
            "text": {"method_phrase": "clustered", "n_cases": "60"},
        },
        "AUROC was 0.795 [0.742, 0.841] (cluster bootstrap over 60 cases; DeLong not used "
        "because rows are clustered).",
    ),
    (
        "auroc_not_estimable",
        "AUROC_ESTIMATE",
        "not_estimable",
        {
            "metric_id": "auroc",
            "status": "not_assessable",
            "numbers": {"value": _ne("single_class")},
        },
        "AUROC was not estimable with an interval (single_class).",
    ),
    (
        "calib_hierarchy",
        "CALIB_HIERARCHY",
        "base",
        {
            "metric_id": "oe",
            "numbers": {
                "oe": OE,
                "slope": SLOPE,
                "intercept": INTERCEPT,
                "brier": BRIER,
                "brier_ref": BRIER_REF,
                "ipa": IPA,
            },
        },
        "The observed-to-expected ratio was 1.144 [0.988, 1.326]; calibration slope 1.195 "
        "[0.902, 1.488]; intercept 0.500 [0.102, 0.899]; Brier 0.159 [0.140, 0.181] (reference "
        "n.e. (fixed_by_outcome_stratification); IPA 0.339 [−0.029, 0.615]ᵇᶜ).",
    ),
    (
        "calib_curve_flag",
        "CALIB_CURVE_FLAG",
        "base",
        {},
        "A flexible calibration curve is not shown because events or non-events are below the "
        "ProofPack convention of two hundred each (after Van Calster and colleagues, 2019); the "
        "decile table is reported instead.",
    ),
    (
        "calib_na",
        "CALIB_NA",
        "base",
        {"text": {"score_type": "logit"}},
        "Calibration statistics are not computed because the score was declared as logit, not a "
        "probability.",
    ),
    (
        "subgroup_table_intro",
        "SUBGROUP_TABLE_INTRO",
        "base",
        {
            "text": {
                "ref": "T1-10",
                "metric_list": "sensitivity and specificity",
                "attribute": "sex",
                "op_id": "op1",
                "reference_level": "M",
                "pre_spec_phrase": "pre-specified in SAP v2",
            }
        },
        "Table T1-10 reports sensitivity and specificity by sex at operating point op1; the "
        "reference level is M (pre-specified in SAP v2).",
    ),
    (
        "subgroup_with_diff",
        "SUBGROUP_ESTIMATE_WITH_DIFF",
        "base",
        {
            "metric_id": "sensitivity",
            "numbers": {"value": PROP, "diff": DIFF},
            "text": {"attribute": "sex", "level": "F", "reference_level": "M"},
        },
        f"For sex = F, sensitivity was {PROP_TXT}, a difference of −3.2 percentage points "
        "[−6.1, −0.4] versus M.",
    ),
    (
        "subgroup_diff_not_estimable",
        "SUBGROUP_ESTIMATE_WITH_DIFF",
        "difference_not_estimable",
        {
            "metric_id": "sensitivity",
            "status": "not_assessable",
            "numbers": {"value": PROP, "diff": _ne("cases_span_both_groups")},
            "text": {"attribute": "sex", "level": "F", "reference_level": "M"},
        },
        f"For sex = F, sensitivity was {PROP_TXT}; the difference versus M was not estimable "
        "with an interval (cases_span_both_groups).",
    ),
    (
        "subgroup_estimate",
        "SUBGROUP_ESTIMATE",
        "base",
        {
            "metric_id": "sensitivity",
            "numbers": {"value": PROP_TIER},
            "text": {"attribute": "site", "level": "S3"},
        },
        "For site = S3, sensitivity was 81/263 (30.8%ᶜ) [25.5, 36.6].",
    ),
    (
        "subgroup_not_estimable",
        "SUBGROUP_ESTIMATE",
        "not_estimable",
        {
            "metric_id": "specificity",
            "status": "not_assessable",
            "numbers": {"value": _ne("zero_denominator")},
            "text": {"attribute": "site", "level": "S3"},
        },
        "For site = S3, specificity was not estimable with an interval (zero_denominator).",
    ),
    (
        "prespec_prespecified",
        "PRESPEC_FLAG",
        "base",
        {"text": {"pre_spec_phrase": "prespecified", "source": "SAP v2"}},
        "This subgroup analysis was pre-specified (SAP v2).",
    ),
    (
        "prespec_exploratory",
        "PRESPEC_FLAG",
        "base",
        {"text": {"pre_spec_phrase": "exploratory"}},
        "This subgroup analysis was not pre-specified and is reported as exploratory.",
    ),
    (
        "low_n",
        "LOW_N_CAVEAT",
        "base",
        {"text": {"level_list": "site = S3 and site = S4", "tier_threshold": "thirty"}},
        "site = S3 and site = S4 contain fewer than thirty rows or events; estimates for these "
        "groups are shown for transparency and carry very low precision.",
    ),
    (
        "hetero",
        "HETERO_EXPLORATORY_FOOTNOTE",
        "base",
        {"numbers": {"p_raw": 0.66114, "p_holm": 0.0004}, "text": {"attribute": "age"}},
        "An exploratory test of homogeneity across levels of age gave p = 0.661 (Holm-adjusted "
        "<0.001); no conclusion about subgroup consistency is drawn from this test.",
    ),
    (
        "criterion_met",
        "CRITERION_STATUS",
        "base",
        {
            "metric_id": "sensitivity",
            "status": "met",
            "numbers": {"value": PROP},
            "text": {**CRIT, "value": "0.2", "status_word": "met", "reason_clause": ""},
        },
        "Criterion C1 (sensitivity, overall, op1, CI lower bound >= 0.2; Dr A. B., 2026-03-01): "
        "observed 30.8% [25.5, 36.6] - criterion met.",
    ),
    (
        "criterion_not_met",
        "CRITERION_STATUS",
        "base",
        {
            "metric_id": "sensitivity",
            "status": "not_met",
            "numbers": {"value": PROP},
            "text": {**CRIT, "value": "0.85", "status_word": "not_met", "reason_clause": ""},
        },
        "Criterion C1 (sensitivity, overall, op1, CI lower bound >= 0.85; Dr A. B., "
        "2026-03-01): observed 30.8% [25.5, 36.6] - criterion not met.",
    ),
    (
        "criterion_not_assessable",
        "CRITERION_STATUS",
        "not_assessable",
        {
            "metric_id": "sensitivity",
            "status": "not_assessable",
            "text": {
                **CRIT,
                "value": "0.85",
                "status_word": "not_assessable",
                "reason_clause": " (requires_compare)",
            },
        },
        "Criterion C1 (sensitivity, overall, op1, CI lower bound >= 0.85; Dr A. B., "
        "2026-03-01): not assessable (requires_compare).",
    ),
    (
        "criterion_not_met_record",
        "CRITERION_NOT_MET_RECORD",
        "base",
        {
            "metric_id": "sensitivity",
            "status": "not_met",
            "numbers": {"value": PROP},
            "text": {
                "criterion_id": "C2",
                "scope": "overall, op1",
                "comparator": ">=",
                "value": "0.85",
            },
        },
        "Record of criterion not met: C2, overall, op1, observed 30.8% [25.5, 36.6] against >= "
        "0.85.",
    ),
    (
        "attainability_false",
        "ATTAINABILITY_NOTE",
        "base",
        {
            "metric_id": "sensitivity",
            "numbers": {"n": 30, "max_lower_bound_at_n": 0.88649},
            "text": {"criterion_id": "C4", "attainable_phrase": "false"},
        },
        "At the observed n of 30, the largest lower confidence bound attainable for sensitivity "
        "is 0.886; criterion C4 is not attainable at this sample size.",
    ),
    (
        "attainability_true",
        "ATTAINABILITY_NOTE",
        "base",
        {
            "metric_id": "specificity",
            "numbers": {"n": 128, "max_lower_bound_at_n": 0.97086},
            "text": {"criterion_id": "C5", "attainable_phrase": "true"},
        },
        "At the observed n of 128, the largest lower confidence bound attainable for specificity "
        "is 0.971; criterion C5 is attainable at this sample size.",
    ),
    (
        "fairness_intro",
        "FAIRNESS_INTRO",
        "base",
        {
            "text": {
                "criterion_of_interest": "tpr_gap",
                "attribute": "sex",
                "author": "Dr F.",
                "date": "2026-02-02",
            }
        },
        "The declared fairness criterion of interest is tpr_gap for sex (Dr F., 2026-02-02); all "
        "other gap statistics are descriptive and are not targets.",
    ),
    (
        "fairness_gap",
        "FAIRNESS_GAP",
        "base",
        {
            "metric_id": "tpr_gap",
            "numbers": {"tpr_gap": TPR, "fpr_gap": FPR, "ppv_gap": PPVG, "auroc_gap": DIFF3},
            "text": {"level": "F", "reference_level": "M"},
        },
        "For F versus M: TPR gap +7.0 [−7.9, +21.7], FPR gap −4.8 [−14.8, +5.4], PPV gap +8.9 "
        "[−6.2, +23.3], AUROC gap −0.012 [−0.041, +0.017].",
    ),
    (
        "selection_rate",
        "SELECTION_RATE_LABEL",
        "base",
        {},
        "Selection-rate (demographic parity) differences are reported for completeness and are "
        "not a target for diagnostic devices.",
    ),
    (
        "impossibility",
        "IMPOSSIBILITY_STATEMENT",
        "base",
        {},
        "Equalised error rates and calibration by group cannot in general hold simultaneously "
        "when base rates differ between groups; see the Methods Appendix for the statement and "
        "citations.",
    ),
    (
        "loso",
        "LOSO_RESULT",
        "base",
        {
            "metric_id": "sensitivity",
            "numbers": {"value": PROP, "diff": DIFF},
            "text": {"site": "S2"},
        },
        "Excluding S2, sensitivity was 30.8% [25.5, 36.6] (change −3.2 percentage points).",
    ),
    (
        "thresh_sens",
        "THRESH_SENS",
        "base",
        {
            "numbers": {"se_minus": PROP, "se_plus": PROP2, "sp_minus": PROP, "sp_plus": PROP2},
            "text": {"thr_minus": 0.45, "thr_plus": 0.55},
        },
        f"At thresholds of 0.45 and 0.55, sensitivity was {PROP_TXT} and {PROP2_TXT} and "
        f"specificity {PROP_TXT} and {PROP2_TXT}; this is a sensitivity analysis, not a "
        "criterion.",
    ),
    (
        "missingness",
        "MISSINGNESS_SENS",
        "base",
        {"metric_id": "sensitivity", "numbers": {"complete": PROP, "missing": PROP2}},
        "Sensitivity was 30.8% [25.5, 36.6] in rows with complete attributes and 27.4% [22.3, "
        "33.1] in rows with any missing attribute.",
    ),
    (
        "duplicates",
        "DUPLICATES_NOTE",
        "base",
        {"numbers": {"n_dup": 4}, "text": {"conflict_clause": ""}},
        "4 duplicate case identifiers were detected.",
    ),
    (
        "monitoring_pointer",
        "MONITORING_POINTER",
        "base",
        {},
        "Post-market performance monitoring analyses are produced separately (T3) and are not "
        "part of this attachment set.",
    ),
    (
        "public_summary",
        "PUBLIC_SUMMARY_NUMBERS",
        "base",
        {"text": {"metric_list_with_ci": f"sensitivity {PROP_TXT}"}},
        f"Plain-language performance figures for the submitter's own summary: sensitivity "
        f"{PROP_TXT}.",
    ),
    (
        "model_card_limits",
        "MODEL_CARD_LIMITS",
        "base",
        {"text": {"limit_list": "fewer than three sites"}},
        "Limitations evident from the data: fewer than three sites.",
    ),
    (
        "paired_diff",
        "PAIRED_DIFF",
        "base",
        {
            "metric_id": "sensitivity",
            "numbers": {"diff": DIFF_PAIRED, "n_pairs": 250},
            "text": {"prior": "1.2", "new": "1.3"},
        },
        "Sensitivity changed by −3.2 percentage points [−6.1, −0.4] from version 1.2 to 1.3 on "
        "250 paired cases (Newcombe paired).",
    ),
    (
        "mcnemar",
        "MCNEMAR_RESULT",
        "base",
        {"numbers": {"b": 10, "c": 2, "p": 0.03857}, "text": {"method": "exact"}},
        "10 cases were correct under the prior version only and 2 under the new version only "
        "(McNemar exact, p = 0.039).",
    ),
    (
        "unpaired",
        "UNPAIRED_LABEL",
        "base",
        {},
        "Versions were evaluated on different cases; the comparison is not like-for-like and "
        "uses unpaired methods.",
    ),
    (
        "ledger_statement",
        "LEDGER_STATEMENT",
        "base",
        {"numbers": {"n_prior": 3, "limit": 5}},
        "This test set has been used in 3 prior version comparisons recorded in the local "
        "ledger; the manufacturer's declared limit is 5.",
    ),
    (
        "ledger_warning",
        "LEDGER_WARNING",
        "base",
        {},
        "The declared limit on comparisons against this test set has been reached or exceeded.",
    ),
    (
        "impact",
        "IMPACT_INPUTS_NOTE",
        "base",
        {},
        "The quantitative differences above are inputs to the manufacturer's impact "
        "assessment; no benefit-risk conclusion is drawn here.",
    ),
    (
        "monitoring_rule",
        "MONITORING_RULE_ECHO",
        "base",
        {
            "text": {
                "rule_text": "two consecutive quarters below 0.80",
                "tiers": "0.1 / 0.25",
                **AUTHOR,
            }
        },
        "The control rule applied is: two consecutive quarters below 0.80 (Dr A. B., "
        "2026-03-01); effect-size tiers for PSI: 0.1 / 0.25.",
    ),
    (
        "psi",
        "PSI_RESULT",
        "base",
        {
            "numbers": {"psi": PSI, "crit": 0.04411, "B": 10, "n": 500, "m": 500, "p": 0.00212},
            "text": {"variable": "score", "alpha": 0.05, "tier": "moderate"},
        },
        "PSI for score was 0.058 [0.031, 0.089] against a critical value of 0.044 at α = 0.05 "
        "for 10 bins with n = 500 and m = 500 (p = 0.002); tier: moderate.",
    ),
    (
        "ks",
        "KS_RESULT",
        "base",
        {"numbers": {"d": KS, "p": 0.00002}, "text": {"variable": "age"}},
        "Kolmogorov-Smirnov D for age was 0.140 [0.082, 0.198] (p = <0.001).",
    ),
    (
        "prevalence_shift",
        "PREVALENCE_SHIFT",
        "base",
        {"numbers": {"ref": PROP, "cur": PROP2}},
        "Observed prevalence moved from 30.8% [25.5, 36.6] to 27.4% [22.3, 33.1].",
    ),
    *[
        (
            f"period_{tid.lower()}",
            tid,
            "base",
            {"metric_id": "sensitivity", "numbers": {"value": PROP}, "text": {"period": "2026-Q1"}},
            f"In 2026-Q1, sensitivity was {PROP_TXT}.",
        )
        for tid in (
            "PERIOD_METRIC_ROW",
            "SUBGROUP_TREND_ROW",
            "AGREEMENT_RATE_ROW",
            "INDET_RATE_ROW",
            "ATTR_DRIFT_ROW",
        )
    ],
    (
        "control_triggered",
        "CONTROL_RULE_STATUS",
        "base",
        {"text": {"triggered_phrase": "triggered", "period": "2026-Q2"}},
        "The declared control rule was triggered in 2026-Q2.",
    ),
    (
        "control_not_triggered",
        "CONTROL_RULE_STATUS",
        "base",
        {"text": {"triggered_phrase": "not_triggered", "period": "2026-Q2"}},
        "The declared control rule was not triggered in 2026-Q2.",
    ),
    (
        "control_not_assessable",
        "CONTROL_RULE_STATUS",
        "base",
        {
            "text": {
                "triggered_phrase": "not_assessable",
                "reason": "no_rows_in_period",
                "period": "2026-Q2",
            }
        },
        "The declared control rule was not assessable (no_rows_in_period) in 2026-Q2.",
    ),
    (
        "summary_pointer",
        "SUMMARY_POINTER",
        "base",
        {},
        "Conclusions, corrective actions and risk analysis are the manufacturer's and are not "
        "drafted here.",
    ),
]


@pytest.mark.parametrize(
    ("template_id", "variant", "kwargs", "expected"),
    [c[1:] for c in CASES],
    ids=[c[0] for c in CASES],
)
def test_each_skeleton_renders_the_exact_sentence_from_literal_numbers(
    template_id, variant, kwargs, expected
):
    key = {k: kwargs.get(k) for k in ("metric_id", "subgroup_id", "comparator_id", "status")}
    assert lib.lookup(template_id, **key)[2] == variant
    assert sentences.render_text(template_id, **kwargs) == expected


def test_the_cases_cover_every_template_every_variant_and_every_phrase_key():
    covered = {(c[1], c[2]) for c in CASES}
    wanted = {(tid, v) for tid, v, _ in lib.all_skeletons() if not v.startswith("phrase:")}
    assert wanted - covered == set()
    assert {tid for tid, _ in covered} == set(lib.LIBRARY)
    assert len(lib.LIBRARY) == 56 and len(wanted) == 62
    # every phrase key is fed, except MODEL_CARD_LIMITS' limit_item list, which a caller
    # composes into limit_list (no v1 claim uses it: the model card is v1.1)
    for tid, t in lib.LIBRARY.items():
        for slot, table in (t.phrases or {}).items():
            if (tid, slot) == ("MODEL_CARD_LIMITS", "limit_item"):
                continue
            fed = {c[3].get("text", {}).get(slot) for c in CASES if c[1] == tid}
            if slot == "status_word":
                fed = {c[3].get("text", {}).get("status_word") for c in CASES if c[1] == tid}
            assert set(table) <= fed, (tid, slot, set(table) - fed)


def test_every_number_slot_binding_names_a_facet_and_matches_the_skeleton():
    for tid, bindings in lib.FACET_BINDINGS.items():
        occ = lib.occurrences(lib.LIBRARY[tid].skeleton)
        for slot, bs in bindings.items():
            assert occ.count(slot) == len(bs), (tid, slot)
            for b in bs:
                selector, dot, facet = b.partition(".")
                assert dot and selector and facet in lib.FACETS, (tid, b)
    for tid, variants in lib.VARIANTS.items():
        assert tid in lib.LIBRARY
        for v in variants:
            occ = lib.occurrences(v.skeleton)
            for slot, bs in v.facets.items():
                assert occ.count(slot) == len(bs), (tid, v.name, slot)
    # the method phrases cover the Number's method enum; the metric names the metric enum
    assert set(lib.METHOD_PHRASES) == set(METHODS)
    from proofpack.resources import load_json_schema

    metric_enum = load_json_schema("output_schema_v1.json")["$defs"]["metricId"]["enum"]
    used = set(metric_enum[: metric_enum.index("prevalence") + 1])
    assert used <= set(lib.METRIC_NAMES)


def test_a_typed_reason_number_prints_the_reason_and_no_digit_from_est():
    num = _ne("clustered_data_analytic_ci_invalid", est=0.7777, n=9, k=7)
    for status in (None, "not_assessable"):
        out = sentences.render_text(
            "OVERALL_ESTIMATE",
            metric_id="sensitivity",
            status=status,
            numbers={"value": num},
            text={"op_id": "op1"},
        )
        assert "clustered_data_analytic_ci_invalid" in out
        assert "77" not in out and "0.778" not in out and "7777" not in out, out
    for facet in ("est", "ci", "ci_lo", "ci_hi", "estci"):
        got = sentences.facet_text(num, facet, "proportion")
        assert not any(ch.isdigit() for ch in got), (facet, got)
    assert sentences.facet_text(num, "est", "proportion") == (
        "n.e. (clustered_data_analytic_ci_invalid)"
    )
    supp = _num(None, None, None, "none", suppressed=True)
    assert sentences.facet_text(supp, "est", "proportion") == "‡"
    assert sentences.facet_text(supp, "reason", "proportion") == "suppressed"


def _forbidden_words() -> set[str]:
    d4 = {
        "pass",
        "fail",
        "verdict",
        "unresolvable",
        "non-inferior",
        "consistent",
        "unbiased",
        "acceptable",
        "safe",
        "compliant",
        "approved",
    }
    return set(checker.VERDICT_WORDS) | set(checker.CERTIFICATION_WORDS) | d4


def test_the_forbidden_grep_over_every_skeleton_variant_and_phrase_is_zero():
    """The D4 section 1.2 grep and the checker's own word lists over the fixed text of
    every skeleton, variant and phrase. The status words are exempt only where the
    library prints them as a status: CRITERION_STATUS's ``status_word`` phrase map and
    CRITERION_NOT_MET_RECORD's fixed ``Record of criterion not met`` (T2 only, D4)."""
    forbidden = _forbidden_words()
    hits = []
    for tid, variant, text in lib.all_skeletons():
        fixed = "".join(lit for lit, _, _, _ in string.Formatter().parse(text))
        words = set(re.split(r"[^a-z-]+", fixed.lower())) - {""}
        words |= {p for w in words for p in w.split("-")}
        hit = words & forbidden
        if (tid, variant) in (
            ("CRITERION_STATUS", "phrase:status_word:met"),
            ("CRITERION_STATUS", "phrase:status_word:not_met"),
            ("CRITERION_NOT_MET_RECORD", "base"),
        ):
            hit -= {"met"}
        if (tid, variant) == (
            "THRESH_PROVENANCE",
            "phrase:provenance_phrase:derived_from_this_dataset",
        ):
            # D4 section 8 / v2 section 3 T1 mandate "optimistically biased" verbatim: the
            # checker lists "biased" for free_text; here it describes the estimate, and it
            # is the one exemption (recorded in the E9 build note)
            hit -= {"biased"}
        if "well-calibrated" in fixed.lower() or "guidance" in words or "cfr" in words:
            hit.add("phrase")
        if hit:
            hits.append((tid, variant, sorted(hit)))
    assert hits == []
    for phrase in list(lib.METHOD_PHRASES.values()) + list(lib.METRIC_NAMES.values()):
        assert not (set(re.split(r"[^a-z]+", phrase.lower())) & forbidden), phrase


# ------------------------------------------------------------------ by pointer facet


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    return assemble(cohort_with_a_thirty_row_site(), crit)


def test_a_family_claim_fills_each_slot_by_pointer_facet_not_by_position(document):
    """E8 carried rows 51 and 52: rule 8b accepts a subset of CALIB_HIERARCHY's pointers;
    the renderer fills each slot from the pointer whose path names that slot."""
    claim = next(c for c in document["claims"] if c["template_id"] == "CALIB_HIERARCHY")
    full = sentences.claim_sentence(claim, document)
    cal = document["calibration"]
    oe = fmt.estimate(cal["oe"]["number"], "three_dp")
    slope = fmt.estimate(cal["slope"]["number"], "three_dp")
    assert f"ratio was {oe} [" in full and f"calibration slope {slope} [" in full
    # drop the slope pointer: the slope slots print "not reported", the others keep
    # their own figures (by position the intercept would have moved into the slope slot)
    subset = dict(claim)
    subset["value_refs"] = [r for r in claim["value_refs"] if "/slope/" not in r]
    got = sentences.claim_sentence(subset, document)
    assert "calibration slope not reported [not reported]" in got
    intercept = fmt.estimate(cal["intercept"]["number"], "three_dp")
    assert f"intercept {intercept} [" in got and f"ratio was {oe} [" in got
    # reversed pointer order: the same sentence
    rev = dict(claim)
    rev["value_refs"] = list(reversed(claim["value_refs"]))
    assert sentences.claim_sentence(rev, document) == full


def test_every_claim_of_the_synthetic_run_renders_and_prints_its_own_numbers(document):
    assert checker.check(document["claims"], document).rejected == []
    assert len(document["claims"]) == 70
    for claim in document["claims"]:
        parts = sentences.claim_parts(claim, document)
        text = "".join(p.text for p in parts)
        assert "{" not in text and "not reported" not in text, text
        numbers = sentences.claim_numbers(claim, document)
        value = numbers.get("value")
        if claim["template_id"] in (
            "OVERALL_ESTIMATE",
            "SUBGROUP_ESTIMATE",
            "SUBGROUP_ESTIMATE_WITH_DIFF",
        ):
            kind = fmt.kind_for(claim["metric_id"])
            if value.get("not_estimable_reason") is not None:
                assert f"({value['not_estimable_reason']})" in text, text
            else:
                assert fmt.estimate(value, kind) in text, (claim["claim_id"], text)
        if (
            claim["template_id"] == "SUBGROUP_ESTIMATE_WITH_DIFF"
            and claim["relation"] != "not_assessable"
        ):
            d = numbers["diff"]
            assert fmt.interval(d, fmt.kind_for(claim["metric_id"], difference=True)) in text
        # the operating-point id and level labels are the customer's words (DEC-62)
        kinds = {p.text: p.kind for p in parts}
        if claim.get("operating_point") and claim["template_id"] == "OVERALL_ESTIMATE":
            assert kinds[claim["operating_point"]] == "customer"
        if claim.get("subgroup") and claim["template_id"].startswith("SUBGROUP"):
            assert kinds[claim["subgroup"]["level"]] == "customer"
        # the status word is a status part (printed inside .status), never fixed text
        if claim["template_id"] == "CRITERION_STATUS":
            status = [p for p in parts if p.kind == "status"]
            assert [p.text for p in status] == [
                {"met": "criterion met", "not_met": "criterion not met"}.get(
                    claim["status"], "not assessable"
                )
            ]


def test_the_auroc_sentence_names_the_method_the_number_carries(document):
    claim = next(c for c in document["claims"] if c["template_id"] == "AUROC_ESTIMATE")
    method = document["overall"]["threshold_free"]["auroc"]["method"]
    assert method == "delong_wald"
    assert sentences.claim_sentence(claim, document).endswith("(DeLong, Wald interval).")
    doc = copy.deepcopy(document)
    doc["overall"]["threshold_free"]["auroc"].update(
        {"method": "cluster_bootstrap_percentile", "n_cases": 37}
    )
    assert "cluster bootstrap over 37 cases" in sentences.claim_sentence(claim, doc)


def test_a_missing_text_slot_raises_and_an_unknown_template_raises():
    with pytest.raises(sentences.SentenceError, match="op_id"):
        sentences.render_text("OVERALL_ESTIMATE", metric_id="sensitivity", numbers={"value": PROP})
    with pytest.raises(sentences.SentenceError, match="unknown template"):
        sentences.render_text("NOPE")
    with pytest.raises(sentences.SentenceError, match="no phrase"):
        sentences.render_text("PRESPEC_FLAG", text={"pre_spec_phrase": "maybe"})
