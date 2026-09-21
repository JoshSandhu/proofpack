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

**What the guard checks.** Four things, each named because naming them is the only way a
reader can tell what is left over. Every one of them is checked in :func:`_resolved`,
which every cell function calls before it routes or returns anything, so no early
return for a single-class or zero-row cell can skip one. A clustered plan with no
``cluster_ids`` raises; a plan asserting independence over ``cluster_ids`` that repeat
raises; ``cluster_ids`` passed with no plan at all are *detected*, not ignored; and
``cluster_ids`` that are not **a one-dimensional column of exactly one id per analysed
row** raise - wrong rank or wrong length, too many or too few - because an array that
does not correspond row-for-row with the data cannot say which row belongs to which case.

Each of those was closed by a different round finding it open. The third came from the
verify note of 2026-09-10. The length half of the fourth came from the round-4
reconciliation: until then 200 case ids beside 400 analysed rows produced
``ClusterPlan(clustered=False, route='none', n_rows=400, n_units=200)`` - a plan
asserting independence whose own ``rows_per_unit`` read 2.0 - and then DeLong or Wilson
on clustered rows, with ``analytic_status: used`` and no flag anywhere in the output.
The rank half, and the "checked in ``_resolved``" clause, came from the round-7 fresh
attack: the check tested ``ids.shape[0]`` while its docstring stated an invariant about
row-for-row correspondence, so a ``(400, 2)`` composite case key satisfied it and
rendered ``delong_wald`` ``(0.6488, 0.7510)`` and ``wilson`` ``(0.6020, 0.6951)`` over
400 rows from 200 patients - 1.387 and 1.370 times narrower than the cluster bootstrap
on the same rows, ``flags == []`` on both; and the first of the four was raised in the
cell functions *after* their degenerate-cell early returns, so a single-class or empty
cell with a clustered plan and no ids returned ``unavailable`` and no error at all.

Measured in the round-7 session with an independent DeLong (placement-value form) and an
independent within-class cluster bootstrap, 200 replications at 200 patients and two
lesions each, within-patient score correlation 0.9, the label constant within patient and
a true AUROC of ``Phi(1/sqrt(2)) = 0.760``: at B = 2000 the analytic interval this guard
keeps off clustered rows covered 0.855 of the time against a nominal 0.95, where the
cluster bootstrap covered 0.950; mean widths 0.0919 and 0.1253, a factor of 1.363. At
B = 1000 the same script gave 0.765 and 0.890, so the bootstrap's own coverage depends on
B and is not claimed to be exact - the comparison between the two is the claim.

**What the guard does not check, and cannot.** When ``cluster_ids`` is **not passed at
all** there is no evidence of clustering in this module's inputs, and the analytic
interval is rendered. Nothing below this line can detect a case column it was never
given; that has to come from the caller that reads the customer's table, on every cell.
``test_cluster_ids_never_passed_at_all_are_still_invisible_to_this_module`` pins the
hole so this paragraph cannot quietly stop being true.

That caller has **three** surfaces to carry, not one. Besides the cells routed here,
:func:`proofpack.stats.discrimination.paired_delong` - the version-comparison statistic
the PCCP report rests on - and
:func:`proofpack.stats.proportions.two_by_two_metrics` - every operating-point
proportion - take no ``cluster_ids`` argument at all, reach no guard, and emit DeLong,
Wilson and Newcombe intervals over whatever rows they are handed. Nothing in ``src``
calls either yet. ``test_the_surfaces_no_clustering_guard_covers_are_named_where_they_live``
pins that, and each of those two functions says it in its own docstring.

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
  legacy ``numpy.random.*`` functions; a test *parses* the package to keep it that
  way - attribute chains and ``from numpy.random import ...`` alike.

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
from collections.abc import Callable, Iterable, Sequence
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
    "auroc_precision_flags",
    "bootstrap_percentile",
    "cell_entropy",
    "clustered_by_case",
    "clustered_flat",
    "percentile_bounds",
    "precision_flags",
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
#: How a :class:`ClusterPlan` was arrived at, and - because ``none`` means the rows are
#: independent - the clustering decision itself. Closed, and validated at construction.
CLUSTER_ROUTES = ("none", "declared", "detected")
#: Below two independent units supplying an outcome class, that class contributes the
#: same rows to every resample and the interval would carry no uncertainty about it.
#: A mathematical floor, not a reporting convention - and it is a floor on the units
#: the resampler can actually *vary*, which is neither ``min`` nor ``sum`` over the
#: resampler's internal strata. Not ``min``: a single mixed-outcome case must not veto a
#: cohort of two hundred (verify note, 2026-09-10, statistics B2 / safety B3). Not
#: ``sum`` either: one pure case plus one mixed case sum to two and draw the same rows
#: every time (re-verify note, 2026-09-10, fresh-attack FA-B1). See
#: :attr:`Resampler.deficient_class`, which applies it to the largest stratum supplying
#: the class.
#:
#: **DEC-08 coverage bar (build day 5, ``scripts/coverage_bar.py`` v1, seed 20260915,
#: R = 400 cohorts, B = 1000, nominal 0.95, bar 0.90): this constant does NOT meet the
#: bar, and was not changed.** Measured on a positive class resting on ``u`` pure-positive
#: cases of three rows and nothing else (30 / 120 negative cases), the percentile
#: interval covered the truth at u = 2 / 3 / 4 / 5 in 0.715 / 0.787 / 0.815 / 0.870 and
#: 0.620 / 0.715 / 0.810 / 0.795 of cohorts; on a clustered proportion cell of ``u``
#: cases at p = 0.5 in 0.505 / 0.762 / 0.870 / 0.940 (u = 2..5) and 0.975 (u = 10), but
#: at p = 0.9 in 0.190 / 0.237 / 0.347 / 0.407 (u = 2..5), 0.672 (u = 10), 0.850 (u = 20)
#: and 0.922 (u = 40) with one row per case. No value of this constant on the grid
#: renders only shapes at or above the bar: the shortfall is the percentile bootstrap's
#: own behaviour at few units and near a boundary proportion, and a floor high enough to
#: clear it (above 40 units at p = 0.9) would refuse fixture F3 (five positives, R2
#: section 9) and most of the R2 section 1.3 small-class route. The shapes below the bar
#: all carry the R2 section 3.3 tier ("not evaluable, shown for transparency" below 10
#: units, "very low precision" below 30); what to do about the 10-40 unit range at high
#: proportions is a decision for Josh, recorded in the day-5 note, not a constant changed
#: here. Full table: ``design/conventions_T7.md``.
MIN_UNITS_PER_STRATUM = 2
#: The other half of the same floor, and the quantitative one. A stratum of one unit is
#: frozen whatever the *other* strata do, so a class can clear
#: :data:`MIN_UNITS_PER_STRATUM` and still have most of its rows identical in every
#: resample - one patient with five malignant lesions beside two mixed patients freezes
#: 71 % of the positive rows, and the interval the module rendered there was 2.1x too
#: narrow, covering the truth 34-62 % of the time at a nominal 95 % (re-verify note,
#: 2026-09-10, fresh-attack FA2-B1).
#:
#: The quantity is exact rather than fitted. The resampled spread of a row-weighted
#: statistic over independent units of weight ``w_j`` goes as ``sum w_j**2``; freezing a
#: stratum deletes its units from that sum, so
#: ``sum_frozen w**2 / sum_all w**2`` is the share of that class's resampling variance
#: the interval cannot see, and the interval's standard deviation is understated by at
#: most ``1 - sqrt(1 - share)``. At one fifth that is a tenth of the class's standard
#: error, which is the most a nominal 95 % interval may knowingly be short by and still
#: be the interval the pack claims. Above it the cell is refused, not annotated: an
#: annotation cannot make a too-narrow interval true.
#:
#: It is an **upper** bound on the cost - the AUROC's other class still contributes
#: variance - which is why it is safe to refuse on. ``test_the_frozen_variance_share_
#: bounds_what_the_freeze_costs`` measures the bound against a matched split control
#: rather than taking it on trust. Both existing multi-lesion fixtures pass it: 199 pure
#: cases beside one mixed case freeze 1/397 of the positive variance weight, and forty
#: all-mixed cases freeze none.
#:
#: **DEC-08 coverage bar (build day 5, ``scripts/coverage_bar.py`` v1, seed 20260915,
#: R = 400 cohorts, B = 1000, nominal 0.95, bar 0.90).** Measured on AUROC cells whose
#: positive class rests on one frozen pure-positive case of three rows beside ``m`` mixed
#: cases, the interval covered the truth at a frozen share of 0.05 / 0.10 / 0.20 in
#: 0.912 / 0.943 / 0.932 of cohorts (30 negative cases) and 0.958 / 0.935 / 0.915 (120
#: negative cases); at 0.30 / 0.41 / 0.50 in 0.863 / 0.877 / 0.843 and 0.873 / 0.823 /
#: 0.770. The rule refuses at ``frozen >= MAX_FROZEN_VARIANCE_SHARE``, so with the
#: constant at 0.20 the shapes it **renders** are 0.05 and 0.10 (both at or above the
#: bar in the recorded run) and the share-0.20 shape (m = 36, 9/45 exactly) is the first
#: shape it **refuses** - a shape measured eight times (N = 30 / N = 120) at 0.932 /
#: 0.915 (recorded run, R = 400), 0.900 / 0.870 (``--quick``, R = 100), and at seed
#: 20260916 (R = 200, B = 500) 0.925 / 0.915 with a fresh generator per cell and
#: 0.880 / 0.915 with one generator shared across the cells: two of eight cells below
#: the bar, so the shape sits near the bar rather than above it. The next refused shape,
#: 0.30, straddles the bar across seeds too: 0.863 / 0.873 in the recorded run, 0.930 /
#: 0.915 at the lens's seed 7 and 0.910 / 0.890 at seed 20260916. The spread is about
#: two and a half Monte-Carlo standard errors (0.015 at R = 400, 0.021 at R = 200). The
#: day-4 value is **kept** as the conservative choice at this boundary: it refuses a
#: shape whose measurements fall on both sides of the bar, and was not loosened to 0.30
#: because that shape's measurements do too. Recorded in the day-5 lens notes (lens 1
#: FA-N1; lens 2 FA-N2 and RG-N1) and repair notes; the full table is in
#: ``design/conventions_T7.md``. This is a measurement on the grid's shapes, not a
#: guarantee.
MAX_FROZEN_VARIANCE_SHARE = 0.20
#: R2 section 3.3 precision tiers, measured in **resampling units** - cases when the
#: rows are clustered, rows when they are not. Advisory only; never a suppression.
#: Below :data:`LOW_PRECISION_UNITS` the tier is "not evaluable, shown for
#: transparency"; below :data:`VERY_LOW_PRECISION_UNITS`, or with fewer than
#: :data:`FEW_EVENTS` units carrying the event, it is "very low precision".
LOW_PRECISION_UNITS = 10
VERY_LOW_PRECISION_UNITS = 30
FEW_EVENTS = 5
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


def precision_flags(n_units: int, n_events: int | None = None) -> list[str]:
    """The R2 section 3.3 tier for a cell of ``n_units`` independent units.

    Exactly the two tiers R2 defines, in the order R2 defines them: ``n < 10`` is *not
    evaluable, shown for transparency* (the more severe label, which the module
    previously never emitted), ``10 <= n < 30`` or fewer than five events is *very low
    precision*. Counted over the cell, because that is the evidence a reviewer is
    judging - not over the smallest internal resampling stratum, which is bookkeeping.
    """
    if n_units < LOW_PRECISION_UNITS:
        return ["not_evaluable_shown_for_transparency"]
    if n_units < VERY_LOW_PRECISION_UNITS or (n_events is not None and n_events < FEW_EVENTS):
        return ["very_low_precision"]
    return []


def auroc_precision_flags(n_units: int, class_units: Iterable[int]) -> list[str]:
    """The R2 section 3.3 tier for an AUROC cell, which needs **both** classes.

    One definition of "a scarce class" for both AUROC routes. The clustered branch
    counts cases and the i.i.d. branch counts rows, but the question is the same in
    both: is *either* class below :data:`LOW_PRECISION_UNITS`? R2 section 3.3 asks for
    at least ten positives and at least ten negatives before an AUROC per group is
    evaluable, so reading only the positives - which the module did between commits
    5b92fc5 and this one - loses the tier on exactly the cells R2 is strictest about:
    an AUROC of 0.97 resting on four negative patients rendered with no tier at all
    (re-verify note, 2026-09-10, regression R1 / fresh-attack FA-B2 and FA-N6).

    ProofPack annotates rather than omits, so the shortage is a tier, never a
    suppression; and it stays at *very low precision* rather than escalating, which is
    what the module emitted before the round-1 repair.
    """
    scarcest = min(class_units, default=0)
    tier = precision_flags(n_units, scarcest)
    if not tier and scarcest < LOW_PRECISION_UNITS:
        return ["very_low_precision"]
    return tier


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
        if self.seed < 0:
            # numpy would raise "expected non-negative integer" on the first cell, half
            # way through a run; refuse the declaration instead.
            raise ValueError(f"bootstrap.seed must not be negative (got {self.seed})")

    def rng(self, cell_key: str) -> np.random.Generator:
        return rng_for_cell(self.seed, cell_key)

    def as_dict(self) -> dict[str, Any]:
        """The manifest block. T7 must state the methods actually used (D1 section 9).

        ``thresholds`` carries the engine constants that decide whether a cell is
        estimable and which precision tier it carries. They are not customer-declarable
        and they are not acceptance criteria; they are method parameters, and a reviewer
        cannot check the refusals without seeing them.
        """
        return {
            "B": self.n_resamples,
            "seed": self.seed,
            "interval": self.interval,
            "seed_source": "declared" if self.seed_declared else "engine_default",
            "b_source": "declared" if self.b_declared else "engine_default",
            "thresholds": {
                # named for what the rule measures. "min_units_per_class" was the
                # round-1 rule, deleted in round 2 and still published in round 2's
                # manifest beside cells it did not decide (re-verify note, FA2-B2).
                "min_units_per_class_stratum": MIN_UNITS_PER_STRATUM,
                "max_frozen_variance_share": MAX_FROZEN_VARIANCE_SHARE,
                "min_usable_fraction": MIN_USABLE_FRACTION,
                "low_precision_units": LOW_PRECISION_UNITS,
                "very_low_precision_units": VERY_LOW_PRECISION_UNITS,
                "small_class": SMALL_CLASS,
            },
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
    """Whether this run resamples rows or cases, and how that was decided.

    The four fields are not independent, and every way they can contradict each other is
    refused at construction rather than at the call sites that might build one:

    * ``route`` is one of three values, and it *is* the clustering decision - ``none``
      means the rows are independent, ``declared`` and ``detected`` mean they are not -
      so :attr:`clustered` is not free to disagree with it;
    * ``clustered=False`` means one row per unit, so an independent plan over a different
      number of rows than units is self-contradictory;
    * ``detected`` means case ids were *seen to repeat*, which is fewer cases than rows;
    * and no plan can have more cases than the rows they were counted from.

    The second of those was added by the round-4 reconciliation, which found the module
    producing ``ClusterPlan(clustered=False, route='none', n_rows=400, n_units=200)``,
    whose own :attr:`rows_per_unit` reported 2.0, and routing it to DeLong. The other
    three were added by the round-7 fresh attack, which found that validating one of the
    contradictions left the rest reachable: ``ClusterPlan(False, 'detected', 400, 400)``
    constructed, routed the cell to ``delong_wald`` with ``analytic_status: used``, and
    emitted a W13 saying "cluster resampling was used and the analytic intervals (DeLong,
    Wilson) were refused" - a false sentence about the run, in the warnings a regulator
    reads. Its mirror, ``ClusterPlan(True, 'none', 400, 200)``, resampled cases correctly
    and carried no W13 at all.
    """

    clustered: bool
    route: str  # "none" | "declared" | "detected"
    n_rows: int
    n_units: int

    def __post_init__(self) -> None:
        if self.route not in CLUSTER_ROUTES:
            raise ValueError(f"unknown clustering route {self.route!r}; one of {CLUSTER_ROUTES}")
        if self.n_rows < 0 or self.n_units < 0:
            raise ValueError(
                f"a plan counts rows and cases, neither of which can be negative "
                f"({self.n_units} units over {self.n_rows} rows)"
            )
        if self.clustered != (self.route != "none"):
            raise ValueError(
                "a plan's route is its clustering decision and the flag cannot disagree "
                f"with it (clustered={self.clustered}, route={self.route!r})"
            )
        if not self.clustered and self.n_units != self.n_rows:
            raise ValueError(
                "a plan asserting the rows are independent must have one unit per row "
                f"({self.n_units} units over {self.n_rows} rows)"
            )
        if self.n_units > self.n_rows:
            raise ValueError(
                "a plan cannot have more cases than the rows they were counted from "
                f"({self.n_units} units over {self.n_rows} rows)"
            )
        if self.route == "detected" and self.n_units >= self.n_rows:
            raise ValueError(
                "'detected' means case ids were seen to repeat, so it needs fewer cases "
                f"than rows ({self.n_units} units over {self.n_rows} rows)"
            )

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


def _case_column(cluster_ids: Sequence[Any] | np.ndarray, n_rows: int | None = None) -> np.ndarray:
    """``cluster_ids`` as a case column, or a refusal. The only asarray in this module.

    ``cluster_ids[i]`` is the case of row ``i``. That invariant needs two things, and
    round 4 checked only the second of them:

    * **one id per row**, so a *one-dimensional* array. A composite case key - the
      two-column selection a pandas caller reaches for first - is ``(n_rows, 2)``, which
      has ``n_rows`` in ``shape[0]`` and no row-to-case correspondence whatsoever. It
      satisfied a length check and rendered DeLong on clustered rows: measured at ace5cf5
      over 200 patients with two lesions each, ``(0.6488, 0.7510)`` where the case column
      gives ``(0.6279, 0.7696)``, 1.387 times too narrow, with ``flags == []``. The rank
      of the array is refused rather than flattened, because flattening invents a
      correspondence the caller did not supply;
    * **exactly ``n_rows`` of them** when the row count is known. An array of a different
      length carries no correspondence in either direction: there is no row ``i`` for a
      surplus id, and no id for a surplus row.

    Both are refused rather than interpreted, because every interpretation - resample the
    prefix, ravel the columns, treat the count as the case count - answers a question
    about a row set that is not the one being reported on. A scalar used to fall off the
    end of ``shape`` with ``IndexError``; it is now refused deliberately, like the rest.
    """
    ids = np.asarray(cluster_ids)
    if ids.ndim != 1:
        raise ValueError(
            "cluster_ids must be a one-dimensional case column, one id per row "
            f"(got an array of shape {ids.shape}); a composite key has to be reduced to "
            "a single id per row before it is passed, not flattened here"
        )
    if n_rows is not None and ids.shape[0] != n_rows:
        raise ValueError(
            "cluster_ids must align row-for-row with the analysed rows "
            f"({ids.shape[0]} ids against {n_rows} rows)"
        )
    return ids


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
    raises, rather than quietly falling back to row resampling. So does any
    ``cluster_ids`` that is not a case column over these rows - see :func:`_case_column`,
    which is where both halves of that are decided. With ``n_rows`` omitted there is no
    second quantity to check the length against and the ids *are* the rows, which is the
    two-argument run-level form; the *shape* is checked in both forms, because a
    ``(n, 2)`` array is not one id per row whether or not a row count was supplied.

    The detection rule is ``units < rows``, the rule this docstring states. It read
    ``units < ids.shape[0]`` until the round-4 reconciliation, which is the same
    comparison only while the two lengths agree - and the three-argument form
    :func:`_resolved` uses on every cell is exactly where they may not.
    """
    ids = None if cluster_ids is None else _case_column(cluster_ids, n_rows)
    rows = int(n_rows if n_rows is not None else (0 if ids is None else ids.shape[0]))
    if clustering_unit == "case_id":
        if ids is None:
            raise ValueError("clustering.unit is 'case_id' but no case_id column was supplied")
        return ClusterPlan(True, "declared", rows, int(np.unique(ids).shape[0]))
    if ids is not None:
        units = int(np.unique(ids).shape[0])
        if units < rows:
            return ClusterPlan(True, "detected", rows, units)
        return ClusterPlan(False, "none", rows, units)
    return ClusterPlan(False, "none", rows, rows)


# ----------------------------------------------------------------------------- resampler


@dataclass(frozen=True)
class _Stratum:
    """One resampling stratum: its units, and the rows each unit carries.

    ``class_unit_rows`` is how many rows of each outcome class each unit contributes,
    in unit order - the weights :attr:`Resampler.frozen_variance_share` is measured on.
    A ``mixed`` unit appears in both entries, which is the whole point of it.
    """

    label: str
    unit_rows: tuple[np.ndarray, ...]
    matrix: np.ndarray | None  # (n_units, rows_per_unit) when every unit is the same size
    class_unit_rows: dict[str, tuple[int, ...]]

    @property
    def n_units(self) -> int:
        return len(self.unit_rows)

    @property
    def frozen(self) -> bool:
        """A stratum of one unit draws that unit every time, so its rows never vary."""
        return self.n_units == 1

    def draw(self, rng: np.random.Generator) -> np.ndarray:
        m = len(self.unit_rows)
        sel = rng.integers(0, m, m)
        if self.matrix is not None:
            return self.matrix[sel].ravel()
        return np.concatenate([self.unit_rows[i] for i in sel])


def _stratum(
    label: str, unit_rows: Sequence[np.ndarray], positives: np.ndarray | None = None
) -> _Stratum:
    """Build a stratum. ``positives`` splits each unit's rows by outcome class.

    Without it the stratum is not conditioned on an outcome (:func:`clustered_flat`),
    so its rows all belong to the single class ``all``.
    """
    rows = tuple(np.asarray(u, dtype=np.intp) for u in unit_rows)
    sizes = {u.shape[0] for u in rows}
    matrix = np.stack(rows) if rows and len(sizes) == 1 else None
    if positives is None:
        per_unit = {"all": tuple(int(u.shape[0]) for u in rows)}
    else:
        pos = np.asarray(positives, dtype=bool)
        n_pos = tuple(int(pos[u].sum()) for u in rows)
        per_unit = {
            "positive": n_pos,
            "negative": tuple(int(u.shape[0]) - k for u, k in zip(rows, n_pos, strict=True)),
        }
    return _Stratum(label=label, unit_rows=rows, matrix=matrix, class_unit_rows=per_unit)


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
        """Diagnostic only. Neither the refusal criterion (:attr:`deficient_class`) nor
        the precision tier (:attr:`class_units`) is measured on it: it was, and one
        multi-lesion patient could then delete a two-hundred-patient interval."""
        return min((s.n_units for s in self.strata), default=0)

    @property
    def class_strata(self) -> dict[str, tuple[int, ...]]:
        """Per outcome class, the unit count of every stratum that can supply its rows.

        A ``mixed`` cluster carries rows of *both* outcomes, so it appears under both:
        it is a fully informative unit, not a shortage. Kept as the separate stratum
        counts rather than a single total because the two questions the module asks of
        them have different answers - see :attr:`class_units` and
        :attr:`deficient_class`.
        """
        sizes = {s.label: s.n_units for s in self.strata}
        if "all" in sizes:
            return {"all": (sizes["all"],)}
        mixed = sizes.get("mixed", 0)
        return {
            "positive": (sizes.get("positive", 0), mixed),
            "negative": (sizes.get("negative", 0), mixed),
        }

    @property
    def class_units(self) -> dict[str, int]:
        """Independent units able to supply rows of each outcome class.

        The *reported* count, and the one the precision tier is measured against.
        ``min`` over the strata is not that quantity: it let one multi-lesion patient
        with one benign and one malignant lesion - the case the ``mixed`` stratum
        exists for - delete the interval of a two-hundred-patient study.
        """
        return {label: sum(parts) for label, parts in self.class_strata.items()}

    @property
    def frozen_variance_share(self) -> dict[str, float]:
        """Per class, the share of its resampling variance weight the freeze destroys.

        The variance of a row-weighted statistic over independent units of weight
        ``w_j`` goes as ``sum w_j**2``, and a stratum of one unit is drawn one-from-one,
        so its units never enter that sum. The ratio is therefore the share of the
        class's resampling variance the interval cannot see - exact under the standard
        model, and an upper bound on what the interval loses, because for an AUROC the
        other class still varies. See :data:`MAX_FROZEN_VARIANCE_SHARE`.
        """
        total: dict[str, float] = {}
        frozen: dict[str, float] = {}
        for stratum in self.strata:
            for label, counts in stratum.class_unit_rows.items():
                weight = float(sum(c * c for c in counts))
                total[label] = total.get(label, 0.0) + weight
                if stratum.frozen:
                    frozen[label] = frozen.get(label, 0.0) + weight
        return {
            label: (frozen.get(label, 0.0) / weight if weight else 0.0)
            for label, weight in total.items()
        }

    def describe(self) -> dict[str, Any]:
        """The quantities the refusal rule is measured on, for the manifest.

        A reviewer cannot check a refusal without the number that decided it (D1
        section 9). Round 2 printed ``insufficient_clusters`` beside ``n_cases: 202``
        and published a threshold the rule no longer used, so the pack contradicted the
        refusal it was meant to explain (re-verify note, 2026-09-10, fresh-attack
        FA2-B2). Unit counts and shares only: nothing row-level is carried here.
        """
        return {
            "kind": self.kind,
            "units_per_stratum": self.units_per_stratum,
            "class_strata": {label: list(parts) for label, parts in self.class_strata.items()},
            "class_units": self.class_units,
            "frozen_variance_share": {
                label: round(share, 6) for label, share in self.frozen_variance_share.items()
            },
            "deficient_class": self.deficient_class,
        }

    @property
    def deficient_class(self) -> str | None:
        """The class this resampler cannot vary, or ``None``.

        Not the same question as :attr:`class_units`, and conflating them was a defect.
        Each stratum is drawn independently, ``m`` units from ``m``; a stratum holding
        a single unit therefore contributes *that unit* to every resample. So a class
        is deficient when its **largest** contributing stratum is below
        :data:`MIN_UNITS_PER_STRATUM`, not when the units summed across its strata are:
        strata ``{positive: 1, mixed: 1, negative: 60}`` count two positive units and
        vary in none of them, and the interval the round-1 code rendered there covered
        the truth 23 % of the time at a nominal 95 % (re-verify note, 2026-09-10,
        fresh-attack FA-B1). A class whose units are split one-and-one across the pure
        and the mixed stratum satisfies the count and violates the reason for it.

        That is the qualitative half. It refuses a class the resampler cannot vary *at
        all*, and it is blind to a class the resampler can barely vary: strata
        ``{positive: 1, mixed: 2, negative: 40}`` clear it while the single pure case
        contributes its five malignant lesions - 71 % of the positive rows - to every
        resample, and the interval rendered there was 2.1x too narrow (re-verify note,
        2026-09-10, fresh-attack FA2-B1). So the second, quantitative half:
        :attr:`frozen_variance_share` against :data:`MAX_FROZEN_VARIANCE_SHARE`. It
        subsumes the first - a class every stratum of which is a singleton has a frozen
        share of exactly 1 - and the first is kept because it is exact where the class
        has no rows at all, and because it is the half a reader checks by counting.

        The scarcest class wins when both are short, so the reported reason names the
        column the customer would actually have to add to.
        """
        counts = self.class_units
        strata = self.class_strata
        frozen = self.frozen_variance_share
        short = [
            (counts[label], rank, label)
            for rank, label in enumerate(("positive", "negative", "all"))
            if label in strata
            and (
                max(strata[label]) < MIN_UNITS_PER_STRATUM
                or frozen.get(label, 0.0) >= MAX_FROZEN_VARIANCE_SHARE
            )
        ]
        return min(short)[2] if short else None

    def draw(self, rng: np.random.Generator) -> np.ndarray:
        return np.concatenate([s.draw(rng) for s in self.strata])


def stratified_by_outcome(positives: np.ndarray) -> Resampler:
    """Rows resampled within outcome class, so every resample keeps the prevalence."""
    pos = np.asarray(positives, dtype=bool)
    return Resampler(
        kind="stratified",
        strata=(
            _stratum("positive", [np.array([i]) for i in np.flatnonzero(pos)], pos),
            _stratum("negative", [np.array([i]) for i in np.flatnonzero(~pos)], pos),
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

    Public, and so it validates its own ``cluster_ids`` through :func:`_case_column`
    rather than trusting the cell functions to have done it: a ``(n, 2)`` array reached
    here would be unique-d over both columns and index rows that do not exist.
    """
    pos = np.asarray(positives, dtype=bool)
    ids = _case_column(cluster_ids, int(pos.shape[0]))
    buckets: dict[str, list[np.ndarray]] = {"positive": [], "negative": [], "mixed": []}
    for rows in _clusters_in_first_appearance_order(ids):
        got = pos[rows]
        label = "positive" if got.all() else "negative" if not got.any() else "mixed"
        buckets[label].append(rows)
    strata = tuple(
        _stratum(label, buckets[label], pos)
        for label in ("positive", "negative", "mixed")
        if buckets[label]
    )
    return Resampler(kind="clustered", strata=strata, n_rows=int(pos.shape[0]))


def clustered_flat(cluster_ids: Sequence[Any] | np.ndarray, n_rows: int | None = None) -> Resampler:
    """Cases resampled in a single stratum - for a proportion inside one cell.

    The cell is already conditioned on the outcome (sensitivity is computed among the
    reference-positive rows), so there is no second class left to stratify on.

    ``n_rows`` is the length of the cell's data. Supplying it is how a caller gets the
    alignment check :func:`clustered_by_case` has always had: ``cluster_ids`` shorter
    than the cell would otherwise give an estimate over all the rows and an interval
    resampled from a prefix of them, in one Number, with no error and no flag.
    """
    ids = _case_column(cluster_ids, None if n_rows is None else int(n_rows))
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


def _refusal_reason(kind: str, deficient_class: str) -> str:
    """The typed reason for a class with too few resampling units.

    Under clustering the shortage is of independent **cases**, and saying
    "insufficient positives" beside ``n_pos: 199`` would be false on its face; the
    remedy is more patients, which is what ``insufficient_clusters`` names. Without
    clustering the unit is the row, so the reason names the class that is actually
    short - ``insufficient_negatives`` has been in the enum since build day 2 and was
    reachable from no code path here.
    """
    if kind == "clustered":
        return "insufficient_clusters"
    return "insufficient_negatives" if deficient_class == "negative" else "insufficient_positives"


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
    #: Why ``sd`` is ``None`` although usable draws exist: :data:`RESAMPLE_SD_NOT_FINITE`
    #: when ``usable.std(ddof=1)`` overflowed float64 (carried item 25 of the day-6
    #: handoff). ``None`` whenever ``sd`` is a float or no interval was formed.
    sd_reason: str | None = None


#: ``resample_sd`` is ``None`` with this reason beside it when the sample standard
#: deviation of the usable draws is not finite. numpy squares the centred draws, so a
#: draw above about 1e154 overflows to ``inf`` while the percentile bounds - order
#: statistics, never squared - stay finite. The interval is kept; only the descriptive
#: sd is withheld, with the reason in the cell, because ``json.dumps(allow_nan=False)``
#: refuses ``inf`` and the alternative (writing the token ``Infinity``) is not JSON.
#: Reproduced at 7eb617f and a0c9abc on 57 rows at ``1e-160`` beside 3 at ``0.5`` with 20
#: events over 30 two-row cases: O:E ``est 13.33``, bounds ``(4.0, 4.0e159)``, ``sd inf``
#: (``tests/test_bootstrap_carried.py``).
RESAMPLE_SD_NOT_FINITE = "resample_sd_not_finite"


def _resample_sd(usable: np.ndarray) -> tuple[float | None, str | None]:
    """The sample sd of the usable draws, or ``(None, RESAMPLE_SD_NOT_FINITE)``."""
    if usable.shape[0] <= 1:
        return 0.0, None
    with np.errstate(over="ignore", invalid="ignore"):
        sd = float(usable.std(ddof=1))
    if not math.isfinite(sd):
        return None, RESAMPLE_SD_NOT_FINITE
    return sd, None


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
    deficient = resampler.deficient_class
    if deficient is not None:
        return BootstrapDraw(
            values=np.empty(0),
            ci_lo=None,
            ci_hi=None,
            sd=None,
            n_requested=n_resamples,
            n_usable=0,
            reason=_refusal_reason(resampler.kind, deficient),
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
    sd, sd_reason = _resample_sd(usable)
    if lo == hi:
        return BootstrapDraw(
            values=values,
            ci_lo=None,
            ci_hi=None,
            sd=sd,
            n_requested=n_resamples,
            n_usable=int(usable.shape[0]),
            reason="boundary_estimate",
            sd_reason=sd_reason,
        )
    return BootstrapDraw(
        values=values,
        ci_lo=lo,
        ci_hi=hi,
        sd=sd,
        n_requested=n_resamples,
        n_usable=int(usable.shape[0]),
        sd_reason=sd_reason,
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
    #: :meth:`Resampler.describe` for the resampler that produced (or refused) the
    #: interval - the quantities the refusal rule is measured on. ``None`` when no
    #: resampler ran, which is exactly when there is nothing to explain.
    resampling: dict[str, Any] | None = None
    #: :attr:`BootstrapDraw.sd_reason`, carried into the cell so a ``resample_sd`` of
    #: ``null`` beside a rendered interval is explained where it is read (item 25).
    resample_sd_reason: str | None = None

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
                "resample_sd_reason": self.resample_sd_reason,
                # the deciding quantity beside the threshold that decided it: a
                # reviewer cannot check a refusal against a constant alone
                "resampling": self.resampling,
                **self.policy.as_dict(),
            }
        return out


def _resolved(
    policy: BootstrapPolicy | None,
    plan: ClusterPlan | None,
    n_rows: int,
    cluster_ids: Sequence[Any] | np.ndarray | None = None,
) -> tuple[BootstrapPolicy, ClusterPlan, np.ndarray | None]:
    """Resolve the policy, the plan and the *validated* case column for one cell.

    Four things can be wrong with the pair, and each is checked in this function - which
    every cell function calls before it routes or returns anything, so a check made here
    cannot be skipped by a degenerate cell returning early:

    * ``cluster_ids`` that are not a case column over these rows -> raises, whether the
      array is the wrong rank or the wrong length. This is checked first because until it
      holds the other three checks are reading a column that does not describe these
      rows: 200 distinct ids beside 400 rows passed the repeat check trivially and
      rendered DeLong, and a ``(400, 2)`` composite key passed the length check and did
      the same;
    * a clustered plan with no ``cluster_ids`` -> raises. Round 4's text said so and the
      raise was in the cell functions, *after* their single-class and zero-row early
      returns, so those cells returned ``analytic_status: unavailable`` and told the
      forgetful caller nothing until some cell happened to be non-degenerate;
    * ``cluster_ids`` in hand and no plan - one forgotten keyword argument out of forty
      cells - used to hand the cell to DeLong or Wilson on clustered rows with no flag,
      no companion refusal and ``analytic_status: used``. Ids that repeat now take the
      ``detected`` route, exactly as :func:`plan_clustering` decides it at run level;
    * a plan that positively asserts independence over ids that repeat -> a
      contradiction, and it raises rather than quietly degrading to row resampling.

    The validated column is returned rather than left for the caller to re-derive, so the
    resamplers below cannot be reached with an array this function has not looked at.

    What is *not* checked, because nothing here can see it: ``cluster_ids`` not passed at
    all. See the module docstring.
    """
    pol = policy if policy is not None else BootstrapPolicy()
    ids = None if cluster_ids is None else _case_column(cluster_ids, n_rows)
    if plan is not None and plan.clustered and ids is None:
        raise ValueError("a clustered plan needs cluster_ids")
    if plan is None:
        if ids is None:
            return pol, ClusterPlan(False, "none", n_rows, n_rows), None
        return pol, plan_clustering("none", ids, n_rows), ids
    if ids is not None and not plan.clustered and int(np.unique(ids).shape[0]) < n_rows:
        raise ValueError(
            "cluster_ids repeat but the plan says the rows are independent "
            f"({int(np.unique(ids).shape[0])} cases over {n_rows} rows); "
            "the analytic interval is not valid here and is not silently substituted"
        )
    return pol, plan, ids


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
    pol, cplan, ids = _resolved(policy, plan, int(pos.shape[0]), cluster_ids)
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
        if ids is None:  # unreachable: _resolved refuses a clustered plan without ids
            raise ValueError("a clustered plan needs cluster_ids")
        resampler = clustered_by_case(pos, ids)
        # the CELL's own case count, never the run-level plan's: a run plan is built
        # once and passed to every subgroup cell, so cplan.n_units here would print the
        # whole cohort's case count beside a subgroup's rows.
        n_cases = resampler.n_units
        draw = bootstrap_percentile(statistic, resampler, pol.rng(cell_key), pol.n_resamples, level)
        refused = not_estimable(
            "clustered_data_analytic_ci_invalid",
            est=point,
            n_pos=n_pos,
            n_neg=n_neg,
            n_cases=n_cases,
            ci_level=level,
        )
        flags = ["delong_refused_clustered"]
        flags += auroc_precision_flags(n_cases, resampler.class_units.values())
        number = _number_from_draw(
            draw,
            est=point,
            method="cluster_bootstrap_percentile",
            level=level,
            flags=flags,
            n_pos=n_pos,
            n_neg=n_neg,
            n_cases=n_cases,
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
            resampler.describe(),
            resample_sd_reason=draw.sd_reason,
        )

    analytic = auroc_number(scores, pos, level=level).auroc
    if min(n_pos, n_neg) >= SMALL_CLASS:
        # "used" is documented as "the analytic interval is the rendered one". When the
        # analytic method produced no interval - a perfectly separated subgroup, which
        # is routine - there is no interval to have used, and the enum already carries
        # the truthful value.
        status = "used" if analytic.has_ci else "unavailable"
        return CellCI(analytic, analytic, status, cell_key, cplan.route)

    resampler = stratified_by_outcome(pos)
    draw = bootstrap_percentile(statistic, resampler, pol.rng(cell_key), pol.n_resamples, level)
    number = _number_from_draw(
        draw,
        est=point,
        method="bootstrap_percentile",
        level=level,
        flags=[
            "analytic_ci_replaced_small_class",
            *auroc_precision_flags(n_pos + n_neg, (n_pos, n_neg)),
        ],
        n_pos=n_pos,
        n_neg=n_neg,
    )
    return CellCI(
        number,
        analytic,
        "replaced_small_class",
        cell_key,
        cplan.route,
        pol,
        draw.n_usable,
        draw.sd,
        resampler.describe(),
        resample_sd_reason=draw.sd_reason,
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
    pol, cplan, ids = _resolved(policy, plan, int(ind.shape[0]), cluster_ids)
    n = int(ind.shape[0])
    k = int(ind.sum())

    if n == 0:
        empty = not_estimable("zero_denominator", n=0, k=0, ci_level=level)
        return CellCI(empty, empty, "unavailable", cell_key, cplan.route)

    if not cplan.clustered:
        number = proportion(k, n, level=level).with_precision_flags()
        return CellCI(
            number, number, "used" if number.has_ci else "unavailable", cell_key, cplan.route
        )

    if ids is None:  # unreachable: _resolved refuses a clustered plan without ids
        raise ValueError("a clustered plan needs cluster_ids")
    resampler = clustered_flat(ids, n_rows=n)
    n_cases = resampler.n_units

    def statistic(idx: np.ndarray) -> float:
        return float(ind[idx].mean())

    draw = bootstrap_percentile(statistic, resampler, pol.rng(cell_key), pol.n_resamples, level)
    refused = not_estimable(
        "clustered_data_analytic_ci_invalid", est=k / n, n=n, k=k, n_cases=n_cases, ci_level=level
    )
    # n is the row count; under clustering the effective sample size is the case count,
    # and a subgroup table that printed n = 160 for twenty patients would overstate the
    # evidence by the design effect. Both are carried, and the tier is taken from cases.
    flags = ["wilson_refused_clustered", *precision_flags(n_cases)]
    number = _number_from_draw(
        draw,
        est=k / n,
        method="cluster_bootstrap_percentile",
        level=level,
        flags=flags,
        n=n,
        k=k,
        n_cases=n_cases,
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
        resampler.describe(),
        resample_sd_reason=draw.sd_reason,
    )
