"""Build day 11 (E11) item 0: the cold lens on the A-P4 merge
(``handoffs/2026-10-02_A_ap4_merge_lens.md``), blockers B1 and B3 (B2 is
``tests/test_ap4_roundtrip.py::
test_t1_criteria_cells_with_a_paired_subgroup_criterion_equal_the_html_in_the_docx``).

* **B1.** ``compare --format json,html,docx`` without the ``[docx]`` extra (the three modules
  hidden as ``tests/test_ap4_extra.py`` hides them) is one typed line on stderr, exit 7,
  before any statistics run, nothing written - ``cmd_run``'s check. At ``a13931b`` the
  same command wrote ``run.json``, the two ingest reports, ``pseudonyms.json``,
  ``T2.html`` and ``T7.html`` and then exited 7 saying nothing was written.
* **B3.** The ``Next step`` line names only documents the command can write: ``run`` never
  writes T2 (in any format), no command writes ``T2.docx``. ``run --templates T2`` names
  ``proofpack compare``; measured with a licence and without one.
"""

from __future__ import annotations

import re
import sys

import pytest

from conftest import ephemeral_registry
from proofpack.cli import main
from proofpack.errors import EXIT_DOCX_EXTRA_MISSING, EXIT_LICENCE, EXIT_OK, EXIT_WARNINGS
from proofpack.render.docx import EXTRA_LINE, EXTRA_MODULES
from test_e10_compare_cli import _compare, _home, _inputs
from test_run_cli import _own_home, _prepare

pytestmark = pytest.mark.day11

COMPARE_POINTER = (
    "Next step: proofpack compare --input NEW --prior PRIOR --criteria FILE writes "
    "T2.html (docs: /docs/compare)"
)


def _hide(monkeypatch, names):
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)
        for loaded in list(sys.modules):
            if loaded.startswith(name + "."):
                monkeypatch.setitem(sys.modules, loaded, None)


def _next_step(printed: str) -> str:
    lines = [ln for ln in printed.splitlines() if ln.startswith("Next step:")]
    assert len(lines) == 1, printed
    return lines[0]


# ------------------------------------------------------------------ B1


@pytest.mark.parametrize("hidden", [EXTRA_MODULES, ("docx",), ("docxtpl",), ("matplotlib",)])
def test_compare_format_docx_without_the_extra_exits_7_with_one_line_and_writes_nothing(
    tmp_path, monkeypatch, capsys, hidden
):
    _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    _hide(monkeypatch, hidden)
    out = tmp_path / "pack"
    rc = _compare(new, prior, crit, out, "--format", "json,html,docx", "--templates", "T2,T7")
    captured = capsys.readouterr()
    assert rc == EXIT_DOCX_EXTRA_MISSING == 7
    assert captured.err.strip().splitlines() == [f"error: {EXTRA_LINE}"]
    assert "Traceback" not in captured.err + captured.out
    assert not out.exists(), sorted(p.name for p in out.iterdir())
    # no statistics ran: the per-user ledger was not touched either
    assert not (tmp_path / "home" / "ledger.json").exists()


def test_compare_format_json_html_with_the_extra_hidden_still_writes_t2(
    tmp_path, monkeypatch, capsys
):
    _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    _hide(monkeypatch, EXTRA_MODULES)
    out = tmp_path / "pack"
    rc = _compare(new, prior, crit, out, "--format", "json,html")
    assert rc == EXIT_OK, capsys.readouterr()
    assert (out / "T2.html").exists()


def test_compare_help_names_docx():
    from proofpack.cli import _build_parser

    sub = next(
        a for a in _build_parser()._subparsers._group_actions if a.dest == "command"
    ).choices["compare"]
    fmt = next(a for a in sub._actions if a.dest == "format")
    assert "json, html, docx" in fmt.help and "[docx] extra" in fmt.help


# ------------------------------------------------------------------ B3


def _run(tmp_path, monkeypatch, capsys, *flags, licence=True):
    _own_home(tmp_path, monkeypatch, licence=licence)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    argv = ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out)]
    rc = main([*argv, "--offline", *flags], registry=ephemeral_registry())
    return rc, capsys.readouterr().out, out


@pytest.mark.parametrize("licence", [True, False])
@pytest.mark.parametrize("formats", ["docx", "json,html", "json,html,docx", "json"])
def test_run_templates_t2_names_compare_and_no_t2_file_run_would_write(
    tmp_path, monkeypatch, capsys, licence, formats
):
    rc, printed, out = _run(
        tmp_path, monkeypatch, capsys, "--templates", "T2", "--format", formats, licence=licence
    )
    assert rc == (EXIT_LICENCE if not licence else rc)
    assert rc in (EXIT_OK, EXIT_WARNINGS, EXIT_LICENCE)
    assert _next_step(printed) == COMPARE_POINTER
    assert not list(out.glob("T2.*"))


@pytest.mark.parametrize(
    "licence, formats, expected",
    [
        (True, "json,docx", "Next step: open the documents beside run.json (T8.docx)"),
        (
            False,
            "json,docx",
            "Next step: proofpack licence install FILE, then run again for T8.docx",
        ),
        (
            False,
            "json,html,docx",
            "Next step: proofpack licence install FILE, then run again for T8.html, T8.docx",
        ),
        (
            False,
            "json",
            "Next step: proofpack licence install FILE, then run again with --format json,html "
            "for T8.html",
        ),
        (True, "json", "Next step: run again with --format json,html for T8.html"),
    ],
)
def test_run_templates_t2_t8_names_t8_only(
    tmp_path, monkeypatch, capsys, licence, formats, expected
):
    _, printed, _ = _run(
        tmp_path, monkeypatch, capsys, "--templates", "T2,T8", "--format", formats, licence=licence
    )
    line = _next_step(printed)
    assert line.startswith(expected), line
    assert not re.search(r"T2\.(html|docx)", line), line


@pytest.mark.parametrize(
    "lic, formats, templates, expected",
    [
        ("ok", "json,docx", "T2", "Next step: compare again with --format json,html for T2.html"),
        (
            "none",
            "json,docx",
            "T2,T7",
            "Next step: proofpack licence install FILE, then compare again for T7.docx",
        ),
        (
            "none",
            "json,docx",
            "T2",
            "Next step: proofpack licence install FILE, then compare again with --format "
            "json,html for T2.html",
        ),
        (
            "none",
            "json,html,docx",
            "T2,T8",
            "Next step: proofpack licence install FILE, then compare again for T2.html, "
            "T8.html, T8.docx",
        ),
    ],
)
def test_compare_next_step_never_names_t2_docx(
    tmp_path, monkeypatch, capsys, lic, formats, templates, expected
):
    if lic == "ok":
        _home(tmp_path, monkeypatch)
    else:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("PROOFPACK_HOME", str(home))
    new, prior, crit = _inputs(tmp_path)
    _compare(new, prior, crit, tmp_path / "pack", "--format", formats, "--templates", templates)
    line = _next_step(capsys.readouterr().out)
    assert line.startswith(expected), line
    assert "T2.docx" not in line
