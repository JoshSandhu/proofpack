"""Build day 9 (E9 item 7): T1 + T7 + T8 on a 100,000-row synthetic table in under 60 s.

The table is drawn in the test from :func:`proofpack.synthetic.make_cohort` (seed
20240101, 100,000 rows, three sites), confirmed as the mapping ``run`` reads, and put
through ``proofpack run --offline --templates T1,T7,T8`` with a test-only licence. Two
wall-clock figures are asserted under 60 s: the whole command (ingest, statistics,
claims, ``run.json`` and the three documents), and the three renders alone from the
``run.json`` it wrote. The measured seconds are printed (``-s``) and recorded in the E9
build note for both shells. Marked ``slow``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from conftest import confirmed_mapping, ephemeral_registry, make_criteria, write_csv, write_yaml
from proofpack.cli import main
from proofpack.errors import EXIT_OK, EXIT_WARNINGS
from proofpack.render.html import render_t8
from proofpack.render.t1 import render_t1
from proofpack.render.t7 import render_t7
from proofpack.synthetic import make_cohort
from test_run_cli import _own_home

pytestmark = [pytest.mark.day9, pytest.mark.slow]
N_ROWS = 100_000
BUDGET_S = 60.0


def test_t1_t7_t8_render_under_sixty_seconds_on_100000_rows(tmp_path: Path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch)
    cols = make_cohort(seed=20240101, n=N_ROWS)
    csv_path = write_csv(tmp_path / "big.csv", cols)
    yml = write_yaml(tmp_path / "criteria.yaml", make_criteria())
    confirmed_mapping(csv_path)
    out = tmp_path / "pack"
    t0 = time.perf_counter()
    rc = main(
        [
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--out",
            str(out),
            "--offline",
            "--templates",
            "T1,T7,T8",
        ],
        registry=ephemeral_registry(),
    )
    whole = time.perf_counter() - t0
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["flow"]["analysed"] == N_ROWS
    t1 = time.perf_counter()
    pages = [render(doc) for render in (render_t1, render_t7, render_t8)]
    renders = time.perf_counter() - t1
    for name, page in zip(("T1", "T7", "T8"), pages, strict=True):
        assert (out / f"{name}.html").read_text(encoding="utf-8") == page
    with capsys.disabled():
        print(
            f"\n[timing] 100,000 rows: run --templates T1,T7,T8 {whole:.2f} s; "
            f"T1+T7+T8 renders from run.json {renders:.2f} s; "
            f"T1 {len(pages[0])} bytes"
        )
    assert whole < BUDGET_S and renders < BUDGET_S
