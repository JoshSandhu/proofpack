"""E14 repair 1 (build day 14, lane E): the findings of the two cold lenses on ``a1840fc``
(``handoffs/2026-10-07_E_e14_lens1_fresh-attack.md`` and
``handoffs/2026-10-07_E_e14_lens1_regression.md``).

* FA-B1 / RG-N3: the two E14 DOCX tests started with ``pytest.importorskip("docxtpl")`` and
  carried only ``day14``. In CI run 37631774505 the job ``pytest + ruff`` skipped them
  (``SKIPPED [1] tests/test_e14_cover_row.py:90: could not import 'docxtpl'``) and the job
  ``pytest -m ap4 with the [docx] extra installed`` did not select them. The cover test is
  now ``test_docx_cover_row_text_equals_the_html_cover_labels_in_order`` in
  ``test_e14_cover_row.py``; both carry ``ap4`` (the docx-extra job runs ``-m ap4``) and
  :data:`ap4_docx.needs_extra`, whose skip condition is false under
  ``PROOFPACK_REQUIRE_DOCX=1``, the variable that job sets. The test that inspects their
  marks is in ``test_e14_repair2.py`` (E14 repair 2, FA-B1).
* FA-B2 / RG-N5, FA-B3, RG-N2: three sentences the lenses found false, each replaced; the
  two tests at the end read the files for the old and the new wording.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.day14

REPO = Path(__file__).resolve().parent.parent


FALSE = [
    # FA-B2 / RG-N5: at 3ee5601 the re-prompt read "answer a or q" under "[a]ccept / [q]uit?"
    ("src/proofpack/cli.py", "re-prompted without being told how to accept"),
    # FA-B3: at a1840fc a merged DOCX row prints several ids in one bracket
    ("src/proofpack/render/anchors.py", "the DOCX template prints the id on each line"),
    # RG-N2: a correctly built new parser turns the walk test red (1 failed, 56 passed)
    ("tests/test_e14_global_flags.py", "parser added later is covered without editing this file"),
]
CORRECTED = [
    ("src/proofpack/cli.py", "the review note records that ``y`` re-prompted"),
    ("src/proofpack/render/anchors.py", "prints a merged line's ids together in"),
    ("tests/test_e14_global_flags.py", "pins the set of 8"),
]


@pytest.mark.parametrize(("rel", "phrase"), FALSE, ids=[r for r, _ in FALSE])
def test_the_sentences_the_e14_lenses_found_false_are_gone(rel: str, phrase: str):
    assert phrase not in (REPO / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize(("rel", "phrase"), CORRECTED, ids=[r for r, _ in CORRECTED])
def test_the_replacement_sentences_are_present(rel: str, phrase: str):
    assert phrase in (REPO / rel).read_text(encoding="utf-8")
