"""Build day 7 (E7): the manifest and canonical JSON; F17 determinism.

F17 (D1 section 3.2): the same inputs run twice in one process give identical hashes.
The two runs here go through ``proofpack.cli.main`` end to end (mapping, ingest,
statistics, criteria, ledger, manifest, the file write); the bytes of the two ``run.json``
files are compared after the four manifest keys ``run_id``, ``started``, ``duration_s``
and ``ledger_count`` and the body's ``ledger.acceptance_runs`` are blanked, and the set of
manifest keys that differ is asserted to hold ``run_id`` and ``ledger_count`` and nothing
outside those four (lens 2 of 21 September, FA-N2: this docstring earlier named three keys
while the body blanked five).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import sysconfig
from pathlib import Path

import pytest

from conftest import (
    confirmed_mapping,
    ephemeral_registry,
    make_cohort,
    make_criteria,
    write_csv,
    write_yaml,
)
from proofpack import __version__
from proofpack import manifest as manifest_mod
from proofpack.cli import main
from proofpack.errors import EXIT_OK

pytestmark = pytest.mark.day7


def test_canonical_json_is_sorted_fixed_separators_utf8_and_refuses_non_finite_floats():
    data = manifest_mod.canonical_json({"b": 1, "a": {"y": [1.5, None], "x": "é"}})
    assert (
        data
        == b'{\n "a": {\n  "x": "\xc3\xa9",\n  "y": [\n   1.5,\n   null\n  ]\n },\n "b": 1\n}\n'
    )
    assert not data.startswith(b"\xef\xbb\xbf")
    for bad in (float("inf"), float("-inf"), float("nan")):
        with pytest.raises(ValueError):
            manifest_mod.canonical_json({"x": bad})
        with pytest.raises(ValueError):
            manifest_mod.canonical_json({"x": {"deep": [1, {"z": bad}]}})
    assert b"Infinity" not in data and b"NaN" not in data


def test_platform_tag_and_reference_platform():
    tag = manifest_mod.platform_tag()
    assert tag == f"{sysconfig.get_platform()}-cp{sys.version_info.major}{sys.version_info.minor}"
    assert re.fullmatch(r"[a-z0-9_.-]+-cp3\d+", tag)
    assert manifest_mod.REFERENCE_PLATFORM == "linux-x86_64-cp312"


def test_build_manifest_hashes_the_files_bytes(tmp_path: Path):
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    a.write_bytes(b"input\r\n")
    b.write_bytes(b"criteria: 1\n")
    c.write_bytes(b"{}")
    m = manifest_mod.build_manifest(
        input_path=a,
        criteria_path=b,
        mapping_path=c,
        seed=7,
        n_resamples=9,
        started="2026-09-21T00:00:00Z",
        duration_s=1.5,
        licence_id="lic_x",
        tier="annual",
        ledger_count=2,
        watermark=None,
    )
    assert m["input_sha256"] == hashlib.sha256(b"input\r\n").hexdigest()
    assert m["criteria_sha256"] == hashlib.sha256(b"criteria: 1\n").hexdigest()
    assert m["mapping_sha256"] == hashlib.sha256(b"{}").hexdigest()
    assert (m["seed"], m["B"], m["engine_version"]) == (7, 9, __version__)
    assert m["reference_platform"] is (m["platform"] == manifest_mod.REFERENCE_PLATFORM)
    assert m["python"] == ".".join(str(x) for x in sys.version_info[:3])
    assert re.fullmatch(r"[0-9a-f-]{36}", m["run_id"])
    assert m["watermark"] is None and m["ledger_count"] == 2
    assert set(m) == {
        "run_id",
        "engine_version",
        "platform",
        "python",
        "numpy",
        "scipy",
        "input_sha256",
        "criteria_sha256",
        "mapping_sha256",
        "seed",
        "B",
        "started",
        "duration_s",
        "reference_platform",
        "licence_id",
        "tier",
        "ledger_count",
        "watermark",
    }


def _run(tmp_path: Path, out: str, csv_path: Path, yml: Path) -> bytes:
    rc = main(
        [
            "--quiet",
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--out",
            str(tmp_path / out),
        ],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_OK
    return (tmp_path / out / "run.json").read_bytes()


def _blank_volatile(raw: bytes) -> tuple[bytes, dict]:
    doc = json.loads(raw)
    manifest = doc["manifest"]
    for key in manifest_mod.VOLATILE_KEYS | manifest_mod.HISTORY_KEYS:
        manifest[key] = None
    doc["ledger"]["acceptance_runs"] = None  # the ledger counts every run with criteria
    return manifest_mod.canonical_json(doc), doc


def test_f17_two_runs_in_one_process_differ_only_in_run_id_started_duration_s_and_the_ledger_count(
    tmp_path: Path, monkeypatch
):
    """F17 as measured (lens 1 of 21 September, RG-N2: the earlier name said 'the three
    volatile keys' while the body blanked four manifest keys and ledger.acceptance_runs).
    The manifest keys that may differ are run_id, started, duration_s and ledger_count;
    ledger.acceptance_runs in the body reads 1 then 2; the three SHA-256 fields are equal
    and the bytes are identical once those keys are blanked."""
    monkeypatch.setenv("PROOFPACK_HOME", str(tmp_path / "home"))
    from conftest import write_licence

    (tmp_path / "home").mkdir()
    write_licence(tmp_path / "home" / "proofpack.lic")
    cols = make_cohort(n=300)
    csv_path = write_csv(tmp_path / "t.csv", cols)
    # no ledger block: no limit, no W14; the count still moves (HISTORY_KEYS)
    yml = write_yaml(tmp_path / "c.yaml", make_criteria(ledger=None))
    mapping = confirmed_mapping(csv_path)
    first = _run(tmp_path, "p1", csv_path, yml)
    second = _run(tmp_path, "p2", csv_path, yml)
    assert first != second  # run_id differs (asserted below); started may or may not
    a, doc_a = _blank_volatile(first)
    b, doc_b = _blank_volatile(second)
    assert a == b
    ma, mb = json.loads(first)["manifest"], json.loads(second)["manifest"]
    differ = {k for k in ma if ma[k] != mb[k]}
    assert differ <= manifest_mod.VOLATILE_KEYS | manifest_mod.HISTORY_KEYS
    assert manifest_mod.VOLATILE_KEYS | manifest_mod.HISTORY_KEYS == {
        "run_id",
        "started",
        "duration_s",
        "ledger_count",
    }
    assert "run_id" in differ and "ledger_count" in differ
    assert (ma["ledger_count"], mb["ledger_count"]) == (1, 2)
    da, db = json.loads(first), json.loads(second)
    assert (da["ledger"]["acceptance_runs"], db["ledger"]["acceptance_runs"]) == (1, 2)
    assert {k for k in da if da[k] != db[k]} == {"manifest", "ledger"}
    assert (
        ma["input_sha256"]
        == mb["input_sha256"]
        == hashlib.sha256(csv_path.read_bytes()).hexdigest()
    )
    assert ma["criteria_sha256"] == hashlib.sha256(yml.read_bytes()).hexdigest()
    assert ma["mapping_sha256"] == hashlib.sha256(mapping.read_bytes()).hexdigest()
    assert ma["reference_platform"] is False  # measured on the build machine, not the image
    assert doc_a["ledger"] == doc_b["ledger"]  # after the count is blanked: same key, no limit
    assert doc_a["ledger"]["warn_limit"] is None


def test_f17_with_a_ledger_block_the_count_is_the_one_field_that_moves(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PROOFPACK_HOME", str(tmp_path / "home"))
    from conftest import write_licence

    (tmp_path / "home").mkdir()
    write_licence(tmp_path / "home" / "proofpack.lic")
    cols = make_cohort(n=200)
    csv_path = write_csv(tmp_path / "t.csv", cols)
    yml = write_yaml(tmp_path / "c.yaml", make_criteria())  # ledger limit 3
    confirmed_mapping(csv_path)
    first = json.loads(_run(tmp_path, "p1", csv_path, yml))
    second = json.loads(_run(tmp_path, "p2", csv_path, yml))
    assert (first["manifest"]["ledger_count"], second["manifest"]["ledger_count"]) == (1, 2)
    assert first["ledger"]["acceptance_runs"] == 1 and second["ledger"]["acceptance_runs"] == 2
    assert first["ledger"]["test_set_sha256"] == second["ledger"]["test_set_sha256"]
    for key in ("overall", "subgroups", "calibration", "criteria_results", "flow", "table1"):
        assert first[key] == second[key], key
