"""The header and key whitelist (D1 section 6, "Aggregate payload rules", first and
fourth bullets): *only keys present in ``egress_schema.json``*; *only canonical names
matching ``^[a-z][a-z0-9_]{0,31}$`` from the schema; original headers never serialised*.

:func:`project` walks a candidate document against one definition of ``schema/
egress_schema.json`` and returns a new document that carries **only** what the schema
names:

- an object keeps the keys its ``properties`` list and drops every other key - dropped,
  not passed and not reported, because the schema is the whole vocabulary;
- a string must match the subschema's ``enum``, ``const`` or ``pattern`` (``re.fullmatch``,
  so a trailing newline that ``re.search``'s ``$`` accepts is refused -
  ``tests/test_egress.py::test_whitelist_refuses_a_trailing_newline_that_re_search_accepts``)
  and its ``maxLength``; a string that does not is refused with :class:`WhitelistError`,
  and so is a string the subschema does not constrain at all - a schema that admitted an
  unconstrained string would admit an original header, so it is the schema that is refused
  there, not the value;
- arrays are projected item by item; numbers, booleans and null pass; a value of a type
  the subschema does not allow is refused.

The projection is generic: it reads the schema and the candidate, not the engine. What
it keeps is decided by the schema's keys and patterns alone. ``tests/test_egress.py::
test_f19_the_forbidden_bytes_are_absent_from_both_payloads_and_the_captured_bytes`` feeds
the F19 run and asserts fourteen named strings, four site labels and 400 ROC thresholds
absent from the projected bytes; a level of an attribute outside ``site``/``device``/
``protocol``/``attr_*`` that matches the ``level`` pattern's token branch does survive
(``pseudonymise.py``,
``test_a_date_shaped_level_of_the_sex_column_passes_the_token_rule_verbatim``).
``build.py`` then validates the projected document with ``jsonschema`` as a second,
independent check.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from proofpack.errors import ProofPackError


class WhitelistError(ProofPackError):
    """A value the schema does not admit reached the projection. Typed, never a send."""

    exit_code = 5

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"egress whitelist refused {path}: {reason}")


def _resolve(schema_root: Mapping[str, Any], sub: Mapping[str, Any]) -> Mapping[str, Any]:
    ref = sub.get("$ref")
    if ref is None:
        return sub
    if not ref.startswith("#/"):
        raise WhitelistError("$ref", f"only local references are followed, not {ref!r}")
    node: Any = schema_root
    for part in ref[2:].split("/"):
        node = node[part]
    return _resolve(schema_root, node)


def _types(sub: Mapping[str, Any]) -> set[str]:
    t = sub.get("type")
    if t is None:
        if "const" in sub:
            return {"string" if isinstance(sub["const"], str) else "any"}
        if "enum" in sub:
            return {"string", "null"}
        if "properties" in sub:
            return {"object"}
        if "items" in sub:
            return {"array"}
        return {"any"}
    return {t} if isinstance(t, str) else set(t)


def project(
    value: Any, schema_root: Mapping[str, Any], sub: Mapping[str, Any], path: str = "$"
) -> Any:
    """Project ``value`` onto ``sub`` (a subschema of ``schema_root``). See the module."""
    sub = _resolve(schema_root, sub)
    allowed = _types(sub)
    if value is None:
        if "null" in allowed or "any" in allowed or None in sub.get("enum", ()):
            return None
        raise WhitelistError(path, "null is not admitted here")
    if isinstance(value, bool):
        if "boolean" in allowed or "any" in allowed:
            return value
        raise WhitelistError(path, "a boolean is not admitted here")
    if isinstance(value, int | float):
        if (
            "number" in allowed
            or "any" in allowed
            or ("integer" in allowed and isinstance(value, int))
        ):
            return value
        raise WhitelistError(path, f"a {type(value).__name__} is not admitted here")
    if isinstance(value, str):
        if "string" not in allowed and "any" not in allowed:
            raise WhitelistError(path, "a string is not admitted here")
        if "const" in sub:
            if value != sub["const"]:
                raise WhitelistError(path, "the string is not the schema's constant")
            return value
        if "enum" in sub:
            if value not in sub["enum"]:
                raise WhitelistError(path, "the string is not in the schema's enum")
            return value
        if "pattern" in sub:
            if "maxLength" in sub and len(value) > sub["maxLength"]:
                raise WhitelistError(path, "the string is longer than the schema allows")
            if not re.fullmatch(sub["pattern"], value):
                raise WhitelistError(path, "the string does not match the schema's pattern")
            return value
        raise WhitelistError(path, "the schema does not constrain this string; refused")
    if isinstance(value, Mapping):
        if "object" not in allowed and "any" not in allowed:
            raise WhitelistError(path, "an object is not admitted here")
        props = sub.get("properties", {})
        out: dict[str, Any] = {}
        for key, subschema in props.items():
            if key in value:
                out[key] = project(value[key], schema_root, subschema, f"{path}.{key}")
        # every key of ``value`` that is not in ``props`` is dropped here
        return out
    if isinstance(value, list | tuple):
        if "array" not in allowed and "any" not in allowed:
            raise WhitelistError(path, "an array is not admitted here")
        items = sub.get("items")
        if items is None:
            raise WhitelistError(path, "the schema does not constrain this array's items")
        return [project(v, schema_root, items, f"{path}[{i}]") for i, v in enumerate(value)]
    raise WhitelistError(path, f"a {type(value).__name__} is not admitted anywhere")


def keys_named(schema_root: Mapping[str, Any]) -> set[str]:
    """Every property name the schema names anywhere; a payload key outside this set
    could only have come from somewhere other than the projection."""
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for k, v in node.items():
                if k == "properties" and isinstance(v, Mapping):
                    found.update(v.keys())
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema_root)
    return found
