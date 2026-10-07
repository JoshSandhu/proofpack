"""Build day 14 (E14 item 4; LW-01 user review note 17): the all-high map prompt
``every role is high (N columns): [a]ccept / [q]uit?`` keeps its answers - ``a`` or
``accept`` accepts, ``q``, ``quit`` or ``abort`` halts (DEC-28 and the repair-2 / lens-3
history: ``n``, ``e``, ``x`` and the empty answer must not accept) - and its re-prompt now
says exactly what to type. At 3ee5601 the re-prompt read ``answer a or q``; in the LW-01
walk-through (Windows 11, Python 3.12.10, the site's synthetic cohort) ``y`` re-prompted
with that line.
"""

from __future__ import annotations

import pytest

from conftest import make_cohort
from proofpack import cli
from proofpack.errors import HaltError
from proofpack.io.mapping import map_headers

pytestmark = pytest.mark.day14


def test_the_reprompt_line_is_pinned():
    assert cli.ALL_HIGH_REPROMPT == "  type a and press Enter to accept, or q to quit"


def test_y_and_the_other_non_answers_reprompt_with_the_new_line_then_a_accepts():
    cols = make_cohort()
    m = map_headers(list(cols), cols)
    assert m.non_high == []
    said: list[str] = []
    seen: list[str] = []
    prompts: list[str] = []
    answers = iter(["y", "yes", "Y", "n", "e", "x", "", "a"])

    def ask(p):
        prompts.append(p)
        seen.append(m.decided_by)
        return next(answers)

    cli._confirm_interactive(m, ask=ask, say=said.append)
    assert said == ["  type a and press Enter to accept, or q to quit"] * 7
    # the prompt itself is unchanged
    assert set(prompts) == {f"every role is high ({len(m.roles)} columns): [a]ccept / [q]uit? "}
    assert seen == ["proposed"] * 8 and m.decided_by == "interactive"


def test_y_then_q_halts_and_y_never_accepted():
    cols = make_cohort()
    m = map_headers(list(cols), cols)
    said: list[str] = []
    answers = iter(["y", "q"])
    with pytest.raises(HaltError) as exc:
        cli._confirm_interactive(m, ask=lambda p: next(answers), say=said.append)
    assert exc.value.code == "H07"
    assert said == [cli.ALL_HIGH_REPROMPT]
    assert m.decided_by == "proposed"


def test_the_answer_tuples_are_unchanged():
    assert cli.ACCEPT_ANSWERS == ("a", "accept")
    assert cli.QUIT_ANSWERS == ("q", "quit", "abort")
    for word in ("y", "yes", "n", "no", "e", "x", ""):
        assert word not in cli.ACCEPT_ANSWERS and word not in cli.QUIT_ANSWERS
