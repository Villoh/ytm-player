"""Tests for SessionMixin._restore_session_state crash-resistance.

Session state is loaded on startup. If session.json is corrupt or
missing we must fall back cleanly — a crash here means users can't
launch the app at all after one bad shutdown.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from ytm_player.app._session import SessionMixin
from ytm_player.services.queue import RepeatMode


def _fresh_session_host():
    h = SessionMixin()
    h.player = MagicMock()
    h.player.set_volume = AsyncMock()
    h.queue = MagicMock()
    h.queue.set_repeat = MagicMock()
    h.queue.add_multiple = MagicMock()
    h.queue.jump_to = MagicMock()
    h.queue.toggle_shuffle = MagicMock()
    h.queue.tracks = []
    h.queue.current_track = None
    h.settings = MagicMock()
    h.settings.playback.default_volume = 80
    h.query_one = MagicMock()
    h._sidebar_per_page = {}
    h._sidebar_default = True
    h._lyrics_sidebar_open = False
    h._active_library_playlist_id = None
    return h


class TestRestoreSessionResilience:
    async def test_missing_file_uses_defaults(self, tmp_path, monkeypatch):
        h = _fresh_session_host()
        missing = tmp_path / "missing.json"
        monkeypatch.setattr("ytm_player.config.paths.SESSION_STATE_FILE", missing, raising=False)
        # Should not raise.
        await h._restore_session_state()
        h.player.set_volume.assert_awaited_once_with(80)

    async def test_corrupt_json_does_not_raise(self, tmp_path, monkeypatch):
        h = _fresh_session_host()
        bad = tmp_path / "session.json"
        bad.write_text("{ this is not valid JSON", encoding="utf-8")
        monkeypatch.setattr("ytm_player.config.paths.SESSION_STATE_FILE", bad, raising=False)
        # Should not raise — bad JSON falls back to defaults.
        await h._restore_session_state()
        h.player.set_volume.assert_awaited_once_with(80)
        h.queue.set_repeat.assert_called_once_with(RepeatMode.OFF)

    async def test_invalid_repeat_value_falls_back_to_off(self, tmp_path, monkeypatch):
        h = _fresh_session_host()
        bad = tmp_path / "session.json"
        bad.write_text('{"repeat": "garbage"}', encoding="utf-8")
        monkeypatch.setattr("ytm_player.config.paths.SESSION_STATE_FILE", bad, raising=False)
        await h._restore_session_state()
        h.queue.set_repeat.assert_called_once_with(RepeatMode.OFF)

    async def test_valid_state_applied(self, tmp_path, monkeypatch):
        h = _fresh_session_host()
        good = tmp_path / "session.json"
        good.write_text(
            '{"schema_version": 1, "volume": 42, "repeat": "all", '
            '"shuffle": false, "queue_tracks": [], "queue_index": 0}',
            encoding="utf-8",
        )
        monkeypatch.setattr("ytm_player.config.paths.SESSION_STATE_FILE", good, raising=False)
        await h._restore_session_state()
        h.player.set_volume.assert_awaited_once_with(42)
        h.queue.set_repeat.assert_called_once_with(RepeatMode.ALL)


class TestSchemaVersion:
    async def test_mismatched_schema_version_discards_state(self, tmp_path, monkeypatch):
        """A session.json with a different schema_version is discarded."""
        h = _fresh_session_host()
        bad = tmp_path / "session.json"
        bad.write_text(
            '{"schema_version": 99, "volume": 42, "repeat": "all"}',
            encoding="utf-8",
        )
        monkeypatch.setattr("ytm_player.config.paths.SESSION_STATE_FILE", bad, raising=False)
        await h._restore_session_state()
        # Defaults applied — volume 80, repeat OFF — not the file's 42 / ALL.
        h.player.set_volume.assert_awaited_once_with(80)
        h.queue.set_repeat.assert_called_once_with(RepeatMode.OFF)
