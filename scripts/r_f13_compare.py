"""The F13 comparison inside the r-captures job (build day 12, lane E; DEC-77).

    PROOFPACK_ASAH_VECTORS=$RUNNER_TEMP/dec77/asah_vectors.csv \
        python scripts/r_f13_compare.py --captures fixtures/r \
        --out fixtures/r/f13_engine_comparison.json

DEC-77 (Josh, 5 October 2026): pROC's aSAH rows are never committed and never leave the
runner. ``fixtures/r/capture.R`` writes them to the file ``PROOFPACK_ASAH_VECTORS`` names;
this script reads them from there (``proofpack.fixtures.load_r_captures``), compares the
engine's F13 values with ``proc_asah.json`` in ``--captures`` (the F13 report row of
``proofpack fixtures``, absolute tolerance 1e-6), and writes
``proofpack.fixtures.f13_comparison_record`` to ``--out``: the engine commit
(``GITHUB_SHA``, else ``--engine-sha``), the run (``GITHUB_RUN_ID``,
``GITHUB_RUN_ATTEMPT``), the sha256 of ``proc_asah.json`` and of the vectors with their
row count, and per compared name the engine value, the R value, the absolute deviation,
the tolerance and whether it is within. It prints one line per compared name (the name and
those numbers) and a summary line; ``tests/test_e12_repair3.py`` feeds it the synthetic
80-row vectors and finds none of their data lines in its output.

Exit 0 when the row is ``matched``; 1 when it is not (the file is still written) or the
vectors or ``proc_asah.json`` cannot be read; 2 when ``PROOFPACK_ASAH_VECTORS`` is not set
or no engine commit is given. Tests: ``tests/test_e12_repair3.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from proofpack import fixtures as fx


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--captures", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--engine-sha", default=None)
    args = ap.parse_args(argv)
    if fx.R_VECTORS_ENV not in os.environ:
        print(f"r-f13-compare: {fx.R_VECTORS_ENV} is not set; refusing", file=sys.stderr)
        return 2
    engine_sha = os.environ.get("GITHUB_SHA") or args.engine_sha
    if not engine_sha:
        print("r-f13-compare: no engine commit (GITHUB_SHA or --engine-sha)", file=sys.stderr)
        return 2
    caps = fx.load_r_captures(args.captures)
    bad = dict(caps.unreadable)
    for rel in (fx.R_CAPTURE_FILES[0], fx.R_VECTORS_FILE):
        if rel in bad:
            print(f"r-f13-compare: {rel} could not be read ({bad[rel]})", file=sys.stderr)
            return 1
    if caps.proc is None or caps.vectors is None:
        print(f"r-f13-compare: {fx.R_CAPTURE_FILES[0]} is absent", file=sys.stderr)
        return 1
    record = fx.f13_comparison_record(
        caps,
        engine_sha=engine_sha,
        run_id=os.environ.get("GITHUB_RUN_ID"),
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    for name, v in record["values"].items():
        print(
            f"r-f13-compare: {name}: engine {v['engine']!r} R {v['r']!r} abs deviation "
            f"{v['abs_deviation']!r} tolerance {v['tolerance']!r} within {v['within']}"
        )
    print(
        f"r-f13-compare: row F13 {record['status']}, max abs deviation "
        f"{record['max_abs_deviation']!r}, {len(record['values'])} values, engine "
        f"{engine_sha}; wrote {args.out}"
    )
    return 0 if record["status"] == "matched" else 1


if __name__ == "__main__":
    sys.exit(main())
