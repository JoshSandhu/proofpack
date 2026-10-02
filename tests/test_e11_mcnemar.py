"""Build day 11 (E11) item 3, DEC-70 (d): Table T2-3 gains per-metric discordant counts and
McNemar on the Sensitivity and Specificity rows, beside the Accuracy row as built.

**This item touches a statistical gate** (a new test statistic on a printed row): DEC-12 (i)
asks for its own fresh-attack lens before it counts as done.

* The counts are the paired cells the Newcombe interval of the same row conditions on:
  ``b`` = ``g`` (prior correct, new wrong), ``c`` = ``f`` (new correct, prior wrong), among
  the reference-positive pairs for sensitivity and the reference-negative pairs for
  specificity (``stats.comparison._mcnemar_by_metric``, through the existing
  :func:`proofpack.stats.comparison.mcnemar`; no new formula).
* **Oracle**: ``statsmodels.stats.contingency_tables.mcnemar`` - ``exact=True`` and
  ``exact=False, correction=True`` - to 1e-9 on F5's two sub-tables. The literal counts,
  read here from the two committed CSVs with the threshold ``>= 0.5`` and no engine code:
  sensitivity ``e 40, f 1, g 5, h 4`` (50 reference-positive pairs); specificity
  ``e 40, f 1, g 5, h 4`` (50 reference-negative pairs); accuracy ``e 80, f 2, g 10, h 8``.
  F5's two sub-tables are equal, so a sensitivity / specificity swap is invisible on F5: the
  constructed pair below has ``Se b 7, c 2`` and ``Sp b 1, c 4``.
* The exact / corrected threshold: ``b + c = 24`` is exact, ``25`` corrected, on the
  sensitivity row.
* Row 147 (lens 3 FA-N1, block D's shape): every T2-3 row's Margin cell holds exactly its
  own criterion ids (a subgroup-scoped criterion is not on the overall row; an op1 criterion
  is not on op2's row) and no ``not_assessable`` line carries the record string.
"""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from conftest import confirmed_mapping, ephemeral_registry
from proofpack.cli import main
from proofpack.errors import EXIT_OK, EXIT_WARNINGS
from proofpack.render import t2 as render_t2
from proofpack.stats.comparison import EXACT_BELOW, VersionArrays, compare_versions, mcnemar
from test_e10_compare_cli import _home

pytestmark = pytest.mark.day11

REPO = Path(__file__).resolve().parent.parent
F5 = REPO / "tests" / "fixtures" / "f5"
PAIRED = "paired_difference_vs_prior"
#: F5's literal paired cells (e both correct, f new only, g prior only, h neither)
F5_CELLS = {
    "sensitivity": (40, 1, 5, 4),
    "specificity": (40, 1, 5, 4),
    "accuracy": (80, 2, 10, 8),
}


def _f5_cells_from_csv() -> dict[str, tuple[int, int, int, int]]:
    """The paired cells by hand from the two CSVs (no engine code)."""

    def read(name):
        with (F5 / name).open(encoding="utf-8", newline="") as fh:
            return {r["row_id"]: r for r in csv.DictReader(fh)}

    new, prior = read("f5_new.csv"), read("f5_prior.csv")
    out = {}
    for metric in ("sensitivity", "specificity", "accuracy"):
        e = f = g = h = 0
        for rid, r in new.items():
            y = r["y_true"] == "1"
            if (metric == "sensitivity" and not y) or (metric == "specificity" and y):
                continue
            cn = (float(r["score"]) >= 0.5) == y
            cp = (float(prior[rid]["score"]) >= 0.5) == y
            e += cn and cp
            f += cn and not cp
            g += cp and not cn
            h += not cn and not cp
        out[metric] = (e, f, g, h)
    return out


def test_f5_cells_by_hand_are_the_literal_counts():
    assert _f5_cells_from_csv() == F5_CELLS


@pytest.mark.parametrize("metric", ["sensitivity", "specificity", "accuracy"])
def test_engine_mcnemar_equals_statsmodels_on_f5_sub_tables(metric):
    from statsmodels.stats.contingency_tables import mcnemar as sm_mcnemar

    e, f, g, h = F5_CELLS[metric]
    b, c = g, f  # b prior correct only, c new correct only
    table = [[e, b], [c, h]]
    exact = mcnemar(b, c)
    assert exact.method == "exact_mcnemar" and b + c < EXACT_BELOW
    ref = sm_mcnemar(table, exact=True)
    assert abs(exact.p - float(ref.pvalue)) <= 1e-9
    corrected = mcnemar(b, c, exact=False)
    ref_cc = sm_mcnemar(table, exact=False, correction=True)
    assert corrected.method == "cc_mcnemar"
    assert abs(corrected.statistic - float(ref_cc.statistic)) <= 1e-9
    assert abs(corrected.p - float(ref_cc.pvalue)) <= 1e-9
    if metric != "accuracy":
        # 2 * P(X <= 1 | Bin(6, 1/2)) = 2 * 7 / 64
        assert abs(exact.p - 14 / 64) <= 1e-15


@pytest.fixture(scope="module")
def f5_document(tmp_path_factory) -> dict[str, Any]:
    from test_e10_t2 import compare_document

    base = tmp_path_factory.mktemp("e11mc")
    for name in ("f5_new.csv", "f5_prior.csv", "criteria.yaml"):
        shutil.copy(F5 / name, base / name)
    return compare_document(
        base, base / "f5_new.csv", base / "f5_prior.csv", base / "criteria.yaml"
    )


def test_f5_compare_carries_the_se_sp_entries_with_the_literal_counts(f5_document):
    by_metric = f5_document["comparison"]["mcnemar_by_metric"]
    assert set(by_metric) == {"op1"} and set(by_metric["op1"]) == {"sensitivity", "specificity"}
    for metric in ("sensitivity", "specificity"):
        entry = by_metric["op1"][metric]
        e, f, g, h = F5_CELLS[metric]
        assert (entry["b"], entry["c"], entry["n_discordant"]) == (g, f, f + g)
        assert entry["method"] == "exact_mcnemar" and entry["statistic"] is None
        assert abs(entry["p"] - 14 / 64) <= 1e-15
        # the same cells the row's Newcombe paired difference conditions on
        diff = f5_document["comparison"]["differences"]["op1"][metric]["number"]
        assert diff["n"] == e + f + g + h and abs(diff["est"] - (f - g) / diff["n"]) <= 1e-15
    acc = f5_document["comparison"]["mcnemar"]["op1"]
    assert (acc["b"], acc["c"]) == (10, 2)


def _arrays(cells: dict[str, tuple[int, int, int, int]]) -> tuple[VersionArrays, VersionArrays]:
    """Pairs with the given (e, f, g, h) on the positives ("se") and negatives ("sp")."""
    pos, pn, pp = [], [], []
    for metric, (e, f, g, h) in cells.items():
        y = metric == "se"
        for n_rows, new_ok, prior_ok in ((e, 1, 1), (f, 1, 0), (g, 0, 1), (h, 0, 0)):
            for _ in range(n_rows):
                pos.append(y)
                pn.append(y if new_ok else not y)
                pp.append(y if prior_ok else not y)
    pos_a = np.array(pos)
    new = VersionArrays(pos_a, None, None, {"op1": np.array(pn)})
    prior = VersionArrays(pos_a.copy(), None, None, {"op1": np.array(pp)})
    return new, prior


def _block(cells):
    from proofpack.stats.comparison import Join

    new, prior = _arrays(cells)
    n = new.n
    join = Join(np.arange(n), np.arange(n), n, 0, 0, 0)
    return compare_versions(new, prior, paired=True, join=join, ops=["op1"], probability=False)


def test_sensitivity_and_specificity_entries_are_their_own_and_b_is_prior_only():
    block = _block({"se": (20, 2, 7, 3), "sp": (25, 4, 1, 2)})
    se = block["mcnemar_by_metric"]["op1"]["sensitivity"]
    sp = block["mcnemar_by_metric"]["op1"]["specificity"]
    assert (se["b"], se["c"]) == (7, 2) and (sp["b"], sp["c"]) == (1, 4)
    assert block["mcnemar"]["op1"]["b"] == 8 and block["mcnemar"]["op1"]["c"] == 6
    from statsmodels.stats.contingency_tables import mcnemar as sm_mcnemar

    assert abs(se["p"] - float(sm_mcnemar([[20, 7], [2, 3]], exact=True).pvalue)) <= 1e-9
    assert abs(sp["p"] - float(sm_mcnemar([[25, 1], [4, 2]], exact=True).pvalue)) <= 1e-9


@pytest.mark.parametrize("b, c, method", [(16, 8, "exact_mcnemar"), (17, 8, "cc_mcnemar")])
def test_the_exact_route_below_25_discordant_pairs_and_corrected_from_25(b, c, method):
    from statsmodels.stats.contingency_tables import mcnemar as sm_mcnemar

    block = _block({"se": (30, c, b, 5), "sp": (30, 1, 1, 5)})
    se = block["mcnemar_by_metric"]["op1"]["sensitivity"]
    assert se["method"] == method and se["n_discordant"] == b + c
    ref = sm_mcnemar([[30, b], [c, 5]], exact=method == "exact_mcnemar", correction=True)
    assert abs(se["p"] - float(ref.pvalue)) <= 1e-9
    if method == "cc_mcnemar":
        assert abs(se["statistic"] - (abs(b - c) - 1) ** 2 / (b + c)) <= 1e-12


def test_unpaired_comparison_has_no_per_metric_mcnemar():
    new, prior = _arrays({"se": (5, 1, 1, 1), "sp": (5, 1, 1, 1)})
    block = compare_versions(new, prior, paired=False, join=None, ops=["op1"], probability=False)
    assert block["mcnemar"] is None and block["mcnemar_by_metric"] is None


# ------------------------------------------------------------------ the page


def _write_pair(work: Path, cells: dict[str, tuple[int, int, int, int]]) -> tuple[Path, Path]:
    rows_new, rows_prior = [], []
    i = 0
    for metric, (e, f, g, h) in cells.items():
        y = 1 if metric == "se" else 0
        for n_rows, new_ok, prior_ok in ((e, 1, 1), (f, 1, 0), (g, 0, 1), (h, 0, 0)):
            for _ in range(n_rows):

                def score(ok, k=i, y=y):
                    hi = 0.9 - (k % 7) / 100
                    lo = 0.1 + (k % 7) / 100
                    return hi if (y == 1) == bool(ok) else lo

                sex = "F" if i % 2 else "M"
                rows_new.append((f"r{i:03d}", y, f"{score(new_ok):.2f}", sex))
                rows_prior.append((f"r{i:03d}", y, f"{score(prior_ok):.2f}", sex))
                i += 1
    paths = []
    for name, rows in (("new.csv", rows_new), ("prior.csv", rows_prior)):
        path = work / name
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["row_id", "y_true", "score", "sex"])
            w.writerows(rows)
        paths.append(path)
    return paths[0], paths[1]


def _criteria(criteria: list[dict[str, Any]], *, ops=None) -> dict[str, Any]:
    crit = yaml.safe_load((F5 / "criteria.yaml").read_text(encoding="utf-8"))
    crit["criteria"] = criteria
    if ops is not None:
        crit["operating_points"] = ops
    return crit


def _paired(cid, metric, op="op1", scope="overall", value=-0.5):
    return {
        "id": cid,
        "metric": metric,
        "type": PAIRED,
        "operating_point": op,
        "scope": scope,
        "statistic": "ci_lower_bound",
        "comparator": ">=",
        "value": value,
        "author": "E11 item 3",
        "date": "2026-10-02",
        "justification": "placement",
    }


def _compare_page(tmp_path, monkeypatch, new, prior, crit, *flags) -> tuple[dict, str]:
    _home(tmp_path, monkeypatch)
    yml = tmp_path / "criteria.yaml"
    yml.write_text(yaml.safe_dump(crit, sort_keys=False), encoding="utf-8")
    confirmed_mapping(new)
    out = tmp_path / "pack"
    argv = ["compare", "--input", str(new), "--prior", str(prior), "--criteria", str(yml)]
    rc = main([*argv, "--out", str(out), "--offline", *flags], registry=ephemeral_registry())
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    return doc, (out / "T2.html").read_text(encoding="utf-8")


def _t2_3_rows(page: str) -> dict[tuple[str, str], list[str]]:
    table = re.search(r'<table class="comparison">(.*?)</table>', page, re.S).group(1)
    rows = {}
    for metric, op, body in re.findall(
        r'<tr data-metric="([a-z]+)"(?: data-op="([^"]+)")?>(.*?)</tr>', table, re.S
    ):
        rows[(metric, op)] = re.findall(r"<td[^>]*>(.*?)</td>", body, re.S)
    return rows


def test_the_constructed_pair_prints_its_own_discordants_on_each_row(tmp_path, monkeypatch):
    work = tmp_path / "in"
    work.mkdir()
    new, prior = _write_pair(work, {"se": (20, 2, 7, 3), "sp": (25, 4, 1, 2)})
    doc, page = _compare_page(tmp_path, monkeypatch, new, prior, _criteria([]))
    rows = _t2_3_rows(page)
    plain = {k: [html.unescape(re.sub(r"<[^>]+>", "", c)) for c in v] for k, v in rows.items()}
    se = doc["comparison"]["mcnemar_by_metric"]["op1"]["sensitivity"]
    sp = doc["comparison"]["mcnemar_by_metric"]["op1"]["specificity"]
    assert (se["b"], se["c"], sp["b"], sp["c"]) == (7, 2, 1, 4)
    assert plain[("sensitivity", "op1")][4:6] == ["7 / 2", f"{se['p']:.3f} (exact)"]
    assert plain[("specificity", "op1")][4:6] == ["1 / 4", f"{sp['p']:.3f} (exact)"]
    assert plain[("accuracy", "op1")][4:6][0] == "8 / 6"
    for key in (("auroc", ""), ("brier", ""), ("slope", "")):
        if key in plain:
            assert plain[key][4:6] == ["— / —", "— (—)"], key


def test_row_147_each_t2_3_row_holds_exactly_its_own_criterion_ids(tmp_path, monkeypatch):
    """Lens 3's block D shape: a subgroup-scoped, an op1 and an op2 paired criterion."""
    ops = [
        {
            "id": "op1",
            "threshold": 0.5,
            "rule": ">=",
            "provenance": "prespecified_sap",
            "source": "F5",
        },
        {
            "id": "op2",
            "threshold": 0.6,
            "rule": ">=",
            "provenance": "prespecified_sap",
            "source": "F5",
        },
    ]
    crit = _criteria(
        [
            _paired("Cacc1", "accuracy", "op1"),
            _paired("Cacc2", "accuracy", "op2", value=0.5),
            _paired("CseF", "sensitivity", "op1", {"attribute": "sex", "level": "F"}),
            _paired("Cse1", "sensitivity", "op1"),
            _paired("Csp2", "specificity", "op2"),
        ],
        ops=ops,
    )
    work = tmp_path / "in"
    work.mkdir()
    for name in ("f5_new.csv", "f5_prior.csv"):
        shutil.copy(F5 / name, work / name)
    doc, page = _compare_page(
        tmp_path, monkeypatch, work / "f5_new.csv", work / "f5_prior.csv", crit
    )
    rows = _t2_3_rows(page)
    expected = {
        ("sensitivity", "op1"): ["Cse1"],
        ("specificity", "op1"): [],
        ("accuracy", "op1"): ["Cacc1"],
        ("sensitivity", "op2"): [],
        ("specificity", "op2"): ["Csp2"],
        ("accuracy", "op2"): ["Cacc2"],
    }
    for key, ids in expected.items():
        margin = rows[key][-2]
        got = re.findall(r'<span class="customer-text inline">([^<]+)</span> \(row', margin)
        assert got == ids, (key, got)
    statuses = {r["criterion_id"]: r["status"] for r in doc["criteria_results"]}
    assert statuses["Cacc2"] == "not_met"
    acc2_status = rows[("accuracy", "op2")][-1]
    assert acc2_status.count(render_t2.NOT_MET_RECORD) == 1


def test_row_147_no_not_assessable_line_carries_the_record_string(tmp_path, monkeypatch):
    """The unpaired path: every paired criterion is not_assessable (not_like_for_like)."""
    crit = _criteria([_paired("Cacc1", "accuracy"), _paired("Cse1", "sensitivity")])
    work = tmp_path / "in"
    work.mkdir()
    shutil.copy(F5 / "f5_new.csv", work / "f5_new.csv")
    lines = (F5 / "f5_prior.csv").read_text(encoding="utf-8").splitlines()
    (work / "f5_prior.csv").write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    doc, page = _compare_page(
        tmp_path,
        monkeypatch,
        work / "f5_new.csv",
        work / "f5_prior.csv",
        crit,
        "--allow-unpaired",
    )
    assert {r["status"] for r in doc["criteria_results"]} == {"not_assessable"}
    rows = _t2_3_rows(page)
    status_cells = [rows[("accuracy", "op1")][-1], rows[("sensitivity", "op1")][-1]]
    for cell in status_cells:
        assert "not assessable" in cell
        assert render_t2.NOT_MET_RECORD not in html.unescape(cell), cell
