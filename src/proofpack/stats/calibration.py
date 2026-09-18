"""``stats.calibration`` - calibration of a declared probability (build day 6, E6).

What this module produces (D1 section 3.1 ``stats.calibration``, R2 section 1.4, D4
section 5.5): for a score the customer declared as a **probability of the positive
class**, the Van Calster 2019 hierarchy as far as the "moderate" level - the O:E ratio,
calibration-in-the-large, the calibration slope and intercept, a decile (equal-mass)
curve - plus the Brier score, its prevalence-only reference and the IPA, and the ECE
under two stated binning schemes as a supplementary figure. Nothing here is a verdict:
no target is compared to, no word describes the calibration, every quantity is an
estimate with an interval or a typed reason why it has none.

Conventions this module fixes (each is also in ``design/conventions_T7.md``)
-----------------------------------------------------------------------------

**Suppression, never a silent transform.** The block is computed only when
``score.type`` is ``probability`` **and** ``score.orientation`` is
``higher_is_positive``. A ``logit`` or ``other`` score is not a probability and the
block is ``None`` with the typed reason ``score_not_probability`` (the declared type in
the detail beside it). A ``lower_is_positive`` "probability" is not the probability of
the positive class either: ``1 - p`` would assume it is the probability of the negative
class, which the customer did not declare, so it is refused with the typed reason
``score_not_positive_class_probability`` rather than transformed (day-5 handoff,
inheritance item 6). The refusal is a value in the output, not an absence: the caller
writes it where D1 puts ``suppressed_reason``.

**O:E ratio.** Observed events ``O = sum(y)`` over expected events ``E = sum(p)``.
The interval is on the log scale by the delta method: with ``E`` taken as fixed and
``O`` binomial with variance ``N pi (1 - pi)`` estimated at ``pi = O / N``,
``Var(ln O) = Var(O) / O**2 = (1 - O/N) / O``, so
``ln(O/E) +/- z * sqrt((1 - O/N) / O)`` and the bounds are exponentiated (method
``log_delta``). This is the standard error Debray et al. 2017 (BMJ, "A guide to
systematic review and meta-analysis of prediction model performance") give for
``ln(O:E)`` **[unverified - cited from memory; the derivation above is self-contained
and the tests recompute it from the formula, not the citation]**. ``O = 0`` makes the
log undefined (``zero_cell_log_undefined``); ``E = 0`` is a zero denominator; a single
outcome class is refused as ``single_class`` before either.

**Calibration-in-the-large** is the intercept ``a`` of the logistic model
``logit P(y=1) = a + logit(p)`` with the slope fixed at 1 (an offset model), fitted by
the module's own Newton-Raphson / IRLS in numpy (:func:`irls_logistic`); the Wald
interval comes from the observed information at convergence (``irls_wald``). The
oracle is ``statsmodels GLM(Binomial)`` with ``offset=logit(p)`` (F4).

**Slope and intercept** are ``b`` and ``a`` of ``logit P(y=1) = a + b * logit(p)``,
the same IRLS with two parameters; Wald intervals from the inverse observed
information (for the canonical logit link the observed and expected information
coincide). Oracle: ``statsmodels GLM(Binomial)`` on ``[1, logit(p)]`` (F4).

**IRLS rules.** Newton steps with step-halving when the deviance does not fall;
converged when the largest parameter change is at most ``IRLS_TOL`` times
``(1 + |parameter|)``; at most ``IRLS_MAX_ITER`` iterations. What does not converge
is a typed outcome, never ``inf``, ``nan`` or a traceback: ``complete_separation``
when every fitted probability is within ``SEPARATION_TOL`` of its label (the MLE does
not exist), ``irls_not_converged`` when the iteration budget runs out, ``single_class``
before any fit when the labels take one value, ``constant_score`` when ``logit(p)``
takes one value (the slope is not identifiable and the two-parameter information is
singular).

**Scores at exactly 0 or 1.** ``logit(0)`` and ``logit(1)`` are infinite. For the two
logit-scale models only, the score is clipped to ``[CLIP_EPS, 1 - CLIP_EPS]`` with
``CLIP_EPS = 1e-12``; the count of clipped rows is carried in the block
(``n_clipped``) and the flag ``scores_clipped_for_logit`` rides on the three IRLS
Numbers when the count is positive. The O:E ratio, the Brier score, the ECE and the
decile curve use the raw score - they are well defined at 0 and 1 and are not clipped.
A test pins the value used at the boundary against the oracle on the clipped vector.

**Decile curve.** Ten equal-mass bins by score rank. Ties are placed by **stable sort
order** (``numpy.argsort(kind="stable")``): two rows with the same score keep their
row order, and the bins are ``numpy.array_split`` of that order, so when ``N`` is not a
multiple of ten the first ``N mod 10`` bins hold one extra row. Each bin reports its
``n``, ``events``, the mean predicted probability and the observed event rate as a
proportion through :func:`~proofpack.stats.bootstrap.proportion_ci` - Wilson on
independent rows, the cluster bootstrap with Wilson refused under a clustered plan
(DEC-10, X2) - carrying the day-5 tier annotations exactly as the subgroup cells do. A
bin that receives no rows (``N < 10``) is ``zero_denominator``, never dropped.

**Brier, reference Brier, IPA.** The Brier score is the plain mean of
``(p - y)**2`` with a percentile bootstrap interval through the day-4 resampler,
stratified by outcome or clustered by case exactly as ``stats.subgroups._brier_cell``
does, so the overall Brier equals the subgroup module's value on the whole cohort taken
as one level (a test checks est and bounds bit for bit under the same cell key). The
reference Brier is ``pi (1 - pi)`` at the observed prevalence - the Brier score of
predicting the prevalence for every row - and ``IPA = 1 - Brier / Brier_ref``. The
outcome-stratified resampler holds the prevalence in every resample by construction, so
the reference Brier cannot vary under it and is reported with the typed reason
``fixed_by_outcome_stratification`` (its uncertainty is the prevalence's, which the
threshold-free block carries); under a clustered plan whose case sizes differ or whose
cases mix outcomes the prevalence does vary and the reference Brier is bootstrapped
with everything else. The IPA draws use each resample's own Brier and reference Brier.

**ECE** (R2 section 1.4, after Nixon et al. 2019): ``sum_b (n_b / N) |mean(y)_b -
mean(p)_b|`` under **two** schemes, each reported with its scheme stated - ten
equal-width bins on ``[0, 1]`` and ten equal-mass bins (the decile bins above). The
equal-width bins are right-closed ``(lo, hi]`` with the first bin closed at 0, so a
score exactly on an interior edge belongs to the bin whose *upper* edge it is: this is
the convention that reproduces R2's F4 figures (0.1255 at five bins, 0.1955 at ten) and
``sklearn.calibration.calibration_curve``'s binning. Both are labelled
``supplementary`` in a ``note`` (R2: "treat ECE as descriptive"). **No interval is
emitted for either ECE** - ``not_computed_this_run`` on the Number, and the reason
why is here: the percentile bootstrap of a binned absolute deviation overstates it in
every resample (the absolute value of sampling noise does not average out), and no coverage run of
that interval has been made against the DEC-08 bar; an interval nobody has measured
would be exactly the kind of number the day-5 lenses found. An ECE interval is a
build item with its own coverage run, not a default.

**The 200/200 annotation** (R2 section 1.4, Van Calster 2019: "a minimum of 200
patients with and 200 patients without the event has been suggested"): when the
analysed rows hold fewer than 200 events **or** fewer than 200 non-events the flag
``below_200_events_or_nonevents`` rides on every decile bin's observed Number and the
block's ``curve_flag`` names the counts and the sentence "ProofPack convention after
Van Calster 2019". The inequality is strict on both sides - 199 events is flagged, 200
is not. Events are counted in analysed **rows**; under clustering the count of cases
carrying the event is reported beside it. It is an annotation, never a suppression
(DEC-08): the curve, the slope, the intercept and the O:E are all still reported.

**Under a clustered plan** (declared or detected) every analytic interval - the
log-delta O:E, the three IRLS Wald intervals, Wilson per bin - is refused with the
typed reason ``clustered_data_analytic_ci_invalid`` on the companion Number (DEC-09,
X2) and the cluster bootstrap takes its place: cases resampled within outcome class
with all rows of a drawn case kept, the statistic (the O:E ratio; the refitted
intercept, slope or intercept-in-the-large; the Brier) recomputed on each resample,
percentile interval, method ``cluster_bootstrap_percentile``, flag
``log_delta_refused_clustered`` or ``irls_wald_refused_clustered`` on the rendered
Number. A resample on which the IRLS does not converge is ``nan`` to the resampler and
counted against :data:`~proofpack.stats.bootstrap.MIN_USABLE_FRACTION`.

**Cell shape.** Every quantity is serialised as the day-4 cell ``{number, analytic,
analytic_status, clustering_route, bootstrap[, detail]}`` so the companion refusal and
the resampling quantities that decided it reach the output JSON beside the rendered
Number; the renderer reads ``number``. D1 section 4.2 writes the block as bare Numbers;
the cell wrapper is the day-4 shape and is recorded as a deviation (day-5 note, open
question 4).

Nothing here reads or writes a file, and nothing here imports scipy - not at module
level and not inside any function. The module must import and run with numpy alone.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from proofpack.io.declare import Declarations
from proofpack.stats.bootstrap import (
    DEFAULT_LEVEL,
    BootstrapPolicy,
    CellCI,
    ClusterPlan,
    Resampler,
    _number_from_draw,
    bootstrap_percentile,
    clustered_by_case,
    plan_clustering,
    precision_flags,
    proportion_ci,
    stratified_by_outcome,
)
from proofpack.stats.number import Number, not_estimable
from proofpack.stats.proportions import z_for

__all__ = [
    "CALIBRATION_CONVENTION",
    "CLIP_EPS",
    "CURVE_MIN_EVENTS",
    "CalibrationResult",
    "IRLS_MAX_ITER",
    "IRLS_TOL",
    "IrlsFit",
    "N_BINS",
    "SEPARATION_TOL",
    "calibration_block",
    "calibration_from_table",
    "ece",
    "equal_mass_bins",
    "equal_width_bin_index",
    "irls_logistic",
    "oe_log_delta_bounds",
    "suppression_reason",
]

#: Van Calster 2019's suggested minimum of patients with, and without, the event
#: below which the flexible curve is not shown. ProofPack's convention: an annotation.
CURVE_MIN_EVENTS = 200
CALIBRATION_CONVENTION = "ProofPack convention after Van Calster 2019"
#: Both ECE schemes and the decile curve use ten bins (D1 section 3.1).
N_BINS = 10
#: Scores at exactly 0 or 1 are clipped to this distance from the boundary for the two
#: logit-scale models only; see the module docstring.
CLIP_EPS = 1e-12
#: IRLS convergence: largest relative parameter change at or below this.
IRLS_TOL = 1e-10
IRLS_MAX_ITER = 100
#: Every fitted probability within this of its label means the MLE does not exist.
SEPARATION_TOL = 1e-8
#: Step-halvings allowed per Newton step before the fit is declared not converged.
MAX_STEP_HALVINGS = 30
_SUPPLEMENTARY_NOTE = (
    "supplementary; ECE is bin-sensitive and descriptive (R2 section 1.4 after Nixon et al. "
    "2019); the scheme is stated beside the value; no interval is emitted for it"
)
_ECE_CI_WHY = (
    "no interval is emitted for the ECE: the percentile bootstrap of a binned absolute "
    "deviation overstates it in every resample (the absolute value of sampling noise does not "
    "average out) and no coverage run of that interval has been made against the DEC-08 bar"
)


def _cell_key(*parts: Any) -> str:
    return json.dumps(["calibration", *[str(p) for p in parts]])


# ------------------------------------------------------------------------- suppression


def suppression_reason(decl: Declarations) -> str | None:
    """The typed reason the block is not computed for these declarations, or ``None``."""
    if decl.score_type != "probability":
        return "score_not_probability"
    if decl.orientation != "higher_is_positive":
        return "score_not_positive_class_probability"
    return None


# ------------------------------------------------------------------------------- O:E


def oe_log_delta_bounds(o: float, e: float, n: int, level: float) -> tuple[float, float]:
    """``exp(ln(O/E) -/+ z * sqrt((1 - O/N) / O))``. Requires ``0 < O`` and ``E > 0``."""
    if o <= 0.0 or e <= 0.0 or n <= 0:
        raise ValueError("the log-delta interval needs O > 0, E > 0 and N > 0")
    se = math.sqrt((1.0 - o / n) / o)
    z = z_for(level)
    centre = math.log(o / e)
    return math.exp(centre - z * se), math.exp(centre + z * se)


# ------------------------------------------------------------------------------ IRLS


@dataclass(frozen=True)
class IrlsFit:
    """One logistic fit: parameters, Wald standard errors and the typed outcome.

    ``reason`` is ``None`` when the fit converged; otherwise one of
    ``complete_separation`` / ``irls_not_converged`` / ``constant_score`` /
    ``single_class`` and ``beta`` / ``se`` are ``None``.
    """

    beta: np.ndarray | None
    se: np.ndarray | None
    iterations: int
    deviance: float | None
    reason: str | None


def _expit(eta: np.ndarray) -> np.ndarray:
    # numerically stable in both tails; eta beyond +/-700 would overflow exp
    out = np.empty_like(eta)
    pos = eta >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-eta[pos]))
    ex = np.exp(eta[~pos])
    out[~pos] = ex / (1.0 + ex)
    return out


def _deviance(y: np.ndarray, mu: np.ndarray) -> float:
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = np.where(y > 0, y * np.log(y / mu), 0.0)
        t2 = np.where(y < 1, (1 - y) * np.log((1 - y) / (1 - mu)), 0.0)
    return float(2.0 * np.sum(t1 + t2))


def irls_logistic(
    y: np.ndarray,
    x: np.ndarray,
    offset: np.ndarray | None = None,
    *,
    tol: float = IRLS_TOL,
    max_iter: int = IRLS_MAX_ITER,
) -> IrlsFit:
    """Logistic regression of ``y`` (0/1) on the design ``x`` with an optional offset.

    Newton-Raphson on the log-likelihood (identical to IRLS for the canonical link),
    with step-halving when a step does not lower the deviance. Returns a typed outcome
    rather than raising: see :class:`IrlsFit`.
    """
    y = np.asarray(y, dtype=np.float64)
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    n, p = x.shape
    off = np.zeros(n) if offset is None else np.asarray(offset, dtype=np.float64)
    if n == 0 or not (0.0 < y.mean() < 1.0):
        return IrlsFit(None, None, 0, None, "single_class")
    if p > 1 and np.ptp(x[:, 1:], axis=0).max() == 0.0:
        return IrlsFit(None, None, 0, None, "constant_score")
    beta = np.zeros(p)
    eta = off + x @ beta
    mu = _expit(eta)
    dev = _deviance(y, mu)
    for it in range(1, max_iter + 1):
        w = mu * (1.0 - mu)
        info = (x * w[:, None]).T @ x
        grad = x.T @ (y - mu)
        try:
            step = np.linalg.solve(info, grad)
        except np.linalg.LinAlgError:
            return IrlsFit(None, None, it, dev, "irls_not_converged")
        # step-halving: accept the first step that does not raise the deviance
        scale = 1.0
        for _ in range(MAX_STEP_HALVINGS + 1):
            cand = beta + scale * step
            eta_c = off + x @ cand
            mu_c = _expit(eta_c)
            dev_c = _deviance(y, mu_c)
            if np.isfinite(dev_c) and dev_c <= dev + 1e-12:
                break
            scale *= 0.5
        else:
            return IrlsFit(None, None, it, dev, "irls_not_converged")
        change = np.max(np.abs(cand - beta) / (1.0 + np.abs(cand)))
        beta, mu, dev = cand, mu_c, dev_c
        if np.all(np.abs(mu - y) < SEPARATION_TOL):
            return IrlsFit(None, None, it, dev, "complete_separation")
        if change <= tol:
            w = mu * (1.0 - mu)
            info = (x * w[:, None]).T @ x
            try:
                cov = np.linalg.inv(info)
            except np.linalg.LinAlgError:
                return IrlsFit(None, None, it, dev, "irls_not_converged")
            se = np.sqrt(np.diag(cov))
            if not (np.all(np.isfinite(beta)) and np.all(np.isfinite(se))):
                return IrlsFit(None, None, it, dev, "irls_not_converged")
            return IrlsFit(beta, se, it, dev, None)
    return IrlsFit(None, None, max_iter, dev, "irls_not_converged")


def _fit_offset(y: np.ndarray, logit_p: np.ndarray) -> IrlsFit:
    return irls_logistic(y, np.ones((y.shape[0], 1)), offset=logit_p)


def _fit_joint(y: np.ndarray, logit_p: np.ndarray) -> IrlsFit:
    return irls_logistic(y, np.column_stack([np.ones(y.shape[0]), logit_p]))


# -------------------------------------------------------------------------- binning


def equal_mass_bins(score: np.ndarray, n_bins: int = N_BINS) -> list[np.ndarray]:
    """Row indices per equal-mass bin, by score rank; ties by stable sort order."""
    order = np.argsort(np.asarray(score, dtype=np.float64), kind="stable")
    return [np.asarray(b, dtype=np.intp) for b in np.array_split(order, n_bins)]


def equal_width_bin_index(score: np.ndarray, n_bins: int = N_BINS) -> np.ndarray:
    """Bin index for right-closed equal-width bins ``(lo, hi]`` on ``[0, 1]``, first bin
    closed at 0. The edges are ``arange(n_bins + 1) / n_bins`` so a decimal score equal
    to an interior edge compares equal to it."""
    edges = np.arange(n_bins + 1) / n_bins
    idx = np.searchsorted(edges, np.asarray(score, dtype=np.float64), side="left") - 1
    return np.clip(idx, 0, n_bins - 1)


def ece(y: np.ndarray, p: np.ndarray, bins: Sequence[np.ndarray]) -> float:
    """``sum_b (n_b / N) |mean(y)_b - mean(p)_b|`` over the given row-index bins."""
    n = y.shape[0]
    total = 0.0
    for rows in bins:
        if rows.shape[0] == 0:
            continue
        total += rows.shape[0] / n * abs(float(y[rows].mean()) - float(p[rows].mean()))
    return total


def _equal_width_rows(p: np.ndarray, n_bins: int = N_BINS) -> list[np.ndarray]:
    idx = equal_width_bin_index(p, n_bins)
    return [np.flatnonzero(idx == b) for b in range(n_bins)]


# ---------------------------------------------------------------------------- cells


@dataclass(frozen=True)
class _Ctx:
    """The analysed rows, typed once, and the run-level clustering decision."""

    y: np.ndarray  # float 0/1
    pos: np.ndarray  # bool
    p: np.ndarray  # raw probability
    logit_p: np.ndarray  # clipped then logit
    n_clipped: int
    ids: np.ndarray | None
    plan: ClusterPlan
    policy: BootstrapPolicy
    level: float

    @property
    def n(self) -> int:
        return int(self.y.shape[0])

    @property
    def clustered(self) -> bool:
        return self.plan.clustered

    def resampler(self) -> Resampler:
        if self.clustered and self.ids is not None:
            return clustered_by_case(self.pos, self.ids)
        return stratified_by_outcome(self.pos)

    def counts(self, resampler: Resampler | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {"n": self.n}
        if self.clustered:
            out["n_cases"] = (
                resampler.n_units if resampler is not None else int(np.unique(self.ids).shape[0])  # type: ignore[arg-type]
            )
        return out

    def tier(self, resampler: Resampler | None = None) -> list[str]:
        units = self.counts(resampler).get("n_cases", self.n)
        events = int(self.pos.sum()) if not self.clustered else None
        return precision_flags(units, events)


def _unavailable(ctx: _Ctx, key: str, reason: str, *, est: float | None = None) -> CellCI:
    number = not_estimable(reason, est=est, ci_level=ctx.level, **ctx.counts())
    return CellCI(number, number, "unavailable", key, ctx.plan.route)


def _clustered_cell(
    ctx: _Ctx,
    key: str,
    *,
    est: float,
    statistic: Callable[[np.ndarray], float],
    refused_flag: str,
    extra_flags: Sequence[str] = (),
) -> CellCI:
    """The cluster-bootstrap route for a quantity whose analytic interval is refused."""
    resampler = ctx.resampler()
    counts = ctx.counts(resampler)
    pol = ctx.policy
    draw = bootstrap_percentile(statistic, resampler, pol.rng(key), pol.n_resamples, ctx.level)
    refused = not_estimable(
        "clustered_data_analytic_ci_invalid", est=est, ci_level=ctx.level, **counts
    )
    flags = [refused_flag, *extra_flags, *ctx.tier(resampler)]
    if draw.reason is not None:
        number = not_estimable(draw.reason, est=est, ci_level=ctx.level, flags=flags, **counts)
        status = "unavailable"
    else:
        number = Number(
            est=est,
            ci_lo=draw.ci_lo,
            ci_hi=draw.ci_hi,
            ci_level=ctx.level,
            method="cluster_bootstrap_percentile",
            flags=flags,
            **counts,
        )
        status = "refused_clustered"
    return CellCI(
        number,
        refused,
        status,
        key,
        ctx.plan.route,
        pol,
        draw.n_usable,
        draw.sd,
        resampler.describe(),
    )


def _oe_cell(ctx: _Ctx) -> CellCI:
    key = _cell_key("oe")
    o = float(ctx.y.sum())
    e = float(ctx.p.sum())
    n = ctx.n
    if n == 0 or e <= 0.0:
        return _unavailable(ctx, key, "zero_denominator")
    est = o / e
    if o == 0.0 or o == n:
        return _unavailable(ctx, key, "single_class", est=est)
    if ctx.clustered:

        def statistic(idx: np.ndarray) -> float:
            den = float(ctx.p[idx].sum())
            return float(ctx.y[idx].sum()) / den if den > 0.0 else float("nan")

        return _clustered_cell(
            ctx, key, est=est, statistic=statistic, refused_flag="log_delta_refused_clustered"
        )
    lo, hi = oe_log_delta_bounds(o, e, n, ctx.level)
    number = Number(
        est=est,
        ci_lo=lo,
        ci_hi=hi,
        ci_level=ctx.level,
        method="log_delta",
        n=n,
        k=int(o),
        flags=ctx.tier(),
    )
    return CellCI(number, number, "used", key, ctx.plan.route)


def _irls_cells(ctx: _Ctx) -> dict[str, tuple[CellCI, dict[str, Any]]]:
    """``intercept_large`` (offset model), ``slope`` and ``intercept`` (joint model),
    each with a detail block (iterations, deviance, the Wald SE or the typed outcome)."""
    clip_flags = ["scores_clipped_for_logit"] if ctx.n_clipped else []
    out: dict[str, tuple[CellCI, dict[str, Any]]] = {}
    if ctx.n == 0:
        for name in ("intercept_large", "slope", "intercept"):
            cell = _unavailable(ctx, _cell_key(name), "zero_denominator")
            out[name] = (cell, {"outcome": "zero_denominator"})
        return out
    fits = {"offset": _fit_offset(ctx.y, ctx.logit_p), "joint": _fit_joint(ctx.y, ctx.logit_p)}
    specs: list[tuple[str, str, int]] = [
        ("intercept_large", "offset", 0),
        ("slope", "joint", 1),
        ("intercept", "joint", 0),
    ]
    for name, model, col in specs:
        key = _cell_key(name)
        fit = fits[model]
        fitter = _fit_offset if model == "offset" else _fit_joint
        detail: dict[str, Any] = {
            "model": (
                "logit P(y=1) = a + logit(p), slope fixed at 1"
                if model == "offset"
                else "logit P(y=1) = a + b * logit(p)"
            ),
            "iterations": fit.iterations,
            "deviance": fit.deviance,
        }
        if fit.reason is not None:
            number = not_estimable(
                fit.reason, ci_level=ctx.level, flags=list(clip_flags), **ctx.counts()
            )
            cell = CellCI(number, number, "unavailable", key, ctx.plan.route)
            out[name] = (cell, {**detail, "outcome": fit.reason})
            continue
        est = float(fit.beta[col])  # type: ignore[index]
        se = float(fit.se[col])  # type: ignore[index]
        if ctx.clustered:

            def statistic(idx: np.ndarray, _f: Any = fitter, _c: int = col) -> float:
                r = _f(ctx.y[idx], ctx.logit_p[idx])
                return float("nan") if r.reason is not None else float(r.beta[_c])

            cell = _clustered_cell(
                ctx,
                key,
                est=est,
                statistic=statistic,
                refused_flag="irls_wald_refused_clustered",
                extra_flags=clip_flags,
            )
            out[name] = (cell, {**detail, "wald_se": se, "outcome": "converged"})
            continue
        z = z_for(ctx.level)
        number = Number(
            est=est,
            ci_lo=est - z * se,
            ci_hi=est + z * se,
            ci_level=ctx.level,
            method="irls_wald",
            flags=[*clip_flags, *ctx.tier()],
            **ctx.counts(),
        )
        cell = CellCI(number, number, "used", key, ctx.plan.route)
        out[name] = (cell, {**detail, "wald_se": se, "outcome": "converged"})
    return out


def _cell_dict(cell: CellCI, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    out = cell.as_dict()
    if detail is not None:
        out["detail"] = detail
    return out


def _prevalence_invariant(resampler: Resampler) -> bool:
    """Whether every resample keeps the prevalence: no mixed stratum, and every stratum's
    units of one size (so the number of rows drawn per class is fixed)."""
    return all(s.label != "mixed" and s.matrix is not None for s in resampler.strata)


def _brier_cells(ctx: _Ctx) -> dict[str, CellCI]:
    """``brier``, ``brier_ref`` and ``ipa``; the Brier exactly as ``_brier_cell``."""
    n = ctx.n
    pol, level = ctx.policy, ctx.level
    sq = (ctx.p - ctx.y) ** 2
    brier = float(sq.mean()) if n else None
    pi = float(ctx.y.mean()) if n else None
    ref = pi * (1.0 - pi) if pi is not None else None
    ipa = 1.0 - brier / ref if brier is not None and ref else None
    keys = {k: _cell_key(k) for k in ("brier", "brier_ref", "ipa")}
    if n == 0:
        return {k: _unavailable(ctx, keys[k], "zero_denominator") for k in keys}
    if not ctx.pos.any() or ctx.pos.all():
        return {
            "brier": _unavailable(ctx, keys["brier"], "single_class", est=brier),
            "brier_ref": _unavailable(ctx, keys["brier_ref"], "single_class", est=ref),
            "ipa": _unavailable(ctx, keys["ipa"], "single_class"),
        }
    resampler = ctx.resampler()
    counts = ctx.counts(resampler)
    method = "cluster_bootstrap_percentile" if ctx.clustered else "bootstrap_percentile"
    tier = precision_flags(resampler.n_units)
    route = ctx.plan.route

    def refusal(est: float | None) -> Number:
        return not_estimable(
            "clustered_data_analytic_ci_invalid" if ctx.clustered else "analytic_ci_unavailable",
            est=est,
            ci_level=level,
            **counts,
        )

    def cell(key: str, est: float, statistic: Callable[[np.ndarray], float]) -> CellCI:
        draw = bootstrap_percentile(statistic, resampler, pol.rng(key), pol.n_resamples, level)
        number = _number_from_draw(draw, est=est, method=method, level=level, flags=tier, **counts)
        status = "refused_clustered" if ctx.clustered else "used"
        if not number.has_ci:
            status = "unavailable"
        return CellCI(
            number,
            refusal(est),
            status,
            key,
            route,
            pol,
            draw.n_usable,
            draw.sd,
            resampler.describe(),
        )

    def ref_of(idx: np.ndarray) -> float:
        q = float(ctx.y[idx].mean())
        return q * (1.0 - q)

    def ipa_of(idx: np.ndarray) -> float:
        r = ref_of(idx)
        return 1.0 - float(sq[idx].mean()) / r if r > 0.0 else float("nan")

    out = {"brier": cell(keys["brier"], brier, lambda idx: float(sq[idx].mean()))}
    if _prevalence_invariant(resampler):
        number = not_estimable(
            "fixed_by_outcome_stratification", est=ref, ci_level=level, flags=list(tier), **counts
        )
        out["brier_ref"] = CellCI(
            number,
            refusal(ref),
            "unavailable",
            keys["brier_ref"],
            route,
            pol,
            0,
            None,
            resampler.describe(),
        )
    else:
        out["brier_ref"] = cell(keys["brier_ref"], ref, ref_of)
    out["ipa"] = cell(keys["ipa"], ipa, ipa_of)
    return out


def _decile_curve(ctx: _Ctx, curve_flag: str | None) -> list[dict[str, Any]]:
    rows_per_bin = equal_mass_bins(ctx.p)
    out = []
    for b, rows in enumerate(rows_per_bin):
        n_b = int(rows.shape[0])
        cell = proportion_ci(
            ctx.pos[rows],
            cell_key=_cell_key("decile", b),
            policy=ctx.policy,
            plan=ctx.plan,
            cluster_ids=None if ctx.ids is None else ctx.ids[rows],
            level=ctx.level,
        )
        if curve_flag is not None and curve_flag not in cell.number.flags:
            cell.number.flags.append(curve_flag)
        out.append(
            {
                "bin": b + 1,
                "n": n_b,
                "events": int(ctx.pos[rows].sum()),
                "mean_pred": float(ctx.p[rows].mean()) if n_b else None,
                "score_min": float(ctx.p[rows].min()) if n_b else None,
                "score_max": float(ctx.p[rows].max()) if n_b else None,
                "observed": cell.as_dict(),
            }
        )
    return out


def _ece_entry(
    ctx: _Ctx, scheme: str, bins: list[np.ndarray], edges: list[float]
) -> dict[str, Any]:
    est = ece(ctx.y, ctx.p, bins) if ctx.n else None
    number = not_estimable("not_computed_this_run", est=est, ci_level=ctx.level, **ctx.counts())
    return {
        "number": number.as_dict(),
        "bins": len(bins),
        "scheme": scheme,
        "edges": edges,
        "note": _SUPPLEMENTARY_NOTE,
        "ci_not_computed_because": _ECE_CI_WHY,
    }


# ------------------------------------------------------------------------ the block


@dataclass(frozen=True)
class CalibrationResult:
    """The D1 ``calibration`` block, or ``None`` with its typed reason."""

    block: dict[str, Any] | None
    suppressed_reason: str | None
    score_type: str
    orientation: str

    def as_document(self) -> dict[str, Any]:
        """The two top-level document entries: the block and, when it is ``None``, the
        typed reason where D1 puts ``suppressed_reason``."""
        return {
            "calibration": self.block,
            "calibration_suppressed_reason": (
                None
                if self.suppressed_reason is None
                else {
                    "reason": self.suppressed_reason,
                    "score_type": self.score_type,
                    "orientation": self.orientation,
                }
            ),
        }


def calibration_block(
    score: Sequence[float] | np.ndarray,
    positives: Sequence[bool] | np.ndarray,
    decl: Declarations,
    *,
    cluster_ids: Sequence[Any] | np.ndarray | None = None,
    plan: ClusterPlan | None = None,
    policy: BootstrapPolicy | None = None,
    level: float = DEFAULT_LEVEL,
) -> CalibrationResult:
    """The calibration block over the analysed rows, or ``None`` with a typed reason.

    ``score`` is the raw declared score over the analysed rows (not re-oriented);
    ``positives`` the reference-positive indicator after the positive-class mapping;
    ``cluster_ids`` the case column sliced to the same rows, or ``None``. ``plan`` is
    the run-level :class:`ClusterPlan` (resolved here from the declarations and the
    ids when omitted, declared or detected - and refused when it contradicts them).
    """
    reason = suppression_reason(decl)
    if reason is not None:
        return CalibrationResult(None, reason, decl.score_type, decl.orientation)
    p = np.asarray(score, dtype=np.float64)
    pos = np.asarray(positives, dtype=bool)
    if p.shape != pos.shape or p.ndim != 1:
        raise ValueError("score and positives must be aligned one-dimensional arrays")
    if p.shape[0] and (np.any(p < 0.0) or np.any(p > 1.0) or np.any(~np.isfinite(p))):
        raise ValueError("a score declared as a probability must lie in [0, 1]")
    n = int(p.shape[0])
    ids = None if cluster_ids is None else np.asarray(cluster_ids, dtype=object)
    resolved = plan_clustering(decl.clustering_unit, ids, n)
    if plan is None:
        plan = resolved
    elif plan.clustered != resolved.clustered:
        raise ValueError(
            "the supplied ClusterPlan contradicts the case column over the analysed rows "
            f"(plan says clustered={plan.clustered}, the column says {resolved.clustered})"
        )
    clipped = np.clip(p, CLIP_EPS, 1.0 - CLIP_EPS)
    n_clipped = int(np.count_nonzero(clipped != p))
    ctx = _Ctx(
        y=pos.astype(np.float64),
        pos=pos,
        p=p,
        logit_p=np.log(clipped / (1.0 - clipped)),
        n_clipped=n_clipped,
        ids=ids,
        plan=plan,
        policy=policy if policy is not None else BootstrapPolicy(),
        level=level,
    )
    events = int(pos.sum())
    nonevents = n - events
    below = events < CURVE_MIN_EVENTS or nonevents < CURVE_MIN_EVENTS
    flag = "below_200_events_or_nonevents" if below else None
    curve_flag = None
    if below:
        curve_flag = {
            "flag": flag,
            "events": events,
            "nonevents": nonevents,
            "minimum": CURVE_MIN_EVENTS,
            "note": (
                f"fewer than {CURVE_MIN_EVENTS} events or fewer than {CURVE_MIN_EVENTS} "
                f"non-events ({CALIBRATION_CONVENTION}); the decile table, intercept, slope and "
                "O:E remain reported"
            ),
        }
        if ctx.clustered and ids is not None:
            curve_flag["event_cases"] = int(np.unique(ids[pos]).shape[0])
            curve_flag["nonevent_cases"] = int(np.unique(ids[~pos]).shape[0])
    mass_bins = equal_mass_bins(p)
    width_bins = _equal_width_rows(p)
    mass_edges = [float(p[b].min()) for b in mass_bins if b.shape[0]] + (
        [float(p[mass_bins[-1]].max())] if n else []
    )
    block: dict[str, Any] = {
        "n": n,
        "events": events,
        "nonevents": nonevents,
        "n_cases": ctx.counts().get("n_cases"),
        "clustering_route": plan.route,
        "n_clipped": n_clipped,
        "clip_eps": CLIP_EPS,
        "oe": _cell_dict(_oe_cell(ctx)),
        **{k: _cell_dict(c, d) for k, (c, d) in _irls_cells(ctx).items()},
        **{k: _cell_dict(v) for k, v in _brier_cells(ctx).items()},
        "ece_equal_width_10": _ece_entry(
            ctx, "equal_width", width_bins, [float(e) for e in np.arange(N_BINS + 1) / N_BINS]
        ),
        "ece_equal_mass_10": _ece_entry(ctx, "equal_mass", mass_bins, mass_edges),
        "decile_curve": _decile_curve(ctx, flag),
        "decile_tie_rule": (
            "ten equal-mass bins by score rank; ties placed by stable sort order (row order "
            "preserved); numpy.array_split, so the first N mod 10 bins hold one extra row"
        ),
        "curve_flag": curve_flag,
        "flags": [flag] if flag else [],
        "convention": CALIBRATION_CONVENTION,
        "suppressed_reason": None,
    }
    return CalibrationResult(block, None, decl.score_type, decl.orientation)


def calibration_from_table(
    table: Any,
    decl: Declarations,
    mask: np.ndarray,
    *,
    plan: ClusterPlan | None = None,
    cluster_ids: Sequence[Any] | np.ndarray | None = None,
    policy: BootstrapPolicy | None = None,
    level: float = DEFAULT_LEVEL,
) -> CalibrationResult:
    """:func:`calibration_block` over a validated Table's analysed rows, the arrays
    taken the way ``stats.subgroups`` takes them (positive-class mapping, the table's
    ``case_id`` column sliced with the mask when no ids are passed)."""
    mask = np.asarray(mask, dtype=bool)
    reason = suppression_reason(decl)
    if reason is not None:
        return CalibrationResult(None, reason, decl.score_type, decl.orientation)
    if table.score is None:
        raise ValueError("calibration needs a score column")
    yt = table.y_true[mask]
    pos = np.array([v == decl.positive for v in yt.tolist()], dtype=bool)
    score = np.asarray(table.score[mask], dtype=np.float64)
    if cluster_ids is None and table.case_id is not None:
        cluster_ids = table.case_id[mask]
    return calibration_block(
        score, pos, decl, cluster_ids=cluster_ids, plan=plan, policy=policy, level=level
    )
