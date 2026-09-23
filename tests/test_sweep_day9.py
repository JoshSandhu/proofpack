"""Build day 9 (E9 item 8): the mutation sweep declares a day-9 list.

The list is run by ``python scripts/mutation_sweep.py --marker day9`` (DEC-12 ii); this
test reads the script's ``--list`` output and pins what the sweep assumes: at least ten
day-9 entries, every id unique across the listing, every file named exists, the list
covers the E9 modules the brief names, and every day-9 pattern matches its file exactly
the number of times it declares (a moved line fails here, not at sweep time).
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.day9

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


def test_the_sweep_declares_a_day9_list_of_ten_or_more_with_unique_ids():
    rows = _listing()
    ids = [r[0] for r in rows if len(r) >= 3]
    assert len(ids) == len(set(ids))
    day9 = [r for r in rows if len(r) >= 3 and r[1] == "day9"]
    assert len(day9) >= 10
    for r in day9:
        assert (ROOT / r[2]).exists(), r
    assert {
        "src/proofpack/narrate/templates.py",
        "src/proofpack/render/sentences.py",
        "src/proofpack/render/t1.py",
        "src/proofpack/render/t7.py",
        "src/proofpack/render/figures.py",
        "src/proofpack/render/html.py",
        "src/proofpack/run.py",
        "src/proofpack/templates/base.html",
        "scripts/build_sample_pack.py",
    } <= {r[2] for r in day9}


def test_every_day9_pattern_matches_its_file_the_declared_number_of_times():
    spec = importlib.util.spec_from_file_location(
        "mutation_sweep", ROOT / "scripts" / "mutation_sweep.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # the dataclass decorator looks its module up
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    assert len(mod.MUTANTS_DAY9) >= 10
    for m in mod.MUTANTS_DAY9:
        text = (ROOT / m.file).read_text(encoding="utf-8")
        assert len(re.findall(m.pattern, text, flags=re.M)) == m.count, m.id


def test_every_declared_mutant_of_every_day_still_matches_its_file():
    """E9 found four stale patterns - three its own code moved, and a day-6 one
    (``list_key_string_not_split``) matching twice since repair 5 of day 8 - each of
    which stops a sweep at plant time. This test reads every list, so a moved line fails
    in CI rather than an evening sweep."""
    spec = importlib.util.spec_from_file_location(
        "mutation_sweep_all", ROOT / "scripts" / "mutation_sweep.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    stale = []
    for m in (*mod.MUTANTS, *mod.AP2_MUTANTS):
        text = (ROOT / m.file).read_text(encoding="utf-8")
        n = len(re.findall(m.pattern, text, flags=re.M))
        if n != m.count:
            stale.append((m.id, m.label, n, m.count))
    assert stale == []
