"""Day 6 A, repair 2 (A-P1 the full mapper) - the lens-2 findings, one test per fix.

Every test names the literal input it feeds and the figures it asserts. Each test that
fixes a finding failed at e92989b (the first ``E`` line is in the repair-2 note); the two
tests whose docstring begins "Pins" passed there and are here to observe a rule a lens
mutant changed without any test noticing (FA-B1's M05, FA-N1's M24).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import make_cohort, make_criteria, write_csv, write_yaml
from proofpack.cli import _confirm_interactive, main
from proofpack.errors import EXIT_HALT, EXIT_OK, HaltError
from proofpack.io import declare
from proofpack.io.mapping import Mapping, apply_mapping, check_h07, check_h11, map_headers
from proofpack.io.profile import profile_column
from proofpack.io.schema import header_set_sha256

pytestmark = pytest.mark.day6

DEC11 = "reduce your case key to one column"


def _cols(**kw) -> dict:
    return {k: list(v) for k, v in kw.items()}


def _answers(*seq):
    it = iter(seq)
    return lambda prompt: next(it)


def _two_partials() -> dict:
    """``patient_nbr`` repeats every three rows, ``mrn_local`` every two (60 rows)."""
    return _cols(
        row_id=[str(i) for i in range(60)],
        label=["0", "1"] * 30,
        prob=[f"{(i % 10) / 10:.1f}" for i in range(60)],
        patient_nbr=[str(1000 + i // 3) for i in range(60)],
        mrn_local=[str(500 + i // 2) for i in range(60)],
    )


# --------------------------------------------------------------------------- FA-B1


def test_two_partial_case_id_headers_reach_e01_at_apply_not_h07(tmp_path: Path, capsys):
    """At e92989b ``run`` on this table was H07 ``two columns map to the same canonical role``."""
    cols = _two_partials()
    m = map_headers(list(cols), cols)
    for h in ("patient_nbr", "mrn_local"):
        e = m.entry(h)
        assert (e.role, e.confidence, e.source) == ("case_id", "low", "partial"), h
        assert e.notes == [
            "header resembles a case identifier; confirm or ignore",
            "2 headers carry a token for case_id; choose one",
        ], h
    with pytest.raises(HaltError) as ei:
        apply_mapping(cols, m)
    assert ei.value.code == "E01"
    assert ei.value.message == (
        "2 columns are mapped to case_id (proofpack map: keep one, set the others to "
        "ignore); reduce your case key to one column"
    )
    assert ei.value.detail == {"n_case_id_columns": 2}
    # through main(): no prior, no --yes, clustering.unit case_id
    csv_path = write_csv(tmp_path / "it.csv", cols)
    yml = write_yaml(
        tmp_path / "c.yaml",
        make_criteria(clustering={"unit": "case_id", "declared_by": "t"}),
    )
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(tmp_path / "p")]
    )
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == "HALT E01: " + ei.value.message
    assert "H07" not in err and "Traceback" not in err
    assert "patient_nbr" not in err and "mrn_local" not in err
    assert not (tmp_path / "p").exists()
    # a prior mapping.json holding both (hand-written the way e92989b's prompt wrote it)
    m.decided_by = "interactive"
    m.write(tmp_path / "m.json")
    rc = main(
        [
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--mapping",
            str(tmp_path / "m.json"),
            "--out",
            str(tmp_path / "p2"),
        ]
    )
    assert rc == EXIT_HALT
    assert capsys.readouterr().err.splitlines()[0].endswith(DEC11)


def test_accept_of_a_second_holder_is_refused_at_the_prompt():
    """At e92989b ``a`` at both prompts wrote two ``case_id`` holders as ``interactive``."""
    cols = _two_partials()
    m = map_headers(list(cols), cols)
    assert [r.original for r in m.non_high] == ["patient_nbr", "mrn_local"]
    said: list[str] = []
    prompts: list[str] = []
    answers = iter(["a", "a", "e", "ignore"])

    def ask(p):
        prompts.append(p)
        return next(answers)

    _confirm_interactive(m, ask=ask, say=said.append)
    assert said == [
        "  case_id is already held by 'patient_nbr': edit this one (e) to ignore or another role"
    ]
    assert len(prompts) == 4  # a, a (refused), e, ignore
    assert m.holders("case_id") == ["patient_nbr"]
    assert m.entry("mrn_local").role is None
    assert m.entry("mrn_local").notes[-1] == "edited interactively"
    assert m.decided_by == "interactive"
    apply_mapping(cols, m)  # no halt
    # the other order: ignore the first, accept the second
    m = map_headers(list(cols), cols)
    answers = iter(["e", "ignore", "a"])
    _confirm_interactive(m, ask=lambda p: next(answers), say=said.append)
    assert m.holders("case_id") == ["mrn_local"] and len(said) == 1
    # a non-case_id pair: label + outcome are both y_true low by name
    two = _cols(label=["0", "1"] * 20, outcome=["0", "1"] * 20, prob=["0.2", "0.7"] * 20)
    m = map_headers(list(two), two)
    assert m.holders("y_true") == ["label", "outcome"]
    said.clear()
    answers = iter(["a", "a", "e", "ignore"])
    _confirm_interactive(m, ask=lambda p: next(answers), say=said.append)
    assert said == [
        "  y_true is already held by 'label': edit this one (e) to ignore or another role"
    ]
    assert m.holders("y_true") == ["label"]


def test_two_partial_case_id_tokens_are_not_counted_by_map_headers_e01():
    """Pins (lens-2 mutant M05): ``patient_weight`` + ``patient_height`` carry the ``patient``
    token and no case key; counting token claims in ``map_headers``'s E01 would halt this
    table. Two name claims (``patient_id`` + ``subject_id``) do halt there."""
    cols = _cols(
        label=["0", "1"] * 30,
        prob=[f"{(i % 10) / 10:.1f}" for i in range(60)],
        patient_weight=[str(60 + i % 25) for i in range(60)],
        patient_height=[str(150 + i % 40) for i in range(60)],
    )
    m = map_headers(list(cols), cols)  # no halt
    for h in ("patient_weight", "patient_height"):
        assert (m.entry(h).role, m.entry(h).confidence, m.entry(h).source) == (
            "case_id",
            "low",
            "partial",
        ), h
    named = _cols(
        label=cols["label"],
        patient_id=[str(i // 2) for i in range(60)],
        subject_id=[str(i // 3) for i in range(60)],
    )
    with pytest.raises(HaltError) as ei:
        map_headers(list(named), named)
    assert ei.value.code == "E01"
    assert ei.value.message == "2 columns resolve to case_id; " + DEC11


# --------------------------------------------------------------------------- FA-N7


def test_attr_twins_are_low_with_the_note_and_reach_the_prompt():
    """At e92989b ``Attr Site`` beside ``attr_site`` were both ``attr_site high`` (0 non-high)."""
    cols = _cols(
        row_id=[str(i) for i in range(60)],
        label=["0", "1"] * 30,
        **{"Attr Site": ["A", "B"] * 30, "attr_site": ["C", "D"] * 30},
    )
    m = map_headers(list(cols), cols)
    for h in ("Attr Site", "attr_site"):
        e = m.entry(h)
        assert (e.role, e.confidence, e.notes) == (
            "attr_site",
            "low",
            ["2 headers claim attr_site; choose one"],
        ), h
    assert [r.original for r in m.non_high] == ["Attr Site", "attr_site"]
    with pytest.raises(HaltError) as ei:
        apply_mapping(cols, m)
    assert ei.value.code == "H07" and ei.value.detail == {"role": "attr_site"}
    answers = iter(["e", "ignore", "a"])  # 'Attr Site' ignored, attr_site accepted
    _confirm_interactive(m, ask=lambda p: next(answers), say=lambda s: None)
    assert m.holders("attr_site") == ["attr_site"]
    assert list(apply_mapping(cols, m)) == ["row_id", "y_true", "Attr Site", "attr_site"]
    # one rater_ pair the same way; a lone attr_ column stays high
    pair = _cols(label=["0", "1"] * 10, rater_a=["0", "1"] * 10, **{"Rater A": ["1", "0"] * 10})
    m = map_headers(list(pair), pair)
    assert [r.confidence for r in m.roles] == ["high", "low", "low"]
    lone = _cols(label=["0", "1"] * 10, attr_site=["A", "B"] * 10)
    assert map_headers(list(lone), lone).entry("attr_site").confidence == "high"


# --------------------------------------------------------------------------- RG-N1


def test_all_high_prompt_reprompts_on_n_no_e_x_and_takes_a():
    """At e92989b ``n`` at the all-high prompt was taken as accept (``decided_by`` interactive).

    Until 1354758 this test was named ``..._on_anything_but_a_or_q``; it feeds the five
    answers ``n no e x a`` and asserts four ``answer a or q`` lines (the empty answer is
    ``tests/test_mapping_repair3.py::test_empty_answer_reprompts_at_both_prompts``).
    """
    cols = make_cohort()
    m = map_headers(list(cols), cols)
    assert m.non_high == []
    said: list[str] = []
    answers = iter(["n", "no", "e", "x", "a"])
    prompts: list[str] = []

    def ask(p):
        prompts.append(p)
        return next(answers)

    _confirm_interactive(m, ask=ask, say=said.append)
    assert len(prompts) == 5 and len(set(prompts)) == 1
    assert said == ["  answer a or q"] * 4
    assert m.decided_by == "interactive"
    m = map_headers(list(cols), cols)
    answers = iter(["n", "q"])
    with pytest.raises(HaltError) as ei:
        _confirm_interactive(m, ask=lambda p: next(answers), say=lambda s: None)
    assert ei.value.code == "H07" and m.decided_by == "proposed"


# --------------------------------------------------------------------------- FA-N5


def test_edit_prompt_refuses_bare_and_non_identifier_attr_names():
    """At e92989b ``attr_x y`` and the bare ``attr_`` were written as the role."""
    cols = make_cohort()
    cols.pop("sex")
    cols["gender"] = ["1", "2"] * (len(cols["y_true"]) // 2)
    m = map_headers(list(cols), cols)
    said: list[str] = []
    answers = iter(["e", "attr_x y", "e", "attr_", "e", "rater_", "e", "attr_x_y"])
    _confirm_interactive(m, ask=lambda p: next(answers), say=said.append)
    assert len(said) == 3 and all(
        s.startswith("  not a canonical role: choose one of") for s in said
    )
    assert said[0].endswith(", or attr_<name> / rater_<name> in lower-case letters, digits and _")
    assert m.entry("gender").role == "attr_x_y"
    # _ask lower-cases the answer, so ``Attr_X`` is the identifier attr_x; rater_b2 accepted
    for answer, role in (("Attr_X", "attr_x"), ("rater_b2", "rater_b2")):
        m = map_headers(list(cols), cols)
        _confirm_interactive(m, ask=_answers("e", answer), say=said.append)
        assert m.entry("gender").role == role and len(said) == 3


# --------------------------------------------------------------------------- FA-N6


def test_out_into_a_missing_directory_halts_h07_before_any_prompt(
    tmp_path: Path, capsys, monkeypatch
):
    """At e92989b this was exit 5 ``internal error: FileNotFoundError`` after the answers."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    out = tmp_path / "no_such_dir" / "m.json"
    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: True)
    asked: list[str] = []

    def ask(prompt=""):
        asked.append(prompt)
        return "a"

    monkeypatch.setattr("builtins.input", ask)
    rc = main(["map", "--input", str(csv_path), "--out", str(out)])
    captured = capsys.readouterr()
    assert rc == EXIT_HALT and asked == [] and captured.out == ""
    assert captured.err.splitlines()[0] == (
        "HALT H07: the directory for --out does not exist: create it or pass --out inside an "
        "existing directory"
    )
    assert "internal error" not in captured.err and "no_such_dir" not in captured.err
    assert not out.parent.exists()
    # the same command with the directory present writes the file
    out.parent.mkdir()
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    assert out.exists() and len(asked) == 1


# --------------------------------------------------------------------------- FA-N10


def test_ctrl_c_during_load_is_h07_not_a_traceback(tmp_path: Path, capsys, monkeypatch):
    """At e92989b ``KeyboardInterrupt`` raised from ``load_table`` propagated out of ``main()``."""
    csv_path = write_csv(tmp_path / "t.csv", make_cohort())

    def ctrl_c(path):
        raise KeyboardInterrupt

    monkeypatch.setattr("proofpack.io.schema.load_table", ctrl_c)
    rc = main(["map", "--input", str(csv_path), "--out", str(tmp_path / "m.json")])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == "HALT H07: mapping interrupted; nothing written"
    assert "Traceback" not in err and not (tmp_path / "m.json").exists()


# --------------------------------------------------------------------------- RG-B1


@pytest.mark.parametrize("bad_role", [123, ["a"], {"x": 1}, 1.5, True])
def test_prior_with_a_non_string_role_halts_h07_under_run_yes_and_map_yes(
    bad_role, tmp_path: Path, capsys
):
    """At e92989b ``run --yes`` was exit 5 ``AttributeError`` (123) / ``TypeError`` (["a"])
    and ``map --yes`` exit 0 with the file rewritten."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    yml = write_yaml(tmp_path / "c.yaml", make_criteria())
    m = map_headers(list(cols))
    m.decided_by = "file"
    data = m.to_dict()
    data["roles"][0]["role"] = bad_role
    prior = tmp_path / "m.json"
    prior.write_text(json.dumps(data), encoding="utf-8")
    before = prior.read_bytes()
    for argv in (
        [
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--mapping",
            str(prior),
            "--out",
            str(tmp_path / "p"),
            "--yes",
        ],
        ["map", "--input", str(csv_path), "--out", str(prior), "--yes"],
    ):
        rc = main(argv)
        err = capsys.readouterr().err
        assert rc == EXIT_HALT, argv
        assert err.splitlines()[0] == "HALT H07: mapping.json could not be read"
        assert "internal error" not in err and "Traceback" not in err
    assert prior.read_bytes() == before
    assert not (tmp_path / "p").exists()


def test_prior_with_a_string_value_summaries_halts_h07(tmp_path: Path, capsys):
    """At e92989b ``"value_summaries": "SECRET_STR"`` was accepted and written back by map --yes."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    m = map_headers(list(cols))
    m.decided_by = "file"
    data = m.to_dict()
    data["value_summaries"] = "SECRET_STR"
    prior = tmp_path / "m.json"
    prior.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and err.splitlines()[0] == "HALT H07: mapping.json could not be read"
    assert "SECRET_STR" not in err
    # null and a mapping still read
    data["value_summaries"] = None
    prior.write_text(json.dumps(data), encoding="utf-8")
    assert Mapping.read(prior).value_summaries == {}


# --------------------------------------------------------------------------- FA-N8 / RG-N3


@pytest.mark.parametrize("key", ["columns", "column", "key", "keys", "units", "fields"])
def test_list_key_strings_and_upper_case_and_reach_e01(key):
    """At e92989b ``columns: "subject_id, hadm_id"`` passed ``validate_dict`` silently."""
    with pytest.raises(HaltError) as ei:
        declare.validate_dict(
            make_criteria(
                clustering={"unit": "case_id", key: "subject_id, hadm_id", "declared_by": "t"}
            )
        )
    assert ei.value.code == "E01"
    assert ei.value.message == f"clustering.{key} names 2 columns; " + DEC11
    assert ei.value.detail == {"n_case_key_columns": 2, "key": key}
    declare.validate_dict(
        make_criteria(clustering={"unit": "case_id", key: "subject_id", "declared_by": "t"})
    )  # one token: no halt
    with pytest.raises(HaltError) as ei:
        declare.validate_dict(make_criteria(clustering={"unit": "a AND b", "declared_by": "t"}))
    assert ei.value.message == "clustering.unit names 2 columns; " + DEC11  # was 3 at e92989b
    with pytest.raises(HaltError) as ei:
        declare.validate_dict(make_criteria(clustering={"unit": "a And b", "declared_by": "t"}))
    assert ei.value.detail == {"n_case_key_columns": 2}


# --------------------------------------------------------------------------- FA-N2


def test_dotted_and_month_name_dates_are_typed_date():
    """At e92989b ``15.03.2024`` x 60 was ``categorical`` with ``values: 15.03.2024 (60)``."""
    for values, months in (
        (["15.03.2024", "16.03.2024", "02.11.2025"] * 20, ("2024-03", "2025-11")),
        (["17 Mar 2024", "18 March 2024", "2 NOV 2025"] * 20, ("2024-03", "2025-11")),
    ):
        s = profile_column(values)
        assert s.inferred_type == "date" and (s.min, s.max) == months, values[0]
        assert s.values_shown is False and values[0] not in json.dumps(s.to_dict())
        cols = _cols(visit=values, label=["0", "1"] * 30)
        m = map_headers(list(cols), cols)
        assert (m.entry("visit").role, m.entry("visit").confidence) == ("event_date", "medium")
        with pytest.raises(HaltError) as ei:
            check_h11(list(cols), None, mapping=m)
        assert ei.value.code == "H11" and ei.value.detail == {"date_like_columns": 1}
    # not dates: a two-digit year (the century is a guess) and a word that is not a month
    for values in (["3/17/24"] * 60, ["17 Foo 2024"] * 60, ["17 Mayhem 2024"] * 60):
        s = profile_column(values)
        assert s.inferred_type == "categorical" and s.render().endswith(f"values: {values[0]} (60)")


# --------------------------------------------------------------------------- FA-N1


def test_header_rename_at_the_same_width_changes_the_hash_and_yes_refuses_the_prior(
    tmp_path: Path,
):
    """Pins (lens-2 mutant M24, the hash reduced to the column count): ``label`` renamed
    ``Label2`` keeps three columns and changes the hash; ``--yes`` then halts H07."""
    a = ["row_id", "label", "prob"]
    b = ["row_id", "Label2", "prob"]
    assert header_set_sha256(a)[:12] == "5fbb6eb2369b"
    assert header_set_sha256(b)[:12] == "4916f8a0beca"
    assert header_set_sha256(["prob", "label", "row_id"]) == header_set_sha256(a)  # order-free
    cols = make_cohort()
    prior = map_headers(list(cols), cols)
    prior.decided_by = "interactive"
    prior.write(tmp_path / "m.json")
    renamed = [h if h != "score" else "Score" for h in cols]  # same width, one letter
    assert len(renamed) == len(cols)
    with pytest.raises(HaltError) as ei:
        check_h07(renamed, tmp_path / "m.json", non_interactive=True)
    assert ei.value.code == "H07"
    assert ei.value.message == "header-set hash differs from mapping.json in non-interactive mode"
