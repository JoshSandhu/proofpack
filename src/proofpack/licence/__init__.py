"""``proofpack.licence`` - verify, locate and install a ``proofpack.lic`` (D1 section 7).

Where the CLI looks for the licence, in order (:func:`installed_path`): the path in the
``PROOFPACK_LICENCE`` environment variable when set; else ``proofpack.lic`` in the per-user
directory (:mod:`proofpack.home`: ``%LOCALAPPDATA%\\proofpack`` on Windows, ``~/.proofpack``
elsewhere, ``PROOFPACK_HOME`` overriding); else ``proofpack.lic`` in the working directory.
``licence install FILE`` copies ``FILE`` to the per-user location after verifying its
signature (a refused file is not installed).

Importing this package does not import ``cryptography``; :func:`verify` does, when called.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from proofpack.home import home_dir
from proofpack.licence.keys import (
    PUBLISHED_PUBLIC_KEY_B64,
    SHIPPED_KEY_ID,
    SHIPPED_PUBLIC_KEY,
    SHIPPED_PUBLIC_KEY_B64,
    KeyRegistry,
)
from proofpack.licence.verify import (
    STATUSES,
    WATERMARK_EXPIRED,
    WATERMARK_NO_LICENCE,
    WATERMARK_TRIAL,
    LicenceResult,
    verify,
)

LICENCE_FILE = "proofpack.lic"
ENV_LICENCE = "PROOFPACK_LICENCE"

__all__ = [
    "PUBLISHED_PUBLIC_KEY_B64",
    "SHIPPED_KEY_ID",
    "SHIPPED_PUBLIC_KEY",
    "SHIPPED_PUBLIC_KEY_B64",
    "STATUSES",
    "WATERMARK_EXPIRED",
    "WATERMARK_NO_LICENCE",
    "WATERMARK_TRIAL",
    "KeyRegistry",
    "LicenceResult",
    "install",
    "installed_path",
    "resolve",
    "verify",
]


def install_location() -> Path:
    return home_dir() / LICENCE_FILE


def installed_path() -> Path | None:
    """The licence file the CLI would read, or ``None`` when none exists."""
    env = os.environ.get(ENV_LICENCE)
    if env:
        return Path(env)
    home = install_location()
    if home.exists():
        return home
    cwd = Path.cwd() / LICENCE_FILE
    if cwd.exists():
        return cwd
    return None


def resolve(*, registry: KeyRegistry | None = None) -> LicenceResult:
    """Verify whichever licence file :func:`installed_path` finds; ``refused`` /
    ``no_file`` when there is none."""
    path = installed_path()
    if path is None:
        return LicenceResult("refused", "no_file")
    return verify(path, registry=registry)


def install(source: str | Path, *, registry: KeyRegistry | None = None) -> LicenceResult:
    """Verify ``source`` and, unless refused, copy its bytes to the per-user location."""
    result = verify(source, registry=registry)
    if result.status == "refused":
        return result
    target = install_location()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return result
