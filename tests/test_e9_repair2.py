"""Build day 9, repair round 2 (lens 2 fresh attack and regression, 23 September 2026).

Each test feeds the input a lens fed and asserts the figure it measured. The tests marked
"fails at dd94874" below were run in a ``dd94874`` worktree with ``PYTHONPATH`` forced; the
first ``E`` line of each is in the repair note. The two marked "pin" hold a branch lens 2
found correct and untested (RG-N2); they pass at ``dd94874``.

* **FA-B1** (fails at dd94874) - on ``cohort_with_a_thirty_row_site()`` with ``CRITERIA``,
  ``FAIRNESS`` and a second operating point ``op2`` (threshold 0.3, rule ``>=``), each of
  the 92 ``SUBGROUP_ESTIMATE_WITH_DIFF`` / ``SUBGROUP_ESTIMATE`` / ``FAIRNESS_GAP``
  sentences on T1 names its claim's operating point;
* **FA-N1, FA-N2** (fail at dd94874) - T7's "printed as detail" and the calibration
  sentence "No target is compared to ..." are gone, on a document whose T1 compares
  ``C_slope`` to the calibration slope (repair 3 deleted the z/p sentence repair 2 wrote
  in their place: lens-3 FA-N3, ``test_e9_repair3.py``);
* **FA-N3, FA-N4 / RG-N1** (fails at dd94874) - the repair-1 test name and module
  docstring the lenses found overclaiming;
* **FA-N6** (fails at dd94874) - with no licence and ``--format json`` the next-step line
  names ``--format json,html``; the licensed ``--format json`` line (pin);
* **FA-N7** (fails at dd94874) - F4's caption with every bin typed;
* F2's specificity half of the marker gate (pin).
"""

from __future__ import annotations

import copy
import html
import re
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import ephemeral_registry, make_criteria
from proofpack.cli import main
from proofpack.errors import EXIT_LICENCE, EXIT_OK
from proofpack.render import t1 as render_t1
from proofpack.render import t7 as render_t7
from test_criteria import CRITERIA, FAIRNESS, _criterion, cohort_with_a_thirty_row_site
from test_run_cli import _own_home, _prepare

pytestmark = pytest.mark.day9

REPO = Path(__file__).resolve().parent.parent
OP_BOUND = {"SUBGROUP_ESTIMATE", "SUBGROUP_ESTIMATE_WITH_DIFF", "FAIRNESS_GAP"}
OP = '<span class="customer-text inline">{}</span>'


@pytest.fixture(scope="module")
def two_op() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    crit["operating_points"].append(
        {"id": "op2", "threshold": 0.3, "rule": ">=", "provenance": "prespecified_sap"}
    )
    return assemble(cohort_with_a_thirty_row_site(), crit)


def _claim_paragraphs(page: str) -> dict[str, str]:
    return dict(re.findall(r'<p class="claim" data-claim="([^"]+)">(.*?)</p>', page, re.S))


# ------------------------------------------------------------------ FA-B1


def test_a_two_operating_point_t1_names_the_operating_point_in_each_bound_sentence(two_op):
    page = render_t1.render_t1(two_op)
    printed = _claim_paragraphs(page)
    counts: dict[str, int] = {}
    unnamed = []
    for claim in two_op["claims"]:
        op, tid = claim.get("operating_point"), claim["template_id"]
        if op is None or claim["claim_id"] not in printed:
            continue
        counts[tid] = counts.get(tid, 0) + 1
        sentence = printed[claim["claim_id"]]
        plain = html.unescape(re.sub(r"<[^>]+>", "", sentence))
        if not re.search(rf"(?<![\w-]){re.escape(op)}(?![\w-])", plain):
            unnamed.append((claim["claim_id"], tid))
        if tid in OP_BOUND and f"at operating point {OP.format(op)}" not in sentence:
            unnamed.append((claim["claim_id"], tid))
    # the lens's count of the three templates on this page is 60 + 30 + 2; every claim
    # printed on T1 with an operating point is counted, not only those three
    assert counts == {
        "OVERALL_ESTIMATE": 26,
        "SUBGROUP_ESTIMATE_WITH_DIFF": 60,
        "SUBGROUP_ESTIMATE": 30,
        "CRITERION_STATUS": 8,
        "FAIRNESS_GAP": 2,
    }
    assert unnamed == []
    age, lv, ref = OP.format("age"), OP.format("0-40"), OP.format("40-65")
    for op, k in (("op1", "30/38 (78.9%ᶜ)"), ("op2", "36/38 (94.7%)")):
        assert f"For {age} = {lv} at operating point {OP.format(op)}, sensitivity was {k}" in page
    f, m = OP.format("F"), OP.format("M")
    # repair 3 (lens-3 FA-N1): the operating-point clause moved after the colon
    for op, gap in (("op1", "+7.0"), ("op2", "+6.4")):
        assert f"For {f} versus {m}: at operating point {OP.format(op)}, TPR gap {gap}" in page
    assert ref in page


# ------------------------------------------------------------------ FA-N1 / FA-N2


def test_t7_prints_no_z_p_location_sentence_and_no_calibration_target_sentence():
    # repair 3 (lens-3 FA-N3): repair 2's sentence "z and the two-sided p are written to
    # run.json beside the difference" printed on clustered T7s, whose detail is empty; it
    # is deleted, and this test (renamed) now asserts it absent
    crit = make_criteria(
        criteria=[
            _criterion(id="C_slope", metric="calibration_slope", operating_point=None, value=0.8)
        ],
        fairness=None,
    )
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    row = doc["criteria_results"][0]
    assert (row["criterion_id"], row["status"]) == ("C_slope", "met")
    t1 = html.unescape(re.sub(r"<[^>]+>", "", render_t1.render_t1(doc)))
    assert (
        "Criterion C_slope (calibration slope, overall, CI lower bound >= 0.8; A, 2026-01-01): "
        "observed 1.349 [1.056, 1.642] - criterion met." in t1
    )
    t7 = render_t7.render_t7(doc)
    assert "No target is compared to" not in t7
    assert "printed as detail" not in t7
    assert "z and the two-sided p are written to run.json beside the difference" not in t7
    detail = next(
        s["diff_vs_reference"]["auroc"]["detail"]
        for s in doc["subgroups"]
        if isinstance(s.get("diff_vs_reference"), dict)
    )
    assert {"z", "p_value"} <= set(detail)


# ------------------------------------------------------------------ FA-N3 / FA-N4 / RG-N1


def test_the_repair_1_file_carries_the_new_name_and_footer_clause_not_the_old():
    # renamed in repair 3 (lens-3 FA-N2 = RG-N1): the body reads four literal substrings of
    # test_e9_repair1.py, two absent and two present
    src = (REPO / "tests" / "test_e9_repair1.py").read_text(encoding="utf-8")
    assert "no_internal_decision_text" not in src
    assert "no_josh_or_open_decision" in src
    head = src.split('"""')[1]
    assert "each fails at\n``71b00d2`` (the pre-fix" not in head.replace("\r\n", "\n")
    assert "except ``test_the_footer_helper_counts_per_page_and_refuses_the_lens_mutant``" in (
        head.replace("\r\n", "\n").replace("\n", " ")
    )


# ------------------------------------------------------------------ FA-N6 (and RG-N2's pin)


def _run(tmp_path, monkeypatch, *extra: str, licence: bool) -> tuple[int, Path]:
    _own_home(tmp_path, monkeypatch, licence=licence)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    argv = ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out)]
    registry = ephemeral_registry() if licence else None
    return main([*argv, "--offline", *extra], registry=registry), out


def test_the_no_licence_json_next_step_names_format_json_html(tmp_path, monkeypatch, capsys):
    rc, out = _run(tmp_path, monkeypatch, "--templates", "T7", "--format", "json", licence=False)
    assert rc == EXIT_LICENCE
    printed = capsys.readouterr().out
    assert (
        "Next step: proofpack licence install FILE, then run again with --format json,html "
        "for T7.html (docs: /docs/run)" in printed
    )
    assert not list(out.glob("*.html"))


def test_pin_the_licensed_json_next_step_names_the_templates_asked(tmp_path, monkeypatch, capsys):
    rc, out = _run(tmp_path, monkeypatch, "--templates", "T1,T7", "--format", "json", licence=True)
    assert rc == EXIT_OK
    printed = capsys.readouterr().out
    assert (
        "Next step: run again with --format json,html for T1.html, T7.html (docs: /docs/run)"
        in printed
    )
    assert "T8.html" not in printed
    assert not list(out.glob("*.html"))


# ------------------------------------------------------------------ FA-N7


def test_f4_with_every_bin_typed_prints_no_bar_drawn(two_op):
    doc = copy.deepcopy(two_op)
    for b in doc["calibration"]["decile_curve"]:
        b["observed"]["number"].update(
            ci_lo=None, ci_hi=None, method="none", not_estimable_reason="boundary_estimate"
        )
    page = render_t1.render_t1(doc)
    f4 = re.search(r'<figure class="figure" id="F4">.*?</figure>', page, re.S).group(0)
    assert 'data-role="decile"' not in f4
    assert "no Number printed" not in f4
    assert "equal-mass bins; no bar drawn; not drawn, no interval: bin 1 n.e." in f4


# ------------------------------------------------------------------ RG-N2's F2 pin


def test_pin_f2_draws_no_marker_for_a_typed_specificity(two_op):
    doc = copy.deepcopy(two_op)
    doc["overall"]["op1"]["specificity"].update(
        ci_lo=None, ci_hi=None, method="none", not_estimable_reason="boundary_estimate"
    )
    page = render_t1.render_t1(doc)
    assert 'data-role="operating-point" data-op="op1"' not in page
    assert 'data-role="operating-point" data-op="op2"' in page
    assert "op1 (specificity n.e. (boundary_estimate))" in page
