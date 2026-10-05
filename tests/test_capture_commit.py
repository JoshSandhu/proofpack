"""The capture commit (5 October 2026): GitHub run 37332685741's R capture in fixtures/r/.

What each test feeds and asserts:

* ``git ls-files fixtures/r`` lists exactly ``README.md``, ``capture.R`` and the three JSON
  files the run uploaded, and no tracked path anywhere matches ``*asah*vectors*`` or
  ``fixtures/r/*.csv`` (DEC-77: the aSAH rows are never committed);
* the three committed JSON files name the same run (37332685741) and the same engine
  commit, and ``f13_engine_comparison.json`` records the sha256 of the committed
  ``proc_asah.json`` (CRLF read as LF);
* ``fixtures/f4_expected.json`` ``r_rms_val_prob`` equals, field by field, the provenance
  and figures of the committed ``rms_val_prob_f4.json`` (they were copied there by script,
  never typed), and its ``file_sha256`` is that file's sha256 (CRLF read as LF).

The JSON files are read as git tracks them (``git show :<path>``, the index), not from the
working tree: the r-captures job runs ``pytest -m day12`` after copying a fresh capture (a
new run id) over the committed files without staging it, and these tests are about the
committed capture.
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
from pathlib import Path

import pytest

from proofpack import fixtures as fx

pytestmark = [pytest.mark.day12, pytest.mark.fixture]
REPO = Path(__file__).resolve().parent.parent
RUN_ID = "37332685741"
ENGINE_SHA = "9d285d986fedd6f6e43fb2c6bfd1497307adbfa1"
THE_THREE = ("proc_asah.json", "rms_val_prob_f4.json", "f13_engine_comparison.json")


def _tracked(*paths: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--", *paths],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.splitlines()


def _tracked_bytes(name: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(REPO), "show", f":fixtures/r/{name}"],
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _json(name: str) -> dict:
    return json.loads(_tracked_bytes(name).decode("utf-8"))


def test_dec77_fixtures_r_tracks_the_three_json_files_and_no_vectors():
    assert sorted(_tracked("fixtures/r")) == sorted(
        ["fixtures/r/README.md", "fixtures/r/capture.R", *(f"fixtures/r/{n}" for n in THE_THREE)]
    )
    every = _tracked()
    assert len(every) > 100
    assert [p for p in every if fnmatch.fnmatch(p.lower(), "*asah*vectors*")] == []
    assert [p for p in every if fnmatch.fnmatch(p.lower(), "fixtures/r/*.csv")] == []


def test_the_three_committed_files_name_run_37332685741_and_one_engine_commit():
    proc, valprob, cmp_doc = (_json(n) for n in THE_THREE)
    for doc in (proc, valprob):
        assert doc["meta"]["github"]["run_id"] == RUN_ID
        assert doc["meta"]["github"]["sha"] == ENGINE_SHA
    assert cmp_doc["github_run_id"] == RUN_ID and cmp_doc["engine_sha"] == ENGINE_SHA
    assert cmp_doc["status"] == "matched"
    assert cmp_doc["proc_asah_sha256"] == fx.lf_sha256(_tracked_bytes(THE_THREE[0]))


def test_f4_expected_r_rms_val_prob_is_copied_from_the_committed_capture():
    raw = _tracked_bytes("rms_val_prob_f4.json")
    cap = json.loads(raw.decode("utf-8"))
    meta, gh = cap["meta"], cap["meta"]["github"]
    exp = json.loads((REPO / "fixtures" / "f4_expected.json").read_text(encoding="utf-8"))
    block = exp["r_rms_val_prob"]
    assert block["status"] == "captured"
    assert block["file"] == "fixtures/r/rms_val_prob_f4.json"
    assert block["file_sha256"] == fx.lf_sha256(raw)
    assert block["github_run_id"] == gh["run_id"] == RUN_ID
    assert block["github_run_attempt"] == gh["run_attempt"]
    assert block["github_workflow"] == gh["workflow"]
    assert block["engine_commit_of_the_run"] == gh["sha"]
    assert block["run_date_utc"] == meta["run_date_utc"]
    assert block["r_version_string"] == meta["r_version_string"]
    assert block["r_platform"] == meta["r_platform"]
    assert block["packages"] == meta["packages"]
    assert block["repos"] == meta["repos"]
    assert block["input_sha256"] == cap["input"]["sha256"]
    copied = block["values_from_the_capture"]
    assert len(copied) >= 4
    for name, value in copied.items():
        assert type(value) is float and value == cap["values"][name], name
