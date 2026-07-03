"""Tests for reporting TUI plays back to the YT Music account history.

Reporting is scheduled with a wall-clock timer so it still fires when the
terminal loses focus but mpv keeps playing. A generation check prevents quick
skips from being logged; a tiny ``position > 0`` guard verifies playback
actually started. Opt-out (default on).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from ytm_player.app._playback import (
    _YTM_HISTORY_MAX,
    _YTM_HISTORY_MIN_SECONDS,
    _YTM_HISTORY_POLL_SECONDS,
    PlaybackMixin,
)


def _host(
    *,
    enabled: bool = True,
    ytmusic: object | None = "default",
    play_generation: int = 1,
    reported_generation: int = -1,
    position: float = 1.0,
    video_id: str = "vid1",
) -> MagicMock:
    host = MagicMock()
    host.settings.playback.sync_history_to_ytmusic = enabled
    host.ytmusic = MagicMock() if ytmusic == "default" else ytmusic
    host._play_generation = play_generation
    host._ytm_reported_generation = reported_generation
    host._ytm_history = None
    host._local_history_play_id = None
    host._local_history_video_id = ""
    host._local_history_pending_seconds = None
    host._track_start_position = 0.0
    host.history = MagicMock()
    host.player.position = position
    host.player.current_track = {"video_id": video_id} if video_id else None
    host.set_timer = MagicMock()
    host.run_worker = MagicMock()
    return host


def _schedule(host, video_id="vid1", generation=1) -> None:
    track = {"video_id": video_id}
    PlaybackMixin._schedule_ytm_history_report.__get__(host)(track, video_id, generation)


def _schedule_local(host, video_id="vid1", generation=1) -> None:
    track = {"video_id": video_id}
    PlaybackMixin._schedule_local_history_log.__get__(host)(track, video_id, generation)


def _report(host, video_id="vid1", generation=1) -> None:
    track = {"video_id": video_id}
    PlaybackMixin._report_ytm_play.__get__(host)(track, video_id, generation)


def _report_local(host, video_id="vid1", generation=1) -> None:
    track = {"video_id": video_id}
    PlaybackMixin._report_local_play.__get__(host)(track, video_id, generation)


# ── scheduling ───────────────────────────────────────────────────────


def test_schedule_arms_initial_threshold_timer() -> None:
    host = _host()
    _schedule(host)
    host.set_timer.assert_called_once()
    assert host.set_timer.call_args.args[0] == _YTM_HISTORY_MIN_SECONDS


def test_schedule_skips_when_disabled() -> None:
    host = _host(enabled=False)
    _schedule(host)
    host.set_timer.assert_not_called()


def test_schedule_skips_without_ytmusic() -> None:
    host = _host(ytmusic=None)
    _schedule(host)
    host.set_timer.assert_not_called()


def test_schedule_skips_without_video_id() -> None:
    host = _host()
    _schedule(host, video_id="")
    host.set_timer.assert_not_called()


# ── timer callback ───────────────────────────────────────────────────


def test_report_fires_once_position_crosses_threshold() -> None:
    host = _host(play_generation=3, position=_YTM_HISTORY_MIN_SECONDS)
    _report(host, generation=3)
    host.ytmusic.add_history_item.assert_called_once_with("vid1")
    host.run_worker.assert_called_once()
    assert host._ytm_reported_generation == 3


def test_report_skips_stale_generation() -> None:
    """A track skipped before the timer fired bumped the generation."""
    host = _host(play_generation=5)
    _report(host, generation=4)
    host.run_worker.assert_not_called()


def test_report_repolls_while_position_below_threshold() -> None:
    host = _host(position=_YTM_HISTORY_MIN_SECONDS - 1)
    _report(host)
    host.ytmusic.add_history_item.assert_not_called()
    host.run_worker.assert_not_called()
    host.set_timer.assert_called_once()
    assert host.set_timer.call_args.args[0] == _YTM_HISTORY_POLL_SECONDS


def test_report_repolls_when_resumed_below_relative_threshold() -> None:
    """On resume-on-launch the track starts mid-file, so raw position is high
    but the actual listen time (position - start) is still below threshold."""
    host = _host(position=_YTM_HISTORY_MIN_SECONDS + 100)
    host._track_start_position = float(_YTM_HISTORY_MIN_SECONDS + 100 - 1)  # heard ~1s
    _report(host)
    host.ytmusic.add_history_item.assert_not_called()
    host.run_worker.assert_not_called()
    host.set_timer.assert_called_once()
    assert host.set_timer.call_args.args[0] == _YTM_HISTORY_POLL_SECONDS


def test_report_fires_when_resumed_and_listened_past_threshold() -> None:
    host = _host(position=200.0, play_generation=3)
    host._track_start_position = float(200 - _YTM_HISTORY_MIN_SECONDS)  # heard 5s
    _report(host, generation=3)
    host.ytmusic.add_history_item.assert_called_once_with("vid1")


def test_report_skips_when_already_reported() -> None:
    host = _host(play_generation=2, reported_generation=2)
    _report(host, generation=2)
    host.run_worker.assert_not_called()


def test_report_skips_when_disabled_mid_play() -> None:
    host = _host(enabled=False)
    _report(host)
    host.run_worker.assert_not_called()


# ── local SQLite history ─────────────────────────────────────────────


def test_local_schedule_arms_threshold_timer() -> None:
    host = _host()
    _schedule_local(host)
    host.set_timer.assert_called_once()
    assert host.set_timer.call_args.args[0] == _YTM_HISTORY_MIN_SECONDS


def test_local_report_repolls_until_position_exceeds_threshold() -> None:
    host = _host(position=_YTM_HISTORY_MIN_SECONDS)
    _report_local(host)
    host.run_worker.assert_not_called()
    host.set_timer.assert_called_once()
    assert host.set_timer.call_args.args[0] == _YTM_HISTORY_POLL_SECONDS


def test_local_report_inserts_once_position_exceeds_threshold() -> None:
    host = _host(position=_YTM_HISTORY_MIN_SECONDS + 1)
    _report_local(host)
    host.run_worker.assert_called_once()


def test_local_report_fires_even_when_current_track_cleared() -> None:
    """Natural advance: a duplicate mpv end-file clears player.current_track
    while the track keeps playing. The report must still fire (generation is
    the source of truth), otherwise the play is silently dropped."""
    host = _host(position=_YTM_HISTORY_MIN_SECONDS + 1)
    host.player.current_track = None
    _report_local(host)
    host.run_worker.assert_called_once()


def test_ytm_report_fires_even_when_current_track_cleared() -> None:
    host = _host(position=_YTM_HISTORY_MIN_SECONDS)
    host.player.current_track = None
    _report(host)
    host.ytmusic.add_history_item.assert_called_once_with("vid1")


async def test_local_insert_records_play_id() -> None:
    host = _host(play_generation=4)
    # _report_local_play stamps the sentinel before scheduling the worker.
    host._local_history_play_id = -1
    host._local_history_video_id = "vid1"
    host.history.log_play = AsyncMock(return_value=123)

    await PlaybackMixin._insert_local_history_play.__get__(host)(
        {"video_id": "vid1"},
        _YTM_HISTORY_MIN_SECONDS + 1,
        "vid1",
        4,
    )

    assert host._local_history_play_id == 123
    assert host._local_history_video_id == "vid1"


async def test_local_insert_still_logs_when_superseded_after_threshold() -> None:
    """A skip right after crossing the 5s threshold must not drop the row."""
    host = _host(play_generation=4)
    host._local_history_play_id = -1
    host._local_history_video_id = "vid1"
    host.history.log_play = AsyncMock(return_value=123)
    # Track was superseded (skip) while the insert was scheduled.
    host._play_generation = 5

    await PlaybackMixin._insert_local_history_play.__get__(host)(
        {"video_id": "vid1"},
        _YTM_HISTORY_MIN_SECONDS + 1,
        "vid1",
        4,
    )

    host.history.log_play.assert_awaited_once()
    assert host._local_history_play_id == 123


async def test_local_insert_bails_when_superseded_by_other_report() -> None:
    """Another track's report reused the sentinel; this stale insert is dropped."""
    host = _host()
    host._local_history_play_id = -1
    host._local_history_video_id = "vid2"  # a newer report claimed the sentinel
    host.history.log_play = AsyncMock(return_value=123)

    await PlaybackMixin._insert_local_history_play.__get__(host)(
        {"video_id": "vid1"},
        _YTM_HISTORY_MIN_SECONDS + 1,
        "vid1",
        1,
    )

    host.history.log_play.assert_not_awaited()


async def test_local_insert_applies_pending_duration() -> None:
    """Finalize ran while the insert was in flight; the final duration wins."""
    host = _host()
    host._local_history_play_id = -1
    host._local_history_video_id = "vid1"
    host._local_history_pending_seconds = 90  # stashed by _log_local_listen
    host._reset_local_history_state = PlaybackMixin._reset_local_history_state.__get__(host)
    host.history.log_play = AsyncMock(return_value=123)
    host.history.update_play_listened_seconds = AsyncMock()

    await PlaybackMixin._insert_local_history_play.__get__(host)(
        {"video_id": "vid1"},
        _YTM_HISTORY_MIN_SECONDS + 1,
        "vid1",
        1,
    )

    host.history.update_play_listened_seconds.assert_awaited_once_with(123, 90)
    # State cleared: the play already ended, nothing left to track.
    assert host._local_history_play_id is None
    assert host._local_history_video_id == ""
    assert host._local_history_pending_seconds is None


async def test_final_local_log_hands_off_when_insert_in_flight() -> None:
    """Finalize while sentinel is -1 stashes the duration and keeps the sentinel."""
    host = _host(position=90)
    host._local_history_play_id = -1
    host._local_history_video_id = "vid1"
    host.history.update_play_listened_seconds = AsyncMock()
    host.history.log_play = AsyncMock()

    await PlaybackMixin._log_local_listen.__get__(host)({"video_id": "vid1"})

    # No DB write here — handed off to the in-flight worker instead.
    host.history.update_play_listened_seconds.assert_not_awaited()
    host.history.log_play.assert_not_awaited()
    assert host._local_history_pending_seconds == 90
    # Sentinel preserved so the worker can attribute + apply the duration.
    assert host._local_history_play_id == -1
    assert host._local_history_video_id == "vid1"


async def test_final_local_log_updates_existing_row() -> None:
    host = _host(position=60)
    host._local_history_play_id = 123
    host._local_history_video_id = "vid1"
    host.history.update_play_listened_seconds = AsyncMock()

    await PlaybackMixin._log_local_listen.__get__(host)({"video_id": "vid1"})

    host.history.update_play_listened_seconds.assert_awaited_once_with(123, 60)
    assert host._local_history_play_id is None
    assert host._local_history_video_id == ""


# ── optimistic cache update ──────────────────────────────────────────


def _add(host, video_id="vid1", track=None) -> None:
    if track is None:
        track = {"video_id": video_id, "title": "X"}
    PlaybackMixin._optimistic_ytm_history_add.__get__(host)(track, video_id)


def test_optimistic_noop_when_cache_unfetched() -> None:
    host = MagicMock()
    host._ytm_history = None
    _add(host)
    assert host._ytm_history is None


def test_optimistic_prepends_and_dedups() -> None:
    host = MagicMock()
    host._ytm_history = [{"video_id": "a"}, {"video_id": "vid1"}, {"video_id": "b"}]
    host._get_current_page.return_value = MagicMock()  # not a RecentlyPlayedPage
    _add(host, "vid1", {"video_id": "vid1", "title": "X"})
    ids = [t["video_id"] for t in host._ytm_history]
    assert ids == ["vid1", "a", "b"]


def test_optimistic_uses_passed_track_not_current_track() -> None:
    """On natural advance a duplicate end-file can clear player.current_track;
    the optimistic add must still use the track captured at schedule time."""
    host = MagicMock()
    host._ytm_history = [{"video_id": "a"}]
    host.player.current_track = None  # cleared by duplicate end-file
    host._get_current_page.return_value = MagicMock()
    _add(host, "vid1", {"video_id": "vid1", "title": "X"})
    assert [t["video_id"] for t in host._ytm_history] == ["vid1", "a"]


def test_optimistic_caps_length() -> None:
    host = MagicMock()
    host._ytm_history = [{"video_id": f"v{i}"} for i in range(_YTM_HISTORY_MAX)]
    host._get_current_page.return_value = MagicMock()
    _add(host, "new", {"video_id": "new", "title": "X"})
    assert len(host._ytm_history) == _YTM_HISTORY_MAX
    assert host._ytm_history[0]["video_id"] == "new"


def test_optimistic_entry_matches_server_row_schema() -> None:
    """Optimistically-added rows and server rows (normalize_tracks output) both
    feed the same cache/TrackTable, so they must share the display schema.
    Tracks flowing through playback are already normalized; this locks that
    contract so the two data paths can't silently diverge.
    """
    from ytm_player.utils.formatting import normalize_tracks

    raw = {
        "videoId": "vid1",
        "title": "Song",
        "artists": [{"name": "Artist"}],
        "album": {"name": "Album"},
        "duration": "3:00",
    }
    server_row = normalize_tracks([raw])[0]

    host = MagicMock()
    host._ytm_history = []
    host._get_current_page.return_value = MagicMock()
    # A track flowing through playback is a normalized dict (same as server_row).
    _add(host, "vid1", dict(server_row))
    entry = host._ytm_history[0]

    # The keys TrackTable renders from must be present on optimistic entries.
    display_keys = {"video_id", "title", "artist", "artists", "album", "duration"}
    assert display_keys <= entry.keys()
    assert display_keys <= server_row.keys()


# ── optimistic local update ──────────────────────────────────────────


def test_optimistic_local_add_calls_page_when_open() -> None:
    from ytm_player.ui.pages.recently_played import _TAB_LOCAL, RecentlyPlayedPage

    host = MagicMock()
    page = MagicMock(spec=RecentlyPlayedPage)
    host._get_current_page.return_value = page
    track = {"video_id": "vid1", "title": "X"}

    PlaybackMixin._optimistic_local_history_add.__get__(host)(track)

    page.optimistic_add.assert_called_once_with(_TAB_LOCAL, track)


def test_optimistic_local_add_noop_when_page_closed() -> None:
    host = MagicMock()
    host._get_current_page.return_value = MagicMock()  # not a RecentlyPlayedPage
    PlaybackMixin._optimistic_local_history_add.__get__(host)({"video_id": "vid1"})
    # No RecentlyPlayedPage → nothing to assert beyond no exception.
