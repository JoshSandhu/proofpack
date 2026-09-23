"""Number formatting for the rendered documents: D4 section 1.2, implemented once, here.

The renderer inserts values from the structured document and nothing else; no template
does arithmetic and no other module rounds (CLAUDE.md: numbers come only from the
engine - this module changes the *printing* of a value the engine computed, never the
value, and ``run.json`` keeps full precision). The rules, each with the D4 line it
implements and the literal test that feeds it (``tests/test_render_format.py``):

* **Proportions** (a Number with ``k`` and ``n``; D4 section 1.2 first bullet): ``k/n
  (xx.x%)`` then the interval in percentage points to one decimal, ``[lo.l, hi.h]``.
  ``81/263 (30.8%) [25.5, 36.6]``. A Number with ``n`` but no ``k`` (the accuracy-like
  Numbers the engine gives without a numerator) prints ``(xx.x%) [lo.l, hi.h]``.
* **Three-decimal quantities** (AUROC, AUPRC, Brier, IPA, O:E, slope, intercept, PSI;
  third bullet), and every other non-proportion estimate (LR+, LR-, DOR, Youden,
  balanced accuracy, F1, MCC - D4 names no rule for these; three decimals is the
  recorded choice): ``0.795 [0.742, 0.841]``.
* **Differences in percentage points with sign** (third bullet): ``-3.2 [-6.1, -0.4]``
  with the Unicode minus D4 prints (U+2212) and an explicit ``+``. An AUROC difference
  is signed to three decimals on the unit scale.
* **p-values**: three decimals, ``<0.001`` below.
* **Suppressed** (fourth bullet): the marker ``‡`` and nothing else - no digit
  from the cell, no count.
* **A typed reason** (fourth bullet): ``n.e. (<reason>)`` - the reason code printed
  inline; no digit from ``est`` even when the engine carried one beside the reason.
* **Tier superscripts** (fifth bullet; R2 section 3.3, a ProofPack convention):
  ``ᵃ`` n < 10, ``ᵇ`` 10 <= n < 30 or events < 5, ``ᶜ`` Wilson half-width
  > 0.10, appended to the printed cell from the Number's ``flags``.
* **Counts** (n, k, events) are the only bare integers.
* **``[unverified]``** markings in any string pass through verbatim (:func:`text`).

Rounding is Python's ``format(x, ".1f")`` / ``".3f"``: the correctly rounded decimal of
the binary double, ties resolved by that value, never by a second rounding. Percentages
are ``x * 100`` formatted once.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

SUPPRESSED_MARK = "‡"
NOT_ESTIMABLE = "n.e."
MINUS = "−"
TIER_SUPERSCRIPTS: dict[str, str] = {
    "not_evaluable_shown_for_transparency": "ᵃ",
    "very_low_precision": "ᵇ",
    "imprecise": "ᶜ",
}
#: Metric ids printed as proportions, three-decimal quantities, or signed differences.
PROPORTION_IDS: frozenset[str] = frozenset(
    {
        "sensitivity",
        "specificity",
        "ppa",
        "npa",
        "ppv",
        "npv",
        "accuracy",
        "prevalence",
        "selection_rate",
    }
)
DIFFERENCE_PP_IDS: frozenset[str] = frozenset(
    {"tpr_gap", "fpr_gap", "ppv_gap", "npv_gap", "selection_rate_gap"}
)
DIFFERENCE_3DP_IDS: frozenset[str] = frozenset({"auroc_gap"})
KINDS: tuple[str, ...] = ("proportion", "three_dp", "difference_pp", "difference_3dp")


def kind_for(metric_id: str | None, *, difference: bool = False) -> str:
    """The printing rule for a metric id (a difference of a proportion is in points)."""
    if metric_id in DIFFERENCE_PP_IDS:
        return "difference_pp"
    if metric_id in DIFFERENCE_3DP_IDS:
        return "difference_3dp"
    if difference:
        return "difference_pp" if metric_id in PROPORTION_IDS else "difference_3dp"
    if metric_id in PROPORTION_IDS:
        return "proportion"
    return "three_dp"


def _signed(x: float, places: int) -> str:
    s = format(abs(x), f".{places}f")
    if x < 0 and float(s) != 0.0:
        return MINUS + s
    return "+" + s if float(s) != 0.0 else s


def _plain(x: float, places: int) -> str:
    s = format(x, f".{places}f")
    return s.replace("-", MINUS)


def percent(x: float, places: int = 1) -> str:
    """``x`` on the unit scale as a percentage string without the sign: ``30.8``."""
    return _plain(x * 100.0, places)


def count(n: Any) -> str:
    """A bare integer count; ``None`` prints as an em dash (U+2014)."""
    return "—" if n is None else str(int(n))


def scalar(x: Any, places: int = 3) -> str:
    """An engine scalar (a compared value, an attainability bound) at ``places``."""
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return str(x)
    return _plain(float(x), places)


def declared(x: Any) -> str:
    """A number the manufacturer declared (a threshold, a criterion value, a prevalence, a
    fairness bound), printed with every digit ``run.json`` carries and no rounding: the
    shortest decimal that reads back to the same double (Python's ``repr``), written
    positionally. ``tests/test_render_format.py::test_declared_values_print_every_digit``
    feeds ``0.4275`` -> ``0.4275``, ``0.8525`` -> ``0.8525``, ``0.8`` -> ``0.8``,
    ``0.00001`` -> ``0.00001``, ``1`` -> ``1`` (repair 1, lens FA-B4: ``0.4275`` printed
    ``0.427`` under a caption saying "as the manufacturer wrote the value")."""
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return str(x)
    return format(Decimal(repr(float(x))), "f").replace("-", MINUS)


def p_value(p: Any) -> str:
    if p is None:
        return "—"
    p = float(p)
    return "<0.001" if p < 0.001 else _plain(p, 3)


def text(s: Any) -> str:
    """A string slot, verbatim: ``[unverified]`` markings survive to the page."""
    return "" if s is None else str(s)


def tiers(number: dict[str, Any]) -> str:
    return "".join(
        TIER_SUPERSCRIPTS[f] for f in number.get("flags") or [] if f in TIER_SUPERSCRIPTS
    )


def number(num: dict[str, Any] | None, kind: str = "three_dp") -> str:
    """One Number rendered per D4 section 1.2 under ``kind`` (see :data:`KINDS`)."""
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    if num is None:
        return NOT_ESTIMABLE
    if num.get("suppressed"):
        return SUPPRESSED_MARK
    reason = num.get("not_estimable_reason")
    if reason is not None or num.get("ci_lo") is None or num.get("ci_hi") is None:
        return f"{NOT_ESTIMABLE} ({reason or 'no_interval'})" + tiers(num)
    est, lo, hi = float(num["est"]), float(num["ci_lo"]), float(num["ci_hi"])
    if kind == "proportion":
        head = f"({percent(est)}%)"
        if num.get("k") is not None and num.get("n") is not None:
            head = f"{count(num['k'])}/{count(num['n'])} {head}"
        body = f"{head} [{percent(lo)}, {percent(hi)}]"
    elif kind == "three_dp":
        body = f"{_plain(est, 3)} [{_plain(lo, 3)}, {_plain(hi, 3)}]"
    elif kind == "difference_pp":
        body = f"{_signed(est * 100.0, 1)} [{_signed(lo * 100.0, 1)}, {_signed(hi * 100.0, 1)}]"
    else:
        body = f"{_signed(est, 3)} [{_signed(lo, 3)}, {_signed(hi, 3)}]"
    return body + tiers(num)


def method(num: dict[str, Any] | None) -> str:
    return "—" if not num else text(num.get("method"))


# ------------------------------------------------ facets of one Number (build day 9, E9)
#
# The sentence renderer (:mod:`proofpack.render.sentences`) prints a Number's parts in
# prose; each part is printed here by the same rule :func:`number` applies to the whole
# cell, so a sentence and a table state one figure one way.


def _has_interval(num: dict[str, Any]) -> bool:
    return (
        not num.get("suppressed")
        and num.get("not_estimable_reason") is None
        and num.get("ci_lo") is not None
        and num.get("ci_hi") is not None
    )


def bound(x: float, kind: str) -> str:
    """One value on the printing scale of ``kind``, without a unit sign."""
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    if kind == "proportion":
        return percent(x)
    if kind == "three_dp":
        return _plain(x, 3)
    if kind == "difference_pp":
        return _signed(x * 100.0, 1)
    return _signed(x, 3)


def estimate(num: dict[str, Any] | None, kind: str) -> str:
    """The estimate alone (``30.8%``, ``0.795``, ``+7.0``) with its tier superscripts;
    ``‡`` when suppressed; ``n.e. (<reason>)`` when a typed reason or no interval stands,
    never a digit from ``est`` (D4 section 1.2)."""
    if num is None:
        return NOT_ESTIMABLE
    if num.get("suppressed"):
        return SUPPRESSED_MARK
    if not _has_interval(num):
        return f"{NOT_ESTIMABLE} ({num.get('not_estimable_reason') or 'no_interval'})" + tiers(num)
    body = bound(float(num["est"]), kind)
    return (body + "%" if kind == "proportion" else body) + tiers(num)


def interval(num: dict[str, Any] | None, kind: str) -> str:
    """The two bounds as a table cell prints them inside its brackets: ``25.5, 36.6``;
    ``no interval`` when the Number has none."""
    if num is None or not _has_interval(num):
        return "no interval"
    return f"{bound(float(num['ci_lo']), kind)}, {bound(float(num['ci_hi']), kind)}"


def one_bound(num: dict[str, Any] | None, which: str, kind: str) -> str:
    """``ci_lo`` or ``ci_hi`` alone, with ``%`` for a proportion (``25.5%``)."""
    if num is None or not _has_interval(num):
        return "no interval"
    body = bound(float(num[which]), kind)
    return body + "%" if kind == "proportion" else body
