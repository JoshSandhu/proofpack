"""Repair 2 of build day 8 (23 September 2026): regression tests for the lens-2 findings
FA-B1 / RG-B1 (a blank or indeterminate-valued ``y_pred`` on a table without a score
column), FA-B2 (Number pointers off the eight shapes, and the claim shapes sharing that
cause), FA-B3 (a fairness bound without a ``criteria`` list on T8), FA-B4 / RG-B2
(``free_text`` spellings) and RG-N2 / FA-N4 (H02 on ``y_pred`` beside a score column).
Each test names the literal input it feeds and the figure it asserts; the repair-2 note
quotes, per test, the first E line in a worktree at 657ef11 with PYTHONPATH forced.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import ephemeral_registry, make_cohort, make_criteria
from proofpack.cli import main
from proofpack.errors import EXIT_HALT, EXIT_OK, EXIT_WARNINGS, HaltError
from proofpack.gates import gate_h02
from proofpack.io import schema as schema_mod
from proofpack.io.declare import validate_dict
from proofpack.narrate import checker
from proofpack.narrate import claims as claims_mod
from proofpack.narrate.templates import LIBRARY
from proofpack.render import html as render_html
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site
from test_run_cli import _own_home, _prepare

pytestmark = pytest.mark.day8


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    return assemble(cohort_with_a_thirty_row_site(), crit)


def _code(claim: dict[str, Any], doc: dict[str, Any]) -> str | None:
    v = checker.check([claim], doc).verdicts[0]
    return None if v.accepted else v.reason_code


def _run(tmp_path: Path, cols: dict[str, list[Any]], crit: dict[str, Any]) -> tuple[int, Path]:
    csv_path, yml = _prepare(tmp_path, cols=cols, crit=crit)
    out = tmp_path / "pack"
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--offline"],
        registry=ephemeral_registry(),
    )
    return rc, out


# ------------------------------------------------- FA-B1 / RG-B1: a blank y_pred, no score


def _y_pred_only(n: int = 120) -> dict[str, list[Any]]:
    cols = make_cohort(n=n, with_y_pred=True)
    del cols["score"]
    return cols


def test_a_blank_y_pred_without_a_score_column_is_excluded_and_counted(tmp_path, monkeypatch):
    """Lens RG-B1's table: 120 rows, no score column, the ``y_pred`` of every even row
    blank. At 657ef11: ``analysed 120``, ``excluded_missing_score 0``, two-by-two
    ``{tp 21, fn 21, fp 7, tn 71}`` and the page cell ``21/42 (50.0%) [35.5, 64.5]``."""
    cols = _y_pred_only()
    cols["y_pred"] = ["" if i % 2 == 0 else v for i, v in enumerate(cols["y_pred"])]
    doc = assemble(cols, make_criteria(criteria=[], fairness=None))
    assert doc["flow"]["excluded_missing_score"] == 60 and doc["flow"]["analysed"] == 60
    assert doc["flow"]["excluded_missing_label"] == 0 and doc["flow"]["indeterminate"] == 0
    assert doc["overall"]["op1"]["two_by_two"] == {"tp": 21, "fn": 3, "fp": 7, "tn": 29}
    sens = doc["overall"]["op1"]["sensitivity"]
    assert (sens["k"], sens["n"]) == (21, 24)
    # lens FA-B1's table: the y_pred of the first 20 positives blank; 18/22, not 18/42
    cols2 = _y_pred_only()
    blanked = 0
    for i, v in enumerate(cols2["y_true"]):
        if v == "1" and blanked < 20:
            cols2["y_pred"][i] = None
            blanked += 1
    doc2 = assemble(cols2, make_criteria(fairness=None))
    assert doc2["flow"]["excluded_missing_score"] == 20 and doc2["flow"]["analysed"] == 100
    assert doc2["overall"]["op1"]["two_by_two"] == {"tp": 18, "fn": 4, "fp": 20, "tn": 58}
    sens2 = doc2["overall"]["op1"]["sensitivity"]
    assert (sens2["k"], sens2["n"]) == (18, 22)
    # beside a score column the score is the prediction input: 60 blank y_pred cells
    # change nothing (the lens's A9; unchanged by this repair and stated)
    cols3 = make_cohort(n=120, with_y_pred=True)
    cols3["y_pred"] = ["" if i % 2 == 0 else v for i, v in enumerate(cols3["y_pred"])]
    doc3 = assemble(cols3, make_criteria(criteria=[], fairness=None))
    assert doc3["flow"]["excluded_missing_score"] == 0 and doc3["flow"]["analysed"] == 120
    assert doc3["overall"]["op1"]["two_by_two"] == {"tp": 34, "fn": 8, "fp": 20, "tn": 58}
    # through the CLI: the page prints the 60 analysed rows' cell, W10 is the one warning
    _own_home(tmp_path, monkeypatch)
    rc, out = _run(tmp_path, cols, make_criteria(fairness=None))
    assert rc == EXIT_WARNINGS
    run = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert run["flow"]["excluded_missing_score"] == 60 and run["flow"]["analysed"] == 60
    assert run["overall"]["op1"]["two_by_two"] == {"tp": 21, "fn": 3, "fp": 7, "tn": 29}
    assert [w["code"] for w in run["warnings"]] == ["W10"] and run["halts"] == []
    page = (out / "T8.html").read_text(encoding="utf-8")
    cells = re.findall(r'<td class="num observed">([^<]*)</td>', page)
    assert cells == ["21/24 (87.5%) [69.0, 95.7]ᵇᶜ"]
    assert "21/42" not in page
    assert 'data-count="rows_analysed">60</td>' in page


def test_a_y_pred_carrying_the_declared_indeterminate_value_is_an_indeterminate_row():
    """Lens FA-B1 (A6b): a ``y_pred`` equal to a declared indeterminate value landed in
    ``fn`` / ``tn`` with ``flow.indeterminate 0``. The value fed is ``indeterminate``
    (``NA`` is a missing token of ``schema_v1.json`` and is read as blank by the day-1
    loader, lens FA-N7's item 9; recorded, outside this repair)."""
    crit = make_criteria(
        criteria=[],
        fairness=None,
        indeterminates={"policy": "report_both_ways", "values": ["indeterminate"]},
    )
    cols = _y_pred_only()
    cols["y_pred"] = ["indeterminate" if i % 10 == 0 else v for i, v in enumerate(cols["y_pred"])]
    decl = validate_dict(crit)
    table = schema_mod.validate(schema_mod.table_from_columns(cols), period=None)
    assert gate_h02(table, decl) is None
    doc = assemble(cols, crit)
    assert doc["flow"]["indeterminate"] == 12 and doc["flow"]["analysed"] == 108
    assert doc["flow"]["excluded_missing_score"] == 0
    assert doc["overall"]["op1"]["two_by_two"] == {"tp": 34, "fn": 7, "fp": 17, "tn": 50}
    # the same twelve rows marked through y_true take the same path
    cols_t = _y_pred_only()
    cols_t["y_true"] = [
        "indeterminate" if i % 10 == 0 else v for i, v in enumerate(cols_t["y_true"])
    ]
    doc_t = assemble(cols_t, crit)
    assert (doc_t["flow"]["indeterminate"], doc_t["flow"]["analysed"]) == (12, 108)
    assert doc_t["overall"]["op1"]["two_by_two"] == doc["overall"]["op1"]["two_by_two"]


# ------------------------------------------------- RG-N2 / FA-N4: H02 on y_pred with a score


def test_h02_on_y_pred_fires_beside_a_score_column(tmp_path, monkeypatch):
    """The repair-1 test feeds ``yes`` / ``no`` without a score column; this one feeds the
    same column beside the score (the README's "with or without a score column" had no
    with-score run on record: lens RG-N2, FA-N4's surviving mutant)."""
    cols = make_cohort(n=120, with_y_pred=True)
    cols["y_pred"] = ["yes" if v == "1" else "no" for v in cols["y_pred"]]
    decl = validate_dict(make_criteria())
    table = schema_mod.validate(schema_mod.table_from_columns(cols), period=None)
    assert table.score is not None
    with pytest.raises(HaltError) as ei:
        gate_h02(table, decl)
    assert ei.value.code == "H02"
    assert ei.value.detail == {"column": "y_pred", "n_unknown_values": 2, "n_declared": 2}
    _own_home(tmp_path, monkeypatch)
    rc, out = _run(tmp_path, cols, make_criteria())
    assert rc == EXIT_HALT and not out.exists()


# ------------------------------------------------- FA-B2: binding off the eight shapes


def _number_paths(doc: dict[str, Any]) -> list[str]:
    def walk(node: Any, path: str):
        if isinstance(node, dict):
            if checker.is_number_object(node):
                yield path
            for k, v in node.items():
                yield from walk(v, f"{path}/{str(k).replace('~', '~0').replace('/', '~1')}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, f"{path}/{i}")

    return list(walk(doc, ""))


def test_every_value_ref_swap_to_every_number_path_is_rejected(document):
    """Lens FA-B2's sweep at 657ef11: 13,962 of 42,849 swaps accepted (its enumeration).
    This one swaps every ``value_ref`` of the 70 engine claims to each of the document's
    418 Number paths, the claim's other pointers included (those are
    ``value_ref_duplicate``): 42,951 swaps, 0 accepted."""
    paths = _number_paths(document)
    assert len(paths) == 418
    assert sum(1 for p in paths if checker.pointer_facets(p) is None) == 225
    engine = claims_mod.build_claims(document)
    assert len(engine) == 70 and checker.check(engine, document).rejected == []
    swaps = 0
    accepted: list[tuple[str, str]] = []
    for claim in engine:
        for i, ref in enumerate(claim["value_refs"]):
            for other in paths:
                if other == ref:
                    continue
                swapped = copy.deepcopy(claim)
                swapped["value_refs"][i] = other
                swaps += 1
                if checker.check([swapped], document).verdicts[0].accepted:
                    accepted.append((claim["claim_id"], other))
    assert swaps == 42951
    assert accepted == []


def test_the_lens_b2_literal_claims_are_rejected_with_the_named_code(document):
    engine = claims_mod.build_claims(document)
    by_id = {c["claim_id"]: c for c in engine}
    overall_sens = by_id["CL-0001"]
    auroc = by_id["CL-0014"]
    sex_f = by_id["CL-0035"]  # sex = F sensitivity, difference vs M
    assert overall_sens["value_refs"] == ["/overall/op1/sensitivity"]
    assert sex_f["reference"] == {"attribute": "sex", "level": "M"}
    analytic0 = "/subgroups/0/metrics/op1/sensitivity/analytic"
    cases = [
        (
            {
                **copy.deepcopy(overall_sens),
                "template_id": "SUBGROUP_ESTIMATE",
                "subgroup": {"attribute": "age", "level": "40-65"},
                "value_refs": [analytic0],
            },
            "value_ref_unbound",
        ),
        ({**copy.deepcopy(overall_sens), "value_refs": [analytic0]}, "value_ref_unbound"),
        (
            {**copy.deepcopy(overall_sens), "value_refs": ["/calibration/oe/analytic"]},
            "value_ref_unbound",
        ),
        (
            {
                **copy.deepcopy(overall_sens),
                "value_refs": ["/fairness/gaps/0/operating_points/op1/tpr_gap/analytic"],
            },
            "value_ref_unbound",
        ),
        (
            {
                **copy.deepcopy(overall_sens),
                "value_refs": ["/calibration/decile_curve/0/observed/number"],
            },
            "value_ref_unbound",
        ),
        (
            {**copy.deepcopy(overall_sens), "metric_id": None, "value_refs": ["/overall/op1/npv"]},
            "metric_mismatch",
        ),
        (
            {
                **copy.deepcopy(overall_sens),
                "relation": "not_assessable",
                "value_refs": ["/overall/op1/two_by_two/tp"],
            },
            "value_ref_unbound",
        ),
        (
            {
                **copy.deepcopy(overall_sens),
                "relation": "not_assessable",
                "value_refs": ["/flow/analysed"],
            },
            "value_ref_unbound",
        ),
        (
            {**copy.deepcopy(sex_f), "value_refs": list(reversed(sex_f["value_refs"]))},
            "value_ref_unbound",
        ),
        ({**copy.deepcopy(sex_f), "reference": None}, "reference_mismatch"),
        (
            {
                **copy.deepcopy(sex_f),
                "comparator_id": "diff_vs_complement",
                "value_refs": [
                    sex_f["value_refs"][0],
                    "/subgroups/4/diff_vs_complement/op1/sensitivity/number",
                ],
            },
            "reference_mismatch",
        ),
        (
            {
                **copy.deepcopy(sex_f),
                "template_id": "SUBGROUP_ESTIMATE",
                "reference": None,
                "comparator_id": None,
                "value_refs": ["/subgroups/4/diff_vs_reference/op1/sensitivity/number"],
            },
            "value_ref_unbound",
        ),
        ({**copy.deepcopy(auroc), "operating_point": "op1"}, "operating_point_mismatch"),
    ]
    for claim, expected in cases:
        assert _code(claim, document) == expected, (claim, expected)
    # every library template outside the bound set that accepts one pointer, given the
    # overall sensitivity Number: 19 templates, each value_ref_unbound (the lens counted
    # 20 with its enumeration); 18 since E10 bound PAIRED_DIFF to the comparison cells
    outside = [
        t
        for t in LIBRARY
        if t not in checker.BOUND_TEMPLATES and LIBRARY[t].refs[0] <= 1 <= LIBRARY[t].refs[1]
    ]
    assert len(outside) == 18 and "PAIRED_DIFF" not in outside
    for t in outside:
        swapped = {**copy.deepcopy(overall_sens), "template_id": t, "guidance_ref": None}
        assert _code(swapped, document) == "value_ref_unbound", t
    # the engine's own claims on the two other document shapes still pass
    cols = make_cohort(n=200, with_case_id=True)
    cols["case_id"] = [f"c{i // 2:06d}" for i in range(200)]
    clustered = assemble(
        cols,
        make_criteria(
            criteria=[], clustering={"unit": "case_id", "declared_by": "t"}, fairness=None
        ),
    )
    assert checker.check(claims_mod.build_claims(clustered), clustered).rejected == []
    y_pred_only = assemble(_y_pred_only(200), make_criteria(criteria=[], fairness=None))
    assert checker.check(claims_mod.build_claims(y_pred_only), y_pred_only).rejected == []


# ------------------------------------------------- FA-B3: a fairness bound, no criteria list


def test_a_fairness_bound_without_a_criteria_list_prints_its_row_on_t8(tmp_path, monkeypatch):
    """Lens FA-B3 (D10): ``criteria`` absent, ``fairness.bound`` present, the 400-row
    fixture. At 657ef11 the page said "No acceptance criteria were declared" with 0
    criterion rows while section 7 counted ``criteria_not_met 1``."""
    _own_home(tmp_path, monkeypatch)
    rc, out = _run(
        tmp_path, cohort_with_a_thirty_row_site(), make_criteria(criteria=None, fairness=FAIRNESS)
    )
    assert rc == EXIT_OK
    run = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert "criteria" not in run["declarations"]
    assert [(r["criterion_id"], r["status"]) for r in run["criteria_results"]] == [
        ("fairness:tpr_gap", "not_met")
    ]
    page = (out / "T8.html").read_text(encoding="utf-8")
    assert "No acceptance criteria were declared" not in page
    assert page.count('class="criterion-row"') == 1
    assert re.findall(r'<td class="status">([^<]*)</td>', page) == ["criterion not met"]
    assert 'data-count="criteria_not_met">1</td>' in page
    assert 'data-count="criteria_rows">1</td>' in page
    # the renderer's gate reads the rows: a document with neither prints the caption
    none = assemble(make_cohort(n=120), make_criteria(criteria=[], fairness=None))
    none["manifest"]["numpy"] = "x.y.z"
    page_none = render_html.render_t8(none)
    assert none["criteria_results"] == []
    assert "No acceptance criteria were declared" in page_none
    assert page_none.count('class="criterion-row"') == 0


# ------------------------------------------------- FA-B4 / RG-B2: free_text spellings


def test_free_text_separated_control_and_small_capital_spellings_are_rejected():
    f = checker.free_text_reason
    for text in (
        "p a s s",  # FA-B4: spaced letters
        "p.a.s.s",
        "pa-ss",
        "fa-il",
        "unaccept-able",
        "well-cali-brated",
        "pa\x01ss",  # RG-B2: C0 control characters inside the word
        "pa\x1fss",
        "pa\x7fss",
        "pa\x85ss",
        "pa\x00ss",
        "ᴘᴀss",  # RG-B2: small capitals
        "pas s",  # RG-B2 recorded as accepted and not graded
        "p-a-s-s",
        "pa ss",  # a thin space
        "non inferior",
        "un biased",
        "w e l l c a l i b r a t e d",  # fourteen single letters; pins no _JOIN_RUN (lens RG-N3)
    ):
        assert f(f"Sensitivity looked {text} here.") == "free_text_verdict_word", repr(text)
    assert f("the C F R part") == "free_text_cfr"
    assert f("per the gui dance") == "free_text_guidance"
    assert f("FDA cle ared") == "free_text_certification_word"
    # accepted, recorded and not defended (the checker docstring names them)
    for text in (
        "Sensitivity was high in every subgroup.",
        "compassionate metabolism",
        "passport",
        "non-inferiority",
        "paßs",
        "p@ss",
        "ninety",
        "the guidances",
        "unsafe",
        "FDAcleared",
    ):
        assert f(text) is None, text
    # the token machinery on one literal: the runs, and the joins that hold pass
    assert checker._tokens("pa ss and p-a-s-s") == ["pa", "ss", "and", "p-a-s-s"]
    assert {"pass", "pa", "ss", "p-a-s-s", "p", "a", "s"} <= checker._words("pa ss and p-a-s-s")


# ------------------------- orchestrator, repair-2 close: a claim that binds no Number


def test_a_claim_bound_to_a_documented_scalar_must_state_not_assessable(document):
    """Rule 5's last branch: a claim whose value_refs name a documented scalar and no
    Number is recomputed as ``not_assessable``. The literal: the first OVERALL_ESTIMATE
    claim re-labelled FLOW_COUNTS over ``/flow/analysed``. With the branch planted to
    echo the stated relation (sweep mutant checker_relation_fallthrough_accepts_estimate)
    ``estimate``, ``above`` and ``within`` were accepted; each is relation_mismatch here."""
    engine = claims_mod.build_claims(document)
    engine = engine if isinstance(engine, list) else engine["claims"]
    base = next(c for c in engine if c["template_id"] == "OVERALL_ESTIMATE")
    claim = {**copy.deepcopy(base), "template_id": "FLOW_COUNTS"}
    claim["value_refs"] = ["/flow/analysed"]
    for relation in ("estimate", "above", "within"):
        assert _code({**claim, "relation": relation}, document) == "relation_mismatch", relation
    # repair 3 (lens FA-B1 at 7fa690b; the lens-3 notes' N6): the same claim stating
    # not_assessable was accepted with metric_id sensitivity and op1 on a run-level count;
    # rule 8b refuses it, and accepts it once the claim names no metric or operating point
    assert _code({**claim, "relation": "not_assessable"}, document) == "template_scope_mismatch"
    bare = {**claim, "relation": "not_assessable", "metric_id": None, "operating_point": None}
    assert _code(bare, document) is None


def test_the_longest_listed_words_spelled_out_letter_by_letter_are_rejected():
    """The join window against the longest listed words: miscalibrated and insignificant
    (13 letters, VERDICT_WORDS) and certification (13, CERTIFICATION_WORDS), each as
    thirteen single letters. Pins _JOIN_RUN >= 13 (sweep mutant checker_join_window_short
    plants 12)."""
    f = checker.free_text_reason
    for word, code in (
        ("miscalibrated", "free_text_verdict_word"),
        ("insignificant", "free_text_verdict_word"),
        ("certification", "free_text_certification_word"),
    ):
        assert f(f"The model was {' '.join(word)} here.") == code, word
