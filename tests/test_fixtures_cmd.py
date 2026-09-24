"""A-P3 item 1 (build day 9, lane A): ``proofpack fixtures`` -> ``fixtures_report.json``.

What each test feeds and asserts:

* the command through ``main`` writes a report that validates against
  ``schema/fixtures_report_schema.json``, with 43 rows: 30 matched, 0 not matched, 2 no
  oracle recorded, 6 not built, 5 compared by the test suite only, exit 0 (measured
  24 September 2026 on win-amd64-cp314, numpy 2.5.1, scipy 1.18.1);
* the committed ``fixtures/oracles_v1.json`` oracle ``captured.F1-wilson.wilson_lo`` moved
  by +2e-9 makes row ``F1-wilson`` (closed-form, tolerance 1e-9) not matched and the
  command exit 6; moved by +5e-10 it stays matched;
* a row built with no oracle (status ``no_oracle_recorded``, ``not_built``, ``suite_only``)
  has ``matched`` false and is not counted in ``summary.matched``, and a report claiming
  such a row matched fails the schema;
* ``clopper_pearson_bounds`` returning ``None`` for an interior count (scipy absent) makes
  four rows not matched with reason ``optional_dependency_missing: scipy``: F1-clopper-pearson,
  F1-register, F1b-clopper-pearson and F1b-register (F1 and F1b are the two interior
  cases);
* ``--r-captures`` prints the typed ``r_captures_not_captured`` line.

The socket test for this command is in ``tests/test_offline.py``
(``test_fixtures_offline_opens_no_socket``).
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

from conftest import ephemeral_registry
from proofpack import fixtures as fx
from proofpack.cli import main
from proofpack.errors import EXIT_FIXTURES_NOT_MATCHED, EXIT_OK
from proofpack.resources import load_json_schema

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def report() -> dict:
    return fx.run_fixtures()


def _cli(tmp_path: Path, *extra: str) -> tuple[int, dict]:
    rc = main(
        ["fixtures", "--offline", "--out", str(tmp_path), *extra], registry=ephemeral_registry()
    )
    return rc, json.loads((tmp_path / fx.REPORT_FILE).read_text(encoding="utf-8"))


def _planted(key: str, value: str, delta: float) -> dict:
    oracles = copy.deepcopy(fx.load_oracles())
    oracles["oracles_v1.json"]["captured"][key]["values"][value] += delta
    return oracles


def test_the_report_validates_against_its_schema_and_carries_the_measured_counts(
    tmp_path: Path, capsys
):
    rc, doc = _cli(tmp_path)
    printed = capsys.readouterr().out
    assert rc == EXIT_OK, printed
    jsonschema.validate(doc, load_json_schema("fixtures_report_schema.json"))
    assert doc["summary"] == {
        "rows": 43,
        "matched": 30,
        "not_matched": 0,
        "no_oracle_recorded": 2,
        "not_built": 6,
        "suite_only": 5,
    }
    assert doc["exit_code"] == 0 and doc["offline"] is True
    assert doc["tolerance_policy"]["closed_form"] == 1e-9
    assert doc["tolerance_policy"]["iterative"] == 1e-6
    ids = [r["id"] for r in doc["rows"]]
    assert len(ids) == len(set(ids))
    fixtures = {r["fixture"] for r in doc["rows"]}
    for n in range(1, 22):
        assert f"F{n}" in fixtures, n
    assert {"F1b", "F1c", "F1d", "F13b"} <= fixtures
    assert "rows 43: matched 30, not matched 0" in printed
    # every matched row compared at least one value, each within its own tolerance
    for r in doc["rows"]:
        if r["status"] == "matched":
            assert r["n_values_compared"] >= 1 and all(v["within"] for v in r["values"])
            assert r["max_abs_deviation"] <= max(v["tolerance"] for v in r["values"])


def test_closed_form_rows_are_compared_at_1e_9_and_iterative_rows_at_1e_6(report):
    by_class: dict[str, set[float]] = {}
    for r in report["rows"]:
        if r["tolerance"]:
            by_class.setdefault(r["tolerance"]["class"], set()).update(
                v["tolerance"] for v in r["values"]
            )
    assert by_class["closed_form"] == {1e-9}
    assert by_class["iterative"] == {1e-6}
    assert by_class["register"] == {1e-4}
    # reported rounding: half a unit of the printed decimals (2 for the bootstrap
    # interval, 4 for the Newcombe table) plus 1e-12
    assert by_class["reported_rounding"] == {0.005 + 1e-12, 0.00005 + 1e-12}


def test_a_planted_oracle_off_by_2e_9_on_a_closed_form_cell_is_not_matched_and_exits_6(
    tmp_path: Path, monkeypatch, capsys
):
    planted = _planted("F1-wilson", "wilson_lo", 2e-9)
    rep = fx.run_fixtures(oracles=planted, doctor=False)
    row = next(r for r in rep["rows"] if r["id"] == "F1-wilson")
    assert row["status"] == "not_matched" and row["matched"] is False
    assert 1.9e-9 < row["max_abs_deviation"] < 2.1e-9
    assert row["reason"] == "outside tolerance: wilson_lo"
    assert rep["exit_code"] == EXIT_FIXTURES_NOT_MATCHED == 6
    assert rep["summary"]["not_matched"] == 1 and rep["summary"]["matched"] == 29
    fx.validate_report(rep)
    # the command: the same planted file through main exits 6 and names the row
    monkeypatch.setattr(fx, "load_oracles", lambda: planted)
    rc, doc = _cli(tmp_path)
    assert rc == 6 and doc["exit_code"] == 6
    assert "not matched: F1-wilson (outside tolerance: wilson_lo)" in capsys.readouterr().out


def test_a_planted_oracle_off_by_5e_10_on_the_same_cell_stays_matched():
    rep = fx.run_fixtures(oracles=_planted("F1-wilson", "wilson_lo", 5e-10), doctor=False)
    row = next(r for r in rep["rows"] if r["id"] == "F1-wilson")
    assert row["status"] == "matched" and 4.9e-10 < row["max_abs_deviation"] < 5.1e-10
    assert rep["exit_code"] == 0


def test_rows_without_an_oracle_are_never_counted_as_matched(report):
    for r in report["rows"]:
        if r["status"] in ("no_oracle_recorded", "not_built", "suite_only"):
            assert r["matched"] is False and r["oracle_source"] is None
            assert r["n_values_compared"] == 0 and r["max_abs_deviation"] is None
    assert report["summary"]["matched"] == sum(1 for r in report["rows"] if r["matched"])
    only = (
        fx.Row("F13", "F13", "planted", status="no_oracle_recorded", reason="none"),
        fx.Row("F5", "F5", "planted", status="not_built", reason="none"),
        fx.Row("F12", "F12", "planted", status="suite_only", reason="none"),
    )
    rep = fx.run_fixtures(rows=only, doctor=False)
    assert rep["summary"]["matched"] == 0 and rep["exit_code"] == 0
    assert [r["matched"] for r in rep["rows"]] == [False, False, False]
    # a report claiming such a row matched does not fit the schema
    bad = copy.deepcopy(rep)
    bad["rows"][0]["matched"] = True
    with pytest.raises(jsonschema.ValidationError):
        fx.validate_report(bad)


def test_the_statuses_of_the_register_rows_are_the_ones_named(report):
    status = {r["id"]: r["status"] for r in report["rows"]}
    assert [k for k, v in status.items() if v == "no_oracle_recorded"] == ["F13", "F13b"]
    assert sorted(k for k, v in status.items() if v == "not_built") == [
        "F15",
        "F16",
        "F21",
        "F3-auprc",
        "F5",
        "F7",
    ]
    assert sorted(k for k, v in status.items() if v == "suite_only") == [
        "F12",
        "F17",
        "F18",
        "F19",
        "F20",
    ]
    f13 = next(r for r in report["rows"] if r["id"] == "F13")
    assert f13["reason"].startswith("[unverified until captured]")
    f14 = next(r for r in report["rows"] if r["id"] == "F14-newcombe")
    assert f14["oracle_source"]["unverified"] is True
    assert f14["oracle_source"]["marking"] == "[unverified against the primary PDF]"


def test_an_absent_optional_dependency_is_not_matched_with_its_reason(monkeypatch):
    import proofpack.stats.proportions as props

    real = props.clopper_pearson_bounds

    def no_scipy(k, n, level=0.95):
        return real(k, n, level) if k in (0, n) else None

    monkeypatch.setattr(props, "clopper_pearson_bounds", no_scipy)
    rep = fx.run_fixtures(doctor=False)
    hit = {r["id"]: r["reason"] for r in rep["rows"] if r["status"] == "not_matched"}
    assert hit == {
        "F1-clopper-pearson": "optional_dependency_missing: scipy",
        "F1-register": "optional_dependency_missing: scipy",
        "F1b-clopper-pearson": "optional_dependency_missing: scipy",
        "F1b-register": "optional_dependency_missing: scipy",
    }
    assert rep["exit_code"] == 6


def test_an_engine_error_is_a_not_matched_row_and_not_a_traceback(monkeypatch):
    import proofpack.stats.discrimination as disc

    def boom(*a, **k):
        raise ZeroDivisionError("planted")

    monkeypatch.setattr(disc, "paired_delong", boom)
    rep = fx.run_fixtures(doctor=False)
    row = next(r for r in rep["rows"] if r["id"] == "F3-delong")
    assert row["status"] == "not_matched" and row["reason"] == "engine_error: ZeroDivisionError"
    assert rep["exit_code"] == 6


def test_r_captures_prints_the_typed_not_captured_line(tmp_path: Path, capsys):
    rc, _ = _cli(tmp_path, "--r-captures")
    out = capsys.readouterr().out
    assert rc == 0
    assert "r-captures: r_captures_not_captured - no R capture is committed" in out
    assert fx.r_captures_status()["status"] == fx.R_CAPTURES_NOT_CAPTURED


def test_the_committed_oracles_equal_a_fresh_capture():
    pytest.importorskip("statsmodels")
    pytest.importorskip("sklearn")
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "capture_fixture_oracles.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_git_sha_is_read_from_the_package_checkout_only(report):
    sha, source = fx.git_sha()
    if (REPO / ".git").exists():
        assert sha is not None and len(sha) == 40 and source.startswith(fx.GIT_SHA_SOURCE)
    assert report["git_sha"] == sha


def test_without_the_newcombe_file_f14_has_no_oracle_recorded_and_the_exit_is_0():
    """An installed wheel carries no fixtures/newcombe_table2.json (it is [unverified] and
    stays out of the package): F14 is then 'no oracle recorded', never matched."""
    oracles = {k: v for k, v in fx.load_oracles().items() if k != "newcombe_table2.json"}
    rep = fx.run_fixtures(oracles=oracles, doctor=False)
    f14 = next(r for r in rep["rows"] if r["id"] == "F14-newcombe")
    assert f14["status"] == "no_oracle_recorded" and f14["matched"] is False
    assert f14["reason"] == fx.NEWCOMBE_ABSENT and f14["oracle_source"] is None
    assert rep["summary"]["matched"] == 29 and rep["exit_code"] == 0
    fx.validate_report(rep)
