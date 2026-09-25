"""Build day 10 (E10 item 7): ``proofpack compare`` on a 100,000-row synthetic pair in
under 120 s.

The new table is :func:`proofpack.synthetic.make_cohort` (seed 20240101, 100,000 rows,
three sites); the prior is the same rows with :func:`proofpack.synthetic.perturb_scores`
(the sample-pack recipe); the criteria are ``make_criteria()`` (B = 200) plus one
``paired_difference_vs_prior`` criterion, so the paired bootstrap of the Brier and slope
differences (two IRLS fits per resample) is in the measurement. The whole command
(ingest of both tables, the new version's statistics, the comparison, claims,
``run.json`` and ``T2.html``) is asserted under 120 s; the measured seconds are printed
(``-s``) and recorded in the E10 build note for both shells. Marked ``slow``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from conftest import confirmed_mapping, ephemeral_registry, make_criteria, write_csv, write_yaml
from proofpack.cli import main
from proofpack.errors import EXIT_OK, EXIT_WARNINGS
from proofpack.render.t2 import render_t2
from proofpack.synthetic import make_cohort, perturb_scores
from test_criteria import _criterion
from test_run_cli import _own_home

pytestmark = [pytest.mark.day10, pytest.mark.slow]
N_ROWS = 100_000
BUDGET_S = 120.0


def test_compare_with_t2_under_120_seconds_on_100000_row_pair(tmp_path: Path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    cols = make_cohort(seed=20240101, n=N_ROWS)
    prior_cols = dict(cols)
    prior_cols["score"] = perturb_scores(cols["score"], 20240101)
    new = write_csv(tmp_path / "new.csv", cols)
    prior = write_csv(tmp_path / "prior.csv", prior_cols)
    crit = make_criteria()
    crit["criteria"].append(
        _criterion(id="Cpd", metric="accuracy", type="paired_difference_vs_prior", value=-0.5)
    )
    yml = write_yaml(tmp_path / "criteria.yaml", crit)
    confirmed_mapping(new)
    out = tmp_path / "pack"
    t0 = time.perf_counter()
    rc = main(
        [
            "compare",
            "--input",
            str(new),
            "--prior",
            str(prior),
            "--criteria",
            str(yml),
            "--out",
            str(out),
            "--offline",
        ],
        registry=ephemeral_registry(),
    )
    whole = time.perf_counter() - t0
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["comparison"]["n_pairs"] == N_ROWS and doc["flow"]["analysed"] == N_ROWS
    assert doc["comparison"]["differences"]["slope"]["number"]["method"] == "bootstrap_percentile"
    row = next(r for r in doc["criteria_results"] if r["criterion_id"] == "Cpd")
    assert row["status"] == "met"
    t1 = time.perf_counter()
    page = render_t2(doc)
    render = time.perf_counter() - t1
    assert (out / "T2.html").read_text(encoding="utf-8") == page
    with capsys.disabled():
        print(
            f"\n[timing] 100,000-row pair: compare --templates T2 {whole:.2f} s; "
            f"T2 render from run.json {render:.2f} s; T2 {len(page)} bytes"
        )
    assert whole < BUDGET_S and render < BUDGET_S
