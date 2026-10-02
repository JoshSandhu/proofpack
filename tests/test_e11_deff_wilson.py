"""Build day 11 (E11) item 5, DEC-18 (a): the design-effect-adjusted Wilson interval for
clustered proportions (method ``wilson_deff``).

**This item touches a statistical gate** (the interval every clustered proportion of five
cases or more now prints): DEC-12 (i) asks for its own fresh-attack lens.

* **Hand oracle** on a literal clustered table - four cases of three rows with 2, 1, 3, 0
  successes (``n = 12``, ``k = 6``, ``p = 0.5``): ``sum (y_i - p m_i)^2 = 5``,
  ``v = 4/3 * 5 / 144 = 5/108``, ``p (1 - p) / n = 1/48``, so ``DEFF = 20/9`` and
  ``n_eff = 5.4``; the Wilson bounds on (0.5, 5.4) by this test's own arithmetic; the
  engine to 1e-12.
* **DEFF = 1 reproduces the plain Wilson interval exactly** (``==``): one row per case
  under a declared plan, and an estimate floored at 1.
* **Wider than the unclustered Wilson** when the cases are positively correlated (the
  literal table: half-width 0.3224 against 0.2462 on the rows).
* **Typed cases**: one case (not estimable; the bootstrap's own refusal renders), one row
  per case (``DEFF = 1``), every row agreeing (the cases as the units), floored at 1.
* **The bar**: ``MIN_CASES_DEFF_WILSON`` equals the committed coverage run's threshold;
  every committed shape with at least that many cases covers at or above 0.90; the T7
  table equals the JSON; ``scripts/coverage_bar.py --deff-wilson`` re-run here writes the
  committed JSON's rows exactly.
* **Accept**: on a clustered run with cells of 2 to 60 cases, every rendered clustered
  proportion is either ``wilson_deff`` on at least five cases or carries its tier
  annotation.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

from assembler import assemble
from conftest import make_cohort, make_criteria
from deff_hand import hand_deff, hand_deff_wilson, hand_wilson
from proofpack.stats.bootstrap import (
    MIN_CASES_DEFF_WILSON,
    plan_clustering,
    precision_flags,
    proportion_ci,
)
from proofpack.stats.number import Number
from proofpack.stats.proportions import (
    DEFF_REASONS,
    DesignEffect,
    design_effect,
    proportion,
    proportion_deff,
    wilson_bounds,
)

pytestmark = pytest.mark.day11

REPO = Path(__file__).resolve().parent.parent
COVERAGE = REPO / "design" / "coverage_deff_wilson.json"
LITERAL_IND = np.array([1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0], dtype=bool)
LITERAL_IDS = np.repeat(np.array(["a", "b", "c", "d"], dtype=object), 3)


def test_the_literal_table_by_hand():
    de = design_effect(LITERAL_IND, LITERAL_IDS)
    assert de.reason == "deff_estimated" and de.n_cases == 4 and de.n == 12
    assert abs(de.deff - 20 / 9) <= 1e-12 and abs(de.n_eff - 5.4) <= 1e-12
    assert abs(hand_deff(LITERAL_IND, LITERAL_IDS.tolist())[0] - 20 / 9) <= 1e-12
    num = proportion_deff(6, 12, de)
    lo, hi = hand_wilson(0.5, 5.4)
    assert abs(num.ci_lo - lo) <= 1e-12 and abs(num.ci_hi - hi) <= 1e-12
    assert (round(num.ci_lo, 4), round(num.ci_hi, 4)) == (0.1776, 0.8224)
    assert num.method == "wilson_deff" and (num.n, num.k, num.n_cases) == (12, 6, 4)
    Number(**num.as_dict())


def test_deff_one_reproduces_the_plain_wilson_interval_exactly():
    for k, n in ((0, 7), (3, 7), (7, 7), (81, 263), (29, 30)):
        de = DesignEffect(1.0, n / 1.0, n, n, "deff_one_row_per_case")
        assert wilson_bounds(k, n) == (
            proportion_deff(k, n, de).ci_lo,
            proportion_deff(k, n, de).ci_hi,
        )
    # through proportion_ci: one row per case under a declared plan
    ids = np.array([f"c{i}" for i in range(40)], dtype=object)
    ind = np.arange(40) % 3 == 0
    plan = plan_clustering("case_id", ids, 40)
    cell = proportion_ci(ind, cell_key="x", plan=plan, cluster_ids=ids)
    plain = proportion(int(ind.sum()), 40)
    assert cell.number.method == "wilson_deff"
    assert (cell.number.ci_lo, cell.number.ci_hi) == (plain.ci_lo, plain.ci_hi)
    assert cell.detail["design_effect"]["reason"] == "deff_one_row_per_case"


def test_an_estimate_below_one_is_floored_and_gives_the_plain_wilson_bounds():
    # cases of two rows each holding one success and one failure: no between-case spread
    ind = np.tile([True, False], 10)
    ids = np.repeat(np.arange(10), 2)
    de = design_effect(ind, ids)
    assert de.reason == "deff_floored_at_one" and de.deff == 1.0 and de.estimate == 0.0
    num = proportion_deff(10, 20, de)
    assert (num.ci_lo, num.ci_hi) == wilson_bounds(10, 20)


def test_positively_correlated_cases_give_a_wider_interval_than_the_rows_wilson():
    num = proportion_deff(6, 12, design_effect(LITERAL_IND, LITERAL_IDS))
    lo, hi = wilson_bounds(6, 12)
    assert num.ci_lo < lo and num.ci_hi > hi
    assert round((num.ci_hi - num.ci_lo) / 2, 4) == 0.3224 and round((hi - lo) / 2, 4) == 0.2462


def test_the_typed_cases():
    one = design_effect(np.array([1, 0, 1], bool), np.array(["a", "a", "a"]))
    assert (one.deff, one.reason) == (None, "deff_not_estimable_single_case")
    with pytest.raises(ValueError, match="no design effect"):
        proportion_deff(2, 3, one)
    boundary = design_effect(np.ones(9, bool), np.repeat([1, 2, 3], 3))
    assert boundary.reason == "deff_boundary_cases_as_units"
    assert boundary.deff == 3.0 and boundary.n_eff == 3.0
    # unequal case sizes 1, 2, 5: sum m^2 / n = 30 / 8 (within-case correlation 1), not 8 / 3
    uneven = design_effect(np.zeros(8, bool), np.array(["a", "b", "b"] + ["c"] * 5))
    assert uneven.deff == 30 / 8 and abs(uneven.n_eff - 64 / 30) <= 1e-15
    assert uneven.deff == hand_deff(np.zeros(8, bool), ["a", "b", "b"] + ["c"] * 5)[0]
    assert set(DEFF_REASONS) == {
        "deff_estimated",
        "deff_floored_at_one",
        "deff_one_row_per_case",
        "deff_boundary_cases_as_units",
        "deff_not_estimable_single_case",
    }
    # one case through proportion_ci: the bootstrap's own refusal renders, route recorded
    ids = np.array(["a"] * 6, dtype=object)
    plan = plan_clustering("case_id", ids, 6)
    cell = proportion_ci(
        np.array([1, 0, 1, 1, 0, 1], bool), cell_key="y", plan=plan, cluster_ids=ids
    )
    assert cell.detail["design_effect"]["route"] == "not_estimable"
    assert cell.number.method != "wilson_deff"


def _clustered_cell(n_cases: int, rows: int = 3, seed: int = 4):
    rng = np.random.default_rng(seed)
    ids = np.repeat(np.array([f"c{i}" for i in range(n_cases)], dtype=object), rows)
    ind = np.repeat(rng.random(n_cases) < 0.6, rows) ^ (rng.random(n_cases * rows) < 0.2)
    plan = plan_clustering("case_id", ids, ids.shape[0])
    return proportion_ci(ind, cell_key=f"k{n_cases}", plan=plan, cluster_ids=ids), ind, ids


def test_the_route_switches_at_the_measured_case_count():
    assert MIN_CASES_DEFF_WILSON == 5
    below, _, _ = _clustered_cell(MIN_CASES_DEFF_WILSON - 1)
    at, ind, ids = _clustered_cell(MIN_CASES_DEFF_WILSON)
    assert below.number.method == "cluster_bootstrap_percentile"
    assert below.detail["design_effect"]["route"] == "below_coverage_bar"
    assert "not_evaluable_shown_for_transparency" in below.number.flags
    assert at.number.method == "wilson_deff" and at.policy is None
    assert at.detail["design_effect"]["route"] == "wilson_deff"
    _, lo, hi = hand_deff_wilson(ind, ids.tolist())
    assert abs(at.number.ci_lo - lo) <= 1e-12 and abs(at.number.ci_hi - hi) <= 1e-12
    assert at.number.flags[0] == "wilson_refused_clustered"
    assert precision_flags(5)[0] in at.number.flags
    assert at.analytic.not_estimable_reason == "clustered_data_analytic_ci_invalid"
    out = at.as_dict()
    assert out["bootstrap"] is None and out["detail"]["design_effect"]["estimator"].endswith(
        "[unverified]"
    )


def test_the_constant_is_the_committed_coverage_runs_threshold_and_t7_prints_its_table():
    sys.path.insert(0, str(REPO / "scripts"))
    import coverage_bar

    data = json.loads(COVERAGE.read_text(encoding="utf-8"))
    assert data["bar"] == 0.9 and data["reps"] == 4000 and data["seed"] == 20261002
    assert data["min_cases_meeting_bar"] == MIN_CASES_DEFF_WILSON
    assert coverage_bar.deff_threshold(data["rows"]) == MIN_CASES_DEFF_WILSON
    assert all(r["coverage"] >= 0.9 for r in data["rows"] if r["u_cases"] >= 5)
    assert any(r["coverage"] < 0.9 for r in data["rows"] if r["u_cases"] == 4)
    conv = (REPO / "design" / "conventions_T7.md").read_text(encoding="utf-8")
    section = conv[conv.index("### Design-effect Wilson interval") :]
    table = {}
    for line in section.splitlines():
        m = re.match(r"^\| (\d+) \| (.*) \|$", line)
        if m:
            table[int(m.group(1))] = [float(x) for x in m.group(2).split(" | ")]
    cols = [(w, p) for p in (0.5, 0.9) for w in (1, 3, 8)]
    by = {(r["u_cases"], r["rows_per_case"], r["truth"]): r["coverage"] for r in data["rows"]}
    assert sorted(table) == sorted({r["u_cases"] for r in data["rows"]})
    for u, values in table.items():
        assert values == [round(by[(u, w, p)], 3) for w, p in cols], u


@pytest.mark.slow
def test_the_coverage_script_rewrites_the_committed_rows(tmp_path):
    sys.path.insert(0, str(REPO / "scripts"))
    import coverage_bar

    out = tmp_path / "deff.json"
    assert coverage_bar.main(["--deff-wilson", "--json", str(out)]) == 0
    again = json.loads(out.read_text(encoding="utf-8"))
    committed = json.loads(COVERAGE.read_text(encoding="utf-8"))
    assert again["rows"] == committed["rows"]
    assert again["min_cases_meeting_bar"] == committed["min_cases_meeting_bar"]


def _clustered_run_cohort() -> tuple[dict, dict]:
    cols = make_cohort(n=360, with_case_id=True)
    cols["case_id"] = [f"c{i // 3:05d}" for i in range(360)]
    # a site of 2 cases, one of 4 and the rest: cells on both sides of the threshold
    cols["site"] = ["S9"] * 6 + ["S8"] * 12 + ["S1", "S1", "S1", "S2", "S2", "S2"] * 57
    crit = make_criteria(criteria=[], clustering={"unit": "case_id", "declared_by": "t"})
    return cols, crit


def test_accept_no_rendered_clustered_proportion_below_the_bar_without_its_tier():
    cols, crit = _clustered_run_cohort()
    doc = assemble(cols, copy.deepcopy(crit))
    seen = {"wilson_deff": 0, "cluster_bootstrap_percentile": 0}
    tiers = {"not_evaluable_shown_for_transparency", "very_low_precision"}
    for row in doc["subgroups"]:
        for metric in ("sensitivity", "specificity", "ppv", "npv", "accuracy"):
            cell = row["metrics"]["op1"][metric]
            num = cell["number"]
            if num["ci_lo"] is None:
                continue
            seen[num["method"]] += 1
            if num["method"] == "wilson_deff":
                assert num["n_cases"] >= MIN_CASES_DEFF_WILSON, (row["level"], metric)
                assert cell["detail"]["design_effect"]["route"] == "wilson_deff"
            else:
                assert num["method"] == "cluster_bootstrap_percentile"
                assert cell["detail"]["design_effect"]["route"] == "below_coverage_bar"
                assert tiers & set(num["flags"]), (row["level"], metric, num["flags"])
    assert seen["wilson_deff"] > 0 and seen["cluster_bootstrap_percentile"] > 0


def test_t7_names_the_method_and_prints_the_coverage_section():
    from proofpack.render import t7 as render_t7

    cols, crit = _clustered_run_cohort()
    doc = assemble(cols, copy.deepcopy(crit))
    page = render_t7.render_t7(doc)
    assert "Coverage of the clustered intervals" in page
    assert "Design-effect Wilson interval for clustered proportions" in page
    assert "wilson_deff" in page and "MIN_CASES_DEFF_WILSON = 5" in page
    desc = render_t7.METHOD_DESCRIPTIONS["wilson_deff"]
    assert "[unverified]" in desc and "citation pending verification" in desc
