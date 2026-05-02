from __future__ import annotations

from unittest.mock import MagicMock

from ytm_player.app._app import YTMPlayerApp
from ytm_player.config.settings import Settings


def test_app_initializes_theme_from_ui_settings(monkeypatch):
    settings = Settings()
    settings.ui.theme = "textual-dark"

    monkeypatch.setattr("ytm_player.app._app.get_settings", lambda: settings)
    monkeypatch.setattr("ytm_player.app._app.get_keymap", MagicMock())
    monkeypatch.setattr("ytm_player.app._app.get_theme", MagicMock())

    app = YTMPlayerApp()

    assert app.theme == "textual-dark"


def test_set_current_theme_as_default_saves_config(monkeypatch):
    settings = Settings()
    settings.ui.theme = "ytm-dark"
    settings.save = MagicMock()

    monkeypatch.setattr("ytm_player.app._app.get_settings", lambda: settings)
    monkeypatch.setattr("ytm_player.app._app.get_keymap", MagicMock())
    monkeypatch.setattr("ytm_player.app._app.get_theme", MagicMock())

    app = YTMPlayerApp()
    app.theme = "textual-dark"
    app.notify = MagicMock()

    app.action_set_current_theme_as_default()

    assert settings.ui.theme == "textual-dark"
    settings.save.assert_called_once_with()
    app.notify.assert_called_once()
    args, kwargs = app.notify.call_args
    message = args[0] if args else kwargs.get("message", "")
    assert "textual-dark" in message
    assert kwargs.get("severity") in (None, "information")


def test_set_current_theme_as_default_rolls_back_on_save_failure(monkeypatch):
    settings = Settings()
    settings.ui.theme = "ytm-dark"
    settings.save = MagicMock(side_effect=OSError("read-only filesystem"))

    monkeypatch.setattr("ytm_player.app._app.get_settings", lambda: settings)
    monkeypatch.setattr("ytm_player.app._app.get_keymap", MagicMock())
    monkeypatch.setattr("ytm_player.app._app.get_theme", MagicMock())

    app = YTMPlayerApp()
    app.theme = "textual-dark"
    app.notify = MagicMock()

    app.action_set_current_theme_as_default()

    assert settings.ui.theme == "ytm-dark"
    settings.save.assert_called_once_with()
    app.notify.assert_called_once()
    _, kwargs = app.notify.call_args
    assert kwargs.get("severity") == "error"


def test_command_palette_exposes_set_default_theme(monkeypatch):
    settings = Settings()

    monkeypatch.setattr("ytm_player.app._app.get_settings", lambda: settings)
    monkeypatch.setattr("ytm_player.app._app.get_keymap", MagicMock())
    monkeypatch.setattr("ytm_player.app._app.get_theme", MagicMock())

    app = YTMPlayerApp()
    screen = MagicMock()
    screen.query.return_value = []
    screen.maximized = None
    screen.focused = None
    commands = list(app.get_system_commands(screen))

    assert any(command.title == "Set Current Theme as Default" for command in commands)
