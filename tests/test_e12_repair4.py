"""E12 repair 4 (Monday 5 October 2026): the blockers of the two cold lenses on ``614edd2``
(``handoffs/2026-10-05_E_e12_lens4_fresh-attack.md`` B1-B4,
``handoffs/2026-10-05_E_e12_lens4_regression.md`` B1-B2).

Each test names the finding it pins and the literal inputs it feeds. Which of these fail at
``614edd2`` (measured in a detached worktree with ``PYTHONPATH=<worktree>/src``), with the
first failing line, and the mutants each kills, are in the repair note.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import test_day12_r_captures as d12
from proofpack import fixtures as fx

pytestmark = pytest.mark.day12

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
SRC = Path(fx.__file__).resolve().parents[1]
CORRUPT_LINE = b"81,Good,2,0.5,9.5\n"  # y = 2: the loader raises ValueError
VECTORS_LABEL = fx.R_VECTORS_FILE  # "$PROOFPACK_ASAH_VECTORS (asah_vectors.csv)"


def _capture(tmp_path: Path) -> Path:
    cap = tmp_path / "r"
    d12.write_synthetic_capture(cap)
    return cap


def _row_and_exit(caps: fx.RCaptures) -> tuple[dict, int]:
    rep = fx.run_fixtures(rows=fx.r_capture_rows(caps), doctor=False)
    fx.validate_report(rep)
    row = next(r for r in rep["rows"] if r["id"] == "F13")
    return row, rep["exit_code"]


# ------------------------------- FA-B1 / RG-B1 (and RG-N1): row F13 per needed file


def _make_unreadable(path: Path, how: str) -> None:
    if how == "corrupt":
        path.write_text('{"values": ', encoding="utf-8")
    else:  # a directory in the file's place
        path.unlink()
        path.mkdir()


#: Outside the job (vectors not read): each file the recorded-comparison gate needs, made
#: unreadable in turn, with the reason prefix row F13 must carry.
LOCAL_CASES = {
    'f13_engine_comparison.json written as {"values": ': (
        "f13_engine_comparison.json",
        "corrupt",
        "oracle_file_unreadable: fixtures/r/f13_engine_comparison.json (JSONDecodeError)",
    ),
    "f13_engine_comparison.json a directory": (
        "f13_engine_comparison.json",
        "dir",
        "oracle_file_unreadable: fixtures/r/f13_engine_comparison.json (",
    ),
    'proc_asah.json written as {"values": ': (
        "proc_asah.json",
        "corrupt",
        "oracle_file_unreadable: fixtures/r/proc_asah.json (JSONDecodeError)",
    ),
    "proc_asah.json a directory": (
        "proc_asah.json",
        "dir",
        "oracle_file_unreadable: fixtures/r/proc_asah.json (",
    ),
}


@pytest.mark.parametrize("case", sorted(LOCAL_CASES))
def test_fa_b1_outside_the_job_each_unreadable_needed_file_makes_row_f13_not_matched_exit_6(
    tmp_path, case
):
    """Lens 4 FA-B1 / RG-B1: the synthetic capture with one needed file written as
    ``{"values": `` or replaced by a directory, read with ``vectors=None``. Row F13 is
    ``not_matched`` with ``oracle_file_unreadable: fixtures/r/<file> (``, the report's
    exit code is 6, and the reason does not hold ``not both committed``. At ``614edd2`` only
    the pytest outcome was read for the comparison file, and mutant M20 (the loop over
    ``(R_CAPTURE_FILES[0],)`` only) made the row ``no_oracle_recorded``, exit 0."""
    cap = _capture(tmp_path)
    name, how, prefix = LOCAL_CASES[case]
    _make_unreadable(cap / name, how)
    caps = fx.load_r_captures(cap, vectors=None)
    row, exit_code = _row_and_exit(caps)
    assert (row["status"], exit_code) == ("not_matched", 6), row["reason"]
    assert row["reason"].startswith(prefix), row["reason"]
    assert "not both committed" not in row["reason"]


def _job_vectors(case: str, cap: Path, tmp_path: Path) -> Path:
    vectors = cap / "asah_vectors.csv"
    if case == "vectors with 81,Good,2,0.5,9.5 appended":
        bad = tmp_path / "corrupt.csv"
        bad.write_bytes(vectors.read_bytes() + CORRUPT_LINE)
        return bad
    if case == "vectors at a path that does not exist":
        return tmp_path / "no-such-dir" / "asah_vectors.csv"
    if case == "vectors path a directory":
        (tmp_path / "a-directory").mkdir()
        return tmp_path / "a-directory"
    if case == 'proc_asah.json written as {"values": ':
        _make_unreadable(cap / "proc_asah.json", "corrupt")
    elif case == "proc_asah.json absent":
        (cap / "proc_asah.json").unlink()
    return vectors


#: The job's shape (the vectors named): each needed file unreadable or missing in turn.
JOB_CASES = {
    "vectors with 81,Good,2,0.5,9.5 appended": f"oracle_file_unreadable: {VECTORS_LABEL} "
    "(ValueError)",
    "vectors at a path that does not exist": f"oracle_file_unreadable: {VECTORS_LABEL} "
    "(FileNotFoundError)",
    "vectors path a directory": f"oracle_file_unreadable: {VECTORS_LABEL} (",
    'proc_asah.json written as {"values": ': "oracle_file_unreadable: "
    "fixtures/r/proc_asah.json (JSONDecodeError)",
    "proc_asah.json absent": "oracle_file_missing: fixtures/r/proc_asah.json",
}


@pytest.mark.parametrize("case", sorted(JOB_CASES))
def test_rg_n1_in_the_job_shape_each_unreadable_or_missing_needed_file_makes_row_f13_not_matched(
    tmp_path, case
):
    """Lens 4 RG-N1 (the same class as FA-B1, in the job's shape): the synthetic capture
    read with ``vectors=`` naming the file ``case`` prepares. Row F13 is ``not_matched``
    with the reason ``JOB_CASES[case]`` starts with, exit code 6. Mutant M1
    (``raise OracleFileMissing(R_CAPTURE_FILES[0])`` -> ``raise OracleAbsent(F13_ABSENT)``)
    made the ``proc_asah.json absent`` case ``no_oracle_recorded``, exit 0."""
    cap = _capture(tmp_path)
    vectors = _job_vectors(case, cap, tmp_path)
    caps = fx.load_r_captures(cap, vectors=vectors)
    row, exit_code = _row_and_exit(caps)
    assert (row["status"], exit_code) == ("not_matched", 6), row["reason"]
    assert row["reason"].startswith(JOB_CASES[case]), row["reason"]


# ------------------------------------------- FA-B2: the suite_only row's max deviation


def test_fa_b2_the_suite_only_row_reports_the_largest_recorded_deviation(tmp_path, monkeypatch):
    """Lens 4 FA-B2: the synthetic record with ``s100b auc``'s ``engine`` +9e-7 and
    ``ndka auc``'s +4e-7, read with ``vectors=None``. Row F13 is ``suite_only`` and its
    ``max_abs_deviation`` equals ``max(abs(engine - r))`` over the 16 F13 names recomputed
    here from the edited record (between 8.9e-7 and 9.1e-7), and the reason holds that
    number's ``repr``. Mutant M18 (``worst = max(worst, dev)`` deleted) reported ``0.0``; a
    last-name-wins ``worst = dev`` reports ``roc.test estimate 2``'s deviation."""
    cap = _capture(tmp_path)
    monkeypatch.setattr(fx, "git_sha", lambda: (d12.SYNTHETIC_ENGINE_SHA, "test"))
    path = cap / "f13_engine_comparison.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["values"]["s100b auc"]["engine"] += 9e-7
    doc["values"]["ndka auc"]["engine"] += 4e-7
    path.write_text(json.dumps(doc), encoding="utf-8")
    expected = max(abs(doc["values"][n]["engine"] - doc["values"][n]["r"]) for n in fx.F13_NAMES)
    assert 8.9e-7 < expected < 9.1e-7
    row, exit_code = _row_and_exit(fx.load_r_captures(cap, vectors=None))
    assert row["status"] == "suite_only" and exit_code == 0, row["reason"]
    assert row["max_abs_deviation"] == expected
    assert f"max abs deviation {expected!r}" in row["reason"]


# ------------------------------------- FA-B3 / RG-B2 (a): the upload guard's output


def _vector_lines(cap: Path) -> list[str]:
    lines = (cap / "asah_vectors.csv").read_text(encoding="utf-8").splitlines()
    return [ln for ln in lines if ln and not ln.startswith("#")]


def _guard(up: Path, vec: Path, cwd: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != fx.R_VECTORS_ENV}
    env[fx.R_VECTORS_ENV] = str(vec)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "r_upload_guard.py"), str(up)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )


GUARD_NAME_PLANTS = (
    "an empty file named with the fifth data line",
    "a directory named with the fifth data line, holding a.json",
    "a file named with the fifth data line inside a directory sub",
)


@pytest.mark.parametrize("plant", GUARD_NAME_PLANTS)
def test_fa_b3_the_upload_guard_prints_no_entry_name_outside_the_three(tmp_path, plant):
    """Lens 4 FA-B3 / RG-B2 (a): ``upload/`` holds the three synthetic JSON files and an
    entry named with the synthetic vectors' fifth data line (``plant``), with
    ``PROOFPACK_ASAH_VECTORS`` naming those vectors. The guard exits 1, and none of the
    vectors' 81 lines (the header and 80 rows) appears in its stdout or stderr; its output
    counts the entries outside the three names. At ``614edd2`` it printed
    ``the files are ['5,Good,0,0.13,6.0', ...]``."""
    cap = _capture(tmp_path)
    up = tmp_path / "upload"
    up.mkdir()
    for name in d12.DEC77_UPLOADED:
        (up / name).write_bytes((cap / name).read_bytes())
    lines = _vector_lines(cap)
    assert len(lines) == 81
    line = lines[5]
    if plant == GUARD_NAME_PLANTS[0]:
        (up / line).write_bytes(b"")
    elif plant == GUARD_NAME_PLANTS[1]:
        (up / line).mkdir()
        (up / line / "a.json").write_bytes(b"{}")
    else:
        (up / "sub").mkdir()
        (up / "sub" / line).write_bytes(b"")
    proc = _guard(up, cap / "asah_vectors.csv", tmp_path)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1, out
    assert [ln for ln in lines if ln in out] == []
    assert "not among the three names" in out


def test_fa_b3_the_upload_guard_names_a_missing_allowed_file(tmp_path):
    """Control for the change above: with ``f13_engine_comparison.json`` removed, the guard
    exits 1 and names it as missing (it is one of the three names, not an entry's name)."""
    cap = _capture(tmp_path)
    up = tmp_path / "upload"
    up.mkdir()
    for name in ("proc_asah.json", "rms_val_prob_f4.json"):
        (up / name).write_bytes((cap / name).read_bytes())
    proc = _guard(up, cap / "asah_vectors.csv", tmp_path)
    assert proc.returncode == 1, proc.stdout
    assert "missing: ['f13_engine_comparison.json']" in proc.stdout


def test_fa_b3_a_file_the_guard_cannot_read_is_a_problem_named_by_error_type(
    tmp_path, monkeypatch, capsys
):
    """The guard's read of each entry raising ``PermissionError`` for ``proc_asah.json`` and
    for an entry named with the fifth data line (``Path.read_bytes`` patched; the guard run
    in-process through ``main``): exit 1, ``proc_asah.json: could not be read
    (PermissionError)`` printed, and none of the vectors' 81 lines in the output."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("r_upload_guard", SCRIPTS / "r_upload_guard.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    cap = _capture(tmp_path)
    up = tmp_path / "upload"
    up.mkdir()
    for name in d12.DEC77_UPLOADED:
        (up / name).write_bytes((cap / name).read_bytes())
    lines = _vector_lines(cap)
    (up / lines[5]).write_bytes(b"")
    blocked = {"proc_asah.json", lines[5]}
    real = Path.read_bytes

    def read_bytes(self):
        if self.parent == up and self.name in blocked:
            raise PermissionError(13, "denied")
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setenv(fx.R_VECTORS_ENV, str(cap / "asah_vectors.csv"))
    assert guard.main([str(up)]) == 1
    out = capsys.readouterr()
    text = out.out + out.err
    assert "proc_asah.json: could not be read (PermissionError)" in text
    assert [ln for ln in lines if ln in text] == []


# ------------------------------------------------------ FA-B4 and the other sentences


def test_fa_b4_the_loader_reads_vectors_named_inside_fixtures_r(tmp_path):
    """Lens 4 FA-B4: the comment on ``R_VECTORS_ENV`` said the loader reads the vectors
    "never from ``fixtures/r/``". It reads the path it is given: the synthetic vectors at
    ``<capture dir>/asah_vectors.csv`` (the capture directory standing for ``fixtures/r``)
    are read, 80 rows. The sentence is gone from ``fixtures.py``; the comment now says the
    loader reads whatever path the variable names and cites this test."""
    cap = _capture(tmp_path)
    caps = fx.load_r_captures(cap, vectors=cap / "asah_vectors.csv")
    assert caps.vectors is not None and len(caps.vectors["y"]) == 80
    source = (SRC / "proofpack" / "fixtures.py").read_text(encoding="utf-8")
    assert "never from ``fixtures/r/``" not in source
    assert "test_fa_b4_the_loader_reads_vectors_named_inside_fixtures_r" in source


#: Sentences lens 4 found false on constructed inputs (or stale), and the files they were in.
REMOVED_SENTENCES = {
    "never a line of the vectors": "scripts/r_upload_guard.py",
    "no git command and no upload of the checkout can reach it": "fixtures/r/capture.R",
    "names a file inside the working directory": "fixtures/r/README.md",
    "the workflow's compare job": "tests/test_day12_r_captures.py",
}


@pytest.mark.parametrize("sentence", sorted(REMOVED_SENTENCES))
def test_rg_b2_the_sentences_lens_4_falsified_are_gone(sentence):
    """Lens 4 FA-B3 / RG-B2 (a) (the guard's "never a line of the vectors"), RG-B2 (b)
    (``capture.R``: ``git --work-tree=<runner temp> add`` committed the vectors), FA-N7 /
    FA-B4's README twin (the check normalises ``dirname()`` only) and RG-N3 (no ``compare``
    job since repair 3): each text is absent from its file."""
    text = " ".join((REPO / REMOVED_SENTENCES[sentence]).read_text(encoding="utf-8").split())
    text = text.replace("# ", "")
    assert sentence not in text
