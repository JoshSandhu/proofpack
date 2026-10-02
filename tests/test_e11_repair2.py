"""E11 repair 2 (2 October 2026): regression tests for the two cold lenses on ``0fa9391``.

Each test below except the one control test was run against ``0fa9391`` in a detached
worktree and failed there; the first failing line of each is in the repair-2 note.

* **FA-B1 / RG-B1 (one cause)** - lens 2 measured ``wilson_deff`` cells inside every
  bound of ``deff_wilson_route`` covering below the DEC-08 bar at the grid's own
  threshold-setting process with no mark on the page. Every clustered proportion that
  prints an interval now carries ``clustered_coverage_not_established``, printed ``ᵈ``
  (DEC-18 (c)). Literal inputs: the lens's shape, five cases of 50 rows beside 25 one-row
  cases (n 275, 30 cases); one cell per route; a run assembled on that shape, whose
  overall accuracy prints ``82.9ᵈ`` in T1's table and ``228/275 (82.9%ᵈ), 95% CI 77.2%
  to 87.4%`` in its sentence.
* **FA-B2** - the long form's Guidance status item and T1's model-card note read the
  AI-DSF qualifier from the guidance map row. Literal input: every ``FDA_AIDSF_*`` row's
  ``version_date`` moved to ``2025-02-03`` (lens FA-B2's edit); T1, T2 and T8 (HTML) and
  T1 and T8 (DOCX) then print no ``January 2025`` and no ``Jan 2025``.
* **FA-N7** - ``doctor`` names only commands this engine's parser has.
"""

from __future__ import annotations

import copy
import html
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from ap4_docx import needs_extra
from assembler import assemble
from conftest import make_cohort, make_criteria
from proofpack.cli import _build_parser, main
from proofpack.errors import EXIT_OK
from proofpack.render import anchors
from proofpack.render import format as fmt
from proofpack.render import html as render_html
from proofpack.render import t1 as render_t1
from proofpack.render import t2 as render_t2
from proofpack.render import t7 as render_t7
from proofpack.resources import load_guidance_map
from proofpack.stats.bootstrap import plan_clustering, proportion_ci
from proofpack.stats.number import FLAGS
from test_e11_aidsf_header import NAME, _Elements

pytestmark = pytest.mark.day11

REPO = Path(__file__).resolve().parent.parent
LENS_SHAPE = [50] * 5 + [1] * 25
LITERAL = "draft guidance (January 2025), not for implementation"
MOVED = "draft guidance (February 2025), not for implementation"
#: ``stats.bootstrap.CLUSTERED_COVERAGE_FLAG``, spelled here so that this file imports at
#: ``0fa9391`` and fails there on assertions (lens 2 RG-N5's trap)
CLUSTERED_COVERAGE_FLAG = "clustered_coverage_not_established"


# ------------------------------------------------------------------ FA-B1 / RG-B1


def _cell(sizes: list[int], successes: list[int]):
    ids = np.repeat(np.array([f"c{i}" for i in range(len(sizes))], dtype=object), sizes)
    ind = np.concatenate([np.arange(m) < y for m, y in zip(sizes, successes, strict=True)]).astype(
        bool
    )
    plan = plan_clustering("case_id", ids, ids.shape[0])
    return proportion_ci(ind, cell_key="r2", plan=plan, cluster_ids=ids)


def test_the_lens_in_route_shape_prints_the_mark():
    """Lens 2's shape (five cases of 50 rows beside 25 one-row cases), 45 successes in
    each large case and 20 of the 25 one-row cases: route ``wilson_deff``, no case-count
    tier (30 cases), and the mark ``ᵈ``. At ``0fa9391`` the flags were
    ``['wilson_refused_clustered']`` and nothing was printed after the interval."""
    cell = _cell(LENS_SHAPE, [45] * 5 + [1] * 20 + [0] * 5)
    num = cell.number
    assert (num.n, num.k, num.n_cases, num.method) == (275, 245, 30, "wilson_deff")
    assert cell.detail["design_effect"]["route"] == "wilson_deff"
    assert num.flags[-1] == CLUSTERED_COVERAGE_FLAG
    assert fmt.tiers(num.as_dict()).endswith("ᵈ")
    assert CLUSTERED_COVERAGE_FLAG in FLAGS
    from proofpack.stats import bootstrap

    assert bootstrap.CLUSTERED_COVERAGE_FLAG == CLUSTERED_COVERAGE_FLAG


@pytest.mark.parametrize(
    ("sizes", "successes", "route", "method"),
    [
        # two to four cases: since E11 repair 3 (DEC-75 (c)) no interval prints there, so
        # the route is tested in tests/test_e11_repair3.py, not here
        # one case of 60 rows beside 39 one-row cases (repair 1's FA shape)
        ([60] + [1] * 39, [54] + [1] * 35 + [0] * 4, "case_share_above_grid", None),
        # five cases of 60 rows
        ([60] * 5, [50, 40, 55, 30, 45], "rows_per_case_above_grid", None),
        # the grid's lowest recorded row's shape: 30 cases of 50 rows
        ([50] * 30, [49] * 25 + [40] * 5, "wilson_deff", "wilson_deff"),
    ],
)
def test_every_clustered_route_that_prints_an_interval_carries_the_mark(
    sizes, successes, route, method
):
    cell = _cell(sizes, successes)
    num = cell.number
    assert cell.detail["design_effect"]["route"] == route
    if method is not None:
        assert num.method == method
    assert num.has_ci
    assert num.flags.count(CLUSTERED_COVERAGE_FLAG) == 1
    assert num.flags[-1] == CLUSTERED_COVERAGE_FLAG


def test_control_a_cell_without_an_interval_and_an_unclustered_cell_carry_no_mark():
    """Control (passes at ``0fa9391`` too): one case of 7 rows with 3 successes prints no
    interval (``insufficient_clusters``), and an unclustered proportion is Wilson."""
    one = _cell([7], [3]).number
    assert (one.method, one.not_estimable_reason) == ("none", "insufficient_clusters")
    assert CLUSTERED_COVERAGE_FLAG not in one.flags
    ind = np.arange(40) % 3 == 0
    plain = proportion_ci(ind, cell_key="plain")
    assert plain.number.method == "wilson"
    assert CLUSTERED_COVERAGE_FLAG not in plain.number.flags


def _lens_shape_run() -> dict:
    cols = make_cohort(n=275, with_case_id=True)
    cols["case_id"] = [f"c{i:03d}" for i, s in enumerate(LENS_SHAPE) for _ in range(s)]
    crit = make_criteria(criteria=[], clustering={"unit": "case_id", "declared_by": "t"})
    return assemble(cols, copy.deepcopy(crit))


def test_a_run_on_the_lens_shape_prints_the_mark_on_t1_and_the_legend_on_t1_and_t7():
    """Lens 2 RG-B1's run: the overall accuracy is ``wilson_deff`` 228/275 [0.7724, 0.874]
    over 30 cases. At ``0fa9391`` T1 printed it with no mark."""
    doc = _lens_shape_run()
    acc = doc["overall"]["op1"]["accuracy"]
    assert (acc["method"], acc["k"], acc["n"], acc["n_cases"]) == ("wilson_deff", 228, 275, 30)
    assert acc["flags"] == ["wilson_refused_clustered", CLUSTERED_COVERAGE_FLAG]
    page = render_t1.render_t1(doc)
    assert 'data-ref="/overall/op1/accuracy" data-kind="proportion" data-facet="est">82.9ᵈ<' in (
        page
    )
    assert "was 228/275 (82.9%ᵈ), 95% CI 77.2% to 87.4%" in page
    # E11 repair 3 (DEC-75 (b)): the row names a clustered interval, not a proportion
    legend = "clustered interval: coverage not established for this cell's case sizes"
    assert legend in html.unescape(page)
    assert legend in html.unescape(render_t7.render_t7(doc))


def test_t7_says_where_the_mark_goes_and_what_a_one_case_cell_prints():
    """Lens 2 FA-N4: the ``wilson_deff`` description said any other clustered proportion
    prints the cluster bootstrap; a one-case cell prints no interval."""
    desc = render_t7.METHOD_DESCRIPTIONS["wilson_deff"]
    assert "any other clustered proportion prints the cluster bootstrap" not in desc
    assert "one case prints no interval" in desc and "insufficient_clusters" in desc
    assert "tier mark ᵈ" in desc


# ------------------------------------------------------------------ FA-B2


def _moved_rows() -> list[dict[str, str]]:
    rows = [dict(r) for r in load_guidance_map()]
    for r in rows:
        if r["internal_id"].startswith("FDA_AIDSF_"):
            r["version_date"] = "2025-02-03"
    return rows


@pytest.fixture
def moved_map(monkeypatch):
    rows = _moved_rows()
    monkeypatch.setattr(anchors, "load_guidance_map", lambda: tuple(rows))
    return rows


@pytest.fixture(scope="module")
def synthetic():
    from ap4_docx import synthetic_document

    return synthetic_document()


def _status_items(page: str) -> list[str]:
    p = _Elements()
    p.feed(page)
    return [text for tag, text, _ in p.closed if tag == "li" and "Guidance status." in text]


def test_the_guidance_status_item_carries_the_literal_qualifier_from_the_map(synthetic):
    """With the committed map, the item carries ``draft guidance (January 2025), not for
    implementation``; at ``0fa9391`` it read ``(January 2025), it is a draft, not for
    implementation``."""
    for page in (render_t1.render_t1(synthetic), render_html.render_t8(synthetic)):
        items = _status_items(page)
        assert len(items) == 1
        assert LITERAL in items[0]
    note = f"Note: model cards are not required per {LITERAL}."
    assert note in render_t1.render_t1(synthetic)


def test_a_moved_map_row_moves_every_month_on_t1_and_t8(synthetic, moved_map):
    for page in (render_t1.render_t1(synthetic), render_html.render_t8(synthetic)):
        assert "January 2025" not in page and "Jan 2025" not in page
        items = _status_items(page)
        assert len(items) == 1 and MOVED in items[0]
    assert f"model cards are not required per {MOVED}" in render_t1.render_t1(synthetic)


def test_a_moved_map_row_moves_every_month_on_t2(tmp_path, moved_map):
    from test_e10_t2 import F5, compare_document

    for name in ("f5_new.csv", "f5_prior.csv", "criteria.yaml"):
        shutil.copy(F5 / name, tmp_path / name)
    doc = compare_document(
        tmp_path, tmp_path / "f5_new.csv", tmp_path / "f5_prior.csv", tmp_path / "criteria.yaml"
    )
    page = render_t2.render_t2(doc)
    assert "January 2025" not in page and "Jan 2025" not in page
    items = _status_items(page)
    assert len(items) == 1 and MOVED in items[0]


@needs_extra
@pytest.mark.ap4
@pytest.mark.parametrize("template_id", ["T1", "T8"])
def test_a_moved_map_row_moves_every_month_in_the_docx(template_id, synthetic, moved_map):
    from ap4_docx import all_text, cell_texts
    from proofpack.render.docx import render_docx_bytes

    data = render_docx_bytes(synthetic, template_id)
    text = all_text(data) + "\n" + "\n".join(cell_texts(data))
    assert "January 2025" not in text and "Jan 2025" not in text
    status = [t for t in text.split("\n") if "Guidance status." in t]
    assert len(status) == 1 and MOVED in status[0]


def test_no_element_naming_the_draft_lacks_the_literal_qualifier(synthetic):
    """The literal rule lens 2 applied (attack 1): every innermost element that names the
    AI-DSF draft, or says ``draft guidance``, carries ``draft guidance (January 2025), not
    for implementation`` itself. Pages: T1 and T8 of the synthetic document."""
    for page in (render_t1.render_t1(synthetic), render_html.render_t8(synthetic)):
        p = _Elements()
        p.feed(page)
        bad = [
            text[:120]
            for tag, text, child_named in p.closed
            if (NAME.search(text) or "draft guidance" in text)
            and not child_named
            and LITERAL not in text
            and tag not in {"html", "body", "main", "section", "div", "ol", "ul", "table"}
        ]
        assert bad == []


# ------------------------------------------------------------------ FA-N7


def test_doctor_names_only_commands_the_parser_has(capsys):
    """At ``0fa9391`` doctor printed ``Next step: proofpack declare --out criteria.yaml``;
    the subcommands are doctor, map, run, compare, fixtures, licence."""
    parser = _build_parser()
    sub = next(a for a in parser._actions if a.dest == "command")
    commands = set(sub.choices)
    assert commands == {"doctor", "map", "run", "compare", "fixtures", "licence"}
    assert main(["doctor", "--offline"]) == EXIT_OK
    out = capsys.readouterr().out
    named = re.findall(r"proofpack (\w+)", out.split("Next step:", 1)[1])
    assert named and set(named) <= commands, named
