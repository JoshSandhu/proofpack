"""The manual PyPI workflow (.github/workflows/pypi.yml, 2 October 2026).

These tests read the YAML. They inspect the trigger (workflow_dispatch and nothing else),
the permissions (none at the top; contents: read for the build job; id-token: write for the
publish job only), the publish job's environment name and the absence of any secret.
"""

from pathlib import Path

import pytest
import yaml

# The release-pipeline lane's marks, as tests/test_workflows.py carries them.
pytestmark = [pytest.mark.day9, pytest.mark.ap3]

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "pypi.yml"


def _load():
    doc = yaml.safe_load(WF.read_text(encoding="utf-8"))
    # PyYAML reads the bare key `on` as the boolean True.
    return doc, doc.get("on", doc.get(True))


def test_the_trigger_is_workflow_dispatch_only():
    _, on = _load()
    assert set(on) == {"workflow_dispatch"}


def test_permissions_are_empty_at_the_top_and_id_token_only_on_publish():
    doc, _ = _load()
    assert doc["permissions"] == {}
    assert doc["jobs"]["build"]["permissions"] == {"contents": "read"}
    assert doc["jobs"]["publish"]["permissions"] == {"id-token": "write"}
    assert doc["jobs"]["publish"]["environment"] == "pypi"
    assert doc["jobs"]["publish"]["needs"] == "build"


def test_the_publish_step_targets_pypi_org_without_a_secret():
    text = WF.read_text(encoding="utf-8")
    assert "secrets." not in text
    assert "password" not in text.split("\njobs:")[1]
    doc, _ = _load()
    step = doc["jobs"]["publish"]["steps"][-1]
    assert step["uses"] == "pypa/gh-action-pypi-publish@release/v1"
    assert "repository-url" not in step["with"]
