"""Build day 12 (5 October 2026), lane E: F13 and F13b - the engine against the R captures.

``fixtures/r/capture.R`` (run by ``.github/workflows/r-captures.yml``) writes
``fixtures/r/proc_asah.json``, ``fixtures/r/rms_val_prob_f4.json`` and the F13 input
``fixtures/r/asah_vectors.csv``. None of the three is committed on build day 12.

**The comparisons** (the first eight tests) each pass through one of two gates (E12
repair 1, lens 1 FA-B1 / RG-N3: the build's single gate skipped all seven comparisons
unless all three files were read, so a committed F13b capture without the vectors file
compared nothing). :func:`_f13_or_skip` reads ``fixtures/r/`` and skips with
:func:`f13_skip_reason` when ``proc_asah.json`` or ``asah_vectors.csv`` was not read and
neither is unreadable; :func:`_f13b_or_skip` skips with :data:`F13B_SKIP` when
``rms_val_prob_f4.json`` was not read and is not unreadable. Otherwise the test compares
the engine with the files, each value with the tolerance written beside it in
:data:`F13_TOL` / :data:`F13B_TOL`.
``tests/test_e12_repair1.py::test_fa_b1_with_the_vectors_absent_the_f13b_comparisons_run``
runs this module with the F13b capture present, the vectors absent and ``val.prob Slope``
moved by 1e-3, and reads three F13b comparisons ``FAILED``.

**The skip reasons.** :func:`test_the_skip_reasons_are_the_typed_strings` asserts the
strings the two gates skip with, on an empty directory and on a capture without its
vectors file, and that neither gate skips when a file it needs is unreadable (E12 repair
2). It inspects those two gates only, not any other skip in this module; the
r-captures workflow's ``compare`` job runs ``grep -q "SKIPPED"`` on the output of
``pytest -m day12 -rs`` and its step exits 1 when the word is there (the step's two shell
lines were run in Git Bash in E12 repair 1 on an output holding a ``SKIPPED`` line: exit
1; the workflow itself has not run).

**The structure tests** write a synthetic capture into ``tmp_path`` in the shape
``capture.R`` writes (the same keys, the comment line and column order of the CSV, numbers
written with 17 significant digits) and run it through the same loader
(``fixtures.load_r_captures``), the same comparison (:func:`_compare`) and the same report
rows (``fixtures.r_capture_rows``), so the comparison code runs today. The synthetic F13
values are computed here from DeLong 1988's placement definition by direct O(m n) sums,
not by the engine's Sun and Xu midrank code; the synthetic F13b values are the statsmodels
``fit(tol=1e-10)`` and scikit-learn figures already recorded in
``fixtures/f4_expected.json``.

**sha256 decision.** The F4 capture records the sha256 of the bytes R read; the tests and
the report compare it with the sha256 of the committed ``fixtures/f4_calibration.csv``
with every CRLF read as LF (``fixtures.lf_sha256``). The index holds the file as LF and the
Linux runner checks it out as LF; a Windows checkout under ``core.autocrlf=true`` may hold
CRLF, which is the same committed content.

**Which intercept.** ``val.prob``'s ``Intercept`` is compared with the engine's
``intercept`` (the joint model ``a + b logit(p)``) and the engine's ``intercept_large``
(slope fixed at 1) with the ``glm(y ~ offset(qlogis(p)))`` intercept; the test names say
so. That ``val.prob`` fits the joint model is [unverified] (rms source not fetched); the
capture's ``glm joint`` values are the same model by ``glm``, compared alongside.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from proofpack import fixtures as fx

pytestmark = pytest.mark.day12

REPO = Path(__file__).resolve().parent.parent
COMMITTED = REPO / "fixtures" / "r"
DRIFT = REPO / "scripts" / "r_capture_drift.py"
Z975 = 1.959963984540054

#: Per field: (absolute tolerance, relative tolerance or None). A value passes when its
#: absolute difference is within the absolute tolerance and, where a relative one is
#: given, also within ``rel * |oracle|``. Counts are compared exactly (tolerance 0).
F13_TOL: dict[str, tuple[float, float | None]] = {
    **{
        f"{s} {k}": tol
        for s in ("s100b", "ndka")
        for k, tol in (
            ("auc", (1e-6, None)),
            ("var_delong", (1e-6, 1e-6)),  # the variance is about 3e-3: relative as well
            ("ci_delong_lo", (1e-6, None)),
            ("ci_delong_hi", (1e-6, None)),
            ("n_cases", (0.0, None)),
            ("n_controls", (0.0, None)),
        )
    },
    "roc.test statistic": (1e-6, None),
    "roc.test p.value": (1e-6, None),
    "roc.test estimate 1": (1e-6, None),
    "roc.test estimate 2": (1e-6, None),
    "roc.test conf.int lo": (1e-6, None),  # compared only when the capture carries it
    "roc.test conf.int hi": (1e-6, None),
}
F13B_TOL: dict[str, tuple[float, float | None]] = {name: (1e-6, None) for name in fx.F13B_NAMES}


# ------------------------------------------------------------------ loading


F13_NEEDS = (fx.R_CAPTURE_FILES[0], fx.R_VECTORS_FILE)
F13B_NEEDS = (fx.R_CAPTURE_FILES[1],)
#: The skip reason of :func:`_f13b_or_skip`.
F13B_SKIP = f"{fx.R_CAPTURES_NOT_CAPTURED}: F13b (absent: {fx.R_CAPTURE_FILES[1]})"


def f13_skip_reason(absent: list[str]) -> str:
    """The skip reason of :func:`_f13_or_skip`, naming the files not read."""
    return f"{fx.R_CAPTURES_NOT_CAPTURED}: F13 (absent: {', '.join(absent)})"


def _gate(directory: Path, needs: tuple[str, ...]) -> tuple[fx.RCaptures, list[str]]:
    """The captures in ``directory`` and the files of ``needs`` neither read nor
    unreadable (an unreadable file does not skip: the comparison then fails on it)."""
    caps = fx.load_r_captures(directory)
    bad = {f for f, _ in caps.unreadable}
    if bad & set(needs):
        return caps, []
    return caps, [f for f in needs if f not in caps.present]


def _f13_or_skip(directory: Path = COMMITTED) -> fx.RCaptures:
    """Skip with :func:`f13_skip_reason` unless ``proc_asah.json`` and ``asah_vectors.csv``
    were both read (or one of them is unreadable)."""
    caps, absent = _gate(directory, F13_NEEDS)
    if absent:
        pytest.skip(f13_skip_reason(absent))
    return caps


def _f13b_or_skip(directory: Path = COMMITTED) -> fx.RCaptures:
    """Skip with :data:`F13B_SKIP` unless ``rms_val_prob_f4.json`` was read (or is
    unreadable). F13b needs no vectors file."""
    caps, absent = _gate(directory, F13B_NEEDS)
    if absent:
        pytest.skip(F13B_SKIP)
    return caps


def _within(engine: float, oracle: float, tol: tuple[float, float | None]) -> bool:
    absolute, relative = tol
    d = abs(engine - oracle)
    return d <= absolute and (relative is None or d <= relative * abs(oracle))


def _compare(engine: dict[str, float], oracle: dict, tol: dict) -> list[tuple]:
    """``(name, engine, oracle, abs difference, within)`` for every name in ``tol`` that the
    oracle carries; a name in ``tol`` other than the conf.int pair that the oracle lacks
    is a failure, not a skip."""
    rows = []
    for name, t in tol.items():
        if name not in oracle and name in fx.F13_OPTIONAL_NAMES:
            continue
        o = oracle.get(name)
        e = engine.get(name)
        comparable = e is not None and _num(o) and math.isfinite(float(o))
        diff = abs(float(e) - float(o)) if comparable else None
        ok = comparable and _within(float(e), float(o), t)
        rows.append((name, e, o, diff, ok))
    return rows


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _f13_rows(caps: fx.RCaptures) -> list[tuple]:
    assert caps.vectors is not None and caps.proc is not None
    engine = fx.f13_engine_values(caps.vectors, with_conf_int=True)
    return _compare(engine, caps.proc["values"], F13_TOL)


def _f13b_rows(caps: fx.RCaptures, names: tuple[str, ...] = fx.F13B_NAMES) -> list[tuple]:
    assert caps.valprob is not None
    engine = fx.f13b_engine_values()
    return _compare(engine, caps.valprob["values"], {n: F13B_TOL[n] for n in names})


def _failures(rows: list[tuple]) -> list[tuple]:
    return [r for r in rows if not r[4]]


# --------------------------------------------- the comparison (skips while absent)


def test_f13_engine_auroc_delong_variance_interval_and_paired_test_equal_proc_on_asah():
    caps = _f13_or_skip()
    rows = _f13_rows(caps)
    assert len(rows) >= len(fx.F13_NAMES)
    assert _failures(rows) == []


def test_f13b_engine_slope_and_joint_intercept_equal_val_prob_slope_and_intercept():
    caps = _f13b_or_skip()
    rows = _f13b_rows(caps, ("val.prob Slope", "val.prob Intercept"))
    assert _failures(rows) == []


def test_f13b_engine_intercept_in_the_large_equals_the_glm_offset_intercept():
    caps = _f13b_or_skip()
    rows = _f13b_rows(caps, ("glm offset (Intercept)", "glm offset tight (Intercept)"))
    assert _failures(rows) == []


def test_f13b_every_compared_value_equals_the_capture():
    caps = _f13b_or_skip()
    assert _failures(_f13b_rows(caps)) == []


def test_f13b_capture_recorded_the_sha256_of_the_committed_f4_bytes_read_as_lf():
    caps = _f13b_or_skip()
    assert caps.valprob is not None
    committed = (REPO / "fixtures" / "f4_calibration.csv").read_bytes().replace(b"\r\n", b"\n")
    assert caps.valprob["input"]["sha256"] == hashlib.sha256(committed).hexdigest()


def test_f13_capture_recorded_the_sha256_of_the_vectors_it_wrote():
    caps = _f13_or_skip()
    assert caps.proc is not None
    assert caps.proc["input"]["vectors_sha256"] == caps.vectors_sha256


def _report_row(rid: str) -> dict:
    rep = fx.run_fixtures(doctor=False)
    fx.validate_report(rep)
    return next(r for r in rep["rows"] if r["id"] == rid)


def test_the_fixtures_report_row_f13_is_matched():
    _f13_or_skip()
    row = _report_row("F13")
    assert row["status"] == "matched", row["reason"]


def test_the_fixtures_report_row_f13b_is_matched():
    _f13b_or_skip()
    row = _report_row("F13b")
    assert row["status"] == "matched", row["reason"]


def test_f4_expected_r_rms_val_prob_is_pending_until_a_capture_is_committed():
    """``f4_expected.json`` says ``[pending]`` while no F4 capture is committed (tracked by
    git). When one is committed the orchestrator replaces the entry with the capture's
    figures; this test then asks for that. It never skips, so the workflow's no-skip rule
    holds; the workflow's compare job copies in a capture git does not track."""
    exp = json.loads((REPO / "fixtures" / "f4_expected.json").read_text(encoding="utf-8"))
    try:
        tracked = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "fixtures/r/rms_val_prob_f4.json"],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        tracked = ""
    if tracked:
        assert exp["r_rms_val_prob"]["status"] != "[pending]"
    else:
        assert exp["r_rms_val_prob"]["status"] == "[pending]"


# ------------------------------------------------------------------ the skip reason


def _no_skip(gate, directory: Path) -> fx.RCaptures:
    """``gate(directory)``; a skip raised by the gate fails the calling test (E12 repair 2,
    lens 2 FA-B1: a ``pytest.skip`` raised inside a test reads as that test skipped)."""
    try:
        return gate(directory)
    except pytest.skip.Exception as exc:
        pytest.fail(f"the gate skipped where a file it needs is unreadable: {exc}")


def test_the_skip_reasons_are_the_typed_strings(tmp_path):
    """Empty directory: F13 skips naming both files, F13b naming its capture. The synthetic
    capture less ``asah_vectors.csv``: F13 skips naming the vectors file, F13b does not
    skip. Then ``proc_asah.json`` = ``{"values": `` (vectors still absent): :func:`_gate`
    returns no absent file for F13, and ``_f13_or_skip`` returns; then
    ``rms_val_prob_f4.json`` = ``{"values": ``: the same for F13b. Those four calls are
    asserted directly or through :func:`_no_skip`, so a gate that skips there fails this
    test (E12 repair 2, lens 2 FA-B1 / RG-N1;
    ``tests/test_e12_repair2.py::test_fa_b1_each_lens_mutant_of_gate_fails_the_skip_reason_test``
    plants the two mutants and reads this test fail on each)."""
    assert fx.R_CAPTURES_NOT_CAPTURED == "r_captures_not_captured"
    with pytest.raises(pytest.skip.Exception) as info:
        _f13_or_skip(tmp_path)
    assert str(info.value) == (
        "r_captures_not_captured: F13 (absent: fixtures/r/proc_asah.json, "
        "fixtures/r/asah_vectors.csv)"
    )
    with pytest.raises(pytest.skip.Exception) as info:
        _f13b_or_skip(tmp_path)
    assert (
        str(info.value) == "r_captures_not_captured: F13b (absent: fixtures/r/rms_val_prob_f4.json)"
    )
    write_synthetic_capture(tmp_path / "r")
    (tmp_path / "r" / "asah_vectors.csv").unlink()
    with pytest.raises(pytest.skip.Exception) as info:
        _f13_or_skip(tmp_path / "r")
    assert str(info.value) == "r_captures_not_captured: F13 (absent: fixtures/r/asah_vectors.csv)"
    assert _f13b_or_skip(tmp_path / "r").valprob is not None
    (tmp_path / "r" / "proc_asah.json").write_text('{"values": ', encoding="utf-8")
    assert _gate(tmp_path / "r", F13_NEEDS)[1] == []
    assert _no_skip(_f13_or_skip, tmp_path / "r").unreadable == (
        ("fixtures/r/proc_asah.json", "JSONDecodeError"),
    )
    (tmp_path / "r" / "rms_val_prob_f4.json").write_text('{"values": ', encoding="utf-8")
    assert _gate(tmp_path / "r", F13B_NEEDS)[1] == []
    caps = _no_skip(_f13b_or_skip, tmp_path / "r")
    assert caps.valprob is None
    assert ("fixtures/r/rms_val_prob_f4.json", "JSONDecodeError") in caps.unreadable


def test_absent_captures_leave_f13_and_f13b_no_oracle_recorded_with_the_unverified_reason(
    tmp_path,
):
    caps = fx.load_r_captures(tmp_path)
    assert caps.present == () and caps.unreadable == ()
    f13, f13b = (fx.compare_row(r, {}) for r in fx.r_capture_rows(caps))
    assert f13["status"] == f13b["status"] == "no_oracle_recorded"
    assert (
        f13["reason"].startswith(fx.F13_ABSENT) and "[unverified until captured]" in f13["reason"]
    )
    assert f13b["reason"] == fx.F13B_ABSENT
    assert f13["oracle_source"] is None and f13["n_values_compared"] == 0


# ----------------------------------------------- structure: a synthetic capture today


def _placements_delong(s: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """DeLong 1988 by definition: psi(x, z) = 1, 1/2, 0 for x > z, x = z, x < z;
    V10_i = mean_j psi(X_i, Z_j) over the controls, V01_j = mean_i psi(X_i, Z_j)."""
    x, z = s[y], s[~y]
    psi = (x[:, None] > z[None, :]) + 0.5 * (x[:, None] == z[None, :])
    return float(psi.mean()), psi.mean(axis=1), psi.mean(axis=0)


def _synthetic_vectors() -> tuple[list[str], dict[str, np.ndarray]]:
    rng = np.random.default_rng(20261005)
    y = rng.random(80) < 0.4
    s100b = np.round(np.where(y, rng.gamma(2.0, 0.25, 80), rng.gamma(1.5, 0.2, 80)), 2)
    ndka = np.round(np.where(y, rng.normal(12, 5, 80), rng.normal(10, 5, 80)), 1)
    lines = [
        "# aSAH from the R package pROC (data(aSAH)), written by fixtures/r/capture.R in "
        "pROC's row order; y = 1 when outcome is Poor (cases), 0 when Good (controls)",
        "row,outcome,y,s100b,ndka",
    ]
    for i in range(80):
        outcome = "Poor" if y[i] else "Good"
        lines.append(f"{i + 1},{outcome},{int(y[i])},{float(s100b[i])!r},{float(ndka[i])!r}")
    return lines, {"y": y, "s100b": s100b, "ndka": ndka}


def _synthetic_proc_values(v: dict[str, np.ndarray]) -> dict[str, float]:
    y = v["y"]
    m, n = int(y.sum()), int((~y).sum())
    out: dict[str, float] = {}
    comps = {}
    for score in ("s100b", "ndka"):
        auc, v10, v01 = _placements_delong(v[score], y)
        var = float(np.var(v10, ddof=1) / m + np.var(v01, ddof=1) / n)
        comps[score] = (auc, v10, v01)
        se = math.sqrt(var)
        out.update(
            {
                f"{score} auc": auc,
                f"{score} var_delong": var,
                f"{score} ci_delong_lo": max(0.0, auc - Z975 * se),
                f"{score} ci_delong_mid": auc,
                f"{score} ci_delong_hi": min(1.0, auc + Z975 * se),
                f"{score} n_cases": m,
                f"{score} n_controls": n,
            }
        )
    (a1, x1, z1), (a2, x2, z2) = comps["s100b"], comps["ndka"]
    var_diff = float(np.var(x1 - x2, ddof=1) / m + np.var(z1 - z2, ddof=1) / n)
    zstat = (a1 - a2) / math.sqrt(var_diff)
    out.update(
        {
            "roc.test statistic": zstat,
            "roc.test p.value": math.erfc(abs(zstat) / math.sqrt(2.0)),
            "roc.test estimate 1": a1,
            "roc.test estimate 2": a2,
        }
    )
    return out


def _synthetic_valprob_values() -> dict[str, float]:
    exp = json.loads((REPO / "fixtures" / "f4_expected.json").read_text(encoding="utf-8"))
    off, joint = exp["statsmodels_glm_binomial_offset"], exp["statsmodels_glm_binomial_joint"]
    p = np.r_[np.arange(1, 20) * 0.05, 0.99]
    y = np.array([0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1], dtype=bool)
    c_roc, _, _ = _placements_delong(p, y)
    return {
        "val.prob Dxy": 2 * c_roc - 1,
        "val.prob C (ROC)": c_roc,
        "val.prob Brier": exp["sklearn_brier"]["brier"],
        "val.prob Intercept": joint["intercept"],
        "val.prob Slope": joint["slope"],
        "glm joint (Intercept)": joint["default_fit_intercept"],
        "glm joint logit_p": joint["default_fit_slope"],
        "glm joint (Intercept) se": joint["default_fit_se_intercept"],
        "glm joint logit_p se": joint["default_fit_se_slope"],
        "glm offset (Intercept)": off["default_fit_intercept_large"],
        "glm offset (Intercept) se": off["default_fit_se"],
        "glm joint tight (Intercept)": joint["intercept"],
        "glm joint tight logit_p": joint["slope"],
        "glm joint tight (Intercept) se": joint["se_intercept"],
        "glm joint tight logit_p se": joint["se_slope"],
        "glm offset tight (Intercept)": off["intercept_large"],
        "glm offset tight (Intercept) se": off["se"],
    }


def _meta() -> dict:
    return {
        "script": "fixtures/r/capture.R",
        "r_version_string": "R version 0.0.0 (synthetic, written by the test)",
        "session_info": "synthetic",
        "packages": {"pROC": "0", "rms": "0", "jsonlite": "0"},
        "repos": {"CRAN": "synthetic"},
        "run_date_utc": "2026-10-05T00:00:00Z",
        "github": {"run_id": None, "sha": None},
    }


def _r_json(doc: dict) -> str:
    """JSON with every float at 17 significant digits, as capture.R's json_number writes."""

    def fmt(x):
        if isinstance(x, float):
            return float(f"{x:.17g}")
        if isinstance(x, dict):
            return {k: fmt(v) for k, v in x.items()}
        if isinstance(x, list):
            return [fmt(v) for v in x]
        return x

    return json.dumps(fmt(doc), indent=2) + "\n"


def write_synthetic_capture(directory: Path) -> dict[str, np.ndarray]:
    directory.mkdir(parents=True, exist_ok=True)
    lines, vectors = _synthetic_vectors()
    csv_bytes = ("\n".join(lines) + "\n").encode("utf-8")
    (directory / "asah_vectors.csv").write_bytes(csv_bytes)
    proc = {
        "schema": fx.R_CAPTURE_SCHEMA,
        "fixture": "F13",
        "what": "synthetic capture written by tests/test_day12_r_captures.py",
        "input": {
            "dataset": "synthetic",
            "n_rows": len(lines) - 2,
            "levels": ["Good", "Poor"],
            "controls": "Good",
            "cases": "Poor",
            "direction": "<",
            "y_mapping": {"Good": 0, "Poor": 1},
            "vectors_file": "fixtures/r/asah_vectors.csv",
            "vectors_sha256": hashlib.sha256(csv_bytes).hexdigest(),
            "sha256_method": "hashlib",
        },
        "values": _synthetic_proc_values(vectors),
        "meta": _meta(),
    }
    f4 = (REPO / "fixtures" / "f4_calibration.csv").read_bytes().replace(b"\r\n", b"\n")
    valprob = {
        "schema": fx.R_CAPTURE_SCHEMA,
        "fixture": "F13b",
        "what": "synthetic capture written by tests/test_day12_r_captures.py",
        "input": {
            "file": "fixtures/f4_calibration.csv",
            "bytes": len(f4),
            "sha256": hashlib.sha256(f4).hexdigest(),
            "sha256_method": "hashlib",
            "n_rows": 20,
            "events": 12,
        },
        "values": _synthetic_valprob_values(),
        "fits": {"glm joint tight": {"iterations": 7, "converged": True, "epsilon": 1e-14}},
        "meta": _meta(),
    }
    (directory / "proc_asah.json").write_text(_r_json(proc), encoding="utf-8")
    (directory / "rms_val_prob_f4.json").write_text(_r_json(valprob), encoding="utf-8")
    return vectors


@pytest.fixture
def synthetic(tmp_path) -> Path:
    write_synthetic_capture(tmp_path / "r")
    return tmp_path / "r"


def test_structure_the_loader_reads_the_three_files_in_the_shape_capture_r_writes(synthetic):
    caps = fx.load_r_captures(synthetic)
    assert caps.present == (*fx.R_CAPTURE_FILES, fx.R_VECTORS_FILE)
    assert caps.unreadable == ()
    assert caps.vectors is not None and len(caps.vectors["y"]) == 80
    assert _f13_or_skip(synthetic) is not None and _f13b_or_skip(synthetic) is not None


def test_structure_the_engine_equals_the_definition_delong_on_the_synthetic_vectors(synthetic):
    caps = fx.load_r_captures(synthetic)
    rows = _f13_rows(caps)
    assert [r[0] for r in rows] == [n for n in F13_TOL if n not in fx.F13_OPTIONAL_NAMES]
    assert _failures(rows) == []
    worst = max(r[3] for r in rows)
    assert worst < 1e-12, worst  # midrank (Sun and Xu) against the O(m n) definition


def test_structure_the_engine_equals_the_recorded_f4_oracles_through_the_f13b_comparison(
    synthetic,
):
    caps = fx.load_r_captures(synthetic)
    assert _failures(_f13b_rows(caps)) == []


def test_structure_the_report_rows_are_matched_and_fit_the_schema(synthetic):
    caps = fx.load_r_captures(synthetic)
    rep = fx.run_fixtures(rows=fx.r_capture_rows(caps), doctor=False)
    fx.validate_report(rep)
    rows = {r["id"]: r for r in rep["rows"]}
    assert rows["F13"]["status"] == "matched" and rows["F13b"]["status"] == "matched"
    assert rows["F13"]["n_values_compared"] == len(fx.F13_NAMES)
    assert rows["F13b"]["n_values_compared"] == len(fx.F13B_NAMES)
    assert rows["F13"]["tolerance"]["value"] == 1e-6
    assert rows["F13"]["oracle_source"]["kind"] == "captured_library"
    assert rows["F13"]["max_abs_deviation"] < 1e-12
    assert rep["exit_code"] == 0


def _edit(path: Path, fn) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_structure_a_value_moved_by_2e_6_is_not_matched_and_exits_6(synthetic):
    def move(doc):
        doc["values"]["s100b var_delong"] += 2e-6

    _edit(synthetic / "proc_asah.json", move)
    caps = fx.load_r_captures(synthetic)
    assert [r[0] for r in _failures(_f13_rows(caps))] == ["s100b var_delong"]
    rep = fx.run_fixtures(rows=fx.r_capture_rows(caps), doctor=False)
    row = next(r for r in rep["rows"] if r["id"] == "F13")
    assert row["status"] == "not_matched"
    assert row["reason"] == "outside tolerance: s100b var_delong"
    assert row["max_abs_deviation"] == pytest.approx(2e-6, rel=1e-6)
    assert rep["exit_code"] == 6


def test_structure_a_relative_variance_error_below_1e_6_absolute_still_fails(synthetic):
    """The variance is near 3e-3; 5e-7 absolute is a relative 1.6e-4, outside the
    relative 1e-6 the pytest comparison adds (the report row applies 1e-6 absolute)."""

    def move(doc):
        doc["values"]["ndka var_delong"] += 5e-7

    _edit(synthetic / "proc_asah.json", move)
    caps = fx.load_r_captures(synthetic)
    assert [r[0] for r in _failures(_f13_rows(caps))] == ["ndka var_delong"]


def test_structure_a_missing_value_is_not_matched(synthetic):
    _edit(synthetic / "rms_val_prob_f4.json", lambda d: d["values"].pop("val.prob Slope"))
    caps = fx.load_r_captures(synthetic)
    assert [r[0] for r in _failures(_f13b_rows(caps))] == ["val.prob Slope"]
    row = fx.compare_row(fx.r_capture_rows(caps)[1], {})
    assert row["status"] == "not_matched"
    assert "oracle value missing: val.prob Slope" in row["reason"]


def test_structure_a_different_f4_sha256_is_an_input_mismatch(synthetic):
    _edit(synthetic / "rms_val_prob_f4.json", lambda d: d["input"].update(sha256="0" * 64))
    row = fx.compare_row(fx.r_capture_rows(fx.load_r_captures(synthetic))[1], {})
    assert row["status"] == "not_matched"
    assert row["reason"].startswith("r_capture_input_mismatch: f4_calibration.csv sha256 ")


def test_structure_edited_vectors_are_an_input_mismatch(synthetic):
    path = synthetic / "asah_vectors.csv"
    path.write_bytes(path.read_bytes() + b"81,Good,0,0.5,9.5\n")
    row = fx.compare_row(fx.r_capture_rows(fx.load_r_captures(synthetic))[0], {})
    assert row["status"] == "not_matched"
    assert row["reason"].startswith("r_capture_input_mismatch: asah_vectors.csv sha256 ")


def test_structure_crlf_vectors_read_as_the_same_bytes(synthetic):
    path = synthetic / "asah_vectors.csv"
    lf = fx.load_r_captures(synthetic).vectors_sha256
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    caps = fx.load_r_captures(synthetic)
    assert caps.vectors_sha256 == lf
    assert fx.compare_row(fx.r_capture_rows(caps)[0], {})["status"] == "matched"


def test_structure_a_capture_without_its_vectors_stays_no_oracle_recorded(synthetic):
    (synthetic / "asah_vectors.csv").unlink()
    caps = fx.load_r_captures(synthetic)
    row = fx.compare_row(fx.r_capture_rows(caps)[0], {})
    assert row["status"] == "no_oracle_recorded"
    assert row["reason"] == f"{fx.F13_ABSENT} (absent: {fx.R_VECTORS_FILE})"
    assert fx.compare_row(fx.r_capture_rows(caps)[1], {})["status"] == "matched"


def test_structure_an_unreadable_capture_is_not_matched(synthetic):
    (synthetic / "proc_asah.json").write_text('{"values": ', encoding="utf-8")
    row = fx.compare_row(fx.r_capture_rows(fx.load_r_captures(synthetic))[0], {})
    assert row["status"] == "not_matched"
    assert row["reason"] == "oracle_file_unreadable: fixtures/r/proc_asah.json (JSONDecodeError)"


def test_structure_a_capture_of_another_fixture_is_an_input_mismatch(synthetic):
    _edit(synthetic / "proc_asah.json", lambda d: d.update(fixture="F13b"))
    row = fx.compare_row(fx.r_capture_rows(fx.load_r_captures(synthetic))[0], {})
    assert row["reason"].startswith("r_capture_input_mismatch: schema ")


def test_structure_r_captures_status_names_the_present_files(synthetic, monkeypatch):
    monkeypatch.setattr(fx, "r_captures_dir", lambda: synthetic)
    status = fx.r_captures_status()
    assert status["status"] == fx.R_CAPTURES_PRESENT
    assert status["present"] == list(fx.R_CAPTURE_FILES)
    monkeypatch.setattr(fx, "r_captures_dir", lambda: synthetic.parent / "empty")
    assert fx.r_captures_status()["status"] == fx.R_CAPTURES_NOT_CAPTURED


def test_an_installed_wheel_reads_no_capture(monkeypatch):
    monkeypatch.setattr(fx, "source_checkout_root", lambda: None)
    caps = fx.load_r_captures()
    assert caps.directory is None and caps.present == ()


# ------------------------------------------------------------------ the drift check


def _drift(committed: Path, fresh: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(DRIFT), "--committed", str(committed), "--fresh", str(fresh)],
        capture_output=True,
        text=True,
    )


def test_drift_nothing_committed_exits_0(tmp_path, synthetic):
    (tmp_path / "none").mkdir()
    proc = _drift(tmp_path / "none", synthetic)
    assert proc.returncode == 0, proc.stdout
    assert "no capture is committed; nothing to compare" in proc.stdout


def test_drift_identical_but_for_meta_exits_0(tmp_path, synthetic):
    write_synthetic_capture(tmp_path / "fresh")
    _edit(tmp_path / "fresh" / "proc_asah.json", lambda d: d["meta"].update(run_date_utc="x"))
    proc = _drift(synthetic, tmp_path / "fresh")
    assert proc.returncode == 0, proc.stdout
    assert "0 difference(s) above 1e-12" in proc.stdout


@pytest.mark.parametrize(("delta", "rc"), [(5e-13, 0), (2e-12, 1)])
def test_drift_fails_above_1e_12(tmp_path, synthetic, delta, rc):
    write_synthetic_capture(tmp_path / "fresh")

    def move(doc):
        doc["values"]["val.prob Slope"] += delta

    _edit(tmp_path / "fresh" / "rms_val_prob_f4.json", move)
    proc = _drift(synthetic, tmp_path / "fresh")
    assert proc.returncode == rc, proc.stdout
    if rc:
        assert "rms_val_prob_f4.json.values.val.prob Slope" in proc.stdout


def test_drift_a_committed_file_the_fresh_run_did_not_write_fails(tmp_path, synthetic):
    write_synthetic_capture(tmp_path / "fresh")
    (tmp_path / "fresh" / "asah_vectors.csv").unlink()
    proc = _drift(synthetic, tmp_path / "fresh")
    assert proc.returncode == 1
    assert "asah_vectors.csv: committed, and the fresh run did not write it" in proc.stdout


def test_drift_changed_vectors_fail_and_crlf_does_not(tmp_path, synthetic):
    write_synthetic_capture(tmp_path / "fresh")
    path = tmp_path / "fresh" / "asah_vectors.csv"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert _drift(synthetic, tmp_path / "fresh").returncode == 0
    path.write_bytes(path.read_bytes() + b"81,Good,0,0.5,9.5\r\n")
    assert _drift(synthetic, tmp_path / "fresh").returncode == 1


def test_drift_a_new_key_is_a_difference(tmp_path, synthetic):
    write_synthetic_capture(tmp_path / "fresh")
    _edit(tmp_path / "fresh" / "proc_asah.json", lambda d: d["values"].update({"extra": 1.0}))
    proc = _drift(synthetic, tmp_path / "fresh")
    assert proc.returncode == 1 and "proc_asah.json.values.extra: fresh only" in proc.stdout


# ------------------------------------------------------------------ the R script and the job


#: Package names :func:`capture_r_package_names` may find in ``capture.R``.
CAPTURE_R_PACKAGES = {"pROC", "rms", "jsonlite", "stats", "utils", "tools"}
#: The patterns :func:`capture_r_package_names` searches with (E12 repair 1, RG-B2).
CAPTURE_R_PACKAGE_PATTERNS = (
    r"\b(?:library|require)\(\s*[\"']?([\w.]+)",
    r"\b(?:requireNamespace|loadNamespace|asNamespace|getNamespace|attachNamespace)"
    r"\(\s*[\"']([\w.]+)",
    r"\bpackage\s*=\s*[\"']([\w.]+)",
    r"\b([\w.]+):::?",
)
#: Calls that run a command, fetch a URL or install a package (searched for by the
#: capture.R test below).
CAPTURE_R_COMMAND_CALL = r"\b(system2|system|shell|pipe|download\.file|url|install\.packages)\s*\("


def capture_r_package_names(text: str) -> set[str]:
    """Every package name the patterns of :data:`CAPTURE_R_PACKAGE_PATTERNS` find."""
    return {m for pat in CAPTURE_R_PACKAGE_PATTERNS for m in re.findall(pat, text)}


def test_capture_r_names_the_three_files_and_its_patterns_find_only_listed_names():
    """What it inspects (E12 repair 1, lens 1 RG-B2; renamed in E12 repair 2, lens 2 FA-B3
    / RG-B2, whose lines passed a name that said "calls only listed packages and
    commands"). Each of the three file names appears quoted in the text; ``library()``
    names exactly pROC, rms and jsonlite; the package names found by
    :data:`CAPTURE_R_PACKAGE_PATTERNS` (``library`` / ``require``, the ``*Namespace``
    calls, ``package =``, ``pkg::`` and ``pkg:::``) are within :data:`CAPTURE_R_PACKAGES`;
    the calls matched by :data:`CAPTURE_R_COMMAND_CALL` are exactly one,
    ``system2("sha256sum", ...)``. Lines that run a command or fetch a URL and that these
    patterns do not match: ``sh <- system2; sh("curl", "https://example.invalid")``,
    ``source("https://...")``, ``readLines("https://...")``,
    ``jsonlite::fromJSON("https://...")``, ``get("system")("curl ...")``,
    ``do.call("system2", ...)`` and ``eval(parse(text = paste0("sys", "tem(...)")))``.
    ``tests/test_e12_repair2.py::test_fa_b3_lens_2_capture_r_lines_pass_this_check`` appends
    each of those seven lines and reads this test pass;
    ``tests/test_e12_repair1.py::test_rg_b2_the_lens_probe_lines_fail_the_capture_r_check``
    appends lens 1's three lines and reads it fail."""
    text = (COMMITTED / "capture.R").read_text(encoding="utf-8")
    for rel in (*fx.R_CAPTURE_FILES, fx.R_VECTORS_FILE):
        assert f'"{Path(rel).name}"' in text, rel
    libs = set(re.findall(r"library\((\w+)\)", text))
    assert libs == {"pROC", "rms", "jsonlite"}
    found = capture_r_package_names(text)
    assert found <= CAPTURE_R_PACKAGES, found - CAPTURE_R_PACKAGES
    commands = [
        (m.group(1), text[m.end() : m.end() + 12])
        for m in re.finditer(CAPTURE_R_COMMAND_CALL, text)
    ]
    assert commands == [("system2", '"sha256sum",')], commands
    assert "direction = DIRECTION" in text and 'LEVELS <- c("Good", "Poor")' in text
    assert 'method = "delong"' in text and "paired = TRUE" in text
    assert "pl = FALSE" in text and 'sprintf("%.17g", x)' in text
    assert f'SCHEMA <- "{fx.R_CAPTURE_SCHEMA}"' in text


#: An action reference the workflow test accepts: ``owner/repo[/path]@v<N>[.<N>...]`` or
#: ``@`` and a 40-hex commit sha.
PINNED_USES = re.compile(r"^[\w.-]+/[\w./-]+@(v\d+(\.\d+)*|[0-9a-f]{40})$")
#: A ``run`` line the workflow test refuses: a git command that writes to a repository,
#: or the GitHub CLI.
GIT_WRITE = re.compile(r"\bgit\s+(push|commit|tag|merge|rebase|reset)\b|\bgh\s+\w")


def test_the_workflow_declares_read_permissions_uses_match_pinned_uses_no_run_matches_git_write():
    """What it inspects in ``.github/workflows/r-captures.yml`` (E12 repair 1, lens 1
    FA-B3; renamed in E12 repair 2, lens 2 FA-B2 / RG-B1, whose workflows passed a name
    that said "no git write step"). The triggers; the top-level ``permissions`` equal
    ``{contents: read}``; every job's ``permissions`` absent or a mapping whose every value
    is ``read`` or ``none``; the substring ``secrets.`` absent from the text; every
    ``uses`` matches :data:`PINNED_USES` (``v<N>`` or a commit sha; a tag can be moved by
    its owner, so it is a pin by name only); no step's ``run`` matches :data:`GIT_WRITE`;
    the container tag; the upload step's name, retention and three paths; the capture and
    drift steps. Not matched: ``git`` with an option before its subcommand
    (``git -C . push``, ``git -c user.name=x commit -am c``), a secret named as
    ``secrets['GITHUB_TOKEN']``, a ``uses`` of an action that commits
    (``stefanzweifel/git-auto-commit-action@v5``).
    ``tests/test_e12_repair2.py::test_fa_b2_lens_2_workflow_mutants_pass_this_check``
    plants each of those four and reads this test pass;
    ``tests/test_e12_repair1.py::test_fa_b3_each_lens_workflow_mutant_fails_the_workflow_test``
    and ``tests/test_e12_repair2.py::test_fa_b2_permission_mutants_fail_this_check`` plant
    W1-W3, ``permissions: read-all`` at job level and ``id-token: write`` at the top level
    and read this test fail on each."""
    import yaml

    path = REPO / ".github" / "workflows" / "r-captures.yml"
    text = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    on = doc.get("on", doc.get(True))
    assert set(on) == {"workflow_dispatch", "push"}
    assert set(on["push"]["paths"]) == {"fixtures/r/**", ".github/workflows/r-captures.yml"}
    assert doc["permissions"] == {"contents": "read"}
    assert "secrets." not in text and "write" not in json.dumps(doc["permissions"])
    cap = doc["jobs"]["capture"]
    assert cap["container"]["image"] == "rocker/r-ver:4.5.1"
    upload = next(s for s in cap["steps"] if str(s.get("uses", "")).startswith("actions/upload"))
    assert upload["with"]["name"] == "r-captures"
    assert upload["with"]["retention-days"] == 30
    assert set(upload["with"]["path"].split()) == {
        *fx.R_CAPTURE_FILES,
        fx.R_VECTORS_FILE,
    }
    assert any("Rscript fixtures/r/capture.R" in str(s.get("run", "")) for s in cap["steps"])
    steps = doc["jobs"]["compare"]["steps"]
    assert any("scripts/r_capture_drift.py" in str(s.get("run", "")) for s in steps)
    for name, job in doc["jobs"].items():
        perms = job.get("permissions", {})
        assert isinstance(perms, dict), (name, perms)
        assert set(perms.values()) <= {"read", "none"}, (name, perms)
        for s in job["steps"]:
            if "uses" in s:
                assert PINNED_USES.match(s["uses"]), s["uses"]
            assert not GIT_WRITE.search(str(s.get("run", ""))), (name, s.get("run"))
