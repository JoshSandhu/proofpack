"""Test-only assembler: one full output document from the day-2/4/5/6 library blocks.

**This is not the engine's assembly.** At 4eb44f3 ``cli.py`` calls no statistics
(``cmd_run`` ingests and runs the HALT gates only) and the assembly of the run's output
JSON - overall, subgroups, calibration, flow, table1, missingness, manifest, ledger - is
build day 7's (E7, ``spec/briefs/day7_E.md``). This module exists so the day-6 tests can
validate a whole document against ``schema/output_schema_v1.json`` with every block the
library can produce today in it; E7 wires the real thing and may take this as a sketch.

The ``overall`` block comes from the engine's own :func:`proofpack.run.overall_block`
(build day 8, E8 item 1): the day-2 functions on an i.i.d. plan, the day-4
cluster-bootstrap route on a clustered plan, ``y_pred`` alone on a table without a score
column - so a document this module assembles carries the same ``overall`` as ``run``.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from conftest import make_criteria
from proofpack import criteria as criteria_mod
from proofpack.io import schema as schema_mod
from proofpack.io.declare import validate_dict
from proofpack.run import narrative_block, overall_block
from proofpack.stats.bootstrap import BootstrapPolicy, plan_clustering, policy_from_declarations
from proofpack.stats.calibration import calibration_from_table
from proofpack.stats.descriptive import flow_block, missingness_block, table1_block
from proofpack.stats.subgroups import subgroup_analysis


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
    doc = {
        "schema_version": 1,
        "manifest": {
            "run_id": "test-only-assembler",
            "engine_version": "0.1.0.dev1",
            "platform": "test",
            "python": "3",
            "numpy": str(np.__version__),
            "scipy": None,
            "input_sha256": None,
            "criteria_sha256": None,
            "mapping_sha256": None,
            "seed": pol.seed,
            "B": pol.n_resamples,
            "started": "2026-09-18T00:00:00Z",
            "duration_s": None,
            "reference_platform": False,
            "licence_id": None,
            "tier": None,
            "ledger_count": None,
            "watermark": None,
        },
        "declarations": decl.raw,
        "halts": [],
        "warnings": warnings,
        "flow": flow_block(table, mask, flow, decl, plan),
        "table1": table1_block(table, decl, mask),
        "missingness": missingness_block(table),
        "overall": overall_block(table, decl, mask, plan=plan, policy=pol),
        **cal.as_document(),
        **sub.as_dict(),
        "suppression_log": [],
    }
    # build day 7: the criteria engine reads the assembled blocks (E7, proofpack.criteria)
    doc["criteria_results"] = criteria_mod.evaluate(decl, doc)
    # build day 8: the claims, their rejections and the guidance anchors (E8, run.narrative_block)
    doc.update(narrative_block(doc))
    return doc
