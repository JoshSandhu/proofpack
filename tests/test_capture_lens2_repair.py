"""Capture repair 2 (orchestrator, Tuesday 6 October 2026): blocker B1 of the second cold lens
on the capture commit (``handoffs/2026-10-06_E_capture_lens2_cold.md``).

At 9d285d9 the T12 golden was rendered with no R capture committed, so it held every word of
F13's and F13b's ``[unverified until captured]`` reasons, and the page-wide forbidden-word
scan covered them. The capture commit (97a2ee4) regenerated the golden with the capture
committed; what was left in the absent state compared ``fx.F13_ABSENT`` and ``fx.F13B_ABSENT``
with themselves or checked a prefix, so the lens's three plants ("are committed and F13 is
matched", "is committed and F13b is verified and matched", "the engine is certified and
validated by") passed the full suite at 5154468.

The reasons below are written out here, not read from :mod:`proofpack.fixtures`, so an edit
to either constant fails this file.
"""

from __future__ import annotations

import html
import re

import pytest

import test_t12 as t12t
from proofpack import fixtures as fx
from proofpack.render import t12

pytestmark = pytest.mark.day12

F13_ABSENT_REASON = (
    "[unverified until captured] the pROC capture (fixtures/r/proc_asah.json) and the "
    "engine comparison the r-captures job records beside it "
    "(fixtures/r/f13_engine_comparison.json) are not both committed; the aSAH vectors are "
    "never committed (DEC-77), so F13 is compared inside that job only "
    "(fixtures/r/capture.R, .github/workflows/r-captures.yml; build day 12) "
    "(absent: fixtures/r/proc_asah.json, fixtures/r/f13_engine_comparison.json)"
)
F13B_ABSENT_REASON = (
    "[unverified until captured] the rms::val.prob capture (fixtures/r/rms_val_prob_f4.json) "
    "is not committed; fixtures/r/capture.R and the r-captures workflow (build day 12) "
    "write it"
)


def _rows(report: dict) -> dict[str, dict]:
    return {r["id"]: r for r in report["rows"] if r["id"] in ("F13", "F13b")}


def _page_text(page: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", page)).split())


def test_capture_lens2_b1_absent_reasons_word_for_word_in_the_report(no_r_capture):
    rows = _rows(fx.run_fixtures(doctor=False))
    assert rows["F13"]["status"] == rows["F13b"]["status"] == "no_oracle_recorded"
    assert rows["F13"]["reason"] == F13_ABSENT_REASON
    assert rows["F13b"]["reason"] == F13B_ABSENT_REASON


def test_capture_lens2_b1_absent_reasons_word_for_word_on_the_t12_page(no_r_capture):
    text = _page_text(t12.render_t12(fx.run_fixtures(doctor=False)))
    assert F13_ABSENT_REASON in text
    assert F13B_ABSENT_REASON in text


def test_capture_lens2_b1_no_forbidden_word_on_the_absent_state_page(no_r_capture):
    """The page-wide scan of ``test_t12`` run over the absent-state render: the same result
    as the committed-state page (nothing outside customer text and the verbatim
    disclaimer; inside them only "endorsed" and "qualified")."""
    page = t12.render_t12(fx.run_fixtures(doctor=False))
    outside, inside = t12t.forbidden_hits(page)
    assert outside == []
    assert {w for hit, _ in inside for w in hit} == {"endorsed", "qualified"}
