"""``proofpack`` command line (D1 section 7). Day 1 surface: doctor, map, run (ingest only).

Exit codes: 0 ok, 2 warnings only, 3 HALT, 4 licence, 5 internal.
On HALT nothing is written to ``--out``.
"""

from __future__ import annotations

import argparse
import json
import os
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

    m = sub.add_parser(
        "map", help="map original headers to canonical roles (D1 section 5)", parents=[common]
    )
    m.add_argument("--input", required=True)
    m.add_argument("--criteria")
    m.add_argument("--out", default="mapping.json")
    m.add_argument(
        "--yes",
        action="store_true",
        help="non-interactive; accepted only when every role is high and a prior "
        "mapping.json with the same header-set hash exists at --out",
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


def _stdin_is_terminal() -> bool:
    """Whether a human can answer a prompt on stdin.

    ``isatty()`` alone is not enough on Windows: with ``stdin=DEVNULL`` it returned True and
    ``input()`` then raised EOFError (measured 18 September 2026, Python 3.14, Windows 11;
    ``tests/test_mapping_full.py::test_non_tty_with_stdin_closed_exits_3_within_the_timeout``).
    ``GetConsoleMode`` returned 0 for that handle. On a real console handle (a fresh console
    window started with PowerShell ``Start-Process python``, 18 September 2026, repair 1)
    ``isatty()`` was True and this function returned True. Not measured: mintty (Git Bash's
    own terminal), where Python's stdin is a pipe. ``_confirm_interactive`` maps EOFError
    and KeyboardInterrupt at the prompt to H07 as well.
    """
    try:
        if not sys.stdin.isatty():
            return False
    except (AttributeError, ValueError):
        return False
    if os.name == "nt":
        import ctypes
        import msvcrt

        try:
            handle = msvcrt.get_osfhandle(sys.stdin.fileno())
            mode = ctypes.c_uint32()
            return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)))
        except (OSError, ValueError, AttributeError):
            return False
    return True


def _ask(ask, prompt: str) -> str:
    """One prompt; a closed stdin or Ctrl-C at it is the H07 abort, not a traceback.

    At 555a5e1 ``KeyboardInterrupt`` raised by ``input`` left ``main()`` uncaught
    (repair 1, FA-N5; ``tests/test_mapping_repair1.py::test_ctrl_c_at_the_prompt_is_h07``
    and ``::test_eof_at_the_prompt_is_h07`` each raise the exception from ``input`` at the
    per-role prompt and at the all-high prompt and assert exit 3 and no ``Traceback``).
    """
    try:
        return (ask(prompt) or "").strip().lower()
    except EOFError:
        raise HaltError(
            "H07", "stdin closed at the prompt: run interactively or pass --yes"
        ) from None
    except KeyboardInterrupt:
        raise HaltError("H07", "mapping interrupted at the prompt; nothing written") from None


def _confirm_interactive(m, ask=None, say=print) -> None:
    """Prompt once per non-high role: accept / edit (a canonical role or ignore) / abort;
    when no role is below high, prompt once for the whole mapping (accept / abort).

    ``ask`` (default ``input``, resolved at call time) and ``say`` are injectable so the
    prompt is testable without a terminal. Raises H07 on abort. Mutates ``m`` in place
    and sets ``decided_by`` to interactive after at least one answer was given (at 555a5e1
    an all-high table asked nothing and was still written as ``interactive`` - repair 1,
    FA-N2; ``tests/test_mapping_repair1.py::test_all_high_table_asks_once_before_interactive``).
    Accept and edit leave ``confidence`` as computed (the build note's needs-from-Josh 1;
    ``test_accept_and_edit_keep_the_computed_confidence`` pins the literal values).
    """
    from proofpack.io.mapping import IGNORE
    from proofpack.io.schema import canonical_columns

    ask = ask or input
    allowed = set(canonical_columns()) | {IGNORE}
    pending = list(m.non_high)
    if not pending:
        answer = _ask(ask, f"every role is high ({len(m.roles)} columns): [a]ccept / [q]uit? ")
        if answer in ("q", "quit", "abort"):
            raise HaltError("H07", "mapping aborted at the prompt; nothing written")
        m.decided_by = "interactive"
        return
    for r in pending:
        while True:
            answer = _ask(
                ask,
                f"{r.original!r} -> {r.role_label} ({r.confidence}): [a]ccept / [e]dit / [q]uit? ",
            )
            if answer in ("a", "accept", ""):
                r.notes.append("accepted interactively")
                break
            if answer in ("q", "quit", "abort"):
                raise HaltError("H07", "mapping aborted at the prompt; nothing written")
            if answer in ("e", "edit"):
                new_role = _ask(ask, "canonical role name, or ignore: ")
                if new_role not in allowed and not new_role.startswith(("attr_", "rater_")):
                    say(f"  not a canonical role: choose one of {', '.join(sorted(allowed))}")
                    continue
                holder = None
                if new_role != IGNORE:
                    holder = next((o for o in m.roles if o is not r and o.role == new_role), None)
                if holder is not None:
                    # apply_mapping would halt H07 on it later (repair 1, FA-N4;
                    # test_edit_to_a_role_another_column_holds_is_refused_at_the_prompt)
                    say(f"  {new_role} is already held by {holder.original!r}: choose another")
                    continue
                r.role = None if new_role == IGNORE else new_role
                r.notes.append("edited interactively")
                break
            say("  answer a, e or q")
    m.decided_by = "interactive"


def _tolerant_console() -> None:
    """Make stdout/stderr replace unencodable characters instead of raising.

    At 555a5e1 ``PYTHONIOENCODING=cp1252`` and a CJK header ended in exit 5
    ``internal error: UnicodeEncodeError`` before the table (repair 1, FA-N8;
    ``tests/test_mapping_repair1.py::test_cp1252_stdout_prints_the_table_with_escapes``).
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            continue


def cmd_map(args: argparse.Namespace) -> int:
    from proofpack.io import declare, mapping
    from proofpack.io.schema import load_table

    _tolerant_console()
    raw = load_table(args.input)
    period = declare.load(args.criteria).period if args.criteria else None
    fresh = mapping.map_headers(raw.headers, raw.columns)
    mapping.check_h11(raw.headers, period, mapping=fresh)
    table = fresh.table()
    if args.yes:
        m = mapping.check_h07(raw.headers, args.out, non_interactive=True, fresh=fresh)
    else:
        tty = _stdin_is_terminal()
        # --quiet keeps the table off a non-terminal stdout; at a terminal the prompts
        # follow, so the table they refer to is printed (repair 1, FA-N12;
        # test_quiet_at_a_terminal_prints_the_table_the_prompt_refers_to)
        if not args.json_log and (not args.quiet or tty):
            print(table)
        if not tty:
            raise HaltError(
                "H07",
                "stdin is not a terminal: run interactively or pass --yes with a prior "
                "mapping.json",
                {"non_high_roles": len(fresh.non_high)},
            )
        m = fresh
        _confirm_interactive(m)
    m.write(args.out)
    _emit(
        args,
        {"mapping": m.to_dict(), "file_sha256": m.file_sha256},
        f"mapping written to {args.out} (decided_by={m.decided_by}, "
        f"sha256={m.file_sha256[:12]})\n"
        + (table if args.yes else "")
        + "\nNext step: proofpack run --input ... --criteria ... --mapping "
        + str(args.out),
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
