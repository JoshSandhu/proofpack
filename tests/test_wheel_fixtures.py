"""A-P3 (build day 9, lane A): ``proofpack fixtures`` from a built wheel in a fresh venv.

The local stand-in for the release workflow's TestPyPI install (which has never run): a
wheel built from this tree (``uv build``, as ``tests/test_render_theme.py`` builds one) is
installed with ``pip --no-deps --no-index --target`` into a venv created here, and
``python -m proofpack.cli fixtures --offline`` runs in it. The runtime dependencies
(numpy, scipy, jsonschema, ...) are not installed into the venv - nothing is downloaded -
so they are put on ``PYTHONPATH`` from the user site-packages directory, with
``PYTHONNOUSERSITE=1`` so its ``.pth`` files (the editable install pointing at the main
tree) are not processed. Asserted: ``proofpack.__file__`` and the oracle files resolve
inside the venv; the report has 30 matched rows and 0 not matched, exit 0; ``git_sha`` is
null with the reason "not a git checkout (an installed wheel carries no git metadata)".
"""

from __future__ import annotations

import json
import os
import site
import subprocess
import sys
from pathlib import Path

import pytest

from test_render_theme import _build_wheel

pytestmark = [pytest.mark.day9, pytest.mark.ap3]


def test_fixtures_runs_from_a_built_wheel_in_a_fresh_venv(tmp_path: Path):
    wheel = _build_wheel(tmp_path / "dist")
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    py = (
        venv
        / ("Scripts" if os.name == "nt" else "bin")
        / ("python.exe" if os.name == "nt" else "python")
    )
    purelib = subprocess.run(
        [str(py), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "--no-deps",
            "--no-index",
            "--target",
            purelib,
            str(wheel),
        ],
        check=True,
        capture_output=True,
    )
    deps = site.getusersitepackages()
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    env.update(PYTHONNOUSERSITE="1", PYTHONPATH=deps, PROOFPACK_HOME=str(tmp_path / "home"))
    probe = subprocess.run(
        [
            str(py),
            "-c",
            "import proofpack, proofpack.resources as r; print(proofpack.__file__); "
            "print(r.resource_path('oracles_v1.json'))",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    if probe.returncode != 0 and "No module named" in probe.stderr:
        pytest.skip(f"runtime dependencies not importable from {deps}: {probe.stderr[-200:]}")
    assert probe.returncode == 0, probe.stderr
    for line in probe.stdout.strip().splitlines():
        assert Path(line).resolve().is_relative_to(venv.resolve()), line
    out = tmp_path / "fx"
    proc = subprocess.run(
        [str(py), "-m", "proofpack.cli", "fixtures", "--offline", "--out", str(out)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((out / "fixtures_report.json").read_text(encoding="utf-8"))
    assert report["summary"]["matched"] == 30 and report["summary"]["not_matched"] == 0
    assert report["git_sha"] is None
    assert report["git_sha_source"] == (
        "not a git checkout (an installed wheel carries no git metadata)"
    )
