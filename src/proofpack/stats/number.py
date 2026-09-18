"""The ``Number`` object - every rendered quantity in a ProofPack document.

D1 section 4.1. The single invariant enforced here, in code, is:

    **No Number may exist without a confidence interval, unless it carries an
    explicit typed reason saying why one is not available.**

There is no silent fallback anywhere in this module. A method that cannot be
computed (zero cell, single class, clustered data, too few events, a missing
optional dependency) produces ``ci_lo = ci_hi = None`` *and* a
``not_estimable_reason`` drawn from :data:`NOT_ESTIMABLE_REASONS`. Constructing a
Number with neither a CI nor a reason raises ``ValueError``.

The dataclass is **frozen**: the invariant is checked in ``__post_init__``, so a
mutable Number would let a caller strip an interval off an already-validated
object and escape the check (the JSON schema would still catch it downstream, but
only if the document is validated). Assigning to any field raises
``dataclasses.FrozenInstanceError``. ``flags`` is the one field still appended to
in place, by :meth:`Number.with_precision_flags`; flags are advisory and cannot
violate the invariant.

This module is numpy-free and scipy-free on purpose: it is imported by everything.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

#: ``method`` enum (D1 section 4.1) plus two additions made on build day 2/3, both
#: recorded in the day-2 handoff:
#:   ``logit_delta``  - PPV/NPV at a declared prevalence, logit-scale delta method
#:                      (D1 says "logit-scale interval"; the enum only had ``log_delta``).
#:   ``newcombe11``   - Newcombe 1998 method 11 (continuity-corrected score),
#:                      shown alongside method 10 where the brief asks for both.
METHODS: frozenset[str] = frozenset(
    {
        "wilson",
        "wilson_cc",
        "clopper_pearson",
        "newcombe10",
        "newcombe11",
        "newcombe_paired",
        "delong_logit",
        "delong_wald",
        "cluster_bootstrap_percentile",
        "bootstrap_percentile",
        "bootstrap_bca",
        "irls_wald",
        "log_delta",
        "logit_delta",
        "chi2_psi",
        "exact_mcnemar",
        "cc_mcnemar",
        "none",
    }
)

#: Typed reasons a quantity has no interval (or no value at all). Every one of
#: these is a *known limitation of a named method*, never a fallback.
NOT_ESTIMABLE_REASONS: frozenset[str] = frozenset(
    {
        # denominators
        "zero_denominator",  # k/n with n = 0
        "single_class",  # no positives or no negatives in the analysed rows
        "insufficient_positives",  # fewer positives than the method needs
        "insufficient_negatives",
        # 2x2 degeneracies
        "zero_cell_log_undefined",  # LR+/LR-/DOR: a zero cell makes log(.) undefined
        "zero_cell_logit_undefined",  # PPV/NPV at prevalence: Se or Sp at a boundary
        # estimate on 0 or 1, where the delta method is invalid; also a resample
        # distribution of zero width, where the bootstrap cannot express uncertainty
        # either and a printed (x, x) would claim a certainty the data do not support
        "boundary_estimate",
        # methods deliberately not available yet / not valid here
        "analytic_ci_unavailable",  # F1, MCC: no standard closed form; bootstrap on day 4
        "clustered_data_analytic_ci_invalid",  # rows are not independent (case_id)
        "scipy_unavailable",  # Clopper-Pearson for 0 < k < n needs scipy.stats.beta
        "not_computed_this_run",
        # bootstrap (build day 4)
        # an outcome class the cluster resampler cannot meaningfully vary. A stratum
        # holding one case is drawn one-from-one, so its rows are frozen into every
        # resample: the class is refused when every stratum supplying it is frozen, and
        # also when the frozen strata hold at least a fifth of the class's resampling
        # variance weight, which is where the interval stops being the interval it
        # claims to be. A case carrying both outcomes counts towards both classes, but
        # counting is not the test - see stats.bootstrap.Resampler.deficient_class and
        # MAX_FROZEN_VARIANCE_SHARE for the two halves and the measurements behind them.
        "insufficient_clusters",
        "degenerate_resamples",  # too few resamples gave a defined statistic
        # subgroup differences (build day 5). Inspects the set intersection of the case
        # ids on the two sides of a difference (a level against its reference level, or
        # against its complement). Under clustering the two sides of an *unpaired*
        # difference must be independent samples; a case with rows on both sides makes
        # them dependent, so neither Newcombe-10, the unpaired DeLong variance nor a
        # two-sided cluster bootstrap describes the difference, and it is refused rather
        # than computed on a false independence. See stats.subgroups.
        "cases_span_both_groups",
        # the exploratory heterogeneity footnote (stats.subgroups): a homogeneity test
        # needs at least two evaluable levels of the attribute to compare
        "insufficient_levels",
        # calibration (build day 6, stats.calibration). Two suppression reasons, kept
        # apart because the remedy differs: a logit or "other" score is not a
        # probability at all (the declared type rides in the detail beside it); a
        # probability declared lower_is_positive is not the probability of the
        # *positive* class, and 1 - p would assume it is the negative class's, which
        # the customer did not declare - refused, never transformed.
        "score_not_probability",
        "score_not_positive_class_probability",
        # the module's own IRLS logistic fits, typed instead of inf / nan / a traceback
        "irls_not_converged",  # the iteration budget ran out
        "complete_separation",  # every fitted probability equals its label; no MLE
        "constant_score",  # logit(p) takes one value; the slope is not identifiable
        # the prevalence-only reference Brier under a resampler that holds the
        # prevalence fixed in every resample (stratified by outcome): the draw has no
        # width by construction, not because of the data
        "fixed_by_outcome_stratification",
    }
)

#: Flags are advisory annotations that never suppress a number (R2 section 3.3).
FLAGS: frozenset[str] = frozenset(
    {
        "not_evaluable_shown_for_transparency",  # n < 10
        "very_low_precision",  # 10 <= n < 30, or events < 5
        "imprecise",  # Wilson half-width > 0.10
        "wald_interval_exceeds_unit_range",  # DeLong Wald CI outside [0, 1]
        # F1 and MCC only: no analytic interval, and whether to bootstrap them or
        # drop them from the document is the customer-facing presentation decision
        # in day-2 question 1, still unanswered. The AUROC paths dropped this flag
        # on build day 4, when stats.bootstrap.auroc_ci landed and made it false.
        "ci_pending_bootstrap",
        "continuity_corrected",
        "shown_alongside_wilson_at_boundary",  # Clopper-Pearson at 0/n and n/n
        # The X2 clustered auto-switch (build day 4). These flags ride on the Number
        # that IS rendered, so the reader of the document sees that an analytic method
        # was refused; the typed reason itself rides on the companion Number.
        "delong_refused_clustered",
        "wilson_refused_clustered",
        # Build day 5: a subgroup *difference* under clustering. Newcombe method 10
        # assumes independent rows on each side; it is refused and the difference is
        # cluster-bootstrapped with each side resampled independently. The flag rides on
        # the rendered difference; the typed reason rides on its companion.
        "newcombe_refused_clustered",
        # R2 1.3: a class below 10 gets the stratified bootstrap as its rendered
        # interval, with the DeLong Number carried alongside. Recorded, never silent.
        "analytic_ci_replaced_small_class",
        # Build day 6, stats.calibration. The 200/200 convention after Van Calster
        # 2019: fewer than 200 events or fewer than 200 non-events in the analysed rows.
        # An annotation on the decile curve and the block (DEC-08), never a suppression.
        "below_200_events_or_nonevents",
        # scores at exactly 0 or 1 were clipped to [CLIP_EPS, 1 - CLIP_EPS] for the
        # logit-scale models; the count of clipped rows is in the block
        "scores_clipped_for_logit",
        # X2 under clustering: the log-delta O:E interval and the IRLS Wald intervals
        # are refused and the cluster bootstrap rendered; the typed reason rides on the
        # companion Number, these ride on the rendered one
        "log_delta_refused_clustered",
        "irls_wald_refused_clustered",
    }
)


@dataclass(frozen=True)
class Number:
    """One rendered quantity: estimate, interval, the method that produced it, and n.

    ``n``/``k`` are the proportion denominators. Discrimination statistics set
    ``n_pos``/``n_neg`` (and ``n_cases`` when clustered) instead, per D1 section 4.1.
    """

    est: float | None
    ci_lo: float | None = None
    ci_hi: float | None = None
    ci_level: float = 0.95
    method: str = "none"
    n: int | None = None
    k: int | None = None
    n_pos: int | None = None
    n_neg: int | None = None
    n_cases: int | None = None
    flags: list[str] = field(default_factory=list)
    suppressed: bool = False
    not_estimable_reason: str | None = None

    def __post_init__(self) -> None:
        if self.method not in METHODS:
            raise ValueError(f"unknown method {self.method!r}")
        if self.not_estimable_reason is not None and self.not_estimable_reason not in (
            NOT_ESTIMABLE_REASONS
        ):
            raise ValueError(f"unknown not_estimable_reason {self.not_estimable_reason!r}")
        for f in self.flags:
            if f not in FLAGS:
                raise ValueError(f"unknown flag {f!r}")
        if self.suppressed:
            if not (self.est is None and self.ci_lo is None and self.ci_hi is None):
                raise ValueError("a suppressed Number must carry no est and no interval")
            return
        has_ci = self.ci_lo is not None and self.ci_hi is not None
        if has_ci:
            if self.method == "none":
                raise ValueError("a Number with an interval must name the method that made it")
            if self.ci_lo > self.ci_hi:  # type: ignore[operator]
                raise ValueError("ci_lo > ci_hi")
            if self.not_estimable_reason is not None:
                raise ValueError("a Number with an interval must not carry a not_estimable_reason")
        else:
            # THE invariant: no Number without a CI, unless it says why, in the enum.
            if self.not_estimable_reason is None:
                raise ValueError(
                    "Number has no confidence interval and no not_estimable_reason "
                    "(D1 section 4.1: nothing is rendered without a CI)"
                )
            if self.ci_lo is not None or self.ci_hi is not None:
                raise ValueError("a half-open interval is never valid")

    @property
    def has_ci(self) -> bool:
        return self.ci_lo is not None and self.ci_hi is not None

    @property
    def half_width(self) -> float | None:
        if not self.has_ci:
            return None
        return (self.ci_hi - self.ci_lo) / 2.0  # type: ignore[operator]

    #: The two R2 section 3.3 tiers. They are ordered and mutually exclusive: a Number
    #: must never carry both, or the document states two different things about the
    #: same cell.
    PRECISION_TIERS = ("not_evaluable_shown_for_transparency", "very_low_precision")

    def with_precision_flags(self) -> Number:
        """Attach the R2 section 3.3 precision tier. Returns ``self`` for chaining.

        A tier already present is left alone rather than joined by a second one: under
        clustering the caller assigns the tier from the *case* count, which is the
        effective sample size, and ``n`` here is the row count.
        """
        n = self.n
        if n is not None and not set(self.PRECISION_TIERS) & set(self.flags):
            if n < 10:
                self.flags.append("not_evaluable_shown_for_transparency")
            elif n < 30:
                self.flags.append("very_low_precision")
        hw = self.half_width
        if hw is not None and hw > 0.10 and "imprecise" not in self.flags:
            self.flags.append("imprecise")
        return self

    def as_dict(self) -> dict[str, Any]:
        """Serialise, dropping the denominator keys that do not apply."""
        d = asdict(self)
        for key in ("n", "k", "n_pos", "n_neg", "n_cases"):
            if d[key] is None:
                del d[key]
        return d


def not_estimable(reason: str, *, est: float | None = None, **kw: Any) -> Number:
    """Build a Number that has no interval, with an explicit typed reason."""
    return Number(est=est, not_estimable_reason=reason, **kw)
