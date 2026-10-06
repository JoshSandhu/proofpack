"""E13 repair 4 (orchestrator, Tuesday 6 October 2026): the two blockers of the lens-4
fresh-attack note (``handoffs/2026-10-06_E_e13_lens4_fresh-attack.md``).

* L4-B1: ``load_r_captures`` read each file with plain ``json.loads``, which keeps the last
  copy of a repeated key; a bad ``"s100b auc"`` pair placed before the real one was never
  read and the command exited 0 with F13 ``suite_only``. A repeated key in any object of an
  R capture file now makes the file unreadable (``DuplicateJSONKeyError``).
* L4-B2: "two or three entries" in ``parity.py`` was false (9 values equal two, 8 three
  and 2 four); pinned in ``tests/test_f16_parity_native.py::``
  ``test_e13r3_b1_deleting_any_one_key_of_a_multi_key_value_is_a_miss``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proofpack import fixtures as fx
from proofpack.cli import main

pytestmark = pytest.mark.day13

REPO = Path(__file__).resolve().parent.parent
BAD_PAIR = '"s100b auc": {"engine": 0.1, "r": 0.9, "tolerance": 1e-06}, '


def _copy_capture(tmp_path: Path, monkeypatch) -> Path:
    committed = fx.r_captures_dir()
    assert committed is not None
    d = tmp_path / "fixtures_r"
    d.mkdir()
    for p in committed.iterdir():
        if p.is_file():
            (d / p.name).write_bytes(p.read_bytes())
    monkeypatch.setattr(fx, "r_captures_dir", lambda: d)
    monkeypatch.delenv(fx.R_VECTORS_ENV, raising=False)
    return d


def _plant_first(path: Path, inside: str, text: str) -> None:
    raw = path.read_text(encoding="utf-8")
    i = raw.index(inside) + len(inside)
    path.write_text(raw[:i] + text + raw[i:], encoding="utf-8")


def _f13(report: dict) -> dict:
    return next(r for r in report["rows"] if r["id"] == "F13")


def test_e13r4_b1_a_repeated_pair_before_the_real_one_is_not_matched(tmp_path, monkeypatch):
    """The lens's plant: a bad ``"s100b auc"`` pair first in ``values``. At b672c32 F13 was
    ``suite_only`` and the reason said 16 values were recorded."""
    d = _copy_capture(tmp_path, monkeypatch)
    _plant_first(d / "f13_engine_comparison.json", '"values": {', BAD_PAIR)
    caps = fx.load_r_captures(d, vectors=None)
    assert ("f13_engine_comparison.json", "DuplicateJSONKeyError") in [
        (Path(f).name, e) for f, e in caps.unreadable
    ]
    row = _f13(fx.run_fixtures(doctor=False))
    assert row["status"] == "not_matched", row["reason"]


def test_e13r4_b1_the_cli_exits_6_on_a_repeated_pair(tmp_path, monkeypatch, capsys):
    d = _copy_capture(tmp_path, monkeypatch)
    _plant_first(d / "f13_engine_comparison.json", '"values": {', BAD_PAIR)
    rc = main(["fixtures", "--offline", "--out", str(tmp_path / "out")])
    assert rc == 6, capsys.readouterr()


@pytest.mark.parametrize("name", ["proc_asah.json", "rms_val_prob_f4.json"])
def test_e13r4_b1_a_repeated_top_level_key_makes_each_capture_file_unreadable(
    tmp_path, monkeypatch, name
):
    d = _copy_capture(tmp_path, monkeypatch)
    _plant_first(d / name, "{", '"schema": "planted", ')
    caps = fx.load_r_captures(d, vectors=None)
    assert (name, "DuplicateJSONKeyError") in [(Path(f).name, e) for f, e in caps.unreadable]


def test_e13r4_the_committed_capture_files_have_no_repeated_key():
    caps = fx.load_r_captures(vectors=None)
    assert caps.unreadable == ()
    assert caps.proc is not None and caps.valprob is not None and caps.comparison is not None


def test_e13r4_b2_the_false_count_sentence_is_gone():
    text = (REPO / "src" / "proofpack" / "parity.py").read_text(encoding="utf-8")
    flat = " ".join(text.split())
    assert "the 67 values equal two or three entries" not in flat
    assert "9 equal two, 8 three and 2 four" in flat
