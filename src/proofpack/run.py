"""``proofpack run``'s assembly (build day 7, E7): ingest, statistics, criteria, manifest.

The order, and what each step is allowed to do:

1. **Licence** (:mod:`proofpack.licence`) - resolved first so the watermark and the exit
   code are known; nothing is skipped on its account. D1 section 7: within ``grace_days``
   the pack renders with the ``LICENCE EXPIRED - not for submission`` watermark; after
   grace ``run`` / ``compare`` emit JSON only; ``doctor`` / ``map`` / ``fixtures`` always
   work. The reading applied here (recorded in the E7 build note; D1 section 7, the
   "Expiry" bullet): ``ok`` and ``grace`` are full runs (exit 0 / 2), ``grace`` with the
   watermark in ``manifest.watermark`` for the renderer's footer; ``expired``, ``refused``
   and no licence at all still compute and write ``run.json`` with the expired watermark
   and exit 4 with the one-line fix, and the renderer (E8/E9) writes no HTML/DOCX on a
   status that is not ``ok`` or ``grace``. The most conservative reading for the customer:
   their numbers are never withheld, only the submission-shaped documents.
2. **Confirmed mapping** (DEC-26): ``--mapping FILE`` or ``<input>.mapping.json`` beside
   the input (``test.csv`` -> ``test.csv.mapping.json``); neither present -> H07 ``run
   proofpack map first`` before any statistics; a file that fails ``check_h07``'s
   ``--yes`` rule (decided_by ``interactive`` or ``file``, header-set hash equal, every
   role high or confirmed, DEC-28 / DEC-29 / DEC-31 / DEC-42) is the same H07 with lane A's
   message. ``run`` writes no ``mapping.json`` anywhere (the pack directory a customer
   hands over must not carry original headers and value summaries: A-P1 carried 20).
3. **Ingest and the HALT gates** (:func:`proofpack.gates.ingest`): nothing is written on
   HALT (D1 section 5).
4. **Statistics**, each block from the library module that owns it and nothing computed
   here: ``flow`` / ``table1`` / ``missingness`` (``stats.descriptive``), ``overall``
   (the day-2 functions over the analysed rows, i.i.d. only - see :func:`overall_block`),
   ``calibration`` or ``None`` with ``calibration_suppressed_reason`` (DEC-36),
   ``subgroups`` / ``subgroup_attributes`` / ``fairness`` (``stats.subgroups``).
5. **Criteria** (:mod:`proofpack.criteria`) over the assembled blocks.
6. **Ledger** (:mod:`proofpack.io.ledger`) and the **manifest** (:mod:`proofpack.manifest`);
   the document is serialised as canonical JSON (a non-finite float raises and nothing is
   written) to ``<out>/run.json``. ``<out>/ingest_report.json`` (the day-1 aggregate
   report) is still written beside it.

``--offline`` opens no socket: nothing in this module or below it imports ``socket``,
``urllib`` or ``http``; ``tests/test_run_cli.py`` makes ``socket.socket`` raise and runs
the whole command.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from proofpack import criteria as criteria_mod
from proofpack import manifest as manifest_mod
from proofpack.errors import EXIT_LICENCE, EXIT_OK, EXIT_WARNINGS, Finding, HaltError
from proofpack.gates import IngestResult, ingest
from proofpack.io import declare, ledger
from proofpack.io import mapping as mapping_mod
from proofpack.io.declare import Declarations
from proofpack.io.schema import Table, analysis_mask, load_table
from proofpack.licence import LicenceResult, resolve
from proofpack.licence.keys import KeyRegistry
from proofpack.licence.verify import WATERMARK_EXPIRED
from proofpack.stats.bootstrap import plan_clustering, policy_from_declarations
from proofpack.stats.calibration import calibration_from_table
from proofpack.stats.descriptive import flow_block, missingness_block, table1_block
from proofpack.stats.discrimination import auroc_number
from proofpack.stats.proportions import Table2x2, proportion, two_by_two_metrics
from proofpack.stats.subgroups import subgroup_analysis

RUN_JSON = "run.json"
INGEST_REPORT = "ingest_report.json"
MAPPING_SUFFIX = ".mapping.json"

#: The one-line fix printed with exit 4.
LICENCE_FIX = (
    "no usable licence: install one with `proofpack licence install FILE` "
    "(docs: /docs/licence); run.json was written with the watermark "
    f"'{WATERMARK_EXPIRED}'"
)


def default_mapping_path(input_path: str | Path) -> Path:
    """``<input>.mapping.json`` beside the input file (DEC-26)."""
    p = Path(input_path)
    return p.with_name(p.name + MAPPING_SUFFIX)


def resolve_mapping_path(input_path: str | Path, mapping: str | Path | None) -> Path:
    """The confirmed mapping ``run`` reads, or H07 ``run proofpack map first``."""
    if mapping is not None:
        p = Path(mapping)
        if not p.exists():
            raise HaltError(
                "H07",
                "run proofpack map first: the --mapping file does not exist",
                {"mapping_given": True, "exists": False},
            )
        return p
    p = default_mapping_path(input_path)
    if not p.exists():
        raise HaltError(
            "H07",
            "run proofpack map first: no confirmed mapping.json was given (--mapping FILE) "
            f"and none exists beside the input as <input>{MAPPING_SUFFIX}",
            {"mapping_given": False, "exists": False},
        )
    return p


def overall_block(table: Table, decl: Declarations, mask: np.ndarray) -> dict[str, Any] | None:
    """The ``overall`` block from the day-2 functions over the analysed rows, i.i.d. only.

    ``two_by_two_metrics`` and ``auroc_number`` take no ``cluster_ids`` (their docstrings
    say so), so on a clustered plan this returns ``None`` rather than render an analytic
    interval on dependent rows; the subgroup rows carry the cluster-bootstrap cells. The
    clustered overall block is carried to E8 (the E7 build note names it). ``None`` also
    for a ``y_pred``-only table (no threshold-free block can exist; the operating-point
    metrics from ``y_pred`` are carried with it).
    """
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


def _warning_entry(f: Finding) -> dict[str, Any]:
    return {"code": f.code, "text_id": None, "params": dict(f.detail)}


@dataclass
class RunOutcome:
    document: dict[str, Any]
    ingest: IngestResult
    licence: LicenceResult
    warnings: list[Finding]
    ledger: ledger.LedgerResult | None
    mapping_path: Path

    @property
    def exit_code(self) -> int:
        if not self.licence.usable:
            return EXIT_LICENCE
        return EXIT_WARNINGS if self.warnings else EXIT_OK


def assemble_run(
    input_path: str | Path,
    criteria_path: str | Path,
    *,
    mapping: str | Path | None = None,
    registry: KeyRegistry | None = None,
    ledger_home: Path | None = None,
) -> RunOutcome:
    """Everything ``proofpack run`` computes, as one document. Writes nothing under
    ``--out``; the one file it writes is ``<PROOFPACK_HOME>/ledger.json`` through
    :func:`proofpack.io.ledger.record_run` (``tests/test_run_cli.py::
    test_assemble_run_writes_only_the_ledger_file_under_home`` walks the directory
    tree before and after and names that file as the one addition)."""
    started = manifest_mod.utc_now_iso()
    t0 = time.perf_counter()
    licence = resolve(registry=registry)
    decl = declare.load(criteria_path)
    raw = load_table(input_path)
    mapping_path = resolve_mapping_path(input_path, mapping)
    result = ingest(raw, decl, mapping_path=mapping_path, non_interactive=True)
    if result.mapping.decided_by not in mapping_mod.CONFIRMED_DECIDED_BY:
        # check_h07 in non-interactive mode refuses this itself; kept as the DEC-26 line
        raise HaltError(
            "H07", "run proofpack map first: the mapping.json beside the input is not confirmed"
        )
    table = result.table
    mask, flow = analysis_mask(table, decl.indeterminate_values)
    policy = policy_from_declarations(decl)
    ids = None if table.case_id is None else table.case_id[mask]
    plan = plan_clustering(decl.clustering_unit, ids, int(mask.sum()))
    warnings: list[Finding] = list(result.warnings)
    finding = plan.finding()
    if finding is not None:
        warnings.append(finding)
    sub = subgroup_analysis(table, decl, mask, plan=plan, policy=policy)
    cal = calibration_from_table(table, decl, mask, plan=plan, policy=policy)

    doc: dict[str, Any] = {
        "schema_version": 1,
        "declarations": decl.raw,
        "halts": [],
        "flow": flow_block(table, mask, flow, decl, plan),
        "table1": table1_block(table, decl, mask),
        "missingness": missingness_block(table),
        "overall": None if plan.clustered else overall_block(table, decl, mask),
        **cal.as_document(),
        **sub.as_dict(),
        "suppression_log": [],  # egress k-suppression is A-P2's; nothing is suppressed locally
        "guidance_refs": [],  # resolved by the renderer (E9)
    }
    doc["criteria_results"] = criteria_mod.evaluate(decl, doc)

    key = ledger.test_set_key(
        table.y_true[mask],
        None if table.score is None else table.score[mask],
        None if table.y_pred is None else table.y_pred[mask],
    )
    limit = (decl.raw.get("ledger") or {}).get("warn_after_acceptance_runs")
    led = ledger.record_run(key, has_criteria=bool(decl.criteria), limit=limit, home=ledger_home)
    if led.warning is not None:
        warnings.append(led.warning)
    doc["warnings"] = [_warning_entry(w) for w in warnings]
    watermark = licence.watermark if licence.status != "refused" else WATERMARK_EXPIRED
    doc["manifest"] = manifest_mod.build_manifest(
        input_path=input_path,
        criteria_path=criteria_path,
        mapping_path=mapping_path,
        seed=policy.seed,
        n_resamples=policy.n_resamples,
        started=started,
        duration_s=round(time.perf_counter() - t0, 3),
        licence_id=licence.licence_id,
        tier=licence.tier,
        ledger_count=led.count,
        watermark=watermark,
    )
    doc["ledger"] = led.as_dict()
    return RunOutcome(doc, result, licence, warnings, led, mapping_path)


def write_run(outcome: RunOutcome, out: str | Path) -> Path:
    """Serialise (canonical JSON; raises on a non-finite float before anything is
    written) and write ``run.json`` and ``ingest_report.json`` into ``out``."""
    data = manifest_mod.canonical_json(outcome.document)
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / RUN_JSON
    target.write_bytes(data)
    report = outcome.ingest.report()
    (out_dir / INGEST_REPORT).write_bytes(manifest_mod.canonical_json(report))
    return target
