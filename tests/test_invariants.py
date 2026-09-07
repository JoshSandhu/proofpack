"""Cross-cutting repository invariants that no single day owns.

Three guarantees live here:

1. ``Number`` is immutable, so the "no Number without a CI" invariant enforced in
   ``__post_init__`` cannot be undone after construction.
2. Every collected test carries a ``dayN`` marker, so the per-day CI gate (which
   iterates the markers declared in ``pyproject.toml``) cannot silently skip a
   future day's tests.
3. Nothing that renders a customer-facing string may emit an ``[unverified]``
   fixture value without carrying its marking. There is no renderer yet - the
   guard is exercised against a synthetic renderer here so that it is a real
   check today, and applied to every source and template file in the repo so it
   fires the moment a real renderer lands (day 5+).
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import re

import pytest

from conftest import UNMARKED_ITEMS  # pytest puts tests/ on sys.path (rootdir conftest)
from proofpack.stats.number import Number

pytestmark = pytest.mark.day1

REPO = pathlib.Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- 1. frozen Number


def test_number_is_frozen_and_cannot_lose_its_interval():
    n = Number(est=0.5, ci_lo=0.2, ci_hi=0.8, method="wilson", n=100, k=50)
    for field, value in (("ci_lo", None), ("ci_hi", None), ("est", 0.99), ("method", "none")):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(n, field, value)
    assert n.as_dict()["ci_lo"] == 0.2 and n.as_dict()["ci_hi"] == 0.8


def test_number_dataclass_is_declared_frozen():
    """Guards the decorator itself: a future edit that drops frozen=True fails here."""
    assert dataclasses.fields(Number)  # it is a dataclass
    assert Number.__dataclass_params__.frozen is True


def test_precision_flags_still_work_on_a_frozen_number():
    n = Number(est=0.5, ci_lo=0.0, ci_hi=1.0, method="wilson", n=12).with_precision_flags()
    assert "very_low_precision" in n.flags and "imprecise" in n.flags


# --------------------------------------------------------------------------- 2. marker coverage


def _declared_day_markers() -> list[str]:
    import tomllib

    with (REPO / "pyproject.toml").open("rb") as fh:
        markers = tomllib.load(fh)["tool"]["pytest"]["ini_options"]["markers"]
    days = {m.split(":", 1)[0] for m in markers if re.fullmatch(r"day\d+", m.split(":", 1)[0])}
    return sorted(days, key=lambda s: int(s[3:]))


def test_every_collected_test_carries_a_day_marker():
    """A test with no ``dayN`` marker would never run in the per-day CI gate."""
    assert UNMARKED_ITEMS == [], (
        "these tests carry no dayN marker and so are invisible to the per-day CI gate: "
        + ", ".join(UNMARKED_ITEMS)
    )


def test_ci_runs_every_declared_day_marker_without_a_hardcoded_list():
    """The per-day gate must be derived from the declared markers, not typed out."""
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    hardcoded = re.findall(r"-m\s+[\"']?day\d+", ci)
    assert hardcoded == [], f"CI hardcodes per-day marker steps: {hardcoded}"
    assert "markers" in ci and "pyproject.toml" in ci, (
        "CI's per-day gate should read the day markers out of pyproject.toml"
    )
    assert _declared_day_markers()[:3] == ["day1", "day2", "day3"]


# --------------------------------------------------------------------- 3. [unverified] markings

UNVERIFIED_MARK = "[unverified"

#: File types that can carry rendered, customer-facing text.
RENDERABLE_SUFFIXES = {".py", ".j2", ".jinja", ".jinja2", ".md", ".html", ".txt", ".rst", ".tex"}


def unverified_fixture_values() -> set[str]:
    """Every interval bound in F14 that is marked ``[unverified]``, as printed to 4 dp."""
    fixture = json.loads((REPO / "fixtures" / "newcombe_table2.json").read_text(encoding="utf-8"))
    assert fixture["provenance"]["status"].startswith(UNVERIFIED_MARK)
    assert fixture["paired_examples"]["status"].startswith(UNVERIFIED_MARK)
    values: set[str] = set()
    blocks = list(fixture["examples"]) + list(fixture["paired_examples"]["examples"])
    for ex in blocks:
        for key in ("method10", "method11"):
            if key in ex:
                for bound in ("lower", "upper"):
                    values.add(f"{ex[key][bound]:.4f}")
    return values


def unmarked_unverified_values(rendered: str, values: set[str]) -> list[str]:
    """Fixture values that appear in ``rendered`` with no ``[unverified]`` marking on it."""
    if UNVERIFIED_MARK in rendered:
        return []
    return sorted(v for v in values if v in rendered)


def test_the_guard_itself_catches_an_unmarked_renderer():
    """Exercises the guard so it is not a vacuous check while no renderer exists."""
    values = unverified_fixture_values()
    assert values, "F14 should carry interval bounds"

    bad = "Difference in sensitivity: 0.2000 (95% CI 0.0524 to 0.3339), Newcombe method 10.\n"
    assert unmarked_unverified_values(bad, values) == ["0.0524", "0.3339"]

    good = bad + "Source: Newcombe 1998 Table II [unverified against the primary PDF].\n"
    assert unmarked_unverified_values(good, values) == []


def test_no_source_or_template_emits_an_unverified_value_unmarked():
    """Fires the moment a renderer prints an F14 value without carrying its marking."""
    values = unverified_fixture_values()
    offenders: dict[str, list[str]] = {}
    roots = [REPO / "src", REPO / "templates", REPO / "design", REPO / "schema"]
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in RENDERABLE_SUFFIXES:
                continue
            if "__pycache__" in path.parts:
                continue
            found = unmarked_unverified_values(path.read_text(encoding="utf-8"), values)
            if found:
                offenders[str(path.relative_to(REPO))] = found
    assert offenders == {}, (
        "these files print [unverified] Newcombe Table II values with no marking: "
        f"{offenders}. Carry the fixture's provenance status through to the rendered "
        "text, or do not render the value."
    )


def test_the_fixture_is_not_packaged_into_the_wheel():
    """An unverified fixture must not ship where a renderer could reach it at runtime."""
    import tomllib

    with (REPO / "pyproject.toml").open("rb") as fh:
        force_include = tomllib.load(fh)["tool"]["hatch"]["build"]["targets"]["wheel"][
            "force-include"
        ]
    assert not any("newcombe" in key.lower() for key in force_include)
