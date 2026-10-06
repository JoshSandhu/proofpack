"""F17 (D1 section 3.2; section 10 gate 3; build day 13, E13): two runs compared under a
three-key mask.

D1 section 3.2's F17 row: *synthetic 5k-row cohort, same platform, two runs: identical
manifest hash and byte-identical JSON*. Two runs of one input cannot be byte-identical
in full: the manifest records the run's own id, its start time and its duration
(:data:`proofpack.manifest.VOLATILE_KEYS`). This module masks those three values
(:data:`MASKED_KEYS`) in ``run.json`` and in the manifest hash, and ``run_id`` in
``pseudonyms.json``; it masks nothing else.

:func:`compare` of two run directories (moved here from ``scripts/f17_determinism.py`` at
build day 13 so the fixtures command and the reference image use the same code) hashes:

* ``run.json`` bytes with the values of ``run_id``, ``started`` and ``duration_s``
  replaced by ``"<masked>"`` - a byte-level substitution; each key must occur exactly
  once, or :func:`mask` raises (a second ``started`` cannot hide a difference);
* the manifest block's SHA-256 over canonical JSON with the same three keys masked (the
  *manifest hash* of D1's row; the egress ``manifest_sha256`` hashes ``run_id`` and so
  differs between two runs by construction: it is recorded, not compared);
* ``pseudonyms.json`` bytes with its ``run_id`` masked, ``ingest_report.json`` bytes as
  written, and the sorted list of file paths under each run directory;
* ``other_files``: the bytes, unmasked, of every file under each run directory other than
  the three above (:data:`KNOWN_FILES`), with its path (:func:`other_files_sha256`). E13
  repair 1, lens FA-B6: at 941c8e4 a ``T8.json`` of ``{"run_id": "a"}`` in one run and
  ``{"run_id": "b", "x": 1}`` in the other left ``identical`` true, because no other
  file's content was read
  (``tests/test_f17_reference_image.py::test_compare_reads_the_bytes_of_every_other_file``).

Where the two runs were made is recorded, never inferred: ``where`` names it, and
``run_platforms`` is read from each ``run.json`` manifest. Hash identity is claimed on the
reference platform only (D1 section 9). The reference-image run is the CI job
:data:`CI_JOB` (``.github/workflows/ci.yml``: two ``docker run --network none`` runs of
one image, compared by ``scripts/f17_determinism.py --compare-dirs
--require-reference-platform``), whose artefact :data:`CI_ARTEFACT` holds both
``run.json`` files and the comparison. This module does not see that run.
:func:`same_platform_repeat` is what ``proofpack fixtures`` runs itself: two in-process
runs on whatever machine runs the command - a same-platform repeat, not the reference
image.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

#: The manifest keys whose values differ between two runs of one input
#: (``proofpack.manifest.VOLATILE_KEYS``); nothing else is masked.
MASKED_KEYS = ("run_id", "started", "duration_s")
MASK = "<masked>"
_VALUE = {
    "run_id": rb'"run_id": "[0-9a-f-]{36}"',
    "started": rb'"started": "[0-9T:\-]+Z"',
    "duration_s": rb'"duration_s": [0-9.eE+\-]+',
}
#: The files :func:`compare` reads under their own rules; every other file under a run
#: directory is compared byte for byte as ``other_files``.
KNOWN_FILES = ("run.json", "pseudonyms.json", "ingest_report.json")
CI_JOB = "docker-smoke"
CI_ARTEFACT = "f17-reference-image"
CI_TEST_FILE = "tests/test_f17_reference_image.py"
#: The rows the fixtures command's own repeat uses (D1's row says 5k; the CI job runs
#: 5,000 on the reference image; 400 keeps ``proofpack fixtures`` quick).
REPEAT_ROWS = 400
SEED = 20240101


def mask(data: bytes, keys: tuple[str, ...] = MASKED_KEYS) -> bytes:
    """Replace each key's value with ``"<masked>"``; each key must occur exactly once."""
    for key in keys:
        data, n = re.subn(_VALUE[key], f'"{key}": "{MASK}"'.encode(), data)
        if n != 1:
            raise ValueError(f"{key} occurs {n} times; expected exactly once")
    return data


def masked_manifest_sha256(run_json: bytes) -> str:
    from proofpack.manifest import canonical_json  # noqa: PLC0415

    manifest = dict(json.loads(run_json.decode("utf-8"))["manifest"])
    for key in MASKED_KEYS:
        manifest[key] = MASK
    return hashlib.sha256(canonical_json(manifest)).hexdigest()


def file_names(run_dir: Path) -> list[str]:
    """The paths of the files under ``run_dir``, relative, with ``/``, sorted."""
    return sorted(p.relative_to(run_dir).as_posix() for p in run_dir.rglob("*") if p.is_file())


def other_files_sha256(run_dir: Path) -> str:
    """SHA-256 over ``path NUL sha256(bytes) LF`` of every file under ``run_dir`` whose
    relative path is not one of :data:`KNOWN_FILES`, in sorted path order."""
    h = hashlib.sha256()
    for name in file_names(run_dir):
        if name in KNOWN_FILES:
            continue
        digest = hashlib.sha256((run_dir / name).read_bytes()).hexdigest()
        h.update(name.encode("utf-8") + bytes([0]) + digest.encode("ascii") + bytes([10]))
    return h.hexdigest()


def compare(run1: Path, run2: Path, *, where: str | None = None) -> dict[str, Any]:
    """The comparison of two run directories (module docstring). ``identical`` is true
    only when every hash in ``checks`` is equal."""
    from proofpack.egress.build import manifest_sha256  # noqa: PLC0415
    from proofpack.manifest import REFERENCE_PLATFORM, platform_tag  # noqa: PLC0415

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
        "file_names": [
            hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()
            for names in (file_names(run1), file_names(run2))
        ],
        "other_files": [other_files_sha256(p) for p in (run1, run2)],
    }
    manifests = [json.loads(x.decode("utf-8"))["manifest"] for x in (ra, rb)]
    run_platforms = [m.get("platform") for m in manifests]
    return {
        "fixture": "F17",
        "where": where,
        "platform": platform_tag(),
        "run_platforms": run_platforms,
        "reference_platform": manifests[0]["reference_platform"],
        "both_runs_on_reference_platform": all(p == REFERENCE_PLATFORM for p in run_platforms)
        and all(m.get("reference_platform") is True for m in manifests),
        "masked_keys": list(MASKED_KEYS),
        "hashed_set": sorted(checks),
        "checks": {k: {"sha256": v, "equal": v[0] == v[1]} for k, v in checks.items()},
        "identical": all(v[0] == v[1] for v in checks.values()),
        "raw_bytes_equal": ra == rb,
        "egress_manifest_sha256_unmasked": [manifest_sha256(m) for m in manifests],
        "ledger_count": [m["ledger_count"] for m in manifests],
        "run_json_bytes": [len(ra), len(rb)],
        "file_names": [file_names(run1), file_names(run2)],
    }


def same_platform_repeat(work: Path, n: int = REPEAT_ROWS) -> dict[str, Any]:
    """Two in-process ``proofpack run --offline --format json`` runs of one synthetic
    cohort (seed 20240101, ``n`` rows, the F12 fixtures' declarations with telemetry off
    and a confirmed mapping), each with its own empty ``PROOFPACK_HOME``, compared. What
    ``proofpack fixtures`` runs for row F17; not the reference image."""
    from proofpack import halt_fixtures as hf  # noqa: PLC0415
    from proofpack.cli import main  # noqa: PLC0415
    from proofpack.synthetic import make_cohort  # noqa: PLC0415

    work.mkdir(parents=True, exist_ok=True)
    table = hf.write_csv(work / "synthetic.csv", make_cohort(seed=SEED, n=n))
    yml = hf.write_yaml(work / "criteria.yaml", hf.fixture_criteria())
    hf.confirm_mapping(table)
    codes = []
    for i in (1, 2):
        home = work / f"home{i}"
        home.mkdir()
        argv = ["run", "--input", str(table), "--criteria", str(yml)]
        argv += ["--out", str(work / f"run{i}"), "--offline", "--format", "json"]
        with (
            hf._environment(home),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            codes.append(main(argv))
    result = compare(
        work / "run1",
        work / "run2",
        where="proofpack fixtures, in process, on this machine: a same-platform repeat, "
        "not the reference image",
    )
    result.update(rows=n, exit_codes=codes, command="run")
    return result


def run_repeat(n: int = REPEAT_ROWS) -> dict[str, Any]:
    """:func:`same_platform_repeat` in a temporary directory (removed after)."""
    tmp = Path(tempfile.mkdtemp(prefix="proofpack-f17-"))
    try:
        return same_platform_repeat(tmp / "work", n)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
