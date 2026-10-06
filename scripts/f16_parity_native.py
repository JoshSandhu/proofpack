"""F16, the engine half (build day 13, E13): write the native parity values.

    python scripts/f16_parity_native.py [--out fixtures/f16_parity_native.json]
    python scripts/f16_parity_native.py --check     # compare the committed file, write nothing

Writes ``proofpack.parity.compute()`` with a ``generated`` block: the engine commit
(``git rev-parse HEAD`` of this checkout), whether tracked files were modified at the time
(``tree_clean``), the platform and the library versions. Run it from a clean tree, so the
recorded commit is the code that produced the values; commit the file in the next commit.
``tests/test_f16_parity_native.py`` holds the committed file equal to a fresh native run
under ``proofpack.parity.compare`` (the site's ``compareEntry`` rules).

``--check`` exits 0 when the committed file agrees with a fresh run, 1 otherwise, and
prints the per-fixture counts and the largest deviation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def generated_block() -> dict:
    from proofpack.manifest import platform_tag  # noqa: PLC0415

    head = _git("rev-parse", "HEAD")
    dirty = _git("status", "--porcelain", "--untracked-files=no")
    return {
        "engine_commit": head.stdout.strip() if head.returncode == 0 else None,
        "tree_clean": dirty.returncode == 0 and not dirty.stdout.strip(),
        "platform": platform_tag(),
        "by": "scripts/f16_parity_native.py",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="F16 engine half: the native parity values")
    ap.add_argument("--out", default=str(ROOT / "fixtures" / "f16_parity_native.json"))
    ap.add_argument("--check", action="store_true", help="compare the committed file only")
    args = ap.parse_args(argv)
    from proofpack import parity  # noqa: PLC0415

    fresh = parity.compute()
    if args.check:
        committed = json.loads(Path(args.out).read_text(encoding="utf-8"))
        result = parity.compare(committed, fresh)
        for fixture, row in result["fixtures"].items():
            print(f"{fixture}: {row}")
        print(
            f"F16 native check: {result['entries']} entries, {len(result['failures'])} "
            f"failures, {result['numeric_bit_equal']} numeric entries bit-equal; committed at "
            f"{committed['generated']['engine_commit']} on {committed['generated']['platform']}"
        )
        for f in result["failures"][:20]:
            print(f"  {f}")
        return 0 if not result["failures"] else 1
    fresh["generated"] = generated_block()
    data = json.dumps(fresh, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    Path(args.out).write_bytes(data.encode("utf-8"))
    n = sum(len(v) for v in fresh["fixtures"].values())
    print(
        f"written: {args.out} ({n} entries over {', '.join(fresh['fixtures'])}); engine "
        f"{fresh['generated']['engine_commit']} tree_clean {fresh['generated']['tree_clean']} "
        f"on {fresh['generated']['platform']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
