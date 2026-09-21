"""Day 6 A, repair 4.2 (A-P1 the full mapper) - lens 1 on 9cfbdd5: B1 in both notes (the
DEC-42 exemption followed a planted ``confirmed`` flag in a ``file`` prior, and the README
and ``_summaries_agree`` said such a prior "holds no value summary" and "is refused"),
regression N1 (the ``check_h07`` class sentence), N3 (two wrong cross-references) and N5
(the DEC-42 test id).

Every test names the literal input it feeds and the figures it asserts. Each test whose
docstring begins "At 9cfbdd5" failed at that sha (the first ``E`` line is in the repair-4.2
note). The sentence test reads ``README.md``, so ``scripts/mutation_sweep.py`` now copies
it (a test that cannot open it would fail against every mutant and count each killed).
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from conftest import make_cohort, make_criteria, write_csv, write_yaml
from proofpack import gates
from proofpack.cli import main
from proofpack.errors import EXIT_HALT, EXIT_OK
from proofpack.io.mapping import (
    Mapping,
    RoleMapping,
    _summaries_agree,
    check_h07,
    map_headers,
    period_for_validate,
)
from proofpack.io.schema import header_set_sha256

pytestmark = pytest.mark.day6

SITE_ONLY = [{"attribute": "site", "prespecified": False, "reference_level": "largest"}]
ROLE_DIFFERENCE = (
    "HALT H07: mapping.json maps a column to {prior} but the mapping computed from this "
    "table gives it {fresh}; run proofpack map again"
)


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


def _run(csv_path: Path, yml: Path, mapping: Path | None, out: Path, *flags: str) -> int:
    argv = ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), *flags]
    if mapping is not None:
        argv += ["--mapping", str(mapping)]
    return main(argv)


def _edit(path: Path, *, original: str, role: str, decided_by: str | None, **entry) -> bytes:
    """Rewrite one entry of a mapping.json by hand and set (or drop) the file's decided_by."""
    data = json.loads(path.read_text(encoding="utf-8"))
    for r in data["roles"]:
        if r["original"] == original:
            r["role"] = role
            r["confirmed"] = True
            r.update(entry)
    if decided_by is None:
        data.pop("decided_by", None)
    else:
        data["decided_by"] = decided_by
    path.write_text(json.dumps(data), encoding="utf-8")
    return path.read_bytes()


def _first_err(capsys) -> str:
    return capsys.readouterr().err.splitlines()[0]


# --------------------------------------------------------------------------- B1 (both notes)


def test_a_confirmed_file_prior_is_h07_on_a_role_difference_with_or_without_a_summary(
    tmp_path: Path, capsys
):
    """At 9cfbdd5 the file ``proofpack run`` wrote without a prompt on ``make_cohort(200)``
    (``decided_by: proposed``, a summary for each of ``row_id, y_true, score, sex, age,
    site``), copied with ``decided_by: file``, ``age -> attr_age_years`` and ``confirmed:
    true`` typed in, passed ``map --yes`` (exit 0, the file rewritten) and ``run --yes``
    (exit 0, ``attr_age_years`` in ``roles_present``) - lens-1 fresh-attack B1 of repair 4.
    Now both are exit 3 H07 ``maps a column to attr_age_years but the mapping computed from
    this table gives it age`` (the line 4fbbf35 printed) and the file's bytes are unchanged;
    the same with ``sex -> ignore`` (``gives it sex``) and with the ``decided_by`` key
    removed. The hand-built prior of lens-1 regression B1 (every role ``high``, ``site ->
    ignore``, ``confirmed: true``, ``value_summaries`` = the one line ``{"site":
    {"inferred_type": "categorical", "split": null}}``) is H07 ``gives it site`` as it is
    with ``value_summaries: {}``. On the Sepsis-shaped cohort a ``file`` prior written by
    ``map_headers`` with ``Gender -> attr_gender_code`` confirmed (``Gender`` is ``medium``
    as computed, the summary intact) is H07 ``gives it sex``: ``decided_by`` alone refuses
    that one."""
    cols = make_cohort(n=200)
    csv_path = write_csv(tmp_path / "t.csv", cols)
    yml = write_yaml(tmp_path / "c.yaml", make_criteria(subgroups=SITE_ONLY))
    assert _run(csv_path, yml, None, tmp_path / "p1") == EXIT_OK
    written = json.loads((tmp_path / "p1" / "mapping.json").read_text(encoding="utf-8"))
    assert written["decided_by"] == "proposed"
    assert sorted(written["value_summaries"]) == ["age", "row_id", "score", "sex", "site", "y_true"]
    hand = tmp_path / "hand.json"
    for original, role, decided_by, fresh in (
        ("age", "attr_age_years", "file", "age"),
        ("sex", "ignore", "file", "sex"),
        ("age", "attr_age_years", None, "age"),
    ):
        hand.write_text(json.dumps(written), encoding="utf-8")
        before = _edit(hand, original=original, role=role, decided_by=decided_by)
        rc = main(["map", "--input", str(csv_path), "--out", str(hand), "--yes"])
        assert rc == EXIT_HALT, (original, role, decided_by)
        assert _first_err(capsys) == ROLE_DIFFERENCE.format(prior=role, fresh=fresh)
        assert hand.read_bytes() == before
        rc = _run(csv_path, yml, hand, tmp_path / "p2", "--yes")
        assert rc == EXIT_HALT, (original, role, decided_by)
        assert _first_err(capsys) == ROLE_DIFFERENCE.format(prior=role, fresh=fresh)
        assert not (tmp_path / "p2").exists()
    # the hand-built prior of lens-1 regression B1: one summary line typed in
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t2.csv", cols)
    built = Mapping(
        header_set_sha256(list(cols)),
        [RoleMapping(h, None if h == "site" else h, "high", "file", [], h == "site") for h in cols],
        "file",
        "",
    )
    prior = tmp_path / "built.json"
    for summaries in ({"site": {"inferred_type": "categorical", "split": None}}, {}):
        built.value_summaries = summaries
        built.write(prior)
        before = prior.read_bytes()
        rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
        assert rc == EXIT_HALT, summaries
        assert _first_err(capsys) == ROLE_DIFFERENCE.format(prior="ignore", fresh="site")
        assert prior.read_bytes() == before
    # decided_by alone: Gender is medium as computed and its summary is the engine's
    cols = _sepsis_shaped()
    csv_path = write_csv(tmp_path / "s.csv", cols)
    m = map_headers(list(cols), cols)
    assert (m.entry("Gender").role, m.entry("Gender").confidence) == ("sex", "medium")
    m.entry("Gender").role = "attr_gender_code"
    m.entry("Gender").confirmed = True
    m.entry("patient").confirmed = True
    m.decided_by = "file"
    prior = tmp_path / "s.json"
    m.write(prior)
    before = prior.read_bytes()
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    assert rc == EXIT_HALT
    assert _first_err(capsys) == ROLE_DIFFERENCE.format(prior="attr_gender_code", fresh="sex")
    assert prior.read_bytes() == before


def test_decided_by_interactive_typed_by_hand_is_read_on_a_non_high_entry_only(
    tmp_path: Path, capsys, monkeypatch
):
    """At 9cfbdd5 the copy of the previous test with ``decided_by: interactive`` typed
    beside ``age -> attr_age_years``, ``confirmed: true`` passed ``map --yes``; now it is
    H07 ``gives it age`` because the mapping computed from the table gives ``age`` ``high``
    and the prompt asks about ``medium`` and ``low`` entries only - with ``"confidence":
    "medium"`` typed on the entry as well it is the same H07 (the computed confidence is
    read, not the stored one). What passes, pinned: on the Sepsis-shaped cohort the file
    ``map_headers`` wrote with ``decided_by: interactive`` typed, ``Gender -> attr_gender_code``
    and ``confirmed: true`` (``Gender`` is ``medium`` as computed, the stored summary is the
    engine's) -> ``map --yes`` exit 0 and the file rewritten with that role; and the file the
    prompt wrote after ``a a`` with ``patient -> sex`` and ``Gender -> case_id`` swapped by
    hand -> ``map --yes`` exit 0, then ``run --yes`` exit 3 H05 (three rows per ``patient``
    value now read as ``case_id`` with conflicting ``y_true``), a gate after the mapping
    check. The swapped file and the one the prompt writes for ``e sex``, ``e case_id``
    differ in the two ``notes`` strings (``accepted interactively`` / ``edited
    interactively``) and the timestamp only, and ``_check_yes_rule`` reads neither."""
    cols = make_cohort(n=200)
    csv_path = write_csv(tmp_path / "t.csv", cols)
    yml = write_yaml(tmp_path / "c.yaml", make_criteria(subgroups=SITE_ONLY))
    assert _run(csv_path, yml, None, tmp_path / "p1") == EXIT_OK
    hand = tmp_path / "hand.json"
    for entry in ({}, {"confidence": "medium"}):
        hand.write_bytes((tmp_path / "p1" / "mapping.json").read_bytes())
        before = _edit(
            hand, original="age", role="attr_age_years", decided_by="interactive", **entry
        )
        rc = main(["map", "--input", str(csv_path), "--out", str(hand), "--yes"])
        assert rc == EXIT_HALT, entry
        assert _first_err(capsys) == ROLE_DIFFERENCE.format(prior="attr_age_years", fresh="age")
        assert hand.read_bytes() == before
    # the non-high entry with the engine's summary: the words are read
    cols = _sepsis_shaped()
    csv_path = write_csv(tmp_path / "s.csv", cols)
    m = map_headers(list(cols), cols)
    m.entry("Gender").role = "attr_gender_code"
    m.entry("Gender").confirmed = True
    m.entry("patient").confirmed = True
    m.decided_by = "interactive"
    prior = tmp_path / "s.json"
    m.write(prior)
    rc = main(["--quiet", "map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    assert rc == EXIT_OK and capsys.readouterr().err == ""
    after = json.loads(prior.read_text(encoding="utf-8"))
    roles = {r["original"]: r["role"] for r in after["roles"]}
    assert (roles["Gender"], after["decided_by"]) == ("attr_gender_code", "interactive")
    # the prompt's own file after "a a", two confirmed roles swapped by hand
    out = tmp_path / "m.json"
    prompts = _drive(monkeypatch, ["a", "a"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    assert len(prompts) == 2
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["decided_by"] == "interactive"
    for r in data["roles"]:
        if r["original"] == "patient":
            assert (r["role"], r["confidence"], r["confirmed"]) == ("case_id", "low", True)
            r["role"] = "sex"
        if r["original"] == "Gender":
            assert (r["role"], r["confidence"], r["confirmed"]) == ("sex", "medium", True)
            r["role"] = "case_id"
    out.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["--quiet", "map", "--input", str(csv_path), "--out", str(out), "--yes"])
    assert rc == EXIT_OK and capsys.readouterr().err == ""
    swapped = {
        r["original"]: r["role"] for r in json.loads(out.read_text(encoding="utf-8"))["roles"]
    }
    assert (swapped["patient"], swapped["Gender"]) == ("sex", "case_id")
    edited = tmp_path / "ee.json"
    _drive(monkeypatch, ["e", "sex", "e", "case_id"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(edited)]) == EXIT_OK
    by_hand = {r["original"]: r for r in data["roles"]}
    by_prompt = {r["original"]: r for r in json.loads(edited.read_text(encoding="utf-8"))["roles"]}
    differences = [(h, k) for h, r in by_hand.items() for k in r if r[k] != by_prompt[h][k]]
    assert differences == [("patient", "notes"), ("Gender", "notes")]
    assert by_hand["patient"]["notes"][-1:] + by_prompt["patient"]["notes"][-1:] == [
        "accepted interactively",
        "edited interactively",
    ]
    yml = write_yaml(tmp_path / "s.yaml", make_criteria(subgroups=SITE_ONLY))
    rc = _run(csv_path, yml, out, tmp_path / "ps", "--yes")
    assert rc == EXIT_HALT
    assert _first_err(capsys).startswith("HALT H05:")


def test_yes_and_run_mapping_keep_decided_by_interactive(tmp_path: Path, capsys, monkeypatch):
    """At 9cfbdd5 ``check_h07`` rewrote an ``interactive`` prior ``file`` on the way out, so
    the Sepsis-shaped cohort answered ``a e attr_gender_code`` and then ``map --yes`` was
    written back ``decided_by: file``. Now: ``map --yes`` twice -> exit 0 both times and
    ``interactive`` both times (under the repair-4.2 rule the second pass would have been
    H07 ``gives it sex`` on the rewritten word); ``run --mapping`` without and with
    ``--yes`` on the lens-3 table ``row_id,label,score,prob,site`` answered ``e
    attr_score_flag a`` -> exit 2 (W10 only) and the pack's ``mapping.json`` says
    ``interactive`` with ``score -> attr_score_flag`` (the Sepsis-shaped cohort itself halts
    H05 at ``run``, three rows per ``patient``); a prior saying
    ``file`` is written back ``file`` and, through ``gates.ingest``, returned ``file``; the
    ``proposed`` case is ``tests/test_mapping_repair3_2.py::
    test_a_proposed_prior_is_not_relabelled_file_by_run_mapping``."""
    cols = _sepsis_shaped()
    csv_path = write_csv(tmp_path / "s.csv", cols)
    yml = write_yaml(tmp_path / "c.yaml", make_criteria(subgroups=SITE_ONLY))
    out = tmp_path / "m.json"
    _drive(monkeypatch, ["a", "e", "attr_gender_code"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    for _ in range(2):
        rc = main(["--quiet", "map", "--input", str(csv_path), "--out", str(out), "--yes"])
        assert rc == EXIT_OK and capsys.readouterr().err == ""
        after = json.loads(out.read_text(encoding="utf-8"))
        assert after["decided_by"] == "interactive"
        assert {r["original"]: r["role"] for r in after["roles"]}["Gender"] == "attr_gender_code"
    # run on a table run takes: the lens-3 table, e attr_score_flag a (W10 only, exit 2)
    cols = _cols(
        row_id=[str(i) for i in range(60)],
        label=["0", "1"] * 30,
        score=["1", "0", "0"] * 20,
        prob=[f"{(i % 10) / 10:.1f}" for i in range(60)],
        site=["A", "B", "B"] * 20,
    )
    csv_path = write_csv(tmp_path / "sp.csv", cols)
    out = tmp_path / "sp.json"
    _drive(monkeypatch, ["e", "attr_score_flag", "a"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    for flags, pack in (((), "p1"), (("--yes",), "p2")):
        rc = _run(csv_path, yml, out, tmp_path / pack, *flags)
        assert rc == 2, capsys.readouterr().err
        copy = json.loads((tmp_path / pack / "mapping.json").read_text(encoding="utf-8"))
        assert copy["decided_by"] == "interactive", flags
        assert {r["original"]: r["role"] for r in copy["roles"]}["score"] == "attr_score_flag"
    # a prior saying file keeps that word too
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    m = map_headers(list(cols), cols)
    m.decided_by = "file"
    prior = tmp_path / "f.json"
    m.write(prior)
    rc = main(["--quiet", "map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    assert rc == EXIT_OK and capsys.readouterr().err == ""
    assert Mapping.read(prior).decided_by == "file"
    assert check_h07(list(cols), prior, non_interactive=True, fresh=m).decided_by == "file"


# --------------------------------------------------------------------------- N1, N3, B1's sentences


def test_the_five_sentences_lens_1_of_repair_4_named_are_gone_from_the_shipped_text():
    """At 9cfbdd5 each of these strings was in the shipped text; lens 1 of repair 4 named
    them (fresh-attack B1, regression B1, N1, N3). Inspected: the README's ``mapping.json``
    paragraph, ``_summaries_agree``'s and ``check_h07``'s docstrings, ``period_for_validate``'s
    docstring and the ``ingest`` source of ``gates.py``."""

    def flat(text: str) -> str:
        return " ".join(text.split())  # the docstrings wrap mid-sentence

    readme = flat((Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8"))
    assert "holds no value summary to compare and is refused on the role difference" not in readme
    assert "a hand-authored ``file`` prior holds none" not in flat(_summaries_agree.__doc__)
    assert "no edited file passed" not in flat(check_h07.__doc__)
    assert "lens-2 FA-B1 of repair 3.2" not in flat(period_for_validate.__doc__)
    assert "lens-2 FA-B1 of repair 3.2" not in flat(inspect.getsource(gates.ingest))
    # the replacements name the inputs fed
    assert (
        "test_a_confirmed_file_prior_is_h07_on_a_role_difference_with_or_without_a_summary"
        in readme
    )
    assert "lens-2 FA-B2 of repair 3.2" in flat(period_for_validate.__doc__)
    assert "lens-2 FA-B2 of repair 3.2" in flat(inspect.getsource(gates.ingest))
