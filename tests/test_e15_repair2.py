"""E15 repair 2 (build day 15, lane E): the findings of the two cold lenses on ``0fb6f71``
(``handoffs/2026-10-08_E_e15_lens2_fresh-attack.md`` and
``handoffs/2026-10-08_E_e15_lens2_regression.md``).

* FA-L2-N1 / RG-N1 (one root cause): the ``with_note_fields`` docstring said "The site
  ports this rule". At site 576bd09 ``guidance-notes.mjs`` lines 70-71 still give the bare
  row text or ``to confirm`` and line 95 adds the words ``section`` and ``eSTAR:``; fed
  every row of the tip's map, its ``noteFor`` differed from ``with_note_fields`` in 64 of
  64 section and eSTAR fields (re-measured in this repair). The first test reads the
  docstring for the old sentence and for the replacement.
* FA-L2-N2: the docstring said "A gap is printed, never hidden (E9)". ``str.strip()``
  keeps U+200B, U+2060, U+FEFF and U+180E, and a cell made only of one of them printed
  ``section \\u200b`` with no marking. The sentence is deleted; the docstring now names
  ``str.strip()`` as the test and the four characters as carried. The second test reads
  the docstring; the third inspects every section and eSTAR cell of the shipped map.
* RG-N3: the repair-1 note said a test feeding three spaces would kill mutant M3
  (``.strip()`` removed). The fourth test feeds an empty cell, three spaces, and a tab
  followed by a space, to ``section`` and to ``estar_section`` of ``FDA_AIDSF_DATA_MGMT``,
  and asserts :data:`anchors.SECTION_GAP` and :data:`anchors.ESTAR_GAP`. It passes at
  0fb6f71; with M3 applied it fails (the run is in the repair-2 note).
"""

from __future__ import annotations

import pytest

from proofpack.render import anchors

pytestmark = pytest.mark.day15

ROW = "FDA_AIDSF_DATA_MGMT"
# str.strip() leaves these in place (FA-L2-N2)
KEPT_BY_STRIP = ("​", "⁠", "﻿", "᠎")


def _doc() -> str:
    return " ".join((anchors.with_note_fields.__doc__ or "").split())


def test_fa_l2_n1_docstring_says_the_site_port_still_implements_the_effc5c7_rule():
    doc = _doc()
    assert "The site ports this rule" not in doc
    for phrase in (
        "still implemented the effc5c7 rule at site 576bd09 (lines 70-71 and 95)",
        "field by field and as the note's text",
        "lane S must re-port the rule when its pin moves past E15",
    ):
        assert phrase in doc, phrase


def test_fa_l2_n2_docstring_names_strip_as_the_test_and_the_characters_it_keeps():
    doc = _doc()
    assert "never hidden" not in doc
    for phrase in (
        "empty after ``str.strip()``",
        "U+200B, U+2060, U+FEFF and U+180E",
        "FA-L2-N2, carried",
    ):
        assert phrase in doc, phrase


def test_no_section_or_estar_cell_of_the_shipped_map_is_only_characters_strip_keeps():
    rows = anchors.load_guidance_map()
    assert len(rows) == 32
    bad = []
    for r in rows:
        for col in ("section", "estar_section"):
            cell = "" if r.get(col) is None else str(r[col])
            rest = "".join(ch for ch in cell if ch not in KEPT_BY_STRIP).strip()
            if cell.strip() and not rest:
                bad.append((r["internal_id"], col, cell))
    assert bad == []


@pytest.mark.parametrize("blank", ["", "   ", "\t "], ids=["empty", "three-spaces", "tab-space"])
def test_rg_n3_a_blank_section_or_estar_cell_prints_the_unverified_gap(blank: str):
    rows = [dict(r) for r in anchors.load_guidance_map()]
    row = next(r for r in rows if r["internal_id"] == ROW)
    assert row["section"].strip() and row["status"].startswith("draft")
    row["section"] = blank
    row["estar_section"] = blank
    fields = anchors.with_note_fields(anchors.guidance_ref_item(ROW, rows), rows)
    assert fields["section"] == anchors.SECTION_GAP
    assert fields["estar"] == anchors.ESTAR_GAP
    assert fields["section"].startswith("[unverified]")
    assert fields["estar"].startswith("[unverified]")
