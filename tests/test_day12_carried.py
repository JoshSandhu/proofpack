"""Build day 12 (5 October 2026), lane E item 0: the E11 items the cold lens 4 carried.

* **N5** - ``stats.bootstrap.clustered_number``'s docstring said a refused Number keeps
  "the same ... flags"; the code appends the case-count tier before the refusal branch.
  The docstring now lists what the code inspects; the test below feeds a Number with an
  interval and ``flags=[]`` at four cases and reads the flags back.
* **Carried row 12 (lens 3 mutants L4 / L5 = RG-N5)** - which guidance-map row the long
  form's Guidance status item and T1's model-card note read was not pinned: every
  moved-map test moved all twelve ``FDA_AIDSF_*`` rows, so
  ``AIDSF_STATUS_ANCHOR = "FDA_AIDSF_DATA_MGMT"`` survived the suite. The tests below move
  one row at a time: ``FDA_AIDSF_PERF_VALIDATION`` alone moves the status item and not the
  note; ``FDA_AIDSF_MODEL_CARD`` alone moves the note and not the status item.
* **Carried row 15 (lens 2 FA-N5, mutant L6)** - the case-share and rows-per-case checks of
  ``deff_wilson_route`` swapped changed only ``detail.design_effect.route`` and survived.
  ``deff_wilson_route(600, 5, 300, True)`` fails both bounds (largest case 300 > 0.20 x 600;
  600 rows > 50 x 5 cases), so the order of the two checks decides the answer.

The mutants each test was run against are named in the day-12 build note with the
failing count.
"""

from __future__ import annotations

import pytest

from proofpack.render import anchors
from proofpack.render import html as render_html
from proofpack.render import t1 as render_t1
from proofpack.resources import load_guidance_map
from proofpack.stats.bootstrap import (
    FEWER_THAN_FIVE_CASES,
    clustered_number,
    deff_wilson_route,
)
from proofpack.stats.number import Number
from test_e11_repair2 import LITERAL, MOVED, _status_items

pytestmark = pytest.mark.day12


# ---------------------------------------------------------------------------- N5


def test_n5_refused_number_without_a_tier_gains_one():
    """Literal input: a Wilson Number 0.5 [0.3, 0.7] on 40 rows with ``flags=[]``, four
    cases. Out: no interval, method ``none``, reason ``fewer_than_five_cases`` and the flag
    list ``['not_evaluable_shown_for_transparency']`` (``precision_flags(4)``), not the
    input's empty list."""
    num = Number(est=0.5, ci_lo=0.3, ci_hi=0.7, method="wilson", n=40, k=20, flags=[])
    out = clustered_number(num, 4)
    assert out.ci_lo is None and out.ci_hi is None
    assert out.method == "none"
    assert out.not_estimable_reason == FEWER_THAN_FIVE_CASES
    assert out.flags == ["not_evaluable_shown_for_transparency"]


def test_n5_imprecise_is_dropped_and_a_present_tier_is_kept_on_refusal():
    num = Number(
        est=0.5,
        ci_lo=0.2,
        ci_hi=0.8,
        method="wilson",
        n=40,
        k=20,
        flags=["very_low_precision", "imprecise"],
    )
    out = clustered_number(num, 3)
    assert out.flags == ["very_low_precision"]
    assert out.not_estimable_reason == FEWER_THAN_FIVE_CASES


# ------------------------------------------------------------- carried row 12


def _one_row_moved(internal_id: str) -> list[dict[str, str]]:
    rows = [dict(r) for r in load_guidance_map()]
    hits = [r for r in rows if r["internal_id"] == internal_id]
    assert len(hits) == 1, internal_id
    hits[0]["version_date"] = "2025-02-03"
    return rows


@pytest.fixture(scope="module")
def synthetic():
    from ap4_docx import synthetic_document

    return synthetic_document()


def test_row12_moving_only_perf_validation_moves_the_status_item_and_not_the_note(
    synthetic, monkeypatch
):
    rows = _one_row_moved("FDA_AIDSF_PERF_VALIDATION")
    monkeypatch.setattr(anchors, "load_guidance_map", lambda: tuple(rows))
    t1 = render_t1.render_t1(synthetic)
    for page in (t1, render_html.render_t8(synthetic)):
        items = _status_items(page)
        assert len(items) == 1
        assert MOVED in items[0] and LITERAL not in items[0]
    assert f"model cards are not required per {LITERAL}" in t1
    assert f"model cards are not required per {MOVED}" not in t1


def test_row12_moving_only_model_card_moves_the_note_and_not_the_status_item(
    synthetic, monkeypatch
):
    rows = _one_row_moved("FDA_AIDSF_MODEL_CARD")
    monkeypatch.setattr(anchors, "load_guidance_map", lambda: tuple(rows))
    t1 = render_t1.render_t1(synthetic)
    for page in (t1, render_html.render_t8(synthetic)):
        items = _status_items(page)
        assert len(items) == 1
        assert LITERAL in items[0] and MOVED not in items[0]
    assert f"model cards are not required per {MOVED}" in t1


def test_row12_the_status_anchor_is_the_t1_title_anchor():
    assert render_html.AIDSF_STATUS_ANCHOR == "FDA_AIDSF_PERF_VALIDATION"
    assert render_t1.T1_TITLE_ANCHOR == render_html.AIDSF_STATUS_ANCHOR
    assert render_t1.MODEL_CARD_ANCHOR == "FDA_AIDSF_MODEL_CARD"


# ------------------------------------------------------------- carried row 15


def test_row15_a_shape_outside_both_bounds_routes_by_the_case_share_first():
    assert deff_wilson_route(600, 5, 300, True) == "case_share_above_grid"


@pytest.mark.parametrize(
    ("args", "route"),
    [
        ((600, 5, 100, True), "rows_per_case_above_grid"),  # share 1/6, 120 rows per case
        ((200, 10, 100, True), "case_share_above_grid"),  # share 1/2, 20 rows per case
        ((200, 10, 20, True), "wilson_deff"),
        ((200, 4, 50, True), "below_coverage_bar"),
        ((200, 10, 20, False), "not_estimable"),
    ],
)
def test_row15_each_route_on_one_shape(args, route):
    assert deff_wilson_route(*args) == route
