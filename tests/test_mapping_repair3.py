"""Day 6 A, repair 3 (A-P1 the full mapper) - the five lens-3 blockers, DEC-28, DEC-29,
DEC-31, DEC-39 and carried 6, 11, 12; one test per fix.

Every test names the literal input it feeds and the figures it asserts. Each test whose
docstring begins "At 1354758" failed at that sha (the first ``E`` line is in the repair-3
note); the five whose docstring begins "Observes" pass there and are here so that one of
the lens-3 mutants L08, L11, L13, L14 or L20 (``scripts/mutation_sweep.py --marker day6``)
fails a test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import make_cohort, make_criteria, write_csv, write_yaml
from proofpack.cli import _confirm_interactive, main
from proofpack.errors import EXIT_HALT, EXIT_OK, EXIT_WARNINGS, HaltError
from proofpack.io.mapping import (
    Mapping,
    RoleMapping,
    apply_mapping,
    check_h07,
    fold_header,
    ignore_collision,
    map_headers,
    normalise_header,
)
from proofpack.io.profile import profile_column
from proofpack.io.schema import canonical_columns, header_set_sha256, load_table

pytestmark = pytest.mark.day6

FIXTURES = Path(__file__).parent / "fixtures" / "mapping"
DEC31_PRIOR = (
    "HALT H07: mapping.json ignores the column whose header is the role name score and maps "
    "another column to score: an ignored column keeps its name and the two would collide; "
    "run proofpack map again and give one of them another role"
)


def _cols(**kw) -> dict:
    return {k: list(v) for k, v in kw.items()}


def _lens_table() -> dict:
    """The lens-3 FA-B2 table: ``score`` holds 0/1, ``prob`` floats in [0, 1]; 60 rows;
    ``site`` (A/B) added so ``run`` has the one subgroup attribute its criteria declare."""
    return _cols(
        row_id=[str(i) for i in range(60)],
        label=["0", "1"] * 30,
        score=["1", "0", "0"] * 20,
        prob=[f"{(i % 10) / 10:.1f}" for i in range(60)],
        site=["A", "B", "B"] * 20,
    )


SITE_ONLY = [{"attribute": "site", "prespecified": False, "reference_level": "largest"}]


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
    """Patch the terminal check and ``input``; return the list the prompts are appended to."""
    prompts: list[str] = []
    it = iter(answers)

    def ask(prompt=""):
        prompts.append(prompt)
        return next(it)

    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: True)
    monkeypatch.setattr("builtins.input", ask)
    return prompts


# --------------------------------------------------------------------------- blocker 1


def test_empty_answer_reprompts_at_both_prompts():
    """At 1354758 ``""`` was in the accept tuple at both prompts: no refusal line and
    ``decided_by`` interactive on the empty answer alone (lens-3 FA-B1)."""
    # the all-high prompt: "" then "a"
    cols = make_cohort()
    m = map_headers(list(cols), cols)
    assert m.non_high == []
    said: list[str] = []
    answers = iter(["", "a"])
    seen: list[str] = []

    def ask(p):
        seen.append(m.decided_by)
        return next(answers)

    _confirm_interactive(m, ask=ask, say=said.append)
    assert said == ["  answer a or q"]
    assert seen == ["proposed", "proposed"] and m.decided_by == "interactive"
    # the per-role prompt (Gender 0/1 -> sex medium): "" then "a"
    cols = _sepsis_shaped()
    m = map_headers(list(cols), cols)
    assert [r.original for r in m.non_high] == ["patient", "Gender"]
    said = []
    answers = iter(["", "a", "", "a"])
    seen = []

    def ask2(p):
        seen.append((m.decided_by, m.entry("patient").confirmed))
        return next(answers)

    _confirm_interactive(m, ask=ask2, say=said.append)
    assert said == ["  answer a, e or q"] * 2
    assert seen[:2] == [("proposed", False), ("proposed", False)]
    assert seen[2] == ("proposed", True) and m.decided_by == "interactive"
    # "accept", "  a  " and "A" read as "a" (stripped and lower-cased by _ask)
    for word in ("accept", "  a  ", "A"):
        m = map_headers(list(cols), cols)
        said = []
        _confirm_interactive(m, ask=lambda p, w=word: w, say=said.append)
        assert said == [] and m.decided_by == "interactive", word


# --------------------------------------------------------------------------- blocker 2 / DEC-31


def test_ignore_on_a_column_named_for_a_held_role_is_refused_at_the_prompt(
    tmp_path: Path, capsys, monkeypatch
):
    """At 1354758 ``e ignore a`` on this table wrote ``score -> ignore, prob -> score`` and
    ``run --mapping`` halted H07 ``two columns map to the same canonical role`` (lens-3
    FA-B2)."""
    cols = _lens_table()
    csv_path = write_csv(tmp_path / "sp.csv", cols)
    yml = write_yaml(tmp_path / "c.yaml", make_criteria(subgroups=SITE_ONLY))
    out = tmp_path / "sp.json"
    m = map_headers(list(cols), cols)
    assert [(r.original, r.role, r.confidence) for r in m.non_high] == [
        ("score", "score", "low"),
        ("prob", "score", "low"),
    ]
    # e ignore -> refused (prob currently holds score); e attr_score_flag -> taken; a for prob
    prompts = _drive(monkeypatch, ["e", "ignore", "e", "attr_score_flag", "a"])
    rc = main(["map", "--input", str(csv_path), "--out", str(out)])
    captured = capsys.readouterr()
    assert rc == EXIT_OK and len(prompts) == 5
    assert prompts[0] == prompts[2] and prompts[0].startswith("'score' -> score (low)")
    assert prompts[4].startswith("'prob' -> score (low)")
    lines = captured.out.splitlines()
    assert (
        "  refused: the ignored column 'score' keeps its name, which is the role score that "
        "'prob' would hold; give one of them another role"
    ) in lines
    written = json.loads(out.read_text(encoding="utf-8"))
    roles = {r["original"]: r for r in written["roles"]}
    assert (roles["score"]["role"], roles["score"]["confirmed"]) == ("attr_score_flag", False)
    assert (roles["prob"]["role"], roles["prob"]["confirmed"]) == ("score", True)
    rc = main(
        [
            "--quiet",
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--mapping",
            str(out),
            "--out",
            str(tmp_path / "p"),
        ]
    )
    # exit 2 = warnings only: W10, the table's prevalence 0.5 against the declared 0.3
    assert rc == EXIT_WARNINGS and (tmp_path / "p" / "ingest_report.json").exists()
    # a prior holding the colliding pair (hand-written the way 1354758's prompt wrote it)
    roles["score"]["role"] = "ignore"
    written["roles"] = list(roles.values())
    written["decided_by"] = "interactive"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(written), encoding="utf-8")
    calls: list[str] = []
    real_apply = apply_mapping

    def spy(columns, mapping):
        calls.append("apply")
        return real_apply(columns, mapping)

    monkeypatch.setattr("proofpack.io.mapping.apply_mapping", spy)
    for flag in ([], ["--yes"]):
        rc = main(
            [
                "run",
                "--input",
                str(csv_path),
                "--criteria",
                str(yml),
                "--mapping",
                str(bad),
                "--out",
                str(tmp_path / "p2"),
                *flag,
            ]
        )
        err = capsys.readouterr().err
        assert rc == EXIT_HALT, flag
        assert err.splitlines()[0] == DEC31_PRIOR
        assert "two columns map to the same canonical role" not in err
        assert "prob" not in err and "Traceback" not in err
    assert calls == [] and not (tmp_path / "p2").exists()
    # the same pair through map --yes
    rc = main(["map", "--input", str(csv_path), "--out", str(bad), "--yes"])
    assert rc == EXIT_HALT and capsys.readouterr().err.splitlines()[0] == DEC31_PRIOR


def test_accept_or_edit_to_a_role_an_ignored_column_is_named_for_is_refused():
    """At 1354758 ``score`` (0/1) ignored first and ``outcome`` then edited to ``score`` was
    written as the colliding pair (the other order of lens-3 FA-B2)."""
    cols = _cols(
        row_id=[str(i) for i in range(60)],
        score=["1", "0", "0"] * 20,
        outcome=[f"{(i % 10) / 10:.1f}" for i in range(60)],
    )
    m = map_headers(list(cols), cols)
    assert [(r.original, r.role, r.confidence) for r in m.non_high] == [
        ("score", "score", "low"),
        ("outcome", "y_true", "low"),
    ]
    said: list[str] = []
    answers = iter(["e", "ignore", "e", "score", "e", "ignore"])
    _confirm_interactive(m, ask=lambda p: next(answers), say=said.append)
    assert said == [
        "  refused: the ignored column 'score' keeps its name, which is the role score that "
        "'outcome' would hold; give one of them another role"
    ]
    assert (m.entry("score").role, m.entry("outcome").role) == (None, None)
    assert ignore_collision(m.roles) is None
    # the helper on a hand-built pair, and a folded header ('Score', ' SCORE ')
    for header in ("Score", " SCORE "):
        pair = ignore_collision(
            [RoleMapping(header, None, "high"), RoleMapping("prob", "score", "high")]
        )
        assert pair is not None and (pair[0].original, pair[1], pair[2].original) == (
            header,
            "score",
            "prob",
        )
    assert (
        ignore_collision(
            [RoleMapping("score", None, "high"), RoleMapping("prob", "y_pred", "high")]
        )
        is None
    )


def test_ignored_columns_otherwise_keep_their_name_at_apply_mapping():
    """DEC-31's second half on a non-colliding pair: ``notes`` ignored beside ``prob -> score``."""
    cols = _cols(row_id=["1", "2"], prob=["0.1", "0.9"], notes=["a", "b"])
    m = Mapping(
        header_set_sha256(list(cols)),
        [
            RoleMapping("row_id", "row_id", "high"),
            RoleMapping("prob", "score", "high"),
            RoleMapping("notes", None, "high"),
        ],
        "file",
        "",
    )
    assert list(apply_mapping(cols, m)) == ["row_id", "score", "notes"]
    # the colliding pair fed to apply_mapping directly (check_h07 halts it first on a prior)
    cols = _cols(row_id=["1", "2"], prob=["0.1", "0.9"], score=["1", "0"])
    m = Mapping(
        header_set_sha256(list(cols)),
        [
            RoleMapping("row_id", "row_id", "high"),
            RoleMapping("prob", "score", "high"),
            RoleMapping("score", None, "high"),
        ],
        "file",
        "",
    )
    with pytest.raises(HaltError) as ei:
        apply_mapping(cols, m)
    assert (ei.value.code, ei.value.message, ei.value.detail) == (
        "H07",
        "two columns map to the same canonical role",
        {"role": "score"},
    )


# --------------------------------------------------------------------------- blocker 3


def test_sixty_distinct_two_digit_year_dates_are_not_typed_date():
    """At 1354758 ``profile.py`` said such a column "stays categorical"; measured ``string``
    (lens-3 FA-B3). Neither shape is ``date`` and neither raises H11."""
    from proofpack.io.mapping import check_h11

    distinct = [f"{i % 28 + 1}/{i % 12 + 1}/24" for i in range(60)]
    assert len(set(distinct)) == 60
    s = profile_column(distinct)
    assert s.inferred_type == "string" and s.values_shown is False
    assert profile_column(["3/17/24"] * 60).inferred_type == "categorical"
    for col in (distinct, ["3/17/24"] * 60):
        cols = _cols(row_id=[str(i) for i in range(60)], visit=col)
        check_h11(list(cols), None, mapping=map_headers(list(cols), cols))


# --------------------------------------------------------------------------- blocker 4


def test_prior_of_nested_brackets_is_h07_not_exit_5(tmp_path: Path, capsys):
    """At 1354758 ``map --yes`` on this file was exit 5 ``internal error: RecursionError``
    (lens-3 FA-B4)."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    prior = tmp_path / "m7.json"
    prior.write_text("[" * 100_000 + "]" * 100_000, encoding="utf-8")
    before = prior.read_bytes()
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == "HALT H07: the prior mapping.json could not be decoded"
    assert "Traceback" not in err and "internal error" not in err
    assert prior.read_bytes() == before
    # the other two decode failures take the same line; a missing file is not a decode
    for content in (b"\xff\xfe", b"{not json"):
        prior.write_bytes(content)
        with pytest.raises(HaltError) as ei:
            Mapping.read(prior)
        assert ei.value.message == "the prior mapping.json could not be decoded"
    assert check_h07(list(cols), tmp_path / "absent.json", non_interactive=False).decided_by == (
        "proposed"
    )


# --------------------------------------------------------------------------- blocker 5


@pytest.mark.parametrize("roles", [{}, "", {"original": "x"}, "SECRET_HDR"])
def test_prior_with_a_non_list_roles_is_h07_and_the_file_is_unchanged(
    roles, tmp_path: Path, capsys
):
    """At 1354758 ``{}`` and ``""`` iterated as empty: ``map --yes`` exit 0 and the file
    rewritten with ``roles: []`` (lens-3 RG-B1)."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    prior = tmp_path / "m.json"
    prior.write_text(
        json.dumps(
            {
                "header_set_sha256": header_set_sha256(list(cols)),
                "roles": roles,
                "decided_by": "file",
            }
        ),
        encoding="utf-8",
    )
    before = prior.read_bytes()
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == "HALT H07: mapping.json could not be read"
    assert "SECRET_HDR" not in err and "Traceback" not in err
    assert prior.read_bytes() == before


def test_confirmed_must_be_a_bool_when_present(tmp_path: Path):
    """``confirmed: "true"`` (a string), ``1`` and ``null`` are H07; absent reads False."""
    cols = make_cohort()
    m = map_headers(list(cols))
    m.decided_by = "file"
    data = m.to_dict()
    prior = tmp_path / "m.json"
    for bad in ("true", 1, None, [True]):
        data["roles"][0]["confirmed"] = bad
        prior.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(HaltError) as ei:
            Mapping.read(prior)
        assert ei.value.code == "H07" and ei.value.message == "mapping.json could not be read"
    del data["roles"][0]["confirmed"]
    prior.write_text(json.dumps(data), encoding="utf-8")
    assert Mapping.read(prior).roles[0].confirmed is False


# --------------------------------------------------------------------------- DEC-28


def test_interactive_accept_records_confirmed_and_yes_takes_it(tmp_path: Path, capsys, monkeypatch):
    """At 1354758 ``map --yes`` on the Sepsis-shaped cohort was H07 ``every mapped role at
    high confidence`` whatever the human had answered (carried 25)."""
    cols = _sepsis_shaped()
    csv_path = write_csv(tmp_path / "s.csv", cols)
    out = tmp_path / "m.json"
    prompts = _drive(monkeypatch, ["a", "a"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    assert len(prompts) == 2
    data = json.loads(out.read_text(encoding="utf-8"))
    flags = {r["original"]: (r["role"], r["confidence"], r["confirmed"]) for r in data["roles"]}
    assert flags["patient"] == ("case_id", "low", True)
    assert flags["Gender"] == ("sex", "medium", True)
    assert [k for k, v in flags.items() if v[2]] == ["patient", "Gender"]
    assert data["decided_by"] == "interactive"
    # --yes accepts the file: every role high or confirmed, and the same roles fresh
    rc = main(["--quiet", "map", "--input", str(csv_path), "--out", str(out), "--yes"])
    assert rc == EXIT_OK and capsys.readouterr().err == ""
    after = json.loads(out.read_text(encoding="utf-8"))
    assert after["decided_by"] == "file"
    assert {r["original"]: r["confirmed"] for r in after["roles"]} == {
        k: v[2] for k, v in flags.items()
    }
    # and run --yes with it
    criteria = make_criteria(
        clustering={"unit": "case_id", "declared_by": "t"},
        subgroups=[
            # the 0/1 coding the human confirmed, and the site column; no age column
            {"attribute": "sex", "prespecified": True, "source": "test", "reference_level": "0"},
            *SITE_ONLY,
        ],
    )
    yml = write_yaml(tmp_path / "c.yaml", criteria)
    rc = main(
        [
            "--quiet",
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--mapping",
            str(out),
            "--out",
            str(tmp_path / "p"),
            "--yes",
        ]
    )
    assert rc == EXIT_OK, capsys.readouterr().err
    assert (tmp_path / "p" / "ingest_report.json").exists()
    # a hand-edited prior: confirmed: true but decided_by proposed -> H07
    data["decided_by"] = "proposed"
    out.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["map", "--input", str(csv_path), "--out", str(out), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and "this one was not confirmed" in err.splitlines()[0]
    # confirmed: true on a role whose fresh confidence is high is harmless
    data["decided_by"] = "interactive"
    for r in data["roles"]:
        if r["original"] == "SepsisLabel":
            r["confirmed"] = True
    out.write_text(json.dumps(data), encoding="utf-8")
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out), "--yes"]) == EXIT_OK
    # confirmed: true removed from Gender -> H07 on the fresh medium
    for r in data["roles"]:
        if r["original"] == "Gender":
            r["confirmed"] = False
    out.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["map", "--input", str(csv_path), "--out", str(out), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: non-interactive mode requires every mapped role at high confidence in "
        "mapping.json or confirmed at the prompt (confirmed: true)"
    )
    assert '"low_or_medium": 1' in err


def test_edit_does_not_record_confirmed_and_an_edited_prior_does_not_pass_yes(
    tmp_path: Path, capsys, monkeypatch
):
    """DEC-28 as built: ``Gender`` edited to ``attr_gender_code`` -> ``confirmed`` False, and
    ``map --yes`` then halts on the unconfirmed medium in the prior (the first rule; the
    role difference would halt it next - open question 1 of the note)."""
    cols = _sepsis_shaped()
    csv_path = write_csv(tmp_path / "s.csv", cols)
    out = tmp_path / "m.json"
    _drive(monkeypatch, ["a", "e", "attr_gender_code"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    data = json.loads(out.read_text(encoding="utf-8"))
    gender = next(r for r in data["roles"] if r["original"] == "Gender")
    assert (gender["role"], gender["confirmed"], gender["notes"]) == (
        "attr_gender_code",
        False,
        ["no dictionary declared for 0/1", "edited interactively"],
    )
    rc = main(["map", "--input", str(csv_path), "--out", str(out), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: non-interactive mode requires every mapped role at high confidence in "
        "mapping.json or confirmed at the prompt (confirmed: true)"
    )
    # with the prior's confidence hand-edited to high the role difference is the halt
    gender["confidence"] = "high"
    out.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["map", "--input", str(csv_path), "--out", str(out), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: mapping.json maps a column to attr_gender_code but the mapping computed "
        "from this table gives it sex; run proofpack map again"
    )


# --------------------------------------------------------------------------- DEC-29


def _confirmed_prior(tmp_path: Path, cols: dict) -> tuple[Path, Path, dict]:
    csv_path = write_csv(tmp_path / "t.csv", cols)
    m = map_headers(list(cols), cols)
    assert m.all_high
    m.decided_by = "interactive"
    prior = tmp_path / "m.json"
    m.write(prior)
    return csv_path, prior, json.loads(prior.read_text(encoding="utf-8"))


def test_yes_halts_h07_on_an_original_outside_the_header_set(tmp_path: Path, capsys):
    """At 1354758 ``original: NOT_A_HEADER`` on the ``site`` entry passed ``map --yes`` with
    exit 0 (carried 13); ``roles: []`` did too."""
    csv_path, prior, data = _confirmed_prior(tmp_path, make_cohort())
    for r in data["roles"]:
        if r["original"] == "site":
            r["original"] = "SECRETH_NOT_A_HEADER"
    prior.write_text(json.dumps(data), encoding="utf-8")
    before = prior.read_bytes()
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: mapping.json names a column that is not in this table's header set; run "
        "proofpack map again"
    )
    assert '"originals_not_in_table": 1' in err and "SECRETH" not in err
    assert prior.read_bytes() == before
    data["roles"] = []
    prior.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: mapping.json has no entry for a column of this table; run proofpack map again"
    )
    assert '"columns_without_entry": 6' in err


@pytest.mark.parametrize("bad_role", ["SECRET_ROLE_NAME", "attr_", "attr_x y", "Score", "rater_"])
def test_yes_halts_h07_on_a_role_outside_the_canonical_set(bad_role, tmp_path: Path, capsys):
    """At 1354758 ``role: SECRET_ROLE_NAME`` at high passed ``map --yes`` with exit 0
    (carried 13)."""
    csv_path, prior, data = _confirmed_prior(tmp_path, make_cohort())
    for r in data["roles"]:
        if r["original"] == "site":
            r["role"] = bad_role
    prior.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: mapping.json holds a role that is not a canonical role or an attr_ / "
        "rater_ name; run proofpack map again"
    )
    assert '"roles_not_canonical": 1' in err and "SECRET" not in err
    assert bad_role not in err or bad_role in ("attr_", "rater_")  # the message names the prefixes
    # an attr_ name that matches the identifier rule reads, and then halts on the difference
    for r in data["roles"]:
        if r["original"] == "site":
            r["role"] = "attr_site_code"
    prior.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and "maps a column to attr_site_code" in err.splitlines()[0]


def test_yes_halts_h07_when_the_prior_role_differs_from_the_fresh_one(tmp_path: Path, capsys):
    """At 1354758 a prior ``age high`` (numeric) on a header set whose ``age`` now holds
    ``[70-80)`` bands passed ``map --yes`` and was rewritten with ``role: age`` (lens-3
    FA-N2, carried 7)."""
    cols = make_cohort()
    csv_path, prior, data = _confirmed_prior(tmp_path, cols)
    assert next(r["role"] for r in data["roles"] if r["original"] == "age") == "age"
    bands = ["[60-70)", "[70-80)", "[80-90)"]
    cols["age"] = [bands[i % 3] for i in range(len(cols["age"]))]
    write_csv(csv_path, cols)
    fresh = map_headers(list(cols), cols)
    assert (fresh.entry("age").role, fresh.entry("age").confidence) == ("age_band", "high")
    before = prior.read_bytes()
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: mapping.json maps a column to age but the mapping computed from this "
        "table gives it age_band; run proofpack map again"
    )
    assert '"prior_role": "age", "fresh_role": "age_band"' in err
    assert prior.read_bytes() == before


# --------------------------------------------------------------------------- DEC-39


def test_date_min_max_below_the_floor_print_as_suppressed():
    """At 1354758 this column printed ``min 1999-01`` - the month held by one row (lens-2
    RG-NB-4, carried 23)."""
    s = profile_column(["2024-03-15"] * 49 + ["1999-01-01"])
    assert s.inferred_type == "date" and (s.min, s.max) == ("<suppressed>", "2024-03")
    assert "1999" not in s.render() and "1999" not in json.dumps(s.to_dict())
    # the floor counts rows in the month, not rows on the day: 5 + 5 rows in 2024-03 print
    s = profile_column(["2024-03-15"] * 5 + ["2024-03-16"] * 5 + ["2025-11-02"] * 9)
    assert (s.min, s.max) == ("2024-03", "<suppressed>")
    s = profile_column(["2024-03-15"] * 10 + ["2025-11-02"] * 10)
    assert (s.min, s.max) == ("2024-03", "2025-11")


# --------------------------------------------------------------------------- carried 6


def test_out_naming_an_existing_directory_halts_h07_before_any_prompt(
    tmp_path: Path, capsys, monkeypatch
):
    """At 1354758 ``--out <dir>`` was answered at the prompt and then exit 5
    ``PermissionError: [Errno 13]`` with the full local path (lens-3 FA-N1)."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    out_dir = tmp_path / "SECRETDIR_pack"
    out_dir.mkdir()
    prompts = _drive(monkeypatch, ["a"])
    rc = main(["map", "--input", str(csv_path), "--out", str(out_dir)])
    captured = capsys.readouterr()
    assert rc == EXIT_HALT and prompts == [] and captured.out == ""
    assert captured.err.splitlines()[0] == (
        "HALT H07: --out names an existing directory (SECRETDIR_pack); pass a file path such "
        "as SECRETDIR_pack/mapping.json"
    )
    assert str(tmp_path) not in captured.err and "internal error" not in captured.err
    assert sorted(out_dir.iterdir()) == []
    # a relative spelling names the same last component; --yes takes the same halt first
    monkeypatch.chdir(tmp_path)
    rc = main(["map", "--input", "t.csv", "--out", "SECRETDIR_pack/", "--yes"])
    assert rc == EXIT_HALT and "(SECRETDIR_pack)" in capsys.readouterr().err.splitlines()[0]


# --------------------------------------------------------------------------- carried 12


def test_ctrl_c_during_write_is_h07_not_a_traceback(tmp_path: Path, capsys, monkeypatch):
    """At 1354758 ``KeyboardInterrupt`` raised from ``Mapping.write`` after the last prompt
    propagated out of ``main()`` (lens-3 FA-N7)."""
    csv_path = write_csv(tmp_path / "t.csv", make_cohort())
    prompts = _drive(monkeypatch, ["a"])

    def ctrl_c(self, path):
        raise KeyboardInterrupt

    monkeypatch.setattr("proofpack.io.mapping.Mapping.write", ctrl_c)
    rc = main(["map", "--input", str(csv_path), "--out", str(tmp_path / "m.json")])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and len(prompts) == 1
    assert err.splitlines()[0] == (
        "HALT H07: mapping interrupted while writing --out; run proofpack map again"
    )
    assert '"out_may_be_partial": true' in err and "Traceback" not in err


# --------------------------------------------------------------------------- carried 11 (mutants)


def test_one_non_date_cell_among_fifty_nine_iso_dates_is_not_typed_date():
    """Observes lens-3 L08 (``any`` for ``all`` in ``_infer_type``'s date arm)."""
    s = profile_column(["2024-03-15"] * 59 + ["not-a-date"])
    assert s.inferred_type == "categorical" and s.min is None
    assert s.top == [["2024-03-15", 59], ["<suppressed>", 1]]
    assert profile_column(["2024-03-15"] * 60).inferred_type == "date"


def test_affix_case_id_pair_reaches_e01_in_map_headers():
    """Observes lens-3 L11 (E01 counting canonical and synonym claims only, not affix):
    ``patient_id`` (synonym) + ``pt_subject_id`` (affix) -> E01 with the count 2."""
    with pytest.raises(HaltError) as ei:
        map_headers(["patient_id", "pt_subject_id", "label"])
    assert ei.value.code == "E01" and ei.value.detail == {"n_case_id_columns": 2}
    assert ei.value.message == "2 columns resolve to case_id; reduce your case key to one column"


def test_fold_header_strips_surrounding_whitespace():
    """Observes lens-3 L13: ``fold_header(" Label ")`` is ``label``, and the in-memory pair
    ``label`` + ``" Label "`` halts H07 in ``map_headers``."""
    assert fold_header(" Label ") == "label" and fold_header("﻿ Label\t") == "label"
    with pytest.raises(HaltError) as ei:
        map_headers(["label", " Label "])
    assert ei.value.code == "H07" and ei.value.detail == {"n_duplicate_headers": 1}


def test_two_high_case_id_columns_reach_e01_at_apply():
    """Observes lens-3 L14 (``apply_mapping``'s E01 counting non-high ``case_id`` only): a
    hand-built mapping with ``case_id`` high on two columns."""
    cols = _cols(a=["1", "2"], b=["3", "4"], y=["0", "1"])
    m = Mapping(
        header_set_sha256(list(cols)),
        [
            RoleMapping("a", "case_id", "high"),
            RoleMapping("b", "case_id", "high"),
            RoleMapping("y", "y_true", "high"),
        ],
        "file",
        "",
    )
    with pytest.raises(HaltError) as ei:
        apply_mapping(cols, m)
    assert ei.value.code == "E01" and ei.value.detail == {"n_case_id_columns": 2}


def test_every_canonical_name_normalises_to_itself():
    """Observes lens-3 L20: the 19 canonical names each satisfy
    ``normalise_header(name) == name``, so ``_name_claim`` needs ``key in canon`` only."""
    names = canonical_columns()
    assert len(names) == 19
    assert [normalise_header(n) for n in names] == names
    m = map_headers(names)
    assert [(r.role, r.source, r.confidence) for r in m.roles] == [
        (n, "canonical", "high") for n in names
    ]


# --------------------------------------------------------------------------- the fixture demo


def test_sepsis_fixture_confirmed_interactively_passes_yes_and_run(
    tmp_path: Path, capsys, monkeypatch
):
    """The committed PhysioNet-shaped fixture (``patient`` low, ``Gender`` 0/1 medium):
    ``a a`` at the two prompts, then ``map --yes`` exit 0 (needs-from-Josh 2 of the day-6
    handoff, DEC-28)."""
    raw = load_table(FIXTURES / "sepsis_2019.csv")
    fresh = map_headers(raw.headers, raw.columns)
    assert [(r.original, r.role, r.confidence) for r in fresh.non_high] == [
        ("patient", "case_id", "low"),
        ("Gender", "sex", "medium"),
    ]
    out = tmp_path / "m.json"
    prompts = _drive(monkeypatch, ["a", "a"])
    src = str(FIXTURES / "sepsis_2019.csv")
    assert main(["--quiet", "map", "--input", src, "--out", str(out)]) == EXIT_OK
    assert len(prompts) == 2
    assert main(["--quiet", "map", "--input", src, "--out", str(out), "--yes"]) == EXIT_OK
    assert capsys.readouterr().err == ""
