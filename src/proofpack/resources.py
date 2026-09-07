"""Locate packaged schema and design files.

In a built wheel the repo's ``schema/`` directory and ``design/guidance_map_v1.csv``
are force-included as ``proofpack/_schema/``. In an editable/dev checkout we fall
back to the repository layout so the files in ``schema/`` stay the single source.
"""

from __future__ import annotations

import csv
import json
from functools import cache
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent.parent

_CANDIDATES = {
    "schema_v1.json": ["_schema/schema_v1.json", "../../schema/schema_v1.json"],
    "criteria_schema.json": ["_schema/criteria_schema.json", "../../schema/criteria_schema.json"],
    "claims_schema.json": ["_schema/claims_schema.json", "../../schema/claims_schema.json"],
    "egress_schema.json": ["_schema/egress_schema.json", "../../schema/egress_schema.json"],
    "guidance_map_v1.csv": ["_schema/guidance_map_v1.csv", "../../design/guidance_map_v1.csv"],
}


def resource_path(name: str) -> Path:
    for rel in _CANDIDATES[name]:
        p = (_PKG_DIR / rel).resolve()
        if p.exists():
            return p
    raise FileNotFoundError(f"packaged resource {name!r} not found")


@cache
def load_json_schema(name: str) -> dict:
    with resource_path(name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


@cache
def load_guidance_map() -> tuple[dict[str, str], ...]:
    with resource_path("guidance_map_v1.csv").open("r", encoding="utf-8", newline="") as fh:
        return tuple(csv.DictReader(fh))


def guidance_ids() -> frozenset[str]:
    return frozenset(row["internal_id"] for row in load_guidance_map())
