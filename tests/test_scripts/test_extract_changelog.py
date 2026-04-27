"""Tests for the publish-workflow CHANGELOG extractor.

The script lives outside the package (under ``.github/scripts/``) so it
gets imported by path here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "extract_changelog.py"
_spec = importlib.util.spec_from_file_location("extract_changelog", _SCRIPT)
assert _spec is not None and _spec.loader is not None
extract_changelog = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(extract_changelog)


SAMPLE_CHANGELOG = """\
# Changelog

All notable changes are documented here.

---

### v1.7.2 (2026-04-27)

A combined release covering many things.

**New**

- Thing A
- Thing B

**Fixes**

- A bug

---

### v1.7.0 (2026-04-27)

Older release.

- Old item
"""


def test_extracts_section_for_existing_version():
    out = extract_changelog.extract_section(SAMPLE_CHANGELOG, "1.7.2")
    assert out.startswith("### v1.7.2 (2026-04-27)")
    assert "Thing A" in out
    assert "Thing B" in out
    assert "A bug" in out


def test_does_not_include_next_release_or_trailing_separator():
    out = extract_changelog.extract_section(SAMPLE_CHANGELOG, "1.7.2")
    assert "v1.7.0" not in out
    assert "Old item" not in out
    assert not out.rstrip().endswith("---")


def test_raises_when_section_missing():
    with pytest.raises(ValueError, match="no '### v9.9.9' section"):
        extract_changelog.extract_section(SAMPLE_CHANGELOG, "9.9.9")


def test_handles_section_at_end_of_file():
    body = "### v1.0.0 (2025-01-01)\n\nFirst release.\n"
    out = extract_changelog.extract_section(body, "1.0.0")
    assert "First release" in out


def test_strips_trailing_blank_lines_and_separator():
    body = "### v1.0.0\n\nContent\n\n\n---\n\n### v0.9.0\n"
    out = extract_changelog.extract_section(body, "1.0.0")
    assert out == "### v1.0.0\n\nContent\n"


def test_does_not_match_partial_version():
    """`1.7.2` must not match a section header for `1.7.20` or similar."""
    body = "### v1.7.20\n\nA different release.\n"
    with pytest.raises(ValueError):
        extract_changelog.extract_section(body, "1.7.2")


def test_main_writes_section_to_stdout(tmp_path, capsys):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(SAMPLE_CHANGELOG, encoding="utf-8")

    rc = extract_changelog.main(["script", "v1.7.2", str(changelog)])
    captured = capsys.readouterr()

    assert rc == 0
    assert captured.out.startswith("### v1.7.2 (2026-04-27)")
    assert "Thing A" in captured.out


def test_main_returns_1_on_missing_section(tmp_path, capsys):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(SAMPLE_CHANGELOG, encoding="utf-8")

    rc = extract_changelog.main(["script", "v9.9.9", str(changelog)])
    captured = capsys.readouterr()

    assert rc == 1
    assert "ERROR" in captured.err


def test_main_returns_2_on_bad_args(capsys):
    rc = extract_changelog.main(["script"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "usage" in captured.err
