"""A-P3 item 3 (build day 9, lane A): T12, the CSA-structured software assurance record.

* **golden**: ``tests/fixtures/golden/T12.html`` is the render of the report
  ``proofpack.fixtures.run_fixtures()`` builds, masked (:func:`masked_report`): the
  machine-dependent report fields (``generated``, ``git_sha``, ``git_sha_source``,
  ``platform``, ``python``, ``numpy``, ``scipy``, ``duration_s``), every row's
  ``max_abs_deviation`` (set to 0 where a comparison was made) and the doctor rows' ``info``
  (set to ``masked``). Regenerate with ``PROOFPACK_REGEN_GOLDEN=1 python -m pytest
  tests/test_t12.py -k golden``;
* every report row appears once as ``<tr data-row="<id>">`` with the status text of its
  status; a report with ``F1-wilson`` planted off by 2e-9 prints that row ``not matched``
  and the count cell ``not_matched`` 1;
* the forbidden grep: the checker's ``VERDICT_WORDS`` and ``CERTIFICATION_WORDS`` plus
  ``validated``, ``compliant``, ``certified``, ``qualified`` over the page's text nodes:
  zero hits outside ``.customer-text`` and the D4 section 7.1 / 1.5 verbatim texts (class
  ``disclaimer``); inside those, the hits are exactly ``endorsed`` and ``qualified`` (the
  footer's "qualified statistician" and "no regulator has endorsed this tool");
* every FDA AI-DSF anchor on the page carries "draft guidance (January 2025), not for
  implementation" in its label and its guidance-table row carries ``class="draft"``;
* the ``[unverified`` markings of F13, F13b, the Newcombe table and the CSA sentence are on
  the page inside ``.unverified``;
* ``fixtures --html`` writes ``T12.html`` under the session's ephemeral-key licence and
  not without one (``PROOFPACK_HOME`` pointed at an empty directory), exit 0 both times.
"""

from __future__ import annotations

import copy
import html
import os
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from conftest import ephemeral_registry
from proofpack import fixtures as fx
from proofpack.cli import main
from proofpack.narrate.checker import CERTIFICATION_WORDS, VERDICT_WORDS
from proofpack.render import t12
from proofpack.resources import load_guidance_map

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "T12.html"
FORBIDDEN = (
    set(VERDICT_WORDS)
    | set(CERTIFICATION_WORDS)
    | {"validated", "compliant", "certified", "qualified"}
)
DRAFT_LABEL = "draft guidance (January 2025), not for implementation"


def masked_report(report: dict) -> dict:
    r = copy.deepcopy(report)
    r.update(
        generated="2026-09-24T00:00:00Z",
        git_sha=None,
        git_sha_source="masked",
        platform="masked-platform",
        on_reference_platform=False,
        python="3.12.0",
        numpy="x.y.z",
        scipy="x.y.z",
        duration_s=None,
    )
    for row in r["rows"]:
        if row["max_abs_deviation"] is not None:
            row["max_abs_deviation"] = 0.0
        for v in row["values"]:
            v["engine"] = v["oracle"]
            v["abs_deviation"] = 0.0
        if row["oracle_source"] and row["oracle_source"].get("library_versions"):
            row["oracle_source"]["library_versions"] = {"masked": "x.y.z"}
    for d in r["doctor"]:
        d["info"] = "masked"
        d["ok"] = True
    return r


@pytest.fixture(scope="module")
def report() -> dict:
    return fx.run_fixtures()


@pytest.fixture(scope="module")
def page(report) -> str:
    return t12.render_t12(report)


class _Walker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[set[str]] = []
        self.skip = 0
        self.nodes: list[tuple[str, set[str]]] = []

    def handle_starttag(self, tag, attrs):
        self.stack.append(set((dict(attrs).get("class") or "").split()))
        if tag in ("style", "title", "script"):
            self.skip += 1

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()
        if tag in ("style", "title", "script"):
            self.skip -= 1

    def handle_data(self, data):
        if self.skip or not data.strip():
            return
        scope: set[str] = set()
        for s in self.stack:
            scope |= s
        self.nodes.append((data, scope))


def forbidden_hits(page: str) -> tuple[list, list]:
    w = _Walker()
    w.feed(page)
    outside, inside = [], []
    for text, scope in w.nodes:
        words = set(re.split(r"[^a-z]+", text.lower())) - {""}
        hit = words & FORBIDDEN
        if not hit:
            continue
        (inside if scope & {"customer-text", "disclaimer"} else outside).append(
            (sorted(hit), text.strip()[:60])
        )
    return outside, inside


def test_golden_t12_matches_the_committed_render(report):
    page = t12.render_t12(masked_report(report)).replace("\r\n", "\n")
    if os.environ.get("PROOFPACK_REGEN_GOLDEN") == "1":
        GOLDEN.write_bytes(page.encode("utf-8"))
    assert GOLDEN.exists(), "regenerate with PROOFPACK_REGEN_GOLDEN=1"
    assert page == GOLDEN.read_bytes().decode("utf-8").replace("\r\n", "\n")
    assert t12.render_t12(masked_report(report)) == t12.render_t12(masked_report(report))


def test_every_report_row_appears_in_t12(report, page):
    for row in report["rows"]:
        cells = re.findall(rf'<tr data-row="{re.escape(row["id"])}">(.*?)</tr>', page)
        assert len(cells) == 1, row["id"]
        status = re.search(
            r'<td class="fixture-status" data-status="([a-z_]+)">([^<]*)</td>', cells[0]
        )
        assert status is not None, row["id"]
        assert status.group(1) == row["status"]
        assert status.group(2) == t12.STATUS_TEXT[row["status"]]
    assert page.count('<tr data-row="') == len(report["rows"]) == 43
    counts = dict(re.findall(r'data-count="([a-z_]+)">([^<]*)</td>', page))
    for key in ("rows", "matched", "not_matched", "no_oracle_recorded", "not_built", "suite_only"):
        assert counts[key] == str(report["summary"][key]), key


def test_a_not_matched_row_prints_as_not_matched():
    oracles = copy.deepcopy(fx.load_oracles())
    oracles["oracles_v1.json"]["captured"]["F1-wilson"]["values"]["wilson_lo"] += 2e-9
    rep = fx.run_fixtures(oracles=oracles, doctor=False)
    page = t12.render_t12(rep)
    row = re.search(r'<tr data-row="F1-wilson">(.*?)</tr>', page).group(1)
    assert '<td class="fixture-status" data-status="not_matched">not matched</td>' in row
    assert "outside tolerance: wilson_lo" in row
    assert 'data-count="not_matched">1</td>' in page
    assert 'data-count="exit_code">6</td>' in page
    outside, _ = forbidden_hits(page)
    assert outside == []


def test_no_forbidden_word_outside_customer_text_and_the_verbatim_disclaimer(report, page):
    outside, inside = forbidden_hits(page)
    assert outside == []
    assert {w for hit, _ in inside for w in hit} == {"endorsed", "qualified"}
    # the same with a licence watermark on the page, and on the masked golden render
    for other in (
        t12.render_t12(report, watermark="LICENCE EXPIRED - not for submission"),
        t12.render_t12(masked_report(report)),
    ):
        assert forbidden_hits(other)[0] == []


def test_every_fda_draft_anchor_is_labelled_on_the_page(page):
    rows = {r["internal_id"]: r for r in load_guidance_map()}
    ids = re.findall(r'<tr id="([A-Z0-9_]+)"', page)
    assert set(ids) == set(t12.T12_ANCHORS.values())
    drafts = [i for i in ids if rows[i]["status"].lower().startswith("draft")]
    assert drafts == ["FDA_AIDSF_PERF_VALIDATION"]
    for i in drafts:
        row = re.search(rf'<tr id="{i}" class="draft">(.*?)</tr>', page)
        assert row is not None and DRAFT_LABEL in row.group(1)
    notes = re.findall(r'<aside class="margin-note draft">(.*?)</aside>', page)
    assert notes and all(DRAFT_LABEL in n for n in notes)


def test_unverified_markings_survive_to_the_page(page):
    spans = [html.unescape(x) for x in re.findall(r'<span class="unverified">([^<]*)</span>', page)]
    assert any(s.startswith("[unverified until captured] the pROC capture") for s in spans)
    assert any(s.startswith("[unverified until captured] the rms::val.prob") for s in spans)
    assert "[unverified against the primary PDF]" in spans
    assert t12.CSA_UNVERIFIED in spans


def test_the_required_sentences_are_on_the_page(page):
    text = html.unescape(page)
    assert t12.SUPPORTS_SENTENCE == (
        "This record supports, does not replace, the manufacturer's own validation."
    )
    assert text.count(t12.SUPPORTS_SENTENCE) == 2
    assert t12.PRINT_SENTENCE in text and "print this HTML page to PDF" in text
    assert "Hash identity is claimed on the reference platform only" in text
    assert "python:3.12-slim linux/amd64" in text
    assert "ProofPack signs nothing." in page
    # four checklist steps, each with four blank sign-off cells
    for step in ("doctor", "fixtures", "mapping", "declarations"):
        row = re.search(rf'<tr data-step="{step}">(.*?)</tr>', page).group(1)
        assert row.count('<td class="signoff"></td>') == 4, step
    # the intended-use slot is the placeholder, never engine-drafted text
    assert "[CUSTOMER TEXT REQUIRED - intended use of ProofPack" in page
    assert "INCOMPLETE - customer sections outstanding: 1" in page


def test_the_failure_mode_table_lists_every_engine_code(page):
    from proofpack import errors

    for code in (
        list(errors.HALT_CODES)
        + list(errors.SCHEMA_CODES)
        + list(errors.MAPPING_CODES)
        + list(errors.WARN_CODES)
    ):
        assert f'<tr data-code="{code}">' in page, code
    assert '<tr data-code="exit 6">' in page


def test_fixtures_html_writes_t12_under_a_licence_and_not_without(tmp_path, monkeypatch, capsys):
    rc = main(
        ["fixtures", "--offline", "--out", str(tmp_path / "a"), "--html"],
        registry=ephemeral_registry(),
    )
    out = capsys.readouterr().out
    assert rc == 0 and (tmp_path / "a" / "T12.html").exists(), out
    assert "document written:" in out
    empty = tmp_path / "home"
    empty.mkdir()
    monkeypatch.setenv("PROOFPACK_HOME", str(empty))
    rc = main(
        ["fixtures", "--offline", "--out", str(tmp_path / "b"), "--html"],
        registry=ephemeral_registry(),
    )
    out = capsys.readouterr().out
    assert rc == 0 and not (tmp_path / "b" / "T12.html").exists()
    assert (tmp_path / "b" / "fixtures_report.json").exists()
    assert "T12.html not written: licence refused (no_file)" in out
