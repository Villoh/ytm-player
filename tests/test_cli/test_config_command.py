"""Tests for `ytm config` editor invocation."""

from __future__ import annotations

from typing import Any

import pytest
from click.testing import CliRunner

from ytm_player.cli import main


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Redirect CONFIG_DIR / CONFIG_FILE to a tmp dir so the test never
    writes to the developer's real config."""
    config_dir = tmp_path / "config"
    config_file = config_dir / "config.toml"
    monkeypatch.setattr("ytm_player.cli.CONFIG_DIR", config_dir)
    monkeypatch.setattr("ytm_player.cli.CONFIG_FILE", config_file)
    return config_dir, config_file


def _patch_subprocess(monkeypatch) -> dict[str, Any]:
    """Intercept subprocess.run so the test never actually launches an editor."""
    captured: dict[str, Any] = {}

    def fake_run(args, **kwargs):
        captured["args"] = list(args)
        captured["kwargs"] = kwargs
        return None

    monkeypatch.setattr("ytm_player.cli.subprocess.run", fake_run)
    return captured


def test_editor_with_args_is_tokenised(isolated_config, monkeypatch):
    """Regression: EDITOR="code -w" must split into ["code", "-w"], not be
    passed as a single argv entry — otherwise subprocess.run would look
    for an executable literally named "code -w" and fail."""
    _, config_file = isolated_config
    monkeypatch.setenv("EDITOR", "code -w")
    captured = _patch_subprocess(monkeypatch)

    result = CliRunner().invoke(main, ["config"])

    assert result.exit_code == 0, result.output
    assert captured["args"] == ["code", "-w", str(config_file)]


def test_single_word_editor_unchanged(isolated_config, monkeypatch):
    """EDITOR="vim" stays a single argv entry, no spurious tokenisation."""
    _, config_file = isolated_config
    monkeypatch.setenv("EDITOR", "vim")
    captured = _patch_subprocess(monkeypatch)

    result = CliRunner().invoke(main, ["config"])

    assert result.exit_code == 0, result.output
    assert captured["args"] == ["vim", str(config_file)]


def test_editor_with_quoted_path(isolated_config, monkeypatch):
    """shlex handles quoted segments — EDITOR='/path/with spaces/ed -x' is
    parsed as ["/path/with spaces/ed", "-x"], not split on the inner space."""
    _, config_file = isolated_config
    monkeypatch.setenv("EDITOR", "'/opt/My Editor/bin/ed' --no-fork")
    captured = _patch_subprocess(monkeypatch)

    result = CliRunner().invoke(main, ["config"])

    assert result.exit_code == 0, result.output
    assert captured["args"] == [
        "/opt/My Editor/bin/ed",
        "--no-fork",
        str(config_file),
    ]


def test_malformed_editor_quoting_does_not_crash(isolated_config, monkeypatch):
    """shlex.split raises ValueError on unbalanced quotes — must be caught
    and routed through _error so the CLI exits cleanly instead of crashing."""
    _, _ = isolated_config
    # Unmatched single quote — shlex.split raises ValueError("No closing quotation").
    monkeypatch.setenv("EDITOR", "code 'unclosed")

    # subprocess.run should never be reached; patch it so a regression that
    # bypassed the ValueError catch would still not actually launch anything.
    captured = _patch_subprocess(monkeypatch)

    result = CliRunner().invoke(main, ["config"])

    # _error calls sys.exit(1).
    assert result.exit_code != 0
    assert "Failed to open editor" in result.output
    assert "args" not in captured
