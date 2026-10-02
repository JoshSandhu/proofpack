"""Build day 11 (E11) item 8: E10 rows 132 and 149, two false typed reasons.

* **Row 132** (lens 1 FA-N4): a ``y_pred``-only pair has no score column; its
  ``comparison.differences.brier`` and ``slope`` now carry ``no_score_column`` - the
  reason the run's own block records (``overall.threshold_free.suppressed_reason``) -
  where ``ad66073`` printed ``score_not_probability``. ``no_score_column`` joins
  ``number.NOT_ESTIMABLE_REASONS`` and the schema's ``notEstimableReason`` enum.
* **Row 149** (lens 3 FA-N3): a ``paired_difference_vs_prior`` criterion on ``ppv`` is
  ``not_assessable / metric_not_compared`` (PPV and NPV are not compared between
  versions); ``ad66073`` read ``comparison_not_computed_for_scope`` although the overall
  scope was compared. ``metric_not_compared`` joins ``criteria.REASON_CODES`` and the
  schema's ``criterionResult.reason_code`` enum; ``f1`` keeps ``metric_not_computed``.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import jsonschema
import pytest
import yaml

from conftest import confirmed_mapping, ephemeral_registry, write_licence
from proofpack import criteria as criteria_mod
from proofpack.resources import load_json_schema
from proofpack.run import assemble_compare
from proofpack.stats.number import NOT_ESTIMABLE_REASONS

pytestmark = pytest.mark.day11

REPO = Path(__file__).resolve().parent.parent
F5 = REPO / "tests" / "fixtures" / "f5"
PAIRED = "paired_difference_vs_prior"


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir()
    write_licence(h / "proofpack.lic")
    monkeypatch.setenv("PROOFPACK_HOME", str(h))
    return h


def _y_pred_only(src: Path, dst: Path) -> None:
    with src.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    with dst.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["row_id", "y_true", "y_pred", "sex"])
        for r in rows:
            w.writerow(
                [r["row_id"], r["y_true"], "1" if float(r["score"]) >= 0.5 else "0", r["sex"]]
            )


def _compare(tmp_path: Path, home: Path, crit: dict, *, y_pred_only: bool = False):
    work = tmp_path / "w"
    work.mkdir()
    for name in ("f5_new.csv", "f5_prior.csv"):
        if y_pred_only:
            _y_pred_only(F5 / name, work / name)
        else:
            shutil.copy(F5 / name, work / name)
    (work / "criteria.yaml").write_text(yaml.safe_dump(crit, sort_keys=False), "utf-8")
    confirmed_mapping(work / "f5_new.csv")
    return assemble_compare(
        work / "f5_new.csv",
        work / "f5_prior.csv",
        work / "criteria.yaml",
        registry=ephemeral_registry(),
        ledger_home=home,
    ).document


def _f5_criteria() -> dict:
    return yaml.safe_load((F5 / "criteria.yaml").read_text(encoding="utf-8"))


def test_row_132_a_y_pred_only_pair_types_its_score_differences_no_score_column(tmp_path, home):
    doc = _compare(tmp_path, home, _f5_criteria(), y_pred_only=True)
    assert doc["overall"]["threshold_free"]["suppressed_reason"] == "no_score_column"
    for key in ("brier", "slope"):
        number = doc["comparison"]["differences"][key]["number"]
        assert number["not_estimable_reason"] == "no_score_column", key
    jsonschema.Draft202012Validator(load_json_schema("output_schema_v1.json")).validate(doc)


def test_row_132_the_reason_is_in_the_code_and_the_schema_enum():
    schema = load_json_schema("output_schema_v1.json")
    assert "no_score_column" in NOT_ESTIMABLE_REASONS
    assert "no_score_column" in schema["$defs"]["notEstimableReason"]["enum"]
    assert set(schema["$defs"]["notEstimableReason"]["enum"]) == set(NOT_ESTIMABLE_REASONS)


def test_row_149_a_paired_ppv_criterion_is_metric_not_compared(tmp_path, home):
    crit = _f5_criteria()
    base = dict(crit["criteria"][1])
    crit["criteria"] = [
        {**base, "id": "Cppv", "metric": "ppv"},
        {**base, "id": "Cnpv", "metric": "npv"},
        {**base, "id": "Cf1", "metric": "f1"},
        {**base, "id": "Cacc", "metric": "accuracy"},
    ]
    doc = _compare(tmp_path, home, crit)
    rows = {r["criterion_id"]: r for r in doc["criteria_results"]}
    for cid in ("Cppv", "Cnpv"):
        assert (rows[cid]["status"], rows[cid]["reason_code"]) == (
            "not_assessable",
            "metric_not_compared",
        ), cid
    assert rows["Cf1"]["reason_code"] == "metric_not_computed"
    assert rows["Cacc"]["reason_code"] == "statistic_compared"
    jsonschema.Draft202012Validator(load_json_schema("output_schema_v1.json")).validate(doc)


def test_row_149_the_reason_is_in_the_code_and_the_schema_enum():
    schema = load_json_schema("output_schema_v1.json")
    enum = schema["$defs"]["criterionResult"]["properties"]["reason_code"]["enum"]
    assert "metric_not_compared" in criteria_mod.REASON_CODES
    assert "metric_not_compared" in enum and set(enum) == set(criteria_mod.REASON_CODES)
