"""Day 6 A, repair 1 (A-P1 the full mapper) - the lens findings, one test per fix.

Every test names the literal input it feeds and the figures it asserts. Each test that
fixes a finding failed at 555a5e1 (the first ``E`` line is in the repair-1 note); the
seven tests whose docstring begins "Pins" passed there and are here to observe a rule a
lens mutant changed without any test noticing (FA-N10, FA-N3; the count is from lens 2,
RG-N2).
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

import proofpack
from conftest import make_cohort, make_criteria, write_csv, write_yaml
from proofpack.cli import _confirm_interactive, main
from proofpack.errors import EXIT_HALT, EXIT_OK, HaltError
from proofpack.io import declare
from proofpack.io.mapping import Mapping, check_h07, check_h11, map_headers
from proofpack.io.profile import SUPPRESSED, SUPPRESSION_K, profile_column
from proofpack.io.schema import header_set_sha256, load_table, table_from_columns

pytestmark = pytest.mark.day6

FIXTURES = Path(__file__).parent / "fixtures" / "mapping"
SRC = Path(proofpack.__file__).parents[1]


def _cols(**kw) -> dict:
    return {k: list(v) for k, v in kw.items()}


# --------------------------------------------------------------------------- FA-B1 / RG-NB-3


def test_numeric_min_max_below_the_floor_print_as_suppressed(tmp_path: Path):
    """At 555a5e1 the first column printed ``min 7 max 100`` while listing 7 as suppressed."""
    assert SUPPRESSION_K == 10
    s = profile_column(["100"] * 41 + ["7"] * 9)
    assert (s.min, s.max) == (SUPPRESSED, "100")
    assert s.render() == (
        "int; 2 unique; 0.0% missing; min <suppressed> max 100; "
        "values: 100 (41), <suppressed> (1 distinct below k=10)"
    )
    assert "7" not in s.render().replace("k=10", "").replace("100", "").replace("0.0%", "")
    s = profile_column(["40"] * 49 + ["97"])
    assert (s.min, s.max) == ("40", SUPPRESSED)
    assert "97" not in s.render() and "97" not in json.dumps(s.to_dict())
    rng = random.Random(20260918)
    ids = [str(rng.randint(1_000_000, 9_999_999)) for _ in range(50)]
    assert len(set(ids)) == 50
    s = profile_column(ids)
    assert (s.min, s.max) == (SUPPRESSED, SUPPRESSED)
    blob = s.render() + json.dumps(s.to_dict())
    for v in ids:
        assert v not in blob
    # the boundary: 10 rows hold the max -> shown; 9 -> the literal
    assert profile_column(["0"] * 40 + ["1"] * 10).max == "1"
    assert profile_column(["0"] * 41 + ["1"] * 9).max == SUPPRESSED
    # "1" and "1.0" are the same number: 5 + 5 rows hold the max -> shown
    assert profile_column(["0"] * 40 + ["1"] * 5 + ["1.0"] * 5).max == "1"
    # the mapper's signals keep the true extremes (unit_interval needs them)
    s = profile_column([f"{i / 100:.2f}" for i in range(50)])
    assert s.signals["min"] == 0.0 and s.signals["max"] == 0.49 and s.signals["unit_interval"]
    assert (s.min, s.max) == (SUPPRESSED, SUPPRESSED)
    # the sepsis fixture's Age column (50 distinct floats) through map_headers and the table
    raw = load_table(FIXTURES / "sepsis_2019.csv")
    m = map_headers(raw.headers, raw.columns)
    age = m.value_summaries["Age"]
    assert age["n_unique"] == 50 and (age["min"], age["max"]) == (SUPPRESSED, SUPPRESSED)
    table = m.table()
    assert "20.04" not in table and "84.65" not in table and "-198.06" not in table
    assert "min <suppressed> max <suppressed>" in table
    # the two-valued label keeps its shown extremes (34 and 16 rows)
    assert (m.value_summaries["SepsisLabel"]["min"], m.value_summaries["SepsisLabel"]["max"]) == (
        "0",
        "1",
    )
    m.write(tmp_path / "m.json")
    written = (tmp_path / "m.json").read_text(encoding="utf-8")
    assert "20.04" not in written and "84.65" not in written


def test_date_min_max_are_months_and_not_put_through_the_floor():
    """Pins the date rule as it stands (D1 section 1 coarsening): three rows, two months."""
    s = profile_column(["2024-03-15", "2024-03-16", "2025-11-02"])
    assert (s.min, s.max) == ("2024-03", "2025-11") and s.values_shown is False


# --------------------------------------------------------------------------- FA-B2 / RG-NB-2


@pytest.mark.parametrize(
    "unit, n",
    [
        ("patient_id/study_id", 2),
        ("patient_id / study_id", 2),
        ("patient_id:study_id", 2),
        ("patient_id-study_id", 2),
        ("patient_id study_id", 2),
        ("patient_id\tstudy_id", 2),
        ("subject_id hadm_id", 2),
        ("patient_id & study_id", 2),
        ("patient_id;study_id", 2),
        ("patient_id|study_id", 2),
        ("patient-id", 2),  # a hyphenated single name counts two tokens (README step 3)
        (["patient_id", "patient_id"], 2),
        ("a, b, c", 3),
    ],
)
def test_separators_the_lens_listed_reach_e01(unit, n):
    """At 555a5e1 the first seven halted H08 ``declaration invalid at clustering/unit: enum``."""
    with pytest.raises(HaltError) as ei:
        declare.validate_dict(make_criteria(clustering={"unit": unit, "declared_by": "t"}))
    assert ei.value.code == "E01"
    assert (
        ei.value.message == f"clustering.unit names {n} columns; reduce your case key to one column"
    )
    assert ei.value.detail == {"n_case_key_columns": n}


@pytest.mark.parametrize("key", ["columns", "column", "key", "keys", "units", "fields"])
def test_clustering_list_keys_of_two_halt_e01_and_of_one_do_not(key):
    """At 555a5e1 ``{unit: case_id, columns: [a, b]}`` passed validate_dict silently."""
    with pytest.raises(HaltError) as ei:
        declare.validate_dict(
            make_criteria(clustering={"unit": "case_id", key: ["a", "b"], "declared_by": "t"})
        )
    assert ei.value.code == "E01"
    assert (
        ei.value.message == f"clustering.{key} lists 2 columns; reduce your case key to one column"
    )
    assert ei.value.detail == {"n_case_key_columns": 2, "key": key}
    declare.validate_dict(
        make_criteria(clustering={"unit": "case_id", key: ["a"], "declared_by": "t"})
    )  # one column listed: no halt


def test_one_column_units_outside_the_enum_stay_h08():
    """``subject_id`` and ``random_id`` are one token each: the schema's enum, not E01."""
    for unit in ("subject_id", "random_id"):
        with pytest.raises(HaltError) as ei:
            declare.validate_dict(make_criteria(clustering={"unit": unit, "declared_by": "t"}))
        assert ei.value.code == "H08" and ei.value.detail["path"] == "clustering/unit"
    for unit in ("case_id", "none"):
        declare.validate_dict(make_criteria(clustering={"unit": unit, "declared_by": "t"}))


def test_slash_composite_unit_via_the_cli_is_e01_not_h08(tmp_path: Path, capsys):
    """The MIMIC notation ``subject_id/hadm_id`` in criteria.yaml, through ``map`` and ``run``."""
    crit = json.loads(json.dumps(make_criteria()))
    crit["clustering"] = {"unit": "subject_id/hadm_id", "declared_by": "t"}
    yml = write_yaml(tmp_path / "c.yaml", crit)
    csv_path = FIXTURES / "mimic_composite_key.csv"
    for argv in (
        ["map", "--input", str(csv_path), "--criteria", str(yml), "--out", str(tmp_path / "m")],
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(tmp_path / "p")],
    ):
        rc = main(argv)
        err = capsys.readouterr().err
        assert rc == EXIT_HALT, argv
        assert err.splitlines()[0] == (
            "HALT E01: clustering.unit names 2 columns; reduce your case key to one column"
        )
        assert "H08" not in err and "Traceback" not in err
    assert not (tmp_path / "m").exists() and not (tmp_path / "p").exists()


# --------------------------------------------------------------------------- FA-N1


def test_yes_refuses_a_proposed_prior(tmp_path: Path, capsys):
    """``run`` writes ``decided_by: proposed``; at 555a5e1 ``map --yes`` then accepted it."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    yml = write_yaml(tmp_path / "c.yaml", make_criteria())
    pack = tmp_path / "pack"
    rc = main(
        ["--quiet", "run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(pack)]
    )
    assert rc == EXIT_OK
    prior = pack / "mapping.json"
    before = prior.read_bytes()
    assert json.loads(before)["decided_by"] == "proposed"
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: non-interactive mode requires a confirmed mapping.json (decided_by "
        "interactive or file); this one was not confirmed: run proofpack map interactively once"
    )
    assert '"decided_by": "proposed"' in err
    assert prior.read_bytes() == before  # not rewritten
    # the same prior confirmed once is then accepted
    m = Mapping.read(prior)
    m.decided_by = "interactive"
    m.write(prior)
    assert (
        main(["--quiet", "map", "--input", str(csv_path), "--out", str(prior), "--yes"]) == EXIT_OK
    )
    assert Mapping.read(prior).decided_by == "file"
    # a day-1 file with no decided_by key reads as "file" and is accepted
    data = json.loads(prior.read_text(encoding="utf-8"))
    del data["decided_by"]
    prior.write_text(json.dumps(data), encoding="utf-8")
    assert Mapping.read(prior).decided_by == "file"
    assert (
        main(["--quiet", "map", "--input", str(csv_path), "--out", str(prior), "--yes"]) == EXIT_OK
    )


# --------------------------------------------------------------------------- FA-N2, N3, N4, N5


def test_all_high_table_asks_once_before_interactive(tmp_path: Path, capsys, monkeypatch):
    """At 555a5e1 the seeded cohort (every role high) asked nothing and wrote ``interactive``."""
    cols = make_cohort()
    m = map_headers(list(cols), cols)
    assert m.non_high == [] and m.decided_by == "proposed"
    prompts: list[str] = []

    def ask(p):
        prompts.append(p)
        return "a"

    _confirm_interactive(m, ask=ask, say=lambda s: None)
    assert prompts == [f"every role is high ({len(m.roles)} columns): [a]ccept / [q]uit? "]
    assert m.decided_by == "interactive"
    with pytest.raises(HaltError) as ei:
        _confirm_interactive(map_headers(list(cols), cols), ask=lambda p: "q", say=lambda s: None)
    assert ei.value.code == "H07" and "aborted at the prompt" in ei.value.message
    # through main(): the one prompt is consumed; 'q' leaves no file
    csv_path = write_csv(tmp_path / "t.csv", cols)
    out = tmp_path / "m.json"
    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: True)
    answers = iter(["q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert main(["map", "--input", str(csv_path), "--out", str(out)]) == EXIT_HALT
    assert not out.exists()
    answers = iter(["a"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert main(["map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    assert Mapping.read(out).decided_by == "interactive"
    capsys.readouterr()


def test_accept_and_edit_keep_the_computed_confidence():
    """Pins (passes at 555a5e1; lens mutants L18/L26 set high on accept/edit unobserved).

    ``gender`` 1/2 is ``sex`` at medium; accepting keeps medium, editing to ``ignore``
    keeps medium with the role cleared, so ``--yes`` still needs Josh's ruling (note D5).
    """
    cols = _cols(label=["0", "1"] * 10, gender=["1", "2"] * 10)
    m = map_headers(list(cols), cols)
    assert (m.entry("gender").role, m.entry("gender").confidence) == ("sex", "medium")
    _confirm_interactive(m, ask=lambda p: "a", say=lambda s: None)
    assert m.entry("gender").confidence == "medium" and not m.all_high
    m = map_headers(list(cols), cols)
    answers = iter(["e", "ignore"])
    _confirm_interactive(m, ask=lambda p: next(answers), say=lambda s: None)
    assert m.entry("gender").role is None and m.entry("gender").confidence == "medium"
    assert m.entry("gender").notes[-1] == "edited interactively"


def test_edit_to_a_role_another_column_holds_is_refused_at_the_prompt():
    """At 555a5e1 ``gender`` edited to ``y_true`` beside ``y_true`` was written (two holders)."""
    cols = make_cohort()
    cols.pop("sex")
    cols["gender"] = ["1", "2"] * (len(cols["y_true"]) // 2)
    m = map_headers(list(cols), cols)
    assert [r.original for r in m.non_high] == ["gender"]
    said: list[str] = []
    answers = iter(["e", "y_true", "e", "sex"])  # refused, then re-prompted, then accepted
    _confirm_interactive(m, ask=lambda p: next(answers), say=said.append)
    assert said == ["  y_true is already held by 'y_true': choose another"]
    assert m.holders("y_true") == ["y_true"]
    assert m.entry("gender").role == "sex"
    assert m.entry("gender").notes[-1] == "edited interactively"


def test_second_edit_to_an_unheld_attr_role_is_accepted():
    cols = make_cohort()
    cols.pop("sex")
    cols["gender"] = ["1", "2"] * (len(cols["y_true"]) // 2)
    m = map_headers(list(cols), cols)
    answers = iter(["e", "attr_coding"])
    _confirm_interactive(m, ask=lambda p: next(answers), say=lambda s: None)
    assert m.entry("gender").role == "attr_coding"


def test_ctrl_c_at_the_prompt_is_h07(tmp_path: Path, capsys, monkeypatch):
    """At 555a5e1 ``KeyboardInterrupt`` from ``input`` left ``main()`` uncaught."""
    cols = make_cohort()
    cols.pop("sex")
    cols["gender"] = ["1", "2"] * (len(cols["y_true"]) // 2)
    csv_path = write_csv(tmp_path / "t.csv", cols)
    out = tmp_path / "m.json"
    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: True)

    def ctrl_c(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", ctrl_c)
    rc = main(["map", "--input", str(csv_path), "--out", str(out)])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == "HALT H07: mapping interrupted at the prompt; nothing written"
    assert "Traceback" not in err and not out.exists()
    # the all-high prompt too
    csv2 = write_csv(tmp_path / "t2.csv", make_cohort())
    assert main(["map", "--input", str(csv2), "--out", str(out)]) == EXIT_HALT
    assert "interrupted at the prompt" in capsys.readouterr().err and not out.exists()


def test_eof_at_the_prompt_is_h07(tmp_path: Path, capsys, monkeypatch):
    """``input`` raising EOFError at the gender prompt and at the all-high prompt: H07, no file."""
    cols = make_cohort()
    cols.pop("sex")
    cols["gender"] = ["1", "2"] * (len(cols["y_true"]) // 2)
    csv_path = write_csv(tmp_path / "t.csv", cols)
    out = tmp_path / "m.json"
    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: True)

    def eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    rc = main(["map", "--input", str(csv_path), "--out", str(out)])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and not out.exists()
    assert err.splitlines()[0] == (
        "HALT H07: stdin closed at the prompt: run interactively or pass --yes"
    )
    assert "Traceback" not in err
    csv2 = write_csv(tmp_path / "t2.csv", make_cohort())
    assert main(["map", "--input", str(csv2), "--out", str(out)]) == EXIT_HALT
    assert "stdin closed at the prompt" in capsys.readouterr().err and not out.exists()


# --------------------------------------------------------------------------- FA-N6


@pytest.mark.parametrize(
    "prior",
    [
        {"header_set_sha256": "HASH", "roles": "SECRET_HDR"},
        {"header_set_sha256": "HASH", "roles": [1, 2]},
        {"header_set_sha256": 123, "roles": []},
        {"header_set_sha256": "HASH", "roles": [{"original": 1, "confidence": "high"}]},
        {"header_set_sha256": "HASH", "roles": [{"original": "x", "confidence": None}]},
        {"header_set_sha256": "HASH", "roles": [], "value_summaries": None},
        [],
    ],
)
def test_malformed_prior_under_yes_halts_h07_not_exit_5(prior, tmp_path: Path, capsys):
    """At 555a5e1 the first three exited 5 ``internal error: AttributeError`` / ``TypeError``."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    if isinstance(prior, dict) and prior.get("header_set_sha256") == "HASH":
        prior["header_set_sha256"] = header_set_sha256(list(cols))
    path = tmp_path / "m.json"
    path.write_text(json.dumps(prior), encoding="utf-8")
    if isinstance(prior, dict) and prior.get("value_summaries", 0) is None:
        # a null value_summaries reads as {} and the file is otherwise well formed
        assert Mapping.read(path).value_summaries == {}
        return
    rc = main(["map", "--input", str(csv_path), "--out", str(path), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == "HALT H07: mapping.json could not be read"
    assert "internal error" not in err and "SECRET_HDR" not in err and "Traceback" not in err


# --------------------------------------------------------------------------- FA-N7


def test_dash_separated_dates_are_typed_date_and_halt_h11():
    """At 555a5e1 ``15-03-2024`` values were ``string`` (free text) and passed H11."""
    cols = _cols(visit=["15-03-2024", "16-03-2024", "02-11-2025"] * 10, label=["0", "1"] * 15)
    s = profile_column(cols["visit"])
    assert s.inferred_type == "date" and (s.min, s.max) == ("2024-03", "2025-11")
    assert s.values_shown is False and "15-03-2024" not in json.dumps(s.to_dict())
    m = map_headers(list(cols), cols)
    assert (m.entry("visit").role, m.entry("visit").confidence) == ("event_date", "medium")
    with pytest.raises(HaltError) as ei:
        check_h11(list(cols), None, mapping=m)
    assert ei.value.code == "H11" and ei.value.detail == {"date_like_columns": 1}
    check_h11(list(cols), {"column": "visit", "granularity": "month"}, mapping=m)
    # Excel serials stay integers (not typed date): 45000..45029 -> int, row_id by values
    serial = _cols(visit=[str(45000 + i) for i in range(30)], label=["0", "1"] * 15)
    assert profile_column(serial["visit"]).inferred_type == "int"
    m2 = map_headers(list(serial), serial)
    assert (m2.entry("visit").role, m2.entry("visit").confidence) == ("row_id", "medium")
    check_h11(list(serial), None, mapping=m2)  # no halt: not a date by header or by values


# --------------------------------------------------------------------------- FA-N8


def test_cp1252_stdout_prints_the_table_with_escapes(tmp_path: Path):
    """At 555a5e1 this ended ``internal error: UnicodeEncodeError``, exit 5, no table."""
    cols = _cols(**{"体温": ["36.6", "37.1"] * 10, "label": ["0", "1"] * 10})
    csv_path = write_csv(tmp_path / "cjk.csv", cols)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    env.pop("PYTHONUTF8", None)
    env["PYTHONIOENCODING"] = "cp1252"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proofpack.cli",
            "map",
            "--input",
            str(csv_path),
            "--out",
            str(tmp_path / "m"),
        ],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
    )
    out = proc.stdout.decode("cp1252", errors="replace")
    err = proc.stderr.decode("cp1252", errors="replace")
    assert proc.returncode == EXIT_HALT, (out, err)  # non-TTY, no --yes: table then H07
    assert "internal error" not in err and "UnicodeEncodeError" not in err
    assert "original header" in out and "\\u4f53\\u6e29" in out and "-> ignore" in out
    assert err.splitlines()[0].startswith("HALT H07: stdin is not a terminal")


# --------------------------------------------------------------------------- FA-N12


def test_quiet_at_a_terminal_prints_the_table_the_prompt_refers_to(
    tmp_path: Path, capsys, monkeypatch
):
    """At 555a5e1 ``--quiet`` at a terminal prompted for ``gender`` with no table printed."""
    cols = make_cohort()
    cols.pop("sex")
    cols["gender"] = ["1", "2"] * (len(cols["y_true"]) // 2)
    csv_path = write_csv(tmp_path / "t.csv", cols)
    out = tmp_path / "m.json"
    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: True)
    answers = iter(["a"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    rc = main(["map", "--input", str(csv_path), "--out", str(out), "--quiet"])
    captured = capsys.readouterr()
    assert rc == EXIT_OK
    assert captured.out.splitlines()[0].split() == [
        "original",
        "header",
        "->",
        "role",
        "conf",
        "value",
        "summary",
    ]
    assert "'gender'" in captured.out and "mapping written" not in captured.out
    # not a terminal: --quiet prints nothing and halts H07 (unchanged)
    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: False)
    rc = main(["map", "--input", str(csv_path), "--out", str(out), "--quiet"])
    captured = capsys.readouterr()
    assert rc == EXIT_HALT and captured.out == "" and captured.err == ""


# --------------------------------------------------------------------------- FA-N10 mutants


def test_free_text_guard_two_unique_column_of_singletons_is_not_free_text():
    """Pins (L09): ``["a", "b"]`` is 2 unique of 2 rows; the <= 2 exemption keeps the split."""
    s = profile_column(["a", "b"])
    assert s.free_text is False and s.values_shown is True
    assert s.top == [[SUPPRESSED, 2]] and s.split == [[SUPPRESSED, 2]]
    s3 = profile_column(["a", "b", "c"])
    assert s3.free_text is True and s3.top == [] and s3.split is None


def test_label_with_ten_distinct_values_is_consistent_and_eleven_is_a_conflict():
    """Pins (L13): the y_true consistency threshold is 10 distinct values."""
    ten = _cols(label=[str(i % 10) for i in range(40)])
    m = map_headers(list(ten), ten)
    assert (m.entry("label").role, m.entry("label").confidence, m.entry("label").notes) == (
        "y_true",
        "high",
        [],
    )
    eleven = _cols(label=[str(i % 11) for i in range(44)])
    m = map_headers(list(eleven), eleven)
    assert (m.entry("label").role, m.entry("label").confidence) == ("y_true", "low")
    assert m.entry("label").notes == ["label column holds 11 distinct values"]


def test_two_partial_tokens_for_one_role_are_both_low_with_the_note():
    """Pins (L14): ``anchor_age`` + ``age_years`` (two partial tokens for age) -> both low."""
    cols = _cols(
        anchor_age=[str(20 + i % 30) for i in range(40)],
        age_years=[str(30 + i % 20) for i in range(40)],
        label=["0", "1"] * 20,
    )
    m = map_headers(list(cols), cols)
    for h in ("anchor_age", "age_years"):
        e = m.entry(h)
        assert (e.role, e.confidence, e.source) == ("age", "low", "partial"), h
        assert e.notes == ["2 headers carry a token for age; choose one"], h
    one = _cols(anchor_age=cols["anchor_age"], label=cols["label"])
    assert map_headers(list(one), one).entry("anchor_age").confidence == "medium"


def test_hash_mismatch_detail_carries_twelve_character_prefixes(tmp_path: Path):
    """Pins (L20): the H07 detail holds the first 12 characters of each hash, not the hashes."""
    cols = make_cohort()
    other = dict(cols)
    other["extra"] = ["0"] * len(cols["y_true"])
    prior = map_headers(list(other), other)
    prior.decided_by = "interactive"
    prior.write(tmp_path / "m.json")
    with pytest.raises(HaltError) as ei:
        check_h07(list(cols), tmp_path / "m.json", non_interactive=True)
    d = ei.value.detail
    assert set(d) == {"expected", "observed"}
    assert d["expected"] == prior.header_set_sha256[:12] and len(d["expected"]) == 12
    assert d["observed"] == header_set_sha256(list(cols))[:12] and len(d["observed"]) == 12


def test_missing_pct_is_rounded_to_two_decimals():
    """Pins (L22): 1 missing of 3 sampled rows -> 33.33, not 33.333333333333336."""
    s = profile_column(["x", None, "x"])
    assert s.missing_pct == 33.33 and s.to_dict()["missing_pct"] == 33.33
    assert profile_column(["x"] * 6 + [None]).missing_pct == 14.29


def test_ingest_still_accepts_a_confirmed_prior_and_the_day1_medium_refusal_holds(
    tmp_path: Path,
):
    """The two day-1 ``--yes`` paths through ``gates.ingest`` with a confirmed prior."""
    cols = make_cohort()
    m = map_headers(list(cols))
    m.decided_by = "file"
    m.write(tmp_path / "mapping.json")
    from proofpack.gates import ingest

    res = ingest(
        table_from_columns(cols),
        declare.validate_dict(make_criteria()),
        mapping_path=tmp_path / "mapping.json",
        non_interactive=True,
    )
    assert res.mapping.decided_by == "file"
    m.decided_by = "proposed"
    m.write(tmp_path / "mapping.json")
    with pytest.raises(HaltError) as ei:
        ingest(
            table_from_columns(cols),
            declare.validate_dict(make_criteria()),
            mapping_path=tmp_path / "mapping.json",
            non_interactive=True,
        )
    assert ei.value.code == "H07" and ei.value.detail == {"decided_by": "proposed"}
