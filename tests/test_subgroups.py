"""Day 5 (E5) - ``stats.subgroups``: per-level metrics, differences, fairness gaps.

What is proved here, and against what:

* **F6** (R2 section 9): sensitivity by site ``[45,5], [38,12], [27,3]`` -> 0.90 / 0.76 /
  0.90; chi-square 4.6327, df 2, p 0.0986; Fisher site 1 vs site 2 p 0.1084; Holm on
  ``[0.012, 0.04, 0.30]`` -> ``[0.036, 0.08, 0.30]``. Oracles: the R2 figures themselves,
  ``scipy.stats.chi2_contingency`` / ``fisher_exact`` and
  ``statsmodels.stats.multitest.multipletests(method="holm")``.
* **F14 applied to differences**: the ``fixtures/newcombe_table2.json`` worked examples,
  driven through ``diff_vs_complement`` on a two-level attribute whose 2x2 tables reproduce
  each pair, to 4 dp. The fixture's provenance is
  **[unverified against the primary PDF]** (transcribed from a secondary source, see the
  fixture) and that status is carried here, not resolved. Plus one ``diff_vs_complement``
  case computed by hand from the Newcombe-10 formula in this file and frozen today (D1 F14:
  "computed on E-Day 5 and frozen then").
* **F8** tiers: Wilson half-width at p = 0.9 for n = 50 / 100 / 300 -> 0.0851 / 0.0596 /
  0.0341, and the R2 section 3.3 tier flags on the row and its Numbers.
* **F18-style injection**: n = 5,000, AUROC lowered by 0.06 in one level of one attribute.
  Measured first, then asserted below the measurement (see the test's docstring).
* The conventions: the Unknown row, the reference rule, the complement, X1 (no
  ``diff_vs_overall``), DEC-10 (every proportion is Wilson or the cluster bootstrap), the
  clustered refusals, the schema, the no-verdict-words grep, the scipy-free import.
"""

from __future__ import annotations

import copy
import importlib
import json
import math
import pathlib
import re
import sys
from statistics import NormalDist
from typing import Any

import jsonschema
import numpy as np
import pytest

from conftest import make_cohort, make_criteria
from proofpack.errors import HaltError
from proofpack.io import schema as schema_mod
from proofpack.io.declare import validate_dict
from proofpack.io.schema import UNKNOWN_LEVEL
from proofpack.resources import load_json_schema
from proofpack.stats import subgroups as subgroups_module
from proofpack.stats.bootstrap import (
    LOW_PRECISION_UNITS,
    MAX_FROZEN_VARIANCE_SHARE,
    VERY_LOW_PRECISION_UNITS,
    BootstrapPolicy,
    ClusterPlan,
    clustered_by_case,
    clustered_flat,
)
from proofpack.stats.discrimination import delong_variance, unpaired_delong
from proofpack.stats.number import FLAGS, METHODS, NOT_ESTIMABLE_REASONS, Number
from proofpack.stats.proportions import newcombe10_bounds
from proofpack.stats.subgroups import (
    AUROC_EVALUABLE_CLASS,
    DEFAULT_AGE_BANDS,
    EXPLORATORY,
    FISHER_EXPECTED_BELOW,
    _homogeneity_test,
    age_band_labels,
    band_ages,
    holm,
    subgroup_analysis,
)

pytestmark = pytest.mark.day5

REPO = pathlib.Path(__file__).resolve().parent.parent
_ND = NormalDist()
Z = _ND.inv_cdf(0.975)
POLICY = BootstrapPolicy(n_resamples=200, seed=20240101)


def approx4(a: float, b: float) -> None:
    assert a == pytest.approx(b, abs=5e-5), (a, b)


# ---------------------------------------------------------------------------- helpers


def run(
    cols: dict[str, list[Any]],
    crit: dict[str, Any] | None = None,
    *,
    policy: BootstrapPolicy = POLICY,
    **kw: Any,
):
    """Validate the columns and declarations the day-1 way and run the analysis."""
    decl = validate_dict(crit if crit is not None else make_criteria())
    table = schema_mod.validate(schema_mod.table_from_columns(cols), period=None)
    mask, _ = schema_mod.analysis_mask(table, decl.indeterminate_values)
    return subgroup_analysis(table, decl, mask, policy=policy, **kw)


def criteria_for(attributes: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    crit = make_criteria(**overrides)
    crit["subgroups"] = attributes
    return crit


def counts_cohort(levels: dict[str, tuple[int, int, int, int]], attribute: str = "site"):
    """A cohort whose per-level 2x2 tables are exactly ``(tp, fn, fp, tn)``.

    Scores are placed so that the operating point ``>= 0.5`` reproduces the counts and
    each level has a spread of scores (so AUROC is defined); positives called positive
    get scores in (0.5, 1), negatives called negative in (0, 0.5).
    """
    y, s, a = [], [], []
    rng = np.random.default_rng(7)
    for level, (tp, fn, fp, tn) in levels.items():
        for k, (label, lo, hi) in enumerate(
            (("1", 0.5, 1.0), ("1", 0.0, 0.5), ("0", 0.5, 1.0), ("0", 0.0, 0.5))
        ):
            count = (tp, fn, fp, tn)[k]
            y += [label] * count
            s += (lo + (hi - lo) * rng.random(count)).round(6).tolist()
            a += [level] * count
    return {"y_true": y, "score": s, attribute: a}


def walk_numbers(node: Any, path: str = "$"):
    """Yield every serialised Number in a JSON-ready structure with its path."""
    if isinstance(node, dict):
        if {"est", "ci_lo", "ci_hi", "method", "not_estimable_reason"} <= set(node):
            yield path, node
            return
        for k, v in node.items():
            yield from walk_numbers(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_numbers(v, f"{path}[{i}]")


def walk_dict_keys(node: Any):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from walk_dict_keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_dict_keys(v)


def walk_keys_and_strings(node: Any):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from walk_keys_and_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_keys_and_strings(v)
    elif isinstance(node, str):
        yield node


PROPORTION_KEYS = {
    "sensitivity",
    "specificity",
    "ppa",
    "npa",
    "ppv",
    "npv",
    "accuracy",
    "selection_rate",
}


# ------------------------------------------------------------------------------- F6


@pytest.mark.fixture
def test_f6_chi_square_homogeneity_of_sensitivity_across_three_sites():
    """R2 section 9 F6: 0.90 / 0.76 / 0.90; chi-square 4.6327, df 2, p 0.0986 - footnote only."""
    rep = run(
        counts_cohort(
            {"site1": (45, 5, 10, 40), "site2": (38, 12, 10, 40), "site3": (27, 3, 10, 40)}
        ),
        criteria_for(
            [
                {
                    "attribute": "site",
                    "prespecified": True,
                    "source": "SAP",
                    "reference_level": "largest",
                }
            ]
        ),
    )
    for level, se in (("site1", 0.90), ("site2", 0.76), ("site3", 0.90)):
        approx4(rep.row("site", level)["metrics"]["op1"]["sensitivity"]["number"]["est"], se)
    tests = rep.attribute("site")["heterogeneity"]["tests"]
    se_test = next(t for t in tests if t["metric"] == "sensitivity")
    assert se_test["test"] == "chi2_homogeneity" and se_test["df"] == 2 and se_test["n_levels"] == 3
    approx4(se_test["statistic"], 4.6327)
    approx4(se_test["p_raw"], 0.0986)
    # the same figures straight from scipy, so the fixture is not only self-consistent
    from scipy.stats import chi2_contingency

    stat, p, dof, _ = chi2_contingency([[45, 5], [38, 12], [27, 3]], correction=False)
    approx4(se_test["statistic"], float(stat))
    approx4(se_test["p_raw"], float(p))
    # every level's specificity is 40/50, so the specificity test sees no heterogeneity
    sp_test = next(t for t in tests if t["metric"] == "specificity")
    assert sp_test["statistic"] == pytest.approx(0.0, abs=1e-12) and sp_test[
        "p_raw"
    ] == pytest.approx(1.0)


@pytest.mark.fixture
def test_f6_fisher_exact_site1_vs_site2():
    """F6: Fisher site 1 vs site 2, p 0.1084.

    R2 computed this as a pairwise Fisher on ``[[45,5],[38,12]]``. Under the module's
    own rule (Fisher only when an expected cell is below 5 and there are exactly two
    levels) that pair takes the chi-square, because its smallest expected cell is 8.5;
    the Fisher branch is exercised on it by lifting the threshold, and the rule itself
    is pinned in the next test.
    """
    entry = _homogeneity_test([(45, 5), (38, 12)], fisher_below=math.inf)
    assert entry["test"] == "fisher_exact" and entry["statistic"] is None and entry["df"] is None
    approx4(entry["p_raw"], 0.1084)
    from scipy.stats import fisher_exact

    approx4(entry["p_raw"], float(fisher_exact([[45, 5], [38, 12]])[1]))
    default = _homogeneity_test([(45, 5), (38, 12)])
    assert default["test"] == "chi2_homogeneity" and default["min_expected"] == pytest.approx(8.5)


def test_fisher_replaces_chi_square_only_for_two_levels_with_a_small_expected_cell():
    assert FISHER_EXPECTED_BELOW == 5.0
    small = _homogeneity_test([(9, 1), (6, 4)])  # expected failures 2.5
    assert small["test"] == "fisher_exact" and small["min_expected"] < 5
    three = _homogeneity_test([(9, 1), (6, 4), (7, 3)])  # small expected, three levels
    assert three["test"] == "chi2_homogeneity" and three["min_expected"] < 5 and three["df"] == 2
    one = _homogeneity_test([(9, 1)])
    assert one["test"] is None and one["not_estimable_reason"] == "insufficient_levels"
    saturated = _homogeneity_test([(9, 0), (6, 0)])
    assert saturated["not_estimable_reason"] == "boundary_estimate"


@pytest.mark.fixture
def test_f6_holm_adjustment_matches_the_fixture_and_statsmodels():
    """F6: Holm on [0.012, 0.04, 0.30] -> [0.036, 0.08, 0.30]; and statsmodels on random sets."""
    got = holm([0.012, 0.04, 0.30])
    for a, b in zip(got, [0.036, 0.08, 0.30], strict=True):
        approx4(a, b)
    from statsmodels.stats.multitest import multipletests

    rng = np.random.default_rng(5)
    for m in (1, 2, 3, 5, 8):
        for _ in range(20):
            p = rng.random(m) ** rng.uniform(0.5, 4.0)
            ours = holm(p.tolist())
            theirs = multipletests(p, method="holm")[1]
            assert np.allclose(ours, theirs, atol=1e-12), (p, ours, theirs)
    # unsorted input keeps its order, and ties are handled the way statsmodels does
    p = [0.3, 0.012, 0.04, 0.04]
    assert np.allclose(holm(p), multipletests(p, method="holm")[1])


def test_the_footnote_is_exploratory_with_no_status_key_beside_any_p_value():
    rep = run(
        counts_cohort({"a": (45, 5, 10, 40), "b": (38, 12, 10, 40), "c": (27, 3, 10, 40)}),
        criteria_for([{"attribute": "site", "prespecified": False, "reference_level": "largest"}]),
    )
    foot = rep.attribute("site")["heterogeneity"]
    assert foot["label"] == EXPLORATORY
    assert (
        foot["sentence"]
        == "exploratory; no conclusion about subgroup consistency is drawn from this test"
    )
    assert foot["adjustment"] == "holm" and foot["family_size"] == 2
    for t in foot["tests"]:
        assert "status" not in t and "verdict" not in t
        assert t["p_holm"] >= t["p_raw"]
    assert "status" not in set(walk_dict_keys(foot))
    # p-values are never Numbers: nothing in the footnote is a rendered quantity with a CI
    assert list(walk_numbers(foot)) == []


def test_holm_is_one_family_per_attribute_across_operating_points_and_both_metrics():
    crit = criteria_for(
        [{"attribute": "site", "prespecified": True, "source": "s", "reference_level": "largest"}]
    )
    crit["operating_points"].append(
        {
            "id": "op2",
            "threshold": 0.3,
            "rule": ">=",
            "provenance": "prespecified_sap",
            "source": "t",
        }
    )
    rep = run(make_cohort(n=600), crit)
    foot = rep.attribute("site")["heterogeneity"]
    assert foot["family_size"] == 4 == len(foot["tests"])
    raw = [t["p_raw"] for t in foot["tests"]]
    assert [t["p_holm"] for t in foot["tests"]] == pytest.approx(holm(raw))


def test_the_module_imports_and_the_footnote_degrades_with_scipy_hidden(monkeypatch):
    """``import proofpack.stats.subgroups`` with scipy absent; the footnote says so, typed."""
    for name in list(sys.modules):
        if name == "scipy" or name.startswith("scipy."):
            monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setitem(sys.modules, "scipy", None)
    monkeypatch.setitem(sys.modules, "scipy.stats", None)
    monkeypatch.delitem(sys.modules, "proofpack.stats.subgroups", raising=False)
    mod = importlib.import_module("proofpack.stats.subgroups")
    entry = mod._homogeneity_test([(45, 5), (38, 12), (27, 3)])
    assert entry["not_estimable_reason"] == "scipy_unavailable"
    assert entry["p_raw"] is None and entry["p_holm"] is None and entry["test"] is None
    foot = mod.heterogeneity_footnote(
        {"op1": {"sensitivity": [(45, 5), (38, 12)]}}, clustering_route="none"
    )
    assert foot["tests"][0]["not_estimable_reason"] == "scipy_unavailable"
    assert foot["family_size"] == 0 and foot["label"] == "exploratory"
    monkeypatch.undo()
    importlib.reload(subgroups_module)


def test_no_module_level_scipy_import_in_subgroups():
    src = (REPO / "src/proofpack/stats/subgroups.py").read_text(encoding="utf-8")
    top_level = [line for line in src.splitlines() if re.match(r"^(from|import)\s+scipy", line)]
    assert top_level == []


# ---------------------------------------------------------------------------- F14


def newcombe_fixture() -> dict[str, Any]:
    fx = json.loads((REPO / "fixtures/newcombe_table2.json").read_text(encoding="utf-8"))
    assert fx["provenance"]["status"] == "[unverified against the primary PDF]"
    return fx


@pytest.mark.fixture
def test_f14_newcombe_table_ii_examples_drive_diff_vs_complement():
    """F14 through ``diff_vs_complement``: a two-level attribute whose per-level 2x2 tables
    reproduce each of Newcombe's Table II pairs as *sensitivity of level A minus
    sensitivity of its complement*, asserting the method-10 bounds to 4 dp.

    Provenance of the expected values: ``fixtures/newcombe_table2.json``, status
    **[unverified against the primary PDF]** - transcribed from a secondary source that
    recasts Newcombe 1998 Table II; the primary PDF was unreachable from the build
    environment. That status is carried here and is not resolved by this test.
    """
    fx = newcombe_fixture()
    for ex in fx["examples"]:
        k1, n1, k2, n2 = ex["k1"], ex["n1"], ex["k2"], ex["n2"]
        # level A: k1 of n1 positives called positive; level B (= A's complement): k2 of n2
        cols = counts_cohort({"A": (k1, n1 - k1, 15, 35), "B": (k2, n2 - k2, 15, 35)})
        rep = run(
            cols,
            criteria_for(
                [{"attribute": "site", "prespecified": True, "source": "t", "reference_level": "B"}]
            ),
        )
        cell = rep.row("site", "A")["diff_vs_complement"]["op1"]["sensitivity"]
        num = cell["number"]
        assert num["method"] == "newcombe10" and cell["analytic_status"] == "used"
        approx4(num["est"], ex["difference"])
        approx4(num["ci_lo"], ex["method10"]["lower"])
        approx4(num["ci_hi"], ex["method10"]["upper"])
        # with two levels the complement of A is B, so diff_vs_reference (ref = B) agrees
        ref = rep.row("site", "A")["diff_vs_reference"]["op1"]["sensitivity"]["number"]
        assert ref["ci_lo"] == num["ci_lo"] and ref["ci_hi"] == num["ci_hi"]


def wilson_by_hand(k: int, n: int) -> tuple[float, float]:
    """Wilson score bounds written out from the formula, not imported."""
    p = k / n
    centre = (2 * n * p + Z * Z) / (2 * (n + Z * Z))
    radius = Z * math.sqrt(Z * Z + 4 * n * p * (1 - p)) / (2 * (n + Z * Z))
    return centre - radius, centre + radius


def newcombe10_by_hand(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson_by_hand(k1, n1)
    l2, u2 = wilson_by_hand(k2, n2)
    d = p1 - p2
    return (
        d,
        d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2),
        d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2),
    )


#: FROZEN on build day 5 (D1 F14: "expected values computed on E-Day 5 and frozen then").
#: Level A: 30 of 40 reference-positive rows called positive. Complement (levels B and C
#: together, 100 of 120): d = 0.75 - 0.83333 = -0.08333; Wilson(30/40) = (0.598060,
#: 0.858129), Wilson(100/120) = (0.756547, 0.889440); lower = d - sqrt((0.75 - 0.598060)^2
#: + (0.889440 - 0.833333)^2) = -0.245301; upper = d + sqrt((0.858129 - 0.75)^2 +
#: (0.833333 - 0.756547)^2) = 0.049286.
F14_COMPLEMENT_FROZEN = {"est": -0.0833, "ci_lo": -0.2453, "ci_hi": 0.0493}


@pytest.mark.fixture
def test_f14_diff_vs_complement_hand_computed_and_frozen():
    """A three-level attribute: the complement of A is B and C *together* (not B alone)."""
    cols = counts_cohort({"A": (30, 10, 10, 50), "B": (60, 10, 20, 70), "C": (40, 10, 10, 50)})
    rep = run(
        cols,
        criteria_for(
            [{"attribute": "site", "prespecified": True, "source": "t", "reference_level": "B"}]
        ),
    )
    num = rep.row("site", "A")["diff_vs_complement"]["op1"]["sensitivity"]["number"]
    d, lo, hi = newcombe10_by_hand(30, 40, 100, 120)
    assert (round(d, 4), round(lo, 4), round(hi, 4)) == (
        F14_COMPLEMENT_FROZEN["est"],
        F14_COMPLEMENT_FROZEN["ci_lo"],
        F14_COMPLEMENT_FROZEN["ci_hi"],
    )
    approx4(num["est"], F14_COMPLEMENT_FROZEN["est"])
    approx4(num["ci_lo"], F14_COMPLEMENT_FROZEN["ci_lo"])
    approx4(num["ci_hi"], F14_COMPLEMENT_FROZEN["ci_hi"])
    assert num["method"] == "newcombe10" and num["n"] == 40
    # and the reference difference is A minus B alone: 30/40 - 60/70
    ref = rep.row("site", "A")["diff_vs_reference"]["op1"]["sensitivity"]["number"]
    approx4(ref["est"], 30 / 40 - 60 / 70)
    lo_ref, hi_ref = newcombe10_bounds(30, 40, 60, 70)
    approx4(ref["ci_lo"], lo_ref)
    approx4(ref["ci_hi"], hi_ref)


# ----------------------------------------------------------------------------- F8


@pytest.mark.fixture
def test_f8_wilson_half_widths_and_the_tier_flags():
    """F8: p = 0.9, n = 50 / 100 / 300 -> half-width 0.0851 / 0.0596 / 0.0341, tiers by n."""
    cols = counts_cohort(
        {
            "n50": (45, 5, 10, 40),
            "n100": (90, 10, 10, 40),
            "n300": (270, 30, 10, 40),
            "n20": (18, 2, 10, 40),  # 10 <= units < 30 on the sensitivity cell
            "n8": (7, 1, 10, 40),  # units < 10
            "few_events": (3, 1, 10, 40),
            "wide": (9, 1, 10, 40),  # half-width 0.19 > 0.10
        }
    )
    rep = run(
        cols,
        criteria_for(
            [{"attribute": "site", "prespecified": True, "source": "t", "reference_level": "n300"}]
        ),
    )
    for level, hw in (("n50", 0.0851), ("n100", 0.0596), ("n300", 0.0341)):
        num = rep.row("site", level)["metrics"]["op1"]["sensitivity"]["number"]
        approx4((num["ci_hi"] - num["ci_lo"]) / 2, hw)
        assert num["method"] == "wilson"
        assert "imprecise" not in num["flags"]
        assert num["est"] == pytest.approx(0.9)
    se = lambda level: rep.row("site", level)["metrics"]["op1"]["sensitivity"]["number"]  # noqa: E731
    assert "very_low_precision" in se("n20")["flags"]
    assert "not_evaluable_shown_for_transparency" in se("n8")["flags"]
    assert "imprecise" in se("wide")["flags"]
    # the row tier counts the level's rows and its events (R2 section 3.3)
    assert rep.row("site", "n300")["tier"] is None
    assert rep.row("site", "few_events")["tier"] == "very_low_precision"  # 54 rows, 4 events
    assert rep.row("site", "few_events")["events"] == 4
    assert LOW_PRECISION_UNITS == 10 and VERY_LOW_PRECISION_UNITS == 30


def test_tiers_count_resampling_units_not_rows_under_clustering():
    """Two rows per case: 40 rows of a level are 20 cases -> very low precision."""
    n = 200
    cols = make_cohort(n=n, with_case_id=True)
    cols["site"] = ["S1"] * 40 + ["S2"] * (n - 40)
    dup = {k: [v[i // 2] for i in range(2 * n)] for k, v in cols.items()}
    dup["row_id"] = [f"r{i:05d}" for i in range(2 * n)]
    crit = criteria_for(
        [{"attribute": "site", "prespecified": True, "source": "t", "reference_level": "S2"}],
        clustering={"unit": "case_id", "declared_by": "t"},
    )
    rep = run(dup, crit)
    row = rep.row("site", "S1")
    assert row["n"] == 80 and row["n_units"] == 40
    assert row["tier"] is None  # 40 cases
    cols["site"] = ["S1"] * 20 + ["S2"] * (n - 20)
    dup = {k: [v[i // 2] for i in range(2 * n)] for k, v in cols.items()}
    dup["row_id"] = [f"r{i:05d}" for i in range(2 * n)]
    row = run(dup, crit).row("site", "S1")
    assert row["n"] == 40 and row["n_units"] == 20 and row["tier"] == "very_low_precision"


# --------------------------------------------------------------------------- injection


def injected_cohort(seed: int, n: int, sep: float, sep_injected: float):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.3).astype(int)
    race = rng.choice(["A", "B", "C"], size=n)
    s = np.where(race == "B", sep_injected, sep)
    z = rng.normal(0.0, 1.0, n) + s * y - s / 2
    score = 1.0 / (1.0 + np.exp(-z))
    return {
        "y_true": ["1" if v else "0" for v in y.tolist()],
        "score": [round(float(v), 6) for v in score.tolist()],
        "race": race.tolist(),
    }


@pytest.mark.fixture
@pytest.mark.slow
def test_f18_injected_auroc_drop_is_recovered_in_at_least_90_percent_of_50_seeds():
    """n = 5,000; AUROC lowered by 0.06 in level B of ``race`` (three equal levels).

    Base separation 1.5 gives AUROC Phi(1.5 / sqrt 2) = 0.8556; level B's separation is
    set so its AUROC is 0.7956. Measured before the assertion was written (build day 5,
    seeds 20260915..20260964, B = 200):

    * B's ``diff_vs_complement`` AUROC interval excluded 0 in **49 of 50** seeds (0.98).
    * A's and C's intervals covered 0 in **19 of 50** (0.38) each - and that is right:
      their complement *contains* the injected level, so their true difference is
      +0.0292, not 0 (X1: the comparison is against the complement, never the overall).
      They covered that true difference in 49 of 50 (0.98).
    * B covered its true difference (-0.06 exactly, its complement being uninjected) in
      43 of 50 (0.86) at 50 seeds; at 300 seeds with the DeLong arithmetic alone the
      coverage was 0.933 vs the complement and 0.943 vs the reference - the 0.86 was
      50-seed noise.

    Asserted: B excludes 0 in >= 90 % (measured 0.98); A and C cover their *true*
    difference in >= 85 % (measured 0.98); and A and C cover 0 in <= 60 % (measured
    0.38) so the X1 property cannot quietly invert.
    """
    n, seeds = 5000, 50
    sep = 1.5
    base = _ND.cdf(sep / math.sqrt(2))
    sep_inj = math.sqrt(2) * _ND.inv_cdf(base - 0.06)

    def pair(s1: float, s2: float) -> float:  # P(positive of s1 > negative of s2)
        return _ND.cdf((s1 / 2 + s2 / 2) / math.sqrt(2))

    def complement_auc(s_other: tuple[float, float]) -> float:
        s1, s2 = s_other
        return 0.25 * (pair(s1, s1) + pair(s2, s2) + pair(s1, s2) + pair(s2, s1))

    seps = {"A": sep, "B": sep_inj, "C": sep}
    truth = {
        lv: _ND.cdf(seps[lv] / math.sqrt(2))
        - complement_auc(tuple(seps[o] for o in "ABC" if o != lv))
        for lv in "ABC"
    }
    assert truth["B"] == pytest.approx(-0.06, abs=1e-9)
    crit = criteria_for(
        [{"attribute": "race", "prespecified": True, "source": "t", "reference_level": "largest"}]
    )
    excludes_zero = dict.fromkeys("ABC", 0)
    covers_zero = dict.fromkeys("ABC", 0)
    covers_truth = dict.fromkeys("ABC", 0)
    for seed in range(seeds):
        rep = run(
            injected_cohort(20260915 + seed, n, sep, sep_inj),
            crit,
            policy=BootstrapPolicy(200, seed),
        )
        for lv in "ABC":
            num = rep.row("race", lv)["diff_vs_complement"]["auroc"]["number"]
            assert num["method"] == "delong_wald"
            lo, hi = num["ci_lo"], num["ci_hi"]
            excludes_zero[lv] += lo > 0 or hi < 0
            covers_zero[lv] += lo <= 0 <= hi
            covers_truth[lv] += lo <= truth[lv] <= hi
    assert excludes_zero["B"] / seeds >= 0.90, excludes_zero
    for lv in "AC":
        assert covers_truth[lv] / seeds >= 0.85, (lv, covers_truth)
        assert covers_zero[lv] / seeds <= 0.60, (lv, covers_zero)


# ------------------------------------------------------------------- unpaired DeLong


def placement_variance(scores: np.ndarray, pos: np.ndarray) -> tuple[float, float]:
    """DeLong 1988 from the placement values, written out: V10_i = mean_j psi(x_i, y_j)."""
    x, y = scores[pos], scores[~pos]
    m, n = x.shape[0], y.shape[0]
    psi = (x[:, None] > y[None, :]).astype(float) + 0.5 * (x[:, None] == y[None, :])
    auc = psi.mean()
    v10 = psi.mean(axis=1)
    v01 = psi.mean(axis=0)
    return float(auc), float(v10.var(ddof=1) / m + v01.var(ddof=1) / n)


def test_unpaired_delong_difference_is_the_sum_of_two_oracled_variances():
    rng = np.random.default_rng(3)
    for _ in range(5):
        n_a, n_b = int(rng.integers(40, 120)), int(rng.integers(40, 120))
        pa = rng.random(n_a) < 0.4
        pb = rng.random(n_b) < 0.4
        sa = rng.normal(0, 1, n_a) + 1.2 * pa
        sb = rng.normal(0, 1, n_b) + 0.8 * pb
        res = unpaired_delong(sa, pa, sb, pb)
        auc_a, var_a = placement_variance(sa, pa)
        auc_b, var_b = placement_variance(sb, pb)
        assert res.auroc_a == pytest.approx(auc_a) and res.auroc_b == pytest.approx(auc_b)
        assert res.variance_a == pytest.approx(var_a, rel=1e-9)
        assert res.variance_b == pytest.approx(var_b, rel=1e-9)
        assert res.variance_difference == pytest.approx(var_a + var_b, rel=1e-12)
        assert res.variance_a == pytest.approx(delong_variance(sa, pa)[1])
        se = math.sqrt(var_a + var_b)
        assert res.difference.method == "delong_wald"
        assert res.difference.ci_lo == pytest.approx(auc_a - auc_b - Z * se)
        assert res.difference.ci_hi == pytest.approx(auc_a - auc_b + Z * se)
        assert res.z == pytest.approx((auc_a - auc_b) / se)
        from scipy.stats import norm

        assert res.p_value == pytest.approx(2 * norm.sf(abs(res.z)), rel=1e-9)


def test_the_auroc_difference_carries_z_and_p_as_detail_never_as_a_verdict():
    rep = run(make_cohort(n=600))
    cell = rep.row("sex", "F")["diff_vs_reference"]["auroc"]
    assert cell["number"]["method"] == "delong_wald"
    detail = cell["detail"]
    assert set(detail) == {
        "method",
        "variance_a",
        "variance_b",
        "variance_difference",
        "z",
        "p_value",
    }
    assert detail["method"] == "unpaired_delong"
    assert detail["variance_difference"] == pytest.approx(
        detail["variance_a"] + detail["variance_b"]
    )
    assert "status" not in cell and "status" not in detail


# --------------------------------------------------------------- conventions: the rows


def test_every_recognised_attribute_is_tabulated_and_undeclared_ones_are_exploratory():
    cols = make_cohort(n=300)
    cols["race"] = (["W", "B", "A"] * 100)[:300]
    cols["attr_scanner"] = (["GE", "Siemens"] * 150)[:300]
    rep = run(cols)  # sex, age, site declared; race and attr_scanner are not
    attrs = {a["attribute"]: a for a in rep.attributes}
    assert set(attrs) == {"age", "sex", "site", "race", "attr_scanner"}
    assert attrs["sex"]["prespecified"] is True and attrs["sex"]["source"] == "test"
    assert attrs["site"]["prespecified"] is False and attrs["site"]["declared"] is True
    for name in ("race", "attr_scanner"):
        assert attrs[name]["prespecified"] is False and attrs[name]["source"] == EXPLORATORY
        assert attrs[name]["declared"] is False and attrs[name]["reference_rule"] in (
            "largest",
            "largest_tie_first_in_level_order",
        )
    for row in rep.rows:
        assert row["prespecified"] == attrs[row["attribute"]]["prespecified"]
        assert row["source"] == attrs[row["attribute"]]["source"]


def test_age_is_banded_by_the_declared_bands_half_open_and_labelled_lo_hi():
    labels, missing, outside = band_ages(
        np.array([0, 39.9, 40, 64, 65, 79.5, 80, 199, 200, np.nan, -1]),
        [[0, 40], [40, 65], [65, 80], [80, 200]],
    )
    assert labels.tolist() == [
        "0-40",
        "0-40",
        "40-65",
        "40-65",
        "65-80",
        "65-80",
        "80-200",
        "80-200",
        UNKNOWN_LEVEL,
        UNKNOWN_LEVEL,
        UNKNOWN_LEVEL,
    ]
    assert (missing, outside) == (1, 2)
    assert age_band_labels([[18, 39.5]]) == ["18-39.5"]
    rep = run(make_cohort(n=300))
    block = rep.attribute("age")
    assert block["bands_source"] == "declared" and block["bands"] == [
        [0, 40],
        [40, 65],
        [65, 80],
        [80, 200],
    ]
    assert block["reference_level"] == "40-65" and block["reference_rule"] == "declared"
    assert block["level_order"] == ["0-40", "40-65", "65-80", "80-200"]


def test_age_falls_back_to_the_d1_default_bands_when_not_declared_and_says_so():
    assert DEFAULT_AGE_BANDS == ((0, 40), (40, 65), (65, 80), (80, 200))
    rep = run(
        make_cohort(n=300),
        criteria_for(
            [{"attribute": "sex", "prespecified": True, "source": "t", "reference_level": "M"}]
        ),
    )
    block = rep.attribute("age")
    assert block["declared"] is False and block["source"] == EXPLORATORY
    assert block["bands_source"] == "engine_default"
    assert block["bands"] == [list(map(float, b)) for b in DEFAULT_AGE_BANDS]
    assert block["reference_rule"] in ("largest", "largest_tie_first_in_level_order")


def test_missing_attribute_values_form_the_unknown_row_which_joins_every_complement():
    cols = make_cohort(n=300)
    for i in range(0, 300, 10):  # 30 rows with a missing site, via three missing tokens
        cols["site"][i] = (None, "NA", "")[i % 3]
    rep = run(cols)
    rows = [r for r in rep.rows if r["attribute"] == "site"]
    unknown = [r for r in rows if r["is_unknown_row"]]
    assert len(unknown) == 1 and unknown[0]["level"] == UNKNOWN_LEVEL and unknown[0]["n"] == 30
    assert rep.attribute("site")["level_order"][-1] == UNKNOWN_LEVEL
    assert rep.attribute("site")["n_unknown_missing"] == 30
    assert not unknown[0]["is_reference"]
    # the complement of S1 = every other analysed site row *including* the 30 unknown rows
    s1 = rep.row("site", "S1")
    pos = np.array([v == "1" for v in cols["y_true"]])
    pred = np.array(cols["score"]) >= 0.5
    site = np.array(
        [v if v not in (None, "NA", "") else UNKNOWN_LEVEL for v in cols["site"]], dtype=object
    )
    in_s1 = site == "S1"
    se_s1 = pred[pos & in_s1].mean()
    se_rest_with_unknown = pred[pos & ~in_s1].mean()
    se_rest_without_unknown = pred[pos & ~in_s1 & (site != UNKNOWN_LEVEL)].mean()
    got = s1["diff_vs_complement"]["op1"]["sensitivity"]["number"]["est"]
    assert got == pytest.approx(se_s1 - se_rest_with_unknown)
    assert got != pytest.approx(se_s1 - se_rest_without_unknown)
    # the Unknown row has its own metrics and differences, like any other level
    assert unknown[0]["diff_vs_reference"]["op1"]["sensitivity"]["number"]["est"] is not None
    assert unknown[0]["diff_vs_complement"]["auroc"] is not None


def test_the_unknown_row_is_never_the_reference_even_when_it_is_the_largest_level():
    cols = make_cohort(n=300)
    cols["site"] = [None] * 200 + ["S1"] * 60 + ["S2"] * 40
    rep = run(
        cols,
        criteria_for([{"attribute": "site", "prespecified": False, "reference_level": "largest"}]),
    )
    block = rep.attribute("site")
    assert block["reference_level"] == "S1" and block["reference_rule"] == "largest"
    assert (
        rep.row("site", UNKNOWN_LEVEL)["n"] == 200
        and not rep.row("site", UNKNOWN_LEVEL)["is_reference"]
    )
    with pytest.raises(HaltError) as info:
        run(
            cols,
            criteria_for(
                [{"attribute": "site", "prespecified": False, "reference_level": UNKNOWN_LEVEL}]
            ),
        )
    assert info.value.code == "H09"


def test_reference_ties_go_to_the_first_level_in_the_level_order_and_the_rule_says_so():
    cols = make_cohort(n=300)
    cols["site"] = ["Zeta"] * 100 + ["Alpha"] * 100 + ["Mid"] * 100
    rep = run(
        cols,
        criteria_for([{"attribute": "site", "prespecified": False, "reference_level": "largest"}]),
    )
    block = rep.attribute("site")
    assert block["level_order"] == ["Alpha", "Mid", "Zeta"]
    assert block["reference_level"] == "Alpha"
    assert block["reference_rule"] == "largest_tie_first_in_level_order"
    ref_row = rep.row("site", "Alpha")
    assert ref_row["is_reference"]
    # the reference row's own differences against the reference are all null
    d = ref_row["diff_vs_reference"]
    assert d["auroc"] is None and all(v is None for v in d["op1"].values())
    assert ref_row["diff_vs_complement"]["auroc"] is not None


def test_a_declared_reference_level_that_is_not_observed_halts_h09():
    with pytest.raises(HaltError) as info:
        run(
            make_cohort(n=200),
            criteria_for(
                [
                    {
                        "attribute": "site",
                        "prespecified": True,
                        "source": "t",
                        "reference_level": "S9",
                    }
                ]
            ),
        )
    assert info.value.code == "H09"


def test_auroc_below_ten_positives_or_negatives_is_shown_not_estimable_never_omitted():
    assert AUROC_EVALUABLE_CLASS == 10
    cols = counts_cohort(
        {
            "fewpos": (5, 2, 20, 40),
            "fewneg": (30, 10, 3, 4),
            "ok": (30, 10, 20, 40),
            "tenten": (8, 2, 5, 5),
        }
    )
    rep = run(
        cols,
        criteria_for(
            [{"attribute": "site", "prespecified": True, "source": "t", "reference_level": "ok"}]
        ),
    )
    few_pos = rep.row("site", "fewpos")["metrics"]["auroc"]
    assert few_pos["number"]["not_estimable_reason"] == "insufficient_positives"
    assert few_pos["number"]["n_pos"] == 7 and few_pos["number"]["est"] is None
    assert (
        rep.row("site", "fewneg")["metrics"]["auroc"]["number"]["not_estimable_reason"]
        == "insufficient_negatives"
    )
    assert rep.row("site", "tenten")["metrics"]["auroc"]["number"]["method"] in (
        "delong_logit",
        "delong_wald",
    )
    assert rep.row("site", "ok")["metrics"]["auroc"]["number"]["ci_lo"] is not None
    # the differences involving a non-evaluable level carry the same reason
    assert (
        rep.row("site", "fewpos")["diff_vs_reference"]["auroc"]["number"]["not_estimable_reason"]
        == "insufficient_positives"
    )
    assert (
        rep.row("site", "fewneg")["diff_vs_complement"]["auroc"]["number"]["not_estimable_reason"]
        == "insufficient_negatives"
    )


def test_brier_is_the_plain_mean_squared_error_with_a_bootstrap_interval_only_for_probabilities():
    cols = make_cohort(n=300)
    rep = run(cols)
    row = rep.row("sex", "F")
    cell = row["metrics"]["brier"]
    sel = np.array(cols["sex"]) == "F"
    y = np.array([v == "1" for v in cols["y_true"]])[sel].astype(float)
    p = np.array(cols["score"])[sel]
    from sklearn.metrics import brier_score_loss

    assert cell["number"]["est"] == pytest.approx(float(np.mean((p - y) ** 2)))
    assert cell["number"]["est"] == pytest.approx(brier_score_loss(y, p))
    assert (
        cell["number"]["method"] == "bootstrap_percentile" and cell["number"]["ci_lo"] is not None
    )
    assert cell["analytic"]["not_estimable_reason"] == "analytic_ci_unavailable"
    crit = make_criteria()
    crit["score"] = {"type": "logit", "orientation": "higher_is_positive"}
    cols_logit = dict(cols)
    cols_logit["score"] = [round(math.log(s / (1 - s)), 6) for s in cols["score"]]
    rep = run(cols_logit, crit)
    cell = rep.row("sex", "F")["metrics"]["brier"]
    assert cell["number"]["not_estimable_reason"] == "not_computed_this_run"
    assert cell["detail"] == {"score_type": "logit"}


# ------------------------------------------------------------------- X1 and DEC-10


def test_x1_there_is_no_diff_vs_overall_anywhere():
    src = (REPO / "src/proofpack/stats/subgroups.py").read_text(encoding="utf-8")
    assert "diff_vs_overall" not in src.replace(
        "no\n``diff_vs_overall``", ""
    )  # docstring mention aside
    body = src.split('"""', 2)[2]  # everything after the module docstring
    assert "overall" not in body
    rep = run(make_cohort(n=300))
    blob = json.dumps(rep.as_dict())
    assert "diff_vs_overall" not in blob and "overall" not in blob
    for row in rep.rows:
        assert set(row) >= {"diff_vs_reference", "diff_vs_complement"}
        assert not any(
            k.startswith("diff_vs_") and k not in ("diff_vs_reference", "diff_vs_complement")
            for k in row
        )


def _proportion_numbers(rep) -> list[tuple[str, dict]]:
    out = []
    for row in rep.rows:
        for key, block in row["metrics"].items():
            if key in ("auroc", "brier"):
                continue
            for metric, cell in block.items():
                if metric in PROPORTION_KEYS:
                    out.append(
                        (f"{row['attribute']}/{row['level']}/{key}/{metric}", cell["number"])
                    )
    return out


def test_dec10_every_proportion_number_is_wilson_or_the_cluster_bootstrap():
    rep = run(make_cohort(n=300))
    nums = _proportion_numbers(rep)
    assert len(nums) == 6 * 9  # 4 age bands + 2 sexes + 3 sites, 6 proportions each
    for path, num in nums:
        if num["ci_lo"] is not None:
            assert num["method"] == "wilson", (path, num)
        else:
            assert num["not_estimable_reason"] in NOT_ESTIMABLE_REASONS
    n = 200
    cols = make_cohort(n=n, with_case_id=True)
    dup = {k: [v[i // 2] for i in range(2 * n)] for k, v in cols.items()}
    dup["row_id"] = [f"r{i:05d}" for i in range(2 * n)]
    rep = run(dup, make_criteria(clustering={"unit": "case_id", "declared_by": "t"}))
    nums = _proportion_numbers(rep)
    for path, num in nums:
        assert num["method"] in ("cluster_bootstrap_percentile", "none"), (path, num)
        if num["method"] == "cluster_bootstrap_percentile":
            assert "wilson_refused_clustered" in num["flags"]
    # nothing anywhere carries a Wald interval or a two_by_two_metrics-only method
    for _path, num in walk_numbers(rep.as_dict()):
        assert num["method"] in METHODS and num["method"] not in (
            "log_delta",
            "logit_delta",
            "irls_wald",
        )


# -------------------------------------------------------------------- clustered paths


def clustered_pair(n: int = 200, span: bool = False):
    cols = make_cohort(n=n, with_case_id=True)
    dup = {k: [v[i // 2] for i in range(2 * n)] for k, v in cols.items()}
    dup["row_id"] = [f"r{i:05d}" for i in range(2 * n)]
    if span:  # the first case's two rows sit in two different sites
        dup["site"][1] = "S2" if dup["site"][0] != "S2" else "S1"
    crit = make_criteria(clustering={"unit": "case_id", "declared_by": "t"})
    return dup, crit


def test_a_case_spanning_two_levels_refuses_the_difference_with_a_typed_reason():
    cols, crit = clustered_pair(span=True)
    rep = run(cols, crit)
    spanned = cols["site"][0]
    other = cols["site"][1]
    for level in (spanned, other):
        cell = rep.row("site", level)["diff_vs_complement"]["auroc"]
        assert cell["number"]["not_estimable_reason"] == "cases_span_both_groups"
        assert cell["number"]["ci_lo"] is None and cell["number"]["est"] is not None
        assert cell["analytic"]["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
        assert cell["analytic_status"] == "unavailable"
    # a level the spanning case does not touch is bootstrapped normally
    untouched = next(lv for lv in ("S1", "S2", "S3") if lv not in (spanned, other))
    cell = rep.row("site", untouched)["diff_vs_complement"]["auroc"]
    assert cell["number"]["method"] == "cluster_bootstrap_percentile"
    assert "cases_span_both_groups" in NOT_ESTIMABLE_REASONS


def test_without_a_spanning_case_the_differences_are_cluster_bootstrapped_with_refused_flags():
    cols, crit = clustered_pair(span=False)
    rep = run(cols, crit)
    for level in ("S1", "S2", "S3"):
        row = rep.row("site", level)
        for kind in ("diff_vs_reference", "diff_vs_complement"):
            if row[kind] is None or row["is_reference"] and kind == "diff_vs_reference":
                continue
            auc = row[kind]["auroc"]
            assert auc["number"]["method"] == "cluster_bootstrap_percentile"
            assert "delong_refused_clustered" in auc["number"]["flags"]
            assert auc["analytic"]["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
            assert auc["analytic_status"] == "refused_clustered"
            assert auc["bootstrap"]["resampling"]["a"]["kind"] == "clustered"
            assert "detail" not in auc
            se = row[kind]["op1"]["sensitivity"]
            assert se["number"]["method"] == "cluster_bootstrap_percentile"
            assert "newcombe_refused_clustered" in se["number"]["flags"]
            assert se["analytic"]["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
            assert se["number"]["n_cases"] is not None
    assert "newcombe_refused_clustered" in FLAGS


def test_the_two_sided_bootstrap_is_deterministic_and_the_policy_seed_moves_only_the_bounds():
    """Inspects: two runs agree; a different seed moves the bounds and not the estimate.

    Renamed in the day-5 repair (regression lens RG-N2): the previous name claimed the
    two sides were drawn independently, which nothing here inspected - the next test
    does that, by recording what each side's resampler is asked to draw.
    """
    cols, crit = clustered_pair(span=False)
    a = run(cols, crit).row("site", "S1")["diff_vs_complement"]["op1"]["sensitivity"]["number"]
    b = run(cols, crit).row("site", "S1")["diff_vs_complement"]["op1"]["sensitivity"]["number"]
    assert a == b
    c = run(cols, crit, policy=BootstrapPolicy(n_resamples=200, seed=99)).row("site", "S1")[
        "diff_vs_complement"
    ]["op1"]["sensitivity"]["number"]
    assert (c["ci_lo"], c["ci_hi"]) != (a["ci_lo"], a["ci_hi"])
    assert c["est"] == a["est"]


class _RecordingResampler:
    """Wraps a Resampler; records each index vector it returns, and appends its side
    label to a log shared with the other side so the order of the draws is visible."""

    def __init__(self, inner, side: str, log: list[str]):
        self.inner = inner
        self.side = side
        self.log = log
        self.draws: list[np.ndarray] = []

    @property
    def deficient_class(self):
        return self.inner.deficient_class

    @property
    def kind(self):
        return self.inner.kind

    def draw(self, rng):
        idx = self.inner.draw(rng)
        self.draws.append(np.asarray(idx).copy())
        self.log.append(self.side)
        return idx


def _record_two_sided(ind_a, ind_b, seed: int, n: int = 50):
    ids_a = np.arange(ind_a.shape[0]) // 2
    ids_b = np.arange(ind_b.shape[0]) // 2
    log: list[str] = []
    ra = _RecordingResampler(clustered_flat(ids_a, n_rows=ind_a.shape[0]), "a", log)
    rb = _RecordingResampler(clustered_flat(ids_b, n_rows=ind_b.shape[0]), "b", log)
    subgroups_module._bootstrap_difference(
        lambda idx: float(ind_a[idx].mean()),
        ra,
        lambda idx: float(ind_b[idx].mean()),
        rb,
        np.random.default_rng(seed),
        n,
        0.95,
    )
    return ra.draws, rb.draws, log


def test_the_two_sided_bootstrap_draws_side_a_then_side_b_from_the_cell_generator():
    """Inspects the index vectors each side's resampler returns across two generators,
    and the order in which the two resamplers are asked to draw, through one log both
    sides append to.

    Side b's draws change when the cell's generator changes (they are drawn from it,
    not from a generator of their own); the log reads ``a, b, a, b, ...`` - one draw per
    side per resample, side a first; the same seed reproduces both sides. Renamed in
    repair round 2 (lens 2, FA-N4): the previous name said "after side a" while nothing
    recorded the order, and the lens's b-before-a mutant survived; on these index
    vectors that mutant moves the interval from (0.0, 0.4643) to (0.0696, 0.4762). The
    committed sweep's ``two_sided_bootstrap_side_b_from_a_fixed_generator`` is killed
    by the first assertion and ``two_sided_bootstrap_side_b_drawn_before_side_a`` by
    the log assertion.
    """
    ind_a = np.array([1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1], dtype=bool)
    ind_b = np.array([1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0], dtype=bool)
    a1, b1, log1 = _record_two_sided(ind_a, ind_b, seed=1)
    a2, b2, log2 = _record_two_sided(ind_a, ind_b, seed=2)
    assert len(a1) == len(b1) == len(a2) == len(b2) == 50
    differs_b = sum(not np.array_equal(x, y) for x, y in zip(b1, b2, strict=True))
    differs_a = sum(not np.array_equal(x, y) for x, y in zip(a1, a2, strict=True))
    assert differs_b > 40, differs_b  # side b is drawn from the cell's generator
    assert differs_a > 40, differs_a
    assert log1 == log2 == ["a", "b"] * 50, log1[:6]
    # the same generator, same seed, reproduces both sides exactly
    a3, b3, _ = _record_two_sided(ind_a, ind_b, seed=1)
    assert all(np.array_equal(x, y) for x, y in zip(b3, b1, strict=True))
    assert all(np.array_equal(x, y) for x, y in zip(a3, a1, strict=True))


def test_a_case_id_column_is_used_even_when_not_passed_and_detected_clustering_routes_everything():
    """Day-4 handoff, 'tomorrow needs' 1: the caller must pass cluster_ids on every cell."""
    cols, _ = clustered_pair(span=False)
    crit = make_criteria()  # clustering.unit: none, but case_id repeats -> detected
    rep = run(cols, crit)
    for _path, num in _proportion_numbers(rep):
        assert num["method"] in ("cluster_bootstrap_percentile", "none")
    cell = rep.row("sex", "F")["metrics"]["op1"]["sensitivity"]
    assert cell["clustering_route"] == "detected"
    assert rep.row("sex", "F")["metrics"]["auroc"]["clustering_route"] == "detected"


def test_a_supplied_plan_that_contradicts_the_case_column_is_refused():
    cols, crit = clustered_pair(span=False)
    decl = validate_dict(crit)
    table = schema_mod.validate(schema_mod.table_from_columns(cols), period=None)
    mask, _ = schema_mod.analysis_mask(table, decl.indeterminate_values)
    with pytest.raises(ValueError, match="contradicts"):
        subgroup_analysis(
            table, decl, mask, plan=ClusterPlan(False, "none", 400, 400), policy=POLICY
        )
    with pytest.raises(ValueError):
        subgroup_analysis(table, decl, mask, cluster_ids=np.arange(10), policy=POLICY)


# ------------------------------------------------------------------------- fairness


def fairness_criteria(**fair: Any) -> dict[str, Any]:
    crit = make_criteria()
    crit["fairness"] = {
        "criterion_of_interest": "tpr_gap",
        "attribute": "sex",
        "bound": 0.05,
        # build day 7 (E7): a bound is compared with the statistic and comparator the
        # customer writes beside it; the schema requires both when a bound is present
        "statistic": "ci_upper_bound",
        "comparator": "<=",
        "author": "Dr F.",
        "date": "2026-02-02",
        "justification": "intended-use population",
        **fair,
    }
    return crit


def test_fairness_gaps_are_the_reference_differences_and_fpr_gap_is_the_mirrored_specificity_gap():
    cols = make_cohort(n=400)
    rep = run(cols, fairness_criteria())
    fair = rep.fairness
    assert fair["attribute"] == "sex" and fair["reference_level"] == "M"
    gap = next(g for g in fair["gaps"] if g["level"] == "F")
    row = rep.row("sex", "F")
    d = row["diff_vs_reference"]["op1"]
    op = gap["operating_points"]["op1"]
    assert op["tpr_gap"] == d["sensitivity"]
    assert op["ppv_gap"] == d["ppv"] and op["npv_gap"] == d["npv"]
    assert gap["auroc_gap"] == row["diff_vs_reference"]["auroc"]
    fpr, sp = op["fpr_gap"]["number"], d["specificity"]["number"]
    assert fpr["est"] == pytest.approx(-sp["est"])
    assert fpr["ci_lo"] == pytest.approx(-sp["ci_hi"]) and fpr["ci_hi"] == pytest.approx(
        -sp["ci_lo"]
    )
    assert fpr["method"] == sp["method"] == "newcombe10"
    # and equals the Newcombe-10 difference computed directly on the false-positive counts
    pos = np.array([v == "1" for v in cols["y_true"]])
    pred = np.array(cols["score"]) >= 0.5
    sex = np.array(cols["sex"])
    fp_f, n_f = int((~pos & pred & (sex == "F")).sum()), int((~pos & (sex == "F")).sum())
    fp_m, n_m = int((~pos & pred & (sex == "M")).sum()), int((~pos & (sex == "M")).sum())
    lo, hi = newcombe10_bounds(fp_f, n_f, fp_m, n_m)
    assert fpr["est"] == pytest.approx(fp_f / n_f - fp_m / n_m)
    assert fpr["ci_lo"] == pytest.approx(lo) and fpr["ci_hi"] == pytest.approx(hi)
    sel = op["selection_rate_gap"]
    assert sel["label"] == "descriptive_not_target"
    assert sel["number"]["est"] == pytest.approx(pred[sex == "F"].mean() - pred[sex == "M"].mean())
    assert gap["calibration"] == {
        "oe": None,
        "slope": None,
        "intercept": None,
        "not_estimable_reason": "not_computed_this_run",
    }


def test_fairness_records_the_criterion_and_bound_verbatim_and_emits_no_status():
    rep = run(make_cohort(n=300), fairness_criteria(criterion_of_interest="auroc_gap", bound=0.02))
    fair = rep.fairness
    assert fair["criterion_of_interest"] == "auroc_gap" and fair["bound"] == 0.02
    assert fair["author"] == "Dr F." and fair["date"] == "2026-02-02"
    assert fair["measured_not_mitigated"] is True
    assert "[unverified" in fair["impossibility_citation"]
    # no key named status / met / verdict anywhere in the block ("analytic_status" is
    # the day-4 audit key and names what became of a method, not a verdict)
    assert not {"status", "met", "not_met", "verdict"} & set(walk_dict_keys(fair))
    rep = run(make_cohort(n=300), fairness_criteria(bound=None))
    assert rep.fairness["bound"] is None
    assert run(make_cohort(n=300)).fairness is None


def test_fairness_gaps_cover_every_non_reference_level_including_unknown():
    cols = make_cohort(n=300)
    cols["sex"][5] = None
    rep = run(cols, fairness_criteria())
    levels = [g["level"] for g in rep.fairness["gaps"]]
    assert levels == ["F", UNKNOWN_LEVEL]
    assert rep.fairness["gaps"][1]["is_unknown_row"] is True


# ------------------------------------------------------------------ output & schema


def _document(rep) -> dict[str, Any]:
    """The day-5 blocks inside a document carrying every top-level key the schema requires
    (the required set grew on build day 7, E7: the other blocks are null or empty here)."""
    return {
        "schema_version": 1,
        "manifest": {
            "run_id": "t",
            "engine_version": "0",
            "platform": "t",
            "python": "3",
            "numpy": "2",
            "scipy": None,
            "input_sha256": None,
            "criteria_sha256": None,
            "mapping_sha256": None,
            "seed": 1,
            "B": 1,
            "started": "t",
            "duration_s": None,
            "reference_platform": False,
            "licence_id": None,
            "tier": None,
            "ledger_count": None,
            "watermark": None,
        },
        "declarations": {},
        "halts": [],
        "warnings": [],
        "flow": {
            "rows_read": 1,
            "dev_rows": 0,
            "excluded_missing_label": 0,
            "excluded_missing_score": 0,
            "indeterminate": 0,
            "analysed": 1,
        },
        "table1": None,
        "missingness": None,
        "overall": None,
        "calibration": None,
        "calibration_suppressed_reason": None,
        "criteria_results": [],
        "suppression_log": [],
        "guidance_refs": [],
        **rep.as_dict(),
    }


@pytest.fixture(scope="module")
def reports():
    cols = make_cohort(n=300)
    cols["site"][3] = None
    iid = run(cols, fairness_criteria())
    cols_c, crit_c = clustered_pair(span=True)
    crit_c["fairness"] = fairness_criteria()["fairness"]
    clustered = run(cols_c, crit_c)
    comparator = make_criteria()
    comparator["reference_standard"] = {"type": "comparator", "description": "t"}
    ppa = run(make_cohort(n=300), comparator)
    return {"iid": iid, "clustered": clustered, "comparator": ppa}


def test_the_day5_output_validates_against_the_output_schema(reports):
    schema = load_json_schema("output_schema_v1.json")
    validator = jsonschema.Draft202012Validator(schema)
    for name, rep in reports.items():
        errors = sorted(validator.iter_errors(_document(rep)), key=lambda e: list(e.absolute_path))
        assert errors == [], (name, [(list(e.absolute_path), e.message[:160]) for e in errors[:5]])


def test_the_schema_rejects_a_verdict_beside_a_p_value_and_a_status_in_fairness(reports):
    schema = load_json_schema("output_schema_v1.json")
    validator = jsonschema.Draft202012Validator(schema)
    doc = _document(reports["iid"])
    bad = copy.deepcopy(doc)
    bad["subgroup_attributes"][0]["heterogeneity"]["tests"][0]["status"] = "met"
    assert any(validator.iter_errors(bad))
    bad = copy.deepcopy(doc)
    bad["fairness"]["status"] = "met"
    assert any(validator.iter_errors(bad))
    bad = copy.deepcopy(doc)
    bad["subgroups"][0]["diff_vs_overall"] = bad["subgroups"][0]["diff_vs_complement"]
    assert any(validator.iter_errors(bad))


def test_every_number_in_the_output_has_a_ci_or_a_typed_reason(reports):
    for name, rep in reports.items():
        seen = 0
        for path, num in walk_numbers(rep.as_dict()):
            seen += 1
            Number(**num)  # re-validates the invariant on the serialised form
            has_ci = num["ci_lo"] is not None and num["ci_hi"] is not None
            assert has_ci or num["not_estimable_reason"] in NOT_ESTIMABLE_REASONS, (name, path, num)
            for f in num["flags"]:
                assert f in FLAGS
        assert seen > 100, name


VERDICT_WORDS = {
    "verdict",
    "pass",
    "passed",
    "fail",
    "failed",
    "met",
    "not_met",
    "unmet",
    "acceptable",
    "unacceptable",
    "good",
    "poor",
    "adequate",
    "inadequate",
    "significant",
    "insignificant",
    "approved",
    "cleared",
    "compliant",
    "noncompliant",
    "satisfactory",
    "safe",
    "effective",
    "fair",
    "unfair",
    "biased",
    "unbiased",
    "consistent",
    "inconsistent",
    "ok",
    # the brief's list also names "well calibrated" (regression lens RG-N5): the phrase
    # is tokenised to "calibrated" - "calibration" (the key) is a different token
    "calibrated",
    "passes",
    "fails",
    # inflections lens 2 (FA-N5) found unflagged: the tokeniser matches whole words
    # after splitting on non-letters and has no stemmer, so a spelling is flagged only
    # when it is listed here
    "passing",
    "failing",
    "meets",
    "verdicts",
    "miscalibrated",
    "satisfied",
    "successful",
}


def _verdict_flagged(token: str) -> bool:
    """Whole-word match after splitting on non-letters; no stemming."""
    words = set(re.split(r"[^a-z]+", token.lower()))
    return bool(words & VERDICT_WORDS)


def test_no_verdict_word_appears_in_any_key_or_engine_string_of_the_output(reports):
    for name, rep in reports.items():
        for token in walk_keys_and_strings(rep.as_dict()):
            assert not _verdict_flagged(token), (name, token)


def test_the_verdict_grep_flags_every_phrase_the_brief_names():
    """The day-5 brief: no 'pass', 'fail', 'verdict', 'met', 'consistent', 'acceptable',
    'unbiased', 'well calibrated' in any key or value. Inspected: each phrase listed
    below, in the spelling listed - the brief's words, three hyphenated or punctuated
    forms, and the seven inflections lens 2 (FA-N5) found unflagged at 9da4401 - trips
    the tokeniser the output test uses. The tokeniser is a whole-word grep, not a
    stemmer: a spelling not in ``VERDICT_WORDS`` is not flagged."""
    for phrase in (
        "pass",
        "passes",
        "fail",
        "fails",
        "verdict",
        "met",
        "not_met",
        "consistent",
        "acceptable",
        "unbiased",
        "well calibrated",
        "model is well-calibrated",
        "criterion: met",
        "passing",
        "failing",
        "meets",
        "verdicts",
        "miscalibrated",
        "satisfied",
        "successful",
    ):
        assert _verdict_flagged(phrase), phrase
    for phrase in ("calibration", "not_computed_this_run", "sensitivity", "descriptive_not_target"):
        assert not _verdict_flagged(phrase), phrase


def test_comparator_reference_standard_routes_to_ppa_npa_everywhere(reports):
    rep = reports["comparator"]
    blob = json.dumps(rep.as_dict())
    assert "sensitivity" not in blob and "specificity" not in blob
    row = rep.row("sex", "F")
    assert {"ppa", "npa"} <= set(row["metrics"]["op1"]) and {"ppa", "npa"} <= set(
        row["diff_vs_reference"]["op1"]
    )
    assert {t["metric"] for t in rep.attribute("sex")["heterogeneity"]["tests"]} == {"ppa", "npa"}


def test_the_enums_added_today_agree_between_code_and_schema():
    schema = load_json_schema("output_schema_v1.json")
    assert set(schema["$defs"]["notEstimableReason"]["enum"]) == NOT_ESTIMABLE_REASONS
    assert set(schema["$defs"]["flag"]["enum"]) == FLAGS
    assert set(schema["$defs"]["method"]["enum"]) == METHODS
    assert {"cases_span_both_groups", "insufficient_levels"} <= NOT_ESTIMABLE_REASONS
    assert "newcombe_refused_clustered" in FLAGS


def test_cells_carry_the_day4_audit_shape_and_cell_keys_are_unique(reports):
    keys: list[str] = []
    for name, rep in reports.items():
        for row in rep.rows:
            for block in row["metrics"].values():
                cells = (
                    [block]
                    if "number" in block
                    else [v for k, v in block.items() if k != "two_by_two"]
                )
                for cell in cells:
                    assert {
                        "number",
                        "analytic",
                        "analytic_status",
                        "clustering_route",
                        "bootstrap",
                    } <= set(cell)
                    if cell["bootstrap"] is not None:
                        keys.append((name, cell["bootstrap"]["cell_key"]))
    assert len(keys) == len(set(keys))
    assert all(json.loads(k)[0] == "subgroups" for _, k in keys)


def test_two_by_two_counts_per_level_sum_to_the_level_and_selection_rate_is_the_called_share():
    cols = make_cohort(n=300)
    rep = run(cols)
    pred = np.array(cols["score"]) >= 0.5
    sex = np.array(cols["sex"])
    for level in ("F", "M"):
        row = rep.row("sex", level)
        t = row["metrics"]["op1"]["two_by_two"]
        assert sum(t.values()) == row["n"] == int((sex == level).sum())
        assert t["tp"] + t["fn"] == row["events"]
        sel = row["metrics"]["op1"]["selection_rate"]["number"]
        assert sel["est"] == pytest.approx(pred[sex == level].mean()) and sel["method"] == "wilson"
        assert sel["k"] == t["tp"] + t["fp"] and sel["n"] == row["n"]


# ------------------------------------------------- day-5 repair round 1 (2026-09-15)
# The lens id each test answers is in its docstring, with what it fails on at d1fd20a.


def f6_tripled_with_case_id() -> dict[str, list[Any]]:
    """F6's counts-exact cohort with every patient's row copied three times under one case id."""
    base = counts_cohort(
        {"site1": (45, 5, 10, 40), "site2": (38, 12, 10, 40), "site3": (27, 3, 10, 40)}
    )
    n = len(base["y_true"])
    cols = {k: [v[i // 3] for i in range(n * 3)] for k, v in base.items()}
    cols["case_id"] = [f"c{i // 3:04d}" for i in range(n * 3)]
    return cols


SITE_LARGEST = [
    {"attribute": "site", "prespecified": True, "source": "SAP", "reference_level": "largest"}
]


def test_the_heterogeneity_footnote_is_refused_on_clustered_rows_with_the_dec09_typed_reason():
    """Fresh-attack lens FA-B1. At d1fd20a the tripled F6 cohort reported chi-square
    13.898, p 0.00096, Holm 0.0019 on the rows (F6 on one row per patient: 4.6327,
    p 0.0986) while every interval in the same block carried
    ``clustered_data_analytic_ci_invalid``. Inspected here: every test entry under a
    declared and under a detected plan carries that typed reason and no p-value, the
    family is empty, the footnote records the route; one row per patient still gives F6;
    the schema accepts the refused footnote and requires the route.
    """
    cols = f6_tripled_with_case_id()
    declared = run(
        cols, criteria_for(SITE_LARGEST, clustering={"unit": "case_id", "declared_by": "t"})
    )
    detected = run(cols, criteria_for(SITE_LARGEST))  # clustering.unit none; the ids repeat
    for rep, route in ((declared, "declared"), (detected, "detected")):
        foot = rep.attribute("site")["heterogeneity"]
        assert foot["clustering_route"] == route
        assert foot["family_size"] == 0 and foot["label"] == EXPLORATORY
        assert {t["metric"] for t in foot["tests"]} == {"sensitivity", "specificity"}
        for t in foot["tests"]:
            assert t["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
            assert t["test"] is None and t["statistic"] is None and t["df"] is None
            assert t["p_raw"] is None and t["p_holm"] is None and t["min_expected"] is None
            assert t["n_levels"] == 3  # what would have been compared is still visible
            assert "status" not in t
        # the same block's own intervals carry the same typed reason on their companion
        cell = rep.row("site", "site1")["metrics"]["op1"]["sensitivity"]
        assert cell["analytic"]["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
        assert "cluster" in json.dumps(foot)
    # the tripled cohort without ids is three identical rows per patient, route none,
    # and the chi-square is three times F6's - the number the refusal keeps off the page
    tripled = run({k: v for k, v in cols.items() if k != "case_id"}, criteria_for(SITE_LARGEST))
    foot = tripled.attribute("site")["heterogeneity"]
    assert foot["clustering_route"] == "none"
    tripled_stat = next(t for t in foot["tests"] if t["metric"] == "sensitivity")["statistic"]
    assert tripled_stat == pytest.approx(3 * 4.632727, abs=5e-5)
    # one row per patient: the F6 figures, route none
    base = run(
        counts_cohort(
            {"site1": (45, 5, 10, 40), "site2": (38, 12, 10, 40), "site3": (27, 3, 10, 40)}
        ),
        criteria_for(SITE_LARGEST),
    )
    foot = base.attribute("site")["heterogeneity"]
    se_test = next(t for t in foot["tests"] if t["metric"] == "sensitivity")
    approx4(se_test["statistic"], 4.6327)
    approx4(se_test["p_raw"], 0.0986)
    assert foot["clustering_route"] == "none"
    # the footnote function itself: the route is validated, the refusal is typed
    foot = subgroups_module.heterogeneity_footnote(
        {"op1": {"sensitivity": [(45, 5), (38, 12)]}}, clustering_route="declared"
    )
    assert foot["tests"][0]["not_estimable_reason"] in NOT_ESTIMABLE_REASONS
    with pytest.raises(ValueError, match="clustering_route"):
        subgroups_module.heterogeneity_footnote({}, clustering_route="rows")
    # and the schema accepts the refused footnote and requires the route
    validator = jsonschema.Draft202012Validator(load_json_schema("output_schema_v1.json"))
    assert list(validator.iter_errors(_document(declared))) == []
    bad = _document(declared)
    del bad["subgroup_attributes"][0]["heterogeneity"]["clustering_route"]
    assert any(validator.iter_errors(bad))


def separated_level_cohort(move_one: bool = False) -> dict[str, list[Any]]:
    """Level A: 10 positives in [0.80, 0.90], 10 negatives in [0.10, 0.20] - perfectly
    separated, DeLong variance exactly zero. Level B: 60/60 overlapping. ``move_one``
    puts one A positive among the negatives so A's variance is no longer zero."""
    rng = np.random.default_rng(2026)
    a_pos = rng.uniform(0.80, 0.90, 10)
    if move_one:
        a_pos[0] = 0.15
    a_neg = rng.uniform(0.10, 0.20, 10)
    b_pos = np.clip(rng.normal(0.6, 0.2, 60), 0.01, 0.99)
    b_neg = np.clip(rng.normal(0.4, 0.2, 60), 0.01, 0.99)
    score = np.concatenate([a_pos, a_neg, b_pos, b_neg])
    return {
        "y_true": ["1"] * 10 + ["0"] * 10 + ["1"] * 60 + ["0"] * 60,
        "score": [round(float(v), 6) for v in score],
        "site": ["A"] * 20 + ["B"] * 120,
    }


SITE_REF_B = [{"attribute": "site", "prespecified": False, "reference_level": "B"}]


def test_unpaired_delong_refuses_the_difference_when_either_arm_has_zero_variance():
    """Fresh-attack lens FA-B2. At d1fd20a a perfectly separated level (own AUROC refused
    ``boundary_estimate``) had its difference rendered ``delong_wald`` with
    ``variance_a = 0.0`` and a p-value in ``detail``; the lens measured that interval
    covering the true difference in 0.269 of replicates where separation occurred.
    Inspected here: ``unpaired_delong`` refuses with ``boundary_estimate`` (estimate
    carried, z and p ``None``) when either arm's variance is zero, in either position
    and for a constant-score arm; the subgroup cell shows the refusal; moving one row so
    the variance is no longer zero renders ``delong_wald`` again - the guard is at zero,
    not near it."""
    cols = separated_level_cohort()
    y = np.array(cols["y_true"]) == "1"
    s = np.array(cols["score"])
    a, b = np.array(cols["site"]) == "A", np.array(cols["site"]) == "B"
    assert delong_variance(s[a], y[a])[1] == 0.0 and delong_variance(s[b], y[b])[1] > 0.0
    for sa, pa, sb, pb in ((s[a], y[a], s[b], y[b]), (s[b], y[b], s[a], y[a])):
        res = unpaired_delong(sa, pa, sb, pb)
        num = res.difference
        assert num.not_estimable_reason == "boundary_estimate" and num.method == "none"
        assert num.est == pytest.approx(res.auroc_a - res.auroc_b)
        assert num.ci_lo is None and num.ci_hi is None
        assert res.z is None and res.p_value is None
        assert min(res.variance_a, res.variance_b) == 0.0
        assert res.variance_difference == pytest.approx(max(res.variance_a, res.variance_b))
    # a constant-score arm: AUROC 0.5 exactly, every placement value equal, variance 0
    const = np.full(40, 0.5)
    res = unpaired_delong(const, np.arange(40) < 15, s[b], y[b])
    assert res.difference.not_estimable_reason == "boundary_estimate" and res.z is None
    # through the subgroup table: the level's own AUROC and its differences agree
    rep = run(cols, criteria_for(SITE_REF_B))
    row = rep.row("site", "A")
    assert row["metrics"]["auroc"]["number"]["not_estimable_reason"] == "boundary_estimate"
    auroc_b = rep.row("site", "B")["metrics"]["auroc"]["number"]["est"]
    for kind in ("diff_vs_reference", "diff_vs_complement"):
        cell = row[kind]["auroc"]
        assert cell["number"]["not_estimable_reason"] == "boundary_estimate"
        assert cell["number"]["method"] == "none" and cell["number"]["ci_lo"] is None
        assert cell["number"]["est"] == pytest.approx(1.0 - auroc_b)
        assert cell["analytic_status"] == "unavailable"
        assert cell["detail"]["variance_a"] == 0.0 and cell["detail"]["z"] is None
        assert cell["detail"]["p_value"] is None
    # B against A is the mirror image and is refused the same way
    b_cell = rep.row("site", "B")["diff_vs_complement"]["auroc"]["number"]
    assert b_cell["not_estimable_reason"] == "boundary_estimate"
    # one A positive moved inside the negatives: variance > 0, delong_wald renders
    moved = run(separated_level_cohort(move_one=True), criteria_for(SITE_REF_B))
    cell = moved.row("site", "A")["diff_vs_reference"]["auroc"]
    assert cell["number"]["method"] == "delong_wald" and cell["detail"]["variance_a"] > 0.0
    assert moved.row("site", "A")["metrics"]["auroc"]["number"]["method"] == "delong_logit"


def test_every_per_level_proportion_matches_numpy_on_the_raw_columns_with_its_k_and_n():
    """Regression lens RG-B1 (and fresh-attack N4): at d1fd20a inverting PPV, NPV and
    accuracy left the whole suite green. Inspected here, for every level of sex and
    site: all six proportions' ``est``, ``k`` and ``n`` against a direct numpy
    computation on the raw columns, and every ``diff_vs_reference`` estimate as level
    minus reference from the same counts."""
    cols = make_cohort(n=400)
    rep = run(cols)
    y = np.array(cols["y_true"]) == "1"
    pred = np.array(cols["score"]) >= 0.5

    def by_hand(sel: np.ndarray) -> dict[str, tuple[int, int]]:
        p, q = y[sel], pred[sel]
        tp, fn = int((p & q).sum()), int((p & ~q).sum())
        fp, tn = int((~p & q).sum()), int((~p & ~q).sum())
        return {
            "sensitivity": (tp, tp + fn),
            "specificity": (tn, tn + fp),
            "ppv": (tp, tp + fp),
            "npv": (tn, tn + fn),
            "accuracy": (tp + tn, int(sel.sum())),
            "selection_rate": (tp + fp, int(sel.sum())),
        }

    checked = 0
    for attribute, reference in (("sex", "M"), ("site", None)):
        column = np.array(cols[attribute])
        levels = sorted(set(column.tolist()))
        if reference is None:
            reference = rep.attribute(attribute)["reference_level"]
        ref_hand = by_hand(column == reference)
        for level in levels:
            hand = by_hand(column == level)
            row = rep.row(attribute, level)
            block = row["metrics"]["op1"]
            for metric, (k, n) in hand.items():
                num = block[metric]["number"]
                assert num["k"] == k and num["n"] == n, (attribute, level, metric, num)
                assert num["est"] == pytest.approx(k / n), (attribute, level, metric)
                assert num["method"] == "wilson"
                checked += 1
                if level != reference:
                    d = row["diff_vs_reference"]["op1"][metric]["number"]
                    rk, rn = ref_hand[metric]
                    assert d["est"] == pytest.approx(k / n - rk / rn), (attribute, level, metric)
                    assert d["method"] == "newcombe10"
    assert checked == 6 * (2 + 3)


def test_the_frozen_share_rule_refuses_the_share_exactly_at_the_constant():
    """Fresh-attack lens FA-N1. The rule is ``frozen >= MAX_FROZEN_VARIANCE_SHARE``: the
    coverage grid's share-0.20 shape (one pure-positive case of three rows beside 36
    mixed cases, 9/45 = 0.2 exactly) is *refused*, and the share-0.10 shape (81 mixed)
    renders. This pins the boundary the corrected docstring and T7 text now describe. It
    passes at d1fd20a as well: the behaviour was never wrong, the sentence was."""
    assert MAX_FROZEN_VARIANCE_SHARE == 0.20

    def shape(mixed: int):
        pos = [True] * 3 + [False] * 30 + [True, False] * mixed
        ids = [0] * 3 + list(range(1, 31)) + [i for i in range(31, 31 + mixed) for _ in range(2)]
        return clustered_by_case(np.array(pos), np.array(ids))

    at_bar = shape(36)
    assert at_bar.frozen_variance_share["positive"] == pytest.approx(0.20)
    assert at_bar.deficient_class == "positive"
    below = shape(81)
    assert below.frozen_variance_share["positive"] == pytest.approx(0.10)
    assert below.deficient_class is None


def test_a_declared_reference_whose_rows_are_all_excluded_halts_h09_naming_the_analysed_rows():
    """Fresh-attack lens FA-N7. Every S3 row loses its score, so S3 is observed in the
    table but absent from the analysed rows; at d1fd20a the halt said the level was
    'not an observed level', which was untrue. The day-1 check on the raw table
    (``io.declare.check_references``) still passes, as it should."""
    cols = make_cohort(n=200)
    cols["score"] = [
        None if s == "S3" else v for v, s in zip(cols["score"], cols["site"], strict=True)
    ]
    crit = criteria_for(
        [{"attribute": "site", "prespecified": True, "source": "t", "reference_level": "S3"}]
    )
    assert "S3" in cols["site"]
    with pytest.raises(HaltError, match="analysed rows") as info:
        run(cols, crit)
    assert info.value.code == "H09"
    assert info.value.detail["reference_level"] == "S3"
    assert "observed" not in str(info.value)


# ------------------------------------------------------------ day-5 repair round 2
# The lens id each test answers is in its docstring, with what it fails on at 9da4401.


def separated_level_cohort_with_case_ids(move_one: bool = False) -> dict[str, list[Any]]:
    """:func:`separated_level_cohort` with every row duplicated under one case id, so a
    declared ``case_id`` unit routes every difference through the two-sided cluster
    bootstrap (lens 2, FA-B1's construction)."""
    base = separated_level_cohort(move_one=move_one)
    n = len(base["y_true"])
    cols = {k: [v[i // 2] for i in range(2 * n)] for k, v in base.items()}
    cols["case_id"] = [f"c{i // 2:04d}" for i in range(2 * n)]
    return cols


CLUSTERED_BY_CASE = {"clustering": {"unit": "case_id", "declared_by": "t"}}


def test_the_two_sided_cluster_bootstrap_refuses_a_difference_whose_one_side_is_frozen():
    """Fresh-attack lens 2 FA-B1. At 9da4401 the separated level A (own AUROC and own
    sensitivity refused ``boundary_estimate`` two keys away) had its AUROC difference
    rendered ``cluster_bootstrap_percentile`` 0.2256 (0.1599, 0.3054) and its sensitivity
    difference 0.35 (0.25, 0.4671) - each the other side's interval alone, shifted; the
    lens measured that AUROC interval covering the true difference in 0.295 of
    replicates and the sensitivity one in 0.615, at a nominal 0.95. Inspected here: on
    the AUROC and the sensitivity difference, against the reference and against the
    complement, from the frozen side (A) and from the side whose complement is frozen
    (B), the Number is ``boundary_estimate`` with the estimate carried as level minus
    other, method ``none``, no bounds, the clustered flags kept, and the cell records
    which side was frozen; with one A positive moved among the negatives nothing is
    frozen and the same cells render with an interval."""
    rep = run(separated_level_cohort_with_case_ids(), criteria_for(SITE_REF_B, **CLUSTERED_BY_CASE))
    row_a, row_b = rep.row("site", "A"), rep.row("site", "B")
    assert row_a["metrics"]["auroc"]["number"]["not_estimable_reason"] == "boundary_estimate"
    assert row_a["metrics"]["op1"]["sensitivity"]["number"]["not_estimable_reason"] == (
        "boundary_estimate"
    )
    auroc_b = row_b["metrics"]["auroc"]["number"]["est"]
    sens_b = row_b["metrics"]["op1"]["sensitivity"]["number"]
    assert 0.0 < auroc_b < 1.0 and 0 < sens_b["k"] < sens_b["n"]
    p_b = sens_b["k"] / sens_b["n"]
    checked = []
    for row, side, kinds, sign in (
        (row_a, "a", ("diff_vs_reference", "diff_vs_complement"), 1.0),
        (row_b, "b", ("diff_vs_complement",), -1.0),
    ):
        for kind in kinds:
            for cell, expected in (
                (row[kind]["auroc"], sign * (1.0 - auroc_b)),
                (row[kind]["op1"]["sensitivity"], sign * (1.0 - p_b)),
            ):
                num = cell["number"]
                assert num["not_estimable_reason"] == "boundary_estimate", (side, kind, num)
                assert num["method"] == "none" and num["ci_lo"] is None and num["ci_hi"] is None
                assert num["est"] == pytest.approx(expected), (side, kind, num["est"], expected)
                assert cell["analytic_status"] == "refused_clustered"
                assert cell["analytic"]["not_estimable_reason"] == (
                    "clustered_data_analytic_ci_invalid"
                )
                assert cell["bootstrap"]["resampling"]["frozen_sides"] == [side]
                assert Number(**num).not_estimable_reason in NOT_ESTIMABLE_REASONS
                checked.append((side, kind))
        flags_auroc = row[kinds[0]]["auroc"]["number"]["flags"]
        flags_sens = row[kinds[0]]["op1"]["sensitivity"]["number"]["flags"]
        assert "delong_refused_clustered" in flags_auroc
        assert "newcombe_refused_clustered" in flags_sens
    assert len(checked) == 6
    # B against the reference is null (B is the reference); B's own cells render
    assert row_b["diff_vs_reference"]["auroc"] is None
    assert row_b["metrics"]["auroc"]["number"]["method"] == "cluster_bootstrap_percentile"
    # the output with the refused differences still validates
    validator = jsonschema.Draft202012Validator(load_json_schema("output_schema_v1.json"))
    assert list(validator.iter_errors(_document(rep))) == []
    # one A positive moved inside the negatives: neither side is frozen, both render
    moved = run(
        separated_level_cohort_with_case_ids(move_one=True),
        criteria_for(SITE_REF_B, **CLUSTERED_BY_CASE),
    )
    for cell in (
        moved.row("site", "A")["diff_vs_reference"]["auroc"],
        moved.row("site", "A")["diff_vs_reference"]["op1"]["sensitivity"],
        moved.row("site", "B")["diff_vs_complement"]["auroc"],
    ):
        assert cell["number"]["method"] == "cluster_bootstrap_percentile", cell["number"]
        assert cell["number"]["ci_lo"] is not None
        assert cell["number"]["not_estimable_reason"] is None
        assert cell["bootstrap"]["resampling"]["frozen_sides"] == []


def test_frozen_sides_applies_the_single_cell_percentile_rule_to_each_side():
    """The unit of FA-B1's repair: :func:`_frozen_sides` names a side whose finite draws
    have coinciding ``alpha/2`` and ``1 - alpha/2`` quantiles - the rule
    :func:`bootstrap_percentile` refuses a single cell on - and nothing else. Inspected:
    a constant side, a side constant in all but one draw of 200 (the quantiles still
    coincide), a side with one NaN draw among constants, a varying side, and a side
    whose draws are all NaN (not named: there is nothing to freeze)."""
    const = np.full(200, 1.0)
    nearly = const.copy()
    nearly[7] = 0.9
    with_nan = const.copy()
    with_nan[3] = np.nan
    varying = np.linspace(0.0, 1.0, 200)
    all_nan = np.full(200, np.nan)
    f = subgroups_module._frozen_sides
    assert f({"a": const, "b": varying}, 0.95) == ("a",)
    assert f({"a": varying, "b": const}, 0.95) == ("b",)
    assert f({"a": const, "b": const}, 0.95) == ("a", "b")
    assert f({"a": nearly, "b": varying}, 0.95) == ("a",)
    assert f({"a": with_nan, "b": varying}, 0.95) == ("a",)
    assert f({"a": varying, "b": varying}, 0.95) == ()
    assert f({"a": all_nan, "b": varying}, 0.95) == ()
    # the constant side alone would be refused by the single-cell rule
    lo, hi = subgroups_module.percentile_bounds(const, 0.95)
    assert lo == hi


def test_fewer_than_two_evaluable_levels_is_insufficient_levels_on_every_route():
    """Lens 2 FA-N8 / RG-N2. At 9da4401 an all-Unknown or one-level attribute under a
    clustered plan reported ``clustered_data_analytic_ci_invalid`` with ``n_levels`` 0 or
    1, where the i.i.d. route reports ``insufficient_levels``. Inspected: both shapes,
    declared and detected, report ``insufficient_levels``; a two-level clustered
    attribute still reports the clustered refusal; the route is recorded either way."""
    n = 60
    base = make_cohort(n=n, with_case_id=True)
    dup = {k: [v[i // 2] for i in range(2 * n)] for k, v in base.items()}
    declared = criteria_for(SITE_LARGEST, **CLUSTERED_BY_CASE)
    detected = criteria_for(SITE_LARGEST)
    for site, n_levels in (([None] * (2 * n), 0), (["S1"] * (2 * n), 1)):
        cols = {**dup, "site": site}
        for crit, route in ((declared, "declared"), (detected, "detected")):
            foot = run(cols, crit).attribute("site")["heterogeneity"]
            assert foot["clustering_route"] == route
            for t in foot["tests"]:
                assert t["not_estimable_reason"] == "insufficient_levels", (route, n_levels, t)
                assert t["n_levels"] == n_levels and t["p_raw"] is None
    two = {**dup, "site": ["S1", "S1", "S2", "S2"] * (n // 2)}
    foot = run(two, declared).attribute("site")["heterogeneity"]
    assert {t["not_estimable_reason"] for t in foot["tests"]} == {
        "clustered_data_analytic_ci_invalid"
    }
    assert {t["n_levels"] for t in foot["tests"]} == {2}
    # the function itself, on the counts: the precedence does not depend on the table
    foot = subgroups_module.heterogeneity_footnote(
        {"op1": {"sensitivity": [(45, 5)], "specificity": [(40, 10), (38, 12)]}},
        clustering_route="declared",
    )
    by_metric = {t["metric"]: t["not_estimable_reason"] for t in foot["tests"]}
    assert by_metric == {
        "sensitivity": "insufficient_levels",
        "specificity": "clustered_data_analytic_ci_invalid",
    }


def test_the_heterogeneity_footnote_has_no_default_clustering_route():
    """Lens 2 FA-N9. At 9da4401 ``clustering_route`` defaulted to ``"none"``, so a direct
    call that forgot it computed the row test (F6: p 0.0986). Inspected: the call
    without the keyword raises ``TypeError``; with it, the F6 figures are unchanged."""
    per_op = {"op1": {"sensitivity": [(45, 5), (38, 12), (27, 3)]}}
    with pytest.raises(TypeError, match="clustering_route"):
        subgroups_module.heterogeneity_footnote(per_op)  # type: ignore[call-arg]
    foot = subgroups_module.heterogeneity_footnote(per_op, clustering_route="none")
    approx4(foot["tests"][0]["p_raw"], 0.0986)


def test_the_sentences_lens_2_falsified_are_gone_from_the_shipped_text():
    """Lens 2 FA-N2 / RG-N1 / FA-N3. Inspected: the two phrases the lens falsified by
    measurement - "at every seed tried" beside a 0.870 and a 0.880, and "not
    implemented for the proportion route" while the AUROC route renders shapes below
    the bar too - are absent from ``design/conventions_T7.md`` and
    ``src/proofpack/stats/bootstrap.py``, and the two measurements that falsified them
    are recorded there. A grep on prose, not a check on behaviour."""
    t7 = (REPO / "design" / "conventions_T7.md").read_text(encoding="utf-8")
    bootstrap_src = (REPO / "src" / "proofpack" / "stats" / "bootstrap.py").read_text(
        encoding="utf-8"
    )
    for text in (t7, bootstrap_src):
        assert "at every seed tried" not in text
        assert "not implemented** for the proportion route" not in text
        assert "not implemented for the proportion route" not in text
        assert "0.880" in text and "0.870" in text
    assert "on either route" in t7
