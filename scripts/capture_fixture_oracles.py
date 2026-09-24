"""Capture the full-precision oracles ``proofpack fixtures`` compares against (A-P3, day 9).

    python scripts/capture_fixture_oracles.py            # rewrites fixtures/oracles_v1.json
    python scripts/capture_fixture_oracles.py --check    # compares a fresh capture with it
    python scripts/capture_fixture_oracles.py --check --committed PATH   # ... with PATH

Nothing here imports ``proofpack``. Each value is computed by one of:

* **statsmodels** ``proportion_confint`` (``method="wilson"`` and ``"beta"``) and
  ``multipletests(method="holm")``;
* **scipy** ``chi2_contingency(correction=False)``;
* **scikit-learn** ``roc_auc_score``;
* **exact rational arithmetic** (``fractions.Fraction``) from the 2x2 formulae written
  out below, converted to float once at the end (``math.sqrt`` for MCC);
* a **hand-written O(m n) DeLong** (DeLong, DeLong and Clarke-Pearson 1988, structural
  components V10 / V01 with the indicator psi(x, y) = 1, 1/2, 0) - written for this file,
  not a third-party library, and not the engine's Sun and Xu placement code.

The register values (D1 section 3.2, from R2 section 9) are typed from D1 section 3.2 as
printed there, with the number of decimals printed; they are the "published table"
oracles. ``tests/test_fixtures_cmd.py::test_the_committed_oracles_equal_a_fresh_capture``
re-runs this capture and compares it with the committed file (skipped where statsmodels
or scikit-learn is absent, as in a customer's install).

``--check`` (A-P3 repair 3, CI-1). The committed file records the platform it was captured
on (``captured_on_platform``: ``sysconfig.get_platform()`` and the CPython tag). A fresh
capture is compared with it in two parts. Everything outside ``captured`` (``register``,
``register_decimals``, ``schema``, ``captured_by``, ``register_source``) and each entry's
``kind``, ``source`` and value names are compared for equality. Each captured value is
compared as a number, under the tolerance class the ``proofpack fixtures`` row that reads
it uses (:data:`CAPTURED_CLASS`; D1 section 9 gives 1e-9 for closed-form values and 1e-6
for iterative ones on platforms other than the reference platform, and the committed file
was not captured on the reference platform). Each value whose float differs is printed
with both figures, the absolute difference and its tolerance. The exit code is 1 when
:func:`compare` returns False and 0 when it returns True. ``tests/test_ap3_repair3.py``
feeds: ``F1-wilson`` ``wilson_lo`` +2e-9 (exit 1), ``F3-delong`` ``paired_p`` +1e-12
(exit 0), ``F6-homogeneity`` ``chi2`` and ``chi2_p`` each +5e-7 (False, True), a changed
``source``, an extra value name, a value ``true`` and a changed ``register`` value (each
False), and a changed platform and numpy version (True).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import sysconfig
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TARGET = REPO / "fixtures" / "oracles_v1.json"

F1_CASES = {"F1": (81, 263), "F1b": (490, 500), "F1c": (0, 20), "F1d": (20, 20)}
F2 = {"tp": 90, "fn": 10, "fp": 20, "tn": 180}
F3_Y = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
F3_S1 = [0.9, 0.8, 0.7, 0.6, 0.35, 0.75, 0.5, 0.4, 0.3, 0.2]
F3_S2 = [0.85, 0.6, 0.65, 0.4, 0.3, 0.7, 0.55, 0.45, 0.35, 0.25]
F6_SITES = [(45, 5), (38, 12), (27, 3)]
F6_HOLM_INPUT = [0.012, 0.04, 0.30]
F8_N = (50, 100, 300)

#: D1 section 9's tolerances for agreement off the reference platform.
TOLERANCE = {"closed_form": 1e-9, "iterative": 1e-6}
#: The tolerance class each captured value is compared under by ``--check``: the class of
#: the ``proofpack fixtures`` row that reads it (src/proofpack/fixtures.py ``register()``;
#: ``tests/test_ap3_repair3.py::test_the_check_classes_are_the_fixtures_rows_classes``
#: compares the two value by value). A str applies to every value of the entry; a dict
#: names the values of another class and the ``_default``.
CAPTURED_CLASS: dict[str, str | dict[str, str]] = {
    **{f"{fid}-wilson": "closed_form" for fid in F1_CASES},
    **{f"{fid}-clopper-pearson": "iterative" for fid in F1_CASES},
    "F2-exact": "closed_form",
    "F3-auroc": "closed_form",
    "F3-delong": "iterative",
    "F6-homogeneity": {"chi2_p": "iterative", "_default": "closed_form"},
    "F8-half-width": "closed_form",
    "F10-exact": "closed_form",
    "F11-ppa-npa": "closed_form",
}
#: Keys of the file that record where and with what it was captured; not compared.
NOT_COMPARED = ("library_versions", "captured_on_platform")

#: D1 section 3.2 as printed (R2 section 9); decimals = digits after the point there.
REGISTER = {
    "F1": {"wilson_lo": 0.2553, "wilson_hi": 0.3662, "cp_lo": 0.2527, "cp_hi": 0.3676},
    "F1b": {"wilson_lo": 0.9636, "wilson_hi": 0.9891, "cp_lo": 0.9635, "cp_hi": 0.9904},
    "F1c": {"wilson_lo": 0.0, "wilson_hi": 0.1611, "cp_lo": 0.0, "cp_hi": 0.1684},
    "F1d": {"wilson_lo": 0.8389, "wilson_hi": 1.0, "cp_lo": 0.8316, "cp_hi": 1.0},
    "F2": {
        "sensitivity": 0.90,
        "sensitivity_ci_lo": 0.8256,
        "sensitivity_ci_hi": 0.9448,
        "specificity": 0.90,
        "specificity_ci_lo": 0.8506,
        "specificity_ci_hi": 0.9343,
        "ppv": 0.8182,
        "npv": 0.9474,
        "prevalence": 0.3333,
        "lr_pos": 9.0,
        "lr_neg": 0.1111,
        "dor": 81.0,
        "youden": 0.80,
        "f1": 0.8571,
        "mcc": 0.7826,
        "ppv_at_0.05": 0.3214,
        "npv_at_0.05": 0.9942,
    },
    "F3": {
        "auc_s1": 0.80,
        "delong_se_s1": 0.1549,
        "logit_ci_lo_s1": 0.3748,
        "logit_ci_hi_s1": 0.9639,
        "wald_ci_lo_s1": 0.4964,
        "wald_ci_hi_s1": 1.1036,
        "auc_s2": 0.64,
        "paired_var_diff": 0.0072,
        "paired_z": 1.8856,
        "paired_p": 0.0593,
    },
    "F3_bootstrap": {"ci_lo": 0.44, "ci_hi": 1.00},
    "F6": {
        "se_site1": 0.90,
        "se_site2": 0.76,
        "se_site3": 0.90,
        "chi2": 4.6327,
        "chi2_p": 0.0986,
        "holm_1": 0.036,
        "holm_2": 0.08,
        "holm_3": 0.30,
    },
    "F8": {"half_width_n50": 0.0851, "half_width_n100": 0.0596, "half_width_n300": 0.0341},
}
#: The printed decimals per register value where they differ from 4 (D1 prints 0.90,
#: 0.80, 0.64, 0.44 / 1.00 and the Holm figures to 2 or 3 places; 9.0 and 81 to 1 / 0).
REGISTER_DECIMALS = {
    "F1": 4,
    "F1b": 4,
    "F1c": 4,
    "F1d": 4,
    "F2": {
        "sensitivity": 2,
        "specificity": 2,
        "lr_pos": 1,
        "dor": 0,
        "youden": 2,
        "_default": 4,
    },
    "F3": {"auc_s1": 2, "auc_s2": 2, "_default": 4},
    "F3_bootstrap": 2,
    "F6": {
        "se_site1": 2,
        "se_site2": 2,
        "se_site3": 2,
        "holm_1": 3,
        "holm_2": 2,
        "holm_3": 2,
        "_default": 4,
    },
    "F8": 4,
}


def _versions() -> dict[str, str]:
    import numpy
    import scipy
    import sklearn
    import statsmodels

    return {
        "statsmodels": statsmodels.__version__,
        "scipy": scipy.__version__,
        "scikit-learn": sklearn.__version__,
        "numpy": numpy.__version__,
        "python": ".".join(str(x) for x in sys.version_info[:3]),
    }


def _sm_ci(k: int, n: int, method: str) -> tuple[float, float]:
    from statsmodels.stats.proportion import proportion_confint

    lo, hi = proportion_confint(k, n, alpha=0.05, method=method)
    # statsmodels returns nan at the boundary for "beta": the bound is 0 or 1 there
    lo = 0.0 if lo != lo else float(lo)
    hi = 1.0 if hi != hi else float(hi)
    return lo, hi


def _f2_exact() -> dict[str, float]:
    tp, fn, fp, tn = (Fraction(F2[k]) for k in ("tp", "fn", "fp", "tn"))
    se, sp = tp / (tp + fn), tn / (tn + fp)
    ppv, npv = tp / (tp + fp), tn / (tn + fn)
    n = tp + fn + fp + tn
    lr_pos, lr_neg = se / (1 - sp), (1 - se) / sp
    out = {
        "sensitivity": se,
        "specificity": sp,
        "ppv": ppv,
        "npv": npv,
        "prevalence": (tp + fn) / n,
        "lr_pos": lr_pos,
        "lr_neg": lr_neg,
        "dor": (tp * tn) / (fp * fn),
        "youden": se + sp - 1,
        "f1": 2 * tp / (2 * tp + fp + fn),
    }
    for prev, key in ((Fraction(5, 100), "0.05"),):
        out[f"ppv_at_{key}"] = se * prev / (se * prev + (1 - sp) * (1 - prev))
        out[f"npv_at_{key}"] = sp * (1 - prev) / (sp * (1 - prev) + (1 - se) * prev)
    values = {k: float(v) for k, v in out.items()}
    num = tp * tn - fp * fn
    den = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    values["mcc"] = float(num) / math.sqrt(float(den))
    for key, k, m in (("sensitivity", 90, 100), ("specificity", 180, 200)):
        lo, hi = _sm_ci(k, m, "wilson")
        values[f"{key}_ci_lo"], values[f"{key}_ci_hi"] = lo, hi
    return values


def _psi(x: float, y: float) -> float:
    return 1.0 if x > y else (0.5 if x == y else 0.0)


def _delong_components(scores: list[float], y: list[int]) -> tuple[list[float], list[float]]:
    pos = [s for s, t in zip(scores, y, strict=True) if t == 1]
    neg = [s for s, t in zip(scores, y, strict=True) if t == 0]
    v10 = [sum(_psi(x, yy) for yy in neg) / len(neg) for x in pos]
    v01 = [sum(_psi(x, yy) for x in pos) / len(pos) for yy in neg]
    return v10, v01


def _cov(a: list[float], b: list[float]) -> float:
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    return sum((x - ma) * (z - mb) for x, z in zip(a, b, strict=True)) / (len(a) - 1)


def _f3() -> dict[str, float]:
    from scipy.stats import norm
    from sklearn.metrics import roc_auc_score

    v10a, v01a = _delong_components(F3_S1, F3_Y)
    v10b, v01b = _delong_components(F3_S2, F3_Y)
    m, n = len(v10a), len(v01a)
    auc_a, auc_b = sum(v10a) / m, sum(v10b) / m
    var_a = _cov(v10a, v10a) / m + _cov(v01a, v01a) / n
    var_b = _cov(v10b, v10b) / m + _cov(v01b, v01b) / n
    cov_ab = _cov(v10a, v10b) / m + _cov(v01a, v01b) / n
    var_diff = var_a + var_b - 2 * cov_ab
    z = (auc_a - auc_b) / math.sqrt(var_diff)
    zq = float(norm.ppf(0.975))
    se_a = math.sqrt(var_a)
    eta, se_eta = math.log(auc_a / (1 - auc_a)), se_a / (auc_a * (1 - auc_a))
    return {
        "auc_s1_sklearn": float(roc_auc_score(F3_Y, F3_S1)),
        "auc_s2_sklearn": float(roc_auc_score(F3_Y, F3_S2)),
        "delong_se_s1": se_a,
        "delong_se_s2": math.sqrt(var_b),
        "logit_ci_lo_s1": 1 / (1 + math.exp(-(eta - zq * se_eta))),
        "logit_ci_hi_s1": 1 / (1 + math.exp(-(eta + zq * se_eta))),
        "wald_ci_lo_s1": auc_a - zq * se_a,
        "wald_ci_hi_s1": auc_a + zq * se_a,
        "paired_var_diff": var_diff,
        "paired_z": z,
        "paired_p": math.erfc(abs(z) / math.sqrt(2.0)),
    }


def _f6() -> dict[str, float]:
    import numpy as np
    from scipy.stats import chi2_contingency
    from statsmodels.stats.multitest import multipletests

    stat, p, _dof, _ = chi2_contingency(np.array(F6_SITES, dtype=float), correction=False)
    holm = multipletests(F6_HOLM_INPUT, method="holm")[1]
    out = {f"se_site{i + 1}": float(Fraction(s, s + f)) for i, (s, f) in enumerate(F6_SITES)}
    out["chi2"] = float(stat)
    out["chi2_p"] = float(p)
    out.update({f"holm_{i + 1}": float(v) for i, v in enumerate(holm)})
    return out


def capture() -> dict:
    versions = _versions()
    sm = f"statsmodels {versions['statsmodels']}"
    entries: dict[str, dict] = {}
    for fid, (k, n) in F1_CASES.items():
        lo, hi = _sm_ci(k, n, "wilson")
        entries[f"{fid}-wilson"] = {
            "source": f"{sm} proportion_confint({k}, {n}, alpha=0.05, method='wilson')",
            "kind": "captured_library",
            "values": {"wilson_lo": lo, "wilson_hi": hi},
        }
        clo, chi = _sm_ci(k, n, "beta")
        entries[f"{fid}-clopper-pearson"] = {
            "source": f"{sm} proportion_confint({k}, {n}, alpha=0.05, method='beta')",
            "kind": "captured_library",
            "values": {"cp_lo": clo, "cp_hi": chi},
        }
    entries["F2-exact"] = {
        "source": (
            "exact rational arithmetic (fractions.Fraction) from the 2x2 formulae in "
            f"scripts/capture_fixture_oracles.py; the two Wilson intervals from {sm} "
            "proportion_confint(method='wilson')"
        ),
        "kind": "captured_formula",
        "values": _f2_exact(),
    }
    f3 = _f3()
    entries["F3-auroc"] = {
        "source": f"scikit-learn {versions['scikit-learn']} roc_auc_score",
        "kind": "captured_library",
        "values": {"auc_s1": f3["auc_s1_sklearn"], "auc_s2": f3["auc_s2_sklearn"]},
    }
    entries["F3-delong"] = {
        "source": (
            "hand-written O(m n) DeLong 1988 structural components in "
            "scripts/capture_fixture_oracles.py (not a third-party library; not the engine's "
            f"Sun and Xu code); normal quantile from scipy {versions['scipy']} norm.ppf(0.975)"
        ),
        "kind": "captured_formula",
        "values": {k: v for k, v in f3.items() if not k.endswith("_sklearn")},
    }
    entries["F6-homogeneity"] = {
        "source": (
            f"scipy {versions['scipy']} chi2_contingency(correction=False); {sm} "
            "multipletests(method='holm'); the three proportions as exact fractions"
        ),
        "kind": "captured_library",
        "values": _f6(),
    }
    f2 = entries["F2-exact"]["values"]
    entries["F10-exact"] = {
        "source": (
            "D1 section 3.2 F10, printed as fractions (96/106, 180/204, 90/106, 184/204); "
            "each converted from fractions.Fraction to float here"
        ),
        "kind": "register_fraction",
        "values": {
            "as_positive_sensitivity": float(Fraction(96, 106)),
            "as_positive_specificity": float(Fraction(180, 204)),
            "as_negative_sensitivity": float(Fraction(90, 106)),
            "as_negative_specificity": float(Fraction(184, 204)),
        },
    }
    entries["F11-ppa-npa"] = {
        "source": (
            "D1 section 3.2 F11 (identical numbers to F2 under the comparator labels): the F2 "
            f"sensitivity and specificity above, with their {sm} Wilson intervals"
        ),
        "kind": "captured_library",
        "values": {
            "ppa": f2["sensitivity"],
            "ppa_ci_lo": f2["sensitivity_ci_lo"],
            "ppa_ci_hi": f2["sensitivity_ci_hi"],
            "npa": f2["specificity"],
            "npa_ci_lo": f2["specificity_ci_lo"],
            "npa_ci_hi": f2["specificity_ci_hi"],
        },
    }
    f8 = {}
    for n in F8_N:
        lo, hi = _sm_ci(round(0.9 * n), n, "wilson")
        f8[f"half_width_n{n}"] = (hi - lo) / 2
    entries["F8-half-width"] = {
        "source": f"{sm} proportion_confint(0.9 n, n, method='wilson'), (hi - lo) / 2",
        "kind": "captured_library",
        "values": f8,
    }
    return {
        "schema": "proofpack-fixture-oracles/1",
        "captured_by": "scripts/capture_fixture_oracles.py",
        "captured_on_platform": platform_tag(),
        "library_versions": versions,
        "register_source": (
            "D1 section 3.2 fixture register (values computed in R2 section 9), typed as printed"
        ),
        "register": REGISTER,
        "register_decimals": REGISTER_DECIMALS,
        "captured": entries,
    }


def dumps(doc: dict) -> str:
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def platform_tag() -> str:
    """``sysconfig.get_platform()`` and the CPython tag, e.g. ``win-amd64 cp314``."""
    return f"{sysconfig.get_platform()} cp{sys.version_info[0]}{sys.version_info[1]}"


def comparable(doc: dict) -> dict:
    """The file without :data:`NOT_COMPARED` (a fresh capture on another machine carries its
    own versions and platform)."""
    return {k: v for k, v in doc.items() if k not in NOT_COMPARED}


def value_class(entry: str, name: str) -> str | None:
    cls = CAPTURED_CLASS.get(entry)
    if isinstance(cls, dict):
        return cls.get(name, cls["_default"])
    return cls


def _is_number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def compare(committed: dict, fresh: dict) -> tuple[list[str], bool]:
    """The lines ``--check`` prints, and False when a line reports a value outside its
    tolerance or a part compared for equality that differs."""
    lines: list[str] = []
    ok = True
    a, b = comparable(committed), comparable(fresh)
    for key in sorted((set(a) | set(b)) - {"captured"}):
        if a.get(key) != b.get(key):
            ok = False
            lines.append(f"{key}: differs (compared for equality)")
    ca, cb = a.get("captured", {}), b.get("captured", {})
    for entry in sorted(set(ca) ^ set(cb)):
        ok = False
        where = "committed file" if entry in ca else "fresh capture"
        lines.append(f"captured.{entry}: present in the {where} only")
    counts = {"identical": 0, "within": 0, "outside": 0}
    for entry in sorted(set(ca) & set(cb)):
        ea, eb = ca[entry], cb[entry]
        for field in ("kind", "source"):
            if ea.get(field) != eb.get(field):
                ok = False
                lines.append(
                    f"captured.{entry}.{field}: committed {ea.get(field)!r} fresh {eb.get(field)!r}"
                )
        va, vb = ea.get("values", {}), eb.get("values", {})
        for name in sorted(set(va) ^ set(vb)):
            ok = False
            where = "committed file" if name in va else "fresh capture"
            lines.append(f"captured.{entry}.values.{name}: present in the {where} only")
        for name in sorted(set(va) & set(vb)):
            x, y = va[name], vb[name]
            cls = value_class(entry, name)
            label = f"captured.{entry}.values.{name}"
            if cls is None:
                ok = False
                lines.append(f"{label}: no tolerance class in CAPTURED_CLASS")
                continue
            if not (_is_number(x) and _is_number(y)):
                ok = False
                lines.append(f"{label}: not a number (committed {x!r}, fresh {y!r})")
                continue
            if float(x) == float(y):
                counts["identical"] += 1
                continue
            dev = abs(float(x) - float(y))
            tol = TOLERANCE[cls]
            within = dev <= tol
            counts["within" if within else "outside"] += 1
            ok = ok and within
            lines.append(
                f"{label}: committed {float(x)!r} fresh {float(y)!r} abs difference "
                f"{dev:.3e} {cls} tolerance {tol:g} {'within' if within else 'OUTSIDE'}"
            )
    lines.append(
        f"captured values: {counts['identical']} identical, {counts['within']} differ within "
        f"their tolerance, {counts['outside']} differ outside it"
    )
    lines.append(
        f"committed file captured on {committed.get('captured_on_platform', '(not recorded)')} "
        f"with {committed.get('library_versions')}; fresh capture on "
        f"{fresh.get('captured_on_platform')} with {fresh.get('library_versions')}"
    )
    return lines, ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument(
        "--committed",
        type=Path,
        default=TARGET,
        help="with --check: the file to compare with (default fixtures/oracles_v1.json)",
    )
    args = ap.parse_args(argv)
    doc = capture()
    if args.check:
        committed = json.loads(args.committed.read_text(encoding="utf-8"))
        lines, ok = compare(committed, json.loads(dumps(doc)))
        print("\n".join(lines))
        return 0 if ok else 1
    TARGET.write_bytes(dumps(doc).encode("utf-8"))
    print(f"wrote {TARGET.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
