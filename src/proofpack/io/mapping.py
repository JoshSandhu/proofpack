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
Two headers resolving to ``case_id`` halt with E01 (DEC-11), not ``low``.

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
#: Roles for which a second name claim is a conflict (attr_/rater_ columns are their own).
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
        """Read a prior ``mapping.json``; any shape or I/O failure is H07 ``could not be read``.

        The shape checks (``header_set_sha256`` a string, each ``roles`` entry a mapping whose
        ``original`` and ``confidence`` are strings; a non-mapping file or a non-list ``roles``
        raises AttributeError/TypeError on its own) are there because at 555a5e1 a file with
        ``"roles": "x"`` or ``"header_set_sha256": 123`` reached ``--yes`` as exit 5
        ``internal error: AttributeError`` / ``TypeError`` (repair 1, FA-N6;
        ``tests/test_mapping_repair1.py::test_malformed_prior_under_yes_halts_h07_not_exit_5``).
        """
        try:
            raw = Path(path).read_bytes()
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data.get("header_set_sha256"), str):
                raise TypeError("header_set_sha256")
            roles = []
            for r in data["roles"]:
                if not isinstance(r, dict):  # a string's characters or a list's ints
                    raise TypeError("role entry")
                role = r.get("role")
                if not isinstance(r["original"], str) or not isinstance(r["confidence"], str):
                    raise TypeError("role entry fields")
                roles.append(
                    RoleMapping(
                        r["original"],
                        None if role in (None, IGNORE) else role,
                        r["confidence"],
                        r.get("source", "ignore" if role in (None, IGNORE) else "file"),
                        list(r.get("notes", [])),
                    )
                )
            m = cls(
                header_set_sha256=data["header_set_sha256"],
                roles=roles,
                decided_by=str(data.get("decided_by", "file")),
                timestamp=str(data.get("timestamp", "")),
                value_summaries=data.get("value_summaries") or {},
            )
            m.file_sha256 = hashlib.sha256(raw).hexdigest()
            return m
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
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
    if key in canon or original in canon:
        return _Claim(key if key in canon else original, "canonical")
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
    (DEC-11) when two headers resolve to ``case_id`` by name.
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
                # only); the values may repeat or not - the human decides
                notes.append("header resembles a case identifier; confirm or ignore")
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


def _decide_named(
    h: str, c: _Claim, s: ColumnSummary | None, name_holders: dict[str, list[str]]
) -> RoleMapping:
    role = c.role
    notes: list[str] = []
    holders = name_holders.get(role, [])
    if role in SINGLE_HOLDER_ROLES and len(holders) >= 2:
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


def apply_mapping(columns: dict[str, list], mapping: Mapping) -> dict[str, list]:
    """Rename original headers to canonical roles. Ignored columns keep their name."""
    out: dict[str, list] = {}
    for original, values in columns.items():
        role = mapping.role_of(original) or original
        if role in out:
            raise HaltError("H07", "two columns map to the same canonical role", {"role": role})
        out[role] = values
    return out


def check_h07(
    headers: list[str],
    mapping_path: str | Path | None,
    *,
    non_interactive: bool,
    fresh: Mapping | None = None,
) -> Mapping:
    """Gate H07 and the ``--yes`` rule.

    Interactive mode (``non_interactive=False``): return the prior mapping if its hash
    matches, otherwise the fresh mapping (the confirm step is the CLI's).
    Non-interactive mode: HALT H07 unless a prior ``mapping.json`` exists, its hash equals
    the current header set, its ``decided_by`` is ``interactive`` or ``file`` (D1 section 5
    step 5's two values; a ``proposed`` file is one ``proofpack run`` wrote without a
    confirm step - at 555a5e1 ``map --yes`` accepted such a file and rewrote it as ``file``,
    repair 1, FA-N1; ``tests/test_mapping_repair1.py::test_yes_refuses_a_proposed_prior``),
    and every mapped role is ``high`` in both the prior file and the fresh mapping computed
    from this table.
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
        if non_interactive and not prior.all_high:
            raise HaltError(
                "H07",
                "non-interactive mode requires every mapped role at high confidence",
                {"low_or_medium": sum(1 for r in prior.roles if r.confidence != "high")},
            )
        if non_interactive and not fresh.all_high:
            raise HaltError(
                "H07",
                "non-interactive mode requires every role at high confidence in the mapping "
                "computed from this table; run interactively",
                {"low_or_medium": len(fresh.non_high)},
            )
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
