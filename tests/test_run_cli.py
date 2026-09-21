"""Build day 7 (E7): ``proofpack run`` end to end - gates, document, exit codes, licence.

The synthetic cohort is ``conftest.make_cohort`` with the site column rewritten so that
``S3`` holds exactly 30 rows (F8). The criteria file holds one criterion that is met, one
on the 30-row cell that is not met (``attainable_at_n: false``), one that is not
assessable (``f1`` at a subgroup scope: the day-5 rows carry no F1 cell) and a fairness
bound. Every run goes through ``proofpack.cli.main``; the subprocess test runs
``python -m proofpack.cli run`` with no licence installed and reads exit 4 with the
watermark.
"""

from __future__ import annotations

import copy
import json
import os
import re
import socket
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jsonschema
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
from proofpack.cli import main
from proofpack.errors import EXIT_HALT, EXIT_LICENCE, EXIT_OK, EXIT_WARNINGS
from proofpack.licence.verify import WATERMARK_EXPIRED, WATERMARK_TRIAL
from proofpack.manifest import REFERENCE_PLATFORM
from proofpack.resources import load_json_schema
from proofpack.run import assemble_run, default_mapping_path
from test_criteria import (
    CLUSTERED_CRITERIA,
    CRITERIA,
    FAIRNESS,
    Z_975,
    assert_no_met_row_is_marked_unattainable,
    clustered_cohort_with_one_wrong_negative_in_s3,
    cohort_with_a_thirty_row_site,
)
from test_subgroups import VERDICT_WORDS, walk_keys_and_strings

pytestmark = pytest.mark.day7

REPO = Path(__file__).resolve().parent.parent


def _criteria() -> dict[str, Any]:
    return make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)


def _prepare(tmp_path: Path, cols=None, crit=None) -> tuple[Path, Path]:
    cols = cols if cols is not None else cohort_with_a_thirty_row_site()
    csv_path = write_csv(tmp_path / "test.csv", cols)
    yml = write_yaml(tmp_path / "criteria.yaml", crit if crit is not None else _criteria())
    confirmed_mapping(csv_path)
    return csv_path, yml


def _run(csv_path: Path, yml: Path, out: Path, *flags: str, registry="ephemeral") -> int:
    reg = ephemeral_registry() if registry == "ephemeral" else registry
    return main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), *flags],
        registry=reg,
    )


def _own_home(tmp_path: Path, monkeypatch, licence: bool = True, **kw) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("PROOFPACK_HOME", str(home))
    if licence:
        write_licence(home / "proofpack.lic", **kw)
    return home


@pytest.fixture
def run_document(tmp_path: Path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    rc = _run(csv_path, yml, out)
    printed = capsys.readouterr().out
    assert rc == EXIT_OK, printed
    return json.loads((out / "run.json").read_text(encoding="utf-8")), printed, out


def test_the_full_run_statuses_reason_codes_and_attainability(run_document):
    doc, printed, out = run_document
    rows = {r["criterion_id"]: r for r in doc["criteria_results"] if r["scope"] == "overall"}
    assert rows["C_met"]["status"] == "met"
    n30 = next(r for r in doc["criteria_results"] if r["criterion_id"] == "C_n30")
    assert n30["status"] == "not_met" and n30["reason_code"] == "statistic_compared"
    assert n30["n"] == 30 and n30["attainable_at_n"] is False
    assert n30["max_lower_bound_at_n"] == pytest.approx(30 / (30 + Z_975**2))
    f1 = [r for r in doc["criteria_results"] if r["criterion_id"] == "C_f1_site"]
    assert {r["status"] for r in f1} == {"not_assessable"}
    assert {r["reason_code"] for r in f1} == {"metric_not_computed_for_scope"}
    fair = [r for r in doc["criteria_results"] if r["criterion_id"] == "fairness:tpr_gap"]
    assert len(fair) == 1 and fair[0]["status"] in ("met", "not_met")
    assert "criteria rows:" in printed and "run written:" in printed
    assert "Next step:" in printed and "/docs/run" in printed
    assert (out / "run.json").exists() and (out / "ingest_report.json").exists()
    assert not (out / "mapping.json").exists()  # DEC-26
    assert_no_met_row_is_marked_unattainable(doc["criteria_results"])


def _crit(**kw) -> dict[str, Any]:
    base = {
        "id": "C",
        "metric": "sensitivity",
        "operating_point": "op1",
        "scope": "overall",
        "statistic": "ci_lower_bound",
        "comparator": ">=",
        "value": 0.85,
        "author": "A",
        "date": "2026-01-01",
        "justification": "j",
    }
    base.update(kw)
    return base


def test_point_estimate_criteria_on_f1_and_mcc_read_method_none_as_not_assessable(
    tmp_path: Path, monkeypatch
):
    """Repair 1 of 21 September (lens 1 B1). On the i.i.d. synthetic run overall.op1.f1
    and .mcc carry method none with not_estimable_reason analytic_ci_unavailable (est
    0.6620689655172414 and 0.4821183187439812, measured). At ab729d3 the two
    point_estimate rows came back not_met (F1_pe, >= 0.70) and met (MCC_pe, >= 0.40)
    with method none and reason_code statistic_compared."""
    _own_home(tmp_path, monkeypatch)
    crit = make_criteria(
        criteria=[
            _crit(id="F1_pe", metric="f1", statistic="point_estimate", value=0.70),
            _crit(id="MCC_pe", metric="mcc", statistic="point_estimate", value=0.40),
        ],
        fairness=None,
    )
    csv_path, yml = _prepare(tmp_path, crit=crit)
    out = tmp_path / "pack"
    assert _run(csv_path, yml, out, "--offline") == EXIT_OK
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    rows = {r["criterion_id"]: r for r in doc["criteria_results"]}
    assert set(rows) == {"F1_pe", "MCC_pe"}
    expected = (("F1_pe", "f1", 0.6620689655172414), ("MCC_pe", "mcc", 0.4821183187439812))
    for cid, metric, est in expected:
        number = doc["overall"]["op1"][metric]
        assert number["method"] == "none" and number["ci_lo"] is None and number["ci_hi"] is None
        assert number["not_estimable_reason"] == "analytic_ci_unavailable"
        assert number["est"] == pytest.approx(est, abs=1e-12)
        row = rows[cid]
        assert (row["status"], row["reason_code"]) == ("not_assessable", "no_interval"), row
        assert row["compared_value"] is None and row["method"] == "none"
        assert row["detail"]["not_estimable_reason"] == "analytic_ci_unavailable"
        assert row["metric_ref"] == f"overall.op1.{metric}"
    jsonschema.validate(doc, load_json_schema("output_schema_v1.json"))


def test_b2_a_met_clustered_cell_carries_no_attainability_flag_through_run(
    tmp_path: Path, monkeypatch
):
    """Repair 1 of 21 September (lens 1 B2), the CLI route of the construction in
    test_criteria: at ab729d3 sp_S3 and acc_S3 were met (compared_value 0.9) beside
    attainable_at_n False and max_lower_bound_at_n 0.8864866068260313."""
    _own_home(tmp_path, monkeypatch)
    crit = make_criteria(
        clustering={"unit": "case_id", "declared_by": "test"},
        criteria=copy.deepcopy(CLUSTERED_CRITERIA),
        fairness=None,
    )
    csv_path, yml = _prepare(tmp_path, clustered_cohort_with_one_wrong_negative_in_s3(), crit)
    out = tmp_path / "pack"
    assert _run(csv_path, yml, out, "--offline") in (EXIT_OK, EXIT_WARNINGS)
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    rows = {r["criterion_id"]: r for r in doc["criteria_results"]}
    for cid in ("sp_S3", "acc_S3"):
        row = rows[cid]
        assert (row["status"], row["compared_value"], row["n"]) == ("met", 0.9, 30), row
        assert row["method"] == "cluster_bootstrap_percentile"
        assert row["attainable_at_n"] is None and row["max_lower_bound_at_n"] is None
        assert row["detail"] == {"attainability_not_computed": "method_not_wilson"}
    assert_no_met_row_is_marked_unattainable(doc["criteria_results"])
    jsonschema.validate(doc, load_json_schema("output_schema_v1.json"))


def test_a_zero_denominator_site_row_is_annotated_method_not_wilson_through_run(
    tmp_path: Path, monkeypatch
):
    """Repair 2 of 21 September (lens 2 FA-N1), the CLI route: 400 rows, the 30 S3 rows
    all y_true 0, criterion sensitivity ci_lower_bound >= 0.8 at {site, S3}. At 02d00c5
    the row read n 0, method none, not_assessable / no_interval, detail
    {'not_estimable_reason': 'zero_denominator'} with no attainability_not_computed key."""
    _own_home(tmp_path, monkeypatch)
    cols = cohort_with_a_thirty_row_site()
    for i in range(30):
        cols["y_true"][i] = "0"
    crit = make_criteria(
        criteria=[
            {
                "id": "se_S3",
                "metric": "sensitivity",
                "operating_point": "op1",
                "scope": {"attribute": "site", "level": "S3"},
                "statistic": "ci_lower_bound",
                "comparator": ">=",
                "value": 0.8,
                "author": "Dr A.",
                "date": "2026-01-01",
                "justification": "test fixture",
            }
        ],
        fairness=None,
    )
    csv_path, yml = _prepare(tmp_path, cols, crit)
    out = tmp_path / "pack"
    assert _run(csv_path, yml, out, "--offline") in (EXIT_OK, EXIT_WARNINGS)
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    [row] = doc["criteria_results"]
    assert (row["criterion_id"], row["n"], row["method"]) == ("se_S3", 0, "none")
    assert (row["status"], row["reason_code"]) == ("not_assessable", "no_interval")
    assert row["compared_value"] is None
    assert row["attainable_at_n"] is None and row["max_lower_bound_at_n"] is None
    assert row["detail"] == {
        "not_estimable_reason": "zero_denominator",
        "attainability_not_computed": "method_not_wilson",
    }
    assert_no_met_row_is_marked_unattainable(doc["criteria_results"])
    jsonschema.validate(doc, load_json_schema("output_schema_v1.json"))


def test_the_manifest_fields_and_the_licence_echo(run_document):
    doc, _, _ = run_document
    m = doc["manifest"]
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", m["run_id"]
    )
    assert m["engine_version"] == "0.1.0.dev1"
    assert re.fullmatch(r".+-cp3\d+", m["platform"])
    # False on the Windows build machine, True on the ubuntu CI runner (linux-x86_64-cp312,
    # run 21 Sept 16:07 UTC): the flag is the comparison, not a constant
    assert m["reference_platform"] is (m["platform"] == REFERENCE_PLATFORM)
    assert re.fullmatch(r"3\.\d+\.\d+", m["python"])
    assert m["numpy"] and (m["scipy"] is None or isinstance(m["scipy"], str))
    for key in ("input_sha256", "criteria_sha256", "mapping_sha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", m[key]), key
    assert (m["seed"], m["B"]) == (20240101, 200)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", m["started"])
    assert isinstance(m["duration_s"], float) and m["duration_s"] >= 0
    assert m["licence_id"].startswith("lic_") and m["tier"] == "annual"
    assert m["ledger_count"] == 1 and m["watermark"] is None
    assert doc["ledger"] == {
        "test_set_sha256": doc["ledger"]["test_set_sha256"],
        "acceptance_runs": 1,
        "warn_limit": 3,
        "counted": True,
    }


def test_the_document_validates_and_is_canonical_json(run_document):
    doc, _, out = run_document
    schema = load_json_schema("output_schema_v1.json")
    v = jsonschema.Draft202012Validator(schema)
    assert list(v.iter_errors(doc)) == []
    raw = (out / "run.json").read_bytes()
    assert raw == (
        json.dumps(
            doc,
            sort_keys=True,
            indent=1,
            separators=(",", ": "),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    assert not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw
    assert b"Infinity" not in raw and b"NaN" not in raw
    assert doc["halts"] == [] and doc["suppression_log"] == [] and doc["guidance_refs"] == []
    assert doc["declarations"]["criteria"][0]["justification"] == "j"
    assert doc["overall"]["threshold_free"]["roc"][0] == [0.0, 0.0, None]
    assert doc["flow"]["dev_rows"] == 0


def test_the_status_words_appear_only_under_criteria_results(run_document):
    doc, _, _ = run_document

    def words(token):
        return set(re.split(r"[^a-z]+", token.lower()))

    rest = {k: v for k, v in doc.items() if k not in ("declarations", "criteria_results")}
    for token in walk_keys_and_strings(rest):
        assert not (words(token) & VERDICT_WORDS), token
    seen = {t for t in walk_keys_and_strings(doc["criteria_results"]) if t in VERDICT_WORDS}
    assert seen == {"met", "not_met"}
    for token in walk_keys_and_strings(doc["criteria_results"]):
        assert not (words(token) & {"pass", "fail", "verdict"}), token


def test_a_criteria_file_lacking_a_justification_is_h08_exit_3_and_no_document(
    tmp_path: Path, monkeypatch, capsys
):
    _own_home(tmp_path, monkeypatch)
    crit = _criteria()
    del crit["criteria"][0]["justification"]
    csv_path, yml = _prepare(tmp_path, crit=crit)
    out = tmp_path / "pack"
    assert _run(csv_path, yml, out) == EXIT_HALT
    err = capsys.readouterr().err
    assert err.splitlines()[0] == "HALT H08: criterion C_met lacks justification"
    assert "No document was written." in err and not out.exists()


def test_auroc_at_an_operating_point_is_h09_exit_3(tmp_path: Path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    crit = _criteria()
    crit["criteria"][3]["operating_point"] = "op1"  # C_auroc
    csv_path, yml = _prepare(tmp_path, crit=crit)
    out = tmp_path / "pack"
    assert _run(csv_path, yml, out) == EXIT_HALT
    err = capsys.readouterr().err
    assert err.splitlines()[0].startswith("HALT H09: criterion C_auroc names an operating point")
    assert not out.exists()


def test_no_confirmed_mapping_is_h07_run_proofpack_map_first(tmp_path: Path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    cols = cohort_with_a_thirty_row_site()
    csv_path = write_csv(tmp_path / "test.csv", cols)
    yml = write_yaml(tmp_path / "criteria.yaml", _criteria())
    out = tmp_path / "pack"
    assert not default_mapping_path(csv_path).exists()
    assert default_mapping_path(csv_path) == tmp_path / "test.csv.mapping.json"
    assert _run(csv_path, yml, out) == EXIT_HALT
    err = capsys.readouterr().err
    assert err.splitlines()[0].startswith("HALT H07: run proofpack map first")
    assert not out.exists()
    # a --mapping that does not exist
    assert _run(csv_path, yml, out, "--mapping", str(tmp_path / "nope.json")) == EXIT_HALT
    assert "run proofpack map first" in capsys.readouterr().err
    # a proposed (unconfirmed) file beside the input
    from proofpack.io.mapping import map_headers

    map_headers(list(cols), cols).write(default_mapping_path(csv_path))
    assert _run(csv_path, yml, out) == EXIT_HALT
    assert "this one was not confirmed" in capsys.readouterr().err
    assert not out.exists()
    # confirmed: the same command runs
    confirmed_mapping(csv_path)
    assert _run(csv_path, yml, out) == EXIT_OK
    assert (out / "run.json").exists()


def test_offline_opens_no_socket(tmp_path: Path, monkeypatch):
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path)

    def refuse(*a, **k):
        raise AssertionError("a socket was opened")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    assert _run(csv_path, yml, tmp_path / "pack", "--offline") == EXIT_OK
    assert (tmp_path / "pack" / "run.json").exists()


def test_no_licence_still_writes_the_json_with_the_watermark_and_exits_4(
    tmp_path: Path, monkeypatch, capsys
):
    _own_home(tmp_path, monkeypatch, licence=False)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    assert _run(csv_path, yml, out, registry=None) == EXIT_LICENCE
    printed = capsys.readouterr().out
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["manifest"]["watermark"] == WATERMARK_EXPIRED
    assert doc["manifest"]["licence_id"] is None and doc["manifest"]["tier"] is None
    assert doc["criteria_results"]  # the numbers are never withheld
    assert "licence refused (no_file)" in printed and "licence install FILE" in printed


def test_expired_past_grace_is_exit_4_with_the_watermark(tmp_path: Path, monkeypatch):
    _own_home(tmp_path, monkeypatch, expires=datetime.now(UTC) - timedelta(days=60))
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    assert _run(csv_path, yml, out) == EXIT_LICENCE
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["manifest"]["watermark"] == WATERMARK_EXPIRED
    assert doc["manifest"]["licence_id"].startswith("lic_")


def test_grace_is_a_full_run_with_the_watermark_and_a_trial_carries_trial(
    tmp_path: Path, monkeypatch
):
    _own_home(tmp_path, monkeypatch, expires=datetime.now(UTC) - timedelta(days=5))
    csv_path, yml = _prepare(tmp_path)
    assert _run(csv_path, yml, tmp_path / "p1") == EXIT_OK
    doc = json.loads((tmp_path / "p1" / "run.json").read_text(encoding="utf-8"))
    assert doc["manifest"]["watermark"] == WATERMARK_EXPIRED
    home = Path(os.environ["PROOFPACK_HOME"])
    write_licence(home / "proofpack.lic", tier="trial", issued=datetime.now(UTC))
    assert _run(csv_path, yml, tmp_path / "p2") == EXIT_OK
    doc = json.loads((tmp_path / "p2" / "run.json").read_text(encoding="utf-8"))
    assert doc["manifest"]["watermark"] == WATERMARK_TRIAL and doc["manifest"]["tier"] == "trial"


def test_a_refused_licence_file_is_exit_4_with_the_watermark(tmp_path: Path, monkeypatch):
    home = _own_home(tmp_path, monkeypatch)
    (home / "proofpack.lic").write_text("garbage", encoding="ascii")
    csv_path, yml = _prepare(tmp_path)
    assert _run(csv_path, yml, tmp_path / "p") == EXIT_LICENCE
    doc = json.loads((tmp_path / "p" / "run.json").read_text(encoding="utf-8"))
    assert doc["manifest"]["watermark"] == WATERMARK_EXPIRED


def test_the_ledger_warning_w14_is_exit_2_and_in_the_document(tmp_path: Path, monkeypatch):
    _own_home(tmp_path, monkeypatch)
    crit = _criteria()
    crit["ledger"] = {"warn_after_acceptance_runs": 2}
    csv_path, yml = _prepare(tmp_path, crit=crit)
    for i in (1, 2):
        assert _run(csv_path, yml, tmp_path / f"p{i}") == EXIT_OK, i
    assert _run(csv_path, yml, tmp_path / "p3") == EXIT_WARNINGS
    doc = json.loads((tmp_path / "p3" / "run.json").read_text(encoding="utf-8"))
    assert [w["code"] for w in doc["warnings"]] == ["W14"]
    assert doc["warnings"][0]["params"] == {"count": 3, "limit": 2}
    assert doc["manifest"]["ledger_count"] == 3 and doc["ledger"]["warn_limit"] == 2
    # without a ledger block: no limit, no warning, the count still reads
    crit.pop("ledger")
    yml = write_yaml(tmp_path / "c2.yaml", crit)
    assert _run(csv_path, yml, tmp_path / "p4") == EXIT_OK
    doc = json.loads((tmp_path / "p4" / "run.json").read_text(encoding="utf-8"))
    assert doc["warnings"] == [] and doc["ledger"]["warn_limit"] is None
    assert doc["manifest"]["ledger_count"] == 4


def test_a_blank_case_id_is_s05_at_ingest_naming_the_count(tmp_path: Path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    cols = make_cohort(n=60, with_case_id=True)
    cols["case_id"][0], cols["case_id"][7], cols["case_id"][8] = "", "NA", None
    crit = make_criteria(clustering={"unit": "case_id", "declared_by": "t"})
    csv_path, yml = _prepare(tmp_path, cols, crit)
    out = tmp_path / "pack"
    assert _run(csv_path, yml, out) == EXIT_HALT
    err = capsys.readouterr().err
    assert (
        err.splitlines()[0]
        == "HALT S05: case_id is blank in 3 row(s); fill every case id or drop the column"
    )
    assert '"count": 3' in err and not out.exists()


def test_a_y_pred_only_table_gives_calibration_null_with_no_score_column(
    tmp_path: Path, monkeypatch
):
    _own_home(tmp_path, monkeypatch)
    cols = make_cohort(n=200, with_y_pred=True)
    del cols["score"]
    crit = make_criteria(criteria=[])
    csv_path, yml = _prepare(tmp_path, cols, crit)
    out = tmp_path / "pack"
    rc = _run(csv_path, yml, out)
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["calibration"] is None
    assert doc["calibration_suppressed_reason"]["reason"] == "no_score_column"
    assert doc["overall"] is None
    assert doc["subgroups"] and doc["criteria_results"] == []
    assert (
        list(
            jsonschema.Draft202012Validator(load_json_schema("output_schema_v1.json")).iter_errors(
                doc
            )
        )
        == []
    )


def test_flow_reconciles_with_dev_rows(tmp_path: Path, monkeypatch):
    _own_home(tmp_path, monkeypatch)
    cols = make_cohort(n=100)
    cols["dataset"] = ["dev"] * 10 + ["test"] * 90
    cols["y_true"][0] = None  # a dev row's missing label is counted nowhere but in dev_rows
    cols["y_true"][20] = None
    crit = make_criteria(criteria=[])
    csv_path, yml = _prepare(tmp_path, cols, crit)
    out = tmp_path / "pack"
    rc = _run(csv_path, yml, out)
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    flow = json.loads((out / "run.json").read_text(encoding="utf-8"))["flow"]
    assert flow["dev_rows"] == 10 and flow["excluded_missing_label"] == 1 and flow["analysed"] == 89
    assert flow["rows_read"] == (
        flow["dev_rows"]
        + flow["excluded_missing_label"]
        + flow["excluded_missing_score"]
        + flow["indeterminate"]
        + flow["analysed"]
    )


def test_a_clustered_run_has_no_overall_block_and_cluster_bootstrap_cells(
    tmp_path: Path, monkeypatch
):
    _own_home(tmp_path, monkeypatch)
    cols = make_cohort(n=200, with_case_id=True)
    cols["case_id"] = [f"c{i // 2}" for i in range(200)]
    crit = make_criteria(criteria=[], clustering={"unit": "case_id", "declared_by": "t"})
    csv_path, yml = _prepare(tmp_path, cols, crit)
    out = tmp_path / "pack"
    assert _run(csv_path, yml, out) in (EXIT_OK, EXIT_WARNINGS)
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["overall"] is None and doc["flow"]["clustered"] is True
    method = doc["subgroups"][0]["metrics"]["op1"]["sensitivity"]["number"]["method"]
    assert method in ("cluster_bootstrap_percentile", "none")


def test_assemble_run_writes_only_the_ledger_file_under_home(tmp_path: Path, monkeypatch):
    """Lens 1 of 21 September, RG-N1: the earlier test walked tmp_path's top level only
    and the docstring said 'writes nothing'; assemble_run writes <home>/ledger.json
    through ledger.record_run. The walk is recursive and names the one addition."""
    home = _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path)
    before = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")}
    outcome = assemble_run(csv_path, yml, registry=ephemeral_registry())
    assert outcome.exit_code == EXIT_OK and outcome.document["criteria_results"]
    after = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")}
    assert after - before == {"home/ledger.json"}
    assert (home / "ledger.json").exists() and not (tmp_path / "pack").exists()


def test_python_m_proofpack_cli_run_in_a_subprocess_without_a_licence(tmp_path: Path):
    """The console form a customer types, with no licence installed: exit 4, run.json
    written with the watermark, the one-line fix printed. The E7 build note quotes the
    lines from both shells."""
    home = tmp_path / "home"
    home.mkdir()
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    env = {**os.environ, "PROOFPACK_HOME": str(home), "PYTHONIOENCODING": "utf-8"}
    env.pop("PROOFPACK_LICENCE", None)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proofpack.cli",
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--out",
            str(out),
            "--offline",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO),
    )
    assert proc.returncode == EXIT_LICENCE, proc.stderr
    assert "run written:" in proc.stdout and "licence refused (no_file)" in proc.stdout
    assert WATERMARK_EXPIRED in proc.stdout and "Traceback" not in proc.stderr
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["manifest"]["watermark"] == WATERMARK_EXPIRED


def test_the_mutation_sweep_declares_a_day7_list_with_no_duplicate_ids():
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "mutation_sweep.py"), "--list"],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    ids = [ln.split()[0] for ln in lines]
    assert len(ids) == len(set(ids))
    day7 = [ln for ln in lines if " day7 " in ln]
    assert len(day7) >= 12
    assert sum(" day5 " in ln for ln in lines) == 34 and sum(" day6 " in ln for ln in lines) == 112
