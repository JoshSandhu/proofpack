"""``stats.descriptive`` - Table 1, the flow counts and the missingness table (day 6).

Three descriptive blocks of the D1 section 4.2 document, all counts and shares, no
Numbers and no intervals (counts are the one thing D1 renders without a CI):

* **``flow``** (D1 ``flow``, D4 section 5.10, the R1 flowchart): ``rows_read``,
  ``excluded_missing_label``, ``excluded_missing_score``, ``indeterminate``,
  ``analysed``, ``n_cases``, ``n_sites``, ``clustered`` and the clustering route. The
  counts are the day-1 :class:`~proofpack.io.schema.FlowCounts` that
  :func:`~proofpack.io.schema.analysis_mask` computes - this module renames them to
  D1's keys and adds the case and site counts over the analysed rows; it does not
  recount. ``n_cases`` is the number of distinct ``case_id`` values among the analysed
  rows, or the analysed row count when the table has no case column (each row is then
  its own case). ``n_sites`` counts the distinct ``site`` levels among the analysed
  rows, the Unknown/missing level excluded; ``None`` without a site column.

* **``table1``** (D1 ``table1``, D4 section 5.4): per attribute, per level, ``n`` and
  ``pct`` over the analysed test rows, the Unknown/missing level included, so the
  levels of one attribute sum to the analysed count and their shares to 1. The
  attributes are the ones ``stats.subgroups`` tabulates - every recognised attribute
  column plus ``age`` banded by the declared bands (or the engine default, D1 section
  2's bands, when ``age`` is present but not declared) - so Table 1 and the subgroup
  tables describe the same levels. ``dev`` is the same table over the rows whose
  ``dataset`` column reads ``dev`` when the table carries any, else ``None``.
  ``similarity`` (standardised differences, Cramer's V, KS) and ``overlap`` (id and
  site overlap counts) are **v1.1** (day-6 brief) and are ``None`` with the reason in
  ``not_computed``. Nothing is rounded: the renderer rounds.

* **``missingness``**: per mapped column, the count and share of rows missing
  **after** the missing-token normalisation (``io.schema``: the tokens in
  ``schema_v1.json``'s ``missing_tokens`` become ``None`` at load; an attribute's
  ``None`` has already been rewritten to ``Unknown/missing`` in the typed table and is
  counted as missing here; a numeric column's ``NaN`` and the indeterminate column's
  ``-1`` are missing). Shares are over every row read, not the analysed rows, because
  missingness is what decided the exclusions.

What leaves this module: counts and shares, keyed by the mapped column names (the
customer's own headers) and by attribute level labels exactly as the rows spell them
(the category values, as ``stats.subgroups`` keys its tables), the Unknown/missing label
included - a level spelt as a number is a key like any other, so a ``site`` column
reading ``1000`` .. ``1029`` on thirty rows makes those thirty strings ``table1.test.site``
keys with ``n: 1`` each. No ``row_id`` value, no ``case_id`` value and no score value is
a key or a value in the three blocks on the cohort
``test_table1_and_missingness_keys_are_column_names_and_level_labels_and_nothing_per_row``
feeds (a ``sex`` level spelt like a name, an ``ethnicity`` level spelt like an id, that
``site`` column); the values under a level are one ``int`` and one ``float``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from proofpack.io.declare import Declarations
from proofpack.io.schema import UNKNOWN_LEVEL, FlowCounts, Table
from proofpack.stats.bootstrap import ClusterPlan, plan_clustering
from proofpack.stats.subgroups import DEFAULT_AGE_BANDS, age_band_labels, band_ages

__all__ = ["flow_block", "missingness_block", "table1_block", "table1_levels"]

V11_REASON = "v1.1"


# ----------------------------------------------------------------------------- flow


def flow_block(
    table: Table,
    mask: np.ndarray,
    flow: FlowCounts,
    decl: Declarations,
    plan: ClusterPlan | None = None,
) -> dict[str, Any]:
    """The D1 ``flow`` block from the day-1 counts, the analysed rows and the plan."""
    mask = np.asarray(mask, dtype=bool)
    analysed = int(mask.sum())
    if flow.included != analysed:
        raise ValueError(
            f"flow.included ({flow.included}) disagrees with the mask ({analysed} rows)"
        )
    if plan is None:
        ids = None if table.case_id is None else table.case_id[mask]
        plan = plan_clustering(decl.clustering_unit, ids, analysed)
    if table.case_id is None:
        n_cases = analysed
    else:
        n_cases = int(np.unique(table.case_id[mask]).shape[0]) if analysed else 0
    n_sites: int | None = None
    if "site" in table.attributes:
        levels = {str(v) for v in table.attributes["site"][mask].tolist()} - {UNKNOWN_LEVEL}
        n_sites = len(levels)
    # E7, carried item 27: rows whose ``dataset`` reads ``dev`` are never analysed and were
    # counted nowhere in the flow, so the flow did not reconcile to rows_read on a table
    # carrying them; they are their own entry, and rows_read = dev_rows + the two
    # exclusions + indeterminate + analysed (``tests/test_run_cli.py`` asserts the sum)
    dev_rows = (
        0 if table.dataset is None else int(sum(1 for v in table.dataset.tolist() if v == "dev"))
    )
    return {
        "rows_read": int(flow.n_rows),
        "dev_rows": dev_rows,
        "excluded_missing_label": int(flow.excluded_missing_y_true),
        "excluded_missing_score": int(flow.excluded_missing_score),
        "indeterminate": int(flow.indeterminate),
        "analysed": analysed,
        "n_cases": n_cases,
        "n_sites": n_sites,
        "clustered": bool(plan.clustered),
        "clustering_route": plan.route,
    }


# --------------------------------------------------------------------------- table 1


def _attribute_labels(
    table: Table, decl: Declarations, rows: np.ndarray
) -> dict[str, tuple[list[str], np.ndarray]]:
    """attribute -> (level order, label per row) over ``rows``, subgroup-style."""
    out: dict[str, tuple[list[str], np.ndarray]] = {}
    for name in sorted(table.attributes):
        labels = np.array([str(v) for v in table.attributes[name][rows].tolist()], dtype=object)
        order = sorted({str(v) for v in labels.tolist() if v != UNKNOWN_LEVEL})
        if bool((labels == UNKNOWN_LEVEL).any()):
            order.append(UNKNOWN_LEVEL)
        out[name] = (order, labels)
    if table.age is not None and "age" not in table.attributes:
        declared = decl.age_bands()
        bands: Sequence[Sequence[float]] = (
            declared if declared else [list(b) for b in DEFAULT_AGE_BANDS]
        )
        banded, _, _ = band_ages(table.age[rows], bands)
        order = list(age_band_labels(bands))
        labels = np.array([str(v) for v in banded.tolist()], dtype=object)
        if bool((labels == UNKNOWN_LEVEL).any()):
            order.append(UNKNOWN_LEVEL)
        out["age"] = (order, labels)
    return out


def table1_levels(table: Table, decl: Declarations, rows: np.ndarray) -> dict[str, Any]:
    """attribute -> level -> ``{n, pct}`` over ``rows`` (a boolean mask)."""
    rows = np.asarray(rows, dtype=bool)
    total = int(rows.sum())
    out: dict[str, Any] = {}
    for name, (order, labels) in _attribute_labels(table, decl, rows).items():
        levels: dict[str, dict[str, Any]] = {}
        for level in order:
            n = int((labels == level).sum())
            levels[level] = {"n": n, "pct": (n / total) if total else 0.0}
        out[name] = levels
    return out


def table1_block(table: Table, decl: Declarations, mask: np.ndarray) -> dict[str, Any]:
    """The D1 ``table1`` block: ``test`` over the analysed rows, ``dev`` over the
    table's ``dataset = dev`` rows when there are any, ``similarity`` and ``overlap``
    ``None`` (v1.1)."""
    mask = np.asarray(mask, dtype=bool)
    dev_rows = (
        np.array([v == "dev" for v in table.dataset.tolist()], dtype=bool)
        if table.dataset is not None
        else np.zeros(table.n_rows, dtype=bool)
    )
    has_dev = bool(dev_rows.any())
    return {
        "test": table1_levels(table, decl, mask),
        "n_test": int(mask.sum()),
        "dev": table1_levels(table, decl, dev_rows) if has_dev else None,
        "n_dev": int(dev_rows.sum()) if has_dev else None,
        "similarity": None,
        "overlap": None,
        "not_computed": {
            **({} if has_dev else {"dev": "no development-set rows in the table"}),
            "similarity": V11_REASON,
            "overlap": V11_REASON,
        },
    }


# ------------------------------------------------------------------------ missingness


def _missing_mask(name: str, col: np.ndarray) -> np.ndarray:
    if col.dtype.kind == "f":
        return np.isnan(col)
    if name == "indeterminate":
        return col == -1
    return np.array([v is None or v == UNKNOWN_LEVEL for v in col.tolist()], dtype=bool)


def missingness_block(table: Table) -> dict[str, Any]:
    """Per mapped column, rows missing after the missing-token normalisation."""
    n = int(table.n_rows)
    columns: dict[str, np.ndarray] = {}
    for name in (
        "y_true",
        "score",
        "y_pred",
        "indeterminate",
        "row_id",
        "case_id",
        "age",
        "period",
        "model_version",
        "dataset",
    ):
        col = getattr(table, name)
        if col is not None:
            columns[name] = col
    columns.update(table.attributes)
    columns.update(table.extras_numeric)
    out: dict[str, Any] = {}
    for name in sorted(columns):
        missing = int(_missing_mask(name, columns[name]).sum())
        out[name] = {"n_missing": missing, "pct": (missing / n) if n else 0.0}
    return {"n_rows": n, "columns": out}
