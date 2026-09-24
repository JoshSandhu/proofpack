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
  captures carried to build days 11-14), or the file is not in this install (F14 in an
  installed wheel: :data:`NEWCOMBE_ABSENT`); never matched;
* ``not_built`` - the engine has no function for the fixture in this version (F5, F7,
  F15, F16, F21, F3's AUPRC); never matched;
* ``suite_only`` - a behaviour the test suite inspects (F12, F17-F20; the row names the
  test file) and this command does not re-run; never matched.

Exit code (:func:`exit_code_for`): ``EXIT_OK`` (0) when every row with an oracle is
``matched``, :data:`proofpack.errors.EXIT_FIXTURES_NOT_MATCHED` (6) when one or more is
``not_matched``. ``no_oracle_recorded``, ``not_built`` and ``suite_only`` rows do not move
the exit code and are never counted as matched
(``tests/test_fixtures_cmd.py::test_rows_without_an_oracle_are_never_counted_as_matched``).

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
    "forms and names Wilson, 2x2, Brier, O/E and PSI; this report also applies it to "
    "F3-auroc, the ECE, reference Brier and IPA values of F4-closed-form and the chi-square "
    "statistic of F6-closed-form, which D1 section 9 does not name",
    "iterative": "absolute deviation at most 1e-6. D1 section 9 gives 1e-6 for iterative "
    "methods and names IRLS slope/intercept and DeLong via placements (F4-irls, F3-delong); "
    "this report also applies it to the Clopper-Pearson rows (a beta quantile) and F6-p, "
    "which D1 section 9 does not name",
    "reported_rounding": "absolute deviation at most half a unit in the last printed decimal "
    "of each value, plus 1e-12. D1 section 9 gives reported rounding for bootstrap CIs "
    "(F3-bootstrap, F9-cluster-bootstrap); this report also applies it to F14-newcombe's "
    "published table, for which D1 section 9 gives no tolerance",
    "register": "absolute deviation at most 1e-4 on the printed value (D1 section 3.2: "
    "'tolerance 1e-4 on the shown rounding')",
}
#: Where each class's number is written: :data:`TOLERANCE_RULES` names the rows each class
#: covers beyond what that section names.
TOLERANCE_SOURCE = (
    "D1 section 9 (closed_form, iterative, reported_rounding); D1 section 3.2 (register)"
)
ROUNDING_SLACK = 1e-12
STATUSES = ("matched", "not_matched", "no_oracle_recorded", "not_built", "suite_only")
#: The R captures D1 section 3.2 names (F13, F13b); none is committed at A-P3.
R_CAPTURE_FILES = ("fixtures/r/proc_asah.json", "fixtures/r/rms_val_prob_f4.json")
R_CAPTURES_NOT_CAPTURED = "r_captures_not_captured"

F2_COUNTS = (90, 10, 20, 180)
F3_Y = (1, 1, 1, 1, 1, 0, 0, 0, 0, 0)
F3_S1 = (0.9, 0.8, 0.7, 0.6, 0.35, 0.75, 0.5, 0.4, 0.3, 0.2)
F3_S2 = (0.85, 0.6, 0.65, 0.4, 0.3, 0.7, 0.55, 0.45, 0.35, 0.25)
F3_SEED = 20240101
F3_B = 2000
F6_SITES = ((45, 5), (38, 12), (27, 3))
F6_HOLM_INPUT = (0.012, 0.04, 0.30)
F1_CASES = {"F1": (81, 263), "F1b": (490, 500), "F1c": (0, 20), "F1d": (20, 20)}


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


class Oracles(dict):
    """The loaded oracle files; looking up a file that did not load raises
    :class:`OracleFileMissing` (a ``KeyError`` would read as an engine error)."""

    def __missing__(self, key: str) -> Any:
        raise OracleFileMissing(key)


def load_oracles() -> dict[str, Any]:
    """The committed oracle files, keyed by the file name each row cites. A file that is
    absent is left out of the mapping (F14's Newcombe table: :data:`NEWCOMBE_ABSENT`; the
    others: :class:`OracleFileMissing` when a row looks it up)."""
    out: dict[str, Any] = Oracles()
    for name in ("oracles_v1.json", "f4_expected.json", "newcombe_table2.json"):
        try:
            out[name] = json.loads(resource_path(name).read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
    return out


#: F14's reason when ``fixtures/newcombe_table2.json`` is absent (an installed wheel): the
#: transcription is [unverified against the primary PDF], and an unverified fixture is not
#: packaged (``tests/test_invariants.py::test_the_fixture_is_not_packaged_into_the_wheel``).
NEWCOMBE_ABSENT = (
    "[unverified against the primary PDF] fixtures/newcombe_table2.json is not shipped in "
    "the wheel (an unverified transcription stays out of the package); F14 is compared in "
    "a source checkout only"
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


def _f14(oracles: dict[str, Any]) -> dict[str, float]:
    from proofpack.stats.proportions import newcombe10_bounds, newcombe11_bounds

    out = {}
    for ex in oracles["newcombe_table2.json"]["examples"]:
        args = (ex["k1"], ex["n1"], ex["k2"], ex["n2"])
        for method, fn in (("method10", newcombe10_bounds), ("method11", newcombe11_bounds)):
            lo, hi = fn(*args)
            out[f"{ex['label']} {method} lower"] = lo
            out[f"{ex['label']} {method} upper"] = hi
    return out


class OptionalDependencyMissing(RuntimeError):
    """A comparison needs a package the install does not have (scipy: ``proofpack[stats]``)."""

    def __init__(self, package: str) -> None:
        self.package = package
        super().__init__(f"{package} is not installed")


# ------------------------------------------------------------------ the register


@dataclass(frozen=True)
class Row:
    """One row of the report. ``engine`` returns the compared values; ``oracle`` returns
    ``(values, per-value tolerance, source)``; a row without either carries ``status``."""

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
    engine_needs_oracles: bool = False


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
    if "newcombe_table2.json" not in o:
        raise OracleAbsent(NEWCOMBE_ABSENT)
    doc = o["newcombe_table2.json"]
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
            ),
            Row(
                f"{fid}-clopper-pearson",
                fid,
                f"Clopper-Pearson 95% interval of {k}/{n} (clopper_pearson_bounds)",
                "iterative",
                lambda k=k, n=n: _f1_cp(k, n),
                _captured(f"{fid}-clopper-pearson", "iterative"),
            ),
            Row(
                f"{fid}-register",
                fid,
                f"Wilson and Clopper-Pearson bounds of {k}/{n} against the printed register",
                "register",
                lambda k=k, n=n: {**_f1_wilson(k, n), **_f1_cp(k, n)},
                _register_oracle(fid),
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
        ),
        Row(
            "F2-register",
            "F2",
            "the same seventeen values against the printed register",
            "register",
            _f2,
            _register_oracle("F2"),
        ),
        Row(
            "F3-auroc",
            "F3",
            "AUROC of s1 and s2 on the ten F3 rows (auroc_mann_whitney)",
            "closed_form",
            _f3_auroc,
            _captured("F3-auroc", "closed_form"),
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
        ),
        Row(
            "F3-register",
            "F3",
            "the F3 AUROCs, s1's DeLong standard error and intervals and the paired test "
            "against the printed register",
            "register",
            _f3_register_values,
            _register_oracle("F3"),
        ),
        Row(
            "F3-bootstrap",
            "F3",
            "stratified bootstrap percentile interval of AUROC(s1), B = 2000, "
            "default_rng(20240101)",
            "reported_rounding",
            lambda: _bootstrap_auroc(False),
            _register_oracle("F3_bootstrap"),
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
        ),
        Row(
            "F4-irls",
            "F4",
            "calibration_block's IRLS intercept-in-the-large, slope and intercept, each with "
            "its Wald standard error",
            "iterative",
            _f4_irls,
            _f4_oracle("irls", "iterative"),
        ),
        Row(
            "F4-register",
            "F4",
            "the F4 calibration values against R2 section 9 as quoted in f4_expected.json "
            "(the five-bin ECE is not emitted by the block and is not compared)",
            "register",
            _f4_register_values,
            _f4_register_oracle,
        ),
        Row(
            "F5",
            "F5",
            "paired McNemar and the accuracy difference on [[80, 10], [2, 8]]",
            status="not_built",
            reason="stats.comparison (McNemar, paired differences) is not in this version",
        ),
        Row(
            "F6-closed-form",
            "F6",
            "sensitivity by site on [45, 5], [38, 12], [27, 3], the chi-square statistic "
            "(heterogeneity_footnote) and Holm on [0.012, 0.04, 0.30] (holm)",
            "closed_form",
            lambda: {k: v for k, v in _f6_closed().items() if not k.startswith("_")},
            _f6_closed_oracle(),
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
        ),
        Row(
            "F6-register",
            "F6",
            "the F6 values against the printed register",
            "register",
            _f6_register_values,
            _register_oracle("F6"),
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
        ),
        Row(
            "F8-register",
            "F8",
            "the three half-widths against the printed register",
            "register",
            _f8,
            _register_oracle("F8"),
        ),
        Row(
            "F9-cluster-bootstrap",
            "F9",
            "cluster-bootstrap percentile interval of AUROC(s1) on the F3 rows each copied "
            "three times under one case id, against F3's printed bootstrap interval",
            "reported_rounding",
            lambda: _bootstrap_auroc(True),
            _register_oracle("F3_bootstrap"),
        ),
        Row(
            "F10-exact",
            "F10",
            "sensitivity and specificity of the F2 table with 6 reference-positive and 4 "
            "reference-negative indeterminates counted each way (indeterminate_both_ways)",
            "closed_form",
            _f10,
            _captured("F10-exact", "closed_form"),
        ),
        Row(
            "F11-ppa-npa",
            "F11",
            "PPA and NPA with their Wilson intervals of the F2 table under "
            "reference_standard type comparator",
            "closed_form",
            _f11,
            _captured("F11-ppa-npa", "closed_form"),
        ),
        Row(
            "F12",
            "F12",
            "HALT codes H01-H11 and exit 3 on the malformed inputs",
            status="suite_only",
            reason="a behaviour, not a value: the test suite inspects each HALT code",
            suite_tests=("tests/test_halt_gates.py",),
        ),
        Row(
            "F13",
            "F13",
            "pROC AUROC and DeLong interval on the aSAH data",
            status="no_oracle_recorded",
            reason="[unverified until captured] the pROC capture (fixtures/r/proc_asah.json) "
            "is carried to build days 11-14",
        ),
        Row(
            "F13b",
            "F13b",
            "rms::val.prob slope and intercept on the F4 rows",
            status="no_oracle_recorded",
            reason="[unverified until captured] the rms::val.prob capture is carried to build "
            "days 11-14 (f4_expected.json r_rms_val_prob: [pending])",
        ),
        Row(
            "F14-newcombe",
            "F14",
            "Newcombe method 10 and method 11 intervals for 56/70 - 48/80, 9/10 - 3/10 and "
            "10/10 - 0/20 (newcombe10_bounds, newcombe11_bounds)",
            "reported_rounding",
            _f14,
            _f14_oracle,
            engine_needs_oracles=True,
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
    ``null``."""
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
        got = row.engine(oracles) if row.engine_needs_oracles else row.engine()
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
    for name in sorted(expected):
        oracle_value = _number(expected[name])
        engine_value = _number(got.get(name))
        if oracle_value is None or engine_value is None:
            dev = None
            within = False
            worst = None
            if engine_value is None:
                not_compared.append(f"engine value {_why_not_compared(got.get(name))}: {name}")
            if oracle_value is None:
                not_compared.append(f"oracle value {_why_not_compared(expected[name])}: {name}")
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
                "tolerance": tol[name],
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


def r_captures_status() -> dict[str, Any]:
    from proofpack.resources import _REPO_ROOT  # noqa: PLC0415 - dev checkout only

    present = [f for f in R_CAPTURE_FILES if (_REPO_ROOT / f).exists()]
    return {
        "files": list(R_CAPTURE_FILES),
        "present": present,
        "status": "present_not_compared" if present else R_CAPTURES_NOT_CAPTURED,
        "line": (
            f"r-captures: {R_CAPTURES_NOT_CAPTURED} - no R capture is committed "
            f"({', '.join(R_CAPTURE_FILES)}); F13 and F13b stay 'no oracle recorded' "
            "until build days 11-14 capture them"
            if not present
            else "r-captures: present_not_compared - this engine version has no comparison "
            "for them; F13 and F13b stay 'no oracle recorded'"
        ),
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
        f"no oracle recorded {s['no_oracle_recorded']}, not built {s['not_built']}, "
        f"compared by the test suite only {s['suite_only']}",
        f"  platform {report['platform']} (reference platform {report['reference_platform']}: "
        f"{'yes' if report['on_reference_platform'] else 'no'}); python {report['python']}, "
        f"numpy {report['numpy']}, scipy {report['scipy'] or 'not installed'}",
    ]
    for r in report["rows"]:
        if r["status"] == "not_matched":
            lines.append(f"  not matched: {r['id']} ({r['reason']})")
    return lines
