"""The upload check of the r-captures job (build day 12, lane E; DEC-77).

    python scripts/r_upload_guard.py upload

DEC-77 (Josh, 5 October 2026): pROC's aSAH rows never leave the runner; the artefact
``r-captures`` holds ``proc_asah.json``, ``rms_val_prob_f4.json`` and
``f13_engine_comparison.json`` only. Before the upload step this script inspects the
directory it is given, recursively, and exits 1 when:

* a path's name matches ``*asah*vectors*`` or ends ``.csv`` (case ignored);
* the file names are not exactly those three, or an entry is not a regular file;
* a file holds the vectors' header line ``row,outcome,y,s100b,ndka``, or, when
  ``PROOFPACK_ASAH_VECTORS`` names a readable file, any of that file's data lines (the
  lines that are not blank and do not start with ``#``) as a substring.

Exit 0 otherwise; 2 when the directory does not exist. It prints file names and counts,
never a line of the vectors. Standard library only. Tests:
``tests/test_e12_repair3.py::test_dec77_upload_guard_*``.
"""

from __future__ import annotations

import fnmatch
import os
import sys
from pathlib import Path

ALLOWED = ("f13_engine_comparison.json", "proc_asah.json", "rms_val_prob_f4.json")
HEADER = "row,outcome,y,s100b,ndka"
ENV = "PROOFPACK_ASAH_VECTORS"


def _vector_lines() -> list[str]:
    path = os.environ.get(ENV)
    if not path:
        return []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, ValueError):
        return []
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln and not ln.startswith("#") and ln != HEADER]


def check(directory: Path) -> list[str]:
    """Every problem found in ``directory`` (empty when it passes)."""
    problems: list[str] = []
    entries = sorted(directory.rglob("*"))
    for p in entries:
        name = p.name.lower()
        if fnmatch.fnmatch(name, "*asah*vectors*") or name.endswith(".csv"):
            problems.append(f"{p.relative_to(directory)}: a vectors or .csv name")
        if not p.is_file():
            problems.append(f"{p.relative_to(directory)}: not a regular file")
    names = sorted(str(p.relative_to(directory)).replace("\\", "/") for p in entries)
    if names != sorted(ALLOWED):
        problems.append(f"the files are {names}, not exactly {sorted(ALLOWED)}")
    needles = [HEADER, *_vector_lines()]
    for p in entries:
        if not p.is_file():
            continue
        text = p.read_bytes().decode("utf-8", errors="replace")
        hits = sum(1 for n in needles if n in text)
        if hits:
            problems.append(f"{p.relative_to(directory)}: holds {hits} line(s) of the vectors")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: r_upload_guard.py DIRECTORY", file=sys.stderr)
        return 2
    directory = Path(args[0])
    if not directory.is_dir():
        print(f"r-upload-guard: {directory} is not a directory", file=sys.stderr)
        return 2
    problems = check(directory)
    for line in problems:
        print(f"r-upload-guard: {line}")
    print(f"r-upload-guard: {len(problems)} problem(s) in {directory}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
