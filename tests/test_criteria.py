"""Build day 7 (E7): the criteria engine and ``stats.attainability``.

Oracles: the attainability figure is recomputed here from the closed form
``n / (n + z^2)`` with ``z = 1.959963984540054`` typed as a literal (the 97.5th normal
percentile to 15 places; scipy's ``norm.ppf(0.975)``), never through ``wilson_bounds``;
the statuses are asserted against hand-built Numbers whose bounds are literals, and
against the assembled synthetic documents where the cohort is constructed so that one
site holds exactly 30 rows (F8: a criterion on an n = 30 cell is ``not_met`` with
``attainable_at_n: false``).
"""

from __future__ import annotations

import copy
import re
from typing import Any

import jsonschema
import pytest

from assembler import assemble
from conftest import make_cohort, make_criteria
from proofpack import criteria as crit_mod
from proofpack.errors import HaltError
from proofpack.io.declare import validate_dict
from proofpack.resources import load_json_schema
from proofpack.stats.attainability import PROPORTION_METRICS, attainable, max_lower_bound_at_n
from test_subgroups import VERDICT_WORDS, walk_keys_and_strings

pytestmark = pytest.mark.day7

Z_975 = 1.959963984540054


# ------------------------------------------------------------------------ attainability


@pytest.mark.parametrize("n", [30, 50, 200])
def test_max_lower_bound_at_n_is_n_over_n_plus_z_squared(n):
    hand = n / (n + Z_975 * Z_975)
    assert max_lower_bound_at_n(n) == pytest.approx(hand, abs=1e-12)


def test_the_hand_figures_at_30_50_200():
    # 30 / 33.841458820694124, 50 / 53.841458820694124, 200 / 203.841458820694124, each
    # re-derived by hand from the Wilson formula at p = 1 with z from
    # statistics.NormalDist().inv_cdf(0.975) (repair 1 of 21 September, RG-N3: the earlier
    # literal 0.928655 at n = 50 was mis-rounded and hidden by a 5e-6 tolerance)
    assert max_lower_bound_at_n(30) == pytest.approx(0.886486606826, abs=1e-9)
    assert max_lower_bound_at_n(50) == pytest.approx(0.928652400867, abs=1e-9)
    assert max_lower_bound_at_n(200) == pytest.approx(0.981154673623, abs=1e-9)


@pytest.mark.parametrize(
    "n, value, expected",
    [
        (30, 0.85, True),
        (30, 0.90, False),
        (30, 0.95, False),
        (50, 0.85, True),
        (50, 0.90, True),
        (50, 0.95, False),
        (200, 0.85, True),
        (200, 0.90, True),
        (200, 0.95, True),
    ],
)
def test_attainable_for_a_ge_criterion_at_30_50_200(n, value, expected):
    assert attainable(value, n, ">=") is expected
    # the strict form differs only at equality, which none of these hit
    assert attainable(value, n, ">") is expected


def test_attainable_at_exactly_the_bound_differs_between_ge_and_gt():
    """A value equal to the k = n bound is attainable under >= (the bound reaches it) and
    not under > (nothing exceeds the largest lower bound). The mutant that reads >= as >
    survived the first day-7 sweep on this; this is its observer."""
    bound = max_lower_bound_at_n(30)
    assert attainable(bound, 30, ">=") is True
    assert attainable(bound, 30, ">") is False


def test_attainable_is_none_for_le_and_lt_and_raises_on_an_unknown_comparator():
    assert attainable(0.9, 30, "<=") is None and attainable(0.9, 30, "<") is None
    with pytest.raises(ValueError):
        attainable(0.9, 30, "==")
    with pytest.raises(ValueError):
        max_lower_bound_at_n(0)


def test_the_bound_rises_with_n_and_never_reaches_one():
    prev = 0.0
    for n in (1, 2, 5, 10, 30, 100, 1000, 100000):
        b = max_lower_bound_at_n(n)
        assert prev < b < 1.0
        prev = b


def test_the_level_moves_the_bound_the_way_z_does():
    # 90 %: z = 1.6448536269514722
    z90 = 1.6448536269514722
    assert max_lower_bound_at_n(30, 0.90) == pytest.approx(30 / (30 + z90 * z90), abs=1e-12)


# ---------------------------------------------------------------- the comparison itself


def _num(est, lo, hi, n=100, method="wilson", reason=None):
    if reason is not None:
        return {
            "est": est,
            "ci_lo": None,
            "ci_hi": None,
            "ci_level": 0.95,
            "method": "none",
            "n": n,
            "flags": [],
            "suppressed": False,
            "not_estimable_reason": reason,
        }
    return {
        "est": est,
        "ci_lo": lo,
        "ci_hi": hi,
        "ci_level": 0.95,
        "method": method,
        "n": n,
        "flags": [],
        "suppressed": False,
        "not_estimable_reason": None,
    }


def _doc_with_overall(**numbers) -> dict[str, Any]:
    return {
        "overall": {"op1": dict(numbers), "threshold_free": {}},
        "subgroups": [],
        "fairness": None,
        "calibration": None,
        "calibration_suppressed_reason": None,
    }


def _decl_with(criteria: list[dict], **over) -> Any:
    return validate_dict(make_criteria(criteria=criteria, **over))


def _criterion(**kw) -> dict:
    base = {
        "id": "C",
        "metric": "sensitivity",
        "operating_point": "op1",
        "scope": "overall",
        "statistic": "ci_lower_bound",
        "comparator": ">=",
        "value": 0.85,
        "author": "A",
        "date": "2026-01-01",
        "justification": "j",
    }
    base.update(kw)
    return {k: v for k, v in base.items() if v is not None}  # None drops the key


@pytest.mark.parametrize(
    "statistic, comparator, value, expected",
    [
        # the Number is est 0.90, ci (0.82, 0.95): each statistic read literally
        ("ci_lower_bound", ">=", 0.82, "met"),
        ("ci_lower_bound", ">=", 0.8201, "not_met"),
        ("ci_lower_bound", ">", 0.82, "not_met"),
        ("ci_lower_bound", ">", 0.8199, "met"),
        ("point_estimate", ">=", 0.90, "met"),
        ("point_estimate", ">=", 0.9001, "not_met"),
        ("ci_upper_bound", "<=", 0.95, "met"),
        ("ci_upper_bound", "<=", 0.9499, "not_met"),
        ("ci_upper_bound", "<", 0.95, "not_met"),
        # the literal reading: a '<=' on the LOWER bound compares the lower bound, and
        # the engine does not swap to the upper end on the customer's behalf
        ("ci_lower_bound", "<=", 0.83, "met"),
        ("ci_lower_bound", "<=", 0.81, "not_met"),
        ("point_estimate", "<", 0.90, "not_met"),
    ],
)
def test_each_statistic_is_read_literally_and_the_comparator_applied_to_it(
    statistic, comparator, value, expected
):
    decl = _decl_with(
        [_criterion(statistic=statistic, comparator=comparator, value=value)],
        fairness=None,
    )
    doc = _doc_with_overall(sensitivity=_num(0.90, 0.82, 0.95, n=100))
    [row] = crit_mod.evaluate(decl, doc)
    assert row["status"] == expected and row["reason_code"] == "statistic_compared"
    read = {"ci_lower_bound": 0.82, "ci_upper_bound": 0.95, "point_estimate": 0.90}[statistic]
    assert row["compared_value"] == read
    assert row["metric_ref"] == "overall.op1.sensitivity"
    assert (row["statistic"], row["comparator"], row["value"]) == (statistic, comparator, value)


def test_attainability_fields_are_filled_for_a_lower_bound_proportion_criterion_only():
    decl = _decl_with(
        [
            _criterion(id="LB", value=0.95),
            _criterion(id="PT", statistic="point_estimate", value=0.95),
            _criterion(id="UB", statistic="ci_upper_bound", comparator="<=", value=0.95),
            _criterion(id="F1", metric="f1", value=0.5),
            _criterion(id="LE", comparator="<=", value=0.95),
        ],
        fairness=None,
    )
    doc = _doc_with_overall(
        sensitivity=_num(0.90, 0.82, 0.95, n=30), f1=_num(0.8, 0.7, 0.9, n=30, method="wilson")
    )
    rows = {r["criterion_id"]: r for r in crit_mod.evaluate(decl, doc)}
    lb = rows["LB"]
    assert lb["max_lower_bound_at_n"] == pytest.approx(30 / (30 + Z_975**2))
    assert lb["attainable_at_n"] is False and lb["status"] == "not_met" and lb["n"] == 30
    for cid in ("PT", "UB", "F1"):
        assert rows[cid]["attainable_at_n"] is None and rows[cid]["max_lower_bound_at_n"] is None
        # lens 3 of 21 September (regression N2): the docstring in stats/attainability.py cites
        # this test for "detail has no attainability key" on these three; assert it here
        assert not any(k.startswith("attainability") for k in rows[cid].get("detail") or {}), cid
    # '<=' on the lower bound: the figure is reported, the question does not arise
    assert rows["LE"]["max_lower_bound_at_n"] is not None and rows["LE"]["attainable_at_n"] is None
    assert "f1" not in PROPORTION_METRICS and "sensitivity" in PROPORTION_METRICS


@pytest.mark.parametrize(
    "statistic, comparator, value",
    [
        ("ci_lower_bound", ">=", 0.0),  # any bound at all
        ("point_estimate", ">=", 0.95),  # est 0.90 sits below: was not_met at ab729d3
        ("point_estimate", ">=", 0.5),  # est 0.90 sits above: was met at ab729d3
        ("ci_upper_bound", "<=", 1.0),
    ],
)
def test_a_number_with_method_none_is_not_assessable_under_each_of_the_three_statistics(
    statistic, comparator, value
):
    """Repair 1 of 21 September (lens 1 B1). The Number is est 0.90, ci (None, None),
    method none, not_estimable_reason single_class, n 100. At ab729d3 the two
    point_estimate rows read est and came back not_met (>= 0.95) and met (>= 0.5); the
    row is now routed on the method before any statistic is read."""
    decl = _decl_with(
        [_criterion(statistic=statistic, comparator=comparator, value=value)], fairness=None
    )
    doc = _doc_with_overall(sensitivity=_num(0.90, None, None, n=100, reason="single_class"))
    [row] = crit_mod.evaluate(decl, doc)
    assert row["status"] == "not_assessable" and row["reason_code"] == "no_interval"
    assert row["detail"]["not_estimable_reason"] == "single_class"
    assert row["compared_value"] is None and row["method"] == "none"
    assert row["attainable_at_n"] is None and row["max_lower_bound_at_n"] is None
    if statistic == "ci_lower_bound":
        # a proportion under ci_lower_bound, but the method is none, not wilson (B2's rule)
        assert row["detail"]["attainability_not_computed"] == "method_not_wilson"
    else:
        assert "attainability_not_computed" not in row["detail"]


@pytest.mark.parametrize(
    "n, reason",
    [
        (0, "zero_denominator"),  # lens 2 of 21 September FA-N1 / RG-N1: the literal input
        (None, "insufficient_positives"),
    ],
)
def test_a_method_none_number_at_n_zero_or_n_null_is_annotated_method_not_wilson(n, reason):
    """Repair 2 of 21 September (lens 2 FA-N1 = RG-N1). At 02d00c5 the annotation branch
    sat under `n > 0`, so this Number (est None, ci (None, None), method none, n 0,
    zero_denominator) under sensitivity ci_lower_bound >= 0.9 came back with detail
    {'not_estimable_reason': 'zero_denominator'} and no attainability_not_computed key,
    while the docstrings said 'on any other method ... method_not_wilson'. The status was
    and is not_assessable / no_interval. A Wilson Number under ci_upper_bound and
    point_estimate carries detail {} and both fields null (the second half)."""
    decl = _decl_with([_criterion(id="se", value=0.9)], fairness=None)
    doc = _doc_with_overall(sensitivity=_num(None, None, None, n=n, reason=reason))
    [row] = crit_mod.evaluate(decl, doc)
    assert (row["status"], row["reason_code"], row["n"]) == ("not_assessable", "no_interval", n)
    assert row["method"] == "none" and row["compared_value"] is None
    assert row["attainable_at_n"] is None and row["max_lower_bound_at_n"] is None
    assert row["detail"] == {
        "not_estimable_reason": reason,
        "attainability_not_computed": "method_not_wilson",
    }
    wilson = _num(1.0, 0.8864866068260313, 1.0, n=30)
    other = (("ci_upper_bound", "<=", 1.0), ("point_estimate", ">=", 0.9))
    for statistic, comparator, value in other:
        decl = _decl_with(
            [
                _criterion(
                    id="sp",
                    metric="specificity",
                    statistic=statistic,
                    comparator=comparator,
                    value=value,
                )
            ],
            fairness=None,
        )
        [row] = crit_mod.evaluate(decl, _doc_with_overall(specificity=wilson))
        assert (row["status"], row["method"]) == ("met", "wilson"), statistic
        assert row["attainable_at_n"] is None and row["max_lower_bound_at_n"] is None
        assert row["detail"] == {}, statistic


CLUSTER_CELL = {
    # the S3 specificity cell of the B2 construction as measured at ab729d3 through
    # proofpack run: 29 of 30 negatives right, 15 two-row cases, B 200, seed 20240101
    "est": 0.9666666666666667,
    "ci_lo": 0.9,
    "ci_hi": 1.0,
    "ci_level": 0.95,
    "method": "cluster_bootstrap_percentile",
    "n": 30,
    "k": 29,
    "n_cases": 15,
    "flags": ["wilson_refused_clustered", "very_low_precision"],
    "suppressed": False,
    "not_estimable_reason": None,
}


def test_a_cluster_bootstrap_cell_gets_no_attainability_flag():
    """Repair 1 of 21 September (lens 1 B2). ci_lo 0.9 on this cell exceeds the Wilson
    k = n figure at n = 30 (0.886486606826), so at ab729d3 the row was met with
    attainable_at_n False and max_lower_bound_at_n 0.8864866068260313 beside it. The
    figure is filled on method wilson only; here both are null and detail says why."""
    decl = _decl_with(
        [_criterion(id="sp", metric="specificity", value=0.89)],
        fairness=None,
    )
    doc = _doc_with_overall(specificity=dict(CLUSTER_CELL))
    [row] = crit_mod.evaluate(decl, doc)
    assert (row["status"], row["compared_value"], row["n"]) == ("met", 0.9, 30)
    assert row["method"] == "cluster_bootstrap_percentile"
    assert row["attainable_at_n"] is None and row["max_lower_bound_at_n"] is None
    assert row["detail"] == {"attainability_not_computed": "method_not_wilson"}
    # a Wilson Number at k = n = 30: est 1.0, ci_lo the k = n figure itself (measured
    # 0.8864866068260313). The figure is filled; against 0.89 the row is not_met with
    # attainable_at_n False, against 0.85 met with attainable_at_n True
    wilson = dict(CLUSTER_CELL, method="wilson", flags=[], est=1.0, ci_lo=0.8864866068260313, k=30)
    del wilson["n_cases"]
    [row] = crit_mod.evaluate(decl, _doc_with_overall(specificity=wilson))
    assert (row["status"], row["attainable_at_n"]) == ("not_met", False)
    assert row["max_lower_bound_at_n"] == pytest.approx(0.886486606826, abs=1e-9)
    assert row["detail"] == {}
    decl = _decl_with([_criterion(id="sp", metric="specificity", value=0.85)], fairness=None)
    [row] = crit_mod.evaluate(decl, _doc_with_overall(specificity=wilson))
    assert (row["status"], row["attainable_at_n"]) == ("met", True)
    assert row["compared_value"] == 0.8864866068260313 and row["detail"] == {}


def assert_no_met_row_is_marked_unattainable(rows: list[dict]) -> None:
    """Over the rows given: no row reads status met beside attainable_at_n False, and a
    filled attainability field sits on a method wilson row only."""
    assert rows
    for row in rows:
        assert not (row["status"] == "met" and row["attainable_at_n"] is False), row
        if row["attainable_at_n"] is not None or row["max_lower_bound_at_n"] is not None:
            assert row["method"] == "wilson", row  # criteria.ATTAINABILITY_METHOD


def test_a_suppressed_number_is_not_assessable():
    decl = _decl_with([_criterion(statistic="point_estimate", value=0.0)], fairness=None)
    num = _num(None, None, None, n=100, reason="single_class")
    num.update({"suppressed": True, "not_estimable_reason": None})
    [row] = crit_mod.evaluate(decl, _doc_with_overall(sensitivity=num))
    assert (row["status"], row["reason_code"]) == ("not_assessable", "suppressed")


def test_every_reason_code_is_in_the_schema_enum_and_the_three_statuses_are_the_schema_s():
    schema = load_json_schema("output_schema_v1.json")["$defs"]["criterionResult"]
    assert set(schema["properties"]["reason_code"]["enum"]) == set(crit_mod.REASON_CODES)
    assert tuple(schema["properties"]["status"]["enum"]) == crit_mod.STATUSES
    assert set(schema["properties"]["statistic"]["enum"]) == set(crit_mod.STATISTICS)
    assert set(schema["properties"]["comparator"]["enum"]) == set(crit_mod.COMPARATORS)
    crit_schema = load_json_schema("criteria_schema.json")
    props = crit_schema["$defs"]["criterion"]["allOf"][1]["properties"]
    assert set(props["statistic"]["enum"]) == set(crit_mod.STATISTICS)
    assert set(props["comparator"]["enum"]) == set(crit_mod.COMPARATORS)
    assert "value" in crit_schema["$defs"]["criterion"]["allOf"][1]["required"]
    # no "default" keyword anywhere in the criteria schema: the engine supplies none

    def keys(node):
        if isinstance(node, dict):
            for k, v in node.items():
                yield k
                yield from keys(v)
        elif isinstance(node, list):
            for v in node:
                yield from keys(v)

    assert "default" not in set(keys(crit_schema))


def test_no_reason_code_or_status_key_carries_a_verdict_word_outside_the_three_statuses():
    def flagged(token):
        return bool(set(re.split(r"[^a-z]+", token.lower())) & VERDICT_WORDS)

    for code in crit_mod.REASON_CODES:
        assert not flagged(code), code


# ------------------------------------------------------------- declaration-time gates


def test_a_threshold_free_metric_with_an_operating_point_is_h09():
    with pytest.raises(HaltError) as ei:
        _decl_with([_criterion(metric="auroc", operating_point="op1")])
    assert ei.value.code == "H09" and ei.value.detail["field"] == "operating_point"
    assert ei.value.detail["metric"] == "auroc"


def test_a_threshold_metric_without_an_operating_point_is_h09():
    with pytest.raises(HaltError) as ei:
        _decl_with([_criterion(operating_point=None)])
    assert ei.value.code == "H09" and ei.value.detail["field"] == "operating_point"


def test_a_fairness_bound_without_statistic_or_comparator_is_h08_naming_the_field():
    fair = {
        "criterion_of_interest": "tpr_gap",
        "attribute": "sex",
        "bound": 0.05,
        "author": "A",
        "date": "2026-01-01",
        "justification": "j",
    }
    with pytest.raises(HaltError) as ei:
        validate_dict(make_criteria(fairness=fair))
    assert ei.value.code == "H08" and ei.value.detail["missing"] == ["statistic", "comparator"]
    with pytest.raises(HaltError) as ei:
        validate_dict(make_criteria(fairness={**fair, "statistic": "point_estimate"}))
    assert ei.value.detail["missing"] == ["comparator"]
    # no bound: descriptive, neither field needed
    validate_dict(make_criteria(fairness={**fair, "bound": None}))
    # the schema says the same on its own (jsonschema, no engine code)
    schema = load_json_schema("criteria_schema.json")
    v = jsonschema.Draft202012Validator(schema)
    assert any(v.iter_errors(make_criteria(fairness=fair)))
    assert not any(
        v.iter_errors(
            make_criteria(fairness={**fair, "statistic": "point_estimate", "comparator": "<="})
        )
    )


def test_a_criterion_lacking_a_justification_is_h08():
    with pytest.raises(HaltError) as ei:
        _decl_with([_criterion(justification="")])
    assert ei.value.code == "H08" and ei.value.detail["missing"] == ["justification"]
    with pytest.raises(HaltError) as ei:
        c = _criterion()
        del c["value"]
        _decl_with([c])
    assert ei.value.code == "H08" and ei.value.detail["validator"] == "required"


def test_an_unknown_statistic_or_comparator_is_h08_from_the_schema():
    for field, bad in (("statistic", "ci_median"), ("comparator", "==")):
        with pytest.raises(HaltError) as ei:
            _decl_with([_criterion(**{field: bad})])
        assert ei.value.code == "H08" and ei.value.detail["validator"] == "enum"
        assert ei.value.detail["path"].endswith(field)


# ------------------------------------------------------------ the assembled documents


def cohort_with_a_thirty_row_site(n: int = 400) -> dict[str, list[Any]]:
    cols = make_cohort(n=n)
    cols["site"] = ["S3"] * 30 + ["S1", "S2"] * ((n - 30) // 2)
    return cols


FAIRNESS = {
    "criterion_of_interest": "tpr_gap",
    "attribute": "sex",
    "bound": 0.10,
    "statistic": "ci_upper_bound",
    "comparator": "<=",
    "author": "Dr F.",
    "date": "2026-02-02",
    "justification": "intended-use population",
}

CRITERIA = [
    _criterion(id="C_met", value=0.5),
    _criterion(
        id="C_n30",
        metric="accuracy",
        scope={"attribute": "site", "level": "S3"},
        value=0.90,
    ),
    _criterion(id="C_f1_site", metric="f1", scope={"attribute": "site", "level": "*"}, value=0.5),
    _criterion(id="C_auroc", metric="auroc", operating_point=None, value=0.5),
    _criterion(id="C_ece", metric="ece", operating_point=None, comparator="<=", value=0.1),
    _criterion(
        id="C_prior",
        type="paired_difference_vs_prior",
        value=-0.03,
    ),
]


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    return assemble(cohort_with_a_thirty_row_site(), crit)


def test_f8_a_criterion_on_a_thirty_row_cell_is_not_met_and_not_attainable(document):
    rows = [r for r in document["criteria_results"] if r["criterion_id"] == "C_n30"]
    [row] = rows
    assert row["n"] == 30 and row["status"] == "not_met"
    assert row["attainable_at_n"] is False
    assert row["max_lower_bound_at_n"] == pytest.approx(30 / (30 + Z_975**2))
    assert row["scope"] == {"attribute": "site", "level": "S3"}
    assert re.fullmatch(r"subgroups\[\d+\]\.metrics\.op1\.accuracy\.number", row["metric_ref"])
    # the row read is the one the ref points at, and the Number's own n is 30
    idx = int(re.search(r"\[(\d+)\]", row["metric_ref"]).group(1))
    cell = document["subgroups"][idx]["metrics"]["op1"]["accuracy"]
    assert cell["number"]["n"] == 30 and row["compared_value"] == cell["number"]["ci_lo"]


def test_no_row_of_the_synthetic_document_is_met_beside_attainable_at_n_false(document):
    assert_no_met_row_is_marked_unattainable(document["criteria_results"])
    n30 = next(r for r in document["criteria_results"] if r["criterion_id"] == "C_n30")
    assert n30["method"] == "wilson" and n30["detail"] == {}


def clustered_cohort_with_one_wrong_negative_in_s3() -> dict[str, list[Any]]:
    """Lens 1 B2's construction: 400 rows in 200 two-row cases, site S3 = rows 0-29, all
    negative, score 0.1 except row 0 at 0.9 (its case c000000's sibling row 1 is right)."""
    cols = make_cohort(n=400, with_case_id=True)
    cols["case_id"] = [f"c{i // 2:06d}" for i in range(400)]
    cols["site"] = ["S3"] * 30 + ["S1", "S2"] * 185
    for i in range(30):
        cols["y_true"][i] = "0"
        cols["score"][i] = 0.1
    cols["score"][0] = 0.9
    return cols


CLUSTERED_CRITERIA = [
    _criterion(
        id="sp_S3",
        metric="specificity",
        scope={"attribute": "site", "level": "S3"},
        value=0.89,
    ),
    _criterion(
        id="acc_S3",
        metric="accuracy",
        scope={"attribute": "site", "level": "S3"},
        value=0.89,
    ),
]


def test_b2_the_clustered_s3_cell_is_met_with_no_attainability_flag_in_the_assembled_document():
    """At ab729d3 both rows were met (ci_lo 0.9 >= 0.89) with attainable_at_n False and
    max_lower_bound_at_n 0.8864866068260313 (the Wilson k = n figure at n = 30)."""
    crit = make_criteria(
        clustering={"unit": "case_id", "declared_by": "test"},
        criteria=copy.deepcopy(CLUSTERED_CRITERIA),
        fairness=None,
    )
    doc = assemble(clustered_cohort_with_one_wrong_negative_in_s3(), crit)
    rows = {r["criterion_id"]: r for r in doc["criteria_results"]}
    assert set(rows) == {"sp_S3", "acc_S3"}
    for cid in ("sp_S3", "acc_S3"):
        row = rows[cid]
        assert (row["status"], row["compared_value"], row["n"]) == ("met", 0.9, 30), row
        assert row["method"] == "cluster_bootstrap_percentile"
        assert row["attainable_at_n"] is None and row["max_lower_bound_at_n"] is None
        assert row["detail"] == {"attainability_not_computed": "method_not_wilson"}
        idx = int(re.search(r"\[(\d+)\]", row["metric_ref"]).group(1))
        num = doc["subgroups"][idx]["metrics"]["op1"][row["metric"]]["number"]
        assert (num["ci_lo"], num["ci_hi"], num["n"], num["k"], num["n_cases"]) == (
            0.9,
            1.0,
            30,
            29,
            15,
        )
        assert num["est"] == pytest.approx(29 / 30, abs=1e-12)
        # the figure that sat beside status met at ab729d3
        assert max_lower_bound_at_n(30) == pytest.approx(0.8864866068260313, abs=1e-12)
        assert num["ci_lo"] > max_lower_bound_at_n(30)
    assert_no_met_row_is_marked_unattainable(doc["criteria_results"])


def test_the_three_statuses_and_their_reason_codes_on_the_synthetic_document(document):
    rows = {r["criterion_id"]: r for r in document["criteria_results"]}
    assert rows["C_met"]["status"] == "met" and rows["C_met"]["reason_code"] == "statistic_compared"
    assert rows["C_met"]["attainable_at_n"] is True
    assert rows["C_n30"]["status"] == "not_met"
    assert rows["C_auroc"]["status"] == "met"
    assert rows["C_auroc"]["metric_ref"] == "overall.threshold_free.auroc"
    assert rows["C_auroc"]["attainable_at_n"] is None  # not a proportion
    assert rows["C_ece"]["status"] == "not_assessable"
    assert rows["C_ece"]["reason_code"] == "metric_not_computed"
    assert rows["C_prior"]["status"] == "not_assessable"
    assert rows["C_prior"]["reason_code"] == "requires_compare"
    # '*' yields one row per tabulated level, all not_assessable for f1 at a subgroup scope
    f1 = [r for r in document["criteria_results"] if r["criterion_id"] == "C_f1_site"]
    assert sorted(r["scope"]["level"] for r in f1) == ["S1", "S2", "S3"]
    assert {r["reason_code"] for r in f1} == {"metric_not_computed_for_scope"}
    assert {r["status"] for r in f1} == {"not_assessable"}


def test_the_fairness_bound_gives_one_row_per_non_reference_level(document):
    rows = [r for r in document["criteria_results"] if r["criterion_id"] == "fairness:tpr_gap"]
    assert [r["scope"] for r in rows] == [{"attribute": "sex", "level": "F"}]
    [row] = rows
    gap = document["fairness"]["gaps"][0]["operating_points"]["op1"]["tpr_gap"]["number"]
    assert row["metric_ref"] == "fairness.gaps[0].operating_points.op1.tpr_gap.number"
    assert row["compared_value"] == gap["ci_hi"]
    assert row["status"] == ("met" if gap["ci_hi"] <= 0.10 else "not_met")
    assert (row["statistic"], row["comparator"], row["value"]) == ("ci_upper_bound", "<=", 0.10)


def test_a_fairness_block_without_a_bound_emits_no_row():
    crit = make_criteria(
        criteria=[_criterion(id="C1", value=0.5)], fairness={**FAIRNESS, "bound": None}
    )
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    assert [r["criterion_id"] for r in doc["criteria_results"]] == ["C1"]
    assert doc["fairness"]["bound"] is None


def test_calibration_by_group_bound_is_not_assessable_until_computed():
    fair = {**FAIRNESS, "criterion_of_interest": "calibration_by_group", "bound": 0.5}
    crit = make_criteria(criteria=[], fairness=fair)
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    rows = doc["criteria_results"]
    assert rows and {r["status"] for r in rows} == {"not_assessable"}
    assert {r["reason_code"] for r in rows} == {"not_estimable_this_run"}


def test_a_gap_criterion_on_an_attribute_that_is_not_the_fairness_one_is_not_assessable():
    crit = make_criteria(
        criteria=[_criterion(id="G", metric="tpr_gap", scope={"attribute": "site", "level": "S1"})],
        fairness=FAIRNESS,
    )
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    [row] = doc["criteria_results"][:1]
    assert row["reason_code"] == "gap_requires_fairness_attribute"
    # and on the reference level itself
    crit = make_criteria(
        criteria=[_criterion(id="G", metric="tpr_gap", scope={"attribute": "sex", "level": "M"})],
        fairness=FAIRNESS,
    )
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    assert doc["criteria_results"][0]["reason_code"] == "level_is_reference"


def test_calibration_criteria_read_the_calibration_cells_and_a_logit_score_is_not_assessable():
    crit = make_criteria(
        criteria=[
            _criterion(id="B", metric="brier", operating_point=None, comparator="<=", value=0.25),
            _criterion(
                id="S",
                metric="calibration_slope",
                operating_point=None,
                statistic="point_estimate",
                value=0.5,
            ),
        ],
        fairness=None,
    )
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    rows = {r["criterion_id"]: r for r in doc["criteria_results"]}
    assert rows["B"]["metric_ref"] == "calibration.brier.number"
    assert rows["B"]["compared_value"] == doc["calibration"]["brier"]["number"]["ci_lo"]
    assert rows["S"]["metric_ref"] == "calibration.slope.number"
    assert rows["S"]["compared_value"] == doc["calibration"]["slope"]["number"]["est"]
    crit["score"] = {"type": "logit", "orientation": "higher_is_positive"}
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    rows = {r["criterion_id"]: r for r in doc["criteria_results"]}
    assert rows["B"]["status"] == "not_assessable"
    assert rows["B"]["reason_code"] == "calibration_suppressed"
    assert rows["B"]["detail"]["reason"] == "score_not_probability"


def test_the_criteria_rows_validate_against_the_schema_and_each_carries_one_status(document):
    schema = load_json_schema("output_schema_v1.json")
    v = jsonschema.Draft202012Validator(schema)
    assert list(v.iter_errors(document)) == []
    for row in document["criteria_results"]:
        assert row["status"] in crit_mod.STATUSES
        assert (row["status"] == "not_assessable") == (row["compared_value"] is None)
    bad = copy.deepcopy(document)
    bad["criteria_results"][0]["status"] = "passed"
    assert any(v.iter_errors(bad))
    bad = copy.deepcopy(document)
    bad["criteria_results"][0]["reason_code"] = "vendor_default"
    assert any(v.iter_errors(bad))


def test_the_status_words_appear_only_under_criteria_results_and_no_verdict_word_anywhere(
    document,
):
    """The E7 twin of the day-5/6 greps: ``met`` / ``not_met`` / ``not_assessable`` occur
    under ``criteria_results`` and nowhere else; ``pass``, ``fail`` and ``verdict`` (and
    the rest of ``VERDICT_WORDS``) occur in no key or string of any block, including the
    criteria block's keys and reason codes."""

    def words(token):
        return set(re.split(r"[^a-z]+", token.lower()))

    status_words = {"met", "not_met", "not_assessable"}
    rest = {k: v for k, v in document.items() if k not in ("declarations", "criteria_results")}
    for token in walk_keys_and_strings(rest):
        assert not (words(token) & VERDICT_WORDS), token
        assert token not in status_words, token
    seen = set()
    for token in walk_keys_and_strings(document["criteria_results"]):
        if token in status_words:
            seen.add(token)
            continue
        assert not (words(token) & {"pass", "fail", "verdict", "passed", "failed"}), token
    assert seen == status_words
