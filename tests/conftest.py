"""Test infrastructure: seeded synthetic cohort factory and a valid declarations factory.

This is *test scaffolding only* - the F18 story-injecting generator is Day 7.
Every value is produced by a seeded numpy Generator; nothing is hand-typed.
"""

from __future__ import annotations

import copy
import csv
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml


def make_cohort(
    seed: int = 20240101,
    n: int = 400,
    prevalence: float = 0.3,
    separation: float = 1.5,
    sites: int = 3,
    with_row_id: bool = True,
    with_case_id: bool = False,
    with_y_pred: bool = False,
    threshold: float = 0.5,
    positive: str = "1",
    negative: str = "0",
) -> dict[str, list[Any]]:
    """Seeded binary cohort with a probability-like score, sex, age, site columns.

    Scores are sigmoid(normal) shifted by ``separation`` for positives, so the
    declared orientation ``higher_is_positive`` is correct and AUROC is well above 0.5.
    """
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < prevalence).astype(int)
    z = rng.normal(0.0, 1.0, n) + separation * y - separation / 2
    score = 1.0 / (1.0 + np.exp(-z))
    cols: dict[str, list[Any]] = {}
    if with_row_id:
        cols["row_id"] = [f"r{i:06d}" for i in range(n)]
    if with_case_id:
        cols["case_id"] = [f"c{i:06d}" for i in range(n)]
    cols["y_true"] = [positive if v == 1 else negative for v in y.tolist()]
    cols["score"] = [round(float(s), 6) for s in score.tolist()]
    if with_y_pred:
        cols["y_pred"] = [positive if s >= threshold else negative for s in cols["score"]]
    cols["sex"] = rng.choice(["F", "M"], size=n).tolist()
    cols["age"] = rng.integers(18, 95, size=n).tolist()
    cols["site"] = rng.choice([f"S{k}" for k in range(1, sites + 1)], size=n).tolist()
    return cols


def make_criteria(threshold: float = 0.5, **overrides: Any) -> dict[str, Any]:
    """A complete, valid criteria.yaml mapping (authored fields are placeholders for tests)."""
    base: dict[str, Any] = {
        "schema_version": 1,
        "model": {
            "name": "synthetic-classifier",
            "version": "1.3",
            "prior_version": "1.2",
            "udi_di": None,
        },
        "task": "binary",
        "classes": {"positive": "1", "negative": "0"},
        "score": {"type": "probability", "orientation": "higher_is_positive"},
        "operating_points": [
            {
                "id": "op1",
                "threshold": threshold,
                "rule": ">=",
                "provenance": "prespecified_sap",
                "source": "test fixture",
            },
        ],
        "reference_standard": {"type": "reference_standard", "description": "test fixture"},
        "indeterminates": {"policy": "none_present", "values": []},
        "clustering": {"unit": "none", "declared_by": "test fixture"},
        "prevalence": [{"label": "intended-use, test", "value": 0.3, "source": "test fixture"}],
        "subgroups": [
            {"attribute": "sex", "prespecified": True, "source": "test", "reference_level": "M"},
            {
                "attribute": "age",
                "prespecified": True,
                "source": "test",
                "bands": [[0, 40], [40, 65], [65, 80], [80, 200]],
                "reference_level": "40-65",
            },
            {"attribute": "site", "prespecified": False, "reference_level": "largest"},
        ],
        "criteria": [
            {
                "id": "C1",
                "metric": "sensitivity",
                "operating_point": "op1",
                "scope": "overall",
                "statistic": "ci_lower_bound",
                "comparator": ">=",
                "value": 0.8,
                "author": "Test Author",
                "date": "2026-01-01",
                "justification": "test fixture",
            },
        ],
        "ledger": {"warn_after_acceptance_runs": 3},
        "egress": {
            "telemetry": False,
            "suppression": {"min_n": 10, "min_events": 5, "min_nonevents": 5},
        },
        "bootstrap": {"B": 200, "seed": 20240101, "interval": "percentile"},
    }
    out = copy.deepcopy(base)
    for k, v in overrides.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = v
    return out


def write_csv(path: Path, cols: dict[str, list[Any]]) -> Path:
    headers = list(cols)
    n = len(cols[headers[0]]) if headers else 0
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        for i in range(n):
            w.writerow([cols[h][i] for h in headers])
    return path


def write_yaml(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


@pytest.fixture
def cohort() -> dict[str, list[Any]]:
    return make_cohort()


@pytest.fixture
def criteria() -> dict[str, Any]:
    return make_criteria()


@pytest.fixture
def cohort_csv(tmp_path: Path, cohort) -> Path:
    return write_csv(tmp_path / "test.csv", cohort)


@pytest.fixture
def criteria_yaml(tmp_path: Path, criteria) -> Path:
    return write_yaml(tmp_path / "criteria.yaml", criteria)


@pytest.fixture
def out_dir(tmp_path: Path) -> Path:
    return tmp_path / "pack"
