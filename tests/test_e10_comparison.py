"""Build day 10 (E10 item 1): ``stats.comparison`` against its oracles and hand derivations.

* **McNemar on R2 section 9 F5** (``b = 10``, ``c = 2``, ``[[80, 10], [2, 8]]``): the exact
  ``p`` and the continuity-corrected chi-square and its ``p`` equal
  ``statsmodels.stats.contingency_tables.mcnemar`` to 1e-6 and R2's printed figures
  (0.0386; 4.0833, 0.0433) to their rounding; ``b + c = 24`` takes the exact route and
  ``b + c = 25`` the corrected one; ``b = c = 0`` gives ``p = 1`` with no statistic;
* **the Newcombe paired interval of the F5 accuracy difference** equals this test's own
  derivation from the published formula, stated in :func:`newcombe_paired_by_hand`;
  the formula's source status is **[unverified]** (the paper was not fetched; the
  register row ``F5-newcombe-paired`` says so and is never ``matched``);
* **the paired DeLong difference on R2's F3 pair** equals this test's own O(m n)
  structural-component computation (DeLong 1988, with the covariance term) to 1e-9;
* **the bootstrap differences reproduce under the same seed** (two calls, one document);
* **the unpaired path labels every Number** (method ``*_not_like_for_like`` and the flag);
* the module imports no renderer or oracle library; the F5 fixture pair reproduces the
  discordant counts through :func:`compare_versions`; a clustered plan carries DEC-09's
  typed refusal beside every cluster-bootstrap difference.
"""

from __future__ import annotations

import csv
import math
import statistics
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

from proofpack.stats import comparison as cmp
from proofpack.stats.bootstrap import BootstrapPolicy, plan_clustering
from proofpack.stats.discrimination import paired_delong
from proofpack.stats.number import METHODS, NOT_ESTIMABLE_REASONS
from proofpack.stats.proportions import difference_paired, wilson_bounds

pytestmark = pytest.mark.day10

REPO = Path(__file__).resolve().parent.parent
F5 = REPO / "tests" / "fixtures" / "f5"
Z = statistics.NormalDist().inv_cdf(0.975)

# R2 section 9 F3
F3_Y = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0], dtype=bool)
F3_S1 = np.array([0.9, 0.8, 0.7, 0.6, 0.35, 0.75, 0.5, 0.4, 0.3, 0.2])
F3_S2 = np.array([0.85, 0.6, 0.65, 0.4, 0.3, 0.7, 0.55, 0.45, 0.35, 0.25])


# ------------------------------------------------------------------ McNemar


def test_f5_mcnemar_equals_statsmodels_and_the_register_figures():
    sm = pytest.importorskip("statsmodels.stats.contingency_tables")
    exact = cmp.mcnemar(10, 2)
    assert exact.method == "exact_mcnemar" and exact.statistic is None
    assert exact.n_discordant == 12
    assert abs(exact.p - sm.mcnemar([[80, 10], [2, 8]], exact=True).pvalue) < 1e-6
    assert round(exact.p, 4) == 0.0386  # R2 section 9 F5
    cc = cmp.mcnemar(10, 2, exact=False)
    ref = sm.mcnemar([[80, 10], [2, 8]], exact=False, correction=True)
    assert cc.method == "cc_mcnemar"
    assert abs(cc.statistic - ref.statistic) < 1e-6 and abs(cc.p - ref.pvalue) < 1e-6
    assert round(cc.statistic, 4) == 4.0833 and round(cc.p, 4) == 0.0433
    # the exact p is two-sided: 2 * P(X <= 2) for X ~ Binomial(12, 1/2), by hand
    assert exact.p == 2 * (math.comb(12, 0) + math.comb(12, 1) + math.comb(12, 2)) / 2**12


def test_the_exact_route_below_25_discordant_pairs_and_the_corrected_route_at_25():
    sm = pytest.importorskip("statsmodels.stats.contingency_tables")
    at24 = cmp.mcnemar(14, 10)
    assert at24.method == "exact_mcnemar" and at24.n_discordant == 24
    assert abs(at24.p - sm.mcnemar([[0, 14], [10, 0]], exact=True).pvalue) < 1e-6
    at25 = cmp.mcnemar(15, 10)
    assert at25.method == "cc_mcnemar" and at25.n_discordant == 25
    ref = sm.mcnemar([[0, 15], [10, 0]], exact=False, correction=True)
    assert abs(at25.statistic - ref.statistic) < 1e-6 and abs(at25.p - ref.pvalue) < 1e-6
    assert at25.statistic == (abs(15 - 10) - 1) ** 2 / 25
    assert cmp.EXACT_BELOW == 25


def test_no_discordant_pairs_gives_p_one_and_no_statistic():
    zero = cmp.mcnemar(0, 0)
    assert zero.p == 1.0 and zero.statistic is None and zero.method == "exact_mcnemar"
    assert zero.as_dict() == {
        "b": 0,
        "c": 0,
        "n_discordant": 0,
        "statistic": None,
        "p": 1.0,
        "method": "exact_mcnemar",
    }
    forced = cmp.mcnemar(0, 0, exact=False)
    assert forced.p == 1.0 and forced.statistic is None
    with pytest.raises(ValueError):
        cmp.mcnemar(-1, 2)


# ------------------------------------------------------------------ Newcombe paired


def newcombe_paired_by_hand(e: int, f: int, g: int, h: int) -> tuple[float, float, float]:
    """Newcombe (1998, Stat Med 17:2635-2650, 'Improved confidence intervals for the
    difference between binomial proportions based on paired data') **method 10**, as
    this test states it - the paper was not fetched in this build environment, so the
    formula is [unverified] against the primary source (the same status as
    ``fixtures/newcombe_table2.json``'s three paired examples):

        n = e + f + g + h;  p1 = (e + f) / n;  p2 = (e + g) / n;  d = p1 - p2 = (f - g) / n
        (l1, u1), (l2, u2): the Wilson score intervals of p1 and p2 (no continuity correction)
        A = (e + f)(g + h)(e + g)(f + h);  phi = 0 when A = 0, else
        phi = (e h - f g) / sqrt(A), with e h - f g replaced by max(e h - f g - n / 2, 0)
              when e h - f g > 0 (the method-10 continuity correction of phi)
        delta = sqrt((p1 - l1)^2 - 2 phi (p1 - l1)(u2 - p2) + (u2 - p2)^2);  L = d - delta
        eps   = sqrt((u1 - p1)^2 - 2 phi (u1 - p1)(p2 - l2) + (p2 - l2)^2);  U = d + eps
    """
    n = e + f + g + h
    p1, p2 = (e + f) / n, (e + g) / n
    d = p1 - p2
    l1, u1 = wilson_bounds(e + f, n)
    l2, u2 = wilson_bounds(e + g, n)
    a = (e + f) * (g + h) * (e + g) * (f + h)
    if a == 0:
        phi = 0.0
    else:
        num = e * h - f * g
        if num > 0:
            num = max(num - n / 2, 0)
        phi = num / math.sqrt(a)
    delta = math.sqrt((p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2)
    eps = math.sqrt((u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2)
    return d, d - delta, d + eps


def test_f5_newcombe_paired_interval_equals_the_hand_derivation_and_is_frozen():
    # F5 as a paired accuracy table, new minus prior: e both correct 80, f new only 2 (c),
    # g prior only 10 (b), h neither 8
    d, lo, hi = newcombe_paired_by_hand(80, 2, 10, 8)
    num = difference_paired(80, 2, 10, 8)
    assert num.method == "newcombe_paired" and num.n == 100
    assert abs(num.est - d) < 1e-12 and abs(d + 0.08) < 1e-12
    assert abs(num.ci_lo - lo) < 1e-12 and abs(num.ci_hi - hi) < 1e-12
    # the frozen figures, four decimals (the register row F5-newcombe-paired states them
    # [unverified]; R2's Wald interval (-0.1461, -0.0139) is a different interval)
    assert (round(lo, 4), round(hi, 4)) == (-0.1554, -0.0102)
    assert lo < -0.05 < hi
    # the same through the comparison module's indicator form
    new = np.array([True] * 80 + [True] * 2 + [False] * 10 + [False] * 8)
    prior = np.array([True] * 80 + [False] * 2 + [True] * 10 + [False] * 8)
    via = cmp.paired_proportion_difference(new, prior)
    assert via.as_dict() == num.as_dict()


@pytest.mark.parametrize("cells", [(36, 12, 2, 0), (2, 98, 0, 0), (0, 30, 0, 0), (5, 3, 7, 9)])
def test_the_engine_paired_interval_follows_the_stated_formula_on_other_tables(cells):
    d, lo, hi = newcombe_paired_by_hand(*cells)
    num = difference_paired(*cells)
    assert abs(num.est - d) < 1e-12
    assert abs(num.ci_lo - max(lo, -1.0)) < 1e-12 and abs(num.ci_hi - min(hi, 1.0)) < 1e-12


# ------------------------------------------------------------------ paired DeLong


def delong_by_hand(scores: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """DeLong 1988 structural components, O(m n): psi(x, y) = 1 if x > y, 1/2 if x == y,
    0 otherwise; V10[i] = mean_j psi(x_i, y_j) over the negatives, V01[j] = mean_i
    psi(x_i, y_j) over the positives; AUC = mean(V10) = mean(V01)."""
    x, yy = scores[y], scores[~y]
    psi = (x[:, None] > yy[None, :]).astype(float) + 0.5 * (x[:, None] == yy[None, :])
    return float(psi.mean()), psi.mean(axis=1), psi.mean(axis=0)


def test_the_paired_delong_difference_on_f3_equals_the_hand_computation_to_1e_9():
    a1, v10_1, v01_1 = delong_by_hand(F3_S1, F3_Y)
    a2, v10_2, v01_2 = delong_by_hand(F3_S2, F3_Y)
    m, n0 = int(F3_Y.sum()), int((~F3_Y).sum())
    s10 = np.cov(np.vstack([v10_1, v10_2]), ddof=1)
    s01 = np.cov(np.vstack([v01_1, v01_2]), ddof=1)
    s = s10 / m + s01 / n0
    var_diff = s[0, 0] + s[1, 1] - 2 * s[0, 1]  # the covariance term is real: same cases
    diff = a1 - a2
    result = paired_delong(F3_S1, F3_S2, F3_Y)
    assert abs(result.difference.est - diff) < 1e-9
    assert abs(result.variance_difference - var_diff) < 1e-9
    assert abs(result.difference.ci_lo - (diff - Z * math.sqrt(var_diff))) < 1e-9
    assert abs(result.difference.ci_hi - (diff + Z * math.sqrt(var_diff))) < 1e-9
    assert abs(var_diff - 0.0072) < 1e-12 and abs(diff - 0.16) < 1e-12  # R2 section 9 F3
    assert abs(result.z - 1.8856) < 5e-5 and abs(result.p_value - 0.0593) < 5e-5
    # without the covariance term the variance would be the unpaired sum, larger
    assert var_diff < s[0, 0] + s[1, 1]


# ------------------------------------------------------------------ the fixture pair


def _f5_arrays() -> tuple[cmp.VersionArrays, cmp.VersionArrays, cmp.Join]:
    def load(name: str) -> list[dict[str, str]]:
        with (F5 / name).open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    new, prior = load("f5_new.csv"), load("f5_prior.csv")
    join = cmp.paired_join(
        [r["row_id"] for r in new],
        [r["row_id"] for r in prior],
        [r["y_true"] for r in new],
        [r["y_true"] for r in prior],
    )

    def arrays(rows: list[dict[str, str]]) -> cmp.VersionArrays:
        pos = np.array([r["y_true"] == "1" for r in rows])
        score = np.array([float(r["score"]) for r in rows])
        return cmp.VersionArrays(
            pos=pos, score=score, probability=score, pred={"op1": score >= 0.5}, case_ids=None
        )

    return arrays(new).take(join.new_index), arrays(prior).take(join.prior_index), join


def test_the_f5_fixture_pair_reproduces_b_10_c_2_through_compare_versions():
    new, prior, join = _f5_arrays()
    assert join.paired and join.n_pairs == 100 and join.as_dict()["label_mismatch"] == 0
    crit = yaml.safe_load((F5 / "criteria.yaml").read_text(encoding="utf-8"))
    assert crit["criteria"][1]["type"] == "paired_difference_vs_prior"
    assert crit["criteria"][1]["value"] == -0.05  # the customer's margin, in the fixture only
    block = cmp.compare_versions(
        new,
        prior,
        paired=True,
        join=join,
        ops=["op1"],
        policy=BootstrapPolicy(n_resamples=200, seed=20240101),
    )
    assert block["paired"] is True and block["label"] is None and block["n_pairs"] == 100
    assert block["mcnemar"]["op1"] == cmp.mcnemar(10, 2).as_dict()
    acc = block["differences"]["op1"]["accuracy"]["number"]
    assert acc["method"] == "newcombe_paired" and acc["n"] == 100
    assert abs(acc["est"] + 0.08) < 1e-12
    hand = newcombe_paired_by_hand(80, 2, 10, 8)
    assert abs(acc["ci_lo"] - hand[1]) < 1e-12 and abs(acc["ci_hi"] - hand[2]) < 1e-12
    for key in ("sensitivity", "specificity"):
        assert block["differences"]["op1"][key]["number"]["method"] == "newcombe_paired"
        assert block["differences"]["op1"][key]["number"]["n"] == 50
    assert block["differences"]["auroc"]["number"]["method"] == "delong_wald"
    for key in ("brier", "slope"):
        assert block["differences"][key]["number"]["method"] == "bootstrap_percentile"
        assert block["differences"][key]["analytic_status"] == "used"
    assert block["subgroups"] == [] and block["subgroups_not_computed"] is None


def test_the_bootstrap_differences_reproduce_under_the_same_seed():
    new, prior, join = _f5_arrays()
    policy = BootstrapPolicy(n_resamples=100, seed=7)
    a = cmp.compare_versions(new, prior, paired=True, join=join, ops=["op1"], policy=policy)
    b = cmp.compare_versions(new, prior, paired=True, join=join, ops=["op1"], policy=policy)
    assert a == b
    assert a["bootstrap"] == {"B": 100, "seed": 7, "interval": "percentile"}
    other = cmp.compare_versions(
        new,
        prior,
        paired=True,
        join=join,
        ops=["op1"],
        policy=BootstrapPolicy(n_resamples=100, seed=8),
    )
    assert other["differences"]["brier"] != a["differences"]["brier"]


def test_a_clustered_plan_bootstraps_every_difference_and_carries_dec_09s_refusal():
    new, prior, join = _f5_arrays()
    ids = np.array([f"c{i // 2}" for i in range(100)], dtype=object)
    new = cmp.VersionArrays(new.pos, new.score, new.probability, new.pred, ids)
    prior = cmp.VersionArrays(prior.pos, prior.score, prior.probability, prior.pred, ids)
    plan = plan_clustering("case_id", ids, 100)
    assert plan.clustered
    block = cmp.compare_versions(
        new,
        prior,
        paired=True,
        join=join,
        ops=["op1"],
        plan=plan,
        policy=BootstrapPolicy(n_resamples=100, seed=1),
    )
    for cell, flag in (
        (block["differences"]["op1"]["accuracy"], "newcombe_refused_clustered"),
        (block["differences"]["auroc"], "delong_refused_clustered"),
    ):
        assert cell["analytic_status"] == "refused_clustered"
        assert cell["analytic"]["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
        assert cell["analytic"]["method"] == "none"
        assert cell["number"]["method"] == "cluster_bootstrap_percentile"
        assert flag in cell["number"]["flags"]
        assert cell["number"]["n_cases"] == 50
        assert cell["number"]["est"] == cell["analytic"]["est"]
    assert block["differences"]["brier"]["number"]["method"] == "cluster_bootstrap_percentile"
    assert block["clustering_route"] == "declared"


# ------------------------------------------------------------------ unpaired


def test_the_unpaired_path_labels_every_number_not_like_for_like():
    new, prior, _ = _f5_arrays()
    prior = prior.take(np.arange(5, 100))  # different rows: no join (both arms mixed)
    block = cmp.compare_versions(new, prior, paired=False, join=None, ops=["op1"])
    assert block["paired"] is False and block["label"] == "not like-for-like"
    assert block["unpaired_rows"] == {
        "n_pairs": 0,
        "new_only": 100,
        "prior_only": 95,
        "label_mismatch": 0,
    }
    with pytest.raises(ValueError):
        cmp.compare_versions(new, prior, paired=True, join=None, ops=["op1"])
    assert block["mcnemar"] is None and block["n_pairs"] is None
    assert block["subgroups"] == []
    assert block["subgroups_not_computed"] == "unpaired_not_like_for_like"
    numbers = []
    for key, value in block["differences"].items():
        cells = value.values() if key not in ("auroc", "brier", "slope") else [value]
        for cell in cells:
            numbers.append(cell["number"])
            if cell["analytic"] is not None:
                numbers.append(cell["analytic"])
    assert len(numbers) >= 7
    for num in numbers:
        assert "not_like_for_like" in num["flags"], num
        if num["ci_lo"] is not None:
            assert num["method"].endswith("_not_like_for_like"), num
            assert num["method"] in METHODS
        else:
            assert num["not_estimable_reason"] in NOT_ESTIMABLE_REASONS
    acc = block["differences"]["op1"]["accuracy"]["number"]
    assert acc["method"] == "newcombe10_not_like_for_like"
    assert block["differences"]["auroc"]["number"]["method"] == "delong_wald_not_like_for_like"
    for key in ("brier", "slope"):
        assert block["differences"][key]["number"]["not_estimable_reason"] == (
            "unpaired_not_like_for_like"
        )


def test_paired_join_counts_unmatched_and_label_mismatched_rows():
    join = cmp.paired_join(
        ["a", "b", "c", None], ["c", "b", "x"], ["1", "0", "1", "0"], ["0", "0", "1"]
    )
    assert join.n_pairs == 1 and join.new_only == 2 and join.prior_only == 1
    assert join.label_mismatch == 1 and not join.paired
    assert join.new_index.tolist() == [1] and join.prior_index.tolist() == [1]
    full = cmp.paired_join(["a", "b"], ["b", "a"])
    assert full.paired and full.n_pairs == 2
    assert full.new_index.tolist() == [0, 1] and full.prior_index.tolist() == [1, 0]


# ------------------------------------------------------------------ module hygiene


def test_the_comparison_module_imports_no_oracle_or_renderer():
    src = (REPO / "src" / "proofpack" / "stats" / "comparison.py").read_text(encoding="utf-8")
    imports = [ln for ln in src.splitlines() if ln.startswith(("import ", "from "))]
    for name in ("jinja2", "statsmodels", "sklearn", "scikit"):
        assert not any(name in ln for ln in imports), name
    before = set(sys.modules)
    import importlib

    importlib.reload(cmp)
    assert not ({"jinja2", "statsmodels", "sklearn"} & (set(sys.modules) - before))
