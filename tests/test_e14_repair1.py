"""E14 repair 1 (build day 14, lane E): the findings of the two cold lenses on ``a1840fc``
(``handoffs/2026-10-07_E_e14_lens1_fresh-attack.md`` and
``handoffs/2026-10-07_E_e14_lens1_regression.md``).

* FA-B1 / RG-N3: the two E14 DOCX tests started with ``pytest.importorskip("docxtpl")`` and
  carried only ``day14``, so every CI job skipped them (CI log of run 37631774505:
  ``SKIPPED [1] tests/test_e14_cover_row.py:90: could not import 'docxtpl'``). The cover
  test is now ``test_docx_cover_row_text_equals_the_html_cover_labels_in_order`` in
  ``test_e14_cover_row.py``; both carry ``ap4`` (the docx-extra job runs ``-m ap4``) and
  :data:`ap4_docx.needs_extra`, whose skip condition is false under
  ``PROOFPACK_REQUIRE_DOCX=1``, the variable that job sets.
  :func:`test_fa_b1_rg_n3_every_e14_docx_test_is_selected_by_ap4_and_takes_the_extra_rule`
  inspects the marks of every ``test_*`` function of the ``test_e14_*`` modules whose source
  calls ``render_docx``.
* FA-B2 / RG-N5, FA-B3, RG-N2: three sentences the lenses found false, each replaced; the
  two tests at the end read the files for the old and the new wording.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import pytest

from ap4_docx import SKIP_REASON

pytestmark = pytest.mark.day14

REPO = Path(__file__).resolve().parent.parent


def _docx_tests():
    for path in sorted((REPO / "tests").glob("test_e14_*.py")):
        if path.stem == Path(__file__).stem:
            continue
        module = importlib.import_module(path.stem)
        for name, fn in vars(module).items():
            if name.startswith("test_") and callable(fn) and "render_docx" in inspect.getsource(fn):
                yield path.stem, name, fn


def test_fa_b1_rg_n3_every_e14_docx_test_is_selected_by_ap4_and_takes_the_extra_rule():
    found = list(_docx_tests())
    assert {(m, n) for m, n, _ in found} == {
        ("test_e14_cover_row", "test_docx_cover_row_text_equals_the_html_cover_labels_in_order"),
        ("test_e14_margin_notes", "test_docx_t1_prints_each_repeated_line_once_naming_every_id"),
    }
    for module, name, fn in found:
        marks = getattr(fn, "pytestmark", [])
        assert "ap4" in {m.name for m in marks}, (module, name)
        reasons = [m.kwargs.get("reason") for m in marks if m.name == "skipif"]
        assert reasons == [SKIP_REASON], (module, name, reasons)
        assert "importorskip" not in inspect.getsource(fn), (module, name)


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
