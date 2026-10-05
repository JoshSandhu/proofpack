"""E11 repair 3 (2 October 2026): DEC-75 (a)-(d) and the cold lens 3 findings on ``3302d59``.

This file collects 20 tests (17 functions, one parametrised four ways). Each of them
except the one control test, ``test_control_an_unclustered_compare_keeps_the_mcnemar_p_value``,
was run against ``45e6761`` (the handoff commit over ``3302d59``; the same ``src``) in a
detached worktree and failed there: ``19 failed, 1 passed``, the pass that control test
(the repair-3 note's figure, re-measured by the cold lens 4 of 2 October 2026, its N4). The
first failing line of each is in the repair-3 note. The names of the new
constants are spelled here, not imported at module level, so that this file imports at
``45e6761``.

* **DEC-75 (a), lens 3 FA-B2.** Under a clustered plan T2-3 prints no McNemar p-value:
  every ``comparison.mcnemar`` and ``mcnemar_by_metric`` entry carries ``b`` and ``c``,
  ``statistic`` and ``p`` ``null``, ``method`` ``none`` and ``not_computed_reason``
  ``mcnemar_assumes_independent_pairs``; T2 prints ``n.e. (<reason>)`` and no
  ``MCNEMAR_RESULT`` sentence. Literal input: the F5 pair with ``case_id`` ten cases of ten
  rows (at ``3302d59``: accuracy ``10 / 2  0.039 (exact)``, Se and Sp ``5 / 1  0.219
  (exact)``).
* **DEC-75 (b), lens 3 FA-B1, FA-N4 / RG-N1, RG-N3.** Every Number with an interval in a
  clustered run or compare carries ``clustered_coverage_not_established`` (``ᵈ``) and the
  tier of its case count; T2 and T8 print the tier legend. Literal inputs: the F5 pair at
  ten cases of ten rows and at five cases of 12 rows beside 40 one-row cases; a 275-row run
  of five cases of 50 rows beside 25 one-row cases; a 300-row run of 150 two-row cases
  nested in every attribute level (so the subgroup differences are computed).
* **DEC-75 (c).** Below five cases a clustered cell prints no interval
  (``fewer_than_five_cases``), the cluster bootstrap included. Literal inputs: four cases of
  three rows (2/1/3/0 successes) and five of three rows; a 120-row run of four cases of 30
  rows; the F5 pair at four cases of 25 rows.
* **DEC-75 (d).** The register row records the 36th Newcombe limit.
* **FA-N2, FA-N3, FA-N6, RG-N2** - four sentences made true.
"""

from __future__ import annotations

import copy
import csv
import html
import re
import shutil
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np
import pytest
import yaml

from ap4_docx import needs_extra
from assembler import assemble
from conftest import make_cohort, make_criteria
from proofpack.render import format as fmt
from proofpack.render import html as render_html
from proofpack.render import t2 as render_t2
from proofpack.render import t7 as render_t7
from proofpack.resources import load_json_schema
from proofpack.stats import bootstrap
from proofpack.stats.bootstrap import auroc_ci, plan_clustering, proportion_ci

pytestmark = pytest.mark.day11

REPO = Path(__file__).resolve().parent.parent
F5 = REPO / "tests" / "fixtures" / "f5"
FLAG = "clustered_coverage_not_established"
FEW = "fewer_than_five_cases"
MCNEMAR_REASON = "mcnemar_assumes_independent_pairs"
TIERS = ("not_evaluable_shown_for_transparency", "very_low_precision")
LEGEND_D = (
    "clustered interval: coverage not established for this cell's case sizes and within-case "
    "correlation (T7 section 6, printed when the run has a clustered interval)"
)


def _numbers(node: Any, path: str = ""):
    """Every Number-shaped dict under ``node`` with its JSON path."""
    if isinstance(node, dict):
        if "method" in node and "est" in node and "flags" in node:
            yield path, node
        for key, value in node.items():
            yield from _numbers(value, f"{path}/{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _numbers(value, f"{path}/{i}")


def _with_interval(doc: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [(p, n) for p, n in _numbers(doc) if n.get("ci_lo") is not None]


def _f5_clustered(base: Path, sizes: list[int] | None) -> dict[str, Any]:
    """The F5 pair with a ``case_id`` column of ``sizes`` (``None``: no clustering) through
    ``assemble_compare`` and ``write_run``, read back (``test_e10_t2.compare_document``)."""
    from test_e10_t2 import compare_document

    base.mkdir(parents=True, exist_ok=True)
    crit = yaml.safe_load((F5 / "criteria.yaml").read_text(encoding="utf-8"))
    if sizes is None:
        for name in ("f5_new.csv", "f5_prior.csv"):
            shutil.copy(F5 / name, base / name)
    else:
        assert sum(sizes) == 100
        case_ids = [f"p{i:03d}" for i, s in enumerate(sizes) for _ in range(s)]
        for name in ("f5_new.csv", "f5_prior.csv"):
            rows = list(csv.DictReader((F5 / name).open(encoding="utf-8")))
            with (base / name).open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=[*rows[0].keys(), "case_id"])
                w.writeheader()
                for r, c in zip(rows, case_ids, strict=True):
                    w.writerow({**r, "case_id": c})
        crit["clustering"] = {"unit": "case_id", "declared_by": "e11 repair 3 test"}
    (base / "criteria.yaml").write_text(yaml.safe_dump(crit, sort_keys=False), encoding="utf-8")
    return compare_document(
        base, base / "f5_new.csv", base / "f5_prior.csv", base / "criteria.yaml"
    )


@pytest.fixture(scope="module")
def cmp10(tmp_path_factory) -> dict[str, Any]:
    return _f5_clustered(tmp_path_factory.mktemp("cmp10"), [10] * 10)


@pytest.fixture(scope="module")
def cmp_lens(tmp_path_factory) -> dict[str, Any]:
    return _f5_clustered(tmp_path_factory.mktemp("cmplens"), [12] * 5 + [1] * 40)


@pytest.fixture(scope="module")
def cmp_plain(tmp_path_factory) -> dict[str, Any]:
    return _f5_clustered(tmp_path_factory.mktemp("cmpplain"), None)


def _run(cols: dict[str, list[Any]]) -> dict[str, Any]:
    crit = make_criteria(criteria=[], clustering={"unit": "case_id", "declared_by": "t"})
    return assemble(cols, copy.deepcopy(crit))


@pytest.fixture(scope="module")
def run_lens() -> dict[str, Any]:
    """Lens 2 / 3's run shape: five cases of 50 rows beside 25 one-row cases (275 rows)."""
    cols = make_cohort(n=275, with_case_id=True)
    sizes = [50] * 5 + [1] * 25
    cols["case_id"] = [f"c{i:03d}" for i, s in enumerate(sizes) for _ in range(s)]
    return _run(cols)


@pytest.fixture(scope="module")
def run_nested() -> dict[str, Any]:
    """150 two-row cases whose two rows share sex, age and site, so no case spans two
    levels of any attribute and the subgroup differences are computed."""
    cols = make_cohort(n=300, with_case_id=True)
    for attr in ("sex", "age", "site"):
        cols[attr] = [cols[attr][i - i % 2] for i in range(300)]
    cols["case_id"] = [f"c{i // 2:04d}" for i in range(300)]
    return _run(cols)


# ------------------------------------------------------------------ DEC-75 (a), FA-B2


def test_dec75a_no_mcnemar_p_value_under_a_clustered_plan_in_run_json(cmp10):
    comparison = cmp10["comparison"]
    assert comparison["clustering_route"] == "declared"
    refused = {"statistic": None, "p": None, "method": "none"}
    assert comparison["mcnemar"]["op1"] == {
        "b": 10,
        "c": 2,
        "n_discordant": 12,
        **refused,
        "not_computed_reason": MCNEMAR_REASON,
    }
    for metric in ("sensitivity", "specificity"):
        assert comparison["mcnemar_by_metric"]["op1"][metric] == {
            "b": 5,
            "c": 1,
            "n_discordant": 6,
            **refused,
            "not_computed_reason": MCNEMAR_REASON,
        }
    jsonschema.validate(cmp10, load_json_schema("output_schema_v1.json"))


def test_dec75a_t2_prints_the_reason_and_no_p_value_and_no_mcnemar_sentence(cmp10):
    page = render_t2.render_t2(cmp10)
    cells = re.findall(r'data-facet="p">([^<]*)</td>', page)
    assert cells == [f"n.e. ({MCNEMAR_REASON})"] * 3
    claims = re.findall(r'<p class="claim"[^>]*>(.*?)</p>', page, re.S)
    assert claims and not [c for c in claims if "McNemar" in c]
    visible = html.unescape(re.sub(r"<[^>]+>", "", page))
    assert "under the new version only (McNemar" not in visible
    assert "on this clustered plan no McNemar test is computed" in visible


def test_dec75a_the_schema_refuses_a_p_value_beside_the_reason_and_a_bare_none():
    schema = load_json_schema("output_schema_v1.json")
    assert "mcnemarEntry" in schema["$defs"]
    sub = {"$defs": schema["$defs"], "$ref": "#/$defs/mcnemarEntry"}
    good = {
        "b": 1,
        "c": 2,
        "n_discordant": 3,
        "statistic": None,
        "p": None,
        "method": "none",
        "not_computed_reason": MCNEMAR_REASON,
    }
    jsonschema.validate(good, sub)
    for bad in (
        {**good, "p": 0.04},
        {**good, "method": "exact_mcnemar"},
        {**good, "not_computed_reason": None},
        {**good, "p": 0.5, "method": "exact_mcnemar", "not_computed_reason": "other"},
    ):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, sub)
    jsonschema.validate(
        {**good, "p": 0.5, "method": "exact_mcnemar", "not_computed_reason": None}, sub
    )


def test_control_an_unclustered_compare_keeps_the_mcnemar_p_value(cmp_plain):
    """Control (passes at ``45e6761`` too, where the key is absent): F5 as committed."""
    entry = cmp_plain["comparison"]["mcnemar"]["op1"]
    assert (entry["b"], entry["c"], entry["p"], entry["method"]) == (
        10,
        2,
        0.03857421875,
        "exact_mcnemar",
    )
    assert entry.get("not_computed_reason") is None
    page = render_t2.render_t2(cmp_plain)
    assert "0.039 (exact)" in page


# ------------------------------------------------------------------ DEC-75 (b), FA-B1


def test_fa_b1_the_t2_3_differences_carry_their_case_count_tier_and_the_mark(cmp10):
    """At ``3302d59`` the six-case sensitivity difference printed ``−8.0 [...]`` bare: its
    flags were ``['newcombe_refused_clustered']``."""
    diffs = cmp10["comparison"]["differences"]["op1"]
    se, acc = diffs["sensitivity"]["number"], diffs["accuracy"]["number"]
    assert (se["method"], se["n_cases"]) == ("cluster_bootstrap_percentile", 6)
    assert se["flags"] == [
        "newcombe_refused_clustered",
        "not_evaluable_shown_for_transparency",
        FLAG,
    ]
    assert acc["n_cases"] == 10 and acc["flags"][-2:] == ["very_low_precision", FLAG]
    page = render_t2.render_t2(cmp10)
    row = re.search(r'<tr data-metric="sensitivity" data-op="op1">(.*?)</tr>', page, re.S)
    delta = re.search(
        r'data-ref="/comparison/differences/op1/sensitivity/number"[^>]*>([^<]*)<', row.group(1)
    )
    assert delta.group(1).endswith("]ᵃᵈ"), delta.group(1)


@pytest.mark.parametrize("which", ["cmp10", "cmp_lens", "run_lens", "run_nested"])
def test_dec75b_every_clustered_interval_carries_the_mark_and_its_case_count_tier(which, request):
    doc = request.getfixturevalue(which)
    assert doc["flow"]["clustered"] is True
    printed = _with_interval(doc)
    assert printed
    bad = []
    for path, num in printed:
        n_cases = num.get("n_cases")
        tiers = [f for f in num["flags"] if f in TIERS]
        ok = (
            FLAG in num["flags"]
            and n_cases is not None
            and n_cases >= 5
            and (n_cases >= 30 or bool(tiers))
            and (n_cases >= 10 or tiers == ["not_evaluable_shown_for_transparency"])
        )
        if not ok:
            bad.append((path, num["method"], n_cases, num["flags"]))
    assert bad == []
    paths = {re.sub(r"/\d+", "/#", p) for p, _ in printed}
    families = {
        "cmp10": ("/comparison/differences/auroc", "/comparison/differences/brier"),
        "cmp_lens": ("/comparison/differences/op1/accuracy",),
        "run_lens": ("/calibration/oe", "/calibration/ipa", "/overall/threshold_free/auroc"),
        "run_nested": ("/diff_vs_reference/", "/diff_vs_complement/", "/metrics/brier"),
    }[which]
    for family in families:
        assert any(family in p for p in paths), (family, sorted(paths)[:20])


def test_dec75b_t2_and_t8_print_the_tier_legend_beside_the_marks(cmp10):
    t2 = html.unescape(render_t2.render_t2(cmp10))
    t8 = html.unescape(render_html.render_t8(cmp10))
    for page in (t2, t8):
        assert "ᵈ" in re.sub(r'<table class="tiers">.*?</table>', "", page, flags=re.S)
        assert f'<th scope="row">ᵈ</th><td>{LEGEND_D}</td>' in page
        assert '<th scope="row">ᵃ</th><td>n < 10: not evaluable' in page
    assert fmt.CLUSTERED_LEGEND_ROW == ("ᵈ", LEGEND_D)


@needs_extra
@pytest.mark.ap4
def test_dec75b_t8_docx_prints_the_tier_legend(cmp10):
    from ap4_docx import cell_texts
    from proofpack.render.docx import render_docx_bytes

    cells = cell_texts(render_docx_bytes(cmp10, "T8"))
    assert LEGEND_D in cells and "ᵈ" in cells


def test_rg_n2_the_legend_row_names_when_t7_prints_section_6(run_lens):
    page = render_t7.render_t7(run_lens)
    assert '<h2 id="t7-s6">6. Coverage of the clustered intervals</h2>' in page
    assert LEGEND_D in html.unescape(page)


# ------------------------------------------------------------------ DEC-75 (c)


def _cell(sizes: list[int], successes: list[int]):
    ids = np.repeat(np.array([f"c{i}" for i in range(len(sizes))], dtype=object), sizes)
    ind = np.concatenate([np.arange(m) < y for m, y in zip(sizes, successes, strict=True)])
    plan = plan_clustering("case_id", ids, ids.shape[0])
    return proportion_ci(ind.astype(bool), cell_key="r3", plan=plan, cluster_ids=ids)


def test_dec75c_four_cases_print_no_interval_and_five_print_one_with_the_mark():
    assert getattr(bootstrap, "MIN_CLUSTERED_CASES", None) == 5
    four = _cell([3] * 4, [2, 1, 3, 0])
    num = four.number
    assert four.detail["design_effect"]["route"] == "below_coverage_bar"
    assert (num.method, num.not_estimable_reason, num.ci_lo, num.ci_hi) == ("none", FEW, None, None)
    assert (num.k, num.n, num.n_cases, num.est) == (6, 12, 4, 0.5)
    assert FLAG not in num.flags and "imprecise" not in num.flags
    assert "not_evaluable_shown_for_transparency" in num.flags
    five = _cell([3] * 5, [2, 1, 3, 0, 2]).number
    assert five.method == "wilson_deff" and five.has_ci and five.flags[-1] == FLAG


def test_dec75c_a_four_case_auroc_and_a_four_case_run_print_no_interval():
    rng = np.random.default_rng(11)
    ids = np.repeat(np.array(["a", "b", "c", "d"], dtype=object), 25)
    pos = rng.random(100) < 0.4
    score = rng.random(100) + pos * 0.5
    plan = plan_clustering("case_id", ids, 100)
    cell = auroc_ci(score, pos, cell_key="r3auroc", plan=plan, cluster_ids=ids)
    assert (cell.number.not_estimable_reason, cell.number.n_cases) == (FEW, 4)
    cols = make_cohort(n=120, with_case_id=True)
    cols["case_id"] = [f"c{i // 30:03d}" for i in range(120)]
    doc = _run(cols)
    assert _with_interval(doc) == []
    assert doc["overall"]["op1"]["accuracy"]["not_estimable_reason"] == FEW
    assert doc["calibration"]["oe"]["number"]["not_estimable_reason"] == FEW


def test_dec75c_a_four_case_compare_prints_no_difference_interval(tmp_path):
    doc = _f5_clustered(tmp_path / "four", [25] * 4)
    assert _with_interval(doc) == []
    diffs = doc["comparison"]["differences"]
    for key in ("sensitivity", "specificity", "accuracy"):
        assert diffs["op1"][key]["number"]["not_estimable_reason"] == FEW, key
    # the AUROC difference is refused before DEC-75 (c) by the class-units rule
    assert diffs["auroc"]["number"]["not_estimable_reason"] in (FEW, "insufficient_clusters")


# ------------------------------------------------------------------ sentences


def test_fa_n6_clustered_t2_sentences_count_rows_not_cases(cmp_lens):
    """At ``3302d59``: "on 100 paired cases" where ``run.json`` had ``n 100, n_cases 45``."""
    page = html.unescape(re.sub(r"<[^>]+>", "", render_t2.render_t2(cmp_lens)))
    assert "paired cases" not in page
    assert "from version 1.2 to 1.3 on 100 paired rows" in page
    assert "cases were correct under the prior version only" not in page


def test_fa_n3_t7_section_6_says_the_engine_estimates_the_design_effect(run_lens):
    page = html.unescape(render_t7.render_t7(run_lens))
    assert "but not its within-case correlation" not in page
    assert "The engine estimates a cell's design effect from its rows" in page


def test_fa_n2_scope_docstring_does_not_say_verbatim():
    import proofpack.scope as scope

    assert "verbatim from D4" not in (scope.__doc__ or "")


def test_dec75d_the_register_row_records_the_36th_newcombe_limit():
    import json

    from proofpack.fixtures import register

    row = next(r for r in register() if r.id == "F5-newcombe-paired")
    for literal in ("35 of its 36", "1 97 1 1", "0.8736", "0.8737", "0.873672", "DEC-75 (d)"):
        assert literal in row.what, literal
    data = json.loads((REPO / "fixtures" / "newcombe1998_paired.json").read_text("utf-8"))
    (excluded,) = data["excluded"]
    assert (excluded["e"], excluded["f"], excluded["g"], excluded["h"]) == (1, 97, 1, 1)
    assert (excluded["printed"], excluded["printed_method8_same_row"]) == (0.8736, 0.8737)
    assert excluded["engine"] == 0.873672


def test_the_t1_ipa_footnote_names_only_the_proportion_tiers_and_the_clustered_mark(run_lens):
    """Repair 3's own sentence check: with the mark on every clustered interval, T1's IPA
    footnote ("the proportion tier applied to the IPA's own interval: it states the
    half-width") would have listed d as a proportion tier. Literal input: the lens-shape run
    with the IPA's flags set to very_low_precision, imprecise and the mark."""
    from proofpack.render import t1 as render_t1

    doc = copy.deepcopy(run_lens)
    doc["calibration"]["ipa"]["number"]["flags"] = ["very_low_precision", "imprecise", FLAG]
    page = render_t1.render_t1(doc)
    assert "The IPA row's tier superscript (ᵇᶜ) is the proportion tier" in page
    assert "(ᵇᶜᵈ)" not in page
    assert "cluster-bootstrap interval and carries the mark ᵈ" in page
