"""E13 lens 5 N0 (orchestrator follow-up, Tuesday 6 October 2026): repeated JSON keys in the
F1-F8 oracle files and the committed F16 parity file.

Repair 4 refused a repeated key in the three R capture files only. Lens 5 planted
``"wilson_lo": 0.9,`` before the real ``wilson_lo`` in ``oracles_v1.json``: ``json.loads``
kept the last copy, F1-wilson stayed ``matched`` and ``fixtures --offline`` exited 0. The
oracle files and the parity file are now read with the same hook; a repeated key makes the
file unreadable and every row citing it ``not_matched``.
"""

from __future__ import annotations

import json
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


# --------------------------------------------- N0 lens B1: repeated entries inside a list


def _redirect_doc(monkeypatch, tmp_path, name: str, edit) -> None:
    doc = json.loads(fx.resource_path(name).read_text(encoding="utf-8"))
    edit(doc)
    path = tmp_path / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    _redirect(monkeypatch, name, path)


def _row(report: dict, rid: str) -> dict:
    return next(r for r in report["rows"] if r["id"] == rid)


def test_e13n0_b1_a_repeated_paired_row_placed_first_is_not_matched(tmp_path, monkeypatch):
    """A second ``e 36 f 12 g 2 h 0`` row with 0.9/0.9 placed first in ``rows``: at
    36bfb2b ``dict()`` kept the real row and F5-newcombe-paired stayed matched, exit 0."""

    def edit(doc):
        bad = dict(doc["rows"][0], method10={"lower": 0.9, "upper": 0.9})
        doc["rows"].insert(0, bad)

    _redirect_doc(monkeypatch, tmp_path, fx.NEWCOMBE_PAIRED_FILE, edit)
    row = _row(fx.run_fixtures(doctor=False), "F5-newcombe-paired")
    assert row["status"] == "not_matched", row["reason"]
    assert "appears twice" in row["reason"]


def test_e13n0_b1_a_repeated_newcombe_example_placed_first_is_not_matched(tmp_path, monkeypatch):
    root = fx.source_checkout_root()
    assert root is not None
    doc = json.loads((root / "fixtures" / fx.NEWCOMBE_FILE).read_text(encoding="utf-8"))
    bad = dict(doc["examples"][0])
    for m in ("method10", "method11"):
        bad[m] = {"lower": 0.9, "upper": 0.9}
    doc["examples"].insert(0, bad)
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "fixtures" / fx.NEWCOMBE_FILE).write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(fx, "source_checkout_root", lambda: tmp_path)
    row = _row(fx.run_fixtures(doctor=False), "F14-newcombe")
    assert row["status"] == "not_matched", row["reason"]
    assert "appears twice" in row["reason"]


def test_e13n0_b1_values_written_as_a_list_of_pairs_is_not_matched(tmp_path, monkeypatch):
    """F1-wilson's ``values`` as ``[["wilson_lo", 0.9], ..., ["wilson_lo", <real>]]``: at
    36bfb2b ``dict()`` kept the last pair and F1-wilson stayed matched."""

    def edit(doc):
        real = doc["captured"]["F1-wilson"]["values"]
        doc["captured"]["F1-wilson"]["values"] = [["wilson_lo", 0.9]] + [
            [k, v] for k, v in real.items()
        ]

    _redirect_doc(monkeypatch, tmp_path, "oracles_v1.json", edit)
    row = _row(fx.run_fixtures(doctor=False), "F1-wilson")
    assert row["status"] == "not_matched", row["reason"]
    assert "not an object" in row["reason"]


def test_e13n0_b1_a_register_entry_written_as_a_list_is_not_matched(tmp_path, monkeypatch):
    def edit(doc):
        doc["register"]["F2"] = [[k, v] for k, v in doc["register"]["F2"].items()]

    _redirect_doc(monkeypatch, tmp_path, "oracles_v1.json", edit)
    report = fx.run_fixtures(doctor=False)
    row = _row(report, "F2-register")
    assert row["status"] == "not_matched", row["reason"]
    assert "oracle_entry_malformed: register.F2 is a JSON array, not an object" in row["reason"]


# --------------------------------------------- N0 lens 2: B1 near-copies, B2 reason words


@pytest.mark.parametrize(
    "plant",
    [
        {"method10": {"lower ": 0.9, "upper ": 0.9}},
        {"method10": {"Lower": 0.9, "Upper": 0.9}},
        {"method10": {}, "method10 ": {"lower": 0.9, "upper": 0.9}},
    ],
    ids=["trailing_space_sides", "capitalised_sides", "second_method10_key"],
)
def test_e13n0_r2_b1_a_paired_row_with_unknown_fields_is_not_matched(tmp_path, monkeypatch, plant):
    """A second ``e 36 f 12 g 2 h 0`` row placed first whose sides or method key are spelt
    otherwise: at ad028a6 ``_paired_rows`` skipped it, 0.9 was never compared, and
    F5-newcombe-paired stayed matched (exit 0)."""

    def edit(doc):
        base = {k: doc["rows"][0][k] for k in ("e", "f", "g", "h")}
        doc["rows"].insert(0, {**base, **plant})

    _redirect_doc(monkeypatch, tmp_path, fx.NEWCOMBE_PAIRED_FILE, edit)
    row = _row(fx.run_fixtures(doctor=False), "F5-newcombe-paired")
    assert row["status"] == "not_matched", row["reason"]
    assert row["reason"].startswith("oracle_entry_malformed: newcombe1998_paired.json rows[0]")


@pytest.mark.parametrize(
    "value,json_type",
    [([["wilson_lo", 0.25], ["wilson_hi", 0.36]], "array"), (None, "null"), ("x", "string")],
    ids=["distinct_pairs", "null", "string"],
)
def test_e13n0_r2_b2_a_non_object_entry_names_its_json_type_and_is_not_called_ambiguous(
    tmp_path, monkeypatch, value, json_type
):
    def edit(doc):
        doc["captured"]["F1-wilson"]["values"] = value

    _redirect_doc(monkeypatch, tmp_path, "oracles_v1.json", edit)
    row = _row(fx.run_fixtures(doctor=False), "F1-wilson")
    assert row["status"] == "not_matched"
    assert row["reason"] == (
        f"oracle_entry_malformed: captured.F1-wilson.values is a JSON {json_type}, not an object"
    )
    assert "ambiguous" not in row["reason"]


def test_e13n0_r2_b2_a_repeated_entry_says_repeated(tmp_path, monkeypatch):
    def edit(doc):
        doc["rows"].insert(0, dict(doc["rows"][0], method10={"lower": 0.9, "upper": 0.9}))

    _redirect_doc(monkeypatch, tmp_path, fx.NEWCOMBE_PAIRED_FILE, edit)
    row = _row(fx.run_fixtures(doctor=False), "F5-newcombe-paired")
    assert row["reason"].startswith("oracle_entry_repeated: newcombe1998_paired.json rows: ")


@pytest.mark.parametrize(
    "value,json_type", [({"a": 1}, "object"), ("rows", "string")], ids=["object", "string"]
)
def test_e13n0_r3_b1_rows_that_is_not_an_array_is_named_as_such(
    tmp_path, monkeypatch, value, json_type
):
    """At edf3ddf the reason named ``rows[0]``, which does not exist (lens 3 B1)."""

    def edit(doc):
        doc["rows"] = value

    _redirect_doc(monkeypatch, tmp_path, fx.NEWCOMBE_PAIRED_FILE, edit)
    row = _row(fx.run_fixtures(doctor=False), "F5-newcombe-paired")
    assert row["status"] == "not_matched"
    assert row["reason"] == (
        f"oracle_entry_malformed: newcombe1998_paired.json rows is a JSON {json_type}, not an array"
    )
