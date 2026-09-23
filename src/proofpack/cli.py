"""``proofpack`` command line (D1 section 7): doctor, map, run, compare, licence.

Exit codes: 0 ok, 2 warnings only, 3 HALT, 4 licence, 5 internal.
On HALT nothing is written to ``--out``. ``run`` (build day 7, E7: :mod:`proofpack.run`)
needs a confirmed mapping (DEC-26) and writes ``run.json`` - the assembled document -
under ``--out``; on a licence that is expired past grace, refused or absent it still
writes the JSON with the expired watermark and exits 4 (D1 section 7: "after grace
run/compare emit JSON only; doctor, map, fixtures always work"). Build day 8 (E8):
``--format json,html`` (the default) also writes ``T8.html`` beside ``run.json`` when
the licence is ``ok`` or ``grace``; ``--templates T8`` (default) names the documents,
and T1 / T7 print a typed "not built in E8" line rather than a traceback.
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
    EXIT_LICENCE,
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
        help="non-interactive; accepted only when a prior mapping.json with the same "
        "header-set hash exists at --out and every role in it is high or was accepted "
        "or edited at the prompt (confirmed: true)",
    )

    r = sub.add_parser(
        "run",
        help="ingest, HALT gates, statistics, criteria and manifest -> <out>/run.json",
        parents=[common],
    )
    r.add_argument("--input", required=True)
    r.add_argument("--criteria", required=True)
    r.add_argument(
        "--mapping",
        help="a confirmed mapping.json (proofpack map); default <input>.mapping.json beside "
        "the input (DEC-26: run never proposes a mapping itself)",
    )
    r.add_argument("--out", default="./pack")
    r.add_argument(
        "--yes",
        action="store_true",
        help="accepted for compatibility; run is always non-interactive since build day 7",
    )
    r.add_argument(
        "--format",
        default=None,
        help="comma list of json, html (default json,html; HTML is written only when the "
        "licence is ok or in grace)",
    )
    r.add_argument(
        "--templates",
        default=None,
        help="comma list of T1, T7, T8 (default T8; T1 and T7 are not built in E8)",
    )

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

    lic = sub.add_parser("licence", help="show | verify FILE | install FILE", parents=[common])
    lic_sub = lic.add_subparsers(dest="licence_command", required=True)
    lic_sub.add_parser("show", help="status of the installed licence (no signature printed)")
    v = lic_sub.add_parser("verify", help="verify FILE against the shipped public key")
    v.add_argument("file")
    i = lic_sub.add_parser("install", help="verify FILE and copy it to the per-user location")
    i.add_argument("file")
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


#: The answers each prompt takes, after ``_ask`` strips surrounding whitespace and
#: lower-cases (``  A  `` and ``Accept`` read as ``a``). An empty answer (Enter alone)
#: re-prompts at both prompts: at 1354758 it was in the accept tuple and a stray Enter
#: wrote ``decided_by: interactive`` (lens-3 FA-B1;
#: ``tests/test_mapping_repair3.py::test_empty_answer_reprompts_at_both_prompts``).
ACCEPT_ANSWERS = ("a", "accept")
EDIT_ANSWERS = ("e", "edit")
QUIT_ANSWERS = ("q", "quit", "abort")


def _confirm_interactive(m, ask=None, say=print, *, period_column: str | None = None) -> None:
    """Prompt once per non-high role: accept / edit (a canonical role or ignore) / abort;
    when no role is below high, prompt once for the whole mapping (``a`` or ``accept``
    accepts, ``q``, ``quit`` or ``abort`` aborts, after stripping and lower-casing; the
    answers ``n``, ``no``, ``e``, ``x`` and the empty answer print ``answer a or q`` and
    ask again - at e92989b ``n`` was taken as accept, repair 2, RG-N1;
    ``tests/test_mapping_repair2.py::test_all_high_prompt_reprompts_on_n_no_e_x_and_takes_a``;
    the empty answer is lens-3 FA-B1, :data:`ACCEPT_ANSWERS`).

    ``ask`` (default ``input``, resolved at call time) and ``say`` are injectable so the
    prompt is testable without a terminal. Raises H07 on abort. Mutates ``m`` in place
    and sets ``decided_by`` to interactive after at least one answer was given (at 555a5e1
    an all-high table asked nothing and was still written as ``interactive`` - repair 1,
    FA-N2; ``tests/test_mapping_repair1.py::test_all_high_table_asks_once_before_interactive``).
    Accept and edit leave ``confidence`` as computed (the build note's needs-from-Josh 1;
    ``test_accept_and_edit_keep_the_computed_confidence`` pins the literal values); an
    entry accepted or edited at the prompt gets ``confirmed: true`` (DEC-28 for the
    accept, ``tests/test_mapping_repair3.py::
    test_interactive_accept_records_confirmed_and_yes_takes_it``; DEC-42 for the edit -
    at 4fbbf35 an edit left it ``false`` and the file the DEC-31 remedy ``e
    attr_score_flag, a`` wrote was H07 under ``--yes`` on the unconfirmed low,
    ``tests/test_mapping_repair4.py::
    test_e_attr_score_flag_beside_prob_score_passes_yes_and_e_attr_patient_code_too``).
    ``period_column`` (the ``period.column`` of ``--criteria``, when given): an edit to
    ``ignore`` on the entry whose original header equals it is refused with one line
    (``refused: the period declaration names a column mapping.json ignores; ...``) and the
    prompt repeats, because ``run`` halts S03 on such a file
    (``io.mapping.period_for_validate``; ``tests/test_mapping_repair4.py::
    test_an_ignored_visit_named_by_period_column_is_s03_on_both_routes`` feeds ``e ignore
    a`` on ``visit``).

    An accept or an edit that would give a role a second holder among the entries already
    settled (high, or answered earlier in this loop) is refused at the prompt; entries
    still to be asked are not counted, so the first of two ``case_id low`` headers can be
    accepted and the second must be edited (repair 2, FA-B1: at e92989b ``a`` at both
    prompts wrote two ``case_id`` holders; repair 1 checked edits only). An edit to
    ``ignore`` on a column whose folded header equals a role any other entry currently
    holds (settled or pending) is refused with one line naming both headers and the
    role (DEC-31; ``io.mapping.ignore_collision``;
    ``tests/test_mapping_repair3.py::test_ignore_on_a_column_named_for_a_held_role_is_refused_at_the_prompt``
    feeds ``e ignore`` on ``score`` while ``prob`` is proposed ``score``). The accept
    arm and the edit arm run the same check for a role an already-ignored entry is
    named for; ``map_headers`` proposes ``ignore`` on no header that is a role name (it
    ignores an empty or unmapped header only), so that direction is reached by a
    hand-built ``Mapping`` (``score -> ignore high`` beside ``prob -> score low``,
    answered ``a`` then ``e y_pred``:
    ``::test_accept_or_edit_to_a_role_an_ignored_column_is_named_for_is_refused``) and
    not from ``proofpack map`` as measured on the 19 canonical names plus ``attr_x`` and
    ``rater_x`` (lens-1 RG-N1 of repair 3). An edited ``attr_`` / ``rater_``
    name must match the schema's identifier rule (at e92989b ``attr_x y`` was written and
    ``validate`` later dropped it into ``unused_columns``, FA-N5;
    ``::test_edit_prompt_refuses_bare_and_non_identifier_attr_names``).
    """
    from proofpack.io.mapping import IGNORE, PERIOD_IGNORED, ignore_collision
    from proofpack.io.schema import _IDENT, canonical_columns

    ask = ask or input
    allowed = set(canonical_columns()) | {IGNORE}
    pending = list(m.non_high)
    if not pending:
        while True:
            answer = _ask(ask, f"every role is high ({len(m.roles)} columns): [a]ccept / [q]uit? ")
            if answer in ACCEPT_ANSWERS:
                break
            if answer in QUIT_ANSWERS:
                raise HaltError("H07", "mapping aborted at the prompt; nothing written")
            say("  answer a or q")
        m.decided_by = "interactive"
        return

    def collision_line(r, role):
        pair = ignore_collision(m.roles, ignored=r, role=role)
        if pair is None:
            return None
        ignored, name, holder = pair
        return (
            f"  refused: the ignored column {ignored.original!r} is named for the role "
            f"{name} that {holder.original!r} would hold (DEC-31); give one of them another role"
        )

    def held_by(r, role):
        after = next(i for i, x in enumerate(pending) if x is r) + 1
        undecided = {id(x) for x in pending[after:]}
        return next(
            (o for o in m.roles if o is not r and id(o) not in undecided and o.role == role),
            None,
        )

    for r in pending:
        while True:
            answer = _ask(
                ask,
                f"{r.original!r} -> {r.role_label} ({r.confidence}): [a]ccept / [e]dit / [q]uit? ",
            )
            if answer in ACCEPT_ANSWERS:
                holder = held_by(r, r.role) if r.role is not None else None
                if holder is not None:
                    say(
                        f"  {r.role} is already held by {holder.original!r}: "
                        "edit this one (e) to ignore or another role"
                    )
                    continue
                line = collision_line(r, r.role)
                if line is not None:
                    say(line)
                    continue
                r.notes.append("accepted interactively")
                r.confirmed = True
                break
            if answer in QUIT_ANSWERS:
                raise HaltError("H07", "mapping aborted at the prompt; nothing written")
            if answer in EDIT_ANSWERS:
                new_role = _ask(ask, "canonical role name, or ignore: ")
                prefixed = _IDENT.match(new_role) and any(
                    new_role.startswith(p) and len(new_role) > len(p) for p in ("attr_", "rater_")
                )
                if new_role not in allowed and not prefixed:
                    say(
                        f"  not a canonical role: choose one of {', '.join(sorted(allowed))}, "
                        "or attr_<name> / rater_<name> in lower-case letters, digits and _"
                    )
                    continue
                holder = None
                if new_role != IGNORE:
                    holder = held_by(r, new_role)
                if holder is not None:
                    # apply_mapping would halt on it later (repair 1, FA-N4;
                    # test_edit_to_a_role_another_column_holds_is_refused_at_the_prompt)
                    say(f"  {new_role} is already held by {holder.original!r}: choose another")
                    continue
                if new_role == IGNORE and period_column is not None and r.original == period_column:
                    # run would halt S03 on the file (io.mapping.period_for_validate);
                    # refused here so the answers given so far are not lost
                    say(f"  refused: {PERIOD_IGNORED}")
                    continue
                line = collision_line(r, None if new_role == IGNORE else new_role)
                if line is not None:
                    say(line)
                    continue
                r.role = None if new_role == IGNORE else new_role
                r.notes.append("edited interactively")
                r.confirmed = True  # DEC-42: a human chose the role, as at an accept
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
    out_path = Path(args.out)
    if out_path.is_dir():
        # at 1354758 ``--out ./pack`` was answered at the prompts and then exit 5
        # ``PermissionError`` with the full local path (lens-3 FA-N1; carried 6;
        # tests/test_mapping_repair3.py::
        # test_out_naming_an_existing_directory_halts_h07_before_any_prompt)
        # ``C:/`` resolves to a name of "" (lens-1 RG-N6 of repair 3: the message printed
        # "()" and "/mapping.json"; tests/test_mapping_repair3_2.py::
        # test_out_naming_a_drive_root_says_so)
        name = out_path.resolve().name or out_path.name
        shown = name or "a drive root"
        example = f"{name}/mapping.json" if name else "mapping.json inside a directory"
        raise HaltError(
            "H07",
            f"--out names an existing directory ({shown}); pass a file path such as {example}",
            {"out_is_dir": True},
        )
    out_dir = out_path.resolve().parent
    if not out_dir.is_dir():
        # checked before the table and the prompts, so no answer is lost (repair 2,
        # FA-N6: at e92989b this was exit 5 FileNotFoundError after the prompts;
        # tests/test_mapping_repair2.py::
        # test_out_into_a_missing_directory_halts_h07_before_any_prompt)
        raise HaltError(
            "H07",
            "the directory for --out does not exist: create it or pass --out inside an "
            "existing directory",
            {"out_dir_exists": False},
        )
    try:
        raw = load_table(args.input)
        period = declare.load(args.criteria).period if args.criteria else None
        fresh = mapping.map_headers(raw.headers, raw.columns)
        mapping.check_h11(raw.headers, period, mapping=fresh)
        table = fresh.table()
        period_column = period.get("column") if period else None
        if args.yes:
            m = mapping.check_h07(raw.headers, args.out, non_interactive=True, fresh=fresh)
            # the prior route at map: a prior ignoring the declared period column is
            # S03 here as it is at run (repair 4 of A-P1; period_for_validate)
            mapping.period_for_validate(m, period)
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
            _confirm_interactive(m, period_column=period_column)
            # a column proposed ``ignore high`` is not among the prompted entries (the
            # loop asks the non-high roles): the same S03 as run's
            # when the period declaration names it (repair 4 of A-P1)
            mapping.period_for_validate(m, period)
    except KeyboardInterrupt:
        # a BaseException main()'s catch-all does not see; here it is the H07 abort _ask
        # gives at a prompt (repair 2, FA-N10: at e92989b Ctrl-C raised from load_table
        # left main() as a traceback; tests/test_mapping_repair2.py::
        # test_ctrl_c_during_load_is_h07_not_a_traceback)
        raise HaltError("H07", "mapping interrupted; nothing written") from None
    try:
        m.write(args.out)
    except OSError:
        # at b0f60a6 a read-only --out under --yes was exit 5 ``internal error:
        # PermissionError: [Errno 13] Permission denied: '<--out as typed>'`` (lens-1
        # FA-N1 of repair 3; tests/test_mapping_repair3_2.py::
        # test_read_only_out_is_h07_without_the_path). The path is not printed.
        raise HaltError(
            "H07",
            "--out could not be written (permission or a device in the way); pass a "
            "writable file path",
            {"out_written": False},
        ) from None
    except KeyboardInterrupt:
        # at 1354758 Ctrl-C raised from write() after the last prompt left main() as a
        # traceback (lens-3 FA-N7; carried 12; tests/test_mapping_repair3.py::
        # test_ctrl_c_during_write_is_h07_not_a_traceback). The file at --out may be
        # partial, so the message does not say "nothing written".
        raise HaltError(
            "H07",
            "mapping interrupted while writing --out; run proofpack map again",
            {"out_may_be_partial": True},
        ) from None
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
    from proofpack.run import (
        DEFAULT_FORMAT,
        DEFAULT_TEMPLATES,
        LICENCE_FIX,
        assemble_run,
        parse_formats,
        parse_templates,
        write_documents,
        write_run,
    )

    _tolerant_console()
    try:
        formats = parse_formats(args.format if args.format is not None else DEFAULT_FORMAT)
        templates = parse_templates(
            args.templates if args.templates is not None else DEFAULT_TEMPLATES
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INTERNAL
    outcome = assemble_run(args.input, args.criteria, mapping=args.mapping, registry=args.registry)
    target = write_run(outcome, args.out)
    documents, notes = write_documents(outcome, args.out, formats, templates)
    doc = outcome.document
    manifest = doc["manifest"]
    # A-P2 (build day 8, lane A): the one telemetry call site, after every document is
    # written. ``sent`` is printed and logged below; the return does not read it
    # (tests/test_telemetry.py::test_the_exit_code_with_a_failed_send_equals_the_exit_code_offline).
    from proofpack.egress import telemetry as telemetry_mod  # noqa: PLC0415 - one call site

    sent = telemetry_mod.run_telemetry(
        doc,
        offline=args.offline,
        licence_status=outcome.licence.status,
        transport=getattr(args, "transport", None),
    )
    statuses = [r["status"] for r in doc["criteria_results"]]
    warn_lines = "".join(f"\n  [{w.code}] {w.message}" for w in outcome.warnings)
    lic = outcome.licence
    lic_line = f"licence {lic.status} ({lic.reason_code})" + (
        f"; watermark: {manifest['watermark']}" if manifest["watermark"] else ""
    )
    counts = {s: statuses.count(s) for s in ("met", "not_met", "not_assessable")}
    summary = (
        f"run written: {target} (run_id {manifest['run_id']})\n"
        f"  analysed {doc['flow']['analysed']} of {doc['flow']['rows_read']} rows; "
        f"criteria rows: {counts['met']} met, {counts['not_met']} not met, "
        f"{counts['not_assessable']} not assessable\n"
        f"  {lic_line}{warn_lines}\n"
        f"{telemetry_mod.summary_lines(sent, offline=args.offline)}"
    )
    if not lic.usable:
        summary += f"  {LICENCE_FIX}\n"
    for path in documents:
        summary += f"  document written: {path}\n"
    for note in notes:
        summary += f"  {note}\n"
    if documents:
        summary += "Next step: open T8.html beside run.json; T1 and T7 land on E9 (docs: /docs/run)"
    elif not lic.usable:
        summary += (
            "Next step: proofpack licence install FILE, then run again for T8.html "
            "(docs: /docs/run)"
        )
    else:
        summary += "Next step: run again with --format json,html for T8.html (docs: /docs/run)"
    _emit(
        args,
        {
            "run": {
                "written": str(target),
                "run_id": manifest["run_id"],
                "exit_code": outcome.exit_code,
                "licence_status": lic.status,
                "telemetry": telemetry_mod.log_entry(sent, offline=args.offline),
                "watermark": manifest["watermark"],
                "criteria_status_counts": counts,
                "warnings": [w.code for w in outcome.warnings],
                "formats": formats,
                "templates": templates,
                "documents": [str(p) for p in documents],
                "document_notes": notes,
                "claims": len(doc["claims"]),
                "claim_rejections": len(doc["claim_rejections"]),
            }
        },
        summary,
    )
    return outcome.exit_code


def cmd_licence(args: argparse.Namespace) -> int:
    from proofpack import licence as licence_mod

    reissue = "Next step: ask licences@globalphoenix.co.uk for a re-issue (docs: /docs/licence)"
    run_next = "Next step: proofpack run --input ... --criteria ... (docs: /docs/run)"
    if args.licence_command == "show":
        path = licence_mod.installed_path()
        result = licence_mod.resolve(registry=args.registry)
        where = "none found" if path is None else str(path)
        hint = (
            "Next step: proofpack licence install FILE (docs: /docs/licence)"
            if result.status == "refused"
            else run_next
        )
    elif args.licence_command == "verify":
        result = licence_mod.verify(args.file, registry=args.registry)
        where = str(args.file)
        hint = (
            f"Next step: proofpack licence install {args.file} (docs: /docs/licence)"
            if result.status != "refused"
            else reissue
        )
    else:
        result = licence_mod.install(args.file, registry=args.registry)
        installed = result.status != "refused"
        where = str(licence_mod.install_location()) if installed else "not installed"
        hint = run_next if installed else reissue
    d = result.as_dict()
    lines = [f"licence: {where}", f"  status: {d['status']} ({d['reason_code']})"]
    if d["licence_id"] is not None:
        lines += [
            f"  licence_id: {d['licence_id']}",
            f"  licensee: {d['licensee']}",
            f"  tier: {d['tier']}",
            f"  expires: {d['expires']} (days_left {d['days_left']})",
            f"  watermark: {d['watermark']}",
            f"  key_id: {d['key_id']}",
        ]
    elif d["detail"]:
        lines.append(f"  detail: {json.dumps(d['detail'])}")
    lines.append(hint)
    _emit(args, {"licence": d, "path": where}, "\n".join(lines))
    return EXIT_OK if result.usable else EXIT_LICENCE


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


def main(argv: list[str] | None = None, *, registry=None, transport=None) -> int:
    """Entry point. ``registry`` (a :class:`proofpack.licence.keys.KeyRegistry`) is the
    test-only hook for licence verification against an ephemeral key pair: the shipped
    key is never rebound; a caller that wants another key names it here. ``transport``
    (A-P2) is the same kind of hook for the telemetry send - a callable ``(url, body,
    timeout) -> status`` that ``proofpack.egress.telemetry.send`` uses in place of
    ``urllib``; the URL itself is the constant ``TELEMETRY_URL`` and has no hook. The
    console script and ``python -m proofpack.cli`` always pass ``None`` for both."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.registry = registry
    args.transport = transport
    handler = {
        "doctor": cmd_doctor,
        "map": cmd_map,
        "run": cmd_run,
        "compare": cmd_compare,
        "licence": cmd_licence,
    }[args.command]
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
