"""A-P3 item 6 (build day 9, lane A): the workflow files, read as YAML and as text.

Neither ``release.yml`` nor ``ci.yml``'s ``docker-smoke`` job has run anywhere (24 September
2026); these tests read the files. What each asserts:

* every shell line in ``ci.yml`` and ``release.yml`` that invokes an engine subcommand
  (``proofpack run|fixtures|doctor|compare|map``, also as ``proofpack:ci <subcommand>`` in a
  ``docker run`` and ``python -m proofpack.cli <subcommand>``; ``echo`` and comment lines
  excluded, since they print text and run nothing) contains ``--offline``; the
  one exception is the A-P2 job ``offline-namespace``, whose script runs ``--online`` inside
  a network namespace on purpose and is listed here by name; ``scripts/f17_determinism.py``
  (called by both workflows) passes ``--offline`` in its own command list;
* the only ``secrets.<name>`` in any workflow is ``GITHUB_TOKEN``; ``id-token: write``
  appears in the ``testpypi`` job only; ``packages: write`` in ``release.yml``'s ``image``
  job only; ``contents: write`` in ``github-release`` only; top-level permissions are
  ``{}`` (release) and ``contents: read`` (ci);
* ``release.yml`` triggers on ``push`` of tags ``v*`` and nothing else;
* ``ci.yml``'s ``docker-smoke`` job has no ``permissions`` block, and no ``docker push``,
  ``docker login`` or ``ghcr.io`` in any step;
* ``release.yml``'s ``github-release`` step attaches the wheel, ``fixtures_report.json``,
  ``sbom.cdx.json``, the sample ``run.json`` and ``T12.html``;
* ``.github/dependabot.yml`` names the ``uv``, ``github-actions`` and ``docker``
  ecosystems, each weekly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent
WF = REPO / ".github" / "workflows"
ENGINE_CALL = re.compile(
    r"(?:(?<![\w.-])proofpack(?::ci)?|proofpack\.cli)\s+(run|fixtures|doctor|compare|map)\b"
)
#: Jobs whose engine runs are deliberately not --offline (A-P2's namespace job).
OFFLINE_EXEMPT_JOBS = {"offline-namespace"}


def _load(name: str) -> dict:
    path = WF / name
    if not path.exists():
        pytest.skip(f"no {name} here (the mutation sweep's copy)")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _on(doc: dict):
    # PyYAML reads the bare key `on` as the boolean True
    return doc.get("on", doc.get(True))


def shell_lines(doc: dict):
    """(job, line) for every line of every ``run:`` step, continuation lines joined."""
    for job_id, job in doc["jobs"].items():
        for step in job.get("steps", []):
            text = step.get("run")
            if not text:
                continue
            for line in re.sub(r"\s*\\\n\s*", " ", text).splitlines():
                # comments and echo lines print text; they run nothing
                if line.strip() and not line.strip().startswith(("#", "echo ")):
                    yield job_id, line


def offline_violations(doc: dict) -> list[tuple[str, str]]:
    out = []
    for job_id, line in shell_lines(doc):
        if job_id in OFFLINE_EXEMPT_JOBS:
            continue
        if ENGINE_CALL.search(line) and "--offline" not in line:
            out.append((job_id, line.strip()))
    return out


@pytest.mark.parametrize("name", ["ci.yml", "release.yml"])
def test_every_engine_run_in_a_workflow_carries_offline(name):
    doc = _load(name)
    calls = [line for job, line in shell_lines(doc) if ENGINE_CALL.search(line)]
    assert calls, name
    assert offline_violations(doc) == []


def test_the_counts_of_engine_lines_are_the_ones_written():
    ci, rel = _load("ci.yml"), _load("release.yml")
    count = {
        n: sum(1 for _, line in shell_lines(d) if ENGINE_CALL.search(line))
        for n, d in (("ci", ci), ("release", rel))
    }
    # ci: doctor in the CI venv, doctor + fixtures + run in the image, doctor in the
    # scipy-free venv; release: fixtures, doctor + fixtures in the image, doctor + fixtures
    # + run from TestPyPI
    assert count == {"ci": 5, "release": 6}


def test_a_planted_line_without_offline_is_caught():
    rel = _load("release.yml")
    rel["jobs"]["build"]["steps"].append({"run": "uv run proofpack fixtures --out x"})
    rel["jobs"]["build"]["steps"].append(
        {"run": "docker run --rm proofpack:ci run --input a \\\n  --criteria b"}
    )
    assert offline_violations(rel) == [
        ("build", "uv run proofpack fixtures --out x"),
        ("build", "docker run --rm proofpack:ci run --input a --criteria b"),
    ]


def test_the_f17_script_runs_the_engine_offline():
    script = (REPO / "scripts" / "f17_determinism.py").read_text(encoding="utf-8")
    block = script[script.index("def run_once") : script.index("def mask")]
    assert '"--offline"' in block and '"proofpack.cli"' in block and '"run"' in block


def test_no_secret_other_than_github_token():
    names = set()
    for path in sorted(WF.glob("*.yml")):
        names |= set(re.findall(r"secrets\.([A-Za-z0-9_]+)", path.read_text(encoding="utf-8")))
    assert names <= {"GITHUB_TOKEN"}, names
    assert "GITHUB_TOKEN" in names


def test_release_triggers_on_v_tags_only_and_permissions_are_minimal():
    rel = _load("release.yml")
    assert _on(rel) == {"push": {"tags": ["v*"]}}
    assert rel["permissions"] == {}
    perms = {job_id: job.get("permissions") for job_id, job in rel["jobs"].items()}
    assert perms == {
        "build": {"contents": "read"},
        "image": {"contents": "read", "packages": "write"},
        "testpypi": {"id-token": "write"},
        "install-from-testpypi": {"contents": "read"},
        "github-release": {"contents": "write"},
        "zap-baseline": {"contents": "read"},
    }
    text = (WF / "release.yml").read_text(encoding="utf-8")
    assert "pull_request_target" not in text
    assert "repository-url: https://test.pypi.org/legacy/" in text
    assert "password:" not in text and "api-token" not in text


def test_ci_builds_the_image_without_pushing():
    ci = _load("ci.yml")
    assert ci["permissions"] == {"contents": "read"}
    job = ci["jobs"]["docker-smoke"]
    assert "permissions" not in job
    for step in job["steps"]:
        text = str(step.get("run", "")) + str(step.get("uses", ""))
        assert "docker push" not in text and "docker login" not in text and "ghcr.io" not in text
    runs = " ".join(str(s.get("run", "")) for s in job["steps"])
    assert "docker build --platform linux/amd64 -t proofpack:ci ." in runs
    assert "--network none proofpack:ci doctor --offline" in runs
    assert "f17_determinism.py --out /work/f17 --n 5000" in runs
    for other in ci["jobs"].values():
        assert "id-token" not in str(other.get("permissions", ""))
    assert "pull_request_target" not in (WF / "ci.yml").read_text(encoding="utf-8")


def test_the_github_release_attaches_the_five_assets():
    rel = _load("release.yml")
    run = " ".join(str(s.get("run", "")) for s in rel["jobs"]["github-release"]["steps"])
    for asset in (
        "dist/*.whl",
        "release/fixtures_report.json",
        "release/sbom.cdx.json",
        "release/sample/run.json",
        "release/T12.html",
    ):
        assert asset in run, asset


def test_dependabot_covers_the_lock_the_actions_and_the_image_weekly():
    path = REPO / ".github" / "dependabot.yml"
    if not path.exists():
        pytest.skip("no dependabot.yml here")
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["version"] == 2
    eco = {u["package-ecosystem"]: u["schedule"]["interval"] for u in doc["updates"]}
    assert eco == {"uv": "weekly", "github-actions": "weekly", "docker": "weekly"}
