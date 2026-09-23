"""Build day 8 (E8 items 7-9): T8 rendered from the synthetic cohort.

* **golden**: ``tests/fixtures/golden/T8.html`` is the render of the synthetic document
  (``tests/assembler.py`` on ``cohort_with_a_thirty_row_site`` with CRITERIA + FAIRNESS,
  B = 200, seed 20240101) compared LF-normalised. Masking: the assembler's manifest already
  carries fixed placeholders for ``run_id`` (``test-only-assembler``), ``started``
  (``2026-09-18T00:00:00Z``) and ``duration_s`` (``null``); the one machine-dependent
  field, ``manifest.numpy``, is set to ``x.y.z`` before rendering. Regenerate with
  ``PROOFPACK_REGEN_GOLDEN=1 python -m pytest tests/test_render_t8.py -k golden``;
* **footer on every page**: the ``page-footer`` marker is counted against the
  ``<section class="page"`` count on a one-page and a two-page document through the base
  furniture, and on T8's three pages; the fixed print footer appears once;
* **anchor label**: every anchor whose map row is the FDA AI-DSF draft carries the label
  in the structured data and on the page; a map row planted without the qualifier makes
  the renderer refuse;
* **section 7 counts** equal counts computed here from the document;
* **the verdict grep on the rendered text**: the three status words appear only inside
  elements of class ``status``; the forbidden words appear nowhere outside the verbatim
  D4 section 7 disclaimer (which negates ``approved`` / ``endorsed``) and the customer's
  own text (``.customer-text``), and a planted ``pass`` in a justification is rendered
  verbatim, escaped, and flagged by the grep exactly there;
* **HTML injection**: a justification and a level label carrying ``<script>``, ``&``,
  ``"`` and a right-to-left override render escaped (asserted on the bytes);
* **twenty cells** printed for the criteria table equal ``fmt.number`` of the Number the
  row's ``metric_ref`` names in the document;
* ``--offline`` with ``--format html`` opens no socket; T8.html is written only on a
  licence that is ok or in grace; ``--templates T1`` prints the typed line.
"""

from __future__ import annotations

import copy
import csv
import html as html_lib
import json
import os
import re
import socket
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import ephemeral_registry, make_cohort, make_criteria, write_csv, write_yaml
from proofpack.cli import main
from proofpack.errors import EXIT_INTERNAL, EXIT_LICENCE, EXIT_OK, EXIT_WARNINGS
from proofpack.narrate import claims as claims_mod
from proofpack.narrate.checker import resolve_pointer
from proofpack.narrate.templates import STATUS_WORDS
from proofpack.render import anchors
from proofpack.render import format as fmt
from proofpack.render import html as render_html
from proofpack.resources import load_guidance_map
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site
from test_run_cli import _own_home, _prepare
from test_subgroups import VERDICT_WORDS

pytestmark = pytest.mark.day8

REPO = Path(__file__).resolve().parent.parent
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "T8.html"
NUMPY_MASK = "x.y.z"
FORBIDDEN_ON_PAGE = {
    "pass",
    "fail",
    "verdict",
    "meets",
    "acceptable",
    "consistent",
    "unbiased",
    "certified",
    "cleared",
    "compliant",
    "safe",
} | VERDICT_WORDS
STATUS_TOKENS = {"criterion", "met", "not", "assessable"}


def _criterion(**kw) -> dict[str, Any]:
    base = {
        "id": "C",
        "metric": "sensitivity",
        "operating_point": "op1",
        "scope": "overall",
        "statistic": "ci_lower_bound",
        "comparator": ">=",
        "value": 0.5,
        "author": "Dr A.",
        "date": "2026-01-01",
        "justification": "test fixture",
    }
    base.update(kw)
    return {k: v for k, v in base.items() if v is not None}


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    doc["manifest"]["numpy"] = NUMPY_MASK
    return doc


@pytest.fixture(scope="module")
def page(document) -> str:
    return render_html.render_t8(document)


# ------------------------------------------------------------------ a text walker


class _TextWalker(HTMLParser):
    """Text nodes of the rendered page with the classes of every open element; the
    <style> and <title> contents are skipped (they are not rendered text)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[set[str]] = []
        self.skip = 0
        self.nodes: list[tuple[str, set[str]]] = []

    def handle_starttag(self, tag, attrs):
        classes = set((dict(attrs).get("class") or "").split())
        self.stack.append(classes)
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


def text_nodes(page: str) -> list[tuple[str, set[str]]]:
    w = _TextWalker()
    w.feed(page)
    return w.nodes


def words(text: str) -> set[str]:
    return set(re.split(r"[^a-z]+", text.lower())) - {""}


def footers_per_page(page: str) -> list[int]:
    """The number of ``page-footer`` elements inside each ``<section class="page`` (E9
    repair 1, lens RG-N3: the footer tests compared two totals, so a footer moved from
    one page to another passed)."""
    chunks = page.split('<section class="page')[1:]
    return [c.split("</section>", 1)[0].count('class="page-footer"') for c in chunks]


# ------------------------------------------------------------------ golden


def test_golden_t8_matches_the_committed_render(document):
    page = render_html.render_t8(document).replace("\r\n", "\n")
    if os.environ.get("PROOFPACK_REGEN_GOLDEN") == "1":
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_bytes(page.encode("utf-8"))
    assert GOLDEN.exists(), "regenerate with PROOFPACK_REGEN_GOLDEN=1"
    golden = GOLDEN.read_bytes().decode("utf-8").replace("\r\n", "\n")
    assert page == golden
    assert NUMPY_MASK in page and "test-only-assembler" in page
    assert render_html.render_t8(document) == render_html.render_t8(document)  # deterministic


# ------------------------------------------------------------------ furniture


def test_the_page_has_no_external_reference_and_the_theme_is_the_only_style_source(page):
    for bad in ("@import", "url(", "<link", "<script", "fonts.googleapis", "@font-face"):
        assert bad not in page, bad
    style = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    assert page.count("<style>") == 1
    # the :root block carries the tokens; the rules reference var(--pp-...) and no hex colour
    assert ":root {" in style and "--pp-color-ink: #16202b;" in style
    rules = style[style.index("}") + 1 :]
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", rules), "a colour literal outside the tokens"
    assert 'lang="en-GB"' in page and '<meta charset="utf-8">' in page
    assert '<th scope="col">' in page and '<th scope="row">' in page


def test_the_footer_repeats_on_every_page_section_and_once_in_print(page, document):
    sections = page.count('<section class="page"')
    assert sections == 3
    assert page.count('class="page-footer"') == sections
    assert page.count('class="print-footer"') == 1
    short = page.count(
        "This output is not a regulatory opinion; no regulator has endorsed this tool."
    )
    assert short == sections + 1
    assert "ProofPack v0.1.0.dev1 on 2026-09-18T00:00:00Z" in page  # the manifest's date, not now()


@pytest.mark.parametrize("n_pages", [1, 2])
def test_the_base_furniture_puts_the_footer_on_each_of_one_and_two_pages(document, n_pages):
    bodies = [f"<h1>Page {i + 1}</h1><p>body</p>" for i in range(n_pages)]
    out = render_html.render_pages(document, bodies)
    assert out.count('<section class="page"') == n_pages
    assert out.count('class="page-footer"') == n_pages
    assert out.count('class="print-footer"') == 1
    assert out.count("no regulator has endorsed this tool.") == n_pages + 1


def test_the_watermark_word_appears_in_every_footer_when_present(document):
    doc = copy.deepcopy(document)
    doc["manifest"]["watermark"] = "LICENCE EXPIRED - not for submission"
    out = render_html.render_t8(doc)
    footers = re.findall(r'<footer class="page-footer">(.*?)</footer>', out, re.S)
    assert len(footers) == 3 and all("LICENCE EXPIRED - not for submission" in f for f in footers)
    assert out.count('class="watermark"') == 3 + 1  # every page footer and the print footer
    assert 'class="stamp"' in out
    plain = render_html.render_t8(document)
    assert 'class="watermark"' not in plain


# ------------------------------------------------------------------ anchors


def test_every_fda_aidsf_anchor_carries_the_draft_label_in_data_and_on_the_page(page, document):
    refs = document["guidance_refs"]
    assert refs
    rows = {r["internal_id"]: r for r in load_guidance_map()}
    drafts = [r for r in refs if rows[r["id"]]["status"].lower().startswith("draft")]
    assert drafts and all(r["id"].startswith("FDA_AIDSF_") for r in drafts)
    label = "draft guidance (January 2025), not for implementation"
    for r in refs:
        assert r["draft"] is (r["id"].startswith("FDA_AIDSF_"))
        assert (label in r["label"]) is r["draft"], r
        assert r["url"] is None
        assert f'id="{r["id"]}"' in page  # the map's internal id as the HTML id
    # the T8 sections' own anchors join the table
    for internal_id in render_html.T8_ANCHORS.values():
        assert f'<tr id="{internal_id}"' in page, internal_id
    page_drafts = re.findall(r'<tr id="(FDA_AIDSF_[A-Z_]+)" class="draft">', page)
    assert page_drafts and all(
        label in row for row in re.findall(r'<tr id="FDA_AIDSF_[A-Z_]+"[^\n]*', page)
    )


def test_a_map_row_without_the_qualifier_makes_the_renderer_refuse(document, tmp_path):
    rows = [dict(r) for r in load_guidance_map()]
    planted = next(r for r in rows if r["internal_id"] == "FDA_AIDSF_PERF_VALIDATION")
    planted["status"] = "draft"
    path = tmp_path / "guidance_map_v1.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with path.open(encoding="utf-8", newline="") as fh:
        tmp_map = list(csv.DictReader(fh))
    with pytest.raises(anchors.AnchorError, match="not for implementation"):
        render_html.render_t8(document, guidance_map=tmp_map)
    with pytest.raises(anchors.AnchorError, match="unknown guidance anchor"):
        anchors.resolve(["FDA_AIDSF_NOPE"])
    item = anchors.guidance_ref_item("FDA_AIDSF_SUBGROUP_PERF")
    assert item["draft"] is True and item["label"].endswith(
        ": draft guidance (January 2025), not for implementation"
    )
    assert anchors.guidance_ref_item("FDA_STAT2007_CI")["draft"] is False
    assert anchors.month_year("2025-01-07") == "January 2025"


# ------------------------------------------------------------------ section 7


def test_section_7_counts_equal_counts_computed_from_the_document(page, document):
    counts = dict(re.findall(r'data-count="([a-z_]+)">([^<]*)</td>', page))
    statuses = [r["status"] for r in document["criteria_results"]]

    def suppressed(node):
        if isinstance(node, dict):
            if {"est", "ci_lo", "ci_hi", "method", "suppressed"} <= set(node):
                yield bool(node["suppressed"])
            for v in node.values():
                yield from suppressed(v)
        elif isinstance(node, list):
            for v in node:
                yield from suppressed(v)

    expected = {
        "claims_generated": len(document["claims"]),
        "claims_rejected": len(document["claim_rejections"]),
        "claims_substituted": sum(1 for r in document["claim_rejections"] if r["substituted"]),
        "rows_analysed": document["flow"]["analysed"],
        "subgroup_rows": len(document["subgroups"]),
        "criteria_rows": len(statuses),
        "criteria_met": statuses.count("met"),
        "criteria_not_met": statuses.count("not_met"),
        "criteria_not_assessable": statuses.count("not_assessable"),
        "suppressed_cells": sum(suppressed(document)),
        "warnings": len(document["warnings"]),
    }
    assert {k: int(v) for k, v in counts.items()} == expected
    assert expected["claims_generated"] == 70 and expected["criteria_rows"] == 9
    assert expected["criteria_met"] == 2 and expected["criteria_not_met"] == 2
    assert "No claim was rejected by the checker." in page


def test_section_7_prints_the_rejections_when_the_document_carries_them(document):
    doc = copy.deepcopy(document)
    doc["claim_rejections"] = [
        {
            "claim_id": "CL-0001",
            "reason_code": "status_mismatch",
            "template_id": "CRITERION_STATUS",
            "substituted": True,
            "detail": {},
        }
    ]
    out = render_html.render_t8(doc)
    assert 'data-count="claims_rejected">1</td>' in out
    assert 'data-count="claims_substituted">1</td>' in out
    assert '<td class="mono">status_mismatch</td>' in out


# ------------------------------------------------------------------ the verdict grep


def _status_and_forbidden_hits(page: str):
    status_hits, forbidden_hits = [], []
    for text, scope in text_nodes(page):
        ws = words(text)
        # the customer's own text is exempt: the fixture's criterion id is "C_met" and is
        # echoed verbatim in the id cell and the declarations echo (both .customer-text)
        if ws & {"met", "assessable"} and not ({"status", "customer-text"} & scope):
            status_hits.append((text, scope))
        hit = ws & FORBIDDEN_ON_PAGE
        if "status" in scope:
            # the three status phrases' own tokens are permitted there and nowhere else
            hit -= STATUS_TOKENS
        if hit:
            forbidden_hits.append((sorted(hit), text.strip()[:60], scope))
    return status_hits, forbidden_hits


def test_status_words_only_in_status_cells_and_no_forbidden_word_outside_the_disclaimer(page):
    status_hits, forbidden = _status_and_forbidden_hits(page)
    assert status_hits == []
    # outside status cells the words occur only in the customer's own text, as the id C_met
    customer_hits = [
        text.strip()[:40]
        for text, scope in text_nodes(page)
        if words(text) & {"met", "assessable"} and "status" not in scope
    ]
    assert customer_hits and all("C_met" in t or "C_met" in page for t in customer_hits)
    # the three status phrases appear, in status cells, exactly as D4 section 1.2 spells them
    cells = re.findall(r'<td class="status">([^<]*)</td>', page)
    assert set(cells) == set(STATUS_WORDS.values())
    assert cells.count("criterion met") == 2 and cells.count("criterion not met") == 2
    # the only forbidden-word hits are the verbatim D4 section 7 disclaimer's negations
    # ("no regulator has ... approved or endorsed") and D4's own out-of-scope wording
    for hit, text, scope in forbidden:
        assert "disclaimer" in scope or "customer-text" in scope, (hit, text, scope)
        assert not (set(hit) & {"pass", "fail", "verdict", "certified", "cleared"}), (hit, text)
    assert "&lt;" not in page.split("<body>")[0]


def test_a_planted_pass_in_a_justification_is_rendered_verbatim_escaped_and_flagged(tmp_path):
    crit = make_criteria(
        criteria=[_criterion(id="C_pass", justification='This model will pass & <win> "easily"')],
        fairness=None,
    )
    doc = assemble(make_cohort(n=120), crit)
    doc["manifest"]["numpy"] = NUMPY_MASK
    out = render_html.render_t8(doc)
    # rendered verbatim: escaped, not rewritten, inside the customer-text block
    assert "This model will pass &amp; &lt;win&gt; &#34;easily&#34;" in out
    assert "will pass & <win>" not in out
    hits = [(text, scope) for text, scope in text_nodes(out) if "pass" in words(text)]
    assert hits and all("customer-text" in scope for scope in (s for _, s in hits))
    # the grep flags it (the customer's word is the customer's, and is not silently dropped)
    _, forbidden = _status_and_forbidden_hits(out)
    assert any("pass" in hit for hit, _, _ in forbidden)


def test_html_injection_in_a_justification_and_a_level_label_is_escaped(tmp_path):
    label = '<script>alert(1)</script>&"‮S1'
    cols = make_cohort(n=120)
    cols["site"] = [label if s == "S1" else s for s in cols["site"]]
    crit = make_criteria(
        criteria=[
            _criterion(
                id="C_site",
                metric="accuracy",
                scope={"attribute": "site", "level": "*"},
                justification='<script>alert(1)</script> & " ‮',
            )
        ],
        fairness=None,
    )
    doc = assemble(cols, crit)
    doc["manifest"]["numpy"] = NUMPY_MASK
    out = render_html.render_t8(doc).encode("utf-8")
    assert b"<script>" not in out and b"alert(1)" in out
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in out
    assert b"\xe2\x80\xae" not in out  # U+202E never reaches the page raw
    assert b"&#x202e;" in out
    assert b"&#34;" in out or b"&quot;" in out
    assert b"&amp;" in out
    # the yaml echo of the declarations is escaped too
    assert out.count(b"&lt;script&gt;") >= 2


def test_a_typed_reason_a_suppressed_cell_and_an_unverified_marking_on_the_page(document):
    doc = copy.deepcopy(document)
    # a criterion row whose Number is suppressed (k-suppression shape) prints the marker
    n30 = next(i for i, r in enumerate(doc["criteria_results"]) if r["criterion_id"] == "C_n30")
    ref = claims_mod._dotted_to_pointer(doc["criteria_results"][n30]["metric_ref"])
    _, number = resolve_pointer(doc, ref)
    number.update({"suppressed": True, "est": None, "ci_lo": None, "ci_hi": None})
    doc["criteria_results"][n30].update(
        {"status": "not_assessable", "reason_code": "suppressed", "compared_value": None}
    )
    # a customer slot carrying an [unverified] marking survives verbatim
    doc["declarations"]["criteria"][0]["justification"] = (
        "Margin per Newcombe Table II [unverified against the primary PDF]"
    )
    out = render_html.render_t8(doc)
    observed = re.findall(r'<td class="num observed">([^<]*)</td>', out)
    assert "‡" in observed
    assert not any(ch.isdigit() for ch in observed[n30])
    # the C_f1_site rows carry no Number (metric_not_computed_for_scope): a dash, no digit
    f1_rows = [i for i, r in enumerate(doc["criteria_results"]) if r["criterion_id"] == "C_f1_site"]
    assert all(observed[i] == "—" for i in f1_rows)
    assert "[unverified against the primary PDF]" in out
    # a Number with a typed reason prints the reason and no digit from est
    doc2 = copy.deepcopy(document)
    met = next(i for i, r in enumerate(doc2["criteria_results"]) if r["criterion_id"] == "C_met")
    num = doc2["overall"]["op1"]["sensitivity"]
    num.update(
        {"ci_lo": None, "ci_hi": None, "method": "none", "not_estimable_reason": "single_class"}
    )
    doc2["criteria_results"][met].update(
        {"status": "not_assessable", "reason_code": "no_interval", "compared_value": None}
    )
    out2 = render_html.render_t8(doc2)
    cell = re.findall(r'<td class="num observed">([^<]*)</td>', out2)[met]
    assert cell.startswith("n.e. (single_class)") and not any(ch.isdigit() for ch in cell)


# ------------------------------------------------------------------ twenty cells


def _criteria_twenty() -> list[dict[str, Any]]:
    return [
        _criterion(id="C_se_overall", value=0.5),
        _criterion(id="C_sp_overall", metric="specificity", value=0.5),
        _criterion(id="C_auroc", metric="auroc", operating_point=None, value=0.5),
        _criterion(id="C_prev", metric="prevalence", operating_point=None, value=0.1),
        _criterion(id="C_acc_site", metric="accuracy", scope={"attribute": "site", "level": "*"}),
        _criterion(id="C_se_site", scope={"attribute": "site", "level": "*"}),
        _criterion(id="C_ppv_sex", metric="ppv", scope={"attribute": "sex", "level": "*"}),
        _criterion(id="C_npv_age", metric="npv", scope={"attribute": "age", "level": "*"}),
        _criterion(
            id="C_auroc_sex",
            metric="auroc",
            operating_point=None,
            scope={"attribute": "sex", "level": "*"},
        ),
        _criterion(id="C_brier", metric="brier", operating_point=None, comparator="<=", value=0.3),
        _criterion(
            id="C_oe", metric="oe", operating_point=None, statistic="point_estimate", value=0.5
        ),
    ]


def test_twenty_printed_cells_equal_fmt_number_of_the_document_number():
    crit = make_criteria(criteria=_criteria_twenty(), fairness=FAIRNESS)
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    doc["manifest"]["numpy"] = NUMPY_MASK
    out = render_html.render_t8(doc)
    observed = re.findall(r'<td class="num observed">([^<]*)</td>', out)
    rows = doc["criteria_results"]
    assert len(observed) == len(rows) >= 20
    compared = 0
    for cell, row in zip(observed, rows, strict=True):
        ref = claims_mod._dotted_to_pointer(row["metric_ref"])
        if ref is None:
            assert cell == "—"
            continue
        found, number = resolve_pointer(doc, ref)
        assert found
        kind = fmt.kind_for(row["metric"], difference=row["metric"].endswith("_gap"))
        assert html_lib.unescape(cell) == fmt.number(number, kind), (row["criterion_id"], cell)
        compared += 1
    assert compared >= 20
    # the declared value prints every digit run.json carries (repair 1, FA-B4); the
    # compared value and the bound, engine numbers, print on the unit scale to 3 dp
    for row, m in zip(
        rows, re.finditer(r'<tr class="criterion-row"[^>]*>(.*?)</tr>', out, re.S), strict=True
    ):
        cells = re.findall(r"<td[^>]*>([^<]*)</td>", m.group(1))
        assert cells[7] == fmt.declared(row["value"])
        assert cells[12] == fmt.scalar(row["compared_value"])
        assert cells[16] == fmt.scalar(row["max_lower_bound_at_n"])
        assert cells[13] == STATUS_WORDS[row["status"]]
        assert cells[14] == row["reason_code"]
        assert int(cells[0]) == rows.index(row) + 1


def test_rows_are_keyed_by_position_so_a_shared_id_prints_every_row(page, document):
    positions = re.findall(r'<tr class="criterion-row" data-position="(\d+)">', page)
    assert positions == [str(i + 1) for i in range(len(document["criteria_results"]))]
    ids = re.findall(r'<td class="customer-text mono">([^<]*)</td>', page)
    assert ids.count("C_f1_site") == 3


# ------------------------------------------------------------------ the CLI route


def test_run_with_format_html_writes_t8_beside_run_json_on_a_valid_licence(tmp_path, monkeypatch):
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--offline"],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_OK
    assert (out / "T8.html").exists() and (out / "run.json").exists()
    page = (out / "T8.html").read_bytes()
    assert b"\r\n" not in page and page.startswith(b"<!DOCTYPE html>")
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert page.decode("utf-8") == render_html.render_t8(doc)  # a pure function of run.json
    assert doc["manifest"]["run_id"][:8].encode() in page


def test_offline_with_format_html_opens_no_socket(tmp_path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path)

    def refuse(*a, **k):
        raise AssertionError("a socket was opened")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    out = tmp_path / "pack"
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
            "json,html",
        ],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_OK and (out / "T8.html").exists()
    assert "document written:" in capsys.readouterr().out


def test_no_licence_writes_json_only_and_says_so(tmp_path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch, licence=False)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--offline"],
        registry=None,
    )
    assert rc == EXIT_LICENCE
    assert (out / "run.json").exists() and not (out / "T8.html").exists()
    printed = capsys.readouterr().out
    assert "HTML not written: licence refused (no_file)" in printed
    assert "then run again for T8.html" in printed


def test_expired_past_grace_writes_json_only(tmp_path, monkeypatch, capsys):
    from datetime import UTC, datetime, timedelta

    _own_home(tmp_path, monkeypatch, expires=datetime.now(UTC) - timedelta(days=60))
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--offline"],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_LICENCE
    assert (out / "run.json").exists() and not (out / "T8.html").exists()
    assert "HTML not written: licence expired" in capsys.readouterr().out


def test_grace_writes_the_document_with_the_watermark(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta

    _own_home(tmp_path, monkeypatch, expires=datetime.now(UTC) - timedelta(days=5))
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--offline"],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_OK
    page = (out / "T8.html").read_text(encoding="utf-8")
    assert page.count("LICENCE EXPIRED - not for submission") >= 4


def test_templates_t1_prints_the_typed_line_and_format_json_writes_no_html(
    tmp_path, monkeypatch, capsys
):
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
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
            "--templates",
            "T1,T7,T8",
        ],
        registry=ephemeral_registry(),
    )
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    printed = capsys.readouterr().out
    # E9 builds T1 and T7: the typed "not built" line is gone and the three are written
    assert "not written" not in printed and "not built" not in printed
    assert (out / "T1.html").exists() and (out / "T7.html").exists()
    assert "Traceback" not in printed and (out / "T8.html").exists()
    rc = main(
        [
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--out",
            str(tmp_path / "p2"),
            "--offline",
            "--format",
            "json",
        ],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_OK and not (tmp_path / "p2" / "T8.html").exists()
    assert "run again with --format json,html" in capsys.readouterr().out
    rc = main(
        [
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--out",
            str(tmp_path / "p3"),
            "--offline",
            "--format",
            "docx",
        ],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_INTERNAL and not (tmp_path / "p3").exists()
    assert "unknown --format token 'docx'" in capsys.readouterr().err


def test_json_log_reports_the_documents(tmp_path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
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
            "--json-log",
        ],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])["run"]
    assert payload["formats"] == ["json", "html"] and payload["templates"] == ["T8"]
    assert payload["documents"] == [str(out / "T8.html")] and payload["document_notes"] == []
    assert payload["claims"] == 70 and payload["claim_rejections"] == 0


def test_the_run_document_validates_with_the_narrative_keys(tmp_path, monkeypatch):
    import jsonschema

    from proofpack.resources import load_json_schema

    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    assert (
        main(
            [
                "run",
                "--input",
                str(csv_path),
                "--criteria",
                str(yml),
                "--out",
                str(out),
                "--offline",
            ],
            registry=ephemeral_registry(),
        )
        == EXIT_OK
    )
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    schema = load_json_schema("output_schema_v1.json")
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(doc)) == []
    assert (
        schema["properties"]["claims"]["items"] == load_json_schema("claims_schema.json")["items"]
    )
    assert set(schema["properties"]["guidance_refs"]["items"]["required"]) == {
        "id",
        "label",
        "draft",
        "url",
    }
    assert {"claims", "claim_rejections", "guidance_refs"} <= set(schema["required"])
    assert doc["claims"] and doc["claim_rejections"] == []
    assert all(r["draft"] is r["id"].startswith("FDA_AIDSF_") for r in doc["guidance_refs"])
    write_csv(tmp_path / "unused.csv", {"a": [1]})
    write_yaml(tmp_path / "unused.yaml", {"a": 1})
