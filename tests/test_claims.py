"""Build day 8 (E8 items 4-6): the claims builder, the template library, the final claims
schema and the claim-binding checker with its adversarial corpus.

* every file in ``tests/fixtures/claims_corpus/`` is a numerically correct but
  semantically false or forbidden claim over the synthetic document (or a document
  patched as the file says); the parametrised test asserts EVERY case is rejected with
  exactly the reason code the file names;
* the synthetic run's own generated claims (three documents: i.i.d. with criteria and a
  fairness bound, clustered, y_pred-only) are ALL accepted and validate against
  ``schema/claims_schema.json``;
* the schema's ``template_id`` enum equals the library's ids; the status, relation and
  comparator enums equal the code's registers; every corpus reason code is in
  ``checker.REASON_CODES``;
* ``resolve`` substitutes the deterministic engine claim for a rejected one and logs the
  rejection; the checker raises nothing on garbage.
"""

from __future__ import annotations

import copy
import json
import string
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from assembler import assemble
from conftest import make_cohort, make_criteria
from proofpack.narrate import checker, templates
from proofpack.narrate import claims as claims_mod
from proofpack.resources import load_guidance_map, load_json_schema
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site

pytestmark = pytest.mark.day8

CORPUS = Path(__file__).resolve().parent / "fixtures" / "claims_corpus"
CORPUS_FILES = sorted(CORPUS.glob("*.json"))


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    return assemble(cohort_with_a_thirty_row_site(), crit)


@pytest.fixture(scope="module")
def clustered_document() -> dict[str, Any]:
    cols = make_cohort(n=200, with_case_id=True)
    cols["case_id"] = [f"c{i // 2:06d}" for i in range(200)]
    crit = make_criteria(
        criteria=[
            {
                "id": "C_over",
                "metric": "sensitivity",
                "operating_point": "op1",
                "scope": "overall",
                "statistic": "ci_lower_bound",
                "comparator": ">=",
                "value": 0.5,
                "author": "A",
                "date": "2026-01-01",
                "justification": "j",
            }
        ],
        clustering={"unit": "case_id", "declared_by": "t"},
        fairness=None,
    )
    return assemble(cols, crit)


@pytest.fixture(scope="module")
def y_pred_only_document() -> dict[str, Any]:
    cols = make_cohort(n=200, with_y_pred=True)
    del cols["score"]
    return assemble(cols, make_criteria(criteria=[], fairness=None))


def _set_pointer(doc: dict[str, Any], ref: str, value: Any) -> None:
    node: Any = doc
    parts = ref[1:].split("/")
    for token in parts[:-1]:
        node = node[int(token)] if isinstance(node, list) else node[token]
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value


# ------------------------------------------------------------------ the corpus (item 6)


def test_the_corpus_holds_at_least_fifty_cases_and_names_a_known_reason_code_each():
    assert len(CORPUS_FILES) >= 50
    names = set()
    for path in CORPUS_FILES:
        entry = json.loads(path.read_text(encoding="utf-8"))
        assert entry["expected_reason_code"] in checker.REASON_CODES, path.name
        assert entry["rule"] and entry["name"] not in names, path.name
        names.add(entry["name"])
        assert ("claim" in entry) != ("claims" in entry), path.name
    # the rules the brief lists at minimum are all present
    for needle in (
        "wrong_subgroup",
        "reference_swapped",
        "status_flipped_met_on_not_met",
        "status_flipped_not_assessable_on_met",
        "status_word_capitalised",
        "criterion_addressed_by_shared_id",
        "difference_sign_flipped",
        "comparator_id",
        "value_ref_to_suppressed_cell",
        "value_ref_to_calibration_when_null",
        "typed_reason_presented_as_estimate",
        "template_id_one_char_off",
        "guidance_ref_not_in_map",
        "fda_anchor_without_draft_qualifier",
        "free_text_ascii_digit",
        "free_text_arabic_indic_digit",
        "free_text_superscript_two",
        "free_text_fullwidth_percent",
        "free_text_number_word_plus_digit",
        "free_text_section_sign",
        "free_text_cfr",
        "free_text_guidance",
        "free_text_pass_lower",
        "free_text_pass_upper",
        "free_text_passes",
        "free_text_well_calibrated",
        "free_text_consistent",
        "free_text_unbiased",
        "free_text_acceptable",
        "free_text_safe",
        "free_text_certified",
        "free_text_approved",
        "free_text_fda_cleared",
        "free_text_cleared",
        "extra_key",
        "missing_value_refs",
        "empty_claims_with_criteria",
    ):
        assert any(needle in n for n in names), needle


@pytest.mark.parametrize("path", CORPUS_FILES, ids=[p.stem for p in CORPUS_FILES])
def test_every_corpus_case_is_rejected_with_the_expected_reason_code(path: Path, document):
    entry = json.loads(path.read_text(encoding="utf-8"))
    doc = copy.deepcopy(document)
    for patch in entry.get("document_patch", []):
        _set_pointer(doc, patch["pointer"], patch["value"])
    guidance_map = entry.get("guidance_map")
    if guidance_map is not None:
        # the override replaces the named rows and keeps the rest of the shipped map
        rows = {r["internal_id"]: dict(r) for r in load_guidance_map()}
        for r in guidance_map:
            rows[r["internal_id"]] = r
        guidance_map = list(rows.values())
    claims = entry["claims"] if "claims" in entry else [entry["claim"]]
    result = checker.check(claims, doc, guidance_map=guidance_map)
    assert len(result.verdicts) == max(1, len(claims))
    verdict = result.verdicts[0]
    assert not verdict.accepted, (path.name, "accepted")
    assert verdict.reason_code == entry["expected_reason_code"], (path.name, verdict)
    # the same claim is rejected through resolve too, and the rejection is logged
    if "claim" in entry:
        _, rejections = checker.resolve(doc, claims, guidance_map=guidance_map)
        assert rejections and rejections[0]["reason_code"] == entry["expected_reason_code"]


def test_the_corpus_is_numerically_correct_where_it_binds_numbers(document):
    """A corpus case is *semantically* false: every pointer it binds that the shipped
    document resolves is a real Number (or the case is about the pointer itself)."""
    pointer_cases = 0
    for path in CORPUS_FILES:
        entry = json.loads(path.read_text(encoding="utf-8"))
        if "claim" not in entry or not isinstance(entry["claim"], dict):
            continue
        if entry["expected_reason_code"] in (
            "value_ref_unresolved",
            "value_ref_not_a_number",
            "value_refs_invalid",
            "missing_key",
        ):
            continue
        for ref in entry["claim"].get("value_refs", []):
            found, value = checker.resolve_pointer(document, ref)
            assert found, (path.name, ref)
            assert checker.is_number_object(value) or checker.is_documented_scalar(ref, value), (
                path.name,
                ref,
            )
            pointer_cases += 1
    assert pointer_cases >= 60


def test_every_reason_code_has_at_least_one_corpus_case():
    """Repair 3 of day 8: 44 codes in ``checker.REASON_CODES`` (``value_ref_unbound``
    joined in repair 2, ``template_mismatch`` in repair 3), 140 corpus files
    (``116``-``130`` joined in repair 2, ``131``-``140`` in repair 3); every code is the
    expected code of at least one file (``claim_id_duplicate`` and
    ``no_claims_for_criteria`` through ``claims`` lists)."""
    expected = {
        json.loads(p.read_text(encoding="utf-8"))["expected_reason_code"] for p in CORPUS_FILES
    }
    assert set(checker.REASON_CODES) - expected == set()
    assert len(checker.REASON_CODES) == 44 and len(CORPUS_FILES) == 140


# ------------------------------------------------------- the engine's own claims (item 4)


@pytest.mark.parametrize("fixture", ["document", "clustered_document", "y_pred_only_document"])
def test_the_synthetic_runs_own_claims_are_all_accepted_and_validate(fixture, request):
    doc = request.getfixturevalue(fixture)
    claims = claims_mod.build_claims(doc)
    assert claims
    jsonschema.validate(claims, load_json_schema("claims_schema.json"))
    result = checker.check(claims, doc)
    assert [v.reason_code for v in result.rejected] == []
    assert len(result.accepted) == len(claims)
    ids = [c["claim_id"] for c in claims]
    assert ids == [f"CL-{i:04d}" for i in range(1, len(claims) + 1)]
    assert all(c["free_text"] is None for c in claims)
    final, rejections = checker.resolve(doc)
    assert final == claims and rejections == []


def test_the_claims_cover_every_slot_the_brief_names(document):
    claims = claims_mod.build_claims(document)
    by_t: dict[str, list] = {}
    for c in claims:
        by_t.setdefault(c["template_id"], []).append(c)
    ops = [k for k in document["overall"] if k != "threshold_free"]
    n_overall = sum(
        1 for op in ops for m in claims_mod.OVERALL_METRIC_ORDER if m in document["overall"][op]
    )
    assert len(by_t["OVERALL_ESTIMATE"]) == n_overall == 13
    assert len(by_t["AUROC_ESTIMATE"]) == 1
    rows = document["subgroups"]
    n_sub = 5 * len(ops) * len(rows)
    assert len(by_t["SUBGROUP_ESTIMATE_WITH_DIFF"]) + len(by_t["SUBGROUP_ESTIMATE"]) == n_sub == 45
    ref_rows = [r for r in rows if r["is_reference"]]
    assert len(by_t["SUBGROUP_ESTIMATE"]) == 5 * len(ops) * len(ref_rows) == 15
    assert len(by_t["CALIB_HIERARCHY"]) == 1 and "CALIB_NA" not in by_t
    assert len(by_t["FAIRNESS_GAP"]) == len(document["fairness"]["gaps"]) * len(ops) == 1
    crit = by_t["CRITERION_STATUS"]
    assert len(crit) == len(document["criteria_results"]) == 9
    for i, c in enumerate(crit):
        row = document["criteria_results"][i]
        assert c["criterion_index"] == i and c["criterion_id"] == row["criterion_id"]
        assert c["status"] == row["status"] and c["comparator_id"] == row["comparator"]
        if row["metric_ref"] is None:
            assert c["value_refs"] == []
        else:
            found, value = checker.resolve_pointer(document, c["value_refs"][0])
            assert found and checker.is_number_object(value)
    # the three C_f1_site rows share an id and are addressed by three positions
    shared = [c for c in crit if c["criterion_id"] == "C_f1_site"]
    assert [c["criterion_index"] for c in shared] == [2, 3, 4]
    # the difference relation is the engine's reading of the diff Number
    f = next(c for c in by_t["SUBGROUP_ESTIMATE_WITH_DIFF"] if c["subgroup"]["level"] == "F")
    diff = document["subgroups"][4]["diff_vs_reference"]["op1"][f["metric_id"]]["number"]
    assert f["reference"] == {"attribute": "sex", "level": "M"}
    assert f["relation"] == claims_mod.relation_of(diff, difference=True) == "within"
    assert diff["ci_lo"] < 0 < diff["ci_hi"]
    # every guidance_ref used is in the map
    ids = {r["internal_id"] for r in load_guidance_map()}
    assert {c["guidance_ref"] for c in claims} - {None} <= ids


def test_relation_of_reads_a_number_the_documented_way():
    num = {
        "est": 0.1,
        "ci_lo": 0.02,
        "ci_hi": 0.2,
        "suppressed": False,
        "not_estimable_reason": None,
    }
    assert claims_mod.relation_of(num) == "estimate"
    assert claims_mod.relation_of(num, difference=True) == "above"
    assert claims_mod.relation_of({**num, "ci_lo": -0.3, "ci_hi": -0.1}, difference=True) == "below"
    assert claims_mod.relation_of({**num, "ci_lo": -0.3}, difference=True) == "within"
    assert claims_mod.relation_of({**num, "ci_lo": 0.0}, difference=True) == "within"
    reason = {**num, "ci_lo": None, "ci_hi": None, "not_estimable_reason": "single_class"}
    assert claims_mod.relation_of(reason) == "not_assessable"
    assert claims_mod.relation_of({**num, "suppressed": True}, difference=True) == "not_assessable"
    assert claims_mod.relation_of(None) == "not_assessable"


def test_dotted_metric_ref_to_pointer():
    f = claims_mod._dotted_to_pointer
    assert f("overall.op1.sensitivity") == "/overall/op1/sensitivity"
    assert (
        f("subgroups[8].metrics.op1.accuracy.number") == "/subgroups/8/metrics/op1/accuracy/number"
    )
    assert f("fairness.gaps[0].operating_points.op1.tpr_gap.number") == (
        "/fairness/gaps/0/operating_points/op1/tpr_gap/number"
    )
    assert f(None) is None and f("") is None
    assert claims_mod.pointer("a/b", "c~d") == "/a~1b/c~0d"


# ------------------------------------------------- schema and library agreement (item 4)


def test_the_claims_schema_is_final_and_its_enums_agree_with_the_code():
    schema = load_json_schema("claims_schema.json")
    assert schema["x-proofpack"]["status"] == "final"
    assert schema["x-proofpack"]["rejections_key"] == "claim_rejections"
    item = schema["items"]
    assert item["additionalProperties"] is False
    assert tuple(item["required"]) == checker.REQUIRED_KEYS
    assert set(item["properties"]) == set(checker.REQUIRED_KEYS)
    assert item["properties"]["template_id"]["enum"] == list(templates.LIBRARY)
    assert item["properties"]["status"]["enum"] == [*checker.STATUSES, None]
    assert item["properties"]["relation"]["enum"] == list(claims_mod.RELATIONS)
    assert item["properties"]["comparator_id"]["enum"] == [*claims_mod.COMPARATOR_IDS, None]


def test_the_library_transcribes_d4_section_8_and_every_slot_is_a_formatter_field():
    lib = templates.LIBRARY
    assert len(lib) == 56
    d4_ids = {
        "DECL_ECHO",
        "THRESH_PROVENANCE",
        "FLOW_COUNTS",
        "TABLE1_INTRO",
        "SIMILARITY_SUMMARY",
        "OVERLAP_RESULT",
        "SITE_COUNT",
        "REPRESENT_ROW",
        "UNKNOWN_ROW_NOTE",
        "REF_STD_TYPE_NOTE",
        "RATER_COLS_NOTE",
        "OVERALL_ESTIMATE",
        "INDET_BOTH_WAYS",
        "PPV_AT_PREVALENCE",
        "PREV_MISMATCH_FLAG",
        "AUROC_ESTIMATE",
        "CALIB_HIERARCHY",
        "CALIB_CURVE_FLAG",
        "CALIB_NA",
        "SUBGROUP_TABLE_INTRO",
        "SUBGROUP_ESTIMATE_WITH_DIFF",
        "PRESPEC_FLAG",
        "LOW_N_CAVEAT",
        "HETERO_EXPLORATORY_FOOTNOTE",
        "CRITERION_STATUS",
        "CRITERION_NOT_MET_RECORD",
        "ATTAINABILITY_NOTE",
        "FAIRNESS_INTRO",
        "FAIRNESS_GAP",
        "SELECTION_RATE_LABEL",
        "IMPOSSIBILITY_STATEMENT",
        "LOSO_RESULT",
        "THRESH_SENS",
        "MISSINGNESS_SENS",
        "DUPLICATES_NOTE",
        "MONITORING_POINTER",
        "PUBLIC_SUMMARY_NUMBERS",
        "MODEL_CARD_LIMITS",
        "PAIRED_DIFF",
        "MCNEMAR_RESULT",
        "UNPAIRED_LABEL",
        "LEDGER_STATEMENT",
        "LEDGER_WARNING",
        "IMPACT_INPUTS_NOTE",
        "MONITORING_RULE_ECHO",
        "PSI_RESULT",
        "KS_RESULT",
        "PREVALENCE_SHIFT",
        "PERIOD_METRIC_ROW",
        "CONTROL_RULE_STATUS",
        "SUBGROUP_TREND_ROW",
        "AGREEMENT_RATE_ROW",
        "INDET_RATE_ROW",
        "ATTR_DRIFT_ROW",
        "SUMMARY_POINTER",
    }
    assert set(lib) - d4_ids == {"SUBGROUP_ESTIMATE"}  # the one recorded engine addition
    assert d4_ids <= set(lib)
    for tid, t in lib.items():
        fields = [f for _, f, _, _ in string.Formatter().parse(t.skeleton) if f is not None]
        assert fields == list(dict.fromkeys(fields)) or tid in (
            "CALIB_HIERARCHY",
            "FAIRNESS_GAP",
            "INDET_BOTH_WAYS",
            "PPV_AT_PREVALENCE",
            "MISSINGNESS_SENS",
            "PREVALENCE_SHIFT",
        ), tid
        assert t.refs[0] <= t.refs[1]
        assert t.guidance_ref is None or t.guidance_ref in {
            r["internal_id"] for r in load_guidance_map()
        }
        # a skeleton carries no digit outside its fixed text and no verdict word
        allowed = [None, "free_text_digit", "free_text_percent"]
        if tid == "CRITERION_NOT_MET_RECORD":
            # D4's fixed T2 sentence carries the status phrase itself ("Record of
            # criterion not met"); every other skeleton takes it through {status_word}
            allowed.append("free_text_verdict_word")
        assert checker.free_text_reason(t.skeleton) in allowed, tid
    assert lib["OVERALL_ESTIMATE"].skeleton == (
        "{metric_name} at operating point {op_id} was {k}/{n} ({est}), 95% CI {ci_lo} to "
        "{ci_hi} ({method})."
    )
    assert templates.STATUS_WORDS == {
        "met": "criterion met",
        "not_met": "criterion not met",
        "not_assessable": "not assessable",
    }
    assert templates.NARRATIVE_FOOTER == (
        "Machine-drafted; requires review by the manufacturer's statistician and regulatory lead."
    )
    assert templates.slots("SUBGROUP_ESTIMATE_WITH_DIFF") == (
        "attribute",
        "level",
        "metric_name",
        "k",
        "n",
        "est",
        "ci",
        "diff",
        "diff_ci",
        "reference_level",
    )


# ------------------------------------------------------------- the checker (item 5)


def test_free_text_reason_on_literal_inputs():
    f = checker.free_text_reason
    assert f("Sensitivity was high in every subgroup.") is None
    assert f("Sensitivity was 0.9.") == "free_text_digit"
    assert f("n²") == "free_text_digit"
    assert f("٣") == "free_text_digit"
    assert f("Ⅷ") == "free_text_digit"  # a Roman numeral (Nl)
    assert f("ninety ％") == "free_text_percent"
    assert f("§ VI") == "free_text_section_sign"
    assert f("per CFR") == "free_text_cfr"
    assert f("per the Guidance") == "free_text_guidance"
    assert f("PASS") == "free_text_verdict_word"
    assert f("well-calibrated") == "free_text_verdict_word"
    assert f("non-inferior") == "free_text_verdict_word"
    assert f("FDA-cleared") == "free_text_certification_word"
    assert f("endorsement") == "free_text_certification_word"
    # 'guidance_ref' in prose is the word guidance
    assert f("see guidance_ref") == "free_text_guidance"
    # words that merely contain a verdict word are not whole-word hits
    assert f("compassionate metabolism") is None


def test_the_checker_never_raises_on_garbage(document):
    garbage = [
        None,
        42,
        "text",
        [],
        {},
        {"claim_id": 3},
        {k: None for k in checker.REQUIRED_KEYS},
        {**{k: None for k in checker.REQUIRED_KEYS}, "claim_id": "CL-0001", "value_refs": None},
        {
            **{k: None for k in checker.REQUIRED_KEYS},
            "claim_id": "CL-0001",
            "template_id": "OVERALL_ESTIMATE",
            "relation": "estimate",
            "value_refs": ["/overall/op1/sensitivity"],
            "criterion_index": True,
        },
    ]
    result = checker.check(garbage, document)
    assert len(result.verdicts) == len(garbage)
    assert all(not v.accepted and v.reason_code in checker.REASON_CODES for v in result.verdicts)
    for bad in (None, "x", {"a": 1}, 7):
        r = checker.check(bad, document)
        assert r.verdicts and not r.verdicts[0].accepted
    assert not checker.check([], None).verdicts  # no criteria, no claims: nothing to say
    assert checker.check([], {"criteria_results": [{"status": "met"}]}).verdicts[0].reason_code == (
        "no_claims_for_criteria"
    )


def test_resolve_substitutes_the_deterministic_claim_and_logs_the_rejection(document):
    engine = claims_mod.build_claims(document)
    tampered = copy.deepcopy(engine)
    crit = next(i for i, c in enumerate(tampered) if c["template_id"] == "CRITERION_STATUS")
    tampered[crit]["status"] = "met" if tampered[crit]["status"] != "met" else "not_met"
    sub = next(
        i for i, c in enumerate(tampered) if c["template_id"] == "SUBGROUP_ESTIMATE_WITH_DIFF"
    )
    tampered[sub]["relation"] = "above"
    tampered[0]["free_text"] = "This model is approved."
    final, rejections = checker.resolve(document, tampered)
    assert [r["reason_code"] for r in rejections] == [
        "free_text_certification_word",
        "relation_mismatch",
        "status_mismatch",
    ]
    assert all(r["substituted"] is True for r in rejections)
    assert {r["claim_id"] for r in rejections} == {
        tampered[0]["claim_id"],
        tampered[sub]["claim_id"],
        tampered[crit]["claim_id"],
    }
    assert final == engine  # every slot filled with the engine's own claim
    assert checker.check(final, document).rejected == []
    # a claim with no slot to substitute is dropped and logged as not substituted
    stray = copy.deepcopy(engine[0])
    stray["claim_id"] = "CL-9999"  # its own id: a repeated id is claim_id_duplicate (repair 1)
    stray["template_id"] = "SUMMARY_POINTERS"
    final2, rejections2 = checker.resolve(document, [*engine, stray])
    assert final2 == engine and rejections2[0]["substituted"] is False
    assert rejections2[0]["reason_code"] == "template_unknown"


def test_the_guidance_map_draft_rows_all_carry_the_qualifier_and_are_the_fda_aidsf_rows():
    rows = {r["internal_id"]: r for r in load_guidance_map()}
    drafts = {k for k, r in rows.items() if r["status"].lower().startswith("draft")}
    assert drafts == {k for k in rows if k.startswith("FDA_AIDSF_")}
    assert len(drafts) == 12
    for k in drafts:
        assert not checker.draft_row_unqualified(rows[k]), k
        assert rows[k]["version_date"] == "2025-01-07"
    assert checker.draft_row_unqualified({"status": "draft"})
    assert checker.draft_row_unqualified({"status": "DRAFT (January 2025)"})
    assert not checker.draft_row_unqualified({"status": "final"})
