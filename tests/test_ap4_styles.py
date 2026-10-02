"""A-P4 item 7 (build day 10, lane A): STYLES = THEME (D5 sections 3.5 and 4).

``word/styles.xml`` of each committed template, and of each freshly generated one, is read
and every ``PP`` style's colour (``w:color``), border colour (``w:pBdr``/``w:tblBorders``)
and shading (``w:shd w:fill``) is asserted equal to the ``design/tokens.json`` value the
HTML theme uses for the same token - :func:`proofpack.render.theme.color`, which is also
what ``css_variables()`` inlines as ``--pp-color-<token>`` into every HTML page - through
the generator's one style-to-token map ``STYLE_TOKENS``. The ``PP Table`` header row's
shading equals ``bg-soft`` (``th { background: var(--pp-color-bg-soft) }`` in
``base.html``). D5 section 3.5's named list is covered.
"""

from __future__ import annotations

import re

import pytest

from ap4_docx import TEMPLATES, load_generator, needs_extra, part
from proofpack.render import theme

pytestmark = [pytest.mark.day10, pytest.mark.ap4, needs_extra]

IDS = ("T1", "T7", "T8")
#: D5 section 3.5's list, verbatim (PP Heading 1-3 expanded).
D5_STYLES = (
    "PP Title",
    "PP Heading 1",
    "PP Heading 2",
    "PP Heading 3",
    "PP Body",
    "PP Table",
    "PP Caption",
    "PP Margin Note",
    "PP Manufacturer Text",
    "PP Placeholder",
    "PP Footer",
)


def _hex(token: str) -> str:
    return theme.color(token).lstrip("#").upper()


def _styles(xml: str) -> dict[str, str]:
    """``{style name: its <w:style> element}`` for the PP styles."""
    out = {}
    for m in re.finditer(r"<w:style\b.*?</w:style>", xml, re.S):
        name = re.search(r'<w:name w:val="([^"]+)"', m.group(0))
        if name and name.group(1).startswith("PP "):
            out[name.group(1)] = m.group(0)
    return out


@pytest.fixture(scope="module")
def generator():
    return load_generator()


@pytest.fixture(scope="module")
def sources(generator, tmp_path_factory) -> dict[str, str]:
    """``styles.xml`` of each committed template and of each regenerated one."""
    out = {}
    fresh = tmp_path_factory.mktemp("styles")
    for p in generator.write_templates(fresh):
        out[f"fresh:{p.stem}"] = part(p.read_bytes(), "word/styles.xml")
    for template_id in IDS:
        out[f"committed:{template_id}"] = part(
            (TEMPLATES / f"{template_id}.docx").read_bytes(), "word/styles.xml"
        )
    return out


def test_d5s_named_styles_are_all_in_the_generators_map(generator):
    assert set(D5_STYLES) <= set(generator.STYLE_TOKENS)
    for name, spec in generator.STYLE_TOKENS.items():
        assert spec["type"] in ("paragraph", "character", "table"), name
        assert f"--pp-color-{spec['color']}" in theme.css_variables(), (name, spec["color"])


@pytest.mark.parametrize("source", [f"{k}:{i}" for k in ("committed", "fresh") for i in IDS])
def test_every_pp_style_colour_border_and_fill_equals_the_theme_token(generator, sources, source):
    styles = _styles(sources[source])
    assert set(styles) == set(generator.STYLE_TOKENS), source
    for name, spec in generator.STYLE_TOKENS.items():
        xml = styles[name]
        colours = re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', xml)
        assert colours == [_hex(spec["color"])], (source, name, colours)
        if "border" in spec:
            borders = set(re.findall(r'w:color="([0-9A-Fa-f]{6})"', xml))
            assert borders == {_hex(spec["border"])}, (source, name, borders)
        fills = set(re.findall(r'<w:shd [^>]*w:fill="([0-9A-Fa-f]{6})"', xml))
        expected = {_hex(spec[k]) for k in ("fill", "header_fill") if k in spec}
        assert fills == expected, (source, name, fills)
        # every colour literal in the style is one of the tokens: nothing typed
        typed = set(re.findall(r'="([0-9A-Fa-f]{6})"', xml))
        allowed = {_hex(spec[k]) for k in ("color", "border", "fill", "header_fill") if k in spec}
        assert typed <= allowed, (source, name, typed - allowed)


@pytest.mark.parametrize("source", [f"{k}:{i}" for k in ("committed", "fresh") for i in IDS])
def test_the_table_header_row_shading_is_bg_soft_and_the_rules_are_line(sources, source):
    table = _styles(sources[source])["PP Table"]
    first_row = re.search(r'<w:tblStylePr w:type="firstRow">.*?</w:tblStylePr>', table, re.S)
    assert first_row, source
    assert re.search(r'<w:shd [^>]*w:fill="([0-9A-Fa-f]{6})"', first_row.group(0)).group(1) == _hex(
        "bg-soft"
    )
    assert "<w:b/>" in first_row.group(0)
    borders = re.search(r"<w:tblBorders>.*?</w:tblBorders>", table, re.S).group(0)
    assert set(re.findall(r'w:color="([0-9A-Fa-f]{6})"', borders)) == {_hex("line")}
    assert {"top", "bottom", "insideH"} == set(re.findall(r"<w:(\w+) w:val=", borders))


def test_the_normal_style_is_ink_and_the_theme_values_are_the_html_pages(sources):
    for source, xml in sources.items():
        normal = re.search(r'<w:style [^>]*w:styleId="Normal".*?</w:style>', xml, re.S).group(0)
        assert re.search(r'<w:color w:val="([0-9A-Fa-f]{6})"', normal).group(1) == _hex("ink"), (
            source
        )
    # theme.color is what the HTML inlines: the same hex, lower case, with the hash
    css = theme.css_root_block()
    for token in ("ink", "ink-soft", "ink-faint", "line", "bg-soft", "honesty", "honesty-bg"):
        assert f"--pp-color-{token}: {theme.color(token)};" in css


def test_a_planted_typed_colour_in_a_style_fails_the_comparison(generator, sources):
    xml = sources["committed:T8"].replace(_hex("ink-soft"), "000000")
    styles = _styles(xml)
    caption = styles["PP Caption"]
    assert re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', caption) != [
        _hex(generator.STYLE_TOKENS["PP Caption"]["color"])
    ]
