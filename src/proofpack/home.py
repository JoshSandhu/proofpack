"""The per-user directory the CLI reads: the installed licence and the local ledger.

``PROOFPACK_HOME`` when set (tests point it at a temporary directory); otherwise
``%LOCALAPPDATA%\\proofpack`` on Windows (``LOCALAPPDATA`` unset -> ``~/.proofpack``) and
``~/.proofpack`` elsewhere. ``platformdirs`` is not a dependency (zero new packages for a
path). Nothing here creates the directory; the writer that needs it does.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_HOME = "PROOFPACK_HOME"


def home_dir() -> Path:
    override = os.environ.get(ENV_HOME)
    if override:
        return Path(override)
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "proofpack"
    return Path.home() / ".proofpack"
