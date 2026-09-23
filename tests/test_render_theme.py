"""Build day 8 (E8 items 2 and 3): jinja2 as an isolated dependency, and the D5 theme.

* ``import proofpack``, ``proofpack.stats``, ``proofpack.narrate`` and ``proofpack.render``
  import with jinja2 (and MarkupSafe) hidden from ``sys.modules``; the renderer raises a
  typed error naming the missing package;
* ``design/tokens.json`` carries every row of D5 section 3.1's colour table, re-typed here
  as literals, and the WCAG contrast of each text token on its declared surface, computed
  here from the hex values with the sRGB formula, equals the ratio D5 states to 0.1 and
  passes 4.5:1;
* a wheel built from the working tree, installed into a fresh venv (no pip, no index,
  no dependencies: ``import proofpack`` needs none), resolves ``resource_path("tokens.json")``
  inside that venv - both printed paths are under the venv, so the test cannot pass by
  reading the source tree (the editable ``.pth`` trap the E7 note describes).
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from proofpack.render import theme
from proofpack.resources import resource_path

pytestmark = pytest.mark.day8

REPO = Path(__file__).resolve().parent.parent

#: D5 section 3.1, transcribed a second time here, row by row (nine rows, nineteen tokens).
D5_COLOURS = {
    "ink": "#16202b",
    "ink-soft": "#4a5a6a",
    "ink-faint": "#6b7784",
    "line": "#d8dfe6",
    "bg": "#ffffff",
    "bg-soft": "#f5f7f9",
    "bg-inset": "#eef1f4",
    "brand": "#123a5f",
    "brand-soft": "#e6eef5",
    "brand-strong": "#0c2740",
    "on-brand": "#ffffff",
    "honesty": "#8a4b00",
    "honesty-bg": "#fdf3e3",
    "stop": "#7f1d1d",
    "stop-bg": "#fdeaea",
    "stop-line": "#c98b8b",
    "ok": "#14532d",
    "ok-bg": "#e4f2e8",
    "ok-line": "#86b39a",
}
#: The contrast ratios D5 section 3.1 states, token on surface. honesty, stop and ok are
#: on their own -bg surfaces, the rows D5 section 3.1 (lines 169-171) pairs them with
#: (DEC-67, lens-6 RG-N3: tokens.json paired them with ``bg`` until repair 6 of build
#: day 8, which gave 6.80, 10.02 and 9.11 against D5's 6.2, 8.7 and 7.9).
D5_CONTRAST = {
    ("ink", "bg"): 16.4,
    ("ink-soft", "bg"): 7.1,
    ("ink-faint", "bg"): 4.6,
    ("line", "bg"): 1.3,
    ("on-brand", "brand"): 11.7,
    ("brand", "brand-soft"): 10.0,
    ("honesty", "honesty-bg"): 6.2,
    ("stop", "stop-bg"): 8.7,
    ("ok", "ok-bg"): 7.9,
}


def _hidden(monkeypatch, *names: str) -> None:
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)
    for mod in list(sys.modules):
        if mod == "proofpack" or mod.startswith("proofpack."):
            monkeypatch.delitem(sys.modules, mod)


def test_import_proofpack_with_jinja2_hidden_and_the_renderer_names_the_package(monkeypatch):
    _hidden(monkeypatch, "jinja2", "markupsafe")
    with pytest.raises(ImportError):
        import jinja2  # noqa: F401
    for name in ("proofpack", "proofpack.stats", "proofpack.narrate", "proofpack.render"):
        importlib.import_module(name)
    assert "jinja2" not in {m for m in sys.modules if sys.modules[m] is not None}
    html = importlib.import_module("proofpack.render.html")
    with pytest.raises(html.RendererUnavailable) as info:
        html.environment()
    assert info.value.package == "jinja2" and "jinja2" in str(info.value)
    from proofpack.errors import ProofPackError

    assert isinstance(info.value, ProofPackError)


def test_tokens_json_carries_every_d5_row_verbatim():
    t = theme.tokens()
    assert t["version"] == "1"
    assert set(t) >= {"color", "type", "space", "radius"}
    assert {k: v["value"] for k, v in t["color"].items()} == D5_COLOURS
    assert len(t["color"]) == 19
    for name, entry in t["color"].items():
        assert entry["role"] in ("text", "ui", "decorative", "surface"), name
    assert t["type"]["text"].startswith("-apple-system, BlinkMacSystemFont")
    assert t["type"]["mono"].startswith("ui-monospace")
    assert t["type"]["scale"] == {
        "tag": "0.72rem",
        "strip": "0.78rem",
        "footnote": "0.85rem",
        "table": "0.92rem",
        "body": "1rem",
        "h3": "1.15rem",
        "h2": "1.4rem",
        "h1": "clamp(1.8rem, 4.2vw, 2.7rem)",
    }
    assert list(t["space"].values()) == [
        "0.25rem",
        "0.5rem",
        "0.75rem",
        "1rem",
        "1.5rem",
        "2rem",
        "2.75rem",
        "3rem",
    ]
    assert t["radius"]["tag"] == "4px" and t["radius"]["button"] == "6px"
    assert t["radius"]["card"] == "8px"
    assert t["print"]["page_margin"] == "20mm 18mm 26mm" and t["print"]["page_size"] == "A4"
    assert theme.color("honesty") == "#8a4b00"
    assert json.loads(resource_path("tokens.json").read_text(encoding="utf-8")) == t


def _luminance(hex_colour: str) -> float:
    r, g, b = (int(hex_colour[i : i + 2], 16) / 255.0 for i in (1, 3, 5))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(fg: str, bg: str) -> float:
    lf, lb = _luminance(fg), _luminance(bg)
    hi, lo = max(lf, lb), min(lf, lb)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("pair", sorted(D5_CONTRAST))
def test_the_declared_contrast_is_the_computed_wcag_ratio(pair):
    fg, bg = pair
    ratio = _contrast(D5_COLOURS[fg], D5_COLOURS[bg])
    entry = theme.tokens()["color"][fg]
    assert entry["contrast"] == f"{D5_CONTRAST[pair]}:1"  # D5's figure, verbatim
    assert float(entry["contrast_computed"].split(":")[0]) == pytest.approx(ratio, abs=0.01)
    assert ratio == pytest.approx(D5_CONTRAST[pair], abs=0.1)
    if entry["role"] == "text":
        assert ratio >= 4.5, (pair, ratio)
    assert entry["on"] == bg


def test_css_variables_cover_every_colour_and_carry_no_role_or_contrast_text():
    v = theme.css_variables()
    for name, value in D5_COLOURS.items():
        assert v[f"--pp-color-{name}"] == value
    assert v["--pp-type-scale-h2"] == "1.4rem" and v["--pp-space-4"] == "1rem"
    assert v["--pp-print-page-margin"] == "20mm 18mm 26mm"
    block = theme.css_root_block()
    assert block.startswith(":root {\n") and block.endswith("\n}")
    assert "contrast" not in block and "role" not in block
    assert all(line.endswith(";") for line in block.splitlines()[1:-1])


def _build_wheel(out: Path) -> Path:
    """A wheel from the working tree: ``uv build`` (hatchling cached) or ``pip wheel``."""
    attempts = (
        [sys.executable, "-m", "uv", "build", "--wheel", "--out-dir", str(out)],
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", str(out)],
    )
    errors = []
    for cmd in attempts:
        proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
        wheels = sorted(out.glob("proofpack-*.whl"))
        if proc.returncode == 0 and wheels:
            return wheels[0]
        errors.append(f"{cmd[2:4]}: rc {proc.returncode}\n{proc.stderr[-800:]}")
    pytest.skip("no wheel builder available in this environment:\n" + "\n".join(errors))


def test_resource_path_tokens_json_resolves_inside_a_built_wheel_in_a_fresh_venv(tmp_path: Path):
    wheel = _build_wheel(tmp_path / "dist")
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    py = (
        venv
        / ("Scripts" if os.name == "nt" else "bin")
        / ("python.exe" if os.name == "nt" else "python")
    )
    assert py.exists(), list(venv.iterdir())
    purelib = subprocess.run(
        [str(py), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert Path(purelib).resolve().is_relative_to(venv.resolve())
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "--no-deps",
            "--no-index",
            "--target",
            purelib,
            str(wheel),
        ],
        check=True,
        capture_output=True,
    )
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    env["PYTHONNOUSERSITE"] = "1"
    command = (
        "import proofpack, proofpack.resources as r; print(proofpack.__file__); "
        'print(r.resource_path("tokens.json"))'
    )
    proc = subprocess.run(
        [str(py), "-c", command], capture_output=True, text=True, env=env, cwd=str(tmp_path)
    )
    assert proc.returncode == 0, proc.stderr
    pkg_file, tokens_path = (Path(p.strip()) for p in proc.stdout.strip().splitlines())
    assert pkg_file.resolve().is_relative_to(venv.resolve()), pkg_file
    assert tokens_path.resolve().is_relative_to(venv.resolve()), tokens_path
    assert not tokens_path.resolve().is_relative_to(REPO.resolve())
    assert tokens_path.parent.name == "_schema" and tokens_path.name == "tokens.json"
    assert json.loads(tokens_path.read_text(encoding="utf-8")) == theme.tokens()
    # the same wheel resolves the guidance map beside it
    proc = subprocess.run(
        [
            str(py),
            "-c",
            'import proofpack.resources as r; print(r.resource_path("guidance_map_v1.csv"))',
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0 and "_schema" in proc.stdout
    shutil.rmtree(venv, ignore_errors=True)
