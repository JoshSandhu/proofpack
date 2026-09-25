"""Build day 10 (E10 item 4): T2, the PCCP performance-evaluation report.

* **golden**: ``tests/fixtures/golden/T2.html`` is the render of the F5 fixture pair's
  compare document (``assemble_compare`` on ``tests/fixtures/f5``, an empty per-user
  home, the test licence), read back from its written ``run.json`` and masked at the
  manifest's machine- and run-dependent keys (``run_id``, ``started``, ``duration_s``,
  ``mapping_sha256`` - the confirmed mapping carries a timestamp - ``numpy``, ``scipy``,
  ``python``, ``platform``, ``reference_platform``), compared LF-normalised. Regenerate
  with ``PROOFPACK_REGEN_GOLDEN=1``;
* **footer on every page** (``test_render_t8.footers_per_page``), once in print;
* **the verdict grep**: the status words only inside ``.status``; the T2 record string
  only in ``not_met`` rows of T2-3 / T2-4 and nowhere on a ``met`` row; the forbidden
  words only in the disclaimer and the customer's own text;
* **every printed Number cell traces to run.json** (the E9 parse test's shape: each
  ``data-ref`` resolves and equals this test's own formatter); the McNemar counts and
  p, the pair counts and the ledger count equal the block's values;
* **a synthetic-cohort compare** (the prior from ``proofpack.synthetic.perturb_scores``,
  recipe recorded there) renders every section, T2-4 for every subgroup row, a ``met``
  paired criterion without the record string and a ``not_met`` one with it;
* **HTML injection** through every customer-text path that reaches T2 (the level labels,
  the criterion id, author, justification, the model name and versions) renders
  escaped, asserted on bytes; the ten CT-20..CT-29 slots carry no customer text in this
  build and print the placeholder box;
* **the draft label** beside every FDA AI-DSF anchor the page cites, and D4's verbatim
  impact caption on Table T2-5.
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from conftest import (
    confirmed_mapping,
    ephemeral_registry,
    make_cohort,
    make_criteria,
    write_csv,
    write_licence,
    write_yaml,
)
from proofpack.narrate.checker import resolve_pointer
from proofpack.narrate.templates import STATUS_WORDS
from proofpack.render import anchors
from proofpack.render import t2 as render_t2
from proofpack.render.html import write_t8
from proofpack.render.t7 import write_t7
from proofpack.resources import load_guidance_map
from proofpack.run import assemble_compare, write_run
from proofpack.synthetic import perturb_scores
from test_criteria import _criterion
from test_render_t1 import _Cells, _own_fmt
from test_render_t8 import FORBIDDEN_ON_PAGE, STATUS_TOKENS, footers_per_page, text_nodes, words

pytestmark = pytest.mark.day10

REPO = Path(__file__).resolve().parent.parent
F5 = REPO / "tests" / "fixtures" / "f5"
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "T2.html"
DRAFT_LABEL = "draft guidance (January 2025), not for implementation"
MASKED_MANIFEST = {
    "run_id": "test-only-compare",
    "started": "2026-09-25T00:00:00Z",
    "duration_s": None,
    "mapping_sha256": "0" * 64,
    "numpy": "x.y.z",
    "scipy": "x.y.z",
    "python": "3",
    "platform": "test",
    "reference_platform": False,
}
PAIRED = "paired_difference_vs_prior"


def compare_document(base: Path, new: Path, prior: Path, crit: Path) -> dict[str, Any]:
    """``assemble_compare`` under its own empty home with the test licence, written and
    read back, so the page is a function of ``run.json``."""
    home = base / "home"
    home.mkdir()
    write_licence(home / "proofpack.lic")
    mp = pytest.MonkeyPatch()
    mp.setenv("PROOFPACK_HOME", str(home))
    try:
        confirmed_mapping(new)
        outcome = assemble_compare(
            new, prior, crit, registry=ephemeral_registry(), ledger_home=home
        )
        target = write_run(outcome, base / "pack")
    finally:
        mp.undo()
    return json.loads(target.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def document(tmp_path_factory) -> dict[str, Any]:
    base = tmp_path_factory.mktemp("t2f5")
    for name in ("f5_new.csv", "f5_prior.csv", "criteria.yaml"):
        shutil.copy(F5 / name, base / name)
    doc = compare_document(base, base / "f5_new.csv", base / "f5_prior.csv", base / "criteria.yaml")
    doc["manifest"].update(MASKED_MANIFEST)
    return doc


@pytest.fixture(scope="module")
def page(document) -> str:
    return render_t2.render_t2(document)


# ------------------------------------------------------------------ golden, furniture


def test_golden_t2_matches_the_committed_render(document):
    out = render_t2.render_t2(document).replace("\r\n", "\n")
    if os.environ.get("PROOFPACK_REGEN_GOLDEN") == "1":
        GOLDEN.write_bytes(out.encode("utf-8"))
    assert GOLDEN.exists(), "regenerate with PROOFPACK_REGEN_GOLDEN=1"
    assert out == GOLDEN.read_bytes().decode("utf-8").replace("\r\n", "\n")
    assert render_t2.render_t2(document) == render_t2.render_t2(document)


def test_the_nine_sections_are_present_in_d4_order(page):
    ids = re.findall(r'<h2 id="t2-s(\d)">', page)
    assert ids == [str(i) for i in range(0, 9)]
    subs = re.findall(r'<h3 id="t2-s4-(\d)">', page)
    assert subs == [str(i) for i in range(1, 8)]


def test_the_footer_is_on_every_page_and_once_in_print(page):
    sections = page.count('<section class="page')
    assert sections == 5
    assert footers_per_page(page) == [1] * sections
    assert page.count('class="print-footer"') == 1
    assert page.count("no regulator has endorsed this tool.") >= sections + 1


def test_every_pccp_anchor_is_labelled_from_the_map_and_every_aidsf_anchor_is_draft(page):
    notes = re.findall(
        r'<aside class="margin-note( draft)?">maps to <a href="#([A-Z0-9_]+)">([^<]*)</a>', page
    )
    cited = {i for _, i, _ in notes}
    for group in render_t2.T2_ANCHORS.values():
        assert set(group) <= cited
    rows = {r["internal_id"]: r for r in load_guidance_map()}
    for draft, internal_id, label in notes:
        assert label == anchors.label_for(rows[internal_id]), internal_id
        assert bool(draft) is internal_id.startswith("FDA_AIDSF_")
        if internal_id.startswith("FDA_PCCP_"):
            assert "2024-12-04, updated 2025-08-18" in label and "final" in label
    # the guidance table: every AI-DSF anchor the document's claims cite carries the label
    table = re.findall(
        r'<tr id="([A-Z0-9_]+)"( class="draft")?><td class="mono">[^<]*</td><td>([^<]*)</td>', page
    )
    aidsf = [(i, d, label) for i, d, label in table if i.startswith("FDA_AIDSF_")]
    assert aidsf and all(d and DRAFT_LABEL in label for _, d, label in aidsf)
    assert all(not d for i, d, _ in table if not i.startswith("FDA_AIDSF_"))


def test_the_placeholder_box_prints_for_each_of_the_ten_ct_slots(page, document):
    slots = re.findall(
        r'<div class="placeholder" data-slot="(CT-\d+)">\[CUSTOMER TEXT REQUIRED - ', page
    )
    assert slots == [f"CT-{i}" for i in range(20, 30)]
    assert 'data-count="outstanding">10<' in page
    assert "INCOMPLETE - customer sections outstanding: 10" in page
    assert page.count('<span class="label">Manufacturer text - justification</span>') == 2
    assert render_t2.IMPACT_CAPTION == (
        "inputs to the manufacturer's impact assessment; no benefit-risk conclusion is drawn"
    )
    caption = re.search(r"<caption>Table T2-5 - quantitative deltas: ([^<]*)</caption>", page)
    assert caption.group(1) == render_t2.IMPACT_CAPTION.replace("'", "&#39;")


# ------------------------------------------------------------------ the verdict grep


def test_status_words_only_in_status_elements_and_the_record_string_only_on_not_met_rows(
    page, document
):
    status_hits, forbidden = [], []
    for text, scope in text_nodes(page):
        ws = words(text)
        if ws & {"met", "assessable"} and not ({"status", "customer-text"} & scope):
            status_hits.append((text.strip()[:60], scope))
        hit = ws & FORBIDDEN_ON_PAGE
        if "status" in scope:
            hit -= STATUS_TOKENS
        if hit and not ({"disclaimer", "customer-text"} & scope):
            forbidden.append((sorted(hit), text.strip()[:60], scope))
    assert status_hits == []
    assert forbidden == []
    record = render_t2.NOT_MET_RECORD
    assert record == "record of criterion not met (PCCP §VII.B(3) requires recording)"
    spans = re.findall(r'<span class="status record">([^<]*)</span>', page)
    assert spans == [record]  # once: C2's row of T2-3 (no subgroup paired criterion)
    assert page.count(record) == 1
    row = re.search(r'<tr data-metric="accuracy" data-op="op1">(.*?)</tr>', page, re.S).group(1)
    assert record in row and "criterion not met" in row
    for other in re.findall(r'<tr data-metric="(?!accuracy)[^"]*"[^>]*>(.*?)</tr>', page, re.S):
        assert record not in other
    cells = re.findall(r'<td class="status">(.*?)</td>', page, re.S)
    assert cells and all(
        re.match("|".join(map(re.escape, STATUS_WORDS.values())), c) for c in cells
    )
    assert "consistent" not in words(re.sub(r"<[^>]+>", " ", page))


# ------------------------------------------------------------------ every number


def test_every_printed_number_cell_traces_to_run_json(page, document):
    parser = _Cells()
    parser.feed(page)
    assert len(parser.cells) >= 40
    for c in parser.cells:
        if c["ref"] == "":
            assert c["text"] == "—", c  # the prior subgroup estimates, not computed
            continue
        found, num = resolve_pointer(document, c["ref"])
        assert found, c
        assert c["text"] == _own_fmt(num, c["kind"], c["facet"]), c
    refs = {c["ref"] for c in parser.cells}
    for ref in (
        "/comparison/differences/op1/accuracy/number",
        "/comparison/differences/auroc/number",
        "/comparison/differences/brier/number",
        "/comparison/differences/slope/number",
        "/comparison/prior/overall/op1/sensitivity",
        "/overall/op1/sensitivity",
        "/comparison/subgroups/0/differences/op1/sensitivity/number",
        "/comparison/subgroups/1/differences/auroc/number",
    ):
        assert ref in refs, ref
    mc = document["comparison"]["mcnemar"]["op1"]
    row = re.search(r'<tr data-metric="accuracy" data-op="op1">(.*?)</tr>', page, re.S).group(1)
    assert f'<td class="num">{mc["b"]} / {mc["c"]}</td>' in row
    assert f'<td class="num">{mc["p"]:.3f} (exact)</td>' in row
    assert f'data-count="n_pairs" colspan="2">{document["comparison"]["n_pairs"]}<' in page
    assert (
        f'data-count="prior_acceptance_runs">{document["comparison"]["ledger"]["prior_acceptance_runs"]}<'
        in page
    )
    # the sentence numbers: each PAIRED_DIFF sentence prints its own difference
    for claim in document["claims"]:
        if claim["template_id"] != "PAIRED_DIFF":
            continue
        sentence = re.search(rf'data-claim="{claim["claim_id"]}">(.*?)</p>', page, re.S).group(1)
        num = resolve_pointer(document, claim["value_refs"][0])[1]
        kind = (
            "difference_pp"
            if claim["metric_id"] in ("sensitivity", "specificity", "accuracy")
            else "difference_3dp"
        )
        assert _own_fmt(num, kind, "est") in re.sub(r"<[^>]+>", "", sentence)


# ------------------------------------------------------------------ the synthetic compare


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory) -> tuple[dict[str, Any], str, Path]:
    base = tmp_path_factory.mktemp("t2syn")
    cols = make_cohort(seed=20240101, n=400)
    prior_cols = dict(cols)
    prior_cols["score"] = perturb_scores(cols["score"], 20240101)
    new = write_csv(base / "new.csv", cols)
    prior = write_csv(base / "prior.csv", prior_cols)
    crit = make_criteria(
        criteria=[
            _criterion(id="Cmet", type=PAIRED, value=-0.5),
            _criterion(id="Cnot", metric="accuracy", type=PAIRED, value=0.5),
            _criterion(
                id="Csex", type=PAIRED, scope={"attribute": "sex", "level": "*"}, value=-0.5
            ),
            _criterion(id="Cpt", value=0.5),
        ],
        fairness=None,
    )
    crit["model"]["prior_version"] = "1.2"
    yml = write_yaml(base / "criteria.yaml", crit)
    doc = compare_document(base, new, prior, yml)
    return doc, render_t2.render_t2(doc), base


def test_the_synthetic_compare_renders_every_section_and_every_subgroup_row(synthetic):
    doc, page, base = synthetic
    assert doc["comparison"]["paired"] and doc["comparison"]["n_pairs"] == 400
    assert re.findall(r'<h2 id="t2-s(\d)">', page) == [str(i) for i in range(9)]
    table = re.search(r'<table class="subgroup-comparison">.*?</table>', page, re.S).group(0)
    levels = re.findall(
        r'<td class="customer-text">([^<]*)</td><td class="customer-text">([^<]*)</td>', table
    )
    assert levels == [(r["attribute"], r["level"]) for r in doc["subgroups"]]
    assert len(levels) >= 9  # sex, age bands, site (+ Unknown rows)
    assert 'colspan="' not in table.split("<tbody>", 1)[1] or "not computed (" in table
    assert doc["claim_rejections"] == []
    # each level row traces its cells
    parser = _Cells()
    parser.feed(page)
    for c in parser.cells:
        if c["ref"]:
            found, num = resolve_pointer(doc, c["ref"])
            assert found and c["text"] == _own_fmt(num, c["kind"], c["facet"]), c
    # T7 and T8 render from the same document (compare --templates T7,T8)
    assert write_t7(doc, base).exists() and write_t8(doc, base).exists()
    t8 = (base / "T8.html").read_text(encoding="utf-8")
    assert "paired difference vs prior version" in t8


def test_a_met_paired_row_prints_no_record_string_and_a_not_met_one_prints_it(synthetic):
    doc, page, _ = synthetic
    rows = {r["criterion_id"]: r for r in doc["criteria_results"] if r["scope"] == "overall"}
    assert rows["Cmet"]["status"] == "met" and rows["Cnot"]["status"] == "not_met"
    record = render_t2.NOT_MET_RECORD
    se_row = re.search(r'<tr data-metric="sensitivity" data-op="op1">(.*?)</tr>', page, re.S).group(
        1
    )
    acc_row = re.search(r'<tr data-metric="accuracy" data-op="op1">(.*?)</tr>', page, re.S).group(1)
    assert "criterion met" in se_row and record not in se_row and "Cmet" in se_row
    assert "criterion not met" in acc_row and record in acc_row and "Cnot" in acc_row
    sex_rows = [r for r in doc["criteria_results"] if r["criterion_id"] == "Csex"]
    assert sex_rows and all(r["status"] == "met" for r in sex_rows)
    table = re.search(r'<table class="subgroup-comparison">.*?</table>', page, re.S).group(0)
    assert table.count("Csex</span>") == len(sex_rows) and record not in table
    # the record sentences: one per not_met row, none for a met row
    records = [c for c in doc["claims"] if c["template_id"] == "CRITERION_NOT_MET_RECORD"]
    assert [c["criterion_id"] for c in records] == ["Cnot"]
    assert page.count('<span class="status">Record of criterion not met</span>: ') == 1
    trace = re.search(r'<table class="traceability">.*?</table>', page, re.S).group(0)
    assert trace.count("4.2 (paired comparison)") == 2 + len(sex_rows)
    assert trace.count("4.1 (criteria echo)") == 1


# ------------------------------------------------------------------ injection


def test_html_injection_through_every_customer_text_path_renders_escaped(tmp_path):
    label = '<script>alert(1)</script>&"‮S1'
    cols = make_cohort(n=160)
    cols["site"] = [label if s == "S1" else s for s in cols["site"]]
    prior_cols = dict(cols)
    prior_cols["score"] = perturb_scores(cols["score"], 20240101)
    new = write_csv(tmp_path / "new.csv", cols)
    prior = write_csv(tmp_path / "prior.csv", prior_cols)
    crit = make_criteria(
        criteria=[
            {
                "id": "C<i>",
                "metric": "sensitivity",
                "type": PAIRED,
                "operating_point": "op1",
                "scope": {"attribute": "site", "level": "*"},
                "statistic": "ci_lower_bound",
                "comparator": ">=",
                "value": 0.5,
                "author": "<b>Dr</b> & co",
                "date": "2026-01-01",
                "justification": '<img src=x onerror=alert(2)> & "q"',
            }
        ],
        fairness=None,
    )
    crit["model"]["name"] = '<i>Model</i> & "x"'
    crit["model"]["prior_version"] = "<u>1.2</u>"
    crit["model"]["version"] = "1.3<b>"
    yml = write_yaml(tmp_path / "criteria.yaml", crit)
    doc = compare_document(tmp_path, new, prior, yml)
    out = render_t2.render_t2(doc).encode("utf-8")
    assert b"<script>" not in out and b"<img" not in out and b"<b>Dr" not in out
    assert b"<u>" not in out and b"1.3<b>" not in out
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in out  # the level label
    assert b"&lt;b&gt;Dr&lt;/b&gt; &amp; co" in out  # the author
    assert b"&lt;img src=x onerror=alert(2)&gt;" in out  # the justification
    assert b"&lt;i&gt;Model&lt;/i&gt; &amp; &#34;x&#34;" in out  # the model name
    assert b"&lt;u&gt;1.2&lt;/u&gt;" in out and b"1.3&lt;b&gt;" in out  # the versions
    assert b"C&lt;i&gt;" in out  # the criterion id
    assert b"\xe2\x80\xae" not in out and b"&#x202e;" in out
    assert out.count(b"<i>") == 0
    # the CT slots hold no customer text in this build: nothing else reaches them
    for i in range(20, 30):
        assert f'data-slot="CT-{i}">[CUSTOMER TEXT REQUIRED - '.encode() in out


def test_t2_refuses_a_run_document(tmp_path):
    from assembler import assemble

    doc = assemble(make_cohort(n=120), make_criteria(criteria=[], fairness=None))
    with pytest.raises(ValueError, match="compare document"):
        render_t2.render_t2(doc)
    doc2 = copy.deepcopy(doc)
    doc2["comparison"] = None
    with pytest.raises(ValueError):
        render_t2.render_t2(doc2)
