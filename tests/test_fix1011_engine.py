"""Regression tests for the engine defects the independent review of 11 October 2026
confirmed by reproduction (``handoffs-orchestrator/2026-10-11_INDEPENDENT_REVIEW.md``,
sections 5 and 6): E1 (install hint), E3 (``y_pred`` with several operating points),
E4 (unquoted YAML date), E5 (version ``2.10``), E6 (unknown keys), E7 (internal references
in the customer's T7), E8 (``ledger.counted``), E9 (``auroc_wald`` description) and the
README status line. Every test here fails on ``b664500``; the note
``handoffs/2026-10-11_E_review_fixes.md`` records the command and its output.
"""

from __future__ import annotations

import copy
import json
import re
import tomllib
from pathlib import Path

import pytest
import yaml

from ap4_docx import needs_extra
from conftest import make_cohort, make_criteria, write_csv, write_yaml
from proofpack.errors import HALT_CODES, HaltError
from proofpack.gates import ingest
from proofpack.io import declare, ledger
from proofpack.io.schema import table_from_columns
from proofpack.resources import load_json_schema

pytestmark = [pytest.mark.day15, pytest.mark.fix1011]

REPO = Path(__file__).resolve().parent.parent


def _write_yaml_text(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- E1


def test_e1_the_docx_extra_line_names_the_three_packages_with_their_minimum_versions():
    from proofpack.render import docx

    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    declared = pyproject["project"]["optional-dependencies"]["docx"]
    assert tuple(docx.EXTRA_PACKAGES) == tuple(declared)
    line = docx.EXTRA_LINE
    for package in declared:
        assert f'"{package}"' in line
    assert "proofpack[" not in line
    assert str(docx.DocxExtraMissing()) == line
    assert "\n" not in line and "nothing was written" in line


def test_e1_no_text_tells_the_user_to_install_the_proofpack_package_with_an_extra():
    """In a fresh environment ``pip install "proofpack[docx]"`` fetches the PyPI
    ``0.1.0.dev1`` build, which the install page forbids."""
    pattern = re.compile(r"""pip install\s+["']?proofpack\[""")
    hits = [
        str(p.relative_to(REPO))
        for p in [
            REPO / "README.md",
            *(REPO / "src").rglob("*.py"),
            *(REPO / "tests").glob("ap4*.py"),
        ]
        if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert hits == []


# --------------------------------------------------------------------------- E3


def _two_point_criteria(**extra):
    crit = make_criteria()
    crit["operating_points"] = [
        {"id": "op1", "threshold": 0.5, "rule": ">=", "provenance": "prespecified_sap"},
        {"id": "op2", "threshold": 0.3, "rule": ">=", "provenance": "prespecified_sap"},
    ]
    crit.update(extra)
    return crit


def _ingest(cols, crit):
    return ingest(table_from_columns(cols), declare.validate_dict(crit))


def test_e3_y_pred_with_two_operating_points_and_no_declaration_halts_h04_and_says_to_declare():
    cols = make_cohort(with_y_pred=True, threshold=0.5)
    with pytest.raises(HaltError) as info:
        _ingest(cols, _two_point_criteria())
    err = info.value
    assert err.code == "H04"
    assert "y_pred_operating_point" in err.message and "criteria.yaml" in err.message
    assert "op1" in err.message and "op2" in err.message
    assert err.detail["reason"] == "y_pred_operating_point_undeclared"
    assert err.detail["operating_points"] == ["op1", "op2"]


def test_e3_the_declared_operating_point_is_the_only_one_y_pred_is_checked_at():
    cols = make_cohort(with_y_pred=True, threshold=0.5)
    result = _ingest(cols, _two_point_criteria(y_pred_operating_point="op1"))
    assert result.declarations.y_pred_operating_point == "op1"
    # the same column declared at the other point is a real mismatch, found at that point
    with pytest.raises(HaltError) as info:
        _ingest(cols, _two_point_criteria(y_pred_operating_point="op2"))
    assert info.value.code == "H04"
    assert info.value.detail["operating_point"] == "op2"
    assert info.value.detail["mismatching_rows"] > 0
    assert "not reproducible from score at operating point op2" in info.value.message
    # and a y_pred made at op2 passes when op2 is the declared one
    cols2 = make_cohort(with_y_pred=True, threshold=0.3)
    assert _ingest(cols2, _two_point_criteria(y_pred_operating_point="op2")).warnings is not None


def test_e3_a_declared_point_that_is_not_an_operating_point_is_h09():
    with pytest.raises(HaltError) as info:
        declare.validate_dict(_two_point_criteria(y_pred_operating_point="op9"))
    assert info.value.code == "H09"
    assert info.value.detail["field"] == "y_pred_operating_point"


def test_e3_one_operating_point_is_unchanged_with_or_without_the_declaration():
    cols = make_cohort(with_y_pred=True, threshold=0.5)
    assert _ingest(cols, make_criteria()).declarations.y_pred_operating_point is None
    assert _ingest(cols, make_criteria(y_pred_operating_point="op1")).table is not None
    bad = copy.deepcopy(cols)
    bad["y_pred"][3] = "1" if bad["y_pred"][3] == "0" else "0"
    with pytest.raises(HaltError) as info:
        _ingest(bad, make_criteria())
    assert info.value.code == "H04"
    assert info.value.message == "y_pred not reproducible from score at operating point op1"


def test_e3_the_halt_code_meaning_string_is_unchanged():
    assert HALT_CODES["H04"] == "y_pred not reproducible from score at a declared operating point"


def test_e3_a_table_without_y_pred_is_unaffected_by_several_operating_points():
    assert _ingest(make_cohort(), _two_point_criteria()).table is not None


def test_e3_the_key_loads_from_a_yaml_file(tmp_path: Path):
    path = write_yaml(tmp_path / "criteria.yaml", _two_point_criteria(y_pred_operating_point="op2"))
    assert declare.load(path).y_pred_operating_point == "op2"


# --------------------------------------------------------------------------- E4


def _criteria_text(tmp_path: Path, edit) -> Path:
    path = write_yaml(tmp_path / "criteria.yaml", make_criteria())
    text = path.read_text(encoding="utf-8")
    return _write_yaml_text(path, edit(text))


def test_e4_an_unquoted_yaml_date_is_read_as_its_iso_text(tmp_path: Path):
    path = _criteria_text(tmp_path, lambda t: t.replace("date: '2026-01-01'", "date: 2026-01-01"))
    assert "date: 2026-01-01" in path.read_text(encoding="utf-8")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert not isinstance(raw["criteria"][0]["date"], str)  # PyYAML gives a datetime.date
    decl = declare.load(path)
    assert decl.criteria[0]["date"] == "2026-01-01"
    assert decl.raw["criteria"][0]["date"] == "2026-01-01"


def test_e4_a_date_in_the_fairness_block_is_read_the_same_way(tmp_path: Path):
    crit = make_criteria(
        fairness={
            "criterion_of_interest": "tpr_gap",
            "attribute": "sex",
            "author": "A",
            "date": "2026-02-02",
            "justification": "j",
        }
    )
    path = write_yaml(tmp_path / "criteria.yaml", crit)
    path.write_text(path.read_text(encoding="utf-8").replace("'2026-02-02'", "2026-02-02"), "utf-8")
    assert declare.load(path).fairness["date"] == "2026-02-02"


def test_e4_only_dates_are_converted_nothing_else_is_coerced(tmp_path: Path):
    # an integer where the text date belongs is still the schema's type halt
    path = _criteria_text(tmp_path, lambda t: t.replace("date: '2026-01-01'", "date: 20260101"))
    with pytest.raises(HaltError) as info:
        declare.load(path)
    assert info.value.code == "H08" and info.value.detail["path"] == "criteria/0/date"
    # a timestamp becomes ISO text with a time part, which the YYYY-MM-DD pattern refuses
    path = _criteria_text(
        tmp_path, lambda t: t.replace("date: '2026-01-01'", "date: 2026-01-01 10:00:00")
    )
    with pytest.raises(HaltError) as info:
        declare.load(path)
    assert info.value.code == "H08" and info.value.detail["validator"] == "pattern"


# --------------------------------------------------------------------------- E5


def test_e5_a_version_is_kept_exactly_as_written(tmp_path: Path):
    def edit(text: str) -> str:
        text = text.replace("version: '1.3'", "version: 2.10").replace(
            "prior_version: '1.2'", "prior_version: 2.20"
        )
        return text

    path = _criteria_text(tmp_path, edit)
    decl = declare.load(path)
    assert decl.raw["model"]["version"] == "2.10"
    assert decl.raw["model"]["prior_version"] == "2.20"


def test_e5_only_the_two_version_scalars_are_re_read(tmp_path: Path):
    path = _criteria_text(
        tmp_path,
        lambda t: t.replace("version: '1.3'", "version: 3").replace(
            "prior_version: '1.2'", "prior_version: null"
        ),
    )
    decl = declare.load(path)
    assert decl.raw["model"]["version"] == "3"
    assert decl.raw["model"]["prior_version"] is None
    # a threshold stays a number: nothing outside the two scalars is touched
    assert decl.operating_points[0].threshold == 0.5
    assert isinstance(decl.raw["operating_points"][0]["threshold"], float)
    # a quoted version is left alone
    path = _criteria_text(tmp_path, lambda t: t)
    assert declare.load(path).raw["model"]["version"] == "1.3"


def test_e5_run_json_records_version_2_10(tmp_path: Path, monkeypatch, capsys):
    from conftest import confirmed_mapping
    from test_run_cli import _own_home, _run

    _own_home(tmp_path, monkeypatch)
    csv_path = write_csv(tmp_path / "test.csv", make_cohort())
    confirmed_mapping(csv_path)
    yml = write_yaml(tmp_path / "criteria.yaml", make_criteria())
    yml.write_text(
        yml.read_text(encoding="utf-8").replace("version: '1.3'", "version: 2.10"), "utf-8"
    )
    out = tmp_path / "pack"
    _run(csv_path, yml, out)
    capsys.readouterr()
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["declarations"]["model"]["version"] == "2.10"


# --------------------------------------------------------------------------- E6

#: (where to put the unknown key, the path the halt must name)
_CLOSED_OBJECTS = [
    ("model", "model"),
    ("classes", "classes"),
    ("score", "score"),
    ("operating_points/0", "operating_points/0"),
    ("reference_standard", "reference_standard"),
    ("indeterminates", "indeterminates"),
    ("clustering", "clustering"),
    ("prevalence/0", "prevalence/0"),
    ("subgroups/0", "subgroups/0"),
    ("criteria/0", "criteria/0"),
    ("criteria/0/scope", "criteria/0/scope"),
    ("fairness", "fairness"),
    ("ledger", "ledger"),
    ("period", "period"),
    ("egress", "egress"),
    ("egress/suppression", "egress/suppression"),
    ("bootstrap", "bootstrap"),
    ("", ""),
]


def _with_every_optional_block():
    crit = make_criteria()
    crit["criteria"][0]["scope"] = {"attribute": "sex", "level": "F"}
    crit["fairness"] = {
        "criterion_of_interest": "tpr_gap",
        "attribute": "sex",
        "author": "A",
        "date": "2026-02-02",
        "justification": "j",
    }
    crit["period"] = {"column": "event_date", "granularity": "quarter"}
    return crit


def _descend(node, path: str):
    for part in [p for p in path.split("/") if p]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def test_e6_the_fully_populated_declaration_is_valid_before_any_key_is_added():
    declare.validate_dict(_with_every_optional_block())


@pytest.mark.parametrize(("where", "named"), _CLOSED_OBJECTS)
def test_e6_an_unknown_key_halts_h08_naming_its_path(where: str, named: str):
    crit = _with_every_optional_block()
    _descend(crit, where)["margin_typo"] = 0.05
    with pytest.raises(HaltError) as info:
        declare.validate_dict(crit)
    err = info.value
    expected = f"{named}/margin_typo" if named else "margin_typo"
    assert err.code == "H08"
    assert f"declaration invalid at {expected}: unknown key" in err.message
    assert err.detail["path"] == expected
    assert "0.05" not in err.message  # the key is named, never a value


def test_e6_every_yaml_file_the_repository_ships_still_validates():
    """The criteria files under ``tests/fixtures`` (the F5 declarations and the mapping
    fixtures) load; the one composite-key file halts E01, as it was written to."""
    shipped = sorted((REPO / "tests" / "fixtures").rglob("*criteria*.yaml"))
    assert shipped, "no criteria file found"
    for path in shipped:
        if path.name == "mimic_composite_key.criteria.yaml":
            with pytest.raises(HaltError) as info:
                declare.load(path)
            assert info.value.code == "E01"
            continue
        declare.load(path)


# --------------------------------------------------------------------------- E7

#: Engineering references that mean nothing to a customer: decision ids, lens and repair
#: numbers, finding ids, script paths, build days, internal spec section references.
_INTERNAL = re.compile(
    r"DEC-\d|\b[Ll]ens(?:es)? \d|\blens's\b|\b[Rr]epair(?: round)? \d|\bFA\d?-[A-Z]*\d"
    r"|\bRG\d?-[A-Z]*\d"
    r"|scripts/|\b[Bb]uild[- ]day\b|\bR[1-6]['’]?s? sections? \d|\bD[1-5] sections? \d"
    r"|\bE1[0-9] (?:item|repair)|tests/|\btest_[a-z_]{8,}"
)


def test_e7_the_scanner_finds_what_it_is_meant_to_find():
    for text in (
        "(DEC-08; build day 5)",
        "Lens 2 (15 September 2026, FA-B1)",
        "`scripts/coverage_bar.py` v1",
        "since E11 repair 3",
        "(R2 section 3.3)",
        "D4 section 5.10",
        "`test_the_prevalence_rule_agrees_with_the_resamplers_own_draws_on_eleven_shapes`",
    ):
        assert _INTERNAL.search(text), text


def test_e7_the_conventions_file_and_the_citation_register_carry_no_internal_reference():
    for name in ("conventions_T7.md", "citations.yaml"):
        text = (REPO / "design" / name).read_text(encoding="utf-8")
        if name == "citations.yaml":
            # the register's own header comments are not printed; its entries are
            text = "\n".join(
                line for line in text.splitlines() if not line.lstrip().startswith("#")
            )
        assert _INTERNAL.findall(text) == [], name


def test_e7_the_rendered_customer_documents_carry_no_internal_reference():
    golden = REPO / "tests" / "fixtures" / "golden"
    for name in ("T1.html", "T2.html", "T7.html", "T8.html"):
        page = (golden / name).read_text(encoding="utf-8")
        text = re.sub(r"<[^>]+>", " ", page)
        assert _INTERNAL.findall(text) == [], name


def test_e7_the_unverified_markings_survive():
    """The scrub keeps every [unverified] marking: the register still has eleven open
    entries and T7 prints each one with the marking and the words beside it."""
    entries = yaml.safe_load((REPO / "design" / "citations.yaml").read_text(encoding="utf-8"))
    open_ids = [c["id"] for c in entries["citations"] if c["verified"] is not True]
    assert len(open_ids) == 11 and "newcombe_1998_paired" not in open_ids
    page = (REPO / "tests" / "fixtures" / "golden" / "T7.html").read_text(encoding="utf-8")
    for citation_id in open_ids:
        row = re.search(rf'<li data-open="{citation_id}">(.*?)</li>', page, re.S)
        assert row is not None, citation_id
        assert "[unverified]" in row.group(1) and "citation pending verification" in row.group(1)
    conventions = (REPO / "design" / "conventions_T7.md").read_text(encoding="utf-8")
    assert conventions.count("[unverified]") >= 2


# --------------------------------------------------------------------------- E8


def test_e8_a_run_that_added_nothing_to_the_ledger_is_not_counted(tmp_path: Path):
    key = ledger.test_set_key(["1", "0"], None, ["1", "0"])
    nothing = ledger.peek(key, counts_this_run=False, limit=None, home=tmp_path)
    assert nothing.as_dict()["acceptance_runs"] == 0
    assert nothing.as_dict()["counted"] is False
    added = ledger.peek(key, counts_this_run=True, limit=None, home=tmp_path)
    assert added.as_dict()["acceptance_runs"] == 1
    assert added.as_dict()["counted"] is True
    (tmp_path / ledger.LEDGER_FILE).write_text("not json", encoding="utf-8")
    unreadable = ledger.peek(key, counts_this_run=True, limit=None, home=tmp_path)
    assert unreadable.as_dict()["acceptance_runs"] is None
    assert unreadable.as_dict()["counted"] is False


def test_e8_a_run_with_no_licence_writes_counted_false_and_a_licensed_run_true(
    tmp_path: Path, monkeypatch, capsys
):
    from conftest import confirmed_mapping
    from test_run_cli import _own_home, _run

    csv_path = write_csv(tmp_path / "test.csv", make_cohort())
    confirmed_mapping(csv_path)
    yml = write_yaml(tmp_path / "criteria.yaml", make_criteria())

    home = _own_home(tmp_path, monkeypatch, licence=False)
    out = tmp_path / "unlicensed"
    _run(csv_path, yml, out)
    capsys.readouterr()
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["ledger"]["acceptance_runs"] == 0
    assert doc["ledger"]["counted"] is False
    assert not (home / ledger.LEDGER_FILE).exists()

    from conftest import write_licence

    write_licence(home / "proofpack.lic")
    out = tmp_path / "licensed"
    _run(csv_path, yml, out)
    capsys.readouterr()
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["ledger"]["acceptance_runs"] == 1
    assert doc["ledger"]["counted"] is True


def _t8_counted_cell(counted: bool, acceptance_runs: int | None) -> str:
    from assembler import assemble
    from proofpack.render import html
    from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site

    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    doc["ledger"] = {
        "test_set_sha256": "0" * 64,
        "warn_limit": None,
        "counted": counted,
        "acceptance_runs": acceptance_runs,
    }
    page = html.render_t8(doc)
    cell = re.search(r'<th scope="row">Counted</th><td>(.*?)</td>', page, re.S)
    assert cell is not None
    return cell.group(1)


def test_e8_t8_prints_yes_only_for_a_run_that_added_to_the_ledger():
    assert _t8_counted_cell(True, 4).startswith("yes")
    not_added = _t8_counted_cell(False, 0)
    assert not_added.startswith("no") and "added nothing to the ledger" in not_added
    unreadable = _t8_counted_cell(False, None)
    assert unreadable.startswith("no") and "could not be read or written" in unreadable


def test_e8_the_output_schema_still_validates_both_values_and_says_what_counted_means():
    import jsonschema

    schema = load_json_schema("output_schema_v1.json")
    node = schema["properties"]["ledger"]
    assert "true only when this run added one to the ledger" in node["description"]
    assert "added one to the test-set ledger" in node["properties"]["counted"]["description"]
    for counted in (True, False):
        jsonschema.validate(
            {
                "test_set_sha256": "0" * 64,
                "acceptance_runs": 0,
                "warn_limit": None,
                "counted": counted,
            },
            {**node, "$defs": schema["$defs"]},
        )


# --------------------------------------------------------------------------- E9


def test_e9_auroc_wald_is_described_as_the_interval_that_is_not_primary():
    from proofpack.stats.discrimination import auroc_number

    schema = load_json_schema("output_schema_v1.json")
    text = schema["$defs"]["thresholdFree"]["properties"]["auroc_wald"]["description"]
    assert "the logit interval (method delong_logit) when the Wald interval is primary" in text
    assert "the Wald interval (method delong_wald) when the logit interval is primary" in text
    assert "shown beside the logit interval" not in text
    # the behaviour the text describes: AUROC below 0.9 with 30 or more per class makes the
    # Wald interval primary and puts the logit interval under auroc_wald
    import numpy as np

    rng = np.random.default_rng(7)
    pos = rng.normal(0.8, 1.0, 60)
    neg = rng.normal(0.0, 1.0, 60)
    scores = np.concatenate([pos, neg])
    labels = np.concatenate([np.ones(60, bool), np.zeros(60, bool)])
    result = auroc_number(scores, labels)
    assert result.auroc.method == "delong_wald"
    assert result.auroc_secondary.method == "delong_logit"


# --------------------------------------------------------------------------- README


def test_readme_status_says_sales_opened_on_9_october_2026():
    status = (
        (REPO / "README.md").read_text(encoding="utf-8").split("## Status", 1)[1].split("##", 1)[0]
    )
    assert "not yet on sale" not in status and "still being built" not in status
    assert "on sale since 9 October 2026" in status


# ----------------------------------------------------------------------------
# Repair round, B1: the T8 ledger row label and the yes branch (lens 1)
# ----------------------------------------------------------------------------


def _t8_runs_row(counted: bool, acceptance_runs: int | None) -> tuple[str, str]:
    """The T8 ledger table's runs row: (label, value)."""
    from assembler import assemble
    from proofpack.render import html
    from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site

    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    doc["ledger"] = {
        "test_set_sha256": "0" * 64,
        "warn_limit": None,
        "counted": counted,
        "acceptance_runs": acceptance_runs,
    }
    page = html.render_t8(doc)
    row = re.search(
        r'<tr><th scope="row">(Acceptance runs recorded[^<]*)</th><td class="num">(.*?)</td>',
        page,
        re.S,
    )
    assert row is not None
    return row.group(1), row.group(2)


def test_b1_the_runs_row_label_says_including_this_run_only_when_it_was_counted():
    label, value = _t8_runs_row(True, 4)
    assert "including this run" in label and value == "4"
    for runs in (0, None):
        label, _ = _t8_runs_row(False, runs)
        assert "including this run" not in label
        assert "not included" in label


def test_b1_the_yes_branch_does_not_claim_a_write_the_engine_cannot_know_of():
    cell = _t8_counted_cell(True, 4)
    assert cell.startswith("yes")
    assert "W15" in cell and "console" in cell


def _licensed_run_with_commit(tmp_path: Path, monkeypatch, capsys, *, commit_fails: bool):
    from conftest import confirmed_mapping
    from proofpack.run import ledger as run_ledger
    from test_run_cli import _own_home, _run

    csv_path = write_csv(tmp_path / "test.csv", make_cohort())
    confirmed_mapping(csv_path)
    yml = write_yaml(tmp_path / "criteria.yaml", make_criteria())
    _own_home(tmp_path, monkeypatch)
    if commit_fails:
        monkeypatch.setattr(run_ledger, "commit", lambda result: ledger._w15(OSError("disk full")))
    out = tmp_path / "pack"
    rc = _run(csv_path, yml, out, "--templates", "T8")
    printed = capsys.readouterr().out
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    return rc, printed, doc, (out / "T8.html").read_text(encoding="utf-8")


def test_b1_a_failed_ledger_commit_leaves_run_json_counted_false_and_the_stored_count(
    tmp_path: Path, monkeypatch, capsys
):
    rc, printed, doc, page = _licensed_run_with_commit(
        tmp_path, monkeypatch, capsys, commit_fails=True
    )
    assert "[W15]" in printed and "were not counted" in printed
    assert doc["ledger"]["counted"] is False
    assert doc["ledger"]["acceptance_runs"] == 0
    assert doc["manifest"]["ledger_count"] == 0
    # the rendered page was written before the commit: it must not assert the write
    cell = re.search(r'<th scope="row">Counted</th><td>(.*?)</td>', page, re.S)
    assert cell is not None and "W15" in cell.group(1)


def test_b1_a_run_whose_commit_succeeds_keeps_counted_true(tmp_path: Path, monkeypatch, capsys):
    rc, printed, doc, _ = _licensed_run_with_commit(
        tmp_path, monkeypatch, capsys, commit_fails=False
    )
    assert "W15" not in printed
    assert doc["ledger"]["counted"] is True
    assert doc["ledger"]["acceptance_runs"] == 1
    assert doc["manifest"]["ledger_count"] == 1


@pytest.mark.ap4
@needs_extra
def test_b1_the_docx_t8_carries_the_same_label_and_counted_wording_as_the_html(
    tmp_path: Path, monkeypatch, capsys
):
    # Needs the [docx] extra: skipped in the main pytest job, run by the
    # docx-extra job (-m ap4 with PROOFPACK_REQUIRE_DOCX=1, where a skip is
    # refused). Gate run on 3dcb228 failed with "No module named 'docx'".
    from ap4_docx import cell_texts
    from conftest import confirmed_mapping
    from test_run_cli import _own_home, _run

    csv_path = write_csv(tmp_path / "test.csv", make_cohort())
    confirmed_mapping(csv_path)
    yml = write_yaml(tmp_path / "criteria.yaml", make_criteria())
    _own_home(tmp_path, monkeypatch)
    out = tmp_path / "pack"
    _run(csv_path, yml, out, "--templates", "T8", "--format", "docx")
    capsys.readouterr()
    cells = cell_texts(out / "T8.docx")
    assert "Acceptance runs recorded (including this run)" in cells
    counted = [c for c in cells if c.startswith("yes (")]
    assert counted and "W15" in counted[0]
    # a licensed run with no criteria adds nothing: the label must not say it is included
    yml2 = write_yaml(tmp_path / "criteria_none.yaml", make_criteria(criteria=[]))
    out2 = tmp_path / "pack2"
    _run(csv_path, yml2, out2, "--templates", "T8", "--format", "docx")
    capsys.readouterr()
    cells2 = cell_texts(out2 / "T8.docx")
    assert not any("including this run" in c for c in cells2)
    assert "Acceptance runs recorded (stored count; this run not included)" in cells2
