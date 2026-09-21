"""Build day 7 (E7): ``io.ledger`` - the local count of acceptance runs per test set.

Every key is recomputed here from the module's documented byte recipe with ``hashlib``
directly (labels joined by ``\\n``, ``0x00``, little-endian float64 score bytes), so a
change to the recipe fails against this file rather than against itself.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from proofpack.errors import FLAG_ONLY_CODES, WARN_CODES
from proofpack.io import ledger

pytestmark = pytest.mark.day7


def test_the_key_is_the_documented_bytes():
    y = ["1", "0", "1"]
    s = np.array([0.9, 0.2, 0.7])
    hand = hashlib.sha256(b"1\n0\n1" + b"\x00" + s.astype("<f8").tobytes()).hexdigest()
    assert ledger.test_set_key(y, s) == hand
    assert ledger.test_set_key(np.array(y, dtype=object), s) == hand
    # a y_pred-only table
    hand2 = hashlib.sha256(b"1\n0\n1" + b"\x00" + b"y_pred\n1\n1\n0").hexdigest()
    assert ledger.test_set_key(y, None, ["1", "1", "0"]) == hand2


def test_row_order_and_any_score_change_move_the_key():
    y = ["1", "0", "1", "0"]
    s = np.array([0.9, 0.2, 0.7, 0.1])
    k = ledger.test_set_key(y, s)
    assert ledger.test_set_key(y[::-1], s[::-1]) != k
    s2 = s.copy()
    s2[3] = 0.1000001
    assert ledger.test_set_key(y, s2) != k
    assert ledger.test_set_key(y, s) == k  # and the same inputs give the same key again


def test_the_count_increments_only_for_runs_with_criteria(tmp_path: Path):
    key = "a" * 64
    r = ledger.record_run(key, has_criteria=False, limit=3, home=tmp_path)
    assert (r.count, r.warning) == (0, None) and not ledger.ledger_path(tmp_path).exists()
    for expected in (1, 2, 3):
        r = ledger.record_run(key, has_criteria=True, limit=3, home=tmp_path)
        assert r.count == expected and r.warning is None, expected
    r = ledger.record_run(key, has_criteria=True, limit=3, home=tmp_path)
    assert r.count == 4 and r.warning is not None
    assert r.warning.code == "W14" and r.warning.detail == {"count": 4, "limit": 3}
    # a run without criteria reads the count without moving it
    r = ledger.record_run(key, has_criteria=False, limit=3, home=tmp_path)
    assert r.count == 4 and r.warning is not None
    # another key is counted apart
    r = ledger.record_run("b" * 64, has_criteria=True, limit=3, home=tmp_path)
    assert r.count == 1 and r.warning is None
    body = json.loads(ledger.ledger_path(tmp_path).read_text(encoding="utf-8"))
    assert body == {"schema": ledger.LEDGER_SCHEMA, "counts": {key: 4, "b" * 64: 1}}


def test_no_limit_means_no_warning_ever(tmp_path: Path):
    key = "c" * 64
    for _ in range(50):
        r = ledger.record_run(key, has_criteria=True, limit=None, home=tmp_path)
        assert r.warning is None
    assert r.count == 50 and r.as_dict() == {
        "test_set_sha256": key,
        "acceptance_runs": 50,
        "warn_limit": None,
        "counted": True,
    }


def test_the_warning_fires_strictly_above_the_limit(tmp_path: Path):
    key = "d" * 64
    for i in range(1, 6):
        r = ledger.record_run(key, has_criteria=True, limit=5, home=tmp_path)
        assert r.warning is None, i
    r = ledger.record_run(key, has_criteria=True, limit=5, home=tmp_path)
    assert r.warning is not None and r.count == 6


def test_an_unreadable_ledger_is_w15_and_the_count_unknown(tmp_path: Path):
    path = ledger.ledger_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json", encoding="utf-8")
    r = ledger.record_run("e" * 64, has_criteria=True, limit=3, home=tmp_path)
    assert r.count is None and r.warning is not None and r.warning.code == "W15"
    assert r.as_dict()["counted"] is False and r.as_dict()["acceptance_runs"] is None
    path.write_text(json.dumps({"schema": "x", "counts": {"k": -1}}), encoding="utf-8")
    r = ledger.record_run("e" * 64, has_criteria=True, limit=3, home=tmp_path)
    assert r.warning is not None and r.warning.code == "W15"
    # a directory where the file should be: OSError on write
    path.unlink()
    path.mkdir()
    r = ledger.record_run("e" * 64, has_criteria=True, limit=3, home=tmp_path)
    assert r.warning is not None and r.warning.code == "W15"


def test_the_codes_are_registered_and_w14_is_flag_only():
    assert "W14" in WARN_CODES and "W15" in WARN_CODES
    assert "W14" in FLAG_ONLY_CODES


def test_the_ledger_lives_in_the_per_user_home_not_beside_a_pack(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PROOFPACK_HOME", str(tmp_path / "h"))
    assert ledger.ledger_path() == tmp_path / "h" / "ledger.json"
    monkeypatch.delenv("PROOFPACK_HOME")
    from proofpack.home import home_dir

    p = ledger.ledger_path()
    assert p.parent == home_dir() and p.name == "ledger.json"
    assert "pack" not in p.parts
