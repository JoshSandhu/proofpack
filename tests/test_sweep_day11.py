"""Build day 11 (E11 item 9): the mutation sweep declares a day-11 list.

Run by ``python scripts/mutation_sweep.py --marker day11`` (DEC-12 ii). Pinned here: every
id unique across the whole listing; at least one mutant per item landed (the item's
module named below); the brief's named mutants are present (the header qualifier dropped,
a compare not counted, the Se/Sp McNemar b and c swapped, the exact/corrected threshold
moved, DEFF forced to 1, n_eff = n * DEFF, the coverage bar at 0.85, a reason code
reverted); one per day-6 observer (19); and every day-11 pattern matches its file the
declared number of times (a moved line fails here, not at sweep time).
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.day11

ROOT = Path(__file__).resolve().parents[1]


def _module():
    spec = importlib.util.spec_from_file_location(
        "mutation_sweep_day11", ROOT / "scripts" / "mutation_sweep.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    return mod


def test_the_day11_list_covers_every_item_and_the_named_mutants():
    mod = _module()
    ids = [m.id for m in mod.MUTANTS]
    assert len(ids) == len(set(ids))
    day11 = {m.id: m for m in mod.MUTANTS_DAY11}
    assert all(m.day == 11 and m in mod.MUTANTS for m in mod.MUTANTS_DAY11)
    named = {
        "e11_t1_header_qualifier_dropped",
        "e11_compare_not_counted",
        "e11_se_sp_mcnemar_b_c_swapped",
        "e11_exact_threshold_moved_to_26",
        "e11_deff_forced_to_one",
        "e11_n_eff_times_deff",
        "e11_coverage_bar_at_0_85",
        "e11_row132_reason_reverted",
        "e11_row149_reason_reverted",
    }
    assert named <= set(day11)
    observers = sorted(i for i in day11 if i.startswith("e11_obs"))
    assert [int(i[7:9]) for i in observers] == list(range(1, 20))
    files = {m.file for m in mod.MUTANTS_DAY11}
    assert {
        "src/proofpack/cli.py",
        "src/proofpack/render/t1.py",
        "src/proofpack/run.py",
        "src/proofpack/stats/comparison.py",
        "src/proofpack/render/t2.py",
        "src/proofpack/stats/proportions.py",
        "src/proofpack/stats/bootstrap.py",
        "scripts/coverage_bar.py",
        "src/proofpack/stats/calibration.py",
        "src/proofpack/stats/descriptive.py",
        "src/proofpack/criteria.py",
    } <= files


def test_every_day11_pattern_matches_its_file_the_declared_number_of_times():
    for m in _module().MUTANTS_DAY11:
        text = (ROOT / m.file).read_text(encoding="utf-8")
        assert len(re.findall(m.pattern, text, flags=re.M)) == m.count, m.id
