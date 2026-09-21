"""The run manifest (D1 section 4.2 ``manifest``; D4 section 11 item 2) and canonical JSON.

Every field is a fact about the run, never a judgement: what was hashed, on what, with
which seed, by which engine, under which licence. F17 (D1 section 3.2): two runs of the
same inputs on the same platform give identical hashes. ``tests/test_manifest.py::
test_f17_two_runs_in_one_process_differ_only_in_run_id_started_duration_s_and_the_ledger_count``
runs the whole command twice in one process and diffs the bytes. It asserts that ``run_id``
and ``ledger_count`` differ, that no manifest key outside ``run_id``, ``started``,
``duration_s`` (:data:`VOLATILE_KEYS`) and ``ledger_count`` (:data:`HISTORY_KEYS`) differs,
that ``ledger.acceptance_runs`` in the body reads 1 then 2, that the three SHA-256 fields
are equal, and that the JSON is byte-identical once those keys are blanked. ``started``
(whole seconds) and ``duration_s`` may or may not differ between two runs; the test does
not assert either way (lens 2 of 21 September, FA-N2: an earlier form of this sentence
listed ``started`` as a key that differed, which the test never measured).

Canonical JSON (:func:`canonical_json`): ``sort_keys=True``, ``indent=1``, separators
``(",", ": ")``, ``ensure_ascii=False``, ``allow_nan=False`` - so a document holding a
non-finite float **raises** ``ValueError`` and nothing is written, rather than the
non-JSON token ``Infinity`` reaching a customer's file (carried item 25) - one trailing
``\\n``, UTF-8 without a byte-order mark.

``platform`` is ``sysconfig.get_platform()`` plus the CPython tag (``-cp312``);
``reference_platform`` is whether that string equals :data:`REFERENCE_PLATFORM`, the
``python:3.12-slim`` linux/amd64 image D1 section 9 names, on which alone hash identity is
claimed (T12). It is ``false`` on the build machine (``win-amd64-cp314``).
"""

from __future__ import annotations

import hashlib
import json
import sys
import sysconfig
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from proofpack import __version__

#: D1 section 9: ``python:3.12-slim`` linux/amd64 with the pinned lockfile.
REFERENCE_PLATFORM = "linux-x86_64-cp312"


def platform_tag() -> str:
    return f"{sysconfig.get_platform()}-cp{sys.version_info.major}{sys.version_info.minor}"


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scipy_version() -> str | None:
    try:
        import scipy  # noqa: PLC0415 - optional at runtime
    except ImportError:
        return None
    return str(scipy.__version__)


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_manifest(
    *,
    input_path: str | Path,
    criteria_path: str | Path,
    mapping_path: str | Path | None,
    seed: int | None,
    n_resamples: int | None,
    started: str,
    duration_s: float | None,
    licence_id: str | None,
    tier: str | None,
    ledger_count: int | None,
    watermark: str | None,
) -> dict[str, Any]:
    plat = platform_tag()
    return {
        "run_id": str(uuid.uuid4()),
        "engine_version": __version__,
        "platform": plat,
        "python": ".".join(str(x) for x in sys.version_info[:3]),
        "numpy": str(np.__version__),
        "scipy": scipy_version(),
        "input_sha256": sha256_file(input_path),
        "criteria_sha256": sha256_file(criteria_path),
        "mapping_sha256": None if mapping_path is None else sha256_file(mapping_path),
        "seed": seed,
        "B": n_resamples,
        "started": started,
        "duration_s": duration_s,
        "reference_platform": plat == REFERENCE_PLATFORM,
        "licence_id": licence_id,
        "tier": tier,
        "ledger_count": ledger_count,
        "watermark": watermark,
    }


def canonical_json(doc: dict[str, Any]) -> bytes:
    """The document's bytes: sorted keys, fixed separators, no NaN or Infinity, UTF-8."""
    text = json.dumps(
        doc, sort_keys=True, indent=1, separators=(",", ": "), ensure_ascii=False, allow_nan=False
    )
    return (text + "\n").encode("utf-8")


#: The manifest keys that differ between two runs of the same inputs (F17): the run's
#: own identity and timing.
VOLATILE_KEYS: frozenset[str] = frozenset({"run_id", "started", "duration_s"})
#: The manifest key that records history rather than this run: the local ledger counts
#: every run with criteria on this test set, so the second of two identical runs carries
#: a count one higher (``ledger.acceptance_runs`` in the document body moves with it).
#: F17's byte comparison blanks these beside the volatile keys; every statistic, hash,
#: criterion row and declaration is compared as written.
HISTORY_KEYS: frozenset[str] = frozenset({"ledger_count"})
