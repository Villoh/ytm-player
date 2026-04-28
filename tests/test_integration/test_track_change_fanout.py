"""Integration test: TRACK_CHANGE event fans out to all registered subscribers.

When Player emits TRACK_CHANGE (e.g. on play, on auto-advance), every
callback registered via Player.on(...) should receive the event in
registration order. This validates the cross-service event-bus contract
that MPRIS / Discord / Last.fm rely on.

Phase 1 of the broad-except audit flagged async-coordination as an
under-covered area. The Player dispatch system bridges from mpv's
callback thread to the asyncio loop via call_soon_threadsafe; this test
exercises the synchronous-fallback path (no event loop registered),
which is the simplest path that still hits _dispatch end-to-end.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from ytm_player.services.player import Player, PlayerEvent


async def test_track_change_event_fans_out_to_all_subscribers(mock_mpv):
    """Three subscribers (mpris/discord/lastfm shaped) all receive TRACK_CHANGE.

    Asserts:
      - every registered callback is invoked exactly once
      - the payload each receives is the original track_info dict
      - callbacks fire in registration order (the contract MPRIS/Discord/
        Last.fm subscribers implicitly depend on)
    """
    # Arrange — fresh Player (autouse _reset_singletons resets between tests).
    player = Player()
    received: list[tuple[str, dict]] = []

    cb_mpris = MagicMock(side_effect=lambda track: received.append(("mpris", track)))
    cb_discord = MagicMock(side_effect=lambda track: received.append(("discord", track)))
    cb_lastfm = MagicMock(side_effect=lambda track: received.append(("lastfm", track)))

    player.on(PlayerEvent.TRACK_CHANGE, cb_mpris)
    player.on(PlayerEvent.TRACK_CHANGE, cb_discord)
    player.on(PlayerEvent.TRACK_CHANGE, cb_lastfm)

    test_track = {
        "video_id": "xyz789",
        "title": "Fanout Track",
        "artist": "Test Artist",
    }

    # Act — trigger TRACK_CHANGE via Player.play (fires after the
    # asyncio.to_thread(_play_sync) returns).
    await player.play("http://fake.url/xyz789.opus", test_track)

    # Assert — all three callbacks received the event in registration order.
    cb_mpris.assert_called_once_with(test_track)
    cb_discord.assert_called_once_with(test_track)
    cb_lastfm.assert_called_once_with(test_track)
    assert [name for name, _payload in received] == ["mpris", "discord", "lastfm"]
    for _name, payload in received:
        assert payload is test_track


async def test_track_change_fan_out_via_loop_dispatch(mock_mpv):
    """Same fan-out contract, but with an event loop registered so dispatch
    routes through call_soon_threadsafe (the production code path used when
    mpv invokes its callbacks from a non-asyncio thread).

    Yields control after play() so queued call_soon callbacks execute before
    assertions.
    """
    player = Player()
    player.set_event_loop(asyncio.get_running_loop())

    received: list[str] = []
    cb_mpris = MagicMock(side_effect=lambda _t: received.append("mpris"))
    cb_discord = MagicMock(side_effect=lambda _t: received.append("discord"))
    cb_lastfm = MagicMock(side_effect=lambda _t: received.append("lastfm"))

    player.on(PlayerEvent.TRACK_CHANGE, cb_mpris)
    player.on(PlayerEvent.TRACK_CHANGE, cb_discord)
    player.on(PlayerEvent.TRACK_CHANGE, cb_lastfm)

    test_track = {"video_id": "xyz789", "title": "Loop Dispatch", "artist": "Artist"}
    await player.play("http://fake.url/xyz789.opus", test_track)

    # call_soon_threadsafe queues callbacks onto the loop — yield control
    # so they run before we assert.
    await asyncio.sleep(0)

    cb_mpris.assert_called_once_with(test_track)
    cb_discord.assert_called_once_with(test_track)
    cb_lastfm.assert_called_once_with(test_track)
    assert received == ["mpris", "discord", "lastfm"]
