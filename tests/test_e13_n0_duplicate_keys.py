"""E13 lens 5 N0 (orchestrator follow-up, Tuesday 6 October 2026): repeated JSON keys in the
F1-F8 oracle files and the committed F16 parity file.

Repair 4 refused a repeated key in the three R capture files only. Lens 5 planted
``"wilson_lo": 0.9,`` before the real ``wilson_lo`` in ``oracles_v1.json``: ``json.loads``
kept the last copy, F1-wilson stayed ``matched`` and ``fixtures --offline`` exited 0. The
oracle files and the parity file are now read with the same hook; a repeated key makes the
file unreadable and every row citing it ``not_matched``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proofpack import fixtures as fx
from proofpack import parity
from proofpack.cli import main

pytestmark = pytest.mark.day13

REPO = Path(__file__).resolve().parent.parent


def _planted_copy(tmp_path: Path, src: Path, anchor: str, text: str) -> Path:
    raw = src.read_text(encoding="utf-8")
    i = raw.index(anchor)
    out = tmp_path / src.name
    out.write_text(raw[:i] + text + raw[i:], encoding="utf-8")
    return out


def _redirect(monkeypatch, name: str, path: Path) -> None:
    real = fx.resource_path
    monkeypatch.setattr(fx, "resource_path", lambda n: path if n == name else real(n))


def test_e13n0_a_repeated_wilson_lo_before_the_real_one_is_unreadable(tmp_path, monkeypatch):
    src = fx.resource_path("oracles_v1.json")
    planted = _planted_copy(tmp_path, src, '"wilson_lo"', '"wilson_lo": 0.9,\n    ')
    _redirect(monkeypatch, "oracles_v1.json", planted)
    oracles = fx.load_oracles()
    assert oracles.unreadable.get("oracles_v1.json") == "DuplicateJSONKeyError"
    report = fx.run_fixtures(doctor=False)
    wilson = [r for r in report["rows"] if r["id"].startswith("F1") and "wilson" in r["id"]]
    assert wilson and all(r["status"] == "not_matched" for r in wilson), wilson


def test_e13n0_the_cli_exits_6_on_a_repeated_oracle_key(tmp_path, monkeypatch, capsys):
    src = fx.resource_path("oracles_v1.json")
    planted = _planted_copy(tmp_path, src, '"wilson_lo"', '"wilson_lo": 0.9,\n    ')
    _redirect(monkeypatch, "oracles_v1.json", planted)
    rc = main(["fixtures", "--offline", "--out", str(tmp_path / "out")])
    assert rc == 6, capsys.readouterr()


@pytest.mark.parametrize("name", ["f4_expected.json", fx.NEWCOMBE_PAIRED_FILE])
def test_e13n0_a_repeated_top_level_key_makes_each_oracle_file_unreadable(
    tmp_path, monkeypatch, name
):
    raw = fx.resource_path(name).read_text(encoding="utf-8")
    i = raw.index("{") + 1
    planted = tmp_path / name
    planted.write_text(raw[:i] + '"planted": 1, "planted": 2, ' + raw[i:], encoding="utf-8")
    _redirect(monkeypatch, name, planted)
    assert fx.load_oracles().unreadable.get(name) == "DuplicateJSONKeyError"


def test_e13n0_a_repeated_key_in_the_committed_parity_file_is_not_matched(tmp_path, monkeypatch):
    (tmp_path / "fixtures").mkdir()
    src = REPO / parity.COMMITTED_FILE
    raw = src.read_text(encoding="utf-8")
    i = raw.index('"fixtures"')
    (tmp_path / parity.COMMITTED_FILE).write_text(
        raw[:i] + '"fixtures": {}, ' + raw[i:], encoding="utf-8"
    )
    monkeypatch.setattr(fx, "source_checkout_root", lambda: tmp_path)
    out = fx.f16_behaviour()
    assert out["status"] == "not_matched", out["reason"]
    assert "DuplicateJSONKeyError" in out["reason"]


def test_e13n0_the_committed_oracle_and_parity_files_have_no_repeated_key():
    assert fx.load_oracles().unreadable == {}
    assert fx.f16_behaviour()["status"] != "not_matched"
