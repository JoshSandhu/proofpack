"""``io.mapping`` - the full mapper (day 6 A; D1 section 5 steps 1-5).

What it does: assigns a canonical ROLE to each original header. It reads no declaration
and writes none: positive class, orientation, threshold, reference-standard type,
indeterminates and clustering are read from ``criteria.yaml`` by :mod:`proofpack.io.declare`.

Name signals (D1 step 2), on the normalised header (BOM stripped, NFC, trimmed,
case-folded, camel-case and spaces/hyphens/dots turned into ``_``):

* exact canonical name, ``attr_*`` / ``rater_*`` -> source ``canonical``;
* the synonym table :data:`SYNONYMS` (also matched with underscores removed) ->
  ``synonym``;
* a synonym after stripping one of :data:`AFFIX_PREFIXES` / :data:`AFFIX_SUFFIXES`
  (``pt_gender``, ``label_v2``) -> ``affix``;
* a header token in :data:`PARTIAL_TOKENS` (``patient_nbr``, ``anchor_age``) ->
  ``partial``;
* a date-like header (the same regex gate H11 inspects) -> ``event_date`` by name.

Value signals (heuristics, from :mod:`proofpack.io.profile` summaries) are listed in
:func:`_value_candidate`. Confidence is the three-level enum ``high | medium | low``:

    name signal                     values                          confidence
    canonical / synonym / affix     consistent with the role        high
    canonical / synonym / affix     no values (header-only call)    high (canonical) /
                                                                    medium (synonym, affix)
    canonical / synonym / affix     conflicting with the role       low  + note
    partial token                   agreeing                        medium
    partial token                   no values / not agreeing        low
    none (heuristic alone)          one candidate for the role      medium
    any                             two headers claim one role      low  + note (both)
    none                            -                               ignore, high

``sex`` coded 1/2 or 0/1 is ``medium`` with the note ``no dictionary declared for ...``
even though the header is an exact synonym: no dictionary is applied to the codes, so the
levels stay the strings ``1`` and ``2`` (or ``0`` and ``1``) until a human confirms them.
Two headers resolving to ``case_id`` by name (canonical, synonym or affix:
``patient_id`` + ``subject_id``) halt with E01 (DEC-11) in :func:`map_headers`. Two
headers that only carry a ``case_id`` token (``patient_nbr`` + ``mrn_local``) are both
``low`` with the two notes, and a mapping that holds two columns on ``case_id`` when it
reaches :func:`apply_mapping` halts E01 there, whatever the source (repair 2, FA-B1: at
e92989b that pair halted H07 ``two columns map to the same canonical role`` through
``proofpack run``, and the accept prompt took both;
``tests/test_mapping_repair2.py::test_two_partial_case_id_headers_reach_e01_at_apply_not_h07``).
The token claims are not counted by ``map_headers``'s E01 because ``patient_weight`` +
``patient_height`` carry the same token and no case key
(``::test_two_partial_case_id_tokens_are_not_counted_by_map_headers_e01``).

Original headers are written to ``mapping.json`` and nowhere else by this module.
``tests/test_mapping_full.py::test_fixture_halts_and_two_constructed_ones_carry_no_header_or_value``
raises every halt the committed fixtures raise, plus two constructed ones, and greps each
message and detail for that table's headers and its cell values of three or more characters.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from proofpack.errors import HaltError
from proofpack.io.profile import SAMPLE_ROWS, ColumnSummary, profile_column
from proofpack.io.schema import (
    _IDENT,
    DATE_LIKE_HEADER,
    canonical_columns,
    date_like_headers,
    header_set_sha256,
)

#: D1 section 5.2 synonym table (lower-cased). Canonical names map to themselves.
SYNONYMS: dict[str, str] = {
    **{
        c: c
        for c in (
            "row_id",
            "case_id",
            "y_true",
            "score",
            "y_pred",
            "indeterminate",
            "age",
            "age_band",
            "sex",
            "race",
            "ethnicity",
            "site",
            "device",
            "protocol",
            "severity",
            "event_date",
            "period",
            "model_version",
            "dataset",
        )
    },
    "label": "y_true",
    "truth": "y_true",
    "gt": "y_true",
    "ground_truth": "y_true",
    "outcome": "y_true",
    "target": "y_true",
    "reference": "y_true",
    "y": "y_true",
    "prob": "score",
    "probability": "score",
    "p1": "score",
    "pred_prob": "score",
    "confidence": "score",
    "output": "score",
    "risk": "score",
    "prediction": "y_pred",
    "predicted": "y_pred",
    "pred_label": "y_pred",
    "class": "y_pred",
    "gender": "sex",
    "centre": "site",
    "center": "site",
    "hospital": "site",
    "institution": "site",
    "facility": "site",
    "scanner": "device",
    "manufacturer": "device",
    "vendor": "device",
    "model_name": "device",
    "patient_id": "case_id",
    "subject_id": "case_id",
    "study_id": "case_id",
    "mrn_hash": "case_id",
    # Dataset-specific rows added on day 6 A for the R3 fixtures (the brief's acceptance:
    # the Sepsis-2019 and Diabetes-130 header sets map high on label/score/site/age/sex).
    # Header names confirmed on the PhysioNet 2019 page (SepsisLabel, Age, Gender) and the
    # UCI page (gender, age, race, patient_nbr, encounter_id); ``readmitted`` and the two
    # PhysioNet prediction-output names are [unverified] on the fetched pages.
    "sepsis_label": "y_true",
    "readmitted": "y_true",
    "predicted_probability": "score",
    "predicted_label": "y_pred",
    "hospital_system": "site",
}

#: Affixes stripped for the second lookup (``pt_age`` -> ``age``, ``label_v2`` -> ``label``).
AFFIX_PREFIXES: tuple[str, ...] = ("pt_", "patient_", "pat_", "subject_", "subj_")
AFFIX_SUFFIXES: tuple[str, ...] = (r"_v\d+",)

#: Header tokens that suggest a role without naming it (source ``partial``).
PARTIAL_TOKENS: dict[str, str] = {
    "patient": "case_id",
    "subject": "case_id",
    "mrn": "case_id",
    "age": "age",
    "sex": "sex",
    "gender": "sex",
    "label": "y_true",
    "outcome": "y_true",
    "truth": "y_true",
    "prob": "score",
    "probability": "score",
    "risk": "score",
    "score": "score",
    "pred": "y_pred",
    "prediction": "y_pred",
    "site": "site",
    "hospital": "site",
    "centre": "site",
    "center": "site",
}

#: Two-valued sets that make a column a ``y_true`` candidate by values alone.
BINARY_LABEL_SETS: tuple[frozenset[str], ...] = (
    frozenset({"0", "1"}),
    frozenset({"true", "false"}),
    frozenset({"yes", "no"}),
    frozenset({"pos", "neg"}),
    frozenset({"positive", "negative"}),
)
SEX_MF = frozenset({"m", "f", "male", "female"})
SEX_12 = frozenset({"1", "2"})
SEX_01 = frozenset({"0", "1"})
#: Age bands like ``[70-80)``, ``70-79``, ``70 - 79``, ``90+``.
AGE_BAND = re.compile(r"^\[?\s*\d{1,3}\s*[-\u2013]\s*\d{1,3}\s*[\)\]]?$|^\d{1,3}\s*\+$")
#: Roles for which a second name claim is a conflict; ``attr_*`` / ``rater_*`` are checked
#: by prefix in :func:`_single_holder` (repair 2, FA-N7: at e92989b ``Attr Site`` beside
#: ``attr_site`` were both ``attr_site high`` and ``run`` halted H07 on the pair).
SINGLE_HOLDER_ROLES = frozenset(canonical_columns())
IGNORE = "ignore"
CONFIDENCES = ("high", "medium", "low")
#: ``decided_by`` values a prior mapping.json may carry for ``--yes`` (D1 section 5 step 5).
CONFIRMED_DECIDED_BY = frozenset({"interactive", "file"})

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[\s\-\.]+")


def normalise_header(header: str) -> str:
    """BOM stripped, NFC, trimmed, camel-case split, separators to ``_``, case-folded."""
    h = unicodedata.normalize("NFC", header.replace("\ufeff", "")).strip()
    h = _CAMEL.sub("_", h)
    h = _SEPARATORS.sub("_", h)
    h = re.sub(r"_+", "_", h).strip("_")
    return h.casefold()


def fold_header(header: str) -> str:
    """BOM stripped, NFC, trimmed, case-folded - the identity two headers must not share."""
    return unicodedata.normalize("NFC", header.replace("\ufeff", "")).strip().casefold()


_SYNONYMS_NO_UNDERSCORE: dict[str, str] = {k.replace("_", ""): v for k, v in SYNONYMS.items()}


def _lookup_synonym(key: str) -> str | None:
    if key in SYNONYMS:
        return SYNONYMS[key]
    return _SYNONYMS_NO_UNDERSCORE.get(key.replace("_", ""))


def _strip_affixes(key: str) -> str | None:
    out = key
    for p in AFFIX_PREFIXES:
        if out.startswith(p) and len(out) > len(p):
            out = out[len(p) :]
            break
    for s in AFFIX_SUFFIXES:
        out2 = re.sub(s + "$", "", out)
        if out2 != out and out2:
            out = out2
            break
    return out if out != key else None


@dataclass
class RoleMapping:
    original: str
    role: str | None  # None = ignore
    confidence: str  # high | medium | low
    source: str = "ignore"  # canonical | synonym | affix | partial | heuristic | ignore
    notes: list[str] = field(default_factory=list)
    # True after ``a`` (DEC-28) or ``e`` (DEC-42; at 4fbbf35 an edit left it False) at the
    # per-role prompt: a human chose the role. Read back from mapping.json as a bool (any
    # other JSON type is H07 in :meth:`Mapping.read`).
    confirmed: bool = False

    @property
    def role_label(self) -> str:
        return self.role or IGNORE


@dataclass
class Mapping:
    header_set_sha256: str
    roles: list[RoleMapping]
    decided_by: str  # proposed | interactive | file
    timestamp: str
    value_summaries: dict = field(default_factory=dict)  # original -> suppressed summary dict
    file_sha256: str | None = None  # sha256 of mapping.json's bytes after write()/read()

    def role_of(self, original: str) -> str | None:
        for r in self.roles:
            if r.original == original:
                return r.role
        return None

    def entry(self, original: str) -> RoleMapping | None:
        for r in self.roles:
            if r.original == original:
                return r
        return None

    def holders(self, role: str) -> list[str]:
        return [r.original for r in self.roles if r.role == role]

    @property
    def all_high(self) -> bool:
        return all(r.confidence == "high" for r in self.roles if r.role is not None)

    @property
    def non_high(self) -> list[RoleMapping]:
        return [r for r in self.roles if r.role is not None and r.confidence != "high"]

    def to_dict(self) -> dict:
        return {
            "header_set_sha256": self.header_set_sha256,
            "roles": [
                {
                    "original": r.original,
                    "role": r.role_label,
                    "confidence": r.confidence,
                    "source": r.source,
                    "notes": list(r.notes),
                    "confirmed": bool(r.confirmed),
                }
                for r in self.roles
            ],
            "value_summaries": self.value_summaries,
            "decided_by": self.decided_by,
            "timestamp": self.timestamp,
        }

    def to_bytes(self) -> bytes:
        return (json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n").encode("utf-8")

    def write(self, path: str | Path) -> str:
        data = self.to_bytes()
        Path(path).write_bytes(data)
        self.file_sha256 = hashlib.sha256(data).hexdigest()
        return self.file_sha256

    @classmethod
    def read(cls, path: str | Path) -> Mapping:
        """Read a prior ``mapping.json``.

        Inspected, each failure H07 ``the prior mapping.json could not be decoded`` or
        ``could not be read``: an OSError on the read; ``json.loads`` on the UTF-8 decoded
        bytes raising ``ValueError`` (``JSONDecodeError``, ``UnicodeDecodeError``) or
        ``RecursionError`` (at 1354758 a file of 100,000 nested ``[`` was exit 5
        ``internal error: RecursionError`` - lens-3 FA-B4;
        ``tests/test_mapping_repair3.py::test_prior_of_nested_brackets_is_h07_not_exit_5``);
        the top level is a mapping (``data.get`` raises AttributeError on a list, str, int,
        null or bool); ``header_set_sha256`` is a string; ``roles`` is a JSON list
        (``isinstance`` - at 1354758 ``"roles": {}`` and ``"roles": ""`` iterated as empty and
        ``map --yes`` exit 0 and rewrote the file, lens-3 RG-B1;
        ``::test_prior_with_a_non_list_roles_is_h07_and_the_file_is_unchanged`` feeds both);
        each entry is a mapping with string ``original`` and ``confidence``, a ``role``
        that is a string or null, and a ``confirmed`` that is absent or a bool;
        ``value_summaries`` is a mapping or null. Not inspected here: the role name, the
        original against the header set, the confidence against ``high|medium|low``,
        ``notes`` entries, ``decided_by``'s type (cast to str) - ``check_h07`` inspects the
        first two and ``decided_by``. At 555a5e1 ``"roles": "x"`` reached ``--yes`` as exit 5
        (repair 1, FA-N6;
        ``tests/test_mapping_repair1.py::test_malformed_prior_under_yes_halts_h07_not_exit_5``
        feeds seven files); at e92989b ``"role": 123`` and ``"role": ["a"]`` passed this
        function and ``run --yes`` was exit 5 ``AttributeError`` / ``TypeError`` (repair 2,
        RG-B1; ``tests/test_mapping_repair2.py::
        test_prior_with_a_non_string_role_halts_h07_under_run_yes_and_map_yes`` feeds five).
        """
        try:
            raw = Path(path).read_bytes()
        except OSError as exc:
            raise HaltError("H07", "mapping.json could not be read") from exc
        try:
            # utf-8-sig: a leading BOM (PowerShell 5.1 Out-File's default) is dropped; at
            # b0f60a6 such a file was H07 "could not be decoded" (repair 3.2, FA-N5;
            # tests/test_mapping_repair3_2.py::test_a_prior_with_a_utf8_bom_is_read)
            data = json.loads(raw.decode("utf-8-sig"))
        except (ValueError, RecursionError) as exc:
            raise HaltError("H07", "the prior mapping.json could not be decoded") from exc
        try:
            if not isinstance(data.get("header_set_sha256"), str):
                raise TypeError("header_set_sha256")
            if not isinstance(data["roles"], list):
                raise TypeError("roles")
            roles = []
            for r in data["roles"]:
                if not isinstance(r, dict):  # a list's ints, strings, lists or nulls
                    raise TypeError("role entry")
                role = r.get("role")
                if not isinstance(r["original"], str) or not isinstance(r["confidence"], str):
                    raise TypeError("role entry fields")
                if role is not None and not isinstance(role, str):
                    raise TypeError("role")
                confirmed = r.get("confirmed", False)
                if not isinstance(confirmed, bool):
                    raise TypeError("confirmed")
                roles.append(
                    RoleMapping(
                        r["original"],
                        None if role in (None, IGNORE) else role,
                        r["confidence"],
                        r.get("source", "ignore" if role in (None, IGNORE) else "file"),
                        list(r.get("notes", [])),
                        confirmed,
                    )
                )
            summaries = data.get("value_summaries")
            if summaries is not None and not isinstance(summaries, dict):
                raise TypeError("value_summaries")
            m = cls(
                header_set_sha256=data["header_set_sha256"],
                roles=roles,
                decided_by=str(data.get("decided_by", "file")),
                timestamp=str(data.get("timestamp", "")),
                value_summaries=summaries or {},
            )
            m.file_sha256 = hashlib.sha256(raw).hexdigest()
            return m
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise HaltError("H07", "mapping.json could not be read") from exc

    def table(self) -> str:
        """The printed mapping table: original header -> role -> confidence -> summary."""
        lines = [f"  {'original header':32} -> {'role':14} {'conf':7} value summary"]
        for r in self.roles:
            summ = self.value_summaries.get(r.original)
            text = ColumnSummary(**_summary_fields(summ)).render() if summ else "(no values)"
            lines.append(f"  {r.original!r:32} -> {r.role_label:14} {r.confidence:7} {text}")
            for n in r.notes:
                lines.append(f"  {'':32}    note: {n}")
        return "\n".join(lines)


def _summary_fields(d: dict) -> dict:
    keys = ColumnSummary.__dataclass_fields__
    return {k: v for k, v in d.items() if k in keys and k != "signals"}


# --------------------------------------------------------------------------- name signals


@dataclass
class _Claim:
    role: str
    source: str  # canonical | synonym | affix | partial | date_header


def _name_claim(original: str, key: str, canon: set[str]) -> _Claim | None:
    if key == "":
        return _Claim(IGNORE, "empty")
    if key in canon:
        # ``original in canon`` implies ``key in canon`` (every canonical name is lower-case
        # letters, digits and ``_``, which normalise_header maps to itself), so the clause
        # ``or original in canon`` that stood here until 1354758 was never the deciding
        # one (lens-3 L20); tests/test_mapping_repair3.py::
        # test_every_canonical_name_normalises_to_itself feeds the whole list.
        return _Claim(key, "canonical")
    if key.startswith(("attr_", "rater_")):
        return _Claim(key, "canonical")
    role = _lookup_synonym(key)
    if role is not None:
        return _Claim(role, "synonym")
    stripped = _strip_affixes(key)
    if stripped is not None:
        role = _lookup_synonym(stripped)
        if role is None and stripped in canon:
            role = stripped
        if role is not None:
            return _Claim(role, "affix")
    if original == "event_date" or DATE_LIKE_HEADER.search(original):
        return _Claim("event_date", "date_header")
    for token in key.split("_"):
        if token in PARTIAL_TOKENS:
            return _Claim(PARTIAL_TOKENS[token], "partial")
    return None


# --------------------------------------------------------------------------- value signals


def _value_candidate(s: ColumnSummary) -> str | None:
    """The role a column's values alone suggest (heuristic), or None.

    * exactly two values from one of :data:`BINARY_LABEL_SETS` -> ``y_true``;
    * float within [0, 1] with more than two unique values -> ``score``;
    * every value a parseable date -> ``event_date``;
    * integer column with ``n_unique == n_rows`` (no missing, >= 2 rows) -> ``row_id``.

    ``case_id`` and the categorical attributes (site/device/race/...) are not among this
    function's outcomes: a repeating column is proposed as ``case_id`` only beside a name
    signal (DEC-11 territory), and attributes are assigned by name only.
    """
    sig = s.signals
    if sig.get("n_nonmissing", 0) < 2:
        return None
    lowered = sig.get("lowered_values", set())
    if len(lowered) == 2 and any(lowered == b for b in BINARY_LABEL_SETS):
        return "y_true"
    if s.inferred_type == "float" and sig.get("unit_interval") and s.n_unique > 2:
        return "score"
    if sig.get("date"):
        return "event_date"
    if s.inferred_type == "int" and sig.get("all_unique"):
        return "row_id"
    return None


def _is_banded_age(s: ColumnSummary) -> bool:
    vals = s.signals.get("lowered_values", set())
    return bool(vals) and all(AGE_BAND.match(v) for v in vals)


def _check_consistency(role: str, s: ColumnSummary) -> tuple[str, str | None, str | None]:
    """(verdict, role_override, note) for a name-claimed role against its values.

    verdict is ``consistent`` | ``conflict`` | ``coded`` (sex 1/2 or 0/1) | ``unknown``.
    """
    sig = s.signals
    kind = s.inferred_type
    lowered = sig.get("lowered_values", set())
    if kind == "empty":
        return "unknown", None, None
    if role in ("y_true", "y_pred"):
        if kind == "float" and s.n_unique > 2:
            return (
                "conflict",
                None,
                f"header names a {'label' if role == 'y_true' else 'prediction'} but the "
                f"values are continuous ({s.n_unique} unique floats); the header's role is "
                "kept at low confidence",
            )
        if s.n_unique > 10:
            return "conflict", None, f"label column holds {s.n_unique} distinct values"
        return "consistent", None, None
    if role == "score":
        if kind not in ("int", "float"):
            return "conflict", None, "header names a score but the values are not numeric"
        if s.n_unique <= 2 and lowered <= {"0", "1", "0.0", "1.0"}:
            return "conflict", None, "header names a score but the values are only 0/1"
        return "consistent", None, None
    if role == "age":
        if kind in ("int", "float"):
            return "consistent", None, None
        if _is_banded_age(s):
            return "consistent", "age_band", "banded values; role age_band"
        return "conflict", None, "header names age but the values are neither numeric nor bands"
    if role == "age_band":
        if kind in ("int", "float"):
            return "consistent", "age", "numeric values; role age"
        return "consistent", None, None
    if role == "sex":
        if lowered and lowered <= SEX_MF:
            return "consistent", None, None
        if lowered and lowered <= SEX_12:
            return "coded", None, "no dictionary declared for 1/2"
        if lowered and lowered <= SEX_01:
            return "coded", None, "no dictionary declared for 0/1"
        return "coded", None, "values outside M/F/male/female; confirm the coding"
    if role == "event_date":
        if sig.get("date"):
            return "consistent", None, None
        return "conflict", None, "header is date-like but the values are not dates"
    if role == "row_id":
        return "consistent", None, None
    return "consistent", None, None


# --------------------------------------------------------------------------- the mapper


def map_headers(
    headers: list[str],
    columns: dict[str, list] | None = None,
    *,
    sample_rows: int = SAMPLE_ROWS,
) -> Mapping:
    """Assign a role and a confidence to every header; summaries when ``columns`` is given.

    Raises H07 when two headers coincide after :func:`normalise_header`, and E01
    (DEC-11) when two headers resolve to ``case_id`` by name (canonical, synonym or
    affix; token claims are not counted - the module docstring names the pair why).
    """
    canon = set(canonical_columns())
    keys = [normalise_header(h) for h in headers]
    folded = [fold_header(h) for h in headers]
    if len(set(folded)) != len(folded):
        dup = len(folded) - len(set(folded))
        raise HaltError(
            "H07",
            "two headers are identical after case-folding, whitespace trimming and unicode "
            "normalisation; rename one of them",
            {"n_duplicate_headers": dup},
        )

    summaries: dict[str, ColumnSummary] = {}
    if columns is not None:
        for h in headers:
            if h in columns:
                summaries[h] = profile_column(columns[h], sample_rows=sample_rows)

    claims: dict[str, _Claim | None] = {
        h: _name_claim(h, k, canon) for h, k in zip(headers, keys, strict=True)
    }
    values: dict[str, str | None] = {
        h: (_value_candidate(summaries[h]) if h in summaries else None) for h in headers
    }

    # DEC-11: two name claims on case_id halt before anything else is decided.
    case_claims = [
        h for h, c in claims.items() if c and c.role == "case_id" and c.source != "partial"
    ]
    if len(case_claims) >= 2:
        raise HaltError(
            "E01",
            f"{len(case_claims)} columns resolve to case_id; reduce your case key to one column",
            {"n_case_id_columns": len(case_claims)},
        )

    name_holders: dict[str, list[str]] = {}
    for h, c in claims.items():
        if c and c.source in ("canonical", "synonym", "affix", "date_header"):
            name_holders.setdefault(c.role, []).append(h)
    partial_holders: dict[str, list[str]] = {}
    for h, c in claims.items():
        if c and c.source == "partial":
            partial_holders.setdefault(c.role, []).append(h)
    value_holders: dict[str, list[str]] = {}
    for h, v in values.items():
        if v is not None:
            value_holders.setdefault(v, []).append(h)

    roles: list[RoleMapping] = []
    for h in headers:
        c = claims[h]
        s = summaries.get(h)
        v = values[h]
        if c is not None and c.source == "empty":
            roles.append(RoleMapping(h, None, "high", "ignore", ["empty header"]))
            continue
        if c is not None and c.source != "partial":
            roles.append(_decide_named(h, c, s, name_holders))
            continue
        if c is not None:  # partial token
            role = c.role
            if name_holders.get(role):
                roles.append(
                    RoleMapping(
                        h,
                        None,
                        "high",
                        "ignore",
                        [f"header resembles {role} but another header names it; ignored"],
                    )
                )
                continue
            n_partial = len(partial_holders.get(role, []))
            if s is None:
                roles.append(RoleMapping(h, role, "low", "partial", ["header token only"]))
                continue
            verdict, override, note = _check_consistency(role, s)
            notes = [note] if note else []
            if role == "case_id":
                # a partial token is not a resolved case key (DEC-11 halts on name claims
                # only); the values may repeat or not - the human decides. A second
                # token holder gets the count note too (repair 2, FA-B1: at e92989b the
                # branch returned before it)
                notes.append("header resembles a case identifier; confirm or ignore")
                if n_partial >= 2:
                    notes.append(f"{n_partial} headers carry a token for {role}; choose one")
                conf = "low"
            elif n_partial >= 2:
                notes.append(f"{n_partial} headers carry a token for {role}; choose one")
                conf = "low"
            else:
                conf = "medium" if verdict in ("consistent", "coded") else "low"
            roles.append(RoleMapping(h, override or role, conf, "partial", notes))
            continue
        if v is not None:
            if name_holders.get(v) or partial_holders.get(v):
                what = {
                    "y_true": "two-valued",
                    "score": "float within [0, 1]",
                    "event_date": "date-valued",
                    "row_id": "unique-integer",
                }[v]
                roles.append(
                    RoleMapping(
                        h, None, "high", "ignore", [f"{what} but {v} is claimed by name; ignored"]
                    )
                )
                continue
            n_v = len(value_holders[v])
            if n_v >= 2:
                roles.append(
                    RoleMapping(
                        h,
                        v,
                        "low",
                        "heuristic",
                        [f"{n_v} columns look like {v} by values; choose one"],
                    )
                )
            else:
                roles.append(RoleMapping(h, v, "medium", "heuristic", ["by values only"]))
            continue
        roles.append(RoleMapping(h, None, "high", "ignore"))

    return Mapping(
        header_set_sha256=header_set_sha256(headers),
        roles=roles,
        decided_by="proposed",
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
        value_summaries={h: summaries[h].to_dict() for h in headers if h in summaries},
    )


def _single_holder(role: str) -> bool:
    """Whether two columns on ``role`` are a conflict (every role except ``ignore``)."""
    return role in SINGLE_HOLDER_ROLES or role.startswith(("attr_", "rater_"))


def _decide_named(
    h: str, c: _Claim, s: ColumnSummary | None, name_holders: dict[str, list[str]]
) -> RoleMapping:
    role = c.role
    notes: list[str] = []
    holders = name_holders.get(role, [])
    if _single_holder(role) and len(holders) >= 2:
        notes.append(f"{len(holders)} headers claim {role}; choose one")
        return RoleMapping(h, role, "low", c.source, notes)
    if s is None:
        conf = "high" if c.source == "canonical" else "medium"
        if c.source != "canonical":
            notes.append("name only; no values inspected")
        return RoleMapping(h, role, conf, c.source, notes)
    verdict, override, note = _check_consistency(role, s)
    if note:
        notes.append(note)
    if verdict == "conflict":
        return RoleMapping(h, role, "low", c.source, notes)
    if verdict == "coded":
        return RoleMapping(h, role, "medium", c.source, notes)
    if verdict == "unknown":
        conf = "high" if c.source == "canonical" else "medium"
        notes.append("no values in the sample")
        return RoleMapping(h, override or role, conf, c.source, notes)
    return RoleMapping(h, override or role, "high", c.source, notes)


# --------------------------------------------------------------------------- apply, H07, H11


#: The key an ignored column takes at :func:`apply_mapping` when its original header is
#: a name ``io.schema.validate`` reads as a role (repair 3.2, FA-B1).
IGNORED_PREFIX = "ignored:"


def read_as_a_role_by_validate(name: str) -> bool:
    """The three header names ``io.schema.validate`` reads as a role rather than parking
    in ``unused_columns``: a canonical name, an ``attr_`` name matching :data:`_IDENT`
    (the bare ``attr_`` matches it), or any ``rater_`` prefix - the three branches of
    its header loop, mirrored here
    (``tests/test_mapping_repair3_2.py::test_ignored_role_names_are_the_names_validate_reads``
    feeds the 19 canonical names, ``attr_x``, ``attr_X``, ``attr_``, ``rater_1``,
    ``rater_`` and ``notes`` to both: ``attr_X`` and ``notes`` are the two parked)."""
    return (
        name in canonical_columns()
        or (name.startswith("attr_") and _IDENT.match(name) is not None)
        or name.startswith("rater_")
    )


def apply_mapping(columns: dict[str, list], mapping: Mapping) -> dict[str, list]:
    """Rename original headers to canonical roles.

    An ignored column keeps its name unless that name is one ``validate`` reads as a
    role (:func:`read_as_a_role_by_validate`), in which case it is keyed
    ``ignored:<original>`` so ``validate`` parks it in ``unused_columns``. At b0f60a6 an
    ignored column kept its name whatever it was, and ``validate`` read it by that
    name: ``sex`` (1/2/9) answered ``e ignore`` at the prompt reached the pack as the
    ``sex`` attribute (``ingest_report.json`` ``attributes: ["sex", "site"]``,
    ``n_unused_columns: 0``), and ``score`` (0/1) ignored beside ``prob`` edited to
    ``attr_prob_raw`` was read as the score (lens-1 FA-B1 of repair 3;
    ``tests/test_mapping_repair3_2.py::test_an_ignored_column_named_for_a_role_does_not_reach_validate_under_that_name``
    feeds both tables through ``map`` and ``run --mapping``). ``notes`` ignored keeps
    its name (``tests/test_mapping_repair3.py::
    test_ignored_columns_otherwise_keep_their_name_at_apply_mapping``).

    Two columns on ``case_id`` are the DEC-11 composite key, E01 ending ``reduce your
    case key to one column``; two columns on any other role are H07 (repair 2, FA-B1:
    at e92989b ``patient_nbr`` + ``mrn_local`` were H07 here through ``proofpack run``).
    The DEC-31 pair ``score -> ignore`` beside ``prob -> score`` is refused at the prompt
    and halted on a prior by :func:`check_h07` before this function runs
    (:func:`ignore_collision`); fed to this function directly it now returns the keys
    ``row_id, score, ignored:score`` (at b0f60a6 it was the H07 above with
    ``{"role": "score"}``; the same test).
    """
    n_case = sum(1 for original in columns if mapping.role_of(original) == "case_id")
    if n_case >= 2:
        raise HaltError(
            "E01",
            f"{n_case} columns are mapped to case_id (proofpack map: keep one, set the "
            "others to ignore); reduce your case key to one column",
            {"n_case_id_columns": n_case},
        )
    out: dict[str, list] = {}
    for original, values in columns.items():
        role = mapping.role_of(original)
        if role is None:
            role = IGNORED_PREFIX + original if read_as_a_role_by_validate(original) else original
        if role in out:
            if role.startswith(IGNORED_PREFIX):
                # a header spelled ``ignored:score`` beside an ignored ``score``: the
                # detail carries a count, not that header
                # (tests/test_mapping_repair3_2.py::
                # test_a_header_spelled_like_the_ignored_key_is_h07_without_the_header)
                raise HaltError(
                    "H07",
                    "a column's header equals the ignored: key of another column; rename one",
                    {"n_ignored_key_collisions": 1},
                )
            raise HaltError("H07", "two columns map to the same canonical role", {"role": role})
        out[role] = values
    return out


#: The halt :func:`period_for_validate` raises: S03 because the declared period column
#: does not reach the table ``validate`` types (it is parked as unused), which is what
#: S03's line in ``errors.SCHEMA_CODES`` says; H11 names the opposite case (a date
#: column with no declaration) and H07 the mapping hash [decision, repair 4 of A-P1].
PERIOD_IGNORED = (
    "the period declaration names a column mapping.json ignores; map it to event_date or "
    "declare another column"
)


def period_for_validate(mapping: Mapping, period: dict | None) -> dict | None:
    """The ``period`` block ``io.schema.validate`` reads, with ``column`` translated from an
    original header to the key :func:`apply_mapping` gives that column.

    ``validate`` reads ``period["column"]`` by name outside its header loop - the fourth
    name it reads, beside the three :func:`read_as_a_role_by_validate` mirrors - so an
    ignored column that keeps its name was the pack's period axis while counted in
    ``n_unused_columns``. At 4fbbf35 ``make_cohort(60)`` plus ``visit`` =
    ``["2024-03-15"] * 30 + ["2024-09-15"] * 30``, ``period: {column: visit, granularity:
    quarter}``, ``map`` answered ``e ignore`` and then ``run --mapping`` was exit 0 with
    ``table.period`` levels ``2024-Q1, 2024-Q3`` built from the ignored column and
    ``n_unused_columns: 1``; a ``visit`` of one ISO date and 59 blanks, proposed ``ignore
    high`` and never prompted, did the same through ``run`` without a prior (lens-2 FA-B1
    of repair 3.2; ``tests/test_mapping_repair4.py::
    test_an_ignored_visit_named_by_period_column_is_s03_on_both_routes`` feeds both, through
    ``gates.ingest`` and through ``proofpack run``). Now: the name is an original
    header whose role is ``ignore`` -> S03 :data:`PERIOD_IGNORED`; whose
    role is ``R`` -> ``column`` becomes ``R`` (at 4fbbf35 ``visit -> event_date`` with
    ``period.column: visit`` was S03 ``declared period column is not present in the
    table``, lens-2 N4 - ``check_h11`` covered the header while ``validate`` wanted the
    role); not an original header (``event_date``, ``period``, or a name ``validate``
    will not find and halts S03 on) -> unchanged.
    """
    if period is None:
        return None
    pcol = period.get("column")
    entry = mapping.entry(pcol) if isinstance(pcol, str) else None
    if entry is None:
        return period
    if entry.role is None:
        raise HaltError("S03", PERIOD_IGNORED, {"period_column_ignored": True})
    return {**period, "column": entry.role}


def ignore_collision(
    roles: list[RoleMapping], *, ignored: RoleMapping | None = None, role: str | None = None
) -> tuple[RoleMapping, str, RoleMapping] | None:
    """DEC-31: the first (ignored entry, role, holder) where an ignored column's folded
    header equals a role another column holds (lens-3 FA-B2: at 1354758 the table
    ``row_id,label,score,prob`` answered ``e ignore a`` wrote ``score -> ignore``,
    ``prob -> score`` and ``proofpack run --mapping`` halted H07 ``two columns map to the
    same canonical role``, because ``apply_mapping`` then kept an ignored column's name;
    since repair 3.2 it keys such a column ``ignored:<original>``, and the refusal
    stays as DEC-31 decided it; ``tests/test_mapping_repair3.py::
    test_ignore_on_a_column_named_for_a_held_role_is_refused_at_the_prompt``).

    With ``ignored`` and ``role`` given, the check is made as if that entry held ``role``
    (``None`` = ignore) - the prompt asks before it changes the entry.
    """
    state = {id(r): r.role for r in roles}
    if ignored is not None:
        state[id(ignored)] = role
    for r in roles:
        if state[id(r)] is not None:
            continue
        name = fold_header(r.original)
        for o in roles:
            if o is not r and state[id(o)] == name:
                return r, name, o
    return None


def _check_prior_against_table(prior: Mapping, headers: list[str]) -> None:
    """DEC-29 and DEC-31 on a prior whose hash matched: entry set = header set, every
    role canonical or ``attr_`` / ``rater_`` (:data:`_IDENT`), no ignore collision."""
    header_set = set(headers)
    unknown = sum(1 for r in prior.roles if r.original not in header_set)
    if unknown:
        raise HaltError(
            "H07",
            "mapping.json names a column that is not in this table's header set; run "
            "proofpack map again",
            {"originals_not_in_table": unknown},
        )
    originals = {r.original for r in prior.roles}
    missing = sum(1 for h in headers if h not in originals)
    if missing:
        raise HaltError(
            "H07",
            "mapping.json has no entry for a column of this table; run proofpack map again",
            {"columns_without_entry": missing},
        )
    duplicated = len(prior.roles) - len(originals)
    if duplicated:
        # ``entry()`` takes the first and ``_check_yes_rule`` would take the last
        raise HaltError(
            "H07",
            "mapping.json holds two entries for one column; run proofpack map again",
            {"duplicate_entries": duplicated},
        )
    canon = set(canonical_columns())
    bad = sum(
        1
        for r in prior.roles
        if r.role is not None
        and r.role not in canon
        and not (
            _IDENT.match(r.role)
            and any(r.role.startswith(p) and len(r.role) > len(p) for p in ("attr_", "rater_"))
        )
    )
    if bad:
        raise HaltError(
            "H07",
            "mapping.json holds a role that is not a canonical role or an attr_ / rater_ "
            "name; run proofpack map again",
            {"roles_not_canonical": bad},
        )
    pair = ignore_collision(prior.roles)
    if pair is not None:
        _, role, _ = pair
        raise HaltError(
            "H07",
            f"mapping.json ignores the column whose header is the role name {role} and maps "
            f"another column to {role} (DEC-31); run proofpack map again and give one of "
            "them another role",
            {"role": role},
        )


def _summary_shape(summary: object) -> tuple[object, frozenset[str] | None] | None:
    """The (``inferred_type``, split values) of a stored value summary, or None when the
    summary is not a mapping. The split's counts are left out (a re-export with the same
    two values in other proportions keeps the shape); a split that is not a list (``"x"``
    and ``{}`` were fed) reads as no split; a list whose items are not non-empty lists
    (``[1, 2]``, ``[]``, ``[[]]``) reads as an empty split and differs from no split, so
    a stored ``split: [1, 2]`` beside a fresh ``split: null`` halts ``--yes`` H07 (lens-2
    RG-B1 of repair 3.2: at 4fbbf35 this sentence said the three read as no split;
    ``tests/test_mapping_repair4.py::test_a_split_that_is_a_list_of_non_lists_is_an_empty_split``)."""
    if not isinstance(summary, dict):
        return None
    split = summary.get("split")
    values = None
    if isinstance(split, list):
        values = frozenset(str(item[0]) for item in split if isinstance(item, list) and item)
    return summary.get("inferred_type"), values


def _summaries_agree(prior: Mapping, fresh: Mapping, original: str) -> bool | None:
    """True / False when both ``value_summaries`` hold ``original`` and their
    :func:`_summary_shape` are equal / differ; None when either holds no summary for it
    (a hand-authored ``file`` prior holds none; a ``fresh`` computed from headers alone
    holds none; at 4fbbf35 ``value_summaries: {}`` and ``null`` in a confirmed prior on
    the ten-string ``patient`` re-export passed ``map --yes`` and were not compared -
    lens-2 FA-B3 / RG-N1 of repair 3.2, pinned as the choice by
    ``tests/test_mapping_repair4.py::test_a_confirmed_prior_without_summaries_is_not_compared``)."""
    if original not in prior.value_summaries or original not in fresh.value_summaries:
        return None
    return _summary_shape(prior.value_summaries[original]) == _summary_shape(
        fresh.value_summaries[original]
    )


def _check_yes_rule(prior: Mapping, fresh: Mapping) -> None:
    """DEC-28 with the carried-7 role comparison, for ``--yes`` on a matching prior, and
    (repair 3.2, FA-B2) for each ``confirmed`` entry the prior's stored value summary
    against the fresh one: ``inferred_type`` and the values of a two-valued ``split``.
    At b0f60a6 the Sepsis-shaped cohort confirmed ``a a``, then re-exported with the
    ``patient`` column holding the ten strings ``0.0`` .. ``0.9`` (``categorical; 20
    unique`` stored, ``float; 10 unique`` fresh), passed ``map --yes`` and ``run --yes``
    with exit 0, and ``Gender`` re-exported as 0/1/2 did too
    (``tests/test_mapping_repair3_2.py::test_yes_halts_h07_when_a_confirmed_columns_values_changed``
    feeds both). Compared only where both summaries hold the column
    (:func:`_summaries_agree`).

    DEC-42 (repair 4): a prior role that differs from the fresh one passes the role
    comparison when the entry is ``confirmed`` (a human accepted or edited it at the
    prompt) and both files hold a summary for the column; the summary comparison then
    decides (equal -> the choice stands; differs -> the values-changed H07). When the
    prior holds no summary for the column (a hand-authored ``file`` prior) it is the
    role-difference H07 as before. At 4fbbf35 an edit left ``confirmed`` False and
    the role difference halted the two edited files fed (``score -> attr_score_flag`` beside
    ``prob -> score`` on ``row_id,label,score,prob``:
    ``tests/test_mapping_repair4.py::test_an_edit_at_the_prompt_is_confirmed_and_passes_yes``)."""
    if not prior.all_high:
        unconfirmed = [
            r
            for r in prior.roles
            if r.role is not None and r.confidence != "high" and not r.confirmed
        ]
        if unconfirmed:
            raise HaltError(
                "H07",
                "non-interactive mode requires every mapped role at high confidence in "
                "mapping.json or confirmed at the prompt (confirmed: true)",
                {"low_or_medium": len(unconfirmed)},
            )
    # every fresh original has a prior entry: _check_prior_against_table ran first
    by_original = {p.original: p for p in prior.roles}
    for f in fresh.roles:
        p = by_original[f.original]
        if p.role == f.role:
            continue
        if p.confirmed and _summaries_agree(prior, fresh, f.original) is not None:
            # DEC-42: a human chose the role at the prompt and the file holds the
            # summary the human saw; the comparison below decides whether it still holds
            continue
        raise HaltError(
            "H07",
            f"mapping.json maps a column to {p.role_label} but the mapping computed from "
            f"this table gives it {f.role_label}; run proofpack map again",
            {"prior_role": p.role_label, "fresh_role": f.role_label},
        )
    changed = sum(
        1
        for f in fresh.roles
        if by_original[f.original].confirmed and _summaries_agree(prior, fresh, f.original) is False
    )
    if changed:
        raise HaltError(
            "H07",
            "the values of a column confirmed at the prompt changed since mapping.json was "
            "written (inferred type or the two-valued split); run proofpack map again",
            {"confirmed_columns_changed": changed},
        )
    if not fresh.all_high:
        unconfirmed = [f for f in fresh.non_high if not by_original[f.original].confirmed]
        if unconfirmed:
            raise HaltError(
                "H07",
                "non-interactive mode requires every role at high confidence in the mapping "
                "computed from this table, or confirmed at the prompt for the same column and "
                "role; run interactively",
                {"low_or_medium": len(unconfirmed)},
            )


def check_h07(
    headers: list[str],
    mapping_path: str | Path | None,
    *,
    non_interactive: bool,
    fresh: Mapping | None = None,
) -> Mapping:
    """Gate H07 and the ``--yes`` rule.

    A prior ``mapping.json`` whose hash matches is returned in either mode after
    :func:`_check_prior_against_table` (DEC-29: its entries name exactly this table's
    headers and every role is canonical or ``attr_`` / ``rater_``; DEC-31: no ignored
    column is named for a role another column holds; at 1354758 ``original:
    NOT_A_HEADER``, ``role: SECRET_ROLE_NAME`` and ``roles: []`` each passed ``map --yes``
    with exit 0 - carried 13; ``tests/test_mapping_repair3.py::
    test_yes_halts_h07_on_an_original_outside_the_header_set`` and its two siblings).
    Interactive mode without a matching prior returns the fresh mapping (the confirm step
    is the CLI's).
    Non-interactive mode additionally requires ``decided_by`` ``interactive`` or ``file``
    (a ``proposed`` file is one ``proofpack run`` wrote without a confirm step - at 555a5e1
    ``map --yes`` accepted it, repair 1, FA-N1;
    ``tests/test_mapping_repair1.py::test_yes_refuses_a_proposed_prior``) and
    :func:`_check_yes_rule` (DEC-28: every mapped role in the prior ``high`` or
    ``confirmed: true``; the prior's role for each column equal to the fresh mapping's -
    at 1354758 a prior ``age high`` on a column now holding bands passed ``map --yes`` and
    was rewritten, lens-3 FA-N2;
    ``::test_yes_halts_h07_when_the_prior_role_differs_from_the_fresh_one``);
    each confirmed entry's stored value summary equal in type and split values to the
    fresh one (repair 3.2, FA-B2 of lens 1: ``_check_yes_rule``); every fresh non-high
    role confirmed in the prior for that column. An entry edited at the prompt is
    ``confirmed`` too (DEC-42, repair 4) and its differing role stands under the same
    value-summary comparison; at 4fbbf35 it was not, and no edited file passed ``--yes``
    (open question 1 of the repair-3 note). The prior is returned with
    ``decided_by`` set to ``file`` when it was ``interactive`` or ``file``; a
    ``proposed`` prior (interactive mode only; ``--yes`` halted on it above) keeps
    ``proposed``.
    """
    current = header_set_sha256(headers)
    fresh = fresh or map_headers(headers)
    prior: Mapping | None = None
    if mapping_path is not None and Path(mapping_path).exists():
        prior = Mapping.read(mapping_path)

    if prior is not None and prior.header_set_sha256 == current:
        if non_interactive and prior.decided_by not in CONFIRMED_DECIDED_BY:
            raise HaltError(
                "H07",
                "non-interactive mode requires a confirmed mapping.json (decided_by "
                "interactive or file); this one was not confirmed: run proofpack map "
                "interactively once",
                {"decided_by": prior.decided_by[:16]},
            )
        _check_prior_against_table(prior, headers)
        if non_interactive:
            _check_yes_rule(prior, fresh)
        if prior.decided_by in CONFIRMED_DECIDED_BY:
            # a ``proposed`` prior keeps that word: at b0f60a6 ``run --mapping`` on the
            # file ``run`` had written without a prompt relabelled it ``file`` on the way
            # into the pack, and ``--yes`` then took it (lens-1 RG-N5 of repair 3;
            # tests/test_mapping_repair3_2.py::
            # test_a_proposed_prior_is_not_relabelled_file_by_run_mapping).
            # DEC-26 (E7, cmd_run) is the halt on the ``proposed`` file itself.
            prior.decided_by = "file"
        return prior

    if non_interactive:
        if prior is None:
            raise HaltError(
                "H07",
                "non-interactive mode requires an existing mapping.json; run interactively "
                "or pass --yes with a prior mapping.json",
            )
        raise HaltError(
            "H07",
            "header-set hash differs from mapping.json in non-interactive mode",
            {"expected": prior.header_set_sha256[:12], "observed": current[:12]},
        )
    return fresh


def date_like_columns(
    headers: list[str], columns: dict[str, list] | None = None, mapping: Mapping | None = None
) -> list[str]:
    """Headers gate H11 inspects: date-like by name, plus date-valued by summary."""
    out = list(date_like_headers(headers))
    if mapping is not None:
        for h in headers:
            summ = mapping.value_summaries.get(h)
            if summ and summ.get("inferred_type") == "date" and h not in out:
                out.append(h)
    elif columns is not None:
        for h in headers:
            if h in columns and h not in out:
                if profile_column(columns[h]).inferred_type == "date":
                    out.append(h)
    return out


def check_h11(
    headers: list[str],
    period: dict | None,
    *,
    columns: dict[str, list] | None = None,
    mapping: Mapping | None = None,
) -> None:
    """Gate H11: a date-like column (by header, or by values when ``columns``/``mapping``
    is given) with no ``period`` declaration covering it -> HALT.

    A column is covered when ``period.column`` equals its original header, or equals its
    mapped role while it is the only holder of that role.
    """
    dl = date_like_columns(headers, columns, mapping)
    if not dl:
        return
    if period is None:
        raise HaltError(
            "H11",
            "date-like column present with no period declaration (privacy)",
            {"date_like_columns": len(dl)},
        )
    pcol = period.get("column")

    def covered(h: str) -> bool:
        if h == pcol:
            return True
        if mapping is not None:
            role = mapping.role_of(h)
            return role is not None and role == pcol and mapping.holders(role) == [h]
        return False

    uncovered = [h for h in dl if not covered(h)]
    if uncovered:
        raise HaltError(
            "H11",
            "date-like column(s) present that the period declaration does not cover (privacy)",
            {"date_like_columns": len(uncovered)},
        )
