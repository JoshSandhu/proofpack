"""Build the ``/sample-pack`` artefact (build day 9, E9 item 6): T1, T7, T8 and run.json of
the synthetic cohort, in one directory the site's S4 wraps without restyling.

    python scripts/build_sample_pack.py --out <dir>

What it does, and what it cannot be made to do:

* it generates its own input - :func:`proofpack.synthetic.make_cohort` at a fixed seed -
  and its own ``criteria.yaml`` (:data:`SAMPLE_CRITERIA`), and takes **no input path**:
  the script cannot be pointed at a customer's table, so its licence-free render (below)
  is not a way round the licence rule for real data;
* it runs the engine's own assembly (:func:`proofpack.run.assemble_run`) with
  ``PROOFPACK_HOME`` set to an empty temporary directory, so no licence and no ledger of
  the machine is read or written, and nothing opens a socket (``assemble_run`` imports no
  network module; telemetry lives in ``cli.cmd_run`` only, which this script does not
  call). The manifest therefore carries DEC-48's ``NO LICENCE - not for submission``, and
  ``data_marking`` ``SYNTHETIC - illustrative`` (``proofpack.scope.SYNTHETIC_MARK``), so
  every page's footer and cover stamp carry both;
* it declares **no acceptance criteria and no fairness bound**: ProofPack never authors a
  criterion, so the sample shows the no-criteria form of T1 section 12 and T8 section 5a;
* ``run.json`` is written by :func:`proofpack.run.write_run` and the three documents are
  rendered from that file read back, so each page is a pure function of the ``run.json``
  beside it. The mapping file's timestamp is fixed (:data:`MAPPING_TIMESTAMP`) so its
  SHA-256 in the manifest is the same on every build; two builds differ only in
  ``run_id``, ``started`` and ``duration_s`` (``tests/test_sample_pack.py``).

Output: ``<out>/run.json``, ``<out>/T1.html``, ``<out>/T7.html``, ``<out>/T8.html``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

SEED = 20240101
N_ROWS = 400
MAPPING_TIMESTAMP = "2026-09-24T00:00:00Z"
FILES = ("run.json", "T1.html", "T7.html", "T8.html")
SAMPLE_CRITERIA: dict[str, Any] = {
    "schema_version": 1,
    "model": {
        "name": "synthetic-sample-classifier",
        "version": "0.9",
        "prior_version": None,
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
            "provenance": "other",
            "source": "synthetic sample: illustrative threshold, no analysis plan exists",
        }
    ],
    "reference_standard": {
        "type": "reference_standard",
        "description": "synthetic labels drawn by the generator; no clinical reference exists",
    },
    "indeterminates": {"policy": "none_present", "values": []},
    "clustering": {"unit": "none", "declared_by": "synthetic sample"},
    "prevalence": [
        {"label": "synthetic, illustrative", "value": 0.3, "source": "the generator's own rate"}
    ],
    "subgroups": [
        {"attribute": "sex", "prespecified": False, "reference_level": "largest"},
        {
            "attribute": "age",
            "prespecified": False,
            "bands": [[0, 40], [40, 65], [65, 80], [80, 200]],
            "reference_level": "largest",
        },
        {"attribute": "site", "prespecified": False, "reference_level": "largest"},
    ],
    "criteria": [],
    "egress": {
        "telemetry": False,
        "suppression": {"min_n": 10, "min_events": 5, "min_nonevents": 5},
    },
    "bootstrap": {"B": 500, "seed": SEED, "interval": "percentile"},
}


def _write_inputs(work: Path) -> tuple[Path, Path]:
    import csv

    from proofpack.io.mapping import map_headers
    from proofpack.io.schema import load_table
    from proofpack.synthetic import make_cohort

    cols = make_cohort(seed=SEED, n=N_ROWS)
    table = work / "synthetic.csv"
    headers = list(cols)
    with table.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(headers)
        for i in range(N_ROWS):
            w.writerow([cols[h][i] for h in headers])
    criteria = work / "criteria.yaml"
    criteria.write_text(yaml.safe_dump(SAMPLE_CRITERIA, sort_keys=False), encoding="utf-8")
    raw = load_table(table)
    mapping = map_headers(raw.headers, raw.columns)
    mapping.decided_by = "file"
    mapping.timestamp = MAPPING_TIMESTAMP
    mapping.write(table.with_name(table.name + ".mapping.json"))
    return table, criteria


def build(out: str | Path) -> list[Path]:
    """Write the four files into ``out`` and return their paths."""
    from proofpack.render.html import render_t8
    from proofpack.render.t1 import render_t1
    from proofpack.render.t7 import render_t7
    from proofpack.run import assemble_run, write_run
    from proofpack.scope import SYNTHETIC_MARK

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="proofpack-sample-") as tmp:
        work = Path(tmp)
        home = work / "home"
        home.mkdir()
        saved = {k: os.environ.get(k) for k in ("PROOFPACK_HOME", "PROOFPACK_LICENCE")}
        os.environ["PROOFPACK_HOME"] = str(home)
        os.environ.pop("PROOFPACK_LICENCE", None)
        try:
            table, criteria = _write_inputs(work)
            outcome = assemble_run(table, criteria, ledger_home=home, data_marking=SYNTHETIC_MARK)
            write_run(outcome, work / "run")
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        data = (work / "run" / "run.json").read_bytes()
    (out_dir / "run.json").write_bytes(data)
    document = json.loads(data.decode("utf-8"))
    written = [out_dir / "run.json"]
    for name, render in (("T1.html", render_t1), ("T7.html", render_t7), ("T8.html", render_t8)):
        target = out_dir / name
        target.write_bytes(render(document).encode("utf-8"))
        written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_sample_pack.py",
        description="Write T1, T7, T8 and run.json of the synthetic cohort (no input path).",
    )
    parser.add_argument("--out", required=True, help="directory to write the four files into")
    args = parser.parse_args(argv)
    for path in build(args.out):
        print(f"written: {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
