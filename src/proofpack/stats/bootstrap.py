"""``stats.bootstrap`` - stratified and clustered resampling, and percentile intervals.

What this module is for (D1 section 3.1, R2 section 1.5): the analytic interval is
always preferred - Wilson for a proportion, DeLong for an AUROC - and the bootstrap
exists for the two cases where no valid analytic form is available:

1. **Clustered rows.** More than one row per ``case_id`` breaks the independence
   assumption both Wilson and DeLong rest on; their intervals come out too narrow,
   by roughly the square root of the design effect. Cases are resampled instead,
   all rows of a drawn case travelling together.
2. **A statistic with no standard closed form**, or a class too small for the normal
   approximation behind DeLong (R2 section 1.3: fall back to a stratified bootstrap
   when either class has fewer than ten members).

**The clustered auto-switch is objection X2 and is the reason this module exists.**
Its required behaviour, verbatim from the master plan section 5.1: *"i.i.d.: DeLong
(Sun & Xu). Clustering declared or detected: cluster bootstrap used; DeLong (and
Wilson for clustered proportions) refused with a typed reason."* Both detection
routes are implemented - ``clustering.unit: case_id`` in the customer's
declarations, and repeated ``case_id`` values observed in the data even when the
declaration says ``none``. The refusal is never swallowed: it is a typed
``not_estimable_reason`` on a companion :class:`~proofpack.stats.number.Number`
that reaches the output JSON, plus a closed-enum flag on the Number that *is*
rendered, plus (for the detected route) a :class:`~proofpack.errors.Finding` the run
carries into ``warnings``.

**The point estimate is not changed by clustering, only the interval.** A clustered
AUROC or proportion is still computed over all analysed rows, so it equals the number
the customer would get from their own table; cases with more rows therefore carry more
weight. The alternative - weighting every case equally - is a different estimand, and
choosing one for the customer would be a vendor-set analysis decision. Recorded here
as a decision, with an open question in the build day 4 handoff.

Seed policy
-----------
Explicit, because reproducibility is part of what a customer is buying.

* **B = 2000** resamples by default (:data:`DEFAULT_B`); ``bootstrap.B`` in
  ``criteria.yaml`` may raise it. R2 section 1.5, after Efron & Tibshirani's
  "at least 1000 for a percentile interval" and MedCalc's default of 1000.
* **One run seed**, taken from ``bootstrap.seed`` when the customer declares one and
  otherwise :data:`DEFAULT_SEED`. Whether it was declared or defaulted is recorded,
  so the manifest never implies the customer chose a seed they did not choose.
* **Every cell derives its own generator** from ``(run_seed, cell_key)`` -
  ``numpy.random.default_rng([run_seed, blake2b(cell_key)])``. Two consequences that
  are the whole point: a cell's interval does not depend on how many other cells the
  run computed, or in what order, so adding a subgroup cannot move an unrelated
  interval; and the derivation is a pure function of the key text, so it is identical
  across processes, platforms and Python builds. ``hashlib.blake2b`` is used rather
  than the built-in ``hash()`` precisely because ``hash()`` of a string is salted per
  process.
* **No global RNG is ever touched.** Nothing here calls ``numpy.random.seed`` or the
  legacy ``numpy.random.*`` functions; a test greps the package to keep it that way.

The **algorithm** is pinned by fixture F3: on the F3 cohort with
``numpy.random.default_rng(20240101)``, B = 2000, positives and negatives resampled
separately, the percentile AUROC interval is ``(0.44, 1.00)`` (R2 section 9). That
fixture is reproduced through the low-level entry point, which takes a Generator
directly; the cell-level entry points derive theirs as described above.

BCa is deferred to v1.1
-----------------------
Percentile intervals only in v1. BCa needs an acceleration constant from a jackknife
over resampling *units*, which under clustering means a leave-one-case-out jackknife
whose behaviour at small cluster counts we have not characterised, and the bias
correction is exactly the part a reviewer would ask us to justify. Half of it is
worse than none of it, so none of it is here: ``bootstrap.interval`` accepts only
``percentile`` in the v1 criteria schema, and :class:`BootstrapPolicy` raises on
anything else rather than quietly substituting a percentile interval. The
``bootstrap_bca`` value stays in the ``method`` enum for v1.1 and a test asserts that
no code path can emit it.

References
----------
Efron B, Tibshirani RJ. *An Introduction to the Bootstrap.* Chapman & Hall, 1993 -
B >= 1000 for percentile intervals, and the stratified/cluster resampling schemes.
**[unverified - cited from R2 section 1.5, which itself records the recommendation as
cited from memory; the book was not fetched in this build environment. Nothing here
depends on the citation: B is a declared, recorded parameter and the resampling
schemes are tested against their own definitions.]**
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from proofpack.errors import Finding
from proofpack.stats.discrimination import SMALL_CLASS, auroc_mann_whitney, auroc_number
from proofpack.stats.number import Number, not_estimable
from proofpack.stats.proportions import proportion

__all__ = [
    "DEFAULT_B",
    "DEFAULT_SEED",
    "BootstrapDraw",
    "BootstrapPolicy",
    "CellCI",
    "ClusterPlan",
    "Resampler",
    "auroc_ci",
    "bootstrap_percentile",
    "cell_entropy",
    "clustered_by_case",
    "clustered_flat",
    "percentile_bounds",
    "plan_clustering",
    "policy_from_declarations",
    "proportion_ci",
    "rng_for_cell",
    "stratified_by_outcome",
]

#: Resamples per interval. R2 section 1.5.
DEFAULT_B = 2000
#: Engine default run seed when the customer declares none. Recorded as *defaulted*.
DEFAULT_SEED = 20240101
DEFAULT_LEVEL = 0.95
#: The only interval type v1 emits. BCa is v1.1; see the module docstring.
SUPPORTED_INTERVALS = ("percentile",)
#: Below two units in a stratum every resample is identical - there is nothing to
#: estimate. A mathematical floor, not a reporting convention.
MIN_UNITS_PER_STRATUM = 2
#: Advisory only (R2 section 3.3 precision tiers); never a suppression.
LOW_PRECISION_UNITS = 10
#: A resample may be degenerate (the statistic undefined on the drawn rows). Below this
#: share of usable resamples the interval is refused rather than quietly computed from
#: whatever survived.
MIN_USABLE_FRACTION = 0.90

#: Closed enum for :attr:`CellCI.analytic_status` - what became of the analytic method
#: for this cell. Every value is rendered; there is no "unknown".
ANALYTIC_STATUS = frozenset(
    {
        "used",  # the analytic interval is the rendered one
        "refused_clustered",  # X2: rows are clustered, so it was refused; bootstrap used
        "replaced_small_class",  # R2 1.3: class < 10, bootstrap primary, analytic alongside
        "unavailable",  # the cell is degenerate; neither method has an interval
    }
)


# --------------------------------------------------------------------------- seed policy


def cell_entropy(cell_key: str) -> int:
    """Stable 64-bit entropy for a cell key.

    ``hashlib.blake2b`` rather than ``hash()``: the built-in string hash is salted per
    process, so a seed derived from it would not survive a second invocation.
    """
    return int.from_bytes(hashlib.blake2b(cell_key.encode("utf-8"), digest_size=8).digest(), "big")


def rng_for_cell(seed: int, cell_key: str) -> np.random.Generator:
    """The generator for one bootstrap cell: a pure function of ``(seed, cell_key)``."""
    return np.random.default_rng([int(seed), cell_entropy(cell_key)])


@dataclass(frozen=True)
class BootstrapPolicy:
    """B, the run seed and the interval type - recorded in the manifest and in T7."""

    n_resamples: int = DEFAULT_B
    seed: int = DEFAULT_SEED
    interval: str = "percentile"
    seed_declared: bool = False
    b_declared: bool = False

    def __post_init__(self) -> None:
        if self.interval not in SUPPORTED_INTERVALS:
            raise ValueError(
                f"bootstrap.interval {self.interval!r} is not available in v1 "
                f"(supported: {', '.join(SUPPORTED_INTERVALS)}); BCa is deferred to v1.1 "
                "and is refused rather than silently replaced by a percentile interval"
            )
        if self.n_resamples < 1:
            raise ValueError("bootstrap.B must be at least 1")

    def rng(self, cell_key: str) -> np.random.Generator:
        return rng_for_cell(self.seed, cell_key)

    def as_dict(self) -> dict[str, Any]:
        return {
            "B": self.n_resamples,
            "seed": self.seed,
            "interval": self.interval,
            "seed_source": "declared" if self.seed_declared else "engine_default",
            "b_source": "declared" if self.b_declared else "engine_default",
        }


def policy_from_declarations(declarations: Any) -> BootstrapPolicy:
    """Read ``bootstrap.{B,seed,interval}`` from a validated ``criteria.yaml`` echo."""
    block = dict(getattr(declarations, "bootstrap", None) or {})
    return BootstrapPolicy(
        n_resamples=int(block.get("B", DEFAULT_B)),
        seed=int(block.get("seed", DEFAULT_SEED)),
        interval=str(block.get("interval", "percentile")),
        seed_declared="seed" in block,
        b_declared="B" in block,
    )


# ---------------------------------------------------------------------- clustering plan


@dataclass(frozen=True)
class ClusterPlan:
    """Whether this run resamples rows or cases, and how that was decided."""

    clustered: bool
    route: str  # "none" | "declared" | "detected"
    n_rows: int
    n_units: int

    @property
    def unit(self) -> str:
        return "case_id" if self.clustered else "row"

    @property
    def rows_per_unit(self) -> float | None:
        return None if not self.n_units else self.n_rows / self.n_units

    def finding(self) -> Finding | None:
        """The warning a run must carry when clustering was *detected*, not declared."""
        if self.route != "detected":
            return None
        return Finding(
            code="W13",
            message=(
                "clustering detected from repeated case_id values although "
                "clustering.unit is 'none'; cluster resampling was used and the "
                "analytic intervals (DeLong, Wilson) were refused"
            ),
            detail={"n_rows": self.n_rows, "n_cases": self.n_units},
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "clustered": self.clustered,
            "route": self.route,
            "unit": self.unit,
            "n_rows": self.n_rows,
            "n_units": self.n_units,
        }


def plan_clustering(
    clustering_unit: str,
    cluster_ids: Sequence[Any] | np.ndarray | None,
    n_rows: int | None = None,
) -> ClusterPlan:
    """Decide the resampling unit. Both X2 routes live here.

    * **declared** - ``clustering.unit: case_id`` in ``criteria.yaml``.
    * **detected** - the declaration says ``none`` but ``case_id`` values repeat, so
      there are fewer cases than rows. The run is clustered anyway, and
      :meth:`ClusterPlan.finding` carries the discrepancy into the run's warnings.

    A declared ``case_id`` unit with no ``case_id`` column is a contradiction and
    raises, rather than quietly falling back to row resampling.
    """
    ids = None if cluster_ids is None else np.asarray(cluster_ids)
    rows = int(n_rows if n_rows is not None else (0 if ids is None else ids.shape[0]))
    if clustering_unit == "case_id":
        if ids is None:
            raise ValueError("clustering.unit is 'case_id' but no case_id column was supplied")
        return ClusterPlan(True, "declared", rows, int(np.unique(ids).shape[0]))
    if ids is not None:
        units = int(np.unique(ids).shape[0])
        if units < ids.shape[0]:
            return ClusterPlan(True, "detected", rows, units)
        return ClusterPlan(False, "none", rows, units)
    return ClusterPlan(False, "none", rows, rows)


# ----------------------------------------------------------------------------- resampler


@dataclass(frozen=True)
class _Stratum:
    """One resampling stratum: its units, and the rows each unit carries."""

    label: str
    unit_rows: tuple[np.ndarray, ...]
    matrix: np.ndarray | None  # (n_units, rows_per_unit) when every unit is the same size

    @property
    def n_units(self) -> int:
        return len(self.unit_rows)

    def draw(self, rng: np.random.Generator) -> np.ndarray:
        m = len(self.unit_rows)
        sel = rng.integers(0, m, m)
        if self.matrix is not None:
            return self.matrix[sel].ravel()
        return np.concatenate([self.unit_rows[i] for i in sel])


def _stratum(label: str, unit_rows: Sequence[np.ndarray]) -> _Stratum:
    rows = tuple(np.asarray(u, dtype=np.intp) for u in unit_rows)
    sizes = {u.shape[0] for u in rows}
    matrix = np.stack(rows) if rows and len(sizes) == 1 else None
    return _Stratum(label=label, unit_rows=rows, matrix=matrix)


@dataclass(frozen=True)
class Resampler:
    """Draws a row-index vector per resample. Deterministic given the generator.

    ``kind`` is ``"stratified"`` (rows resampled within outcome class, preserving
    prevalence) or ``"clustered"`` (cases resampled, every row of a drawn case kept).
    Both consume the generator identically - one ``rng.integers(0, m, m)`` call per
    stratum, in stratum order - which is why a clustered resampler over one-row cases
    reproduces a stratified one bit for bit.
    """

    kind: str
    strata: tuple[_Stratum, ...]
    n_rows: int

    @property
    def n_units(self) -> int:
        return sum(s.n_units for s in self.strata)

    @property
    def units_per_stratum(self) -> dict[str, int]:
        return {s.label: s.n_units for s in self.strata}

    @property
    def smallest_stratum(self) -> int:
        return min((s.n_units for s in self.strata), default=0)

    def draw(self, rng: np.random.Generator) -> np.ndarray:
        return np.concatenate([s.draw(rng) for s in self.strata])


def stratified_by_outcome(positives: np.ndarray) -> Resampler:
    """Rows resampled within outcome class, so every resample keeps the prevalence."""
    pos = np.asarray(positives, dtype=bool)
    return Resampler(
        kind="stratified",
        strata=(
            _stratum("positive", [np.array([i]) for i in np.flatnonzero(pos)]),
            _stratum("negative", [np.array([i]) for i in np.flatnonzero(~pos)]),
        ),
        n_rows=int(pos.shape[0]),
    )


def _clusters_in_first_appearance_order(cluster_ids: np.ndarray) -> list[np.ndarray]:
    """Row indices per cluster, ordered by where each cluster first appears.

    First-appearance order rather than sorted-id order: it does not depend on how the
    customer names their cases, and it makes a clustered resampler over one-row cases
    line up exactly with a stratified row resampler over the same rows.
    """
    _, first, inverse = np.unique(cluster_ids, return_index=True, return_inverse=True)
    order = np.argsort(first, kind="mergesort")
    rank = np.empty(order.shape[0], dtype=np.intp)
    rank[order] = np.arange(order.shape[0])
    keys = rank[np.asarray(inverse).ravel()]
    return [np.flatnonzero(keys == j) for j in range(order.shape[0])]


def clustered_by_case(positives: np.ndarray, cluster_ids: Sequence[Any] | np.ndarray) -> Resampler:
    """Cases resampled within outcome class; every row of a drawn case travels with it.

    A case whose rows carry both outcomes (legitimate when the unit of analysis is a
    patient with several lesions) forms its own ``mixed`` stratum rather than being
    forced into one class.
    """
    pos = np.asarray(positives, dtype=bool)
    ids = np.asarray(cluster_ids)
    if ids.shape[0] != pos.shape[0]:
        raise ValueError("cluster_ids must align with the positives mask")
    buckets: dict[str, list[np.ndarray]] = {"positive": [], "negative": [], "mixed": []}
    for rows in _clusters_in_first_appearance_order(ids):
        got = pos[rows]
        label = "positive" if got.all() else "negative" if not got.any() else "mixed"
        buckets[label].append(rows)
    strata = tuple(
        _stratum(label, buckets[label])
        for label in ("positive", "negative", "mixed")
        if buckets[label]
    )
    return Resampler(kind="clustered", strata=strata, n_rows=int(pos.shape[0]))


def clustered_flat(cluster_ids: Sequence[Any] | np.ndarray) -> Resampler:
    """Cases resampled in a single stratum - for a proportion inside one cell.

    The cell is already conditioned on the outcome (sensitivity is computed among the
    reference-positive rows), so there is no second class left to stratify on.
    """
    ids = np.asarray(cluster_ids)
    groups = _clusters_in_first_appearance_order(ids)
    return Resampler(kind="clustered", strata=(_stratum("all", groups),), n_rows=int(ids.shape[0]))


# ------------------------------------------------------------------ percentile machinery


def percentile_bounds(values: np.ndarray, level: float = DEFAULT_LEVEL) -> tuple[float, float]:
    """Percentile interval: the ``alpha/2`` and ``1 - alpha/2`` quantiles of the draws."""
    if not 0.0 < level < 1.0:
        raise ValueError("level must be in (0, 1)")
    alpha = 1.0 - level
    lo, hi = np.quantile(np.asarray(values, dtype=np.float64), [alpha / 2.0, 1.0 - alpha / 2.0])
    return float(lo), float(hi)


@dataclass(frozen=True)
class BootstrapDraw:
    """The resample distribution and the percentile interval taken from it."""

    values: np.ndarray
    ci_lo: float | None
    ci_hi: float | None
    sd: float | None
    n_requested: int
    n_usable: int
    reason: str | None = None  # a typed not-estimable reason when no interval was formed


def bootstrap_percentile(
    statistic: Callable[[np.ndarray], float],
    resampler: Resampler,
    rng: np.random.Generator,
    n_resamples: int = DEFAULT_B,
    level: float = DEFAULT_LEVEL,
) -> BootstrapDraw:
    """Run the resampler ``n_resamples`` times and take the percentile interval.

    ``statistic`` receives a row-index vector and returns a float, or ``nan`` when it
    is undefined on those rows. A degenerate resample is never silently dropped: if
    fewer than :data:`MIN_USABLE_FRACTION` of the draws are usable, the interval is
    refused with ``degenerate_resamples`` instead of being computed from the residue.
    A zero-width interval (every resample identical) is refused as
    ``boundary_estimate`` - the bootstrap genuinely cannot express uncertainty there,
    and a printed ``(1.00, 1.00)`` would claim a certainty the data do not support.
    """
    if resampler.smallest_stratum < MIN_UNITS_PER_STRATUM:
        return BootstrapDraw(
            values=np.empty(0),
            ci_lo=None,
            ci_hi=None,
            sd=None,
            n_requested=n_resamples,
            n_usable=0,
            reason=(
                "insufficient_clusters"
                if resampler.kind == "clustered"
                else "insufficient_positives"
            ),
        )
    values = np.empty(n_resamples, dtype=np.float64)
    for b in range(n_resamples):
        values[b] = statistic(resampler.draw(rng))
    usable = values[np.isfinite(values)]
    if usable.shape[0] < math.ceil(MIN_USABLE_FRACTION * n_resamples):
        return BootstrapDraw(
            values=values,
            ci_lo=None,
            ci_hi=None,
            sd=None,
            n_requested=n_resamples,
            n_usable=int(usable.shape[0]),
            reason="degenerate_resamples",
        )
    lo, hi = percentile_bounds(usable, level)
    sd = float(usable.std(ddof=1)) if usable.shape[0] > 1 else 0.0
    if lo == hi:
        return BootstrapDraw(
            values=values,
            ci_lo=None,
            ci_hi=None,
            sd=sd,
            n_requested=n_resamples,
            n_usable=int(usable.shape[0]),
            reason="boundary_estimate",
        )
    return BootstrapDraw(
        values=values,
        ci_lo=lo,
        ci_hi=hi,
        sd=sd,
        n_requested=n_resamples,
        n_usable=int(usable.shape[0]),
    )


# ------------------------------------------------------------------------------ the cell


@dataclass(frozen=True)
class CellCI:
    """One cell's rendered Number, plus what became of the analytic method.

    ``analytic_status`` is the audit trail X2 asks for. When it is
    ``refused_clustered``, ``analytic`` is a Number with no interval carrying the typed
    reason ``clustered_data_analytic_ci_invalid`` - the refusal is a value in the
    output JSON, not a log line and not a swallowed exception.
    """

    number: Number
    analytic: Number | None
    analytic_status: str
    cell_key: str
    route: str
    policy: BootstrapPolicy | None = None
    n_usable: int = 0
    resample_sd: float | None = None

    def __post_init__(self) -> None:
        if self.analytic_status not in ANALYTIC_STATUS:
            raise ValueError(f"unknown analytic_status {self.analytic_status!r}")

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "number": self.number.as_dict(),
            "analytic": None if self.analytic is None else self.analytic.as_dict(),
            "analytic_status": self.analytic_status,
            "clustering_route": self.route,
            "bootstrap": None,
        }
        if self.policy is not None:
            out["bootstrap"] = {
                "cell_key": self.cell_key,
                "usable_resamples": self.n_usable,
                "resample_sd": self.resample_sd,
                **self.policy.as_dict(),
            }
        return out


def _resolved(
    policy: BootstrapPolicy | None, plan: ClusterPlan | None, n_rows: int
) -> tuple[BootstrapPolicy, ClusterPlan]:
    return (
        policy if policy is not None else BootstrapPolicy(),
        plan if plan is not None else ClusterPlan(False, "none", n_rows, n_rows),
    )


def _number_from_draw(
    draw: BootstrapDraw,
    *,
    est: float,
    method: str,
    level: float,
    flags: list[str],
    **counts: Any,
) -> Number:
    """A Number from a completed draw, or a typed refusal carrying the same counts."""
    if draw.reason is not None:
        return not_estimable(draw.reason, est=est, ci_level=level, flags=list(flags), **counts)
    return Number(
        est=est,
        ci_lo=draw.ci_lo,
        ci_hi=draw.ci_hi,
        ci_level=level,
        method=method,
        flags=list(flags),
        **counts,
    ).with_precision_flags()


def auroc_ci(
    scores: np.ndarray,
    positives: np.ndarray,
    *,
    cell_key: str,
    policy: BootstrapPolicy | None = None,
    plan: ClusterPlan | None = None,
    cluster_ids: Sequence[Any] | np.ndarray | None = None,
    level: float = DEFAULT_LEVEL,
) -> CellCI:
    """The rendered AUROC for one cell, with the interval the data actually permit.

    Routing, in order:

    * **clustered** (declared or detected) - cases resampled within outcome class;
      DeLong refused with ``clustered_data_analytic_ci_invalid`` and the flag
      ``delong_refused_clustered`` on the rendered Number (X2).
    * **i.i.d., both classes at least 10** - DeLong, exactly as build day 3 computes
      it. No bootstrap: R2 section 1.5 says never bootstrap where the analytic form
      is standard.
    * **i.i.d., a class below 10** - stratified bootstrap as the rendered interval
      (R2 section 1.3), with the DeLong Number carried alongside as ``analytic`` and
      the switch recorded in ``method`` and in the flag
      ``analytic_ci_replaced_small_class``. Nothing is hidden and nothing is silent.
    """
    scores = np.asarray(scores, dtype=np.float64)
    pos = np.asarray(positives, dtype=bool)
    pol, cplan = _resolved(policy, plan, int(pos.shape[0]))
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())

    if n_pos == 0 or n_neg == 0:
        empty = not_estimable("single_class", n_pos=n_pos, n_neg=n_neg, ci_level=level)
        return CellCI(empty, empty, "unavailable", cell_key, cplan.route)

    point = auroc_mann_whitney(scores, pos)

    def statistic(idx: np.ndarray) -> float:
        got = pos[idx]
        if not got.any() or got.all():
            return float("nan")
        return auroc_mann_whitney(scores[idx], got)

    if cplan.clustered:
        if cluster_ids is None:
            raise ValueError("a clustered plan needs cluster_ids")
        resampler = clustered_by_case(pos, cluster_ids)
        draw = bootstrap_percentile(statistic, resampler, pol.rng(cell_key), pol.n_resamples, level)
        refused = not_estimable(
            "clustered_data_analytic_ci_invalid",
            est=point,
            n_pos=n_pos,
            n_neg=n_neg,
            n_cases=cplan.n_units,
            ci_level=level,
        )
        flags = ["delong_refused_clustered"]
        if resampler.smallest_stratum < LOW_PRECISION_UNITS:
            flags.append("very_low_precision")
        number = _number_from_draw(
            draw,
            est=point,
            method="cluster_bootstrap_percentile",
            level=level,
            flags=flags,
            n_pos=n_pos,
            n_neg=n_neg,
            n_cases=cplan.n_units,
        )
        return CellCI(
            number,
            refused,
            "refused_clustered",
            cell_key,
            cplan.route,
            pol,
            draw.n_usable,
            draw.sd,
        )

    analytic = auroc_number(scores, pos, level=level).auroc
    if min(n_pos, n_neg) >= SMALL_CLASS:
        return CellCI(analytic, analytic, "used", cell_key, cplan.route)

    resampler = stratified_by_outcome(pos)
    draw = bootstrap_percentile(statistic, resampler, pol.rng(cell_key), pol.n_resamples, level)
    number = _number_from_draw(
        draw,
        est=point,
        method="bootstrap_percentile",
        level=level,
        flags=["analytic_ci_replaced_small_class", "very_low_precision"],
        n_pos=n_pos,
        n_neg=n_neg,
    )
    return CellCI(
        number, analytic, "replaced_small_class", cell_key, cplan.route, pol, draw.n_usable, draw.sd
    )


def proportion_ci(
    indicator: np.ndarray,
    *,
    cell_key: str,
    policy: BootstrapPolicy | None = None,
    plan: ClusterPlan | None = None,
    cluster_ids: Sequence[Any] | np.ndarray | None = None,
    level: float = DEFAULT_LEVEL,
) -> CellCI:
    """One proportion (sensitivity, specificity, accuracy, ...) for one cell.

    ``indicator`` is the boolean success vector over the rows of the cell, so the cell
    is already conditioned: for sensitivity these are the reference-positive rows and
    the indicator is "predicted positive".

    * **i.i.d.** - Wilson, unchanged from build day 2. No bootstrap.
    * **clustered** - cases resampled; **Wilson refused** with
      ``clustered_data_analytic_ci_invalid`` and the flag ``wilson_refused_clustered``
      on the rendered Number (X2).
    """
    ind = np.asarray(indicator, dtype=bool)
    pol, cplan = _resolved(policy, plan, int(ind.shape[0]))
    n = int(ind.shape[0])
    k = int(ind.sum())

    if n == 0:
        empty = not_estimable("zero_denominator", n=0, k=0, ci_level=level)
        return CellCI(empty, empty, "unavailable", cell_key, cplan.route)

    if not cplan.clustered:
        number = proportion(k, n, level=level).with_precision_flags()
        return CellCI(number, number, "used", cell_key, cplan.route)

    if cluster_ids is None:
        raise ValueError("a clustered plan needs cluster_ids")
    resampler = clustered_flat(cluster_ids)

    def statistic(idx: np.ndarray) -> float:
        return float(ind[idx].mean())

    draw = bootstrap_percentile(statistic, resampler, pol.rng(cell_key), pol.n_resamples, level)
    refused = not_estimable(
        "clustered_data_analytic_ci_invalid", est=k / n, n=n, k=k, ci_level=level
    )
    flags = ["wilson_refused_clustered"]
    if resampler.smallest_stratum < LOW_PRECISION_UNITS:
        flags.append("very_low_precision")
    number = _number_from_draw(
        draw,
        est=k / n,
        method="cluster_bootstrap_percentile",
        level=level,
        flags=flags,
        n=n,
        k=k,
    )
    return CellCI(
        number, refused, "refused_clustered", cell_key, cplan.route, pol, draw.n_usable, draw.sd
    )
