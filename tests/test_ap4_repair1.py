"""A-P4 repair round 1 (build day 10, lane A, run on 26 September 2026): the two lens-1
notes at ``4879ac5`` (``handoffs/2026-09-25_A_ap4_lens1_fresh-attack.md`` and
``..._regression.md``). Each sentence violation is closed here by a phrase test that fails
at ``4879ac5``; the behaviour the corrected sentences describe is measured beside them.

* FA-S1 = RG1-N2: ``render/docx.py`` cited the byte-identity test under
  ``tests/test_ap4_roundtrip.py``; it is in ``tests/test_ap4_determinism.py``.
* FA-S2: ``render/figures_png.py`` cited a truncated test id.
* FA-S3: "a customer string is written as it is" - docxtpl rewrites ``{_{``, ``}_}``,
  ``{_%``, ``%_}`` after rendering and turns a newline into a line break (measured below).
* RG1-N1: ``tests/ap4_docx.py`` and ``ci.yml`` said what the two CI jobs do; neither has run.
  The docstring and the comment now record the local measurement with the modules hidden.
* RG1-N3: ``tests/test_ap4_sentences.py`` named FA3-S2 as a note-only item of the seven; the
  note-only item is lens 2 FA N6 alone.
* RG1-N9: the ap4 wheel test built through ``uv build --wheel`` without ``--offline``;
  DEC-72 names the offline route as the only one.
* RG1-N11: ``scripts/mutation_sweep.py`` said every ap4 mutant "would count as survived"
  without the extra, unmeasured; measured, one of three tried does, two are killed by the
  pattern-count test alone. The comment now says so.
* FA-R4 (record-and-carry in the lens, closed here): nothing asserted the vertical order of
  F5 rows in the PNG; ``test_f5_png_rows_sit_at_the_svg_row_fractions_top_down`` does, and
  the mutant ``ap4_f5_rows_flipped`` joins the ap4 list.
* RP1-1 (found here by naming the killing test of every ap4 mutant): ``ap4_figure_width_100mm``
  passed ``test_inline_images_are_160_mm_wide_...`` at ``4879ac5`` because that test read its
  expected extent from the mutated constant; the sweep reported it killed on
  ``test_sweep_ap4``'s pattern-count test alone. The test now types 5,760,000 EMU.
* FA-S4 (the builder's note): 20 of the synthetic T7's 21 ``[unverified]`` runs are in
  ``PP Unverified``; the one in a plain run is the conventions paragraph "Fairness is
  measured, never mitigated." (``conventions_T7.md`` through ``markdown_blocks``, one run per
  paragraph). Pinned below so the note's count stays measured.
"""

from __future__ import annotations

import copy
import re
from collections import Counter
from pathlib import Path

import pytest

from ap4_docx import all_text, needs_extra, part, styled_runs, synthetic_document
from test_render_figures import _figure, _plot

pytestmark = [pytest.mark.day10, pytest.mark.ap4]
REPO = Path(__file__).resolve().parent.parent

ABSENT = [
    (
        "src/proofpack/render/docx.py",
        "tests/test_ap4_roundtrip.py::\ntest_two_renders_of_one_document_are_byte_identical",
    ),
    ("src/proofpack/render/docx.py", "a customer string is written as it is"),
    ("src/proofpack/render/figures_png.py", "::test_png_bytes_are_identical_across_two_renders``"),
    ("tests/ap4_docx.py", "so the skip cannot hide there"),
    (".github/workflows/ci.yml", "so the same tests skip there with that named reason"),
    ("scripts/mutation_sweep.py", "every mutant would count as survived"),
    ("tests/test_ap4_sentences.py", "lens 2 FA N6 and FA3-S2"),
    ("tests/test_ap4_templates.py", "_build_wheel"),
    ("tests/test_ap4_docx.py", "render_docx.FIGURE_WIDTH_MM * 36000"),
]
PRESENT = [
    (
        "src/proofpack/render/docx.py",
        "tests/test_ap4_determinism.py::\ntest_two_renders_of_one_document_are_byte_identical",
    ),
    ("src/proofpack/render/docx.py", "no customer string is evaluated as a\ntemplate"),
    (
        "src/proofpack/render/figures_png.py",
        "::test_png_bytes_are_identical_across_two_renders_and_carry_no_metadata``",
    ),
    ("tests/ap4_docx.py", "Neither job had run when this was written"),
    (".github/workflows/ci.yml", "Neither job had run anywhere when this was written"),
    ("scripts/mutation_sweep.py", "is reported SURVIVED"),
    ("tests/test_ap4_sentences.py", "One of the seven (lens 2 FA N6)"),
    ("tests/test_ap4_templates.py", '"--offline"'),
    ("tests/test_ap4_docx.py", "== {5_760_000}"),
]


@pytest.mark.parametrize("name,phrase", ABSENT)
def test_the_false_sentence_is_absent(name: str, phrase: str):
    assert phrase not in (REPO / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name,phrase", PRESENT)
def test_the_corrected_sentence_is_present(name: str, phrase: str):
    assert phrase in (REPO / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "module", ["src/proofpack/render/docx.py", "src/proofpack/render/figures_png.py"]
)
def test_every_test_citation_in_the_module_docstring_names_a_def_in_that_file(module: str):
    """Inspects the module docstring for ``tests/<file>.py::<name>`` citations (a line break
    after ``::`` allowed) and looks for ``def <name>(`` in that file. FA-S1 and FA-S2 were
    each one such citation whose name was not in the cited file."""
    src = (REPO / module).read_text(encoding="utf-8")
    docstring = src.split('"""')[1]
    cites = re.findall(r"(tests/test_\w+\.py)\s*::\s*(test_\w+)", docstring)
    assert len(cites) >= 1, module
    for file, name in cites:
        assert f"def {name}(" in (REPO / file).read_text(encoding="utf-8"), (file, name)


def test_the_f5_rows_flipped_mutant_is_in_the_ap4_list():
    """Only the id, marker and day: the pattern count is ``test_sweep_ap4``'s. A pattern
    check here would fail first under ``-x`` when the mutant is planted and hide whether
    ``test_f5_png_rows_sit_at_the_svg_row_fractions_top_down`` kills it (measured: it did,
    at ``1 failed, 81 passed``, before this test lost its pattern assertion)."""
    from test_sweep_ap4 import _sweep

    mod = _sweep()
    (m,) = [x for x in mod.MUTANTS if x.id == "ap4_f5_rows_flipped"]
    assert m.marker == "ap4" and m.day == 10 and m.file == "src/proofpack/render/figures_png.py"


# ------------------------------------------------------------------ behaviour (the extra)


@pytest.fixture(scope="module")
def document():
    return synthetic_document()


def _with_model_name(document, name: str):
    doc = copy.deepcopy(document)
    doc["declarations"]["model"]["name"] = name
    return doc


@needs_extra
def test_docxtpl_rewrites_the_four_escape_sequences_and_a_newline(document):
    """FA-S3: ``declarations.model.name`` of T8 fed the literal strings below. Not evaluated
    as a template (``m49n`` never appears); the DOCX text is docxtpl's rewrite."""
    from proofpack.render import docx as render_docx

    cases = {
        "m{_{ 7*7 }_}n": "m{{ 7*7 }}n",
        "p{_% if 1 %_}q": "p{% if 1 %}q",
        "QQa\nbZZ": "QQa\nbZZ",  # a <w:br/> in the XML; python-docx reads the break as \n
        "a\tb": "a\tb",  # round-trips (a <w:tab/>)
    }
    for planted, read_back in cases.items():
        data = render_docx.render_docx_bytes(_with_model_name(document, planted), "T8")
        text = all_text(data)
        assert read_back in text, planted
        assert "m49n" not in text
        if planted != read_back:
            assert planted not in text, planted
    data = render_docx.render_docx_bytes(_with_model_name(document, "QQa\nbZZ"), "T8")
    assert re.search(r"QQa</w:t>\s*<w:br/>\s*<w:t[^>]*>bZZ", part(data, "word/document.xml"))


@needs_extra
def test_f5_png_rows_sit_at_the_svg_row_fractions_top_down(document):
    """FA-R4: for every F5 figure of the synthetic document (nine: age, sex, site x
    sensitivity, specificity, AUROC), each estimate marker's y, as a fraction of the axis
    height from the bottom (``(ylim[0] - y) / (ylim[0] - ylim[1])``), equals the SVG
    circle's ``cy`` through the inverse map (``ymin`` 0, ``ymax`` 1: a fraction from the
    bottom), to 1e-9; the y limits are inverted (first row at the top) and the marker ys
    increase with the row index. At ``4879ac5`` the same code passes; the planted
    ``ap4_f5_rows_flipped`` (``ax.set_ylim(-0.5, n_rows - 0.5)``) fails here."""
    from proofpack.render import anchors, figures, figures_png
    from proofpack.render import t1 as render_t1

    page = render_t1.render_t1(document)
    ids = [r["id"] for r in document.get("guidance_refs") or []]
    refs = {r["id"]: r for r in anchors.resolve(ids)}
    figs = figures_png.all_figures(document, refs)
    specs = figures.f5_forest(document, {})
    checked = 0
    for attribute, per_metric in figs["f5"].items():
        for fig, spec in zip(per_metric, specs[attribute], strict=True):
            inv, plot = _plot(_figure(page, spec["id"]))
            cys = re.findall(r'data-role="estimate" cx="[^"]+" cy="([^"]+)"', plot)
            ax = fig.axes[0]
            bottom, top = ax.get_ylim()
            assert bottom > top, (spec["id"], ax.get_ylim())
            ests = [a for a in ax.lines if (a.get_gid() or "").startswith("estimate:")]
            ests.sort(key=lambda a: int(a.get_gid().split(":")[1]))
            assert len(ests) == len(cys) >= 2, spec["id"]
            ys = []
            for artist, cy in zip(ests, cys, strict=True):
                ((_, my),) = [(float(x), float(y)) for x, y in artist.get_xydata()]
                ys.append(my)
                frac_png = (bottom - my) / (bottom - top)
                frac_svg = inv.y(float(cy))
                assert abs(frac_png - frac_svg) <= 1e-9, (spec["id"], my, cy, frac_png, frac_svg)
            assert ys == sorted(ys) and ys[0] == 0.0, (spec["id"], ys)
            checked += 1
    assert checked == 9


@needs_extra
def test_t7_unverified_runs_are_twenty_in_pp_unverified_and_one_in_the_conventions_paragraph(
    document,
):
    from proofpack.render import docx as render_docx

    runs = styled_runs(render_docx.render_docx_bytes(document, "T7"))
    marked = [(r, t) for t, _, r in runs if "[unverified]" in t]
    assert Counter(r for r, _ in marked) == {"PP Unverified": 20, None: 1}
    (plain,) = [t for r, t in marked if r is None]
    assert plain.startswith("Fairness is measured, never mitigated.")
