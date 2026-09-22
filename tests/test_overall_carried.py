"""Build day 8 (E8 item 1): the ``overall`` block on a clustered plan and on a y_pred-only
table (E7 cut 1, carried item 42).

Oracles, none of them through the code under test:

* the clustered overall sensitivity's ``est`` equals the pooled ``k/n`` counted here by
  hand from the fixture columns, and its interval equals what ``proportion_ci`` (the
  subgroup rows' cluster-bootstrap route) gives on the same rows, same case ids, same
  seed, same B and the same cell key - the function the block claims to reuse;
* the y_pred-only two-by-two equals scikit-learn's ``confusion_matrix`` on the fixture;
* a one-level attribute puts every analysed row in one subgroup stratum, and that
  stratum's rendered Number carries the same ``est``, ``n``, ``k``, ``n_cases`` and
  method as the overall cell (the interval differs only by the bootstrap stream, which
  is seeded from the cell key);
* ``json.dumps(block, allow_nan=False)`` succeeds on both blocks;
* a criterion at ``scope: overall`` on a clustered run is compared, never
  ``overall_not_computed``.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np
import pytest
from sklearn.metrics import confusion_matrix

from conftest import ephemeral_registry, make_cohort, make_criteria
from proofpack.cli import main
from proofpack.errors import EXIT_OK, EXIT_WARNINGS
from proofpack.io.declare import validate_dict
from proofpack.resources import load_json_schema
from proofpack.run import CLUSTERED_REFUSED_2X2, NO_SCORE_COLUMN
from proofpack.stats.bootstrap import plan_clustering, policy_from_declarations, proportion_ci
from test_run_cli import _own_home, _prepare

pytestmark = pytest.mark.day8


def _clustered_cols(n: int = 200) -> dict[str, list[Any]]:
    cols = make_cohort(n=n, with_case_id=True)
    cols["case_id"] = [f"c{i // 2:06d}" for i in range(n)]
    return cols


def _clustered_crit(criteria=None) -> dict[str, Any]:
    return make_criteria(
        criteria=criteria if criteria is not None else [],
        clustering={"unit": "case_id", "declared_by": "test"},
        fairness=None,
    )


def _run_doc(tmp_path: Path, monkeypatch, cols, crit) -> dict[str, Any]:
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path, cols, crit)
    out = tmp_path / "pack"
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--offline"],
        registry=ephemeral_registry(),
    )
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    return json.loads((out / "run.json").read_text(encoding="utf-8"))


def _hand_sensitivity(cols, threshold=0.5) -> tuple[int, int, np.ndarray, list[str]]:
    """Pooled k/n for sensitivity at op1 from the fixture columns, by hand."""
    pos_rows = [i for i, v in enumerate(cols["y_true"]) if v == "1"]
    called = np.array([cols["score"][i] >= threshold for i in pos_rows], dtype=bool)
    ids = [cols["case_id"][i] for i in pos_rows]
    return int(called.sum()), len(pos_rows), called, ids


def test_the_clustered_overall_sensitivity_is_the_pooled_k_over_n_and_the_subgroup_route_interval(
    tmp_path: Path, monkeypatch
):
    cols = _clustered_cols()
    crit = _clustered_crit()
    doc = _run_doc(tmp_path, monkeypatch, cols, crit)
    num = doc["overall"]["op1"]["sensitivity"]
    k, n, indicator, ids = _hand_sensitivity(cols)
    assert (num["k"], num["n"]) == (k, n)
    assert num["est"] == pytest.approx(k / n, abs=1e-15)
    assert num["method"] == "cluster_bootstrap_percentile"
    assert "wilson_refused_clustered" in num["flags"]
    assert num["n_cases"] == len(set(ids))
    # the subgroup route on the same rows: proportion_ci with the same policy, plan,
    # case ids and cell key gives the same interval (same seed, same B)
    decl = validate_dict(crit)
    policy = policy_from_declarations(decl)
    all_ids = np.asarray(cols["case_id"], dtype=object)
    plan = plan_clustering("case_id", all_ids, len(cols["case_id"]))
    cell = proportion_ci(
        indicator,
        cell_key=json.dumps(["overall", "op1", "sensitivity"]),
        policy=policy,
        plan=plan,
        cluster_ids=np.asarray(ids, dtype=object),
    )
    assert (cell.number.ci_lo, cell.number.ci_hi) == (num["ci_lo"], num["ci_hi"])
    assert cell.number.est == num["est"]
    assert policy.n_resamples == 200 and policy.seed == 20240101
    # the same interval is NOT the i.i.d. Wilson interval (the analytic method was refused)
    from proofpack.stats.proportions import proportion

    wilson = proportion(k, n)
    assert (wilson.ci_lo, wilson.ci_hi) != (num["ci_lo"], num["ci_hi"])


def test_the_two_by_two_only_metrics_are_typed_clustered_data_analytic_ci_invalid(
    tmp_path: Path, monkeypatch
):
    doc = _run_doc(tmp_path, monkeypatch, _clustered_cols(), _clustered_crit())
    block = doc["overall"]["op1"]
    assert set(CLUSTERED_REFUSED_2X2) == {
        "youden",
        "balanced_accuracy",
        "lr_pos",
        "lr_neg",
        "dor",
        "f1",
        "mcc",
    }
    for key in CLUSTERED_REFUSED_2X2:
        num = block[key]
        assert num["not_estimable_reason"] == "clustered_data_analytic_ci_invalid", key
        assert num["ci_lo"] is None and num["ci_hi"] is None and num["method"] == "none"
    # the point estimates are the two-by-two functions of the four counts
    t = block["two_by_two"]
    tp, fn, fp, tn = t["tp"], t["fn"], t["fp"], t["tn"]
    assert block["f1"]["est"] == pytest.approx(2 * tp / (2 * tp + fp + fn))
    se, sp = tp / (tp + fn), tn / (tn + fp)
    assert block["youden"]["est"] == pytest.approx(se + sp - 1)
    assert block["balanced_accuracy"]["est"] == pytest.approx((se + sp) / 2)
    tf = doc["overall"]["threshold_free"]
    assert tf["auroc"]["method"] == "cluster_bootstrap_percentile"
    assert "delong_refused_clustered" in tf["auroc"]["flags"]
    assert tf["auroc_wald"] is None and tf["roc"][0] == [0.0, 0.0, None]
    assert tf["prevalence"]["method"] == "cluster_bootstrap_percentile"
    assert tf["prevalence"] == block["prevalence"]
    json.dumps(doc["overall"], allow_nan=False)
    jsonschema.validate(doc, load_json_schema("output_schema_v1.json"))


def test_a_one_level_attribute_stratum_carries_the_same_counts_as_the_overall_cell(
    tmp_path: Path, monkeypatch
):
    cols = _clustered_cols()
    cols["site"] = ["S1"] * len(cols["site"])
    doc = _run_doc(tmp_path, monkeypatch, cols, _clustered_crit())
    [row] = [r for r in doc["subgroups"] if r["attribute"] == "site"]
    assert row["level"] == "S1" and row["n"] == doc["flow"]["analysed"]
    for metric in ("sensitivity", "specificity", "ppv", "npv", "accuracy"):
        cell = row["metrics"]["op1"][metric]["number"]
        num = doc["overall"]["op1"][metric]
        for key in ("est", "n", "k", "n_cases", "method"):
            assert cell[key] == num[key], (metric, key)
        assert cell["method"] == "cluster_bootstrap_percentile"
        assert row["metrics"]["op1"][metric]["analytic_status"] == "refused_clustered"
    assert row["metrics"]["op1"]["two_by_two"] == doc["overall"]["op1"]["two_by_two"]
    auroc = row["metrics"]["auroc"]["number"]
    tf = doc["overall"]["threshold_free"]["auroc"]
    assert (auroc["est"], auroc["n_pos"], auroc["n_neg"], auroc["n_cases"]) == (
        tf["est"],
        tf["n_pos"],
        tf["n_neg"],
        tf["n_cases"],
    )


def test_a_criterion_at_scope_overall_on_a_clustered_run_is_compared(tmp_path: Path, monkeypatch):
    crit = _clustered_crit(
        criteria=[
            {
                "id": "C_over",
                "metric": "sensitivity",
                "operating_point": "op1",
                "scope": "overall",
                "statistic": "ci_lower_bound",
                "comparator": ">=",
                "value": 0.5,
                "author": "A",
                "date": "2026-01-01",
                "justification": "j",
            },
            {
                "id": "C_auroc",
                "metric": "auroc",
                "scope": "overall",
                "statistic": "ci_lower_bound",
                "comparator": ">=",
                "value": 0.5,
                "author": "A",
                "date": "2026-01-01",
                "justification": "j",
            },
            {
                "id": "C_f1",
                "metric": "f1",
                "operating_point": "op1",
                "scope": "overall",
                "statistic": "point_estimate",
                "comparator": ">=",
                "value": 0.5,
                "author": "A",
                "date": "2026-01-01",
                "justification": "j",
            },
        ]
    )
    doc = _run_doc(tmp_path, monkeypatch, _clustered_cols(), crit)
    rows = {r["criterion_id"]: r for r in doc["criteria_results"]}
    assert rows["C_over"]["status"] in ("met", "not_met")
    assert rows["C_over"]["reason_code"] == "statistic_compared"
    assert rows["C_over"]["method"] == "cluster_bootstrap_percentile"
    assert rows["C_over"]["compared_value"] == doc["overall"]["op1"]["sensitivity"]["ci_lo"]
    assert rows["C_over"]["detail"] == {"attainability_not_computed": "method_not_wilson"}
    assert rows["C_auroc"]["status"] in ("met", "not_met")
    f1 = rows["C_f1"]
    assert (f1["status"], f1["reason_code"]) == ("not_assessable", "no_interval")
    assert rows["C_f1"]["detail"]["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
    assert not any(r["reason_code"] == "overall_not_computed" for r in doc["criteria_results"])


def test_the_y_pred_only_overall_two_by_two_equals_sklearn_and_the_threshold_free_block_is_typed(
    tmp_path: Path, monkeypatch
):
    cols = make_cohort(n=200, with_y_pred=True)
    del cols["score"]
    crit = make_criteria(
        criteria=[
            {
                "id": "C_over",
                "metric": "sensitivity",
                "operating_point": "op1",
                "scope": "overall",
                "statistic": "ci_lower_bound",
                "comparator": ">=",
                "value": 0.5,
                "author": "A",
                "date": "2026-01-01",
                "justification": "j",
            }
        ],
        fairness=None,
    )
    doc = _run_doc(tmp_path, monkeypatch, cols, crit)
    overall = doc["overall"]
    y_true = np.array([v == "1" for v in cols["y_true"]])
    y_pred = np.array([v == "1" for v in cols["y_pred"]])
    cm = confusion_matrix(y_true, y_pred, labels=[False, True])
    assert overall["op1"]["two_by_two"] == {
        "tn": int(cm[0, 0]),
        "fp": int(cm[0, 1]),
        "fn": int(cm[1, 0]),
        "tp": int(cm[1, 1]),
    }
    se = overall["op1"]["sensitivity"]
    assert se["method"] == "wilson" and se["k"] == int(cm[1, 1]) and se["n"] == int(cm[1].sum())
    tf = overall["threshold_free"]
    assert tf["suppressed_reason"] == NO_SCORE_COLUMN == "no_score_column"
    assert tf["auroc"]["not_estimable_reason"] == "not_computed_this_run"
    assert tf["auroc"]["est"] is None and tf["roc"] == [] and tf["auroc_wald"] is None
    assert tf["prevalence"]["k"] == int(y_true.sum()) and tf["prevalence"]["n"] == 200
    [row] = doc["criteria_results"]
    assert row["status"] in ("met", "not_met") and row["method"] == "wilson"
    assert row["attainable_at_n"] is not None
    # the subgroup rows on the same table agree with the overall cell (carried 42's asymmetry)
    total_tp = sum(
        r["metrics"]["op1"]["two_by_two"]["tp"] for r in doc["subgroups"] if r["attribute"] == "sex"
    )
    assert total_tp == overall["op1"]["two_by_two"]["tp"]
    assert doc["calibration"] is None
    json.dumps(overall, allow_nan=False)
    jsonschema.validate(doc, load_json_schema("output_schema_v1.json"))


def test_a_y_pred_only_clustered_table_routes_the_overall_through_the_cluster_bootstrap(
    tmp_path: Path, monkeypatch
):
    cols = make_cohort(n=200, with_y_pred=True, with_case_id=True)
    cols["case_id"] = [f"c{i // 2:06d}" for i in range(200)]
    del cols["score"]
    doc = _run_doc(tmp_path, monkeypatch, cols, _clustered_crit())
    se = doc["overall"]["op1"]["sensitivity"]
    assert se["method"] == "cluster_bootstrap_percentile" and "n_cases" in se
    assert doc["overall"]["threshold_free"]["suppressed_reason"] == "no_score_column"
    prev = doc["overall"]["threshold_free"]["prevalence"]
    assert prev["method"] == "cluster_bootstrap_percentile"
    jsonschema.validate(doc, load_json_schema("output_schema_v1.json"))


def test_an_iid_run_is_unchanged_by_item_1(tmp_path: Path, monkeypatch):
    """The i.i.d. route still comes from two_by_two_metrics and auroc_number: Wilson,
    DeLong with a secondary interval, F1 analytic_ci_unavailable."""
    doc = _run_doc(tmp_path, monkeypatch, make_cohort(n=200), make_criteria(criteria=[]))
    block = doc["overall"]["op1"]
    assert block["sensitivity"]["method"] == "wilson"
    assert block["f1"]["not_estimable_reason"] == "analytic_ci_unavailable"
    assert doc["overall"]["threshold_free"]["auroc"]["method"].startswith("delong")
    assert doc["overall"]["threshold_free"]["auroc_wald"] is not None
    assert "suppressed_reason" not in doc["overall"]["threshold_free"]


def test_the_assembler_document_carries_the_same_overall_shape(tmp_path: Path):
    from assembler import assemble

    doc = assemble(_clustered_cols(), copy.deepcopy(_clustered_crit()))
    assert doc["overall"]["op1"]["sensitivity"]["method"] == "cluster_bootstrap_percentile"
    jsonschema.validate(doc, load_json_schema("output_schema_v1.json"))
