"""``io.ledger`` - how many times a test set has been used with acceptance criteria (E7).

D1 section 3.1 ``io.ledger``: "local SQLite/JSON: SHA-256 of ``y_true`` + ``score`` columns
x count of runs with ``criteria`` present". v2 section 3 T2 / D4 section 11 item 6 render it:
"this test set (SHA-256 <hash[:12]>) has been used in N ... runs recorded in the local
ledger; the manufacturer's declared limit is L".

Store: **one JSON file per user**, ``ledger.json`` in :func:`proofpack.home` (the same
directory the licence file is installed to - ``%LOCALAPPDATA%\\proofpack`` on Windows,
``~/.proofpack`` elsewhere, ``PROOFPACK_HOME`` overriding both). Not SQLite: the record is
a flat map of hash -> count, read and rewritten whole, and a JSON file can be opened by the
customer's RA lead with no tool. Not beside the pack: the count is a property of the test
set across every pack built from it, and a file inside ``--out`` would travel with the pack
a customer hands over (DEC-26's rule for ``mapping.json`` applies here for the same reason)
and would reset with every new ``--out``.

Key: the SHA-256 of these bytes, in this order, over the **analysed rows** (the analysis
mask of ``io.schema.analysis_mask``, in row order): the UTF-8 bytes of the ``y_true``
strings joined by ``\\n``; the byte ``0x00``; then either the little-endian float64 bytes of
the ``score`` column (``numpy.asarray(score, '<f8').tobytes()``) or, for a ``y_pred``-only
table, the bytes ``y_pred\\n`` followed by the ``y_pred`` strings joined by ``\\n``. A test
set with the same labels and scores in the same row order has the same key on every
platform; a re-ordered file does not (row order is part of the data as handed over).

Count: incremented once per ``run`` whose declarations carry a ``criteria`` block (a run
without criteria is an estimate-only run and is not an acceptance decision); read back
after the increment, so ``ledger_count`` in the manifest **includes the run that wrote
it**. Warning: ``W14`` with ``{count, limit}`` when ``count > ledger.warn_after_acceptance_
runs``; no ``ledger`` block in ``criteria.yaml`` -> no limit -> no warning ever (D1: "no
default"). A ledger file that cannot be read or written gives ``W15`` and
``ledger_count: null`` rather than a halt or a traceback: the pack is still the pack, and
the manifest says the count is unknown.

``--offline`` changes nothing here: the file is local.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from proofpack.errors import Finding
from proofpack.home import home_dir

LEDGER_FILE = "ledger.json"
LEDGER_SCHEMA = "proofpack-ledger/1"


def test_set_key(
    y_true: list[Any] | np.ndarray,
    score: np.ndarray | None,
    y_pred: list[Any] | np.ndarray | None = None,
) -> str:
    """The SHA-256 key of one analysed test set (see the module docstring for the bytes)."""
    h = hashlib.sha256()
    labels = [str(v) for v in (y_true.tolist() if isinstance(y_true, np.ndarray) else y_true)]
    h.update("\n".join(labels).encode("utf-8"))
    h.update(b"\x00")
    if score is not None:
        h.update(np.asarray(score, dtype="<f8").tobytes())
    else:
        preds = [str(v) for v in (y_pred.tolist() if isinstance(y_pred, np.ndarray) else y_pred)]
        h.update(b"y_pred\n" + "\n".join(preds).encode("utf-8"))
    return h.hexdigest()


@dataclass(frozen=True)
class LedgerResult:
    """What one run learnt from the ledger; JSON-ready via :meth:`as_dict`."""

    key: str
    count: int | None
    limit: int | None
    path: str | None
    warning: Finding | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "test_set_sha256": self.key,
            "acceptance_runs": self.count,
            "warn_limit": self.limit,
            "counted": self.count is not None,
        }


def ledger_path(home: Path | None = None) -> Path:
    return (home if home is not None else home_dir()) / LEDGER_FILE


def _read(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("counts"), dict):
        raise ValueError("ledger file is not a proofpack ledger")
    counts = data["counts"]
    for k, v in counts.items():
        if not isinstance(k, str) or not isinstance(v, int) or v < 0:
            raise ValueError("ledger file holds a non-count entry")
    return dict(counts)


def record_run(
    key: str,
    *,
    has_criteria: bool,
    limit: int | None,
    home: Path | None = None,
) -> LedgerResult:
    """Count this run on ``key`` when it carries criteria; compare with ``limit``."""
    path = ledger_path(home)
    try:
        counts = _read(path)
        if has_criteria:
            counts[key] = counts.get(key, 0) + 1
            path.parent.mkdir(parents=True, exist_ok=True)
            body = {"schema": LEDGER_SCHEMA, "counts": counts}
            path.write_text(
                json.dumps(body, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
            )
        count: int | None = counts.get(key, 0)
    except (OSError, ValueError) as exc:
        return LedgerResult(
            key,
            None,
            limit,
            None,
            Finding(
                "W15",
                "the local ledger could not be read or written; acceptance runs on this "
                "test set were not counted",
                {"error": type(exc).__name__},
            ),
        )
    warning = None
    if limit is not None and count is not None and count > limit:
        warning = Finding(
            "W14",
            "the declared limit on acceptance runs against this test set is exceeded",
            {"count": count, "limit": int(limit)},
        )
    return LedgerResult(key, count, limit, str(path), warning)
