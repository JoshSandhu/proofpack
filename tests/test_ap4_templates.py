"""A-P4 item 2 (build day 10, lane A): the DOCX templates ``src/proofpack/templates/T1.docx``,
``T7.docx``, ``T8.docx`` and their generator ``scripts/make_docx_templates.py`` (D4 sections
2, 9, 10, 11; D5 section 3.5).

* the generator regenerates the three files into a temporary directory and **every part**
  (``word/document.xml``, ``word/styles.xml``, ``word/header*.xml``, ``word/footer*.xml``
  and the rest) equals the committed file's, so a hand edit to a committed ``.docx`` fails;
  a planted one-character edit is shown to fail;
* every section has its own footer part (not linked to the previous) carrying the
  ``{{ footer }}`` slot, the ``{{ watermark }}`` slot inside ``{%p if watermark %}`` and a
  ``PAGE`` field code, and its own header part carrying D4 section 1.5's header line;
* the margin notes are two-column tables after each section heading (one per anchored
  section: 15 in T1, 6 in T7, 6 in T8), each with the ``ref.draft`` branch;
* every table with rows is a ``{%tr for %}`` row loop; the generator types no colour
  (every colour goes through ``theme.color``), no external relationship, no thumbnail.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pytest

from ap4_docx import (
    TEMPLATES,
    footer_parts,
    header_parts,
    load_generator,
    needs_extra,
    part,
    part_names,
    xml_text,
)

pytestmark = [pytest.mark.day10, pytest.mark.ap4, needs_extra]

IDS = ("T1", "T7", "T8")
#: Sections with a margin-note table: T1's fifteen (D4 section 2), T7's six anchored
#: sections (D4 section 10: sections 6 and 7 carry no anchor), T8's six (``html.T8_ANCHORS``).
MARGIN_NOTE_TABLES = {"T1": 15, "T7": 6, "T8": 6}


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory) -> dict[str, bytes]:
    gen = load_generator()
    out = tmp_path_factory.mktemp("docx_templates")
    paths = gen.write_templates(Path(out))
    assert sorted(p.name for p in paths) == [f"{i}.docx" for i in IDS]
    return {p.stem: p.read_bytes() for p in paths}


def committed(template_id: str) -> bytes:
    return (TEMPLATES / f"{template_id}.docx").read_bytes()


def parts_equal(a: bytes, b: bytes) -> list[str]:
    """The names of the parts that differ between two packages (or exist in one only)."""
    with zipfile.ZipFile(io.BytesIO(a)) as za, zipfile.ZipFile(io.BytesIO(b)) as zb:
        names = set(za.namelist()) | set(zb.namelist())
        return sorted(
            n
            for n in names
            if n not in za.namelist() or n not in zb.namelist() or za.read(n) != zb.read(n)
        )


# ------------------------------------------------------------------ regeneration


@pytest.mark.parametrize("template_id", IDS)
def test_the_regenerated_template_equals_the_committed_one_part_by_part(regenerated, template_id):
    diff = parts_equal(regenerated[template_id], committed(template_id))
    assert diff == [], f"{template_id}.docx: regenerate with python scripts/make_docx_templates.py"
    for name in ("word/document.xml", "word/styles.xml", "word/footer1.xml", "word/header1.xml"):
        assert part(regenerated[template_id], name) == part(committed(template_id), name)


def test_a_one_character_hand_edit_to_a_committed_template_fails_the_comparison(regenerated):
    data = committed("T8")
    edited = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(edited, "w") as dst:
        for info in src.infolist():
            raw = src.read(info.filename)
            if info.filename == "word/document.xml":
                raw = raw.replace(b"{{ template_name }}", b"{{ template_name }} ", 1)
            dst.writestr(info, raw)
    diff = parts_equal(regenerated["T8"], edited.getvalue())
    assert diff == ["word/document.xml"]


# ------------------------------------------------------------------ furniture


@pytest.mark.parametrize("template_id", IDS)
def test_every_section_has_its_own_footer_with_the_slots_and_a_page_field(template_id):
    data = committed(template_id)
    document = part(data, "word/document.xml")
    n_sections = document.count("<w:sectPr")
    footers, headers = footer_parts(data), header_parts(data)
    assert n_sections >= 3 and len(footers) == len(headers) == n_sections, template_id
    # each sectPr references a footer and a header of its own (no section inherits)
    assert document.count('<w:footerReference w:type="default"') == n_sections
    assert document.count('<w:headerReference w:type="default"') == n_sections
    for xml in footers:
        text = xml_text(xml)
        assert "{{ footer }}" in text and "{%p if watermark %}" in text
        assert "{{ watermark }}" in text and "{%p endif %}" in text
        assert re.search(r"<w:instrText[^>]*> PAGE </w:instrText>", xml), template_id
        assert re.search(r"<w:instrText[^>]*> NUMPAGES </w:instrText>", xml), template_id
        assert 'w:fldCharType="begin"' in xml and 'w:fldCharType="end"' in xml
        assert 'w:val="PPFooter"' in xml and 'w:val="PPWatermark"' in xml
    for xml in headers:
        text = xml_text(xml)
        assert "{{ header_customer }}" in text and "{{ header_engine }}" in text
        assert 'w:val="PPManufacturerTextInline"' in xml  # DEC-62: the model name is the maker's


@pytest.mark.parametrize("template_id", IDS)
def test_margin_notes_are_two_column_tables_with_the_draft_branch(template_id):
    document = part(committed(template_id), "word/document.xml")
    text = xml_text(document)
    assert text.count("Guidance anchor") == MARGIN_NOTE_TABLES[template_id], template_id
    tables = re.findall(r"<w:tbl>.*?</w:tbl>", document, re.S)
    notes = [t for t in tables if "Guidance anchor" in xml_text(t)]
    assert len(notes) == MARGIN_NOTE_TABLES[template_id]
    for t in notes:
        assert t.count("<w:gridCol") == 2, "two columns"
        t_text = xml_text(t)
        assert ".draft %}" in t_text and "{%p else %}" in t_text
        assert 'w:val="PPMarginNoteDraft"' in t and 'w:val="PPMarginNote"' in t
        assert ".label }} · section {{" in t_text and "eSTAR: {{" in t_text


@pytest.mark.parametrize("template_id", IDS)
def test_every_row_table_is_a_tr_for_loop_and_the_header_row_repeats(template_id):
    document = part(committed(template_id), "word/document.xml")
    tables = re.findall(r"<w:tbl>.*?</w:tbl>", document, re.S)
    loops = 0
    for t in tables:
        t_text = xml_text(t)
        if "{%tr for " in t_text:
            loops += 1
            assert "{%tr endfor %}" in t_text
        assert "<w:tblHeader" in t  # the header row repeats on a page break
        assert 'w:val="PPTable"' in t
    assert loops >= {"T1": 12, "T7": 4, "T8": 6}[template_id], (template_id, loops)


@pytest.mark.parametrize("template_id", IDS)
def test_the_package_has_no_external_relationship_and_no_thumbnail(template_id):
    data = committed(template_id)
    names = part_names(data)
    assert not any("thumbnail" in n for n in names)
    for n in names:
        if n.endswith(".rels"):
            assert 'TargetMode="External"' not in part(data, n), n
    assert "jpeg" not in part(data, "[Content_Types].xml")
    assert "thumbnail" not in part(data, "_rels/.rels")


# ------------------------------------------------------------------ the generator


def test_the_generator_types_no_colour_and_reads_every_colour_from_the_theme():
    src = (TEMPLATES.parent.parent.parent / "scripts" / "make_docx_templates.py").read_text(
        encoding="utf-8"
    )
    assert re.search(r"#[0-9a-fA-F]{6}\b", src) is None
    assert re.search(r"RGBColor\(\s*0x", src) is None
    assert "RGBColor.from_string(_hex(" in src
    assert "theme.color(token)" in src
    gen = load_generator()
    for name, spec in gen.STYLE_TOKENS.items():
        assert name.startswith("PP "), name
        for key in ("color", "border", "fill", "header_fill"):
            if key in spec:
                assert gen._hex(spec[key]) == gen.theme.color(spec[key]).lstrip("#").upper()


def test_the_generator_stamps_a_fixed_time_and_the_title_of_each_template(regenerated):
    for template_id, data in regenerated.items():
        core = part(data, "docProps/core.xml")
        assert "2026-09-25T00:00:00Z" in core, template_id
        assert "<dc:creator>ProofPack</dc:creator>" in core
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            assert {zi.date_time for zi in z.infolist()} == {(2026, 9, 25, 0, 0, 0)}


def test_a_built_wheel_carries_the_three_docx_templates_beside_the_html_ones(tmp_path):
    """The templates live inside the package (``src/proofpack/templates``), so hatch's
    package include ships them with the code: the wheel built from this tree holds the
    three ``.docx`` beside ``T1.html`` and the rest (no force-include line is needed for a
    file inside the package; ``design/`` and ``schema/`` files need one)."""
    from test_render_theme import _build_wheel

    wheel = _build_wheel(tmp_path / "dist")
    with zipfile.ZipFile(wheel) as z:
        names = set(z.namelist())
        for template_id in IDS:
            assert f"proofpack/templates/{template_id}.docx" in names, template_id
            assert f"proofpack/templates/{template_id}.html" in names, template_id
            assert z.read(f"proofpack/templates/{template_id}.docx") == committed(template_id)
