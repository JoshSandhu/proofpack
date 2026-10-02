"""E11 repair 1 (2 October 2026): regression tests for the two cold lenses on ``2adfaaa``.

Each test here was run against ``2adfaaa`` in a detached worktree and failed there (the
first failing line of each is in the repair note). Literal inputs are the F5 pair
(``tests/fixtures/f5``) under the ephemeral test licence, ``--offline``.

* **RG-B1 / FA-N2** - a run or compare whose writer raises after another of its documents
  reached disk is counted in the ledger (DEC-47 counts a run that wrote a document). At
  ``2adfaaa`` the CLI recorded the ledger only when ``write_documents`` returned, so the
  ledger stayed at ``{key: 1}`` while ``run.json`` said ``ledger_count`` 2.
* **FA-N6 (M19's half)** - a compare whose first writer raises wrote nothing and is not
  counted (this one passes at ``2adfaaa``; planted there, M19 fails it).
* **FA-B1 / RG-B2** - the two lenses' one-dominant-case cells print the cluster bootstrap
  with route ``case_share_above_grid``; at ``2adfaaa`` both printed ``wilson_deff``. The T7
  sentence for ``wilson_deff`` names where it prints and no longer says its measured
  coverage is at or above the bar.
* **FA-N1** - ``run --templates T2`` without a licence carrying the ``compare`` feature
  names the licence before ``proofpack compare``.
* **FA-N4** - ``compare --format ...docx --templates T2,...`` no longer prints that T2 is
  "not built in this engine version"; it says T2 has no DOCX writer.

The writers are patched on the module objects imported at the top of this file (not by
dotted string), so the patch is undone on the module that the run reads (lens FA-N8).
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import numpy as np
import pytest

import proofpack.render.html as render_html
import proofpack.render.t2 as render_t2
import proofpack.render.t7 as render_t7
import proofpack.run as run_mod
from ap4_docx import needs_extra
from conftest import ephemeral_registry
from proofpack.cli import main
from proofpack.errors import EXIT_INTERNAL, EXIT_LICENCE, EXIT_OK, EXIT_WARNINGS
from proofpack.stats.bootstrap import plan_clustering, proportion_ci
from test_e10_compare_cli import _compare, _home, _inputs

pytestmark = pytest.mark.day11


def _run(new: Path, crit: Path, out: Path, *flags: str) -> int:
    argv = ["run", "--input", str(new), "--criteria", str(crit), "--out", str(out)]
    return main([*argv, "--offline", *flags], registry=ephemeral_registry())


def _counts(home: Path) -> dict:
    path = home / "ledger.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))["counts"]


def _doc(out: Path) -> dict:
    return json.loads((out / "run.json").read_text(encoding="utf-8"))


def _boom(document, out_dir):
    raise OSError("disk full (planted)")


# ------------------------------------------------------------------ RG-B1 / FA-N2


def test_a_run_whose_t8_writer_raises_after_t1_and_t7_counts(tmp_path, monkeypatch, capsys):
    home = _home(tmp_path, monkeypatch)
    new, _, crit = _inputs(tmp_path)
    assert _run(new, crit, tmp_path / "r1") in (EXIT_OK, EXIT_WARNINGS)
    key = _doc(tmp_path / "r1")["ledger"]["test_set_sha256"]
    assert _counts(home) == {key: 1}
    monkeypatch.setattr(render_html, "write_t8", _boom)
    monkeypatch.setattr(run_mod, "write_t8", _boom)
    out = tmp_path / "r2"
    assert _run(new, crit, out, "--templates", "T1,T7,T8") == EXIT_INTERNAL
    assert "disk full (planted)" in capsys.readouterr().err
    assert (out / "T1.html").exists() and (out / "T7.html").exists()
    assert not (out / "T8.html").exists()
    # the run wrote two documents: counted, and the count its run.json carries is stored
    assert _counts(home) == {key: 2}
    assert _doc(out)["manifest"]["ledger_count"] == 2


def test_a_read_only_t8_after_t1_and_t7_counts_the_run(tmp_path, monkeypatch, capsys):
    """The lens's own probe (RG-B1), no patch: a read-only ``T8.html`` already in
    ``--out`` makes the T8 writer raise ``PermissionError`` after T1 and T7 are written."""
    home = _home(tmp_path, monkeypatch)
    new, _, crit = _inputs(tmp_path)
    assert _run(new, crit, tmp_path / "r1") in (EXIT_OK, EXIT_WARNINGS)
    key = _doc(tmp_path / "r1")["ledger"]["test_set_sha256"]
    out = tmp_path / "r2"
    out.mkdir()
    locked = out / "T8.html"
    locked.write_text("held open elsewhere", encoding="utf-8")
    os.chmod(locked, stat.S_IREAD)
    try:
        rc = _run(new, crit, out, "--templates", "T1,T7,T8")
    finally:
        os.chmod(locked, stat.S_IREAD | stat.S_IWRITE)
    assert rc == EXIT_INTERNAL
    assert "PermissionError" in capsys.readouterr().err
    assert locked.read_text(encoding="utf-8") == "held open elsewhere"
    assert _counts(home) == {key: 2}
    assert _doc(out)["manifest"]["ledger_count"] == 2


def test_a_compare_whose_t2_writer_raises_after_t7_counts(tmp_path, monkeypatch, capsys):
    home = _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    monkeypatch.setattr(render_t2, "write_t2", _boom)
    out = tmp_path / "c"
    assert _compare(new, prior, crit, out, "--templates", "T7,T2") == EXIT_INTERNAL
    assert "disk full (planted)" in capsys.readouterr().err
    assert (out / "T7.html").exists() and not (out / "T2.html").exists()
    key = _doc(out)["ledger"]["test_set_sha256"]
    assert _counts(home) == {key: 1}
    assert _doc(out)["manifest"]["ledger_count"] == 1


def test_a_compare_whose_first_writer_raises_writes_no_document_and_is_not_counted(
    tmp_path, monkeypatch, capsys
):
    """The other half of DEC-47 (lens FA-N6's M19: a ledger commit moved above the write
    survived the suite at ``2adfaaa``). It inspects ``T*.html`` and the ledger; the
    compare still writes its JSON files (lens 2 FA-N2 measured ``run.json``,
    ``ingest_report.json``, ``compare_ingest_report.json`` and ``pseudonyms.json``)."""
    home = _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    monkeypatch.setattr(render_t2, "write_t2", _boom)
    monkeypatch.setattr(render_t7, "write_t7", _boom)
    out = tmp_path / "c"
    assert _compare(new, prior, crit, out, "--templates", "T2,T7") == EXIT_INTERNAL
    capsys.readouterr()
    assert not list(out.glob("T*.html"))
    assert _counts(home) == {}


# ------------------------------------------------------------------ FA-B1 / RG-B2


def _cell(sizes: list[int], successes: list[int]):
    ids = np.repeat(np.array([f"c{i}" for i in range(len(sizes))], dtype=object), sizes)
    ind = np.concatenate([np.arange(m) < y for m, y in zip(sizes, successes, strict=True)]).astype(
        bool
    )
    plan = plan_clustering("case_id", ids, ids.shape[0])
    return proportion_ci(ind, cell_key="lens", plan=plan, cluster_ids=ids)


def test_the_regression_lens_literal_draw_prints_the_bootstrap_not_wilson_deff():
    """RG-B2's one literal draw: a case of 40 rows with 20 successes beside nine one-row
    cases, all successes (n 49, k 29, 10 cases). At 2adfaaa: ``wilson_deff`` 0.5918
    [0.4275, 0.7379], route ``wilson_deff``. The largest case holds 40 / 49 of the rows."""
    cell = _cell([40] + [1] * 9, [20] + [1] * 9)
    num = cell.number
    assert (num.n, num.k, num.n_cases) == (49, 29, 10)
    assert num.method == "cluster_bootstrap_percentile"
    assert cell.detail["design_effect"]["route"] == "case_share_above_grid"
    assert "very_low_precision" in num.flags


def test_the_fresh_attack_lens_forty_case_shape_prints_the_bootstrap():
    """FA-B1's first shape: one case of 60 rows beside 39 of one row (40 cases, n 99); at
    2adfaaa it printed ``wilson_deff`` with no tier annotation on 4000 of 4000 draws."""
    cell = _cell([60] + [1] * 39, [54] + [1] * 35 + [0] * 4)
    assert cell.number.n_cases == 40 and cell.number.n == 99
    assert cell.number.method == "cluster_bootstrap_percentile"
    assert cell.detail["design_effect"]["route"] == "case_share_above_grid"


def test_the_t7_wilson_deff_sentence_names_where_it_prints_and_claims_no_coverage():
    from proofpack.render.t7 import METHOD_DESCRIPTIONS

    desc = METHOD_DESCRIPTIONS["wilson_deff"]
    assert "where its measured coverage is at or above" not in desc
    assert "no case holds more than a fifth of the rows" in desc
    assert "including the shapes where it fell below the 0.90 bar" in desc


# ------------------------------------------------------------------ FA-N1


@pytest.mark.parametrize(
    "licence",
    [
        pytest.param(None, id="no-licence"),
        pytest.param(["T1", "T7", "T8"], id="licence-without-compare"),
    ],
)
def test_run_templates_t2_without_a_compare_licence_names_the_licence_first(
    tmp_path, monkeypatch, capsys, licence
):
    if licence is None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("PROOFPACK_HOME", str(home))
    else:
        _home(tmp_path, monkeypatch, features=licence)
    new, prior, crit = _inputs(tmp_path)
    rc = _run(new, crit, tmp_path / "r", "--templates", "T2")
    printed = capsys.readouterr().out
    assert rc == (EXIT_LICENCE if licence is None else rc)
    lines = [ln for ln in printed.splitlines() if ln.startswith("Next step:")]
    assert lines == [
        "Next step: proofpack licence install FILE (a licence carrying the compare feature), "
        "then proofpack compare --input NEW --prior PRIOR --criteria FILE writes T2.html "
        "(docs: /docs/compare)"
    ]
    # the counter-example the lens ran: that compare under this licence writes no T2.html
    assert _compare(new, prior, crit, tmp_path / "c") == EXIT_LICENCE
    capsys.readouterr()
    assert not (tmp_path / "c" / "T2.html").exists()


# ------------------------------------------------------------------ FA-N4


@needs_extra
@pytest.mark.ap4
def test_compare_docx_note_for_t2_names_the_missing_docx_writer(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    out = tmp_path / "c"
    rc = _compare(new, prior, crit, out, "--format", "json,html,docx", "--templates", "T2,T7")
    printed = capsys.readouterr().out
    assert rc in (EXIT_OK, EXIT_WARNINGS), printed
    assert (out / "T2.html").exists() and not (out / "T2.docx").exists()
    assert "not built in this engine version" not in printed
    assert (
        "T2.docx not written: T2 has no DOCX writer in this engine version (it is written as "
        "T2.html under --format html)"
    ) in printed
