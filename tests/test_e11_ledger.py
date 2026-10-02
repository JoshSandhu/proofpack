"""Build day 11 (E11) item 2, DEC-70 (b) with DEC-47: one ledger limit.

* A comparison that wrote a document is a run: ``compare`` increments the **same** counter
  ``run`` does (the SHA-256 of the analysed new table's ``y_true`` and score), against the
  one declaration ``ledger.warn_after_acceptance_runs``. Literal: two ``run`` and one
  ``compare`` on the F5 new table -> ``ledger.json`` counts ``{key: 3}``; the compare's
  manifest ``ledger_count`` is 3 and its ``comparison.ledger.prior_acceptance_runs`` 2.
  At ``ad66073`` the compare was counted under ``compare:<sha256>`` (``{key: 2,
  compare:key: 1}``).
* A run that wrote no document is not counted (DEC-47): no licence (exit 4), a licence
  without the ``compare`` feature (exit 4; row 148, lens 3 FA-N2), ``--format json``,
  ``run --templates T2``. At ``ad66073`` each of those counted.
* The count is recorded after the write: a writer that raises leaves ``ledger.json`` as it
  was (exit 5).
* Row 143: with no ``ledger`` block the T2 section-7 sentence and ``LEDGER_STATEMENT`` end
  ``(ledger.warn_after_acceptance_runs): none declared.``; at ``ad66073`` they read
  ``... is no limit declared.``
* The sentences say a comparison counts as a run (T2 section 7, ``LEDGER_STATEMENT``,
  ``LEDGER_WARNING``).
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pytest

from conftest import ephemeral_registry
from proofpack.cli import main
from proofpack.errors import EXIT_INTERNAL, EXIT_LICENCE, EXIT_OK, EXIT_WARNINGS
from test_e10_compare_cli import _compare, _home, _inputs, f5_criteria

pytestmark = pytest.mark.day11

COUNTS_AS_RUN = "(a version comparison that wrote a document counts as a run)"


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


def test_two_runs_and_one_compare_on_the_same_table_count_three_on_one_key(
    tmp_path, monkeypatch, capsys
):
    home = _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    for i in (1, 2):
        assert _run(new, crit, tmp_path / f"r{i}") in (EXIT_OK, EXIT_WARNINGS)
        assert (tmp_path / f"r{i}" / "T8.html").exists()
    key = _doc(tmp_path / "r1")["ledger"]["test_set_sha256"]
    assert _counts(home) == {key: 2}
    assert _compare(new, prior, crit, tmp_path / "c") in (EXIT_OK, EXIT_WARNINGS)
    doc = _doc(tmp_path / "c")
    assert doc["ledger"]["test_set_sha256"] == key
    assert _counts(home) == {key: 3}
    assert doc["manifest"]["ledger_count"] == 3 and doc["ledger"]["acceptance_runs"] == 3
    assert doc["comparison"]["ledger"]["prior_acceptance_runs"] == 2
    # a run after the compare reads the compare: 4, against the one declared limit (3)
    assert _run(new, crit, tmp_path / "r3") == EXIT_WARNINGS
    after = _doc(tmp_path / "r3")
    assert after["manifest"]["ledger_count"] == 4 and _counts(home) == {key: 4}
    assert [w["params"] for w in after["warnings"] if w["code"] == "W14"] == [
        {"count": 4, "limit": 3}
    ]
    capsys.readouterr()


def test_a_compare_at_the_limit_carries_the_warning_and_the_banner(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    for i in range(3):
        assert _run(new, crit, tmp_path / f"r{i}") in (EXIT_OK, EXIT_WARNINGS)
    assert _compare(new, prior, crit, tmp_path / "c") == EXIT_WARNINGS
    doc = _doc(tmp_path / "c")
    led = doc["comparison"]["ledger"]
    assert (led["prior_acceptance_runs"], led["warn_limit"], led["limit_reached"]) == (3, 3, True)
    assert [w["code"] for w in doc["warnings"]] == ["W14"]
    page = html.unescape((tmp_path / "c" / "T2.html").read_text(encoding="utf-8"))
    assert "version comparisons included, has reached or exceeded" in page
    assert len(_counts(home)) == 1


@pytest.mark.parametrize(
    "case",
    ["no_licence", "licence_without_compare", "format_json", "run_templates_t2", "compare_json"],
)
def test_a_run_or_compare_that_wrote_no_document_is_not_counted(
    tmp_path, monkeypatch, capsys, case
):
    if case == "no_licence":
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("PROOFPACK_HOME", str(home))
    elif case == "licence_without_compare":
        home = _home(tmp_path, monkeypatch, features=["T1", "T7", "T8"])
    else:
        home = _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    out = tmp_path / "out"
    if case in ("no_licence", "format_json", "run_templates_t2"):
        flags = {
            "no_licence": (),
            "format_json": ("--format", "json"),
            "run_templates_t2": ("--templates", "T2"),
        }[case]
        rc = _run(new, crit, out, *flags)
    else:
        flags = ("--format", "json") if case == "compare_json" else ()
        rc = _compare(new, prior, crit, out, *flags)
    if case in ("no_licence", "licence_without_compare"):
        assert rc == EXIT_LICENCE
    else:
        assert rc in (EXIT_OK, EXIT_WARNINGS)
    assert {p.suffix for p in out.iterdir()} == {".json"}
    assert _counts(home) == {}, case
    doc = _doc(out)
    # the document carries the count it was not part of: the stored count, 0
    assert doc["manifest"]["ledger_count"] == 0 and doc["ledger"]["acceptance_runs"] == 0
    capsys.readouterr()


def test_two_compares_with_a_licence_without_compare_leave_the_ledger_empty(
    tmp_path, monkeypatch, capsys
):
    """Lens 3 FA-N2's literal (row 148): two such compares left ``{"compare:...": 2}``."""
    home = _home(tmp_path, monkeypatch, features=["T1", "T7", "T8"])
    new, prior, crit = _inputs(tmp_path)
    for i in (1, 2):
        assert _compare(new, prior, crit, tmp_path / f"c{i}") == EXIT_LICENCE
    assert _counts(home) == {}
    capsys.readouterr()


def test_the_count_is_recorded_after_the_write(tmp_path, monkeypatch, capsys):
    home = _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    assert _run(new, crit, tmp_path / "r1") in (EXIT_OK, EXIT_WARNINGS)
    before = _counts(home)
    assert list(before.values()) == [1]
    from proofpack.render import html as render_html

    def boom(document, out_dir):
        raise OSError("disk full (planted)")

    monkeypatch.setattr(render_html, "write_t8", boom)
    monkeypatch.setattr("proofpack.run.write_t8", boom, raising=False)
    assert _run(new, crit, tmp_path / "r2") == EXIT_INTERNAL
    assert "disk full (planted)" in capsys.readouterr().err
    assert _counts(home) == before
    assert not (tmp_path / "r2" / "T8.html").exists()


def test_no_ledger_block_reads_none_declared_in_the_sentence_and_section_7(
    tmp_path, monkeypatch, capsys
):
    _home(tmp_path, monkeypatch)
    crit_data = f5_criteria()
    crit_data.pop("ledger")
    new, prior, crit = _inputs(tmp_path, crit_data)
    assert _compare(new, prior, crit, tmp_path / "c") == EXIT_OK
    page = html.unescape((tmp_path / "c" / "T2.html").read_text(encoding="utf-8"))
    text = re.sub(r"<[^>]+>", "", page)
    assert "no limit declared" not in text
    hits = re.findall(
        r"This test set (?:\(SHA-256 [0-9a-f]{12}\) )?has been used in 0 prior acceptance runs "
        r"recorded in the local ledger \(a version comparison that wrote a document counts as "
        r"a run\); the manufacturer's declared limit on those runs "
        r"\(ledger\.warn_after_acceptance_runs\): none declared\.",
        text,
    )
    assert len(hits) == 2, hits  # the section-7 paragraph and the LEDGER_STATEMENT claim
    capsys.readouterr()


def test_the_three_ledger_texts_say_a_comparison_counts_as_a_run():
    from proofpack.narrate.templates import LIBRARY

    root = Path(__file__).resolve().parent.parent
    t2 = (root / "src" / "proofpack" / "templates" / "T2.html").read_text(encoding="utf-8")
    assert COUNTS_AS_RUN in LIBRARY["LEDGER_STATEMENT"].skeleton
    assert "version comparisons included" in LIBRARY["LEDGER_WARNING"].skeleton
    assert COUNTS_AS_RUN in t2 and "version comparisons included" in t2
    for text in (LIBRARY["LEDGER_STATEMENT"].skeleton, t2):
        assert "prior version comparisons" not in text
    assert "warn_after_comparisons" not in t2


def test_record_run_is_peek_then_commit(tmp_path):
    from proofpack.io import ledger

    key = "a" * 64
    peeked = ledger.peek(key, counts_this_run=True, limit=1, home=tmp_path)
    assert (peeked.stored, peeked.count, peeked.pending) == (0, 1, True)
    assert not (tmp_path / "ledger.json").exists()
    assert ledger.commit(peeked) is None
    assert ledger.peek(key, counts_this_run=False, limit=1, home=tmp_path).count == 1
    again = ledger.record_run(key, has_criteria=True, limit=1, home=tmp_path)
    assert again.count == 2 and again.warning.code == "W14"
