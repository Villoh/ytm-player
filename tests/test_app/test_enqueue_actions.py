"""Tests for the app-level Add-to-Queue / Play-Next keyboard handlers.

These live in TrackActionsMixin and back the ``Z``/``C-z`` and ``X``/``C-x``
keys on every page (one shared path, no per-page copies).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from ytm_player.app._track_actions import TrackActionsMixin


class TestResolveActionTrack:
    def test_prefers_focused_track(self):
        host = MagicMock()
        focused = {"video_id": "f1", "title": "Focused"}
        host._get_focused_track = MagicMock(return_value=focused)
        assert TrackActionsMixin._resolve_action_track(host) is focused

    def test_falls_back_to_playing_track(self):
        host = MagicMock()
        host._get_focused_track = MagicMock(return_value=None)
        playing = {"video_id": "p1", "title": "Playing"}
        host.player = MagicMock()
        host.player.current_track = playing
        assert TrackActionsMixin._resolve_action_track(host) is playing

    def test_none_when_nothing_focused_or_playing(self):
        host = MagicMock()
        host._get_focused_track = MagicMock(return_value=None)
        host.player = None
        assert TrackActionsMixin._resolve_action_track(host) is None


class TestEnqueueHelpers:
    def test_enqueue_track_adds_refreshes_notifies(self):
        host = MagicMock()
        track = {"video_id": "v1", "title": "Song"}
        TrackActionsMixin._enqueue_track(host, track)
        host.queue.add.assert_called_once_with(track)
        host._refresh_queue_page.assert_called_once()
        assert "Song" in host.notify.call_args[0][0]

    def test_play_track_next_inserts_refreshes_notifies(self):
        host = MagicMock()
        track = {"video_id": "v1", "title": "Song"}
        TrackActionsMixin._play_track_next(host, track)
        host.queue.add_next.assert_called_once_with(track)
        host._refresh_queue_page.assert_called_once()
        msg = host.notify.call_args[0][0]
        assert "Song" in msg and "next" in msg.lower()

    def test_missing_title_falls_back(self):
        host = MagicMock()
        TrackActionsMixin._enqueue_track(host, {"video_id": "v1"})
        assert "track" in host.notify.call_args[0][0]


class TestAddFocusedToQueue:
    def test_enqueues_resolved_track(self):
        host = MagicMock()
        track = {"video_id": "v1", "title": "Song"}
        host._resolve_action_track = MagicMock(return_value=track)
        TrackActionsMixin._add_focused_to_queue(host)
        host._enqueue_track.assert_called_once_with(track)

    def test_warns_and_noops_without_track(self):
        host = MagicMock()
        host._resolve_action_track = MagicMock(return_value=None)
        TrackActionsMixin._add_focused_to_queue(host)
        host._enqueue_track.assert_not_called()
        host.notify.assert_called_once()
        assert host.notify.call_args.kwargs.get("severity") == "warning"


class TestPlayFocusedNext:
    def test_plays_resolved_track_next(self):
        host = MagicMock()
        track = {"video_id": "v1", "title": "Song"}
        host._resolve_action_track = MagicMock(return_value=track)
        TrackActionsMixin._play_focused_next(host)
        host._play_track_next.assert_called_once_with(track)

    def test_warns_and_noops_without_track(self):
        host = MagicMock()
        host._resolve_action_track = MagicMock(return_value=None)
        TrackActionsMixin._play_focused_next(host)
        host._play_track_next.assert_not_called()
        host.notify.assert_called_once()
        assert host.notify.call_args.kwargs.get("severity") == "warning"
