"""Build day 14 (E14 item 1; LW-01 user review note 8): the cover row ``Guidance versions
referenced`` of T1, T2 and T8 lists each distinct guidance document once, by its map label
(document, version or date, status), never a ``ProofPack internal`` entry, each linking to
the first row of the guidance table carrying that label; the guidance table keeps every
internal id (the full register) and the draft status stays in the label and in run.json.

At 3ee5601, on a licensed ``run --templates T1,T7,T8`` of the site's
``/demo/synthetic_cohort.csv`` (5,000 rows; Windows 11, Python 3.14), T1's cover row had 19
entries - the AI-DSF draft title 12 times and two ``ProofPack internal`` entries - for the
table's 3 distinct documents; T8's had 7 for 2. The same counts on this file's 5,000-row
``make_cohort`` run: ``test_licensed_t1_cover_has_the_three_documents_the_table_names``
reads ``assert 19 == 3`` at 3ee5601.
"""

from __future__ import annotations

import html
import json

import pytest

from ap4_docx import cell_texts, needs_extra
from e14_pages import (
    AIDSF_TITLE,
    DRAFT_LABEL,
    INTERNAL_PREFIX,
    cover,
    document,  # noqa: F401 - a fixture
    guidance_table,
    licensed_pack,  # noqa: F401 - a fixture
    pages,
    t2_page,  # noqa: F401 - a fixture
)
from proofpack.render import anchors
from proofpack.render import html as render_html
from proofpack.render import t1 as render_t1
from proofpack.resources import load_guidance_map

pytestmark = pytest.mark.day14


def test_cover_row_lists_each_distinct_guidance_document_once(document, licensed_pack, t2_page):  # noqa: F811
    for name, page in pages(document, licensed_pack, t2_page).items():
        got = cover(page)
        expected: list[tuple[str, str]] = []
        for internal_id, _draft, _mono, label in guidance_table(page):
            if label.startswith(INTERNAL_PREFIX):
                continue
            if label not in [lab for _, lab in expected]:
                expected.append((internal_id, label))
        assert got == expected, (name, len(got), len(expected))
        assert len({lab for _, lab in got}) == len(got), name
        assert not [lab for _, lab in got if lab.startswith(INTERNAL_PREFIX)], name
        aidsf = [lab for _, lab in got if AIDSF_TITLE in lab]
        assert len(aidsf) <= 1, name
        assert all(DRAFT_LABEL in lab for lab in aidsf), name


def test_licensed_t1_cover_has_the_three_documents_the_table_names(licensed_pack):  # noqa: F811
    page = (licensed_pack / "T1.html").read_text(encoding="utf-8")
    got = cover(page)
    table = guidance_table(page)
    assert len(table) == 19  # the full register: every internal id keeps its row
    assert {"PP_SCOPE", "PP_METHODS"} <= {i for i, *_ in table}
    assert len(got) == 3, [lab[:40] for _, lab in got]
    assert sum(1 for _, lab in got if AIDSF_TITLE in lab) == 1
    # each cover link lands on the first table row carrying its label
    for href, label in got:
        assert href == next(i for i, _d, _m, lab in table if lab == label)


def test_the_draft_status_stays_in_the_structured_data(licensed_pack):  # noqa: F811
    doc = json.loads((licensed_pack / "run.json").read_text(encoding="utf-8"))
    aidsf = [r for r in doc["guidance_refs"] if r["id"].startswith("FDA_AIDSF_")]
    assert aidsf and all(r["draft"] is True and DRAFT_LABEL in r["label"] for r in aidsf)


def test_cover_documents_unit():
    rows = {r["internal_id"]: r for r in load_guidance_map()}
    ids = ["PP_SCOPE", "FDA_AIDSF_CALIBRATION", "FDA_STAT2007_CI", "FDA_AIDSF_MONITORING"]
    ids += ["PP_METHODS", "FDA_STAT2007_BY_SITE"]
    docs = anchors.cover_documents(anchors.resolve(ids))
    # map order: the AI-DSF rows, then the 2007 rows; the internal rows are dropped
    assert [d["id"] for d in docs] == ["FDA_AIDSF_CALIBRATION", "FDA_STAT2007_CI"]
    assert docs[0]["label"] == anchors.label_for(rows["FDA_AIDSF_CALIBRATION"])
    assert docs[0]["draft"] is True and docs[1]["draft"] is False
    assert anchors.cover_documents(anchors.resolve(["PP_SCOPE", "PP_METHODS"])) == []


@pytest.mark.ap4
@needs_extra
def test_docx_cover_row_text_equals_the_html_cover_labels_in_order(document):  # noqa: F811
    """The DOCX cover cell ``Guidance versions referenced`` of T1 and T8, read through
    python-docx, equals the HTML cover's link labels of the same document joined with
    ``"; "``, in order (E14 repair 1, FA-B1: the test this replaces checked only that the
    cell held no internal entry and the AI-DSF title once, and passed with the T1 cover
    loop cut to ``cover_guidance[:1]``). Marked ``ap4`` so the CI job docx-extra runs it
    under ``PROOFPACK_REQUIRE_DOCX=1`` (RG-N3)."""
    from proofpack.render import docx as render_docx  # noqa: PLC0415

    for template_id, html_page in (
        ("T1", render_t1.render_t1(document)),
        ("T8", render_html.render_t8(document)),
    ):
        labels = [html.unescape(lab) for _, lab in cover(html_page)]
        assert labels, template_id
        cells = cell_texts(render_docx.render_docx_bytes(document, template_id))
        at = cells.index("Guidance versions referenced")
        assert cells[at + 1] == "; ".join(labels), (template_id, cells[at + 1], labels)
