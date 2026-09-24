"""Render T12.html from a fixtures_report.json for the release assets (A-P3, build day 9).

    python scripts/build_t12.py --report release/fixtures_report.json --out release

``proofpack fixtures --html`` writes T12 only under a usable licence (the rule T8 has). The
release workflow has no licence, so this script renders the page from the report the
workflow's own ``proofpack fixtures --offline`` wrote, with the manifest mark
``NO LICENCE - not for submission`` (DEC-48's string, as ``scripts/build_sample_pack.py``
sets for the sample pack) on every page. It reads no customer data: its one input is the
report, which holds the fixture register's values and the build machine's versions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    from proofpack.fixtures import validate_report
    from proofpack.licence.verify import WATERMARK_NO_LICENCE
    from proofpack.render.t12 import write_t12

    ap = argparse.ArgumentParser(description="T12.html from a fixtures_report.json")
    ap.add_argument("--report", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    validate_report(report)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    target = write_t12(report, args.out, watermark=WATERMARK_NO_LICENCE)
    print(f"written: {target} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
