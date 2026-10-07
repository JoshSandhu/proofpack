"""Shared pages for the build-day-14 tests (E14, LW-01): the pages items 1 and 2 read.

* ``document``: the synthetic document T1's golden uses (assembler, CRITERIA + FAIRNESS);
* ``licensed_pack``: a licensed ``proofpack --offline --quiet run --templates T1,T7,T8`` of
  the 5,000-row synthetic cohort (:func:`proofpack.synthetic.make_cohort` at its default
  seed, ``n=5000``) with ``make_criteria()``'s declarations, under its own home with an
  ephemeral-signed licence - the path the LW-01 walk-through measured;
* ``t2_page``: T2 of the F5 compare fixture (the T2 golden's document).
"""

from __future__ import annotations

import copy
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import (
    confirmed_mapping,
    ephemeral_registry,
    make_cohort,
    make_criteria,
    write_csv,
    write_licence,
    write_yaml,
)
from proofpack import cli
from proofpack.render import html as render_html
from proofpack.render import t1 as render_t1
from proofpack.render import t2 as render_t2
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site

DRAFT_LABEL = "draft guidance (January 2025), not for implementation"
INTERNAL_PREFIX = "ProofPack internal"
AIDSF_TITLE = "Artificial Intelligence-Enabled Device Software Functions: Lifecycle"

COVER = re.compile(r'<th scope="row">Guidance versions referenced</th><td>(.*?)</td>', re.S)
COVER_LINK = re.compile(r'<a href="#([A-Z0-9_]+)">([^<]*)</a>')
TABLE_ROW = re.compile(
    r'<tr id="([A-Z0-9_]+)"( class="draft")?><td class="mono">([^<]*)</td><td>([^<]*)</td>'
)
NOTE = re.compile(r'<aside class="margin-note( draft)?"( data-also="([^"]*)")?>(.*?)</aside>')


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    return assemble(cohort_with_a_thirty_row_site(), crit)


@pytest.fixture(scope="module")
def licensed_pack(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("e14pack")
    home = base / "home"
    home.mkdir()
    mp = pytest.MonkeyPatch()
    mp.setenv("PROOFPACK_HOME", str(home))
    try:
        write_licence(home / "proofpack.lic")
        csv_path = write_csv(base / "synthetic_cohort.csv", make_cohort(n=5000))
        yml = write_yaml(base / "criteria.yaml", make_criteria())
        confirmed_mapping(csv_path)
        out = base / "pack"
        argv = ["--offline", "--quiet", "run", "--input", str(csv_path), "--criteria", str(yml)]
        argv += ["--out", str(out), "--templates", "T1,T7,T8"]
        rc = cli.main(argv, registry=ephemeral_registry())
    finally:
        mp.undo()
    assert rc in (0, 2), rc
    return out


@pytest.fixture(scope="module")
def t2_page(tmp_path_factory) -> str:
    from test_e10_t2 import F5, compare_document  # noqa: PLC0415

    base = tmp_path_factory.mktemp("e14t2")
    for name in ("f5_new.csv", "f5_prior.csv", "criteria.yaml"):
        shutil.copy(F5 / name, base / name)
    doc = compare_document(base, base / "f5_new.csv", base / "f5_prior.csv", base / "criteria.yaml")
    return render_t2.render_t2(doc)


def pages(document, licensed_pack, t2_page) -> dict[str, str]:
    return {
        "T1 (render)": render_t1.render_t1(document),
        "T8 (render)": render_html.render_t8(document),
        "T1 (licensed run)": (licensed_pack / "T1.html").read_text(encoding="utf-8"),
        "T8 (licensed run)": (licensed_pack / "T8.html").read_text(encoding="utf-8"),
        "T2 (render)": t2_page,
    }


def cover(page: str) -> list[tuple[str, str]]:
    m = COVER.search(page)
    assert m, "no cover row"
    return COVER_LINK.findall(m.group(1))


def guidance_table(page: str) -> list[tuple[str, bool, str, str]]:
    start = page.index('<table class="guidance">')
    body = page[start : page.index("</table>", start)]
    return [(i, bool(d), mono, label) for i, d, mono, label in TABLE_ROW.findall(body)]


def blocks(page: str) -> list[tuple[str, str]]:
    """``(h2 id, html)`` per block: from one ``<h2`` to the next; the part before the
    first ``<h2`` (the cover, where T2 prints section 0's note) is ``@start``."""
    starts = [0] + [m.start() for m in re.finditer(r"<h2 ", page)] + [len(page)]
    out = []
    for a, b in zip(starts, starts[1:], strict=False):
        m = re.match(r'<h2 id="([^"]+)"', page[a:])
        out.append((m.group(1) if m else "@start" if a == 0 else f"@{a}", page[a:b]))
    return out


def visible(note_html: str) -> str:
    return re.sub(r"<[^>]+>", "", note_html)
