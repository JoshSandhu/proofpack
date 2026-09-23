"""Repair 4 of build day 8 (23 September 2026): regression tests for the lens-4 findings
at ``23f3d9f`` - FA-B1 (the criteria row's Number read by splitting a dotted path), FA-B2
(a ``y_pred``-only table with two operating points; DEC-61), FA-B3 (``CALIB_NA`` on a
reason its sentence does not state), FA-B4 (``free_text`` spellings; DEC-60, the vendored
TR39 subset), FA-N1 (manufacturer words outside ``.customer-text``; DEC-62) and the
sentence findings RG-N1, FA-N2 and FA-N3. Each test names the literal inputs it feeds and
the figures it asserts; the repair-4 note quotes, per test, the first E line in a
worktree at ``23f3d9f`` with PYTHONPATH forced.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import ephemeral_registry, make_cohort, make_criteria
from proofpack.cli import main
from proofpack.errors import EXIT_HALT, EXIT_OK, EXIT_WARNINGS, HaltError
from proofpack.narrate import checker
from proofpack.narrate import claims as claims_mod
from proofpack.render import format as fmt
from proofpack.render import html as render_html
from test_render_t8 import _status_and_forbidden_hits
from test_run_cli import _own_home, _prepare

pytestmark = pytest.mark.day8

ROOT = Path(__file__).resolve().parents[1]


def _criterion(cid: str, op: str) -> dict[str, Any]:
    return {
        "id": cid,
        "metric": "sensitivity",
        "operating_point": op,
        "scope": "overall",
        "statistic": "point_estimate",
        "comparator": ">=",
        "value": 0.5,
        "author": "A",
        "date": "2026-01-01",
        "justification": "j",
    }


def _op(op_id: str, threshold: float) -> dict[str, Any]:
    return {
        "id": op_id,
        "threshold": threshold,
        "rule": ">=",
        "provenance": "prespecified_sap",
        "source": "s",
    }


def _cli(tmp_path: Path, monkeypatch, cols, crit, *flags: str) -> tuple[int, Path]:
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path, cols=cols, crit=crit)
    out = tmp_path / "pack"
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), *flags],
        registry=ephemeral_registry(),
    )
    return rc, out


# ---------------------------------------------- FA-B1: the criteria row's Number, looked up


def test_an_operating_point_id_holding_a_dot_or_brackets_prints_its_own_number():
    """Lens-4 FA-B1: operating points ``0`` (threshold 0.2), ``[0]`` (0.8) and ``t0.5``
    (0.5) on ``make_cohort(n=300)``, one ``sensitivity point_estimate >= 0.5`` criterion
    on each. At ``23f3d9f`` row ``C_br`` printed ``99/101 (98.0%) [93.1, 99.5]`` (op
    ``0``'s) beside ``criterion not met``, and ``C_dot`` printed a dash."""
    crit = make_criteria(
        criteria=[
            _criterion("C_zero", "0"),
            _criterion("C_br", "[0]"),
            _criterion("C_dot", "t0.5"),
        ],
        fairness=None,
    )
    crit["operating_points"] = [_op("0", 0.2), _op("[0]", 0.8), _op("t0.5", 0.5)]
    doc = assemble(make_cohort(n=300), crit)
    rows = render_html.criteria_rows(doc)
    assert [(r["criterion_id"], r["observed"], r["status_word"]) for r in rows] == [
        ("C_zero", "99/101 (98.0%) [93.1, 99.5]", "criterion met"),
        ("C_br", "29/101 (28.7%) [20.8, 38.2]", "criterion not met"),
        ("C_dot", "85/101 (84.2%) [75.8, 90.0]", "criterion met"),
    ]
    for row, op in zip(rows, ("0", "[0]", "t0.5"), strict=True):
        number = doc["overall"][op]["sensitivity"]
        assert row["observed"] == fmt.number(number, fmt.kind_for("sensitivity"))
    crit_claims = [c for c in doc["claims"] if c["template_id"] == "CRITERION_STATUS"]
    assert [c["value_refs"] for c in crit_claims] == [
        ["/overall/0/sensitivity"],
        ["/overall/[0]/sensitivity"],
        ["/overall/t0.5/sensitivity"],
    ]
    assert doc["claim_rejections"] == []


def test_an_operating_point_id_with_an_unclosed_bracket_runs_and_prints_its_number(
    tmp_path, monkeypatch
):
    """Lens-4 FA-B1: operating point ``a[0`` exited 5 (``internal error: ValueError``,
    from the dotted-path split inside ``build_claims``) at ``23f3d9f``. Fed through the
    CLI with a licence, beside ``0`` (0.2) and ``[0]`` (0.8), on ``make_cohort(n=300)``."""
    crit = make_criteria(
        criteria=[_criterion("C_zero", "0"), _criterion("C_br", "[0]"), _criterion("C_a", "a[0")],
        fairness=None,
    )
    crit["operating_points"] = [_op("0", 0.2), _op("[0]", 0.8), _op("a[0", 0.5)]
    rc, out = _cli(tmp_path, monkeypatch, make_cohort(n=300), crit, "--offline")
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    page = (out / "T8.html").read_text(encoding="utf-8")
    cells = re.findall(r'<td class="num observed">([^<]*)</td>', page)
    assert cells == [
        "99/101 (98.0%) [93.1, 99.5]",
        "29/101 (28.7%) [20.8, 38.2]",
        "85/101 (84.2%) [75.8, 90.0]",
    ]


# ---------------------------------------------- FA-B2 / DEC-61: one y_pred, one threshold


def _y_pred_only(n: int) -> dict[str, list[Any]]:
    cols = make_cohort(n=n, with_y_pred=True)
    del cols["score"]
    return cols


def test_a_y_pred_only_table_with_two_operating_points_halts_h08(tmp_path, monkeypatch):
    """Lens-4 FA-B2, DEC-61: 300 rows without a score column, operating points ``op_lo``
    (0.1) and ``op_hi`` (0.9). At ``23f3d9f`` both blocks were ``{tp 85, fn 16, fp 39, tn
    160}`` with ``warnings []`` and exit 0."""
    crit = make_criteria(criteria=[], fairness=None)
    crit["operating_points"] = [_op("op_lo", 0.1), _op("op_hi", 0.9)]
    with pytest.raises(HaltError) as ei:
        assemble(_y_pred_only(300), crit)
    assert ei.value.code == "H08"
    assert ei.value.detail == {
        "field": "operating_points",
        "reason": "no_score_column",
        "operating_points": ["op_lo", "op_hi"],
    }
    assert "op_lo, op_hi" in str(ei.value)
    rc, out = _cli(tmp_path, monkeypatch, _y_pred_only(300), crit, "--offline")
    assert rc == EXIT_HALT and not out.exists()


def test_the_tables_dec61_leaves_running_still_run():
    """Guards (they pass at ``23f3d9f``): a ``y_pred``-only table with one operating point,
    and a table with a score column and two operating points (0.1 and 0.9), whose
    sensitivities differ: 101/101 and 12/101 on ``make_cohort(n=300)``."""
    one = assemble(_y_pred_only(300), make_criteria(criteria=[], fairness=None))
    assert one["overall"]["op1"]["two_by_two"] == {"tp": 85, "fn": 16, "fp": 39, "tn": 160}
    crit = make_criteria(criteria=[], fairness=None)
    crit["operating_points"] = [_op("op_lo", 0.1), _op("op_hi", 0.9)]
    two = assemble(make_cohort(n=300), crit)
    assert two["overall"]["op_lo"]["two_by_two"]["tp"] == 101
    assert two["overall"]["op_hi"]["two_by_two"]["tp"] == 12


# ---------------------------------------------- FA-B3: CALIB_NA states one reason


def _calib_na() -> dict[str, Any]:
    return {
        "claim_id": "CL-9001",
        "template_id": "CALIB_NA",
        "metric_id": None,
        "operating_point": None,
        "subgroup": None,
        "reference": None,
        "comparator_id": None,
        "criterion_index": None,
        "criterion_id": None,
        "status": None,
        "relation": "not_assessable",
        "value_refs": [],
        "guidance_ref": "FDA_AIDSF_CALIBRATION",
        "free_text": None,
    }


@pytest.mark.parametrize(
    ("score", "reason", "claimed"),
    [
        (None, "no_score_column", False),
        (
            {"type": "probability", "orientation": "lower_is_positive"},
            "score_not_positive_class_probability",
            False,
        ),
        ({"type": "logit", "orientation": "higher_is_positive"}, "score_not_probability", True),
    ],
)
def test_calib_na_is_claimed_and_accepted_only_on_score_not_probability(score, reason, claimed):
    """Lens-4 FA-B3: at ``23f3d9f`` a ``y_pred``-only document (200 rows) carried
    ``CALIB_NA`` - "the score was declared as probability, not a probability" - and the
    checker accepted it."""
    crit = make_criteria(criteria=[], fairness=None)
    if score is None:
        cols = _y_pred_only(200)
    else:
        cols = make_cohort(n=200)
        crit["score"] = score
    doc = assemble(cols, crit)
    assert doc["calibration"] is None
    assert doc["calibration_suppressed_reason"]["reason"] == reason
    templates = [c["template_id"] for c in claims_mod.build_claims(doc)]
    assert ("CALIB_NA" in templates) is claimed
    verdict = checker.check([_calib_na()], doc).verdicts[0]
    assert verdict.accepted is claimed
    if not claimed:
        assert verdict.reason_code == "template_mismatch"


# ---------------------------------------------- FA-B4 / DEC-60: free_text spellings

#: Lens-4 FA-B4's 35 look-alike literals (33, then its two capital-I analogues).
LENS4_LOOKALIKES = (
    "fai|",
    "fai∣",
    "faił",
    "faiɫ",
    "faiƖ",
    "faiߊ",
    "faiⵏ",
    "faiꓲ",
    "fai׀",
    "faiΙ",
    "faiІ",
    "faɩl",
    "ⲣass",
    "⍴ass",
    "ꓑass",
    "p⍺ss",
    "paꓢs",
    "paꮪs",
    "gⲟⲟd",
    "gဝဝd",
    "gഠഠd",
    "ⲟk",
    "ցood",
    "m℮℮ts",
    "mҽҽts",
    "սnbiased",
    "ⲥonsistent",
    "veгdict",
    "ѵerdict",
    "saꞙe",
    "unbi⍺sed",
    "ᏚAFE",
    "ꓳꓗ",
    "faiＩ",
    "fai𝐈",
)


def test_the_lens4_lookalike_literals_are_rejected():
    """Lens-4 FA-B4: each of these 35 was accepted at ``23f3d9f``, bare and inside "The
    model was {} here."."""
    assert len(LENS4_LOOKALIKES) == 35
    for text in LENS4_LOOKALIKES:
        for fed in (text, f"The model was {text} here."):
            assert checker.free_text_reason(fed) == "free_text_verdict_word", repr(fed)


def test_well_calibrated_with_a_separator_and_letters_attached_is_rejected():
    """Lens-4 FA-B4 and RG-N2: each was accepted at ``23f3d9f`` (the substring rule
    removed hyphens only)."""
    for text in (
        "well calibratedness",
        "well_calibratedness",
        "well.calibratedness",
        "well calibratedness",
        "Well calibratedly",
        "well.calibratedly",
        "well_calibrateds",
        "well/calibratedness",
    ):
        for fed in (text, f"The model was {text} here."):
            assert checker.free_text_reason(fed) == "free_text_verdict_word", repr(fed)


def test_each_reading_has_a_literal_that_pins_it():
    """For each reading of ``checker._readings`` (indices 0-6), a literal whose rejecting
    readings are asserted, so a sweep mutant dropping a reading is killed (lens-4 RG-N5
    found the 7fa690b reading and the all-``rn`` replacement unpinned). Reading 2 (the
    full map) is not singled out: reading 4 is reading 2 with ``rn`` read as ``m``, and
    no listed word contains ``rn``."""
    expected = {
        "passᴀ": [0],  # 657ef11's map: the small capital A ends the word
        "ᴘassɑ": [1],  # 7fa690b's map: small capital P read, the alpha ends it
        "ᴄonsistentɑ": [1],
        "ϲonsΙstent": [2, 3, 4],  # _BEFORE_NFKC; TR39 reads Greek capital iota as l
        "faΙI": [3],  # ASCII capital I as l, Greek capital iota as i
        "rnΙscalibrated": [4],  # rn as m, Greek capital iota as i
        "turn rnΙscalibrated": [4],  # every rn, not the first only
        "ꓑassIng": [5],  # TR39 (Lisu PA as P), ASCII I read as i
        "ꓝaiI": [6],  # TR39 (Lisu TSA as F) and ASCII I read as l
    }
    for text, readings in expected.items():
        hits = [
            i
            for i, r in enumerate(checker._readings(text))
            if checker._words(r) & checker.VERDICT_WORDS
        ]
        assert hits == readings, (text, hits)
        assert checker.free_text_reason(text) == "free_text_verdict_word", text
    for text in ("turn rneets", "paꜱꜱ"):
        assert checker.free_text_reason(text) == "free_text_verdict_word", text


def test_each_hand_mapped_letter_has_a_literal_the_tr39_readings_do_not_reject():
    """The hand maps of repairs 1-3 beside TR39: each literal carries the Greek capital
    iota, which the full reading takes as ``i`` and TR39 as ``l``, so only the full,
    capital-I or rn reading rejects it, through the letter named."""
    for text, letter in (
        ("unbΙɑsed", "ɑ"),
        ("ƒaΙled", "ƒ"),
        ("faΙǀ", "ǀ"),
        ("Ιncօnsistent", "օ"),
        ("ᏢassΙng", "Ꮲ"),
        ("unbΙаsed", "а"),
    ):
        readings = checker._readings(text)
        hits = [i for i, r in enumerate(readings) if checker._words(r) & checker.VERDICT_WORDS]
        assert hits and max(hits) <= 4, (text, hits)
        assert checker.free_text_reason(text) == "free_text_verdict_word", (text, letter)


def test_prose_the_new_readings_leave_accepted():
    """The literals the orchestrator named, the repair-2 and repair-3 guards, and prose
    with the characters TR39 maps from ASCII punctuation (``|``) and from Greek letters
    used in statistics. ``unmet`` is itself a listed word (``VERDICT_WORDS``) and is
    rejected, at ``23f3d9f`` too."""
    for text in (
        "compass",
        "passport",
        "Illness",
        "compassionate metabolism",
        "In the Internal set the return was modern.",
        "Iterations ran in turn.",
        "Cohen's κ and the α level are reported | per site.",
        "The panel read the images; sensitivity was high.",
    ):
        assert checker.free_text_reason(text) is None, text
    assert checker.free_text_reason("unmet") == "free_text_verdict_word"


# ---------------------------------------------- DEC-60: the vendored TR39 subset


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "tr39_subset", ROOT / "scripts" / "tr39_subset.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_the_vendored_tr39_subset_carries_its_source_and_counts():
    from proofpack.narrate import tr39_confusables as tr39  # noqa: PLC0415 - absent before repair 4

    assert tr39.SOURCE_URL == "https://www.unicode.org/Public/security/latest/confusables.txt"
    assert tr39.VERSION == "18.0.0"
    assert tr39.DATE == "2026-08-06, 01:05:35 GMT"
    assert tr39.FULL_SHA256 == "6ed3ee967c9dfdf6677d563c9985182fbc50a2efb7d6059cd57b2e2ce18f5b92"
    assert (tr39.FULL_BYTES, tr39.FULL_ENTRIES, len(tr39.CONFUSABLES)) == (763128, 6712, 1905)
    assert "https://www.unicode.org/terms_of_use.html" in tr39.NOTICE
    for key, target in tr39.CONFUSABLES.items():
        letters = "".join(c for c in target if unicodedata.category(c) != "Mn")
        assert re.fullmatch(r"[A-Za-z]+", letters), (hex(key), target)


def test_the_vendored_tr39_subset_regenerates_from_the_full_file():
    """When the full ``confusables.txt`` is present (``PROOFPACK_TR39_FULL``, or
    ``workflows/data/confusables-18.0.0.txt`` beside the repository), the generator's
    output equals the committed module, and the file's SHA-256 equals the one recorded."""
    from proofpack.narrate import tr39_confusables as tr39  # noqa: PLC0415 - absent before repair 4

    full = os.environ.get("PROOFPACK_TR39_FULL") or str(
        ROOT.parent / "workflows" / "data" / "confusables-18.0.0.txt"
    )
    if not Path(full).exists():
        pytest.skip(f"full confusables.txt not present at {full}")
    gen = _load_generator()
    data = Path(full).read_bytes()
    assert hashlib.sha256(data).hexdigest() == tr39.FULL_SHA256
    header, entries = gen.parse(data)
    assert (header["version"], header["date"], len(entries)) == (tr39.VERSION, tr39.DATE, 6712)
    assert gen.subset(entries) == tr39.CONFUSABLES
    committed = (ROOT / "src" / "proofpack" / "narrate" / "tr39_confusables.py").read_bytes()
    assert gen.render(header, entries, data) == committed.decode("utf-8").replace("\r\n", "\n")


# ---------------------------------------------- FA-N1 / DEC-62: the manufacturer's words


def test_model_name_version_and_operating_point_are_customer_text_on_t8():
    """Lens-4 FA-N1, DEC-62: model ``Safe triage``, version ``2 unbiased``, operating point
    ``pass``. At ``23f3d9f`` the page test's grep found four hits outside ``.customer-text``
    and the disclaimer (the three page headers and the operating-point cell), and the
    ``<title>`` carried both words."""
    crit = make_criteria(criteria=[_criterion("C1", "pass")], fairness=None)
    crit["model"]["name"] = "Safe triage"
    crit["model"]["version"] = "2 unbiased"
    crit["operating_points"] = [_op("pass", 0.5)]
    doc = assemble(make_cohort(n=200), crit)
    page = render_html.render_t8(doc)
    _, forbidden = _status_and_forbidden_hits(page)
    outside = [h for h in forbidden if not ({"customer-text", "disclaimer"} & h[2])]
    assert outside == []
    headers = re.findall(r'<header class="page-header">(.*?)</header>', page)
    assert len(headers) == 3
    assert all(
        h.startswith('<span class="customer-text">Safe triage v2 unbiased</span> · T8')
        for h in headers
    )
    title = re.search(r"<title>(.*?)</title>", page).group(1)
    assert "Safe" not in title and "unbiased" not in title
    assert '<td class="customer-text">pass</td>' in page


# ---------------------------------------------- the sentence findings


def test_a_dev_row_with_a_blank_y_pred_counts_under_dev_rows():
    """Lens-4 RG-N1 / FA-N2's table, backing the corrected README, schema and docstring
    sentences: 120 rows without a score column, rows 0-19 ``dev``, ``y_pred`` blank on rows
    0, 10, ..., 110 and ``y_true`` blank on rows 0, 20, ..., 100. This test passes at
    ``23f3d9f`` (the behaviour did not change; the sentences did)."""
    cols = _y_pred_only(120)
    cols["dataset"] = ["dev" if i < 20 else "test" for i in range(120)]
    cols["y_pred"] = [None if i % 10 == 0 else v for i, v in enumerate(cols["y_pred"])]
    cols["y_true"] = [None if i % 20 == 0 else v for i, v in enumerate(cols["y_true"])]
    flow = assemble(cols, make_criteria(criteria=[], fairness=None))["flow"]
    assert {k: flow[k] for k in ("rows_read", "dev_rows", "analysed")} == {
        "rows_read": 120,
        "dev_rows": 20,
        "analysed": 90,
    }
    assert (flow["excluded_missing_label"], flow["excluded_missing_score"]) == (5, 5)


def _flat(path: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8").replace("\r\n", "\n")
    return re.sub(r"\s+", " ", text.replace("#:", " "))


def test_the_lens4_false_sentences_are_gone_from_the_shipped_text():
    """Lens-4 RG-N1, FA-N2 and FA-N3: each literal below was a false sentence at
    ``23f3d9f`` (whitespace and comment markers collapsed before the search)."""
    gone = {
        "README.md": [
            "counted under `flow.excluded_missing_score` when the row's `y_true` is present"
        ],
        "schema/schema_v1.json": [
            "counted under flow.excluded_missing_score when its y_true is present"
        ],
        "schema/output_schema_v1.json": [
            '"Rows whose y_true is present and whose prediction input'
        ],
        "src/proofpack/io/schema.py": [
            "A row whose ``y_true`` is present and whose prediction input"
        ],
        "src/proofpack/narrate/templates.py": ["One skeleton differs from D4 section 8's text"],
        "src/proofpack/narrate/checker.py": [
            "(U+03F2, and its capital U+03F9) into a final sigma",
            "The capital forms Ɑ (U+2C6D), Ƒ (U+0191), Օ (U+0555) and ꮲ (U+ABB2)",
            "The Latin small capitals (U+1D00-U+1D22",
            "every capital ``I`` read as ``l``",
        ],
    }
    for path, literals in gone.items():
        text = _flat(path)
        for literal in literals:
            assert literal not in text, (path, literal)


def test_the_sweep_lists_the_repair4_mutants():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mutation_sweep.py"), "--list"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    day8 = {ln.split()[0] for ln in proc.stdout.splitlines() if " day8 " in ln}
    assert {
        "checker_well_calibrated_hyphen_only",
        "checker_tr39_map_empty",
        "checker_tr39_reading_dropped",
        "checker_tr39_capital_i_reading_dropped",
        "claims_metric_ref_split_again",
        "html_metric_ref_split_again",
        "checker_metric_ref_split_again",
        "gates_dec61_y_pred_operating_points_unchecked",
        "run_dec61_gate_not_called_in_overall_block",
        "claims_calib_na_on_any_reason",
        "checker_calib_na_reason_unchecked",
        "html_header_model_not_customer_text",
        "t8_operating_point_cell_not_customer_text",
    } <= day8
