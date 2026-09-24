"""F17 (D1 section 3.2): two runs of the synthetic cohort on one platform, compared.

    python scripts/f17_determinism.py --out DIR [--n 5000]
    python scripts/f17_determinism.py --out DIR --n 400 --inputs-only   # the inputs alone

What it does:

1. writes ``DIR/inputs/synthetic.csv`` (``proofpack.synthetic.make_cohort``, seed
   20240101, ``--n`` rows), ``DIR/inputs/criteria.yaml`` (``scripts/build_sample_pack.py``'s
   ``SAMPLE_CRITERIA``: no acceptance criteria, ``egress.telemetry: false``) and a confirmed
   ``synthetic.csv.mapping.json`` with a fixed timestamp;
2. runs ``python -m proofpack.cli run ... --offline --format json`` twice, each in its own
   subprocess with its own empty ``PROOFPACK_HOME`` (so no licence is read: both exit 4 and
   write ``run.json`` with the ``NO LICENCE`` watermark; ``manifest.ledger_count`` is 0 in
   both, measured 24 September 2026, because the sample declares no criteria list and
   DEC-47 counts only runs with one that wrote a document) into ``DIR/run1`` and
   ``DIR/run2``;
3. compares, and writes ``DIR/f17_result.json``:

   * ``run.json`` bytes with the values of ``run_id``, ``started`` and ``duration_s`` masked
     (:data:`MASKED_KEYS`, a byte-level substitution; each key must occur exactly once);
   * the manifest block's SHA-256 over canonical JSON with the same three keys masked;
   * ``pseudonyms.json`` bytes with its ``run_id`` masked (it carries the run's id,
     A-P2 note item 3), and ``ingest_report.json`` bytes as written;
   * the egress ``manifest_sha256`` of each run (unmasked, recorded, not compared: it
     hashes ``run_id``, so two runs differ there by construction).

Exit 0 when every compared hash is equal, 1 otherwise. The platform is recorded; D1
section 9 claims hash identity on the reference platform (``python:3.12-slim``
linux/amd64) only - a result from any other platform is a same-platform repeat there.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
SEED = 20240101
MAPPING_TIMESTAMP = "2026-09-24T00:00:00Z"
#: The manifest keys whose values differ between two runs of one input (manifest.py's
#: VOLATILE_KEYS); nothing else is masked.
MASKED_KEYS = ("run_id", "started", "duration_s")
MASK = "<masked>"
_VALUE = {
    "run_id": rb'"run_id": "[0-9a-f-]{36}"',
    "started": rb'"started": "[0-9T:\-]+Z"',
    "duration_s": rb'"duration_s": [0-9.eE+\-]+',
}


def _sample_criteria() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "build_sample_pack", HERE / "build_sample_pack.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return json.loads(json.dumps(module.SAMPLE_CRITERIA))


def write_inputs(work: Path, n: int) -> tuple[Path, Path, Path]:
    from proofpack.io.mapping import map_headers
    from proofpack.io.schema import load_table
    from proofpack.synthetic import make_cohort

    work.mkdir(parents=True, exist_ok=True)
    cols = make_cohort(seed=SEED, n=n)
    table = work / "synthetic.csv"
    headers = list(cols)
    with table.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(headers)
        for i in range(n):
            w.writerow([cols[h][i] for h in headers])
    criteria = work / "criteria.yaml"
    criteria.write_text(yaml.safe_dump(_sample_criteria(), sort_keys=False), encoding="utf-8")
    raw = load_table(table)
    mapping = map_headers(raw.headers, raw.columns)
    mapping.decided_by = "file"
    mapping.timestamp = MAPPING_TIMESTAMP
    mapping_path = table.with_name(table.name + ".mapping.json")
    mapping.write(mapping_path)
    return table, criteria, mapping_path


def run_once(table: Path, criteria: Path, mapping: Path, out: Path, home: Path) -> int:
    home.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "PROOFPACK_LICENCE"}
    env["PROOFPACK_HOME"] = str(home)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proofpack.cli",
            "run",
            "--input",
            str(table),
            "--criteria",
            str(criteria),
            "--mapping",
            str(mapping),
            "--out",
            str(out),
            "--offline",
            "--format",
            "json",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(home),
    )
    return proc.returncode


def mask(data: bytes, keys: tuple[str, ...] = MASKED_KEYS) -> bytes:
    """Replace each key's value with ``"<masked>"``; each key must occur exactly once."""
    for key in keys:
        data, n = re.subn(_VALUE[key], f'"{key}": "{MASK}"'.encode(), data)
        if n != 1:
            raise ValueError(f"{key} occurs {n} times; expected exactly once")
    return data


def masked_manifest_sha256(run_json: bytes) -> str:
    from proofpack.manifest import canonical_json

    manifest = dict(json.loads(run_json.decode("utf-8"))["manifest"])
    for key in MASKED_KEYS:
        manifest[key] = MASK
    return hashlib.sha256(canonical_json(manifest)).hexdigest()


def compare(run1: Path, run2: Path) -> dict[str, Any]:
    from proofpack.egress.build import manifest_sha256
    from proofpack.manifest import platform_tag

    a, b = (p / "run.json" for p in (run1, run2))
    ra, rb = a.read_bytes(), b.read_bytes()
    checks = {
        "run_json_masked": [hashlib.sha256(mask(x)).hexdigest() for x in (ra, rb)],
        "manifest_masked": [masked_manifest_sha256(x) for x in (ra, rb)],
        "pseudonyms_json_masked": [
            hashlib.sha256(mask((p / "pseudonyms.json").read_bytes(), ("run_id",))).hexdigest()
            for p in (run1, run2)
        ],
        "ingest_report_json": [
            hashlib.sha256((p / "ingest_report.json").read_bytes()).hexdigest()
            for p in (run1, run2)
        ],
    }
    manifests = [json.loads(x.decode("utf-8"))["manifest"] for x in (ra, rb)]
    return {
        "fixture": "F17",
        "platform": platform_tag(),
        "reference_platform": manifests[0]["reference_platform"],
        "masked_keys": list(MASKED_KEYS),
        "hashed_set": sorted(checks),
        "checks": {k: {"sha256": v, "equal": v[0] == v[1]} for k, v in checks.items()},
        "identical": all(v[0] == v[1] for v in checks.values()),
        "raw_bytes_equal": ra == rb,
        "egress_manifest_sha256_unmasked": [manifest_sha256(m) for m in manifests],
        "ledger_count": [m["ledger_count"] for m in manifests],
        "run_json_bytes": [len(ra), len(rb)],
    }


def run_f17(out: Path, n: int = 5000) -> dict[str, Any]:
    table, criteria, mapping = write_inputs(out / "inputs", n)
    codes = [run_once(table, criteria, mapping, out / f"run{i}", out / f"home{i}") for i in (1, 2)]
    result = compare(out / "run1", out / "run2")
    result.update(rows=n, exit_codes=codes)
    (out / "f17_result.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="F17: two runs of the synthetic cohort, compared")
    ap.add_argument("--out", default=None, help="working directory (default: a temporary one)")
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--inputs-only", action="store_true", help="write the inputs and stop")
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="proofpack-f17-"))
    if args.inputs_only:
        for p in write_inputs(out, args.n):
            print(f"written: {p}")
        return 0
    result = run_f17(out, args.n)
    for name, check in result["checks"].items():
        print(f"{name}: {'equal' if check['equal'] else 'DIFFERENT'} {check['sha256'][0][:16]}")
    print(
        f"F17 {result['rows']} rows on {result['platform']} (reference platform: "
        f"{'yes' if result['reference_platform'] else 'no'}); run exit codes "
        f"{result['exit_codes']}; identical under the mask {list(MASKED_KEYS)}: "
        f"{'yes' if result['identical'] else 'no'}; written: {out / 'f17_result.json'}"
    )
    return 0 if result["identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
