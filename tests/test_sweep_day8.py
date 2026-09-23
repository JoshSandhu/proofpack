"""Build day 8 (E8 item 10): the mutation sweep declares a day-8 list.

The list itself is run by ``python scripts/mutation_sweep.py --marker day8`` (DEC-12 ii);
this test reads the script's ``--list`` output and pins what the sweep would otherwise
assume: the day-8 entries exist, there are at least twelve of them, every id is unique
across the whole listing, and every day-8 file named exists in the tree (a mutant naming a
file that does not exist would be reported as a match failure at sweep time, not here).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.day8

ROOT = Path(__file__).resolve().parents[1]


def _listing() -> list[str]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mutation_sweep.py"), "--list"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.splitlines()


def test_the_mutation_sweep_declares_a_day8_list_with_no_duplicate_ids():
    lines = _listing()
    rows = [ln.split() for ln in lines if ln.strip()]
    ids = [r[0] for r in rows if len(r) >= 3 and r[1].startswith("day")]
    assert len(ids) == len(set(ids)), "duplicate mutant ids in the listing"
    day8 = [r for r in rows if len(r) >= 3 and r[1] == "day8"]
    assert len(day8) >= 12
    for r in day8:
        assert (ROOT / r[2]).exists(), f"day8 mutant {r[0]} names a missing file {r[2]}"


def test_the_day8_list_covers_the_four_e8_modules_and_the_template():
    day8 = [ln.split() for ln in _listing() if " day8 " in ln]
    files = {r[2] for r in day8}
    assert {
        "src/proofpack/render/format.py",
        "src/proofpack/narrate/checker.py",
        "src/proofpack/narrate/claims.py",
        "src/proofpack/render/anchors.py",
        "src/proofpack/render/html.py",
        "src/proofpack/templates/T8.html",
        "src/proofpack/run.py",
    } <= files
