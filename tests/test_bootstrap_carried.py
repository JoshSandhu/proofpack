"""Carried item 25 of the day-6 handoff (build day 7, E7): ``resample_sd`` was ``inf``.

The construction is the lens-3 fresh-attack's, re-run at ``7eb617f`` and at ``a0c9abc``:
57 rows at ``1e-160`` beside 3 at ``0.5``, 20 events, 30 two-row declared cases, B = 200,
seed 20240101. The O:E draws include values above 1e154, numpy squares the centred draws
in ``usable.std(ddof=1)`` and the sample sd overflows to ``inf`` while the percentile
bounds - order statistics - stay finite: ``est 13.33``, bounds ``(4.0, 4.0e159)``.
``json.dumps(block, allow_nan=False)`` then raised ``Out of range float values are not
JSON compliant: inf``, and the CLI's default ``json.dumps`` would have written the
non-JSON token ``Infinity``.

The fix is confined to :func:`proofpack.stats.bootstrap._resample_sd` (the non-finite
branch of ``bootstrap_percentile``): the sd is ``None`` and the typed reason
``resample_sd_not_finite`` rides beside it in the cell's bootstrap block. Every other
figure of the block is pinned against the snapshot taken at ``a0c9abc``
(``tests/fixtures/item25_oe_block_a0c9abc.json``, written by the build session with
every non-finite float replaced by a string because JSON cannot hold one).

Measured failing in a worktree at ``a0c9abc`` with ``PYTHONPATH`` forced to its ``src``:
``test_item25_resample_sd_is_none_with_the_reason_and_the_block_serialises`` fails on
``assert sd is None`` with ``inf``; the snapshot test passes there by construction (the
snapshot was taken there).
"""

from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import pytest

from conftest import make_criteria
from proofpack.io.declare import validate_dict
from proofpack.stats import bootstrap
from proofpack.stats.bootstrap import BootstrapPolicy, plan_clustering
from proofpack.stats.calibration import calibration_block

pytestmark = pytest.mark.day7

# read through the module so that at a0c9abc (no such name) the first test still reaches
# its ``assert sd is None`` and fails on the ``inf`` rather than on an ImportError
RESAMPLE_SD_NOT_FINITE = getattr(bootstrap, "RESAMPLE_SD_NOT_FINITE", "resample_sd_not_finite")

SNAPSHOT = pathlib.Path(__file__).parent / "fixtures" / "item25_oe_block_a0c9abc.json"


def _item25_block() -> dict:
    crit = make_criteria(clustering={"unit": "case_id", "declared_by": "test"})
    decl = validate_dict(crit)
    p = np.array([1e-160] * 57 + [0.5] * 3)
    y = np.array([True] * 20 + [False] * 40)
    ids = np.array([f"c{i // 2}" for i in range(60)], dtype=object)
    plan = plan_clustering("case_id", ids, 60)
    res = calibration_block(
        p,
        y,
        decl,
        cluster_ids=ids,
        plan=plan,
        policy=BootstrapPolicy(n_resamples=200, seed=20240101),
    )
    assert res.block is not None
    return res.block


def test_item25_resample_sd_is_none_with_the_reason_and_the_block_serialises():
    block = _item25_block()
    oe = block["oe"]
    number = oe["number"]
    # the interval itself is finite and kept: only the descriptive sd is withheld
    assert number["est"] == pytest.approx(20 / 1.5)
    assert number["ci_lo"] == pytest.approx(4.0)
    assert math.isfinite(number["ci_hi"]) and number["ci_hi"] > 1e150
    assert number["method"] == "cluster_bootstrap_percentile"
    sd = oe["bootstrap"]["resample_sd"]
    assert sd is None, sd  # a0c9abc: inf
    assert oe["bootstrap"].get("resample_sd_reason") == RESAMPLE_SD_NOT_FINITE
    # every other cell of the block keeps a finite sd and no reason
    for key, cell in block.items():
        if key == "oe" or not isinstance(cell, dict) or not cell.get("bootstrap"):
            continue
        assert cell["bootstrap"].get("resample_sd_reason") is None, key
        sd = cell["bootstrap"]["resample_sd"]
        assert sd is None or math.isfinite(sd), (key, sd)
    # (b) the whole block is JSON with allow_nan=False
    text = json.dumps(block, allow_nan=False, sort_keys=True)
    assert "Infinity" not in text and "NaN" not in text


def _strip_sd(node):
    """Drop the two keys the fix may change, everywhere in the block."""
    if isinstance(node, dict):
        return {
            k: _strip_sd(v)
            for k, v in node.items()
            if k not in ("resample_sd", "resample_sd_reason")
        }
    if isinstance(node, list):
        return [_strip_sd(v) for v in node]
    return node


def test_item25_every_other_figure_of_the_block_is_unchanged_against_a0c9abc():
    """(c) the snapshot taken at ``a0c9abc`` minus ``resample_sd`` equals the block now
    minus ``resample_sd`` and ``resample_sd_reason``; the O:E ``resample_sd`` was the only
    non-finite float in the snapshot (its ``_provenance`` says so)."""
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert "a0c9abc" in snap["_provenance"]
    before = _strip_sd(snap["block"])
    now = _strip_sd(_item25_block())
    assert json.dumps(now, sort_keys=True, allow_nan=False) == json.dumps(before, sort_keys=True)
    # the snapshot's one non-finite value was the O:E resample_sd, nothing else
    text = json.dumps(snap["block"])
    assert text.count("non-finite float at a0c9abc") == 1
    assert snap["block"]["oe"]["bootstrap"]["resample_sd"] == "non-finite float at a0c9abc"


def test_resample_sd_helper_is_exact_on_the_three_branches():
    _resample_sd = bootstrap._resample_sd
    assert _resample_sd(np.array([0.5])) == (0.0, None)
    sd, reason = _resample_sd(np.array([1.0, 2.0, 3.0, 4.0]))
    assert sd == pytest.approx(math.sqrt(5 / 3)) and reason is None
    sd, reason = _resample_sd(np.array([1e160, 1.0, 2.0]))
    assert sd is None and reason == RESAMPLE_SD_NOT_FINITE
    # a draw just below the overflow point keeps a finite sd: the branch is the
    # finiteness of the sd, not a threshold of its own
    sd, reason = _resample_sd(np.array([1e150, 1.0, 2.0]))
    assert sd is not None and math.isfinite(sd) and reason is None


def test_a_finite_cell_carries_a_null_reason_beside_its_sd():
    crit = make_criteria()
    decl = validate_dict(crit)
    rng = np.random.default_rng(1)
    p = rng.random(80)
    y = rng.random(80) < p
    res = calibration_block(p, y, decl, policy=BootstrapPolicy(n_resamples=100, seed=1))
    brier = res.block["brier"]
    assert math.isfinite(brier["bootstrap"]["resample_sd"])
    assert brier["bootstrap"]["resample_sd_reason"] is None
