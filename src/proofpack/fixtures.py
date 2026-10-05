"""``proofpack fixtures`` (D1 section 7; A-P3, build day 9): the fixture register F1-F21
run through the engine's own functions, each compared with its recorded oracle, written
as ``fixtures_report.json`` (schema: ``schema/fixtures_report_schema.json``).

What one report row says, and nothing more: which engine values were compared with which
recorded values, under which tolerance class of D1 section 9, the largest absolute
deviation observed, and ``matched`` true or false. The engine chooses no acceptance
criterion here: the tolerance classes are D1 section 9's, the oracles are the files named
in each row, and a row is ``matched`` only when every compared value lies within its
tolerance. The five row statuses:

* ``matched`` / ``not_matched`` - a value comparison was made (``not_matched`` also when
  the engine raised, or an optional dependency the comparison needs is absent: the row
  carries the typed ``reason``);
* ``no_oracle_recorded`` - no oracle file exists for the fixture yet (F13, F13b: the R
  captures ``fixtures/r/capture.R`` writes, absent until one is committed:
  :data:`F13_ABSENT`, :data:`F13B_ABSENT`; never read from an installed wheel:
  :data:`R_CAPTURES_NOT_READ`. F13 outside the r-captures job, once committed, is
  ``suite_only``: the comparison as that job recorded it, :func:`f13_oracle`), or F14's
  Newcombe file
  is not read (the package is not ``<root>/src/proofpack`` of a ``pyproject.toml`` naming
  ``proofpack``: :data:`NEWCOMBE_ABSENT`); never matched;
* ``not_built`` - the engine has no function for the fixture in this version (F5, F7,
  F15, F16, F21, F3's AUPRC); never matched;
* ``suite_only`` - a behaviour the test suite inspects (F12, F17-F20; the row names the
  test file) and this command does not re-run; never matched. F13 outside the r-captures
  job, when ``proc_asah.json`` and :data:`R_COMPARISON_FILE` are committed and agree,
  carries it too: the comparison was made inside that job (DEC-77), not by this command.

Exit code (:func:`exit_code_for`): ``EXIT_OK`` (0) when every row with an oracle is
``matched``, :data:`proofpack.errors.EXIT_FIXTURES_NOT_MATCHED` (6) when one or more is
``not_matched``. ``no_oracle_recorded``, ``not_built`` and ``suite_only`` rows do not move
the exit code and are never counted as matched
(``tests/test_fixtures_cmd.py::test_rows_without_an_oracle_are_never_counted_as_matched``).

:func:`compare_row` iterates over the value names the row declares (``Row.compares``)
together with the oracle's own keys.
``tests/test_ap3_repair2.py::test_a_deleted_oracle_value_is_not_matched_and_exits_6``
deletes ``captured.F1-wilson.values.wilson_lo``, ``register.F1.wilson_lo`` and the
Newcombe example ``9/10 - 3/10`` in turn; each gives its row ``not_matched`` with
``oracle value missing: <name>``, and exit 6.

Tolerances (:data:`TOLERANCES`): D1 section 9's ``closed_form`` 1e-9 and ``iterative`` 1e-6
against the captured oracles; ``reported_rounding`` (half a unit in the last printed
decimal of each value, plus 1e-12) for the bootstrap intervals and the Newcombe table;
``register`` 1e-4 for the D1 section 3.2 register values, the tolerance D1 section 3.2
states for them. The register's printed F3 logit lower bound 0.3748 is 5.8e-5 from the
engine's 0.374858 and from the captured O(m n) DeLong oracle's (both print 0.3749): it
lies within the register's 1e-4 and outside half a unit of its fourth decimal.

``git_sha`` (:func:`git_sha`) is read with ``git rev-parse HEAD`` only in a directory whose
``src/proofpack`` is the imported package and whose ``pyproject.toml`` names the project
``proofpack``; otherwise it is ``null`` with the reason
(``tests/test_ap3_repair1.py::test_git_sha_is_null_for_a_wheel_vendored_inside_another_git_repository``).
"""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from proofpack import __version__
from proofpack.errors import EXIT_FIXTURES_NOT_MATCHED, EXIT_OK
from proofpack.manifest import REFERENCE_PLATFORM, platform_tag, scipy_version, utc_now_iso
from proofpack.resources import resource_path

REPORT_FILE = "fixtures_report.json"
REPORT_SCHEMA_ID = "proofpack-fixtures-report/1"
#: D1 section 9. ``reported_rounding`` has no single number: see :func:`rounding_tolerance`.
TOLERANCES: dict[str, float | None] = {
    "closed_form": 1e-9,
    "iterative": 1e-6,
    "reported_rounding": None,
    "register": 1e-4,
}
#: The rule each class applies, printed in the report and in T12.
TOLERANCE_RULES: dict[str, str] = {
    "closed_form": "absolute deviation at most 1e-9. D1 section 9 gives 1e-9 for closed "
    "forms and lists Wilson, 2x2, Brier, O/E and PSI; this report applies it to the rows "
    "F1-wilson, F1b-wilson, F1c-wilson, F1d-wilson, F2-exact, F3-auroc, F4-closed-form, "
    "F5-mcnemar, F6-closed-form, F8-half-width, F10-exact and F11-ppa-npa",
    "iterative": "absolute deviation at most 1e-6. D1 section 9 gives 1e-6 for iterative "
    "methods and lists IRLS slope/intercept and DeLong via placements; this report applies "
    "it to the rows F1-clopper-pearson, F1b-clopper-pearson, F1c-clopper-pearson, "
    "F1d-clopper-pearson, F3-delong, F4-irls, F5-delong-pair and F6-p, to F13 (pROC on "
    "aSAH) inside the r-captures job, where the aSAH vectors exist (DEC-77), and to F13b "
    "(rms::val.prob and glm on fixtures/f4_calibration.csv) when its R capture is present",
    "reported_rounding": "absolute deviation at most half a unit in the last printed decimal "
    "of each value, plus 1e-12. D1 section 9 gives reported rounding for bootstrap CIs; this "
    "report applies it to the rows F3-bootstrap, F9-cluster-bootstrap, F14-newcombe (a "
    "published table, for which D1 section 9 gives no tolerance) and F5-newcombe-paired (a "
    "published table too, read from the primary PDF on build day 11)",
    "register": "absolute deviation at most 1e-4 on the printed value (D1 section 3.2: "
    "'tolerance 1e-4 on the shown rounding')",
}
#: Where each class's number is written. :data:`TOLERANCE_RULES` lists the rows each class
#: is applied to (``tests/test_ap3_repair2.py::test_each_tolerance_rule_lists_its_rows``).
TOLERANCE_SOURCE = (
    "D1 section 9 (closed_form, iterative, reported_rounding); D1 section 3.2 (register)"
)
ROUNDING_SLACK = 1e-12
#: ``no_independent_oracle`` (build day 10, E10): a frozen engine value with no oracle
#: outside the engine: never ``matched`` against itself, never ``not_matched``; it does not
#: move the exit code. F5's Newcombe paired interval carried it on day 10; since build day
#: 11 (E11 item 4) that row is compared with the paper's Table III and no row carries it.
STATUSES = (
    "matched",
    "not_matched",
    "no_oracle_recorded",
    "no_independent_oracle",
    "not_built",
    "suite_only",
)
#: The R captures D1 section 3.2 names (F13, F13b), written by ``fixtures/r/capture.R``
#: (build day 12) and read only from a source checkout (:func:`r_captures_dir`).
R_CAPTURE_FILES = ("fixtures/r/proc_asah.json", "fixtures/r/rms_val_prob_f4.json")
#: DEC-77 (Josh, 5 October 2026): pROC's aSAH rows are never committed and never leave the
#: GitHub runner. ``capture.R`` writes them to the file this environment variable names,
#: in the runner's temporary space. :func:`load_r_captures` reads the vectors from the path
#: this variable names, whatever it is: nothing in Python refuses a path inside the checkout
#: (``tests/test_e12_repair4.py::test_fa_b4_the_loader_reads_vectors_named_inside_fixtures_r``
#: names ``<capture dir>/asah_vectors.csv`` and reads its 80 rows). ``.gitignore`` lists
#: ``fixtures/r/*.csv`` and ``*asah*vectors*``.
R_VECTORS_ENV = "PROOFPACK_ASAH_VECTORS"
#: How the vectors file is named in ``unreadable``, ``present`` and row reasons.
R_VECTORS_FILE = f"${R_VECTORS_ENV} (asah_vectors.csv)"
#: What the r-captures job records of its own F13 comparison (aggregates and the vectors'
#: sha256 only, :func:`f13_comparison_record`), committed beside ``proc_asah.json``.
R_COMPARISON_FILE = "fixtures/r/f13_engine_comparison.json"
R_COMPARISON_SCHEMA = "proofpack-r-f13-comparison/1"
R_CAPTURES_NOT_CAPTURED = "r_captures_not_captured"
#: The typed skip reason of the F13 comparisons that need the aSAH vectors, when
#: :data:`R_VECTORS_ENV` is not set (DEC-77: everywhere outside the r-captures job).
R_VECTORS_NOT_COMMITTED = "r_vectors_not_committed_dec77"

F2_COUNTS = (90, 10, 20, 180)
F3_Y = (1, 1, 1, 1, 1, 0, 0, 0, 0, 0)
F3_S1 = (0.9, 0.8, 0.7, 0.6, 0.35, 0.75, 0.5, 0.4, 0.3, 0.2)
F3_S2 = (0.85, 0.6, 0.65, 0.4, 0.3, 0.7, 0.55, 0.45, 0.35, 0.25)
F3_SEED = 20240101
F3_B = 2000
F6_SITES = ((45, 5), (38, 12), (27, 3))
F6_HOLM_INPUT = (0.012, 0.04, 0.30)
F1_CASES = {"F1": (81, 263), "F1b": (490, 500), "F1c": (0, 20), "F1d": (20, 20)}
#: F14's three worked examples (k1, n1, k2, n2), labelled "k1/n1 - k2/n2" in the file.
F14_CASES = ((56, 70, 48, 80), (9, 10, 3, 10), (10, 10, 0, 20))

#: The value names each compared row declares (``Row.compares``). Lens FA2-B1: the
#: compared set was the oracle file's own keys, so a value deleted from the file was not
#: compared and the row read matched.
WILSON_NAMES = ("wilson_lo", "wilson_hi")
CP_NAMES = ("cp_lo", "cp_hi")
F2_NAMES = (
    "sensitivity",
    "specificity",
    "ppv",
    "npv",
    "prevalence",
    "lr_pos",
    "lr_neg",
    "dor",
    "youden",
    "f1",
    "mcc",
    "sensitivity_ci_lo",
    "sensitivity_ci_hi",
    "specificity_ci_lo",
    "specificity_ci_hi",
    "ppv_at_0.05",
    "npv_at_0.05",
)
F3_AUROC_NAMES = ("auc_s1", "auc_s2")
F3_DELONG_NAMES = (
    "delong_se_s1",
    "delong_se_s2",
    "logit_ci_lo_s1",
    "logit_ci_hi_s1",
    "wald_ci_lo_s1",
    "wald_ci_hi_s1",
    "paired_var_diff",
    "paired_z",
    "paired_p",
)
F3_REGISTER_NAMES = F3_AUROC_NAMES + tuple(n for n in F3_DELONG_NAMES if n != "delong_se_s2")
BOOTSTRAP_NAMES = ("ci_lo", "ci_hi")
F5_MCNEMAR_NAMES = ("mcnemar_exact_p", "cc_chi2", "cc_chi2_p")
F5_REGISTER_NAMES = F5_MCNEMAR_NAMES + ("accuracy_diff",)
#: E11 item 4: the cell sets of Newcombe 1998 (paired) Table III, method 10, with the sides
#: the transcription compares (``fixtures/newcombe1998_paired.json``; the lower limit of
#: e 1 f 97 g 1 h 1 is recorded there as excluded, with the reason).
F5_NEWCOMBE_PAIRED_CASES: tuple[tuple[int, int, int, int, tuple[str, ...]], ...] = tuple(
    (*cells, ("upper",) if cells == (1, 97, 1, 1) else ("lower", "upper"))
    for cells in (
        (36, 12, 2, 0),
        (20, 12, 2, 16),
        (18, 12, 2, 18),
        (36, 14, 0, 0),
        (35, 14, 0, 1),
        (18, 14, 0, 18),
        (2, 97, 1, 0),
        (1, 97, 1, 1),
        (0, 29, 1, 0),
        (2, 98, 0, 0),
        (1, 98, 0, 1),
        (0, 30, 0, 0),
        (54, 0, 0, 0),
        (53, 0, 0, 1),
        (30, 0, 0, 24),
        (29, 0, 0, 25),
        (28, 0, 0, 26),
        (27, 0, 0, 27),
    )
)
F5_NEWCOMBE_PAIRED_NAMES = tuple(
    f"e {e} f {f} g {g} h {h} method10 {side}"
    for e, f, g, h, sides in F5_NEWCOMBE_PAIRED_CASES
    for side in sides
)
F5_DELONG_PAIR_NAMES = ("est", "var_diff", "ci_lo", "ci_hi")
F4_CLOSED_NAMES = (
    "oe",
    "oe_ci_lo",
    "oe_ci_hi",
    "brier",
    "brier_ref",
    "ipa",
    "ece_equal_width_10",
    "ece_equal_mass_10",
)
F4_IRLS_NAMES = (
    "intercept_large",
    "intercept_large_se",
    "slope",
    "slope_se",
    "intercept",
    "intercept_se",
)
F4_REGISTER_NAMES = (
    "brier",
    "brier_ref",
    "ipa",
    "oe",
    "intercept_large",
    "slope",
    "intercept",
    "ece_10_equal_width",
    "ece_10_equal_mass",
)
F6_CLOSED_NAMES = ("se_site1", "se_site2", "se_site3", "chi2", "holm_1", "holm_2", "holm_3")
F6_REGISTER_NAMES = (*F6_CLOSED_NAMES, "chi2_p")
F8_NAMES = ("half_width_n50", "half_width_n100", "half_width_n300")
F10_NAMES = (
    "as_positive_sensitivity",
    "as_positive_specificity",
    "as_negative_sensitivity",
    "as_negative_specificity",
)
F11_NAMES = ("ppa", "ppa_ci_lo", "ppa_ci_hi", "npa", "npa_ci_lo", "npa_ci_hi")
F14_NAMES = tuple(
    f"{k1}/{n1} - {k2}/{n2} {method} {side}"
    for k1, n1, k2, n2 in F14_CASES
    for method in ("method10", "method11")
    for side in ("lower", "upper")
)


def rounding_tolerance(decimals: int) -> float:
    """Half a unit in the last printed decimal, plus :data:`ROUNDING_SLACK`."""
    return 0.5 * 10.0 ** (-int(decimals)) + ROUNDING_SLACK


# ----------------------------------------------------------------------- oracle files


class OracleFileMissing(LookupError):
    """An oracle file other than the Newcombe table is not in this install: every row that
    cites it is ``not_matched`` with reason ``oracle_file_missing: <file>``."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(name)


class OracleFileUnreadable(ValueError):
    """An oracle file is present and does not parse (lens RG2-N3: a truncated
    ``oracles_v1.json``): every row that cites it is ``not_matched`` with reason
    ``oracle_file_unreadable: <file> (<error type>)``."""

    def __init__(self, name: str, error: str) -> None:
        self.name = name
        self.error = error
        super().__init__(f"{name} ({error})")


class Oracles(dict):
    """The loaded oracle files. Looking up a file that did not load raises
    :class:`OracleFileUnreadable` when it was present and did not parse, and
    :class:`OracleFileMissing` otherwise (a ``KeyError`` would read as an engine error)."""

    def __init__(self) -> None:
        super().__init__()
        self.unreadable: dict[str, str] = {}

    def __missing__(self, key: str) -> Any:
        if key in self.unreadable:
            raise OracleFileUnreadable(key, self.unreadable[key])
        raise OracleFileMissing(key)


NEWCOMBE_FILE = "newcombe_table2.json"
#: E11 item 4 (DEC-70 (a)): Table III of Newcombe 1998 (paired data), transcribed from the
#: primary PDF on 2 October 2026 (provenance inside the file); packaged as
#: ``proofpack/_fixtures/newcombe1998_paired.json``.
NEWCOMBE_PAIRED_FILE = "newcombe1998_paired.json"


def load_oracles() -> dict[str, Any]:
    """The committed oracle files, keyed by the file name each row cites. A file that is
    absent is left out of the mapping (F14's Newcombe table: :data:`NEWCOMBE_ABSENT`; the
    others: :class:`OracleFileMissing` when a row looks it up); a file that raises
    ``ValueError`` when parsed is named in ``unreadable``. The Newcombe table is read from
    ``<root>/fixtures/newcombe_table2.json`` only when :func:`source_checkout_root` returns
    ``<root>`` (lens FA2-R2: a wheel installed with ``pip --target X/src`` read
    ``X/fixtures/newcombe_table2.json``)."""
    out = Oracles()
    paths: dict[str, Callable[[], Path]] = {
        "oracles_v1.json": lambda: resource_path("oracles_v1.json"),
        "f4_expected.json": lambda: resource_path("f4_expected.json"),
        NEWCOMBE_PAIRED_FILE: lambda: resource_path(NEWCOMBE_PAIRED_FILE),
    }
    root = source_checkout_root()
    if root is not None:
        paths[NEWCOMBE_FILE] = lambda: root / "fixtures" / NEWCOMBE_FILE
    for name, where in paths.items():
        try:
            out[name] = json.loads(where().read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except ValueError as exc:  # JSONDecodeError, UnicodeDecodeError
            out.unreadable[name] = type(exc).__name__
    return out


#: F14's reason when the Newcombe table is not read: the package is not
#: ``<root>/src/proofpack`` of a ``pyproject.toml`` naming ``proofpack`` (an installed
#: wheel), or that checkout has no ``fixtures/newcombe_table2.json``. The transcription is
#: [unverified against the primary PDF] and is not packaged
#: (``tests/test_invariants.py::test_the_fixture_is_not_packaged_into_the_wheel``).
NEWCOMBE_ABSENT = (
    "[unverified against the primary PDF] fixtures/newcombe_table2.json is not shipped in "
    "the wheel (an unverified transcription stays out of the package); it is read only when "
    "the package is <root>/src/proofpack and <root>/pyproject.toml names proofpack"
)


class OracleAbsent(LookupError):
    """The oracle file a row cites is not present in this install."""


def _f4_rows() -> tuple[np.ndarray, np.ndarray]:
    lines = [
        ln
        for ln in resource_path("f4_calibration.csv").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    p, y = [], []
    for r in csv.DictReader(lines):
        p.append(float(r["score"]))
        y.append(int(r["y_true"]))
    return np.array(p, dtype=np.float64), np.array(y, dtype=bool)


def _register(oracles: dict[str, Any], key: str) -> tuple[dict[str, float], dict[str, float]]:
    """A register entry and the per-value tolerance its printed decimals give."""
    doc = oracles["oracles_v1.json"]
    values = doc["register"][key]
    dec = doc["register_decimals"][key]
    if key == "F3_bootstrap":  # a bootstrap interval: D1 section 9's reported rounding
        tol = {
            k: rounding_tolerance(dec if isinstance(dec, int) else dec.get(k, dec["_default"]))
            for k in values
        }
    else:
        tol = {k: float(TOLERANCES["register"]) for k in values}  # type: ignore[arg-type]
    return values, tol


# ------------------------------------------------------------------- engine values


def _f1_wilson(k: int, n: int) -> dict[str, float]:
    from proofpack.stats.proportions import proportion

    num = proportion(k, n)
    return {"wilson_lo": num.ci_lo, "wilson_hi": num.ci_hi}


def _f1_cp(k: int, n: int) -> dict[str, float]:
    from proofpack.stats.proportions import clopper_pearson_bounds

    bounds = clopper_pearson_bounds(k, n)
    if bounds is None:
        raise OptionalDependencyMissing("scipy")
    return {"cp_lo": bounds[0], "cp_hi": bounds[1]}


def _f2() -> dict[str, float]:
    from proofpack.stats.proportions import (
        Table2x2,
        npv_at_prevalence,
        ppv_at_prevalence,
        two_by_two_metrics,
    )

    t = Table2x2(*F2_COUNTS)
    m = two_by_two_metrics(t)
    out = {
        k: m[k].est
        for k in (
            "sensitivity",
            "specificity",
            "ppv",
            "npv",
            "prevalence",
            "lr_pos",
            "lr_neg",
            "dor",
            "youden",
            "f1",
            "mcc",
        )
    }
    for key in ("sensitivity", "specificity"):
        out[f"{key}_ci_lo"], out[f"{key}_ci_hi"] = m[key].ci_lo, m[key].ci_hi
    out["ppv_at_0.05"] = ppv_at_prevalence(t, 0.05).est
    out["npv_at_0.05"] = npv_at_prevalence(t, 0.05).est
    return out


def _f3_arrays() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.array(F3_S1, dtype=np.float64),
        np.array(F3_S2, dtype=np.float64),
        np.array(F3_Y, dtype=bool),
    )


def _f3_auroc() -> dict[str, float]:
    from proofpack.stats.discrimination import auroc_mann_whitney

    s1, s2, y = _f3_arrays()
    return {"auc_s1": auroc_mann_whitney(s1, y), "auc_s2": auroc_mann_whitney(s2, y)}


def _f3_delong() -> dict[str, float]:
    from proofpack.stats.discrimination import auroc_number, paired_delong, wald_ci

    s1, s2, y = _f3_arrays()
    a, b = auroc_number(s1, y), auroc_number(s2, y)
    paired = paired_delong(s1, s2, y)
    return {
        "delong_se_s1": a.se,
        "delong_se_s2": b.se,
        "logit_ci_lo_s1": a.auroc.ci_lo,
        "logit_ci_hi_s1": a.auroc.ci_hi,
        # wald_ci before the unit-range clip the rendered secondary Number applies (its
        # flag wald_interval_exceeds_unit_range): the register prints 1.1036
        "wald_ci_lo_s1": wald_ci(a.auroc.est, a.se)[0],
        "wald_ci_hi_s1": wald_ci(a.auroc.est, a.se)[1],
        "paired_var_diff": paired.variance_difference,
        "paired_z": paired.z,
        "paired_p": paired.p_value,
    }


def _f3_register_values() -> dict[str, float]:
    out = _f3_delong()
    out.update(_f3_auroc())
    return {k: v for k, v in out.items() if k != "delong_se_s2"}


def _bootstrap_auroc(cluster: bool) -> dict[str, float]:
    from proofpack.stats.bootstrap import (
        bootstrap_percentile,
        clustered_by_case,
        stratified_by_outcome,
    )
    from proofpack.stats.discrimination import auroc_mann_whitney

    s, _, y = _f3_arrays()
    if cluster:
        s, y = np.repeat(s, 3), np.repeat(y, 3)
        resampler = clustered_by_case(y, np.repeat(np.arange(10), 3))
    else:
        resampler = stratified_by_outcome(y)
    draw = bootstrap_percentile(
        lambda i: auroc_mann_whitney(s[i], y[i]),
        resampler,
        np.random.default_rng(F3_SEED),
        F3_B,
    )
    return {"ci_lo": draw.ci_lo, "ci_hi": draw.ci_hi}


#: The declarations F4's calibration block is computed under: a probability score,
#: higher is positive, no clustering. Only the F4 row reads it; it is the engine's
#: fixture input, not a customer's declaration.
F4_DECLARATIONS: dict[str, Any] = {
    "schema_version": 1,
    "model": {"name": "fixture-F4", "version": "1", "prior_version": None, "udi_di": None},
    "task": "binary",
    "classes": {"positive": "1", "negative": "0"},
    "score": {"type": "probability", "orientation": "higher_is_positive"},
    "operating_points": [
        {
            "id": "op1",
            "threshold": 0.5,
            "rule": ">=",
            "provenance": "other",
            "source": "fixture F4 (R2 section 9)",
        }
    ],
    "reference_standard": {"type": "reference_standard", "description": "fixture F4"},
    "indeterminates": {"policy": "none_present", "values": []},
    "clustering": {"unit": "none", "declared_by": "fixture F4"},
    "prevalence": [{"label": "fixture F4", "value": 0.6, "source": "fixture F4"}],
    "subgroups": [{"attribute": "site", "prespecified": False, "reference_level": "largest"}],
    "criteria": [],
}


def _f5_mcnemar() -> dict[str, float]:
    """R2 section 9 F5 through ``stats.comparison.mcnemar``: the exact route (the one the
    engine takes at b + c = 12) and the continuity-corrected route forced on the same
    table, so both printed figures are compared."""
    from proofpack.stats.comparison import mcnemar

    exact = mcnemar(10, 2, exact=True)
    cc = mcnemar(10, 2, exact=False)
    return {
        "mcnemar_exact_p": exact.p,
        "cc_chi2": float(cc.statistic),
        "cc_chi2_p": cc.p,
    }


def _f5_register_values() -> dict[str, float]:
    from proofpack.stats.proportions import difference_paired

    return {**_f5_mcnemar(), "accuracy_diff": difference_paired(80, 2, 10, 8).est}


def _f5_delong_pair() -> dict[str, float]:
    """The paired DeLong difference on the F3 pair (``paired_delong``, Sun and Xu)."""
    from proofpack.stats.discrimination import paired_delong

    s1, s2, y = _f3_arrays()
    r = paired_delong(s1, s2, y)
    return {
        "est": float(r.difference.est),
        "var_diff": r.variance_difference,
        "ci_lo": float(r.difference.ci_lo),
        "ci_hi": float(r.difference.ci_hi),
    }


def _f4_block() -> dict[str, Any]:
    from proofpack.io.declare import validate_dict
    from proofpack.stats.bootstrap import BootstrapPolicy
    from proofpack.stats.calibration import calibration_block

    p, y = _f4_rows()
    res = calibration_block(
        p,
        y,
        validate_dict(json.loads(json.dumps(F4_DECLARATIONS))),
        policy=BootstrapPolicy(n_resamples=200, seed=F3_SEED),
    )
    if res.block is None:
        raise RuntimeError(f"calibration suppressed: {res.suppressed_reason}")
    return res.block


def _f4_closed() -> dict[str, float]:
    b = _f4_block()
    return {
        "oe": b["oe"]["number"]["est"],
        "oe_ci_lo": b["oe"]["number"]["ci_lo"],
        "oe_ci_hi": b["oe"]["number"]["ci_hi"],
        "brier": b["brier"]["number"]["est"],
        "brier_ref": b["brier_ref"]["number"]["est"],
        "ipa": b["ipa"]["number"]["est"],
        "ece_equal_width_10": b["ece_equal_width_10"]["number"]["est"],
        "ece_equal_mass_10": b["ece_equal_mass_10"]["number"]["est"],
    }


def _f4_irls() -> dict[str, float]:
    b = _f4_block()
    return {
        "intercept_large": b["intercept_large"]["number"]["est"],
        "intercept_large_se": b["intercept_large"]["detail"]["wald_se"],
        "slope": b["slope"]["number"]["est"],
        "slope_se": b["slope"]["detail"]["wald_se"],
        "intercept": b["intercept"]["number"]["est"],
        "intercept_se": b["intercept"]["detail"]["wald_se"],
    }


def _f4_register_values() -> dict[str, float]:
    closed, irls = _f4_closed(), _f4_irls()
    return {
        "brier": closed["brier"],
        "brier_ref": closed["brier_ref"],
        "ipa": closed["ipa"],
        "oe": closed["oe"],
        "intercept_large": irls["intercept_large"],
        "slope": irls["slope"],
        "intercept": irls["intercept"],
        "ece_10_equal_width": closed["ece_equal_width_10"],
        "ece_10_equal_mass": closed["ece_equal_mass_10"],
    }


def _f6_closed() -> dict[str, float]:
    from proofpack.stats.proportions import proportion
    from proofpack.stats.subgroups import heterogeneity_footnote, holm

    out = {f"se_site{i + 1}": proportion(s, s + f).est for i, (s, f) in enumerate(F6_SITES)}
    foot = heterogeneity_footnote(
        {"op1": {"sensitivity": [tuple(c) for c in F6_SITES]}}, clustering_route="none"
    )
    test = foot["tests"][0]
    if test["not_estimable_reason"] == "scipy_unavailable":
        raise OptionalDependencyMissing("scipy")
    out["chi2"] = test["statistic"]
    out.update({f"holm_{i + 1}": v for i, v in enumerate(holm(list(F6_HOLM_INPUT)))})
    out["_chi2_p"] = test["p_raw"]
    return out


def _f6_p() -> dict[str, float]:
    return {"chi2_p": _f6_closed()["_chi2_p"]}


def _f6_register_values() -> dict[str, float]:
    out = _f6_closed()
    out["chi2_p"] = out.pop("_chi2_p")
    return out


def _f8() -> dict[str, float]:
    from proofpack.stats.proportions import proportion

    out = {}
    for n in (50, 100, 300):
        num = proportion(round(0.9 * n), n)
        out[f"half_width_n{n}"] = (num.ci_hi - num.ci_lo) / 2
    return out


def _f10() -> dict[str, float]:
    from proofpack.stats.proportions import Table2x2, indeterminate_both_ways, two_by_two_metrics

    both = indeterminate_both_ways(Table2x2(*F2_COUNTS), 6, 4)
    out = {}
    for side, t in (("as_positive", both.as_positive), ("as_negative", both.as_negative)):
        m = two_by_two_metrics(t)
        out[f"{side}_sensitivity"] = m["sensitivity"].est
        out[f"{side}_specificity"] = m["specificity"].est
    return out


def _f11() -> dict[str, float]:
    from proofpack.stats.proportions import Table2x2, two_by_two_metrics

    m = two_by_two_metrics(Table2x2(*F2_COUNTS), reference_standard_type="comparator")
    out = {}
    for key in ("ppa", "npa"):
        out[key] = m[key].est
        out[f"{key}_ci_lo"], out[f"{key}_ci_hi"] = m[key].ci_lo, m[key].ci_hi
    return out


def _paired_rows(doc: dict[str, Any]) -> list[tuple[str, float]]:
    out = []
    for row in doc["rows"]:
        cells = f"e {row['e']} f {row['f']} g {row['g']} h {row['h']}"
        for side in ("lower", "upper"):
            if side in row["method10"]:
                out.append((f"{cells} method10 {side}", float(row["method10"][side])))
    return out


def _f5_newcombe_paired() -> dict[str, float]:
    """``proportions.difference_paired`` (Newcombe 1998 paired, method 10) on every cell
    set of the paper's Table III that the transcription carries."""
    from proofpack.stats.proportions import difference_paired

    out = {}
    for e, f, g, h, sides in F5_NEWCOMBE_PAIRED_CASES:
        num = difference_paired(e, f, g, h)
        for side in sides:
            out[f"e {e} f {f} g {g} h {h} method10 {side}"] = float(
                num.ci_lo if side == "lower" else num.ci_hi
            )
    return out


def _f5_newcombe_paired_oracle(o: dict[str, Any]):
    doc = o[NEWCOMBE_PAIRED_FILE]
    values = dict(_paired_rows(doc))
    excluded = "; ".join(
        f"e {x['e']} f {x['f']} g {x['g']} h {x['h']} {x['value']} not compared: printed "
        f"{x['printed']}, method 8 of the same row printed {x['printed_method8_same_row']}"
        for x in doc.get("excluded") or []
    )
    return (
        values,
        {k: rounding_tolerance(int(doc["decimals"])) for k in values},
        {
            "kind": "published_table",
            "file": f"fixtures/{NEWCOMBE_PAIRED_FILE}",
            "entry": "rows",
            "detail": f"{doc['primary_reference']}; Table III, method 10, transcribed from "
            f"the primary PDF ({doc['provenance']['captured']}); {excluded}",
            "library_versions": None,
            "unverified": False,
            "marking": None,
        },
    )


def _f14() -> dict[str, float]:
    from proofpack.stats.proportions import newcombe10_bounds, newcombe11_bounds

    out = {}
    for k1, n1, k2, n2 in F14_CASES:
        for method, fn in (("method10", newcombe10_bounds), ("method11", newcombe11_bounds)):
            lo, hi = fn(k1, n1, k2, n2)
            out[f"{k1}/{n1} - {k2}/{n2} {method} lower"] = lo
            out[f"{k1}/{n1} - {k2}/{n2} {method} upper"] = hi
    return out


# ------------------------------------------------------------------ the R captures


class RCaptureInputMismatch(ValueError):
    """An R capture is present and was computed on other inputs than the engine is given
    (a sha256 that differs, another schema or fixture id, no ``values`` object): the row
    is ``not_matched`` with reason ``r_capture_input_mismatch: <what differs>``."""


class WithheldVectors(dict):
    """The aSAH columns ``y``, ``s100b`` and ``ndka`` (read-only numpy arrays) whose
    ``repr`` and ``str`` name the row count only (DEC-77, E12 repair 3): pytest's
    assertion output prints the ``repr`` of the objects an assertion names. At
    ``e6ad3c8``, ``assert caps.vectors is not None and caps.proc is not None`` on a
    two-row vectors file with ``proc_asah.json`` absent printed
    ``'ndka': array([98765.4321, 12345.6789])``.
    ``tests/test_e12_repair3.py::test_dec77_the_vectors_repr_holds_no_value`` and
    ``::test_dec77_a_failing_assertion_on_the_captures_prints_no_vector_value`` feed that
    file and read none of its values in the ``repr`` or in pytest's output."""

    def __repr__(self) -> str:
        n = len(self["y"]) if "y" in self else 0
        return f"<aSAH vectors withheld (DEC-77): {n} rows>"

    __str__ = __repr__


@dataclass(frozen=True)
class RCaptures:
    """What :func:`load_r_captures` read. ``proc`` / ``valprob`` / ``comparison`` are the
    parsed JSON documents of ``proc_asah.json``, ``rms_val_prob_f4.json`` and
    :data:`R_COMPARISON_FILE` (``None`` when the file is absent or could not be read: the
    file is then named in ``unreadable`` with the error type); ``proc_sha256`` the sha256
    of ``proc_asah.json``'s bytes with CRLF read as LF. ``vectors_path`` is the file
    :data:`R_VECTORS_ENV` names, ``None`` when it is not set (DEC-77: every place but the
    r-captures job); ``vectors`` the columns read from it (:class:`WithheldVectors`) and
    ``vectors_sha256`` the sha256 of its bytes with CRLF read as LF. When ``vectors_path``
    is set, a file there that is missing or does not parse is named in ``unreadable``."""

    directory: Path | None
    proc: dict[str, Any] | None = None
    valprob: dict[str, Any] | None = None
    vectors: WithheldVectors | None = None
    vectors_sha256: str | None = None
    unreadable: tuple[tuple[str, str], ...] = ()
    comparison: dict[str, Any] | None = None
    proc_sha256: str | None = None
    vectors_path: Path | None = None

    @property
    def present(self) -> tuple[str, ...]:
        """The files of :data:`R_CAPTURE_FILES`, :data:`R_VECTORS_FILE` and
        :data:`R_COMPARISON_FILE` that were read."""
        found = (
            (R_CAPTURE_FILES[0], self.proc is not None),
            (R_CAPTURE_FILES[1], self.valprob is not None),
            (R_VECTORS_FILE, self.vectors is not None),
            (R_COMPARISON_FILE, self.comparison is not None),
        )
        return tuple(name for name, ok in found if ok)


def lf_sha256(data: bytes) -> str:
    """sha256 of ``data`` with every CRLF read as LF (the bytes the index holds)."""
    import hashlib  # noqa: PLC0415

    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _read_asah_vectors(data: bytes) -> WithheldVectors:
    """The columns of an ``asah_vectors.csv``; ``ValueError`` (with no value from the file
    in its message) when the bytes do not parse as one."""
    try:
        lines = [
            ln for ln in data.decode("utf-8").splitlines() if ln.strip() and not ln.startswith("#")
        ]
        y, s100b, ndka = [], [], []
        for r in csv.DictReader(lines):
            y.append(int(r["y"]))
            s100b.append(float(r["s100b"]))
            ndka.append(float(r["ndka"]))
    except (ValueError, KeyError, TypeError, csv.Error) as exc:
        raise ValueError(f"asah_vectors.csv does not parse ({type(exc).__name__})") from None
    if not y or set(y) - {0, 1}:
        raise ValueError("asah_vectors.csv: y must be 0 or 1 on at least one row")
    cols = {
        "y": np.array(y, dtype=bool),
        "s100b": np.array(s100b, dtype=np.float64),
        "ndka": np.array(ndka, dtype=np.float64),
    }
    for a in cols.values():
        a.setflags(write=False)
    return WithheldVectors(cols)


def r_captures_dir() -> Path | None:
    """``<root>/fixtures/r`` of the proofpack source checkout the package was imported
    from (:func:`source_checkout_root`); ``None`` for an installed wheel, which carries no
    R capture."""
    root = source_checkout_root()
    return None if root is None else root / "fixtures" / "r"


#: :func:`load_r_captures`'s default for ``vectors``: read :data:`R_VECTORS_ENV`.
FROM_ENV = "from the environment"


def _vectors_path_from_env() -> Path | None:
    """The path :data:`R_VECTORS_ENV` names; ``None`` when the variable is not set. An
    empty value counts as set (it names no file, so the vectors are then unreadable): a
    workflow step that sets the variable from an empty expression must fail, not skip."""
    value = os.environ.get(R_VECTORS_ENV)
    return None if value is None else Path(value)


def load_r_captures(
    directory: Path | None = None, *, vectors: Path | str | None = FROM_ENV
) -> RCaptures:
    """Read ``proc_asah.json``, ``rms_val_prob_f4.json`` and :data:`R_COMPARISON_FILE`
    from ``directory`` (default :func:`r_captures_dir`), and the aSAH vectors from the file
    ``vectors`` names (default: :data:`R_VECTORS_ENV`; ``None``: not read, the DEC-77
    shape everywhere outside the r-captures job). A JSON file that is absent is left
    ``None``; one that cannot be read or parsed is ``None`` and named in ``unreadable``.
    The vectors file, when one is named, is named in ``unreadable`` when it is missing as
    well (``FileNotFoundError``): there its absence is a failure, not a skip."""
    where = r_captures_dir() if directory is None else Path(directory)
    if where is None:
        return RCaptures(directory=None)
    vectors_path = _vectors_path_from_env() if vectors == FROM_ENV else vectors
    vectors_path = None if vectors_path is None else Path(vectors_path)
    docs: dict[str, dict[str, Any] | None] = {}
    unreadable: list[tuple[str, str]] = []
    proc_sha = None
    for rel in (*R_CAPTURE_FILES, R_COMPARISON_FILE):
        try:
            raw_json = (where / Path(rel).name).read_bytes()
            doc = json.loads(raw_json.decode("utf-8"))
            if not isinstance(doc, dict):
                raise ValueError("not a JSON object")
            docs[rel] = doc
            if rel == R_CAPTURE_FILES[0]:
                proc_sha = lf_sha256(raw_json)
        except FileNotFoundError:
            docs[rel] = None
        except (ValueError, OSError) as exc:
            docs[rel] = None
            unreadable.append((rel, type(exc).__name__))
    cols = sha = None
    if vectors_path is not None:
        try:
            raw = vectors_path.read_bytes()
            cols, sha = _read_asah_vectors(raw), lf_sha256(raw)
        except (ValueError, OSError) as exc:
            unreadable.append((R_VECTORS_FILE, type(exc).__name__))
    return RCaptures(
        directory=where,
        proc=docs[R_CAPTURE_FILES[0]],
        valprob=docs[R_CAPTURE_FILES[1]],
        vectors=cols,
        vectors_sha256=sha,
        unreadable=tuple(unreadable),
        comparison=docs[R_COMPARISON_FILE],
        proc_sha256=proc_sha,
        vectors_path=vectors_path,
    )


#: F13's compared values, named as ``capture.R`` names them in ``proc_asah.json``'s
#: ``values``: per score the AUROC, ``var(roc, method = "delong")``, the
#: ``ci.auc(method = "delong")`` bounds and the case / control counts (which pin the
#: level mapping), then ``roc.test(method = "delong", paired = TRUE)``.
F13_NAMES = (
    *(
        f"{score} {k}"
        for score in ("s100b", "ndka")
        for k in ("auc", "var_delong", "ci_delong_lo", "ci_delong_hi", "n_cases", "n_controls")
    ),
    "roc.test statistic",
    "roc.test p.value",
    "roc.test estimate 1",
    "roc.test estimate 2",
)
#: Not in the report row: pROC writes ``conf.int`` on a paired DeLong ``roc.test`` only in
#: some versions [unverified: the version that added it was not read], and a row compares a
#: fixed set of names. ``tests/test_day12_r_captures.py`` compares them when the capture
#: carries them (``f13_engine_values(..., with_conf_int=True)``). The committed capture
#: (GitHub run 37332685741, pROC 1.19.0.1) carries them; that run's ``pytest -m day12``
#: step reported no skip.
F13_OPTIONAL_NAMES = ("roc.test conf.int lo", "roc.test conf.int hi")
#: F13b's compared values, named as ``capture.R`` names them in
#: ``rms_val_prob_f4.json``'s ``values``. ``val.prob Intercept`` is compared with the
#: engine's ``intercept`` - the intercept of the joint model ``a + b logit(p)``, the
#: model ``val.prob`` fits with ``lrm.fit(logit, y)`` [unverified: from memory of the rms
#: source, not a fetched copy; the capture's ``glm joint`` values are the same model fitted
#: by ``glm``, so a different definition shows as ``val.prob Intercept`` alone outside
#: tolerance]. In the committed capture (GitHub run 37332685741, rms 8.1.0) ``val.prob
#: Intercept`` is 1.2e-15 from ``glm joint tight (Intercept)`` and 0.044 from ``glm offset
#: (Intercept)`` on the F4 rows; the rms source is still not read. The engine's
#: ``intercept_large`` (slope fixed at 1) is compared with ``glm offset (Intercept)``.
#: Standard errors are compared with the ``epsilon 1e-14``
#: fits only: at the default convergence they need not agree to 1e-6 (statsmodels'
#: default fit was 9.13e-6 and 1.99e-5 from its tight fit on these rows,
#: ``f4_expected.json``).
F13B_NAMES = (
    "val.prob Slope",
    "val.prob Intercept",
    "val.prob Brier",
    "val.prob C (ROC)",
    "glm joint (Intercept)",
    "glm joint logit_p",
    "glm offset (Intercept)",
    "glm joint tight (Intercept)",
    "glm joint tight logit_p",
    "glm joint tight (Intercept) se",
    "glm joint tight logit_p se",
    "glm offset tight (Intercept)",
    "glm offset tight (Intercept) se",
)
R_CAPTURE_SCHEMA = "proofpack-r-capture/1"
#: The reasons F13 and F13b carry while no capture is committed (``no_oracle_recorded``).
F13_ABSENT = (
    "[unverified until captured] the pROC capture (fixtures/r/proc_asah.json) and the "
    "engine comparison the r-captures job records beside it "
    "(fixtures/r/f13_engine_comparison.json) are not both committed; the aSAH vectors are "
    "never committed (DEC-77), so F13 is compared inside that job only "
    "(fixtures/r/capture.R, .github/workflows/r-captures.yml; build day 12)"
)
F13B_ABSENT = (
    "[unverified until captured] the rms::val.prob capture (fixtures/r/rms_val_prob_f4.json) "
    "is not committed; fixtures/r/capture.R and the r-captures workflow (build day 12) "
    "write it"
)
#: The reason F13 and F13b carry when the package is not a source checkout (an installed
#: wheel): :func:`r_captures_dir` is ``None`` and nothing under ``fixtures/r`` is read, so
#: whether a capture is committed is not known here (E12 repair 1, lens 1 FA-N8:
#: ``tests/test_e12_repair1.py::test_fa_n8_an_installed_package_says_it_read_no_capture``).
R_CAPTURES_NOT_READ = (
    "[unverified until captured] an installed package reads no R capture: fixtures/r/ is "
    "read only when the package is <root>/src/proofpack and <root>/pyproject.toml names "
    "proofpack"
)


def f13_engine_values(
    vectors: dict[str, np.ndarray], *, with_conf_int: bool = False
) -> dict[str, float]:
    """The engine on the aSAH vectors: ``auroc_number`` (its ``delong_wald`` Number is the
    interval compared with ``ci.auc``: pROC's DeLong interval is taken to be the Wald
    interval [unverified: pROC's source was not read; the comparison is what tests it: GitHub
    run 37332685741 recorded both scores' bounds 0.0 from ``ci.auc``'s on aSAH]),
    ``delong_variance`` and ``paired_delong`` (s100b first, as ``roc.test(roc1, roc2)``)."""
    from proofpack.stats.discrimination import auroc_number, delong_variance, paired_delong

    y = np.asarray(vectors["y"], dtype=bool)
    out: dict[str, float] = {}
    for score in ("s100b", "ndka"):
        s = vectors[score]
        r = auroc_number(s, y)
        wald = next(
            (
                n
                for n in (r.auroc, r.auroc_secondary)
                if n is not None and n.method == "delong_wald"
            ),
            None,
        )
        if wald is None:
            raise RuntimeError(f"{score}: auroc_number returned no delong_wald interval")
        _, var = delong_variance(s, y)
        out[f"{score} auc"] = float(r.auroc.est)  # type: ignore[arg-type]
        out[f"{score} var_delong"] = var
        out[f"{score} ci_delong_lo"] = float(wald.ci_lo)  # type: ignore[arg-type]
        out[f"{score} ci_delong_hi"] = float(wald.ci_hi)  # type: ignore[arg-type]
        out[f"{score} n_cases"] = float(r.n_pos)
        out[f"{score} n_controls"] = float(r.n_neg)
    pd = paired_delong(vectors["s100b"], vectors["ndka"], y)
    out["roc.test statistic"] = pd.z
    out["roc.test p.value"] = pd.p_value
    out["roc.test estimate 1"] = float(pd.auroc_a.est)  # type: ignore[arg-type]
    out["roc.test estimate 2"] = float(pd.auroc_b.est)  # type: ignore[arg-type]
    if with_conf_int and pd.difference.has_ci:
        out["roc.test conf.int lo"] = float(pd.difference.ci_lo)  # type: ignore[arg-type]
        out["roc.test conf.int hi"] = float(pd.difference.ci_hi)  # type: ignore[arg-type]
    return out


def f13b_engine_values() -> dict[str, float]:
    """The engine on the committed F4 rows: the IRLS slope and intercepts with their Wald
    standard errors (``calibration_block``), the Brier score and the AUROC."""
    from proofpack.stats.discrimination import auroc_mann_whitney

    irls, closed = _f4_irls(), _f4_closed()
    p, y = _f4_rows()
    return {
        "val.prob Slope": irls["slope"],
        "val.prob Intercept": irls["intercept"],
        "val.prob Brier": closed["brier"],
        "val.prob C (ROC)": auroc_mann_whitney(p, y),
        "glm joint (Intercept)": irls["intercept"],
        "glm joint logit_p": irls["slope"],
        "glm offset (Intercept)": irls["intercept_large"],
        "glm joint tight (Intercept)": irls["intercept"],
        "glm joint tight logit_p": irls["slope"],
        "glm joint tight (Intercept) se": irls["intercept_se"],
        "glm joint tight logit_p se": irls["slope_se"],
        "glm offset tight (Intercept)": irls["intercept_large"],
        "glm offset tight (Intercept) se": irls["intercept_large_se"],
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _r_source(doc: dict[str, Any], file: str) -> dict[str, Any]:
    meta = _as_dict(doc.get("meta"))
    gh = _as_dict(meta.get("github"))
    versions = {"R": str(meta.get("r_version_string"))}
    versions.update({str(k): str(v) for k, v in _as_dict(meta.get("packages")).items()})
    run = (
        f"GitHub run {gh.get('run_id')} at {gh.get('sha')}"
        if gh.get("run_id")
        else "not a GitHub run"
    )
    return {
        "kind": "captured_library",
        "file": file,
        "entry": "values",
        "detail": f"{doc.get('what')}; {meta.get('r_version_string')}; captured "
        f"{meta.get('run_date_utc')}; {run}; repos {meta.get('repos')}",
        "library_versions": versions,
        "unverified": False,
        "marking": None,
    }


def _r_values(
    doc: dict[str, Any], names: tuple[str, ...]
) -> tuple[dict[str, Any], dict[str, float]]:
    values = doc.get("values")
    if not isinstance(values, dict):
        raise RCaptureInputMismatch("the capture has no values object")
    picked = {k: values.get(k) for k in names}
    return picked, {k: float(TOLERANCES["iterative"]) for k in picked}  # type: ignore[arg-type]


def _check_header(doc: dict[str, Any], fixture: str) -> None:
    if doc.get("schema") != R_CAPTURE_SCHEMA or doc.get("fixture") != fixture:
        raise RCaptureInputMismatch(
            f"schema {doc.get('schema')!r} fixture {doc.get('fixture')!r}, expected "
            f"{R_CAPTURE_SCHEMA!r} {fixture!r}"
        )


class ComparedInRunner(Exception):  # noqa: N818 - a row outcome, not an error
    """F13 outside the r-captures job (DEC-77): the row as the job's recorded comparison
    (:data:`R_COMPARISON_FILE`) gives it, read by :func:`f13_recorded_outcome`.
    :func:`compare_row` writes ``status``, ``reason`` and ``max_abs_deviation`` into the
    row as they are and returns it; this command compares no value itself."""

    def __init__(self, status: str, reason: str, max_abs_deviation: float | None) -> None:
        self.status = status
        self.reason = reason
        self.max_abs_deviation = max_abs_deviation
        super().__init__(reason)


#: The files F13's row names as where it was compared, when it is ``suite_only``.
F13_RUNNER_SUITE = (".github/workflows/r-captures.yml", "tests/test_day12_r_captures.py")


def _json_number(value: Any) -> float | None:
    """``value`` as a float when it is a finite JSON number (an ``int`` or ``float``, not a
    ``bool`` and not a string); ``None`` otherwise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    out = float(value)
    return out if math.isfinite(out) else None


def _is_hex(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(c in "0123456789abcdef" for c in value)
    )


def f13_recorded_outcome(caps: RCaptures) -> ComparedInRunner:
    """F13 from ``proc_asah.json`` and :data:`R_COMPARISON_FILE` when the vectors are not
    read here (DEC-77). The comparison file must name the schema
    :data:`R_COMPARISON_SCHEMA` and fixture ``F13``; its ``proc_asah_sha256`` must equal the
    sha256 of the committed ``proc_asah.json`` (CRLF read as LF), its ``vectors_sha256`` and
    ``vectors_rows`` the ones ``proc_asah.json``'s ``input`` records, its
    ``github_run_id`` the run id in ``proc_asah.json``'s ``meta.github``, and its
    ``engine_sha`` must be 40 hex characters; otherwise :class:`RCaptureInputMismatch`. Each
    name of :data:`F13_NAMES` must carry ``engine`` and ``r`` as finite JSON numbers (a string is
    refused), ``r`` equal to
    ``proc_asah.json``'s value and ``tolerance`` equal to the ``iterative`` 1e-6; the
    deviation is recomputed here as ``abs(engine - r)`` (the file's ``abs_deviation`` and
    ``within`` are not read). Outcome: ``not_matched`` when a name fails those checks or
    lies outside 1e-6, ``suite_only`` otherwise, with a reason naming the run, the engine
    commit, the maximum deviation and that a local re-check needs R; when the engine commit
    is not this checkout's HEAD (:func:`git_sha`) the reason says so."""
    proc, cmp_doc = caps.proc, caps.comparison
    assert proc is not None and cmp_doc is not None
    if cmp_doc.get("schema") != R_COMPARISON_SCHEMA or cmp_doc.get("fixture") != "F13":
        raise RCaptureInputMismatch(
            f"{R_COMPARISON_FILE} schema {cmp_doc.get('schema')!r} fixture "
            f"{cmp_doc.get('fixture')!r}, expected {R_COMPARISON_SCHEMA!r} 'F13'"
        )
    p_input = _as_dict(proc.get("input"))
    p_run = _as_dict(_as_dict(proc.get("meta")).get("github")).get("run_id")
    checks = (
        ("proc_asah_sha256", cmp_doc.get("proc_asah_sha256"), caps.proc_sha256),
        ("vectors_sha256", cmp_doc.get("vectors_sha256"), p_input.get("vectors_sha256")),
        ("vectors_rows", cmp_doc.get("vectors_rows"), p_input.get("n_rows")),
        ("github_run_id", cmp_doc.get("github_run_id"), p_run),
    )
    for key, recorded, expected in checks:
        if recorded is None or isinstance(recorded, bool) or str(recorded) != str(expected):
            raise RCaptureInputMismatch(
                f"{R_COMPARISON_FILE} {key} {recorded!r}, proc_asah.json gives {expected!r}"
            )
    engine_sha = cmp_doc.get("engine_sha")
    if not _is_hex(engine_sha, 40) or not _is_hex(caps.proc_sha256, 64):
        raise RCaptureInputMismatch(f"{R_COMPARISON_FILE} engine_sha {engine_sha!r}")
    values = _as_dict(cmp_doc.get("values"))
    proc_values = _as_dict(proc.get("values"))
    tol = float(TOLERANCES["iterative"])  # type: ignore[arg-type]
    problems: list[str] = []
    outside: list[str] = []
    worst = 0.0
    for name in F13_NAMES:
        rec = _as_dict(values.get(name))
        e, r = _json_number(rec.get("engine")), _json_number(rec.get("r"))
        if e is None or r is None:
            problems.append(f"no engine and R numbers: {name}")
            continue
        if r != _json_number(proc_values.get(name)):
            problems.append(f"R value not proc_asah.json's: {name}")
            continue
        if _json_number(rec.get("tolerance")) != tol:
            problems.append(f"tolerance not {tol:g}: {name}")
            continue
        dev = abs(e - r)
        worst = max(worst, dev)
        if not dev <= tol:
            outside.append(name)
    run = f"GitHub run {cmp_doc.get('github_run_id')}"
    if problems or outside:
        parts = problems + (["outside tolerance: " + ", ".join(outside)] if outside else [])
        return ComparedInRunner(
            "not_matched",
            f"r_capture_recorded_not_matched: {R_COMPARISON_FILE} ({run}, engine commit "
            f"{engine_sha}): " + "; ".join(parts),
            worst if not problems else None,
        )
    head, head_source = git_sha()
    if head is None:
        where = f"this checkout's HEAD was not read ({head_source})"
    elif head == engine_sha:
        where = "the engine commit is this checkout's HEAD"
    else:
        where = (
            f"the engine commit is not this checkout's HEAD ({head}); this command did not "
            "run that comparison on this checkout's engine"
        )
    return ComparedInRunner(
        "suite_only",
        f"compared inside the r-captures job, not by this command: {run} recorded "
        f"{len(F13_NAMES)} values of the engine at commit {engine_sha} against pROC "
        f"(proc_asah.json), max abs deviation {worst!r}, each within 1e-6 as recomputed "
        f"here from the recorded engine and R numbers; {where}. The aSAH vectors are never "
        "committed (DEC-77), so a local re-check needs R: the r-captures job "
        "(fixtures/r/README.md)",
        worst,
    )


def f13_oracle(caps: RCaptures):
    """``(values, tolerance, source)`` of ``proc_asah.json`` compared with the engine on
    the vectors :data:`R_VECTORS_ENV` names (the r-captures job's shape). From an installed
    package (``caps.directory`` ``None``) :class:`OracleAbsent` with
    :data:`R_CAPTURES_NOT_READ`.

    With ``caps.vectors_path`` set: an unreadable or missing vectors file, or an unreadable
    ``proc_asah.json``, is :class:`OracleFileUnreadable`; an absent ``proc_asah.json`` is
    :class:`OracleFileMissing` (both rows ``not_matched``); the capture's
    ``input.vectors_sha256`` must equal the sha256 of the vectors read (CRLF read as LF).

    With ``caps.vectors_path`` ``None`` (DEC-77: everywhere else): an unreadable
    ``proc_asah.json`` or :data:`R_COMPARISON_FILE` is :class:`OracleFileUnreadable`;
    while either is absent :class:`OracleAbsent` with :data:`F13_ABSENT` and the absent
    files; when both are read, :class:`ComparedInRunner` from
    :func:`f13_recorded_outcome`."""
    if caps.directory is None:
        raise OracleAbsent(R_CAPTURES_NOT_READ)
    bad = dict(caps.unreadable)
    if caps.vectors_path is None:
        for rel in (R_CAPTURE_FILES[0], R_COMPARISON_FILE):
            if rel in bad:
                raise OracleFileUnreadable(rel, bad[rel])
        missing = [
            rel
            for rel, doc in ((R_CAPTURE_FILES[0], caps.proc), (R_COMPARISON_FILE, caps.comparison))
            if doc is None
        ]
        if missing:
            raise OracleAbsent(f"{F13_ABSENT} (absent: {', '.join(missing)})")
        _check_header(caps.proc, "F13")  # type: ignore[arg-type]
        raise f13_recorded_outcome(caps)
    for rel in (R_CAPTURE_FILES[0], R_VECTORS_FILE):
        if rel in bad:
            raise OracleFileUnreadable(rel, bad[rel])
    if caps.proc is None:
        raise OracleFileMissing(R_CAPTURE_FILES[0])
    if caps.vectors is None:  # the loader names a vectors file it could not read
        raise OracleFileUnreadable(R_VECTORS_FILE, "not read")
    _check_header(caps.proc, "F13")
    recorded = _as_dict(caps.proc.get("input")).get("vectors_sha256")
    if recorded != caps.vectors_sha256:
        raise RCaptureInputMismatch(
            f"asah_vectors.csv sha256 {caps.vectors_sha256} (CRLF read as LF), the capture "
            f"recorded {recorded}"
        )
    values, tol = _r_values(caps.proc, F13_NAMES)
    return values, tol, _r_source(caps.proc, R_CAPTURE_FILES[0])


def f13b_oracle(caps: RCaptures):
    """``(values, tolerance, source)`` of ``rms_val_prob_f4.json``; the capture's
    ``input.sha256`` must equal the sha256 of the F4 file the engine reads (CRLF read as
    LF); :class:`OracleAbsent` with :data:`F13B_ABSENT` while the capture is absent, and
    with :data:`R_CAPTURES_NOT_READ` from an installed package."""
    if caps.directory is None:
        raise OracleAbsent(R_CAPTURES_NOT_READ)
    bad = dict(caps.unreadable)
    if R_CAPTURE_FILES[1] in bad:
        raise OracleFileUnreadable(R_CAPTURE_FILES[1], bad[R_CAPTURE_FILES[1]])
    if caps.valprob is None:
        raise OracleAbsent(F13B_ABSENT)
    _check_header(caps.valprob, "F13b")
    committed = lf_sha256(resource_path("f4_calibration.csv").read_bytes())
    recorded = _as_dict(caps.valprob.get("input")).get("sha256")
    if recorded != committed:
        raise RCaptureInputMismatch(
            f"f4_calibration.csv sha256 {committed} (CRLF read as LF), the capture recorded "
            f"{recorded}"
        )
    values, tol = _r_values(caps.valprob, F13B_NAMES)
    return values, tol, _r_source(caps.valprob, R_CAPTURE_FILES[1])


def f13_comparison_record(
    caps: RCaptures, *, engine_sha: str, run_id: str | None, run_attempt: str | None = None
) -> dict[str, Any]:
    """What the r-captures job writes to :data:`R_COMPARISON_FILE` (DEC-77): the F13 report
    row computed on ``caps`` in the job's shape (``caps.vectors_path`` set; ``ValueError``
    otherwise), as the engine commit, the run, the sha256 of ``proc_asah.json`` and of the
    vectors with their row count, the row's status and maximum deviation, and per compared
    name the engine value, the R value, the absolute deviation, the tolerance and whether it
    is within: aggregates and two sha256 values.
    ``tests/test_e12_repair3.py::test_dec77_the_record_holds_no_vector_line`` feeds the
    synthetic 80-row vectors and finds none of their 81 lines (header included) in the
    JSON text."""
    if caps.vectors_path is None:
        raise ValueError(f"{R_VECTORS_ENV} is not set: the vectors are not read here")
    row = compare_row(r_capture_rows(caps)[0], {})
    n_rows = len(caps.vectors["y"]) if caps.vectors is not None else None
    return {
        "schema": R_COMPARISON_SCHEMA,
        "fixture": "F13",
        "what": "the engine's F13 values on the aSAH vectors (read inside the r-captures job "
        "from the runner's temporary space, never committed or uploaded: DEC-77) compared "
        "with proc_asah.json; aggregates and the vectors' sha256 only",
        "engine_sha": engine_sha,
        "engine_version": __version__,
        "github_run_id": run_id,
        "github_run_attempt": run_attempt,
        "proc_asah_sha256": caps.proc_sha256,
        "vectors_sha256": caps.vectors_sha256,
        "vectors_rows": n_rows,
        "tolerance_class": "iterative",
        "status": row["status"],
        "reason": row["reason"],
        "max_abs_deviation": row["max_abs_deviation"],
        "values": {
            v["name"]: {
                "engine": v["engine"],
                "r": v["oracle"],
                "abs_deviation": v["abs_deviation"],
                "tolerance": v["tolerance"],
                "within": v["within"],
            }
            for v in row["values"]
        },
    }


class OptionalDependencyMissing(RuntimeError):
    """A comparison needs a package the install does not have (scipy: ``proofpack[stats]``)."""

    def __init__(self, package: str) -> None:
        self.package = package
        super().__init__(f"{package} is not installed")


# ------------------------------------------------------------------ the register


@dataclass(frozen=True)
class Row:
    """One row of the report. ``engine`` returns the compared values; ``oracle`` returns
    ``(values, per-value tolerance, source)``; ``compares`` names the values the row
    compares (the oracle's own keys are compared as well); a row without ``engine`` or
    ``oracle`` carries ``status``."""

    id: str
    fixture: str
    what: str
    tolerance_class: str | None = None
    engine: Callable[..., dict[str, float]] | None = None
    oracle: Callable[[dict[str, Any]], tuple[dict[str, float], dict[str, float], dict]] | None = (
        None
    )
    status: str | None = None  # for rows that are not compared
    reason: str | None = None
    suite_tests: tuple[str, ...] = ()
    compares: tuple[str, ...] = ()


def _captured(key: str, cls: str) -> Callable:
    def oracle(o: dict[str, Any]):
        doc = o["oracles_v1.json"]
        entry = doc["captured"][key]
        tol = TOLERANCES[cls]
        values = dict(entry["values"])
        return (
            values,
            {k: float(tol) for k in values},  # type: ignore[arg-type]
            {
                "kind": entry["kind"],
                "file": "fixtures/oracles_v1.json",
                "entry": f"captured.{key}",
                "detail": entry["source"],
                "library_versions": doc["library_versions"],
                "unverified": False,
                "marking": None,
            },
        )

    return oracle


def _register_oracle(key: str) -> Callable:
    def oracle(o: dict[str, Any]):
        values, tol = _register(o, key)
        return (
            dict(values),
            tol,
            {
                "kind": "published_table",
                "file": "fixtures/oracles_v1.json",
                "entry": f"register.{key}",
                "detail": o["oracles_v1.json"]["register_source"],
                "library_versions": None,
                "unverified": False,
                "marking": None,
            },
        )

    return oracle


def _f4_oracle(section: str, cls: str) -> Callable:
    def oracle(o: dict[str, Any]):
        f4 = o["f4_expected.json"]
        tol = TOLERANCES[cls]
        if section == "closed":
            hand = f4["hand"]
            values = {
                "oe": hand["oe"]["value"],
                "oe_ci_lo": hand["oe_ci_95"]["lo"],
                "oe_ci_hi": hand["oe_ci_95"]["hi"],
                "brier": f4["sklearn_brier"]["brier"],
                "brier_ref": hand["brier_ref"]["value"],
                "ipa": hand["ipa"]["value"],
                "ece_equal_width_10": hand["ece_equal_width_10"]["value"],
                "ece_equal_mass_10": hand["ece_equal_mass_10"]["value"],
            }
            detail = (
                "fixtures/f4_expected.json: sklearn_brier (scikit-learn brier_score_loss) and "
                "hand (the formulae recorded beside each value); " + f4["produced"]
            )
        else:
            off, joint = f4["statsmodels_glm_binomial_offset"], f4["statsmodels_glm_binomial_joint"]
            values = {
                "intercept_large": off["intercept_large"],
                "intercept_large_se": off["se"],
                "slope": joint["slope"],
                "slope_se": joint["se_slope"],
                "intercept": joint["intercept"],
                "intercept_se": joint["se_intercept"],
            }
            detail = (
                "fixtures/f4_expected.json: statsmodels GLM(Binomial) fit(tol=1e-10) with and "
                "without the offset; " + f4["produced"]
            )
        return (
            values,
            {k: float(tol) for k in values},  # type: ignore[arg-type]
            {
                "kind": "captured_library",
                "file": "fixtures/f4_expected.json",
                "entry": section,
                "detail": detail,
                "library_versions": None,
                "unverified": False,
                "marking": None,
            },
        )

    return oracle


def _f4_register_oracle(o: dict[str, Any]):
    q = o["f4_expected.json"]["r2_quoted"]
    values = {
        "brier": q["brier"],
        "brier_ref": q["brier_ref"],
        "ipa": q["ipa"],
        "oe": q["oe"],
        "intercept_large": q["intercept_large"],
        "slope": q["slope"],
        "intercept": q["intercept"],
        "ece_10_equal_width": q["ece_10"],
        "ece_10_equal_mass": q["ece_10"],
    }
    tol = {k: float(TOLERANCES["register"]) for k in values}  # type: ignore[arg-type]
    return (
        values,
        tol,
        {
            "kind": "published_table",
            "file": "fixtures/f4_expected.json",
            "entry": "r2_quoted",
            "detail": "R2 section 9 F4 as quoted in fixtures/f4_expected.json (4 decimals; "
            "0.24 to 2)",
            "library_versions": None,
            "unverified": False,
            "marking": None,
        },
    )


def _f14_oracle(o: dict[str, Any]):
    if NEWCOMBE_FILE not in o and NEWCOMBE_FILE not in getattr(o, "unreadable", {}):
        raise OracleAbsent(NEWCOMBE_ABSENT)
    doc = o[NEWCOMBE_FILE]
    values = {}
    for ex in doc["examples"]:
        for method in ("method10", "method11"):
            values[f"{ex['label']} {method} lower"] = ex[method]["lower"]
            values[f"{ex['label']} {method} upper"] = ex[method]["upper"]
    status = doc["provenance"]["status"]
    return (
        values,
        {k: rounding_tolerance(4) for k in values},
        {
            "kind": "published_table",
            "file": "fixtures/newcombe_table2.json",
            "entry": "examples",
            "detail": doc["provenance"]["actual_source"],
            "library_versions": None,
            "unverified": "[unverified" in status,
            "marking": status,
        },
    )


def r_capture_rows(captures: RCaptures | None = None) -> tuple[Row, Row]:
    """The F13 and F13b rows (build day 12). Bound to ``captures`` when given (the test
    hook: a capture written into a temporary directory and read by
    :func:`load_r_captures`); otherwise each comparison reads :func:`load_r_captures`
    afresh. While a capture is absent the row is ``no_oracle_recorded`` with
    :data:`F13_ABSENT` / :data:`F13B_ABSENT`; when present it is ``matched`` or
    ``not_matched`` under the ``iterative`` tolerance (absolute 1e-6 on every value). F13
    is compared with the engine only where :data:`R_VECTORS_ENV` names the vectors (the
    r-captures job); elsewhere :func:`f13_oracle` reads the job's recorded comparison."""

    def get() -> RCaptures:
        return captures if captures is not None else load_r_captures()

    def f13_engine() -> dict[str, float]:
        vectors = get().vectors
        if vectors is None:  # the oracle raises OracleAbsent first; kept for direct calls
            raise RuntimeError("no asah_vectors.csv")
        return f13_engine_values(vectors)

    return (
        Row(
            "F13",
            "F13",
            "pROC on aSAH (outcome ~ s100b and ~ ndka, levels and direction written out): AUROC, "
            "DeLong variance, ci.auc(method = 'delong') bounds, case and control counts, "
            "and the paired roc.test(method = 'delong') of s100b against ndka",
            "iterative",
            f13_engine,
            lambda _o: f13_oracle(get()),
            compares=F13_NAMES,
        ),
        Row(
            "F13b",
            "F13b",
            "rms::val.prob Slope, Intercept, Brier and C (ROC) on the committed F4 rows, and "
            "glm(y ~ qlogis(p)) and glm(y ~ offset(qlogis(p))) coefficients (standard errors "
            "at epsilon 1e-14)",
            "iterative",
            f13b_engine_values,
            lambda _o: f13b_oracle(get()),
            compares=F13B_NAMES,
        ),
    )


def register() -> tuple[Row, ...]:
    """Every row, in register order (D1 section 3.2)."""
    rows: list[Row] = []
    for fid, (k, n) in F1_CASES.items():
        rows += [
            Row(
                f"{fid}-wilson",
                fid,
                f"Wilson 95% interval of {k}/{n} (proportion(), the rendered Number)",
                "closed_form",
                lambda k=k, n=n: _f1_wilson(k, n),
                _captured(f"{fid}-wilson", "closed_form"),
                compares=WILSON_NAMES,
            ),
            Row(
                f"{fid}-clopper-pearson",
                fid,
                f"Clopper-Pearson 95% interval of {k}/{n} (clopper_pearson_bounds)",
                "iterative",
                lambda k=k, n=n: _f1_cp(k, n),
                _captured(f"{fid}-clopper-pearson", "iterative"),
                compares=CP_NAMES,
            ),
            Row(
                f"{fid}-register",
                fid,
                f"Wilson and Clopper-Pearson bounds of {k}/{n} against the printed register",
                "register",
                lambda k=k, n=n: {**_f1_wilson(k, n), **_f1_cp(k, n)},
                _register_oracle(fid),
                compares=WILSON_NAMES + CP_NAMES,
            ),
        ]
    rows += [
        Row(
            "F2-exact",
            "F2",
            "two_by_two_metrics on TP 90, FN 10, FP 20, TN 180: eleven point estimates, the "
            "two Wilson intervals, PPV and NPV at prevalence 0.05",
            "closed_form",
            _f2,
            _captured("F2-exact", "closed_form"),
            compares=F2_NAMES,
        ),
        Row(
            "F2-register",
            "F2",
            "the same seventeen values against the printed register",
            "register",
            _f2,
            _register_oracle("F2"),
            compares=F2_NAMES,
        ),
        Row(
            "F3-auroc",
            "F3",
            "AUROC of s1 and s2 on the ten F3 rows (auroc_mann_whitney)",
            "closed_form",
            _f3_auroc,
            _captured("F3-auroc", "closed_form"),
            compares=F3_AUROC_NAMES,
        ),
        Row(
            "F3-delong",
            "F3",
            "DeLong standard errors, the logit and Wald intervals of s1, and the paired "
            "variance, z and p of s1 - s2 (auroc_number, paired_delong; the Wald bounds "
            "from wald_ci before the unit-range clip of the rendered Number)",
            "iterative",
            _f3_delong,
            _captured("F3-delong", "iterative"),
            compares=F3_DELONG_NAMES,
        ),
        Row(
            "F3-register",
            "F3",
            "the F3 AUROCs, s1's DeLong standard error and intervals and the paired test "
            "against the printed register",
            "register",
            _f3_register_values,
            _register_oracle("F3"),
            compares=F3_REGISTER_NAMES,
        ),
        Row(
            "F3-bootstrap",
            "F3",
            "stratified bootstrap percentile interval of AUROC(s1), B = 2000, "
            "default_rng(20240101)",
            "reported_rounding",
            lambda: _bootstrap_auroc(False),
            _register_oracle("F3_bootstrap"),
            compares=BOOTSTRAP_NAMES,
        ),
        Row(
            "F3-auprc",
            "F3",
            "AUPRC(s1) (register 0.835)",
            status="not_built",
            reason="the engine emits no AUPRC in this version (output schema types it null)",
        ),
        Row(
            "F4-closed-form",
            "F4",
            "calibration_block on the twenty F4 rows: O:E and its interval, Brier, reference "
            "Brier, IPA, ECE over ten equal-width and ten equal-mass bins",
            "closed_form",
            _f4_closed,
            _f4_oracle("closed", "closed_form"),
            compares=F4_CLOSED_NAMES,
        ),
        Row(
            "F4-irls",
            "F4",
            "calibration_block's IRLS intercept-in-the-large, slope and intercept, each with "
            "its Wald standard error",
            "iterative",
            _f4_irls,
            _f4_oracle("irls", "iterative"),
            compares=F4_IRLS_NAMES,
        ),
        Row(
            "F4-register",
            "F4",
            "the F4 calibration values against R2 section 9 as quoted in f4_expected.json "
            "(the five-bin ECE is not emitted by the block and is not compared)",
            "register",
            _f4_register_values,
            _f4_register_oracle,
            compares=F4_REGISTER_NAMES,
        ),
        Row(
            "F5-mcnemar",
            "F5",
            "McNemar on the F5 discordants b = 10, c = 2: the exact p (the engine's route "
            "below 25 discordant pairs) and the continuity-corrected chi-square and p "
            "(stats.comparison.mcnemar)",
            "closed_form",
            _f5_mcnemar,
            _captured("F5-mcnemar", "closed_form"),
            compares=F5_MCNEMAR_NAMES,
        ),
        Row(
            "F5-register",
            "F5",
            "the F5 McNemar figures and the paired accuracy difference (difference_paired on "
            "e 80, f 2, g 10, h 8) against the printed register",
            "register",
            _f5_register_values,
            _register_oracle("F5"),
            compares=F5_REGISTER_NAMES,
        ),
        Row(
            "F5-newcombe-paired",
            "F5",
            "the Newcombe paired method 10 interval (difference_paired, which gives the F5 "
            "accuracy difference -0.08 [-0.1554, -0.0102]) against the method 10 rows of "
            "Table III of Newcombe 1998 (paired data), read from the primary PDF on build "
            "day 11; 35 of its 36 printed method 10 limits are compared, and the 36th (cells "
            "1 97 1 1, lower: printed 0.8736 for method 10 and 0.8737 for method 8, engine "
            "0.873672) is recorded in the file's excluded entry, not compared (DEC-75 (d): "
            "Josh counts 35 of 36 as verified, 2 October 2026)",
            "reported_rounding",
            _f5_newcombe_paired,
            _f5_newcombe_paired_oracle,
            compares=F5_NEWCOMBE_PAIRED_NAMES,
        ),
        Row(
            "F5-delong-pair",
            "F5",
            "the paired DeLong difference AUC(s1) - AUC(s2) on the F3 pair with its Wald "
            "interval and variance (paired_delong, Sun and Xu components with covariance)",
            "iterative",
            _f5_delong_pair,
            _captured("F5-delong-pair", "iterative"),
            compares=F5_DELONG_PAIR_NAMES,
        ),
        Row(
            "F6-closed-form",
            "F6",
            "sensitivity by site on [45, 5], [38, 12], [27, 3], the chi-square statistic "
            "(heterogeneity_footnote) and Holm on [0.012, 0.04, 0.30] (holm)",
            "closed_form",
            lambda: {k: v for k, v in _f6_closed().items() if not k.startswith("_")},
            _f6_closed_oracle(),
            compares=F6_CLOSED_NAMES,
        ),
        Row(
            "F6-p",
            "F6",
            "the chi-square p-value of the same table (heterogeneity_footnote); Fisher's p "
            "for site 1 against site 2 is not compared (the public route runs Fisher only "
            "when an expected cell is below 5)",
            "iterative",
            _f6_p,
            _f6_p_oracle(),
            compares=("chi2_p",),
        ),
        Row(
            "F6-register",
            "F6",
            "the F6 values against the printed register",
            "register",
            _f6_register_values,
            _register_oracle("F6"),
            compares=F6_REGISTER_NAMES,
        ),
        Row(
            "F7",
            "F7",
            "PSI and KS drift statistics",
            status="not_built",
            reason="stats.drift is not in this version",
        ),
        Row(
            "F8-half-width",
            "F8",
            "Wilson half-widths at p = 0.9 for n = 50, 100, 300 (proportion())",
            "closed_form",
            _f8,
            _captured("F8-half-width", "closed_form"),
            compares=F8_NAMES,
        ),
        Row(
            "F8-register",
            "F8",
            "the three half-widths against the printed register",
            "register",
            _f8,
            _register_oracle("F8"),
            compares=F8_NAMES,
        ),
        Row(
            "F9-cluster-bootstrap",
            "F9",
            "cluster-bootstrap percentile interval of AUROC(s1) on the F3 rows each copied "
            "three times under one case id, against F3's printed bootstrap interval",
            "reported_rounding",
            lambda: _bootstrap_auroc(True),
            _register_oracle("F3_bootstrap"),
            compares=BOOTSTRAP_NAMES,
        ),
        Row(
            "F10-exact",
            "F10",
            "sensitivity and specificity of the F2 table with 6 reference-positive and 4 "
            "reference-negative indeterminates counted each way (indeterminate_both_ways)",
            "closed_form",
            _f10,
            _captured("F10-exact", "closed_form"),
            compares=F10_NAMES,
        ),
        Row(
            "F11-ppa-npa",
            "F11",
            "PPA and NPA with their Wilson intervals of the F2 table under "
            "reference_standard type comparator",
            "closed_form",
            _f11,
            _captured("F11-ppa-npa", "closed_form"),
            compares=F11_NAMES,
        ),
        Row(
            "F12",
            "F12",
            "HALT codes H01-H11 and exit 3 on the malformed inputs",
            status="suite_only",
            reason="a behaviour, not a value: the test suite inspects each HALT code",
            suite_tests=("tests/test_halt_gates.py",),
        ),
        *r_capture_rows(),
        Row(
            "F14-newcombe",
            "F14",
            "Newcombe method 10 and method 11 intervals for 56/70 - 48/80, 9/10 - 3/10 and "
            "10/10 - 0/20 (newcombe10_bounds, newcombe11_bounds)",
            "reported_rounding",
            _f14,
            _f14_oracle,
            compares=F14_NAMES,
        ),
        Row(
            "F15",
            "F15",
            "PSI critical value at B = 10, alpha 0.05",
            status="not_built",
            reason="stats.drift is not in this version",
        ),
        Row(
            "F16",
            "F16",
            "F1-F8 under Pyodide against native",
            status="not_built",
            reason="the Pyodide build is build day 10's",
        ),
        Row(
            "F17",
            "F17",
            "two runs of the synthetic cohort: manifest and run.json bytes with run_id, "
            "started and duration_s masked",
            status="suite_only",
            reason="a same-platform repeat run by the suite and by scripts/f17_determinism.py; "
            "hash identity is claimed on the reference platform only (D1 section 9)",
            suite_tests=("tests/test_f17_determinism.py", "tests/test_manifest.py"),
        ),
        Row(
            "F18",
            "F18",
            "recovery of an injected -0.06 AUROC gap over seeded cohorts",
            status="suite_only",
            reason="a coverage property over seeds, not a value",
            suite_tests=("tests/test_subgroups.py",),
        ),
        Row(
            "F19",
            "F19",
            "egress payload: schema, whitelist, suppression, no site name",
            status="suite_only",
            reason="a property of the egress bytes, not a value",
            suite_tests=("tests/test_egress.py", "tests/test_offline.py"),
        ),
        Row(
            "F20",
            "F20",
            "licence verify: valid, expired, tampered, wrong key, trial",
            status="suite_only",
            reason="a behaviour of the licence check, not a value",
            suite_tests=("tests/test_licence.py",),
        ),
        Row(
            "F21",
            "F21",
            "Sepsis-2019 regression snapshot",
            status="not_built",
            reason="no Sepsis-2019 prediction file or snapshot is committed in this repository",
        ),
    ]
    return tuple(rows)


def _f6_closed_oracle() -> Callable:
    base = _captured("F6-homogeneity", "closed_form")

    def oracle(o: dict[str, Any]):
        values, tol, src = base(o)
        values = {k: v for k, v in values.items() if k != "chi2_p"}
        return values, {k: tol[k] for k in values}, src

    return oracle


def _f6_p_oracle() -> Callable:
    base = _captured("F6-homogeneity", "iterative")

    def oracle(o: dict[str, Any]):
        values, tol, src = base(o)
        return {"chi2_p": values["chi2_p"]}, {"chi2_p": tol["chi2_p"]}, src

    return oracle


# ----------------------------------------------------------------------- comparing


def _number(value: Any) -> float | None:
    """``value`` as a finite float, or ``None`` when it is absent, not a number, or not
    finite (NaN and infinity cannot be written to JSON, and are not compared)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _why_not_compared(value: Any) -> str:
    if value is None:
        return "missing"
    if isinstance(value, bool):  # lens FA2-R8: True read as "not finite (1.0)"
        return "not a number (bool)"
    try:
        return f"not finite ({float(value)!r})"
    except (TypeError, ValueError):
        return f"not a number ({type(value).__name__})"


def compare_row(row: Row, oracles: dict[str, Any]) -> dict[str, Any]:
    """One report row. The inputs the tests feed and the rows they read back
    (``tests/test_ap3_repair1.py`` unless named): ``f4_expected.json`` absent gives the
    three F4 rows ``not_matched``, ``oracle_file_missing: f4_expected.json``; the entry
    ``captured.F1-wilson`` deleted gives ``oracle_error: KeyError``; ``paired_delong``
    raising ``ZeroDivisionError`` gives ``engine_error: ZeroDivisionError``
    (``tests/test_fixtures_cmd.py``); F8's ``half_width_n50`` left out, or NaN, is written
    as ``engine: null``, ``within: false``, and the row's ``max_abs_deviation`` is
    ``null``. In ``tests/test_ap3_repair2.py``: ``captured.F1-wilson.values.wilson_lo``
    deleted gives ``oracle value missing: wilson_lo``; ``oracles_v1.json`` truncated to
    ``{"captured": `` gives ``oracle_file_unreadable: oracles_v1.json (JSONDecodeError)``."""
    out: dict[str, Any] = {
        "id": row.id,
        "fixture": row.fixture,
        "what_is_compared": row.what,
        "status": row.status,
        "matched": False,
        "oracle_source": None,
        "tolerance": None,
        "max_abs_deviation": None,
        "n_values_compared": 0,
        "values": [],
        "reason": row.reason,
        "suite_tests": list(row.suite_tests),
    }
    if row.engine is None or row.oracle is None:
        return out
    try:
        expected, tol, source = row.oracle(oracles)
    except OracleAbsent as exc:
        out.update(status="no_oracle_recorded", reason=str(exc))
        return out
    except OracleFileMissing as exc:
        out.update(status="not_matched", reason=f"oracle_file_missing: {exc.name}")
        return out
    except OracleFileUnreadable as exc:
        out.update(status="not_matched", reason=f"oracle_file_unreadable: {exc}")
        return out
    except RCaptureInputMismatch as exc:
        out.update(status="not_matched", reason=f"r_capture_input_mismatch: {exc}")
        return out
    except ComparedInRunner as exc:
        out.update(
            status=exc.status,
            reason=exc.reason,
            max_abs_deviation=exc.max_abs_deviation,
            suite_tests=list(F13_RUNNER_SUITE),
        )
        return out
    except Exception as exc:  # noqa: BLE001 - reported as the row's reason
        out.update(status="not_matched", reason=f"oracle_error: {type(exc).__name__}")
        return out
    out["oracle_source"] = source
    out["tolerance"] = {
        "class": row.tolerance_class,
        "value": TOLERANCES[row.tolerance_class or "closed_form"],
        "rule": TOLERANCE_RULES[row.tolerance_class or "closed_form"],
    }
    try:
        got = row.engine()
    except OptionalDependencyMissing as exc:
        out.update(status="not_matched", reason=f"optional_dependency_missing: {exc.package}")
        return out
    except Exception as exc:  # noqa: BLE001 - reported as the row's reason
        out.update(status="not_matched", reason=f"engine_error: {type(exc).__name__}")
        return out
    if not isinstance(got, dict):
        out.update(status="not_matched", reason=f"engine_error: returned {type(got).__name__}")
        return out
    worst: float | None = 0.0
    all_in = True
    values = []
    not_compared: list[str] = []
    for name in sorted(set(row.compares) | set(expected)):
        oracle_value = _number(expected.get(name))
        engine_value = _number(got.get(name))
        if oracle_value is None or engine_value is None:
            dev = None
            within = False
            worst = None
            if engine_value is None:
                not_compared.append(f"engine value {_why_not_compared(got.get(name))}: {name}")
            if oracle_value is None:
                not_compared.append(f"oracle value {_why_not_compared(expected.get(name))}: {name}")
        else:
            dev = abs(engine_value - oracle_value)
            within = dev <= tol[name]
            if worst is not None:
                worst = max(worst, dev)
        all_in = all_in and within
        values.append(
            {
                "name": name,
                "engine": engine_value,
                "oracle": oracle_value,
                "abs_deviation": dev,
                "tolerance": tol.get(name),
                "within": within,
            }
        )
    out["values"] = values
    out["n_values_compared"] = len(values)
    out["max_abs_deviation"] = worst if values else None
    out["matched"] = bool(values) and all_in
    out["status"] = "matched" if out["matched"] else "not_matched"
    if not out["matched"] and out["reason"] is None:
        outside = [v["name"] for v in values if v["abs_deviation"] is not None and not v["within"]]
        parts = list(not_compared)
        if outside:
            parts.append("outside tolerance: " + ", ".join(outside))
        out["reason"] = "; ".join(parts) or "no value compared"
    return out


#: :func:`git_sha`'s reason when the directory three levels up has ``.git`` and
#: ``pyproject.toml`` but is not the proofpack source checkout the package was imported
#: from (lens FA-R1: a wheel installed with ``pip --target vendor`` inside the customer's
#: own git repository recorded that repository's HEAD).
NOT_THE_PROOFPACK_CHECKOUT = (
    "not a proofpack source checkout (the package is not <checkout>/src/proofpack of a "
    "pyproject.toml naming proofpack); the enclosing git repository is not read"
)
GIT_SHA_SOURCE = (
    "git rev-parse HEAD in the proofpack source checkout the package was imported from "
    "(src/proofpack; pyproject.toml names proofpack)"
)


def _is_proofpack_checkout(root: Path, package_dir: Path) -> bool:
    import tomllib  # noqa: PLC0415

    if package_dir != (root / "src" / "proofpack").resolve():
        return False
    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (project.get("project") or {}).get("name") == "proofpack"


def source_checkout_root() -> Path | None:
    """``<root>`` when this package is ``<root>/src/proofpack`` and ``<root>/pyproject.toml``
    names the project ``proofpack``; ``None`` otherwise."""
    package_dir = Path(__file__).resolve().parent
    root = package_dir.parent.parent
    return root if _is_proofpack_checkout(root, package_dir) else None


def git_sha() -> tuple[str | None, str]:
    """``(sha, source)`` of the proofpack source checkout the package was imported from;
    ``(None, reason)`` otherwise."""
    package_dir = Path(__file__).resolve().parent
    root = package_dir.parent.parent
    if not (root / ".git").exists() or not (root / "pyproject.toml").exists():
        return None, "not a git checkout (an installed wheel carries no git metadata)"
    if not _is_proofpack_checkout(root, package_dir):
        return None, NOT_THE_PROOFPACK_CHECKOUT
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"git not runnable: {type(exc).__name__}"
    sha = proc.stdout.strip()
    if proc.returncode != 0 or len(sha) != 40:
        return None, "git rev-parse HEAD did not return a commit"
    if dirty.returncode != 0:
        state = "tracked-file state not read (git status failed)"
    else:
        state = "tracked files modified" if dirty.stdout.strip() else "tracked files unmodified"
    return sha, f"{GIT_SHA_SOURCE}; {state}"


def _numpy_version() -> str:
    return str(np.__version__)


def summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    counts["rows"] = len(rows)
    return counts


def exit_code_for(rows: list[dict[str, Any]]) -> int:
    """0 when no row is ``not_matched``, :data:`EXIT_FIXTURES_NOT_MATCHED` otherwise."""
    return EXIT_FIXTURES_NOT_MATCHED if any(r["status"] == "not_matched" for r in rows) else EXIT_OK


#: :func:`r_captures_status` when rows F13 and F13b each hold one or more values whose
#: ``abs_deviation`` is a number (an engine value and an oracle value both read; E12
#: repair 2, lens 2 FA-B4: repair 1 counted ``n_values_compared``, the names tried, so a
#: capture with ``values`` ``{}`` read as present).
R_CAPTURES_PRESENT = "present_compared_in_rows_f13_f13b"
#: :func:`r_captures_status` in every other case: the two rows are not both
#: ``no_oracle_recorded`` and do not both hold a value with a numeric ``abs_deviation``
#: (inputs fed in ``tests/test_e12_repair1.py::test_fa_b2_*`` and
#: ``tests/test_e12_repair2.py::test_fa_b4_*``).
R_CAPTURES_PARTIAL = "partial_see_rows_f13_f13b"


def _deviations_read(row: dict[str, Any]) -> int:
    """How many of ``row["values"]`` carry a numeric ``abs_deviation``; for F13 read from
    the r-captures job's recorded comparison (``suite_only``, DEC-77), the names that
    comparison recorded when its ``max_abs_deviation`` is a number."""
    if row["status"] == "suite_only" and row["max_abs_deviation"] is not None:
        return len(F13_NAMES)
    return sum(1 for v in row["values"] if v["abs_deviation"] is not None)


def r_captures_status(caps: RCaptures | None = None) -> dict[str, Any]:
    """The ``--r-captures`` line, derived from the two report rows :func:`r_capture_rows`
    gives on ``caps`` (default :func:`load_r_captures`), not from which files exist (E12
    repair 1, lens 1 FA-B2). ``status``: :data:`R_CAPTURES_NOT_CAPTURED` when both rows are
    ``no_oracle_recorded``; :data:`R_CAPTURES_PRESENT` when each row holds one or more
    values with a numeric ``abs_deviation`` (F13 read from the job's recorded comparison:
    ``suite_only`` with a numeric ``max_abs_deviation``); :data:`R_CAPTURES_PARTIAL`
    otherwise. The line names the files read, the files unreadable, the files absent and
    each row's status; outside the r-captures job (:data:`R_VECTORS_ENV` not set) the
    vectors are not counted absent and the line says where they are read. The inputs the
    tests feed are in ``tests/test_e12_repair1.py`` (``test_fa_b2_*``),
    ``tests/test_e12_repair2.py`` (``test_fa_b4_*``) and ``tests/test_e12_repair3.py``."""
    caps = load_r_captures() if caps is None else caps
    rows = [compare_row(r, {}) for r in r_capture_rows(caps)]
    status = (
        R_CAPTURES_NOT_CAPTURED
        if all(r["status"] == "no_oracle_recorded" for r in rows)
        else R_CAPTURES_PRESENT
        if all(_deviations_read(r) > 0 for r in rows)
        else R_CAPTURES_PARTIAL
    )
    local = caps.vectors_path is None
    every = (*R_CAPTURE_FILES, R_COMPARISON_FILE) if local else (*R_CAPTURE_FILES, R_VECTORS_FILE)
    unreadable = [f for f, _ in caps.unreadable]
    absent = [f for f in every if f not in caps.present and f not in unreadable]
    row_text = ", ".join(f"row {r['id']} {r['status']}" for r in rows)
    if local:
        row_text += "; the aSAH vectors are read inside the r-captures job only (DEC-77)"
    if caps.directory is None:
        line = (
            f"r-captures: {status} - an installed package reads no R capture (fixtures/r/ is "
            f"read from a proofpack source checkout only); {row_text}"
        )
    elif status == R_CAPTURES_NOT_CAPTURED and not caps.present and not unreadable:
        line = (
            f"r-captures: {R_CAPTURES_NOT_CAPTURED} - no R capture is committed "
            f"({', '.join(R_CAPTURE_FILES)}); F13 and F13b stay 'no oracle recorded' "
            "until fixtures/r/capture.R's output is committed"
        )
    else:
        line = (
            f"r-captures: {status} - read: {', '.join(caps.present) or 'none'}; unreadable: "
            f"{', '.join(unreadable) or 'none'}; absent: {', '.join(absent) or 'none'}; "
            f"{row_text}"
        )
    return {
        "files": list(R_CAPTURE_FILES),
        "present": [f for f in R_CAPTURE_FILES if f in caps.present],
        "unreadable": unreadable,
        "rows": {r["id"]: r["status"] for r in rows},
        "status": status,
        "line": line,
    }


def run_fixtures(
    *,
    oracles: dict[str, Any] | None = None,
    rows: tuple[Row, ...] | None = None,
    doctor: bool = True,
) -> dict[str, Any]:
    """Build the report (writes nothing). ``oracles`` / ``rows`` are the test hooks for a
    planted oracle and a planted register; the CLI passes neither."""
    t0 = time.perf_counter()
    oracles = oracles if oracles is not None else load_oracles()
    out_rows = [compare_row(r, oracles) for r in (rows if rows is not None else register())]
    sha, sha_source = git_sha()
    plat = platform_tag()
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA_ID,
        "engine_version": __version__,
        "git_sha": sha,
        "git_sha_source": sha_source,
        "platform": plat,
        "reference_platform": REFERENCE_PLATFORM,
        "on_reference_platform": plat == REFERENCE_PLATFORM,
        "python": ".".join(str(x) for x in sys.version_info[:3]),
        "numpy": _numpy_version(),
        "scipy": scipy_version(),
        "generated": utc_now_iso(),
        "offline": True,
        "tolerance_policy": {
            "source": TOLERANCE_SOURCE,
            "closed_form": TOLERANCES["closed_form"],
            "iterative": TOLERANCES["iterative"],
            "reported_rounding": TOLERANCE_RULES["reported_rounding"],
            "register": TOLERANCE_RULES["register"],
        },
        "rows": out_rows,
        "summary": summary(out_rows),
        "exit_code": exit_code_for(out_rows),
        "doctor": _doctor_rows() if doctor else [],
        "duration_s": None,
    }
    report["duration_s"] = round(time.perf_counter() - t0, 3)
    return report


def _doctor_rows() -> list[dict[str, Any]]:
    from proofpack.doctor import run_checks  # noqa: PLC0415

    return [
        {"name": c.name, "ok": bool(c.ok), "essential": bool(c.essential), "info": c.info}
        for c in run_checks(offline=True)
    ]


def write_report(report: dict[str, Any], out_dir: str | Path) -> Path:
    from proofpack.manifest import canonical_json  # noqa: PLC0415

    target = Path(out_dir) / REPORT_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json(report))
    return target


def validate_report(report: dict[str, Any]) -> None:
    """Raise ``jsonschema.ValidationError`` when the report does not fit its schema."""
    import jsonschema  # noqa: PLC0415

    from proofpack.resources import load_json_schema  # noqa: PLC0415

    jsonschema.validate(report, load_json_schema("fixtures_report_schema.json"))


def summary_lines(report: dict[str, Any], path: Path | None) -> list[str]:
    s = report["summary"]
    lines = [
        f"fixtures report written: {path}" if path is not None else "fixtures report built",
        f"  rows {s['rows']}: matched {s['matched']}, not matched {s['not_matched']}, "
        f"no oracle recorded {s['no_oracle_recorded']}, no independent oracle "
        f"{s['no_independent_oracle']}, not built {s['not_built']}, "
        f"compared by the test suite only {s['suite_only']}",
        f"  platform {report['platform']} (reference platform {report['reference_platform']}: "
        f"{'yes' if report['on_reference_platform'] else 'no'}); python {report['python']}, "
        f"numpy {report['numpy']}, scipy {report['scipy'] or 'not installed'}",
    ]
    for r in report["rows"]:
        if r["status"] == "not_matched":
            lines.append(f"  not matched: {r['id']} ({r['reason']})")
    return lines
