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
  never typed), and its ``file_sha256`` is that file's sha256 (CRLF read as LF);
* (capture repair B3) each of the three tracked files has the size and sha256 of the
  artefact as downloaded, which ``fixtures/r/README.md`` records for all three, and so does
  its working-tree copy with CRLF read as LF (outside the r-captures job).

The JSON files are read as git tracks them (``git show :<path>``, the index), not from the
working tree: the r-captures job runs ``pytest -m day12`` after copying a fresh capture (a
new run id) over the committed files without staging it, and these tests are about the
committed capture.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
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


#: The sha256 and size of each file of run 37332685741's artefact ``r-captures``, measured on
#: the two downloads (handoffs/2026-10-05_E_capture_commit.md, "The artefact bytes"; the
#: cold lens's fresh third download gave the same). fixtures/r/README.md records the same
#: table; a later capture changes both, and this test with them.
ARTEFACT = {
    "proc_asah.json": (4471, "01cf2f7bd8c57e7dfbc568ed6867b864701ceb8cf8827db68d7ee3d1e31d9a96"),
    "rms_val_prob_f4.json": (
        5401,
        "44a3866fdccd67eb76532705d9b03eda7c26f2a32ff5d7124a5a6c156c79be27",
    ),
    "f13_engine_comparison.json": (
        3517,
        "a36b7f54454c68e5e1478cbe4c19651a43f3f954fc1d7b25150f10a06921307f",
    ),
}
README_ROW = re.compile(r"^\| `([a-z0-9_]+\.json)` \| ([0-9,]+) \| `([0-9a-f]{64})` \|$", re.M)


def _in_the_r_captures_job() -> bool:
    """True inside the r-captures workflow, whose steps copy a fresh capture over the
    working tree before ``pytest -m day12`` (and whose day-12 step fails on any skip)."""
    return os.environ.get("GITHUB_WORKFLOW") == "r-captures"


def test_capture_repair_b3_the_three_files_are_the_artefact_bytes_the_readme_records():
    """Capture repair B3 (cold lens on 78bd085): the README's table records all three files,
    with the size and sha256 :data:`ARTEFACT` holds; the tracked blob (``git show :<path>``)
    of each has that size and that sha256, raw and with CRLF read as LF (the blob holds no
    CR); and the working-tree copy, CRLF read as LF, has that sha256 too (except inside the
    r-captures job, which overwrites the working tree with its fresh capture). Each of the
    lens's eight staged edits of f13_engine_comparison.json (two one-ulp engine values,
    ``within``, ``abs_deviation``, the top-level maximum, ``engine_version``,
    ``tolerance_class``, ``reason``) changes the blob's sha256 and fails here."""
    readme = _tracked_bytes("README.md").decode("utf-8").replace("\r\n", "\n")
    recorded = {
        name: (int(size.replace(",", "")), sha) for name, size, sha in README_ROW.findall(readme)
    }
    assert recorded == ARTEFACT
    for name, (size, sha) in ARTEFACT.items():
        blob = _tracked_bytes(name)
        assert b"\r" not in blob, name
        assert len(blob) == size, name
        assert hashlib.sha256(blob).hexdigest() == sha, name
        assert fx.lf_sha256(blob) == sha, name
        if not _in_the_r_captures_job():
            work = (REPO / "fixtures" / "r" / name).read_bytes()
            assert fx.lf_sha256(work) == sha, f"{name} (working tree)"


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
