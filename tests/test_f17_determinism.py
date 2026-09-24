"""A-P3 item 2 (build day 9, lane A): F17 through ``scripts/f17_determinism.py``.

The script writes the 5,000-row synthetic cohort (seed 20240101) and runs ``python -m
proofpack.cli run ... --offline --format json`` twice in two subprocesses, each with its
own empty ``PROOFPACK_HOME``, then compares four SHA-256 values per run: ``run.json`` with
the values of ``run_id``, ``started`` and ``duration_s`` masked; the manifest block with the
same three masked; ``pseudonyms.json`` with its ``run_id`` masked (A-P2 note item 3: it is
in the hashed set, because it is written beside ``run.json`` on every run and its body -
the level-to-pseudonym map - must come out the same; its ``run_id`` is the run's own id);
``ingest_report.json`` as written.

Measured on win-amd64-cp314 (Windows 11, Python 3.14.6, numpy 2.5.1), 24 September 2026:
the four pairs equal, both runs exit 4 (no licence), ``run.json`` 593,303 bytes each, the
unmasked egress ``manifest_sha256`` different (it hashes ``run_id``). That is a
same-platform repeat on a machine that is not the reference platform; D1 section 9 and T12
claim hash identity on ``python:3.12-slim`` linux/amd64 only, where the CI Docker job is
written to run the same script (it has not run there).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

import proofpack
from proofpack.manifest import VOLATILE_KEYS, platform_tag

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent


def _script():
    spec = importlib.util.spec_from_file_location(
        "f17_determinism", REPO / "scripts" / "f17_determinism.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["f17_determinism"] = module
    spec.loader.exec_module(module)
    return module


F17 = _script()


@pytest.fixture(scope="module")
def result(tmp_path_factory) -> dict:
    return F17.run_f17(tmp_path_factory.mktemp("f17"), n=5000)


def test_the_engine_under_test_is_this_tree():
    # the subprocess runs inherit this environment (PYTHONPATH forced to <tree>/src)
    assert Path(proofpack.__file__).resolve().is_relative_to(REPO / "src")


def test_f17_two_runs_are_identical_under_the_three_key_mask(result):
    assert result["identical"] is True, result["checks"]
    assert set(result["checks"]) == {
        "run_json_masked",
        "manifest_masked",
        "pseudonyms_json_masked",
        "ingest_report_json",
    }
    assert all(c["equal"] for c in result["checks"].values())
    assert result["rows"] == 5000 and result["exit_codes"] == [4, 4]
    assert result["platform"] == platform_tag()
    # the unmasked bytes differ (run_id at least) and so does the egress manifest hash
    assert result["raw_bytes_equal"] is False
    a, b = result["egress_manifest_sha256_unmasked"]
    assert a != b
    assert result["ledger_count"] == [0, 0]


def test_the_mask_is_exactly_the_manifest_volatile_keys():
    assert tuple(F17.MASKED_KEYS) == ("run_id", "started", "duration_s")
    assert set(F17.MASKED_KEYS) == set(VOLATILE_KEYS)


def test_a_changed_score_is_detected_under_the_same_mask(tmp_path: Path, result):
    """One score in one row changed between the runs: the masked run.json hashes differ."""
    table, criteria, mapping = F17.write_inputs(tmp_path / "in1", 400)
    F17.run_once(table, criteria, mapping, tmp_path / "run1", tmp_path / "home1")
    lines = table.read_text(encoding="utf-8").splitlines()
    cells = lines[1].split(",")
    header = lines[0].split(",")
    i = header.index("score")
    cells[i] = f"{min(0.999999, float(cells[i]) + 0.1):.6f}"
    lines[1] = ",".join(cells)
    table2 = tmp_path / "in2" / "synthetic.csv"
    table2.parent.mkdir()
    table2.write_text("\n".join(lines) + "\n", encoding="utf-8")
    F17.run_once(table2, criteria, mapping, tmp_path / "run2", tmp_path / "home2")
    cmp = F17.compare(tmp_path / "run1", tmp_path / "run2")
    assert cmp["identical"] is False
    assert cmp["checks"]["run_json_masked"]["equal"] is False
    assert cmp["checks"]["manifest_masked"]["equal"] is False  # input_sha256 moved


def test_mask_refuses_a_key_that_is_absent_or_repeated():
    with pytest.raises(ValueError, match="occurs 0 times"):
        F17.mask(b'{"x": 1}')
    two = b'"run_id": "' + b"a" * 36 + b'"\n"run_id": "' + b"b" * 36 + b'"'
    with pytest.raises(ValueError, match="occurs 2 times"):
        F17.mask(two, ("run_id",))


def test_the_result_names_the_platform_and_the_hashed_set(result):
    assert json.loads(json.dumps(result)) == result
    assert result["reference_platform"] is (platform_tag() == "linux-x86_64-cp312")
    assert result["hashed_set"] == sorted(result["checks"])
    assert result["masked_keys"] == ["run_id", "started", "duration_s"]
