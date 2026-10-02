"""A-P4 item 3 (build day 10, lane A): ``render/docx.py`` - the DOCX rendered through
docxtpl from the **same context** the HTML uses (D4 section 9; D5 section 3.5).

* :func:`docx_context` returns the HTML context builder's dict (``t1_context``,
  ``t7_context``, ``t8_context``) with the DOCX's readings of the HTML-only keys added
  beside them, never in place: every HTML key is present with the same value;
* customer text is in ``PP Manufacturer Text`` (paragraphs), ``PP Manufacturer Text
  Inline`` (runs, including a claim sentence's customer parts through ``RichText``) and
  labelled "Manufacturer text"; the unfilled slots are ``PP Placeholder`` paragraphs with
  :data:`proofpack.scope.PLACEHOLDER`'s text, one per slot;
* ``‡`` (a planted suppressed Number) and ``n.e.`` survive as text;
* every FDA-draft anchor prints its map label with the draft qualifier;
* the criteria table's status cells hold the three status words only, in ``PP Status``;
* the manifest's watermark is in every section's footer beside the short disclaimer, and
  absent everywhere when the manifest carries none;
* the inline images are 160 mm wide and there is one per HTML figure;
* the HTML-only keys have their DOCX reading on the page (T7's conventions, T8's YAML
  echo, T1's sentences);
* a hostile level label is escaped in the XML and round-trips as text.
"""

from __future__ import annotations

import copy
import re
from typing import Any

import pytest

from ap4_docx import (
    MANUFACTURER_PARAGRAPH_STYLES,
    MANUFACTURER_RUN_STYLE,
    STATUS_RUN_STYLE,
    all_text,
    body_paragraphs,
    cell_texts,
    engine_text,
    needs_extra,
    open_docx,
    paragraph_texts,
    part,
    section_footers,
    section_headers,
    styled_runs,
    synthetic_document,
)
from proofpack.narrate.templates import STATUS_WORDS
from proofpack.render import docx as render_docx
from proofpack.render import html as render_html
from proofpack.render import sentences
from proofpack.render import t1 as render_t1
from proofpack.render import t7 as render_t7
from proofpack.scope import PLACEHOLDER, SHORT_FORM, SYNTHETIC_MARK

pytestmark = [pytest.mark.day10, pytest.mark.ap4, needs_extra]

DRAFT_LABEL = "draft guidance (January 2025), not for implementation"
IDS = ("T1", "T7", "T8")


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    return synthetic_document(watermark="TRIAL")


@pytest.fixture(scope="module")
def rendered(document) -> dict[str, bytes]:
    return {i: render_docx.render_docx_bytes(document, i) for i in IDS}


@pytest.fixture(scope="module")
def plain() -> dict[str, bytes]:
    doc = synthetic_document()
    return {i: render_docx.render_docx_bytes(doc, i) for i in IDS}


# ------------------------------------------------------------------ one context


def test_the_docx_context_is_the_html_context_with_readings_added_beside_html_only_keys(
    document,
):
    for template_id, builder in (
        ("T1", render_t1.t1_context),
        ("T7", render_t7.t7_context),
        ("T8", render_html.t8_context),
    ):
        html_ctx = builder(document)
        ctx = render_docx.docx_context(document, template_id)
        for key, value in html_ctx.items():
            assert key in ctx, (template_id, key)
            if isinstance(value, (str, int, float, bool)) or value is None:
                assert ctx[key] == value, (template_id, key)
        added = set(ctx) - set(html_ctx)
        expected = {
            "T1": set(),
            "T7": {
                "subgroup_conventions_blocks",
                "calibration_conventions_blocks",
                "coverage_conventions_blocks",
                "conventions_intro_blocks",
            },
            "T8": set(),
        }[template_id]
        assert added == expected, (template_id, added)
    # T1's added reading sits inside the sentence dicts, beside the html key
    ctx = render_docx.docx_context(document, "T1")
    sentence = ctx["performance"][0]["sentences"][0]
    assert "html" in sentence and "rich" in sentence
    src = open(render_docx.__file__, encoding="utf-8").read()
    for name in ("t1_context", "t7_context", "t8_context"):
        assert name in src
    # no number is formatted in the DOCX module: fmt is only handed to Jinja as filters
    body = src.split('"""', 2)[2]
    assert set(re.findall(r"fmt\.(\w+)", body)) == {
        "number",
        "count",
        "scalar",
        "text",
        "method",
        "p_value",
    }
    assert body.count("fmt.") == 6


def test_t7_conventions_t8_yaml_echo_and_t1_sentences_have_their_docx_reading(document, rendered):
    t7_ctx = render_docx.docx_context(document, "T7")
    t7_text = "\n".join(paragraph_texts(rendered["T7"]))
    for key in ("subgroup_conventions_blocks", "calibration_conventions_blocks"):
        blocks = t7_ctx[key]
        assert blocks and all({"text", "mono"} <= set(b) for b in blocks)
        for b in blocks:
            for line in b["text"].split("\n"):
                assert line in t7_text, (key, line[:60])
    t8_ctx = render_html.t8_context(document)
    t8_text = "\n".join(paragraph_texts(rendered["T8"]))
    for line in t8_ctx["criteria_yaml"].splitlines():
        assert line.strip() in t8_text, line
    t1_text = "\n".join(paragraph_texts(rendered["T1"]))
    claims = document["claims"]
    assert len(claims) >= 40
    for claim in claims[:40]:
        assert sentences.claim_sentence(claim, document) in t1_text, claim["template_id"]


def test_markdown_blocks_reads_paragraphs_headings_and_a_pipe_table():
    blocks = render_docx.markdown_blocks(
        "## Heading **bold**\n\nA `code` para\ncontinues.\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n\nEnd."
    )
    assert blocks == [
        {"text": "Heading bold", "mono": False},
        {"text": "A code para continues.", "mono": False},
        {"text": "| a | b |\n|---|---|\n| 1 | 2 |", "mono": True},
        {"text": "End.", "mono": False},
    ]


# ------------------------------------------------------------------ customer text


def test_customer_text_is_in_the_manufacturer_styles_and_labelled(document, rendered):
    runs = styled_runs(rendered["T1"])
    justifications = {
        c["justification"] for c in document["declarations"]["criteria"] if c.get("justification")
    }
    assert justifications
    para_texts = {}
    for text, pstyle, _ in runs:
        para_texts.setdefault(pstyle, []).append(text)
    manufacturer = "\n".join(para_texts.get("PP Manufacturer Text", []))
    for j in justifications:
        assert j in manufacturer, j
    d = open_docx(rendered["T1"])
    labels = [p.text for p in body_paragraphs(d) if p.style.name == "PP Manufacturer Text Label"]
    assert labels and all(t.startswith("Manufacturer text - ") for t in labels), labels[:3]
    # the model name (DEC-62) in the header and the level labels in the subgroup tables
    model = document["declarations"]["model"]
    for h in section_headers(rendered["T1"]):
        assert f"{model['name']} v{model['version']}" in h
    levels = {r["level"] for r in document["subgroups"]}
    inline_or_manufacturer = {
        text.strip()
        for text, pstyle, rstyle in runs
        if pstyle in MANUFACTURER_PARAGRAPH_STYLES or rstyle == MANUFACTURER_RUN_STYLE
    }
    joined = "\n".join(inline_or_manufacturer)
    for level in levels:
        assert level in joined, level
    # a claim sentence's customer part (the operating point id) is an inline-styled run
    op = next(k for k in document["overall"] if k != "threshold_free")
    assert any(
        text.strip() == op and rstyle == MANUFACTURER_RUN_STYLE and pstyle == "PP Body"
        for text, pstyle, rstyle in runs
    ), "claim sentence customer part"


def test_each_unfilled_slot_is_a_placeholder_paragraph_with_the_exact_text(document, rendered):
    slots = render_t1.customer_slots(document)
    outstanding = [s for s in slots.values() if not s["filled"]]
    assert outstanding
    d = open_docx(rendered["T1"])
    placeholders = [p.text for p in body_paragraphs(d) if p.style.name == "PP Placeholder"]
    expected = [PLACEHOLDER.format(title=s["title"]) for s in outstanding]
    for text in expected:
        assert text in placeholders, text
    # the cover count and the INCOMPLETE stamp
    assert f"customer sections outstanding: {len(outstanding)}" in all_text(rendered["T1"])
    assert placeholders.count(expected[0]) == 1


# ------------------------------------------------------------------ glyphs


def test_suppressed_mark_and_not_estimable_survive_as_text(document):
    doc = copy.deepcopy(document)
    num = doc["overall"]["op1"]["sensitivity"]
    num["suppressed"] = True
    data = render_docx.render_docx_bytes(doc, "T1")
    text = "\n".join(paragraph_texts(data))
    assert "‡" in text
    assert "‡" not in "\n".join(paragraph_texts(render_docx.render_docx_bytes(document, "T1")))
    assert "n.e." in text
    assert "n.e. (" in text  # the reason beside it


# ------------------------------------------------------------------ anchors


@pytest.mark.parametrize("template_id", IDS)
def test_every_fda_draft_anchor_prints_its_map_label_with_the_qualifier(
    document, rendered, template_id
):
    ctx = render_docx.docx_context(document, template_id)
    text = engine_text(rendered[template_id])
    refs = ctx["guidance_refs"]
    drafts = [r for r in refs if r.get("draft")]
    assert drafts
    for r in refs:
        assert r["label"] in text, r["id"]
        if r.get("draft"):
            assert DRAFT_LABEL in r["label"]
    assert text.count(DRAFT_LABEL) >= len(drafts)
    assert text.count("maps to") >= {"T1": 15, "T7": 6, "T8": 6}[template_id]


# ------------------------------------------------------------------ status words


@pytest.mark.parametrize("template_id", ("T1", "T8"))
def test_status_cells_hold_the_three_words_only_in_pp_status(rendered, template_id):
    runs = styled_runs(rendered[template_id])
    status_runs = [text for text, _, rstyle in runs if rstyle == STATUS_RUN_STYLE]
    assert status_runs
    assert set(status_runs) <= set(STATUS_WORDS.values())
    assert {"criterion met", "criterion not met", "not assessable"} == set(STATUS_WORDS.values())


# ------------------------------------------------------------------ footer


@pytest.mark.parametrize("template_id", IDS)
def test_the_watermark_and_the_short_disclaimer_are_in_every_section_footer(
    document, rendered, plain, template_id
):
    footers = section_footers(rendered[template_id])
    assert len(footers) == {"T1": 9, "T7": 3, "T8": 3}[template_id]
    head = SHORT_FORM.split("{")[0]
    for f in footers:
        assert f.startswith(head) and "TRIAL" in f
        assert document["manifest"]["started"] in f
        assert "Page " in f
    for f in section_footers(plain[template_id]):
        assert f.startswith(head) and "TRIAL" not in f
    # the watermark part is a paragraph in PP Watermark; absent from the plain render
    assert 'w:val="PPWatermark"' in part(rendered[template_id], "word/footer1.xml")
    # the cover stamp: the licence mark only when the manifest carries one (the INCOMPLETE
    # mark is there in both, the synthetic run has unfilled slots)
    plain_stamps = [
        p.text for p in open_docx(plain[template_id]).paragraphs if p.style.name == "PP Stamp"
    ]
    stamps = [
        p.text for p in open_docx(rendered[template_id]).paragraphs if p.style.name == "PP Stamp"
    ]
    assert "TRIAL" in stamps and "TRIAL" not in plain_stamps
    # T8 section 11 repeats the marks when a licence or data mark applies, so the sets
    # are compared, not the lists
    assert set(stamps) - {"TRIAL"} == set(plain_stamps)
    if template_id != "T7":  # T7 has no customer-text slot, so no INCOMPLETE stamp
        assert plain_stamps and plain_stamps[0].startswith("INCOMPLETE - customer sections")


def test_the_data_mark_joins_the_licence_mark_in_the_footer(document):
    doc = synthetic_document(watermark="TRIAL", data_marking=SYNTHETIC_MARK)
    data = render_docx.render_docx_bytes(doc, "T8")
    for f in section_footers(data):
        assert f"TRIAL · {SYNTHETIC_MARK}" in f


# ------------------------------------------------------------------ figures in place


def test_inline_images_are_160_mm_wide_one_per_html_figure_at_the_figure_position(
    document, rendered
):
    xml = part(rendered["T1"], "word/document.xml")
    extents = re.findall(r'<wp:extent cx="(\d+)" cy="(\d+)"', xml)
    page = render_t1.render_t1(document)
    assert len(extents) == len(re.findall(r"<svg ", page)) == 11
    # 160 mm x 36,000 EMU per mm, typed here and not read from the module: at 4879ac5 the
    # expected value was read from the module's FIGURE_WIDTH_MM constant, so the planted mutant
    # ap4_figure_width_100mm passed this test (A-P4 repair 1, RP1-1)
    assert {int(cx) for cx, _ in extents} == {5_760_000}
    # each image is followed by its caption, as the HTML's figcaption
    d = open_docx(rendered["T1"])
    paras = d.paragraphs
    captions = 0
    for i, p in enumerate(paras):
        if "<wp:extent" in p._p.xml or "graphicData" in p._p.xml:
            nxt = paras[i + 1]
            assert nxt.style.name == "PP Caption" and nxt.text.startswith("F"), nxt.text[:40]
            captions += 1
    assert captions == 11
    assert "F3 (precision-recall) is not drawn" in "\n".join(paragraph_texts(rendered["T1"]))


# ------------------------------------------------------------------ escaping


def test_a_hostile_level_label_is_escaped_in_the_xml_and_round_trips(document):
    doc = copy.deepcopy(document)
    hostile = '<w:t>&</w:t>"{{ 1 + 1 }}'
    for row in doc["subgroups"]:
        if row["attribute"] == "sex" and row["level"] == "F":
            row["level"] = hostile
    data = render_docx.render_docx_bytes(doc, "T1")
    xml = part(data, "word/document.xml")
    assert "&lt;w:t&gt;&amp;&lt;/w:t&gt;" in xml
    assert "{{ 1 + 1 }}" in "\n".join(cell_texts(data))  # not evaluated
    assert hostile in "\n".join(cell_texts(data))


def test_an_unknown_template_id_is_refused_and_the_writer_names_the_file(document, tmp_path):
    with pytest.raises(ValueError):
        render_docx.render_docx_bytes(document, "T2")
    with pytest.raises(ValueError):
        render_docx.docx_context(document, "T9")
    out = render_docx.write_docx("T8")(document, tmp_path)
    assert out.name == "T8.docx" and out.read_bytes()[:2] == b"PK"
