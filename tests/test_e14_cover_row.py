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

import io
import json
import re
import zipfile

import pytest

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


def test_docx_cover_row_names_the_distinct_documents(document):  # noqa: F811
    pytest.importorskip("docxtpl")
    from proofpack.render import docx as render_docx  # noqa: PLC0415

    for template_id in ("T1", "T8"):
        data = render_docx.render_docx_bytes(document, template_id)
        xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
        text = re.sub(r"<[^>]+>", "", xml)
        cell = text[text.index("Guidance versions referenced") :]
        cell = cell[len("Guidance versions referenced") : cell.index("Customer sections")]
        assert INTERNAL_PREFIX not in cell, template_id
        assert cell.count(AIDSF_TITLE) == 1, (template_id, cell.count(AIDSF_TITLE))
