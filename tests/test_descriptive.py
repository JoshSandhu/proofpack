"""Day 6 (E6) - ``stats.descriptive``: the flow counts, Table 1 and the missingness table.

Every figure here is a count or a share checked against a direct numpy count on the raw
columns the test built, so the oracle is the construction itself: three rows with a
missing label, two with a missing score and four indeterminate rows give exactly those
flow counts; a column with seven missing tokens (seven different spellings from
``schema_v1.json``'s ``missing_tokens``) counts seven; the levels of every Table 1
attribute sum to 1 within 1e-12 with the Unknown/missing level included; nothing is
rounded and every count is an ``int``.
"""

from __future__ import annotations

import json
from typing import Any

import jsonschema
import numpy as np
import pytest

from conftest import make_cohort, make_criteria
from proofpack.io import schema as schema_mod
from proofpack.io.declare import validate_dict
from proofpack.io.schema import UNKNOWN_LEVEL
from proofpack.resources import load_json_schema
from proofpack.stats.bootstrap import BootstrapPolicy, ClusterPlan
from proofpack.stats.descriptive import (
    flow_block,
    missingness_block,
    table1_block,
    table1_levels,
)
from proofpack.stats.subgroups import subgroup_analysis

pytestmark = pytest.mark.day6

POLICY = BootstrapPolicy(n_resamples=50, seed=1)


def prepared(cols: dict[str, list[Any]], crit: dict[str, Any] | None = None):
    decl = validate_dict(crit if crit is not None else make_criteria())
    table = schema_mod.validate(schema_mod.table_from_columns(cols), period=None)
    mask, flow = schema_mod.analysis_mask(table, decl.indeterminate_values)
    return decl, table, mask, flow


def cohort_with_exclusions(n: int = 60):
    """Three missing labels, two missing scores, four indeterminates, seven missing sexes."""
    cols = make_cohort(n=n, with_case_id=True)
    cols["y_true"][0], cols["y_true"][1], cols["y_true"][2] = None, "", "NA"
    cols["score"][3], cols["score"][4] = None, "nan"
    for i in (5, 6, 7, 8):
        cols["y_true"][i] = "2"
    for i, tok in enumerate(("", "NA", "nan", "null", "Unknown", "missing", "N/A")):
        cols["sex"][10 + i] = tok
    crit = make_criteria(indeterminates={"policy": "none_present", "values": ["2"]})
    return cols, crit


# ------------------------------------------------------------------------------ flow


def test_flow_counts_are_exactly_the_exclusions_planted():
    cols, crit = cohort_with_exclusions(60)
    decl, table, mask, flow = prepared(cols, crit)
    f = flow_block(table, mask, flow, decl)
    assert f == {
        "rows_read": 60,
        "excluded_missing_label": 3,
        "excluded_missing_score": 2,
        "indeterminate": 4,
        "analysed": 51,
        "n_cases": 51,
        "n_sites": 3,
        "clustered": False,
        "clustering_route": "none",
    }
    assert all(
        isinstance(v, int) for k, v in f.items() if k not in ("clustered", "clustering_route")
    )
    assert f["rows_read"] == (
        f["excluded_missing_label"]
        + f["excluded_missing_score"]
        + f["indeterminate"]
        + f["analysed"]
    )


def test_flow_counts_cases_and_the_clustered_route_under_a_case_column():
    n = 40
    cols = make_cohort(n=n, with_case_id=True)
    dup = {k: [v[i // 2] for i in range(2 * n)] for k, v in cols.items()}
    dup["row_id"] = [f"r{i:05d}" for i in range(2 * n)]
    decl, table, mask, flow = prepared(
        dup, make_criteria(clustering={"unit": "case_id", "declared_by": "t"})
    )
    f = flow_block(table, mask, flow, decl)
    assert f["analysed"] == 80 and f["n_cases"] == 40
    assert f["clustered"] is True and f["clustering_route"] == "declared"
    decl, table, mask, flow = prepared(dup, make_criteria())
    f = flow_block(table, mask, flow, decl)
    assert f["clustering_route"] == "detected" and f["clustered"] is True
    # no case column: every analysed row is its own case, and no site column -> null
    cols = make_cohort(n=30)
    del cols["site"]
    decl, table, mask, flow = prepared(cols)
    f = flow_block(table, mask, flow, decl)
    assert f["n_cases"] == f["analysed"] == 30 and f["n_sites"] is None
    # a plan passed in is used as given, and a mask that disagrees with the counts is refused
    plan = ClusterPlan(False, "none", 30, 30)
    assert flow_block(table, mask, flow, decl, plan)["clustering_route"] == "none"
    with pytest.raises(ValueError, match="disagrees"):
        flow_block(table, np.zeros(30, dtype=bool), flow, decl)


# --------------------------------------------------------------------------- table 1


def test_table1_and_missingness_keys_are_column_names_and_level_labels_and_nothing_per_row():
    """Lens 1 of 2026-09-18, FA-N3: the day-6 docstring said no row value, header or id
    leaves the module; attribute level labels are row values and the column names are
    headers, and both are keys. Inspected: ``sex`` on row 0 set to ``PATIENT-NAME-JOSH``
    and an ``ethnicity`` column whose row 1 reads ``ID-77812``. Both strings are Table 1
    keys and ``ethnicity`` is a missingness key; no ``row_id`` value, no ``case_id`` value
    and no score string is a key or a string anywhere in the three blocks, and every
    leaf under a level is an ``int`` count or a ``float`` share."""
    cols = make_cohort(n=60, with_case_id=True)
    cols["sex"][0] = "PATIENT-NAME-JOSH"
    cols["ethnicity"] = ["A"] * 60
    cols["ethnicity"][1] = "ID-77812"
    decl, table, mask, flow = prepared(cols)
    t1 = table1_block(table, decl, mask)
    miss = missingness_block(table)
    f = flow_block(table, mask, flow, decl)
    assert "PATIENT-NAME-JOSH" in t1["test"]["sex"] and t1["test"]["sex"]["PATIENT-NAME-JOSH"] == {
        "n": 1,
        "pct": 1 / 60,
    }
    assert "ID-77812" in t1["test"]["ethnicity"]
    assert "ethnicity" in miss["columns"] and "sex" in miss["columns"]
    tokens = set()
    for node in (t1, miss, f):
        tokens |= set(_keys_and_strings(node))
    per_row = set(cols["row_id"]) | set(cols["case_id"]) | {str(v) for v in cols["score"]}
    assert not (tokens & per_row), tokens & per_row
    for attr, levels in t1["test"].items():
        for label, leaf in levels.items():
            assert set(leaf) == {"n", "pct"} and isinstance(leaf["n"], int), (attr, label)
            assert isinstance(leaf["pct"], float)


def _keys_and_strings(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _keys_and_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _keys_and_strings(v)
    elif isinstance(node, str):
        yield node


def test_table1_pct_sums_to_one_per_attribute_within_1e_12_including_the_unknown_level():
    cols = make_cohort(n=200)
    for i in range(7):
        cols["sex"][i] = None
    for i in range(3):
        cols["site"][i] = "NA"
    cols["age"][0] = None
    decl, table, mask, _ = prepared(cols)
    t1 = table1_block(table, decl, mask)
    test = t1["test"]
    assert set(test) == {"sex", "site", "age"}
    assert UNKNOWN_LEVEL in test["sex"] and test["sex"][UNKNOWN_LEVEL]["n"] == 7
    assert test["site"][UNKNOWN_LEVEL]["n"] == 3 and test["age"][UNKNOWN_LEVEL]["n"] == 1
    for attr, levels in test.items():
        assert abs(sum(lv["pct"] for lv in levels.values()) - 1.0) <= 1e-12, attr
        assert sum(lv["n"] for lv in levels.values()) == t1["n_test"] == 200
        for lv in levels.values():
            assert isinstance(lv["n"], int) and lv["pct"] == lv["n"] / 200  # not rounded
    assert list(test["age"]) == ["0-40", "40-65", "65-80", "80-200", UNKNOWN_LEVEL]
    assert list(test["sex"]) == ["F", "M", UNKNOWN_LEVEL]
    assert t1["dev"] is None and t1["n_dev"] is None
    assert t1["similarity"] is None and t1["overlap"] is None
    assert t1["not_computed"]["similarity"] == "v1.1" and t1["not_computed"]["overlap"] == "v1.1"
    assert "dev" in t1["not_computed"]


def test_table1_levels_agree_with_the_subgroup_rows_and_use_the_declared_bands():
    cols = make_cohort(n=150)
    cols["sex"][4] = None
    crit = make_criteria()
    crit["subgroups"][1]["bands"] = [[0, 50], [50, 200]]
    crit["subgroups"][1]["reference_level"] = "0-50"
    decl, table, mask, _ = prepared(cols, crit)
    t1 = table1_block(table, decl, mask)
    rep = subgroup_analysis(table, decl, mask, policy=POLICY)
    for row in rep.rows:
        assert t1["test"][row["attribute"]][row["level"]]["n"] == row["n"], (
            row["attribute"],
            row["level"],
        )
    assert list(t1["test"]["age"]) == ["0-50", "50-200"]
    # without a declared age attribute the engine default bands are used, as in subgroups
    crit2 = make_criteria()
    crit2["subgroups"] = [s for s in crit2["subgroups"] if s["attribute"] != "age"]
    decl2, table, mask, _ = prepared(cols, crit2)
    assert list(table1_block(table, decl2, mask)["test"]["age"]) == [
        "0-40",
        "40-65",
        "65-80",
        "80-200",
    ]


def test_table1_dev_is_tabulated_when_the_table_carries_dev_rows_and_never_analysed():
    cols = make_cohort(n=100)
    cols["dataset"] = ["dev"] * 30 + ["test"] * 70
    decl, table, mask, flow = prepared(cols)
    assert int(mask.sum()) == 70
    t1 = table1_block(table, decl, mask)
    assert t1["n_dev"] == 30 and t1["n_test"] == 70
    assert sum(lv["n"] for lv in t1["dev"]["sex"].values()) == 30
    assert abs(sum(lv["pct"] for lv in t1["dev"]["site"].values()) - 1.0) <= 1e-12
    assert "dev" not in t1["not_computed"]
    dev_rows = np.arange(100) < 30
    assert table1_levels(table, decl, dev_rows) == t1["dev"]


# ------------------------------------------------------------------------ missingness


def test_missingness_counts_seven_missing_tokens_as_seven_after_normalisation():
    cols, crit = cohort_with_exclusions(60)
    decl, table, mask, _ = prepared(cols, crit)
    m = missingness_block(table)
    assert m["n_rows"] == 60
    assert m["columns"]["sex"] == {"n_missing": 7, "pct": 7 / 60}
    assert m["columns"]["y_true"] == {"n_missing": 3, "pct": 3 / 60}
    assert m["columns"]["score"] == {"n_missing": 2, "pct": 2 / 60}
    assert m["columns"]["site"]["n_missing"] == 0 and m["columns"]["case_id"]["n_missing"] == 0
    assert set(m["columns"]) == {"age", "case_id", "row_id", "score", "sex", "site", "y_true"}
    assert all(isinstance(v["n_missing"], int) for v in m["columns"].values())
    # the seven spellings were normalised to one Unknown/missing level in the typed table
    assert int((table.attributes["sex"] == UNKNOWN_LEVEL).sum()) == 7


def test_missingness_covers_numeric_extras_indeterminate_and_y_pred_columns():
    cols = make_cohort(n=20, with_y_pred=True)
    cols["indeterminate"] = ["0"] * 17 + ["", "1", None]
    cols["attr_bmi"] = ["22.5"] * 15 + ["NA"] * 5
    cols["y_pred"][0] = "null"
    decl, table, mask, _ = prepared(cols)
    m = missingness_block(table)["columns"]
    assert m["indeterminate"]["n_missing"] == 2
    assert m["attr_bmi"] == {"n_missing": 5, "pct": 0.25}
    assert m["y_pred"]["n_missing"] == 1


# ----------------------------------------------------------------------------- schema


def test_the_three_blocks_validate_against_their_schema_fragments_and_carry_no_number():
    cols, crit = cohort_with_exclusions(60)
    decl, table, mask, flow = prepared(cols, crit)
    schema = load_json_schema("output_schema_v1.json")
    for ref, block in (
        ("#/properties/flow", flow_block(table, mask, flow, decl)),
        ("#/$defs/table1Block", table1_block(table, decl, mask)),
        ("#/$defs/missingnessBlock", missingness_block(table)),
    ):
        v = jsonschema.Draft202012Validator(
            {"$ref": ref, "$defs": schema["$defs"], "properties": schema["properties"]}
        )
        assert list(v.iter_errors(block)) == [], ref
        blob = json.dumps(block)
        assert "ci_lo" not in blob and "not_estimable_reason" not in blob
        json.loads(blob)  # round-trips: plain ints, floats, strings, null
