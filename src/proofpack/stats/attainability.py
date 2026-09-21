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

which is the closed form the oracle test recomputes by hand. It rises with ``n`` and never
reaches 1: at n = 30 it is 0.8865, at n = 50 0.9287, at n = 200 0.9812 (95 %). A ``>=``
criterion whose ``value`` exceeds it cannot be met by any outcome at that ``n``, whatever
the model does - which is the fact the pack states, and all it states.

Under clustering the rendered interval is a cluster bootstrap, not Wilson, and the
effective sample is smaller than ``n`` rows: the figure here is the i.i.d. Wilson bound
over the rows, so ``attainable_at_n: false`` is exact (not attainable even with independent
rows) and ``true`` says only that the row count alone does not rule the criterion out.
The criteria row records ``n`` and the Number's method beside the figure so a reader can
see which case applies.
"""

from __future__ import annotations

from proofpack.stats.proportions import wilson_bounds

#: Metric ids whose Number is a plain proportion ``k / n`` with a Wilson (or cluster
#: bootstrap) interval, for which the k = n bound is the attainability figure. F1, MCC,
#: balanced accuracy, the likelihood ratios and the DOR are not proportions of one
#: denominator and get ``null`` (D1: "null for non-proportion metrics").
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
