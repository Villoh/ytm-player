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
    host._track_start_position = 0.0
    host.history = MagicMock()
    host.player.position = position
    host.player.current_track = {"video_id": video_id} if video_id else None
    host.set_timer = MagicMock()
    host.run_worker = MagicMock()
    return host


def _schedule(host, video_id="vid1", generation=1) -> None:
    PlaybackMixin._schedule_ytm_history_report.__get__(host)(video_id, generation)


def _schedule_local(host, video_id="vid1", generation=1) -> None:
    PlaybackMixin._schedule_local_history_log.__get__(host)(video_id, generation)


def _report(host, video_id="vid1", generation=1) -> None:
    PlaybackMixin._report_ytm_play.__get__(host)(video_id, generation)


def _report_local(host, video_id="vid1", generation=1) -> None:
    PlaybackMixin._report_local_play.__get__(host)(video_id, generation)


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


async def test_local_insert_records_play_id() -> None:
    host = _host(play_generation=4)
    host.history.log_play = AsyncMock(return_value=123)

    await PlaybackMixin._insert_local_history_play.__get__(host)(
        {"video_id": "vid1"},
        _YTM_HISTORY_MIN_SECONDS + 1,
        "vid1",
        4,
    )

    assert host._local_history_play_id == 123
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


def _add(host, video_id="vid1") -> None:
    PlaybackMixin._optimistic_ytm_history_add.__get__(host)(video_id)


def test_optimistic_noop_when_cache_unfetched() -> None:
    host = MagicMock()
    host._ytm_history = None
    _add(host)
    assert host._ytm_history is None


def test_optimistic_prepends_and_dedups() -> None:
    host = MagicMock()
    host._ytm_history = [{"video_id": "a"}, {"video_id": "vid1"}, {"video_id": "b"}]
    host.player.current_track = {"video_id": "vid1", "title": "X"}
    host._get_current_page.return_value = MagicMock()  # not a RecentlyPlayedPage
    _add(host, "vid1")
    ids = [t["video_id"] for t in host._ytm_history]
    assert ids == ["vid1", "a", "b"]


def test_optimistic_caps_length() -> None:
    host = MagicMock()
    host._ytm_history = [{"video_id": f"v{i}"} for i in range(_YTM_HISTORY_MAX)]
    host.player.current_track = {"video_id": "new", "title": "X"}
    host._get_current_page.return_value = MagicMock()
    _add(host, "new")
    assert len(host._ytm_history) == _YTM_HISTORY_MAX
    assert host._ytm_history[0]["video_id"] == "new"
