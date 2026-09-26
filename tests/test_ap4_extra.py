"""A-P4 item 1 (build day 10, lane A): the ``[docx]`` extra (D1 section 0: never imported
in the browser; D4 section 9).

* ``pyproject.toml`` declares ``docx = [docxtpl, python-docx, matplotlib]`` and ``uv.lock``
  resolves the three (and their nine additions) - read from the files, not typed here;
* in a **subprocess**, ``import proofpack``, ``import proofpack.render.html``,
  ``import proofpack.render.docx``, ``import proofpack.cli`` and a T8 HTML render leave
  none of ``docx``, ``docxtpl``, ``matplotlib`` in ``sys.modules``;
* with the three modules hidden (``sys.modules[name] = None``), ``run --format json,html``
  still writes ``T8.html``; ``run --format json,html,docx`` (and each module hidden alone)
  prints one typed line on stderr, exits :data:`EXIT_DOCX_EXTRA_MISSING` (7) and writes
  nothing - no traceback, no ``run.json``;
* the code is in ``errors.py`` and the CLI's exit-code table; ``doctor`` names the three;
* the CI job ``docx-extra`` installs the extra and runs ``-m ap4`` with
  ``PROOFPACK_REQUIRE_DOCX=1``, and under that variable the skip of
  :data:`tests.ap4_docx.needs_extra` is refused here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from ap4_docx import EXTRA_REQUIRED, REPO, REQUIRE_ENV, synthetic_document
from conftest import ephemeral_registry
from proofpack.cli import main
from proofpack.errors import EXIT_DOCX_EXTRA_MISSING, EXIT_OK, EXIT_WARNINGS
from proofpack.render.docx import EXTRA_LINE, EXTRA_MODULES, DocxExtraMissing, extra_available
from test_run_cli import _own_home, _prepare

pytestmark = [pytest.mark.day10, pytest.mark.ap4]

DISTRIBUTIONS = {"docxtpl": "docxtpl", "python-docx": "docx", "matplotlib": "matplotlib"}


def _pyproject() -> dict:
    with (REPO / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def _lock() -> dict:
    with (REPO / "uv.lock").open("rb") as fh:
        return tomllib.load(fh)


# ------------------------------------------------------------------ the declaration


def test_pyproject_declares_the_extra_with_the_three_packages_and_floors():
    extra = _pyproject()["project"]["optional-dependencies"]["docx"]
    names = {}
    for spec in extra:
        name, _, floor = spec.partition(">=")
        names[name.strip()] = floor.strip()
    assert set(names) == set(DISTRIBUTIONS)
    assert all(floor for floor in names.values()), names
    assert set(EXTRA_MODULES) == set(DISTRIBUTIONS.values())


def test_uv_lock_resolves_the_extra_and_records_it_on_the_project():
    lock = _lock()
    by_name = {p["name"]: p for p in lock["package"]}
    project = by_name["proofpack"]
    assert set(project["metadata"]["provides-extras"]) == {"docx", "stats"}
    locked_extra = {d["name"] for d in project["optional-dependencies"]["docx"]}
    assert locked_extra == set(DISTRIBUTIONS)
    for name in DISTRIBUTIONS:
        assert name in by_name, name
        # the floor in pyproject.toml is at or below the locked version
        floor = next(
            s.partition(">=")[2]
            for s in _pyproject()["project"]["optional-dependencies"]["docx"]
            if s.startswith(name)
        )
        locked = tuple(int(x) for x in by_name[name]["version"].split(".")[:2])
        assert tuple(int(x) for x in floor.split(".")[:2]) <= locked, (name, floor, locked)
    # the nine additions of the re-lock (25 September 2026), so a later lock that drops
    # one is noticed
    for name in (
        "contourpy",
        "cycler",
        "docxtpl",
        "fonttools",
        "kiwisolver",
        "lxml",
        "matplotlib",
        "pillow",
        "python-docx",
    ):
        assert name in by_name, name


# ------------------------------------------------------------------ import hygiene


SUBPROCESS_SCRIPT = """
import json, sys
sys.path.insert(0, {src!r})
import proofpack
import proofpack.render.html as html
import proofpack.render.docx
import proofpack.render.figures
import proofpack.run
import proofpack.cli
doc = json.loads(open({doc!r}, encoding="utf-8").read())
page = html.render_t8(doc)
assert "<!DOCTYPE html>" in page
hits = sorted(m for m in ("docx", "docxtpl", "matplotlib") if m in sys.modules)
hits += sorted(m for m in sys.modules if m.startswith(("docx.", "docxtpl.", "matplotlib.")))
print(json.dumps({{"hits": hits, "docx_module": "proofpack.render.docx" in sys.modules}}))
"""


def test_import_proofpack_html_render_and_the_docx_module_load_none_of_the_extra(tmp_path):
    """Run in a subprocess: this process may already hold matplotlib from another test."""
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(synthetic_document()), encoding="utf-8")
    script = SUBPROCESS_SCRIPT.format(src=str(REPO / "src"), doc=str(doc_path))
    env = {**os.environ, "PYTHONPATH": str(REPO / "src"), "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(tmp_path),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    assert result == {"hits": [], "docx_module": True}


def test_figures_png_is_the_one_module_importing_matplotlib_and_docx_the_one_importing_docxtpl():
    src = REPO / "src" / "proofpack"
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(src).as_posix()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import matplotlib", "from matplotlib")):
                assert rel == "render/figures_png.py", (rel, stripped)
            if stripped.startswith(("import docxtpl", "from docxtpl", "import docx", "from docx")):
                assert rel == "render/docx.py", (rel, stripped)
                assert line.startswith("    "), (rel, stripped)  # inside a function


# ------------------------------------------------------------------ hidden modules


def _hide(monkeypatch, names):
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)
        for loaded in list(sys.modules):
            if loaded.startswith(name + "."):
                monkeypatch.setitem(sys.modules, loaded, None)


def _run(tmp_path, monkeypatch, *flags, out_name="pack"):
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / out_name
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), *flags],
        registry=ephemeral_registry(),
    )
    return rc, out


def test_extra_available_is_false_with_any_one_module_hidden(monkeypatch):
    for name in EXTRA_MODULES:
        with monkeypatch.context() as mp:
            _hide(mp, [name])
            assert extra_available() is False, name
            with pytest.raises(DocxExtraMissing) as exc:
                from proofpack.render.docx import require_extra

                require_extra()
            assert exc.value.exit_code == EXIT_DOCX_EXTRA_MISSING == 7
            assert str(exc.value) == EXTRA_LINE


def test_with_the_three_hidden_run_format_json_html_still_writes_t8_html(
    tmp_path, monkeypatch, capsys
):
    _hide(monkeypatch, EXTRA_MODULES)
    rc, out = _run(tmp_path, monkeypatch, "--offline", "--format", "json,html")
    assert rc in (EXIT_OK, EXIT_WARNINGS), capsys.readouterr()
    assert (out / "T8.html").exists() and (out / "run.json").exists()
    assert not (out / "T8.docx").exists()


@pytest.mark.parametrize("hidden", [EXTRA_MODULES, ("docx",), ("docxtpl",), ("matplotlib",)])
def test_with_modules_hidden_run_format_docx_prints_one_typed_line_exits_7_and_writes_nothing(
    tmp_path, monkeypatch, capsys, hidden
):
    _hide(monkeypatch, hidden)
    rc, out = _run(tmp_path, monkeypatch, "--offline", "--format", "json,html,docx")
    captured = capsys.readouterr()
    assert rc == EXIT_DOCX_EXTRA_MISSING == 7
    assert captured.err.strip().splitlines() == [f"error: {EXTRA_LINE}"]
    assert "Traceback" not in captured.err and "Traceback" not in captured.out
    assert not out.exists(), sorted(p.name for p in out.iterdir())
    assert "[docx]" in EXTRA_LINE and "nothing was written" in EXTRA_LINE


def test_docx_alone_is_a_format_token_and_is_refused_the_same_way_without_the_extra(
    tmp_path, monkeypatch, capsys
):
    _hide(monkeypatch, EXTRA_MODULES)
    rc, out = _run(tmp_path, monkeypatch, "--offline", "--format", "docx")
    assert rc == EXIT_DOCX_EXTRA_MISSING
    assert capsys.readouterr().err.strip() == f"error: {EXTRA_LINE}"
    assert not out.exists()


# ------------------------------------------------------------------ documentation


def test_exit_code_seven_is_in_errors_py_and_the_cli_exit_table():
    errors = " ".join((REPO / "src" / "proofpack" / "errors.py").read_text("utf-8").split())
    cli = " ".join((REPO / "src" / "proofpack" / "cli.py").read_text("utf-8").split())
    assert "EXIT_DOCX_EXTRA_MISSING = 7" in errors
    assert "7 ``--format docx`` asked without the ``[docx]`` extra" in errors
    assert "7 ``run --format ...docx...`` without the ``[docx]`` extra" in cli


def test_doctor_names_the_three_modules_of_the_extra(capsys):
    from proofpack.cli import main as cli_main

    rc = cli_main(["doctor", "--offline"])
    printed = capsys.readouterr().out
    assert rc == 0, printed
    row = next(line for line in printed.splitlines() if "docx extra" in line)
    if extra_available():
        for name in ("docxtpl", "python-docx", "matplotlib"):
            assert name in row, row
    else:
        assert "not installed" in row, row


# ------------------------------------------------------------------ CI


def test_ci_has_a_docx_extra_job_installing_the_extra_and_running_ap4_with_the_skip_refused():
    ci = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    job = ci["jobs"]["docx-extra"]
    runs = [str(s.get("run", "")) for s in job["steps"]]
    assert any("uv sync" in r and "--extra docx" in r and "--locked" in r for r in runs), runs
    pytest_step = next(s for s in job["steps"] if "-m ap4" in str(s.get("run", "")))
    env = {**job.get("env", {}), **pytest_step.get("env", {})}
    assert str(env.get(REQUIRE_ENV)) == "1", env
    # the main test job installs no extra: the ap4 tests skip there with the named reason
    main_runs = [str(s.get("run", "")) for s in ci["jobs"]["test"]["steps"]]
    assert not any("--extra docx" in r for r in main_runs)


def test_when_the_extra_is_required_it_is_installed():
    """Under ``PROOFPACK_REQUIRE_DOCX=1`` (the CI job) a missing package is a failure, not
    a skip; elsewhere this test records which case this run is."""
    if EXTRA_REQUIRED:
        assert extra_available(), "PROOFPACK_REQUIRE_DOCX=1 but the extra is not installed"
        import docx  # noqa: F401
        import docxtpl  # noqa: F401
        import matplotlib  # noqa: F401
    else:
        assert isinstance(extra_available(), bool)


def test_the_helper_module_is_not_collected_and_names_the_skip_reason():
    src = (Path(__file__).parent / "ap4_docx.py").read_text(encoding="utf-8")
    assert "def test_" not in src
    assert REQUIRE_ENV in src and "docx-extra" in src
