"""``io.declare`` - load and validate ``criteria.yaml`` (D1 section 2).

Declarations are never inferred. Positive class, score orientation and type,
operating points (thresholds), intended-use prevalence and the subgroup
attribute list are MANDATORY; absence is gate H08. A criterion or fairness
block without ``author``/``date``/``justification`` is also H08. DEC-65's control-character
halt and the self-reference halt are described at :func:`_check_control_characters`,
with the literal inputs the tests feed. References to unknown metric ids, operating
points, attributes or levels are gate H09.

The engine supplies no default for anything a customer must own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from proofpack.errors import HaltError
from proofpack.resources import load_json_schema

MANDATORY_BLOCKS: tuple[str, ...] = (
    "classes",
    "score",
    "operating_points",
    "prevalence",
    "subgroups",
)

#: Additional blocks that D1 section 5.4 says are declared, never inferred.
DECLARED_BLOCKS: tuple[str, ...] = ("reference_standard", "indeterminates", "clustering")

AUTHORED_FIELDS: tuple[str, ...] = ("author", "date", "justification")
#: Operating-point ids the run document uses as keys beside the operating points (repair
#: 3 of build day 8, lens FA-B3 at 7fa690b): ``overall.threshold_free``, and ``auroc`` /
#: ``brier`` in each subgroup row's ``metrics``. An operating point declared with one of
#: these ids is H08 (``tests/test_e8_repair3.py::
#: test_an_operating_point_id_the_document_reserves_halts_h08``).
RESERVED_OPERATING_POINT_IDS: frozenset[str] = frozenset({"threshold_free", "auroc", "brier"})

#: DEC-65 (repair 5 of build day 8, lens-5 FA5-B4 at 375719c). :data:`_CONTROL` matches
#: U+0000 to U+001F, U+007F and U+0080 to U+009F; :data:`_CONTROL_MULTILINE` is the same
#: set less tab (U+0009) and line feed (U+000A). :func:`control_character_at` applies the
#: second to a string held directly under one of these three keys (the names D1 section
#: 6 gives the free-text declaration fields) and the first to every other string and to
#: every key. What ``validate_dict`` does with a hit, and the halts that come before it,
#: are at :func:`_check_control_characters`.
MULTILINE_FIELDS: frozenset[str] = frozenset({"justification", "description", "source"})
_CONTROL = re.compile("[\x00-\x1f\x7f-\x9f]")
_CONTROL_MULTILINE = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def _path_text(path: tuple[Any, ...]) -> str:
    """A path as the schema halt writes it (``criteria/0/justification``)."""
    return "/".join(str(p) for p in path) or "<root>"


def _string_hit(text: str, path: tuple[Any, ...]) -> tuple[str, str] | None:
    key = path[-1] if path else None
    rx = _CONTROL_MULTILINE if key in MULTILINE_FIELDS else _CONTROL
    m = rx.search(text)
    if m is None:
        return None
    return _path_text(path), f"U+{ord(m.group()):04X}"


def _children(container: Any, path: tuple[Any, ...]):
    """``(child path, is a mapping item, key, value)`` for each item, in document order."""
    if isinstance(container, dict):
        return (((*path, k), True, k, v) for k, v in container.items())
    return (((*path, i), False, i, v) for i, v in enumerate(container))


def control_character_at(value: Any, path: tuple[Any, ...] = ()) -> tuple[str, str] | None:
    """The first ``(field path, "U+XXXX")`` whose string holds a character that
    :data:`_CONTROL` (or, under a key in :data:`MULTILINE_FIELDS`, :data:`_CONTROL_MULTILINE`)
    matches, walking each mapping item (its key, then its value) and each list item in
    document order, depth first; ``None`` when the walk ends without a match.
    The path is written as the schema halt writes it (``criteria/0/justification``); a key
    is named by its parent's path and ``(key)``. The value itself is not returned.

    The walk keeps its own stack (no recursion) and enters each list or mapping object
    once, by ``id``; a second reference to one (a YAML alias) is not walked again.
    Repair 6 of build day 8, lens-6 RG-B1 / FA-N4: at ea2f743 the walk recursed with no
    record of what it had entered, and ``zz_extra: &a [*a]`` as line 1 of a valid
    ``criteria.yaml`` ended ``internal error: RecursionError`` (exit 5); an alias chain
    20 levels deep (1,048,576 leaves) took 0.51 s.
    ``tests/test_e8_repair6.py::test_an_alias_chain_24_deep_is_walked_in_under_two_seconds``
    feeds a chain 24 deep."""
    if isinstance(value, str):
        return _string_hit(value, path)
    if not isinstance(value, (dict, list, tuple)):
        return None
    entered = {id(value)}
    stack = [(path, _children(value, path))]
    while stack:
        parent, children = stack[-1]
        item = next(children, None)
        if item is None:
            stack.pop()
            continue
        child_path, is_mapping_item, k, v = item
        if is_mapping_item:
            if isinstance(k, str) and _CONTROL.search(k):
                return f"{_path_text(parent)} (key)", f"U+{ord(_CONTROL.search(k).group()):04X}"
        if isinstance(v, str):
            found = _string_hit(v, child_path)
            if found is not None:
                return found
        elif isinstance(v, (dict, list, tuple)) and id(v) not in entered:
            entered.add(id(v))
            stack.append((child_path, _children(v, child_path)))
    return None


def self_reference_at(value: Any) -> str | None:
    """The path of the first item, in document order, that is a list or mapping object
    enclosing it - what PyYAML's ``safe_load`` builds from an alias inside its own anchor
    (``zz_extra: &a [*a]`` loads as a list whose item 0 is that list: ``zz_extra/0``).
    ``None`` when the walk ends without one. No recursion; each object is entered once."""
    if not isinstance(value, (dict, list, tuple)):
        return None
    open_ids = {id(value)}
    finished: set[int] = set()
    stack = [(id(value), _children(value, ()))]
    while stack:
        oid, children = stack[-1]
        item = next(children, None)
        if item is None:
            stack.pop()
            open_ids.discard(oid)
            finished.add(oid)
            continue
        child_path, _is_mapping_item, _k, v = item
        if isinstance(v, (dict, list, tuple)):
            vid = id(v)
            if vid in open_ids:
                return _path_text(child_path)
            if vid not in finished:
                open_ids.add(vid)
                stack.append((vid, _children(v, child_path)))
    return None


def _check_control_characters(data: dict[str, Any]) -> None:
    """Two H08 halts on the parsed document, in this order.

    1. :func:`self_reference_at`: ``declaration invalid at <path>: the value contains
       itself (a YAML alias inside its own anchor); remove the alias``, detail
       ``{"field", "reason": "self_reference"}``. ``tests/test_e8_repair6.py`` feeds
       ``&a [*a]`` as ``zz_extra`` at the root, as ``extra`` under ``model`` and as
       ``extra`` in ``criteria[0]`` (exit 5 at ea2f743 in each; lens-6 RG-B1).
    2. DEC-65, :func:`control_character_at`: ``declaration invalid at <path>: control
       character U+XXXX; remove it``, detail ``{"field", "reason": "control_character",
       "codepoint"}``. ``tests/test_e8_repair5.py`` names the 43 fields and 14 literals it
       feeds, and the tab and line feed it feeds to ``justification``, ``description`` and
       ``source`` (accepted there).

    ``validate_dict`` runs this after the mandatory-block H08s and DEC-11's E01. Two
    documents the tests feed halt before it: ``Tri\\x00age`` as the model name with the
    ``prevalence`` block removed halts ``mandatory declaration block(s) missing:
    prevalence`` (``tests/test_e8_repair6.py::
    test_a_missing_block_halts_before_the_control_character_walk``), and U+0001 after the
    first character of ``clustering.unit`` halts E01 (``tests/test_e8_repair5.py::
    test_u0001_in_each_string_field_of_the_criteria_document_halts``)."""
    cycle = self_reference_at(data)
    if cycle is not None:
        raise HaltError(
            "H08",
            f"declaration invalid at {cycle}: the value contains itself (a YAML alias inside "
            "its own anchor); remove the alias",
            {"field": cycle, "reason": "self_reference"},
        )
    found = control_character_at(data)
    if found is not None:
        field_path, codepoint = found
        raise HaltError(
            "H08",
            f"declaration invalid at {field_path}: control character {codepoint}; remove it",
            {"field": field_path, "reason": "control_character", "codepoint": codepoint},
        )


def metric_ids() -> frozenset[str]:
    return frozenset(load_json_schema("criteria_schema.json")["$defs"]["metric_id"]["enum"])


def metric_needs_operating_point(metric: str) -> bool:
    """Whether a criterion on ``metric`` is read at an operating point (E7, ``criteria``)."""
    from proofpack.criteria import needs_operating_point

    return needs_operating_point(metric)


@dataclass
class OperatingPoint:
    id: str
    threshold: float
    rule: str
    provenance: str
    source: str | None = None

    def is_positive(self, score: float) -> bool:
        if self.rule == ">=":
            return score >= self.threshold
        if self.rule == ">":
            return score > self.threshold
        if self.rule == "<=":
            return score <= self.threshold
        if self.rule == "<":
            return score < self.threshold
        raise ValueError(self.rule)


@dataclass
class Declarations:
    """Typed view over a validated ``criteria.yaml``; ``raw`` is echoed verbatim in T8."""

    raw: dict[str, Any]
    positive: str
    negative: str
    score_type: str
    orientation: str
    operating_points: list[OperatingPoint]
    indeterminate_values: set[str]
    indeterminate_policy: str
    reference_standard_type: str
    clustering_unit: str
    prevalence: list[dict[str, Any]]
    subgroups: list[dict[str, Any]]
    criteria: list[dict[str, Any]] = field(default_factory=list)
    fairness: dict[str, Any] | None = None
    period: dict[str, Any] | None = None
    egress: dict[str, Any] = field(default_factory=dict)
    bootstrap: dict[str, Any] = field(default_factory=dict)

    @property
    def classes(self) -> set[str]:
        return {self.positive, self.negative}

    def operating_point(self, op_id: str) -> OperatingPoint | None:
        for op in self.operating_points:
            if op.id == op_id:
                return op
        return None

    @property
    def subgroup_attributes(self) -> list[str]:
        return [s["attribute"] for s in self.subgroups]

    def age_bands(self) -> list[list[float]] | None:
        for s in self.subgroups:
            if s["attribute"] == "age":
                return s.get("bands")
        return None


def _label(v: Any) -> str:
    """Declared class labels are compared as trimmed strings against table cells."""
    if isinstance(v, bool):
        return "1" if v else "0"
    return str(v).strip()


def load_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    try:
        with p.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        raise HaltError("H08", f"criteria file could not be read: {type(exc).__name__}") from exc
    if not isinstance(data, dict):
        raise HaltError("H08", "criteria file must be a YAML mapping")
    return data


def _h08_from_schema_error(err: jsonschema.ValidationError) -> HaltError:
    path = "/".join(str(x) for x in err.absolute_path) or "<root>"
    # jsonschema messages can echo the offending *value*; keep only the validator and path.
    return HaltError(
        "H08",
        f"declaration invalid at {path}: {err.validator}",
        {"path": path, "validator": err.validator},
    )


#: What splits a ``clustering.unit`` string into column names (DEC-11): the word
#: `` and `` and any run of characters outside ``[A-Za-z0-9_]`` (so ``,`` ``+`` ``&`` ``;``
#: ``|`` ``/`` ``:`` ``-`` a space and a tab all split; at 555a5e1 only the first five and
#: `` and `` did, and ``subject_id/hadm_id`` fell through to the schema's H08 enum halt -
#: repair 1, FA-B2 / RG-NB-2). A hyphenated single name such as ``patient-id`` therefore
#: also counts two tokens; ``tests/test_mapping_repair1.py::
#: test_separators_the_lens_listed_reach_e01`` and ``tests/test_mapping_full.py::
#: test_composite_clustering_unit_halts_e01_before_the_schema_check`` list the literal
#: strings fed and the count each one yields.
_CASE_KEY_SEPARATORS = re.compile(r"\s+[Aa][Nn][Dd]\s+|[^A-Za-z0-9_]+")
#: ``clustering`` keys other than ``unit`` whose list value is read as a case key.
_CASE_KEY_LIST_KEYS: tuple[str, ...] = ("columns", "column", "key", "keys", "units", "fields")


def _check_dec11_case_key(clustering: Any) -> None:
    """DEC-11: halt E01 (message ending ``reduce your case key to one column``) when
    ``clustering.unit`` is a list of two or more, or a string that splits into two or more
    tokens on :data:`_CASE_KEY_SEPARATORS`, or when one of :data:`_CASE_KEY_LIST_KEYS`
    holds a list of two or more or a string that splits into two or more tokens the same
    way (repair 2, FA-N8: at e92989b ``columns: "subject_id, hadm_id"`` passed and
    ``unit: "a AND b"`` counted three tokens;
    ``tests/test_mapping_repair2.py::test_list_key_strings_and_upper_case_and_reach_e01``).
    Runs before the jsonschema step, which would otherwise report the string as an H08
    enum error naming no fix."""
    if not isinstance(clustering, dict):
        return
    unit = clustering.get("unit")
    n = 0
    if isinstance(unit, (list, tuple)):
        n = len(unit)
    elif isinstance(unit, str):
        n = len([t for t in _CASE_KEY_SEPARATORS.split(unit) if t])
    if n >= 2:
        raise HaltError(
            "E01",
            f"clustering.unit names {n} columns; reduce your case key to one column",
            {"n_case_key_columns": n},
        )
    for key in _CASE_KEY_LIST_KEYS:
        value = clustering.get(key)
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            raise HaltError(
                "E01",
                f"clustering.{key} lists {len(value)} columns; reduce your case key to one column",
                {"n_case_key_columns": len(value), "key": key},
            )
        if isinstance(value, str):
            n = len([t for t in _CASE_KEY_SEPARATORS.split(value) if t])
            if n >= 2:
                raise HaltError(
                    "E01",
                    f"clustering.{key} names {n} columns; reduce your case key to one column",
                    {"n_case_key_columns": n, "key": key},
                )


def validate_dict(data: dict[str, Any]) -> Declarations:
    """Validate a criteria mapping and return :class:`Declarations`.

    Raises H08 for missing/malformed mandatory declarations and H09 for
    references to unknown metric ids or operating points. Attribute/level
    references need the table and are checked in :func:`check_references`.
    """
    if not isinstance(data, dict):
        raise HaltError("H08", "criteria must be a mapping")

    missing = [b for b in MANDATORY_BLOCKS if b not in data or data[b] in (None, {}, [])]
    if missing:
        raise HaltError(
            "H08",
            "mandatory declaration block(s) missing: " + ", ".join(missing),
            {"missing": missing},
        )
    missing_declared = [b for b in DECLARED_BLOCKS if b not in data or data[b] in (None, {})]
    if missing_declared:
        raise HaltError(
            "H08",
            "declared-never-inferred block(s) missing: " + ", ".join(missing_declared),
            {"missing": missing_declared},
        )

    # DEC-11's E01 first (a tab in clustering.unit is a separator there:
    # tests/test_mapping_repair1.py::test_separators_the_lens_listed_reach_e01), then the
    # self-reference and DEC-65 halts, above the lines below that print a criterion id
    _check_dec11_case_key(data.get("clustering"))
    _check_control_characters(data)

    # authored fields first so the message is specific (D1 section 2 rule)
    criteria_block = data.get("criteria") or []
    if not isinstance(criteria_block, list):
        raise HaltError("H08", "criteria block must be a list")
    for i, c in enumerate(criteria_block):
        if not isinstance(c, dict):
            raise HaltError("H08", f"criteria[{i}] is not a mapping")
        empty = [f for f in AUTHORED_FIELDS if not str(c.get(f) or "").strip()]
        if empty:
            raise HaltError(
                "H08",
                f"criterion {c.get('id', i)!s} lacks {', '.join(empty)}",
                {"criterion": str(c.get("id", i)), "missing": empty},
            )
    fairness = data.get("fairness")
    if fairness is not None:
        if not isinstance(fairness, dict):
            raise HaltError("H08", "fairness block is not a mapping")
        empty = [f for f in AUTHORED_FIELDS if not str(fairness.get(f) or "").strip()]
        if empty:
            raise HaltError("H08", "fairness block lacks " + ", ".join(empty), {"missing": empty})
        if fairness.get("bound") is not None:
            # E7: a bound is compared the way a criterion is, with the statistic and the
            # comparator the customer wrote beside it; the engine supplies neither
            lacking = [f for f in ("statistic", "comparator") if fairness.get(f) is None]
            if lacking:
                raise HaltError(
                    "H08",
                    "fairness block declares a bound but lacks " + ", ".join(lacking),
                    {"missing": lacking},
                )

    schema = load_json_schema("criteria_schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        raise _h08_from_schema_error(errors[0])

    ops = [
        OperatingPoint(
            id=str(op["id"]),
            threshold=float(op["threshold"]),
            rule=op["rule"],
            provenance=op["provenance"],
            source=op.get("source"),
        )
        for op in data["operating_points"]
    ]
    op_ids = [op.id for op in ops]
    if len(set(op_ids)) != len(op_ids):
        raise HaltError("H08", "operating point ids are not unique")
    reserved = [i for i in op_ids if i in RESERVED_OPERATING_POINT_IDS]
    if reserved:
        raise HaltError(
            "H08",
            "operating point id is a key the run document reserves: " + ", ".join(reserved),
            {"field": "operating_points", "reserved": reserved},
        )

    known_metrics = metric_ids()
    for c in criteria_block:
        if c["metric"] not in known_metrics:
            raise HaltError(
                "H09",
                f"criterion {c['id']} references unknown metric",
                {"criterion": str(c["id"]), "field": "metric"},
            )
        op_ref = c.get("operating_point")
        if op_ref is not None and str(op_ref) not in op_ids:
            raise HaltError(
                "H09",
                f"criterion {c['id']} references unknown operating point",
                {"criterion": str(c["id"]), "field": "operating_point"},
            )
        # E7: a threshold metric is read at one operating point and a threshold-free one
        # (auroc, brier, ...) at none; the pairing is checked here, at declaration time,
        # rather than surfacing as a not_assessable row (D1 section 5 H09: "unknown
        # metric/operating point")
        threshold = metric_needs_operating_point(c["metric"])
        if threshold and op_ref is None:
            raise HaltError(
                "H09",
                f"criterion {c['id']} names a threshold metric without an operating point",
                {"criterion": str(c["id"]), "field": "operating_point", "metric": c["metric"]},
            )
        if not threshold and op_ref is not None:
            raise HaltError(
                "H09",
                f"criterion {c['id']} names an operating point for a threshold-free metric",
                {"criterion": str(c["id"]), "field": "operating_point", "metric": c["metric"]},
            )

    pos, neg = _label(data["classes"]["positive"]), _label(data["classes"]["negative"])
    if pos == neg:
        raise HaltError("H08", "classes.positive and classes.negative are identical")
    indet_vals = {_label(v) for v in (data["indeterminates"].get("values") or [])}
    if indet_vals & {pos, neg}:
        raise HaltError("H08", "an indeterminate value coincides with a declared class")

    sub_attrs = [s["attribute"] for s in data["subgroups"]]
    if len(set(sub_attrs)) != len(sub_attrs):
        raise HaltError("H08", "subgroup attributes are not unique")

    return Declarations(
        raw=data,
        positive=pos,
        negative=neg,
        score_type=data["score"]["type"],
        orientation=data["score"]["orientation"],
        operating_points=ops,
        indeterminate_values=indet_vals,
        indeterminate_policy=data["indeterminates"]["policy"],
        reference_standard_type=data["reference_standard"]["type"],
        clustering_unit=data["clustering"]["unit"],
        prevalence=list(data["prevalence"]),
        subgroups=list(data["subgroups"]),
        criteria=list(data.get("criteria") or []),
        fairness=fairness,
        period=data.get("period"),
        egress=dict(data.get("egress") or {}),
        bootstrap=dict(data.get("bootstrap") or {}),
    )


def load(path: str | Path) -> Declarations:
    return validate_dict(load_yaml(path))


def check_references(
    decl: Declarations, table_attributes: dict[str, list[str]], has_age: bool
) -> None:
    """Gate H09 for attribute/level references, and H08 for numeric attributes without bands.

    ``table_attributes`` maps attribute name -> observed levels.
    """
    available = set(table_attributes) | ({"age"} if has_age else set())
    for s in decl.subgroups:
        a = s["attribute"]
        if a not in available:
            raise HaltError(
                "H09",
                "subgroup declaration references attribute absent from the table",
                {"attribute": a},
            )
        if a == "age" and has_age and "age" not in table_attributes and not s.get("bands"):
            raise HaltError(
                "H08", "numeric age column present but no age bands declared", {"attribute": a}
            )
        ref = s.get("reference_level")
        if ref is not None and ref != "largest" and a in table_attributes:
            if _label(ref) not in table_attributes[a]:
                raise HaltError(
                    "H09",
                    "subgroup reference_level is not an observed level",
                    {"attribute": a},
                )
    for c in decl.criteria:
        scope = c.get("scope", "overall")
        if isinstance(scope, dict):
            a = scope["attribute"]
            if a not in available:
                raise HaltError(
                    "H09",
                    f"criterion {c['id']} references unknown attribute",
                    {"criterion": str(c["id"]), "attribute": a},
                )
            lvl = _label(scope["level"])
            if lvl != "*" and a in table_attributes and lvl not in table_attributes[a]:
                raise HaltError(
                    "H09",
                    f"criterion {c['id']} references unknown level",
                    {"criterion": str(c["id"]), "attribute": a},
                )
    if decl.fairness is not None:
        a = decl.fairness["attribute"]
        if a not in available:
            raise HaltError(
                "H09",
                "fairness block references attribute absent from the table",
                {"attribute": a},
            )
