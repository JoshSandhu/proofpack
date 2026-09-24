"""Build day 9, repair round 3 (lens 3 fresh attack and regression, 24 September 2026).

Each test feeds the input a lens fed, or the input named in its docstring, and asserts the
literal text it measured. Run alone in a ``952bddc`` worktree with ``PYTHONPATH`` forced,
this file gives ``5 failed``; the first ``E`` line of each is quoted under "Pre-fix" in
``handoffs/2026-09-24_E_lens4_regression.md`` and in the repair-4 note.

* **FA-B1** - ``criteria_results`` rows C3 (op2), C4 (op1) and C5 (``auroc``, no operating
  point), all scoped on sex = F, plus ``FAIRNESS``'s ``fairness:tpr_gap`` rows (one per
  operating point), on ``cohort_with_a_thirty_row_site()`` with ``op2`` (threshold 0.3,
  rule ``>=``): the lines the three sex F5 plots draw and the criteria cell of the F row
  of the op1 and op2 sex T1-11 tables;
* **FA-N1** - the two ``FAIRNESS_GAP`` sentences of that document;
* **FA-N3** - T7 of the i.i.d. document above and of the clustered document
  (400 rows, ``case_id = c{i//2}``);
* **FA-N2 = RG-N1** - the repair-2 test file's test names.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import make_cohort, make_criteria
from proofpack.render import t1 as render_t1
from proofpack.render import t7 as render_t7
from test_criteria import FAIRNESS, _criterion, cohort_with_a_thirty_row_site

pytestmark = pytest.mark.day9

REPO = Path(__file__).resolve().parent.parent
SEX_F = {"attribute": "sex", "level": "F"}


@pytest.fixture(scope="module")
def two_op_criteria() -> dict[str, Any]:
    crit = make_criteria(
        criteria=[
            _criterion(id="C3", operating_point="op2", scope=dict(SEX_F), value=0.70),
            _criterion(id="C4", operating_point="op1", scope=dict(SEX_F), value=0.60),
            _criterion(id="C5", metric="auroc", operating_point=None, scope=dict(SEX_F), value=0.5),
        ],
        fairness=FAIRNESS,
    )
    crit["operating_points"].append(
        {"id": "op2", "threshold": 0.3, "rule": ">=", "provenance": "prespecified_sap"}
    )
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    rows = [
        (r["criterion_id"], r["operating_point"], r["metric"], r["status"])
        for r in doc["criteria_results"]
    ]
    assert rows == [
        ("C3", "op2", "sensitivity", "met"),
        ("C4", "op1", "sensitivity", "met"),
        ("C5", None, "auroc", "met"),
        ("fairness:tpr_gap", "op1", "tpr_gap", "not_met"),
        ("fairness:tpr_gap", "op2", "tpr_gap", "not_met"),
    ]
    return doc


def _plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


# ------------------------------------------------------------------ FA-B1


def test_an_op2_criterion_draws_no_line_on_the_op1_f5_plot(two_op_criteria):
    page = render_t1.render_t1(two_op_criteria)
    lines = {}
    for fig in re.findall(r'<figure[^>]*id="F5-sex-[^"]*".*?</figure>', page, re.S):
        fid = re.search(r'id="(F5-sex-[^"]*)"', fig).group(1)
        lines[fid] = re.findall(r"customer criterion [^<]*", fig)
        if fid == "F5-sex-sensitivity":
            assert "Sensitivity by sex at operating point op1" in fig
    assert lines == {
        "F5-sex-sensitivity": ["customer criterion C4 (A, 2026-01-01): 0.6"],
        "F5-sex-specificity": [],
        "F5-sex-auroc": ["customer criterion C5 (A, 2026-01-01): 0.5"],
    }


def test_the_sex_f_row_of_the_op1_and_op2_t1_11_prints_its_own_criteria_rows_and_c5(
    two_op_criteria,
):
    page = render_t1.render_t1(two_op_criteria)
    cells = {}
    # each T1-11 is the table after its operating point's T1-10 (data-op on T1-10)
    for op, table in re.findall(
        r'<table class="subgroup" data-attribute="sex" data-op="(\w+)">.*?</table>\s*</div>\s*'
        r'<div class="table-wrap">\s*<table class="differences">(.*?)</table>',
        page,
        re.S,
    ):
        row = re.search(r'<tr><th scope="row" class="customer-text">F</th>(.*?)</tr>', table)
        cells[op] = re.findall(r"(\S+) \(row (\d+)\) → (criterion \w+(?: \w+)?)", _plain(row[1]))
    assert cells == {
        "op1": [
            ("C4", "2", "criterion met"),
            ("C5", "3", "criterion met"),
            ("fairness:tpr_gap", "4", "criterion not met"),
        ],
        "op2": [
            ("C3", "1", "criterion met"),
            ("C5", "3", "criterion met"),
            ("fairness:tpr_gap", "5", "criterion not met"),
        ],
    }


# ------------------------------------------------------------------ FA-N1


def test_the_fairness_gap_sentence_prints_the_auroc_gap_outside_the_operating_point_clause(
    two_op_criteria,
):
    page = render_t1.render_t1(two_op_criteria)
    claims = [
        html.unescape(re.sub(r"<[^>]+>", "", s))
        for s in re.findall(r'<p class="claim" data-claim="[^"]+">(.*?)</p>', page)
    ]
    printed = [s for s in claims if s.startswith("For F versus M")]
    assert printed == [
        "For F versus M: at operating point op1, TPR gap +7.0 [−7.9, +21.7], FPR gap −4.8 "
        "[−14.8, +5.4], PPV gap +8.9 [−6.2, +23.3]; AUROC gap (no operating point) +0.079 "
        "[−0.002, +0.160].",
        "For F versus M: at operating point op2, TPR gap +6.4 [−1.7, +15.8], FPR gap −1.3 "
        "[−13.0, +10.4], PPV gap +4.2 [−7.7, +15.8]; AUROC gap (no operating point) +0.079 "
        "[−0.002, +0.160].",
    ]
    assert not [s for s in claims if "AUROC gap" in s and "AUROC gap (no operating point)" not in s]


# ------------------------------------------------------------------ FA-N3


def test_t7_of_the_iid_and_clustered_documents_prints_no_z_p_location_sentence(two_op_criteria):
    cols = make_cohort(n=400, with_case_id=True)
    cols["case_id"] = [f"c{i // 2}" for i in range(400)]
    clustered = assemble(
        cols,
        make_criteria(
            criteria=[], clustering={"unit": "case_id", "declared_by": "test"}, fairness=None
        ),
    )
    details = [
        s[key]["auroc"].get("detail")
        for s in clustered["subgroups"]
        for key in ("diff_vs_reference", "diff_vs_complement")
        if isinstance(s.get(key), dict) and isinstance(s[key].get("auroc"), dict)
    ]
    # the lens's measurement: 15 AUROC difference cells, each detail empty
    assert len(details) == 15 and all(not d for d in details)
    for doc in (two_op_criteria, clustered):
        t7 = render_t7.render_t7(doc)
        assert "written to run.json beside the" not in t7
        assert "z and the two-sided p" not in t7
        assert "the unpaired DeLong (1988) difference" in t7


# ------------------------------------------------------------------ FA-N2 = RG-N1


def test_the_repair_2_file_no_longer_carries_the_name_state_what_they_inspect():
    src = (REPO / "tests" / "test_e9_repair2.py").read_text(encoding="utf-8")
    assert "state_what_they_inspect" not in src
    assert "def test_the_repair_1_file_carries_the_new_name_and_footer_clause_not_the_old(" in src
