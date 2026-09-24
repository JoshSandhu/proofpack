"""A-P3 repair 1 (build day 9, lane A): the lens-1 findings at ``1a967d8``, each as the
literal input the lens fed and the figure it measured.

* FA-B1 / FA-R2: F8's engine output with ``half_width_n50`` left out, and with it set to
  NaN, through ``main(["fixtures", ...])``: exit 6, ``fixtures_report.json`` written and
  schema-valid, row ``F8-half-width`` not matched with ``max_abs_deviation`` null (at
  ``1a967d8`` the NaN case exited 5 with ``ValueError`` and wrote no report). The oracle
  entry ``captured.F1-wilson`` deleted: exit 6, row ``F1-wilson`` reason
  ``oracle_error: KeyError`` (was exit 5, ``KeyError``). ``f4_expected.json`` absent:
  exit 6, rows ``F4-closed-form``, ``F4-irls`` and ``F4-register`` reason
  ``oracle_file_missing: f4_expected.json`` (was exit 5, ``FileNotFoundError``).
* FA-R1: ``fixtures.py`` placed at ``<X>/vendor/proofpack/`` inside a directory ``<X>`` with
  ``.git`` and a ``pyproject.toml`` naming ``customer``: ``git_sha`` is null and git is
  not called (at ``1a967d8`` it returned the HEAD of ``<X>``).
* RG-B1: T12's W16 row does not print "exit 2"; its exit-0 row names W16.
* FA-R4: each code in T12's failure-mode table is either written as a quoted literal in a
  ``.py`` file under ``src/proofpack`` outside ``errors.py`` and ``render/``, or its action
  begins "not raised in this version" (H10 at ``1a967d8`` did neither).
* FA-R3: T12's doctor table has no "Condition held" column; a doctor row with ``ok`` false
  prints "yes" under "Flagged by doctor" and the caption counts 1.
* FA-R7: no tolerance rule cites D1 section 9 for published tables; the F14 rule says D1
  section 9 gives no tolerance for its table; the policy source names D1 section 3.2 for
  the register class.
* The sentences the lenses found false (FA-R2, FA-R5 / RG-B2, FA-R11, FA-R13 / RG-N4,
  RG-N3, RG-N5) are absent from the files that carried them.
"""

from __future__ import annotations

import copy
import json
import math
import re
import subprocess
import types
from pathlib import Path

import pytest

from conftest import ephemeral_registry
from proofpack import errors
from proofpack import fixtures as fx
from proofpack.cli import main
from proofpack.errors import EXIT_FIXTURES_NOT_MATCHED
from proofpack.render import t12

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src" / "proofpack"


def _cli(tmp_path: Path) -> tuple[int, dict | None, str]:
    rc = main(["fixtures", "--offline", "--out", str(tmp_path)], registry=ephemeral_registry())
    path = tmp_path / fx.REPORT_FILE
    doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    return rc, doc, ""


def _row(doc: dict, row_id: str) -> dict:
    return next(r for r in doc["rows"] if r["id"] == row_id)


# ----------------------------------------------------------- FA-B1 / FA-R2: the rows


def test_an_engine_value_left_out_is_not_matched_and_exits_6(tmp_path, monkeypatch, capsys):
    real = fx._f8
    monkeypatch.setattr(
        fx, "_f8", lambda: {k: v for k, v in real().items() if k != "half_width_n50"}
    )
    rc, doc, _ = _cli(tmp_path)
    printed = capsys.readouterr().out
    assert rc == EXIT_FIXTURES_NOT_MATCHED == 6, printed
    assert doc is not None and doc["exit_code"] == 6
    fx.validate_report(doc)
    row = _row(doc, "F8-half-width")
    assert row["status"] == "not_matched" and row["matched"] is False
    assert row["max_abs_deviation"] is None
    cell = next(v for v in row["values"] if v["name"] == "half_width_n50")
    assert cell == {
        "name": "half_width_n50",
        "engine": None,
        "oracle": cell["oracle"],
        "abs_deviation": None,
        "tolerance": 1e-9,
        "within": False,
    }
    assert row["reason"] == "engine value missing: half_width_n50"
    assert "not matched: F8-half-width (engine value missing: half_width_n50)" in printed


def test_an_engine_nan_is_not_matched_the_report_is_written_and_exits_6(tmp_path, monkeypatch):
    real = fx._f8

    def with_nan():
        out = real()
        out["half_width_n50"] = float("nan")
        return out

    monkeypatch.setattr(fx, "_f8", with_nan)
    rc, doc, _ = _cli(tmp_path)
    assert rc == 6 and doc is not None
    fx.validate_report(doc)
    text = (tmp_path / fx.REPORT_FILE).read_text(encoding="utf-8")
    assert "NaN" not in text and "Infinity" not in text
    row = _row(doc, "F8-half-width")
    assert row["status"] == "not_matched" and row["max_abs_deviation"] is None
    assert row["reason"] == "engine value not finite (nan): half_width_n50"
    # T12 prints "—" for the row's largest deviation, not the largest of the others
    page = t12.render_t12(doc)
    cells = re.search(r'<tr data-row="F8-half-width">(.*?)</tr>', page).group(1)
    assert '<td class="num mono">—</td>' in cells


def test_a_deleted_oracle_entry_is_not_matched_and_exits_6(tmp_path, monkeypatch):
    oracles = copy.deepcopy(fx.load_oracles())
    del oracles["oracles_v1.json"]["captured"]["F1-wilson"]
    monkeypatch.setattr(fx, "load_oracles", lambda: oracles)
    rc, doc, _ = _cli(tmp_path)
    assert rc == 6 and doc is not None
    fx.validate_report(doc)
    row = _row(doc, "F1-wilson")
    assert row["status"] == "not_matched" and row["reason"] == "oracle_error: KeyError"
    assert [r["id"] for r in doc["rows"] if r["status"] == "not_matched"] == ["F1-wilson"]


def test_an_absent_oracle_file_is_not_matched_and_exits_6(tmp_path, monkeypatch):
    real = fx.resource_path

    def without_f4(name):
        if name == "f4_expected.json":
            raise FileNotFoundError(name)
        return real(name)

    monkeypatch.setattr(fx, "resource_path", without_f4)
    rc, doc, _ = _cli(tmp_path)
    assert rc == 6 and doc is not None
    fx.validate_report(doc)
    hit = {r["id"]: r["reason"] for r in doc["rows"] if r["status"] == "not_matched"}
    assert hit == {
        "F4-closed-form": "oracle_file_missing: f4_expected.json",
        "F4-irls": "oracle_file_missing: f4_expected.json",
        "F4-register": "oracle_file_missing: f4_expected.json",
    }


def test_a_planted_row_with_one_value_missing_and_one_nan_is_not_matched():
    row = fx.Row(
        "F8-planted",
        "F8",
        "planted",
        tolerance_class="closed_form",
        engine=lambda: {"a": 1.0, "b": math.inf},
        oracle=lambda o: ({"a": 1.0, "b": 2.0, "c": 3.0}, {k: 1e-9 for k in "abc"}, {}),
    )
    out = fx.compare_row(row, {})
    assert out["status"] == "not_matched" and out["matched"] is False
    assert out["max_abs_deviation"] is None
    assert [v["within"] for v in out["values"]] == [True, False, False]
    assert out["reason"] == "engine value not finite (inf): b; engine value missing: c"


# ------------------------------------------------------------------ FA-R1: git_sha


def _fake_git(status_out: str = "", status_rc: int = 0):
    calls: list[list[str]] = []

    def run(cmd, **kw):
        calls.append(cmd)
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "a" * 40 + "\n", "")
        return subprocess.CompletedProcess(cmd, status_rc, status_out, "")

    return types.SimpleNamespace(run=run, SubprocessError=subprocess.SubprocessError), calls


def _tree(root: Path, project: str, package: str) -> Path:
    (root / ".git").mkdir(parents=True)
    (root / "pyproject.toml").write_text(f'[project]\nname = "{project}"\n', encoding="utf-8")
    target = root / package / "fixtures.py"
    target.parent.mkdir(parents=True)
    target.write_text("", encoding="utf-8")
    return target


@pytest.mark.parametrize("project", ["customer", "proofpack"])
def test_git_sha_is_null_for_a_wheel_vendored_inside_another_git_repository(
    tmp_path, monkeypatch, project
):
    target = _tree(tmp_path / "X", project, "vendor/proofpack")
    fake, calls = _fake_git()
    monkeypatch.setattr(fx, "subprocess", fake)
    monkeypatch.setattr(fx, "__file__", str(target))
    sha, source = fx.git_sha()
    assert sha is None and source == fx.NOT_THE_PROOFPACK_CHECKOUT
    assert calls == []


@pytest.mark.parametrize(
    ("status_out", "status_rc", "state"),
    [
        ("", 0, "tracked files unmodified"),
        (" M src/proofpack/fixtures.py\n", 0, "tracked files modified"),
        ("", 128, "tracked-file state not read (git status failed)"),
    ],
)
def test_git_sha_in_a_proofpack_checkout_records_the_tracked_file_state(
    tmp_path, monkeypatch, status_out, status_rc, state
):
    target = _tree(tmp_path / "Y", "proofpack", "src/proofpack")
    fake, calls = _fake_git(status_out, status_rc)
    monkeypatch.setattr(fx, "subprocess", fake)
    monkeypatch.setattr(fx, "__file__", str(target))
    sha, source = fx.git_sha()
    assert sha == "a" * 40 and source == f"{fx.GIT_SHA_SOURCE}; {state}"
    assert len(calls) == 2


# ------------------------------------------------------ RG-B1, FA-R4, FA-R3: T12


def test_t12_does_not_give_w16_the_exit_2_action():
    rows = {r["code"]: r for r in t12.failure_mode_rows()}
    assert "exit 2" not in rows["W16"]["does"]
    assert "the exit code is the run's own" in rows["W16"]["does"]
    assert rows["exit 0"]["inspects"] == "no HALT, no warning other than W16, a usable licence"
    # every other W-code keeps the exit-2 action
    for code in errors.WARN_CODES:
        if code != "W16":
            assert rows[code]["does"] == t12.WARNING_ACTION, code


def test_each_failure_mode_code_is_raised_somewhere_or_says_it_is_not():
    sources = [
        p.read_text(encoding="utf-8")
        for p in SRC.rglob("*.py")
        if p.name != "errors.py" and "render" not in p.relative_to(SRC).parts
    ]
    unraised = []
    for row in t12.failure_mode_rows():
        if row["kind"] == "exit":
            continue
        code = row["code"]
        quoted = (f'"{code}"', f"'{code}'")
        if not any(q in text for text in sources for q in quoted):
            unraised.append(code)
            assert row["does"].startswith("not raised in this version"), code
    assert unraised == ["H10"]


def test_t12_doctor_table_prints_doctors_mark_not_a_held_condition():
    report = fx.run_fixtures(rows=(), doctor=True)
    page = t12.render_t12(report)
    assert "Condition held" not in page and "condition not held" not in page
    ref = next(d for d in report["doctor"] if d["name"] == "reference platform")
    row = re.search(r'<tr data-check="reference platform">(.*?)</tr>', page).group(1)
    assert row.startswith("<td>reference platform</td><td>" + ("no" if ref["ok"] else "yes"))
    bad = copy.deepcopy(report)
    next(d for d in bad["doctor"] if d["name"] == "numpy")["ok"] = False
    page = t12.render_t12(bad)
    row = re.search(r'<tr data-check="numpy">(.*?)</tr>', page).group(1)
    assert row.startswith("<td>numpy</td><td>yes</td>")
    assert "(1 flagged by doctor)" in page


# --------------------------------------------------------------- FA-R7: citations


def test_the_tolerance_rules_drop_the_three_citations_lens_1_found_false():
    # repair 2 (lens FA2-R4) rewrote the rules to list their rows:
    # tests/test_ap3_repair2.py::test_each_tolerance_rule_lists_its_rows
    rules = fx.TOLERANCE_RULES
    assert "bootstrap intervals and published tables" not in rules["reported_rounding"]
    assert (
        "F14-newcombe (a published table, for which D1 section 9 gives no tolerance)"
        in (rules["reported_rounding"])
    )
    assert "lists IRLS slope/intercept and DeLong via placements" in rules["iterative"]
    assert "(D1 section 9, iterative)" not in rules["iterative"]
    report = fx.run_fixtures(doctor=False)
    assert report["tolerance_policy"]["source"] == (
        "D1 section 9 (closed_form, iterative, reported_rounding); D1 section 3.2 (register)"
    )
    cp = _row(report, "F1-clopper-pearson")
    assert cp["tolerance"]["rule"] == rules["iterative"]


# ------------------------------------------------- the sentences the lenses refused


REFUSED = {
    "src/proofpack/fixtures.py": (
        "Never raises",
        "a row reports, never raises",
        "imports no network module",
        "in the package's checkout",
        "bootstrap intervals and published tables",
    ),
    "src/proofpack/render/t12.py": ("the report itself is always written",),
    "src/proofpack/templates/T12.html": (
        "is raised by the engine itself",
        "Condition held",
        "deviations are the largest absolute difference",
    ),
    "src/proofpack/cli.py": ("Opens no socket, with or without --offline",),
    ".github/workflows/release.yml": (
        "asserts it on every line that runs the engine",
        "TestPyPI is reached by trusted publishing",
    ),
    "Dockerfile": ("No key material enters", "admits nothing else"),
    ".dockerignore": ("and nothing else",),
    "tests/test_fixtures_cmd.py": ("three interior",),
    "tests/test_offline.py": ("it had not run anywhere",),
    "tests/test_workflows.py": ("the mutation sweep's copy)",),
    "tests/test_dockerfile.py": ('pytest.skip("no Dockerfile in this tree")',),
}


@pytest.mark.parametrize("rel", sorted(REFUSED))
def test_the_sentences_the_lenses_found_false_are_gone(rel):
    text = " ".join((REPO / rel).read_text(encoding="utf-8").split())
    for sentence in REFUSED[rel]:
        assert sentence not in text, (rel, sentence)
