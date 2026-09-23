"""Repair 3 of build day 8 (23 September 2026): regression tests for the lens-3 findings
at ``7fa690b`` - RG-B1 (``well-calibrated`` with letters attached; and ``passᴀ``, found
beside it), RG-B2 / FA-B1 (template relabels, slot permutations and count templates),
RG-B3 (the withdrawn Mn / Cf mutant), FA-B2 (nine homoglyph literals), FA-B3 (reserved
operating-point ids) and the sentence findings RG-N3, FA-N3 and FA-N4. Each test names
the literal inputs it feeds and the figures it asserts; the repair-3 note quotes, per
test, the first E line in a worktree at ``0f553c9`` with PYTHONPATH forced.
"""

from __future__ import annotations

import copy
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
from proofpack.errors import EXIT_HALT, EXIT_OK, HaltError
from proofpack.io.declare import validate_dict
from proofpack.narrate import checker
from proofpack.narrate import claims as claims_mod
from proofpack.narrate.templates import LIBRARY
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site
from test_run_cli import _own_home, _prepare

pytestmark = pytest.mark.day8

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    return assemble(cohort_with_a_thirty_row_site(), crit)


def _code(claim: dict[str, Any], doc: dict[str, Any]) -> str | None:
    v = checker.check([claim], doc).verdicts[0]
    return None if v.accepted else v.reason_code


# ---------------------------------------------- RG-B1: the rejections 657ef11 made, kept
#
# Frozen copies of the word rule as it stood at 657ef11 and at 7fa690b (read from
# `git show <sha>:src/proofpack/narrate/checker.py`), so this file does not read the
# code under test to decide what the earlier commits rejected. Digit, per-cent and
# section-sign rules are unchanged since 657ef11 and are left out.

#: 657ef11's map (27 letters) and 7fa690b's (those 27 plus 24 small capitals), as printed
#: by each commit's ``CONFUSABLES`` in a worktree
_R1 = dict(zip("аеорсухіјѕԁһԛԝӏαεικνορτυχɡı", "aeopcyxijsdhqwlaeikvoptuxgi", strict=True))
_R2 = {**_R1, **dict(zip("ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘʀꜱᴛᴜᴠᴡʏᴢ", "abcdefghijklmnoprstuvwyz", strict=True))}
_HYPHENS = frozenset("‐\u2011‒–—―")


def _norm(text: str, table: dict[str, str]) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    out = []
    for ch in unicodedata.normalize("NFD", folded):
        if unicodedata.category(ch) in ("Mn", "Cf"):
            continue
        ch = table.get(ch, ch)
        out.append("-" if ch in _HYPHENS else ch)
    return "".join(out)


def _code_657ef11(text: str) -> str | None:
    n = _norm(text, _R1)
    words: set[str] = set()
    for token in set(re.split(r"[^a-z\-]+", n)) - {""}:
        words.add(token.strip("-"))
        words.update(token.split("-"))
    words -= {""}
    if words & checker.VERDICT_WORDS or "well-calibrated" in n:
        return "free_text_verdict_word"
    if "cfr" in words:
        return "free_text_cfr"
    if "guidance" in words:
        return "free_text_guidance"
    if words & checker.CERTIFICATION_WORDS or any(w.startswith("fda-") for w in words):
        return "free_text_certification_word"
    return None


def _code_7fa690b(text: str) -> str | None:
    n = _norm(text, _R2)
    tokens = [t for t in re.split(r"[^a-z\-]+", n) if t.strip("-")]
    words: set[str] = set()
    for token in tokens:
        words.add(token.strip("-"))
        words.update(token.split("-"))
        words.add(token.replace("-", ""))
    parts = [t.replace("-", "") for t in tokens]
    for i in range(len(parts)):
        joined = parts[i]
        for j in range(i + 1, min(i + 14, len(parts))):
            joined += parts[j]
            words.add(joined)
    words -= {""}
    if words & checker.VERDICT_WORDS or words & {"well-calibrated", "wellcalibrated"}:
        return "free_text_verdict_word"
    if "cfr" in words:
        return "free_text_cfr"
    if "guidance" in words:
        return "free_text_guidance"
    if words & checker.CERTIFICATION_WORDS or any(w.startswith("fda-") for w in words):
        return "free_text_certification_word"
    return None


def _spellings() -> list[str]:
    """Lens RG-B1's generator (``probe/fz.py``), with the small capital ``ᴀ`` and the
    Latin alpha ``ɑ`` added to the affixes: every listed word and ``well-calibrated``,
    with ten prefixes and ten suffixes, nine attached tails, and eleven separators at
    every internal position; each bare and inside a sentence."""
    words = sorted(
        set(checker.VERDICT_WORDS) | set(checker.CERTIFICATION_WORDS) | {"well-calibrated"}
    )
    affix = ["", "ness", "ly", "s", "ed", "ing", "x", "un", "non", "pre", "ᴀ", "ɑ"]
    tails = ["-", "_", "\u00ad", "\u200d", "\u2011", "'s", "-ish", "ᴀ", "ɑ"]
    seps = [" ", "-", ".", "\u00ad", "\u200b", "\x01", "\u2011", "/", "'", "_", "\u0301"]
    cands: set[str] = set()
    for w in words:
        for a in affix:
            for b in affix:
                cands.add(b + w + a)
        for t in tails:
            cands.add(w + t)
            cands.add(t + w)
        for s in seps:
            for k in range(1, len(w)):
                cands.add(w[:k] + s + w[k:])
    out = []
    for t in sorted(cands):
        out.extend((t, f"The model was {t} here."))
    return out


def test_every_spelling_rejected_at_657ef11_or_7fa690b_is_still_rejected():
    """Lens RG-B1: 180 texts of its 18,752 were rejected at 657ef11 and accepted at
    7fa690b, each ``well-calibrated`` with letters attached. With the small capital and
    the alpha added as affixes (the letters repair 2 and repair 3 map), this generator
    gives the count asserted below; every text either earlier rule rejected is rejected."""
    texts = _spellings()
    assert len(texts) == 23020
    lost = [
        t
        for t in texts
        if (_code_657ef11(t) is not None or _code_7fa690b(t) is not None)
        and checker.free_text_reason(t) is None
    ]
    assert lost == []
    f = checker.free_text_reason
    for text in (
        "well-calibratedness",
        "well-calibratedly",
        "well-calibrateds",
        "unwell-calibratedness",
        "wellcalibratedness",
        "passᴀ",  # 657ef11: ᴀ split it from pass; 7fa690b read passa
        "ᴀpass",
        "passɑ",
    ):
        assert f(text) == "free_text_verdict_word", repr(text)


# ---------------------------------------------- RG-B3: the Mn / Cf drop step, pinned


def test_a_format_character_inside_an_unlisted_word_is_dropped_not_a_boundary():
    """Lens RG-B3: ``com\\u00adpass`` (a soft hyphen), ``pass\\u200dport`` (a zero-width
    joiner) and ``tres\\u00adpass`` read ``compass``, ``passport`` and ``trespass``. With
    the drop step planted out (sweep mutant ``checker_format_characters_kept``) each was
    ``free_text_verdict_word`` at 7fa690b. This test passes at 0f553c9: it is the pin for
    that mutant, and the listing test below is the one that fails there."""
    for text in ("com\u00adpass", "pass\u200dport", "tres\u00adpass"):
        assert checker.free_text_reason(text) is None, repr(text)
    assert checker.free_text_reason("pa\u00adss") == "free_text_verdict_word"


def test_the_sweep_lists_the_restored_mutant_and_the_repair3_mutants():
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
        "checker_format_characters_kept",
        "checker_well_calibrated_substring_dropped",
        "checker_earlier_readings_dropped",
        "checker_not_met_record_on_any_row",
        "checker_template_shapes_unchecked",
        "checker_slot_order_unchecked",
        "checker_calib_na_beside_calibration",
        "declare_reserved_operating_point_ids_accepted",
    } <= day8
    source = (ROOT / "scripts" / "mutation_sweep.py").read_text(encoding="utf-8")
    assert "became equivalent" not in source


# ---------------------------------------------- FA-B2: the nine homoglyph literals


def test_the_nine_homoglyph_literals_and_their_capitals_are_rejected():
    """Lens FA-B2 at 7fa690b: these nine were accepted. The capitals Ɑ (U+2C6D), Ƒ
    (U+0191), Օ (U+0555), ꮲ (U+ABB2) and Ϲ (U+03F9) are fed beside them. The class of
    homoglyph spellings is open (needs-from-Josh in the repair-3 note); this test feeds
    these literals and no others."""
    f = checker.free_text_reason
    for text in (
        "pɑss",
        "unbiɑsed",
        "faiI",
        "ƒail",
        "faiǀ",
        "gօօd",
        "ϲonsistent",
        "Ꮲass",
        "rneets",
        "PⱭSS",
        "ƑAIL",
        "GՕՕD",
        "ꮲass",
        "Ϲonsistent",
    ):
        assert f(f"Sensitivity looked {text} here.") == "free_text_verdict_word", repr(text)
    # ordinary prose the two new readings (capital I as l, rn as m) leave accepted
    for text in (
        "In the Internal set the return was modern.",
        "Iterations ran in turn.",
        "compass",
        "passport",
    ):
        assert f(text) is None, text
    # _tokens reads a-z and '-' only: at the 657ef11 reading, before the map, the alpha
    # ends a run
    assert checker._tokens(checker.normalise_free_text("pɑss", checker._CONFUSABLES_R1)) == [
        "p",
        "ss",
    ]


# ---------------------------------------------- RG-B2 / FA-B1: template binding


def test_the_round_3_template_relabels_are_rejected_with_the_named_code(document):
    """The lens-3 pair's literal claims on the synthetic document (70 engine claims):
    each was accepted at 7fa690b."""
    engine = claims_mod.build_claims(document)
    assert len(engine) == 70 and checker.check(engine, document).rejected == []
    by_id = {c["claim_id"]: c for c in engine}
    c_met = by_id["CL-0062"]
    assert (c_met["criterion_id"], c_met["status"]) == ("C_met", "met")
    cases: list[tuple[dict[str, Any], str | None]] = [
        ({**copy.deepcopy(c_met), "template_id": "CRITERION_NOT_MET_RECORD"}, "template_mismatch"),
        ({**copy.deepcopy(by_id["CL-0001"]), "template_id": "AUROC_ESTIMATE"}, "value_ref_unbound"),
        (
            {**copy.deepcopy(by_id["CL-0014"]), "template_id": "OVERALL_ESTIMATE"},
            "value_ref_unbound",
        ),
        (
            {
                **copy.deepcopy(by_id["CL-0014"]),
                "metric_id": "prevalence",
                "value_refs": ["/overall/threshold_free/prevalence"],
            },
            "metric_mismatch",
        ),
    ]
    gap, cal = by_id["CL-0061"], by_id["CL-0060"]
    g = list(gap["value_refs"])
    cases.append(
        ({**copy.deepcopy(gap), "value_refs": [g[1], g[0], g[2], g[3]]}, "value_ref_unbound")
    )
    cases.append(({**copy.deepcopy(gap), "value_refs": g[::-1]}, "value_ref_unbound"))
    k = list(cal["value_refs"])
    cases.append(({**copy.deepcopy(cal), "value_refs": [k[1], k[0], *k[2:]]}, "value_ref_unbound"))
    cases.append(({**copy.deepcopy(cal), "value_refs": k[::-1]}, "value_ref_unbound"))
    count = {
        **copy.deepcopy(by_id["CL-0001"]),
        "metric_id": None,
        "operating_point": None,
        "relation": "not_assessable",
        "guidance_ref": None,
    }
    flow7 = [
        f"/flow/{k}"
        for k in (
            "rows_read",
            "excluded_missing_label",
            "excluded_missing_score",
            "indeterminate",
            "analysed",
            "n_cases",
            "n_sites",
        )
    ]
    cases += [
        ({**count, "template_id": "CALIB_NA", "value_refs": []}, "template_mismatch"),
        (
            {**count, "template_id": "SITE_COUNT", "value_refs": ["/flow/rows_read"]},
            "value_ref_unbound",
        ),
        ({**count, "template_id": "SITE_COUNT", "value_refs": ["/flow/n_sites"]}, None),
        (
            {
                **count,
                "template_id": "LEDGER_STATEMENT",
                "value_refs": ["/criteria_results/0/value", "/fairness/bound"],
            },
            "value_ref_unbound",
        ),
        (
            {**count, "template_id": "DUPLICATES_NOTE", "value_refs": ["/manifest/seed"]},
            "value_ref_unbound",
        ),
        ({**count, "template_id": "FLOW_COUNTS", "value_refs": flow7[::-1]}, "value_ref_unbound"),
        ({**count, "template_id": "FLOW_COUNTS", "value_refs": flow7}, None),
        (
            {
                **count,
                "template_id": "FLOW_COUNTS",
                "metric_id": "sensitivity",
                "operating_point": "op1",
                "subgroup": {"attribute": "sex", "level": "F"},
                "value_refs": ["/flow/analysed"],
            },
            "template_scope_mismatch",
        ),
    ]
    for claim, expected in cases:
        assert _code(claim, document) == expected, (claim["template_id"], claim["value_refs"])


def test_every_engine_claim_relabelled_to_every_other_template(document):
    """Lens RG-B2 re-ran lens 2's single-field sweep at 7fa690b: 39 of 8,988 accepted,
    among them 18 criterion relabels and 14 relabels between OVERALL_ESTIMATE and
    AUROC_ESTIMATE. Here: each of the 70 engine claims under each of the other 55
    library templates (3,850 claims). Accepted, and asserted: the two criterion rows with
    status ``not_met`` (C_n30, fairness:tpr_gap) as CRITERION_NOT_MET_RECORD, and the two
    rows whose ``attainable_at_n`` is a boolean (C_met, C_n30) as ATTAINABILITY_NOTE."""
    engine = claims_mod.build_claims(document)
    relabels = 0
    accepted: list[tuple[str, str]] = []
    for claim in engine:
        for t in LIBRARY:
            if t == claim["template_id"]:
                continue
            relabels += 1
            if _code({**copy.deepcopy(claim), "template_id": t}, document) is None:
                accepted.append((claim["criterion_id"] or claim["claim_id"], t))
    assert relabels == 3850
    assert sorted(accepted) == [
        ("C_met", "ATTAINABILITY_NOTE"),
        ("C_n30", "ATTAINABILITY_NOTE"),
        ("C_n30", "CRITERION_NOT_MET_RECORD"),
        ("fairness:tpr_gap", "CRITERION_NOT_MET_RECORD"),
    ]
    rows = document["criteria_results"]
    assert [r["status"] for r in rows if r["criterion_id"] in ("C_n30", "fairness:tpr_gap")] == [
        "not_met",
        "not_met",
    ]
    assert [r["attainable_at_n"] for r in rows[:2]] == [True, False]


# ---------------------------------------------- FA-B3: reserved operating-point ids


@pytest.mark.parametrize("op_id", ["threshold_free", "auroc", "brier"])
def test_an_operating_point_id_the_document_reserves_halts_h08(op_id, tmp_path, monkeypatch):
    """Lens FA-B3 at 7fa690b: an operating point declared ``threshold_free`` ran to exit 0
    with ``overall`` holding only the threshold-free block and criterion C1 printed
    ``not_assessable`` / ``metric_not_computed``. Measured in repair 3 at 0f553c9 on the
    200-row cohort: ids ``auroc`` and ``brier`` ran to exit 0 with 15 engine claims where
    ``op1`` gives 60 (each subgroup row's ``metrics[op_id]`` is the subgroup AUROC or
    Brier cell)."""
    crit = make_criteria(criteria=[], fairness=None)
    crit["operating_points"][0]["id"] = op_id
    with pytest.raises(HaltError) as ei:
        validate_dict(crit)
    assert ei.value.code == "H08"
    assert ei.value.detail == {"field": "operating_points", "reserved": [op_id]}
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path, cols=make_cohort(n=200), crit=crit)
    out = tmp_path / "pack"
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--offline"],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_HALT and not out.exists()


def test_the_ids_the_lens_ran_clean_still_run(tmp_path, monkeypatch):
    """Lens FA-B3: ids ``two_by_two`` and ``0`` ran clean (60 claims, 0 rejected)."""
    for op_id in ("two_by_two", "0"):
        crit = make_criteria(criteria=[], fairness=None)
        crit["operating_points"][0]["id"] = op_id
        doc = assemble(make_cohort(n=200), crit)
        engine = claims_mod.build_claims(doc)
        assert len(engine) == 60 and checker.check(engine, doc).rejected == []
    _own_home(tmp_path, monkeypatch)
    crit = make_criteria(criteria=[], fairness=None)
    crit["operating_points"][0]["id"] = "two_by_two"
    csv_path, yml = _prepare(tmp_path, cols=make_cohort(n=200), crit=crit)
    rc = main(
        [
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--out",
            str(tmp_path / "pack"),
            "--offline",
        ],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_OK


# ---------------------------------------------- the sentence findings


def test_a_blank_y_pred_on_a_blank_label_row_counts_under_missing_label():
    """Lens FA-N3's second table, backing the corrected README and schema sentences: 120
    rows without a score column, ``y_pred`` blank on rows 0, 10, ..., 110 and ``y_true``
    blank on rows 0, 20, ..., 100 (six of the twelve). This test passes at 0f553c9 (the
    behaviour did not change; the sentences did)."""
    cols = make_cohort(n=120, with_y_pred=True)
    del cols["score"]
    cols["y_pred"] = [None if i % 10 == 0 else v for i, v in enumerate(cols["y_pred"])]
    cols["y_true"] = [None if i % 20 == 0 else v for i, v in enumerate(cols["y_true"])]
    doc = assemble(cols, make_criteria(criteria=[], fairness=None))
    assert doc["flow"]["excluded_missing_label"] == 6
    assert doc["flow"]["excluded_missing_score"] == 6
    assert doc["flow"]["analysed"] == 108


def test_the_refused_sentences_are_gone_from_the_shipped_text():
    """Lenses RG-N3, FA-N3, FA-N4 and RG-B2 at 7fa690b: each literal below was a false
    sentence in shipped text."""
    checker_src = (ROOT / "src" / "proofpack" / "narrate" / "checker.py").read_text(
        encoding="utf-8"
    )
    assert "so ``AUROC_ESTIMATE`` with ``op1`` is refused" not in checker_src
    assert "The runs of letters and hyphens" not in checker_src
    gates_src = (ROOT / "src" / "proofpack" / "gates.py").read_text(encoding="utf-8")
    assert "analysis_mask` excludes it and counts it" not in gates_src.replace("\n", " ")
    corpus = (
        ROOT / "tests" / "fixtures" / "claims_corpus" / "129_free_text_pass_spaced_letters.json"
    ).read_text(encoding="utf-8")
    assert "every run of consecutive tokens" not in corpus
    assert "(on a table without a score column, a y_pred)" in LIBRARY["FLOW_COUNTS"].skeleton
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "from every statistic and counted under `flow.excluded_missing_score` (the" not in (
        readme.replace("\r\n", "\n").replace("\n  ", " ")
    )
