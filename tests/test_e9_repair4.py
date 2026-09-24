"""Build day 9, repair round 4 (lens 4 fresh attack and regression, 24 September 2026).

Each test feeds the input a lens fed and asserts the literal text measured. The first
``E`` line of each test, run in an ``f72a9af`` worktree with ``PYTHONPATH`` forced, is
quoted in the message of the commit that added this file.

* **FA-B1** - on ``cohort_with_a_thirty_row_site()`` (one operating point, op1):
  ``Cpd`` (sensitivity, op1, ``type: paired_difference_vs_prior``, sex = F, -0.05),
  ``Cauc_pd`` (auroc, the same type, sex = F, 0.55), ``Cpt`` (sensitivity, op1,
  ``type: point``, sex = F, 0.6), ``Cauc`` (auroc, no ``type``, sex = F, 0.5) and
  ``Cref`` (sensitivity, op1, sex = M, 0.5): the lines the three sex F5 plots draw, the
  criteria cell of the F row of the sex T1-11, and the three T1-11 tables' text;
* **FA-N1 = RG-N1, FA-N2 = RG-N2, FA-N3 = RG-N3** - the text of
  ``tests/test_e9_repair3.py`` and ``render/t1.py``.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import make_criteria
from proofpack.render import t1 as render_t1
from test_criteria import _criterion, cohort_with_a_thirty_row_site

pytestmark = pytest.mark.day9

REPO = Path(__file__).resolve().parent.parent
SEX_F = {"attribute": "sex", "level": "F"}
PAIRED = "paired_difference_vs_prior"


@pytest.fixture(scope="module")
def paired_doc() -> dict[str, Any]:
    doc = assemble(
        cohort_with_a_thirty_row_site(),
        make_criteria(
            criteria=[
                _criterion(id="Cpd", type=PAIRED, scope=dict(SEX_F), value=-0.05),
                _criterion(
                    id="Cauc_pd",
                    type=PAIRED,
                    metric="auroc",
                    operating_point=None,
                    scope=dict(SEX_F),
                    value=0.55,
                ),
                _criterion(id="Cpt", type="point", scope=dict(SEX_F), value=0.6),
                _criterion(
                    id="Cauc", metric="auroc", operating_point=None, scope=dict(SEX_F), value=0.5
                ),
                _criterion(id="Cref", scope={"attribute": "sex", "level": "M"}, value=0.5),
            ],
            fairness=None,
        ),
    )
    rows = [
        (r["criterion_id"], r["operating_point"], r["status"], r["reason_code"])
        for r in doc["criteria_results"]
    ]
    assert rows == [
        ("Cpd", "op1", "not_assessable", "requires_compare"),
        ("Cauc_pd", None, "not_assessable", "requires_compare"),
        ("Cpt", "op1", "met", "statistic_compared"),
        ("Cauc", None, "met", "statistic_compared"),
        ("Cref", "op1", "met", "statistic_compared"),
    ]
    return doc


def _plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


# ------------------------------------------------------------------ FA-B1


def test_a_paired_difference_criterion_draws_no_f5_line(paired_doc):
    page = render_t1.render_t1(paired_doc)
    lines = {}
    for fig in re.findall(r'<figure[^>]*id="F5-sex-[^"]*".*?</figure>', page, re.S):
        fid = re.search(r'id="(F5-sex-[^"]*)"', fig).group(1)
        lines[fid] = re.findall(r"customer criterion [^<]*", fig)
    assert lines == {
        "F5-sex-sensitivity": [
            "customer criterion Cpt (A, 2026-01-01): 0.6",
            "customer criterion Cref (A, 2026-01-01): 0.5",
        ],
        "F5-sex-specificity": [],
        "F5-sex-auroc": ["customer criterion Cauc (A, 2026-01-01): 0.5"],
    }
    # f72a9af drew Cpd at x = 178.5, left of the plot's x0 = 190
    assert 'd="M178.5,20.0 L178.5,72.0"' not in page


def test_the_sex_t1_11_rows_still_print_the_paired_rows_status_and_not_cref(paired_doc):
    page = render_t1.render_t1(paired_doc)
    cells = {}
    for table in re.findall(
        r'<table class="subgroup" data-attribute="sex" data-op="op1">.*?</table>\s*</div>\s*'
        r'<div class="table-wrap">\s*<table class="differences">(.*?)</table>',
        page,
        re.S,
    ):
        for lv, row in re.findall(
            r'<tr><th scope="row" class="customer-text">([^<]*)</th>(.*?)</tr>', table
        ):
            cells[lv] = re.findall(
                r"(\S+) \(row (\d+)\) → (criterion \w+(?: \w+)?|not assessable)", _plain(row)
            )
    assert cells["F"] == [
        ("Cpd", "1", "not assessable"),
        ("Cauc_pd", "2", "not assessable"),
        ("Cpt", "3", "criterion met"),
        ("Cauc", "4", "criterion met"),
    ]
    assert "M" not in cells  # the reference level has no T1-11 row
    differences = re.findall(r'<table class="differences">(.*?)</table>', page, re.S)
    assert len(differences) == 3
    assert not [t for t in differences if "Cref" in t]


# ------------------------------------------------------------------ sentence repairs


def test_the_repair_3_file_names_where_its_e_lines_are_and_what_its_t1_11_test_reads():
    src = (REPO / "tests" / "test_e9_repair3.py").read_text(encoding="utf-8")
    assert "the first ``E`` line of each is in the repair note" not in src
    assert "handoffs/2026-09-24_E_lens4_regression.md" in src
    assert "def test_each_t1_11_prints_" not in src
    assert "def test_the_sex_f_row_of_the_op1_and_op2_t1_11_prints_its_own_criteria_rows" in src


def test_t1_py_no_longer_calls_an_op_less_row_an_auroc_criterion():
    src = (REPO / "src" / "proofpack" / "render" / "t1.py").read_text(encoding="utf-8")
    assert "(an ``auroc`` criterion" not in src
    assert "with each criterion scoped on the attribute and level and declared" not in src
    assert "a criteria row\n    scoped on it is printed in no T1-11" in src.replace("\r\n", "\n")
