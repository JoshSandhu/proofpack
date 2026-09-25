"""Build day 10 (E10 item 2): the ``paired_difference_vs_prior`` criterion.

* in ``compare`` the criterion is evaluated against the customer's margin with its
  declared statistic and comparator (DEC-44 / DEC-46) and reports ``met`` / ``not_met`` /
  ``not_assessable`` with the machine reason: F5's ``C2`` (accuracy, ``ci_lower_bound >=
  -0.05``) is ``not_met`` - the brief's acceptance test; the fixture's difference is
  -0.08 and its lower bound -0.155;
* outside ``compare`` (a ``run`` document, no ``comparison`` block) it stays
  ``not_assessable`` / ``requires_compare``; on an unpaired comparison it is
  ``not_assessable`` / ``not_like_for_like`` (D1 section 2's "comparator not
  like-for-like");
* **E9 row 121 / need 32** (lens-5 FA-N1): on lens 5's ``Cpd`` input, T1 now prints the
  declared type in Table T1-17 and the phrase "difference against the prior version" in
  the ``CRITERION_STATUS`` sentence and in T1-11's criterion cell. At ``81f1102`` the
  page carried ``CI lower bound >= -0.05`` and no such phrase
  (``test_the_lens_5_cpd_input_names_the_difference_against_the_prior_version``);
* **no margin anywhere but criteria.yaml**: a grep over ``src/`` (code, templates,
  schema defaults) for ``0.02``, ``0.03``, ``0.05``, ``delta_default`` and
  ``default_margin`` finds no margin literal outside the fixture values D1 section 3.2
  names (``test_no_margin_is_typed_anywhere_but_a_customers_criteria_yaml``).
"""

from __future__ import annotations

import copy
import html
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import confirmed_mapping, ephemeral_registry, make_criteria
from proofpack import criteria as criteria_mod
from proofpack.render import t1 as render_t1
from proofpack.run import assemble_compare
from test_criteria import _criterion, cohort_with_a_thirty_row_site

pytestmark = pytest.mark.day10

REPO = Path(__file__).resolve().parent.parent
F5 = REPO / "tests" / "fixtures" / "f5"
PAIRED = "paired_difference_vs_prior"
PHRASE = "difference against the prior version"


def f5_compare(tmp_path: Path, home: Path, **overrides: Any):
    """``assemble_compare`` on the F5 fixture pair, criteria.yaml as committed unless a
    key is overridden (``criteria`` replaces the list)."""
    work = tmp_path / "f5"
    work.mkdir(exist_ok=True)
    for name in ("f5_new.csv", "f5_prior.csv", "criteria.yaml"):
        shutil.copy(F5 / name, work / name)
    if overrides:
        import yaml

        crit = yaml.safe_load((work / "criteria.yaml").read_text(encoding="utf-8"))
        crit.update(overrides)
        (work / "criteria.yaml").write_text(yaml.safe_dump(crit, sort_keys=False), "utf-8")
    confirmed_mapping(work / "f5_new.csv")
    return assemble_compare(
        work / "f5_new.csv",
        work / "f5_prior.csv",
        work / "criteria.yaml",
        registry=ephemeral_registry(),
        ledger_home=home,
    )


@pytest.fixture
def home(tmp_path: Path, monkeypatch) -> Path:
    from conftest import write_licence

    h = tmp_path / "home"
    h.mkdir()
    write_licence(h / "proofpack.lic")
    monkeypatch.setenv("PROOFPACK_HOME", str(h))
    return h


# ------------------------------------------------------------------ the acceptance test


def test_f5_at_margin_minus_0_05_is_not_met_with_the_machine_reason(tmp_path, home):
    doc = f5_compare(tmp_path, home).document
    rows = {r["criterion_id"]: r for r in doc["criteria_results"]}
    c2 = rows["C2"]
    assert c2["status"] == "not_met" and c2["reason_code"] == "statistic_compared"
    assert c2["statistic"] == "ci_lower_bound" and c2["comparator"] == ">="
    assert c2["value"] == -0.05  # read from criteria.yaml, nowhere else
    assert c2["metric_ref"] == "comparison.differences.op1.accuracy.number"
    assert c2["method"] == "newcombe_paired" and c2["n"] == 100
    number = doc["comparison"]["differences"]["op1"]["accuracy"]["number"]
    assert c2["compared_value"] == number["ci_lo"] < -0.05
    assert abs(number["est"] + 0.08) < 1e-12
    # the point criterion beside it is unchanged by the comparison
    assert rows["C1"]["metric_ref"] == "overall.op1.sensitivity"


@pytest.mark.parametrize(
    "statistic, comparator, value, expected",
    [
        ("ci_lower_bound", ">=", -0.05, "not_met"),
        ("ci_lower_bound", ">=", -0.16, "met"),
        ("point_estimate", ">=", -0.08, "met"),
        ("point_estimate", ">", -0.08, "not_met"),
        ("ci_upper_bound", "<=", 0.0, "met"),  # DEC-44: the upper end, literally
        ("ci_upper_bound", "<", -0.01, "met"),  # ci_hi -0.0102 < -0.01
    ],
)
def test_the_declared_statistic_and_comparator_decide_the_status(
    tmp_path, home, statistic, comparator, value, expected
):
    crit = [
        _criterion(
            id="Cpd",
            metric="accuracy",
            type=PAIRED,
            statistic=statistic,
            comparator=comparator,
            value=value,
        )
    ]
    doc = f5_compare(tmp_path, home, criteria=crit).document
    (row,) = doc["criteria_results"]
    assert (row["status"], row["reason_code"]) == (expected, "statistic_compared"), row


def test_paired_criteria_on_auroc_brier_slope_and_a_subgroup_read_their_cells(tmp_path, home):
    crit = [
        _criterion(id="Cauc", metric="auroc", type=PAIRED, operating_point=None, value=-0.5),
        _criterion(id="Cbr", metric="brier", type=PAIRED, operating_point=None, value=-0.5),
        _criterion(
            id="Csl", metric="calibration_slope", type=PAIRED, operating_point=None, value=-5
        ),
        _criterion(
            id="Csex",
            metric="sensitivity",
            type=PAIRED,
            scope={"attribute": "sex", "level": "F"},
            value=-0.5,
        ),
        _criterion(
            id="Cstar",
            metric="specificity",
            type=PAIRED,
            scope={"attribute": "sex", "level": "*"},
            value=-0.5,
        ),
        _criterion(id="Cppv", metric="ppv", type=PAIRED, value=-0.5),
    ]
    doc = f5_compare(tmp_path, home, criteria=crit).document
    rows = doc["criteria_results"]
    by_id: dict[str, list[dict]] = {}
    for r in rows:
        by_id.setdefault(r["criterion_id"], []).append(r)
    assert by_id["Cauc"][0]["metric_ref"] == "comparison.differences.auroc.number"
    assert by_id["Cauc"][0]["status"] == "met"
    assert by_id["Cbr"][0]["metric_ref"] == "comparison.differences.brier.number"
    assert by_id["Csl"][0]["metric_ref"] == "comparison.differences.slope.number"
    f = next(
        i for i, r in enumerate(doc["subgroups"]) if r["attribute"] == "sex" and r["level"] == "F"
    )
    assert (
        by_id["Csex"][0]["metric_ref"]
        == f"comparison.subgroups[{f}].differences.op1.sensitivity.number"
    )
    assert by_id["Csex"][0]["status"] == "met"
    assert [r["scope"]["level"] for r in by_id["Cstar"]] == ["F", "M"]
    assert all(r["status"] == "met" for r in by_id["Cstar"])
    # PPV is not a paired proportion (its denominators differ between the versions)
    assert by_id["Cppv"][0]["status"] == "not_assessable"
    assert by_id["Cppv"][0]["reason_code"] == "comparison_not_computed_for_scope"


# ------------------------------------------------------------------ outside compare


def _f5_with_case_ids(work: Path) -> None:
    """The three F5 files in ``work`` with a ``case_id`` column ``c{i // 2}`` on both
    versions and ``clustering.unit: case_id`` (lens 1 FA-B1's input)."""
    import yaml

    work.mkdir(exist_ok=True)
    for name in ("f5_new.csv", "f5_prior.csv"):
        lines = (F5 / name).read_text(encoding="utf-8").splitlines()
        out = [lines[0] + ",case_id"] + [f"{ln},c{i // 2}" for i, ln in enumerate(lines[1:])]
        (work / name).write_text("\n".join(out) + "\n", encoding="utf-8")
    crit = yaml.safe_load((F5 / "criteria.yaml").read_text(encoding="utf-8"))
    crit["clustering"] = {"unit": "case_id", "declared_by": "test"}
    crit["criteria"] = [
        dict(
            crit["criteria"][1],
            id="Cse",
            metric="sensitivity",
            justification="lens 1 FA-B1: a paired margin on sensitivity under clustering",
            value=-0.30,
        )
    ]
    (work / "criteria.yaml").write_text(yaml.safe_dump(crit, sort_keys=False), "utf-8")
    confirmed_mapping(work / "f5_new.csv")


def test_f5_case_id_c_i_over_2_assesses_a_paired_se_criterion_and_t2_prints_the_ci(tmp_path, home):
    """Lens 1 FA-B1 through ``assemble_compare`` and T2: ``Cse`` (sensitivity,
    ``ci_lower_bound >= -0.30``, overall, op1) on the F5 pair with ``case_id = c{i // 2}``
    is ``met`` with ``compared_value`` the cluster-bootstrap lower bound (-0.2 at B 200,
    seed 20240101); T2-3's sensitivity cell prints the interval and the page carries no
    ``insufficient_clusters``. At 322c5a4 the row was ``not_assessable`` /
    ``no_interval`` with ``detail.not_estimable_reason`` ``insufficient_clusters`` and
    T2-3 printed ``n.e. (insufficient_clusters)`` beside the run's own sensitivity
    interval on the same 26 cases."""
    from proofpack.render.t2 import render_t2

    work = tmp_path / "f5c"
    _f5_with_case_ids(work)
    outcome = assemble_compare(
        work / "f5_new.csv",
        work / "f5_prior.csv",
        work / "criteria.yaml",
        registry=ephemeral_registry(),
        ledger_home=home,
    )
    doc = outcome.document
    assert doc["comparison"]["clustering_route"] == "declared"
    se = doc["comparison"]["differences"]["op1"]["sensitivity"]["number"]
    own = doc["overall"]["op1"]["sensitivity"]
    assert own["method"] == "cluster_bootstrap_percentile" and own["n_cases"] == 26
    assert se["method"] == "cluster_bootstrap_percentile" and se["n_cases"] == 26
    assert se["not_estimable_reason"] is None and se["n"] == 50
    assert round(se["ci_lo"], 4) == -0.2 and se["est"] == -0.08
    (row,) = doc["criteria_results"]
    assert row["criterion_id"] == "Cse"
    assert row["status"] == "met" and row["reason_code"] == "statistic_compared"
    assert row["compared_value"] == se["ci_lo"]
    assert "not_estimable_reason" not in row["detail"]
    for entry in doc["comparison"]["subgroups"]:
        for metric in ("sensitivity", "specificity"):
            num = entry["differences"]["op1"][metric]["number"]
            assert num["method"] == "cluster_bootstrap_percentile", (entry["level"], metric)
    page = render_t2(doc)
    assert "insufficient_clusters" not in page
    assert "n.e." not in page
    visible = html.unescape(re.sub(r"<[^>]+>", "", page))
    assert visible.count("Criterion Cse (sensitivity difference against the prior version") == 1
    assert "criterion met" in page and "not assessable" not in page
    se_row = re.search(r'<tr data-metric="sensitivity" data-op="op1">(.*?)</tr>', page, re.S)
    assert se_row is not None
    assert "−8.0 [−20.0, +2.0]" in html.unescape(se_row.group(1))
    assert "cluster_bootstrap_percentile" in se_row.group(1)


def test_two_paired_criteria_on_the_accuracy_cell_both_print_on_the_t2_3_row(tmp_path, home):
    """Lens 1 FA-N2 / lens 2 FA-F5 (E10 repair 2). Two ``paired_difference_vs_prior``
    criteria on one cell (accuracy, op1, overall) of the F5 pair: ``Cfirst``
    (``point_estimate >= -0.10``, met: the estimate is -0.08) declared before ``C2``
    (``ci_lower_bound >= -0.05``, not_met: the lower bound is -0.1554). T2-3's accuracy
    row prints both ids, both status words and the record string once (C2's); the
    sentences and the traceability table carry both. At 667a201 the row printed
    ``Cfirst`` only, ``C2`` nowhere, and the record string reached the page 0 times
    (lens 2 block I: ``Cfirst 1 C2 0 record string on page 0``)."""
    import yaml

    from proofpack.render.t2 import NOT_MET_RECORD, render_t2

    base = yaml.safe_load((F5 / "criteria.yaml").read_text(encoding="utf-8"))["criteria"][1]
    crit = [
        dict(base, id="Cfirst", statistic="point_estimate", value=-0.10),
        dict(base, id="C2"),
    ]
    doc = f5_compare(tmp_path, home, criteria=crit).document
    statuses = [(r["criterion_id"], r["status"]) for r in doc["criteria_results"]]
    assert statuses == [("Cfirst", "met"), ("C2", "not_met")]
    number = doc["comparison"]["differences"]["op1"]["accuracy"]["number"]
    assert doc["criteria_results"][0]["compared_value"] == number["est"] == -0.08
    assert doc["criteria_results"][1]["compared_value"] == number["ci_lo"] < -0.05
    page = render_t2(doc)
    row = re.search(r'<tr data-metric="accuracy" data-op="op1">(.*?)</tr>', page, re.S).group(1)
    assert row.count("Cfirst</span> (row 1)") == 1 and row.count("C2</span> (row 2)") == 1
    margin, status = re.findall(r"<td class=\"(?:num|status)\">(.*?)</td>", row, re.S)[-2:]
    assert margin.split("<br>")[0].startswith('<span class="customer-text inline">Cfirst</span>')
    assert margin.split("<br>")[1].startswith('<span class="customer-text inline">C2</span>')
    assert "point estimate &gt;= " in margin and "ci lower bound &gt;= " in margin
    lines = status.split("<br>")
    assert lines[0] == "criterion met"
    assert lines[1] == f'criterion not met - <span class="status record">{NOT_MET_RECORD}</span>'
    assert page.count(NOT_MET_RECORD) == 1
    for other in re.findall(r'<tr data-metric="(?!accuracy)[^"]*"[^>]*>(.*?)</tr>', page, re.S):
        assert "Cfirst" not in other and "C2</span>" not in other
    visible = html.unescape(re.sub(r"<[^>]+>", "", page))
    for cid in ("Cfirst", "C2"):
        assert visible.count(f"Criterion {cid} (accuracy difference against the prior version") == 1
    trace = re.search(r'<table class="traceability">.*?</table>', page, re.S).group(0)
    assert trace.count("Cfirst") == 1 and trace.count(">C2<") == 1


def test_outside_compare_the_criterion_stays_requires_compare():
    crit = make_criteria(criteria=[_criterion(id="Cpd", type=PAIRED, value=-0.05)], fairness=None)
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    assert "comparison" not in doc
    (row,) = doc["criteria_results"]
    assert (row["status"], row["reason_code"]) == ("not_assessable", "requires_compare")
    assert row["metric_ref"] is None and row["compared_value"] is None


def test_on_an_unpaired_comparison_the_criterion_is_not_assessable_not_like_for_like(
    tmp_path, home
):
    work = tmp_path / "unpaired"
    work.mkdir()
    for name in ("f5_new.csv", "criteria.yaml"):
        shutil.copy(F5 / name, work / name)
    lines = (F5 / "f5_prior.csv").read_text(encoding="utf-8").splitlines()
    lines[1] = lines[1].replace("f5-000", "f5-999")  # one row_id of the prior is unmatched
    (work / "f5_prior.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    confirmed_mapping(work / "f5_new.csv")
    outcome = assemble_compare(
        work / "f5_new.csv",
        work / "f5_prior.csv",
        work / "criteria.yaml",
        allow_unpaired=True,
        registry=ephemeral_registry(),
        ledger_home=home,
    )
    doc = outcome.document
    assert doc["comparison"]["paired"] is False
    c2 = next(r for r in doc["criteria_results"] if r["criterion_id"] == "C2")
    assert (c2["status"], c2["reason_code"]) == ("not_assessable", "not_like_for_like")
    assert c2["metric_ref"] is None and c2["compared_value"] is None
    assert "W12" in [w.code for w in outcome.warnings]


def test_the_two_new_reason_codes_are_in_the_closed_set_and_the_schema():
    from proofpack.resources import load_json_schema

    enum = load_json_schema("output_schema_v1.json")["$defs"]["criterionResult"]["properties"][
        "reason_code"
    ]["enum"]
    for code in ("not_like_for_like", "comparison_not_computed_for_scope", "requires_compare"):
        assert code in criteria_mod.REASON_CODES and code in enum
    assert set(criteria_mod.REASON_CODES) == set(enum)


# ------------------------------------------------------------------ E9 row 121


@pytest.fixture(scope="module")
def cpd_page() -> tuple[str, dict[str, Any]]:
    """Lens 5's input (handoffs/2026-09-24_E_lens5_fresh-attack.md): ``Cpd``
    (sensitivity, type paired_difference_vs_prior, sex = F, -0.05) on the thirty-row-site
    cohort, rendered as T1."""
    crit = make_criteria(
        criteria=[
            _criterion(id="Cpd", type=PAIRED, scope={"attribute": "sex", "level": "F"}, value=-0.05)
        ],
        fairness=None,
    )
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    return render_t1.render_t1(doc), doc


def test_the_lens_5_cpd_input_names_the_difference_against_the_prior_version(cpd_page):
    page, doc = cpd_page
    (row,) = doc["criteria_results"]
    assert row["status"] == "not_assessable" and row["reason_code"] == "requires_compare"
    # the CRITERION_STATUS sentence (lens 5 counted 'paired' 0 times at e62d329)
    claim = re.search(
        r'<p class="claim" data-claim="CL-\d+">(.*?)</p>', page[page.index("t1-s12") :], re.S
    )
    sentence = re.sub(r"<[^>]+>", "", claim.group(1))
    assert "CI lower bound &gt;= −0.05" in sentence
    assert f"sensitivity {PHRASE}, sex = F, op1" in sentence
    assert "not assessable (requires_compare)" in sentence
    # Table T1-17's Type column
    row_html = re.search(r'<tr class="criterion-row" data-position="1">(.*?)</tr>', page, re.S)
    cells = re.findall(r"<td[^>]*>([^<]*)</td>", row_html.group(1))
    assert cells[3] == "paired difference vs prior version" and cells[2] == "sensitivity"
    assert '<th scope="col">Type</th>' in page
    # T1-11's criterion cell (E9 repair 4's regex still matches the id and the row)
    t1_11 = re.findall(
        r"Cpd</span> \(row 1\) → <span class=\"status\">not assessable</span>([^;]*);", page
    )
    assert t1_11 and all(f" ({PHRASE})" == t for t in t1_11), t1_11
    assert page.count(PHRASE) == 2  # the sentence and the one T1-11 cell (one op)


def test_a_point_criterion_prints_type_point_and_no_prior_phrase():
    crit = make_criteria(criteria=[_criterion(id="C1", value=0.5)], fairness=None)
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    page = render_t1.render_t1(doc)
    assert PHRASE not in page
    row_html = re.search(r'<tr class="criterion-row" data-position="1">(.*?)</tr>', page, re.S)
    cells = re.findall(r"<td[^>]*>([^<]*)</td>", row_html.group(1))
    assert cells[3] == "point"


# ------------------------------------------------------------------ no margin in the engine

#: The values a margin might be typed as (the brief's list) and the names a default might
#: carry. ``0.05`` also occurs in ``src/`` as R2 section 9 F2's intended-use prevalence
#: (``fixtures.py``: ``ppv_at_0.05`` / ``npv_at_0.05``, a fixture register value, not a
#: margin) and in two docstrings that quote lens inputs; each allowed line is listed here
#: with the reason it is not a margin, so a new occurrence fails.
MARGIN_TOKENS = ("0.02", "0.03", "0.05", "delta_default", "default_margin")
ALLOWED: dict[str, tuple[str, ...]] = {
    "src/proofpack/fixtures.py": (
        '"ppv_at_0.05",',
        '"npv_at_0.05",',
        'out["ppv_at_0.05"] = ppv_at_prevalence(t, 0.05).est',
        'out["npv_at_0.05"] = npv_at_prevalence(t, 0.05).est',
        "two Wilson intervals, PPV and NPV at prevalence 0.05",
        "PSI critical value at B = 10, alpha 0.05",
    ),
    "src/proofpack/render/figures.py": (
        "``Cpd`` (sensitivity, op1, sex = F, value -0.05) was drawn at x = 178.5 on the op1",
    ),
    "src/proofpack/stats/bootstrap.py": (
        "cases, the interval covered the truth at a frozen share of 0.05 / 0.10 / 0.20 in",
        "constant at 0.20 the shapes it **renders** are 0.05 and 0.10 (both at or above the",
    ),
}


def test_no_margin_is_typed_anywhere_but_a_customers_criteria_yaml():
    pattern = re.compile(r"(?<![\d.])(0\.02|0\.03|0\.05)(?![\d])|delta_default|default_margin")
    hits: list[tuple[str, str]] = []
    roots = [REPO / "src", REPO / "schema"]  # src/ holds the templates; schema/ the defaults
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in {
                ".py",
                ".html",
                ".j2",
                ".json",
                ".csv",
                ".yaml",
                ".md",
            }:
                continue
            if "__pycache__" in path.parts or path.name == "tr39_confusables.py":
                continue
            rel = path.relative_to(REPO).as_posix()
            for line in path.read_text(encoding="utf-8").splitlines():
                if not pattern.search(line):
                    continue
                if any(a in line for a in ALLOWED.get(rel, ())):
                    continue
                hits.append((rel, line.strip()[:100]))
    assert hits == [], hits
    # the fixture's margin is in the fixture, where a customer's would be
    assert "value: -0.05" in (F5 / "criteria.yaml").read_text(encoding="utf-8")


def test_the_margin_the_engine_compares_with_is_the_declared_value_only(tmp_path, home):
    """Move the fixture's margin and the status follows it; nothing in the engine holds
    another value to fall back to (the mutation sweep plants ``criterion_comparator_flipped``
    and ``unpaired_criterion_assessed`` against this file)."""
    crit = yaml_criteria()
    crit[1]["value"] = -0.5
    doc = f5_compare(tmp_path, home, criteria=crit).document
    c2 = next(r for r in doc["criteria_results"] if r["criterion_id"] == "C2")
    assert c2["status"] == "met" and c2["value"] == -0.5


def yaml_criteria() -> list[dict[str, Any]]:
    import yaml

    return copy.deepcopy(
        yaml.safe_load((F5 / "criteria.yaml").read_text(encoding="utf-8"))["criteria"]
    )
