"""A-P3 (build day 9, lane A): ``proofpack fixtures`` from a built wheel in a fresh venv.

The local stand-in for the release workflow's TestPyPI install (which has never run): a
wheel built from this tree (``uv build``, as ``tests/test_render_theme.py`` builds one) is
installed with ``pip --no-deps --no-index --target`` into a venv created here, and
``python -m proofpack.cli fixtures --offline`` runs in it. The runtime dependencies
(numpy, scipy, jsonschema, ...) are not installed into the venv - nothing is downloaded -
so they are put on ``PYTHONPATH`` from :func:`dependency_paths`: the directory from which
the interpreter running pytest imports each module of :data:`RUNTIME_MODULES` (A-P3 repair
3, CI-2: at ``78ae8dc`` the path was ``site.getusersitepackages()``; in GitHub Actions
run 36005620750 the fixtures run then exited 5 with ``ModuleNotFoundError: No module
named 'numpy'``). ``PYTHONNOUSERSITE=1`` is set, as at ``78ae8dc``. Asserted:
the probe imports proofpack and each of :data:`RUNTIME_MODULES` in the fresh venv (no
skip when it cannot: the test fails), ``proofpack.__file__`` and the oracle files resolve
inside the venv; the report has 29 matched rows and 0 not matched, exit 0 (F14 is 'no
oracle recorded': its [unverified] Newcombe transcription is not packaged); ``git_sha`` is
null with the reason "not a git checkout (an installed wheel carries no git metadata)".
The test is skipped only when the interpreter running pytest cannot import one of
:data:`RUNTIME_MODULES` itself, and the skip names it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from test_render_theme import _build_wheel

pytestmark = [pytest.mark.day9, pytest.mark.ap3]

#: The import names of the 14 packages of ``requirements.lock`` (``uv export --no-dev
#: --extra stats``): the runtime dependencies and scipy, and what they import.
RUNTIME_MODULES = (
    "numpy",
    "scipy",
    "yaml",
    "jsonschema",
    "jsonschema_specifications",
    "referencing",
    "rpds",
    "attrs",
    "jinja2",
    "markupsafe",
    "cryptography",
    "cffi",
    "pycparser",
    "typing_extensions",
)


def dependency_paths() -> list[str]:
    """The ``sys.path`` directory each of :data:`RUNTIME_MODULES` is imported from by this
    interpreter, in first-seen order; skips the calling test, naming the module, when one is
    not importable here."""
    out: list[str] = []
    for name in RUNTIME_MODULES:
        spec = importlib.util.find_spec(name)
        if spec is None or spec.origin is None:
            pytest.skip(f"{name} is not importable by the interpreter running pytest")
        where = Path(spec.origin).parent
        if spec.submodule_search_locations:  # a package: its directory's parent
            where = where.parent
        if str(where) not in out:
            out.append(str(where))
    return out


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
    deps = dependency_paths()
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    env.update(
        PYTHONNOUSERSITE="1",
        PYTHONPATH=os.pathsep.join(deps),
        PROOFPACK_HOME=str(tmp_path / "home"),
    )
    probe = subprocess.run(
        [
            str(py),
            "-c",
            f"import {', '.join(RUNTIME_MODULES)}; "
            "import proofpack, proofpack.resources as r; print(proofpack.__file__); "
            "print(r.resource_path('oracles_v1.json'))",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert probe.returncode == 0, f"PYTHONPATH={env['PYTHONPATH']}\n{probe.stderr}"
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
    assert report["summary"]["matched"] == 29 and report["summary"]["not_matched"] == 0
    # the Newcombe transcription is [unverified] and not packaged: F14 has no oracle here
    f14 = next(r for r in report["rows"] if r["id"] == "F14-newcombe")
    assert f14["status"] == "no_oracle_recorded" and f14["matched"] is False
    assert f14["reason"].startswith("[unverified against the primary PDF] fixtures/newcombe")
    assert report["git_sha"] is None
    assert report["git_sha_source"] == (
        "not a git checkout (an installed wheel carries no git metadata)"
    )
