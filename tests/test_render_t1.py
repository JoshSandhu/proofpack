"""Build day 9 (E9 item 3): T1, the FDA AI-DSF performance evidence attachment set.

* **golden**: ``tests/fixtures/golden/T1.html`` is the render of the synthetic document
  T8's and T7's goldens use (assembler, CRITERIA + FAIRNESS, B = 200, seed 20240101;
  ``run_id``, ``started``, ``duration_s`` fixed by the assembler, ``manifest.numpy`` set
  to ``x.y.z``), compared LF-normalised. Regenerate with ``PROOFPACK_REGEN_GOLDEN=1``;
* **footer on every page** by E8's count: ``<section class="page"`` equals the
  ``page-footer`` count, one ``print-footer``;
* **every FDA-draft anchor labelled**, and a map row planted without the qualifier in a
  temporary copy of the map makes ``render_t1`` refuse;
* **the verdict grep** over the rendered text: the status words only inside ``.status``;
  the forbidden words only inside the disclaimer and the customer's own text;
* **twenty-three cells listed below** (and every other ``data-ref`` cell) equal the
  Number of ``run.json`` their pointer names, re-formatted by this test's own formatter
  from D4 section 1.2's rules (not :mod:`proofpack.render.format`), on a ``proofpack run
  --templates T1`` output;
* **HTML injection** through the level labels, the justification, the author and the
  model name renders escaped (asserted on bytes);
* the placeholder rule (no empty heading; one box per outstanding slot, and the cover
  count equals them), ``calibration: null`` beside its reason (DEC-36), the IPA tier
  (DEC-35) and the clustered calibration cell with its tier (DEC-34).
"""

from __future__ import annotations

import copy
import csv
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import ephemeral_registry, make_cohort, make_criteria
from proofpack.cli import main
from proofpack.errors import EXIT_OK, EXIT_WARNINGS
from proofpack.narrate.checker import resolve_pointer
from proofpack.narrate.templates import STATUS_WORDS
from proofpack.render import anchors
from proofpack.render import t1 as render_t1
from proofpack.resources import load_guidance_map
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site
from test_render_t8 import FORBIDDEN_ON_PAGE, STATUS_TOKENS, text_nodes, words
from test_run_cli import _own_home, _prepare

pytestmark = pytest.mark.day9

REPO = Path(__file__).resolve().parent.parent
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "T1.html"
NUMPY_MASK = "x.y.z"
DRAFT_LABEL = "draft guidance (January 2025), not for implementation"


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    doc["manifest"]["numpy"] = NUMPY_MASK
    return doc


@pytest.fixture(scope="module")
def page(document) -> str:
    return render_t1.render_t1(document)


def test_golden_t1_matches_the_committed_render(document):
    out = render_t1.render_t1(document).replace("\r\n", "\n")
    if os.environ.get("PROOFPACK_REGEN_GOLDEN") == "1":
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_bytes(out.encode("utf-8"))
    assert GOLDEN.exists(), "regenerate with PROOFPACK_REGEN_GOLDEN=1"
    assert out == GOLDEN.read_bytes().decode("utf-8").replace("\r\n", "\n")
    assert render_t1.render_t1(document) == render_t1.render_t1(document)


def test_the_fifteen_sections_are_present_in_d4_order(page):
    ids = re.findall(r'<h2 id="t1-s(\d+)">', page)
    assert ids == [str(i) for i in range(1, 16)]


def test_the_footer_is_on_every_page_and_once_in_print(page):
    sections = page.count('<section class="page')
    assert sections == 9
    assert page.count('class="page-footer"') == sections
    assert page.count('class="print-footer"') == 1
    assert page.count("no regulator has endorsed this tool.") >= sections + 1


# ------------------------------------------------------------------ anchors


def test_every_fda_draft_anchor_is_labelled_in_every_margin_note(page):
    notes = re.findall(
        r'<aside class="margin-note( draft)?">maps to <a href="#([A-Z0-9_]+)">([^<]*)</a>', page
    )
    assert len(notes) >= 20
    for draft, internal_id, label in notes:
        is_draft = internal_id.startswith("FDA_AIDSF_")
        assert bool(draft) is is_draft, internal_id
        assert (DRAFT_LABEL in label) is is_draft, (internal_id, label)
    # the section anchors D4 section 2 names are all cited
    cited = {i for _, i, _ in notes}
    for group in render_t1.T1_ANCHORS.values():
        assert set(group) <= cited
    assert "FDA_AIDSF_MODEL_CARD" in cited and "FDA_AIDSF_PUBLIC_SUMMARY" in cited


def test_a_map_row_without_the_qualifier_makes_t1_refuse(document, tmp_path):
    rows = [dict(r) for r in load_guidance_map()]
    planted = next(r for r in rows if r["internal_id"] == "FDA_AIDSF_MODEL_CARD")
    planted["status"] = "draft"
    path = tmp_path / "guidance_map_v1.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with path.open(encoding="utf-8", newline="") as fh:
        tmp_map = list(csv.DictReader(fh))
    with pytest.raises(anchors.AnchorError, match="not for implementation"):
        render_t1.render_t1(document, guidance_map=tmp_map)


# ------------------------------------------------------------------ the verdict grep


def test_status_words_only_in_status_elements_and_no_forbidden_word_outside_exempt_text(page):
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
    spans = re.findall(r'<(?:td|span) class="status">([^<]*)</(?:td|span)>', page)
    assert set(spans) <= set(STATUS_WORDS.values()) and spans
    # the differences table names no consistency verdict
    assert "consistent" not in words(re.sub(r"<[^>]+>", " ", page))


# ------------------------------------------------------------------ twenty-three cells


_TIERS = {"not_evaluable_shown_for_transparency": "ᵃ", "very_low_precision": "ᵇ", "imprecise": "ᶜ"}


def _own_fmt(num: dict[str, Any] | None, kind: str, facet: str) -> str:
    """This test's formatter, from D4 section 1.2 directly: a proportion's k/n and one
    decimal in percent, three decimals otherwise, signed percentage points for a
    difference, U+2212 minus; ``n.e. (<reason>)`` without a digit from est."""
    minus = "−"

    def plain(x, places):
        return f"{x:.{places}f}".replace("-", minus)

    def signed(x, places):
        s = f"{abs(x):.{places}f}"
        if float(s) == 0.0:
            return s
        return (minus if x < 0 else "+") + s

    def one(x):
        return {
            "proportion": plain(x * 100, 1),
            "three_dp": plain(x, 3),
            "difference_pp": signed(x * 100, 1),
            "difference_3dp": signed(x, 3),
        }[kind]

    tiers = "".join(_TIERS[f] for f in (num or {}).get("flags") or [] if f in _TIERS)
    has_ci = (
        num is not None
        and not num.get("suppressed")
        and num.get("not_estimable_reason") is None
        and num.get("ci_lo") is not None
    )
    if facet == "kn":
        return f"{num['k']}/{num['n']}" if num and num.get("k") is not None else "—"
    if not has_ci:
        ne = f"n.e. ({(num or {}).get('not_estimable_reason') or 'no_interval'})" + tiers
        return {"ci": "no interval"}.get(facet, ne)
    est, lo, hi = num["est"], num["ci_lo"], num["ci_hi"]
    if facet == "est":
        return one(est) + tiers
    if facet == "ci":
        return f"[{one(lo)}, {one(hi)}]"
    head = f"({one(est)}%)" if kind == "proportion" else one(est)
    if kind == "proportion" and num.get("k") is not None:
        head = f"{num['k']}/{num['n']} {head}"
    return f"{head} [{one(lo)}, {one(hi)}]" + tiers


class _Cells(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cells: list[dict[str, str]] = []
        self._open: dict[str, str] | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "td" and "data-ref" in a and "data-kind" in a:
            self._open = {
                "ref": a["data-ref"],
                "kind": a["data-kind"],
                "facet": a["data-facet"],
                "text": "",
            }

    def handle_data(self, data):
        if self._open is not None:
            self._open["text"] += data

    def handle_endtag(self, tag):
        if tag == "td" and self._open is not None:
            self.cells.append(self._open)
            self._open = None


@pytest.fixture(scope="module")
def cli_run(tmp_path_factory) -> tuple[dict[str, Any], str]:
    base = tmp_path_factory.mktemp("t1cli")
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
                "--templates",
                "T1",
            ],
            registry=ephemeral_registry(),
        )
        assert rc in (EXIT_OK, EXIT_WARNINGS)
        doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
        page = (out / "T1.html").read_bytes()
        assert b"\r\n" not in page
        return doc, page.decode("utf-8")
    finally:
        mp.undo()


def _index(doc, attribute, level):
    return next(
        i
        for i, r in enumerate(doc["subgroups"])
        if r["attribute"] == attribute and r["level"] == level
    )


def test_twenty_three_listed_cells_equal_the_run_json_number_by_d4_rules(cli_run):
    doc, page = cli_run
    assert page == render_t1.render_t1(doc)  # a pure function of run.json
    parser = _Cells()
    parser.feed(page)
    by_ref: dict[tuple[str, str], str] = {}
    for c in parser.cells:
        by_ref.setdefault((c["ref"], c["facet"]), c["text"])
    f = _index(doc, "sex", "F")
    a0 = _index(doc, "age", "0-40")
    listed = [
        ("/overall/op1/sensitivity", "proportion", "kn"),
        ("/overall/op1/sensitivity", "proportion", "est"),
        ("/overall/op1/sensitivity", "proportion", "ci"),
        ("/overall/op1/specificity", "proportion", "ci"),
        ("/overall/op1/ppv", "proportion", "est"),
        ("/overall/op1/npv", "proportion", "ci"),
        ("/overall/op1/accuracy", "proportion", "kn"),
        ("/overall/op1/lr_pos", "three_dp", "est"),
        ("/overall/op1/lr_neg", "three_dp", "ci"),
        ("/overall/op1/dor", "three_dp", "ci"),
        ("/overall/op1/f1", "three_dp", "est"),
        ("/overall/threshold_free/auroc", "three_dp", "cell"),
        ("/overall/threshold_free/prevalence", "proportion", "cell"),
        ("/calibration/oe/number", "three_dp", "cell"),
        ("/calibration/slope/number", "three_dp", "cell"),
        ("/calibration/ipa/number", "three_dp", "cell"),
        ("/calibration/brier_ref/number", "three_dp", "cell"),
        ("/calibration/decile_curve/3/observed/number", "proportion", "cell"),
        (f"/subgroups/{f}/metrics/op1/sensitivity/number", "proportion", "cell"),
        (f"/subgroups/{f}/diff_vs_reference/op1/sensitivity/number", "difference_pp", "cell"),
        (f"/subgroups/{a0}/metrics/auroc/number", "three_dp", "cell"),
        (f"/subgroups/{a0}/diff_vs_reference/auroc/number", "difference_3dp", "cell"),
        ("/fairness/gaps/0/operating_points/op1/tpr_gap/number", "difference_pp", "cell"),
    ]
    assert len(listed) == 23
    for ref, kind, facet in listed:
        found, num = resolve_pointer(doc, ref)
        assert found, ref
        assert (ref, facet) in by_ref, (ref, facet)
        assert by_ref[(ref, facet)] == _own_fmt(num, kind, facet), (ref, facet)
    # and every other Number cell on the page, by the same formatter
    assert len(parser.cells) >= 120
    for c in parser.cells:
        found, num = resolve_pointer(doc, c["ref"])
        if not found or num is None:
            assert c["text"].startswith("not computed") or c["text"] == "n.e.", c
            continue
        assert c["text"] == _own_fmt(num, c["kind"], c["facet"]), c


# ------------------------------------------------------------------ injection


def test_html_injection_through_every_customer_text_slot_renders_escaped():
    label = '<script>alert(1)</script>&"‮S1'
    cols = make_cohort(n=160)
    cols["site"] = [label if s == "S1" else s for s in cols["site"]]
    crit = make_criteria(
        criteria=[
            {
                "id": "C<i>",
                "metric": "sensitivity",
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
    doc = assemble(cols, crit)
    out = render_t1.render_t1(doc).encode("utf-8")
    assert b"<script>" not in out and b"<img" not in out and b"<b>Dr" not in out
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in out  # the level label
    assert b"&lt;b&gt;Dr&lt;/b&gt; &amp; co" in out  # the author
    assert b"&lt;img src=x onerror=alert(2)&gt;" in out  # the justification
    assert b"&lt;i&gt;Model&lt;/i&gt; &amp; &#34;x&#34;" in out  # the model name
    assert b"C&lt;i&gt;" in out  # the criterion id
    assert b"\xe2\x80\xae" not in out and b"&#x202e;" in out
    assert out.count(b"<i>") == 0


# ------------------------------------------------------------------ rules


def test_no_heading_is_empty_and_each_outstanding_slot_prints_the_placeholder(page, document):
    body = page.split("<body>", 1)[1]
    chunks = re.split(r"<h[23][^>]*>", body)[1:]
    for chunk in chunks:
        after = chunk.split("</h", 1)[1]
        nxt = re.split(r"<h[23][^>]*>|</section>", after)[0]
        content = re.sub(r'<aside class="margin-note[^"]*">.*?</aside>', "", nxt, flags=re.S)
        assert re.sub(r"<[^>]+>|\s", "", content), chunk[:80]
    slots = render_t1.customer_slots(document)
    outstanding = [s for s in slots.values() if not s["filled"]]
    assert page.count('class="placeholder" data-slot="CT-') == len(outstanding) == 11
    assert "INCOMPLETE - customer sections outstanding: 11" in page
    assert '<td class="num" data-count="outstanding">11</td>' in page
    for s in outstanding:
        assert f"[CUSTOMER TEXT REQUIRED - {s['title']}; ProofPack does not draft this]" in page
    # CT-10 fills from criteria.yaml when every declared subgroup names its source
    crit = make_criteria(criteria=[], fairness=None)
    for s in crit["subgroups"]:
        s["source"] = f"SAP v2 {s['attribute']}"
    doc = assemble(make_cohort(n=160), crit)
    out = render_t1.render_t1(doc)
    assert "Manufacturer text - pre-specification source" in out
    assert "sex: SAP v2 sex; age: SAP v2 age; site: SAP v2 site" in out
    assert "INCOMPLETE - customer sections outstanding: 10" in out


def test_calibration_null_prints_beside_its_reason():
    crit = make_criteria(
        criteria=[], fairness=None, score={"type": "logit", "orientation": "higher_is_positive"}
    )
    doc = assemble(make_cohort(n=160), crit)
    assert doc["calibration"] is None
    out = render_t1.render_t1(doc)
    assert (
        'calibration: null - reason <span class="mono">score_not_probability</span> (score '
        "declared logit, higher_is_positive)." in out
    )
    assert "Calibration statistics are not computed because the score was declared as" in out
    assert 'data-quantity="oe"' not in out


def test_the_ipa_prints_its_row_tier_and_the_dec35_footnote(document):
    doc = copy.deepcopy(document)
    doc["calibration"]["ipa"]["number"]["flags"] = ["very_low_precision", "imprecise"]
    out = render_t1.render_t1(doc)
    row = re.search(r'<tr data-quantity="ipa">(.*?)</tr>', out, re.S).group(1)
    assert "ᵇᶜ</td>" in row
    assert "The IPA row's tier superscript (ᵇᶜ) is the proportion tier applied to the IPA" in out


def test_a_clustered_run_prints_the_calibration_cells_with_their_tiers_dec34():
    cols = make_cohort(n=180, with_case_id=True)
    cols["case_id"] = [f"c{i // 3:06d}" for i in range(180)]
    crit = make_criteria(
        criteria=[], clustering={"unit": "case_id", "declared_by": "test"}, fairness=None
    )
    doc = assemble(cols, crit)
    assert doc["flow"]["clustered"] is True
    out = render_t1.render_t1(doc)
    num = doc["calibration"]["intercept_large"]["number"]
    row = re.search(r'<tr data-quantity="intercept_large">(.*?)</tr>', out, re.S).group(1)
    tiers = "".join(_TIERS[f] for f in num["flags"] if f in _TIERS)
    assert f">{_own_fmt(num, 'three_dp', 'cell')}</td>" in row
    assert row.count(tiers) >= 1 if tiers else True
    assert "cluster_bootstrap_percentile" in row
    assert "Under the clustered plan every interval above is a cluster-bootstrap interval" in out
    assert "DEC-34" in out


def test_run_templates_t1_writes_t1_html_beside_run_json(cli_run):
    doc, page = cli_run
    assert page.startswith("<!DOCTYPE html>") and doc["manifest"]["run_id"][:8] in page
