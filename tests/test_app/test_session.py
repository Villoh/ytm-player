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
    h._pending_resume_video_id = None
    h._pending_resume_position = 0.0
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


class TestResumeOnLaunch:
    async def test_resume_on_launch_disabled_skips_restore(self, tmp_path, monkeypatch):
        """When resume_on_launch is False, the resume block is skipped."""
        h = _fresh_session_host()
        h.settings.playback.resume_on_launch = False
        good = tmp_path / "session.json"
        good.write_text(
            '{"schema_version": 1, "volume": 80, "repeat": "off", '
            '"shuffle": false, "queue_tracks": [{"video_id": "abc", "title": "X"}], '
            '"queue_index": 0, "resume": {"video_id": "abc", "position": 42.5}}',
            encoding="utf-8",
        )
        monkeypatch.setattr("ytm_player.config.paths.SESSION_STATE_FILE", good, raising=False)
        h._pending_resume_video_id = None
        h._pending_resume_position = 0.0
        await h._restore_session_state()
        assert h._pending_resume_video_id is None
        assert h._pending_resume_position == 0.0

    async def test_resume_on_launch_enabled_sets_pending(self, tmp_path, monkeypatch):
        """When resume_on_launch is True (default), pending state is populated."""
        h = _fresh_session_host()
        h.settings.playback.resume_on_launch = True
        # Make queue.tracks behave like a real list with a matching video_id.
        sample_track = {"video_id": "abc", "title": "X", "duration": 200}
        h.queue.tracks = [sample_track]
        h.queue.current_track = sample_track
        h._pending_resume_video_id = None
        h._pending_resume_position = 0.0

        good = tmp_path / "session.json"
        good.write_text(
            '{"schema_version": 1, "volume": 80, "repeat": "off", '
            '"shuffle": false, "queue_tracks": [{"video_id": "abc", "title": "X"}], '
            '"queue_index": 0, "resume": {"video_id": "abc", "position": 42.5}}',
            encoding="utf-8",
        )
        monkeypatch.setattr("ytm_player.config.paths.SESSION_STATE_FILE", good, raising=False)
        await h._restore_session_state()
        assert h._pending_resume_video_id == "abc"
        assert h._pending_resume_position == 42.5
