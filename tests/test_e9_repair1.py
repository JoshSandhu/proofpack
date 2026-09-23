"""Build day 9, repair round 1 (lens 1 fresh attack and regression, 23 September 2026).

Each test feeds the input a lens fed and asserts the figure it measured. Each fails at
``71b00d2`` except ``test_the_footer_helper_counts_per_page_and_refuses_the_lens_mutant``,
which checks the test helper ``footers_per_page`` on a mutant it builds and passes there
(lens-2 FA-N4 / RG-N1); its pre-fix evidence is the lens's mutant planted in ``71b00d2``'s
``T1.html``, in the repair note. The pre-fix lines are in the repair note:

* **FA-B1 / RG-B2** - the page grep of ``test_render_t1`` (the words of
  ``test_render_t8.FORBIDDEN_ON_PAGE`` outside ``.status``, ``.disclaimer`` and
  ``.customer-text``) over T7 of the i.i.d. document, T7 of a clustered document (400 rows,
  ``case_id = c{i//2}``), the sample pack's T7 and T1 with every operating point's
  provenance ``derived_from_this_dataset``; and FA-N1's ``Josh`` / ``open decision``;
* **FA-B2** - on that clustered document the T1-10 / T1-11 captions, F4's bar method and
  T7's X1 paragraph name the methods of the Numbers they print;
* **FA-B3** - a Number with no interval is not plotted: F4's bin 1 on the clustered
  document; F5's reference line and F2's marker with a typed reason planted on the
  overall AUROC and the overall sensitivity of the i.i.d. document;
* **RG-B1** - F4's on-plot note reads ``calibration.curve_flag.minimum`` (150 planted);
* the sentences the lenses falsified (FA-N2, FA-N3 / RG-N13, FA-N10 parts, RG-N11) are
  gone from the shipped text, and the exit-4 next-step line names the templates asked.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import make_cohort, make_criteria
from proofpack.cli import main
from proofpack.errors import EXIT_LICENCE
from proofpack.narrate.templates import METHOD_PHRASES
from proofpack.render import html as render_html
from proofpack.render import t1 as render_t1
from proofpack.render import t7 as render_t7
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site
from test_render_t8 import FORBIDDEN_ON_PAGE, footers_per_page, text_nodes, words
from test_run_cli import _own_home, _prepare
from test_sample_pack import builds  # noqa: F401 - the module-scoped sample-pack fixture

pytestmark = pytest.mark.day9

REPO = Path(__file__).resolve().parent.parent
EXEMPT = {"status", "disclaimer", "customer-text"}


def forbidden_outside_exempt(page: str) -> list[tuple[list[str], str]]:
    """``test_render_t1``'s verdict grep: forbidden words outside the exempt scopes."""
    out = []
    for text, scope in text_nodes(page):
        hit = words(text) & FORBIDDEN_ON_PAGE
        if hit and not (EXEMPT & scope):
            out.append((sorted(hit), text.strip()[:80]))
    return out


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    return assemble(cohort_with_a_thirty_row_site(), crit)


@pytest.fixture(scope="module")
def clustered() -> dict[str, Any]:
    cols = make_cohort(n=400, with_case_id=True)
    cols["case_id"] = [f"c{i // 2}" for i in range(400)]
    crit = make_criteria(
        criteria=[], clustering={"unit": "case_id", "declared_by": "test"}, fairness=None
    )
    doc = assemble(cols, crit)
    assert doc["flow"]["clustered"] is True
    return doc


# ------------------------------------------------------------------ FA-B1 / RG-B2 / FA-N1


def test_t7_iid_and_clustered_carry_no_forbidden_word_and_no_josh_or_open_decision(
    document, clustered
):
    for doc in (document, clustered):
        page = render_t7.render_t7(doc)
        assert forbidden_outside_exempt(page) == []
        assert "Josh" not in page and "open decision" not in page
        assert "Every number here comes from a committed script" not in page
    # the clustered page carries the coverage section, where "effective" was printed
    assert "Cluster-bootstrap coverage" in render_t7.render_t7(clustered)


def test_the_sample_packs_t7_carries_no_forbidden_word(builds):  # noqa: F811
    a, _ = builds
    for name in ("T1.html", "T7.html", "T8.html"):
        page = (a / name).read_text(encoding="utf-8")
        assert forbidden_outside_exempt(page) == [], name


def test_t1_with_a_derived_threshold_carries_no_forbidden_word(document):
    doc = copy.deepcopy(document)
    for op in doc["declarations"]["operating_points"]:
        op["provenance"] = "derived_from_this_dataset"
    page = render_t1.render_t1(doc)
    assert forbidden_outside_exempt(page) == []
    assert (
        '<span class="provenance">derived from this dataset: the threshold was chosen on the '
        "same data its performance is estimated on</span>" in page
    )


# ------------------------------------------------------------------ FA-B2


def _captions(page: str, cls: str) -> list[str]:
    return re.findall(rf'<table class="{cls}"[^>]*>\s*<caption>(.*?)</caption>', page, re.S)


def test_a_clustered_t1_and_t7_name_the_methods_their_numbers_carry(clustered):
    page = render_t1.render_t1(clustered)
    t10, t11 = _captions(page, "subgroup"), _captions(page, "differences")
    assert len(t10) == 3 and len(t11) == 3
    for cap in t10:
        assert "Interval methods in this table: cluster bootstrap, percentile interval;" in cap
        assert "Wilson" not in cap and "DeLong" not in cap
    for cap in t11:
        assert "interval methods in this table: no interval method;" in cap
        assert "Newcombe" not in cap and "DeLong" not in cap
    f4 = re.search(r'<figure class="figure" id="F4">.*?</figure>', page, re.S).group(0)
    assert "bar interval: cluster bootstrap, percentile interval;" in f4
    x1 = re.search(r'<p class="x1">(.*?)</p>', render_t7.render_t7(clustered)).group(1)
    assert "Newcombe" not in x1 and "DeLong" not in x1
    assert x1.endswith('in this run: no interval method (<span class="mono">none</span>, 105).')


def test_an_iid_t1_caption_lists_the_methods_of_its_cells(document):
    page = render_t1.render_t1(document)
    tables = re.findall(r'<table class="subgroup".*?</table>', page, re.S)
    assert len(tables) == 3
    for table in tables:
        methods = set()
        for ref in re.findall(r'data-ref="([^"]+)"', table):
            node: Any = document
            for part in ref.strip("/").split("/"):
                node = node[int(part)] if isinstance(node, list) else node[part]
            methods.add(node["method"])
        expected = "; ".join(METHOD_PHRASES[m] for m in sorted(methods))
        assert f"Interval methods in this table: {expected};" in table


# ------------------------------------------------------------------ FA-B3


def test_a_decile_bin_with_a_typed_reason_is_not_plotted(clustered):
    bin1 = clustered["calibration"]["decile_curve"][0]["observed"]["number"]
    assert bin1["not_estimable_reason"] == "boundary_estimate" and bin1["est"] == 0.0
    page = render_t1.render_t1(clustered)
    f4 = re.search(r'<figure class="figure" id="F4">.*?</figure>', page, re.S).group(0)
    assert 'data-role="decile" data-bin="1"' not in f4
    assert f4.count('data-role="decile"') == 9 and f4.count('data-role="interval"') == 9
    assert "not drawn, no interval: bin 1 n.e. (boundary_estimate);" in f4


def test_f5_draws_no_reference_line_and_f2_no_marker_for_a_typed_reason(document):
    page = render_t1.render_t1(document)
    assert 'id="F5-sex-auroc"' in page
    assert re.search(r'id="F5-sex-auroc".*?data-role="reference"', page, re.S)
    assert 'data-role="operating-point" data-op="op1"' in page
    doc = copy.deepcopy(document)
    for num in (doc["overall"]["threshold_free"]["auroc"], doc["overall"]["op1"]["sensitivity"]):
        num.update(ci_lo=None, ci_hi=None, method="none", not_estimable_reason="boundary_estimate")
    out = render_t1.render_t1(doc)
    for metric in ("auroc", "sensitivity"):
        for attribute in ("sex", "age", "site"):
            fig = re.search(
                rf'<figure class="figure" id="F5-{attribute}-{metric}".*?</figure>', out, re.S
            ).group(0)
            assert 'data-role="reference"' not in fig
            assert "no reference line: the overall estimate is n.e. (boundary_estimate)" in fig
    assert 'data-role="operating-point"' not in out
    assert (
        "operating point(s) not drawn, a Number without an interval: op1 (sensitivity n.e. "
        "(boundary_estimate))" in out
    )


# ------------------------------------------------------------------ RG-B1


def test_the_f4_note_reads_the_curve_flag_minimum(document):
    assert isinstance(document["calibration"]["curve_flag"], dict)
    doc = copy.deepcopy(document)
    doc["calibration"]["curve_flag"]["minimum"] = 150
    page = render_t1.render_t1(doc)
    svg = re.search(r'<figure class="figure" id="F4">.*?</svg>', page, re.S).group(0)
    notes = re.findall(r'<text class="fig-text fig-note"[^>]*>([^<]*)</text>', svg)
    assert notes == ["150/150 convention: fewer than 150 events or non-events"]
    assert "200" not in notes[0]


# ------------------------------------------------------------------ falsified sentences


def test_the_sentences_repair_1_falsified_are_gone_from_the_shipped_text(document):
    t1 = render_t1.render_t1(document)
    t7 = render_t7.render_t7(document)
    t8 = render_html.render_t8(document)
    # FA-N2: two runs of one input differ at manifest.run_id, so no identical manifest hash
    assert "identical manifest hash" not in t7
    # FA-N3 / RG-N13: the engine prints no Clopper-Pearson interval
    for page in (t1, t8):
        assert "Clopper-Pearson alongside" not in page
    # FA-N10 (IPA): the footnote names a superscript only when the IPA row carries one
    assert document["calibration"]["ipa"]["number"]["flags"] == []
    assert "The IPA row&#39;s tier superscript" not in t1
    assert "The IPA row's tier superscript" not in t1
    src = REPO / "src" / "proofpack"
    fmt_src = (src / "render" / "format.py").read_text(encoding="utf-8")
    assert "state one figure one way" not in fmt_src
    sent_src = (src / "render" / "sentences.py").read_text(encoding="utf-8")
    assert "never shifts a number into another slot" not in sent_src


def test_the_exit_4_next_step_names_the_templates_asked(tmp_path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch, licence=False)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    argv = ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out)]
    rc = main([*argv, "--offline", "--templates", "T1,T7"], registry=None)
    assert rc == EXIT_LICENCE
    printed = capsys.readouterr().out
    assert "then run again for T1.html, T7.html (docs: /docs/run)" in printed
    assert "T8.html" not in printed


# ------------------------------------------------------------------ RG-N3


def test_the_footer_helper_counts_per_page_and_refuses_the_lens_mutant(document):
    page = render_t1.render_t1(document)
    assert footers_per_page(page) == [1] * 9
    # the lens's mutant: page 9's footer moved onto page 1; the totals still agree
    sections = page.split('<section class="page')
    footer = re.search(r'<footer class="page-footer">.*?</footer>', sections[9], re.S).group(0)
    sections[9] = sections[9].replace(footer, "", 1)
    sections[1] = sections[1].replace("</section>", footer + "</section>", 1)
    mutant = '<section class="page'.join(sections)
    assert mutant.count('class="page-footer"') == mutant.count('<section class="page')
    assert footers_per_page(mutant) == [2, 1, 1, 1, 1, 1, 1, 1, 0]
