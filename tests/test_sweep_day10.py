"""Build day 9 (E10 item 8): the mutation sweep declares a day-10 list.

The list is run by ``python scripts/mutation_sweep.py --marker day10`` (DEC-12 ii); this
test reads the script's ``--list`` output and pins what the sweep assumes: at least ten
day-10 entries, every id unique across the listing, every file named exists, the list
covers the E9 modules the brief names, and every day-10 pattern matches its file exactly
the number of times it declares (a moved line fails here, not at sweep time).
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.day10

ROOT = Path(__file__).resolve().parents[1]


def _listing() -> list[list[str]]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mutation_sweep.py"), "--list"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    return [ln.split() for ln in proc.stdout.splitlines() if ln.strip()]


def test_the_sweep_declares_a_day10_list_of_ten_or_more_with_unique_ids():
    rows = _listing()
    ids = [r[0] for r in rows if len(r) >= 3]
    assert len(ids) == len(set(ids))
    day10 = [r for r in rows if len(r) >= 3 and r[1] == "day10"]
    assert len(day10) >= 10
    for r in day10:
        assert (ROOT / r[2]).exists(), r
    assert {
        "src/proofpack/stats/comparison.py",
        "src/proofpack/stats/proportions.py",
        "src/proofpack/stats/discrimination.py",
        "src/proofpack/criteria.py",
        "src/proofpack/run.py",
        "src/proofpack/render/t2.py",
        "src/proofpack/narrate/checker.py",
        "src/proofpack/narrate/claims.py",
    } <= {r[2] for r in day10}


def test_every_day10_pattern_matches_its_file_the_declared_number_of_times():
    spec = importlib.util.spec_from_file_location(
        "mutation_sweep", ROOT / "scripts" / "mutation_sweep.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # the dataclass decorator looks its module up
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    assert len(mod.MUTANTS_DAY10) >= 10
    for m in mod.MUTANTS_DAY10:
        text = (ROOT / m.file).read_text(encoding="utf-8")
        assert len(re.findall(m.pattern, text, flags=re.M)) == m.count, m.id
