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
  discordant counts through :func:`compare_versions`;
* **the F5 pair under ``case_id = c{i // 2}``** (E10 repair 1, lens 1 FA-B1): the six
  sensitivity / specificity cells (overall and both ``sex`` entries) equal a seed-fixed
  re-run of ``clustered_flat`` + ``bootstrap_percentile`` on the same conditioned pairs
  (at 322c5a4 they were refused ``insufficient_clusters``), and the twelve proportion
  and AUROC cells carry DEC-09's typed refusal beside a cluster-bootstrap Number while
  the two calibration cells carry no companion;
* **the five cluster-bootstrap cells that go through ``clustered_by_case``** (E10 repair
  2, lens 2 FA-F3: the overall AUROC, Brier and slope cells and both ``sex`` AUROC cells)
  equal a seed-fixed re-run of that resampler with the engine's cell key; the DEC-09
  refusal beside a conditioned cell carries the conditioned pair count; every
  cluster-bootstrap interval on the F5 pair brackets its estimate;
* ``paired_delong`` has the three callers in ``src`` its docstring names (lens 2 FA-F1).
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

from proofpack.stats import comparison as cmp
from proofpack.stats.bootstrap import (
    BootstrapPolicy,
    bootstrap_percentile,
    clustered_by_case,
    clustered_flat,
    plan_clustering,
)
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
    formula is [unverified] against the primary source (no worked example of the paired
    paper is in the repository; ``fixtures/newcombe_table2.json`` holds three examples
    of the *independent*-proportions paper, ``56/70 - 48/80`` and two more):

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


def _f5_clustered(policy: BootstrapPolicy):
    """The F5 pair with ``case_id = c{i // 2}`` (two rows per case, 50 cases), the
    ``sex`` levels as subgroup entries, through :func:`compare_versions`."""
    new, prior, join = _f5_arrays()
    ids = np.array([f"c{i // 2}" for i in range(100)], dtype=object)
    new = cmp.VersionArrays(new.pos, new.score, new.probability, new.pred, ids)
    prior = cmp.VersionArrays(prior.pos, prior.score, prior.probability, prior.pred, ids)
    plan = plan_clustering("case_id", ids, 100)
    assert plan.clustered
    with (F5 / "f5_new.csv").open(encoding="utf-8", newline="") as fh:
        sex = np.array([r["sex"] for r in csv.DictReader(fh)])
    subgroups = [
        {"attribute": "sex", "level": lv, "rows": np.flatnonzero(sex == lv)} for lv in ("M", "F")
    ]
    block = cmp.compare_versions(
        new,
        prior,
        paired=True,
        join=join,
        ops=["op1"],
        plan=plan,
        policy=policy,
        subgroups=subgroups,
    )
    return new, prior, ids, block


def test_f5_case_id_c_i_over_2_se_sp_cells_equal_a_clustered_flat_rerun():
    """Lens 1 FA-B1 (E10 repair 1). At 322c5a4 the six sensitivity / specificity cells
    below (overall and both ``sex`` entries) came back with no interval and the reason
    ``insufficient_clusters`` beside ``n_cases`` 26 / 24, because the conditioned cell was
    resampled by ``clustered_by_case``, whose second outcome stratum is empty on a
    conditioned cell. The cells now go through ``clustered_flat`` (the resampler
    ``proportion_ci`` uses); this test re-runs that resampler with the same seed, key
    and B on the same conditioned pairs and asserts the identical interval."""
    policy = BootstrapPolicy(n_resamples=200, seed=20240101)
    new, prior, ids, block = _f5_clustered(policy)
    with (F5 / "f5_new.csv").open(encoding="utf-8", newline="") as fh:
        sex = np.array([r["sex"] for r in csv.DictReader(fh)])
    expected_cases = {
        ("overall", "sensitivity"): 26,
        ("overall", "specificity"): 26,
        ("M", "sensitivity"): 26,
        ("M", "specificity"): 24,
        ("F", "sensitivity"): 24,
        ("F", "specificity"): 26,
    }
    entries = {"overall": (np.arange(100), block["differences"])}
    for e in block["subgroups"]:
        entries[e["level"]] = (np.flatnonzero(sex == e["level"]), e["differences"])
    checked = 0
    for (scope, metric), n_cases in expected_cases.items():
        rows, diffs = entries[scope]
        cell = diffs["op1"][metric]
        num, ana = cell["number"], cell["analytic"]
        assert cell["analytic_status"] == "refused_clustered"
        assert ana["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
        assert num["method"] == "cluster_bootstrap_percentile", (scope, metric, num)
        assert num["not_estimable_reason"] is None
        assert num["ci_lo"] is not None and num["ci_hi"] is not None
        assert num["ci_lo"] < num["est"] < num["ci_hi"]
        assert num["flags"] == ["newcombe_refused_clustered"]
        assert num["n_cases"] == n_cases and num["est"] == ana["est"]
        # the oracle: the same resampler, seed, key and B on the same conditioned pairs
        pos = new.pos[rows]
        sel = pos if metric == "sensitivity" else ~pos
        pred_new, pred_prior = new.pred["op1"][rows][sel], prior.pred["op1"][rows][sel]
        if metric == "specificity":
            pred_new, pred_prior = ~pred_new, ~pred_prior
        a, b = pred_new.astype(np.float64), pred_prior.astype(np.float64)
        assert num["n"] == int(sel.sum()) and abs(num["est"] - (a.mean() - b.mean())) < 1e-12
        # E10 repair 2 (lens 2 FA-F3, mutant M5): the DEC-09 refusal beside the cell
        # carries the conditioned pair count too (50 / 26 / 24 here), not the 100 pairs
        assert ana["n"] == int(sel.sum()) and ana["n"] < 100, (scope, metric, ana)
        resampler = clustered_flat(ids[rows][sel], n_rows=int(sel.sum()))
        assert resampler.n_units == n_cases
        key_parts = ("overall",) if scope == "overall" else ("subgroups", "sex", scope)
        short = "se" if metric == "sensitivity" else "sp"
        key = json.dumps(["comparison", *key_parts, "op1", short])

        def stat(idx: np.ndarray, a: np.ndarray = a, b: np.ndarray = b) -> float:
            return float(a[idx].mean() - b[idx].mean())

        draw = bootstrap_percentile(stat, resampler, policy.rng(key), 200, 0.95)
        assert draw.reason is None
        assert (num["ci_lo"], num["ci_hi"]) == (draw.ci_lo, draw.ci_hi), (scope, metric)
        checked += 1
    assert checked == 6
    # the figures measured on 25 September 2026 (B 200, seed 20240101), overall
    se, sp = block["differences"]["op1"]["sensitivity"], block["differences"]["op1"]["specificity"]
    assert se["number"]["est"] == -0.08 and sp["number"]["est"] == -0.08
    assert (round(se["number"]["ci_lo"], 4), round(se["number"]["ci_hi"], 4)) == (-0.2, 0.0196)
    assert (round(sp["number"]["ci_lo"], 4), round(sp["number"]["ci_hi"], 4)) == (-0.2, 0.0204)


def test_f5_c_i_over_2_twelve_cells_refused_analytic_and_two_calibration_cells_no_companion():
    """The fourteen cells of the F5 pair under ``case_id = c{i // 2}``: overall
    sensitivity, specificity, accuracy, AUROC, Brier, slope and, for each ``sex`` entry,
    sensitivity, specificity, accuracy, AUROC. The twelve proportion and AUROC cells
    carry the DEC-09 refusal as ``analytic`` and a ``cluster_bootstrap_percentile``
    Number with its ``*_refused_clustered`` flag; the two calibration cells are cluster
    bootstraps with no analytic companion (``analytic`` is None). Every one of the
    fourteen intervals brackets its estimate (E10 repair 2, lens 2 FA-F3 mutant M11: with
    the AUROC resample statistic's sign flipped, lens 2 measured the AUROC cell printing
    ``[-0.0001, +0.1734]`` around ``-0.0776`` and the three E10 test files passing at
    667a201, 44 passed; re-measured in repair 2, and this test fails on that mutant
    now). Named for what it asserts (lens 2 FA-F2: the name at 667a201 said fourteen
    cells carry the refusal)."""
    _, _, _, block = _f5_clustered(BootstrapPolicy(n_resamples=100, seed=1))
    cells = []
    for diffs in (block["differences"], *(e["differences"] for e in block["subgroups"])):
        for metric in ("sensitivity", "specificity", "accuracy"):
            cells.append((diffs["op1"][metric], "newcombe_refused_clustered"))
        cells.append((diffs["auroc"], "delong_refused_clustered"))
    for cell, flag in cells:
        assert cell["analytic_status"] == "refused_clustered"
        assert cell["analytic"]["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
        assert cell["analytic"]["method"] == "none"
        assert cell["number"]["method"] == "cluster_bootstrap_percentile"
        assert cell["number"]["ci_lo"] is not None
        assert flag in cell["number"]["flags"]
        assert cell["number"]["est"] == cell["analytic"]["est"]
    assert len(cells) == 12
    assert block["differences"]["op1"]["accuracy"]["number"]["n_cases"] == 50
    assert block["differences"]["auroc"]["number"]["n_cases"] == 50
    for key in ("brier", "slope"):
        cell = block["differences"][key]
        assert cell["number"]["method"] == "cluster_bootstrap_percentile"
        assert cell["analytic"] is None and cell["analytic_status"] == "used"
        cells.append((cell, None))
    assert len(cells) == 14
    for cell, _ in cells:
        num = cell["number"]
        assert num["ci_lo"] < num["est"] < num["ci_hi"], num
    assert block["clustering_route"] == "declared"


def test_f5_case_id_c_i_over_2_auroc_brier_slope_cells_equal_a_clustered_by_case_rerun():
    """Lens 2 FA-F3 (E10 repair 2), mutants M10 and M11: the five cells the comparison
    resamples through ``clustered_by_case`` (cases resampled within outcome class:
    positive 24 / negative 24 / mixed 2 on the F5 pair under ``case_id = c{i // 2}``) -
    the overall AUROC, Brier and slope differences and both ``sex`` AUROC differences -
    equal a seed-fixed re-run of that resampler with the engine's cell key, B 200, seed
    20240101. At 667a201 lens 2's mutants M10 (the three cells resampled in one stratum
    through ``clustered_flat``) and M11 (the AUROC resample statistic's sign flipped)
    each passed the three E10 test files (44 passed; re-measured in repair 2); with this
    test in the file each is killed (M10 by this test alone, M11 by this test and the
    fourteen-cells test above). The overall AUROC and Brier figures measured on 25
    September 2026 are pinned to four decimals at the end."""
    policy = BootstrapPolicy(n_resamples=200, seed=20240101)
    new, prior, ids, block = _f5_clustered(policy)
    with (F5 / "f5_new.csv").open(encoding="utf-8", newline="") as fh:
        sex = np.array([r["sex"] for r in csv.DictReader(fh)])
    scopes = {"overall": np.arange(100)}
    for e in block["subgroups"]:
        scopes[e["level"]] = np.flatnonzero(sex == e["level"])
    y = new.pos.astype(np.float64)
    sq_new, sq_prior = (new.probability - y) ** 2, (prior.probability - y) ** 2
    ln, lp = cmp._logit(new.probability), cmp._logit(prior.probability)
    checked = 0
    for scope, rows in scopes.items():
        diffs = block["differences"] if scope == "overall" else None
        if diffs is None:
            (diffs,) = [e["differences"] for e in block["subgroups"] if e["level"] == scope]
        key_parts = ("overall",) if scope == "overall" else ("subgroups", "sex", scope)
        pos, sn, sp = new.pos[rows], new.score[rows], prior.score[rows]
        resampler = clustered_by_case(pos, ids[rows])
        assert resampler.kind == "clustered"
        if scope == "overall":
            assert resampler.units_per_stratum == {"positive": 24, "negative": 24, "mixed": 2}

        def auroc_stat(idx: np.ndarray, pos=pos, sn=sn, sp=sp) -> float:
            p = pos[idx]
            if not p.any() or p.all():
                return float("nan")
            return float(cmp.auroc_mann_whitney(sn[idx], p) - cmp.auroc_mann_whitney(sp[idx], p))

        stats = {"auroc": auroc_stat}
        if scope == "overall":

            def brier_stat(idx: np.ndarray) -> float:
                return float(sq_new[idx].mean() - sq_prior[idx].mean())

            def slope_stat(idx: np.ndarray) -> float:
                return cmp._slope(y[idx], ln[idx]) - cmp._slope(y[idx], lp[idx])

            stats.update({"brier": brier_stat, "slope": slope_stat})
        for key, stat in stats.items():
            num = diffs[key]["number"]
            assert num["method"] == "cluster_bootstrap_percentile", (scope, key, num)
            assert num["n_cases"] == resampler.n_units
            draw = bootstrap_percentile(
                stat, resampler, policy.rng(json.dumps(["comparison", *key_parts, key])), 200, 0.95
            )
            assert draw.reason is None
            assert (num["ci_lo"], num["ci_hi"]) == (draw.ci_lo, draw.ci_hi), (scope, key)
            assert draw.ci_lo < num["est"] < draw.ci_hi
            checked += 1
    assert checked == 5
    auroc = block["differences"]["auroc"]["number"]
    own = cmp.auroc_mann_whitney(new.score, new.pos) - cmp.auroc_mann_whitney(
        prior.score, prior.pos
    )
    assert abs(auroc["est"] - own) < 1e-12
    assert (round(auroc["est"], 4), round(auroc["ci_lo"], 4), round(auroc["ci_hi"], 4)) == (
        -0.0776,
        -0.1734,
        0.0001,
    )
    brier = block["differences"]["brier"]["number"]
    assert (round(brier["est"], 4), round(brier["ci_lo"], 4), round(brier["ci_hi"], 4)) == (
        0.0388,
        -0.0068,
        0.0906,
    )


def test_paired_delong_has_three_callers_in_src_as_its_docstring_names():
    """Lens 2 FA-F1: at 667a201 ``stats/discrimination.py`` said ``paired_delong`` had one
    caller in ``src`` while ``fixtures.py`` called it twice. The literal call sites,
    counted by grep over ``src``, and the two docstrings naming all three."""
    src = REPO / "src" / "proofpack"
    calls: dict[str, int] = {}
    for path in sorted(src.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        # a call site: the name followed by an argument; not ``unpaired_delong(``, not
        # ``def paired_delong(`` and not the grep line quoted in the module docstring
        n = len(re.findall(r"(?<![a-z])paired_delong\([a-z]", text))
        if n:
            calls[path.relative_to(src).as_posix()] = n
    assert calls == {"fixtures.py": 2, "stats/comparison.py": 1}
    module_doc = (src / "stats" / "discrimination.py").read_text(encoding="utf-8")
    assert "Its callers in ``src`` are three" in module_doc
    assert "one caller in ``src``" not in module_doc
    assert "fixtures._f3_delong" in paired_delong.__doc__
    assert "fixtures._f5_delong_pair" in paired_delong.__doc__


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
