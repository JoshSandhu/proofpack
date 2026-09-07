"""ProofPack engine.

Importing this package must never require scipy (CI runs an ``import proofpack``
job with scipy uninstalled). scipy is an optional extra used only by
statistics modules that land on later build days.
"""

from proofpack.errors import (
    EXIT_HALT,
    EXIT_INTERNAL,
    EXIT_LICENCE,
    EXIT_OK,
    EXIT_WARNINGS,
    HALT_CODES,
    Finding,
    HaltError,
)

__version__ = "0.1.0.dev1"

__all__ = [
    "EXIT_HALT",
    "EXIT_INTERNAL",
    "EXIT_LICENCE",
    "EXIT_OK",
    "EXIT_WARNINGS",
    "HALT_CODES",
    "HaltError",
    "Finding",
    "__version__",
]
