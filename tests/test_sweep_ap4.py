"""A-P4 (build day 10, lane A): the ap4 mutant list of ``scripts/mutation_sweep.py``.

Asserted: at least eight mutants carry the marker ``ap4`` and day 10; the eight named
kinds the brief asks for are each present (a fmt call bypassed on the way to the DOCX,
the footer part dropped from a section, the watermark slot emptied, a style colour typed,
the PNG dpi changed, the coordinate map off by one unit, the extra-missing branch
raising, the parity tolerance widened); their ids are unique across the whole list; each
pattern matches its declared count in this tree.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.day10, pytest.mark.ap4]
REPO = Path(__file__).resolve().parent.parent


def _sweep():
    spec = importlib.util.spec_from_file_location(
        "mutation_sweep_ap4", REPO / "scripts" / "mutation_sweep.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["mutation_sweep_ap4"] = module
    spec.loader.exec_module(module)
    return module


def test_the_ap4_list_has_at_least_eight_mutants_of_the_named_kinds_whose_patterns_match():
    mod = _sweep()
    ap4 = [m for m in mod.MUTANTS if m.marker == "ap4"]
    assert len(ap4) >= 8 and all(m.day == 10 for m in ap4)
    ids = [m.id for m in mod.MUTANTS]
    assert len(ids) == len(set(ids))
    for needed in (
        "ap4_t1_cell_fmt_bypassed",
        "ap4_landscape_footer_dropped",
        "ap4_footer_emptied_in_render",
        "ap4_watermark_slot_emptied",
        "ap4_style_colour_typed",
        "ap4_png_dpi_150",
        "ap4_map_off_by_one_unit",
        "ap4_extra_missing_branch_raises",
        "ap4_parity_tolerance_widened",
    ):
        assert needed in ids, needed
    for m in ap4:
        text = (REPO / m.file).read_text(encoding="utf-8")
        assert len(re.findall(m.pattern, text, flags=re.M)) == m.count, m.id
        assert m.what
