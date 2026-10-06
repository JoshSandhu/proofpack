"""E13 repair 3 (orchestrator, Tuesday 6 October 2026): blockers B2 and B3 of the lens-3
fresh-attack note (``handoffs/2026-10-05_E_e13_lens3_fresh-attack.md``). B1 (the F16
register-class lookup) is ``tests/test_f16_parity_native.py::``
``test_e13r3_b1_deleting_any_one_key_of_a_multi_key_value_is_a_miss``.

* B2: ``f13_recorded_outcome`` read only the 16 names of ``F13_NAMES``; a recorded pair
  outside them (the lens's ``"ndka auc (second capture)"``, 0.8 apart, ``within: false``)
  was never read, the command exited 0 and the reason typed "recorded 16 values".
* B3: T12's F13 Values cell printed ``n_values_compared`` (0) beside a largest deviation of
  2.78e-17 and a status saying this command recomputed the deviations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from proofpack import fixtures as fx
from proofpack.cli import main
from proofpack.render import t12

pytestmark = pytest.mark.day13

EXTRA = "ndka auc (second capture)"


def _capture_with(tmp_path: Path, monkeypatch, edit) -> Path:
    committed = fx.r_captures_dir()
    assert committed is not None
    d = tmp_path / "fixtures_r"
    d.mkdir()
    for p in committed.iterdir():
        if p.is_file():
            (d / p.name).write_bytes(p.read_bytes())
    path = d / "f13_engine_comparison.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    edit(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(fx, "r_captures_dir", lambda: d)
    monkeypatch.delenv(fx.R_VECTORS_ENV, raising=False)
    return d


def _f13(report: dict) -> dict:
    return next(r for r in report["rows"] if r["id"] == "F13")


def test_e13r3_b2_a_recorded_name_outside_the_16_is_not_matched_and_named(tmp_path, monkeypatch):
    def add(doc):
        doc["values"][EXTRA] = {
            "engine": 0.1,
            "r": 0.9,
            "tolerance": 1e-6,
            "abs_deviation": 0.8,
            "within": False,
        }

    _capture_with(tmp_path, monkeypatch, add)
    row = _f13(fx.run_fixtures(doctor=False))
    assert row["status"] == "not_matched", row["reason"]
    assert EXTRA in row["reason"]


def test_e13r3_b2_the_cli_exits_6_on_a_recorded_name_outside_the_16(tmp_path, monkeypatch, capsys):
    _capture_with(
        tmp_path, monkeypatch, lambda doc: doc["values"].__setitem__(EXTRA, {"engine": 0.5})
    )
    rc = main(["fixtures", "--offline", "--out", str(tmp_path / "out")])
    assert rc == 6, capsys.readouterr()


def test_e13r3_b2_the_reason_counts_the_values_it_recomputed(report_committed):
    """The committed capture: 16 names recomputed, and the reason's count is that count."""
    row = _f13(report_committed)
    assert row["status"] == "suite_only"
    assert re.search(r"recorded (\d+) values", row["reason"]).group(1) == str(len(fx.F13_NAMES))


def test_e13r3_b3_the_t12_values_cell_of_f13_prints_the_recomputed_count(report_committed):
    page = t12.render_t12(report_committed)
    tr = re.search(r'<tr data-row="F13">(.*?)</tr>', page, re.S).group(1)
    nums = re.findall(r'<td class="num">([^<]*)</td>', tr)
    assert nums == [str(len(fx.F13_NAMES))], nums
    assert t12.SUITE_ONLY_RECORDED_TEXT in tr
    # the report itself keeps n_values_compared 0 (the schema's suite_only rule)
    assert _f13(report_committed)["n_values_compared"] == 0


def test_e13r3_b3_a_not_matched_f13_row_prints_n_values_compared(tmp_path, monkeypatch):
    _capture_with(tmp_path, monkeypatch, lambda doc: doc["values"].pop(fx.F13_NAMES[0]))
    report = fx.run_fixtures(doctor=False)
    assert _f13(report)["status"] == "not_matched"
    assert t12.values_cell(_f13(report)) == _f13(report)["n_values_compared"]


@pytest.fixture(scope="module")
def report_committed() -> dict:
    return fx.run_fixtures(doctor=False)
