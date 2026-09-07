"""HALT gates H01-H12 (D1 section 5.6) and the ingest pipeline that runs them.

Order of evaluation in :func:`ingest`:

1. H11 (date column without period declaration) - on raw headers, before typing.
2. H07 (mapping hash, non-interactive rule) - on raw headers.
3. schema typing (S-codes).
4. H02, H03, H05, H06, H01, H04 - on the typed table.
5. H09 (attribute/level references) and H08 (bands) - declarations vs table.
6. H10 - prevalence flag (warning only).

H12 is a ``compare``-only gate and lives in :func:`check_paired`.
No document is ever written by anything in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from proofpack.errors import Finding, HaltError
from proofpack.io import declare as declare_mod
from proofpack.io import mapping as mapping_mod
from proofpack.io import schema as schema_mod
from proofpack.io.declare import Declarations
from proofpack.io.schema import RawTable, Table

# --------------------------------------------------------------------------- helpers


def auroc_mann_whitney(scores: np.ndarray, positives: np.ndarray) -> float:
    """AUROC by Mann-Whitney placement with midranks for ties (numpy only).

    ``positives`` is a boolean mask. Requires at least one positive and one negative.
    """
    scores = np.asarray(scores, dtype=np.float64)
    pos = np.asarray(positives, dtype=bool)
    n1 = int(pos.sum())
    n0 = int((~pos).sum())
    if n1 == 0 or n0 == 0:
        raise ValueError("AUROC needs both classes")
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    ranks = np.empty(len(scores), dtype=np.float64)
    # midranks: average rank within tie groups
    i = 0
    n = len(scores)
    while i < n:
        j = i
        while j + 1 < n and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j + 2) / 2.0  # 1-based average
        i = j + 1
    rank_sum_pos = ranks[pos].sum()
    return float((rank_sum_pos - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def _oriented(scores: np.ndarray, orientation: str) -> np.ndarray:
    return scores if orientation == "higher_is_positive" else -scores


# --------------------------------------------------------------------------- gates


def gate_h02(table: Table, decl: Declarations) -> None:
    allowed = decl.classes | decl.indeterminate_values
    observed = {v for v in table.y_true.tolist() if v is not None}
    unknown = observed - allowed
    if unknown:
        raise HaltError(
            "H02",
            "y_true contains value(s) outside declared classes and indeterminate values",
            {"n_unknown_values": len(unknown), "n_declared": len(allowed)},
        )


def gate_h03(table: Table, decl: Declarations) -> None:
    if decl.score_type != "probability" or table.score is None:
        return
    s = table.score[~np.isnan(table.score)]
    bad = int(((s < 0.0) | (s > 1.0)).sum())
    if bad:
        raise HaltError(
            "H03", "score.type is probability but values lie outside [0, 1]", {"count": bad}
        )


def gate_h04(table: Table, decl: Declarations, mask: np.ndarray) -> None:
    if table.y_pred is None or table.score is None:
        return
    yp = table.y_pred
    for op in decl.operating_points:
        mismatch = 0
        for i in np.flatnonzero(mask):
            p = yp[i]
            if p is None or p in decl.indeterminate_values:
                continue
            sc = table.score[i]
            expected = decl.positive if op.is_positive(sc) else decl.negative
            if p != expected:
                mismatch += 1
        if mismatch:
            raise HaltError(
                "H04",
                f"y_pred not reproducible from score at operating point {op.id}",
                {"operating_point": op.id, "mismatching_rows": mismatch},
            )


def gate_h05(table: Table, decl: Declarations) -> None:
    if table.row_id is not None:
        ids = [v for v in table.row_id.tolist() if v is not None]
        dup = len(ids) - len(set(ids))
        if dup:
            raise HaltError("H05", "duplicate row_id values", {"duplicates": dup})
    if table.case_id is not None and decl.clustering_unit == "none":
        seen: dict[str, str] = {}
        conflicts = 0
        for cid, yt in zip(table.case_id.tolist(), table.y_true.tolist(), strict=True):
            if cid is None or yt is None:
                continue
            if cid in seen and seen[cid] != yt:
                conflicts += 1
            seen.setdefault(cid, yt)
        if conflicts:
            raise HaltError(
                "H05",
                "duplicate case_id rows with conflicting y_true while clustering.unit is none",
                {"conflicting_rows": conflicts},
            )


def gate_h06(table: Table, decl: Declarations, mask: np.ndarray) -> list[Finding]:
    yt = table.y_true[mask]
    n_pos = int(sum(1 for v in yt.tolist() if v == decl.positive))
    n_neg = int(sum(1 for v in yt.tolist() if v == decl.negative))
    if mask.sum() == 0:
        raise HaltError("H06", "no analysable rows after exclusions", {"n": 0})
    if n_pos == 0 or n_neg == 0:
        raise HaltError("H06", "single-class dataset", {"n_positive": n_pos, "n_negative": n_neg})
    warnings: list[Finding] = []
    if "site" in table.attributes:
        sites = table.attributes["site"][mask]
        single = 0
        for s in sorted({str(v) for v in sites.tolist()}):
            sel = sites == s
            vals = {v for v in yt[sel].tolist()}
            if len(vals & decl.classes) < 2:
                single += 1
        if single:
            warnings.append(
                Finding(
                    "W06",
                    "single-class site(s) present; site-level metrics limited",
                    {"single_class_sites": single},
                )
            )
    return warnings


def gate_h01(table: Table, decl: Declarations, mask: np.ndarray) -> float | None:
    if table.score is None:
        return None
    yt = table.y_true[mask]
    pos = np.array([v == decl.positive for v in yt.tolist()], dtype=bool)
    auc = auroc_mann_whitney(_oriented(table.score[mask], decl.orientation), pos)
    if auc < 0.5:
        raise HaltError(
            "H01",
            "declared orientation contradicts data; check score.orientation / classes.positive",
            {"auroc_declared_orientation": round(auc, 4)},
        )
    return auc


def gate_h10(table: Table, decl: Declarations, mask: np.ndarray) -> list[Finding]:
    yt = table.y_true[mask]
    n_pos = sum(1 for v in yt.tolist() if v == decl.positive)
    n = int(mask.sum())
    if n == 0:
        return []
    observed = n_pos / n
    out: list[Finding] = []
    for entry in decl.prevalence:
        if abs(observed - float(entry["value"])) > 0.10:
            out.append(
                Finding(
                    "W10",
                    "observed prevalence differs from declared intended-use prevalence by "
                    "> 0.10 absolute; PPV/NPV will also be computed at declared prevalence",
                    {
                        "label": entry["label"],
                        "observed": round(observed, 4),
                        "declared": float(entry["value"]),
                    },
                )
            )
    return out


def check_paired(new: Table, prior: Table, *, allow_unpaired: bool = False) -> Finding | None:
    """Gate H12: paired ``compare`` requires matched ``row_id`` sets."""
    if new.row_id is None or prior.row_id is None:
        raise HaltError("H12", "paired compare requires row_id in both tables")
    a = {v for v in new.row_id.tolist() if v is not None}
    b = {v for v in prior.row_id.tolist() if v is not None}
    unmatched = len(a ^ b)
    if unmatched == 0:
        return None
    if allow_unpaired:
        return Finding(
            "W12",
            "unmatched row_ids; unpaired methods used, labelled not like-for-like",
            {"unmatched": unmatched},
        )
    raise HaltError("H12", "paired compare with unmatched row_ids", {"unmatched": unmatched})


# --------------------------------------------------------------------------- pipeline


@dataclass
class IngestResult:
    table: Table
    declarations: Declarations
    mapping: mapping_mod.Mapping
    mask: np.ndarray
    warnings: list[Finding] = field(default_factory=list)
    auroc_check: float | None = None

    @property
    def exit_code(self) -> int:
        from proofpack.errors import EXIT_OK, EXIT_WARNINGS

        return EXIT_WARNINGS if self.warnings else EXIT_OK

    def report(self) -> dict:
        """Aggregate-only ingest report (safe to write locally; never egressed as-is)."""
        t = self.table
        return {
            "schema_version": 1,
            "header_set_sha256": t.header_set_sha256,
            "n_rows": t.n_rows,
            "flow": t.flow.as_dict() if t.flow else None,
            "roles_present": sorted(r.role for r in self.mapping.roles if r.role is not None),
            "n_unused_columns": len(t.unused_columns),
            "n_rater_columns": len(t.rater_columns),
            "attributes": sorted(t.attributes),
            "declared": {
                "positive": self.declarations.positive,
                "orientation": self.declarations.orientation,
                "score_type": self.declarations.score_type,
                "operating_points": [op.id for op in self.declarations.operating_points],
                "clustering_unit": self.declarations.clustering_unit,
            },
            "warnings": [
                {"code": w.code, "message": w.message, "detail": w.detail} for w in self.warnings
            ],
            "halt_code": None,
        }


def ingest(
    raw: RawTable,
    decl: Declarations,
    *,
    mapping_path: str | Path | None = None,
    non_interactive: bool = False,
) -> IngestResult:
    """Run mapping, typing and every HALT gate. Raises :class:`HaltError`; writes nothing."""
    mapping_mod.check_h11(raw.headers, decl.period)
    mapping = mapping_mod.check_h07(raw.headers, mapping_path, non_interactive=non_interactive)
    canonical_cols = mapping_mod.apply_mapping(raw.columns, mapping)
    raw_mapped = RawTable(
        headers=list(canonical_cols),
        columns=canonical_cols,
        n_rows=raw.n_rows,
        source=raw.source,
        header_set_sha256=raw.header_set_sha256,
    )
    table = schema_mod.validate(raw_mapped, period=decl.period)
    gate_h02(table, decl)
    gate_h03(table, decl)
    gate_h05(table, decl)
    mask, _flow = schema_mod.analysis_mask(table, decl.indeterminate_values)
    warnings = gate_h06(table, decl, mask)
    auc = gate_h01(table, decl, mask)
    gate_h04(table, decl, mask)
    declare_mod.check_references(
        decl, {a: table.levels(a) for a in table.attributes}, has_age=table.age is not None
    )
    warnings += gate_h10(table, decl, mask)
    return IngestResult(table, decl, mapping, mask, warnings, auc)
