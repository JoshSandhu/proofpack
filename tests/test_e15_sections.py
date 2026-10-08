"""Build day 15 (E15): the guidance map's ``section`` column transcribed from the documents.

At effc5c7 all 32 rows of ``design/guidance_map_v1.csv`` had an empty ``section``. Through
``anchors.with_note_fields`` the 30 regulatory rows gave ``section`` ``to confirm``; the 21
FDA AI-DSF and PCCP rows gave ``estar`` ``to confirm``, and the 4 ``FDA_STAT2007_*`` rows
and the 5 UK and EU rows gave ``n/a`` (measured in E15 repair 1). E15
fetched each primary document on 8 October 2026, filled ``section`` with the headings as the
document prints them and recorded the reading in ``design/guidance_sections.yaml``; no
FDA eSTAR mapping was found, so the eSTAR slot prints ``[unverified] eSTAR section not
mapped`` and an empty ``section`` would print ``[unverified] section not transcribed``.

(a) every non-empty ``section`` has a provenance row (url, date read, version line, quoted
headings) and the quoted headings appear in it, in order; (b) a T1 of the 5,000-row synthetic
cohort (the licensed run LW-01 measured) prints no ``to confirm`` and every regulatory note
names its section with the document's draft or final word and carries the [unverified]
eSTAR marking; (c) the markings reach the HTML and the DOCX; (d) the goldens carry them.
"""

from __future__ import annotations

import csv
import html
import io
import re
import zipfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from ap4_docx import needs_extra, synthetic_document
from e14_pages import DRAFT_LABEL, NOTE, licensed_pack, visible  # noqa: F401 - a fixture
from proofpack.render import anchors
from proofpack.render import t1 as render_t1
from proofpack.resources import load_guidance_map

pytestmark = pytest.mark.day15

REPO = Path(__file__).resolve().parents[1]
MAP = REPO / "design" / "guidance_map_v1.csv"
SOURCES = REPO / "design" / "guidance_sections.yaml"
GOLDEN = REPO / "tests" / "fixtures" / "golden"
DATE_READ = "2026-10-08"


def map_rows() -> dict[str, dict[str, str]]:
    with MAP.open(encoding="utf-8", newline="") as fh:
        return {r["internal_id"]: r for r in csv.DictReader(fh)}


def sources() -> dict[str, Any]:
    return yaml.safe_load(SOURCES.read_text(encoding="utf-8"))


def _note_id(note_html: str) -> str:
    m = re.search(r'href="#([A-Z0-9_]+)"', note_html)
    assert m, note_html
    return m.group(1)


# ------------------------------------------------------------------ (a) provenance


def test_every_filled_section_has_a_source_row_with_url_date_and_version():
    rows, src = map_rows(), sources()
    docs = {d["id"]: d for d in src["documents"]}
    prov = {p["internal_id"]: p for p in src["rows"]}
    assert len(prov) == len(src["rows"]), "one provenance row per id"
    filled = {i for i, r in rows.items() if r["section"].strip()}
    assert filled == set(prov), filled ^ set(prov)
    for i in filled:
        row, p = rows[i], prov[i]
        assert p["section"] == row["section"], i  # character for character
        d = docs[p["document"]]
        assert d["map_document"] == row["document"], i
        assert d["url"].startswith("https://"), i
        assert str(d["date_read"]) == DATE_READ, i
        assert d["version_line"].strip() and d["fetch"].startswith("HTTP 200"), i
        assert "transcribed 2026-10-08" in row["notes"], i


def test_every_quoted_heading_appears_in_the_section_in_order():
    for p in sources()["rows"]:
        assert p["headings"], p["internal_id"]
        at = 0
        for h in p["headings"]:
            text = h["text"]
            assert text.strip() == text and "  " not in text, (p["internal_id"], text)
            found = p["section"].find(text, at)
            assert found >= 0, (p["internal_id"], text, p["section"])
            at = found + len(text)


def test_no_regulatory_row_is_left_empty_without_a_reason():
    rows, src = map_rows(), sources()
    unfilled = {u["internal_id"]: u for u in src["unfilled"]}
    for i, r in rows.items():
        if anchors.is_internal(r):
            assert r["section"] == "", i  # ProofPack's own text prints "section n/a"
        elif not r["section"].strip():
            assert unfilled.get(i, {}).get("reason"), f"{i}: empty section without a reason"


def test_no_fda_row_claims_an_estar_section_while_none_was_read():
    src = sources()
    assert src["estar"]["mapped"] is False
    assert src["estar"]["printed"] == anchors.ESTAR_GAP
    for i, r in map_rows().items():
        if r["document"].startswith("FDA"):
            # FDA_STAT2007_* printed "eSTAR: n/a" at effc5c7: an unread claim, now the gap
            assert r["estar_section"] == "", i
        else:
            assert r["estar_section"] in ("", "n/a"), i


def test_the_draft_row_keeps_its_status_and_the_sections_do_not_carry_it():
    """Inspects the CSV only: each FDA_AIDSF_ row's ``status`` is ``draft - not for
    implementation``, its ``version_date`` ``2025-01-07``, and its ``section`` free of the
    word draft. It passes at effc5c7 and calls no label code. The draft label on the page is
    inspected by test (b) below and by ``test_e11_aidsf_header.py`` (E15 repair 1, mutant
    K)."""
    for i, r in map_rows().items():
        if i.startswith("FDA_AIDSF_"):
            assert r["status"] == "draft - not for implementation", i
            assert r["version_date"] == "2025-01-07", i
            assert "draft" not in r["section"].lower(), i


# ------------------------------------------------------------------ the note fields


def test_a_transcribed_row_prints_its_section_and_the_estar_gap():
    item = anchors.guidance_ref_item("FDA_AIDSF_DATA_MGMT")
    note = anchors.with_note_fields(item)
    # at effc5c7: section "to confirm", estar "to confirm"
    assert note["section"] == "section VIII. Data Management"
    assert note["estar"] == "[unverified] eSTAR section not mapped" == anchors.ESTAR_GAP
    internal = anchors.with_note_fields(anchors.guidance_ref_item("PP_SCOPE"))
    assert (internal["section"], internal["estar"]) == ("section n/a", "eSTAR: n/a")
    gb = anchors.with_note_fields(anchors.guidance_ref_item("GB_PMS_44ZM3"))
    assert gb["estar"] == "eSTAR: n/a"


def test_an_empty_section_prints_the_unverified_gap_not_to_confirm():
    rows = [dict(r) for r in load_guidance_map()]
    for r in rows:
        if r["internal_id"] == "FDA_AIDSF_CALIBRATION":
            r["section"] = ""
    note = anchors.with_note_fields(anchors.guidance_ref_item("FDA_AIDSF_CALIBRATION", rows), rows)
    assert note["section"] == "[unverified] section not transcribed" == anchors.SECTION_GAP
    assert "to confirm" not in str(note)


# ------------------------------------------------------------------ (b) T1 of the cohort


def test_t1_of_the_synthetic_cohort_names_every_section_and_marks_every_gap(licensed_pack):  # noqa: F811
    page = (licensed_pack / "T1.html").read_text(encoding="utf-8")
    assert "to confirm" not in page
    rows = map_rows()
    notes = NOTE.findall(page)
    assert len(notes) >= 15
    regulatory = 0
    for draft, _attr, _also, inner in notes:
        i = _note_id(inner)
        text = html.unescape(visible(inner))
        row = rows[i]
        if anchors.is_internal(row):
            assert text.endswith("· section n/a · eSTAR: n/a"), text
            continue
        regulatory += 1
        # names the section the map holds, with the document's draft or final word
        assert f"· section {row['section']} ·" in text, text
        if anchors.is_draft(row):
            assert draft and DRAFT_LABEL in text, text
        else:
            assert not draft and f"{row['status']})" in text, text
        assert "[unverified]" in text and text.endswith(anchors.ESTAR_GAP), text
    assert regulatory >= 15


# ------------------------------------------------------------------ (c) HTML and DOCX


def _render_with_calibration_gap(monkeypatch) -> str:
    rows = [dict(r) for r in load_guidance_map()]
    for r in rows:
        if r["internal_id"] == "FDA_AIDSF_CALIBRATION":
            r["section"] = ""
    monkeypatch.setattr(anchors, "load_guidance_map", lambda: tuple(rows))
    return render_t1.render_t1(synthetic_document())


def test_the_unverified_markings_survive_to_the_html(monkeypatch):
    page = render_t1.render_t1(synthetic_document())
    regulatory = [n for n in NOTE.findall(page) if not _note_id(n[3]).startswith("PP_")]
    assert regulatory and all(anchors.ESTAR_GAP in n[3] for n in regulatory)
    assert anchors.SECTION_GAP not in page
    gap_page = _render_with_calibration_gap(monkeypatch)
    s8 = gap_page[gap_page.index('<h2 id="t1-s8"') : gap_page.index('<h2 id="t1-s9"')]
    assert f"· {anchors.SECTION_GAP} · {anchors.ESTAR_GAP}</aside>" in s8
    assert "to confirm" not in gap_page


@pytest.mark.ap4
@needs_extra
def test_the_unverified_markings_survive_to_the_docx(monkeypatch):
    from proofpack.render import docx as render_docx  # noqa: PLC0415

    def text(doc) -> str:
        data = render_docx.render_docx_bytes(doc, "T1")
        xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
        return html.unescape(re.sub(r"<[^>]+>", "", xml))

    out = text(synthetic_document())
    assert "to confirm" not in out
    assert out.count(anchors.ESTAR_GAP) >= 15
    assert "section VIII. Data Management · [unverified] eSTAR section not mapped" in out
    rows = [dict(r) for r in load_guidance_map()]
    for r in rows:
        if r["internal_id"] == "FDA_AIDSF_CALIBRATION":
            r["section"] = ""
    monkeypatch.setattr(anchors, "load_guidance_map", lambda: tuple(rows))
    gap = text(synthetic_document())
    assert f"· {anchors.SECTION_GAP} · {anchors.ESTAR_GAP}" in gap


# ------------------------------------------------------------------ (d) goldens


@pytest.mark.parametrize("name", ["T1", "T2", "T7", "T8", "T12"])
def test_the_goldens_carry_the_markings_and_no_to_confirm(name):
    page = (GOLDEN / f"{name}.html").read_text(encoding="utf-8")
    assert "to confirm" not in page
    notes = [n for n in NOTE.findall(page) if not _note_id(n[3]).startswith("PP_")]
    assert all(anchors.ESTAR_GAP in n[3] for n in notes), name
