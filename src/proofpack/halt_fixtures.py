"""F12 (D1 section 3.2; build day 13, E13): the HALT fixtures, run through the CLI.

D1 section 3.2's F12 row: *swapped labels (AUROC 0.20); score 1.3 with probability;
y_pred mismatch on 1 row; conflicting duplicate case_id; single-class file; header-set
hash mismatch; missing classes; criterion on unknown metric; date column without
period* - each a typed HALT code, exit 3, no document written. Section 10 gate 4 asks
the same of H01-H12.

Which codes exist (:mod:`proofpack.errors`, read at build day 13):

* ``HALT_CODES`` H01-H12. H10 is flag only (``FLAG_ONLY_CODES``; ``gates.gate_h10``
  emits the warning W10 and the run exits 2), so it has no HALT fixture here. H12 is
  raised by ``proofpack compare`` only (paired mode, unmatched ``row_id``). That leaves
  eleven gate fixtures: H01-H09, H11 (``run``) and H12 (``compare``).
* ``SCHEMA_CODES`` S01-S05 and ``MAPPING_CODES`` E01 are raised as ``HaltError`` too and
  exit 3, but they are not among the twelve gates; they are listed in
  :data:`OTHER_EXIT_3_CODES` and have no fixture in this register.
* ``WARN_CODES`` W06, W10, W12-W16 are warnings (exit 2, or the run's own code for
  W14-W16); none is a HALT.

Every fixture writes its inputs into a fresh directory (a seeded synthetic cohort from
:func:`proofpack.synthetic.make_cohort`, the declarations of :func:`fixture_criteria`
and, except where the fixture is about the mapping, a confirmed ``<input>.mapping.json``
as ``proofpack map`` writes it), then runs ``proofpack run`` (or ``compare``) with
``--offline``. Before build day 13 the CLI test in ``tests/test_halt_gates.py`` wrote no
mapping, so since DEC-26 (build day 7) seven of its ten ``run`` scenarios exited 3 on
H07 ("run proofpack map first") instead of their own code, and the test read only the
exit code (measured on 5 October 2026 at 5154468: H01-H06 and H11 printed ``HALT H07``).
:func:`check` reads the printed code as well as the exit code.

"No document written" is measured as: no file under the fixture's directory (inputs,
``--out`` and the ``PROOFPACK_HOME`` the run is given) was added, removed or changed by
the run, and ``--out`` does not exist afterwards. The engine documents no file for a
halt (``errors``: "No document is written on HALT"). :func:`check` inspects those two
places only: a file written anywhere else is not seen (E13 lens 1, RG-B3: a planted
invoke that wrote ``leaked_run.json`` to another temporary directory scored ``ok``).
"""

from __future__ import annotations

import contextlib
import copy
import csv
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from proofpack.errors import EXIT_HALT, FLAG_ONLY_CODES, HALT_CODES, MAPPING_CODES, SCHEMA_CODES

#: Exit-3 codes outside the twelve gates; no fixture here (module docstring).
OTHER_EXIT_3_CODES: tuple[str, ...] = (*SCHEMA_CODES, *MAPPING_CODES)
#: The printed first line of a halt (``cli.main``): ``HALT <code>: <message>``.
HALT_LINE = re.compile(r"^HALT ([A-Z][0-9]{2}): ")
NO_DOCUMENT_LINE = "No document was written."
SEED = 20240101


def fixture_criteria(**overrides: Any) -> dict[str, Any]:
    """A complete, valid ``criteria.yaml`` mapping: ``tests/conftest.py::make_criteria()``
    with its defaults (``tests/test_f12_halt_cli.py`` holds the two equal), so the
    fixtures run from an installed wheel, where the tests directory does not exist. The
    authored fields are fixture placeholders, not a customer's criteria."""
    base: dict[str, Any] = {
        "schema_version": 1,
        "model": {
            "name": "synthetic-classifier",
            "version": "1.3",
            "prior_version": "1.2",
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
                "provenance": "prespecified_sap",
                "source": "test fixture",
            },
        ],
        "reference_standard": {"type": "reference_standard", "description": "test fixture"},
        "indeterminates": {"policy": "none_present", "values": []},
        "clustering": {"unit": "none", "declared_by": "test fixture"},
        "prevalence": [{"label": "intended-use, test", "value": 0.3, "source": "test fixture"}],
        "subgroups": [
            {"attribute": "sex", "prespecified": True, "source": "test", "reference_level": "M"},
            {
                "attribute": "age",
                "prespecified": True,
                "source": "test",
                "bands": [[0, 40], [40, 65], [65, 80], [80, 200]],
                "reference_level": "40-65",
            },
            {"attribute": "site", "prespecified": False, "reference_level": "largest"},
        ],
        "criteria": [
            {
                "id": "C1",
                "metric": "sensitivity",
                "operating_point": "op1",
                "scope": "overall",
                "statistic": "ci_lower_bound",
                "comparator": ">=",
                "value": 0.8,
                "author": "Test Author",
                "date": "2026-01-01",
                "justification": "test fixture",
            },
        ],
        "ledger": {"warn_after_acceptance_runs": 3},
        "egress": {
            "telemetry": False,
            "suppression": {"min_n": 10, "min_events": 5, "min_nonevents": 5},
        },
        "bootstrap": {"B": 200, "seed": 20240101, "interval": "percentile"},
    }
    out = copy.deepcopy(base)
    for k, v in overrides.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = v
    return out


def write_csv(path: Path, cols: dict[str, list[Any]]) -> Path:
    headers = list(cols)
    n = len(cols[headers[0]])
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(headers)
        for i in range(n):
            w.writerow([cols[h][i] for h in headers])
    return path


def write_yaml(path: Path, data: dict[str, Any]) -> Path:
    import yaml  # noqa: PLC0415

    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def confirm_mapping(csv_path: Path) -> Path:
    """The computed mapping of ``csv_path`` written beside it as ``<input>.mapping.json``
    with ``decided_by: file`` (``tests/conftest.py::confirmed_mapping``)."""
    from proofpack.io.mapping import map_headers  # noqa: PLC0415
    from proofpack.io.schema import load_table  # noqa: PLC0415

    raw = load_table(csv_path)
    m = map_headers(raw.headers, raw.columns)
    m.decided_by = "file"
    m.timestamp = "2026-10-06T00:00:00Z"
    target = csv_path.with_name(csv_path.name + ".mapping.json")
    m.write(target)
    return target


def _cohort(**kw: Any) -> dict[str, list[Any]]:
    from proofpack.synthetic import make_cohort  # noqa: PLC0415

    return make_cohort(seed=SEED, **kw)


def _run_args(d: Path, cols, crit, *, mapping: bool = True) -> list[str]:
    table = write_csv(d / "test.csv", cols)
    yml = write_yaml(d / "criteria.yaml", crit)
    if mapping:
        confirm_mapping(table)
    return ["run", "--input", str(table), "--criteria", str(yml)]


# --------------------------------------------------------------------------- the inputs


def _h01(d: Path) -> list[str]:
    # the score is declared lower-is-positive while it is higher-is-positive: AUROC < 0.5
    crit = fixture_criteria(score={"type": "probability", "orientation": "lower_is_positive"})
    return _run_args(d, _cohort(), crit)


def _h02(d: Path) -> list[str]:
    cols = _cohort()
    cols["y_true"][5] = "2"
    return _run_args(d, cols, fixture_criteria())


def _h03(d: Path) -> list[str]:
    cols = _cohort()
    cols["score"][7] = 1.3
    return _run_args(d, cols, fixture_criteria())


def _h04(d: Path) -> list[str]:
    cols = _cohort(with_y_pred=True, threshold=0.5)
    cols["y_pred"][3] = "1" if cols["y_pred"][3] == "0" else "0"
    return _run_args(d, cols, fixture_criteria())


def _h05(d: Path) -> list[str]:
    # conflicting duplicate case_id (D1 section 3.2's wording): rows 0 and 1 share a case id
    # and disagree on y_true, with clustering.unit none
    cols = _cohort(with_case_id=True)
    cols["case_id"][1] = cols["case_id"][0]
    cols["y_true"][0], cols["y_true"][1] = "1", "0"
    return _run_args(d, cols, fixture_criteria())


def _h06(d: Path) -> list[str]:
    cols = _cohort()
    cols["y_true"] = ["0"] * len(cols["y_true"])
    return _run_args(d, cols, fixture_criteria())


def _h07(d: Path) -> list[str]:
    # header-set hash mismatch: the confirmed mapping was written for the table before a
    # column was added to it
    cols = _cohort()
    table = write_csv(d / "test.csv", cols)
    confirm_mapping(table)
    cols["extra_column"] = [0] * len(cols["y_true"])
    write_csv(table, cols)
    yml = write_yaml(d / "criteria.yaml", fixture_criteria())
    return ["run", "--input", str(table), "--criteria", str(yml)]


def _h08(d: Path) -> list[str]:
    return _run_args(d, _cohort(), fixture_criteria(classes=None))


def _h09(d: Path) -> list[str]:
    crit = fixture_criteria()
    crit["criteria"][0]["metric"] = "not_a_metric"
    return _run_args(d, _cohort(), crit)


def _h11(d: Path) -> list[str]:
    cols = _cohort()
    cols["event_date"] = ["2026-01-15"] * len(cols["y_true"])
    return _run_args(d, cols, fixture_criteria())


def _h12(d: Path) -> list[str]:
    new, prior = _cohort(), _cohort()
    prior["row_id"][0] = "not-in-new"
    a = write_csv(d / "new.csv", new)
    b = write_csv(d / "prior.csv", prior)
    confirm_mapping(a)
    yml = write_yaml(d / "criteria.yaml", fixture_criteria())
    return ["compare", "--input", str(a), "--prior", str(b), "--criteria", str(yml)]


@dataclass(frozen=True)
class HaltFixture:
    code: str
    command: str
    what: str
    build: Callable[[Path], list[str]]

    @property
    def id(self) -> str:
        return f"F12-{self.code}"


#: The eleven gate fixtures (module docstring). The test suite holds this list equal to
#: ``HALT_CODES`` less ``FLAG_ONLY_CODES``.
FIXTURES: tuple[HaltFixture, ...] = (
    HaltFixture("H01", "run", "score declared lower-is-positive (AUROC below 0.5)", _h01),
    HaltFixture("H02", "run", "y_true holds '2', outside the declared classes", _h02),
    HaltFixture("H03", "run", "score 1.3 with score.type probability", _h03),
    HaltFixture("H04", "run", "y_pred differs from the operating point on 1 row", _h04),
    HaltFixture("H05", "run", "conflicting duplicate case_id, clustering none", _h05),
    HaltFixture("H06", "run", "single-class file (every y_true 0)", _h06),
    HaltFixture("H07", "run", "header-set hash differs from the confirmed mapping", _h07),
    HaltFixture("H08", "run", "the classes declaration missing", _h08),
    HaltFixture("H09", "run", "criterion C1 on an unknown metric", _h09),
    HaltFixture("H11", "run", "date column event_date with no period declared", _h11),
    HaltFixture("H12", "compare", "paired compare with one unmatched row_id", _h12),
)
#: The gate codes with no HALT fixture, and why.
NO_FIXTURE: dict[str, str] = {
    code: "flag only: gates.gate_h10 emits W10 and the run exits 2"
    for code in sorted(FLAG_ONLY_CODES & set(HALT_CODES))
}


def _snapshot(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@contextlib.contextmanager
def _environment(home: Path) -> Iterator[None]:
    saved = {k: os.environ.get(k) for k in ("PROOFPACK_HOME", "PROOFPACK_LICENCE")}
    os.environ["PROOFPACK_HOME"] = str(home)
    os.environ.pop("PROOFPACK_LICENCE", None)
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def in_process(argv: list[str], home: Path) -> tuple[int, str]:
    """``proofpack.cli.main(argv)`` with ``PROOFPACK_HOME`` set to ``home``:
    ``(exit code, stderr)``. What ``proofpack fixtures`` uses."""
    from proofpack.cli import main  # noqa: PLC0415

    err = io.StringIO()
    with (
        _environment(home),
        contextlib.redirect_stderr(err),
        contextlib.redirect_stdout(io.StringIO()),
    ):
        rc = main(argv)
    return rc, err.getvalue()


def subprocess_cli(argv: list[str], home: Path) -> tuple[int, str]:
    """``python -m proofpack.cli <argv>`` in a child process with ``PROOFPACK_HOME`` set to
    ``home``: ``(exit code, stderr)``. What ``tests/test_f12_halt_cli.py`` uses."""
    env = {k: v for k, v in os.environ.items() if k != "PROOFPACK_LICENCE"}
    env["PROOFPACK_HOME"] = str(home)
    proc = subprocess.run(
        [sys.executable, "-m", "proofpack.cli", *argv],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(home),
        timeout=600,
    )
    return proc.returncode, proc.stderr


def check(
    fixture: HaltFixture,
    work: Path,
    invoke: Callable[[list[str], Path], tuple[int, str]] = in_process,
) -> dict[str, Any]:
    """Build ``fixture``'s inputs in ``work`` (an empty directory), run it with
    ``--offline`` through ``invoke`` and return what was measured. ``ok`` is true only when
    the exit code is 3, the first stderr line names the fixture's own code, the stderr
    says no document was written, ``--out`` does not exist and no file under ``work`` was
    added, removed or changed."""
    work.mkdir(parents=True, exist_ok=True)
    home = work / "home"
    home.mkdir()
    argv = fixture.build(work)
    out = work / "pack"
    argv += ["--out", str(out), "--offline"]
    before = _snapshot(work)
    rc, stderr = invoke(argv, home)
    after = _snapshot(work)
    lines = stderr.splitlines()
    first = lines[0] if lines else ""
    m = HALT_LINE.match(first)
    printed = m.group(1) if m else None
    changed = sorted({k for k in set(before) | set(after) if before.get(k) != after.get(k)})
    result = {
        "id": fixture.id,
        "code": fixture.code,
        "command": fixture.command,
        "what": fixture.what,
        "exit_code": rc,
        "printed_code": printed,
        "no_document_line": NO_DOCUMENT_LINE in stderr,
        "out_exists": out.exists(),
        "files_changed": changed,
    }
    result["ok"] = (
        rc == EXIT_HALT
        and printed == fixture.code
        and result["no_document_line"]
        and not result["out_exists"]
        and not changed
    )
    return result


def run_all(
    invoke: Callable[[list[str], Path], tuple[int, str]] = in_process,
    fixtures: tuple[HaltFixture, ...] = FIXTURES,
) -> list[dict[str, Any]]:
    """:func:`check` on every fixture, each in its own temporary directory (removed after)."""
    results = []
    for fx in fixtures:
        tmp = Path(tempfile.mkdtemp(prefix=f"proofpack-{fx.id}-"))
        try:
            results.append(check(fx, tmp / "work", invoke))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return results
