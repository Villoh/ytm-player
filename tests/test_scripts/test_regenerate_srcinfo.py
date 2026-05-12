"""Tests for scripts/regenerate_srcinfo.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the script importable as a module.
SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))


def test_parses_pkgname_pkgver():
    from regenerate_srcinfo import parse_pkgbuild

    pkgbuild = """
pkgname=test-pkg
pkgver=1.2.3
pkgrel=1
pkgdesc='A test package'
arch=('any')
url='https://example.com'
license=('MIT')
"""
    result = parse_pkgbuild(pkgbuild)
    assert result["pkgname"] == "test-pkg"
    assert result["pkgver"] == "1.2.3"
    assert result["pkgrel"] == "1"
    assert result["pkgdesc"] == "A test package"
    assert result["arch"] == ["any"]
    assert result["url"] == "https://example.com"
    assert result["license"] == ["MIT"]


def test_parses_array_with_multiple_entries():
    from regenerate_srcinfo import parse_pkgbuild

    pkgbuild = """
pkgname=test
depends=('python' 'mpv' 'ffmpeg')
"""
    result = parse_pkgbuild(pkgbuild)
    assert result["depends"] == ["python", "mpv", "ffmpeg"]


def test_emits_srcinfo_format():
    from regenerate_srcinfo import emit_srcinfo

    parsed = {
        "pkgname": "ytm-player-git",
        "pkgver": "1.9.0",
        "pkgrel": "1",
        "pkgdesc": "YouTube Music TUI client",
        "arch": ["any"],
        "license": ["MIT"],
        "depends": ["python", "mpv"],
        "url": "https://github.com/peternaame-boop/ytm-player",
        "source": ["git+https://github.com/peternaame-boop/ytm-player.git"],
        "sha256sums": ["SKIP"],
    }
    output = emit_srcinfo(parsed)
    assert "pkgbase = ytm-player-git" in output
    assert "pkgver = 1.9.0" in output
    assert "depends = python" in output
    assert "depends = mpv" in output
    # Empty-line separator + pkgname trailing line is required by AUR.
    assert "\npkgname = ytm-player-git" in output


def test_round_trip_with_repo_pkgbuild():
    """Smoke test: parsing the actual repo PKGBUILD yields a non-empty .SRCINFO."""
    from regenerate_srcinfo import emit_srcinfo, parse_pkgbuild

    pkgbuild_path = Path(__file__).resolve().parents[2] / "aur" / "PKGBUILD"
    if not pkgbuild_path.exists():
        pytest.skip("aur/PKGBUILD not present in this checkout")
    parsed = parse_pkgbuild(pkgbuild_path.read_text(encoding="utf-8"))
    output = emit_srcinfo(parsed)
    # Must include the pkgname (top-level pkgbase line).
    assert "pkgbase = " in output
    # Must include a pkgver line.
    assert "\tpkgver = " in output
    # Must end with a pkgname trailing line.
    assert "pkgname = " in output


def test_multiline_array():
    """Array values may span multiple lines."""
    from regenerate_srcinfo import parse_pkgbuild

    pkgbuild = """
pkgname=test
depends=('python'
         'mpv'
         'ffmpeg')
"""
    result = parse_pkgbuild(pkgbuild)
    assert result["depends"] == ["python", "mpv", "ffmpeg"]


def test_expands_shell_variables_in_arrays():
    """``source=("git+${url}.git")`` should expand against the already-parsed url scalar."""
    from regenerate_srcinfo import parse_pkgbuild

    pkgbuild = """
pkgname=test
url='https://example.com/foo'
source=("git+${url}.git")
"""
    result = parse_pkgbuild(pkgbuild)
    assert result["source"] == ["git+https://example.com/foo.git"]
