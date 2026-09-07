"""Day 4 (E4) - ``stats.bootstrap``: stratified and clustered resampling.

Three things are being proved here.

**F3 - the resampling algorithm is pinned.** R2 section 9 records the F3 stratified
bootstrap AUROC interval as ``(0.44, 1.00)`` at B = 2000 with
``default_rng(20240101)``, positives and negatives resampled separately. That is
reproduced exactly, which pins the scheme (which units are drawn, in which order,
with which quantile convention) rather than merely testing that some interval comes
back.

**The bootstrap-vs-DeLong tolerance.** Stated once, here, before any measurement, and
derived rather than tuned. The Monte-Carlo standard error of a percentile endpoint at
B resamples is ``sqrt(p(1-p)/B) / f(q_p)``; approximating the bootstrap distribution
by a normal with standard deviation ``sd`` gives ``f(q_p) = phi(z_{1-p})/sd``, so the
endpoint carries ``sqrt(p(1-p)/B) * sd / phi(z)`` of pure Monte-Carlo noise - at
p = 0.025 and B = 2000 that is ``0.0598 * sd``. Where the bootstrap distribution is
*discrete*, as an AUROC on few cases is (its support is spaced ``1/(n_pos*n_neg)``
apart), the endpoint can only land on a support point and the granularity dominates,
so the endpoint error is ``max(0.0598 * sd, spacing/2)``. The tolerance is three of
those, one endpoint at a time. :func:`endpoint_mc_error` computes it and
``test_the_tolerance_model_matches_the_measured_spread`` checks the model against the
measured spread over twelve seeds instead of taking it on trust.

That endpoint tolerance **holds on the F3 cohort**, across thirteen seeds, against the
DeLong Wald interval as the engine renders it. It **does not hold in general, at any
n**: a percentile interval is asymmetric and bounded and a Wald interval is symmetric,
so the two differ systematically once the AUROC is away from 0.5 - measured at three
and a half Monte-Carlo standard errors at sixty cases per class and an AUROC of 0.85.
``test_the_endpoint_tolerance_is_not_claimed_beyond_f3`` asserts that shortfall, so the
F3 result can never be quietly generalised. What *does* hold everywhere the AUROC is
non-degenerate is the agreement of the two **variance estimates**: the bootstrap
standard deviation reproduces the DeLong standard error to within
``3/sqrt(2B) + 1/n_min``, checked over a 7 x 4 grid of cohort sizes and separations.
That is the substantive claim, and it is the one that would catch a resampler drawing
the wrong unit.

**F9 - clustered variance inflation.** Two halves. The D1 section 3.2 register half:
the cluster bootstrap on F3 rows duplicated three times reproduces the F3 stratified
bootstrap on the underlying cases *exactly* (the register asks for 0.01). The
inflation half: with k rows per case and complete within-case correlation the design
effect is k, so the clustered interval should be about ``sqrt(k)`` times as wide as
the i.i.d. one; the test asserts that direction and that magnitude, at two values of
k and three cohort seeds each.
"""

from __future__ import annotations

import ast
import json
import math
import pathlib
import re
import subprocess
import sys
from statistics import NormalDist

import numpy as np
import pytest

from proofpack.resources import load_json_schema
from proofpack.stats.bootstrap import (
    ANALYTIC_STATUS,
    DEFAULT_B,
    DEFAULT_SEED,
    BootstrapPolicy,
    CellCI,
    ClusterPlan,
    auroc_ci,
    bootstrap_percentile,
    cell_entropy,
    clustered_by_case,
    clustered_flat,
    percentile_bounds,
    plan_clustering,
    policy_from_declarations,
    proportion_ci,
    rng_for_cell,
    stratified_by_outcome,
)
from proofpack.stats.discrimination import auroc_mann_whitney, delong_variance, wald_ci
from proofpack.stats.number import FLAGS, METHODS, NOT_ESTIMABLE_REASONS, Number
from proofpack.stats.proportions import proportion, z_for

pytestmark = pytest.mark.day4

REPO = pathlib.Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------- F3 fixture

F3_Y = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0], dtype=bool)
F3_S1 = np.array([0.9, 0.8, 0.7, 0.6, 0.35, 0.75, 0.5, 0.4, 0.3, 0.2])
#: R2 section 9 / D1 section 3.2: the pinned stratified bootstrap interval.
F3_BOOTSTRAP_CI = (0.44, 1.00)
#: Build day 3's hand-derived DeLong standard error for the same cohort.
F3_DELONG_SE = 0.15491933384829668
F3_AUC = 0.80


def auroc_statistic(scores: np.ndarray, positives: np.ndarray):
    def statistic(idx: np.ndarray) -> float:
        got = positives[idx]
        if not got.any() or got.all():
            return float("nan")
        return auroc_mann_whitney(scores[idx], got)

    return statistic


def draw_auroc(scores, positives, seed, *, cluster_ids=None, b=DEFAULT_B, level=0.95):
    positives = np.asarray(positives, dtype=bool)
    resampler = (
        stratified_by_outcome(positives)
        if cluster_ids is None
        else clustered_by_case(positives, cluster_ids)
    )
    return bootstrap_percentile(
        auroc_statistic(np.asarray(scores, dtype=float), positives),
        resampler,
        np.random.default_rng(seed),
        b,
        level,
    )


# ------------------------------------------------------------------- the tolerance model

#: p = alpha/2 for a 95% interval.
_TAIL = 0.025
_ND = NormalDist()


def endpoint_mc_error(sd: float, n_pos: int, n_neg: int, b: int = DEFAULT_B) -> float:
    """One percentile endpoint's error budget - Monte-Carlo noise, or the AUROC grid.

    ``sqrt(p(1-p)/B) * sd / phi(z_{1-p})`` is the Monte-Carlo standard error of the
    endpoint under a smooth bootstrap distribution. ``1/(n_pos*n_neg)`` is the spacing
    of the AUROC's support; when the distribution is that coarse the endpoint jumps
    between adjacent support points and half a step is the floor.
    """
    smooth = math.sqrt(_TAIL * (1.0 - _TAIL) / b) * sd / _ND.pdf(_ND.inv_cdf(1.0 - _TAIL))
    granularity = 0.5 / (n_pos * n_neg)
    return max(smooth, granularity)


def endpoint_tolerance(sd: float, n_pos: int, n_neg: int, b: int = DEFAULT_B) -> float:
    """Three endpoint error budgets. Stated before measuring; never widened to pass."""
    return 3.0 * endpoint_mc_error(sd, n_pos, n_neg, b)


def rendered_delong_wald(scores, positives, level=0.95):
    """The DeLong Wald interval as the engine renders it - clamped into [0, 1]."""
    positives = np.asarray(positives, dtype=bool)
    auc, var = delong_variance(np.asarray(scores, dtype=float), positives)
    lo, hi = wald_ci(auc, math.sqrt(var), level)
    return max(0.0, lo), min(1.0, hi), math.sqrt(var)


# ============================================================== 1. resampler mechanics


def test_stratified_resampling_preserves_the_class_counts():
    """Every resample keeps the prevalence - that is what "stratified" buys."""
    rng = np.random.default_rng(1)
    pos = np.array([True] * 7 + [False] * 13)
    resampler = stratified_by_outcome(pos)
    for _ in range(200):
        idx = resampler.draw(rng)
        assert idx.shape[0] == 20
        assert int(pos[idx].sum()) == 7
        assert int((~pos[idx]).sum()) == 13


def test_clustered_resampling_draws_whole_cases_never_part_of_one():
    rng = np.random.default_rng(2)
    cid = np.repeat(np.arange(6), 4)
    pos = np.repeat(np.array([True, True, True, False, False, False]), 4)
    resampler = clustered_by_case(pos, cid)
    for _ in range(200):
        idx = resampler.draw(rng)
        counts = np.bincount(cid[idx], minlength=6)
        # every case appears a whole number of times, all four of its rows together
        assert np.all(counts % 4 == 0)
        assert idx.shape[0] == 24


def test_a_clustered_resampler_over_one_row_cases_reduces_to_a_stratified_one():
    """The two schemes are the same scheme when every case carries one row."""
    pos = np.array([True] * 5 + [False] * 5)
    cid = np.arange(10)
    a = stratified_by_outcome(pos)
    b = clustered_by_case(pos, cid)
    ra, rb = np.random.default_rng(99), np.random.default_rng(99)
    for _ in range(50):
        assert np.array_equal(a.draw(ra), b.draw(rb))


def test_cases_whose_rows_carry_both_outcomes_get_their_own_stratum():
    pos = np.array([True, True, False, False, True, False])
    cid = np.array(["a", "a", "b", "b", "c", "c"])
    resampler = clustered_by_case(pos, cid)
    assert resampler.units_per_stratum == {"positive": 1, "negative": 1, "mixed": 1}


def test_case_order_does_not_depend_on_how_the_customer_names_their_cases():
    """Cases are ordered by first appearance, so relabelling ids changes nothing."""
    pos = np.array([True] * 6 + [False] * 6)
    cid_a = np.repeat(["p1", "p2", "p3", "n1", "n2", "n3"], 2)
    cid_b = np.repeat(["zz", "aa", "mm", "qq", "bb", "cc"], 2)
    ra, rb = np.random.default_rng(5), np.random.default_rng(5)
    a, b = clustered_by_case(pos, cid_a), clustered_by_case(pos, cid_b)
    for _ in range(50):
        assert np.array_equal(a.draw(ra), b.draw(rb))


def test_percentile_bounds_reject_a_nonsense_level():
    with pytest.raises(ValueError, match="level"):
        percentile_bounds(np.arange(10.0), level=1.5)


# =========================================================== 2. seed policy, determinism


def test_the_same_seed_reproduces_the_interval_bit_for_bit():
    a = draw_auroc(F3_S1, F3_Y, 20240101)
    b = draw_auroc(F3_S1, F3_Y, 20240101)
    assert np.array_equal(a.values, b.values)
    assert (a.ci_lo, a.ci_hi) == (b.ci_lo, b.ci_hi)


def test_the_same_seed_reproduces_the_interval_across_process_invocations(tmp_path):
    """A different PYTHONHASHSEED must not move a single digit."""
    script = tmp_path / "determinism_probe.py"
    src = (
        "import json, numpy as np\n"
        "from proofpack.stats.bootstrap import auroc_ci, plan_clustering, BootstrapPolicy\n"
        "rng = np.random.default_rng(4242)\n"
        "y = np.array([True]*40 + [False]*60)\n"
        "s = rng.normal(size=100) + y*1.1\n"
        "cid = np.repeat(np.arange(50), 2)\n"
        "plan = plan_clustering('case_id', cid)\n"
        "pol = BootstrapPolicy(n_resamples=400, seed=777)\n"
        "cells = {k: auroc_ci(s, y, cell_key=k, policy=pol, plan=plan, "
        "cluster_ids=cid).as_dict() for k in ('overall.auroc', 'sex.F.auroc')}\n"
        "print(json.dumps(cells, sort_keys=True))\n"
    )
    script.write_text(src, encoding="utf-8")
    outs = []
    for salt in ("0", "12345"):
        env = {**_clean_env(), "PYTHONHASHSEED": salt}
        outs.append(
            subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            ).stdout
        )
    assert outs[0] == outs[1]
    payload = json.loads(outs[0])
    # and the two cells really did get independent streams
    assert payload["overall.auroc"]["number"] != payload["sex.F.auroc"]["number"]


def _clean_env() -> dict[str, str]:
    import os

    env = dict(os.environ)
    env.pop("PYTHONHASHSEED", None)
    return env


def test_a_different_seed_gives_a_different_but_stable_interval():
    a = draw_auroc(F3_S1, F3_Y, 20240101)
    b = draw_auroc(F3_S1, F3_Y, 7)
    assert not np.array_equal(a.values, b.values)
    again = draw_auroc(F3_S1, F3_Y, 7)
    assert np.array_equal(b.values, again.values)
    # "different but stable": every seed lands inside the same error budget
    eps = endpoint_mc_error(F3_DELONG_SE, 5, 5)
    los = [draw_auroc(F3_S1, F3_Y, s).ci_lo for s in range(1000, 1012)]
    assert max(los) - min(los) <= 4.0 * eps


def test_each_cell_gets_its_own_stream_so_cell_order_cannot_move_an_interval():
    """Adding a subgroup must not shift an unrelated subgroup's interval."""
    rng = np.random.default_rng(11)
    y = np.array([True] * 20 + [False] * 20)
    s = rng.normal(size=40) + y
    cid = np.repeat(np.arange(20), 2)
    plan = plan_clustering("case_id", cid)
    pol = BootstrapPolicy(n_resamples=300, seed=5)
    first = auroc_ci(s, y, cell_key="overall.auroc", policy=pol, plan=plan, cluster_ids=cid)
    # compute two other cells in between; the first cell must be unchanged
    auroc_ci(s, y, cell_key="site.S1.auroc", policy=pol, plan=plan, cluster_ids=cid)
    auroc_ci(s, y, cell_key="sex.M.auroc", policy=pol, plan=plan, cluster_ids=cid)
    again = auroc_ci(s, y, cell_key="overall.auroc", policy=pol, plan=plan, cluster_ids=cid)
    assert first.number.as_dict() == again.number.as_dict()


def test_cell_entropy_is_a_stable_pure_function_of_the_key_text():
    """Golden values: a change to the derivation moves every interval, so it must show."""
    assert cell_entropy("overall.auroc") == cell_entropy("overall.auroc")
    assert cell_entropy("overall.auroc") != cell_entropy("overall.sensitivity")
    frozen = {
        "overall.auroc": 16129942596152027382,
        "subgroups.sex.F.op1.sensitivity": 16622151060278641896,
    }
    assert {k: cell_entropy(k) for k in frozen} == frozen
    assert rng_for_cell(1, "x").integers(0, 100, 3).tolist() == [87, 10, 50]


def _dotted(node: ast.AST) -> str | None:
    """``np.random.seed`` for an attribute chain, or ``None`` if it is not one."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


#: The only members of the ``numpy.random`` namespace this package may name.
GLOBAL_RNG_ALLOWED = {"np.random.default_rng", "numpy.random.default_rng", "np.random.Generator"}


def global_rng_offenders(tree: ast.AST) -> list[str]:
    """Every reference in ``tree`` to a global or legacy random API.

    Two forms, because walking attribute chains alone missed the second:
    ``np.random.seed(0)`` (an attribute chain) and ``from numpy.random import seed``
    (an import binding the same function to a bare name, invisible to the chain walk).
    """
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            name = _dotted(node)
            if name is None:
                continue
            root = name.rsplit(".", 1)[0]
            if root in {"np.random", "numpy.random", "random"} and name not in GLOBAL_RNG_ALLOWED:
                found.append(name)
        elif isinstance(node, ast.ImportFrom) and (node.module or "") in {"random", "numpy.random"}:
            for alias in node.names:
                name = f"{node.module}.{alias.name}"
                if name not in GLOBAL_RNG_ALLOWED:
                    found.append(name)
    return found


def test_nothing_touches_a_global_random_number_generator():
    """Parsed, not grepped: prose about the legacy API must not fail its own rule."""
    offenders: list[tuple[str, str]] = []
    for path in (REPO / "src" / "proofpack").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders += [(str(path.relative_to(REPO)), name) for name in global_rng_offenders(tree)]
    assert offenders == [], offenders


def test_the_policy_records_whether_the_seed_was_declared_or_defaulted():
    class Decl:
        bootstrap: dict = {}

    default = policy_from_declarations(Decl())
    assert default.as_dict() == {
        "B": DEFAULT_B,
        "seed": DEFAULT_SEED,
        "interval": "percentile",
        "seed_source": "engine_default",
        "b_source": "engine_default",
        # T7 must state the methods actually used, and a reviewer cannot check a
        # refusal or a precision tier without the constants that produced it.
        "thresholds": {
            "min_units_per_class": 2,
            "min_usable_fraction": 0.90,
            "low_precision_units": 10,
            "very_low_precision_units": 30,
            "small_class": 10,
        },
    }

    class Declared:
        bootstrap = {"B": 5000, "seed": 99}

    got = policy_from_declarations(Declared())
    assert got.as_dict()["seed_source"] == "declared"
    assert got.as_dict()["b_source"] == "declared"
    assert got.n_resamples == 5000 and got.seed == 99


def test_b_defaults_to_two_thousand():
    assert DEFAULT_B == 2000
    assert BootstrapPolicy().n_resamples == 2000


# ============================================================================ 3. F3


def test_f3_stratified_bootstrap_reproduces_the_pinned_fixture_interval():
    """R2 section 9: B=2000, default_rng(20240101), positives and negatives separately."""
    draw = draw_auroc(F3_S1, F3_Y, 20240101)
    assert (round(draw.ci_lo, 10), round(draw.ci_hi, 10)) == F3_BOOTSTRAP_CI
    assert draw.n_usable == DEFAULT_B


def test_the_f3_pin_does_not_depend_on_the_quantile_convention():
    """The pinned endpoints sit on support points, so linear vs lower cannot differ."""
    draw = draw_auroc(F3_S1, F3_Y, 20240101)
    for method in ("linear", "lower", "higher", "nearest"):
        lo, hi = np.quantile(draw.values, [0.025, 0.975], method=method)
        assert (round(float(lo), 10), round(float(hi), 10)) == F3_BOOTSTRAP_CI


def test_the_tolerance_model_matches_the_measured_spread():
    """The error budget is a model; check it against twelve seeds before relying on it."""
    los, his, sds = [], [], []
    for seed in range(2000, 2012):
        d = draw_auroc(F3_S1, F3_Y, seed)
        los.append(d.ci_lo)
        his.append(d.ci_hi)
        sds.append(d.sd)
    eps = endpoint_mc_error(F3_DELONG_SE, 5, 5)
    assert eps == pytest.approx(0.02, abs=1e-9)  # the grid term dominates at 5 vs 5
    assert float(np.std(los)) <= eps
    assert float(np.std(his)) <= eps
    # and the resample spread tracks the analytic standard error
    assert float(np.mean(sds)) == pytest.approx(F3_DELONG_SE, rel=0.10)


def test_f3_bootstrap_reproduces_the_delong_interval_within_the_stated_tolerance():
    """Acceptance F3, against the DeLong Wald interval as the engine renders it."""
    wald_lo, wald_hi, se = rendered_delong_wald(F3_S1, F3_Y)
    assert se == pytest.approx(F3_DELONG_SE, abs=1e-12)
    assert (round(wald_lo, 4), round(wald_hi, 4)) == (0.4964, 1.0)  # clamped from 1.1036
    tol = endpoint_tolerance(F3_DELONG_SE, 5, 5)
    assert tol == pytest.approx(0.06, abs=1e-9)
    worst = 0.0
    for seed in [20240101, *range(3000, 3012)]:
        d = draw_auroc(F3_S1, F3_Y, seed)
        worst = max(worst, abs(d.ci_lo - wald_lo), abs(d.ci_hi - wald_hi))
    assert worst <= tol, f"worst endpoint gap {worst:.4f} exceeds the stated {tol:.4f}"


def test_the_f3_gap_to_the_logit_interval_is_recorded_not_hidden():
    """Honest counterpart: the logit interval is *not* reproduced within the tolerance.

    D1 section 3.1 makes the logit interval primary below 30 per class. A percentile
    bootstrap is an untransformed-scale interval and does not track a transformed-scale
    one at five cases per class; the gap is stated here so nobody discovers it later.
    """
    from proofpack.stats.discrimination import logit_ci

    lo, hi = logit_ci(F3_AUC, F3_DELONG_SE)
    d = draw_auroc(F3_S1, F3_Y, 20240101)
    tol = endpoint_tolerance(F3_DELONG_SE, 5, 5)
    assert abs(d.ci_lo - lo) == pytest.approx(0.0651, abs=5e-4)
    assert abs(d.ci_hi - hi) == pytest.approx(0.0361, abs=5e-4)
    assert abs(d.ci_lo - lo) > tol  # the shortfall, asserted rather than described


def se_band(n_min: int, b: int = DEFAULT_B) -> float:
    """Relative tolerance on ``sd_bootstrap / se_DeLong - 1``, derived, not tuned.

    Two terms, both a priori. ``3/sqrt(2B)`` is three relative Monte-Carlo standard
    errors of a sample standard deviation over B draws. ``1/n_min`` is the leading
    order of the small-sample bias of a bootstrap variance estimate for a two-sample
    U-statistic, which the AUROC is. The expansion assumes the U-statistic is
    non-degenerate, so the band is claimed only away from the boundary - see
    :data:`NON_DEGENERATE_AUC`.
    """
    return 3.0 / math.sqrt(2.0 * b) + 1.0 / n_min


#: Above this the AUROC is effectively degenerate: the first-order projection the
#: O(1/n) expansion rests on stops leading, and DeLong's own normal approximation is
#: already unreliable (D1 switches to the logit interval above 0.9 for the same reason,
#: and the engine refuses an interval outright at exactly 0 or 1).
NON_DEGENERATE_AUC = 0.98


@pytest.mark.parametrize("n_per_class", [5, 10, 20, 30, 60, 100, 200])
@pytest.mark.parametrize("separation", [0.5, 1.2, 2.0, 3.0])
def test_the_bootstrap_standard_error_reproduces_delongs_across_a_grid(n_per_class, separation):
    """The substantive claim: same variance estimate, to within a derived tolerance.

    This is what "the bootstrap reproduces DeLong" can honestly mean. It is a real
    test, not a weak one: resampling the wrong unit - rows instead of cases - moves
    the standard error by a factor of sqrt(rows per case), far outside this band.
    """
    band = se_band(n_per_class)
    asserted = 0
    for cohort_seed in (101, 102, 103):
        rng = np.random.default_rng(cohort_seed)
        y = np.array([True] * n_per_class + [False] * n_per_class)
        s = rng.normal(size=2 * n_per_class) + y * separation
        _, _, se = rendered_delong_wald(s, y)
        auc = auroc_mann_whitney(s, y)
        if se == 0.0 or auc > NON_DEGENERATE_AUC:
            continue
        d = draw_auroc(s, y, 20240101)
        assert abs(d.sd / se - 1.0) <= band, (cohort_seed, auc, se, d.sd)
        asserted += 1
    # Nine of the 84 (n, separation, cohort seed) cells are excluded as degenerate - the
    # whole separation = 3.0 column, where the AUROC sits above 0.98. Without this line
    # a parametrisation whose every cell was excluded would pass green and vacuous.
    assert asserted, ("every cell excluded as degenerate", n_per_class, separation)


def test_f3_bootstrap_standard_error_reproduces_the_delong_standard_error():
    """The same claim on the F3 cohort itself, over thirteen seeds."""
    band = se_band(5)
    for seed in [20240101, *range(3000, 3012)]:
        d = draw_auroc(F3_S1, F3_Y, seed)
        assert abs(d.sd / F3_DELONG_SE - 1.0) <= band


def test_the_endpoint_tolerance_is_not_claimed_beyond_f3():
    """A shortfall test: percentile and Wald are different intervals, and stay so.

    The percentile interval is asymmetric and bounded; DeLong's Wald interval is
    symmetric. At 60 cases per class and an AUROC of about 0.85 the endpoints differ
    by roughly three and a half Monte-Carlo standard errors - a real difference in
    construction, not noise. Asserted here so the claim in the F3 test above is never
    quietly generalised.
    """
    rng = np.random.default_rng(14)
    y = np.array([True] * 60 + [False] * 60)
    s = rng.normal(size=120) + y * 1.2
    assert 0.84 < auroc_mann_whitney(s, y) < 0.87
    wald_lo, wald_hi, se = rendered_delong_wald(s, y)
    d = draw_auroc(s, y, 20240101)
    gap = max(abs(d.ci_lo - wald_lo), abs(d.ci_hi - wald_hi))
    assert gap > endpoint_tolerance(se, 60, 60)
    assert abs(d.sd / se - 1.0) <= se_band(60)  # but the variance estimate still agrees


def test_percentile_machinery_matches_scipys_on_an_iid_statistic():
    """D1 section 3.1 CI oracle: cross-check the percentile interval against scipy."""
    scipy_stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(3)
    x = rng.normal(size=200)
    ours = bootstrap_percentile(
        lambda idx: float(x[idx].mean()),
        clustered_flat(np.arange(200)),  # 200 one-row units: an ordinary row bootstrap
        np.random.default_rng(1),
        4000,
    )
    theirs = scipy_stats.bootstrap(
        (x,),
        np.mean,
        n_resamples=4000,
        method="percentile",
        random_state=np.random.default_rng(2),
    ).confidence_interval
    assert ours.ci_lo == pytest.approx(theirs.low, abs=0.01)
    assert ours.ci_hi == pytest.approx(theirs.high, abs=0.01)


# ============================================================================ 4. F9


def test_f9a_cluster_bootstrap_on_duplicated_f3_equals_the_stratified_bootstrap():
    """D1 section 3.2 F9: same cases, same seed - the register asks for 0.01, we get 0."""
    y3 = np.repeat(F3_Y, 3)
    s3 = np.repeat(F3_S1, 3)
    cid = np.repeat(np.arange(10), 3)
    iid = draw_auroc(F3_S1, F3_Y, 20240101)
    clustered = draw_auroc(s3, y3, 20240101, cluster_ids=cid)
    assert np.array_equal(iid.values, clustered.values)
    assert (clustered.ci_lo, clustered.ci_hi) == (iid.ci_lo, iid.ci_hi)
    assert abs(clustered.ci_lo - F3_BOOTSTRAP_CI[0]) < 0.01
    assert abs(clustered.ci_hi - F3_BOOTSTRAP_CI[1]) < 0.01


def _clustered_cohort(seed: int, k: int, n_cases: int = 60):
    """``n_cases`` cases, each replicated ``k`` times - complete intra-cluster correlation."""
    rng = np.random.default_rng(seed)
    y_case = np.array([True] * (n_cases // 2) + [False] * (n_cases // 2))
    s_case = rng.normal(size=n_cases) + y_case * 1.0
    return (
        np.repeat(y_case, k),
        np.repeat(s_case, k),
        np.repeat(np.arange(n_cases), k),
        y_case,
        s_case,
    )


@pytest.mark.parametrize("k", [3, 5])
@pytest.mark.parametrize("seed", [11, 12, 13])
def test_f9b_the_clustered_interval_is_wider_by_about_the_design_effect(k, seed):
    """With k rows per case and complete within-case correlation, design effect = k.

    The i.i.d. bootstrap believes it has ``k`` times as much information as it has, so
    its interval is about ``sqrt(k)`` too narrow. The assertion is on the direction and
    on the magnitude - a band of +/- 20% around ``sqrt(k)``, which is far outside the
    ~3% relative Monte-Carlo noise on an interval width at B = 2000.
    """
    y, s, cid, y_case, s_case = _clustered_cohort(seed, k)
    iid = draw_auroc(s, y, 20240101)
    clustered = draw_auroc(s, y, 20240101, cluster_ids=cid)
    ratio = (clustered.ci_hi - clustered.ci_lo) / (iid.ci_hi - iid.ci_lo)
    assert ratio > 1.0
    assert 0.8 * math.sqrt(k) <= ratio <= 1.2 * math.sqrt(k), ratio
    # and the clustered interval is exactly the case-level one: replication adds nothing
    case_level = draw_auroc(s_case, y_case, 20240101)
    assert (clustered.ci_lo, clustered.ci_hi) == (case_level.ci_lo, case_level.ci_hi)


def _correlated_cohort(seed: int, k: int, rho: float, n_cases: int = 60):
    """Cases with a real intra-cluster correlation ``rho`` in the score, not duplicates.

    Each case carries a case-level effect with variance ``rho`` and per-row noise with
    variance ``1 - rho``, so the within-case correlation of the score is ``rho`` by
    construction and the design effect is ``1 + (k - 1) * rho``.
    """
    rng = np.random.default_rng(seed)
    y_case = np.array([True] * (n_cases // 2) + [False] * (n_cases // 2))
    case_effect = rng.normal(size=n_cases) * math.sqrt(rho)
    rows = n_cases * k
    score = (
        np.repeat(case_effect, k)
        + rng.normal(size=rows) * math.sqrt(1.0 - rho)
        + np.repeat(y_case, k) * 1.0
    )
    return np.repeat(y_case, k), score, np.repeat(np.arange(n_cases), k)


@pytest.mark.parametrize("rho", [0.0, 0.3, 0.6, 0.9])
def test_f9b_the_width_ratio_tracks_the_design_effect_at_a_real_correlation(rho):
    """Not duplicated rows: a genuine intra-cluster correlation, and its design effect.

    ``rho = 0`` is the negative control that matters most - with independent rows the
    cluster bootstrap must *not* inflate anything, or the module would simply be
    widening every clustered interval regardless of the data.
    """
    k = 4
    predicted = math.sqrt(1.0 + (k - 1) * rho)
    for seed in (11, 12, 13):
        y, s, cid = _correlated_cohort(seed, k, rho)
        iid = draw_auroc(s, y, 20240101, b=1000)
        clustered = draw_auroc(s, y, 20240101, cluster_ids=cid, b=1000)
        ratio = (clustered.ci_hi - clustered.ci_lo) / (iid.ci_hi - iid.ci_lo)
        assert 0.8 * predicted <= ratio <= 1.2 * predicted, (seed, rho, ratio, predicted)
        if rho >= 0.3:
            assert ratio > 1.15  # materially wider, not merely different


def test_f9_naive_delong_shrinks_under_clustering_and_is_therefore_refused():
    """The premise of the refusal, measured: duplication divides the SE by about sqrt(k)."""
    y_case = np.array([True] * 30 + [False] * 30)
    rng = np.random.default_rng(21)
    s_case = rng.normal(size=60) + y_case
    _, honest_var = delong_variance(s_case, y_case)
    for k in (2, 4, 9):
        y, s = np.repeat(y_case, k), np.repeat(s_case, k)
        _, naive_var = delong_variance(s, y)
        assert math.sqrt(naive_var) == pytest.approx(math.sqrt(honest_var) / math.sqrt(k), rel=0.06)
    # and the engine refuses to report it
    cid = np.repeat(np.arange(60), 4)
    cell = auroc_ci(
        np.repeat(s_case, 4),
        np.repeat(y_case, 4),
        cell_key="overall.auroc",
        plan=plan_clustering("case_id", cid),
        cluster_ids=cid,
        policy=BootstrapPolicy(n_resamples=400),
    )
    assert cell.analytic.not_estimable_reason == "clustered_data_analytic_ci_invalid"
    assert cell.number.method == "cluster_bootstrap_percentile"
    assert cell.number.half_width > math.sqrt(honest_var)  # honest width, not the naive one


# ============================================================ 5. X2 - the refusal surface


def _duplicated_cohort(k=3):
    y = np.repeat(F3_Y, k)
    s = np.repeat(F3_S1, k)
    cid = np.repeat([f"case{i}" for i in range(10)], k)
    return s, y, cid


def test_declared_clustering_refuses_delong_with_a_typed_reason_in_the_json():
    s, y, cid = _duplicated_cohort()
    plan = plan_clustering("case_id", cid)
    assert (plan.clustered, plan.route) == (True, "declared")
    cell = auroc_ci(s, y, cell_key="overall.auroc", plan=plan, cluster_ids=cid)
    payload = cell.as_dict()
    assert payload["number"]["method"] == "cluster_bootstrap_percentile"
    assert "delong_refused_clustered" in payload["number"]["flags"]
    assert payload["analytic"]["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
    assert payload["analytic"]["ci_lo"] is None and payload["analytic"]["ci_hi"] is None
    assert payload["analytic_status"] == "refused_clustered"
    assert payload["number"]["n_cases"] == 10
    assert payload["bootstrap"]["B"] == 2000
    # the whole thing survives a JSON round trip - it is data, not a log line
    assert json.loads(json.dumps(payload)) == payload


def test_detected_clustering_takes_the_same_path_and_raises_a_warning():
    """The declaration says none; repeated case_id values say otherwise. Data wins."""
    s, y, cid = _duplicated_cohort()
    plan = plan_clustering("none", cid)
    assert (plan.clustered, plan.route, plan.n_units, plan.n_rows) == (True, "detected", 10, 30)
    finding = plan.finding()
    assert finding is not None and finding.code == "W13"
    assert finding.detail == {"n_rows": 30, "n_cases": 10}
    cell = auroc_ci(s, y, cell_key="overall.auroc", plan=plan, cluster_ids=cid)
    assert cell.number.method == "cluster_bootstrap_percentile"
    assert cell.analytic.not_estimable_reason == "clustered_data_analytic_ci_invalid"
    assert cell.route == "detected"
    # identical numbers to the declared route: only the provenance differs
    declared = auroc_ci(
        s, y, cell_key="overall.auroc", plan=plan_clustering("case_id", cid), cluster_ids=cid
    )
    assert cell.number.as_dict() == declared.number.as_dict()


def test_an_unclustered_run_raises_no_warning_and_keeps_delong():
    rng = np.random.default_rng(31)
    y = np.array([True] * 30 + [False] * 30)
    s = rng.normal(size=60) + y
    cid = np.arange(60)
    plan = plan_clustering("none", cid)
    assert (plan.clustered, plan.route) == (False, "none")
    assert plan.finding() is None
    cell = auroc_ci(s, y, cell_key="overall.auroc", plan=plan, cluster_ids=cid)
    assert cell.number.method in {"delong_logit", "delong_wald"}
    assert cell.analytic_status == "used"
    assert cell.policy is None  # no bootstrap ran at all


def test_a_clustered_proportion_refuses_wilson_with_a_typed_reason():
    rng = np.random.default_rng(41)
    cid = np.repeat(np.arange(40), 4)
    per_case = rng.random(40) < 0.75
    ind = np.repeat(per_case, 4)
    plan = plan_clustering("case_id", cid)
    cell = proportion_ci(ind, cell_key="op1.sensitivity", plan=plan, cluster_ids=cid)
    assert cell.number.method == "cluster_bootstrap_percentile"
    assert "wilson_refused_clustered" in cell.number.flags
    assert cell.analytic.not_estimable_reason == "clustered_data_analytic_ci_invalid"
    assert cell.number.n == 160 and cell.number.k == int(ind.sum())
    # and it is materially wider than the (invalid) Wilson interval on 160 rows
    wilson = proportion(int(ind.sum()), 160)
    assert cell.number.half_width > 1.5 * wilson.half_width


def test_an_iid_proportion_is_still_exactly_wilson():
    ind = np.array([True] * 81 + [False] * 182)
    cell = proportion_ci(ind, cell_key="op1.sensitivity")
    assert cell.number.method == "wilson"
    assert cell.analytic_status == "used"
    assert cell.policy is None
    assert (cell.number.ci_lo, cell.number.ci_hi) == (
        proportion(81, 263).ci_lo,
        proportion(81, 263).ci_hi,
    )
    assert round(cell.number.ci_lo, 4) == 0.2553  # R2 section 9 F1
    assert round(cell.number.ci_hi, 4) == 0.3662


def test_a_declared_case_id_unit_with_no_case_id_column_is_a_contradiction():
    with pytest.raises(ValueError, match="no case_id column"):
        plan_clustering("case_id", None)


def test_a_clustered_cell_never_swallows_the_refusal_into_an_exception():
    """Every clustered cell returns a Number - refusals are values, not raised."""
    rng = np.random.default_rng(51)
    for n_cases, k in ((2, 3), (3, 2), (12, 5), (40, 2)):
        y_case = np.array([True] * (n_cases // 2) + [False] * (n_cases - n_cases // 2))
        s_case = rng.normal(size=n_cases)
        y, s = np.repeat(y_case, k), np.repeat(s_case, k)
        cid = np.repeat(np.arange(n_cases), k)
        cell = auroc_ci(
            s,
            y,
            cell_key="c",
            plan=plan_clustering("case_id", cid),
            cluster_ids=cid,
            policy=BootstrapPolicy(n_resamples=200),
        )
        assert cell.number.has_ci or cell.number.not_estimable_reason in NOT_ESTIMABLE_REASONS
        assert cell.analytic.not_estimable_reason == "clustered_data_analytic_ci_invalid"
        assert cell.analytic_status in ANALYTIC_STATUS


def test_a_clustered_plan_without_cluster_ids_is_a_programming_error_not_a_silent_switch():
    s, y, cid = _duplicated_cohort()
    plan = plan_clustering("case_id", cid)
    with pytest.raises(ValueError, match="needs cluster_ids"):
        auroc_ci(s, y, cell_key="c", plan=plan)
    with pytest.raises(ValueError, match="needs cluster_ids"):
        proportion_ci(np.ones(30, dtype=bool), cell_key="c", plan=plan)


# ================================================================= 6. per-cell fallbacks


def test_a_small_class_switches_to_the_stratified_bootstrap_and_says_so():
    """R2 section 1.3: below ten in a class, DeLong gives way - visibly."""
    cell = auroc_ci(F3_S1, F3_Y, cell_key="overall.auroc")
    assert cell.number.method == "bootstrap_percentile"
    assert "analytic_ci_replaced_small_class" in cell.number.flags
    assert cell.analytic_status == "replaced_small_class"
    assert cell.analytic.method == "delong_logit"  # carried alongside, not discarded
    assert cell.policy is not None and cell.policy.n_resamples == DEFAULT_B


def test_ten_or_more_in_each_class_keeps_delong_and_runs_no_bootstrap():
    rng = np.random.default_rng(61)
    y = np.array([True] * 10 + [False] * 10)
    s = rng.normal(size=20) + y
    cell = auroc_ci(s, y, cell_key="overall.auroc")
    assert cell.number.method in {"delong_logit", "delong_wald"}
    assert cell.analytic_status == "used"
    assert cell.n_usable == 0 and cell.resample_sd is None


def test_a_single_class_cell_is_not_estimable():
    cell = auroc_ci(F3_S1, np.ones(10, dtype=bool), cell_key="c")
    assert cell.number.not_estimable_reason == "single_class"
    assert cell.analytic_status == "unavailable"


def test_an_empty_cell_is_not_estimable_rather_than_a_zero():
    cell = proportion_ci(np.zeros(0, dtype=bool), cell_key="c")
    assert cell.number.not_estimable_reason == "zero_denominator"
    assert cell.number.est is None


def test_fewer_than_two_cases_in_a_stratum_is_not_estimable():
    y = np.array([True, True, False, False, False, False])
    s = np.array([0.9, 0.8, 0.4, 0.3, 0.2, 0.1])
    cid = np.array(["a", "a", "b", "b", "c", "c"])  # one positive case, two negative
    cell = auroc_ci(
        s,
        y,
        cell_key="c",
        plan=plan_clustering("case_id", cid),
        cluster_ids=cid,
        policy=BootstrapPolicy(n_resamples=50),
    )
    assert cell.number.not_estimable_reason == "insufficient_clusters"
    assert cell.number.est == pytest.approx(1.0)  # the point estimate survives
    assert cell.analytic.not_estimable_reason == "clustered_data_analytic_ci_invalid"


def test_perfect_separation_under_clustering_refuses_a_zero_width_interval():
    """A printed (1.00, 1.00) would claim a certainty the data do not support."""
    y_case = np.array([True] * 6 + [False] * 6)
    s_case = np.array([0.9] * 6 + [0.1] * 6)
    cid = np.repeat(np.arange(12), 2)
    cell = auroc_ci(
        np.repeat(s_case, 2),
        np.repeat(y_case, 2),
        cell_key="c",
        plan=plan_clustering("case_id", cid),
        cluster_ids=cid,
        policy=BootstrapPolicy(n_resamples=200),
    )
    assert cell.number.not_estimable_reason == "boundary_estimate"
    assert cell.number.est == 1.0
    assert not cell.number.has_ci


def test_degenerate_resamples_are_refused_rather_than_quietly_dropped():
    """If most draws give no statistic, the survivors are not an interval."""
    calls = {"n": 0}

    def flaky(_idx: np.ndarray) -> float:
        calls["n"] += 1
        return float("nan") if calls["n"] % 4 else 0.5

    draw = bootstrap_percentile(
        flaky,
        stratified_by_outcome(np.array([True] * 5 + [False] * 5)),
        np.random.default_rng(1),
        100,
    )
    assert draw.reason == "degenerate_resamples"
    assert draw.ci_lo is None and draw.ci_hi is None
    assert draw.n_usable == 25


def test_every_number_this_module_can_produce_has_a_ci_or_a_typed_reason():
    rng = np.random.default_rng(71)
    seen_reasons, seen_methods = set(), set()
    for n_cases in (1, 2, 3, 6, 14):
        for k in (1, 2, 3):
            for sep in (0.0, 3.0, 30.0):
                n_pos = max(1, n_cases // 2)
                y_case = np.array([True] * n_pos + [False] * (n_cases - n_pos))
                s_case = rng.normal(size=n_cases) + y_case * sep
                y, s = np.repeat(y_case, k), np.repeat(s_case, k)
                cid = np.repeat(np.arange(n_cases), k)
                for unit in ("none", "case_id"):
                    plan = plan_clustering(unit, cid)
                    cells: list[CellCI] = [
                        auroc_ci(
                            s,
                            y,
                            cell_key="a",
                            plan=plan,
                            cluster_ids=cid,
                            policy=BootstrapPolicy(n_resamples=60),
                        ),
                        proportion_ci(
                            s > 0,
                            cell_key="p",
                            plan=plan,
                            cluster_ids=cid,
                            policy=BootstrapPolicy(n_resamples=60),
                        ),
                    ]
                    for cell in cells:
                        for num in (cell.number, cell.analytic):
                            if num is None:
                                continue
                            assert isinstance(num, Number)
                            assert num.has_ci or num.not_estimable_reason is not None
                            if num.not_estimable_reason:
                                seen_reasons.add(num.not_estimable_reason)
                            seen_methods.add(num.method)
    assert seen_reasons <= NOT_ESTIMABLE_REASONS
    assert seen_methods <= METHODS
    assert "clustered_data_analytic_ci_invalid" in seen_reasons
    assert "cluster_bootstrap_percentile" in seen_methods


# ====================================================== 7. enums, schema, BCa deferral


def test_flag_enum_agrees_between_code_and_schema():
    schema = load_json_schema("output_schema_v1.json")
    assert set(schema["$defs"]["flag"]["enum"]) == set(FLAGS)
    assert set(schema["$defs"]["method"]["enum"]) == set(METHODS)
    assert set(schema["$defs"]["notEstimableReason"]["enum"]) == set(NOT_ESTIMABLE_REASONS)


def test_every_number_this_module_emits_validates_against_the_output_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_json_schema("output_schema_v1.json")
    number_schema = {**schema["$defs"]["Number"], "$defs": schema["$defs"]}
    s, y, cid = _duplicated_cohort()
    cells = [
        auroc_ci(s, y, cell_key="a", plan=plan_clustering("case_id", cid), cluster_ids=cid),
        auroc_ci(F3_S1, F3_Y, cell_key="b"),
        proportion_ci(
            np.repeat([True] * 6 + [False] * 4, 3),
            cell_key="c",
            plan=plan_clustering("case_id", cid),
            cluster_ids=cid,
        ),
        proportion_ci(np.array([True] * 81 + [False] * 182), cell_key="d"),
    ]
    for cell in cells:
        for num in (cell.number, cell.analytic):
            if num is not None:
                jsonschema.validate(num.as_dict(), number_schema)


def test_bca_is_deferred_to_v1_1_and_cannot_be_emitted():
    """Half a BCa is worse than none. The enum value stays; no code path reaches it."""
    with pytest.raises(ValueError, match="deferred to v1.1"):
        BootstrapPolicy(interval="bca")

    class Decl:
        bootstrap = {"interval": "bca"}

    with pytest.raises(ValueError, match="deferred to v1.1"):
        policy_from_declarations(Decl())

    # the criteria schema refuses it at declaration time, before anything runs
    criteria = load_json_schema("criteria_schema.json")
    assert criteria["properties"]["bootstrap"]["properties"]["interval"]["enum"] == ["percentile"]

    # and no module assigns the bootstrap_bca method
    pattern = re.compile(r"""method\s*=\s*['"]bootstrap_bca['"]""")
    for path in (REPO / "src" / "proofpack").rglob("*.py"):
        assert not pattern.search(path.read_text(encoding="utf-8")), path
    assert "bootstrap_bca" in METHODS  # reserved for v1.1


def test_the_bootstrap_module_needs_no_scipy():
    text = (REPO / "src" / "proofpack" / "stats" / "bootstrap.py").read_text(encoding="utf-8")
    assert "scipy" not in text
    out = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import proofpack.stats.bootstrap; print('scipy' in sys.modules)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.strip() == "False"


def test_an_unknown_analytic_status_is_rejected():
    n = proportion(5, 10)
    with pytest.raises(ValueError, match="analytic_status"):
        CellCI(n, n, "looks_fine", "c", "none")


def test_the_plan_serialises_the_provenance_of_the_clustering_decision():
    _, _, cid = _duplicated_cohort()
    assert plan_clustering("case_id", cid).as_dict() == {
        "clustered": True,
        "route": "declared",
        "unit": "case_id",
        "n_rows": 30,
        "n_units": 10,
    }
    assert ClusterPlan(False, "none", 10, 10).rows_per_unit == 1.0
    assert plan_clustering("case_id", cid).rows_per_unit == 3.0


def test_z_for_is_the_same_quantile_the_analytic_intervals_use():
    """Guards against the bootstrap and the analytic path drifting apart on the level."""
    assert z_for(0.95) == pytest.approx(1.959963984540054, abs=1e-12)


# ==================================== 8. repairs from the day-4 adversarial verification
#
# One test per blocker raised by the three verify notes
# (``handoffs/2026-09-10_E_verify_{statistics,safety,acceptance}.md``). Each one fails
# against 5bc69fb, the pre-repair commit; the verbatim failures are recorded in
# ``handoffs/2026-09-10_E_verify.md``.


def _multi_lesion_cohort(n_cases: int, k: int, seed: int, mixed: int = 0):
    """``n_cases`` patients with ``k`` lesions each; ``mixed`` of them carry both outcomes.

    The design the module docstring names as the reason the ``mixed`` stratum exists:
    one patient, several lesions, not all of them malignant.
    """
    rng = np.random.default_rng(seed)
    y_case = np.array([True] * (n_cases // 2) + [False] * (n_cases - n_cases // 2))
    y = np.repeat(y_case, k)
    cid = np.repeat(np.arange(n_cases), k)
    for j in range(mixed):
        y[j * k] = not y[j * k]  # flip one lesion of patient j: that case is now mixed
    s = rng.normal(size=n_cases * k) + y * 1.0
    return s, y, cid


def test_n_cases_is_the_cells_own_case_count_not_the_runs():
    """B1 (statistics) / B3 (acceptance): a run-level ClusterPlan must not set a cell count.

    Day 5 is instructed to build one ClusterPlan for the run and pass it to every cell,
    so every subgroup row would otherwise print the whole run's case count - here 40
    cases beside 36 analysed rows, which is arithmetically impossible.
    """
    s, y, cid = _multi_lesion_cohort(40, 3, seed=5)
    run_plan = plan_clustering("case_id", cid)
    assert (run_plan.n_rows, run_plan.n_units) == (120, 40)

    # a subgroup slice: 36 rows, 12 whole cases, six of each outcome
    cell = np.isin(cid, [*range(6), *range(20, 26)])
    assert int(cell.sum()) == 36
    got = auroc_ci(
        s[cell],
        y[cell],
        cell_key="subgroups.sex.F.auroc",
        plan=run_plan,
        cluster_ids=cid[cell],
        policy=BootstrapPolicy(n_resamples=200),
    )
    assert got.number.n_cases == 12
    assert got.analytic.n_cases == 12
    assert got.number.n_cases <= got.number.n_pos + got.number.n_neg


def test_one_mixed_outcome_case_does_not_veto_a_two_hundred_case_cohort():
    """B2 (statistics) / B3 (safety): the refusal is about the data, not the bookkeeping.

    ``clustered_by_case`` gives a case carrying both outcomes its own ``mixed`` stratum.
    Refusing on ``min`` over the strata let a single multi-lesion patient delete the
    interval of a 200-patient study, with ``insufficient_clusters`` printed beside
    ``n_cases: 200`` and a ``very_low_precision`` flag on the same Number.
    """
    s, y, cid = _multi_lesion_cohort(200, 2, seed=7, mixed=1)
    resampler = clustered_by_case(y, cid)
    assert resampler.units_per_stratum.get("mixed") == 1  # the singleton stratum is real
    cell = auroc_ci(
        s,
        y,
        cell_key="overall.auroc",
        plan=plan_clustering("case_id", cid),
        cluster_ids=cid,
        policy=BootstrapPolicy(n_resamples=400),
    )
    assert cell.number.has_ci, cell.number.not_estimable_reason
    assert cell.number.method == "cluster_bootstrap_percentile"
    assert cell.number.n_cases == 200
    assert "very_low_precision" not in cell.number.flags
    assert "not_evaluable_shown_for_transparency" not in cell.number.flags


def test_the_refusal_names_the_class_that_is_actually_short():
    """B2 (statistics) / B4 (acceptance) / N1 (safety): the typed reason must be true.

    ``insufficient_negatives`` is in the enum and was emitted by no code path, while
    ``insufficient_positives`` was printed beside ``n_pos: 25``.
    """
    rng = np.random.default_rng(23)
    y = np.array([True] * 25 + [False] * 1)
    s = rng.normal(size=26) + y
    short_negatives = auroc_ci(s, y, cell_key="c", policy=BootstrapPolicy(n_resamples=50))
    assert short_negatives.number.not_estimable_reason == "insufficient_negatives"
    assert short_negatives.number.n_pos == 25 and short_negatives.number.n_neg == 1

    short_positives = auroc_ci(s, ~y, cell_key="c", policy=BootstrapPolicy(n_resamples=50))
    assert short_positives.number.not_estimable_reason == "insufficient_positives"


def test_a_perfectly_separated_cell_promises_no_bootstrap_and_claims_no_analytic_ci():
    """B3 (statistics): two false statements reached the output JSON.

    ``ci_pending_bootstrap`` is defined as "day-4 bootstrap will fill this interval";
    day 4 has landed and this cell has been through it. ``analytic_status: used`` is
    defined as "the analytic interval is the rendered one" - there is no interval.
    """
    y = np.array([True] * 30 + [False] * 30)
    s = np.concatenate([np.linspace(0.6, 1.0, 30), np.linspace(0.0, 0.4, 30)])
    cell = auroc_ci(s, y, cell_key="subgroups.site.A.auroc")
    assert cell.number.est == 1.0 and not cell.number.has_ci
    assert cell.number.not_estimable_reason == "boundary_estimate"
    assert "ci_pending_bootstrap" not in cell.number.flags
    assert cell.analytic_status == "unavailable"
    assert "ci_pending_bootstrap" not in json.dumps(cell.as_dict())


def test_cluster_ids_without_a_plan_never_reach_delong_or_wilson():
    """B1 (safety) / B1 (acceptance): X2 defeated by forgetting one keyword argument.

    The mirror mistake - a clustered plan with no ``cluster_ids`` - already raises. The
    reverse silently produced a DeLong interval several times too narrow, with
    ``analytic_status: used`` and no flag anywhere in the output.
    """
    s, y, cid = _multi_lesion_cohort(20, 5, seed=9)
    cell = auroc_ci(s, y, cell_key="overall.auroc", cluster_ids=cid)
    assert cell.analytic_status != "used"
    assert cell.number.method == "cluster_bootstrap_percentile"
    assert "delong_refused_clustered" in cell.number.flags
    assert cell.route == "detected"

    prop = proportion_ci(s > 0, cell_key="op1.sensitivity", cluster_ids=cid)
    assert prop.analytic_status == "refused_clustered"
    assert prop.number.method == "cluster_bootstrap_percentile"
    assert "wilson_refused_clustered" in prop.number.flags

    # and a plan that positively asserts independence over clustered ids is a
    # contradiction, exactly as the mirror case is
    iid_plan = ClusterPlan(False, "none", int(y.shape[0]), int(y.shape[0]))
    with pytest.raises(ValueError, match="cluster_ids repeat"):
        auroc_ci(s, y, cell_key="c", plan=iid_plan, cluster_ids=cid)
    with pytest.raises(ValueError, match="cluster_ids repeat"):
        proportion_ci(s > 0, cell_key="c", plan=iid_plan, cluster_ids=cid)


@pytest.mark.parametrize("duplicated", [1, 2, 10])
def test_any_repeated_case_id_triggers_the_clustered_path(duplicated):
    """B2 (safety): D1 line 43 says ``n_rows > n_cases``, with no threshold.

    Every other day-4 fixture duplicates *every* case, so a partially clustered table -
    a handful of patients contributing a second lesion, which is the realistic shape -
    was never exercised, and an arbitrary threshold survived all 213 tests.
    """
    rng = np.random.default_rng(101 + duplicated)
    ids = np.concatenate([np.arange(100), np.arange(duplicated)])
    plan = plan_clustering("none", ids)
    assert (plan.clustered, plan.route) == (True, "detected")
    assert (plan.n_rows, plan.n_units) == (100 + duplicated, 100)
    finding = plan.finding()
    assert finding is not None and finding.code == "W13"

    y = np.isin(ids, np.arange(50))
    s = rng.normal(size=ids.shape[0]) + y
    cell = auroc_ci(
        s, y, cell_key="c", plan=plan, cluster_ids=ids, policy=BootstrapPolicy(n_resamples=200)
    )
    assert cell.number.method == "cluster_bootstrap_percentile"
    assert "delong_refused_clustered" in cell.number.flags


def test_a_clustered_proportion_refuses_cluster_ids_that_do_not_align():
    """B4 (safety) / B2 (acceptance): one Number built from three different row sets.

    ``clustered_by_case`` checks the length; ``clustered_flat`` did not, so a short
    ``cluster_ids`` gave an estimate over all the rows, an interval resampled from a
    prefix of them, and ``n`` equal to all of them, with no error and no flag.
    """
    rng = np.random.default_rng(13)
    cid = np.repeat(np.arange(100), 4)
    ind = rng.random(400) < 0.8
    plan = plan_clustering("case_id", cid)
    with pytest.raises(ValueError, match="align"):
        proportion_ci(ind, cell_key="c", plan=plan, cluster_ids=cid[:200])
    with pytest.raises(ValueError, match="align"):
        clustered_flat(cid[:200], n_rows=400)


# ---------------------------------------------- non-blocking observations, repaired here


def test_a_clustered_proportion_reports_its_case_count():
    """N7 (safety) / N4 (acceptance): n = 160 rows over 20 patients, with no n_cases."""
    cid = np.repeat(np.arange(20), 8)
    ind = np.repeat(np.random.default_rng(3).random(20) < 0.75, 8)
    cell = proportion_ci(
        ind,
        cell_key="op1.sensitivity",
        plan=plan_clustering("case_id", cid),
        cluster_ids=cid,
        policy=BootstrapPolicy(n_resamples=200),
    )
    assert cell.number.n == 160 and cell.number.n_cases == 20
    assert cell.analytic.n_cases == 20


@pytest.mark.parametrize(
    ("n_cases", "expected"),
    [(6, "not_evaluable_shown_for_transparency"), (20, "very_low_precision"), (60, None)],
)
def test_the_precision_tier_follows_r2_section_3_3_on_the_cells_units(n_cases, expected):
    """N1 (acceptance): ``n < 10`` is "not evaluable", ``10 <= n < 30`` is "very low".

    The module attached the *less* severe label below ten, and measured it on the
    smallest resampling stratum rather than on the cell.
    """
    s, y, cid = _multi_lesion_cohort(n_cases, 3, seed=17)
    cell = auroc_ci(
        s,
        y,
        cell_key="c",
        plan=plan_clustering("case_id", cid),
        cluster_ids=cid,
        policy=BootstrapPolicy(n_resamples=200),
    )
    tiers = {"not_evaluable_shown_for_transparency", "very_low_precision"}
    assert set(cell.number.flags) & tiers == ({expected} if expected else set())


def test_the_engine_default_seed_is_pinned_by_this_test_not_only_by_prose():
    """N3 (safety): mutating DEFAULT_SEED left all 85 day-4 tests passing.

    Every customer's intervals move if this constant moves between releases, and
    reproducing a pack against a re-run is part of what is sold.
    """
    assert DEFAULT_SEED == 20240101
    assert BootstrapPolicy().seed == DEFAULT_SEED
    pinned = bootstrap_percentile(
        auroc_statistic(F3_S1, F3_Y),
        stratified_by_outcome(F3_Y),
        np.random.default_rng(DEFAULT_SEED),
        DEFAULT_B,
    )
    assert (round(pinned.ci_lo, 2), round(pinned.ci_hi, 2)) == F3_BOOTSTRAP_CI


def test_a_negative_declared_seed_is_refused_at_declaration_time():
    """N4 (safety): ``{"seed": -1}`` validated, then crashed numpy on the first cell."""
    with pytest.raises(ValueError, match="seed"):
        BootstrapPolicy(seed=-1)
    criteria = load_json_schema("criteria_schema.json")
    assert criteria["properties"]["bootstrap"]["properties"]["seed"]["minimum"] == 0
    assert criteria["properties"]["bootstrap"]["additionalProperties"] is False


def test_the_global_rng_guard_also_rejects_the_import_form():
    """N3 (acceptance): the ast walk saw attribute chains only.

    ``from numpy.random import seed`` slipped past it; the guard's whole purpose is
    that reading the prose is not enough.
    """
    probe = ast.parse("from numpy.random import seed\n\n\ndef f():\n    seed(0)\n")
    assert global_rng_offenders(probe) == ["numpy.random.seed"]
    clean = ast.parse("import numpy as np\n\n\ndef f():\n    return np.random.default_rng(1)\n")
    assert global_rng_offenders(clean) == []


def test_a_warning_code_is_validated_the_way_a_halt_code_is():
    """N5 (acceptance): ``Finding.code`` was free text while ``HaltError.code`` was closed.

    W13 is invented in this module, W10 and W12 in ``gates``; only W06 appears in the
    spec. A warning code reaches the rendered document and the exit status, so a typo or
    a collision between two lanes has to fail at construction.
    """
    from proofpack.errors import WARN_CODES, Finding

    _, _, cid = _duplicated_cohort()
    assert plan_clustering("none", cid).finding().code in WARN_CODES
    assert {"W06", "W10", "W12", "W13"} <= set(WARN_CODES)
    with pytest.raises(ValueError, match="unknown warning code"):
        Finding("W99", "a code nobody registered")


# ============================ 9. repairs from the day-4 re-verification (repair round 2)
#
# One test per blocker raised by the two re-verify notes
# (``handoffs/2026-09-10_E_reverify_r1_{regression,fresh-attack}.md``). R1 and FA-B2 are
# the same defect found by two lenses. Each test fails against 5b92fc5, the round-1
# commit; the verbatim failures are recorded in ``handoffs/2026-09-10_E_verify.md``.


def _imbalanced_lesion_cohort(n_pos_cases: int, n_neg_cases: int, k: int, seed: int):
    """``n_pos_cases`` all-malignant patients and ``n_neg_cases`` all-benign ones.

    ``k`` rows each. ``_multi_lesion_cohort`` is balanced by construction, so every
    precision assertion written against it is blind to *which* class is scarce. This
    one is not.
    """
    rng = np.random.default_rng(seed)
    y_case = np.array([True] * n_pos_cases + [False] * n_neg_cases)
    y = np.repeat(y_case, k)
    cid = np.repeat(np.arange(y_case.shape[0]), k)
    s = rng.normal(size=y.shape[0]) + y * 1.0
    return s, y, cid


@pytest.mark.parametrize(
    ("n_pos_cases", "n_neg_cases", "expected"),
    [
        (40, 3, "very_low_precision"),
        (40, 5, "very_low_precision"),
        (40, 9, "very_low_precision"),
        (60, 6, "very_low_precision"),
        (100, 8, "very_low_precision"),
        (3, 40, "very_low_precision"),
        (9, 40, "very_low_precision"),
        (40, 12, None),  # negative control: neither class is short, so no tier
    ],
)
def test_the_clustered_precision_tier_reads_the_scarcer_class(n_pos_cases, n_neg_cases, expected):
    """R1 (regression) / FA-B2 (fresh attack): the tier read only the positive class.

    R2 section 3.3 asks for at least ten positives **and** at least ten negatives
    before an AUROC per group is evaluable, so the tier has to come from whichever
    class is scarce. Repair round 1 passed ``class_units["positive"]`` in as the event
    count, so an AUROC resting on three negative patients carried no tier at all, where
    the code before it did. ``imprecise`` is not a substitute - it is a half-width
    heuristic and it does not fire when the interval is narrow (100 against 8 below).
    """
    s, y, cid = _imbalanced_lesion_cohort(n_pos_cases, n_neg_cases, 3, seed=5)
    cell = auroc_ci(
        s,
        y,
        cell_key="subgroups.site.C.auroc",
        plan=plan_clustering("case_id", cid),
        cluster_ids=cid,
        policy=BootstrapPolicy(n_resamples=200),
    )
    tiers = {"not_evaluable_shown_for_transparency", "very_low_precision"}
    got = set(cell.number.flags) & tiers
    assert got == ({expected} if expected else set()), cell.number.flags

    # and it is symmetric: the same shortage on the other side gets the same tier
    s2, y2, cid2 = _imbalanced_lesion_cohort(n_neg_cases, n_pos_cases, 3, seed=5)
    mirror = auroc_ci(
        s2,
        y2,
        cell_key="subgroups.site.C.auroc",
        plan=plan_clustering("case_id", cid2),
        cluster_ids=cid2,
        policy=BootstrapPolicy(n_resamples=200),
    )
    assert set(mirror.number.flags) & tiers == got


def test_both_auroc_routes_use_one_definition_of_a_scarce_class():
    """R1 (regression) / FA-N6 (fresh attack): two definitions of "events" in one module.

    The i.i.d. small-class branch counted events as ``min(n_pos, n_neg)`` against
    ``n_pos + n_neg`` units, so nine positives among 409 rows carried no tier either -
    409 units, nine events, and R2 section 3.3's five-event floor never reached. Both
    branches now ask one question: is either class below ``LOW_PRECISION_UNITS``?
    """
    rng = np.random.default_rng(7)
    y = np.array([True] * 9 + [False] * 400)
    s = rng.normal(size=409) + y * 1.0
    iid = auroc_ci(s, y, cell_key="c", policy=BootstrapPolicy(n_resamples=200))
    assert iid.number.method == "bootstrap_percentile"
    assert "very_low_precision" in iid.number.flags

    # the same nine-against-many shortage, clustered: the same tier
    s2, y2, cid2 = _imbalanced_lesion_cohort(9, 400, 2, seed=11)
    clustered = auroc_ci(
        s2,
        y2,
        cell_key="c",
        plan=plan_clustering("case_id", cid2),
        cluster_ids=cid2,
        policy=BootstrapPolicy(n_resamples=200),
    )
    assert "very_low_precision" in clustered.number.flags


def _one_pure_one_mixed_cohort(positive_side: bool, n_other: int = 60, seed: int = 13):
    """One pure case and one mixed case supplying a class, against ``n_other`` pure cases.

    Two rows per case. The class in question has ``class_units == 2`` and **zero**
    resampling variability: a stratum of one unit draws that unit every time.
    """
    rows = [[True, True], [True, False]] + [[False, False]] * n_other
    y = np.array([v for case in rows for v in case])
    if not positive_side:
        y = ~y
    cid = np.repeat(np.arange(n_other + 2), 2)
    s = np.random.default_rng(seed).normal(size=y.shape[0]) + y * 1.0
    return s, y, cid


@pytest.mark.parametrize("positive_side", [True, False])
def test_a_class_whose_every_stratum_is_a_singleton_is_refused(positive_side):
    """FA-B1 (fresh attack): the round-1 class floor counted units it could not resample.

    Strata ``{positive: 1, mixed: 1, negative: 60}`` sum to two positive units and
    passed the floor, but the pure stratum draws one from one and the mixed stratum
    draws one from one, so **every resample carries the same positive rows**. The
    engine rendered an interval there - measured coverage 0.233 against a nominal 0.95
    over 300 replications, 15x too narrow on one draw - where the code before round 1
    refused with ``insufficient_clusters``. That is the module's own stated rationale
    for ``MIN_UNITS_PER_STRATUM``: below two independent units supplying a class, the
    interval carries no uncertainty about it.
    """
    s, y, cid = _one_pure_one_mixed_cohort(positive_side)
    resampler = clustered_by_case(y, cid)
    label = "positive" if positive_side else "negative"
    assert resampler.units_per_stratum.get("mixed") == 1
    assert resampler.class_units[label] == 2  # the count that satisfied the round-1 floor

    # the property the floor exists to guarantee, measured rather than argued
    gen = np.random.default_rng(1)
    wanted = y if positive_side else ~y
    seen = {tuple(sorted(int(i) for i in resampler.draw(gen) if wanted[i])) for _ in range(200)}
    assert len(seen) == 1, "the class does vary; this fixture no longer proves anything"

    assert resampler.deficient_class == label
    cell = auroc_ci(
        s,
        y,
        cell_key="subgroups.age.65plus.auroc",
        plan=plan_clustering("case_id", cid),
        cluster_ids=cid,
        policy=BootstrapPolicy(n_resamples=400),
    )
    assert not cell.number.has_ci, (cell.number.ci_lo, cell.number.ci_hi)
    assert cell.number.not_estimable_reason == "insufficient_clusters"

    # and the round-1 repair this must not undo: one mixed case among many pure ones
    # still forms an interval (the D2 defect, re-asserted from the other direction)
    s2, y2, cid2 = _multi_lesion_cohort(200, 2, seed=7, mixed=1)
    kept = auroc_ci(
        s2,
        y2,
        cell_key="overall.auroc",
        plan=plan_clustering("case_id", cid2),
        cluster_ids=cid2,
        policy=BootstrapPolicy(n_resamples=200),
    )
    assert kept.number.has_ci, kept.number.not_estimable_reason


def test_a_mixed_outcome_case_counts_towards_both_classes():
    """FA-B3 (fresh attack): the load-bearing half of the round-1 D2 repair, pinned.

    Mutation R7 - ``mixed = 0`` in ``Resampler.class_units`` - survived all 102 day-4
    tests, because the D2 regression cohort is 199 pure cases plus one mixed and the
    pure strata carry the count on their own. On the canonical multi-lesion design,
    forty patients each with one malignant and one benign lesion, **every** case is
    mixed: without the clause both classes report zero units and the whole 80-lesion
    cell is refused.
    """
    rng = np.random.default_rng(21)
    y = np.array([True, False] * 40)
    cid = np.repeat(np.arange(40), 2)
    s = rng.normal(size=80) + y * 1.0

    resampler = clustered_by_case(y, cid)
    assert resampler.units_per_stratum == {"mixed": 40}
    assert resampler.class_units == {"positive": 40, "negative": 40}
    assert resampler.deficient_class is None

    cell = auroc_ci(
        s,
        y,
        cell_key="overall.auroc",
        plan=plan_clustering("case_id", cid),
        cluster_ids=cid,
        policy=BootstrapPolicy(n_resamples=400),
    )
    assert cell.number.method == "cluster_bootstrap_percentile"
    assert cell.number.has_ci, cell.number.not_estimable_reason
    assert cell.number.n_cases == 40
    assert cell.number.n_pos == 40 and cell.number.n_neg == 40


def test_one_number_never_carries_two_precision_tiers():
    """FA-N2 (fresh attack): the single-tier guard was pinned by no test.

    Under clustering the caller assigns the tier from the **case** count, which is the
    effective sample size, while ``Number.n`` is the row count; twenty rows over five
    patients would otherwise print *not evaluable* and *very low precision* on one
    Number, which is a contradiction a reviewer has to resolve by guessing. Round 1
    added the guard while repairing the tier and left it unpinned - mutation R16
    survived all 102 day-4 tests.
    """
    cid = np.repeat(np.arange(5), 4)
    ind = np.repeat(np.random.default_rng(3).random(5) < 0.6, 4)
    cell = proportion_ci(
        ind,
        cell_key="op1.sensitivity",
        plan=plan_clustering("case_id", cid),
        cluster_ids=cid,
        policy=BootstrapPolicy(n_resamples=200),
    )
    assert cell.number.n == 20 and cell.number.n_cases == 5
    tiers = set(Number.PRECISION_TIERS) & set(cell.number.flags)
    assert tiers == {"not_evaluable_shown_for_transparency"}, cell.number.flags
