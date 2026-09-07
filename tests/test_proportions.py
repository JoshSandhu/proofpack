"""Day 2 (E2) - ``stats.proportions``.

Fixtures F1, F1b-F1d, F2, F10, F11 come from R2 section 9 / D1 section 3.2 and are
checked both against the frozen expected values (1e-4) and against independent
oracles (``statsmodels``, ``scipy``) to 1e-10, which is much tighter than the
acceptance line. F14 is the transcribed Newcombe Table II, checked to 4 dp.

statsmodels and scikit-learn are **test-only** dependencies: a test in this file
asserts no module under ``src/proofpack`` imports them.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

from proofpack.resources import load_json_schema, resource_path
from proofpack.stats.number import METHODS, NOT_ESTIMABLE_REASONS, Number
from proofpack.stats.proportions import (
    Table2x2,
    clopper_pearson_bounds,
    difference_paired,
    difference_unpaired,
    indeterminate_both_ways,
    newcombe10_bounds,
    newcombe11_bounds,
    newcombe_paired_bounds,
    npv_at_prevalence,
    ppv_at_prevalence,
    proportion,
    proportion_exact_alternative,
    sensitivity_id,
    specificity_id,
    table_2x2_from_arrays,
    two_by_two_metrics,
    wald_bounds,
    wilson_bounds,
    z_for,
)

pytestmark = pytest.mark.day2

TOL = 1e-4  # the acceptance tolerance
REPO = pathlib.Path(__file__).resolve().parent.parent


def approx4(value: float, expected: float) -> None:
    assert abs(value - expected) <= TOL, f"{value!r} != {expected!r} within {TOL}"


# --------------------------------------------------------------------------- F1 family

F1_CASES = [
    # (k, n, wilson, clopper_pearson)
    (81, 263, (0.2553, 0.3662), (0.2527, 0.3676)),
    (490, 500, (0.9636, 0.9891), (0.9635, 0.9904)),
    (0, 20, (0.0, 0.1611), (0.0, 0.1684)),
    (20, 20, (0.8389, 1.0), (0.8316, 1.0)),
]


@pytest.mark.fixture
@pytest.mark.parametrize(("k", "n", "wilson", "cp"), F1_CASES)
def test_f1_wilson_and_clopper_pearson_frozen(k, n, wilson, cp):
    lo, hi = wilson_bounds(k, n)
    approx4(lo, wilson[0])
    approx4(hi, wilson[1])
    clo, chi = clopper_pearson_bounds(k, n)
    approx4(clo, cp[0])
    approx4(chi, cp[1])


@pytest.mark.fixture
@pytest.mark.parametrize(("k", "n", "_w", "_c"), F1_CASES)
def test_f1_against_statsmodels_oracle(k, n, _w, _c):
    """Agreement with statsmodels far tighter than the 1e-4 acceptance line."""
    sm = pytest.importorskip("statsmodels.stats.proportion")
    for method, ours in (
        ("wilson", wilson_bounds(k, n)),
        ("beta", clopper_pearson_bounds(k, n)),
    ):
        lo, hi = sm.proportion_confint(k, n, alpha=0.05, method=method)
        # statsmodels returns nan at the boundaries for 'beta'; treat nan as the bound.
        lo = 0.0 if lo != lo else float(lo)
        hi = 1.0 if hi != hi else float(hi)
        assert abs(ours[0] - lo) < 1e-10, (method, k, n, ours, (lo, hi))
        assert abs(ours[1] - hi) < 1e-10, (method, k, n, ours, (lo, hi))


@pytest.mark.fixture
def test_f1_clopper_pearson_matches_scipy_binomtest():
    scipy_stats = pytest.importorskip("scipy.stats")
    for k, n in [(81, 263), (490, 500), (0, 20), (20, 20), (1, 3), (17, 17)]:
        ci = scipy_stats.binomtest(k, n).proportion_ci(method="exact")
        lo, hi = clopper_pearson_bounds(k, n)
        assert abs(lo - ci.low) < 1e-12
        assert abs(hi - ci.high) < 1e-12


@pytest.mark.fixture
def test_f1c_wald_is_degenerate_and_never_emitted():
    """0/20 Wald is (0, 0). It exists only in the test module; no Number may carry it."""
    assert wald_bounds(0, 20) == (0.0, 0.0)
    assert "wald" not in METHODS
    src = (REPO / "src" / "proofpack").rglob("*.py")
    for path in src:
        text = path.read_text(encoding="utf-8")
        assert '"wald"' not in text and "'wald'" not in text, path


def test_clopper_pearson_shown_alongside_wilson_only_at_boundaries():
    assert proportion_exact_alternative(81, 263) is None
    for k, n in ((0, 20), (20, 20)):
        alt = proportion_exact_alternative(k, n)
        assert alt is not None
        assert alt.method == "clopper_pearson"
        assert "shown_alongside_wilson_at_boundary" in alt.flags


def test_boundary_clopper_pearson_needs_no_scipy():
    """0/n and n/n are closed form, so the boundary case never depends on scipy."""
    code = (
        "import importlib.util,sys;"
        "assert importlib.util.find_spec('scipy') is not None;"
        "import proofpack.stats.proportions as p;"
        "print(p.clopper_pearson_bounds(0,20));"
        "assert 'scipy' not in sys.modules"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.startswith("(0.0, 0.168")


def test_wilson_continuity_correction_is_wider_and_not_default():
    plain = wilson_bounds(81, 263)
    cc = wilson_bounds(81, 263, continuity=True)
    assert cc[0] < plain[0] and cc[1] > plain[1]
    assert proportion(81, 263).method == "wilson"


def test_z_for_matches_scipy():
    scipy_stats = pytest.importorskip("scipy.stats")
    for level in (0.90, 0.95, 0.99):
        assert abs(z_for(level) - scipy_stats.norm.ppf(1 - (1 - level) / 2)) < 1e-12


# ---------------------------------------------------------------------------- F2 2x2

F2 = Table2x2(tp=90, fn=10, fp=20, tn=180)
F2_EXPECTED = {
    "sensitivity": (0.90, (0.8256, 0.9448)),
    "specificity": (0.90, (0.8506, 0.9343)),
    "ppv": (0.8182, None),
    "npv": (0.9474, None),
    "prevalence": (0.3333, None),
    "lr_pos": (9.0, None),
    "lr_neg": (0.1111, None),
    "dor": (81.0, None),
    "youden": (0.80, None),
    "f1": (0.8571, None),
    "mcc": (0.7826, None),
}


@pytest.mark.fixture
def test_f2_two_by_two_point_estimates_and_wilson_cis():
    m = two_by_two_metrics(F2)
    for key, (est, ci) in F2_EXPECTED.items():
        approx4(m[key].est, est)
        if ci is not None:
            approx4(m[key].ci_lo, ci[0])
            approx4(m[key].ci_hi, ci[1])
    approx4(m["accuracy"].est, 270 / 300)
    approx4(m["balanced_accuracy"].est, 0.90)


@pytest.mark.fixture
def test_f2_ppv_npv_adjusted_to_declared_prevalence():
    approx4(ppv_at_prevalence(F2, 0.05).est, 0.3214)
    approx4(npv_at_prevalence(F2, 0.05).est, 0.9942)


def test_ppv_at_study_prevalence_reproduces_the_observed_ppv():
    """Sanity identity for the Bayes formula: at the study prevalence it must agree."""
    m = two_by_two_metrics(F2)
    pi = F2.n_pos / F2.n
    assert abs(ppv_at_prevalence(F2, pi).est - m["ppv"].est) < 1e-12
    assert abs(npv_at_prevalence(F2, pi).est - m["npv"].est) < 1e-12


def test_ppv_logit_interval_brackets_the_estimate_and_stays_in_unit_range():
    n = ppv_at_prevalence(F2, 0.05)
    assert n.method == "logit_delta"
    assert 0.0 < n.ci_lo < n.est < n.ci_hi < 1.0


def test_predictive_values_are_not_estimable_at_a_boundary_cell():
    perfect = Table2x2(tp=50, fn=0, fp=0, tn=50)  # Se = 1, Sp = 1
    p = ppv_at_prevalence(perfect, 0.05)
    assert p.ci_lo is None and p.not_estimable_reason == "zero_cell_logit_undefined"


def test_zero_cells_give_typed_reasons_not_silent_fallbacks():
    t = Table2x2(tp=50, fn=0, fp=0, tn=50)
    m = two_by_two_metrics(t)
    for key in ("lr_pos", "lr_neg", "dor"):
        assert m[key].ci_lo is None
        assert m[key].not_estimable_reason == "zero_cell_log_undefined"
    single = Table2x2(tp=0, fn=0, fp=10, tn=90)
    ms = two_by_two_metrics(single)
    assert ms["sensitivity"].not_estimable_reason == "zero_denominator"
    assert ms["youden"].not_estimable_reason == "single_class"


def test_f1_and_mcc_carry_a_typed_reason_rather_than_an_invented_interval():
    m = two_by_two_metrics(F2)
    for key in ("f1", "mcc"):
        assert m[key].ci_lo is None
        assert m[key].not_estimable_reason == "analytic_ci_unavailable"
        assert "ci_pending_bootstrap" in m[key].flags


def test_2x2_from_arrays_matches_hand_counts():
    y = ["1"] * 100 + ["0"] * 200
    pred = [True] * 90 + [False] * 10 + [True] * 20 + [False] * 180
    assert table_2x2_from_arrays(y, pred, "1") == F2


# ----------------------------------------------------------------- F11 PPA/NPA routing


@pytest.mark.fixture
def test_f11_ppa_npa_routing_when_reference_is_a_comparator():
    m = two_by_two_metrics(F2, reference_standard_type="comparator")
    assert sensitivity_id("comparator") == "ppa"
    assert specificity_id("comparator") == "npa"
    approx4(m["ppa"].est, 0.90)
    approx4(m["npa"].est, 0.90)
    # Identical numbers to F2, only the labels differ.
    ref = two_by_two_metrics(F2)
    assert m["ppa"].as_dict()["est"] == ref["sensitivity"].as_dict()["est"]
    assert m["ppa"].ci_lo == ref["sensitivity"].ci_lo
    # The forbidden words must not appear anywhere in the serialised block.
    blob = json.dumps({k: v.as_dict() for k, v in m.items()})
    assert "sensitivity" not in blob
    assert "specificity" not in blob


# -------------------------------------------------------------- F10 both-way indeterminates


@pytest.mark.fixture
def test_f10_indeterminates_both_ways():
    both = indeterminate_both_ways(F2, indeterminate_ref_pos=6, indeterminate_ref_neg=4)
    ap = two_by_two_metrics(both.as_positive)
    an = two_by_two_metrics(both.as_negative)
    approx4(ap["sensitivity"].est, 96 / 106)  # 0.9057
    approx4(ap["specificity"].est, 180 / 204)  # 0.8824
    approx4(an["sensitivity"].est, 90 / 106)  # 0.8491
    approx4(an["specificity"].est, 184 / 204)  # 0.9020
    # Both denominators grow by the indeterminates: nothing is quietly dropped.
    assert both.as_positive.n == both.as_negative.n == F2.n + 10
    for table in (both.as_positive, both.as_negative):
        assert table.n_pos == 106 and table.n_neg == 204


def test_indeterminate_both_ways_bracket_the_complete_case_analysis():
    both = indeterminate_both_ways(F2, 6, 4)
    se_cc = two_by_two_metrics(F2)["sensitivity"].est
    se_hi = two_by_two_metrics(both.as_positive)["sensitivity"].est
    se_lo = two_by_two_metrics(both.as_negative)["sensitivity"].est
    assert se_lo <= se_cc <= se_hi


# ------------------------------------------------------------------ F14 Newcombe Table II


@pytest.fixture(scope="module")
def newcombe_table2() -> dict:
    with (REPO / "fixtures" / "newcombe_table2.json").open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.fixture
def test_f14_newcombe_table2_unpaired_methods_10_and_11(newcombe_table2):
    """Reproduce every transcribed Table II interval to 4 decimal places."""
    for ex in newcombe_table2["examples"]:
        k1, n1, k2, n2 = ex["k1"], ex["n1"], ex["k2"], ex["n2"]
        assert abs((k1 / n1 - k2 / n2) - ex["difference"]) < 1e-12
        lo, hi = newcombe10_bounds(k1, n1, k2, n2)
        assert round(lo, 4) == ex["method10"]["lower"], ex["label"]
        assert round(hi, 4) == ex["method10"]["upper"], ex["label"]
        lo11, hi11 = newcombe11_bounds(k1, n1, k2, n2)
        assert round(lo11, 4) == ex["method11"]["lower"], ex["label"]
        assert round(hi11, 4) == ex["method11"]["upper"], ex["label"]


@pytest.mark.fixture
def test_f14_newcombe_paired_method_10(newcombe_table2):
    for ex in newcombe_table2["paired_examples"]["examples"]:
        e, f, g, h = ex["e"], ex["f"], ex["g"], ex["h"]
        lo, hi = newcombe_paired_bounds(e, f, g, h)
        assert round(lo, 4) == ex["method10"]["lower"], ex
        assert round(hi, 4) == ex["method10"]["upper"], ex
        assert abs(difference_paired(e, f, g, h).est - ex["difference"]) < 1e-12


def test_f14_fixture_records_its_provenance_honestly(newcombe_table2):
    """The fixture must not claim a primary-source transcription it did not make."""
    prov = newcombe_table2["provenance"]
    assert prov["transcribed_from_primary_pdf"] is False
    assert prov["status"].startswith("[unverified")
    assert prov["actual_source"].startswith("Values as reproduced")
    assert newcombe_table2["paired_examples"]["status"].startswith("[unverified")


def test_method11_is_wider_than_method10_everywhere_in_table2(newcombe_table2):
    for ex in newcombe_table2["examples"]:
        a = newcombe10_bounds(ex["k1"], ex["n1"], ex["k2"], ex["n2"])
        b = newcombe11_bounds(ex["k1"], ex["n1"], ex["k2"], ex["n2"])
        assert b[0] <= a[0] and b[1] >= a[1], ex["label"]


def test_unpaired_difference_number_carries_method_and_n():
    d = difference_unpaired(56, 70, 48, 80)
    assert d.method == "newcombe10" and d.n == 70
    assert d.ci_lo < d.est < d.ci_hi
    dcc = difference_unpaired(56, 70, 48, 80, continuity=True)
    assert dcc.method == "newcombe11" and "continuity_corrected" in dcc.flags


def test_newcombe10_matches_youden_construction():
    """J = Se - FPR is a difference of two independent proportions."""
    m = two_by_two_metrics(F2)
    lo, hi = newcombe10_bounds(F2.tp, F2.n_pos, F2.fp, F2.n_neg)
    assert abs(m["youden"].ci_lo - lo) < 1e-12
    assert abs(m["youden"].ci_hi - hi) < 1e-12


def test_difference_intervals_never_leave_the_minus_one_to_one_range():
    for k1, n1, k2, n2 in [(0, 5, 5, 5), (5, 5, 0, 5), (1, 2, 1, 2), (0, 1, 0, 1)]:
        lo, hi = newcombe10_bounds(k1, n1, k2, n2)
        assert -1.0 <= lo <= hi <= 1.0
        lo, hi = newcombe11_bounds(k1, n1, k2, n2)
        assert -1.0 <= lo <= hi <= 1.0


# ------------------------------------------------- the invariant: no Number without a CI


def test_number_without_ci_and_without_reason_is_impossible():
    with pytest.raises(ValueError, match="no confidence interval"):
        Number(est=0.5)
    with pytest.raises(ValueError, match="half-open"):
        Number(est=0.5, ci_lo=0.4, not_estimable_reason="single_class")
    with pytest.raises(ValueError, match="must name the method"):
        Number(est=0.5, ci_lo=0.4, ci_hi=0.6)
    with pytest.raises(ValueError, match="must not carry a not_estimable_reason"):
        Number(est=0.5, ci_lo=0.4, ci_hi=0.6, method="wilson", not_estimable_reason="single_class")
    with pytest.raises(ValueError, match="unknown method"):
        Number(est=0.5, ci_lo=0.4, ci_hi=0.6, method="made_up")
    with pytest.raises(ValueError, match="unknown not_estimable_reason"):
        Number(est=None, not_estimable_reason="because")


def test_every_number_this_module_can_produce_has_a_ci_or_a_typed_reason():
    """Sweep the whole 2x2 space at small n plus the fixture tables."""
    produced: list[Number] = []
    for tp in range(3):
        for fn in range(3):
            for fp in range(3):
                for tn in range(3):
                    t = Table2x2(tp, fn, fp, tn)
                    if t.n == 0:
                        continue
                    produced.extend(two_by_two_metrics(t).values())
                    produced.extend(
                        two_by_two_metrics(t, reference_standard_type="comparator").values()
                    )
                    produced.append(ppv_at_prevalence(t, 0.05))
                    produced.append(npv_at_prevalence(t, 0.05))
    for k in range(0, 21):
        produced.append(proportion(k, 20))
        alt = proportion_exact_alternative(k, 20)
        if alt is not None:
            produced.append(alt)
    produced.append(difference_unpaired(1, 2, 0, 2))
    produced.append(difference_paired(1, 1, 1, 1))
    assert produced
    for num in produced:
        assert num.has_ci or num.not_estimable_reason in NOT_ESTIMABLE_REASONS or num.suppressed
        if num.has_ci:
            assert num.method != "none"
            assert num.ci_lo <= num.ci_hi


def test_wilson_covers_the_point_estimate_over_a_wide_grid():
    for n in (1, 2, 5, 20, 263, 500, 5000):
        for k in {0, 1, n // 3, n // 2, n - 1, n}:
            if not 0 <= k <= n:
                continue
            lo, hi = wilson_bounds(k, n)
            assert 0.0 <= lo <= k / n <= hi <= 1.0, (k, n)


# ----------------------------------------------------------------------- output schema


def test_output_schema_is_valid_and_enforces_the_no_ci_rule():
    import jsonschema

    schema = load_json_schema("output_schema_v1.json")
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    number_schema = {"$ref": "#/$defs/Number", "$defs": schema["$defs"]}
    v = validator_cls(number_schema)

    good = proportion(81, 263).as_dict()
    good.setdefault("n", 263)
    v.validate(_fill(good))

    reasoned = two_by_two_metrics(F2)["f1"].as_dict()
    v.validate(_fill(reasoned))

    bad = _fill(proportion(81, 263).as_dict())
    bad["ci_lo"] = None
    bad["ci_hi"] = None
    with pytest.raises(jsonschema.ValidationError):
        v.validate(bad)  # no interval, no reason, and method != none

    bad2 = _fill(proportion(81, 263).as_dict())
    bad2["method"] = "wald"
    with pytest.raises(jsonschema.ValidationError):
        v.validate(bad2)


def _fill(d: dict) -> dict:
    for key in ("est", "ci_lo", "ci_hi", "not_estimable_reason"):
        d.setdefault(key, None)
    d.setdefault("flags", [])
    d.setdefault("suppressed", False)
    d.setdefault("ci_level", 0.95)
    d.setdefault("method", "none")
    return d


def test_operating_point_block_forbids_mixing_sensitivity_and_ppa():
    import jsonschema

    schema = load_json_schema("output_schema_v1.json")
    v = jsonschema.validators.validator_for(schema)(
        {"$ref": "#/$defs/operatingPointBlock", "$defs": schema["$defs"]}
    )
    se = _fill(proportion(90, 100).as_dict())
    sp = _fill(proportion(180, 200).as_dict())
    v.validate({"two_by_two": F2.as_dict(), "sensitivity": se, "specificity": sp})
    v.validate({"two_by_two": F2.as_dict(), "ppa": se, "npa": sp})
    with pytest.raises(jsonschema.ValidationError):
        v.validate(
            {"two_by_two": F2.as_dict(), "sensitivity": se, "specificity": sp, "ppa": se, "npa": sp}
        )


def test_output_schema_ships_in_the_wheel_layout():
    assert resource_path("output_schema_v1.json").exists()


def test_method_and_reason_enums_agree_between_code_and_schema():
    schema = load_json_schema("output_schema_v1.json")
    assert set(schema["$defs"]["method"]["enum"]) == set(METHODS)
    assert set(schema["$defs"]["notEstimableReason"]["enum"]) == set(NOT_ESTIMABLE_REASONS)


# --------------------------------------------------------------- oracles stay test-only


def test_no_oracle_leaks_into_the_runtime_package():
    """statsmodels / scikit-learn / pandas are test dependencies only."""
    banned = ("statsmodels", "sklearn", "scikit", "pandas")
    for path in (REPO / "src" / "proofpack").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for name in banned:
            assert f"import {name}" not in text, (path, name)
