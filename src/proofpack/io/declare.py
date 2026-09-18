"""``io.declare`` - load and validate ``criteria.yaml`` (D1 section 2).

Declarations are never inferred. Positive class, score orientation and type,
operating points (thresholds), intended-use prevalence and the subgroup
attribute list are MANDATORY; absence is gate H08. A criterion or fairness
block without ``author``/``date``/``justification`` is also H08. References
to unknown metric ids, operating points, attributes or levels are gate H09.

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


def metric_ids() -> frozenset[str]:
    return frozenset(load_json_schema("criteria_schema.json")["$defs"]["metric_id"]["enum"])


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


#: Separators that make a ``clustering.unit`` string name more than one column (DEC-11).
_CASE_KEY_SEPARATORS = re.compile(r"\s*(?:,|\+|&|;|\||\s+and\s+)\s*")


def _check_dec11_case_key(clustering: Any) -> None:
    """DEC-11: ``clustering.unit`` naming two or more columns halts E01, before the schema
    check would report it as an H08 type error."""
    if not isinstance(clustering, dict):
        return
    unit = clustering.get("unit")
    if isinstance(unit, (list, tuple)):
        n = len(unit)
    elif isinstance(unit, str):
        n = len([t for t in _CASE_KEY_SEPARATORS.split(unit) if t.strip()])
    else:
        return
    if n >= 2:
        raise HaltError(
            "E01",
            f"clustering.unit names {n} columns; reduce your case key to one column",
            {"n_case_key_columns": n},
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

    _check_dec11_case_key(data.get("clustering"))

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
