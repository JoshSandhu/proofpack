"""F12 - every HALT code H01-H12 fires, exits 3 through the CLI, and writes no document.

Each scenario builds a cohort + declarations that trip exactly one gate, runs it
through the public API (expecting :class:`HaltError` with that code) and through
``proofpack.cli.main`` (expecting exit 3 and an empty/absent ``--out``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import make_cohort, make_criteria, write_csv, write_yaml
from proofpack.cli import main
from proofpack.errors import EXIT_HALT, EXIT_OK, EXIT_WARNINGS, HALT_CODES, HaltError
from proofpack.gates import check_paired, ingest
from proofpack.io import declare
from proofpack.io.mapping import map_headers
from proofpack.io.schema import load_table, table_from_columns

pytestmark = [pytest.mark.day1, pytest.mark.fixture]


# --------------------------------------------------------------------------- scenarios
# Each returns (cols, criteria_dict, cli_extra_args, setup(tmp_path) -> None)


def s_h01():
    cols = make_cohort()
    crit = make_criteria(score={"type": "probability", "orientation": "lower_is_positive"})
    return cols, crit, [], None


def s_h02():
    cols = make_cohort()
    cols["y_true"][5] = "2"
    return cols, make_criteria(), [], None


def s_h03():
    cols = make_cohort()
    cols["score"][7] = 1.5
    return cols, make_criteria(), [], None


def s_h04():
    cols = make_cohort(with_y_pred=True, threshold=0.5)
    cols["y_pred"][3] = "1" if cols["y_pred"][3] == "0" else "0"
    return cols, make_criteria(threshold=0.5), [], None


def s_h05():
    cols = make_cohort()
    cols["row_id"][1] = cols["row_id"][0]
    return cols, make_criteria(), [], None


def s_h06():
    cols = make_cohort()
    cols["y_true"] = ["0"] * len(cols["y_true"])
    return cols, make_criteria(), [], None


def s_h07():
    cols = make_cohort()
    return cols, make_criteria(), ["--yes"], None  # --yes with no prior mapping.json


def s_h08():
    cols = make_cohort()
    return cols, make_criteria(classes=None), [], None


def s_h09():
    cols = make_cohort()
    crit = make_criteria()
    crit["criteria"][0]["metric"] = "not_a_metric"
    return cols, crit, [], None


def s_h11():
    cols = make_cohort()
    cols["event_date"] = ["2026-01-15"] * len(cols["y_true"])
    return cols, make_criteria(), [], None


SCENARIOS = {
    "H01": s_h01,
    "H02": s_h02,
    "H03": s_h03,
    "H04": s_h04,
    "H05": s_h05,
    "H06": s_h06,
    "H07": s_h07,
    "H08": s_h08,
    "H09": s_h09,
    "H11": s_h11,
}


def _decl(crit):
    return declare.validate_dict(crit)


@pytest.mark.parametrize("code", sorted(SCENARIOS))
def test_gate_fires_via_api(code):
    cols, crit, extra, _ = SCENARIOS[code]()
    with pytest.raises(HaltError) as ei:
        decl = _decl(crit)
        ingest(table_from_columns(cols), decl, non_interactive="--yes" in extra)
    assert ei.value.code == code
    assert ei.value.exit_code == EXIT_HALT


@pytest.mark.parametrize("code", sorted(SCENARIOS))
def test_gate_exits_3_and_writes_nothing(code, tmp_path: Path):
    cols, crit, extra, _ = SCENARIOS[code]()
    csv_path = write_csv(tmp_path / "test.csv", cols)
    yml = write_yaml(tmp_path / "criteria.yaml", crit)
    out = tmp_path / "pack"
    rc = main(
        [
            "--quiet",
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--out",
            str(out),
            *extra,
        ]
    )
    assert rc == EXIT_HALT
    assert not out.exists() or not any(out.iterdir())


def test_h10_is_flag_only(tmp_path: Path):
    cols = make_cohort(prevalence=0.3)
    crit = make_criteria(prevalence=[{"label": "screening", "value": 0.02, "source": "t"}])
    res = ingest(table_from_columns(cols), _decl(crit))
    assert [w.code for w in res.warnings] == ["W10"]
    assert res.exit_code == EXIT_WARNINGS
    csv_path = write_csv(tmp_path / "test.csv", cols)
    yml = write_yaml(tmp_path / "criteria.yaml", crit)
    out = tmp_path / "pack"
    rc = main(
        ["--quiet", "run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out)]
    )
    assert rc == EXIT_WARNINGS
    report = json.loads((out / "ingest_report.json").read_text())
    assert report["warnings"][0]["code"] == "W10"
    assert report["halt_code"] is None


def test_h12_unmatched_row_ids(tmp_path: Path):
    new = make_cohort(seed=1)
    prior = make_cohort(seed=2)
    prior["row_id"][0] = "not-in-new"
    decl = _decl(make_criteria())
    tn = ingest(table_from_columns(new), decl).table
    tp = ingest(table_from_columns(prior), decl).table
    with pytest.raises(HaltError) as ei:
        check_paired(tn, tp)
    assert ei.value.code == "H12"
    assert ei.value.exit_code == EXIT_HALT
    w = check_paired(tn, tp, allow_unpaired=True)
    assert w is not None and w.code == "W12"
    # CLI: exit 3, nothing written
    a = write_csv(tmp_path / "new.csv", new)
    b = write_csv(tmp_path / "prior.csv", prior)
    yml = write_yaml(tmp_path / "criteria.yaml", make_criteria())
    out = tmp_path / "pack"
    rc = main(
        [
            "--quiet",
            "compare",
            "--input",
            str(a),
            "--prior",
            str(b),
            "--criteria",
            str(yml),
            "--out",
            str(out),
        ]
    )
    assert rc == EXIT_HALT
    assert not out.exists() or not any(out.iterdir())
    rc = main(
        [
            "--quiet",
            "compare",
            "--input",
            str(a),
            "--prior",
            str(b),
            "--criteria",
            str(yml),
            "--out",
            str(out),
            "--allow-unpaired",
        ]
    )
    assert rc == EXIT_WARNINGS
    assert (out / "compare_ingest_report.json").exists()


def test_every_halt_code_has_a_scenario():
    covered = set(SCENARIOS) | {"H10", "H12"}
    assert covered == set(HALT_CODES)


# --------------------------------------------------------------------------- gate details


def test_h05_case_id_conflict_only_when_unclustered():
    cols = make_cohort(with_case_id=True)
    cols["case_id"][1] = cols["case_id"][0]
    cols["y_true"][0], cols["y_true"][1] = "1", "0"
    with pytest.raises(HaltError) as ei:
        ingest(table_from_columns(cols), _decl(make_criteria()))
    assert ei.value.code == "H05"
    clustered = make_criteria(clustering={"unit": "case_id", "declared_by": "t"})
    ingest(table_from_columns(cols), _decl(clustered))  # no HALT


def test_h06_single_class_site_is_warning():
    cols = make_cohort(sites=2)
    cols["y_true"] = ["1" if s == "S1" else "0" for s in cols["site"]]
    res = ingest(
        table_from_columns(cols),
        _decl(make_criteria(score={"type": "probability", "orientation": "higher_is_positive"})),
    )
    assert "W06" in {w.code for w in res.warnings}


def test_h07_accepts_yes_with_matching_high_mapping(tmp_path: Path):
    cols = make_cohort()
    m = map_headers(list(cols))
    m.write(tmp_path / "mapping.json")
    res = ingest(
        table_from_columns(cols),
        _decl(make_criteria()),
        mapping_path=tmp_path / "mapping.json",
        non_interactive=True,
    )
    assert res.mapping.decided_by == "file"


def test_h07_rejects_yes_when_headers_change(tmp_path: Path):
    cols = make_cohort()
    map_headers(list(cols)).write(tmp_path / "mapping.json")
    cols["extra"] = [0] * len(cols["y_true"])
    with pytest.raises(HaltError) as ei:
        ingest(
            table_from_columns(cols),
            _decl(make_criteria()),
            mapping_path=tmp_path / "mapping.json",
            non_interactive=True,
        )
    assert ei.value.code == "H07"


def test_h07_rejects_yes_when_a_role_is_medium(tmp_path: Path):
    cols = make_cohort()
    cols["label"] = cols.pop("y_true")
    map_headers(list(cols)).write(tmp_path / "mapping.json")
    with pytest.raises(HaltError) as ei:
        ingest(
            table_from_columns(cols),
            _decl(make_criteria()),
            mapping_path=tmp_path / "mapping.json",
            non_interactive=True,
        )
    assert ei.value.code == "H07"


def test_synonym_mapping_interactive_path():
    cols = make_cohort()
    cols["label"] = cols.pop("y_true")
    cols["gender"] = cols.pop("sex")
    res = ingest(table_from_columns(cols), _decl(make_criteria()))
    assert "sex" in res.table.attributes
    assert res.mapping.role_of("label") == "y_true"


def test_h08_variants():
    for block in ("score", "operating_points", "prevalence", "subgroups"):
        with pytest.raises(HaltError) as ei:
            _decl(make_criteria(**{block: None}))
        assert ei.value.code == "H08", block
    crit = make_criteria()
    crit["criteria"][0]["justification"] = "  "
    with pytest.raises(HaltError) as ei:
        _decl(crit)
    assert ei.value.code == "H08"
    crit = make_criteria(fairness={"criterion_of_interest": "tpr_gap", "attribute": "sex"})
    with pytest.raises(HaltError) as ei:
        _decl(crit)
    assert ei.value.code == "H08"


def test_h08_age_without_bands():
    crit = make_criteria()
    crit["subgroups"][1] = {"attribute": "age", "prespecified": True}
    with pytest.raises(HaltError) as ei:
        ingest(table_from_columns(make_cohort()), _decl(crit))
    assert ei.value.code == "H08"


def test_h09_variants():
    crit = make_criteria()
    crit["criteria"][0]["operating_point"] = "op9"
    with pytest.raises(HaltError) as ei:
        _decl(crit)
    assert ei.value.code == "H09"
    crit = make_criteria()
    crit["criteria"][0]["scope"] = {"attribute": "race", "level": "*"}
    with pytest.raises(HaltError) as ei:
        ingest(table_from_columns(make_cohort()), _decl(crit))
    assert ei.value.code == "H09"
    crit = make_criteria()
    crit["criteria"][0]["scope"] = {"attribute": "sex", "level": "X"}
    with pytest.raises(HaltError) as ei:
        ingest(table_from_columns(make_cohort()), _decl(crit))
    assert ei.value.code == "H09"
    crit = make_criteria(
        fairness={
            "criterion_of_interest": "tpr_gap",
            "attribute": "race",
            "author": "a",
            "date": "2026-01-01",
            "justification": "j",
        }
    )
    with pytest.raises(HaltError) as ei:
        ingest(table_from_columns(make_cohort()), _decl(crit))
    assert ei.value.code == "H09"


def test_h11_covered_by_period_declaration_and_dates_coarsened():
    cols = make_cohort()
    cols["event_date"] = ["2026-02-15", "2026-05-01"] * (len(cols["y_true"]) // 2)
    crit = make_criteria(period={"column": "event_date", "granularity": "quarter"})
    res = ingest(table_from_columns(cols), _decl(crit))
    assert set(res.table.period.tolist()) == {"2026-Q1", "2026-Q2"}
    assert "event_date" not in res.table.attributes


def test_h11_second_date_column_still_halts():
    cols = make_cohort()
    cols["event_date"] = ["2026-02-15"] * len(cols["y_true"])
    cols["scan_date"] = ["2026-02-15"] * len(cols["y_true"])
    crit = make_criteria(period={"column": "event_date", "granularity": "quarter"})
    with pytest.raises(HaltError) as ei:
        ingest(table_from_columns(cols), _decl(crit))
    assert ei.value.code == "H11"


def test_halt_detail_never_carries_headers_or_values():
    """Aggregates-only egress: HALT detail must not echo cell values or original headers."""
    cols = make_cohort()
    cols["y_true"][5] = "SECRET_LABEL"
    cols["patient_name_col"] = ["x"] * len(cols["y_true"])
    with pytest.raises(HaltError) as ei:
        ingest(table_from_columns(cols), _decl(make_criteria()))
    blob = json.dumps(ei.value.detail) + ei.value.message
    assert "SECRET_LABEL" not in blob
    assert "patient_name_col" not in blob


def test_clean_run_exit_0_and_report(tmp_path: Path, cohort_csv, criteria_yaml, out_dir):
    rc = main(
        [
            "--quiet",
            "run",
            "--input",
            str(cohort_csv),
            "--criteria",
            str(criteria_yaml),
            "--out",
            str(out_dir),
        ]
    )
    assert rc == EXIT_OK
    report = json.loads((out_dir / "ingest_report.json").read_text())
    assert report["flow"]["included"] == 400
    assert report["declared"]["positive"] == "1"
    assert (out_dir / "mapping.json").exists()
    raw = load_table(cohort_csv)
    assert raw.header_set_sha256 == report["header_set_sha256"]
