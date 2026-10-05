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

Exit 0 otherwise; 2 when the directory does not exist. What it prints (E12 repair 4,
lens 4 FA-B3; repair 5, lens 5 FA-B3): the directory argument it was given (in the last
line, and in the line it prints when that is not a directory), the three names above, those
of the three it did not find, the error type of a file it could not read, and counts.
A problem with an entry whose relative path is not one
of the three is printed with the words "an entry not among the three names" in place of the
path. At ``614edd2`` the guard printed every entry's path, so an entry named with a data line
of the vectors put that line on stdout (lens 4, measured). The test
``tests/test_e12_repair4.py::test_fa_b3_the_upload_guard_prints_no_entry_name_outside_the_three``
plants an entry named with the synthetic vectors' fifth data line (an empty file, a
directory holding ``a.json``, a file in a subdirectory ``sub``) and finds none of the
vectors' 81 lines in stdout or stderr. Standard library only. Other tests:
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
    """Every problem found in ``directory`` (empty when it passes). A problem names an entry
    only when its relative path is one of :data:`ALLOWED`; any other entry is counted."""
    problems: list[str] = []
    entries = sorted(directory.rglob("*"))
    rel = {p: str(p.relative_to(directory)).replace("\\", "/") for p in entries}

    def label(p: Path) -> str:
        return rel[p] if rel[p] in ALLOWED else "an entry not among the three names"

    for p in entries:
        name = p.name.lower()
        if fnmatch.fnmatch(name, "*asah*vectors*") or name.endswith(".csv"):
            problems.append(f"{label(p)}: a vectors or .csv name")
        if not p.is_file():
            problems.append(f"{label(p)}: not a regular file")
    others = [p for p in entries if rel[p] not in ALLOWED]
    missing = sorted(set(ALLOWED) - set(rel.values()))
    if others or missing:
        problems.append(
            f"{len(others)} entr{'y' if len(others) == 1 else 'ies'} not among the three names "
            f"{sorted(ALLOWED)}; missing: {missing}"
        )
    needles = [HEADER, *_vector_lines()]
    for p in entries:
        if not p.is_file():
            continue
        try:
            text = p.read_bytes().decode("utf-8", errors="replace")
        except OSError as exc:
            problems.append(f"{label(p)}: could not be read ({type(exc).__name__})")
            continue
        hits = sum(1 for n in needles if n in text)
        if hits:
            problems.append(f"{label(p)}: holds {hits} line(s) of the vectors")
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
