"""Build the DOCX templates ``src/proofpack/templates/T1.docx``, ``T7.docx`` and ``T8.docx``
(A-P4, build day 10, lane A; D4 sections 2, 9, 10, 11 and 14; D5 section 3.5).

    python scripts/make_docx_templates.py            # writes the three files
    python scripts/make_docx_templates.py --out DIR  # writes them elsewhere (the test)

Each template is a Word document that ``docxtpl`` renders: the Jinja tags in it name the
**same context keys** the HTML templates use (``proofpack.render.t1.t1_context``,
``t7.t7_context``, ``html.t8_context``), the tables are ``{%tr for %}`` row loops, the
margin notes are two-column tables after each section heading, the footer part of every
section carries the D4 section 7.1 short disclaimer (``{{ footer }}``), the watermark
slot (``{{ watermark }}`` inside ``{%p if watermark %}``) and a PAGE field code, and the
header part carries D4 section 1.5's header line. The DOCX mirrors the HTML templates'
content, not their markup: what ``base.html``, ``_furniture.html`` and ``_criteria.html``
print, this prints, in the same order and through the same context values.

**Styles** (D5 section 3.5, over Word's default fonts): the named ``PP ...`` styles below,
each colour read from ``design/tokens.json`` through :mod:`proofpack.render.theme` at
generation time - :data:`STYLE_TOKENS` is the one map from style to token, and
``tests/test_ap4_styles.py`` reads ``styles.xml`` of each generated file and asserts every
``PP`` style's colour equals the token the HTML theme uses. Sizes are the D5 rem scale
on an 11 pt body (Word's default), computed from ``tokens.json``'s ``type.scale``. The
monospace face is the first concrete family of the token's ``type.mono`` stack.

**Determinism**: the three files are committed. ``tests/test_ap4_templates.py`` regenerates
them into a temporary directory and compares the extracted ``word/document.xml``,
``word/styles.xml``, ``word/header*.xml`` and ``word/footer*.xml`` with the committed
files', so a hand edit to a committed ``.docx`` fails.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import io
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from proofpack.render import t1 as render_t1  # noqa: E402
from proofpack.render import theme  # noqa: E402
from proofpack.render.t1 import COVER_NOTE, MODEL_CARD_NOTE, PUBLIC_SUMMARY_NOTE  # noqa: E402
from proofpack.scope import LONG_FORM_TITLE  # noqa: E402

TEMPLATES_DIR = REPO / "src" / "proofpack" / "templates"
TEMPLATE_IDS = ("T1", "T7", "T8")
#: A fixed timestamp for the template files' own docProps (the rendered document's are
#: the manifest's, set by proofpack.render.docx).
TEMPLATE_STAMP = _dt.datetime(2026, 9, 25, 0, 0, 0)
BASE_PT = 11.0
#: The D5 section 3.5 style set: name -> (type, colour token, extra token uses). Every
#: colour a style carries is a token; the test reads this map.
STYLE_TOKENS: dict[str, dict[str, str]] = {
    "PP Title": {"type": "paragraph", "color": "ink"},
    "PP Heading 1": {"type": "paragraph", "color": "ink"},
    "PP Heading 2": {"type": "paragraph", "color": "ink"},
    "PP Heading 3": {"type": "paragraph", "color": "ink"},
    "PP Body": {"type": "paragraph", "color": "ink"},
    "PP Caption": {"type": "paragraph", "color": "ink-soft"},
    "PP Table": {"type": "table", "color": "ink", "border": "line", "header_fill": "bg-soft"},
    "PP Margin Note": {"type": "paragraph", "color": "ink-soft", "border": "line"},
    "PP Margin Note Draft": {"type": "paragraph", "color": "honesty", "border": "honesty"},
    "PP Manufacturer Text": {"type": "paragraph", "color": "ink-soft", "border": "ink-faint"},
    "PP Manufacturer Text Label": {"type": "paragraph", "color": "ink-faint"},
    "PP Manufacturer Text Inline": {"type": "character", "color": "ink-soft"},
    "PP Placeholder": {
        "type": "paragraph",
        "color": "honesty",
        "border": "honesty",
        "fill": "honesty-bg",
    },
    "PP Footer": {"type": "paragraph", "color": "ink-soft"},
    "PP Header": {"type": "paragraph", "color": "ink-soft"},
    "PP Watermark": {"type": "paragraph", "color": "honesty", "fill": "honesty-bg"},
    "PP Stamp": {"type": "paragraph", "color": "honesty", "border": "honesty"},
    "PP Disclaimer": {"type": "paragraph", "color": "ink-soft"},
    "PP Narrative Footer": {"type": "paragraph", "color": "ink-soft"},
    "PP Status": {"type": "character", "color": "ink"},
    "PP Mono": {"type": "character", "color": "ink"},
    "PP Unverified": {"type": "character", "color": "honesty"},
    "PP Highlight": {"type": "character", "color": "ink", "fill": "brand-soft"},
}
TIER_LEGEND_CAPTION = (
    "Tier superscripts - ProofPack reporting convention (R2 section 3.3); annotations, "
    "never suppression"
)


# ------------------------------------------------------------------ tokens


def _hex(token: str) -> str:
    return theme.color(token).lstrip("#").upper()


def _rem(scale_key: str) -> float:
    """A ``type.scale`` value in rem (``clamp(...)`` reads as its first argument) on the
    11 pt body."""
    raw = str(theme.tokens()["type"]["scale"][scale_key])
    m = re.search(r"([\d.]+)rem", raw)
    return float(m.group(1)) * BASE_PT if m else BASE_PT


def _mono_face() -> str:
    generic = {"ui-monospace", "monospace", "system-ui", "serif", "sans-serif"}
    for part in str(theme.tokens()["type"]["mono"]).split(","):
        name = part.strip().strip('"').strip("'")
        if name and name not in generic:
            return name
    return "Consolas"


def _margins_mm() -> tuple[float, float, float]:
    """``print.page_margin`` (``top sides bottom``) in mm."""
    parts = [float(v.rstrip("m")) for v in str(theme.tokens()["print"]["page_margin"]).split()]
    return parts[0], parts[1], parts[2]


# ------------------------------------------------------------------ styles


def _border(tag: str, colour: str, val: str = "single", sz: str = "4", space: str = "6"):
    el = OxmlElement(f"w:{tag}")
    el.set(qn("w:val"), val)
    el.set(qn("w:sz"), sz)
    el.set(qn("w:space"), space)
    el.set(qn("w:color"), colour)
    return el


def _shd(fill: str):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:color"), "auto")
    el.set(qn("w:fill"), fill)
    return el


def _p_border(style: Any, colour: str, sides: tuple[str, ...], val: str = "single") -> None:
    ppr = style.element.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    for side in sides:
        pbdr.append(_border(side, colour, val=val))
    ppr.insert(0, pbdr)


def _p_shading(style: Any, fill: str) -> None:
    ppr = style.element.get_or_add_pPr()
    shd = _shd(fill)
    pbdr = ppr.find(qn("w:pBdr"))
    if pbdr is not None:
        pbdr.addnext(shd)
    else:
        ppr.insert(0, shd)


def add_styles(doc: Any) -> None:
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.size = Pt(BASE_PT)
    normal.font.color.rgb = RGBColor.from_string(_hex("ink"))
    mono = _mono_face()

    def para(name: str, size_pt: float, *, bold: bool = False, italic: bool = False) -> Any:
        st = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = normal
        st.font.size = Pt(size_pt)
        st.font.bold = bold or None
        st.font.italic = italic or None
        st.font.color.rgb = RGBColor.from_string(_hex(STYLE_TOKENS[name]["color"]))
        st.paragraph_format.space_after = Pt(4)
        return st

    def char(name: str) -> Any:
        st = styles.add_style(name, WD_STYLE_TYPE.CHARACTER)
        st.font.color.rgb = RGBColor.from_string(_hex(STYLE_TOKENS[name]["color"]))
        return st

    para("PP Title", _rem("h1"), bold=True).paragraph_format.space_after = Pt(10)
    para("PP Heading 1", _rem("h1") * 0.8, bold=True).paragraph_format.space_before = Pt(14)
    para("PP Heading 2", _rem("h2"), bold=True).paragraph_format.space_before = Pt(12)
    para("PP Heading 3", _rem("h3"), bold=True).paragraph_format.space_before = Pt(8)
    para("PP Body", _rem("body"))
    para("PP Caption", _rem("footnote"))
    st = para("PP Margin Note", _rem("footnote"))
    _p_border(st, _hex(STYLE_TOKENS["PP Margin Note"]["border"]), ("left",))
    st = para("PP Margin Note Draft", _rem("footnote"))
    _p_border(st, _hex(STYLE_TOKENS["PP Margin Note Draft"]["border"]), ("left",))
    st = para("PP Manufacturer Text", _rem("body"))
    st.paragraph_format.left_indent = Pt(10)
    _p_border(st, _hex(STYLE_TOKENS["PP Manufacturer Text"]["border"]), ("left",))
    st = para("PP Manufacturer Text Label", _rem("tag"))
    st.paragraph_format.left_indent = Pt(10)
    st.paragraph_format.space_after = Pt(0)
    st = para("PP Placeholder", _rem("body"))
    _p_border(
        st,
        _hex(STYLE_TOKENS["PP Placeholder"]["border"]),
        ("top", "left", "bottom", "right"),
        "dashed",
    )
    _p_shading(st, _hex(STYLE_TOKENS["PP Placeholder"]["fill"]))
    para("PP Footer", float(BASE_PT * 0.72))
    para("PP Header", _rem("strip"))
    st = para("PP Watermark", _rem("body"), bold=True)
    _p_shading(st, _hex(STYLE_TOKENS["PP Watermark"]["fill"]))
    st = para("PP Stamp", _rem("body"))
    _p_border(st, _hex(STYLE_TOKENS["PP Stamp"]["border"]), ("top", "left", "bottom", "right"))
    para("PP Disclaimer", _rem("footnote"))
    para("PP Narrative Footer", _rem("footnote"), italic=True)
    char("PP Status").font.bold = True
    char("PP Manufacturer Text Inline")
    st = char("PP Mono")
    st.font.name = mono
    st = char("PP Unverified")
    st.font.name = mono
    st = char("PP Highlight")
    st.font.bold = True
    rpr = st.element.get_or_add_rPr()
    rpr.append(_shd(_hex(STYLE_TOKENS["PP Highlight"]["fill"])))

    table = styles.add_style("PP Table", WD_STYLE_TYPE.TABLE)
    table.base_style = styles["Normal Table"]
    table.font.size = Pt(_rem("table"))
    table.font.color.rgb = RGBColor.from_string(_hex(STYLE_TOKENS["PP Table"]["color"]))
    tblpr = OxmlElement("w:tblPr")
    borders = OxmlElement("w:tblBorders")
    line = _hex(STYLE_TOKENS["PP Table"]["border"])
    for side in ("top", "bottom", "insideH"):
        borders.append(_border(side, line, space="0"))
    tblpr.append(borders)
    mar = OxmlElement("w:tblCellMar")
    for side, w in (("left", "80"), ("right", "80")):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), w)
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblpr.append(mar)
    table.element.append(tblpr)
    first = OxmlElement("w:tblStylePr")
    first.set(qn("w:type"), "firstRow")
    rpr = OxmlElement("w:rPr")
    rpr.append(OxmlElement("w:b"))
    first.append(rpr)
    tcpr = OxmlElement("w:tcPr")
    tcpr.append(_shd(_hex(STYLE_TOKENS["PP Table"]["header_fill"])))
    first.append(tcpr)
    table.element.append(first)


# ------------------------------------------------------------------ the builder

Runs = str | list[tuple[str, str | None]]
#: A paragraph inside a table cell: (paragraph style or None, runs); a run-less
#: ``{%p ... %}`` tag paragraph is (None, "{%p ... %}").
Para = tuple[str | None, Runs]


def _add_runs(paragraph: Any, runs: Runs) -> None:
    if isinstance(runs, str):
        paragraph.add_run(runs)
        return
    for text, style in runs:
        run = paragraph.add_run(text)
        if style:
            run.style = style


def _add_field(paragraph: Any, instr: str) -> None:
    """A field code (``PAGE``, ``NUMPAGES``) as the fldChar run sequence."""
    for kind, text in (
        ("begin", None),
        (None, instr),
        ("separate", None),
        (None, "1"),
        ("end", None),
    ):
        run = paragraph.add_run()
        if kind is not None:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
            run._r.append(el)
        elif text == instr:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = f" {instr} "
            run._r.append(el)
        else:
            run.text = text


class Builder:
    """Writes one template: sections, furniture, paragraphs, tables and tags."""

    def __init__(self, template_name: str) -> None:
        self.doc = Document()
        add_styles(self.doc)
        self.template_name = template_name
        self._section(self.doc.sections[0], landscape=False)

    # -- sections and furniture

    def _section(self, section: Any, *, landscape: bool) -> None:
        top, sides, bottom = _margins_mm()
        w, h = Mm(210), Mm(297)
        if landscape:
            section.orientation = WD_ORIENT.LANDSCAPE
            w, h = h, w
        else:
            section.orientation = WD_ORIENT.PORTRAIT
        section.page_width, section.page_height = w, h
        section.top_margin, section.bottom_margin = Mm(top), Mm(bottom)
        section.left_margin, section.right_margin = Mm(sides), Mm(sides)
        section.header_distance, section.footer_distance = Mm(8), Mm(8)
        header = section.header
        header.is_linked_to_previous = False
        hp = header.paragraphs[0]
        hp.style = "PP Header"
        _add_runs(
            hp,
            [
                ("{{ header_customer }}", "PP Manufacturer Text Inline"),
                (" · {{ header_engine }}", None),
            ],
        )
        footer = section.footer
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0]
        fp.style = "PP Footer"
        fp.add_run("{{ footer }}")
        footer.add_paragraph("{%p if watermark %}")
        footer.add_paragraph("{{ watermark }}", style="PP Watermark")
        footer.add_paragraph("{%p endif %}")
        pg = footer.add_paragraph(style="PP Footer")
        pg.add_run("Page ")
        _add_field(pg, "PAGE")
        pg.add_run(" of ")
        _add_field(pg, "NUMPAGES")
        pg.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    def new_section(self, *, landscape: bool = False) -> None:
        self._section(self.doc.add_section(WD_SECTION.NEW_PAGE), landscape=landscape)

    # -- paragraphs

    def p(self, runs: Runs, style: str = "PP Body", align: str | None = None) -> Any:
        paragraph = self.doc.add_paragraph(style=style)
        _add_runs(paragraph, runs)
        if align == "right":
            paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        return paragraph

    def tag(self, text: str) -> None:
        self.doc.add_paragraph(text)

    def title(self, text: str) -> None:
        self.p(text, "PP Title")

    def h2(self, runs: Runs) -> None:
        self.p(runs, "PP Heading 2")

    def h3(self, runs: Runs) -> None:
        self.p(runs, "PP Heading 3")

    def caption(self, runs: Runs) -> None:
        self.p(runs, "PP Caption")

    def placeholder(self, expr: str) -> None:
        self.p("{{ " + expr + " }}", "PP Placeholder")

    def no_data(self, text: str) -> None:
        self.p(text, "PP Placeholder")

    def manufacturer(self, label: Runs, body: Runs, *, mono: bool = False) -> None:
        lab = self.doc.add_paragraph(style="PP Manufacturer Text Label")
        lab.add_run("Manufacturer text - ")
        _add_runs(lab, label)
        paragraph = self.doc.add_paragraph(style="PP Manufacturer Text")
        if mono and isinstance(body, str):
            paragraph.add_run(body).style = "PP Mono"
        else:
            _add_runs(paragraph, body)

    def stamps(self) -> None:
        self.tag("{%p for mark in marks %}")
        self.p("{{ mark.text }}", "PP Stamp")
        self.tag("{%p endfor %}")

    def narrative(self, items_expr: str) -> None:
        """The claim sentences of ``items_expr`` (each a RichText ``rich``) and D4
        section 1.4's block footer."""
        self.tag("{%p if " + items_expr + " %}")
        self.tag("{%p for s in " + items_expr + " %}")
        self.p("{{r s.rich }}", "PP Body")
        self.tag("{%p endfor %}")
        self.p("{{ narrative_footer }}", "PP Narrative Footer")
        self.tag("{%p endif %}")

    def figure(self, expr: str, absent: str | None) -> None:
        """``{{ expr.image }}`` with its caption where the spec exists, else the no-data
        line (``absent``: a literal or a ``{{ }}`` expression)."""
        self.tag("{%p if " + expr + " %}")
        self.p("{{ " + expr + ".image }}", "PP Body")
        self.caption("{{ " + expr + ".title }}. {{ " + expr + ".caption }}.")
        if absent is not None:
            self.tag("{%p else %}")
            self.no_data(absent)
        self.tag("{%p endif %}")

    # -- tables

    def table(
        self,
        headers: list[Runs],
        cells: list[list[Para]],
        *,
        loop: str | None = None,
        num: tuple[int, ...] = (),
        widths_mm: tuple[float, ...] | None = None,
    ) -> Any:
        """A ``PP Table``: the header row, then ``{%tr for <loop> %}`` / the cell row /
        ``{%tr endfor %}`` (or the cell row alone when ``loop`` is None). ``cells`` holds
        one list of paragraphs per column; columns in ``num`` are right-aligned."""
        n = len(headers)
        rows = 4 if loop else 2
        t = self.doc.add_table(rows=rows, cols=n)
        t.style = self.doc.styles["PP Table"]
        header_row = t.rows[0]
        trpr = header_row._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:tblHeader"))
        for j, h in enumerate(headers):
            c = header_row.cells[j]
            c.paragraphs[0].text = ""
            _add_runs(c.paragraphs[0], h)
            if j in num:
                c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        body = t.rows[2] if loop else t.rows[1]
        if loop:
            t.rows[1].cells[0].paragraphs[0].add_run("{%tr for " + loop + " %}")
            t.rows[3].cells[0].paragraphs[0].add_run("{%tr endfor %}")
        for j, paras in enumerate(cells):
            c = body.cells[j]
            first = True
            for style, runs in paras:
                paragraph = c.paragraphs[0] if first else c.add_paragraph()
                first = False
                if style:
                    paragraph.style = style
                _add_runs(paragraph, runs)
                if j in num and style not in (None,):
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                elif j in num and not (isinstance(runs, str) and runs.startswith("{%p")):
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if widths_mm:
            for j, w in enumerate(widths_mm):
                for row in t.rows:
                    row.cells[j].width = Mm(w)
        return t

    def margin_notes(self, expr: str, *, single: bool = False) -> None:
        """D4 section 1.1's margin note as a two-column table: one row per anchor of
        ``expr`` (a list), or the one row of ``expr`` (a dict) when ``single``. A list goes
        through the ``distinct_notes`` filter (E14 item 2, as the HTML's ``notes()``
        macro): anchors that print the same label, section and eSTAR text share one row,
        whose bracket names every id it stands for (``[FDA_STAT2007_CI,
        FDA_STAT2007_INDETERMINATE]``)."""
        ref = expr if single else "ref"
        # E15: ``section`` and ``estar`` carry their own words (``section <...>`` or the
        # [unverified] gap; ``eSTAR: <...>`` or the [unverified] gap), as the HTML macro
        note = "{{ " + ref + ".label }} · {{ " + ref + ".section }} · {{ " + ref + ".estar }}"
        ids = "  [{{ " + ref + ".id }}]"
        if not single:
            ids = "  [{{ ref.id }}{% for other in ref.also %}, {{ other }}{% endfor %}]"
        cell = [
            (None, "{%p if " + ref + ".draft %}"),
            ("PP Margin Note Draft", [(note, None), (ids, "PP Mono")]),
            (None, "{%p else %}"),
            ("PP Margin Note", [(note, None), (ids, "PP Mono")]),
            (None, "{%p endif %}"),
        ]
        self.table(
            ["Guidance anchor", "maps to"],
            [[("PP Margin Note", "maps to")], cell],
            loop=None if single else "ref in " + expr + " | distinct_notes",
            widths_mm=(28.0, 146.0),
        )

    # -- output

    def bytes(self) -> bytes:
        buf = io.BytesIO()
        props = self.doc.core_properties
        props.author = "ProofPack"
        props.last_modified_by = "ProofPack"
        props.title = self.template_name
        props.created = TEMPLATE_STAMP
        props.modified = TEMPLATE_STAMP
        props.revision = 1
        self.doc.save(buf)
        return fixed_zip(strip_thumbnail(buf.getvalue()), TEMPLATE_STAMP)


THUMBNAIL = "docProps/thumbnail.jpeg"


def strip_thumbnail(data: bytes) -> bytes:
    """python-docx's default document carries a JPEG thumbnail of a blank page
    (``docProps/thumbnail.jpeg``, its package relationship and its content type): the
    part is dropped here, so neither a template nor a rendered pack carries an image of
    nothing (a rendered pack inherits its template's parts)."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            if info.filename == THUMBNAIL:
                continue
            raw = src.read(info.filename)
            if info.filename == "_rels/.rels":
                target = THUMBNAIL.encode()
                raw = re.sub(rb'<Relationship [^>]*Target="' + target + rb'"[^>]*/>', b"", raw)
            elif info.filename == "[Content_Types].xml":
                raw = re.sub(rb'<Default Extension="jpeg"[^>]*/>', b"", raw)
            dst.writestr(info, raw)
    return out.getvalue()


def fixed_zip(data: bytes, stamp: _dt.datetime) -> bytes:
    """``data`` (a zip) rewritten with every entry's mtime set to ``stamp`` and one
    compression setting, entries in their original order (the DOCX writer of
    ``proofpack.render.docx`` uses this too, with the manifest's ``started``)."""
    date_time = (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second)
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            zi = zipfile.ZipInfo(info.filename, date_time=date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0
            dst.writestr(zi, src.read(info.filename), compresslevel=6)
    return out.getvalue()


# ------------------------------------------------------------------ shared blocks


def _n(expr: str) -> Para:
    return ("PP Body", "{{ " + expr + " }}")


def _c(expr: str) -> Para:
    """A customer-text cell (D4 section 1.3 / DEC-62)."""
    return ("PP Manufacturer Text", "{{ " + expr + " }}")


def _m(expr: str) -> Para:
    return ("PP Body", [("{{ " + expr + " }}", "PP Mono")])


def _s(expr: str) -> Para:
    """A status-word cell: the three words only, in the PP Status character style."""
    return ("PP Body", [("{{ " + expr + " }}", "PP Status")])


def cover_and_stamps(b: Builder, note: str) -> None:
    b.title("{{ template_name }}")
    b.caption(note)
    b.stamps()


def long_form(b: Builder) -> None:
    b.tag("{%p for item in long_form_items %}")
    b.p(
        [("{{ loop.index }}. ", None), ("{{ item[0] }}", None), (" {{ item[1] }}", None)],
        "PP Disclaimer",
    )
    b.tag("{%p endfor %}")


def guidance_table(b: Builder, *, url: bool) -> None:
    headers: list[Runs] = ["Internal id", "Document, version or date, status", "Draft"]
    cells: list[list[Para]] = [
        [_m("ref.id")],
        [_n("ref.label")],
        [("PP Body", "{{ 'yes' if ref.draft else 'no' }}")],
    ]
    if url:
        headers.append("URL")
        cells.append([("PP Body", "{{ ref.url if ref.url else 'not recorded' }}")])
    b.table(headers, cells, loop="ref in guidance_refs")


def criteria_table(b: Builder) -> None:
    """Table T1-17 / T2-2 as ``_criteria.html`` prints it (one block, used by T1 and T8)."""
    b.caption(
        "One row per evaluated criterion, in the order the engine evaluated them (a criterion "
        "with level: * yields one row per level; rows are addressed by position, never by id, "
        "and each row's author, date and justification are those of the criteria.yaml entry it "
        "was evaluated from). Observed values print by the metric's rule of D4 section 1.2; the "
        "declared value prints with every digit run.json carries, unrounded; the compared "
        "statistic and the largest attainable lower bound, which the engine computed, print on "
        "the unit scale to three decimals. Status words are the engine's three and nothing else. "
        "The Type column is the declaration entry's type: a paired difference against the prior "
        "model version is a margin on the new-minus-prior difference, evaluated by proofpack "
        "compare, never a bound on the scope's own statistic."
    )
    op_cell: list[Para] = [
        (None, "{%p if r.operating_point_is_customer_text %}"),
        _c("r.operating_point"),
        (None, "{%p else %}"),
        _n("r.operating_point"),
        (None, "{%p endif %}"),
    ]
    b.table(
        [
            "#",
            "Id",
            "Metric",
            "Type",
            "Scope",
            "Op.",
            "Statistic",
            "Comp.",
            "Value",
            "Author · date",
            "Observed (95% CI)",
            "n",
            "Method",
            "Compared",
            "Status",
            "Reason code",
            "Attainable at n",
            "Max LB at n",
            "Detail",
        ],
        [
            [_n("r.position")],
            [("PP Manufacturer Text", [("{{ r.criterion_id }}", "PP Mono")])],
            [_n("r.metric")],
            [_n("r.type")],
            [_c("r.scope")],
            op_cell,
            [_n("r.statistic")],
            [_n("r.comparator")],
            [_n("r.value")],
            [_c("r.authored")],
            [_n("r.observed")],
            [_n("r.n")],
            [_m("r.method")],
            [_n("r.compared_value")],
            [_s("r.status_word")],
            [_m("r.reason_code")],
            [_n("r.attainable_at_n")],
            [_n("r.max_lower_bound_at_n")],
            [_m("r.detail")],
        ],
        loop="r in criteria_rows",
        num=(0, 8, 10, 11, 13, 17),
    )
    b.caption("Justification of each row, verbatim, in the order of the table:")
    b.tag("{%p for r in criteria_rows %}")
    b.manufacturer("justification of row {{ r.position }}", "{{ r.justification }}")
    b.tag("{%p endfor %}")


def flow_table(b: Builder) -> None:
    b.caption("Table T1-2 - flow of rows (D4 section 5.10)")
    b.table(["Step", "Rows"], [[_n("row[0]")], [_n("row[1]")]], loop="row in flow_rows", num=(1,))


def tier_table(b: Builder) -> None:
    b.caption(TIER_LEGEND_CAPTION)
    b.table(["Mark", "Meaning"], [[_n("row[0]")], [_n("row[1]")]], loop="row in tier_legend")


def declarations_table(b: Builder, caption: str) -> None:
    b.caption(caption)
    label: list[Para] = [
        (None, "{%p if row[2] %}"),
        ("PP Body", [("{{ row[0] }}", "PP Highlight")]),
        (None, "{%p else %}"),
        _n("row[0]"),
        (None, "{%p endif %}"),
    ]
    b.table(["Declaration", "Value"], [label, [_c("row[1]")]], loop="row in declaration_rows")


# ------------------------------------------------------------------ T8


def build_t8() -> bytes:
    b = Builder("T8 · Run manifest, declarations, scope and disclaimer")
    # page 1
    cover_and_stamps(
        b,
        "Attachment set prepared for the manufacturer's own submission or record. Not a "
        "submission. No regulator has endorsed this tool.",
    )
    b.caption("Cover block")
    b.table(
        ["Field", "Value"],
        [
            [("PP Body", "Model")],
            [
                (
                    "PP Manufacturer Text",
                    "{{ model.name }} v{{ model.version }}{% if model.prior_version is not none %}"
                    " (prior version {{ model.prior_version | fmt_text }}){% endif %}",
                )
            ],
        ],
    )
    b.table(
        ["Field", "Value"],
        [[("PP Body", "Run id")], [_m("document.manifest.run_id | fmt_text")]],
    )
    b.table(
        ["Field", "Value"],
        [
            [("PP Body", "Engine version")],
            [_n("document.manifest.engine_version | fmt_text")],
        ],
    )
    b.table(
        ["Field", "Value"],
        [
            [("PP Body", "Reference platform")],
            [
                (
                    "PP Body",
                    "{{ document.manifest.reference_platform | fmt_scalar }} "
                    "({{ document.manifest.platform | fmt_text }})",
                )
            ],
        ],
    )
    b.table(
        ["Field", "Value"],
        [[("PP Body", "Input SHA-256")], [_m("document.manifest.input_sha256 | fmt_text")]],
    )
    b.table(
        ["Field", "Value"],
        [
            [("PP Body", "Guidance versions referenced")],
            [
                (
                    "PP Body",
                    "{% for ref in cover_guidance %}{{ ref.label }}{% if not loop.last %}; "
                    "{% endif %}{% endfor %}",
                )
            ],
        ],
    )
    b.table(
        ["Field", "Value"],
        [
            [("PP Body", "Customer sections outstanding")],
            [_n("customer_sections_outstanding | length | fmt_count")],
        ],
        num=(1,),
    )
    b.h2("1. {{ long_form_title }}")
    b.margin_notes("anchor.disclaimer", single=True)
    long_form(b)
    # page 2
    b.new_section()
    b.h2("2. Run manifest")
    b.margin_notes("anchor.manifest", single=True)
    b.caption("Manifest, as recorded by the engine at run time (every field a fact about the run)")
    b.table(["Field", "Value"], [[_n("row[0]")], [_m("row[1]")]], loop="row in manifest_rows")
    b.h2("3. Declarations echo")
    b.margin_notes("anchor.declarations", single=True)
    b.p(
        "Every declaration below was written by the manufacturer in criteria.yaml; the engine "
        "infers none and supplies no default. The positive class and the score orientation are "
        "highlighted."
    )
    declarations_table(b, "Table T1-1 - declarations that shape every number in the pack")
    b.manufacturer(
        "the declarations block of run.json as YAML (keys in canonical order; the file's "
        "SHA-256 is in the manifest)",
        "{{ criteria_yaml }}",
        mono=True,
    )
    b.h2("4. Mapping report")
    b.p(
        "The confirmed mapping is not printed in this pack: its SHA-256 is in the manifest "
        "above, and the original headers and value summaries stay in the mapping.json beside "
        "the input, never in a document a customer hands over."
    )
    # page 3
    b.new_section()
    b.h2("5. HALT and warning log")
    b.tag("{%p if halts %}")
    b.tag("{%p for h in halts %}")
    b.p("{{ h | fmt_text }}")
    b.tag("{%p endfor %}")
    b.tag("{%p else %}")
    b.p("No HALT gate fired (a document is only written when none does).")
    b.tag("{%p endif %}")
    b.tag("{%p if warning_rows %}")
    b.caption("Warnings raised")
    b.table(
        ["Code", "Meaning", "Parameters"],
        [[_m("w.code")], [_n("w.text")], [_m("w.params")]],
        loop="w in warning_rows",
    )
    b.tag("{%p else %}")
    b.p("No warnings were raised.")
    b.tag("{%p endif %}")
    b.h2("5a. Acceptance criteria (Table T1-17)")
    b.margin_notes("anchor.criteria", single=True)
    b.tag("{%p if has_criteria %}")
    criteria_table(b)
    # E11 repair 3 (DEC-75 (b), lens 3 FA-N4 / RG-N1): the criteria cells print the tier
    # marks, d included; the legend follows the table that prints them
    tier_table(b)
    b.tag("{%p else %}")
    b.p("No acceptance criteria were declared; estimates and intervals only.")
    b.tag("{%p endif %}")
    b.h2("6. Ledger")
    b.margin_notes("anchor.ledger", single=True)
    b.caption("Acceptance-decision runs recorded against this test set in the local ledger")
    b.table(["Field", "Value"], [[("PP Body", "Test-set SHA-256")], [_m("ledger.test_set_sha256")]])
    b.table(
        ["Field", "Value"],
        [
            [("PP Body", "Acceptance runs recorded (including this run)")],
            [_n("ledger.acceptance_runs")],
        ],
        num=(1,),
    )
    b.table(
        ["Field", "Value"],
        [[("PP Body", "Manifest ledger count")], [_n("ledger.ledger_count")]],
        num=(1,),
    )
    b.table(
        ["Field", "Value"],
        [
            [("PP Body", "Declared limit (warn_after_acceptance_runs)")],
            [_c("ledger.declared_limit")],
        ],
        num=(1,),
    )
    b.table(
        ["Field", "Value"],
        [
            [("PP Body", "Counted")],
            [
                (
                    "PP Body",
                    "{% if ledger.counted %}yes{% else %}no (the ledger could not be read or "
                    "written; see the warning log){% endif %}",
                )
            ],
        ],
    )
    b.h2("7. Narrative integrity")
    b.margin_notes("anchor.narrative", single=True)
    b.caption("Counts computed from the document by the renderer")
    for label, key in (
        ("Claims generated", "claims_generated"),
        ("Claims rejected by the checker", "claims_rejected"),
        ("Claims substituted by the deterministic template claim", "claims_substituted"),
        ("Rows analysed", "rows_analysed"),
        ("Subgroup rows", "subgroup_rows"),
        ("Criteria rows", "criteria_rows"),
    ):
        b.table(
            ["Count", "Value"],
            [[("PP Body", label)], [_n(f"integrity.{key} | fmt_count")]],
            num=(1,),
        )
    b.tag("{%p if has_criteria %}")
    b.table(
        ["Status", "Rows"],
        [[_s("status_words[row[0]]")], [_n("row[1] | fmt_count")]],
        loop="row in integrity.criteria_by_status",
        num=(1,),
    )
    b.tag("{%p endif %}")
    for label, key in (("Suppressed cells", "suppressed_cells"), ("Warnings", "warnings")):
        b.table(
            ["Count", "Value"],
            [[("PP Body", label)], [_n(f"integrity.{key} | fmt_count")]],
            num=(1,),
        )
    b.tag("{%p if rejections %}")
    b.caption(
        "Claim rejections (each replaced by the deterministic template claim for its slot "
        "where one exists)"
    )
    b.table(
        ["Claim id", "Template", "Reason code", "Substituted"],
        [
            [_m("rj.claim_id | fmt_text")],
            [_m("rj.template_id | fmt_text")],
            [_m("rj.reason_code | fmt_text")],
            [("PP Body", "{% if rj.substituted %}yes{% else %}no{% endif %}")],
        ],
        loop="rj in rejections",
    )
    b.tag("{%p else %}")
    b.p("No claim was rejected by the checker.")
    b.tag("{%p endif %}")
    b.p("{{ narrative_footer }}", "PP Narrative Footer")
    b.h2("8. Out of scope - never performed by ProofPack")
    b.tag("{%p for item in out_of_scope %}")
    b.p("- {{ item }}")
    b.tag("{%p endfor %}")
    b.h2("9. Guidance references")
    b.caption(
        "Every anchor used in this render, labelled from the guidance map; a draft is a draft "
        "in the label and in the structured data"
    )
    guidance_table(b, url=True)
    b.h2("10. Customer sections outstanding")
    b.tag("{%p if customer_sections_outstanding %}")
    b.p(
        "The customer-text slots of the attachment set (T1) that no text filled in this build; "
        "T1 prints each as below and ProofPack drafts none of them."
    )
    b.tag("{%p for slot in customer_sections_outstanding %}")
    b.placeholder("slot.text")
    b.tag("{%p endfor %}")
    b.tag("{%p else %}")
    b.p("No customer-text slot of the attachment set is outstanding.")
    b.tag("{%p endif %}")
    b.h2("11. Data status")
    b.tag("{%p if watermark %}")
    b.stamps()
    b.p(
        "This document carries the marking above and must not be used in any regulatory "
        "record while it does."
    )
    b.tag("{%p else %}")
    b.p("No synthetic, demonstration or trial marking applies to this run.")
    b.tag("{%p endif %}")
    return b.bytes()


# ------------------------------------------------------------------ T7


def conventions(b: Builder, expr: str) -> None:
    """The conventions file's section as the DOCX prints it: one paragraph per block of
    the markdown source (``proofpack.render.docx.markdown_blocks``), tables as mono
    lines."""
    b.tag("{%p for block in " + expr + " %}")
    b.tag("{%p if block.mono %}")
    b.p([("{{ block.text }}", "PP Mono")])
    b.tag("{%p else %}")
    b.p("{{ block.text }}")
    b.tag("{%p endif %}")
    b.tag("{%p endfor %}")


def build_t7() -> bytes:
    b = Builder("T7 · Methods appendix")
    cover_and_stamps(
        b,
        "The methods this run used, read from the run document. Attachment set prepared for "
        "the manufacturer's own submission or record. Not a submission. No regulator has "
        "endorsed this tool.",
    )
    b.h2("1. Software, determinism and tolerances")
    b.margin_notes("anchor.software", single=True)
    b.caption("As recorded in the manifest of this run")
    b.table(["Field", "Value"], [[_n("row[0]")], [_m("row[1]")]], loop="row in software_rows")
    b.p("{{ tolerance_policy }}")
    b.h2("2. Data handling")
    b.margin_notes("anchor.data", single=True)
    b.p(
        [
            ("Mapping: rule-based, confirmed before the run; mapping.json SHA-256 ", None),
            ("{{ mapping_sha256 }}", "PP Mono"),
            (".", None),
        ]
    )
    b.tag("{%p if halts %}")
    b.tag("{%p for h in halts %}")
    b.p("{{ h }}")
    b.tag("{%p endfor %}")
    b.tag("{%p else %}")
    b.p("HALT gates: none fired (a document is written only when none does).")
    b.tag("{%p endif %}")
    b.p(
        'Warnings raised: {% if warning_codes %}{{ warning_codes | join(", ") }}'
        "{% else %}none{% endif %}."
    )
    flow_table(b)
    b.p(
        [
            ("Clustering: declared unit ", None),
            ("{{ clustering.declared }}", "PP Manufacturer Text Inline"),
            (
                "; clustered path used: {% if clustering.clustered %}yes{% else %}no{% endif %} "
                "(route ",
                None,
            ),
            ("{{ clustering.route }}", "PP Mono"),
            ("; {{ clustering.n_cases }} cases).", None),
        ]
    )
    b.new_section()
    b.h2("3. Methods used in this run")
    b.margin_notes("anchor.methods", single=True)
    b.caption(
        "Every interval method named by a Number in the run document, and how many Numbers "
        "carry it (read from run.json, not a list of what ProofPack can do)"
    )
    b.table(
        ["Method", "What it is", "Numbers"],
        [[_m("m.id")], [_n("m.description")], [_n("m.count")]],
        loop="m in methods",
        num=(2,),
    )
    b.tag("{%p if has_subgroups %}")
    b.h2("4. Subgroups and differences")
    b.margin_notes("anchor.subgroups", single=True)
    b.p(
        "{{ x1_sentence }} Interval methods of the difference Numbers in this run: "
        "{% for m in x1_methods %}{{ m.phrase }} ({{ m.id }}, {{ m.count }})"
        "{% if not loop.last %}; {% endif %}{% else %}none recorded{% endfor %}."
    )
    conventions(b, "subgroup_conventions_blocks")
    b.tag("{%p endif %}")
    b.h2("5. Calibration")
    b.margin_notes("anchor.calibration", single=True)
    b.tag("{%p if has_calibration %}")
    conventions(b, "calibration_conventions_blocks")
    b.tag("{%p elif calibration_reason %}")
    b.p(
        [
            ("calibration: null - reason ", None),
            ("{{ calibration_reason.reason }}", "PP Mono"),
            (
                " (score declared {{ calibration_reason.score_type }}, "
                "{{ calibration_reason.orientation }}).",
                None,
            ),
        ]
    )
    b.tag("{%p else %}")
    b.no_data("calibration: null - the run document records no reason")
    b.tag("{%p endif %}")
    b.tag("{%p if has_cluster_bootstrap %}")
    b.h2("6. Coverage of the clustered intervals")
    conventions(b, "coverage_conventions_blocks")
    b.tag("{%p endif %}")
    b.tag("{%p if fairness %}")
    b.h2("7. Fairness")
    b.caption("Gap definitions, as the engine computed them")
    b.table(
        ["Gap", "Definition"],
        [[_m("row[0]")], [_n("row[1]")]],
        loop="row in fairness.definitions",
    )
    b.p(
        [
            ("Impossibility statement: {{ fairness.citation }} ", None),
            ("[unverified]", "PP Unverified"),
            (" {{ fairness.pending }}.", None),
        ]
    )
    b.tag("{%p endif %}")
    b.new_section()
    b.h2("8. Reporting conventions")
    b.margin_notes("anchor.conventions", single=True)
    b.p("{{ conventions_sentence }}")
    conventions(b, "conventions_intro_blocks")
    tier_table(b)
    b.tag("{%p if not_run %}")
    b.p('Not part of this run: {{ not_run | join("; ") }}.')
    b.tag("{%p endif %}")
    b.h2("9. Library and reference citations")
    b.tag("{%p if citations_used %}")
    b.tag("{%p for c in citations_used %}")
    b.p(
        [
            ("- {{ c.text }}{% if c.url %} ({{ c.url }}){% endif %}", None),
            ("{% if c.mark %} {{ c.mark }}{% endif %}", "PP Unverified"),
        ]
    )
    b.tag("{%p endfor %}")
    b.tag("{%p else %}")
    b.no_data("No citation in the register names a method or block this run used.")
    b.tag("{%p endif %}")
    b.h2("10. Open verification items")
    b.tag("{%p if open_items %}")
    b.tag("{%p for c in open_items %}")
    b.p(
        [
            ("- {{ c.text }} - ", None),
            ("{{ c.mark }}", "PP Unverified"),
            (" (source: {{ c.source }})", None),
        ]
    )
    b.tag("{%p endfor %}")
    b.tag("{%p else %}")
    b.p("No open verification item is recorded in the citation register.")
    b.tag("{%p endif %}")
    return b.bytes()


# ------------------------------------------------------------------ T1


def _ncell(expr: str) -> list[Para]:
    """A Number cell: the text D4 section 1.2 prints (the same string the HTML cell
    carries)."""
    return [_n(expr + ".text")]


def build_t1() -> bytes:
    # E11 item 1: the template's own core title carries the draft qualifier too (the
    # rendered title is the header line, set from the context at render time)
    b = Builder(render_t1.template_name())
    # page 1: cover
    cover_and_stamps(b, "{{ cover_note }}")
    b.caption("Cover block")
    b.table(
        ["Field", "Value"],
        [
            [("PP Body", "Manufacturer")],
            [
                (None, '{%p if slots["CT-01"].filled %}'),
                ("PP Manufacturer Text Label", "Manufacturer text - manufacturer"),
                ("PP Manufacturer Text", '{{ slots["CT-01"].text }}'),
                (None, "{%p else %}"),
                ("PP Placeholder", '{{ slots["CT-01"].text }}'),
                (None, "{%p endif %}"),
            ],
        ],
    )
    b.table(
        ["Field", "Value"],
        [
            [("PP Body", "Model")],
            [("PP Manufacturer Text", "{{ model.name }} v{{ model.version }}")],
        ],
    )
    b.table(
        ["Field", "Value"],
        [
            [_n("row[0]")],
            [
                (None, "{%p if row[2] %}"),
                _m("row[1]"),
                (None, "{%p else %}"),
                _n("row[1]"),
                (None, "{%p endif %}"),
            ],
        ],
        loop="row in cover_rows",
    )
    b.table(
        ["Field", "Value"],
        [
            [("PP Body", "Guidance versions referenced")],
            [
                (
                    "PP Body",
                    "{% for ref in cover_guidance %}{{ ref.label }}{% if not loop.last %}; "
                    "{% endif %}{% endfor %}",
                )
            ],
        ],
    )
    b.table(
        ["Field", "Value"],
        [[("PP Body", "Customer sections outstanding")], [_n("outstanding")]],
        num=(1,),
    )
    b.h2("Device and intended use")
    b.placeholder('slots["CT-02"].text')
    # page 2: scope and limits
    b.new_section()
    b.h2("{{ long_form_title }}")
    long_form(b)
    b.caption(
        "Guidance versions referenced in this render, labelled from the guidance map; a draft "
        "is a draft in the label and in the structured data"
    )
    guidance_table(b, url=False)
    # page 3: sections 1-3
    b.new_section()
    b.h2("1. Scope and declarations summary")
    b.margin_notes("anchors.s1")
    declarations_table(
        b,
        "Table T1-1 - declarations that shape every number in the pack (all from "
        "criteria.yaml; the engine supplies no default)",
    )
    b.h2("2. Data management - dataset description")
    b.margin_notes("anchors.s2")
    b.placeholder('slots["CT-03"].text')
    flow_table(b)
    b.caption("Table T1-3 - Table 1 of the test set{% if dev_note %}; {{ dev_note }}{% endif %}")
    b.table(
        ["Attribute", "Level", "Test n (%)"],
        [[_c("r.attribute")], [_c("r.level")], [("PP Body", "{{ r.n }} ({{ r.pct }})")]],
        loop="r in table1_rows",
        num=(2,),
    )
    b.h2("3. Test-set independence and sequestration")
    b.margin_notes("anchors.s3")
    b.placeholder('slots["CT-04"].text')
    b.tag("{%p if overlap_note %}")
    b.no_data("{{ overlap_note }}")
    b.tag("{%p endif %}")
    # page 4: sections 4-6
    b.new_section()
    b.h2("4. Site diversity")
    b.margin_notes("anchors.s4")
    b.placeholder('slots["CT-05"].text')
    b.tag("{%p if site_block %}")
    b.p("Table T1-5 is the site table of section 9 (per site, D4 section 5.3 format).")
    b.tag("{%p else %}")
    b.no_data("No site attribute was supplied: per-site performance is not reported.")
    b.tag("{%p endif %}")
    b.h2("5. Representativeness")
    b.margin_notes("anchors.s5")
    b.placeholder('slots["CT-06"].text')
    b.p(
        "The distribution of each attribute in the test set is Table T1-3 (section 2); the "
        "adequacy of that distribution for the intended use is the manufacturer's judgement."
    )
    b.h2("6. Reference standard")
    b.margin_notes("anchors.s6")
    b.manufacturer(
        "reference standard as declared",
        "{{ reference_standard.type }} ({{ reference_standard.description }})",
    )
    b.placeholder('slots["CT-07"].text')
    # page 5: section 7
    b.new_section()
    b.h2("7. Performance validation - overall, per operating point")
    b.margin_notes("anchors.s7")
    b.placeholder('slots["CT-08"].text')
    b.tag("{%p for p in performance %}")
    b.h3([("Operating point ", None), ("{{ p.op }}", "PP Manufacturer Text Inline")])
    b.caption(
        [
            ("Table T1-6 - two-by-two at operating point ", None),
            ("{{ p.op }}", "PP Manufacturer Text Inline"),
            (" (threshold ", None),
            ("{{ p.threshold }}", "PP Manufacturer Text Inline"),
            (", rule {{ p.rule }}); totals are the denominators of the Numbers below", None),
        ]
    )
    b.table(
        ["", "Device positive", "Device negative", "Total"],
        [
            [_n("p.two_by_two.row_pos")],
            [_n("p.two_by_two.tp")],
            [_n("p.two_by_two.fn")],
            [_n("p.two_by_two.n_pos")],
        ],
        num=(1, 2, 3),
    )
    b.table(
        ["", "Device positive", "Device negative", "Total"],
        [
            [_n("p.two_by_two.row_neg")],
            [_n("p.two_by_two.fp")],
            [_n("p.two_by_two.tn")],
            [_n("p.two_by_two.n_neg")],
        ],
        num=(1, 2, 3),
    )
    b.table(
        ["", "Device positive", "Device negative", "Total"],
        [
            [("PP Body", "Total")],
            [_n("p.two_by_two.d_pos")],
            [_n("p.two_by_two.d_neg")],
            [_n("p.two_by_two.total")],
        ],
        num=(1, 2, 3),
    )
    b.tag("{%p if p.indeterminate_both_ways %}")
    b.no_data(
        "Indeterminate results allocated both ways (FDA 2007): the allocation tables are not "
        "computed in this build."
    )
    b.tag("{%p endif %}")
    b.caption(
        [
            ("Table T1-7 - operating-point metrics at ", None),
            ("{{ p.op }}", "PP Manufacturer Text Inline"),
            (
                "; the threshold was {{ p.provenance }}. Wilson score without continuity "
                "correction for proportions unless the Method column says otherwise",
                None,
            ),
        ]
    )
    b.table(
        ["Metric", "k/n", "Estimate (% for proportions)", "95% CI", "Method"],
        [
            [("PP Body", "{{ r.label }}{% if r.supplementary %} (supplementary){% endif %}")],
            _ncell("r.kn"),
            _ncell("r.est"),
            _ncell("r.ci"),
            [_m("r.method.text")],
        ],
        loop="r in p.rows",
        num=(1, 2, 3),
    )
    b.tag("{%p if p.prev_rows %}")
    b.caption("Predictive values at the declared intended-use prevalence (Table T1-7, continued)")
    b.table(
        ["Metric", "k/n", "Estimate (%)", "95% CI", "Method"],
        [
            [_c("r.label")],
            [("PP Body", "—")],
            _ncell("r.est"),
            _ncell("r.ci"),
            [_m("r.method.text")],
        ],
        loop="r in p.prev_rows",
        num=(1, 2, 3),
    )
    b.tag("{%p endif %}")
    b.narrative("p.sentences")
    b.tag("{%p endfor %}")
    b.caption("Table T1-8 - threshold-free performance (AUROC, AUPRC, prevalence)")
    b.table(
        ["Quantity", "Estimate [95% CI]", "Method"],
        [[_n("r.label")], _ncell("r.cell"), [_m("r.method.text")]],
        loop="r in threshold_free",
        num=(1,),
    )
    b.narrative("auroc_sentences")
    b.figure("figures.f2", "F2 (ROC) is not drawn: the run document carries no ROC array.")
    b.figure("figures.f3", "{{ figures.f3_note }}")
    # page 6: section 8
    b.new_section()
    b.h2("8. Calibration")
    b.margin_notes("anchors.s8")
    b.placeholder('slots["CT-09"].text')
    b.tag("{%p if calibration.present %}")
    b.caption(
        "Table T1-9 - calibration of the declared probability score (D4 section 5.5)"
        "{% if calibration.curve_note %}; {{ calibration.curve_note }}{% endif %}"
    )
    b.table(
        ["Quantity", "Estimate [95% CI]", "Method"],
        [[_n("r.label")], _ncell("r.cell"), [_m("r.method.text")]],
        loop="r in calibration.rows",
        num=(1,),
    )
    b.tag("{%p if calibration.ipa_tiers or calibration.clustered %}")
    b.p(
        "{% if calibration.ipa_tiers %}The IPA row's tier superscript ({{ calibration.ipa_tiers "
        "}}) is the proportion tier applied to the IPA's own interval: it states the half-width "
        "on the IPA's scale and nothing about a proportion (ProofPack reporting convention; T7, "
        "DEC-35).{% endif %}{% if calibration.ipa_tiers and calibration.clustered %} {% endif %}"
        "{% if calibration.clustered %}Under the clustered plan every interval above is a "
        "cluster-bootstrap interval and carries the mark ᵈ (coverage not established for its "
        "case sizes; legend in section 9); each cell keeps its tier annotation and the measured "
        "coverage of the route, including the one cell below the bar, is in T7 (DEC-18 (c), "
        "DEC-34).{% endif %}",
        "PP Caption",
    )
    b.tag("{%p endif %}")
    b.caption("Decile table - ten equal-mass bins by score; observed k/n (%) with its interval")
    b.table(
        ["Decile", "n", "Mean predicted", "Observed k/n (%) [95% CI]"],
        [[_n("d.bin")], [_n("d.n")], [_n("d.mean_pred")], _ncell("d.observed")],
        loop="d in calibration.deciles",
        num=(0, 1, 2, 3),
    )
    b.figure("figures.f4", None)
    b.tag("{%p elif calibration.reason %}")
    b.p(
        [
            ("calibration: null - reason ", None),
            ("{{ calibration.reason.reason }}", "PP Mono"),
            (
                " (score declared {{ calibration.reason.score_type }}, "
                "{{ calibration.reason.orientation }}).",
                None,
            ),
        ]
    )
    b.tag("{%p if figures.f4_note %}")
    b.no_data("{{ figures.f4_note }}")
    b.tag("{%p endif %}")
    b.tag("{%p else %}")
    b.no_data("calibration: null - the run document records no reason")
    b.tag("{%p if figures.f4_note %}")
    b.no_data("{{ figures.f4_note }}")
    b.tag("{%p endif %}")
    b.tag("{%p endif %}")
    b.narrative("calibration.sentences")
    # page 7: section 9 (landscape)
    b.new_section(landscape=True)
    b.h2("9. Subgroup performance")
    b.margin_notes("anchors.s9")
    b.tag('{%p if slots["CT-10"].filled %}')
    b.manufacturer(
        "pre-specification source of each subgroup attribute (criteria.yaml)",
        '{{ slots["CT-10"].text }}',
    )
    b.tag("{%p else %}")
    b.placeholder('slots["CT-10"].text')
    b.tag("{%p endif %}")
    b.tag("{%p for s in subgroups %}")
    b.h3([("Attribute ", None), ("{{ s.attribute }}", "PP Manufacturer Text Inline")])
    b.tag("{%p for o in s.ops %}")
    b.caption(
        [
            ("Table T1-10 - performance by ", None),
            ("{{ s.attribute }}", "PP Manufacturer Text Inline"),
            (" at operating point ", None),
            ("{{ o.op }}", "PP Manufacturer Text Inline"),
            ("; reference level ", None),
            ("{{ s.reference_level }}", "PP Manufacturer Text Inline"),
            (
                " (rule {{ s.reference_rule }}); {% if s.prespecified %}pre-specified{% else %}"
                "not pre-specified, exploratory{% endif %}. Interval methods in this table: "
                "{{ o.table_methods }}; tiers are ProofPack reporting conventions",
                None,
            ),
        ]
    )
    b.table(
        [
            "Group",
            "n",
            "Events",
            "{{ se_label }} k/n (%) [95% CI]",
            "{{ sp_label }} k/n (%) [95% CI]",
            "AUROC [95% CI]",
            "Pre-spec.",
            "Tier",
        ],
        [
            [("PP Manufacturer Text", "{{ r.level }}{% if r.is_reference %} (ref){% endif %}")],
            [_n("r.n")],
            [_n("r.events")],
            _ncell("r.se"),
            _ncell("r.sp"),
            _ncell("r.auroc"),
            [_n("r.prespecified")],
            [_n("r.tier")],
        ],
        loop="r in o.table",
        num=(1, 2, 3, 4, 5),
    )
    b.table(
        [
            "Group",
            "n",
            "Events",
            "{{ se_label }} k/n (%) [95% CI]",
            "{{ sp_label }} k/n (%) [95% CI]",
            "AUROC [95% CI]",
            "Pre-spec.",
            "Tier",
        ],
        [
            [("PP Body", "Overall")],
            [_n("o.overall.n")],
            [_n("o.overall.events")],
            _ncell("o.overall.se"),
            _ncell("o.overall.sp"),
            _ncell("o.overall.auroc"),
            [("PP Body", "—")],
            [("PP Body", "")],
        ],
        num=(1, 2, 3, 4, 5),
    )
    b.tag("{%p if o.diffs %}")
    b.caption(
        [
            ("Table T1-11 - differences against the reference level ", None),
            ("{{ s.reference_level }}", "PP Manufacturer Text Inline"),
            (
                " (proportions in percentage points; interval methods in this table: "
                "{{ o.diff_methods }}; differences only, from which no statement about "
                "subgroup consistency is drawn)",
                None,
            ),
        ]
    )
    crit_cell: list[Para] = [
        (
            "PP Body",
            [
                ("{% for c in d.criteria %}", None),
                ("{{ c.id }}", "PP Manufacturer Text Inline"),
                (" (row {{ c.position }}) → ", None),
                ("{{ c.status_word }}", "PP Status"),
                # E11 item 0 (b) (the A-P4 merge lens, B2): E10's type note after the status,
                # outside PP Status, as T1.html prints it outside .status
                (
                    "{{ c.type_note }}"
                    "; max LB {{ c.max_lb }} at n = {{ c.n }}, attainable: {{ c.attainable }}"
                    "{% if not loop.last %}\n{% endif %}{% endfor %}",
                    None,
                ),
            ],
        )
    ]
    b.table(
        [
            "Group",
            "Δ {{ se_label }} (pp) [95% CI]",
            "Δ {{ sp_label }} (pp) [95% CI]",
            "Δ AUROC [95% CI]",
            "Criterion (id) and status; max lower bound at n",
        ],
        [[_c("d.level")], _ncell("d.se"), _ncell("d.sp"), _ncell("d.auroc"), crit_cell],
        loop="d in o.diffs",
        num=(1, 2, 3),
    )
    b.tag("{%p endif %}")
    b.tag("{%p if o.tests %}")
    b.p(
        'Exploratory test of homogeneity ({{ o.route or "none" }} route): {% for t in o.tests %}'
        "{{ t.metric }} {{ t.test }} p = {{ t.p_raw }} (Holm {{ t.p_holm }})"
        "{% if t.reason %} [{{ t.reason }}]{% endif %}{% if not loop.last %}; {% endif %}"
        "{% endfor %}; {{ o.sentence }}.",
        "PP Caption",
    )
    b.tag("{%p endif %}")
    b.tag("{%p endfor %}")
    b.tag("{%p for f in figures.f5.get(s.attribute, []) %}")
    b.figure("f", None)
    b.tag("{%p endfor %}")
    b.narrative("s.sentences")
    b.tag("{%p else %}")
    b.no_data("No subgroup attribute was tabulated in this run.")
    b.tag("{%p endfor %}")
    b.no_data(
        "Intersectional subgroups (sex x age, race x site) are not computed in this release (v1.1)."
    )
    tier_table(b)
    # page 8: sections 10-12
    b.new_section()
    b.h2("10. Fairness (descriptive)")
    b.margin_notes("anchors.s10")
    b.tag("{%p if fairness %}")
    b.manufacturer(
        "fairness declaration ({{ fairness.author }}, {{ fairness.date }})",
        "criterion of interest {{ fairness.criterion_of_interest }} on {{ fairness.attribute }}; "
        "{{ fairness.justification }}",
    )
    b.caption(
        [
            ("Table T1-13 - gaps of each level against the reference level ", None),
            ("{{ fairness.reference_level }}", "PP Manufacturer Text Inline"),
            (
                " (percentage points; AUROC on its own scale). The declared criterion of "
                "interest is the manufacturer's; every other gap is descriptive and not a "
                "target; the selection-rate gap is descriptive only",
                None,
            ),
        ]
    )
    b.table(
        [
            "Level",
            "Op.",
            "Δ TPR [95% CI]",
            "Δ FPR [95% CI]",
            "Δ PPV [95% CI]",
            "Δ NPV [95% CI]",
            "Δ AUROC [95% CI]",
            "Selection-rate gap (descriptive)",
            "Calibration by group",
        ],
        [
            [_c("g.level")],
            [_c("g.op")],
            _ncell("g.tpr"),
            _ncell("g.fpr"),
            _ncell("g.ppv"),
            _ncell("g.npv"),
            _ncell("g.auroc"),
            _ncell("g.selection"),
            [_m('g.calibration_reason or "—"')],
        ],
        loop="g in fairness.gaps",
        num=(2, 3, 4, 5, 6, 7),
    )
    b.p(
        [
            ("Impossibility statement: {{ fairness.citation }} ", None),
            ("[unverified]", "PP Unverified"),
            (" citation pending verification (T7).", None),
        ],
        "PP Caption",
    )
    b.narrative("fairness.sentences")
    b.tag("{%p else %}")
    b.no_data("No fairness criterion of interest was declared: no fairness block was computed.")
    b.tag("{%p endif %}")
    b.h2("11. Robustness")
    b.margin_notes("anchors.s11")
    b.no_data(
        "Robustness analyses (leave-one-site-out, threshold sensitivity, missingness) are not "
        "computed in this build (v1.1): the run document carries no robustness block."
    )
    b.h2("12. Acceptance criteria")
    b.margin_notes("anchors.s12")
    b.tag("{%p if has_criteria %}")
    criteria_table(b)
    b.narrative("criterion_sentences")
    b.tag("{%p else %}")
    b.p("No acceptance criteria were declared; estimates and intervals only.")
    b.tag("{%p endif %}")
    # page 9: sections 13-15
    b.new_section()
    b.h2("13. Performance monitoring")
    b.margin_notes("anchors.s13")
    b.placeholder('slots["CT-11"].text')
    b.no_data(
        "Monitoring analyses are produced by T3, which is v1.1; they are not part of this "
        "attachment set."
    )
    b.h2("14. Inputs for the public submission summary")
    b.margin_notes("anchors.s14")
    b.p("Supplement only: {{ public_summary_note }}.")
    b.caption("Table T1-18 - plain-language numbers (the same Numbers as Tables T1-7 and T1-8)")
    b.table(
        ["Metric", "Estimate", "95% CI", "n"],
        [[_n("r.metric")], _ncell("r.est"), _ncell("r.ci"), [_n("r.n")]],
        loop="r in public_summary",
        num=(1, 2, 3),
    )
    b.h2("15. Model card")
    b.margin_notes("anchors.s15")
    b.p("Note: {{ model_card_note }}.")
    b.no_data(
        "The optional model card is not produced in this release; it is scheduled for "
        "ProofPack v1.1."
    )
    b.h2("Appendices")
    b.p(
        "Appendix A, the methods appendix, is T7; appendix B, the run manifest, declarations, "
        "scope and disclaimer, is T8. Both are written beside this document from the same "
        "run.json."
    )
    return b.bytes()


BUILDERS = {"T1": build_t1, "T7": build_t7, "T8": build_t8}
#: The three literals the T1 template repeats from proofpack.render.t1 (checked here so
#: a change to the constants fails the regeneration test rather than drifting).
_T1_LITERALS = (COVER_NOTE, PUBLIC_SUMMARY_NOTE, MODEL_CARD_NOTE, LONG_FORM_TITLE)


def write_templates(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for tid in TEMPLATE_IDS:
        path = out_dir / f"{tid}.docx"
        path.write_bytes(BUILDERS[tid]())
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--out", default=str(TEMPLATES_DIR))
    args = ap.parse_args(argv)
    for path in write_templates(Path(args.out)):
        print(f"{path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
