"""Writes ``tests/fixtures/mapping/*.csv`` and the ``*.expected.json`` beside each.

Every value is synthetic (seeded numpy, seed 20260918); only the HEADER SETS follow the
public datasets. The expected roles and confidences are AUTHORED here from the rules in
``io.mapping``'s docstring - they are not produced by running the mapper, so the
fixture-driven test (``tests/test_mapping_full.py::test_fixture_roles_and_confidences``)
compares two independent readings of the same rules.

Header provenance (fetched in the Claude in-app browser, 18 September 2026):

* PhysioNet/CinC 2019 (https://physionet.org/content/challenge-2019/1.0.0/): the 41
  columns HR ... SepsisLabel; ``Gender`` is "Female (0) or Male (1)"; ``Age`` in years
  (100 for 90 or above); one file per subject (``p00101.psv``), so the patient id is the
  file name - here it arrives as a column ``patient`` [decision]. The two hospital
  systems (training set A and B) are the site attribute (R3); here ``hospital`` = A/B
  [decision]. The prediction columns ``PredictedProbability`` / ``PredictedLabel`` are the
  challenge's sample-code output names [unverified on the fetched page, which only says
  "the risk of sepsis (a real number) and a binary sepsis prediction (0 or 1)"]. Only the
  8 vital-sign columns and the 6 demographic columns are carried; the 26 laboratory
  columns are omitted (they map to ignore like the vitals).
* Diabetes 130-US hospitals (https://archive.ics.uci.edu/dataset/296/...): the fetched
  variables table (first page) confirms encounter_id, patient_nbr, race, gender (male,
  female, unknown/invalid), age ([0, 10) ... [90, 100)), weight, admission_type_id,
  discharge_disposition_id, admission_source_id, time_in_hospital. The remaining headers
  used here (payer_code ... readmitted) are from the same dataset's CSV [unverified on the
  fetched page - later pages of the table were not opened]. The public file carries no
  hospital identifier and no model output; ``hospital`` (H01..H05) and ``pred_prob`` are
  appended [decision].
* MIMIC-IV Clinical Database Demo 2.2 (https://physionet.org/content/mimic-iv-demo/2.2/):
  the fetched page names ``subject_id`` and ``anchor_year_group``; ``hadm_id``, ``gender``,
  ``anchor_age``, ``race``, ``admittime``, ``dischtime`` are the patients/admissions
  columns per the MIMIC-IV documentation [unverified on the fetched page].

Usage: ``python scripts/make_mapping_fixtures.py`` (idempotent; overwrites).
"""

from __future__ import annotations

import csv
import json
import unicodedata
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "mapping"
SEED = 20260918
N = 50

IGN = ["ignore", "high"]
NOTE_01 = "no dictionary declared for 0/1"
NOTE_12 = "no dictionary declared for 1/2"


def rng() -> np.random.Generator:
    return np.random.default_rng(SEED)


def _fmt(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float):
        return f"{x:.4f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))
    return str(x)


# --------------------------------------------------------------------------- base tables


def sepsis_columns(n: int = N, *, gender: str = "01", label: str = "01", score: str = "prob"):
    r = rng()
    patients = [f"p{100 + i // 5:06d}" for i in range(n)]  # 5 hourly rows per subject
    iculos = [i % 5 + 1 for i in range(n)]
    y = (r.random(n) < 0.3).astype(int)  # ~15 positives so both label counts are >= 10
    prob = np.clip(0.15 + 0.5 * y + r.normal(0, 0.15, n), 0.001, 0.999)
    unit1 = r.integers(0, 2, n)
    cols = {
        "patient": patients,
        "HR": [int(v) if r.random() > 0.1 else None for v in r.integers(55, 125, n)],
        "O2Sat": [int(v) if r.random() > 0.1 else None for v in r.integers(88, 101, n)],
        "Temp": [round(float(v), 1) if r.random() > 0.5 else None for v in r.normal(37, 0.7, n)],
        "SBP": [int(v) for v in r.integers(90, 160, n)],
        "MAP": [int(v) for v in r.integers(60, 110, n)],
        "DBP": [int(v) for v in r.integers(50, 95, n)],
        "Resp": [int(v) for v in r.integers(10, 30, n)],
        "EtCO2": [None] * n,
        "Age": [round(float(v), 2) for v in r.uniform(18, 89, n)],
        "Gender": {
            "01": [int(v) for v in r.integers(0, 2, n)],
            "12": [int(v) for v in r.integers(1, 3, n)],
            "mf": [("M", "F")[v] for v in r.integers(0, 2, n)],
        }[gender],
        "Unit1": [int(v) if r.random() > 0.2 else None for v in unit1],
        "Unit2": [int(1 - v) if r.random() > 0.2 else None for v in unit1],
        "HospAdmTime": [round(float(v), 2) for v in -r.uniform(0.1, 200, n)],
        "ICULOS": iculos,
        "SepsisLabel": {
            "01": [int(v) for v in y],
            "scores": [round(float(v), 3) for v in prob],
        }[label],
        "PredictedProbability": {
            "prob": [round(float(v), 4) for v in prob],
            "01": [int(v >= 0.5) for v in prob],
        }[score],
        "PredictedLabel": [int(v >= 0.5) for v in prob],
        "hospital": [("A", "B")[v] for v in r.integers(0, 2, n)],
    }
    return cols


SEPSIS_EXPECTED = {
    "patient": ["case_id", "low"],
    "HR": IGN,
    "O2Sat": IGN,
    "Temp": IGN,
    "SBP": IGN,
    "MAP": IGN,
    "DBP": IGN,
    "Resp": IGN,
    "EtCO2": IGN,
    "Age": ["age", "high"],
    "Gender": ["sex", "medium"],
    "Unit1": IGN,
    "Unit2": IGN,
    "HospAdmTime": IGN,
    "ICULOS": IGN,
    "SepsisLabel": ["y_true", "high"],
    "PredictedProbability": ["score", "high"],
    "PredictedLabel": ["y_pred", "high"],
    "hospital": ["site", "high"],
}


def diabetes_columns(n: int = N, *, age: str = "bands", gender: str = "mf", label: str = "3"):
    r = rng()
    patient = [int(v) for v in r.integers(1000, 1030, n)]
    bands = ["[40-50)", "[50-60)", "[60-70)", "[70-80)", "[80-90)"]
    dash = ["40-49", "50-59", "60-69", "70-79", "80-89"]
    band_idx = r.integers(0, 5, n)
    races = ["Caucasian", "AfricanAmerican", "Hispanic", "Asian", "Other", "?"]
    cols = {
        "encounter_id": [int(v) for v in np.arange(500001, 500001 + n)],
        "patient_nbr": patient,
        "race": [races[v] for v in r.choice(6, n, p=[0.6, 0.2, 0.08, 0.04, 0.04, 0.04])],
        "gender": {
            "mf": [("Male", "Female")[v] for v in r.integers(0, 2, n)],
            "01": [int(v) for v in r.integers(0, 2, n)],
        }[gender],
        "age": {
            "bands": [bands[v] for v in band_idx],
            "dash": [dash[v] for v in band_idx],
            "numeric": [int(40 + 10 * v + r.integers(0, 10)) for v in band_idx],
        }[age],
        "weight": ["?"] * n,
        "admission_type_id": [int(v) for v in r.integers(1, 7, n)],
        "discharge_disposition_id": [int(v) for v in r.integers(1, 7, n)],
        "admission_source_id": [int(v) for v in r.integers(1, 8, n)],
        "time_in_hospital": [int(v) for v in r.integers(1, 15, n)],
        "payer_code": [("MC", "HM", "BC", "?")[v] for v in r.integers(0, 4, n)],
        "medical_specialty": [
            ("?", "InternalMedicine", "Cardiology", "Surgery-General")[v]
            for v in r.integers(0, 4, n)
        ],
        "num_lab_procedures": [int(v) for v in r.integers(30, 46, n)],
        "num_procedures": [int(v) for v in r.integers(0, 4, n)],
        "num_medications": [int(v) for v in r.integers(5, 20, n)],
        "number_outpatient": [int(v) for v in r.integers(0, 3, n)],
        "number_emergency": [int(v) for v in r.integers(0, 3, n)],
        "number_inpatient": [int(v) for v in r.integers(0, 3, n)],
        "diag_1": [
            ("250.83", "428", "V57", "414.01", "786", "401.9", "486", "V58")[v]
            for v in r.integers(0, 8, n)
        ],
        "number_diagnoses": [int(v) for v in r.integers(3, 10, n)],
        "max_glu_serum": [("None", ">200", ">300", "Norm")[v] for v in r.integers(0, 4, n)],
        "A1Cresult": [("None", ">7", ">8", "Norm")[v] for v in r.integers(0, 4, n)],
        "metformin": [("No", "Steady", "Up", "Down")[v] for v in r.integers(0, 4, n)],
        "insulin": [("No", "Steady", "Up", "Down")[v] for v in r.integers(0, 4, n)],
        "change": [("No", "Ch")[v] for v in r.integers(0, 2, n)],
        "diabetesMed": [("Yes", "No")[v] for v in r.integers(0, 2, n)],
        "readmitted": {
            "3": [("NO", "<30", ">30")[v] for v in r.choice(3, n, p=[0.55, 0.2, 0.25])],
            "01": [int(v) for v in r.integers(0, 2, n)],
        }[label],
        "pred_prob": [round(float(v), 4) for v in r.uniform(0.01, 0.99, n)],
        "hospital": [f"H{v:02d}" for v in r.integers(1, 6, n)],
    }
    return cols


DIABETES_EXPECTED = {
    "encounter_id": ["row_id", "medium"],
    "patient_nbr": ["case_id", "low"],
    "race": ["race", "high"],
    "gender": ["sex", "high"],
    "age": ["age_band", "high"],
    "weight": IGN,
    "admission_type_id": IGN,
    "discharge_disposition_id": IGN,
    "admission_source_id": IGN,
    "time_in_hospital": ["event_date", "low"],
    "payer_code": IGN,
    "medical_specialty": IGN,
    "num_lab_procedures": IGN,
    "num_procedures": IGN,
    "num_medications": IGN,
    "number_outpatient": IGN,
    "number_emergency": IGN,
    "number_inpatient": IGN,
    "diag_1": IGN,
    "number_diagnoses": IGN,
    "max_glu_serum": IGN,
    "A1Cresult": IGN,
    "metformin": IGN,
    "insulin": IGN,
    "change": IGN,
    "diabetesMed": IGN,
    "readmitted": ["y_true", "high"],
    "pred_prob": ["score", "high"],
    "hospital": ["site", "high"],
}


def mimic_columns(n: int = N):
    r = rng()
    subjects = [int(v) for v in r.integers(10000032, 10000060, n)]
    days = r.integers(0, 3000, n)
    races = ["WHITE", "BLACK/AFRICAN AMERICAN", "HISPANIC/LATINO", "ASIAN", "OTHER", "UNKNOWN"]
    admit = [
        f"{2150 + int(d) // 365:04d}-{1 + (int(d) // 30) % 12:02d}-{1 + int(d) % 28:02d} 10:15:00"
        for d in days
    ]
    disch = [
        f"{2150 + int(d) // 365:04d}-{1 + (int(d) // 30) % 12:02d}-{1 + int(d) % 28:02d} 17:40:00"
        for d in days
    ]
    y = [int(v) for v in r.integers(0, 2, n)]
    return {
        "subject_id": subjects,
        "hadm_id": [int(v) for v in np.arange(20000001, 20000001 + n)],
        "gender": [("M", "F")[v] for v in r.integers(0, 2, n)],
        "anchor_age": [int(v) for v in r.integers(18, 91, n)],
        "race": [races[v] for v in r.choice(6, n, p=[0.6, 0.15, 0.1, 0.05, 0.05, 0.05])],
        "admittime": admit,
        "dischtime": disch,
        "label": y,
        "probability": [round(float(v), 4) for v in r.uniform(0.01, 0.99, n)],
    }


MIMIC_EXPECTED = {
    "subject_id": ["case_id", "high"],
    "hadm_id": ["row_id", "medium"],
    "gender": ["sex", "high"],
    "anchor_age": ["age", "medium"],
    "race": ["race", "high"],
    "admittime": ["event_date", "low"],
    "dischtime": ["event_date", "low"],
    "label": ["y_true", "high"],
    "probability": ["score", "high"],
}


# --------------------------------------------------------------------------- helpers


def rename(cols: dict, mapping: dict[str, str]) -> dict:
    return {mapping.get(k, k): v for k, v in cols.items()}


def rename_expected(exp: dict, mapping: dict[str, str]) -> dict:
    return {mapping.get(k, k): v for k, v in exp.items()}


def with_(exp: dict, **changes) -> dict:
    out = dict(exp)
    out.update(changes)
    return out


def write_fixture(
    name: str,
    cols: dict,
    expected: dict | None,
    *,
    comment: str,
    halt: dict | None = None,
    notes: dict | None = None,
    encoding: str = "utf-8",
    criteria: dict | None = None,
    n_rows: int | None = None,
) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    headers = list(cols)
    n = len(cols[headers[0]]) if headers else 0
    if n_rows is not None:
        n = n_rows
    csv_path = OUT / f"{name}.csv"
    # keep the line ending the checkout already has (CRLF on Windows with autocrlf, LF on
    # a Linux checkout), so regenerating marks no fixture modified for endings alone
    # (repair 1, RG-NB-7: at 555a5e1 the generator wrote LF and git status listed all 35)
    eol = "\r\n" if csv_path.exists() and b"\r\n" in csv_path.read_bytes() else "\n"
    with csv_path.open("w", encoding=encoding, newline="") as fh:
        w = csv.writer(fh, lineterminator=eol)
        w.writerow(headers)
        for i in range(n):
            w.writerow([_fmt(cols[h][i]) for h in headers])
    spec = {
        "comment": comment,
        "n_rows": n,
        "halt": halt,
        "roles": expected,
        "notes": notes or {},
    }
    if criteria is not None:
        import yaml

        (OUT / f"{name}.criteria.yaml").write_text(
            yaml.safe_dump(criteria, sort_keys=False), encoding="utf-8"
        )
        spec["criteria"] = f"{name}.criteria.yaml"
    (OUT / f"{name}.expected.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def composite_criteria() -> dict:
    """A criteria.yaml whose clustering.unit names two columns (DEC-11)."""
    return {
        "schema_version": 1,
        "model": {"name": "fixture", "version": "1"},
        "task": "binary",
        "classes": {"positive": "1", "negative": "0"},
        "score": {"type": "probability", "orientation": "higher_is_positive"},
        "operating_points": [
            {"id": "op1", "threshold": 0.5, "rule": ">=", "provenance": "prespecified_sap"}
        ],
        "reference_standard": {"type": "reference_standard", "description": "fixture"},
        "indeterminates": {"policy": "none_present", "values": []},
        "clustering": {"unit": ["subject_id", "hadm_id"], "declared_by": "fixture"},
        "prevalence": [{"label": "fixture", "value": 0.3, "source": "fixture"}],
        "subgroups": [{"attribute": "sex", "prespecified": True, "reference_level": "M"}],
        "criteria": [],
    }


# --------------------------------------------------------------------------- the register


def main() -> None:
    # ---- Sepsis-2019 style
    write_fixture(
        "sepsis_2019",
        sepsis_columns(),
        SEPSIS_EXPECTED,
        comment="PhysioNet 2019 headers with the real Gender coding 0/1 -> sex is medium",
        notes={"Gender": NOTE_01, "Unit1": "claimed by name", "patient": "case identifier"},
    )
    write_fixture(
        "sepsis_2019_gender_mf",
        sepsis_columns(gender="mf"),
        with_(SEPSIS_EXPECTED, Gender=["sex", "high"]),
        comment="Same headers, Gender recoded M/F -> label/score/site/age/sex all high",
    )
    write_fixture(
        "sepsis_sex_12",
        sepsis_columns(gender="12"),
        SEPSIS_EXPECTED,
        comment="Gender coded 1/2 -> sex medium with the 1/2 note",
        notes={"Gender": NOTE_12},
    )
    lower = {h: h.lower() for h in SEPSIS_EXPECTED}
    write_fixture(
        "sepsis_lowercase",
        rename(sepsis_columns(gender="mf"), lower),
        rename_expected(with_(SEPSIS_EXPECTED, Gender=["sex", "high"]), lower),
        comment="every header lower-cased (sepsislabel, predictedprobability, ...)",
    )
    upper = {h: h.upper() for h in SEPSIS_EXPECTED}
    write_fixture(
        "sepsis_uppercase",
        rename(sepsis_columns(gender="mf"), upper),
        rename_expected(with_(SEPSIS_EXPECTED, Gender=["sex", "high"]), upper),
        comment="every header upper-cased",
    )
    spaces = {
        "SepsisLabel": "Sepsis Label",
        "PredictedProbability": "Predicted Probability",
        "PredictedLabel": "Predicted Label",
        "HospAdmTime": "Hosp Adm Time",
        "O2Sat": "O2 Sat",
    }
    write_fixture(
        "sepsis_spaces",
        rename(sepsis_columns(gender="mf"), spaces),
        rename_expected(with_(SEPSIS_EXPECTED, Gender=["sex", "high"]), spaces),
        comment="spaces inside headers",
    )
    pt = {"Age": "pt_Age", "Gender": "pt_Gender", "SepsisLabel": "pt_SepsisLabel"}
    write_fixture(
        "sepsis_pt_prefix",
        rename(sepsis_columns(gender="mf"), pt),
        rename_expected(with_(SEPSIS_EXPECTED, Gender=["sex", "high"]), pt),
        comment="pt_ prefix on three headers (affix rule)",
    )
    v2 = {"SepsisLabel": "SepsisLabel_v2", "PredictedProbability": "PredictedProbability_v2"}
    write_fixture(
        "sepsis_v2_suffix",
        rename(sepsis_columns(gender="mf"), v2),
        rename_expected(with_(SEPSIS_EXPECTED, Gender=["sex", "high"]), v2),
        comment="_v2 suffix on two headers (affix rule)",
    )
    british = {"hospital": "centre", "Gender": "Sex"}
    write_fixture(
        "sepsis_british",
        rename(sepsis_columns(gender="mf"), british),
        rename_expected(with_(SEPSIS_EXPECTED, Gender=["sex", "high"]), british),
        comment="British spelling: centre; Sex instead of Gender",
    )
    american = {"hospital": "center"}
    write_fixture(
        "sepsis_american",
        rename(sepsis_columns(gender="mf"), american),
        rename_expected(with_(SEPSIS_EXPECTED, Gender=["sex", "high"]), american),
        comment="American spelling: center",
    )
    uni = {"Temp": "Température", "Resp": "Atemfrequenz (Größe)"}
    write_fixture(
        "sepsis_unicode_headers",
        rename(sepsis_columns(gender="mf"), uni),
        rename_expected(with_(SEPSIS_EXPECTED, Gender=["sex", "high"]), uni),
        comment="non-ASCII headers map to ignore and print (PYTHONUTF8=1 on Windows)",
    )
    write_fixture(
        "sepsis_bom_first_header",
        sepsis_columns(gender="mf"),
        with_(SEPSIS_EXPECTED, Gender=["sex", "high"]),
        comment="file written with a UTF-8 BOM before the first header",
        encoding="utf-8-sig",
    )
    ws = {"SepsisLabel": "  SepsisLabel ", "Age": "Age  ", "patient": " patient"}
    write_fixture(
        "sepsis_whitespace_headers",
        rename(sepsis_columns(gender="mf"), ws),
        with_(SEPSIS_EXPECTED, Gender=["sex", "high"]),  # load_table strips the headers
        comment="leading/trailing whitespace in three headers (load_table strips them)",
    )
    two = sepsis_columns(gender="mf")
    two["outcome"] = list(two["SepsisLabel"])
    write_fixture(
        "sepsis_two_labels",
        two,
        with_(
            SEPSIS_EXPECTED,
            Gender=["sex", "high"],
            SepsisLabel=["y_true", "low"],
            outcome=["y_true", "low"],
        ),
        comment="SepsisLabel and outcome both name y_true -> both low, --yes refused",
        notes={"SepsisLabel": "2 headers claim y_true", "outcome": "2 headers claim y_true"},
    )
    write_fixture(
        "sepsis_label_holds_scores",
        sepsis_columns(gender="mf", label="scores"),
        with_(SEPSIS_EXPECTED, Gender=["sex", "high"], SepsisLabel=["y_true", "low"]),
        comment="SepsisLabel holds floats in (0,1): the header's role wins at low",
        notes={"SepsisLabel": "continuous"},
    )
    write_fixture(
        "sepsis_score_holds_01",
        sepsis_columns(gender="mf", score="01"),
        with_(SEPSIS_EXPECTED, Gender=["sex", "high"], PredictedProbability=["score", "low"]),
        comment="PredictedProbability holds only 0/1 -> score at low with a note",
        notes={"PredictedProbability": "only 0/1"},
    )
    visit = sepsis_columns(gender="mf")
    r = rng()
    visit["visit"] = [
        f"2025-{1 + int(v) % 12:02d}-{1 + int(v) % 28:02d}" for v in r.integers(0, 400, N)
    ]
    write_fixture(
        "sepsis_visit_dates",
        visit,
        with_(SEPSIS_EXPECTED, Gender=["sex", "high"], visit=["event_date", "medium"]),
        comment="a column named visit holding ISO dates -> event_date by values; H11 via the CLI",
        notes={"visit": "by values only"},
    )
    wide = sepsis_columns(gender="mf")
    r = rng()
    wide_expected = with_(SEPSIS_EXPECTED, Gender=["sex", "high"])
    for i in range(200 - len(wide)):
        wide[f"lab_{i + 1:03d}"] = [round(float(v), 2) for v in r.normal(10, 3, N)]
        wide_expected[f"lab_{i + 1:03d}"] = IGN
    write_fixture("sepsis_200_columns", wide, wide_expected, comment="200 columns")
    write_fixture(
        "sepsis_one_row",
        sepsis_columns(gender="mf"),
        with_(
            SEPSIS_EXPECTED,
            Gender=["sex", "high"],
            EtCO2=IGN,
        ),
        comment="a 1-row table: value heuristics need >= 2 non-missing rows; names still map",
        n_rows=1,
    )
    write_fixture(
        "sepsis_zero_rows",
        sepsis_columns(gender="mf"),
        {
            **{h: IGN for h in SEPSIS_EXPECTED},
            "patient": ["case_id", "low"],
            "Age": ["age", "high"],
            "Gender": ["sex", "medium"],
            "SepsisLabel": ["y_true", "medium"],
            "PredictedProbability": ["score", "medium"],
            "PredictedLabel": ["y_pred", "medium"],
            "hospital": ["site", "medium"],
        },
        comment="header-only file: canonical names high, synonyms medium, no values",
        n_rows=0,
    )
    empty = sepsis_columns(gender="mf")
    empty[""] = [int(v) for v in range(N)]
    write_fixture(
        "sepsis_empty_header",
        empty,
        with_(SEPSIS_EXPECTED, Gender=["sex", "high"], **{"": IGN}),
        comment="a header that is the empty string (pandas index export) -> ignore",
    )
    dup = sepsis_columns(gender="mf")
    dup["sepsislabel"] = list(dup["SepsisLabel"])
    write_fixture(
        "sepsis_dup_after_fold",
        dup,
        None,
        comment="SepsisLabel and sepsislabel: identical after case-folding -> HALT H07",
        halt={"code": "H07", "message_contains": "identical after case-folding"},
    )
    nfc = unicodedata.normalize("NFC", "Température")
    nfd = unicodedata.normalize("NFD", "Température")
    twins = rename(sepsis_columns(gender="mf"), {"Temp": nfc})
    twins[nfd] = list(twins[nfc])
    write_fixture(
        "sepsis_nfc_nfd_twins",
        twins,
        None,
        comment="the same header in NFC and NFD -> HALT H07",
        halt={"code": "H07", "message_contains": "unicode normalisation"},
    )
    two_ids = rename(sepsis_columns(gender="mf"), {"patient": "patient_id"})
    two_ids["subject_id"] = list(two_ids["patient_id"])
    write_fixture(
        "sepsis_two_case_ids",
        two_ids,
        None,
        comment="patient_id and subject_id both name case_id -> E01 (DEC-11)",
        halt={"code": "E01", "message_ends": "reduce your case key to one column"},
    )

    # ---- Diabetes-130 style
    write_fixture(
        "diabetes_130",
        diabetes_columns(),
        DIABETES_EXPECTED,
        comment="UCI Diabetes-130 headers (subset); time_in_hospital is date-like by header "
        "(H11 inspects it) but holds integers -> event_date at low with a conflict note",
        notes={
            "diabetesMed": "claimed by name",
            "time_in_hospital": "not dates",
            "patient_nbr": "case identifier",
        },
    )
    upper_d = {h: h.upper() for h in DIABETES_EXPECTED}
    write_fixture(
        "diabetes_uppercase",
        rename(diabetes_columns(), upper_d),
        rename_expected(DIABETES_EXPECTED, upper_d),
        comment="every header upper-cased",
    )
    write_fixture(
        "diabetes_age_numeric",
        diabetes_columns(age="numeric"),
        with_(DIABETES_EXPECTED, age=["age", "high"]),
        comment="age holds integers -> age",
    )
    write_fixture(
        "diabetes_age_dash_bands",
        diabetes_columns(age="dash"),
        DIABETES_EXPECTED,
        comment="age holds 70-79 style bands -> age_band",
    )
    write_fixture(
        "diabetes_sex_01",
        diabetes_columns(gender="01"),
        with_(DIABETES_EXPECTED, gender=["sex", "medium"]),
        comment="gender coded 0/1 -> sex medium with the 0/1 note",
        notes={"gender": NOTE_01},
    )
    write_fixture(
        "diabetes_readmitted_binary",
        diabetes_columns(label="01"),
        DIABETES_EXPECTED,
        comment="readmitted as 0/1",
    )
    camel = {
        "encounter_id": "EncounterId",
        "patient_nbr": "PatientNbr",
        "time_in_hospital": "TimeInHospital",
        "diabetesMed": "DiabetesMed",
        "readmitted": "Readmitted",
        "pred_prob": "PredProb",
    }
    write_fixture(
        "diabetes_camel_case",
        rename(diabetes_columns(), camel),
        with_(rename_expected(DIABETES_EXPECTED, camel), TimeInHospital=IGN),
        comment="camel-case headers split on the case change; TimeInHospital is not "
        "date-like to H11's header regex (no separator before Time), and its token "
        "'hospital' is out-ranked by the header that names site -> ignore",
    )

    # ---- MIMIC-IV demo style
    write_fixture(
        "mimic_iv_demo",
        mimic_columns(),
        MIMIC_EXPECTED,
        comment="MIMIC-IV demo patients+admissions headers; admittime/dischtime are datetimes "
        "-> two value-only event_date candidates at low",
        notes={"admittime": "2 columns look like event_date"},
    )
    m_visit = mimic_columns()
    m_visit["visit"] = m_visit.pop("admittime")
    m_visit.pop("dischtime")
    write_fixture(
        "mimic_visit_dates",
        m_visit,
        {
            **{k: v for k, v in MIMIC_EXPECTED.items() if k not in ("admittime", "dischtime")},
            "visit": ["event_date", "medium"],
        },
        comment="a single date-valued column named visit -> event_date medium",
    )
    write_fixture(
        "mimic_composite_key",
        mimic_columns(),
        None,
        comment="criteria.yaml declares clustering.unit as a two-column list -> E01 (DEC-11)",
        halt={"code": "E01", "message_ends": "reduce your case key to one column"},
        criteria=composite_criteria(),
    )
    hyphen = {"subject_id": "subject-id", "hadm_id": "hadm-id", "anchor_age": "anchor-age"}
    write_fixture(
        "mimic_hyphen_headers",
        rename(mimic_columns(), hyphen),
        rename_expected(MIMIC_EXPECTED, hyphen),
        comment="hyphens in headers normalise to underscores",
    )


if __name__ == "__main__":
    main()
    print(f"wrote {len(list(OUT.glob('*.csv')))} fixtures to {OUT}")
