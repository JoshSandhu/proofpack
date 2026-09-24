"""T12, the software assurance record (D1 section 1's T12 row and the day-9 row; A-P3).

A CSA-structured page (intended use, failure modes, assurance evidence, the manufacturer's
installation and operational checks) rendered from ``fixtures_report.json`` alone, through
``base.html``'s furniture. It is written by ``proofpack fixtures --html`` beside the
report, under the licence rule ``run`` applies to T8 (the page is written only when the
licence is ``ok`` or ``grace``; ``tests/test_t12.py::
test_fixtures_html_writes_t12_under_a_licence_and_not_without`` writes the report without
a licence and no T12).

Where each part comes from:

* **intended use** - a customer-text slot (:data:`INTENDED_USE_SLOT`); ProofPack has no
  input for it in this version, so the page prints the placeholder
  (:data:`proofpack.scope.PLACEHOLDER`) and the cover carries the INCOMPLETE stamp;
* **failure modes** - every code in :mod:`proofpack.errors` (the twelve H-gates, the S- and
  E-codes, the W-codes and the exit codes) with the condition it inspects (the module's
  own one-line text) and the engine action :func:`failure_mode_rows` gives it; the codes
  no engine path raises (:data:`NOT_RAISED`) say so in that column;
* **assurance evidence** - every row of the report, whatever its status
  (``tests/test_t12.py::test_every_report_row_appears_in_t12``);
* **installation and operational checks** - the report's ``doctor`` rows, the report's
  counts, and two steps the manufacturer's RA lead performs (mapping verification and
  the declaration-echo check), each with blank fields for the person, the date and the
  signature: ProofPack signs nothing;
* **determinism** - D1 section 9's tolerance text (``render.t7.TOLERANCE_POLICY``) and the
  F17 sentence naming the masked keys and the reference platform.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from proofpack import errors
from proofpack.render import anchors
from proofpack.render import html as render_html
from proofpack.render.t7 import TOLERANCE_POLICY
from proofpack.scope import PLACEHOLDER

T12_FILE = "T12.html"
T12_ANCHORS: dict[str, str] = {
    "scope": "PP_SCOPE",
    "evidence": "FDA_AIDSF_PERF_VALIDATION",
    "determinism": "PP_METHODS",
}
#: The words the status cell prints for each report status.
STATUS_TEXT: dict[str, str] = {
    "matched": "matched",
    "not_matched": "not matched",
    "no_oracle_recorded": "no oracle recorded",
    "not_built": "not built in this version",
    "suite_only": "compared by the test suite only",
}
INTENDED_USE_SLOT = (
    "CT-T12",
    "intended use of ProofPack in the manufacturer's process, and the records its output enters",
)
SUPPORTS_SENTENCE = "This record supports, does not replace, the manufacturer's own validation."
PRINT_SENTENCE = (
    "ProofPack writes no PDF in this version (D4 section 9): to keep this record as a PDF, "
    "print this HTML page to PDF from a browser."
)
F17_SENTENCE = (
    "Two runs of the same inputs on the same platform are compared as the manifest and the "
    "bytes of run.json with run_id, started and duration_s masked (F17; "
    "scripts/f17_determinism.py). Hash identity is claimed on the reference platform only, "
    "python:3.12-slim linux/amd64 with the pinned lockfile."
)
CSA_SENTENCE = (
    "Structured after FDA's Computer Software Assurance approach: intended use, failure "
    "modes, assurance evidence and the records the manufacturer keeps."
)
CSA_UNVERIFIED = (
    "[unverified: the current version and status of FDA's Computer Software Assurance "
    "guidance were not fetched for this build]"
)


#: Codes defined in :mod:`proofpack.errors` that no engine path raises in this version, and
#: what fires instead (lens FA-R4: ``gates.gate_h10`` creates ``Finding("W10", ...)``).
NOT_RAISED: dict[str, str] = {
    "H10": "not raised in this version: gates.gate_h10 emits W10 (a warning, below)",
}
#: Warning codes whose exit behaviour differs from the other W-codes' (lens RG-B1).
WARNING_ACTIONS: dict[str, str] = {
    "W16": "flag only: one line printed after run.json is written, not in the document; "
    "the exit code is the run's own (exit 0 with the W16 line in tests/test_telemetry.py::"
    "test_a_302_through_the_cli_prints_w16_and_the_location_host_receives_nothing)",
}
WARNING_ACTION = "warning: the run completes; exit 2 unless another code sets it"


def failure_mode_rows() -> list[dict[str, str]]:
    """One row per engine code: what it inspects and the engine action printed for it."""
    rows: list[dict[str, str]] = []
    for code, text in errors.HALT_CODES.items():
        does = (
            NOT_RAISED[code]
            if code in NOT_RAISED
            else "flag only: the run completes and the code is recorded"
            if code in errors.FLAG_ONLY_CODES
            else "HALT: exit 3, no document written"
        )
        rows.append({"code": code, "inspects": text, "does": does, "kind": "gate"})
    for code, text in errors.SCHEMA_CODES.items():
        rows.append(
            {
                "code": code,
                "inspects": text,
                "does": "HALT: exit 3, no document written",
                "kind": "schema",
            }
        )
    for code, text in errors.MAPPING_CODES.items():
        rows.append(
            {
                "code": code,
                "inspects": text,
                "does": "HALT: exit 3, no document written",
                "kind": "mapping",
            }
        )
    for code, text in errors.WARN_CODES.items():
        rows.append(
            {
                "code": code,
                "inspects": text,
                "does": WARNING_ACTIONS.get(code, WARNING_ACTION),
                "kind": "warning",
            }
        )
    exits = (
        (errors.EXIT_OK, "no HALT, no warning other than W16, a usable licence"),
        (errors.EXIT_WARNINGS, "one or more warnings"),
        (errors.EXIT_HALT, "a HALT code fired; nothing written"),
        (errors.EXIT_LICENCE, "no usable licence; run.json written with the watermark"),
        (errors.EXIT_INTERNAL, "an internal error"),
        (
            errors.EXIT_FIXTURES_NOT_MATCHED,
            "proofpack fixtures: one or more rows with an oracle not matched",
        ),
    )
    for code, text in exits:
        rows.append({"code": f"exit {code}", "inspects": text, "does": "", "kind": "exit"})
    return rows


def _dev(value: Any) -> str:
    if value is None:
        return "—"
    return "0" if value == 0 else f"{float(value):.2e}"


def _tolerance(t: dict[str, Any] | None) -> str:
    if not t:
        return "—"
    if t.get("value") is None:
        return f"{t['class'].replace('_', ' ')}: half a unit in the last printed decimal"
    return f"{t['class'].replace('_', ' ')}: {float(t['value']):.0e}"


def _oracle(src: dict[str, Any] | None) -> dict[str, Any]:
    if not src:
        return {"file": "—", "entry": "", "marking": None}
    return {
        "file": src["file"],
        "entry": src["entry"],
        "marking": src.get("marking") if src.get("unverified") else None,
    }


def evidence_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for r in report["rows"]:
        reason = r.get("reason") or ""
        out.append(
            {
                "id": r["id"],
                "fixture": r["fixture"],
                "what": r["what_is_compared"],
                "oracle": _oracle(r.get("oracle_source")),
                "tolerance": _tolerance(r.get("tolerance")),
                "deviation": _dev(r.get("max_abs_deviation")),
                "n": str(r.get("n_values_compared", 0)),
                "status": r["status"],
                "status_text": STATUS_TEXT[r["status"]],
                "reason": reason,
                "reason_unverified": reason.startswith("[unverified"),
                "suite_tests": ", ".join(r.get("suite_tests") or []),
            }
        )
    return out


def environment_rows(report: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("Engine version", str(report["engine_version"])),
        ("Git commit", report["git_sha"] or "not recorded"),
        ("Git commit source", str(report["git_sha_source"])),
        ("Platform", str(report["platform"])),
        ("Reference platform", str(report["reference_platform"])),
        ("On the reference platform", "yes" if report["on_reference_platform"] else "no"),
        ("Python", str(report["python"])),
        ("numpy", str(report["numpy"])),
        ("scipy", report["scipy"] or "not installed"),
        ("Report generated (UTC)", str(report["generated"])),
    ]


def doctor_rows(report: dict[str, Any]) -> list[dict[str, str]]:
    """``flagged`` is doctor's own mark: "yes" where doctor printed the check as not ok. The
    column does not say that a check's condition holds: ``doctor.run_checks`` passes
    ``ok=True`` as a literal for the reference platform, network, scipy and docx rows
    (lens FA-R3)."""
    return [
        {
            "name": d["name"],
            "flagged": "no" if d["ok"] else "yes",
            "essential": "yes" if d["essential"] else "no",
            "info": d["info"],
        }
        for d in report.get("doctor") or []
        # the licence row is not printed: T12 is written only under a usable licence, and
        # the licence state is the cover stamp's (tests/test_t12.py, the forbidden grep)
        if d["name"] != "licence"
    ]


def t12_context(
    report: dict[str, Any], *, watermark: str | None = None, guidance_map: Any = None
) -> dict[str, Any]:
    refs = anchors.resolve(list(T12_ANCHORS.values()), guidance_map)
    by_id = {r["id"]: r for r in refs}
    slot_id, slot_title = INTENDED_USE_SLOT
    pseudo = {
        "manifest": {
            "engine_version": report["engine_version"],
            "started": report["generated"],
            "run_id": "",
            "watermark": watermark,
        },
        "declarations": {},
    }
    s = report["summary"]
    ctx: dict[str, Any] = {
        "template_name": "T12 · Software assurance record (CSA-structured)",
        "report": report,
        "slot": {
            "id": slot_id,
            "title": slot_title,
            "text": PLACEHOLDER.format(title=slot_title),
        },
        "failure_modes": failure_mode_rows(),
        "evidence": evidence_rows(report),
        "environment": environment_rows(report),
        "doctor": doctor_rows(report),
        "doctor_flagged": sum(1 for d in doctor_rows(report) if d["flagged"] == "yes"),
        "summary": s,
        "tolerance_rules": [
            (k.replace("_", " "), v) for k, v in report["tolerance_policy"].items() if k != "source"
        ],
        "tolerance_policy": TOLERANCE_POLICY,
        "f17_sentence": F17_SENTENCE,
        "platform_sentence": (
            f"This report was generated on {report['platform']}, which "
            + ("is" if report["on_reference_platform"] else "is not")
            + " the reference platform."
        ),
        "supports_sentence": SUPPORTS_SENTENCE,
        "print_sentence": PRINT_SENTENCE,
        "csa_sentence": CSA_SENTENCE,
        "csa_unverified": CSA_UNVERIFIED,
        "guidance_refs": refs,
        "anchor": {
            key: anchors.with_note_fields(by_id[value], guidance_map)
            for key, value in T12_ANCHORS.items()
        },
    }
    ctx.update(render_html.furniture(pseudo, "T12", refs, outstanding=1))
    ctx["header_engine"] = (
        f"T12 · ProofPack v{report['engine_version']} · fixtures report {str(report['generated'])}"
    )
    ctx["title"] = ctx["header_engine"]
    return ctx


def render_t12(
    report: dict[str, Any], *, watermark: str | None = None, guidance_map: Any = None
) -> str:
    env = render_html.environment()
    html = env.get_template(T12_FILE).render(
        **t12_context(report, watermark=watermark, guidance_map=guidance_map)
    )
    return render_html.neutralise_bidi(html)


def write_t12(report: dict[str, Any], out_dir: str | Path, *, watermark: str | None = None) -> Path:
    target = Path(out_dir) / T12_FILE
    target.write_bytes(render_t12(report, watermark=watermark).encode("utf-8"))
    return target
