"""Write the F5 fixture pair (build day 10, E10): ``tests/fixtures/f5/f5_new.csv``,
``f5_prior.csv`` and ``criteria.yaml``.

R2 section 9 F5 is a paired table, not a row table: 100 cases, ``b = 10`` (prior correct,
new wrong), ``c = 2`` (new correct, prior wrong), ``[[80, 10], [2, 8]]``. This script
lays 100 rows out so that the accuracy two-by-two of the two versions at the declared
operating point (threshold 0.5, rule ``>=``) reproduces exactly those discordant counts:
80 rows both versions classify correctly, 10 the prior alone, 2 the new alone, 8 neither;
50 reference-positive and 50 reference-negative rows, so the table is two-class (H06) and
the declared orientation holds (H01). The scores are the correct-side base value plus a
seeded jitter (``default_rng(5)``) that never crosses the threshold, rounded to four
decimals; every value is reproducible from this file and none is real.

    python scripts/make_f5_fixture.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import yaml

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "f5"
SEED = 5
CRITERIA = {
    "schema_version": 1,
    "model": {
        "name": "f5-fixture-classifier",
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
            "threshold": 0.5,
            "rule": ">=",
            "provenance": "prespecified_sap",
            "source": "R2 section 9 F5 (fixture)",
        }
    ],
    "reference_standard": {"type": "reference_standard", "description": "fixture labels"},
    "indeterminates": {"policy": "none_present", "values": []},
    "clustering": {"unit": "none", "declared_by": "fixture"},
    "prevalence": [{"label": "fixture", "value": 0.5, "source": "fixture"}],
    "subgroups": [
        {"attribute": "sex", "prespecified": True, "source": "fixture", "reference_level": "M"}
    ],
    "criteria": [
        {
            "id": "C1",
            "metric": "sensitivity",
            "operating_point": "op1",
            "scope": "overall",
            "statistic": "ci_lower_bound",
            "comparator": ">=",
            "value": 0.7,
            "author": "F5 fixture author",
            "date": "2026-09-25",
            "justification": "a point criterion beside the paired one, so T2-2 prints both types",
        },
        {
            "id": "C2",
            "metric": "accuracy",
            "type": "paired_difference_vs_prior",
            "operating_point": "op1",
            "scope": "overall",
            "statistic": "ci_lower_bound",
            "comparator": ">=",
            "value": -0.05,
            "author": "F5 fixture author",
            "date": "2026-09-25",
            "justification": (
                "the brief's acceptance test: the F5 accuracy difference of -0.08 against a "
                "margin of -0.05 is not met"
            ),
        },
    ],
    "ledger": {"warn_after_acceptance_runs": 3},
    "egress": {"telemetry": False},
    "bootstrap": {"B": 200, "seed": 20240101, "interval": "percentile"},
}


def rows() -> list[dict[str, object]]:
    rng = np.random.default_rng(SEED)
    # (n, positive, new_correct, prior_correct)
    layout = [
        (40, 1, True, True),
        (40, 0, True, True),
        (5, 1, False, True),
        (5, 0, False, True),
        (1, 1, True, False),
        (1, 0, True, False),
        (4, 1, False, False),
        (4, 0, False, False),
    ]
    out: list[dict[str, object]] = []

    def score(positive: int, correct: bool) -> float:
        high = correct if positive else not correct
        base = 0.75 if high else 0.25
        return round(float(base + rng.uniform(-0.2, 0.2)), 4)

    i = 0
    for n, positive, new_ok, prior_ok in layout:
        for _ in range(n):
            out.append(
                {
                    "row_id": f"f5-{i:03d}",
                    "y_true": positive,
                    "score_new": score(positive, new_ok),
                    "score_prior": score(positive, prior_ok),
                    "sex": "F" if i % 2 else "M",
                }
            )
            i += 1
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    data = rows()
    for name, key in (("f5_new.csv", "score_new"), ("f5_prior.csv", "score_prior")):
        with (OUT / name).open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["row_id", "y_true", "score", "sex"])
            for r in data:
                w.writerow([r["row_id"], r["y_true"], f"{r[key]:.4f}", r["sex"]])
    (OUT / "criteria.yaml").write_text(
        yaml.safe_dump(CRITERIA, sort_keys=False), encoding="utf-8", newline="\n"
    )
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
