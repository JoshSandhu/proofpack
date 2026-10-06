"""Build day 13 (E13) item 5: rows F12, F16, F17 and F19 of ``fixtures_report.json``.

Each row carries a status this command measured itself, the artefacts it cites and, for a
committed file, the engine commit that produced it; a CI artefact this command cannot see
says so (``seen_by_this_command: false``, no run id, no engine commit). No row says
"verified" where only CI could show it. The report has no ``--format``: it is always
JSON (``proofpack fixtures --offline`` writes ``fixtures_report.json``).
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from proofpack import f17, f19, parity
from proofpack import fixtures as fx
from proofpack.errors import EXIT_FIXTURES_NOT_MATCHED
from proofpack.manifest import canonical_json

pytestmark = [pytest.mark.day13, pytest.mark.fixture]
REPO = Path(__file__).resolve().parent.parent
ROWS = ("F12", "F16", "F17", "F19")


@pytest.fixture(scope="module")
def report() -> dict:
    rep = fx.run_fixtures(doctor=False)
    fx.validate_report(rep)
    return rep


def _row(report: dict, rid: str) -> dict:
    return next(r for r in report["rows"] if r["id"] == rid)


def test_the_four_rows_are_measured_by_this_command_and_behave(report):
    for rid in ROWS:
        r = _row(report, rid)
        assert r["status"] == "suite_only", (rid, r["reason"])
        m = r["evidence"]["measured_by_this_command"]
        assert m["total"] >= 2 and m["ok"] == m["total"] and m["failures"] == [], rid
        assert r["matched"] is False  # a behaviour is never "matched"
    assert report["summary"]["not_built"] == 4 and report["summary"]["suite_only"] == 7
    assert _row(report, "F12")["evidence"]["measured_by_this_command"]["total"] == 11
    assert _row(report, "F19")["evidence"]["measured_by_this_command"]["total"] == 2
    assert _row(report, "F17")["evidence"]["measured_by_this_command"]["total"] == 6


def test_no_row_says_verified_and_ci_artefacts_are_marked_unseen(report):
    for rid in ROWS:
        text = json.dumps(_row(report, rid))
        assert re.findall(r"(?<![Uu]n)verified", text) == [], rid
        for a in _row(report, rid)["evidence"]["artefacts"]:
            if a["kind"] == "ci_job":
                assert a["seen_by_this_command"] is False and a["engine_commit"] is None
                assert "run id is not known" in a["note"]
    assert {a["name"] for a in _row(report, "F17")["evidence"]["artefacts"]} >= {
        f"{f17.CI_JOB} (artefact {f17.CI_ARTEFACT})",
        f17.CI_TEST_FILE,
    }
    assert {a["name"] for a in _row(report, "F19")["evidence"]["artefacts"]} >= {
        f"{f19.CI_JOB} (artefact {f19.CI_ARTEFACT})",
        f19.CI_TEST_FILE,
    }
    assert "not the reference image" in _row(report, "F17")["reason"]


def test_the_f19_row_names_the_namespace_fallback_and_the_three_socket_attributes(report):
    """E13 repair 1, lens FA-B3 / RG-B2 and FA-B4 / RG-B1: at 941c8e4 the F19 reason said
    "The --offline run inside unshare -rn" (the three runs of the job at 941c8e4 logged
    ``namespace command: sudo unshare -n``) and "sockets refused" (a socket made through
    ``_socket.socket`` was not counted)."""
    row = _row(report, "F19")
    text = json.dumps(row)
    assert "inside unshare -rn" not in text and "sockets refused" not in text
    assert (
        "uses unshare -rn where the runner allows it and sudo unshare -n otherwise, and "
        "records which in the artefact's namespace.txt" in row["reason"]
    )
    assert (
        "with socket.socket, socket.getaddrinfo and socket.create_connection replaced by "
        "counting refusals" in row["reason"]
    )


def test_the_f12_row_names_where_no_file_was_written(report):
    """E13 repair 1, lens RG-B3: at 941c8e4 the F12 row said "no file written";
    ``halt_fixtures.check`` inspects the fixture's directory and ``--out`` only."""
    row = _row(report, "F12")
    assert "no file written" not in row["what_is_compared"]
    assert row["what_is_compared"].endswith(
        "no file added, removed or changed under the fixture's directory (its inputs and "
        "its PROOFPACK_HOME), and no --out"
    )
    assert "changed no file under the fixture's directory and wrote no --out" in row["reason"]


#: (file, a sentence an E13 lens 1 note found false at 941c8e4); each must be absent.
FALSE_AT_941C8E4 = (
    ("src/proofpack/f19.py", "would be counted, not sent"),
    ("src/proofpack/f19.py", "(``--offline`` inside ``unshare -rn``)"),
    ("src/proofpack/fixtures.py", "sockets refused"),
    ("src/proofpack/fixtures.py", '"unshare -rn "'),
    ("src/proofpack/fixtures.py", "line, no file written"),
    ("src/proofpack/fixtures.py", "every register value F1-F11"),
    ("src/proofpack/parity.py", "for every value the fixture"),
    ("src/proofpack/f17.py", "and fails on any other difference"),
    ("src/proofpack/render/t12.py", "compared by the test suite only"),
    ("src/proofpack/templates/T12.html", "compared by the test suite only"),
    ("tests/test_f19_egress_bytes.py", "runs this file inside ``unshare -rn``"),
    ("tests/test_f19_egress_bytes.py", "bypasses_the_recorder_is_counted_and_refused"),
    ("tests/test_f16_parity_native.py", "test_every_register_row_with_an_engine_is_in_the_file"),
)


@pytest.mark.parametrize("path,sentence", FALSE_AT_941C8E4)
def test_the_sentences_the_e13_lenses_found_false_are_gone(path, sentence):
    text = (REPO / path).read_text(encoding="utf-8")
    assert sentence not in text, (path, sentence)


def test_f16_names_the_committed_file_and_the_engine_commit_that_wrote_it(report):
    committed = json.loads((REPO / parity.COMMITTED_FILE).read_text(encoding="utf-8"))
    r = _row(report, "F16")
    files = [a for a in r["evidence"]["artefacts"] if a["kind"] == "committed_file"]
    assert len(files) == 1 and files[0]["name"] == parity.COMMITTED_FILE
    assert files[0]["engine_commit"] == committed["generated"]["engine_commit"]
    assert "engine half only" in r["reason"] and "Pyodide half" in r["reason"]
    assert "not run by this command or this repository" in r["reason"]
    assert r["evidence"]["measured_by_this_command"]["total"] == sum(
        len(v) for v in committed["fixtures"].values()
    )


def test_the_report_carries_the_engine_commit_of_this_checkout(report):
    assert re.fullmatch(r"[0-9a-f]{40}", report["git_sha"])


def test_f16_drift_is_not_matched_and_exits_6():
    committed = json.loads((REPO / parity.COMMITTED_FILE).read_text(encoding="utf-8"))
    fresh = copy.deepcopy(committed)
    block = fresh["fixtures"]["F1"]
    key = next(k for k, e in block.items() if e.get("tol") == "closed")
    block[key]["value"] += 1e-6
    out = fx.f16_behaviour(committed, fresh)
    assert out["status"] == "not_matched" and key in out["reason"]
    assert fx.exit_code_for([{"status": out["status"]}]) == EXIT_FIXTURES_NOT_MATCHED


def test_f16_outside_a_source_checkout_is_no_oracle_recorded(monkeypatch):
    monkeypatch.setattr(fx, "source_checkout_root", lambda: None)
    out = fx.f16_behaviour()
    assert out["status"] == "no_oracle_recorded"
    assert "read only from a proofpack source checkout" in out["reason"]


def test_f16_an_unreadable_committed_file_is_not_matched(monkeypatch, tmp_path):
    (tmp_path / "fixtures").mkdir()
    (tmp_path / parity.COMMITTED_FILE).write_text('{"fixtures": ', encoding="utf-8")
    monkeypatch.setattr(fx, "source_checkout_root", lambda: tmp_path)
    out = fx.f16_behaviour()
    assert out["status"] == "not_matched" and "oracle_file_unreadable" in out["reason"]


def test_f17_one_unequal_check_is_not_matched():
    result = f17.run_repeat()
    assert fx.f17_behaviour(result)["status"] == "suite_only"
    planted = copy.deepcopy(result)
    planted["checks"]["run_json_masked"]["equal"] = False
    out = fx.f17_behaviour(planted)
    assert out["status"] == "not_matched" and "run_json_masked" in out["reason"]
    assert out["evidence"]["measured_by_this_command"]["failures"] == ["run_json_masked"]


def test_f19_one_failing_cohort_is_not_matched():
    results = f19.run_all()
    assert fx.f19_behaviour(results)["status"] == "suite_only"
    planted = copy.deepcopy(results)
    planted[1]["small_cells_unsuppressed"] = 3
    out = fx.f19_behaviour(planted)
    assert out["status"] == "not_matched"
    assert "small_cell_real_site_names: small_cells_unsuppressed" in out["reason"]
    assert fx.f19_behaviour([])["status"] == "not_matched"


def test_the_cli_writes_the_four_rows_into_fixtures_report_json(tmp_path, capsys):
    from proofpack.cli import main

    rc = main(["fixtures", "--offline", "--out", str(tmp_path)])
    assert rc == 0
    doc = json.loads((tmp_path / fx.REPORT_FILE).read_text(encoding="utf-8"))
    assert (tmp_path / fx.REPORT_FILE).read_bytes() == canonical_json(doc)
    for rid in ROWS:
        assert _row(doc, rid)["status"] == "suite_only"
        assert _row(doc, rid)["evidence"]["artefacts"]
