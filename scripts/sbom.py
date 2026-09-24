"""CycloneDX 1.5 JSON SBOM from ``uv.lock``, standard library only (A-P3, build day 9).

    python scripts/sbom.py --out sbom.cdx.json [--lock uv.lock]

What it writes, and from what:

* ``bomFormat`` ``CycloneDX``, ``specVersion`` ``1.5``, ``version`` 1, and a
  ``serialNumber`` that is ``urn:uuid:`` + a UUID5 of the SHA-256 of ``uv.lock`` - so two
  runs on one lock file write the same bytes (no clock is read; ``metadata.timestamp`` is
  written only when ``SOURCE_DATE_EPOCH`` is set, as that date);
* ``metadata.component``: the project package of the lock (``source = { editable = "." }``)
  with its version and purl; ``metadata.tools.components``: this script;
* ``components``: every other ``[[package]]`` of the lock, each with ``type`` library,
  ``bom-ref`` and ``purl`` (``pkg:pypi/<name>@<version>``), the sdist SHA-256 when the
  lock records one, and ``scope``: ``required`` for the closure of the project's runtime
  dependencies, ``optional`` for what the ``stats`` extra adds, ``excluded`` for the
  development group (test oracles, linters) that no install of the wheel carries;
* ``dependencies``: each package's ``dependsOn`` purls as the lock lists them.

The CycloneDX schema file was not fetched for this build; ``tests/test_sbom.py`` checks
the fields above structurally (every locked package present with a purl, two runs
byte-identical), not against the published JSON schema.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tomllib
import uuid
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL_NAME = "proofpack scripts/sbom.py"


def purl(name: str, version: str) -> str:
    return f"pkg:pypi/{name.lower().replace('_', '-')}@{version}"


def _closure(packages: dict[str, dict], roots: list[str]) -> set[str]:
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        name = stack.pop()
        if name in seen or name not in packages:
            continue
        seen.add(name)
        # a dependency's own extras are not followed: the lock lists what each entry needs
        stack += [d["name"] for d in packages[name].get("dependencies", [])]
    return seen


def build_sbom(lock_path: Path) -> dict:
    raw = lock_path.read_bytes()
    lock = tomllib.loads(raw.decode("utf-8"))
    packages = {p["name"]: p for p in lock["package"]}
    project = next(p for p in lock["package"] if "editable" in p.get("source", {}))
    runtime = _closure(packages, [d["name"] for d in project.get("dependencies", [])])
    stats = _closure(
        packages,
        [d["name"] for d in project.get("optional-dependencies", {}).get("stats", [])],
    )
    serial = uuid.uuid5(uuid.NAMESPACE_URL, "sha256:" + hashlib.sha256(raw).hexdigest())
    components = []
    dependencies = []
    for name in sorted(packages):
        pkg = packages[name]
        ref = purl(name, pkg["version"])
        dependencies.append(
            {
                "ref": ref,
                "dependsOn": sorted(
                    {
                        purl(d["name"], packages[d["name"]]["version"])
                        for d in pkg.get("dependencies", [])
                        if d["name"] in packages
                    }
                ),
            }
        )
        if pkg is project:
            continue
        scope = "required" if name in runtime else ("optional" if name in stats else "excluded")
        comp: dict = {
            "type": "library",
            "bom-ref": ref,
            "name": name,
            "version": pkg["version"],
            "purl": ref,
            "scope": scope,
        }
        sdist = pkg.get("sdist") or {}
        if str(sdist.get("hash", "")).startswith("sha256:"):
            comp["hashes"] = [{"alg": "SHA-256", "content": sdist["hash"].split(":", 1)[1]}]
        components.append(comp)
    metadata: dict = {
        "tools": {"components": [{"type": "application", "name": TOOL_NAME}]},
        "component": {
            "type": "library",
            "bom-ref": purl(project["name"], project["version"]),
            "name": project["name"],
            "version": project["version"],
            "purl": purl(project["name"], project["version"]),
        },
    }
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        metadata["timestamp"] = (
            datetime.fromtimestamp(int(epoch), UTC).isoformat().replace("+00:00", "Z")
        )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": metadata,
        "components": components,
        "dependencies": dependencies,
    }


def dumps(bom: dict) -> bytes:
    return (json.dumps(bom, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CycloneDX 1.5 JSON SBOM from uv.lock")
    ap.add_argument("--lock", default=str(REPO / "uv.lock"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    bom = build_sbom(Path(args.lock))
    Path(args.out).write_bytes(dumps(bom))
    scopes = [c["scope"] for c in bom["components"]]
    print(
        f"sbom written: {args.out} (CycloneDX 1.5; {len(scopes)} components: "
        f"{scopes.count('required')} required, {scopes.count('optional')} optional, "
        f"{scopes.count('excluded')} excluded)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
