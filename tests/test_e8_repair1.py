"""Repair 1 of build day 8 (23 September 2026): regression tests for the lens findings
FA-B1 (binding), FA-B2 (free_text spellings), FA-B3 (y_pred vocabulary), FA-B4 (declared
digits), FA-B5 (prior_version), FA-N1 (author by position), FA-N2 (the clustered
prevalence no test pinned), FA-N4 (the checker items sharing B1's cause), RG-N1 and RG-N4
(malformed documents). Each test names the literal input it feeds and the figure it
asserts; every one failed in a worktree at 29fc04e with PYTHONPATH forced, and the
repair-1 note quotes the first E line of each.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from assembler import assemble
from conftest import ephemeral_registry, make_cohort, make_criteria
from proofpack import criteria as criteria_mod
from proofpack.cli import main
from proofpack.errors import EXIT_HALT, EXIT_OK, HaltError
from proofpack.gates import gate_h02
from proofpack.io import schema as schema_mod
from proofpack.io.declare import validate_dict
from proofpack.narrate import checker
from proofpack.narrate import claims as claims_mod
from proofpack.render import html as render_html
from proofpack.resources import load_json_schema
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


# ------------------------------------------------------------------ FA-B1: binding


def _sibling_numbers(doc: dict[str, Any], ref: str) -> list[str]:
    """Pointers to the other Numbers in the same block as ``ref``."""
    head, _, key = ref.rpartition("/")
    if key == "number":  # a day-4 cell: siblings are the other cells of its block
        cell_head, _, cell_key = head.rpartition("/")
        found, block = checker.resolve_pointer(doc, cell_head)
        return [
            f"{cell_head}/{k}/number"
            for k, v in (block or {}).items()
            if found
            and k != cell_key
            and isinstance(v, dict)
            and checker.is_number_object(v.get("number"))
        ]
    found, block = checker.resolve_pointer(doc, head)
    return [
        f"{head}/{k}"
        for k, v in (block or {}).items()
        if found and k != key and checker.is_number_object(v)
    ]


def test_every_sibling_metric_swap_and_field_mutation_is_rejected(document):
    """Lens FA-B1's sweep at 29fc04e: 339 sibling swaps accepted, 294 field mutations
    accepted. This sweep enumerates siblings its own way (every other Number in the same
    block, calibration and gap cells included: 580 swaps, 155 mutations on the synthetic
    document); every swap and every mutation is rejected."""
    engine = claims_mod.build_claims(document)
    assert len(engine) == 70
    swaps = 0
    accepted_swaps: list[tuple[str, str]] = []
    for claim in engine:
        for i, ref in enumerate(claim["value_refs"]):
            for other in _sibling_numbers(document, ref):
                if other in claim["value_refs"]:
                    continue
                swapped = copy.deepcopy(claim)
                swapped["value_refs"][i] = other
                swaps += 1
                if checker.check([swapped], document).verdicts[0].accepted:
                    accepted_swaps.append((claim["claim_id"], other))
    assert swaps == 580
    assert accepted_swaps == []
    mutations = accepted = 0
    metric_ids = sorted(load_json_schema("output_schema_v1.json")["$defs"]["metricId"]["enum"])
    for claim in engine:
        variants: list[dict[str, Any]] = []
        if claim["metric_id"] is not None:
            other = next(m for m in metric_ids if m != claim["metric_id"])
            variants.append({**copy.deepcopy(claim), "metric_id": other})
        if claim["operating_point"] is not None:
            variants.append({**copy.deepcopy(claim), "operating_point": "op2"})
        if claim["subgroup"] is None:
            variants.append(
                {**copy.deepcopy(claim), "subgroup": {"attribute": "sex", "level": "M"}}
            )
        for v in variants:
            mutations += 1
            accepted += checker.check([v], document).verdicts[0].accepted
    assert mutations == 155
    assert accepted == 0
    assert checker.check(engine, document).rejected == []  # the engine's own 70 still pass


def test_the_lens_b1_and_n4_literal_claims_are_rejected_with_the_named_code(document):
    engine = claims_mod.build_claims(document)
    by_id = {c["claim_id"]: c for c in engine}
    crit_met = by_id["CL-0062"]  # C_met, sensitivity, met
    crit_n30 = by_id["CL-0063"]  # C_n30, accuracy at site = S3, not_met
    auroc = by_id["CL-0014"]
    sub_diff = by_id["CL-0030"]  # age = 80-200 sensitivity with the difference cell
    calib = by_id["CL-0060"]
    gap = by_id["CL-0061"]
    f1_s1 = by_id["CL-0064"]  # C_f1_site at index 2, site = S1
    cases = [
        ({**copy.deepcopy(crit_met), "value_refs": ["/overall/op1/npv"]}, "metric_mismatch"),
        ({**copy.deepcopy(auroc), "value_refs": ["/overall/op1/sensitivity"]}, "metric_mismatch"),
        (
            {
                **copy.deepcopy(engine[0]),
                "template_id": "SUBGROUP_ESTIMATE",
                "subgroup": {"attribute": "age", "level": "40-65"},
            },
            "subgroup_mismatch",
        ),
        (
            {**copy.deepcopy(crit_n30), "value_refs": ["/overall/op1/sensitivity"]},
            "metric_mismatch",
        ),
        (
            {
                **copy.deepcopy(crit_n30),
                "subgroup": {"attribute": "sex", "level": "F"},
                "value_refs": ["/overall/op1/accuracy"],
            },
            "subgroup_mismatch",
        ),
        (
            {
                **copy.deepcopy(engine[0]),
                "value_refs": ["/subgroups/4/metrics/op1/sensitivity/number"],
            },
            "subgroup_mismatch",
        ),
        (
            {**copy.deepcopy(engine[0]), "value_refs": ["/overall/op1/two_by_two/tp"]},
            "relation_mismatch",
        ),
        (
            {**copy.deepcopy(sub_diff), "value_refs": [sub_diff["value_refs"][1]] * 2},
            "value_ref_duplicate",
        ),
        (
            {**copy.deepcopy(calib), "value_refs": ["/calibration/oe/number"] * 4},
            "value_ref_duplicate",
        ),
        ({**copy.deepcopy(gap), "value_refs": [gap["value_refs"][0]] * 4}, "value_ref_duplicate"),
        ({**copy.deepcopy(engine[0]), "operating_point": "op9"}, "operating_point_mismatch"),
        ({**copy.deepcopy(engine[0]), "operating_point": "op2"}, "operating_point_mismatch"),
        (
            {**copy.deepcopy(engine[0]), "subgroup": {"attribute": "sex", "level": "M"}},
            "template_scope_mismatch",
        ),
        (
            {**copy.deepcopy(engine[0]), "template_id": "SUBGROUP_ESTIMATE"},
            "template_scope_mismatch",
        ),
        ({**copy.deepcopy(engine[0]), "comparator_id": ">"}, "comparator_mismatch"),
        ({**copy.deepcopy(f1_s1), "criterion_index": 3}, "criterion_row_mismatch"),
        ({**copy.deepcopy(crit_met), "value_refs": []}, "criterion_row_mismatch"),
        ({**copy.deepcopy(engine[0]), "metric_id": "calibration_by_group"}, "metric_mismatch"),
    ]
    for claim, expected in cases:
        assert _code(claim, document) == expected, (claim, expected)
    # a claim_id carried twice rejects both copies; resolve fills the slot once
    dup = checker.check([engine[0], copy.deepcopy(engine[0])], document)
    assert [v.reason_code for v in dup.verdicts] == ["claim_id_duplicate"] * 2
    a, b = copy.deepcopy(engine[0]), copy.deepcopy(engine[0])
    a["relation"] = b["relation"] = "above"
    b["claim_id"] = "CL-9999"
    final, rejections = checker.resolve(document, [a, b])
    assert [c["claim_id"] for c in final] == ["CL-0001"]
    assert [r["substituted"] for r in rejections] == [True, False]
    # what rule 4 does not bind, stated: a metric family member under its own template
    assert _code({**copy.deepcopy(calib), "metric_id": "calibration_slope"}, document) is None
    assert checker._DOC_KEY_FOR_METRIC == {
        k: v for k, v in criteria_mod.CALIBRATION_KEYS.items() if k != v
    }


def test_a_pointer_of_another_operating_point_is_rejected_when_that_point_exists():
    """Two declared operating points (op1 at 0.5, op2 at 0.6): a claim naming op2 bound to
    /overall/op1/sensitivity is operating_point_mismatch. On a one-point document the
    check that op2 is a key of document.overall fires first; this document separates the
    per-pointer check (the day-8 sweep's `checker_operating_point_binding_skipped`)."""
    crit = make_criteria(criteria=[], fairness=None)
    crit["operating_points"].append({**crit["operating_points"][0], "id": "op2", "threshold": 0.6})
    doc = assemble(make_cohort(n=120), crit)
    assert sorted(k for k in doc["overall"] if k != "threshold_free") == ["op1", "op2"]
    engine = claims_mod.build_claims(doc)
    op1 = next(c for c in engine if c["value_refs"] == ["/overall/op1/sensitivity"])
    op2 = next(c for c in engine if c["value_refs"] == ["/overall/op2/sensitivity"])
    assert op1["operating_point"] == "op1" and op2["operating_point"] == "op2"
    assert checker.check(engine, doc).rejected == []
    crossed = {**copy.deepcopy(op1), "operating_point": "op2"}
    assert _code(crossed, doc) == "operating_point_mismatch"
    crossed2 = {**copy.deepcopy(op2), "value_refs": ["/overall/op1/sensitivity"]}
    assert _code(crossed2, doc) == "operating_point_mismatch"


# ------------------------------------------------------------------ FA-B2: free_text


def test_free_text_spellings_from_the_lens_are_rejected_and_plain_words_are_not():
    f = checker.free_text_reason
    for text in (
        "pаss",  # Cyrillic a
        "раss",  # Cyrillic er, a
        "pa‍ss",  # zero-width joiner
        "pa‌ss",  # zero-width non-joiner
        "pa­ss",  # soft hyphen
        "un-biased",
        "pass-",
        "-pass",
        "verdict-like",
        "fail-safe",
        "méets",  # combining acute
        "paß",  # eszett
        "non‑inferior",  # non-breaking hyphen
        "PАSS",  # Cyrillic capital a (U+0410), upper case
        "paſs",  # long s
        "ｐａｓｓ",  # fullwidth
    ):
        assert f(f"Sensitivity looked {text} here.") == "free_text_verdict_word", text
    assert f("FDA‑cleared") == "free_text_certification_word"
    assert f("Sensitivity was high in every subgroup.") is None
    assert f("compassionate metabolism") is None
    assert f("passport") is None
    assert f("non-inferiority") is None  # not a listed word; recorded, not defended
    assert f("paßs") is None  # 'passs' after the case fold: not a listed word


# ------------------------------------------------------------------ FA-B3: y_pred


def _y_pred_only_yes_no(n: int = 120) -> dict[str, list[Any]]:
    cols = make_cohort(n=n, with_y_pred=True)
    del cols["score"]
    cols["y_pred"] = ["yes" if v == "1" else "no" for v in cols["y_pred"]]
    return cols


def test_y_pred_outside_the_declared_classes_is_h02_at_the_gate_and_through_the_cli(
    tmp_path: Path, monkeypatch
):
    """Lens FA-B3: at 29fc04e this table gave overall.op1.two_by_two {tp 0, fn 37, fp 0,
    tn 63} on 100 rows and exit 0 through the CLI with sensitivity 0/42 on the page."""
    decl = validate_dict(make_criteria())
    table = schema_mod.validate(schema_mod.table_from_columns(_y_pred_only_yes_no()), period=None)
    with pytest.raises(HaltError) as ei:
        gate_h02(table, decl)
    assert ei.value.code == "H02"
    assert ei.value.detail == {"column": "y_pred", "n_unknown_values": 2, "n_declared": 2}
    assert "y_pred" in str(ei.value)
    cols_ok = make_cohort(n=120, with_y_pred=True)
    del cols_ok["score"]
    table_ok = schema_mod.validate(schema_mod.table_from_columns(cols_ok), period=None)
    assert gate_h02(table_ok, decl) is None
    # through the CLI: HALT, exit 3, nothing written
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path, cols=_y_pred_only_yes_no(), crit=make_criteria())
    out = tmp_path / "pack"
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--offline"],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_HALT
    assert not out.exists()


# ------------------------------------------------------------------ FA-B4: declared digits


def test_declared_numbers_print_every_digit_on_the_page():
    crit = make_criteria(
        threshold=0.4275,
        criteria=copy.deepcopy(CRITERIA),
        fairness={**FAIRNESS, "bound": 0.1005},
        prevalence=[{"label": "intended-use, test", "value": 0.0125, "source": "test fixture"}],
    )
    crit["criteria"][0]["value"] = 0.8525
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    doc["manifest"]["numpy"] = "x.y.z"
    page = render_html.render_t8(doc)
    for literal in (
        "threshold 0.4275 rule",
        '<td class="num">0.8525</td>',
        "intended-use, test: 0.0125 (",
        "bound 0.1005 (",
    ):
        assert literal in page, literal
    for rounded in (
        "threshold 0.427 ",
        '<td class="num">0.853</td>',
        "test: 0.013 (",
        "bound 0.101 ",
    ):
        assert rounded not in page, rounded
    assert page.count("0.4275") >= 2  # the T1-1 row and the YAML echo state one threshold
    assert "as the manufacturer wrote the value" not in page


# ------------------------------------------------------------------ FA-B5: prior_version


def test_a_criteria_yaml_without_prior_version_renders_and_runs(tmp_path: Path, monkeypatch):
    crit = make_criteria()
    del crit["model"]["prior_version"]
    doc = assemble(make_cohort(n=120), crit)
    doc["manifest"]["numpy"] = "x.y.z"
    page = render_html.render_t8(doc)
    assert "synthetic-classifier v1.3" in page and "prior version" not in page
    with_prior = render_html.render_t8({**doc, "declarations": make_criteria()})
    assert "synthetic-classifier v1.3 (prior version 1.2)" in with_prior
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path, cols=make_cohort(n=120), crit=crit)
    out = tmp_path / "pack"
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--offline"],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_OK
    assert (out / "T8.html").exists() and (out / "run.json").exists()


# ------------------------------------------------------------------ FA-N1: author by position


def test_two_criteria_sharing_an_id_print_their_own_author_and_justification(document):
    base = {
        "metric": "sensitivity",
        "operating_point": "op1",
        "scope": "overall",
        "statistic": "ci_lower_bound",
        "comparator": ">=",
    }
    crit = make_criteria(
        criteria=[
            {
                **base,
                "id": "C_dup",
                "value": 0.5,
                "author": "Author One",
                "date": "2026-01-01",
                "justification": "first justification",
            },
            {
                **base,
                "id": "C_dup",
                "value": 0.99,
                "author": "Author Two",
                "date": "2026-02-02",
                "justification": "second justification",
            },
        ],
        fairness=None,
    )
    doc = assemble(make_cohort(n=120), crit)
    assert [r["declaration_index"] for r in doc["criteria_results"]] == [0, 1]
    page = render_html.render_t8(doc)
    authored = re.findall(r'<td class="customer-text">(Author[^<]*)</td>', page)
    assert authored == ["Author One · 2026-01-01", "Author Two · 2026-02-02"]
    justifications = re.findall(r"Manufacturer text - justification</span>([^<]*)</div>", page)
    assert justifications == ["first justification", "second justification"]
    # the synthetic document: the level-* rows share their entry's index; the fairness
    # row has none and prints the fairness block's author
    rows = document["criteria_results"]
    assert [r["declaration_index"] for r in rows] == [0, 1, 2, 2, 2, 3, 4, 5, None]
    page2 = render_html.render_t8({**document, "manifest": {**document["manifest"], "numpy": "x"}})
    authored2 = re.findall(r'<td class="customer-text">([^<]* · [^<]*)</td>', page2)
    assert authored2[-1] == f"{FAIRNESS['author']} · {FAIRNESS['date']}"
    assert len(authored2) == 9
    jsonschema.validate(document, load_json_schema("output_schema_v1.json"))


# ------------------------------------------------------------------ RG-N1 / RG-N4: documents


def test_two_malformed_documents_are_rejected_not_raised(document):
    engine = claims_mod.build_claims(document)
    gap = next(c for c in engine if c["template_id"] == "FAIRNESS_GAP")
    scalar_gap = {
        **copy.deepcopy(gap),
        "relation": "not_assessable",
        "value_refs": ["/flow/rows_read", "/flow/analysed", "/flow/n_cases", "/flow/n_sites"],
    }
    bad = {"flow": copy.deepcopy(document["flow"]), "fairness": "x"}
    verdict = checker.check([scalar_gap], bad).verdicts[0]
    assert not verdict.accepted and verdict.reason_code == "subgroup_not_in_document"
    string_ci = copy.deepcopy(document)
    string_ci["overall"]["op1"]["sensitivity"]["ci_lo"] = "0.1"
    verdict2 = checker.check([engine[0]], string_ci).verdicts[0]
    assert not verdict2.accepted and verdict2.reason_code == "value_ref_not_a_number"
    string_diff = copy.deepcopy(document)
    string_diff["subgroups"][4]["diff_vs_reference"]["op1"]["sensitivity"]["number"]["ci_lo"] = (
        "-0.1"
    )
    rebuilt = claims_mod.build_claims(string_diff)  # raised TypeError at 29fc04e
    sex_f = next(
        c
        for c in rebuilt
        if c["subgroup"] == {"attribute": "sex", "level": "F"} and c["metric_id"] == "sensitivity"
    )
    assert sex_f["relation"] == "not_assessable"


# ------------------------------------------------------------------ FA-N2: clustered prevalence


def test_the_clustered_overall_prevalence_is_the_pooled_positive_share():
    cols = make_cohort(n=200, with_case_id=True)
    cols["case_id"] = [f"c{i // 2:06d}" for i in range(200)]
    crit = make_criteria(
        criteria=[], clustering={"unit": "case_id", "declared_by": "t"}, fairness=None
    )
    doc = assemble(cols, crit)
    n_pos = sum(1 for v in cols["y_true"] if v == "1")
    prevalence = doc["overall"]["op1"]["prevalence"]
    assert prevalence["method"] == "cluster_bootstrap_percentile"
    assert prevalence["k"] == n_pos == 69 and prevalence["n"] == 200
    assert prevalence["est"] == n_pos / 200 == 0.345
    assert doc["overall"]["threshold_free"]["prevalence"] == prevalence
    assert json.dumps(prevalence, allow_nan=False)
