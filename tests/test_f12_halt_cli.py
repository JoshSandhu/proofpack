"""F12 in full (build day 13, E13; D1 section 3.2, section 10 gate 4): every HALT fixture
of ``proofpack.halt_fixtures`` run through the real CLI in a child process
(``python -m proofpack.cli run|compare ... --offline``) exits 3, prints its own code on
the first stderr line, says no document was written, leaves ``--out`` absent and changes
no file under the fixture's directory (inputs and ``PROOFPACK_HOME``).

Measured at 5154468 on 5 October 2026 (win-amd64-cp314): ``tests/test_halt_gates.py::
test_gate_exits_3_and_writes_nothing`` wrote no ``<input>.mapping.json``, so H01-H06 and
H11 exited 3 by printing ``HALT H07: run proofpack map first`` and the test, which read
only the exit code, passed. The two ``check`` tests below plant exactly that and a
fixture that writes a file, and assert ``check`` reports them.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from conftest import make_criteria
from proofpack import halt_fixtures as hf
from proofpack.errors import EXIT_HALT, FLAG_ONLY_CODES, HALT_CODES, MAPPING_CODES, SCHEMA_CODES

pytestmark = [pytest.mark.day13, pytest.mark.fixture]


@pytest.mark.parametrize("fixture", hf.FIXTURES, ids=[f.id for f in hf.FIXTURES])
def test_f12_each_halt_fixture_through_the_cli_exits_3_prints_its_code_and_writes_nothing(
    fixture: hf.HaltFixture, tmp_path: Path
):
    r = hf.check(fixture, tmp_path / "work", hf.subprocess_cli)
    assert r["exit_code"] == EXIT_HALT, r
    assert r["printed_code"] == fixture.code, r
    assert r["no_document_line"] is True, r
    assert r["out_exists"] is False, r
    assert r["files_changed"] == [], r
    assert r["ok"] is True


def test_f12_every_gate_but_the_flag_only_one_has_a_fixture_and_the_ids_are_unique():
    codes = [f.code for f in hf.FIXTURES]
    assert len(codes) == len(set(codes)) == 11
    assert set(codes) == set(HALT_CODES) - set(FLAG_ONLY_CODES)
    assert set(hf.NO_FIXTURE) == {"H10"} and "W10" in hf.NO_FIXTURE["H10"]
    assert [f.command for f in hf.FIXTURES if f.command != "run"] == ["compare"]
    assert {f.code for f in hf.FIXTURES if f.command == "compare"} == {"H12"}
    assert hf.OTHER_EXIT_3_CODES == (*SCHEMA_CODES, *MAPPING_CODES)
    assert set(hf.OTHER_EXIT_3_CODES) == {"S01", "S02", "S03", "S04", "S05", "E01"}


def test_f12_the_packaged_criteria_equal_the_test_factorys():
    assert hf.fixture_criteria() == make_criteria()
    assert hf.fixture_criteria(classes=None) == make_criteria(classes=None)


def test_f12_check_reports_a_fixture_that_exits_3_on_another_code(tmp_path: Path):
    """The pre-E13 shape: H01's input with no confirmed mapping exits 3 on H07."""

    def h01_without_mapping(d: Path) -> list[str]:
        crit = hf.fixture_criteria(
            score={"type": "probability", "orientation": "lower_is_positive"}
        )
        return hf._run_args(d, hf._cohort(), crit, mapping=False)

    planted = hf.HaltFixture("H01", "run", "planted: no mapping", h01_without_mapping)
    r = hf.check(planted, tmp_path / "w", hf.in_process)
    assert r["exit_code"] == EXIT_HALT
    assert r["printed_code"] == "H07"
    assert r["ok"] is False


def test_f12_check_reports_a_halt_that_leaves_a_file_or_an_out_directory(tmp_path: Path):
    fixture = hf.FIXTURES[0]

    def writes_a_document(argv: list[str], home: Path) -> tuple[int, str]:
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir()
        (out / "run.json").write_text("{}", encoding="utf-8")
        return EXIT_HALT, f"HALT {fixture.code}: planted\n  {hf.NO_DOCUMENT_LINE}\n"

    r = hf.check(fixture, tmp_path / "a", writes_a_document)
    assert r["printed_code"] == fixture.code and r["exit_code"] == EXIT_HALT
    assert r["out_exists"] is True and r["files_changed"] == ["pack/run.json"]
    assert r["ok"] is False

    def touches_the_ledger(argv: list[str], home: Path) -> tuple[int, str]:
        (home / "ledger.json").write_text("{}", encoding="utf-8")
        return EXIT_HALT, f"HALT {fixture.code}: planted\n  {hf.NO_DOCUMENT_LINE}\n"

    r = hf.check(fixture, tmp_path / "b", touches_the_ledger)
    assert r["files_changed"] == ["home/ledger.json"] and r["ok"] is False

    def silent(argv: list[str], home: Path) -> tuple[int, str]:
        return EXIT_HALT, ""

    r = hf.check(fixture, tmp_path / "c", silent)
    assert r["printed_code"] is None and r["ok"] is False


def test_f12_the_in_process_runner_restores_the_environment(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PROOFPACK_HOME", str(tmp_path / "mine"))
    monkeypatch.setenv("PROOFPACK_LICENCE", "kept")
    r = hf.check(hf.FIXTURES[1], tmp_path / "w", hf.in_process)
    assert r["ok"] is True
    assert os.environ["PROOFPACK_HOME"] == str(tmp_path / "mine")
    assert os.environ["PROOFPACK_LICENCE"] == "kept"


# --------------------------------------------------------------- the fixtures report row


def _row_f12(report: dict) -> dict:
    return next(r for r in report["rows"] if r["id"] == "F12")


def test_f12_the_report_row_carries_the_count_of_this_commands_own_run():
    from proofpack import fixtures as fx

    report = fx.run_fixtures(doctor=False)
    fx.validate_report(report)
    row = _row_f12(report)
    measured = row["evidence"]["measured_by_this_command"]
    assert row["status"] == "suite_only" and row["matched"] is False
    assert (measured["total"], measured["ok"], measured["failures"]) == (11, 11, [])
    assert [i["code"] for i in measured["items"]] == [f.code for f in hf.FIXTURES]
    assert all(
        i["exit_code"] == EXIT_HALT and i["printed_code"] == i["code"] for i in measured["items"]
    )
    assert "11 of 11 exited 3" in row["reason"]
    assert report["exit_code"] == 0


def test_f12_the_reason_and_counts_follow_the_results_not_a_typed_number():
    from proofpack import fixtures as fx

    three = [
        {
            "id": f"F12-H0{i}",
            "code": f"H0{i}",
            "command": "run",
            "exit_code": 3,
            "printed_code": f"H0{i}",
            "out_exists": False,
            "files_changed": [],
            "ok": True,
        }
        for i in (1, 2, 3)
    ]
    got = fx.f12_behaviour(three)
    assert got["status"] == "suite_only"
    assert got["evidence"]["measured_by_this_command"]["total"] == 3
    assert "ran 3 HALT fixtures (H01, H02, H03)" in got["reason"]
    assert "3 of 3 exited 3" in got["reason"]
    assert fx.f12_behaviour([])["status"] == "not_matched"


def test_f12_a_fixture_that_does_not_halt_makes_the_row_not_matched_and_the_command_exit_6(
    monkeypatch,
):
    from proofpack import fixtures as fx
    from proofpack.errors import EXIT_FIXTURES_NOT_MATCHED

    real = hf.run_all

    def one_wrong(*a, **k):
        out = real(*a, **k)
        out[0] = {**out[0], "printed_code": "H07", "ok": False}
        return out

    monkeypatch.setattr(hf, "run_all", one_wrong)
    report = fx.run_fixtures(doctor=False)
    fx.validate_report(report)
    row = _row_f12(report)
    assert row["status"] == "not_matched"
    assert "H01 exit 3, printed H07" in row["reason"]
    assert row["evidence"]["measured_by_this_command"]["failures"] == ["F12-H01"]
    assert report["exit_code"] == EXIT_FIXTURES_NOT_MATCHED
