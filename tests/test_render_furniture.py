"""Build day 9 (E9 item 4): the D5 section 3.5 furniture on T1, T7 and T8.

* the cover stamp prints each mark the manifest carries - the licence mark and the data
  mark - as the engine's own constants spell them, imported here from
  ``proofpack.licence.verify`` and ``proofpack.scope`` (never retyped in a test or a
  template), and the same words ride in every page footer;
* the section margin note carries D4 section 1.1's section and eSTAR parts;
* the Manufacturer-text block and the placeholder box are on T1 and T8;
* a trial, a grace (expired) and a no-licence run each write their own constant into
  ``run.json`` (DEC-48 for the last), and the page rendered from that ``run.json`` stamps
  it;
* the A4 print CSS lives in ``templates/_print.css.j2``; no template and no rendered page
  carries ``@import``, ``url(`` or ``<link``; no template retypes a mark.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import make_criteria
from proofpack.licence.verify import WATERMARK_EXPIRED, WATERMARK_NO_LICENCE, WATERMARK_TRIAL
from proofpack.render import html as render_html
from proofpack.render import t1 as render_t1
from proofpack.render import t7 as render_t7
from proofpack.scope import DEMO_MARK, INCOMPLETE_MARK, PLACEHOLDER, SYNTHETIC_MARK
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site
from test_run_cli import _own_home, _prepare, _run

pytestmark = pytest.mark.day9

TEMPLATES = Path(render_html.TEMPLATES_DIR)
RENDERERS = {
    "T1": render_t1.render_t1,
    "T7": render_t7.render_t7,
    "T8": render_html.render_t8,
}


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    return assemble(cohort_with_a_thirty_row_site(), crit)


def _footers(page: str) -> list[str]:
    return re.findall(r'<footer class="page-footer">(.*?)</footer>', page, re.S)


@pytest.mark.parametrize(
    "licence_mark", [WATERMARK_TRIAL, WATERMARK_EXPIRED, WATERMARK_NO_LICENCE, None]
)
@pytest.mark.parametrize("data_mark", [SYNTHETIC_MARK, DEMO_MARK, None])
def test_the_cover_stamp_and_every_footer_carry_the_manifests_own_constants(
    document, licence_mark, data_mark
):
    doc = copy.deepcopy(document)
    doc["manifest"]["watermark"] = licence_mark
    if data_mark is not None:
        doc["manifest"]["data_marking"] = data_mark
    for name, render in RENDERERS.items():
        page = render(doc)
        cover = page.split('<section class="page', 2)[1]
        for kind, mark in (("licence", licence_mark), ("data", data_mark)):
            stamp = f'<p class="stamp" data-mark="{kind}">{mark}</p>'
            if mark is None:
                assert f'data-mark="{kind}"' not in page, (name, kind)
                continue
            assert stamp in cover, (name, stamp)
            footers = _footers(page)
            assert footers and all(mark in f for f in footers), (name, mark)
            assert mark in page.split('<div class="print-footer">', 1)[1]
        if licence_mark is None and data_mark is None:
            assert 'class="watermark"' not in page, name


def test_each_furniture_element_is_on_t1_and_t8(document):
    for name in ("T1", "T8"):
        page = RENDERERS[name](document)
        # the cover stamp: T1's and T8's pack has outstanding customer slots
        n = len([s for s in render_t1.customer_slots(document).values() if not s["filled"]])
        stamp = INCOMPLETE_MARK.format(n=n)
        assert f'<p class="stamp" data-mark="incomplete">{stamp}</p>' in page
        # the footer on every page section
        assert page.count('class="page-footer"') == page.count('<section class="page')
        # the margin note in D4 section 1.1's shape
        assert re.search(
            r'<aside class="margin-note draft">maps to <a href="#FDA_AIDSF_[A-Z_]+">'
            r"[^<]*not for implementation</a> · section to confirm · eSTAR: to "
            r"confirm</aside>",
            page,
        ), name
        assert "· section n/a · eSTAR: n/a</aside>" in page  # a ProofPack-internal anchor
        # the Manufacturer-text block (indented, labelled, the customer's words)
        assert '<div class="customer-text"><span class="label">Manufacturer text - ' in page
        # the placeholder box, spelled from scope.PLACEHOLDER
        title = render_t1.CUSTOMER_TEXT_SLOTS[0][1]
        box = PLACEHOLDER.format(title=title)
        assert f'<div class="placeholder" data-slot="CT-01">{box}</div>' in page, name
    t7 = render_t7.render_t7(document)
    assert t7.count('class="page-footer"') == t7.count('<section class="page') == 3
    assert "· eSTAR: " in t7


def _write_doc(tmp_path: Path, monkeypatch, name: str, **licence) -> tuple[dict, Path]:
    base = tmp_path / name
    base.mkdir()
    has = licence.pop("licence", True)
    _own_home(base, monkeypatch, licence=has, **licence)
    csv_path, yml = _prepare(base)
    out = base / "pack"
    _run(csv_path, yml, out, "--offline", "--templates", "T1,T7,T8")
    return json.loads((out / "run.json").read_text(encoding="utf-8")), out


def test_trial_grace_and_no_licence_runs_carry_their_own_constant(tmp_path, monkeypatch):
    now = datetime.now(UTC)
    trial, out_t = _write_doc(
        tmp_path, monkeypatch, "trial", tier="trial", issued=now - timedelta(days=1)
    )
    assert trial["manifest"]["watermark"] == WATERMARK_TRIAL
    grace, out_g = _write_doc(tmp_path, monkeypatch, "grace", expires=now - timedelta(days=5))
    assert grace["manifest"]["watermark"] == WATERMARK_EXPIRED
    none, out_n = _write_doc(tmp_path, monkeypatch, "none", licence=False)
    assert none["manifest"]["watermark"] == WATERMARK_NO_LICENCE  # DEC-48
    assert "data_marking" not in none["manifest"]  # set only by the sample-pack script
    for out, mark in ((out_t, WATERMARK_TRIAL), (out_g, WATERMARK_EXPIRED)):
        for name in ("T1", "T7", "T8"):
            page = (out / f"{name}.html").read_text(encoding="utf-8")
            assert f'<p class="stamp" data-mark="licence">{mark}</p>' in page, (name, mark)
    # no licence: JSON only (D1 section 7); the page a renderer makes from it stamps DEC-48's
    assert not (out_n / "T1.html").exists()
    page = render_t1.render_t1(none)
    assert f'<p class="stamp" data-mark="licence">{WATERMARK_NO_LICENCE}</p>' in page


def test_the_print_css_is_its_own_file_and_nothing_loads_from_outside(document):
    css = (TEMPLATES / "_print.css.j2").read_text(encoding="utf-8")
    assert "@media print" in css and "@page" in css and "position: fixed" in css
    for path in TEMPLATES.iterdir():
        # the rules' own comments name what they forbid; the grep reads the markup
        text = re.sub(r"\{#.*?#\}", "", path.read_text(encoding="utf-8"), flags=re.S)
        for bad in ("@import", "url(", "<link", "<script"):
            assert bad not in text, (path.name, bad)
        # no template retypes a mark: every stamp and footer word comes from the context
        for mark in (
            WATERMARK_TRIAL,
            WATERMARK_EXPIRED,
            WATERMARK_NO_LICENCE,
            SYNTHETIC_MARK,
            DEMO_MARK,
            "INCOMPLETE",
            "CUSTOMER TEXT REQUIRED",
        ):
            assert mark not in text, (path.name, mark)
    for render in RENDERERS.values():
        page = render(document)
        for bad in ("@import", "url(", "<link", "<script"):
            assert bad not in page
        assert page.count("@media print") == 1


def test_the_theme_block_reaches_the_style_unescaped_so_the_system_fonts_apply(
    document, monkeypatch
):
    """E9 found the E8 pages rendering in the browser's serif default: autoescape wrote the
    font stacks' quotes as ``&#34;``, which CSS reads as the end of the declaration."""
    from proofpack.render import theme

    for render in RENDERERS.values():
        style = render(document).split("<style>", 1)[1].split("</style>", 1)[0]
        assert "&#34;" not in style and "&quot;" not in style
        assert '--pp-type-text: -apple-system, BlinkMacSystemFont, "Segoe UI"' in style
        assert '--pp-type-mono: ui-monospace, "Cascadia Mono"' in style
    monkeypatch.setattr(theme, "css_variables", lambda: {"--pp-x": "red;} body{display:none"})
    with pytest.raises(ValueError, match=re.escape("the refused characters < > { } ; \\:")):
        theme.css_root_block()


def test_the_theme_guard_message_names_the_six_characters_it_refuses_and_no_other_class(
    monkeypatch,
):
    """E9 repair 1, lens RG-N10: the message said "a character a <style> block cannot hold"
    while the guard refuses six named characters and accepts ``a /* b`` and an unbalanced
    ``"``. Inspected: each of the six planted alone raises with the list of six in the
    message; the two values the lens fed are accepted (the guard's scope, recorded)."""
    from proofpack.render import theme

    for ch in "<>{};\\":
        monkeypatch.setattr(theme, "css_variables", lambda ch=ch: {"--pp-x": f"a{ch}b"})
        with pytest.raises(ValueError) as err:
            theme.css_root_block()
        assert "the refused characters < > { } ; \\:" in str(err.value)
        assert "cannot hold" not in str(err.value)
    for accepted in ("a /* b", '"unbalanced'):
        monkeypatch.setattr(theme, "css_variables", lambda v=accepted: {"--pp-x": v})
        assert accepted in theme.css_root_block()
