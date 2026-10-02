"""A-P4 item 6 (build day 10, lane A): the DOCX round-trip (D4 section 9 "every number
string in the DOCX/HTML parses back to a Number in the JSON at the stated rounding",
section 14).

On one ``proofpack run --format json,html,docx --templates T1,T7,T8`` of the synthetic
cohort (the T1 CLI fixture's cohort and criteria, under an ephemeral licence):

* python-docx reads every paragraph and table cell of each DOCX;
* the twenty-three listed cells of ``tests/test_render_t1.py`` (``LISTED_CELLS``) print in
  the T1 DOCX exactly as that test's own D4 formatter prints the ``run.json`` Number;
* **every decimal token** of each DOCX (``d.d``, signed or not, U+2212 or ASCII minus) is
  explained by one of: a Number of ``run.json`` through :mod:`proofpack.render.format`
  (``number``, ``estimate``, ``interval``, ``bound`` in the four kinds), a declared value
  (``fmt.declared``), an engine scalar (``fmt.scalar``, ``fmt.p_value``), a string the
  document itself carries, or a literal of the template's own text (captions, section
  references); the Number-explained count is asserted so the check has teeth;
* the footer is on every section; the ``[unverified]`` markings, the tier superscripts and
  the draft-anchor labels survive extraction in the same number as the HTML prints them;
* the forbidden-word grep (``test_render_t8.FORBIDDEN_ON_PAGE``) over the engine's text is
  zero; status words only in ``PP Status`` runs;
* the extracted text of each DOCX equals the HTML's visible text for the named cells:
  twenty of T1's listed cells (:data:`TWENTY_CELLS`), every criteria-table cell of T8 and
  every table cell of T7.
"""

from __future__ import annotations

import copy
import csv
import html as html_lib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from ap4_docx import (
    REPO,
    STATUS_RUN_STYLE,
    TEMPLATES,
    TIER_GLYPHS,
    cell_texts,
    engine_text,
    needs_extra,
    open_docx,
    paragraph_texts,
    part,
    section_footers,
    styled_runs,
    words,
    xml_text,
)
from conftest import ephemeral_registry, make_criteria
from proofpack.cli import main
from proofpack.errors import EXIT_OK, EXIT_WARNINGS
from proofpack.narrate.checker import resolve_pointer
from proofpack.narrate.templates import STATUS_WORDS
from proofpack.render import format as fmt
from proofpack.render import t1 as render_t1
from proofpack.render import t7 as render_t7
from proofpack.scope import LONG_FORM_ITEMS, SHORT_FORM
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site
from test_render_t1 import LISTED_CELLS, _Cells, _own_fmt, listed_cells
from test_render_t8 import FORBIDDEN_ON_PAGE, STATUS_TOKENS, text_nodes
from test_run_cli import _own_home, _prepare

pytestmark = [pytest.mark.day10, pytest.mark.ap4, needs_extra]

IDS = ("T1", "T7", "T8")
DRAFT_LABEL = "draft guidance (January 2025), not for implementation"
KINDS = ("proportion", "three_dp", "difference_pp", "difference_3dp")
DECIMAL = re.compile(r"(?<![\w.])[−+-]?\d+\.\d+(?![\w.])")
#: The twenty named cells whose DOCX text must equal the HTML's visible cell text: the
#: first twenty of ``LISTED_CELLS`` (pointer, kind, facet), by name.
TWENTY_CELLS = LISTED_CELLS[:20]


@pytest.fixture(scope="module")
def cli_run(tmp_path_factory):
    """``(doc, {id: html}, {id: docx bytes}, printed)`` of one CLI run with all three
    formats and templates."""
    base = tmp_path_factory.mktemp("ap4cli")
    mp = pytest.MonkeyPatch()
    try:
        _own_home(base, mp)
        crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
        csv_path, yml = _prepare(base, cohort_with_a_thirty_row_site(), crit)
        out = base / "pack"
        rc = main(
            [
                "run",
                "--input",
                str(csv_path),
                "--criteria",
                str(yml),
                "--out",
                str(out),
                "--offline",
                "--format",
                "json,html,docx",
                "--templates",
                "T1,T7,T8",
            ],
            registry=ephemeral_registry(),
        )
        assert rc in (EXIT_OK, EXIT_WARNINGS)
        doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
        pages = {i: (out / f"{i}.html").read_text(encoding="utf-8") for i in IDS}
        docs = {i: (out / f"{i}.docx").read_bytes() for i in IDS}
        return doc, pages, docs
    finally:
        mp.undo()


# ------------------------------------------------------------------ helpers


def _numbers(node: Any):
    """Every Number-shaped dict in the document (an ``est`` key with ``method`` or
    ``ci_lo`` or a typed reason beside it)."""
    if isinstance(node, dict):
        if "est" in node and (
            {"method", "ci_lo", "not_estimable_reason", "suppressed"} & set(node)
        ):
            yield node
        for v in node.values():
            yield from _numbers(v)
    elif isinstance(node, list):
        for v in node:
            yield from _numbers(v)


def _floats(node: Any):
    if isinstance(node, bool):
        return
    if isinstance(node, (int, float)):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _floats(v)
    elif isinstance(node, list):
        for v in node:
            yield from _floats(v)


def _strings(node: Any):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


def _decimals(text: str) -> list[str]:
    return [t.replace("-", "−") for t in DECIMAL.findall(text)]


def number_explained(doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for num in _numbers(doc):
        for kind in KINDS:
            for s in (
                fmt.number(num, kind),
                fmt.estimate(num, kind),
                fmt.interval(num, kind),
            ):
                out.update(_decimals(s))
            if fmt.has_interval(num) and isinstance(num.get("est"), (int, float)):
                for v in (num["est"], num["ci_lo"], num["ci_hi"]):
                    out.update(_decimals(fmt.bound(float(v), kind)))
    return out


def scalar_explained(doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for x in _floats(doc):
        for s in (fmt.declared(x), fmt.scalar(x), fmt.p_value(x), fmt.percent(x)):
            out.update(_decimals(s))
    for s in _strings(doc):
        out.update(_decimals(s))
    return out


def template_literals(template_id: str) -> set[str]:
    xml = part((TEMPLATES / f"{template_id}.docx").read_bytes(), "word/document.xml")
    out = set(_decimals(xml_text(xml)))
    for name in ("conventions_T7.md", "citations.yaml"):
        out.update(_decimals((REPO / "design" / name).read_text(encoding="utf-8")))
    with (REPO / "design" / "guidance_map_v1.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for v in row.values():
                out.update(_decimals(v or ""))
    out.update(_decimals(render_t7.TOLERANCE_POLICY))
    # the engine's prose constants (the long disclaimer names 21 CFR 807.92)
    for prose in (SHORT_FORM, render_t1.PUBLIC_SUMMARY_NOTE, render_t1.COVER_NOTE):
        out.update(_decimals(prose))
    for _title, body in LONG_FORM_ITEMS:
        out.update(_decimals(body))
    return out


class _Tds(HTMLParser):
    """Every ``<td>`` / ``<th>`` of a page as visible text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cells: list[str] = []
        self._depth = 0
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("td", "th"):
            self._depth += 1
            self._buf = []

    def handle_data(self, data):
        if self._depth:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._depth:
            self._depth -= 1
            self.cells.append(" ".join("".join(self._buf).split()))


def _html_cells(page: str) -> list[str]:
    p = _Tds()
    p.feed(page)
    return p.cells


def _norm(s: str) -> str:
    return " ".join(s.split())


# ------------------------------------------------------------------ the listed cells


def test_the_twenty_three_listed_cells_print_in_the_t1_docx_by_the_d4_formatter(cli_run):
    doc, _, docs = cli_run
    cells = {_norm(c) for c in cell_texts(docs["T1"])}
    listed = listed_cells(doc)
    assert len(listed) == 23
    for ref, kind, facet in listed:
        found, num = resolve_pointer(doc, ref)
        assert found, ref
        text = _own_fmt(num, kind, facet)
        assert text in cells, (ref, facet, text)


def test_twenty_named_cells_have_the_same_text_in_the_docx_as_the_visible_html(cli_run):
    doc, pages, docs = cli_run
    parser = _Cells()
    parser.feed(pages["T1"])
    by_ref: dict[tuple[str, str], str] = {}
    for c in parser.cells:
        by_ref.setdefault((c["ref"], c["facet"]), c["text"])
    docx_cells = {_norm(c) for c in cell_texts(docs["T1"])}
    f = next(
        i for i, r in enumerate(doc["subgroups"]) if r["attribute"] == "sex" and r["level"] == "F"
    )
    a0 = next(
        i
        for i, r in enumerate(doc["subgroups"])
        if r["attribute"] == "age" and r["level"] == "0-40"
    )
    assert len(TWENTY_CELLS) == 20
    for ref, _kind, facet in TWENTY_CELLS:
        ref = ref.format(f=f, a0=a0)
        html_text = _norm(html_lib.unescape(by_ref[(ref, facet)]))
        assert html_text in docx_cells, (ref, facet, html_text)


def test_every_t8_criteria_cell_and_every_t7_table_cell_is_in_the_docx_as_the_html_shows_it(
    cli_run,
):
    _, pages, docs = cli_run
    for template_id in ("T7", "T8"):
        docx_cells = {_norm(c) for c in cell_texts(docs[template_id])}
        docx_paras = {_norm(p) for p in paragraph_texts(docs[template_id])}
        joined = _norm("\n".join(paragraph_texts(docs[template_id])))
        html_cells = [c for c in _html_cells(pages[template_id]) if c]
        assert len(html_cells) >= 40, template_id
        # a justification row's one HTML cell holds the label and the body; the DOCX
        # prints them as two paragraphs (PP Manufacturer Text Label, PP Manufacturer Text)
        composite = [c for c in html_cells if c.startswith("Manufacturer text - ")]
        simple = [c for c in html_cells if not c.startswith("Manufacturer text - ")]
        exact = [c for c in simple if c in docx_cells or c in docx_paras]
        assert len(exact) >= {"T7": 60, "T8": len(simple)}[template_id], (
            template_id,
            len(exact),
            len(simple),
            [c for c in simple if c not in exact][:10],
        )
        for c in composite:
            label = c[: len("Manufacturer text - ")]
            assert any(p.startswith(label) for p in docx_paras), c
        # T7's conventions pipe table is an HTML <table> and a DOCX monospace block
        # (docx_context's *_blocks): each of its cells is in the block's text
        missing = [c for c in simple if c not in joined]
        assert missing == [], (template_id, missing[:10])
    observed = re.findall(r'<td class="num observed">([^<]*)</td>', pages["T8"])
    assert len(observed) >= 9
    t8_cells = {_norm(c) for c in cell_texts(docs["T8"])}
    for cell in observed:
        assert _norm(html_lib.unescape(cell)) in t8_cells, cell


# ------------------------------------------------------------------ every decimal token


@pytest.mark.parametrize("template_id", IDS)
def test_every_decimal_token_of_the_docx_parses_back_to_run_json_at_fmts_rounding(
    cli_run, template_id
):
    doc, _, docs = cli_run
    text = "\n".join(paragraph_texts(docs[template_id]) + section_footers(docs[template_id]))
    tokens = _decimals(text)
    assert tokens
    by_number = number_explained(doc)
    by_scalar = scalar_explained(doc)
    literals = template_literals(template_id)
    orphans = sorted({t for t in tokens if t not in by_number | by_scalar | literals})
    assert orphans == [], (template_id, orphans)
    explained_by_numbers = sum(1 for t in tokens if t in by_number)
    assert explained_by_numbers >= {"T1": 400, "T7": 20, "T8": 15}[template_id], (
        template_id,
        explained_by_numbers,
        len(tokens),
    )


def test_the_decimal_scan_catches_a_planted_orphan(cli_run):
    doc, _, _ = cli_run
    by_number, by_scalar = number_explained(doc), scalar_explained(doc)
    planted = "0.12345678"
    assert planted not in by_number | by_scalar | template_literals("T8")
    assert _decimals(f"sensitivity {planted} [0.1, 0.2]") == [planted, "0.1", "0.2"]


# ------------------------------------------------------------------ furniture and marks


@pytest.mark.parametrize("template_id", IDS)
def test_the_footer_is_on_every_section_with_no_watermark_under_a_valid_licence(
    cli_run, template_id
):
    doc, _, docs = cli_run
    footers = section_footers(docs[template_id])
    assert len(footers) == len(open_docx(docs[template_id]).sections) >= 3
    head = SHORT_FORM.split("{")[0]
    for f in footers:
        assert f.startswith(head)
        assert doc["manifest"]["engine_version"] in f and doc["manifest"]["started"] in f
    assert doc["manifest"]["watermark"] is None
    assert "not for submission" not in "\n".join(footers)


def _html_body_text(page: str) -> str:
    """The page's visible text outside the per-page footers (which repeat the guidance
    list the DOCX carries in its footer parts) and outside the SVG figures (whose row
    labels the DOCX carries as pixels)."""
    skip = {"page-footer", "print-footer", "fig-text"}
    return "\n".join(t for t, scope in text_nodes(page) if not (scope & skip))


def test_unverified_markings_survive_extraction_in_the_html_count(cli_run):
    _, pages, docs = cli_run
    html_text = _html_body_text(pages["T7"])
    docx_text = "\n".join(paragraph_texts(docs["T7"]))
    assert html_text.count("[unverified]") == docx_text.count("[unverified]") >= 5
    assert html_text.count("citation pending verification") == docx_text.count(
        "citation pending verification"
    )
    # in the mono, honesty-coloured run style
    runs = styled_runs(docs["T7"])
    assert any(t == "[unverified]" and r == "PP Unverified" for t, _, r in runs)


def test_tier_superscripts_survive_extraction_in_the_html_count(cli_run):
    _, pages, docs = cli_run
    html_text = _html_body_text(pages["T1"])
    docx_text = "\n".join(paragraph_texts(docs["T1"]))
    for glyph in TIER_GLYPHS:
        assert html_text.count(glyph) == docx_text.count(glyph), glyph
    assert sum(docx_text.count(g) for g in TIER_GLYPHS) >= 20


@pytest.mark.parametrize("template_id", IDS)
def test_draft_anchor_labels_survive_in_the_html_count(cli_run, template_id):
    _, pages, docs = cli_run
    html_text = _html_body_text(pages[template_id])
    docx_text = "\n".join(paragraph_texts(docs[template_id]))
    assert html_text.count(DRAFT_LABEL) == docx_text.count(DRAFT_LABEL) >= 3, template_id
    # and the footers: one guidance list per DOCX section, the same list per HTML page
    assert all(f.count(DRAFT_LABEL) >= 1 for f in section_footers(docs[template_id]))


# ------------------------------------------------------------------ the verdict grep


@pytest.mark.parametrize("template_id", IDS)
def test_no_forbidden_word_outside_customer_text_and_status_words_only_in_pp_status(
    cli_run, template_id
):
    _, _, docs = cli_run
    forbidden = []
    status_hits = []
    for text, pstyle, rstyle in styled_runs(docs[template_id]):
        if pstyle in ("PP Manufacturer Text", "PP Manufacturer Text Label"):
            continue
        if rstyle == "PP Manufacturer Text Inline":
            continue
        ws = words(text)
        hit = ws & FORBIDDEN_ON_PAGE
        if rstyle == STATUS_RUN_STYLE:
            hit -= STATUS_TOKENS
            assert text in STATUS_WORDS.values(), text
        if hit and pstyle != "PP Disclaimer":
            forbidden.append((sorted(hit), text[:60], pstyle, rstyle))
        if ws & {"met", "assessable"} and rstyle != STATUS_RUN_STYLE:
            status_hits.append((text[:60], pstyle, rstyle))
    assert forbidden == [], forbidden
    assert status_hits == [], status_hits
    # the words the engine's own text carries at all are the long disclaimer's, in
    # PP Disclaimer paragraphs (the HTML exempts .disclaimer the same way)
    disclaimer = "\n".join(
        t for t, pstyle, _ in styled_runs(docs[template_id]) if pstyle == "PP Disclaimer"
    )
    hits = words(engine_text(docs[template_id])) & (FORBIDDEN_ON_PAGE - STATUS_TOKENS)
    assert hits <= words(disclaimer), (template_id, hits - words(disclaimer))


def test_helper_paths_exist():
    assert Path(TEMPLATES).is_dir()


# ------------------------------------------------------------------ E11 item 0 (b)

#: A paired subgroup criterion (E10's ``paired_difference_vs_prior`` on ``sex = F``) beside
#: the synthetic CRITERIA: its T1-11 cell carries E10's type note in T1.html, and at
#: a13931b the T1.docx cell did not (the A-P4 merge lens's B2).
PAIRED_SUBGROUP = {
    "id": "C_pd_sub",
    "metric": "sensitivity",
    "type": "paired_difference_vs_prior",
    "operating_point": "op1",
    "scope": {"attribute": "sex", "level": "F"},
    "statistic": "ci_lower_bound",
    "comparator": ">=",
    "value": -0.05,
    "author": "E11 item 0 (b)",
    "date": "2026-10-02",
    "justification": "a paired criterion on a subgroup cell, so T1-11 prints the type note",
}
TYPE_NOTE = "(difference against the prior version)"


@pytest.fixture(scope="module")
def paired_t1(tmp_path_factory):
    base = tmp_path_factory.mktemp("e11pd")
    mp = pytest.MonkeyPatch()
    try:
        _own_home(base, mp)
        crit = make_criteria(
            criteria=[*copy.deepcopy(CRITERIA), dict(PAIRED_SUBGROUP)], fairness=FAIRNESS
        )
        csv_path, yml = _prepare(base, cohort_with_a_thirty_row_site(), crit)
        out = base / "pack"
        argv = ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out)]
        rc = main(
            [*argv, "--offline", "--format", "json,html,docx", "--templates", "T1"],
            registry=ephemeral_registry(),
        )
        assert rc in (EXIT_OK, EXIT_WARNINGS)
        return (out / "T1.html").read_text(encoding="utf-8"), (out / "T1.docx").read_bytes()
    finally:
        mp.undo()


@pytest.mark.day11
def test_t1_criteria_cells_with_a_paired_subgroup_criterion_equal_the_html_in_the_docx(
    paired_t1,
):
    """Every T1 cell that carries a criterion id (T1-11's criterion cells and T1-17's
    criteria table) prints in T1.docx as T1.html shows it, the type note included."""
    page, docx_bytes = paired_t1
    ids = [c["id"] for c in CRITERIA] + [PAIRED_SUBGROUP["id"]]
    html_cells = [
        c
        for c in _html_cells(page)
        if any(re.search(rf"(?<!\w){re.escape(i)}(?!\w)", c) for i in ids)
    ]
    t1_11 = [c for c in html_cells if "→" in c]
    assert any(PAIRED_SUBGROUP["id"] in c and TYPE_NOTE in c for c in t1_11), t1_11
    # whitespace dropped on both sides: T1-11 joins criteria with <br> (no text node in the
    # HTML parser's cell) where the DOCX has a line break
    squash = "".join
    docx_cells = {_norm(c) for c in cell_texts(docx_bytes)}
    squashed = {squash(c.split()) for c in docx_cells}
    missing = [c for c in html_cells if squash(c.split()) not in squashed]
    assert missing == [], missing
    note_html = sum(c.count(TYPE_NOTE) for c in t1_11)
    note_docx = sum(c.count(TYPE_NOTE) for c in docx_cells if "→" in c)
    assert note_html == note_docx >= 1, (note_html, note_docx)
