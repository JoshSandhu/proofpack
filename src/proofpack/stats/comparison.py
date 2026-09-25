"""``stats.comparison`` - version N against version N-1 (build day 10, E10).

D1 section 3.1's row: a paired join on ``row_id`` (gate H12 decides paired or not; the
unpaired path is reached only through ``--allow-unpaired``); for every declared operating
point the two-by-two of each version and the discordant counts ``b`` (prior correct, new
wrong) and ``c`` (new correct, prior wrong); McNemar; the paired differences of the
conditioned proportions with the Newcombe paired interval; the paired DeLong AUROC
difference on independent rows or the cluster-bootstrap difference on clustered rows; the
paired bootstrap differences of the Brier score and of the calibration slope for a
probability score; per-subgroup paired differences; the unpaired fallback with every
Number labelled ``not like-for-like``. Every quantity is a
:class:`~proofpack.stats.number.Number` (estimate, interval, method, n) or carries a typed
reason; the margin a difference is compared with lives in the customer's ``criteria.yaml``
and nowhere here (:mod:`proofpack.criteria` reads the block).

Methods, each written here or reused from the day-2/3/4 modules
-----------------------------------------------------------------

* **McNemar** (:func:`mcnemar`): on the discordant counts of *accuracy* at one operating
  point. Exact when ``b + c < EXACT_BELOW`` (25): the two-sided binomial test on
  ``min(b, c)`` with ``n = b + c`` and ``p = 1/2``, ``p = min(1, 2 * P(X <= min(b, c)))``,
  which is what ``statsmodels.stats.contingency_tables.mcnemar(exact=True)`` computes;
  ``b = c = 0`` gives ``p = 1`` and no statistic. Otherwise the continuity-corrected
  chi-square ``(|b - c| - 1)^2 / (b + c)`` on one degree of freedom, ``p = erfc(sqrt(
  statistic / 2))`` (``mcnemar(exact=False, correction=True)``). The ``method`` field
  names which (``exact_mcnemar`` / ``cc_mcnemar``, D1 section 4.1's enum).
* **Paired proportion difference** (:func:`paired_proportion_difference`): the four
  paired cells ``e`` (both correct), ``f`` (new correct only), ``g`` (prior correct only),
  ``h`` (neither) through :func:`proofpack.stats.proportions.difference_paired`, the
  Newcombe (1998, paired) method 10 score interval already in ``proportions.py`` since
  build day 2 - **not** the unpaired method 10 beside it. The estimate is ``(f - g) / n``
  = new minus prior; ``n`` is the number of pairs the proportion is conditioned on (the
  reference-positive pairs for sensitivity, every pair for accuracy). The formula and its
  source status are stated in ``tests/test_e10_comparison.py``.
* **Paired AUROC difference**: :func:`proofpack.stats.discrimination.paired_delong` on
  independent rows (Sun and Xu structural components of the two score vectors on the same
  cases, covariance included: ``Var(A - B) = S_aa + S_bb - 2 S_ab``); on a clustered plan
  the cluster bootstrap of the difference through :mod:`proofpack.stats.bootstrap`'s
  resampler (cases resampled within outcome class, every row of a drawn case kept; B and
  the seed from the declarations, the cell key recorded), with the DeLong refusal carried
  beside it as the ``analytic`` companion (DEC-09: ``clustered_data_analytic_ci_invalid``).
  The paired proportions take the same route under clustering (the Newcombe paired
  interval assumes independent pairs), with ``newcombe_refused_clustered`` on the
  rendered Number.
* **Brier and calibration-slope differences**: the paired bootstrap of ``Brier_new -
  Brier_prior`` and of ``slope_new - slope_prior`` (each slope the joint IRLS fit of
  :mod:`proofpack.stats.calibration` on the resampled pairs), stratified by outcome on
  independent rows and clustered by case otherwise; on a score that is not a declared
  probability both carry the typed reason ``score_not_probability`` (DEC-36's shape: the
  reason rides beside the null in ``calibration_suppressed_reason``).
* **Unpaired fallback** (H12 with ``--allow-unpaired``): the difference of two independent
  proportions by the unpaired Newcombe method 10 (``proportions.difference_unpaired``)
  and the unpaired DeLong difference (``discrimination.unpaired_delong``), every Number
  carrying the method ``<method>_not_like_for_like`` and the flag ``not_like_for_like``;
  the Brier and slope differences are refused with ``unpaired_not_like_for_like``; on
  clustered rows the analytic methods are refused with DEC-09's reason. No margin, no
  status: the criteria engine returns ``not_assessable`` / ``not_like_for_like`` for
  every ``paired_difference_vs_prior`` criterion on an unpaired comparison.

Nothing here imports jinja2, statsmodels or scikit-learn (``tests/test_e10_comparison.py::
test_the_comparison_module_imports_no_oracle_or_renderer``).
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from proofpack.stats.bootstrap import (
    DEFAULT_LEVEL,
    BootstrapPolicy,
    ClusterPlan,
    Resampler,
    bootstrap_percentile,
    clustered_by_case,
    stratified_by_outcome,
)
from proofpack.stats.calibration import CLIP_EPS, _fit_joint
from proofpack.stats.discrimination import (
    auroc_mann_whitney,
    paired_delong,
    unpaired_delong,
)
from proofpack.stats.number import Number, not_estimable
from proofpack.stats.proportions import difference_paired, difference_unpaired

__all__ = [
    "EXACT_BELOW",
    "Join",
    "McNemar",
    "VersionArrays",
    "compare_versions",
    "mcnemar",
    "paired_join",
    "paired_proportion_difference",
]

#: Below this many discordant pairs the McNemar test is exact (R2 section 6, D1 section
#: 3.1: "McNemar exact when b + c < 25 else continuity-corrected chi-square").
EXACT_BELOW = 25
#: The label every unpaired Number carries (D1 section 3.1; D4 section 5.7's caption).
NOT_LIKE_FOR_LIKE = "not like-for-like"
#: The three conditioned proportions compared per operating point, in the vocabulary of
#: ``stats.subgroups._conditioned`` (``se`` / ``sp`` are renamed to the reference-standard
#: ids by the caller's keys). PPV and NPV are not paired proportions (their denominators
#: differ between the versions) and are not compared.
PROPORTIONS: tuple[str, ...] = ("se", "sp", "accuracy")
#: ``comparison.differences`` keys that are not per operating point.
THRESHOLD_FREE_KEYS: tuple[str, ...] = ("auroc", "brier", "slope")


# ------------------------------------------------------------------------------- join


@dataclass(frozen=True)
class Join:
    """The paired join of two analysed tables on ``row_id``: the positions of the pairs
    in each table (aligned), the pair count and the counts left out."""

    new_index: np.ndarray
    prior_index: np.ndarray
    n_pairs: int
    new_only: int
    prior_only: int
    label_mismatch: int

    @property
    def paired(self) -> bool:
        return self.new_only == 0 and self.prior_only == 0 and self.label_mismatch == 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_pairs": self.n_pairs,
            "new_only": self.new_only,
            "prior_only": self.prior_only,
            "label_mismatch": self.label_mismatch,
        }


def paired_join(
    new_ids: Sequence[Any] | np.ndarray,
    prior_ids: Sequence[Any] | np.ndarray,
    new_labels: Sequence[Any] | np.ndarray | None = None,
    prior_labels: Sequence[Any] | np.ndarray | None = None,
) -> Join:
    """Pairs by ``row_id`` in the new table's row order. A blank id joins nothing. When
    labels are given, a pair whose ``y_true`` differs between the versions is not a pair
    (the same test set has one label per row) and is counted in ``label_mismatch``."""
    new_list = list(np.asarray(new_ids, dtype=object).tolist())
    prior_list = list(np.asarray(prior_ids, dtype=object).tolist())
    prior_pos: dict[Any, int] = {}
    for j, rid in enumerate(prior_list):
        if rid is not None:
            prior_pos.setdefault(rid, j)
    nl = None if new_labels is None else list(np.asarray(new_labels, dtype=object).tolist())
    pl = None if prior_labels is None else list(np.asarray(prior_labels, dtype=object).tolist())
    ni: list[int] = []
    pi: list[int] = []
    mismatch = 0
    matched_prior: set[int] = set()
    for i, rid in enumerate(new_list):
        j = prior_pos.get(rid) if rid is not None else None
        if j is None:
            continue
        matched_prior.add(j)
        if nl is not None and pl is not None and nl[i] != pl[j]:
            mismatch += 1
            continue
        ni.append(i)
        pi.append(j)
    new_only = sum(1 for rid in new_list if rid is None or rid not in prior_pos)
    prior_only = len(prior_list) - len(matched_prior)
    return Join(
        np.asarray(ni, dtype=np.intp),
        np.asarray(pi, dtype=np.intp),
        len(ni),
        int(new_only),
        int(prior_only),
        int(mismatch),
    )


# ---------------------------------------------------------------------------- McNemar


@dataclass(frozen=True)
class McNemar:
    """Discordant counts and the test on them. ``statistic`` is ``None`` on the exact
    route (a binomial tail has no chi-square statistic)."""

    b: int
    c: int
    n_discordant: int
    statistic: float | None
    p: float
    method: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _binomial_cdf_half(k: int, n: int) -> float:
    """``P(X <= k)`` for ``X ~ Binomial(n, 1/2)``, exactly (integer arithmetic)."""
    total = sum(math.comb(n, i) for i in range(0, k + 1))
    return total / (2**n)


def _chi2_sf_1df(statistic: float) -> float:
    """``P(chi^2_1 > statistic)`` = ``P(|Z| > sqrt(statistic))`` = ``erfc(sqrt(s / 2))``."""
    return float(math.erfc(math.sqrt(statistic / 2.0)))


def mcnemar(b: int, c: int, exact: bool | None = None) -> McNemar:
    """See the module docstring. ``b`` = prior correct and new wrong; ``c`` = new correct
    and prior wrong. ``exact`` ``None`` applies the ``b + c < EXACT_BELOW`` rule (the
    engine's only call); ``True`` / ``False`` forces one route (the fixture register
    compares both figures of R2's F5 on one table)."""
    b, c = int(b), int(c)
    if b < 0 or c < 0:
        raise ValueError("discordant counts must not be negative")
    n = b + c
    if (n < EXACT_BELOW) if exact is None else exact:
        p = min(1.0, 2.0 * _binomial_cdf_half(min(b, c), n)) if n > 0 else 1.0
        return McNemar(b, c, n, None, float(p), "exact_mcnemar")
    if n == 0:
        return McNemar(b, c, n, None, 1.0, "cc_mcnemar")
    statistic = (abs(b - c) - 1.0) ** 2 / n
    return McNemar(b, c, n, float(statistic), _chi2_sf_1df(statistic), "cc_mcnemar")


# ------------------------------------------------------------------- paired proportions


def paired_proportion_difference(
    correct_new: np.ndarray, correct_prior: np.ndarray, level: float = DEFAULT_LEVEL
) -> Number:
    """New minus prior for one conditioned proportion on the same pairs: the Newcombe
    paired method 10 interval of :func:`proofpack.stats.proportions.difference_paired`
    with ``e`` both correct, ``f`` new only, ``g`` prior only, ``h`` neither."""
    a = np.asarray(correct_new, dtype=bool)
    b = np.asarray(correct_prior, dtype=bool)
    if a.shape != b.shape:
        raise ValueError("the two indicator vectors must be aligned pairs")
    e = int((a & b).sum())
    f = int((a & ~b).sum())
    g = int((~a & b).sum())
    h = int((~a & ~b).sum())
    return difference_paired(e, f, g, h, level)


# ------------------------------------------------------------------------- the arrays


@dataclass(frozen=True)
class VersionArrays:
    """One version's analysed rows, aligned to the pairs when the comparison is paired.

    ``pos`` is the reference-positive mask; ``score`` the declared-orientation score
    (higher is positive) or ``None`` on a ``y_pred``-only table; ``probability`` the
    declared probability (unoriented, for the Brier and slope) or ``None``; ``pred`` the
    predicted-positive mask per operating point id; ``case_ids`` the cluster ids or
    ``None``.
    """

    pos: np.ndarray
    score: np.ndarray | None
    probability: np.ndarray | None
    pred: dict[str, np.ndarray]
    case_ids: np.ndarray | None = None

    @property
    def n(self) -> int:
        return int(self.pos.shape[0])

    def take(self, index: np.ndarray) -> VersionArrays:
        idx = np.asarray(index, dtype=np.intp)
        return VersionArrays(
            pos=self.pos[idx],
            score=None if self.score is None else self.score[idx],
            probability=None if self.probability is None else self.probability[idx],
            pred={op: p[idx] for op, p in self.pred.items()},
            case_ids=None if self.case_ids is None else self.case_ids[idx],
        )


def _conditioned(pos: np.ndarray, pred: np.ndarray, metric: str) -> tuple[np.ndarray, np.ndarray]:
    """``(selection mask, correct indicator over the selected rows)`` for one metric; the
    same conditioning ``stats.subgroups._conditioned`` applies."""
    if metric == "se":
        sel = pos
        ind = pred[sel]
    elif metric == "sp":
        sel = ~pos
        ind = ~pred[sel]
    elif metric == "accuracy":
        sel = np.ones(pos.shape[0], dtype=bool)
        ind = pos == pred
    else:  # pragma: no cover
        raise ValueError(metric)
    return sel, np.asarray(ind, dtype=bool)


def _cell_key(*parts: Any) -> str:
    return json.dumps(["comparison", *[str(p) for p in parts]])


def _cell(number: Number, analytic: Number | None, status: str) -> dict[str, Any]:
    """The comparison difference cell: the Number the page prints, the analytic method's
    companion (a typed refusal under clustering, the same Number when used) and what
    became of the analytic method (``used`` / ``refused_clustered`` /
    ``not_computed``)."""
    return {
        "number": number.as_dict(),
        "analytic": None if analytic is None else analytic.as_dict(),
        "analytic_status": status,
    }


def _labelled_unpaired(number: Number) -> Number:
    """The unpaired label on a Number: ``<method>_not_like_for_like`` in the method
    field and ``not_like_for_like`` among its flags."""
    d = asdict(number)
    if number.has_ci:
        d["method"] = f"{number.method}_not_like_for_like"
    d["flags"] = [*d["flags"], "not_like_for_like"]
    return Number(**d)


def _resampler(arrays: VersionArrays, plan: ClusterPlan | None) -> Resampler:
    if plan is not None and plan.clustered:
        if arrays.case_ids is None:
            raise ValueError("a clustered plan needs the case ids of the pairs")
        return clustered_by_case(arrays.pos, arrays.case_ids)
    return stratified_by_outcome(arrays.pos)


def _bootstrap_number(
    statistic: Callable[[np.ndarray], float],
    est: float | None,
    *,
    resampler: Resampler,
    policy: BootstrapPolicy,
    key: str,
    level: float,
    method: str,
    flags: list[str],
    **counts: Any,
) -> Number:
    draw = bootstrap_percentile(statistic, resampler, policy.rng(key), policy.n_resamples, level)
    if draw.ci_lo is None or draw.ci_hi is None:
        return not_estimable(
            str(draw.reason or "degenerate_resamples"), est=est, ci_level=level, **counts
        )
    return Number(
        est=est,
        ci_lo=draw.ci_lo,
        ci_hi=draw.ci_hi,
        ci_level=level,
        method=method,
        flags=list(flags),
        **counts,
    )


# ------------------------------------------------------------------- paired comparison


def _paired_proportion_cell(
    new: VersionArrays,
    prior: VersionArrays,
    op: str,
    metric: str,
    *,
    plan: ClusterPlan | None,
    policy: BootstrapPolicy,
    level: float,
    key_parts: tuple[Any, ...],
) -> dict[str, Any]:
    sel, correct_new = _conditioned(new.pos, new.pred[op], metric)
    _, correct_prior = _conditioned(prior.pos, prior.pred[op], metric)
    analytic = paired_proportion_difference(correct_new, correct_prior, level)
    clustered = plan is not None and plan.clustered
    if not clustered:
        return _cell(analytic, analytic, "used")
    n = int(sel.sum())
    if n == 0 or not analytic.has_ci:
        return _cell(analytic, analytic, "used")
    refusal = not_estimable(
        "clustered_data_analytic_ci_invalid", est=analytic.est, n=n, ci_level=level
    )
    sub = new.take(np.flatnonzero(sel))
    ids = sub.case_ids
    resampler = (
        clustered_by_case(sub.pos, ids) if ids is not None else stratified_by_outcome(sub.pos)
    )
    a = np.asarray(correct_new, dtype=np.float64)
    b = np.asarray(correct_prior, dtype=np.float64)

    def stat(idx: np.ndarray) -> float:
        return float(a[idx].mean() - b[idx].mean()) if idx.shape[0] else float("nan")

    number = _bootstrap_number(
        stat,
        analytic.est,
        resampler=resampler,
        policy=policy,
        key=_cell_key(*key_parts, op, metric),
        level=level,
        method="cluster_bootstrap_percentile",
        flags=["newcombe_refused_clustered"],
        n=n,
        n_cases=resampler.n_units,
    )
    return _cell(number, refusal, "refused_clustered")


def _paired_auroc_cell(
    new: VersionArrays,
    prior: VersionArrays,
    *,
    plan: ClusterPlan | None,
    policy: BootstrapPolicy,
    level: float,
    key_parts: tuple[Any, ...],
) -> dict[str, Any]:
    n_pos, n_neg = int(new.pos.sum()), int((~new.pos).sum())
    if new.score is None or prior.score is None:
        return _cell(
            not_estimable("not_computed_this_run", n_pos=n_pos, n_neg=n_neg, ci_level=level),
            None,
            "not_computed",
        )
    if n_pos < 2 or n_neg < 2:
        reason = "insufficient_positives" if n_pos < 2 else "insufficient_negatives"
        return _cell(not_estimable(reason, n_pos=n_pos, n_neg=n_neg, ci_level=level), None, "used")
    clustered = plan is not None and plan.clustered
    if not clustered:
        result = paired_delong(new.score, prior.score, new.pos, level)
        return _cell(result.difference, result.difference, "used")
    diff = float(
        auroc_mann_whitney(new.score, new.pos) - auroc_mann_whitney(prior.score, prior.pos)
    )
    refusal = not_estimable(
        "clustered_data_analytic_ci_invalid", est=diff, n_pos=n_pos, n_neg=n_neg, ci_level=level
    )
    resampler = _resampler(new, plan)
    sn, sp, pos = new.score, prior.score, new.pos

    def stat(idx: np.ndarray) -> float:
        p = pos[idx]
        if not p.any() or p.all():
            return float("nan")
        return float(auroc_mann_whitney(sn[idx], p) - auroc_mann_whitney(sp[idx], p))

    number = _bootstrap_number(
        stat,
        diff,
        resampler=resampler,
        policy=policy,
        key=_cell_key(*key_parts, "auroc"),
        level=level,
        method="cluster_bootstrap_percentile",
        flags=["delong_refused_clustered"],
        n_pos=n_pos,
        n_neg=n_neg,
        n_cases=resampler.n_units,
    )
    return _cell(number, refusal, "refused_clustered")


def _logit(p: np.ndarray) -> np.ndarray:
    q = np.clip(np.asarray(p, dtype=np.float64), CLIP_EPS, 1.0 - CLIP_EPS)
    return np.log(q / (1.0 - q))


def _slope(y: np.ndarray, logit_p: np.ndarray) -> float:
    fit = _fit_joint(y, logit_p)
    return float(fit.beta[1]) if fit.beta is not None else float("nan")


def _paired_calibration_cells(
    new: VersionArrays,
    prior: VersionArrays,
    *,
    plan: ClusterPlan | None,
    policy: BootstrapPolicy,
    level: float,
    key_parts: tuple[Any, ...],
    probability: bool,
) -> dict[str, dict[str, Any]]:
    n = new.n
    if not probability or new.probability is None or prior.probability is None:
        reason = "score_not_probability" if new.probability is None else "not_computed_this_run"
        return {
            k: _cell(not_estimable(reason, n=n, ci_level=level), None, "not_computed")
            for k in ("brier", "slope")
        }
    y = new.pos.astype(np.float64)
    pn, pp = new.probability.astype(np.float64), prior.probability.astype(np.float64)
    if n == 0 or not new.pos.any() or new.pos.all():
        reason = "zero_denominator" if n == 0 else "single_class"
        return {
            k: _cell(not_estimable(reason, n=n, ci_level=level), None, "used")
            for k in ("brier", "slope")
        }
    clustered = plan is not None and plan.clustered
    resampler = _resampler(new, plan)
    method = "cluster_bootstrap_percentile" if clustered else "bootstrap_percentile"
    counts: dict[str, Any] = {"n": n}
    if clustered:
        counts["n_cases"] = resampler.n_units
    sq_new, sq_prior = (pn - y) ** 2, (pp - y) ** 2
    brier_diff = float(sq_new.mean() - sq_prior.mean())

    def brier_stat(idx: np.ndarray) -> float:
        return float(sq_new[idx].mean() - sq_prior[idx].mean())

    ln, lp = _logit(pn), _logit(pp)
    slope_new, slope_prior = _slope(y, ln), _slope(y, lp)
    slope_diff = slope_new - slope_prior

    def slope_stat(idx: np.ndarray) -> float:
        return _slope(y[idx], ln[idx]) - _slope(y[idx], lp[idx])

    out: dict[str, dict[str, Any]] = {}
    for key, est, stat in (("brier", brier_diff, brier_stat), ("slope", slope_diff, slope_stat)):
        if not math.isfinite(est):
            out[key] = _cell(
                not_estimable("irls_not_converged", ci_level=level, **counts), None, "used"
            )
            continue
        number = _bootstrap_number(
            stat,
            est,
            resampler=resampler,
            policy=policy,
            key=_cell_key(*key_parts, key),
            level=level,
            method=method,
            flags=[],
            **counts,
        )
        out[key] = _cell(number, None, "used")
    return out


def _paired_differences(
    new: VersionArrays,
    prior: VersionArrays,
    *,
    ops: Sequence[str],
    se_key: str,
    sp_key: str,
    plan: ClusterPlan | None,
    policy: BootstrapPolicy,
    level: float,
    key_parts: tuple[Any, ...],
    probability: bool,
    with_calibration: bool = True,
) -> dict[str, Any]:
    keys = {"se": se_key, "sp": sp_key, "accuracy": "accuracy"}
    out: dict[str, Any] = {}
    for op in ops:
        out[op] = {
            keys[m]: _paired_proportion_cell(
                new, prior, op, m, plan=plan, policy=policy, level=level, key_parts=key_parts
            )
            for m in PROPORTIONS
        }
    out["auroc"] = _paired_auroc_cell(
        new, prior, plan=plan, policy=policy, level=level, key_parts=key_parts
    )
    if with_calibration:
        out.update(
            _paired_calibration_cells(
                new,
                prior,
                plan=plan,
                policy=policy,
                level=level,
                key_parts=key_parts,
                probability=probability,
            )
        )
    return out


def _mcnemar_by_op(new: VersionArrays, prior: VersionArrays, ops: Sequence[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for op in ops:
        correct_new = new.pos == new.pred[op]
        correct_prior = prior.pos == prior.pred[op]
        b = int((correct_prior & ~correct_new).sum())
        c = int((correct_new & ~correct_prior).sum())
        out[op] = mcnemar(b, c).as_dict()
    return out


# ----------------------------------------------------------------- unpaired comparison


def _unpaired_proportion_cell(
    new: VersionArrays, prior: VersionArrays, op: str, metric: str, *, clustered: bool, level: float
) -> dict[str, Any]:
    _, cn = _conditioned(new.pos, new.pred[op], metric)
    _, cp = _conditioned(prior.pos, prior.pred[op], metric)
    k1, n1, k2, n2 = int(cn.sum()), int(cn.shape[0]), int(cp.sum()), int(cp.shape[0])
    if clustered:
        est = (k1 / n1 - k2 / n2) if n1 and n2 else None
        number = _labelled_unpaired(
            not_estimable(
                "clustered_data_analytic_ci_invalid", est=est, n=min(n1, n2), ci_level=level
            )
        )
        return _cell(number, number, "refused_clustered")
    number = _labelled_unpaired(difference_unpaired(k1, n1, k2, n2, level))
    return _cell(number, number, "used")


def _unpaired_auroc_cell(
    new: VersionArrays, prior: VersionArrays, *, clustered: bool, level: float
) -> dict[str, Any]:
    counts = {
        "n_pos": int(new.pos.sum()) + int(prior.pos.sum()),
        "n_neg": int((~new.pos).sum()) + int((~prior.pos).sum()),
    }
    if new.score is None or prior.score is None:
        number = _labelled_unpaired(
            not_estimable("not_computed_this_run", ci_level=level, **counts)
        )
        return _cell(number, None, "not_computed")
    small = (
        int(new.pos.sum()) < 2
        or int((~new.pos).sum()) < 2
        or int(prior.pos.sum()) < 2
        or int((~prior.pos).sum()) < 2
    )
    if small:
        number = _labelled_unpaired(
            not_estimable("insufficient_positives", ci_level=level, **counts)
        )
        return _cell(number, number, "used")
    if clustered:
        est = float(
            auroc_mann_whitney(new.score, new.pos) - auroc_mann_whitney(prior.score, prior.pos)
        )
        number = _labelled_unpaired(
            not_estimable("clustered_data_analytic_ci_invalid", est=est, ci_level=level, **counts)
        )
        return _cell(number, number, "refused_clustered")
    result = unpaired_delong(new.score, new.pos, prior.score, prior.pos, level)
    number = _labelled_unpaired(result.difference)
    return _cell(number, number, "used")


def _unpaired_differences(
    new: VersionArrays,
    prior: VersionArrays,
    *,
    ops: Sequence[str],
    se_key: str,
    sp_key: str,
    clustered: bool,
    level: float,
) -> dict[str, Any]:
    keys = {"se": se_key, "sp": sp_key, "accuracy": "accuracy"}
    out: dict[str, Any] = {}
    for op in ops:
        out[op] = {
            keys[m]: _unpaired_proportion_cell(new, prior, op, m, clustered=clustered, level=level)
            for m in PROPORTIONS
        }
    out["auroc"] = _unpaired_auroc_cell(new, prior, clustered=clustered, level=level)
    for key in ("brier", "slope"):
        number = _labelled_unpaired(
            not_estimable("unpaired_not_like_for_like", n=min(new.n, prior.n), ci_level=level)
        )
        out[key] = _cell(number, None, "not_computed")
    return out


# ------------------------------------------------------------------------- the block


def compare_versions(
    new: VersionArrays,
    prior: VersionArrays,
    *,
    paired: bool,
    join: Join | None,
    ops: Sequence[str],
    se_key: str = "sensitivity",
    sp_key: str = "specificity",
    plan: ClusterPlan | None = None,
    policy: BootstrapPolicy | None = None,
    level: float = DEFAULT_LEVEL,
    probability: bool = True,
    subgroups: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    """The ``comparison`` block's statistics (D1 section 4.2), without ``prior_version``
    and ``ledger``, which the assembly adds.

    ``paired`` says which path; ``join`` is the ``row_id`` join (recorded for its counts
    on either path; ``None`` when no join was attempted); on the paired path ``new`` and
    ``prior`` are already aligned to the pairs (``VersionArrays.take``).
    ``subgroups`` lists ``{"attribute", "level", "rows"}`` with ``rows`` the positions,
    among the pairs, of the new version's rows in that level; each yields per-operating-
    point paired proportion differences and the paired AUROC difference on those pairs
    (the calibration differences are overall only). On the unpaired path the subgroup
    list is empty and ``subgroups_not_computed`` says why.
    """
    pol = policy if policy is not None else BootstrapPolicy()
    if paired and (join is None or not join.paired):
        raise ValueError("a paired comparison needs a one-to-one join")
    clustered = plan is not None and plan.clustered
    block: dict[str, Any] = {
        "paired": paired,
        "label": None if paired else NOT_LIKE_FOR_LIKE,
        "n_pairs": join.n_pairs if join is not None else None,
        "unpaired_rows": (
            join.as_dict()
            if join is not None
            else {"n_pairs": 0, "new_only": new.n, "prior_only": prior.n, "label_mismatch": 0}
        ),
        "n_new": new.n,
        "n_prior": prior.n,
        "clustering_route": plan.route if plan is not None else "none",
        "bootstrap": {"B": pol.n_resamples, "seed": pol.seed, "interval": pol.interval},
        "score_is_probability": bool(probability),
    }
    if paired:
        if new.n != prior.n:
            raise ValueError("a paired comparison needs aligned arrays")
        block["mcnemar"] = _mcnemar_by_op(new, prior, ops)
        block["differences"] = _paired_differences(
            new,
            prior,
            ops=ops,
            se_key=se_key,
            sp_key=sp_key,
            plan=plan,
            policy=pol,
            level=level,
            key_parts=("overall",),
            probability=probability,
        )
        rows_out: list[dict[str, Any]] = []
        for s in subgroups:
            rows = np.asarray(s["rows"], dtype=np.intp)
            entry: dict[str, Any] = {
                "attribute": str(s["attribute"]),
                "level": str(s["level"]),
                "n_pairs": int(rows.shape[0]),
                "differences": None,
                "not_computed_reason": None,
            }
            if rows.shape[0] == 0:
                entry["not_computed_reason"] = "zero_denominator"
            else:
                sub_new, sub_prior = new.take(rows), prior.take(rows)
                entry["differences"] = _paired_differences(
                    sub_new,
                    sub_prior,
                    ops=ops,
                    se_key=se_key,
                    sp_key=sp_key,
                    plan=plan,
                    policy=pol,
                    level=level,
                    key_parts=("subgroups", s["attribute"], s["level"]),
                    probability=probability,
                    with_calibration=False,
                )
            rows_out.append(entry)
        block["subgroups"] = rows_out
        block["subgroups_not_computed"] = None
    else:
        block["mcnemar"] = None
        block["differences"] = _unpaired_differences(
            new, prior, ops=ops, se_key=se_key, sp_key=sp_key, clustered=clustered, level=level
        )
        block["subgroups"] = []
        block["subgroups_not_computed"] = "unpaired_not_like_for_like"
    return block
