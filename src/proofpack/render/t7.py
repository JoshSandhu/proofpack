"""T7, the methods appendix, from what the run actually did (D4 section 10; build day 9, E9).

Nothing on this page is a static list of what ProofPack can do. Each part is read from
the run document:

* **methods used** - the distinct ``method`` of every Number object in the document
  (the same walk T8 section 7 counts suppressed cells with: every dict carrying ``est``,
  ``ci_lo``, ``ci_hi``, ``method`` and ``suppressed``, companions under ``analytic``
  included), each printed with its fixed description from :data:`METHOD_DESCRIPTIONS`
  and the number of Numbers that carry it. ``tests/test_render_t7.py`` walks
  ``run.json`` itself and asserts the page lists exactly that set;
* **software** - the manifest's versions, platform, seed and B; the tolerance policy is
  D1 section 9's text (:data:`TOLERANCE_POLICY`);
* **data handling** - the manifest's mapping hash, the document's ``halts`` and
  ``warnings``, the ``flow`` counts and the clustering route taken;
* **the X1 complement sentence** (Master section 5.1 X1) when the run has subgroup rows,
  and the conventions file's sections (``design/conventions_T7.md``, verbatim through
  :mod:`proofpack.render.markdown`) for the blocks the run computed: subgroups,
  calibration (which carries DEC-34's 0.897 coverage cell and DEC-35's IPA note), and the
  cluster-bootstrap coverage bar when a Number carries ``cluster_bootstrap_percentile``;
* **the conventions sentence** (Master section 3.1, "Reporting conventions, not
  acceptance criteria"; X3) and the conventions file's own first paragraph;
* **citations** from ``design/citations.yaml``: those whose ``used_by`` names a method or
  block of this run, and, under "Open verification items", every entry with
  ``verified: false``, each printed ``citation pending verification`` with its
  ``[unverified]`` marking kept.

The analyses the run did not perform (robustness, version comparison, drift) are named in
one line; no heading is printed for them.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from proofpack.render import anchors, markdown
from proofpack.render import format as fmt
from proofpack.render import html as render_html
from proofpack.resources import resource_path

T7_FILE = "T7.html"
T7_ANCHORS: dict[str, str] = {
    "software": "PP_METHODS",
    "data": "FDA_AIDSF_DATA_MGMT",
    "methods": "FDA_STAT2007_CI",
    "subgroups": "FDA_AIDSF_SUBGROUP_PERF",
    "calibration": "FDA_AIDSF_CALIBRATION",
    "conventions": "PP_METHODS",
}
UNVERIFIED_MARK = "[unverified]"
PENDING = "citation pending verification"

#: D1 section 9, verbatim (the T7/T12 tolerance text).
TOLERANCE_POLICY = (
    "Reference platform: python:3.12-slim linux/amd64 with the pinned lockfile. Same image + "
    "same inputs → identical manifest hash and byte-identical JSON (F17). Other platforms "
    "(arm64 laptop, Windows pip, Pyodide) → agreement to tolerance: 1e-9 closed-form (Wilson, "
    "2×2, Brier, O/E, PSI), 1e-6 iterative (IRLS slope/intercept, DeLong via placements), "
    "bootstrap CIs to reported rounding with identical seed and "
    "numpy.random.default_rng(seed)."
)
#: Master section 5.1 X1, the T7 sentence, verbatim.
X1_SENTENCE = (
    "Differences are reported against the declared reference level and against the "
    "complement of the subgroup (all other rows); both use Newcombe (1998) method 10 for "
    "proportions and unpaired DeLong for AUROC. No difference is reported against the "
    "overall cohort because the subgroup is part of it."
)
#: Master section 3.1 (CHK B5; X3), the conventions sentence, verbatim.
CONVENTIONS_SENTENCE = (
    "Reporting conventions, not acceptance criteria: the vendor-set numbers in ProofPack are "
    'k-suppression (n<10, events<5, non-events<5), AUROC "not evaluable" below 10 '
    "positives/10 negatives, low-n tiers (n<10, n<30), the 200/200 calibration-curve flag "
    '(after Van Calster 2019), and the bootstrap B. Each is labelled "ProofPack reporting '
    'convention" wherever it appears (T7, T8, /trust) and none produces a status word.'
)
#: D4 section 1.2's tier definitions (fifth bullet), the legend the tables use.
TIER_LEGEND: tuple[tuple[str, str], ...] = (
    ("ᵃ", "n < 10: not evaluable, shown for transparency"),
    ("ᵇ", "10 <= n < 30 or events < 5: very low precision"),
    ("ᶜ", "Wilson half-width > 0.10: imprecise"),
)

#: One fixed description per ``Number.method``; T7 prints the ones the run used.
METHOD_DESCRIPTIONS: dict[str, str] = {
    "wilson": (
        "Wilson score interval without continuity correction, for a proportion k/n on "
        "independent rows. Clopper-Pearson is not printed beside it at k = 0 or k = n in this "
        "build (D4 section 1.2 asks for it; carried)."
    ),
    "wilson_cc": "Wilson score interval with continuity correction.",
    "clopper_pearson": "Clopper-Pearson exact interval for a proportion.",
    "newcombe10": (
        "Newcombe (1998) method 10: a difference between two independent proportions from "
        "their two Wilson intervals (subgroup differences, fairness gaps, Youden J, balanced "
        "accuracy)."
    ),
    "newcombe11": "Newcombe (1998) method 11, the continuity-corrected companion of method 10.",
    "newcombe_paired": "Newcombe's interval for a difference between paired proportions.",
    "delong_wald": (
        "DeLong variance of the AUROC from placements (the Sun and Xu algorithm) with a Wald "
        "interval; for a difference between disjoint groups the two variances add (unpaired "
        "DeLong)."
    ),
    "delong_logit": "DeLong variance of the AUROC with the interval formed on the logit scale.",
    "cluster_bootstrap_percentile": (
        "Cluster bootstrap: cases, not rows, resampled (within outcome class where the "
        "statistic needs both classes), percentile interval, with the seed and B of section "
        "1. Used where rows are clustered; the analytic interval is then refused with the "
        "typed reason clustered_data_analytic_ci_invalid."
    ),
    "bootstrap_percentile": (
        "Stratified bootstrap over rows within outcome class, percentile interval (the Brier "
        "score, reference Brier and IPA), with the seed and B of section 1."
    ),
    "bootstrap_bca": "Bootstrap interval with bias correction and acceleration (BCa).",
    "irls_wald": (
        "Calibration-in-the-large, slope and intercept fitted by the engine's own "
        "Newton-Raphson (IRLS) with a Wald interval from the observed information."
    ),
    "log_delta": (
        "Delta method on the log scale (the observed-to-expected ratio; LR+, LR- and the "
        "diagnostic odds ratio)."
    ),
    "logit_delta": (
        "Delta method on the logit scale for PPV and NPV at a declared prevalence (after "
        f"Mercaldo 2007 {UNVERIFIED_MARK}, {PENDING})."
    ),
    "chi2_psi": "Population stability index against its chi-square critical value.",
    "exact_mcnemar": "Exact McNemar test on the discordant pairs.",
    "cc_mcnemar": "Continuity-corrected McNemar test on the discordant pairs.",
    "none": (
        "No interval: the Number carries a typed reason, printed as n.e. with the reason "
        "code, and no other method is substituted."
    ),
}
#: Blocks of run.json whose presence names an analysis the run performed.
NOT_RUN_BLOCKS: tuple[tuple[str, str], ...] = (
    ("robustness", "robustness analyses (leave-one-site-out, threshold and missingness)"),
    ("comparison", "version comparison (T2)"),
    ("drift", "drift and period monitoring (T3)"),
)


def number_objects(node: Any):
    """Every Number object in ``node`` (the T8 section 7 walk)."""
    yield from render_html._walk_numbers(node)


def methods_used(document: dict[str, Any]) -> Counter:
    """``{method: count}`` over every Number object of the document."""
    return Counter(str(n.get("method")) for n in number_objects(document))


def load_citations(path: str | Path | None = None) -> list[dict[str, Any]]:
    """The citation register (``design/citations.yaml`` unless ``path`` names another)."""
    src = Path(path) if path is not None else resource_path("citations.yaml")
    data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    return [c for c in data.get("citations") or [] if isinstance(c, dict)]


def features(document: dict[str, Any], methods: Counter) -> set[str]:
    """The method ids and block words a citation's ``used_by`` may name."""
    out = set(methods)
    if document.get("subgroups"):
        out.add("subgroups")
    if isinstance(document.get("calibration"), dict):
        out.add("calibration")
    if isinstance(document.get("fairness"), dict):
        out.add("fairness")
    if (document.get("flow") or {}).get("clustered"):
        out.add("clustered")
    if any((o or {}).get("ppv_at_prevalence") for o in (document.get("overall") or {}).values()):
        out.add("prevalence")
    return out


def _citation_row(c: dict[str, Any]) -> dict[str, Any]:
    verified = c.get("verified") is True
    return {
        "id": fmt.text(c.get("id")),
        "text": fmt.text(c.get("text")),
        "source": fmt.text(c.get("source")),
        "url": fmt.text(c.get("url")) or None,
        "verified": verified,
        "mark": "" if verified else f"{UNVERIFIED_MARK} {PENDING}",
    }


def _conventions() -> dict[str, str]:
    text = resource_path("conventions_T7.md").read_text(encoding="utf-8")
    return markdown.sections(text)


def _section(sections: dict[str, str], prefix: str) -> str:
    for key, body in sections.items():
        if key.startswith(prefix):
            return markdown.to_html(body, shift=1)
    raise KeyError(f"conventions_T7.md has no section starting {prefix!r}")


def t7_context(
    document: dict[str, Any],
    guidance_map: Any = None,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    m = document["manifest"]
    methods = methods_used(document)
    feats = features(document, methods)
    cites = load_citations() if citations is None else citations
    used = [_citation_row(c) for c in cites if set(c.get("used_by") or []) & feats]
    open_items = [_citation_row(c) for c in cites if c.get("verified") is not True]
    refs = anchors.resolve(list(T7_ANCHORS.values()), guidance_map)
    by_id = {r["id"]: r for r in refs}
    conv = _conventions()
    flow = document.get("flow") or {}
    decl = document.get("declarations") or {}
    boot = decl.get("bootstrap") or {}
    clustering = decl.get("clustering") or {}
    cal_reason = document.get("calibration_suppressed_reason")
    ctx: dict[str, Any] = {
        "template_name": "T7 · Methods appendix",
        "software_rows": [
            ("Engine version", fmt.text(m.get("engine_version"))),
            ("Python", fmt.text(m.get("python"))),
            ("numpy", fmt.text(m.get("numpy"))),
            ("scipy", fmt.text(m.get("scipy")) or "not installed"),
            ("Platform", fmt.text(m.get("platform"))),
            ("Reference platform", fmt.scalar(m.get("reference_platform"))),
            ("Seed", fmt.scalar(m.get("seed"))),
            ("Bootstrap resamples (B)", fmt.scalar(m.get("B"))),
            ("Bootstrap interval", fmt.text(boot.get("interval")) or "percentile"),
        ],
        "tolerance_policy": TOLERANCE_POLICY,
        "mapping_sha256": fmt.text(m.get("mapping_sha256")) or "not recorded",
        "halts": [fmt.text(h) for h in document.get("halts") or []],
        "warning_codes": [fmt.text(w.get("code")) for w in document.get("warnings") or []],
        "flow_rows": flow_rows(document),
        "clustering": {
            "declared": fmt.text(clustering.get("unit")) or "none",
            "clustered": bool(flow.get("clustered")),
            "route": fmt.text(flow.get("clustering_route")) or "none",
            "n_cases": fmt.count(flow.get("n_cases")),
        },
        "methods": [
            {
                "id": method,
                "description": METHOD_DESCRIPTIONS.get(method, "no description is recorded"),
                "count": fmt.count(n),
            }
            for method, n in sorted(methods.items())
        ],
        "has_subgroups": bool(document.get("subgroups")),
        "x1_sentence": X1_SENTENCE,
        "subgroup_conventions": _section(conv, "Subgroup tables"),
        "has_calibration": isinstance(document.get("calibration"), dict),
        "calibration_reason": (
            {
                "reason": fmt.text(cal_reason.get("reason")),
                "score_type": fmt.text(cal_reason.get("score_type")),
                "orientation": fmt.text(cal_reason.get("orientation")),
            }
            if isinstance(cal_reason, dict)
            else None
        ),
        "calibration_conventions": _section(conv, "Calibration"),
        "has_cluster_bootstrap": "cluster_bootstrap_percentile" in methods,
        "coverage_conventions": _section(conv, "Cluster-bootstrap coverage bar"),
        "fairness": _fairness(document),
        "conventions_sentence": CONVENTIONS_SENTENCE,
        "conventions_intro": markdown.to_html(conv.get("", "").split("\n", 1)[-1], shift=1),
        "tier_legend": TIER_LEGEND,
        "not_run": [label for key, label in NOT_RUN_BLOCKS if not document.get(key)],
        "citations_used": used,
        "open_items": open_items,
        "guidance_refs": refs,
        "anchor": {key: by_id[value] for key, value in T7_ANCHORS.items()},
    }
    ctx.update(render_html.furniture(document, "T7", refs))
    return ctx


def _fairness(document: dict[str, Any]) -> dict[str, Any] | None:
    f = document.get("fairness")
    if not isinstance(f, dict):
        return None
    return {
        "definitions": [
            # sorted: the page is the same from the in-memory document and from run.json,
            # whose canonical serialisation sorts keys
            (fmt.text(k), fmt.text(v))
            for k, v in sorted((f.get("gap_definitions") or {}).items())
        ],
        "citation": fmt.text(f.get("impossibility_citation")),
        "pending": PENDING,
    }


def flow_rows(document: dict[str, Any]) -> list[tuple[str, str]]:
    """D4 section 5.10's flow table, in its order."""
    flow = document.get("flow") or {}
    return [
        ("Rows read", fmt.count(flow.get("rows_read"))),
        ("Excluded: missing label", fmt.count(flow.get("excluded_missing_label"))),
        ("Excluded: missing score", fmt.count(flow.get("excluded_missing_score"))),
        ("Indeterminate", fmt.count(flow.get("indeterminate"))),
        ("Analysed", fmt.count(flow.get("analysed"))),
        ("Cases (clusters)", fmt.count(flow.get("n_cases"))),
        ("Sites", fmt.count(flow.get("n_sites"))),
        ("Clustered path used", "yes" if flow.get("clustered") else "no"),
    ]


def render_t7(
    document: dict[str, Any],
    *,
    guidance_map: Any = None,
    citations: list[dict[str, Any]] | None = None,
) -> str:
    env = render_html.environment()
    ctx = t7_context(document, guidance_map, citations)
    return render_html.neutralise_bidi(env.get_template(T7_FILE).render(**ctx))


def write_t7(document: dict[str, Any], out_dir: str | Path) -> Path:
    target = Path(out_dir) / T7_FILE
    target.write_bytes(render_t7(document).encode("utf-8"))
    return target
