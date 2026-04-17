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
        assert player._current_track is None, (
            "play() error path must clear _current_track"
        )
        # Lock should have been acquired at least twice (once for the play
        # setup, once for the cleanup).
        assert len(lock_acquisitions) >= 2, (
            f"expected >=2 lock acquisitions (setup + error cleanup), "
            f"got {len(lock_acquisitions)}"
        )
        # ERROR event should have fired.
        assert len(errors) == 1


class TestTryRecoverState:
    """I4: _try_recover() must clear _current_track so the next play()
    doesn't increment _end_file_skip for a track mpv won't fire end-file for."""

    async def test_try_recover_clears_current_track(self, player):
        """After mpv recovery, _current_track must be None.

        The bug: _try_recover only resets _end_file_skip = 0.  If
        _current_track stays set, the next play() call sees it != None
        and increments _end_file_skip — eating the legitimate end-of-track
        event from the new playback.
        """
        # Pretend a track was playing when mpv crashed.
        player._current_track = {"video_id": "stale", "title": "Stale"}
        player._end_file_skip = 7  # arbitrary leftover

        # _try_recover re-creates _mpv via _init_mpv.  Patch _init_mpv to
        # return a fresh mock so we don't actually init mpv.
        new_mock_mpv = MagicMock()
        new_mock_mpv.volume = 80
        with patch.object(player, "_init_mpv", return_value=new_mock_mpv):
            ok = player._try_recover()

        assert ok is True
        assert player._current_track is None, (
            "_try_recover must clear _current_track to avoid skip-counter leak"
        )
        assert player._end_file_skip == 0
