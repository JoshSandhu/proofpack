"""Day 3 (E3) - ``stats.discrimination``.

F3 (R2 section 9) is checked value by value. The DeLong standard error is *also*
hand-derived here from the definition of the structural components, so the fixture
is not merely copied from the research document: the placement values, the two
component variances, the variance and the SE are all written out below and asserted
against the fast Sun & Xu implementation.

AUPRC is deferred to v1.1 (brief) - a test asserts nothing computes one.
"""

from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import pytest

from proofpack.stats.discrimination import (
    LOGIT_PRIMARY_CLASS,
    auroc_mann_whitney,
    auroc_number,
    delong_covariance,
    delong_variance,
    locate_operating_points,
    logit_ci,
    paired_delong,
    roc_curve,
    wald_ci,
)
from proofpack.stats.number import Number

pytestmark = pytest.mark.day3

REPO = pathlib.Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------------ F3 inputs

F3_Y = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0], dtype=bool)
F3_S1 = np.array([0.9, 0.8, 0.7, 0.6, 0.35, 0.75, 0.5, 0.4, 0.3, 0.2])
F3_S2 = np.array([0.85, 0.6, 0.65, 0.4, 0.3, 0.7, 0.55, 0.45, 0.35, 0.25])

F3_EXPECTED = {
    "auc1": 0.80,
    "se1": 0.1549,
    "wald": (0.4964, 1.1036),
    "logit": (0.3748, 0.9639),
    "auc2": 0.64,
    "var_diff": 0.0072,
    "z": 1.8856,
    "p": 0.0593,
}

# ---- Hand-computed DeLong structural components for F3/s1 (see module docstring).
# positives x = [0.90, 0.80, 0.70, 0.60, 0.35]; negatives y = [0.75, 0.50, 0.40, 0.30, 0.20]
# V10[i] = (1/n0) * sum_j psi(x_i, y_j), psi = 1 if x > y, 0.5 if x == y, 0 otherwise:
#   0.90 beats all 5 -> 1.0 ; 0.80 beats all 5 -> 1.0 ; 0.70 beats 4 -> 0.8 ;
#   0.60 beats 4 -> 0.8 ; 0.35 beats {0.30, 0.20} -> 0.4
# V01[j] = (1/m) * sum_i psi(x_i, y_j):
#   0.75 <- {0.90, 0.80} -> 0.4 ; 0.50 <- 4 -> 0.8 ; 0.40 <- 4 -> 0.8 ;
#   0.30 <- 5 -> 1.0 ; 0.20 <- 5 -> 1.0
# S10 = var(V10, ddof=1) = 0.24 / 4 = 0.06 ; S01 = var(V01, ddof=1) = 0.24 / 4 = 0.06
# Var(AUC) = S10 / m + S01 / n0 = 0.06/5 + 0.06/5 = 0.024 ; SE = sqrt(0.024) = 0.15491933...
HAND_V10 = [1.0, 1.0, 0.8, 0.8, 0.4]
HAND_V01 = [0.4, 0.8, 0.8, 1.0, 1.0]
HAND_S10 = 0.06
HAND_S01 = 0.06
HAND_VAR = 0.024
HAND_SE = 0.15491933384829668


def _brute_force_components(scores: np.ndarray, pos: np.ndarray) -> tuple[list, list]:
    """V10 / V01 straight from the kernel definition - O(n*m), no midrank tricks."""
    x = scores[pos]
    y = scores[~pos]

    def psi(a: float, b: float) -> float:
        return 1.0 if a > b else (0.5 if a == b else 0.0)

    v10 = [sum(psi(xi, yj) for yj in y) / len(y) for xi in x]
    v01 = [sum(psi(xi, yj) for xi in x) / len(x) for yj in y]
    return v10, v01


# ------------------------------------------------------------------------ AUROC


@pytest.mark.fixture
def test_f3_auroc_matches_sklearn_to_1e_9():
    sk = pytest.importorskip("sklearn.metrics")
    for s in (F3_S1, F3_S2):
        ours = auroc_mann_whitney(s, F3_Y)
        theirs = float(sk.roc_auc_score(F3_Y.astype(int), s))
        assert abs(ours - theirs) < 1e-9, (ours, theirs)
    assert abs(auroc_mann_whitney(F3_S1, F3_Y) - F3_EXPECTED["auc1"]) < 1e-12
    assert abs(auroc_mann_whitney(F3_S2, F3_Y) - F3_EXPECTED["auc2"]) < 1e-12


@pytest.mark.fixture
def test_auroc_matches_sklearn_over_random_cohorts_including_heavy_ties():
    """Acceptance line: AUROC within 1e-9 of sklearn. Checked on 200 random cohorts."""
    sk = pytest.importorskip("sklearn.metrics")
    rng = np.random.default_rng(20260909)
    worst = 0.0
    for _ in range(200):
        n = int(rng.integers(10, 400))
        y = rng.integers(0, 2, size=n).astype(bool)
        if y.all() or (~y).all():
            continue
        style = rng.integers(0, 3)
        if style == 0:
            s = rng.normal(size=n) + y * 0.8
        elif style == 1:  # heavy ties: only 4 distinct scores
            s = np.round(rng.random(n) * 3) / 3.0
        else:  # every score identical -> AUC exactly 0.5
            s = np.full(n, 0.42)
        d = abs(auroc_mann_whitney(s, y) - float(sk.roc_auc_score(y.astype(int), s)))
        worst = max(worst, d)
    assert worst < 1e-9, worst


def test_auroc_matches_scipy_mannwhitneyu():
    scipy_stats = pytest.importorskip("scipy.stats")
    u = scipy_stats.mannwhitneyu(F3_S1[F3_Y], F3_S1[~F3_Y], alternative="greater").statistic
    assert abs(auroc_mann_whitney(F3_S1, F3_Y) - u / 25.0) < 1e-12


def test_auroc_needs_both_classes():
    with pytest.raises(ValueError, match="both classes"):
        auroc_mann_whitney(F3_S1, np.ones(10, dtype=bool))


# ------------------------------------------------------------- DeLong variance (F3)


@pytest.mark.fixture
def test_delong_se_matches_the_hand_computed_fixture_to_1e_6():
    """Acceptance line: DeLong SE within 1e-6 of the hand-computed fixture."""
    auc, var = delong_variance(F3_S1, F3_Y)
    se = math.sqrt(var)
    assert abs(auc - F3_EXPECTED["auc1"]) < 1e-12
    assert abs(var - HAND_VAR) < 1e-12
    assert abs(se - HAND_SE) < 1e-6
    assert abs(se - F3_EXPECTED["se1"]) < 1e-4  # the value as printed in R2 section 9


@pytest.mark.fixture
def test_fast_algorithm_reproduces_the_hand_computed_structural_components():
    """Sun & Xu midranks must equal the O(n*m) kernel definition, term by term."""
    v10, v01 = _brute_force_components(F3_S1, F3_Y)
    assert v10 == HAND_V10
    assert v01 == HAND_V01
    assert abs(float(np.var(v10, ddof=1)) - HAND_S10) < 1e-15
    assert abs(float(np.var(v01, ddof=1)) - HAND_S01) < 1e-15
    # ... and the fast path must produce the same variance from them.
    _, s = delong_covariance(F3_S1[None, :], F3_Y)
    assert abs(float(s[0, 0]) - (HAND_S10 / 5 + HAND_S01 / 5)) < 1e-15


def test_fast_and_brute_force_agree_on_random_cohorts_with_ties():
    rng = np.random.default_rng(7)
    for _ in range(60):
        n = int(rng.integers(8, 60))
        y = rng.integers(0, 2, size=n).astype(bool)
        if y.sum() < 2 or (~y).sum() < 2:
            continue
        s = np.round(rng.random(n) * 5) / 5.0  # deliberate ties
        v10, v01 = _brute_force_components(s, y)
        m, n0 = int(y.sum()), int((~y).sum())
        expected = float(np.var(v10, ddof=1)) / m + float(np.var(v01, ddof=1)) / n0
        _, var = delong_variance(s, y)
        assert abs(var - expected) < 1e-12


def test_delong_needs_two_of_each_class():
    y = np.array([1, 0, 0, 0], dtype=bool)
    with pytest.raises(ValueError, match="at least two"):
        delong_variance(np.array([0.9, 0.5, 0.4, 0.3]), y)


# -------------------------------------------------------------------------- intervals


@pytest.mark.fixture
def test_f3_wald_and_logit_intervals():
    auc, var = delong_variance(F3_S1, F3_Y)
    se = math.sqrt(var)
    w = wald_ci(auc, se)
    assert abs(w[0] - F3_EXPECTED["wald"][0]) < 1e-4
    assert abs(w[1] - F3_EXPECTED["wald"][1]) < 1e-4
    assert w[1] > 1.0  # this is why the logit interval is primary here
    lg = logit_ci(auc, se)
    assert abs(lg[0] - F3_EXPECTED["logit"][0]) < 1e-4
    assert abs(lg[1] - F3_EXPECTED["logit"][1]) < 1e-4
    assert 0.0 < lg[0] < auc < lg[1] < 1.0


@pytest.mark.fixture
def test_f3_auroc_number_prefers_logit_and_flags_the_wald_overflow():
    r = auroc_number(F3_S1, F3_Y)
    assert r.auroc.method == "delong_logit"
    assert r.auroc.n_pos == 5 and r.auroc.n_neg == 5
    assert "very_low_precision" in r.auroc.flags  # min class < 10 (R2 section 1.3)
    assert r.auroc_secondary.method == "delong_wald"
    assert "wald_interval_exceeds_unit_range" in r.auroc_secondary.flags
    assert r.auroc_secondary.ci_hi == 1.0  # clamped for rendering, flagged as clamped
    assert abs(r.se - HAND_SE) < 1e-6


def test_wald_is_primary_for_a_large_mid_range_auc():
    rng = np.random.default_rng(11)
    n = 800
    y = np.array([True] * 400 + [False] * 400)
    s = rng.normal(size=n) + y * 0.9
    r = auroc_number(s, y)
    assert min(r.auroc.n_pos, r.auroc.n_neg) >= LOGIT_PRIMARY_CLASS
    assert 0.5 < r.auroc.est < 0.9
    assert r.auroc.method == "delong_wald"
    assert r.auroc_secondary.method == "delong_logit"


def test_logit_is_primary_above_point_nine_even_at_large_n():
    rng = np.random.default_rng(12)
    y = np.array([True] * 400 + [False] * 400)
    s = rng.normal(size=800) + y * 3.0
    r = auroc_number(s, y)
    assert r.auroc.est > 0.9
    assert r.auroc.method == "delong_logit"


def test_logit_ci_is_undefined_at_a_degenerate_auc():
    with pytest.raises(ValueError, match="undefined at AUC"):
        logit_ci(1.0, 0.05)


def test_perfect_separation_gives_a_typed_reason_not_a_zero_width_interval():
    y = np.array([True] * 5 + [False] * 5)
    s = np.array([0.9, 0.8, 0.7, 0.6, 0.55, 0.4, 0.3, 0.2, 0.1, 0.05])
    r = auroc_number(s, y)
    assert r.auroc.est == 1.0
    assert not r.auroc.has_ci
    assert r.auroc.not_estimable_reason == "boundary_estimate"
    assert "ci_pending_bootstrap" in r.auroc.flags


def test_single_class_gives_a_typed_reason():
    r = auroc_number(F3_S1, np.ones(10, dtype=bool))
    assert r.auroc.not_estimable_reason == "single_class"
    assert r.roc == []


def test_delong_is_refused_under_clustering_rather_than_reported_too_small():
    """F9's premise: duplicating each row k times shrinks the naive SE by ~sqrt(k)."""
    y = np.repeat(F3_Y, 3)
    s = np.repeat(F3_S1, 3)
    _, var = delong_variance(s, y)
    naive_se = math.sqrt(var)
    assert naive_se < HAND_SE / 1.5  # demonstrably wrong under clustering
    r = auroc_number(s, y, clustered=True, n_cases=10)
    assert not r.auroc.has_ci
    assert r.auroc.not_estimable_reason == "clustered_data_analytic_ci_invalid"
    assert r.auroc.n_cases == 10
    assert abs(r.auroc.est - 0.8) < 1e-12  # the point estimate is still correct
    assert r.se is None


# ---------------------------------------------------------------------- paired DeLong


@pytest.mark.fixture
def test_f3_paired_delong():
    pd = paired_delong(F3_S1, F3_S2, F3_Y)
    assert abs(pd.auroc_a.est - F3_EXPECTED["auc1"]) < 1e-12
    assert abs(pd.auroc_b.est - F3_EXPECTED["auc2"]) < 1e-12
    assert abs(pd.variance_difference - F3_EXPECTED["var_diff"]) < 1e-4
    assert abs(pd.z - F3_EXPECTED["z"]) < 1e-4
    assert abs(pd.p_value - F3_EXPECTED["p"]) < 1e-4
    assert pd.method == "paired_delong"
    assert pd.difference.method == "delong_wald"
    assert pd.difference.ci_lo < pd.difference.est < pd.difference.ci_hi


def test_paired_variance_is_smaller_than_the_unpaired_sum_when_correlated():
    _, s = delong_covariance(np.vstack([F3_S1, F3_S2]), F3_Y)
    unpaired = float(s[0, 0] + s[1, 1])
    paired = float(s[0, 0] + s[1, 1] - 2 * s[0, 1])
    assert s[0, 1] > 0  # the two classifiers are positively correlated
    assert paired < unpaired


def test_paired_p_value_matches_the_normal_tail():
    scipy_stats = pytest.importorskip("scipy.stats")
    pd = paired_delong(F3_S1, F3_S2, F3_Y)
    assert abs(pd.p_value - 2 * (1 - scipy_stats.norm.cdf(abs(pd.z)))) < 1e-12


def test_paired_delong_of_a_classifier_against_itself_is_a_zero_difference():
    pd = paired_delong(F3_S1, F3_S1, F3_Y)
    assert abs(pd.variance_difference) < 1e-15
    assert pd.z == 0.0
    assert pd.p_value == 1.0
    assert pd.difference.not_estimable_reason == "boundary_estimate"


def test_paired_delong_requires_the_same_cases():
    with pytest.raises(ValueError, match="same cases"):
        paired_delong(F3_S1, F3_S2[:5], F3_Y)


# -------------------------------------------------------------------------- ROC arrays


def test_roc_curve_starts_at_the_origin_and_is_monotone():
    roc = roc_curve(F3_S1, F3_Y)
    assert roc[0] == [0.0, 0.0, float("inf")]
    assert roc[-1][:2] == [1.0, 1.0]
    fprs = [p[0] for p in roc]
    tprs = [p[1] for p in roc]
    assert fprs == sorted(fprs)
    assert tprs == sorted(tprs)
    assert len(roc) == 1 + len(set(F3_S1.tolist()))


def test_roc_curve_trapezoid_area_equals_the_auroc():
    for scores in (F3_S1, F3_S2):
        roc = roc_curve(scores, F3_Y)
        x = [p[0] for p in roc]
        y = [p[1] for p in roc]
        area = sum((x[i + 1] - x[i]) * (y[i + 1] + y[i]) / 2.0 for i in range(len(roc) - 1))
        assert abs(area - auroc_mann_whitney(scores, F3_Y)) < 1e-12


def test_roc_curve_matches_sklearn():
    sk = pytest.importorskip("sklearn.metrics")
    fpr, tpr, _ = sk.roc_curve(F3_Y.astype(int), F3_S1, drop_intermediate=False)
    ours = roc_curve(F3_S1, F3_Y)
    assert [round(p[0], 12) for p in ours] == [round(float(v), 12) for v in fpr]
    assert [round(p[1], 12) for p in ours] == [round(float(v), 12) for v in tpr]


def test_operating_points_are_located_on_the_curve():
    from proofpack.io.declare import OperatingPoint

    ops = [OperatingPoint(id="op1", threshold=0.6, rule=">=", provenance="declared")]
    marks = locate_operating_points(F3_S1, F3_Y, ops)
    assert marks == [{"id": "op1", "threshold": 0.6, "fpr": 0.2, "tpr": 0.8}]


# ------------------------------------------------------------------- AUPRC is deferred


def test_auprc_is_not_implemented_in_v1():
    """The brief defers AUPRC to v1.1. Nothing may compute one, and the schema
    types the field as null so it cannot be emitted by accident."""
    import proofpack.stats.discrimination as disc
    from proofpack.resources import load_json_schema

    assert not any("auprc" in name.lower() for name in dir(disc))
    src = (REPO / "src" / "proofpack").rglob("*.py")
    for path in src:
        text = path.read_text(encoding="utf-8").lower()
        assert "average_precision" not in text, path
    schema = load_json_schema("output_schema_v1.json")
    assert schema["$defs"]["thresholdFree"]["properties"]["auprc"]["type"] == "null"


# ------------------------------------------------------- every Number still has a CI


def test_every_discrimination_number_has_a_ci_or_a_typed_reason():
    rng = np.random.default_rng(3)
    produced: list[Number] = []
    cases = [
        (F3_S1, F3_Y, False),
        (F3_S1, np.ones(10, dtype=bool), False),
        (np.repeat(F3_S1, 3), np.repeat(F3_Y, 3), True),
        (np.full(10, 0.5), F3_Y, False),  # every score tied -> AUC 0.5, SE 0
        (np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]), F3_Y, False),
    ]
    for _ in range(30):
        n = int(rng.integers(4, 80))
        y = rng.integers(0, 2, size=n).astype(bool)
        cases.append((rng.random(n), y, False))
    for s, y, clustered in cases:
        r = auroc_number(s, y, clustered=clustered, n_cases=len(s) // 3 or None)
        produced.append(r.auroc)
        if r.auroc_secondary is not None:
            produced.append(r.auroc_secondary)
        if int(y.sum()) >= 2 and int((~y).sum()) >= 2:
            pd = paired_delong(s, s[::-1], y)
            produced.extend([pd.auroc_a, pd.auroc_b, pd.difference])
    assert len(produced) > 40
    for num in produced:
        assert num.has_ci or num.not_estimable_reason is not None
        if num.has_ci:
            assert num.method in ("delong_logit", "delong_wald")
            assert num.ci_lo <= num.est <= num.ci_hi or num.method == "delong_wald"


def test_discrimination_imports_without_scipy():
    """Module-level scipy import would break the day-1 import-light CI job."""
    text = (REPO / "src" / "proofpack" / "stats" / "discrimination.py").read_text()
    assert "import scipy" not in text


# ------------------------------------------------------------------ F13 (pending R)

F13_PATH = REPO / "fixtures" / "r" / "proc_asah.json"


@pytest.mark.fixture
@pytest.mark.xfail(reason="pending R capture on day 12 (pROC on aSAH); fixture not yet committed")
def test_f13_matches_proc_on_the_asah_dataset():
    """pROC ``roc``/``ci.auc(method='delong')``/``roc.test`` on ``aSAH``.

    Day 12 runs ``rocker/r-ver`` in CI and commits ``fixtures/r/proc_asah.json`` with
    the s100b and ndka scores, the reference outcome, the two AUCs, the DeLong CIs
    and the paired test. This test is written against that shape now so the capture
    has an exact target; it xfails until the file exists. Engine must match AUC and
    the DeLong CI within 1e-6 (D1 section 3.2, v1 stage-7 acceptance).
    """
    with F13_PATH.open(encoding="utf-8") as fh:
        cap = json.load(fh)
    y = np.array(cap["outcome_poor"], dtype=bool)
    s100b = np.array(cap["s100b"], dtype=float)
    ndka = np.array(cap["ndka"], dtype=float)

    r = auroc_number(s100b, y)
    assert abs(r.auroc.est - cap["auc_s100b"]) < 1e-6
    assert abs(r.se - cap["delong_se_s100b"]) < 1e-6
    lo, hi = cap["delong_ci_s100b"]
    w = wald_ci(r.auroc.est, r.se)
    assert abs(w[0] - lo) < 1e-6 and abs(w[1] - hi) < 1e-6

    pd = paired_delong(s100b, ndka, y)
    assert abs(pd.z - cap["roc_test_z"]) < 1e-6
    assert abs(pd.p_value - cap["roc_test_p"]) < 1e-6


def test_f13_capture_is_still_outstanding():
    """Guard: if someone commits the capture, the xfail above must be removed."""
    assert not F13_PATH.exists(), (
        "fixtures/r/proc_asah.json now exists - remove the xfail on "
        "test_f13_matches_proc_on_the_asah_dataset and make it a real test"
    )
