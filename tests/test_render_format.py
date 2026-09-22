"""Build day 8 (E8 item 7): ``proofpack.render.format`` on literal inputs - the D4
section 1.2 rules, one assertion per rule, every expected string typed by hand."""

from __future__ import annotations

import pytest

from proofpack.render import format as fmt

pytestmark = pytest.mark.day8


def _num(est, lo, hi, **kw):
    base = {
        "est": est,
        "ci_lo": lo,
        "ci_hi": hi,
        "ci_level": 0.95,
        "method": "wilson",
        "flags": [],
        "suppressed": False,
        "not_estimable_reason": None,
    }
    base.update(kw)
    return base


def test_the_d4_proportion_example_prints_k_over_n_percent_and_the_interval_in_points():
    # D4 section 1.2: 81/263 (30.8%) [25.5, 36.6]
    num = _num(81 / 263, 0.2551, 0.3662, k=81, n=263)
    assert fmt.number(num, "proportion") == "81/263 (30.8%) [25.5, 36.6]"


def test_a_proportion_without_k_prints_the_percentage_and_interval_only():
    assert fmt.number(_num(0.9, 0.826, 0.945, n=100), "proportion") == "(90.0%) [82.6, 94.5]"


def test_three_decimal_quantities():
    assert fmt.number(_num(0.7948394595, 0.7421, 0.8412, method="delong_logit"), "three_dp") == (
        "0.795 [0.742, 0.841]"
    )
    assert fmt.number(_num(1.0, 0.95, 1.05, method="log_delta"), "three_dp") == (
        "1.000 [0.950, 1.050]"
    )


def test_differences_in_percentage_points_carry_a_sign_and_the_unicode_minus():
    num = _num(-0.032, -0.061, -0.004, method="newcombe10")
    assert fmt.number(num, "difference_pp") == "−3.2 [−6.1, −0.4]"
    assert fmt.number(_num(0.05, -0.01, 0.11, method="newcombe10"), "difference_pp") == (
        "+5.0 [−1.0, +11.0]"
    )
    assert fmt.number(_num(0.0, -0.02, 0.02, method="newcombe10"), "difference_pp") == (
        "0.0 [−2.0, +2.0]"
    )
    assert fmt.number(_num(-0.0123, -0.05, 0.03, method="delong_logit"), "difference_3dp") == (
        "−0.012 [−0.050, +0.030]"
    )


def test_a_suppressed_number_prints_the_marker_and_no_digit():
    num = _num(None, None, None, suppressed=True, n=7, k=3)
    out = fmt.number(num, "proportion")
    assert out == "‡"
    assert not any(ch.isdigit() for ch in out)


def test_a_typed_reason_prints_the_reason_and_no_digit_from_est():
    num = _num(0.6620689655172414, None, None, method="none")
    num["not_estimable_reason"] = "analytic_ci_unavailable"
    num["n"] = 400
    for kind in fmt.KINDS:
        out = fmt.number(num, kind)
        assert out == "n.e. (analytic_ci_unavailable)", kind
        assert not any(ch.isdigit() for ch in out)
    assert fmt.number(None, "three_dp") == "n.e."


def test_tier_superscripts_follow_the_flags():
    num = _num(0.5, 0.2, 0.8, k=5, n=10, flags=["very_low_precision", "imprecise"])
    assert fmt.number(num, "proportion") == "5/10 (50.0%) [20.0, 80.0]ᵇᶜ"
    num = _num(1.0, 0.6, 1.0, k=4, n=4, flags=["not_evaluable_shown_for_transparency"])
    assert fmt.number(num, "proportion").endswith("ᵃ")
    reason = _num(None, None, None, method="none", flags=["not_evaluable_shown_for_transparency"])
    reason["not_estimable_reason"] = "single_class"
    assert fmt.number(reason, "proportion") == "n.e. (single_class)ᵃ"


def test_counts_scalars_and_p_values():
    assert fmt.count(30) == "30" and fmt.count(0) == "0" and fmt.count(None) == "—"
    assert fmt.scalar(0.85) == "0.850" and fmt.scalar(0.8864866068260313) == "0.886"
    assert fmt.scalar(True) == "yes" and fmt.scalar(False) == "no" and fmt.scalar(None) == "—"
    assert fmt.scalar(3) == "3"
    assert fmt.p_value(0.0004) == "<0.001" and fmt.p_value(0.0314159) == "0.031"
    assert fmt.p_value(None) == "—"


def test_text_passes_unverified_markings_verbatim():
    s = "Newcombe 1998 Table II [unverified against the primary PDF]"
    assert fmt.text(s) == s
    assert fmt.text(None) == ""


def test_rounding_is_the_single_format_call_on_the_double():
    # format(0.30798479087452474 * 100, ".1f") == "30.8"; a value whose binary double sits
    # just below a tie rounds down, the way format() reads it, never re-rounded
    assert fmt.percent(0.30798479087452474) == "30.8"
    assert fmt.percent(0.12345) == "12.3"
    assert fmt.percent(0.125) == "12.5"
    assert fmt.scalar(0.0005, 3) == "0.001" or fmt.scalar(0.0005, 3) == "0.000"
    assert fmt.scalar(2.675, 2) == "2.67"  # the classic binary-double case


def test_kind_for_maps_metric_families():
    assert fmt.kind_for("sensitivity") == "proportion"
    assert fmt.kind_for("ppa") == "proportion" and fmt.kind_for("prevalence") == "proportion"
    assert fmt.kind_for("auroc") == "three_dp" and fmt.kind_for("brier") == "three_dp"
    assert fmt.kind_for("f1") == "three_dp" and fmt.kind_for("lr_pos") == "three_dp"
    assert fmt.kind_for("tpr_gap") == "difference_pp"
    assert fmt.kind_for("auroc_gap") == "difference_3dp"
    assert fmt.kind_for("sensitivity", difference=True) == "difference_pp"
    assert fmt.kind_for("auroc", difference=True) == "difference_3dp"
    with pytest.raises(ValueError):
        fmt.number(_num(0.5, 0.4, 0.6), "percent")


def test_method_prints_the_method_string_or_a_dash():
    assert fmt.method(_num(0.5, 0.4, 0.6, method="cluster_bootstrap_percentile")) == (
        "cluster_bootstrap_percentile"
    )
    assert fmt.method(None) == "—"
