"""``io.mapping`` - header-only mapper stub (day 1).

Full rule-based mapping with value-level summaries and interactive acceptance is
the mapping day's work. Day 1 ships the parts gates H07 and H11 need:

* the order-independent ``header_set_sha256`` (from :mod:`proofpack.io.schema`);
* exact-name and synonym-table roles with ``high``/``medium`` confidence;
* ``mapping.json`` read/write with ``decided_by`` and the hash;
* the non-interactive acceptance rule: ``--yes`` is accepted only when every role
  is ``high`` **and** a prior ``mapping.json`` exists with the same header-set hash.

Original headers are stored in ``mapping.json`` (local only) and never leave the
machine; nothing here returns them inside an error message.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from proofpack.errors import HaltError
from proofpack.io.schema import canonical_columns, date_like_headers, header_set_sha256

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
}


@dataclass
class RoleMapping:
    original: str
    role: str | None
    confidence: str  # high | medium | low


@dataclass
class Mapping:
    header_set_sha256: str
    roles: list[RoleMapping]
    decided_by: str  # interactive | file | stub
    timestamp: str
    value_summaries: dict = field(default_factory=dict)  # suppressed aggregates; empty on day 1

    def role_of(self, original: str) -> str | None:
        for r in self.roles:
            if r.original == original:
                return r.role
        return None

    @property
    def all_high(self) -> bool:
        return all(r.confidence == "high" for r in self.roles if r.role is not None)

    def to_dict(self) -> dict:
        return {
            "header_set_sha256": self.header_set_sha256,
            "roles": [
                {"original": r.original, "role": r.role, "confidence": r.confidence}
                for r in self.roles
            ],
            "value_summaries": self.value_summaries,
            "decided_by": self.decided_by,
            "timestamp": self.timestamp,
        }

    def write(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def read(cls, path: str | Path) -> Mapping:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            return cls(
                header_set_sha256=data["header_set_sha256"],
                roles=[
                    RoleMapping(r["original"], r.get("role"), r["confidence"])
                    for r in data["roles"]
                ],
                decided_by=data.get("decided_by", "file"),
                timestamp=data.get("timestamp", ""),
                value_summaries=data.get("value_summaries", {}),
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise HaltError("H07", "mapping.json could not be read") from exc


def map_headers(headers: list[str]) -> Mapping:
    """Header-only mapping: exact canonical name -> high; synonym -> medium; else unmapped."""
    canon = set(canonical_columns())
    roles: list[RoleMapping] = []
    for h in headers:
        key = h.strip().lower()
        if h in canon or key in canon:
            roles.append(RoleMapping(h, key, "high"))
        elif key.startswith(("attr_", "rater_")):
            roles.append(RoleMapping(h, key, "high"))
        elif key in SYNONYMS:
            roles.append(RoleMapping(h, SYNONYMS[key], "medium"))
        else:
            roles.append(RoleMapping(h, None, "low"))
    return Mapping(
        header_set_sha256=header_set_sha256(headers),
        roles=roles,
        decided_by="stub",
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def apply_mapping(columns: dict[str, list], mapping: Mapping) -> dict[str, list]:
    """Rename original headers to canonical roles. Unmapped columns keep their name."""
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
    matches, otherwise the fresh header-only mapping (the interactive step is later work).
    Non-interactive mode: HALT H07 unless a prior ``mapping.json`` exists, its hash equals
    the current header set and every mapped role is ``high``.
    """
    current = header_set_sha256(headers)
    fresh = fresh or map_headers(headers)
    prior: Mapping | None = None
    if mapping_path is not None and Path(mapping_path).exists():
        prior = Mapping.read(mapping_path)

    if prior is not None and prior.header_set_sha256 == current:
        if non_interactive and not prior.all_high:
            raise HaltError(
                "H07",
                "non-interactive mode requires every mapped role at high confidence",
                {"low_or_medium": sum(1 for r in prior.roles if r.confidence != "high")},
            )
        prior.decided_by = "file"
        return prior

    if non_interactive:
        if prior is None:
            raise HaltError("H07", "non-interactive mode requires an existing mapping.json")
        raise HaltError(
            "H07",
            "header-set hash differs from mapping.json in non-interactive mode",
            {"expected": prior.header_set_sha256[:12], "observed": current[:12]},
        )
    return fresh


def check_h11(headers: list[str], period: dict | None) -> None:
    """Gate H11: any date-like column present with no ``period`` declaration -> HALT."""
    dl = date_like_headers(headers)
    if not dl:
        return
    if period is None:
        raise HaltError(
            "H11",
            "date-like column present with no period declaration (privacy)",
            {"date_like_columns": len(dl)},
        )
    uncovered = [h for h in dl if h != period.get("column")]
    if uncovered:
        raise HaltError(
            "H11",
            "date-like column(s) present that the period declaration does not cover (privacy)",
            {"date_like_columns": len(uncovered)},
        )
