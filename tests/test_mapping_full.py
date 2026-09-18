"""Day 6 A - the full mapper (A-P1): fixtures, profiler, heuristics, DEC-11, the --yes matrix.

Every test names the literal input it feeds and the figures it asserts. The fixture
register under ``tests/fixtures/mapping`` is written by ``scripts/make_mapping_fixtures.py``,
whose expected roles are authored by hand from the rules, not produced by the mapper.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

import proofpack
from conftest import make_cohort, make_criteria, write_csv, write_yaml
from proofpack.cli import _confirm_interactive, main
from proofpack.errors import EXIT_HALT, EXIT_OK, MAPPING_CODES, HaltError
from proofpack.gates import ingest
from proofpack.io import declare
from proofpack.io.mapping import (
    BINARY_LABEL_SETS,
    Mapping,
    check_h07,
    check_h11,
    map_headers,
    normalise_header,
)
from proofpack.io.profile import (
    SAMPLE_ROWS,
    SUPPRESSED,
    SUPPRESSION_K,
    profile_column,
)
from proofpack.io.schema import load_table, table_from_columns

pytestmark = pytest.mark.day6

FIXTURES = Path(__file__).parent / "fixtures" / "mapping"
FIXTURE_IDS = sorted(p.name[: -len(".expected.json")] for p in FIXTURES.glob("*.expected.json"))
SRC = Path(proofpack.__file__).parents[1]


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONUTF8"] = "1"
    return env


def _roles(m: Mapping) -> dict[str, list[str]]:
    return {r.original: [r.role_label, r.confidence] for r in m.roles}


def _cols(**kw) -> dict:
    return {k: list(v) for k, v in kw.items()}


# --------------------------------------------------------------------------- fixtures


def test_register_has_at_least_thirty_fixtures_with_expectations():
    assert len(FIXTURE_IDS) >= 30, FIXTURE_IDS
    for fid in FIXTURE_IDS:
        assert (FIXTURES / f"{fid}.csv").exists(), fid
        spec = json.loads((FIXTURES / f"{fid}.expected.json").read_text(encoding="utf-8"))
        raw = load_table(FIXTURES / f"{fid}.csv")
        assert raw.n_rows <= 50, (fid, raw.n_rows)
        assert raw.n_rows == spec["n_rows"], fid
        if spec["halt"] is None:
            assert set(spec["roles"]) == set(raw.headers), fid


@pytest.mark.parametrize("fid", FIXTURE_IDS)
def test_fixture_roles_and_confidences(fid: str, capsys):
    spec = json.loads((FIXTURES / f"{fid}.expected.json").read_text(encoding="utf-8"))
    csv_path = FIXTURES / f"{fid}.csv"
    raw = load_table(csv_path)
    if spec.get("criteria"):
        # a declaration-level halt: driven through the CLI so the exit code is asserted too
        rc = main(["map", "--input", str(csv_path), "--criteria", str(FIXTURES / spec["criteria"])])
        err = capsys.readouterr().err
        assert rc == EXIT_HALT
        assert f"HALT {spec['halt']['code']}" in err
        assert err.splitlines()[0].endswith(spec["halt"]["message_ends"])
        assert "Traceback" not in err
        return
    if spec["halt"] is not None:
        with pytest.raises(HaltError) as ei:
            map_headers(raw.headers, raw.columns)
        assert ei.value.code == spec["halt"]["code"]
        if "message_contains" in spec["halt"]:
            assert spec["halt"]["message_contains"] in ei.value.message
        if "message_ends" in spec["halt"]:
            assert ei.value.message.endswith(spec["halt"]["message_ends"])
        return
    m = map_headers(raw.headers, raw.columns)
    assert _roles(m) == spec["roles"]
    for header, fragment in spec["notes"].items():
        entry = m.entry(header)
        assert entry is not None and any(fragment in n for n in entry.notes), (
            header,
            entry.notes if entry else None,
        )


def test_acceptance_sepsis_and_diabetes_map_high_on_the_five_named_columns():
    """The brief's acceptance, read literally against the two real header sets.

    ``sepsis_2019`` carries PhysioNet's real Gender coding (0/1) and its sex column is
    ``medium`` with the 0/1 note; the M/F recoding in ``sepsis_2019_gender_mf`` is high.
    """
    sep = map_headers(*_load("sepsis_2019_gender_mf"))
    for h, role in (
        ("SepsisLabel", "y_true"),
        ("PredictedProbability", "score"),
        ("hospital", "site"),
        ("Age", "age"),
        ("Gender", "sex"),
    ):
        e = sep.entry(h)
        assert (e.role, e.confidence) == (role, "high"), h
    real = map_headers(*_load("sepsis_2019")).entry("Gender")
    assert (real.role, real.confidence) == ("sex", "medium")
    assert "no dictionary declared for 0/1" in real.notes
    dia = map_headers(*_load("diabetes_130"))
    for h, role in (
        ("readmitted", "y_true"),
        ("pred_prob", "score"),
        ("hospital", "site"),
        ("age", "age_band"),
        ("gender", "sex"),
    ):
        e = dia.entry(h)
        assert (e.role, e.confidence) == (role, "high"), h


def _load(fid: str):
    raw = load_table(FIXTURES / f"{fid}.csv")
    return raw.headers, raw.columns


# --------------------------------------------------------------------------- profiler


def test_free_text_column_with_thirty_distinct_values_shows_none_of_them():
    col = [f"note number {i} about a patient" for i in range(30)]
    s = profile_column(col)
    assert s.inferred_type == "string" and s.n_unique == 30
    assert s.free_text is True and s.values_shown is False
    assert s.top == [] and s.split is None
    rendered = s.render()
    assert "values not shown (free text)" in rendered
    for v in col:
        assert v not in rendered
    assert "30 unique" in rendered and "0.0% missing" in rendered


def test_suppression_floor_count_nine_is_suppressed_and_count_ten_is_shown():
    assert SUPPRESSION_K == 10
    col = ["shown10"] * 10 + ["hidden9"] * 9 + ["shown11"] * 11
    s = profile_column(col)
    assert s.top == [["shown11", 11], ["shown10", 10], [SUPPRESSED, 1]]
    assert s.n_suppressed_values == 1
    assert "hidden9" not in s.render() and "hidden9" not in json.dumps(s.to_dict())


def test_two_unique_split_is_suppressed_the_same_way():
    col = ["0"] * 41 + ["1"] * 9
    s = profile_column(col)
    assert s.split == [["0", 41], [SUPPRESSED, 1]]
    assert s.n_unique == 2 and s.inferred_type == "int"
    # 41 rows hold the min (shown); 9 rows hold the max (below k=10: the literal).
    # At 555a5e1 this line read ``s.max == "1"`` and pinned the leak (repair 1, FA-B1).
    assert s.min == "0" and s.max == SUPPRESSED


def test_sample_boundary_row_10001_does_not_reach_the_summary():
    assert SAMPLE_ROWS == 10_000
    col = ["x"] * 10_000 + ["ZZZ_ROW_10001"]
    s = profile_column(col)
    assert s.n_sampled == 10_000 and s.n_unique == 1
    assert "ZZZ_ROW_10001" not in json.dumps(s.to_dict())
    col2 = ["x"] * 9_999 + ["ZZZ_ROW_10000"]
    s2 = profile_column(col2)
    assert s2.n_sampled == 10_000 and s2.n_unique == 2


def test_missing_pct_after_missing_token_normalisation():
    raw = table_from_columns({"c": ["1", "NA", "", "unknown", "2", None, "3", "4"]})
    s = profile_column(raw.columns["c"])
    assert s.n_sampled == 8 and s.n_missing == 4 and s.missing_pct == 50.0
    # each of 1..4 is held by one row (below k=10), so both extremes are the literal
    assert s.inferred_type == "int" and s.min == SUPPRESSED and s.max == SUPPRESSED
    assert s.signals["min"] == 1.0 and s.signals["max"] == 4.0  # the mapper still sees them


def test_date_column_lists_no_values_and_coarsens_min_max_to_month():
    col = ["2024-03-15", "2024-03-16", "2025-11-02"] * 5
    s = profile_column(col)
    assert s.inferred_type == "date" and s.values_shown is False
    assert (s.min, s.max) == ("2024-03", "2025-11")
    assert "2024-03-15" not in s.render() and "2024-03-15" not in json.dumps(s.to_dict())


def test_type_inference_literal_columns():
    assert profile_column(["1", "2", "-3"]).inferred_type == "int"
    assert profile_column(["1.5", "2", "3e-1"]).inferred_type == "float"
    assert profile_column(["2024-01-02", "03/04/2024", "2024/05/06"]).inferred_type == "date"
    assert profile_column(["a", "b", "a"]).inferred_type == "categorical"
    assert profile_column([f"v{i}" for i in range(21)]).inferred_type == "string"
    assert profile_column([None, None]).inferred_type == "empty"


# --------------------------------------------------------------------------- heuristics


@pytest.mark.parametrize("pair", [sorted(s) for s in BINARY_LABEL_SETS])
def test_two_valued_column_from_each_label_set_is_a_y_true_candidate_at_medium(pair):
    a, b = pair
    m = map_headers(["col"], _cols(col=[a, b, a.upper(), b.upper()] * 5))
    e = m.entry("col")
    assert (e.role, e.confidence, e.source) == ("y_true", "medium", "heuristic")


def test_two_valued_column_under_a_score_synonym_is_score_at_low_not_y_true():
    m = map_headers(["prob"], _cols(prob=["0", "1"] * 10))
    e = m.entry("prob")
    assert (e.role, e.confidence) == ("score", "low")
    assert any("only 0/1" in n for n in e.notes)


def test_float_within_unit_interval_is_a_score_candidate_and_outside_is_ignored():
    inside = [f"{i / 20:.2f}" for i in range(21)]
    e = map_headers(["x"], _cols(x=inside)).entry("x")
    assert (e.role, e.confidence) == ("score", "medium")
    outside = inside[:-1] + ["1.5"]
    e2 = map_headers(["x"], _cols(x=outside)).entry("x")
    assert (e2.role, e2.confidence) == (None, "high")
    two_values = ["0.25", "0.75"] * 10
    e3 = map_headers(["x"], _cols(x=two_values)).entry("x")
    assert e3.role is None


def test_visit_column_holding_dates_is_event_date_at_medium():
    m = map_headers(["visit"], _cols(visit=["2025-01-0" + str(i % 9 + 1) for i in range(20)]))
    e = m.entry("visit")
    assert (e.role, e.confidence, e.source) == ("event_date", "medium", "heuristic")


def test_unique_integer_column_is_row_id_and_a_repeating_one_is_not_case_id():
    unique = [str(i) for i in range(30)]
    e = map_headers(["idx"], _cols(idx=unique)).entry("idx")
    assert (e.role, e.confidence) == ("row_id", "medium")
    repeating = [str(i % 7) for i in range(30)]
    e2 = map_headers(["idx"], _cols(idx=repeating)).entry("idx")
    assert (e2.role, e2.confidence) == (None, "high")
    strings = [f"p{i % 7}" for i in range(30)]
    e3 = map_headers(["idx"], _cols(idx=strings)).entry("idx")
    assert e3.role is None


def test_case_id_from_a_partial_token_is_low_and_from_a_synonym_is_high():
    repeating = [str(i % 7) for i in range(30)]
    e = map_headers(["patient_nbr"], _cols(patient_nbr=repeating)).entry("patient_nbr")
    assert (e.role, e.confidence, e.source) == ("case_id", "low", "partial")
    e2 = map_headers(["patient_id"], _cols(patient_id=repeating)).entry("patient_id")
    assert (e2.role, e2.confidence, e2.source) == ("case_id", "high", "synonym")


def test_age_numeric_banded_and_neither():
    e = map_headers(["age"], _cols(age=[str(20 + i) for i in range(30)])).entry("age")
    assert (e.role, e.confidence) == ("age", "high")
    bands = ["[70-80)", "[60-70)", "[80-90)"] * 10
    e2 = map_headers(["age"], _cols(age=bands)).entry("age")
    assert (e2.role, e2.confidence) == ("age_band", "high")
    dash = ["70-79", "60-69", "90+"] * 10
    e3 = map_headers(["age"], _cols(age=dash)).entry("age")
    assert (e3.role, e3.confidence) == ("age_band", "high")
    words = ["old", "young"] * 15
    e4 = map_headers(["age"], _cols(age=words)).entry("age")
    assert (e4.role, e4.confidence) == ("age", "low")


@pytest.mark.parametrize(
    "values, expected_conf, note",
    [
        (["M", "F"], "high", None),
        (["male", "Female"], "high", None),
        (["1", "2"], "medium", "no dictionary declared for 1/2"),
        (["0", "1"], "medium", "no dictionary declared for 0/1"),
        (["X", "Y"], "medium", "values outside M/F/male/female"),
    ],
)
def test_sex_coding_rules(values, expected_conf, note):
    for header in ("sex", "gender", "Gender"):
        e = map_headers([header], _cols(**{header: values * 10})).entry(header)
        assert (e.role, e.confidence) == ("sex", expected_conf), (header, values)
        if note:
            assert any(note in n for n in e.notes), e.notes


def test_site_device_protocol_severity_race_ethnicity_by_synonym_only():
    cols = _cols(
        centre=["A", "B"] * 10,
        scanner=["S1", "S2"] * 10,
        protocol=["P1", "P2"] * 10,
        severity=["mild", "severe"] * 10,
        race=["W", "B"] * 10,
        ethnicity=["H", "NH"] * 10,
        unnamed=["A", "B", "C"] * 7,
    )
    m = map_headers(list(cols), cols)
    expect = {
        "centre": "site",
        "scanner": "device",
        "protocol": "protocol",
        "severity": "severity",
        "race": "race",
        "ethnicity": "ethnicity",
    }
    for h, role in expect.items():
        e = m.entry(h)
        assert (e.role, e.confidence) == (role, "high"), h
    assert m.entry("unnamed").role is None


def test_every_other_column_is_ignore_at_high_and_keeps_its_header():
    m = map_headers(
        ["Krankenhausaufenthalt (Tage)"], _cols(**{"Krankenhausaufenthalt (Tage)": ["3", "4"] * 5})
    )
    e = m.entry("Krankenhausaufenthalt (Tage)")
    assert (e.role, e.confidence, e.role_label) == (None, "high", "ignore")
    assert m.to_dict()["roles"][0]["original"] == "Krankenhausaufenthalt (Tage)"


def test_header_only_call_keeps_the_day1_confidences():
    m = map_headers(["score", "label", "gender", "other"])
    assert _roles(m) == {
        "score": ["score", "high"],
        "label": ["y_true", "medium"],
        "gender": ["sex", "medium"],
        "other": ["ignore", "high"],
    }


# --------------------------------------------------------------------------- conflicts


def test_label_holding_continuous_scores_keeps_the_role_at_low_with_a_note():
    floats = [f"{(i * 37 % 100) / 100:.2f}" for i in range(30)]
    e = map_headers(["label"], _cols(label=floats)).entry("label")
    assert (e.role, e.confidence) == ("y_true", "low")
    assert any("continuous" in n for n in e.notes)


def test_two_headers_claiming_y_true_are_both_low_and_yes_is_refused(tmp_path: Path):
    cols = make_cohort()
    cols["label"] = cols.pop("y_true")
    cols["outcome"] = list(cols["label"])
    raw = table_from_columns(cols)
    m = map_headers(raw.headers, raw.columns)
    assert (m.entry("label").role, m.entry("label").confidence) == ("y_true", "low")
    assert (m.entry("outcome").role, m.entry("outcome").confidence) == ("y_true", "low")
    assert any("2 headers claim y_true" in n for n in m.entry("label").notes)
    m.decided_by = "interactive"  # a confirmed prior (repair 1: a proposed one is refused first)
    m.write(tmp_path / "mapping.json")
    with pytest.raises(HaltError) as ei:
        check_h07(raw.headers, tmp_path / "mapping.json", non_interactive=True, fresh=m)
    assert ei.value.code == "H07"
    assert ei.value.detail == {"low_or_medium": 2}


def test_value_candidate_yields_to_a_header_that_names_the_role():
    cols = _cols(label=["0", "1"] * 10, flag=["yes", "no"] * 10)
    m = map_headers(list(cols), cols)
    assert (m.entry("label").role, m.entry("label").confidence) == ("y_true", "high")
    e = m.entry("flag")
    assert e.role is None and any("claimed by name" in n for n in e.notes)


def test_two_value_only_candidates_for_one_role_are_both_low():
    cols = _cols(a=["0", "1"] * 10, b=["true", "false"] * 10)
    m = map_headers(list(cols), cols)
    for h in ("a", "b"):
        e = m.entry(h)
        assert (e.role, e.confidence) == ("y_true", "low"), h
        assert any("2 columns look like y_true" in n for n in e.notes)


# --------------------------------------------------------------------------- hostile headers


def test_normalise_header_literal_cases():
    assert normalise_header("﻿patient_id") == "patient_id"
    assert normalise_header("  Sepsis Label ") == "sepsis_label"
    assert normalise_header("PredictedProbability") == "predicted_probability"
    assert normalise_header("subject-id") == "subject_id"
    assert normalise_header("O2Sat") == "o2_sat"
    nfd = unicodedata.normalize("NFD", "Température")
    assert normalise_header(nfd) == "température"


def test_bom_in_the_first_header_still_resolves_the_role():
    e = map_headers(["﻿patient_id"], _cols(**{"﻿patient_id": ["1", "2"] * 5})).entry("﻿patient_id")
    assert (e.role, e.confidence) == ("case_id", "high")


def test_duplicate_headers_after_case_folding_halt_h07_via_the_cli_without_a_traceback(
    tmp_path: Path, capsys
):
    cols = make_cohort()
    cols["Y_TRUE"] = list(cols["y_true"])  # exact-duplicate check in load_table passes
    csv_path = write_csv(tmp_path / "t.csv", cols)
    rc = main(["map", "--input", str(csv_path), "--out", str(tmp_path / "m.json")])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert "HALT H07" in err and "identical after case-folding" in err
    assert "Traceback" not in err
    assert not (tmp_path / "m.json").exists()


def test_empty_string_header_is_ignore():
    e = map_headers([""], _cols(**{"": [str(i) for i in range(10)]})).entry("")
    assert (e.role, e.confidence) == (None, "high") and "empty header" in e.notes


# --------------------------------------------------------------------------- DEC-11


def test_e01_is_registered_and_constructs():
    assert "E01" in MAPPING_CODES
    err = HaltError("E01", "x; reduce your case key to one column")
    assert err.exit_code == EXIT_HALT


def test_two_case_id_headers_halt_e01_through_map_headers_and_ingest():
    cols = make_cohort()
    cols["patient_id"] = [f"c{i}" for i in range(len(cols["y_true"]))]
    cols["subject_id"] = list(cols["patient_id"])
    with pytest.raises(HaltError) as ei:
        map_headers(list(cols), cols)
    assert ei.value.code == "E01"
    assert ei.value.message.endswith("reduce your case key to one column")
    assert ei.value.detail == {"n_case_id_columns": 2}
    with pytest.raises(HaltError) as ei2:
        ingest(table_from_columns(cols), declare.validate_dict(make_criteria()))
    assert ei2.value.code == "E01"


@pytest.mark.parametrize(
    "unit, n",
    [
        (["patient_id", "study_id"], 2),
        ("patient_id, study_id", 2),
        ("patient_id+study_id", 2),
        ("patient_id and study_id", 2),
        (["a", "b", "c"], 3),
    ],
)
def test_composite_clustering_unit_halts_e01_before_the_schema_check(unit, n):
    crit = make_criteria(clustering={"unit": unit, "declared_by": "t"})
    with pytest.raises(HaltError) as ei:
        declare.validate_dict(crit)
    assert ei.value.code == "E01"
    assert ei.value.message.endswith("reduce your case key to one column")
    assert ei.value.detail == {"n_case_key_columns": n}


def test_single_column_clustering_units_are_not_e01():
    for unit in ("case_id", "none", ["case_id"], "random_id"):
        crit = make_criteria(clustering={"unit": unit, "declared_by": "t"})
        try:
            declare.validate_dict(crit)
        except HaltError as exc:
            assert exc.code == "H08", unit  # the schema's enum, not DEC-11


def test_dec11_via_the_cli_run_and_map_exit_3_with_the_message_and_no_traceback(
    tmp_path: Path, capsys
):
    cols = make_cohort(with_case_id=True)
    csv_path = write_csv(tmp_path / "t.csv", cols)
    yml = write_yaml(
        tmp_path / "c.yaml",
        make_criteria(clustering={"unit": ["case_id", "row_id"], "declared_by": "t"}),
    )
    out = tmp_path / "pack"
    for argv in (
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out)],
        ["map", "--input", str(csv_path), "--criteria", str(yml), "--out", str(tmp_path / "m")],
    ):
        rc = main(argv)
        err = capsys.readouterr().err
        assert rc == EXIT_HALT, argv
        assert err.splitlines()[0] == (
            "HALT E01: clustering.unit names 2 columns; reduce your case key to one column"
        )
        assert "Traceback" not in err
    assert not out.exists()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proofpack.cli",
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--out",
            str(out),
        ],
        env=_env(),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == EXIT_HALT
    assert "reduce your case key to one column" in proc.stderr
    assert "Traceback" not in proc.stderr + proc.stdout


# --------------------------------------------------------------------------- --yes / TTY matrix


def _cohort_csv(tmp_path: Path, **changes) -> tuple[Path, dict]:
    cols = make_cohort()
    for k, v in changes.items():
        cols[k] = v
    return write_csv(tmp_path / "t.csv", cols), cols


def test_yes_without_a_prior_mapping_halts_h07(tmp_path: Path, capsys):
    csv_path, _ = _cohort_csv(tmp_path)
    rc = main(["map", "--input", str(csv_path), "--out", str(tmp_path / "m.json"), "--yes"])
    assert rc == EXIT_HALT
    assert "HALT H07" in capsys.readouterr().err
    assert not (tmp_path / "m.json").exists()


def test_yes_with_matching_all_high_prior_is_accepted(tmp_path: Path, capsys):
    csv_path, cols = _cohort_csv(tmp_path)
    prior = tmp_path / "m.json"
    confirmed = map_headers(list(cols), cols)
    confirmed.decided_by = "interactive"  # repair 1: a proposed prior is refused (FA-N1)
    confirmed.write(prior)
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    out = capsys.readouterr().out
    assert rc == EXIT_OK
    assert "decided_by=file" in out and "original header" in out
    written = Mapping.read(prior)
    assert written.decided_by == "file"
    assert written.file_sha256 == hashlib.sha256(prior.read_bytes()).hexdigest()


def test_yes_with_matching_prior_holding_a_medium_role_halts_h07(tmp_path: Path, capsys):
    csv_path, cols = _cohort_csv(tmp_path)
    prior = tmp_path / "m.json"
    m = map_headers(list(cols))  # header-only: 'label' would be medium; use canonical + edit
    m.roles[0].confidence = "medium"
    m.decided_by = "interactive"
    m.write(prior)
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    assert rc == EXIT_HALT
    assert "every mapped role at high confidence" in capsys.readouterr().err


def test_yes_with_a_prior_whose_hash_differs_halts_h07(tmp_path: Path, capsys):
    csv_path, cols = _cohort_csv(tmp_path)
    prior = tmp_path / "m.json"
    other = dict(cols)
    other["extra"] = [0] * len(cols["y_true"])
    map_headers(list(other), other).write(prior)
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    assert rc == EXIT_HALT
    assert "header-set hash differs" in capsys.readouterr().err


def test_yes_is_refused_when_the_fresh_mapping_has_a_medium_even_if_the_file_says_high(
    tmp_path: Path,
):
    cols = make_cohort()
    cols["sex"] = ["0", "1"] * (len(cols["y_true"]) // 2)  # sex 0/1 -> medium when computed
    raw = table_from_columns(cols)
    prior = tmp_path / "m.json"
    forged = map_headers(raw.headers)  # header-only: every canonical name is high
    assert forged.all_high
    forged.decided_by = "file"
    forged.write(prior)
    fresh = map_headers(raw.headers, raw.columns)
    assert fresh.entry("sex").confidence == "medium"
    with pytest.raises(HaltError) as ei:
        check_h07(raw.headers, prior, non_interactive=True, fresh=fresh)
    assert ei.value.code == "H07"
    assert "computed from this table" in ei.value.message


def test_non_tty_without_yes_prints_the_table_then_halts_h07(tmp_path: Path, capsys, monkeypatch):
    csv_path, _ = _cohort_csv(tmp_path)
    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: False)
    rc = main(["map", "--input", str(csv_path), "--out", str(tmp_path / "m.json")])
    captured = capsys.readouterr()
    assert rc == EXIT_HALT
    assert "original header" in captured.out and "'y_true'" in captured.out
    assert "run interactively or pass --yes with a prior mapping.json" in captured.err
    assert not (tmp_path / "m.json").exists()


def test_non_tty_with_stdin_closed_exits_3_within_the_timeout(tmp_path: Path):
    csv_path, _ = _cohort_csv(tmp_path)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proofpack.cli",
            "map",
            "--input",
            str(csv_path),
            "--out",
            str(tmp_path / "m.json"),
        ],
        env=_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == EXIT_HALT
    assert "HALT H07" in proc.stderr and "Traceback" not in proc.stderr
    assert "original header" in proc.stdout


def test_tty_prompt_accept_edit_and_abort(tmp_path: Path, capsys, monkeypatch):
    cols = make_cohort()
    cols["label"] = cols.pop("y_true")
    cols.pop("sex")
    cols["gender"] = ["1", "2"] * (len(cols["label"]) // 2)  # the only non-high role
    csv_path = write_csv(tmp_path / "t.csv", cols)
    out = tmp_path / "m.json"
    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: True)
    answers = iter(["a"])  # only gender (medium) is prompted; label is high (synonym+values)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    rc = main(["map", "--input", str(csv_path), "--out", str(out)])
    assert rc == EXIT_OK
    written = Mapping.read(out)
    assert written.decided_by == "interactive"
    assert written.entry("gender").role == "sex"
    assert "accepted interactively" in written.entry("gender").notes
    assert written.timestamp.endswith("+00:00")
    # edit: gender -> ignore
    answers = iter(["e", "not_a_role", "e", "ignore"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    rc = main(["map", "--input", str(csv_path), "--out", str(out)])
    assert rc == EXIT_OK
    written = Mapping.read(out)
    assert written.entry("gender").role is None
    assert "edited interactively" in written.entry("gender").notes
    # abort: nothing written
    out.unlink()
    answers = iter(["q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    rc = main(["map", "--input", str(csv_path), "--out", str(out)])
    assert rc == EXIT_HALT
    assert "aborted at the prompt" in capsys.readouterr().err
    assert not out.exists()


def test_confirm_helper_prompts_once_per_non_high_role_only():
    cols = _cols(label=["0", "1"] * 10, gender=["1", "2"] * 10, x=["a", "b", "c"] * 7)
    m = map_headers(list(cols), cols)
    assert [r.original for r in m.non_high] == ["gender"]
    prompts: list[str] = []

    def ask(p):
        prompts.append(p)
        return "a"

    _confirm_interactive(m, ask=ask, say=lambda s: None)
    assert len(prompts) == 1 and "'gender'" in prompts[0]
    assert m.decided_by == "interactive"


# --------------------------------------------------------------------------- mapping.json


def test_mapping_json_round_trip_and_hash_is_order_independent(tmp_path: Path):
    raw = load_table(FIXTURES / "sepsis_2019.csv")
    m = map_headers(raw.headers, raw.columns)
    sha = m.write(tmp_path / "mapping.json")
    assert sha == hashlib.sha256((tmp_path / "mapping.json").read_bytes()).hexdigest()
    back = Mapping.read(tmp_path / "mapping.json")
    assert back.file_sha256 == sha
    assert _roles(back) == _roles(m)
    assert back.value_summaries == m.value_summaries
    assert back.header_set_sha256 == m.header_set_sha256
    reversed_headers = list(reversed(raw.headers))
    m2 = map_headers(reversed_headers, raw.columns)
    assert m2.header_set_sha256 == m.header_set_sha256
    assert [r.original for r in m2.roles] == reversed_headers
    data = json.loads((tmp_path / "mapping.json").read_text(encoding="utf-8"))
    assert set(data) == {
        "header_set_sha256",
        "roles",
        "value_summaries",
        "decided_by",
        "timestamp",
    }
    assert set(data["roles"][0]) == {"original", "role", "confidence", "source", "notes"}
    assert data["roles"][0]["original"] == "patient"
    assert data["decided_by"] == "proposed"


def test_value_summaries_in_mapping_json_are_the_suppressed_ones():
    raw = load_table(FIXTURES / "sepsis_2019.csv")
    m = map_headers(raw.headers, raw.columns)
    patient = m.value_summaries["patient"]
    # 10 subjects x 5 rows: every id has count 5 < k=10 -> all suppressed
    assert patient["n_unique"] == 10
    assert patient["top"] == [[SUPPRESSED, 10]]
    blob = json.dumps(m.value_summaries)
    assert "p000100" not in blob
    label = m.value_summaries["SepsisLabel"]
    assert label["split"] is not None and label["n_unique"] == 2


# --------------------------------------------------------------------------- privacy


def test_fixture_halts_and_two_constructed_ones_carry_no_header_or_value():
    """Walks every halt the committed fixtures raise, plus two constructed ones.

    Renamed in repair 1 (FA-N11): the old id ``test_no_halt_carries_a_header_or_value``
    asserted a universal the test does not inspect.
    """
    seen = 0
    for fid in FIXTURE_IDS:
        spec = json.loads((FIXTURES / f"{fid}.expected.json").read_text(encoding="utf-8"))
        if spec["halt"] is None or spec.get("criteria"):
            continue
        raw = load_table(FIXTURES / f"{fid}.csv")
        with pytest.raises(HaltError) as ei:
            map_headers(raw.headers, raw.columns)
        seen += 1
        blob = ei.value.message + json.dumps(ei.value.detail)
        for h in raw.headers:
            if len(h) >= 2:
                assert h not in blob, (fid, h)
        for col in raw.columns.values():
            for v in col[:50]:
                if v is not None and len(v) >= 3:
                    assert v not in blob, (fid, v)
    assert seen >= 3
    cols = _cols(**{"SECRET_HDR_label": ["0", "1"] * 5, "secret_hdr_label": ["0", "1"] * 5})
    with pytest.raises(HaltError) as ei:
        map_headers(list(cols), cols)
    assert "SECRET_HDR" not in ei.value.message + json.dumps(ei.value.detail)
    cols = _cols(Patient_ID=["SECRETVAL"] * 10, Subject_ID=["SECRETVAL"] * 10)
    with pytest.raises(HaltError) as ei:
        map_headers(list(cols), cols)
    blob = ei.value.message + json.dumps(ei.value.detail)
    assert ei.value.code == "E01" and "SECRETVAL" not in blob and "Patient_ID" not in blob


# --------------------------------------------------------------------------- H11 by values


def test_h11_fires_on_a_visit_column_holding_dates_and_period_can_cover_it():
    raw = load_table(FIXTURES / "sepsis_visit_dates.csv")
    m = map_headers(raw.headers, raw.columns)
    with pytest.raises(HaltError) as ei:
        check_h11(raw.headers, None, mapping=m)
    assert ei.value.code == "H11" and ei.value.detail == {"date_like_columns": 1}
    check_h11(raw.headers, {"column": "visit", "granularity": "quarter"}, mapping=m)
    check_h11(raw.headers, {"column": "event_date", "granularity": "quarter"}, mapping=m)
    with pytest.raises(HaltError):
        check_h11(raw.headers, {"column": "other", "granularity": "quarter"}, mapping=m)
    # header-only call keeps the day-1 behaviour: 'visit' is not date-like by name
    check_h11(raw.headers, None)


def test_h11_two_columns_sharing_the_event_date_role_are_not_covered_by_the_role_name():
    cols = make_cohort()
    n = len(cols["y_true"])
    cols["event_date"] = ["2026-02-15"] * n
    cols["scan_date"] = ["2026-02-15"] * n
    raw = table_from_columns(cols)
    m = map_headers(raw.headers, raw.columns)
    assert m.holders("event_date") == ["event_date", "scan_date"]
    with pytest.raises(HaltError) as ei:
        check_h11(raw.headers, {"column": "event_date", "granularity": "quarter"}, mapping=m)
    assert ei.value.code == "H11" and ei.value.detail == {"date_like_columns": 1}


# --------------------------------------------------------------------------- CLI table


def test_cli_map_prints_the_table_for_the_sepsis_fixture_in_a_subprocess(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proofpack.cli",
            "map",
            "--input",
            str(FIXTURES / "sepsis_2019.csv"),
            "--out",
            str(tmp_path / "m.json"),
        ],
        env=_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert proc.returncode == EXIT_HALT  # non-TTY, no --yes: table then H07
    lines = proc.stdout.splitlines()
    assert lines[0].split() == ["original", "header", "->", "role", "conf", "value", "summary"]
    row = next(line for line in lines if line.strip().startswith("'SepsisLabel'"))
    assert "-> y_true" in row and " high " in row and "int; 2 unique; 0.0% missing" in row
    gender = next(line for line in lines if line.strip().startswith("'Gender'"))
    assert "-> sex" in gender and " medium " in gender
    assert any("note: no dictionary declared for 0/1" in line for line in lines)
    assert "p000100" not in proc.stdout  # every patient id has count 5 < k


def test_cli_map_prints_non_ascii_headers_with_pythonutf8(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proofpack.cli",
            "map",
            "--input",
            str(FIXTURES / "sepsis_unicode_headers.csv"),
            "--out",
            str(tmp_path / "m.json"),
        ],
        env=_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert proc.returncode == EXIT_HALT
    assert "'Température'" in proc.stdout and "-> ignore" in proc.stdout
