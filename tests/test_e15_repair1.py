"""E15 repair 1 (build day 15, lane E): the findings of the two cold lenses on ``e5319e0``
(``handoffs/2026-10-08_E_e15_lens1_fresh-attack.md`` and
``handoffs/2026-10-08_E_e15_lens1_regression.md``).

* RG-B1 / FA-R1: E15 changed what ``anchors.with_note_fields`` returns, and the site's JS
  port and its tests S10-S3-2 and S10-S3-2b compare against it (DEC-43). The record is in
  the function's docstring and in the repair note's changes for lane S; the test below
  reads the docstring for the old shape, the port's path and the two site test ids.
* FA-R2: the module docstring of ``test_e15_sections.py`` said 30 of the 32 rows had an
  empty ``section`` at effc5c7 and that every regulatory note printed ``eSTAR: to
  confirm``. Measured at effc5c7: 32 of 32 empty; ``estar`` was ``to confirm`` for 21 rows
  and ``n/a`` for 9 regulatory rows.
* RG-N1: the docstring of the draft-row test in ``test_e15_sections.py`` said filling
  ``section`` "cannot drop" the draft words; the test reads three CSV columns and calls no
  label code (mutant K, which drops the draft label from the note item, leaves it passing).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proofpack.render import anchors

pytestmark = pytest.mark.day15

REPO = Path(__file__).resolve().parent.parent

FALSE = [
    # FA-R2: at effc5c7 all 32 rows had an empty section, not 30
    ("tests/test_e15_sections.py", "30 of the 32 rows"),
    # FA-R2: the FDA_STAT2007_* and UK/EU notes printed "eSTAR: n/a" at effc5c7
    ("tests/test_e15_sections.py", "so every regulatory margin note printed"),
    # RG-N1: the test does not inspect the label
    ("tests/test_e15_sections.py", "cannot drop them"),
]
CORRECTED = [
    ("tests/test_e15_sections.py", "At effc5c7 all 32 rows"),
    ("tests/test_e15_sections.py", "the 4 ``FDA_STAT2007_*`` rows"),
    ("tests/test_e15_sections.py", "Inspects the CSV only"),
]


@pytest.mark.parametrize(("rel", "phrase"), FALSE, ids=[p for _, p in FALSE])
def test_the_sentences_the_e15_lenses_found_false_are_gone(rel: str, phrase: str):
    assert phrase not in (REPO / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize(("rel", "phrase"), CORRECTED, ids=[p for _, p in CORRECTED])
def test_the_replacement_sentences_are_present(rel: str, phrase: str):
    assert phrase in (REPO / rel).read_text(encoding="utf-8")


def test_rg_b1_with_note_fields_records_its_contract_change_and_the_site_port():
    doc = " ".join((anchors.with_note_fields.__doc__ or "").split())
    for phrase in (
        "at effc5c7 both fields were bare",
        "proofpack-site/src/data/guidance-notes.mjs",
        "S10-S3-2 and S10-S3-2b",
        "DEC-43",
    ):
        assert phrase in doc, phrase
