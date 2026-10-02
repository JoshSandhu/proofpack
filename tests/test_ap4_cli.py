"""A-P4 item 5 (build day 10, lane A): ``proofpack run --format json,html,docx`` (D1 section
7), under the licence rule ``T8.html`` uses (E8: written when the licence is ``ok`` or in
``grace``; JSON only otherwise).

* the four licence states - ``ok``, ``grace``, ``expired`` (past grace), no licence - and
  exactly which files exist afterwards; the grace render carries the ``LICENCE EXPIRED``
  watermark in every DOCX section footer;
* ``--format docx`` alone writes the ``.docx`` files and no HTML; ``--templates T1`` writes
  ``T1.html`` and ``T1.docx`` only;
* the printed ``Next step`` line names the ``.docx`` files in each state;
* ``--json-log`` lists the documents; ``--offline`` is unchanged (the socket test is in
  ``tests/test_offline.py``, which gained the docx run).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ap4_docx import needs_extra, section_footers
from conftest import ephemeral_registry
from proofpack.cli import main
from proofpack.errors import EXIT_LICENCE, EXIT_OK, EXIT_WARNINGS
from proofpack.licence import WATERMARK_EXPIRED
from proofpack.run import document_names, parse_formats
from test_run_cli import _own_home, _prepare

pytestmark = [pytest.mark.day10, pytest.mark.ap4, needs_extra]

ALL = ("T1.html", "T1.docx", "T7.html", "T7.docx", "T8.html", "T8.docx")


def _run(tmp_path, *flags, out_name="pack"):
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / out_name
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--offline"]
        + list(flags),
        registry=ephemeral_registry(),
    )
    return rc, out


def _files(out):
    return sorted(p.name for p in out.iterdir() if p.suffix in (".html", ".docx"))


@pytest.mark.parametrize(
    "state, kwargs, usable",
    [
        ("ok", {"licence": True}, True),
        ("grace", {"licence": True, "expires": datetime.now(UTC) - timedelta(days=5)}, True),
        ("expired", {"licence": True, "expires": datetime.now(UTC) - timedelta(days=60)}, False),
        ("none", {"licence": False}, False),
    ],
)
def test_the_licence_states_and_which_files_exist(
    tmp_path, monkeypatch, capsys, state, kwargs, usable
):
    _own_home(tmp_path, monkeypatch, **kwargs)
    rc, out = _run(tmp_path, "--format", "json,html,docx", "--templates", "T1,T7,T8")
    printed = capsys.readouterr().out
    assert (out / "run.json").exists()
    if usable:
        assert rc in (EXIT_OK, EXIT_WARNINGS), (state, printed)
        assert _files(out) == sorted(ALL), state
        assert (
            "Next step: open the documents beside run.json (T1.html, T1.docx, T7.html, T7.docx, "
            "T8.html, T8.docx)" in printed
        ), printed
        footers = [f for i in ("T1", "T7", "T8") for f in section_footers(out / f"{i}.docx")]
        if state == "grace":
            assert all(WATERMARK_EXPIRED in f for f in footers), state
        else:
            assert not any("not for submission" in f for f in footers), state
    else:
        assert rc == EXIT_LICENCE, (state, printed)
        assert _files(out) == [], state
        assert "HTML and DOCX not written: licence" in printed
        assert (
            "Next step: proofpack licence install FILE, then run again for T1.html, T1.docx, "
            "T7.html, T7.docx, T8.html, T8.docx (docs: /docs/run)" in printed
        ), printed


def test_docx_alone_writes_the_docx_files_and_no_html(tmp_path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    rc, out = _run(tmp_path, "--format", "docx", "--templates", "T1,T7,T8")
    printed = capsys.readouterr().out
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    assert _files(out) == ["T1.docx", "T7.docx", "T8.docx"]
    assert "Next step: open the documents beside run.json (T1.docx, T7.docx, T8.docx)" in printed


def test_templates_t1_writes_t1_html_and_t1_docx_only(tmp_path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    rc, out = _run(tmp_path, "--format", "json,html,docx", "--templates", "T1")
    printed = capsys.readouterr().out
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    assert _files(out) == ["T1.docx", "T1.html"]
    assert "(T1.html, T1.docx)" in printed


def test_the_default_format_writes_no_docx(tmp_path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    rc, out = _run(tmp_path)
    capsys.readouterr()
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    assert _files(out) == ["T8.html"]


def test_no_licence_with_docx_alone_names_the_docx_files_without_a_format_hint(
    tmp_path, monkeypatch, capsys
):
    _own_home(tmp_path, monkeypatch, licence=False)
    rc, out = _run(tmp_path, "--format", "docx", "--templates", "T8")
    printed = capsys.readouterr().out
    assert rc == EXIT_LICENCE and _files(out) == []
    assert "then run again for T8.docx (docs: /docs/run)" in printed
    assert "--format json,html" not in printed  # the format asked already names a document


def test_json_log_reports_the_six_documents(tmp_path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    rc, out = _run(tmp_path, "--format", "json,html,docx", "--templates", "T1,T7,T8", "--json-log")
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])["run"]
    assert payload["formats"] == ["json", "html", "docx"]
    assert [Path(p).name for p in payload["documents"]] == list(ALL)
    assert payload["document_notes"] == []


def test_document_names_and_parse_formats():
    assert document_names(["json", "html", "docx"], ["T1", "T8"]) == [
        "T1.html",
        "T1.docx",
        "T8.html",
        "T8.docx",
    ]
    assert document_names(["docx"], ["T7"]) == ["T7.docx"]
    # E11 item 0 (c): no html/docx asked -> no names (the CLI names the html fallback
    # itself, after "with --format json,html"); T2 is never a run document, T2.docx none
    assert document_names(["json"], ["T8"]) == []
    assert document_names(["html", "docx"], ["T2", "T8"]) == ["T8.html", "T8.docx"]
    assert document_names(["html", "docx"], ["T2", "T7"], command="compare") == [
        "T2.html",
        "T7.html",
        "T7.docx",
    ]
    assert parse_formats("json,html,docx") == ["json", "html", "docx"]
    assert parse_formats("docx") == ["docx"]
    with pytest.raises(ValueError):
        parse_formats("pdf")
