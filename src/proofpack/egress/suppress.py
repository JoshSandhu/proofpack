"""k-suppression before serialisation (D1 section 6, "Aggregate payload rules", second
bullet): *any cell with n < 10 or events < 5 or non-events < 5 -> suppressed: true, values
null (defaults from v2 section 2; customer may only tighten)*.

What a "cell" is here (recorded in ``schema/egress_schema.json`` ``x-proofpack.
suppression_cells``): a subgroup row (its ``n`` rows and ``events``), a fairness gap row,
a calibration decile bin (``n``, ``events``), an overall two-by-two table (``n = tp + fn +
fp + tn``, ``events = tp + fn``, ``non-events = fp + tn``), and every Number on its own
counts - ``n`` and, where the Number carries them, ``k`` and ``n - k`` (a proportion's two
arms) or ``n_pos`` and ``n_neg`` (an AUROC's two classes). A Number whose ``n`` is unknown
cannot be shown to clear the floor and is suppressed. A Number inside a suppressed row is
suppressed with the row.

The thresholds come from ``criteria.yaml``'s ``egress.suppression`` block (D1 section 2:
``egress: {telemetry: true, suppression: {min_n: 10, min_events: 5, min_nonevents: 5}}
# may only be made stricter``). A value below the default is refused as **H08** - the
declaration gate, exit 3, nothing written - rather than as a warning that lets the run
proceed on the default: a warning would be a silent fallback to a rule the customer did
not declare, and a looser value changes what leaves the machine. ``schema/
criteria_schema.json`` already carries ``minimum`` 10 / 5 / 5 on the three keys, so a
looser ``criteria.yaml`` halts at ``io.declare.validate_dict`` before this module is
reached; :func:`thresholds_from_declarations` refuses the same values for a caller that
hands it a dict directly, and names the field, the declared value and the default.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from proofpack.errors import HaltError

#: D1 section 6 defaults; ``schema/egress_schema.json`` ``x-proofpack.suppression_defaults``
#: carries the same three figures and ``tests/test_egress.py`` holds them equal.
DEFAULT_MIN_N = 10
DEFAULT_MIN_EVENTS = 5
DEFAULT_MIN_NONEVENTS = 5


@dataclass(frozen=True)
class Thresholds:
    min_n: int = DEFAULT_MIN_N
    min_events: int = DEFAULT_MIN_EVENTS
    min_nonevents: int = DEFAULT_MIN_NONEVENTS

    def as_dict(self) -> dict[str, int]:
        return {
            "min_n": self.min_n,
            "min_events": self.min_events,
            "min_nonevents": self.min_nonevents,
        }


DEFAULT_THRESHOLDS = Thresholds()

_FIELDS = (
    ("min_n", DEFAULT_MIN_N),
    ("min_events", DEFAULT_MIN_EVENTS),
    ("min_nonevents", DEFAULT_MIN_NONEVENTS),
)


def thresholds_from_declarations(egress: Mapping[str, Any] | None) -> Thresholds:
    """The thresholds a run applies: the declared ``egress.suppression`` values, each at
    least its default; a missing block or key is the default; a looser or non-integer value
    is H08 with ``{"field", "declared", "default"}`` in the detail."""
    block = (egress or {}).get("suppression") or {}
    if not isinstance(block, Mapping):
        raise HaltError(
            "H08",
            "egress.suppression must be a mapping of min_n, min_events and min_nonevents",
            {"field": "egress.suppression"},
        )
    values: dict[str, int] = {}
    for name, default in _FIELDS:
        declared = block.get(name, default)
        if isinstance(declared, bool) or not isinstance(declared, int):
            raise HaltError(
                "H08",
                f"egress.suppression.{name} must be an integer of at least {default}",
                {"field": f"egress.suppression.{name}", "default": default},
            )
        if declared < default:
            raise HaltError(
                "H08",
                f"egress.suppression.{name} may only be made stricter than the default "
                f"{default} (declared {declared}); D1 section 6: customers may only tighten "
                "the suppression thresholds",
                {"field": f"egress.suppression.{name}", "declared": declared, "default": default},
            )
        values[name] = declared
    return Thresholds(**values)


def is_suppressed(
    n: int | None, events: int | None, nonevents: int | None, thresholds: Thresholds
) -> bool:
    """The rule on one cell. ``None`` for a count means it is unknown; an unknown ``n``
    suppresses (the floor cannot be shown to be cleared); an unknown ``events`` or
    ``nonevents`` is not tested (a cell that carries no event count, such as a bin of a
    regression task, is judged on ``n`` alone)."""
    if n is None or n < thresholds.min_n:
        return True
    if events is not None and events < thresholds.min_events:
        return True
    if nonevents is not None and nonevents < thresholds.min_nonevents:
        return True
    return False


NUMBER_KEYS = ("est", "ci_lo", "ci_hi", "method", "n", "k", "suppressed")


def suppressed_number() -> dict[str, Any]:
    """The null shape: every value field ``None``, ``suppressed: true``."""
    return {
        "est": None,
        "ci_lo": None,
        "ci_hi": None,
        "method": None,
        "n": None,
        "k": None,
        "suppressed": True,
    }


def number_counts(number: Mapping[str, Any]) -> tuple[int | None, int | None, int | None]:
    """``(n, events, nonevents)`` of an engine Number: ``n`` / ``k`` / ``n - k`` for a
    proportion, ``n_pos + n_neg`` / ``n_pos`` / ``n_neg`` for a two-class statistic, ``n``
    alone otherwise."""
    n = number.get("n")
    k = number.get("k")
    n_pos = number.get("n_pos")
    n_neg = number.get("n_neg")
    if n is None and isinstance(n_pos, int) and isinstance(n_neg, int):
        return n_pos + n_neg, n_pos, n_neg
    if isinstance(n, int) and isinstance(k, int):
        return n, k, n - k
    if isinstance(n, int) and isinstance(n_pos, int) and isinstance(n_neg, int):
        return n, n_pos, n_neg
    return (n if isinstance(n, int) else None), None, None


def project_number(
    number: Mapping[str, Any] | None,
    thresholds: Thresholds,
    *,
    row_suppressed: bool = False,
) -> dict[str, Any]:
    """The egress projection of one engine Number (``stats.number.Number.as_dict``):
    ``est``, ``ci_lo``, ``ci_hi``, ``method``, ``n``, ``k`` and ``suppressed`` only - never
    ``flags``, ``ci_level``, ``not_estimable_reason``, ``n_pos``, ``n_neg`` or
    ``n_cases`` - and the null shape when the row is suppressed, when the Number's own
    counts fall below the thresholds, when its ``n`` is unknown, or when the engine itself
    marked it ``suppressed``."""
    if number is None or row_suppressed or number.get("suppressed") is True:
        return suppressed_number()
    n, events, nonevents = number_counts(number)
    if is_suppressed(n, events, nonevents, thresholds):
        return suppressed_number()
    return {
        "est": number.get("est"),
        "ci_lo": number.get("ci_lo"),
        "ci_hi": number.get("ci_hi"),
        "method": number.get("method"),
        "n": n,
        "k": number.get("k") if isinstance(number.get("k"), int) else None,
        "suppressed": False,
    }
