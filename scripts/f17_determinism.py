"""F17 (D1 section 3.2): two runs of the synthetic cohort on one platform, compared.

    python scripts/f17_determinism.py --out DIR [--n 5000]
    python scripts/f17_determinism.py --out DIR --n 400 --inputs-only   # the inputs alone
    python scripts/f17_determinism.py --out DIR --compare               # E10: compare twice
    python scripts/f17_determinism.py --out DIR --compare-dirs RUN1 RUN2 \
        [--require-reference-platform] [--where TEXT]                   # E13: two runs made
                                                                        # elsewhere, compared

Since build day 13 the mask and the comparison live in ``proofpack.f17`` (the fixtures
command and the reference-image job use the same code); this script keeps the inputs,
the subprocess runs and the command line. ``--compare-dirs`` is what the CI job
docker-smoke runs inside the image on the two ``run.json`` directories its two
``docker run --network none`` runs wrote; with ``--require-reference-platform`` it exits 1
unless both manifests record ``linux-x86_64-cp312``.

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
   * the sorted list of file paths under each run directory (``file_names``; lens FA2-R9:
     a ``T8.html`` added to one run left ``identical`` true);
   * the egress ``manifest_sha256`` of each run (unmasked, recorded, not compared: it
     hashes ``run_id``, so two runs differ there by construction).

Exit 0 when every compared hash is equal, 1 otherwise. The platform is recorded; D1
section 9 claims hash identity on the reference platform (``python:3.12-slim``
linux/amd64) only - a result from any other platform is a same-platform repeat there.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from proofpack import f17 as _f17

HERE = Path(__file__).resolve().parent
SEED = 20240101
MAPPING_TIMESTAMP = "2026-09-24T00:00:00Z"
#: The manifest keys whose values differ between two runs of one input (manifest.py's
#: VOLATILE_KEYS); nothing else is masked. Defined in ``proofpack.f17`` since build day 13.
MASKED_KEYS = _f17.MASKED_KEYS
MASK = _f17.MASK


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


def write_prior(table: Path) -> Path:
    """E10: the synthetic prior version's table beside ``table`` (the sample-pack recipe,
    ``proofpack.synthetic.perturb_scores`` at the same seed)."""
    from proofpack.synthetic import perturb_scores

    with table.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]
    i = header.index("score")
    prior_scores = perturb_scores([float(r[i]) for r in body], SEED)
    prior = table.with_name("synthetic_prior.csv")
    with prior.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        for r, p in zip(body, prior_scores, strict=True):
            r = list(r)
            r[i] = f"{p:.6f}"
            w.writerow(r)
    return prior


def run_once(
    table: Path,
    criteria: Path,
    mapping: Path,
    out: Path,
    home: Path,
    prior: Path | None = None,
) -> int:
    """``proofpack run`` (or, with ``prior``, ``proofpack compare``: E10) in a subprocess."""
    home.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "PROOFPACK_LICENCE"}
    env["PROOFPACK_HOME"] = str(home)
    command = ["run"] if prior is None else ["compare", "--prior", str(prior)]
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proofpack.cli",
            *command,
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
    """Replace each key's value with ``"<masked>"``; each key must occur exactly once
    (``proofpack.f17.mask``)."""
    return _f17.mask(data, keys)


def masked_manifest_sha256(run_json: bytes) -> str:
    return _f17.masked_manifest_sha256(run_json)


def file_names(run_dir: Path) -> list[str]:
    """The paths of the files under ``run_dir``, relative, with ``/``, sorted."""
    return _f17.file_names(run_dir)


def compare(run1: Path, run2: Path, where: str | None = None) -> dict[str, Any]:
    """``proofpack.f17.compare`` (moved there at build day 13)."""
    return _f17.compare(run1, run2, where=where)


def run_f17(out: Path, n: int = 5000, *, compare_mode: bool = False) -> dict[str, Any]:
    table, criteria, mapping = write_inputs(out / "inputs", n)
    prior = write_prior(table) if compare_mode else None
    codes = [
        run_once(table, criteria, mapping, out / f"run{i}", out / f"home{i}", prior) for i in (1, 2)
    ]
    result = compare(out / "run1", out / "run2")
    result.update(rows=n, exit_codes=codes, command="compare" if compare_mode else "run")
    (out / "f17_result.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="F17: two runs of the synthetic cohort, compared")
    ap.add_argument("--out", default=None, help="working directory (default: a temporary one)")
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--inputs-only", action="store_true", help="write the inputs and stop")
    ap.add_argument(
        "--compare",
        action="store_true",
        help="E10: run proofpack compare (against the synthetic prior) twice instead of run",
    )
    ap.add_argument(
        "--compare-dirs",
        nargs=2,
        metavar=("RUN1", "RUN2"),
        help="E13: compare two run directories made elsewhere (the reference-image job's "
        "two docker runs) and write f17_result.json to --out",
    )
    ap.add_argument(
        "--require-reference-platform",
        action="store_true",
        help="E13: with --compare-dirs, exit 1 unless both run.json manifests record the "
        "reference platform",
    )
    ap.add_argument("--where", default=None, help="E13: where the two runs were made")
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="proofpack-f17-"))
    if args.compare_dirs:
        return _compare_dirs(args, out)
    if args.inputs_only:
        for p in write_inputs(out, args.n):
            print(f"written: {p}")
        return 0
    result = run_f17(out, args.n, compare_mode=args.compare)
    for name, check in result["checks"].items():
        print(f"{name}: {'equal' if check['equal'] else 'DIFFERENT'} {check['sha256'][0][:16]}")
    print(
        f"F17 ({result['command']}) {result['rows']} rows on {result['platform']} "
        "(reference platform: "
        f"{'yes' if result['reference_platform'] else 'no'}); run exit codes "
        f"{result['exit_codes']}; identical under the mask {list(MASKED_KEYS)}: "
        f"{'yes' if result['identical'] else 'no'}; written: {out / 'f17_result.json'}"
    )
    return 0 if result["identical"] else 1


def _compare_dirs(args: argparse.Namespace, out: Path) -> int:
    """E13: the reference-image comparison. Exit 0 only when every hash is equal (and, with
    --require-reference-platform, both manifests record the reference platform); 1
    otherwise, including a masked key that occurs other than exactly once."""
    run1, run2 = (Path(p) for p in args.compare_dirs)
    try:
        result = compare(run1, run2, where=args.where)
    except ValueError as exc:
        print(f"F17 compare-dirs: refused: {exc}")
        return 1
    result["command"] = "compare-dirs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "f17_result.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    for name, check in result["checks"].items():
        print(f"{name}: {'equal' if check['equal'] else 'DIFFERENT'} {check['sha256'][0][:16]}")
    ok = result["identical"] and (
        result["both_runs_on_reference_platform"] or not args.require_reference_platform
    )
    print(
        f"F17 (compare-dirs) {run1} vs {run2}; run platforms {result['run_platforms']}; "
        f"both on the reference platform: "
        f"{'yes' if result['both_runs_on_reference_platform'] else 'no'}; identical under the "
        f"mask {list(MASKED_KEYS)}: {'yes' if result['identical'] else 'no'}; "
        f"written: {out / 'f17_result.json'}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
