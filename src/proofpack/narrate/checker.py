"""The claim-binding checker (D1 section 4.4; build day 8, E8).

:func:`check` is pure - it reads the claims, the document, the template library and the
guidance map, returns one verdict per claim and raises nothing: malformed input is a
typed rejection (``not_an_object``, ``missing_key``, ``unknown_key``, ...). The rules,
applied in this order and stopping at the first that fails:

1. the claim is an object with exactly the keys of ``schema/claims_schema.json``
   (``not_an_object`` / ``missing_key`` / ``unknown_key``), ``claim_id`` matches
   ``CL-`` + digits, ``value_refs`` is a list of strings (``claim_id_invalid``,
   ``value_refs_invalid``);
2. ``template_id`` is in the library (``template_unknown``); ``relation`` is in its
   enum (``relation_unknown``); ``status`` is ``null`` or exactly one of ``met`` /
   ``not_met`` / ``not_assessable`` - case-sensitive, so ``Met`` is
   ``status_not_in_enum``; ``comparator_id`` is in its enum (``comparator_unknown``);
   ``metric_id`` is null or in D1 section 4.3's enum (``metric_unknown``);
3. the number of ``value_refs`` is within the template's range (``value_refs_count``);
   every ``value_ref`` is an RFC 6901 pointer that resolves in the document
   (``value_ref_unresolved``) to a Number object (the eight required keys of D1 section
   4.1) or to one of the documented scalars in :data:`DOCUMENTED_SCALARS`
   (``value_ref_not_a_number``); a resolved Number that is suppressed is refused whatever
   the relation (``value_ref_suppressed``);
4. ``relation`` equals the engine's recomputation from the bound Numbers
   (:func:`proofpack.narrate.claims.relation_of`): a Number carrying a typed reason
   presented as an estimate, or a difference whose sign the claim states wrongly, is
   ``relation_mismatch``;
5. ``subgroup`` and ``reference`` name rows of ``document.subgroups``
   (``subgroup_not_in_document`` / ``reference_not_in_document``); every pointer under
   ``/subgroups/<i>/`` points at the claimed subgroup's own row (``subgroup_mismatch``:
   the right number attached to the wrong subgroup); ``reference`` is the attribute's
   declared reference level (``reference_mismatch``: the reference swapped);
6. ``comparator_id`` matches the row: on a difference claim it is the difference block
   the second pointer reads; on a criterion claim it is the row's comparator
   (``comparator_mismatch``);
7. a criterion claim addresses its row **by position**: ``criterion_index`` is an integer
   in range (``criterion_index_missing`` when an id is named and no index -
   two rows may share an id; ``criterion_index_invalid``); ``criterion_id`` equals the
   row's (``criterion_id_mismatch``); ``status`` equals the row's
   (``status_mismatch``); and, on a ``met`` / ``not_met`` row, comparing the bound
   Number's named statistic with the row's comparator and value gives the same status
   (``status_recomputation_mismatch``). A claim under any other template carries no
   status (``status_on_non_criterion``);
8. ``guidance_ref`` is null or an ``internal_id`` of the guidance map
   (``guidance_ref_unknown``); a draft row - status beginning ``draft`` - must carry the
   qualifier ``not for implementation`` in its status (``guidance_draft_unqualified``);
9. ``free_text``, when not null, contains no digit in any script (Unicode ``Nd``, ``Nl``
   and ``No``, so the Arabic-Indic digits and a superscript two are digits; the text is
   NFKC-normalised first, so a fullwidth per-cent sign is ``%``): ``free_text_digit``;
   no ``%`` or per-mille sign (``free_text_percent``); none of :data:`VERDICT_WORDS` as
   a whole word in any case (``free_text_verdict_word``); no section sign
   (``free_text_section_sign``); not ``CFR`` as a whole word (``free_text_cfr``); not
   ``guidance`` as a whole word (``free_text_guidance``); none of
   :data:`CERTIFICATION_WORDS` (``free_text_certification_word``).

At document level, an empty claims list on a document that carries criteria rows is one
rejection with ``claim_id`` null (``no_claims_for_criteria``): a T8 that printed no
criterion sentence beside a criteria table would be silent where D4 section 11 item 7
requires a count.

On rejection the block is replaced by the deterministic template claim for its slot
(:func:`resolve`) and the rejection is recorded in the document's ``claim_rejections``
list, which T8 section 7 prints.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from proofpack.narrate import claims as claims_mod
from proofpack.narrate.templates import LIBRARY
from proofpack.resources import load_guidance_map, load_json_schema

REQUIRED_KEYS: tuple[str, ...] = (
    "claim_id",
    "template_id",
    "metric_id",
    "operating_point",
    "subgroup",
    "reference",
    "comparator_id",
    "criterion_index",
    "criterion_id",
    "status",
    "relation",
    "value_refs",
    "guidance_ref",
    "free_text",
)
STATUSES: tuple[str, ...] = ("met", "not_met", "not_assessable")
NUMBER_KEYS: frozenset[str] = frozenset(
    {"est", "ci_lo", "ci_hi", "ci_level", "method", "flags", "suppressed", "not_estimable_reason"}
)
CRITERION_TEMPLATES: frozenset[str] = frozenset(
    {"CRITERION_STATUS", "CRITERION_NOT_MET_RECORD", "ATTAINABILITY_NOTE"}
)
DIFFERENCE_TEMPLATES: frozenset[str] = frozenset({"SUBGROUP_ESTIMATE_WITH_DIFF", "FAIRNESS_GAP"})
DIFFERENCE_BLOCKS: tuple[str, ...] = ("diff_vs_reference", "diff_vs_complement")

#: Pointers that resolve to a bare number the renderer may print (counts and declared
#: values; D4 section 1.2: counts are the only bare integers). Anything else numeric that
#: is not a Number object is refused (``value_ref_not_a_number``).
DOCUMENTED_SCALARS: tuple[str, ...] = (
    r"^/criteria_results/\d+/(value|compared_value|n|max_lower_bound_at_n)$",
    r"^/flow/(rows_read|dev_rows|excluded_missing_label|excluded_missing_score|indeterminate"
    r"|analysed|n_cases|n_sites)$",
    r"^/ledger/(acceptance_runs|warn_limit)$",
    r"^/manifest/(ledger_count|seed|B|duration_s)$",
    r"^/subgroups/\d+/(n|events|n_units|event_units)$",
    r"^/calibration/(n|events|nonevents|n_cases|n_clipped)$",
    r"^/overall/[^/]+/two_by_two/(tp|fn|fp|tn)$",
    r"^/fairness/gaps/\d+/n$",
    r"^/fairness/bound$",
)
_SCALAR_RES = tuple(re.compile(p) for p in DOCUMENTED_SCALARS)

#: D1 section 4.4's verdict words, D4 section 1.2's forbidden list and the inflections
#: the day-5 grep learnt; matched as whole words after lower-casing.
VERDICT_WORDS: frozenset[str] = frozenset(
    {
        "pass",
        "passes",
        "passed",
        "passing",
        "fail",
        "fails",
        "failed",
        "failing",
        "verdict",
        "verdicts",
        "unbiased",
        "biased",
        "calibrated",
        "miscalibrated",
        "consistent",
        "inconsistent",
        "meets",
        "met",
        "unmet",
        "acceptable",
        "unacceptable",
        "safe",
        "unresolvable",
        "non-inferior",
        "noninferior",
        "compliant",
        "noncompliant",
        "satisfactory",
        "satisfied",
        "successful",
        "adequate",
        "inadequate",
        "significant",
        "insignificant",
        "good",
        "poor",
        "fair",
        "unfair",
        "effective",
        "ok",
    }
)
#: No claim of certification, approval or endorsement, anywhere, ever (CLAUDE.md).
CERTIFICATION_WORDS: frozenset[str] = frozenset(
    {
        "certified",
        "certification",
        "approved",
        "approval",
        "endorsed",
        "endorsement",
        "cleared",
        "clearance",
    }
)
#: Reason codes, closed. ``check`` never emits a code outside this dictionary.
REASON_CODES: dict[str, str] = {
    "not_an_object": "the claim is not a JSON object",
    "missing_key": "a required key is absent",
    "unknown_key": "a key outside the claims schema is present",
    "claim_id_invalid": "claim_id is not CL- followed by four or more digits",
    "value_refs_invalid": "value_refs is not a list of strings",
    "template_unknown": "template_id is not in the library",
    "relation_unknown": "relation is not in its enum",
    "status_not_in_enum": "status is not null, met, not_met or not_assessable (case-sensitive)",
    "comparator_unknown": "comparator_id is not in its enum",
    "metric_unknown": "metric_id is not a metric id of D1 section 4.3",
    "value_refs_count": "the number of value_refs is outside the template's range",
    "value_ref_unresolved": "a value_ref does not resolve in the document",
    "value_ref_not_a_number": "a value_ref resolves to neither a Number nor a documented scalar",
    "value_ref_suppressed": "a value_ref resolves to a suppressed Number",
    "relation_mismatch": "relation differs from the engine's recomputation from the bound Numbers",
    "subgroup_not_in_document": "subgroup names no row of document.subgroups",
    "reference_not_in_document": "reference names no row of document.subgroups",
    "subgroup_mismatch": (
        "a value_ref under /subgroups points at a row other than the claimed subgroup"
    ),
    "reference_mismatch": "reference is not the attribute's declared reference level",
    "comparator_mismatch": "comparator_id does not match the row the claim reads",
    "criterion_index_missing": "a criterion is addressed by id without a position",
    "criterion_index_invalid": "criterion_index is not a position in criteria_results",
    "criterion_id_mismatch": "criterion_id differs from the row's at criterion_index",
    "status_mismatch": "status differs from criteria_results[criterion_index].status",
    "status_recomputation_mismatch": (
        "the row's statistic, comparator and value on the bound Number give another status"
    ),
    "status_on_non_criterion": "a status is carried by a claim that is not a criterion claim",
    "guidance_ref_unknown": "guidance_ref is not an internal_id of guidance_map_v1.csv",
    "guidance_draft_unqualified": "a draft guidance row lacks the not-for-implementation qualifier",
    "free_text_digit": "free_text contains a digit",
    "free_text_percent": "free_text contains a per-cent or per-mille sign",
    "free_text_verdict_word": "free_text contains a verdict word",
    "free_text_section_sign": "free_text contains a section sign",
    "free_text_cfr": "free_text contains CFR",
    "free_text_guidance": "free_text contains the word guidance outside guidance_ref",
    "free_text_certification_word": (
        "free_text claims certification, approval, endorsement or clearance"
    ),
    "no_claims_for_criteria": "the claims list is empty on a document that carries criteria rows",
}


@dataclass(frozen=True)
class Verdict:
    claim_id: str | None
    accepted: bool
    reason_code: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def as_rejection(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "reason_code": self.reason_code,
            "detail": dict(self.detail),
        }


@dataclass(frozen=True)
class CheckResult:
    verdicts: list[Verdict]

    @property
    def accepted(self) -> list[Verdict]:
        return [v for v in self.verdicts if v.accepted]

    @property
    def rejected(self) -> list[Verdict]:
        return [v for v in self.verdicts if not v.accepted]

    def rejections(self) -> list[dict[str, Any]]:
        return [v.as_rejection() for v in self.rejected]


def resolve_pointer(doc: Any, ref: str) -> tuple[bool, Any]:
    """RFC 6901 resolution: ``(found, value)``; never raises."""
    if not isinstance(ref, str) or not ref.startswith("/"):
        return False, None
    node = doc
    for raw in ref[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            if token not in node:
                return False, None
            node = node[token]
        elif isinstance(node, list):
            if not re.fullmatch(r"0|[1-9]\d*", token) or int(token) >= len(node):
                return False, None
            node = node[int(token)]
        else:
            return False, None
    return True, node


def is_number_object(value: Any) -> bool:
    return isinstance(value, dict) and NUMBER_KEYS <= set(value)


def is_documented_scalar(ref: str, value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and any(r.match(ref) for r in _SCALAR_RES)
    )


def _words(text: str) -> set[str]:
    return set(re.split(r"[^a-z\-]+", text.lower())) - {""}


def free_text_reason(text: str) -> str | None:
    """The first forbidden-token rule ``text`` breaks, or ``None``."""
    norm = unicodedata.normalize("NFKC", text)
    for ch in text + norm:  # the raw text too: NFKC turns a Roman numeral into letters
        if ch.isnumeric() or unicodedata.category(ch) in ("Nd", "Nl", "No"):
            return "free_text_digit"
    if "%" in norm or "‰" in norm or "‱" in norm:
        return "free_text_percent"
    if "§" in norm:
        return "free_text_section_sign"
    words = _words(norm)
    if words & VERDICT_WORDS or "well-calibrated" in norm.lower():
        return "free_text_verdict_word"
    if "cfr" in words:
        return "free_text_cfr"
    if "guidance" in words:
        return "free_text_guidance"
    if words & CERTIFICATION_WORDS or any(w.startswith("fda-") for w in words):
        return "free_text_certification_word"
    return None


def _guidance_rows(guidance_map: Any) -> dict[str, dict[str, str]]:
    rows = load_guidance_map() if guidance_map is None else guidance_map
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("internal_id"):
            out[str(row["internal_id"])] = {str(k): str(v) for k, v in row.items()}
    return out


def draft_row_unqualified(row: dict[str, str]) -> bool:
    status = str(row.get("status", "")).strip().lower()
    return status.startswith("draft") and "not for implementation" not in status


def _compare(statistic_value: float, comparator: str, value: float) -> bool | None:
    if comparator == ">=":
        return statistic_value >= value
    if comparator == ">":
        return statistic_value > value
    if comparator == "<=":
        return statistic_value <= value
    if comparator == "<":
        return statistic_value < value
    return None


def _statistic_of(number: dict[str, Any], statistic: Any) -> Any:
    key = {"ci_lower_bound": "ci_lo", "ci_upper_bound": "ci_hi", "point_estimate": "est"}.get(
        statistic
    )
    return None if key is None else number.get(key)


def _subgroup_index(doc: dict[str, Any], sub: Any) -> int | None:
    if not isinstance(sub, dict):
        return None
    for i, row in enumerate(doc.get("subgroups") or []):
        if not isinstance(row, dict):
            continue
        if str(row.get("attribute")) == str(sub.get("attribute")) and str(row.get("level")) == str(
            sub.get("level")
        ):
            return i
    return None


def _check_one(
    claim: Any,
    doc: dict[str, Any],
    library: dict[str, Any],
    guidance: dict[str, dict[str, str]],
    metric_ids: frozenset[str],
) -> Verdict:
    cid = claim.get("claim_id") if isinstance(claim, dict) else None
    cid = cid if isinstance(cid, str) else None

    def reject(code: str, **detail: Any) -> Verdict:
        assert code in REASON_CODES
        return Verdict(cid, False, code, detail)

    # 1. structure
    if not isinstance(claim, dict):
        return reject("not_an_object")
    missing = [k for k in REQUIRED_KEYS if k not in claim]
    if missing:
        return reject("missing_key", keys=missing)
    extra = [k for k in claim if k not in REQUIRED_KEYS]
    if extra:
        return reject("unknown_key", keys=extra)
    if not isinstance(cid, str) or not re.fullmatch(r"CL-\d{4,}", cid):
        return reject("claim_id_invalid")
    refs = claim["value_refs"]
    if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
        return reject("value_refs_invalid")
    # 2. enums
    template_id = claim["template_id"]
    if not isinstance(template_id, str) or template_id not in library:
        return reject("template_unknown", template_id=template_id)
    template = library[template_id]
    if claim["relation"] not in claims_mod.RELATIONS:
        return reject("relation_unknown", relation=claim["relation"])
    status = claim["status"]
    if status is not None and status not in STATUSES:
        return reject("status_not_in_enum", status=status)
    comparator_id = claim["comparator_id"]
    if comparator_id is not None and comparator_id not in claims_mod.COMPARATOR_IDS:
        return reject("comparator_unknown", comparator_id=comparator_id)
    metric_id = claim["metric_id"]
    if metric_id is not None and metric_id not in metric_ids:
        return reject("metric_unknown", metric_id=metric_id)
    # 3. value_refs
    lo, hi = template.refs
    if not (lo <= len(refs) <= hi):
        return reject("value_refs_count", count=len(refs), expected=[lo, hi])
    numbers: list[tuple[str, dict[str, Any]]] = []
    for ref in refs:
        found, value = resolve_pointer(doc, ref)
        if not found or value is None:
            return reject("value_ref_unresolved", value_ref=ref)
        if is_number_object(value):
            if value.get("suppressed"):
                return reject("value_ref_suppressed", value_ref=ref)
            numbers.append((ref, value))
        elif not is_documented_scalar(ref, value):
            return reject("value_ref_not_a_number", value_ref=ref)
    # 4. relation
    if template_id in DIFFERENCE_TEMPLATES:
        diff_numbers = [n for r, n in numbers if any(f"/{b}/" in r for b in DIFFERENCE_BLOCKS)]
        if template_id == "FAIRNESS_GAP":
            diff_numbers = [n for r, n in numbers if "/tpr_gap/" in r] or [
                n for _, n in numbers[:1]
            ]
        expected = claims_mod.relation_of(
            diff_numbers[0] if diff_numbers else None, difference=True
        )
    elif template_id in CRITERION_TEMPLATES:
        expected = "estimate" if status in ("met", "not_met") else "not_assessable"
    elif numbers:
        expected = claims_mod.relation_of(numbers[0][1])
    else:
        expected = (
            claim["relation"] if claim["relation"] in ("estimate", "not_assessable") else None
        )
    if claim["relation"] != expected:
        return reject("relation_mismatch", stated=claim["relation"], recomputed=expected)
    # 5. subgroup and reference
    sub = claim["subgroup"]
    if sub is not None:
        if template_id == "FAIRNESS_GAP":
            fairness = doc.get("fairness") or {}
            levels = {
                str(g.get("level")) for g in fairness.get("gaps") or [] if isinstance(g, dict)
            }
            if (
                not isinstance(sub, dict)
                or str(fairness.get("attribute")) != str(sub.get("attribute"))
                or str(sub.get("level")) not in levels
            ):
                return reject("subgroup_not_in_document", subgroup=sub)
            gap_idx = [
                j
                for j, g in enumerate(fairness.get("gaps") or [])
                if isinstance(g, dict) and str(g.get("level")) == str(sub.get("level"))
            ]
            for ref, _ in numbers:
                m = re.match(r"^/fairness/gaps/(\d+)/", ref)
                if m and int(m.group(1)) not in gap_idx:
                    return reject("subgroup_mismatch", value_ref=ref, subgroup=sub)
            ref_level = fairness.get("reference_level")
        else:
            idx = _subgroup_index(doc, sub)
            if idx is None:
                return reject("subgroup_not_in_document", subgroup=sub)
            for ref, _ in numbers:
                m = re.match(r"^/subgroups/(\d+)/", ref)
                if m and int(m.group(1)) != idx:
                    return reject("subgroup_mismatch", value_ref=ref, subgroup=sub, row=idx)
            ref_level = claims_mod._reference_levels(doc).get(str(sub.get("attribute")))
        reference = claim["reference"]
        if reference is not None:
            if not isinstance(reference, dict) or _subgroup_index(doc, reference) is None:
                return reject("reference_not_in_document", reference=reference)
            if str(reference.get("attribute")) != str(sub.get("attribute")) or (
                ref_level is None or str(reference.get("level")) != str(ref_level)
            ):
                return reject("reference_mismatch", reference=reference, declared=ref_level)
            if str(reference.get("level")) == str(sub.get("level")):
                return reject("reference_mismatch", reference=reference, declared=ref_level)
    elif claim["reference"] is not None:
        return reject("reference_not_in_document", reference=claim["reference"])
    # 6. comparator_id on a difference claim
    if template_id in DIFFERENCE_TEMPLATES:
        blocks = {b for r, _ in numbers for b in DIFFERENCE_BLOCKS if f"/{b}/" in r}
        if template_id == "FAIRNESS_GAP":
            blocks = {"diff_vs_reference"}
        if comparator_id not in blocks or len(blocks) != 1:
            return reject("comparator_mismatch", comparator_id=comparator_id, blocks=sorted(blocks))
    # 7. criteria by position
    if template_id in CRITERION_TEMPLATES:
        index = claim["criterion_index"]
        rows = doc.get("criteria_results") or []
        if index is None:
            return reject("criterion_index_missing", criterion_id=claim["criterion_id"])
        if isinstance(index, bool) or not isinstance(index, int) or not (0 <= index < len(rows)):
            return reject("criterion_index_invalid", criterion_index=index)
        row = rows[index]
        if not isinstance(row, dict):
            return reject("criterion_index_invalid", criterion_index=index)
        if claim["criterion_id"] != row.get("criterion_id"):
            return reject(
                "criterion_id_mismatch", claimed=claim["criterion_id"], row=row.get("criterion_id")
            )
        if status != row.get("status"):
            return reject("status_mismatch", claimed=status, row=row.get("status"))
        if comparator_id != row.get("comparator"):
            return reject(
                "comparator_mismatch", comparator_id=comparator_id, row=row.get("comparator")
            )
        if status in ("met", "not_met"):
            if not numbers:
                return reject("status_recomputation_mismatch", reason="no Number bound")
            stat = _statistic_of(numbers[0][1], row.get("statistic"))
            value = row.get("value")
            if not isinstance(stat, (int, float)) or not isinstance(value, (int, float)):
                return reject(
                    "status_recomputation_mismatch", reason="statistic or value not numeric"
                )
            met = _compare(float(stat), str(row.get("comparator")), float(value))
            if met is None or ("met" if met else "not_met") != status:
                return reject("status_recomputation_mismatch", claimed=status, recomputed=met)
    elif status is not None:
        return reject("status_on_non_criterion", status=status)
    elif claim["criterion_index"] is not None or claim["criterion_id"] is not None:
        return reject("status_on_non_criterion", criterion_index=claim["criterion_index"])
    # 8. guidance_ref
    gref = claim["guidance_ref"]
    if gref is not None:
        if not isinstance(gref, str) or gref not in guidance:
            return reject("guidance_ref_unknown", guidance_ref=gref)
        if draft_row_unqualified(guidance[gref]):
            return reject(
                "guidance_draft_unqualified", guidance_ref=gref, status=guidance[gref].get("status")
            )
    # 9. free_text
    text = claim["free_text"]
    if text is not None:
        if not isinstance(text, str):
            return reject("free_text_digit", reason="free_text is not a string")
        code = free_text_reason(text)
        if code is not None:
            return reject(code)
    return Verdict(cid, True)


def check(
    claims: Any,
    document: Any,
    library: dict[str, Any] | None = None,
    guidance_map: Any = None,
) -> CheckResult:
    """One :class:`Verdict` per claim, plus the document-level verdict when the list is
    empty on a document with criteria rows. Pure; never raises on malformed input."""
    lib = LIBRARY if library is None else library
    guidance = _guidance_rows(guidance_map)
    doc = document if isinstance(document, dict) else {}
    try:
        metric_ids = frozenset(
            load_json_schema("output_schema_v1.json")["$defs"]["metricId"]["enum"]
        ) | {"calibration_by_group"}
    except (KeyError, OSError, ValueError):  # pragma: no cover - the packaged schema is fixed
        metric_ids = frozenset()
    verdicts: list[Verdict] = []
    if not isinstance(claims, list):
        return CheckResult(
            [Verdict(None, False, "not_an_object", {"claims": type(claims).__name__})]
        )
    if not claims and doc.get("criteria_results"):
        return CheckResult([Verdict(None, False, "no_claims_for_criteria", {})])
    for claim in claims:
        verdicts.append(_check_one(claim, doc, lib, guidance, metric_ids))
    return CheckResult(verdicts)


def resolve(
    document: dict[str, Any],
    claims: list[dict[str, Any]] | None = None,
    *,
    guidance_map: Any = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The claims a document carries and the rejections T8 prints.

    ``claims`` defaults to the engine's own :func:`~proofpack.narrate.claims.build_claims`.
    Every claim is checked; a rejected one is replaced by the deterministic template claim
    for its slot (the engine's claim with the same template, metric, operating point,
    subgroup and criterion position) when that substitute is itself accepted, and dropped
    otherwise; each rejection is recorded as ``{claim_id, reason_code, template_id,
    substituted, detail}``.
    """
    engine = claims_mod.build_claims(document)
    by_slot = {claims_mod.slot_key(c): c for c in engine}
    incoming = engine if claims is None else claims
    result = check(incoming, document, guidance_map=guidance_map)
    final: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    if result.verdicts and result.verdicts[0].claim_id is None and not result.verdicts[0].accepted:
        v = result.verdicts[0]
        rejections.append({**v.as_rejection(), "template_id": None, "substituted": False})
        return final, rejections
    for claim, verdict in zip(incoming, result.verdicts, strict=True):
        if verdict.accepted:
            final.append(claim)
            continue
        substitute = by_slot.get(claims_mod.slot_key(claim)) if isinstance(claim, dict) else None
        substituted = False
        if substitute is not None and substitute is not claim:
            again = check([substitute], document, guidance_map=guidance_map)
            if again.verdicts and again.verdicts[0].accepted:
                final.append(substitute)
                substituted = True
        rejections.append(
            {
                **verdict.as_rejection(),
                "template_id": claim.get("template_id") if isinstance(claim, dict) else None,
                "substituted": substituted,
            }
        )
    return final, rejections
