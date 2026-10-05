"""E12 repair 3 (Monday 5 October 2026): DEC-77 and the two blockers of the cold
fresh-attack lens on ``e6ad3c8`` (``handoffs/2026-10-05_E_e12_lens3_fresh-attack.md`` B1 and
B2; ``handoffs/2026-10-05_E_e12_lens3_regression.md`` reported PASS).

DEC-77 (Josh, 5 October 2026): pROC's aSAH rows are never committed and never leave the
GitHub runner. ``capture.R`` writes them to the file ``PROOFPACK_ASAH_VECTORS`` names in the
runner's temporary space; the engine compares itself with pROC there
(``scripts/r_f13_compare.py``) and the job uploads three JSON files from ``upload/`` after
``scripts/r_upload_guard.py`` inspects it. Outside the job the F13 comparisons that need the
vectors skip with ``r_vectors_not_committed_dec77``, and the F13 report row reads the job's
recorded comparison (``suite_only``).

Each test names the finding it pins and the literal inputs it feeds. Which of these fail at
``e6ad3c8`` (measured in a detached worktree with ``PYTHONPATH=<worktree>/src``), and the
mutants each kills, are in the repair note.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import test_day12_r_captures as d12
import test_e12_repair2 as r2
from proofpack import fixtures as fx

pytestmark = pytest.mark.day12

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
SRC = Path(fx.__file__).resolve().parents[1]
CORRUPT_LINE = b"81,Good,2,0.5,9.5\n"  # y = 2: the loader raises ValueError

#: The three F13 comparisons that need the vectors (the job's shape).
F13_JOB_TESTS = (
    "test_f13_engine_auroc_delong_variance_interval_and_paired_test_equal_proc_on_asah",
    "test_f13_capture_recorded_the_sha256_of_the_vectors_it_wrote",
    "test_the_fixtures_report_row_f13_is_matched",
)
F13_RECORDED_TEST = "test_f13_outside_the_job_the_row_reads_the_recorded_comparison_as_suite_only"
F13B_TESTS = (
    "test_f13b_engine_slope_and_joint_intercept_equal_val_prob_slope_and_intercept",
    "test_f13b_engine_intercept_in_the_large_equals_the_glm_offset_intercept",
    "test_f13b_every_compared_value_equals_the_capture",
    "test_f13b_capture_recorded_the_sha256_of_the_committed_f4_bytes_read_as_lf",
    "test_the_fixtures_report_row_f13b_is_matched",
)


def _capture(tmp_path: Path, monkeypatch) -> Path:
    """The synthetic capture in ``tmp_path/r``, made the day-12 module's ``COMMITTED`` and
    ``fixtures.r_captures_dir()``; ``PROOFPACK_ASAH_VECTORS`` unset."""
    cap = tmp_path / "r"
    d12.write_synthetic_capture(cap)
    monkeypatch.setattr(d12, "COMMITTED", cap)
    monkeypatch.setattr(fx, "r_captures_dir", lambda: cap)
    monkeypatch.delenv(fx.R_VECTORS_ENV, raising=False)
    return cap


def _outcomes(module, names) -> dict[str, str]:
    get = module.get if isinstance(module, dict) else lambda n: getattr(module, n)
    return {n: r2._outcome(get(n)) for n in names}


# ------------------------------------------------- FA-B1 / FA-B2: the job's shape


def _job_case(case: str, cap: Path, tmp_path: Path) -> str:
    """The value ``PROOFPACK_ASAH_VECTORS`` takes in ``case``, after preparing it."""
    vectors = cap / "asah_vectors.csv"
    if case == "vectors corrupt (81,Good,2,0.5,9.5 appended)":
        bad = tmp_path / "corrupt.csv"
        bad.write_bytes(vectors.read_bytes() + CORRUPT_LINE)
        return str(bad)
    if case == "vectors missing":
        return str(tmp_path / "no-such-dir" / "asah_vectors.csv")
    if case == "vectors set to the empty string":
        return ""
    if case == "vectors path is a directory":
        (tmp_path / "a-directory").mkdir()
        return str(tmp_path / "a-directory")
    if case == "proc_asah.json unreadable":
        (cap / "proc_asah.json").write_text('{"values": ', encoding="utf-8")
        return str(vectors)
    if case == "proc_asah.json absent":
        (cap / "proc_asah.json").unlink()
        return str(vectors)
    raise AssertionError(case)


JOB_CASES = (
    "vectors corrupt (81,Good,2,0.5,9.5 appended)",
    "vectors missing",
    "vectors set to the empty string",
    "vectors path is a directory",
    "proc_asah.json unreadable",
    "proc_asah.json absent",
)


@pytest.mark.parametrize("case", JOB_CASES)
def test_fa_b1_in_the_job_shape_each_unreadable_or_missing_file_fails_the_f13_comparisons(
    tmp_path, monkeypatch, case
):
    """Lens 3 FA-B1 (and the DEC-77 runner shape): ``PROOFPACK_ASAH_VECTORS`` set and one
    needed file unreadable or missing, per ``case``. Each of the three F13 comparisons that
    need the vectors reads ``failed``, none ``skipped``. At ``e6ad3c8`` no test fed the
    vectors file unreadable, and mutant G3 made the comparisons skip as "absent"."""
    cap = _capture(tmp_path, monkeypatch)
    monkeypatch.setenv(fx.R_VECTORS_ENV, _job_case(case, cap, tmp_path))
    assert _outcomes(d12, F13_JOB_TESTS) == dict.fromkeys(F13_JOB_TESTS, "failed")


def test_fa_b1_control_in_the_job_shape_the_three_f13_comparisons_pass(tmp_path, monkeypatch):
    cap = _capture(tmp_path, monkeypatch)
    monkeypatch.setenv(fx.R_VECTORS_ENV, str(cap / "asah_vectors.csv"))
    assert _outcomes(d12, F13_JOB_TESTS) == dict.fromkeys(F13_JOB_TESTS, "passed")


def test_fa_b2_a_corrupt_vectors_file_is_named_unreadable_and_row_f13_says_so(tmp_path):
    """Lens 3 FA-B2: the synthetic vectors with ``81,Good,2,0.5,9.5`` appended, named
    through ``vectors=``. ``unreadable`` is exactly that file with ``ValueError``; row F13 is
    ``not_matched`` with ``oracle_file_unreadable: $PROOFPACK_ASAH_VECTORS
    (asah_vectors.csv) (ValueError)``. Mutant L1 (the loader's ``unreadable.append`` for the
    vectors -> ``pass``) fails both assertions."""
    cap = tmp_path / "r"
    d12.write_synthetic_capture(cap)
    bad = tmp_path / "corrupt.csv"
    bad.write_bytes((cap / "asah_vectors.csv").read_bytes() + CORRUPT_LINE)
    caps = fx.load_r_captures(cap, vectors=bad)
    assert caps.unreadable == ((fx.R_VECTORS_FILE, "ValueError"),)
    assert caps.vectors is None
    row = fx.compare_row(fx.r_capture_rows(caps)[0], {})
    assert (row["status"], row["reason"]) == (
        "not_matched",
        "oracle_file_unreadable: $PROOFPACK_ASAH_VECTORS (asah_vectors.csv) (ValueError)",
    )


@pytest.mark.parametrize(
    "case",
    ["f13_engine_comparison.json unreadable", "proc_asah.json unreadable", "comparison a dir"],
)
def test_outside_the_job_an_unreadable_needed_file_fails_the_recorded_comparison(
    tmp_path, monkeypatch, case
):
    """Outside the job (``PROOFPACK_ASAH_VECTORS`` unset): ``f13_engine_comparison.json`` or
    ``proc_asah.json`` written as ``{"values": ``, or the comparison file replaced by a
    directory: the recorded-comparison test reads ``failed``, not ``skipped``."""
    cap = _capture(tmp_path, monkeypatch)
    if case == "comparison a dir":
        (cap / "f13_engine_comparison.json").unlink()
        (cap / "f13_engine_comparison.json").mkdir()
    else:
        (cap / case.split()[0]).write_text('{"values": ', encoding="utf-8")
    assert _outcomes(d12, [F13_RECORDED_TEST]) == {F13_RECORDED_TEST: "failed"}


def test_an_unreadable_f13b_capture_fails_the_five_f13b_comparisons(tmp_path, monkeypatch):
    cap = _capture(tmp_path, monkeypatch)
    (cap / "rms_val_prob_f4.json").write_text('{"values": ', encoding="utf-8")
    assert _outcomes(d12, F13B_TESTS) == dict.fromkeys(F13B_TESTS, "failed")


# ----------------------------------------------------- the gate mutants, planted

#: Mutants of the day-12 module's gates: (the text replaced, its replacement). R1-R3 turn
#: the job shape's failure into a skip; G3a / G3b are lens 3's G3 moved to the files the
#: recorded-comparison gate needs (lens 3's literal G3, on the vectors, is equivalent in
#: this code: that gate reads with the vectors not read).
GATE_MUTANTS = {
    "R1 skip when the vectors were not read": (
        "    return fx.load_r_captures(directory or COMMITTED)\n",
        "    caps = fx.load_r_captures(directory or COMMITTED)\n"
        "    if caps.vectors is None:\n"
        "        pytest.skip(f13_vectors_skip_reason())\n"
        "    return caps\n",
    ),
    "R2 an empty value reads as unset": (
        "    if fx.R_VECTORS_ENV not in os.environ:\n",
        "    if not os.environ.get(fx.R_VECTORS_ENV):\n",
    ),
    "R3 skip when the vectors are unreadable": (
        "    return fx.load_r_captures(directory or COMMITTED)\n",
        "    caps = fx.load_r_captures(directory or COMMITTED)\n"
        "    if fx.R_VECTORS_FILE in dict(caps.unreadable):\n"
        "        pytest.skip(f13_vectors_skip_reason())\n"
        "    return caps\n",
    ),
    "G3a the gate ignores an unreadable comparison file": (
        "    bad = {f for f, _ in caps.unreadable}\n",
        "    bad = {f for f, _ in caps.unreadable if f != fx.R_COMPARISON_FILE}\n",
    ),
    "G3b the gate ignores an unreadable proc_asah.json": (
        "    bad = {f for f, _ in caps.unreadable}\n",
        "    bad = {f for f, _ in caps.unreadable if f != fx.R_CAPTURE_FILES[0]}\n",
    ),
}


@pytest.mark.parametrize("mutant", sorted(GATE_MUTANTS))
def test_each_gate_mutant_fails_the_skip_reason_test(tmp_path, monkeypatch, mutant):
    """Each mutant of :data:`GATE_MUTANTS` planted in the day-12 module's source: its
    skip-reason test reads ``failed`` (unmutated: ``passed``, the control below)."""
    old, new = GATE_MUTANTS[mutant]
    source = r2._day12_source()
    assert source.count(old) == 1, mutant
    module = r2._day12_module(source.replace(old, new))
    skip_test = module["test_the_skip_reasons_are_the_typed_strings"]
    assert r2._outcome(skip_test, tmp_path, monkeypatch) == "failed"


@pytest.mark.parametrize("mutant", ["R1 skip when the vectors were not read"])
def test_under_r1_the_job_shape_comparisons_skip_where_unmutated_they_fail(
    tmp_path, monkeypatch, mutant
):
    """What R1 would do, measured: with the vectors corrupt, the three F13 comparisons of the
    mutated module read ``skipped`` (unmutated: ``failed``, the parametrised test above)."""
    old, new = GATE_MUTANTS[mutant]
    module = r2._day12_module(r2._day12_source().replace(old, new))
    cap = _capture(tmp_path, monkeypatch)
    module["COMMITTED"] = cap
    monkeypatch.setenv(fx.R_VECTORS_ENV, _job_case(JOB_CASES[0], cap, tmp_path))
    assert _outcomes(module, F13_JOB_TESTS) == dict.fromkeys(F13_JOB_TESTS, "skipped")


# --------------------------------------------- DEC-77: outside the job, the record


def _row13(cap: Path) -> dict:
    return fx.compare_row(fx.r_capture_rows(fx.load_r_captures(cap, vectors=None))[0], {})


def test_dec77_outside_the_job_f13_is_suite_only_and_names_the_run_and_the_engine_commit(
    tmp_path, monkeypatch
):
    """The synthetic capture and its record (run ``20261005``, engine ``e`` x 40) with the
    vectors not read. HEAD ``e`` x 40: ``suite_only``, the reason names the run, the
    commit, ``a local re-check needs R`` and "the engine commit is this checkout's HEAD",
    and holds no ``matched``. HEAD ``f`` x 40: the reason says the commit "is not this
    checkout's HEAD". HEAD not read: it says so. A vectors file in the capture directory
    is not read (``vectors`` ``None``, not in ``present``)."""
    cap = _capture(tmp_path, monkeypatch)
    monkeypatch.setattr(fx, "git_sha", lambda: (d12.SYNTHETIC_ENGINE_SHA, "test"))
    row = _row13(cap)
    assert row["status"] == "suite_only" and row["matched"] is False
    assert row["n_values_compared"] == 0 and row["oracle_source"] is None
    assert row["max_abs_deviation"] is not None and row["max_abs_deviation"] < 1e-12
    assert row["suite_tests"] == list(fx.F13_RUNNER_SUITE)
    reason = row["reason"]
    for part in (
        "compared inside the r-captures job, not by this command",
        f"GitHub run {d12.SYNTHETIC_RUN_ID}",
        f"engine at commit {d12.SYNTHETIC_ENGINE_SHA}",
        "max abs deviation",
        "the engine commit is this checkout's HEAD",
        "a local re-check needs R",
        "DEC-77",
    ):
        assert part in reason, part
    assert "matched" not in reason
    monkeypatch.setattr(fx, "git_sha", lambda: ("f" * 40, "test"))
    assert (
        "the engine commit is not this checkout's HEAD (" + "f" * 40 + ")" in _row13(cap)["reason"]
    )
    monkeypatch.setattr(fx, "git_sha", lambda: (None, "not a git checkout"))
    assert "this checkout's HEAD was not read (not a git checkout)" in _row13(cap)["reason"]
    caps = fx.load_r_captures(cap, vectors=None)
    assert (cap / "asah_vectors.csv").exists() and caps.vectors is None
    assert fx.R_VECTORS_FILE not in caps.present
    rep = fx.run_fixtures(rows=fx.r_capture_rows(caps), doctor=False)
    fx.validate_report(rep)
    assert rep["summary"]["suite_only"] == 1 and rep["summary"]["matched"] == 1
    st = fx.r_captures_status(caps)
    assert st["status"] == fx.R_CAPTURES_PRESENT


def _edit_record(cap: Path, fn) -> None:
    path = cap / "f13_engine_comparison.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _move_engine(doc, by=2e-6, name="s100b auc"):
    doc["values"][name]["engine"] += by


RECORD_EDITS = {
    "engine value +2e-6 (s100b auc)": (_move_engine, "outside tolerance: s100b auc"),
    "within true but engine +2e-6": (
        lambda d: (_move_engine(d), d["values"]["s100b auc"].update(within=True)),
        "outside tolerance: s100b auc",
    ),
    "tolerance 1e-3 and engine +2e-6": (
        lambda d: (_move_engine(d), d["values"]["s100b auc"].update(tolerance=1e-3)),
        "tolerance not 1e-06: s100b auc",
    ),
    "R value not proc_asah.json's": (
        lambda d: d["values"]["ndka auc"].update(r=0.5),
        "R value not proc_asah.json's: ndka auc",
    ),
    "a compared name removed": (
        lambda d: d["values"].pop("roc.test p.value"),
        "no engine and R numbers: roc.test p.value",
    ),
    "engine value a string": (
        lambda d: d["values"]["s100b auc"].update(engine="0.7"),
        "no engine and R numbers: s100b auc",
    ),
}


@pytest.mark.parametrize("edit", sorted(RECORD_EDITS))
def test_dec77_a_recorded_comparison_outside_tolerance_or_inconsistent_is_not_matched(
    tmp_path, monkeypatch, edit
):
    """Each edit of the synthetic record: row F13 ``not_matched`` with
    ``r_capture_recorded_not_matched`` and the named problem, and exit code 6."""
    cap = _capture(tmp_path, monkeypatch)
    fn, expected = RECORD_EDITS[edit]
    _edit_record(cap, fn)
    row = _row13(cap)
    assert row["status"] == "not_matched"
    assert row["reason"].startswith("r_capture_recorded_not_matched: ")
    assert expected in row["reason"]
    caps = fx.load_r_captures(cap, vectors=None)
    rep = fx.run_fixtures(rows=fx.r_capture_rows(caps), doctor=False)
    assert rep["exit_code"] == 6


MISMATCH_EDITS = {
    "vectors_sha256": lambda d: d.update(vectors_sha256="0" * 64),
    "vectors_rows": lambda d: d.update(vectors_rows=79),
    "github_run_id": lambda d: d.update(github_run_id="1"),
    "proc_asah_sha256": lambda d: d.update(proc_asah_sha256="0" * 64),
    "engine_sha": lambda d: d.update(engine_sha="HEAD"),
    "schema": lambda d: d.update(schema="proofpack-r-f13-comparison/0"),
}


@pytest.mark.parametrize("key", sorted(MISMATCH_EDITS))
def test_dec77_a_record_that_does_not_belong_to_proc_asah_is_an_input_mismatch(
    tmp_path, monkeypatch, key
):
    """``key`` of the synthetic record changed (``vectors_sha256`` / ``proc_asah_sha256``
    ``0`` x 64, ``vectors_rows`` 79, ``github_run_id`` ``1``, ``engine_sha`` ``HEAD``, the
    schema ``.../0``): row F13 ``not_matched`` with ``r_capture_input_mismatch`` naming the
    file. And ``proc_asah.json`` edited after the record was written (a value +1e-9)
    gives the same (its sha256 no longer matches)."""
    cap = _capture(tmp_path, monkeypatch)
    _edit_record(cap, MISMATCH_EDITS[key])
    row = _row13(cap)
    assert row["status"] == "not_matched"
    assert row["reason"].startswith("r_capture_input_mismatch: fixtures/r/f13_engine_comparison")
    cap2 = _capture(tmp_path / "second", monkeypatch)
    d12._edit(cap2 / "proc_asah.json", lambda d: d["values"].update({"s100b auc": 0.7}))
    assert _row13(cap2)["reason"].startswith(
        "r_capture_input_mismatch: fixtures/r/f13_engine_comparison.json proc_asah_sha256"
    )


def test_dec77_the_record_holds_no_vector_line(tmp_path):
    """``fixtures.f13_comparison_record`` on the synthetic capture: the 16 F13 names, status
    ``matched``, 80 rows, and none of the 80 data lines of the vectors file (nor its header)
    in the JSON text; with the vectors not read it raises ``ValueError``."""
    cap = tmp_path / "r"
    d12.write_synthetic_capture(cap)
    record = fx.f13_comparison_record(d12._load(cap), engine_sha="a" * 40, run_id="7")
    assert sorted(record["values"]) == sorted(fx.F13_NAMES)
    assert record["status"] == "matched" and record["vectors_rows"] == 80
    text = json.dumps(record)
    lines = (cap / "asah_vectors.csv").read_text(encoding="utf-8").splitlines()
    data = [ln for ln in lines if ln and not ln.startswith("#")]
    assert len(data) == 81  # the header and 80 rows
    assert not [ln for ln in data if ln in text]
    with pytest.raises(ValueError, match="PROOFPACK_ASAH_VECTORS is not set"):
        fx.f13_comparison_record(
            fx.load_r_captures(cap, vectors=None), engine_sha="a" * 40, run_id="7"
        )


def test_dec77_the_vectors_repr_holds_no_value(tmp_path):
    """Vectors whose values are 0.123456789 / 98765.4321 and 0.987654321 / 12345.6789:
    neither value appears in ``repr`` or ``str`` of the captures or of the vectors, which
    read ``<aSAH vectors withheld (DEC-77): 2 rows>``; the arrays are read-only."""
    path = tmp_path / "v.csv"
    path.write_text(
        "row,outcome,y,s100b,ndka\n1,Good,0,0.123456789,98765.4321\n"
        "2,Poor,1,0.987654321,12345.6789\n",
        encoding="utf-8",
    )
    caps = fx.load_r_captures(tmp_path, vectors=path)
    shown = repr(caps) + str(caps) + repr(caps.vectors) + str(caps.vectors)
    for value in ("0.123456789", "98765.4321", "0.987654321", "12345.6789", "0.12345", "98765"):
        assert value not in shown, value
    assert repr(caps.vectors) == "<aSAH vectors withheld (DEC-77): 2 rows>"
    with pytest.raises(ValueError):
        caps.vectors["s100b"][0] = 1.0


def test_dec77_a_failing_assertion_on_the_captures_prints_no_vector_value(tmp_path):
    """The leak route pytest's assertion output opens: a test asserting
    ``caps.vectors is not None and caps.proc is not None`` on captures whose vectors were
    read and whose ``proc_asah.json`` is absent, run by pytest in a subprocess. Its output
    holds ``withheld`` and none of ``0.12345679`` / ``0.98765432`` (numpy's print of the
    s100b values), ``98765.4321``, ``12345.6789``. At ``e6ad3c8`` the same assertion on the
    ``RCaptures`` of that commit printed ``'ndka': array([98765.4321, 12345.6789])``
    (measured in the repair note)."""
    vec = tmp_path / "v.csv"
    vec.write_text(
        "row,outcome,y,s100b,ndka\n1,Good,0,0.123456789,98765.4321\n"
        "2,Poor,1,0.987654321,12345.6789\n",
        encoding="utf-8",
    )
    (tmp_path / "t").mkdir()
    (tmp_path / "t" / "test_leak.py").write_text(
        "import os\nfrom pathlib import Path\nfrom proofpack import fixtures as fx\n\n\n"
        "def test_leak():\n"
        "    caps = fx.load_r_captures(Path(os.environ['LEAK_DIR']),"
        " vectors=Path(os.environ['LEAK_VEC']))\n"
        "    assert caps.vectors is not None and caps.proc is not None\n",
        encoding="utf-8",
    )
    env = dict(os.environ, LEAK_DIR=str(tmp_path / "t"), LEAK_VEC=str(vec))
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_leak.py"],
        cwd=tmp_path / "t",
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    out = proc.stdout + proc.stderr
    assert "1 failed" in out and "withheld" in out, out[-2000:]
    for value in ("0.12345679", "0.98765432", "98765.4321", "12345.6789"):
        assert value not in out, value  # numpy prints s100b to 8 significant digits


# ------------------------------------------------------ the two scripts the job runs


def _script(name: str, args: list[str], env_extra: dict, cwd: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in (fx.R_VECTORS_ENV, "GITHUB_SHA")}
    env.update(env_extra)
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )


def test_r_f13_compare_refuses_without_the_variable_fails_on_missing_vectors_and_writes_a_record(
    tmp_path,
):
    """``scripts/r_f13_compare.py`` on the synthetic capture: ``PROOFPACK_ASAH_VECTORS``
    unset -> exit 2; set to a missing file -> exit 1 and no record; set to the vectors with
    ``--engine-sha`` ``a`` x 40 -> exit 0, a record whose ``status`` is ``matched``, 16
    printed per-name lines, and none of the vectors' data lines in the output; that record
    copied over the synthetic one reads ``suite_only`` outside the job."""
    cap = tmp_path / "r"
    d12.write_synthetic_capture(cap)
    out = tmp_path / "out" / "f13_engine_comparison.json"
    args = ["--captures", str(cap), "--out", str(out), "--engine-sha", "a" * 40]
    assert _script("r_f13_compare.py", args, {}, tmp_path).returncode == 2
    missing = {fx.R_VECTORS_ENV: str(tmp_path / "none.csv")}
    assert _script("r_f13_compare.py", args, missing, tmp_path).returncode == 1
    assert not out.exists()
    good = {fx.R_VECTORS_ENV: str(cap / "asah_vectors.csv"), "GITHUB_RUN_ID": "20261005"}
    proc = _script("r_f13_compare.py", args, good, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["status"] == "matched" and record["engine_sha"] == "a" * 40
    assert len([ln for ln in proc.stdout.splitlines() if " tolerance " in ln]) == 16
    data = (cap / "asah_vectors.csv").read_text(encoding="utf-8").splitlines()[2:]
    assert not [ln for ln in data if ln in proc.stdout]
    (cap / "f13_engine_comparison.json").write_bytes(out.read_bytes())
    assert _row13(cap)["status"] == "suite_only"


def _upload_dir(tmp_path: Path) -> Path:
    cap = tmp_path / "r"
    d12.write_synthetic_capture(cap)
    up = tmp_path / "upload"
    up.mkdir()
    for name in d12.DEC77_UPLOADED:
        (up / name).write_bytes((cap / name).read_bytes())
    return up


UPLOAD_PLANTS = {
    "asah_vectors.csv added": ("asah_vectors.csv", b"row,outcome,y,s100b,ndka\n"),
    "a .CSV file added": ("x.CSV", b"a,b\n"),
    "ASAH-Vectors.json added": ("ASAH-Vectors.json", b"{}"),
    "notes.txt added": ("notes.txt", b"nothing"),
    "the header inside a JSON file": ("proc_asah.json", b'{"x": "row,outcome,y,s100b,ndka"}'),
    "a data line inside a JSON file": ("rms_val_prob_f4.json", None),
}


@pytest.mark.parametrize("plant", sorted(UPLOAD_PLANTS))
def test_dec77_upload_guard_exits_1_on_each_plant(tmp_path, plant):
    """``scripts/r_upload_guard.py`` on ``upload/`` holding the three synthetic JSON files,
    with ``PROOFPACK_ASAH_VECTORS`` naming the synthetic vectors, and one plant: a file
    named ``asah_vectors.csv``, ``x.CSV``, ``ASAH-Vectors.json`` or ``notes.txt``; the
    vectors' header in ``proc_asah.json``; the vectors' fifth data line inside
    ``rms_val_prob_f4.json``. Each exits 1."""
    up = _upload_dir(tmp_path)
    vec = tmp_path / "r" / "asah_vectors.csv"
    name, data = UPLOAD_PLANTS[plant]
    if data is None:
        line = vec.read_text(encoding="utf-8").splitlines()[6]
        data = json.dumps({"note": line}).encode("utf-8")
    (up / name).write_bytes(data)
    proc = _script("r_upload_guard.py", [str(up)], {fx.R_VECTORS_ENV: str(vec)}, tmp_path)
    assert proc.returncode == 1, proc.stdout
    assert "row,outcome" not in proc.stdout.replace("row,outcome,y,s100b,ndka", "")


def test_dec77_upload_guard_control_the_three_json_files_exit_0_and_a_missing_one_exits_1(
    tmp_path,
):
    up = _upload_dir(tmp_path)
    vec = {fx.R_VECTORS_ENV: str(tmp_path / "r" / "asah_vectors.csv")}
    proc = _script("r_upload_guard.py", [str(up)], vec, tmp_path)
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.strip().endswith("0 problem(s) in " + str(up))
    (up / "f13_engine_comparison.json").unlink()
    assert _script("r_upload_guard.py", [str(up)], vec, tmp_path).returncode == 1


# ------------------------------------------------------ the sentences this repair changed


def test_the_day12_docstring_names_what_the_skip_reason_test_feeds():
    """Lens 3 FA-B1: the module docstring said the test asserts "that neither gate skips when
    a file it needs is unreadable"; it fed two of the three files. The sentence is gone; the
    docstring names the inputs, ``81,Good,2,0.5,9.5`` among them."""
    doc = " ".join((d12.__doc__ or "").split())
    assert "neither gate skips when a file it needs is unreadable" not in doc
    for fed in ("81,Good,2,0.5,9.5", "a path that does not exist", "the empty string"):
        assert fed in doc, fed


def test_the_readme_states_dec77_as_decided_and_what_is_committed():
    """At ``e6ad3c8`` the README said whether ``asah_vectors.csv`` may be committed "is open"
    and "is a question for Josh". It now states DEC-77 as decided, names the three JSON
    files the artefact holds, and says the vectors are never committed or uploaded."""
    readme = " ".join((REPO / "fixtures" / "r" / "README.md").read_text("utf-8").split())
    assert "is open" not in readme and "question for Josh" not in readme
    assert "DEC-77" in readme and "decided" in readme
    for name in d12.DEC77_UPLOADED:
        assert f"`{name}`" in readme, name
    assert "never committed" in readme and "never uploaded" in readme


def test_the_loader_names_a_capture_path_that_is_a_directory_unreadable(tmp_path):
    """Lens 3 regression N4: ``proc_asah.json`` a directory crashed ``--r-captures`` (exit 5,
    ``PermissionError``). The loader names it in ``unreadable`` and row F13 is
    ``not_matched``."""
    (tmp_path / "proc_asah.json").mkdir()
    caps = fx.load_r_captures(tmp_path, vectors=None)
    assert [f for f, _ in caps.unreadable] == ["fixtures/r/proc_asah.json"]
    row = fx.compare_row(fx.r_capture_rows(caps)[0], {})
    assert row["status"] == "not_matched"
    assert row["reason"].startswith("oracle_file_unreadable: fixtures/r/proc_asah.json (")
