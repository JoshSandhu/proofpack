"""Build day 11 (E11) item 7: the day-6 handoff's carried observers
(``handoffs/2026-09-18_E.md``, table A, items 1-19), one assertion each.

None of the nineteen was closed on a later day: the day-7 note lists 1-19 open
(``handoffs/2026-09-21_E.md`` line 190) and the day-8 note "E6 items still open ... 1-24"
(``handoffs/2026-09-22_E.md`` line 112); no later note closes one. Each test below names
the item, its mutant as planted on build day 11 (the code moved since day 6, so each
mutant is the day-6 one re-expressed on today's line) and fails on it; the build note
records the planted result of every one.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from conftest import make_cohort, make_criteria
from proofpack.io import schema as schema_mod
from proofpack.io.declare import validate_dict
from proofpack.stats.bootstrap import BootstrapPolicy
from proofpack.stats.calibration import calibration_block, calibration_from_table
from proofpack.stats.descriptive import flow_block, table1_block
from proofpack.stats.proportions import z_for
from test_calibration import POLICY, block, cohort_arrays, decl, f4, hand_equal_mass

pytestmark = pytest.mark.day11

CLUSTERED = {"clustering": {"unit": "case_id", "declared_by": "t"}}


def _clustered(p, y, ids, policy=POLICY, level=0.95):
    res = calibration_block(
        np.asarray(p, dtype=np.float64),
        np.asarray(y, dtype=bool),
        decl(**CLUSTERED),
        cluster_ids=np.asarray(ids, dtype=object),
        policy=policy,
        level=level,
    )
    assert res.block is not None
    return res.block


# 1. mutant: _decile_curve passes plan=None to proportion_ci
def test_item1_a_decile_bin_of_one_row_cases_keeps_the_declared_route():
    _, p, y = cohort_arrays(n=200)
    b = _clustered(p, y, [f"c{i}" for i in range(200)])
    routes = {d["observed"]["clustering_route"] for d in b["decile_curve"]}
    methods = {d["observed"]["number"]["method"] for d in b["decile_curve"]}
    assert routes == {"declared"} and methods == {"wilson_deff"}


# 2. mutant: _Ctx.tier drops the few-events rule on i.i.d. rows (events = None)
def test_item2_iid_n100_with_three_events_carries_very_low_precision():
    rng = np.random.default_rng(2)
    p = rng.uniform(0.01, 0.1, 100)
    y = np.zeros(100, bool)
    y[:3] = True
    b = block(p, y)
    assert "very_low_precision" in b["oe"]["number"]["flags"]


# 3. mutant: the i.i.d. IPA resample uses the full-cohort Brier
def test_item3_the_iid_ipa_on_f4_has_its_interval_and_flags():
    p, y = f4()
    ipa = block(p, y)["ipa"]["number"]
    assert (round(ipa["ci_lo"], 4), round(ipa["ci_hi"], 4)) == (-0.0290, 0.6148)
    assert ipa["flags"] == ["very_low_precision", "imprecise"]


# 4. mutant: IRLS_TOL = 1e-3 (moves this cohort's slope by 3.3e-6, inside F4's 1e-6 gate
#    on F4 itself but not here)
def test_item4_the_slope_equals_statsmodels_to_1e_9_on_a_random_cohort():
    import statsmodels.api as sm

    rng = np.random.default_rng(11)
    n = 150
    p = rng.uniform(0.02, 0.98, n)
    lp = np.log(p / (1 - p))
    y = rng.uniform(size=n) < 1 / (1 + np.exp(-(0.3 + 1.7 * lp)))
    ref = sm.GLM(y.astype(float), sm.add_constant(lp), family=sm.families.Binomial()).fit(
        tol=1e-14, maxiter=200
    )
    b = block(p, y)
    assert abs(b["slope"]["number"]["est"] - float(ref.params[1])) <= 1e-9
    assert abs(b["intercept"]["number"]["est"] - float(ref.params[0])) <= 1e-9


# 5. mutant: _clustered_cell drops the tier flags
def test_item5_a_clustered_cohort_of_20_cases_keeps_its_tier_on_the_oe_and_the_fits():
    _, p, y = cohort_arrays(n=40)
    b = _clustered(p, y, [f"c{i // 2}" for i in range(40)])
    for key in ("oe", "intercept_large", "slope", "intercept"):
        assert "very_low_precision" in b[key]["number"]["flags"], key


# 6. mutant: the 200/200 rule counted on cases, not rows, under clustering
def test_item6_rows_decide_the_200_200_flag_under_clustering():
    rng = np.random.default_rng(6)
    y = np.repeat(np.arange(300) < 150, 2)  # 300 event rows in 150 cases, 300 non-event
    p = np.clip(rng.uniform(0.05, 0.95, 600), 0.01, 0.99)
    b = _clustered(p, y, [f"c{i // 2}" for i in range(600)])
    assert b["events"] == 300 and b["nonevents"] == 300
    assert b["flags"] == [] and b["curve_flag"] is None


# 7. mutant: flow.n_sites counts Unknown/missing as a site
def test_item7_a_blank_site_is_not_counted_as_a_site():
    cols = make_cohort(n=60)
    cols["site"] = ["S1", "S2", "S3"] * 20
    cols["site"][0] = ""
    d = validate_dict(make_criteria())
    table = schema_mod.validate(schema_mod.table_from_columns(cols), period=None)
    mask, flow = schema_mod.analysis_mask(table, d.indeterminate_values)
    assert flow_block(table, mask, flow, d)["n_sites"] == 3


# 8. mutant: table1.dev tabulated over ~mask instead of the dataset = dev rows
def test_item8_the_dev_table_is_the_dev_rows_only_beside_excluded_test_rows():
    cols = make_cohort(n=100)
    cols["dataset"] = ["dev"] * 30 + ["test"] * 70
    for i in (40, 41, 42, 43, 44):
        cols["y_true"][i] = ""  # five excluded test rows
    d = validate_dict(make_criteria())
    table = schema_mod.validate(schema_mod.table_from_columns(cols), period=None)
    mask, _ = schema_mod.analysis_mask(table, d.indeterminate_values)
    t1 = table1_block(table, d, mask)
    assert sum(lv["n"] for lv in t1["dev"]["sex"].values()) == 30


# 9. mutant: the DEC-09 companion on the O:E carries est=None
def test_item9_the_clustered_oe_companion_carries_the_estimate():
    _, p, y = cohort_arrays(n=200)
    b = _clustered(p, y, [f"c{i // 2}" for i in range(200)])
    for key in ("oe", "intercept_large", "slope"):
        assert b[key]["analytic"]["est"] == b[key]["number"]["est"] is not None, key


def _forty_one_row_cases_two_events():
    rng = np.random.default_rng(3)
    p = rng.uniform(0.05, 0.3, 40)
    y = np.zeros(40, bool)
    y[:2] = True
    return _clustered(p, y, [f"c{i}" for i in range(40)])


# 10. mutant: a refused clustered draw reports analytic_status refused_clustered
def test_item10_a_degenerate_clustered_oe_is_unavailable_not_refused_clustered():
    oe = _forty_one_row_cases_two_events()["oe"]
    assert oe["number"]["not_estimable_reason"] == "degenerate_resamples"
    assert oe["analytic_status"] == "unavailable"


# 11. mutant: scores_clipped_for_logit dropped from the clustered IRLS Numbers
def test_item11_clipped_scores_are_flagged_on_the_clustered_fits():
    _, p, y = cohort_arrays(n=200)
    p = p.copy()
    p[:10], p[10:20] = 0.0, 1.0
    b = _clustered(p, y, [f"c{i // 2}" for i in range(200)])
    assert b["n_clipped"] == 20
    for key in ("intercept_large", "slope", "intercept"):
        assert "scores_clipped_for_logit" in b[key]["number"]["flags"], key


# 12. mutant: calibration_from_table passes table.case_id unsliced by the mask
def test_item12_the_case_column_is_sliced_with_the_mask():
    rng = np.random.default_rng(12)
    y_true = np.array(["1", "0"] * 20, dtype=object)
    y_true[5] = ""
    table = SimpleNamespace(
        y_true=y_true,
        score=rng.uniform(0.05, 0.95, 40),
        case_id=np.array([f"c{i // 2}" for i in range(40)], dtype=object),
    )
    mask = y_true != ""
    res = calibration_from_table(table, decl(**CLUSTERED), mask, policy=POLICY)
    assert res.block is not None and res.block["n"] == 39


# 13. mutant: curve_flag.event_cases counted over the non-event rows
def test_item13_event_cases_are_the_cases_of_the_event_rows():
    _, p, y = cohort_arrays(n=200)
    ids = np.array([f"c{i // 2}" for i in range(200)], dtype=object)
    b = _clustered(p, y, ids)
    assert b["curve_flag"]["event_cases"] == len(set(ids[y].tolist()))
    assert b["curve_flag"]["event_cases"] != len(set(ids[~y].tolist()))


# 14. mutant: _Ctx.tier applies the few-events rule under clustering (DEC-35 kept the
#     day-6 policy: cases decide the tier under clustering, not events)
def test_item14_the_clustered_oe_on_60_one_row_cases_with_3_events_has_no_events_tier():
    rng = np.random.default_rng(3)
    rng.uniform(0.05, 0.3, 40)  # the same stream position as the prototype measured
    p = rng.uniform(0.02, 0.2, 60)
    y = np.zeros(60, bool)
    y[:3] = True
    b = _clustered(p, y, [f"c{i}" for i in range(60)])
    assert "very_low_precision" not in b["oe"]["number"]["flags"]


# 15. mutant: _prevalence_invariant never inspects a stratum's last unit
def test_item15_a_differing_last_unit_makes_the_reference_brier_vary():
    # positive cases c0-c2 of one row, then c3 of two rows (last), beside ten one-row
    # negative cases: R * pos_u - P * rows_u reads 10, 10, 10, 20 in the positive stratum
    ids = ["c0", "c1", "c2", "c3", "c3"] + [f"n{i}" for i in range(10)]
    y = np.array([True] * 5 + [False] * 10)
    p = np.linspace(0.2, 0.8, 15)
    b = _clustered(p, y, ids, policy=BootstrapPolicy(n_resamples=200, seed=5))
    assert b["brier_ref"]["number"]["not_estimable_reason"] != "fixed_by_outcome_stratification"


# 16. mutant: _irls_cells uses z_for(DEFAULT_LEVEL) instead of z_for(ctx.level)
def test_item16_f4_at_level_0_90_puts_its_three_wald_bounds_at_z_0_90():
    p, y = f4()
    res = calibration_block(p, y, decl(), policy=POLICY, level=0.90)
    z = z_for(0.90)
    for key in ("intercept_large", "slope", "intercept"):
        cell = res.block[key]
        est, se = cell["number"]["est"], cell["detail"]["wald_se"]
        assert cell["number"]["ci_level"] == 0.9
        assert abs(cell["number"]["ci_lo"] - (est - z * se)) <= 1e-12, key
        assert abs(cell["number"]["ci_hi"] - (est + z * se)) <= 1e-12, key


# 17. mutant: mean_pred is the bin's median
def test_item17_mean_pred_is_the_mean_of_the_bins_scores():
    _, p, y = cohort_arrays(n=300)
    b = block(p, y)
    for d, rows in zip(b["decile_curve"], hand_equal_mass(p), strict=True):
        assert abs(d["mean_pred"] - float(np.mean(p[rows]))) <= 1e-15


# 18. mutant: SEPARATION_TOL = 1e-4
def test_item18_scores_within_1e_5_of_their_labels_converge_and_are_not_separated():
    p = np.array([1e-5] * 30 + [1 - 1e-5] * 30)
    y = p > 0.5
    il = block(p, y)["intercept_large"]
    assert il["number"]["method"] == "irls_wald" and il["detail"]["outcome"] == "converged"
    assert abs(il["number"]["est"]) <= 1e-9
    assert round(il["number"]["ci_lo"], 2) == -80.02


# 19. the docstring's "a resample on which the IRLS does not converge is nan to the
#     resampler and counted against MIN_USABLE_FRACTION"; mutant: the clustered statistic
#     returns 0.0 for a refit that did not converge
def test_item19_a_non_converging_refit_is_not_a_usable_resample():
    slope = _forty_one_row_cases_two_events()["slope"]
    assert slope["bootstrap"]["usable_resamples"] < 200
    assert slope["number"]["not_estimable_reason"] == "degenerate_resamples"


def test_the_module_lists_nineteen_items():
    import re
    import sys

    names = [n for n in dir(sys.modules[__name__]) if n.startswith("test_item")]
    assert sorted(int(re.match(r"test_item(\d+)_", n).group(1)) for n in names) == list(
        range(1, 20)
    )
