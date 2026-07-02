"""Tests for the TUI single-instance launch guard.

A second `ytm` launch while a TUI is already running would unlink the live
instance's IPC socket, overwrite its PID file, and fight over session.json —
so the CLI must refuse to start and point at the existing PID instead.
"""

from __future__ import annotations

import faulthandler

from click.testing import CliRunner

from ytm_player.cli import main
from ytm_player.config.settings import Settings


def test_second_instance_is_refused(monkeypatch):
    monkeypatch.setattr("ytm_player.cli.try_claim_pid", lambda: 12345)

    result = CliRunner().invoke(main, [])

    assert result.exit_code == 1
    assert "already running (PID 12345)" in result.stderr


def test_launch_proceeds_when_no_instance_running(monkeypatch, tmp_path):
    """The guard must not block a legitimate launch."""
    monkeypatch.setattr("ytm_player.cli.try_claim_pid", lambda: None)
    # Neutralise the TUI-launch side effects downstream of the guard so the
    # test never touches real config/logs/crash dirs or starts Textual.
    monkeypatch.setattr("ytm_player.cli.ensure_dirs", lambda: None)
    monkeypatch.setattr("ytm_player.cli.get_settings", lambda: Settings())
    monkeypatch.setattr("ytm_player.cli.setup_logging", lambda **kwargs: None)
    monkeypatch.setattr("ytm_player.cli.install_excepthooks", lambda **kwargs: None)
    monkeypatch.setattr("ytm_player.cli.CRASH_DIR", tmp_path / "crashes")
    monkeypatch.setattr(faulthandler, "enable", lambda **kwargs: None)

    launched = {}

    class FakeApp:
        def run(self):
            launched["ran"] = True

    import ytm_player.app

    monkeypatch.setattr(ytm_player.app, "YTMPlayerApp", FakeApp)

    result = CliRunner().invoke(main, [])

    assert result.exit_code == 0, result.output
    assert launched.get("ran") is True
