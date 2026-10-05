"""The drift check of the r-captures workflow (build day 12, lane E).

    python scripts/r_capture_drift.py --committed fixtures/r --fresh "$PROOFPACK_R_OUT"

Compares the files ``fixtures/r/capture.R`` has just written (``--fresh``) with the ones
committed in the repository (``--committed``):

* ``proc_asah.json`` and ``rms_val_prob_f4.json``: every key except ``meta`` (the R
  session, the run date, the GitHub run), recursively. Two numbers differ when
  ``abs(a - b) > 1e-12`` (absolute; ``--tol`` changes it); any other value (a string, a
  boolean, null, a key present on one side only, a list of another length) differs when
  it is not equal. ``proc_asah.json``'s ``input`` carries the sha256 and row count of the
  aSAH vectors, so a change in the vectors shows there; the vectors themselves are never
  committed (DEC-77) and are not compared here. ``f13_engine_comparison.json`` is the
  engine's output, not R's, and is not compared either.

A file that is not committed is not compared (the first run has nothing to compare
with); a committed file that the fresh run did not write is a difference. Exit 0 when
nothing differs, 1 when something does, 2 on a usage error. Standard library only, so
that it runs on the runner's own ``python3``. Tests: ``tests/test_day12_r_captures.py``.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

JSON_FILES = ("proc_asah.json", "rms_val_prob_f4.json")
TOL = 1e-12
#: The top-level key that is provenance, not a captured value.
META = "meta"


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def diff_values(a: Any, b: Any, path: str, tol: float) -> list[str]:
    """Every difference between ``a`` (committed) and ``b`` (fresh) below ``path``."""
    if _is_number(a) and _is_number(b):
        fa, fb = float(a), float(b)
        if not (math.isfinite(fa) and math.isfinite(fb)):
            return [] if fa == fb else [f"{path}: committed {a!r} fresh {b!r}"]
        d = abs(fa - fb)
        return [] if d <= tol else [f"{path}: committed {a!r} fresh {b!r} abs difference {d:.3e}"]
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[str] = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                side = "fresh only" if k not in a else "committed only"
                out.append(f"{path}.{k}: {side}")
                continue
            out += diff_values(a[k], b[k], f"{path}.{k}", tol)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: committed {len(a)} items, fresh {len(b)}"]
        out = []
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            out += diff_values(x, y, f"{path}[{i}]", tol)
        return out
    return [] if a == b else [f"{path}: committed {a!r} fresh {b!r}"]


def compare(committed: Path, fresh: Path, tol: float = TOL) -> tuple[list[str], list[str]]:
    """``(lines, differences)``: a line per file, and every difference found."""
    lines: list[str] = []
    diffs: list[str] = []
    for name in JSON_FILES:
        c, f = committed / name, fresh / name
        if not c.exists():
            lines.append(f"{name}: not committed - not compared")
            continue
        if not f.exists():
            diffs.append(f"{name}: committed, and the fresh run did not write it")
            lines.append(f"{name}: MISSING from the fresh run")
            continue
        a = json.loads(c.read_text(encoding="utf-8"))
        b = json.loads(f.read_text(encoding="utf-8"))
        a = {k: v for k, v in a.items() if k != META} if isinstance(a, dict) else a
        b = {k: v for k, v in b.items() if k != META} if isinstance(b, dict) else b
        found = diff_values(a, b, name, tol)
        diffs += found
        lines.append(f"{name}: {'identical within ' + str(tol) if not found else 'DIFFERS'}")
    return lines, diffs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--committed", required=True, type=Path)
    ap.add_argument("--fresh", required=True, type=Path)
    ap.add_argument("--tol", type=float, default=TOL)
    args = ap.parse_args(argv)
    if not args.fresh.is_dir():
        print(f"r-capture drift: --fresh {args.fresh} is not a directory", file=sys.stderr)
        return 2
    lines, diffs = compare(args.committed, args.fresh, args.tol)
    for line in lines:
        print(f"r-capture drift: {line}")
    for d in diffs:
        print(f"r-capture drift: {d}")
    if all(line.endswith("not compared") for line in lines):
        print("r-capture drift: no capture is committed; nothing to compare")
    print(f"r-capture drift: {len(diffs)} difference(s) above {args.tol}")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
