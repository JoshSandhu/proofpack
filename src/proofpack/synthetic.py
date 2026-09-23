"""A seeded synthetic binary cohort (build day 9, E9): the generator the tests have used
since day 1 (``tests/conftest.py`` imports it from here), moved into the package so that
``scripts/build_sample_pack.py`` and the 100,000-row timing test draw the same rows.

Every value is produced by one seeded ``numpy.random.Generator``; nothing is hand-typed and
nothing is real. The rows carry a probability-like score, ``sex``, ``age`` and ``site``.
"""

from __future__ import annotations

from typing import Any

import numpy as np


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
