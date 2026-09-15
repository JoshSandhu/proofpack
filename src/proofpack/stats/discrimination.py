"""``stats.discrimination`` - AUROC, DeLong variance, and the ROC coordinate arrays.

Methods (D1 section 3.1, R2 section 1.3):

* **AUROC** by the Mann-Whitney statistic with midranks for ties. Exact, numpy only.
* **DeLong (1988) variance** from structural components, computed with the
  **Sun & Xu (2014)** O(N log N) midrank algorithm - written here from the published
  algorithm, nothing vendored (so R2 section 10's licence question does not arise).
* **Logit-transformed CI** as the primary interval when ``AUC > 0.9`` or either class
  has fewer than 30 cases; the plain Wald interval is carried alongside as secondary
  and is flagged when it leaves ``[0, 1]``.
* **Paired DeLong** for two correlated ROC curves on the same cases: the covariance
  of the two AUCs comes from the same structural components, giving
  ``Var(A - B) = S_aa + S_bb - 2 S_ab``, a z statistic and a two-sided p-value.
* **ROC coordinate arrays** with the declared operating points located on the curve.

**AUPRC is deferred to v1.1 and is deliberately not implemented here.** The output
schema types ``auprc`` as ``null`` so nobody can quietly start emitting one.

**Clustered data**: when rows are not independent (declared ``clustering.unit =
case_id``, or more rows than cases) the DeLong variance is *wrong* - it shrinks
roughly as sqrt(rows/cases). It is refused with the typed reason
``clustered_data_analytic_ci_invalid``. The refusal is not a property of this module:
nothing here inspects a case column, and this file will compute a DeLong interval over
whatever rows it is handed. It is ``stats.bootstrap.auroc_ci`` that decides the route,
and it can only decide it on the ``cluster_ids`` it is given - see that module's
docstring for what its guard checks and for the cases it cannot see. Since build
day 4 ``auroc_ci`` fills the clustered path with a cluster bootstrap, so this Number no
longer promises a later interval - it is the companion refusal itself.

**That covers ``auroc_number`` and nothing else in this file.** ``paired_delong``, the
version-comparison statistic the PCCP performance-evaluation report rests on, has no
``cluster_ids`` parameter for a caller to pass and no route decision anywhere: it will
build a ``delong_wald`` interval for the difference and two logit intervals for the arms
over clustered rows, with no flag and no companion refusal, exactly as ``auroc_number``
would. Nothing in ``src`` calls it yet (the round-7 fresh attack, 2026-09-10). Making it
clustering-aware needs a cluster bootstrap of the *difference*, which is a build-day
feature and not a docstring; until then the caller that reads the customer's table has to
carry clustering here itself.

No scipy: the normal quantile comes from ``statistics.NormalDist`` and the normal
tail from ``math.erfc``.

References
----------
DeLong ER, DeLong DM, Clarke-Pearson DL. "Comparing the areas under two or more
correlated receiver operating characteristic curves: a nonparametric approach."
Biometrics 1988;44:837-845.
Sun X, Xu W. "Fast implementation of DeLong's algorithm for comparing the areas
under correlated receiver operating characteristic curves." IEEE Signal Processing
Letters 2014;21(11):1389-1393. **[unverified - the paper was not fetched in this
build environment (egress allowlist); the algorithm implemented below is the
standard midrank formulation and is checked against a direct O(n*m) computation of
the same structural components in the tests, so its correctness does not rest on
the citation.]**
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from proofpack.stats.number import Number, not_estimable
from proofpack.stats.proportions import z_for

__all__ = [
    "DiscriminationResult",
    "auroc",
    "auroc_mann_whitney",
    "auroc_number",
    "delong_covariance",
    "delong_variance",
    "logit_ci",
    "paired_delong",
    "roc_curve",
    "unpaired_delong",
    "wald_ci",
]


# --------------------------------------------------------------------------- AUROC


def auroc_mann_whitney(scores: np.ndarray, positives: np.ndarray) -> float:
    """AUROC by Mann-Whitney placement with midranks for ties (numpy only).

    ``positives`` is a boolean mask. Requires at least one positive and one negative.
    Ties contribute 0.5, which is what the midrank average gives.
    """
    scores = np.asarray(scores, dtype=np.float64)
    pos = np.asarray(positives, dtype=bool)
    n1 = int(pos.sum())
    n0 = int((~pos).sum())
    if n1 == 0 or n0 == 0:
        raise ValueError("AUROC needs both classes")
    ranks = _midranks(scores)
    rank_sum_pos = float(ranks[pos].sum())
    return float((rank_sum_pos - n1 * (n1 + 1) / 2.0) / (n1 * n0))


#: Alias; ``auroc`` is the name the rest of the stats package uses.
auroc = auroc_mann_whitney


def _midranks(x: np.ndarray) -> np.ndarray:
    """1-based midranks of ``x`` (average rank within each tie group). O(n log n)."""
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[0]
    order = np.argsort(x, kind="mergesort")
    sorted_x = x[order]
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_x[j + 1] == sorted_x[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j + 2) / 2.0
        i = j + 1
    return ranks


# ------------------------------------------------------------------ DeLong (Sun & Xu)


def delong_covariance(
    score_matrix: np.ndarray, positives: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """DeLong structural components for one or more classifiers on the same cases.

    ``score_matrix`` is ``(k, n)`` - one row per classifier, one column per case, all
    classifiers scoring the *same* cases in the same order. Returns ``(aucs, S)``
    where ``S`` is the ``(k, k)`` covariance matrix of the AUC estimates.

    Sun & Xu's formulation, using midranks of each classifier's scores computed
    three times - within positives, within negatives, and over the pooled sample::

        V10[k, i] = (tz[k, i]      - tx[k, i]) / n0            for the m positives
        V01[k, j] = 1 - (tz[k, m+j] - ty[k, j]) / m            for the n0 negatives
        S = cov(V10) / m + cov(V01) / n0                       (unbiased, ddof=1)

    ``auc[k] = mean(tz[k, :m]) / n0 - (m + 1) / (2 n0)`` falls out of the same
    midranks and is asserted equal to :func:`auroc_mann_whitney` in the tests.
    """
    sm = np.atleast_2d(np.asarray(score_matrix, dtype=np.float64))
    pos = np.asarray(positives, dtype=bool)
    if sm.shape[1] != pos.shape[0]:
        raise ValueError("score_matrix columns must align with the positives mask")
    m = int(pos.sum())
    n0 = int((~pos).sum())
    if m < 2 or n0 < 2:
        raise ValueError("DeLong needs at least two positives and two negatives")
    k = sm.shape[0]

    x = sm[:, pos]  # (k, m)   positives
    y = sm[:, ~pos]  # (k, n0)  negatives
    v10 = np.empty((k, m), dtype=np.float64)
    v01 = np.empty((k, n0), dtype=np.float64)
    aucs = np.empty(k, dtype=np.float64)
    for r in range(k):
        tx = _midranks(x[r])
        ty = _midranks(y[r])
        tz = _midranks(np.concatenate([x[r], y[r]]))
        v10[r] = (tz[:m] - tx) / n0
        v01[r] = 1.0 - (tz[m:] - ty) / m
        aucs[r] = float(tz[:m].sum()) / (m * n0) - (m + 1.0) / (2.0 * n0)

    s10 = np.cov(v10, ddof=1) if k > 1 else np.array([[float(np.var(v10[0], ddof=1))]])
    s01 = np.cov(v01, ddof=1) if k > 1 else np.array([[float(np.var(v01[0], ddof=1))]])
    s = np.atleast_2d(s10) / m + np.atleast_2d(s01) / n0
    return aucs, s


def delong_variance(scores: np.ndarray, positives: np.ndarray) -> tuple[float, float]:
    """``(auc, variance)`` for a single classifier."""
    aucs, s = delong_covariance(np.asarray(scores, dtype=np.float64)[None, :], positives)
    return float(aucs[0]), float(s[0, 0])


# --------------------------------------------------------------------------- intervals


def wald_ci(auc: float, se: float, level: float = 0.95) -> tuple[float, float]:
    """Plain DeLong Wald interval. May leave [0, 1]; that is the point of the flag."""
    z = z_for(level)
    return (auc - z * se, auc + z * se)


def logit_ci(auc: float, se: float, level: float = 0.95) -> tuple[float, float]:
    """Logit-transformed DeLong interval.

    ``eta = log(A / (1 - A))``, ``SE(eta) = SE(A) / (A (1 - A))``, interval on the
    logit scale, back-transformed with the logistic. Always inside (0, 1).
    """
    if not 0.0 < auc < 1.0:
        raise ValueError("logit transform undefined at AUC 0 or 1")
    z = z_for(level)
    eta = math.log(auc / (1.0 - auc))
    se_eta = se / (auc * (1.0 - auc))
    lo = eta - z * se_eta
    hi = eta + z * se_eta
    return (1.0 / (1.0 + math.exp(-lo)), 1.0 / (1.0 + math.exp(-hi)))


#: Below this count in either class, R2 section 1.3 wants a stratified bootstrap
#: instead of DeLong; ``stats.bootstrap.auroc_ci`` routes that switch and records it.
SMALL_CLASS = 10
#: At or below this, the logit interval is primary regardless of the AUC (D1 section 3.1).
LOGIT_PRIMARY_CLASS = 30


@dataclass
class DiscriminationResult:
    """AUROC with both intervals, the ROC arrays, and the counts behind them."""

    auroc: Number
    auroc_secondary: Number | None
    se: float | None
    n_pos: int
    n_neg: int
    roc: list[list[float]]
    clustered: bool = False
    n_cases: int | None = None


def auroc_number(
    scores: np.ndarray,
    positives: np.ndarray,
    level: float = 0.95,
    clustered: bool = False,
    n_cases: int | None = None,
) -> DiscriminationResult:
    """The rendered AUROC: point estimate, primary interval, secondary interval.

    The primary interval is the **logit** DeLong CI when ``AUC > 0.9`` or either
    class has fewer than 30 cases, and the plain Wald CI otherwise; the other one is
    returned as ``auroc_secondary``. Under clustering, DeLong is refused outright.
    """
    scores = np.asarray(scores, dtype=np.float64)
    pos = np.asarray(positives, dtype=bool)
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    roc = roc_curve(scores, pos) if n_pos and n_neg else []

    if n_pos == 0 or n_neg == 0:
        return DiscriminationResult(
            auroc=not_estimable("single_class", n_pos=n_pos, n_neg=n_neg, ci_level=level),
            auroc_secondary=None,
            se=None,
            n_pos=n_pos,
            n_neg=n_neg,
            roc=roc,
        )
    point = auroc_mann_whitney(scores, pos)

    if clustered:
        # Rows are not independent: the DeLong variance would be too small. Refuse it.
        return DiscriminationResult(
            auroc=not_estimable(
                "clustered_data_analytic_ci_invalid",
                est=point,
                n_pos=n_pos,
                n_neg=n_neg,
                n_cases=n_cases,
                ci_level=level,
            ),
            auroc_secondary=None,
            se=None,
            n_pos=n_pos,
            n_neg=n_neg,
            roc=roc,
            clustered=True,
            n_cases=n_cases,
        )

    if n_pos < 2 or n_neg < 2:
        reason = "insufficient_positives" if n_pos < 2 else "insufficient_negatives"
        return DiscriminationResult(
            auroc=not_estimable(reason, est=point, n_pos=n_pos, n_neg=n_neg, ci_level=level),
            auroc_secondary=None,
            se=None,
            n_pos=n_pos,
            n_neg=n_neg,
            roc=roc,
        )

    _, var = delong_variance(scores, pos)
    se = math.sqrt(max(var, 0.0))

    flags: list[str] = []
    if min(n_pos, n_neg) < SMALL_CLASS:
        flags.append("very_low_precision")
    w_lo, w_hi = wald_ci(point, se, level)
    wald_out_of_range = w_lo < 0.0 or w_hi > 1.0

    if not 0.0 < point < 1.0 or se == 0.0:
        # A degenerate AUC (0 or 1) has no logit; the Wald interval is also useless.
        return DiscriminationResult(
            auroc=not_estimable(
                "boundary_estimate",
                est=point,
                n_pos=n_pos,
                n_neg=n_neg,
                ci_level=level,
                flags=flags,
            ),
            auroc_secondary=None,
            se=se,
            n_pos=n_pos,
            n_neg=n_neg,
            roc=roc,
        )

    l_lo, l_hi = logit_ci(point, se, level)
    logit_number = Number(
        est=point,
        ci_lo=l_lo,
        ci_hi=l_hi,
        ci_level=level,
        method="delong_logit",
        n_pos=n_pos,
        n_neg=n_neg,
        flags=list(flags),
    )
    wald_number = Number(
        est=point,
        ci_lo=max(0.0, w_lo),
        ci_hi=min(1.0, w_hi),
        ci_level=level,
        method="delong_wald",
        n_pos=n_pos,
        n_neg=n_neg,
        flags=[*flags, "wald_interval_exceeds_unit_range"] if wald_out_of_range else list(flags),
    )
    logit_primary = point > 0.9 or min(n_pos, n_neg) < LOGIT_PRIMARY_CLASS
    primary, secondary = (
        (logit_number, wald_number) if logit_primary else (wald_number, logit_number)
    )
    return DiscriminationResult(
        auroc=primary,
        auroc_secondary=secondary,
        se=se,
        n_pos=n_pos,
        n_neg=n_neg,
        roc=roc,
    )


# ----------------------------------------------------------------------- paired DeLong


@dataclass
class PairedDeLong:
    """Two correlated ROC curves on the same cases."""

    auroc_a: Number
    auroc_b: Number
    difference: Number
    variance_difference: float
    z: float
    p_value: float
    method: str = "paired_delong"


def _two_sided_p(z: float) -> float:
    """Two-sided normal tail. stdlib only."""
    return float(math.erfc(abs(z) / math.sqrt(2.0)))


def paired_delong(
    scores_a: np.ndarray,
    scores_b: np.ndarray,
    positives: np.ndarray,
    level: float = 0.95,
) -> PairedDeLong:
    """DeLong's test for AUC(A) - AUC(B) on the same cases.

    The two AUCs share structural components, so the covariance term is real and
    ``Var(A - B) = S_aa + S_bb - 2 S_ab`` is (usually much) smaller than the
    unpaired sum. The difference Number carries a Wald interval on that variance;
    the AUCs themselves carry their logit intervals.

    **Rows are assumed independent and nothing here checks that.** This function has
    **no clustering parameter**: no caller can tell it that its rows are lesions of two
    hundred patients, and it reaches none of the X2 routing in ``stats.bootstrap``. On
    clustered rows the paired variance is understated the same way the unpaired one is,
    and the interval comes back with no flag and no companion refusal. Nothing in ``src``
    calls this yet; the day-5 caller must not call it on a clustered table until a
    cluster bootstrap of the difference exists (round-7 fresh attack, 2026-09-10).
    """
    a = np.asarray(scores_a, dtype=np.float64)
    b = np.asarray(scores_b, dtype=np.float64)
    pos = np.asarray(positives, dtype=bool)
    if a.shape != b.shape:
        raise ValueError("paired DeLong needs the same cases scored by both classifiers")
    aucs, s = delong_covariance(np.vstack([a, b]), pos)
    var_diff = float(s[0, 0] + s[1, 1] - 2.0 * s[0, 1])
    diff = float(aucs[0] - aucs[1])
    se = math.sqrt(max(var_diff, 0.0))
    z = diff / se if se > 0 else 0.0
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    zq = z_for(level)
    difference = (
        Number(
            est=diff,
            ci_lo=diff - zq * se,
            ci_hi=diff + zq * se,
            ci_level=level,
            method="delong_wald",
            n_pos=n_pos,
            n_neg=n_neg,
        )
        if se > 0
        else not_estimable("boundary_estimate", est=diff, n_pos=n_pos, n_neg=n_neg, ci_level=level)
    )
    return PairedDeLong(
        auroc_a=auroc_number(a, pos, level).auroc,
        auroc_b=auroc_number(b, pos, level).auroc,
        difference=difference,
        variance_difference=var_diff,
        z=float(z),
        p_value=_two_sided_p(z),
    )


# --------------------------------------------------------------------- unpaired DeLong


@dataclass
class UnpairedDeLong:
    """Two ROC curves on **disjoint** samples (a subgroup and its complement)."""

    auroc_a: float
    auroc_b: float
    difference: Number
    variance_a: float
    variance_b: float
    variance_difference: float
    z: float
    p_value: float
    method: str = "unpaired_delong"


def unpaired_delong(
    scores_a: np.ndarray,
    positives_a: np.ndarray,
    scores_b: np.ndarray,
    positives_b: np.ndarray,
    level: float = 0.95,
) -> UnpairedDeLong:
    """AUC(A) - AUC(B) for two ROC curves estimated on **independent** samples.

    DeLong, DeLong and Clarke-Pearson (1988, Biometrics 44:837-845) give the
    covariance matrix of a vector of AUC estimates from the structural components
    ``V10`` (one per positive) and ``V01`` (one per negative): ``S = S10/m + S01/n``.
    When the two curves are estimated on disjoint samples no case contributes a
    component to both, so the cross term is zero and the variance of the difference is
    the plain sum ``Var(A) + Var(B)`` - each computed by :func:`delong_variance`, the
    day-3 code that R2 section 9 F3 pins at ``SE = 0.1549`` and that the day-3 tests
    check against a direct O(n*m) computation of the same components. The interval is
    Wald on the difference, ``diff +/- z * sqrt(Var(A) + Var(B))``; ``z`` and the
    two-sided p-value are returned as *detail* and are never a verdict about the
    subgroup (R2 section 3.4: "never let a p-value clear a subgroup").

    **Checked against**: (a) the day-3 :func:`delong_variance` on each arm separately,
    so the sum is exactly the sum of two oracled quantities; (b) in
    ``tests/test_subgroups.py`` the difference and its variance are recomputed from the
    placement-value definition of ``V10``/``V01`` written out in the test, and the z
    against ``scipy.stats.norm`` for the tail. No R (pROC) capture exists for the
    unpaired case; pROC's ``roc.test(paired = FALSE)`` is the natural external oracle
    and is **[unverified - not captured in this build environment]**.

    Rows on each side are assumed independent **and independent of the other side**.
    This function has no clustering parameter and inspects no case column; the caller
    (``stats.subgroups``) routes clustered data away from it and refuses the
    difference outright when a case has rows on both sides.
    """
    a = np.asarray(scores_a, dtype=np.float64)
    b = np.asarray(scores_b, dtype=np.float64)
    pa = np.asarray(positives_a, dtype=bool)
    pb = np.asarray(positives_b, dtype=bool)
    auc_a, var_a = delong_variance(a, pa)
    auc_b, var_b = delong_variance(b, pb)
    var_diff = float(var_a + var_b)
    diff = float(auc_a - auc_b)
    se = math.sqrt(max(var_diff, 0.0))
    z = diff / se if se > 0 else 0.0
    counts = {
        "n_pos": int(pa.sum()) + int(pb.sum()),
        "n_neg": int((~pa).sum()) + int((~pb).sum()),
    }
    zq = z_for(level)
    difference = (
        Number(
            est=diff,
            ci_lo=diff - zq * se,
            ci_hi=diff + zq * se,
            ci_level=level,
            method="delong_wald",
            **counts,
        )
        if se > 0
        else not_estimable("boundary_estimate", est=diff, ci_level=level, **counts)
    )
    return UnpairedDeLong(
        auroc_a=float(auc_a),
        auroc_b=float(auc_b),
        difference=difference,
        variance_a=float(var_a),
        variance_b=float(var_b),
        variance_difference=var_diff,
        z=float(z),
        p_value=_two_sided_p(z),
    )


# ------------------------------------------------------------------------- ROC arrays


def roc_curve(scores: np.ndarray, positives: np.ndarray) -> list[list[float]]:
    """ROC coordinates as ``[[fpr, tpr, threshold], ...]``, ordered by falling threshold.

    One point per distinct score value, plus the origin at ``threshold = +inf``.
    A prediction is positive when ``score >= threshold`` (the engine's default rule;
    the declared rule is applied by :func:`locate_operating_points`).
    """
    scores = np.asarray(scores, dtype=np.float64)
    pos = np.asarray(positives, dtype=bool)
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return []
    order = np.argsort(-scores, kind="mergesort")
    s = scores[order]
    p = pos[order]
    tp = np.cumsum(p)
    fp = np.cumsum(~p)
    # Keep only the last index of each run of equal scores.
    last = np.r_[np.flatnonzero(np.diff(s) != 0), s.shape[0] - 1]
    out = [[0.0, 0.0, float("inf")]]
    for i in last:
        out.append([float(fp[i]) / n_neg, float(tp[i]) / n_pos, float(s[i])])
    return out


def locate_operating_points(
    scores: np.ndarray,
    positives: np.ndarray,
    operating_points: list,
) -> list[dict]:
    """Mark each declared operating point on the ROC curve (D1 section 4.2)."""
    scores = np.asarray(scores, dtype=np.float64)
    pos = np.asarray(positives, dtype=bool)
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    marks: list[dict] = []
    for op in operating_points:
        pred = np.array([op.is_positive(float(v)) for v in scores], dtype=bool)
        marks.append(
            {
                "id": op.id,
                "threshold": float(op.threshold),
                "fpr": float(np.count_nonzero(~pos & pred)) / n_neg if n_neg else 0.0,
                "tpr": float(np.count_nonzero(pos & pred)) / n_pos if n_pos else 0.0,
            }
        )
    return marks
