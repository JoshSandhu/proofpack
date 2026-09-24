"""A-P3 (build day 9, lane A): the ap3 mutant list of ``scripts/mutation_sweep.py``.

Asserted: at least eight mutants carry the marker ``ap3`` and day 9; their ids are unique
across the whole list; each pattern matches its declared count in this tree (a mutant
whose pattern no longer matches would stop the sweep); the copy the sweep makes holds the
Dockerfile, .dockerignore, .github and uv.lock that the ap3 tests read.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent


def _sweep():
    spec = importlib.util.spec_from_file_location(
        "mutation_sweep_ap3", REPO / "scripts" / "mutation_sweep.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["mutation_sweep_ap3"] = module
    spec.loader.exec_module(module)
    return module


def test_the_ap3_list_has_at_least_eight_mutants_whose_patterns_match():
    mod = _sweep()
    ap3 = [m for m in mod.MUTANTS if m.marker == "ap3"]
    assert len(ap3) >= 8 and all(m.day == 9 for m in ap3)
    ids = [m.id for m in mod.MUTANTS]
    assert len(ids) == len(set(ids))
    for m in ap3:
        path = REPO / m.file
        if not path.exists():
            pytest.skip(f"{m.file} is not in this tree")
        text = path.read_text(encoding="utf-8")
        assert len(re.findall(m.pattern, text, flags=re.M)) == m.count, m.id
    assert {"Dockerfile", ".dockerignore", ".github", "uv.lock"} <= set(mod.COPIED)
