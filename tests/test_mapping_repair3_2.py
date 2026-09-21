"""Day 6 A, repair 3.2 (A-P1 the full mapper) - the lens-1 findings on b0f60a6: FA-B1,
FA-B2, FA-B3 / RG-N7 (a README sentence), FA-N1, FA-N4, FA-N5, RG-N5, RG-N6, and the
inputs four of lens 1's surviving mutants (M03, M05, M15, M20) needed.

Every test names the literal input it feeds and the figures it asserts. Each test whose
docstring begins "At b0f60a6" failed at that sha (the first ``E`` line is in the repair
note); those whose docstring begins "Passes at b0f60a6" did not: they run the
counter-example a sentence needed, or feed a mutant's input.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from conftest import make_cohort, make_criteria, write_csv, write_yaml
from proofpack.cli import main
from proofpack.errors import EXIT_HALT, EXIT_OK, EXIT_WARNINGS, HaltError
from proofpack.gates import ingest
from proofpack.io import declare
from proofpack.io.mapping import (
    Mapping,
    RoleMapping,
    apply_mapping,
    map_headers,
    period_for_validate,
    read_as_a_role_by_validate,
)
from proofpack.io.profile import profile_column
from proofpack.io.schema import canonical_columns, header_set_sha256, table_from_columns, validate

pytestmark = pytest.mark.day6

SITE_ONLY = [{"attribute": "site", "prespecified": False, "reference_level": "largest"}]
SEX_REF = {"attribute": "sex", "prespecified": True, "source": "test", "reference_level": "1"}


def _cols(**kw) -> dict:
    return {k: list(v) for k, v in kw.items()}


def _sepsis_shaped() -> dict:
    """``patient`` repeats (case_id low), ``Gender`` 0/1 (sex medium), the rest high; 60 rows."""
    return _cols(
        patient=[f"p{i // 3:04d}" for i in range(60)],
        Gender=["0", "1"] * 30,
        SepsisLabel=["0", "1", "0"] * 20,
        PredictedProbability=[f"{(i % 10) / 10:.1f}" for i in range(60)],
        hospital=["A", "B"] * 30,
    )


def _drive(monkeypatch, answers: list[str]) -> list[str]:
    prompts: list[str] = []
    it = iter(answers)

    def ask(prompt=""):
        prompts.append(prompt)
        return next(it)

    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: True)
    monkeypatch.setattr("builtins.input", ask)
    return prompts


def _run(csv_path: Path, yml: Path, mapping: Path, out: Path, *flags: str) -> int:
    return main(
        [
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--mapping",
            str(mapping),
            "--out",
            str(out),
            *flags,
        ]
    )


def _file_prior(tmp_path: Path, cols: dict, ignored: str, name: str) -> Path:
    m = map_headers(list(cols), cols)
    m.entry(ignored).role = None
    m.decided_by = "file"
    prior = tmp_path / name
    m.write(prior)
    return prior


# --------------------------------------------------------------------------- FA-B1


def test_an_ignored_column_named_for_a_role_does_not_reach_validate_under_that_name(
    tmp_path: Path, capsys, monkeypatch
):
    """At b0f60a6 ``sex`` (1/2/9, ``sex medium``) answered ``e ignore`` reached the pack as
    the ``sex`` attribute (``run --mapping`` exit 2, ``attributes: ["sex", "site"]``,
    ``n_unused_columns: 0``), and ``score`` (0/1) ignored beside ``prob`` edited to
    ``attr_prob_raw`` was read as the score (exit 2, ``n_unused_columns: 0``); three
    file priors ignoring ``sex`` (M/F), ``case_id`` and ``attr_ward`` were consumed as
    those roles (lens-1 FA-B1)."""
    # the sex table: ignored at the prompt, then run with a sex subgroup declared -> H09
    cols = _cols(
        row_id=[str(i) for i in range(60)],
        label=["0", "1"] * 30,
        prob=[f"{(i % 10) / 10:.1f}" for i in range(60)],
        sex=["1", "2", "9"] * 20,
        site=["A", "B", "B"] * 20,
    )
    csv_path = write_csv(tmp_path / "sx.csv", cols)
    out = tmp_path / "sx.json"
    assert [(r.original, r.role, r.confidence) for r in map_headers(list(cols), cols).non_high] == [
        ("sex", "sex", "medium")
    ]
    prompts = _drive(monkeypatch, ["e", "ignore"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    assert len(prompts) == 2
    yml = write_yaml(tmp_path / "c.yaml", make_criteria(subgroups=[SEX_REF, *SITE_ONLY]))
    rc = _run(csv_path, yml, out, tmp_path / "p")
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H09: subgroup declaration references attribute absent from the table"
    )
    assert not (tmp_path / "p").exists()
    # without the sex subgroup the run passes and the ignored column is the one unused
    yml = write_yaml(tmp_path / "c2.yaml", make_criteria(subgroups=SITE_ONLY))
    rc = _run(csv_path, yml, out, tmp_path / "p")
    report = json.loads((tmp_path / "p" / "ingest_report.json").read_text(encoding="utf-8"))
    assert rc == EXIT_WARNINGS  # W10 only: prevalence 0.5 against the declared 0.3
    assert (report["attributes"], report["n_unused_columns"]) == (["site"], 1)
    assert report["roles_present"] == ["row_id", "score", "site", "y_true"]
    # the score table: score ignored, prob -> attr_prob_raw; no score reaches validate -> S01
    cols = _cols(
        row_id=[str(i) for i in range(60)],
        label=["0", "1"] * 30,
        prob=[f"{(i % 10) / 10:.1f}" for i in range(60)],
        score=["1", "0", "0"] * 20,
        site=["A", "B", "B"] * 20,
    )
    csv_path = write_csv(tmp_path / "sc.csv", cols)
    out = tmp_path / "sc.json"
    prompts = _drive(monkeypatch, ["e", "attr_prob_raw", "e", "ignore"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    assert len(prompts) == 4
    rc = _run(csv_path, yml, out, tmp_path / "p2")
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == "HALT S01: one of 'score' or 'y_pred' is required"
    # three file priors through gates.ingest (the in-memory Table, not the report)
    decl = declare.load(yml)
    cohort = make_cohort(n=60, with_case_id=True)
    cohort["attr_ward"] = ["W1", "W2"] * 30
    raw = table_from_columns(cohort)
    for ignored, expect_attrs, expect_case in (
        ("sex", ["attr_ward", "site"], True),
        ("case_id", ["attr_ward", "sex", "site"], False),
        ("attr_ward", ["sex", "site"], True),
    ):
        prior = _file_prior(tmp_path, cohort, ignored, f"{ignored}.json")
        result = ingest(raw, decl, mapping_path=prior)
        assert sorted(result.table.attributes) == expect_attrs, ignored
        assert (result.table.case_id is not None) is expect_case, ignored
        assert result.table.unused_columns == [f"ignored:{ignored}"], ignored
    # the control from the lens: case_id mapped to attr_caseid is an attribute, not the key
    m = map_headers(list(cohort), cohort)
    m.entry("case_id").role = "attr_caseid"
    m.decided_by = "file"
    m.write(tmp_path / "ctl.json")
    result = ingest(raw, decl, mapping_path=tmp_path / "ctl.json")
    assert result.table.case_id is None and "attr_caseid" in result.table.attributes


def test_ignored_role_names_are_the_names_validate_reads():
    """``read_as_a_role_by_validate`` agrees with ``validate``'s header loop on the 19
    canonical names, ``attr_x``, ``attr_X``, ``attr_``, ``rater_1``, ``rater_`` and
    ``notes``: a name is keyed ``ignored:`` at ``apply_mapping`` exactly when ``validate``
    would not park it in ``unused_columns``. The fourth name ``validate`` reads, by
    ``period["column"]`` outside that loop, is the last block (repair 4, lens-2 FA-B2 of
    repair 3.2): an ignored ``visit`` keeps its name at ``apply_mapping`` and ``validate``
    alone builds the period from it while parking it; ``period_for_validate`` halts S03
    on that mapping before ``validate`` runs."""
    names = canonical_columns() + ["attr_x", "attr_X", "attr_", "rater_1", "rater_", "notes"]
    # the bare ``attr_`` matches _IDENT, so validate reads it as an attribute (day-1
    # validate; the mapper's own role check refuses the bare prefix as a role)
    assert [n for n in names if read_as_a_role_by_validate(n)] == canonical_columns() + [
        "attr_x",
        "attr_",
        "rater_1",
        "rater_",
    ]
    for name in names:
        if name in ("y_true", "score"):
            continue
        cols = _cols(y_true=["0", "1"] * 5, score=["0.2", "0.8"] * 5)
        cols[name] = ["a", "b"] * 5
        try:
            parked = name in validate(table_from_columns(cols)).unused_columns
        except HaltError as exc:
            # validate typed the column as that role and halted on "a"/"b" (S02 for
            # indeterminate, age, dataset ...): read, not parked
            assert exc.code in ("S02", "S03"), name
            parked = False
        assert parked is (not read_as_a_role_by_validate(name)), name
        m = Mapping(
            header_set_sha256(list(cols)),
            [
                RoleMapping("y_true", "y_true", "high"),
                RoleMapping("score", "score", "high"),
                RoleMapping(name, None, "high"),
            ],
            "file",
            "",
        )
        keys = list(apply_mapping(cols, m))
        assert keys[2] == (name if parked else f"ignored:{name}"), name
    # the fourth name: period["column"], read by name outside the header loop
    cols = _cols(y_true=["0", "1"] * 5, score=["0.2", "0.8"] * 5)
    cols["visit"] = ["2024-03-15", "2024-09-15"] * 5
    m = Mapping(
        header_set_sha256(list(cols)),
        [
            RoleMapping("y_true", "y_true", "high"),
            RoleMapping("score", "score", "high"),
            RoleMapping("visit", None, "high"),
        ],
        "file",
        "",
    )
    period = {"column": "visit", "granularity": "quarter"}
    mapped = apply_mapping(cols, m)
    assert list(mapped) == ["y_true", "score", "visit"]
    table = validate(table_from_columns(mapped), period=period)
    assert table.unused_columns == ["visit"]
    assert sorted(set(table.period.tolist())) == ["2024-Q1", "2024-Q3"]  # what 4fbbf35 shipped
    with pytest.raises(HaltError) as ei:
        period_for_validate(m, period)
    assert (ei.value.code, ei.value.detail) == ("S03", {"period_column_ignored": True})


def test_a_header_spelled_like_the_ignored_key_is_h07_without_the_header(tmp_path: Path, capsys):
    """A header ``ignored:score`` (ignored, not a role name, so it keeps its name) beside an
    ignored ``score`` (keyed ``ignored:score``) is H07 with a count in the detail, not the
    header; through ``run --mapping`` the header is absent from stderr."""
    cols = _cols(y_true=["0", "1"] * 30, prob=["0.2", "0.8"] * 30, score=["1", "0"] * 30)
    cols["ignored:score"] = ["x", "y"] * 30
    csv_path = write_csv(tmp_path / "t.csv", cols)
    m = map_headers(list(cols), cols)
    for header in ("score", "ignored:score"):
        m.entry(header).role = None
    m.entry("prob").role = "y_pred"  # so no entry holds score and DEC-31 does not halt first
    m.decided_by = "file"
    prior = tmp_path / "m.json"
    m.write(prior)
    with pytest.raises(HaltError) as ei:
        apply_mapping(cols, m)
    assert (ei.value.message, ei.value.detail) == (
        "a column's header equals the ignored: key of another column; rename one",
        {"n_ignored_key_collisions": 1},
    )
    # apply_mapping runs before the subgroup gates, so the default criteria serve
    yml = write_yaml(tmp_path / "c.yaml", make_criteria())
    rc = _run(csv_path, yml, prior, tmp_path / "p")
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and "ignored:score" not in err
    assert err.splitlines()[0].startswith("HALT H07: a column's header equals the ignored: key")


# --------------------------------------------------------------------------- FA-B2


def test_yes_halts_h07_when_a_confirmed_columns_values_changed(tmp_path: Path, capsys, monkeypatch):
    """At b0f60a6 the Sepsis-shaped cohort confirmed ``a a``, re-exported with ``patient``
    holding the ten strings ``0.0`` .. ``0.9``, passed ``map --yes`` and ``run --yes`` with
    exit 0 (``clustering.unit: case_id``, 60 rows, no warning), and ``Gender`` as 0/1/2 did
    too (lens-1 FA-B2)."""
    cols = _sepsis_shaped()
    csv_path = write_csv(tmp_path / "s.csv", cols)
    out = tmp_path / "m.json"
    _drive(monkeypatch, ["a", "a"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    stored = json.loads(out.read_text(encoding="utf-8"))["value_summaries"]
    patient = stored["patient"]
    assert (patient["inferred_type"], patient["n_unique"]) == ("categorical", 20)
    assert [v for v, _ in stored["Gender"]["split"]] == ["0", "1"]
    yml = write_yaml(
        tmp_path / "c.yaml",
        make_criteria(
            clustering={"unit": "case_id", "declared_by": "t"},
            subgroups=[{**SEX_REF, "reference_level": "0"}, *SITE_ONLY],
        ),
    )
    halt = (
        "HALT H07: the values of a column confirmed at the prompt changed since mapping.json "
        "was written (inferred type or the two-valued split); run proofpack map again"
    )
    before = out.read_bytes()
    changed = {
        "patient": [f"{(i % 10) / 10:.1f}" for i in range(60)],  # float; 10 unique
        "Gender": ["0", "1", "2"] * 20,  # three values: no split
    }
    for column, values in changed.items():
        write_csv(csv_path, {**cols, column: values})
        rc = main(["map", "--input", str(csv_path), "--out", str(out), "--yes"])
        err = capsys.readouterr().err
        assert rc == EXIT_HALT, column
        assert err.splitlines()[0] == halt and '"confirmed_columns_changed": 1' in err
        assert "0.0" not in err and "0.9" not in err and out.read_bytes() == before
        rc = _run(csv_path, yml, out, tmp_path / "p", "--yes")
        assert rc == EXIT_HALT and capsys.readouterr().err.splitlines()[0] == halt
        assert not (tmp_path / "p").exists()
    # the same two Gender values in other proportions (40/20) keep the shape: exit 0
    write_csv(csv_path, {**cols, "Gender": ["0", "0", "1"] * 20})
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out), "--yes"]) == EXIT_OK
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out), "--yes"]) == EXIT_OK
    assert capsys.readouterr().err == ""
    # an unconfirmed high column whose values changed (hospital A/B -> A/B/C) is not compared
    write_csv(csv_path, {**cols, "hospital": ["A", "B", "C"] * 20})
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out), "--yes"]) == EXIT_OK
    # a hand-edited summary of a shape the comparison does not read (split not a list)
    data = json.loads(out.read_text(encoding="utf-8"))
    data["value_summaries"]["Gender"]["split"] = "x"
    out.write_text(json.dumps(data), encoding="utf-8")
    write_csv(csv_path, cols)
    rc = main(["map", "--input", str(csv_path), "--out", str(out), "--yes"])
    assert rc == EXIT_HALT and capsys.readouterr().err.splitlines()[0] == halt


# --------------------------------------------------------------------------- FA-B3 / RG-N7


def test_the_mapper_sets_confirmed_only_on_an_accept_or_an_edit_and_yes_writes_back_what_it_read(
    tmp_path: Path, capsys, monkeypatch
):
    """Passes at b0f60a6: the counter-example the README sentence "confirmed is true only on
    an entry answered a" needed (lens-1 FA-B3 / RG-N7). ``confirmed: true`` planted by hand
    on ``SepsisLabel`` (high, never prompted) survives ``map --yes``; the prompt itself sets
    it on ``patient`` and ``Gender`` (answered ``a``, or edited: DEC-42, repair 4 - until
    4fbbf35 this test asserted ``["patient"]`` after ``a e attr_gender_code``) and on
    nothing else."""
    cols = _sepsis_shaped()
    csv_path = write_csv(tmp_path / "s.csv", cols)
    out = tmp_path / "m.json"
    _drive(monkeypatch, ["a", "e", "attr_gender_code"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [r["original"] for r in data["roles"] if r["confirmed"]] == ["patient", "Gender"]
    _drive(monkeypatch, ["a", "a"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [r["original"] for r in data["roles"] if r["confirmed"]] == ["patient", "Gender"]
    for r in data["roles"]:
        if r["original"] == "SepsisLabel":
            r["confirmed"] = True
    out.write_text(json.dumps(data), encoding="utf-8")
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out), "--yes"]) == EXIT_OK
    after = json.loads(out.read_text(encoding="utf-8"))
    assert [r["original"] for r in after["roles"] if r["confirmed"]] == [
        "patient",
        "Gender",
        "SepsisLabel",
    ]
    assert after["decided_by"] == "file" and capsys.readouterr().err == ""


# --------------------------------------------------------------------------- FA-N1


def test_read_only_out_is_h07_without_the_path(tmp_path: Path, capsys):
    """At b0f60a6 ``map --yes`` on a read-only ``--out`` was exit 5 ``internal error:
    PermissionError: [Errno 13] Permission denied: '<--out as typed>'`` (lens-1 FA-N1)."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    m = map_headers(list(cols), cols)
    m.decided_by = "interactive"
    out = tmp_path / "SECRETDIR_ro" / "SECRETFILE_m.json"
    out.parent.mkdir()
    m.write(out)
    os.chmod(out, stat.S_IREAD)
    try:
        rc = main(["map", "--input", str(csv_path), "--out", str(out), "--yes"])
        err = capsys.readouterr().err
    finally:
        os.chmod(out, stat.S_IREAD | stat.S_IWRITE)
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: --out could not be written (permission or a device in the way); pass a "
        "writable file path"
    )
    assert "SECRET" not in err and "internal error" not in err and "Traceback" not in err


# --------------------------------------------------------------------------- FA-N4


def test_us_shaped_slash_dates_key_to_a_real_month():
    """At b0f60a6 ``["03/15/2024"] * 60`` printed ``min 2024-15 max 2024-15`` (lens-1
    FA-N4). Day-first stays the reading when it gives a month: ``["03/04/2024"] * 60`` is
    ``2024-04``; ``["13/15/2024"] * 60`` is a month under neither order and stays ``2024-15``."""
    s = profile_column(["03/15/2024"] * 60)
    assert (s.inferred_type, s.min, s.max) == ("date", "2024-03", "2024-03")
    assert profile_column(["03/04/2024"] * 60).min == "2024-04"
    assert profile_column(["15.03.2024"] * 30 + ["03/15/2024"] * 30).min == "2024-03"
    assert profile_column(["13/15/2024"] * 60).min == "2024-15"


# --------------------------------------------------------------------------- FA-N5


def test_a_prior_with_a_utf8_bom_is_read(tmp_path: Path, capsys):
    """At b0f60a6 a confirmed prior with a leading ``EF BB BF`` (PowerShell 5.1 ``Out-File``)
    was H07 ``the prior mapping.json could not be decoded`` under ``map --yes`` (lens-1
    FA-N5)."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    m = map_headers(list(cols), cols)
    m.decided_by = "interactive"
    prior = tmp_path / "bom.json"
    prior.write_bytes(b"\xef\xbb\xbf" + m.to_bytes())
    assert Mapping.read(prior).decided_by == "interactive"
    rc = main(["--quiet", "map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    assert rc == EXIT_OK and capsys.readouterr().err == ""
    assert prior.read_bytes()[:1] == b"{"  # written back without the BOM


# --------------------------------------------------------------------------- RG-N5


def test_a_proposed_prior_is_not_relabelled_file_by_run_mapping(tmp_path: Path, capsys):
    """At b0f60a6 ``run --mapping p1/mapping.json`` (the ``proposed`` file ``run`` wrote,
    no ``--yes``) wrote ``p2/mapping.json`` with ``decided_by: file`` and ``map --yes`` on
    that file was exit 0 (lens-1 RG-N5; ``cmd_run`` untouched, DEC-26 is E7's)."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    yml = write_yaml(tmp_path / "c.yaml", make_criteria())
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(tmp_path / "p1")]
    )
    p1 = tmp_path / "p1" / "mapping.json"
    assert rc == EXIT_OK and json.loads(p1.read_text(encoding="utf-8"))["decided_by"] == "proposed"
    rc = _run(csv_path, yml, p1, tmp_path / "p2")
    p2 = tmp_path / "p2" / "mapping.json"
    assert rc == EXIT_OK and json.loads(p2.read_text(encoding="utf-8"))["decided_by"] == "proposed"
    for flags in (["map", "--input", str(csv_path), "--out", str(p2), "--yes"],):
        rc = main(flags)
        err = capsys.readouterr().err
        assert rc == EXIT_HALT and "this one was not confirmed" in err.splitlines()[0]
    rc = _run(csv_path, yml, p2, tmp_path / "p3", "--yes")
    assert rc == EXIT_HALT and "this one was not confirmed" in capsys.readouterr().err
    # an interactive prior is still relabelled file on the way into the pack
    data = json.loads(p1.read_text(encoding="utf-8"))
    data["decided_by"] = "interactive"
    p1.write_text(json.dumps(data), encoding="utf-8")
    assert _run(csv_path, yml, p1, tmp_path / "p4") == EXIT_OK
    p4 = tmp_path / "p4" / "mapping.json"
    assert json.loads(p4.read_text(encoding="utf-8"))["decided_by"] == "file"


# --------------------------------------------------------------------------- RG-N6


def test_out_naming_a_drive_root_says_so(tmp_path: Path, capsys):
    """At b0f60a6 ``--out C:/`` printed ``--out names an existing directory (); pass a file
    path such as /mapping.json`` (lens-1 RG-N6). The root of ``tmp_path``'s drive is fed."""
    csv_path = write_csv(tmp_path / "t.csv", make_cohort())
    root = tmp_path.anchor
    assert Path(root).is_dir() and Path(root).resolve().name == ""
    rc = main(["map", "--input", str(csv_path), "--out", root, "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: --out names an existing directory (a drive root); pass a file path such "
        "as mapping.json inside a directory"
    )


# --------------------------------------------------------------------------- lens-1 mutants


def test_a_prior_missing_one_entry_is_h07_with_the_count_one(tmp_path: Path, capsys):
    """Passes at b0f60a6: lens-1 M05 (``if missing > 1``) survived because only ``roles:
    []`` was fed; the ``site`` entry alone removed -> ``columns_without_entry: 1``."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    m = map_headers(list(cols), cols)
    m.decided_by = "interactive"
    data = m.to_dict()
    data["roles"] = [r for r in data["roles"] if r["original"] != "site"]
    prior = tmp_path / "m.json"
    prior.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and '"columns_without_entry": 1' in err
    assert err.splitlines()[0] == (
        "HALT H07: mapping.json has no entry for a column of this table; run proofpack map again"
    )


def test_date_min_month_held_by_nine_rows_is_suppressed():
    """Passes at b0f60a6: lens-1 M15 (the min floor at 9) survived because the nine-row month
    fed was the max only; ``["1999-01-05"] * 9 + ["2024-03-15"] * 50`` -> ``min <suppressed>``,
    and at ten rows ``1999-01``."""
    assert profile_column(["1999-01-05"] * 9 + ["2024-03-15"] * 50).min == "<suppressed>"
    assert profile_column(["1999-01-05"] * 10 + ["2024-03-15"] * 50).min == "1999-01"


def test_a_file_prior_ignoring_a_high_column_halts_yes_on_the_role_difference(
    tmp_path: Path, capsys
):
    """Passes at b0f60a6: lens-1 M03 (the role difference skipped when the prior says
    ``ignore``) survived unfed; a ``file`` prior with ``site -> ignore`` on ``make_cohort()``
    under ``map --yes`` -> ``prior_role ignore, fresh_role site``."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    prior = _file_prior(tmp_path, cols, "site", "m.json")
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: mapping.json maps a column to ignore but the mapping computed from this "
        "table gives it site; run proofpack map again"
    )
    assert '"prior_role": "ignore", "fresh_role": "site"' in err


def test_a_fresh_non_high_role_needs_confirmed_on_its_own_entry(
    tmp_path: Path, capsys, monkeypatch
):
    """Passes at b0f60a6: lens-1 M20 (``confirmed`` on any prior entry) survived unfed;
    ``Gender`` hand-set ``confidence: high, confirmed: false`` beside ``patient`` confirmed
    -> H07 ``run interactively`` under ``map --yes``."""
    cols = _sepsis_shaped()
    csv_path = write_csv(tmp_path / "s.csv", cols)
    out = tmp_path / "m.json"
    _drive(monkeypatch, ["a", "a"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    data = json.loads(out.read_text(encoding="utf-8"))
    for r in data["roles"]:
        if r["original"] == "Gender":
            r["confirmed"], r["confidence"] = False, "high"
    out.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["map", "--input", str(csv_path), "--out", str(out), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: non-interactive mode requires every role at high confidence in the mapping "
        "computed from this table, or confirmed at the prompt for the same column and role; "
        "run interactively"
    )
    assert '"low_or_medium": 1' in err
