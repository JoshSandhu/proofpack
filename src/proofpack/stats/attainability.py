"""``stats.attainability`` - the largest lower bound a proportion can reach at the observed n.

D1 section 2, attainability paragraph (v2 section 4 ``stats.attainability``): for each
``ci_lower_bound`` criterion the engine reports the largest lower bound achievable at the
observed ``n`` - the Wilson lower bound at ``k = n`` - and marks "criterion not attainable
at observed n" when that is below the criterion's ``value``. **No sample-size advice is
emitted** (v2 section 1 OUT; the "139 positives needed" figure of F8 is test-only and never
rendered).

Formula (R2 section 1.1: the Wilson score interval, Newcombe 1998 method 3, ProofPack's
default; :func:`proofpack.stats.proportions.wilson_bounds` is the one implementation and
is what this module calls). With ``p = k / n`` and ``z`` the two-sided normal quantile,

    lower = (2 n p + z^2 - z sqrt(z^2 + 4 n p (1 - p))) / (2 (n + z^2))

and at ``k = n`` (``p = 1``) the square root collapses to ``z``, so

    max_lower_bound_at_n = n / (n + z^2)

which is the closed form the oracle test recomputes by hand (``tests/test_criteria.py``:
0.886486606826 at n = 30, 0.928652400867 at n = 50, 0.981154673623 at n = 200, 95 %;
``test_the_bound_rises_with_n_and_never_reaches_one`` inspects n = 1 ... 100000). The pack
states the figure and, for a ``>=`` / ``>`` criterion, whether ``value`` is at or below it;
nothing else.

The figure is the Wilson bound and belongs beside a Wilson interval only. For a
``ci_lower_bound`` criterion on a metric in :data:`PROPORTION_METRICS`, ``criteria._row``
fills ``attainable_at_n`` / ``max_lower_bound_at_n`` when the Number's ``method`` is
``wilson`` (``criteria.ATTAINABILITY_METHOD``) and its ``n`` is an ``int`` above 0, and
leaves both ``null`` with ``detail.attainability_not_computed: method_not_wilson`` when
the ``method`` is anything else, whatever ``n`` (``tests/test_criteria.py::
test_a_method_none_number_at_n_zero_or_n_null_is_annotated_method_not_wilson``: at
``02d00c5`` a ``zero_denominator`` Number at n = 0 carried no annotation). Under a
``ci_upper_bound`` or ``point_estimate`` criterion, or on a metric outside the set, both
are ``null`` and ``detail`` has no attainability key (the same test, a Wilson Number
under each). Measured at
``ab729d3`` (lens 1 of 21 September, B2): a cluster-bootstrap percentile interval on 30
negatives in 15 two-row cases with one wrong row (``k`` 29, ``n_cases`` 15) had ``ci_lo``
0.9 - the wrong row's case is absent from about a third of the resamples - against the
k = n Wilson figure 0.8865, so a ``ci_lower_bound >= 0.89`` criterion was ``met`` in a row
that also carried ``attainable_at_n: false``. ``tests/test_criteria.py::
test_a_cluster_bootstrap_cell_gets_no_attainability_flag`` feeds that construction.
"""

from __future__ import annotations

from proofpack.stats.proportions import wilson_bounds

#: Metric ids whose Number is a plain proportion ``k / n``; the attainability figure is
#: filled for these when the Number's interval is Wilson (``criteria.ATTAINABILITY_METHOD``).
#: F1, MCC, balanced accuracy, the likelihood ratios and the DOR are not proportions of
#: one denominator and get ``null`` (D1: "null for non-proportion metrics").
PROPORTION_METRICS: frozenset[str] = frozenset(
    {"sensitivity", "specificity", "ppa", "npa", "ppv", "npv", "accuracy", "prevalence"}
)


def max_lower_bound_at_n(n: int, level: float = 0.95) -> float:
    """The Wilson lower bound at ``k = n`` (``n / (n + z^2)``), via ``wilson_bounds``."""
    if n <= 0:
        raise ValueError("n must be positive")
    return wilson_bounds(n, n, level)[0]


def attainable(value: float, n: int, comparator: str, level: float = 0.95) -> bool | None:
    """Whether a ``ci_lower_bound`` criterion ``lower_bound <comparator> value`` can be met
    at ``n``: for ``>=`` the k = n bound must reach ``value``, for ``>`` exceed it. For
    ``<=`` and ``<`` the lower bound can be 0 (k = 0), so the question does not arise and
    the answer is ``None`` (the figure is still reported)."""
    bound = max_lower_bound_at_n(n, level)
    if comparator == ">=":
        return bound >= value
    if comparator == ">":
        return bound > value
    if comparator in ("<=", "<"):
        return None
    raise ValueError(f"unknown comparator {comparator!r}")
