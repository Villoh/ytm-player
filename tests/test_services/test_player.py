"""Concurrency and recovery tests for Player.

The Player runs on the main thread but mpv invokes end-file/time-pos
callbacks on its own thread, which dispatches through Player._dispatch.
The shared state (_current_track, _end_file_skip) MUST be mutated only
under _skip_lock — otherwise mpv's callback can read a half-updated
state and miscount _end_file_skip, swallowing legitimate end-of-track
events (the "auto-advance randomly stops" class of bug).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def player(monkeypatch):
    """Construct a Player with mpv fully mocked, reset singleton on teardown."""
    from ytm_player.services.player import Player

    # Reset the singleton so each test gets a fresh instance.
    Player._instance = None

    mock_mpv_instance = MagicMock()
    mock_mpv_instance.volume = 80
    mock_mpv_instance.pause = False
    mock_mpv_class = MagicMock(return_value=mock_mpv_instance)

    monkeypatch.setattr("mpv.MPV", mock_mpv_class)

    p = Player()
    p._mpv = mock_mpv_instance  # ensure tests use the mock
    yield p
    Player._instance = None


class TestPlayCurrentTrackLocking:
    """C1: play()/stop() must clear _current_track under _skip_lock."""

    async def test_play_error_path_clears_current_track_under_lock(self, player):
        """If _play_sync raises, _current_track must be cleared atomically.

        The bug: clearing _current_track outside _skip_lock races with
        mpv's end-file callback, which reads _current_track to decide
        whether to dispatch TRACK_END.
        """
        from ytm_player.services.player import PlayerEvent

        # Pretend a previous track is still loaded.
        player._current_track = {"video_id": "prev", "title": "Prev"}

        # Track lock acquisitions during the failure path.
        original_lock = player._skip_lock
        lock_acquisitions: list[bool] = []

        class TrackingLock:
            def __enter__(self):
                lock_acquisitions.append(True)
                original_lock.__enter__()
                return self

            def __exit__(self, *args):
                original_lock.__exit__(*args)

        player._skip_lock = TrackingLock()

        def fail_sync(url):
            raise RuntimeError("simulated mpv failure")

        # Subscribe to ERROR events to confirm dispatch happens.
        errors: list = []
        player.on(PlayerEvent.ERROR, lambda exc: errors.append(exc))

        with patch.object(player, "_play_sync", side_effect=fail_sync):
            await player.play("http://stream", {"video_id": "new", "title": "New"})

        # After failure: _current_track should be cleared.
        assert player._current_track is None, "play() error path must clear _current_track"
        # Lock should have been acquired at least twice (once for the play
        # setup, once for the cleanup).
        assert len(lock_acquisitions) >= 2, (
            f"expected >=2 lock acquisitions (setup + error cleanup), got {len(lock_acquisitions)}"
        )
        # ERROR event should have fired.
        assert len(errors) == 1


class TestTryRecoverState:
    """Regression: _try_recover() must NOT clear _current_track.

    _try_recover is only ever called from within play(), which has already
    set _current_track to the new track being started. Clearing it breaks
    MPRIS, Discord, Last.fm, and the _on_end_file guard for the recovered
    track — auto-advance silently breaks until the next manual play.
    """

    def test_try_recover_preserves_current_track(self, player):
        """Regression: _try_recover must NOT clear _current_track.

        It's only called from play() which has already set _current_track
        to the new track we're starting. Clearing it would break MPRIS,
        Discord, and the _on_end_file guard for the recovered track.
        """
        player._current_track = {"video_id": "abc", "title": "X"}
        player._end_file_skip = 7  # arbitrary leftover

        new_mock_mpv = MagicMock()
        new_mock_mpv.volume = 80
        with patch.object(player, "_init_mpv", return_value=new_mock_mpv):
            ok = player._try_recover()

        assert ok is True
        assert player._current_track == {"video_id": "abc", "title": "X"}, (
            "_try_recover must NOT clear _current_track"
        )
        assert player._end_file_skip == 0

    async def test_play_with_recovery_keeps_current_track_set(self, player):
        """End-to-end: play() → _play_sync raises ShutdownError → _try_recover
        succeeds → second mpv.play() succeeds → _current_track is the new track,
        NOT None.
        """
        # Use the mpv proxy from services.player so this test works whether
        # libmpv is genuinely importable or replaced with the stub.
        from ytm_player.services.player import mpv as _mpv

        # First mpv.play() raises ShutdownError; second succeeds.
        player._mpv.play = MagicMock(side_effect=[_mpv.ShutdownError("simulated crash"), None])
        player._mpv.pause = False

        # _try_recover replaces _mpv with a fresh instance.
        new_mpv = MagicMock()
        new_mpv.play = MagicMock(return_value=None)
        new_mpv.pause = False
        player._init_mpv = MagicMock(return_value=new_mpv)
        player._loop = None  # Skip volume restore branch.

        track = {"video_id": "abc", "title": "X"}
        await player.play("http://example.com/stream", track)

        assert player._current_track == track, (
            "After successful recovery, _current_track must reflect the new track"
        )
