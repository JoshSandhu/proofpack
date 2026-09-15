"""DEC-12(ii): the mutation sweep as a committed script.

Plants a declared list of mutants - each ``(id, file, regex, replacement, expected count)``
- one at a time into a *copy* of the working tree, runs the named pytest marker there,
and prints killed / survived per mutant. A mutant is **killed** when the marker's tests
fail against it and **survived** when they all pass. A surviving mutant that is not
equivalent (i.e. it changes behaviour) is a coverage gap: close it with a test, or carry
it in the handoff note with the reason.

Why a copy and not a worktree: the sweep must run against the *working tree* (the code
being handed off, committed or not), and a git worktree can only check out a commit. The
copy holds ``src``, ``tests``, ``schema``, ``fixtures``, ``design`` and
``pyproject.toml``; ``PYTHONPATH`` is forced to the copy's ``src`` and the script
asserts that ``proofpack`` resolves there before any mutant runs, so an editable install
of the real tree cannot be what the tests import.

Usage::

    python scripts/mutation_sweep.py --marker day5            # every declared mutant
    python scripts/mutation_sweep.py --marker day5 --only ref_largest_to_smallest
    python scripts/mutation_sweep.py --list
    python scripts/mutation_sweep.py --marker day5 --fail-on-survivor   # exit 1 if any survive

The round-7 repair of build day 4 ran this by hand as a scratch file; it found that the
two changes that round's commit narrated most prominently were unobservable, which is
why it is a script now (DEC-12, Josh, 13 September 2026).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COPIED = ("src", "tests", "schema", "fixtures", "design", "pyproject.toml")
SUBGROUPS = "src/proofpack/stats/subgroups.py"
OUTPUT_SCHEMA = "schema/output_schema_v1.json"


@dataclass(frozen=True)
class Mutant:
    id: str
    file: str
    pattern: str
    replacement: str
    count: int = 1  # how many matches the pattern must have (all are replaced)
    what: str = ""  # the behaviour it changes, for the report


#: The day-5 list. Every one changes behaviour; none is intended to be equivalent.
MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        "ref_largest_to_smallest",
        SUBGROUPS,
        r"largest = max\(lv\.n for lv in candidates\)",
        "largest = min(lv.n for lv in candidates)",
        what="reference-level choice: 'largest' picks the smallest level",
    ),
    Mutant(
        "ref_tie_last_in_order",
        SUBGROUPS,
        r"return tied\[0\]\.label,",
        "return tied[-1].label,",
        what="reference tie rule: last in level order instead of first",
    ),
    Mutant(
        "unknown_row_can_be_reference",
        SUBGROUPS,
        r"candidates = \[lv for lv in levels if not lv\.is_unknown\]",
        "candidates = list(levels)",
        what="the Unknown row becomes a candidate reference level",
    ),
    Mutant(
        "complement_excludes_unknown",
        SUBGROUPS,
        r"np\.concatenate\(\[lv\.rows for lv in attr\.levels\]\)\n            if attr\.levels",
        "np.concatenate([lv.rows for lv in attr.levels if not lv.is_unknown])\n"
        "            if attr.levels",
        what="complement definition: the Unknown row is left out of every complement",
    ),
    Mutant(
        "unknown_row_not_marked",
        SUBGROUPS,
        r"levels\.append\(_Level\(attribute, UNKNOWN_LEVEL, unknown_rows, True\)\)",
        "levels.append(_Level(attribute, UNKNOWN_LEVEL, unknown_rows, False))",
        what="Unknown row membership: missing rows form a level not marked is_unknown_row",
    ),
    Mutant(
        "tier_counts_rows_not_units",
        SUBGROUPS,
        r"tier_flags = precision_flags\(n_units, event_units\)",
        "tier_flags = precision_flags(n, events)",
        what="tier thresholds measured in rows instead of resampling units",
    ),
    Mutant(
        "evaluability_ten_to_five",
        SUBGROUPS,
        r"^AUROC_EVALUABLE_CLASS = 10$",
        "AUROC_EVALUABLE_CLASS = 5",
        what="the 10/10 AUROC evaluability rule loosened to 5",
    ),
    Mutant(
        "evaluability_off_by_one",
        SUBGROUPS,
        r"if n_pos < AUROC_EVALUABLE_CLASS:",
        "if n_pos <= AUROC_EVALUABLE_CLASS:",
        what="the 10/10 rule refuses a level with exactly ten positives",
    ),
    Mutant(
        "difference_sign_flipped",
        SUBGROUPS,
        r"number = difference_unpaired\(k1, n1, k2, n2, level\)",
        "number = difference_unpaired(k2, n2, k1, n1, level)",
        what="the sign of a proportion difference (other minus level)",
    ),
    Mutant(
        "holm_no_running_maximum",
        SUBGROUPS,
        r"running = max\(running, min\(1\.0, pvalues\[i\] \* \(m - rank\)\)\)",
        "running = min(1.0, pvalues[i] * (m - rank))",
        what="Holm ordering: the step-down monotonicity is dropped",
    ),
    Mutant(
        "holm_unsorted",
        SUBGROUPS,
        r"order = sorted\(range\(m\), key=lambda i: pvalues\[i\]\)",
        "order = list(range(m))",
        what="Holm ordering: p-values are not sorted before the step-down",
    ),
    Mutant(
        "fpr_gap_sign",
        SUBGROUPS,
        r'"fpr_gap": _mirror_cell\(d\[arrays\.sp_key\]\),',
        '"fpr_gap": d[arrays.sp_key],',
        what="fpr_gap emitted as the specificity difference instead of its mirror",
    ),
    Mutant(
        "clustered_span_refusal_off",
        SUBGROUPS,
        r"if _shared_cases\(ids_a, ids_b\):",
        "if False and _shared_cases(ids_a, ids_b):",
        count=2,
        what="the clustered refusal: cases spanning both sides no longer refuse",
    ),
    Mutant(
        "proportion_cells_lose_cluster_ids",
        SUBGROUPS,
        r"cluster_ids=arrays\.ids_for\(rows\),(\n        level=arrays\.level,\n    \)"
        r"\n\n\ndef _proportion_difference)",
        r"cluster_ids=None,\1",
        what="DEC-10 / X2: proportion cells reach Wilson on clustered rows",
    ),
    Mutant(
        "fisher_branch_removed",
        SUBGROUPS,
        r"if n_levels == 2 and min_expected < fisher_below:",
        "if False:",
        what="Fisher exact never replaces the chi-square",
    ),
    Mutant(
        "selection_rate_label",
        SUBGROUPS,
        r'^SELECTION_RATE_LABEL = "descriptive_not_target"$',
        'SELECTION_RATE_LABEL = "target"',
        what="the selection-rate gap loses its R2 section 4 label",
    ),
    Mutant(
        "undeclared_not_exploratory",
        SUBGROUPS,
        r"if spec is not None else EXPLORATORY\)",
        'if spec is not None else "declared")',
        what="an undeclared attribute is no longer labelled exploratory",
    ),
    Mutant(
        "default_age_bands_changed",
        SUBGROUPS,
        r"\(\(0, 40\), \(40, 65\), \(65, 80\), \(80, 200\)\)",
        "((0, 18), (18, 40), (40, 65), (65, 80), (80, 200))",
        what="the engine-default age bands drift from D1's",
    ),
    Mutant(
        "age_bands_closed_on_the_right",
        SUBGROUPS,
        r"\(a < float\(hi\)\)",
        "(a <= float(hi))",
        what="age banding becomes [lo, hi] instead of [lo, hi)",
    ),
    Mutant(
        "schema_extension_missing_reason",
        OUTPUT_SCHEMA,
        r'"cases_span_both_groups", "insufficient_levels"',
        '"cases_span_both_groups"',
        what="the output schema no longer accepts one of the day-5 typed reasons",
    ),
    Mutant(
        "schema_extension_missing_flag",
        OUTPUT_SCHEMA,
        r'"wilson_refused_clustered", "newcombe_refused_clustered",',
        '"wilson_refused_clustered",',
        what="the output schema no longer accepts the day-5 flag",
    ),
)


def make_copy() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="proofpack-mutants-"))
    for item in COPIED:
        src = REPO / item
        if src.is_dir():
            shutil.copytree(src, tmp / item, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, tmp / item)
    return tmp


def env_for(copy: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(copy / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def assert_imports_from_copy(copy: Path) -> None:
    out = subprocess.run(
        [sys.executable, "-c", "import proofpack, sys; print(proofpack.__file__)"],
        cwd=copy,
        env=env_for(copy),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if Path(out).resolve().parent.parent != (copy / "src").resolve():
        raise SystemExit(f"proofpack resolves to {out}, not the copy under {copy / 'src'}")


def plant(copy: Path, mutant: Mutant) -> None:
    target = copy / mutant.file
    original = (REPO / mutant.file).read_text(encoding="utf-8")
    mutated, n = re.subn(mutant.pattern, mutant.replacement, original, flags=re.M)
    if n != mutant.count:
        raise SystemExit(
            f"mutant {mutant.id}: pattern matched {n} time(s) in {mutant.file}, expected "
            f"{mutant.count} - the code moved; update the mutant list"
        )
    target.write_text(mutated, encoding="utf-8")


def restore(copy: Path, mutant: Mutant) -> None:
    shutil.copy2(REPO / mutant.file, copy / mutant.file)


def run_marker(copy: Path, marker: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", "-m", marker],
        cwd=copy,
        env=env_for(copy),
        capture_output=True,
        text=True,
    )
    tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-3:])
    return proc.returncode, tail


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="plant declared mutants and run a pytest marker")
    ap.add_argument("--marker", default="day5")
    ap.add_argument("--only", action="append", help="mutant id(s) to run")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fail-on-survivor", action="store_true")
    args = ap.parse_args(argv)
    chosen = [m for m in MUTANTS if not args.only or m.id in args.only]
    if args.list:
        for m in MUTANTS:
            print(f"{m.id:<36} {m.file:<36} {m.what}")
        return 0
    copy = make_copy()
    try:
        assert_imports_from_copy(copy)
        rc, tail = run_marker(copy, args.marker)
        if rc != 0:
            print(f"baseline (no mutant) does not pass -m {args.marker}; refusing to sweep\n{tail}")
            return 2
        print(f"baseline: -m {args.marker} passes in the copy at {copy}\n")
        survivors = []
        t0 = time.time()
        for m in chosen:
            plant(copy, m)
            rc, tail = run_marker(copy, args.marker)
            restore(copy, m)
            status = "killed" if rc != 0 else "SURVIVED"
            if rc == 0:
                survivors.append(m)
            print(f"{status:<9} {m.id:<36} {m.what}")
            if rc != 0:
                print(f"          {tail.splitlines()[-1][:110]}")
        killed = len(chosen) - len(survivors)
        print(
            f"\n{len(chosen)} planted, {killed} killed, {len(survivors)} survived; "
            f"{time.time() - t0:.0f} s"
        )
        for m in survivors:
            print(f"  survivor: {m.id} - {m.what}")
        return 1 if survivors and args.fail_on_survivor else 0
    finally:
        shutil.rmtree(copy, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
