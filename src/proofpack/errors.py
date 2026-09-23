"""Exit codes, HALT codes and the exception hierarchy (D1 section 5).

Exit codes: 0 ok, 2 warnings only, 3 HALT, 4 licence, 5 internal.
No document is written on HALT ("never a silent number").
"""

from __future__ import annotations

from dataclasses import dataclass, field

EXIT_OK = 0
EXIT_WARNINGS = 2
EXIT_HALT = 3
EXIT_LICENCE = 4
EXIT_INTERNAL = 5

#: HALT gate codes and their one-line meaning (D1 section 5 table).
HALT_CODES: dict[str, str] = {
    "H01": "AUROC < 0.5 on declared orientation",
    "H02": (
        "y_true or y_pred non-blank values not a subset of declared classes and "
        "indeterminate values"
    ),
    "H03": "score.type is probability and a value lies outside [0, 1]",
    "H04": "y_pred not reproducible from score at a declared operating point",
    "H05": "duplicate row_id, or duplicate case_id rows with conflicting y_true",
    "H06": "single-class dataset",
    "H07": "header-set hash differs from mapping.json in non-interactive mode",
    "H08": "mandatory declaration missing or criterion lacking author/date/justification",
    "H09": "criterion references unknown metric/operating point/attribute/level",
    "H10": "observed vs declared intended-use prevalence differ by > 0.10 absolute (flag only)",
    "H11": "date-like column present with no period declaration",
    "H12": "compare paired mode with unmatched row_ids",
}

#: Structural schema failures that also HALT (exit 3) but are not one of the twelve
#: declared gates. They are reported with an S-code so the H-code table stays exact.
SCHEMA_CODES: dict[str, str] = {
    "S01": "required column missing",
    "S02": "column value cannot be coerced to its declared type",
    "S03": "declared period column not present in the table",
    "S04": "table could not be read",
    # E7 (carried item 26 of the day-6 handoff): a blank case_id (empty, NA, null) in any
    # row. Every consumer of the case column (flow, calibration, subgroups) sorts its
    # values, and None beside str raised TypeError there; a blank id would otherwise be
    # read as one case shared by every blank row or as a case of its own, and neither is
    # what the customer declared. The count of blank ids is the detail; no id is printed.
    "S05": "case_id is blank in one or more rows",
}

#: Mapper halts that are neither one of the twelve gates nor a schema failure. They exit
#: 3 like the others. E01 is DEC-11 (Josh, 13 September 2026); its message ends "reduce
#: your case key to one column". Raised by ``io.declare._check_dec11_case_key`` (a
#: ``clustering.unit`` list of >= 2, a string splitting into >= 2 tokens, or a list of
#: >= 2 under ``clustering.columns``/``key``/...), by ``io.mapping.map_headers`` (two
#: headers resolving to ``case_id`` by name) and by ``io.mapping.apply_mapping`` (two
#: columns mapped to ``case_id``, whatever the source). ``tests/test_mapping_full.py::
#: test_dec11_via_the_cli_run_and_map_exit_3_with_the_message_and_no_traceback`` runs
#: ``run`` and ``map`` through ``main()`` and one subprocess and asserts exit 3, the first
#: stderr line and no ``Traceback``.
MAPPING_CODES: dict[str, str] = {
    "E01": "composite case key: two or more columns identify a case (DEC-11)",
}

#: Gates that produce a flag/warning rather than a HALT. W14 is the ledger's limit
#: warning (E7): the run completes and the document carries the count and the limit.
#: W16 (A-P2, build day 8) is the telemetry send that did not succeed: printed as one
#: line after run.json is written (``egress.telemetry.SendResult.line``) and not
#: appended to the document; ``cmd_run`` returns the run's exit code without reading
#: the result (tests/test_telemetry.py: the 500 / timeout / refused / schema-unreadable
#: runs each assert ``rc == EXIT_OK`` and the W16 line).
FLAG_ONLY_CODES = frozenset({"H10", "W14", "W16"})

#: Non-fatal warning codes, closed the way :data:`HALT_CODES` is. ``Finding.code`` used
#: to be free text, so a typo or a collision between two lanes could not be caught, and
#: three of the four codes in use appear nowhere in the spec. D1 section 5 names W06;
#: the rest are recorded here as engine codes so at least they cannot drift silently.
WARN_CODES: dict[str, str] = {
    "W06": "single-class site(s) present; site-level metrics limited (D1 section 5)",
    "W10": "observed prevalence differs from declared intended-use prevalence by > 0.10",
    "W12": "unmatched row_ids in a paired compare; unpaired methods used",
    "W13": "clustering detected from repeated case_id although clustering.unit is 'none'",
    # E7, io.ledger: the customer's warn_after_acceptance_runs is exceeded on this test set
    # (D4 section 11 item 6, the T2 ledger banner); W15 when the ledger file could not be
    # read or written and the count is unknown.
    "W14": "acceptance runs on this test set exceed the declared ledger limit",
    "W15": "the local ledger could not be read or written; acceptance runs not counted",
    # A-P2 (build day 8), egress.telemetry: the one outbound call did not succeed or was
    # not made (timeout, unreachable, refused, a non-2xx status, an invalid payload, the
    # schema resource unreadable). Printed as one line; the line's own words are the
    # measured ones (tests/test_telemetry.py, the W16 tests named in FLAG_ONLY_CODES).
    "W16": "telemetry not sent; run.json and the exit code are unchanged",
}


class ProofPackError(Exception):
    """Base class for all engine errors."""


@dataclass
class HaltError(ProofPackError):
    """A HALT gate fired. Carries the code, a human message and coarse detail.

    ``detail`` may contain only aggregates (counts, column *roles*, declared
    values). It must never carry row-level data or original headers, because the
    telemetry payload carries ``halt_code`` and support triage may quote messages.
    """

    code: str
    message: str
    detail: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            self.code not in HALT_CODES
            and self.code not in SCHEMA_CODES
            and self.code not in MAPPING_CODES
        ):
            raise ValueError(f"unknown HALT code {self.code!r}")
        super().__init__(f"{self.code}: {self.message}")

    @property
    def exit_code(self) -> int:
        return EXIT_HALT


@dataclass
class Finding:
    """A non-fatal finding (W06, W10, ...). Rendered in T8; exit code 2 if any.

    The code is validated against :data:`WARN_CODES` exactly as ``HaltError`` validates
    against :data:`HALT_CODES`: a warning code reaches the document and the exit status,
    so a typo must fail at construction rather than render as a warning nobody can look
    up.
    """

    code: str
    message: str
    detail: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.code not in WARN_CODES:
            raise ValueError(f"unknown warning code {self.code!r}")


class LicenceError(ProofPackError):
    exit_code = EXIT_LICENCE
