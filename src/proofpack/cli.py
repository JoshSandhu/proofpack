"""``proofpack`` command line (D1 section 7). Day 1 surface: doctor, map, run (ingest only).

Exit codes: 0 ok, 2 warnings only, 3 HALT, 4 licence, 5 internal.
On HALT nothing is written to ``--out``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from proofpack import __version__
from proofpack.errors import (
    EXIT_HALT,
    EXIT_INTERNAL,
    EXIT_OK,
    EXIT_WARNINGS,
    HaltError,
    ProofPackError,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="proofpack", description="ProofPack engine")
    p.add_argument("--version", action="version", version=f"proofpack {__version__}")
    # Global flags are accepted both before and after the subcommand
    # (`proofpack --offline doctor` and `proofpack doctor --offline`, per D1 section 7).
    common = argparse.ArgumentParser(add_help=False)
    for parser, default in ((p, False), (common, argparse.SUPPRESS)):
        parser.add_argument("--offline", action="store_true", default=default, help="zero sockets")
        parser.add_argument("--quiet", action="store_true", default=default)
        parser.add_argument(
            "--json-log", action="store_true", default=default, help="machine-readable messages"
        )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="environment self-check", parents=[common])

    m = sub.add_parser("map", help="header-only mapping (day 1 stub)", parents=[common])
    m.add_argument("--input", required=True)
    m.add_argument("--criteria")
    m.add_argument("--out", default="mapping.json")
    m.add_argument(
        "--yes",
        action="store_true",
        help="non-interactive; requires prior mapping.json with the same header set",
    )

    r = sub.add_parser(
        "run", help="ingest + HALT gates (statistics land on later days)", parents=[common]
    )
    r.add_argument("--input", required=True)
    r.add_argument("--criteria", required=True)
    r.add_argument("--mapping")
    r.add_argument("--out", default="./pack")
    r.add_argument("--yes", action="store_true")

    c = sub.add_parser(
        "compare", help="paired ingest of new vs prior (gate H12 only on day 1)", parents=[common]
    )
    c.add_argument("--input", required=True)
    c.add_argument("--prior", required=True)
    c.add_argument("--criteria", required=True)
    c.add_argument("--mapping")
    c.add_argument("--out", default="./pack")
    c.add_argument("--yes", action="store_true")
    c.add_argument("--allow-unpaired", action="store_true")
    return p


def _emit(args: argparse.Namespace, payload: dict, text: str) -> None:
    if args.quiet:
        return
    if args.json_log:
        print(json.dumps(payload))
    else:
        print(text)


def cmd_doctor(args: argparse.Namespace) -> int:
    from proofpack.doctor import doctor_ok, format_checks, run_checks

    checks = run_checks(offline=args.offline)
    _emit(args, {"doctor": [c.__dict__ for c in checks]}, format_checks(checks))
    return EXIT_OK if doctor_ok(checks) else EXIT_INTERNAL


def cmd_map(args: argparse.Namespace) -> int:
    from proofpack.io import declare, mapping
    from proofpack.io.schema import load_table

    raw = load_table(args.input)
    period = declare.load(args.criteria).period if args.criteria else None
    mapping.check_h11(raw.headers, period)
    m = mapping.check_h07(raw.headers, args.out, non_interactive=args.yes)
    m.write(args.out)
    rows = "\n".join(
        f"  {r.original!r:30} -> {r.role or '(unused)':16} {r.confidence}" for r in m.roles
    )
    _emit(
        args,
        {"mapping": m.to_dict()},
        f"mapping written to {args.out} (decided_by={m.decided_by})\n{rows}\n"
        "Next step: review the roles, then proofpack run --input ... --criteria ...",
    )
    return EXIT_OK


def cmd_run(args: argparse.Namespace) -> int:
    from proofpack.gates import ingest
    from proofpack.io import declare
    from proofpack.io.schema import load_table

    decl = declare.load(args.criteria)
    raw = load_table(args.input)
    result = ingest(raw, decl, mapping_path=args.mapping, non_interactive=args.yes)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = result.report()
    (out / "ingest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    result.mapping.write(out / "mapping.json")
    warn_lines = "".join(f"\n  [{w.code}] {w.message}" for w in result.warnings)
    _emit(
        args,
        {"run": report},
        f"ingest ok: {report['flow']['included']} rows included of {report['n_rows']}"
        f"{warn_lines}\nwritten: {out / 'ingest_report.json'}\n"
        "Next step: statistics and templates land on later build days.",
    )
    return result.exit_code


def cmd_compare(args: argparse.Namespace) -> int:
    from proofpack.gates import check_paired, ingest
    from proofpack.io import declare
    from proofpack.io.schema import load_table

    decl = declare.load(args.criteria)
    new = ingest(load_table(args.input), decl, mapping_path=args.mapping, non_interactive=args.yes)
    prior = ingest(
        load_table(args.prior), decl, mapping_path=args.mapping, non_interactive=args.yes
    )
    w12 = check_paired(new.table, prior.table, allow_unpaired=args.allow_unpaired)
    warnings = new.warnings + prior.warnings + ([w12] if w12 else [])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "new": new.report(),
        "prior": prior.report(),
        "paired": w12 is None,
        "warnings": [{"code": w.code, "message": w.message} for w in warnings],
    }
    (out / "compare_ingest_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    _emit(
        args,
        {"compare": report},
        f"compare ingest ok (paired={w12 is None}); written: "
        f"{out / 'compare_ingest_report.json'}\n"
        "Next step: paired statistics land on the comparison build day.",
    )
    return EXIT_WARNINGS if warnings else EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = {"doctor": cmd_doctor, "map": cmd_map, "run": cmd_run, "compare": cmd_compare}[
        args.command
    ]
    try:
        return handler(args)
    except HaltError as exc:
        payload = {"halt_code": exc.code, "message": exc.message, "detail": exc.detail}
        if args.json_log:
            print(json.dumps(payload), file=sys.stderr)
        elif not args.quiet:
            print(f"HALT {exc.code}: {exc.message}", file=sys.stderr)
            if exc.detail:
                print(f"  detail: {json.dumps(exc.detail)}", file=sys.stderr)
            print("  No document was written.", file=sys.stderr)
        return EXIT_HALT
    except ProofPackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", EXIT_INTERNAL)
    except Exception as exc:  # noqa: BLE001 - internal failure must map to exit 5
        print(f"internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
