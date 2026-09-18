"""``io.profile`` - value-level column summaries for the mapper (D1 section 5 step 1).

One :class:`ColumnSummary` per column, computed from the first :data:`SAMPLE_ROWS`
rows after the header (a prefix sample; no seed is involved). It holds the inferred
type, ``n_unique``, the top <= :data:`TOP_VALUES` values with counts, min/max for
numeric and date columns, the missing percentage after the schema's missing-token
normalisation, and for <= 2-unique-value columns the split (candidate labels).

Suppression is applied before anything is displayed or written: a value is listed only
when its count in the sample is >= :data:`SUPPRESSION_K`; below that it is replaced by
the literal ``<suppressed>`` and counted in ``n_suppressed_values``. Free-text-looking
columns (more than :data:`FREE_TEXT_UNIQUE_SHARE` of the non-missing sample is unique
and the type is not numeric or date) list no values at all. Date min/max are coarsened
to ``YYYY-MM``; a date column lists no values (D1 section 1's rule on raw dates). The
summary is what ``mapping.json``'s ``value_summaries`` holds and what
the printed table shows.

Typing reuses :mod:`proofpack.io.schema`: the missing tokens are already applied by
``load_table`` / ``table_from_columns`` (a ``None`` cell is missing), ``float()`` is the
numeric rule ``_to_float`` uses, and ``_ISO_DATE`` is the date prefix ``coarsen_date``
accepts. Two slash-separated date shapes are accepted in addition (recorded in
:data:`DATE_PATTERNS`).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from proofpack.io.schema import _ISO_DATE, _norm_cell, missing_tokens

#: Rows inspected per column: the first 10,000 after the header (D1 section 5 step 1).
SAMPLE_ROWS = 10_000
#: Suppression floor for a listed value. D1 section 5 states no floor of its own, so the
#: egress ``n < 10`` cell rule of D1 section 6 is used [decision, day 6 A].
SUPPRESSION_K = 10
#: Top values listed per column (D1 section 5 step 1: "top <= 20").
TOP_VALUES = 20
#: A categorical/string column whose unique share of the non-missing sample exceeds
#: this is treated as free text and lists no values. Columns with <= 2 unique values are
#: exempt so the label split still shows [decision, day 6 A].
FREE_TEXT_UNIQUE_SHARE = 0.5
#: The literal that replaces a suppressed value.
SUPPRESSED = "<suppressed>"

_INT = re.compile(r"^[+-]?\d+$")
#: Date shapes the value sniff accepts: the schema's ISO prefix, then D/M/YYYY and
#: YYYY/MM/DD. A column is typed ``date`` only when every non-missing sampled value
#: matches one of them.
DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    _ISO_DATE,
    re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"),
    re.compile(r"^\d{4}/\d{2}/\d{2}$"),
)


@dataclass
class ColumnSummary:
    """Aggregates only. ``top`` and ``split`` hold ``[value_or_<suppressed>, count]`` pairs."""

    inferred_type: str  # int | float | date | categorical | string | empty
    n_sampled: int
    n_missing: int
    missing_pct: float
    n_unique: int
    top: list[list] = field(default_factory=list)
    n_suppressed_values: int = 0
    min: str | None = None
    max: str | None = None
    split: list[list] | None = None
    free_text: bool = False
    values_shown: bool = True
    # value signals the mapper's heuristics read (aggregates; not part of to_dict())
    signals: dict = field(default_factory=dict)

    @property
    def n_nonmissing(self) -> int:
        return self.n_sampled - self.n_missing

    def to_dict(self) -> dict:
        return {
            "inferred_type": self.inferred_type,
            "n_sampled": self.n_sampled,
            "n_missing": self.n_missing,
            "missing_pct": self.missing_pct,
            "n_unique": self.n_unique,
            "top": self.top,
            "n_suppressed_values": self.n_suppressed_values,
            "min": self.min,
            "max": self.max,
            "split": self.split,
            "free_text": self.free_text,
            "values_shown": self.values_shown,
        }

    def render(self) -> str:
        """One line for the printed mapping table."""
        parts = [
            self.inferred_type,
            f"{self.n_unique} unique",
            f"{self.missing_pct:.1f}% missing",
        ]
        if self.min is not None:
            parts.append(f"min {self.min} max {self.max}")
        if not self.values_shown:
            reason = "free text" if self.free_text else "dates"
            parts.append(f"values not shown ({reason})")
        elif self.top:
            shown = ", ".join(
                f"{v} ({c} distinct below k={SUPPRESSION_K})" if v == SUPPRESSED else f"{v} ({c})"
                for v, c in self.top
            )
            parts.append("values: " + shown)
        return "; ".join(parts)


def _infer_type(values: list[str]) -> str:
    if not values:
        return "empty"
    if all(_INT.match(v) for v in values):
        return "int"
    try:
        for v in values:
            float(v)
    except ValueError:
        pass
    else:
        return "float"
    if all(any(p.match(v) for p in DATE_PATTERNS) for v in values):
        return "date"
    return "categorical" if len(set(values)) <= TOP_VALUES else "string"


def _fmt_num(x: float) -> str:
    if math.isfinite(x) and x == int(x) and abs(x) < 1e15:
        return str(int(x))
    return f"{x:g}"


def _date_key(v: str) -> str:
    """``YYYY-MM`` for ordering and display; slash shapes are reduced by their digits."""
    m = _ISO_DATE.match(v)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"^(\d{4})/(\d{2})/\d{2}$", v)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"^\d{1,2}/(\d{1,2})/(\d{4})$", v)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    return v  # unreachable for a value that passed DATE_PATTERNS


def profile_column(column: list[str | None], *, sample_rows: int = SAMPLE_ROWS) -> ColumnSummary:
    """Summarise one raw column (``None`` = missing) from its first ``sample_rows`` values."""
    sample = column[:sample_rows]
    if any(not (v is None or isinstance(v, str)) for v in sample):
        # in-memory callers (tests, the demo) may pass typed cells; apply the schema's
        # missing-token normalisation exactly as table_from_columns does
        missing = missing_tokens()
        sample = [
            v if (v is None or isinstance(v, str)) else _norm_cell(v, missing) for v in sample
        ]
    n = len(sample)
    present = [v for v in sample if v is not None]
    n_missing = n - len(present)
    counts = Counter(present)
    kind = _infer_type(present)
    n_unique = len(counts)
    missing_pct = (100.0 * n_missing / n) if n else 0.0

    lo = hi = None
    signals: dict = {"n_rows": n, "n_nonmissing": len(present)}
    if kind in ("int", "float"):
        nums = [f for f in (float(v) for v in present) if not math.isnan(f)]
        lo, hi = (min(nums), max(nums)) if nums else (None, None)
        signals["numeric"] = True
        signals["min"], signals["max"] = lo, hi
        signals["unit_interval"] = lo is not None and lo >= 0.0 and hi <= 1.0
        signals["all_unique"] = len(present) >= 2 and n_unique == len(present) == n
    elif kind == "date":
        keys = sorted(_date_key(v) for v in present)
        lo, hi = keys[0], keys[-1]
        signals["date"] = True

    lowered = {v.casefold() for v in counts}
    signals["lowered_values"] = lowered
    signals["n_unique"] = n_unique

    free_text = (
        kind in ("categorical", "string")
        and n_unique > 2
        and len(present) > 0
        and n_unique > FREE_TEXT_UNIQUE_SHARE * len(present)
    )
    values_shown = not free_text and kind != "date"

    top: list[list] = []
    n_suppressed = 0
    if values_shown:
        # the top <= 20 by count, listed only at or above the floor; the suppressed count
        # is over every distinct value below the floor, not only the inspected twenty
        for value, count in counts.most_common(TOP_VALUES):
            if count >= SUPPRESSION_K:
                top.append([value, count])
        n_suppressed = sum(1 for c in counts.values() if c < SUPPRESSION_K)
        if n_suppressed:
            top.append([SUPPRESSED, n_suppressed])
    split = list(top) if (values_shown and 1 <= n_unique <= 2) else None

    return ColumnSummary(
        inferred_type=kind,
        n_sampled=n,
        n_missing=n_missing,
        missing_pct=round(missing_pct, 2),
        n_unique=n_unique,
        top=top,
        n_suppressed_values=n_suppressed,
        min=_fmt_num(lo) if isinstance(lo, float) else lo,
        max=_fmt_num(hi) if isinstance(hi, float) else hi,
        split=split,
        free_text=free_text,
        values_shown=values_shown,
        signals=signals,
    )


def profile_columns(columns: dict[str, list], *, sample_rows: int = SAMPLE_ROWS) -> dict:
    return {h: profile_column(v, sample_rows=sample_rows) for h, v in columns.items()}
