"""``stats.proportions`` - binomial proportions, 2x2 tables and their differences.

Methods (D1 section 3.1, R2 sections 1.2 and 9):

* **Wilson score** interval, no continuity correction - the default for every
  proportion (FDA 2007 first choice).
* **Wilson score with continuity correction** - available, never the default
  (over-conservative).
* **Clopper-Pearson exact** - shown *alongside* Wilson at 0/n and n/n, where Wald
  is degenerate. Closed form at the boundaries (no scipy); ``scipy.stats.beta.ppf``
  for 0 < k < n, and an explicit ``scipy_unavailable`` reason if scipy is absent.
* **Wald** - computed for tests only. It is never returned as a ``Number`` and is
  never rendered (R2: 0/20 Wald = (0, 0)).
* **Newcombe 1998 method 10** (square-and-add of two Wilson intervals) and
  **method 11** (the same with continuity-corrected Wilson intervals) for the
  difference between two *independent* proportions.
* **Newcombe paired** - the score-based interval for the difference between two
  proportions on the same cases, with the continuity-corrected correlation term.
* 2x2 derived metrics, PPA/NPA routing, both-way indeterminate tables, and
  PPV/NPV at a declared prevalence with a logit-scale delta interval.

scipy is imported *inside* the one function that needs it, so ``import proofpack``
still works with scipy absent (day-1 CI job).

References
----------
Newcombe RG. "Two-sided confidence intervals for the single proportion: comparison
of seven methods." Statist Med 1998;17:857-872.
Newcombe RG. "Interval estimation for the difference between independent
proportions: comparison of eleven methods." Statist Med 1998;17:873-890.
Newcombe RG. "Improved confidence intervals for the difference between binomial
proportions based on paired data." Statist Med 1998;17:2635-2650.
Mercaldo ND, Lau KF, Zhou XH. "Confidence intervals for predictive values..."
Statist Med 2007;26:2170-2183. **[unverified - not fetched this session; the
logit-scale form used below is derived from first principles in ``ppv_at_prevalence``
and is testable without the paper.]**
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np

from proofpack.stats.number import Number, not_estimable

_ND = NormalDist()


def z_for(level: float = 0.95) -> float:
    """Two-sided normal quantile. stdlib only - no scipy on the runtime path."""
    if not 0.0 < level < 1.0:
        raise ValueError("level must be in (0, 1)")
    return _ND.inv_cdf(1.0 - (1.0 - level) / 2.0)


# --------------------------------------------------------------------- single proportion


def wilson_bounds(
    k: int, n: int, level: float = 0.95, continuity: bool = False
) -> tuple[float, float]:
    """Wilson score interval bounds for ``k`` successes in ``n`` trials.

    ``continuity=True`` gives Newcombe 1998 (seven methods) method 4. The
    uncorrected form is method 3 and is ProofPack's default.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= k <= n:
        raise ValueError("k must lie in [0, n]")
    z = z_for(level)
    p = k / n
    z2 = z * z
    denom = 2.0 * (n + z2)
    if not continuity:
        centre = 2.0 * n * p + z2
        rad = z * math.sqrt(z2 + 4.0 * n * p * (1.0 - p))
        return (
            _clip((centre - rad) / denom),
            _clip((centre + rad) / denom),
        )
    # Continuity-corrected form (Newcombe 1998a method 4): the two roots are
    # computed separately and clamped so the interval never inverts at 0/n, n/n.
    if k == 0:
        lo = 0.0
    else:
        inner = z2 - 1.0 / n + 4.0 * n * p * (1.0 - p) + (4.0 * p - 2.0)
        lo = (2.0 * n * p + z2 - 1.0 - z * math.sqrt(max(inner, 0.0))) / denom
    if k == n:
        hi = 1.0
    else:
        inner = z2 - 1.0 / n + 4.0 * n * p * (1.0 - p) - (4.0 * p - 2.0)
        hi = (2.0 * n * p + z2 + 1.0 + z * math.sqrt(max(inner, 0.0))) / denom
    return (_clip(lo), _clip(hi))


def _clip(x: float) -> float:
    return min(1.0, max(0.0, x))


def wald_bounds(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Wald interval. **Test-only.** Degenerate at 0/n and n/n; never rendered."""
    p = k / n
    z = z_for(level)
    half = z * math.sqrt(p * (1.0 - p) / n)
    return (_clip(p - half), _clip(p + half))


def clopper_pearson_bounds(k: int, n: int, level: float = 0.95) -> tuple[float, float] | None:
    """Clopper-Pearson exact bounds, or ``None`` when scipy is needed and absent.

    At the boundaries the exact interval is closed form and needs no library:
    ``k = 0`` gives ``(0, 1 - (alpha/2)**(1/n))`` and ``k = n`` the mirror image.
    Those are exactly the cases D1 asks us to show alongside Wilson, so the
    boundary behaviour never depends on an optional dependency.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    alpha = 1.0 - level
    if k == 0:
        return (0.0, 1.0 - (alpha / 2.0) ** (1.0 / n))
    if k == n:
        return ((alpha / 2.0) ** (1.0 / n), 1.0)
    try:
        from scipy.stats import beta  # noqa: PLC0415  (optional dependency, imported lazily)
    except ImportError:
        return None
    lo = float(beta.ppf(alpha / 2.0, k, n - k + 1))
    hi = float(beta.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return (_clip(lo), _clip(hi))


def proportion(
    k: int, n: int, level: float = 0.95, continuity: bool = False, flags: list[str] | None = None
) -> Number:
    """The default proportion Number: point estimate with a Wilson interval."""
    if n <= 0:
        return not_estimable("zero_denominator", n=0, k=int(k), ci_level=level)
    lo, hi = wilson_bounds(k, n, level, continuity=continuity)
    fl = list(flags or [])
    if continuity:
        fl.append("continuity_corrected")
    num = Number(
        est=k / n,
        ci_lo=lo,
        ci_hi=hi,
        ci_level=level,
        method="wilson_cc" if continuity else "wilson",
        n=int(n),
        k=int(k),
        flags=fl,
    )
    return num.with_precision_flags()


def proportion_exact_alternative(k: int, n: int, level: float = 0.95) -> Number | None:
    """Clopper-Pearson shown *alongside* Wilson - returned only at 0/n and n/n.

    D1: "Clopper-Pearson shown for 0/n and n/n". Elsewhere it is available through
    :func:`clopper_pearson_bounds` for tests and oracles but is not part of the
    rendered document, so this returns ``None``.
    """
    if n <= 0 or not (k == 0 or k == n):
        return None
    bounds = clopper_pearson_bounds(k, n, level)
    if bounds is None:
        return not_estimable(
            "scipy_unavailable", est=k / n, n=int(n), k=int(k), ci_level=level
        )  # pragma: no cover - boundary case is closed form, so unreachable in practice
    lo, hi = bounds
    return Number(
        est=k / n,
        ci_lo=lo,
        ci_hi=hi,
        ci_level=level,
        method="clopper_pearson",
        n=int(n),
        k=int(k),
        flags=["shown_alongside_wilson_at_boundary"],
    )


# ------------------------------------------------------------- differences of proportions


def newcombe10_bounds(
    k1: int, n1: int, k2: int, n2: int, level: float = 0.95
) -> tuple[float, float]:
    """Newcombe 1998 (eleven methods) **method 10**: square-and-add Wilson bounds.

    For independent samples, with ``d = p1 - p2``::

        lower = d - sqrt((p1 - l1)^2 + (u2 - p2)^2)
        upper = d + sqrt((u1 - p1)^2 + (p2 - l2)^2)

    where (l, u) are the uncorrected Wilson intervals for each proportion.
    """
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson_bounds(k1, n1, level)
    l2, u2 = wilson_bounds(k2, n2, level)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (max(-1.0, lo), min(1.0, hi))


def newcombe11_bounds(
    k1: int, n1: int, k2: int, n2: int, level: float = 0.95
) -> tuple[float, float]:
    """Newcombe 1998 **method 11**: method 10 built from continuity-corrected Wilson."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson_bounds(k1, n1, level, continuity=True)
    l2, u2 = wilson_bounds(k2, n2, level, continuity=True)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (max(-1.0, lo), min(1.0, hi))


def difference_unpaired(
    k1: int, n1: int, k2: int, n2: int, level: float = 0.95, continuity: bool = False
) -> Number:
    """Difference of two independent proportions, Newcombe method 10 (or 11)."""
    if n1 <= 0 or n2 <= 0:
        return not_estimable("zero_denominator", ci_level=level)
    if continuity:
        lo, hi = newcombe11_bounds(k1, n1, k2, n2, level)
    else:
        lo, hi = newcombe10_bounds(k1, n1, k2, n2, level)
    return Number(
        est=k1 / n1 - k2 / n2,
        ci_lo=lo,
        ci_hi=hi,
        ci_level=level,
        method="newcombe11" if continuity else "newcombe10",
        n=int(min(n1, n2)),
        flags=["continuity_corrected"] if continuity else [],
    )


def newcombe_paired_bounds(
    e: int, f: int, g: int, h: int, level: float = 0.95
) -> tuple[float, float]:
    """Newcombe 1998 (paired) **method 10**: score interval with a corrected phi.

    The paired 2x2 counts are ``e`` (both positive), ``f`` (first only), ``g``
    (second only), ``h`` (both negative); ``p1 = (e+f)/n``, ``p2 = (e+g)/n``.
    Method 10 is the square-and-add of the two Wilson intervals with a covariance
    term ``phi``, whose numerator is continuity-corrected to
    ``max(eh - fg - n/2, 0)`` when ``eh > fg``.
    """
    n = e + f + g + h
    if n <= 0:
        raise ValueError("empty paired table")
    p1 = (e + f) / n
    p2 = (e + g) / n
    d = p1 - p2
    l1, u1 = wilson_bounds(e + f, n, level)
    l2, u2 = wilson_bounds(e + g, n, level)
    phi = _paired_phi(e, f, g, h)
    lo = d - math.sqrt(
        max((p1 - l1) ** 2 - 2.0 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2, 0.0)
    )
    hi = d + math.sqrt(
        max((u1 - p1) ** 2 - 2.0 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2, 0.0)
    )
    return (max(-1.0, lo), min(1.0, hi))


def _paired_phi(e: int, f: int, g: int, h: int) -> float:
    """Estimated correlation between the two paired indicators (Newcombe 1998c)."""
    n = e + f + g + h
    a = (e + f) * (g + h) * (e + g) * (f + h)
    if a <= 0:
        return 0.0
    num = e * h - f * g
    if num > 0:  # continuity correction, method 10
        num = max(e * h - f * g - n / 2.0, 0.0)
    return float(num / math.sqrt(a))


def difference_paired(e: int, f: int, g: int, h: int, level: float = 0.95) -> Number:
    """Difference of two proportions measured on the same cases (Newcombe paired)."""
    n = e + f + g + h
    if n <= 0:
        return not_estimable("zero_denominator", ci_level=level)
    lo, hi = newcombe_paired_bounds(e, f, g, h, level)
    return Number(
        est=(f - g) / n,
        ci_lo=lo,
        ci_hi=hi,
        ci_level=level,
        method="newcombe_paired",
        n=int(n),
    )


# ------------------------------------------------------------------------ 2x2 tables


@dataclass(frozen=True)
class Table2x2:
    """Counts against the reference standard at one operating point."""

    tp: int
    fn: int
    fp: int
    tn: int

    @property
    def n_pos(self) -> int:
        return self.tp + self.fn

    @property
    def n_neg(self) -> int:
        return self.fp + self.tn

    @property
    def n(self) -> int:
        return self.tp + self.fn + self.fp + self.tn

    def as_dict(self) -> dict[str, int]:
        return {"tp": self.tp, "fn": self.fn, "fp": self.fp, "tn": self.tn}


#: Metric ids used when the reference standard is a true reference standard, and
#: the ids used when it is a non-reference *comparator* (FDA 2007: report PPA/NPA,
#: never "sensitivity"/"specificity").
_SE_ID = {"reference": "sensitivity", "comparator": "ppa"}
_SP_ID = {"reference": "specificity", "comparator": "npa"}


def sensitivity_id(reference_standard_type: str) -> str:
    return _SE_ID.get(reference_standard_type, "sensitivity")


def specificity_id(reference_standard_type: str) -> str:
    return _SP_ID.get(reference_standard_type, "specificity")


def _ratio_log_delta(est: float, se_log: float, level: float, n: int, invalid: bool) -> Number:
    if invalid or not math.isfinite(se_log) or not math.isfinite(est) or est <= 0.0:
        return not_estimable("zero_cell_log_undefined", est=None, n=n, ci_level=level)
    z = z_for(level)
    lo = est * math.exp(-z * se_log)
    hi = est * math.exp(z * se_log)
    return Number(est=est, ci_lo=lo, ci_hi=hi, ci_level=level, method="log_delta", n=n)


def two_by_two_metrics(
    t: Table2x2, level: float = 0.95, reference_standard_type: str = "reference"
) -> dict[str, Number]:
    """Every metric derivable from a 2x2, each with its method name and n.

    Proportions get Wilson intervals. Youden J and balanced accuracy are functions
    of the difference between two *independent* proportions (Se and 1 - Sp, on
    disjoint row sets) and so carry Newcombe-10 intervals. LR+, LR- and DOR use the
    log-scale delta method and become ``zero_cell_log_undefined`` at a zero cell.
    F1 and MCC have no standard closed-form interval: they are emitted with an
    explicit ``analytic_ci_unavailable`` reason and the ``ci_pending_bootstrap``
    flag, never with a made-up interval.

    **Rows are assumed independent and nothing here checks that.** A 2x2 table is four
    counts: by the time the rows reach this function the case column is gone, and there
    is **no clustering parameter** to restore it. Every Wilson and Newcombe interval below
    is therefore computed as though each row were its own patient. The X2 routing lives in
    ``stats.bootstrap.proportion_ci``, which takes the indicator vector and the
    ``cluster_ids`` beside it; this function reaches none of it. The caller that reads the
    customer's table has to choose between the two (round-7 fresh attack, 2026-09-10).
    """
    tp, fn, fp, tn = t.tp, t.fn, t.fp, t.tn
    n_pos, n_neg, n = t.n_pos, t.n_neg, t.n
    out: dict[str, Number] = {}

    se_key, sp_key = (
        sensitivity_id(reference_standard_type),
        specificity_id(reference_standard_type),
    )
    out[se_key] = (
        proportion(tp, n_pos, level)
        if n_pos > 0
        else not_estimable("zero_denominator", n=0, ci_level=level)
    )
    out[sp_key] = (
        proportion(tn, n_neg, level)
        if n_neg > 0
        else not_estimable("zero_denominator", n=0, ci_level=level)
    )
    out["ppv"] = (
        proportion(tp, tp + fp, level)
        if (tp + fp) > 0
        else not_estimable("zero_denominator", n=0, ci_level=level)
    )
    out["npv"] = (
        proportion(tn, tn + fn, level)
        if (tn + fn) > 0
        else not_estimable("zero_denominator", n=0, ci_level=level)
    )
    out["accuracy"] = (
        proportion(tp + tn, n, level)
        if n > 0
        else not_estimable("zero_denominator", n=0, ci_level=level)
    )
    out["prevalence"] = (
        proportion(n_pos, n, level)
        if n > 0
        else not_estimable("zero_denominator", n=0, ci_level=level)
    )

    if n_pos > 0 and n_neg > 0:
        # J = Se - FPR: difference of two independent proportions.
        j = difference_unpaired(tp, n_pos, fp, n_neg, level)
        out["youden"] = Number(
            est=j.est,
            ci_lo=j.ci_lo,
            ci_hi=j.ci_hi,
            ci_level=level,
            method="newcombe10",
            n=n,
        )
        out["balanced_accuracy"] = Number(
            est=(j.est + 1.0) / 2.0,  # type: ignore[operator]
            ci_lo=(j.ci_lo + 1.0) / 2.0,  # type: ignore[operator]
            ci_hi=(j.ci_hi + 1.0) / 2.0,  # type: ignore[operator]
            ci_level=level,
            method="newcombe10",
            n=n,
        )
    else:
        out["youden"] = not_estimable("single_class", n=n, ci_level=level)
        out["balanced_accuracy"] = not_estimable("single_class", n=n, ci_level=level)

    se = tp / n_pos if n_pos else float("nan")
    sp = tn / n_neg if n_neg else float("nan")
    zero_cell = tp == 0 or fn == 0 or fp == 0 or tn == 0
    out["lr_pos"] = _ratio_log_delta(
        se / (1.0 - sp) if n_pos and n_neg and sp < 1.0 else float("nan"),
        math.sqrt((1.0 - se) / (se * n_pos) + sp / ((1.0 - sp) * n_neg))
        if n_pos and n_neg and 0.0 < se and sp < 1.0
        else float("nan"),
        level,
        n,
        invalid=(fp == 0 or tp == 0 or n_pos == 0 or n_neg == 0),
    )
    out["lr_neg"] = _ratio_log_delta(
        (1.0 - se) / sp if n_pos and n_neg and sp > 0.0 else float("nan"),
        math.sqrt(se / ((1.0 - se) * n_pos) + (1.0 - sp) / (sp * n_neg))
        if n_pos and n_neg and se < 1.0 and sp > 0.0
        else float("nan"),
        level,
        n,
        invalid=(fn == 0 or tn == 0 or n_pos == 0 or n_neg == 0),
    )
    out["dor"] = _ratio_log_delta(
        (tp * tn) / (fp * fn) if not zero_cell else float("nan"),
        math.sqrt(1.0 / tp + 1.0 / fn + 1.0 / fp + 1.0 / tn) if not zero_cell else float("nan"),
        level,
        n,
        invalid=zero_cell,
    )

    f1_den = 2 * tp + fp + fn
    out["f1"] = not_estimable(
        "analytic_ci_unavailable",
        est=(2 * tp / f1_den) if f1_den > 0 else None,
        n=n,
        ci_level=level,
        flags=["ci_pending_bootstrap"],
    )
    mcc_den = math.sqrt(float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)))
    out["mcc"] = not_estimable(
        "analytic_ci_unavailable",
        est=((tp * tn - fp * fn) / mcc_den) if mcc_den > 0 else None,
        n=n,
        ci_level=level,
        flags=["ci_pending_bootstrap"],
    )
    return out


# ------------------------------------------------------- PPV / NPV at declared prevalence


def ppv_at_prevalence(t: Table2x2, prevalence: float, level: float = 0.95) -> Number:
    """Bayes PPV at a declared prevalence, with a logit-scale delta interval.

    ``PPV(pi) = Se pi / (Se pi + (1 - Sp)(1 - pi))``, so

        ``logit PPV = logit(pi) + log Se - log(1 - Sp)``

    and, since Se and (1 - Sp) come from disjoint row sets,

        ``Var(logit PPV) = (1 - Se)/(Se n1) + Sp/((1 - Sp) n0)``

    which is the same variance as ``log LR+``. The interval is back-transformed
    with the logistic. This is the Mercaldo-style logit interval **[unverified
    against the 2007 paper - derived here instead, and tested against the
    identity PPV(study prevalence) == TP/(TP+FP)]**. At Se = 0 or Sp = 1 the
    log terms are undefined and the Number carries ``zero_cell_logit_undefined``.
    """
    return _predictive_at_prevalence(t, prevalence, level, positive=True)


def npv_at_prevalence(t: Table2x2, prevalence: float, level: float = 0.95) -> Number:
    """Bayes NPV at a declared prevalence, logit-scale delta interval (see PPV)."""
    return _predictive_at_prevalence(t, prevalence, level, positive=False)


def _predictive_at_prevalence(t: Table2x2, pi: float, level: float, positive: bool) -> Number:
    n_pos, n_neg = t.n_pos, t.n_neg
    if n_pos == 0 or n_neg == 0:
        return not_estimable("single_class", n=t.n, ci_level=level)
    if not 0.0 < pi < 1.0:
        return not_estimable("boundary_estimate", n=t.n, ci_level=level)
    se = t.tp / n_pos
    sp = t.tn / n_neg
    if positive:
        num = se * pi
        den = se * pi + (1.0 - sp) * (1.0 - pi)
        est = num / den if den > 0 else None
        undefined = se <= 0.0 or sp >= 1.0
        var = (
            (1.0 - se) / (se * n_pos) + sp / ((1.0 - sp) * n_neg) if not undefined else float("nan")
        )
    else:
        num = sp * (1.0 - pi)
        den = sp * (1.0 - pi) + (1.0 - se) * pi
        est = num / den if den > 0 else None
        undefined = sp <= 0.0 or se >= 1.0
        var = (
            (1.0 - sp) / (sp * n_neg) + se / ((1.0 - se) * n_pos) if not undefined else float("nan")
        )
    if undefined or est is None or not (0.0 < est < 1.0) or not math.isfinite(var):
        return not_estimable("zero_cell_logit_undefined", est=est, n=t.n, ci_level=level)
    z = z_for(level)
    eta = math.log(est / (1.0 - est))
    half = z * math.sqrt(var)
    lo = 1.0 / (1.0 + math.exp(-(eta - half)))
    hi = 1.0 / (1.0 + math.exp(-(eta + half)))
    return Number(
        est=est,
        ci_lo=lo,
        ci_hi=hi,
        ci_level=level,
        method="logit_delta",
        n=t.n,
    )


# --------------------------------------------------------------- indeterminate handling


@dataclass(frozen=True)
class BothWayTables:
    """The two 2x2 tables an indeterminate test result forces us to show (FDA 2007).

    ``as_positive`` counts every indeterminate *test result* as test-positive;
    ``as_negative`` counts it as test-negative. Both are rendered; neither is a
    default. ``n_indeterminate_*`` are the reference-standard splits.
    """

    as_positive: Table2x2
    as_negative: Table2x2
    n_indeterminate_pos: int
    n_indeterminate_neg: int


def indeterminate_both_ways(
    t: Table2x2, indeterminate_ref_pos: int, indeterminate_ref_neg: int
) -> BothWayTables:
    """Build the as-positive and as-negative tables from a determinate 2x2."""
    ip, ineg = int(indeterminate_ref_pos), int(indeterminate_ref_neg)
    if ip < 0 or ineg < 0:
        raise ValueError("indeterminate counts must be non-negative")
    return BothWayTables(
        as_positive=Table2x2(tp=t.tp + ip, fn=t.fn, fp=t.fp + ineg, tn=t.tn),
        as_negative=Table2x2(tp=t.tp, fn=t.fn + ip, fp=t.fp, tn=t.tn + ineg),
        n_indeterminate_pos=ip,
        n_indeterminate_neg=ineg,
    )


# ------------------------------------------------------------------- table -> counts


def table_2x2_from_arrays(
    y_true: np.ndarray,
    predicted_positive: np.ndarray,
    positive_label: str,
) -> Table2x2:
    """Counts from aligned arrays: ``y_true`` labels and a boolean prediction mask."""
    yt = np.asarray([str(v) for v in np.asarray(y_true).tolist()])
    pred = np.asarray(predicted_positive, dtype=bool)
    if yt.shape[0] != pred.shape[0]:
        raise ValueError("y_true and predicted_positive must align")
    is_pos = yt == str(positive_label)
    return Table2x2(
        tp=int(np.count_nonzero(is_pos & pred)),
        fn=int(np.count_nonzero(is_pos & ~pred)),
        fp=int(np.count_nonzero(~is_pos & pred)),
        tn=int(np.count_nonzero(~is_pos & ~pred)),
    )
