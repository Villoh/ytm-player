"""Shared fixtures for app/ mixin tests.

The mixins inherit from textual.App and read attributes set on `self`
(player, queue, settings, etc.). Booting a real App per test is slow and
brittle. Instead we build a MagicMock host configured with the minimum
attributes each mixin reads, then call mixin methods directly with
``Mixin.method.__get__(host)(...)``.

For methods that touch widget tree (`self.query_one(...)`), the host's
``query_one`` returns a MagicMock by default — tests can override per-id
via the ``query_one_map`` argument to ``make_host``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


def make_host(
    *,
    player: Any | None = None,
    queue: Any | None = None,
    settings: Any | None = None,
    ytmusic: Any | None = None,
    history: Any | None = None,
    cache: Any | None = None,
    stream_resolver: Any | None = None,
    discord: Any | None = None,
    lastfm: Any | None = None,
    mpris: Any | None = None,
    mac_media: Any | None = None,
    downloader: Any | None = None,
    query_one_map: dict[str, Any] | None = None,
) -> MagicMock:
    """Build a MagicMock host with the attributes mixins read.

    Anything not passed in defaults to a MagicMock so attribute access
    doesn't AttributeError. For services that should be "absent" (e.g.
    no Discord configured), pass ``discord=None`` explicitly.
    """
    host = MagicMock()
    host.player = player if player is not None else MagicMock()
    host.queue = queue if queue is not None else MagicMock()
    host.settings = settings if settings is not None else MagicMock()
    host.ytmusic = ytmusic if ytmusic is not None else MagicMock()
    host.history = history
    host.cache = cache
    host.stream_resolver = stream_resolver if stream_resolver is not None else MagicMock()
    host.discord = discord
    host.lastfm = lastfm
    host.mpris = mpris
    host.mac_media = mac_media
    host.downloader = downloader if downloader is not None else MagicMock()

    # Async methods that mixins await on the host itself.
    host.notify = MagicMock()
    host.call_later = MagicMock()
    host.run_worker = MagicMock()

    # query_one routing.
    qmap = query_one_map or {}

    def _query_one(selector: str, *_args: Any, **_kwargs: Any) -> Any:
        return qmap.get(selector, MagicMock())

    host.query_one = MagicMock(side_effect=_query_one)
    return host


@pytest.fixture
def host() -> MagicMock:
    """Default empty mock host."""
    return make_host()


@pytest.fixture
def make_async_player() -> Any:
    """Build a player MagicMock with async methods stubbed via AsyncMock."""

    def _factory(**overrides: Any) -> MagicMock:
        p = MagicMock()
        p.play = AsyncMock()
        p.pause = AsyncMock()
        p.resume = AsyncMock()
        p.toggle_pause = AsyncMock()
        p.set_volume = AsyncMock()
        p.change_volume = AsyncMock()
        p.seek = AsyncMock()
        p.seek_absolute = AsyncMock()
        p.seek_start = AsyncMock()
        p.mute = AsyncMock()
        p.is_playing = False
        p.is_paused = False
        p.position = 0.0
        p.duration = 0.0
        p.volume = 80
        p.current_track = None
        for k, v in overrides.items():
            setattr(p, k, v)
        return p

    return _factory
