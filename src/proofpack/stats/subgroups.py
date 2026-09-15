"""``stats.subgroups`` - per-attribute, per-level performance, differences and fairness gaps.

What this module produces (D1 section 3.1 ``stats.subgroups`` and ``stats.fairness``,
R2 sections 3 and 4, D4 section 5.3): for every attribute column the mapping recognised,
one row per level - including an explicit ``Unknown/missing`` row - carrying, at every
declared operating point, each proportion metric as a :class:`~proofpack.stats.number.Number`
(Wilson, or the cluster bootstrap under clustering - DEC-10), the level's AUROC, its
Brier score, and two families of differences: against the attribute's **reference level**
and against the level's **complement**. Nothing is a verdict. Every quantity is an
estimate with an interval or a typed reason why it has none.

Conventions this module fixes (each is also in ``design/conventions_T7.md``)
-----------------------------------------------------------------------------

**Which attributes are tabulated.** Every attribute column the mapping recognised
(``io.schema.Table.attributes`` - the canonical attribute columns plus ``attr_*``
categorical extras) and, when a numeric ``age`` column exists, ``age`` banded. A
declared attribute (``subgroups:`` in ``criteria.yaml``) carries the customer's own
``prespecified`` flag and ``source``; an attribute that is present but not declared is
still tabulated, with ``prespecified: false`` and ``source: "exploratory"`` (D1 section
2: "attributes not listed are still tabulated but labelled exploratory").

**Age bands.** ``[lo, hi)`` - a row belongs to the first band with ``lo <= age < hi``,
labelled ``"lo-hi"``. The declared bands are used when the ``age`` declaration carries
them (``io.declare.check_references`` halts with H08 when a declared ``age`` has no
bands). When ``age`` is not declared at all the engine uses :data:`DEFAULT_AGE_BANDS`,
which are the bands D1 section 2 shows in its ``criteria.yaml`` -
``[[0,40],[40,65],[65,80],[80,200]]`` - and the attribute block records
``bands_source: "engine_default"`` so a reviewer can see the customer did not choose
them. R2 section 3.1 names a different canonical banding (``<18, 18-39, 40-64, 65-79,
>=80``); which of the two should be the engine default is an open question in the day-5
note, not a decision this module takes silently. An age that falls in no band, or is
missing, goes to the Unknown row; the attribute block counts both kinds separately.

**The Unknown row.** Rows whose attribute value is missing (``None`` after the
missing-token normalisation, which ``io.schema`` has already rewritten to
``"Unknown/missing"``) form the explicit Unknown row (``is_unknown_row: true``). It is
a level like any other for its own metrics and its own differences; it **takes part in
every other level's complement**; and it is **never a reference level** - a declared
``reference_level`` naming it halts with H09.

**The reference level.** The declared one, or the largest level by ``n`` when the
declaration says ``largest`` (and for an undeclared, exploratory attribute). Ties on
``n`` go to the first level in the level order, which is the sorted level labels; the
attribute block records ``reference_rule`` as ``declared``, ``largest`` or
``largest_tie_first_in_level_order`` so the tie is visible. The reference row's
``diff_vs_reference`` entries are ``null``.

**The complement of a level** is every other analysed row of the same attribute -
all other levels **and the Unknown row**. A subgroup is never compared against the
overall cohort, because the subgroup is part of it (objection X1): there is no
``diff_vs_overall`` anywhere in this module or its output, and a test greps for it.

**Differences.** Proportion metrics by Newcombe 1998 method 10 through
:func:`proofpack.stats.proportions.difference_unpaired`; AUROC by the unpaired DeLong
difference (:func:`proofpack.stats.discrimination.unpaired_delong` - the two variances
add because the samples are disjoint; Wald interval; ``z`` and the two-sided ``p`` are
carried in the cell's ``detail`` and are never a verdict). Both are valid only for
independent rows. **Under a clustered plan** the analytic methods are refused with the
typed reason ``clustered_data_analytic_ci_invalid`` on the companion Number; if the two
sides share no case the difference is computed by the cluster bootstrap - cases resampled
within each side *independently* with the day-4 :class:`~proofpack.stats.bootstrap.Resampler`,
percentile interval, method ``cluster_bootstrap_percentile``, flag
``newcombe_refused_clustered`` (proportions) or ``delong_refused_clustered`` (AUROC) on the
rendered Number; if **any** case has rows on both sides the two sides are not independent
samples and the difference is refused outright with ``cases_span_both_groups``. A
difference is refused with ``boundary_estimate`` (estimate carried) when one side is
frozen: on the analytic route when either side's DeLong variance is zero
(:func:`~proofpack.stats.discrimination.unpaired_delong`), and on the cluster-bootstrap
route when either side's own resampled statistic has a zero-width percentile interval
(:func:`_frozen_sides`) - the interval would otherwise be the other side's alone. The
cell records which sides were frozen under ``bootstrap.resampling.frozen_sides``.

**AUROC evaluability.** A level with fewer than :data:`AUROC_EVALUABLE_CLASS` positives
or fewer than that many negatives has its AUROC shown as not estimable
(``insufficient_positives`` / ``insufficient_negatives``), never omitted (R2 section
3.3). The constant equals ``stats.discrimination.SMALL_CLASS`` numerically but is a
different rule: R2 section 1.3's small-class switch to a bootstrap applies to a cohort;
section 3.3's per-group rule refuses the estimate. A difference involving a
non-evaluable level carries the same reason.

**Tiers** are the day-4 :func:`~proofpack.stats.bootstrap.precision_flags`, measured in
resampling units (cases under clustering, rows otherwise) and in units carrying the
event; the thresholds are imported, not restated.

**Brier** per level only when ``score.type`` is ``probability`` and the orientation is
``higher_is_positive`` (so the score *is* the probability of the positive class): the
plain mean squared error with a percentile bootstrap interval through the day-4
resampler (stratified by outcome, or clustered). Otherwise ``not_computed_this_run``
with the declared score type in the cell's ``detail``.

**Fairness** (R2 section 4) is *measured, never mitigated*: for the attribute the
``fairness`` block names, the gaps against the reference level are the very
``diff_vs_reference`` Numbers already computed - ``tpr_gap`` is the sensitivity
difference, ``fpr_gap`` is ``(1 - specificity)`` difference, i.e. minus the specificity
difference with the bounds mirrored, ``ppv_gap``, ``npv_gap``, ``auroc_gap`` - plus a
selection-rate gap (share of rows called positive at the operating point, Newcombe-10
difference) labelled ``descriptive_not_target`` because base rates legitimately differ
by group and demographic parity is not a target for a diagnostic tool.
Calibration-by-group belongs to the calibration day and is emitted as ``null`` with the
reason ``not_computed_this_run``. The ``criterion_of_interest`` and ``bound`` are
recorded verbatim and **no status is emitted**: the comparison to the bound is the
criteria day's (E7). R2 section 4 rests on the Kleinberg / Chouldechova impossibility
result, which R2 records as **[unverified - cited from memory]**; that marking is
carried here unchanged and is not resolved by this module.

**Heterogeneity footnote** (R2 section 3.4): per attribute and operating point, a
chi-square test of homogeneity across the evaluable levels for sensitivity and for
specificity separately (Pearson, no continuity correction, ``scipy.stats.chi2_contingency``),
Fisher's exact test instead when there are exactly two levels and any expected cell is
below 5; raw p-values plus Holm-adjusted p-values within the attribute's family (own
implementation, checked against ``statsmodels.stats.multitest.multipletests`` in the
tests). The Unknown row is not a level of the attribute for this purpose and is left
out of the test. The footnote is labelled ``exploratory``, carries the D4 sentence, and
has no ``status`` key beside any p-value. With scipy absent the test entries carry
``not_estimable_reason: scipy_unavailable``; the module imports without scipy. **Under
a clustered plan** (declared or detected) the tests are not run: the chi-square counts
rows as independent trials, so every entry carries
``not_estimable_reason: clustered_data_analytic_ci_invalid`` and the footnote records
the ``clustering_route`` (lens note 2026-09-15, FA-B1). Fewer than two evaluable levels
is ``insufficient_levels`` on every route.

**Cell shape.** Every metric and every difference is serialised as the day-4 cell
``{number, analytic, analytic_status, clustering_route, bootstrap}`` (plus an optional
``detail``) rather than as a bare Number, so the X2 companion refusal and the resampling
quantities that decided it reach the output JSON beside the rendered Number. The
renderer reads ``number``. D1 section 4.2 writes the block as Numbers; the cell wrapper is
the day-4 shape and is recorded as a deviation in the day-5 note.

Nothing here reads or writes a file, and nothing here imports scipy at module level.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from proofpack.errors import HaltError
from proofpack.io.declare import Declarations, OperatingPoint
from proofpack.io.schema import UNKNOWN_LEVEL, Table
from proofpack.stats.bootstrap import (
    CLUSTER_ROUTES,
    DEFAULT_LEVEL,
    MIN_USABLE_FRACTION,
    BootstrapDraw,
    BootstrapPolicy,
    CellCI,
    ClusterPlan,
    Resampler,
    _number_from_draw,
    _refusal_reason,
    auroc_ci,
    bootstrap_percentile,
    clustered_by_case,
    clustered_flat,
    percentile_bounds,
    plan_clustering,
    precision_flags,
    proportion_ci,
    stratified_by_outcome,
)
from proofpack.stats.discrimination import auroc_mann_whitney, unpaired_delong
from proofpack.stats.number import Number, not_estimable
from proofpack.stats.proportions import difference_unpaired, sensitivity_id, specificity_id

__all__ = [
    "AUROC_EVALUABLE_CLASS",
    "DEFAULT_AGE_BANDS",
    "EXPLORATORY",
    "FAIRNESS_GAP_KEYS",
    "FISHER_EXPECTED_BELOW",
    "HETEROGENEITY_SENTENCE",
    "SubgroupReport",
    "age_band_labels",
    "band_ages",
    "heterogeneity_footnote",
    "holm",
    "subgroup_analysis",
]

#: D1 section 2's example bands, used when ``age`` is present but not declared. See the
#: module docstring: R2 section 3.1 names a different canonical banding and the choice
#: between them is an open question, recorded rather than decided here.
DEFAULT_AGE_BANDS: tuple[tuple[float, float], ...] = ((0, 40), (40, 65), (65, 80), (80, 200))
#: The ``source`` of an attribute that is tabulated without having been declared.
EXPLORATORY = "exploratory"
#: R2 section 3.3: an AUROC per group needs at least this many positives *and* this many
#: negatives, else it is shown as not evaluable with a reason. Numerically equal to
#: ``stats.discrimination.SMALL_CLASS`` but a different rule (see the module docstring).
AUROC_EVALUABLE_CLASS = 10
#: R2 section 3.4: Fisher's exact test replaces the chi-square when any expected cell is
#: below this and the attribute has exactly two evaluable levels.
FISHER_EXPECTED_BELOW = 5.0
#: D4 section 5.3b, verbatim - the footnote's sentence.
HETEROGENEITY_SENTENCE = (
    "exploratory; no conclusion about subgroup consistency is drawn from this test"
)
#: R2 section 4's label for the selection-rate gap.
SELECTION_RATE_LABEL = "descriptive_not_target"
#: The gap keys the fairness block emits per operating point, and the metric each is
#: read from. ``fpr_gap`` is the mirrored specificity difference.
FAIRNESS_GAP_KEYS = ("tpr_gap", "fpr_gap", "ppv_gap", "npv_gap", "selection_rate_gap")
#: The proportion metrics computed per level and operating point, in output order.
#: The sensitivity/specificity keys are routed through ``sensitivity_id`` /
#: ``specificity_id`` (PPA/NPA when the reference standard is a comparator).
PROPORTION_METRICS = ("se", "sp", "ppv", "npv", "accuracy", "selection_rate")

REFERENCE_RULES = ("declared", "largest", "largest_tie_first_in_level_order")


# ------------------------------------------------------------------------------- age


def age_band_labels(bands: Sequence[Sequence[float]]) -> list[str]:
    """``"lo-hi"`` per band, integers printed without a decimal point."""

    def fmt(x: float) -> str:
        return str(int(x)) if float(x).is_integer() else str(x)

    return [f"{fmt(lo)}-{fmt(hi)}" for lo, hi in bands]


def band_ages(age: np.ndarray, bands: Sequence[Sequence[float]]) -> tuple[np.ndarray, int, int]:
    """Band a float age column. Returns ``(labels, n_missing, n_outside_bands)``.

    ``[lo, hi)``: the first band with ``lo <= age < hi`` wins. NaN and out-of-band ages
    are labelled :data:`~proofpack.io.schema.UNKNOWN_LEVEL` and counted separately.
    """
    a = np.asarray(age, dtype=np.float64)
    labels = age_band_labels(bands)
    out = np.full(a.shape[0], UNKNOWN_LEVEL, dtype=object)
    placed = np.zeros(a.shape[0], dtype=bool)
    for (lo, hi), label in zip(bands, labels, strict=True):
        hit = ~placed & (a >= float(lo)) & (a < float(hi))
        out[hit] = label
        placed |= hit
    missing = np.isnan(a)
    outside = ~placed & ~missing
    return out, int(missing.sum()), int(outside.sum())


# ------------------------------------------------------------------------- multiplicity


def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values, in the input order.

    Sort ascending; the i-th smallest (0-based) is multiplied by ``m - i``; the running
    maximum is taken so the adjusted values are monotone; each is capped at 1. Checked
    against ``statsmodels.stats.multitest.multipletests(method="holm")`` in the tests.
    """
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, pvalues[i] * (m - rank)))
        adjusted[i] = running
    return adjusted


def _homogeneity_test(
    counts: Sequence[tuple[int, int]], fisher_below: float = FISHER_EXPECTED_BELOW
) -> dict[str, Any]:
    """Chi-square (or Fisher) test of homogeneity of a proportion across levels.

    ``counts`` is ``[(successes, failures), ...]`` over the evaluable levels. Pearson
    chi-square without continuity correction; Fisher's exact test instead when there are
    exactly two levels and the smallest expected cell is below ``fisher_below``
    (:data:`FISHER_EXPECTED_BELOW`; the F6 test passes ``inf`` to exercise the Fisher
    branch on R2's site-1-vs-site-2 pair, whose expected cells are all above 5). scipy
    is imported here, inside the function, so the module imports without it and the
    entry carries ``scipy_unavailable`` instead of raising.
    """
    table = [[int(s), int(f)] for s, f in counts]
    n_levels = len(table)
    base: dict[str, Any] = {
        "test": None,
        "statistic": None,
        "df": None,
        "p_raw": None,
        "p_holm": None,
        "n_levels": n_levels,
        "min_expected": None,
        "not_estimable_reason": None,
    }
    if n_levels < 2:
        base["not_estimable_reason"] = "insufficient_levels"
        return base
    if sum(r[0] for r in table) == 0 or sum(r[1] for r in table) == 0:
        # every level at 0 or every level at 1: a zero column, expected counts of zero,
        # and no homogeneity question left to ask
        base["not_estimable_reason"] = "boundary_estimate"
        return base
    try:
        from scipy.stats import (  # noqa: PLC0415  (optional dependency, imported lazily)
            chi2_contingency,
            fisher_exact,
        )
    except ImportError:
        base["not_estimable_reason"] = "scipy_unavailable"
        return base
    arr = np.asarray(table, dtype=np.float64)
    expected = np.outer(arr.sum(axis=1), arr.sum(axis=0)) / arr.sum()
    min_expected = float(expected.min())
    base["min_expected"] = min_expected
    if n_levels == 2 and min_expected < fisher_below:
        _, p = fisher_exact(table)
        base.update(test="fisher_exact", statistic=None, df=None, p_raw=float(p))
        return base
    stat, p, dof, _ = chi2_contingency(arr, correction=False)
    base.update(test="chi2_homogeneity", statistic=float(stat), df=int(dof), p_raw=float(p))
    return base


def _clustered_refusal(counts: Sequence[tuple[int, int]]) -> dict[str, Any]:
    """The footnote entry for a clustered table: no test, the typed reason, the level count."""
    return {
        "test": None,
        "statistic": None,
        "df": None,
        "p_raw": None,
        "p_holm": None,
        "n_levels": len(counts),
        "min_expected": None,
        "not_estimable_reason": "clustered_data_analytic_ci_invalid",
    }


def heterogeneity_footnote(
    per_op: dict[str, dict[str, Sequence[tuple[int, int]]]],
    *,
    clustering_route: str,
) -> dict[str, Any]:
    """The exploratory footnote for one attribute.

    ``per_op`` maps operating point id -> ``{"sensitivity": [(tp, fn), ...],
    "specificity": [(tn, fp), ...]}`` over the evaluable levels (the Unknown row
    excluded). All tests of one attribute form one Holm family. There is no ``status``
    key anywhere in the result, by design and by test.

    ``clustering_route`` is the run-level :class:`~proofpack.stats.bootstrap.ClusterPlan`
    route (``none`` / ``declared`` / ``detected``) and has no default: a caller that
    omits it gets a ``TypeError``, not the row test (lens 2, FA-N9). The chi-square and
    Fisher tests count **rows** as independent Bernoulli trials; under a clustered plan
    the rows are not, the chi-square statistic grows with the rows-per-case factor and
    the p-value shrinks with it (F6 with every patient's row copied three times:
    chi-square 13.898, p 0.00096 against 4.6327, p 0.0986 on one row per patient - lens
    note 2026-09-15, FA-B1). So under ``declared`` or ``detected`` every entry carries
    ``not_estimable_reason: clustered_data_analytic_ci_invalid`` - the DEC-09 typed
    reason the same block's intervals already carry - with ``n_levels`` kept so the
    reader sees what would have been compared, and the Holm family is empty. No
    case-level homogeneity test is offered in its place: a switch to a different method
    is a method choice, not a fallback, and none is made here.

    Precedence of the two refusals (lens 2, FA-N8 / RG-N2): fewer than two evaluable
    levels is ``insufficient_levels`` on every route, because there was no comparison
    to make before the question of independence arose; the clustered refusal applies
    only where a test would otherwise have run.
    """
    if clustering_route not in CLUSTER_ROUTES:
        raise ValueError(f"unknown clustering_route {clustering_route!r}")
    clustered = clustering_route != "none"
    tests: list[dict[str, Any]] = []
    for op_id, metrics in per_op.items():
        for metric, counts in metrics.items():
            entry = (
                _clustered_refusal(counts)
                if clustered and len(counts) >= 2
                else _homogeneity_test(counts)
            )
            entry = {"operating_point": op_id, "metric": metric, **entry}
            tests.append(entry)
    raw = [t["p_raw"] for t in tests if t["p_raw"] is not None]
    adjusted = holm(raw) if raw else []
    it = iter(adjusted)
    for t in tests:
        if t["p_raw"] is not None:
            t["p_holm"] = next(it)
    return {
        "label": EXPLORATORY,
        "sentence": HETEROGENEITY_SENTENCE,
        "adjustment": "holm",
        "family_size": len(raw),
        "clustering_route": clustering_route,
        "tests": tests,
    }


# --------------------------------------------------------------------------- arrays


@dataclass(frozen=True)
class _Arrays:
    """The analysed rows, typed once, and the run-level clustering decision."""

    pos: np.ndarray  # reference-positive, bool
    score: np.ndarray | None  # oriented so higher = positive; None without a score column
    prob: np.ndarray | None  # the probability of the positive class, or None
    predicted: dict[str, np.ndarray]  # op id -> called positive, bool
    ids: np.ndarray | None  # validated case column over the analysed rows
    plan: ClusterPlan
    policy: BootstrapPolicy
    level: float
    se_key: str
    sp_key: str
    score_type: str

    @property
    def clustered(self) -> bool:
        return self.plan.clustered

    def ids_for(self, rows: np.ndarray) -> np.ndarray | None:
        return None if self.ids is None else self.ids[rows]

    def units(self, rows: np.ndarray) -> int:
        """Resampling units in ``rows``: cases under clustering, rows otherwise."""
        if self.ids is None:
            return int(rows.shape[0])
        return int(np.unique(self.ids[rows]).shape[0])


def _cell_key(*parts: Any) -> str:
    """One unambiguous key per cell: level labels may contain any character."""
    return json.dumps(["subgroups", *[str(p) for p in parts]])


def _cell(cell: CellCI, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    out = cell.as_dict()
    if detail is not None:
        out["detail"] = detail
    return out


def _unavailable(number: Number, key: str, route: str, analytic: Number | None = None) -> CellCI:
    """A cell with no interval from either method; ``analytic`` carries a companion
    refusal where there is one (a clustered difference whose cases span both sides)."""
    return CellCI(number, analytic, "unavailable", key, route)


# -------------------------------------------------------------- two-sided bootstrap


def _frozen_sides(side_values: dict[str, np.ndarray], level: float) -> tuple[str, ...]:
    """The sides whose own resampled statistic has a zero-width percentile interval.

    :func:`proofpack.stats.bootstrap.bootstrap_percentile` refuses a single cell with
    ``boundary_estimate`` when the ``alpha/2`` and ``1 - alpha/2`` quantiles of its
    draws coincide. The same rule, applied to each side's finite draws on its own: a
    perfectly separated level's AUROC is 1.0 (or 0.0) in every case-resample, a level's
    proportion at ``k = n`` or ``k = 0`` is the same in every resample, and a
    constant-score level's AUROC is 0.5 in every resample.
    """
    frozen: list[str] = []
    for side, values in side_values.items():
        finite = values[np.isfinite(values)]
        if finite.shape[0] == 0:
            continue
        lo, hi = percentile_bounds(finite, level)
        if lo == hi:
            frozen.append(side)
    return tuple(frozen)


def _bootstrap_difference(
    stat_a: Callable[[np.ndarray], float],
    res_a: Resampler,
    stat_b: Callable[[np.ndarray], float],
    res_b: Resampler,
    rng: np.random.Generator,
    n_resamples: int,
    level: float,
) -> tuple[BootstrapDraw, tuple[str, ...]]:
    """Percentile interval for ``stat_a - stat_b`` with the two sides drawn independently.

    Returns the draw and the sides found frozen (``("a",)``, ``("b",)``, ``("a", "b")``
    or ``()``), which the cell records under ``bootstrap.resampling.frozen_sides``.

    The same refusal rules as :func:`proofpack.stats.bootstrap.bootstrap_percentile`,
    applied to each side: a side whose class the resampler cannot vary refuses the
    difference with that side's typed reason before any draw is made; after the draws,
    a side whose own statistic has a zero-width percentile interval (:func:`_frozen_sides`)
    refuses the difference with ``boundary_estimate``, estimate carried, because
    ``values = const - stat_b(draw)`` would make the rendered interval the other side's
    alone, shifted (lens note 2026-09-15, lens 2 FA-B1: measured on a 10-case level
    perfectly separated beside a 60-case level under clustering, that interval covered
    the true AUROC difference in 0.295 of replicates, and the sensitivity difference at
    10/10 in 0.615, at a nominal 0.95). What is inspected:
    ``test_the_two_sided_cluster_bootstrap_refuses_a_difference_whose_one_side_is_frozen``
    reads the AUROC and sensitivity differences of a separated level, and of the
    complement that contains it, on the repair-round-1 cohort duplicated under case ids.
    The two sides consume one generator in a fixed order (a then b, one draw each per
    resample), so the draw is a pure function of the cell key like every other cell.
    """
    for res in (res_a, res_b):
        deficient = res.deficient_class
        if deficient is not None:
            return BootstrapDraw(
                values=np.empty(0),
                ci_lo=None,
                ci_hi=None,
                sd=None,
                n_requested=n_resamples,
                n_usable=0,
                reason=_refusal_reason(res.kind, deficient),
            ), ()
    values_a = np.empty(n_resamples, dtype=np.float64)
    values_b = np.empty(n_resamples, dtype=np.float64)
    for b in range(n_resamples):
        values_a[b] = stat_a(res_a.draw(rng))
        values_b[b] = stat_b(res_b.draw(rng))
    values = values_a - values_b
    usable = values[np.isfinite(values)]
    if usable.shape[0] < math.ceil(MIN_USABLE_FRACTION * n_resamples):
        return BootstrapDraw(
            values, None, None, None, n_resamples, int(usable.shape[0]), "degenerate_resamples"
        ), ()
    frozen = _frozen_sides({"a": values_a, "b": values_b}, level)
    lo, hi = percentile_bounds(usable, level)
    sd = float(usable.std(ddof=1)) if usable.shape[0] > 1 else 0.0
    if frozen or lo == hi:
        return BootstrapDraw(
            values, None, None, sd, n_resamples, int(usable.shape[0]), "boundary_estimate"
        ), frozen
    return BootstrapDraw(values, lo, hi, sd, n_resamples, int(usable.shape[0])), frozen


def _shared_cases(ids_a: np.ndarray, ids_b: np.ndarray) -> int:
    """How many cases have rows on both sides. Any is a dependence between the sides."""
    return int(np.intersect1d(np.unique(ids_a), np.unique(ids_b)).shape[0])


# ---------------------------------------------------------------- per-level metrics


def _proportion_cell(arrays: _Arrays, rows: np.ndarray, indicator: np.ndarray, key: str) -> CellCI:
    """One proportion over ``rows`` (already conditioned), routed by DEC-10."""
    return proportion_ci(
        indicator,
        cell_key=key,
        policy=arrays.policy,
        plan=arrays.plan,
        cluster_ids=arrays.ids_for(rows),
        level=arrays.level,
    )


def _proportion_difference(
    arrays: _Arrays,
    rows_a: np.ndarray,
    ind_a: np.ndarray,
    rows_b: np.ndarray,
    ind_b: np.ndarray,
    key: str,
) -> CellCI:
    """``p_a - p_b`` for two conditioned row sets: Newcombe-10, or the cluster bootstrap.

    ``rows_a`` / ``rows_b`` are the row indices the two indicators are defined on (for a
    sensitivity difference, each side's reference-positive rows), so the case ids can be
    sliced with them and the shared-case test is made on exactly the rows that enter the
    difference.
    """
    n1, n2 = int(ind_a.shape[0]), int(ind_b.shape[0])
    k1, k2 = int(ind_a.sum()), int(ind_b.sum())
    level, route = arrays.level, arrays.plan.route
    if n1 == 0 or n2 == 0:
        return _unavailable(not_estimable("zero_denominator", ci_level=level), key, route)
    d = k1 / n1 - k2 / n2
    if not arrays.clustered:
        number = difference_unpaired(k1, n1, k2, n2, level)
        return CellCI(number, number, "used" if number.has_ci else "unavailable", key, route)

    ids_a, ids_b = arrays.ids_for(rows_a), arrays.ids_for(rows_b)
    assert ids_a is not None and ids_b is not None  # a clustered plan always has ids
    n_cases = min(int(np.unique(ids_a).shape[0]), int(np.unique(ids_b).shape[0]))
    counts = {"n": min(n1, n2), "n_cases": n_cases}
    refused = not_estimable("clustered_data_analytic_ci_invalid", est=d, ci_level=level, **counts)
    if _shared_cases(ids_a, ids_b):
        return _unavailable(
            not_estimable("cases_span_both_groups", est=d, ci_level=level, **counts),
            key,
            route,
            refused,
        )
    res_a, res_b = clustered_flat(ids_a, n_rows=n1), clustered_flat(ids_b, n_rows=n2)
    pol = arrays.policy
    draw, frozen = _bootstrap_difference(
        lambda idx: float(ind_a[idx].mean()),
        res_a,
        lambda idx: float(ind_b[idx].mean()),
        res_b,
        pol.rng(key),
        pol.n_resamples,
        level,
    )
    number = _number_from_draw(
        draw,
        est=d,
        method="cluster_bootstrap_percentile",
        level=level,
        flags=["newcombe_refused_clustered", *precision_flags(n_cases)],
        **counts,
    )
    return CellCI(
        number,
        refused,
        "refused_clustered",
        key,
        route,
        pol,
        draw.n_usable,
        draw.sd,
        {"a": res_a.describe(), "b": res_b.describe(), "frozen_sides": list(frozen)},
    )


def _auroc_evaluability(pos: np.ndarray) -> str | None:
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    if n_pos < AUROC_EVALUABLE_CLASS:
        return "insufficient_positives"
    if n_neg < AUROC_EVALUABLE_CLASS:
        return "insufficient_negatives"
    return None


def _auroc_cell(arrays: _Arrays, rows: np.ndarray, key: str) -> CellCI:
    pos = arrays.pos[rows]
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    level, route = arrays.level, arrays.plan.route
    counts = {"n_pos": n_pos, "n_neg": n_neg}
    if arrays.score is None:
        return _unavailable(
            not_estimable("not_computed_this_run", ci_level=level, **counts), key, route
        )
    reason = _auroc_evaluability(pos)
    if reason is not None:
        # R2 section 3.3: shown as not evaluable, with the reason and the counts, never
        # omitted. No point estimate is carried: D4 section 5.3 renders "n.e.".
        return _unavailable(not_estimable(reason, ci_level=level, **counts), key, route)
    return auroc_ci(
        arrays.score[rows],
        pos,
        cell_key=key,
        policy=arrays.policy,
        plan=arrays.plan,
        cluster_ids=arrays.ids_for(rows),
        level=level,
    )


def _auroc_difference(
    arrays: _Arrays, rows_a: np.ndarray, rows_b: np.ndarray, key: str
) -> tuple[CellCI, dict[str, Any] | None]:
    """``AUROC(a) - AUROC(b)``: unpaired DeLong, or the two-sided cluster bootstrap.

    Returns the cell and, for the analytic route, the detail block carrying the two
    variances, ``z`` and the two-sided ``p`` - detail, never a verdict.
    """
    pos_a, pos_b = arrays.pos[rows_a], arrays.pos[rows_b]
    level, route = arrays.level, arrays.plan.route
    counts = {
        "n_pos": int(pos_a.sum()) + int(pos_b.sum()),
        "n_neg": int((~pos_a).sum()) + int((~pos_b).sum()),
    }
    if arrays.score is None:
        number = not_estimable("not_computed_this_run", ci_level=level, **counts)
        return _unavailable(number, key, route), None
    reason = _auroc_evaluability(pos_a) or _auroc_evaluability(pos_b)
    if reason is not None:
        return _unavailable(not_estimable(reason, ci_level=level, **counts), key, route), None
    s_a, s_b = arrays.score[rows_a], arrays.score[rows_b]
    if not arrays.clustered:
        result = unpaired_delong(s_a, pos_a, s_b, pos_b, level)
        number = result.difference
        status = "used" if number.has_ci else "unavailable"
        detail = {
            "method": result.method,
            "variance_a": result.variance_a,
            "variance_b": result.variance_b,
            "variance_difference": result.variance_difference,
            "z": result.z,
            "p_value": result.p_value,
        }
        return CellCI(number, number, status, key, route), detail

    ids_a, ids_b = arrays.ids_for(rows_a), arrays.ids_for(rows_b)
    assert ids_a is not None and ids_b is not None
    d = auroc_mann_whitney(s_a, pos_a) - auroc_mann_whitney(s_b, pos_b)
    n_cases = min(int(np.unique(ids_a).shape[0]), int(np.unique(ids_b).shape[0]))
    counts["n_cases"] = n_cases
    refused = not_estimable("clustered_data_analytic_ci_invalid", est=d, ci_level=level, **counts)
    if _shared_cases(ids_a, ids_b):
        spanned = not_estimable("cases_span_both_groups", est=d, ci_level=level, **counts)
        return _unavailable(spanned, key, route, refused), None
    res_a, res_b = clustered_by_case(pos_a, ids_a), clustered_by_case(pos_b, ids_b)

    def stat(scores: np.ndarray, pos: np.ndarray) -> Callable[[np.ndarray], float]:
        def statistic(idx: np.ndarray) -> float:
            got = pos[idx]
            if not got.any() or got.all():
                return float("nan")
            return auroc_mann_whitney(scores[idx], got)

        return statistic

    pol = arrays.policy
    draw, frozen = _bootstrap_difference(
        stat(s_a, pos_a), res_a, stat(s_b, pos_b), res_b, pol.rng(key), pol.n_resamples, level
    )
    number = _number_from_draw(
        draw,
        est=d,
        method="cluster_bootstrap_percentile",
        level=level,
        flags=["delong_refused_clustered", *precision_flags(n_cases)],
        **counts,
    )
    cell = CellCI(
        number,
        refused,
        "refused_clustered",
        key,
        route,
        pol,
        draw.n_usable,
        draw.sd,
        {"a": res_a.describe(), "b": res_b.describe(), "frozen_sides": list(frozen)},
    )
    return cell, None


def _brier_cell(
    arrays: _Arrays, rows: np.ndarray, key: str
) -> tuple[CellCI, dict[str, Any] | None]:
    pos = arrays.pos[rows]
    n = int(rows.shape[0])
    level, route = arrays.level, arrays.plan.route
    if arrays.prob is None:
        number = not_estimable("not_computed_this_run", n=n, ci_level=level)
        return _unavailable(number, key, route), {"score_type": arrays.score_type}
    p = arrays.prob[rows]
    sq = (p - pos.astype(np.float64)) ** 2
    est = float(sq.mean()) if n else None
    if n == 0:
        return _unavailable(
            not_estimable("zero_denominator", n=0, ci_level=level), key, route
        ), None
    if not pos.any() or pos.all():
        # the stratified resampler has an empty stratum here; refused rather than
        # resampled from a single class as if it were the cohort
        return _unavailable(
            not_estimable("single_class", est=est, n=n, ci_level=level), key, route
        ), None
    ids = arrays.ids_for(rows)
    resampler = (
        clustered_by_case(pos, ids)
        if arrays.clustered and ids is not None
        else (stratified_by_outcome(pos))
    )
    pol = arrays.policy
    draw = bootstrap_percentile(
        lambda idx: float(sq[idx].mean()), resampler, pol.rng(key), pol.n_resamples, level
    )
    n_units = resampler.n_units
    method = "cluster_bootstrap_percentile" if arrays.clustered else "bootstrap_percentile"
    counts: dict[str, Any] = {"n": n}
    if arrays.clustered:
        counts["n_cases"] = n_units
    number = _number_from_draw(
        draw, est=est, method=method, level=level, flags=precision_flags(n_units), **counts
    )
    status = "refused_clustered" if arrays.clustered else "used"
    analytic = (
        not_estimable("clustered_data_analytic_ci_invalid", est=est, ci_level=level, **counts)
        if arrays.clustered
        else not_estimable("analytic_ci_unavailable", est=est, ci_level=level, **counts)
    )
    if not number.has_ci:
        status = "unavailable"
    return (
        CellCI(
            number, analytic, status, key, route, pol, draw.n_usable, draw.sd, resampler.describe()
        ),
        None,
    )


# ------------------------------------------------------------------------ the groups


@dataclass(frozen=True)
class _Level:
    attribute: str
    label: str
    rows: np.ndarray
    is_unknown: bool

    @property
    def n(self) -> int:
        return int(self.rows.shape[0])


@dataclass
class _Attribute:
    name: str
    prespecified: bool
    source: str
    declared: bool
    levels: list[_Level]  # in level order; the Unknown row last when present
    reference: str | None
    reference_rule: str | None
    bands: list[list[float]] | None = None
    bands_source: str | None = None
    n_missing: int = 0
    n_outside_bands: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def unknown(self) -> _Level | None:
        return next((lv for lv in self.levels if lv.is_unknown), None)

    def level(self, label: str) -> _Level:
        return next(lv for lv in self.levels if lv.label == label)


def _levels_from_labels(attribute: str, labels: np.ndarray) -> list[_Level]:
    """Level order = sorted labels, the Unknown row last. Missing values are Unknown."""
    lab = np.array(
        [UNKNOWN_LEVEL if v is None else str(v) for v in np.asarray(labels, dtype=object).tolist()],
        dtype=object,
    )
    known = sorted({v for v in lab.tolist() if v != UNKNOWN_LEVEL})
    levels = [_Level(attribute, v, np.flatnonzero(lab == v), False) for v in known]
    unknown_rows = np.flatnonzero(lab == UNKNOWN_LEVEL)
    if unknown_rows.shape[0]:
        levels.append(_Level(attribute, UNKNOWN_LEVEL, unknown_rows, True))
    return levels


def _choose_reference(
    attribute: str, levels: list[_Level], declared: Any
) -> tuple[str | None, str | None]:
    """The reference level and the rule that chose it.

    ``declared`` is the declaration's ``reference_level`` (a label, ``"largest"`` or
    ``None``). The Unknown row is never a candidate; declaring it halts with H09.
    """
    candidates = [lv for lv in levels if not lv.is_unknown]
    if not candidates:
        return None, None
    if declared is not None and str(declared) != "largest":
        label = str(declared).strip()
        if label == UNKNOWN_LEVEL:
            raise HaltError(
                "H09",
                "subgroup reference_level names the Unknown/missing row, never a reference level",
                {"attribute": attribute},
            )
        if label not in {lv.label for lv in candidates}:
            # either the declared label is absent from the table, or every row carrying
            # it was excluded by the analysis mask (missing score, indeterminate): the
            # message names the analysed rows, which is what was inspected
            raise HaltError(
                "H09",
                "subgroup reference_level is not a level of the analysed rows",
                {"attribute": attribute, "reference_level": label},
            )
        return label, "declared"
    largest = max(lv.n for lv in candidates)
    tied = [lv for lv in candidates if lv.n == largest]
    # ties: the first in the level order (sorted labels), and the rule says so
    return tied[0].label, "largest" if len(tied) == 1 else "largest_tie_first_in_level_order"


def _attributes(table: Table, decl: Declarations, mask: np.ndarray) -> list[_Attribute]:
    declared = {s["attribute"]: s for s in decl.subgroups}
    out: list[_Attribute] = []
    names = sorted(table.attributes)
    if table.age is not None:
        names = ["age", *[n for n in names if n != "age"]]
    for name in names:
        spec = declared.get(name)
        bands = None
        bands_source = None
        n_missing = n_outside = 0
        if name == "age" and table.age is not None:
            if spec is not None and spec.get("bands"):
                bands = [list(map(float, b)) for b in spec["bands"]]
                bands_source = "declared"
            else:
                bands = [list(map(float, b)) for b in DEFAULT_AGE_BANDS]
                bands_source = "engine_default"
            labels, n_missing, n_outside = band_ages(table.age[mask], bands)
        else:
            labels = table.attributes[name][mask]
            n_missing = int(sum(1 for v in labels.tolist() if v is None or v == UNKNOWN_LEVEL))
        levels = _levels_from_labels(name, labels)
        ref, rule = _choose_reference(
            name, levels, None if spec is None else spec.get("reference_level")
        )
        out.append(
            _Attribute(
                name=name,
                prespecified=bool(spec.get("prespecified", False)) if spec is not None else False,
                source=(str(spec.get("source") or "declared") if spec is not None else EXPLORATORY),
                declared=spec is not None,
                levels=levels,
                reference=ref,
                reference_rule=rule,
                bands=bands,
                bands_source=bands_source,
                n_missing=n_missing,
                n_outside_bands=n_outside,
            )
        )
    return out


# ------------------------------------------------------------------------- the report


@dataclass
class SubgroupReport:
    """The three output blocks: rows, attribute blocks, fairness. All JSON-ready."""

    rows: list[dict[str, Any]]
    attributes: list[dict[str, Any]]
    fairness: dict[str, Any] | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "subgroups": self.rows,
            "subgroup_attributes": self.attributes,
            "fairness": self.fairness,
        }

    def row(self, attribute: str, level: str) -> dict[str, Any]:
        for r in self.rows:
            if r["attribute"] == attribute and r["level"] == level:
                return r
        raise KeyError((attribute, level))

    def attribute(self, name: str) -> dict[str, Any]:
        for a in self.attributes:
            if a["attribute"] == name:
                return a
        raise KeyError(name)


def _arrays(
    table: Table,
    decl: Declarations,
    mask: np.ndarray,
    plan: ClusterPlan | None,
    cluster_ids: Sequence[Any] | np.ndarray | None,
    policy: BootstrapPolicy | None,
    level: float,
) -> _Arrays:
    mask = np.asarray(mask, dtype=bool)
    n = int(mask.sum())
    yt = table.y_true[mask]
    pos = np.array([v == decl.positive for v in yt.tolist()], dtype=bool)
    raw_score = None if table.score is None else np.asarray(table.score[mask], dtype=np.float64)
    if raw_score is not None:
        score = raw_score if decl.orientation == "higher_is_positive" else -raw_score
        prob = (
            raw_score
            if (decl.score_type == "probability" and decl.orientation == "higher_is_positive")
            else None
        )
    else:
        score = prob = None
    predicted: dict[str, np.ndarray] = {}
    for op in decl.operating_points:
        if raw_score is not None:
            predicted[op.id] = np.array([op.is_positive(float(v)) for v in raw_score], dtype=bool)
        elif table.y_pred is not None:
            predicted[op.id] = np.array(
                [v == decl.positive for v in table.y_pred[mask].tolist()], dtype=bool
            )
        else:  # pragma: no cover - io.schema requires a score or a y_pred column
            raise ValueError("neither a score nor a y_pred column is present")
    if cluster_ids is None and table.case_id is not None:
        cluster_ids = table.case_id[mask]
    ids = None if cluster_ids is None else np.asarray(cluster_ids, dtype=object)
    resolved = plan_clustering(decl.clustering_unit, ids, n)
    if plan is None:
        plan = resolved
    elif plan.clustered != resolved.clustered:
        raise ValueError(
            "the supplied ClusterPlan contradicts the case column over the analysed rows "
            f"(plan says clustered={plan.clustered}, the column says {resolved.clustered})"
        )
    if plan.clustered and ids is None:  # pragma: no cover - plan_clustering already raised
        raise ValueError("a clustered plan needs cluster_ids")
    return _Arrays(
        pos=pos,
        score=score,
        prob=prob,
        predicted=predicted,
        ids=ids,
        plan=plan,
        policy=policy if policy is not None else BootstrapPolicy(),
        level=level,
        se_key=sensitivity_id(decl.reference_standard_type),
        sp_key=specificity_id(decl.reference_standard_type),
        score_type=decl.score_type,
    )


def _two_by_two(pos: np.ndarray, pred: np.ndarray) -> dict[str, int]:
    return {
        "tp": int(np.count_nonzero(pos & pred)),
        "fn": int(np.count_nonzero(pos & ~pred)),
        "fp": int(np.count_nonzero(~pos & pred)),
        "tn": int(np.count_nonzero(~pos & ~pred)),
    }


def _conditioned(
    rows: np.ndarray, pos: np.ndarray, pred: np.ndarray, metric: str
) -> tuple[np.ndarray, np.ndarray]:
    """``(rows the proportion is defined on, indicator over those rows)`` for one metric."""
    if metric == "se":
        sel = pos
        ind = pred[sel]
    elif metric == "sp":
        sel = ~pos
        ind = ~pred[sel]
    elif metric == "ppv":
        sel = pred
        ind = pos[sel]
    elif metric == "npv":
        sel = ~pred
        ind = ~pos[sel]
    elif metric == "accuracy":
        sel = np.ones(rows.shape[0], dtype=bool)
        ind = pos == pred
    elif metric == "selection_rate":
        sel = np.ones(rows.shape[0], dtype=bool)
        ind = pred
    else:  # pragma: no cover
        raise ValueError(metric)
    return rows[sel], np.asarray(ind, dtype=bool)


def _metric_key(arrays: _Arrays, metric: str) -> str:
    return {"se": arrays.se_key, "sp": arrays.sp_key}.get(metric, metric)


def _level_row(
    arrays: _Arrays, attr: _Attribute, lv: _Level, ops: list[OperatingPoint]
) -> dict[str, Any]:
    rows = lv.rows
    pos = arrays.pos[rows]
    n = lv.n
    events = int(pos.sum())
    n_units = arrays.units(rows)
    event_units = arrays.units(rows[pos]) if events else 0
    tier_flags = precision_flags(n_units, event_units)
    metrics: dict[str, Any] = {}
    for op in ops:
        pred = arrays.predicted[op.id][rows]
        block: dict[str, Any] = {"two_by_two": _two_by_two(pos, pred)}
        for metric in PROPORTION_METRICS:
            sub_rows, ind = _conditioned(rows, pos, pred, metric)
            key = _cell_key(attr.name, lv.label, op.id, _metric_key(arrays, metric))
            block[_metric_key(arrays, metric)] = _cell(_proportion_cell(arrays, sub_rows, ind, key))
        metrics[op.id] = block
    metrics["auroc"] = _cell(_auroc_cell(arrays, rows, _cell_key(attr.name, lv.label, "auroc")))
    brier, detail = _brier_cell(arrays, rows, _cell_key(attr.name, lv.label, "brier"))
    metrics["brier"] = _cell(brier, detail)
    return {
        "attribute": attr.name,
        "level": lv.label,
        "prespecified": attr.prespecified,
        "source": attr.source,
        "is_reference": lv.label == attr.reference and not lv.is_unknown,
        "is_unknown_row": lv.is_unknown,
        "n": n,
        "events": events,
        "n_units": n_units,
        "event_units": event_units,
        "tier": tier_flags[0] if tier_flags else None,
        "metrics": metrics,
    }


def _differences(
    arrays: _Arrays,
    attr: _Attribute,
    lv: _Level,
    other_rows: np.ndarray,
    kind: str,
    ops: list[OperatingPoint],
) -> dict[str, Any]:
    """``diff_vs_reference`` / ``diff_vs_complement`` for one level: level minus other."""
    out: dict[str, Any] = {}
    rows = lv.rows
    pos_a, pos_b = arrays.pos[rows], arrays.pos[other_rows]
    for op in ops:
        pred_a, pred_b = arrays.predicted[op.id][rows], arrays.predicted[op.id][other_rows]
        block: dict[str, Any] = {}
        for metric in PROPORTION_METRICS:
            ra, ia = _conditioned(rows, pos_a, pred_a, metric)
            rb, ib = _conditioned(other_rows, pos_b, pred_b, metric)
            mkey = _metric_key(arrays, metric)
            key = _cell_key(attr.name, lv.label, kind, op.id, mkey)
            block[mkey] = _cell(_proportion_difference(arrays, ra, ia, rb, ib, key))
        out[op.id] = block
    key = _cell_key(attr.name, lv.label, kind, "auroc")
    cell, detail = _auroc_difference(arrays, rows, other_rows, key)
    out["auroc"] = _cell(cell, detail)
    return out


def _null_differences(arrays: _Arrays, ops: list[OperatingPoint]) -> dict[str, Any]:
    """The reference row's own ``diff_vs_reference``: the same keys, every value null."""
    return {
        **{op.id: {_metric_key(arrays, m): None for m in PROPORTION_METRICS} for op in ops},
        "auroc": None,
    }


def _mirror(number: Number) -> Number:
    """``-x`` of a difference Number: the estimate negated and the bounds swapped."""
    return Number(
        est=None if number.est is None else -number.est,
        ci_lo=None if number.ci_hi is None else -number.ci_hi,
        ci_hi=None if number.ci_lo is None else -number.ci_lo,
        ci_level=number.ci_level,
        method=number.method,
        n=number.n,
        k=number.k,
        n_pos=number.n_pos,
        n_neg=number.n_neg,
        n_cases=number.n_cases,
        flags=list(number.flags),
        suppressed=number.suppressed,
        not_estimable_reason=number.not_estimable_reason,
    )


def _mirror_cell(cell: dict[str, Any]) -> dict[str, Any]:
    """A serialised difference cell with its sign reversed (``fpr_gap`` from the Sp gap)."""
    out = dict(cell)
    out["number"] = _mirror(Number(**cell["number"])).as_dict()
    if cell.get("analytic") is not None:
        out["analytic"] = _mirror(Number(**cell["analytic"])).as_dict()
    return out


def _fairness(
    decl: Declarations,
    arrays: _Arrays,
    attrs: list[_Attribute],
    rows: list[dict[str, Any]],
    ops: list[OperatingPoint],
) -> dict[str, Any] | None:
    """The ``fairness`` block: the reference-level differences re-read as gaps.

    Measured, never mitigated (R2 section 4). Kleinberg / Chouldechova impossibility is
    cited there **[unverified - cited from memory]** and the marking is carried, not
    resolved, here. ``criterion_of_interest`` and ``bound`` are echoed verbatim; the
    comparison to the bound is E7's and no status is emitted today.
    """
    if decl.fairness is None:
        return None
    name = str(decl.fairness["attribute"])
    attr = next((a for a in attrs if a.name == name), None)
    if attr is None:
        raise HaltError(
            "H09", "fairness block references attribute absent from the table", {"attribute": name}
        )
    gaps: list[dict[str, Any]] = []
    for r in rows:
        if r["attribute"] != name or r["is_reference"]:
            continue
        diff = r["diff_vs_reference"]
        if diff is None:  # no reference level exists (every row of the attribute is Unknown)
            continue
        per_op: dict[str, Any] = {}
        for op in ops:
            d = diff[op.id]
            per_op[op.id] = {
                "tpr_gap": d[arrays.se_key],
                "fpr_gap": _mirror_cell(d[arrays.sp_key]),
                "ppv_gap": d["ppv"],
                "npv_gap": d["npv"],
                "selection_rate_gap": {**d["selection_rate"], "label": SELECTION_RATE_LABEL},
            }
        gaps.append(
            {
                "level": r["level"],
                "is_unknown_row": r["is_unknown_row"],
                "n": r["n"],
                "operating_points": per_op,
                "auroc_gap": diff["auroc"],
                "calibration": {
                    "oe": None,
                    "slope": None,
                    "intercept": None,
                    "not_estimable_reason": "not_computed_this_run",
                },
            }
        )
    return {
        "attribute": name,
        "reference_level": attr.reference,
        "reference_rule": attr.reference_rule,
        "criterion_of_interest": decl.fairness["criterion_of_interest"],
        "bound": decl.fairness.get("bound"),
        "author": decl.fairness.get("author"),
        "date": decl.fairness.get("date"),
        "justification": decl.fairness.get("justification"),
        "measured_not_mitigated": True,
        "gap_definitions": {
            "tpr_gap": f"{arrays.se_key} of the level minus the reference level",
            "fpr_gap": f"(1 - {arrays.sp_key}) of the level minus the reference level",
            "ppv_gap": "ppv of the level minus the reference level",
            "npv_gap": "npv of the level minus the reference level",
            "auroc_gap": "auroc of the level minus the reference level",
            "selection_rate_gap": (
                "share of rows called positive at the operating point, level minus "
                "reference level; " + SELECTION_RATE_LABEL
            ),
        },
        "impossibility_citation": (
            "R2 section 4: Kleinberg / Chouldechova impossibility "
            "[unverified - cited from memory in R2; not resolved here]"
        ),
        "gaps": gaps,
    }


def subgroup_analysis(
    table: Table,
    decl: Declarations,
    mask: np.ndarray,
    *,
    plan: ClusterPlan | None = None,
    cluster_ids: Sequence[Any] | np.ndarray | None = None,
    policy: BootstrapPolicy | None = None,
    level: float = DEFAULT_LEVEL,
) -> SubgroupReport:
    """The subgroup, per-attribute and fairness blocks for one run.

    ``table`` is the validated :class:`~proofpack.io.schema.Table`, ``mask`` the analysis
    rows from :func:`~proofpack.io.schema.analysis_mask`, ``decl`` the validated
    declarations (the operating points are taken from it, thresholds already declared).
    ``cluster_ids`` is the case column over the *analysed* rows; when omitted and the
    table has a ``case_id`` column, that column is used (the day-4 handoff's first
    "tomorrow needs"). What is inspected: ``test_a_case_id_column_is_used_even_when_
    not_passed_and_detected_clustering_routes_everything`` omits the argument over a
    repeating ``case_id`` column under ``clustering.unit: none`` and reads every
    proportion Number's method and the cells' ``clustering_route``;
    ``test_a_supplied_plan_that_contradicts_the_case_column_is_refused`` supplies a
    non-clustered plan over the same column and an ids vector of the wrong length. A
    declared ``case_id`` unit with no ``case_id`` column raises in
    :func:`~proofpack.stats.bootstrap.plan_clustering`. ``plan`` is the run-level
    :class:`ClusterPlan`; when omitted it is resolved here by ``plan_clustering``,
    declared or detected. Every cell receives the case ids **sliced with its rows**.
    """
    arrays = _arrays(table, decl, mask, plan, cluster_ids, policy, level)
    ops = list(decl.operating_points)
    attrs = _attributes(table, decl, mask)
    rows: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    for attr in attrs:
        all_rows = (
            np.concatenate([lv.rows for lv in attr.levels])
            if attr.levels
            else np.empty(0, dtype=np.intp)
        )
        ref = attr.level(attr.reference) if attr.reference is not None else None
        for lv in attr.levels:
            row = _level_row(arrays, attr, lv, ops)
            if ref is None:
                row["diff_vs_reference"] = None
            elif lv.label == ref.label:
                row["diff_vs_reference"] = _null_differences(arrays, ops)
            else:
                row["diff_vs_reference"] = _differences(
                    arrays, attr, lv, ref.rows, "diff_vs_reference", ops
                )
            complement = np.setdiff1d(all_rows, lv.rows, assume_unique=True)
            row["diff_vs_complement"] = (
                _differences(arrays, attr, lv, complement, "diff_vs_complement", ops)
                if complement.shape[0]
                else None
            )
            rows.append(row)
        blocks.append(_attribute_block(arrays, attr, ops))
    fairness = _fairness(decl, arrays, attrs, rows, ops)
    return SubgroupReport(rows, blocks, fairness)


def _attribute_block(
    arrays: _Arrays, attr: _Attribute, ops: list[OperatingPoint]
) -> dict[str, Any]:
    per_op: dict[str, dict[str, list[tuple[int, int]]]] = {}
    evaluable = [lv for lv in attr.levels if not lv.is_unknown]
    for op in ops:
        se_counts: list[tuple[int, int]] = []
        sp_counts: list[tuple[int, int]] = []
        for lv in evaluable:
            pos = arrays.pos[lv.rows]
            pred = arrays.predicted[op.id][lv.rows]
            t = _two_by_two(pos, pred)
            if t["tp"] + t["fn"]:
                se_counts.append((t["tp"], t["fn"]))
            if t["tn"] + t["fp"]:
                sp_counts.append((t["tn"], t["fp"]))
        per_op[op.id] = {arrays.se_key: se_counts, arrays.sp_key: sp_counts}
    return {
        "attribute": attr.name,
        "prespecified": attr.prespecified,
        "source": attr.source,
        "declared": attr.declared,
        "reference_level": attr.reference,
        "reference_rule": attr.reference_rule,
        "level_order": [lv.label for lv in attr.levels],
        "has_unknown_row": attr.unknown is not None,
        "n_unknown_missing": attr.n_missing,
        "n_outside_bands": attr.n_outside_bands,
        "bands": attr.bands,
        "bands_source": attr.bands_source,
        "complement_definition": (
            "every other analysed row of this attribute, including the Unknown/missing row"
        ),
        "heterogeneity": heterogeneity_footnote(per_op, clustering_route=arrays.plan.route),
    }
