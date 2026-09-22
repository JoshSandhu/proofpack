"""Build day 8, lane A (A-P2): fixture F19 and the egress rules (D1 section 6).

F19 (D1 section 3.2): *run with an intersectional cell n=7, events=2 and site names "St
Mary's"; telemetry payload validates against egress_schema.json; no key outside whitelist;
cell suppressed; "St Mary's" absent from every egress byte*. The cohort here is
``conftest.make_cohort`` (seed 20240101, 400 rows) with the site column rewritten so that
``St Mary's`` holds exactly 7 rows with 2 events, ``Königsberg`` (non-ASCII) and ``Site A``
(a name that reads like a pseudonym) hold 60 rows each and ``Royal Free`` the rest, plus a
free-text column ``clinician_note`` the mapper ignores (an original header and a value that
must never be serialised). Every run goes through ``proofpack.cli.main`` with a recording
transport in place of ``urllib``; the bytes asserted on are the serialised payloads and
the bytes that transport captured.

The engine has no intersectional (two-attribute) cell at 7b2ca2a; the n = 7 cell is the
``site`` level ``St Mary's``, which is the smallest cell the document tabulates.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from conftest import (
    NETWORK_ATTEMPTS,
    confirmed_mapping,
    ephemeral_registry,
    make_cohort,
    make_criteria,
    write_csv,
    write_licence,
    write_yaml,
)
from proofpack import egress
from proofpack.egress import build as build_mod
from proofpack.egress import pseudonymise, suppress, telemetry, whitelist
from proofpack.errors import (
    EXIT_HALT,
    EXIT_OK,
    FLAG_ONLY_CODES,
    HALT_CODES,
    MAPPING_CODES,
    SCHEMA_CODES,
    WARN_CODES,
    HaltError,
)
from proofpack.manifest import REFERENCE_PLATFORM, canonical_json, platform_tag
from proofpack.resources import load_json_schema
from test_criteria import FAIRNESS

pytestmark = [pytest.mark.day8, pytest.mark.ap2]

REPO = Path(__file__).resolve().parent.parent
ST_MARYS = "St Mary's"
KONIGSBERG = "Königsberg"
SITE_A = "Site A"
ROYAL_FREE = "Royal Free"
NOTE_HEADER = "clinician_note"
NOTE_VALUE = "seen in clinic on Tuesday"


def f19_cohort() -> dict[str, list[Any]]:
    cols = make_cohort(n=400)
    site = [ROYAL_FREE] * 400
    for i in range(0, 7):
        site[i] = ST_MARYS
    for i in range(7, 67):
        site[i] = KONIGSBERG
    for i in range(67, 127):
        site[i] = SITE_A
    cols["site"] = site
    for i in range(7):  # St Mary's: 2 events, 5 non-events
        cols["y_true"][i] = "1" if i < 2 else "0"
    cols[NOTE_HEADER] = [NOTE_VALUE] * 400
    return cols


def f19_criteria(**egress_overrides: Any) -> dict[str, Any]:
    crit = make_criteria(fairness=copy.deepcopy(FAIRNESS))
    crit["egress"] = {
        "telemetry": True,
        "suppression": {"min_n": 10, "min_events": 5, "min_nonevents": 5},
    }
    crit["egress"].update(egress_overrides)
    return crit


class Recorder:
    """A transport that records what it was handed and answers a fixed status."""

    def __init__(self, status: int = 204, out_dir: Path | None = None) -> None:
        self.status = status
        self.calls: list[dict[str, Any]] = []
        self.out_dir = out_dir

    def __call__(self, url: str, body: bytes, timeout: float) -> int:
        entry = {"url": url, "body": body, "timeout": timeout}
        if self.out_dir is not None:
            target = self.out_dir / "run.json"
            entry["run_json_exists"] = target.exists()
            if target.exists():
                entry["run_json_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
        self.calls.append(entry)
        return self.status


def prepare(
    tmp_path: Path, monkeypatch, crit=None, licence: bool = True
) -> tuple[Path, Path, Path]:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("PROOFPACK_HOME", str(home))
    if licence:
        write_licence(home / "proofpack.lic")
    csv_path = write_csv(tmp_path / "test.csv", f19_cohort())
    yml = write_yaml(tmp_path / "criteria.yaml", crit if crit is not None else f19_criteria())
    confirmed_mapping(csv_path)
    return csv_path, yml, tmp_path / "pack"


def run_cli(csv_path, yml, out, *flags, transport=None, registry="ephemeral") -> int:
    from proofpack.cli import main

    reg = ephemeral_registry() if registry == "ephemeral" else registry
    return main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), *flags],
        registry=reg,
        transport=transport,
    )


@pytest.fixture
def f19(tmp_path: Path, monkeypatch, capsys):
    """One F19 run with telemetry on and a 204 recorder: ``(doc, aggregates, pmap, rec,
    out, printed)``."""
    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    rec = Recorder(204, out)
    rc = run_cli(csv_path, yml, out, transport=rec)
    printed = capsys.readouterr().out
    assert rc == EXIT_OK, printed
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    thresholds = egress.thresholds_from_declarations(doc["declarations"].get("egress"))
    agg, pmap = egress.build_aggregates(doc, thresholds)
    return doc, agg, pmap, rec, out, printed


def walk(value: Any, path: str = "$"):
    """Yield ``(path, key)`` for every dict key and ``(path, value)`` for every string."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield path, k
            yield from walk(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk(v, f"{path}[{i}]")


# ------------------------------------------------------------------ the payloads validate


def test_f19_the_telemetry_payload_validates_and_carries_only_the_schema_keys(f19):
    doc, agg, pmap, rec, out, printed = f19
    schema = load_json_schema("egress_schema.json")
    assert len(rec.calls) == 1
    call = rec.calls[0]
    assert call["url"] == telemetry.TELEMETRY_URL and call["timeout"] == telemetry.TIMEOUT_S
    payload = json.loads(call["body"].decode("utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)  # the root oneOf
    assert set(payload) == set(schema["$defs"]["telemetry"]["required"])
    assert payload["schema"] == "proofpack-telemetry/1"
    assert payload["run_id"] == doc["manifest"]["run_id"]
    assert payload["licence_id"] == doc["manifest"]["licence_id"]
    assert payload["licence_id"] is not None
    assert payload["halt_code"] is None
    assert payload["row_count_bucket"] == "<1k"
    assert payload["manifest_sha256"] == egress.manifest_sha256(doc["manifest"])
    assert payload["duration_s"] == doc["manifest"]["duration_s"]
    assert "telemetry sent (http 204)" in printed
    assert NETWORK_ATTEMPTS == []


def test_f19_the_aggregates_document_validates_and_no_key_is_outside_the_schema(f19):
    doc, agg, pmap, rec, out, printed = f19
    schema = load_json_schema("egress_schema.json")
    jsonschema.Draft202012Validator(schema).validate(agg)
    named = whitelist.keys_named(schema)
    keys = set()

    def keys_of(v):
        if isinstance(v, dict):
            for k, x in v.items():
                keys.add(k)
                keys_of(x)
        elif isinstance(v, list):
            for x in v:
                keys_of(x)

    keys_of(agg)
    assert keys <= named, sorted(keys - named)
    assert agg["schema"] == "proofpack-aggregates/1"
    assert len(agg["cells"]) > 50 and len(agg["two_by_two"]) == 1
    assert len(agg["calibration_bins"]) == 10


# --------------------------------------------------------------------- k-suppression F19


def test_f19_the_n7_cell_is_suppressed_and_no_digit_of_its_estimates_is_in_the_bytes(f19):
    doc, agg, pmap, rec, out, printed = f19
    row = next(r for r in doc["subgroups"] if r["attribute"] == "site" and r["level"] == ST_MARYS)
    assert (row["n"], row["events"]) == (7, 2)
    label = pmap["site"][ST_MARYS]
    cells = [c for c in agg["cells"] if c["attribute"] == "site" and c["level"] == label]
    assert len(cells) >= 5
    for c in cells:
        assert c["number"] == suppress.suppressed_number(), c
    # the local interval bounds of that row must not appear in the egress bytes (the
    # Wilson bounds at n <= 7 are specific to the cell; a short estimate such as 0.5 or
    # 0.8333333333333334 = 5/6 recurs legitimately in other cells and is not searched for)
    agg_bytes = json.dumps(agg, ensure_ascii=False, sort_keys=True)
    locals_: list[str] = []
    for block in row["metrics"]["op1"].values():
        if isinstance(block, dict) and isinstance(block.get("number"), dict):
            for key in ("ci_lo", "ci_hi"):
                v = block["number"].get(key)
                if isinstance(v, float) and len(repr(v)) >= 10:
                    locals_.append(repr(v))
    assert len(locals_) >= 6, locals_
    for s in locals_:
        assert s not in agg_bytes, s
        assert s not in rec.calls[0]["body"].decode("utf-8"), s
    # the unsuppressed rows are still there with their n
    big = [c for c in agg["cells"] if c["attribute"] == "site" and c["level"] != label]
    assert any(c["number"]["suppressed"] is False and c["number"]["n"] == 60 for c in big)


def test_f19_the_forbidden_bytes_are_absent_from_both_payloads_and_the_captured_bytes(
    f19, tmp_path: Path
):
    doc, agg, pmap, rec, out, printed = f19
    tele_bytes = rec.calls[0]["body"]
    agg_bytes = json.dumps(agg, ensure_ascii=False, sort_keys=True).encode("utf-8")
    tele_text = tele_bytes.decode("utf-8")
    agg_text = agg_bytes.decode("utf-8")
    licence_text = (tmp_path / "home" / "proofpack.lic").read_text(encoding="ascii")
    signature = licence_text.split(".")[1]
    forbidden: dict[str, str] = {
        "St Mary's": ST_MARYS,
        "Königsberg": KONIGSBERG,
        "Royal Free": ROYAL_FREE,
        "original header": NOTE_HEADER,
        "free-text value": NOTE_VALUE,
        "ledger key": doc["ledger"]["test_set_sha256"],
        "licence signature": signature,
        "input sha256": doc["manifest"]["input_sha256"],
        "criteria sha256": doc["manifest"]["criteria_sha256"],
        "mapping sha256": doc["manifest"]["mapping_sha256"],
        "criterion date": doc["declarations"]["criteria"][0]["date"],
        "fairness date": doc["declarations"]["fairness"]["date"],
        "justification": doc["declarations"]["criteria"][0]["justification"],
        "model name": doc["declarations"]["model"]["name"],
    }
    for what, needle in forbidden.items():
        assert needle not in tele_text, what
        assert needle not in agg_text, what
    # every level label of the pseudonymised attribute, as a JSON string; the one label
    # that reads like a pseudonym ("Site A") is the collision case and is asserted on by
    # test_f19_a_site_named_like_a_pseudonym_is_remapped_and_the_map_is_a_bijection
    for level in [r["level"] for r in doc["subgroups"] if r["attribute"] == "site"]:
        assert level not in tele_text
        if pseudonymise.TOKEN.match(level) or re.fullmatch(r"Site [A-Z]+", level):
            continue
        assert json.dumps(level, ensure_ascii=False) not in agg_text, level
    # every ROC threshold value (E7 lens RG-N8): 401 points, none in either payload
    roc = doc["overall"]["threshold_free"]["roc"]
    thresholds = [p[2] for p in roc if p[2] is not None]
    assert len(thresholds) >= 300
    for t in thresholds:
        s = json.dumps(t)
        assert s not in tele_text
        assert s not in agg_text, s
    assert '"roc"' not in agg_text and '"declarations"' not in agg_text
    assert doc["manifest"]["started"] not in agg_text
    # the whole run.json is not a substring of anything sent, and the payload is small
    assert len(tele_bytes) < 600


def test_f19_pseudonyms_json_holds_the_map_beside_run_json_and_is_not_inside_any_payload(f19):
    doc, agg, pmap, rec, out, printed = f19
    path = out / egress.PSEUDONYMS_JSON
    assert path.exists() and sorted(p.name for p in out.iterdir()) == [
        "ingest_report.json",
        "pseudonyms.json",
        "run.json",
    ]
    local = json.loads(path.read_text(encoding="utf-8"))
    assert local["schema"] == "proofpack-pseudonyms/1" and local["local_only"] is True
    assert local["run_id"] == doc["manifest"]["run_id"]
    assert local["attributes"] == pmap
    assert local["attributes"]["site"] == {
        KONIGSBERG: "Site A",
        ROYAL_FREE: "Site B",
        SITE_A: "Site C",
        ST_MARYS: "Site D",
    }
    # sex and age levels are tokens and are not in the map
    assert set(local["attributes"]) == {"site"}
    agg_text = json.dumps(agg, ensure_ascii=False)
    assert "pseudonyms" not in agg_text and "local_only" not in agg_text
    assert "pseudonyms" not in rec.calls[0]["body"].decode("utf-8")


def test_f19_a_site_named_like_a_pseudonym_is_remapped_and_the_map_is_a_bijection(f19):
    doc, agg, pmap, rec, out, printed = f19
    site_map = pmap["site"]
    assert site_map[SITE_A] == "Site C" and site_map[KONIGSBERG] == "Site A"
    assert len(set(site_map.values())) == len(site_map)  # a bijection
    # the bytes "Site A" in the payload denote Königsberg's 60-row cell, not the
    # customer's "Site A"; both rows carry n = 60 so the cell is told by its label
    by_label = {}
    for c in agg["cells"]:
        if c["attribute"] == "site" and c["metric_id"] == "accuracy":
            by_label[c["level"]] = c["number"]["n"]
    assert by_label == {"Site A": 60, "Site B": 273, "Site C": 60, "Site D": None}
    # code-point order: K (0x4B) < R < S; "Site A" < "St Mary's" because "i" < "t"
    assert sorted([KONIGSBERG, ROYAL_FREE, SITE_A, ST_MARYS]) == [
        KONIGSBERG,
        ROYAL_FREE,
        SITE_A,
        ST_MARYS,
    ]


def test_pseudonym_letters_and_the_unknown_row_and_the_token_rule():
    assert [pseudonymise.letters(i) for i in (0, 1, 25, 26, 27, 51, 52, 701, 702)] == [
        "A",
        "B",
        "Z",
        "AA",
        "AB",
        "AZ",
        "BA",
        "ZZ",
        "AAA",
    ]
    levels = {"site": {"b", "a", "Unknown/missing"}, "sex": {"F", "M", "not stated"}}
    m = pseudonymise.build_map({}, levels=levels)
    assert m == {"site": {"a": "Site A", "b": "Site B"}, "sex": {"not stated": "Level A"}}
    assert pseudonymise.pseudonym(m, "site", "Unknown/missing") == "Unknown/missing"
    assert pseudonymise.pseudonym(m, "sex", "F") == "F"
    assert pseudonymise.pseudonym(m, "sex", "not stated") == "Level A"
    with pytest.raises(KeyError):
        pseudonymise.pseudonym(m, "site", "c")
    assert pseudonymise.build_map({}, levels={"attr_scanner": {"GE Signa 1.5T"}}) == {
        "attr_scanner": {"GE Signa 1.5T": "Level A"}
    }


# ------------------------------------------------------- the thresholds and the refusal


def test_a_looser_suppression_value_is_refused_h08_at_the_cli_and_nothing_is_written(
    tmp_path: Path, monkeypatch, capsys
):
    crit = f19_criteria(suppression={"min_n": 9, "min_events": 5, "min_nonevents": 5})
    csv_path, yml, out = prepare(tmp_path, monkeypatch, crit=crit)
    rec = Recorder(204, out)
    assert run_cli(csv_path, yml, out, transport=rec) == EXIT_HALT
    err = capsys.readouterr().err
    assert "HALT H08" in err and "egress/suppression/min_n" in err
    assert not out.exists() and rec.calls == []


@pytest.mark.parametrize(
    "field, value, default",
    [("min_n", 9, 10), ("min_events", 4, 5), ("min_nonevents", 0, 5), ("min_n", -1, 10)],
)
def test_a_looser_value_handed_directly_is_h08_naming_field_declared_and_default(
    field, value, default
):
    block = {"suppression": {"min_n": 10, "min_events": 5, "min_nonevents": 5}}
    block["suppression"][field] = value
    with pytest.raises(HaltError) as info:
        suppress.thresholds_from_declarations(block)
    assert info.value.code == "H08"
    assert info.value.detail == {
        "field": f"egress.suppression.{field}",
        "declared": value,
        "default": default,
    }
    assert "only be made stricter" in info.value.message


def test_default_absent_and_stricter_thresholds_are_accepted_and_a_bool_is_refused():
    assert suppress.thresholds_from_declarations(None) == suppress.DEFAULT_THRESHOLDS
    assert suppress.thresholds_from_declarations({"telemetry": False}) == suppress.Thresholds(
        10, 5, 5
    )
    assert suppress.thresholds_from_declarations(
        {"suppression": {"min_n": 20, "min_events": 5, "min_nonevents": 11}}
    ) == suppress.Thresholds(20, 5, 11)
    with pytest.raises(HaltError):
        suppress.thresholds_from_declarations({"suppression": {"min_n": True}})
    with pytest.raises(HaltError):
        suppress.thresholds_from_declarations({"suppression": [10]})


@pytest.mark.parametrize(
    "n, events, nonevents, expected",
    [
        (10, 5, 5, False),
        (9, 5, 5, True),
        (10, 4, 6, True),
        (10, 6, 4, True),
        (None, 50, 50, True),
        (10, None, None, False),
        (7, 2, 5, True),
    ],
)
def test_is_suppressed_on_the_defaults(n, events, nonevents, expected):
    assert suppress.is_suppressed(n, events, nonevents, suppress.DEFAULT_THRESHOLDS) is expected


def test_a_stricter_threshold_suppresses_the_sixty_row_cells_too(f19):
    doc, agg, pmap, rec, out, printed = f19
    strict, _ = egress.build_aggregates(doc, suppress.Thresholds(min_n=61))
    site_cells = [c for c in strict["cells"] if c["attribute"] == "site"]
    assert all(c["number"]["suppressed"] for c in site_cells if c["level"] != "Site B")
    assert any(not c["number"]["suppressed"] for c in site_cells if c["level"] == "Site B")


def test_project_number_drops_flags_and_reasons_and_suppresses_unknown_n_and_small_arms():
    t = suppress.DEFAULT_THRESHOLDS
    full = {
        "est": 0.75,
        "ci_lo": 0.6684,
        "ci_hi": 0.8169,
        "ci_level": 0.95,
        "flags": ["imprecise"],
        "k": 96,
        "method": "wilson",
        "n": 128,
        "not_estimable_reason": None,
        "suppressed": False,
    }
    assert suppress.project_number(full, t) == {
        "est": 0.75,
        "ci_lo": 0.6684,
        "ci_hi": 0.8169,
        "method": "wilson",
        "n": 128,
        "k": 96,
        "suppressed": False,
    }
    assert suppress.project_number({**full, "k": 3}, t) == suppress.suppressed_number()
    assert suppress.project_number({**full, "k": 125}, t) == suppress.suppressed_number()
    assert suppress.project_number({**full, "n": 9, "k": 4}, t) == suppress.suppressed_number()
    no_n = {"est": 0.5, "ci_lo": None, "ci_hi": None, "method": "none", "suppressed": False}
    assert suppress.project_number(no_n, t) == suppress.suppressed_number()
    auroc = {**full, "k": None, "n": None, "n_pos": 4, "n_neg": 100, "method": "delong_wald"}
    del auroc["k"], auroc["n"]
    assert suppress.project_number(auroc, t) == suppress.suppressed_number()
    auroc["n_pos"] = 5
    assert suppress.project_number(auroc, t)["n"] == 105
    assert suppress.project_number(full, t, row_suppressed=True) == suppress.suppressed_number()
    assert suppress.project_number({**full, "suppressed": True}, t) == suppress.suppressed_number()
    assert suppress.project_number(None, t) == suppress.suppressed_number()


# ----------------------------------------------------------------- the whitelist itself


def test_whitelist_drops_unknown_keys_and_refuses_unconstrained_or_mismatched_strings():
    schema = load_json_schema("egress_schema.json")
    tele = schema["$defs"]["telemetry"]
    good = {
        "schema": "proofpack-telemetry/1",
        "licence_id": "lic_0123456789abcdef0123456789abcdef",
        "run_id": "9822b658-0a43-4b13-9b86-9ec1a74b0e19",
        "engine_version": "0.1.0.dev1",
        "platform": "linux-x86_64-cp312",
        "manifest_sha256": "f" * 64,
        "duration_s": 1.5,
        "halt_code": None,
        "row_count_bucket": "<1k",
        "timestamp": "2026-09-22T13:29:12Z",
    }
    with_extra = {**good, "roc": [[0, 0, 0.5]], "original_header": "Patient ID", "site": "X"}
    assert whitelist.project(with_extra, schema, tele) == good
    with pytest.raises(whitelist.WhitelistError) as info:
        whitelist.project({**good, "platform": "St Mary's"}, schema, tele)
    assert info.value.path == "$.platform"
    with pytest.raises(whitelist.WhitelistError):
        whitelist.project({**good, "row_count_bucket": "7"}, schema, tele)
    with pytest.raises(whitelist.WhitelistError):
        whitelist.project({**good, "halt_code": "H99"}, schema, tele)
    with pytest.raises(whitelist.WhitelistError):
        whitelist.project({**good, "duration_s": "1.5"}, schema, tele)
    # an unconstrained string in a schema is refused, not passed
    loose = {"properties": {"note": {"type": "string"}}}
    with pytest.raises(whitelist.WhitelistError) as info:
        whitelist.project({"note": "free text"}, {"$defs": {}}, loose)
    assert "does not constrain" in info.value.reason
    # nested: an aggregate cell with a level outside the pattern
    cell = schema["$defs"]["aggregate_cell"]
    ok = {
        "metric_id": "sensitivity",
        "operating_point": "op1",
        "attribute": "site",
        "level": "Site A",
        "number": suppress.suppressed_number(),
    }
    assert whitelist.project({**ok, "n_pos": 3}, schema, cell) == ok
    with pytest.raises(whitelist.WhitelistError):
        whitelist.project({**ok, "level": ST_MARYS}, schema, cell)


def test_every_string_property_in_the_schema_is_constrained_and_every_object_is_closed():
    schema = load_json_schema("egress_schema.json")
    problems = []

    def walk_schema(node, path):
        if not isinstance(node, dict):
            if isinstance(node, list):
                for i, v in enumerate(node):
                    walk_schema(v, f"{path}[{i}]")
            return
        if node.get("type") == "object" or "properties" in node:
            if node.get("additionalProperties") is not False:
                problems.append(f"{path}: additionalProperties is not false")
        types = node.get("type")
        types = [types] if isinstance(types, str) else (types or [])
        if "string" in types and not any(k in node for k in ("enum", "const", "pattern")):
            problems.append(f"{path}: an unconstrained string")
        if "pattern" in node and "maxLength" not in node:
            problems.append(f"{path}: a pattern with no maxLength")
        for k, v in node.items():
            # if / then narrow a closed object; they open nothing and are not walked
            if k in (
                "enum",
                "const",
                "required",
                "description",
                "pattern",
                "$id",
                "$schema",
                "if",
                "then",
            ):
                continue
            walk_schema(v, f"{path}/{k}")

    walk_schema(schema["$defs"], "$defs")
    assert problems == []


# ---------------------------------------------------- enum agreement with the constants


def test_schema_enums_and_constants_agree_with_the_engine():
    schema = load_json_schema("egress_schema.json")
    tele = schema["$defs"]["telemetry"]["properties"]
    assert tele["row_count_bucket"]["enum"] == [b[0] for b in build_mod.ROW_COUNT_BUCKETS]
    expected_halts = sorted(set(HALT_CODES) | set(SCHEMA_CODES) | set(MAPPING_CODES))
    assert tele["halt_code"]["enum"] == [*expected_halts, None]
    assert (
        schema["$defs"]["metric_id"]["enum"]
        == (load_json_schema("criteria_schema.json")["$defs"]["metric_id"]["enum"])
    )
    assert schema["$defs"]["method"]["enum"] == [
        *load_json_schema("output_schema_v1.json")["$defs"]["method"]["enum"],
        None,
    ]
    for tag in (platform_tag(), REFERENCE_PLATFORM, "macosx-14.0-arm64-cp312", "win-amd64-cp314"):
        assert re.search(tele["platform"]["pattern"], tag), tag
    assert not re.search(tele["platform"]["pattern"], "St Mary's")
    x = schema["x-proofpack"]
    assert x["telemetry_url"] == telemetry.TELEMETRY_URL
    assert x["suppression_defaults"] == suppress.DEFAULT_THRESHOLDS.as_dict()
    assert x["telemetry_off_switches"] == ["--offline", "egress.telemetry: false"]
    assert schema["$defs"]["telemetry"]["required"] == [
        "schema",
        "licence_id",
        "run_id",
        "engine_version",
        "platform",
        "manifest_sha256",
        "duration_s",
        "halt_code",
        "row_count_bucket",
        "timestamp",
    ]
    assert "W16" in WARN_CODES and "W16" in FLAG_ONLY_CODES
    assert re.search(tele["licence_id"]["pattern"], "lic_" + "0" * 32)
    assert re.search(tele["licence_id"]["pattern"], "lic_test0000000000000000000000000001")
    assert not re.search(tele["licence_id"]["pattern"], "L-1")


@pytest.mark.parametrize(
    "rows, bucket",
    [
        (0, "<1k"),
        (999, "<1k"),
        (1000, "1k-10k"),
        (9999, "1k-10k"),
        (10000, "10k-100k"),
        (99999, "10k-100k"),
        (100000, ">100k"),
        (5_000_000, ">100k"),
    ],
)
def test_row_count_bucket_boundaries(rows, bucket):
    assert egress.row_count_bucket(rows) == bucket


def test_row_count_bucket_refuses_a_negative_or_missing_count():
    with pytest.raises(egress.EgressError):
        egress.row_count_bucket(-1)
    with pytest.raises(egress.EgressError):
        egress.row_count_bucket(None)


def test_manifest_sha256_is_the_hash_of_the_manifest_block_alone(f19):
    doc, agg, pmap, rec, out, printed = f19
    expected = hashlib.sha256(canonical_json(doc["manifest"])).hexdigest()
    assert egress.manifest_sha256(doc["manifest"]) == expected
    assert expected != hashlib.sha256(canonical_json(doc)).hexdigest()
    assert expected != hashlib.sha256((out / "run.json").read_bytes()).hexdigest()


def test_build_payload_refuses_a_document_that_does_not_validate(f19):
    doc, agg, pmap, rec, out, printed = f19
    bad = copy.deepcopy(doc)
    bad["manifest"]["platform"] = "St Mary's laptop"
    with pytest.raises(egress.EgressError):
        egress.build_payload(bad, licence_status="ok")
    bad = copy.deepcopy(doc)
    bad["flow"]["rows_read"] = -5
    with pytest.raises(egress.EgressError):
        egress.build_payload(bad, licence_status="ok")
    # a refused licence sends null, a verified one the id
    assert egress.build_payload(doc, licence_status="refused")["licence_id"] is None
    assert (
        egress.build_payload(doc, licence_status="ok")["licence_id"]
        == doc["manifest"]["licence_id"]
    )
    assert egress.build_payload(doc, licence_status="grace")["licence_id"] is not None


def test_the_mutation_sweep_declares_an_ap2_list_of_at_least_eight():
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "mutation_sweep.py"), "--list"],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    ids = [ln.split()[0] for ln in lines]
    assert len(ids) == len(set(ids))
    ap2 = [ln for ln in lines if " ap2 " in ln]
    assert len(ap2) >= 8, len(ap2)
    for needed in (
        "min_n",
        "min_events",
        "min_nonevents",
        "pseudonym_order",
        "whitelist",
        "timeout",
        "offline_short_circuit",
        "exit_code",
    ):
        assert any(needed in ln for ln in ap2), needed
