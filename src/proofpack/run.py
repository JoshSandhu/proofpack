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
   (see :func:`overall_block`: the day-2 functions on an i.i.d. plan, the day-4
   cluster-bootstrap route on a clustered plan, ``y_pred`` alone on a table without a
   score column - E8 item 1),
   ``calibration`` or ``None`` with ``calibration_suppressed_reason`` (DEC-36),
   ``subgroups`` / ``subgroup_attributes`` / ``fairness`` (``stats.subgroups``).
5. **Criteria** (:mod:`proofpack.criteria`) over the assembled blocks.
5b. **Narrative** (:func:`narrative_block`, E8): the claims list built from the assembled
   blocks and the criteria rows, checked by :mod:`proofpack.narrate.checker` (rejected
   claims replaced by the deterministic template claim and logged in
   ``claim_rejections``), and the guidance anchors the claims cite resolved through the
   map into ``guidance_refs``.
6. **Ledger** (:mod:`proofpack.io.ledger`) and the **manifest** (:mod:`proofpack.manifest`);
   the document is serialised as canonical JSON (a non-finite float raises and nothing is
   written) to ``<out>/run.json``. ``<out>/ingest_report.json`` (the day-1 aggregate
   report) is still written beside it.
7. **Documents** (:func:`write_documents`, E8): ``<out>/T8.html`` beside ``run.json``
   when ``--format`` includes ``html`` (the default ``json,html``) and the licence is
   ``ok`` or ``grace``; on any other licence state the JSON alone is written and the
   summary says so; ``--templates`` names T1 / T7 / T8, of which E8 renders T8 and prints
   a typed one-line note for the other two.

``--offline`` opens no socket: nothing in this module or below it imports ``socket``,
``urllib`` or ``http``; ``tests/test_run_cli.py`` makes ``socket.socket`` raise and runs
the whole command.
"""

from __future__ import annotations

import json
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
from proofpack.narrate import checker as checker_mod
from proofpack.render import anchors as anchors_mod
from proofpack.render.html import TemplateNotBuilt, write_t8
from proofpack.stats.bootstrap import (
    DEFAULT_LEVEL,
    BootstrapPolicy,
    ClusterPlan,
    auroc_ci,
    plan_clustering,
    policy_from_declarations,
    proportion_ci,
)
from proofpack.stats.calibration import calibration_from_table
from proofpack.stats.descriptive import flow_block, missingness_block, table1_block
from proofpack.stats.discrimination import auroc_number, roc_curve
from proofpack.stats.number import not_estimable
from proofpack.stats.proportions import (
    Table2x2,
    proportion,
    sensitivity_id,
    specificity_id,
    two_by_two_metrics,
)
from proofpack.stats.subgroups import _conditioned, subgroup_analysis

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


def _overall_cell_key(*parts: Any) -> str:
    """One unambiguous bootstrap cell key for an overall cell (the subgroup rows use the
    same shape under ``"subgroups"``; ``rng_for_cell`` seeds each cell from it)."""
    return json.dumps(["overall", *[str(p) for p in parts]])


#: The two-by-two metrics whose analytic interval assumes independent rows and for which
#: no cluster-bootstrap route exists in the engine today: under a clustered plan each is
#: typed ``clustered_data_analytic_ci_invalid`` (DEC-09) with the point estimate that
#: ``two_by_two_metrics`` computes from the four counts and no interval.
CLUSTERED_REFUSED_2X2: tuple[str, ...] = (
    "youden",
    "balanced_accuracy",
    "lr_pos",
    "lr_neg",
    "dor",
    "f1",
    "mcc",
)
#: The overall proportions routed through ``proportion_ci`` under a clustered plan, in
#: the vocabulary of ``stats.subgroups._conditioned`` (``se`` / ``sp`` are renamed to the
#: reference-standard ids).
_OVERALL_PROPORTIONS: tuple[str, ...] = ("se", "sp", "ppv", "npv", "accuracy")
#: The structured reason on ``threshold_free`` of a ``y_pred``-only table (E7 carried
#: item 42): no score column, so no threshold-free statistic can exist. The AUROC Number
#: itself carries ``not_computed_this_run``, the reason the subgroup rows use for the
#: same absence (``no_score_column`` is a calibration suppression reason, not a Number
#: reason - E7's decision, unchanged here).
NO_SCORE_COLUMN = "no_score_column"


def overall_block(
    table: Table,
    decl: Declarations,
    mask: np.ndarray,
    *,
    plan: ClusterPlan | None = None,
    policy: BootstrapPolicy | None = None,
) -> dict[str, Any]:
    """The ``overall`` block over the analysed rows, on every plan and every table (E8 item 1).

    Which existing function each cell comes from:

    * **i.i.d. plan** (``plan`` ``None`` or not clustered): unchanged from E7 - every
      operating-point metric from :func:`~proofpack.stats.proportions.two_by_two_metrics`
      (Wilson for the proportions, Newcombe-10 for Youden / balanced accuracy, log-delta
      for LR+ / LR- / DOR, ``analytic_ci_unavailable`` for F1 / MCC), the AUROC from
      :func:`~proofpack.stats.discrimination.auroc_number` (DeLong) and the prevalence
      from :func:`~proofpack.stats.proportions.proportion`.
    * **clustered plan** (declared or detected): the five conditioned proportions
      (sensitivity or PPA, specificity or NPA, PPV, NPV, accuracy) and the prevalence each
      come from :func:`~proofpack.stats.bootstrap.proportion_ci` - the cluster-bootstrap
      route the subgroup rows take through ``stats.subgroups._proportion_cell``, with the
      rows conditioned by ``stats.subgroups._conditioned`` and the case ids sliced with
      them, never a second implementation - so the rendered Number carries
      ``cluster_bootstrap_percentile``, the flag ``wilson_refused_clustered`` and
      ``n_cases``; the AUROC comes from :func:`~proofpack.stats.bootstrap.auroc_ci`'s
      clustered route (``delong_refused_clustered``; ``auroc_wald`` is ``null``, there is
      no Wald interval); the ROC coordinates from
      :func:`~proofpack.stats.discrimination.roc_curve`; and the seven two-by-two-only
      metrics in :data:`CLUSTERED_REFUSED_2X2` are typed
      ``clustered_data_analytic_ci_invalid`` (DEC-09) with the point estimate that
      ``two_by_two_metrics`` gives from the four counts (``None`` where it gives none)
      and no interval. The bootstrap cell key is ``["overall", <op>, <metric>]`` /
      ``["overall", "auroc"]`` / ``["overall", "prevalence"]``, so an overall cell's
      draw is seeded like a subgroup cell's but is its own stream; ``tests/
      test_overall_carried.py`` calls ``proportion_ci`` with the same key on the same
      rows and asserts the interval equal.
    * **``y_pred``-only table** (no score column; E7 carried item 42): the operating-point
      block from ``y_pred == positive`` alone through the same two routes above, and
      ``threshold_free`` carrying an AUROC Number typed ``not_computed_this_run`` (the
      subgroup rows' reason for the same absence), ``roc`` empty and the structured key
      ``suppressed_reason: no_score_column`` (:data:`NO_SCORE_COLUMN`).

    The two-by-two counts are the same four integers on every route; ``tests/
    test_overall_carried.py`` compares them with scikit-learn's ``confusion_matrix``.
    The block's *shape* (a Number per metric) is unchanged from E7, so ``criteria`` reads
    ``overall.<op>.<metric>`` on a clustered run as it does on an i.i.d. one; the
    bootstrap audit (companion refusal, usable resamples) is not carried into the
    overall block in E8 - the subgroup cells carry theirs.
    """
    yt = table.y_true[mask]
    pos = np.array([v == decl.positive for v in yt.tolist()], dtype=bool)
    n_rows = int(pos.shape[0])
    all_rows = np.arange(n_rows, dtype=np.intp)
    raw_score = None if table.score is None else np.asarray(table.score[mask], dtype=np.float64)
    ids = None if table.case_id is None else np.asarray(table.case_id[mask], dtype=object)
    clustered = plan is not None and plan.clustered
    if clustered and ids is None:
        raise ValueError("a clustered plan needs a case column")
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    se_key = sensitivity_id(decl.reference_standard_type)
    sp_key = specificity_id(decl.reference_standard_type)
    level = DEFAULT_LEVEL
    pol = policy if policy is not None else BootstrapPolicy()

    def clustered_proportion(rows: np.ndarray, indicator: np.ndarray, key: str) -> dict[str, Any]:
        cell = proportion_ci(
            indicator,
            cell_key=key,
            policy=pol,
            plan=plan,
            cluster_ids=ids[rows],
            level=level,
        )
        return cell.number.as_dict()

    out: dict[str, Any] = {}
    prevalence: dict[str, Any] | None = None
    if clustered:
        prevalence = clustered_proportion(all_rows, pos, _overall_cell_key("prevalence"))
    for op in decl.operating_points:
        if raw_score is not None:
            pred = np.array([op.is_positive(float(v)) for v in raw_score], dtype=bool)
        else:
            pred = np.array([v == decl.positive for v in table.y_pred[mask].tolist()], dtype=bool)
        t = Table2x2(
            tp=int((pos & pred).sum()),
            fn=int((pos & ~pred).sum()),
            fp=int((~pos & pred).sum()),
            tn=int((~pos & ~pred).sum()),
        )
        metrics = two_by_two_metrics(t, reference_standard_type=decl.reference_standard_type)
        if not clustered:
            block = {k: v.as_dict() for k, v in metrics.items()}
        else:
            block = {}
            for metric in _OVERALL_PROPORTIONS:
                rows, ind = _conditioned(all_rows, pos, pred, metric)
                key = {"se": se_key, "sp": sp_key}.get(metric, metric)
                block[key] = clustered_proportion(rows, ind, _overall_cell_key(op.id, key))
            block["prevalence"] = dict(prevalence)  # type: ignore[arg-type]
            for key in CLUSTERED_REFUSED_2X2:
                block[key] = not_estimable(
                    "clustered_data_analytic_ci_invalid",
                    est=metrics[key].est,
                    n=t.n,
                    ci_level=level,
                ).as_dict()
        block["two_by_two"] = t.as_dict()
        block["ppv_at_prevalence"] = []
        out[op.id] = block

    if raw_score is None:
        out["threshold_free"] = {
            "auroc": not_estimable(
                "not_computed_this_run", n_pos=n_pos, n_neg=n_neg, ci_level=level
            ).as_dict(),
            "auroc_wald": None,
            "auprc": None,
            "prevalence": prevalence
            if prevalence is not None
            else proportion(n_pos, n_pos + n_neg).as_dict(),
            "roc": [],
            "suppressed_reason": NO_SCORE_COLUMN,
        }
        return out
    oriented = raw_score if decl.orientation == "higher_is_positive" else -raw_score
    if clustered:
        auroc = auroc_ci(
            oriented,
            pos,
            cell_key=_overall_cell_key("auroc"),
            policy=pol,
            plan=plan,
            cluster_ids=ids,
            level=level,
        ).number
        out["threshold_free"] = {
            "auroc": auroc.as_dict(),
            "auroc_wald": None,
            "auprc": None,
            "prevalence": dict(prevalence),  # type: ignore[arg-type]
            "roc": roc_curve(oriented, pos),
        }
        return out
    disc = auroc_number(oriented, pos)
    out["threshold_free"] = {
        "auroc": disc.auroc.as_dict(),
        "auroc_wald": None if disc.auroc_secondary is None else disc.auroc_secondary.as_dict(),
        "auprc": None,
        "prevalence": proportion(n_pos, n_pos + n_neg).as_dict(),
        "roc": disc.roc,
    }
    return out


#: The document keys the narrative step writes (E8): the claims the checker accepted
#: (rejected ones replaced by the deterministic template claim for their slot), the
#: rejections T8 section 7 prints, and the guidance anchors the claims cite, resolved
#: through ``design/guidance_map_v1.csv`` into ``{id, label, draft, url}`` items (the
#: draft status as structured data, D1 section 4.2 / CLAUDE.md).
NARRATIVE_KEYS: tuple[str, ...] = ("claims", "claim_rejections", "guidance_refs")
#: ``--templates`` ids the CLI accepts; only T8 is rendered in E8 (T1 and T7: E9).
TEMPLATE_IDS: tuple[str, ...] = ("T1", "T7", "T8")
FORMATS: tuple[str, ...] = ("json", "html")
#: ``--format`` default: the JSON is always written; the HTML documents are written
#: beside it when the licence is ``ok`` or ``grace`` (D1 section 7: after grace, JSON
#: only). D1 section 7 lists ``--format json,html,docx`` without a default; ``json,html``
#: is the E8 decision (a customer who runs ``proofpack run`` gets the pack they bought,
#: and ``--format json`` is the explicit way to ask for the document alone).
DEFAULT_FORMAT = "json,html"
DEFAULT_TEMPLATES = "T8"


def narrative_block(doc: dict[str, Any]) -> dict[str, Any]:
    """The three :data:`NARRATIVE_KEYS` for an assembled document (the one call site is
    :func:`assemble_run`, after the criteria rows exist and before the manifest)."""
    claims, rejections = checker_mod.resolve(doc)
    ids = sorted({c["guidance_ref"] for c in claims if c.get("guidance_ref")})
    return {
        "claims": claims,
        "claim_rejections": rejections,
        "guidance_refs": anchors_mod.resolve(ids),
    }


def parse_formats(text: str) -> list[str]:
    """``--format json,html`` -> ``["json", "html"]``; an unknown token raises ``ValueError``."""
    out: list[str] = []
    for token in text.split(","):
        t = token.strip().lower()
        if not t:
            continue
        if t not in FORMATS:
            raise ValueError(
                f"unknown --format token {token.strip()!r}; choose from {', '.join(FORMATS)}"
            )
        if t not in out:
            out.append(t)
    return out or ["json"]


def parse_templates(text: str) -> list[str]:
    out: list[str] = []
    for token in text.split(","):
        t = token.strip().upper()
        if not t:
            continue
        if t not in TEMPLATE_IDS:
            raise ValueError(
                f"unknown --templates id {token.strip()!r}; choose from {', '.join(TEMPLATE_IDS)}"
            )
        if t not in out:
            out.append(t)
    return out or [DEFAULT_TEMPLATES]


def write_documents(
    outcome: RunOutcome, out: str | Path, formats: list[str], templates: list[str]
) -> tuple[list[Path], list[str]]:
    """The HTML documents beside ``run.json`` - only on a licence that is ``ok`` or
    ``grace`` (D1 section 7; the E7 "after grace" decision: the JSON is emitted, the
    documents are not). Returns the paths written and one line per template not
    written (a template not built in E8, or the licence state)."""
    written: list[Path] = []
    notes: list[str] = []
    if "html" not in formats:
        return written, notes
    if not outcome.licence.usable:
        notes.append(
            f"HTML not written: licence {outcome.licence.status} ({outcome.licence.reason_code}); "
            "run.json only (D1 section 7: after grace, JSON only)"
        )
        return written, notes
    for template in templates:
        if template == "T8":
            written.append(write_t8(outcome.document, out))
            continue
        exc = TemplateNotBuilt(f"template {template} is not built in E8 (E9 renders T1 and T7)")
        notes.append(f"{template} not written: {exc}")
    return written, notes


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
        "overall": overall_block(table, decl, mask, plan=plan, policy=policy),
        **cal.as_document(),
        **sub.as_dict(),
        "suppression_log": [],  # egress k-suppression is A-P2's; nothing is suppressed locally
    }
    doc["criteria_results"] = criteria_mod.evaluate(decl, doc)
    doc.update(narrative_block(doc))

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
