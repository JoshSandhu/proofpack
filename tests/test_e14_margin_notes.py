"""Build day 14 (E14 item 2; LW-01 user review note 9): within one block, anchors that
resolve to the same visible margin line (same document label, same ``section``, same
``eSTAR`` text) print that line once; lines that differ in any visible part stay. The
merged ids stay on the printed line as ``data-also`` so every anchor D4 section 2 names
for the block is still cited.

At 3ee5601 T1 section 7 printed four lines, two distinct: the FDA 2007 statistical
guidance line twice (``FDA_STAT2007_CI``, ``FDA_STAT2007_INDETERMINATE``) and the AI-DSF
draft line twice (``FDA_AIDSF_PERF_VALIDATION``, ``FDA_AIDSF_LABELING_METRICS``);
T2 section 5 printed the PCCP line twice (``FDA_PCCP_MP4_UPDATE``, ``FDA_PCCP_PMS_PLANS``).
"""

from __future__ import annotations

import re

import pytest

from ap4_docx import needs_extra
from e14_pages import (
    DRAFT_LABEL,
    NOTE,
    blocks,
    document,  # noqa: F401 - a fixture
    licensed_pack,  # noqa: F401 - a fixture
    pages,
    t2_page,  # noqa: F401 - a fixture
    visible,
)
from proofpack.render import anchors
from proofpack.render import t1 as render_t1
from proofpack.render import t2 as render_t2

pytestmark = pytest.mark.day14


def _ids(notes) -> set[str]:
    ids: set[str] = set()
    for _draft, _attr, also, inner in notes:
        ids |= set(re.findall(r'href="#([A-Z0-9_]+)"', inner)) | set(also.split())
    return ids


def test_each_visible_margin_line_is_unique_within_its_block(document, licensed_pack, t2_page):  # noqa: F811
    for name, page in pages(document, licensed_pack, t2_page).items():
        for block, body in blocks(page):
            lines = [visible(n[3]) for n in NOTE.findall(body)]
            assert len(lines) == len(set(lines)), (name, block, lines)


def test_t1_section_7_prints_two_lines_and_keeps_every_anchor(document):  # noqa: F811
    body = dict(blocks(render_t1.render_t1(document)))["t1-s7"]
    notes = NOTE.findall(body)
    assert len(notes) == 2
    assert _ids(notes) == set(render_t1.T1_ANCHORS["s7"])
    # the AI-DSF line keeps the draft qualifier and the draft class
    drafts = [n for n in notes if n[0]]
    assert len(drafts) == 1 and DRAFT_LABEL in visible(drafts[0][3])
    assert drafts[0][2] == "FDA_AIDSF_LABELING_METRICS"


def test_every_block_still_cites_every_anchor_it_names(document, t2_page):  # noqa: F811
    for page, sections, prefix in (
        (render_t1.render_t1(document), render_t1.T1_ANCHORS, "t1-"),
        (t2_page, render_t2.T2_ANCHORS, "t2-"),
    ):
        by_block = dict(blocks(page))
        for key, ids in sections.items():
            block = {"scope": f"{prefix}scope-limits", "s0": "@start"}.get(key, f"{prefix}{key}")
            assert _ids(NOTE.findall(by_block[block])) == set(ids), block


def test_t2_section_5_prints_the_pccp_line_once(t2_page):  # noqa: F811
    notes = NOTE.findall(dict(blocks(t2_page))["t2-s5"])
    assert len(notes) == 1 and notes[0][2] == "FDA_PCCP_PMS_PLANS"


def test_lines_that_differ_in_any_visible_part_stay():
    a = {"id": "A", "label": "L", "section": "to confirm", "estar": "to confirm", "draft": True}
    b = {**a, "id": "B", "section": "4.2"}
    c = {**a, "id": "C", "estar": "n/a"}
    d = {**a, "id": "D", "label": "M"}
    e = {**a, "id": "E"}
    out = anchors.distinct_notes([a, b, c, d, e])
    assert [x["id"] for x in out] == ["A", "B", "C", "D"]
    assert out[0]["also"] == ["E"] and all(x["also"] == [] for x in out[1:])
    # the inputs are not changed (the DOCX template reads the same context)
    assert "also" not in a and "also" not in e


@pytest.mark.ap4
@needs_extra
def test_docx_t1_prints_each_repeated_line_once_naming_every_id(document):  # noqa: F811
    """The DOCX margin line prints its ids in brackets; since E14 a merged line names every
    id it stands for (at 3ee5601 T1.docx section 7 printed four rows, two of them repeats
    differing only in the bracketed id, and the HTML/DOCX draft-label counts were equal).
    Marked ``ap4`` so the CI job docx-extra runs it under ``PROOFPACK_REQUIRE_DOCX=1``
    (E14 repair 1, RG-N3)."""
    import io  # noqa: PLC0415
    import zipfile  # noqa: PLC0415

    from proofpack.render import docx as render_docx  # noqa: PLC0415

    data = render_docx.render_docx_bytes(document, "T1")
    xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
    text = re.sub(r"<[^>]+>", "", xml)
    assert text.count("[FDA_STAT2007_CI, FDA_STAT2007_INDETERMINATE]") == 1
    assert text.count("[FDA_AIDSF_PERF_VALIDATION, FDA_AIDSF_LABELING_METRICS]") == 1
    assert "[FDA_STAT2007_INDETERMINATE]" not in text
    assert "[FDA_AIDSF_LABELING_METRICS]" not in text
