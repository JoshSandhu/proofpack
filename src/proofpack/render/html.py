"""HTML rendering through jinja2 (build day 8, E8). jinja2 is imported here only, inside
:func:`environment`; the module itself imports without it and
:class:`RendererUnavailable` names the missing package.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from proofpack.errors import ProofPackError

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"


class RendererUnavailable(ProofPackError):
    """jinja2 is not installed: ``pip install jinja2>=3.1`` (a runtime dependency of the
    package; the HTML renderer is the only importer)."""

    def __init__(self, package: str = "jinja2") -> None:
        self.package = package
        super().__init__(
            f"the HTML renderer needs the package {package!r}, which is not installed "
            f"(install proofpack with its dependencies: {package}>=3.1)"
        )


def environment() -> Any:
    """A jinja2 environment over ``templates/``: autoescape on, ``StrictUndefined``."""
    try:
        import jinja2  # noqa: PLC0415 - imported here only, so `import proofpack` needs no jinja2
    except ImportError as exc:
        raise RendererUnavailable("jinja2") from exc
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
    )
