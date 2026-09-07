"""ProofPack statistics modules.

Nothing here imports scipy at module level: ``import proofpack.stats`` must work in
an environment with numpy only (day-1 CI job). Optional-dependency imports live
inside the single function that needs them.
"""

from proofpack.stats.number import (
    FLAGS,
    METHODS,
    NOT_ESTIMABLE_REASONS,
    Number,
    not_estimable,
)

__all__ = ["FLAGS", "METHODS", "NOT_ESTIMABLE_REASONS", "Number", "not_estimable"]
