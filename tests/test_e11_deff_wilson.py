"""Build day 11 (E11) item 5, DEC-18 (a): the design-effect-adjusted Wilson interval for
clustered proportions (method ``wilson_deff``).

**This item touches a statistical gate** (the interval a clustered proportion prints):
DEC-12 (i) asks for its own fresh-attack lens. E11 repair 1 narrowed the route (a case
share and a rows-per-case bound, ``stats.bootstrap.deff_wilson_route``) and widened the
coverage grid (``scripts/coverage_bar.py --deff-wilson`` v2); the tests below read the v2
JSON.

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
* **The bar**: the committed coverage run's threshold (the smallest case count from
  which every printed constant-setting row covers at or above 0.90) is at most
  ``VERY_LOW_PRECISION_UNITS`` (30), so every printed ``wilson_deff`` cell of fewer cases
  carries its tier annotation; each row's ``route`` is ``deff_wilson_route`` of its
  shape; the T7 table equals the JSON; a sample of rows re-runs exactly.
* **Accept**: on a clustered run, every ``wilson_deff`` cell is inside the route's bounds,
  every other cell names its route, and every cell of fewer than 30 cases carries its
  tier annotation.
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
    MAX_CASE_SHARE_DEFF_WILSON,
    MAX_ROWS_PER_CASE_DEFF_WILSON,
    MIN_CASES_DEFF_WILSON,
    VERY_LOW_PRECISION_UNITS,
    deff_wilson_route,
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


def test_the_route_switches_at_five_cases_and_names_each_other_route():
    """E11 repair 1: five cases or more, no case above a fifth of the rows, at most 50 rows
    per case. Literal shapes: the two lenses' one-dominant-case cells (49 rows in 10 cases,
    the largest 40; 99 rows in 40 cases, the largest 60) go to the bootstrap."""
    assert MIN_CASES_DEFF_WILSON == 5
    assert (MAX_CASE_SHARE_DEFF_WILSON, MAX_ROWS_PER_CASE_DEFF_WILSON) == (0.20, 50)
    assert deff_wilson_route(12, 4, 3, True) == "below_coverage_bar"
    assert deff_wilson_route(15, 5, 3, True) == "wilson_deff"
    assert deff_wilson_route(50, 5, 10, True) == "wilson_deff"  # exactly a fifth
    assert deff_wilson_route(51, 5, 11, True) == "case_share_above_grid"
    assert deff_wilson_route(49, 10, 40, True) == "case_share_above_grid"
    assert deff_wilson_route(99, 40, 60, True) == "case_share_above_grid"
    assert deff_wilson_route(2000, 40, 50, True) == "wilson_deff"  # exactly 50 per case
    assert deff_wilson_route(2040, 40, 51, True) == "rows_per_case_above_grid"
    assert deff_wilson_route(6, 1, 6, False) == "not_estimable"
    below, _, _ = _clustered_cell(MIN_CASES_DEFF_WILSON - 1)
    at, ind, ids = _clustered_cell(MIN_CASES_DEFF_WILSON)
    # E11 repair 3 (DEC-75 (c)): four cases print no interval (at 3302d59 the cluster
    # bootstrap printed one with its tier)
    assert below.number.method == "none"
    assert below.number.not_estimable_reason == "fewer_than_five_cases"
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


def _coverage_script():
    sys.path.insert(0, str(REPO / "scripts"))
    import coverage_bar

    return coverage_bar


def test_every_committed_grid_row_at_its_process_of_30_cases_or_more_is_at_or_above_the_bar():
    """E11 repair 1 (lenses FA-B1, RG-B2); renamed in E11 repair 2 (lens 2 FA-N1: the old
    name asserted that no unannotated cell was left below the bar, and the lens measured
    an off-grid shape at this process at 0.8285). It inspects the committed JSON only:
    every printed grid row (``route == wilson_deff``) of the constant-setting process
    (TAU2 0.5, truth 0.5 / 0.9) with at least the threshold's cases covers at or above
    0.90, and the threshold (30 in the committed run) is at most
    ``VERY_LOW_PRECISION_UNITS``. The mark on every clustered cell is
    ``tests/test_e11_repair2.py``'s."""
    coverage_bar = _coverage_script()
    data = json.loads(COVERAGE.read_text(encoding="utf-8"))
    assert data["bar"] == 0.9 and data["reps"] == 4000 and data["seed"] == 20261002
    assert data["version"].startswith("coverage_bar.py --deff-wilson v2")
    assert len(data["rows"]) == 1000
    assert (data["max_case_share"], data["max_rows_per_case"]) == (
        MAX_CASE_SHARE_DEFF_WILSON,
        MAX_ROWS_PER_CASE_DEFF_WILSON,
    )
    threshold = data["min_cases_meeting_bar"]
    assert threshold == coverage_bar.deff_threshold(data["rows"]) == 30
    assert threshold <= VERY_LOW_PRECISION_UNITS
    for r in data["rows"]:
        assert r["route"] == deff_wilson_route(
            r["n_rows"], r["u_cases"], r["largest_case_rows"], True
        ), r["index"]
    printed = [r for r in data["rows"] if r["route"] == "wilson_deff"]
    setting = [r for r in printed if r["sets_constant"]]
    assert all(r["coverage"] >= 0.9 for r in setting if r["u_cases"] >= threshold)
    assert min(r["coverage"] for r in setting if r["u_cases"] >= threshold) == 0.90675
    below = [r for r in setting if r["coverage"] < 0.9]
    assert len(below) == 12 and max(r["u_cases"] for r in below) == 20
    # the recorded rows below the bar at 30 cases or more (printed with the mark d since
    # E11 repair 2)
    recorded = [r for r in printed if not r["sets_constant"] and r["u_cases"] >= 30]
    assert (len(recorded), sum(r["coverage"] < 0.9 for r in recorded)) == (162, 26)
    assert min(r["coverage"] for r in recorded) == 0.7635
    # the shapes the case-share bound sends to the bootstrap
    share = [r for r in data["rows"] if r["route"] == "case_share_above_grid"]
    assert len(share) == 408 and min(r["coverage"] for r in share) == 0.13725


def test_t7_prints_the_committed_table():
    data = json.loads(COVERAGE.read_text(encoding="utf-8"))
    printed = [r for r in data["rows"] if r["route"] == "wilson_deff"]
    groups = (
        lambda r: r["tau2"] == 0.5 and r["truth"] in (0.5, 0.9),
        lambda r: r["tau2"] == 0.8 and r["truth"] in (0.5, 0.9),
        lambda r: r["tau2"] == 0.5 and r["truth"] > 0.9,
        lambda r: r["tau2"] == 0.8 and r["truth"] > 0.9,
    )
    expected = {}
    for u in sorted({r["u_cases"] for r in printed}):
        cells = []
        for g in groups:
            sel = [r["coverage"] for r in printed if r["u_cases"] == u and g(r)]
            cells.append(f"{min(sel):.3f} ({len(sel)})")
        expected[u] = cells
    conv = (REPO / "design" / "conventions_T7.md").read_text(encoding="utf-8")
    section = conv[conv.index("### Design-effect Wilson interval") :]
    section = section[: section.index("\n## ")]
    table = {}
    for line in section.splitlines():
        m = re.match(r"^\| (\d+) \| (.*) \|$", line)
        if m:
            table[int(m.group(1))] = m.group(2).split(" | ")
    assert table == expected
    for literal in ("0.907", "0.808", "0.763", "0.137", "26 of the 162", "Twelve printed rows"):
        assert literal in section, literal
    # E11 repair 2 (lens 2 RG-N1): the prose's lowest recorded figure is the table's own
    # printing of the same row (0.7635 prints 0.763), not a second rounding
    recorded = [r for r in printed if not r["sets_constant"] and r["u_cases"] >= 30]
    lowest = f"{min(r['coverage'] for r in recorded):.3f}"
    assert f"(lowest {lowest}: 30 cases of 50 rows" in " ".join(section.split())
    assert "0.764" not in section


@pytest.mark.slow
def test_the_coverage_script_rewrites_a_sample_of_the_committed_rows():
    """Every row has a generator of its own (``default_rng([seed, index])``), so a sample
    re-runs alone: every 25th row (40 rows, about 3 s) equals the committed row exactly."""
    coverage_bar = _coverage_script()
    committed = json.loads(COVERAGE.read_text(encoding="utf-8"))["rows"]
    only = set(range(0, len(committed), 25))
    again = coverage_bar.deff_rows(4000, only=only)
    assert [r["index"] for r in again] == sorted(only)
    for r in again:
        assert r == committed[r["index"]], r["index"]


def _clustered_run_cohort() -> tuple[dict, dict]:
    cols = make_cohort(n=360, with_case_id=True)
    cols["case_id"] = [f"c{i // 3:05d}" for i in range(360)]
    # a site of 2 cases, one of 4 and the rest: cells on both sides of the threshold
    cols["site"] = ["S9"] * 6 + ["S8"] * 12 + ["S1", "S1", "S1", "S2", "S2", "S2"] * 57
    crit = make_criteria(criteria=[], clustering={"unit": "case_id", "declared_by": "t"})
    return cols, crit


def test_accept_every_printed_cell_under_the_committed_threshold_carries_its_tier():
    """The brief's Accept line, read against the committed run (E11 repair 1): a printed
    clustered proportion of fewer cases than the coverage run's threshold (30) carries its
    tier annotation, whichever interval it prints; a ``wilson_deff`` cell has at least
    five cases; every other cell names its route."""
    threshold = json.loads(COVERAGE.read_text(encoding="utf-8"))["min_cases_meeting_bar"]
    cols, crit = _clustered_run_cohort()
    doc = assemble(cols, copy.deepcopy(crit))
    seen = {"wilson_deff": 0, "cluster_bootstrap_percentile": 0, "fewer_than_five_cases": 0}
    tiers = {"not_evaluable_shown_for_transparency", "very_low_precision"}
    for row in doc["subgroups"]:
        for metric in ("sensitivity", "specificity", "ppv", "npv", "accuracy"):
            cell = row["metrics"]["op1"][metric]
            num = cell["number"]
            if num["n_cases"] < 5:
                # E11 repair 3 (DEC-75 (c)): sites S9 (2 cases) and S8 (4 cases) print no
                # interval; at 3302d59 they printed the cluster bootstrap with a tier
                assert num["ci_lo"] is None, (row["level"], metric)
                if num["not_estimable_reason"] == "fewer_than_five_cases":
                    seen["fewer_than_five_cases"] += 1
            if num["ci_lo"] is None:
                continue
            seen[num["method"]] += 1
            route = cell["detail"]["design_effect"]["route"]
            if num["method"] == "wilson_deff":
                assert num["n_cases"] >= MIN_CASES_DEFF_WILSON, (row["level"], metric)
                assert route == "wilson_deff"
            else:
                assert num["method"] == "cluster_bootstrap_percentile"
                assert route == "below_coverage_bar"
            if num["n_cases"] < threshold:
                assert tiers & set(num["flags"]), (row["level"], metric, num["flags"])
    assert seen["wilson_deff"] > 0 and seen["fewer_than_five_cases"] > 0


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
