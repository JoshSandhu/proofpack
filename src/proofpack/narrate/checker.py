"""The claim-binding checker (D1 section 4.4; build day 8, E8; repair 1, 23 September).

:func:`check` reads the claims, the document, the template library and the guidance map
and returns one verdict per claim. A malformed *claim* is a typed rejection, not an
exception: ``tests/test_claims.py::test_the_checker_never_raises_on_garbage`` feeds nine
literal non-claims, and ``tests/test_e8_repair1.py::
test_two_malformed_documents_are_rejected_not_raised`` feeds two malformed documents (a
``fairness`` block that is the string ``x`` under a ``FAIRNESS_GAP`` claim bound to four
``/flow/`` counts; an ``overall.op1.sensitivity`` whose ``ci_lo`` is the string ``0.1``).
No other input is claimed. The rules, applied in this order and stopping at the first
that fails:

1. the claim is an object with exactly the keys of ``schema/claims_schema.json``
   (``not_an_object`` / ``missing_key`` / ``unknown_key``), ``claim_id`` matches
   ``CL-`` + digits, ``value_refs`` is a list of strings (``claim_id_invalid``,
   ``value_refs_invalid``);
2. ``template_id`` is in the library (``template_unknown``); ``relation`` is in its
   enum (``relation_unknown``); ``status`` is ``null`` or exactly one of ``met`` /
   ``not_met`` / ``not_assessable`` - case-sensitive, so ``Met`` is
   ``status_not_in_enum``; ``comparator_id`` is in its enum (``comparator_unknown``);
   ``metric_id`` is null, in D1 section 4.3's enum, or ``calibration_by_group`` (the
   fairness criterion of interest the criteria engine emits, E7) (``metric_unknown``);
3. the number of ``value_refs`` is within the template's range (``value_refs_count``);
   no pointer appears twice (``value_ref_duplicate``); every ``value_ref`` is an RFC
   6901 pointer that resolves in the document (``value_ref_unresolved``) to a Number
   object (the eight required keys of D1 section 4.1, with ``est``, ``ci_lo`` and
   ``ci_hi`` each a number or null) or to one of the documented scalars in
   :data:`DOCUMENTED_SCALARS` (``value_ref_not_a_number``); a resolved Number that is
   suppressed is refused whatever the relation (``value_ref_suppressed``);
4. **binding** (repair 1, lens FA-B1; repair 2, lens FA-B2): every Number pointer is
   read for the metric, operating point, row and difference block its path names,
   through the eight pointer shapes in :data:`POINTER_SHAPES`; a Number at any other
   path (a day-4 cell's ``analytic``, a decile-curve ``observed``, a ``diff_vs_*``
   ``auroc``) is refused (``value_ref_unbound``), as is a Number under a template
   outside :data:`BOUND_TEMPLATES` (the compare, period and flow templates bind no
   Number in v1), a documented scalar under an estimate template
   (:data:`ESTIMATE_TEMPLATES`: ``/flow/analysed`` is not an estimate), a difference
   block read off :data:`DIFFERENCE_TEMPLATES`, and a ``SUBGROUP_ESTIMATE_WITH_DIFF``
   whose first pointer is not the ``metrics`` cell or whose second is not a
   ``diff_vs_*`` cell (the ``{est}`` slot would print the difference). A claim that
   binds a Number names a ``metric_id`` (``metric_mismatch`` on null) and binds Numbers
   of that metric only, or of the template's family (:data:`METRIC_FAMILIES`: the
   calibration cells under ``CALIB_HIERARCHY``, the gap cells under ``FAIRNESS_GAP``)
   (``metric_mismatch``); every pointer's operating point equals the claim's - null
   equals null (the literal fed: the engine's ``AUROC_ESTIMATE`` claim ``CL-0014``, bound
   to ``/overall/threshold_free/auroc``, given ``operating_point`` ``op1``); ``FAIRNESS_GAP``'s
   ``auroc_gap`` pointer is the one exemption - and a claim's ``operating_point`` is a
   key of ``document.overall`` (``operating_point_mismatch``); a template in
   :data:`OVERALL_TEMPLATES` carries no ``subgroup`` and one in
   :data:`SUBGROUP_TEMPLATES` carries one (``template_scope_mismatch``). Inspected by
   ``tests/test_e8_repair2.py::test_every_value_ref_swap_to_every_number_path_is_rejected``
   (every ``value_ref`` of the synthetic document's 70 engine claims swapped to each of
   its 418 Number paths) and ``::test_the_lens_b2_literal_claims_are_rejected_with_the_
   named_code``;
5. ``relation`` equals the engine's recomputation from the bound Numbers
   (:func:`proofpack.narrate.claims.relation_of`): a Number carrying a typed reason
   presented as an estimate, or a difference whose sign the claim states wrongly, is
   ``relation_mismatch``; a claim that binds no Number (counts only, or nothing) can
   state ``not_assessable`` and nothing else;
6. ``subgroup`` and ``reference`` name rows of ``document.subgroups``
   (``subgroup_not_in_document`` / ``reference_not_in_document``); each Number
   pointer's facets (rule 4 refused any pointer without them) are inspected: on a claim
   with a ``subgroup`` the scope is ``subgroup`` at the row's index or ``gap`` at a gap
   whose level is the claim's, on a claim without one the scope is ``overall``
   (``subgroup_mismatch``); ``reference`` is the attribute's declared reference level
   (``reference_mismatch``: the reference swapped), is present on a claim reading a
   ``diff_vs_reference`` block or the gaps of a fairness block that declares a
   reference level, and is null on every other claim (repair 2, lens FA-B2:
   ``reference: null`` on the engine's ``SUBGROUP_ESTIMATE_WITH_DIFF`` claim, and
   ``diff_vs_complement`` with ``reference`` still naming ``sex = M``, were accepted);
7. ``comparator_id`` matches the row: on a difference claim it is the difference block
   the second pointer reads; on a criterion claim it is the row's comparator; on any
   other claim it is null (``comparator_mismatch``);
8. a criterion claim addresses its row **by position**: ``criterion_index`` is an integer
   in range (``criterion_index_missing`` when an id is named and no index -
   two rows may share an id; ``criterion_index_invalid``); ``criterion_id`` equals the
   row's (``criterion_id_mismatch``); the claim's ``metric_id``, ``operating_point``,
   ``subgroup`` (the row's ``scope``) and ``value_refs`` (the row's ``metric_ref`` as a
   pointer through :func:`proofpack.narrate.claims.metric_ref_pointers`, or none) equal
   the row's (``criterion_row_mismatch``); ``status`` equals the row's
   (``status_mismatch``); and, on a ``met`` / ``not_met`` row, comparing the bound
   Number's named statistic with the row's comparator and value gives the same status
   (``status_recomputation_mismatch``); ``CRITERION_NOT_MET_RECORD`` addresses a
   ``not_met`` row and ``ATTAINABILITY_NOTE`` a row whose ``attainable_at_n`` is ``true``
   or ``false`` (``template_mismatch``, repair 3). A claim under any other template
   carries no status (``status_on_non_criterion``);
8b. (repair 3, lenses RG-B2 and FA-B1 at ``7fa690b``) the template against its pointers
   and the document: an estimate template's pointers match the shapes
   :data:`TEMPLATE_SHAPES` gives it (``value_ref_unbound``); ``AUROC_ESTIMATE`` carries
   ``metric_id`` ``auroc`` (``metric_mismatch``); ``CALIB_HIERARCHY``'s and
   ``FAIRNESS_GAP``'s pointers name distinct slots of :data:`SLOT_ORDER` in that order,
   and a documented scalar outside a criterion template is one of the template's
   :data:`SCALAR_SLOTS`, distinct and in that order (``value_ref_unbound``); a template
   of :data:`SCALAR_SLOTS` carries no metric, operating point, subgroup or reference
   (``template_scope_mismatch``); ``CALIB_NA`` sits on a document whose ``calibration``
   is not an object and whose ``calibration_suppressed_reason.reason`` is
   ``score_not_probability`` (``template_mismatch``; the reason since repair 4, lens-4
   FA-B3: ``tests/test_e8_repair4.py`` feeds a ``y_pred``-only document). The literals fed are in
   ``tests/test_e8_repair3.py::test_the_round_3_template_relabels_are_rejected_with_the_named_code``
   and corpus files ``131``-``140``. The rule inspects the order of the pointers, not
   which slot each fills: that is the sentence renderer's (E9), and a subset of a
   family's pointers leaves the other slots without a pointer;
9. ``guidance_ref`` is null or an ``internal_id`` of the guidance map
   (``guidance_ref_unknown``); a draft row - status beginning ``draft`` - must carry the
   qualifier ``not for implementation`` in its status (``guidance_draft_unqualified``);
10. ``free_text``, when not null, contains no digit in any script (Unicode ``Nd``, ``Nl``
    and ``No``, so the Arabic-Indic digits and a superscript two are digits; the text is
    NFKC-normalised first, so a fullwidth per-cent sign is ``%``): ``free_text_digit``;
    no ``%`` or per-mille sign (``free_text_percent``); no section sign
    (``free_text_section_sign``). For the word rules the text is read five ways
    (:func:`_readings`), each through :func:`normalise_free_text` - NFKC, case fold
    (``ß`` to ``ss``, ``ſ`` to ``s``), NFD, drop combining marks (``Mn``) and format
    characters (``Cf``: zero-width joiner and non-joiner, soft hyphen), map the letters
    of a confusable map to the Latin letter each resembles, and turn U+2010-U+2015 into
    ``-``; the words of all five readings are pooled - and a word is matched as
    the whole hyphenated token, as each hyphen-separated part, as the token with its
    hyphens removed, and as every run of two to fourteen consecutive tokens joined; a
    reading that contains ``wellcalibrated`` once its hyphens are removed is
    ``free_text_verdict_word`` whatever letters touch it (repair 3, lens RG-B1:
    ``well-calibratedness``, ``well-calibratedly``, ``well-calibrateds``; and
    ``passᴀ``, rejected at ``657ef11`` and accepted at ``7fa690b``; lens FA-B2's nine
    literals ``pɑss``, ``unbiɑsed``, ``faiI``, ``ƒail``, ``faiǀ``, ``gօօd``,
    ``ϲonsistent``, ``Ꮲass``, ``rneets``: ``tests/test_e8_repair3.py`` feeds each;
    spellings built from other letters are an open class, needs-from-Josh in the
    repair-3 note)
    (:func:`_words`; repair 2, lenses FA-B4 and RG-B2: ``p a s s``, ``p.a.s.s``,
    ``pa-ss``, ``fa-il``, ``unaccept-able``, ``well-cali-brated``, ``pa\\x01ss``,
    ``pa\\x1fss``, ``pa\\x7fss``, ``pa\\x85ss``, ``pa\\x00ss`` and the small capitals
    ``ᴘᴀss`` were accepted at ``657ef11``; ``tests/test_e8_repair2.py::
    test_free_text_separated_control_and_small_capital_spellings_are_rejected`` feeds
    each; accepted there and recorded, not defended: ``p@ss`` - the ``@`` splits ``p``
    from ``ss`` and no run of tokens joins to a listed word - and the unlisted words
    ``ninety``, ``guidances``, ``unsafe``, ``FDAcleared``, needs-from-Josh 2 of the
    repair-1 note), so the corpus files ``104``-``115``, ``129``, ``130``, ``139`` and ``140``
    (``pаss``, ``pa‍ss``, ``pa‌ss``,
    ``pa­ss``, ``un-biased``, ``pass-``, ``-pass``, ``verdict-like``, ``fail-safe``,
    ``méets``, ``paß``, ``non‑inferior``) are each rejected: none of
    :data:`VERDICT_WORDS` (``free_text_verdict_word``); not ``CFR`` (``free_text_cfr``);
    not ``guidance`` (``free_text_guidance``); none of :data:`CERTIFICATION_WORDS`
    (``free_text_certification_word``).

At document level, an empty claims list on a document that carries criteria rows is one
rejection with ``claim_id`` null (``no_claims_for_criteria``): a T8 that printed no
criterion sentence beside a criteria table would be silent where D4 section 11 item 7
requires a count. A ``claim_id`` carried by more than one claim rejects every claim
carrying it (``claim_id_duplicate``).

On rejection the block is replaced by the deterministic template claim for its slot
(:func:`resolve`) and the rejection is recorded in the document's ``claim_rejections``
list, which T8 section 7 prints.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, replace
from typing import Any

from proofpack.narrate import claims as claims_mod
from proofpack.narrate import tr39_confusables as tr39_mod
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
#: ``PAIRED_DIFF`` (build day 10, E10) reads the version comparison's difference cells
#: (``diff_vs_prior``, the ninth to twelfth pointer shapes).
DIFFERENCE_TEMPLATES: frozenset[str] = frozenset(
    {"SUBGROUP_ESTIMATE_WITH_DIFF", "FAIRNESS_GAP", "PAIRED_DIFF"}
)
DIFFERENCE_BLOCKS: tuple[str, ...] = ("diff_vs_reference", "diff_vs_complement")
#: The block name the comparison shapes carry; a criterion template may read it too (a
#: ``paired_difference_vs_prior`` criterion's Number is a difference against the prior).
PRIOR_BLOCK = "diff_vs_prior"

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
    # build day 10 (E10): the version comparison's counts and p-values
    r"^/comparison/(n_pairs|n_new|n_prior)$",
    r"^/comparison/mcnemar/[^/]+/(b|c|n_discordant|p|statistic)$",
    r"^/comparison/ledger/(prior_acceptance_runs|warn_limit)$",
    r"^/comparison/subgroups/\d+/n_pairs$",
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
#: Letters of other scripts shaped like a Latin letter, mapped before the word split
#: (repair 1, lens FA-B2: ``pаss`` with a Cyrillic ``а``). Upper-case forms
#: reach this map through the case fold that precedes it. These 27 are the map as it
#: stood at ``657ef11``; :data:`CONFUSABLES` is the union of the three maps.
_CONFUSABLES_R1: dict[str, str] = {
    "а": "a",  # Cyrillic a
    "е": "e",  # Cyrillic ie
    "о": "o",  # Cyrillic o
    "р": "p",  # Cyrillic er
    "с": "c",  # Cyrillic es
    "у": "y",  # Cyrillic u
    "х": "x",  # Cyrillic ha
    "і": "i",  # Cyrillic byelorussian-ukrainian i
    "ј": "j",  # Cyrillic je
    "ѕ": "s",  # Cyrillic dze
    "ԁ": "d",  # Cyrillic komi de
    "һ": "h",  # Cyrillic shha
    "ԛ": "q",  # Cyrillic qa
    "ԝ": "w",  # Cyrillic we
    "ӏ": "l",  # Cyrillic palochka
    "α": "a",  # Greek alpha
    "ε": "e",  # Greek epsilon
    "ι": "i",  # Greek iota
    "κ": "k",  # Greek kappa
    "ν": "v",  # Greek nu
    "ο": "o",  # Greek omicron
    "ρ": "p",  # Greek rho
    "τ": "t",  # Greek tau
    "υ": "u",  # Greek upsilon
    "χ": "x",  # Greek chi
    "ɡ": "g",  # Latin script g
    "ı": "i",  # Latin dotless i
}
#: Twenty-four Latin small capitals, one per letter below: repair 2, lens RG-B2 - ``ᴘᴀss``
#: was accepted. Other small capitals are not in this map (lens-4 FA-N3 named U+1D01,
#: U+1D03, U+1D06, U+1D0C, U+1D0E, U+1D10, U+1D15, U+1D19, U+1D1A, U+A7AF and U+0276).
_SMALL_CAPITALS: dict[str, str] = {
    "ᴀ": "a",
    "ʙ": "b",
    "ᴄ": "c",
    "ᴅ": "d",
    "ᴇ": "e",
    "ꜰ": "f",
    "ɢ": "g",
    "ʜ": "h",
    "ɪ": "i",
    "ᴊ": "j",
    "ᴋ": "k",
    "ʟ": "l",
    "ᴍ": "m",
    "ɴ": "n",
    "ᴏ": "o",
    "ᴘ": "p",
    "ʀ": "r",
    "ꜱ": "s",
    "ᴛ": "t",
    "ᴜ": "u",
    "ᴠ": "v",
    "ᴡ": "w",
    "ʏ": "y",
    "ᴢ": "z",
}
#: Repair 3, lens FA-B2 at ``7fa690b``: the letters of the lens's nine literals ``pɑss``,
#: ``unbiɑsed``, ``ƒail``, ``faiǀ``, ``gօօd`` and ``Ꮲass`` (``faiI``, ``rneets`` and
#: ``ϲonsistent`` are read through :data:`_BEFORE_NFKC` and :func:`_readings`). Ɑ
#: (U+2C6D), Ƒ (U+0191) and Օ (U+0555) case-fold to the first, second and fourth key, and
#: ꮲ (U+ABB2, CHEROKEE SMALL LETTER TLV) case-folds to the fifth. Repair 4 vendored TR39
#: 18.0.0 (DEC-60, :mod:`proofpack.narrate.tr39_confusables`), which lists the five keys;
#: this map is kept as it stood, since its reading is one of the pooled readings.
_HOMOGLYPHS_R3: dict[str, str] = {
    "ɑ": "a",  # Latin alpha, U+0251
    "ƒ": "f",  # Latin f with hook, U+0192
    "ǀ": "l",  # Latin letter dental click, U+01C0
    "օ": "o",  # Armenian oh, U+0585
    "Ꮲ": "p",  # Cherokee letter tlv, U+13E2
}
#: Mapped in the raw text, before NFKC: NFKC turns the Greek lunate sigma U+03F2 into
#: U+03C2 (final sigma) and its capital U+03F9 into U+03A3 (capital sigma); the case fold
#: turns each into ``σ``.
_BEFORE_NFKC: dict[str, str] = {"ϲ": "c", "Ϲ": "c"}
CONFUSABLES: dict[str, str] = {**_CONFUSABLES_R1, **_SMALL_CAPITALS, **_HOMOGLYPHS_R3}
_UNICODE_HYPHENS = frozenset("‐‑‒–—―")


@dataclass(frozen=True)
class Facets:
    """What a Number pointer's path names (rule 4): the metric key, the operating point,
    the row kind (``overall``, ``subgroup`` or ``gap``) and its index, and the difference
    block when the path reads one."""

    metric: str | None = None
    operating_point: str | None = None
    scope: str = "overall"
    index: int | None = None
    block: str | None = None
    #: the index of the shape in :data:`POINTER_SHAPES` the path matched (repair 3)
    shape: int | None = None


#: The eight pointer shapes rule 4 reads, as (pattern, facets). Any other path resolving
#: to a Number carries no facets.
POINTER_SHAPES: tuple[tuple[str, Any], ...] = (
    (r"^/overall/threshold_free/([^/]+)$", lambda m: Facets(metric=m[1])),
    (r"^/overall/([^/]+)/([^/]+)$", lambda m: Facets(metric=m[2], operating_point=m[1])),
    (
        r"^/subgroups/(\d+)/metrics/(auroc|brier)/number$",
        lambda m: Facets(metric=m[2], scope="subgroup", index=int(m[1])),
    ),
    (
        r"^/subgroups/(\d+)/metrics/([^/]+)/([^/]+)/number$",
        lambda m: Facets(metric=m[3], operating_point=m[2], scope="subgroup", index=int(m[1])),
    ),
    (
        r"^/subgroups/(\d+)/(diff_vs_reference|diff_vs_complement)/([^/]+)/([^/]+)/number$",
        lambda m: Facets(
            metric=m[4], operating_point=m[3], scope="subgroup", index=int(m[1]), block=m[2]
        ),
    ),
    (r"^/calibration/([^/]+)/number$", lambda m: Facets(metric=m[1])),
    (
        r"^/fairness/gaps/(\d+)/operating_points/([^/]+)/([^/]+)/number$",
        lambda m: Facets(metric=m[3], operating_point=m[2], scope="gap", index=int(m[1])),
    ),
    (
        r"^/fairness/gaps/(\d+)/auroc_gap/number$",
        lambda m: Facets(metric="auroc_gap", scope="gap", index=int(m[1])),
    ),
    # build day 10 (E10): the version comparison's difference cells (shapes 8-11). The
    # subgroup entries are parallel to document.subgroups, so their index is a row index.
    (
        r"^/comparison/differences/(auroc|brier|slope)/number$",
        lambda m: Facets(metric=m[1], block="diff_vs_prior"),
    ),
    (
        r"^/comparison/differences/([^/]+)/([^/]+)/number$",
        lambda m: Facets(metric=m[2], operating_point=m[1], block="diff_vs_prior"),
    ),
    (
        r"^/comparison/subgroups/(\d+)/differences/auroc/number$",
        lambda m: Facets(metric="auroc", scope="subgroup", index=int(m[1]), block="diff_vs_prior"),
    ),
    (
        r"^/comparison/subgroups/(\d+)/differences/([^/]+)/([^/]+)/number$",
        lambda m: Facets(
            metric=m[3],
            operating_point=m[2],
            scope="subgroup",
            index=int(m[1]),
            block="diff_vs_prior",
        ),
    ),
)
_SHAPE_RES = tuple((re.compile(p), f) for p, f in POINTER_SHAPES)
#: Templates whose sentence reports a family of cells beside the claim's ``metric_id``.
METRIC_FAMILIES: dict[str, frozenset[str]] = {
    "CALIB_HIERARCHY": frozenset(claims_mod.CALIBRATION_REFS),
    "FAIRNESS_GAP": frozenset(claims_mod.FAIRNESS_GAP_ORDER),
}
#: Metric ids whose document key differs from the id (``criteria.CALIBRATION_KEYS``;
#: ``tests/test_e8_repair1.py`` asserts the two maps agree).
_DOC_KEY_FOR_METRIC: dict[str, str] = {
    "calibration_slope": "slope",
    "calibration_intercept": "intercept",
}
OVERALL_TEMPLATES: frozenset[str] = frozenset(
    {"OVERALL_ESTIMATE", "AUROC_ESTIMATE", "CALIB_HIERARCHY", "CALIB_NA"}
)
SUBGROUP_TEMPLATES: frozenset[str] = frozenset(
    {"SUBGROUP_ESTIMATE", "SUBGROUP_ESTIMATE_WITH_DIFF", "FAIRNESS_GAP"}
)
#: The templates under which a claim may bind a Number in v1: the seven rule 4 reads and
#: the three criterion templates. Every other template (``PAIRED_DIFF``, ``PSI_RESULT``,
#: ``PERIOD_METRIC_ROW``, ``LEDGER_STATEMENT``, ...) binds no Number until the document
#: block it reads exists and its pointer shape joins :data:`POINTER_SHAPES` (repair 2,
#: lens FA-B2: ``OVERALL_ESTIMATE`` renamed to any of 20 such templates was accepted).
BOUND_TEMPLATES: frozenset[str] = (
    OVERALL_TEMPLATES | SUBGROUP_TEMPLATES | CRITERION_TEMPLATES | {"PAIRED_DIFF"}
)
#: The templates whose every ``value_ref`` is a Number (a count is not an estimate;
#: ``CALIB_NA`` binds nothing).
ESTIMATE_TEMPLATES: frozenset[str] = (OVERALL_TEMPLATES | SUBGROUP_TEMPLATES) - {"CALIB_NA"}
#: Rule 8b (repair 3): the shapes of :data:`POINTER_SHAPES`, by index, each estimate
#: template's pointers may match (``OVERALL_ESTIMATE`` the operating-point cells,
#: ``AUROC_ESTIMATE`` the threshold-free ones, and so on).
TEMPLATE_SHAPES: dict[str, frozenset[int]] = {
    "OVERALL_ESTIMATE": frozenset({1}),
    "AUROC_ESTIMATE": frozenset({0}),
    "SUBGROUP_ESTIMATE": frozenset({2, 3}),
    "SUBGROUP_ESTIMATE_WITH_DIFF": frozenset({3, 4}),
    "CALIB_HIERARCHY": frozenset({5}),
    "FAIRNESS_GAP": frozenset({6, 7}),
    "PAIRED_DIFF": frozenset({8, 9, 10, 11}),
}
#: Rule 8b: the ``metric_id`` a template whose skeleton names its metric may carry.
TEMPLATE_METRICS: dict[str, frozenset[str]] = {"AUROC_ESTIMATE": frozenset({"auroc"})}
#: Rule 8b: the slots of a family template, in skeleton order; its pointers' metrics
#: are distinct and follow this order.
SLOT_ORDER: dict[str, tuple[str, ...]] = {
    "CALIB_HIERARCHY": claims_mod.CALIBRATION_REFS,
    "FAIRNESS_GAP": claims_mod.FAIRNESS_GAP_ORDER,
}
#: Rule 8b: the documented scalars a count template may bind, in skeleton order. A
#: documented scalar under any other template outside :data:`CRITERION_TEMPLATES` is
#: ``value_ref_unbound`` (``LEDGER_STATEMENT`` and ``DUPLICATES_NOTE`` bind none in v1).
SCALAR_SLOTS: dict[str, tuple[str, ...]] = {
    "FLOW_COUNTS": (
        "/flow/rows_read",
        "/flow/excluded_missing_label",
        "/flow/excluded_missing_score",
        "/flow/indeterminate",
        "/flow/analysed",
        "/flow/n_cases",
        "/flow/n_sites",
    ),
    "SITE_COUNT": ("/flow/n_sites",),
    # build day 10 (E10): a slot beginning ``^`` is a pattern (the operating point is in
    # the McNemar path); the rest are exact pointers
    "PAIRED_DIFF": (r"^/comparison/(subgroups/\d+/)?n_pairs$",),
    "MCNEMAR_RESULT": (
        r"^/comparison/mcnemar/[^/]+/b$",
        r"^/comparison/mcnemar/[^/]+/c$",
        r"^/comparison/mcnemar/[^/]+/p$",
    ),
    "LEDGER_STATEMENT": ("/comparison/ledger/prior_acceptance_runs",),
}
#: The count templates that describe the run, not a metric, an operating point or a row
#: (rule 8b's scope check); ``PAIRED_DIFF`` and ``MCNEMAR_RESULT`` bind counts beside a
#: metric and an operating point.
RUN_LEVEL_COUNT_TEMPLATES: frozenset[str] = frozenset(
    {"FLOW_COUNTS", "SITE_COUNT", "LEDGER_STATEMENT"}
)


def _scalar_slot_position(slots: tuple[str, ...], ref: str) -> int:
    for i, slot in enumerate(slots):
        if slot.startswith("^"):
            if re.fullmatch(slot, ref):
                return i
        elif slot == ref:
            return i
    return -1


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
    "metric_unknown": "metric_id is not a metric id of D1 section 4.3 or calibration_by_group",
    "value_refs_count": "the number of value_refs is outside the template's range",
    "value_ref_duplicate": "the same pointer appears twice in value_refs",
    "value_ref_unresolved": "a value_ref does not resolve in the document",
    "value_ref_not_a_number": "a value_ref resolves to neither a Number nor a documented scalar",
    "value_ref_suppressed": "a value_ref resolves to a suppressed Number",
    "value_ref_unbound": (
        "a value_ref rule 4 cannot bind: a Number off the eight pointer shapes, a Number under "
        "a template that binds none, a bare count under an estimate template, a difference "
        "block off a difference template, or the estimate and difference slots swapped"
    ),
    "metric_mismatch": (
        "a value_ref names a metric other than metric_id or the template's family, or a "
        "Number is bound and metric_id is null"
    ),
    "operating_point_mismatch": (
        "a value_ref names another operating point, or operating_point is not in document.overall"
    ),
    "template_scope_mismatch": (
        "an overall template carries a subgroup, or a subgroup template carries none"
    ),
    "relation_mismatch": "relation differs from the engine's recomputation from the bound Numbers",
    "subgroup_not_in_document": "subgroup names no row of document.subgroups",
    "reference_not_in_document": "reference names no row of document.subgroups",
    "subgroup_mismatch": (
        "a value_ref reads a row other than the claimed subgroup, or a subgroup row on a claim "
        "without one"
    ),
    "reference_mismatch": "reference is not the attribute's declared reference level",
    "comparator_mismatch": "comparator_id does not match the row the claim reads",
    "criterion_index_missing": "a criterion is addressed by id without a position",
    "criterion_index_invalid": "criterion_index is not a position in criteria_results",
    "criterion_id_mismatch": "criterion_id differs from the row's at criterion_index",
    "criterion_row_mismatch": (
        "metric_id, operating_point, subgroup or value_refs differ from the row at criterion_index"
    ),
    "claim_id_duplicate": "claim_id is carried by more than one claim in the list",
    "status_mismatch": "status differs from criteria_results[criterion_index].status",
    "status_recomputation_mismatch": (
        "the row's statistic, comparator and value on the bound Number give another status"
    ),
    "status_on_non_criterion": "a status is carried by a claim that is not a criterion claim",
    "template_mismatch": (
        "the template states what the row or document does not carry: CRITERION_NOT_MET_RECORD "
        "on a row whose status is not not_met, ATTAINABILITY_NOTE on a row without "
        "attainable_at_n, CALIB_NA on a document whose calibration block is present or whose "
        "calibration_suppressed_reason is not score_not_probability"
    ),
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


def _number_or_none(value: Any) -> bool:
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool))


def is_number_object(value: Any) -> bool:
    """The eight keys of D1 section 4.1, with ``est``, ``ci_lo`` and ``ci_hi`` each a number
    or null (repair 1, lens RG-N4: a ``ci_lo`` of ``"0.1"`` is not a Number)."""
    return (
        isinstance(value, dict)
        and NUMBER_KEYS <= set(value)
        and all(_number_or_none(value[k]) for k in ("est", "ci_lo", "ci_hi"))
    )


def pointer_facets(ref: str) -> Facets | None:
    """The facets of a Number pointer's path (rule 4), or ``None`` off the eight shapes."""
    for i, (pattern, build) in enumerate(_SHAPE_RES):
        m = pattern.match(ref)
        if m:
            return replace(build(m), shape=i)
    return None


def is_documented_scalar(ref: str, value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and any(r.match(ref) for r in _SCALAR_RES)
    )


def normalise_free_text(text: str, confusables: dict[str, str] = CONFUSABLES) -> str:
    """One reading of the text for the word rules (rule 10): NFKC, case fold, NFD,
    combining marks and format characters dropped, ``confusables`` mapped (by default
    :data:`CONFUSABLES`), U+2010-U+2015 as ``-``."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    out: list[str] = []
    for ch in unicodedata.normalize("NFD", folded):
        if unicodedata.category(ch) in ("Mn", "Cf"):
            continue
        ch = confusables.get(ch, ch)
        out.append("-" if ch in _UNICODE_HYPHENS else ch)
    return "".join(out)


#: The confusable maps of the two earlier readings: ``657ef11``'s 27 letters, and
#: ``7fa690b``'s 27 plus the small capitals. A letter a later map adds stops acting as a
#: word boundary, so ``passᴀ`` - rejected at ``657ef11`` (``ᴀ`` split it from ``pass``) -
#: read ``passa`` at ``7fa690b`` and was accepted (repair 3: found beside lens RG-B1's
#: ``well-calibratedness``). Each earlier reading is kept beside the full one.
_READING_MAPS: tuple[dict[str, str], ...] = (
    _CONFUSABLES_R1,
    {**_CONFUSABLES_R1, **_SMALL_CAPITALS},
)


#: DEC-60 (repair 4): the vendored TR39 18.0.0 entries as a character map for the TR39
#: readings. The two entries whose source is an ASCII letter (``I`` -> ``l`` and ``m`` ->
#: ``rn``) are left out, so ASCII letters read as written in the first TR39 reading:
#: ``meets`` stays ``meets``, and ``faiI`` is read by the readings that take an ASCII
#: capital ``I`` as ``l``. TR39 writes ``m`` as ``rn`` (U+FF4D and U+1D426 map to ``rn``);
#: both TR39 readings read every ``rn`` as ``m``.
_TR39: dict[str, str] = {
    chr(k): v
    for k, v in tr39_mod.CONFUSABLES.items()
    if not ("a" <= chr(k) <= "z" or "A" <= chr(k) <= "Z")
}


def _tr39_mapped(text: str) -> str:
    """``text`` with :data:`_TR39` applied, then NFKC, then :data:`_TR39` again (NFKC can
    produce a character the map lists)."""
    once = "".join(_TR39.get(ch, ch) for ch in text)
    return "".join(_TR39.get(ch, ch) for ch in unicodedata.normalize("NFKC", once))


def _readings(text: str) -> tuple[str, ...]:
    """The normalised readings the word rules read, each a :func:`normalise_free_text`:
    one per map in :data:`_READING_MAPS`; the full map after :data:`_BEFORE_NFKC`; the
    same with every ASCII capital ``I`` read as ``l`` (``faiI``); and the full reading with
    every ``rn`` read as ``m`` (``rneets``) - repair 3, lens FA-B2 at ``7fa690b``. Repair
    4 (DEC-60, lens-4 FA-B4) adds two: the text through :func:`_tr39_mapped` with every
    ``rn`` read as ``m``, and the same with every ASCII capital ``I`` read as ``l`` first.
    No word the rules match contains ``rn``. The literals ``tests/test_e8_repair4.py``
    feeds are named there."""
    early = tuple(normalise_free_text(text, m) for m in _READING_MAPS)
    raw = "".join(_BEFORE_NFKC.get(ch, ch) for ch in text)
    full = normalise_free_text(raw)
    capital_i = normalise_free_text(raw.replace("I", "l"))
    rn = full.replace("rn", "m")
    tr = _tr39_mapped(text)
    tr39 = normalise_free_text(tr).replace("rn", "m")
    tr39_i = normalise_free_text(tr.replace("I", "l")).replace("rn", "m")
    return (*early, full, capital_i, rn, tr39, tr39_i)


_LETTERS_ONLY = re.compile(r"[^a-z]+")

#: The longest run of consecutive tokens :func:`_words` joins. With 13 planted, ``-m day8``
#: gave 224 passed at ``7fa690b`` (the repair-2 note; lens RG-N3).
_JOIN_RUN = 14


def _tokens(text: str) -> list[str]:
    """The maximal runs of the characters ``a``-``z`` and ``-`` in normalised text, in
    order, dropping a run made of hyphens only; every other character ends a run
    (``pɑss`` at ``7fa690b``, before ``ɑ`` was mapped, gave ``p`` and ``ss``)."""
    return [t for t in re.split(r"[^a-z\-]+", text) if t.strip("-")]


def _words(text: str) -> set[str]:
    """From normalised text: each token, its hyphen-separated parts, the token with its
    hyphens removed, and every run of two to :data:`_JOIN_RUN` consecutive tokens joined
    (repair 2, lenses FA-B4 and RG-B2: ``p a s s``, ``pa-ss`` and ``pa\\x01ss`` are the
    tokens ``p a s s`` / ``pa-ss`` / ``pa ss``, and ``pass`` is in the set for each)."""
    tokens = _tokens(text)
    out: set[str] = set()
    for token in tokens:
        out.add(token.strip("-"))
        out.update(token.split("-"))
        out.add(token.replace("-", ""))
    parts = [t.replace("-", "") for t in tokens]
    for i in range(len(parts)):
        joined = parts[i]
        for j in range(i + 1, min(i + _JOIN_RUN, len(parts))):
            joined += parts[j]
            out.add(joined)
    return out - {""}


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
    readings = _readings(text)
    words: set[str] = set()
    for reading in readings:
        words |= _words(reading)
    if words & VERDICT_WORDS or words & {"well-calibrated", "wellcalibrated"}:
        return "free_text_verdict_word"
    # the phrase with letters touching it (657ef11's substring rule; lens RG-B1 at
    # 7fa690b: well-calibratedness, well-calibratedly, well-calibrateds were accepted),
    # read in each reading with every character outside a-z removed (repair 4, lens-4
    # FA-B4 / RG-N2: well calibratedness, well_calibratedness, well.calibratedness were
    # accepted when only hyphens were removed)
    if any("wellcalibrated" in _LETTERS_ONLY.sub("", r) for r in readings):
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
    row_refs: list[str | None] | None = None,
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
    if len(set(refs)) != len(refs):
        return reject("value_ref_duplicate", value_refs=list(refs))
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
    # 4. binding: every Number pointer carries facets or is refused (repair 1, lens
    # FA-B1; repair 2, lens FA-B2: 225 of the synthetic document's 418 Numbers sit off
    # the eight shapes and a claim bound to one was bound by nothing)
    facets: list[tuple[str, Facets]] = []
    for ref, _ in numbers:
        f = pointer_facets(ref)
        if f is None:
            return reject("value_ref_unbound", value_ref=ref, reason="path off the pointer shapes")
        facets.append((ref, f))
    if numbers and template_id not in BOUND_TEMPLATES:
        return reject(
            "value_ref_unbound", template_id=template_id, reason="template binds no Number in v1"
        )
    if template_id in ESTIMATE_TEMPLATES and len(numbers) != len(refs):
        bound = {r for r, _ in numbers}
        return reject(
            "value_ref_unbound",
            value_refs=[r for r in refs if r not in bound],
            reason="a documented scalar under an estimate template",
        )
    if template_id not in DIFFERENCE_TEMPLATES and any(
        f.block and not (f.block == PRIOR_BLOCK and template_id in CRITERION_TEMPLATES)
        for _, f in facets
    ):
        return reject(
            "value_ref_unbound",
            value_refs=[r for r, f in facets if f.block],
            reason="a difference block under a template without a difference clause",
        )
    if template_id == "PAIRED_DIFF" and any(f.block != PRIOR_BLOCK for _, f in facets):
        return reject(
            "value_ref_unbound",
            value_refs=[r for r, f in facets if f.block != PRIOR_BLOCK],
            reason="PAIRED_DIFF reads the version comparison's difference cells only",
        )
    if template_id == "SUBGROUP_ESTIMATE_WITH_DIFF":
        blocks = [f.block for _, f in facets]
        if len(blocks) != 2 or blocks[0] is not None or blocks[1] not in DIFFERENCE_BLOCKS:
            return reject(
                "value_ref_unbound",
                value_refs=list(refs),
                reason="the estimate slot reads a metrics cell and the difference slot a "
                "diff_vs_* cell, in that order",
            )
    op = claim["operating_point"]
    if numbers and metric_id is None:
        return reject("metric_mismatch", metric_id=None, reason="a Number is bound")
    if metric_id is not None:
        doc_key = _DOC_KEY_FOR_METRIC.get(metric_id, metric_id)
        family = METRIC_FAMILIES.get(template_id, frozenset())
        if family and doc_key not in family:
            return reject("metric_mismatch", metric_id=metric_id, family=sorted(family))
        allowed = {doc_key} | family
        for ref, f in facets:
            if f.metric is not None and f.metric not in allowed:
                return reject("metric_mismatch", value_ref=ref, metric_id=metric_id)
    for ref, f in facets:
        if f.operating_point == op:
            continue
        if template_id == "FAIRNESS_GAP" and f.metric == "auroc_gap" and f.operating_point is None:
            continue  # the gap sentence reads the three operating-point gaps and the AUROC gap
        return reject("operating_point_mismatch", value_ref=ref, operating_point=op)
    overall = doc.get("overall")
    if op is not None and isinstance(overall, dict):
        if op == "threshold_free" or op not in overall:
            return reject("operating_point_mismatch", operating_point=op)
    sub = claim["subgroup"]
    if template_id in OVERALL_TEMPLATES and sub is not None:
        return reject("template_scope_mismatch", template_id=template_id, subgroup=sub)
    if template_id in SUBGROUP_TEMPLATES and sub is None:
        return reject("template_scope_mismatch", template_id=template_id, subgroup=None)
    # 5. relation
    if template_id in DIFFERENCE_TEMPLATES:
        diff_numbers = [n for r, n in numbers if any(f"/{b}/" in r for b in DIFFERENCE_BLOCKS)]
        if template_id == "PAIRED_DIFF":
            diff_numbers = [n for _, n in numbers]
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
        expected = "not_assessable"
    if claim["relation"] != expected:
        return reject("relation_mismatch", stated=claim["relation"], recomputed=expected)
    # 6. subgroup and reference
    fairness = doc.get("fairness")
    fairness = fairness if isinstance(fairness, dict) else {}
    gaps = [g if isinstance(g, dict) else {} for g in fairness.get("gaps") or []]
    if sub is not None:
        if not isinstance(sub, dict):
            return reject("subgroup_not_in_document", subgroup=sub)
        gap_idx = [j for j, g in enumerate(gaps) if str(g.get("level")) == str(sub.get("level"))]
        if str(fairness.get("attribute")) != str(sub.get("attribute")):
            gap_idx = []
        if template_id == "FAIRNESS_GAP":
            if not gap_idx:
                return reject("subgroup_not_in_document", subgroup=sub)
            idx = None
            ref_level = fairness.get("reference_level")
        else:
            idx = _subgroup_index(doc, sub)
            if idx is None:
                return reject("subgroup_not_in_document", subgroup=sub)
            ref_level = claims_mod._reference_levels(doc).get(str(sub.get("attribute")))
        for ref, f in facets:
            if f.scope == "subgroup" and f.index == idx:
                continue
            if f.scope == "gap" and f.index in gap_idx:
                continue
            return reject("subgroup_mismatch", value_ref=ref, subgroup=sub, row=idx)
        reference = claim["reference"]
        # the block the claim's difference is against: the gaps are differences against
        # the fairness reference level; a SUBGROUP_ESTIMATE_WITH_DIFF reads the block its
        # second pointer names; every other template reads no difference
        block_read = (
            "diff_vs_reference"
            if template_id == "FAIRNESS_GAP"
            else next((f.block for _, f in facets if f.block is not None), None)
        )
        if reference is None and block_read == "diff_vs_reference" and ref_level is not None:
            return reject(
                "reference_mismatch",
                reference=None,
                declared=ref_level,
                reason="a difference against the reference level names it",
            )
        if reference is not None:
            if block_read != "diff_vs_reference":
                return reject(
                    "reference_mismatch",
                    reference=reference,
                    declared=ref_level,
                    reason="no difference against the reference level is read",
                )
            if not isinstance(reference, dict) or _subgroup_index(doc, reference) is None:
                return reject("reference_not_in_document", reference=reference)
            if str(reference.get("attribute")) != str(sub.get("attribute")) or (
                ref_level is None or str(reference.get("level")) != str(ref_level)
            ):
                return reject("reference_mismatch", reference=reference, declared=ref_level)
            if str(reference.get("level")) == str(sub.get("level")):
                return reject("reference_mismatch", reference=reference, declared=ref_level)
    else:
        if claim["reference"] is not None:
            return reject("reference_not_in_document", reference=claim["reference"])
        for ref, f in facets:
            if f.scope != "overall":
                return reject("subgroup_mismatch", value_ref=ref, subgroup=None)
    # 7. comparator_id
    if template_id in DIFFERENCE_TEMPLATES:
        blocks = {b for r, _ in numbers for b in DIFFERENCE_BLOCKS if f"/{b}/" in r}
        if template_id == "FAIRNESS_GAP":
            blocks = {"diff_vs_reference"}
        if template_id == "PAIRED_DIFF":
            blocks = {f.block for _, f in facets if f.block is not None}
        if comparator_id not in blocks or len(blocks) != 1:
            return reject("comparator_mismatch", comparator_id=comparator_id, blocks=sorted(blocks))
    elif template_id not in CRITERION_TEMPLATES and comparator_id is not None:
        return reject("comparator_mismatch", comparator_id=comparator_id, blocks=[])
    # 8. criteria by position
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
        row_scope = row.get("scope")
        row_sub = (
            {"attribute": str(row_scope.get("attribute")), "level": str(row_scope.get("level"))}
            if isinstance(row_scope, dict)
            else None
        )
        claim_sub = (
            {"attribute": str(sub.get("attribute")), "level": str(sub.get("level"))}
            if isinstance(sub, dict)
            else None
        )
        # the row's Number by lookup, not by splitting the dotted path (repair 4, lens-4
        # FA-B1: an operating point '[0]' read operating point '0''s Number)
        if row_refs is None:
            row_refs = claims_mod.criteria_row_pointers(doc)
        row_ref = row_refs[index] if index < len(row_refs) else None
        for field_name, claimed, expected_value in (
            ("metric_id", metric_id, row.get("metric")),
            ("operating_point", op, row.get("operating_point")),
            ("subgroup", claim_sub, row_sub),
            ("value_refs", list(refs), [] if row_ref is None else [row_ref]),
        ):
            if claimed != expected_value:
                return reject(
                    "criterion_row_mismatch", field=field_name, claimed=claimed, row=expected_value
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
        # 8b (repair 3, lenses RG-B2 / FA-B1 at 7fa690b): the template's own status
        if template_id == "CRITERION_NOT_MET_RECORD" and row.get("status") != "not_met":
            return reject("template_mismatch", template_id=template_id, row=row.get("status"))
        if template_id == "ATTAINABILITY_NOTE" and not isinstance(row.get("attainable_at_n"), bool):
            return reject(
                "template_mismatch", template_id=template_id, row=row.get("attainable_at_n")
            )
    elif status is not None:
        return reject("status_on_non_criterion", status=status)
    elif claim["criterion_index"] is not None or claim["criterion_id"] is not None:
        return reject("status_on_non_criterion", criterion_index=claim["criterion_index"])
    # 8b. the template against its pointers and the document (repair 3, lenses RG-B2 and
    # FA-B1 at 7fa690b: CL-0001 re-labelled AUROC_ESTIMATE, CL-0014 re-labelled
    # OVERALL_ESTIMATE, gap and calibration pointers permuted, CALIB_NA beside a
    # calibration block, count templates over other counts - each was accepted)
    shapes = TEMPLATE_SHAPES.get(template_id)
    for ref, f in facets:
        if shapes is not None and f.shape not in shapes:
            return reject(
                "value_ref_unbound",
                value_ref=ref,
                template_id=template_id,
                reason="the template reads another pointer shape",
            )
    template_metrics = TEMPLATE_METRICS.get(template_id)
    if template_metrics is not None and metric_id not in template_metrics:
        return reject("metric_mismatch", metric_id=metric_id, template_id=template_id)
    order = SLOT_ORDER.get(template_id)
    if order is not None:
        slot_positions = [order.index(f.metric) if f.metric in order else -1 for _, f in facets]
        if -1 in slot_positions or slot_positions != sorted(set(slot_positions)):
            return reject(
                "value_ref_unbound",
                value_refs=list(refs),
                reason="the pointers do not name the skeleton's slots in its order",
            )
    bound = {r for r, _ in numbers}
    scalars = [r for r in refs if r not in bound]
    if scalars and template_id not in CRITERION_TEMPLATES:
        scalar_slots = SCALAR_SLOTS.get(template_id, ())
        scalar_positions = [_scalar_slot_position(scalar_slots, r) for r in scalars]
        if -1 in scalar_positions or scalar_positions != sorted(set(scalar_positions)):
            return reject(
                "value_ref_unbound",
                value_refs=scalars,
                reason="a count the template's skeleton does not name, or out of its order",
            )
    if template_id in RUN_LEVEL_COUNT_TEMPLATES and any(
        claim[k] is not None for k in ("metric_id", "operating_point", "subgroup", "reference")
    ):
        return reject(
            "template_scope_mismatch",
            template_id=template_id,
            reason="a run-level count template carries a metric, operating point or row",
        )
    if template_id == "CALIB_NA" and isinstance(doc.get("calibration"), dict):
        return reject("template_mismatch", template_id=template_id, reason="calibration present")
    # repair 4, lens-4 FA-B3: the sentence states score_not_probability
    if (
        template_id == "CALIB_NA"
        and not isinstance(doc.get("calibration"), dict)
        and claims_mod.calibration_suppression(doc) != claims_mod.CALIB_NA_REASON
    ):
        return reject(
            "template_mismatch",
            template_id=template_id,
            reason=claims_mod.calibration_suppression(doc),
        )
    # 9. guidance_ref
    gref = claim["guidance_ref"]
    if gref is not None:
        if not isinstance(gref, str) or gref not in guidance:
            return reject("guidance_ref_unknown", guidance_ref=gref)
        if draft_row_unqualified(guidance[gref]):
            return reject(
                "guidance_draft_unqualified", guidance_ref=gref, status=guidance[gref].get("status")
            )
    # 10. free_text
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
    empty on a document with criteria rows. Pure: it writes nothing and reads no
    environment; what it raises on is stated in the module docstring."""
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
    row_refs = claims_mod.criteria_row_pointers(doc)
    ids = [c.get("claim_id") for c in claims if isinstance(c, dict)]
    repeated = {i for i in ids if isinstance(i, str) and ids.count(i) > 1}
    for claim in claims:
        if isinstance(claim, dict) and claim.get("claim_id") in repeated:
            cid = claim["claim_id"]
            verdicts.append(Verdict(cid, False, "claim_id_duplicate", {"count": ids.count(cid)}))
            continue
        verdicts.append(_check_one(claim, doc, lib, guidance, metric_ids, row_refs))
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
    subgroup and criterion position) when that substitute is itself accepted and the slot
    is not already filled - by an accepted claim or by an earlier substitute (repair 1,
    lens FA-N4: two rejected claims on one slot gave ``final`` two copies of ``CL-0001``)
    - and dropped otherwise; each rejection is recorded as ``{claim_id, reason_code,
    template_id, substituted, detail}``.
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
    filled: set[tuple[Any, ...]] = set()
    for claim, verdict in zip(incoming, result.verdicts, strict=True):
        if verdict.accepted:
            final.append(claim)
            filled.add(claims_mod.slot_key(claim))
            continue
        slot = claims_mod.slot_key(claim) if isinstance(claim, dict) else None
        substitute = by_slot.get(slot) if slot is not None else None
        substituted = False
        if substitute is not None and slot not in filled:
            again = check([substitute], document, guidance_map=guidance_map)
            if again.verdicts and again.verdicts[0].accepted:
                final.append(substitute)
                filled.add(slot)
                substituted = True
        rejections.append(
            {
                **verdict.as_rejection(),
                "template_id": claim.get("template_id") if isinstance(claim, dict) else None,
                "substituted": substituted,
            }
        )
    return final, rejections
