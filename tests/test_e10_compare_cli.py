"""Build day 10 (E10 item 3): ``proofpack compare`` end to end.

* on the F5 fixture pair the command writes ``run.json`` valid against
  ``schema/output_schema_v1.json`` with D1 section 4.2's ``comparison`` block, the
  ``criteria_results`` of the paired criterion, ``compare_ingest_report.json`` beside
  it, and ``T2.html`` (the default template) under a usable licence;
* H12 halts (exit 3, nothing written) on an unmatched ``row_id`` set, and on a pair whose
  ``y_true`` differs; ``--allow-unpaired`` takes the unpaired path with the label in
  ``run.json`` and every difference Number labelled;
* a compare with no ``paired_difference_vs_prior`` criterion writes no margin and no
  status column on T2-3 (D4 section 5.7);
* ``--templates`` accepts T2, T7 and T8 and refuses T1; ``run --templates T2`` prints the
  typed line; a licence without the ``compare`` feature writes ``run.json`` and no
  document (exit 4); the printed ``Next step`` lines have ``run``'s shape;
* two compare runs are byte-identical after ``scripts/f17_determinism.py``'s masking
  (its ``--compare`` mode), and the command opens no socket (``tests/test_offline.py``).
"""

from __future__ import annotations

import copy
import hashlib
import html
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import yaml

from conftest import confirmed_mapping, ephemeral_registry, write_licence
from proofpack.cli import main
from proofpack.errors import EXIT_HALT, EXIT_INTERNAL, EXIT_LICENCE, EXIT_OK, EXIT_WARNINGS
from proofpack.resources import load_json_schema

pytestmark = pytest.mark.day10

REPO = Path(__file__).resolve().parent.parent
F5 = REPO / "tests" / "fixtures" / "f5"


def _home(tmp_path: Path, monkeypatch, **licence: Any) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("PROOFPACK_HOME", str(home))
    write_licence(home / "proofpack.lic", **licence)
    return home


def _inputs(tmp_path: Path, crit: dict[str, Any] | None = None) -> tuple[Path, Path, Path]:
    work = tmp_path / "in"
    work.mkdir(exist_ok=True)
    for name in ("f5_new.csv", "f5_prior.csv", "criteria.yaml"):
        shutil.copy(F5 / name, work / name)
    if crit is not None:
        (work / "criteria.yaml").write_text(yaml.safe_dump(crit, sort_keys=False), "utf-8")
    confirmed_mapping(work / "f5_new.csv")
    return work / "f5_new.csv", work / "f5_prior.csv", work / "criteria.yaml"


def _compare(new: Path, prior: Path, crit: Path, out: Path, *flags: str, registry="ephemeral"):
    reg = ephemeral_registry() if registry == "ephemeral" else registry
    argv = ["compare", "--input", str(new), "--prior", str(prior), "--criteria", str(crit)]
    return main([*argv, "--out", str(out), "--offline", *flags], registry=reg)


def f5_criteria() -> dict[str, Any]:
    return yaml.safe_load((F5 / "criteria.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def f5_run(tmp_path: Path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    out = tmp_path / "pack"
    rc = _compare(new, prior, crit, out)
    printed = capsys.readouterr().out
    assert rc == EXIT_OK, printed
    return json.loads((out / "run.json").read_text(encoding="utf-8")), printed, out


# ------------------------------------------------------------------ the block


def test_compare_on_f5_writes_a_valid_document_with_the_comparison_block(f5_run):
    doc, printed, out = f5_run
    jsonschema.Draft202012Validator(load_json_schema("output_schema_v1.json")).validate(doc)
    c = doc["comparison"]
    assert c["paired"] is True and c["n_pairs"] == 100 and c["prior_version"] == "1.2"
    assert c["mcnemar"]["op1"]["b"] == 10 and c["mcnemar"]["op1"]["c"] == 2
    assert c["mcnemar"]["op1"]["method"] == "exact_mcnemar"
    assert round(c["mcnemar"]["op1"]["p"], 4) == 0.0386
    assert set(c["differences"]) == {"op1", "auroc", "brier", "slope"}
    assert set(c["differences"]["op1"]) == {"sensitivity", "specificity", "accuracy"}
    assert len(c["subgroups"]) == len(doc["subgroups"])
    assert c["ledger"]["prior_acceptance_runs"] == 0 and c["ledger"]["warn_limit"] == 3
    assert c["ledger"]["limit_reached"] is False
    assert re.fullmatch(r"[0-9a-f]{64}", doc["manifest"]["prior_input_sha256"])
    assert (
        doc["manifest"]["prior_input_sha256"]
        == hashlib.sha256((F5 / "f5_prior.csv").read_bytes()).hexdigest()
    )
    assert c["prior"]["overall"]["op1"]["accuracy"]["k"] == 90
    assert doc["overall"]["op1"]["accuracy"]["k"] == 82
    rows = {r["criterion_id"]: r for r in doc["criteria_results"]}
    assert rows["C2"]["status"] == "not_met"
    assert doc["claim_rejections"] == [] and len(doc["claims"]) == 39
    assert sorted(p.name for p in out.iterdir()) == [
        "T2.html",
        "compare_ingest_report.json",
        "ingest_report.json",
        "pseudonyms.json",
        "run.json",
    ]
    report = json.loads((out / "compare_ingest_report.json").read_text(encoding="utf-8"))
    assert report["paired"] is True and set(report) == {"new", "prior", "paired", "warnings"}
    assert "compare written:" in printed and "paired on row_id: 100 pairs" in printed
    assert "criteria rows: 0 met, 2 not met, 0 not assessable" in printed
    assert printed.rstrip().endswith(
        "Next step: open the documents beside run.json; --templates T2,T7,T8 writes all "
        "three (docs: /docs/compare)"
    )
    assert "telemetry skipped (--offline)" in printed


def test_a_compare_document_carries_the_t2_claims_and_the_record_sentence(f5_run):
    doc, _, _ = f5_run
    ids = [c["template_id"] for c in doc["claims"]]
    for tid in (
        "PAIRED_DIFF",
        "MCNEMAR_RESULT",
        "LEDGER_STATEMENT",
        "IMPACT_INPUTS_NOTE",
        "MONITORING_POINTER",
        "CRITERION_STATUS",
        "CRITERION_NOT_MET_RECORD",
    ):
        assert tid in ids, tid
    assert ids.count("PAIRED_DIFF") == 6 and ids.count("CRITERION_NOT_MET_RECORD") == 2
    assert "UNPAIRED_LABEL" not in ids and "LEDGER_WARNING" not in ids
    paired = [c for c in doc["claims"] if c["template_id"] == "PAIRED_DIFF"]
    assert all(c["comparator_id"] == "diff_vs_prior" for c in paired)
    assert paired[0]["value_refs"] == [
        "/comparison/differences/op1/sensitivity/number",
        "/comparison/n_pairs",
    ]


# ------------------------------------------------------------------ H12


def test_h12_halts_on_an_unmatched_row_id_set_and_allow_unpaired_takes_the_labelled_path(
    tmp_path, monkeypatch, capsys
):
    _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    lines = prior.read_text(encoding="utf-8").splitlines()
    lines[1] = lines[1].replace("f5-000", "f5-999")
    prior.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = tmp_path / "pack"
    rc = _compare(new, prior, crit, out)
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and "HALT H12" in err and "No document was written" in err
    assert not out.exists() or not any(out.iterdir())
    rc = _compare(new, prior, crit, out, "--allow-unpaired")
    printed = capsys.readouterr().out
    assert rc == EXIT_WARNINGS, printed
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(load_json_schema("output_schema_v1.json")).validate(doc)
    c = doc["comparison"]
    assert c["paired"] is False and c["label"] == "not like-for-like"
    assert c["unpaired_rows"] == {
        "n_pairs": 99,
        "new_only": 1,
        "prior_only": 1,
        "label_mismatch": 0,
    }
    assert c["mcnemar"] is None and c["subgroups"] == []
    for key, cell in c["differences"].items():
        cells = cell.values() if key == "op1" else [cell]
        for one in cells:
            assert "not_like_for_like" in one["number"]["flags"]
            if one["number"]["ci_lo"] is not None:
                assert one["number"]["method"].endswith("_not_like_for_like")
    assert [w["code"] for w in doc["warnings"]] == ["W12"]
    assert "UNPAIRED - not like-for-like" in printed
    assert "[W12]" in printed
    c2 = next(r for r in doc["criteria_results"] if r["criterion_id"] == "C2")
    assert (c2["status"], c2["reason_code"]) == ("not_assessable", "not_like_for_like")
    page = (out / "T2.html").read_text(encoding="utf-8")
    assert "UNPAIRED - not like-for-like; Newcombe 10 / unpaired DeLong" in page
    assert "Versions were evaluated on different cases" in page


def test_h12_halts_when_a_paired_row_carries_a_different_label(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    lines = prior.read_text(encoding="utf-8").splitlines()
    assert lines[1].startswith("f5-000,1,")
    lines[1] = lines[1].replace("f5-000,1,", "f5-000,0,")
    prior.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = tmp_path / "pack"
    rc = _compare(new, prior, crit, out)
    err = capsys.readouterr().err
    assert rc == EXIT_HALT and "HALT H12" in err and '"label_mismatch": 1' in err
    assert not out.exists()


# ------------------------------------------------------------------ no paired criterion


def test_a_compare_with_no_paired_criterion_prints_no_margin_and_no_status_column(
    tmp_path, monkeypatch, capsys
):
    _home(tmp_path, monkeypatch)
    crit = f5_criteria()
    crit["criteria"] = [crit["criteria"][0]]  # the point criterion only
    new, prior, yml = _inputs(tmp_path, crit)
    out = tmp_path / "pack"
    assert _compare(new, prior, yml, out) == EXIT_OK, capsys.readouterr().out
    page = (out / "T2.html").read_text(encoding="utf-8")
    table = re.search(r'<table class="comparison">.*?</table>', page, re.S).group(0)
    assert "Margin" not in table and "Status" not in table
    assert 'class="status"' not in table and "record of criterion not met" not in table
    assert "no paired_difference_vs_prior criterion is declared" in table
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert all("value" not in c or c["value"] == 0.7 for c in doc["declarations"]["criteria"])
    # and with none at all: the criteria table is absent, the traceability table says so
    crit["criteria"] = []
    new, prior, yml = _inputs(tmp_path, crit)
    assert _compare(new, prior, yml, out) == EXIT_OK, capsys.readouterr().out
    page = (out / "T2.html").read_text(encoding="utf-8")
    assert "No acceptance criteria were declared; estimates and intervals only." in page
    assert "No criterion was declared; no traceability row exists." in page


# ------------------------------------------------------------------ templates, licence


def test_templates_t2_t7_t8_are_accepted_and_t1_is_refused(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    out = tmp_path / "pack"
    assert _compare(new, prior, crit, out, "--templates", "T2,T7,T8") == EXIT_OK
    printed = capsys.readouterr().out
    for name in ("T2.html", "T7.html", "T8.html"):
        assert (out / name).exists(), name
        assert f"document written: {out / name}" in printed
    assert _compare(new, prior, crit, tmp_path / "x", "--templates", "T1") == EXIT_INTERNAL
    assert "unknown --templates id 'T1'; choose from T2, T7, T8" in capsys.readouterr().err
    # run --templates T2 prints the typed line and writes no T2
    rc = main(
        [
            "run",
            "--input",
            str(new),
            "--criteria",
            str(crit),
            "--out",
            str(tmp_path / "run"),
            "--offline",
            "--templates",
            "T2",
        ],
        registry=ephemeral_registry(),
    )
    printed = capsys.readouterr().out
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    assert (
        "T2 not written: T2 is the version comparison report, written by proofpack compare"
        in printed
    )
    assert not (tmp_path / "run" / "T2.html").exists()


def test_a_licence_without_the_compare_feature_writes_json_only_and_exits_4(
    tmp_path, monkeypatch, capsys
):
    _home(tmp_path, monkeypatch, features=["T1", "T7", "T8"])
    new, prior, crit = _inputs(tmp_path)
    out = tmp_path / "pack"
    rc = _compare(new, prior, crit, out)
    printed = capsys.readouterr().out
    assert rc == EXIT_LICENCE, printed
    assert (out / "run.json").exists() and not (out / "T2.html").exists()
    assert "does not carry the 'compare' feature; run.json only" in printed
    assert "Next step: proofpack licence install FILE, then compare again for T2.html" in printed
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["manifest"]["watermark"] is None  # a valid licence: no false expiry mark


def test_no_licence_writes_json_with_the_no_licence_mark_and_exits_4(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("PROOFPACK_HOME", str(home))
    new, prior, crit = _inputs(tmp_path)
    out = tmp_path / "pack"
    rc = _compare(new, prior, crit, out)
    printed = capsys.readouterr().out
    assert rc == EXIT_LICENCE
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["manifest"]["watermark"] == "NO LICENCE - not for submission"
    assert not (out / "T2.html").exists()
    assert "run.json was written with the watermark 'NO LICENCE - not for submission'" in printed


def test_json_log_reports_the_compare(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    out = tmp_path / "pack"
    assert _compare(new, prior, crit, out, "--json-log") == EXIT_OK
    log = json.loads(capsys.readouterr().out.strip().splitlines()[-1])["compare"]
    assert log["paired"] is True and log["n_pairs"] == 100 and log["templates"] == ["T2"]
    assert log["documents"] == [str(out / "T2.html")] and log["claim_rejections"] == 0


# ------------------------------------------------------------------ the ledger


def test_the_compare_ledger_counts_prior_comparisons_and_reaches_the_declared_limit(
    tmp_path, monkeypatch, capsys
):
    _home(tmp_path, monkeypatch)
    new, prior, crit = _inputs(tmp_path)
    seen = []
    for i in range(4):
        out = tmp_path / f"pack{i}"
        assert _compare(new, prior, crit, out) in (EXIT_OK, EXIT_WARNINGS), capsys.readouterr().out
        doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
        seen.append(
            (
                doc["comparison"]["ledger"]["prior_acceptance_runs"],
                doc["comparison"]["ledger"]["limit_reached"],
            )
        )
    assert seen == [(0, False), (1, False), (2, False), (3, True)]
    page = (tmp_path / "pack3" / "T2.html").read_text(encoding="utf-8")
    # E10 repair 1 (lens 1 FA-N3): the banner names the declaration the limit came from
    assert (
        "has reached or exceeded the manufacturer's declared ledger limit "
        "(ledger.warn_after_acceptance_runs)"
    ) in html.unescape(page)
    assert 'data-slot="ledger-warning"' in page
    assert "LEDGER_WARNING" in [c["template_id"] for c in doc["claims"]]
    # a compare is counted under its own key (compare:<sha256>), apart from run's
    ledger = json.loads((tmp_path / "home" / "ledger.json").read_text(encoding="utf-8"))
    keys = list(ledger["counts"])
    assert len(keys) == 1 and keys[0].startswith("compare:") and ledger["counts"][keys[0]] == 4


# ------------------------------------------------------------------ determinism


def _f17():
    spec = importlib.util.spec_from_file_location(
        "f17_determinism", REPO / "scripts" / "f17_determinism.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["f17_determinism"] = module
    spec.loader.exec_module(module)
    return module


def test_two_compare_runs_are_byte_identical_after_the_f17_masking(tmp_path: Path):
    f17 = _f17()
    result = f17.run_f17(tmp_path / "f17", n=400, compare_mode=True)
    assert result["command"] == "compare" and result["identical"] is True, result["checks"]
    assert result["exit_codes"] == [4, 4]  # no licence in the F17 homes: JSON only
    assert all(c["equal"] for c in result["checks"].values())
    doc = json.loads((tmp_path / "f17" / "run1" / "run.json").read_text(encoding="utf-8"))
    assert doc["comparison"]["paired"] is True and doc["comparison"]["n_pairs"] == 400
    assert "compare_ingest_report.json" in result["file_names"][0]


def test_the_f17_script_compare_flag_runs_from_the_command_line(tmp_path: Path):
    f17 = _f17()
    assert f17.main(["--out", str(tmp_path / "cli"), "--n", "120", "--compare"]) == 0
    result = json.loads((tmp_path / "cli" / "f17_result.json").read_text(encoding="utf-8"))
    assert result["command"] == "compare" and result["identical"] is True


def test_the_prior_version_recipe_is_the_synthetic_modules_and_seeded(tmp_path: Path):
    from proofpack.synthetic import PRIOR_NOISE_SD, PRIOR_SHRINK, make_cohort, perturb_scores

    cols = make_cohort(seed=20240101, n=50)
    a = perturb_scores(cols["score"], 20240101)
    b = perturb_scores(cols["score"], 20240101)
    assert a == b and a != cols["score"] and all(0 < p < 1 for p in a)
    assert perturb_scores(cols["score"], 1) != a
    assert (PRIOR_SHRINK, PRIOR_NOISE_SD) == (0.85, 0.5)
    f17 = _f17()
    table, _, _ = f17.write_inputs(tmp_path / "in", 50)
    prior = f17.write_prior(table)
    rows = prior.read_text(encoding="utf-8").splitlines()
    assert rows[0] == table.read_text(encoding="utf-8").splitlines()[0]
    assert copy.deepcopy(a)[0] == float(rows[1].split(",")[2])
