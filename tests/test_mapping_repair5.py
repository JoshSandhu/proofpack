"""Day 6 A, repair 5 (A-P1 the full mapper), applied by the orchestrating session after the
round-4 lens cap on f108f17 - the two blockers of the lens-2 fresh-attack note
(scratchpad notes/2026-09-21_A_p1_r4_lens2_fresh-attack.md):

FA-B2: ``profile_column`` typed ``["17 ſep 2024"] * 60`` (long s, U+017F) and
``["3 aprıl 2024"] * 60`` (dotless i, U+0131) ``date`` because Python's Unicode
IGNORECASE matches those two letters to ``s`` and ``i``, and ``_date_key``'s ASCII-only
month branch then missed them and returned the value itself, so the printed table and
``mapping.json`` carried a day-level date as the column's min and max. Now the month
pattern is ASCII (the two columns are not typed ``date``) and a value ``_date_key``
cannot key is withheld as ``<suppressed>``.

FA-B1: the README ``--yes`` bullet said a hand-authored ``file`` prior "holds none and is
not compared"; one that holds a summary line for a confirmed column is compared. The
sentence now says so and the test below pins the behaviour it describes (this test also
passes at f108f17: the behaviour was right, the sentence was not).

Each test names the literal input it feeds; the first ``E`` line at f108f17 for the FA-B2
test is quoted in the commit message.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import make_cohort, write_csv
from proofpack.cli import main
from proofpack.errors import EXIT_HALT, EXIT_OK
from proofpack.io.mapping import Mapping, RoleMapping
from proofpack.io.profile import DATE_PATTERNS, SUPPRESSED, _date_key, profile_column
from proofpack.io.schema import header_set_sha256

pytestmark = pytest.mark.day6

LONG_S = "17 ſep 2024"
DOTLESS_I = "3 aprıl 2024"


def test_a_month_name_with_a_long_s_or_a_dotless_i_is_not_typed_date_and_never_printed_day_level():
    """At f108f17: ``profile_column([LONG_S] * 60)`` -> ``('date', '17 ſep 2024',
    '17 ſep 2024')`` (the first E line of the run at that sha:
    ``assert 'date' != 'date'``). Now the two columns are ``categorical`` (their one value
    is shown by the k-floor as a top value, which is the categorical rule, not a date
    coarsening), no DATE_PATTERN matches either string, and ``_date_key`` withholds them."""
    for value in (LONG_S, DOTLESS_I):
        summary = profile_column([value] * 60)
        assert summary.inferred_type != "date", value
        assert summary.min not in (value,) and summary.max not in (value,), value
        assert not any(p.match(value) for p in DATE_PATTERNS), value
        assert _date_key(value) == SUPPRESSED
    # the ASCII spelling is unchanged
    summary = profile_column(["17 Sep 2024"] * 60)
    assert (summary.inferred_type, summary.min, summary.max) == ("date", "2024-09", "2024-09")
    # ten long-s rows beside fifty ISO rows: at f108f17 min was '17 ſep 2024'
    summary = profile_column([LONG_S] * 10 + ["2024-09-01"] * 50)
    assert LONG_S not in (summary.min, summary.max)


def test_the_cli_table_and_mapping_json_carry_no_day_level_date_for_the_long_s_column(
    tmp_path: Path, capsys, monkeypatch
):
    """``make_cohort(60)`` plus ``visit`` = ``[LONG_S] * 60``, ``map`` answered ``a`` at
    every prompt: neither the printed table nor ``mapping.json``'s value summaries hold
    the string ``17 ſep 2024`` as a min or max."""
    cols = {k: list(v) for k, v in make_cohort(n=60).items()}
    cols["visit"] = [LONG_S] * 60
    csv_path = write_csv(tmp_path / "t.csv", cols)
    monkeypatch.setattr("proofpack.cli._stdin_is_terminal", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "a")
    out = tmp_path / "m.json"
    rc = main(["map", "--input", str(csv_path), "--out", str(out)])
    captured = capsys.readouterr()
    assert rc == EXIT_OK, captured.err
    assert f"min {LONG_S}" not in captured.out and f"max {LONG_S}" not in captured.out
    data = json.loads(out.read_text(encoding="utf-8"))
    visit = data["value_summaries"]["visit"]
    assert visit.get("min") != LONG_S and visit.get("max") != LONG_S


def test_a_file_prior_with_a_typed_summary_is_compared(tmp_path: Path, capsys):
    """The README ``--yes`` clause: a hand-authored ``file`` prior that holds a summary
    line for a confirmed column is compared like an engine-written one. ``make_cohort()``
    to ``t.csv``; a prior with every role = its header at ``high``, ``decided_by: file``,
    ``confirmed: true`` on ``sex``, and ``value_summaries`` = ``{"sex":
    {"inferred_type": "int", "split": null}}`` (the fresh summary of ``sex`` is
    ``categorical`` with a two-valued split) -> ``map --yes`` exit 3 H07 ``the values of a
    column confirmed at the prompt changed``; the same prior with the fresh summary's
    ``inferred_type`` and ``split`` typed in -> exit 0 (compared and equal); with
    ``value_summaries: {}`` -> exit 0 (not compared)."""
    cols = make_cohort()
    csv_path = write_csv(tmp_path / "t.csv", cols)
    fresh = profile_column(list(cols["sex"]))
    built = Mapping(
        header_set_sha256(list(cols)),
        [RoleMapping(h, h, "high", "file", [], h == "sex") for h in cols],
        "file",
        "",
    )
    prior = tmp_path / "hand.json"
    outcomes = []
    for summaries in (
        {"sex": {"inferred_type": "int", "split": None}},
        {"sex": {"inferred_type": fresh.inferred_type, "split": fresh.split}},
        {},
    ):
        built.value_summaries = summaries
        built.write(prior)
        rc = main(["map", "--input", str(csv_path), "--out", str(prior), "--yes"])
        err = capsys.readouterr().err
        outcomes.append((rc, err.splitlines()[0] if err else ""))
    assert outcomes[0][0] == EXIT_HALT and "confirmed at the prompt changed" in outcomes[0][1]
    assert outcomes[1][0] == EXIT_OK
    assert outcomes[2][0] == EXIT_OK
