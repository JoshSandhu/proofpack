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
    "H02": "y_true values not a subset of declared classes and indeterminate values",
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
}

#: Gates that produce a flag/warning rather than a HALT.
FLAG_ONLY_CODES = frozenset({"H10"})


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
        if self.code not in HALT_CODES and self.code not in SCHEMA_CODES:
            raise ValueError(f"unknown HALT code {self.code!r}")
        super().__init__(f"{self.code}: {self.message}")

    @property
    def exit_code(self) -> int:
        return EXIT_HALT


@dataclass
class Finding:
    """A non-fatal finding (W06, W10, ...). Rendered in T8; exit code 2 if any."""

    code: str
    message: str
    detail: dict = field(default_factory=dict)


class LicenceError(ProofPackError):
    exit_code = EXIT_LICENCE
