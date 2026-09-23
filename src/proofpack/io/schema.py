"""``io.schema`` - load and validate the canonical test table (D1 section 1).

Responsibilities on day 1: read CSV or JSON, apply the missing-token convention,
coerce declared types, coarsen dates to the declared period granularity at
ingest (raw dates never survive), count the flow (included / excluded-missing /
indeterminate) and expose typed numpy columns for the HALT gates.

Everything here is aggregates-safe: no method returns original headers or row
values in an error message.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from proofpack.errors import HaltError
from proofpack.resources import load_json_schema

_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_IDENT = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


def _schema() -> dict:
    return load_json_schema("schema_v1.json")


def canonical_columns() -> list[str]:
    return list(_schema()["x-proofpack"]["canonical_columns"])


def attribute_columns() -> list[str]:
    return list(_schema()["x-proofpack"]["attribute_columns"])


def missing_tokens() -> frozenset[str]:
    return frozenset(_schema()["x-proofpack"]["missing_tokens"])


def header_set_sha256(headers: list[str]) -> str:
    """Order-independent hash of the header set (mapping.json identity, D1 section 5.5)."""
    joined = "\n".join(sorted(h.strip() for h in headers))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


@dataclass
class RawTable:
    """Columns as strings (None = missing token). Nothing typed yet."""

    headers: list[str]
    columns: dict[str, list[str | None]]
    n_rows: int
    source: str
    header_set_sha256: str

    def has(self, name: str) -> bool:
        return name in self.columns


def _norm_cell(value: Any, missing: frozenset[str]) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, bool):
        s = "1" if value else "0"
    elif isinstance(value, (int, float)):
        s = repr(value) if isinstance(value, float) else str(value)
    else:
        s = str(value)
    s = s.strip()
    if s in missing:
        return None
    return s


def load_table(path: str | Path) -> RawTable:
    """Read a CSV (UTF-8, header row) or JSON table into a :class:`RawTable`.

    JSON accepted shapes: a list of row objects, or ``{"columns": {name: [values]}}``.
    """
    p = Path(path)
    missing = missing_tokens()
    try:
        if p.suffix.lower() == ".json":
            with p.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            headers, columns = _from_json(data, missing)
        else:
            with p.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.reader(fh)
                try:
                    headers = [h.strip() for h in next(reader)]
                except StopIteration:
                    raise HaltError("S04", "table is empty (no header row)") from None
                columns: dict[str, list[str | None]] = {h: [] for h in headers}
                if len(set(headers)) != len(headers):
                    raise HaltError("S04", "duplicate header names in table")
                for row in reader:
                    if not row or all(c.strip() == "" for c in row):
                        continue
                    if len(row) != len(headers):
                        raise HaltError(
                            "S04",
                            "row width differs from header width",
                            {"expected": len(headers), "observed": len(row)},
                        )
                    for h, cell in zip(headers, row, strict=True):
                        columns[h].append(_norm_cell(cell, missing))
    except HaltError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, csv.Error) as exc:
        raise HaltError("S04", f"table could not be read: {type(exc).__name__}") from exc
    n_rows = len(next(iter(columns.values()))) if columns else 0
    return RawTable(
        headers=headers,
        columns=columns,
        n_rows=n_rows,
        source=str(p.name),
        header_set_sha256=header_set_sha256(headers),
    )


def _from_json(data: Any, missing: frozenset[str]) -> tuple[list[str], dict]:
    if isinstance(data, dict) and "columns" in data and isinstance(data["columns"], dict):
        cols = data["columns"]
        headers = [str(k).strip() for k in cols]
        lengths = {len(v) for v in cols.values()}
        if len(lengths) > 1:
            raise HaltError("S04", "JSON columns have differing lengths")
        columns = {
            h: [_norm_cell(v, missing) for v in cols[k]] for h, k in zip(headers, cols, strict=True)
        }
        return headers, columns
    if isinstance(data, list):
        if not data:
            raise HaltError("S04", "table is empty (no rows)")
        if not all(isinstance(r, dict) for r in data):
            raise HaltError("S04", "JSON table rows must be objects")
        headers: list[str] = []
        for r in data:
            for k in r:
                k = str(k).strip()
                if k not in headers:
                    headers.append(k)
        columns = {h: [_norm_cell(r.get(h), missing) for r in data] for h in headers}
        return headers, columns
    raise HaltError("S04", "JSON table must be a list of objects or {columns: {...}}")


def table_from_columns(columns: dict[str, list[Any]], source: str = "<memory>") -> RawTable:
    """Build a RawTable from in-memory columns (tests and the Pyodide demo)."""
    missing = missing_tokens()
    headers = [str(h).strip() for h in columns]
    lengths = {len(v) for v in columns.values()}
    if len(lengths) > 1:
        raise HaltError("S04", "columns have differing lengths")
    cols = {
        h: [_norm_cell(v, missing) for v in columns[k]]
        for h, k in zip(headers, columns, strict=True)
    }
    n = len(next(iter(cols.values()))) if cols else 0
    return RawTable(headers, cols, n, source, header_set_sha256(headers))


# --------------------------------------------------------------------------- typed table


@dataclass
class FlowCounts:
    """R1 flowchart counts. Aggregates only."""

    n_rows: int
    included: int
    excluded_missing_y_true: int
    excluded_missing_score: int
    indeterminate: int

    def as_dict(self) -> dict[str, int]:
        return dict(self.__dict__)


@dataclass
class Table:
    """Typed canonical table. Column arrays are aligned to the original row order.

    ``y_true``/``y_pred`` are object arrays of ``str`` (None when missing);
    ``score``/``age`` are float64 with NaN for missing; ``indeterminate`` is an
    int8 array (0/1, -1 missing); attributes are object arrays of ``str`` with
    ``"Unknown/missing"`` substituted for missing (never dropped, D1 section 1).
    """

    n_rows: int
    headers: list[str]
    header_set_sha256: str
    y_true: np.ndarray
    score: np.ndarray | None
    y_pred: np.ndarray | None
    indeterminate: np.ndarray | None
    row_id: np.ndarray | None
    case_id: np.ndarray | None
    age: np.ndarray | None
    attributes: dict[str, np.ndarray]
    period: np.ndarray | None
    model_version: np.ndarray | None
    dataset: np.ndarray | None
    extras_numeric: dict[str, np.ndarray] = field(default_factory=dict)
    rater_columns: list[str] = field(default_factory=list)
    unused_columns: list[str] = field(default_factory=list)
    date_like_columns: list[str] = field(default_factory=list)
    flow: FlowCounts | None = None

    @property
    def has_score(self) -> bool:
        return self.score is not None

    def levels(self, attribute: str) -> list[str]:
        if attribute == "age" and self.age is not None:
            return []
        if attribute in self.attributes:
            vals = self.attributes[attribute]
            return sorted({str(v) for v in vals.tolist()})
        return []


UNKNOWN_LEVEL = "Unknown/missing"

#: Header tokens that make a column "date-like" for gate H11 (header-only stub; the
#: value-level date sniff belongs to the full mapper on the mapping day).
DATE_LIKE_HEADER = re.compile(r"(^|_)(date|dt|time|timestamp|datetime|dob)($|_)", re.IGNORECASE)


def date_like_headers(headers: list[str]) -> list[str]:
    """Canonical/raw header names that look like a date column."""
    out = []
    for h in headers:
        if h == "event_date" or DATE_LIKE_HEADER.search(h):
            out.append(h)
    return out


def _to_float(col: list[str | None], name: str) -> np.ndarray:
    out = np.full(len(col), np.nan, dtype=np.float64)
    bad = 0
    for i, v in enumerate(col):
        if v is None:
            continue
        try:
            out[i] = float(v)
        except ValueError:
            bad += 1
    if bad:
        raise HaltError(
            "S02",
            f"column role {name!r} has {bad} value(s) that are not numeric",
            {"role": name, "count": bad},
        )
    if name == "score" and np.isinf(out[~np.isnan(out)]).any():
        raise HaltError("S02", "score contains infinite values", {"role": name})
    return out


def _to_int01(col: list[str | None], name: str) -> np.ndarray:
    out = np.full(len(col), -1, dtype=np.int8)
    bad = 0
    for i, v in enumerate(col):
        if v is None:
            continue
        if v in ("0", "1"):
            out[i] = int(v)
        else:
            try:
                f = float(v)
            except ValueError:
                bad += 1
                continue
            if f in (0.0, 1.0):
                out[i] = int(f)
            else:
                bad += 1
    if bad:
        raise HaltError("S02", f"column role {name!r} must be 0/1", {"role": name, "count": bad})
    return out


def _to_obj(col: list[str | None]) -> np.ndarray:
    return np.array(col, dtype=object)


def _to_attr(col: list[str | None]) -> np.ndarray:
    return np.array([UNKNOWN_LEVEL if v is None else v for v in col], dtype=object)


def coarsen_date(value: str | None, granularity: str) -> str | None:
    """Coarsen an ISO date string to ``YYYY``, ``YYYY-MM`` or ``YYYY-Qn``."""
    if value is None:
        return None
    m = _ISO_DATE.match(value)
    if not m:
        raise HaltError("S02", "period column contains a value that is not an ISO date")
    y, mo = int(m.group(1)), int(m.group(2))
    if not 1 <= mo <= 12:
        raise HaltError("S02", "period column contains an invalid month")
    if granularity == "year":
        return f"{y:04d}"
    if granularity == "month":
        return f"{y:04d}-{mo:02d}"
    if granularity == "quarter":
        return f"{y:04d}-Q{(mo - 1) // 3 + 1}"
    raise ValueError(f"unknown granularity {granularity!r}")


def validate(raw: RawTable, period: dict | None = None) -> Table:
    """Type and validate a :class:`RawTable` against schema v1.

    ``period`` is the declared ``period`` block (``{column, granularity}``) or None.
    Structural failures raise :class:`HaltError` with an S-code; the H-gates that
    need declarations are run later by :mod:`proofpack.gates`.
    """
    cols = raw.columns
    if "y_true" not in cols:
        raise HaltError("S01", "required column role 'y_true' is missing", {"role": "y_true"})
    if "score" not in cols and "y_pred" not in cols:
        raise HaltError("S01", "one of 'score' or 'y_pred' is required", {"role": "score"})

    y_true = _to_obj(cols["y_true"])
    score = _to_float(cols["score"], "score") if "score" in cols else None
    y_pred = _to_obj(cols["y_pred"]) if "y_pred" in cols else None
    indet = _to_int01(cols["indeterminate"], "indeterminate") if "indeterminate" in cols else None
    row_id = _to_obj(cols["row_id"]) if "row_id" in cols else None
    case_id = _to_obj(cols["case_id"]) if "case_id" in cols else None
    if case_id is not None:
        # E7, carried item 26: a blank id (None after the missing-token normalisation) is
        # S05, not a case of its own and not a case shared by every blank row
        blank = int(sum(1 for v in case_id.tolist() if v is None))
        if blank:
            raise HaltError(
                "S05",
                f"case_id is blank in {blank} row(s); fill every case id or drop the column",
                {"role": "case_id", "count": blank},
            )
    age = _to_float(cols["age"], "age") if "age" in cols else None

    attributes: dict[str, np.ndarray] = {}
    for a in attribute_columns():
        if a == "age":
            continue
        if a in cols:
            attributes[a] = _to_attr(cols[a])

    extras_numeric: dict[str, np.ndarray] = {}
    raters: list[str] = []
    unused: list[str] = []
    known = set(canonical_columns())
    for h in raw.headers:
        if h in known:
            continue
        if h.startswith("attr_") and _IDENT.match(h):
            col = cols[h]
            try:
                extras_numeric[h] = _to_float(col, h)
            except HaltError:
                attributes[h] = _to_attr(col)
        elif h.startswith("rater_"):
            raters.append(h)
        else:
            unused.append(h)

    # dates: coarsen at ingest; the raw column never reaches the Table
    period_arr = None
    if period is not None:
        pcol = period["column"]
        if pcol not in cols:
            raise HaltError("S03", "declared period column is not present in the table")
        if pcol == "period":
            period_arr = _to_obj(cols["period"])
        else:
            gran = period["granularity"]
            period_arr = np.array([coarsen_date(v, gran) for v in cols[pcol]], dtype=object)
    elif "period" in cols:
        period_arr = _to_obj(cols["period"])

    model_version = _to_obj(cols["model_version"]) if "model_version" in cols else None
    dataset = _to_obj(cols["dataset"]) if "dataset" in cols else None
    if dataset is not None:
        badset = {v for v in dataset.tolist() if v is not None and v not in ("dev", "test")}
        if badset:
            raise HaltError("S02", "dataset column must be dev/test", {"count": len(badset)})

    return Table(
        n_rows=raw.n_rows,
        headers=list(raw.headers),
        header_set_sha256=raw.header_set_sha256,
        y_true=y_true,
        score=score,
        y_pred=y_pred,
        indeterminate=indet,
        row_id=row_id,
        case_id=case_id,
        age=age,
        attributes=attributes,
        period=period_arr,
        model_version=model_version,
        dataset=dataset,
        extras_numeric=extras_numeric,
        rater_columns=raters,
        unused_columns=unused,
        date_like_columns=date_like_headers(raw.headers),
    )


def analysis_mask(table: Table, indeterminate_values: set[str]) -> tuple[np.ndarray, FlowCounts]:
    """Rows usable for analysis, and the flow counts.

    A row is excluded when ``y_true`` is missing, or the prediction input is missing:
    ``score`` while a score column exists, otherwise ``y_pred`` (repair 2 of build day 8,
    lens FA-B1 / RG-B1: at ``657ef11`` a blank ``y_pred`` on a table without a score
    column reached ``overall_block`` as a negative prediction - 60 blanks in 120 rows gave
    ``{tp 21, fn 21, fp 7, tn 71}`` where the 60 non-blank rows give ``{tp 21, fn 3, fp 7,
    tn 29}``; ``tests/test_e8_repair2.py`` feeds that table). A row whose ``y_true`` is
    present and whose prediction input is missing counts under ``excluded_missing_score``,
    the flow's one "missing prediction input" entry (D1 section 2: "excluded-missing"); a
    row missing both counts under ``excluded_missing_y_true`` (``excl_sc`` below reads
    ``~yt_missing``). Indeterminate rows - ``y_true`` or ``y_pred`` holding a
    declared indeterminate value (``schema_v1.json``: the 0/1 column is "an alternative to
    listing indeterminate values in y_true / y_pred"), or the 0/1 column - are counted
    separately and excluded from the default mask (both-way analysis is a later day).
    ``dev`` rows are never analysed.
    """
    n = table.n_rows
    yt_missing = np.array([v is None for v in table.y_true.tolist()], dtype=bool)
    if table.dataset is not None:
        dev = np.array([v == "dev" for v in table.dataset.tolist()], dtype=bool)
    else:
        dev = np.zeros(n, dtype=bool)
    if table.score is not None:
        sc_missing = np.isnan(table.score)
    elif table.y_pred is not None:
        sc_missing = np.array([v is None for v in table.y_pred.tolist()], dtype=bool)
    else:  # pragma: no cover - validate() requires a score or a y_pred column
        sc_missing = np.zeros(n, dtype=bool)
    indet = np.array(
        [v is not None and v in indeterminate_values for v in table.y_true.tolist()], dtype=bool
    )
    if table.y_pred is not None:
        indet |= np.array(
            [v is not None and v in indeterminate_values for v in table.y_pred.tolist()],
            dtype=bool,
        )
    if table.indeterminate is not None:
        indet |= table.indeterminate == 1
    base = ~dev
    excl_yt = base & yt_missing
    excl_sc = base & ~yt_missing & sc_missing
    indet_rows = base & ~yt_missing & ~sc_missing & indet
    included = base & ~yt_missing & ~sc_missing & ~indet
    flow = FlowCounts(
        n_rows=int(n),
        included=int(included.sum()),
        excluded_missing_y_true=int(excl_yt.sum()),
        excluded_missing_score=int(excl_sc.sum()),
        indeterminate=int(indet_rows.sum()),
    )
    table.flow = flow
    return included, flow
