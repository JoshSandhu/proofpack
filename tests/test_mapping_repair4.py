"""Day 6 A, repair 4 (A-P1 the full mapper) - the lens-2 findings on 4fbbf35: FA-B1 (the
per-value date order leaked a nine-row month), FA-B2 (an ignored column named by
``period.column`` was the pack's period axis), FA-B3 / RG-N1 (the README ``--yes``
sentence and its unpinned no-summary choice), RG-B1 (the ``_summary_shape`` sentence),
and DEC-42 (an edit at the prompt confirms the entry).

Every test names the literal input it feeds and the figures it asserts. Each test whose
docstring begins "At 4fbbf35" failed at that sha (the first ``E`` line is in the repair-4
note); those whose docstring begins "Passes at 4fbbf35" did not: they pin a choice, or
feed the input a sentence or a mutant needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import make_cohort, make_criteria, write_csv, write_yaml
from proofpack.cli import main
from proofpack.errors import EXIT_HALT, EXIT_OK, HaltError
from proofpack.gates import ingest
from proofpack.io import declare
from proofpack.io.mapping import (
    PERIOD_IGNORED,
    Mapping,
    RoleMapping,
    _summary_shape,
    map_headers,
    period_for_validate,
)
from proofpack.io.profile import SUPPRESSED, profile_column
from proofpack.io.schema import header_set_sha256, table_from_columns

pytestmark = pytest.mark.day6

SITE_ONLY = [{"attribute": "site", "prespecified": False, "reference_level": "largest"}]
PERIOD_HALT = f"HALT S03: {PERIOD_IGNORED}"


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


def _lens_table() -> dict:
    """The lens-3 FA-B2 table: ``score`` holds 0/1, ``prob`` floats in [0, 1]; 60 rows;
    ``site`` (A/B) so ``run`` has the one subgroup attribute its criteria declare."""
    return _cols(
        row_id=[str(i) for i in range(60)],
        label=["0", "1"] * 30,
        score=["1", "0", "0"] * 20,
        prob=[f"{(i % 10) / 10:.1f}" for i in range(60)],
        site=["A", "B", "B"] * 20,
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


# --------------------------------------------------------------------------- FA-B1 (DEC-39)


def test_date_order_is_decided_once_per_column():
    """At 4fbbf35 ``["03/15/2024"] * 9 + ["04/03/2024"]`` printed ``min 2024-03 max 2024-03``
    (nine rows of March 2024 and one of April, read under two conventions in one column),
    and ``["03/15/2024"] * 9 + ["03/04/2024"]`` (ten rows of March) printed ``<suppressed>``
    twice (lens-2 FA-B1). The ``.`` and ``-`` twins behave the same; ``["03/13/2024"] * 60``
    -> ``2024-03`` (M09) and ``["12/15/2024"] * 60`` -> ``2024-12`` (M21)."""
    for sep in ("/", ".", "-"):
        march = f"03{sep}15{sep}2024"
        nine_march_one_april = [march] * 9 + [f"04{sep}03{sep}2024"]
        s = profile_column(nine_march_one_april)
        assert (s.inferred_type, s.min, s.max) == ("date", SUPPRESSED, SUPPRESSED), sep
        ten_march = [march] * 9 + [f"03{sep}04{sep}2024"]
        s = profile_column(ten_march)
        assert (s.inferred_type, s.min, s.max) == ("date", "2024-03", "2024-03"), sep
    s = profile_column(["03/15/2024"] * 9 + ["04/03/2024"] + ["12/25/2025"] * 50)
    assert (s.min, s.max) == (SUPPRESSED, "2025-12")
    # the two boundaries lens 2 left unpinned (its mutants M09 and M21)
    assert profile_column(["03/13/2024"] * 60).min == "2024-03"
    assert profile_column(["12/15/2024"] * 60).min == "2024-12"
    # a first field above 12 anywhere in the column keeps every value day-first: the
    # 30/30 mix of ``15.03.2024`` and ``03/15/2024`` keys the second half ``2024-15``
    s = profile_column(["15.03.2024"] * 30 + ["03/15/2024"] * 30)
    assert (s.min, s.max) == ("2024-03", "2024-15")


def test_the_printed_table_withholds_a_nine_row_month_of_a_us_shaped_column(
    tmp_path: Path, capsys, monkeypatch
):
    """At 4fbbf35 the table ``proofpack map`` printed for ``visit`` = ``["03/15/2024"] * 9 +
    ["04/03/2024"] + ["12/25/2025"] * 50`` read ``min 2024-03 max 2025-12`` (lens-2 FA-B1);
    now ``min <suppressed> max 2025-12``. stdin is not a terminal, so the table prints and
    the command halts H07 before any prompt."""
    cols = make_cohort(n=60)
    cols["visit"] = ["03/15/2024"] * 9 + ["04/03/2024"] + ["12/25/2025"] * 50
    csv_path = write_csv(tmp_path / "t.csv", cols)
    yml = write_yaml(
        tmp_path / "c.yaml", make_criteria(period={"column": "visit", "granularity": "quarter"})
    )
    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: False)
    rc = main(
        ["map", "--input", str(csv_path), "--criteria", str(yml), "--out", str(tmp_path / "m")]
    )
    captured = capsys.readouterr()
    assert rc == EXIT_HALT and "stdin is not a terminal" in captured.err
    visit_line = next(line for line in captured.out.splitlines() if line.startswith("  'visit'"))
    assert "min <suppressed> max 2025-12" in visit_line and "2024-03" not in captured.out


# --------------------------------------------------------------------------- FA-B2 (period)


def test_an_ignored_visit_named_by_period_column_is_s03_on_both_routes(
    tmp_path: Path, capsys, monkeypatch
):
    """At 4fbbf35 ``make_cohort(60)`` plus ``visit`` = ``["2024-03-15"] * 30 +
    ["2024-09-15"] * 30`` with ``period: {column: visit, granularity: quarter}``, ``map``
    answered ``e ignore`` and ``run --mapping`` was exit 0 with ``table.period`` levels
    ``2024-Q1, 2024-Q3`` from the ignored column and ``n_unused_columns: 1`` (lens-2
    FA-B2); ``visit`` of one ISO date and 59 blanks, proposed ``ignore high``, did the
    same through ``run`` with no prior. Both routes are S03 now; the prompt refuses the
    ``ignore``; and the control ``visit -> event_date`` builds the period under the
    original header (S03 ``not present in the table`` at 4fbbf35, lens-2 N4)."""
    cols = make_cohort(n=60)
    cols["visit"] = ["2024-03-15"] * 30 + ["2024-09-15"] * 30
    csv_path = write_csv(tmp_path / "t.csv", cols)
    yml = write_yaml(
        tmp_path / "c.yaml",
        make_criteria(period={"column": "visit", "granularity": "quarter"}, subgroups=SITE_ONLY),
    )
    out = tmp_path / "m.json"
    fresh = map_headers(list(cols), cols)
    assert [(r.original, r.role, r.confidence) for r in fresh.non_high] == [
        ("visit", "event_date", "medium")
    ]
    # the prior route: the file map wrote at 4fbbf35 for ``e ignore`` (visit -> ignore,
    # decided_by interactive), built here without the prompt
    prior = map_headers(list(cols), cols)
    prior.entry("visit").role = None
    prior.entry("visit").confirmed = True
    prior.decided_by = "interactive"
    prior.write(out)
    before = out.read_bytes()
    for flags in ([], ["--yes"]):
        rc = _run(csv_path, yml, out, tmp_path / "p", *flags)
        err = capsys.readouterr().err
        assert rc == EXIT_HALT, flags
        assert err.splitlines()[0] == PERIOD_HALT and "visit" not in err
        assert '"period_column_ignored": true' in err
        assert not (tmp_path / "p").exists()
    with pytest.raises(HaltError) as ei:
        ingest(table_from_columns(cols), declare.load(yml), mapping_path=out)
    assert (ei.value.code, ei.value.detail) == ("S03", {"period_column_ignored": True})
    rc = main(["map", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and err.splitlines()[0] == PERIOD_HALT
    assert out.read_bytes() == before
    # the prompt: e ignore is refused with the one line, a then accepts event_date
    prompts = _drive(monkeypatch, ["e", "ignore", "a"])
    rc = main(["map", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out)])
    captured = capsys.readouterr()
    assert rc == EXIT_OK and len(prompts) == 3
    assert f"  refused: {PERIOD_IGNORED}" in captured.out.splitlines()
    written = json.loads(out.read_text(encoding="utf-8"))
    visit = next(r for r in written["roles"] if r["original"] == "visit")
    assert (visit["role"], visit["confirmed"]) == ("event_date", True)
    # the control: run --mapping on that file builds the period from the mapped column
    rc = _run(csv_path, yml, out, tmp_path / "p0")
    assert rc == EXIT_OK, capsys.readouterr().err
    report = json.loads((tmp_path / "p0" / "ingest_report.json").read_text(encoding="utf-8"))
    assert report["n_unused_columns"] == 0 and "event_date" in report["roles_present"]
    result = ingest(table_from_columns(cols), declare.load(yml), mapping_path=out)
    assert sorted(set(result.table.period.tolist())) == ["2024-Q1", "2024-Q3"]
    before = out.read_bytes()
    # the computed route: one date and 59 blanks is proposed ignore high and never prompted
    cols["visit"] = ["2024-03-15"] + [""] * 59
    csv_path = write_csv(tmp_path / "t2.csv", cols)
    fresh = map_headers(list(cols), cols)
    assert (fresh.entry("visit").role, fresh.entry("visit").confidence) == (None, "high")
    rc = _run(csv_path, yml, None, tmp_path / "p2")
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and err.splitlines()[0] == PERIOD_HALT
    assert not (tmp_path / "p2").exists()
    # at map every role is high, so the one prompt is the all-high accept; then S03
    prompts = _drive(monkeypatch, ["a"])
    rc = main(["map", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out)])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and err.splitlines()[0] == PERIOD_HALT and len(prompts) == 1
    assert out.read_bytes() == before  # nothing written over the prior
    # a period declaration naming the role, or a name that is no header, is passed through
    m = fresh
    m.entry("visit").role = "event_date"
    assert period_for_validate(m, {"column": "visit", "granularity": "quarter"}) == {
        "column": "event_date",
        "granularity": "quarter",
    }
    for pcol in ("event_date", "period", "other"):
        period = {"column": pcol, "granularity": "month"}
        assert period_for_validate(m, period) is period
    assert period_for_validate(m, None) is None


# --------------------------------------------------------------------------- FA-B3 / RG-N1


def test_a_confirmed_prior_without_summaries_is_not_compared(tmp_path: Path, capsys, monkeypatch):
    """Passes at 4fbbf35: the choice lens-2 FA-B3 / RG-N1 asked to pin. The Sepsis-shaped
    cohort confirmed ``a a``, ``value_summaries`` replaced by ``{}`` and by ``null``, then
    ``patient`` re-exported as the ten strings ``0.0`` .. ``0.9`` -> ``map --yes`` exit 0 and
    the file rewritten ``decided_by: file`` (with the summaries intact the same re-export is
    H07: ``tests/test_mapping_repair3_2.py::
    test_yes_halts_h07_when_a_confirmed_columns_values_changed``).
    With ``or`` -> ``and`` in ``_summaries_agree`` (lens-2 M06) this is exit 5 ``KeyError``."""
    cols = _sepsis_shaped()
    csv_path = write_csv(tmp_path / "s.csv", cols)
    out = tmp_path / "m.json"
    _drive(monkeypatch, ["a", "a"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["value_summaries"]["patient"]["inferred_type"] == "categorical"
    write_csv(csv_path, {**cols, "patient": [f"{(i % 10) / 10:.1f}" for i in range(60)]})
    for summaries in ({}, None):
        out.write_text(json.dumps({**data, "value_summaries": summaries}), encoding="utf-8")
        rc = main(["--quiet", "map", "--input", str(csv_path), "--out", str(out), "--yes"])
        assert rc == EXIT_OK and capsys.readouterr().err == "", summaries
        after = json.loads(out.read_text(encoding="utf-8"))
        assert after["decided_by"] == "file" and after["value_summaries"] == {}


# --------------------------------------------------------------------------- RG-B1


def test_a_split_that_is_a_list_of_non_lists_is_an_empty_split(tmp_path: Path, capsys, monkeypatch):
    """Passes at 4fbbf35 (the code was right, the ``_summary_shape`` sentence was not: lens-2
    RG-B1). ``split: [1, 2]``, ``[]`` and ``[[]]`` read as an empty split (``frozenset()``),
    ``"x"`` and ``{}`` as no split (``None``); a stored ``patient`` split hand-set to ``[1, 2]``
    beside the fresh ``null`` halts ``map --yes`` H07 on the unchanged table."""
    assert _summary_shape({"inferred_type": "categorical", "split": None}) == ("categorical", None)
    for split in ([1, 2], [], [[]]):
        assert _summary_shape({"inferred_type": "categorical", "split": split}) == (
            "categorical",
            frozenset(),
        ), split
    for split in ("x", {}):
        assert _summary_shape({"inferred_type": "categorical", "split": split}) == (
            "categorical",
            None,
        ), split
    assert _summary_shape("x") is None
    cols = _sepsis_shaped()
    csv_path = write_csv(tmp_path / "s.csv", cols)
    out = tmp_path / "m.json"
    _drive(monkeypatch, ["a", "a"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["value_summaries"]["patient"]["split"] is None
    data["value_summaries"]["patient"]["split"] = [1, 2]
    out.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["map", "--input", str(csv_path), "--out", str(out), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: the values of a column confirmed at the prompt changed since mapping.json "
        "was written (inferred type or the two-valued split); run proofpack map again"
    )


# --------------------------------------------------------------------------- DEC-42


def test_an_edit_at_the_prompt_is_confirmed_and_passes_yes(tmp_path: Path, capsys, monkeypatch):
    """At 4fbbf35 the DEC-31 remedy on ``row_id,label,score,prob,site`` (``e attr_score_flag``
    for ``score``, ``a`` for ``prob``) wrote ``score`` unconfirmed and ``map --yes`` was H07
    ``requires every mapped role at high confidence in mapping.json or confirmed at the
    prompt`` for ever (lens-1 RG-N4 / repair-3 open question 1). Now both entries are
    ``confirmed: true``, ``map --yes`` is exit 0 and ``run --yes`` exit 2 (W10 only);
    ``patient`` (low)
    edited to ``attr_patient_code`` passes too. A ``file`` prior with ``confirmed: true`` on
    ``site -> ignore`` and no stored summary for ``site`` is refused on the role difference;
    the same flag planted in a file ``map_headers`` wrote (summaries intact) passes - the
    flag is read and not verified (the README sentence)."""
    cols = _lens_table()
    csv_path = write_csv(tmp_path / "sp.csv", cols)
    yml = write_yaml(tmp_path / "c.yaml", make_criteria(subgroups=SITE_ONLY))
    out = tmp_path / "sp.json"
    prompts = _drive(monkeypatch, ["e", "attr_score_flag", "a"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    assert len(prompts) == 3
    rc = main(["--quiet", "map", "--input", str(csv_path), "--out", str(out), "--yes"])
    assert rc == EXIT_OK and capsys.readouterr().err == ""
    after = json.loads(out.read_text(encoding="utf-8"))
    roles = {r["original"]: r for r in after["roles"]}
    assert after["decided_by"] == "file"
    assert (roles["score"]["role"], roles["score"]["confidence"], roles["score"]["confirmed"]) == (
        "attr_score_flag",
        "low",
        True,
    )
    assert (roles["prob"]["role"], roles["prob"]["confirmed"]) == ("score", True)
    rc = _run(csv_path, yml, out, tmp_path / "p", "--yes")
    # exit 2 = warnings only: W10, the table's prevalence 0.5 against the declared 0.3
    assert rc == 2, capsys.readouterr().err
    report = json.loads((tmp_path / "p" / "ingest_report.json").read_text(encoding="utf-8"))
    assert report["roles_present"] == ["attr_score_flag", "row_id", "score", "site", "y_true"]
    # an entry edited to a role whose fresh confidence is low: patient -> attr_patient_code
    cols = _sepsis_shaped()
    csv_path = write_csv(tmp_path / "s.csv", cols)
    out = tmp_path / "s.json"
    _drive(monkeypatch, ["e", "attr_patient_code", "a"])
    assert main(["--quiet", "map", "--input", str(csv_path), "--out", str(out)]) == EXIT_OK
    data = json.loads(out.read_text(encoding="utf-8"))
    patient = next(r for r in data["roles"] if r["original"] == "patient")
    assert (patient["role"], patient["confidence"], patient["confirmed"]) == (
        "attr_patient_code",
        "low",
        True,
    )
    rc = main(["--quiet", "map", "--input", str(csv_path), "--out", str(out), "--yes"])
    assert rc == EXIT_OK and capsys.readouterr().err == ""
    # a hand-authored file prior: confirmed: true on site -> ignore, no summaries
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    hand = Mapping(
        header_set_sha256(list(cols)),
        [RoleMapping(h, None if h == "site" else h, "high", "file", [], h == "site") for h in cols],
        "file",
        "",
    )
    prior = tmp_path / "hand.json"
    hand.write(prior)
    assert json.loads(prior.read_text(encoding="utf-8"))["value_summaries"] == {}
    rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    err = capsys.readouterr().err
    assert rc == EXIT_HALT
    assert err.splitlines()[0] == (
        "HALT H07: mapping.json maps a column to ignore but the mapping computed from this "
        "table gives it site; run proofpack map again"
    )
    # the flag planted in a file map_headers wrote: the stored site summary equals the
    # fresh one, so the ignore stands (the flag cannot be verified)
    planted = map_headers(list(cols), cols)
    planted.entry("site").role = None
    planted.entry("site").confirmed = True
    planted.decided_by = "file"
    planted.write(prior)
    rc = main(["--quiet", "map", "--input", str(csv_path), "--out", str(prior), "--yes"])
    assert rc == EXIT_OK and capsys.readouterr().err == ""
