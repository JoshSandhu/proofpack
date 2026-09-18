"""Test-only assembler: one full output document from the day-2/4/5/6 library blocks.

**This is not the engine's assembly.** At 4eb44f3 ``cli.py`` calls no statistics
(``cmd_run`` ingests and runs the HALT gates only) and the assembly of the run's output
JSON - overall, subgroups, calibration, flow, table1, missingness, manifest, ledger - is
build day 7's (E7, ``spec/briefs/day7_E.md``). This module exists so the day-6 tests can
validate a whole document against ``schema/output_schema_v1.json`` with every block the
library can produce today in it; E7 wires the real thing and may take this as a sketch.

The ``overall`` block is built from the day-2 functions over the analysed rows. Two of
those - :func:`~proofpack.stats.proportions.two_by_two_metrics` and
:func:`~proofpack.stats.discrimination.auroc_number` - take no ``cluster_ids`` and are
documented as such; here ``overall`` is therefore only built for a non-clustered plan
and left ``None`` otherwise, so this module never renders an analytic interval on
clustered rows.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from conftest import make_criteria
from proofpack.io import schema as schema_mod
from proofpack.io.declare import Declarations, validate_dict
from proofpack.stats.bootstrap import BootstrapPolicy, plan_clustering, policy_from_declarations
from proofpack.stats.calibration import calibration_from_table
from proofpack.stats.descriptive import flow_block, missingness_block, table1_block
from proofpack.stats.discrimination import auroc_number
from proofpack.stats.proportions import (
    Table2x2,
    proportion,
    two_by_two_metrics,
)
from proofpack.stats.subgroups import subgroup_analysis


def _overall(
    table: schema_mod.Table, decl: Declarations, mask: np.ndarray
) -> dict[str, Any] | None:
    if table.score is None:
        return None
    yt = table.y_true[mask]
    pos = np.array([v == decl.positive for v in yt.tolist()], dtype=bool)
    score = np.asarray(table.score[mask], dtype=np.float64)
    oriented = score if decl.orientation == "higher_is_positive" else -score
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    out: dict[str, Any] = {}
    for op in decl.operating_points:
        pred = np.array([op.is_positive(float(v)) for v in score], dtype=bool)
        t = Table2x2(
            tp=int((pos & pred).sum()),
            fn=int((pos & ~pred).sum()),
            fp=int((~pos & pred).sum()),
            tn=int((~pos & ~pred).sum()),
        )
        metrics = two_by_two_metrics(t, reference_standard_type=decl.reference_standard_type)
        block = {k: v.as_dict() for k, v in metrics.items()}
        block["two_by_two"] = t.as_dict()
        block["ppv_at_prevalence"] = []
        out[op.id] = block
    disc = auroc_number(oriented, pos)
    out["threshold_free"] = {
        "auroc": disc.auroc.as_dict(),
        "auroc_wald": None if disc.auroc_secondary is None else disc.auroc_secondary.as_dict(),
        "auprc": None,
        "prevalence": proportion(n_pos, n_pos + n_neg).as_dict(),
        "roc": disc.roc,
    }
    return out


def assemble(
    cols: dict[str, list[Any]],
    crit: dict[str, Any] | None = None,
    *,
    policy: BootstrapPolicy | None = None,
) -> dict[str, Any]:
    """Validate ``cols`` and ``crit`` the day-1 way and build one output document."""
    crit = crit if crit is not None else make_criteria()
    decl = validate_dict(crit)
    table = schema_mod.validate(schema_mod.table_from_columns(cols), period=None)
    mask, flow = schema_mod.analysis_mask(table, decl.indeterminate_values)
    pol = policy if policy is not None else policy_from_declarations(decl)
    ids = None if table.case_id is None else table.case_id[mask]
    plan = plan_clustering(decl.clustering_unit, ids, int(mask.sum()))
    sub = subgroup_analysis(table, decl, mask, plan=plan, policy=pol)
    cal = calibration_from_table(table, decl, mask, plan=plan, policy=pol)
    warnings = []
    finding = plan.finding()
    if finding is not None:
        warnings.append({"code": finding.code, "text_id": None, "params": dict(finding.detail)})
    return {
        "schema_version": 1,
        "manifest": {
            "run_id": "test-only-assembler",
            "engine_version": "0.1.0.dev1",
            "python": "3",
            "numpy": str(np.__version__),
            "seed": pol.seed,
            "B": pol.n_resamples,
            "started": "2026-09-18T00:00:00Z",
            "reference_platform": False,
        },
        "declarations": decl.raw,
        "halts": [],
        "warnings": warnings,
        "flow": flow_block(table, mask, flow, decl, plan),
        "table1": table1_block(table, decl, mask),
        "missingness": missingness_block(table),
        "overall": None if plan.clustered else _overall(table, decl, mask),
        **cal.as_document(),
        **sub.as_dict(),
    }
