"""F17 (build day 13, E13; D1 section 3.2, section 10 gate 3): two runs, one mask, and the
reference-image job.

What runs here is **not the reference image**: the CLI twice in two child processes on
whatever machine runs pytest (``scripts/f17_determinism.py``'s ``run_once``), compared by
``proofpack.f17.compare`` - the same function the CI job ``docker-smoke`` runs inside the
image on its two ``docker run --network none`` directories
(``scripts/f17_determinism.py --compare-dirs ... --require-reference-platform``). That job's
result is the artefact ``f17-reference-image``; this file does not see it. It also holds the
workflow to the shape the note describes, and plants differences the mask must not hide.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

import proofpack
from proofpack import f17
from proofpack.manifest import REFERENCE_PLATFORM, VOLATILE_KEYS, platform_tag

pytestmark = [pytest.mark.day13, pytest.mark.fixture]
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


SCRIPT = _script()


@pytest.fixture(scope="module")
def two_runs(tmp_path_factory) -> Path:
    work = tmp_path_factory.mktemp("f17cli")
    table, criteria, mapping = SCRIPT.write_inputs(work / "in", 400)
    for i in (1, 2):
        rc = SCRIPT.run_once(table, criteria, mapping, work / f"run{i}", work / f"home{i}")
        assert rc == 4  # no licence in the fresh home: run.json written, no document
    return work


def test_the_engine_under_test_is_this_tree():
    assert Path(proofpack.__file__).resolve().is_relative_to(REPO / "src")


def test_f17_cli_twice_same_platform_repeat_not_the_reference_image_is_identical_under_the_mask(
    two_runs: Path,
):
    where = "pytest, two child processes on this machine: not the reference image"
    result = f17.compare(two_runs / "run1", two_runs / "run2", where=where)
    assert result["identical"] is True, result["checks"]
    assert result["where"] == where
    assert result["masked_keys"] == ["run_id", "started", "duration_s"]
    assert set(f17.MASKED_KEYS) == set(VOLATILE_KEYS)
    assert result["hashed_set"] == [
        "file_names",
        "ingest_report_json",
        "manifest_masked",
        "other_files",
        "pseudonyms_json_masked",
        "run_json_masked",
    ]
    assert result["raw_bytes_equal"] is False  # run_id at least differs
    assert result["run_platforms"] == [platform_tag(), platform_tag()]
    # the platform recorded is this machine's; on a Linux CPython 3.12 runner the tag
    # equals the reference platform's, but the process is still not the reference image
    assert result["both_runs_on_reference_platform"] is (platform_tag() == REFERENCE_PLATFORM)


def test_the_script_and_the_fixtures_command_share_one_mask_and_one_comparison():
    assert SCRIPT.MASKED_KEYS is f17.MASKED_KEYS
    assert SCRIPT.compare.__doc__ and "proofpack.f17.compare" in SCRIPT.compare.__doc__
    assert SCRIPT.mask(b'"run_id": "' + b"a" * 36 + b'"', ("run_id",)) == b'"run_id": "<masked>"'


def _copy(two_runs: Path, tmp_path: Path) -> tuple[Path, Path]:
    a, b = tmp_path / "a", tmp_path / "b"
    shutil.copytree(two_runs / "run1", a)
    shutil.copytree(two_runs / "run2", b)
    return a, b


def test_compare_reads_the_bytes_of_every_other_file(two_runs: Path, tmp_path):
    """E13 repair 1, lens FA-B6: a ``T8.json`` of ``{"run_id": "a"}`` in one run and
    ``{"run_id": "b", "x": 1}`` in the other (same file names) left ``identical`` true at
    941c8e4. Now ``other_files`` differs; the same file with equal bytes in both is equal."""
    a, b = _copy(two_runs, tmp_path)
    (a / "T8.json").write_text('{"run_id": "a"}', encoding="utf-8")
    (b / "T8.json").write_text('{"run_id": "b", "x": 1}', encoding="utf-8")
    result = f17.compare(a, b)
    assert result["identical"] is False
    assert [k for k, v in result["checks"].items() if not v["equal"]] == ["other_files"]
    (b / "T8.json").write_text('{"run_id": "a"}', encoding="utf-8")
    assert f17.compare(a, b)["identical"] is True
    (b / "sub").mkdir()
    (a / "sub").mkdir()
    (a / "sub" / "run.json").write_bytes(b"1")
    (b / "sub" / "run.json").write_bytes(b"2")
    nested = f17.compare(a, b)
    assert [k for k, v in nested["checks"].items() if not v["equal"]] == ["other_files"]


def test_compare_dirs_exits_0_on_the_two_runs_and_writes_the_result(two_runs: Path, tmp_path):
    a, b = _copy(two_runs, tmp_path)
    rc = SCRIPT.main(["--out", str(tmp_path / "o"), "--compare-dirs", str(a), str(b)])
    assert rc == 0
    result = json.loads((tmp_path / "o" / "f17_result.json").read_text(encoding="utf-8"))
    assert result["identical"] is True and result["command"] == "compare-dirs"


def test_compare_dirs_fails_on_one_changed_byte_outside_the_three_keys(two_runs: Path, tmp_path):
    a, b = _copy(two_runs, tmp_path)
    data = (b / "run.json").read_bytes()
    i = data.index(b'"engine_version": "') + len(b'"engine_version": "')
    planted = data[:i] + (b"9" if data[i : i + 1] != b"9" else b"8") + data[i + 1 :]
    (b / "run.json").write_bytes(planted)
    rc = SCRIPT.main(["--out", str(tmp_path / "o"), "--compare-dirs", str(a), str(b)])
    assert rc == 1
    result = json.loads((tmp_path / "o" / "f17_result.json").read_text(encoding="utf-8"))
    assert result["checks"]["run_json_masked"]["equal"] is False
    assert result["checks"]["manifest_masked"]["equal"] is False


def test_compare_dirs_ignores_a_changed_run_id_started_and_duration_only(two_runs: Path, tmp_path):
    a, b = _copy(two_runs, tmp_path)
    doc = (b / "run.json").read_text(encoding="utf-8")
    for key, new in (
        ("started", '"started": "2099-01-01T00:00:00Z"'),
        ("duration_s", '"duration_s": 123.456'),
    ):
        start = doc.index(f'"{key}": ')
        end = doc.index("\n", start)
        tail = "," if doc[end - 1] == "," else ""
        doc = doc[:start] + new + tail + doc[end:]
    (b / "run.json").write_text(doc, encoding="utf-8", newline="")
    rc = SCRIPT.main(["--out", str(tmp_path / "o"), "--compare-dirs", str(a), str(b)])
    assert rc == 0


def test_compare_dirs_refuses_a_masked_key_that_occurs_twice(two_runs: Path, tmp_path, capsys):
    a, b = _copy(two_runs, tmp_path)
    data = (b / "run.json").read_bytes()
    i = data.index(b'"started": ')
    j = data.index(b"\n", i)
    line = data[i:j].rstrip(b",")
    (b / "run.json").write_bytes(data[: j + 1] + b"  " + line + b",\n" + data[j + 1 :])
    rc = SCRIPT.main(["--out", str(tmp_path / "o"), "--compare-dirs", str(a), str(b)])
    assert rc == 1
    assert "started occurs 2 times" in capsys.readouterr().out


def test_require_reference_platform_fails_when_a_manifest_records_another_platform(
    two_runs: Path, tmp_path
):
    """Both run.json files rewritten to say ``win-amd64-cp314`` and ``reference_platform:
    false``: identical, but --require-reference-platform exits 1 (on any machine)."""
    a, b = _copy(two_runs, tmp_path)
    for d in (a, b):
        doc = json.loads((d / "run.json").read_text(encoding="utf-8"))
        old = json.dumps(doc["manifest"]["platform"])
        text = (d / "run.json").read_text(encoding="utf-8")
        text = text.replace(f'"platform": {old}', '"platform": "win-amd64-cp314"')
        text = text.replace('"reference_platform": true', '"reference_platform": false')
        (d / "run.json").write_text(text, encoding="utf-8", newline="")
    base = ["--out", str(tmp_path / "o"), "--compare-dirs", str(a), str(b)]
    assert SCRIPT.main(base) == 0
    assert SCRIPT.main([*base, "--require-reference-platform"]) == 1
    result = json.loads((tmp_path / "o" / "f17_result.json").read_text(encoding="utf-8"))
    assert result["run_platforms"] == ["win-amd64-cp314", "win-amd64-cp314"]
    assert result["both_runs_on_reference_platform"] is False


def test_the_docker_smoke_job_runs_f17_twice_on_one_image_and_uploads_both_run_json():
    ci = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    job = ci["jobs"][f17.CI_JOB]
    assert job["runs-on"] == "ubuntu-24.04"
    steps = job["steps"]
    builds = [s for s in steps if "docker build" in str(s.get("run", ""))]
    assert len(builds) == 1  # one image, built once
    step = next(s for s in steps if str(s.get("name", "")).startswith("F17 on the reference"))
    run = step["run"]
    assert "set -euo pipefail" in run
    assert "for i in 1 2; do" in run
    assert (
        'docker run --rm --network none -v "$PWD/smoke:/work" -w /work proofpack:ci run '
        "--input /work/f17in/synthetic.csv" in run
    )
    assert "--out /work/f17ref/run$i --format json --offline" in run
    assert "--n 5000 --inputs-only" in run
    assert "--compare-dirs /work/f17ref/run1 /work/f17ref/run2 --require-reference-platform" in run
    assert run.count("--network none") == 3
    assert steps.index(step) > steps.index(builds[0])
    upload = steps[steps.index(step) + 1]
    assert upload["uses"] == "actions/upload-artifact@v7"
    assert upload["with"]["name"] == f17.CI_ARTEFACT == "f17-reference-image"
    assert upload["with"]["if-no-files-found"] == "error"
    for path in ("run1/run.json", "run2/run.json", "f17_result.json"):
        assert f"smoke/f17ref/{path}" in upload["with"]["path"]
    assert f17.CI_TEST_FILE == "tests/test_f17_reference_image.py"
