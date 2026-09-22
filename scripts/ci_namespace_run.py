"""One full ``proofpack run`` for the CI job ``offline-namespace`` (A-P2, F19): the
synthetic cohort, a confirmed mapping and an ephemeral-key licence, inside ``unshare -rn``
(a user namespace with no network; ``.github/workflows/ci.yml``).

Two invocations, each asserting that ``run.json`` was written and exiting with the run's
own exit code:

    python scripts/ci_namespace_run.py --offline   # exit 0; "telemetry skipped (--offline)"
    python scripts/ci_namespace_run.py --online    # exit 0; the send fails (no network in
                                                   # the namespace) and prints one [W16]
                                                   # line; run.json is written all the same

The licence is signed by the test suite's ephemeral key (``tests/conftest.py``) and
verified through ``proofpack.cli.main(..., registry=...)``, the test-only hook, because
the shipped public key's signing key is a secret of the site repository that CI here does
not hold; the command, its documents and its telemetry path are otherwise the customer's.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(REPO / "src"))


def main(argv: list[str]) -> int:
    from conftest import (
        confirmed_mapping,
        ephemeral_registry,
        make_cohort,
        make_criteria,
        write_csv,
        write_licence,
        write_yaml,
    )
    from proofpack.cli import main as cli_main

    if argv[:1] not in (["--offline"], ["--online"]):
        print("usage: ci_namespace_run.py --offline | --online", file=sys.stderr)
        return 2
    offline = argv[0] == "--offline"
    work = Path(tempfile.mkdtemp(prefix="proofpack-namespace-"))
    home = work / "home"
    home.mkdir()
    os.environ["PROOFPACK_HOME"] = str(home)
    os.environ.pop("PROOFPACK_LICENCE", None)
    write_licence(home / "proofpack.lic")
    csv_path = write_csv(work / "test.csv", make_cohort())
    crit = make_criteria()
    crit["egress"]["telemetry"] = True
    yml = write_yaml(work / "criteria.yaml", crit)
    confirmed_mapping(csv_path)
    out = work / "pack"
    args = ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out)]
    if offline:
        args.append("--offline")
    rc = cli_main(args, registry=ephemeral_registry())
    written = (out / "run.json").exists()
    print(
        f"namespace run: {'--offline' if offline else '--online'} exit={rc} run.json="
        f"{'written' if written else 'MISSING'}"
    )
    if not written:
        return 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
