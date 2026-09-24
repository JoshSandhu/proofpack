"""A-P3 repair 3 (build day 9, lane A): the three findings of GitHub Actions run 36005620750
on main ``78ae8dc``, each as the literal input fed and the figure asserted.

* CI-1: ``scripts/capture_fixture_oracles.py --check`` exited 1 on ubuntu / Python 3.12
  with nothing printed. Fed here, through ``--check --committed <copy>``: the committed
  file (repair round 1, RG3-B1: a capture made in the test, labelled as captured on
  ``planted-platform cp0``) with ``captured.F1-wilson.values.wilson_lo`` moved by +2e-9 and
  ``captured.F3-delong.values.paired_p`` by +1e-12 gives exit 1, one line per moved value
  with both figures (``OUTSIDE`` for the first, ``within`` for the second) and the count
  line ``63 identical, 1 differ within their tolerance, 1 differ outside it``; the second
  move alone gives exit 0. Through ``compare()``, the committed side labelled
  ``planted-platform cp0``: ``F6-homogeneity`` ``chi2_p`` moved by +5e-7 is within
  (iterative, 1e-6) and ``chi2`` moved by +5e-7 is not (closed form, 1e-9); a changed
  ``source``, an extra value name and a value ``true`` are each reported and give
  False. The committed file names the platform it was captured on, and each
  value's class in the script equals the tolerance the ``proofpack fixtures`` rows apply
  to it.
* CI-2: with ``PYTHONUSERBASE`` set to an empty directory and the dependencies reachable
  only through ``PYTHONPATH`` (the layout of CI's ``.venv``), a fresh interpreter given
  ``PYTHONPATH=<site.getusersitepackages()>`` cannot import numpy (the 78ae8dc layout),
  and one given ``tests/test_wheel_fixtures.py::dependency_paths()`` imports the six
  runtime modules.
* CI-3: in ``ci.yml`` ``docker-smoke`` and ``release.yml`` ``image``, the build step tees
  its log to ``docker-build.log`` and the digest step reads it with ``grep`` (no ``docker
  image inspect``); the step's pattern, applied to three lines of run 36005620750's log,
  returns ``docker.io/library/python:3.12-slim@sha256:2f17fc04...06a9``.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "capture_fixture_oracles.py"
COMMITTED = REPO / "fixtures" / "oracles_v1.json"


def _capture_module():
    spec = importlib.util.spec_from_file_location("capture_fixture_oracles_r3", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["capture_fixture_oracles_r3"] = module
    spec.loader.exec_module(module)
    return module


def _committed() -> dict:
    return json.loads(COMMITTED.read_text(encoding="utf-8"))


def _moved(doc: dict, entry: str, name: str, by: float) -> tuple[dict, float, float]:
    out = copy.deepcopy(doc)
    before = out["captured"][entry]["values"][name]
    out["captured"][entry]["values"][name] = before + by
    return out, before, before + by


#: The platform a committed side is labelled with when a test needs the tolerance
#: comparison (repair round 1: the same platform and library versions compare exactly).
OTHER_PLATFORM = "planted-platform cp0"


def fresh_capture() -> dict:
    """A capture made in this process, as ``--check`` reads it (repair round 1, RG3-B1:
    the CI-1 subprocess tests move values in this, not in fixtures/oracles_v1.json, so
    their counts do not depend on the committed file equalling this machine's capture)."""
    pytest.importorskip("statsmodels")
    pytest.importorskip("sklearn")
    mod = _capture_module()
    return json.loads(mod.dumps(mod.capture()))


def elsewhere(doc: dict) -> dict:
    """A copy of ``doc`` whose ``captured_on_platform`` is :data:`OTHER_PLATFORM`."""
    out = copy.deepcopy(doc)
    out["captured_on_platform"] = OTHER_PLATFORM
    return out


def _check(tmp_path: Path, doc: dict) -> subprocess.CompletedProcess:
    pytest.importorskip("statsmodels")
    pytest.importorskip("sklearn")
    path = tmp_path / "oracles_moved.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--check", "--committed", str(path)],
        capture_output=True,
        text=True,
    )


# ------------------------------------------------------------------------------ CI-1


def test_ci1_check_prints_each_moved_value_with_both_figures_and_exits_1(tmp_path: Path):
    doc, lo_c, lo_f = _moved(elsewhere(fresh_capture()), "F1-wilson", "wilson_lo", 2e-9)
    doc, p_c, p_f = _moved(doc, "F3-delong", "paired_p", 1e-12)
    proc = _check(tmp_path, doc)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    lines = proc.stdout.splitlines()
    lo = [ln for ln in lines if ln.startswith("captured.F1-wilson.values.wilson_lo:")]
    p = [ln for ln in lines if ln.startswith("captured.F3-delong.values.paired_p:")]
    assert len(lo) == 1 and len(p) == 1, proc.stdout
    # the file on disk is the "committed" side; the script's own capture is the fresh side
    assert f"committed {lo_f!r} fresh {lo_c!r}" in lo[0] and lo[0].endswith(
        "closed_form tolerance 1e-09 OUTSIDE"
    )
    assert f"committed {p_f!r} fresh {p_c!r}" in p[0] and p[0].endswith(
        "iterative tolerance 1e-06 within"
    )
    assert (
        "captured values: 63 identical, 1 differ within their tolerance, 1 differ outside it"
        in lines
    )


def test_ci1_a_value_moved_within_its_class_is_printed_and_exits_0(tmp_path: Path):
    doc, p_c, p_f = _moved(elsewhere(fresh_capture()), "F3-delong", "paired_p", 1e-12)
    proc = _check(tmp_path, doc)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"captured.F3-delong.values.paired_p: committed {p_f!r} fresh {p_c!r}" in proc.stdout
    assert "64 identical, 1 differ within their tolerance, 0 differ outside it" in proc.stdout


def test_ci1_chi2_p_is_compared_as_iterative_and_chi2_as_closed_form():
    mod = _capture_module()
    base = _committed()
    doc, _, _ = _moved(elsewhere(base), "F6-homogeneity", "chi2_p", 5e-7)
    lines, ok = mod.compare(doc, base)
    assert ok is True and any(ln.endswith("iterative tolerance 1e-06 within") for ln in lines)
    doc, _, _ = _moved(elsewhere(base), "F6-homogeneity", "chi2", 5e-7)
    lines, ok = mod.compare(doc, base)
    assert ok is False and any(ln.endswith("closed_form tolerance 1e-09 OUTSIDE") for ln in lines)


def test_ci1_a_changed_source_an_extra_value_and_a_bool_are_each_reported():
    mod = _capture_module()
    base = _committed()
    doc = copy.deepcopy(base)
    doc["captured"]["F2-exact"]["source"] = "planted"
    lines, ok = mod.compare(doc, base)
    assert ok is False and any(ln.startswith("captured.F2-exact.source:") for ln in lines)
    doc = copy.deepcopy(base)
    doc["captured"]["F8-half-width"]["values"]["half_width_n7"] = 0.1
    lines, ok = mod.compare(doc, base)
    assert ok is False
    assert "captured.F8-half-width.values.half_width_n7: present in the committed file only" in (
        lines
    )
    doc = copy.deepcopy(base)
    doc["captured"]["F10-exact"]["values"]["as_positive_sensitivity"] = True
    lines, ok = mod.compare(doc, base)
    assert ok is False and any("as_positive_sensitivity: not a number" in ln for ln in lines)
    doc = copy.deepcopy(base)
    doc["register"]["F1"]["wilson_lo"] = 0.2554
    lines, ok = mod.compare(doc, base)
    assert ok is False and "register: differs (compared for equality)" in lines
    # a changed platform and numpy version select the tolerance classes; with no value
    # moved the result is True
    doc = copy.deepcopy(base)
    doc["captured_on_platform"] = "linux-x86_64 cp312"
    doc["library_versions"]["numpy"] = "2.5.3"
    lines, ok = mod.compare(doc, base)
    assert ok is True


def test_ci1_the_committed_file_names_the_platform_it_was_captured_on():
    doc = _committed()
    assert doc["captured_on_platform"] == "win-amd64 cp314"
    assert doc["library_versions"] == {
        "numpy": "2.5.1",
        "python": "3.14.6",
        "scikit-learn": "1.9.0",
        "scipy": "1.18.1",
        "statsmodels": "0.15.0",
    }


def test_the_check_classes_are_the_fixtures_rows_classes():
    """For each value a ``proofpack fixtures`` row reads from ``captured``, the tolerance
    the row applies equals the one ``--check`` applies (the smallest, where two rows read
    the same value); every captured value has a class in the script."""
    from proofpack import fixtures as fx

    mod = _capture_module()
    oracles = fx.load_oracles()
    applied: dict[tuple[str, str], float] = {}
    for row in fx.register():
        if row.oracle is None:
            continue
        try:
            values, tol, source = row.oracle(oracles)
        except fx.OracleAbsent:
            continue
        if not source["entry"].startswith("captured."):
            continue
        entry = source["entry"][len("captured.") :]
        for name in values:
            key = (entry, name)
            applied[key] = min(applied.get(key, tol[name]), tol[name])
    assert len(applied) >= 50, len(applied)
    for (entry, name), tol in sorted(applied.items()):
        assert mod.TOLERANCE[mod.value_class(entry, name)] == tol, (entry, name)
    for entry, body in _committed()["captured"].items():
        for name in body["values"]:
            assert mod.value_class(entry, name) in mod.TOLERANCE, (entry, name)


# ------------------------------------------------------------------------------ CI-2


def _package_dir(name: str) -> str:
    spec = importlib.util.find_spec(name)
    assert spec is not None and spec.origin is not None, name
    return str(Path(spec.origin).parent.parent)


def test_ci2_the_wheel_test_takes_its_dependency_path_from_where_they_are_imported(
    tmp_path: Path,
):
    empty = tmp_path / "userbase"
    empty.mkdir()
    # a fresh venv: its interpreter has no site-packages of its own holding numpy, whether
    # pytest runs from a venv (CI's .venv) or from a user site (this machine)
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    py = str(
        venv
        / ("Scripts" if os.name == "nt" else "bin")
        / ("python.exe" if os.name == "nt" else "python")
    )
    reach = []
    for name in ("pytest", "numpy", "yaml", "jinja2"):
        d = _package_dir(name)
        if d not in reach:
            reach.append(d)
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    env.update(
        PYTHONUSERBASE=str(empty),
        PYTHONNOUSERSITE="1",
        PYTHONPATH=os.pathsep.join([str(REPO / "tests"), str(REPO / "src"), *reach]),
    )
    probe = subprocess.run(
        [
            py,
            "-c",
            "import json, site, test_wheel_fixtures as t; "
            "print(json.dumps([site.getusersitepackages(), t.dependency_paths()]))",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert probe.returncode == 0, probe.stderr
    user_site, paths = json.loads(probe.stdout.strip().splitlines()[-1])
    assert _package_dir("numpy") in paths and user_site not in paths
    imports = "import numpy, scipy, yaml, jsonschema, jinja2, cryptography"
    run_env = {k: v for k, v in env.items() if k != "PYTHONPATH"}
    old = subprocess.run(
        [py, "-c", imports],
        capture_output=True,
        text=True,
        env={**run_env, "PYTHONPATH": user_site},
        cwd=str(tmp_path),
    )
    assert old.returncode != 0 and "No module named 'numpy'" in old.stderr
    new = subprocess.run(
        [py, "-c", imports],
        capture_output=True,
        text=True,
        env={**run_env, "PYTHONPATH": os.pathsep.join(paths)},
        cwd=str(tmp_path),
    )
    assert new.returncode == 0, new.stderr


# ------------------------------------------------------------------------------ CI-3

#: Three lines of the docker-smoke job's log in run 36005620750 (24 September 2026).
CI_LOG_LINES = (
    "#2 [internal] load metadata for docker.io/library/python:3.12-slim\n"
    "#6 [1/5] FROM docker.io/library/python:3.12-slim@sha256:"
    "2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9\n"
    "#6 resolve docker.io/library/python:3.12-slim@sha256:"
    "2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9 done\n"
)
DIGEST_STEP = "record the base image digest (the Dockerfile pin is [unverified] until this is read)"


@pytest.mark.parametrize("name,job", [("ci.yml", "docker-smoke"), ("release.yml", "image")])
def test_ci3_the_digest_step_reads_the_build_log(name: str, job: str):
    doc = yaml.safe_load((REPO / ".github" / "workflows" / name).read_text(encoding="utf-8"))
    steps = doc["jobs"][job]["steps"]
    runs = [str(s.get("run", "")) for s in steps]
    build = next(i for i, r in enumerate(runs) if "docker build" in r)
    digest = next(i for i, s in enumerate(steps) if s.get("name") == DIGEST_STEP)
    smoke = next(i for i, r in enumerate(runs) if "--network none proofpack:ci doctor" in r)
    assert build < digest < smoke
    assert "set -euo pipefail" in runs[build]
    assert "docker build --platform linux/amd64 -t proofpack:ci ." in runs[build]
    assert runs[build].rstrip().endswith("2>&1 | tee docker-build.log")
    assert "docker image inspect" not in runs[digest]
    assert runs[digest].rstrip().endswith("docker-build.log")
    pattern = re.search(r"grep -o -m1 -E '([^']+)' docker-build\.log", runs[digest])
    assert pattern is not None, runs[digest]
    found = re.findall(pattern.group(1), CI_LOG_LINES)
    assert found[0] == (
        "docker.io/library/python:3.12-slim@sha256:"
        "2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9"
    )


@pytest.mark.parametrize("name", ["ci.yml", "release.yml"])
def test_ci3_no_step_inspects_the_base_image_from_the_daemon_store(name: str):
    doc = yaml.safe_load((REPO / ".github" / "workflows" / name).read_text(encoding="utf-8"))
    for job_id, job in doc["jobs"].items():
        for step in job.get("steps", []):
            run = str(step.get("run", ""))
            assert "docker image inspect python" not in run, (job_id, step.get("name"))
