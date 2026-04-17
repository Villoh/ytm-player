"""Tests for PlaybackMixin.play_track guards and dispatch.

Three bug classes guarded against:
1. Double-click producing two play_track calls (debounce within 1 second).
2. Tracks lacking video_id (AI-generated streams) hanging the queue
   instead of being skipped.
3. Cached audio path bypasses stream resolver entirely.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from ytm_player.app._playback import PlaybackMixin


def _fresh_playback_host():
    """Build a PlaybackMixin instance with the attrs play_track reads."""
    p = PlaybackMixin()
    p.player = MagicMock()
    p.player.play = AsyncMock()
    p.player.current_track = None
    p.player.position = 0.0
    p.stream_resolver = MagicMock()
    p.stream_resolver.resolve = AsyncMock(return_value=None)
    p.stream_resolver.clear_cache = MagicMock()
    p.queue = MagicMock()
    p.queue.next_track = MagicMock(return_value=None)
    p.queue.peek_next = MagicMock(return_value=None)
    p.history = None
    p.cache = None
    p.discord = None
    p.lastfm = None
    p.mpris = None
    p.mac_media = None
    p.settings = MagicMock()
    p.settings.notifications.enabled = False
    p.notify = MagicMock()
    p.call_later = MagicMock()
    p.run_worker = MagicMock()
    # query_one raises — caught by play_track's try/except around UI updates
    p.query_one = MagicMock(side_effect=Exception("no widget in test"))
    p._last_play_video_id = None
    p._last_play_time = 0.0
    p._consecutive_failures = 0
    p._track_start_position = 0.0
    p._advancing = False
    return p


class TestPlayTrackDebounce:
    async def test_failed_play_clears_debounce_so_retry_works(self, monkeypatch):
        """Regression: stream-resolve failure must clear the debounce stamp.

        Otherwise the user clicking the same track again within 1s gets
        silently no-op'd instead of retrying.
        """
        host = _fresh_playback_host()
        # Resolver returns None — simulating "stream unavailable".
        host.stream_resolver.resolve = AsyncMock(return_value=None)
        # No queue advance candidate.
        host.queue.next_track = MagicMock(return_value=None)

        monkeypatch.setattr("ytm_player.app._playback.time.monotonic", lambda: 100.0)

        track = {"video_id": "abc", "title": "X"}
        await host.play_track(track)

        # First call set the stamp, then the failure handler should have cleared it.
        assert host._last_play_video_id == ""

        # Second call within "1s" should NOT be debounced.
        from ytm_player.services.stream import StreamInfo

        host.stream_resolver.resolve = AsyncMock(
            return_value=StreamInfo(
                url="http://x",
                video_id="abc",
                format="opus",
                bitrate=128,
                duration=200,
                expires_at=float("inf"),
                thumbnail_url=None,
            )
        )
        await host.play_track(track)
        host.player.play.assert_called_once()

    async def test_same_video_id_within_1s_is_debounced(self, monkeypatch):
        """Calling play_track twice for same video_id within 1s is a no-op the second time."""
        host = _fresh_playback_host()
        from ytm_player.services.stream import StreamInfo

        host.stream_resolver.resolve = AsyncMock(
            return_value=StreamInfo(
                url="http://x",
                video_id="abc",
                format="opus",
                bitrate=128,
                duration=200,
                expires_at=float("inf"),
                thumbnail_url=None,
            )
        )

        track = {"video_id": "abc", "title": "X", "artist": "Y"}

        # Freeze monotonic so both calls land in the same instant.
        monkeypatch.setattr("ytm_player.app._playback.time.monotonic", lambda: 100.0)
        await host.play_track(track)
        await host.play_track(track)

        host.player.play.assert_called_once()

    async def test_different_video_ids_not_debounced(self, monkeypatch):
        host = _fresh_playback_host()
        from ytm_player.services.stream import StreamInfo

        async def resolve_side_effect(vid):
            return StreamInfo(
                url=f"http://{vid}",
                video_id=vid,
                format="opus",
                bitrate=128,
                duration=200,
                expires_at=float("inf"),
                thumbnail_url=None,
            )

        host.stream_resolver.resolve = AsyncMock(side_effect=resolve_side_effect)
        monkeypatch.setattr("ytm_player.app._playback.time.monotonic", lambda: 100.0)
        await host.play_track({"video_id": "abc", "title": "A"})
        await host.play_track({"video_id": "xyz", "title": "B"})
        assert host.player.play.call_count == 2


class TestPlayTrackMissingVideoId:
    async def test_missing_video_id_skips_and_advances(self):
        host = _fresh_playback_host()
        host.queue.next_track = MagicMock(return_value={"video_id": "next123", "title": "Next"})
        await host.play_track({"video_id": "", "title": "AI track", "artist": ""})
        # User notified, queue advance attempted.
        assert host.notify.called
        host.queue.next_track.assert_called_once()
        # Stream resolver was NOT invoked for the broken track.
        host.stream_resolver.resolve.assert_not_called()


class TestPlayTrackCacheHit:
    async def test_cache_hit_bypasses_stream_resolver(self, tmp_path):
        host = _fresh_playback_host()
        cached_file = tmp_path / "abc.opus"
        cached_file.write_bytes(b"")
        host.cache = MagicMock()
        host.cache.get = AsyncMock(return_value=cached_file)

        track = {"video_id": "abc", "title": "X", "duration": 200}
        await host.play_track(track)

        # Cached path used; remote resolver skipped.
        host.cache.get.assert_called_once_with("abc")
        host.stream_resolver.resolve.assert_not_called()
        host.player.play.assert_called_once()
        played_url = host.player.play.call_args[0][0]
        assert played_url == str(cached_file)
