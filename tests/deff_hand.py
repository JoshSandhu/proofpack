"""A hand computation of the design-effect Wilson interval (E11 item 5), written here from
the formula stated in ``stats.proportions.design_effect`` and imported by no engine code:
the tests compare the engine with this, never the engine with itself.

    K cases, m_i rows and y_i successes in case i, n = sum m_i, p = k / n
    v    = K / (K - 1) * sum_i (y_i - p m_i)^2 / n^2
    DEFF = v / (p (1 - p) / n), floored at 1
    n_eff = n / DEFF;  Wilson on (p, n_eff):
    (2 n_eff p + z^2 -+ z sqrt(z^2 + 4 n_eff p (1 - p))) / (2 (n_eff + z^2))
"""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any


def hand_deff(indicator: Any, case_ids: list[Any]) -> tuple[float, int]:
    """``(DEFF, K)`` with the typed cases of the engine's rule: one row per case -> 1;
    all rows agree with a case of two or more rows -> sum m_i^2 / n; below 1 -> 1."""
    ys: dict[Any, list[int]] = {}
    for v, c in zip([bool(x) for x in indicator], case_ids, strict=True):
        ys.setdefault(c, []).append(int(v))
    n = sum(len(v) for v in ys.values())
    big_k = len(ys)
    if big_k < 2:
        raise ValueError("one case")
    if max(len(v) for v in ys.values()) == 1:
        return 1.0, big_k
    k = sum(sum(v) for v in ys.values())
    if k in (0, n):
        return sum(len(v) ** 2 for v in ys.values()) / n, big_k
    p = k / n
    ss = sum((sum(v) - p * len(v)) ** 2 for v in ys.values())
    v = big_k / (big_k - 1) * ss / (n * n)
    return max(v / (p * (1 - p) / n), 1.0), big_k


def hand_wilson(p: float, n_eff: float, level: float = 0.95) -> tuple[float, float]:
    z = NormalDist().inv_cdf(0.5 + level / 2)
    centre = 2 * n_eff * p + z * z
    rad = z * math.sqrt(z * z + 4 * n_eff * p * (1 - p))
    den = 2 * (n_eff + z * z)
    return max(0.0, (centre - rad) / den), min(1.0, (centre + rad) / den)


def hand_deff_wilson(indicator: Any, case_ids: list[Any], level: float = 0.95):
    """``(DEFF, lower, upper)`` for the proportion of ``indicator`` over ``case_ids``."""
    ind = [bool(x) for x in indicator]
    deff, _ = hand_deff(ind, case_ids)
    n = len(ind)
    lo, hi = hand_wilson(sum(ind) / n, n / deff, level)
    return deff, lo, hi
