"""E12 repair 1 (Monday 5 October 2026): regression tests for the findings of the two cold
lenses on ``2328e86`` (``handoffs/2026-10-05_E_e12_lens1_fresh-attack.md`` and
``handoffs/2026-10-05_E_e12_lens1_regression.md``). Each test names the finding it pins
and the literal inputs it feeds. The file was run against ``2328e86`` in a detached
worktree (``PYTHONPATH=<worktree>/src``): 18 failed and 2 passed there. The 2 that passed
are the controls ``test_fa_b3_control_the_committed_workflow_copied_passes`` and
``test_rg_b2_control_the_committed_capture_r_copied_passes``, which pass at both commits
(E12 repair 2, lens 2 FA-B5). The first failing line of each of the 18 is in the repair
note.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import test_day12_r_captures as d12
from proofpack import fixtures as fx
from proofpack.stats.bootstrap import clustered_number
from proofpack.stats.number import Number

pytestmark = pytest.mark.day12

REPO = Path(__file__).resolve().parent.parent
SRC = Path(fx.__file__).resolve().parents[1]

# ------------------------------------------------------------------ FA-B1 / RG-N3

#: A pytest plugin for the subprocess below: every read of ``<checkout>/fixtures/r`` by
#: ``fixtures.load_r_captures`` reads ``E12R1_CAPTURE_DIR`` instead. The gates of
#: ``tests/test_day12_r_captures.py`` (the build's and the repair's) call
#: ``fx.load_r_captures`` with that directory, so both are fed the same files.
REDIRECT_PLUGIN = """
import os
from pathlib import Path

from proofpack import fixtures as fx

_TARGET = Path(os.environ["E12R1_CAPTURE_DIR"])
_ORIGINAL = fx.load_r_captures


def _redirect(directory=None):
    where = fx.r_captures_dir() if directory is None else Path(directory)
    if where is not None and Path(where).resolve() == (
        Path(fx.source_checkout_root()) / "fixtures" / "r"
    ).resolve():
        return _ORIGINAL(_TARGET)
    return _ORIGINAL(directory)


fx.load_r_captures = _redirect
"""


def _run_day12_module(capture_dir: Path, plugin_dir: Path) -> dict[str, str]:
    """``tests/test_day12_r_captures.py`` in a subprocess with its capture directory
    redirected to ``capture_dir``; ``{test name: PASSED | FAILED | SKIPPED}``."""
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "e12r1_redirect.py").write_text(REDIRECT_PLUGIN, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(plugin_dir), str(SRC)])
    env["E12R1_CAPTURE_DIR"] = str(capture_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-p",
            "no:cacheprovider",
            "-p",
            "e12r1_redirect",
            "-rs",
            "tests/test_day12_r_captures.py",
        ],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
    found = re.findall(r"test_day12_r_captures\.py::(\w+) (PASSED|FAILED|SKIPPED)", proc.stdout)
    assert found, proc.stdout[-3000:] + proc.stderr[-3000:]
    return dict(found)


def test_fa_b1_with_the_vectors_absent_the_f13b_comparisons_run(tmp_path):
    """Lens 1 FA-B1's repro: the synthetic capture with ``asah_vectors.csv`` deleted and
    ``val.prob Slope`` moved by +1e-3. At ``2328e86`` every comparison read ``SKIPPED``
    (``r_captures_not_captured``). Here the three F13b comparisons that read the slope
    are ``FAILED``, the two that do not are ``PASSED``, and the F13 ones are ``SKIPPED``."""
    cap = tmp_path / "r"
    d12.write_synthetic_capture(cap)
    (cap / "asah_vectors.csv").unlink()
    path = cap / "rms_val_prob_f4.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["values"]["val.prob Slope"] += 1e-3
    path.write_text(json.dumps(doc), encoding="utf-8")
    out = _run_day12_module(cap, tmp_path / "plugin")
    for name in (
        "test_f13b_engine_slope_and_joint_intercept_equal_val_prob_slope_and_intercept",
        "test_f13b_every_compared_value_equals_the_capture",
        "test_the_fixtures_report_row_f13b_is_matched",
    ):
        assert out.get(name) == "FAILED", (name, out.get(name))
    for name in (
        "test_f13b_engine_intercept_in_the_large_equals_the_glm_offset_intercept",
        "test_f13b_capture_recorded_the_sha256_of_the_committed_f4_bytes_read_as_lf",
    ):
        assert out.get(name) == "PASSED", (name, out.get(name))
    for name in (
        "test_f13_engine_auroc_delong_variance_interval_and_paired_test_equal_proc_on_asah",
        "test_f13_capture_recorded_the_sha256_of_the_vectors_it_wrote",
        "test_the_fixtures_report_row_f13_is_matched",
    ):
        assert out.get(name) == "SKIPPED", (name, out.get(name))


# ------------------------------------------------------------------ FA-B2


def _status_on(monkeypatch, directory: Path) -> dict:
    monkeypatch.setattr(fx, "r_captures_dir", lambda: directory)
    return fx.r_captures_status()


def test_fa_b2_the_f13b_capture_alone_is_partial_and_names_each_row(tmp_path, monkeypatch):
    """Only ``rms_val_prob_f4.json`` (synthetic). At ``2328e86`` the line said "rows F13
    and F13b of the report compare them with the engine" while F13 was
    ``no_oracle_recorded``."""
    d12.write_synthetic_capture(tmp_path / "full")
    only = tmp_path / "only"
    only.mkdir()
    (only / "rms_val_prob_f4.json").write_bytes(
        (tmp_path / "full" / "rms_val_prob_f4.json").read_bytes()
    )
    st = _status_on(monkeypatch, only)
    assert "compare them with the engine" not in st["line"]
    assert st["status"] == "partial_see_rows_f13_f13b" == fx.R_CAPTURES_PARTIAL
    assert st["line"] == (
        "r-captures: partial_see_rows_f13_f13b - read: fixtures/r/rms_val_prob_f4.json; "
        "unreadable: none; absent: fixtures/r/proc_asah.json, fixtures/r/asah_vectors.csv; "
        "row F13 no_oracle_recorded, row F13b matched"
    )


def test_fa_b2_both_json_without_the_vectors_is_partial(tmp_path, monkeypatch):
    d12.write_synthetic_capture(tmp_path / "r")
    (tmp_path / "r" / "asah_vectors.csv").unlink()
    st = _status_on(monkeypatch, tmp_path / "r")
    assert st["status"] == "partial_see_rows_f13_f13b"
    assert st["line"].endswith(
        "absent: fixtures/r/asah_vectors.csv; row F13 no_oracle_recorded, row F13b matched"
    )


def test_fa_b2_an_unreadable_capture_is_not_called_not_captured(tmp_path, monkeypatch):
    """``proc_asah.json`` = ``{"values": `` alone. At ``2328e86`` the line said "no R
    capture is committed" while row F13 was ``not_matched`` (JSONDecodeError)."""
    (tmp_path / "proc_asah.json").write_text('{"values": ', encoding="utf-8")
    st = _status_on(monkeypatch, tmp_path)
    assert "no R capture is committed" not in st["line"]
    assert st["status"] == "partial_see_rows_f13_f13b"
    assert st["unreadable"] == ["fixtures/r/proc_asah.json"]
    assert st["line"] == (
        "r-captures: partial_see_rows_f13_f13b - read: none; unreadable: "
        "fixtures/r/proc_asah.json; absent: fixtures/r/rms_val_prob_f4.json, "
        "fixtures/r/asah_vectors.csv; row F13 not_matched, row F13b no_oracle_recorded"
    )


def test_fa_b2_all_three_present_and_all_absent(tmp_path, monkeypatch):
    d12.write_synthetic_capture(tmp_path / "r")
    st = _status_on(monkeypatch, tmp_path / "r")
    assert st["status"] == "present_compared_in_rows_f13_f13b" == fx.R_CAPTURES_PRESENT
    assert st["line"].endswith("absent: none; row F13 matched, row F13b matched")
    (tmp_path / "empty").mkdir()
    st = _status_on(monkeypatch, tmp_path / "empty")
    assert st["status"] == "r_captures_not_captured"
    assert st["line"].startswith(
        "r-captures: r_captures_not_captured - no R capture is committed "
        "(fixtures/r/proc_asah.json, fixtures/r/rms_val_prob_f4.json)"
    )


# ------------------------------------------------------------------ FA-B3


def _workflow_test():
    (fn,) = [getattr(d12, n) for n in dir(d12) if n.startswith("test_the_workflow_")]
    return fn


WORKFLOW = REPO / ".github" / "workflows" / "r-captures.yml"
W_MUTANTS = {
    "W1 job-level contents: write": (
        "  capture:\n",
        "  capture:\n    permissions:\n      contents: write\n",
    ),
    "W1b job-level write-all": ("  capture:\n", "  capture:\n    permissions: write-all\n"),
    "W2 checkout@main": ("actions/checkout@v4", "actions/checkout@main"),
    "W3 commit and push": (
        "run: Rscript fixtures/r/capture.R\n",
        "run: Rscript fixtures/r/capture.R && git add fixtures/r && git commit -m c && git push\n",
    ),
}


def _plant_workflow(root: Path, text: str) -> None:
    path = root / ".github" / "workflows" / "r-captures.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize("mutant", sorted(W_MUTANTS))
def test_fa_b3_each_lens_workflow_mutant_fails_the_workflow_test(tmp_path, monkeypatch, mutant):
    """Lens 1 FA-B3's W1-W3 (and W1 as the string ``write-all``), each planted in a copy of
    the committed workflow. At ``2328e86`` each passed the workflow test."""
    text = WORKFLOW.read_text(encoding="utf-8").replace("\r\n", "\n")
    old, new = W_MUTANTS[mutant]
    assert text.count(old) >= 1, mutant
    _plant_workflow(tmp_path, text.replace(old, new, 1))
    monkeypatch.setattr(d12, "REPO", tmp_path)
    with pytest.raises(AssertionError):
        _workflow_test()()


def test_fa_b3_control_the_committed_workflow_copied_passes(tmp_path, monkeypatch):
    _plant_workflow(tmp_path, WORKFLOW.read_text(encoding="utf-8"))
    monkeypatch.setattr(d12, "REPO", tmp_path)
    _workflow_test()()


# ------------------------------------------------------------------ RG-B2

CAPTURE_R = REPO / "fixtures" / "r" / "capture.R"
RG_B2_PROBES = (
    'x <- loadNamespace("ggplot2")',
    'y <- get("lm", envir = asNamespace("Hmisc"))',
    'system2("curl", "https://example.invalid")',
)


def _capture_r_test():
    (fn,) = [getattr(d12, n) for n in dir(d12) if n.startswith("test_capture_r_")]
    return fn


@pytest.mark.parametrize("probe", RG_B2_PROBES)
def test_rg_b2_the_lens_probe_lines_fail_the_capture_r_check(tmp_path, monkeypatch, probe):
    """Regression lens RG-B2's three lines, each appended alone to a copy of
    ``capture.R``. At ``2328e86`` all three together passed the "four packages only"
    test."""
    (tmp_path / "capture.R").write_text(
        CAPTURE_R.read_text(encoding="utf-8") + "\n" + probe + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(d12, "COMMITTED", tmp_path)
    with pytest.raises(AssertionError):
        _capture_r_test()()


def test_rg_b2_control_the_committed_capture_r_copied_passes(tmp_path, monkeypatch):
    (tmp_path / "capture.R").write_bytes(CAPTURE_R.read_bytes())
    monkeypatch.setattr(d12, "COMMITTED", tmp_path)
    _capture_r_test()()


# ------------------------------------------------------------------ RG-B1


def test_rg_b1_the_misspelt_skip_sentence_is_gone():
    """RG-B1: the module docstring said a misspelt reason "cannot pass as a skip"; the
    lens appended ``pytest.skip("r_capture_not_captured")`` and it passed. The sentence is
    deleted; the docstring now names the two gates the skip-reason test inspects."""
    doc = d12.__doc__ or ""
    assert "cannot pass as a skip" not in doc
    assert "It inspects those two gates only" in doc


# ------------------------------------------------------------------ FA-B4 / RG-N1


def test_fa_b4_the_refusal_fills_n_cases_only_when_absent():
    """Wilson 0.5 [0.3, 0.7], n 40, k 20, no flags: ``n_cases`` ``None`` with argument 4
    leaves with ``n_cases`` 4; ``n_cases`` 3 with argument 4 leaves with 3; ``n`` and ``k``
    unchanged; argument ``None`` raises. At ``2328e86`` the docstring said "the same
    estimate and counts" and its ordered list had no ``ValueError`` step."""
    doc = clustered_number.__doc__ or ""
    assert "the same estimate and counts" not in doc
    assert "``n_cases`` ``None`` raises ``ValueError``" in doc
    base = dict(est=0.5, ci_lo=0.3, ci_hi=0.7, method="wilson", n=40, k=20, flags=[])
    out = clustered_number(Number(**base), 4)
    assert (out.n_cases, out.n, out.k, out.est, out.method) == (4, 40, 20, 0.5, "none")
    assert out.not_estimable_reason == "fewer_than_five_cases"
    out3 = clustered_number(Number(**base, n_cases=3), 4)
    assert (out3.n_cases, out3.n, out3.k) == (3, 40, 20)
    with pytest.raises(ValueError, match="needs the case count of its cell"):
        clustered_number(Number(**base), None)


# ------------------------------------------------------------------ FA-N8


def test_fa_n8_an_installed_package_says_it_read_no_capture(monkeypatch):
    """``source_checkout_root`` -> ``None`` (an installed wheel). At ``2328e86`` F13 read
    "... are not both committed ...", which an installed package cannot know."""
    monkeypatch.setattr(fx, "source_checkout_root", lambda: None)
    rows = [fx.compare_row(r, {}) for r in fx.r_capture_rows()]
    for row in rows:
        assert row["status"] == "no_oracle_recorded"
        assert "not both committed" not in row["reason"]
        assert "is not committed" not in row["reason"]
        assert row["reason"] == (
            "[unverified until captured] an installed package reads no R capture: "
            "fixtures/r/ is read only when the package is <root>/src/proofpack and "
            "<root>/pyproject.toml names proofpack"
        )
    st = fx.r_captures_status()
    assert st["status"] == "r_captures_not_captured"
    assert "no R capture is committed" not in st["line"]
    assert "an installed package reads no R capture" in st["line"]


# ------------------------------------------------------------------ RG-N6


@pytest.mark.parametrize(
    ("written", "reason"),
    [
        ("NaN", "oracle value not finite (nan): val.prob Slope"),
        ("NA", "oracle value not a number (str): val.prob Slope"),
        ("Inf", "oracle value not finite (inf): val.prob Slope"),
    ],
)
def test_rg_n6_the_strings_capture_r_writes_for_non_finite_values(tmp_path, written, reason):
    """``val.prob Slope`` written as each string ``capture.R``'s ``json_number`` writes
    for a value that is not finite: the report row is ``not_matched`` with the reason
    named. At ``2328e86`` capture.R's comment said such a value "can never read as a
    number"; the report reads it with ``float()``."""
    text = CAPTURE_R.read_text(encoding="utf-8")
    assert "can never read as a number" not in text
    assert "passes a string to float()" in text
    d12.write_synthetic_capture(tmp_path / "r")
    path = tmp_path / "r" / "rms_val_prob_f4.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["values"]["val.prob Slope"] = written
    path.write_text(json.dumps(doc), encoding="utf-8")
    row = fx.compare_row(fx.r_capture_rows(fx.load_r_captures(tmp_path / "r"))[1], {})
    assert row["status"] == "not_matched"
    assert reason in row["reason"]
