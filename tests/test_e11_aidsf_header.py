"""Build day 11 (E11) item 1, DEC-71 (a): the T1 page's title line names the AI-DSF draft
with the qualifier every other mention carries, read from the guidance map row, in the line
itself.

* :func:`test_t1_title_line_carries_the_draft_qualifier_read_from_the_map_row` - the ``<h1>``
  of T1 (and the T1.docx title paragraph, the same context key) reads ``T1 · FDA AI-DSF
  performance evidence attachment set, per draft guidance (January 2025), not for
  implementation``; with the map row's ``version_date`` moved the month follows the row; a
  map row whose status drops ``not for implementation`` refuses the render. At ``ad66073``
  the line was ``T1 · FDA AI-DSF performance evidence attachment set``.
* :func:`test_no_rendered_template_names_the_ai_dsf_draft_without_its_qualifier` - the grep
  the item asks for, by element: every innermost HTML element (and every DOCX paragraph,
  header and footer paragraph and the core title) whose text names the AI-DSF draft (``AI-DSF``
  or its title, ``Artificial Intelligence-Enabled Device Software Functions: Lifecycle``)
  also carries ``not for implementation``. Pages: the five committed goldens (T1, T2, T7, T8,
  T12; each golden test asserts the live render equals the file) and a live T1 render;
  DOCX: T1, T7 and T8 of the synthetic document when the ``[docx]`` extra is installed.
  The PCCP guidance's title also contains ``Artificial Intelligence-Enabled Device Software
  Functions``; it is a final guidance and is not matched (the pattern needs ``: Lifecycle``).
  Internal ids such as ``FDA_AIDSF_SUBGROUP_PERF`` are identifiers, not the name, and are
  not matched.
"""

from __future__ import annotations

import copy
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from proofpack.render import anchors
from proofpack.render import t1 as render_t1
from proofpack.render.docx import extra_available
from proofpack.resources import load_guidance_map

pytestmark = pytest.mark.day11

REPO = Path(__file__).resolve().parent.parent
GOLDENS = REPO / "tests" / "fixtures" / "golden"
QUALIFIER = "not for implementation"
NAME = re.compile(r"AI-DSF|Artificial Intelligence-Enabled Device Software Functions:\s+Lifecycle")
EXPECTED_TITLE = (
    "T1 · FDA AI-DSF performance evidence attachment set, per draft guidance "
    "(January 2025), not for implementation"
)
VOID = {"br", "hr", "img", "meta", "link", "input", "col", "wbr", "source"}


class _Elements(HTMLParser):
    """``(tag, text, child_named)`` for every closed element: its full visible text and
    whether a child element's text already named the draft."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[list] = []
        self.closed: list[tuple[str, str, bool]] = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        self.stack.append([tag, [], False])

    def handle_data(self, data):
        for frame in self.stack:
            frame[1].append(data)

    def handle_endtag(self, tag):
        if tag in VOID or not self.stack:
            return
        while self.stack:
            t, buf, child_named = self.stack.pop()
            text = " ".join("".join(buf).split())
            named = bool(NAME.search(text))
            self.closed.append((t, text, child_named))
            if self.stack and named:
                self.stack[-1][2] = True
            if t == tag:
                break


def unqualified_elements(page: str) -> list[tuple[str, str]]:
    p = _Elements()
    p.feed(page)
    return [
        (tag, text[:160])
        for tag, text, child_named in p.closed
        if NAME.search(text) and not child_named and QUALIFIER not in text
    ]


def _h1(page: str) -> str:
    m = re.search(r"<h1>(.*?)</h1>", page, re.S)
    assert m, "no h1"
    return " ".join(m.group(1).split())


@pytest.fixture(scope="module")
def synthetic():
    from ap4_docx import synthetic_document

    return synthetic_document()


def test_t1_title_line_carries_the_draft_qualifier_read_from_the_map_row(synthetic):
    import html as html_lib

    page = render_t1.render_t1(synthetic)
    assert html_lib.unescape(_h1(page)) == EXPECTED_TITLE
    assert render_t1.template_name() == EXPECTED_TITLE
    # the month is the row's, not typed in t1.py
    rows = [dict(r) for r in load_guidance_map()]
    for r in rows:
        if r["internal_id"] == render_t1.T1_TITLE_ANCHOR:
            r["version_date"] = "2025-02-03"
    moved = render_t1.render_t1(synthetic, guidance_map=rows)
    assert html_lib.unescape(_h1(moved)).endswith(
        ", per draft guidance (February 2025), not for implementation"
    )
    # a draft row without the qualifier refuses the render (never an unqualified title)
    bare = copy.deepcopy(rows)
    for r in bare:
        if r["internal_id"] == render_t1.T1_TITLE_ANCHOR:
            r["status"] = "draft"
    with pytest.raises(anchors.AnchorError):
        render_t1.template_name(bare)


def test_the_element_scan_catches_the_ad66073_title():
    old = "<h1>T1 · FDA AI-DSF performance evidence attachment set</h1>"
    assert unqualified_elements(f"<html><body>{old}</body></html>") == [
        ("h1", "T1 · FDA AI-DSF performance evidence attachment set")
    ]
    ok = f"<html><body><h1>{EXPECTED_TITLE}</h1></body></html>"
    assert unqualified_elements(ok) == []


@pytest.mark.parametrize("name", ["T1", "T2", "T7", "T8", "T12"])
def test_no_rendered_template_names_the_ai_dsf_draft_without_its_qualifier(name, synthetic):
    page = (GOLDENS / f"{name}.html").read_text(encoding="utf-8")
    assert unqualified_elements(page) == []
    if name == "T1":
        live = render_t1.render_t1(synthetic)
        assert len(NAME.findall(live)) >= 1
        assert unqualified_elements(live) == []


@pytest.mark.skipif(not extra_available(), reason="the [docx] extra is not installed")
@pytest.mark.parametrize("template_id", ["T1", "T7", "T8"])
def test_no_docx_paragraph_names_the_ai_dsf_draft_without_its_qualifier(template_id, synthetic):
    from ap4_docx import open_docx, paragraph_texts, section_footers, section_headers
    from proofpack.render.docx import render_docx_bytes

    data = render_docx_bytes(synthetic, template_id)
    texts = paragraph_texts(data) + section_headers(data) + section_footers(data)
    texts.append(str(open_docx(data).core_properties.title))
    named = [t for t in texts if NAME.search(t)]
    bad = [t[:160] for t in named if QUALIFIER not in t]
    assert bad == []
    if template_id == "T1":
        assert EXPECTED_TITLE in texts
